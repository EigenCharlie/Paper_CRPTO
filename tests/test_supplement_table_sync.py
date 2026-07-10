"""Drift guards for the diagnostic multidataset evidence.

Chapter 30 retains the detailed A25/A34 values. The submitted body and
supplement deliberately keep only the scope boundary: these older replications
are static transfer evidence, not active-policy certificates. Tests preserve
both contracts without forcing retired detail back into the IJDS narrative.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TABLES = REPO / "reports" / "crpto" / "tables"

SUPPLEMENT = REPO / "paper" / "supplement_ijds.qmd"
PAPER = REPO / "paper" / "CRPTO_ijds.qmd"
BOOK_CH30 = REPO / "book" / "chapters" / "30-replicacion-multidataset.qmd"


def _read_rows(name: str) -> list[dict[str, str]]:
    path = TABLES / name
    if not path.is_file():
        pytest.skip(f"{name} not present locally.")
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _text(path: Path) -> str:
    if not path.is_file():
        pytest.skip(f"{path} not present locally.")
    return path.read_text(encoding="utf-8")


def test_a25_robust_objectives_match_book_and_diagnostic_status() -> None:
    """A25 values remain in the book while IJDS surfaces retain their boundary."""
    rows = _read_rows("crpto_tableA25_external_replication_gate.csv")
    book = _text(BOOK_CH30)
    missing: list[str] = []
    for row in rows:
        dollars = f"${round(float(row['robust_objective'])):,}"
        if dollars not in book:
            missing.append(f"{row['dataset']} {dollars} missing in {BOOK_CH30.name}")
    assert not missing, "A25 robust objective drift:\n" + "\n".join(missing)

    supplement = _text(SUPPLEMENT)
    paper = _text(PAPER)
    assert "A25--A34" in supplement
    assert "Static transfer evidence; not active Lending Club certificates." in supplement
    assert "Prosper" in paper and "Freddie/Mendeley" in paper
    assert "retained as diagnostics or external context" in paper


def test_a34_price_of_robustness_matches_historical_book_surface() -> None:
    """A34 signed price-of-robustness values remain traceable in chapter 30."""
    rows = _read_rows("crpto_tableA34_price_of_robustness_cross_dataset.csv")
    book = _text(BOOK_CH30)
    missing: list[str] = []
    for row in rows:
        pct = f"+{float(row['price_of_robustness_pct']) * 100:.2f}%"
        if pct not in book:
            missing.append(f"{row['application']} {pct} missing in {BOOK_CH30.name}")
    assert not missing, "A34 price-of-robustness drift:\n" + "\n".join(missing)

    supplement = _text(SUPPLEMENT)
    assert "older frozen replication contracts" in supplement
    assert "cannot be quoted as direct" in supplement
    assert "replications of the active midpoint policy" in supplement
