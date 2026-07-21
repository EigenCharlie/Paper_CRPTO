from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from src.ijds_audit.rolling_origin_equal_followup import (
    CHARGED_OFF_LAG_MONTHS,
    COMMON_FOLLOWUP_MONTHS,
    COMPLETE_ENDPOINT_REASONS,
    EXPECTED_COVERAGE_CELLS,
    PROTOCOL_TAG,
    RUN_TAG,
    build_endpoint_census_tables,
    load_equal_followup_config,
    load_raw_candidate_rows,
    origin_specs,
    reconstruct_origin_outcomes,
    select_origin_scores,
    validate_common_followup_cutoff,
    verify_origin_freeze,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "experiments" / "ijds_rolling_origin_equal_followup_2026-07-21_v1.yaml"
PROTOCOL = ROOT / "docs" / "research" / "ijds_rolling_origin_equal_followup_protocol_2026-07-21.md"


def _config_and_origins() -> tuple[dict[str, object], tuple[object, ...]]:
    config = load_equal_followup_config(CONFIG, repo_root=ROOT)
    return config, origin_specs(config)


def test_config_locks_two_origins_equal_followup_and_coverage_only() -> None:
    config, origins = _config_and_origins()
    assert config["run_tag"] == RUN_TAG
    assert config["protocol_tag"] == PROTOCOL_TAG
    evaluation = config["evaluation"]
    assert evaluation["common_followup_months_after_quarter_end"] == 39
    assert evaluation["charged_off_reporting_lag_months"] == 6
    assert evaluation["learner"] == "catboost_platt"
    assert evaluation["taxonomy_groups"] == 5
    assert evaluation["expected_windows_per_origin"] == 8
    assert evaluation["expected_coverage_cells"] == EXPECTED_COVERAGE_CELLS
    assert evaluation["no_model_selection"] is True
    assert evaluation["no_origin_selection"] is True
    assert evaluation["no_window_selection"] is True
    assert evaluation["no_pooling"] is True
    assert evaluation["no_portfolio_evaluation"] is True
    assert tuple(origin.origin_id for origin in origins) == ("primary_2016", "rolling_2017")
    assert tuple(origin.expected_candidate_rows for origin in origins) == (74_537, 77_105)
    assert tuple(origin.evaluation_cutoff for origin in origins) == (
        "2019-09-30",
        "2020-09-30",
    )
    assert all(len(origin.window_ids) == 8 for origin in origins)


def test_protocol_predeclares_followup_defect_sharp_bounds_and_full_reason_grid() -> None:
    text = PROTOCOL.read_text(encoding="utf-8")
    for token in (
        "51 months",
        "39 months",
        "2019-09-30",
        "2020-09-30",
        "74,537",
        "77,105",
        "coverage_lower = 1 - mean(miss_high)",
        "coverage_upper = 1 - mean(miss_low)",
        "terminal_after_reconstructed_cutoff",
        "explicit zero-count rows",
        "not a finite-sample rejection",
        "failure of the conformal theorem",
        "no portfolio",
        "preregistration",
    ):
        assert token in text


@pytest.mark.parametrize(
    ("quarter_end", "cutoff"),
    [("2016-06-30", "2019-09-30"), ("2017-06-30", "2020-09-30")],
)
def test_common_followup_cutoffs_are_exactly_thirty_nine_months(
    quarter_end: str, cutoff: str
) -> None:
    validate_common_followup_cutoff(
        issue_quarter_end=quarter_end,
        evaluation_cutoff=cutoff,
        followup_months=COMMON_FOLLOWUP_MONTHS,
    )


def test_common_followup_rejects_the_old_common_calendar_cutoff_for_2016() -> None:
    with pytest.raises(RuntimeError, match="Equal-follow-up cutoff changed"):
        validate_common_followup_cutoff(
            issue_quarter_end="2016-06-30",
            evaluation_cutoff="2020-09-30",
            followup_months=COMMON_FOLLOWUP_MONTHS,
        )


def test_common_followup_rejects_a_changed_relative_horizon() -> None:
    with pytest.raises(RuntimeError, match="Common relative follow-up changed"):
        validate_common_followup_cutoff(
            issue_quarter_end="2017-06-30",
            evaluation_cutoff="2020-09-30",
            followup_months=COMMON_FOLLOWUP_MONTHS - 1,
        )


def test_frozen_score_selector_is_status_independent_and_complete() -> None:
    _, origins = _config_and_origins()
    spec = replace(origins[0], expected_candidate_rows=3)
    scores = pd.DataFrame(
        {
            "id": ["a", "b", "c", "outside"],
            "issue_d": pd.to_datetime(["2016-04-01", "2016-05-01", "2016-06-01", "2016-07-01"]),
            "design_split": ["primary_oot"] * 4,
            "pd_catboost_platt": [0.1, 0.2, 0.3, 0.4],
        }
    )
    selected = select_origin_scores(scores, spec)
    assert selected["id"].tolist() == ["a", "b", "c"]
    assert tuple(selected["period"].astype(str)) == spec.issue_periods
    assert selected["origin_id"].eq("primary_2016").all()


def test_frozen_score_selector_rejects_outcome_bearing_input() -> None:
    _, origins = _config_and_origins()
    spec = replace(origins[0], expected_candidate_rows=3)
    scores = pd.DataFrame(
        {
            "id": ["a", "b", "c"],
            "issue_d": pd.to_datetime(["2016-04-01", "2016-05-01", "2016-06-01"]),
            "design_split": ["primary_oot"] * 3,
            "pd_catboost_platt": [0.1, 0.2, 0.3],
            "snapshot_default": [0, 1, pd.NA],
        }
    )
    with pytest.raises(RuntimeError, match="Outcome columns entered"):
        select_origin_scores(scores, spec)


def test_raw_endpoint_join_uses_only_the_frozen_candidate_identities(tmp_path: Path) -> None:
    frozen = pd.DataFrame(
        {
            "id": pd.Series(["a", "b"], dtype="string"),
            "origin_id": ["primary_2016", "rolling_2017"],
            "origin_year": [2016, 2017],
            "period": pd.Series(["2016-04", "2017-05"], dtype="string"),
        }
    )
    raw_path = tmp_path / "raw.csv"
    pd.DataFrame(
        {
            "id": ["a", "outside", "b"],
            "issue_d": ["Apr-2016", "Apr-2016", "May-2017"],
            "term": ["36 months", "36 months", "36 months"],
            "loan_status": ["Fully Paid", "Charged Off", "Current"],
            "last_pymnt_d": ["Jan-2019", "Jan-2019", "Jan-2020"],
        }
    ).to_csv(raw_path, index=False)
    joined = load_raw_candidate_rows(raw_path, frozen, csv_chunksize=2)
    assert set(joined["id"].astype(str)) == {"a", "b"}
    assert "outside" not in set(joined["id"].astype(str))
    assert joined.set_index("id")["loan_status"].astype(str).to_dict() == {
        "a": "Fully Paid",
        "b": "Current",
    }


def test_raw_endpoint_join_rejects_a_term_mismatch(tmp_path: Path) -> None:
    frozen = pd.DataFrame(
        {
            "id": pd.Series(["a"], dtype="string"),
            "origin_id": ["primary_2016"],
            "origin_year": [2016],
            "period": pd.Series(["2016-04"], dtype="string"),
        }
    )
    raw_path = tmp_path / "raw.csv"
    pd.DataFrame(
        {
            "id": ["a"],
            "issue_d": ["Apr-2016"],
            "term": ["60 months"],
            "loan_status": ["Fully Paid"],
            "last_pymnt_d": ["Jan-2019"],
        }
    ).to_csv(raw_path, index=False)
    with pytest.raises(RuntimeError, match="36-month design"):
        load_raw_candidate_rows(raw_path, frozen, csv_chunksize=1)


def test_endpoint_reconstruction_reports_all_five_reasons_including_zero_rows() -> None:
    _, origins = _config_and_origins()
    spec = replace(origins[0], expected_candidate_rows=5)
    raw = pd.DataFrame(
        {
            "id": pd.Series(["fp", "co", "late", "missing", "current"], dtype="string"),
            "origin_id": [spec.origin_id] * 5,
            "origin_year": [spec.year] * 5,
            "period": ["2016-04", "2016-04", "2016-05", "2016-06", "2016-06"],
            "issue_d": pd.to_datetime(
                ["2016-04-01", "2016-04-01", "2016-05-01", "2016-06-01", "2016-06-01"]
            ),
            "loan_status": pd.Series(
                ["Fully Paid", "Charged Off", "Charged Off", "Fully Paid", "Current"],
                dtype="string",
            ),
            "last_pymnt_d": pd.Series(
                ["Jun-2019", "Mar-2019", "Apr-2019", pd.NA, "Aug-2019"],
                dtype="string",
            ),
        }
    )
    outcomes = reconstruct_origin_outcomes(raw, spec, charged_off_lag_months=CHARGED_OFF_LAG_MONTHS)
    origin, monthly, reasons, monthly_reasons = build_endpoint_census_tables(outcomes, spec)
    assert origin.loc[0, ["candidate_rows", "resolved_rows", "unresolved_rows"]].tolist() == [
        5,
        2,
        3,
    ]
    assert monthly["candidate_rows"].tolist() == [2, 1, 2]
    assert tuple(reasons["snapshot_resolution"]) == COMPLETE_ENDPOINT_REASONS
    assert reasons["candidate_rows"].tolist() == [1, 1, 1, 1, 1]
    assert reasons["resolved_rows"].tolist() == [1, 1, 0, 0, 0]
    assert len(monthly_reasons) == 15
    assert int(monthly_reasons["candidate_rows"].sum()) == 5
    assert int((monthly_reasons["candidate_rows"] == 0).sum()) > 0


def test_source_freezes_and_required_coverage_artifacts_match_declared_hashes() -> None:
    _, origins = _config_and_origins()
    for origin in origins:
        freeze_path = ROOT / str(origin.source_freeze["path"])
        required_paths = [
            ROOT / str(descriptor["path"])
            for descriptor in origin.source_freeze["required_artifacts"].values()
        ]
        if not freeze_path.is_file() or not all(path.is_file() for path in required_paths):
            pytest.skip("DVC-fetched outcome-free rolling-origin artifacts are unavailable.")
        verified = verify_origin_freeze(origin, repo_root=ROOT)
        assert verified.freeze_descriptor["sha256"] == origin.source_freeze["sha256"]
        assert set(verified.artifact_paths) == {"scores", "recipes", "fit_audit"}
        assert "allocations" not in verified.artifact_paths
        assert verified.freeze["outcome_columns_passed_to_policy_or_comparator"] == []
