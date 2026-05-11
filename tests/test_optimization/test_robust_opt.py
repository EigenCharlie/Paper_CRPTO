"""Property-based tests for ``src.optimization.robust_opt``.

The module is a thin set of math helpers that translate conformal prediction
intervals into uncertainty sets and scenario-based loss estimates. The
invariants are simple enough that Hypothesis can exhaustively check them
without re-running the frozen champion.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st
from hypothesis.extra.numpy import arrays

from src.optimization.robust_opt import (
    build_box_uncertainty_set,
    scenario_analysis,
    worst_case_expected_loss,
)

SUPPRESS = (HealthCheck.function_scoped_fixture,)


@st.composite
def pd_low_high(draw: st.DrawFn) -> tuple[np.ndarray, np.ndarray]:
    """Draw (pd_low, pd_high) with pd_low <= pd_high element-wise."""
    n = draw(st.integers(min_value=1, max_value=64))
    low = draw(arrays(np.float64, shape=n, elements=st.floats(0.0, 0.95)))
    extra = draw(arrays(np.float64, shape=n, elements=st.floats(0.0, 0.05)))
    high = np.clip(low + extra, 0.0, 1.0)
    return low, high


@st.composite
def pd_triple(draw: st.DrawFn) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Draw (pd_low, pd_point, pd_high) ordered element-wise."""
    n = draw(st.integers(min_value=1, max_value=32))
    low = draw(arrays(np.float64, shape=n, elements=st.floats(0.0, 0.6)))
    width = draw(arrays(np.float64, shape=n, elements=st.floats(0.0, 0.3)))
    high = np.clip(low + width, 0.0, 1.0)
    # pd_point lies somewhere between low and high
    alpha = draw(arrays(np.float64, shape=n, elements=st.floats(0.0, 1.0)))
    point = low + alpha * (high - low)
    return low, point, high


# ---------------------------------------------------------------------------
# build_box_uncertainty_set
# ---------------------------------------------------------------------------


@given(pair=pd_low_high())
@settings(max_examples=80, suppress_health_check=SUPPRESS, deadline=None)
def test_box_uncertainty_keys_and_shapes(pair: tuple[np.ndarray, np.ndarray]) -> None:
    low, high = pair
    out = build_box_uncertainty_set(low, high)
    assert set(out.keys()) == {"pd_low", "pd_high", "pd_center", "pd_radius"}
    for arr in out.values():
        assert arr.shape == low.shape


@given(pair=pd_low_high())
@settings(max_examples=80, suppress_health_check=SUPPRESS, deadline=None)
def test_box_center_between_low_and_high(pair: tuple[np.ndarray, np.ndarray]) -> None:
    low, high = pair
    out = build_box_uncertainty_set(low, high)
    assert np.all(out["pd_center"] >= low - 1e-12)
    assert np.all(out["pd_center"] <= high + 1e-12)


@given(pair=pd_low_high())
@settings(max_examples=80, suppress_health_check=SUPPRESS, deadline=None)
def test_box_radius_non_negative(pair: tuple[np.ndarray, np.ndarray]) -> None:
    low, high = pair
    out = build_box_uncertainty_set(low, high)
    assert np.all(out["pd_radius"] >= -1e-12)


def test_box_with_lgd_bounds_includes_lgd_keys() -> None:
    pd_low = np.array([0.05, 0.10])
    pd_high = np.array([0.12, 0.20])
    lgd_low = np.array([0.30, 0.35])
    lgd_high = np.array([0.50, 0.55])
    out = build_box_uncertainty_set(pd_low, pd_high, lgd_low=lgd_low, lgd_high=lgd_high)
    assert {"lgd_low", "lgd_high", "lgd_center", "lgd_radius"} <= out.keys()
    assert np.allclose(out["lgd_center"], (lgd_low + lgd_high) / 2)
    assert np.allclose(out["lgd_radius"], (lgd_high - lgd_low) / 2)


# ---------------------------------------------------------------------------
# worst_case_expected_loss
# ---------------------------------------------------------------------------


@given(pair=pd_low_high(), gamma=st.floats(0.0, 1.0))
@settings(max_examples=60, suppress_health_check=SUPPRESS, deadline=None)
def test_worst_case_loss_non_negative(pair: tuple[np.ndarray, np.ndarray], gamma: float) -> None:
    _, pd_high = pair
    n = pd_high.shape[0]
    allocation = np.full(n, gamma)
    loan_amounts = np.ones(n) * 1000.0
    loss = worst_case_expected_loss(allocation, loan_amounts, pd_high)
    assert loss >= -1e-9


@given(pair=pd_low_high())
@settings(max_examples=40, suppress_health_check=SUPPRESS, deadline=None)
def test_worst_case_loss_scales_with_allocation(
    pair: tuple[np.ndarray, np.ndarray],
) -> None:
    _, pd_high = pair
    n = pd_high.shape[0]
    loan_amounts = np.ones(n) * 1000.0
    half = worst_case_expected_loss(np.full(n, 0.5), loan_amounts, pd_high)
    full = worst_case_expected_loss(np.full(n, 1.0), loan_amounts, pd_high)
    zero = worst_case_expected_loss(np.zeros(n), loan_amounts, pd_high)
    assert zero == pytest.approx(0.0, abs=1e-9)
    assert half <= full + 1e-9
    if np.any(pd_high > 0):
        assert full > zero


def test_worst_case_loss_uses_lgd_high_when_provided() -> None:
    allocation = np.array([1.0, 1.0])
    loan_amounts = np.array([1000.0, 1000.0])
    pd_high = np.array([0.10, 0.20])
    lgd_high = np.array([0.50, 0.60])
    loss_with = worst_case_expected_loss(allocation, loan_amounts, pd_high, lgd_high=lgd_high)
    loss_default = worst_case_expected_loss(allocation, loan_amounts, pd_high)
    expected_with = 1000.0 * 0.10 * 0.50 + 1000.0 * 0.20 * 0.60
    expected_default = 1000.0 * 0.10 * 0.45 + 1000.0 * 0.20 * 0.45
    assert loss_with == pytest.approx(expected_with)
    assert loss_default == pytest.approx(expected_default)


# ---------------------------------------------------------------------------
# scenario_analysis
# ---------------------------------------------------------------------------


@given(triple=pd_triple())
@settings(max_examples=60, suppress_health_check=SUPPRESS, deadline=None)
def test_scenario_ordering_best_le_expected_le_worst(
    triple: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    low, point, high = triple
    n = low.shape[0]
    allocation = np.full(n, 0.5)
    loan_amounts = np.ones(n) * 1000.0
    lgd = np.full(n, 0.45)
    df = scenario_analysis(allocation, loan_amounts, low, point, high, lgd)
    row = df.iloc[0]
    assert row["best_case"] <= row["expected"] + 1e-9
    assert row["expected"] <= row["worst_case"] + 1e-9
    assert row["range"] >= -1e-9


def test_scenario_analysis_columns() -> None:
    n = 4
    allocation = np.full(n, 1.0)
    loan_amounts = np.full(n, 500.0)
    lgd = np.full(n, 0.45)
    df = scenario_analysis(
        allocation,
        loan_amounts,
        pd_low=np.full(n, 0.05),
        pd_point=np.full(n, 0.10),
        pd_high=np.full(n, 0.20),
        lgd=lgd,
    )
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["best_case", "expected", "worst_case", "range"]
    assert len(df) == 1
