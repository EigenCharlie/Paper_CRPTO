from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.evaluation import maturity_safe_portfolio as portfolio
from src.optimization.policy import PolicyMode
from src.optimization.policy_selection import LinearPolicyCandidate


def _decision_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": ["a", "b"],
            "issue_d": pd.to_datetime(["2016-04-01", "2016-04-01"]),
            "loan_amnt": [100.0, 200.0],
            "purpose": ["x", "y"],
            "contractual_rate": [0.10, 0.20],
            "pd_point": [0.10, 0.25],
            "conformal_lower": [0.00, 0.10],
            "conformal_upper": [0.20, 0.40],
            "conformal_group": [0, 1],
        }
    )


def _config(*, strict: bool) -> dict[str, object]:
    return {
        "payoff": {"lgd": 0.45},
        "policy": {
            "budget": 200.0,
            "max_concentration_by_purpose": 1.0,
            "min_budget_utilization_solver": 1.0,
        },
        "execution": {
            "solver_time_limit_seconds": 10,
            "threads": 1,
            "solver_backend": "highspy",
            "strict_solver_backend": strict,
            "random_seed": 42,
        },
    }


def _candidate() -> LinearPolicyCandidate:
    return LinearPolicyCandidate(
        candidate_id="linear-001",
        risk_tolerance=0.17,
        gamma=0.5,
        uncertainty_aversion=0.0,
        min_budget_utilization=1.0,
    )


def _fake_solver(actual_backend: str, captured: dict[str, np.ndarray]):
    def solve(**kwargs: object) -> SimpleNamespace:
        point = np.asarray(kwargs["pd_point"], dtype=float)
        legacy_interest = np.asarray(kwargs["int_rates"], dtype=float)
        lgd = np.asarray(kwargs["lgd"], dtype=float)
        allocation = np.array([1.0, 0.5])
        exposure = allocation * _decision_frame()["loan_amnt"].to_numpy(dtype=float)
        captured["int_rates"] = legacy_interest
        return SimpleNamespace(
            solution={
                "solver_status": "Optimal",
                "solver_backend": actual_backend,
                "objective_value": float(exposure @ (legacy_interest - point * lgd)),
            },
            allocation=allocation,
            effective_pd=point,
            policy_mode=PolicyMode.BLENDED_UNCERTAINTY,
            gamma=0.5,
            delta_cap_quantile=1.0,
            tail_focus_quantile=1.0,
            objective_risk_mode="legacy",
        )

    return solve


def test_coherent_objective_uses_legacy_solver_argument_compatibly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, np.ndarray] = {}
    monkeypatch.setattr(portfolio, "solve_policy_allocation", _fake_solver("highspy", captured))

    solved = portfolio.solve_coherent_policy(
        _decision_frame(),
        _candidate(),
        config=_config(strict=True),
        robust=True,
    )

    np.testing.assert_allclose(captured["int_rates"], np.array([0.09, 0.15]))
    np.testing.assert_allclose(solved.expected_payoff_rate, np.array([0.045, 0.0375]))


def test_strict_highspy_backend_rejects_silent_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        portfolio,
        "solve_policy_allocation",
        _fake_solver("highspy_fallback_highs_sparse", {}),
    )

    with pytest.raises(RuntimeError, match="Strict solver backend mismatch"):
        portfolio.solve_coherent_policy(
            _decision_frame(),
            _candidate(),
            config=_config(strict=True),
            robust=True,
        )


def test_non_strict_backend_retains_fallback_compatibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        portfolio,
        "solve_policy_allocation",
        _fake_solver("highspy_fallback_highs_sparse", {}),
    )

    solved = portfolio.solve_coherent_policy(
        _decision_frame(),
        _candidate(),
        config=_config(strict=False),
        robust=True,
    )

    assert solved.result.solution["solver_backend"] == "highspy_fallback_highs_sparse"


def test_prejoined_evaluation_separates_menu_and_funded_censoring_counts() -> None:
    joined = _decision_frame().assign(
        allocation_fraction=[1.0, 0.5],
        exposure=[100.0, 100.0],
        weight=[0.5, 0.5],
        pd_effective=[0.1, 0.25],
        expected_payoff_rate=[0.045, 0.0375],
        expected_payoff_contribution=[4.5, 3.75],
        role="primary_oot",
        period="2016-04",
        policy_label="guardrail_linear-001",
        candidate_id="linear-001",
        snapshot_default=pd.Series([0, pd.NA], dtype="Int8"),
        snapshot_resolution=pd.Series(["fully_paid", "right_censored"], dtype="string"),
    )
    base_record = {
        "role": "primary_oot",
        "period": "2016-04",
        "policy_label": "guardrail_linear-001",
        "robust_guardrail": True,
        "total_allocated": 200.0,
    }

    record, evaluated = portfolio.evaluate_prejoined_frozen_allocation(
        base_record,
        joined,
        config=_config(strict=True),
        n_unresolved_candidates=7,
    )

    assert record["n_unresolved_candidates"] == 7
    assert record["n_unresolved_positive_exposure"] == 1
    assert record["unresolved_exposure_share"] == pytest.approx(0.5)
    assert evaluated["realized_payoff_lower"].notna().all()
