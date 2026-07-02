"""Native cuOpt adapter for portfolio LP solves.

This bypasses the fragile Pyomo -> cuOpt integration and builds the LP
directly with cuOpt's Python API. The model matches the continuous LP used by
the canonical portfolio optimization path.
"""

from __future__ import annotations

from contextlib import suppress
import importlib
import os
from pathlib import Path
import time
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger
from scipy.sparse import csr_matrix


def _require_cuopt() -> Any:
    try:
        from cuopt import linear_programming as lp_api  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - exercised in RAPIDS env only
        raise RuntimeError(
            "solver_backend='cuopt' requested but native cuOpt Python API is not available."
        ) from exc
    return lp_api


def _extract_primal_solution(solution: Any, n_vars: int) -> np.ndarray:
    values = np.asarray(solution.get_primal_solution(), dtype=float)
    if values.ndim != 1 or len(values) < n_vars:
        raise RuntimeError(
            f"cuOpt primal solution has unexpected shape {values.shape}; expected >= {n_vars}."
        )
    return values


def _normalize_parameter_name(raw: str) -> str:
    name = str(raw).strip().replace("-", "_").lower()
    if name.startswith("cuopt_"):
        name = name[len("cuopt_") :]
    return name


def _coerce_setting_value(raw: Any) -> Any:
    if isinstance(raw, str):
        value = raw.strip()
        if value.lower() in {"true", "false"}:
            return value.lower() == "true"
        if value.lower() in {"none", "null", ""}:
            return None
        with suppress(ValueError):
            return int(value)
        with suppress(ValueError):
            return float(value)
        return value
    return raw


def _resolve_cuopt_setting_value(name: str, value: Any) -> Any:
    """Resolve cuOpt enum-like values when the installed Python API exposes them."""
    if not isinstance(value, str):
        return value
    token = value.strip()
    if not token:
        return value
    enum_specs = {
        "method": (
            "SolverMethod",
            {
                "concurrent": "Concurrent",
                "pdlp": "PDLP",
                "dual simplex": "DualSimplex",
                "dual_simplex": "DualSimplex",
                "dualsimplex": "DualSimplex",
                "barrier": "Barrier",
            },
        ),
        "pdlp_solver_mode": (
            "PDLPSolverMode",
            {
                "stable1": "Stable1",
                "stable2": "Stable2",
                "stable3": "Stable3",
                "methodical1": "Methodical1",
                "fast1": "Fast1",
            },
        ),
    }
    if name not in enum_specs:
        return value
    enum_name, aliases = enum_specs[name]
    try:
        lp_module = importlib.import_module("cuopt.linear_programming")
        enum_cls = getattr(lp_module, enum_name)
        attr = aliases[token.lower().replace("-", "_")]
        return getattr(enum_cls, attr)
    except Exception:
        return value


def _unique_cuopt_log_file(log_dir: str | Path, *, random_seed: int | None) -> str:
    target = Path(log_dir)
    target.mkdir(parents=True, exist_ok=True)
    seed_token = "none" if random_seed is None else str(int(random_seed))
    return str(target / f"cuopt_seed-{seed_token}_pid-{os.getpid()}_{time.time_ns()}.log")


def solve_portfolio_cuopt_native(
    *,
    loans: pd.DataFrame,
    pd_point: np.ndarray,
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
    time_limit: int = 300,
    random_seed: int | None = None,
    presolve: int | None = 1,
    cuopt_parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Solve the portfolio LP natively with cuOpt."""
    lp_api = _require_cuopt()

    n = len(loans)
    if n == 0:
        raise ValueError("Cannot solve empty portfolio.")

    loan_amounts = (
        loans["loan_amnt"].to_numpy(dtype=float)
        if "loan_amnt" in loans.columns
        else np.ones(n, dtype=float) * 10_000.0
    )
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

    use_pd_slack = float(pd_cap_slack_penalty) > 0
    obj = loan_amounts * (rates - point * lgd_arr - uncertainty_aversion * pd_uncertainty * lgd_arr)

    rows: list[np.ndarray] = []
    rhs: list[float] = []
    row_types: list[str] = []

    # Budget cap
    rows.append(loan_amounts.astype(float))
    rhs.append(float(total_budget))
    row_types.append("L")

    # Optional minimum budget utilization
    min_budget_utilization = float(np.clip(min_budget_utilization, 0.0, 1.0))
    if min_budget_utilization > 0:
        rows.append((-loan_amounts).astype(float))
        rhs.append(float(-min_budget_utilization * total_budget))
        row_types.append("L")

    # Portfolio PD cap: sum(x_i * loan_i * (pd_i - max_pd)) - slack <= 0
    pd_row = loan_amounts * (pd_constraint - float(max_portfolio_pd))
    rows.append(pd_row.astype(float))
    rhs.append(0.0)
    row_types.append("L")

    if "purpose" in loans.columns:
        purposes = loans["purpose"].fillna("unknown").astype(str)
        top_purposes = purposes.unique()
        for purpose in top_purposes:
            mask = (purposes == purpose).to_numpy(dtype=float)
            row = loan_amounts * (mask - float(max_concentration))
            rows.append(row.astype(float))
            rhs.append(0.0)
            row_types.append("L")

    A = np.vstack(rows).astype(np.float64)

    var_lb = np.zeros(n + int(use_pd_slack), dtype=np.float64)
    var_ub = np.ones(n + int(use_pd_slack), dtype=np.float64)
    if use_pd_slack:
        slack_col = np.zeros((A.shape[0], 1), dtype=np.float64)
        pd_cap_row_idx = 2 if min_budget_utilization > 0 else 1
        slack_col[pd_cap_row_idx, 0] = -1.0
        A = np.hstack([A, slack_col])
        obj = np.concatenate([obj.astype(np.float64), np.array([-float(pd_cap_slack_penalty)])])
        var_ub[-1] = float(total_budget)
    else:
        obj = obj.astype(np.float64)

    A_csr = csr_matrix(A)
    dm = lp_api.DataModel()
    dm.set_csr_constraint_matrix(
        A_csr.data.astype(np.float64),
        A_csr.indices.astype(np.int32),
        A_csr.indptr.astype(np.int32),
    )
    dm.set_constraint_bounds(np.asarray(rhs, dtype=np.float64))
    dm.set_row_types(np.asarray(row_types))
    dm.set_objective_coefficients(obj)
    dm.set_maximize(True)
    dm.set_variable_lower_bounds(var_lb)
    dm.set_variable_upper_bounds(var_ub)

    settings = lp_api.SolverSettings()
    requested_parameters = {
        _normalize_parameter_name(k): _coerce_setting_value(v)
        for k, v in dict(cuopt_parameters or {}).items()
    }
    log_dir = requested_parameters.pop("log_dir", None)
    if log_dir and not requested_parameters.get("log_file"):
        requested_parameters["log_file"] = _unique_cuopt_log_file(
            str(log_dir), random_seed=random_seed
        )

    applied_parameters: dict[str, Any] = {
        "log_to_console": bool(requested_parameters.pop("log_to_console", False)),
        "time_limit": int(time_limit),
    }
    if random_seed is not None:
        applied_parameters["random_seed"] = int(random_seed)
    if presolve is not None:
        applied_parameters["presolve"] = int(presolve)
    for name, value in requested_parameters.items():
        if value is not None:
            applied_parameters[name] = value
    rejected_parameters: dict[str, str] = {}
    critical_parameters = {
        "time_limit",
        "method",
        "pdlp_solver_mode",
        "pdlp_precision",
        "num_cpu_threads",
        "presolve",
    }
    for name, value in applied_parameters.items():
        try:
            settings.set_parameter(name, _resolve_cuopt_setting_value(name, value))
        except Exception as exc:
            rejected_parameters[name] = str(exc)
            if name in critical_parameters:
                raise

    solution = lp_api.Solve(dm, settings)
    termination_reason = str(solution.get_termination_reason())
    if "Optimal" not in termination_reason and "Feasible" not in termination_reason:
        raise RuntimeError(
            f"cuOpt solve did not produce an acceptable solution: {termination_reason}"
        )

    primal = _extract_primal_solution(solution, n + int(use_pd_slack))
    x = primal[:n]
    pd_cap_slack = float(primal[-1]) if use_pd_slack else 0.0
    allocation = {i: float(x[i]) for i in range(n)}
    total_allocated = float(np.sum(x * loan_amounts))
    n_funded = int(np.sum(x > 0.01))
    obj_value = float(solution.get_primal_objective())

    logger.info(
        "Portfolio solved (cuopt_native): obj={:,.2f}, funded={}/{}, allocated={:,.0f}, pd_cap_slack={:.4f}",
        obj_value,
        n_funded,
        n,
        total_allocated,
        pd_cap_slack,
    )

    return {
        "allocation": allocation,
        "objective_value": obj_value,
        "n_funded": n_funded,
        "total_allocated": total_allocated,
        "solver_status": termination_reason,
        "solver_backend": "cuopt",
        "pd_cap_slack": pd_cap_slack,
        "cuopt_parameters": applied_parameters,
        "cuopt_method": applied_parameters.get("method", "default"),
        "cuopt_pdlp_solver_mode": applied_parameters.get("pdlp_solver_mode", "default"),
        "cuopt_log_file": applied_parameters.get("log_file", ""),
        "cuopt_rejected_parameters": rejected_parameters,
    }
