"""Exact-budget point-score LPs and comparator-frontier identities."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import highspy
import numpy as np
import pandas as pd
from scipy.sparse import csc_matrix


@dataclass(frozen=True)
class PointPortfolioSolution:
    """A reconciled solution of the exact-budget point-score LP."""

    allocation_fraction: np.ndarray
    exposure: np.ndarray
    objective_value: float
    weighted_point_score: float
    total_allocated: float
    basis_cap_lower: float
    basis_cap_upper: float
    simplex_iterations: int


class PointPortfolioSession:
    """A warm-started HiGHS model for repeated caps on one monthly menu."""

    def __init__(
        self,
        frame: pd.DataFrame,
        *,
        point_score: Sequence[float] | np.ndarray,
        objective_rate: Sequence[float] | np.ndarray,
        budget: float,
        purpose_cap: float,
        time_limit: int = 300,
        threads: int = 1,
    ) -> None:
        n = len(frame)
        if n == 0 or float(budget) <= 0.0:
            raise ValueError("The point portfolio requires candidates and a positive budget.")
        self.point = _validated_vector(point_score, name="point_score", n=n)
        self.objective = _validated_vector(objective_rate, name="objective_rate", n=n)
        if bool(np.any((self.point < 0.0) | (self.point > 1.0))):
            raise ValueError("point_score must lie in [0, 1].")
        if not 0.0 < float(purpose_cap) <= 1.0:
            raise ValueError("purpose_cap must lie in (0, 1].")
        self.budget = float(budget)
        lp, self.risk_row, self.amount = _point_lp(
            frame,
            self.point,
            self.objective,
            budget=self.budget,
            risk_cap=0.5,
            purpose_cap=float(purpose_cap),
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
            raise RuntimeError("HiGHS rejected the exact-budget point LP.")

    def solve(self, risk_cap: float) -> PointPortfolioSolution:
        """Change only the risk RHS and reoptimize from the current basis."""
        cap = float(risk_cap)
        if not 0.0 <= cap <= 1.0:
            raise ValueError("risk_cap must lie in [0, 1].")
        status = self.solver.changeRowBounds(
            int(self.risk_row),
            -highspy.kHighsInf,
            cap * self.budget,
        )
        if status != highspy.HighsStatus.kOk:
            raise RuntimeError("HiGHS rejected the point-risk RHS update.")
        if self.solver.run() == highspy.HighsStatus.kError:
            raise RuntimeError("HiGHS failed while solving the exact-budget point LP.")
        model_status = self.solver.modelStatusToString(self.solver.getModelStatus())
        if "Optimal" not in str(model_status):
            raise RuntimeError(f"Point LP is not optimal: {model_status}.")
        fraction = np.clip(np.asarray(self.solver.getSolution().col_value, dtype=float), 0.0, 1.0)
        exposure = self.amount * fraction
        total = float(exposure.sum())
        if not np.isclose(total, self.budget, rtol=0.0, atol=1e-4):
            raise RuntimeError(f"Point LP did not fill its budget: {total}.")
        objective_value = float(exposure @ self.objective)
        weighted_point = float(exposure @ self.point / total)
        ranging_status, ranging = self.solver.getRanging()
        if ranging_status != highspy.HighsStatus.kOk:
            raise RuntimeError("HiGHS did not return basis ranging information.")
        lower_rhs = float(ranging.row_bound_dn.value_[self.risk_row])
        upper_rhs = float(ranging.row_bound_up.value_[self.risk_row])
        info = self.solver.getInfo()
        return PointPortfolioSolution(
            allocation_fraction=fraction,
            exposure=exposure,
            objective_value=objective_value,
            weighted_point_score=weighted_point,
            total_allocated=total,
            basis_cap_lower=max(0.0, lower_rhs / self.budget),
            basis_cap_upper=min(1.0, upper_rhs / self.budget),
            simplex_iterations=int(getattr(info, "simplex_iteration_count", 0) or 0),
        )

    def basis_breakpoints(
        self,
        *,
        lower_cap: float,
        upper_cap: float,
        tolerance: float = 1e-10,
        max_bases: int = 10_000,
    ) -> tuple[float, ...]:
        """Enumerate basis-range endpoints over a closed cap interval."""
        lower = float(lower_cap)
        upper = float(upper_cap)
        if not 0.0 <= lower < upper <= 1.0:
            raise ValueError("Frontier cap support must be a nonempty subset of [0, 1].")
        caps = {lower, upper}
        probe = lower
        for _ in range(int(max_bases)):
            solution = self.solve(probe)
            basis_lower = float(np.clip(solution.basis_cap_lower, lower, upper))
            basis_upper = float(np.clip(solution.basis_cap_upper, lower, upper))
            caps.update((basis_lower, basis_upper))
            if basis_upper >= upper - tolerance:
                break
            if (
                basis_upper <= probe + tolerance
                and solution.weighted_point_score < probe - 0.5 * tolerance
            ):
                caps.add(upper)
                break
            next_probe = np.nextafter(basis_upper, np.inf)
            minimum_step = max(float(tolerance), 1e-12)
            if next_probe <= basis_upper + minimum_step:
                next_probe = basis_upper + minimum_step
            probe = min(next_probe, upper)
        else:
            raise RuntimeError(f"Frontier enumeration exceeded {max_bases} bases.")
        ordered = sorted(cap for cap in caps if lower - tolerance <= cap <= upper + tolerance)
        deduplicated: list[float] = []
        for cap in ordered:
            if not deduplicated or cap - deduplicated[-1] > tolerance:
                deduplicated.append(cap)
            elif abs(cap - upper) <= tolerance:
                deduplicated[-1] = upper
        deduplicated[0] = lower
        deduplicated[-1] = upper
        return tuple(deduplicated)


def _validated_vector(values: Sequence[float] | np.ndarray, *, name: str, n: int) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.shape != (n,) or not bool(np.isfinite(array).all()):
        raise ValueError(f"{name} must be a finite vector with {n} rows.")
    return array


def _point_lp(
    frame: pd.DataFrame,
    point_score: np.ndarray,
    objective_rate: np.ndarray,
    *,
    budget: float,
    risk_cap: float,
    purpose_cap: float,
) -> tuple[highspy.HighsLp, int, np.ndarray]:
    n = len(frame)
    amount = _validated_vector(frame["loan_amnt"], name="loan_amnt", n=n)
    if bool(np.any(amount <= 0.0)):
        raise ValueError("loan_amnt must be positive.")
    rows = [amount]
    lower = [float(budget)]
    upper = [float(budget)]
    risk_row = len(rows)
    rows.append(amount * point_score)
    lower.append(-highspy.kHighsInf)
    upper.append(float(risk_cap) * float(budget))
    purposes = frame["purpose"].astype("string").fillna("unknown")
    for purpose in sorted(purposes.unique()):
        rows.append(amount * purposes.eq(purpose).to_numpy(dtype=float))
        lower.append(-highspy.kHighsInf)
        upper.append(float(purpose_cap) * float(budget))
    matrix = csc_matrix(np.vstack(rows))
    lp = highspy.HighsLp()
    lp.num_col_ = n
    lp.num_row_ = len(rows)
    lp.col_cost_ = (amount * objective_rate).tolist()
    lp.col_lower_ = np.zeros(n).tolist()
    lp.col_upper_ = np.ones(n).tolist()
    lp.row_lower_ = lower
    lp.row_upper_ = upper
    lp.sense_ = highspy.ObjSense.kMaximize
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.num_col_ = n
    lp.a_matrix_.num_row_ = len(rows)
    lp.a_matrix_.start_ = matrix.indptr.astype(np.int32).tolist()
    lp.a_matrix_.index_ = matrix.indices.astype(np.int32).tolist()
    lp.a_matrix_.value_ = matrix.data.astype(float).tolist()
    return lp, risk_row, amount


def solve_point_portfolio(
    frame: pd.DataFrame,
    *,
    point_score: Sequence[float] | np.ndarray,
    objective_rate: Sequence[float] | np.ndarray,
    budget: float,
    risk_cap: float,
    purpose_cap: float,
    time_limit: int = 300,
    threads: int = 1,
) -> PointPortfolioSolution:
    """Solve the full-budget point LP and expose the current basis cap range."""
    session = PointPortfolioSession(
        frame,
        point_score=point_score,
        objective_rate=objective_rate,
        budget=float(budget),
        purpose_cap=float(purpose_cap),
        time_limit=time_limit,
        threads=threads,
    )
    return session.solve(float(risk_cap))


def enumerate_basis_breakpoints(
    frame: pd.DataFrame,
    *,
    point_score: Sequence[float] | np.ndarray,
    objective_rate: Sequence[float] | np.ndarray,
    budget: float,
    purpose_cap: float,
    lower_cap: float,
    upper_cap: float,
    tolerance: float = 1e-10,
    max_bases: int = 10_000,
    time_limit: int = 300,
    threads: int = 1,
) -> tuple[float, ...]:
    """Enumerate HiGHS basis-range endpoints over a closed cap interval."""
    session = PointPortfolioSession(
        frame,
        point_score=point_score,
        objective_rate=objective_rate,
        budget=budget,
        purpose_cap=purpose_cap,
        time_limit=time_limit,
        threads=threads,
    )
    return session.basis_breakpoints(
        lower_cap=lower_cap,
        upper_cap=upper_cap,
        tolerance=tolerance,
        max_bases=max_bases,
    )


def c2_cap(
    exposure: Sequence[float] | np.ndarray, point_score: Sequence[float] | np.ndarray
) -> float:
    """Return the funded point-score moment defining comparator C2."""
    funded = np.asarray(exposure, dtype=float)
    point = np.asarray(point_score, dtype=float)
    if funded.shape != point.shape or funded.ndim != 1:
        raise ValueError("C2 exposure and point-score vectors must align.")
    total = float(funded.sum())
    if total <= 0.0:
        raise ValueError("C2 requires positive funded exposure.")
    return float(funded @ point / total)


def verify_c2_dominance(
    *,
    guardrail_exposure: Sequence[float] | np.ndarray,
    point_solution: PointPortfolioSolution,
    point_score: Sequence[float] | np.ndarray,
    objective_rate: Sequence[float] | np.ndarray,
    tolerance: float = 1e-5,
) -> dict[str, float]:
    """Reconcile C2 feasibility and point-objective weak dominance."""
    guard = np.asarray(guardrail_exposure, dtype=float)
    point = np.asarray(point_score, dtype=float)
    objective = np.asarray(objective_rate, dtype=float)
    cap = c2_cap(guard, point)
    point_residual = float(point_solution.weighted_point_score - cap)
    guard_objective = float(guard @ objective)
    difference = float(point_solution.objective_value - guard_objective)
    if point_residual > 1e-10:
        raise RuntimeError(f"C2 point comparator exceeds its cap by {point_residual:.3e}.")
    if difference < -float(tolerance):
        raise RuntimeError(f"C2 objective dominance failed by {difference:.6f} dollars.")
    return {
        "c2_cap": cap,
        "c2_point_cap_residual": point_residual,
        "guardrail_objective": guard_objective,
        "point_objective": float(point_solution.objective_value),
        "point_minus_guardrail_objective": difference,
    }
