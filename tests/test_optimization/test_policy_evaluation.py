from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.optimization import policy_evaluation
from src.optimization.policy import PolicyMode


def _inputs() -> dict[str, Any]:
    loans = pd.DataFrame(
        {
            "loan_amnt": [100.0, 200.0],
            "grade": ["A", "B"],
            "term": [36, 60],
            "verification_status": ["Verified", "Not Verified"],
        }
    )
    return {
        "loans": loans,
        "pd_point": np.array([0.10, 0.20]),
        "pd_low": np.array([0.05, 0.10]),
        "pd_high": np.array([0.30, 0.50]),
        "lgd": np.array([0.45, 0.45]),
        "int_rates": np.array([0.12, 0.15]),
    }


def test_solve_policy_allocation_resolves_effective_pd_once(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_optimize(**kwargs):
        captured.update(kwargs)
        return {
            "allocation_vector": np.array([1.0, 0.5]),
            "objective_value": 1.0,
            "n_funded": 2,
            "total_allocated": 200.0,
        }

    monkeypatch.setattr(policy_evaluation, "optimize_portfolio_allocation", fake_optimize)
    result = policy_evaluation.solve_policy_allocation(
        **_inputs(),
        policy_mode=PolicyMode.BLENDED_UNCERTAINTY,
        gamma=0.5,
    )

    assert result.policy_mode is PolicyMode.BLENDED_UNCERTAINTY
    assert np.allclose(result.effective_pd, np.array([0.20, 0.35]))
    assert np.allclose(captured["pd_constraint_override"], result.effective_pd)
    assert np.allclose(captured["pd_point"], _inputs()["pd_point"])
    assert result.objective_risk_mode == "point_pd_plus_aversion"
    assert np.allclose(result.allocation, np.array([1.0, 0.5]))


def test_nonrobust_policy_always_uses_point_pd(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_optimize(**kwargs):
        captured.update(kwargs)
        return {
            "allocation_vector": np.array([0.0, 1.0]),
            "objective_value": 1.0,
            "n_funded": 1,
            "total_allocated": 200.0,
        }

    monkeypatch.setattr(policy_evaluation, "optimize_portfolio_allocation", fake_optimize)
    result = policy_evaluation.solve_policy_allocation(
        **_inputs(),
        robust=False,
        policy_mode=PolicyMode.SEGMENT_TAIL_BLENDED_UNCERTAINTY,
        gamma=0.9,
        uncertainty_aversion=0.5,
    )

    assert result.policy_mode is PolicyMode.POINT_ESTIMATE
    assert result.gamma == 0.0
    assert np.allclose(result.effective_pd, _inputs()["pd_point"])
    assert np.allclose(captured["pd_constraint_override"], _inputs()["pd_point"])
    assert captured["uncertainty_aversion"] == 0.0


def test_uncertainty_aversion_keeps_point_pd_objective(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_optimize(**kwargs):
        captured.update(kwargs)
        return {
            "allocation_vector": np.array([1.0, 0.0]),
            "objective_value": 1.0,
            "n_funded": 1,
            "total_allocated": 100.0,
        }

    monkeypatch.setattr(policy_evaluation, "optimize_portfolio_allocation", fake_optimize)
    result = policy_evaluation.solve_policy_allocation(
        **_inputs(),
        policy_mode=PolicyMode.BLENDED_UNCERTAINTY,
        gamma=0.5,
        uncertainty_aversion=0.05,
    )

    assert np.allclose(captured["pd_point"], _inputs()["pd_point"])
    assert np.allclose(captured["pd_constraint_override"], result.effective_pd)
    assert captured["uncertainty_aversion"] == 0.05
    assert result.objective_risk_mode == "point_pd_plus_aversion"
