"""Tests for endpoint-availability reconstruction and summaries."""

from __future__ import annotations

import pandas as pd

from src.ijds_audit.endpoint_sensitivity import (
    endpoint_census,
    rebuild_archive_outcomes,
    summarize_coverage_sensitivity,
)


def test_rebuild_archive_outcomes_changes_only_lagged_charge_off_resolution() -> None:
    universe = pd.DataFrame(
        {
            "id": pd.Series(["good", "bad"], dtype="string"),
            "loan_status": ["Fully Paid", "Charged Off"],
            "last_pymnt_d": ["Jan-2020", "Jan-2020"],
            "design_split": ["primary_oot", "primary_oot"],
            "issue_d": pd.to_datetime(["2016-04-01", "2016-04-01"]),
        }
    )
    lag0 = rebuild_archive_outcomes(
        universe,
        evaluation_cutoff="2020-06-30",
        charged_off_lag_months=0,
    )
    lag12 = rebuild_archive_outcomes(
        universe,
        evaluation_cutoff="2020-06-30",
        charged_off_lag_months=12,
    )
    assert lag0["snapshot_default"].tolist() == [0, 1]
    assert lag12["snapshot_default"].iloc[0] == 0
    assert pd.isna(lag12["snapshot_default"].iloc[1])
    census = endpoint_census(lag12, lag_months=12)
    assert census.loc[0, "resolved_rows"] == 1
    assert census.loc[0, "unresolved_rows"] == 1


def test_coverage_summary_retains_each_lag_learner_and_role() -> None:
    coverage = pd.DataFrame(
        {
            "charged_off_lag_months": [0, 0, 12, 12],
            "learner": ["m", "m", "m", "m"],
            "role": ["primary_oot"] * 4,
            "window_id": ["w1", "w2", "w1", "w2"],
            "coverage_lower": [0.8, 0.82, 0.79, 0.80],
            "coverage_upper": [0.88, 0.89, 0.90, 0.91],
        }
    )
    summary = summarize_coverage_sensitivity(coverage)
    assert summary["windows"].tolist() == [2, 2]
    assert summary["coverage_upper_max"].tolist() == [0.89, 0.91]
