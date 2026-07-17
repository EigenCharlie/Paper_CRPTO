"""Fixed temporal PD model and probability-calibration helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from src.features.feature_engineering import run_feature_pipeline

OUTCOME_COLUMNS = frozenset(
    {
        "default_flag",
        "loan_status",
        "outcome",
        "payoff",
        "realized_payoff",
        "snapshot_default",
        "snapshot_resolution",
        "weighted_default",
        "weighted_miscoverage",
        "y_true",
    }
)


def validate_model_feature_contract(model_config: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """Return fixed feature lists after rejecting outcome-derived names."""
    numeric = [str(value) for value in model_config["numeric_features"]]
    categorical = [str(value) for value in model_config["categorical_features"]]
    features = numeric + categorical
    duplicates = sorted({name for name in features if features.count(name) > 1})
    if duplicates:
        raise ValueError(f"Model feature config contains duplicates: {duplicates}")
    forbidden = sorted(OUTCOME_COLUMNS.intersection(features))
    if forbidden:
        raise ValueError(f"Model feature config contains outcome fields: {forbidden}")
    return numeric, categorical


def engineer_model_matrix(
    frame: pd.DataFrame,
    *,
    numeric_features: Sequence[str],
    categorical_features: Sequence[str],
) -> pd.DataFrame:
    """Build target-free canonical features with CatBoost-safe dtypes."""
    source = frame.drop(
        columns=["loan_status", "snapshot_default", "snapshot_resolution"],
        errors="ignore",
    )
    engineered = run_feature_pipeline(source)
    output = pd.DataFrame(index=frame.index)
    for feature in numeric_features:
        values = engineered.get(feature, pd.Series(np.nan, index=frame.index))
        output[feature] = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan)
    for feature in categorical_features:
        values = engineered.get(feature, pd.Series("__MISSING__", index=frame.index))
        output[feature] = values.astype("string").fillna("__MISSING__").astype(str)
    if OUTCOME_COLUMNS.intersection(output.columns):
        raise AssertionError("Engineered model matrix contains an outcome field.")
    return output


def require_binary_labels(frame: pd.DataFrame, *, block: str) -> np.ndarray:
    """Return observed binary labels or fail instead of dropping rows."""
    labels = frame["snapshot_default"]
    if bool(labels.isna().any()):
        raise RuntimeError(f"{block} contains unresolved snapshot outcomes.")
    values = labels.astype(int).to_numpy(dtype=int)
    if set(np.unique(values)) != {0, 1}:
        raise RuntimeError(f"{block} must contain both binary outcome classes.")
    return values


def classification_metrics(
    y_true: np.ndarray,
    probabilities: np.ndarray,
) -> dict[str, float | int]:
    """Compute fixed binary probability metrics."""
    clipped = np.clip(np.asarray(probabilities, dtype=float), 1e-12, 1.0 - 1e-12)
    return {
        "rows": int(len(y_true)),
        "default_rate": float(np.mean(y_true)),
        "roc_auc": float(roc_auc_score(y_true, clipped)),
        "brier": float(brier_score_loss(y_true, clipped)),
        "log_loss": float(log_loss(y_true, clipped, labels=[0, 1])),
    }


def catboost_raw_margin(model: CatBoostClassifier, features: pd.DataFrame) -> np.ndarray:
    """Return the one-dimensional CatBoost raw margin."""
    prediction = np.asarray(
        model.predict(features, prediction_type="RawFormulaVal"),
        dtype=float,
    ).reshape(-1)
    if len(prediction) != len(features) or not bool(np.isfinite(prediction).all()):
        raise RuntimeError("CatBoost returned invalid raw margins.")
    return prediction


def fit_platt_calibrator(
    raw_margin: np.ndarray,
    labels: np.ndarray,
    config: Mapping[str, Any],
) -> LogisticRegression:
    """Fit the predeclared Platt calibrator on CatBoost raw margins."""
    model = LogisticRegression(**dict(config["logistic_regression"]))
    model.fit(np.asarray(raw_margin, dtype=float).reshape(-1, 1), labels)
    return model


def apply_platt_calibrator(
    calibrator: LogisticRegression,
    raw_margin: np.ndarray,
) -> np.ndarray:
    """Apply a fitted raw-margin Platt calibrator."""
    probabilities = np.asarray(
        calibrator.predict_proba(np.asarray(raw_margin, dtype=float).reshape(-1, 1))[:, 1],
        dtype=float,
    )
    if not bool(np.isfinite(probabilities).all()):
        raise RuntimeError("Probability calibrator returned non-finite values.")
    return np.clip(probabilities, 0.0, 1.0)
