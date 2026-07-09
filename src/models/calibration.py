"""Probability calibration methods.

Available methods: Isotonic, Platt (Sigmoid), Beta, and Venn-Abers.
Canonical calibrator is selected at training time via temporal multi-metric validation.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pandas as pd
from loguru import logger
from scipy.optimize import minimize_scalar
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

from src.utils.io_utils import load_pickle_compat


class LogitShiftCalibrator:
    """Lightweight serializable calibrator that shifts log-odds by a fixed delta."""

    def __init__(self, delta: float):
        self.delta = float(delta)

    def transform(self, scores: np.ndarray) -> np.ndarray:
        scores_arr = np.clip(np.asarray(scores, dtype=float), 1e-6, 1.0 - 1e-6)
        logits = np.log(scores_arr / (1.0 - scores_arr))
        shifted = 1.0 / (1.0 + np.exp(-(logits + self.delta)))
        clipped: np.ndarray = np.clip(np.asarray(shifted, dtype=float), 0.0, 1.0)
        return clipped

    def predict(self, scores: np.ndarray) -> np.ndarray:
        return self.transform(scores)

    def get_params(self, deep: bool = True) -> dict[str, float]:
        return {"delta": float(self.delta)}

    def __repr__(self) -> str:
        return f"LogitShiftCalibrator(delta={self.delta:.6f})"


class TemperatureScalingCalibrator:
    """Serializable binary temperature scaler over probability logits."""

    def __init__(self, temperature: float = 1.0) -> None:
        self.temperature = float(temperature)
        self._is_fitted = False

    @staticmethod
    def _logit(scores: np.ndarray) -> np.ndarray:
        clipped = np.clip(np.asarray(scores, dtype=float).reshape(-1), 1e-6, 1.0 - 1e-6)
        logits: np.ndarray = np.log(clipped / (1.0 - clipped))
        return logits

    @staticmethod
    def _sigmoid(logits: np.ndarray) -> np.ndarray:
        return cast(np.ndarray, 1.0 / (1.0 + np.exp(-logits)))

    def fit(self, y_prob_raw: np.ndarray, y_true: np.ndarray) -> TemperatureScalingCalibrator:
        logits = self._logit(y_prob_raw)
        y = np.asarray(y_true, dtype=int)

        def objective(raw_temperature: float) -> float:
            temperature = max(float(raw_temperature), 1e-3)
            pred = np.clip(self._sigmoid(logits / temperature), 1e-6, 1.0 - 1e-6)
            return float(log_loss(y, pred))

        result = minimize_scalar(objective, bounds=(0.05, 10.0), method="bounded")
        self.temperature = float(result.x if result.success else 1.0)
        self._is_fitted = True
        logger.info("Fitted temperature scaling calibrator (T={:.6f})", self.temperature)
        return self

    def predict(self, y_prob_raw: np.ndarray) -> np.ndarray:
        if not self._is_fitted:
            raise RuntimeError("TemperatureScalingCalibrator is not fitted.")
        logits = self._logit(y_prob_raw)
        clipped: np.ndarray = np.clip(self._sigmoid(logits / max(self.temperature, 1e-3)), 0.0, 1.0)
        return clipped


class QuadraticLogitCalibrator:
    """Logistic calibrator over logit(p) and logit(p)^2."""

    def __init__(self) -> None:
        self.model = LogisticRegression(max_iter=1000)
        self._is_fitted = False

    @staticmethod
    def _design_matrix(y_prob_raw: np.ndarray) -> np.ndarray:
        clipped = np.clip(np.asarray(y_prob_raw, dtype=float).reshape(-1), 1e-6, 1.0 - 1e-6)
        logits = np.log(clipped / (1.0 - clipped))
        return np.column_stack([logits, logits**2])

    def fit(self, y_prob_raw: np.ndarray, y_true: np.ndarray) -> QuadraticLogitCalibrator:
        self.model.fit(self._design_matrix(y_prob_raw), np.asarray(y_true, dtype=int))
        self._is_fitted = True
        logger.info("Fitted quadratic-logit calibrator")
        return self

    def predict(self, y_prob_raw: np.ndarray) -> np.ndarray:
        if not self._is_fitted:
            raise RuntimeError("QuadraticLogitCalibrator is not fitted.")
        return cast(np.ndarray, self.model.predict_proba(self._design_matrix(y_prob_raw))[:, 1])


def expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Compute Expected Calibration Error (ECE)."""
    bin_edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (y_prob >= bin_edges[i]) & (y_prob < bin_edges[i + 1])
        if mask.sum() == 0:
            continue
        bin_acc = y_true[mask].mean()
        bin_conf = y_prob[mask].mean()
        ece += mask.sum() / len(y_true) * abs(bin_acc - bin_conf)
    return ece


def adaptive_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Compute quantile-binned ECE to reduce sensitivity to sparse fixed bins."""
    y_arr = np.asarray(y_true, dtype=float).reshape(-1)
    p_arr = np.asarray(y_prob, dtype=float).reshape(-1)
    if len(y_arr) == 0:
        return 0.0
    order = np.argsort(p_arr, kind="mergesort")
    y_sorted = y_arr[order]
    p_sorted = p_arr[order]
    bins = [
        chunk
        for chunk in np.array_split(np.arange(len(y_sorted)), max(1, int(n_bins)))
        if len(chunk)
    ]
    ace = 0.0
    for idx in bins:
        bin_acc = float(y_sorted[idx].mean())
        bin_conf = float(p_sorted[idx].mean())
        ace += len(idx) / len(y_sorted) * abs(bin_acc - bin_conf)
    return float(ace)


def calibrate_isotonic(
    y_cal: np.ndarray,
    proba_cal: np.ndarray,
) -> IsotonicRegression:
    """Fit isotonic regression calibrator."""
    iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip")
    iso.fit(proba_cal, y_cal)
    logger.info("Fitted isotonic calibrator")
    return iso


def calibrate_platt(
    model: Any,
    X_cal: pd.DataFrame,
    y_cal: pd.Series,
) -> LogisticRegression:
    """Fit Platt scaling as logistic regression over raw model scores.

    Returning a score-based calibrator keeps downstream conformal code agnostic
    to feature-space requirements of the base classifier.
    """
    proba_cal = model.predict_proba(X_cal)[:, 1]
    cal_model = LogisticRegression(max_iter=1000)
    cal_model.fit(proba_cal.reshape(-1, 1), y_cal)
    logger.info("Fitted Platt scaling calibrator")
    return cal_model


def calibrate_beta(
    y_cal: np.ndarray,
    proba_cal: np.ndarray,
    parameters: str = "abm",
) -> Any:
    """Fit beta calibration (Kull et al. 2017).

    Args:
        y_cal: Binary labels.
        proba_cal: Raw probabilities from base model.
        parameters: Beta calibration parameterisation.
            "abm" = 3 parameters (handles asymmetric distortions).
            "am" = 2 parameters (equivalent to Platt when a=b).

    Returns:
        Fitted BetaCalibration object with .predict() method.
    """
    from betacal import BetaCalibration

    bc = BetaCalibration(parameters=parameters)
    bc.fit(proba_cal, y_cal)
    logger.info(f"Fitted beta calibrator (parameters={parameters})")
    return bc


def evaluate_calibration(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    name: str = "model",
    n_bins: int = 10,
) -> dict[str, float]:
    """Evaluate calibration quality."""
    from sklearn.metrics import brier_score_loss, log_loss

    ece = expected_calibration_error(y_true, y_prob, n_bins)
    adaptive_ece = adaptive_calibration_error(y_true, y_prob, n_bins)
    brier = brier_score_loss(y_true, y_prob)
    logloss = log_loss(y_true, y_prob)
    metrics = {
        "ece": ece,
        "adaptive_ece": adaptive_ece,
        "brier_score": brier,
        "log_loss": logloss,
    }
    logger.info(
        f"Calibration [{name}] — ECE: {ece:.4f}, Adaptive ECE: {adaptive_ece:.4f}, "
        f"Brier: {brier:.4f}, Log-loss: {logloss:.4f}"
    )
    return metrics


def load_probability_calibrator(path: str | None) -> Any | None:
    """Load a canonical or shadow calibrator from disk."""
    if not path:
        return None
    return load_pickle_compat(path)
