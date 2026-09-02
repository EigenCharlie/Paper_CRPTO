"""Drift guards for the active IJDS evidence and manuscript surfaces."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts import extend_ijds_evidence_from_sealed_parent_2026_09_01 as support_extension
from scripts.build_ijds_submission_tex import render_submission_tex
from src.ijds_audit.publication_sources import load_source_registry

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json"
RUN = "ijds-binary-geometry-frontier-v4-2026-07-15-v5"
COMMIT = "e2bba580a0b07c145bd64ff61440973d6e31349b"
CLOSED_WINDOW_IDS = (
    "w01_2012m01_m06",
    "w02_2012m02_m07",
    "w03_2012m03_m08",
    "w04_2012m04_m09",
    "w05_2012m05_m10",
    "w06_2012m06_m11",
    "w07_2012m07_m12",
    "w08_2012m08_2013m01",
)
SURFACES = (
    REPO / "paper/CRPTO_ijds.qmd",
    REPO / "paper/supplement_ijds.qmd",
    REPO / "paper/submission/CRPTO_ijds_submission.tex",
)
ACTIVE_DVC_COUNT_SURFACES = (
    REPO / "README.md",
    REPO / "CLAUDE.md",
    REPO / ".codex/skills/crpto/SKILL.md",
    REPO / "docs/security/SECRETS_AND_REMOTES.md",
    REPO / "paper/CRPTO_ijds.qmd",
    REPO / "paper/supplement_ijds.qmd",
    REPO / "paper/submission/CRPTO_ijds_submission.tex",
    REPO / "paper/submission/DATA_CODE_DISCLOSURE_FORM_DRAFT.md",
    REPO / "paper/submission/EDITOR_ONLY_REPRODUCIBILITY_CROSSWALK.md",
    REPO / "paper/submission/REPRODUCIBILITY_PACKAGE.md",
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

    assert evidence["schema_version"] == support_extension.EXTENSION_SCHEMA
    assert evidence["status"] == support_extension.EXTENSION_STATUS
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


def test_active_dvc_pointer_count_is_synchronized_across_release_surfaces() -> None:
    registry = load_source_registry(
        REPO / "configs/ijds_active_evidence_sources.yaml",
        repo_root=REPO,
    )
    expected = len(registry["dvc_pointers"])

    for surface in ACTIVE_DVC_COUNT_SURFACES:
        text = _normalize(surface.read_text(encoding="utf-8"))
        counts = {int(value) for value in re.findall(r"\b(\d+)\s+dvc pointers?\b", text)}
        assert counts == {expected}, surface


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
    assert phase["alpha"] == pytest.approx(0.10)
    assert phase["w7_fit_rows"] == 5929
    assert phase["w8_fit_rows"] == 6238
    assert phase["w7_fit_default_rows"] == 603
    assert phase["w8_fit_default_rows"] == 606
    assert phase["w7_fit_prevalence"] == pytest.approx(0.10170349131388093)
    assert phase["w8_fit_prevalence"] == pytest.approx(0.0971465213209362)
    assert phase["w7_finite_sample_rank"] == 5337
    assert phase["w8_finite_sample_rank"] == 5616
    assert phase["w7_finite_phase_allowance"] == 592
    assert phase["w8_finite_phase_allowance"] == 622
    assert phase["w7_phase_margin"] == 11
    assert phase["w8_phase_margin"] == -16
    assert phase["w7_phase_boundary_rate"] == pytest.approx(592 / 5929)
    assert phase["w8_phase_boundary_rate"] == pytest.approx(622 / 6238)
    assert phase["calibration_scores_below_half_all_windows"] is True
    assert phase["w7_threshold_branch"] == "one_minus_11th_largest_default_score"
    assert phase["w8_fit_nondefault_rows"] == 5632
    assert phase["w8_threshold_branch"] == "5616th_smallest_of_5632_nondefault_scores"
    assert phase["w8_target_score_max"] == pytest.approx(0.11189296397180755)
    assert phase["w8_positive_label_coverage_boundary"] == pytest.approx(1 - 0.1118010883671265)
    assert phase["w8_all_target_scores_below_positive_label_coverage_boundary"] is True
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
    assert portfolio["registered_cap_values_all_envelopes_include_zero"] is True
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
    support = portfolio["policy_support_rhs_semantics"]
    assert support["central_rows"] == 7_297
    assert support["upper_status_rows"] == 7_228
    assert support["basic_status_rows"] == 69
    assert support["v2_semantic_false_failures"] == 66
    assert support["status_aware_cap_containment_passes"] == 7_297
    assert support["registered_support_lower"] == 0.05
    assert support["registered_support_upper"] == 0.12
    assert support["absolute_gap_tolerance"] == 1.0e-10
    assert support["initial_positive_gaps"] == 196
    assert support["registered_gap_seed_solves"] == 196
    assert support["upper_status_gap_seed_solves"] == 196
    assert support["basic_status_gap_seed_solves"] == 0
    assert support["strictly_interior_gap_seed_solves"] == 196
    assert support["maximum_seed_midpoint_match_distance"] < 1.0e-12
    assert support["maximum_v2_seed_expected_objective_difference"] == 0.0
    assert support["maximum_v2_seed_weighted_point_difference"] == 0.0
    assert support["status_aware_seed_cap_containment_passes"] == 196
    assert support["recomputed_target_gap_coverage_passes"] == 196
    assert support["covered_periods"] == 15
    assert support["zero_tolerance_positive_seams"] == 465
    assert support["maximum_zero_tolerance_seam_width"] == pytest.approx(1.6653345369377348e-16)
    assert support["total_zero_tolerance_seam_width"] == pytest.approx(6.6405214660392176e-15)
    assert support["positive_gaps_at_1e_15"] == 0
    assert support["rhs_support_coverage_gate_passed"] is True
    assert support["freeze_reconciliation_rows"] == 7_297
    assert support["freeze_reconciliation_passes"] == 7_297
    assert support["freeze_reconciliation_gate_passed"] is True
    assert support["all_basis_dual_feasibility_contracts_passed"] is True
    assert support["lateral_breakpoint_rows"] == 2_952
    assert support["lateral_probe_paths"] == 5_874
    assert support["lateral_allocation_difference_rows"] == 0
    assert support["maximum_pairwise_allocation_distance"] == pytest.approx(3.078713590737436e-14)
    assert support["corrected_lateral_gate_passed"] is True
    assert support["v2_warning_rows"] == 13
    assert support["v2_unique_warning_targets"] == 8
    assert support["v3a_gap_seed_warning_rows"] == 1
    assert support["v3a_warning_repeats_same_v2_variable_at_both_neighbor_endpoints"] is True
    assert support["maximum_coordinate_exposure_mobility_dollars"] == pytest.approx(
        0.9615019985630913
    )
    assert support["strict_numerical_uniqueness_gate_passed"] is False
    assert support["rhs_coverage_recovered_without_uniqueness_promotion"] is True
    assert support["epsilon_mobility_is_exact_nonuniqueness_evidence"] is False
    assert support["exact_symbolic_optimal_face_claim_active"] is False
    assert support["exact_nonuniqueness_claim_active"] is False
    assert support["allocation_continuity_claim_active"] is False
    assert support["continuous_outcome_envelope_claim_active"] is False


def test_common_panel_response_is_exact_and_bounded() -> None:
    evidence = _json(EVIDENCE)
    common = evidence["common_panel_threshold_response"]

    assert common["full_census_and_identities_verified"] is True
    assert common["stratum_rows"] == 175
    assert common["learner_rows"] == 35
    assert common["stratum_sharp_sign_census"] == {
        "negative": 122,
        "exactly_zero": 5,
        "positive": 48,
    }
    assert common["learner_transition_sharp_sign_census"] == {
        "negative": 31,
        "exactly_zero": 0,
        "positive": 4,
    }
    assert common["cellwise_identification_width"]["median"] == pytest.approx(
        0.00018501007277062863
    )
    assert common["cellwise_identification_width"]["p90"] == pytest.approx(0.0010631809232049042)
    assert common["cellwise_identification_width"]["maximum"] == pytest.approx(0.002346383353779821)
    assert common["interpretation"]["sharpness_is_cellwise"] is True
    assert common["interpretation"]["joint_attainability_of_all_cell_endpoints_claimed"] is False
    assert common["interpretation"]["stratum_sign_census_is_substantive_discovery"] is False


def test_complete_binary_phase_census_is_calibration_only_and_nonselective() -> None:
    phase = _json(EVIDENCE)["binary_phase_census"]

    assert phase["complete_census_verified"] is True
    assert phase["cells"] == 200
    assert phase["global"]["threshold_below_half"] == 87
    assert phase["global"]["phase_margin_nonpositive"] == 87
    assert phase["global"]["half_condition_applicable"] == 184
    assert phase["global"]["source_condition_applicable"] == 188
    assert [row["threshold_below_half"] for row in phase["ordered_conformal_groups"]] == [
        40,
        40,
        7,
        0,
        0,
    ]
    assert len(phase["rows"]) == 200
    assert phase["interpretation"]["target_or_evaluation_endpoint_read"] is False
    assert phase["interpretation"]["universal_phase_law_claimed"] is False


def test_complete_binary_phase_target_support_census_is_bounded() -> None:
    support = _json(EVIDENCE)["binary_phase_target_support"]

    assert support["complete_census_verified"] is True
    assert support["cells"] == 200
    assert support["learner_window_cells"] == 40
    assert support["threshold_below_half_cells"] == 87
    assert support["target_support_cells"] == 87
    assert support["positive_label_exclusion_cells"] == 87
    assert support["phase_margin_prevalence_boundary_reconciles_all_cells"] is True
    assert [
        row["positive_label_excluded_from_every_target_set"]
        for row in support["ordered_stratum_census"]
    ] == [40, 40, 7, 0, 0]
    assert support["exclusion_strata_resolved_miss_fraction_range"] == pytest.approx(
        [0.2397794701677335, 0.5845764027953737]
    )
    interpretation = support["interpretation"]
    assert interpretation["every_positive_label_would_be_missed_in_exclusion_cells"] is True
    assert (
        interpretation["nominal_coverage_impossibility_established_for_all_exclusion_cells"]
        is False
    )
    assert interpretation["stratum_specific_target_prevalence_identified"] is False
    assert interpretation["global_target_prevalence_substituted_for_stratum_prevalence"] is False
    assert interpretation["unconditional_prevalence_only_phase_theorem_claimed"] is False
    assert interpretation["complete_explanation_of_aggregate_shortfall_claimed"] is False


def test_dual_coefficient_frontier_certificate_is_complete_and_bounded() -> None:
    dual = _json(EVIDENCE)["dual_coefficient_binary_set_native"]

    assert dual["complete_certificate_census_verified"] is True
    assert dual["menu_certificates"] == 208
    assert dual["role_menu_certificates"] == {"policy_development": 88, "primary_oot": 120}
    assert dual["new_optimizations"] == 0
    assert dual["all_conditions_certified"] is True
    assert dual["all_maximin_optimizers_singleton_zero"] is True
    assert dual["continuous_cap_frontier_collapses"] is True
    assert dual["cap_domain"] == [0.0, 1.0]
    assert dual["interpretation"]["true_zero_default_risk_claimed"] is False
    assert dual["interpretation"]["optimizer_uniqueness_claimed"] is False
    assert dual["interpretation"]["conformal_validity_repair_claimed"] is False


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


def test_closed_calibrator_family_is_complete_and_nonselective() -> None:
    evidence = _json(EVIDENCE)
    sensitivity = evidence["sensitivity"]["calibrator_family"]

    assert sensitivity["result_state"] == "uniform_closed_family_shortfall_not_established"
    assert sensitivity["methods"] == ["platt", "isotonic", "beta", "venn_abers"]
    assert sensitivity["counts"] == {
        "methods": 4,
        "windows": 8,
        "scopes_per_method_window": 6,
        "evaluation_cells": 192,
        "overall_cells": 32,
        "pairwise_cells": 288,
        "candidate_rows": 376890,
        "resolved_rows": 364814,
        "unresolved_rows": 12076,
        "resolved_y0": 307842,
        "resolved_y1": 56972,
    }
    assert sensitivity["overall_cells_with_coverage_upper_below_nominal"] == 18
    assert sensitivity["overall_cells_with_coverage_upper_at_or_above_nominal"] == 14
    assert sensitivity["overall_result_census_by_method"] == {
        "platt": {"upper_below_nominal": 8, "upper_at_or_above_nominal": 0},
        "isotonic": {"upper_below_nominal": 1, "upper_at_or_above_nominal": 7},
        "beta": {"upper_below_nominal": 8, "upper_at_or_above_nominal": 0},
        "venn_abers": {"upper_below_nominal": 1, "upper_at_or_above_nominal": 7},
    }
    assert len(sensitivity["method_fit_rows"]) == 4
    assert len(sensitivity["cell_rows"]) == 192
    assert len(sensitivity["pairwise_rows"]) == 288
    overall = [row for row in sensitivity["cell_rows"] if int(row["conformal_group"]) == -1]
    assert len(overall) == 32
    assert sum(row["coverage_upper_below_nominal"] is True for row in overall) == 18
    assert sum(row["coverage_upper_below_nominal"] is False for row in overall) == 14
    assert all(row["shared_loanwise_completion"] is True for row in sensitivity["pairwise_rows"])

    interpretation = sensitivity["interpretation"]
    assert interpretation["learner_calibrator_window_or_result_selected"] is False
    assert interpretation["calibrator_winner"] is None
    assert interpretation["selected_calibrator"] is None
    assert interpretation["portfolio_score_changed"] is False
    assert interpretation["portfolio_optimization"] is False
    assert interpretation["portfolio_optimization_run"] is False
    assert interpretation["pre_existing_platt_score_remains_primary_portfolio_score"] is True
    assert interpretation["alternative_calibrator_maps_propagated_to_portfolio"] is False
    assert interpretation["uniform_shortfall_not_established_is_not_true_coverage_dependence"]
    assert interpretation["temporal_transport_established"] is False
    assert interpretation["prospective_transport_established"] is False
    assert (
        interpretation["venn_abers_multiprobability_guarantee_transported_to_scalarization"]
        is False
    )

    expected_artifacts = {
        "table/calibrator_fit_diagnostics": (
            "reports/crpto/tables/crpto_ijds_v4_tableS2C_calibrator_fit_diagnostics.csv"
        ),
        "table/calibrator_sensitivity_cells": (
            "reports/crpto/tables/crpto_ijds_v4_tableS6O_calibrator_sensitivity_cells.csv"
        ),
        "table/calibrator_pairwise_shared_completion": (
            "reports/crpto/tables/crpto_ijds_v4_tableS6P_calibrator_pairwise_shared_completion.csv"
        ),
    }
    for name, path in expected_artifacts.items():
        assert evidence["paper_artifacts"][name]["path"] == path

    calibrator_surfaces = (
        REPO / "paper/CRPTO_ijds.qmd",
        REPO / "paper/supplement_ijds.qmd",
        REPO / "docs/ACADEMIC_CONTEXT.md",
        REPO / "scripts/build_ijds_machine_readable_supplement.py",
    )
    for surface in calibrator_surfaces:
        text = re.sub(r"\s+", " ", surface.read_text(encoding="utf-8")).lower()
        assert "pre-existing platt score" in text
        assert "none of the three alternative" in text
        assert "no map from this sensitivity enters portfolio optimization" not in text
        assert "no sensitivity arm enters the lp" not in text


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
    assert rolling["common_issue_months"] == ["April", "May", "June"]
    assert rolling["individual_followup_months_after_issue_month_end"] == 39
    assert rolling["exact_calendar_month_age_matched"] is True
    assert rolling["exact_day_level_age_matched"] is False
    assert rolling["cutoff_by_issue_period"] == {
        "2016-04": "2019-07-31",
        "2016-05": "2019-08-31",
        "2016-06": "2019-09-30",
        "2017-04": "2020-07-31",
        "2017-05": "2020-08-31",
        "2017-06": "2020-09-30",
    }
    assert rolling["primary_2016_periods"] == ["2016-04", "2016-05", "2016-06"]
    assert rolling["rolling_2017_periods"] == ["2017-04", "2017-05", "2017-06"]
    assert rolling["primary_2016_census"] == {
        "candidate_rows": 74537,
        "resolved_rows": 73934,
        "unresolved_rows": 603,
    }
    assert rolling["rolling_2017_census"] == {
        "candidate_rows": 77105,
        "resolved_rows": 66037,
        "unresolved_rows": 11068,
    }
    assert rolling["coarser_equal_quarter_followup_retained_as_provenance"] == {
        "run_tag": "ijds-rolling-origin-equal-followup-2026-07-21-v1",
        "protocol_tag": "protocol/ijds-rolling-origin-equal-followup-2026-07-21-v1",
        "all_sixteen_upper_below_nominal": True,
        "approximate_followup_months_by_issue_month": {
            "April": 41,
            "May": 40,
            "June": 39,
        },
    }
    assert rolling["unequal_followup_runs_retained_as_provenance"] == {
        "rolling_2017_run_tag": "ijds-rolling-origin-2017-2026-07-15-v4",
        "primary_2016_recovery_run_tag": ("ijds-rolling-origin-primary-recovery-2026-07-21-v1"),
    }
    assert rolling["primary_2016_upper_max"] == pytest.approx(0.8791204368300307)
    assert rolling["rolling_2017_upper_max"] == pytest.approx(0.8752610077167499)
    assert all(
        row["candidate_rows"] != 376890
        for row in rolling["rows"]
        if row["origin_id"] == "primary_2016"
    )
    assert {(row["origin_id"], row["window"]) for row in rolling["rows"]} == {
        (origin, f"W{window}")
        for origin in ("primary_2016", "rolling_2017")
        for window in range(1, 9)
    }
    assert {row["individual_followup_months"] for row in rolling["rows"]} == {39}
    assert {
        (row["origin_id"], row["evaluation_cutoff_min"], row["evaluation_cutoff_max"])
        for row in rolling["rows"]
    } == {
        ("primary_2016", "2019-07-31", "2019-09-30"),
        ("rolling_2017", "2020-07-31", "2020-09-30"),
    }
    assert len(rolling["monthly_endpoint_census"]) == 6
    assert {
        (row["period"], row["individual_evaluation_cutoff"])
        for row in rolling["monthly_endpoint_census"]
    } == set(rolling["cutoff_by_issue_period"].items())
    for origin, expected in {
        "primary_2016": (74537, 73934, 603),
        "rolling_2017": (77105, 66037, 11068),
    }.items():
        scoped = [row for row in rolling["monthly_endpoint_census"] if row["origin_id"] == origin]
        assert sum(row["candidate_rows"] for row in scoped) == expected[0]
        assert sum(row["resolved_rows"] for row in scoped) == expected[1]
        assert sum(row["unresolved_rows"] for row in scoped) == expected[2]
    assert rolling["all_sixteen_upper_below_nominal"] is True
    assert rolling["model_or_origin_selected"] is False
    assert rolling["independent_replication_claim_authorized"] is False

    diagnostic = evidence["conformal_set_diagnostics"]
    assert diagnostic["learner_window_cells"] == 40
    assert diagnostic["all_forty_resolved_y0_coverage_above_y1"] is True
    assert diagnostic["resolved_y0_coverage_min"] == pytest.approx(0.9829815294859051)
    assert diagnostic["resolved_y0_coverage_max"] == pytest.approx(0.9927137947388596)
    assert diagnostic["resolved_y1_coverage_min"] == pytest.approx(0.23257038545250297)
    assert diagnostic["resolved_y1_coverage_max"] == pytest.approx(0.3639156076669241)
    assert diagnostic["interpretation"]["label_conditional_guarantee"] is False
    assert (
        diagnostic["interpretation"]["all_candidate_label_conditional_coverage_estimated"] is False
    )
    assert diagnostic["interpretation"]["fairness_or_equalized_coverage_claim"] is False


def test_joint_block_rank_reference_is_complete_and_scoped() -> None:
    exact = _json(EVIDENCE)["exchangeability_transport_test"]

    assert exact["run_tag"] == "ijds-exchangeability-transport-test-2026-07-21-v1"
    assert exact["rank_null"]["law"] == "BetaBinomial(m, n + 1 - r, r)"
    assert exact["rank_null"]["continuous_scores_give_exact_count_law"] is True
    assert exact["rank_null"]["beta_binomial_upper_tail_is_conservative_with_ties"] is True
    assert exact["rank_null"]["stronger_than_single_future_point_split_conformal_condition"] is True
    assert (
        exact["rank_null"]["rejection_need_not_refute_pointwise_marginal_split_conformal_validity"]
        is True
    )
    assert exact["unresolved_endpoint_rule"]["sharp_under_unrestricted_binary_completion"] is True
    assert exact["multiplicity"]["familywise_alpha"] == 0.05
    assert exact["multiplicity"]["active_role"] == "locked_nominal_reporting_thresholds"
    assert exact["multiplicity"]["would_control_fwer_if_family_fixed_ex_ante"] is True
    assert exact["multiplicity"]["post_selection_fwer_control_claimed"] is False
    assert exact["multiplicity"]["study_wide_fwer_control_claimed"] is False
    assert exact["thirty_one_of_forty_meet_locked_nominal_thresholds"] is True
    assert exact["cells_meeting_locked_nominal_thresholds"] == 31
    assert exact["cells_not_meeting_locked_nominal_thresholds"] == 9
    assert exact["nominal_flags_by_learner"] == {
        "catboost_platt": 8,
        "numeric_logistic_platt": 4,
        "catboost_monotonic_platt": 8,
        "woe_scorecard_platform_platt": 6,
        "woe_scorecard_borrower_platt": 5,
    }
    assert len(exact["cell_rows"]) == 40
    assert len(exact["stratum_rows"]) == 200
    assert {
        (row["learner"], row["window"])
        for row in exact["cell_rows"]
        if not row["meets_locked_nominal_holm_threshold"]
    } == {
        *(("numeric_logistic_platt", f"W{window}") for window in range(1, 5)),
        *(("woe_scorecard_platform_platt", f"W{window}") for window in range(1, 3)),
        *(("woe_scorecard_borrower_platt", f"W{window}") for window in range(1, 4)),
    }
    assert exact["interpretation"]["preregistered"] is False
    assert exact["interpretation"]["confirmatory"] is False
    assert exact["interpretation"]["usual_single_future_point_condition_tested_directly"] is False
    assert exact["interpretation"]["usual_pointwise_split_conformal_theorem_refuted"] is False
    assert exact["interpretation"]["post_selection_fwer_control_claimed"] is False
    assert exact["interpretation"]["nonflag_establishes_exchangeability"] is False
    assert exact["interpretation"]["flag_identifies_cause_of_shift"] is False


def test_closed_coverage_diagnostics_are_complete_and_nonselective() -> None:
    closed = _json(EVIDENCE)["closed_coverage_diagnostics"]

    assert closed["all_sixty_four_primary_upper_below_nominal"] is True
    assert closed["censored_extension_mixed_stress_pattern"] is True
    assert closed["censored_extension_catboost_below_nominal_windows"] == list(CLOSED_WINDOW_IDS)
    assert closed["censored_extension_logistic_contains_nominal_windows"] == list(
        CLOSED_WINDOW_IDS[:6]
    )
    assert closed["censored_extension_logistic_below_nominal_windows"] == list(
        CLOSED_WINDOW_IDS[6:]
    )
    assert len(closed["taxonomy_rows"]) == 64
    assert len(closed["taxonomy_summary_rows"]) == 8
    assert len(closed["censored_extension_rows"]) == 16
    assert {
        (row["learner"], int(row["taxonomy_groups"])) for row in closed["taxonomy_summary_rows"]
    } == {
        (learner, groups)
        for learner in ("catboost_platt", "numeric_logistic_platt")
        for groups in (1, 2, 5, 10)
    }
    assert all(row["windows_upper_below_0_90"] == 8 for row in closed["taxonomy_summary_rows"])
    assert all(row["coverage_upper"] < 0.90 for row in closed["taxonomy_rows"])
    assert closed["joint_block_rank_reference_extended_to_these_rows"] is False
    assert closed["independent_replication_claimed"] is False
    assert closed["extension_is_primary_oot"] is False


def test_label_mondrian_sensitivity_is_complete_and_nonconfirmatory() -> None:
    label = _json(EVIDENCE)["sensitivity"]["label_mondrian"]

    assert label["freeze_run_tag"] == "ijds-label-mondrian-freeze-2026-07-21-v1"
    assert label["run_tag"] == "ijds-label-mondrian-evaluation-2026-07-21-v1"
    assert label["counts"] == {
        "learner_window_cells": 40,
        "threshold_cells": 400,
        "target_category_cells": 400,
        "target_stratum_cells": 200,
        "learners": 5,
        "windows_per_learner": 8,
        "score_strata": 5,
        "labels": 2,
        "candidate_rows": 376890,
        "resolved_rows": 364814,
        "unresolved_rows": 12076,
    }
    assert label["learner_window_states"] == {
        "robust_shortfall": 27,
        "robust_at_or_above_nominal": 1,
        "crosses_nominal": 12,
    }
    assert label["category_states"] == {
        "crosses_nominal": 185,
        "robust_shortfall": 109,
        "robust_at_or_above_nominal": 106,
    }
    assert label["mixed_category_identification_states"] is True
    assert label["all_forty_aggregate_class_gap_bounds_cross_zero"] is True
    assert label["average_set_size_min"] == pytest.approx(1.7237177956432912)
    assert label["average_set_size_max"] == pytest.approx(1.785467908408289)
    assert label["set_both_share_min"] == pytest.approx(0.7237177956432912)
    assert label["set_both_share_max"] == pytest.approx(0.7854679084082888)
    assert len(label["cell_rows"]) == 40
    assert len(label["stratum_rows"]) == 200
    assert len(label["category_rows"]) == 400
    assert all(
        row["coverage_gap_y0_minus_y1_lower"] <= 0 <= row["coverage_gap_y0_minus_y1_upper"]
        for row in label["cell_rows"]
    )
    assert label["interpretation"]["label_conditional_transport_guarantee"] is False
    assert label["interpretation"]["fairness_claim"] is False
    assert label["interpretation"]["policy_claim"] is False


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
        "exchangeability_transport/summary",
        "exchangeability_transport/config",
        "exchangeability_transport/stratum_tests",
        "exchangeability_transport/learner_window_cells",
        "common_panel_threshold_response/summary",
        "common_panel_threshold_response/config",
        "common_panel_threshold_response/execution_receipt",
        "common_panel_threshold_response/protocol",
        "common_panel_threshold_response/runner",
        "common_panel_threshold_response/implementation",
        "common_panel_threshold_response/adjacent_stratum_threshold_response",
        "common_panel_threshold_response/adjacent_learner_threshold_response",
        "rolling_origin_equal_followup/summary",
        "rolling_origin_equal_followup/config",
        "rolling_origin_equal_followup/temporal_coverage",
        "rolling_origin_equal_followup/origin_endpoint_census",
        "rolling_origin_individual_age_followup/summary",
        "rolling_origin_individual_age_followup/config",
        "rolling_origin_individual_age_followup/execution_receipt",
        "rolling_origin_individual_age_followup/temporal_coverage",
        "rolling_origin_individual_age_followup/origin_endpoint_census",
        "rolling_origin_individual_age_followup/monthly_endpoint_census",
        "rolling_origin_individual_age_followup/origin_endpoint_reason_census",
        "rolling_origin_individual_age_followup/monthly_endpoint_reason_census",
        "label_mondrian/outcome_free/freeze",
        "label_mondrian/outcome_free/config",
        "label_mondrian/outcome_free/thresholds",
        "label_mondrian/evaluation/summary",
        "label_mondrian/evaluation/config",
        "label_mondrian/evaluation/label_mondrian_diagnostics",
        "label_mondrian/evaluation/label_mondrian_category_diagnostics",
        "label_mondrian/evaluation/label_mondrian_stratum_diagnostics",
        "artifact_descriptor_helper",
        "outcome_free/source_protocol_freeze",
        "two_ruler/outcome_free/freeze",
        "credit_controls/freeze",
    }.issubset(evidence["source_artifacts"])
    assert evidence["paper_artifacts"]
    parent_bytes = subprocess.check_output(
        [
            "git",
            "show",
            f"{support_extension.PARENT_COMMIT}:{support_extension.PARENT_MANIFEST_PATH}",
        ],
        cwd=REPO,
    )
    assert hashlib.sha256(parent_bytes).hexdigest() == evidence["incremental_parent"]["sha256"]
    parent = json.loads(parent_bytes)
    sealed_by_path = {
        descriptor["path"]: descriptor for descriptor in parent["source_artifacts"].values()
    }
    registry = load_source_registry(
        REPO / "configs/ijds_active_evidence_sources.yaml", repo_root=REPO
    )
    dvc_roots = tuple(
        str(Path(pointer).parent / Path(pointer).stem).replace("\\", "/")
        for pointer in registry["dvc_pointers"]
    )
    for descriptor in (
        *evidence["source_artifacts"].values(),
        *evidence["paper_artifacts"].values(),
    ):
        path = REPO / descriptor["path"]
        if not path.is_file():
            assert descriptor == sealed_by_path.get(descriptor["path"])
            assert any(
                descriptor["path"] == root or descriptor["path"].startswith(f"{root}/")
                for root in dvc_roots
            )
            continue
        assert path.stat().st_size == descriptor["bytes"]
        assert _sha256(path) == descriptor["sha256"]


def test_manuscript_surfaces_share_v4_claims_and_retire_old_headlines() -> None:
    shared_active = (
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
        "2,985",
        "0.001284",
        "3,067",
        "216",
        "72",
        "individual-age",
        "31 of 40",
        "109",
        "label-mondrian",
        "status-indexed",
        "selected-set",
    )
    supplement_active = ("0.884669", "0.884332", "0.879120", "0.875261")
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
        assert not [token for token in shared_active if _normalize(token) not in text], surface
        assert not [token for token in retired if _normalize(token) in text], surface
    supplement = _normalize((REPO / "paper/supplement_ijds.qmd").read_text(encoding="utf-8"))
    assert not [token for token in supplement_active if _normalize(token) not in supplement]


def test_official_tex_is_deterministically_generated_from_qmd() -> None:
    assert render_submission_tex(check=True)
