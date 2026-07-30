"""Exact shared-completion bounds for a frozen monthly decision catalog.

This module is deliberately outcome-evaluation only.  It never fits a model,
recomputes conformal sets, solves a portfolio, or selects a policy.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import product
from typing import Any

import numpy as np
import pandas as pd

METRICS = ("payoff_shortfall", "default_gap", "miscoverage_excess")
RESOLVED_ENDPOINTS = {
    "fully_paid_by_reconstructed_cutoff": 0.0,
    "charged_off_by_reconstructed_cutoff": 1.0,
}
UNRESOLVED_ENDPOINTS = {
    "terminal_availability_date_missing",
    "nonterminal_or_unresolved_status",
}
POLICY_KEY = (
    "role",
    "period",
    "window_id",
    "frontier_ruler",
    "frontier_coordinate",
    "gamma",
)
ALLOCATION_KEY = (*POLICY_KEY, "id")

REQUIRED_DECISION_COLUMNS = frozenset(
    {
        *ALLOCATION_KEY,
        "candidate_id",
        "policy_label",
        "pd_point",
        "contractual_rate",
        "conformal_lower",
        "conformal_upper",
        "exposure",
        "expected_payoff_rate",
        "expected_payoff_contribution",
    }
)
FORBIDDEN_DECISION_COLUMNS = frozenset(
    {
        "default_flag",
        "loan_status",
        "outcome",
        "realized_payoff",
        "snapshot_default",
        "snapshot_resolution",
        "terminal_default",
        "total_pymnt",
        "weighted_default",
        "weighted_miscoverage",
        "y_true",
    }
)


@dataclass(frozen=True)
class DecisionCatalogSpec:
    """Complete catalog, temporal split, and numerical contract."""

    budget: float
    budget_tolerance: float
    lgd: float
    nominal_miscoverage: float
    alpha: float
    numeric_tolerance: float
    payoff_contribution_tolerance: float
    calibration_role: str
    target_role: str
    calibration_periods: tuple[str, ...]
    target_periods: tuple[str, ...]
    window_ids: tuple[str, ...]
    rulers: tuple[str, ...]
    coordinates: tuple[float, ...]
    gamma_grid: tuple[float, ...]
    expected_rank: int
    expected_policies_per_block: int
    expected_policy_rows: int
    expected_allocation_rows: int
    expected_set_type_counts: Mapping[str, int]


@dataclass(frozen=True)
class CatalogAudit:
    """Outcome-free catalog validation result."""

    set_types: np.ndarray
    summary: dict[str, Any]


@dataclass(frozen=True)
class DecisionCatalogTransportResult:
    """All deterministic tables and their compact scientific summary."""

    policy_score_bounds: pd.DataFrame
    block_score_bounds: pd.DataFrame
    calibration_thresholds: pd.DataFrame
    target_classification: pd.DataFrame
    summary: dict[str, Any]


def spec_from_config(design: Mapping[str, Any]) -> DecisionCatalogSpec:
    """Construct a typed contract from the locked YAML design section."""
    return DecisionCatalogSpec(
        budget=float(design["budget_dollars"]),
        budget_tolerance=float(design["budget_tolerance_dollars"]),
        lgd=float(design["lgd"]),
        nominal_miscoverage=float(design["nominal_miscoverage"]),
        alpha=float(design["alpha"]),
        numeric_tolerance=float(design["numeric_tolerance"]),
        payoff_contribution_tolerance=float(design["payoff_contribution_tolerance_dollars"]),
        calibration_role=str(design["calibration_role"]),
        target_role=str(design["target_role"]),
        calibration_periods=tuple(str(value) for value in design["calibration_periods"]),
        target_periods=tuple(str(value) for value in design["target_periods"]),
        window_ids=tuple(str(value) for value in design["window_ids"]),
        rulers=tuple(str(value) for value in design["rulers"]),
        coordinates=tuple(float(value) for value in design["coordinates"]),
        gamma_grid=tuple(float(value) for value in design["gamma_grid"]),
        expected_rank=int(design["expected_rank"]),
        expected_policies_per_block=int(design["expected_policies_per_block"]),
        expected_policy_rows=int(design["expected_policy_rows"]),
        expected_allocation_rows=int(design["expected_allocation_rows"]),
        expected_set_type_counts={
            str(key): int(value) for key, value in design["expected_set_type_counts"].items()
        },
    )


def _require_unique_nonempty(values: Sequence[Any], *, label: str) -> tuple[Any, ...]:
    domain = tuple(values)
    if not domain or len(set(domain)) != len(domain):
        raise ValueError(f"{label} must be nonempty and duplicate-free.")
    if any(isinstance(value, str) and not value for value in domain):
        raise ValueError(f"{label} contains an empty identity.")
    return domain


def validate_spec(spec: DecisionCatalogSpec) -> None:
    """Reject incoherent declared designs before touching scientific values."""
    if not np.isfinite(spec.budget) or spec.budget <= 0.0:
        raise ValueError("Budget must be positive and finite.")
    if not np.isfinite(spec.budget_tolerance) or spec.budget_tolerance < 0.0:
        raise ValueError("Budget tolerance must be finite and nonnegative.")
    if not 0.0 <= spec.lgd <= 1.0:
        raise ValueError("LGD must lie in [0, 1].")
    if not 0.0 < spec.nominal_miscoverage < 1.0 or not 0.0 < spec.alpha < 1.0:
        raise ValueError("Nominal miscoverage and alpha must lie in (0, 1).")
    if not np.isfinite(spec.numeric_tolerance) or spec.numeric_tolerance < 0.0:
        raise ValueError("Numeric tolerance must be finite and nonnegative.")
    if (
        not np.isfinite(spec.payoff_contribution_tolerance)
        or spec.payoff_contribution_tolerance < 0.0
    ):
        raise ValueError("Payoff-contribution tolerance must be finite and nonnegative.")
    if spec.calibration_role == spec.target_role:
        raise ValueError("Calibration and target roles must differ.")
    _require_unique_nonempty(spec.calibration_periods, label="calibration_periods")
    _require_unique_nonempty(spec.target_periods, label="target_periods")
    _require_unique_nonempty(spec.window_ids, label="window_ids")
    _require_unique_nonempty(spec.rulers, label="rulers")
    _require_unique_nonempty(spec.coordinates, label="coordinates")
    _require_unique_nonempty(spec.gamma_grid, label="gamma_grid")
    if set(spec.calibration_periods).intersection(spec.target_periods):
        raise ValueError("Calibration and target periods overlap.")
    expected_per_block = (
        len(spec.window_ids) * len(spec.rulers) * len(spec.coordinates) * len(spec.gamma_grid)
    )
    if spec.expected_policies_per_block != expected_per_block:
        raise ValueError("Declared policies-per-block does not equal the Cartesian catalog.")
    expected_blocks = len(spec.calibration_periods) + len(spec.target_periods)
    if spec.expected_policy_rows != expected_blocks * expected_per_block:
        raise ValueError("Declared policy-row census does not equal blocks times catalog size.")
    rank = finite_sample_rank(len(spec.calibration_periods), alpha=spec.alpha)
    if rank != spec.expected_rank or rank > len(spec.calibration_periods):
        raise ValueError("Declared calibration rank is incoherent or exceeds its sample.")
    expected_labels = {"empty", "zero_only", "one_only", "both"}
    if set(spec.expected_set_type_counts) != expected_labels:
        raise ValueError("Set-type census must declare exactly the four binary set types.")
    if sum(spec.expected_set_type_counts.values()) != spec.expected_allocation_rows:
        raise ValueError("Set-type census does not sum to expected allocation rows.")


def finite_sample_rank(count: int, *, alpha: float) -> int:
    """Return ``ceil((n + 1) * (1 - alpha))`` for a finite block sample."""
    if isinstance(count, bool) or int(count) != count or int(count) < 1:
        raise ValueError("Calibration count must be a positive integer.")
    if not 0.0 < float(alpha) < 1.0:
        raise ValueError("alpha must lie in (0, 1).")
    return int(math.ceil((int(count) + 1) * (1.0 - float(alpha))))


def exact_binary_set_types(lower: pd.Series, upper: pd.Series) -> np.ndarray:
    """Classify exact binary membership after strict interval validation."""
    low = pd.to_numeric(lower, errors="raise").to_numpy(dtype=float)
    high = pd.to_numeric(upper, errors="raise").to_numpy(dtype=float)
    if low.shape != high.shape or low.ndim != 1 or not bool(np.isfinite(low).all()):
        raise ValueError("Conformal endpoints must be aligned finite vectors.")
    if not bool(np.isfinite(high).all()):
        raise ValueError("Conformal endpoints must be aligned finite vectors.")
    if bool(((low < 0.0) | (low > 1.0) | (high < 0.0) | (high > 1.0)).any()):
        raise ValueError("Conformal endpoints must lie exactly in [0, 1].")
    if bool((low > high).any()):
        raise ValueError("A conformal interval has lower endpoint above upper endpoint.")
    contains_zero = low <= 0.0
    contains_one = high >= 1.0
    labels = np.full(len(low), "empty", dtype=object)
    labels[contains_zero & ~contains_one] = "zero_only"
    labels[~contains_zero & contains_one] = "one_only"
    labels[contains_zero & contains_one] = "both"
    return labels.astype(str)


def _expected_policy_grid(spec: DecisionCatalogSpec) -> pd.DataFrame:
    blocks = [
        *((spec.calibration_role, period) for period in spec.calibration_periods),
        *((spec.target_role, period) for period in spec.target_periods),
    ]
    rows = [
        (role, period, window, ruler, coordinate, gamma)
        for (role, period), window, ruler, coordinate, gamma in product(
            blocks,
            spec.window_ids,
            spec.rulers,
            spec.coordinates,
            spec.gamma_grid,
        )
    ]
    return pd.DataFrame(rows, columns=POLICY_KEY)


def _require_exact_domain(series: pd.Series, expected: Sequence[Any], *, label: str) -> None:
    if bool(series.isna().any()):
        raise RuntimeError(f"{label} contains missing values.")
    actual = set(series.tolist())
    declared = set(expected)
    if actual != declared:
        raise RuntimeError(
            f"{label} domain changed: missing={sorted(declared - actual)}, "
            f"unexpected={sorted(actual - declared)}."
        )


def validate_outcome_free_catalog(
    allocations: pd.DataFrame,
    *,
    spec: DecisionCatalogSpec,
) -> CatalogAudit:
    """Validate outcome isolation, complete cells, budgets, and binary geometry."""
    validate_spec(spec)
    missing = sorted(REQUIRED_DECISION_COLUMNS.difference(allocations.columns))
    if missing:
        raise ValueError(f"Outcome-free allocations omit columns: {missing}.")
    normalized = {str(column).casefold() for column in allocations.columns}
    forbidden = set(FORBIDDEN_DECISION_COLUMNS).intersection(normalized)
    forbidden.update(
        column
        for column in normalized
        if column.startswith(("realized_", "snapshot_")) or "miscoverage" in column
    )
    if forbidden:
        raise ValueError(f"Outcome-free allocations leak endpoint fields: {sorted(forbidden)}.")
    if len(allocations) != spec.expected_allocation_rows:
        raise RuntimeError("Outcome-free allocation-row census changed.")
    if bool(allocations[list(ALLOCATION_KEY)].isna().any().any()):
        raise RuntimeError("Allocation identities contain missing values.")
    if bool(allocations["id"].astype("string").str.strip().eq("").any()):
        raise RuntimeError("Allocation IDs contain empty identities.")
    if bool(allocations.duplicated(list(ALLOCATION_KEY)).any()):
        raise RuntimeError("A policy contains duplicate funded loan IDs.")

    _require_exact_domain(
        allocations["role"], (spec.calibration_role, spec.target_role), label="role"
    )
    _require_exact_domain(allocations["window_id"], spec.window_ids, label="window_id")
    _require_exact_domain(allocations["frontier_ruler"], spec.rulers, label="ruler")
    _require_exact_domain(
        pd.to_numeric(allocations["frontier_coordinate"], errors="raise"),
        spec.coordinates,
        label="coordinate",
    )
    _require_exact_domain(
        pd.to_numeric(allocations["gamma"], errors="raise"), spec.gamma_grid, label="gamma"
    )
    role_periods = set(
        zip(
            allocations["role"].astype(str),
            allocations["period"].astype(str),
            strict=True,
        )
    )
    expected_role_periods = {
        *((spec.calibration_role, period) for period in spec.calibration_periods),
        *((spec.target_role, period) for period in spec.target_periods),
    }
    if role_periods != expected_role_periods:
        raise RuntimeError("Role-period block identities changed.")

    policies = allocations[list(POLICY_KEY)].drop_duplicates()
    expected_policies = _expected_policy_grid(spec)
    reconciled = expected_policies.merge(
        policies,
        on=list(POLICY_KEY),
        how="outer",
        indicator=True,
        validate="one_to_one",
    )
    if len(policies) != spec.expected_policy_rows or not bool(
        reconciled["_merge"].eq("both").all()
    ):
        raise RuntimeError("The complete policy catalog has a missing or extra cell.")
    for identity in ("candidate_id", "policy_label"):
        counts = allocations.groupby(list(POLICY_KEY), observed=True)[identity].nunique(
            dropna=False
        )
        if not bool(counts.eq(1).all()):
            raise RuntimeError(f"{identity} is not constant within a policy cell.")

    numeric = allocations[
        [
            "pd_point",
            "contractual_rate",
            "conformal_lower",
            "conformal_upper",
            "exposure",
            "expected_payoff_rate",
            "expected_payoff_contribution",
        ]
    ].apply(pd.to_numeric, errors="raise")
    if not bool(np.isfinite(numeric.to_numpy(dtype=float)).all()):
        raise ValueError("Decision quantities must be finite.")
    if bool(((numeric["pd_point"] < 0.0) | (numeric["pd_point"] > 1.0)).any()):
        raise ValueError("Point PD values must lie in [0, 1].")
    if bool(((numeric["contractual_rate"] < 0.0) | (numeric["contractual_rate"] > 1.0)).any()):
        raise ValueError("Contractual rates must lie in [0, 1].")
    if bool((numeric["exposure"] <= 0.0).any()):
        raise ValueError("Funded exposure must be strictly positive.")

    budgets = (
        allocations.assign(__exposure=numeric["exposure"])
        .groupby(list(POLICY_KEY), observed=True, sort=False)["__exposure"]
        .sum()
    )
    budget_error = np.abs(budgets.to_numpy(dtype=float) - spec.budget)
    if not bool((budget_error <= spec.budget_tolerance).all()):
        raise RuntimeError("At least one policy fails the declared full-budget tolerance.")

    set_types = exact_binary_set_types(numeric["conformal_lower"], numeric["conformal_upper"])
    set_counts = {label: int(np.sum(set_types == label)) for label in spec.expected_set_type_counts}
    if set_counts != dict(spec.expected_set_type_counts):
        raise RuntimeError(f"Frozen binary set census changed: {set_counts}.")
    if set_counts["one_only"] != 0:
        raise RuntimeError(
            "A {1}-only funded set invalidates the monotone shared-completion bound."
        )

    expected_rate = (1.0 - numeric["pd_point"].to_numpy(dtype=float)) * numeric[
        "contractual_rate"
    ].to_numpy(dtype=float) - numeric["pd_point"].to_numpy(dtype=float) * spec.lgd
    if not bool(
        np.isclose(
            expected_rate,
            numeric["expected_payoff_rate"].to_numpy(dtype=float),
            atol=spec.numeric_tolerance,
            rtol=0.0,
        ).all()
    ):
        raise RuntimeError("Stored expected-payoff rates do not reconcile to p, r, and LGD.")
    expected_contribution = numeric["exposure"].to_numpy(dtype=float) * expected_rate
    if not bool(
        np.isclose(
            expected_contribution,
            numeric["expected_payoff_contribution"].to_numpy(dtype=float),
            atol=spec.payoff_contribution_tolerance,
            rtol=0.0,
        ).all()
    ):
        raise RuntimeError("Stored expected-payoff contributions do not reconcile.")

    return CatalogAudit(
        set_types=set_types,
        summary={
            "allocation_rows": int(len(allocations)),
            "policy_rows": int(len(policies)),
            "blocks": int(len(expected_role_periods)),
            "policies_per_block": int(spec.expected_policies_per_block),
            "set_type_counts": set_counts,
            "maximum_absolute_budget_error_dollars": float(budget_error.max(initial=0.0)),
            "outcome_free": True,
            "catalog_complete": True,
        },
    )


def validate_decision_alignment(
    outcome_free: pd.DataFrame,
    evaluated_join: pd.DataFrame,
    *,
    numeric_tolerance: float,
) -> np.ndarray:
    """Return the join row order after reconciling every frozen decision field."""
    missing = sorted(set(outcome_free.columns).difference(evaluated_join.columns))
    if missing:
        raise RuntimeError(f"Endpoint join omits frozen decision columns: {missing}.")
    for label, frame in (("outcome-free", outcome_free), ("endpoint-joined", evaluated_join)):
        if bool(frame[list(ALLOCATION_KEY)].isna().any().any()):
            raise RuntimeError(f"{label} allocation keys contain missing values.")
        if bool(frame.duplicated(list(ALLOCATION_KEY)).any()):
            raise RuntimeError(f"{label} allocation keys are not unique.")
    if len(outcome_free) != len(evaluated_join):
        raise RuntimeError("Endpoint join changed the funded allocation-row census.")

    left_key = pd.MultiIndex.from_frame(outcome_free[list(ALLOCATION_KEY)])
    right_key = pd.MultiIndex.from_frame(evaluated_join[list(ALLOCATION_KEY)])
    order = right_key.get_indexer(left_key)
    if bool((order < 0).any()) or len(set(order.tolist())) != len(order):
        raise RuntimeError("Endpoint join changed the canonical funded allocation keys.")

    for column in outcome_free.columns:
        left = outcome_free[column]
        right = evaluated_join[column].iloc[order].reset_index(drop=True)
        if pd.api.types.is_numeric_dtype(left.dtype):
            left_values = pd.to_numeric(left, errors="raise").to_numpy(dtype=float)
            right_values = pd.to_numeric(right, errors="raise").to_numpy(dtype=float)
            equal = np.isclose(
                left_values,
                right_values,
                atol=float(numeric_tolerance),
                rtol=0.0,
                equal_nan=True,
            )
        elif pd.api.types.is_datetime64_any_dtype(left.dtype):
            equal = pd.to_datetime(left).to_numpy() == pd.to_datetime(right).to_numpy()
        else:
            left_values = left.astype("string").fillna("<NA>").to_numpy(dtype=str)
            right_values = right.astype("string").fillna("<NA>").to_numpy(dtype=str)
            equal = left_values == right_values
        if not bool(np.asarray(equal).all()):
            raise RuntimeError(f"Endpoint join changed frozen decision column {column!r}.")
    return order


def _validated_outcomes(joined: pd.DataFrame, order: np.ndarray) -> np.ndarray:
    required = {"snapshot_default", "snapshot_resolution"}
    missing = sorted(required.difference(joined.columns))
    if missing:
        raise ValueError(f"Endpoint join omits outcome columns: {missing}.")
    resolution = joined["snapshot_resolution"].iloc[order].astype("string")
    if bool(resolution.isna().any()) or bool(resolution.astype("string").str.strip().eq("").any()):
        raise RuntimeError("Endpoint resolution provenance is missing.")
    raw_outcome = joined["snapshot_default"].iloc[order]
    numeric_outcome = pd.to_numeric(raw_outcome, errors="coerce")
    invalid_nonmissing = raw_outcome.notna().to_numpy(dtype=bool) & numeric_outcome.isna().to_numpy(
        dtype=bool
    )
    if bool(invalid_nonmissing.any()):
        raise ValueError("A nonmissing endpoint outcome is not numeric.")
    outcome = numeric_outcome.astype("Float64").to_numpy(dtype=float, na_value=np.nan)
    resolved = np.isfinite(outcome)
    if bool(np.isinf(outcome).any()) or bool(np.any(resolved & ~np.isin(outcome, [0.0, 1.0]))):
        raise ValueError("Resolved endpoint outcomes must be binary; unresolved outcomes are NA.")
    resolution_values = resolution.to_numpy(dtype=str)
    allowed = set(RESOLVED_ENDPOINTS).union(UNRESOLVED_ENDPOINTS)
    unexpected = sorted(set(resolution_values).difference(allowed))
    if unexpected:
        raise RuntimeError(f"Endpoint resolution taxonomy changed: {unexpected}.")
    for label, expected_outcome in RESOLVED_ENDPOINTS.items():
        mask = resolution_values == label
        if bool((~resolved[mask]).any()) or bool((outcome[mask] != expected_outcome).any()):
            raise RuntimeError(f"Endpoint resolution {label!r} disagrees with its binary outcome.")
    unresolved_mask = np.isin(resolution_values, tuple(UNRESOLVED_ENDPOINTS))
    if bool(resolved[unresolved_mask].any()):
        raise RuntimeError("An unresolved endpoint-resolution reason has a binary outcome.")
    shared = pd.DataFrame(
        {
            "id": joined["id"].iloc[order].astype("string").to_numpy(),
            "snapshot_default": pd.Series(outcome, dtype="Float64"),
            "snapshot_resolution": resolution.astype("string").to_numpy(),
        }
    )
    grouped = shared.groupby("id", observed=True, sort=False)
    outcome_values = grouped["snapshot_default"].nunique(dropna=False)
    resolution_values = grouped["snapshot_resolution"].nunique(dropna=False)
    if not bool(outcome_values.eq(1).all() and resolution_values.eq(1).all()):
        raise RuntimeError("A repeated loan ID does not use one shared endpoint completion state.")
    return outcome


def _policy_score_bounds(
    allocations: pd.DataFrame,
    *,
    outcomes: np.ndarray,
    set_types: np.ndarray,
    spec: DecisionCatalogSpec,
) -> pd.DataFrame:
    exposure = pd.to_numeric(allocations["exposure"], errors="raise").to_numpy(dtype=float)
    point = pd.to_numeric(allocations["pd_point"], errors="raise").to_numpy(dtype=float)
    rate = pd.to_numeric(allocations["contractual_rate"], errors="raise").to_numpy(dtype=float)
    unresolved = ~np.isfinite(outcomes)
    y_lower = np.where(unresolved, 0.0, outcomes)
    y_upper = np.where(unresolved, 1.0, outcomes)
    contains_zero = np.isin(set_types, ["zero_only", "both"])
    contains_one = np.isin(set_types, ["one_only", "both"])
    miss_zero = (~contains_zero).astype(float)
    miss_one = (~contains_one).astype(float)
    if bool((miss_one < miss_zero).any()):
        raise RuntimeError("Miscoverage is not monotone under the shared binary completion.")
    payoff_coefficient = exposure * (rate + spec.lgd) / spec.budget
    default_coefficient = exposure / spec.budget
    if bool((payoff_coefficient < 0.0).any()) or bool((default_coefficient < 0.0).any()):
        raise RuntimeError("A decision-loss coefficient is negative.")

    resolved_miss = np.where(outcomes == 0.0, miss_zero, miss_one)
    miss_lower = np.where(unresolved, miss_zero, resolved_miss)
    miss_upper = np.where(unresolved, miss_one, resolved_miss)
    work = allocations[list(POLICY_KEY)].copy()
    work["candidate_id"] = allocations["candidate_id"].astype(str).to_numpy()
    work["policy_label"] = allocations["policy_label"].astype(str).to_numpy()
    work["exposure"] = exposure
    work["funded_rows"] = 1
    work["unresolved_funded_rows"] = unresolved.astype(int)
    work["unresolved_exposure"] = exposure * unresolved.astype(float)
    work["payoff_shortfall_lower_raw"] = payoff_coefficient * (y_lower - point)
    work["payoff_shortfall_upper_raw"] = payoff_coefficient * (y_upper - point)
    work["default_gap_lower_raw"] = default_coefficient * (y_lower - point)
    work["default_gap_upper_raw"] = default_coefficient * (y_upper - point)
    work["miscoverage_excess_lower_raw"] = exposure * miss_lower / spec.budget
    work["miscoverage_excess_upper_raw"] = exposure * miss_upper / spec.budget

    group_columns = [*POLICY_KEY, "candidate_id", "policy_label"]
    summed = work.groupby(group_columns, observed=True, sort=True, as_index=False).agg(
        exposure=("exposure", "sum"),
        funded_rows=("funded_rows", "sum"),
        unresolved_funded_rows=("unresolved_funded_rows", "sum"),
        unresolved_exposure=("unresolved_exposure", "sum"),
        payoff_shortfall_lower_raw=("payoff_shortfall_lower_raw", "sum"),
        payoff_shortfall_upper_raw=("payoff_shortfall_upper_raw", "sum"),
        default_gap_lower_raw=("default_gap_lower_raw", "sum"),
        default_gap_upper_raw=("default_gap_upper_raw", "sum"),
        miscoverage_excess_lower_raw=("miscoverage_excess_lower_raw", "sum"),
        miscoverage_excess_upper_raw=("miscoverage_excess_upper_raw", "sum"),
    )
    summed["miscoverage_excess_lower_raw"] -= spec.nominal_miscoverage
    summed["miscoverage_excess_upper_raw"] -= spec.nominal_miscoverage

    tables: list[pd.DataFrame] = []
    identity = [*group_columns, "exposure", "funded_rows", "unresolved_funded_rows"]
    for metric in METRICS:
        table = summed[identity].copy()
        table["unresolved_exposure_share"] = summed["unresolved_exposure"] / spec.budget
        table["metric"] = metric
        table["raw_gap_lower"] = summed[f"{metric}_lower_raw"]
        table["raw_gap_upper"] = summed[f"{metric}_upper_raw"]
        table["score_lower"] = np.maximum(table["raw_gap_lower"], 0.0)
        table["score_upper"] = np.maximum(table["raw_gap_upper"], 0.0)
        tables.append(table)
    result = pd.concat(tables, ignore_index=True)
    if len(result) != spec.expected_policy_rows * len(METRICS):
        raise RuntimeError("Policy-metric output census changed.")
    if bool((result["score_lower"] > result["score_upper"]).any()):
        raise RuntimeError("A policy score bound is incoherent.")
    return result.sort_values(["role", "period", "metric", *POLICY_KEY[2:]]).reset_index(drop=True)


def _block_score_bounds(policy_scores: pd.DataFrame, *, spec: DecisionCatalogSpec) -> pd.DataFrame:
    block = policy_scores.groupby(
        ["role", "period", "metric"], observed=True, sort=True, as_index=False
    ).agg(
        score_lower=("score_lower", "max"),
        score_upper=("score_upper", "max"),
        policies=("candidate_id", "size"),
    )
    expected_rows = (len(spec.calibration_periods) + len(spec.target_periods)) * len(METRICS)
    if len(block) != expected_rows or not bool(
        block["policies"].eq(spec.expected_policies_per_block).all()
    ):
        raise RuntimeError("Block-metric catalog census changed.")
    if bool((block["score_lower"] > block["score_upper"]).any()):
        raise RuntimeError("A block score bound is incoherent.")
    return block


def _calibration_thresholds(
    block_scores: pd.DataFrame, *, spec: DecisionCatalogSpec
) -> pd.DataFrame:
    development = block_scores.loc[block_scores["role"].eq(spec.calibration_role)]
    rows: list[dict[str, Any]] = []
    for metric in METRICS:
        values = development.loc[development["metric"].eq(metric)]
        if len(values) != len(spec.calibration_periods):
            raise RuntimeError("Calibration block census changed for a metric.")
        rank = finite_sample_rank(len(values), alpha=spec.alpha)
        if rank != spec.expected_rank or rank > len(values):
            raise RuntimeError("Calibration rank changed.")
        lower = np.sort(values["score_lower"].to_numpy(dtype=float))
        upper = np.sort(values["score_upper"].to_numpy(dtype=float))
        rows.append(
            {
                "metric": metric,
                "calibration_blocks": int(len(values)),
                "alpha": float(spec.alpha),
                "rank": int(rank),
                "q_lower": float(lower[rank - 1]),
                "q_upper": float(upper[rank - 1]),
                "development_min_lower": float(lower[0]),
                "development_max_upper": float(upper[-1]),
            }
        )
    result = pd.DataFrame(rows)
    if len(result) != len(METRICS) or bool((result["q_lower"] > result["q_upper"]).any()):
        raise RuntimeError("Calibration-threshold output is incoherent.")
    return result


def _target_classification(
    block_scores: pd.DataFrame,
    thresholds: pd.DataFrame,
    *,
    spec: DecisionCatalogSpec,
) -> pd.DataFrame:
    target = block_scores.loc[block_scores["role"].eq(spec.target_role)].merge(
        thresholds[["metric", "q_lower", "q_upper", "development_max_upper"]],
        on="metric",
        how="left",
        validate="many_to_one",
    )
    definitely_exceeds = target["score_lower"] > target["q_upper"]
    definitely_within = target["score_upper"] <= target["q_lower"]
    target["classification"] = np.select(
        [definitely_exceeds, definitely_within],
        ["definitely_exceeds", "definitely_within"],
        default="indeterminate",
    )
    target["exceeds_conservative_reference"] = definitely_exceeds
    target["within_conservative_reference"] = target["score_upper"] <= target["q_upper"]
    target["exceeds_all_development_upper"] = (
        target["score_lower"] > target["development_max_upper"]
    )
    expected_rows = len(spec.target_periods) * len(METRICS)
    if len(target) != expected_rows or bool(target[["q_lower", "q_upper"]].isna().any().any()):
        raise RuntimeError("Target-classification output census changed.")
    return target.sort_values(["period", "metric"]).reset_index(drop=True)


def build_decision_catalog_transport(
    outcome_free_allocations: pd.DataFrame,
    evaluated_join: pd.DataFrame,
    *,
    spec: DecisionCatalogSpec,
) -> DecisionCatalogTransportResult:
    """Build exact policy, block, threshold, and target bound tables."""
    audit = validate_outcome_free_catalog(outcome_free_allocations, spec=spec)
    order = validate_decision_alignment(
        outcome_free_allocations,
        evaluated_join,
        numeric_tolerance=spec.numeric_tolerance,
    )
    outcomes = _validated_outcomes(evaluated_join, order)
    policy_scores = _policy_score_bounds(
        outcome_free_allocations,
        outcomes=outcomes,
        set_types=audit.set_types,
        spec=spec,
    )
    block_scores = _block_score_bounds(policy_scores, spec=spec)
    thresholds = _calibration_thresholds(block_scores, spec=spec)
    target = _target_classification(block_scores, thresholds, spec=spec)

    separation = []
    for metric in METRICS:
        metric_target = target.loc[target["metric"].eq(metric)]
        threshold = thresholds.loc[thresholds["metric"].eq(metric)].iloc[0]
        separation.append(
            {
                "metric": metric,
                "robust_complete_separation": bool(
                    metric_target["exceeds_all_development_upper"].all()
                ),
                "target_definitely_exceeds_count": int(
                    metric_target["classification"].eq("definitely_exceeds").sum()
                ),
                "target_blocks": int(len(metric_target)),
                "development_q_lower": float(threshold["q_lower"]),
                "development_q_upper": float(threshold["q_upper"]),
                "target_score_lower_min": float(metric_target["score_lower"].min()),
                "target_score_lower_max": float(metric_target["score_lower"].max()),
            }
        )
    summary = {
        "status": "complete_postinspection_decision_catalog_transport_candidate",
        "catalog_audit": audit.summary,
        "outcomes": {
            "joined_rows": int(len(evaluated_join)),
            "resolved_rows_across_policy_allocations": int(np.isfinite(outcomes).sum()),
            "unresolved_rows_across_policy_allocations": int((~np.isfinite(outcomes)).sum()),
            "decision_alignment_exact_with_numeric_tolerance": True,
        },
        "design": {
            "metrics": list(METRICS),
            "calibration_blocks": len(spec.calibration_periods),
            "target_blocks": len(spec.target_periods),
            "policies_per_block": spec.expected_policies_per_block,
            "shared_unresolved_completion": True,
            "exact_binary_endpoint_membership": True,
            "rank": spec.expected_rank,
            "alpha": spec.alpha,
        },
        "output_census": {
            "policy_score_bounds": int(len(policy_scores)),
            "block_score_bounds": int(len(block_scores)),
            "calibration_thresholds": int(len(thresholds)),
            "target_classification": int(len(target)),
        },
        "metric_results": separation,
        "ordering_reference": {
            "reported": False,
            "reason": (
                "one_over_choose_26_11_applies_to_one_prespecified_scalar_ranking_not_the_"
                "postinspection_intersection_of_three_metric_rankings"
            ),
            "p_value_reported": False,
        },
        "claim_boundary": {
            "diagnostic_candidate_only": True,
            "active_claim": False,
            "policy_selection": None,
            "policy_winner": None,
            "causal_interpretation": False,
            "conformal_guarantee_repair": False,
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    }
    return DecisionCatalogTransportResult(
        policy_score_bounds=policy_scores,
        block_score_bounds=block_scores,
        calibration_thresholds=thresholds,
        target_classification=target,
        summary=summary,
    )
