from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.optimize_portfolio_tradeoff import (
    _build_policy_grid,
    _prepare_tradeoff_inputs,
    _select_champion_policy,
)


def test_build_policy_grid_preserves_tradeoff_frontier_contract() -> None:
    grid = _build_policy_grid()

    assert len(grid) == 63
    assert len(grid) == len(set(grid))
    assert grid[0] == ("hard_worst_case", 1.0, 1.0, 1.0)
    assert {mode for mode, _, _, _ in grid} == {
        "hard_worst_case",
        "blended_uncertainty",
        "capped_blended_uncertainty",
        "tail_blended_uncertainty",
        "segment_tail_blended_uncertainty",
        "segment_relative_tail_blended_uncertainty",
    }
    assert all(0.0 <= gamma <= 1.0 for _, gamma, _, _ in grid)
    assert {delta_cap for _, _, delta_cap, _ in grid} == {0.50, 0.75, 0.90, 1.0}
    assert {tail_focus for _, _, _, tail_focus in grid} == {0.75, 0.90, 0.95, 1.0}


def test_prepare_tradeoff_inputs_resolves_modern_interval_columns() -> None:
    loans = pd.DataFrame(
        {
            "int_rate": ["10.5%", "8.0%", None],
            "default_flag": [0, 1, None],
        }
    )
    intervals = pd.DataFrame(
        {
            "y_pred": [0.10, 0.20, 0.30],
            "pd_low_90": [0.05, 0.10, 0.20],
            "pd_high_90": [0.15, 0.30, 0.40],
        }
    )

    prepared = _prepare_tradeoff_inputs(loans, intervals)

    np.testing.assert_allclose(prepared.pd_point, [0.10, 0.20, 0.30])
    np.testing.assert_allclose(prepared.pd_low, [0.05, 0.10, 0.20])
    np.testing.assert_allclose(prepared.pd_high, [0.15, 0.30, 0.40])
    np.testing.assert_allclose(prepared.lgd, [0.45, 0.45, 0.45])
    np.testing.assert_allclose(prepared.int_rates, [0.105, 0.08, 0.12])
    np.testing.assert_array_equal(prepared.default_flag, [0, 1, 0])


def test_prepare_tradeoff_inputs_uses_defaults_for_optional_loan_columns() -> None:
    loans = pd.DataFrame({"loan_amnt": [1000.0, 2000.0]})
    intervals = pd.DataFrame(
        {
            "pd_point": [0.11, 0.22],
            "pd_low": [0.01, 0.02],
            "pd_high": [0.31, 0.42],
        }
    )

    prepared = _prepare_tradeoff_inputs(loans, intervals)

    np.testing.assert_allclose(prepared.pd_point, [0.11, 0.22])
    np.testing.assert_allclose(prepared.pd_low, [0.01, 0.02])
    np.testing.assert_allclose(prepared.pd_high, [0.31, 0.42])
    np.testing.assert_allclose(prepared.int_rates, [0.12, 0.12])
    np.testing.assert_array_equal(prepared.default_flag, [0, 0])


def test_select_champion_policy_exposes_dual_selectors() -> None:
    frontier = pd.DataFrame(
        [
            {
                "policy": "nonrobust",
                "risk_tolerance": 0.10,
                "policy_mode": "point_estimate",
                "gamma": 0.0,
                "uncertainty_aversion": 0.0,
                "realized_total_return": 100.0,
                "price_of_robustness": 0.0,
                "ab_pass": True,
                "n_funded": 10,
                "solver_backend": "cuopt",
                "min_budget_utilization": 0.0,
                "pd_cap_slack_penalty": 0.0,
                "pd_cap_slack": 0.0,
                "ab_diff_total_return": 0.0,
            },
            {
                "policy": "robust",
                "risk_tolerance": 0.10,
                "policy_mode": "blended_uncertainty",
                "gamma": 0.0,
                "uncertainty_aversion": 0.0,
                "realized_total_return": 120.0,
                "price_of_robustness": -10.0,
                "ab_pass": True,
                "n_funded": 11,
                "solver_backend": "cuopt",
                "min_budget_utilization": 0.0,
                "pd_cap_slack_penalty": 0.0,
                "pd_cap_slack": 0.0,
                "ab_diff_total_return": 20.0,
            },
            {
                "policy": "robust",
                "risk_tolerance": 0.10,
                "policy_mode": "blended_uncertainty",
                "gamma": 0.5,
                "uncertainty_aversion": 0.5,
                "realized_total_return": 95.0,
                "price_of_robustness": 5.0,
                "ab_pass": True,
                "n_funded": 9,
                "solver_backend": "cuopt",
                "min_budget_utilization": 0.05,
                "pd_cap_slack_penalty": 1.5,
                "pd_cap_slack": 0.0,
                "ab_diff_total_return": -5.0,
            },
        ]
    )

    frontier_out, selected, robust_selected, balanced_selected, guardrail_selected = (
        _select_champion_policy(frontier)
    )

    assert selected["gamma"] == 0.0
    assert robust_selected is not None
    assert robust_selected["gamma"] == 0.5
    assert balanced_selected is not None
    assert balanced_selected["gamma"] == 0.5
    assert guardrail_selected is not None
    assert guardrail_selected["gamma"] == 0.5
    assert frontier_out["selected_for_champion"].sum() == 1
    assert frontier_out["selected_for_robustness_aware"].sum() == 1
    assert frontier_out["selected_for_balanced_robustness"].sum() == 1
    assert frontier_out["selected_for_guardrail_robustness"].sum() == 1
