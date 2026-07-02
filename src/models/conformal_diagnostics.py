"""Conformal prediction diagnostics — first step of the conformal split.

The functions here used to live inside ``src/models/conformal.py``. They are
**pure data summaries** — no MAPIE calls, no classifier state, no pickled
references — so moving them does not affect ``pd_canonical_calibrator.pkl``
deserialization.

The legacy import path keeps working:

    >>> from src.models.conformal import validate_coverage  # still valid

because ``conformal.py`` re-exports both names. New call sites should prefer:

    >>> from src.models.conformal_diagnostics import validate_coverage

See ``docs/refactor/CONFORMAL_REFACTOR_PLAN.md`` for the full split plan.
"""

from __future__ import annotations

import numpy as np
from loguru import logger


def validate_coverage(
    y_true: np.ndarray,
    y_intervals: np.ndarray,
    alpha: float,
    log_summary: bool = True,
) -> dict[str, float]:
    """Validate empirical coverage of a conformal interval set against its target.

    Args:
        y_true: observed labels.
        y_intervals: ``(n, 2)`` array of ``[low, high]`` per observation.
        alpha: miscoverage rate. Target coverage is ``1 - alpha``.
        log_summary: emit a one-line diagnostic summary. Large grid searches
            set this to ``False`` to avoid logging becoming the bottleneck.

    Returns:
        Dict with empirical_coverage, target_coverage, coverage_gap,
        avg_interval_width and median_interval_width.
    """
    low = y_intervals[:, 0]
    high = y_intervals[:, 1]
    covered = ((y_true >= low) & (y_true <= high)).mean()
    target = 1 - alpha

    metrics = {
        "empirical_coverage": float(covered),
        "target_coverage": float(target),
        "coverage_gap": float(abs(covered - target)),
        "avg_interval_width": float((high - low).mean()),
        "median_interval_width": float(np.median(high - low)),
    }
    if log_summary:
        logger.info(f"Coverage validation: empirical={covered:.4f} vs target={target:.4f}")
    return metrics


def summarize_prediction_sets(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_sets: np.ndarray,
) -> dict[str, float]:
    """Summarize binary conformal prediction sets for abstention analysis.

    Reports singleton/ambiguous/empty rates, set coverage and conditional
    default rates by set type.
    """
    true_arr = np.asarray(y_true, dtype=int).reshape(-1)
    pred_arr = np.asarray(y_pred, dtype=int).reshape(-1)
    sets = np.asarray(y_sets, dtype=int)
    if sets.ndim != 2:
        raise ValueError(f"Expected y_sets to be 2D, got shape={sets.shape}")
    if len(true_arr) != len(sets):
        raise ValueError("y_true and y_sets must have the same length.")

    set_size = sets.sum(axis=1)
    singleton_mask = set_size == 1
    ambiguous_mask = set_size > 1
    empty_mask = set_size == 0
    covered_mask = sets[np.arange(len(true_arr)), true_arr] == 1
    positive_singleton_mask = singleton_mask & (pred_arr == 1)

    return {
        "n_obs": float(len(true_arr)),
        "set_coverage": float(covered_mask.mean()) if len(true_arr) else float("nan"),
        "singleton_rate": float(singleton_mask.mean()) if len(true_arr) else float("nan"),
        "ambiguity_rate": float(ambiguous_mask.mean()) if len(true_arr) else float("nan"),
        "empty_set_rate": float(empty_mask.mean()) if len(true_arr) else float("nan"),
        "default_rate_ambiguous": float(true_arr[ambiguous_mask].mean())
        if ambiguous_mask.any()
        else float("nan"),
        "default_rate_singleton_positive": float(true_arr[positive_singleton_mask].mean())
        if positive_singleton_mask.any()
        else float("nan"),
        "default_rate_overall": float(true_arr.mean()) if len(true_arr) else float("nan"),
    }
