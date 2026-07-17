"""Outcome-free score frontiers for the normalized-stringency challenger."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import highspy
import numpy as np
import pandas as pd
from scipy.sparse import csc_matrix


@dataclass(frozen=True)
class ScoreFrontierSolution:
    """Reconciled exact-budget solution on a score/objective frontier."""

    allocation_fraction: np.ndarray
    exposure: np.ndarray
    objective_value: float
    weighted_score: float
    total_allocated: float
    simplex_iterations: int


class ObjectiveFloorPortfolioSession:
    """Warm-started score optimization under a changing plug-in objective floor."""

    def __init__(
        self,
        frame: pd.DataFrame,
        *,
        score: Sequence[float] | np.ndarray,
        objective_rate: Sequence[float] | np.ndarray,
        budget: float,
        purpose_cap: float,
        sense: Literal["minimize", "maximize"] = "minimize",
        time_limit: int = 300,
        threads: int = 1,
    ) -> None:
        n = len(frame)
        if n == 0 or float(budget) <= 0.0:
            raise ValueError("The frontier requires candidates and a positive budget.")
        self.score = _validated_vector(score, name="score", n=n)
        self.objective = _validated_vector(objective_rate, name="objective_rate", n=n)
        if bool(np.any((self.score < 0.0) | (self.score > 1.0))):
            raise ValueError("score must lie in [0, 1].")
        if sense not in {"minimize", "maximize"}:
            raise ValueError("sense must be 'minimize' or 'maximize'.")
        self.budget = float(budget)
        lp, self.objective_floor_row, self.amount = _objective_floor_lp(
            frame,
            self.score,
            self.objective,
            budget=self.budget,
            purpose_cap=float(purpose_cap),
            sense=sense,
        )
        self.solver = highspy.Highs()
        if hasattr(self.solver, "resetGlobalScheduler"):
            self.solver.resetGlobalScheduler(True)
        self.solver.setOptionValue("output_flag", False)
        self.solver.setOptionValue("log_to_console", False)
        self.solver.setOptionValue("solver", "simplex")
        self.solver.setOptionValue("presolve", "on")
        self.solver.setOptionValue("time_limit", float(time_limit))
        self.solver.setOptionValue("threads", max(1, int(threads)))
        if self.solver.passModel(lp) != highspy.HighsStatus.kOk:
            raise RuntimeError("HiGHS rejected the objective-floor portfolio LP.")

    def solve(self, objective_floor: float | None = None) -> ScoreFrontierSolution:
        """Optimize score with an optional absolute plug-in objective floor."""
        lower = -highspy.kHighsInf if objective_floor is None else float(objective_floor)
        status = self.solver.changeRowBounds(
            int(self.objective_floor_row),
            lower,
            highspy.kHighsInf,
        )
        if status != highspy.HighsStatus.kOk:
            raise RuntimeError("HiGHS rejected the plug-in objective-floor update.")
        if self.solver.run() == highspy.HighsStatus.kError:
            raise RuntimeError("HiGHS failed while solving the objective-floor LP.")
        model_status = self.solver.modelStatusToString(self.solver.getModelStatus())
        if "Optimal" not in str(model_status):
            raise RuntimeError(f"Objective-floor LP is not optimal: {model_status}.")
        fraction = np.clip(
            np.asarray(self.solver.getSolution().col_value, dtype=float),
            0.0,
            1.0,
        )
        exposure = self.amount * fraction
        total = float(exposure.sum())
        if not np.isclose(total, self.budget, rtol=0.0, atol=1e-4):
            raise RuntimeError(f"Objective-floor LP did not fill its budget: {total}.")
        info = self.solver.getInfo()
        return ScoreFrontierSolution(
            allocation_fraction=fraction,
            exposure=exposure,
            objective_value=float(exposure @ self.objective),
            weighted_score=float(exposure @ self.score / total),
            total_allocated=total,
            simplex_iterations=int(getattr(info, "simplex_iteration_count", 0) or 0),
        )


def normalized_score_cap(
    *,
    minimum_score: float,
    score_at_objective: float,
    coordinate: float,
    minimum_range: float = 0.0,
) -> float:
    """Map a unit coordinate to one score's attainable decision range."""
    lower = float(minimum_score)
    upper = float(score_at_objective)
    value = float(coordinate)
    if not 0.0 <= value <= 1.0:
        raise ValueError("Normalized score coordinate must lie in [0, 1].")
    score_range = upper - lower
    if score_range < float(minimum_range):
        raise ValueError(
            f"Normalized score range {score_range:.12g} is below {minimum_range:.12g}."
        )
    return lower + value * score_range


def common_objective_target(
    *,
    minimum_objectives: Sequence[float] | np.ndarray,
    objective_optimum: float,
    coordinate: float,
    minimum_range: float = 0.0,
) -> tuple[float, float]:
    """Return the common lower endpoint and matched absolute objective target."""
    minima = np.asarray(minimum_objectives, dtype=float)
    if minima.ndim != 1 or len(minima) == 0 or not bool(np.isfinite(minima).all()):
        raise ValueError("minimum_objectives must be a nonempty finite vector.")
    value = float(coordinate)
    if not 0.0 <= value <= 1.0:
        raise ValueError("Objective coordinate must lie in [0, 1].")
    lower = float(minima.max())
    objective_range = float(objective_optimum) - lower
    if objective_range < float(minimum_range):
        raise ValueError(
            f"Common objective range {objective_range:.12g} is below {minimum_range:.12g}."
        )
    return lower, lower + value * objective_range


def normalized_exposure_distance(
    first: Sequence[float] | np.ndarray,
    second: Sequence[float] | np.ndarray,
    *,
    budget: float,
) -> float:
    """Return turnover-like L1 exposure distance normalized by twice the budget."""
    left = np.asarray(first, dtype=float)
    right = np.asarray(second, dtype=float)
    if left.shape != right.shape or left.ndim != 1:
        raise ValueError("Exposure vectors must be aligned one-dimensional arrays.")
    if float(budget) <= 0.0:
        raise ValueError("budget must be positive.")
    return float(np.abs(left - right).sum() / (2.0 * float(budget)))


def solve_glop_portfolio(
    frame: pd.DataFrame,
    *,
    score: Sequence[float] | np.ndarray,
    objective_rate: Sequence[float] | np.ndarray,
    budget: float,
    purpose_cap: float,
    mode: Literal["normalized_score", "objective_matched"],
    threshold: float,
) -> ScoreFrontierSolution:
    """Independently resolve one declared frontier cell with OR-Tools GLOP."""
    from ortools.linear_solver import pywraplp

    n = len(frame)
    amount = _validated_vector(frame["loan_amnt"], name="loan_amnt", n=n)
    score_array = _validated_vector(score, name="score", n=n)
    objective = _validated_vector(objective_rate, name="objective_rate", n=n)
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if solver is None:
        raise RuntimeError("OR-Tools GLOP is unavailable.")
    variables = [solver.NumVar(0.0, 1.0, f"x_{index}") for index in range(n)]
    solver.Add(solver.Sum(float(amount[index]) * variables[index] for index in range(n)) == budget)
    purposes = frame["purpose"].astype("string").fillna("unknown")
    for purpose in sorted(purposes.unique()):
        mask = purposes.eq(purpose).to_numpy(dtype=bool)
        solver.Add(
            solver.Sum(float(amount[index]) * variables[index] for index in np.flatnonzero(mask))
            <= float(purpose_cap) * float(budget)
        )
    if mode == "normalized_score":
        solver.Add(
            solver.Sum(
                float(amount[index] * score_array[index]) * variables[index] for index in range(n)
            )
            <= float(threshold) * float(budget)
        )
        solver.Maximize(
            solver.Sum(
                float(amount[index] * objective[index]) * variables[index] for index in range(n)
            )
        )
    elif mode == "objective_matched":
        solver.Add(
            solver.Sum(
                float(amount[index] * objective[index]) * variables[index] for index in range(n)
            )
            >= float(threshold)
        )
        solver.Minimize(
            solver.Sum(
                float(amount[index] * score_array[index]) * variables[index] for index in range(n)
            )
        )
    else:
        raise ValueError(f"Unknown frontier mode: {mode}.")
    status = solver.Solve()
    if status != pywraplp.Solver.OPTIMAL:
        raise RuntimeError(f"GLOP frontier solve is not optimal: status {status}.")
    fraction = np.asarray([variable.solution_value() for variable in variables], dtype=float)
    fraction = np.clip(fraction, 0.0, 1.0)
    exposure = amount * fraction
    total = float(exposure.sum())
    return ScoreFrontierSolution(
        allocation_fraction=fraction,
        exposure=exposure,
        objective_value=float(exposure @ objective),
        weighted_score=float(exposure @ score_array / total),
        total_allocated=total,
        simplex_iterations=int(solver.iterations()),
    )


def _validated_vector(
    values: Sequence[float] | np.ndarray,
    *,
    name: str,
    n: int,
) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.shape != (n,) or not bool(np.isfinite(array).all()):
        raise ValueError(f"{name} must be a finite vector with {n} rows.")
    return array


def _objective_floor_lp(
    frame: pd.DataFrame,
    score: np.ndarray,
    objective_rate: np.ndarray,
    *,
    budget: float,
    purpose_cap: float,
    sense: Literal["minimize", "maximize"],
) -> tuple[highspy.HighsLp, int, np.ndarray]:
    n = len(frame)
    amount = _validated_vector(frame["loan_amnt"], name="loan_amnt", n=n)
    if bool(np.any(amount <= 0.0)):
        raise ValueError("loan_amnt must be positive.")
    if not 0.0 < float(purpose_cap) <= 1.0:
        raise ValueError("purpose_cap must lie in (0, 1].")
    rows = [amount]
    lower = [float(budget)]
    upper = [float(budget)]
    objective_floor_row = len(rows)
    rows.append(amount * objective_rate)
    lower.append(-highspy.kHighsInf)
    upper.append(highspy.kHighsInf)
    purposes = frame["purpose"].astype("string").fillna("unknown")
    for purpose in sorted(purposes.unique()):
        rows.append(amount * purposes.eq(purpose).to_numpy(dtype=float))
        lower.append(-highspy.kHighsInf)
        upper.append(float(purpose_cap) * float(budget))
    matrix = csc_matrix(np.vstack(rows))
    lp = highspy.HighsLp()
    lp.num_col_ = n
    lp.num_row_ = len(rows)
    lp.col_cost_ = (amount * score).tolist()
    lp.col_lower_ = np.zeros(n).tolist()
    lp.col_upper_ = np.ones(n).tolist()
    lp.row_lower_ = lower
    lp.row_upper_ = upper
    lp.sense_ = highspy.ObjSense.kMinimize if sense == "minimize" else highspy.ObjSense.kMaximize
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.num_col_ = n
    lp.a_matrix_.num_row_ = len(rows)
    lp.a_matrix_.start_ = matrix.indptr.astype(np.int32).tolist()
    lp.a_matrix_.index_ = matrix.indices.astype(np.int32).tolist()
    lp.a_matrix_.value_ = matrix.data.astype(float).tolist()
    return lp, objective_floor_row, amount
