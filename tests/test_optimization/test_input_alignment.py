from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.optimization.input_alignment import align_candidate_intervals


def test_id_alignment_preserves_left_order_and_interval_payload() -> None:
    candidates = pd.DataFrame(
        {
            "id": ["b", "a", "c"],
            "grade": ["B", "A", "C"],
            "y_pred": [9.0, 8.0, 7.0],
        }
    )
    intervals = pd.DataFrame(
        {
            "id": ["a", "b", "c"],
            "grade": ["score_q01", "score_q02", "score_q03"],
            "y_pred": [0.1, 0.2, 0.3],
        }
    )

    aligned = align_candidate_intervals(
        candidates,
        intervals,
        max_candidates=None,
        random_state=42,
    )

    assert aligned.mode == "id"
    assert aligned.available_rows == 3
    assert aligned.selected_rows == 3
    assert aligned.candidates["id"].tolist() == ["b", "a", "c"]
    assert aligned.candidates["grade"].tolist() == ["B", "A", "C"]
    assert aligned.intervals["id"].tolist() == ["b", "a", "c"]
    assert aligned.intervals["grade"].tolist() == ["score_q02", "score_q01", "score_q03"]
    np.testing.assert_allclose(aligned.intervals["y_pred"], [0.2, 0.1, 0.3])


def test_id_alignment_sampling_is_sorted_and_reproducible() -> None:
    candidates = pd.DataFrame({"id": np.arange(20), "row": np.arange(20)})
    intervals = pd.DataFrame(
        {
            "id": np.arange(19, -1, -1),
            "y_pred": np.arange(19, -1, -1) / 100.0,
        }
    )
    expected_positions = np.sort(np.random.default_rng(17).choice(20, size=6, replace=False))

    first = align_candidate_intervals(
        candidates,
        intervals,
        max_candidates=6,
        random_state=17,
    )
    second = align_candidate_intervals(
        candidates,
        intervals,
        max_candidates=6,
        random_state=17,
    )

    assert first.candidates["row"].tolist() == expected_positions.tolist()
    pd.testing.assert_frame_equal(first.candidates, second.candidates)
    pd.testing.assert_frame_equal(first.intervals, second.intervals)


def test_row_number_alignment_reorders_interval_rows_without_losing_source_columns() -> None:
    candidates = pd.DataFrame({"loan": ["a", "b", "c"], "grade": ["A", "B", "C"]})
    intervals = pd.DataFrame(
        {
            "_row_number": [2, 0, 1],
            "grade": ["q3", "q1", "q2"],
            "y_pred": [0.3, 0.1, 0.2],
        }
    )

    aligned = align_candidate_intervals(
        candidates,
        intervals,
        max_candidates=0,
        random_state=42,
    )

    assert aligned.mode == "row_number"
    assert aligned.candidates["loan"].tolist() == ["a", "b", "c"]
    assert aligned.intervals["_row_number"].tolist() == [0, 1, 2]
    assert aligned.intervals["grade"].tolist() == ["q1", "q2", "q3"]


def test_positional_fallback_samples_from_full_alignable_universe() -> None:
    candidates = pd.DataFrame({"row": np.arange(10)})
    intervals = pd.DataFrame({"y_pred": np.arange(10) / 100.0})
    expected_positions = np.sort(np.random.default_rng(7).choice(10, size=4, replace=False))

    aligned = align_candidate_intervals(
        candidates,
        intervals,
        max_candidates=4,
        random_state=7,
    )

    assert aligned.mode == "position"
    assert aligned.available_rows == 10
    assert aligned.candidates["row"].tolist() == expected_positions.tolist()
    np.testing.assert_allclose(
        aligned.intervals["y_pred"],
        expected_positions / 100.0,
    )
    assert max(expected_positions) >= 4


@pytest.mark.parametrize(
    ("candidate_ids", "interval_ids", "message"),
    [
        (["a", "a"], ["a", "b"], "candidate id alignment key is not unique"),
        (["a", "b"], ["a", "a"], "interval id alignment key is not unique"),
        (["a", None], ["a", "b"], "candidate id alignment key contains missing"),
        (["a", "b"], ["a", None], "interval id alignment key contains missing"),
    ],
)
def test_id_alignment_rejects_ambiguous_keys(
    candidate_ids: list[str | None],
    interval_ids: list[str | None],
    message: str,
) -> None:
    candidates = pd.DataFrame({"id": candidate_ids})
    intervals = pd.DataFrame({"id": interval_ids, "y_pred": [0.1, 0.2]})

    with pytest.raises(ValueError, match=message):
        align_candidate_intervals(
            candidates,
            intervals,
            max_candidates=None,
            random_state=42,
        )


def test_id_alignment_rejects_disjoint_universes() -> None:
    candidates = pd.DataFrame({"id": ["a", "b"]})
    intervals = pd.DataFrame({"id": ["c", "d"], "y_pred": [0.1, 0.2]})

    with pytest.raises(ValueError, match="universes do not match exactly"):
        align_candidate_intervals(
            candidates,
            intervals,
            max_candidates=None,
            random_state=42,
        )


def test_id_alignment_rejects_partial_overlap_by_default() -> None:
    candidates = pd.DataFrame({"id": ["a", "b", "c"]})
    intervals = pd.DataFrame({"id": ["a", "b", "d"], "y_pred": [0.1, 0.2, 0.3]})

    with pytest.raises(ValueError, match="universes do not match exactly"):
        align_candidate_intervals(
            candidates,
            intervals,
            max_candidates=None,
            random_state=42,
        )


def test_partial_overlap_requires_explicit_legacy_opt_out() -> None:
    candidates = pd.DataFrame({"id": ["a", "b", "c"]})
    intervals = pd.DataFrame({"id": ["a", "b", "d"], "y_pred": [0.1, 0.2, 0.3]})

    aligned = align_candidate_intervals(
        candidates,
        intervals,
        max_candidates=None,
        random_state=42,
        require_full_match=False,
    )

    assert aligned.available_rows == 2
    assert aligned.candidates["id"].tolist() == ["a", "b"]
