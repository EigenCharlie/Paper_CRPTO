from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_print_css_does_not_create_a_trailing_grid_page() -> None:
    css = (ROOT / "paper" / "ijds.css").read_text(encoding="utf-8")

    assert "#quarto-content {\n    display: block !important;" in css
    assert "grid-template-rows: none !important;" in css
    assert "break-after: auto !important;" in css
    assert "page-break-after: auto !important;" in css
    assert "break-after: avoid-page" not in css
