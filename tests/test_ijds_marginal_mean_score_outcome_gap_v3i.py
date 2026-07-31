from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.experiments.run_ijds_marginal_mean_score_outcome_gap_v3i as runner
from scripts.experiments.run_ijds_marginal_mean_score_outcome_gap_v3i import (
    LOCKED_CONFIG_PATH,
    RUN_TAG,
    _load_config,
)
from src.ijds_audit.marginal_mean_score_outcome_gap_v3i import (
    ENDPOINT_REASONS,
    RESOLUTION_CHARGED_OFF,
    RESOLUTION_FULLY_PAID,
    RESOLUTION_NONTERMINAL,
    RESOLUTION_TERMINAL_AFTER,
    RESOLUTION_TERMINAL_MISSING,
    MarginalGapTables,
    build_marginal_gap_tables,
    build_row_level_endpoint,
    hash_endpoint_assignments,
    hash_sorted_identifiers,
    scan_primary_oot_raw_archive,
)

LEARNERS = (
    "catboost_platt",
    "numeric_logistic_platt",
    "catboost_monotonic_platt",
    "woe_scorecard_platform_platt",
    "woe_scorecard_borrower_platt",
)
SCORE_COLUMNS = {
    "catboost_platt": "pd_catboost_platt",
    "numeric_logistic_platt": "pd_numeric_logistic_platt",
    "catboost_monotonic_platt": "pd_catboost_monotonic_platt",
    "woe_scorecard_platform_platt": "pd_woe_scorecard_platform_platt",
    "woe_scorecard_borrower_platt": "pd_woe_scorecard_borrower_platt",
}


def _synthetic_archive() -> BytesIO:
    return BytesIO(
        b"id,issue_d,term,loan_status,last_pymnt_d\n"
        b"a,Apr-2016,36 months,Fully Paid,Mar-2020\n"
        b"b,Apr-2016,36 months,Charged Off,Jan-2020\n"
        b"c,Apr-2016,36 months,Current,Aug-2020\n"
        b"d,Apr-2016,36 months,Charged Off,Jun-2020\n"
        b"e,Apr-2016,36 months,Fully Paid,\n"
        b"f,Apr-2016,60 months,Fully Paid,Mar-2020\n"
        b"g,Mar-2016,36 months,Charged Off,Jan-2020\n"
    )


def _synthetic_scores() -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "id": list("abcde"),
            "issue_d": pd.to_datetime(["2016-04-01"] * 5),
            "design_split": ["primary_oot"] * 5,
        }
    )
    for offset, column in enumerate(SCORE_COLUMNS.values()):
        frame[column] = np.asarray([0.1, 0.2, 0.3, 0.4, 0.5]) + offset * 0.01
    return frame


def test_v3h_hash_serialization_vectors_are_preserved() -> None:
    identifiers = pd.Series(["é", "::", "a"], dtype="string")
    assert hash_sorted_identifiers(identifiers, label="literal") == (
        "81f6992fb47d559c793c87786fe34a258f8a816b741079c8301d1af281d54e0d"
    )
    endpoint = pd.DataFrame(
        {
            "id": ["é", "a"],
            "role": ["primary_oot", "primary_oot"],
            "period": ["2016-04", "2016-04"],
            "snapshot_resolution": [
                "nonterminal_or_unresolved_status",
                "fully_paid_by_reconstructed_cutoff",
            ],
            "snapshot_default": pd.Series([pd.NA, 0], dtype="Int8"),
        }
    )
    assert hash_endpoint_assignments(endpoint) == (
        "1e4d90031d9c00cabbb31dc16e591c3bcba0c7a2cbd1669f5778b37d091402c3"
    )


def test_direct_calculation_reproduces_endpoint_and_sharp_formulas() -> None:
    scores = _synthetic_scores()
    scan = scan_primary_oot_raw_archive(
        _synthetic_archive(),
        required_columns=("id", "issue_d", "term", "loan_status", "last_pymnt_d"),
        csv_chunksize=2,
        term_months=36,
        start_month="2016-04",
        end_month="2016-04",
        expected_raw_rows=7,
        expected_candidates=5,
        expected_issue_months=("2016-04",),
        expected_candidate_ids=scores["id"],
    )
    assert scan.audit["selection_columns"] == ["term", "issue_d"]
    assert scan.audit["membership_uses_loan_status"] is False
    assert scan.audit["raw_score_id_lookup"]["equals_raw_primary_ids"] is True

    endpoint = build_row_level_endpoint(
        scan.frame,
        cutoff="2020-09-30",
        charged_off_lag_months=6,
    )
    reason_by_id = endpoint.set_index("id")["snapshot_resolution"].to_dict()
    assert reason_by_id == {
        "a": RESOLUTION_FULLY_PAID,
        "b": RESOLUTION_CHARGED_OFF,
        "c": RESOLUTION_NONTERMINAL,
        "d": RESOLUTION_TERMINAL_AFTER,
        "e": RESOLUTION_TERMINAL_MISSING,
    }
    expected_reasons = {
        RESOLUTION_CHARGED_OFF: {
            "candidate_rows": 1,
            "resolved_rows": 1,
            "unresolved_rows": 0,
        },
        RESOLUTION_FULLY_PAID: {
            "candidate_rows": 1,
            "resolved_rows": 1,
            "unresolved_rows": 0,
        },
        RESOLUTION_NONTERMINAL: {
            "candidate_rows": 1,
            "resolved_rows": 0,
            "unresolved_rows": 1,
        },
        RESOLUTION_TERMINAL_AFTER: {
            "candidate_rows": 1,
            "resolved_rows": 0,
            "unresolved_rows": 1,
        },
        RESOLUTION_TERMINAL_MISSING: {
            "candidate_rows": 1,
            "resolved_rows": 0,
            "unresolved_rows": 1,
        },
    }
    expected_month = {"2016-04": dict.fromkeys(ENDPOINT_REASONS, 1)}
    candidate_hash = hash_sorted_identifiers(scores["id"], label="synthetic scores")
    endpoint_hash = hash_endpoint_assignments(endpoint)
    tables = build_marginal_gap_tables(
        scores,
        endpoint,
        learners=LEARNERS,
        score_columns=SCORE_COLUMNS,
        expected_issue_months=("2016-04",),
        expected_candidate_id_sha256=candidate_hash,
        expected_endpoint_row_sha256=endpoint_hash,
        expected_reason_census=expected_reasons,
        expected_monthly_reason_candidate_rows=expected_month,
        expected_candidates=5,
        expected_resolved=2,
        expected_unresolved=3,
        expected_resolved_y0=1,
        expected_resolved_y1=1,
    )
    assert tables.table["learner"].tolist() == list(LEARNERS)
    assert np.allclose(tables.table["outcome_mean_lower"], 0.2)
    assert np.allclose(tables.table["outcome_mean_upper"], 0.8)
    assert np.allclose(tables.table["identification_width"], 0.6)
    assert tables.table["identified_grid_points"].eq(4).all()
    assert bool(tables.table["joint_endpoint_attainment"].all())
    assert tables.table["lower_endpoint_completion"].eq("all_unresolved_outcomes_one").all()
    assert tables.table["upper_endpoint_completion"].eq("all_unresolved_outcomes_zero").all()
    assert np.allclose(
        tables.table["marginal_mean_score_outcome_gap_lower"],
        tables.table["mean_score"] - 0.8,
    )
    assert np.allclose(
        tables.table["marginal_mean_score_outcome_gap_upper"],
        tables.table["mean_score"] - 0.2,
    )
    assert len(tables.endpoint_reason_census) == 5
    assert len(tables.monthly_endpoint_reason_census) == 5
    assert tables.join_audit["one_to_one_outer_join"] is True


def test_score_schema_fails_closed_on_an_added_column() -> None:
    scores = _synthetic_scores().assign(snapshot_default=0)
    endpoint_scan = scan_primary_oot_raw_archive(
        _synthetic_archive(),
        required_columns=("id", "issue_d", "term", "loan_status", "last_pymnt_d"),
        csv_chunksize=10,
        term_months=36,
        start_month="2016-04",
        end_month="2016-04",
        expected_raw_rows=7,
        expected_candidates=5,
        expected_issue_months=("2016-04",),
    )
    endpoint = build_row_level_endpoint(
        endpoint_scan.frame,
        cutoff="2020-09-30",
        charged_off_lag_months=6,
    )
    with pytest.raises(RuntimeError, match="schema changed"):
        build_marginal_gap_tables(
            scores,
            endpoint,
            learners=LEARNERS,
            score_columns=SCORE_COLUMNS,
            expected_issue_months=("2016-04",),
            expected_candidate_id_sha256=hash_sorted_identifiers(scores["id"], label="scores"),
            expected_endpoint_row_sha256=hash_endpoint_assignments(endpoint),
            expected_reason_census={},
            expected_monthly_reason_candidate_rows={},
            expected_candidates=5,
            expected_resolved=2,
            expected_unresolved=3,
            expected_resolved_y0=1,
            expected_resolved_y1=1,
        )


@pytest.mark.parametrize("invalid", ["not-a-label", np.inf, -np.inf, 0.5])
def test_nonmissing_endpoint_labels_must_be_finite_binary(invalid: object) -> None:
    scores = _synthetic_scores()
    scan = scan_primary_oot_raw_archive(
        _synthetic_archive(),
        required_columns=("id", "issue_d", "term", "loan_status", "last_pymnt_d"),
        csv_chunksize=10,
        term_months=36,
        start_month="2016-04",
        end_month="2016-04",
        expected_raw_rows=7,
        expected_candidates=5,
        expected_issue_months=("2016-04",),
    )
    endpoint = build_row_level_endpoint(
        scan.frame,
        cutoff="2020-09-30",
        charged_off_lag_months=6,
    )
    endpoint["snapshot_default"] = endpoint["snapshot_default"].astype(object)
    endpoint.loc[0, "snapshot_default"] = invalid
    with pytest.raises(RuntimeError, match="finite and binary"):
        build_marginal_gap_tables(
            scores,
            endpoint,
            learners=LEARNERS,
            score_columns=SCORE_COLUMNS,
            expected_issue_months=("2016-04",),
            expected_candidate_id_sha256=hash_sorted_identifiers(scores["id"], label="scores"),
            expected_endpoint_row_sha256="0" * 64,
            expected_reason_census={},
            expected_monthly_reason_candidate_rows={},
            expected_candidates=5,
            expected_resolved=2,
            expected_unresolved=3,
            expected_resolved_y0=1,
            expected_resolved_y1=1,
        )


def test_endpoint_label_must_agree_with_its_resolution_reason() -> None:
    scores = _synthetic_scores()
    scan = scan_primary_oot_raw_archive(
        _synthetic_archive(),
        required_columns=("id", "issue_d", "term", "loan_status", "last_pymnt_d"),
        csv_chunksize=10,
        term_months=36,
        start_month="2016-04",
        end_month="2016-04",
        expected_raw_rows=7,
        expected_candidates=5,
        expected_issue_months=("2016-04",),
    )
    endpoint = build_row_level_endpoint(
        scan.frame,
        cutoff="2020-09-30",
        charged_off_lag_months=6,
    )
    endpoint["snapshot_default"] = endpoint["snapshot_default"].astype(object)
    endpoint.loc[endpoint["id"].eq("c"), "snapshot_default"] = 0
    with pytest.raises(RuntimeError, match="disagrees with its endpoint reason"):
        build_marginal_gap_tables(
            scores,
            endpoint,
            learners=LEARNERS,
            score_columns=SCORE_COLUMNS,
            expected_issue_months=("2016-04",),
            expected_candidate_id_sha256=hash_sorted_identifiers(scores["id"], label="scores"),
            expected_endpoint_row_sha256="0" * 64,
            expected_reason_census={},
            expected_monthly_reason_candidate_rows={},
            expected_candidates=5,
            expected_resolved=2,
            expected_unresolved=3,
            expected_resolved_y0=1,
            expected_resolved_y1=1,
        )


def test_locked_config_is_strict_and_post_inspection() -> None:
    root = Path(__file__).resolve().parents[1]
    config = _load_config(root / LOCKED_CONFIG_PATH)
    assert config["run_tag"] == RUN_TAG
    assert config["interpretation"]["post_inspection"] is True
    assert config["interpretation"]["preregistered"] is False
    assert config["interpretation"]["no_dvc_requirement"] is True
    transport = runner._validate_artifact_transport(config)
    assert transport["artifact_tag"] == runner.ARTIFACT_TAG
    assert transport["artifact_commit_relationship"] == "single_direct_child_of_protocol_commit"
    assert len(transport["exact_tracked_paths"]) == 5
    assert transport["pending_at_runner_exit"] is True

    drifted = deepcopy(config)
    drifted["artifact_transport"]["exact_tracked_paths"].append("undeclared-sixth-path")
    with pytest.raises(RuntimeError, match="artifact-transport identity changed"):
        runner._validate_artifact_transport(drifted)


def test_run_rejects_the_execution_checkout_as_the_protected_root() -> None:
    root = Path(__file__).resolve().parents[1]
    with pytest.raises(RuntimeError, match="to differ from the run clone"):
        runner.run(
            config_path=root / LOCKED_CONFIG_PATH,
            protected_read_root=root,
            repo_root=root,
        )


def test_sanitized_environment_omits_machine_local_paths() -> None:
    environment = runner._sanitized_environment()
    assert environment["absolute_executable_path_serialized"] is False
    assert "executable" not in environment
    assert str(runner.ROOT.resolve()) not in str(environment)


def test_source_snapshots_must_equal_the_locked_yaml_descriptors() -> None:
    config = _load_config(Path(__file__).resolve().parents[1] / LOCKED_CONFIG_PATH)
    snapshot = {key: dict(config["source"][key]) for key in runner.SOURCE_KEYS}
    runner._require_exact_source_snapshot(snapshot, config, stage="initial")

    drifted = deepcopy(snapshot)
    drifted["scores"]["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="initial protected-source snapshot"):
        runner._require_exact_source_snapshot(drifted, config, stage="initial")


def test_v3h_reconciliation_fails_on_any_disclosed_row_drift() -> None:
    config = _load_config(Path(__file__).resolve().parents[1] / LOCKED_CONFIG_PATH)
    prior = config["prior_inspection"]
    rows = []
    for learner in LEARNERS:
        expected = prior["learner_rows"][learner]
        rows.append(
            {
                "learner": learner,
                "score_sum": expected["score_sum"],
                "mean_score": expected["mean_score"],
                "marginal_mean_score_outcome_gap_lower": expected["gap_lower"],
                "marginal_mean_score_outcome_gap_upper": expected["gap_upper"],
                "outcome_mean_lower": prior["outcome_mean_lower"],
                "outcome_mean_upper": prior["outcome_mean_upper"],
                "identification_width": prior["identification_width"],
            }
        )
    tables = MarginalGapTables(
        table=pd.DataFrame(rows),
        endpoint_reason_census=pd.DataFrame(),
        monthly_endpoint_reason_census=pd.DataFrame(),
        join_audit={},
        endpoint_row_sha256="0" * 64,
    )
    assert runner._reconcile_v3h(tables, config)["maximum_absolute_difference"] == 0.0
    tables.table.loc[0, "marginal_mean_score_outcome_gap_upper"] += 1.0e-6
    with pytest.raises(RuntimeError, match="did not reconcile V3H"):
        runner._reconcile_v3h(tables, config)
    assert config["stop_rules"]["stop_on_result_sign_or_learner_order"] is False
