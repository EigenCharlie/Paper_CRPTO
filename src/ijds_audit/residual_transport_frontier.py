"""Finite-archive residual-distribution transport diagnostics.

This module computes descriptive, directional empirical-CDF discrepancies
between frozen conformal-fit residuals and the fixed primary-OOT archive.  It
does not test exchangeability, transport coverage validity, or any policy
claim.  Unresolved binary outcomes are handled by sharp endpoint completions
of their two possible absolute residuals.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from src.ijds_audit.common_panel_threshold_response import validate_residual_fit_audit
from src.ijds_audit.grid_contracts import require_exact_grid, require_unique_row
from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    assign_conformal_groups,
)

_REFERENCE_COLUMNS = {
    "learner",
    "window_id",
    "taxonomy_groups",
    "conformal_group",
    "role",
    "candidate_rows",
    "resolved_rows",
    "unresolved_rows",
    "resolved_misses",
    "misses_min",
    "misses_max",
    "coverage_resolved",
    "coverage_lower",
    "coverage_upper",
    "score_min",
    "score_max",
    "fit_rows",
    "fit_residual_quantile",
    "fit_score_min",
    "fit_score_max",
}

_MONTHLY_SUM_COLUMNS = (
    "target_rows",
    "resolved_rows",
    "unresolved_rows",
    "resolved_misses",
    "unresolved_misses_min",
    "unresolved_misses_max",
    "misses_min",
    "misses_max",
)


def _unit_interval_array(
    values: Sequence[float] | np.ndarray,
    *,
    label: str,
    allow_empty: bool = False,
) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{label} must be one-dimensional.")
    if not allow_empty and len(array) == 0:
        raise ValueError(f"{label} must be nonempty.")
    if not np.isfinite(array).all() or np.any((array < 0.0) | (array > 1.0)):
        raise ValueError(f"{label} must contain finite values in [0, 1].")
    return array


def directional_ks(
    calibration_residuals: Sequence[float] | np.ndarray,
    target_residuals: Sequence[float] | np.ndarray,
) -> dict[str, float | int]:
    """Return both directional empirical-CDF suprema and finite witnesses.

    ``calibration_minus_target_ks`` is ``sup_t(F_cal(t)-F_target(t))``;
    ``target_minus_calibration_ks`` reverses the subtraction.  The grid is the
    union of observed residual values.  This is a descriptive full-census
    statistic and intentionally has no p-value.
    """
    calibration = np.sort(
        _unit_interval_array(calibration_residuals, label="calibration_residuals")
    )
    target = np.sort(_unit_interval_array(target_residuals, label="target_residuals"))
    grid = np.unique(np.concatenate((calibration, target)))
    calibration_counts = np.searchsorted(calibration, grid, side="right").astype(np.int64)
    target_counts = np.searchsorted(target, grid, side="right").astype(np.int64)
    denominator = int(len(calibration) * len(target))
    calibration_numerators = calibration_counts * len(target) - target_counts * len(calibration)
    target_numerators = -calibration_numerators
    calibration_numerator = int(np.max(calibration_numerators))
    target_numerator = int(np.max(target_numerators))
    calibration_index = int(np.flatnonzero(calibration_numerators == calibration_numerator)[0])
    target_index = int(np.flatnonzero(target_numerators == target_numerator)[0])
    return {
        "calibration_minus_target_ks": calibration_numerator / denominator,
        "calibration_minus_target_witness": float(grid[calibration_index]),
        "calibration_minus_target_numerator": calibration_numerator,
        "target_minus_calibration_ks": target_numerator / denominator,
        "target_minus_calibration_witness": float(grid[target_index]),
        "target_minus_calibration_numerator": target_numerator,
        "ks_denominator": denominator,
        "ks_grid_points": int(len(grid)),
    }


def completion_directional_ks_frontier(
    calibration_residuals: Sequence[float] | np.ndarray,
    resolved_target_residuals: Sequence[float] | np.ndarray,
    unresolved_probabilities: Sequence[float] | np.ndarray,
) -> dict[str, float | int | str]:
    """Return sharp directional-KS extrema over all binary completions.

    For an unresolved score ``p``, the two possible residuals are ``p`` and
    ``1-p``.  Assigning every unresolved row its smaller residual gives the
    pointwise-largest target CDF; assigning every row its larger residual gives
    the pointwise-smallest target CDF.  Monotonicity of each directional
    supremum therefore makes these two endpoint completions globally sharp.
    No assertion is made that every value between the extrema is attainable.
    """
    calibration = _unit_interval_array(calibration_residuals, label="calibration_residuals")
    resolved = _unit_interval_array(resolved_target_residuals, label="resolved_target_residuals")
    unresolved = _unit_interval_array(
        unresolved_probabilities,
        label="unresolved_probabilities",
        allow_empty=True,
    )
    residual_if_zero = unresolved
    residual_if_one = 1.0 - unresolved
    low_completion = np.concatenate((resolved, np.minimum(residual_if_zero, residual_if_one)))
    high_completion = np.concatenate((resolved, np.maximum(residual_if_zero, residual_if_one)))

    low = directional_ks(calibration, low_completion)
    high = directional_ks(calibration, high_completion)
    calibration_min = float(low["calibration_minus_target_ks"])
    calibration_max = float(high["calibration_minus_target_ks"])
    target_min = float(high["target_minus_calibration_ks"])
    target_max = float(low["target_minus_calibration_ks"])
    denominator = int(low["ks_denominator"])
    if int(high["ks_denominator"]) != denominator:
        raise RuntimeError("Completion endpoints changed the target KS denominator.")
    calibration_min_numerator = int(low["calibration_minus_target_numerator"])
    calibration_max_numerator = int(high["calibration_minus_target_numerator"])
    target_min_numerator = int(high["target_minus_calibration_numerator"])
    target_max_numerator = int(low["target_minus_calibration_numerator"])
    if (
        calibration_min_numerator > calibration_max_numerator
        or target_min_numerator > target_max_numerator
    ):
        raise RuntimeError("Sharp completion ordering failed for directional KS.")
    if calibration_min_numerator > target_max_numerator:
        classification = "larger_target_residual_discrepancy_dominates"
    elif target_min_numerator > calibration_max_numerator:
        classification = "smaller_target_residual_discrepancy_dominates"
    else:
        classification = "directional_discrepancies_not_robustly_ordered"
    return {
        "calibration_minus_target_ks_min": calibration_min,
        "calibration_minus_target_ks_min_numerator": calibration_min_numerator,
        "calibration_minus_target_ks_min_witness": float(low["calibration_minus_target_witness"]),
        "calibration_minus_target_ks_max": calibration_max,
        "calibration_minus_target_ks_max_numerator": calibration_max_numerator,
        "calibration_minus_target_ks_max_witness": float(high["calibration_minus_target_witness"]),
        "target_minus_calibration_ks_min": target_min,
        "target_minus_calibration_ks_min_numerator": target_min_numerator,
        "target_minus_calibration_ks_min_witness": float(high["target_minus_calibration_witness"]),
        "target_minus_calibration_ks_max": target_max,
        "target_minus_calibration_ks_max_numerator": target_max_numerator,
        "target_minus_calibration_ks_max_witness": float(low["target_minus_calibration_witness"]),
        "sharp_directional_discrepancy_comparison": classification,
        "completion_directional_ks_denominator": denominator,
        "low_completion_grid_points": int(low["ks_grid_points"]),
        "high_completion_grid_points": int(high["ks_grid_points"]),
    }


def _declared_tuple(values: Sequence[str], *, label: str, length: int) -> tuple[str, ...]:
    declared = tuple(str(value) for value in values)
    if len(declared) != length or len(set(declared)) != length or any(not x for x in declared):
        raise ValueError(f"{label} must contain exactly {length} distinct nonempty values.")
    return declared


def _expected_count(value: int, *, label: str) -> int:
    if isinstance(value, (bool, np.bool_)) or int(value) != value or int(value) < 0:
        raise ValueError(f"{label} must be a nonnegative integer.")
    return int(value)


def _exact_integer(value: Any, *, label: str) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise RuntimeError(f"{label} is not an integer count.")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{label} is not numeric.") from exc
    if not np.isfinite(numeric) or not numeric.is_integer():
        raise RuntimeError(f"{label} is not an exact finite integer.")
    return int(numeric)


def _require_close(actual: float, expected: Any, *, label: str, tolerance: float) -> None:
    try:
        reference = float(expected)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{label} is not numeric in the reference.") from exc
    if not np.isfinite(actual) or not np.isfinite(reference):
        raise RuntimeError(f"{label} is nonfinite.")
    if not np.isclose(actual, reference, atol=tolerance, rtol=0.0):
        raise RuntimeError(f"{label} did not reconcile: {actual!r} != {reference!r}.")


def _hash_strings(values: np.ndarray) -> str:
    digest = hashlib.sha256()
    for value in values:
        encoded = str(value).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, byteorder="little", signed=False))
        digest.update(encoded)
    return digest.hexdigest()


def _validate_endpoint_panel(
    scores: pd.DataFrame,
    outcomes: pd.DataFrame,
    *,
    learners: tuple[str, ...],
    role: str,
    issue_months: tuple[str, ...],
    expected: Mapping[str, int],
) -> pd.DataFrame:
    required_scores = {"id", "issue_d", "design_split", *(f"pd_{x}" for x in learners)}
    if missing := sorted(required_scores.difference(scores.columns)):
        raise ValueError(f"Frozen scores omit columns: {missing}.")
    if not {"id", "snapshot_default"}.issubset(outcomes.columns):
        raise ValueError("Endpoint outcomes must contain id and snapshot_default.")

    panel = scores.loc[scores["design_split"].eq(role)].copy()
    if panel["id"].isna().any() or panel["id"].duplicated().any():
        raise RuntimeError("Fixed-panel score IDs are missing or duplicated.")
    panel["_canonical_id"] = panel["id"].astype(str)
    if panel["_canonical_id"].eq("").any() or panel["_canonical_id"].duplicated().any():
        raise RuntimeError("Fixed-panel score IDs collide after canonicalization.")
    panel["issue_month"] = (
        pd.to_datetime(panel["issue_d"], errors="raise").dt.to_period("M").astype(str)
    )
    actual_months = tuple(sorted(panel["issue_month"].unique()))
    if actual_months != issue_months:
        raise RuntimeError(f"Fixed-panel issue months changed: {actual_months!r}.")
    if len(panel) != expected["candidate"]:
        raise RuntimeError("Fixed-panel candidate census changed.")

    endpoint = outcomes.loc[:, ["id", "snapshot_default"]].copy()
    if endpoint["id"].isna().any() or endpoint["id"].duplicated().any():
        raise RuntimeError("Endpoint outcomes contain missing or duplicate IDs.")
    panel = panel.merge(endpoint, on="id", how="left", validate="one_to_one", indicator=True)
    if not panel["_merge"].eq("both").all():
        examples = panel.loc[~panel["_merge"].eq("both"), "id"].head(5).astype(str).tolist()
        raise RuntimeError(f"Endpoint alignment is incomplete; examples={examples!r}.")
    panel = panel.drop(columns="_merge")
    raw = panel["snapshot_default"]
    labels = pd.to_numeric(raw, errors="coerce").to_numpy(dtype=float)
    invalid_nonmissing = raw.notna().to_numpy(dtype=bool) & np.isnan(labels)
    if invalid_nonmissing.any() or np.isinf(labels).any():
        raise RuntimeError("Endpoint contains a nonnumeric or infinite outcome.")
    resolved = np.isfinite(labels)
    if not np.isin(labels[resolved], (0.0, 1.0)).all():
        raise RuntimeError("Resolved endpoint contains a nonbinary outcome.")
    actual = {
        "candidate": int(len(panel)),
        "resolved": int(resolved.sum()),
        "unresolved": int((~resolved).sum()),
        "resolved_y0": int(np.sum(labels == 0.0)),
        "resolved_y1": int(np.sum(labels == 1.0)),
    }
    if actual != dict(expected):
        raise RuntimeError(f"Fixed-panel endpoint census changed: {actual!r} != {expected!r}.")
    panel["_label"] = labels
    return panel.sort_values("_canonical_id", kind="stable").reset_index(drop=True)


def _prepare_reference(
    reference: pd.DataFrame,
    *,
    learners: tuple[str, ...],
    windows: tuple[str, ...],
    taxonomy_groups: int,
    role: str,
) -> pd.DataFrame:
    if missing := sorted(_REFERENCE_COLUMNS.difference(reference.columns)):
        raise ValueError(f"V5/exchangeability reference omits columns: {missing}.")
    selected = reference.loc[
        reference["role"].eq(role)
        & reference["taxonomy_groups"].eq(taxonomy_groups)
        & reference["learner"].isin(learners)
        & reference["window_id"].isin(windows)
        & reference["conformal_group"].isin(range(taxonomy_groups))
    ].copy()
    require_exact_grid(
        selected,
        domains={
            "learner": learners,
            "window_id": windows,
            "conformal_group": tuple(range(taxonomy_groups)),
        },
        label="residual-transport V5 reference",
    )
    return selected


def _cell_statistics(
    *,
    calibration_residuals: np.ndarray,
    resolved_target_residuals: np.ndarray,
    unresolved_probabilities: np.ndarray,
    target_scores: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    if len(resolved_target_residuals) == 0:
        raise RuntimeError("Every residual-transport cell must contain a resolved target row.")
    if len(target_scores) != len(resolved_target_residuals) + len(unresolved_probabilities):
        raise RuntimeError("Target residual cell arrays are not aligned.")
    resolved_ks = directional_ks(calibration_residuals, resolved_target_residuals)
    frontier = completion_directional_ks_frontier(
        calibration_residuals,
        resolved_target_residuals,
        unresolved_probabilities,
    )
    residual_if_zero = unresolved_probabilities
    residual_if_one = 1.0 - unresolved_probabilities
    miss_if_zero = residual_if_zero > threshold
    miss_if_one = residual_if_one > threshold
    resolved_misses = int(np.sum(resolved_target_residuals > threshold))
    unresolved_misses_min = int(np.sum(np.minimum(miss_if_zero, miss_if_one)))
    unresolved_misses_max = int(np.sum(np.maximum(miss_if_zero, miss_if_one)))
    misses_min = resolved_misses + unresolved_misses_min
    misses_max = resolved_misses + unresolved_misses_max
    target_rows = int(len(target_scores))
    resolved_rows = int(len(resolved_target_residuals))
    if not 0 <= misses_min <= misses_max <= target_rows:
        raise RuntimeError("Completion miss extrema left their exact count domain.")
    return {
        "target_rows": target_rows,
        "resolved_rows": resolved_rows,
        "unresolved_rows": int(len(unresolved_probabilities)),
        "score_min": float(np.min(target_scores)),
        "score_max": float(np.max(target_scores)),
        "fit_residual_quantile": float(threshold),
        "fit_cdf_at_quantile": float(np.mean(calibration_residuals <= threshold)),
        "resolved_target_cdf_at_quantile": float(np.mean(resolved_target_residuals <= threshold)),
        "all_target_cdf_at_quantile_min": 1.0 - misses_max / target_rows,
        "all_target_cdf_at_quantile_max": 1.0 - misses_min / target_rows,
        "resolved_misses": resolved_misses,
        "unresolved_misses_min": unresolved_misses_min,
        "unresolved_misses_max": unresolved_misses_max,
        "misses_min": misses_min,
        "misses_max": misses_max,
        "coverage_resolved": 1.0 - resolved_misses / resolved_rows,
        "coverage_lower": 1.0 - misses_max / target_rows,
        "coverage_upper": 1.0 - misses_min / target_rows,
        "resolved_calibration_minus_target_ks": float(resolved_ks["calibration_minus_target_ks"]),
        "resolved_calibration_minus_target_witness": float(
            resolved_ks["calibration_minus_target_witness"]
        ),
        "resolved_calibration_minus_target_numerator": int(
            resolved_ks["calibration_minus_target_numerator"]
        ),
        "resolved_target_minus_calibration_ks": float(resolved_ks["target_minus_calibration_ks"]),
        "resolved_target_minus_calibration_witness": float(
            resolved_ks["target_minus_calibration_witness"]
        ),
        "resolved_target_minus_calibration_numerator": int(
            resolved_ks["target_minus_calibration_numerator"]
        ),
        "resolved_directional_ks_denominator": int(resolved_ks["ks_denominator"]),
        "resolved_ks_grid_points": int(resolved_ks["ks_grid_points"]),
        **frontier,
    }


def _reconcile_pooled_reference(
    record: Mapping[str, Any],
    reference: pd.Series,
    *,
    label: str,
    tolerance: float,
) -> None:
    integer_pairs = {
        "candidate_rows": "target_rows",
        "resolved_rows": "resolved_rows",
        "unresolved_rows": "unresolved_rows",
        "resolved_misses": "resolved_misses",
        "misses_min": "misses_min",
        "misses_max": "misses_max",
        "fit_rows": "fit_rows",
    }
    for reference_name, record_name in integer_pairs.items():
        expected = _exact_integer(reference[reference_name], label=f"{label} {reference_name}")
        actual = int(record[record_name])
        if actual != expected:
            raise RuntimeError(f"{label} {reference_name} changed: {actual} != {expected}.")
    for field in (
        "coverage_resolved",
        "coverage_lower",
        "coverage_upper",
        "score_min",
        "score_max",
        "fit_residual_quantile",
        "fit_score_min",
        "fit_score_max",
    ):
        _require_close(
            float(record[field]),
            reference[field],
            label=f"{label} {field}",
            tolerance=tolerance,
        )


def build_residual_transport_frontier(
    scores: pd.DataFrame,
    outcomes: pd.DataFrame,
    recipes: Mapping[str, Mapping[str, Mapping[int, BinaryOutcomeConformalRecipe]]],
    reference: pd.DataFrame,
    *,
    fit_audit: pd.DataFrame,
    learners: Sequence[str],
    window_ids: Sequence[str],
    role: str,
    taxonomy_groups: int,
    expected_issue_months: Sequence[str],
    expected_candidates: int,
    expected_resolved: int,
    expected_unresolved: int,
    expected_resolved_y0: int,
    expected_resolved_y1: int,
    tolerance: float = 1.0e-12,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Build the exhaustive 5 x 8 x 5 x 15 and pooled residual frontier."""
    declared_learners = _declared_tuple(learners, label="learners", length=5)
    declared_windows = _declared_tuple(window_ids, label="window_ids", length=8)
    months = tuple(str(value) for value in expected_issue_months)
    if len(months) != 15 or len(set(months)) != 15 or tuple(sorted(months)) != months:
        raise ValueError("expected_issue_months must be the 15 distinct ordered target months.")
    if taxonomy_groups != 5 or isinstance(taxonomy_groups, (bool, np.bool_)):
        raise ValueError("Residual transport requires exactly five taxonomy groups.")
    if not isinstance(role, str) or not role:
        raise ValueError("role must be a nonempty string.")
    if not np.isfinite(tolerance) or tolerance < 0.0 or tolerance > 1.0e-12:
        raise ValueError("tolerance must be finite, nonnegative, and at most 1e-12.")
    expected = {
        "candidate": _expected_count(expected_candidates, label="expected_candidates"),
        "resolved": _expected_count(expected_resolved, label="expected_resolved"),
        "unresolved": _expected_count(expected_unresolved, label="expected_unresolved"),
        "resolved_y0": _expected_count(expected_resolved_y0, label="expected_resolved_y0"),
        "resolved_y1": _expected_count(expected_resolved_y1, label="expected_resolved_y1"),
    }
    if expected["resolved"] + expected["unresolved"] != expected["candidate"]:
        raise ValueError("Expected resolved and unresolved counts do not sum to candidates.")
    if expected["resolved_y0"] + expected["resolved_y1"] != expected["resolved"]:
        raise ValueError("Expected resolved class counts do not sum to resolved rows.")

    panel = _validate_endpoint_panel(
        scores,
        outcomes,
        learners=declared_learners,
        role=role,
        issue_months=months,
        expected=expected,
    )
    fit_summary = validate_residual_fit_audit(
        fit_audit,
        recipes,
        learners=declared_learners,
        window_ids=declared_windows,
        taxonomy_groups=taxonomy_groups,
        tolerance=tolerance,
    )
    fit = fit_audit.loc[fit_audit["taxonomy_groups"].eq(taxonomy_groups)].copy()
    fit["conformal_group"] = pd.to_numeric(fit["conformal_group"], errors="raise").astype(int)
    fit["pd_point"] = pd.to_numeric(fit["pd_point"], errors="raise").astype(float)
    fit["terminal_default"] = pd.to_numeric(fit["terminal_default"], errors="raise").astype(float)
    fit["_residual"] = np.abs(fit["terminal_default"] - fit["pd_point"])
    grouped_fit = fit.groupby(
        ["learner", "window_id", "conformal_group"], observed=True, sort=False
    )
    canonical_reference = _prepare_reference(
        reference,
        learners=declared_learners,
        windows=declared_windows,
        taxonomy_groups=taxonomy_groups,
        role=role,
    )

    labels = panel["_label"].to_numpy(dtype=float)
    resolved = np.isfinite(labels)
    monthly_rows: list[dict[str, Any]] = []
    pooled_rows: list[dict[str, Any]] = []
    for learner in declared_learners:
        probabilities = pd.to_numeric(panel[f"pd_{learner}"], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(probabilities).all() or np.any(
            (probabilities < 0.0) | (probabilities > 1.0)
        ):
            raise RuntimeError(f"Frozen probabilities are invalid for {learner!r}.")
        learner_recipes = recipes[learner]
        common_edges = learner_recipes[declared_windows[0]][taxonomy_groups].bin_edges
        assignments = assign_conformal_groups(probabilities, common_edges)
        if not np.array_equal(np.unique(assignments), np.arange(taxonomy_groups)):
            raise RuntimeError(f"Fixed panel does not populate every stratum for {learner!r}.")

        for window_id in declared_windows:
            recipe = learner_recipes[window_id][taxonomy_groups]
            current_assignments = assign_conformal_groups(probabilities, recipe.bin_edges)
            if not np.array_equal(current_assignments, assignments):
                raise RuntimeError(f"Target assignments changed for {learner}/{window_id}.")
            for group in range(taxonomy_groups):
                fit_block = grouped_fit.get_group((learner, window_id, group))
                calibration = fit_block["_residual"].to_numpy(dtype=float)
                threshold = float(recipe.residual_quantiles[group])
                fit_rows = int(len(calibration))
                rank = int(recipe.finite_sample_ranks[group])
                raw_rank = int(recipe.raw_finite_sample_ranks[group])
                if fit_rows != int(recipe.group_counts[group]):
                    raise RuntimeError("Fit residual count changed after the fit-audit gate.")
                base = {
                    "learner": learner,
                    "window_id": window_id,
                    "taxonomy_groups": taxonomy_groups,
                    "conformal_group": group,
                    "score_stratum": group + 1,
                    "role": role,
                    "fit_rows": fit_rows,
                    "finite_sample_rank": rank,
                    "raw_finite_sample_rank": raw_rank,
                    "fit_score_min": float(fit_block["pd_point"].min()),
                    "fit_score_max": float(fit_block["pd_point"].max()),
                    "fit_residual_min": float(np.min(calibration)),
                    "fit_residual_max": float(np.max(calibration)),
                }
                group_mask = assignments == group
                pooled_resolved = group_mask & resolved
                pooled_unresolved = group_mask & ~resolved
                pooled_record = {
                    **base,
                    "target_scope": "pooled_15_issue_months",
                    "issue_month": "ALL",
                    **_cell_statistics(
                        calibration_residuals=calibration,
                        resolved_target_residuals=np.abs(
                            labels[pooled_resolved] - probabilities[pooled_resolved]
                        ),
                        unresolved_probabilities=probabilities[pooled_unresolved],
                        target_scores=probabilities[group_mask],
                        threshold=threshold,
                    ),
                }
                reference_row = require_unique_row(
                    canonical_reference,
                    key={
                        "learner": learner,
                        "window_id": window_id,
                        "conformal_group": group,
                    },
                    label="residual-transport V5 reference",
                )
                _reconcile_pooled_reference(
                    pooled_record,
                    reference_row,
                    label=f"{learner}/{window_id}/stratum-{group}",
                    tolerance=tolerance,
                )
                pooled_record["v5_q_and_coverage_reconciled"] = True
                pooled_rows.append(pooled_record)

                for month in months:
                    month_mask = group_mask & panel["issue_month"].eq(month).to_numpy(dtype=bool)
                    if not month_mask.any():
                        raise RuntimeError(
                            "Monthly residual cell is empty: "
                            f"{learner}/{window_id}/{group}/{month}."
                        )
                    month_resolved = month_mask & resolved
                    month_unresolved = month_mask & ~resolved
                    monthly_rows.append(
                        {
                            **base,
                            "target_scope": "single_issue_month",
                            "issue_month": month,
                            **_cell_statistics(
                                calibration_residuals=calibration,
                                resolved_target_residuals=np.abs(
                                    labels[month_resolved] - probabilities[month_resolved]
                                ),
                                unresolved_probabilities=probabilities[month_unresolved],
                                target_scores=probabilities[month_mask],
                                threshold=threshold,
                            ),
                        }
                    )

    monthly = pd.DataFrame(monthly_rows).reset_index(drop=True)
    pooled = pd.DataFrame(pooled_rows).reset_index(drop=True)
    expected_monthly_rows = (
        len(declared_learners) * len(declared_windows) * taxonomy_groups * len(months)
    )
    expected_pooled_rows = len(declared_learners) * len(declared_windows) * taxonomy_groups
    if len(monthly) != expected_monthly_rows or len(pooled) != expected_pooled_rows:
        raise RuntimeError("Residual-transport complete grid changed.")
    monthly_keys = ["learner", "window_id", "conformal_group", "issue_month"]
    pooled_keys = ["learner", "window_id", "conformal_group"]
    if monthly.duplicated(monthly_keys).any() or pooled.duplicated(pooled_keys).any():
        raise RuntimeError("Residual-transport output keys are duplicated.")
    for _, pooled_row in pooled.iterrows():
        block = monthly.loc[
            monthly["learner"].eq(pooled_row["learner"])
            & monthly["window_id"].eq(pooled_row["window_id"])
            & monthly["conformal_group"].eq(pooled_row["conformal_group"])
        ]
        if len(block) != len(months):
            raise RuntimeError("Monthly-to-pooled residual grid is incomplete.")
        for column in _MONTHLY_SUM_COLUMNS:
            if int(block[column].sum()) != int(pooled_row[column]):
                raise RuntimeError(f"Monthly-to-pooled count failed for {column!r}.")

    summary = {
        "status": "candidate_module_only_no_active_evidence",
        "candidate_rows": int(len(panel)),
        "resolved_rows": int(resolved.sum()),
        "unresolved_rows": int((~resolved).sum()),
        "learners": list(declared_learners),
        "window_ids": list(declared_windows),
        "taxonomy_groups": taxonomy_groups,
        "issue_months": list(months),
        "monthly_rows": int(len(monthly)),
        "pooled_rows": int(len(pooled)),
        "panel_ids_sha256": _hash_strings(panel["_canonical_id"].to_numpy(dtype=str)),
        "fit_audit": fit_summary,
        "directional_ks_p_values_computed": False,
        "completion_extrema_are_sharp_endpoints": True,
        "directional_discrepancy_comparison_uses_strict_separation": True,
        "directional_discrepancy_ties_are_not_robustly_ordered": True,
        "interior_attainability_claimed": False,
        "monthly_to_pooled_q_counts_reconciled": True,
        "pooled_v5_q_and_coverage_reconciled": True,
    }
    return monthly, pooled, summary
