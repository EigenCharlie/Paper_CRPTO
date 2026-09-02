"""Build the deterministic anonymous machine-readable IJDS supplement."""

from __future__ import annotations

import argparse
import csv
import io
import math
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Final, NoReturn

from scripts.check_publication_integrity import (
    REVIEWER_FORBIDDEN_LITERALS,
    REVIEWER_FORBIDDEN_PATTERNS,
)
from src.ijds_audit.publication_schemas import S6B_PUBLICATION_COLUMNS
from src.utils.pipeline_runtime import atomic_write_bytes

ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "reports" / "crpto" / "tables"
OUTPUT = ROOT / "paper" / "submission" / "CRPTO_ijds_machine_readable_supplement.zip"
SOURCE_FILENAMES = {
    "Table_S2C_calibrator_fit_diagnostics.csv": (
        "crpto_ijds_v4_tableS2C_calibrator_fit_diagnostics.csv"
    ),
    "Table_S6B_exchangeability_cells.csv": "crpto_ijds_v4_tableS6B_exchangeability_cells.csv",
    "Table_S6C_exchangeability_strata.csv": "crpto_ijds_v4_tableS6C_exchangeability_strata.csv",
    "Table_S6D_label_mondrian_cells.csv": "crpto_ijds_v4_tableS6D_label_mondrian_cells.csv",
    "Table_S6E_label_mondrian_strata.csv": "crpto_ijds_v4_tableS6E_label_mondrian_strata.csv",
    "Table_S6F_label_mondrian_categories.csv": (
        "crpto_ijds_v4_tableS6F_label_mondrian_categories.csv"
    ),
    "Table_S6J_common_panel_threshold_response_strata.csv": (
        "crpto_ijds_v4_tableS6J_common_panel_threshold_response_strata.csv"
    ),
    "Table_S6K_common_panel_threshold_response_learners.csv": (
        "crpto_ijds_v4_tableS6K_common_panel_threshold_response_learners.csv"
    ),
    "Table_S6L_residual_transport_summary.csv": (
        "crpto_ijds_v4_tableS6L_residual_transport_summary.csv"
    ),
    "Table_S6M_residual_transport_pooled.csv": (
        "crpto_ijds_v4_tableS6M_residual_transport_pooled.csv"
    ),
    "Table_S6N_marginal_score_outcome_gap.csv": (
        "crpto_ijds_v4_tableS6N_marginal_score_outcome_gap.csv"
    ),
    "Table_S6O_calibrator_sensitivity_cells.csv": (
        "crpto_ijds_v4_tableS6O_calibrator_sensitivity_cells.csv"
    ),
    "Table_S6P_calibrator_pairwise_shared_completion.csv": (
        "crpto_ijds_v4_tableS6P_calibrator_pairwise_shared_completion.csv"
    ),
    "Table_S6Q_binary_phase_target_support.csv": (
        "crpto_ijds_v4_tableS6Q_binary_phase_target_support.csv"
    ),
    "Table_S9G_decision_catalog_metric_separation.csv": (
        "crpto_ijds_v4_tableS9G_decision_catalog_metric_separation.csv"
    ),
    "Table_S9H_decision_catalog_target_blocks.csv": (
        "crpto_ijds_v4_tableS9H_decision_catalog_target_blocks.csv"
    ),
    "Table_S9I_funded_selection_track_estimands.csv": (
        "crpto_ijds_v4_tableS9I_funded_selection_track_estimands.csv"
    ),
    "Table_S9J_funded_selection_gamma_contrasts.csv": (
        "crpto_ijds_v4_tableS9J_funded_selection_gamma_contrasts.csv"
    ),
    "Table_S9K_set_preserving_embedding_allocation_summary.csv": (
        "crpto_ijds_v4_tableS9K_set_preserving_embedding_allocation_summary.csv"
    ),
    "Table_S9L_set_preserving_embedding_direction_census.csv": (
        "crpto_ijds_v4_tableS9L_set_preserving_embedding_direction_census.csv"
    ),
}
SOURCES = {name: TABLE_DIR / filename for name, filename in SOURCE_FILENAMES.items()}


def _columns(*parts: str) -> tuple[str, ...]:
    """Declare a readable, exact CSV header without relying on a source CSV."""

    return tuple("".join(parts).split(","))


S2C_COLUMNS: Final = _columns(
    "method,rows,default_rate,roc_auc,brier,log_loss,ece_10,",
    "venn_multiprobability_gap_mean,same_sample_descriptive_only,selection_metric",
)
S6C_COLUMNS: Final = _columns(
    "learner,learner_label,window,window_id,taxonomy_groups,score_stratum,",
    "conformal_group,role,fit_rows,finite_sample_rank,beta_a,beta_b,",
    "fit_residual_quantile,fit_score_min,fit_score_max,fit_residual_below_threshold,",
    "fit_residual_equal_threshold,fit_residual_above_threshold,",
    "continuous_threshold_tie_singleton,candidate_rows,score_min,score_max,resolved_rows,",
    "unresolved_rows,resolved_misses,coverage_resolved,",
    "resolved_target_residual_equal_threshold,unresolved_equal_threshold_if_y0,",
    "unresolved_equal_threshold_if_y1,unresolved_min_equal_threshold,",
    "unresolved_max_equal_threshold,unresolved_min_misses,unresolved_max_misses,",
    "misses_min,misses_max,miss_rate_min,miss_rate_max,coverage_lower,coverage_upper,",
    "null_expected_miss_rate,null_expected_misses,joint_block_reference_exact_log_p_value,",
    "joint_block_reference_exact_p_value,joint_block_reference_exact_neg_log10_p_value,",
    "source_within_cell_bonferroni_log_p_value,source_within_cell_bonferroni_p_value,",
    "meets_locked_nominal_within_cell_threshold,candidate_rows_active_reference,",
    "resolved_rows_active_reference,unresolved_rows_active_reference,",
    "fit_rows_active_reference,coverage_resolved_active_reference,",
    "coverage_lower_active_reference,coverage_upper_active_reference,",
    "score_min_active_reference,score_max_active_reference,",
    "fit_residual_quantile_active_reference,fit_score_min_active_reference,",
    "fit_score_max_active_reference,coverage_resolved_active_difference,",
    "coverage_lower_active_difference,coverage_upper_active_difference,",
    "score_min_active_difference,score_max_active_difference,",
    "fit_residual_quantile_active_difference,fit_score_min_active_difference,",
    "fit_score_max_active_difference",
)
S6D_COLUMNS: Final = _columns(
    "learner,learner_label,window,window_id,taxonomy_groups,",
    "identification_state_at_nominal,role,score_strata_observed,threshold_cells,",
    "infinite_threshold_cells,average_set_size,singleton_share,set_empty_count,",
    "set_empty_share,set_zero_only_count,set_zero_only_share,set_one_only_count,",
    "set_one_only_share,set_both_count,set_both_share,candidate_rows,resolved_rows,",
    "unresolved_rows,resolved_y0_rows,resolved_y1_rows,resolved_covered_rows,",
    "coverage_resolved,coverage_resolved_y0,coverage_resolved_y1,",
    "coverage_resolved_gap_y0_minus_y1,coverage_lower,coverage_upper,coverage_y0_lower,",
    "coverage_y0_upper,coverage_y1_lower,coverage_y1_upper,",
    "coverage_gap_y0_minus_y1_lower,coverage_gap_y0_minus_y1_upper,",
    "gap_lower_unresolved_y1_rows,gap_upper_unresolved_y1_rows,",
    "unresolved_zero_covered_rows,unresolved_zero_missed_rows,",
    "unresolved_one_covered_rows,unresolved_one_missed_rows,baseline_average_set_size,",
    "baseline_singleton_share,baseline_set_empty_count,baseline_set_empty_share,",
    "baseline_set_zero_only_count,baseline_set_zero_only_share,",
    "baseline_set_one_only_count,baseline_set_one_only_share,baseline_set_both_count,",
    "baseline_set_both_share,baseline_candidate_rows,baseline_resolved_rows,",
    "baseline_unresolved_rows,baseline_resolved_y0_rows,baseline_resolved_y1_rows,",
    "baseline_resolved_covered_rows,baseline_coverage_resolved,",
    "baseline_coverage_resolved_y0,baseline_coverage_resolved_y1,",
    "baseline_coverage_resolved_gap_y0_minus_y1,baseline_coverage_lower,",
    "baseline_coverage_upper,baseline_coverage_y0_lower,baseline_coverage_y0_upper,",
    "baseline_coverage_y1_lower,baseline_coverage_y1_upper,",
    "baseline_coverage_gap_y0_minus_y1_lower,",
    "baseline_coverage_gap_y0_minus_y1_upper,baseline_gap_lower_unresolved_y1_rows,",
    "baseline_gap_upper_unresolved_y1_rows,baseline_unresolved_zero_covered_rows,",
    "baseline_unresolved_zero_missed_rows,baseline_unresolved_one_covered_rows,",
    "baseline_unresolved_one_missed_rows,baseline_mean_width,",
    "resolved_coverage_delta_label_mondrian_minus_baseline,",
    "resolved_y0_coverage_delta_label_mondrian_minus_baseline,",
    "resolved_y1_coverage_delta_label_mondrian_minus_baseline,",
    "average_set_size_delta_label_mondrian_minus_baseline",
)
S6E_COLUMNS: Final = _columns(
    "learner,learner_label,window,window_id,taxonomy_groups,role,score_stratum,",
    "candidate_stratum_rows,resolved_rows,unresolved_rows,resolved_covered_rows,",
    "coverage_resolved,coverage_lower,coverage_upper,baseline_resolved_covered_rows,",
    "baseline_coverage_resolved,baseline_coverage_lower,baseline_coverage_upper,",
    "resolved_y0_rows,resolved_y1_rows,coverage_resolved_gap_y0_minus_y1,",
    "conditional_gap_defined,coverage_gap_y0_minus_y1_lower,",
    "coverage_gap_y0_minus_y1_upper,gap_lower_unresolved_y1_rows,",
    "gap_upper_unresolved_y1_rows,average_set_size,singleton_share,set_empty_count,",
    "set_empty_share,set_zero_only_count,set_zero_only_share,set_one_only_count,",
    "set_one_only_share,set_both_count,set_both_share,candidate_rows,",
    "baseline_average_set_size,baseline_singleton_share,baseline_set_empty_count,",
    "baseline_set_empty_share,baseline_set_zero_only_count,baseline_set_zero_only_share,",
    "baseline_set_one_only_count,baseline_set_one_only_share,baseline_set_both_count,",
    "baseline_set_both_share,baseline_candidate_rows,",
    "baseline_coverage_resolved_gap_y0_minus_y1,",
    "baseline_coverage_gap_y0_minus_y1_lower,",
    "baseline_coverage_gap_y0_minus_y1_upper,baseline_gap_lower_unresolved_y1_rows,",
    "baseline_gap_upper_unresolved_y1_rows,",
    "resolved_coverage_delta_label_mondrian_minus_baseline,",
    "average_set_size_delta_label_mondrian_minus_baseline,sharp_endpoint_delta_reported",
)
S6F_COLUMNS: Final = _columns(
    "learner,learner_label,window,window_id,taxonomy_groups,role,score_stratum,label,",
    "alpha,fit_rows,finite_sample_rank,threshold,threshold_is_infinite,",
    "score_stratum_present,candidate_stratum_rows,resolved_label_rows,",
    "resolved_label_covered_rows,coverage_resolved_label,",
    "baseline_resolved_label_covered_rows,baseline_coverage_resolved_label,",
    "unresolved_stratum_rows,unresolved_label_covered_if_assigned_rows,",
    "unresolved_label_missed_if_assigned_rows,",
    "baseline_unresolved_label_covered_if_assigned_rows,",
    "baseline_unresolved_label_missed_if_assigned_rows,conditional_coverage_defined,",
    "coverage_label_lower,coverage_label_upper,baseline_coverage_label_lower,",
    "baseline_coverage_label_upper,label_prevalence_lower,label_prevalence_upper,",
    "coverage_upper_below_nominal,identification_state_at_nominal,",
    "baseline_identification_state_at_nominal,",
    "resolved_coverage_delta_label_mondrian_minus_baseline,sharp_endpoint_delta_reported",
)
S6J_COLUMNS: Final = _columns(
    "learner,learner_label,pair_id,transition,pair_index,window_from,window_to,",
    "taxonomy_groups,conformal_group,score_stratum,candidate_rows,resolved_rows,",
    "unresolved_rows,threshold_from,threshold_to,threshold_low,threshold_high,",
    "threshold_delta,threshold_sign,potential_y0_crossed_rows,potential_y1_crossed_rows,",
    "resolved_y0_crossed_rows,resolved_y1_crossed_rows,resolved_y0_delta_numerator,",
    "resolved_y1_delta_numerator,resolved_delta_numerator,",
    "resolved_covered_from_numerator,resolved_covered_to_numerator,resolved_delta_rate,",
    "delta_lower_numerator,delta_upper_numerator,delta_width_numerator,delta_lower,",
    "delta_upper,delta_width",
)
S6K_COLUMNS: Final = _columns(
    "learner,learner_label,pair_id,transition,pair_index,window_from,window_to,",
    "taxonomy_groups,strata_rows,candidate_rows,resolved_rows,unresolved_rows,",
    "potential_y0_crossed_rows,potential_y1_crossed_rows,resolved_y0_crossed_rows,",
    "resolved_y1_crossed_rows,resolved_y0_delta_numerator,resolved_y1_delta_numerator,",
    "resolved_delta_numerator,resolved_covered_from_numerator,",
    "resolved_covered_to_numerator,delta_lower_numerator,delta_upper_numerator,",
    "delta_width_numerator,threshold_decrease_strata,threshold_equal_strata,",
    "threshold_increase_strata,resolved_delta_rate,delta_lower,delta_upper,delta_width",
)
S6L_COLUMNS: Final = _columns(
    "learner,learner_label,pooled_cells,",
    "larger_target_residual_discrepancy_dominates,",
    "smaller_target_residual_discrepancy_dominates,",
    "directional_discrepancies_not_robustly_ordered",
)
S6M_COLUMNS: Final = _columns(
    "learner,learner_label,window_id,score_stratum,fit_rows,target_rows,resolved_rows,",
    "unresolved_rows,completion_directional_ks_denominator,",
    "calibration_minus_target_ks_min,calibration_minus_target_ks_max,",
    "target_minus_calibration_ks_min,target_minus_calibration_ks_max,",
    "calibration_minus_target_ks_min_numerator,",
    "calibration_minus_target_ks_max_numerator,",
    "target_minus_calibration_ks_min_numerator,target_minus_calibration_ks_max_numerator,",
    "sharp_directional_discrepancy_comparison,v5_q_and_coverage_reconciled",
)
S6N_COLUMNS: Final = _columns(
    "learner_order,learner,learner_label,candidate_rows,resolved_rows,unresolved_outcomes,",
    "mean_score,outcome_mean_lower,outcome_mean_upper,",
    "marginal_mean_score_outcome_gap_lower,marginal_mean_score_outcome_gap_upper,",
    "identification_width,identified_grid_points,identified_grid_step,",
    "joint_endpoint_attainment",
)
S6O_COLUMNS: Final = _columns(
    "method,window_id,taxonomy_groups,role,conformal_group,candidate_rows,resolved_rows,",
    "unresolved_rows,coverage_resolved,coverage_lower,coverage_upper,",
    "coverage_resolved_y0,coverage_resolved_y1,rows,mean_width,average_set_size,",
    "singleton_share,set_empty_count,set_empty_share,set_zero_only_count,",
    "set_zero_only_share,set_one_only_count,set_one_only_share,set_both_count,",
    "set_both_share,lower_positive_share,upper_saturated_share,width_q00,width_q10,",
    "width_q25,width_q50,width_q75,width_q90,width_q100,score_min,score_max,fit_rows,",
    "fit_prevalence,fit_residual_quantile,fit_score_min,fit_score_max,",
    "scores_below_fit_range,scores_above_fit_range,venn_multiprobability_gap_mean,",
    "venn_multiprobability_gap_q50,coverage_upper_below_nominal",
)
S6P_COLUMNS: Final = _columns(
    "method_a,method_b,window_id,taxonomy_groups,role,conformal_group,candidate_rows,",
    "resolved_rows,unresolved_rows,coverage_difference_resolved,",
    "coverage_difference_lower,coverage_difference_upper,shared_loanwise_completion",
)
S6Q_COLUMNS: Final = _columns(
    "learner,learner_label,window,window_id,taxonomy_groups,score_stratum,",
    "conformal_group,alpha,fit_rows,fit_defaults,fit_default_prevalence,",
    "finite_sample_rank,boundary_count,phase_boundary_rate,phase_margin,",
    "phase_prevalence_at_or_below_boundary,frozen_threshold,threshold_below_half,",
    "max_score_below_half_condition,target_candidate_rows,target_score_max,",
    "positive_label_boundary,target_max_below_positive_label_boundary,",
    "positive_label_excluded_from_every_target_set,target_resolved_rows,",
    "target_resolved_misses,resolved_misses_in_exclusion_strata,",
    "resolved_misses_all_strata,exclusion_strata_resolved_miss_fraction",
)
S9G_COLUMNS: Final = _columns(
    "metric,target_blocks,minimum_target_lower,development_maximum_upper,",
    "all_target_blocks_exceed_development,minimum_separation_margin",
)
S9H_COLUMNS: Final = _columns(
    "period,metric,score_lower,score_upper,policies,development_max_upper,",
    "classification,exceeds_all_development_upper",
)
S9I_COLUMNS: Final = _columns(
    "window_id,role,frontier_ruler,frontier_coordinate,gamma,candidate_id,",
    "selected_positions,funded_dollars,committed_capital_usd,cash_residual_usd,",
    "resolved_positions,unresolved_positions,empty_set_positions,full_set_positions,",
    "singleton_zero_positions,singleton_one_positions,count_selected_fcp_lower,",
    "count_selected_fcp_upper,count_selected_coverage_lower,",
    "count_selected_coverage_upper,invested_dollar_selected_fcp_lower,",
    "invested_dollar_selected_fcp_upper,invested_dollar_selected_coverage_lower,",
    "invested_dollar_selected_coverage_upper,fixed_capital_decision_fcp_lower,",
    "fixed_capital_decision_fcp_upper,fixed_capital_decision_coverage_lower,",
    "fixed_capital_decision_coverage_upper,",
    "count_selected_minus_invested_dollar_selected_fcp_lower,",
    "count_selected_minus_invested_dollar_selected_fcp_upper,",
    "count_selected_minus_invested_dollar_selected_coverage_lower,",
    "count_selected_minus_invested_dollar_selected_coverage_upper,",
    "count_selected_minus_fixed_capital_decision_fcp_lower,",
    "count_selected_minus_fixed_capital_decision_fcp_upper,",
    "count_selected_minus_fixed_capital_decision_coverage_lower,",
    "count_selected_minus_fixed_capital_decision_coverage_upper,sharpness,periods",
)
S9J_COLUMNS: Final = _columns(
    "window_id,role,frontier_ruler,frontier_coordinate,gamma0_candidate_id,",
    "gamma1_candidate_id,gamma0_selected_positions,gamma1_selected_positions,",
    "gamma0_funded_dollars,gamma1_funded_dollars,committed_capital_usd,",
    "funded_union_positions,funded_overlap_positions,unresolved_union_positions,",
    "gamma1_minus_gamma0_count_selected_fcp_lower,",
    "gamma1_minus_gamma0_count_selected_fcp_upper,",
    "gamma1_minus_gamma0_count_selected_coverage_lower,",
    "gamma1_minus_gamma0_count_selected_coverage_upper,",
    "gamma1_minus_gamma0_count_selected_fcp_direction,",
    "gamma1_minus_gamma0_invested_dollar_selected_fcp_lower,",
    "gamma1_minus_gamma0_invested_dollar_selected_fcp_upper,",
    "gamma1_minus_gamma0_invested_dollar_selected_coverage_lower,",
    "gamma1_minus_gamma0_invested_dollar_selected_coverage_upper,",
    "gamma1_minus_gamma0_invested_dollar_selected_fcp_direction,",
    "gamma1_minus_gamma0_fixed_capital_decision_fcp_lower,",
    "gamma1_minus_gamma0_fixed_capital_decision_fcp_upper,",
    "gamma1_minus_gamma0_fixed_capital_decision_coverage_lower,",
    "gamma1_minus_gamma0_fixed_capital_decision_coverage_upper,",
    "gamma1_minus_gamma0_fixed_capital_decision_fcp_direction,sharpness,periods",
)
S9K_COLUMNS: Final = _columns(
    "ruler,noncontrol_theta_contrasts,allocation_changes_gt_1e10,",
    "allocation_change_fraction,maximum_normalized_exposure_distance,",
    "set_diagnostic_rows,sets_changed,maximum_upper_contraction",
)
S9L_COLUMNS: Final = _columns(
    "contrast_family,metric,cells,negative,positive,",
    "not_directionally_separated_at_tolerance,within_tolerance",
)

LEARNER_METADATA: Final = {
    "catboost_platt": ("CatBoost", "pd_catboost_platt", "1"),
    "numeric_logistic_platt": ("Numeric logistic", "pd_numeric_logistic_platt", "2"),
    "catboost_monotonic_platt": (
        "Monotonic CatBoost",
        "pd_catboost_monotonic_platt",
        "3",
    ),
    "woe_scorecard_platform_platt": (
        "Platform-signal WOE scorecard",
        "pd_woe_scorecard_platform_platt",
        "4",
    ),
    "woe_scorecard_borrower_platt": (
        "Pricing-excluded application WOE scorecard",
        "pd_woe_scorecard_borrower_platt",
        "5",
    ),
}
WINDOW_METADATA: Final = {
    "w01_2012m01_m06": "W1",
    "w02_2012m02_m07": "W2",
    "w03_2012m03_m08": "W3",
    "w04_2012m04_m09": "W4",
    "w05_2012m05_m10": "W5",
    "w06_2012m06_m11": "W6",
    "w07_2012m07_m12": "W7",
    "w08_2012m08_2013m01": "W8",
}
WINDOW_IDS: Final = tuple(WINDOW_METADATA)
PAIR_METADATA: Final = {
    str(index): (
        f"{index:02d}:{WINDOW_IDS[index]}->{WINDOW_IDS[index + 1]}",
        f"W{index + 1}--W{index + 2}",
        WINDOW_IDS[index],
        WINDOW_IDS[index + 1],
    )
    for index in range(7)
}
PRIMARY_CANDIDATES: Final = 376_890
PRIMARY_RESOLVED: Final = 364_814
PRIMARY_UNRESOLVED: Final = 12_076
ISSUE_MONTHS: Final = (
    "2016-04",
    "2016-05",
    "2016-06",
    "2016-07",
    "2016-08",
    "2016-09",
    "2016-10",
    "2016-11",
    "2016-12",
    "2017-01",
    "2017-02",
    "2017-03",
    "2017-04",
    "2017-05",
    "2017-06",
)
RULERS: Final = ("objective_matched", "normalized_score")
EMBEDDING_RULERS: Final = ("all_rulers", *RULERS)
EMBEDDING_CONTRAST_FAMILIES: Final = (
    "theta_minus_theta_0_within_gamma",
    "gamma_1_minus_gamma_0_within_theta",
)
EMBEDDING_METRICS: Final = (
    "standardized_payoff",
    "funded_default",
    "funded_binary_miscoverage",
)
COORDINATES: Final = ("0.25", "0.5", "0.75")
GAMMAS: Final = ("0.0", "1.0")
METRICS: Final = ("payoff_shortfall", "default_gap", "miscoverage_excess")


@dataclass(frozen=True)
class CsvContract:
    columns: tuple[str, ...]
    rows: int
    key_columns: tuple[str, ...]
    expected_keys: frozenset[tuple[str, ...]]
    exact_domains: dict[str, frozenset[str]]


def _grid(*axes: tuple[str, ...]) -> frozenset[tuple[str, ...]]:
    return frozenset(product(*axes))


LEARNERS: Final = tuple(LEARNER_METADATA)
WINDOWS: Final = tuple(WINDOW_METADATA)
GROUPS_ZERO_BASED: Final = tuple(str(value) for value in range(5))
STRATA_ONE_BASED: Final = tuple(str(value) for value in range(1, 6))
PAIRS: Final = tuple(str(value) for value in range(7))
CALIBRATOR_METHODS: Final = ("platt", "isotonic", "beta", "venn_abers")
CALIBRATOR_GROUPS: Final = ("-1", *GROUPS_ZERO_BASED)
CALIBRATOR_PAIRS: Final = (
    ("platt", "isotonic"),
    ("platt", "beta"),
    ("platt", "venn_abers"),
    ("isotonic", "beta"),
    ("isotonic", "venn_abers"),
    ("beta", "venn_abers"),
)
CALIBRATOR_PAIR_KEYS: Final = frozenset(
    (method_a, method_b, window, group)
    for method_a, method_b in CALIBRATOR_PAIRS
    for window in WINDOWS
    for group in CALIBRATOR_GROUPS
)
BOOLEAN_DOMAIN: Final = frozenset({"True", "False"})
IDENTIFICATION_STATE_DOMAIN: Final = frozenset(
    {"robust_shortfall", "crosses_nominal", "robust_at_or_above_nominal", "undefined"}
)

TABLE_CONTRACTS: Final = {
    "Table_S2C_calibrator_fit_diagnostics.csv": CsvContract(
        columns=S2C_COLUMNS,
        rows=4,
        key_columns=("method",),
        expected_keys=_grid(CALIBRATOR_METHODS),
        exact_domains={
            "method": frozenset(CALIBRATOR_METHODS),
            "rows": frozenset({"14077"}),
            "same_sample_descriptive_only": frozenset({"True"}),
            "selection_metric": frozenset({"False"}),
        },
    ),
    "Table_S6B_exchangeability_cells.csv": CsvContract(
        columns=S6B_PUBLICATION_COLUMNS,
        rows=40,
        key_columns=("learner", "window_id"),
        expected_keys=_grid(LEARNERS, WINDOWS),
        exact_domains={
            "taxonomy_groups": frozenset({"5"}),
            "stratum_tests": frozenset({"5"}),
            "all_calibration_threshold_ties_singleton": BOOLEAN_DOMAIN,
            "meets_locked_nominal_holm_threshold": BOOLEAN_DOMAIN,
        },
    ),
    "Table_S6C_exchangeability_strata.csv": CsvContract(
        columns=S6C_COLUMNS,
        rows=200,
        key_columns=("learner", "window_id", "score_stratum"),
        expected_keys=_grid(LEARNERS, WINDOWS, STRATA_ONE_BASED),
        exact_domains={
            "taxonomy_groups": frozenset({"5"}),
            "role": frozenset({"primary_oot"}),
            "score_stratum": frozenset(STRATA_ONE_BASED),
            "conformal_group": frozenset(GROUPS_ZERO_BASED),
            "continuous_threshold_tie_singleton": BOOLEAN_DOMAIN,
            "meets_locked_nominal_within_cell_threshold": BOOLEAN_DOMAIN,
        },
    ),
    "Table_S6D_label_mondrian_cells.csv": CsvContract(
        columns=S6D_COLUMNS,
        rows=40,
        key_columns=("learner", "window_id"),
        expected_keys=_grid(LEARNERS, WINDOWS),
        exact_domains={
            "taxonomy_groups": frozenset({"5"}),
            "role": frozenset({"primary_oot"}),
            "identification_state_at_nominal": IDENTIFICATION_STATE_DOMAIN,
        },
    ),
    "Table_S6E_label_mondrian_strata.csv": CsvContract(
        columns=S6E_COLUMNS,
        rows=200,
        key_columns=("learner", "window_id", "score_stratum"),
        expected_keys=_grid(LEARNERS, WINDOWS, GROUPS_ZERO_BASED),
        exact_domains={
            "taxonomy_groups": frozenset({"5"}),
            "role": frozenset({"primary_oot"}),
            "score_stratum": frozenset(GROUPS_ZERO_BASED),
            "conditional_gap_defined": BOOLEAN_DOMAIN,
            "sharp_endpoint_delta_reported": frozenset({"False"}),
        },
    ),
    "Table_S6F_label_mondrian_categories.csv": CsvContract(
        columns=S6F_COLUMNS,
        rows=400,
        key_columns=("learner", "window_id", "score_stratum", "label"),
        expected_keys=_grid(LEARNERS, WINDOWS, GROUPS_ZERO_BASED, ("0", "1")),
        exact_domains={
            "taxonomy_groups": frozenset({"5"}),
            "role": frozenset({"primary_oot"}),
            "score_stratum": frozenset(GROUPS_ZERO_BASED),
            "label": frozenset({"0", "1"}),
            "alpha": frozenset({"0.1"}),
            "threshold_is_infinite": BOOLEAN_DOMAIN,
            "score_stratum_present": BOOLEAN_DOMAIN,
            "conditional_coverage_defined": BOOLEAN_DOMAIN,
            "coverage_upper_below_nominal": BOOLEAN_DOMAIN,
            "identification_state_at_nominal": IDENTIFICATION_STATE_DOMAIN,
            "baseline_identification_state_at_nominal": IDENTIFICATION_STATE_DOMAIN,
            "sharp_endpoint_delta_reported": frozenset({"False"}),
        },
    ),
    "Table_S6J_common_panel_threshold_response_strata.csv": CsvContract(
        columns=S6J_COLUMNS,
        rows=175,
        key_columns=("learner", "pair_index", "conformal_group"),
        expected_keys=_grid(LEARNERS, PAIRS, GROUPS_ZERO_BASED),
        exact_domains={
            "taxonomy_groups": frozenset({"5"}),
            "pair_index": frozenset(PAIRS),
            "conformal_group": frozenset(GROUPS_ZERO_BASED),
            "score_stratum": frozenset(STRATA_ONE_BASED),
            "threshold_sign": frozenset({"-1", "0", "1"}),
        },
    ),
    "Table_S6K_common_panel_threshold_response_learners.csv": CsvContract(
        columns=S6K_COLUMNS,
        rows=35,
        key_columns=("learner", "pair_index"),
        expected_keys=_grid(LEARNERS, PAIRS),
        exact_domains={
            "taxonomy_groups": frozenset({"5"}),
            "strata_rows": frozenset({"5"}),
            "pair_index": frozenset(PAIRS),
        },
    ),
    "Table_S6L_residual_transport_summary.csv": CsvContract(
        columns=S6L_COLUMNS,
        rows=5,
        key_columns=("learner",),
        expected_keys=_grid(LEARNERS),
        exact_domains={"pooled_cells": frozenset({"40"})},
    ),
    "Table_S6M_residual_transport_pooled.csv": CsvContract(
        columns=S6M_COLUMNS,
        rows=200,
        key_columns=("learner", "window_id", "score_stratum"),
        expected_keys=_grid(LEARNERS, WINDOWS, STRATA_ONE_BASED),
        exact_domains={
            "score_stratum": frozenset(STRATA_ONE_BASED),
            "sharp_directional_discrepancy_comparison": frozenset(
                {
                    "larger_target_residual_discrepancy_dominates",
                    "smaller_target_residual_discrepancy_dominates",
                    "directional_discrepancies_not_robustly_ordered",
                }
            ),
            "v5_q_and_coverage_reconciled": frozenset({"True"}),
        },
    ),
    "Table_S6N_marginal_score_outcome_gap.csv": CsvContract(
        columns=S6N_COLUMNS,
        rows=5,
        key_columns=("learner",),
        expected_keys=_grid(LEARNERS),
        exact_domains={
            "candidate_rows": frozenset({str(PRIMARY_CANDIDATES)}),
            "resolved_rows": frozenset({str(PRIMARY_RESOLVED)}),
            "unresolved_outcomes": frozenset({str(PRIMARY_UNRESOLVED)}),
            "joint_endpoint_attainment": frozenset({"True"}),
        },
    ),
    "Table_S6O_calibrator_sensitivity_cells.csv": CsvContract(
        columns=S6O_COLUMNS,
        rows=192,
        key_columns=("method", "window_id", "conformal_group"),
        expected_keys=_grid(CALIBRATOR_METHODS, WINDOWS, CALIBRATOR_GROUPS),
        exact_domains={
            "method": frozenset(CALIBRATOR_METHODS),
            "taxonomy_groups": frozenset({"5"}),
            "role": frozenset({"primary_oot"}),
            "conformal_group": frozenset(CALIBRATOR_GROUPS),
            "coverage_upper_below_nominal": BOOLEAN_DOMAIN,
        },
    ),
    "Table_S6P_calibrator_pairwise_shared_completion.csv": CsvContract(
        columns=S6P_COLUMNS,
        rows=288,
        key_columns=("method_a", "method_b", "window_id", "conformal_group"),
        expected_keys=CALIBRATOR_PAIR_KEYS,
        exact_domains={
            "method_a": frozenset(CALIBRATOR_METHODS),
            "method_b": frozenset(CALIBRATOR_METHODS),
            "taxonomy_groups": frozenset({"5"}),
            "role": frozenset({"primary_oot"}),
            "conformal_group": frozenset(CALIBRATOR_GROUPS),
            "shared_loanwise_completion": frozenset({"True"}),
        },
    ),
    "Table_S6Q_binary_phase_target_support.csv": CsvContract(
        columns=S6Q_COLUMNS,
        rows=200,
        key_columns=("learner", "window_id", "conformal_group"),
        expected_keys=_grid(LEARNERS, WINDOWS, GROUPS_ZERO_BASED),
        exact_domains={
            "taxonomy_groups": frozenset({"5"}),
            "score_stratum": frozenset(STRATA_ONE_BASED),
            "conformal_group": frozenset(GROUPS_ZERO_BASED),
            "alpha": frozenset({"0.1"}),
            "phase_prevalence_at_or_below_boundary": BOOLEAN_DOMAIN,
            "threshold_below_half": BOOLEAN_DOMAIN,
            "max_score_below_half_condition": BOOLEAN_DOMAIN,
            "target_max_below_positive_label_boundary": BOOLEAN_DOMAIN,
            "positive_label_excluded_from_every_target_set": BOOLEAN_DOMAIN,
        },
    ),
    "Table_S9G_decision_catalog_metric_separation.csv": CsvContract(
        columns=S9G_COLUMNS,
        rows=3,
        key_columns=("metric",),
        expected_keys=_grid(METRICS),
        exact_domains={
            "target_blocks": frozenset({"15"}),
            "all_target_blocks_exceed_development": frozenset({"True"}),
        },
    ),
    "Table_S9H_decision_catalog_target_blocks.csv": CsvContract(
        columns=S9H_COLUMNS,
        rows=45,
        key_columns=("period", "metric"),
        expected_keys=_grid(ISSUE_MONTHS, METRICS),
        exact_domains={
            "policies": frozenset({"240"}),
            "classification": frozenset({"definitely_exceeds"}),
            "exceeds_all_development_upper": frozenset({"True"}),
        },
    ),
    "Table_S9I_funded_selection_track_estimands.csv": CsvContract(
        columns=S9I_COLUMNS,
        rows=96,
        key_columns=("window_id", "frontier_ruler", "frontier_coordinate", "gamma"),
        expected_keys=_grid(WINDOWS, RULERS, COORDINATES, GAMMAS),
        exact_domains={
            "role": frozenset({"primary_oot"}),
            "frontier_ruler": frozenset(RULERS),
            "frontier_coordinate": frozenset(COORDINATES),
            "gamma": frozenset(GAMMAS),
            "singleton_one_positions": frozenset({"0"}),
            "sharpness": frozenset({"cellwise_shared_binary_completion"}),
            "periods": frozenset({"15"}),
        },
    ),
    "Table_S9J_funded_selection_gamma_contrasts.csv": CsvContract(
        columns=S9J_COLUMNS,
        rows=48,
        key_columns=("window_id", "frontier_ruler", "frontier_coordinate"),
        expected_keys=_grid(WINDOWS, RULERS, COORDINATES),
        exact_domains={
            "role": frozenset({"primary_oot"}),
            "frontier_ruler": frozenset(RULERS),
            "frontier_coordinate": frozenset(COORDINATES),
            "gamma1_minus_gamma0_count_selected_fcp_direction": frozenset({"higher", "lower"}),
            "gamma1_minus_gamma0_invested_dollar_selected_fcp_direction": frozenset(
                {"higher", "crossing"}
            ),
            "gamma1_minus_gamma0_fixed_capital_decision_fcp_direction": frozenset(
                {"higher", "crossing"}
            ),
            "sharpness": frozenset({"cellwise_shared_binary_completion"}),
            "periods": frozenset({"15"}),
        },
    ),
    "Table_S9K_set_preserving_embedding_allocation_summary.csv": CsvContract(
        columns=S9K_COLUMNS,
        rows=3,
        key_columns=("ruler",),
        expected_keys=_grid(EMBEDDING_RULERS),
        exact_domains={
            "ruler": frozenset(EMBEDDING_RULERS),
            "set_diagnostic_rows": frozenset({"80"}),
            "sets_changed": frozenset({"0"}),
        },
    ),
    "Table_S9L_set_preserving_embedding_direction_census.csv": CsvContract(
        columns=S9L_COLUMNS,
        rows=6,
        key_columns=("contrast_family", "metric"),
        expected_keys=_grid(EMBEDDING_CONTRAST_FAMILIES, EMBEDDING_METRICS),
        exact_domains={
            "contrast_family": frozenset(EMBEDDING_CONTRAST_FAMILIES),
            "metric": frozenset(EMBEDDING_METRICS),
        },
    ),
}
README = """Anonymous machine-readable online supplement

These nineteen aggregate CSV files provide the complete calibration-fit, cell,
score-stratum, label-category, common-panel adjacent-threshold,
residual-distribution, marginal score-outcome, calibrator-pair, decision-catalog,
and funded-estimand rows summarized by PDF Tables S2C, S6B, S6D, S6F,
S6J--S6P, and S9G--S9L. S6C, S6E, S6M, and the stratum rows of S6O are
machine-readable-first layouts because their 192--200-row grids are unsuitable
for complete display in a reviewer PDF.

Historical display-label crosswalk (PDF -> canonical CSV stem):
S2 -> table6_credit_controls + tableS2_credit_prediction_metrics
S6 -> table1_coverage_windows + tableS6A_conformal_set_diagnostics
S7 Panels A--B -> table2_phase_transition
S7B -> tableS5_label_lag_sensitivity
S7C -> tableS9_missingness_encoding_sensitivity
S7F -> tableS11_fit_label_completion
S9 -> table5_two_ruler_tracks
S9B--S9C -> tableS6_endpoint_availability_sensitivity
S9D--S9E -> tableS7_portfolio_structure_sensitivity
S9F -> tableS12_allocation_granularity
S10 -> tableS1_named_comparators
S11 -> table4_direction_summary

Those aggregate presentation files are not duplicated in this reviewer
archive. Archive entries use their PDF suffix directly; for example,
Table_S6B_exchangeability_cells.csv is the complete machine-readable companion
to the PDF's Table S6B summary view.

The joint-block columns preserve the executed calculation while using active
reporting names. A threshold flag is a retrospective nominal reporting flag,
not post-selection FWER control, proof of conformal-theorem failure, or proof
of exchangeability when absent. Label-Mondrian rows are a deterministic
sensitivity, not a selected repair, class-conditional transport guarantee, or
fairness result. No row contains author identity, repository coordinates,
commits, tags, hashes, local paths, or loan-level data.

The common-panel tables report all 175 stratum transitions and all 35
learner-level aggregates. Their sharp all-candidate response bounds assign each
unresolved loan once and share that completion across both thresholds. They are
descriptive finite-archive identities, not temporal-validity tests, slopes,
rankings, or selected-transition evidence.

The residual tables report cellwise sharp ranges for two one-sided empirical
CDF discrepancies, not a KS test or global stochastic ordering. The marginal
table is finite-archive partial identification, not individual or conditional
calibration. Decision-catalog rows concern the worst loss over the fixed
catalog, not every policy. Funded-estimand rows keep count, invested-dollar,
and fixed-capital weightings distinct and do not establish FCR or selected-set
validity.

The calibrator tables report all four same-sample 2011 fit diagnostics, all 192
pooled-plus-stratum evaluation cells, and all 288 pairwise cells under one
common uncalibrated-probability taxonomy. Pairwise bounds share each loanwise
unresolved completion across the two methods. These retrospective rows select
no calibrator, rank no method from the fit diagnostics, transfer no Venn--Abers
multiprobability guarantee to the scalar score, and perform no portfolio
optimization. The separate primary portfolio analysis already uses the
pre-existing Platt score; none of the three alternative maps is propagated.

The binary phase target-support table reports all 200 learner--window--stratum
joins. Its 87 label-one exclusions are exact set-membership statements for the
frozen archive scores. The resolved-miss fractions only localize observed
misses by stratum; they are not class-conditional validity, a complete causal
decomposition, or evidence that target prevalence is constant within strata.

The set-preserving embedding tables report the full allocation-change and
descriptive direction censuses from a retrospective post-inspection
sensitivity. Identical binary prediction sets do not select an embedding,
ruler, coordinate, or policy, and the reported directions are neither causal
nor confirmatory.

"""
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
ZIP_ONLY_FORBIDDEN_LITERALS = (
    "/users/",
    "carlos",
    "vergara rojas",
    "cavr94@gmail.com",
    "protocol_commit",
    "protocol_tag",
    "run_tag",
    "sha256",
    "reject_flag",
    "hierarchical_fwer",
    "minimum_reference_score_stratum",
    "minimum_reference_excess_miss_rate_pp",
)
FORBIDDEN_FINGERPRINTS = tuple(
    dict.fromkeys(
        literal.encode("utf-8")
        for literal in (*REVIEWER_FORBIDDEN_LITERALS, *ZIP_ONLY_FORBIDDEN_LITERALS)
    )
)
FORBIDDEN_FINGERPRINT_PATTERNS = (
    *(
        (
            label,
            re.compile(pattern.pattern.encode("ascii"), pattern.flags & ~re.RegexFlag.UNICODE),
        )
        for label, pattern in REVIEWER_FORBIDDEN_PATTERNS
    ),
    (
        "protocol or run-tag value",
        re.compile(
            rb"\b(?:protocol/)?ijds-[a-z0-9_.-]+-20\d{2}-\d{2}-\d{2}-v\d+[a-z]?\b", re.IGNORECASE
        ),
    ),
)


TEXT_COLUMNS: Final = frozenset(
    {
        "estimand",
        "method",
        "method_a",
        "method_b",
        "learner",
        "learner_label",
        "score_column",
        "lower_endpoint_completion",
        "upper_endpoint_completion",
        "window",
        "window_id",
        "role",
        "pair_id",
        "transition",
        "window_from",
        "window_to",
        "identification_state_at_nominal",
        "baseline_identification_state_at_nominal",
        "period",
        "metric",
        "classification",
        "frontier_ruler",
        "ruler",
        "contrast_family",
        "candidate_id",
        "gamma0_candidate_id",
        "gamma1_candidate_id",
        "sharpness",
        "sharp_directional_discrepancy_comparison",
        "gamma1_minus_gamma0_count_selected_fcp_direction",
        "gamma1_minus_gamma0_invested_dollar_selected_fcp_direction",
        "gamma1_minus_gamma0_fixed_capital_decision_fcp_direction",
    }
)
BOOLEAN_COLUMNS: Final = frozenset(
    {
        "sharp_binary_completion",
        "all_calibration_threshold_ties_singleton",
        "meets_locked_nominal_holm_threshold",
        "continuous_threshold_tie_singleton",
        "meets_locked_nominal_within_cell_threshold",
        "conditional_gap_defined",
        "sharp_endpoint_delta_reported",
        "threshold_is_infinite",
        "score_stratum_present",
        "conditional_coverage_defined",
        "coverage_upper_below_nominal",
        "v5_q_and_coverage_reconciled",
        "joint_endpoint_attainment",
        "all_target_blocks_exceed_development",
        "exceeds_all_development_upper",
        "same_sample_descriptive_only",
        "selection_metric",
        "shared_loanwise_completion",
        "phase_prevalence_at_or_below_boundary",
        "threshold_below_half",
        "max_score_below_half_condition",
        "target_max_below_positive_label_boundary",
        "positive_label_excluded_from_every_target_set",
    }
)
OPTIONAL_NUMERIC_COLUMNS: Final = frozenset(
    {
        "venn_multiprobability_gap_mean",
        "venn_multiprobability_gap_q50",
    }
)
EXPLICIT_INTEGER_COLUMNS: Final = frozenset(
    {
        "learner_order",
        "label",
        "pair_index",
        "score_stratum",
        "conformal_group",
        "taxonomy_groups",
        "stratum_tests",
        "score_strata_observed",
        "threshold_cells",
        "infinite_threshold_cells",
        "strata_rows",
        "beta_a",
        "beta_b",
        "fit_residual_below_threshold",
        "fit_residual_equal_threshold",
        "fit_residual_above_threshold",
        "resolved_misses",
        "unresolved_min_misses",
        "unresolved_max_misses",
        "misses_min",
        "misses_max",
        "threshold_sign",
        "threshold_decrease_strata",
        "threshold_equal_strata",
        "threshold_increase_strata",
        "strata_with_non_singleton_calibration_threshold_ties",
        "pooled_cells",
        "unresolved_outcomes",
        "identified_grid_points",
        "target_blocks",
        "policies",
        "periods",
        "selected_positions",
        "resolved_positions",
        "unresolved_positions",
        "empty_set_positions",
        "full_set_positions",
        "singleton_zero_positions",
        "singleton_one_positions",
        "funded_union_positions",
        "funded_overlap_positions",
        "unresolved_union_positions",
        "gamma0_selected_positions",
        "gamma1_selected_positions",
        "noncontrol_theta_contrasts",
        "allocation_changes_gt_1e10",
        "sets_changed",
        "cells",
        "negative",
        "positive",
        "not_directionally_separated_at_tolerance",
        "within_tolerance",
        "fit_defaults",
        "phase_margin",
        "target_resolved_misses",
        "resolved_misses_in_exclusion_strata",
        "resolved_misses_all_strata",
    }
)


def _table_label(name: str) -> str:
    return name.removeprefix("Table_").split("_", maxsplit=1)[0]


def _fail(name: str, path: Path, detail: str) -> NoReturn:
    raise RuntimeError(f"Unexpected {_table_label(name)} reviewer schema in {path}: {detail}")


def _as_float(name: str, path: Path, row_number: int, column: str, raw: str) -> float:
    try:
        value = float(raw)
    except ValueError:
        _fail(name, path, f"row {row_number} column {column!r} is not numeric: {raw!r}.")
    if not math.isfinite(value):
        _fail(name, path, f"row {row_number} column {column!r} is not finite: {raw!r}.")
    return value


def _as_int(name: str, path: Path, row_number: int, column: str, raw: str) -> int:
    if re.fullmatch(r"-?(?:0|[1-9][0-9]*)", raw) is None:
        _fail(name, path, f"row {row_number} column {column!r} is not an exact integer: {raw!r}.")
    return int(raw)


def _is_integer_column(column: str) -> bool:
    return column in EXPLICIT_INTEGER_COLUMNS or column.endswith(
        ("_rows", "_count", "_numerator", "_rank")
    )


def _validate_numeric_domain(
    name: str,
    path: Path,
    row_number: int,
    column: str,
    value: float,
) -> None:
    lower: float | None = None
    upper: float | None = None
    if "log_p_value" in column and "neg_log10" not in column:
        upper = 0.0
    elif "neg_log10_p_value" in column:
        lower = 0.0
    elif "p_value" in column or column.endswith("_share") or "critical_value" in column:
        lower, upper = 0.0, 1.0
    elif "coverage" in column:
        if any(token in column for token in ("_gap_", "_delta_", "_difference", "_minus_")):
            lower, upper = -1.0, 1.0
        else:
            lower, upper = 0.0, 1.0
    elif (
        "miss_rate" in column
        or column == "alpha"
        or column
        in {
            "mean_score",
            "outcome_mean_lower",
            "outcome_mean_upper",
            "fit_residual_quantile",
            "fit_score_min",
            "fit_score_max",
            "score_min",
            "score_max",
            "threshold",
            "threshold_from",
            "threshold_to",
            "threshold_low",
            "threshold_high",
            "identification_width",
            "label_prevalence_lower",
            "label_prevalence_upper",
            "default_rate",
            "roc_auc",
            "brier",
            "ece_10",
            "fit_prevalence",
            "mean_width",
            "lower_positive_share",
            "upper_saturated_share",
            "width_q00",
            "width_q10",
            "width_q25",
            "width_q50",
            "width_q75",
            "width_q90",
            "width_q100",
            "venn_multiprobability_gap_mean",
            "venn_multiprobability_gap_q50",
        }
    ):
        lower, upper = 0.0, 1.0
    elif column.endswith("average_set_size"):
        lower, upper = 0.0, 2.0
    elif column in {
        "threshold_delta",
        "resolved_delta_rate",
        "delta_lower",
        "delta_upper",
        "delta_width",
    }:
        lower, upper = -1.0, 1.0
    elif column in {"score_sum", "null_expected_misses", "log_loss"}:
        lower = 0.0
    elif column in {"allocation_change_fraction", "maximum_upper_contraction"}:
        lower, upper = 0.0, 1.0
    elif column == "maximum_normalized_exposure_distance":
        lower, upper = 0.0, 2.0
    if lower is not None and value < lower:
        _fail(name, path, f"row {row_number} column {column!r} is below {lower}: {value}.")
    if upper is not None and value > upper:
        _fail(name, path, f"row {row_number} column {column!r} exceeds {upper}: {value}.")


def _validate_metadata(
    name: str,
    path: Path,
    row_number: int,
    row: dict[str, str],
) -> None:
    learner = row.get("learner")
    if learner is not None:
        expected_label, expected_score, expected_order = LEARNER_METADATA[learner]
        if row.get("learner_label") != expected_label:
            _fail(name, path, f"row {row_number} learner label does not match {learner!r}.")
        if "score_column" in row and row["score_column"] != expected_score:
            _fail(name, path, f"row {row_number} score column does not match {learner!r}.")
        if "learner_order" in row and row["learner_order"] != expected_order:
            _fail(name, path, f"row {row_number} learner order does not match {learner!r}.")

    if "window_id" in row and "window" in row:
        expected_window = WINDOW_METADATA[row["window_id"]]
        if row["window"] != expected_window:
            _fail(name, path, f"row {row_number} window label and ID disagree.")

    if (
        "conformal_group" in row
        and "score_stratum" in row
        and int(row["score_stratum"]) != int(row["conformal_group"]) + 1
    ):
        _fail(name, path, f"row {row_number} score stratum is not conformal group plus one.")

    if "pair_index" in row:
        expected = PAIR_METADATA[row["pair_index"]]
        observed = (row["pair_id"], row["transition"], row["window_from"], row["window_to"])
        if observed != expected:
            _fail(name, path, f"row {row_number} adjacent-window pair metadata disagree.")


def _validate_bounds(
    name: str,
    path: Path,
    row_number: int,
    row: dict[str, str],
) -> None:
    for column in row:
        if not column.endswith("_lower"):
            continue
        upper_column = f"{column[:-6]}_upper"
        if upper_column not in row:
            continue
        lower = float(row[column])
        upper = float(row[upper_column])
        if lower > upper:
            _fail(
                name,
                path,
                f"row {row_number} reverses bounds {column!r} and {upper_column!r}.",
            )


def _require_close(
    name: str,
    path: Path,
    row_number: int,
    label: str,
    observed: float,
    expected: float,
    *,
    tolerance: float = 5e-13,
) -> None:
    if not math.isclose(observed, expected, rel_tol=tolerance, abs_tol=tolerance):
        _fail(
            name,
            path,
            f"row {row_number} fails {label}: observed {observed!r}, expected {expected!r}.",
        )


def _validate_set_partition(
    name: str,
    path: Path,
    row_number: int,
    row: dict[str, str],
    *,
    prefix: str = "",
) -> None:
    count = sum(
        int(row[f"{prefix}set_{set_name}_count"])
        for set_name in ("empty", "zero_only", "one_only", "both")
    )
    candidates = int(row[f"{prefix}candidate_rows"])
    if count != candidates:
        _fail(name, path, f"row {row_number} {prefix}binary-set counts do not partition rows.")


def _validate_set_metrics(
    name: str,
    path: Path,
    row_number: int,
    row: dict[str, str],
    *,
    prefix: str = "",
) -> None:
    candidates = int(row[f"{prefix}candidate_rows"])
    counts = {
        set_name: int(row[f"{prefix}set_{set_name}_count"])
        for set_name in ("empty", "zero_only", "one_only", "both")
    }
    for set_name, count in counts.items():
        _require_close(
            name,
            path,
            row_number,
            f"{prefix}set share {set_name}",
            float(row[f"{prefix}set_{set_name}_share"]),
            count / candidates,
        )
    _require_close(
        name,
        path,
        row_number,
        f"{prefix}average set size",
        float(row[f"{prefix}average_set_size"]),
        (counts["zero_only"] + counts["one_only"] + 2 * counts["both"]) / candidates,
    )
    _require_close(
        name,
        path,
        row_number,
        f"{prefix}singleton share",
        float(row[f"{prefix}singleton_share"]),
        (counts["zero_only"] + counts["one_only"]) / candidates,
    )


def _validate_row_identities(
    name: str,
    path: Path,
    row_number: int,
    row: dict[str, str],
) -> None:
    if name in {
        "Table_S6C_exchangeability_strata.csv",
        "Table_S6D_label_mondrian_cells.csv",
        "Table_S6E_label_mondrian_strata.csv",
        "Table_S6J_common_panel_threshold_response_strata.csv",
        "Table_S6K_common_panel_threshold_response_learners.csv",
        "Table_S6O_calibrator_sensitivity_cells.csv",
        "Table_S6P_calibrator_pairwise_shared_completion.csv",
    }:
        candidate_column = (
            "candidate_stratum_rows"
            if name == "Table_S6E_label_mondrian_strata.csv"
            else "candidate_rows"
        )
        if int(row[candidate_column]) != int(row["resolved_rows"]) + int(row["unresolved_rows"]):
            _fail(name, path, f"row {row_number} resolved and unresolved rows do not partition.")

    if name == "Table_S2C_calibrator_fit_diagnostics.csv":
        gap = row["venn_multiprobability_gap_mean"]
        if (row["method"] == "venn_abers") != (gap != ""):
            _fail(
                name,
                path,
                f"row {row_number} Venn-only multiprobability diagnostic is mis-scoped.",
            )

    if name == "Table_S6O_calibrator_sensitivity_cells.csv":
        candidates = int(row["candidate_rows"])
        if int(row["rows"]) != candidates:
            _fail(name, path, f"row {row_number} duplicates inconsistent candidate counts.")
        if row["conformal_group"] == "-1" and (
            candidates,
            int(row["resolved_rows"]),
            int(row["unresolved_rows"]),
        ) != (PRIMARY_CANDIDATES, PRIMARY_RESOLVED, PRIMARY_UNRESOLVED):
            _fail(name, path, f"row {row_number} leaves the fixed primary endpoint census.")
        _validate_set_partition(name, path, row_number, row)
        _validate_set_metrics(name, path, row_number, row)
        width_quantiles = [
            float(row[column])
            for column in (
                "width_q00",
                "width_q10",
                "width_q25",
                "width_q50",
                "width_q75",
                "width_q90",
                "width_q100",
            )
        ]
        if width_quantiles != sorted(width_quantiles):
            _fail(name, path, f"row {row_number} width quantiles are not monotone.")
        expected_flag = str(float(row["coverage_upper"]) < 0.90)
        if row["coverage_upper_below_nominal"] != expected_flag:
            _fail(name, path, f"row {row_number} has an inconsistent nominal-coverage flag.")
        gaps = (
            row["venn_multiprobability_gap_mean"],
            row["venn_multiprobability_gap_q50"],
        )
        if (row["method"] == "venn_abers") != all(gap != "" for gap in gaps):
            _fail(
                name,
                path,
                f"row {row_number} Venn-only multiprobability diagnostics are mis-scoped.",
            )
        if row["method"] != "venn_abers" and any(gap != "" for gap in gaps):
            _fail(
                name,
                path,
                f"row {row_number} leaks a Venn-only diagnostic to another method.",
            )

    if name == "Table_S6P_calibrator_pairwise_shared_completion.csv":
        if row["conformal_group"] == "-1" and (
            int(row["candidate_rows"]),
            int(row["resolved_rows"]),
            int(row["unresolved_rows"]),
        ) != (PRIMARY_CANDIDATES, PRIMARY_RESOLVED, PRIMARY_UNRESOLVED):
            _fail(name, path, f"row {row_number} leaves the fixed primary endpoint census.")
        lower = float(row["coverage_difference_lower"])
        resolved = float(row["coverage_difference_resolved"])
        upper = float(row["coverage_difference_upper"])
        if not lower <= resolved <= upper:
            _fail(name, path, f"row {row_number} reverses the shared-completion bounds.")

    if name == "Table_S6Q_binary_phase_target_support.csv":
        fit_rows = int(row["fit_rows"])
        fit_defaults = int(row["fit_defaults"])
        boundary_count = int(row["boundary_count"])
        threshold = float(row["frozen_threshold"])
        target_score_max = float(row["target_score_max"])
        positive_boundary = float(row["positive_label_boundary"])
        support = target_score_max < positive_boundary
        low = threshold < 0.5
        _require_close(
            name,
            path,
            row_number,
            "fit default prevalence",
            float(row["fit_default_prevalence"]),
            fit_defaults / fit_rows,
        )
        _require_close(
            name,
            path,
            row_number,
            "finite phase boundary rate",
            float(row["phase_boundary_rate"]),
            boundary_count / fit_rows,
        )
        _require_close(
            name,
            path,
            row_number,
            "positive-label score boundary",
            positive_boundary,
            1.0 - threshold,
        )
        expected_flags = {
            "phase_prevalence_at_or_below_boundary": fit_defaults <= boundary_count,
            "threshold_below_half": low,
            "target_max_below_positive_label_boundary": support,
            "positive_label_excluded_from_every_target_set": low and support,
        }
        if int(row["phase_margin"]) != fit_defaults - boundary_count:
            _fail(name, path, f"row {row_number} has an inconsistent integer phase margin.")
        if any(row[column] != str(value) for column, value in expected_flags.items()):
            _fail(name, path, f"row {row_number} has an inconsistent support flag.")
        if not (
            0
            <= int(row["target_resolved_misses"])
            <= int(row["target_resolved_rows"])
            <= int(row["target_candidate_rows"])
        ):
            _fail(name, path, f"row {row_number} has invalid target row counts.")

    if name == "Table_S6D_label_mondrian_cells.csv":
        if (
            int(row["candidate_rows"]),
            int(row["resolved_rows"]),
            int(row["unresolved_rows"]),
        ) != (PRIMARY_CANDIDATES, PRIMARY_RESOLVED, PRIMARY_UNRESOLVED):
            _fail(name, path, f"row {row_number} leaves the fixed primary endpoint census.")
        if int(row["resolved_rows"]) != int(row["resolved_y0_rows"]) + int(row["resolved_y1_rows"]):
            _fail(name, path, f"row {row_number} resolved label rows do not partition.")
        _validate_set_partition(name, path, row_number, row)
        _validate_set_partition(name, path, row_number, row, prefix="baseline_")
        _validate_set_metrics(name, path, row_number, row)
        _validate_set_metrics(name, path, row_number, row, prefix="baseline_")

    if name == "Table_S6E_label_mondrian_strata.csv":
        if row["candidate_rows"] != row["candidate_stratum_rows"]:
            _fail(name, path, f"row {row_number} duplicates inconsistent candidate counts.")
        if int(row["resolved_rows"]) != int(row["resolved_y0_rows"]) + int(row["resolved_y1_rows"]):
            _fail(name, path, f"row {row_number} resolved label rows do not partition.")
        _validate_set_partition(name, path, row_number, row)
        _validate_set_partition(name, path, row_number, row, prefix="baseline_")
        _validate_set_metrics(name, path, row_number, row)
        _validate_set_metrics(name, path, row_number, row, prefix="baseline_")

    if name in {
        "Table_S6D_label_mondrian_cells.csv",
        "Table_S6E_label_mondrian_strata.csv",
    }:
        resolved = int(row["resolved_rows"])
        for prefix in ("", "baseline_"):
            _require_close(
                name,
                path,
                row_number,
                f"{prefix}resolved coverage",
                float(row[f"{prefix}coverage_resolved"]),
                int(row[f"{prefix}resolved_covered_rows"]) / resolved,
            )

    if name == "Table_S6F_label_mondrian_categories.csv":
        unresolved = int(row["unresolved_stratum_rows"])
        for prefix in ("", "baseline_"):
            covered = int(row[f"{prefix}unresolved_label_covered_if_assigned_rows"])
            missed = int(row[f"{prefix}unresolved_label_missed_if_assigned_rows"])
            if covered + missed != unresolved:
                _fail(
                    name,
                    path,
                    f"row {row_number} {prefix}unresolved assigned-label rows do not partition.",
                )

    if name == "Table_S6J_common_panel_threshold_response_strata.csv":
        threshold_from = float(row["threshold_from"])
        threshold_to = float(row["threshold_to"])
        _require_close(
            name,
            path,
            row_number,
            "threshold lower endpoint",
            float(row["threshold_low"]),
            min(threshold_from, threshold_to),
        )
        _require_close(
            name,
            path,
            row_number,
            "threshold upper endpoint",
            float(row["threshold_high"]),
            max(threshold_from, threshold_to),
        )
        _require_close(
            name,
            path,
            row_number,
            "threshold signed change",
            float(row["threshold_delta"]),
            threshold_to - threshold_from,
        )
        expected_sign = (threshold_to > threshold_from) - (threshold_to < threshold_from)
        if int(row["threshold_sign"]) != expected_sign:
            _fail(name, path, f"row {row_number} threshold sign disagrees with thresholds.")

    if name in {
        "Table_S6J_common_panel_threshold_response_strata.csv",
        "Table_S6K_common_panel_threshold_response_learners.csv",
    }:
        candidates = int(row["candidate_rows"])
        resolved = int(row["resolved_rows"])
        lower_n = int(row["delta_lower_numerator"])
        upper_n = int(row["delta_upper_numerator"])
        width_n = int(row["delta_width_numerator"])
        resolved_delta_n = int(row["resolved_delta_numerator"])
        if width_n != upper_n - lower_n:
            _fail(name, path, f"row {row_number} sharp response numerator width is inconsistent.")
        if resolved_delta_n != int(row["resolved_y0_delta_numerator"]) + int(
            row["resolved_y1_delta_numerator"]
        ):
            _fail(name, path, f"row {row_number} resolved class numerators do not add.")
        if resolved_delta_n != int(row["resolved_covered_to_numerator"]) - int(
            row["resolved_covered_from_numerator"]
        ):
            _fail(name, path, f"row {row_number} resolved covered-count change is inconsistent.")
        for label, observed, expected in (
            ("delta lower rate", float(row["delta_lower"]), lower_n / candidates),
            ("delta upper rate", float(row["delta_upper"]), upper_n / candidates),
            ("delta width rate", float(row["delta_width"]), width_n / candidates),
            ("resolved delta rate", float(row["resolved_delta_rate"]), resolved_delta_n / resolved),
        ):
            _require_close(name, path, row_number, label, observed, expected)

    if name == "Table_S6K_common_panel_threshold_response_learners.csv":
        if (
            int(row["candidate_rows"]),
            int(row["resolved_rows"]),
            int(row["unresolved_rows"]),
        ) != (PRIMARY_CANDIDATES, PRIMARY_RESOLVED, PRIMARY_UNRESOLVED):
            _fail(name, path, f"row {row_number} leaves the fixed primary endpoint census.")
        if (
            sum(
                int(row[column])
                for column in (
                    "threshold_decrease_strata",
                    "threshold_equal_strata",
                    "threshold_increase_strata",
                )
            )
            != 5
        ):
            _fail(name, path, f"row {row_number} threshold-direction strata do not partition five.")

    if name == "Table_S9K_set_preserving_embedding_allocation_summary.csv":
        contrasts = int(row["noncontrol_theta_contrasts"])
        changes = int(row["allocation_changes_gt_1e10"])
        if contrasts <= 0:
            _fail(name, path, f"row {row_number} has no non-control theta contrasts.")
        if changes > contrasts:
            _fail(name, path, f"row {row_number} allocation changes exceed contrasts.")
        _require_close(
            name,
            path,
            row_number,
            "allocation-change fraction",
            float(row["allocation_change_fraction"]),
            changes / contrasts,
        )

    if name == "Table_S9L_set_preserving_embedding_direction_census.csv":
        directional_cells = sum(
            int(row[column])
            for column in (
                "negative",
                "positive",
                "not_directionally_separated_at_tolerance",
                "within_tolerance",
            )
        )
        if directional_cells != int(row["cells"]):
            _fail(name, path, f"row {row_number} direction counts do not partition cells.")


def _read_validated_reviewer_csv(
    name: str,
    path: Path,
) -> tuple[bytes, list[dict[str, str]]]:
    contract = TABLE_CONTRACTS.get(name)
    if contract is None:
        raise ValueError(f"No machine-readable supplement contract for {name!r}.")
    payload = path.read_bytes()
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail(name, path, f"payload is not strict UTF-8 ({exc}).")
    try:
        parsed = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except csv.Error as exc:
        _fail(name, path, f"malformed CSV ({exc}).")
    if not parsed:
        _fail(name, path, "file is empty.")
    header = tuple(parsed[0])
    if header != contract.columns:
        _fail(name, path, f"header is {header!r}; expected {contract.columns!r}.")
    rows: list[dict[str, str]] = []
    for row_number, values in enumerate(parsed[1:], start=2):
        if len(values) != len(header):
            _fail(
                name,
                path,
                f"row {row_number} has {len(values)} fields; expected {len(header)}.",
            )
        row = dict(zip(header, values, strict=True))
        for column, domain in contract.exact_domains.items():
            if row[column] not in domain:
                _fail(
                    name,
                    path,
                    f"row {row_number} column {column!r} has out-of-domain value "
                    f"{row[column]!r}; expected one of {sorted(domain)!r}.",
                )
        for column, raw in row.items():
            if column in TEXT_COLUMNS or column in BOOLEAN_COLUMNS:
                continue
            if raw == "" and column in OPTIONAL_NUMERIC_COLUMNS:
                continue
            value = _as_float(name, path, row_number, column, raw)
            _validate_numeric_domain(name, path, row_number, column, value)
            if _is_integer_column(column):
                integer = _as_int(name, path, row_number, column, raw)
                if integer < 0 and not (
                    column in {"threshold_sign", "conformal_group", "phase_margin"}
                    or ("delta" in column and column.endswith("_numerator"))
                ):
                    _fail(name, path, f"row {row_number} column {column!r} is negative.")
        _validate_metadata(name, path, row_number, row)
        _validate_bounds(name, path, row_number, row)
        _validate_row_identities(name, path, row_number, row)
        rows.append(row)

    if len(rows) != contract.rows:
        _fail(name, path, f"has {len(rows)} data rows; expected {contract.rows}.")
    keys = [tuple(row[column] for column in contract.key_columns) for row in rows]
    duplicates = sorted(key for key, count in Counter(keys).items() if count != 1)
    if duplicates:
        _fail(name, path, f"duplicate composite keys {duplicates[:5]!r}.")
    observed_keys = frozenset(keys)
    if observed_keys != contract.expected_keys:
        missing = sorted(contract.expected_keys - observed_keys)
        extra = sorted(observed_keys - contract.expected_keys)
        _fail(
            name,
            path,
            f"grid mismatch; missing={missing[:5]!r}, extra={extra[:5]!r}.",
        )
    return payload, rows


def _reviewer_csv_payload(name: str, path: Path) -> bytes:
    payload, _ = _read_validated_reviewer_csv(name, path)
    return payload


def _validate_partitioned_primary_census(
    name: str,
    path: Path,
    rows: list[dict[str, str]],
    *,
    candidate_column: str = "candidate_rows",
    resolved_column: str = "resolved_rows",
    unresolved_column: str = "unresolved_rows",
    group_columns: tuple[str, ...] = ("learner", "window_id"),
) -> None:
    totals: dict[tuple[str, ...], list[int]] = defaultdict(lambda: [0, 0, 0])
    for row in rows:
        key = tuple(row[column] for column in group_columns)
        totals[key][0] += int(row[candidate_column])
        totals[key][1] += int(row[resolved_column])
        totals[key][2] += int(row[unresolved_column])
    expected = [PRIMARY_CANDIDATES, PRIMARY_RESOLVED, PRIMARY_UNRESOLVED]
    failures = sorted(key for key, values in totals.items() if values != expected)
    if failures:
        _fail(name, path, f"partitioned primary census fails for keys {failures[:5]!r}.")


def _validate_cross_table_contract(
    paths: dict[str, Path],
    rows_by_name: dict[str, list[dict[str, str]]],
) -> None:
    s2c_name = "Table_S2C_calibrator_fit_diagnostics.csv"
    s6b_name = "Table_S6B_exchangeability_cells.csv"
    s6c_name = "Table_S6C_exchangeability_strata.csv"
    s6d_name = "Table_S6D_label_mondrian_cells.csv"
    s6e_name = "Table_S6E_label_mondrian_strata.csv"
    s6f_name = "Table_S6F_label_mondrian_categories.csv"
    s6j_name = "Table_S6J_common_panel_threshold_response_strata.csv"
    s6k_name = "Table_S6K_common_panel_threshold_response_learners.csv"
    s6o_name = "Table_S6O_calibrator_sensitivity_cells.csv"
    s6p_name = "Table_S6P_calibrator_pairwise_shared_completion.csv"
    s6q_name = "Table_S6Q_binary_phase_target_support.csv"
    _validate_partitioned_primary_census(s6c_name, paths[s6c_name], rows_by_name[s6c_name])
    _validate_partitioned_primary_census(
        s6e_name,
        paths[s6e_name],
        rows_by_name[s6e_name],
        candidate_column="candidate_stratum_rows",
    )
    _validate_partitioned_primary_census(
        s6j_name,
        paths[s6j_name],
        rows_by_name[s6j_name],
        group_columns=("learner", "pair_index"),
    )
    s6o_strata = [row for row in rows_by_name[s6o_name] if row["conformal_group"] != "-1"]
    _validate_partitioned_primary_census(
        s6o_name,
        paths[s6o_name],
        s6o_strata,
        group_columns=("method", "window_id"),
    )
    s6p_strata = [row for row in rows_by_name[s6p_name] if row["conformal_group"] != "-1"]
    _validate_partitioned_primary_census(
        s6p_name,
        paths[s6p_name],
        s6p_strata,
        group_columns=("method_a", "method_b", "window_id"),
    )

    fit_methods = {row["method"] for row in rows_by_name[s2c_name]}
    if fit_methods != set(CALIBRATOR_METHODS):
        _fail(s2c_name, paths[s2c_name], "the closed four-method fit census changed.")
    calibrator_cells = {
        (row["method"], row["window_id"], row["conformal_group"]): row
        for row in rows_by_name[s6o_name]
    }
    overall = [row for row in rows_by_name[s6o_name] if row["conformal_group"] == "-1"]
    below_by_method = Counter(
        row["method"] for row in overall if row["coverage_upper_below_nominal"] == "True"
    )
    if len(overall) != 32 or sum(below_by_method.values()) != 18:
        _fail(
            s6o_name,
            paths[s6o_name],
            "the complete 18-below/14-at-or-above pooled result census changed.",
        )
    if below_by_method != Counter({"platt": 8, "beta": 8, "isotonic": 1, "venn_abers": 1}):
        _fail(s6o_name, paths[s6o_name], "the pooled result census by method changed.")

    for row_number, pair in enumerate(rows_by_name[s6p_name], start=2):
        key_a = (pair["method_a"], pair["window_id"], pair["conformal_group"])
        key_b = (pair["method_b"], pair["window_id"], pair["conformal_group"])
        cell_a = calibrator_cells[key_a]
        cell_b = calibrator_cells[key_b]
        for column in (
            "taxonomy_groups",
            "role",
            "candidate_rows",
            "resolved_rows",
            "unresolved_rows",
        ):
            if pair[column] != cell_a[column] or pair[column] != cell_b[column]:
                _fail(
                    s6p_name,
                    paths[s6p_name],
                    f"S6O-to-S6P metadata disagree at row {row_number}.",
                )
        _require_close(
            s6p_name,
            paths[s6p_name],
            row_number,
            "S6O-to-S6P resolved coverage difference",
            float(pair["coverage_difference_resolved"]),
            float(cell_a["coverage_resolved"]) - float(cell_b["coverage_resolved"]),
        )
        if (
            pair["method_a"] == "platt"
            and pair["method_b"] == "beta"
            and any(
                float(pair[column]) != 0.0
                for column in (
                    "coverage_difference_resolved",
                    "coverage_difference_lower",
                    "coverage_difference_upper",
                )
            )
        ):
            _fail(
                s6p_name,
                paths[s6p_name],
                "the exact Platt--beta binary-coverage equivalence changed.",
            )

    exchangeability_strata: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows_by_name[s6c_name]:
        exchangeability_strata[(row["learner"], row["window_id"])].append(row)
    for row_number, cell in enumerate(rows_by_name[s6b_name], start=2):
        cell_key = (cell["learner"], cell["window_id"])
        strata = exchangeability_strata[cell_key]
        if len(strata) != int(cell["stratum_tests"]):
            _fail(
                s6b_name,
                paths[s6b_name],
                f"S6B-to-S6C stratum census fails at {cell_key!r}.",
            )
        if any(
            stratum[column] != cell[column]
            for stratum in strata
            for column in ("learner_label", "window", "taxonomy_groups")
        ):
            _fail(
                s6b_name,
                paths[s6b_name],
                f"S6B-to-S6C metadata disagree at {cell_key!r}.",
            )
        for cell_column, stratum_column in (
            ("minimum_stratum_log_p_value", "joint_block_reference_exact_log_p_value"),
            ("minimum_stratum_p_value", "joint_block_reference_exact_p_value"),
            ("source_cell_bonferroni_log_p_value", "source_within_cell_bonferroni_log_p_value"),
            ("source_cell_bonferroni_p_value", "source_within_cell_bonferroni_p_value"),
        ):
            _require_close(
                s6b_name,
                paths[s6b_name],
                row_number,
                f"S6B-to-S6C minimum {cell_column}",
                float(cell[cell_column]),
                min(float(stratum[stratum_column]) for stratum in strata),
            )
        non_singleton_ties = sum(
            stratum["continuous_threshold_tie_singleton"] == "False" for stratum in strata
        )
        if int(cell["strata_with_non_singleton_calibration_threshold_ties"]) != non_singleton_ties:
            _fail(
                s6b_name,
                paths[s6b_name],
                f"S6B-to-S6C tie census fails at {cell_key!r}.",
            )
        expected_all_singleton = "True" if non_singleton_ties == 0 else "False"
        if cell["all_calibration_threshold_ties_singleton"] != expected_all_singleton:
            _fail(
                s6b_name,
                paths[s6b_name],
                f"S6B-to-S6C all-singleton flag fails at {cell_key!r}.",
            )

    s6c_by_key = {
        (row["learner"], row["window_id"], row["conformal_group"]): row
        for row in rows_by_name[s6c_name]
    }
    support_by_learner_window: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    support_counts = Counter()
    for row_number, support_row in enumerate(rows_by_name[s6q_name], start=2):
        key = (
            support_row["learner"],
            support_row["window_id"],
            support_row["conformal_group"],
        )
        stratum = s6c_by_key[key]
        for support_column, stratum_column in (
            ("learner_label", "learner_label"),
            ("window", "window"),
            ("taxonomy_groups", "taxonomy_groups"),
            ("score_stratum", "score_stratum"),
        ):
            if support_row[support_column] != stratum[stratum_column]:
                _fail(
                    s6q_name,
                    paths[s6q_name],
                    f"S6C-to-S6Q field {support_column!r} disagrees at row {row_number}.",
                )
        for support_column, stratum_column in (
            ("fit_rows", "fit_rows"),
            ("finite_sample_rank", "finite_sample_rank"),
            ("frozen_threshold", "fit_residual_quantile"),
            ("target_candidate_rows", "candidate_rows"),
            ("target_score_max", "score_max"),
            ("target_resolved_rows", "resolved_rows"),
            ("target_resolved_misses", "resolved_misses"),
        ):
            _require_close(
                s6q_name,
                paths[s6q_name],
                row_number,
                f"S6C-to-S6Q field {support_column}",
                float(support_row[support_column]),
                float(stratum[stratum_column]),
            )
        if support_row["max_score_below_half_condition"] != str(
            float(stratum["fit_score_max"]) < 0.5
        ):
            _fail(
                s6q_name,
                paths[s6q_name],
                f"S6C-to-S6Q calibration support disagrees at row {row_number}.",
            )
        learner_window = (support_row["learner"], support_row["window_id"])
        support_by_learner_window[learner_window].append(support_row)
        if support_row["positive_label_excluded_from_every_target_set"] == "True":
            support_counts[int(support_row["conformal_group"])] += 1
    if support_counts != Counter({0: 40, 1: 40, 2: 7}):
        _fail(s6q_name, paths[s6q_name], "the complete 40/40/7/0/0 support census changed.")
    for learner_window, support_rows in support_by_learner_window.items():
        misses_all = sum(int(row["target_resolved_misses"]) for row in support_rows)
        misses_excluded = sum(
            int(row["target_resolved_misses"])
            for row in support_rows
            if row["positive_label_excluded_from_every_target_set"] == "True"
        )
        for row_number, row in enumerate(support_rows, start=2):
            if (
                int(row["resolved_misses_all_strata"]) != misses_all
                or int(row["resolved_misses_in_exclusion_strata"]) != misses_excluded
            ):
                _fail(
                    s6q_name,
                    paths[s6q_name],
                    f"resolved-miss localization fails at {learner_window!r}.",
                )
            _require_close(
                s6q_name,
                paths[s6q_name],
                row_number,
                "resolved-miss localization fraction",
                float(row["exclusion_strata_resolved_miss_fraction"]),
                misses_excluded / misses_all,
            )

    s6e = {
        (row["learner"], row["window_id"], row["score_stratum"]): row
        for row in rows_by_name[s6e_name]
    }
    categories: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows_by_name[s6f_name]:
        categories[(row["learner"], row["window_id"], row["score_stratum"])].append(row)
    for category_key, category_rows in categories.items():
        stratum = s6e[category_key]
        if {row["label"] for row in category_rows} != {"0", "1"}:
            _fail(s6f_name, paths[s6f_name], f"label grid is incomplete for {category_key!r}.")
        if {row["candidate_stratum_rows"] for row in category_rows} != {
            stratum["candidate_stratum_rows"]
        }:
            _fail(
                s6f_name,
                paths[s6f_name],
                f"candidate stratum rows disagree with S6E at {category_key!r}.",
            )
        if {row["unresolved_stratum_rows"] for row in category_rows} != {
            stratum["unresolved_rows"]
        }:
            _fail(
                s6f_name,
                paths[s6f_name],
                f"unresolved stratum rows disagree with S6E at {category_key!r}.",
            )
        if sum(int(row["resolved_label_rows"]) for row in category_rows) != int(
            stratum["resolved_rows"]
        ):
            _fail(
                s6f_name,
                paths[s6f_name],
                f"resolved label rows disagree with S6E at {category_key!r}.",
            )
        if sum(int(row["resolved_label_covered_rows"]) for row in category_rows) != int(
            stratum["resolved_covered_rows"]
        ):
            _fail(
                s6f_name,
                paths[s6f_name],
                f"resolved covered rows disagree with S6E at {category_key!r}.",
            )
        if sum(int(row["baseline_resolved_label_covered_rows"]) for row in category_rows) != int(
            stratum["baseline_resolved_covered_rows"]
        ):
            _fail(
                s6f_name,
                paths[s6f_name],
                f"baseline resolved covered rows disagree with S6E at {category_key!r}.",
            )
        for label, column in (("0", "resolved_y0_rows"), ("1", "resolved_y1_rows")):
            label_row = next(row for row in category_rows if row["label"] == label)
            if int(label_row["resolved_label_rows"]) != int(stratum[column]):
                _fail(
                    s6f_name,
                    paths[s6f_name],
                    f"resolved label partition disagrees with S6E at {category_key!r}.",
                )

    label_strata: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    label_categories: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows_by_name[s6e_name]:
        label_strata[(row["learner"], row["window_id"])].append(row)
    for row in rows_by_name[s6f_name]:
        label_categories[(row["learner"], row["window_id"])].append(row)
    for row_number, cell in enumerate(rows_by_name[s6d_name], start=2):
        cell_key = (cell["learner"], cell["window_id"])
        strata = label_strata[cell_key]
        cell_categories = label_categories[cell_key]
        if len(strata) != int(cell["score_strata_observed"]):
            _fail(s6d_name, paths[s6d_name], f"S6D-to-S6E stratum census fails at {cell_key!r}.")
        if len(cell_categories) != int(cell["threshold_cells"]):
            _fail(
                s6d_name,
                paths[s6d_name],
                f"S6D-to-S6F threshold-cell census fails at {cell_key!r}.",
            )
        infinite_thresholds = sum(
            category["threshold_is_infinite"] == "True" for category in cell_categories
        )
        if int(cell["infinite_threshold_cells"]) != infinite_thresholds:
            _fail(
                s6d_name,
                paths[s6d_name],
                f"S6D-to-S6F infinite-threshold census fails at {cell_key!r}.",
            )
        if any(
            stratum[column] != cell[column]
            for stratum in strata
            for column in ("learner_label", "window", "taxonomy_groups", "role")
        ):
            _fail(s6d_name, paths[s6d_name], f"S6D-to-S6E metadata disagree at {cell_key!r}.")

        integer_aggregates = {
            "candidate_rows": "candidate_stratum_rows",
            "resolved_rows": "resolved_rows",
            "unresolved_rows": "unresolved_rows",
            "resolved_y0_rows": "resolved_y0_rows",
            "resolved_y1_rows": "resolved_y1_rows",
            "resolved_covered_rows": "resolved_covered_rows",
            "set_empty_count": "set_empty_count",
            "set_zero_only_count": "set_zero_only_count",
            "set_one_only_count": "set_one_only_count",
            "set_both_count": "set_both_count",
            "baseline_candidate_rows": "baseline_candidate_rows",
            "baseline_resolved_rows": "resolved_rows",
            "baseline_unresolved_rows": "unresolved_rows",
            "baseline_resolved_y0_rows": "resolved_y0_rows",
            "baseline_resolved_y1_rows": "resolved_y1_rows",
            "baseline_resolved_covered_rows": "baseline_resolved_covered_rows",
            "baseline_set_empty_count": "baseline_set_empty_count",
            "baseline_set_zero_only_count": "baseline_set_zero_only_count",
            "baseline_set_one_only_count": "baseline_set_one_only_count",
            "baseline_set_both_count": "baseline_set_both_count",
        }
        for cell_column, stratum_column in integer_aggregates.items():
            expected = sum(int(stratum[stratum_column]) for stratum in strata)
            if int(cell[cell_column]) != expected:
                _fail(
                    s6d_name,
                    paths[s6d_name],
                    f"S6D-to-S6E aggregate {cell_column!r} fails at {cell_key!r}.",
                )

        candidate_rows = int(cell["candidate_rows"])
        resolved_rows = int(cell["resolved_rows"])
        weighted_metrics = {
            "average_set_size": (
                "average_set_size",
                "candidate_stratum_rows",
                candidate_rows,
            ),
            "singleton_share": ("singleton_share", "candidate_stratum_rows", candidate_rows),
            "coverage_resolved": ("coverage_resolved", "resolved_rows", resolved_rows),
            "coverage_lower": ("coverage_lower", "candidate_stratum_rows", candidate_rows),
            "coverage_upper": ("coverage_upper", "candidate_stratum_rows", candidate_rows),
            "baseline_average_set_size": (
                "baseline_average_set_size",
                "baseline_candidate_rows",
                candidate_rows,
            ),
            "baseline_singleton_share": (
                "baseline_singleton_share",
                "baseline_candidate_rows",
                candidate_rows,
            ),
            "baseline_coverage_resolved": (
                "baseline_coverage_resolved",
                "resolved_rows",
                resolved_rows,
            ),
            "baseline_coverage_lower": (
                "baseline_coverage_lower",
                "baseline_candidate_rows",
                candidate_rows,
            ),
            "baseline_coverage_upper": (
                "baseline_coverage_upper",
                "baseline_candidate_rows",
                candidate_rows,
            ),
        }
        for cell_column, (stratum_column, weight_column, denominator) in weighted_metrics.items():
            expected_weighted = (
                sum(
                    float(stratum[stratum_column]) * int(stratum[weight_column])
                    for stratum in strata
                )
                / denominator
            )
            _require_close(
                s6d_name,
                paths[s6d_name],
                row_number,
                f"S6D-to-S6E weighted {cell_column}",
                float(cell[cell_column]),
                expected_weighted,
            )

        for prefix in ("", "baseline_"):
            for set_name in ("empty", "zero_only", "one_only", "both"):
                expected_share = int(cell[f"{prefix}set_{set_name}_count"]) / candidate_rows
                _require_close(
                    s6d_name,
                    paths[s6d_name],
                    row_number,
                    f"S6D {prefix}set share {set_name}",
                    float(cell[f"{prefix}set_{set_name}_share"]),
                    expected_share,
                )

        categories_by_label = {
            label: [category for category in cell_categories if category["label"] == label]
            for label in ("0", "1")
        }
        for label, suffix in (("0", "y0"), ("1", "y1")):
            label_rows = categories_by_label[label]
            resolved_label_rows = sum(int(row["resolved_label_rows"]) for row in label_rows)
            for prefix in ("", "baseline_"):
                covered = sum(
                    int(row[f"{prefix}resolved_label_covered_rows"]) for row in label_rows
                )
                _require_close(
                    s6d_name,
                    paths[s6d_name],
                    row_number,
                    f"S6D-to-S6F {prefix}resolved {suffix} coverage",
                    float(cell[f"{prefix}coverage_resolved_{suffix}"]),
                    covered / resolved_label_rows,
                )
                for disposition in ("covered", "missed"):
                    expected_unresolved = sum(
                        int(row[f"{prefix}unresolved_label_{disposition}_if_assigned_rows"])
                        for row in label_rows
                    )
                    column = (
                        f"{prefix}unresolved_{'zero' if label == '0' else 'one'}_{disposition}_rows"
                    )
                    if int(cell[column]) != expected_unresolved:
                        _fail(
                            s6d_name,
                            paths[s6d_name],
                            f"S6D-to-S6F aggregate {column!r} fails at {cell_key!r}.",
                        )

        metric_identities = {
            "coverage_resolved_gap_y0_minus_y1": float(cell["coverage_resolved_y0"])
            - float(cell["coverage_resolved_y1"]),
            "baseline_coverage_resolved_gap_y0_minus_y1": float(
                cell["baseline_coverage_resolved_y0"]
            )
            - float(cell["baseline_coverage_resolved_y1"]),
            "resolved_coverage_delta_label_mondrian_minus_baseline": float(
                cell["coverage_resolved"]
            )
            - float(cell["baseline_coverage_resolved"]),
            "resolved_y0_coverage_delta_label_mondrian_minus_baseline": float(
                cell["coverage_resolved_y0"]
            )
            - float(cell["baseline_coverage_resolved_y0"]),
            "resolved_y1_coverage_delta_label_mondrian_minus_baseline": float(
                cell["coverage_resolved_y1"]
            )
            - float(cell["baseline_coverage_resolved_y1"]),
            "average_set_size_delta_label_mondrian_minus_baseline": float(cell["average_set_size"])
            - float(cell["baseline_average_set_size"]),
        }
        for column, expected_metric in metric_identities.items():
            _require_close(
                s6d_name,
                paths[s6d_name],
                row_number,
                f"S6D identity {column}",
                float(cell[column]),
                expected_metric,
            )

    s6c_thresholds = {
        (row["learner"], row["window_id"], row["conformal_group"]): float(
            row["fit_residual_quantile"]
        )
        for row in rows_by_name[s6c_name]
    }
    for row_number, row in enumerate(rows_by_name[s6j_name], start=2):
        from_key = (row["learner"], row["window_from"], row["conformal_group"])
        to_key = (row["learner"], row["window_to"], row["conformal_group"])
        _require_close(
            s6j_name,
            paths[s6j_name],
            row_number,
            "S6C-to-S6J source threshold",
            float(row["threshold_from"]),
            s6c_thresholds[from_key],
        )
        _require_close(
            s6j_name,
            paths[s6j_name],
            row_number,
            "S6C-to-S6J target threshold",
            float(row["threshold_to"]),
            s6c_thresholds[to_key],
        )

    aggregate_columns = (
        "candidate_rows",
        "resolved_rows",
        "unresolved_rows",
        "potential_y0_crossed_rows",
        "potential_y1_crossed_rows",
        "resolved_y0_crossed_rows",
        "resolved_y1_crossed_rows",
        "resolved_y0_delta_numerator",
        "resolved_y1_delta_numerator",
        "resolved_delta_numerator",
        "resolved_covered_from_numerator",
        "resolved_covered_to_numerator",
        "delta_lower_numerator",
        "delta_upper_numerator",
        "delta_width_numerator",
    )
    strata_by_pair: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows_by_name[s6j_name]:
        strata_by_pair[(row["learner"], row["pair_index"])].append(row)
    for row in rows_by_name[s6k_name]:
        pair_key = (row["learner"], row["pair_index"])
        strata = strata_by_pair[pair_key]
        for column in aggregate_columns:
            if int(row[column]) != sum(int(stratum[column]) for stratum in strata):
                _fail(
                    s6k_name,
                    paths[s6k_name],
                    f"S6J-to-S6K aggregate {column!r} fails at {pair_key!r}.",
                )
        direction_counts = Counter(int(stratum["threshold_sign"]) for stratum in strata)
        expected_directions = {
            "threshold_decrease_strata": direction_counts[-1],
            "threshold_equal_strata": direction_counts[0],
            "threshold_increase_strata": direction_counts[1],
        }
        if any(int(row[column]) != expected for column, expected in expected_directions.items()):
            _fail(
                s6k_name,
                paths[s6k_name],
                f"S6J-to-S6K threshold directions fail at {pair_key!r}.",
            )

    s6l_name = "Table_S6L_residual_transport_summary.csv"
    s6m_name = "Table_S6M_residual_transport_pooled.csv"
    residual_by_learner: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows_by_name[s6m_name]:
        residual_by_learner[row["learner"]][row["sharp_directional_discrepancy_comparison"]] += 1
    residual_columns = (
        "larger_target_residual_discrepancy_dominates",
        "smaller_target_residual_discrepancy_dominates",
        "directional_discrepancies_not_robustly_ordered",
    )
    for row in rows_by_name[s6l_name]:
        learner = row["learner"]
        counts = residual_by_learner[learner]
        if int(row["pooled_cells"]) != sum(counts.values()):
            _fail(s6l_name, paths[s6l_name], f"pooled cell count fails for {learner!r}.")
        for column in residual_columns:
            if int(row[column]) != counts[column]:
                _fail(
                    s6l_name,
                    paths[s6l_name],
                    f"S6L-to-S6M direction census fails for {learner!r} and {column!r}.",
                )
    aggregate_residual = Counter(
        row["sharp_directional_discrepancy_comparison"] for row in rows_by_name[s6m_name]
    )
    if aggregate_residual != Counter(
        {
            "larger_target_residual_discrepancy_dominates": 158,
            "smaller_target_residual_discrepancy_dominates": 8,
            "directional_discrepancies_not_robustly_ordered": 34,
        }
    ):
        _fail(s6m_name, paths[s6m_name], "the exact pooled residual census changed.")

    s6n_name = "Table_S6N_marginal_score_outcome_gap.csv"
    for row_number, row in enumerate(rows_by_name[s6n_name], start=2):
        mean_score = float(row["mean_score"])
        outcome_lower = float(row["outcome_mean_lower"])
        outcome_upper = float(row["outcome_mean_upper"])
        gap_lower = float(row["marginal_mean_score_outcome_gap_lower"])
        gap_upper = float(row["marginal_mean_score_outcome_gap_upper"])
        _require_close(
            s6n_name,
            paths[s6n_name],
            row_number,
            "marginal gap lower identity",
            gap_lower,
            mean_score - outcome_upper,
        )
        _require_close(
            s6n_name,
            paths[s6n_name],
            row_number,
            "marginal gap upper identity",
            gap_upper,
            mean_score - outcome_lower,
        )
        if gap_upper >= 0.0:
            _fail(s6n_name, paths[s6n_name], "a marginal gap upper endpoint is nonnegative.")

    s9g_name = "Table_S9G_decision_catalog_metric_separation.csv"
    s9h_name = "Table_S9H_decision_catalog_target_blocks.csv"
    blocks_by_metric: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows_by_name[s9h_name]:
        blocks_by_metric[row["metric"]].append(row)
    for row_number, row in enumerate(rows_by_name[s9g_name], start=2):
        metric = row["metric"]
        blocks = blocks_by_metric[metric]
        minimum_target = min(float(block["score_lower"]) for block in blocks)
        development_upper = max(float(block["development_max_upper"]) for block in blocks)
        if len(blocks) != int(row["target_blocks"]):
            _fail(s9g_name, paths[s9g_name], f"target block census fails for {metric!r}.")
        for column, expected_value in (
            ("minimum_target_lower", minimum_target),
            ("development_maximum_upper", development_upper),
            ("minimum_separation_margin", minimum_target - development_upper),
        ):
            _require_close(
                s9g_name,
                paths[s9g_name],
                row_number,
                f"S9G-to-S9H {column}",
                float(row[column]),
                expected_value,
            )
        if minimum_target <= development_upper:
            _fail(s9g_name, paths[s9g_name], f"separation fails for {metric!r}.")

    s9i_name = "Table_S9I_funded_selection_track_estimands.csv"
    s9i_rows = rows_by_name[s9i_name]
    if sum(float(row["count_selected_coverage_upper"]) < 0.90 for row in s9i_rows) != 80:
        _fail(s9i_name, paths[s9i_name], "count coverage upper endpoint census changed.")
    if sum(float(row["count_selected_coverage_lower"]) < 0.90 for row in s9i_rows) != 96:
        _fail(s9i_name, paths[s9i_name], "count coverage lower endpoint census changed.")
    for row_number, row in enumerate(s9i_rows, start=2):
        for prefix in (
            "count_selected",
            "invested_dollar_selected",
            "fixed_capital_decision",
        ):
            _require_close(
                s9i_name,
                paths[s9i_name],
                row_number,
                f"{prefix} coverage lower complement",
                float(row[f"{prefix}_coverage_lower"]),
                1.0 - float(row[f"{prefix}_fcp_upper"]),
            )
            _require_close(
                s9i_name,
                paths[s9i_name],
                row_number,
                f"{prefix} coverage upper complement",
                float(row[f"{prefix}_coverage_upper"]),
                1.0 - float(row[f"{prefix}_fcp_lower"]),
            )
        for contrast in (
            "count_selected_minus_invested_dollar_selected",
            "count_selected_minus_fixed_capital_decision",
        ):
            if float(row[f"{contrast}_coverage_lower"]) <= 0.0:
                _fail(s9i_name, paths[s9i_name], f"{contrast} lower endpoint is not positive.")
            _require_close(
                s9i_name,
                paths[s9i_name],
                row_number,
                f"{contrast} lower sign reversal",
                float(row[f"{contrast}_coverage_lower"]),
                -float(row[f"{contrast}_fcp_upper"]),
            )
            _require_close(
                s9i_name,
                paths[s9i_name],
                row_number,
                f"{contrast} upper sign reversal",
                float(row[f"{contrast}_coverage_upper"]),
                -float(row[f"{contrast}_fcp_lower"]),
            )

    s9j_name = "Table_S9J_funded_selection_gamma_contrasts.csv"
    s9j_rows = rows_by_name[s9j_name]
    expected_gamma_directions = {
        "gamma1_minus_gamma0_count_selected_fcp_direction": Counter({"higher": 40, "lower": 8}),
        "gamma1_minus_gamma0_invested_dollar_selected_fcp_direction": Counter(
            {"higher": 40, "crossing": 8}
        ),
        "gamma1_minus_gamma0_fixed_capital_decision_fcp_direction": Counter(
            {"higher": 40, "crossing": 8}
        ),
    }
    for column, expected_counts in expected_gamma_directions.items():
        if Counter(row[column] for row in s9j_rows) != expected_counts:
            _fail(s9j_name, paths[s9j_name], f"gamma direction census changed for {column!r}.")
    for row_number, row in enumerate(s9j_rows, start=2):
        for prefix in (
            "gamma1_minus_gamma0_count_selected",
            "gamma1_minus_gamma0_invested_dollar_selected",
            "gamma1_minus_gamma0_fixed_capital_decision",
        ):
            _require_close(
                s9j_name,
                paths[s9j_name],
                row_number,
                f"{prefix} coverage lower sign reversal",
                float(row[f"{prefix}_coverage_lower"]),
                -float(row[f"{prefix}_fcp_upper"]),
            )
            _require_close(
                s9j_name,
                paths[s9j_name],
                row_number,
                f"{prefix} coverage upper sign reversal",
                float(row[f"{prefix}_coverage_upper"]),
                -float(row[f"{prefix}_fcp_lower"]),
            )

    s9k_name = "Table_S9K_set_preserving_embedding_allocation_summary.csv"
    s9k_rows = rows_by_name[s9k_name]
    expected_s9k = {
        "all_rulers": (11_520, 9_659, 0.684049776890922),
        "objective_matched": (5_760, 3_899, 0.5758632511294073),
        "normalized_score": (5_760, 5_760, 0.684049776890922),
    }
    observed_s9k_order = [row["ruler"] for row in s9k_rows]
    if observed_s9k_order != list(EMBEDDING_RULERS):
        _fail(s9k_name, paths[s9k_name], "the locked all-rulers-first row order changed.")
    for row_number, row in enumerate(s9k_rows, start=2):
        ruler = row["ruler"]
        contrasts, changes, maximum_distance = expected_s9k[ruler]
        if int(row["noncontrol_theta_contrasts"]) != contrasts:
            _fail(s9k_name, paths[s9k_name], f"contrast census changed for {ruler!r}.")
        if int(row["allocation_changes_gt_1e10"]) != changes:
            _fail(s9k_name, paths[s9k_name], f"allocation-change census changed for {ruler!r}.")
        _require_close(
            s9k_name,
            paths[s9k_name],
            row_number,
            "maximum normalized exposure distance",
            float(row["maximum_normalized_exposure_distance"]),
            maximum_distance,
        )
        _require_close(
            s9k_name,
            paths[s9k_name],
            row_number,
            "common maximum upper contraction",
            float(row["maximum_upper_contraction"]),
            0.8920116585417792,
        )
    s9k_by_ruler = {row["ruler"]: row for row in s9k_rows}
    for column in ("noncontrol_theta_contrasts", "allocation_changes_gt_1e10"):
        if int(s9k_by_ruler["all_rulers"][column]) != sum(
            int(s9k_by_ruler[ruler][column]) for ruler in RULERS
        ):
            _fail(s9k_name, paths[s9k_name], f"all-rulers {column} does not add.")

    s9l_name = "Table_S9L_set_preserving_embedding_direction_census.csv"
    s9l_rows = rows_by_name[s9l_name]
    expected_s9l = {
        ("theta_minus_theta_0_within_gamma", "standardized_payoff"): (
            768,
            128,
            338,
            230,
            72,
        ),
        ("theta_minus_theta_0_within_gamma", "funded_default"): (
            768,
            350,
            157,
            173,
            88,
        ),
        ("theta_minus_theta_0_within_gamma", "funded_binary_miscoverage"): (
            768,
            340,
            259,
            81,
            88,
        ),
        ("gamma_1_minus_gamma_0_within_theta", "standardized_payoff"): (
            240,
            149,
            0,
            74,
            17,
        ),
        ("gamma_1_minus_gamma_0_within_theta", "funded_default"): (
            240,
            0,
            153,
            70,
            17,
        ),
        ("gamma_1_minus_gamma_0_within_theta", "funded_binary_miscoverage"): (
            240,
            0,
            191,
            32,
            17,
        ),
    }
    expected_s9l_order = [
        (contrast_family, metric)
        for contrast_family in EMBEDDING_CONTRAST_FAMILIES
        for metric in EMBEDDING_METRICS
    ]
    observed_s9l_order = [(row["contrast_family"], row["metric"]) for row in s9l_rows]
    if observed_s9l_order != expected_s9l_order:
        _fail(s9l_name, paths[s9l_name], "the locked contrast-family/metric row order changed.")
    census_columns = (
        "cells",
        "negative",
        "positive",
        "not_directionally_separated_at_tolerance",
        "within_tolerance",
    )
    for row in s9l_rows:
        key = (row["contrast_family"], row["metric"])
        observed = tuple(int(row[column]) for column in census_columns)
        if observed != expected_s9l[key]:
            _fail(s9l_name, paths[s9l_name], f"the exact direction census changed for {key!r}.")


def _zip_payload(sources: dict[str, Path] | None = None) -> bytes:
    selected = SOURCES if sources is None else sources
    if set(selected) != set(SOURCE_FILENAMES):
        raise ValueError("Machine-readable supplement sources left the exact table census.")
    missing = [str(path) for path in selected.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing publication tables: {missing}")
    normalized_paths = [str(path.resolve()).casefold() for path in selected.values()]
    if len(normalized_paths) != len(set(normalized_paths)):
        raise ValueError("Machine-readable supplement source paths must be distinct.")
    validated = {name: _read_validated_reviewer_csv(name, path) for name, path in selected.items()}
    csv_payloads = {name: item[0] for name, item in validated.items()}
    _validate_cross_table_contract(
        selected,
        {name: item[1] for name, item in validated.items()},
    )
    entries = {"README.txt": README.encode("utf-8"), **csv_payloads}
    for name, payload in entries.items():
        lowered = payload.lower()
        if any(token in lowered for token in FORBIDDEN_FINGERPRINTS):
            raise RuntimeError(f"Reviewer fingerprint found in {name}.")
        for label, pattern in FORBIDDEN_FINGERPRINT_PATTERNS:
            if pattern.search(payload):
                raise RuntimeError(f"Reviewer {label} found in {name}.")
    buffer = io.BytesIO()
    # Store entries rather than deflating them: compressed byte streams can vary
    # across zlib releases even when the logical CSV payloads are identical.
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(entries):
            payload = entries[name]
            info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload, compress_type=zipfile.ZIP_STORED)
    return buffer.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--table-dir", type=Path, default=TABLE_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    table_dir = args.table_dir.resolve()
    output = args.output.resolve()
    sources = {name: table_dir / filename for name, filename in SOURCE_FILENAMES.items()}
    payload = _zip_payload(sources)
    if args.check:
        if not output.is_file() or output.read_bytes() != payload:
            print(f"stale machine-readable supplement: {output}")
            return 1
        print(f"machine-readable supplement is current: {output}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(output, payload)
    print(f"machine-readable supplement rendered: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
