"""Portfolio optimization with native HiGHS and optional compatibility backends.

Maximizes expected return net of expected loss under credit constraints.
Supports multiple uncertainty policies for PD constraints:
- point_estimate: uses point PD only
- hard_worst_case: uses conformal upper bound
- blended_uncertainty: interpolates between point and upper bound

The active IJDS path uses the direct ``highspy`` formulation. Pyomo remains a
lazy-loaded compatibility backend for historical replay and cross-solver tests.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import pandas as pd
from loguru import logger
from scipy.optimize import linprog
from scipy.sparse import csc_matrix, csr_matrix, hstack

from src.optimization.policy import PolicyMode, resolve_policy_mode


@dataclass(frozen=True)
class _PortfolioLpComponents:
    n: int
    loan_amounts: np.ndarray
    objective_coefficients: np.ndarray
    a_ub: csr_matrix
    rhs: np.ndarray
    bounds: list[tuple[float, float]]
    use_pd_slack: bool


def _require_pyomo() -> Any:
    """Import the compatibility modeling layer only when explicitly requested."""
    try:
        import pyomo.environ as pyo
    except ImportError as exc:  # pragma: no cover - exercised in minimal installs
        raise RuntimeError(
            "The Pyomo compatibility backend is not installed. "
            "Run `uv sync --group compat` or use the native highspy backend."
        ) from exc
    return pyo


def solution_allocation_vector(solution: Mapping[str, Any], n_items: int) -> np.ndarray:
    """Return a validated dense allocation vector from any solver payload."""
    n = int(n_items)
    if n < 0:
        raise ValueError(f"n_items must be nonnegative, got {n}")

    raw_vector = solution.get("allocation_vector")
    if raw_vector is not None:
        allocation = np.asarray(raw_vector, dtype=float)
    else:
        raw_mapping = solution.get("allocation")
        if not isinstance(raw_mapping, Mapping):
            raise TypeError(
                "Solver result must contain allocation_vector or an allocation mapping."
            )
        allocation = np.fromiter(
            (float(raw_mapping.get(i, 0.0)) for i in range(n)),
            dtype=float,
            count=n,
        )

    if allocation.shape != (n,):
        raise ValueError(f"Solver allocation shape mismatch: {allocation.shape} != {(n,)}")
    if not np.all(np.isfinite(allocation)):
        raise ValueError("Solver allocation contains non-finite values.")
    return allocation


def compute_effective_pd(
    pd_point: np.ndarray,
    pd_high: np.ndarray,
    *,
    policy_mode: str | PolicyMode = PolicyMode.HARD_WORST_CASE,
    gamma: float = 1.0,
    delta_cap_quantile: float | None = None,
    tail_focus_quantile: float | None = None,
    segment_labels: np.ndarray | None = None,
    min_segment_size: int = 100,
) -> np.ndarray:
    """Resolve the PD vector used in the portfolio PD constraint.

    Args:
        pd_point: Point PD estimates.
        pd_high: Upper conformal PD bound.
        policy_mode: A :class:`PolicyMode` or legacy alias string. Canonical
            names: ``point_estimate``, ``hard_worst_case``, ``blended_uncertainty``,
            ``capped_blended_uncertainty``, ``tail_blended_uncertainty``,
            ``segment_tail_blended_uncertainty``,
            ``segment_relative_tail_blended_uncertainty``. Legacy aliases
            (``"point"``, ``"worst_case"``, ``"robust"``, ...) are also accepted.
        gamma: Blend weight for the blended policies.
        delta_cap_quantile: Optional quantile cap for ``capped_blended_uncertainty``.
        tail_focus_quantile: Optional uncertainty-tail quantile for
            ``tail_blended_uncertainty``.
        segment_labels: Optional context labels used by
            ``segment_tail_blended_uncertainty``.
        min_segment_size: Minimum segment size before falling back to global
            tail cutoff in the segment-based policies.
    """
    point = np.asarray(pd_point, dtype=float)
    high = np.asarray(pd_high, dtype=float)
    mode = resolve_policy_mode(policy_mode)
    if mode is PolicyMode.POINT_ESTIMATE:
        return point
    if mode is PolicyMode.HARD_WORST_CASE:
        return high
    if mode is PolicyMode.BLENDED_UNCERTAINTY:
        return _blend_pd(point, _pd_delta(point, high), gamma)
    if mode is PolicyMode.CAPPED_BLENDED_UNCERTAINTY:
        delta = _pd_delta(point, high)
        cap = _quantile_or_zero(delta, _clipped_quantile(delta_cap_quantile, default=1.0))
        return _blend_pd(point, np.minimum(delta, cap), gamma)
    if mode is PolicyMode.TAIL_BLENDED_UNCERTAINTY:
        delta = _pd_delta(point, high)
        local_delta = _tail_delta(
            delta=delta,
            score=delta,
            q=_clipped_quantile(tail_focus_quantile, default=0.9),
        )
        return _blend_pd(point, local_delta, gamma)
    if mode is PolicyMode.SEGMENT_TAIL_BLENDED_UNCERTAINTY:
        delta = _pd_delta(point, high)
        q = _clipped_quantile(tail_focus_quantile, default=0.9)
        local_delta = _segment_tail_delta(
            delta=delta,
            score=delta,
            q=q,
            segment_labels=segment_labels,
            min_segment_size=min_segment_size,
        )
        return _blend_pd(point, local_delta, gamma)
    if mode is PolicyMode.SEGMENT_RELATIVE_TAIL_BLENDED_UNCERTAINTY:
        delta = _pd_delta(point, high)
        relative_width = delta / np.maximum(point, 1e-4)
        q = _clipped_quantile(tail_focus_quantile, default=0.9)
        local_delta = _segment_tail_delta(
            delta=delta,
            score=relative_width,
            q=q,
            segment_labels=segment_labels,
            min_segment_size=min_segment_size,
        )
        return _blend_pd(point, local_delta, gamma)
    raise ValueError(f"Unhandled policy mode: {mode!r}")  # safety net, unreachable


def _pd_delta(point: np.ndarray, high: np.ndarray) -> np.ndarray:
    return cast(np.ndarray, np.clip(high - point, 0.0, 1.0))


def _clipped_quantile(value: float | None, *, default: float) -> float:
    raw = default if value is None else float(value)
    return float(np.clip(raw, 0.0, 1.0))


def _quantile_or_zero(values: np.ndarray, q: float) -> float:
    return float(np.quantile(values, q)) if len(values) else 0.0


def _blend_pd(point: np.ndarray, delta: np.ndarray, gamma: float) -> np.ndarray:
    weight = float(np.clip(gamma, 0.0, 1.0))
    return np.clip(point + weight * delta, 0.0, 1.0)


def _tail_delta(*, delta: np.ndarray, score: np.ndarray, q: float) -> np.ndarray:
    cutoff = _quantile_or_zero(score, q)
    return np.where(score >= cutoff, delta, 0.0)


def _segment_tail_delta(
    *,
    delta: np.ndarray,
    score: np.ndarray,
    q: float,
    segment_labels: np.ndarray | None,
    min_segment_size: int,
) -> np.ndarray:
    if segment_labels is None or len(segment_labels) != len(delta):
        return _tail_delta(delta=delta, score=score, q=q)

    labels = pd.Series(np.asarray(segment_labels, dtype=object)).fillna("unknown").astype(str)
    local_delta = np.zeros_like(delta)
    global_cutoff = _quantile_or_zero(score, q)
    min_size = int(max(min_segment_size, 1))
    for label in labels.unique():
        mask_arr = (labels == label).to_numpy(dtype=bool)
        segment_score = score[mask_arr]
        cutoff = (
            global_cutoff if len(segment_score) < min_size else _quantile_or_zero(segment_score, q)
        )
        local_delta[mask_arr] = np.where(segment_score >= cutoff, delta[mask_arr], 0.0)
    return local_delta


def build_portfolio_model(
    loans: pd.DataFrame,
    pd_point: np.ndarray,
    pd_low: np.ndarray,
    pd_high: np.ndarray,
    lgd: np.ndarray,
    int_rates: np.ndarray,
    total_budget: float = 1_000_000,
    max_concentration: float = 0.25,
    max_portfolio_pd: float = 0.10,
    robust: bool = True,
    uncertainty_aversion: float = 0.0,
    min_budget_utilization: float = 0.0,
    pd_cap_slack_penalty: float = 0.0,
    pd_constraint_override: np.ndarray | None = None,
) -> Any:
    """Build Pyomo portfolio optimization model.

    Args:
        loans: DataFrame with loan features.
        pd_point: Point PD estimates.
        pd_low: Lower bound PD from conformal prediction.
        pd_high: Upper bound PD from conformal prediction.
        lgd: Loss Given Default estimates.
        int_rates: Interest rates (expected return).
        total_budget: Total capital to allocate.
        max_concentration: Maximum fraction per purpose segment.
        max_portfolio_pd: Maximum portfolio-level default rate.
        robust: If True, use pd_high for risk constraints.
        uncertainty_aversion: Linear penalty weight on PD uncertainty in the objective.
        min_budget_utilization: Optional minimum budget utilization in [0, 1].
        pd_cap_slack_penalty: Optional penalty for weighted-PD cap slack.

    Returns:
        Pyomo ConcreteModel ready to solve.
    """
    pyo = _require_pyomo()
    n = len(loans)
    model = pyo.ConcreteModel("CreditPortfolioOptimization")

    model.I = pyo.RangeSet(0, n - 1)

    model.int_rate = pyo.Param(model.I, initialize=dict(enumerate(int_rates)))
    pd_constraint = (
        np.asarray(pd_constraint_override, dtype=float)
        if pd_constraint_override is not None
        else (pd_high if robust else pd_point)
    )
    model.pd_point = pyo.Param(model.I, initialize=dict(enumerate(pd_point)))
    model.pd_worst = pyo.Param(model.I, initialize=dict(enumerate(pd_constraint)))
    pd_uncertainty = np.clip(pd_high - pd_point, 0.0, 1.0)
    model.pd_uncertainty = pyo.Param(model.I, initialize=dict(enumerate(pd_uncertainty)))
    model.lgd = pyo.Param(model.I, initialize=dict(enumerate(lgd)))
    model.loan_amnt = pyo.Param(
        model.I,
        initialize=dict(
            enumerate(loans["loan_amnt"].values if "loan_amnt" in loans.columns else np.ones(n))
        ),
    )

    # x[i] = fraction of loan i to fund
    model.x = pyo.Var(model.I, domain=pyo.NonNegativeReals, bounds=(0, 1))
    use_pd_slack = pd_cap_slack_penalty > 0
    if use_pd_slack:
        # Slack in weighted-PD units to avoid degenerate zero-investment solutions.
        model.pd_cap_slack = pyo.Var(domain=pyo.NonNegativeReals)

    def objective_rule(m: Any) -> Any:
        base = sum(
            m.x[i]
            * m.loan_amnt[i]
            * (
                m.int_rate[i]
                - m.pd_point[i] * m.lgd[i]
                - uncertainty_aversion * m.pd_uncertainty[i] * m.lgd[i]
            )
            for i in m.I
        )
        if use_pd_slack:
            return base - pd_cap_slack_penalty * m.pd_cap_slack
        return base

    model.obj = pyo.Objective(rule=objective_rule, sense=pyo.maximize)

    def budget_rule(m: Any) -> Any:
        return sum(m.x[i] * m.loan_amnt[i] for i in m.I) <= total_budget

    model.budget = pyo.Constraint(rule=budget_rule)

    min_budget_utilization = float(np.clip(min_budget_utilization, 0.0, 1.0))
    if min_budget_utilization > 0:

        def min_budget_rule(m: Any) -> Any:
            return (
                sum(m.x[i] * m.loan_amnt[i] for i in m.I) >= min_budget_utilization * total_budget
            )

        model.min_budget = pyo.Constraint(rule=min_budget_rule)

    def pd_cap_rule(m: Any) -> Any:
        total_exposure = sum(m.x[i] * m.loan_amnt[i] for i in m.I) + 1e-6
        weighted_pd = sum(m.x[i] * m.loan_amnt[i] * m.pd_worst[i] for i in m.I)
        rhs = max_portfolio_pd * total_exposure
        if use_pd_slack:
            rhs = rhs + m.pd_cap_slack
        return weighted_pd <= rhs

    model.pd_cap = pyo.Constraint(rule=pd_cap_rule)

    if "purpose" in loans.columns:
        purposes = loans["purpose"].fillna("unknown").astype(str).unique()
        loan_purpose = loans["purpose"].fillna("unknown").astype(str).values
        for p_idx, purpose in enumerate(purposes):
            mask = [i for i in range(n) if loan_purpose[i] == purpose]

            def concentration_rule(m: Any, _idx: Any = None, _mask: list[int] = mask) -> Any:
                total = sum(m.x[i] * m.loan_amnt[i] for i in m.I) + 1e-6
                sector = sum(m.x[i] * m.loan_amnt[i] for i in _mask)
                return sector <= max_concentration * total

            setattr(model, f"concentration_{p_idx}", pyo.Constraint(rule=concentration_rule))

    logger.info(
        f"Built portfolio model: {n} loans, budget={total_budget:,.0f}, robust={robust}, "
        f"uncertainty_aversion={uncertainty_aversion:.3f}, "
        f"min_budget_utilization={min_budget_utilization:.3f}, "
        f"pd_cap_slack_penalty={pd_cap_slack_penalty:.3f}"
    )
    return model


def solve_portfolio(
    model: Any,
    time_limit: int = 300,
    threads: int = 4,
    solver_backend: str = "highs",
) -> dict[str, Any]:
    """Solve portfolio optimization with HiGHS (default) or optional cuOpt."""
    backend = solver_backend.strip().lower()
    results = _solve_pyomo_backend(
        model,
        backend=backend,
        time_limit=time_limit,
        threads=threads,
    )
    solution = _pyomo_portfolio_solution(model, backend=backend, results=results)
    logger.info(
        "Portfolio solved ({}): obj={:,.2f}, funded={}/{}, allocated={:,.0f}, pd_cap_slack={:.4f}",
        backend,
        solution["objective_value"],
        solution["n_funded"],
        len(solution["allocation"]),
        solution["total_allocated"],
        solution["pd_cap_slack"],
    )
    return solution


def _solve_pyomo_backend(
    model: Any,
    *,
    backend: str,
    time_limit: int,
    threads: int,
) -> Any:
    if backend == "highs":
        return _solve_pyomo_highs(model, time_limit=time_limit, threads=threads)
    if backend == "cuopt":
        return _solve_pyomo_cuopt(model, time_limit=time_limit, threads=threads)
    raise ValueError(f"Unsupported solver_backend={backend!r}. Use 'highs' or 'cuopt'.")


def _solve_pyomo_highs(
    model: Any,
    *,
    time_limit: int,
    threads: int,
) -> Any:
    _require_pyomo()
    from pyomo.contrib.appsi.solvers import Highs

    solver = Highs()
    solver.config.time_limit = time_limit
    _ = threads  # reserved for future HiGHS appsi configuration
    return solver.solve(model)


def _solve_pyomo_cuopt(
    model: Any,
    *,
    time_limit: int,
    threads: int,
) -> Any:
    pyo = _require_pyomo()
    solver = pyo.SolverFactory("cuopt")
    if solver is None or not solver.available(False):
        raise RuntimeError(
            "solver_backend='cuopt' requested but Pyomo cuOpt solver is not available "
            "in this environment."
        )
    _ = (time_limit, threads)  # backend-specific options vary by cuOpt deployment
    return solver.solve(model)


def _pyomo_portfolio_solution(
    model: Any,
    *,
    backend: str,
    results: Any,
) -> dict[str, Any]:
    pyo = _require_pyomo()
    index_set = model.I
    decision_vars = model.x
    loan_amount_param = model.loan_amnt
    allocation = {i: pyo.value(decision_vars[i]) for i in index_set}
    obj_value = pyo.value(model.obj)
    n_funded = sum(1 for v in allocation.values() if v > 0.01)
    total_allocated = sum(allocation[i] * pyo.value(loan_amount_param[i]) for i in index_set)
    pd_cap_slack = float(pyo.value(model.pd_cap_slack)) if hasattr(model, "pd_cap_slack") else 0.0

    return {
        "allocation": allocation,
        "objective_value": float(obj_value),
        "n_funded": int(n_funded),
        "total_allocated": float(total_allocated),
        "solver_status": _pyomo_termination_status(results),
        "solver_backend": backend,
        "pd_cap_slack": pd_cap_slack,
    }


def _pyomo_termination_status(results: Any) -> str:
    termination = getattr(results, "termination_condition", None)
    if termination is None and hasattr(results, "solver"):
        termination = getattr(results.solver, "termination_condition", None)
    return str(termination) if termination is not None else "unknown"


def solve_portfolio_highs_sparse(
    *,
    loans: pd.DataFrame,
    pd_point: np.ndarray,
    pd_low: np.ndarray,
    pd_high: np.ndarray,
    lgd: np.ndarray,
    int_rates: np.ndarray,
    total_budget: float = 1_000_000,
    max_concentration: float = 0.25,
    max_portfolio_pd: float = 0.10,
    robust: bool = True,
    uncertainty_aversion: float = 0.0,
    min_budget_utilization: float = 0.0,
    pd_cap_slack_penalty: float = 0.0,
    pd_constraint_override: np.ndarray | None = None,
    objective_rate_override: np.ndarray | None = None,
    time_limit: int = 300,
    threads: int = 4,
) -> dict[str, Any]:
    """Solve the continuous portfolio LP through SciPy's sparse HiGHS interface.

    This matches :func:`build_portfolio_model` algebraically but bypasses Pyomo
    model construction. The CRPTO exact rerank solves thousands of very similar
    large LPs, so avoiding per-check symbolic model creation is material.
    """
    components = _portfolio_lp_components(
        loans=loans,
        pd_point=pd_point,
        pd_high=pd_high,
        lgd=lgd,
        int_rates=int_rates,
        total_budget=total_budget,
        max_concentration=max_concentration,
        max_portfolio_pd=max_portfolio_pd,
        robust=robust,
        uncertainty_aversion=uncertainty_aversion,
        min_budget_utilization=min_budget_utilization,
        pd_cap_slack_penalty=pd_cap_slack_penalty,
        pd_constraint_override=pd_constraint_override,
        objective_rate_override=objective_rate_override,
    )

    options: dict[str, Any] = {
        "time_limit": float(time_limit),
        "presolve": True,
        "disp": False,
    }
    _ = threads  # SciPy's HiGHS wrapper does not expose a documented threads option.
    result = linprog(
        -components.objective_coefficients.astype(float),
        A_ub=components.a_ub,
        b_ub=components.rhs,
        bounds=components.bounds,
        method="highs",
        options=options,
    )
    if not bool(result.success) or result.x is None:
        raise RuntimeError(
            "SciPy HiGHS did not solve portfolio LP to optimality: "
            f"status={result.status}, message={result.message}"
        )

    primal = np.asarray(result.x, dtype=float)
    summary = _portfolio_solution_summary(primal, components)
    solver_status = "optimal" if bool(result.success) else str(result.message)

    logger.info(
        "Portfolio solved (highs_sparse): obj={:,.2f}, funded={}/{}, allocated={:,.0f}, "
        "pd_cap_slack={:.4f}, status={}",
        summary["objective_value"],
        summary["n_funded"],
        components.n,
        summary["total_allocated"],
        summary["pd_cap_slack"],
        solver_status,
    )
    return {
        **summary,
        "solver_status": solver_status,
        "solver_backend": "highs_sparse",
        "highs_status": int(result.status),
        "highs_message": str(result.message),
        "highs_iterations": int(getattr(result, "nit", 0) or 0),
    }


def solve_portfolio_highspy_native(
    *,
    loans: pd.DataFrame,
    pd_point: np.ndarray,
    pd_low: np.ndarray,
    pd_high: np.ndarray,
    lgd: np.ndarray,
    int_rates: np.ndarray,
    total_budget: float = 1_000_000,
    max_concentration: float = 0.25,
    max_portfolio_pd: float = 0.10,
    robust: bool = True,
    uncertainty_aversion: float = 0.0,
    min_budget_utilization: float = 0.0,
    pd_cap_slack_penalty: float = 0.0,
    pd_constraint_override: np.ndarray | None = None,
    objective_rate_override: np.ndarray | None = None,
    time_limit: int = 300,
    threads: int = 4,
) -> dict[str, Any]:
    """Solve the continuous portfolio LP through the native highspy API.

    ``scipy.optimize.linprog(method="highs")`` is reliable and already avoids
    Pyomo's symbolic-model overhead, but it only exposes a small documented
    subset of HiGHS controls. The native binding lets the exact rerank set
    HiGHS' own thread/parallel options while preserving the same LP algebra.
    """
    try:
        import highspy
    except Exception as exc:  # pragma: no cover - optional runtime dependency
        raise RuntimeError(
            "solver_backend='highspy' requested but highspy is unavailable."
        ) from exc

    components = _portfolio_lp_components(
        loans=loans,
        pd_point=pd_point,
        pd_high=pd_high,
        lgd=lgd,
        int_rates=int_rates,
        total_budget=total_budget,
        max_concentration=max_concentration,
        max_portfolio_pd=max_portfolio_pd,
        robust=robust,
        uncertainty_aversion=uncertainty_aversion,
        min_budget_utilization=min_budget_utilization,
        pd_cap_slack_penalty=pd_cap_slack_penalty,
        pd_constraint_override=pd_constraint_override,
        objective_rate_override=objective_rate_override,
    )
    lp = _build_highspy_lp(highspy, components)
    solver = highspy.Highs()
    _configure_highspy_solver(highspy, solver, time_limit=time_limit, threads=threads)

    status = solver.passModel(lp)
    if status != highspy.HighsStatus.kOk:
        raise RuntimeError(f"highspy failed to accept portfolio LP: {status}")
    run_status = solver.run()
    if run_status == highspy.HighsStatus.kError:
        raise RuntimeError(f"highspy failed while solving portfolio LP: {run_status}")

    model_status = solver.getModelStatus()
    status_text = str(solver.modelStatusToString(model_status))
    if "Optimal" not in status_text:
        raise RuntimeError(
            "highspy did not solve portfolio LP to optimality: "
            f"run_status={run_status}, model_status={status_text}"
        )

    solution = solver.getSolution()
    primal = np.asarray(solution.col_value, dtype=float)
    if len(primal) < components.n:
        raise RuntimeError(
            f"highspy primal solution has length {len(primal)}; expected >= {components.n}."
        )
    summary = _portfolio_solution_summary(primal, components)
    info = solver.getInfo()

    logger.info(
        "Portfolio solved (highspy): obj={:,.2f}, funded={}/{}, allocated={:,.0f}, "
        "pd_cap_slack={:.4f}, status={}",
        summary["objective_value"],
        summary["n_funded"],
        components.n,
        summary["total_allocated"],
        summary["pd_cap_slack"],
        status_text,
    )
    return {
        **summary,
        "solver_status": status_text,
        "solver_backend": "highspy",
        "highs_model_status": status_text,
        "highs_simplex_iterations": int(getattr(info, "simplex_iteration_count", 0) or 0),
        "highs_ipm_iterations": int(getattr(info, "ipm_iteration_count", 0) or 0),
    }


def _build_highspy_lp(highspy: Any, components: _PortfolioLpComponents) -> Any:
    a_ub: csc_matrix = components.a_ub.tocsc()
    bounds = np.asarray(components.bounds, dtype=np.double)
    lp = highspy.HighsLp()
    lp.num_col_ = int(a_ub.shape[1])
    lp.num_row_ = int(a_ub.shape[0])
    lp.col_cost_ = components.objective_coefficients.astype(np.double).tolist()
    lp.col_lower_ = bounds[:, 0].tolist()
    lp.col_upper_ = bounds[:, 1].tolist()
    lp.row_lower_ = np.full(a_ub.shape[0], -highspy.kHighsInf, dtype=np.double).tolist()
    lp.row_upper_ = components.rhs.astype(np.double).tolist()
    lp.sense_ = highspy.ObjSense.kMaximize
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.num_col_ = int(a_ub.shape[1])
    lp.a_matrix_.num_row_ = int(a_ub.shape[0])
    lp.a_matrix_.start_ = a_ub.indptr.astype(np.int32).tolist()
    lp.a_matrix_.index_ = a_ub.indices.astype(np.int32).tolist()
    lp.a_matrix_.value_ = a_ub.data.astype(np.double).tolist()
    return lp


def _configure_highspy_solver(
    highspy: Any,
    solver: Any,
    *,
    time_limit: int,
    threads: int,
) -> None:
    if _env_int("HIGHS_RESET_GLOBAL_SCHEDULER", 1) and hasattr(solver, "resetGlobalScheduler"):
        solver.resetGlobalScheduler(True)
    options: dict[str, bool | int | float | str] = {
        "output_flag": False,
        "log_to_console": False,
        "time_limit": float(time_limit),
        "presolve": _env_str("HIGHS_PRESOLVE", "on"),
        "threads": max(1, int(threads)),
        "parallel": _env_str("HIGHS_PARALLEL", "choose"),
        "solver": _env_str("HIGHS_SOLVER", "choose"),
        "simplex_strategy": _env_int("HIGHS_SIMPLEX_STRATEGY", 0),
    }
    for name, value in options.items():
        status = _set_highs_option(solver, name, value)
        if status != highspy.HighsStatus.kOk and name == "threads":
            status = _retry_highspy_threads_option(solver, name, value)
        if status != highspy.HighsStatus.kOk:
            logger.warning("HiGHS rejected option {}={!r}: {}", name, value, status)


def _set_highs_option(
    highs_solver: Any,
    name: str,
    value: bool | int | float | str,
) -> Any:
    return highs_solver.setOptionValue(name, value)


def _retry_highspy_threads_option(
    solver: Any,
    name: str,
    value: bool | int | float | str,
) -> Any:
    if hasattr(solver, "resetGlobalScheduler"):
        solver.resetGlobalScheduler(True)
    return _set_highs_option(solver, name, value)


def _env_str(name: str, default: str) -> str:
    return str(os.environ.get(name, default)).strip() or default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return int(default)
    try:
        return int(raw)
    except ValueError:
        logger.warning("Ignoring invalid {}={!r}; using {}", name, raw, default)
        return int(default)


def _portfolio_lp_components(
    *,
    loans: pd.DataFrame,
    pd_point: np.ndarray,
    pd_high: np.ndarray,
    lgd: np.ndarray,
    int_rates: np.ndarray,
    total_budget: float,
    max_concentration: float,
    max_portfolio_pd: float,
    robust: bool,
    uncertainty_aversion: float,
    min_budget_utilization: float,
    pd_cap_slack_penalty: float,
    pd_constraint_override: np.ndarray | None,
    objective_rate_override: np.ndarray | None,
) -> _PortfolioLpComponents:
    n = len(loans)
    if n == 0:
        raise ValueError("Cannot solve empty portfolio.")

    loan_amounts = _loan_amounts(loans, n)
    point = np.asarray(pd_point, dtype=float)
    high = np.asarray(pd_high, dtype=float)
    lgd_arr = np.asarray(lgd, dtype=float)
    rates = np.asarray(int_rates, dtype=float)
    pd_constraint = (
        np.asarray(pd_constraint_override, dtype=float)
        if pd_constraint_override is not None
        else (high if robust else point)
    )
    pd_uncertainty = np.clip(high - point, 0.0, 1.0)
    if objective_rate_override is None:
        objective_rate = rates - point * lgd_arr
    else:
        objective_rate = np.asarray(objective_rate_override, dtype=float)
        if objective_rate.shape != point.shape:
            raise ValueError("objective_rate_override must align with pd_point.")
        if not bool(np.isfinite(objective_rate).all()):
            raise ValueError("objective_rate_override must contain finite values.")
    objective = loan_amounts * (
        objective_rate - float(uncertainty_aversion) * pd_uncertainty * lgd_arr
    )

    rows, rhs, pd_cap_row_idx = _portfolio_constraint_rows(
        loans=loans,
        loan_amounts=loan_amounts,
        pd_constraint=pd_constraint,
        total_budget=total_budget,
        max_concentration=max_concentration,
        max_portfolio_pd=max_portfolio_pd,
        min_budget_utilization=min_budget_utilization,
    )
    a_ub = csr_matrix(np.vstack(rows).astype(float))
    objective_coefficients = objective.astype(float)
    bounds = [(0.0, 1.0)] * n
    use_pd_slack = float(pd_cap_slack_penalty) > 0.0
    if use_pd_slack:
        slack_col = np.zeros((a_ub.shape[0], 1), dtype=float)
        slack_col[pd_cap_row_idx, 0] = -1.0
        a_ub = hstack([a_ub, csr_matrix(slack_col)], format="csr")
        objective_coefficients = np.concatenate(
            [objective_coefficients, np.array([-float(pd_cap_slack_penalty)], dtype=float)]
        )
        bounds.append((0.0, float(total_budget)))

    return _PortfolioLpComponents(
        n=n,
        loan_amounts=loan_amounts,
        objective_coefficients=objective_coefficients,
        a_ub=a_ub,
        rhs=np.asarray(rhs, dtype=float),
        bounds=bounds,
        use_pd_slack=use_pd_slack,
    )


def _loan_amounts(loans: pd.DataFrame, n: int) -> np.ndarray:
    if "loan_amnt" not in loans.columns:
        return np.ones(n, dtype=float)
    return cast(
        np.ndarray,
        pd.to_numeric(loans["loan_amnt"], errors="coerce").fillna(1.0).to_numpy(dtype=float),
    )


def _portfolio_constraint_rows(
    *,
    loans: pd.DataFrame,
    loan_amounts: np.ndarray,
    pd_constraint: np.ndarray,
    total_budget: float,
    max_concentration: float,
    max_portfolio_pd: float,
    min_budget_utilization: float,
) -> tuple[list[np.ndarray], list[float], int]:
    rows: list[np.ndarray] = [loan_amounts.astype(float)]
    rhs: list[float] = [float(total_budget)]

    min_budget_utilization = float(np.clip(min_budget_utilization, 0.0, 1.0))
    if min_budget_utilization > 0:
        rows.append((-loan_amounts).astype(float))
        rhs.append(float(-min_budget_utilization * total_budget))

    pd_cap_row_idx = len(rows)
    rows.append((loan_amounts * (pd_constraint - float(max_portfolio_pd))).astype(float))
    rhs.append(0.0)

    if "purpose" in loans.columns:
        purposes = loans["purpose"].fillna("unknown").astype(str)
        for purpose in purposes.unique():
            mask = (purposes == purpose).to_numpy(dtype=float)
            rows.append((loan_amounts * (mask - float(max_concentration))).astype(float))
            rhs.append(0.0)
    return rows, rhs, pd_cap_row_idx


def _portfolio_solution_summary(
    primal: np.ndarray,
    components: _PortfolioLpComponents,
) -> dict[str, Any]:
    alloc = np.clip(primal[: components.n], 0.0, 1.0)
    pd_cap_slack = float(primal[-1]) if components.use_pd_slack else 0.0
    total_allocated = float(np.sum(alloc * components.loan_amounts))
    objective_value = float(np.dot(primal, components.objective_coefficients))
    return {
        "allocation": {i: float(value) for i, value in enumerate(alloc) if value > 1e-12},
        "allocation_vector": alloc,
        "objective_value": objective_value,
        "n_funded": int(np.sum(alloc > 0.01)),
        "total_allocated": total_allocated,
        "pd_cap_slack": pd_cap_slack,
    }


def optimize_portfolio_allocation(
    *,
    loans: pd.DataFrame,
    pd_point: np.ndarray,
    pd_low: np.ndarray,
    pd_high: np.ndarray,
    lgd: np.ndarray,
    int_rates: np.ndarray,
    total_budget: float = 1_000_000,
    max_concentration: float = 0.25,
    max_portfolio_pd: float = 0.10,
    robust: bool = True,
    uncertainty_aversion: float = 0.0,
    min_budget_utilization: float = 0.0,
    pd_cap_slack_penalty: float = 0.0,
    pd_constraint_override: np.ndarray | None = None,
    objective_rate_override: np.ndarray | None = None,
    time_limit: int = 300,
    threads: int = 4,
    solver_backend: str = "highs",
    random_seed: int | None = None,
    cuopt_presolve: int | None = 1,
    cuopt_parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Unified portfolio solve entrypoint for CPU and native cuOpt backends."""
    backend = solver_backend.strip().lower()
    if backend in {"highs", "highs_sparse", "scipy_highs"}:
        return solve_portfolio_highs_sparse(
            loans=loans,
            pd_point=pd_point,
            pd_low=pd_low,
            pd_high=pd_high,
            lgd=lgd,
            int_rates=int_rates,
            total_budget=total_budget,
            max_concentration=max_concentration,
            max_portfolio_pd=max_portfolio_pd,
            robust=robust,
            uncertainty_aversion=uncertainty_aversion,
            min_budget_utilization=min_budget_utilization,
            pd_cap_slack_penalty=pd_cap_slack_penalty,
            pd_constraint_override=pd_constraint_override,
            objective_rate_override=objective_rate_override,
            time_limit=time_limit,
            threads=threads,
        )
    if backend in {"highspy", "highs_native", "native_highs"}:
        try:
            return solve_portfolio_highspy_native(
                loans=loans,
                pd_point=pd_point,
                pd_low=pd_low,
                pd_high=pd_high,
                lgd=lgd,
                int_rates=int_rates,
                total_budget=total_budget,
                max_concentration=max_concentration,
                max_portfolio_pd=max_portfolio_pd,
                robust=robust,
                uncertainty_aversion=uncertainty_aversion,
                min_budget_utilization=min_budget_utilization,
                pd_cap_slack_penalty=pd_cap_slack_penalty,
                pd_constraint_override=pd_constraint_override,
                objective_rate_override=objective_rate_override,
                time_limit=time_limit,
                threads=threads,
            )
        except RuntimeError as exc:
            if str(os.environ.get("HIGHS_NATIVE_FALLBACK_SCIPY", "1")).strip() in {
                "0",
                "false",
                "False",
            }:
                raise
            logger.warning(
                "Native highspy solve failed; falling back to SciPy HiGHS sparse exact solve: {}",
                exc,
            )
            result = solve_portfolio_highs_sparse(
                loans=loans,
                pd_point=pd_point,
                pd_low=pd_low,
                pd_high=pd_high,
                lgd=lgd,
                int_rates=int_rates,
                total_budget=total_budget,
                max_concentration=max_concentration,
                max_portfolio_pd=max_portfolio_pd,
                robust=robust,
                uncertainty_aversion=uncertainty_aversion,
                min_budget_utilization=min_budget_utilization,
                pd_cap_slack_penalty=pd_cap_slack_penalty,
                pd_constraint_override=pd_constraint_override,
                objective_rate_override=objective_rate_override,
                time_limit=time_limit,
                threads=threads,
            )
            result["solver_backend"] = "highspy_fallback_highs_sparse"
            result["native_solver_error"] = str(exc)
            return result
    if backend == "cuopt":
        if objective_rate_override is not None:
            raise ValueError("objective_rate_override is not supported by the cuOpt backend.")
        from src.optimization.cuopt_adapter import solve_portfolio_cuopt_native

        return solve_portfolio_cuopt_native(
            loans=loans,
            pd_point=pd_point,
            pd_high=pd_high,
            lgd=lgd,
            int_rates=int_rates,
            total_budget=total_budget,
            max_concentration=max_concentration,
            max_portfolio_pd=max_portfolio_pd,
            robust=robust,
            uncertainty_aversion=uncertainty_aversion,
            min_budget_utilization=min_budget_utilization,
            pd_cap_slack_penalty=pd_cap_slack_penalty,
            pd_constraint_override=pd_constraint_override,
            time_limit=time_limit,
            random_seed=random_seed,
            presolve=cuopt_presolve,
            cuopt_parameters=cuopt_parameters,
        )

    if backend not in {"highs_pyomo", "pyomo_highs"}:
        raise ValueError(
            f"Unsupported solver_backend={solver_backend!r}. "
            "Use 'highs', 'highs_sparse', 'highspy', 'highs_pyomo', or 'cuopt'."
        )

    if objective_rate_override is not None:
        raise ValueError("objective_rate_override is not supported by the Pyomo backend.")

    model = build_portfolio_model(
        loans=loans,
        pd_point=pd_point,
        pd_low=pd_low,
        pd_high=pd_high,
        lgd=lgd,
        int_rates=int_rates,
        total_budget=total_budget,
        max_concentration=max_concentration,
        max_portfolio_pd=max_portfolio_pd,
        robust=robust,
        uncertainty_aversion=uncertainty_aversion,
        min_budget_utilization=min_budget_utilization,
        pd_cap_slack_penalty=pd_cap_slack_penalty,
        pd_constraint_override=pd_constraint_override,
    )
    return solve_portfolio(
        model,
        time_limit=time_limit,
        threads=threads,
        solver_backend="highs",
    )


def build_binary_model(
    loans: pd.DataFrame,
    pd_point: np.ndarray,
    pd_high: np.ndarray,
    lgd: np.ndarray,
    int_rates: np.ndarray,
    total_budget: float = 1_000_000,
    max_portfolio_pd: float = 0.10,
) -> Any:
    """Build MILP approve/reject model (binary decisions)."""
    pyo = _require_pyomo()
    n = len(loans)
    model = pyo.ConcreteModel("CreditApprovalMILP")

    model.I = pyo.RangeSet(0, n - 1)
    model.int_rate = pyo.Param(model.I, initialize=dict(enumerate(int_rates)))
    model.pd_point = pyo.Param(model.I, initialize=dict(enumerate(pd_point)))
    model.pd_high = pyo.Param(model.I, initialize=dict(enumerate(pd_high)))
    model.lgd = pyo.Param(model.I, initialize=dict(enumerate(lgd)))
    model.loan_amnt = pyo.Param(model.I, initialize=dict(enumerate(loans["loan_amnt"].values)))
    model.x = pyo.Var(model.I, domain=pyo.Binary)

    def objective_rule(m: Any) -> Any:
        return sum(
            m.x[i] * m.loan_amnt[i] * (m.int_rate[i] - m.pd_point[i] * m.lgd[i]) for i in m.I
        )

    model.obj = pyo.Objective(rule=objective_rule, sense=pyo.maximize)

    def budget_rule(m: Any) -> Any:
        return sum(m.x[i] * m.loan_amnt[i] for i in m.I) <= total_budget

    model.budget = pyo.Constraint(rule=budget_rule)

    def pd_cap_rule(m: Any) -> Any:
        total = sum(m.x[i] * m.loan_amnt[i] for i in m.I) + 1e-6
        weighted = sum(m.x[i] * m.loan_amnt[i] * m.pd_high[i] for i in m.I)
        return weighted <= max_portfolio_pd * total

    model.pd_cap = pyo.Constraint(rule=pd_cap_rule)

    logger.info(f"Built binary approval model: {n} loans")
    return model
