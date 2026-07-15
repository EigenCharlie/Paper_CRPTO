"""Scope boundaries for active publication-integrity scanning."""

from __future__ import annotations

from scripts.check_publication_integrity import ACTIVE_EDITORIAL_SURFACES, REPO


def test_historical_extraction_manifest_is_not_an_active_editorial_surface() -> None:
    assert REPO / "EXTRACTION_MANIFEST.md" not in ACTIVE_EDITORIAL_SURFACES
    assert REPO / "docs/research/active_claims_2026-07-14.md" in ACTIVE_EDITORIAL_SURFACES
