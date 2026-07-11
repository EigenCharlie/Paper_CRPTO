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

    assert cfg["version"] == "2026-07-10"
    assert cfg["decision_status"] == "reconstructed_active"
    assert primary["id"] == "informs_ijds"
    assert cfg["current_decision"]["write_first_for"] == "informs_ijds"
    assert cfg["current_decision"]["keep_second_ready_for"] == "ejor"
    for key in ("manuscript_source", "supplement_source", "official_tex_source"):
        assert Path(primary[key]).is_file()
    assert Path(active["claim_registry"]).is_file()
    assert Path(active["evidence_manifest"]).is_file()
    assert Path(active["parent_evidence_manifest"]).is_file()


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
    assert "Carlos Alfredo Vergara Rojas" not in tex


def test_active_contract_is_small_complete_and_numerically_locked() -> None:
    active = _config()["active_scientific_contract"]
    assert active["parent_run_tag"].endswith("maturity-safe-locked-bounded-h1h2-v2")
    assert active["run_tag"].endswith("comparator-stringency-audit-v1")
    assert active["posthoc_diagnostic_after_parent_results"] is True
    assert active["method"]["policy"] == "q=0.75p+0.25u with tau=0.17."
    assert "0.06831339893217318" in active["method"]["comparator"]
    assert active["headline"]["candidate_coverage"] == pytest.approx([0.854923, 0.879692])
    matched = active["headline"]["development_matched"]
    assert matched["payoff_difference"] == pytest.approx([-506587.03, -295967.17])
    assert matched["default_difference"] == pytest.approx([0.034431, 0.056287])
    assert matched["miscoverage_difference"] == pytest.approx([0.027093, 0.046283])
    assert active["headline"]["family_all_three_guardrail_worse"] == 7
    assert active["headline"]["family_pairs"] == 9
    assert len(active["required_artifacts"]) == 18
    for artifact in active["required_artifacts"]:
        assert Path(artifact).is_file(), artifact


def test_historical_diagnostics_are_explicitly_outside_active_evidence() -> None:
    historical = _config()["historical_boundary"]
    assert historical["compact_v7_status"] == "frozen_no_go_provenance"
    assert historical["diagnostics_status"] == "historical_not_active_evidence"
    text = " ".join(historical["diagnostics"])
    assert "A1--A24" in text
    assert "A25--A34" in text
    assert "A35--A40" in text
    assert "cannot validate" in historical["rule"]
