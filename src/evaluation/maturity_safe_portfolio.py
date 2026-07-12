"""Outcome-isolated portfolio decisions and bounded retrospective evaluation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.evaluation.coverage_transport import binary_miscoverage_bounds
from src.evaluation.standardized_credit_payoff import (
    PAYOFF_ID,
    contractual_rate_decimal,
    expected_objective_coefficients,
    realized_standardized_payoff_bounds,
)
from src.models.maturity_safe_pd import OUTCOME_COLUMNS
from src.optimization.policy_evaluation import PolicyAllocationResult, solve_policy_allocation
from src.optimization.policy_selection import LinearPolicyCandidate


@dataclass(frozen=True)
class SolveResult:
    """A solved portfolio plus independently reconciled payoff quantities."""

    result: PolicyAllocationResult
    exposure: np.ndarray
    expected_payoff_rate: np.ndarray
    expected_objective: float


@dataclass(frozen=True)
class MonthlyPolicySpec:
    """One frozen policy evaluated under a stable publication label."""

    candidate: LinearPolicyCandidate
    robust: bool
    label: str


def assert_outcome_free_decision_frame(frame: pd.DataFrame) -> None:
    """Fail if a decision frame contains an outcome or outcome-derived field."""
    normalized = {str(column).casefold() for column in frame.columns}
    forbidden = sorted(OUTCOME_COLUMNS.intersection(normalized))
    pattern_forbidden = sorted(
        column
        for column in normalized
        if any(token in column for token in ("realized", "miscoverage", "outcome"))
    )
    violations = sorted(set(forbidden + pattern_forbidden))
    if violations:
        raise ValueError(f"Decision frame contains outcome-derived columns: {violations}")


def build_decision_panel(
    frame: pd.DataFrame,
    *,
    pd_point: np.ndarray,
    conformal_lower: np.ndarray,
    conformal_upper: np.ndarray,
    conformal_groups: np.ndarray,
) -> pd.DataFrame:
    """Build the only dataframe supplied to policy solving."""
    n_rows = len(frame)
    arrays = [pd_point, conformal_lower, conformal_upper, conformal_groups]
    if any(len(values) != n_rows for values in arrays):
        raise ValueError("Decision-panel prediction arrays must align with candidates.")
    loan_amount = pd.to_numeric(frame["loan_amnt"], errors="coerce").to_numpy(dtype=float)
    if not bool(np.isfinite(loan_amount).all()) or bool(np.any(loan_amount <= 0.0)):
        raise ValueError("Decision candidates require positive finite loan_amnt.")
    panel = pd.DataFrame(
        {
            "id": frame["id"].astype("string").to_numpy(),
            "issue_d": pd.to_datetime(frame["issue_d"]).to_numpy(),
            "loan_amnt": loan_amount,
            "purpose": frame["purpose"].astype("string").fillna("unknown").to_numpy(),
            "contractual_rate": contractual_rate_decimal(frame["int_rate"]),
            "pd_point": np.asarray(pd_point, dtype=float),
            "conformal_lower": np.asarray(conformal_lower, dtype=float),
            "conformal_upper": np.asarray(conformal_upper, dtype=float),
            "conformal_group": np.asarray(conformal_groups, dtype=int),
        }
    )
    probability_columns = ["pd_point", "conformal_lower", "conformal_upper"]
    probability_values = panel[probability_columns].to_numpy(dtype=float)
    if not bool(np.isfinite(probability_values).all()):
        raise ValueError("Decision panel contains non-finite probability values.")
    if bool(np.any((probability_values < 0.0) | (probability_values > 1.0))):
        raise ValueError("Decision scores must lie in [0, 1].")
    if bool(np.any(panel["conformal_lower"] > panel["pd_point"] + 1e-12)) or bool(
        np.any(panel["pd_point"] > panel["conformal_upper"] + 1e-12)
    ):
        raise ValueError("Binary-outcome conformal intervals must contain the point score.")
    assert_outcome_free_decision_frame(panel)
    return panel


def build_outcome_panel(frame: pd.DataFrame) -> pd.DataFrame:
    """Build the ID-keyed snapshot outcomes kept outside decisions."""
    return pd.DataFrame(
        {
            "id": frame["id"].astype("string").to_numpy(),
            "loan_status": frame["loan_status"].astype("string").to_numpy(),
            "snapshot_default": frame["snapshot_default"].astype("Int8").to_numpy(),
            "snapshot_resolution": frame["snapshot_resolution"].astype("string").to_numpy(),
        }
    )


def solve_coherent_policy(
    frame: pd.DataFrame,
    candidate: LinearPolicyCandidate,
    *,
    config: Mapping[str, Any],
    robust: bool,
    effective_score_override: np.ndarray | None = None,
) -> SolveResult:
    """Optimize and independently reconcile ``(1-p)r-pLGD``."""
    assert_outcome_free_decision_frame(frame)
    payoff = config["payoff"]
    policy = config["policy"]
    execution = config["execution"]
    point = frame["pd_point"].to_numpy(dtype=float)
    rates = frame["contractual_rate"].to_numpy(dtype=float)
    lgd_value = float(payoff["lgd"])
    objective_coefficients = expected_objective_coefficients(point, rates, lgd=lgd_value)
    requested_backend = str(execution["solver_backend"])
    result = solve_policy_allocation(
        loans=frame,
        pd_point=point,
        pd_low=frame["conformal_lower"].to_numpy(dtype=float),
        pd_high=frame["conformal_upper"].to_numpy(dtype=float),
        lgd=np.full(len(frame), lgd_value, dtype=float),
        int_rates=rates,
        objective_rate_override=objective_coefficients,
        total_budget=float(policy["budget"]),
        max_concentration=float(policy["max_concentration_by_purpose"]),
        risk_tolerance=float(candidate.risk_tolerance),
        robust=bool(robust),
        pd_constraint_override=effective_score_override,
        uncertainty_aversion=0.0,
        min_budget_utilization=float(policy["min_budget_utilization_solver"]),
        pd_cap_slack_penalty=0.0,
        policy_mode=candidate.policy_mode,
        gamma=float(candidate.gamma),
        delta_cap_quantile=float(candidate.delta_cap_quantile),
        tail_focus_quantile=float(candidate.tail_focus_quantile),
        time_limit=int(execution["solver_time_limit_seconds"]),
        threads=int(execution["threads"]),
        solver_backend=requested_backend,
        random_seed=int(execution["random_seed"]),
    )
    _require_requested_solver_backend(
        requested=requested_backend,
        actual=str(result.solution.get("solver_backend", "unknown")),
        strict=bool(execution.get("strict_solver_backend", False)),
    )
    exposure = result.allocation * frame["loan_amnt"].to_numpy(dtype=float)
    payoff_rate = objective_coefficients
    reconciled = float(exposure @ payoff_rate)
    solver_objective = float(result.solution.get("objective_value", np.nan))
    if not np.isfinite(solver_objective) or not np.isclose(
        solver_objective,
        reconciled,
        rtol=0.0,
        atol=1e-5,
    ):
        raise RuntimeError(
            "Solver objective does not reconcile to coherent payoff: "
            f"solver={solver_objective}, independent={reconciled}."
        )
    return SolveResult(
        result=result,
        exposure=exposure,
        expected_payoff_rate=payoff_rate,
        expected_objective=reconciled,
    )


def _require_requested_solver_backend(*, requested: str, actual: str, strict: bool) -> None:
    if not strict:
        return
    requested_normalized = requested.strip().casefold()
    actual_normalized = actual.strip().casefold()
    canonical_actual = {
        "highs": "highs_sparse",
        "scipy_highs": "highs_sparse",
        "highs_sparse": "highs_sparse",
        "highspy": "highspy",
        "highs_native": "highspy",
        "native_highs": "highspy",
        "highs_pyomo": "highs",
        "pyomo_highs": "highs",
        "cuopt": "cuopt",
    }.get(requested_normalized, requested_normalized)
    if actual_normalized != canonical_actual:
        raise RuntimeError(
            f"Strict solver backend mismatch: requested={requested!r}, actual={actual!r}."
        )


def outcome_free_solve_record(
    frame: pd.DataFrame,
    candidate: LinearPolicyCandidate,
    solved: SolveResult,
    *,
    allocation_tolerance: float,
) -> dict[str, Any]:
    """Summarize one solve using decision-time quantities only."""
    total = float(solved.exposure.sum())
    if total <= 0.0:
        raise RuntimeError(f"Policy {candidate.candidate_id} allocated no capital.")
    weights = solved.exposure / total
    active = solved.exposure > float(allocation_tolerance)
    return {
        **candidate.to_record(),
        "payoff_id": PAYOFF_ID,
        "solver_status": str(solved.result.solution.get("solver_status", "unknown")),
        "solver_backend_actual": str(solved.result.solution.get("solver_backend", "unknown")),
        "expected_objective": solved.expected_objective,
        "n_candidates": int(len(frame)),
        "n_positive_exposure": int(active.sum()),
        "total_allocated": total,
        "weighted_pd_point": float(weights @ frame["pd_point"].to_numpy(dtype=float)),
        "weighted_pd_effective": float(weights @ solved.result.effective_pd),
        "weighted_conformal_upper": float(weights @ frame["conformal_upper"].to_numpy(dtype=float)),
        "highs_simplex_iterations": int(
            solved.result.solution.get("highs_simplex_iterations", 0) or 0
        ),
        "highs_ipm_iterations": int(solved.result.solution.get("highs_ipm_iterations", 0) or 0),
    }


def solve_outcome_free_allocation(
    decision_frame: pd.DataFrame,
    candidate: LinearPolicyCandidate,
    *,
    config: Mapping[str, Any],
    robust: bool,
    role: str,
    period: str,
    policy_label: str,
    effective_score_override: np.ndarray | None = None,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Solve and materialize an allocation before any outcome join."""
    assert_outcome_free_decision_frame(decision_frame)
    solved = solve_coherent_policy(
        decision_frame,
        candidate,
        config=config,
        robust=robust,
        effective_score_override=effective_score_override,
    )
    tolerance = float(config["execution"]["allocation_tolerance"])
    record = outcome_free_solve_record(
        decision_frame,
        candidate,
        solved,
        allocation_tolerance=tolerance,
    )
    active = solved.exposure > tolerance
    allocation = decision_frame.loc[active].copy()
    allocation["allocation_fraction"] = solved.result.allocation[active]
    allocation["exposure"] = solved.exposure[active]
    total = float(allocation["exposure"].sum())
    allocation["weight"] = allocation["exposure"] / total
    allocation["pd_effective"] = solved.result.effective_pd[active]
    allocation["expected_payoff_rate"] = solved.expected_payoff_rate[active]
    allocation["expected_payoff_contribution"] = (
        allocation["exposure"] * allocation["expected_payoff_rate"]
    )
    allocation["role"] = role
    allocation["period"] = period
    allocation["policy_label"] = policy_label
    allocation["candidate_id"] = candidate.candidate_id
    return {
        **record,
        "role": role,
        "period": period,
        "policy_label": policy_label,
        "robust_guardrail": bool(robust),
    }, allocation


def evaluation_record_and_allocations(
    decision_frame: pd.DataFrame,
    outcomes: pd.DataFrame,
    candidate: LinearPolicyCandidate,
    *,
    config: Mapping[str, Any],
    robust: bool,
    role: str,
    period: str,
    policy_label: str,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Solve outcome-free, then join outcomes for bounded evaluation."""
    base_record, allocation = solve_outcome_free_allocation(
        decision_frame,
        candidate,
        config=config,
        robust=robust,
        role=role,
        period=period,
        policy_label=policy_label,
    )
    return evaluate_frozen_allocation(base_record, allocation, outcomes, config=config)


def evaluate_frozen_allocation(
    base_record: Mapping[str, Any],
    allocation: pd.DataFrame,
    outcomes: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Join outcomes to an already frozen allocation and compute sharp bounds."""
    assert_outcome_free_decision_frame(
        allocation.drop(
            columns=[
                "allocation_fraction",
                "exposure",
                "weight",
                "pd_effective",
                "expected_payoff_rate",
                "expected_payoff_contribution",
                "role",
                "period",
                "policy_label",
                "candidate_id",
            ],
            errors="ignore",
        )
    )
    joined = allocation.merge(outcomes, on="id", how="left", validate="one_to_one")
    return evaluate_prejoined_frozen_allocation(
        base_record,
        joined,
        config=config,
        n_unresolved_candidates=int(outcomes["snapshot_default"].isna().sum()),
    )


def evaluate_prejoined_frozen_allocation(
    base_record: Mapping[str, Any],
    joined_allocation: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    n_unresolved_candidates: int,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Evaluate one frozen allocation after a validated shared outcome join."""
    joined = joined_allocation.copy()
    if bool(joined["id"].duplicated().any()):
        raise RuntimeError("A frozen policy allocation contains duplicate loan IDs.")
    if bool(joined["snapshot_resolution"].isna().any()):
        raise RuntimeError("Funded allocation could not be aligned to snapshot outcomes.")
    y_true = pd.to_numeric(joined["snapshot_default"], errors="coerce").to_numpy(dtype=float)
    payoff_low, payoff_high = realized_standardized_payoff_bounds(
        y_true,
        joined["contractual_rate"].to_numpy(dtype=float),
        lgd=float(config["payoff"]["lgd"]),
    )
    miss_low, miss_high = binary_miscoverage_bounds(
        y_true,
        joined["conformal_lower"].to_numpy(dtype=float),
        joined["conformal_upper"].to_numpy(dtype=float),
    )
    joined["realized_payoff_rate_lower"] = payoff_low
    joined["realized_payoff_rate_upper"] = payoff_high
    joined["realized_payoff_lower"] = joined["exposure"] * payoff_low
    joined["realized_payoff_upper"] = joined["exposure"] * payoff_high
    joined["miscoverage_lower"] = miss_low
    joined["miscoverage_upper"] = miss_high
    weights = joined["weight"].to_numpy(dtype=float)
    unresolved = ~np.isfinite(y_true)
    default_lower = np.nan_to_num(y_true, nan=0.0)
    default_upper = np.where(unresolved, 1.0, y_true)
    realized_lower = float(joined["realized_payoff_lower"].sum())
    realized_upper = float(joined["realized_payoff_upper"].sum())
    role = str(base_record["role"])
    period = str(base_record["period"])
    policy_label = str(base_record["policy_label"])
    robust = bool(base_record["robust_guardrail"])
    record = {
        **base_record,
        "role": role,
        "period": period,
        "policy_label": policy_label,
        "robust_guardrail": bool(robust),
        "n_unresolved_candidates": int(n_unresolved_candidates),
        "n_unresolved_positive_exposure": int(unresolved.sum()),
        "unresolved_exposure_share": float(weights @ unresolved.astype(float)),
        "realized_payoff_lower": realized_lower,
        "realized_payoff_upper": realized_upper,
        "realized_payoff_exact": (
            realized_lower if np.isclose(realized_lower, realized_upper, atol=1e-12) else None
        ),
        "weighted_default_lower": float(weights @ default_lower),
        "weighted_default_upper": float(weights @ default_upper),
        "weighted_miscoverage_lower": float(weights @ miss_low),
        "weighted_miscoverage_upper": float(weights @ miss_high),
        "full_budget": bool(
            np.isclose(
                float(base_record["total_allocated"]),
                float(config["policy"]["budget"]),
                rtol=0.0,
                atol=1e-4,
            )
        ),
    }
    return record, joined


def aggregate_monthly_evaluation(frame: pd.DataFrame) -> dict[str, Any]:
    """Aggregate fixed-policy months using allocated capital as weights."""
    if frame.empty:
        raise ValueError("Monthly evaluation frame is empty.")
    budget = pd.to_numeric(frame["total_allocated"], errors="raise").to_numpy(dtype=float)
    total_budget = float(budget.sum())
    if total_budget <= 0.0:
        raise ValueError("Monthly evaluation has no allocated budget.")
    month_weights = budget / total_budget
    weighted_columns = [
        "weighted_pd_point",
        "weighted_pd_effective",
        "weighted_conformal_upper",
        "weighted_default_lower",
        "weighted_default_upper",
        "weighted_miscoverage_lower",
        "weighted_miscoverage_upper",
        "unresolved_exposure_share",
    ]
    result: dict[str, Any] = {
        "policy_label": str(frame["policy_label"].iloc[0]),
        "months": int(len(frame)),
        "total_budget": total_budget,
        "expected_objective": float(frame["expected_objective"].sum()),
        "realized_payoff_lower": float(frame["realized_payoff_lower"].sum()),
        "realized_payoff_upper": float(frame["realized_payoff_upper"].sum()),
        "unresolved_candidates": int(frame["n_unresolved_candidates"].sum()),
        "unresolved_positive_exposure": int(frame["n_unresolved_positive_exposure"].sum()),
    }
    for column in weighted_columns:
        values = pd.to_numeric(frame[column], errors="raise").to_numpy(dtype=float)
        result[column] = float(month_weights @ values)
    return result


def evaluate_policy_specs_by_month(
    decision_frame: pd.DataFrame,
    outcomes: pd.DataFrame,
    specs: Sequence[MonthlyPolicySpec],
    *,
    config: Mapping[str, Any],
    role: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate frozen policy specs on each issue-month menu in stable order."""
    assert_outcome_free_decision_frame(decision_frame)
    if not specs:
        raise ValueError("At least one monthly policy spec is required.")
    labels = [spec.label for spec in specs]
    if len(labels) != len(set(labels)):
        raise ValueError("Monthly policy labels must be unique.")

    periods = sorted(pd.to_datetime(decision_frame["issue_d"]).dt.to_period("M").unique())
    records: list[dict[str, Any]] = []
    allocations: list[pd.DataFrame] = []
    for period_value in periods:
        period = str(period_value)
        month_mask = pd.to_datetime(decision_frame["issue_d"]).dt.to_period("M").eq(period_value)
        month = decision_frame.loc[month_mask].copy()
        month_outcomes = outcomes.loc[outcomes["id"].isin(month["id"])].copy()
        for spec in specs:
            record, funded = evaluation_record_and_allocations(
                month,
                month_outcomes,
                spec.candidate,
                config=config,
                robust=spec.robust,
                role=role,
                period=period,
                policy_label=spec.label,
            )
            records.append(record)
            allocations.append(funded)

    evaluation = pd.DataFrame(records)
    funded = pd.concat(allocations, ignore_index=True)
    expected_rows = len(periods) * len(specs)
    if len(evaluation) != expected_rows:
        raise RuntimeError(
            f"Monthly evaluation produced {len(evaluation)} rows; expected {expected_rows}."
        )
    return evaluation, funded


def select_policy_on_development(
    decision_frame: pd.DataFrame,
    outcomes: pd.DataFrame,
    candidates: Sequence[tuple[LinearPolicyCandidate, bool, str]],
    *,
    config: Mapping[str, Any],
) -> tuple[LinearPolicyCandidate, pd.DataFrame, pd.DataFrame]:
    """Select once on labeled development months by realized coherent payoff."""
    assert_outcome_free_decision_frame(decision_frame)
    periods = sorted(pd.to_datetime(decision_frame["issue_d"]).dt.to_period("M").unique())
    monthly_records: list[dict[str, Any]] = []
    for candidate, robust, label in candidates:
        for period_value in periods:
            period = str(period_value)
            month_mask = (
                pd.to_datetime(decision_frame["issue_d"]).dt.to_period("M").eq(period_value)
            )
            month = decision_frame.loc[month_mask].copy()
            month_outcomes = outcomes.loc[outcomes["id"].isin(month["id"])].copy()
            record, _ = evaluation_record_and_allocations(
                month,
                month_outcomes,
                candidate,
                config=config,
                robust=robust,
                role="policy_development",
                period=period,
                policy_label=label,
            )
            if record["realized_payoff_exact"] is None:
                raise RuntimeError("Policy development contains unresolved outcomes.")
            monthly_records.append(record)
    monthly = pd.DataFrame(monthly_records)
    grid = (
        monthly.groupby(["candidate_id", "policy_label"], observed=True, as_index=False)
        .agg(
            months=("period", "size"),
            full_budget_months=("full_budget", "sum"),
            total_allocated=("total_allocated", "sum"),
            expected_objective=("expected_objective", "sum"),
            realized_payoff=("realized_payoff_exact", "sum"),
            weighted_default=("weighted_default_lower", "mean"),
            weighted_miscoverage=("weighted_miscoverage_lower", "mean"),
        )
        .sort_values(
            ["realized_payoff", "expected_objective", "candidate_id"],
            ascending=[False, False, True],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )
    expected_months = len(periods)
    eligible = grid.loc[grid["full_budget_months"].eq(expected_months)]
    if eligible.empty:
        raise RuntimeError("No development policy used the full budget in every month.")
    selected_id = str(eligible.iloc[0]["candidate_id"])
    selected = next(
        candidate for candidate, _, _ in candidates if candidate.candidate_id == selected_id
    )
    return selected, grid, monthly
