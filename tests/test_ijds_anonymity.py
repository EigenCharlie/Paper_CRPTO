from __future__ import annotations

from scripts.check_publication_integrity import (
    REVIEWER_FORBIDDEN_LITERALS,
    REVIEWER_FORBIDDEN_PATTERNS,
    REVIEWER_SURFACES,
)


def test_reviewer_surfaces_exclude_identity_and_searchable_fingerprints() -> None:
    for path in REVIEWER_SURFACES:
        text = path.read_text(encoding="utf-8")
        normalized = text.lower()

        for token in REVIEWER_FORBIDDEN_LITERALS:
            assert token not in normalized, f"{path.name} exposes {token!r}"
        for label, pattern in REVIEWER_FORBIDDEN_PATTERNS:
            assert pattern.search(text) is None, f"{path.name} exposes {label}"
