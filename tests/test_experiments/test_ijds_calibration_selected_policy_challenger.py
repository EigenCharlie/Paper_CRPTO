from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.experiments.run_ijds_calibration_selected_policy_challenger import (
    FORBIDDEN_SELECTOR_COLUMNS,
    _funded_allocation_frame,
    _measure_ex_ante_solution,
    _selector_input_frame,
)
from src.optimization.policy import PolicyMode
from src.optimization.policy_evaluation import PolicyAllocationResult
from src.optimization.policy_selection import LinearPolicyCandidate


def test_ex_ante_measurement_contains_no_outcome_fields() -> None:
    frame = pd.DataFrame(
        {
            "_loan_amount": [100.0, 200.0],
            "_pd_point": [0.10, 0.20],
            "_pd_high": [0.30, 0.50],
        }
    )
    candidate = LinearPolicyCandidate(
        candidate_id="linear-001",
        risk_tolerance=0.20,
        gamma=0.50,
        uncertainty_aversion=0.0,
    )
    result = PolicyAllocationResult(
        solution={
            "solver_status": "Optimal",
            "objective_value": 10.0,
        },
        allocation=np.array([1.0, 0.5]),
        effective_pd=np.array([0.20, 0.35]),
        policy_mode=PolicyMode.BLENDED_UNCERTAINTY,
        gamma=0.50,
        delta_cap_quantile=1.0,
        tail_focus_quantile=1.0,
        objective_risk_mode="point_pd_plus_aversion",
    )

    record = _measure_ex_ante_solution(frame, candidate, result, alpha=0.10)

    assert not FORBIDDEN_SELECTOR_COLUMNS.intersection(record)
    assert record["expected_objective"] == 10.0
    assert record["weighted_pd_effective"] == 0.275


def test_selector_input_frame_drops_all_outcomes() -> None:
    frame = pd.DataFrame(
        {
            "id": ["a"],
            "loan_amnt": [100.0],
            "purpose": ["credit_card"],
            "issue_d": ["2017-11-01"],
            "default_flag": [1],
            "y_true": [1],
            "loan_status": ["Charged Off"],
            "_outcome": [1.0],
            "_pd_point": [0.1],
            "_pd_low": [0.0],
            "_pd_high": [0.3],
            "_loan_amount": [100.0],
            "_int_rate": [0.2],
        }
    )

    selector = _selector_input_frame(frame)

    assert not {"default_flag", "y_true", "loan_status", "_outcome"}.intersection(selector.columns)


def test_funded_allocation_frame_reconciles_exposure_and_return() -> None:
    frame = pd.DataFrame(
        {
            "id": ["a", "b"],
            "issue_d": ["2020-01-01", "2020-02-01"],
            "grade": ["A", "B"],
            "_loan_amount": [100.0, 200.0],
            "_int_rate": [0.10, 0.20],
            "_outcome": [0.0, 1.0],
            "_pd_point": [0.10, 0.20],
            "_pd_low": [0.0, 0.0],
            "_pd_high": [0.30, 0.50],
        }
    )
    result = PolicyAllocationResult(
        solution={"solver_status": "Optimal", "objective_value": 10.0},
        allocation=np.array([1.0, 0.5]),
        effective_pd=np.array([0.20, 0.35]),
        policy_mode=PolicyMode.BLENDED_UNCERTAINTY,
        gamma=0.50,
        delta_cap_quantile=1.0,
        tail_focus_quantile=1.0,
        objective_risk_mode="point_pd_plus_aversion",
    )

    funded = _funded_allocation_frame(frame, result, role="selected", lgd=0.45)

    assert funded["funded_exposure"].sum() == 200.0
    assert funded["funded_weight"].sum() == 1.0
    assert funded["realized_return_contribution"].sum() == -35.0
