from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ijds_audit.missingness_sensitivity import (
    build_missingness_variant,
    load_missingness_config,
)
from src.ijds_audit.prediction import PreparedData

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/experiments/ijds_missingness_sensitivity_2026-07-15_v3.yaml"
LEGACY_CONFIG = ROOT / "configs/experiments/ijds_missingness_sensitivity_2026-07-15_v2.yaml"


def _prepared() -> PreparedData:
    universe = pd.DataFrame(
        {
            "mths_since_last_delinq": [None, 12.0, 24.0],
            "pub_rec_bankruptcies": [None, 0.0, 2.0],
        }
    )
    features = pd.DataFrame(
        {
            "delinq_recency": [999.0, 12.0, 24.0],
            "has_bankruptcy": [0, 0, 1],
            "income": [1.0, 2.0, 3.0],
            "purpose": ["a", "b", "c"],
        }
    )
    return PreparedData(
        universe=universe,
        features=features,
        numeric_features=("delinq_recency", "has_bankruptcy", "income"),
        categorical_features=("purpose",),
        source_inventory={},
        availability_audit=pd.DataFrame(),
        monthly_residual_availability=pd.DataFrame(),
    )


def test_missingness_protocol_is_closed_and_no_selection() -> None:
    config = load_missingness_config(CONFIG, repo_root=ROOT)
    assert [item["id"] for item in config["specifications"]] == [
        "catboost_platt",
        "catboost_missing_indicators_platt",
        "catboost_native_missing_platt",
    ]
    assert config["evaluation"]["no_model_selection"] is True
    assert config["evaluation"]["no_portfolio_optimization"] is True
    assert config["protocol_tag"].endswith("2026-07-15-v3")
    assert config["specifications"][2]["added_numeric_features"] == [
        "delinq_recency_native",
        "has_bankruptcy_native",
    ]


def test_stopped_v2_contract_remains_parseable_but_distinct() -> None:
    config = load_missingness_config(LEGACY_CONFIG, repo_root=ROOT)
    assert config["specifications"][2]["added_numeric_features"] == [
        "delinq_recency_native",
        "bankruptcy_count_native",
    ]


def test_explicit_indicator_variant_retains_active_mappings() -> None:
    variant = build_missingness_variant(_prepared(), variant="explicit_indicators")
    assert variant.features["delinq_recency"].tolist() == [999.0, 12.0, 24.0]
    assert variant.features["delinq_recency_missing"].tolist() == [1, 0, 0]
    assert variant.features["bankruptcy_count_missing"].tolist() == [1, 0, 0]


def test_native_variant_preserves_feature_semantics_and_nan() -> None:
    variant = build_missingness_variant(_prepared(), variant="native_missing")
    assert "delinq_recency" not in variant.features
    assert "has_bankruptcy" not in variant.features
    assert pd.isna(variant.features.loc[0, "delinq_recency_native"])
    assert pd.isna(variant.features.loc[0, "has_bankruptcy_native"])
    assert variant.features.loc[1, "delinq_recency_native"] == 12.0
    assert variant.features["has_bankruptcy_native"].iloc[1:].tolist() == [0.0, 1.0]
    assert "bankruptcy_count_native" not in variant.features


def test_legacy_native_variant_remains_explicitly_reproducible() -> None:
    variant = build_missingness_variant(_prepared(), variant="native_missing_legacy_count")
    assert pd.isna(variant.features.loc[0, "bankruptcy_count_native"])
    assert variant.features["bankruptcy_count_native"].iloc[1:].tolist() == [0.0, 2.0]
