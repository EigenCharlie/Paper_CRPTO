"""Drift guards for the active IJDS evidence and manuscript surfaces."""

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
RUN = "ijds-binary-geometry-frontier-v4-2026-07-15-v5"
COMMIT = "e2bba580a0b07c145bd64ff61440973d6e31349b"
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

    assert evidence["status"] == "active_ijds_v5_endpoint_reason_audited_paper_facing_evidence"
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
        "primary_oot_resolved": 364814,
        "primary_oot_unresolved": 12076,
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
        "evaluation_endpoint": "terminal_default_reconstructed_as_observable_by_2020-09-30",
        "archive_is_verified_point_in_time_snapshot": False,
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
    assert data["eligible_raw_features"] == 30
    assert data["declared_coverage_exceptions"] == 2
    assert data["coverage_exceptions_requiring_sensitivity"] == 2
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
    assert rows["catboost_monotonic_platt"]["roc_auc"] == pytest.approx(0.6519537792141734)
    assert rows["woe_scorecard_borrower_platt"]["coverage_upper_max"] == pytest.approx(
        0.8977261269866539
    )
    assert controls["calibration"]["optimizer_success_rows"] == 30
    assert controls["calibration"]["all_primary_oot_mean_calibration_error_negative"] is True
    assert controls["calibration"]["all_primary_oot_slopes_below_one"] is True
    assert controls["woe_iv"]["optbinning_problems"] == 45
    assert controls["woe_iv"]["all_optimal"] is True
    assert controls["temporal_shift"]["primary_oot_score_psi"][
        "woe_scorecard_borrower_platt"
    ] == pytest.approx(0.07233216453444681)
    assert coverage["catboost_all_eight_upper_below_nominal"] is True
    assert coverage["logistic_all_eight_upper_below_nominal"] is True
    assert coverage["catboost_bound_min"] == pytest.approx(0.8424845445620738)
    assert coverage["catboost_bound_max"] == pytest.approx(0.8825970442304121)
    assert coverage["logistic_bound_min"] == pytest.approx(0.8500305128817427)
    assert coverage["logistic_bound_max"] == pytest.approx(0.8962217092520364)
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
    assert phase["w8_oot_coverage_bound"] == pytest.approx([0.8225359596189609, 0.8547066934861538])
    lag = phase["label_lag_sensitivity"]
    assert lag["admissible_lags_months"] == [0, 3, 6]
    assert lag["nonadmissible_lags_months"] == [8, 12]
    assert lag["w7_to_w8_threshold_crossing_at_all_admissible_lags"] is True
    assert lag["crossing_disappears_outside_locked_retention_scope"] is True
    assert lag["causal_interpretation_authorized"] is False

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
        ("funded_miscoverage", "crosses_zero"): 45,
        ("funded_miscoverage", "guardrail_higher"): 27,
        ("standardized_payoff", "crosses_zero"): 66,
        ("standardized_payoff", "guardrail_lower"): 6,
        ("terminal_default", "crosses_zero"): 72,
    }
    tie = portfolio["evaluated_point_cap_solver_stability"]
    assert tie["point_cap_rows"] == 7297
    assert tie["near_zero_bases"] == 0
    assert tie["tie_sensitive_rows"] == 0
    assert tie["continuous_frontier_uniqueness_claim"] is False


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
        "outcome_audit_rows": 8,
    }
    assert challenger["primary_oot_unresolved"] == 12076
    assert challenger["manifest"]["sha256"] == (
        "9ee55a2522349c8520f308bc69273774dd48964847dfd340b78a7be46474cd7f"
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
    assert quarter["payoff_bound_usd_lower_min"] == pytest.approx(-9134.339201705214)
    assert quarter["payoff_bound_usd_upper_max"] == pytest.approx(5603.660798333496)
    assert quarter["default_bound_pp_upper_max"] == pytest.approx(0.12654340602615935)
    assert quarter["payoff_direction_pattern"] == "crosses_zero:8"
    assert quarter["default_direction_pattern"] == "crosses_zero:8"
    assert quarter["miscoverage_direction_pattern"] == "crosses_zero:8"

    half = rows[("objective_matched", 0.5)]
    assert half["payoff_bound_usd_upper_max"] < 0.0
    assert half["default_bound_pp_lower_min"] > 0.0
    assert half["miscoverage_bound_pp_lower_min"] > 0.0

    three_quarters = rows[("objective_matched", 0.75)]
    assert three_quarters["payoff_direction_pattern"] == "gamma_1_lower:1;crosses_zero:7"
    assert three_quarters["default_direction_pattern"] == "gamma_1_higher:1;crosses_zero:7"
    assert three_quarters["miscoverage_direction_pattern"] == "gamma_1_higher:8"

    normalized = [row for key, row in rows.items() if key[0] == "normalized_score"]
    assert all(row["payoff_bound_usd_upper_max"] < 0.0 for row in normalized[:2])
    assert normalized[2]["payoff_direction_pattern"] == "gamma_1_lower:7;crosses_zero:1"
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


def test_endpoint_availability_sensitivity_is_complete_and_nonselective() -> None:
    sensitivity = _json(EVIDENCE)["sensitivity"]["evaluation_endpoint_availability"]

    assert sensitivity["charged_off_lags_months"] == [0, 3, 6, 8, 12]
    assert sensitivity["endpoint_or_result_selected"] is False
    assert sensitivity["allocation_refit"] is False
    assert sensitivity["six_month_endpoint_reconciles_to_active_evaluation"] is True
    assert sensitivity["fit_label_lag_crossed_factorially"] is False
    assert len(sensitivity["rows"]) == 5
    assert {row["charged_off_lag_months"] for row in sensitivity["rows"]} == {
        0,
        3,
        6,
        8,
        12,
    }


def test_portfolio_structure_sensitivity_is_complete_and_nonselective() -> None:
    sensitivity = _json(EVIDENCE)["sensitivity"]["portfolio_structure"]

    assert sensitivity["scenario_count"] == 36
    assert sensitivity["complete_cartesian_grid"] is True
    assert sensitivity["scenario_or_result_selected"] is False
    assert sensitivity["baseline_reconciles_to_active_evaluation"] is True
    assert sensitivity["every_scenario_has_adverse_default_and_miscoverage_cells"] is True
    assert sensitivity["minimum_adverse_default_cells_per_scenario"] == 17
    assert sensitivity["minimum_adverse_miscoverage_cells_per_scenario"] == 21
    assert sensitivity["universally_favorable_scenarios"] == 0
    assert sensitivity["universally_adverse_scenarios"] == 0
    assert sensitivity["scenarios_with_any_favorable_payoff_cell"] == 26
    assert sensitivity["scenarios_with_any_favorable_default_cell"] == 20
    assert sensitivity["scenarios_with_any_favorable_miscoverage_cell"] == 20
    assert sensitivity["portfolios_per_scenario"] == 1440
    assert sensitivity["purpose_cap_binding_share_by_cap"] == {
        "0.20": 1.0,
        "0.25": 1.0,
        "0.30": 1.0,
        "1.00": 0.0,
    }
    assert sensitivity["maximum_loan_weight_by_budget"] == {
        "500000": 0.08,
        "1000000": 0.04,
        "2000000": 0.02,
    }
    assert len(sensitivity["rows"]) == 36


def test_endpoint_reasons_missingness_and_second_origin_are_bounded() -> None:
    evidence = _json(EVIDENCE)
    endpoint = evidence["evaluation_endpoint"]
    assert endpoint["reason_census_partitions_primary_candidates"] is True
    assert endpoint["primary_oot_nonterminal_or_unresolved_status"] == 11551
    assert endpoint["primary_oot_terminal_after_cutoff"] == 47
    assert endpoint["primary_oot_terminal_availability_date_missing"] == 478
    assert endpoint["missingness_mechanism_identified"] is False

    missingness = evidence["sensitivity"]["missingness_encoding"]
    assert missingness["all_three_all_eight_upper_below_nominal"] is True
    assert missingness["model_or_encoding_selected"] is False
    assert missingness["missingness_mechanism_identified"] is False
    assert missingness["portfolio_claim_authorized"] is False
    assert len(missingness["rows"]) == 3

    rolling = evidence["sensitivity"]["rolling_origin"]
    assert rolling["origin_count"] == 2
    assert rolling["window_cells"] == 16
    assert rolling["all_sixteen_upper_below_nominal"] is True
    assert rolling["model_or_origin_selected"] is False
    assert rolling["independent_replication_claim_authorized"] is False


def test_fit_label_completion_and_allocation_granularity_are_bounded() -> None:
    evidence = _json(EVIDENCE)
    fit = evidence["sensitivity"]["fit_label_completion"]
    assert fit["unavailable_fit_labels_total"] == 215
    assert fit["unavailable_fit_labels_by_split"] == {
        "pd_development": 41,
        "probability_calibration": 24,
        "conformal_fit": 150,
    }
    assert fit["all_scenarios_all_windows_upper_below_nominal"] is True
    assert fit["w7_w8_crossing_scenarios"] == 3
    assert fit["w7_w8_crossing_in_all_scenarios"] is False
    assert fit["scenarios_are_sharp_bounds_over_all_label_assignments"] is False
    assert fit["scenario_or_result_selected"] is False
    assert len(fit["rows"]) == 4

    granularity = evidence["sensitivity"]["allocation_granularity"]
    assert granularity["portfolios"] == 1440
    assert granularity["tracks"] == 96
    assert granularity["source_rows"] == 143175
    assert granularity["changed_rows"] == 2985
    assert granularity["cash_share_max"] < 3.4e-5
    assert granularity["default_rate_perturbation_abs_max"] < 1.3e-5
    assert granularity["integer_policy_or_reoptimization_claim_authorized"] is False


def test_evidence_manifest_hashes_every_active_output() -> None:
    evidence = _json(EVIDENCE)

    assert {
        "active_source_registry",
        "evidence_builder",
        "source_registry_loader",
        "claim_ledger_contract",
        "claim_ledger_loader",
        "endpoint_availability_sensitivity/summary",
        "endpoint_availability_sensitivity/loader",
        "portfolio_structure_sensitivity/summary",
        "portfolio_structure_sensitivity/loader",
        "robustness_sensitivities/loader",
        "artifact_descriptor_helper",
        "outcome_free/source_protocol_freeze",
        "two_ruler/outcome_free/freeze",
        "credit_controls/freeze",
    }.issubset(evidence["source_artifacts"])
    assert evidence["paper_artifacts"]
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
        "364,814",
        "12,076",
        "307,842",
        "56,972",
        "478",
        "6,240",
        "9,134.34",
        "5,603.66",
        "14,738",
        "155,937.27",
        "44 loan-month positions",
        "0.1017",
        "0.0971",
        "0.8884",
        "0.1118",
        "215",
        "0.884669",
        "2,985",
        "0.001284",
        "3,067",
        "216",
        "72",
        "0.884332",
        "0.874768",
        "status-indexed",
        "selected-set",
    )
    retired = (
        "0.879647",
        "0.845072",
        "0.870973",
        "7 of 9",
        "5 of 9",
        "selected guardrail",
        "all nine policies are co-primary",
        "$179,327.59",
        "active v3",
        "endpoint-recovery direction reconciliation",
    )
    for surface in SURFACES:
        text = _normalize(surface.read_text(encoding="utf-8"))
        assert not [token for token in active if _normalize(token) not in text], surface
        assert not [token for token in retired if _normalize(token) in text], surface


def test_official_tex_is_deterministically_generated_from_qmd() -> None:
    assert render_submission_tex(check=True)
