from __future__ import annotations

from itertools import product

import pandas as pd
import pytest

from src.ijds_audit.marginal_mean_score_outcome_gap import (
    ESTIMAND,
    marginal_mean_score_outcome_gap,
    normalize_endpoint_resolution_table,
)

LEARNERS = (
    "catboost_platt",
    "numeric_logistic_platt",
    "catboost_monotonic_platt",
    "woe_scorecard_platform_platt",
    "woe_scorecard_borrower_platt",
)
SCORE_COLUMNS = {learner: f"pd_{learner}" for learner in LEARNERS}
REASON_CENSUS = {
    "charged_off_by_reconstructed_cutoff": {
        "candidate_rows": 1,
        "resolved_rows": 1,
        "unresolved_rows": 0,
    },
    "fully_paid_by_reconstructed_cutoff": {
        "candidate_rows": 2,
        "resolved_rows": 2,
        "unresolved_rows": 0,
    },
    "nonterminal_or_unresolved_status": {
        "candidate_rows": 1,
        "resolved_rows": 0,
        "unresolved_rows": 1,
    },
    "terminal_after_reconstructed_cutoff": {
        "candidate_rows": 0,
        "resolved_rows": 0,
        "unresolved_rows": 0,
    },
    "terminal_availability_date_missing": {
        "candidate_rows": 0,
        "resolved_rows": 0,
        "unresolved_rows": 0,
    },
}


def _scores(*, value: float | None = None) -> pd.DataFrame:
    base = [0.05, 0.10, 0.15, 0.20] if value is None else [value] * 4
    payload: dict[str, object] = {
        "id": ["4", "2", "1", "3", "fit"],
        "issue_d": ["2016-04-01"] * 4 + ["2012-01-01"],
        "design_split": ["primary_oot"] * 4 + ["conformal_fit"],
    }
    for offset, column in enumerate(SCORE_COLUMNS.values()):
        payload[column] = [min(item + 0.01 * offset, 1.0) for item in base] + [0.99]
    return pd.DataFrame(payload)


def _endpoint() -> pd.DataFrame:
    rows = []
    for reason, counts in REASON_CENSUS.items():
        rows.append(
            {
                "role": "primary_oot",
                "snapshot_resolution": reason,
                **counts,
            }
        )
    rows.append(
        {
            "role": "conformal_fit",
            "snapshot_resolution": "fully_paid_by_reconstructed_cutoff",
            "candidate_rows": 2,
            "resolved_rows": 2,
            "unresolved_rows": 0,
        }
    )
    return pd.DataFrame(rows)


def _run(
    scores: pd.DataFrame | None = None,
    endpoint: pd.DataFrame | None = None,
):
    return marginal_mean_score_outcome_gap(
        _scores() if scores is None else scores,
        _endpoint() if endpoint is None else endpoint,
        learners=LEARNERS,
        score_columns=SCORE_COLUMNS,
        role="primary_oot",
        expected_issue_months=("2016-04",),
        expected_reason_census=REASON_CENSUS,
        expected_candidates=4,
        expected_resolved=3,
        expected_unresolved=1,
        expected_resolved_y0=2,
        expected_resolved_y1=1,
    )


def test_complete_five_learner_interval_matches_binary_completion_oracle() -> None:
    result = _run()
    table = result.table.set_index("learner")
    assert result.table["learner"].tolist() == list(LEARNERS)
    assert result.table["estimand"].eq(ESTIMAND).all()
    assert len(result.table) == 5
    assert len(result.candidate_id_sha256) == 64
    assert result.issue_months == ("2016-04",)

    mean_score = 0.125
    attainable = [mean_score - ((1 + sum(completion)) / 4) for completion in product((0, 1))]
    assert table.loc["catboost_platt", "mean_score"] == pytest.approx(mean_score)
    assert table.loc["catboost_platt", "marginal_mean_score_outcome_gap_lower"] == pytest.approx(
        min(attainable)
    )
    assert table.loc["catboost_platt", "marginal_mean_score_outcome_gap_upper"] == pytest.approx(
        max(attainable)
    )
    assert table.loc["catboost_platt", "identification_width"] == pytest.approx(0.25)


def test_result_sign_never_blocks_complete_reporting() -> None:
    result = _run(_scores(value=0.90))
    assert len(result.table) == 5
    assert result.table["marginal_mean_score_outcome_gap_upper"].gt(0.0).all()
    assert result.table["marginal_mean_score_outcome_gap_lower"].gt(0.0).all()


def test_candidate_hash_and_results_are_invariant_to_input_row_order() -> None:
    original = _run()
    shuffled = _run(_scores().sample(frac=1.0, random_state=26).reset_index(drop=True))
    assert original.candidate_id_sha256 == shuffled.candidate_id_sha256
    pd.testing.assert_frame_equal(original.table, shuffled.table)


def test_duplicate_target_identifier_fails_closed() -> None:
    scores = _scores()
    scores.loc[1, "id"] = scores.loc[0, "id"]
    with pytest.raises(RuntimeError, match="duplicates"):
        _run(scores)


@pytest.mark.parametrize("invalid", [float("nan"), -0.01, 1.01])
def test_invalid_score_fails_closed(invalid: float) -> None:
    scores = _scores()
    scores.loc[0, "pd_catboost_platt"] = invalid
    with pytest.raises(RuntimeError, match=r"nonfinite|leaves"):
        _run(scores)


def test_issue_month_drift_fails_closed() -> None:
    scores = _scores()
    scores.loc[0, "issue_d"] = "2016-05-01"
    with pytest.raises(RuntimeError, match="issue-month"):
        _run(scores)


def test_endpoint_reason_drift_fails_closed() -> None:
    endpoint = _endpoint()
    mask = endpoint["snapshot_resolution"].eq("nonterminal_or_unresolved_status")
    endpoint.loc[mask, "candidate_rows"] = 2
    endpoint.loc[mask, "unresolved_rows"] = 2
    with pytest.raises(RuntimeError, match="Endpoint reason"):
        _run(endpoint=endpoint)


def test_endpoint_normalizer_rejects_nonpartitioning_reason() -> None:
    endpoint = _endpoint()
    endpoint.loc[0, "unresolved_rows"] = 1
    with pytest.raises(RuntimeError, match="does not partition"):
        normalize_endpoint_resolution_table(endpoint)
