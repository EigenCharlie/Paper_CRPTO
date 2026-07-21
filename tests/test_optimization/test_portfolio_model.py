from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import src.optimization.portfolio_model as portfolio_model
from src.optimization.portfolio_model import (
    optimize_portfolio_allocation,
    solution_allocation_vector,
)


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


def test_solution_allocation_vector_normalizes_dense_and_sparse_payloads() -> None:
    dense = solution_allocation_vector(
        {"allocation_vector": np.array([0.25, 0.0, 1.0])},
        3,
    )
    sparse = solution_allocation_vector({"allocation": {0: 0.25, 2: 1.0}}, 3)

    np.testing.assert_allclose(dense, [0.25, 0.0, 1.0])
    np.testing.assert_allclose(sparse, dense)


@pytest.mark.parametrize(
    ("solution", "n_items", "error", "match"),
    [
        ({"allocation_vector": [0.5, 0.5]}, 3, ValueError, "shape mismatch"),
        ({"allocation": {0: float("nan")}}, 1, ValueError, "non-finite"),
        ({}, 1, TypeError, "allocation_vector"),
        ({"allocation": {}}, -1, ValueError, "nonnegative"),
    ],
)
def test_solution_allocation_vector_rejects_invalid_payloads(
    solution: dict[str, object],
    n_items: int,
    error: type[Exception],
    match: str,
) -> None:
    with pytest.raises(error, match=match):
        solution_allocation_vector(solution, n_items)


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


def test_highs_sparse_supports_minimum_utilization_slack_and_unit_amounts() -> None:
    loans = pd.DataFrame({"purpose": ["a", "b", "c"]})
    pd_point = np.full(3, 0.20)
    pd_high = np.full(3, 0.30)
    result = optimize_portfolio_allocation(
        loans=loans,
        pd_point=pd_point,
        pd_low=np.full(3, 0.10),
        pd_high=pd_high,
        lgd=np.full(3, 0.45),
        int_rates=np.full(3, 0.50),
        total_budget=3.0,
        max_concentration=1.0,
        max_portfolio_pd=0.10,
        robust=True,
        min_budget_utilization=0.80,
        pd_cap_slack_penalty=0.01,
        solver_backend="highs_sparse",
    )

    assert float(result["total_allocated"]) >= 2.4 - 1e-7
    assert float(result["pd_cap_slack"]) > 0.0


@pytest.mark.parametrize(
    ("loans", "objective", "match"),
    [
        (pd.DataFrame(), np.array([]), "empty portfolio"),
        (pd.DataFrame({"loan_amnt": [1.0, 1.0]}), np.array([0.1]), "must align"),
        (
            pd.DataFrame({"loan_amnt": [1.0, 1.0]}),
            np.array([0.1, np.nan]),
            "finite values",
        ),
    ],
)
def test_portfolio_rejects_invalid_objective_inputs(
    loans: pd.DataFrame,
    objective: np.ndarray,
    match: str,
) -> None:
    n = len(loans)
    with pytest.raises(ValueError, match=match):
        optimize_portfolio_allocation(
            loans=loans,
            pd_point=np.full(n, 0.10),
            pd_low=np.full(n, 0.05),
            pd_high=np.full(n, 0.15),
            lgd=np.full(n, 0.45),
            int_rates=np.full(n, 0.20),
            objective_rate_override=objective,
            solver_backend="highs_sparse",
        )


def test_sparse_solver_surfaces_nonoptimal_status(monkeypatch: pytest.MonkeyPatch) -> None:
    loans, pd_point, pd_low, pd_high, lgd, int_rates = _toy_loans()
    failed = SimpleNamespace(success=False, x=None, status=2, message="infeasible")
    monkeypatch.setattr(portfolio_model, "linprog", lambda *args, **kwargs: failed)

    with pytest.raises(RuntimeError, match="status=2, message=infeasible"):
        optimize_portfolio_allocation(
            loans=loans,
            pd_point=pd_point,
            pd_low=pd_low,
            pd_high=pd_high,
            lgd=lgd,
            int_rates=int_rates,
            solver_backend="highs_sparse",
        )


def test_highspy_matches_sparse_highs_objective_on_toy_lp() -> None:
    pytest.importorskip("highspy")
    loans, pd_point, pd_low, pd_high, lgd, int_rates = _toy_loans()
    kwargs = {
        "loans": loans,
        "pd_point": pd_point,
        "pd_low": pd_low,
        "pd_high": pd_high,
        "lgd": lgd,
        "int_rates": int_rates,
        "total_budget": 3500,
        "max_concentration": 0.60,
        "max_portfolio_pd": 0.11,
        "robust": True,
        "pd_constraint_override": pd_high,
    }

    native = optimize_portfolio_allocation(**kwargs, solver_backend="highspy")
    sparse = optimize_portfolio_allocation(**kwargs, solver_backend="highs_sparse")

    assert native["objective_value"] == pytest.approx(sparse["objective_value"], rel=1e-6)
    assert native["total_allocated"] == pytest.approx(sparse["total_allocated"], rel=1e-6)


def test_explicit_objective_rate_override_matches_independent_reconciliation() -> None:
    loans, pd_point, pd_low, pd_high, lgd, int_rates = _toy_loans()
    coherent_rates = (1.0 - pd_point) * int_rates - pd_point * lgd
    result = optimize_portfolio_allocation(
        loans=loans,
        pd_point=pd_point,
        pd_low=pd_low,
        pd_high=pd_high,
        lgd=lgd,
        int_rates=int_rates,
        objective_rate_override=coherent_rates,
        total_budget=3500,
        max_concentration=0.60,
        max_portfolio_pd=0.11,
        robust=True,
        pd_constraint_override=pd_high,
        solver_backend="highspy",
    )

    allocation = np.asarray(result["allocation_vector"], dtype=float)
    exposure = allocation * loans["loan_amnt"].to_numpy(dtype=float)
    assert result["objective_value"] == pytest.approx(float(exposure @ coherent_rates))


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


def test_highspy_failure_is_not_hidden_when_fallback_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loans, pd_point, pd_low, pd_high, lgd, int_rates = _toy_loans()
    monkeypatch.setenv("HIGHS_NATIVE_FALLBACK_SCIPY", "0")
    monkeypatch.setattr(
        portfolio_model,
        "solve_portfolio_highspy_native",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("native failure")),
    )

    with pytest.raises(RuntimeError, match="native failure"):
        optimize_portfolio_allocation(
            loans=loans,
            pd_point=pd_point,
            pd_low=pd_low,
            pd_high=pd_high,
            lgd=lgd,
            int_rates=int_rates,
            solver_backend="highspy",
        )


def test_highspy_configuration_retries_threads_and_tolerates_optional_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeStatus:
        kOk = "ok"

    class FakeSolver:
        def __init__(self) -> None:
            self.options: list[str] = []
            self.resets = 0

        def resetGlobalScheduler(self, blocking: bool) -> None:
            assert blocking is True
            self.resets += 1

        def setOptionValue(self, name: str, value: object) -> str:
            self.options.append(name)
            if name == "threads" and self.options.count("threads") == 1:
                return "rejected"
            if name == "parallel":
                return "rejected"
            return "ok"

    solver = FakeSolver()
    monkeypatch.setenv("HIGHS_SIMPLEX_STRATEGY", "invalid")
    portfolio_model._configure_highspy_solver(
        SimpleNamespace(HighsStatus=FakeStatus),
        solver,
        time_limit=10,
        threads=2,
    )

    assert solver.options.count("threads") == 2
    assert solver.resets == 2


@pytest.mark.parametrize(
    ("failure", "match"),
    [
        ("pass_model", "failed to accept"),
        ("run", "failed while solving"),
        ("model_status", "did not solve.*Infeasible"),
        ("short_primal", "primal solution has length 0"),
    ],
)
def test_highspy_native_rejects_invalid_solver_outcomes(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    match: str,
) -> None:
    class FakeStatus:
        kOk = "ok"
        kError = "error"

    class FakeSolver:
        def passModel(self, model: object) -> str:
            assert model is not None
            return "rejected" if failure == "pass_model" else "ok"

        def run(self) -> str:
            return "error" if failure == "run" else "ok"

        def getModelStatus(self) -> str:
            return "status"

        def modelStatusToString(self, status: str) -> str:
            assert status == "status"
            return "Infeasible" if failure == "model_status" else "Optimal"

        def getSolution(self) -> SimpleNamespace:
            return SimpleNamespace(col_value=[])

    fake_highspy = SimpleNamespace(HighsStatus=FakeStatus, Highs=FakeSolver)
    monkeypatch.setitem(sys.modules, "highspy", fake_highspy)
    monkeypatch.setattr(portfolio_model, "_build_highspy_lp", lambda *_: object())
    monkeypatch.setattr(portfolio_model, "_configure_highspy_solver", lambda *_, **__: None)
    loans, pd_point, pd_low, pd_high, lgd, int_rates = _toy_loans()

    with pytest.raises(RuntimeError, match=match):
        portfolio_model.solve_portfolio_highspy_native(
            loans=loans,
            pd_point=pd_point,
            pd_low=pd_low,
            pd_high=pd_high,
            lgd=lgd,
            int_rates=int_rates,
        )


@pytest.mark.parametrize("backend", ["cuopt", "highs_pyomo", "pyomo_highs"])
def test_removed_compatibility_backends_fail_explicitly(backend: str) -> None:
    loans, pd_point, pd_low, pd_high, lgd, int_rates = _toy_loans()

    with pytest.raises(ValueError, match="Use 'highs', 'highs_sparse', or 'highspy'"):
        optimize_portfolio_allocation(
            loans=loans,
            pd_point=pd_point,
            pd_low=pd_low,
            pd_high=pd_high,
            lgd=lgd,
            int_rates=int_rates,
            solver_backend=backend,
        )
