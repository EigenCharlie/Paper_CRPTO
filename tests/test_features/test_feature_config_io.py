"""Round-trip tests for ``src.features.feature_config_io``.

The frozen pipeline still writes ``data/processed/feature_config.pkl``;
this module adds a YAML companion path that downstream code can adopt
gradually. The tests verify equivalence between the two formats and the
auto fallback behaviour.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pytest
import yaml

from src.features.feature_config_io import (
    DEFAULT_PICKLE_PATH,
    load_feature_config,
    pickle_to_yaml,
    save_feature_config,
)

SAMPLE_CONFIG: dict = {
    "NUMERIC_FEATURES": ["loan_amnt", "annual_inc", "dti"],
    "CATEGORICAL_FEATURES": ["grade", "purpose"],
    "WOE_FEATURES": ["grade_woe", "purpose_woe"],
    "iv_scores": {"grade": 0.42, "purpose": 0.18},
    "schema_version": "v2",
}


def test_save_then_load_round_trip(tmp_path: Path) -> None:
    save_feature_config(SAMPLE_CONFIG, repo_root=tmp_path)
    loaded = load_feature_config(repo_root=tmp_path)
    assert loaded == SAMPLE_CONFIG


def test_load_prefers_yaml_over_pickle(tmp_path: Path) -> None:
    yaml_target = tmp_path / "data" / "processed" / "feature_config.yml"
    pkl_target = tmp_path / "data" / "processed" / "feature_config.pkl"
    yaml_target.parent.mkdir(parents=True, exist_ok=True)
    yaml_target.write_text(yaml.safe_dump({"NUMERIC_FEATURES": ["from_yaml"]}))
    joblib.dump({"NUMERIC_FEATURES": ["from_pickle"]}, pkl_target)
    loaded = load_feature_config(repo_root=tmp_path)
    assert loaded["NUMERIC_FEATURES"] == ["from_yaml"]


def test_load_falls_back_to_pickle_when_yaml_absent(tmp_path: Path) -> None:
    pkl_target = tmp_path / "data" / "processed" / "feature_config.pkl"
    pkl_target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"NUMERIC_FEATURES": ["from_pickle"]}, pkl_target)
    loaded = load_feature_config(repo_root=tmp_path)
    assert loaded["NUMERIC_FEATURES"] == ["from_pickle"]


def test_load_prefer_yaml_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_feature_config(repo_root=tmp_path, prefer="yaml")


def test_load_prefer_pickle_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_feature_config(repo_root=tmp_path, prefer="pickle")


def test_pickle_to_yaml_round_trip(tmp_path: Path) -> None:
    pkl = tmp_path / "src.pkl"
    yml = tmp_path / "dst.yml"
    joblib.dump(SAMPLE_CONFIG, pkl)
    pickle_to_yaml(pickle_path=pkl, yaml_path=yml)
    loaded = yaml.safe_load(yml.read_text(encoding="utf-8"))
    assert loaded == SAMPLE_CONFIG


def test_save_also_pickle_writes_both(tmp_path: Path) -> None:
    save_feature_config(SAMPLE_CONFIG, repo_root=tmp_path, also_pickle=True)
    yml = tmp_path / "data" / "processed" / "feature_config.yml"
    pkl = tmp_path / "data" / "processed" / "feature_config.pkl"
    assert yml.is_file()
    assert pkl.is_file()
    assert joblib.load(pkl) == SAMPLE_CONFIG


def test_save_rejects_unknown_prefer_value(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="prefer must be"):
        load_feature_config(repo_root=tmp_path, prefer="json")


# ---------------------------------------------------------------------------
# Live champion artefact (optional — skipped if not present locally)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_champion_pickle_yaml_round_trip(tmp_path: Path) -> None:
    """If the frozen ``feature_config.pkl`` is on disk, the YAML companion
    we generate should round-trip to the same Python dict."""
    if not DEFAULT_PICKLE_PATH.is_file():
        pytest.skip(f"{DEFAULT_PICKLE_PATH} not available locally.")
    original = joblib.load(DEFAULT_PICKLE_PATH)
    yml = tmp_path / "feature_config.yml"
    pickle_to_yaml(pickle_path=DEFAULT_PICKLE_PATH, yaml_path=yml)
    round_tripped = yaml.safe_load(yml.read_text(encoding="utf-8"))
    assert round_tripped == original
