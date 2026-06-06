"""Drift guard for hand-authored multidataset tables in the paper surfaces.

The online supplement, the IJDS body, and book chapter 30 embed the external
replication tables (A25, A34) as hand-written Markdown rather than reading the
CSV at render time. That is convenient but can silently drift if a CSV is
regenerated without updating the prose. These tests assert the headline numbers
shown in those surfaces still match the source CSVs.

Only a few anchor values are checked -- enough to catch a stale copy/paste,
without re-implementing a full Markdown table parser.
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


def test_a25_robust_objectives_match_surfaces() -> None:
    """A25 robust LP objectives (as `$N`) appear in supplement, paper, and book."""
    rows = _read_rows("crpto_tableA25_external_replication_gate.csv")
    surfaces = {p: _text(p) for p in (SUPPLEMENT, PAPER, BOOK_CH30)}
    missing: list[str] = []
    for row in rows:
        dollars = f"${round(float(row['robust_objective'])):,}"
        for path, body in surfaces.items():
            if dollars not in body:
                missing.append(f"{row['dataset']} {dollars} missing in {path.name}")
    assert not missing, "A25 robust objective drift:\n" + "\n".join(missing)


def test_a34_price_of_robustness_match_surfaces() -> None:
    """A34 signed price-of-robustness (as `+X.XX%`) appears in supplement and book."""
    rows = _read_rows("crpto_tableA34_price_of_robustness_cross_dataset.csv")
    surfaces = {p: _text(p) for p in (SUPPLEMENT, BOOK_CH30)}
    missing: list[str] = []
    for row in rows:
        pct = f"+{float(row['price_of_robustness_pct']) * 100:.2f}%"
        for path, body in surfaces.items():
            if pct not in body:
                missing.append(f"{row['application']} {pct} missing in {path.name}")
    assert not missing, "A34 price-of-robustness drift:\n" + "\n".join(missing)
