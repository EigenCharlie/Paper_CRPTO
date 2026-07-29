from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_html_previews_use_offline_native_mathml() -> None:
    for relative in ("paper/CRPTO_ijds.qmd", "paper/supplement_ijds.qmd"):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "html-math-method: mathml" in source


def test_official_template_does_not_stretch_sparse_float_pages() -> None:
    template = (ROOT / "paper/submission/informs-pandoc-template.tex").read_text(encoding="utf-8")
    assert "\\begin{document}\n\\raggedbottom" in template


def test_print_css_does_not_create_a_trailing_grid_page() -> None:
    css = (ROOT / "paper" / "ijds.css").read_text(encoding="utf-8")

    assert "#quarto-content {\n    display: block !important;" in css
    assert "grid-template-rows: none !important;" in css
    assert "break-after: auto !important;" in css
    assert "page-break-after: auto !important;" in css
    assert "break-after: avoid-page" not in css
