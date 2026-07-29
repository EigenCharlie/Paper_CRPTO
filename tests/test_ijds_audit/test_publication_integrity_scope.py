"""Scope boundaries for active publication-integrity scanning."""

from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.check_publication_integrity import (
    ACTIVE_EDITORIAL_SURFACES,
    REPO,
    _guarded_check,
    _paper_artifact_failures,
)


def test_historical_extraction_manifest_is_not_an_active_editorial_surface() -> None:
    assert REPO / "EXTRACTION_MANIFEST.md" not in ACTIVE_EDITORIAL_SURFACES
    assert REPO / "docs/research/active_claims_2026-07-14.md" in ACTIVE_EDITORIAL_SURFACES


def test_integrity_subcheck_reports_schema_drift_without_aborting() -> None:
    def stale_manifest() -> list[str]:
        raise KeyError("common_panel_threshold_response")

    assert _guarded_check("evidence decision contract", stale_manifest) == [
        "evidence decision contract failed closed: 'common_panel_threshold_response'"
    ]


def _descriptor(path: Path, *, root: Path) -> dict[str, object]:
    payload = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def test_paper_artifact_descriptors_fail_closed_on_tampering(tmp_path: Path) -> None:
    artifact = tmp_path / "table.csv"
    artifact.write_text("a,b\n1,2\n", encoding="utf-8")
    descriptors = {"table/example": _descriptor(artifact, root=tmp_path)}

    assert _paper_artifact_failures(descriptors, repo_root=tmp_path) == []

    artifact.write_text("a,b\n1,3\n", encoding="utf-8")
    failures = _paper_artifact_failures(descriptors, repo_root=tmp_path)
    assert len(failures) == 1
    assert "mismatched on sha256" in failures[0]


def test_paper_artifact_descriptors_reject_path_escape_and_duplicates(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.csv"
    outside.write_text("x\n", encoding="utf-8")
    escaped = {
        "table/one": {"path": "../outside.csv", "bytes": 2, "sha256": "0" * 64},
        "table/two": {"path": "../outside.csv", "bytes": 2, "sha256": "0" * 64},
    }

    failures = _paper_artifact_failures(escaped, repo_root=tmp_path)
    assert any("failed verification" in failure for failure in failures)
    assert any("duplicates the path" in failure for failure in failures)
