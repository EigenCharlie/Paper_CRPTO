"""Coverage audits and exact selection-transport decompositions."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd

from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    assign_conformal_groups,
)


def binary_miscoverage_bounds(
    outcomes: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Return sharp binary-outcome miscoverage bounds for nullable outcomes."""
    y_true = np.asarray(outcomes, dtype=float)
    low = np.asarray(lower, dtype=float)
    high = np.asarray(upper, dtype=float)
    if not (y_true.shape == low.shape == high.shape):
        raise ValueError("Outcome and interval arrays must align.")
    observed = np.isfinite(y_true)
    miss_observed = (y_true < low) | (y_true > high)
    miss_zero = (low > 0.0) | (high < 0.0)
    miss_one = (low > 1.0) | (high < 1.0)
    bound_low = np.where(observed, miss_observed, np.minimum(miss_zero, miss_one))
    bound_high = np.where(observed, miss_observed, np.maximum(miss_zero, miss_one))
    return bound_low.astype(float), bound_high.astype(float)


def _coverage_summary(
    subset: pd.DataFrame,
    *,
    design_split: str,
    period: str,
    group_label: str,
) -> dict[str, Any]:
    y_true = pd.to_numeric(subset["snapshot_default"], errors="coerce").to_numpy(dtype=float)
    lower = subset["conformal_lower"].to_numpy(dtype=float)
    upper = subset["conformal_upper"].to_numpy(dtype=float)
    miss_low, miss_high = binary_miscoverage_bounds(y_true, lower, upper)
    resolved = np.isfinite(y_true)
    resolved_coverage = float(1.0 - miss_low[resolved].mean()) if bool(resolved.any()) else None
    return {
        "design_split": design_split,
        "period": period,
        "conformal_group": group_label,
        "rows": int(len(subset)),
        "resolved_rows": int(resolved.sum()),
        "unresolved_rows": int((~resolved).sum()),
        "resolved_empirical_coverage": resolved_coverage,
        "all_candidate_coverage_lower": float(1.0 - miss_high.mean()),
        "all_candidate_coverage_upper": float(1.0 - miss_low.mean()),
        "all_candidate_miscoverage_lower": float(miss_low.mean()),
        "all_candidate_miscoverage_upper": float(miss_high.mean()),
        "mean_interval_width": float((upper - lower).mean()),
        "lower_endpoint_zero_share": float(np.mean(lower <= 1e-12)),
        "upper_endpoint_one_share": float(np.mean(upper >= 1.0 - 1e-12)),
        "pd_point_min": float(subset["pd_point"].min()),
        "pd_point_max": float(subset["pd_point"].max()),
        "below_fit_score_range": int(subset["below_fit_score_range"].sum()),
        "above_fit_score_range": int(subset["above_fit_score_range"].sum()),
    }


def build_temporal_conformal_audit(
    decision_frame: pd.DataFrame,
    outcomes: pd.DataFrame,
    recipe: BinaryOutcomeConformalRecipe,
) -> pd.DataFrame:
    """Audit marginal coverage by month and score stratum after freezing."""
    merged = decision_frame.merge(outcomes, on="id", how="left", validate="one_to_one")
    if bool(merged["snapshot_resolution"].isna().any()):
        raise RuntimeError("Temporal conformal audit could not align all outcomes.")
    merged["period"] = pd.to_datetime(merged["issue_d"]).dt.to_period("M").astype(str)
    point = merged["pd_point"].to_numpy(dtype=float)
    assigned = assign_conformal_groups(point, recipe.bin_edges)
    if not np.array_equal(assigned, merged["conformal_group"].to_numpy(dtype=int)):
        raise AssertionError("Stored groups do not match the frozen conformal recipe.")
    merged["below_fit_score_range"] = point < float(recipe.bin_edges[0])
    merged["above_fit_score_range"] = point > float(recipe.bin_edges[-1])

    rows: list[dict[str, Any]] = []
    splits = sorted(merged["design_split"].astype(str).unique())
    for design_split in splits:
        split_frame = merged.loc[merged["design_split"].astype(str).eq(design_split)]
        periods = sorted(split_frame["period"].astype(str).unique())
        for period in periods:
            month = split_frame.loc[split_frame["period"].astype(str).eq(period)]
            rows.append(
                _coverage_summary(
                    month,
                    design_split=design_split,
                    period=period,
                    group_label="ALL",
                )
            )
            for group in sorted(month["conformal_group"].astype(int).unique()):
                group_frame = month.loc[month["conformal_group"].eq(group)]
                rows.append(
                    _coverage_summary(
                        group_frame,
                        design_split=design_split,
                        period=period,
                        group_label=f"score_q{int(group):02d}",
                    )
                )
        pooled_period = f"{periods[0]}_to_{periods[-1]}"
        rows.append(
            _coverage_summary(
                split_frame,
                design_split=design_split,
                period=pooled_period,
                group_label="ALL",
            )
        )
        for group in sorted(split_frame["conformal_group"].astype(int).unique()):
            group_frame = split_frame.loc[split_frame["conformal_group"].eq(group)]
            rows.append(
                _coverage_summary(
                    group_frame,
                    design_split=design_split,
                    period=pooled_period,
                    group_label=f"score_q{int(group):02d}",
                )
            )
    return (
        pd.DataFrame(rows)
        .sort_values(
            ["design_split", "period", "conformal_group"],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    total = float(weights.sum())
    if total <= 0.0:
        raise ValueError("Transport decomposition weights must sum to a positive value.")
    return float(weights @ values / total)


def metric_transport_decomposition(
    *,
    metric_name: str,
    candidate_values: np.ndarray,
    candidate_exposure: np.ndarray,
    candidate_groups: np.ndarray,
    funded_values: np.ndarray,
    funded_exposure: np.ndarray,
    funded_groups: np.ndarray,
    reference: float | None = None,
) -> dict[str, float | str]:
    """Decompose row, exposure, group-composition, and within-group shifts."""
    values = np.asarray(candidate_values, dtype=float)
    exposure = np.asarray(candidate_exposure, dtype=float)
    groups = np.asarray(candidate_groups, dtype=int)
    selected_values = np.asarray(funded_values, dtype=float)
    selected_exposure = np.asarray(funded_exposure, dtype=float)
    selected_groups = np.asarray(funded_groups, dtype=int)
    if not (len(values) == len(exposure) == len(groups)):
        raise ValueError("Candidate transport arrays must align.")
    if not (len(selected_values) == len(selected_exposure) == len(selected_groups)):
        raise ValueError("Funded transport arrays must align.")
    arrays = [values, exposure, selected_values, selected_exposure]
    if any(not bool(np.isfinite(array).all()) for array in arrays):
        raise ValueError("Exact transport decomposition requires finite values.")

    row_value = float(values.mean())
    exposure_value = _weighted_mean(values, exposure)
    funded_value = _weighted_mean(selected_values, selected_exposure)
    funded_total = float(selected_exposure.sum())
    group_mix_value = 0.0
    for group in sorted(set(selected_groups.tolist())):
        candidate_mask = groups == group
        funded_mask = selected_groups == group
        if not bool(candidate_mask.any()):
            raise ValueError(f"Funded conformal group {group} is absent from candidates.")
        candidate_group_rate = _weighted_mean(values[candidate_mask], exposure[candidate_mask])
        funded_group_share = float(selected_exposure[funded_mask].sum() / funded_total)
        group_mix_value += funded_group_share * candidate_group_rate

    reference_value = row_value if reference is None else float(reference)
    row_minus_reference = row_value - reference_value
    row_to_exposure = exposure_value - row_value
    group_composition = group_mix_value - exposure_value
    within_group_selection = funded_value - group_mix_value
    total = funded_value - reference_value
    reconstructed = (
        row_minus_reference + row_to_exposure + group_composition + within_group_selection
    )
    return {
        "metric": metric_name,
        "reference": reference_value,
        "candidate_row": row_value,
        "candidate_exposure_weighted": exposure_value,
        "funded_group_mix_counterfactual": group_mix_value,
        "funded_exposure_weighted": funded_value,
        "row_minus_reference": row_minus_reference,
        "row_to_exposure": row_to_exposure,
        "group_composition": group_composition,
        "within_group_selection": within_group_selection,
        "total_minus_reference": total,
        "identity_residual": total - reconstructed,
    }


def coverage_and_default_transport_decomposition(
    candidates_with_outcomes: pd.DataFrame,
    funded_allocations: pd.DataFrame,
    *,
    alpha: float,
) -> pd.DataFrame:
    """Return exact miscoverage and default transport identities."""
    candidate_y = pd.to_numeric(
        candidates_with_outcomes["snapshot_default"], errors="coerce"
    ).to_numpy(dtype=float)
    funded_y = pd.to_numeric(funded_allocations["snapshot_default"], errors="coerce").to_numpy(
        dtype=float
    )
    if not bool(np.isfinite(candidate_y).all()) or not bool(np.isfinite(funded_y).all()):
        raise ValueError("Exact transport decomposition cannot include unresolved outcomes.")
    candidate_miss, _ = binary_miscoverage_bounds(
        candidate_y,
        candidates_with_outcomes["conformal_lower"].to_numpy(dtype=float),
        candidates_with_outcomes["conformal_upper"].to_numpy(dtype=float),
    )
    funded_miss, _ = binary_miscoverage_bounds(
        funded_y,
        funded_allocations["conformal_lower"].to_numpy(dtype=float),
        funded_allocations["conformal_upper"].to_numpy(dtype=float),
    )
    candidate_exposure = candidates_with_outcomes["loan_amnt"].to_numpy(dtype=float)
    candidate_groups = candidates_with_outcomes["conformal_group"].to_numpy(dtype=int)
    funded_exposure = funded_allocations["exposure"].to_numpy(dtype=float)
    funded_groups = funded_allocations["conformal_group"].to_numpy(dtype=int)
    records = [
        metric_transport_decomposition(
            metric_name="binary_miscoverage",
            candidate_values=candidate_miss,
            candidate_exposure=candidate_exposure,
            candidate_groups=candidate_groups,
            funded_values=funded_miss,
            funded_exposure=funded_exposure,
            funded_groups=funded_groups,
            reference=float(alpha),
        ),
        metric_transport_decomposition(
            metric_name="snapshot_default",
            candidate_values=candidate_y,
            candidate_exposure=candidate_exposure,
            candidate_groups=candidate_groups,
            funded_values=funded_y,
            funded_exposure=funded_exposure,
            funded_groups=funded_groups,
        ),
    ]
    result = pd.DataFrame(records)
    if bool((result["identity_residual"].abs() > 1e-12).any()):
        raise AssertionError("Transport decomposition identity did not reconcile.")
    return result


def weighted_group_shares(
    groups: Sequence[int],
    exposure: Sequence[float],
) -> dict[str, float]:
    """Return deterministic exposure shares by conformal group."""
    group_array = np.asarray(tuple(groups), dtype=int)
    exposure_array = np.asarray(tuple(exposure), dtype=float)
    total = float(exposure_array.sum())
    if total <= 0.0 or len(group_array) != len(exposure_array):
        raise ValueError("Group shares require aligned positive exposure.")
    return {
        f"score_q{int(group):02d}": float(exposure_array[group_array == group].sum() / total)
        for group in sorted(set(group_array.tolist()))
    }
