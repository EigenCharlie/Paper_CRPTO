"""Binary prediction-set geometry for clipped residual intervals."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

EMPTY = 0
ZERO_ONLY = 1
ONE_ONLY = 2
BOTH = 3
SET_LABELS = {EMPTY: "empty", ZERO_ONLY: "{0}", ONE_ONLY: "{1}", BOTH: "{0,1}"}


@dataclass(frozen=True)
class ConstantScorePhase:
    """Population geometry under a constant score and Bernoulli prevalence."""

    residual_quantile: float
    discrete_set: str
    coverage: float


def binary_set_codes(
    lower: Sequence[float] | np.ndarray,
    upper: Sequence[float] | np.ndarray,
    *,
    tolerance: float = 1e-12,
) -> np.ndarray:
    """Encode each interval's intersection with the binary outcome space."""
    low = np.asarray(lower, dtype=float)
    high = np.asarray(upper, dtype=float)
    if low.shape != high.shape or low.ndim != 1:
        raise ValueError("Binary interval endpoints must be aligned one-dimensional arrays.")
    if not bool(np.isfinite(low).all() and np.isfinite(high).all()):
        raise ValueError("Binary interval endpoints must be finite.")
    if bool(np.any(low > high + tolerance)):
        raise ValueError("An interval has lower endpoint above its upper endpoint.")
    contains_zero = (low <= tolerance) & (high >= -tolerance)
    contains_one = (low <= 1.0 + tolerance) & (high >= 1.0 - tolerance)
    return contains_zero.astype(np.int8) + 2 * contains_one.astype(np.int8)


def summarize_binary_geometry(
    lower: Sequence[float] | np.ndarray,
    upper: Sequence[float] | np.ndarray,
    *,
    width_quantiles: Sequence[float] = (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0),
) -> dict[str, Any]:
    """Return continuous width and discrete-set diagnostics without outcomes."""
    low = np.asarray(lower, dtype=float)
    high = np.asarray(upper, dtype=float)
    if len(low) == 0:
        raise ValueError("Binary geometry requires at least one interval.")
    codes = binary_set_codes(low, high)
    width = high - low
    result: dict[str, Any] = {
        "rows": int(len(low)),
        "mean_width": float(np.mean(width)),
        "lower_positive_share": float(np.mean(low > 1e-12)),
        "upper_saturated_share": float(np.mean(high >= 1.0 - 1e-12)),
    }
    for code in SET_LABELS:
        key = {EMPTY: "empty", ZERO_ONLY: "zero_only", ONE_ONLY: "one_only", BOTH: "both"}[code]
        count = int(np.sum(codes == code))
        result[f"set_{key}_count"] = count
        result[f"set_{key}_share"] = float(count / len(codes)) if len(codes) else np.nan
    for quantile in width_quantiles:
        if not 0.0 <= float(quantile) <= 1.0:
            raise ValueError("Width quantiles must lie in [0, 1].")
        name = f"width_q{int(round(100 * float(quantile))):02d}"
        result[name] = float(np.quantile(width, float(quantile)))
    return result


def constant_score_population_phase(
    *, score: float, prevalence: float, alpha: float
) -> ConstantScorePhase:
    """Evaluate the exact population phase for p<1/2 and Bernoulli outcomes.

    At a constant score ``p``, residuals are ``p`` for Y=0 and ``1-p`` for
    Y=1. The lower population quantile is selected when prevalence is at most
    alpha; otherwise the upper residual is required.
    """
    p = float(score)
    pi = float(prevalence)
    a = float(alpha)
    if not 0.0 <= p < 0.5:
        raise ValueError("The stated proposition requires 0 <= score < 1/2.")
    if not 0.0 <= pi <= 1.0 or not 0.0 < a < 1.0:
        raise ValueError("Prevalence and alpha are outside their probability domains.")
    quantile = p if pi <= a else 1.0 - p
    lower = max(0.0, p - quantile)
    upper = min(1.0, p + quantile)
    code = int(binary_set_codes([lower], [upper])[0])
    coverage = (1.0 - pi) * float(lower <= 0.0 <= upper) + pi * float(lower <= 1.0 <= upper)
    return ConstantScorePhase(quantile, SET_LABELS[code], float(coverage))
