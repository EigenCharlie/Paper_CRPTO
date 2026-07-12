from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.evaluation.comparator_audit import (
    affine_score_cap_diagnostics,
    build_fixed_cap_grid,
    comparator_multiverse_envelope,
    contemporaneous_point_cap_target,
    development_supported_cap_range,
    exact_match_diagnostics,
    require_affine_score_cap_equivalence,
    translate_affine_score_cap,
    weighted_funded_point_risk,
)


def test_development_supported_cap_range_rounds_outward_and_clips() -> None:
    result = development_supported_cap_range(
        [0.0531, 0.0683, 0.07342],
        step=0.0025,
        lower_limit=0.05,
        upper_limit=0.12,
    )

    assert result.lower == pytest.approx(0.0525)
    assert result.upper == pytest.approx(0.075)
    assert result.target_minimum == pytest.approx(0.0531)
    assert result.target_maximum == pytest.approx(0.07342)
    assert result.target_count == 3


def test_weighted_point_risk_and_match_reconcile_exactly() -> None:
    allocations = np.array([0.0, 20.0, 30.0, 50.0])
    point_risks = np.array([0.99, 0.02, 0.08, 0.10])
    expected = (20.0 * 0.02 + 30.0 * 0.08 + 50.0 * 0.10) / 100.0

    assert weighted_funded_point_risk(allocations, point_risks) == pytest.approx(expected)
    diagnostics = exact_match_diagnostics(
        allocations,
        point_risks,
        target=expected,
        tolerance=1e-15,
    )

    assert diagnostics.matched is True
    assert diagnostics.difference == pytest.approx(0.0, abs=1e-15)


def test_contemporaneous_target_accepts_only_outcome_free_allocations() -> None:
    allocation = pd.DataFrame(
        {"id": ["a", "b"], "exposure": [25.0, 75.0], "pd_point": [0.04, 0.08]}
    )
    assert contemporaneous_point_cap_target(allocation) == pytest.approx(0.07)

    with pytest.raises(ValueError, match="outcome-derived"):
        contemporaneous_point_cap_target(allocation.assign(snapshot_default=[0.0, 1.0]))


def test_affine_cap_translation_and_feasible_set_equivalence() -> None:
    point_scores = np.array([0.02, 0.05, 0.10, 0.20])
    audit_scores = 0.75 * point_scores + 0.01
    score_cap = 0.085

    assert translate_affine_score_cap(score_cap, slope=0.75, intercept=0.01) == pytest.approx(0.10)
    diagnostics = require_affine_score_cap_equivalence(
        point_scores,
        audit_scores,
        score_cap=score_cap,
    )

    assert diagnostics.is_affine is True
    assert diagnostics.feasible_sets_equal is True
    assert diagnostics.point_cap == pytest.approx(0.10)


def test_non_affine_scores_are_diagnosed_and_rejected() -> None:
    point_scores = np.array([0.0, 0.25, 0.50, 0.75, 1.0])
    audit_scores = point_scores**2

    diagnostics = affine_score_cap_diagnostics(
        point_scores,
        audit_scores,
        score_cap=0.4,
        tolerance=1e-10,
    )
    assert diagnostics.is_affine is False
    assert diagnostics.point_cap is None
    assert diagnostics.max_absolute_residual > 0.0

    with pytest.raises(ValueError, match="positive affine mapping"):
        require_affine_score_cap_equivalence(
            point_scores,
            audit_scores,
            score_cap=0.4,
            tolerance=1e-10,
        )


@pytest.mark.parametrize(
    ("bounds", "expected_sign"),
    [
        ([(-3.0, -1.0), (-2.0, -0.5)], "strictly_negative"),
        ([(0.2, 1.0), (0.1, 2.0)], "strictly_positive"),
        ([(-1.0, -0.1), (0.2, 1.0)], "indeterminate"),
    ],
)
def test_comparator_multiverse_envelope_classifies_sign(
    bounds: list[tuple[float, float]], expected_sign: str
) -> None:
    frame = pd.DataFrame(bounds, columns=["lower", "upper"])
    envelope = comparator_multiverse_envelope(
        frame,
        lower_column="lower",
        upper_column="upper",
    )

    assert envelope.lower == min(lower for lower, _ in bounds)
    assert envelope.upper == max(upper for _, upper in bounds)
    assert envelope.sign == expected_sign


@pytest.mark.parametrize(
    ("start", "stop", "step"),
    [(0.2, 0.1, 0.01), (0.1, 0.2, 0.0), (0.1, 0.2, -0.1), (0.1, 0.25, 0.1)],
)
def test_fixed_cap_grid_rejects_invalid_ranges_and_steps(
    start: float, stop: float, step: float
) -> None:
    with pytest.raises(ValueError):
        build_fixed_cap_grid(start, stop, step)


def test_fixed_cap_grid_is_deterministic_and_includes_endpoints() -> None:
    expected = np.array([0.05, 0.10, 0.15, 0.20])
    np.testing.assert_array_equal(build_fixed_cap_grid(0.05, 0.20, 0.05), expected)
