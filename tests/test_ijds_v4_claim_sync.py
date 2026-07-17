"""Structure and wording checks for the active V4 paper and its controls."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BODY = REPO / "paper/CRPTO_ijds.qmd"
SUPPLEMENT = REPO / "paper/supplement_ijds.qmd"
OFFICIAL = REPO / "paper/submission/CRPTO_ijds_submission.tex"


def test_body_and_generated_tex_share_architecture_citations_and_displays() -> None:
    body = BODY.read_text(encoding="utf-8")
    official = OFFICIAL.read_text(encoding="utf-8")
    sections = (
        "Introduction",
        "Related Work",
        "Data and Locked Evaluation Design",
        "Method",
        "Audit Theory and Estimands",
        "Results",
        "Discussion",
        "Limitations",
        "Reproducibility",
        "Conclusion",
    )
    assert [body.index(f"# {section}") for section in sections] == sorted(
        body.index(f"# {section}") for section in sections
    )
    assert [official.index(rf"\section{{{section}}}") for section in sections] == sorted(
        official.index(rf"\section{{{section}}}") for section in sections
    )

    body_citations = {
        key
        for key in re.findall(r"@([A-Za-z0-9_:-]+)", body)
        if not key.startswith(("fig-", "tbl-", "eq-", "sec-"))
    }
    tex_citations: set[str] = set()
    for group in re.findall(r"\\cite\w*\{([^}]+)\}", official):
        tex_citations.update(key.strip() for key in group.split(","))
    assert body_citations == tex_citations
    body_table_ids = set(re.findall(r"\{#(tbl-[A-Za-z0-9_-]+)\}", body))
    assert body_table_ids == {"tbl-protocol", "tbl-credit-controls", "tbl-two-ruler"}
    assert official.count(r"\begin{longtable}") == len(body_table_ids)
    assert body.count("{#fig-") == official.count(r"\begin{figure}") == 2


def test_v4_wording_keeps_theory_and_empirical_scope_separate() -> None:
    body = BODY.read_text(encoding="utf-8").lower()
    supplement = SUPPLEMENT.read_text(encoding="utf-8").lower()
    body_normalized = re.sub(r"\s+", " ", body)
    supplement_normalized = re.sub(r"\s+", " ", supplement)

    for surface in (body_normalized, supplement_normalized):
        assert "constant-score" in surface
        assert re.search(r"varying scores|scores vary", surface)
        assert "not a confidence interval" in surface
        assert "not a deployable" in surface
        assert "not independent replications" in surface
    assert "not a prospective trial, preregistration, or causal estimate" in body_normalized
    assert "not a causal identified set" in supplement
    assert (
        "constant-score theorem identifies a mechanism rather than the varying-score empirical path"
    ) in body_normalized
    for surface in (body_normalized, supplement_normalized):
        assert "simulation claim" not in surface
        assert "no portfolio claim uses this simulation" not in surface


def test_review_surfaces_do_not_expose_exact_v4_identifiers() -> None:
    for path in (BODY, SUPPLEMENT, OFFICIAL):
        text = path.read_text(encoding="utf-8")
        assert "ijds-binary-geometry-frontier-v4-2026-07-12" not in text
        assert "60cdf298d965525cddaaf03abccd15ff805e1a15" not in text
        assert "c2b3dc2d18c9fed80708682d5a0369c80c89643e2d28024418522d954ebe667c" not in text
