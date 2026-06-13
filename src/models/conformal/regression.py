"""Regression-style conformal interval helpers."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from loguru import logger


def create_regression_intervals(
    regressor: Any,
    X_cal: pd.DataFrame,
    y_cal: pd.Series,
    X_test: pd.DataFrame,
    alpha: float = 0.1,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate regression intervals using MAPIE."""
    from mapie.regression import SplitConformalRegressor

    mapie = SplitConformalRegressor(
        estimator=regressor,
        confidence_level=1 - alpha,
        prefit=True,
    )
    mapie.conformalize(X_cal, y_cal)

    y_pred, y_intervals_raw = mapie.predict_interval(X_test)
    y_intervals = y_intervals_raw[:, :, 0]

    avg_width = (y_intervals[:, 1] - y_intervals[:, 0]).mean()
    logger.info(f"Conformal regression intervals (alpha={alpha}): avg_width={avg_width:.4f}")
    return y_pred, y_intervals


def create_residual_intervals(
    regressor: Any,
    X_cal: pd.DataFrame,
    y_cal: pd.Series,
    X_test: pd.DataFrame,
    alpha: float = 0.1,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate naive residual-based prediction intervals as a benchmark."""
    if hasattr(regressor, "predict_proba"):
        cal_preds = regressor.predict_proba(X_cal)[:, 1]
        test_preds = regressor.predict_proba(X_test)[:, 1]
    else:
        cal_preds = regressor.predict(X_cal)
        test_preds = regressor.predict(X_test)

    cal_preds = np.asarray(cal_preds, dtype=float)
    test_preds = np.asarray(test_preds, dtype=float)
    y_cal_arr = np.asarray(y_cal, dtype=float)

    residuals = y_cal_arr - cal_preds
    q_low = np.percentile(residuals, 100 * (alpha / 2))
    q_high = np.percentile(residuals, 100 * (1 - alpha / 2))

    low = test_preds + q_low
    high = test_preds + q_high
    y_intervals = np.column_stack([low, high])

    avg_width = float((high - low).mean())
    logger.info(f"Residual intervals (bootstrap-style, alpha={alpha}): avg_width={avg_width:.4f}")
    return test_preds, y_intervals
