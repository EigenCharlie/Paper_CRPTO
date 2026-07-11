from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.features.feature_engineering import (
    CATBOOST_FEATURES,
    CATEGORICAL_FEATURES,
    TARGET,
    build_feature_config,
    build_feature_manifest,
    normalize_raw_columns,
)

CONTRACT_PATH = Path("models/pd_model_contract.json")
EXPECTED_CONTRACT_OMISSIONS = {"rev_utilization", "high_util_pct"}


def test_lending_club_credit_line_dates_use_the_declared_month_year_format() -> None:
    normalized = normalize_raw_columns(
        pd.DataFrame(
            {
                "issue_d": ["2016-04-01", "2016-05-01"],
                "earliest_cr_line": ["Jan-1985", "Sep-2007"],
            }
        )
    )

    assert normalized["earliest_cr_line"].tolist() == [
        pd.Timestamp("1985-01-01"),
        pd.Timestamp("2007-09-01"),
    ]


def _load_contract() -> dict[str, object]:
    if not CONTRACT_PATH.is_file():
        pytest.skip(f"{CONTRACT_PATH} is not available in this checkout.")
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_frozen_pd_contract_matches_current_catboost_feature_order() -> None:
    contract = _load_contract()
    feature_names = contract["feature_names"]
    categorical = contract["categorical_features"]
    n_features = contract["n_features"]
    assert isinstance(feature_names, list)
    assert isinstance(categorical, list)
    assert isinstance(n_features, int)
    assert all(isinstance(feature, str) for feature in feature_names)
    assert all(isinstance(feature, str) for feature in categorical)

    expected_features = [
        feature for feature in CATBOOST_FEATURES if feature not in EXPECTED_CONTRACT_OMISSIONS
    ]

    assert n_features == 42
    assert len(feature_names) == 42
    assert feature_names == expected_features
    assert categorical == CATEGORICAL_FEATURES
    assert set(CATBOOST_FEATURES) - set(feature_names) == EXPECTED_CONTRACT_OMISSIONS


def test_feature_config_materializes_the_champion_feature_contract() -> None:
    contract = _load_contract()
    feature_names = contract["feature_names"]
    assert isinstance(feature_names, list)
    assert all(isinstance(feature, str) for feature in feature_names)
    frame = pd.DataFrame(
        {
            **{feature: [1, 2, 3] for feature in feature_names},
            "id": [101, 102, 103],
            "issue_d": pd.to_datetime(["2018-01-01", "2018-02-01", "2018-03-01"]),
            "loan_status": ["Current", "Charged Off", "Current"],
            TARGET: [0, 1, 0],
        }
    )

    config = build_feature_config(frame)
    manifest = build_feature_manifest(frame, frame, frame, feature_config=config)
    roles = dict(zip(manifest["feature"], manifest["role"], strict=True))

    assert config["CATBOOST_FEATURES"] == feature_names
    assert config["CORE_FEATURE_SET_V2"] == feature_names
    assert set(EXPECTED_CONTRACT_OMISSIONS).isdisjoint(config["CATBOOST_FEATURES"])
    assert roles["loan_amnt"] == "core_shared"
    assert roles["grade"] == "core_catboost_only"
    assert roles["int_rate_bucket__grade"] == "core_catboost_only"
    assert roles[TARGET] == "target"
    assert roles["issue_d"] == "metadata"
