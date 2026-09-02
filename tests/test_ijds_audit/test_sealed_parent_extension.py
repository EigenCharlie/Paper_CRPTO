"""Contracts for the additive 2026-09-01 sealed-parent evidence extension."""

from __future__ import annotations

import json
from typing import Any

import pytest

from scripts import extend_ijds_evidence_from_sealed_parent_2026_09_01 as extension
from src.ijds_audit.publication_generation import PUBLICATION_IMPLEMENTATION_PATHS

REPO = extension.ROOT
EVIDENCE = REPO / "reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json"


def _current() -> dict[str, Any]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _refreshed_figure_artifacts() -> set[str]:
    return {
        f"figure/{name}/{kind}" for name in extension.REFRESHED_FIGURES for kind in ("png", "pdf")
    }


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
        "binary_phase_target_support",
        "incremental_parent",
        "audit_thesis",
        "source_artifacts",
        "paper_artifacts",
        "claim_ledger",
    }
    for key, value in parent.items():
        if key not in allowed_top_level_changes:
            assert current[key] == value, key

    assert current["lineages"] == parent["lineages"]
    assert current["sensitivities"] == parent["sensitivities"]
    assert current["replay_dependencies"] == parent["replay_dependencies"]

    refreshed = _refreshed_figure_artifacts()
    changed_paper_artifacts: set[str] = set()
    for name, descriptor in parent["paper_artifacts"].items():
        if current["paper_artifacts"][name] != descriptor:
            changed_paper_artifacts.add(name)
            assert name in refreshed
            assert current["paper_artifacts"][name]["path"] == descriptor["path"]
        else:
            assert name not in refreshed
    assert changed_paper_artifacts == refreshed
    assert set(current["paper_artifacts"]).difference(parent["paper_artifacts"]) == {
        "table/binary_phase_target_support"
    }

    implementation_names = set(PUBLICATION_IMPLEMENTATION_PATHS)
    for name, descriptor in parent["source_artifacts"].items():
        if name not in implementation_names:
            assert current["source_artifacts"][name] == descriptor


def test_extension_has_exact_inventory_and_parent_seal() -> None:
    current = _current()
    parent = current["incremental_parent"]
    assert current["schema_version"] == extension.EXTENSION_SCHEMA
    assert current["status"] == extension.EXTENSION_STATUS
    assert len(current["paper_artifacts"]) == 56
    assert (
        sum(
            descriptor["path"].endswith(".csv")
            for descriptor in current["paper_artifacts"].values()
        )
        == 46
    )
    assert parent["commit"] == extension.PARENT_COMMIT
    assert parent["path"] == extension.PARENT_MANIFEST_PATH
    assert parent["bytes"] == extension.PARENT_MANIFEST_BYTES
    assert parent["sha256"] == extension.PARENT_MANIFEST_SHA256
    assert parent["schema_version"] == extension.PARENT_SCHEMA
    assert parent["status"] == extension.PARENT_STATUS
    assert parent["extension_scope"] == [extension.NEW_TABLE_KEY]
    assert parent["derived_from_parent_paper_artifacts"] == [
        "table/binary_phase_census",
        "table/conformal_set_diagnostics",
        "table/exchangeability_cells",
        "table/exchangeability_strata",
    ]
    assert parent["protected_stages_run"] == []
    assert parent["historical_numeric_payload_recomputed"] is False
    assert parent["all_declared_cells_reported_without_selection"] is True
    assert parent["unmaterialized_unchanged_dvc_sources"] == sorted(
        set(parent["unmaterialized_unchanged_dvc_sources"])
    )


def test_extension_promotes_only_the_additive_table_and_refreshed_figures() -> None:
    expected = {
        extension.TABLE_TARGETS[extension.NEW_TABLE_KEY],
        *(
            extension.FIGURE_DIR / f"{extension.FIGURE_STEMS[name]}.{kind}"
            for name in extension.REFRESHED_FIGURES
            for kind in ("png", "pdf")
        ),
    }
    assert frozenset(expected) == extension.PROMOTED_TARGETS
    assert {path.suffix for path in extension.PROMOTED_TARGETS} == {".csv", ".png", ".pdf"}


def test_parent_manifest_hash_is_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extension, "PARENT_MANIFEST_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="no longer matches its seal"):
        extension._load_pinned_parent()
