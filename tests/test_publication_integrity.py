from __future__ import annotations

from scripts.check_publication_integrity import check_publication_integrity


def test_active_ijds_publication_surfaces_are_claim_synchronized() -> None:
    assert check_publication_integrity() == []
