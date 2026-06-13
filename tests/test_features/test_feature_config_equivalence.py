"""Equivalence tests for the frozen feature_config pickle and YAML views."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.features.feature_config_io import (
    DEFAULT_PICKLE_PATH,
    DEFAULT_YAML_PATH,
    load_feature_config,
)

CORE_EQUIVALENCE_KEYS = (
    "CATBOOST_FEATURES",
    "CATEGORICAL_FEATURES",
    "LOGREG_FEATURES",
    "NUMERIC_FEATURES",
    "FLAG_FEATURES",
    "WOE_FEATURES",
    "INTERACTION_FEATURES",
    "CHALLENGER_FEATURE_POOL_V2",
    "CORE_FEATURE_SET_V2",
    "MISSINGNESS_INDICATORS",
    "iv_scores",
    "schema_version",
)

OPTIONAL_EQUIVALENCE_KEYS = (
    "binning",
    "BINNING",
    "monotone_constraints",
    "MONOTONE_CONSTRAINTS",
)


def _skip_if_missing(path: Path) -> None:
    if not path.is_file():
        pytest.skip(f"{path} not available locally.")


@pytest.mark.integration
def test_frozen_feature_config_pickle_yaml_equivalence() -> None:
    """The champion YAML companion must preserve the pickle feature contract."""
    _skip_if_missing(DEFAULT_PICKLE_PATH)
    _skip_if_missing(DEFAULT_YAML_PATH)

    pickle_cfg = load_feature_config(prefer="pickle")
    yaml_cfg = load_feature_config(prefer="yaml")

    assert set(yaml_cfg) == set(pickle_cfg)
    for key in CORE_EQUIVALENCE_KEYS:
        assert yaml_cfg[key] == pickle_cfg[key]

    for key in OPTIONAL_EQUIVALENCE_KEYS:
        if key in pickle_cfg or key in yaml_cfg:
            assert yaml_cfg.get(key) == pickle_cfg.get(key)


def test_yaml_first_loader_preserves_explicit_pickle_escape_hatch(tmp_path: Path) -> None:
    """Consumers can still force the legacy pickle when auditing format drift."""
    pkl = tmp_path / "feature_config.pkl"
    yml = tmp_path / "feature_config.yml"
    import joblib
    import yaml

    joblib.dump({"CATBOOST_FEATURES": ["from_pickle"]}, pkl)
    yml.write_text(yaml.safe_dump({"CATBOOST_FEATURES": ["from_yaml"]}), encoding="utf-8")

    yaml_cfg: dict[str, Any] = load_feature_config(pickle_path=pkl, yaml_path=yml)
    pickle_cfg: dict[str, Any] = load_feature_config(
        pickle_path=pkl,
        yaml_path=yml,
        prefer="pickle",
    )

    assert yaml_cfg["CATBOOST_FEATURES"] == ["from_yaml"]
    assert pickle_cfg["CATBOOST_FEATURES"] == ["from_pickle"]
