"""Drift guards for the active fixed-taxonomy IJDS evidence and manuscripts."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

from scripts.build_ijds_submission_tex import render_submission_tex

REPO = Path(__file__).resolve().parents[1]
TABLES = REPO / "reports/crpto/tables"
EVIDENCE = REPO / "reports/crpto/ijds_fixed_taxonomy_c2_evidence.json"
OUTCOME_FREE_RUN = "ijds-fixed-taxonomy-c2-2026-07-11-v1"
EVALUATION_RUN = "ijds-fixed-taxonomy-c2-2026-07-11-v2"
OUTCOME_FREE_COMMIT = "4835cc18a0117a695f89f9da70a4e3af97663a27"
EVALUATION_COMMIT = "a88839dfe14875fca2c02c43725291bc49d98611"
OUTCOME_FREE_FREEZE = "93690082880ef4ff1375dcd5b26d2df79f80e6ebe09a6d83b7fd99a9abb4cfae"
SURFACES = (
    REPO / "paper/CRPTO_ijds.qmd",
    REPO / "paper/supplement_ijds.qmd",
    REPO / "paper/submission/CRPTO_ijds_submission.tex",
)


def _json(path: Path) -> dict[str, Any]:
    assert path.is_file(), f"Missing JSON evidence: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(stem: str) -> list[dict[str, str]]:
    with (TABLES / f"{stem}.csv").open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize(text: str) -> str:
    value = text.lower()
    for old, new in {
        r"\$": "$",
        r"\%": "%",
        r"\_": "_",
        "{,}": ",",
        "{[}": "[",
        "{]}": "]",
        "{": "",
        "}": "",
        "`": "",
    }.items():
        value = value.replace(old, new)
    return re.sub(r"\s+", " ", value)


def test_active_evidence_locks_v1_outcome_free_lineage_and_v2_evaluation() -> None:
    evidence = _json(EVIDENCE)
    source = evidence["outcome_free_source"]

    assert evidence["status"] == "complete_reconciled_paper_evidence"
    assert evidence["run_tag"] == EVALUATION_RUN
    assert evidence["protocol_commit"] == EVALUATION_COMMIT
    assert source["source_run_tag"] == OUTCOME_FREE_RUN
    assert source["source_protocol_commit"] == OUTCOME_FREE_COMMIT
    assert source["source_protocol_freeze"]["sha256"] == OUTCOME_FREE_FREEZE
    assert source["reuse_scope"] == "outcome_free_predictions_models_and_allocations_only"
    assert evidence["claim_boundary"] == {
        "previously_inspected_archive": True,
        "confirmatory": False,
        "prospective": False,
        "causal": False,
        "selected_set_validity": False,
        "all_nine_policies_primary": True,
    }


def test_active_headline_is_exact_and_does_not_promote_a_winner() -> None:
    evidence = _json(EVIDENCE)
    headline = evidence["headline"]
    decision = evidence["decision"]

    assert headline["conformal_fit_coverage_seed_42"] == pytest.approx(0.9003880117741504)
    assert headline["primary_all_candidate_coverage"] == pytest.approx(
        [0.8547135769057285, 0.8796465812305978]
    )
    assert headline["canonical_c2_direction_counts"] == {
        "payoff_worse": 7,
        "default_higher": 1,
        "miscoverage_higher": 8,
        "policies": 9,
    }
    assert headline["comparator_multiverse_envelopes_indeterminate"] == 27
    assert headline["comparator_multiverse_envelopes_total"] == 27
    assert headline["c2_max_funded_pd_match_residual"] < 5e-17
    assert headline["purpose_caps_below_one_bind_every_guardrail_month"] is True
    assert decision["universal_guardrail_direction_allowed"] is False
    assert decision["policy_winner_allowed"] is False
    assert decision["selected_set_validity_allowed"] is False
    assert decision["current_superiority_submission_go"] is False
    assert decision["ijds_audit_narrative_go"] is True
    assert decision["post_result_audit_framing"] is True
    assert decision["prespecified_negative_fallback"] is False


def test_direction_and_sensitivity_tables_match_headline() -> None:
    directions = {
        row["comparator_rule"]: row for row in _rows("crpto_ijds_ft_table4_direction_summary")
    }
    c0 = directions["c0_same_numeric_cap"]
    c2 = directions["c2_contemporaneous"]
    envelope = directions["finite_multiverse_envelope"]

    assert (int(c0["payoff_positive"]), int(c0["default_negative"])) == (9, 9)
    assert (
        int(c2["payoff_negative"]),
        int(c2["default_positive"]),
        int(c2["miscoverage_positive"]),
    ) == (7, 1, 8)
    assert (
        int(envelope["payoff_indeterminate"]),
        int(envelope["default_indeterminate"]),
        int(envelope["miscoverage_indeterminate"]),
    ) == (9, 9, 9)

    sensitivity = _rows("crpto_ijds_ft_tableS1_seed_cap_sensitivity")
    assert len(sensitivity) == 180
    assert {int(row["seed"]) for row in sensitivity} == {40, 41, 42, 43, 44}
    assert {float(row["purpose_cap"]) for row in sensitivity} == {0.2, 0.25, 0.3, 1.0}


def test_multiverse_binding_and_endpoint_diagnostics_are_derived() -> None:
    evidence = _json(EVIDENCE)

    envelopes = evidence["canonical_comparator_envelopes"]
    assert len(envelopes) == 27
    assert {row["paired_policy_id"] for row in envelopes} == {
        f"linear-{index:03d}" for index in range(1, 10)
    }
    assert {row["metric"] for row in envelopes} == {
        "realized_payoff",
        "terminal_default",
        "funded_miscoverage",
    }
    assert {row["sign"] for row in envelopes} == {"indeterminate"}
    assert {int(row["record_count"]) for row in envelopes} == {32}

    binding = evidence["purpose_cap_binding"]
    assert binding["guardrail_months"] == 2025
    assert binding["binding_guardrail_months"] == 2025
    assert binding["all_bind"] is True
    assert binding["maximum_absolute_cap_residual"] < 2e-16

    inventory = evidence["endpoint_inventory"]
    assert inventory["terminal_endpoint"]["resolved_rows"] == 499845
    assert inventory["terminal_endpoint"]["unresolved_rows"] == 40276
    assert inventory["frozen_status_diagnostic"] == {
        "resolved_rows": 500019,
        "unresolved_rows": 40102,
    }
    assert inventory["literal_default_rows_reclassified_unresolved"] == 174


def test_archive_ablation_distances_reconcile_to_frozen_allocations() -> None:
    rows = _rows("crpto_ijds_ft_tableS4_group_ablation")
    clipping = [float(row["clipped_vs_unclipped_allocation_l1"]) for row in rows]
    taxonomy = [float(row["unclipped_group_vs_pooled_allocation_l1"]) for row in rows]
    affine = [float(row["pooled_affine_vs_point_allocation_l1"]) for row in rows]

    assert min(clipping) == pytest.approx(4684.843282767612)
    assert max(clipping) == pytest.approx(46609.497902620766)
    assert min(taxonomy) == pytest.approx(9849022.183609739)
    assert max(taxonomy) == pytest.approx(21351895.344954066)
    assert max(affine) == pytest.approx(0.0, abs=1e-12)


def test_coverage_table_contains_all_fixed_taxonomies_and_unresolved_rows() -> None:
    coverage = _rows("crpto_ijds_ft_table2_coverage")
    primary = [row for row in coverage if row["design_split"] == "primary_oot"]

    assert {int(row["taxonomy_groups"]) for row in primary} == {1, 2, 5, 10}
    assert {int(row["rows"]) for row in primary} == {376890}
    assert {int(row["unresolved_rows"]) for row in primary} == {11551}
    assert max(float(row["all_candidate_coverage_upper"]) for row in primary) == pytest.approx(
        0.88194221650349
    )


def test_evidence_manifest_hashes_all_publication_outputs() -> None:
    evidence = _json(EVIDENCE)
    outputs = evidence["publication_artifacts"]

    assert len(outputs) == 62
    for relative, descriptor in outputs.items():
        path = REPO / relative
        assert path.is_file(), path
        assert path.stat().st_size == descriptor["bytes"]
        assert _sha256(path) == descriptor["sha256"]

    provenance = evidence["build_provenance"]
    assert provenance["hash_algorithm"] == "sha256"
    assert set(provenance["source_files"]) == {
        "evidence_builder",
        "temporal_evidence_module",
        "environment_lock",
    }
    for descriptor in provenance["source_files"].values():
        path = REPO / descriptor["path"]
        assert path.stat().st_size == descriptor["bytes"]
        assert _sha256(path) == descriptor["sha256"]


def test_temporal_design_sensitivity_is_locked_and_does_not_select_a_window() -> None:
    temporal = _json(EVIDENCE)["temporal_design_sensitivity"]

    assert temporal["status"] == "complete_locked_design_sensitivity"
    assert temporal["run_tag"] == "ijds-fixed-taxonomy-c2-temporal-v3-2026-07-12-v1"
    assert temporal["protocol_commit"] == "c5ceab737ab3cda8aed7d3c1fd24a506418cfa35"
    assert temporal["no_result_based_promotion"] is True
    assert temporal["development_supported_point_cap_range"] == pytest.approx(
        {
            "lower": 0.06,
            "upper": 0.0825,
            "step": 0.0025,
            "target_minimum": 0.0600396539710651,
            "target_maximum": 0.0814989466504543,
            "target_count": 9,
        }
    )

    equivalence = temporal["code_path_equivalence"]
    assert equivalence["point_predictions"] == {
        "common_oot_rows": 465117,
        "maximum_absolute_pd_point_difference": 0.0,
        "exact": True,
    }
    assert equivalence["point_policy_allocations"]["canonical_point_policy_cells"] == 570
    assert equivalence["point_policy_allocations"]["maximum_absolute_exposure_difference"] == 0.0
    assert equivalence["point_policy_allocations"]["total_allocation_l1_difference"] == 0.0
    assert equivalence["point_policy_allocations"]["exact"] is True


def test_temporal_tables_capture_window_lag_and_comparator_sensitivity() -> None:
    windows = _rows("crpto_ijds_ft_tableS8_temporal_windows")
    five_group = {row["window_id"]: row for row in windows if int(row["taxonomy_groups"]) == 5}
    assert set(five_group) == {"early_2012h1", "late_2012h2_2013m1"}
    assert float(five_group["early_2012h1"]["all_candidate_coverage_lower"]) == pytest.approx(
        0.8547135769057285
    )
    assert float(five_group["late_2012h2_2013m1"]["all_candidate_coverage_upper"]) == (
        pytest.approx(0.8709729628676759)
    )
    assert max(float(row["all_candidate_coverage_upper"]) for row in windows) < 0.90

    lags = _rows("crpto_ijds_ft_tableS9_label_lags")
    assert {int(row["charged_off_lag_months"]) for row in lags} == {0, 3, 6, 12}
    assert max(float(row["all_candidate_coverage_upper"]) for row in lags) < 0.90

    directions = _rows("crpto_ijds_ft_tableS10_timing_directions")
    assert len(directions) == 18
    payoff = {
        row["window_id"]: row
        for row in directions
        if row["metric"] == "realized_payoff" and row["comparator_rule"] == "c2_contemporaneous"
    }
    assert int(payoff["early_2012h1"]["negative"]) == 7
    assert int(payoff["late_2012h2_2013m1"]["negative"]) == 5

    scopes = _rows("crpto_ijds_ft_tableS11_comparator_scopes")
    assert len(scopes) == 9
    assert {row["scope"] for row in scopes} == {
        "core_rules",
        "development_supported",
        "broad_stress",
    }
    assert {int(row["indeterminate"]) for row in scopes} == {9}

    late_c2 = _rows("crpto_ijds_ft_tableS13_late_c2_contrasts")
    scope_envelopes = _rows("crpto_ijds_ft_tableS14_comparator_scope_envelopes")
    assert len(late_c2) == 9
    assert len(scope_envelopes) == 81
    assert {row["sign"] for row in scope_envelopes} == {"indeterminate"}


def test_manuscript_surfaces_share_active_claims_and_retire_p1_c1_headlines() -> None:
    active = (
        "465,117",
        "0.900388",
        "0.900174",
        "0.854714",
        "0.879647",
        "0.845072",
        "0.870973",
        "7 of 9",
        "5 of 9",
        "180",
        "2,025",
        "27",
        "0.0600",
        "0.0825",
        "81",
        "62",
        "standardized payoff",
        "selected-set",
        "not a prospective",
    )
    retired = (
        "0.854923",
        "0.879692",
        "0.068313",
        "295,967.17",
        "506,587.03",
        "selected guardrail",
    )
    for surface in SURFACES:
        text = _normalize(surface.read_text(encoding="utf-8"))
        assert not [token for token in active if _normalize(token) not in text], surface
        assert not [token for token in retired if _normalize(token) in text], surface


def test_manuscript_discloses_post_result_pivot_and_correct_label_cutoff() -> None:
    body = _normalize((REPO / "paper/CRPTO_ijds.qmd").read_text(encoding="utf-8"))
    supplement = _normalize((REPO / "paper/supplement_ijds.qmd").read_text(encoding="utf-8"))

    assert "present negative audit framing was formulated after observing that stop" in body
    assert "information cutoff of march 31, 2016" in body
    assert "the reference recipe uses 2012h1" in body
    assert "the timing sensitivity uses july 2012--january 2013" in body
    assert "labels observable by the end of 2012h1" not in body
    assert "audit interpretation in the paper was developed after observing that failure" in (
        supplement
    )
    assert "identity s1 (binary interval geometry)" in supplement
    for surface in (body, supplement):
        assert "represented by its convex hull" not in surface
        assert "calibrated probability of default" not in surface
    assert "nor the convex hull of a discrete prediction set" in supplement


def test_body_and_generated_tex_share_architecture_citations_and_displays() -> None:
    body = SURFACES[0].read_text(encoding="utf-8")
    official = SURFACES[2].read_text(encoding="utf-8")
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

    body_positions = [body.index(f"# {section}") for section in sections]
    tex_positions = [official.index(rf"\section{{{section}}}") for section in sections]
    assert body_positions == sorted(body_positions)
    assert tex_positions == sorted(tex_positions)
    assert "abstract: |" in body
    assert r"\ABSTRACT{" in official

    body_citations = {
        key
        for key in re.findall(r"@([A-Za-z0-9_:-]+)", body)
        if not key.startswith(("fig-", "tbl-", "eq-", "sec-"))
    }
    tex_citations: set[str] = set()
    for group in re.findall(r"\\cite\w*\{([^}]+)\}", official):
        tex_citations.update(key.strip() for key in group.split(","))
    assert body_citations == tex_citations
    assert len(body_citations) == 41
    assert body.count("{#tbl-") == official.count(r"\begin{longtable}") == 7
    assert body.count("{#fig-") == official.count(r"\begin{figure}") == 3


def test_official_tex_is_deterministically_generated_from_qmd() -> None:
    assert render_submission_tex(check=True)
