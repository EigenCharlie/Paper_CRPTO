from __future__ import annotations

import json
from pathlib import Path

import yaml

from src.ijds_audit.publication_sources import load_source_registry

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "configs/ijds_active_evidence_sources.yaml"


def _config() -> dict:
    return yaml.safe_load(
        Path("configs/crpto_publication_targets.yaml").read_text(encoding="utf-8")
    )


def _evidence() -> dict:
    return json.loads(
        Path("reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json").read_text(
            encoding="utf-8"
        )
    )


def _registry() -> dict:
    return load_source_registry(REGISTRY_PATH, repo_root=ROOT)


def test_publication_target_points_to_active_sources() -> None:
    cfg = _config()
    primary = cfg["primary_target"]
    active = cfg["active_scientific_contract"]
    registry = _registry()

    assert cfg["version"] == str(registry["schema_version"]).rsplit(".", maxsplit=1)[0]
    assert cfg["decision_status"] == "prefreeze_active"
    assert primary["id"] == "informs_ijds"
    assert cfg["current_decision"]["write_first_for"] == "informs_ijds"
    assert cfg["current_decision"]["keep_second_ready_for"] == "ejor"
    for key in ("manuscript_source", "supplement_source", "official_tex_source"):
        assert Path(primary[key]).is_file()
    for key in ("claim_registry", "source_registry", "evidence_manifest"):
        assert Path(active[key]).is_file()


def test_publication_target_urls_are_official_https() -> None:
    urls = _config()["primary_target"]["official_urls"]
    assert urls
    assert all(url.startswith("https://") for url in urls.values())


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
    for path in (
        Path("paper/submission/TITLE_PAGE_DRAFT.md"),
        Path("paper/submission/COVER_LETTER_AND_DISCLOSURE.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert "Carlos Alfredo Vergara Rojas" not in text
        assert "cavr94@gmail.com" not in text


def test_active_contract_has_one_numeric_source_and_current_lineages() -> None:
    active = _config()["active_scientific_contract"]
    evidence = _evidence()
    registry = _registry()

    assert "headline" not in active
    assert active["lineage_and_dvc_authority"] == active["source_registry"]
    assert not {
        "outcome_free_run_tag",
        "run_tag",
        "two_ruler_outcome_free_run_tag",
        "two_ruler_run_tag",
        "credit_control_outcome_free_run_tag",
        "credit_control_run_tag",
        "dvc_pointers",
    }.intersection(active)
    lineages = registry["lineages"]
    assert lineages["binary_geometry"]["outcome_free"]["run_tag"].endswith("2026-07-12-v1")
    assert lineages["binary_geometry"]["evaluation"]["run_tag"].endswith("2026-07-14-v3")
    assert lineages["two_ruler"]["outcome_free"]["run_tag"].endswith("2026-07-13-v1c")
    assert lineages["two_ruler"]["evaluation"]["run_tag"].endswith("2026-07-14-v3")
    assert lineages["credit_controls"]["outcome_free"]["run_tag"].endswith("2026-07-13-v1b")
    assert lineages["credit_controls"]["evaluation"]["run_tag"].endswith("2026-07-14-v3")
    assert evidence["lineages"] == lineages
    assert active["previously_inspected_retrospective_archive"] is True
    assert active["archive_is_verified_point_in_time_snapshot"] is False
    assert active["confirmatory"] is False
    assert active["prospective"] is False
    assert active["causal"] is False
    assert active["policy_winner_allowed"] is False

    assert evidence["design"]["primary_oot_candidates"] == 376890
    assert evidence["design"]["primary_oot_resolved"] == 364814
    assert evidence["design"]["primary_oot_unresolved"] == 12076
    assert evidence["design"]["archive_is_verified_point_in_time_snapshot"] is False
    assert evidence["coverage"]["catboost_bound_max"] < 0.90
    assert evidence["coverage"]["logistic_bound_max"] < 0.90
    assert evidence["credit_risk_controls"]["all_five_all_eight_upper_below_nominal"] is True
    assert evidence["decision_challenger"]["counts"]["evaluated_portfolios"] == 6240
    assert evidence["decision_challenger"]["interpretation"]["policy_winner"] is None
    assert evidence["portfolio"]["broad_stress_cells"] == 216
    assert evidence["portfolio"]["broad_stress_all_envelopes_cross_zero"] is True


def test_active_capsule_paths_exist() -> None:
    active = _config()["active_scientific_contract"]
    registry = _registry()
    evidence = _evidence()
    expected_artifacts = {
        active["evidence_manifest"],
        *(descriptor["path"] for descriptor in evidence["paper_artifacts"].values()),
    }
    assert set(active["required_artifacts"]) == expected_artifacts
    for artifact in active["required_artifacts"]:
        assert Path(artifact).is_file(), artifact
    for pointer in registry["dvc_pointers"]:
        assert Path(pointer).is_file(), pointer

    code_surface = active["active_code_surface"]
    assert code_surface["historical_execution_in_active_capsule"] is False
    for group in ("paper_pipeline", "protocol_entrypoints"):
        for path in code_surface[group]:
            assert Path(path).is_file(), path


def test_historical_diagnostics_are_explicitly_outside_active_evidence() -> None:
    historical = _config()["historical_boundary"]
    assert historical["compact_v7_status"] == "git_history_only"
    assert historical["diagnostics_status"] == "git_history_only"
    text = " ".join(historical["diagnostics"])
    assert "A1--A24" in text
    assert "A25--A34" in text
    assert "A35--A40" in text
    assert "cannot validate" in historical["rule"]
