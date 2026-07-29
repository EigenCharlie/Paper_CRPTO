"""Exact binary split-conformal geometry over frozen calibration blocks.

The absolute-residual nonconformity ``s(y) = |y - p|`` is the binary case of the
least-ambiguous set-valued classifier score. Its calibration residuals are the
multiset sum of two mirror samples,

    R = {{ p_i : Y_i = 0 }}  (+)  {{ 1 - p_i : Y_i = 1 }},

so the fitted threshold is exactly ``c = R_(k)`` with ``k = ceil((n+1)(1-alpha))``.
This module recomputes that order statistic from the frozen calibration rows,
reconciles it against the frozen recipe quantile, and reports the phase margin

    m = D - (n - k) = D - floor(alpha * (n + 1)) + 1,

whose sign determines which mirror sample supplies the threshold.

Boundary conditions are reported, never assumed. The regime equivalence anchored
at one half requires ``max_i p_i < 1/2`` on the calibration block; the weaker
no-interleaving condition ``max_{Y=0} p + max_{Y=1} p < 1`` governs only which
sample supplies the threshold. Target-side statements require their own support
conditions, which are emitted as explicit flags rather than presumed.

Nothing here selects a learner, window, stratum, or recipe, and nothing here
establishes selected-set or funded-set validity.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REQUIRED_FIT_COLUMNS = (
    "learner",
    "window_id",
    "taxonomy_groups",
    "conformal_group",
    "pd_point",
    "terminal_default",
)

LOW_REGIME = "low"
HIGH_REGIME = "high"


def _positive_integer(value: Any, *, label: str) -> int:
    """Return an explicitly integral positive scalar without truncation."""
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{label} must be a positive integer.")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be a positive integer.") from error
    if not math.isfinite(numeric) or numeric < 1.0 or not numeric.is_integer():
        raise ValueError(f"{label} must be a positive integer.")
    return int(numeric)


def _integral_array(
    values: pd.Series,
    *,
    label: str,
    minimum: int | None = None,
    maximum: int | None = None,
) -> np.ndarray:
    """Validate integral scientific keys or counts before converting them."""
    if not pd.api.types.is_numeric_dtype(values):
        raise ValueError(f"{label} must contain finite integers.")
    numeric = values.to_numpy(dtype=float)
    if not bool(np.isfinite(numeric).all()) or not bool(np.equal(numeric, np.floor(numeric)).all()):
        raise ValueError(f"{label} must contain finite integers.")
    if bool(np.any(np.abs(numeric) > 2**53)):
        raise ValueError(f"{label} exceed the supported integer range.")
    if minimum is not None and bool(np.any(numeric < minimum)):
        raise ValueError(f"{label} must be at least {minimum}.")
    if maximum is not None and bool(np.any(numeric > maximum)):
        raise ValueError(f"{label} must be at most {maximum}.")
    return numeric.astype(np.int64)


def _declared_string_domain(values: Sequence[str], *, label: str) -> tuple[str, ...]:
    """Return a nonempty, duplicate-free declared identity domain."""
    if isinstance(values, (str, bytes)):
        raise ValueError(f"The expected {label} domain must be a sequence of identities.")
    raw = tuple(values)
    if not raw or any(not isinstance(value, str) or not value for value in raw):
        raise ValueError(f"The expected {label} domain must be nonempty.")
    normalized = tuple(str(value) for value in raw)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"The expected {label} domain contains duplicate identities.")
    return normalized


def _require_exact_domain(
    frame: pd.DataFrame,
    *,
    column: str,
    expected: Sequence[str],
    label: str,
) -> None:
    """Fail when an entire declared identity is absent or an extra one appears."""
    if frame[column].isna().any():
        raise RuntimeError(f"The {label} domain contains a missing identity.")
    actual = set(frame[column].astype(str).unique())
    declared = set(expected)
    if actual != declared:
        missing = sorted(declared.difference(actual))
        unexpected = sorted(actual.difference(declared))
        raise RuntimeError(
            f"The {label} domain left the exact declared identities: "
            f"missing={missing}, unexpected={unexpected}."
        )


def finite_sample_rank(count: int, *, alpha: float) -> int:
    """Return the split-conformal order-statistic rank for a calibration block."""
    sample_count = _positive_integer(count, label="Calibration-block row count")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie strictly inside the unit interval.")
    return int(math.ceil((sample_count + 1) * (1.0 - alpha)))


def mirror_residuals(scores: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Return the calibration residual multiset ``|y - p|`` for binary labels."""
    point = np.asarray(scores, dtype=float)
    outcome = np.asarray(labels, dtype=float)
    if point.shape != outcome.shape or point.ndim != 1:
        raise ValueError("Scores and labels must be aligned one-dimensional arrays.")
    if not bool(np.isfinite(point).all()):
        raise ValueError("Calibration scores must be finite.")
    if bool(np.any(point < 0.0) or np.any(point > 1.0)):
        raise ValueError("The order-statistic characterization requires scores in [0, 1].")
    if not set(np.unique(outcome)).issubset({0.0, 1.0}):
        raise ValueError("Calibration labels must be binary.")
    return np.abs(outcome - point)


def _stratum_record(
    *,
    learner: str,
    window_id: str,
    taxonomy_groups: int,
    conformal_group: int,
    scores: np.ndarray,
    labels: np.ndarray,
    alpha: float,
) -> dict[str, object]:
    residuals = mirror_residuals(scores, labels)
    count = int(scores.size)
    rank = finite_sample_rank(count, alpha=alpha)
    defaults = int(labels.sum())
    nondefaults = count - defaults
    boundary = count - rank

    if rank <= count:
        threshold = float(np.sort(residuals)[rank - 1])
        threshold_is_capped = False
    else:
        # The frozen implementation returns 1.0 rather than an infinite threshold.
        threshold = 1.0
        threshold_is_capped = True

    nondefault_scores = scores[labels == 0.0]
    default_scores = scores[labels == 1.0]
    max_nondefault = float(nondefault_scores.max()) if nondefault_scores.size else float("-inf")
    max_default = float(default_scores.max()) if default_scores.size else float("-inf")

    # (S): the two mirror samples do not interleave.
    separated = (max_nondefault + max_default) < 1.0 if defaults and nondefaults else True
    # (S-half): every calibration score is below one half.
    separated_half = bool(scores.max() < 0.5)

    below_half = int(np.count_nonzero((labels == 0.0) & (scores < 0.5)))
    above_half = int(np.count_nonzero((labels == 1.0) & (scores > 0.5)))

    margin = defaults - boundary
    regime = None if threshold_is_capped else (LOW_REGIME if threshold < 0.5 else HIGH_REGIME)
    return {
        "learner": learner,
        "window_id": window_id,
        "taxonomy_groups": int(taxonomy_groups),
        "conformal_group": int(conformal_group),
        "score_stratum": int(conformal_group) + 1,
        "fit_rows": count,
        "fit_defaults": defaults,
        "fit_nondefaults": nondefaults,
        "fit_prevalence": float(defaults / count),
        "finite_sample_rank": rank,
        "boundary_count": boundary,
        "boundary_closed_form": int(math.floor(alpha * (count + 1))) - 1,
        "phase_margin": margin,
        "recomputed_threshold": threshold,
        "threshold_is_capped": threshold_is_capped,
        "threshold_below_half": bool(threshold < 0.5),
        "regime": regime,
        "margin_predicts_low": bool(margin <= 0),
        "fit_score_min": float(scores.min()),
        "fit_score_max": float(scores.max()),
        "fit_score_max_nondefault": max_nondefault,
        "fit_score_max_default": max_default,
        "separation_no_interleave": bool(separated),
        "separation_below_half": separated_half,
        "count_nondefault_below_half": below_half,
        "count_default_above_half": above_half,
        "exact_half_criterion": bool((below_half + above_half) >= rank),
    }


def build_stratum_phase_table(
    fit_audit: pd.DataFrame,
    *,
    learners: Sequence[str],
    window_ids: Sequence[str],
    taxonomy_groups: int,
    alpha: float = 0.10,
) -> pd.DataFrame:
    """Return the exact phase table for every declared learner-window stratum.

    Every declared cell must be present; a missing or duplicated stratum is an
    error rather than a silently dropped row.
    """
    missing = set(REQUIRED_FIT_COLUMNS).difference(fit_audit.columns)
    if missing:
        raise ValueError(f"Residual fit audit omits columns: {sorted(missing)}")

    taxonomy_count = _positive_integer(taxonomy_groups, label="taxonomy_groups")
    declared_learners = _declared_string_domain(learners, label="learner")
    declared_windows = _declared_string_domain(window_ids, label="window")
    taxonomy_values = _integral_array(
        fit_audit["taxonomy_groups"],
        label="Residual-fit taxonomy_groups",
        minimum=1,
    )
    frame = fit_audit.loc[taxonomy_values == taxonomy_count].copy()
    if frame.empty:
        raise RuntimeError("The declared taxonomy, learner, and window selection is empty.")
    _require_exact_domain(
        frame,
        column="learner",
        expected=declared_learners,
        label="residual-fit learner",
    )
    _require_exact_domain(
        frame,
        column="window_id",
        expected=declared_windows,
        label="residual-fit window",
    )
    frame["learner"] = frame["learner"].astype(str)
    frame["window_id"] = frame["window_id"].astype(str)
    frame["conformal_group"] = _integral_array(
        frame["conformal_group"],
        label="Residual-fit conformal_group keys",
        minimum=0,
        maximum=taxonomy_count - 1,
    )

    records: list[dict[str, object]] = []
    for (learner, window_id, group), block in frame.groupby(
        ["learner", "window_id", "conformal_group"], sort=True
    ):
        records.append(
            _stratum_record(
                learner=str(learner),
                window_id=str(window_id),
                taxonomy_groups=taxonomy_count,
                conformal_group=int(group),
                scores=block["pd_point"].to_numpy(dtype=float),
                labels=block["terminal_default"].to_numpy(dtype=float),
                alpha=float(alpha),
            )
        )

    table = pd.DataFrame.from_records(records)
    expected_keys = {
        (str(learner), str(window_id), group)
        for learner in declared_learners
        for window_id in declared_windows
        for group in range(taxonomy_count)
    }
    actual_keys = {
        (str(row.learner), str(row.window_id), row.conformal_group)
        for row in table.itertuples(index=False)
    }
    expected_rows = len(expected_keys)
    if len(table) != expected_rows:
        raise RuntimeError(
            f"Phase table census changed: {len(table)} rows against {expected_rows} declared."
        )
    if actual_keys != expected_keys:
        missing_keys = sorted(expected_keys.difference(actual_keys))
        unexpected_keys = sorted(actual_keys.difference(expected_keys))
        raise RuntimeError(
            "The phase table left the exact declared stratum grid: "
            f"missing={missing_keys}, unexpected={unexpected_keys}."
        )
    if table.duplicated(["learner", "window_id", "conformal_group"]).any():
        raise RuntimeError("The phase table contains a duplicated stratum key.")
    return table.sort_values(["learner", "window_id", "conformal_group"]).reset_index(drop=True)


def reconcile_phase_table(
    phase_table: pd.DataFrame,
    frozen_strata: pd.DataFrame,
    *,
    atol: float = 1.0e-12,
) -> pd.DataFrame:
    """Reconcile the recomputed threshold against the frozen recipe quantile."""
    if not math.isfinite(atol) or atol < 0.0:
        raise ValueError("The reconciliation tolerance must be finite and nonnegative.")
    required = {
        "learner",
        "window_id",
        "score_stratum",
        "fit_rows",
        "finite_sample_rank",
        "recomputed_threshold",
    }
    if not required.issubset(phase_table.columns):
        raise ValueError("The phase table is missing reconciliation keys.")
    frozen_required = {
        "learner",
        "window_id",
        "score_stratum",
        "fit_rows",
        "finite_sample_rank",
        "fit_residual_quantile",
    }
    missing = frozen_required.difference(frozen_strata.columns)
    if missing:
        raise ValueError(f"The frozen stratum table omits columns: {sorted(missing)}")

    phase = phase_table.copy()
    phase["score_stratum"] = _integral_array(
        phase["score_stratum"],
        label="Recomputed score_stratum keys",
        minimum=1,
    )
    if phase.duplicated(["learner", "window_id", "score_stratum"]).any():
        raise RuntimeError("The phase table contains a duplicated reconciliation key.")

    frozen = frozen_strata[sorted(frozen_required)].copy()
    frozen["score_stratum"] = _integral_array(
        frozen["score_stratum"],
        label="Frozen score_stratum keys",
        minimum=1,
    )
    frozen["fit_rows"] = _integral_array(
        frozen["fit_rows"],
        label="Frozen fit-row counts",
        minimum=1,
    )
    frozen["finite_sample_rank"] = _integral_array(
        frozen["finite_sample_rank"],
        label="Frozen finite-sample ranks",
        minimum=1,
    )
    frozen = frozen.rename(
        columns={
            "fit_rows": "frozen_fit_rows",
            "finite_sample_rank": "frozen_rank",
            "fit_residual_quantile": "frozen_threshold",
        }
    )
    reconciliation_keys = ["learner", "window_id", "score_stratum"]
    if frozen.duplicated(reconciliation_keys).any():
        raise RuntimeError("The frozen stratum table contains a duplicated reconciliation key.")
    if len(frozen) != len(phase):
        raise RuntimeError(
            "The frozen and recomputed phase-table censuses differ: "
            f"{len(frozen)} against {len(phase)}."
        )
    merged = phase.merge(
        frozen,
        on=reconciliation_keys,
        how="inner",
        validate="one_to_one",
    )
    if len(merged) != len(phase):
        raise RuntimeError(
            f"Reconciliation lost rows: {len(merged)} against {len(phase)} recomputed."
        )
    merged["threshold_gap"] = (merged["recomputed_threshold"] - merged["frozen_threshold"]).abs()
    merged["threshold_reconciles"] = merged["threshold_gap"] <= atol
    merged["rows_reconcile"] = merged["fit_rows"].eq(merged["frozen_fit_rows"])
    merged["rank_reconciles"] = merged["finite_sample_rank"].eq(merged["frozen_rank"])
    return merged


def phase_geometry_evidence(
    *,
    fit_audit_path: Path,
    frozen_strata: pd.DataFrame,
    expected_learners: Sequence[str],
    expected_window_ids: Sequence[str],
    alpha: float = 0.10,
    taxonomy_groups: int = 5,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Build the fail-closed paper evidence for exact binary phase geometry.

    The threshold is recomputed as the order statistic of the two mirror
    calibration samples and reconciled against every frozen recipe quantile.
    Learner and window domains must be declared independently of the supplied
    tables, so deleting a complete identity cannot shrink the audit silently.
    The crossing step is derived from the complete primary-CatBoost path and
    is accepted only when exactly one high-to-low transition remains.

    This is a reusable implementation of the evidence-builder contract. It does
    not read evaluation outcomes beyond the already frozen aggregate stratum
    table and does not write or promote any artifact.
    """
    required_frozen = {
        "learner",
        "window_id",
        "score_stratum",
        "fit_rows",
        "finite_sample_rank",
        "fit_residual_quantile",
        "coverage_resolved",
    }
    missing = required_frozen.difference(frozen_strata.columns)
    if missing:
        raise ValueError(f"The frozen stratum table omits columns: {sorted(missing)}")
    if frozen_strata.empty:
        raise RuntimeError("The frozen stratum table is empty.")
    taxonomy_count = _positive_integer(taxonomy_groups, label="taxonomy_groups")
    declared_learners = _declared_string_domain(expected_learners, label="learner")
    declared_windows = _declared_string_domain(expected_window_ids, label="window")
    frozen = frozen_strata.copy()
    frozen["score_stratum"] = _integral_array(
        frozen["score_stratum"],
        label="Frozen score_stratum keys",
        minimum=1,
        maximum=taxonomy_count,
    )
    frozen["fit_rows"] = _integral_array(
        frozen["fit_rows"],
        label="Frozen fit-row counts",
        minimum=1,
    )
    frozen["finite_sample_rank"] = _integral_array(
        frozen["finite_sample_rank"],
        label="Frozen finite-sample ranks",
        minimum=1,
    )
    _require_exact_domain(
        frozen,
        column="learner",
        expected=declared_learners,
        label="frozen learner",
    )
    _require_exact_domain(
        frozen,
        column="window_id",
        expected=declared_windows,
        label="frozen window",
    )
    frozen["learner"] = frozen["learner"].astype(str)
    frozen["window_id"] = frozen["window_id"].astype(str)
    keys = ["learner", "window_id", "score_stratum"]
    if frozen.duplicated(keys).any():
        raise RuntimeError("The frozen stratum table contains a duplicated stratum key.")

    numeric_columns = (
        "score_stratum",
        "fit_rows",
        "finite_sample_rank",
        "fit_residual_quantile",
        "coverage_resolved",
    )
    for column in numeric_columns:
        if not pd.api.types.is_numeric_dtype(frozen[column]):
            raise ValueError(f"Frozen stratum column {column!r} must be numeric.")
    if not bool(np.isfinite(frozen.loc[:, list(numeric_columns)].to_numpy(dtype=float)).all()):
        raise RuntimeError("The frozen stratum table contains a nonfinite scientific value.")
    if not bool(frozen["coverage_resolved"].between(0.0, 1.0).all()):
        raise RuntimeError("A frozen resolved-coverage value lies outside [0, 1].")

    table = build_stratum_phase_table(
        pd.read_parquet(fit_audit_path),
        learners=declared_learners,
        window_ids=declared_windows,
        taxonomy_groups=taxonomy_count,
        alpha=alpha,
    )
    reconciled = reconcile_phase_table(table, frozen)
    if not bool(reconciled["threshold_reconciles"].all()):
        raise RuntimeError("A recomputed phase threshold left the frozen recipe quantile.")
    if not bool(reconciled["rows_reconcile"].all() and reconciled["rank_reconciles"].all()):
        raise RuntimeError("Recomputed calibration counts or ranks left the frozen stratum table.")
    if not bool(table["boundary_count"].eq(table["boundary_closed_form"]).all()):
        raise RuntimeError("The closed-form phase boundary left the realized rank convention.")
    if not bool((table["exact_half_criterion"] == table["threshold_below_half"]).all()):
        raise RuntimeError("The exact half criterion left the realized threshold regime.")
    if bool(table["threshold_is_capped"].any()):
        raise RuntimeError(
            "A stratum reached the degenerate rank>n case, where the implementation "
            "caps the threshold at one; the regime label would be meaningless."
        )

    # The boundary identity below is algebraic. The data-bearing check is that the
    # realized rank convention leaves exactly n-k residuals strictly above the
    # threshold, which the frozen stratum table records independently.
    if "fit_residual_above_threshold" in frozen.columns:
        if not pd.api.types.is_numeric_dtype(frozen["fit_residual_above_threshold"]):
            raise ValueError("Frozen residual-above-threshold counts must be numeric.")
        above_source = frozen[
            ["learner", "window_id", "score_stratum", "fit_residual_above_threshold"]
        ].copy()
        above_source["fit_residual_above_threshold"] = _integral_array(
            above_source["fit_residual_above_threshold"],
            label="Frozen residual-above-threshold counts",
            minimum=0,
        )
        above = reconciled.merge(
            above_source,
            on=keys,
            how="inner",
            validate="one_to_one",
        )
        if len(above) != len(reconciled):
            raise RuntimeError("Residual-above-threshold reconciliation lost strata.")
        if not bool(above["fit_residual_above_threshold"].eq(above["boundary_count"]).all()):
            raise RuntimeError(
                "The realized residual count above the threshold left the rank convention."
            )

    separated = table["separation_below_half"]
    if not bool(
        (
            table.loc[separated, "margin_predicts_low"]
            == table.loc[separated, "threshold_below_half"]
        ).all()
    ):
        raise RuntimeError("The phase margin left the regime where its condition holds.")

    prevalence_by_stratum = table.groupby("score_stratum")["fit_prevalence"].agg(["min", "max"])
    low_by_stratum = (
        table.assign(low=table["threshold_below_half"].astype(int))
        .groupby("score_stratum")["low"]
        .sum()
    )

    crossing = frozen.loc[
        frozen["learner"].eq("catboost_platt") & frozen["score_stratum"].eq(3)
    ].copy()
    window_order = {window_id: index for index, window_id in enumerate(declared_windows)}
    crossing["_window_order"] = crossing["window_id"].map(window_order)
    crossing = crossing.sort_values("_window_order")
    if set(crossing["window_id"].astype(str)) != set(declared_windows):
        raise RuntimeError("The crossing stratum left the declared window identities.")
    coverage_path = crossing["coverage_resolved"].to_numpy(dtype=float)
    threshold_path = crossing["fit_residual_quantile"].to_numpy(dtype=float)
    if len(coverage_path) != len(declared_windows):
        raise RuntimeError("The crossing stratum census left the declared window set.")
    if not bool(np.isfinite(coverage_path).all() and np.isfinite(threshold_path).all()):
        raise RuntimeError("The crossing path contains a nonfinite value.")

    descends = (threshold_path[:-1] >= 0.5) & (threshold_path[1:] < 0.5)
    ascends = (threshold_path[:-1] < 0.5) & (threshold_path[1:] >= 0.5)
    transitions = int(descends.sum() + ascends.sum())
    if transitions != 1 or not bool(descends.any()):
        raise RuntimeError(
            "The crossing stratum no longer has exactly one high-to-low regime change: "
            f"{transitions} transitions detected."
        )
    crossing_step = int(np.argmax(descends)) + 1
    if crossing_step < 2:
        raise RuntimeError("The crossing has no adjacent earlier step to compare against.")

    publication_columns = [
        "learner",
        "window_id",
        "taxonomy_groups",
        "conformal_group",
        "score_stratum",
        "fit_rows",
        "fit_defaults",
        "fit_nondefaults",
        "fit_prevalence",
        "finite_sample_rank",
        "boundary_count",
        "boundary_closed_form",
        "phase_margin",
        "recomputed_threshold",
        "threshold_is_capped",
        "threshold_below_half",
        "regime",
        "margin_predicts_low",
        "separation_no_interleave",
        "separation_below_half",
        "count_nondefault_below_half",
        "count_default_above_half",
        "exact_half_criterion",
        "fit_score_min",
        "fit_score_max",
        "fit_score_max_nondefault",
        "fit_score_max_default",
    ]
    publication_table = table[publication_columns].sort_values(
        ["learner", "window_id", "score_stratum"]
    )
    crossing_change = coverage_path[crossing_step] - coverage_path[crossing_step - 1]
    first_differences = np.diff(coverage_path)
    evidence = {
        "strata": int(len(table)),
        "threshold_reconciles_all_strata": bool(reconciled["threshold_reconciles"].all()),
        "strata_with_a_capped_threshold": int(table["threshold_is_capped"].sum()),
        "separation_no_interleave_strata": int(table["separation_no_interleave"].sum()),
        "maximum_threshold_gap": float(reconciled["threshold_gap"].max()),
        "boundary_closed_form": "n_minus_k_equals_floor_alpha_times_n_plus_one_minus_one",
        "separation_below_half_strata": int(separated.sum()),
        "low_regime_strata": int(table["threshold_below_half"].sum()),
        "low_regime_cells_by_score_stratum": {
            str(int(index)): int(value) for index, value in low_by_stratum.items()
        },
        "within_stratum_fit_prevalence_range": {
            str(int(index)): [float(row["min"]), float(row["max"])]
            for index, row in prevalence_by_stratum.iterrows()
        },
        "crossing_threshold_change": float(
            threshold_path[crossing_step] - threshold_path[crossing_step - 1]
        ),
        "crossing_coverage_change": float(crossing_change),
        "adjacent_noncrossing_coverage_change": float(
            coverage_path[crossing_step - 1] - coverage_path[crossing_step - 2]
        ),
        "coverage_first_differences": [float(value) for value in first_differences.tolist()],
        "crossing_step_absolute_rank_among_first_differences": int(
            1 + sum(abs(step) > abs(crossing_change) for step in first_differences)
        ),
        "crossing_coverage_change_is_smaller_than_adjacent": bool(
            abs(crossing_change)
            < abs(coverage_path[crossing_step - 1] - coverage_path[crossing_step - 2])
        ),
        "crossing_coverage_change_is_not_the_largest_on_the_path": bool(
            abs(crossing_change) < max(abs(step) for step in first_differences)
        ),
        "claim_boundary": (
            "The threshold is exactly the k-th order statistic of the two mirror "
            "calibration samples. The regime criterion requires the stated "
            "below-half calibration condition, and target-side statements require "
            "their own support condition. The crossing probability is "
            "Poisson-Binomial, not Binomial. The primary CatBoost specification "
            "was frozen before the evaluation-outcome join, but the W7--W8 geometry "
            "was inspected retrospectively; the crossing was not predeclared, "
            "preregistered, or confirmatory. The phase table covers every learner "
            "window, and stratum in the declared grid without selection. Nothing "
            "here establishes selected-set or funded-set validity."
        ),
    }
    return evidence, publication_table.reset_index(drop=True)


def coverage_decomposition_evidence(
    conformal_set_table: pd.DataFrame,
    *,
    prevalence_lower: float,
    prevalence_upper: float,
    alpha: float = 0.10,
) -> dict[str, Any]:
    """Return the resolved-panel binary coverage mixture and breakeven summary.

    The decomposition is deliberately resolved-panel only. Every denominator,
    coverage value, mixture identity, and common-panel prevalence is validated
    before a scalar summary is emitted.
    """
    required = {
        "coverage_resolved",
        "coverage_resolved_y0",
        "coverage_resolved_y1",
        "resolved_y0_rows",
        "resolved_y1_rows",
    }
    missing = required.difference(conformal_set_table.columns)
    if missing:
        raise ValueError(f"Conformal-set diagnostics omit columns: {sorted(missing)}")
    if conformal_set_table.empty:
        raise RuntimeError("The conformal-set diagnostic table is empty.")
    if not math.isfinite(alpha) or not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie strictly inside the unit interval.")
    if not (
        math.isfinite(prevalence_lower)
        and math.isfinite(prevalence_upper)
        and 0.0 <= prevalence_lower <= prevalence_upper <= 1.0
    ):
        raise ValueError("Prevalence bounds must be finite and ordered inside [0, 1].")

    table = conformal_set_table
    for column in required:
        if not pd.api.types.is_numeric_dtype(table[column]):
            raise ValueError(f"Conformal-set diagnostic column {column!r} must be numeric.")
    values = table.loc[:, sorted(required)].to_numpy(dtype=float)
    if not bool(np.isfinite(values).all()):
        raise RuntimeError("A conformal-set diagnostic cell contains a nonfinite value.")

    count_columns = ["resolved_y0_rows", "resolved_y1_rows"]
    counts = table.loc[:, count_columns].to_numpy(dtype=float)
    if bool(np.any(counts <= 0.0)) or not bool(np.equal(counts, np.floor(counts)).all()):
        raise RuntimeError(
            "Each class-conditional coverage denominator must be a positive integer."
        )
    coverage_columns = [
        "coverage_resolved",
        "coverage_resolved_y0",
        "coverage_resolved_y1",
    ]
    if not all(table[column].between(0.0, 1.0).all() for column in coverage_columns):
        raise RuntimeError("A resolved coverage value lies outside [0, 1].")

    resolved = table["resolved_y0_rows"] + table["resolved_y1_rows"]
    prevalence = table["resolved_y1_rows"] / resolved
    reconstructed = (1.0 - prevalence) * table["coverage_resolved_y0"] + (
        prevalence * table["coverage_resolved_y1"]
    )
    residual = (reconstructed - table["coverage_resolved"]).abs()
    if not bool((residual <= 1.0e-12).all()):
        raise RuntimeError("The binary coverage mixture identity did not reconcile.")

    if int(prevalence.nunique()) != 1:
        raise RuntimeError(
            "Resolved prevalence varies across cells, so a single scalar cannot "
            "represent the target panel."
        )
    spread = table["coverage_resolved_y0"] - table["coverage_resolved_y1"]
    if not bool((spread > 0.0).all()):
        raise RuntimeError(
            "A class-coverage spread is nonpositive, so the breakeven denominator is invalid."
        )
    breakeven = (table["coverage_resolved_y0"] - (1.0 - alpha)) / spread
    if not bool(np.isfinite(breakeven.to_numpy(dtype=float)).all()):
        raise RuntimeError("A breakeven prevalence is nonfinite.")
    if not bool(breakeven.between(0.0, 1.0).all()):
        raise RuntimeError("A breakeven prevalence lies outside [0, 1] and is not attainable.")
    relative_reduction = (prevalence - breakeven) / prevalence
    if not bool(np.isfinite(relative_reduction.to_numpy(dtype=float)).all()):
        raise RuntimeError("A relative prevalence reduction is nonfinite.")

    return {
        "cells": int(len(table)),
        "mixture_identity_max_abs_residual": float(residual.max()),
        "resolved_prevalence": float(prevalence.iloc[0]),
        "breakeven_prevalence_range": [float(breakeven.min()), float(breakeven.max())],
        "all_candidate_prevalence_bound": [float(prevalence_lower), float(prevalence_upper)],
        "resolved_prevalence_exceeds_breakeven_in_every_cell": bool((prevalence > breakeven).all()),
        "relative_prevalence_reduction_to_nominal_range": [
            float(relative_reduction.min()),
            float(relative_reduction.max()),
        ],
        "claim_boundary": (
            "The mixture identity and the breakeven are computed on the resolved "
            "panel only. A completion moves unresolved rows into the prevalence "
            "and into both class-conditional coverages at once, so the breakeven "
            "is not invariant to it and this decomposition does not by itself "
            "extend to unresolved outcomes; the sharp coverage bounds carry that "
            "statement. The decomposition is descriptive attribution over realized "
            "class coverages. It identifies no shift mechanism, no cause of the "
            "prevalence level, and no label-conditional validity, and it selects "
            "no learner or window."
        ),
    }


def coverage_change_between_thresholds(
    *,
    target_scores: np.ndarray,
    target_labels: np.ndarray,
    lower_threshold: float,
    upper_threshold: float,
) -> dict[str, float]:
    """Return the exact resolved-panel coverage change for two thresholds.

    For ``0 <= c_lo <= c_hi <= 1``, binary-set coverage satisfies

        Cov(c_hi) - Cov(c_lo)
          = (1-pi) P(c_lo < p <= c_hi | Y=0)
          + pi P(1-c_hi <= p < 1-c_lo | Y=1).

    This identity compares two *fixed* thresholds on one target distribution.
    It does not couple two different calibration blocks or assume that the same
    block can simultaneously occupy both sides of a label-count transition.
    All quantities condition on resolved target labels and therefore inherit
    the corresponding completion boundary.
    """
    scores = np.asarray(target_scores, dtype=float)
    labels = np.asarray(target_labels, dtype=float)
    if scores.shape != labels.shape or scores.ndim != 1:
        raise ValueError("Target scores and labels must be aligned one-dimensional arrays.")
    if not set(np.unique(labels)).issubset({0.0, 1.0}):
        raise ValueError("Target labels must be binary.")
    resolved = scores.size
    if resolved == 0:
        raise ValueError("The coverage identity requires at least one resolved target row.")
    c_lo = float(lower_threshold)
    c_hi = float(upper_threshold)
    if not np.isfinite(c_lo) or not np.isfinite(c_hi):
        raise ValueError("Both thresholds must be finite.")
    if not 0.0 <= c_lo <= c_hi <= 1.0:
        raise ValueError("Thresholds must satisfy 0 <= lower <= upper <= 1.")
    if not bool(np.isfinite(scores).all()) or bool(np.any(scores < 0.0) or np.any(scores > 1.0)):
        raise ValueError("Target scores must be finite and lie in [0, 1].")

    is_default = labels == 1.0
    prevalence = float(is_default.mean())
    nondefault_crossing_mass = (
        float(np.mean((scores[~is_default] > c_lo) & (scores[~is_default] <= c_hi)))
        if int((~is_default).sum())
        else 0.0
    )
    default_crossing_mass = (
        float(np.mean((scores[is_default] >= 1.0 - c_hi) & (scores[is_default] < 1.0 - c_lo)))
        if int(is_default.sum())
        else 0.0
    )
    coverage_change = float(
        (1.0 - prevalence) * nondefault_crossing_mass + prevalence * default_crossing_mass
    )
    return {
        "target_rows": float(resolved),
        "target_prevalence": prevalence,
        "lower_threshold": c_lo,
        "upper_threshold": c_hi,
        "threshold_change": float(c_hi - c_lo),
        "nondefault_crossing_mass": nondefault_crossing_mass,
        "default_crossing_mass": default_crossing_mass,
        "coverage_change": coverage_change,
    }


def sharp_coverage_change_bounds(
    *,
    target_scores: np.ndarray,
    target_labels: np.ndarray,
    lower_threshold: float,
    upper_threshold: float,
    weights: np.ndarray | None = None,
) -> dict[str, float]:
    """Return sharp two-threshold coverage-change bounds with unresolved labels.

    Missing labels must be encoded as ``NaN``. For each unresolved unit, the
    contribution difference is evaluated at both attainable binary labels and
    its minimum or maximum is added once. Optional nonnegative weights define
    the declared normalization; without them each target row has unit weight.
    """
    scores = np.asarray(target_scores, dtype=float)
    labels = np.asarray(target_labels, dtype=float)
    if scores.shape != labels.shape or scores.ndim != 1:
        raise ValueError("Target scores and labels must be aligned one-dimensional arrays.")
    if scores.size == 0:
        raise ValueError("Coverage-change bounds require at least one target row.")
    if not bool(np.isfinite(scores).all()) or bool(np.any(scores < 0.0) or np.any(scores > 1.0)):
        raise ValueError("Target scores must be finite and lie in [0, 1].")
    observed = labels[~np.isnan(labels)]
    if not set(np.unique(observed)).issubset({0.0, 1.0}):
        raise ValueError("Observed target labels must be binary; unresolved labels must be NaN.")

    c_lo = float(lower_threshold)
    c_hi = float(upper_threshold)
    if not np.isfinite(c_lo) or not np.isfinite(c_hi):
        raise ValueError("Both thresholds must be finite.")
    if not 0.0 <= c_lo <= c_hi <= 1.0:
        raise ValueError("Thresholds must satisfy 0 <= lower <= upper <= 1.")

    if weights is None:
        weight = np.ones(scores.size, dtype=float)
    else:
        weight = np.asarray(weights, dtype=float)
        if weight.shape != scores.shape:
            raise ValueError("Weights must align with target scores.")
    if not bool(np.isfinite(weight).all()) or bool(np.any(weight < 0.0)):
        raise ValueError("Weights must be finite and nonnegative.")
    normalizer = float(weight.sum())
    if normalizer <= 0.0:
        raise ValueError("The coverage-change normalizer must be positive.")

    delta_y0 = ((scores <= c_hi) & (scores > c_lo)).astype(float)
    delta_y1 = ((scores >= 1.0 - c_hi) & (scores < 1.0 - c_lo)).astype(float)
    unresolved = np.isnan(labels)
    resolved_delta = np.where(labels == 1.0, delta_y1, delta_y0)
    resolved_contribution = float((weight[~unresolved] * resolved_delta[~unresolved]).sum())
    unresolved_lower = float(
        (weight[unresolved] * np.minimum(delta_y0[unresolved], delta_y1[unresolved])).sum()
    )
    unresolved_upper = float(
        (weight[unresolved] * np.maximum(delta_y0[unresolved], delta_y1[unresolved])).sum()
    )
    return {
        "target_rows": float(scores.size),
        "resolved_rows": float((~unresolved).sum()),
        "unresolved_rows": float(unresolved.sum()),
        "normalizer": normalizer,
        "coverage_change_lower": float((resolved_contribution + unresolved_lower) / normalizer),
        "coverage_change_upper": float((resolved_contribution + unresolved_upper) / normalizer),
    }


def outcome_free_binary_set_bounds(
    allocations: pd.DataFrame,
    *,
    exposure_column: str = "exposure",
    lower_column: str = "conformal_lower",
    upper_column: str = "conformal_upper",
    tolerance: float = 1.0e-12,
) -> pd.Series:
    """Return sharp outcome-free bounds induced by empty and full binary sets.

    A binary prediction set is empty exactly when ``lower > 0`` and
    ``upper < 1``; such a unit is missed under either attainable outcome. It
    contains both labels exactly when ``lower = 0`` and ``upper = 1``; such a
    unit is covered under either outcome. Consequently, after normalizing by
    total funded exposure,

    ``empty_share <= miscoverage <= 1 - both_share``

    and equivalently

    ``both_share <= coverage <= 1 - empty_share``.

    These bounds are sharp over unrestricted loan-wise binary outcomes. A
    positive lower endpoint *alone* is not an outcome-free miss: if the upper
    endpoint is one, outcome ``Y=1`` remains covered. ``tolerance`` is used
    only to admit and clip small numerical excursions outside ``[0, 1]``. It
    never snaps an endpoint already inside the unit interval to zero or one.
    """
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("The endpoint tolerance must be finite and nonnegative.")
    for column in (exposure_column, lower_column, upper_column):
        if column not in allocations.columns:
            raise ValueError(f"Allocations omit the required column {column!r}.")
    exposure = allocations[exposure_column].to_numpy(dtype=float)
    lower = allocations[lower_column].to_numpy(dtype=float)
    upper = allocations[upper_column].to_numpy(dtype=float)
    if not bool(
        np.isfinite(exposure).all() and np.isfinite(lower).all() and np.isfinite(upper).all()
    ):
        raise ValueError("Exposure and conformal endpoints must be finite.")
    if bool(np.any(exposure < 0.0)):
        raise ValueError("Exposure must be nonnegative.")
    if bool(
        np.any(lower < -tolerance)
        or np.any(lower > 1.0 + tolerance)
        or np.any(upper < -tolerance)
        or np.any(upper > 1.0 + tolerance)
    ):
        raise ValueError("Conformal endpoints must lie inside [0, 1].")
    normalized_lower = np.clip(lower, 0.0, 1.0)
    normalized_upper = np.clip(upper, 0.0, 1.0)
    if bool(np.any(normalized_lower > normalized_upper)):
        raise ValueError("A conformal lower endpoint exceeds its upper endpoint.")
    total = float(exposure.sum())
    if total <= 0.0:
        raise ValueError("Total funded exposure must be positive.")
    empty = (normalized_lower > 0.0) & (normalized_upper < 1.0)
    both = (normalized_lower <= 0.0) & (normalized_upper >= 1.0)
    empty_exposure = float(exposure[empty].sum())
    both_exposure = float(exposure[both].sum())
    empty_share = float(empty_exposure / total)
    both_share = float(both_exposure / total)
    return pd.Series(
        {
            "funded_exposure": total,
            "empty_set_exposure": empty_exposure,
            "both_set_exposure": both_exposure,
            "outcome_free_miscoverage_lower": empty_share,
            "outcome_free_miscoverage_upper": float(1.0 - both_share),
            "outcome_free_coverage_lower": both_share,
            "outcome_free_coverage_upper": float(1.0 - empty_share),
        }
    )


def positive_coverable_exposure_share_of_total(
    allocations: pd.DataFrame,
    *,
    exposure_column: str = "exposure",
    upper_column: str = "conformal_upper",
    tolerance: float = 1.0e-9,
) -> pd.Series:
    """Return the total-capital share on units capable of covering ``Y=1``.

    A funded positive case is covered if and only if its clipped upper endpoint
    saturates at one. The returned share therefore bounds the *covered-positive
    contribution normalized by total funded capital*. It does not bound
    positive-class conditional coverage, whose denominator is the unknown
    funded-positive exposure. ``tolerance`` is used only to admit and clip a
    small numerical excursion outside ``[0, 1]``; an endpoint already below
    one is never promoted to one.
    """
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("The endpoint tolerance must be finite and nonnegative.")
    for column in (exposure_column, upper_column):
        if column not in allocations.columns:
            raise ValueError(f"Allocations omit the required column {column!r}.")
    exposure = allocations[exposure_column].to_numpy(dtype=float)
    upper = allocations[upper_column].to_numpy(dtype=float)
    if not bool(np.isfinite(exposure).all() and np.isfinite(upper).all()):
        raise ValueError("Exposure and conformal upper endpoints must be finite.")
    if bool(np.any(exposure < 0.0)):
        raise ValueError("Exposure must be nonnegative.")
    if bool(np.any(upper < -tolerance) or np.any(upper > 1.0 + tolerance)):
        raise ValueError("Conformal upper endpoints must lie inside [0, 1].")
    normalized_upper = np.clip(upper, 0.0, 1.0)
    total = float(exposure.sum())
    if total <= 0.0:
        raise ValueError("Total funded exposure must be positive.")
    saturated = exposure[normalized_upper == 1.0].sum()
    return pd.Series(
        {
            "funded_exposure": total,
            "positive_coverable_exposure": float(saturated),
            "positive_coverable_exposure_share_of_total": float(saturated / total),
        }
    )
