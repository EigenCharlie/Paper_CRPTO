"""Tests for the active evidence source registry."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.ijds_audit.publication_sources import (
    active_lineage_run_tags,
    load_source_registry,
    load_verified_source_registry,
)
from src.utils.artifact_descriptor import relative_artifact_descriptor

ROOT = Path(__file__).resolve().parents[2]

FREEZE_TAG = "binary-freeze-v1"
EVALUATION_TAG = "binary-evaluation-v2"
DIAGNOSTIC_TAG = "raw-data-audit-v1"
SENSITIVITY_TAG = "endpoint-sensitivity-v1"
DVC_ROOTS = ("data/processed", "models")


def _protocol_identity(
    run_tag: str,
    *,
    paper_role: str,
    dvc_tracked: bool,
    commit: str,
) -> dict[str, Any]:
    return {
        "run_tag": run_tag,
        "protocol_tag": f"protocol/{run_tag}",
        "protocol_commit": commit,
        "scientific_uv_lock_sha256": "a" * 64,
        "paper_role": paper_role,
        "dvc_tracked": dvc_tracked,
    }


def _explicit_payload(root: Path) -> dict[str, Any]:
    source = root / "evidence" / "source.json"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text('{"status": "fixture"}\n', encoding="utf-8")
    tracked_tags = (FREEZE_TAG, EVALUATION_TAG, SENSITIVITY_TAG)
    return {
        "schema_version": "test-explicit-v1",
        "status": "active_ijds_paper_evidence_source_registry",
        "lineages": {
            "binary_geometry": {
                "outcome_free": _protocol_identity(
                    FREEZE_TAG,
                    paper_role="outcome_free",
                    dvc_tracked=True,
                    commit="1" * 40,
                ),
                "evaluation": _protocol_identity(
                    EVALUATION_TAG,
                    paper_role="evaluation",
                    dvc_tracked=True,
                    commit="2" * 40,
                ),
            }
        },
        "diagnostics": {
            "raw_data_audit": {
                "run_tag": DIAGNOSTIC_TAG,
                "status": "complete_fixture_diagnostic",
                "paper_role": "diagnostic",
                "dvc_tracked": False,
            }
        },
        "sensitivities": {
            "endpoint_availability": _protocol_identity(
                SENSITIVITY_TAG,
                paper_role="assumption_sensitivity",
                dvc_tracked=True,
                commit="3" * 40,
            )
        },
        "dvc_pointers": [
            f"{prefix}/experiments/ijds_audit/{run_tag}.dvc"
            for run_tag in tracked_tags
            for prefix in DVC_ROOTS
        ],
        "sources": {
            "fixture": relative_artifact_descriptor(source, repo_root=root),
        },
    }


def _valid_pointer_payload(run_tag: str) -> dict[str, Any]:
    return {
        "outs": [
            {
                "md5": f"{'a' * 32}.dir",
                "size": 128,
                "nfiles": 2,
                "hash": "md5",
                "path": run_tag,
            }
        ]
    }


def _write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_registry(root: Path, payload: dict[str, Any]) -> Path:
    path = root / "configs" / "ijds_active_evidence_sources.yaml"
    _write_yaml(path, payload)
    return path


def _materialize_registry(root: Path, payload: dict[str, Any]) -> Path:
    for pointer in payload["dvc_pointers"]:
        pointer_path = root / pointer
        _write_yaml(pointer_path, _valid_pointer_payload(pointer_path.stem))
    return _write_registry(root, payload)


def _init_git(root: Path) -> None:
    subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)


def _transport_payload(root: Path, *, dvc_tracked: bool) -> dict[str, Any]:
    run_tag = "transport-fixture"
    if dvc_tracked:
        source = root / "models" / "experiments" / "ijds_audit" / run_tag / "evidence.json"
        pointers = [f"models/experiments/ijds_audit/{run_tag}.dvc"]
        dvc_roots = ["models"]
    else:
        source = root / "evidence" / "source.json"
        pointers = []
        dvc_roots = None
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text('{"status": "fixture"}\n', encoding="utf-8")
    identity: dict[str, Any] = {
        "run_tag": run_tag,
        "status": "complete_fixture",
        "paper_role": "transport_fixture",
        "dvc_tracked": dvc_tracked,
    }
    if dvc_roots is not None:
        identity["dvc_roots"] = dvc_roots
    return {
        "schema_version": "transport-fixture-v1",
        "status": "active_ijds_paper_evidence_source_registry",
        "lineages": {"fixture": identity},
        "dvc_pointers": pointers,
        "sources": {"fixture": relative_artifact_descriptor(source, repo_root=root)},
    }


def test_active_evidence_registry_verifies_every_source() -> None:
    payload, sources = load_verified_source_registry(
        ROOT / "configs/ijds_active_evidence_sources.yaml",
        repo_root=ROOT,
    )
    assert payload["schema_version"] == "2026-07-26.4"
    assert set(sources) == {
        "v4_config",
        "v4_summary",
        "v4_receipt",
        "two_ruler_manifest",
        "credit_summary",
        "credit_receipt",
        "raw_data_audit",
        "label_lag_sensitivity",
        "solver_tie_audit",
        "policy_support_optimal_face_evidence",
        "endpoint_sensitivity_summary",
        "structural_sensitivity_config",
        "structural_sensitivity_freeze",
        "structural_sensitivity_summary",
        "rolling_origin_summary",
        "rolling_origin_receipt",
        "rolling_origin_2017_v2_config",
        "rolling_origin_2017_v2_freeze",
        "rolling_origin_2017_v2_scores",
        "rolling_origin_2017_v2_residual_recipes",
        "rolling_origin_2017_v2_fit_audit",
        "rolling_primary_recovery_summary",
        "rolling_primary_recovery_receipt",
        "conformal_set_diagnostics_summary",
        "conformal_set_diagnostics_receipt",
        "exchangeability_transport_summary",
        "exchangeability_transport_config",
        "exchangeability_transport_receipt",
        "common_panel_threshold_response_config",
        "common_panel_threshold_response_summary",
        "common_panel_threshold_response_receipt",
        "common_panel_threshold_response_strata",
        "common_panel_threshold_response_learners",
        "rolling_equal_followup_summary",
        "rolling_equal_followup_config",
        "rolling_equal_followup_receipt",
        "rolling_individual_age_followup_summary",
        "rolling_individual_age_followup_config",
        "rolling_individual_age_followup_receipt",
        "label_mondrian_freeze",
        "label_mondrian_freeze_config",
        "label_mondrian_freeze_receipt",
        "label_mondrian_evaluation_summary",
        "label_mondrian_evaluation_config",
        "label_mondrian_evaluation_receipt",
        "missingness_summary",
        "missingness_receipt",
        "fit_label_completion_freeze",
        "fit_label_completion_summary",
        "allocation_granularity_freeze",
        "allocation_granularity_summary",
    }
    assert len(payload["dvc_pointers"]) == 53
    assert payload["lineages"]["binary_geometry"]["evaluation"]["run_tag"].endswith("2026-07-15-v5")
    assert payload["sensitivities"]["rolling_origin_individual_age_followup"]["paper_role"] == (
        "individual_issue_month_age_equalized_two_origin_retrospective_sensitivity"
    )
    common_panel = payload["lineages"]["diagnostics"]["common_panel_threshold_response"]
    assert common_panel["artifact_commit"] == "526a71bd0a0a7663a313dc12b0ce0eb3307719d9"
    assert common_panel["artifact_parent_commit"] == common_panel["protocol_commit"]
    assert len(common_panel["artifact_paths"]) == 4
    assert "protocol_bundle" not in common_panel
    assert (
        payload["replay_dependencies"]["rolling_origin_equal_followup_parent"]["paper_role"]
        == "non_primary_equal_quarter_level_minimum_followup_parent_provenance"
    )


def test_active_registry_returns_all_dvc_run_tags_in_causal_config_order() -> None:
    payload = load_source_registry(ROOT / "configs/ijds_active_evidence_sources.yaml")

    assert active_lineage_run_tags(payload) == (
        "ijds-binary-geometry-frontier-v4-2026-07-12-v1",
        "ijds-binary-geometry-frontier-v4-2026-07-15-v5",
        "ijds-normalized-objective-frontier-2026-07-13-v1c",
        "ijds-normalized-objective-frontier-2026-07-15-v5",
        "ijds-credit-risk-controls-2026-07-13-v1b",
        "ijds-credit-risk-controls-2026-07-15-v5",
        "ijds-policy-support-tie-audit-2026-07-12-v1",
        "ijds-policy-support-optimal-face-audit-2026-07-21-v2",
        "ijds-policy-support-rhs-semantics-recovery-2026-07-21-v3a",
        "ijds-conformal-set-diagnostics-2026-07-21-v1",
        "ijds-exchangeability-transport-test-2026-07-21-v1",
        "ijds-endpoint-availability-sensitivity-2026-07-14-v1",
        "ijds-portfolio-structure-sensitivity-2026-07-15-v6",
        "ijds-rolling-origin-individual-age-followup-2026-07-21-v1",
        "ijds-missingness-sensitivity-2026-07-15-v3",
        "ijds-fit-label-completion-sensitivity-2026-07-16-v2",
        "ijds-allocation-granularity-sensitivity-2026-07-16-v3",
        "ijds-label-mondrian-freeze-2026-07-21-v1",
        "ijds-label-mondrian-evaluation-2026-07-21-v1",
        "ijds-rolling-origin-2017-2026-07-12-v2",
        "ijds-rolling-origin-equal-followup-2026-07-21-v1",
        "ijds-rolling-origin-2017-2026-07-15-v4",
        "ijds-rolling-origin-primary-recovery-2026-07-21-v1",
        "ijds-binary-geometry-frontier-v4-2026-07-14-v3",
        "ijds-normalized-objective-frontier-2026-07-14-v3",
        "ijds-credit-risk-controls-2026-07-14-v3",
        "ijds-portfolio-structure-sensitivity-2026-07-15-v5",
    )


def test_verified_registry_requires_git_transport_for_non_dvc_source(tmp_path: Path) -> None:
    _init_git(tmp_path)
    payload = _transport_payload(tmp_path, dvc_tracked=False)
    registry_path = _write_registry(tmp_path, payload)

    with pytest.raises(RuntimeError, match="lack Git or active-DVC transport"):
        load_verified_source_registry(registry_path, repo_root=tmp_path)

    source = tmp_path / payload["sources"]["fixture"]["path"]
    subprocess.run(["git", "add", str(source)], cwd=tmp_path, check=True)
    loaded, verified = load_verified_source_registry(registry_path, repo_root=tmp_path)

    assert loaded["schema_version"] == "transport-fixture-v1"
    assert verified["fixture"] == source.resolve()


def test_verified_registry_accepts_source_inside_tracked_dvc_output(tmp_path: Path) -> None:
    _init_git(tmp_path)
    payload = _transport_payload(tmp_path, dvc_tracked=True)
    registry_path = _materialize_registry(tmp_path, payload)
    pointer = tmp_path / payload["dvc_pointers"][0]
    subprocess.run(["git", "add", str(pointer)], cwd=tmp_path, check=True)

    _, verified = load_verified_source_registry(registry_path, repo_root=tmp_path)

    assert verified["fixture"].is_file()


def test_verified_registry_rejects_untracked_active_dvc_pointer(tmp_path: Path) -> None:
    _init_git(tmp_path)
    payload = _transport_payload(tmp_path, dvc_tracked=True)
    registry_path = _materialize_registry(tmp_path, payload)

    with pytest.raises(RuntimeError, match="DVC pointers are not Git-tracked"):
        load_verified_source_registry(registry_path, repo_root=tmp_path)


def test_registry_verifies_exact_direct_child_git_artifact_commit(tmp_path: Path) -> None:
    _init_git(tmp_path)
    lock = b"version = 1\n"
    (tmp_path / "uv.lock").write_bytes(lock)
    subprocess.run(["git", "add", "uv.lock"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "protocol"], cwd=tmp_path, check=True)
    protocol_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    protocol_tag = "protocol/artifact-fixture"
    subprocess.run(["git", "tag", protocol_tag], cwd=tmp_path, check=True)

    artifact_path = tmp_path / "evidence" / "result.json"
    artifact_path.parent.mkdir()
    artifact_path.write_text('{"status": "complete"}\n', encoding="utf-8")
    receipt_path = tmp_path / "evidence" / "receipt.json"
    receipt_path.write_text('{"status": "verified"}\n', encoding="utf-8")
    subprocess.run(
        ["git", "add", "evidence/receipt.json", "evidence/result.json"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(["git", "commit", "--quiet", "-m", "artifact"], cwd=tmp_path, check=True)
    artifact_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    artifact_tag = "artifacts/artifact-fixture"
    subprocess.run(["git", "tag", artifact_tag], cwd=tmp_path, check=True)

    payload: dict[str, Any] = {
        "schema_version": "artifact-fixture-v1",
        "status": "active_ijds_paper_evidence_source_registry",
        "lineages": {
            "fixture": {
                "run_tag": "artifact-fixture",
                "protocol_tag": protocol_tag,
                "protocol_commit": protocol_commit,
                "scientific_uv_lock_sha256": hashlib.sha256(lock).hexdigest(),
                "paper_role": "git_artifact_fixture",
                "dvc_tracked": False,
                "artifact_tag": artifact_tag,
                "artifact_commit": artifact_commit,
                "artifact_parent_commit": protocol_commit,
                "artifact_transport": "git_force_tracked_direct_child_commit",
                "artifact_paths": ["evidence/receipt.json", "evidence/result.json"],
            }
        },
        "dvc_pointers": [],
        "sources": {
            "fixture": relative_artifact_descriptor(artifact_path, repo_root=tmp_path),
            "receipt": relative_artifact_descriptor(receipt_path, repo_root=tmp_path),
        },
    }
    registry_path = _write_registry(tmp_path, payload)

    loaded, _ = load_verified_source_registry(registry_path, repo_root=tmp_path)
    assert loaded["lineages"]["fixture"]["artifact_commit"] == artifact_commit

    payload["lineages"]["fixture"]["artifact_paths"] = ["evidence/other.json"]
    registry_path = _write_registry(tmp_path, payload)
    with pytest.raises(RuntimeError, match="declared exact artifact paths"):
        load_verified_source_registry(registry_path, repo_root=tmp_path)

    payload["lineages"]["fixture"]["artifact_paths"] = [
        "evidence/receipt.json",
        "evidence/result.json",
    ]
    del payload["sources"]["receipt"]
    registry_path = _write_registry(tmp_path, payload)
    with pytest.raises(RuntimeError, match="lack active hash descriptors"):
        load_verified_source_registry(registry_path, repo_root=tmp_path)


def test_registry_rejects_incomplete_git_artifact_contract(tmp_path: Path) -> None:
    payload = _explicit_payload(tmp_path)
    payload["lineages"]["binary_geometry"]["evaluation"]["artifact_tag"] = "artifacts/incomplete"
    registry_path = _write_registry(tmp_path, payload)

    with pytest.raises(TypeError, match="incomplete Git artifact contract"):
        load_source_registry(registry_path)


def test_tracked_unit_can_declare_one_dvc_root(tmp_path: Path) -> None:
    payload = _explicit_payload(tmp_path)
    run_tag = "data-only-replay-dependency"
    payload["replay_dependencies"] = {
        "fixture": {
            **_protocol_identity(
                run_tag,
                paper_role="non_evidence_replay_dependency",
                dvc_tracked=True,
                commit="4" * 40,
            ),
            "dvc_roots": ["data/processed"],
        }
    }
    pointer = f"data/processed/experiments/ijds_audit/{run_tag}.dvc"
    payload["dvc_pointers"].append(pointer)
    registry_path = _materialize_registry(tmp_path, payload)

    loaded = load_source_registry(registry_path, repo_root=tmp_path)

    assert active_lineage_run_tags(loaded)[-1] == run_tag


def test_registry_rejects_dvc_roots_on_untracked_unit(tmp_path: Path) -> None:
    payload = _explicit_payload(tmp_path)
    payload["diagnostics"]["raw_data_audit"]["dvc_roots"] = ["data/processed"]
    registry_path = _write_registry(tmp_path, payload)

    with pytest.raises(ValueError, match="requires dvc_tracked=true"):
        load_source_registry(registry_path)


def test_explicit_paper_roles_and_dvc_tracking_control_pointer_contract(tmp_path: Path) -> None:
    registry_path = _materialize_registry(tmp_path, _explicit_payload(tmp_path))

    payload = load_source_registry(registry_path, repo_root=tmp_path)

    assert payload["sensitivities"]["endpoint_availability"]["paper_role"] == (
        "assumption_sensitivity"
    )
    assert active_lineage_run_tags(payload) == (
        FREEZE_TAG,
        EVALUATION_TAG,
        SENSITIVITY_TAG,
    )


def test_registry_rejects_duplicate_run_tags_across_identity_sections(tmp_path: Path) -> None:
    payload = _explicit_payload(tmp_path)
    payload["diagnostics"]["raw_data_audit"]["run_tag"] = FREEZE_TAG
    registry_path = _write_registry(tmp_path, payload)

    with pytest.raises(ValueError, match="run tags must be globally unique"):
        load_source_registry(registry_path)


@pytest.mark.parametrize(
    ("section", "group", "unit"),
    [
        ("lineages", "binary_geometry", "outcome_free"),
        ("diagnostics", None, "raw_data_audit"),
        ("sensitivities", None, "endpoint_availability"),
    ],
)
def test_registry_rejects_missing_run_tag_in_every_identity_section(
    tmp_path: Path,
    section: str,
    group: str | None,
    unit: str,
) -> None:
    payload = _explicit_payload(tmp_path)
    section_payload = payload[section]
    identity = section_payload[group][unit] if group is not None else section_payload[unit]
    del identity["run_tag"]
    registry_path = _write_registry(tmp_path, payload)

    with pytest.raises(TypeError, match=r"Missing registry identity: .*run_tag"):
        load_source_registry(registry_path)


def test_registry_rejects_incomplete_protocol_identity(tmp_path: Path) -> None:
    payload = _explicit_payload(tmp_path)
    del payload["sensitivities"]["endpoint_availability"]["protocol_commit"]
    registry_path = _write_registry(tmp_path, payload)

    with pytest.raises(TypeError, match="protocol_commit"):
        load_source_registry(registry_path)


def test_registry_requires_scientific_lock_for_protocol_identity(tmp_path: Path) -> None:
    payload = _explicit_payload(tmp_path)
    del payload["sensitivities"]["endpoint_availability"]["scientific_uv_lock_sha256"]
    registry_path = _write_registry(tmp_path, payload)

    with pytest.raises(TypeError, match="scientific_uv_lock_sha256"):
        load_source_registry(registry_path)


def test_registry_rejects_malformed_scientific_lock(tmp_path: Path) -> None:
    payload = _explicit_payload(tmp_path)
    payload["sensitivities"]["endpoint_availability"]["scientific_uv_lock_sha256"] = "ABC"
    registry_path = _write_registry(tmp_path, payload)

    with pytest.raises(ValueError, match="64-character lowercase"):
        load_source_registry(registry_path)


def test_registry_verifies_lock_from_protocol_commit(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    lock = b"version = 1\n"
    (tmp_path / "uv.lock").write_bytes(lock)
    subprocess.run(["git", "add", "uv.lock"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "fixture"], cwd=tmp_path, check=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    payload = _explicit_payload(tmp_path)
    for section in ("lineages", "diagnostics", "sensitivities"):
        del payload[section]
    run_tag = "fixture-protocol"
    protocol_tag = f"protocol/{run_tag}"
    subprocess.run(["git", "tag", protocol_tag], cwd=tmp_path, check=True)
    payload["lineages"] = {
        "fixture": {
            **_protocol_identity(
                run_tag,
                paper_role="outcome_free",
                dvc_tracked=True,
                commit=commit,
            ),
            "scientific_uv_lock_sha256": hashlib.sha256(lock).hexdigest(),
        }
    }
    payload["dvc_pointers"] = [f"{root}/experiments/ijds_audit/{run_tag}.dvc" for root in DVC_ROOTS]
    registry_path = _materialize_registry(tmp_path, payload)

    load_source_registry(registry_path, repo_root=tmp_path)

    payload["lineages"]["fixture"]["scientific_uv_lock_sha256"] = "0" * 64
    registry_path = _write_registry(tmp_path, payload)
    with pytest.raises(RuntimeError, match="commit contains"):
        load_source_registry(registry_path, repo_root=tmp_path)


def test_registry_verifies_portable_protocol_bundle_when_local_tag_is_absent(
    tmp_path: Path,
) -> None:
    producer = tmp_path / "producer"
    consumer = tmp_path / "consumer"
    producer.mkdir()
    consumer.mkdir()
    for repository in (producer, consumer):
        subprocess.run(["git", "init", "--quiet"], cwd=repository, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=repository, check=True
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repository, check=True)

    lock = b"version = 1\n"
    (producer / "uv.lock").write_bytes(lock)
    subprocess.run(["git", "add", "uv.lock"], cwd=producer, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "fixture"], cwd=producer, check=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=producer,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    run_tag = "portable-protocol"
    protocol_tag = f"protocol/{run_tag}"
    subprocess.run(["git", "tag", protocol_tag], cwd=producer, check=True)
    bundle_relative = f"provenance/git-bundles/{run_tag}.bundle"
    bundle = consumer / bundle_relative
    bundle.parent.mkdir(parents=True)
    subprocess.run(["git", "bundle", "create", str(bundle), protocol_tag], cwd=producer, check=True)
    source = consumer / "evidence/source.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"status": "fixture"}\n', encoding="utf-8")
    payload = {
        "schema_version": "test-portable-v1",
        "status": "active_ijds_paper_evidence_source_registry",
        "lineages": {
            "fixture": {
                **_protocol_identity(
                    run_tag,
                    paper_role="portable_clean_tagged_replay",
                    dvc_tracked=False,
                    commit=commit,
                ),
                "protocol_bundle": bundle_relative,
                "scientific_uv_lock_sha256": hashlib.sha256(lock).hexdigest(),
            }
        },
        "dvc_pointers": [],
        "sources": {
            "fixture": relative_artifact_descriptor(source, repo_root=consumer),
            "protocol_bundle": relative_artifact_descriptor(bundle, repo_root=consumer),
        },
    }
    registry_path = _write_registry(consumer, payload)
    subprocess.run(
        [
            "git",
            "add",
            "--",
            source.relative_to(consumer),
            bundle.relative_to(consumer),
            registry_path.relative_to(consumer),
        ],
        cwd=consumer,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "--quiet", "-m", "track portable evidence transport"],
        cwd=consumer,
        check=True,
    )

    loaded, sources = load_verified_source_registry(registry_path, repo_root=consumer)

    assert loaded["lineages"]["fixture"]["protocol_commit"] == commit
    assert sources["protocol_bundle"] == bundle.resolve()


def test_registry_rejects_unsafe_protocol_bundle_path(tmp_path: Path) -> None:
    payload = _explicit_payload(tmp_path)
    payload["sensitivities"]["endpoint_availability"]["protocol_bundle"] = "../tag.bundle"
    registry_path = _write_registry(tmp_path, payload)

    with pytest.raises(ValueError, match="repository-relative"):
        load_source_registry(registry_path)


def test_registry_rejects_null_explicit_dvc_tracking(tmp_path: Path) -> None:
    payload = _explicit_payload(tmp_path)
    payload["diagnostics"]["raw_data_audit"]["dvc_tracked"] = None
    registry_path = _write_registry(tmp_path, payload)

    with pytest.raises(TypeError, match="dvc_tracked must be boolean"):
        load_source_registry(registry_path)


@pytest.mark.parametrize("field", ["paper_role", "dvc_tracked"])
def test_registry_rejects_partially_explicit_identity(tmp_path: Path, field: str) -> None:
    payload = _explicit_payload(tmp_path)
    del payload["sensitivities"]["endpoint_availability"][field]
    registry_path = _write_registry(tmp_path, payload)

    with pytest.raises(TypeError, match="require both paper_role and dvc_tracked"):
        load_source_registry(registry_path)


@pytest.mark.parametrize("mutation", ["missing", "unexpected"])
def test_registry_rejects_missing_or_unexpected_dvc_pointers(
    tmp_path: Path,
    mutation: str,
) -> None:
    payload = _explicit_payload(tmp_path)
    if mutation == "missing":
        payload["dvc_pointers"].pop()
    else:
        payload["dvc_pointers"].append(f"models/experiments/ijds_audit/{DIAGNOSTIC_TAG}.dvc")
    registry_path = _write_registry(tmp_path, payload)

    with pytest.raises(ValueError, match="do not match"):
        load_source_registry(registry_path)


def test_registry_rejects_pointer_out_path_mismatch(tmp_path: Path) -> None:
    payload = _explicit_payload(tmp_path)
    registry_path = _materialize_registry(tmp_path, payload)
    pointer_path = tmp_path / payload["dvc_pointers"][0]
    pointer_payload = _valid_pointer_payload(pointer_path.stem)
    pointer_payload["outs"][0]["path"] = "different-run"
    _write_yaml(pointer_path, pointer_payload)

    with pytest.raises(ValueError, match="does not match run directory"):
        load_source_registry(registry_path, repo_root=tmp_path)


def test_registry_normalizes_pointer_out_path_before_matching(tmp_path: Path) -> None:
    payload = _explicit_payload(tmp_path)
    registry_path = _materialize_registry(tmp_path, payload)
    pointer_path = tmp_path / payload["dvc_pointers"][0]
    pointer_payload = _valid_pointer_payload(pointer_path.stem)
    pointer_payload["outs"][0]["path"] = f"./{pointer_path.stem}/"
    _write_yaml(pointer_path, pointer_payload)

    loaded = load_source_registry(registry_path, repo_root=tmp_path)

    assert loaded["schema_version"] == "test-explicit-v1"


@pytest.mark.parametrize(
    ("mutation", "expected_message"),
    [
        ("outs", "exactly one out"),
        ("md5", "md5 must be"),
        ("size", "size must be a non-negative integer"),
        ("nfiles", "nfiles must be a non-negative integer"),
    ],
)
def test_registry_rejects_malformed_pointer_structure(
    tmp_path: Path,
    mutation: str,
    expected_message: str,
) -> None:
    payload = _explicit_payload(tmp_path)
    registry_path = _materialize_registry(tmp_path, payload)
    pointer_path = tmp_path / payload["dvc_pointers"][0]
    pointer_payload = _valid_pointer_payload(pointer_path.stem)
    if mutation == "outs":
        pointer_payload["outs"] = []
    elif mutation == "md5":
        pointer_payload["outs"][0]["md5"] = "not-an-md5"
    elif mutation == "size":
        pointer_payload["outs"][0]["size"] = True
    else:
        pointer_payload["outs"][0]["nfiles"] = -1
    _write_yaml(pointer_path, pointer_payload)

    with pytest.raises((TypeError, ValueError), match=expected_message):
        load_source_registry(registry_path, repo_root=tmp_path)


def test_registry_rejects_malformed_pointer_yaml(tmp_path: Path) -> None:
    payload = _explicit_payload(tmp_path)
    registry_path = _materialize_registry(tmp_path, payload)
    pointer_path = tmp_path / payload["dvc_pointers"][0]
    pointer_path.write_text("outs:\n- md5: [\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Malformed active DVC pointer YAML"):
        load_source_registry(registry_path, repo_root=tmp_path)
