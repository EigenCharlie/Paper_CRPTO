"""Contracts for the additive 2026-08-01 sealed-parent evidence extension."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts import extend_ijds_evidence_from_sealed_parent_2026_08_01 as extension
from src.ijds_audit.publication_generation import PUBLICATION_IMPLEMENTATION_PATHS

REPO = Path(__file__).resolve().parents[2]
EVIDENCE = REPO / "reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json"


def _current() -> dict[str, Any]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_extension_preserves_every_parent_scientific_payload() -> None:
    _, parent = extension._load_pinned_parent()
    current = _current()
    allowed_top_level_changes = {
        "schema_version",
        "status",
        "source_registry",
        "lineages",
        "sensitivities",
        "replay_dependencies",
        "binary_phase_census",
        "dual_coefficient_binary_set_native",
        "incremental_parent",
        "audit_thesis",
        "source_artifacts",
        "paper_artifacts",
        "claim_ledger",
    }
    for key, value in parent.items():
        if key not in allowed_top_level_changes:
            assert current[key] == value, key

    parent_diagnostics = parent["lineages"]["diagnostics"]
    current_diagnostics = current["lineages"]["diagnostics"]
    assert {key: current_diagnostics[key] for key in parent_diagnostics} == parent_diagnostics
    assert current["sensitivities"] == parent["sensitivities"]
    assert current["replay_dependencies"] == parent["replay_dependencies"]

    for name, descriptor in parent["paper_artifacts"].items():
        assert current["paper_artifacts"][name] == descriptor
    implementation_names = set(PUBLICATION_IMPLEMENTATION_PATHS)
    for name, descriptor in parent["source_artifacts"].items():
        if name not in implementation_names:
            assert current["source_artifacts"][name] == descriptor


def test_extension_has_exact_new_inventory_and_parent_seal() -> None:
    current = _current()
    assert current["schema_version"] == extension.EXTENSION_SCHEMA
    assert current["status"] == extension.EXTENSION_STATUS
    assert len(current["paper_artifacts"]) == 55
    assert (
        sum(
            descriptor["path"].endswith(".csv")
            for descriptor in current["paper_artifacts"].values()
        )
        == 45
    )
    assert current["incremental_parent"] == {
        **current["incremental_parent"],
        "commit": extension.PARENT_COMMIT,
        "path": extension.PARENT_MANIFEST_PATH,
        "bytes": extension.PARENT_MANIFEST_BYTES,
        "sha256": extension.PARENT_MANIFEST_SHA256,
        "schema_version": extension.PARENT_SCHEMA,
        "status": extension.PARENT_STATUS,
        "extension_scope": [
            "binary_phase_census",
            "dual_coefficient_binary_set_native",
        ],
        "historical_numeric_payload_recomputed": False,
        "protected_stages_run": [],
    }
    assert len(current["incremental_parent"]["unmaterialized_unchanged_dvc_sources"]) == 33


def test_extension_recomputes_the_two_git_native_results_byte_identically() -> None:
    assert extension.build_extension(check=True) == EVIDENCE


def test_extension_promotes_only_the_two_additive_tables() -> None:
    assert (
        frozenset(extension.TABLE_TARGETS[name] for name in extension.NEW_TABLE_KEYS)
        == extension.PROMOTED_EXTENSION_TARGETS
    )
    assert {path.suffix for path in extension.PROMOTED_EXTENSION_TARGETS} == {".csv"}


def test_parent_manifest_hash_is_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extension, "PARENT_MANIFEST_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="no longer matches its seal"):
        extension._load_pinned_parent()
