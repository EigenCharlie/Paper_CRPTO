"""Coherent expected and realized standardized credit payoff."""

from __future__ import annotations

import numpy as np
import pandas as pd

PAYOFF_ID = "coherent_standardized_binary_payoff_v1"


def contractual_rate_decimal(values: pd.Series) -> np.ndarray:
    """Convert Lending Club percent-point rates to decimal annual rates once."""
    rates = (
        values.astype("string")
        .str.strip()
        .str.rstrip("%")
        .pipe(pd.to_numeric, errors="coerce")
        .to_numpy(dtype=float)
        / 100.0
    )
    if not bool(np.isfinite(rates).all()) or bool(np.any((rates < 0.0) | (rates > 1.0))):
        raise ValueError("Contractual rates must be finite percent-point values in [0, 100].")
    return rates


def expected_standardized_payoff_rate(
    probabilities: np.ndarray,
    contractual_rates: np.ndarray,
    *,
    lgd: float,
) -> np.ndarray:
    """Return ``(1-p)r - p*LGD`` per dollar of exposure."""
    point = np.asarray(probabilities, dtype=float)
    rates = np.asarray(contractual_rates, dtype=float)
    if point.shape != rates.shape:
        raise ValueError("probabilities and contractual_rates must align.")
    return (1.0 - point) * rates - point * float(lgd)


def realized_standardized_payoff_bounds(
    outcomes: np.ndarray,
    contractual_rates: np.ndarray,
    *,
    lgd: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return sharp payoff bounds while retaining unresolved outcomes."""
    y_true = np.asarray(outcomes, dtype=float)
    rates = np.asarray(contractual_rates, dtype=float)
    if y_true.shape != rates.shape:
        raise ValueError("outcomes and contractual_rates must align.")
    observed = np.isfinite(y_true)
    if bool(np.any(observed & ~np.isin(y_true, [0.0, 1.0]))):
        raise ValueError("Observed outcomes must be binary.")
    filled = np.nan_to_num(y_true, nan=0.0)
    realized = (1.0 - filled) * rates - filled * float(lgd)
    lower = np.where(observed, realized, -float(lgd))
    upper = np.where(observed, realized, rates)
    return lower.astype(float), upper.astype(float)
