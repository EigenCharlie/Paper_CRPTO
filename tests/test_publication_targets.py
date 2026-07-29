from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

from scripts.build_ijds_binary_geometry_frontier_v4_evidence import FIGURE_STEMS, TABLE_TARGETS
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
    assert primary["constraints"]["prefreeze_page_limit"] is None
    assert primary["constraints"]["final_freeze_pre_reference_page_limit"] == 25
    assert primary["constraints"]["page_limit_excludes"] == ["references"]
    assert "initial_submission_pages" not in primary["constraints"]
    assert cfg["current_decision"]["write_first_for"] == "informs_ijds"
    assert cfg["current_decision"]["keep_second_ready_for"] == "ejor"
    for key in (
        "manuscript_source",
        "supplement_source",
        "machine_readable_supplement",
        "official_tex_source",
    ):
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
    assert lineages["binary_geometry"]["evaluation"]["run_tag"].endswith("2026-07-15-v5")
    assert lineages["two_ruler"]["outcome_free"]["run_tag"].endswith("2026-07-13-v1c")
    assert lineages["two_ruler"]["evaluation"]["run_tag"].endswith("2026-07-15-v5")
    assert lineages["credit_controls"]["outcome_free"]["run_tag"].endswith("2026-07-13-v1b")
    assert lineages["credit_controls"]["evaluation"]["run_tag"].endswith("2026-07-15-v5")
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
    assert evidence["portfolio"]["registered_cap_values_all_envelopes_include_zero"] is True


def test_active_capsule_paths_exist() -> None:
    active = _config()["active_scientific_contract"]
    registry = _registry()
    evidence = _evidence()
    support_artifacts = {
        "reports/crpto/ijds_policy_support_tie_evidence.json",
        "reports/crpto/ijds_policy_support_optimal_face_evidence.json",
        "reports/crpto/tables/crpto_ijds_comparator_support_domain.csv",
        "reports/crpto/tables/crpto_ijds_gamma_endpoint_audit.csv",
        "reports/crpto/tables/crpto_ijds_policy_family_domain.csv",
    }
    expected_artifacts = {
        active["evidence_manifest"],
        *(descriptor["path"] for descriptor in evidence["paper_artifacts"].values()),
        *support_artifacts,
    }
    paper_artifact_paths = {
        descriptor["path"] for descriptor in evidence["paper_artifacts"].values()
    }
    expected_artifact_count = len(TABLE_TARGETS) + 2 * len(FIGURE_STEMS)
    assert len(paper_artifact_paths) == expected_artifact_count
    assert len({path for path in paper_artifact_paths if path.endswith(".csv")}) == len(
        TABLE_TARGETS
    )
    assert len(
        {path for path in paper_artifact_paths if path.endswith((".pdf", ".png"))}
    ) == 2 * len(FIGURE_STEMS)
    assert len(registry["dvc_pointers"]) == 53
    assert (
        "reports/crpto/tables/crpto_ijds_v4_tableS7D_individual_age_endpoint_census.csv"
        in active["required_artifacts"]
    )
    assert (
        "reports/crpto/tables/crpto_ijds_v4_tableS7D_equal_followup_census.csv"
        not in active["required_artifacts"]
    )
    assert set(active["required_artifacts"]) == expected_artifacts
    for artifact in active["required_artifacts"]:
        assert Path(artifact).is_file(), artifact
    for pointer in registry["dvc_pointers"]:
        assert Path(pointer).is_file(), pointer

    code_surface = active["active_code_surface"]
    assert code_surface["historical_execution_in_active_capsule"] is False
    for path in code_surface["source_roots"]:
        assert Path(path).is_dir(), path
    for group in ("paper_pipeline", "protocol_entrypoints", "support_tools"):
        for path in code_surface[group]:
            assert Path(path).is_file(), path
    assert {
        "scripts/experiments/run_ijds_exchangeability_transport_test.py",
        "scripts/experiments/run_ijds_common_panel_threshold_response_v8.py",
        "scripts/experiments/run_ijds_rolling_origin_equal_followup.py",
        "scripts/experiments/run_ijds_rolling_origin_individual_age_followup.py",
        "scripts/experiments/run_ijds_label_mondrian_freeze.py",
        "scripts/experiments/run_ijds_label_mondrian_evaluation.py",
        "scripts/experiments/run_ijds_policy_support_optimal_face_v2.py",
        "scripts/experiments/run_ijds_policy_support_rhs_semantics_recovery_v3a.py",
    }.issubset(code_surface["protocol_entrypoints"])


def test_hash_bound_candidate_replays_cannot_leak_into_active_surfaces() -> None:
    config = _config()
    active = config["active_scientific_contract"]
    quarantine = config["executed_quarantine_capsule"]
    stopped = config["stopped_tagged_candidate_capsule"]
    # Structural loading is sufficient here: the registry's protocol-tag and
    # DVC replay checks are covered separately, and this quarantine test must
    # also run in constrained Windows runtimes without inheritable git handles.
    registry = load_source_registry(REGISTRY_PATH)

    for capsule in (quarantine, stopped):
        assert capsule["active_paper_evidence_allowed"] is False
        assert capsule["active_claim_support_allowed"] is False
        assert capsule["machine_readable_supplement_allowed"] is False
        assert capsule["dvc_pointer_count_change_allowed"] is False
        assert set(capsule["replay_entrypoints"]).isdisjoint(
            active["active_code_surface"]["protocol_entrypoints"]
        )
    assert set(quarantine["replay_entrypoints"]).isdisjoint(stopped["replay_entrypoints"])
    assert set(quarantine["local_candidate_artifacts_not_required"]).isdisjoint(
        active["required_artifacts"]
    )
    assert set(quarantine["forbidden_active_paper_artifacts_until_promotion"]).isdisjoint(
        active["required_artifacts"]
    )
    assert len(registry["dvc_pointers"]) == 53

    for group in (
        "replay_entrypoints",
        "protocols",
        "configs",
        "implementations",
        "receipt_indexes",
    ):
        for path in quarantine[group]:
            assert Path(path).is_file(), path
    for group in ("replay_entrypoints", "protocols", "configs", "implementations"):
        for path in stopped[group]:
            assert Path(path).is_file(), path

    manuscript_text = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in ("paper/CRPTO_ijds.qmd", "paper/supplement_ijds.qmd")
    )
    forbidden_run_tags = {
        *quarantine["quarantined_run_scope"],
        *stopped["forbidden_run_tags_in_manuscript"],
    }
    for run_tag in forbidden_run_tags:
        assert run_tag not in manuscript_text


def test_superseded_v7_runner_is_classified_but_cannot_support_active_evidence() -> None:
    config = _config()
    active = set(
        config["active_scientific_contract"]["active_code_surface"]["protocol_entrypoints"]
    )
    quarantine = set(config["executed_quarantine_capsule"]["replay_entrypoints"])
    stopped = set(config["stopped_tagged_candidate_capsule"]["replay_entrypoints"])
    superseded = config["superseded_protocol_capsule"]

    assert superseded["active_paper_evidence_allowed"] is False
    assert superseded["active_claim_support_allowed"] is False
    assert set(superseded["protocol_entrypoints"]).isdisjoint(active | quarantine | stopped)
    for group in ("protocol_entrypoints", "protocols", "configs"):
        for path in superseded[group]:
            assert Path(path).is_file(), path


def test_reviewer_zip_is_tracked() -> None:
    config = _config()
    reviewer_zip = config["primary_target"]["machine_readable_supplement"]
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", reviewer_zip],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert tracked.returncode == 0, (
        f"reviewer ZIP must be committed, not merely present: {reviewer_zip}"
    )


def test_quarantined_publication_aliases_are_absent() -> None:
    config = _config()
    forbidden = config["executed_quarantine_capsule"][
        "forbidden_active_paper_artifacts_until_promotion"
    ]
    present = [path for path in forbidden if (ROOT / path).exists()]

    assert not present, f"quarantined publication aliases exist: {present}"


def test_active_capsule_does_not_advertise_retired_result_families() -> None:
    config = _config()
    assert "historical_boundary" not in config
    serialized = json.dumps(config).lower()
    assert "pool93" not in serialized
    assert "compact-v7" not in serialized
    assert "a1--a40" not in serialized
