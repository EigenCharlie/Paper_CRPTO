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
}
SOURCES = {name: TABLE_DIR / filename for name, filename in SOURCE_FILENAMES.items()}


def _columns(*parts: str) -> tuple[str, ...]:
    """Declare a readable, exact CSV header without relying on a source CSV."""

    return tuple("".join(parts).split(","))


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
BOOLEAN_DOMAIN: Final = frozenset({"True", "False"})
IDENTIFICATION_STATE_DOMAIN: Final = frozenset(
    {"robust_shortfall", "crosses_nominal", "robust_at_or_above_nominal", "undefined"}
)

TABLE_CONTRACTS: Final = {
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
}
README = """Anonymous machine-readable online supplement

These seven aggregate CSV files provide the complete cell, score-stratum,
label-category, and common-panel adjacent-threshold rows summarized by PDF
Tables S6B, S6D, S6F, S6J, and S6K. S6C and S6E are machine-readable-only
tables because their 200-row
layouts are unsuitable for a reviewer PDF.

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
        if any(token in column for token in ("_gap_", "_delta_", "_difference")):
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
    elif column in {"score_sum", "null_expected_misses"}:
        lower = 0.0
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

    if "window_id" in row:
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
    }:
        candidate_column = (
            "candidate_stratum_rows"
            if name == "Table_S6E_label_mondrian_strata.csv"
            else "candidate_rows"
        )
        if int(row[candidate_column]) != int(row["resolved_rows"]) + int(row["unresolved_rows"]):
            _fail(name, path, f"row {row_number} resolved and unresolved rows do not partition.")

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
            value = _as_float(name, path, row_number, column, raw)
            _validate_numeric_domain(name, path, row_number, column, value)
            if _is_integer_column(column):
                integer = _as_int(name, path, row_number, column, raw)
                if integer < 0 and not (
                    column == "threshold_sign"
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
    s6b_name = "Table_S6B_exchangeability_cells.csv"
    s6c_name = "Table_S6C_exchangeability_strata.csv"
    s6d_name = "Table_S6D_label_mondrian_cells.csv"
    s6e_name = "Table_S6E_label_mondrian_strata.csv"
    s6f_name = "Table_S6F_label_mondrian_categories.csv"
    s6j_name = "Table_S6J_common_panel_threshold_response_strata.csv"
    s6k_name = "Table_S6K_common_panel_threshold_response_learners.csv"
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
