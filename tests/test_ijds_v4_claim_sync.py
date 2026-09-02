"""Structure and wording checks for the active V4 paper and its controls."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BODY = REPO / "paper/CRPTO_ijds.qmd"
SUPPLEMENT = REPO / "paper/supplement_ijds.qmd"
OFFICIAL = REPO / "paper/submission/CRPTO_ijds_submission.tex"
REGISTRY = REPO / "docs/research/active_claims_2026-07-14.md"
CLAIM_MATRIX = REPO / "paper/submission/CLAIM_AUDIT_MATRIX.md"


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
    assert "@joshi2026risk_controlled_postprocessing" in related
    assert "@liang2026model_selection_conformal" in related
    assert "@yang2025selection_aggregation_conformal" in related
    assert "@zhu2026action_conditional_risk_averse" in related
    assert "@lakkaraju2017selective" in related
    assert "@kleinberg2018human" in related
    assert "Selecting a predictor or conformal set is a different object" in related
    assert "finite discrete action space" in related


def test_body_wording_preserves_information_and_identification_boundaries() -> None:
    body = BODY.read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", body)
    information = _section(body, "## Information boundary", "## Identification safeguards")

    assert "links a Platt-scaled default score" in normalized
    assert "calibrated default score" not in normalized
    assert (
        "A uniform shortfall across the four calibrators is therefore not established" in normalized
    )
    assert "shortfall is therefore not uniform" not in normalized.lower()
    assert "scores, prediction sets, and strata" in re.sub(r"\s+", " ", information)
    assert "administrative-outcome panel is joined one-to-one only after" in re.sub(
        r"\s+", " ", information
    )
    assert "scores, administrative outcomes, and strata" not in information
    assert "Online Supplement Online Supplement" not in body
    assert "Online Supplement Appendix E.6" in normalized
    assert "208 window-by-role-month certificates over 26 candidate menus" in normalized
    assert "208 monthly menus" not in normalized


def test_fixed_top_k_jomi_corollary_keeps_its_exact_boundary() -> None:
    body = BODY.read_text(encoding="utf-8")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")
    marker = "<!-- claim:theory.jomi_top_k_reference_size_law -->"

    assert body.count(marker) == 1
    assert supplement.count(marker) == 1
    assert r"1\le K<m" in body
    assert r"1\le K<m" in supplement
    assert r"\alpha\in(0,1)" in body
    assert r"\alpha\in(0,1)" in supplement
    for surface in (body, supplement):
        normalized = re.sub(r"\s+", " ", surface)
        assert r"\operatorname{BetaBinomial}(n,K+1,m-K)" in surface
        assert r"Z_i>T_{\mathrm{topK}}" in surface
        assert r"S_i>T_{\mathrm{topK}}" not in surface
        assert r"r_\alpha" in surface
        assert (
            "not a new beta--binomial law" in normalized
            or "do not claim a new beta--binomial law" in normalized
        )
        assert "finite cutoff" in normalized
    assert "equal-notional corollary" in supplement.lower()
    assert "ijds-equal-notional-jomi-synthetic-feasibility" not in body
    assert "ijds-equal-notional-jomi-synthetic-feasibility" not in supplement
    assert "0.09994" not in body
    assert "0.09994" not in supplement
    assert r"M_{\rm det}" not in supplement
    assert r"M_{\mathrm{det}}\le M^{*}" in supplement


def test_dual_coefficient_certificate_count_names_the_repeated_unit() -> None:
    for path in (BODY, SUPPLEMENT, REGISTRY, CLAIM_MATRIX):
        normalized = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
        assert "208 window-by-role-month certificates over 26" in normalized
        assert "208 monthly menus" not in normalized

    matrix = CLAIM_MATRIX.read_text(encoding="utf-8")
    assert "Set-native binary worst-label counterpart" in matrix
    assert "Set-native binary robust counterpart" not in matrix
    assert "worst-label-minus-continuous-embedding" in matrix
    assert "robust-minus-V1d" not in matrix


def test_policy_post_processing_neighbor_keeps_quantitative_conditions() -> None:
    body = BODY.read_text(encoding="utf-8")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")
    related = _section(body, "# Related Work", "# Data and Locked Evaluation Design")

    for surface in (related, supplement):
        assert "pointwise exact-safe fallback" in surface
        assert "exchangeable labeled observations" in surface
        assert r"p_s<\varepsilon<p_0" in surface
        assert r"c_Wz^\beta" in surface
        assert r"F_{\widehat\Delta}" in surface


def test_theory_has_two_suites_and_compact_statement_hierarchy() -> None:
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
    lemma_numbers = [
        int(value) for value in re.findall(r"^\*\*Lemma (\d+)", theory, flags=re.MULTILINE)
    ]
    corollary_numbers = [
        int(value) for value in re.findall(r"^\*\*Corollary (\d+)", theory, flags=re.MULTILINE)
    ]
    assert proposition_numbers == [1, 2]
    assert lemma_numbers == [1, 2, 3, 4]
    assert corollary_numbers == [1, 2]
    assert "**Proposition 7" not in theory

    supplement = SUPPLEMENT.read_text(encoding="utf-8")
    assert "**Remark (set-native degeneracy).**" in supplement
    assert "**Lemma 5 (conditional within-basis bound-endpoint sufficiency).**" in supplement

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
