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
    return expected_objective_coefficients(probabilities, contractual_rates, lgd=lgd)


def expected_objective_coefficients(
    probabilities: np.ndarray,
    contractual_rates: np.ndarray,
    *,
    lgd: float,
) -> np.ndarray:
    """Return coherent expected standardized-payoff objective coefficients."""
    point = np.asarray(probabilities, dtype=float)
    rates = np.asarray(contractual_rates, dtype=float)
    loss_given_default = _validated_payoff_inputs(point, rates, lgd=lgd)
    return (1.0 - point) * rates - point * loss_given_default


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
    loss_given_default = _validated_lgd(lgd)
    _validate_rates(rates)
    if bool(np.isinf(y_true).any()):
        raise ValueError("Outcomes must be binary or NaN when unresolved.")
    observed = np.isfinite(y_true)
    if bool(np.any(observed & ~np.isin(y_true, [0.0, 1.0]))):
        raise ValueError("Observed outcomes must be binary.")
    filled = np.nan_to_num(y_true, nan=0.0)
    realized = (1.0 - filled) * rates - filled * loss_given_default
    lower = np.where(observed, realized, -loss_given_default)
    upper = np.where(observed, realized, rates)
    return lower.astype(float), upper.astype(float)


def _validated_payoff_inputs(
    probabilities: np.ndarray,
    contractual_rates: np.ndarray,
    *,
    lgd: float,
) -> float:
    if probabilities.shape != contractual_rates.shape:
        raise ValueError("probabilities and contractual_rates must align.")
    if not bool(np.isfinite(probabilities).all()) or bool(
        np.any((probabilities < 0.0) | (probabilities > 1.0))
    ):
        raise ValueError("Probabilities must be finite values in [0, 1].")
    _validate_rates(contractual_rates)
    return _validated_lgd(lgd)


def _validate_rates(contractual_rates: np.ndarray) -> None:
    if not bool(np.isfinite(contractual_rates).all()) or bool(
        np.any((contractual_rates < 0.0) | (contractual_rates > 1.0))
    ):
        raise ValueError("Contractual rates must be finite decimal values in [0, 1].")


def _validated_lgd(lgd: float) -> float:
    value = float(lgd)
    if not np.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("LGD must be a finite value in [0, 1].")
    return value
