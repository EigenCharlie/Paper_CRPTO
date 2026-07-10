"""Simple, outcome-free selection primitives for the active IJDS policy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product

import numpy as np
import pandas as pd

from src.optimization.policy import PolicyMode

FORBIDDEN_POLICY_SELECTION_COLUMNS = frozenset(
    {
        "default_flag",
        "y_true",
        "outcome",
        "weighted_outcome",
        "weighted_miscoverage",
        "realized_return",
        "realized_risk_tolerance_excess",
    }
)
REQUIRED_POLICY_SELECTION_COLUMNS = frozenset(
    {
        "candidate_id",
        "solver_status",
        "expected_objective",
        "endpoint_budget",
        "weighted_pd_effective",
        "risk_tolerance",
        "total_allocated",
    }
)


@dataclass(frozen=True)
class LinearPolicyCandidate:
    """One linear conformal-guardrail policy."""

    candidate_id: str
    risk_tolerance: float
    gamma: float
    uncertainty_aversion: float
    policy_mode: str = PolicyMode.BLENDED_UNCERTAINTY.value
    delta_cap_quantile: float = 1.0
    tail_focus_quantile: float = 1.0
    min_budget_utilization: float = 0.0
    pd_cap_slack_penalty: float = 0.0

    def to_record(self) -> dict[str, float | str]:
        """Return a JSON/table-friendly record."""
        return asdict(self)


def build_linear_policy_grid(
    *,
    risk_tolerances: list[float],
    gammas: list[float],
    uncertainty_aversions: list[float],
) -> list[LinearPolicyCandidate]:
    """Build a deterministic Cartesian grid of linear policies."""
    return [
        LinearPolicyCandidate(
            candidate_id=f"linear-{index:03d}",
            risk_tolerance=float(tau),
            gamma=float(gamma),
            uncertainty_aversion=float(aversion),
        )
        for index, (tau, gamma, aversion) in enumerate(
            product(risk_tolerances, gammas, uncertainty_aversions),
            start=1,
        )
    ]


def temporal_period_labels(
    issue_dates: pd.Series,
    *,
    combine_years_from: int | None = 2020,
) -> pd.Series:
    """Map issue dates to half-year periods, optionally pooling late years."""
    dates = pd.to_datetime(issue_dates, errors="coerce")
    if dates.isna().any():
        raise ValueError(f"issue_dates contains {int(dates.isna().sum())} invalid values.")
    years = dates.dt.year.astype(int)
    halves = np.where(dates.dt.month.to_numpy() <= 6, "H1", "H2")
    labels = pd.Series(years.astype(str) + halves, index=issue_dates.index, dtype="string")
    if combine_years_from is not None:
        labels.loc[years >= int(combine_years_from)] = f"{int(combine_years_from)}+"
    return labels


def policy_eligibility_mask(
    results: pd.DataFrame,
    *,
    endpoint_budget_cap: float,
    budget: float,
    min_budget_utilization: float = 0.999,
) -> pd.Series:
    """Return the deterministic ex-ante feasibility screen for policy rows."""
    missing = sorted(REQUIRED_POLICY_SELECTION_COLUMNS.difference(results.columns))
    if missing:
        raise ValueError(f"Policy results are missing required columns: {missing}")
    if float(budget) <= 0.0:
        raise ValueError("budget must be positive.")
    if not 0.0 <= float(min_budget_utilization) <= 1.0:
        raise ValueError("min_budget_utilization must lie in [0, 1].")

    solver_ok = results["solver_status"].astype(str).str.strip().str.casefold().eq("optimal")
    budget_ok = pd.to_numeric(results["total_allocated"], errors="raise") >= (
        float(budget) * float(min_budget_utilization)
    )
    endpoint_ok = pd.to_numeric(results["endpoint_budget"], errors="raise") <= (
        float(endpoint_budget_cap) + 1e-12
    )
    cap_ok = pd.to_numeric(results["weighted_pd_effective"], errors="raise") <= (
        pd.to_numeric(results["risk_tolerance"], errors="raise") + 1e-12
    )
    objective_ok = np.isfinite(
        pd.to_numeric(results["expected_objective"], errors="raise").to_numpy(dtype=float)
    )
    return solver_ok & budget_ok & endpoint_ok & cap_ok & objective_ok


def endpoint_cap_stability(
    results: pd.DataFrame,
    *,
    selected_candidate_id: str,
    endpoint_budget_cap: float,
    budget: float,
    min_budget_utilization: float = 0.999,
) -> dict[str, float | str | None]:
    """Return the cap interval over which the selected candidate stays optimal.

    Solver, budget, effective-PD, and finite-objective screens are held fixed.
    Eligibility is monotone in the endpoint cap, so a higher-ranked candidate
    can displace the selected policy only when its endpoint first becomes
    feasible.
    """
    base_feasible = results.loc[
        policy_eligibility_mask(
            results,
            endpoint_budget_cap=float("inf"),
            budget=budget,
            min_budget_utilization=min_budget_utilization,
        )
    ].copy()
    selected_rows = base_feasible.loc[
        base_feasible["candidate_id"].astype(str).eq(str(selected_candidate_id))
    ]
    if len(selected_rows) != 1:
        raise ValueError(
            "selected_candidate_id must identify exactly one base-feasible policy row."
        )
    ranked = base_feasible.sort_values(
        ["expected_objective", "endpoint_budget", "candidate_id"],
        ascending=[False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    selected_position = int(
        ranked.index[ranked["candidate_id"].astype(str).eq(str(selected_candidate_id))][0]
    )
    selected_endpoint = float(selected_rows.iloc[0]["endpoint_budget"])
    superior = ranked.iloc[:selected_position]
    upper_exclusive = (
        float(pd.to_numeric(superior["endpoint_budget"], errors="raise").min())
        if not superior.empty
        else None
    )
    cap = float(endpoint_budget_cap)
    if cap + 1e-12 < selected_endpoint or (
        upper_exclusive is not None and cap + 1e-12 >= upper_exclusive
    ):
        raise ValueError("Selected candidate is not optimal at endpoint_budget_cap.")
    return {
        "selected_candidate_id": str(selected_candidate_id),
        "selected_endpoint_budget": selected_endpoint,
        "cap_lower_inclusive": selected_endpoint,
        "cap_upper_exclusive": upper_exclusive,
        "declared_endpoint_budget_cap": cap,
        "margin_to_lower_boundary": cap - selected_endpoint,
        "margin_to_upper_boundary": (None if upper_exclusive is None else upper_exclusive - cap),
    }


def select_policy_result_ex_ante(
    results: pd.DataFrame,
    *,
    endpoint_budget_cap: float,
    budget: float,
    min_budget_utilization: float = 0.999,
) -> tuple[pd.Series, dict[str, int | float | str]]:
    """Maximize expected objective under outcome-free feasibility screens."""
    forbidden = sorted(FORBIDDEN_POLICY_SELECTION_COLUMNS.intersection(results.columns))
    if forbidden:
        raise ValueError(f"Ex-ante selector received outcome-derived columns: {forbidden}")
    if results.empty:
        raise ValueError("Ex-ante selection results are empty.")
    if results["candidate_id"].astype(str).duplicated().any():
        raise ValueError("Ex-ante selection results contain duplicate candidate_id values.")
    eligible_mask = policy_eligibility_mask(
        results,
        endpoint_budget_cap=endpoint_budget_cap,
        budget=budget,
        min_budget_utilization=min_budget_utilization,
    )
    eligible = results.loc[eligible_mask].copy()
    if eligible.empty:
        raise RuntimeError(
            "No policy satisfies the deterministic endpoint, effective-PD, and budget screens."
        )
    selected = eligible.sort_values(
        ["expected_objective", "endpoint_budget", "candidate_id"],
        ascending=[False, True, True],
        kind="mergesort",
    ).iloc[0]
    audit: dict[str, int | float | str] = {
        "selection_rule": "max_expected_objective_under_deterministic_endpoint_screen",
        "n_total": int(len(results)),
        "n_eligible": int(len(eligible)),
        "selected_candidate_id": str(selected["candidate_id"]),
        "endpoint_budget_cap": float(endpoint_budget_cap),
        "min_budget_utilization": float(min_budget_utilization),
        "outcome_columns_used": 0,
        "statistical_assumption_columns_used": 0,
    }
    return selected, audit
