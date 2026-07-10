"""Tests for scripts/benchmark_conformal_variants.py."""

from __future__ import annotations

from scripts.benchmark_conformal_variants import _build_output_paths, _normalize_search_space


def test_build_output_paths_uses_namespaced_shadow_locations() -> None:
    paths = _build_output_paths("abc/def")

    assert paths["data_dir"].as_posix().endswith("data/processed/conformal_gap/abc_def")
    assert paths["models_dir"].as_posix().endswith("models/conformal_gap/abc_def")
    assert (
        paths["selection_status"]
        .as_posix()
        .endswith("models/conformal_gap/abc_def/conformal_variant_selection_status.json")
    )


def test_normalize_search_space_dedupes_and_applies_defaults() -> None:
    space = _normalize_search_space(
        calibration_size_fractions=(0.25, 1.5, 0.5),
        partition_candidates=(" grade ", "grade", ""),
        partition_probability_sources=("RAW", "raw"),
        n_score_bins_candidates=(0, 10),
        fallback_modes=("", "Grade_Then_Global", "grade_then_global"),
        score_scale_families=("",),
        min_group_sizes=None,
        min_group_size_default=500,
    )

    assert space.partition_candidates == ("grade",)
    assert space.partition_probability_sources == ("raw",)
    assert space.n_score_bins_candidates == (10,)
    assert space.fallback_modes == ("grade_then_global",)
    assert space.score_scale_families == ("none",)
    assert space.min_group_sizes == (500,)
    assert space.calibration_size_fractions == (0.25, 0.5)
