from __future__ import annotations

import pytest

import scripts.train_pd_model as pd_train
from scripts.train_pd_model import (
    TrainingSplits,
    _apply_cli_overrides,
    _apply_pd_replay_manifest,
    _load_training_splits,
    _normalize_sample_size,
    _sample_training_splits,
)


def _base_config() -> dict[str, object]:
    return {
        "training_regime": {"mode": "full", "recent_window_quarters": 8},
        "stable_core": {"enabled": False},
        "hpo": {"enabled": True, "n_trials": 100},
        "challenger_pipeline": {"enabled": True},
        "validation": {
            "walk_forward": {"enabled": True},
            "seed_replay": {"enabled": True},
        },
        "model": {"params": {"iterations": 500, "learning_rate": 0.05}},
    }


def test_apply_cli_overrides_keeps_nested_config_intent() -> None:
    base = _base_config()

    updated = _apply_cli_overrides(
        base,
        training_regime_mode="recent",
        recent_window_quarters=4,
        half_life_quarters=2,
        stable_core_enabled=True,
        hpo_n_trials=12,
        hpo_enabled=False,
        challenger_enabled=False,
        walk_forward_enabled=False,
        seed_replay_enabled=False,
        catboost_iterations=250,
    )

    assert base["training_regime"] == {"mode": "full", "recent_window_quarters": 8}
    assert updated["training_regime"] == {
        "mode": "recent",
        "recent_window_quarters": 4,
        "half_life_quarters": 2,
    }
    assert updated["stable_core"] == {"enabled": True}
    assert updated["hpo"] == {"enabled": False, "n_trials": 12}
    assert updated["challenger_pipeline"] == {"enabled": False}
    assert updated["validation"] == {
        "walk_forward": {"enabled": False},
        "seed_replay": {"enabled": False},
    }
    assert updated["model"] == {"params": {"iterations": 250, "learning_rate": 0.05}}


def test_apply_pd_replay_manifest_forces_replay_without_dropping_base_params() -> None:
    replay_cfg = {"selected_params": {"depth": 6, "learning_rate": 0.0573}}

    updated = _apply_pd_replay_manifest(_base_config(), replay_cfg)

    assert updated["hpo"]["enabled"] is False
    assert updated["validation"]["seed_replay"]["enabled"] is False
    assert updated["challenger_pipeline"]["enabled"] is False
    assert updated["model"]["params"] == {
        "iterations": 500,
        "learning_rate": 0.0573,
        "depth": 6,
    }


def test_apply_pd_replay_manifest_requires_selected_params() -> None:
    with pytest.raises(ValueError, match="selected_params"):
        _apply_pd_replay_manifest(_base_config(), {"selected_params": {}})


def test_resolve_training_features_filters_splits_and_disables_stable_core_in_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_resolve_feature_sets(*args, **kwargs):
        return {
            "feature_source": "fixture",
            "catboost_features": ["a", "b", "missing", "rev_utilization"],
            "logreg_features": ["a", "b", "rev_utilization"],
            "categorical_features": ["b", "missing"],
        }

    monkeypatch.setattr(pd_train, "resolve_feature_sets", fake_resolve_feature_sets)
    train = pd_train.pd.DataFrame({"a": [1], "b": ["x"], "rev_utilization": [0.2]})
    cal = pd_train.pd.DataFrame({"a": [1], "b": ["x"], "rev_utilization": [0.2]})
    test = pd_train.pd.DataFrame({"a": [1], "b": ["x"], "rev_utilization": [0.2]})

    resolved = pd_train._resolve_training_features(
        config={
            "feature_source": {"mode": "auto", "feature_config_path": "feature_config.pkl"},
            "stable_core": {"enabled": True, "exclude_features": ["rev_utilization"]},
        },
        train=train,
        cal=cal,
        test=test,
        run_mode="search",
        replay_cfg={},
    )

    assert resolved.feature_source == "fixture"
    assert resolved.catboost_features == ["a", "b"]
    assert resolved.logreg_features == ["a", "b"]
    assert resolved.categorical_features == ["b"]
    assert resolved.stable_core_meta["enabled"] is True

    replay = pd_train._resolve_training_features(
        config={
            "feature_source": {"mode": "auto", "feature_config_path": "feature_config.pkl"},
            "stable_core": {"enabled": True, "exclude_features": ["rev_utilization"]},
        },
        train=train,
        cal=cal,
        test=test,
        run_mode="replay",
        replay_cfg={
            "feature_names": ["a", "rev_utilization"],
            "categorical_features": ["rev_utilization"],
        },
    )

    assert replay.catboost_features == ["a", "rev_utilization"]
    assert replay.logreg_features == ["a", "rev_utilization"]
    assert replay.categorical_features == ["rev_utilization"]
    assert replay.stable_core_meta == {"enabled": False, "excluded_features": []}


def test_load_training_splits_uses_config_paths_and_normalizes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_read_split(path: str) -> pd_train.pd.DataFrame:
        calls.append(path)
        return pd_train.pd.DataFrame({"source": [path]})

    def fake_normalize(df: pd_train.pd.DataFrame) -> pd_train.pd.DataFrame:
        out = df.copy()
        out["normalized"] = True
        return out

    monkeypatch.setattr(pd_train, "read_split_with_fe_fallback", fake_read_split)
    monkeypatch.setattr(pd_train, "_normalize_percent_columns", fake_normalize)

    splits = _load_training_splits(
        {
            "train_path": "train.parquet",
            "test_path": "test.parquet",
            "calibration_path": "calibration.parquet",
        }
    )

    assert calls == ["train.parquet", "test.parquet", "calibration.parquet"]
    assert splits.train.to_dict(orient="records") == [
        {"source": "train.parquet", "normalized": True}
    ]
    assert splits.test.to_dict(orient="records") == [{"source": "test.parquet", "normalized": True}]
    assert splits.cal.to_dict(orient="records") == [
        {"source": "calibration.parquet", "normalized": True}
    ]


def test_sample_training_splits_is_deterministic_and_keeps_small_splits() -> None:
    train = pd_train.pd.DataFrame({"row": range(10)})
    cal = pd_train.pd.DataFrame({"row": range(10, 20)})
    test = pd_train.pd.DataFrame({"row": [100, 101]})

    sampled = _sample_training_splits(TrainingSplits(train=train, cal=cal, test=test), 3)

    assert sampled.train["row"].tolist() == train.sample(n=3, random_state=42)["row"].tolist()
    assert sampled.cal["row"].tolist() == cal.sample(n=3, random_state=42)["row"].tolist()
    assert sampled.test.equals(test)
    assert sampled.train.index.tolist() == [0, 1, 2]
    assert sampled.cal.index.tolist() == [0, 1, 2]


@pytest.mark.parametrize("raw_sample_size", [None, 0, -5])
def test_normalize_sample_size_treats_non_positive_as_full_data(
    raw_sample_size: int | None,
) -> None:
    assert _normalize_sample_size(raw_sample_size) is None


def test_normalize_sample_size_keeps_positive_integer() -> None:
    assert _normalize_sample_size(50) == 50
