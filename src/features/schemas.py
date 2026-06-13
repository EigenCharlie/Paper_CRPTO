"""Pandera schemas for DataFrame validation at pipeline boundaries."""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa

# ── Loan Master Schema ──
loan_master_schema = pa.DataFrameSchema(
    columns={
        "loan_amnt": pa.Column(float, pa.Check.greater_than(0), nullable=False),
        "annual_inc": pa.Column(float, pa.Check.greater_than_or_equal_to(0), nullable=True),
        "loan_to_income": pa.Column(float, pa.Check.in_range(0, 100), nullable=True),
        "dti": pa.Column(float, pa.Check.in_range(0, 999), nullable=True),
        "default_flag": pa.Column(int, pa.Check.isin([0, 1]), nullable=False),
        "int_rate": pa.Column(float, pa.Check.in_range(0, 100), nullable=True),
    },
    coerce=True,
    strict=False,  # Allow extra columns
)

# ── Time Series Schema (Nixtla-compatible) ──
time_series_schema = pa.DataFrameSchema(
    columns={
        "ds": pa.Column("datetime64[ns]", nullable=False),
        "unique_id": pa.Column(str, nullable=False),
        "y": pa.Column(float, pa.Check.in_range(0, 1), nullable=False),  # default_rate
        "loan_count": pa.Column(int, pa.Check.greater_than(0), nullable=False),
    },
    coerce=True,
    strict=False,
)

# ── EAD Dataset Schema ──
ead_schema = pa.DataFrameSchema(
    columns={
        "default_flag": pa.Column(int, pa.Check.equal_to(1), nullable=False),  # Only defaults
        "loan_amnt": pa.Column(float, pa.Check.greater_than(0), nullable=False),
    },
    coerce=True,
    strict=False,
)

# ── Prediction Output Schema ──
prediction_schema = pa.DataFrameSchema(
    columns={
        "pd_point": pa.Column(float, pa.Check.in_range(0, 1), nullable=False),
        "pd_low": pa.Column(float, pa.Check.in_range(0, 1), nullable=False),
        "pd_high": pa.Column(float, pa.Check.in_range(0, 1), nullable=False),
    },
    checks=[
        pa.Check(
            lambda df: (df["pd_low"] <= df["pd_point"]).all(), error="pd_low must be <= pd_point"
        ),
        pa.Check(
            lambda df: (df["pd_point"] <= df["pd_high"]).all(), error="pd_point must be <= pd_high"
        ),
    ],
    coerce=True,
    strict=False,
)


# ── Conformal Output Schema ──
conformal_output_schema = pa.DataFrameSchema(
    columns={
        "y_pred": pa.Column(float, pa.Check.in_range(0, 1), nullable=False),
        "pd_low_90": pa.Column(float, pa.Check.in_range(0, 1), nullable=False),
        "pd_high_90": pa.Column(float, pa.Check.in_range(0, 1), nullable=False),
        "grade": pa.Column(str, nullable=True),
        "width_90": pa.Column(float, pa.Check.greater_than_or_equal_to(0), nullable=False),
    },
    checks=[
        pa.Check(
            lambda df: (df["pd_low_90"] <= df["pd_high_90"]).all(),
            error="pd_low_90 must be <= pd_high_90",
        ),
    ],
    coerce=True,
    strict=False,
)

feature_config_table_schema = pa.DataFrameSchema(
    columns={
        "section": pa.Column(str, nullable=False),
        "kind": pa.Column(str, pa.Check.isin(["list", "dict", "scalar"]), nullable=False),
        "ordinal": pa.Column(int, pa.Check.greater_than_or_equal_to(0), nullable=False),
        "key": pa.Column(str, nullable=True),
        "value_json": pa.Column(str, nullable=False),
    },
    coerce=True,
    strict=True,
)


def validate_conformal_output(df: pd.DataFrame) -> pd.DataFrame:
    """Validate conformal intervals DataFrame."""
    return conformal_output_schema.validate(df)


def validate_loan_master(df: pd.DataFrame) -> pd.DataFrame:
    """Validate loan_master DataFrame."""
    return loan_master_schema.validate(df)


def validate_time_series(df: pd.DataFrame) -> pd.DataFrame:
    """Validate time_series DataFrame."""
    return time_series_schema.validate(df)


def validate_predictions(df: pd.DataFrame) -> pd.DataFrame:
    """Validate prediction output DataFrame."""
    return prediction_schema.validate(df)


def validate_feature_config_table(df: pd.DataFrame) -> pd.DataFrame:
    """Validate the long-form feature configuration table."""
    return feature_config_table_schema.validate(df)


# ---------------------------------------------------------------------------
# DataFrameModel variants (Pandera 0.20+ class-based style)
# ---------------------------------------------------------------------------
#
# The dict-based ``DataFrameSchema`` above remains the canonical contract used
# by the pipeline. The class-based ``DataFrameModel`` form below is the
# recommended modern style for new schemas: it gives IDE autocomplete, is
# subclass-friendly, and renders cleanly in MRM model cards.


class PredictionOutputModel(pa.DataFrameModel):
    """Class-based equivalent of :data:`prediction_schema`."""

    pd_point: pa.typing.Series[float] = pa.Field(ge=0.0, le=1.0)
    pd_low: pa.typing.Series[float] = pa.Field(ge=0.0, le=1.0)
    pd_high: pa.typing.Series[float] = pa.Field(ge=0.0, le=1.0)

    @pa.dataframe_check
    @classmethod
    def low_le_point_le_high(cls, df: pd.DataFrame) -> bool:
        return bool(((df["pd_low"] <= df["pd_point"]) & (df["pd_point"] <= df["pd_high"])).all())

    class Config:
        coerce = True
        strict = False


class ConformalOutputModel(pa.DataFrameModel):
    """Class-based equivalent of :data:`conformal_output_schema`."""

    y_pred: pa.typing.Series[float] = pa.Field(ge=0.0, le=1.0)
    pd_low_90: pa.typing.Series[float] = pa.Field(ge=0.0, le=1.0)
    pd_high_90: pa.typing.Series[float] = pa.Field(ge=0.0, le=1.0)
    grade: pa.typing.Series[str] = pa.Field(nullable=True)
    width_90: pa.typing.Series[float] = pa.Field(ge=0.0)

    @pa.dataframe_check
    @classmethod
    def low_le_high(cls, df: pd.DataFrame) -> bool:
        return bool((df["pd_low_90"] <= df["pd_high_90"]).all())

    class Config:
        coerce = True
        strict = False
