"""Tests for ``src.optimization.policy`` and the policy contract of
``src.optimization.portfolio_model.compute_effective_pd``.

Property-based tests (Hypothesis) exercise the invariants every uncertainty
policy must respect — without re-running the frozen champion. They use small
arrays generated on the fly so the suite stays fast.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st
from hypothesis.extra.numpy import arrays

from src.optimization.policy import PolicyMode, all_policy_modes, resolve_policy_mode
from src.optimization.portfolio_model import compute_effective_pd

# ---------------------------------------------------------------------------
# PolicyMode + resolver
# ---------------------------------------------------------------------------


def test_all_policy_modes_returns_seven_canonical_members() -> None:
    assert len(all_policy_modes()) == 7


@pytest.mark.parametrize(
    ("alias", "expected"),
    [
        ("point", PolicyMode.POINT_ESTIMATE),
        ("point_estimate", PolicyMode.POINT_ESTIMATE),
        ("nonrobust", PolicyMode.POINT_ESTIMATE),
        ("non_robust", PolicyMode.POINT_ESTIMATE),
        ("HARD_WORST_CASE", PolicyMode.HARD_WORST_CASE),
        ("Worst_Case", PolicyMode.HARD_WORST_CASE),
        ("robust", PolicyMode.HARD_WORST_CASE),
        ("blended", PolicyMode.BLENDED_UNCERTAINTY),
        ("blended_uncertainty", PolicyMode.BLENDED_UNCERTAINTY),
        ("capped_blended", PolicyMode.CAPPED_BLENDED_UNCERTAINTY),
        ("tail_blended", PolicyMode.TAIL_BLENDED_UNCERTAINTY),
        ("segment_tail_blended", PolicyMode.SEGMENT_TAIL_BLENDED_UNCERTAINTY),
        (
            "segment_relative_tail_blended",
            PolicyMode.SEGMENT_RELATIVE_TAIL_BLENDED_UNCERTAINTY,
        ),
    ],
)
def test_resolve_policy_mode_handles_aliases(alias: str, expected: PolicyMode) -> None:
    assert resolve_policy_mode(alias) is expected


def test_resolve_policy_mode_rejects_unknown_alias() -> None:
    with pytest.raises(ValueError, match="Unsupported policy_mode"):
        resolve_policy_mode("does_not_exist")


def test_resolve_policy_mode_passes_through_enum() -> None:
    assert resolve_policy_mode(PolicyMode.BLENDED_UNCERTAINTY) is PolicyMode.BLENDED_UNCERTAINTY


def test_resolve_policy_mode_defaults_for_none_or_empty() -> None:
    assert resolve_policy_mode(None) is PolicyMode.HARD_WORST_CASE
    assert resolve_policy_mode("") is PolicyMode.HARD_WORST_CASE


# ---------------------------------------------------------------------------
# compute_effective_pd — invariants per policy
# ---------------------------------------------------------------------------

PD_VEC = arrays(
    np.float64, shape=st.integers(min_value=1, max_value=64), elements=st.floats(0.0, 1.0)
)


@st.composite
def pd_pair(draw: st.DrawFn) -> tuple[np.ndarray, np.ndarray]:
    """Draw a (pd_point, pd_high) pair where pd_high >= pd_point elementwise."""
    point = draw(PD_VEC)
    extra = draw(
        arrays(
            np.float64,
            shape=point.shape,
            elements=st.floats(0.0, 1.0),
        )
    )
    high = np.clip(point + extra, 0.0, 1.0)
    return point, high


SUPPRESS_FUNCTION_SCOPED = (HealthCheck.function_scoped_fixture,)


@given(pair=pd_pair())
@settings(max_examples=80, suppress_health_check=SUPPRESS_FUNCTION_SCOPED, deadline=None)
def test_point_estimate_returns_point_pd(pair: tuple[np.ndarray, np.ndarray]) -> None:
    point, high = pair
    out = compute_effective_pd(point, high, policy_mode=PolicyMode.POINT_ESTIMATE)
    assert np.allclose(out, point)


@given(pair=pd_pair())
@settings(max_examples=80, suppress_health_check=SUPPRESS_FUNCTION_SCOPED, deadline=None)
def test_hard_worst_case_returns_upper_bound(pair: tuple[np.ndarray, np.ndarray]) -> None:
    point, high = pair
    out = compute_effective_pd(point, high, policy_mode=PolicyMode.HARD_WORST_CASE)
    assert np.allclose(out, high)


@given(pair=pd_pair(), gamma=st.floats(0.0, 1.0))
@settings(max_examples=80, suppress_health_check=SUPPRESS_FUNCTION_SCOPED, deadline=None)
def test_blended_is_between_point_and_high(
    pair: tuple[np.ndarray, np.ndarray], gamma: float
) -> None:
    point, high = pair
    out = compute_effective_pd(point, high, policy_mode=PolicyMode.BLENDED_UNCERTAINTY, gamma=gamma)
    assert np.all(out >= point - 1e-12)
    assert np.all(out <= high + 1e-12)
    assert np.all((out >= 0.0) & (out <= 1.0))


@given(pair=pd_pair(), gamma=st.floats(0.0, 1.0))
@settings(max_examples=60, suppress_health_check=SUPPRESS_FUNCTION_SCOPED, deadline=None)
def test_blended_monotone_in_gamma(pair: tuple[np.ndarray, np.ndarray], gamma: float) -> None:
    """Larger gamma must not decrease the effective PD on any loan."""
    point, high = pair
    out_low = compute_effective_pd(
        point, high, policy_mode=PolicyMode.BLENDED_UNCERTAINTY, gamma=0.0
    )
    out_high = compute_effective_pd(
        point, high, policy_mode=PolicyMode.BLENDED_UNCERTAINTY, gamma=1.0
    )
    out_mid = compute_effective_pd(
        point, high, policy_mode=PolicyMode.BLENDED_UNCERTAINTY, gamma=gamma
    )
    assert np.all(out_low <= out_mid + 1e-12)
    assert np.all(out_mid <= out_high + 1e-12)
    assert np.allclose(out_low, point)
    assert np.allclose(out_high, high)


@pytest.mark.parametrize("mode", list(all_policy_modes()))
def test_every_policy_produces_pd_in_unit_interval(mode: PolicyMode) -> None:
    rng = np.random.default_rng(seed=42)
    point = rng.uniform(0.0, 0.6, size=128)
    high = np.clip(point + rng.uniform(0.0, 0.3, size=128), 0.0, 1.0)
    segment_labels = rng.choice(["A", "B", "C"], size=128)
    out = compute_effective_pd(
        point,
        high,
        policy_mode=mode,
        gamma=0.5,
        delta_cap_quantile=0.95,
        tail_focus_quantile=0.85,
        segment_labels=segment_labels,
        min_segment_size=8,
    )
    assert out.shape == point.shape
    assert np.all((out >= 0.0) & (out <= 1.0))


def test_segment_tail_blended_uses_segment_cutoffs_when_segments_are_large() -> None:
    point = np.full(6, 0.10)
    high = point + np.array([0.01, 0.04, 0.07, 0.02, 0.06, 0.10])
    labels = np.array(["A", "A", "A", "B", "B", "B"])

    out = compute_effective_pd(
        point,
        high,
        policy_mode=PolicyMode.SEGMENT_TAIL_BLENDED_UNCERTAINTY,
        gamma=0.5,
        tail_focus_quantile=0.5,
        segment_labels=labels,
        min_segment_size=3,
    )

    expected_delta = np.array([0.00, 0.04, 0.07, 0.00, 0.06, 0.10])
    assert np.allclose(out, point + 0.5 * expected_delta)


def test_segment_relative_tail_blended_ranks_by_relative_width() -> None:
    point = np.array([0.10, 0.20, 0.10, 0.20])
    high = np.array([0.12, 0.26, 0.15, 0.22])
    labels = np.array(["A", "A", "B", "B"])

    out = compute_effective_pd(
        point,
        high,
        policy_mode=PolicyMode.SEGMENT_RELATIVE_TAIL_BLENDED_UNCERTAINTY,
        gamma=1.0,
        tail_focus_quantile=0.5,
        segment_labels=labels,
        min_segment_size=1,
    )

    assert np.allclose(out, np.array([0.10, 0.26, 0.15, 0.20]))


def test_legacy_string_aliases_still_work() -> None:
    """Backward compatibility: passing a legacy string must equal passing the enum."""
    rng = np.random.default_rng(seed=7)
    point = rng.uniform(0.0, 0.5, size=32)
    high = np.clip(point + rng.uniform(0.0, 0.2, size=32), 0.0, 1.0)
    for alias, mode in [
        ("worst_case", PolicyMode.HARD_WORST_CASE),
        ("robust", PolicyMode.HARD_WORST_CASE),
        ("point", PolicyMode.POINT_ESTIMATE),
        ("nonrobust", PolicyMode.POINT_ESTIMATE),
    ]:
        a = compute_effective_pd(point, high, policy_mode=alias)
        b = compute_effective_pd(point, high, policy_mode=mode)
        assert np.allclose(a, b)


def test_unsupported_mode_raises() -> None:
    point = np.array([0.1, 0.2])
    high = np.array([0.2, 0.3])
    with pytest.raises(ValueError, match="Unsupported policy_mode"):
        compute_effective_pd(point, high, policy_mode="bogus")
