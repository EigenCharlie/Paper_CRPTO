"""Exact reviewer-facing table schemas shared by evidence and ZIP builders."""

from __future__ import annotations

S6B_PUBLICATION_COLUMNS = (
    "learner",
    "learner_label",
    "window",
    "window_id",
    "taxonomy_groups",
    "stratum_tests",
    "minimum_stratum_log_p_value",
    "minimum_stratum_p_value",
    "source_cell_bonferroni_log_p_value",
    "source_cell_bonferroni_p_value",
    "strata_with_non_singleton_calibration_threshold_ties",
    "all_calibration_threshold_ties_singleton",
    "source_holm_rank",
    "locked_nominal_holm_critical_value",
    "source_holm_adjusted_log_p_value",
    "source_holm_adjusted_p_value",
    "meets_locked_nominal_holm_threshold",
)

S6B_RETIRED_COLUMNS = frozenset(
    {
        "source_holm_reject_flag",
        "source_declared_hierarchical_fwer_alpha",
    }
)

S6B_QUARANTINED_COLUMNS = frozenset(
    {
        "minimum_reference_score_stratum",
        "minimum_reference_excess_miss_rate_pp",
    }
)
