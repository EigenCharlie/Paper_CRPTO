"""Secondary observed cumulative cash-yield metrics for snapshot evaluation.

These metrics use undiscounted cumulative payments observed at one data
snapshot. They are not IRR, NPV, or terminal profit measures.
"""

from __future__ import annotations

import numpy as np

CASH_YIELD_ID = "observed_undiscounted_snapshot_cash_yield_v1"


def observed_undiscounted_snapshot_cash_yield(
    funded_amnt: np.ndarray,
    total_pymnt: np.ndarray,
) -> np.ndarray:
    """Return per-loan net cash yield ``(total_pymnt - funded_amnt) / funded_amnt``."""
    principal, payments = _validated_cash_inputs(funded_amnt, total_pymnt)
    return (payments - principal) / principal


def exposure_weighted_undiscounted_snapshot_cash_yield(
    funded_amnt: np.ndarray,
    total_pymnt: np.ndarray,
) -> float:
    """Return funded-principal-weighted observed cumulative net cash yield."""
    principal, payments = _validated_cash_inputs(funded_amnt, total_pymnt)
    return float((payments.sum() - principal.sum()) / principal.sum())


def exposure_weighted_undiscounted_snapshot_cash_yield_difference(
    funded_amnt_a: np.ndarray,
    total_pymnt_a: np.ndarray,
    funded_amnt_b: np.ndarray,
    total_pymnt_b: np.ndarray,
) -> float:
    """Return portfolio A minus portfolio B undiscounted snapshot cash yield."""
    yield_a = exposure_weighted_undiscounted_snapshot_cash_yield(
        funded_amnt_a,
        total_pymnt_a,
    )
    yield_b = exposure_weighted_undiscounted_snapshot_cash_yield(
        funded_amnt_b,
        total_pymnt_b,
    )
    return yield_a - yield_b


def _validated_cash_inputs(
    funded_amnt: np.ndarray,
    total_pymnt: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    principal = np.asarray(funded_amnt, dtype=float)
    payments = np.asarray(total_pymnt, dtype=float)
    if principal.shape != payments.shape:
        raise ValueError("funded_amnt and total_pymnt must align.")
    if principal.ndim != 1 or principal.size == 0:
        raise ValueError("Cash-yield inputs must be non-empty one-dimensional arrays.")
    if not bool(np.isfinite(principal).all()) or bool(np.any(principal <= 0.0)):
        raise ValueError("funded_amnt must contain finite positive principal values.")
    if not bool(np.isfinite(payments).all()) or bool(np.any(payments < 0.0)):
        raise ValueError("total_pymnt must contain finite nonnegative cumulative payments.")
    return principal, payments
