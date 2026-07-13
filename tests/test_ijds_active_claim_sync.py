"""Drift guards for the active V4, two-ruler, and credit-control evidence."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

from scripts.build_ijds_submission_tex import render_submission_tex

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json"
RUN = "ijds-binary-geometry-frontier-v4-2026-07-12-v2"
COMMIT = "60cdf298d965525cddaaf03abccd15ff805e1a15"
SURFACES = (
    REPO / "paper/CRPTO_ijds.qmd",
    REPO / "paper/supplement_ijds.qmd",
    REPO / "paper/submission/CRPTO_ijds_submission.tex",
)


def _json(path: Path) -> dict[str, Any]:
    assert path.is_file(), path
    return json.loads(path.read_text(encoding="utf-8"))


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
        "{": "",
        "}": "",
        "`": "",
    }.items():
        value = value.replace(old, new)
    return re.sub(r"\s+", " ", value)


def test_active_evidence_locks_v4_lineage_and_claim_boundary() -> None:
    evidence = _json(EVIDENCE)

    assert evidence["status"] == (
        "active_ijds_v4_two_ruler_and_credit_controls_paper_facing_evidence"
    )
    assert evidence["run_tag"] == RUN
    assert evidence["protocol_commit"] == COMMIT
    assert evidence["claim_boundary"] == {
        "previously_inspected_archive": True,
        "confirmatory": False,
        "prospective": False,
        "causal": False,
        "selected_set_validity": False,
        "policy_winner": False,
        "nested_scopes_are_independent_replications": False,
    }
    assert evidence["protected_stages_run"] == []
    assert evidence["protected_artifacts_written"] == []


def test_active_design_is_exact() -> None:
    evidence = _json(EVIDENCE)
    design = evidence["design"]

    assert design == {
        "primary_oot_candidates": 376890,
        "primary_oot_resolved": 365339,
        "primary_oot_unresolved": 11551,
        "residual_windows": 8,
        "learners": 5,
        "v4_detailed_coverage_learners": 2,
        "credit_control_learners": 5,
        "portfolio_learners": 1,
        "taxonomy_diagnostics": [1, 2, 5, 10],
        "policies": 9,
        "v4_policies_are_supporting_not_closed_family": True,
        "oot_months": 15,
        "development_months": 11,
        "two_ruler_gamma_grid": [0.0, 0.25, 0.5, 0.75, 1.0],
        "two_ruler_primary_contrast": "gamma_1_minus_gamma_0",
        "two_ruler_interior_coordinates": [0.25, 0.5, 0.75],
        "two_ruler_tracks": 6,
        "frontier_caps": 3067,
        "development_support_lower": pytest.approx(0.0555726278946077),
        "development_support_upper": pytest.approx(0.09999720664228194),
    }


def test_full_data_contract_credit_controls_and_coverage_are_exact() -> None:
    evidence = _json(EVIDENCE)
    data = evidence["data_contract"]
    controls = evidence["credit_risk_controls"]
    coverage = evidence["coverage"]

    assert data["raw_rows"] == 2925493
    assert data["valid_loan_rows"] == 2925492
    assert data["term36_rows_all_dates"] == 2060077
    assert data["term60_rows_all_dates"] == 865415
    assert data["active_design_rows"] == 640543
    assert data["raw_schema_columns"] == 142
    assert data["eligible_raw_features"] == 28
    assert data["late_schema_features"] == 48
    assert data["sampling"] == "none_all_eligible_rows_within_each_declared_temporal_role"

    assert controls["all_five_all_eight_upper_below_nominal"] is True
    assert controls["controls_enter_portfolio_optimization"] is False
    assert controls["model_or_feature_selected_from_oot"] is False
    assert controls["scorecard_superiority_claim_authorized"] is False
    rows = {row["learner"]: row for row in controls["rows"]}
    assert set(rows) == {
        "catboost_platt",
        "numeric_logistic_platt",
        "catboost_monotonic_platt",
        "woe_scorecard_platform_platt",
        "woe_scorecard_borrower_platt",
    }
    assert all(row["windows_upper_below_0_90"] == 8 for row in rows.values())
    assert rows["catboost_monotonic_platt"]["roc_auc"] == pytest.approx(0.6522442096629454)
    assert rows["woe_scorecard_borrower_platt"]["coverage_upper_max"] == pytest.approx(
        0.8969725914723129
    )
    assert controls["calibration"]["optimizer_success_rows"] == 30
    assert controls["calibration"]["all_primary_oot_slopes_below_one"] is True
    assert controls["woe_iv"]["optbinning_problems"] == 45
    assert controls["woe_iv"]["all_optimal"] is True
    assert controls["temporal_shift"]["primary_oot_score_psi"][
        "woe_scorecard_borrower_platt"
    ] == pytest.approx(0.07233216453444681)
    assert coverage["catboost_all_eight_upper_below_nominal"] is True
    assert coverage["logistic_all_eight_upper_below_nominal"] is True
    assert coverage["catboost_bound_min"] == pytest.approx(0.8385311364058479)
    assert coverage["catboost_bound_max"] == pytest.approx(0.8821672105919499)
    assert coverage["logistic_bound_min"] == pytest.approx(0.8456870704980233)
    assert coverage["logistic_bound_max"] == pytest.approx(0.895653904322216)
    rows = coverage["rows"]
    assert len(rows) == 16
    assert {row["learner"] for row in rows} == {
        "catboost_platt",
        "numeric_logistic_platt",
    }
    assert {row["window_id"] for row in rows} == {
        f"w{index:02d}_" + suffix
        for index, suffix in enumerate(
            (
                "2012m01_m06",
                "2012m02_m07",
                "2012m03_m08",
                "2012m04_m09",
                "2012m05_m10",
                "2012m06_m11",
                "2012m07_m12",
                "2012m08_2013m01",
            ),
            start=1,
        )
    }


def test_phase_transition_and_portfolio_boundary_are_exact() -> None:
    evidence = _json(EVIDENCE)
    phase = evidence["binary_phase_transition"]
    portfolio = evidence["portfolio"]

    assert phase["stratum"] == 2
    assert phase["w7_fit_prevalence"] == pytest.approx(0.10170349131388093)
    assert phase["w8_fit_prevalence"] == pytest.approx(0.0971465213209362)
    assert phase["w7_residual_quantile"] == pytest.approx(0.8884345991499274)
    assert phase["w8_residual_quantile"] == pytest.approx(0.1118010883671265)
    assert phase["w7_mean_width"] == pytest.approx(0.9842633701640714)
    assert phase["w8_mean_width"] == pytest.approx(0.2076312400549422)
    assert phase["w8_oot_coverage_bound"] == pytest.approx([0.8225359596189609, 0.8536819866661607])

    assert portfolio["c2_cells"] == 1080
    assert portfolio["c2_match_residual_abs_max"] < 1e-16
    assert portfolio["c2_point_minus_guardrail_objective_min"] > -1e-5
    assert portfolio["broad_stress_all_envelopes_cross_zero"] is True
    assert portfolio["broad_stress_cells"] == 216
    assert portfolio["w8_development_all_envelopes_cross_zero"] is True
    counts = {
        (row["metric"], row["direction"]): row["cells"]
        for row in portfolio["development_direction_counts"]
    }
    assert counts == {
        ("funded_miscoverage", "crosses_zero"): 33,
        ("funded_miscoverage", "guardrail_higher"): 39,
        ("standardized_payoff", "crosses_zero"): 51,
        ("standardized_payoff", "guardrail_lower"): 21,
        ("terminal_default", "crosses_zero"): 72,
    }


def test_two_ruler_diagnostic_is_finite_complete_and_nonselective() -> None:
    challenger = _json(EVIDENCE)["decision_challenger"]

    assert challenger["scope"] == "finite_two_ruler_three_interior_coordinate_diagnostic"
    assert challenger["continuous_frontier_claim"] is False
    assert challenger["tracks_are_independent_replications"] is False
    assert challenger["endpoint_contrast"] == "gamma_1_minus_gamma_0"
    assert challenger["counts"] == {
        "evaluated_portfolios": 6240,
        "joined_funded_rows": 622455,
        "window_endpoint_contrasts": 48,
        "monthly_endpoint_contrasts": 720,
        "metric_direction_cells": 144,
        "outcome_audit_rows": 5,
    }
    assert challenger["primary_oot_unresolved"] == 11551
    assert challenger["manifest"]["sha256"] == (
        "d3808ce7c7a8e6fee3ef51aefd031e8abf55e11ef3536745ee213fd04752588a"
    )

    rows = {(row["ruler"], row["coordinate"]): row for row in challenger["rows"]}
    assert set(rows) == {
        (ruler, coordinate)
        for ruler in ("objective_matched", "normalized_score")
        for coordinate in (0.25, 0.5, 0.75)
    }
    quarter = rows[("objective_matched", 0.25)]
    assert quarter["active_months_per_window_min"] == 4
    assert quarter["active_months_per_window_max"] == 4
    assert quarter["payoff_bound_usd_lower_min"] == pytest.approx(5603.660798294787)
    assert quarter["default_bound_pp_upper_max"] == pytest.approx(-0.006789927307173987)

    half = rows[("objective_matched", 0.5)]
    assert half["payoff_bound_usd_upper_max"] < 0.0
    assert half["default_bound_pp_lower_min"] > 0.0
    assert half["miscoverage_bound_pp_lower_min"] > 0.0

    three_quarters = rows[("objective_matched", 0.75)]
    assert three_quarters["payoff_direction_pattern"] == "gamma_1_lower:1;crosses_zero:7"
    assert three_quarters["default_direction_pattern"] == "gamma_1_higher:1;crosses_zero:7"
    assert three_quarters["miscoverage_direction_pattern"] == "gamma_1_higher:8"

    normalized = [row for key, row in rows.items() if key[0] == "normalized_score"]
    assert all(row["payoff_bound_usd_upper_max"] < 0.0 for row in normalized)
    assert all(row["default_bound_pp_lower_min"] > 0.0 for row in normalized)
    assert all(row["miscoverage_bound_pp_lower_min"] > 0.0 for row in normalized)

    repetition = challenger["objective_matched_coordinate_025_repetition"]
    assert repetition["allocations_identical_across_windows_to_cents"] is True
    assert repetition["changed_loan_month_positions_min"] == 44
    assert repetition["changed_loan_month_positions_max"] == 44
    assert repetition["one_way_turnover_usd_min"] == pytest.approx(155937.26968238514)

    interpretation = challenger["interpretation"]
    assert interpretation["normalized_score_equalizes_opportunity_cost"] is False
    assert interpretation["preferred_gamma"] is None
    assert interpretation["preferred_ruler"] is None
    assert interpretation["preferred_coordinate"] is None
    assert interpretation["policy_winner"] is None


def test_simulation_is_explicitly_non_claim_bearing_for_portfolios() -> None:
    simulation = _json(EVIDENCE)["simulation"]

    assert simulation["scope"] == "coverage_mechanism_only_portfolio_component_degenerate"
    assert simulation["repetitions"] == 19200
    assert simulation["cells"] == 192
    assert simulation["portfolio_claim_allowed"] is False
    assert simulation["same_cap_allocation_distance_mean"] == pytest.approx(2.083333333e-6)
    assert simulation["c2_allocation_distance_mean"] == pytest.approx(1.041666667e-6)


def test_evidence_manifest_hashes_every_active_output() -> None:
    evidence = _json(EVIDENCE)

    assert len(evidence["source_artifacts"]) == 69
    assert len(evidence["paper_artifacts"]) == 16
    for descriptor in (
        *evidence["source_artifacts"].values(),
        *evidence["paper_artifacts"].values(),
    ):
        path = REPO / descriptor["path"]
        assert path.is_file(), path
        assert path.stat().st_size == descriptor["bytes"]
        assert _sha256(path) == descriptor["sha256"]


def test_manuscript_surfaces_share_v4_claims_and_retire_old_headlines() -> None:
    active = (
        "376,890",
        "11,551",
        "6,240",
        "5,603.66",
        "155,937.27",
        "44 loan-month positions",
        "0.1017",
        "0.0971",
        "0.8884",
        "0.1118",
        "3,067",
        "216",
        "72",
        "standardized payoff",
        "selected-set",
    )
    retired = (
        "0.854714",
        "0.879647",
        "0.845072",
        "0.870973",
        "7 of 9",
        "5 of 9",
        "selected guardrail",
        "all nine policies are co-primary",
        "$179,327.59",
    )
    for surface in SURFACES:
        text = _normalize(surface.read_text(encoding="utf-8"))
        assert not [token for token in active if _normalize(token) not in text], surface
        assert not [token for token in retired if _normalize(token) in text], surface


def test_official_tex_is_deterministically_generated_from_qmd() -> None:
    assert render_submission_tex(check=True)
