"""Retrospective label-by-score-stratum Mondrian conformal diagnostics.

The fitting functions in this module use only historical conformal-fit labels.
Evaluation outcomes enter only through :func:`evaluate_label_mondrian`, after
the threshold table has been frozen by the separate protocol runner.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import product
from typing import Any

import numpy as np
import pandas as pd

from src.ijds_audit.grid_contracts import require_exact_grid, require_unique_row
from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    apply_binary_outcome_recipe,
    assign_conformal_groups,
)

FORBIDDEN_EVALUATION_COLUMNS = frozenset(
    {
        "snapshot_default",
        "snapshot_resolution",
        "terminal_default",
        "loan_status",
        "label_available",
        "label_available_at",
        "covered",
        "miscovered",
    }
)


def _as_probability_vector(values: Any, *, label: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or len(array) == 0:
        raise ValueError(f"{label} must be a nonempty one-dimensional vector.")
    if not bool(np.isfinite(array).all()):
        raise ValueError(f"{label} must be finite.")
    if bool(np.any((array < 0.0) | (array > 1.0))):
        raise ValueError(f"{label} must lie in [0, 1].")
    return array


def _as_binary_vector(values: Any, *, label: str) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1 or len(array) == 0:
        raise ValueError(f"{label} must be a nonempty one-dimensional vector.")
    if not bool(np.isin(array, (0, 1)).all()):
        raise ValueError(f"{label} must contain only 0 and 1.")
    return array.astype(int)


def exact_split_conformal_threshold(
    residuals: Any,
    *,
    alpha: float,
) -> tuple[int, float]:
    """Return the exact split-conformal rank and threshold.

    The rank is ``ceil((n + 1) * (1 - alpha))``. When it equals ``n + 1``,
    the threshold is positive infinity rather than a clipped sample maximum.
    """
    scores = np.asarray(residuals, dtype=float)
    if scores.ndim != 1 or len(scores) == 0:
        raise ValueError("Residuals must be a nonempty one-dimensional vector.")
    if not bool(np.isfinite(scores).all()) or bool(np.any(scores < 0.0)):
        raise ValueError("Residuals must be finite and nonnegative.")
    if not 0.0 < float(alpha) < 1.0:
        raise ValueError("alpha must lie in (0, 1).")
    count = int(len(scores))
    rank = int(np.ceil((count + 1) * (1.0 - float(alpha))))
    if not 1 <= rank <= count + 1:
        raise RuntimeError("Exact split-conformal rank left its admissible range.")
    if rank == count + 1:
        return rank, float("inf")
    threshold = float(np.partition(scores, rank - 1)[rank - 1])
    return rank, threshold


def _require_score_frame_outcome_free(scores: pd.DataFrame, learners: Sequence[str]) -> None:
    leaked = sorted(FORBIDDEN_EVALUATION_COLUMNS.intersection(scores.columns))
    if leaked:
        raise RuntimeError(f"Evaluation outcome columns entered the frozen score frame: {leaked}.")
    required = {"id", "issue_d", "design_split", *(f"pd_{name}" for name in learners)}
    missing = sorted(required.difference(scores.columns))
    if missing:
        raise ValueError(f"Frozen scores omit columns: {missing}.")
    if bool(scores["id"].duplicated().any()):
        raise RuntimeError("Frozen scores contain duplicate IDs.")


def fit_label_mondrian_thresholds(
    scores: pd.DataFrame,
    fit_audit: pd.DataFrame,
    recipes: Mapping[str, Mapping[str, Mapping[int, BinaryOutcomeConformalRecipe]]],
    *,
    learners: Sequence[str],
    window_ids: Sequence[str],
    taxonomy_groups: int,
    alpha: float,
    reconciliation_atol: float = 5.0e-14,
) -> pd.DataFrame:
    """Fit all label-by-score-stratum thresholds from frozen fit artifacts."""
    _require_score_frame_outcome_free(scores, learners)
    required_audit = {
        "id",
        "issue_d",
        "learner",
        "window_id",
        "taxonomy_groups",
        "conformal_group",
        "pd_point",
        "conformal_lower",
        "conformal_upper",
        "terminal_default",
        "covered",
    }
    missing_audit = sorted(required_audit.difference(fit_audit.columns))
    if missing_audit:
        raise ValueError(f"Frozen residual fit audit omits columns: {missing_audit}.")
    if not 0.0 < float(alpha) < 1.0:
        raise ValueError("alpha must lie in (0, 1).")
    if taxonomy_groups < 1:
        raise ValueError("taxonomy_groups must be positive.")

    selected = fit_audit.loc[
        fit_audit["taxonomy_groups"].eq(taxonomy_groups)
        & fit_audit["learner"].isin(learners)
        & fit_audit["window_id"].isin(window_ids)
    ].copy()
    actual_learners = set(selected["learner"].astype(str).unique())
    actual_windows = set(selected["window_id"].astype(str).unique())
    if actual_learners != set(learners) or actual_windows != set(window_ids):
        raise RuntimeError("Frozen fit-audit learner/window support changed.")

    rows: list[dict[str, Any]] = []
    for learner in learners:
        if learner not in recipes:
            raise RuntimeError(f"Frozen recipes omit learner {learner!r}.")
        expected_taxonomy_provenance = f"{learner}_201101_201112_all_status_independent_scores"
        canonical_bin_edges: tuple[float, ...] | None = None
        score_column = f"pd_{learner}"
        score_lookup = scores[["id", "issue_d", "design_split", score_column]].copy()
        for window_id in window_ids:
            try:
                recipe = recipes[learner][window_id][taxonomy_groups]
            except KeyError as exc:
                raise RuntimeError(
                    f"Frozen recipes omit {learner}/{window_id}/{taxonomy_groups}."
                ) from exc
            if not np.isclose(recipe.alpha, alpha, atol=0.0, rtol=0.0):
                raise RuntimeError(f"Frozen recipe alpha changed for {learner}/{window_id}.")
            if recipe.requested_groups != taxonomy_groups:
                raise RuntimeError(f"Frozen recipe group count changed for {learner}/{window_id}.")
            if recipe.taxonomy_method != "fixed_empirical_linear_score_quantiles":
                raise RuntimeError(f"Frozen taxonomy method changed for {learner}/{window_id}.")
            if recipe.taxonomy_provenance != expected_taxonomy_provenance:
                raise RuntimeError(f"Frozen taxonomy provenance changed for {learner}/{window_id}.")
            recipe_edges = tuple(float(value) for value in recipe.bin_edges)
            if canonical_bin_edges is None:
                canonical_bin_edges = recipe_edges
            elif recipe_edges != canonical_bin_edges:
                raise RuntimeError(f"Frozen taxonomy edges changed across windows for {learner}.")

            cell = selected.loc[
                selected["learner"].eq(learner) & selected["window_id"].eq(window_id)
            ].copy()
            if len(cell) == 0 or bool(cell["id"].duplicated().any()):
                raise RuntimeError(
                    f"Fit-audit IDs are empty or duplicated for {learner}/{window_id}."
                )
            cell = cell.merge(
                score_lookup,
                on="id",
                how="left",
                validate="one_to_one",
                suffixes=("_audit", "_score"),
                indicator="_score_merge",
            )
            if not bool(cell["_score_merge"].eq("both").all()):
                raise RuntimeError(
                    f"Fit-audit IDs do not align to scores for {learner}/{window_id}."
                )
            if not bool(cell["design_split"].eq("conformal_fit").all()):
                raise RuntimeError(
                    f"Non-fit rows entered label-Mondrian fitting for {learner}/{window_id}."
                )
            if not bool(
                pd.to_datetime(cell["issue_d_audit"], errors="raise")
                .eq(pd.to_datetime(cell["issue_d_score"], errors="raise"))
                .all()
            ):
                raise RuntimeError(f"Fit-audit issue dates changed for {learner}/{window_id}.")

            probability = _as_probability_vector(cell["pd_point"], label="Fit-audit scores")
            source_probability = _as_probability_vector(
                cell[score_column], label="Frozen source scores"
            )
            if not bool(
                np.isclose(
                    probability,
                    source_probability,
                    atol=reconciliation_atol,
                    rtol=reconciliation_atol,
                ).all()
            ):
                raise RuntimeError(f"Fit-audit scores changed for {learner}/{window_id}.")
            # The hash-locked score frame is canonical. The fit audit is only
            # a reconciled view and must not define a slightly different order
            # statistic through round-off or serialization drift.
            probability = source_probability
            labels = _as_binary_vector(
                cell["terminal_default"], label="Historical conformal-fit labels"
            )
            assigned, lower, upper = apply_binary_outcome_recipe(probability, recipe)
            audit_groups = cell["conformal_group"].to_numpy(dtype=int)
            if not np.array_equal(assigned, audit_groups):
                raise RuntimeError(
                    f"Frozen score-stratum assignments changed for {learner}/{window_id}."
                )
            if tuple(np.bincount(assigned, minlength=taxonomy_groups)) != tuple(
                recipe.group_counts
            ):
                raise RuntimeError(
                    f"Frozen marginal group counts changed for {learner}/{window_id}."
                )
            if not bool(
                np.isclose(
                    lower,
                    cell["conformal_lower"].to_numpy(dtype=float),
                    atol=reconciliation_atol,
                    rtol=reconciliation_atol,
                ).all()
            ) or not bool(
                np.isclose(
                    upper,
                    cell["conformal_upper"].to_numpy(dtype=float),
                    atol=reconciliation_atol,
                    rtol=reconciliation_atol,
                ).all()
            ):
                raise RuntimeError(f"Frozen marginal intervals changed for {learner}/{window_id}.")
            baseline_covered = ((labels == 0) & (lower <= 0.0)) | ((labels == 1) & (upper >= 1.0))
            if not np.array_equal(baseline_covered, cell["covered"].to_numpy(dtype=bool)):
                raise RuntimeError(f"Frozen fit coverage changed for {learner}/{window_id}.")

            residuals = np.abs(labels.astype(float) - probability)
            for stratum, target_label in product(range(taxonomy_groups), (0, 1)):
                stratum_mask = assigned == stratum
                label_mask = stratum_mask & (labels == target_label)
                label_residuals = residuals[label_mask]
                if len(label_residuals) == 0:
                    raise RuntimeError(
                        f"Empty label-Mondrian cell {learner}/{window_id}/"
                        f"stratum={stratum}/label={target_label}."
                    )
                rank, threshold = exact_split_conformal_threshold(
                    label_residuals,
                    alpha=alpha,
                )
                rows.append(
                    {
                        "learner": learner,
                        "window_id": window_id,
                        "taxonomy_groups": int(taxonomy_groups),
                        "score_stratum": int(stratum),
                        "label": int(target_label),
                        "alpha": float(alpha),
                        "fit_group_rows": int(stratum_mask.sum()),
                        "fit_rows": int(label_mask.sum()),
                        "fit_label_share_within_stratum": float(
                            label_mask.sum() / stratum_mask.sum()
                        ),
                        "finite_sample_rank": int(rank),
                        "rank_reference_size": int(label_mask.sum() + 1),
                        "threshold": float(threshold),
                        "threshold_is_infinite": bool(np.isposinf(threshold)),
                        "fit_score_min": float(probability[label_mask].min()),
                        "fit_score_max": float(probability[label_mask].max()),
                        "fit_residual_min": float(label_residuals.min()),
                        "fit_residual_max": float(label_residuals.max()),
                    }
                )

    result = pd.DataFrame(rows)
    require_exact_grid(
        result,
        domains={
            "learner": tuple(learners),
            "window_id": tuple(window_ids),
            "score_stratum": tuple(range(taxonomy_groups)),
            "label": (0, 1),
        },
        label="label-Mondrian threshold freeze",
    )
    if len(result) != len(learners) * len(window_ids) * taxonomy_groups * 2:
        raise RuntimeError("Label-Mondrian threshold census changed.")
    finite = result.loc[~result["threshold_is_infinite"], "threshold"].to_numpy(dtype=float)
    if not bool(np.isfinite(finite).all()) or bool(np.any(finite < 0.0)):
        raise RuntimeError("A finite label-Mondrian threshold is invalid.")
    expected_infinite = result["finite_sample_rank"].eq(result["rank_reference_size"])
    if not np.array_equal(expected_infinite, result["threshold_is_infinite"]):
        raise RuntimeError("Infinity flags do not match exact n+1 ranks.")
    learner_order = {name: index for index, name in enumerate(learners)}
    window_order = {name: index for index, name in enumerate(window_ids)}
    result["_learner_order"] = result["learner"].map(learner_order)
    result["_window_order"] = result["window_id"].map(window_order)
    return (
        result.sort_values(
            ["_learner_order", "_window_order", "score_stratum", "label"],
            kind="stable",
        )
        .drop(columns=["_learner_order", "_window_order"])
        .reset_index(drop=True)
    )


def apply_label_mondrian_thresholds(
    probabilities: Any,
    recipe: BinaryOutcomeConformalRecipe,
    thresholds: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return score strata and membership indicators for labels zero and one."""
    point = _as_probability_vector(probabilities, label="Candidate scores")
    groups = int(recipe.requested_groups)
    require_exact_grid(
        thresholds,
        domains={"score_stratum": tuple(range(groups)), "label": (0, 1)},
        label="one learner-window label-Mondrian threshold table",
    )
    if not thresholds["taxonomy_groups"].eq(groups).all():
        raise RuntimeError("Threshold taxonomy does not match the frozen recipe.")
    q0 = np.empty(groups, dtype=float)
    q1 = np.empty(groups, dtype=float)
    for stratum in range(groups):
        for target_label, target in ((0, q0), (1, q1)):
            row = require_unique_row(
                thresholds,
                key={"score_stratum": stratum, "label": target_label},
                label="one learner-window label-Mondrian threshold table",
            )
            threshold = float(row["threshold"])
            if np.isnan(threshold) or threshold < 0.0 or np.isneginf(threshold):
                raise RuntimeError("Label-Mondrian threshold is invalid.")
            target[stratum] = threshold
    assigned = assign_conformal_groups(point, recipe.bin_edges)
    contains_zero = point <= q0[assigned]
    contains_one = (1.0 - point) <= q1[assigned]
    return assigned, contains_zero, contains_one


def sharp_class_coverage_ratio_bounds(
    contains_label: Any,
    outcomes: Any,
    *,
    target_label: int,
) -> tuple[float, float]:
    """Sharp class-specific coverage bounds over unrestricted unresolved labels."""
    if target_label not in (0, 1):
        raise ValueError("target_label must be zero or one.")
    contains = np.asarray(contains_label, dtype=bool)
    raw = np.asarray(outcomes, dtype=float)
    if contains.ndim != 1 or raw.ndim != 1 or len(contains) != len(raw) or len(raw) == 0:
        raise ValueError("Set membership and outcomes must be nonempty aligned vectors.")
    if bool(np.isinf(raw).any()):
        raise ValueError("Outcomes may be binary or unresolved NaN, never infinite.")
    resolved = ~np.isnan(raw)
    if not bool(np.isin(raw[resolved], (0.0, 1.0)).all()):
        raise ValueError("Resolved outcomes must be binary.")
    target = resolved & (raw == float(target_label))
    resolved_total = int(target.sum())
    resolved_covered = int((target & contains).sum())
    unresolved_contains = int((~resolved & contains).sum())
    unresolved_misses = int((~resolved & ~contains).sum())

    lower_denominator = resolved_total + unresolved_misses
    if lower_denominator > 0:
        lower = resolved_covered / lower_denominator
    elif unresolved_contains > 0:
        lower = 1.0
    else:
        raise RuntimeError("Class coverage is undefined for every admissible completion.")
    upper_denominator = resolved_total + unresolved_contains
    if upper_denominator > 0:
        upper = (resolved_covered + unresolved_contains) / upper_denominator
    elif unresolved_misses > 0:
        upper = 0.0
    else:
        raise RuntimeError("Class coverage is undefined for every admissible completion.")
    if lower > upper + 1.0e-15:
        raise RuntimeError("Sharp class-specific ratio bounds are reversed.")
    return float(lower), float(upper)


def _extreme_weight_sum(
    category_counts: Mapping[tuple[int, int], int],
    *,
    take: int,
    denominator_zero: int,
    denominator_one: int,
    largest: bool,
) -> float:
    weighted = [
        (
            zero / denominator_zero + one / denominator_one,
            int(category_counts.get((zero, one), 0)),
        )
        for zero, one in product((0, 1), repeat=2)
    ]
    weighted.sort(key=lambda item: item[0], reverse=largest)
    remaining = int(take)
    total = 0.0
    for weight, available in weighted:
        chosen = min(remaining, available)
        total += chosen * weight
        remaining -= chosen
        if remaining == 0:
            break
    if remaining != 0:
        raise RuntimeError("Gap optimizer could not allocate the declared unresolved count.")
    return total


def sharp_class_coverage_gap_bounds(
    contains_zero: Any,
    contains_one: Any,
    outcomes: Any,
) -> tuple[float, float, int, int]:
    """Sharp bounds for class-0 minus class-1 coverage under one completion.

    The returned integer witnesses are the numbers of unresolved rows assigned
    label one at the lower and upper gap endpoints, respectively.
    """
    c0 = np.asarray(contains_zero, dtype=bool)
    c1 = np.asarray(contains_one, dtype=bool)
    raw = np.asarray(outcomes, dtype=float)
    if (
        c0.ndim != 1
        or c1.ndim != 1
        or raw.ndim != 1
        or len(c0) != len(c1)
        or len(c0) != len(raw)
        or len(raw) == 0
    ):
        raise ValueError("Set memberships and outcomes must be nonempty aligned vectors.")
    if bool(np.isinf(raw).any()):
        raise ValueError("Outcomes may be binary or unresolved NaN, never infinite.")
    resolved = ~np.isnan(raw)
    if not bool(np.isin(raw[resolved], (0.0, 1.0)).all()):
        raise ValueError("Resolved outcomes must be binary.")
    resolved_zero = resolved & (raw == 0.0)
    resolved_one = resolved & (raw == 1.0)
    b0 = int(resolved_zero.sum())
    b1 = int(resolved_one.sum())
    if b0 == 0 or b1 == 0:
        raise RuntimeError("Both resolved labels are required for sharp gap bounds.")
    a0 = int((resolved_zero & c0).sum())
    a1 = int((resolved_one & c1).sum())
    unresolved_c0 = c0[~resolved].astype(int)
    unresolved_c1 = c1[~resolved].astype(int)
    unresolved = int(len(unresolved_c0))
    categories: tuple[tuple[int, int], ...] = ((0, 0), (0, 1), (1, 0), (1, 1))
    category_counts: dict[tuple[int, int], int] = {
        category: int(((unresolved_c0 == category[0]) & (unresolved_c1 == category[1])).sum())
        for category in categories
    }
    total_zero_covered = int(unresolved_c0.sum())

    lower = float("inf")
    upper = float("-inf")
    lower_witness = 0
    upper_witness = 0
    for assigned_one in range(unresolved + 1):
        denominator_one = b1 + assigned_one
        denominator_zero = b0 + unresolved - assigned_one
        base = (a0 + total_zero_covered) / denominator_zero - a1 / denominator_one
        smallest = _extreme_weight_sum(
            category_counts,
            take=assigned_one,
            denominator_zero=denominator_zero,
            denominator_one=denominator_one,
            largest=False,
        )
        largest = _extreme_weight_sum(
            category_counts,
            take=assigned_one,
            denominator_zero=denominator_zero,
            denominator_one=denominator_one,
            largest=True,
        )
        candidate_upper = base - smallest
        candidate_lower = base - largest
        if candidate_lower < lower:
            lower = float(candidate_lower)
            lower_witness = assigned_one
        if candidate_upper > upper:
            upper = float(candidate_upper)
            upper_witness = assigned_one
    if not np.isfinite(lower) or not np.isfinite(upper) or lower > upper + 1.0e-15:
        raise RuntimeError("Sharp class-coverage gap optimization failed.")
    return lower, upper, lower_witness, upper_witness


def _set_summary(contains_zero: np.ndarray, contains_one: np.ndarray) -> dict[str, Any]:
    empty = ~contains_zero & ~contains_one
    zero_only = contains_zero & ~contains_one
    one_only = ~contains_zero & contains_one
    both = contains_zero & contains_one
    partition = empty.astype(int) + zero_only + one_only + both
    if not bool(np.equal(partition, 1).all()):
        raise RuntimeError("Binary label-Mondrian sets do not partition the candidates.")
    cardinality = contains_zero.astype(int) + contains_one.astype(int)
    rows = int(len(cardinality))
    return {
        "average_set_size": float(cardinality.mean()),
        "singleton_share": float((cardinality == 1).mean()),
        "set_empty_count": int(empty.sum()),
        "set_empty_share": float(empty.mean()),
        "set_zero_only_count": int(zero_only.sum()),
        "set_zero_only_share": float(zero_only.mean()),
        "set_one_only_count": int(one_only.sum()),
        "set_one_only_share": float(one_only.mean()),
        "set_both_count": int(both.sum()),
        "set_both_share": float(both.mean()),
        "candidate_rows": rows,
    }


def _coverage_summary(
    contains_zero: np.ndarray,
    contains_one: np.ndarray,
    outcomes: np.ndarray,
) -> dict[str, Any]:
    if bool(np.isinf(outcomes).any()):
        raise ValueError("Outcomes may be binary or unresolved NaN, never infinite.")
    resolved = ~np.isnan(outcomes)
    labels = outcomes[resolved].astype(int)
    resolved_zero = labels == 0
    resolved_one = labels == 1
    if not bool(resolved_zero.any()) or not bool(resolved_one.any()):
        raise RuntimeError("Both resolved endpoint labels are required.")
    covered_resolved = (resolved_zero & contains_zero[resolved]) | (
        resolved_one & contains_one[resolved]
    )
    unresolved_zero = contains_zero[~resolved]
    unresolved_one = contains_one[~resolved]
    always_covered = unresolved_zero & unresolved_one
    never_covered = ~unresolved_zero & ~unresolved_one
    candidate_rows = int(len(outcomes))
    observed_covered = int(covered_resolved.sum())
    coverage_lower = (observed_covered + int(always_covered.sum())) / candidate_rows
    coverage_upper = (
        observed_covered + int((~resolved).sum()) - int(never_covered.sum())
    ) / candidate_rows
    y0_lower, y0_upper = sharp_class_coverage_ratio_bounds(
        contains_zero,
        outcomes,
        target_label=0,
    )
    y1_lower, y1_upper = sharp_class_coverage_ratio_bounds(
        contains_one,
        outcomes,
        target_label=1,
    )
    gap_lower, gap_upper, gap_lower_witness, gap_upper_witness = sharp_class_coverage_gap_bounds(
        contains_zero, contains_one, outcomes
    )
    return {
        "resolved_rows": int(resolved.sum()),
        "unresolved_rows": int((~resolved).sum()),
        "resolved_y0_rows": int(resolved_zero.sum()),
        "resolved_y1_rows": int(resolved_one.sum()),
        "resolved_covered_rows": observed_covered,
        "coverage_resolved": float(covered_resolved.mean()),
        "coverage_resolved_y0": float(contains_zero[resolved][resolved_zero].mean()),
        "coverage_resolved_y1": float(contains_one[resolved][resolved_one].mean()),
        "coverage_resolved_gap_y0_minus_y1": float(
            contains_zero[resolved][resolved_zero].mean()
            - contains_one[resolved][resolved_one].mean()
        ),
        "coverage_lower": float(coverage_lower),
        "coverage_upper": float(coverage_upper),
        "coverage_y0_lower": y0_lower,
        "coverage_y0_upper": y0_upper,
        "coverage_y1_lower": y1_lower,
        "coverage_y1_upper": y1_upper,
        "coverage_gap_y0_minus_y1_lower": gap_lower,
        "coverage_gap_y0_minus_y1_upper": gap_upper,
        "gap_lower_unresolved_y1_rows": int(gap_lower_witness),
        "gap_upper_unresolved_y1_rows": int(gap_upper_witness),
        "unresolved_zero_covered_rows": int(unresolved_zero.sum()),
        "unresolved_zero_missed_rows": int((~unresolved_zero).sum()),
        "unresolved_one_covered_rows": int(unresolved_one.sum()),
        "unresolved_one_missed_rows": int((~unresolved_one).sum()),
    }


def _require_close(actual: float, expected: float, *, label: str, atol: float) -> float:
    difference = float(actual - expected)
    if not np.isclose(actual, expected, atol=atol, rtol=atol):
        raise RuntimeError(f"Baseline {label} did not reconcile: {actual!r} != {expected!r}.")
    return difference


def _nominal_identification_state(
    lower: float,
    upper: float,
    *,
    nominal: float,
    defined: bool,
) -> str:
    if not defined:
        return "undefined"
    if upper < nominal:
        return "robust_shortfall"
    if lower >= nominal:
        return "robust_at_or_above_nominal"
    return "crosses_nominal"


def evaluate_label_mondrian(
    scores: pd.DataFrame,
    outcomes: pd.DataFrame,
    recipes: Mapping[str, Mapping[str, Mapping[int, BinaryOutcomeConformalRecipe]]],
    thresholds: pd.DataFrame,
    baseline_set_reference: pd.DataFrame,
    baseline_coverage_reference: pd.DataFrame,
    *,
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
    reconciliation_atol: float = 5.0e-14,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Evaluate a frozen label-Mondrian table against the active endpoint."""
    _require_score_frame_outcome_free(scores, learners)
    require_exact_grid(
        thresholds,
        domains={
            "learner": tuple(learners),
            "window_id": tuple(window_ids),
            "score_stratum": tuple(range(taxonomy_groups)),
            "label": (0, 1),
        },
        label="frozen label-Mondrian threshold table",
    )
    primary = scores.loc[scores["design_split"].eq(role)].copy()
    primary["issue_month"] = pd.to_datetime(primary["issue_d"], errors="raise").dt.to_period("M")
    actual_months = tuple(sorted(primary["issue_month"].astype(str).unique()))
    if actual_months != tuple(expected_issue_months):
        raise RuntimeError(
            f"Primary issue-month set changed: {actual_months!r} != {tuple(expected_issue_months)!r}."
        )
    if len(primary) != expected_candidates or bool(primary["id"].duplicated().any()):
        raise RuntimeError("Primary score census or ID uniqueness changed.")
    if not {"id", "snapshot_default"}.issubset(outcomes.columns):
        raise ValueError("Endpoint outcomes must contain id and snapshot_default.")
    endpoint = outcomes[["id", "snapshot_default"]].copy()
    if bool(endpoint["id"].duplicated().any()):
        raise RuntimeError("Endpoint outcomes contain duplicate IDs.")
    joined = primary.merge(
        endpoint,
        on="id",
        how="left",
        validate="one_to_one",
        indicator="_endpoint_merge",
    )
    if not bool(joined["_endpoint_merge"].eq("both").all()):
        raise RuntimeError("Endpoint alignment is incomplete for frozen primary IDs.")
    joined = joined.drop(columns="_endpoint_merge")
    endpoint_values = joined["snapshot_default"].to_numpy(dtype=float)
    if bool(np.isinf(endpoint_values).any()):
        raise RuntimeError("Endpoint contains an infinite outcome.")
    resolved = ~np.isnan(endpoint_values)
    if not bool(np.isin(endpoint_values[resolved], (0.0, 1.0)).all()):
        raise RuntimeError("Resolved endpoint contains a nonbinary outcome.")
    actual_counts = {
        "resolved": int(resolved.sum()),
        "unresolved": int((~resolved).sum()),
        "resolved_y0": int((endpoint_values[resolved] == 0.0).sum()),
        "resolved_y1": int((endpoint_values[resolved] == 1.0).sum()),
    }
    expected_counts = {
        "resolved": int(expected_resolved),
        "unresolved": int(expected_unresolved),
        "resolved_y0": int(expected_resolved_y0),
        "resolved_y1": int(expected_resolved_y1),
    }
    if actual_counts != expected_counts:
        raise RuntimeError(f"Endpoint census changed: {actual_counts!r} != {expected_counts!r}.")

    baseline_sets = baseline_set_reference.loc[
        baseline_set_reference["taxonomy_groups"].eq(taxonomy_groups)
        & baseline_set_reference["role"].eq(role)
    ].copy()
    baseline_coverage = baseline_coverage_reference.loc[
        baseline_coverage_reference["taxonomy_groups"].eq(taxonomy_groups)
        & baseline_coverage_reference["role"].eq(role)
        & baseline_coverage_reference["conformal_group"].eq(-1)
    ].copy()
    for frame, label in (
        (baseline_sets, "baseline set diagnostics"),
        (baseline_coverage, "baseline coverage"),
    ):
        require_exact_grid(
            frame,
            domains={"learner": tuple(learners), "window_id": tuple(window_ids)},
            label=label,
        )

    evaluation_rows: list[dict[str, Any]] = []
    category_rows: list[dict[str, Any]] = []
    stratum_rows: list[dict[str, Any]] = []
    reconciliation_rows: list[dict[str, Any]] = []
    for learner in learners:
        probability = _as_probability_vector(
            joined[f"pd_{learner}"], label=f"Primary scores for {learner}"
        )
        for window_id in window_ids:
            recipe = recipes[learner][window_id][taxonomy_groups]
            cell_thresholds = thresholds.loc[
                thresholds["learner"].eq(learner) & thresholds["window_id"].eq(window_id)
            ].copy()
            assigned, contains_zero, contains_one = apply_label_mondrian_thresholds(
                probability,
                recipe,
                cell_thresholds,
            )
            baseline_assigned, baseline_lower, baseline_upper = apply_binary_outcome_recipe(
                probability, recipe
            )
            if not np.array_equal(assigned, baseline_assigned):
                raise RuntimeError("Label-Mondrian and baseline score strata diverged.")
            baseline_zero = baseline_lower <= 0.0
            baseline_one = baseline_upper >= 1.0
            actual_baseline = {
                **_set_summary(baseline_zero, baseline_one),
                **_coverage_summary(baseline_zero, baseline_one, endpoint_values),
                "mean_width": float(np.mean(baseline_upper - baseline_lower)),
            }
            set_metrics = _set_summary(contains_zero, contains_one)
            coverage_metrics = _coverage_summary(contains_zero, contains_one, endpoint_values)
            evaluation_rows.append(
                {
                    "learner": learner,
                    "window_id": window_id,
                    "taxonomy_groups": int(taxonomy_groups),
                    "role": role,
                    "score_strata_observed": int(len(np.unique(assigned))),
                    "threshold_cells": int(len(cell_thresholds)),
                    "infinite_threshold_cells": int(cell_thresholds["threshold_is_infinite"].sum()),
                    **set_metrics,
                    **coverage_metrics,
                    **{f"baseline_{metric}": value for metric, value in actual_baseline.items()},
                    "resolved_coverage_delta_label_mondrian_minus_baseline": float(
                        coverage_metrics["coverage_resolved"] - actual_baseline["coverage_resolved"]
                    ),
                    "resolved_y0_coverage_delta_label_mondrian_minus_baseline": float(
                        coverage_metrics["coverage_resolved_y0"]
                        - actual_baseline["coverage_resolved_y0"]
                    ),
                    "resolved_y1_coverage_delta_label_mondrian_minus_baseline": float(
                        coverage_metrics["coverage_resolved_y1"]
                        - actual_baseline["coverage_resolved_y1"]
                    ),
                    "average_set_size_delta_label_mondrian_minus_baseline": float(
                        set_metrics["average_set_size"] - actual_baseline["average_set_size"]
                    ),
                }
            )

            resolved_endpoint = ~np.isnan(endpoint_values)
            for score_stratum, target_label in product(range(taxonomy_groups), (0, 1)):
                stratum_mask = assigned == score_stratum
                target_resolved = (
                    stratum_mask & resolved_endpoint & (endpoint_values == float(target_label))
                )
                stratum_unresolved = stratum_mask & ~resolved_endpoint
                contains_target = contains_zero if target_label == 0 else contains_one
                baseline_contains_target = baseline_zero if target_label == 0 else baseline_one
                resolved_label_rows = int(target_resolved.sum())
                resolved_label_covered = int((target_resolved & contains_target).sum())
                baseline_resolved_label_covered = int(
                    (target_resolved & baseline_contains_target).sum()
                )
                unresolved_label_covered = int((stratum_unresolved & contains_target).sum())
                unresolved_label_missed = int((stratum_unresolved & ~contains_target).sum())
                baseline_unresolved_label_covered = int(
                    (stratum_unresolved & baseline_contains_target).sum()
                )
                baseline_unresolved_label_missed = int(
                    (stratum_unresolved & ~baseline_contains_target).sum()
                )
                category_defined = bool(resolved_label_rows > 0 or stratum_unresolved.any())
                if category_defined:
                    category_lower, category_upper = sharp_class_coverage_ratio_bounds(
                        contains_target[stratum_mask],
                        endpoint_values[stratum_mask],
                        target_label=target_label,
                    )
                    baseline_category_lower, baseline_category_upper = (
                        sharp_class_coverage_ratio_bounds(
                            baseline_contains_target[stratum_mask],
                            endpoint_values[stratum_mask],
                            target_label=target_label,
                        )
                    )
                else:
                    category_lower, category_upper = float("nan"), float("nan")
                    baseline_category_lower, baseline_category_upper = (
                        float("nan"),
                        float("nan"),
                    )
                threshold_row = require_unique_row(
                    cell_thresholds,
                    key={"score_stratum": score_stratum, "label": target_label},
                    label="one target label-Mondrian category",
                )
                candidate_stratum_rows = int(stratum_mask.sum())
                stratum_present = candidate_stratum_rows > 0
                category_rows.append(
                    {
                        "learner": learner,
                        "window_id": window_id,
                        "taxonomy_groups": int(taxonomy_groups),
                        "role": role,
                        "score_stratum": int(score_stratum),
                        "label": int(target_label),
                        "alpha": float(threshold_row["alpha"]),
                        "fit_rows": int(threshold_row["fit_rows"]),
                        "finite_sample_rank": int(threshold_row["finite_sample_rank"]),
                        "threshold": float(threshold_row["threshold"]),
                        "threshold_is_infinite": bool(threshold_row["threshold_is_infinite"]),
                        "score_stratum_present": stratum_present,
                        "candidate_stratum_rows": candidate_stratum_rows,
                        "resolved_label_rows": resolved_label_rows,
                        "resolved_label_covered_rows": resolved_label_covered,
                        "coverage_resolved_label": (
                            float(resolved_label_covered / resolved_label_rows)
                            if resolved_label_rows > 0
                            else float("nan")
                        ),
                        "baseline_resolved_label_covered_rows": (baseline_resolved_label_covered),
                        "baseline_coverage_resolved_label": (
                            float(baseline_resolved_label_covered / resolved_label_rows)
                            if resolved_label_rows > 0
                            else float("nan")
                        ),
                        "unresolved_stratum_rows": int(stratum_unresolved.sum()),
                        "unresolved_label_covered_if_assigned_rows": unresolved_label_covered,
                        "unresolved_label_missed_if_assigned_rows": unresolved_label_missed,
                        "baseline_unresolved_label_covered_if_assigned_rows": (
                            baseline_unresolved_label_covered
                        ),
                        "baseline_unresolved_label_missed_if_assigned_rows": (
                            baseline_unresolved_label_missed
                        ),
                        "conditional_coverage_defined": category_defined,
                        "coverage_label_lower": category_lower,
                        "coverage_label_upper": category_upper,
                        "baseline_coverage_label_lower": baseline_category_lower,
                        "baseline_coverage_label_upper": baseline_category_upper,
                        "label_prevalence_lower": (
                            float(resolved_label_rows / candidate_stratum_rows)
                            if stratum_present
                            else float("nan")
                        ),
                        "label_prevalence_upper": (
                            float(
                                (resolved_label_rows + int(stratum_unresolved.sum()))
                                / candidate_stratum_rows
                            )
                            if stratum_present
                            else float("nan")
                        ),
                        "coverage_upper_below_nominal": bool(
                            category_defined
                            and category_upper < 1.0 - float(threshold_row["alpha"])
                        ),
                        "identification_state_at_nominal": _nominal_identification_state(
                            category_lower,
                            category_upper,
                            nominal=1.0 - float(threshold_row["alpha"]),
                            defined=category_defined,
                        ),
                        "baseline_identification_state_at_nominal": (
                            _nominal_identification_state(
                                baseline_category_lower,
                                baseline_category_upper,
                                nominal=1.0 - float(threshold_row["alpha"]),
                                defined=category_defined,
                            )
                        ),
                        "resolved_coverage_delta_label_mondrian_minus_baseline": (
                            float(
                                (resolved_label_covered - baseline_resolved_label_covered)
                                / resolved_label_rows
                            )
                            if resolved_label_rows > 0
                            else float("nan")
                        ),
                        "sharp_endpoint_delta_reported": False,
                    }
                )

            for score_stratum in range(taxonomy_groups):
                stratum_mask = assigned == score_stratum
                stratum_outcomes = endpoint_values[stratum_mask]
                stratum_zero = contains_zero[stratum_mask]
                stratum_one = contains_one[stratum_mask]
                baseline_stratum_zero = baseline_zero[stratum_mask]
                baseline_stratum_one = baseline_one[stratum_mask]
                stratum_resolved = ~np.isnan(stratum_outcomes)
                resolved_y0 = int((stratum_resolved & (stratum_outcomes == 0.0)).sum())
                resolved_y1 = int((stratum_resolved & (stratum_outcomes == 1.0)).sum())
                resolved_covered = (
                    (stratum_outcomes[stratum_resolved] == 0.0) & stratum_zero[stratum_resolved]
                ) | ((stratum_outcomes[stratum_resolved] == 1.0) & stratum_one[stratum_resolved])
                unresolved_zero = stratum_zero[~stratum_resolved]
                unresolved_one = stratum_one[~stratum_resolved]
                unresolved_always_covered = unresolved_zero & unresolved_one
                unresolved_never_covered = ~unresolved_zero & ~unresolved_one
                baseline_resolved_covered = (
                    (stratum_outcomes[stratum_resolved] == 0.0)
                    & baseline_stratum_zero[stratum_resolved]
                ) | (
                    (stratum_outcomes[stratum_resolved] == 1.0)
                    & baseline_stratum_one[stratum_resolved]
                )
                baseline_unresolved_zero = baseline_stratum_zero[~stratum_resolved]
                baseline_unresolved_one = baseline_stratum_one[~stratum_resolved]
                baseline_unresolved_always_covered = (
                    baseline_unresolved_zero & baseline_unresolved_one
                )
                baseline_unresolved_never_covered = (
                    ~baseline_unresolved_zero & ~baseline_unresolved_one
                )
                stratum_candidate_rows = int(stratum_mask.sum())
                marginal_coverage_lower = float(
                    (int(resolved_covered.sum()) + int(unresolved_always_covered.sum()))
                    / stratum_candidate_rows
                )
                marginal_coverage_upper = float(
                    (
                        int(resolved_covered.sum())
                        + int((~stratum_resolved).sum())
                        - int(unresolved_never_covered.sum())
                    )
                    / stratum_candidate_rows
                )
                baseline_marginal_coverage_lower = float(
                    (
                        int(baseline_resolved_covered.sum())
                        + int(baseline_unresolved_always_covered.sum())
                    )
                    / stratum_candidate_rows
                )
                baseline_marginal_coverage_upper = float(
                    (
                        int(baseline_resolved_covered.sum())
                        + int((~stratum_resolved).sum())
                        - int(baseline_unresolved_never_covered.sum())
                    )
                    / stratum_candidate_rows
                )
                gap_defined = resolved_y0 > 0 and resolved_y1 > 0
                if gap_defined:
                    gap_lower, gap_upper, gap_lower_witness, gap_upper_witness = (
                        sharp_class_coverage_gap_bounds(
                            stratum_zero,
                            stratum_one,
                            stratum_outcomes,
                        )
                    )
                    resolved_gap = float(
                        stratum_zero[stratum_resolved & (stratum_outcomes == 0.0)].mean()
                        - stratum_one[stratum_resolved & (stratum_outcomes == 1.0)].mean()
                    )
                    (
                        baseline_gap_lower,
                        baseline_gap_upper,
                        baseline_gap_lower_witness,
                        baseline_gap_upper_witness,
                    ) = sharp_class_coverage_gap_bounds(
                        baseline_stratum_zero,
                        baseline_stratum_one,
                        stratum_outcomes,
                    )
                    baseline_resolved_gap = float(
                        baseline_stratum_zero[stratum_resolved & (stratum_outcomes == 0.0)].mean()
                        - baseline_stratum_one[stratum_resolved & (stratum_outcomes == 1.0)].mean()
                    )
                else:
                    gap_lower = gap_upper = resolved_gap = float("nan")
                    gap_lower_witness = gap_upper_witness = -1
                    baseline_gap_lower = baseline_gap_upper = baseline_resolved_gap = float("nan")
                    baseline_gap_lower_witness = baseline_gap_upper_witness = -1
                stratum_set = _set_summary(stratum_zero, stratum_one)
                baseline_stratum_set = _set_summary(baseline_stratum_zero, baseline_stratum_one)
                stratum_rows.append(
                    {
                        "learner": learner,
                        "window_id": window_id,
                        "taxonomy_groups": int(taxonomy_groups),
                        "role": role,
                        "score_stratum": int(score_stratum),
                        "candidate_stratum_rows": stratum_candidate_rows,
                        "resolved_rows": int(stratum_resolved.sum()),
                        "unresolved_rows": int((~stratum_resolved).sum()),
                        "resolved_covered_rows": int(resolved_covered.sum()),
                        "coverage_resolved": float(resolved_covered.mean()),
                        "coverage_lower": marginal_coverage_lower,
                        "coverage_upper": marginal_coverage_upper,
                        "baseline_resolved_covered_rows": int(baseline_resolved_covered.sum()),
                        "baseline_coverage_resolved": float(baseline_resolved_covered.mean()),
                        "baseline_coverage_lower": baseline_marginal_coverage_lower,
                        "baseline_coverage_upper": baseline_marginal_coverage_upper,
                        "resolved_y0_rows": resolved_y0,
                        "resolved_y1_rows": resolved_y1,
                        "coverage_resolved_gap_y0_minus_y1": resolved_gap,
                        "conditional_gap_defined": gap_defined,
                        "coverage_gap_y0_minus_y1_lower": gap_lower,
                        "coverage_gap_y0_minus_y1_upper": gap_upper,
                        "gap_lower_unresolved_y1_rows": int(gap_lower_witness),
                        "gap_upper_unresolved_y1_rows": int(gap_upper_witness),
                        **stratum_set,
                        **{
                            f"baseline_{metric}": value
                            for metric, value in baseline_stratum_set.items()
                        },
                        "baseline_coverage_resolved_gap_y0_minus_y1": (baseline_resolved_gap),
                        "baseline_coverage_gap_y0_minus_y1_lower": baseline_gap_lower,
                        "baseline_coverage_gap_y0_minus_y1_upper": baseline_gap_upper,
                        "baseline_gap_lower_unresolved_y1_rows": int(baseline_gap_lower_witness),
                        "baseline_gap_upper_unresolved_y1_rows": int(baseline_gap_upper_witness),
                        "resolved_coverage_delta_label_mondrian_minus_baseline": float(
                            resolved_covered.mean() - baseline_resolved_covered.mean()
                        ),
                        "average_set_size_delta_label_mondrian_minus_baseline": float(
                            stratum_set["average_set_size"]
                            - baseline_stratum_set["average_set_size"]
                        ),
                        "sharp_endpoint_delta_reported": False,
                    }
                )

            set_reference = require_unique_row(
                baseline_sets,
                key={"learner": learner, "window_id": window_id},
                label="baseline set diagnostics",
            )
            coverage_reference = require_unique_row(
                baseline_coverage,
                key={"learner": learner, "window_id": window_id},
                label="baseline coverage",
            )
            reference_map = {
                "coverage_lower": float(coverage_reference["coverage_lower"]),
                "coverage_upper": float(coverage_reference["coverage_upper"]),
                "coverage_resolved": float(set_reference["coverage_resolved"]),
                "coverage_resolved_y0": float(set_reference["coverage_resolved_y0"]),
                "coverage_resolved_y1": float(set_reference["coverage_resolved_y1"]),
                "average_set_size": float(set_reference["average_set_size"]),
                "singleton_share": float(set_reference["singleton_share"]),
                "set_empty_share": float(set_reference["set_empty_share"]),
                "set_zero_only_share": float(set_reference["set_zero_only_share"]),
                "set_one_only_share": float(set_reference["set_one_only_share"]),
                "set_both_share": float(set_reference["set_both_share"]),
                "mean_width": float(set_reference["mean_width"]),
            }
            reconciliation_row: dict[str, Any] = {
                "learner": learner,
                "window_id": window_id,
                "taxonomy_groups": int(taxonomy_groups),
                "role": role,
            }
            for metric, reference_value in reference_map.items():
                actual_value = float(actual_baseline[metric])
                reconciliation_row[f"{metric}_actual"] = actual_value
                reconciliation_row[f"{metric}_reference"] = reference_value
                reconciliation_row[f"{metric}_difference"] = _require_close(
                    actual_value,
                    reference_value,
                    label=f"{learner}/{window_id} {metric}",
                    atol=reconciliation_atol,
                )
            reconciliation_rows.append(reconciliation_row)

    evaluation_result = pd.DataFrame(evaluation_rows)
    category_result = pd.DataFrame(category_rows)
    stratum_result = pd.DataFrame(stratum_rows)
    reconciliation_result = pd.DataFrame(reconciliation_rows)
    for frame, label in (
        (evaluation_result, "label-Mondrian evaluation"),
        (reconciliation_result, "marginal-baseline reconciliation"),
    ):
        require_exact_grid(
            frame,
            domains={"learner": tuple(learners), "window_id": tuple(window_ids)},
            label=label,
        )
    require_exact_grid(
        category_result,
        domains={
            "learner": tuple(learners),
            "window_id": tuple(window_ids),
            "score_stratum": tuple(range(taxonomy_groups)),
            "label": (0, 1),
        },
        label="label-Mondrian target categories",
    )
    require_exact_grid(
        stratum_result,
        domains={
            "learner": tuple(learners),
            "window_id": tuple(window_ids),
            "score_stratum": tuple(range(taxonomy_groups)),
        },
        label="label-Mondrian target strata",
    )
    defined_categories = category_result["conditional_coverage_defined"].astype(bool)
    for metric in (
        "coverage_label_lower",
        "coverage_label_upper",
        "baseline_coverage_label_lower",
        "baseline_coverage_label_upper",
    ):
        if not bool(
            np.isfinite(category_result.loc[defined_categories, metric].to_numpy(dtype=float)).all()
        ):
            raise RuntimeError(f"Label-Mondrian target categories contain nonfinite {metric}.")
    present_categories = category_result["score_stratum_present"].astype(bool)
    for metric in ("label_prevalence_lower", "label_prevalence_upper"):
        if not bool(
            np.isfinite(category_result.loc[present_categories, metric].to_numpy(dtype=float)).all()
        ):
            raise RuntimeError(f"Label-Mondrian target categories contain nonfinite {metric}.")
    if not bool(
        category_result.loc[defined_categories, "coverage_label_lower"]
        .le(category_result.loc[defined_categories, "coverage_label_upper"])
        .all()
    ):
        raise RuntimeError("Label-Mondrian category coverage bounds are reversed.")
    if not bool(
        category_result.loc[defined_categories, "baseline_coverage_label_lower"]
        .le(category_result.loc[defined_categories, "baseline_coverage_label_upper"])
        .all()
    ):
        raise RuntimeError("Baseline category coverage bounds are reversed.")
    allowed_states = {
        "robust_shortfall",
        "robust_at_or_above_nominal",
        "crosses_nominal",
        "undefined",
    }
    for state_column in (
        "identification_state_at_nominal",
        "baseline_identification_state_at_nominal",
    ):
        if set(category_result[state_column].astype(str).unique()).difference(allowed_states):
            raise RuntimeError(f"Label-Mondrian category contains invalid {state_column}.")
    if not bool(
        category_result["label_prevalence_lower"]
        .le(category_result["label_prevalence_upper"])
        .all()
    ):
        raise RuntimeError("Label-Mondrian category prevalence bounds are reversed.")
    defined_gaps = stratum_result["conditional_gap_defined"].astype(bool)
    for metric in (
        "coverage_resolved",
        "coverage_lower",
        "coverage_upper",
        "baseline_coverage_resolved",
        "baseline_coverage_lower",
        "baseline_coverage_upper",
    ):
        if not bool(np.isfinite(stratum_result[metric].to_numpy(dtype=float)).all()):
            raise RuntimeError(f"Label-Mondrian target strata contain nonfinite {metric}.")
    if not bool(stratum_result["coverage_lower"].le(stratum_result["coverage_upper"]).all()):
        raise RuntimeError("Label-Mondrian stratum marginal coverage bounds are reversed.")
    if not bool(
        stratum_result["baseline_coverage_lower"]
        .le(stratum_result["baseline_coverage_upper"])
        .all()
    ):
        raise RuntimeError("Baseline stratum marginal coverage bounds are reversed.")
    for metric in (
        "coverage_gap_y0_minus_y1_lower",
        "coverage_gap_y0_minus_y1_upper",
        "baseline_coverage_gap_y0_minus_y1_lower",
        "baseline_coverage_gap_y0_minus_y1_upper",
    ):
        if not bool(
            np.isfinite(stratum_result.loc[defined_gaps, metric].to_numpy(dtype=float)).all()
        ):
            raise RuntimeError(f"Label-Mondrian target strata contain nonfinite {metric}.")
    if not bool(
        stratum_result.loc[defined_gaps, "coverage_gap_y0_minus_y1_lower"]
        .le(stratum_result.loc[defined_gaps, "coverage_gap_y0_minus_y1_upper"])
        .all()
    ):
        raise RuntimeError("Label-Mondrian stratum gap bounds are reversed.")
    if not bool(
        stratum_result.loc[defined_gaps, "baseline_coverage_gap_y0_minus_y1_lower"]
        .le(stratum_result.loc[defined_gaps, "baseline_coverage_gap_y0_minus_y1_upper"])
        .all()
    ):
        raise RuntimeError("Baseline stratum gap bounds are reversed.")
    for metric in (
        "average_set_size",
        "singleton_share",
        "set_empty_share",
        "set_zero_only_share",
        "set_one_only_share",
        "set_both_share",
    ):
        if not bool(np.isfinite(evaluation_result[metric].to_numpy(dtype=float)).all()):
            raise RuntimeError(f"Label-Mondrian evaluation contains nonfinite {metric}.")
    if not bool(
        np.isclose(
            evaluation_result["average_set_size"],
            evaluation_result["singleton_share"] + 2.0 * evaluation_result["set_both_share"],
            atol=reconciliation_atol,
            rtol=reconciliation_atol,
        ).all()
    ):
        raise RuntimeError("Label-Mondrian AvgC identity failed.")
    if not bool(
        np.isclose(
            evaluation_result["average_set_size"],
            1.0 - evaluation_result["set_empty_share"] + evaluation_result["set_both_share"],
            atol=reconciliation_atol,
            rtol=reconciliation_atol,
        ).all()
    ):
        raise RuntimeError("Label-Mondrian set-partition identity failed.")
    learner_order = {name: index for index, name in enumerate(learners)}
    window_order = {name: index for index, name in enumerate(window_ids)}
    for frame in (
        evaluation_result,
        category_result,
        stratum_result,
        reconciliation_result,
    ):
        frame["_learner_order"] = frame["learner"].map(learner_order)
        frame["_window_order"] = frame["window_id"].map(window_order)
        sort_columns = ["_learner_order", "_window_order"]
        if "score_stratum" in frame.columns:
            sort_columns.append("score_stratum")
        if "label" in frame.columns:
            sort_columns.append("label")
        frame.sort_values(sort_columns, inplace=True, kind="stable")
        frame.drop(columns=["_learner_order", "_window_order"], inplace=True)
        frame.reset_index(drop=True, inplace=True)
    return evaluation_result, category_result, stratum_result, reconciliation_result
