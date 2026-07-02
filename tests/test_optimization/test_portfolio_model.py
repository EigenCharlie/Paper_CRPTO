from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import src.optimization.portfolio_model as portfolio_model
from src.optimization.portfolio_model import optimize_portfolio_allocation


def _toy_loans() -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    loans = pd.DataFrame(
        {
            "loan_amnt": [1000, 1200, 900, 1100, 800, 950],
            "purpose": ["debt", "debt", "home", "home", "small", "small"],
        }
    )
    pd_point = np.array([0.03, 0.05, 0.08, 0.10, 0.12, 0.07], dtype=float)
    pd_low = np.clip(pd_point - 0.01, 0.0, 1.0)
    pd_high = pd_point + np.array([0.02, 0.02, 0.03, 0.03, 0.04, 0.02], dtype=float)
    lgd = np.full(len(loans), 0.45, dtype=float)
    int_rates = np.array([0.11, 0.13, 0.17, 0.18, 0.22, 0.16], dtype=float)
    return loans, pd_point, pd_low, pd_high, lgd, int_rates


def _weighted(values: np.ndarray, allocation: np.ndarray, amounts: np.ndarray) -> float:
    exposure = float(np.sum(allocation * amounts))
    return float(np.sum(allocation * amounts * values) / exposure)


def test_highs_sparse_respects_portfolio_constraints() -> None:
    loans, pd_point, pd_low, pd_high, lgd, int_rates = _toy_loans()
    result = optimize_portfolio_allocation(
        loans=loans,
        pd_point=pd_point,
        pd_low=pd_low,
        pd_high=pd_high,
        lgd=lgd,
        int_rates=int_rates,
        total_budget=3500,
        max_concentration=0.60,
        max_portfolio_pd=0.11,
        robust=True,
        pd_constraint_override=pd_high,
        solver_backend="highs_sparse",
    )

    alloc = np.asarray(result["allocation_vector"], dtype=float)
    amounts = loans["loan_amnt"].to_numpy(dtype=float)
    assert result["solver_status"] == "optimal"
    assert np.sum(alloc * amounts) <= 3500 + 1e-5
    assert _weighted(pd_high, alloc, amounts) <= 0.11 + 1e-7
    purposes = loans["purpose"].to_numpy()
    total = float(np.sum(alloc * amounts))
    for purpose in np.unique(purposes):
        exposure = float(np.sum(alloc[purposes == purpose] * amounts[purposes == purpose]))
        assert exposure <= 0.60 * total + 1e-5


def test_highs_sparse_matches_pyomo_highs_objective_on_toy_lp() -> None:
    loans, pd_point, pd_low, pd_high, lgd, int_rates = _toy_loans()
    kwargs = dict(
        loans=loans,
        pd_point=pd_point,
        pd_low=pd_low,
        pd_high=pd_high,
        lgd=lgd,
        int_rates=int_rates,
        total_budget=3500,
        max_concentration=0.60,
        max_portfolio_pd=0.11,
        robust=True,
        pd_constraint_override=pd_high,
    )

    sparse = optimize_portfolio_allocation(**kwargs, solver_backend="highs_sparse")
    pyomo = optimize_portfolio_allocation(**kwargs, solver_backend="highs_pyomo")

    assert sparse["objective_value"] == pytest.approx(pyomo["objective_value"], rel=1e-6)
    assert sparse["total_allocated"] == pytest.approx(pyomo["total_allocated"], rel=1e-6)


def test_highspy_matches_sparse_highs_objective_on_toy_lp() -> None:
    pytest.importorskip("highspy")
    loans, pd_point, pd_low, pd_high, lgd, int_rates = _toy_loans()
    kwargs = dict(
        loans=loans,
        pd_point=pd_point,
        pd_low=pd_low,
        pd_high=pd_high,
        lgd=lgd,
        int_rates=int_rates,
        total_budget=3500,
        max_concentration=0.60,
        max_portfolio_pd=0.11,
        robust=True,
        pd_constraint_override=pd_high,
    )

    native = optimize_portfolio_allocation(**kwargs, solver_backend="highspy")
    sparse = optimize_portfolio_allocation(**kwargs, solver_backend="highs_sparse")

    assert native["objective_value"] == pytest.approx(sparse["objective_value"], rel=1e-6)
    assert native["total_allocated"] == pytest.approx(sparse["total_allocated"], rel=1e-6)


def test_highspy_falls_back_to_sparse_highs_when_native_solver_fails(
    monkeypatch,
) -> None:
    pytest.importorskip("highspy")
    loans, pd_point, pd_low, pd_high, lgd, int_rates = _toy_loans()

    def fail_native(**_: object) -> dict[str, object]:
        raise RuntimeError("native warning")

    monkeypatch.setattr(portfolio_model, "solve_portfolio_highspy_native", fail_native)
    result = portfolio_model.optimize_portfolio_allocation(
        loans=loans,
        pd_point=pd_point,
        pd_low=pd_low,
        pd_high=pd_high,
        lgd=lgd,
        int_rates=int_rates,
        total_budget=3500,
        max_concentration=0.60,
        max_portfolio_pd=0.11,
        robust=True,
        pd_constraint_override=pd_high,
        solver_backend="highspy",
    )

    assert result["solver_backend"] == "highspy_fallback_highs_sparse"
    assert result["native_solver_error"] == "native warning"
