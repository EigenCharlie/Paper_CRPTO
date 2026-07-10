from __future__ import annotations

import pandas as pd
import pytest

from src.optimization.policy_selection import (
    build_linear_policy_grid,
    select_policy_result_ex_ante,
    temporal_period_labels,
)


def _selection_results() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "candidate_id": ["linear-001", "linear-002", "linear-003"],
            "solver_status": ["Optimal", "Optimal", "Optimal"],
            "expected_objective": [120.0, 110.0, 100.0],
            "markov_loss_threshold": [0.70, 0.58, 0.50],
            "weighted_pd_effective": [0.17, 0.17, 0.17],
            "risk_tolerance": [0.17, 0.17, 0.17],
            "total_allocated": [1_000.0, 1_000.0, 1_000.0],
        }
    )


def test_round_grid_is_deterministic() -> None:
    grid = build_linear_policy_grid(
        risk_tolerances=[0.15, 0.17, 0.19],
        gammas=[0.25, 0.50, 0.75],
        uncertainty_aversions=[0.0],
    )

    assert len(grid) == 9
    assert grid[4].candidate_id == "linear-005"
    assert grid[4].risk_tolerance == 0.17
    assert grid[4].gamma == 0.50


def test_selector_uses_expected_objective_inside_screen() -> None:
    selected, audit = select_policy_result_ex_ante(
        _selection_results(),
        markov_threshold_cap=0.60,
        budget=1_000.0,
    )

    assert selected["candidate_id"] == "linear-002"
    assert audit["n_eligible"] == 2
    assert audit["outcome_columns_used"] == 0


def test_selector_does_not_accept_suboptimal_status() -> None:
    results = _selection_results()
    results.loc[0, "solver_status"] = "Suboptimal"
    results.loc[0, "markov_loss_threshold"] = 0.50

    selected, _ = select_policy_result_ex_ante(
        results,
        markov_threshold_cap=0.60,
        budget=1_000.0,
    )

    assert selected["candidate_id"] == "linear-002"


def test_selector_rejects_duplicate_candidates() -> None:
    results = pd.concat([_selection_results(), _selection_results().iloc[[0]]])

    with pytest.raises(ValueError, match="duplicate candidate_id"):
        select_policy_result_ex_ante(
            results,
            markov_threshold_cap=0.60,
            budget=1_000.0,
        )


def test_selector_rejects_outcome_derived_columns() -> None:
    results = _selection_results().assign(realized_return=[1.0, 2.0, 3.0])

    with pytest.raises(ValueError, match="outcome-derived"):
        select_policy_result_ex_ante(
            results,
            markov_threshold_cap=0.60,
            budget=1_000.0,
        )


def test_selector_rejects_invalid_budget_utilization() -> None:
    with pytest.raises(ValueError, match="min_budget_utilization"):
        select_policy_result_ex_ante(
            _selection_results(),
            markov_threshold_cap=0.60,
            budget=1_000.0,
            min_budget_utilization=1.01,
        )


def test_temporal_labels_pool_late_years() -> None:
    dates = pd.Series(["2018-01-01", "2018-08-01", "2020-03-01", "2021-09-01"])

    assert temporal_period_labels(dates).tolist() == [
        "2018H1",
        "2018H2",
        "2020+",
        "2020+",
    ]
