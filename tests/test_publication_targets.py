from __future__ import annotations

from pathlib import Path

import pytest
import yaml


def _config() -> dict:
    return yaml.safe_load(
        Path("configs/crpto_publication_targets.yaml").read_text(encoding="utf-8")
    )


def test_publication_target_points_to_active_sources() -> None:
    cfg = _config()
    primary = cfg["primary_target"]
    active = cfg["active_scientific_contract"]

    assert cfg["version"] == "2026-07-12"
    assert cfg["decision_status"] == "reconstructed_active"
    assert primary["id"] == "informs_ijds"
    assert cfg["current_decision"]["write_first_for"] == "informs_ijds"
    assert cfg["current_decision"]["keep_second_ready_for"] == "ejor"
    for key in ("manuscript_source", "supplement_source", "official_tex_source"):
        assert Path(primary[key]).is_file()
    assert Path(active["claim_registry"]).is_file()
    assert Path(active["evidence_manifest"]).is_file()


def test_publication_target_urls_are_official_https() -> None:
    cfg = _config()
    targets = [cfg["primary_target"], *cfg["secondary_targets"]]
    for target in targets:
        for url in target["official_urls"].values():
            assert url.startswith("https://"), (target["id"], url)


def test_ijds_sources_are_anonymous_by_default() -> None:
    for path in (Path("paper/CRPTO_ijds.qmd"), Path("paper/supplement_ijds.qmd")):
        text = path.read_text(encoding="utf-8")
        assert 'author: "Anonymous"' in text
        assert "Carlos Alfredo Vergara Rojas" not in text
        assert "cavr94@gmail.com" not in text
    tex = Path("paper/submission/CRPTO_ijds_submission.tex").read_text(encoding="utf-8")
    assert r"\documentclass[ijds,dblanonrev]{informs4}" in tex
    assert r"\ACKNOWLEDGMENT" not in tex
    assert "Carlos Alfredo Vergara Rojas" not in tex
    title_template = Path("paper/submission/TITLE_PAGE_DRAFT.md").read_text(encoding="utf-8")
    assert "Carlos Alfredo Vergara Rojas" not in title_template
    assert "cavr94@gmail.com" not in title_template
    cover_template = Path("paper/submission/COVER_LETTER_AND_DISCLOSURE.md").read_text(
        encoding="utf-8"
    )
    assert "Carlos Alfredo Vergara Rojas" not in cover_template
    assert "cavr94@gmail.com" not in cover_template


def test_active_contract_is_small_complete_and_numerically_locked() -> None:
    active = _config()["active_scientific_contract"]
    assert active["outcome_free_run_tag"].endswith("2026-07-11-v1")
    assert active["run_tag"].endswith("2026-07-11-v2")
    assert active["temporal_run_tag"].endswith("temporal-v3-2026-07-12-v1")
    assert active["previously_inspected_retrospective_archive"] is True
    assert active["post_result_audit_framing"] is True
    assert active["prespecified_negative_fallback"] is False
    assert "all nine" in active["method"]["policies"].lower()
    assert "c2 matches" in active["method"]["comparator"].lower()
    assert active["headline"]["early_candidate_coverage"] == pytest.approx([0.854714, 0.879647])
    assert active["headline"]["late_candidate_coverage"] == pytest.approx([0.845072, 0.870973])
    assert active["headline"]["early_c2"] == {
        "payoff_worse": 7,
        "default_higher": 1,
        "miscoverage_higher": 8,
        "policy_pairs": 9,
    }
    assert active["headline"]["late_c2"] == {
        "payoff_worse": 5,
        "default_higher": 1,
        "miscoverage_higher": 8,
        "policy_pairs": 9,
    }
    assert active["headline"]["seed_purpose_cells_per_window"] == 180
    assert active["headline"]["seed_purpose_cells_total"] == 360
    assert active["headline"]["binding_guardrail_month_cells"] == 2025
    assert active["headline"]["terminal_endpoint_inventory"] == {
        "resolved": 499845,
        "unresolved": 40276,
    }
    assert active["headline"]["indeterminate_envelopes_per_scope"] == 27
    assert active["headline"]["total_scope_envelopes"] == 81
    assert active["headline"]["common_oot_point_rows"] == 465117
    assert active["headline"]["maximum_point_score_difference"] == 0.0
    assert active["headline"]["canonical_point_policy_cells"] == 570
    assert active["headline"]["maximum_point_exposure_difference"] == 0.0
    assert active["headline"]["universal_policy_direction_allowed"] is False
    assert len(active["required_artifacts"]) == 23
    for artifact in active["required_artifacts"]:
        assert Path(artifact).is_file(), artifact
    assert len(active["dvc_pointers"]) == 6
    for pointer in active["dvc_pointers"]:
        assert Path(pointer).is_file(), pointer


def test_historical_diagnostics_are_explicitly_outside_active_evidence() -> None:
    historical = _config()["historical_boundary"]
    assert historical["compact_v7_status"] == "git_history_only"
    assert historical["diagnostics_status"] == "git_history_only"
    text = " ".join(historical["diagnostics"])
    assert "A1--A24" in text
    assert "A25--A34" in text
    assert "A35--A40" in text
    assert "cannot validate" in historical["rule"]
