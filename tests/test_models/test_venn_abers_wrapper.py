"""Smoke tests for :class:`src.models.venn_abers.VennAbersScoreCalibrator`.

These do not re-train the champion calibrator; they only verify the wrapper
contract (1-D input, ordered bounds, point estimate within [0, 1]) on a small
synthetic dataset.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.models.venn_abers import VennAbersScoreCalibrator


@pytest.fixture
def synthetic_scores() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42)
    n = 200
    # Linear logit, well-separated classes
    y = rng.integers(0, 2, size=n)
    base = np.where(y == 1, 0.7, 0.2)
    noise = rng.normal(0.0, 0.05, size=n)
    scores = np.clip(base + noise, 0.0, 1.0)
    return scores, y


def test_fit_returns_self(synthetic_scores: tuple[np.ndarray, np.ndarray]) -> None:
    scores, y = synthetic_scores
    cal = VennAbersScoreCalibrator()
    out = cal.fit(scores, y)
    assert out is cal


def test_predict_before_fit_raises() -> None:
    cal = VennAbersScoreCalibrator()
    with pytest.raises(RuntimeError, match="not fitted"):
        cal.predict(np.array([0.1, 0.5, 0.9]))


def test_predict_returns_unit_interval(
    synthetic_scores: tuple[np.ndarray, np.ndarray],
) -> None:
    scores, y = synthetic_scores
    cal = VennAbersScoreCalibrator().fit(scores, y)
    out = cal.predict(scores)
    assert out.shape == scores.shape
    assert np.all((out >= 0.0) & (out <= 1.0))


def test_predict_proba_columns_sum_to_one(
    synthetic_scores: tuple[np.ndarray, np.ndarray],
) -> None:
    scores, y = synthetic_scores
    cal = VennAbersScoreCalibrator().fit(scores, y)
    proba = cal.predict_proba(scores)
    assert proba.shape == (scores.shape[0], 2)
    assert np.allclose(proba.sum(axis=1), 1.0, atol=1e-6)


def test_predict_intervals_ordered_low_le_high(
    synthetic_scores: tuple[np.ndarray, np.ndarray],
) -> None:
    scores, y = synthetic_scores
    cal = VennAbersScoreCalibrator().fit(scores, y)
    low, high = cal.predict_intervals(scores)
    assert low.shape == high.shape == scores.shape
    assert np.all(low <= high + 1e-12)
    assert np.all((low >= 0.0) & (high <= 1.0))


def test_one_dimensional_input_accepted() -> None:
    """The wrapper exists primarily to accept 1-D score vectors directly."""
    rng = np.random.default_rng(7)
    scores_1d = rng.uniform(0.0, 1.0, size=64)
    y = (scores_1d > 0.5).astype(int)
    cal = VennAbersScoreCalibrator().fit(scores_1d, y)
    out = cal.predict(scores_1d)
    assert out.ndim == 1
    assert out.shape == scores_1d.shape
