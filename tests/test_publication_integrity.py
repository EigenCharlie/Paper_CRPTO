from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

import scripts.check_publication_integrity as integrity
from scripts.check_publication_integrity import (
    EXPECTED_SCIENTIFIC_GIT_LINEAGES,
    SOURCE_REGISTRY_PATH,
    _check_sealed_extension_payload,
    _load_integrity_source_registry,
    _scientific_git_lineages,
    _sealed_parent_manifest,
    check_publication_integrity,
)


def test_active_ijds_publication_surfaces_are_claim_synchronized() -> None:
    assert check_publication_integrity() == []


def test_scientific_git_lineage_count_is_derived_from_registry() -> None:
    registry = yaml.safe_load(SOURCE_REGISTRY_PATH.read_text(encoding="utf-8"))

    assert _scientific_git_lineages(registry) == EXPECTED_SCIENTIFIC_GIT_LINEAGES
    assert len(EXPECTED_SCIENTIFIC_GIT_LINEAGES) == 11

    missing = deepcopy(registry)
    del missing["lineages"]["diagnostics"]["common_panel_threshold_response"]["artifact_tag"]
    assert _scientific_git_lineages(missing) != EXPECTED_SCIENTIFIC_GIT_LINEAGES

    unexpected = deepcopy(registry)
    unexpected["sensitivities"]["endpoint_availability"]["artifact_tag"] = "artifacts/unexpected"
    assert _scientific_git_lineages(unexpected) != EXPECTED_SCIENTIFIC_GIT_LINEAGES


def test_missing_dvc_sources_use_only_the_exact_sealed_incremental_bridge() -> None:
    verification = _load_integrity_source_registry()

    assert verification.mode == "sealed_incremental"
    assert len(verification.missing_dvc_sources) == 33
    assert set(verification.registered) == set(verification.registry["sources"])
    assert _sealed_parent_manifest()["schema_version"] == "2026-07-31.1"


def test_incremental_bridge_rejects_changed_parent_descriptor(
    tmp_path: Path,
) -> None:
    registry = yaml.safe_load(SOURCE_REGISTRY_PATH.read_text(encoding="utf-8"))
    registry["sources"]["v4_summary"]["sha256"] = "0" * 64
    mutated_path = tmp_path / "mutated_registry.yaml"
    mutated_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

    with pytest.raises(RuntimeError, match="differs from the sealed parent registry"):
        _load_integrity_source_registry(mutated_path)


def test_strict_registry_failure_does_not_fall_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_strict(*args: object, **kwargs: object) -> object:
        raise RuntimeError("materialized source hash drift")

    def forbidden_fallback(*args: object, **kwargs: object) -> object:
        pytest.fail("non-missing strict failures must not enter incremental mode")

    monkeypatch.setattr(integrity, "load_verified_source_registry", fail_strict)
    monkeypatch.setattr(
        integrity,
        "load_verified_or_sealed_source_registry",
        forbidden_fallback,
    )
    with pytest.raises(RuntimeError, match="materialized source hash drift"):
        _load_integrity_source_registry()


def test_sealed_parent_manifest_hash_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(integrity, "SEALED_PARENT_MANIFEST_SHA256", "0" * 64)

    with pytest.raises(RuntimeError, match="exact byte/hash pin"):
        _sealed_parent_manifest()


def test_sealed_extension_payload_and_boundaries_are_fail_closed() -> None:
    evidence = json.loads(integrity.EVIDENCE_PATH.read_text(encoding="utf-8"))
    registry = yaml.safe_load(SOURCE_REGISTRY_PATH.read_text(encoding="utf-8"))

    assert _check_sealed_extension_payload(evidence, registry) == []

    wrong_phase_count = deepcopy(evidence)
    wrong_phase_count["binary_phase_census"]["cells"] = 199
    assert "binary-phase 200-cell census or exact checks changed" in (
        _check_sealed_extension_payload(wrong_phase_count, registry)
    )

    leaked_phase_row = deepcopy(evidence)
    leaked_phase_row["binary_phase_census"]["rows"][0]["target_coverage"] = 0.9
    assert "binary-phase 200-cell census or exact checks changed" in (
        _check_sealed_extension_payload(leaked_phase_row, registry)
    )

    wrong_dual_census = deepcopy(evidence)
    wrong_dual_census["dual_coefficient_binary_set_native"]["new_optimizations"] = 1
    assert "dual-coefficient 208/88/120/0 certificate census changed" in (
        _check_sealed_extension_payload(wrong_dual_census, registry)
    )

    promoted_dual_claim = deepcopy(evidence)
    promoted_dual_claim["dual_coefficient_binary_set_native"]["optimizer_unique_certified"] = True
    assert "dual-coefficient interpretation boundary changed" in (
        _check_sealed_extension_payload(promoted_dual_claim, registry)
    )

    wrong_identity = deepcopy(evidence)
    wrong_identity["binary_phase_census"]["artifact_commit"] = "0" * 40
    assert "binary-phase identity differs from the registry" in (
        _check_sealed_extension_payload(wrong_identity, registry)
    )
