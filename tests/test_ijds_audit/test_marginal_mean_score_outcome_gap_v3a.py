from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.ijds_audit.marginal_mean_score_outcome_gap_v3a import (
    ENDPOINT_REASONS,
    RESOLUTION_CHARGED_OFF,
    RESOLUTION_FULLY_PAID,
    RESOLUTION_NONTERMINAL,
    RESOLUTION_TERMINAL_AFTER,
    RESOLUTION_TERMINAL_MISSING,
    build_row_level_endpoint,
    hash_endpoint_assignments,
    hash_sorted_identifiers,
    marginal_mean_score_outcome_gap_v3a,
    scan_primary_oot_raw_archive,
)

LEARNERS = ("l1", "l2", "l3", "l4", "l5")
SCORE_COLUMNS = {learner: f"pd_{learner}" for learner in LEARNERS}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _raw_primary() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": pd.Series(["1", "2", "3", "4", "5"], dtype="string"),
            "period": pd.Series(["2016-04"] * 5, dtype="string"),
            "role": pd.Series(["primary_oot"] * 5, dtype="string"),
            "loan_status": pd.Series(
                ["Fully Paid", "Charged Off", "Default", "Charged Off", "Charged Off"],
                dtype="string",
            ),
            "last_pymnt_d": pd.Series(
                ["Sep-2020", "Mar-2020", "Sep-2020", "Apr-2020", pd.NA],
                dtype="string",
            ),
        }
    )


def _scores() -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "id": pd.Series(["1", "2", "3", "4", "5"], dtype="string"),
            "issue_d": pd.to_datetime(["2016-04-01"] * 5),
            "design_split": pd.Series(["primary_oot"] * 5, dtype="string"),
        }
    )
    values = {
        "l1": [0.1] * 5,
        "l2": [0.9] * 5,
        "l3": [0.5] * 5,
        "l4": [0.0, 0.25, 0.5, 0.75, 1.0],
        "l5": [0.2, 0.3, 0.4, 0.5, 0.6],
    }
    for learner, column in SCORE_COLUMNS.items():
        frame[column] = np.asarray(values[learner], dtype=float)
    return frame


def _endpoint_hash(endpoint: pd.DataFrame) -> str:
    digest = hashlib.sha256()
    for row in endpoint.sort_values("id", kind="mergesort").itertuples(index=False):
        y = None if pd.isna(row.snapshot_default) else int(row.snapshot_default)
        record = [
            str(row.id),
            str(row.role),
            str(row.period),
            str(row.snapshot_resolution),
            y,
        ]
        payload = json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode()
        digest.update(len(payload).to_bytes(8, "little", signed=False))
        digest.update(payload)
    return digest.hexdigest()


def test_hash_serialization_literal_vectors() -> None:
    identifiers = pd.Series(["é", "::", "a"], dtype="string")
    _require(
        hash_sorted_identifiers(identifiers, label="literal vector")
        == "81f6992fb47d559c793c87786fe34a258f8a816b741079c8301d1af281d54e0d",
        "ID length-prefix/UTF-8/sort serialization drifted",
    )
    endpoint = pd.DataFrame(
        {
            "id": pd.Series(["é", "a"], dtype="string"),
            "role": ["primary_oot", "primary_oot"],
            "period": ["2016-04", "2016-04"],
            "snapshot_resolution": [
                RESOLUTION_NONTERMINAL,
                RESOLUTION_FULLY_PAID,
            ],
            "snapshot_default": pd.Series([pd.NA, 0], dtype="Int8"),
        }
    )
    _require(
        hash_endpoint_assignments(endpoint)
        == "1e4d90031d9c00cabbb31dc16e591c3bcba0c7a2cbd1669f5778b37d091402c3",
        "endpoint JSON/nullable/length-prefix serialization drifted",
    )


def _reason_contract() -> dict[str, dict[str, int]]:
    return {
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


def _monthly_contract() -> dict[str, dict[str, int]]:
    return {"2016-04": dict.fromkeys(ENDPOINT_REASONS, 1)}


def _run_synthetic(scores: pd.DataFrame | None = None, endpoint: pd.DataFrame | None = None):
    score_frame = _scores() if scores is None else scores
    endpoint_frame = (
        build_row_level_endpoint(_raw_primary(), cutoff="2020-09-30", charged_off_lag_months=6)
        if endpoint is None
        else endpoint
    )
    return marginal_mean_score_outcome_gap_v3a(
        score_frame,
        endpoint_frame,
        learners=LEARNERS,
        score_columns=SCORE_COLUMNS,
        role="primary_oot",
        expected_issue_months=("2016-04",),
        expected_candidate_id_sha256=hash_sorted_identifiers(
            score_frame.loc[score_frame["design_split"].eq("primary_oot"), "id"],
            label="test scores",
        ),
        expected_endpoint_row_sha256=_endpoint_hash(endpoint_frame),
        expected_reason_census=_reason_contract(),
        expected_monthly_reason_candidate_rows=_monthly_contract(),
        expected_candidates=5,
        expected_resolved=2,
        expected_unresolved=3,
        expected_resolved_y0=1,
        expected_resolved_y1=1,
    )


def test_row_endpoint_keeps_exact_default_status_unresolved() -> None:
    endpoint = build_row_level_endpoint(
        _raw_primary(), cutoff="2020-09-30", charged_off_lag_months=6
    )
    indexed = endpoint.set_index("id")
    _require(pd.isna(indexed.loc["3", "snapshot_default"]), "Default must remain unresolved")
    _require(
        indexed.loc["3", "snapshot_resolution"] == RESOLUTION_NONTERMINAL,
        "Default used the wrong endpoint reason",
    )
    _require(
        indexed.loc["4", "snapshot_resolution"] == RESOLUTION_TERMINAL_AFTER,
        "post-cutoff terminal row was not censored",
    )
    _require(
        indexed.loc["5", "snapshot_resolution"] == RESOLUTION_TERMINAL_MISSING,
        "missing terminal availability date used the wrong reason",
    )


def test_v3a_bounds_join_same_rows_and_do_not_stop_on_sign() -> None:
    result = _run_synthetic()
    table = result.table.set_index("learner")
    _require(len(table) == 5, "complete learner census missing")
    _require(table.loc["l1", "marginal_mean_score_outcome_gap_upper"] < 0.0, "negative case lost")
    _require(table.loc["l2", "marginal_mean_score_outcome_gap_lower"] > 0.0, "positive case lost")
    _require(
        table.loc["l3", "marginal_mean_score_outcome_gap_lower"]
        < 0.0
        < table.loc["l3", "marginal_mean_score_outcome_gap_upper"],
        "crossing case lost",
    )
    _require(bool(table["identified_grid_points"].eq(4).all()), "identified grid size drifted")
    _require(
        bool(np.isclose(table["identified_grid_step"], 0.2, atol=0.0, rtol=0.0).all()),
        "identified grid step drifted",
    )
    _require(result.join_audit["score_only_rows"] == 0, "score-only IDs were accepted")
    _require(result.join_audit["outcome_only_rows"] == 0, "outcome-only IDs were accepted")
    _require(
        result.join_audit["all_three_id_hashes_equal_locked_hash"] is True,
        "common candidate hash was not certified",
    )
    _require(len(result.monthly_endpoint_reason_census) == 5, "zero-filled monthly grid changed")


def test_v3a_is_invariant_to_row_permutation() -> None:
    baseline = _run_synthetic()
    permuted_scores = _scores().iloc[[4, 2, 0, 3, 1]].reset_index(drop=True)
    endpoint = (
        build_row_level_endpoint(_raw_primary(), cutoff="2020-09-30", charged_off_lag_months=6)
        .iloc[[1, 4, 2, 0, 3]]
        .reset_index(drop=True)
    )
    replay = _run_synthetic(permuted_scores, endpoint)
    pd.testing.assert_frame_equal(baseline.table, replay.table, check_exact=True)
    _require(
        baseline.endpoint_row_sha256 == replay.endpoint_row_sha256,
        "endpoint assignment hash depends on row order",
    )


def test_v3a_rejects_missing_extra_or_period_mismatched_outcomes() -> None:
    endpoint = build_row_level_endpoint(
        _raw_primary(), cutoff="2020-09-30", charged_off_lag_months=6
    )
    bad_ids = endpoint.copy()
    bad_ids.loc[0, "id"] = "extra"
    with pytest.raises(RuntimeError, match="ID hashes"):
        _run_synthetic(endpoint=bad_ids)
    bad_period = endpoint.copy()
    bad_period.loc[0, "period"] = "2016-05"
    with pytest.raises(RuntimeError, match="issue months disagree"):
        _run_synthetic(endpoint=bad_period)


def test_v3a_rejects_duplicate_ids_and_nonfinite_scores() -> None:
    duplicate = _scores()
    duplicate.loc[1, "id"] = duplicate.loc[0, "id"]
    with pytest.raises(RuntimeError, match="duplicate"):
        _run_synthetic(scores=duplicate)
    nonfinite = _scores()
    nonfinite.loc[0, "pd_l1"] = np.nan
    with pytest.raises(RuntimeError, match="nonfinite"):
        _run_synthetic(scores=nonfinite)


def test_raw_scan_builds_independent_primary_and_score_lookup_censuses(
    tmp_path: Path,
) -> None:
    raw = _raw_primary().drop(columns=["period", "role"]).copy()
    raw["issue_d"] = "Apr-2016"
    raw["term"] = "36 months"
    raw = pd.concat(
        [
            raw,
            pd.DataFrame(
                {
                    "id": ["6", "7"],
                    "issue_d": ["Apr-2016", "Mar-2016"],
                    "term": ["60 months", "36 months"],
                    "loan_status": ["Fully Paid", "Fully Paid"],
                    "last_pymnt_d": ["Sep-2020", "Sep-2020"],
                }
            ),
        ],
        ignore_index=True,
    )
    path = tmp_path / "raw.csv"
    raw.to_csv(path, index=False)
    scan = scan_primary_oot_raw_archive(
        path,
        required_columns=("id", "issue_d", "term", "loan_status", "last_pymnt_d"),
        csv_chunksize=2,
        term_months=36,
        start_month="2016-04",
        end_month="2016-04",
        expected_raw_rows=7,
        expected_candidates=5,
        expected_issue_months=("2016-04",),
        expected_candidate_ids=pd.Series(["1", "2", "3", "4", "5"], dtype="string"),
    )
    _require(len(scan.frame) == 5, "status-independent raw target size changed")
    _require(scan.audit["membership_uses_loan_status"] is False, "status entered membership")
    _require(
        scan.audit["raw_score_id_lookup"]["equals_raw_primary_ids"] is True,
        "independent raw score-ID lookup was not reconciled",
    )


def test_raw_endpoint_rejects_parser_format_drift() -> None:
    raw = _raw_primary()
    raw.loc[0, "last_pymnt_d"] = "2020-09-30"
    with pytest.raises(RuntimeError, match="canonical Mon-YYYY"):
        build_row_level_endpoint(raw, cutoff="2020-09-30", charged_off_lag_months=6)


def test_v3a_rejects_endpoint_hash_or_monthly_census_drift() -> None:
    scores = _scores()
    endpoint = build_row_level_endpoint(
        _raw_primary(), cutoff="2020-09-30", charged_off_lag_months=6
    )
    common = {
        "scores": scores,
        "endpoint": endpoint,
        "learners": LEARNERS,
        "score_columns": SCORE_COLUMNS,
        "role": "primary_oot",
        "expected_issue_months": ("2016-04",),
        "expected_candidate_id_sha256": hash_sorted_identifiers(scores["id"], label="test"),
        "expected_reason_census": _reason_contract(),
        "expected_candidates": 5,
        "expected_resolved": 2,
        "expected_unresolved": 3,
        "expected_resolved_y0": 1,
        "expected_resolved_y1": 1,
    }
    with pytest.raises(RuntimeError, match="assignment hash changed"):
        marginal_mean_score_outcome_gap_v3a(
            **common,
            expected_endpoint_row_sha256="0" * 64,
            expected_monthly_reason_candidate_rows=_monthly_contract(),
        )
    bad_month = _monthly_contract()
    bad_month["2016-04"] = dict(bad_month["2016-04"])
    bad_month["2016-04"][RESOLUTION_NONTERMINAL] = 2
    with pytest.raises(RuntimeError, match="Monthly endpoint census changed"):
        marginal_mean_score_outcome_gap_v3a(
            **common,
            expected_endpoint_row_sha256=_endpoint_hash(endpoint),
            expected_monthly_reason_candidate_rows=bad_month,
        )
