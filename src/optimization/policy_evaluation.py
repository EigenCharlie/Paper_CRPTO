"""Shared execution contract for portfolio uncertainty policies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.optimization.policy import PolicyMode, policy_segment_labels, resolve_policy_mode
from src.optimization.portfolio_model import (
    compute_effective_pd,
    optimize_portfolio_allocation,
    solution_allocation_vector,
)


@dataclass(frozen=True)
class PolicyAllocationResult:
    """Solver payload, dense allocation, and effective PD for one policy."""

    solution: dict[str, Any]
    allocation: np.ndarray
    effective_pd: np.ndarray
    policy_mode: PolicyMode
    gamma: float
    delta_cap_quantile: float
    tail_focus_quantile: float
    objective_risk_mode: str


def solve_policy_allocation(
    *,
    loans: pd.DataFrame,
    pd_point: np.ndarray,
    pd_low: np.ndarray,
    pd_high: np.ndarray,
    lgd: np.ndarray,
    int_rates: np.ndarray,
    total_budget: float = 1_000_000.0,
    max_concentration: float = 0.25,
    risk_tolerance: float = 0.10,
    robust: bool = True,
    pd_constraint_override: np.ndarray | None = None,
    objective_rate_override: np.ndarray | None = None,
    uncertainty_aversion: float = 0.0,
    min_budget_utilization: float = 0.0,
    pd_cap_slack_penalty: float = 0.0,
    policy_mode: str | PolicyMode = PolicyMode.HARD_WORST_CASE,
    gamma: float = 1.0,
    delta_cap_quantile: float = 1.0,
    tail_focus_quantile: float = 1.0,
    time_limit: int = 300,
    threads: int = 4,
    solver_backend: str = "highs",
) -> PolicyAllocationResult:
    """Resolve policy semantics once and solve the corresponding portfolio.

    ``robust=False`` always means a point-PD constraint, regardless of any
    uncertainty-policy arguments supplied by a legacy caller.
    """
    effective_mode = resolve_policy_mode(policy_mode) if robust else PolicyMode.POINT_ESTIMATE
    effective_gamma = float(gamma) if robust else 0.0
    effective_delta_cap = float(delta_cap_quantile) if robust else 1.0
    effective_tail_focus = float(tail_focus_quantile) if robust else 1.0
    effective_aversion = float(uncertainty_aversion) if robust else 0.0
    if pd_constraint_override is None:
        effective_pd = compute_effective_pd(
            pd_point=pd_point,
            pd_high=pd_high,
            policy_mode=effective_mode,
            gamma=effective_gamma,
            delta_cap_quantile=effective_delta_cap,
            tail_focus_quantile=effective_tail_focus,
            segment_labels=policy_segment_labels(loans, effective_mode),
        )
    else:
        effective_pd = np.asarray(pd_constraint_override, dtype=float)
        if effective_pd.shape != np.asarray(pd_point).shape:
            raise ValueError("pd_constraint_override must align with pd_point.")
        if not bool(np.isfinite(effective_pd).all()):
            raise ValueError("pd_constraint_override must contain finite values.")
    solution = optimize_portfolio_allocation(
        loans=loans,
        pd_point=pd_point,
        pd_low=pd_low,
        pd_high=pd_high,
        lgd=lgd,
        int_rates=int_rates,
        total_budget=total_budget,
        max_concentration=max_concentration,
        max_portfolio_pd=risk_tolerance,
        robust=robust,
        uncertainty_aversion=effective_aversion,
        min_budget_utilization=min_budget_utilization,
        pd_cap_slack_penalty=pd_cap_slack_penalty,
        pd_constraint_override=effective_pd,
        objective_rate_override=objective_rate_override,
        time_limit=time_limit,
        threads=threads,
        solver_backend=solver_backend,
    )
    return PolicyAllocationResult(
        solution=solution,
        allocation=solution_allocation_vector(solution, len(loans)),
        effective_pd=effective_pd,
        policy_mode=effective_mode,
        gamma=effective_gamma,
        delta_cap_quantile=effective_delta_cap,
        tail_focus_quantile=effective_tail_focus,
        objective_risk_mode="point_pd_plus_aversion",
    )
