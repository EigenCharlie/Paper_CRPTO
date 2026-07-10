"""Shared exact-alpha panel loading and policy evaluation for IJDS experiments."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate_alpha_gamma_bound import _load_aligned_dataset  # noqa: E402
from src.models.conformal_alpha_grid import alpha_interval_columns  # noqa: E402
from src.optimization.certificate_semantics import (  # noqa: E402
    compute_funded_certificate_metrics,
)
from src.optimization.input_alignment import align_candidate_intervals  # noqa: E402
from src.optimization.policy_evaluation import (  # noqa: E402
    PolicyAllocationResult,
    solve_policy_allocation,
)
from src.optimization.policy_selection import (  # noqa: E402
    LinearPolicyCandidate,
    temporal_period_labels,
)
from src.utils.script_helpers import parse_percent_series, resolve_repo_artifact_path  # noqa: E402


def load_policy_panel(config: dict[str, Any], *, root: Path = ROOT) -> pd.DataFrame:
    """Load aligned loans and the exact interval columns declared by config."""
    source = config["source"]
    design = config["design"]
    execution = config["execution"]
    interval_path = resolve_repo_artifact_path(source["conformal_intervals_path"], root=root)
    aligned = _load_aligned_dataset(
        conformal_intervals_path=str(interval_path),
        max_candidates=0,
        random_state=int(execution.get("random_seed", 42)),
    )
    exact_grid_value = str(source.get("exact_alpha_grid_path", "")).strip()
    if not exact_grid_value:
        raise ValueError("Active IJDS policy evaluation requires exact_alpha_grid_path.")
    exact_grid_path = resolve_repo_artifact_path(exact_grid_value, root=root)
    exact_alignment = align_candidate_intervals(
        aligned,
        pd.read_parquet(exact_grid_path),
        max_candidates=0,
        random_state=int(execution.get("random_seed", 42)),
    )
    panel = exact_alignment.candidates.copy()
    exact = exact_alignment.intervals
    low_column, high_column = alpha_interval_columns(float(design["alpha"]))
    required = {"y_pred", low_column, high_column}
    missing = sorted(required.difference(exact.columns))
    if missing:
        raise KeyError(f"Exact alpha grid is missing columns: {missing}")

    panel["_pd_point"] = exact["y_pred"].to_numpy(dtype=float)
    panel["_pd_low"] = exact[low_column].to_numpy(dtype=float)
    panel["_pd_high"] = exact[high_column].to_numpy(dtype=float)
    panel["_outcome"] = pd.to_numeric(panel["y_true"], errors="raise").astype(float)
    panel["_loan_amount"] = pd.to_numeric(panel["loan_amnt"], errors="coerce").fillna(1.0)
    panel["_int_rate"] = parse_percent_series(panel["int_rate"])
    panel["_period"] = temporal_period_labels(
        panel["issue_d"],
        combine_years_from=int(design["combine_years_from"]),
    )
    panel.attrs["exact_alpha_grid_path"] = str(exact_grid_path)
    return panel


def solve_candidate(
    frame: pd.DataFrame,
    candidate: LinearPolicyCandidate,
    *,
    config: dict[str, Any],
    robust: bool = True,
) -> PolicyAllocationResult:
    """Solve one declared policy on one aligned panel."""
    design = config["design"]
    execution = config["execution"]
    return solve_policy_allocation(
        loans=frame,
        pd_point=frame["_pd_point"].to_numpy(dtype=float),
        pd_low=frame["_pd_low"].to_numpy(dtype=float),
        pd_high=frame["_pd_high"].to_numpy(dtype=float),
        lgd=np.full(len(frame), float(design["lgd"]), dtype=float),
        int_rates=frame["_int_rate"].to_numpy(dtype=float),
        total_budget=float(design["budget"]),
        max_concentration=float(design["max_concentration"]),
        risk_tolerance=float(candidate.risk_tolerance),
        robust=robust,
        uncertainty_aversion=float(candidate.uncertainty_aversion) if robust else 0.0,
        min_budget_utilization=float(candidate.min_budget_utilization),
        pd_cap_slack_penalty=float(candidate.pd_cap_slack_penalty),
        policy_mode=candidate.policy_mode,
        gamma=float(candidate.gamma),
        delta_cap_quantile=float(candidate.delta_cap_quantile),
        tail_focus_quantile=float(candidate.tail_focus_quantile),
        time_limit=int(execution["time_limit"]),
        threads=int(execution["threads"]),
        solver_backend=str(execution["solver_backend"]),
        random_seed=int(execution.get("random_seed", 42)),
    )


def evaluate_candidate(
    frame: pd.DataFrame,
    candidate: LinearPolicyCandidate,
    *,
    config: dict[str, Any],
    robust: bool,
    period: str,
) -> tuple[dict[str, Any], PolicyAllocationResult]:
    """Solve and score one policy on one evaluation period."""
    result = solve_candidate(frame, candidate, config=config, robust=robust)
    exposure = result.allocation * frame["_loan_amount"].to_numpy(dtype=float)
    total_allocated = float(exposure.sum())
    if total_allocated <= 0.0:
        raise RuntimeError(f"Policy {candidate.candidate_id} allocated no capital in {period}.")
    weights = exposure / total_allocated
    outcomes = frame["_outcome"].to_numpy(dtype=float)
    alpha = float(config["design"]["alpha"])
    certificate = compute_funded_certificate_metrics(
        weights,
        outcomes=outcomes,
        pd_point=frame["_pd_point"].to_numpy(dtype=float),
        pd_high=frame["_pd_high"].to_numpy(dtype=float),
        pd_effective=result.effective_pd,
        alpha=alpha,
        risk_tolerance=float(candidate.risk_tolerance),
        pd_cap_slack=float(result.solution.get("pd_cap_slack", 0.0)),
    )
    funded = result.allocation > 0.01
    rates = frame["_int_rate"].to_numpy(dtype=float)
    lgd = float(config["design"]["lgd"])
    realized_return = float(
        np.sum(
            np.where(
                funded & (outcomes.astype(int) == 1),
                -lgd * exposure,
                np.where(funded, rates * exposure, 0.0),
            )
        )
    )
    record: dict[str, Any] = {
        "period": period,
        **candidate.to_record(),
        "solver_status": str(result.solution.get("solver_status", "unknown")),
        "objective_risk_mode": result.objective_risk_mode,
        "expected_objective": float(result.solution.get("objective_value", float("nan"))),
        "n_panel": int(len(frame)),
        "n_funded": int(certificate.n_funded),
        "total_allocated": total_allocated,
        "realized_return": realized_return,
        "weighted_outcome": certificate.weighted_outcome,
        "weighted_miscoverage": certificate.weighted_miscoverage,
        "weighted_pd_point": certificate.weighted_pd_point,
        "weighted_pd_effective": certificate.weighted_pd_effective,
        "gamma_cp": certificate.gamma_cp,
        "gamma_internalized": certificate.gamma_internalized,
        "gamma_residual": certificate.gamma_residual,
        "endpoint_budget": certificate.endpoint_budget,
        "markov_loss_threshold": certificate.markov_loss_threshold,
        "realized_risk_tolerance_excess": certificate.realized_risk_tolerance_excess,
        "screen_V_leq_sqrt_alpha": bool(
            certificate.weighted_miscoverage <= certificate.sqrt_alpha + 1e-12
        ),
        "screen_risk_excess_leq_alpha": bool(
            certificate.realized_risk_tolerance_excess <= alpha + 1e-12
        ),
    }
    return record, result
