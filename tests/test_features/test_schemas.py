"""Tests for the Pandera schemas in :mod:`src.features.schemas`.

Both the dict-based ``DataFrameSchema`` and the class-based ``DataFrameModel``
forms must accept canonical CRPTO outputs and reject the common violations
(non-monotone PD intervals, out-of-range probabilities).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pandera.errors
import pytest

from src.features import schemas as cs

# ---------------------------------------------------------------------------
# Loan master
# ---------------------------------------------------------------------------


def _valid_loan_master(n: int = 8) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "loan_amnt": rng.uniform(1000, 35_000, n),
            "annual_inc": rng.uniform(30_000, 200_000, n),
            "loan_to_income": rng.uniform(0.01, 1.0, n),
            "dti": rng.uniform(0.5, 35.0, n),
            "default_flag": rng.integers(0, 2, n),
            "int_rate": rng.uniform(5.0, 25.0, n),
        }
    )


def test_loan_master_accepts_canonical_frame() -> None:
    df = _valid_loan_master()
    out = cs.validate_loan_master(df)
    assert len(out) == len(df)


def test_loan_master_rejects_invalid_default_flag() -> None:
    df = _valid_loan_master()
    df.loc[0, "default_flag"] = 7  # not in {0, 1}
    with pytest.raises(pandera.errors.SchemaError):
        cs.validate_loan_master(df)


# ---------------------------------------------------------------------------
# Prediction (dict-based + class-based)
# ---------------------------------------------------------------------------


def _valid_predictions(n: int = 8) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    pd_point = rng.uniform(0.05, 0.4, n)
    delta = rng.uniform(0.0, 0.05, n)
    return pd.DataFrame(
        {
            "pd_point": pd_point,
            "pd_low": np.clip(pd_point - delta, 0.0, 1.0),
            "pd_high": np.clip(pd_point + delta, 0.0, 1.0),
        }
    )


def test_prediction_schema_accepts_monotone_intervals() -> None:
    df = _valid_predictions()
    out = cs.validate_predictions(df)
    assert len(out) == len(df)


def test_prediction_schema_rejects_inverted_bounds() -> None:
    df = _valid_predictions()
    df.loc[0, "pd_low"] = df.loc[0, "pd_high"] + 0.05  # invert
    with pytest.raises(pandera.errors.SchemaError):
        cs.validate_predictions(df)


def test_prediction_dataframe_model_accepts_monotone_intervals() -> None:
    df = _valid_predictions()
    out = cs.PredictionOutputModel.validate(df)
    assert len(out) == len(df)


def test_prediction_dataframe_model_rejects_out_of_range_probabilities() -> None:
    df = _valid_predictions()
    df.loc[0, "pd_high"] = 1.5
    with pytest.raises(pandera.errors.SchemaError):
        cs.PredictionOutputModel.validate(df)


# ---------------------------------------------------------------------------
# Conformal output
# ---------------------------------------------------------------------------


def _valid_conformal(n: int = 8) -> pd.DataFrame:
    rng = np.random.default_rng(2)
    y_pred = rng.uniform(0.05, 0.4, n)
    width = rng.uniform(0.0, 0.1, n)
    return pd.DataFrame(
        {
            "y_pred": y_pred,
            "pd_low_90": np.clip(y_pred - width / 2, 0.0, 1.0),
            "pd_high_90": np.clip(y_pred + width / 2, 0.0, 1.0),
            "grade": rng.choice(["A", "B", "C"], n),
            "width_90": width,
        }
    )


def test_conformal_schema_accepts_canonical_frame() -> None:
    df = _valid_conformal()
    out = cs.validate_conformal_output(df)
    assert len(out) == len(df)


def test_conformal_dataframe_model_round_trip() -> None:
    df = _valid_conformal()
    out = cs.ConformalOutputModel.validate(df)
    assert len(out) == len(df)


def test_conformal_schema_rejects_negative_width() -> None:
    df = _valid_conformal()
    df.loc[0, "width_90"] = -0.05
    with pytest.raises(pandera.errors.SchemaError):
        cs.validate_conformal_output(df)
