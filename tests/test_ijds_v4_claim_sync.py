"""Structure and wording checks for the active V4 paper and its controls."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BODY = REPO / "paper/CRPTO_ijds.qmd"
SUPPLEMENT = REPO / "paper/supplement_ijds.qmd"
OFFICIAL = REPO / "paper/submission/CRPTO_ijds_submission.tex"


def _section(text: str, start: str, end: str) -> str:
    return text[text.index(start) : text.index(end)]


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
    assert body_table_ids == {
        "tbl-protocol",
        "tbl-credit-controls",
        "tbl-mondrian-roles",
        "tbl-claim-boundary",
        "tbl-two-ruler",
        "tbl-catalog-transport",
        "tbl-embedding-direction",
        "tbl-calibrator-sensitivity",
        "tbl-phase-census",
        "tbl-related-calibrated-objects",
        "tbl-set-native-direction",
    }
    assert official.count(r"\begin{longtable}") == len(body_table_ids)
    body_figure_ids = set(re.findall(r"\{#(fig-[A-Za-z0-9_-]+)", body))
    assert body_figure_ids == {
        "fig-information-boundary",
        "fig-coverage",
        "fig-phase",
        "fig-common-panel",
    }
    assert official.count(r"\begin{figure}") == len(body_figure_ids)


def test_v4_wording_keeps_theory_and_empirical_scope_separate() -> None:
    body = BODY.read_text(encoding="utf-8").lower()
    supplement = SUPPLEMENT.read_text(encoding="utf-8").lower()
    body_normalized = re.sub(r"\s+", " ", body)
    supplement_normalized = re.sub(r"\s+", " ", supplement)

    for surface in (body_normalized, supplement_normalized):
        assert "constant-score" not in surface
        assert re.search(r"varying scores|scores vary", surface)
        assert "not a confidence interval" in surface
        assert "not a selected operating policy" in surface
        assert "not a promoted operating policy" not in surface
        assert "not independent replications" in surface
    assert "not a prospective trial, preregistration, or causal estimate" in body_normalized
    assert "not a causal identified set" in supplement
    # The exact threshold characterization and target-side implication have
    # separate conditions. The two-threshold result is a band-mass identity, not
    # a universal continuity or constant-score argument.
    assert "target-support condition" in body_normalized
    for surface in (body_normalized, supplement_normalized):
        assert "coverage response" in surface or "coverage change" in surface
        assert "does not imply continuity" in surface
        assert "artifact of a degenerate score" not in surface
    for surface in (body_normalized, supplement_normalized):
        assert "simulation claim" not in surface
        assert "no portfolio claim uses this simulation" not in surface


def test_related_work_is_ordered_by_calibrated_object() -> None:
    body = BODY.read_text(encoding="utf-8")
    related = _section(body, "# Related Work", "# Data and Locked Evaluation Design")

    assert re.findall(r"^## (.+)$", related, flags=re.MULTILINE) == [
        "Probability calibration",
        "Conformal membership and temporal transport",
        "Selection, false-coverage rate, and selective labels",
        "Decision loss and risk calibration",
        "Robust constraints and predictive ambiguity sets",
        "Credit outcomes, censoring, and portfolio value",
    ]
    assert "Conformal Predictive Portfolio Selection" in related
    assert "@kato2025" in related
    assert "@lakkaraju2017selective" in related
    assert "@kleinberg2018human" in related


def test_theory_has_two_suites_and_sequential_propositions() -> None:
    body = BODY.read_text(encoding="utf-8")
    method = _section(body, "# Method", "# Audit Theory and Estimands")
    theory = _section(body, "# Audit Theory and Estimands", "# Results")

    assert re.findall(r"^## (.+)$", theory, flags=re.MULTILINE) == [
        "Prediction geometry and partial identification",
        "Decision geometry",
    ]
    proposition_numbers = [
        int(value) for value in re.findall(r"^\*\*Proposition (\d+)", theory, flags=re.MULTILINE)
    ]
    assert proposition_numbers == list(range(1, 9))

    joint_block = "## Joint-block combined-rank reference diagnostic"
    assert method.count(joint_block) == 1
    assert joint_block not in theory
    assert body.index(joint_block) < body.index("# Audit Theory and Estimands")


def test_secondary_theory_claims_remain_as_results_bridges_only() -> None:
    body = BODY.read_text(encoding="utf-8")
    results = _section(body, "# Results", "# Discussion")

    markers = (
        "<!-- claim:theory.sharp_directional_residual_frontier -->",
        "<!-- claim:theory.selection_weight_covariance_identity -->",
        "<!-- claim:theory.monotone_catalog_completion -->",
    )
    for marker in markers:
        assert body.count(marker) == 1
        assert marker in results

    for formal_statement in (
        "**Proposition 8 (sharp directional residual-distribution bounds).**",
        "**Identity 1 (count versus exposure weighting).**",
        "**Lemma 2 (monotone finite-catalog completion).**",
    ):
        assert formal_statement not in body


def test_review_surfaces_do_not_expose_exact_v4_identifiers() -> None:
    for path in (BODY, SUPPLEMENT, OFFICIAL):
        text = path.read_text(encoding="utf-8")
        assert "ijds-binary-geometry-frontier-v4-2026-07-12" not in text
        assert "60cdf298d965525cddaaf03abccd15ff805e1a15" not in text
        assert "c2b3dc2d18c9fed80708682d5a0369c80c89643e2d28024418522d954ebe667c" not in text
