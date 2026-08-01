"""Complete, outcome-free census of exact binary conformal phase geometry.

The module accepts only frozen calibration rows and frozen calibration-stratum
statistics.  It deliberately emits a complete identifier-bearing cell table
and a separate permutation-symmetric global summary.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from itertools import product
from typing import Any

import numpy as np
import pandas as pd

FIT_INPUT_COLUMNS = (
    "id",
    "learner",
    "window_id",
    "taxonomy_groups",
    "conformal_group",
    "pd_point",
    "terminal_default",
)

FROZEN_INPUT_COLUMNS = (
    "learner",
    "window_id",
    "taxonomy_groups",
    "conformal_group",
    "fit_rows",
    "finite_sample_rank",
    "fit_residual_quantile",
    "fit_score_min",
    "fit_score_max",
    "fit_residual_below_threshold",
    "fit_residual_equal_threshold",
    "fit_residual_above_threshold",
)

CELL_KEY_COLUMNS = ("learner", "window_id", "conformal_group")

CELL_OUTPUT_COLUMNS = (
    "learner",
    "window_id",
    "taxonomy_groups",
    "conformal_group",
    "alpha",
    "fit_rows",
    "fit_defaults",
    "fit_nondefaults",
    "fit_default_prevalence",
    "finite_sample_rank",
    "boundary_count",
    "boundary_closed_form",
    "phase_margin",
    "frozen_fit_rows",
    "frozen_finite_sample_rank",
    "frozen_threshold",
    "recomputed_threshold",
    "threshold_gap",
    "threshold_below_half",
    "recomputed_residual_below_threshold",
    "recomputed_residual_equal_threshold",
    "recomputed_residual_above_threshold",
    "frozen_residual_below_threshold",
    "frozen_residual_equal_threshold",
    "frozen_residual_above_threshold",
    "recomputed_score_min",
    "recomputed_score_max",
    "frozen_score_min",
    "frozen_score_max",
    "fit_score_max_nondefault",
    "fit_score_max_default",
    "both_classes_nonempty",
    "count_nondefault_score_below_half",
    "count_default_score_above_half",
    "exact_half_criterion_expected",
    "exact_half_criterion_observed",
    "exact_half_criterion_pass",
    "max_score_below_half_condition",
    "phase_margin_half_check_applicable",
    "phase_margin_half_check_pass",
    "no_interleaving_condition",
    "expected_threshold_source_branch",
    "threshold_source_branch",
    "phase_margin_source_check_applicable",
    "phase_margin_source_check_pass",
    "boundary_identity_reconciles",
    "rows_reconcile",
    "rank_reconciles",
    "threshold_reconciles",
    "tie_counts_reconcile",
    "score_extrema_reconcile",
    "rank_bracket_reconciles",
    "cell_reconciles",
)


def _positive_integer(value: Any, *, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a positive integer.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a positive integer.") from exc
    if not math.isfinite(number) or number < 1 or not number.is_integer():
        raise ValueError(f"{label} must be a positive integer.")
    return int(number)


def _validate_alpha(value: Any) -> float:
    try:
        alpha = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("alpha must be finite and strictly between zero and one.") from exc
    if not math.isfinite(alpha) or not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be finite and strictly between zero and one.")
    return alpha


def _validate_tolerance(value: Any) -> float:
    try:
        tolerance = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("threshold_tolerance must be finite and nonnegative.") from exc
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("threshold_tolerance must be finite and nonnegative.")
    return tolerance


def _declared_domain(values: Sequence[str], *, label: str) -> tuple[str, ...]:
    domain = tuple(str(value).strip() for value in values)
    if not domain or any(not value for value in domain):
        raise ValueError(f"The declared {label} domain must contain nonempty strings.")
    if len(set(domain)) != len(domain):
        raise ValueError(f"The declared {label} domain contains duplicates.")
    return domain


def _require_exact_columns(frame: pd.DataFrame, expected: Sequence[str], *, label: str) -> None:
    expected_set = set(expected)
    actual_set = set(frame.columns)
    missing = expected_set.difference(actual_set)
    extra = actual_set.difference(expected_set)
    if missing or extra:
        raise ValueError(
            f"{label} must contain exactly the allowlisted columns; "
            f"missing={sorted(missing)}, extra={sorted(extra)}."
        )


def _string_series(series: pd.Series, *, label: str) -> pd.Series:
    if bool(series.isna().any()):
        raise ValueError(f"{label} contains a missing identifier.")
    result = series.astype(str).str.strip()
    if bool(result.eq("").any()):
        raise ValueError(f"{label} contains a blank identifier.")
    return result


def _numeric_series(series: pd.Series, *, label: str) -> pd.Series:
    result = pd.to_numeric(series, errors="coerce")
    values = result.to_numpy(dtype=float)
    if not bool(np.isfinite(values).all()):
        raise ValueError(f"{label} must contain finite numeric values.")
    return pd.Series(values, index=series.index, name=series.name)


def _integer_series(
    series: pd.Series,
    *,
    label: str,
    minimum: int | None = None,
    maximum: int | None = None,
) -> pd.Series:
    numeric = _numeric_series(series, label=label)
    values = numeric.to_numpy(dtype=float)
    if not bool(np.equal(values, np.floor(values)).all()):
        raise ValueError(f"{label} must contain integers.")
    integers = values.astype(np.int64)
    if minimum is not None and not bool((integers >= minimum).all()):
        raise ValueError(f"{label} contains a value below {minimum}.")
    if maximum is not None and not bool((integers <= maximum).all()):
        raise ValueError(f"{label} contains a value above {maximum}.")
    return pd.Series(integers, index=series.index, name=series.name)


def finite_sample_rank(n: int, *, alpha: float) -> int:
    """Return the uncapped split-conformal order-statistic rank."""
    rows = _positive_integer(n, label="n")
    level = _validate_alpha(alpha)
    return int(math.ceil((rows + 1) * (1.0 - level)))


def _expected_keys(
    learners: Sequence[str], window_ids: Sequence[str], taxonomy_groups: int
) -> tuple[tuple[str, str, int], ...]:
    return tuple(product(learners, window_ids, range(taxonomy_groups)))


def _require_exact_grid(
    frame: pd.DataFrame,
    *,
    expected_keys: Sequence[tuple[str, str, int]],
    label: str,
) -> None:
    actual = {
        (str(learner), str(window_id), int(group))
        for learner, window_id, group in frame.loc[:, list(CELL_KEY_COLUMNS)].itertuples(
            index=False, name=None
        )
    }
    expected = set(expected_keys)
    missing = expected.difference(actual)
    extra = actual.difference(expected)
    if missing or extra:
        raise RuntimeError(
            f"{label} does not form the declared complete grid; "
            f"missing_cells={len(missing)}, extra_cells={len(extra)}."
        )


def _prepare_fit_rows(
    frame: pd.DataFrame,
    *,
    taxonomy_groups: int,
    expected_keys: Sequence[tuple[str, str, int]],
) -> pd.DataFrame:
    _require_exact_columns(frame, FIT_INPUT_COLUMNS, label="Calibration-row input")
    fit = frame.loc[:, list(FIT_INPUT_COLUMNS)].copy()
    fit["learner"] = _string_series(fit["learner"], label="Calibration learner")
    fit["window_id"] = _string_series(fit["window_id"], label="Calibration window")
    fit["taxonomy_groups"] = _integer_series(
        fit["taxonomy_groups"], label="Calibration taxonomy_groups", minimum=1
    )
    fit = fit.loc[fit["taxonomy_groups"].eq(taxonomy_groups)].copy()
    if fit.empty:
        raise RuntimeError("The declared calibration taxonomy has no rows.")
    fit["conformal_group"] = _integer_series(
        fit["conformal_group"],
        label="Calibration conformal_group",
        minimum=0,
        maximum=taxonomy_groups - 1,
    )
    fit["pd_point"] = _numeric_series(fit["pd_point"], label="Calibration score")
    if not bool(fit["pd_point"].between(0.0, 1.0).all()):
        raise ValueError("Calibration scores must lie inside [0, 1].")
    fit["terminal_default"] = _numeric_series(
        fit["terminal_default"], label="Calibration binary label"
    )
    if not bool(fit["terminal_default"].isin((0.0, 1.0)).all()):
        raise ValueError("Calibration labels must be exactly binary.")
    if bool(fit["id"].isna().any()):
        raise ValueError("Calibration id contains a missing value.")
    duplicate_id_key = ["learner", "window_id", "id"]
    if bool(fit.duplicated(duplicate_id_key).any()):
        raise RuntimeError("The calibration input contains a duplicate fit ID key.")
    _require_exact_grid(fit, expected_keys=expected_keys, label="Calibration rows")
    return fit


def _prepare_frozen_cells(
    frame: pd.DataFrame,
    *,
    taxonomy_groups: int,
    expected_keys: Sequence[tuple[str, str, int]],
) -> pd.DataFrame:
    _require_exact_columns(frame, FROZEN_INPUT_COLUMNS, label="Frozen-stratum input")
    frozen = frame.loc[:, list(FROZEN_INPUT_COLUMNS)].copy()
    frozen["learner"] = _string_series(frozen["learner"], label="Frozen learner")
    frozen["window_id"] = _string_series(frozen["window_id"], label="Frozen window")
    frozen["taxonomy_groups"] = _integer_series(
        frozen["taxonomy_groups"], label="Frozen taxonomy_groups", minimum=1
    )
    frozen = frozen.loc[frozen["taxonomy_groups"].eq(taxonomy_groups)].copy()
    if frozen.empty:
        raise RuntimeError("The declared frozen taxonomy has no rows.")
    frozen["conformal_group"] = _integer_series(
        frozen["conformal_group"],
        label="Frozen conformal_group",
        minimum=0,
        maximum=taxonomy_groups - 1,
    )
    integer_columns = (
        "fit_rows",
        "finite_sample_rank",
        "fit_residual_below_threshold",
        "fit_residual_equal_threshold",
        "fit_residual_above_threshold",
    )
    for column in integer_columns:
        minimum = 1 if column in {"fit_rows", "finite_sample_rank"} else 0
        frozen[column] = _integer_series(frozen[column], label=f"Frozen {column}", minimum=minimum)
    float_columns = ("fit_residual_quantile", "fit_score_min", "fit_score_max")
    for column in float_columns:
        frozen[column] = _numeric_series(frozen[column], label=f"Frozen {column}")
        if not bool(frozen[column].between(0.0, 1.0).all()):
            raise ValueError(f"Frozen {column} must lie inside [0, 1].")
    if not bool(frozen["fit_score_min"].le(frozen["fit_score_max"]).all()):
        raise RuntimeError("A frozen score minimum exceeds its maximum.")
    if not bool(frozen["finite_sample_rank"].le(frozen["fit_rows"]).all()):
        raise RuntimeError("A frozen finite-sample rank is not attained.")
    tie_total = (
        frozen["fit_residual_below_threshold"]
        + frozen["fit_residual_equal_threshold"]
        + frozen["fit_residual_above_threshold"]
    )
    if not bool(tie_total.eq(frozen["fit_rows"]).all()):
        raise RuntimeError("Frozen residual tie counts do not sum to fit_rows.")
    bracket = frozen["fit_residual_below_threshold"].lt(frozen["finite_sample_rank"]) & frozen[
        "finite_sample_rank"
    ].le(frozen["fit_residual_below_threshold"] + frozen["fit_residual_equal_threshold"])
    if not bool(bracket.all()):
        raise RuntimeError("Frozen residual tie counts do not bracket the declared rank.")
    if bool(frozen.duplicated(list(CELL_KEY_COLUMNS)).any()):
        raise RuntimeError("The frozen input contains a duplicate cell key.")
    _require_exact_grid(frozen, expected_keys=expected_keys, label="Frozen strata")
    if len(frozen) != len(expected_keys):
        raise RuntimeError("The frozen cell table is not one row per declared cell.")
    return frozen


def _close(left: float, right: float, *, tolerance: float) -> bool:
    return bool(np.isclose(left, right, atol=tolerance, rtol=0.0))


def _cell_row(
    fit: pd.DataFrame,
    frozen: pd.Series,
    *,
    learner: str,
    window_id: str,
    conformal_group: int,
    taxonomy_groups: int,
    alpha: float,
    tolerance: float,
) -> dict[str, Any]:
    scores = fit["pd_point"].to_numpy(dtype=float)
    labels = fit["terminal_default"].to_numpy(dtype=float)
    rows = int(len(fit))
    rank = finite_sample_rank(rows, alpha=alpha)
    if rank > rows:
        raise RuntimeError("A calibration cell requires a capped finite-sample rank.")

    defaults = int(np.sum(labels == 1.0))
    nondefaults = rows - defaults
    both_classes = defaults > 0 and nondefaults > 0
    if not both_classes:
        raise RuntimeError("A calibration cell has an empty binary class.")

    residuals = np.abs(labels - scores)
    threshold = float(np.partition(residuals, rank - 1)[rank - 1])
    residual_below = int(np.sum(residuals < threshold))
    residual_equal = int(np.sum(residuals == threshold))
    residual_above = int(np.sum(residuals > threshold))
    rank_bracket = (
        residual_below < rank <= residual_below + residual_equal
        and residual_below + residual_equal + residual_above == rows
    )
    if not rank_bracket:
        raise RuntimeError("A recomputed threshold does not bracket its exact rank.")

    boundary = rows - rank
    boundary_closed_form = math.floor(alpha * (rows + 1)) - 1
    boundary_identity = boundary == boundary_closed_form
    if not boundary_identity:
        raise RuntimeError("The finite-rank boundary left its closed form.")
    margin = defaults - boundary

    count_nondefault_below_half = int(np.sum((labels == 0.0) & (scores < 0.5)))
    count_default_above_half = int(np.sum((labels == 1.0) & (scores > 0.5)))
    half_expected = count_nondefault_below_half + count_default_above_half >= rank
    half_observed = threshold < 0.5
    exact_half_pass = half_expected == half_observed
    if not exact_half_pass:
        raise RuntimeError("The exact half-threshold identity failed in a calibration cell.")

    score_min = float(scores.min())
    score_max = float(scores.max())
    score_max_nondefault = float(scores[labels == 0.0].max())
    score_max_default = float(scores[labels == 1.0].max())

    all_scores_below_half = score_max < 0.5
    margin_half_pass = True
    if all_scores_below_half:
        margin_half_pass = (margin <= 0) == half_observed
        if not margin_half_pass:
            raise RuntimeError("The conditional phase-margin half check failed.")

    no_interleaving = score_max_nondefault + score_max_default < 1.0
    expected_source = "condition_not_met"
    source = "condition_not_met"
    margin_source_pass = True
    if no_interleaving:
        expected_source = "nondefault_mirror" if margin <= 0 else "default_mirror"
        nondefault_residuals = residuals[labels == 0.0]
        default_residuals = residuals[labels == 1.0]
        in_nondefault = bool(np.equal(nondefault_residuals, threshold).any())
        in_default = bool(np.equal(default_residuals, threshold).any())
        if in_nondefault == in_default:
            raise RuntimeError("The no-interleaving threshold source is not unique.")
        source = "nondefault_mirror" if in_nondefault else "default_mirror"
        margin_source_pass = source == expected_source
        if not margin_source_pass:
            raise RuntimeError("The conditional phase-margin source check failed.")

    frozen_rows = int(frozen["fit_rows"])
    frozen_rank = int(frozen["finite_sample_rank"])
    frozen_threshold = float(frozen["fit_residual_quantile"])
    frozen_below = int(frozen["fit_residual_below_threshold"])
    frozen_equal = int(frozen["fit_residual_equal_threshold"])
    frozen_above = int(frozen["fit_residual_above_threshold"])
    frozen_score_min = float(frozen["fit_score_min"])
    frozen_score_max = float(frozen["fit_score_max"])
    rows_reconcile = rows == frozen_rows
    rank_reconciles = rank == frozen_rank
    threshold_reconciles = _close(threshold, frozen_threshold, tolerance=tolerance)
    tie_counts_reconcile = (
        residual_below == frozen_below
        and residual_equal == frozen_equal
        and residual_above == frozen_above
    )
    score_extrema_reconcile = _close(score_min, frozen_score_min, tolerance=tolerance) and _close(
        score_max, frozen_score_max, tolerance=tolerance
    )
    cell_reconciles = (
        rows_reconcile
        and rank_reconciles
        and threshold_reconciles
        and tie_counts_reconcile
        and score_extrema_reconcile
        and rank_bracket
        and boundary_identity
        and exact_half_pass
        and margin_half_pass
        and margin_source_pass
    )
    if not cell_reconciles:
        key = (learner, window_id, conformal_group)
        raise RuntimeError(f"Calibration cell {key!r} does not reconcile to its frozen row.")

    return {
        "learner": learner,
        "window_id": window_id,
        "taxonomy_groups": taxonomy_groups,
        "conformal_group": conformal_group,
        "alpha": alpha,
        "fit_rows": rows,
        "fit_defaults": defaults,
        "fit_nondefaults": nondefaults,
        "fit_default_prevalence": float(defaults / rows),
        "finite_sample_rank": rank,
        "boundary_count": boundary,
        "boundary_closed_form": boundary_closed_form,
        "phase_margin": margin,
        "frozen_fit_rows": frozen_rows,
        "frozen_finite_sample_rank": frozen_rank,
        "frozen_threshold": frozen_threshold,
        "recomputed_threshold": threshold,
        "threshold_gap": float(abs(threshold - frozen_threshold)),
        "threshold_below_half": half_observed,
        "recomputed_residual_below_threshold": residual_below,
        "recomputed_residual_equal_threshold": residual_equal,
        "recomputed_residual_above_threshold": residual_above,
        "frozen_residual_below_threshold": frozen_below,
        "frozen_residual_equal_threshold": frozen_equal,
        "frozen_residual_above_threshold": frozen_above,
        "recomputed_score_min": score_min,
        "recomputed_score_max": score_max,
        "frozen_score_min": frozen_score_min,
        "frozen_score_max": frozen_score_max,
        "fit_score_max_nondefault": score_max_nondefault,
        "fit_score_max_default": score_max_default,
        "both_classes_nonempty": both_classes,
        "count_nondefault_score_below_half": count_nondefault_below_half,
        "count_default_score_above_half": count_default_above_half,
        "exact_half_criterion_expected": half_expected,
        "exact_half_criterion_observed": half_observed,
        "exact_half_criterion_pass": exact_half_pass,
        "max_score_below_half_condition": all_scores_below_half,
        "phase_margin_half_check_applicable": all_scores_below_half,
        "phase_margin_half_check_pass": margin_half_pass,
        "no_interleaving_condition": no_interleaving,
        "expected_threshold_source_branch": expected_source,
        "threshold_source_branch": source,
        "phase_margin_source_check_applicable": no_interleaving,
        "phase_margin_source_check_pass": margin_source_pass,
        "boundary_identity_reconciles": boundary_identity,
        "rows_reconcile": rows_reconcile,
        "rank_reconciles": rank_reconciles,
        "threshold_reconciles": threshold_reconciles,
        "tie_counts_reconcile": tie_counts_reconcile,
        "score_extrema_reconcile": score_extrema_reconcile,
        "rank_bracket_reconciles": rank_bracket,
        "cell_reconciles": cell_reconciles,
    }


def _global_summary(
    table: pd.DataFrame,
    *,
    learner_count: int,
    window_count: int,
    taxonomy_groups: int,
    expected_cells: int,
) -> dict[str, Any]:
    half_applicable = table["phase_margin_half_check_applicable"].astype(bool)
    source_applicable = table["phase_margin_source_check_applicable"].astype(bool)
    source = table.loc[source_applicable, "threshold_source_branch"]
    counts = {
        "cells_both_classes_nonempty": int(table["both_classes_nonempty"].sum()),
        "cells_with_uncapped_rank": int(table["finite_sample_rank"].le(table["fit_rows"]).sum()),
        "cells_threshold_below_half": int(table["threshold_below_half"].sum()),
        "cells_threshold_at_or_above_half": int((~table["threshold_below_half"]).sum()),
        "cells_phase_margin_nonpositive": int(table["phase_margin"].le(0).sum()),
        "cells_phase_margin_positive": int(table["phase_margin"].gt(0).sum()),
        "cells_exact_half_criterion_pass": int(table["exact_half_criterion_pass"].sum()),
        "cells_max_score_below_half_condition": int(half_applicable.sum()),
        "cells_phase_margin_half_check_pass_when_applicable": int(
            table.loc[half_applicable, "phase_margin_half_check_pass"].sum()
        ),
        "cells_no_interleaving_condition": int(source_applicable.sum()),
        "cells_phase_margin_source_check_pass_when_applicable": int(
            table.loc[source_applicable, "phase_margin_source_check_pass"].sum()
        ),
        "cells_nondefault_mirror_source_under_condition": int(source.eq("nondefault_mirror").sum()),
        "cells_default_mirror_source_under_condition": int(source.eq("default_mirror").sum()),
        "cells_reconciled": int(table["cell_reconciles"].sum()),
    }
    all_condition_checks = bool(
        table.loc[half_applicable, "phase_margin_half_check_pass"].all()
        and table.loc[source_applicable, "phase_margin_source_check_pass"].all()
    )
    expected_cells_per_stratum = learner_count * window_count
    ordered_strata: list[dict[str, Any]] = []
    for group in range(taxonomy_groups):
        stratum = table.loc[table["conformal_group"].eq(group)]
        stratum_half = stratum["phase_margin_half_check_applicable"].astype(bool)
        stratum_source = stratum["phase_margin_source_check_applicable"].astype(bool)
        if len(stratum) != expected_cells_per_stratum:
            raise RuntimeError(
                f"Ordered conformal group {group} is incomplete: "
                f"{len(stratum)} != {expected_cells_per_stratum}."
            )
        ordered_strata.append(
            {
                "conformal_group": group,
                "expected_cells": expected_cells_per_stratum,
                "observed_cells": int(len(stratum)),
                "cells_both_classes_nonempty": int(stratum["both_classes_nonempty"].sum()),
                "cells_with_uncapped_rank": int(
                    stratum["finite_sample_rank"].le(stratum["fit_rows"]).sum()
                ),
                "cells_threshold_below_half": int(stratum["threshold_below_half"].sum()),
                "cells_phase_margin_nonpositive": int(stratum["phase_margin"].le(0).sum()),
                "cells_exact_half_criterion_pass": int(stratum["exact_half_criterion_pass"].sum()),
                "cells_max_score_below_half_condition": int(stratum_half.sum()),
                "cells_phase_margin_half_check_pass_when_applicable": int(
                    stratum.loc[stratum_half, "phase_margin_half_check_pass"].sum()
                ),
                "cells_no_interleaving_condition": int(stratum_source.sum()),
                "cells_phase_margin_source_check_pass_when_applicable": int(
                    stratum.loc[stratum_source, "phase_margin_source_check_pass"].sum()
                ),
                "cells_reconciled": int(stratum["cell_reconciles"].sum()),
            }
        )
    return {
        "status": "complete_outcome_free_binary_phase_census",
        "design_cardinalities": {
            "learner_count": learner_count,
            "window_count": window_count,
            "stratum_count_per_learner_window": taxonomy_groups,
            "expected_cells": expected_cells,
            "observed_cells": int(len(table)),
        },
        "global_counts": counts,
        "complete_ordered_stratum_summary": ordered_strata,
        "global_checks": {
            "complete_grid": len(table) == expected_cells,
            "all_cells_both_classes_nonempty": bool(table["both_classes_nonempty"].all()),
            "all_ranks_uncapped": bool(table["finite_sample_rank"].le(table["fit_rows"]).all()),
            "boundary_identity_all_cells": bool(table["boundary_identity_reconciles"].all()),
            "exact_half_criterion_all_cells": bool(table["exact_half_criterion_pass"].all()),
            "all_applicable_condition_checks_pass": all_condition_checks,
            "all_cells_reconcile": bool(table["cell_reconciles"].all()),
        },
        "reporting_contract": {
            "complete_identifier_bearing_cell_table": True,
            "learner_window_summary_permutation_symmetric": True,
            "complete_ordered_stratum_summary": True,
            "all_strata_reported_without_selection": True,
            "learner_window_identifier_breakdowns": False,
            "learner_window_identifier_values_in_summary": False,
            "cell_extrema_in_summary": False,
        },
    }


def build_binary_phase_census(
    calibration_rows: pd.DataFrame,
    frozen_strata: pd.DataFrame,
    *,
    expected_learners: Sequence[str],
    expected_window_ids: Sequence[str],
    taxonomy_groups: int,
    expected_cells: int,
    alpha: float = 0.10,
    threshold_tolerance: float = 1.0e-15,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build and reconcile the complete cell table and symmetric summary."""
    learners = _declared_domain(expected_learners, label="learner")
    windows = _declared_domain(expected_window_ids, label="window")
    groups = _positive_integer(taxonomy_groups, label="taxonomy_groups")
    cells = _positive_integer(expected_cells, label="expected_cells")
    level = _validate_alpha(alpha)
    tolerance = _validate_tolerance(threshold_tolerance)
    expected = _expected_keys(learners, windows, groups)
    if cells != len(expected):
        raise ValueError(
            "expected_cells must equal the complete learner-by-window-by-stratum product."
        )

    fit = _prepare_fit_rows(
        calibration_rows,
        taxonomy_groups=groups,
        expected_keys=expected,
    )
    frozen = _prepare_frozen_cells(
        frozen_strata,
        taxonomy_groups=groups,
        expected_keys=expected,
    )
    fit_groups = {
        (str(key[0]), str(key[1]), int(key[2])): group
        for key, group in fit.groupby(list(CELL_KEY_COLUMNS), sort=False, observed=True)
    }
    frozen_rows = {
        (str(row["learner"]), str(row["window_id"]), int(row["conformal_group"])): row
        for _, row in frozen.iterrows()
    }
    rows = [
        _cell_row(
            fit_groups[key],
            frozen_rows[key],
            learner=key[0],
            window_id=key[1],
            conformal_group=key[2],
            taxonomy_groups=groups,
            alpha=level,
            tolerance=tolerance,
        )
        for key in expected
    ]
    table = pd.DataFrame(rows, columns=list(CELL_OUTPUT_COLUMNS))
    if len(table) != cells:
        raise RuntimeError("The computed census is incomplete.")
    summary = _global_summary(
        table,
        learner_count=len(learners),
        window_count=len(windows),
        taxonomy_groups=groups,
        expected_cells=cells,
    )
    return table, summary
