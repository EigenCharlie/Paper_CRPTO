from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from src.ijds_audit.rolling_origin_equal_followup import (
    CHARGED_OFF_LAG_MONTHS,
    COMPLETE_ENDPOINT_REASONS,
    OriginSpec,
    origin_specs,
    select_origin_scores,
)
from src.ijds_audit.rolling_origin_individual_age_followup import (
    ENDPOINT_RULE,
    EXPECTED_CUTOFFS_BY_PERIOD,
    INDIVIDUAL_FOLLOWUP_MONTHS,
    PROTOCOL_TAG,
    RUN_TAG,
    build_individual_age_census_tables,
    load_individual_age_followup_config,
    loan_specific_cutoff_frame,
    reconstruct_individual_age_outcomes,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs"
    / "experiments"
    / "ijds_rolling_origin_individual_age_followup_2026-07-21_v1.yaml"
)
PROTOCOL = (
    ROOT
    / "docs"
    / "research"
    / "ijds_rolling_origin_individual_age_followup_protocol_2026-07-21.md"
)


def _config_and_origins() -> tuple[dict[str, Any], tuple[OriginSpec, ...]]:
    config, parent, _ = load_individual_age_followup_config(CONFIG, repo_root=ROOT)
    return config, origin_specs(parent)


def test_config_locks_complete_descriptive_individual_age_family() -> None:
    config, origins = _config_and_origins()
    assert config["run_tag"] == RUN_TAG
    assert config["protocol_tag"] == PROTOCOL_TAG
    evaluation = config["evaluation"]
    assert evaluation["individual_followup_months_after_issue_month_end"] == 39
    assert evaluation["issue_date_resolution"] == "calendar_month"
    assert evaluation["expected_cutoffs_by_issue_period"] == EXPECTED_CUTOFFS_BY_PERIOD
    assert evaluation["expected_coverage_cells"] == 16
    assert evaluation["complete_descriptive_family"] is True
    assert evaluation["error_controlled"] is False
    assert evaluation["hypothesis_tests"] is False
    assert evaluation["multiplicity_adjustment"] is False
    assert evaluation["no_model_selection"] is True
    assert evaluation["no_origin_selection"] is True
    assert evaluation["no_month_selection"] is True
    assert evaluation["no_window_selection"] is True
    assert evaluation["no_pooling"] is True
    assert evaluation["no_portfolio_evaluation"] is True
    assert tuple(origin.origin_id for origin in origins) == ("primary_2016", "rolling_2017")
    assert tuple(origin.expected_candidate_rows for origin in origins) == (74_537, 77_105)
    assert all(len(origin.window_ids) == 8 for origin in origins)


def test_parent_equal_followup_config_is_hash_locked() -> None:
    _, _, descriptor = load_individual_age_followup_config(CONFIG, repo_root=ROOT)
    assert descriptor == {
        "path": "configs/experiments/ijds_rolling_origin_equal_followup_2026-07-21_v1.yaml",
        "bytes": 5502,
        "sha256": "5a3d8369a371b346b2268377a195028e84ed8efca74a9e55e468b4df0ed0828a",
    }


def test_protocol_states_month_resolution_complete_reporting_and_no_error_control() -> None:
    text = PROTOCOL.read_text(encoding="utf-8")
    for token in (
        "41, 40, and 39",
        "C_i = month_end(I_i + 39 calendar months)",
        "2019-07-31",
        "2019-08-31",
        "2019-09-30",
        "2020-07-31",
        "2020-08-31",
        "2020-09-30",
        "calendar-month resolution",
        "complete descriptive sensitivity",
        "not an error-controlled",
        "hypothesis test, p-value calculation",
        "coverage_lower = 1 - mean(miss_high)",
        "coverage_upper = 1 - mean(miss_low)",
        "explicit zero-count rows",
        "portfolio allocation",
    ):
        assert token in text


def test_loan_specific_cutoffs_match_all_six_predeclared_months() -> None:
    issue_dates = pd.Series(
        pd.to_datetime(
            [
                "2016-04-01",
                "2016-05-15",
                "2016-06-30",
                "2017-04-01",
                "2017-05-01",
                "2017-06-01",
            ]
        )
    )
    cutoffs = loan_specific_cutoff_frame(issue_dates)
    observed = {
        str(row.period): str(pd.Timestamp(row.individual_evaluation_cutoff).date())
        for row in cutoffs.itertuples(index=False)
    }
    assert observed == EXPECTED_CUTOFFS_BY_PERIOD
    assert cutoffs["individual_followup_months"].eq(39).all()
    assert cutoffs["issue_month_end"].dt.is_month_end.all()
    assert cutoffs["individual_evaluation_cutoff"].dt.is_month_end.all()


def test_loan_specific_cutoff_rejects_changed_horizon_and_unsupported_month() -> None:
    with pytest.raises(RuntimeError, match="Individual follow-up horizon changed"):
        loan_specific_cutoff_frame(
            pd.Series(pd.to_datetime(["2017-06-01"])),
            followup_months=INDIVIDUAL_FOLLOWUP_MONTHS - 1,
        )
    with pytest.raises(RuntimeError, match="exceeds the declared endpoint support"):
        loan_specific_cutoff_frame(pd.Series(pd.to_datetime(["2017-07-01"])))


def test_score_selection_remains_outcome_free_before_endpoint_reconstruction() -> None:
    _, origins = _config_and_origins()
    spec = replace(origins[0], expected_candidate_rows=3)
    clean = pd.DataFrame(
        {
            "id": ["a", "b", "c"],
            "issue_d": pd.to_datetime(["2016-04-01", "2016-05-01", "2016-06-01"]),
            "design_split": ["primary_oot"] * 3,
            "pd_catboost_platt": [0.1, 0.2, 0.3],
        }
    )
    selected = select_origin_scores(clean, spec)
    assert selected["id"].tolist() == ["a", "b", "c"]
    with pytest.raises(RuntimeError, match="Outcome columns entered"):
        select_origin_scores(clean.assign(snapshot_default=[0, 1, pd.NA]), spec)


def test_individual_age_reconstruction_uses_each_issue_month_cutoff() -> None:
    _, origins = _config_and_origins()
    spec = replace(origins[0], expected_candidate_rows=6)
    raw = pd.DataFrame(
        {
            "id": pd.Series(
                ["fp_apr", "co_apr_late", "co_may", "missing", "current", "fp_jun"],
                dtype="string",
            ),
            "origin_id": [spec.origin_id] * 6,
            "origin_year": [spec.year] * 6,
            "period": ["2016-04", "2016-04", "2016-05", "2016-05", "2016-06", "2016-06"],
            "issue_d": pd.to_datetime(
                [
                    "2016-04-01",
                    "2016-04-01",
                    "2016-05-01",
                    "2016-05-01",
                    "2016-06-01",
                    "2016-06-01",
                ]
            ),
            "loan_status": pd.Series(
                ["Fully Paid", "Charged Off", "Charged Off", "Fully Paid", "Current", "Fully Paid"],
                dtype="string",
            ),
            "last_pymnt_d": pd.Series(
                ["Jul-2019", "Feb-2019", "Feb-2019", pd.NA, "Sep-2019", "Sep-2019"],
                dtype="string",
            ),
        }
    )
    outcomes = reconstruct_individual_age_outcomes(
        raw, spec, charged_off_lag_months=CHARGED_OFF_LAG_MONTHS
    )
    indexed = outcomes.set_index("id")
    assert indexed.loc["co_apr_late", "snapshot_resolution"] == (
        "terminal_after_reconstructed_cutoff"
    )
    assert indexed.loc["co_may", "snapshot_resolution"] == ("charged_off_by_reconstructed_cutoff")
    assert pd.isna(indexed.loc["co_apr_late", "snapshot_default"])
    assert indexed.loc["co_may", "snapshot_default"] == 1
    assert indexed["endpoint_rule"].eq(ENDPOINT_RULE).all()
    assert str(pd.Timestamp(indexed.loc["fp_apr", "individual_evaluation_cutoff"]).date()) == (
        "2019-07-31"
    )
    assert str(pd.Timestamp(indexed.loc["co_may", "individual_evaluation_cutoff"]).date()) == (
        "2019-08-31"
    )

    origin, monthly, reasons, monthly_reasons = build_individual_age_census_tables(outcomes, spec)
    assert origin.loc[0, ["candidate_rows", "resolved_rows", "unresolved_rows"]].tolist() == [
        6,
        3,
        3,
    ]
    assert monthly["candidate_rows"].tolist() == [2, 2, 2]
    assert tuple(reasons["snapshot_resolution"]) == COMPLETE_ENDPOINT_REASONS
    assert reasons["candidate_rows"].tolist() == [2, 1, 1, 1, 1]
    assert reasons["resolved_rows"].tolist() == [2, 1, 0, 0, 0]
    assert len(monthly_reasons) == 15
    assert int(monthly_reasons["candidate_rows"].sum()) == 6
    assert int((monthly_reasons["candidate_rows"] == 0).sum()) > 0
