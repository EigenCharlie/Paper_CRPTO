from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.feature_engineering import TARGET
from src.features.tabprep_challenger import (
    TabPrepChallengerTransformer,
    TabPrepVariantConfig,
    resolve_tabprep_categorical_features,
    resolve_tabprep_input_features,
)


def _fixture_frame(n_rows: int = 80) -> pd.DataFrame:
    rng = np.random.default_rng(123)
    dti = np.linspace(4.0, 34.0, n_rows)
    grade = np.where(dti > 20, "C", "A")
    purpose = np.where(np.arange(n_rows) % 3 == 0, "debt_consolidation", "credit_card")
    target = ((dti > 22) | (purpose == "debt_consolidation")).astype(int)
    return pd.DataFrame(
        {
            "id": np.arange(n_rows),
            "issue_d": pd.date_range("2016-01-01", periods=n_rows, freq="MS"),
            "loan_amnt": np.linspace(1_000.0, 20_000.0, n_rows),
            "annual_inc": np.linspace(30_000.0, 120_000.0, n_rows),
            "dti": dti,
            "installment": np.linspace(75.0, 700.0, n_rows),
            "open_acc": rng.integers(1, 12, size=n_rows),
            "has_recent_inq": rng.integers(0, 2, size=n_rows),
            "inq_last_12m__is_missing": rng.integers(0, 2, size=n_rows),
            "grade": grade,
            "purpose": purpose,
            "verification_status": np.where(
                np.arange(n_rows) % 2 == 0, "Verified", "Source Verified"
            ),
            "term": np.where(np.arange(n_rows) % 2 == 0, "36", "60"),
            "loan_status": np.where(target == 1, "Charged Off", "Fully Paid"),
            "url": [f"https://example.invalid/{idx}" for idx in range(n_rows)],
            TARGET: target,
        }
    )


def _feature_config() -> dict[str, object]:
    return {
        "CHALLENGER_FEATURE_POOL_V2": [
            "id",
            "loan_amnt",
            "annual_inc",
            "dti",
            "installment",
            "open_acc",
            "has_recent_inq",
            "inq_last_12m__is_missing",
            "grade",
            "purpose",
            "verification_status",
            "term",
            "loan_status",
            "url",
        ],
        "CATEGORICAL_FEATURES": ["grade", "purpose", "verification_status", "term"],
        "INTERACTION_FEATURES": [],
    }


def _small_variant() -> TabPrepVariantConfig:
    return TabPrepVariantConfig(
        name="unit",
        max_generated_features=24,
        arithmetic_features=8,
        groupby_features=5,
        target_encoding_features=3,
        interaction_encoding_features=4,
        rsfc_features=4,
        max_numeric_base_features=5,
        max_groupby_numeric_features=4,
        max_categorical_base_features=3,
        max_scoring_rows=80,
        n_oof_folds=4,
        min_group_support=2,
    )


def test_resolve_tabprep_input_features_filters_forbidden_columns() -> None:
    frame = _fixture_frame()

    features = resolve_tabprep_input_features(frame, feature_config=_feature_config())

    assert "loan_status" not in features
    assert "url" not in features
    assert "id" not in features
    assert "verification_status" in features
    assert "grade" in features
    assert "dti" in features


def test_tabprep_transformer_is_deterministic_and_split_aligned() -> None:
    train = _fixture_frame()
    test = _fixture_frame(20).assign(grade="Z")
    features = resolve_tabprep_input_features(train, feature_config=_feature_config())
    categorical = resolve_tabprep_categorical_features(features, feature_config=_feature_config())

    first = TabPrepChallengerTransformer(
        variant=_small_variant(),
        input_features=features,
        categorical_features=categorical,
        random_state=7,
    )
    first_train = first.fit_transform(train, train[TARGET], issue_dates=train["issue_d"])
    first_test = first.transform(test)

    second = TabPrepChallengerTransformer(
        variant=_small_variant(),
        input_features=features,
        categorical_features=categorical,
        random_state=7,
    )
    second_train = second.fit_transform(train, train[TARGET], issue_dates=train["issue_d"])
    second_test = second.transform(test)

    assert list(first_train.columns) == list(first_test.columns)
    assert first_train.shape[1] > 0
    assert not np.isinf(first_train.to_numpy(dtype=float)).any()
    assert not np.isinf(first_test.to_numpy(dtype=float)).any()
    pd.testing.assert_frame_equal(first_train, second_train)
    pd.testing.assert_frame_equal(first_test, second_test)


def test_transform_ignores_target_column_in_new_splits() -> None:
    train = _fixture_frame()
    features = resolve_tabprep_input_features(train, feature_config=_feature_config())
    categorical = resolve_tabprep_categorical_features(features, feature_config=_feature_config())
    transformer = TabPrepChallengerTransformer(
        variant=_small_variant(),
        input_features=features,
        categorical_features=categorical,
        random_state=11,
    )
    transformer.fit_transform(train, train[TARGET], issue_dates=train["issue_d"])

    cal_a = _fixture_frame(20)
    cal_b = cal_a.copy()
    cal_a[TARGET] = 0
    cal_b[TARGET] = 1

    pd.testing.assert_frame_equal(transformer.transform(cal_a), transformer.transform(cal_b))


def test_generated_manifest_contains_provenance_without_forbidden_sources() -> None:
    train = _fixture_frame()
    features = resolve_tabprep_input_features(train, feature_config=_feature_config())
    categorical = resolve_tabprep_categorical_features(features, feature_config=_feature_config())
    transformer = TabPrepChallengerTransformer(
        variant=_small_variant(),
        input_features=features,
        categorical_features=categorical,
        random_state=5,
    )
    transformer.fit_transform(train, train[TARGET], issue_dates=train["issue_d"])

    manifest = transformer.feature_manifest()

    assert {"feature", "generator", "operation", "source_features"}.issubset(manifest.columns)
    assert not manifest["source_features"].str.contains("loan_status|url|id").any()
