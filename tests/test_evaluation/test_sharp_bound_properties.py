from __future__ import annotations

from itertools import product

import numpy as np
import pytest
from hypothesis import given, strategies as st

from src.evaluation.policy_contrast_bounds import (
    _binary_identification_width,
    _sharp_binary_sum_bounds,
)


@st.composite
def binary_sum_cases(
    draw: st.DrawFn,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    size = draw(st.integers(min_value=1, max_value=8))
    values = st.floats(
        min_value=-1_000.0,
        max_value=1_000.0,
        allow_nan=False,
        allow_infinity=False,
        width=32,
    )
    value_if_zero = np.asarray(
        draw(st.lists(values, min_size=size, max_size=size)),
        dtype=float,
    )
    value_if_one = np.asarray(
        draw(st.lists(values, min_size=size, max_size=size)),
        dtype=float,
    )
    outcome_codes = draw(st.lists(st.sampled_from((0, 1, None)), min_size=size, max_size=size))
    outcomes = np.asarray(
        [np.nan if value is None else float(value) for value in outcome_codes],
        dtype=float,
    )
    return value_if_zero, value_if_one, outcomes


@given(binary_sum_cases())
def test_sharp_binary_bounds_equal_exhaustive_completion_extrema(
    case: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    value_if_zero, value_if_one, outcomes = case
    lower, upper = _sharp_binary_sum_bounds(value_if_zero, value_if_one, outcomes)
    unresolved = np.flatnonzero(~np.isfinite(outcomes))
    attainable: list[float] = []
    for assignment in product((0.0, 1.0), repeat=len(unresolved)):
        completed = outcomes.copy()
        completed[unresolved] = assignment
        contributions = np.where(completed == 1.0, value_if_one, value_if_zero)
        attainable.append(float(contributions.sum()))

    assert lower == pytest.approx(min(attainable), abs=1.0e-9)
    assert upper == pytest.approx(max(attainable), abs=1.0e-9)
    assert lower <= upper


@given(binary_sum_cases())
def test_identification_width_reconciles_with_sharp_interval(
    case: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    value_if_zero, value_if_one, outcomes = case
    lower, upper = _sharp_binary_sum_bounds(value_if_zero, value_if_one, outcomes)
    width = _binary_identification_width(value_if_zero, value_if_one, outcomes)

    assert width >= 0.0
    assert width == pytest.approx(upper - lower, abs=1.0e-9)
