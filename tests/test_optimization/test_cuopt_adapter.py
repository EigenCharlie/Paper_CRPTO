from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest

import src.optimization.cuopt_adapter as cuopt_adapter


class _FakeDataModel:
    def set_csr_constraint_matrix(
        self,
        data: np.ndarray,
        indices: np.ndarray,
        indptr: np.ndarray,
    ) -> None:
        self.data = data
        self.indices = indices
        self.indptr = indptr

    def set_constraint_bounds(self, bounds: np.ndarray) -> None:
        self.constraint_bounds = bounds

    def set_row_types(self, row_types: np.ndarray) -> None:
        self.row_types = row_types

    def set_objective_coefficients(self, objective: np.ndarray) -> None:
        self.objective = objective

    def set_maximize(self, maximize: bool) -> None:
        self.maximize = maximize

    def set_variable_lower_bounds(self, bounds: np.ndarray) -> None:
        self.variable_lower_bounds = bounds

    def set_variable_upper_bounds(self, bounds: np.ndarray) -> None:
        self.variable_upper_bounds = bounds


class _FakeSettings:
    def __init__(self) -> None:
        self.parameters: dict[str, Any] = {}

    def set_parameter(self, name: str, value: Any) -> None:
        self.parameters[name] = value


class _FakeSolution:
    def __init__(
        self,
        primal: np.ndarray,
        *,
        objective: float = 12.5,
        termination_reason: str = "Optimal",
    ) -> None:
        self._primal = primal
        self._objective = objective
        self._termination_reason = termination_reason

    def get_primal_solution(self) -> np.ndarray:
        return self._primal

    def get_primal_objective(self) -> float:
        return self._objective

    def get_termination_reason(self) -> str:
        return self._termination_reason


class _FakeLpApi:
    def __init__(self, solution: _FakeSolution) -> None:
        self.solution = solution
        self.data_model: _FakeDataModel | None = None
        self.settings: _FakeSettings | None = None

    def DataModel(self) -> _FakeDataModel:
        self.data_model = _FakeDataModel()
        return self.data_model

    def SolverSettings(self) -> _FakeSettings:
        self.settings = _FakeSettings()
        return self.settings

    def Solve(self, data_model: _FakeDataModel, settings: _FakeSettings) -> _FakeSolution:
        self.solved_data_model = data_model
        self.solved_settings = settings
        return self.solution


def test_cuopt_native_uses_shared_lp_components_and_solver_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    loans = pd.DataFrame(
        {
            "loan_amnt": [100.0, 200.0, 300.0],
            "purpose": ["debt", "home", "home"],
        }
    )
    fake_api = _FakeLpApi(_FakeSolution(np.array([0.50, 0.25, 0.00, 3.00])))
    monkeypatch.setattr(cuopt_adapter, "_require_cuopt", lambda: fake_api)

    result = cuopt_adapter.solve_portfolio_cuopt_native(
        loans=loans,
        pd_point=np.array([0.02, 0.04, 0.06]),
        pd_high=np.array([0.03, 0.05, 0.08]),
        lgd=np.array([0.45, 0.45, 0.45]),
        int_rates=np.array([0.12, 0.14, 0.16]),
        total_budget=1_000.0,
        max_concentration=0.75,
        max_portfolio_pd=0.10,
        robust=True,
        min_budget_utilization=0.20,
        pd_cap_slack_penalty=0.50,
        time_limit=15,
        random_seed=9,
        presolve=0,
        cuopt_parameters={
            "log_to_console": "true",
            "log_dir": str(tmp_path),
            "num_cpu_threads": "2",
        },
    )

    assert fake_api.data_model is not None
    assert fake_api.settings is not None
    assert fake_api.data_model.maximize is True
    assert fake_api.data_model.constraint_bounds[0] == pytest.approx(1_000.0)
    assert fake_api.data_model.variable_lower_bounds.tolist() == [0.0, 0.0, 0.0, 0.0]
    assert fake_api.data_model.variable_upper_bounds.tolist() == [1.0, 1.0, 1.0, 1_000.0]
    assert set(fake_api.data_model.row_types.tolist()) == {"L"}
    assert fake_api.settings.parameters["time_limit"] == 15
    assert fake_api.settings.parameters["random_seed"] == 9
    assert fake_api.settings.parameters["presolve"] == 0
    assert fake_api.settings.parameters["log_to_console"] is True
    assert fake_api.settings.parameters["num_cpu_threads"] == 2
    assert str(tmp_path) in str(fake_api.settings.parameters["log_file"])

    assert result["solver_backend"] == "cuopt"
    assert result["allocation"] == {0: 0.5, 1: 0.25, 2: 0.0}
    assert np.allclose(result["allocation_vector"], np.array([0.5, 0.25, 0.0]))
    assert result["total_allocated"] == pytest.approx(100.0)
    assert result["pd_cap_slack"] == pytest.approx(3.0)
    assert result["cuopt_log_file"] == fake_api.settings.parameters["log_file"]


def test_cuopt_native_rejects_non_feasible_termination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loans = pd.DataFrame({"loan_amnt": [100.0], "purpose": ["debt"]})
    fake_api = _FakeLpApi(_FakeSolution(np.array([0.0]), termination_reason="Infeasible"))
    monkeypatch.setattr(cuopt_adapter, "_require_cuopt", lambda: fake_api)

    with pytest.raises(RuntimeError, match="did not produce an acceptable solution"):
        cuopt_adapter.solve_portfolio_cuopt_native(
            loans=loans,
            pd_point=np.array([0.02]),
            pd_high=np.array([0.03]),
            lgd=np.array([0.45]),
            int_rates=np.array([0.12]),
        )
