"""Outcome-free primitives for comparator-stringency audits."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, Decimal
from typing import Literal

import numpy as np
import pandas as pd

OUTCOME_DERIVED_COLUMNS = frozenset(
    {
        "default_flag",
        "loan_status",
        "outcome",
        "realized_return",
        "realized_risk_tolerance_excess",
        "snapshot_default",
        "weighted_miscoverage",
        "weighted_outcome",
        "y_true",
    }
)

EnvelopeSign = Literal["strictly_negative", "strictly_positive", "indeterminate"]


@dataclass(frozen=True)
class MatchDiagnostics:
    """Numerical reconciliation of an achieved point-risk moment to a target."""

    target: float
    achieved: float
    difference: float
    absolute_difference: float
    tolerance: float
    matched: bool


@dataclass(frozen=True)
class AffineCapDiagnostics:
    """Empirical diagnostics for a score-to-point affine cap mapping."""

    is_affine: bool
    slope: float
    intercept: float
    max_absolute_residual: float
    score_cap: float
    point_cap: float | None
    feasible_sets_equal: bool
    mismatch_count: int
    tolerance: float


@dataclass(frozen=True)
class ComparatorEnvelope:
    """Finite envelope across existing sharp contrast intervals."""

    lower: float
    upper: float
    sign: EnvelopeSign
    record_count: int
    lower_record_index: object
    upper_record_index: object


@dataclass(frozen=True)
class DevelopmentSupportedCapRange:
    """Point-cap range derived only from outcome-free development targets."""

    lower: float
    upper: float
    step: float
    target_minimum: float
    target_maximum: float
    target_count: int


def _one_dimensional_finite(values: object, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional.")
    if array.size == 0:
        raise ValueError(f"{name} must not be empty.")
    if not bool(np.all(np.isfinite(array))):
        raise ValueError(f"{name} must contain only finite values.")
    return array


def _validate_tolerance(tolerance: float) -> float:
    value = float(tolerance)
    if not np.isfinite(value) or value < 0.0:
        raise ValueError("tolerance must be finite and non-negative.")
    return value


def assert_outcome_free_frame(frame: pd.DataFrame) -> None:
    """Reject columns that reveal or are derived from post-decision outcomes."""
    normalized = {str(column).strip().casefold() for column in frame.columns}
    forbidden = sorted(OUTCOME_DERIVED_COLUMNS.intersection(normalized))
    if forbidden:
        raise ValueError(f"Comparator target received outcome-derived columns: {forbidden}")


def weighted_funded_point_risk(
    allocations: object,
    point_risks: object,
    *,
    funded_tolerance: float = 0.0,
) -> float:
    """Return the capital-weighted point-risk moment among funded rows."""
    weights = _one_dimensional_finite(allocations, name="allocations")
    risks = _one_dimensional_finite(point_risks, name="point_risks")
    if weights.shape != risks.shape:
        raise ValueError("allocations and point_risks must align.")
    threshold = _validate_tolerance(funded_tolerance)
    if bool(np.any(weights < 0.0)):
        raise ValueError("allocations must be non-negative.")
    if bool(np.any((risks < 0.0) | (risks > 1.0))):
        raise ValueError("point_risks must lie in [0, 1].")
    funded = weights > threshold
    funded_capital = float(weights[funded].sum())
    if funded_capital <= 0.0:
        raise ValueError("At least one row must have positive funded capital.")
    return float(weights[funded] @ risks[funded] / funded_capital)


def contemporaneous_point_cap_target(
    frozen_guardrail_allocation: pd.DataFrame,
    *,
    allocation_column: str = "exposure",
    point_risk_column: str = "pd_point",
    funded_tolerance: float = 0.0,
) -> float:
    """Derive an outcome-free point cap from one frozen guardrail allocation."""
    assert_outcome_free_frame(frozen_guardrail_allocation)
    required = {allocation_column, point_risk_column}
    missing = sorted(required.difference(frozen_guardrail_allocation.columns))
    if missing:
        raise ValueError(f"Frozen allocation is missing required columns: {missing}")
    return weighted_funded_point_risk(
        pd.to_numeric(frozen_guardrail_allocation[allocation_column], errors="raise"),
        pd.to_numeric(frozen_guardrail_allocation[point_risk_column], errors="raise"),
        funded_tolerance=funded_tolerance,
    )


def exact_match_diagnostics(
    allocations: object,
    point_risks: object,
    *,
    target: float,
    tolerance: float = 1e-12,
    funded_tolerance: float = 0.0,
) -> MatchDiagnostics:
    """Compare a funded point-risk moment with a frozen target."""
    tolerance_value = _validate_tolerance(tolerance)
    target_value = float(target)
    if not np.isfinite(target_value) or not 0.0 <= target_value <= 1.0:
        raise ValueError("target must be finite and lie in [0, 1].")
    achieved = weighted_funded_point_risk(
        allocations,
        point_risks,
        funded_tolerance=funded_tolerance,
    )
    difference = achieved - target_value
    absolute_difference = abs(difference)
    return MatchDiagnostics(
        target=target_value,
        achieved=achieved,
        difference=difference,
        absolute_difference=absolute_difference,
        tolerance=tolerance_value,
        matched=absolute_difference <= tolerance_value,
    )


def translate_affine_score_cap(
    score_cap: float,
    *,
    slope: float,
    intercept: float,
) -> float:
    """Translate ``score <= cap`` to its point-score cap for a positive affine map."""
    values = np.asarray([score_cap, slope, intercept], dtype=float)
    if not bool(np.all(np.isfinite(values))):
        raise ValueError("score_cap, slope, and intercept must be finite.")
    if float(slope) <= 0.0:
        raise ValueError("slope must be positive to preserve cap inequality direction.")
    return (float(score_cap) - float(intercept)) / float(slope)


def affine_score_cap_diagnostics(
    point_scores: object,
    audit_scores: object,
    *,
    score_cap: float,
    tolerance: float = 1e-12,
) -> AffineCapDiagnostics:
    """Diagnose affine score geometry and the induced empirical feasible sets."""
    points = _one_dimensional_finite(point_scores, name="point_scores")
    scores = _one_dimensional_finite(audit_scores, name="audit_scores")
    if points.shape != scores.shape:
        raise ValueError("point_scores and audit_scores must align.")
    tolerance_value = _validate_tolerance(tolerance)
    cap = float(score_cap)
    if not np.isfinite(cap):
        raise ValueError("score_cap must be finite.")
    design = np.column_stack((points, np.ones_like(points)))
    coefficients, _, rank, _ = np.linalg.lstsq(design, scores, rcond=None)
    slope, intercept = (float(value) for value in coefficients)
    residual = scores - (slope * points + intercept)
    max_residual = float(np.max(np.abs(residual)))
    is_affine = bool(rank == 2 and slope > 0.0 and max_residual <= tolerance_value)
    point_cap = (
        translate_affine_score_cap(cap, slope=slope, intercept=intercept) if is_affine else None
    )
    if point_cap is None:
        mismatch_count = int(points.size)
        feasible_sets_equal = False
    else:
        score_feasible = scores <= cap + tolerance_value
        point_feasible = points <= point_cap + tolerance_value
        mismatch_count = int(np.count_nonzero(score_feasible != point_feasible))
        feasible_sets_equal = mismatch_count == 0
    return AffineCapDiagnostics(
        is_affine=is_affine,
        slope=slope,
        intercept=intercept,
        max_absolute_residual=max_residual,
        score_cap=cap,
        point_cap=point_cap,
        feasible_sets_equal=feasible_sets_equal,
        mismatch_count=mismatch_count,
        tolerance=tolerance_value,
    )


def require_affine_score_cap_equivalence(
    point_scores: object,
    audit_scores: object,
    *,
    score_cap: float,
    tolerance: float = 1e-12,
) -> AffineCapDiagnostics:
    """Return affine diagnostics or reject non-affine/non-equivalent score caps."""
    diagnostics = affine_score_cap_diagnostics(
        point_scores,
        audit_scores,
        score_cap=score_cap,
        tolerance=tolerance,
    )
    if not diagnostics.is_affine:
        raise ValueError(
            "Scores do not admit a positive affine mapping within tolerance; "
            f"max residual={diagnostics.max_absolute_residual:.6g}."
        )
    if not diagnostics.feasible_sets_equal:
        raise ValueError(
            "Affine cap translation did not reproduce the empirical feasible set; "
            f"mismatches={diagnostics.mismatch_count}."
        )
    return diagnostics


def comparator_multiverse_envelope(
    sharp_contrasts: pd.DataFrame,
    *,
    lower_column: str,
    upper_column: str,
    tolerance: float = 0.0,
) -> ComparatorEnvelope:
    """Envelope a finite set of precomputed sharp contrast intervals."""
    if sharp_contrasts.empty:
        raise ValueError("sharp_contrasts must not be empty.")
    missing = sorted({lower_column, upper_column}.difference(sharp_contrasts.columns))
    if missing:
        raise ValueError(f"Sharp contrasts are missing required columns: {missing}")
    tolerance_value = _validate_tolerance(tolerance)
    lower = pd.to_numeric(sharp_contrasts[lower_column], errors="raise")
    upper = pd.to_numeric(sharp_contrasts[upper_column], errors="raise")
    lower_values = lower.to_numpy(dtype=float)
    upper_values = upper.to_numpy(dtype=float)
    if not bool(np.all(np.isfinite(lower_values))) or not bool(np.all(np.isfinite(upper_values))):
        raise ValueError("Sharp contrast bounds must be finite.")
    if bool(np.any(lower_values > upper_values + tolerance_value)):
        raise ValueError("Each sharp contrast lower bound must not exceed its upper bound.")
    envelope_lower = float(lower_values.min())
    envelope_upper = float(upper_values.max())
    if envelope_lower > tolerance_value:
        sign: EnvelopeSign = "strictly_positive"
    elif envelope_upper < -tolerance_value:
        sign = "strictly_negative"
    else:
        sign = "indeterminate"
    return ComparatorEnvelope(
        lower=envelope_lower,
        upper=envelope_upper,
        sign=sign,
        record_count=int(len(sharp_contrasts)),
        lower_record_index=lower.idxmin(),
        upper_record_index=upper.idxmax(),
    )


def build_fixed_cap_grid(
    start: float,
    stop: float,
    step: float,
    *,
    tolerance: float = 1e-12,
) -> np.ndarray:
    """Build a deterministic inclusive grid after validating endpoint alignment."""
    values = np.asarray([start, stop, step], dtype=float)
    if not bool(np.all(np.isfinite(values))):
        raise ValueError("start, stop, and step must be finite.")
    tolerance_value = _validate_tolerance(tolerance)
    start_value, stop_value, step_value = (float(value) for value in values)
    if step_value <= 0.0:
        raise ValueError("step must be positive.")
    if stop_value < start_value:
        raise ValueError("stop must be greater than or equal to start.")
    start_decimal = Decimal(str(start_value))
    stop_decimal = Decimal(str(stop_value))
    step_decimal = Decimal(str(step_value))
    intervals = (stop_decimal - start_decimal) / step_decimal
    rounded_intervals = intervals.to_integral_value(rounding=ROUND_HALF_EVEN)
    endpoint_error = abs((intervals - rounded_intervals) * step_decimal)
    if endpoint_error > Decimal(str(tolerance_value)):
        raise ValueError("step must land on stop within tolerance.")
    interval_count = int(rounded_intervals)
    return np.asarray(
        [float(start_decimal + index * step_decimal) for index in range(interval_count + 1)],
        dtype=float,
    )


def development_supported_cap_range(
    targets: object,
    *,
    step: float,
    lower_limit: float,
    upper_limit: float,
) -> DevelopmentSupportedCapRange:
    """Round development-only funded-risk targets outward onto a fixed grid."""
    values = _one_dimensional_finite(targets, name="targets")
    if bool(np.any((values < 0.0) | (values > 1.0))):
        raise ValueError("targets must lie in [0, 1].")
    step_decimal = Decimal(str(float(step)))
    lower_decimal = Decimal(str(float(lower_limit)))
    upper_decimal = Decimal(str(float(upper_limit)))
    if step_decimal <= 0:
        raise ValueError("step must be positive.")
    if upper_decimal < lower_decimal:
        raise ValueError("upper_limit must be at least lower_limit.")
    minimum = Decimal(str(float(values.min())))
    maximum = Decimal(str(float(values.max())))
    rounded_lower = (minimum / step_decimal).to_integral_value(rounding=ROUND_FLOOR) * step_decimal
    rounded_upper = (maximum / step_decimal).to_integral_value(
        rounding=ROUND_CEILING
    ) * step_decimal
    clipped_lower = max(lower_decimal, rounded_lower)
    clipped_upper = min(upper_decimal, rounded_upper)
    if clipped_lower > clipped_upper:
        raise ValueError("Development targets do not overlap the declared broad frontier.")
    return DevelopmentSupportedCapRange(
        lower=float(clipped_lower),
        upper=float(clipped_upper),
        step=float(step_decimal),
        target_minimum=float(minimum),
        target_maximum=float(maximum),
        target_count=int(values.size),
    )
