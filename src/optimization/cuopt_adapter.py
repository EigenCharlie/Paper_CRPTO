"""Native cuOpt adapter for portfolio LP solves.

This bypasses the fragile Pyomo -> cuOpt integration and builds the LP
directly with cuOpt's Python API. The model matches the continuous LP used by
the canonical portfolio optimization path.
"""

from __future__ import annotations

import importlib
import os
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from src.optimization.portfolio_model import _portfolio_lp_components, _PortfolioLpComponents


def _require_cuopt() -> Any:
    try:
        return importlib.import_module("cuopt").linear_programming
    except Exception as exc:  # pragma: no cover - exercised in RAPIDS env only
        raise RuntimeError(
            "solver_backend='cuopt' requested but native cuOpt Python API is not available."
        ) from exc


def _extract_primal_solution(solution: Any, n_vars: int) -> np.ndarray:
    values = np.asarray(solution.get_primal_solution(), dtype=float)
    if values.ndim != 1 or len(values) < n_vars:
        raise RuntimeError(
            f"cuOpt primal solution has unexpected shape {values.shape}; expected >= {n_vars}."
        )
    return values


def _normalize_parameter_name(raw: str) -> str:
    name = str(raw).strip().replace("-", "_").lower()
    name = name.removeprefix("cuopt_")
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


def _cuopt_data_model(lp_api: Any, components: _PortfolioLpComponents) -> Any:
    matrix = components.a_ub.tocsr()
    dm = lp_api.DataModel()
    dm.set_csr_constraint_matrix(
        matrix.data.astype(np.float64),
        matrix.indices.astype(np.int32),
        matrix.indptr.astype(np.int32),
    )
    dm.set_constraint_bounds(components.rhs.astype(np.float64))
    dm.set_row_types(np.asarray(["L"] * len(components.rhs)))
    dm.set_objective_coefficients(components.objective_coefficients.astype(np.float64))
    dm.set_maximize(True)

    bounds = np.asarray(components.bounds, dtype=np.float64)
    dm.set_variable_lower_bounds(bounds[:, 0])
    dm.set_variable_upper_bounds(bounds[:, 1])
    return dm


def _cuopt_solver_settings(
    lp_api: Any,
    *,
    time_limit: int,
    random_seed: int | None,
    presolve: int | None,
    cuopt_parameters: dict[str, Any] | None,
) -> tuple[Any, dict[str, Any], dict[str, str]]:
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
    return settings, applied_parameters, rejected_parameters


def _cuopt_result_payload(
    *,
    solution: Any,
    primal: np.ndarray,
    components: _PortfolioLpComponents,
    termination_reason: str,
    applied_parameters: dict[str, Any],
    rejected_parameters: dict[str, str],
) -> dict[str, Any]:
    x = np.clip(primal[: components.n], 0.0, 1.0)
    pd_cap_slack = float(primal[-1]) if components.use_pd_slack else 0.0
    allocation = {i: float(x[i]) for i in range(components.n)}
    allocation_vector = x.astype(float)
    total_allocated = float(np.sum(x * components.loan_amounts))
    n_funded = int(np.sum(x > 0.01))
    obj_value = float(solution.get_primal_objective())

    logger.info(
        "Portfolio solved (cuopt_native): obj={:,.2f}, funded={}/{}, allocated={:,.0f}, pd_cap_slack={:.4f}",
        obj_value,
        n_funded,
        components.n,
        total_allocated,
        pd_cap_slack,
    )

    return {
        "allocation": allocation,
        "allocation_vector": allocation_vector,
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
        objective_rate_override=None,
    )
    dm = _cuopt_data_model(lp_api, components)
    settings, applied_parameters, rejected_parameters = _cuopt_solver_settings(
        lp_api,
        time_limit=time_limit,
        random_seed=random_seed,
        presolve=presolve,
        cuopt_parameters=cuopt_parameters,
    )

    solution = lp_api.Solve(dm, settings)
    termination_reason = str(solution.get_termination_reason())
    if "Optimal" not in termination_reason and "Feasible" not in termination_reason:
        raise RuntimeError(
            f"cuOpt solve did not produce an acceptable solution: {termination_reason}"
        )

    primal = _extract_primal_solution(solution, components.n + int(components.use_pd_slack))
    return _cuopt_result_payload(
        solution=solution,
        primal=primal,
        components=components,
        termination_reason=termination_reason,
        applied_parameters=applied_parameters,
        rejected_parameters=rejected_parameters,
    )
