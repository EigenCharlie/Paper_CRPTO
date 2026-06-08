"""Tests for scripts/benchmark_conformal_variants.py."""

from __future__ import annotations

from scripts.benchmark_conformal_variants import _build_output_paths


def test_build_output_paths_uses_namespaced_shadow_locations() -> None:
    paths = _build_output_paths("abc/def")

    assert paths["data_dir"].as_posix().endswith("data/processed/conformal_gap/abc_def")
    assert paths["models_dir"].as_posix().endswith("models/conformal_gap/abc_def")
    assert (
        paths["selection_status"]
        .as_posix()
        .endswith("models/conformal_gap/abc_def/conformal_variant_selection_status.json")
    )
