from __future__ import annotations

import numpy as np
import pandas as pd

from src.evaluation.comparator_transport_simulation import (
    SimulationDesign,
    affine_transformed_cap,
    run_simulation,
    solve_full_budget_allocation,
)


def _small_design() -> SimulationDesign:
    return SimulationDesign(
        random_seed=20260711,
        repetitions=3,
        sample_size=240,
        temporal_shift_grid=(0.0, 0.10),
    )


def test_simulation_is_bitwise_deterministic() -> None:
    first = run_simulation(_small_design())
    second = run_simulation(_small_design())

    pd.testing.assert_frame_equal(first, second, check_exact=True)


def test_zero_shift_preserves_calibration_in_expectation() -> None:
    design = SimulationDesign(7, 40, 500, (0.0,))
    results = run_simulation(design)

    assert abs(results["score_drift"].mean()) < 0.01
    assert abs(results["base_rate_drift_coverage_effect"].mean()) < 0.01
    assert abs(results["transported_coverage"].mean() - (1.0 - design.alpha)) < 0.04


def test_positive_affine_placebo_has_identical_allocation() -> None:
    objective = np.array([8.0, 7.0, 6.0, 5.0, 4.0, 3.0])
    score = np.array([0.35, 0.30, 0.22, 0.12, 0.08, 0.04])
    cap = 0.18
    original = solve_full_budget_allocation(objective, score, funded_count=3, score_cap=cap)
    transformed = solve_full_budget_allocation(
        objective,
        2.5 * score + 0.07,
        funded_count=3,
        score_cap=affine_transformed_cap(cap, slope=2.5, intercept=0.07),
    )

    np.testing.assert_allclose(original, transformed, atol=1e-12, rtol=0.0)


def test_constructed_same_cap_and_moment_match_are_different() -> None:
    objective = np.array([10.0, 9.0, 8.0, 7.0, 6.0, 5.0])
    point = np.array([0.30, 0.26, 0.22, 0.10, 0.08, 0.05])
    group_score = np.array([0.44, 0.40, 0.26, 0.13, 0.10, 0.07])
    guard = solve_full_budget_allocation(objective, group_score, funded_count=3, score_cap=0.17)
    target = float(guard @ point / guard.sum())
    same_cap = solve_full_budget_allocation(objective, point, funded_count=3, score_cap=0.17)
    matched = solve_full_budget_allocation(objective, point, funded_count=3, score_cap=target)

    assert not np.allclose(same_cap, matched)
    assert abs(float(matched @ point / matched.sum()) - target) <= 1e-12
    assert abs(float(same_cap @ point / same_cap.sum()) - target) > 1e-3
