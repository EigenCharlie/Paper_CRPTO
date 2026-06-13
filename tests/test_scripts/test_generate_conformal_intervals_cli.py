from __future__ import annotations

import pytest

import scripts.generate_conformal_intervals as conformal_script
from scripts.generate_conformal_intervals import (
    _build_tuning_split,
    _parse_bool_tuple,
    _parse_float_tuple,
    _parse_int_tuple,
    _parse_str_tuple,
    _resolve_tuning_grid,
    _select_best_tuning_config,
)


def test_conformal_cli_tuple_parsers_strip_and_cast_values() -> None:
    assert _parse_float_tuple("0.1, 0.05") == (0.1, 0.05)
    assert _parse_int_tuple("5, 10") == (5, 10)
    assert _parse_bool_tuple("true,false,1,0,yes,no,y,n") == (
        True,
        False,
        True,
        False,
        True,
        False,
        True,
        False,
    )
    assert _parse_str_tuple("raw, calibrated ") == ("raw", "calibrated")


@pytest.mark.parametrize(
    "parser",
    [_parse_float_tuple, _parse_int_tuple, _parse_bool_tuple, _parse_str_tuple],
)
def test_conformal_cli_tuple_parsers_reject_empty_lists(parser) -> None:
    with pytest.raises(ValueError, match="Expected at least one"):
        parser(" , ")


def test_resolve_tuning_grid_normalizes_candidates() -> None:
    grid = _resolve_tuning_grid(
        partition="grade",
        partition_candidates=(" grade ", "grade", "score_bin"),
        partition_probability_sources=(" RAW ", "calibrated", "raw"),
        n_score_bins_candidates=(0, 5, 5),
        fallback_modes=(" Grade_Then_Global ", "global", "global"),
        score_scale_families=(" None ", "bernoulli_sqrt", "none"),
        scaled_scores_options=(True, False),
    )

    assert grid.partition_candidates == ("grade", "score_bin")
    assert grid.partition_probability_sources == ("raw", "calibrated")
    assert grid.n_score_bins_candidates == (5, 5)
    assert grid.fallback_modes == ("grade_then_global", "global")
    assert grid.score_scale_families == ("none", "bernoulli_sqrt")
    assert grid.scaled_scores_options == (True, False)


def test_resolve_tuning_grid_uses_current_defaults_for_empty_inputs() -> None:
    grid = _resolve_tuning_grid(
        partition="",
        partition_candidates=None,
        partition_probability_sources=(),
        n_score_bins_candidates=(0,),
        fallback_modes=(),
        score_scale_families=(),
        scaled_scores_options=(),
    )

    assert grid.partition_candidates == ("grade",)
    assert grid.partition_probability_sources == ("raw",)
    assert grid.n_score_bins_candidates == (10,)
    assert grid.fallback_modes == ("grade_then_global",)
    assert grid.score_scale_families == ("none",)
    assert grid.scaled_scores_options == ()


def test_build_tuning_split_materializes_fit_and_holdout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_split_calibration_for_tuning(**kwargs):
        return conformal_script.np.array([0, 2]), conformal_script.np.array([1, 3])

    monkeypatch.setattr(
        conformal_script,
        "split_calibration_for_tuning",
        fake_split_calibration_for_tuning,
    )
    cal_df = conformal_script.pd.DataFrame(
        {
            "issue_d": ["2020-01-01", "2020-02-01", "2020-03-01", "bad-date"],
            "feature": [10, 20, 30, 40],
        }
    )
    test_df = conformal_script.pd.DataFrame({"issue_d": ["2021-01-01", "not-a-date"]})
    x_cal = conformal_script.pd.DataFrame({"feature": [10, 20, 30, 40]})
    y_cal = conformal_script.pd.Series([0.0, 1.0, 0.0, 1.0])
    group_cal = conformal_script.pd.Series(["A", "B", "A", "C"])
    y_prob_raw = conformal_script.np.array([0.1, 0.2, 0.3, 0.4])

    split = _build_tuning_split(
        cal_df=cal_df,
        test_df=test_df,
        X_cal=x_cal,
        y_cal=y_cal,
        group_cal_base=group_cal,
        y_prob_cal_raw=y_prob_raw,
        tuning_holdout_ratio=0.5,
        tuning_random_state=7,
    )

    assert split.idx_cal_fit.tolist() == [0, 2]
    assert split.idx_cal_tune.tolist() == [1, 3]
    assert split.X_cal_fit["feature"].tolist() == [10, 30]
    assert split.X_tune["feature"].tolist() == [20, 40]
    assert split.y_cal_fit.tolist() == [0.0, 0.0]
    assert split.y_tune.tolist() == [1.0, 1.0]
    assert split.y_prob_cal_fit.tolist() == [0.1, 0.3]
    assert split.y_prob_cal_tune.tolist() == [0.2, 0.4]
    assert split.group_cal_fit_base.tolist() == ["A", "A"]
    assert split.group_tune_base.tolist() == ["B", "C"]
    assert split.issue_tune.isna().tolist() == [False, True]
    assert split.issue_test.isna().tolist() == [False, True]


def test_build_tuning_split_rejects_empty_holdout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_split_calibration_for_tuning(**kwargs):
        return conformal_script.np.array([0, 1]), conformal_script.np.array([], dtype=int)

    monkeypatch.setattr(
        conformal_script,
        "split_calibration_for_tuning",
        fake_split_calibration_for_tuning,
    )

    with pytest.raises(ValueError, match="holdout split is empty"):
        _build_tuning_split(
            cal_df=conformal_script.pd.DataFrame({"feature": [1, 2]}),
            test_df=conformal_script.pd.DataFrame({"feature": [3]}),
            X_cal=conformal_script.pd.DataFrame({"feature": [1, 2]}),
            y_cal=conformal_script.pd.Series([0.0, 1.0]),
            group_cal_base=conformal_script.pd.Series(["A", "B"]),
            y_prob_cal_raw=conformal_script.np.array([0.1, 0.2]),
            tuning_holdout_ratio=0.5,
            tuning_random_state=7,
        )


def test_select_best_tuning_config_materializes_promoted_config() -> None:
    rows = [
        {
            "partition": "grade",
            "partition_probability_source": "raw",
            "n_score_bins": 10,
            "fallback_mode": "grade_then_global",
            "alpha_used_90": 0.10,
            "scaled_scores": False,
            "score_scale_family": "none",
            "min_group_size": 200,
            "empirical_coverage": 0.902,
            "target_coverage": 0.9,
            "coverage_gap": 0.002,
            "avg_interval_width": 0.40,
            "median_interval_width": 0.38,
            "min_group_coverage": 0.901,
            "max_group_coverage": 0.93,
            "std_group_coverage": 0.01,
            "winkler_90": 0.30,
            "max_monthly_gap": 0.02,
            "stability_over_time": 0.98,
        },
        {
            "partition": "score_bin",
            "partition_probability_source": "calibrated",
            "n_score_bins": 5,
            "fallback_mode": "global",
            "alpha_used_90": 0.09,
            "scaled_scores": True,
            "score_scale_family": "bernoulli_sqrt",
            "min_group_size": 500,
            "empirical_coverage": 0.922,
            "target_coverage": 0.9,
            "coverage_gap": 0.022,
            "avg_interval_width": 0.35,
            "median_interval_width": 0.34,
            "min_group_coverage": 0.912,
            "max_group_coverage": 0.94,
            "std_group_coverage": 0.01,
            "winkler_90": 0.20,
            "max_monthly_gap": 0.01,
            "stability_over_time": 0.99,
        },
    ]

    selection = _select_best_tuning_config(
        rows,
        partition_candidates=("grade", "score_bin"),
        alpha_target_90=0.10,
        min_group_coverage_target=0.90,
        group_coverage_floor_target_90=0.92,
        coverage_guardband_90=0.015,
        min_group_guardband_90=0.0,
        max_width_budget_90=0.80,
        target_coverage_90=0.90,
    )

    assert {"is_pareto", "global_ok", "group_ok", "width_ok"}.issubset(selection.tuning_df.columns)
    assert selection.selection_tier == "strong_global+strong_group+width"
    assert selection.best_cfg == {
        "partition": "score_bin",
        "partition_candidates": ["grade", "score_bin"],
        "partition_probability_source": "calibrated",
        "n_score_bins": 5,
        "fallback_mode": "global",
        "alpha_target_90": 0.10,
        "alpha_used_90": 0.09,
        "scaled_scores": True,
        "score_scale_family": "bernoulli_sqrt",
        "min_group_size": 500,
        "min_group_coverage_target": 0.90,
        "group_coverage_floor_target_90": 0.92,
        "coverage_guardband_90": 0.015,
        "min_group_guardband_90": 0.0,
        "max_width_budget_90": 0.80,
        "selection_tier": "strong_global+strong_group+width",
    }
