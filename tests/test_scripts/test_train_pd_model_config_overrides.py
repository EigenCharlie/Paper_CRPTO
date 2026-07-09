from __future__ import annotations

import json
import sys
import types

import numpy as np
import pytest

import scripts.train_pd_model as pd_train
from scripts.train_pd_model import (
    _apply_cli_overrides,
    _apply_pd_replay_manifest,
    _gate_tier,
    _load_training_splits,
    _normalize_sample_size,
    _prepare_training_inputs,
    _replay_selection_policy,
    _sample_training_splits,
    _select_calibration_from_backtest,
    _summarize_replayed_trials,
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


def test_select_calibration_from_backtest_uses_search_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_evaluate(
        method: str,
        y_true: np.ndarray,
        y_prob_raw: np.ndarray,
        splits: list[tuple[np.ndarray, np.ndarray]],
    ) -> dict[str, object]:
        calls.append(method)
        return {
            "method": method,
            "folds_used": 1,
            "mean_brier": 0.1 if method == "isotonic" else 0.2,
            "mean_log_loss": 0.3,
            "mean_ece": 0.01,
            "mean_auc_drop": 0.0,
            "brier_variance": 0.0,
            "ece_variance": 0.0,
            "stability": 0.0,
            "degradation_rate": 0.0,
            "folds": [{"n": len(y_true), "p": len(y_prob_raw), "splits": len(splits)}],
        }

    monkeypatch.setattr(pd_train, "_evaluate_calibration_method", fake_evaluate)

    selected, report, reports = _select_calibration_from_backtest(
        run_mode="search",
        replay_cfg={},
        cal_cfg={"candidates": ["platt", "isotonic"]},
        y_cal=np.array([0.0, 1.0, 0.0, 1.0]),
        y_prob_tuned_cal=np.array([0.2, 0.8, 0.3, 0.7]),
        cal_splits=[(np.array([0, 1]), np.array([2, 3]))],
    )

    assert calls == ["platt", "isotonic"]
    assert selected == "isotonic"
    assert report["selection_reason"] == "feasible_multi_metric"
    assert [row["method"] for row in reports] == ["platt", "isotonic"]


def test_select_calibration_from_backtest_keeps_replay_method_on_diagnostic_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_evaluate(*args, **kwargs):
        raise RuntimeError("diagnostic fold failed")

    monkeypatch.setattr(pd_train, "_evaluate_calibration_method", fake_evaluate)

    selected, report, reports = _select_calibration_from_backtest(
        run_mode="replay",
        replay_cfg={"selected_calibration_method": "venn_abers"},
        cal_cfg={"candidates": ["platt", "isotonic"]},
        y_cal=np.array([0.0, 1.0]),
        y_prob_tuned_cal=np.array([0.25, 0.75]),
        cal_splits=[],
    )

    assert selected == "venn_abers"
    assert report["selection_reason"] == "frozen_replay_manifest"
    assert report["feasible_candidates"] == reports
    assert reports[0]["method"] == "venn_abers"
    assert reports[0]["error"] == "diagnostic fold failed"


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

    (
        feature_source,
        feature_config_path,
        catboost_features,
        logreg_features,
        categorical_features,
        stable_core_meta,
    ) = pd_train._resolve_training_features(
        config={
            "feature_source": {"mode": "auto", "feature_config_path": "feature_config.yml"},
            "stable_core": {"enabled": True, "exclude_features": ["rev_utilization"]},
        },
        train=train,
        cal=cal,
        test=test,
        run_mode="search",
        replay_cfg={},
    )

    assert feature_source == "fixture"
    assert feature_config_path == "feature_config.yml"
    assert catboost_features == ["a", "b"]
    assert logreg_features == ["a", "b"]
    assert categorical_features == ["b"]
    assert stable_core_meta["enabled"] is True

    (
        _replay_feature_source,
        _replay_feature_config_path,
        replay_catboost_features,
        replay_logreg_features,
        replay_categorical_features,
        replay_stable_core_meta,
    ) = pd_train._resolve_training_features(
        config={
            "feature_source": {"mode": "auto", "feature_config_path": "feature_config.yml"},
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

    assert replay_catboost_features == ["a", "rev_utilization"]
    assert replay_logreg_features == ["a", "rev_utilization"]
    assert replay_categorical_features == ["rev_utilization"]
    assert replay_stable_core_meta == {"enabled": False, "excluded_features": []}


def test_replay_trial_summary_prioritizes_gate_then_ece_then_auc() -> None:
    rows = [
        {
            "trial_number": 1,
            "validation_auc": 0.80,
            "validation_brier": 0.20,
            "validation_ece": 0.05,
            "gate_attrs_present": True,
            "gate_all_pass": False,
        },
        {
            "trial_number": 2,
            "validation_auc": 0.79,
            "validation_brier": 0.21,
            "validation_ece": 0.06,
            "gate_attrs_present": True,
            "gate_all_pass": True,
        },
        {
            "trial_number": 3,
            "validation_auc": 0.90,
            "validation_brier": 0.19,
            "validation_ece": 0.01,
            "gate_attrs_present": False,
            "gate_all_pass": None,
        },
    ]

    summary = _summarize_replayed_trials(rows, prioritize_gate_pass=True)

    assert summary["trial_number"].tolist() == [2, 3, 1]
    assert summary["gate_tier"].tolist() == [0, 1, 2]
    assert _gate_tier(True, prioritize_gate_pass=True) == 0
    assert _gate_tier(None, prioritize_gate_pass=True) == 1
    assert _gate_tier(False, prioritize_gate_pass=True) == 2
    assert _gate_tier(False, prioritize_gate_pass=False) == 1
    assert _replay_selection_policy(True)["rank_order"][0] == "gate_tier(pass->unknown->fail)"


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

    train_split, cal_split, test_split = _load_training_splits(
        {
            "train_path": "train.parquet",
            "test_path": "test.parquet",
            "calibration_path": "calibration.parquet",
        }
    )

    assert calls == ["train.parquet", "test.parquet", "calibration.parquet"]
    assert train_split.to_dict(orient="records") == [
        {"source": "train.parquet", "normalized": True}
    ]
    assert test_split.to_dict(orient="records") == [{"source": "test.parquet", "normalized": True}]
    assert cal_split.to_dict(orient="records") == [
        {"source": "calibration.parquet", "normalized": True}
    ]


def test_sample_training_splits_is_deterministic_and_keeps_small_splits() -> None:
    train = pd_train.pd.DataFrame({"row": range(10)})
    cal = pd_train.pd.DataFrame({"row": range(10, 20)})
    test = pd_train.pd.DataFrame({"row": [100, 101]})

    sampled_train, sampled_cal, sampled_test = _sample_training_splits((train, cal, test), 3)

    assert sampled_train["row"].tolist() == train.sample(n=3, random_state=42)["row"].tolist()
    assert sampled_cal["row"].tolist() == cal.sample(n=3, random_state=42)["row"].tolist()
    assert sampled_test.equals(test)
    assert sampled_train.index.tolist() == [0, 1, 2]
    assert sampled_cal.index.tolist() == [0, 1, 2]


@pytest.mark.parametrize("raw_sample_size", [None, 0, -5])
def test_normalize_sample_size_treats_non_positive_as_full_data(
    raw_sample_size: int | None,
) -> None:
    assert _normalize_sample_size(raw_sample_size) is None


def test_normalize_sample_size_keeps_positive_integer() -> None:
    assert _normalize_sample_size(50) == 50


def test_prepare_training_inputs_builds_model_ready_frames() -> None:
    train = pd_train.pd.DataFrame(
        {
            "issue_d": pd_train.pd.date_range("2018-01-01", periods=10, freq="MS"),
            "default_flag": [0, 1] * 5,
            "score": [0.1, 0.2, None, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            "grade": ["A", "B", None, "C", "A", "B", "C", "A", "B", "C"],
            "_recency_weight": [1.0 + i for i in range(10)],
        }
    )
    cal = pd_train.pd.DataFrame(
        {
            "issue_d": pd_train.pd.date_range("2019-01-01", periods=2, freq="MS"),
            "default_flag": [0, 1],
            "score": [0.3, 0.4],
            "grade": ["A", "C"],
        }
    )
    test = pd_train.pd.DataFrame(
        {
            "issue_d": pd_train.pd.date_range("2020-01-01", periods=2, freq="MS"),
            "default_flag": [1, 0],
            "score": [None, 0.9],
            "grade": ["B", None],
        }
    )

    (
        train_val,
        train_fit_weights,
        train_val_weights,
        y_train_fit,
        _y_val,
        y_cal,
        y_test,
        x_train_fit_cb,
        _x_val_cb,
        _x_cal_cb,
        x_test_cb,
        x_train_fit_lr,
        x_test_lr,
        lr_fill,
    ) = _prepare_training_inputs(
        train,
        cal,
        test,
        catboost_features=["score", "grade"],
        categorical_features=["grade"],
        logreg_features=["score"],
        val_fraction=0.2,
    )

    assert len(x_train_fit_cb) == 8
    assert len(train_val) == 2
    assert train_fit_weights.tolist() == [1.0 + i for i in range(8)]
    assert train_val_weights.tolist() == [9.0, 10.0]
    assert pd_train.pd.api.types.is_integer_dtype(y_train_fit)
    assert y_cal.tolist() == [0, 1]
    assert y_test.tolist() == [1, 0]
    assert x_train_fit_cb.columns.tolist() == ["score", "grade"]
    assert x_test_cb["grade"].tolist() == ["B", "UNKNOWN"]
    assert x_test_lr.isna().sum().sum() == 0
    assert lr_fill["score"] == x_train_fit_lr["score"].median()


def test_evaluate_walk_forward_stage_reports_disabled_without_training(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("walk-forward evaluator should not run when disabled")

    monkeypatch.setattr(pd_train, "_evaluate_walk_forward_auc", fail_if_called)

    report = pd_train._evaluate_walk_forward_stage(
        enabled=False,
        walk_cfg={"n_windows": 5},
        train=pd_train.pd.DataFrame(),
        catboost_features=[],
        categorical_features=[],
        model_params={},
    )

    assert report == {
        "enabled": False,
        "reason": "disabled_in_config",
        "n_windows_requested": 5,
        "n_windows_used": 0,
        "folds": [],
    }


def test_evaluate_walk_forward_stage_normalizes_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_evaluate(train_df: pd_train.pd.DataFrame, **kwargs):
        captured["train_rows"] = len(train_df)
        captured.update(kwargs)
        return {"enabled": True, "n_windows_used": 1}

    monkeypatch.setattr(pd_train, "_evaluate_walk_forward_auc", fake_evaluate)

    report = pd_train._evaluate_walk_forward_stage(
        enabled=True,
        walk_cfg={
            "n_windows": "4",
            "min_train_rows": "12",
            "window_rows": "6",
            "date_col": "issue_d",
            "max_rows": "0",
        },
        train=pd_train.pd.DataFrame({"x": [1, 2]}),
        catboost_features=["x"],
        categorical_features=[],
        model_params={"depth": 4},
    )

    assert report == {"enabled": True, "n_windows_used": 1}
    assert captured["features"] == ["x"]
    assert captured["target"] == pd_train.TARGET
    assert captured["params"] == {"depth": 4}
    assert captured["n_windows"] == 4
    assert captured["min_train_rows"] == 12
    assert captured["window_rows"] == 6
    assert captured["max_rows"] is None


def test_export_shap_feature_importance_writes_summary(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_catboost = types.ModuleType("catboost")

    class FakePool:
        def __init__(self, frame, cat_features):
            self.frame = frame
            self.cat_features = cat_features

    fake_catboost.Pool = FakePool
    monkeypatch.setitem(sys.modules, "catboost", fake_catboost)

    class FakeModel:
        def get_feature_importance(self, *, type: str, data: FakePool):
            assert type == "ShapValues"
            assert data.cat_features == ["grade"]
            return np.array([[0.1, 0.4, 0.5], [0.3, -0.2, 0.5]])

    shap_dir = tmp_path / "shap"
    result = pd_train._export_shap_feature_importance(
        cb_tuned_model=FakeModel(),
        X_test_cb=pd_train.pd.DataFrame({"score": [1.0, 2.0], "grade": ["A", "B"]}),
        categorical_features=["grade"],
        catboost_features=["score", "grade"],
        shap_dir=shap_dir,
    )

    summary = json.loads((shap_dir / "shap_feature_importance.json").read_text(encoding="utf-8"))
    assert result == {"exported": True, "n_features": 2, "path": str(shap_dir)}
    assert (shap_dir / "shap_values_test.npz").exists()
    assert summary["expected_value"] == 0.5
    assert summary["top_features"][0]["feature"] == "grade"
