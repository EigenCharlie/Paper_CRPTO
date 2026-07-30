"""Finite-archive funded-selection estimands with shared binary completions.

This module audits a fixed, outcome-blind USD 25 allocation support.  It does
not provide selection-conditional conformal coverage or false-coverage-rate
control; those require additional probabilistic assumptions and procedures.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.evaluation.coverage_transport import binary_miscoverage_bounds

RESOLVED_ENDPOINTS = {
    "fully_paid_by_reconstructed_cutoff": 0.0,
    "charged_off_by_reconstructed_cutoff": 1.0,
}
UNRESOLVED_ENDPOINTS = {
    "terminal_availability_date_missing",
    "nonterminal_or_unresolved_status",
}
JOIN_KEYS = ("id", "window_id", "role", "period", "candidate_id")
LINEAGE_STRING_COLUMNS = (
    "design_split",
    "purpose",
    "policy_label",
    "comparator_rule",
    "paired_policy_id",
    "frontier_ruler",
)
LINEAGE_DATETIME_COLUMNS = ("issue_d",)
LINEAGE_NUMERIC_COLUMNS = (
    "pd_point",
    "loan_amnt",
    "contractual_rate",
    "conformal_lower",
    "conformal_upper",
    "allocation_fraction",
    "exposure",
    "weight",
    "pd_effective",
    "expected_payoff_rate",
    "expected_payoff_contribution",
    "frontier_coordinate",
    "frontier_cap",
    "objective_target",
    "gamma",
)
PARENT_EVALUATION_LINEAGE_COLUMNS = (
    *LINEAGE_STRING_COLUMNS,
    *LINEAGE_DATETIME_COLUMNS,
    *LINEAGE_NUMERIC_COLUMNS,
)
ROUNDING_CHANGED_COLUMNS = {
    "allocation_fraction",
    "exposure",
    "weight",
    "expected_payoff_contribution",
}
ROUNDING_INVARIANT_COLUMNS = tuple(
    column for column in PARENT_EVALUATION_LINEAGE_COLUMNS if column not in ROUNDING_CHANGED_COLUMNS
)
MONTHLY_POLICY_KEYS = (
    "window_id",
    "role",
    "period",
    "frontier_ruler",
    "frontier_coordinate",
    "gamma",
    "candidate_id",
)
TRACK_POLICY_KEYS = (
    "window_id",
    "role",
    "frontier_ruler",
    "frontier_coordinate",
    "gamma",
    "candidate_id",
)
MONTHLY_CONTRAST_KEYS = (
    "window_id",
    "role",
    "period",
    "frontier_ruler",
    "frontier_coordinate",
)
TRACK_CONTRAST_KEYS = (
    "window_id",
    "role",
    "frontier_ruler",
    "frontier_coordinate",
)


@dataclass(frozen=True)
class FundedSelectionTables:
    """Complete fixed-support summaries and gamma endpoint contrasts."""

    monthly_bounds: pd.DataFrame
    track_bounds: pd.DataFrame
    monthly_gamma_contrasts: pd.DataFrame
    track_gamma_contrasts: pd.DataFrame
    support_and_fixed_capital_reconciliation: pd.DataFrame


def build_funded_selection_estimand_audit(
    rounded_allocations: pd.DataFrame,
    continuous_parent_allocations: pd.DataFrame,
    joined_funded_allocations: pd.DataFrame,
    granularity_contrasts: pd.DataFrame,
    *,
    periods: Sequence[str],
    role: str = "primary_oot",
    lot_size_usd: float = 25.0,
    committed_budget_usd: float = 1_000_000.0,
    tolerance: float = 1.0e-12,
    source_rounding_tolerance: float = 1.0e-8,
    expected_source_positive_positions: int | None = None,
    expected_rounded_positive_positions: int | None = None,
    expected_removed_positions: int | None = None,
    expected_changed_positions: int | None = None,
) -> FundedSelectionTables:
    """Build exhaustive binary- and dollar-weighted fixed-support bounds.

    The binary selection unit is one unique loan position in one issue month.
    Track rows pool all selected positions over the declared period grid before
    division.  Every contrast uses the same unresolved binary label for a loan
    on both sides, which makes the reported cellwise bounds sharp.
    """
    expected_periods = tuple(str(value) for value in periods)
    if not expected_periods or len(expected_periods) != len(set(expected_periods)):
        raise ValueError("Periods must be a non-empty sequence of unique labels.")
    if not np.isfinite(lot_size_usd) or lot_size_usd <= 0.0:
        raise ValueError("The funded-support lot size must be finite and positive.")
    if not np.isfinite(committed_budget_usd) or committed_budget_usd <= 0.0:
        raise ValueError("The monthly committed budget must be finite and positive.")
    if not np.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("Tolerance must be finite and non-negative.")
    if not np.isfinite(source_rounding_tolerance) or source_rounding_tolerance <= 0.0:
        raise ValueError("Source rounding tolerance must be finite and positive.")

    funded, continuous = _prepare_funded_rows(
        rounded_allocations,
        continuous_parent_allocations,
        joined_funded_allocations,
        periods=expected_periods,
        role=str(role),
        lot_size_usd=float(lot_size_usd),
        tolerance=float(tolerance),
        source_rounding_tolerance=float(source_rounding_tolerance),
        expected_source_positive_positions=expected_source_positive_positions,
        expected_rounded_positive_positions=expected_rounded_positive_positions,
        expected_removed_positions=expected_removed_positions,
        expected_changed_positions=expected_changed_positions,
    )
    monthly = _summarize_policies(
        funded, keys=MONTHLY_POLICY_KEYS, committed_budget_usd=committed_budget_usd
    )
    tracks = _summarize_policies(
        funded, keys=TRACK_POLICY_KEYS, committed_budget_usd=committed_budget_usd
    )
    monthly_contrasts = _gamma_contrasts(
        funded, keys=MONTHLY_CONTRAST_KEYS, committed_budget_usd=committed_budget_usd
    )
    track_contrasts = _gamma_contrasts(
        funded, keys=TRACK_CONTRAST_KEYS, committed_budget_usd=committed_budget_usd
    )
    reconciliation = _reconcile_support_and_fixed_capital_to_v3(
        funded,
        continuous,
        granularity_contrasts,
        committed_budget_usd=committed_budget_usd,
        tolerance=tolerance,
        source_rounding_tolerance=source_rounding_tolerance,
    )
    return FundedSelectionTables(
        monthly_bounds=monthly,
        track_bounds=tracks,
        monthly_gamma_contrasts=monthly_contrasts,
        track_gamma_contrasts=track_contrasts,
        support_and_fixed_capital_reconciliation=reconciliation,
    )


def _require_columns(frame: pd.DataFrame, required: set[str], *, label: str) -> None:
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise KeyError(f"{label} is missing required columns: {missing}.")


def _numeric_array(frame: pd.DataFrame, column: str) -> np.ndarray:
    values = pd.to_numeric(frame[column], errors="raise").to_numpy(dtype=float)
    if not bool(np.isfinite(values).all()):
        raise ValueError(f"Column {column!r} contains nonfinite values.")
    return values


def _require_exact_lineage_pairs(
    frame: pd.DataFrame,
    *,
    columns: Sequence[str],
    left_suffix: str,
    right_suffix: str,
    label: str,
) -> None:
    """Require NaN-safe exact equality for declared paired lineage columns."""
    for column in columns:
        left = frame[f"{column}{left_suffix}"]
        right = frame[f"{column}{right_suffix}"]
        if column in LINEAGE_NUMERIC_COLUMNS:
            left_values = pd.to_numeric(left, errors="raise").to_numpy(dtype=float, na_value=np.nan)
            right_values = pd.to_numeric(right, errors="raise").to_numpy(
                dtype=float, na_value=np.nan
            )
            equal = np.array_equal(left_values, right_values, equal_nan=True)
        elif column in LINEAGE_DATETIME_COLUMNS:
            left_values = pd.to_datetime(left, errors="raise").to_numpy()
            right_values = pd.to_datetime(right, errors="raise").to_numpy()
            equal = np.array_equal(left_values, right_values)
        else:
            left_values = left.astype("string")
            right_values = right.astype("string")
            equal = bool(
                left_values.isna().equals(right_values.isna())
                and left_values.fillna("<NA>").equals(right_values.fillna("<NA>"))
            )
        if not equal:
            raise RuntimeError(f"{label} disagree on {column!r}.")


def _prepare_funded_rows(
    rounded: pd.DataFrame,
    parent: pd.DataFrame,
    joined: pd.DataFrame,
    *,
    periods: tuple[str, ...],
    role: str,
    lot_size_usd: float,
    tolerance: float,
    source_rounding_tolerance: float,
    expected_source_positive_positions: int | None,
    expected_rounded_positive_positions: int | None,
    expected_removed_positions: int | None,
    expected_changed_positions: int | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rounded_required = {
        *JOIN_KEYS,
        *ROUNDING_INVARIANT_COLUMNS,
        "exposure",
        "source_exposure",
    }
    parent_required = {
        *JOIN_KEYS,
        *PARENT_EVALUATION_LINEAGE_COLUMNS,
    }
    joined_required = {
        *JOIN_KEYS,
        "conformal_lower",
        "conformal_upper",
        "snapshot_default",
        "snapshot_resolution",
        "miscoverage_lower",
        "miscoverage_upper",
    }
    _require_columns(rounded, rounded_required, label="Rounded allocation support")
    _require_columns(parent, parent_required, label="Continuous V3 parent allocations")
    _require_columns(
        joined,
        joined_required | set(PARENT_EVALUATION_LINEAGE_COLUMNS),
        label="Outcome-joined allocations",
    )

    source = rounded.copy()
    source["role"] = source["role"].astype(str)
    source["period"] = source["period"].astype(str)
    if set(source["role"]) != {role}:
        raise RuntimeError("Rounded support does not contain exactly the declared role.")
    if set(source["period"]) != set(periods):
        raise RuntimeError("Rounded support period population differs from the locked grid.")
    if bool(source.duplicated(list(JOIN_KEYS)).any()):
        raise RuntimeError("Rounded support contains duplicate loan-policy-month rows.")

    exposure = _numeric_array(source, "exposure")
    if bool((exposure <= tolerance).any()):
        raise RuntimeError("Every retained funded-support exposure must be positive.")
    remainder = np.mod(exposure, lot_size_usd)
    if bool((remainder != 0.0).any()):
        raise RuntimeError("Funded-support exposures are not exact lot multiples.")
    gamma = _numeric_array(source, "gamma")
    if set(gamma.tolist()) != {0.0, 1.0}:
        raise RuntimeError("The funded-support audit requires both gamma endpoints 0 and 1.")

    track_keys = ["window_id", "candidate_id"]
    track_metadata = source.groupby(track_keys, observed=True, sort=False).agg(
        roles=("role", "nunique"),
        rulers=("frontier_ruler", "nunique"),
        coordinates=("frontier_coordinate", "nunique"),
        gammas=("gamma", "nunique"),
        months=("period", "nunique"),
    )
    if bool((track_metadata[["roles", "rulers", "coordinates", "gammas"]] != 1).any(axis=None)):
        raise RuntimeError("A candidate_id aliases multiple policy tracks.")
    if not bool(track_metadata["months"].eq(len(periods)).all()):
        raise RuntimeError("At least one policy track has an incomplete month grid.")
    for (window_id, candidate_id), track in source.groupby(track_keys, observed=True, sort=False):
        if set(track["period"].astype(str)) != set(periods):
            raise RuntimeError(
                f"Policy track {window_id!r}/{candidate_id!r} has the wrong month labels."
            )
        if bool(track["id"].astype(str).duplicated().any()):
            raise RuntimeError(
                f"Policy track {window_id!r}/{candidate_id!r} repeats a loan across issue months."
            )

    source_track_index = pd.MultiIndex.from_frame(source[track_keys].drop_duplicates())
    parent_track_index = pd.MultiIndex.from_frame(parent[track_keys])
    relevant_parent = parent.loc[
        parent_track_index.isin(source_track_index)
        & parent["role"].astype(str).eq(role)
        & parent["period"].astype(str).isin(periods)
    ].copy()
    relevant_parent_track_index = pd.MultiIndex.from_frame(
        relevant_parent[track_keys].drop_duplicates()
    )
    if set(relevant_parent_track_index.tolist()) != set(source_track_index.tolist()):
        raise RuntimeError("The continuous V3 parent omits a rounded policy track.")
    if bool(relevant_parent.duplicated(list(JOIN_KEYS)).any()):
        raise RuntimeError("Continuous V3 parent allocations contain duplicate join keys.")

    joined_track_index = pd.MultiIndex.from_frame(joined[track_keys])
    relevant_joined = joined.loc[
        joined_track_index.isin(source_track_index)
        & joined["role"].astype(str).eq(role)
        & joined["period"].astype(str).isin(periods)
    ].copy()
    relevant_joined_track_index = pd.MultiIndex.from_frame(
        relevant_joined[track_keys].drop_duplicates()
    )
    if set(relevant_joined_track_index.tolist()) != set(source_track_index.tolist()):
        raise RuntimeError("The outcome-joined source omits a rounded policy track.")
    if bool(relevant_joined.duplicated(list(JOIN_KEYS)).any()):
        raise RuntimeError("Outcome-joined allocations contain duplicate join keys.")

    lineage = relevant_parent.loc[:, [*JOIN_KEYS, *PARENT_EVALUATION_LINEAGE_COLUMNS]].merge(
        relevant_joined.loc[:, [*JOIN_KEYS, *PARENT_EVALUATION_LINEAGE_COLUMNS]],
        on=list(JOIN_KEYS),
        how="outer",
        validate="one_to_one",
        indicator=True,
        suffixes=("_parent", "_evaluation"),
    )
    if not bool(lineage["_merge"].eq("both").all()):
        raise RuntimeError("V3 parent and V5 outcome join have different funded supports.")
    _require_exact_lineage_pairs(
        lineage,
        columns=PARENT_EVALUATION_LINEAGE_COLUMNS,
        left_suffix="_parent",
        right_suffix="_evaluation",
        label="V3 parent and V5 outcome join",
    )

    rounding_lineage = relevant_parent.loc[:, [*JOIN_KEYS, *ROUNDING_INVARIANT_COLUMNS]].merge(
        source.loc[:, [*JOIN_KEYS, *ROUNDING_INVARIANT_COLUMNS]],
        on=list(JOIN_KEYS),
        how="inner",
        validate="one_to_one",
        suffixes=("_parent", "_rounded"),
    )
    if len(rounding_lineage) != len(source):
        raise RuntimeError("Rounded support is not a subset of its exact V3 parent support.")
    _require_exact_lineage_pairs(
        rounding_lineage,
        columns=ROUNDING_INVARIANT_COLUMNS,
        left_suffix="_parent",
        right_suffix="_rounded",
        label="V3 parent and rounded support",
    )

    outcome_columns = [
        "snapshot_default",
        "snapshot_resolution",
        "miscoverage_lower",
        "miscoverage_upper",
    ]
    continuous = relevant_parent.loc[:, [*parent_required]].merge(
        relevant_joined.loc[:, [*JOIN_KEYS, *outcome_columns]],
        on=list(JOIN_KEYS),
        how="left",
        validate="one_to_one",
    )
    if bool(
        continuous[["snapshot_resolution", "miscoverage_lower", "miscoverage_upper"]]
        .isna()
        .any(axis=None)
    ):
        raise RuntimeError("The V3 parent support is not fully covered by the V5 outcome join.")
    continuous["funded_exposure"] = _numeric_array(continuous, "exposure")
    if bool((continuous["funded_exposure"] <= tolerance).any()):
        raise RuntimeError("Continuous source contains a non-positive retained exposure.")
    continuous = _attach_binary_miscoverage(continuous)
    for (window_id, candidate_id), track in continuous.groupby(
        track_keys, observed=True, sort=False
    ):
        if set(track["period"].astype(str)) != set(periods):
            raise RuntimeError(
                f"Continuous track {window_id!r}/{candidate_id!r} has the wrong month grid."
            )
        if bool(track["id"].astype(str).duplicated().any()):
            raise RuntimeError(
                f"Continuous track {window_id!r}/{candidate_id!r} repeats a loan across issue months."
            )

    support_keys = list(JOIN_KEYS)
    continuous_support = continuous.loc[:, [*support_keys, "funded_exposure"]].rename(
        columns={"funded_exposure": "continuous_exposure"}
    )
    rounded_support = source.loc[:, [*support_keys, "source_exposure", "exposure"]].rename(
        columns={"exposure": "rounded_exposure"}
    )
    support = continuous_support.merge(
        rounded_support,
        on=support_keys,
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    added = int(support["_merge"].eq("right_only").sum())
    removed = int(support["_merge"].eq("left_only").sum())
    retained = support["_merge"].eq("both")
    if added:
        raise RuntimeError(
            "Rounded USD 25 support adds positions absent from its continuous parent."
        )
    retained_source = pd.to_numeric(
        support.loc[retained, "source_exposure"], errors="raise"
    ).to_numpy(dtype=float)
    retained_continuous = pd.to_numeric(
        support.loc[retained, "continuous_exposure"], errors="raise"
    ).to_numpy(dtype=float)
    retained_rounded = pd.to_numeric(
        support.loc[retained, "rounded_exposure"], errors="raise"
    ).to_numpy(dtype=float)
    if not np.array_equal(retained_source, retained_continuous):
        raise RuntimeError("Rounded source_exposure does not equal the continuous parent exposure.")
    expected_rounded = lot_size_usd * np.floor(
        (np.maximum(retained_source, 0.0) + source_rounding_tolerance) / lot_size_usd
    )
    if not np.array_equal(retained_rounded, expected_rounded):
        raise RuntimeError("Rounded exposure does not equal the locked USD 25 floor transform.")
    removed_source = pd.to_numeric(
        support.loc[support["_merge"].eq("left_only"), "continuous_exposure"], errors="raise"
    ).to_numpy(dtype=float)
    if not bool(np.isfinite(removed_source).all()):
        raise RuntimeError("Removed V3 parent exposures contain nonfinite values.")
    removed_rounded = lot_size_usd * np.floor(
        (np.maximum(removed_source, 0.0) + source_rounding_tolerance) / lot_size_usd
    )
    if bool((removed_rounded != 0.0).any()):
        raise RuntimeError("A removed V3 parent position does not floor to zero exposure.")
    changed_retained = int(
        (np.abs(retained_rounded - retained_source) > source_rounding_tolerance).sum()
    )
    support_counts = {
        "source": int(len(continuous_support)),
        "rounded": int(len(rounded_support)),
        "removed": removed,
        "changed": changed_retained + removed,
    }
    expected_counts = {
        "source": expected_source_positive_positions,
        "rounded": expected_rounded_positive_positions,
        "removed": expected_removed_positions,
        "changed": expected_changed_positions,
    }
    for label, expected_count in expected_counts.items():
        if expected_count is not None and support_counts[label] != int(expected_count):
            raise RuntimeError(
                f"USD 25 support {label} census changed: "
                f"{support_counts[label]} != {int(expected_count)}."
            )

    facts = continuous.loc[:, list(joined_required)].copy()
    facts["role"] = facts["role"].astype(str)
    facts["period"] = facts["period"].astype(str)
    facts = facts.rename(
        columns={
            "conformal_lower": "evaluation_conformal_lower",
            "conformal_upper": "evaluation_conformal_upper",
            "miscoverage_lower": "evaluation_miscoverage_lower",
            "miscoverage_upper": "evaluation_miscoverage_upper",
        }
    )
    funded = source.merge(facts, on=list(JOIN_KEYS), how="left", validate="one_to_one")
    outcome_columns = [
        "evaluation_conformal_lower",
        "evaluation_conformal_upper",
        "snapshot_resolution",
        "evaluation_miscoverage_lower",
        "evaluation_miscoverage_upper",
    ]
    if bool(funded[outcome_columns].isna().any(axis=None)):
        raise RuntimeError("The rounded funded support is not fully covered by the outcome join.")

    lower = _numeric_array(funded, "conformal_lower")
    upper = _numeric_array(funded, "conformal_upper")
    evaluation_lower = _numeric_array(funded, "evaluation_conformal_lower")
    evaluation_upper = _numeric_array(funded, "evaluation_conformal_upper")
    if bool((lower > upper).any()):
        raise RuntimeError("A conformal interval has reversed endpoints.")
    if not np.array_equal(lower, evaluation_lower) or not np.array_equal(upper, evaluation_upper):
        raise RuntimeError("Rounded support and evaluation conformal endpoints differ.")

    funded["funded_exposure"] = exposure
    funded = _attach_binary_miscoverage(funded)
    return funded, continuous


def _attach_binary_miscoverage(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    if bool(result["snapshot_resolution"].isna().any()):
        raise RuntimeError("A funded row has no registered endpoint-resolution reason.")
    lower = _numeric_array(result, "conformal_lower")
    upper = _numeric_array(result, "conformal_upper")
    if bool((lower > upper).any()):
        raise RuntimeError("A conformal interval has reversed endpoints.")
    raw_outcome = result["snapshot_default"]
    numeric_outcome = pd.to_numeric(raw_outcome, errors="coerce")
    raw_missing = raw_outcome.isna().to_numpy(dtype=bool)
    parsed_outcome = numeric_outcome.to_numpy(dtype=float, na_value=np.nan)
    invalid_nonmissing = (~raw_missing) & (
        (~np.isfinite(parsed_outcome)) | (~np.isin(parsed_outcome, [0.0, 1.0]))
    )
    if bool(invalid_nonmissing.any()):
        raise ValueError("Every nonmissing funded outcome must be finite and binary.")
    outcome = parsed_outcome.copy()
    outcome[raw_missing] = np.nan
    resolved = ~raw_missing
    resolution = result["snapshot_resolution"].astype("string").to_numpy(dtype=str)
    allowed = set(RESOLVED_ENDPOINTS).union(UNRESOLVED_ENDPOINTS)
    unexpected = sorted(set(resolution).difference(allowed))
    if unexpected:
        raise RuntimeError(f"Funded endpoint resolution taxonomy changed: {unexpected}.")
    for label, expected_outcome in RESOLVED_ENDPOINTS.items():
        mask = resolution == label
        if bool((~resolved[mask]).any()) or bool((outcome[mask] != expected_outcome).any()):
            raise RuntimeError(f"Funded endpoint reason {label!r} disagrees with its outcome.")
    unresolved_mask = np.isin(resolution, tuple(UNRESOLVED_ENDPOINTS))
    if bool(resolved[unresolved_mask].any()):
        raise RuntimeError("An unresolved funded endpoint reason has a binary outcome.")
    miss_lower, miss_upper = binary_miscoverage_bounds(outcome, lower, upper)
    stored_lower_column = (
        "evaluation_miscoverage_lower"
        if "evaluation_miscoverage_lower" in result
        else "miscoverage_lower"
    )
    stored_upper_column = (
        "evaluation_miscoverage_upper"
        if "evaluation_miscoverage_upper" in result
        else "miscoverage_upper"
    )
    stored_lower = _numeric_array(result, stored_lower_column)
    stored_upper = _numeric_array(result, stored_upper_column)
    if not np.array_equal(miss_lower, stored_lower) or not np.array_equal(miss_upper, stored_upper):
        raise RuntimeError("Recomputed binary miscoverage does not reconcile to evaluation rows.")
    miss_zero = ((lower > 0.0) | (upper < 0.0)).astype(float)
    miss_one = ((lower > 1.0) | (upper < 1.0)).astype(float)
    result["outcome_resolved"] = resolved
    result["miss_zero"] = miss_zero
    result["miss_one"] = miss_one
    result["miss_lower"] = miss_lower
    result["miss_upper"] = miss_upper
    result["set_empty"] = (miss_zero == 1.0) & (miss_one == 1.0)
    result["set_full"] = (miss_zero == 0.0) & (miss_one == 0.0)
    result["set_singleton_zero"] = (miss_zero == 0.0) & (miss_one == 1.0)
    result["set_singleton_one"] = (miss_zero == 1.0) & (miss_one == 0.0)
    return result


def _sharp_linear_bounds(frame: pd.DataFrame, coefficients: np.ndarray) -> tuple[float, float]:
    if len(frame) != len(coefficients):
        raise ValueError("Sharp-bound coefficients do not align with funded rows.")
    resolved = frame["outcome_resolved"].to_numpy(dtype=bool)
    outcome = pd.to_numeric(frame["snapshot_default"], errors="coerce").to_numpy(dtype=float)
    miss_zero = frame["miss_zero"].to_numpy(dtype=float)
    miss_one = frame["miss_one"].to_numpy(dtype=float)
    observed_miss = np.where(outcome == 0.0, miss_zero, miss_one)
    contribution_zero = coefficients * miss_zero
    contribution_one = coefficients * miss_one
    lower = np.where(
        resolved,
        coefficients * observed_miss,
        np.minimum(contribution_zero, contribution_one),
    )
    upper = np.where(
        resolved,
        coefficients * observed_miss,
        np.maximum(contribution_zero, contribution_one),
    )
    return float(lower.sum()), float(upper.sum())


def _policy_record(frame: pd.DataFrame, *, committed_capital_usd: float) -> dict[str, Any]:
    n_selected = len(frame)
    if n_selected <= 0:
        raise RuntimeError("A funded policy group is empty.")
    exposure = frame["funded_exposure"].to_numpy(dtype=float)
    funded_dollars = float(exposure.sum())
    if not np.isfinite(funded_dollars) or funded_dollars <= 0.0:
        raise RuntimeError("A funded policy group has no positive funded dollars.")
    capital_tolerance = max(1.0e-8, committed_capital_usd * 1.0e-12)
    if funded_dollars > committed_capital_usd + capital_tolerance:
        raise RuntimeError("Funded dollars exceed the declared fixed capital.")
    miss_lower = frame["miss_lower"].to_numpy(dtype=float)
    miss_upper = frame["miss_upper"].to_numpy(dtype=float)
    count_fcp_lower = float(miss_lower.mean())
    count_fcp_upper = float(miss_upper.mean())
    dollar_fcp_lower = float(exposure @ miss_lower / funded_dollars)
    dollar_fcp_upper = float(exposure @ miss_upper / funded_dollars)
    fixed_fcp_lower = float(exposure @ miss_lower / committed_capital_usd)
    fixed_fcp_upper = float(exposure @ miss_upper / committed_capital_usd)
    count_minus_invested_coefficients = (
        np.full(n_selected, 1.0 / n_selected) - exposure / funded_dollars
    )
    count_minus_invested_lower, count_minus_invested_upper = _sharp_linear_bounds(
        frame, count_minus_invested_coefficients
    )
    count_minus_fixed_coefficients = (
        np.full(n_selected, 1.0 / n_selected) - exposure / committed_capital_usd
    )
    count_minus_fixed_lower, count_minus_fixed_upper = _sharp_linear_bounds(
        frame, count_minus_fixed_coefficients
    )
    resolved = frame["outcome_resolved"].to_numpy(dtype=bool)
    return {
        "selected_positions": int(n_selected),
        "funded_dollars": funded_dollars,
        "committed_capital_usd": committed_capital_usd,
        "cash_residual_usd": committed_capital_usd - funded_dollars,
        "resolved_positions": int(resolved.sum()),
        "unresolved_positions": int((~resolved).sum()),
        "empty_set_positions": int(frame["set_empty"].sum()),
        "full_set_positions": int(frame["set_full"].sum()),
        "singleton_zero_positions": int(frame["set_singleton_zero"].sum()),
        "singleton_one_positions": int(frame["set_singleton_one"].sum()),
        "count_selected_fcp_lower": count_fcp_lower,
        "count_selected_fcp_upper": count_fcp_upper,
        "count_selected_coverage_lower": 1.0 - count_fcp_upper,
        "count_selected_coverage_upper": 1.0 - count_fcp_lower,
        "invested_dollar_selected_fcp_lower": dollar_fcp_lower,
        "invested_dollar_selected_fcp_upper": dollar_fcp_upper,
        "invested_dollar_selected_coverage_lower": 1.0 - dollar_fcp_upper,
        "invested_dollar_selected_coverage_upper": 1.0 - dollar_fcp_lower,
        "fixed_capital_decision_fcp_lower": fixed_fcp_lower,
        "fixed_capital_decision_fcp_upper": fixed_fcp_upper,
        "fixed_capital_decision_coverage_lower": 1.0 - fixed_fcp_upper,
        "fixed_capital_decision_coverage_upper": 1.0 - fixed_fcp_lower,
        "count_selected_minus_invested_dollar_selected_fcp_lower": (count_minus_invested_lower),
        "count_selected_minus_invested_dollar_selected_fcp_upper": (count_minus_invested_upper),
        "count_selected_minus_invested_dollar_selected_coverage_lower": (
            -count_minus_invested_upper
        ),
        "count_selected_minus_invested_dollar_selected_coverage_upper": (
            -count_minus_invested_lower
        ),
        "count_selected_minus_fixed_capital_decision_fcp_lower": count_minus_fixed_lower,
        "count_selected_minus_fixed_capital_decision_fcp_upper": count_minus_fixed_upper,
        "count_selected_minus_fixed_capital_decision_coverage_lower": (-count_minus_fixed_upper),
        "count_selected_minus_fixed_capital_decision_coverage_upper": (-count_minus_fixed_lower),
        "sharpness": "cellwise_shared_binary_completion",
    }


def _summarize_policies(
    frame: pd.DataFrame, *, keys: Sequence[str], committed_budget_usd: float
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for raw_keys, group in frame.groupby(list(keys), observed=True, sort=True):
        values = raw_keys if isinstance(raw_keys, tuple) else (raw_keys,)
        row = {str(key): value for key, value in zip(keys, values, strict=True)}
        period_count = int(group["period"].nunique())
        row.update(_policy_record(group, committed_capital_usd=committed_budget_usd * period_count))
        row["periods"] = period_count
        rows.append(row)
    return pd.DataFrame(rows).sort_values(list(keys), kind="stable").reset_index(drop=True)


def _coalesced_union(policy_zero: pd.DataFrame, policy_one: pd.DataFrame) -> pd.DataFrame:
    identity = ["id", "period"]
    columns = [
        *identity,
        "funded_exposure",
        "snapshot_default",
        "outcome_resolved",
        "miss_zero",
        "miss_one",
        "conformal_lower",
        "conformal_upper",
    ]
    left = policy_zero.loc[:, columns].rename(
        columns={column: f"{column}_g0" for column in columns if column not in identity}
    )
    right = policy_one.loc[:, columns].rename(
        columns={column: f"{column}_g1" for column in columns if column not in identity}
    )
    union = left.merge(right, on=identity, how="outer", validate="one_to_one", indicator=True)
    overlap = union["_merge"].eq("both")
    for column in ("snapshot_default", "outcome_resolved", "miss_zero", "miss_one"):
        left_values = union.loc[overlap, f"{column}_g0"]
        right_values = union.loc[overlap, f"{column}_g1"]
        if not bool(left_values.fillna(-9).eq(right_values.fillna(-9)).all()):
            raise RuntimeError(f"Gamma policies disagree on shared loan field {column!r}.")
    for column in ("conformal_lower", "conformal_upper"):
        left_values = pd.to_numeric(union.loc[overlap, f"{column}_g0"], errors="raise")
        right_values = pd.to_numeric(union.loc[overlap, f"{column}_g1"], errors="raise")
        if not np.array_equal(
            left_values.to_numpy(dtype=float), right_values.to_numpy(dtype=float)
        ):
            raise RuntimeError("Gamma policies disagree on shared-loan conformal endpoints.")
    for column in ("snapshot_default", "outcome_resolved", "miss_zero", "miss_one"):
        union[column] = union[f"{column}_g1"].combine_first(union[f"{column}_g0"])
    union["exposure_g0"] = union["funded_exposure_g0"].fillna(0.0).astype(float)
    union["exposure_g1"] = union["funded_exposure_g1"].fillna(0.0).astype(float)
    union["selected_g0"] = union["_merge"].isin(["left_only", "both"])
    union["selected_g1"] = union["_merge"].isin(["right_only", "both"])
    return union


def _direction(lower: float, upper: float, *, tolerance: float = 1.0e-12) -> str:
    if lower > tolerance:
        return "higher"
    if upper < -tolerance:
        return "lower"
    if abs(lower) <= tolerance and abs(upper) <= tolerance:
        return "zero"
    return "crossing"


def _gamma_contrast_record(
    policy_zero: pd.DataFrame,
    policy_one: pd.DataFrame,
    *,
    committed_capital_usd: float,
) -> dict[str, Any]:
    union = _coalesced_union(policy_zero, policy_one)
    n_zero = len(policy_zero)
    n_one = len(policy_one)
    dollars_zero = float(policy_zero["funded_exposure"].sum())
    dollars_one = float(policy_one["funded_exposure"].sum())
    if min(n_zero, n_one) <= 0 or min(dollars_zero, dollars_one) <= 0.0:
        raise RuntimeError("Both gamma policies must have positive support and capital.")

    count_coefficients = (
        union["selected_g1"].to_numpy(dtype=float) / n_one
        - union["selected_g0"].to_numpy(dtype=float) / n_zero
    )
    dollar_coefficients = (
        union["exposure_g1"].to_numpy(dtype=float) / dollars_one
        - union["exposure_g0"].to_numpy(dtype=float) / dollars_zero
    )
    fixed_capital_coefficients = (
        union["exposure_g1"].to_numpy(dtype=float) - union["exposure_g0"].to_numpy(dtype=float)
    ) / committed_capital_usd
    count_lower, count_upper = _sharp_linear_bounds(union, count_coefficients)
    dollar_lower, dollar_upper = _sharp_linear_bounds(union, dollar_coefficients)
    fixed_lower, fixed_upper = _sharp_linear_bounds(union, fixed_capital_coefficients)
    unresolved = ~union["outcome_resolved"].to_numpy(dtype=bool)
    return {
        "gamma0_candidate_id": str(policy_zero["candidate_id"].iloc[0]),
        "gamma1_candidate_id": str(policy_one["candidate_id"].iloc[0]),
        "gamma0_selected_positions": int(n_zero),
        "gamma1_selected_positions": int(n_one),
        "gamma0_funded_dollars": dollars_zero,
        "gamma1_funded_dollars": dollars_one,
        "committed_capital_usd": committed_capital_usd,
        "funded_union_positions": int(len(union)),
        "funded_overlap_positions": int(union["_merge"].eq("both").sum()),
        "unresolved_union_positions": int(unresolved.sum()),
        "gamma1_minus_gamma0_count_selected_fcp_lower": count_lower,
        "gamma1_minus_gamma0_count_selected_fcp_upper": count_upper,
        "gamma1_minus_gamma0_count_selected_coverage_lower": -count_upper,
        "gamma1_minus_gamma0_count_selected_coverage_upper": -count_lower,
        "gamma1_minus_gamma0_count_selected_fcp_direction": _direction(count_lower, count_upper),
        "gamma1_minus_gamma0_invested_dollar_selected_fcp_lower": dollar_lower,
        "gamma1_minus_gamma0_invested_dollar_selected_fcp_upper": dollar_upper,
        "gamma1_minus_gamma0_invested_dollar_selected_coverage_lower": -dollar_upper,
        "gamma1_minus_gamma0_invested_dollar_selected_coverage_upper": -dollar_lower,
        "gamma1_minus_gamma0_invested_dollar_selected_fcp_direction": _direction(
            dollar_lower, dollar_upper
        ),
        "gamma1_minus_gamma0_fixed_capital_decision_fcp_lower": fixed_lower,
        "gamma1_minus_gamma0_fixed_capital_decision_fcp_upper": fixed_upper,
        "gamma1_minus_gamma0_fixed_capital_decision_coverage_lower": -fixed_upper,
        "gamma1_minus_gamma0_fixed_capital_decision_coverage_upper": -fixed_lower,
        "gamma1_minus_gamma0_fixed_capital_decision_fcp_direction": _direction(
            fixed_lower, fixed_upper
        ),
        "sharpness": "cellwise_shared_binary_completion",
    }


def _gamma_contrasts(
    frame: pd.DataFrame, *, keys: Sequence[str], committed_budget_usd: float
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for raw_keys, group in frame.groupby(list(keys), observed=True, sort=True):
        gamma_values = sorted(group["gamma"].astype(float).unique().tolist())
        if gamma_values != [0.0, 1.0]:
            raise RuntimeError("A gamma contrast cell does not contain both locked endpoints.")
        policy_zero = group.loc[group["gamma"].astype(float).eq(0.0)].copy()
        policy_one = group.loc[group["gamma"].astype(float).eq(1.0)].copy()
        if policy_zero["candidate_id"].nunique() != 1 or policy_one["candidate_id"].nunique() != 1:
            raise RuntimeError("A gamma contrast cell aliases multiple policies per endpoint.")
        values = raw_keys if isinstance(raw_keys, tuple) else (raw_keys,)
        row = {str(key): value for key, value in zip(keys, values, strict=True)}
        period_count = int(group["period"].nunique())
        row.update(
            _gamma_contrast_record(
                policy_zero,
                policy_one,
                committed_capital_usd=committed_budget_usd * period_count,
            )
        )
        row["periods"] = period_count
        rows.append(row)
    return pd.DataFrame(rows).sort_values(list(keys), kind="stable").reset_index(drop=True)


def _reconcile_support_and_fixed_capital_to_v3(
    rounded: pd.DataFrame,
    continuous: pd.DataFrame,
    registered: pd.DataFrame,
    *,
    committed_budget_usd: float,
    tolerance: float,
    source_rounding_tolerance: float,
) -> pd.DataFrame:
    required = {
        "window_id",
        "candidate_id",
        "frontier_ruler",
        "frontier_coordinate",
        "gamma",
        "periods",
        "role",
        "weighted_miscoverage_difference_lower",
        "weighted_miscoverage_difference_upper",
        "contrast",
        "policy_a",
        "policy_b",
        "policy_a_normalization_capital",
        "policy_b_normalization_capital",
    }
    _require_columns(registered, required, label="Registered V3 granularity contrasts")
    if bool(registered.duplicated(["window_id", "candidate_id"]).any()):
        raise RuntimeError("Registered V3 granularity contrasts duplicate a policy track.")
    rows: list[dict[str, Any]] = []
    for (window_id, candidate_id), rounded_track in rounded.groupby(
        ["window_id", "candidate_id"], observed=True, sort=True
    ):
        continuous_track = continuous.loc[
            continuous["window_id"].eq(window_id) & continuous["candidate_id"].eq(candidate_id)
        ].copy()
        if continuous_track.empty:
            raise RuntimeError("A rounded track has no continuous V5 parent track.")
        period_count = int(rounded_track["period"].nunique())
        committed = committed_budget_usd * period_count
        union = _coalesced_union(continuous_track, rounded_track)
        continuous_positions = int(len(continuous_track))
        rounded_positions = int(len(rounded_track))
        removed_positions = int(union["_merge"].eq("left_only").sum())
        added_positions = int(union["_merge"].eq("right_only").sum())
        if added_positions:
            raise RuntimeError("A rounded policy support contains a non-parent position.")
        count_coefficients = (
            union["selected_g1"].to_numpy(dtype=float) / rounded_positions
            - union["selected_g0"].to_numpy(dtype=float) / continuous_positions
        )
        count_lower, count_upper = _sharp_linear_bounds(union, count_coefficients)
        coefficients = (
            union["exposure_g1"].to_numpy(dtype=float) - union["exposure_g0"].to_numpy(dtype=float)
        ) / committed
        recomputed_lower, recomputed_upper = _sharp_linear_bounds(union, coefficients)
        reference = registered.loc[
            registered["window_id"].eq(window_id) & registered["candidate_id"].eq(candidate_id)
        ]
        if len(reference) != 1:
            raise RuntimeError("A registered V3 track is absent or duplicated.")
        record = reference.iloc[0]
        metadata_matches = (
            str(record["role"]) == str(rounded_track["role"].iloc[0])
            and str(record["frontier_ruler"]) == str(rounded_track["frontier_ruler"].iloc[0])
            and np.isclose(
                float(record["frontier_coordinate"]),
                float(rounded_track["frontier_coordinate"].iloc[0]),
                rtol=0.0,
                atol=tolerance,
            )
            and np.isclose(
                float(record["gamma"]),
                float(rounded_track["gamma"].iloc[0]),
                rtol=0.0,
                atol=tolerance,
            )
            and int(record["periods"]) == period_count
            and str(record["contrast"]) == "rounded_lot_minus_continuous"
            and str(record["policy_a"]) == "rounded_lot"
            and str(record["policy_b"]) == "continuous"
            and np.isclose(
                float(record["policy_a_normalization_capital"]),
                committed,
                rtol=0.0,
                atol=tolerance,
            )
            and np.isclose(
                float(record["policy_b_normalization_capital"]),
                committed,
                rtol=0.0,
                atol=tolerance,
            )
        )
        if not metadata_matches:
            raise RuntimeError("Registered V3 reconciliation metadata changed.")
        source_lower = float(record["weighted_miscoverage_difference_lower"])
        source_upper = float(record["weighted_miscoverage_difference_upper"])
        if not np.isclose(
            recomputed_lower, source_lower, rtol=0.0, atol=tolerance
        ) or not np.isclose(recomputed_upper, source_upper, rtol=0.0, atol=tolerance):
            raise RuntimeError("Fixed-capital recomputation does not reconcile to V3.")
        rows.append(
            {
                "window_id": str(window_id),
                "candidate_id": str(candidate_id),
                "role": str(rounded_track["role"].iloc[0]),
                "frontier_ruler": str(rounded_track["frontier_ruler"].iloc[0]),
                "frontier_coordinate": float(rounded_track["frontier_coordinate"].iloc[0]),
                "gamma": float(rounded_track["gamma"].iloc[0]),
                "periods": period_count,
                "committed_capital_usd": committed,
                "continuous_selected_positions": continuous_positions,
                "rounded_selected_positions": rounded_positions,
                "removed_selected_positions": removed_positions,
                "added_selected_positions": added_positions,
                "rounding_changed_positions": int(
                    (
                        np.abs(
                            rounded_track["funded_exposure"].to_numpy(dtype=float)
                            - pd.to_numeric(
                                rounded_track["source_exposure"], errors="raise"
                            ).to_numpy(dtype=float)
                        )
                        > source_rounding_tolerance
                    ).sum()
                )
                + removed_positions,
                "rounded_minus_continuous_count_selected_fcp_lower": count_lower,
                "rounded_minus_continuous_count_selected_fcp_upper": count_upper,
                "rounded_minus_continuous_count_selected_coverage_lower": -count_upper,
                "rounded_minus_continuous_count_selected_coverage_upper": -count_lower,
                "rounded_minus_continuous_count_selected_fcp_direction": _direction(
                    count_lower, count_upper
                ),
                "registered_v3_rounded_minus_continuous_fixed_capital_fcp_lower": source_lower,
                "registered_v3_rounded_minus_continuous_fixed_capital_fcp_upper": source_upper,
                "recomputed_rounded_minus_continuous_fixed_capital_fcp_lower": (recomputed_lower),
                "recomputed_rounded_minus_continuous_fixed_capital_fcp_upper": (recomputed_upper),
                "lower_absolute_difference": abs(recomputed_lower - source_lower),
                "upper_absolute_difference": abs(recomputed_upper - source_upper),
                "exact_within_locked_tolerance": True,
            }
        )
    result = (
        pd.DataFrame(rows)
        .sort_values(["window_id", "candidate_id"], kind="stable")
        .reset_index(drop=True)
    )
    if len(result) != len(registered):
        raise RuntimeError("V3 reconciliation did not retain the complete track census.")
    return result
