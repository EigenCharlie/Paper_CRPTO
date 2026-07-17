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


def test_active_evidence_registry_verifies_every_source() -> None:
    payload, sources = load_verified_source_registry(
        ROOT / "configs/ijds_active_evidence_sources.yaml",
        repo_root=ROOT,
    )
    assert payload["schema_version"] == "2026-07-15.4"
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
        "endpoint_sensitivity_summary",
        "structural_sensitivity_config",
        "structural_sensitivity_freeze",
        "structural_sensitivity_summary",
        "rolling_origin_summary",
        "rolling_origin_receipt",
        "missingness_summary",
        "missingness_receipt",
    }
    assert len(payload["dvc_pointers"]) == 27
    assert payload["lineages"]["binary_geometry"]["evaluation"]["run_tag"].endswith("2026-07-15-v5")


def test_active_registry_returns_all_dvc_run_tags_in_causal_config_order() -> None:
    payload = load_source_registry(ROOT / "configs/ijds_active_evidence_sources.yaml")

    assert active_lineage_run_tags(payload) == (
        "ijds-binary-geometry-frontier-v4-2026-07-12-v1",
        "ijds-binary-geometry-frontier-v4-2026-07-15-v5",
        "ijds-normalized-objective-frontier-2026-07-13-v1c",
        "ijds-normalized-objective-frontier-2026-07-15-v5",
        "ijds-credit-risk-controls-2026-07-13-v1b",
        "ijds-credit-risk-controls-2026-07-15-v5",
        "ijds-endpoint-availability-sensitivity-2026-07-14-v1",
        "ijds-portfolio-structure-sensitivity-2026-07-15-v6",
        "ijds-rolling-origin-2017-2026-07-15-v4",
        "ijds-missingness-sensitivity-2026-07-15-v3",
        "ijds-binary-geometry-frontier-v4-2026-07-14-v3",
        "ijds-normalized-objective-frontier-2026-07-14-v3",
        "ijds-credit-risk-controls-2026-07-14-v3",
        "ijds-portfolio-structure-sensitivity-2026-07-15-v5",
    )


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
