"""Tests for the active evidence source registry."""

from __future__ import annotations

from pathlib import Path

from src.ijds_audit.publication_sources import load_verified_source_registry

ROOT = Path(__file__).resolve().parents[2]


def test_active_evidence_registry_verifies_every_source() -> None:
    payload, sources = load_verified_source_registry(
        ROOT / "configs/ijds_active_evidence_sources.yaml",
        repo_root=ROOT,
    )
    assert payload["schema_version"] == "2026-07-14.2"
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
    }
    assert len(payload["dvc_pointers"]) == 12
    assert payload["lineages"]["binary_geometry"]["evaluation"]["run_tag"].endswith("2026-07-14-v3")
