from __future__ import annotations

import numpy as np

from scripts.benchmark_pd_set_prediction import (
    _build_output_paths,
    _promotion_gate,
    _set_benchmark_settings,
)


def test_build_output_paths_uses_namespaced_shadow_locations() -> None:
    paths = _build_output_paths("set/audit")

    assert (
        paths["cases"]
        .as_posix()
        .endswith("data/processed/conformal_gap/set_audit/pd_set_prediction_cases.parquet")
    )
    assert (
        paths["status"]
        .as_posix()
        .endswith("models/conformal_gap/set_audit/pd_set_prediction_status.json")
    )


def test_set_benchmark_settings_normalizes_inputs_and_fallback() -> None:
    settings = _set_benchmark_settings(
        alpha=0.1,
        method="lac",
        methods=("lac", "aps", "lac"),
        partitions=("global", "global", "grade"),
        partition_probability_source="RAW",
        n_score_bins=10,
        min_group_size=500,
        fallback_mode="score_only",
        calibration_size_fractions=(0.25, 1.5, 0.50),
        prob_cal_lookup={"raw": np.array([0.1]), "calibrated": np.array([0.2])},
    )

    assert settings.methods == ("lac", "aps")
    assert settings.partitions == ("global", "grade")
    assert settings.partition_probability_source == "raw"
    assert settings.effective_fallback_mode == "global_only"
    assert settings.calibration_size_fractions == (0.25, 0.50)


def test_promotion_gate_requires_coverage_grade_a_and_breadth() -> None:
    gate = _promotion_gate(
        {"set_coverage": 0.90},
        [
            {"slice_value": "A", "singleton_rate": 0.81},
            {"slice_value": "B", "singleton_rate": 0.41},
            {"slice_value": "C", "singleton_rate": 0.42},
            {"slice_value": "D", "singleton_rate": 0.43},
        ],
    )

    assert gate["pass"] is True
    assert gate["grade_a_singleton_rate"] == 0.81
    assert gate["grades_with_singleton_above_40pct"] == 4
