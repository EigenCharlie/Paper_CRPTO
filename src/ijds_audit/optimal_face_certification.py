"""Full-basis and conditional optimal-face diagnostics for IJDS point LPs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import highspy
import numpy as np
from scipy.sparse import csc_matrix, vstack

from src.ijds_audit.portfolio import PointPortfolioSession, PointPortfolioSolution

_STATUS_NAMES = {
    highspy.HighsBasisStatus.kLower: "lower",
    highspy.HighsBasisStatus.kBasic: "basic",
    highspy.HighsBasisStatus.kUpper: "upper",
    highspy.HighsBasisStatus.kZero: "zero",
    highspy.HighsBasisStatus.kNonbasic: "nonbasic",
}
_STATUS_CODES = {status: index for index, status in enumerate(_STATUS_NAMES)}


@dataclass(frozen=True)
class FullBasisAudit:
    """One complete basis summary plus auditable row and warning details."""

    summary: dict[str, Any]
    column_values: np.ndarray
    row_details: tuple[dict[str, Any], ...]
    flagged_nonbasic: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class SecondarySolve:
    """Raw, unmodified result of one fresh conditional face solve."""

    values: np.ndarray
    run_time_seconds: float
    maximum_column_bound_violation: float
    maximum_row_bound_violation: float


def basis_status_name(status: highspy.HighsBasisStatus) -> str:
    """Return a stable lowercase name for one HiGHS basis status."""
    try:
        return _STATUS_NAMES[status]
    except KeyError as exc:  # pragma: no cover - defensive against a future HiGHS enum
        raise ValueError(f"Unsupported HiGHS basis status: {status!r}.") from exc


def _basis_array_digest(
    statuses: np.ndarray,
    duals: np.ndarray,
    values: np.ndarray,
) -> str:
    codes = np.asarray([_STATUS_CODES[item] for item in statuses], dtype="<i2")
    payload = b"".join(
        (
            codes.tobytes(order="C"),
            np.asarray(duals, dtype="<f8").tobytes(order="C"),
            np.asarray(values, dtype="<f8").tobytes(order="C"),
        )
    )
    return hashlib.sha256(payload).hexdigest()


def _finite_min(values: np.ndarray) -> float:
    return float(values.min()) if values.size else float("nan")


def _row_names(session: PointPortfolioSession, supplied: tuple[str, ...] | None) -> tuple[str, ...]:
    rows = int(session.solver.getLp().num_row_)
    if supplied is not None:
        if len(supplied) != rows:
            raise ValueError(f"Expected {rows} row names, received {len(supplied)}.")
        return supplied
    return tuple(f"row_{index}" for index in range(rows))


def audit_full_basis(
    session: PointPortfolioSession,
    solution: PointPortfolioSolution,
    *,
    dual_absolute_tolerance: float,
    dual_relative_tolerance: float,
    primal_tolerance: float,
    column_names: tuple[str, ...] | None = None,
    row_names: tuple[str, ...] | None = None,
) -> FullBasisAudit:
    """Audit structural columns and row/slack variables in one optimal basis.

    ``col_dual`` is the structural-column reduced cost. HiGHS exposes the
    corresponding row/slack certificate as ``row_dual``. Equality rows are
    recorded but excluded from movable-slack warnings because they have no
    admissible slack direction.
    """
    dual_abs_tol = float(dual_absolute_tolerance)
    dual_rel_tol = float(dual_relative_tolerance)
    primal_tol = float(primal_tolerance)
    if dual_abs_tol <= 0.0 or dual_rel_tol < 0.0 or primal_tol <= 0.0:
        raise ValueError("Basis tolerances must be positive (relative dual may be zero).")

    raw = session.solver.getSolution()
    basis = session.solver.getBasis()
    lp = session.solver.getLp()
    if not bool(getattr(raw, "value_valid", True)) or not bool(getattr(raw, "dual_valid", True)):
        raise RuntimeError("HiGHS returned an invalid primal or dual solution.")
    col_values = np.asarray(raw.col_value, dtype=float)
    col_duals = np.asarray(raw.col_dual, dtype=float)
    col_costs = np.asarray(lp.col_cost_, dtype=float)
    col_lower = np.asarray(lp.col_lower_, dtype=float)
    col_upper = np.asarray(lp.col_upper_, dtype=float)
    col_status = np.asarray(basis.col_status, dtype=object)
    row_values = np.asarray(raw.row_value, dtype=float)
    row_duals = np.asarray(raw.row_dual, dtype=float)
    row_lower = np.asarray(lp.row_lower_, dtype=float)
    row_upper = np.asarray(lp.row_upper_, dtype=float)
    row_status = np.asarray(basis.row_status, dtype=object)

    n_columns = int(lp.num_col_)
    n_rows = int(lp.num_row_)
    expected_column_shape = (n_columns,)
    expected_row_shape = (n_rows,)
    for name, array, expected in (
        ("column values", col_values, expected_column_shape),
        ("column duals", col_duals, expected_column_shape),
        ("column costs", col_costs, expected_column_shape),
        ("column basis statuses", col_status, expected_column_shape),
        ("row values", row_values, expected_row_shape),
        ("row duals", row_duals, expected_row_shape),
        ("row basis statuses", row_status, expected_row_shape),
    ):
        if array.shape != expected:
            raise RuntimeError(f"HiGHS {name} have shape {array.shape}, expected {expected}.")
    if not bool(
        np.isfinite(col_values).all()
        and np.isfinite(col_duals).all()
        and np.isfinite(col_costs).all()
        and np.isfinite(row_values).all()
        and np.isfinite(row_duals).all()
    ):
        raise RuntimeError("HiGHS returned a non-finite basis value or dual.")

    names = (
        tuple(str(value) for value in column_names)
        if column_names is not None
        else tuple(f"column_{index}" for index in range(n_columns))
    )
    if len(names) != n_columns:
        raise ValueError(f"Expected {n_columns} column names, received {len(names)}.")
    resolved_row_names = _row_names(session, row_names)

    col_basic = col_status == highspy.HighsBasisStatus.kBasic
    col_lower_nonbasic = col_status == highspy.HighsBasisStatus.kLower
    col_upper_nonbasic = col_status == highspy.HighsBasisStatus.kUpper
    col_zero_nonbasic = col_status == highspy.HighsBasisStatus.kZero
    col_generic_nonbasic = col_status == highspy.HighsBasisStatus.kNonbasic
    col_supported_nonbasic = col_lower_nonbasic | col_upper_nonbasic
    col_nonbasic = ~col_basic
    col_unsupported = col_nonbasic & ~col_supported_nonbasic
    objective_reference = float(np.abs(col_costs).max(initial=0.0))
    if objective_reference <= 0.0:
        raise RuntimeError("Cannot define the registered objective dual scale.")
    # Structural reduced costs share the objective units of c. The infinity
    # norm is a common, predeclared reference for all columns and scales
    # exactly with a change in objective units.
    col_dual_scale = np.full(n_columns, objective_reference, dtype=float)
    col_dual_threshold = (dual_abs_tol + dual_rel_tol) * col_dual_scale
    col_abs_dual = np.abs(col_duals[col_nonbasic])
    col_scaled_dual = col_abs_dual / col_dual_scale[col_nonbasic]
    col_near_zero = col_nonbasic & (np.abs(col_duals) <= col_dual_threshold)
    col_lower_violation = float(np.maximum(col_duals[col_lower_nonbasic], 0.0).max(initial=0.0))
    col_upper_violation = float(np.maximum(-col_duals[col_upper_nonbasic], 0.0).max(initial=0.0))

    row_basic = row_status == highspy.HighsBasisStatus.kBasic
    row_lower_nonbasic = row_status == highspy.HighsBasisStatus.kLower
    row_upper_nonbasic = row_status == highspy.HighsBasisStatus.kUpper
    row_zero_nonbasic = row_status == highspy.HighsBasisStatus.kZero
    row_generic_nonbasic = row_status == highspy.HighsBasisStatus.kNonbasic
    row_nonbasic = ~row_basic
    row_equality = (
        np.isfinite(row_lower)
        & np.isfinite(row_upper)
        & (np.abs(row_upper - row_lower) <= primal_tol)
    )
    # Fixed equality rows (the budget row in the point LP) do not have a
    # movable slack direction. They remain fully recorded, but are excluded
    # from reduced-cost warnings and one-sided row-dual sign checks.
    row_movable_nonbasic = row_nonbasic & ~row_equality
    row_supported_nonbasic = row_lower_nonbasic | row_upper_nonbasic
    row_unsupported = row_movable_nonbasic & ~row_supported_nonbasic
    row_matrix = _matrix_from_lp(lp)
    row_coefficient_max = np.asarray(np.abs(row_matrix).max(axis=1).toarray(), dtype=float).reshape(
        -1
    )
    if objective_reference <= 0.0 or bool(np.any(row_coefficient_max <= 0.0)):
        raise RuntimeError("Cannot define the registered row/slack dual scale.")
    # A row marginal has objective-units per row-activity unit. Dividing the
    # maximum objective coefficient by the maximum coefficient in each row
    # gives a predeclared, LP-derived reference with the same units. Both the
    # marginal and this scale multiply identically when the objective is
    # rescaled, so the row warning is invariant to objective units.
    row_dual_scale = objective_reference / row_coefficient_max
    row_dual_threshold = (dual_abs_tol + dual_rel_tol) * row_dual_scale
    row_abs_dual = np.abs(row_duals[row_movable_nonbasic])
    row_scaled_dual = row_abs_dual / row_dual_scale[row_movable_nonbasic]
    row_near_zero = row_movable_nonbasic & (np.abs(row_duals) <= row_dual_threshold)
    basis_dimension_valid = int(col_basic.sum() + row_basic.sum()) == n_rows

    # For a maximization LP, HiGHS reports nonnegative row marginals at an
    # active upper row and nonpositive marginals at an active lower row.
    row_lower_movable = row_lower_nonbasic & ~row_equality
    row_upper_movable = row_upper_nonbasic & ~row_equality
    row_lower_violation = float(np.maximum(row_duals[row_lower_movable], 0.0).max(initial=0.0))
    row_upper_violation = float(np.maximum(-row_duals[row_upper_movable], 0.0).max(initial=0.0))
    col_lower_scaled_violation = float(
        (np.maximum(col_duals[col_lower_nonbasic], 0.0) / col_dual_scale[col_lower_nonbasic]).max(
            initial=0.0
        )
    )
    col_upper_scaled_violation = float(
        (np.maximum(-col_duals[col_upper_nonbasic], 0.0) / col_dual_scale[col_upper_nonbasic]).max(
            initial=0.0
        )
    )
    row_lower_scaled_violation = float(
        (np.maximum(row_duals[row_lower_movable], 0.0) / row_dual_scale[row_lower_movable]).max(
            initial=0.0
        )
    )
    row_upper_scaled_violation = float(
        (np.maximum(-row_duals[row_upper_movable], 0.0) / row_dual_scale[row_upper_movable]).max(
            initial=0.0
        )
    )

    col_lower_primal_violation = np.where(
        np.isfinite(col_lower), np.maximum(col_lower - col_values, 0.0), 0.0
    )
    col_upper_primal_violation = np.where(
        np.isfinite(col_upper), np.maximum(col_values - col_upper, 0.0), 0.0
    )
    row_lower_primal_violation = np.where(
        np.isfinite(row_lower), np.maximum(row_lower - row_values, 0.0), 0.0
    )
    row_upper_primal_violation = np.where(
        np.isfinite(row_upper), np.maximum(row_values - row_upper, 0.0), 0.0
    )

    col_degenerate = col_basic & (
        (np.abs(col_values - col_lower) <= primal_tol)
        | (np.abs(col_upper - col_values) <= primal_tol)
    )
    lower_distance = np.where(np.isfinite(row_lower), np.abs(row_values - row_lower), np.inf)
    upper_distance = np.where(np.isfinite(row_upper), np.abs(row_upper - row_values), np.inf)
    row_degenerate = (
        row_basic & ~row_equality & (np.minimum(lower_distance, upper_distance) <= primal_tol)
    )

    flagged: list[dict[str, Any]] = []
    for index in np.flatnonzero(col_near_zero):
        flagged.append(
            {
                "variable_kind": "column",
                "variable_index": int(index),
                "variable_name": names[int(index)],
                "basis_status": basis_status_name(col_status[index]),
                "base_value": float(col_values[index]),
                "lower_bound": float(col_lower[index]),
                "upper_bound": float(col_upper[index]),
                "dual_or_reduced_cost": float(col_duals[index]),
                "absolute_dual_or_reduced_cost": float(abs(col_duals[index])),
                "scaled_absolute_dual_or_reduced_cost": float(
                    abs(col_duals[index]) / col_dual_scale[index]
                ),
                "dual_reference_scale": float(col_dual_scale[index]),
                "near_zero_threshold": float(col_dual_threshold[index]),
                "objective_cost": float(col_costs[index]),
            }
        )
    for index in np.flatnonzero(row_near_zero):
        flagged.append(
            {
                "variable_kind": "row_activity",
                "variable_index": int(index),
                "variable_name": resolved_row_names[int(index)],
                "basis_status": basis_status_name(row_status[index]),
                "base_value": float(row_values[index]),
                "lower_bound": float(row_lower[index]),
                "upper_bound": float(row_upper[index]),
                "dual_or_reduced_cost": float(row_duals[index]),
                "absolute_dual_or_reduced_cost": float(abs(row_duals[index])),
                "scaled_absolute_dual_or_reduced_cost": float(
                    abs(row_duals[index]) / row_dual_scale[index]
                ),
                "dual_reference_scale": float(row_dual_scale[index]),
                "near_zero_threshold": float(row_dual_threshold[index]),
                "objective_cost": 0.0,
            }
        )

    row_details = tuple(
        {
            "row_index": int(index),
            "row_name": resolved_row_names[index],
            "basis_status": basis_status_name(row_status[index]),
            "row_value": float(row_values[index]),
            "row_lower": float(row_lower[index]),
            "row_upper": float(row_upper[index]),
            "row_dual": float(row_duals[index]),
            "absolute_row_dual": float(abs(row_duals[index])),
            "row_dual_reference_scale": float(row_dual_scale[index]),
            "row_near_zero_threshold": float(row_dual_threshold[index]),
            "is_equality": bool(row_equality[index]),
            "is_nonbasic": bool(row_nonbasic[index]),
            "is_movable_nonbasic": bool(row_movable_nonbasic[index]),
            "is_near_zero_nonbasic": bool(row_near_zero[index]),
            "lower_bound_violation": float(row_lower_primal_violation[index]),
            "upper_bound_violation": float(row_upper_primal_violation[index]),
        }
        for index in range(n_rows)
    )

    reconciled_objective = float(session.amount @ (col_values * session.objective))
    raw_solver_objective = float(session.solver.getObjectiveValue())
    raw_linear_objective = float(col_costs @ col_values)
    summary = {
        "basis_valid": bool(basis.valid),
        "basis_dimension_valid": bool(basis_dimension_valid),
        "value_valid": bool(getattr(raw, "value_valid", True)),
        "dual_valid": bool(getattr(raw, "dual_valid", True)),
        "columns": n_columns,
        "rows": n_rows,
        "basic_columns": int(col_basic.sum()),
        "lower_nonbasic_columns": int(col_lower_nonbasic.sum()),
        "upper_nonbasic_columns": int(col_upper_nonbasic.sum()),
        "zero_nonbasic_columns": int(col_zero_nonbasic.sum()),
        "generic_nonbasic_columns": int(col_generic_nonbasic.sum()),
        "unsupported_nonbasic_columns": int(col_unsupported.sum()),
        "minimum_absolute_nonbasic_column_reduced_cost": _finite_min(col_abs_dual),
        "minimum_scaled_nonbasic_column_reduced_cost": _finite_min(col_scaled_dual),
        "maximum_absolute_nonbasic_column_reduced_cost": float(col_abs_dual.max(initial=0.0)),
        "maximum_scaled_nonbasic_column_reduced_cost": float(col_scaled_dual.max(initial=0.0)),
        "near_zero_nonbasic_columns": int(col_near_zero.sum()),
        "basic_rows": int(row_basic.sum()),
        "lower_nonbasic_rows": int(row_lower_nonbasic.sum()),
        "upper_nonbasic_rows": int(row_upper_nonbasic.sum()),
        "zero_nonbasic_rows": int(row_zero_nonbasic.sum()),
        "generic_nonbasic_rows": int(row_generic_nonbasic.sum()),
        "equality_rows": int(row_equality.sum()),
        "movable_nonbasic_rows": int(row_movable_nonbasic.sum()),
        "unsupported_movable_nonbasic_rows": int(row_unsupported.sum()),
        "minimum_absolute_nonbasic_row_dual": _finite_min(row_abs_dual),
        "minimum_scaled_nonbasic_row_dual": _finite_min(row_scaled_dual),
        "near_zero_nonbasic_rows": int(row_near_zero.sum()),
        "near_zero_nonbasic_total": int(col_near_zero.sum() + row_near_zero.sum()),
        "primal_degenerate_basic_columns": int(col_degenerate.sum()),
        "primal_degenerate_basic_rows": int(row_degenerate.sum()),
        "basis_primal_degenerate": bool(col_degenerate.any() or row_degenerate.any()),
        "maximum_column_dual_sign_violation": max(col_lower_violation, col_upper_violation),
        "maximum_row_dual_sign_violation": max(row_lower_violation, row_upper_violation),
        "maximum_dual_sign_violation": max(
            col_lower_violation,
            col_upper_violation,
            row_lower_violation,
            row_upper_violation,
        ),
        "maximum_scaled_column_dual_sign_violation": max(
            col_lower_scaled_violation, col_upper_scaled_violation
        ),
        "maximum_scaled_row_dual_sign_violation": max(
            row_lower_scaled_violation, row_upper_scaled_violation
        ),
        "maximum_scaled_dual_sign_violation": max(
            col_lower_scaled_violation,
            col_upper_scaled_violation,
            row_lower_scaled_violation,
            row_upper_scaled_violation,
        ),
        "maximum_column_bound_violation": float(
            max(
                col_lower_primal_violation.max(initial=0.0),
                col_upper_primal_violation.max(initial=0.0),
            )
        ),
        "maximum_row_bound_violation": float(
            max(
                row_lower_primal_violation.max(initial=0.0),
                row_upper_primal_violation.max(initial=0.0),
            )
        ),
        "maximum_primal_bound_violation": float(
            max(
                col_lower_primal_violation.max(initial=0.0),
                col_upper_primal_violation.max(initial=0.0),
                row_lower_primal_violation.max(initial=0.0),
                row_upper_primal_violation.max(initial=0.0),
            )
        ),
        "raw_solver_objective": raw_solver_objective,
        "raw_linear_objective": raw_linear_objective,
        "raw_objective_internal_reconciliation_error": float(
            raw_linear_objective - raw_solver_objective
        ),
        "objective_reconciliation_error": float(reconciled_objective - solution.objective_value),
        "solution_to_raw_solver_objective_error": float(
            solution.objective_value - raw_solver_objective
        ),
        "column_basis_state_sha256": _basis_array_digest(col_status, col_duals, col_values),
        "row_basis_state_sha256": _basis_array_digest(row_status, row_duals, row_values),
    }
    return FullBasisAudit(
        summary=summary,
        column_values=col_values.copy(),
        row_details=row_details,
        flagged_nonbasic=tuple(flagged),
    )


def breakpoint_probe_plan(breakpoints: np.ndarray) -> tuple[dict[str, float | str], ...]:
    """Return one registered midpoint seed from every available V1-breakpoint side."""
    values = np.asarray(breakpoints, dtype=float)
    if values.ndim != 1 or values.size < 2 or not bool(np.isfinite(values).all()):
        raise ValueError("At least two finite basis breakpoints are required.")
    ordered = np.unique(values)
    if ordered.size != values.size:
        raise ValueError("Basis breakpoints must be unique within a period.")
    rows: list[dict[str, float | str]] = []
    for index, cap in enumerate(ordered):
        if index > 0:
            rows.append(
                {
                    "point_cap": float(cap),
                    "probe_side": "left",
                    "seed_cap": float((ordered[index - 1] + cap) / 2.0),
                }
            )
        if index + 1 < ordered.size:
            rows.append(
                {
                    "point_cap": float(cap),
                    "probe_side": "right",
                    "seed_cap": float((cap + ordered[index + 1]) / 2.0),
                }
            )
    return tuple(rows)


def normalized_exposure_distance(left: np.ndarray, right: np.ndarray) -> float:
    """Return symmetric L1 exposure distance normalized by committed capital."""
    first = np.asarray(left, dtype=float)
    second = np.asarray(right, dtype=float)
    if first.shape != second.shape or first.ndim != 1:
        raise ValueError("Exposure vectors must be aligned one-dimensional arrays.")
    denominator = float(first.sum() + second.sum())
    if denominator <= 0.0:
        raise ValueError("Exposure distance requires positive committed capital.")
    return float(np.abs(first - second).sum() / denominator)


def _matrix_from_lp(lp: highspy.HighsLp) -> csc_matrix:
    matrix = lp.a_matrix_
    if matrix.format_ != highspy.MatrixFormat.kColwise:
        raise RuntimeError("Optimal-face certification requires a column-wise HiGHS matrix.")
    return csc_matrix(
        (
            np.asarray(matrix.value_, dtype=float),
            np.asarray(matrix.index_, dtype=np.int32),
            np.asarray(matrix.start_, dtype=np.int32),
        ),
        shape=(int(lp.num_row_), int(lp.num_col_)),
    )


def _secondary_lp(
    base: highspy.HighsLp,
    *,
    primary_cost: np.ndarray,
    target_cost: np.ndarray,
    face_lower: float,
    face_upper: float,
) -> highspy.HighsLp:
    matrix = _matrix_from_lp(base)
    augmented = vstack((matrix, csc_matrix(primary_cost.reshape(1, -1))), format="csc")
    lp = highspy.HighsLp()
    lp.num_col_ = int(base.num_col_)
    lp.num_row_ = int(base.num_row_) + 1
    lp.col_cost_ = np.asarray(target_cost, dtype=float).tolist()
    lp.col_lower_ = list(base.col_lower_)
    lp.col_upper_ = list(base.col_upper_)
    lp.row_lower_ = [*base.row_lower_, float(face_lower)]
    lp.row_upper_ = [*base.row_upper_, float(face_upper)]
    lp.sense_ = highspy.ObjSense.kMaximize
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.num_col_ = int(base.num_col_)
    lp.a_matrix_.num_row_ = int(base.num_row_) + 1
    lp.a_matrix_.start_ = augmented.indptr.astype(np.int32).tolist()
    lp.a_matrix_.index_ = augmented.indices.astype(np.int32).tolist()
    lp.a_matrix_.value_ = augmented.data.astype(float).tolist()
    return lp


def _set_secondary_option(solver: highspy.Highs, option: str, expected: str | int | float) -> None:
    """Set and verify every registered secondary-solver option."""
    if solver.setOptionValue(option, expected) != highspy.HighsStatus.kOk:
        raise RuntimeError(f"HiGHS rejected secondary option {option}.")
    result = solver.getOptionValue(option)
    if not isinstance(result, tuple) or len(result) != 2:
        raise RuntimeError(f"HiGHS did not expose secondary option {option}.")
    status, actual = result
    matches = (
        str(actual) == expected if isinstance(expected, str) else float(actual) == float(expected)
    )
    if status != highspy.HighsStatus.kOk or not matches:
        raise RuntimeError(f"HiGHS effective secondary option drifted: {option}={actual!r}.")


def _solve_secondary(
    lp: highspy.HighsLp,
    *,
    time_limit: int,
    threads: int,
    dual_feasibility_tolerance: float,
    primal_feasibility_tolerance: float,
) -> SecondarySolve:
    solver = highspy.Highs()
    if hasattr(solver, "resetGlobalScheduler"):
        solver.resetGlobalScheduler(True)
    if hasattr(solver, "zeroAllClocks"):
        solver.zeroAllClocks()
    solver.setOptionValue("output_flag", False)
    solver.setOptionValue("log_to_console", False)
    for option, value in (
        ("solver", "simplex"),
        ("presolve", "on"),
        ("time_limit", float(time_limit)),
        ("threads", max(1, int(threads))),
        ("dual_feasibility_tolerance", float(dual_feasibility_tolerance)),
        ("primal_feasibility_tolerance", float(primal_feasibility_tolerance)),
    ):
        _set_secondary_option(solver, option, value)
    if solver.passModel(lp) != highspy.HighsStatus.kOk:
        raise RuntimeError("HiGHS rejected an optimal-face secondary LP.")
    if solver.run() == highspy.HighsStatus.kError:
        raise RuntimeError("HiGHS failed while solving an optimal-face secondary LP.")
    status = solver.modelStatusToString(solver.getModelStatus())
    if "Optimal" not in str(status):
        raise RuntimeError(f"Optimal-face secondary LP is not optimal: {status}.")
    raw = solver.getSolution()
    if not bool(getattr(raw, "value_valid", False)):
        raise RuntimeError("Optimal-face secondary LP returned invalid primal values.")
    values = np.asarray(raw.col_value, dtype=float)
    if values.shape != (int(lp.num_col_),) or not bool(np.isfinite(values).all()):
        raise RuntimeError("Optimal-face secondary LP returned invalid column values.")
    col_lower = np.asarray(lp.col_lower_, dtype=float)
    col_upper = np.asarray(lp.col_upper_, dtype=float)
    col_lower_violation = np.where(np.isfinite(col_lower), np.maximum(col_lower - values, 0.0), 0.0)
    col_upper_violation = np.where(np.isfinite(col_upper), np.maximum(values - col_upper, 0.0), 0.0)
    row_values = _matrix_from_lp(lp) @ values
    row_lower = np.asarray(lp.row_lower_, dtype=float)
    row_upper = np.asarray(lp.row_upper_, dtype=float)
    row_lower_violation = np.where(
        np.isfinite(row_lower), np.maximum(row_lower - row_values, 0.0), 0.0
    )
    row_upper_violation = np.where(
        np.isfinite(row_upper), np.maximum(row_values - row_upper, 0.0), 0.0
    )
    maximum_column_violation = float(
        max(
            col_lower_violation.max(initial=0.0),
            col_upper_violation.max(initial=0.0),
        )
    )
    maximum_row_violation = float(
        max(
            row_lower_violation.max(initial=0.0),
            row_upper_violation.max(initial=0.0),
        )
    )
    return SecondarySolve(
        values=values,
        run_time_seconds=float(solver.getRunTime()),
        maximum_column_bound_violation=maximum_column_violation,
        maximum_row_bound_violation=maximum_row_violation,
    )


def optimal_face_range(
    session: PointPortfolioSession,
    solution: PointPortfolioSolution,
    *,
    variable_kind: str,
    variable_index: int,
    objective_absolute_tolerance: float,
    objective_relative_tolerance: float,
    time_limit: int,
    threads: int,
    dual_feasibility_tolerance: float,
    primal_feasibility_tolerance: float,
) -> dict[str, Any]:
    """Minimize and maximize one warned standard variable on the primary face."""
    base = session.solver.getLp()
    primary_cost = np.asarray(base.col_cost_, dtype=float)
    matrix = _matrix_from_lp(base)
    primary_raw = session.solver.getSolution()
    if not bool(getattr(primary_raw, "value_valid", False)):
        raise RuntimeError("Primary face solve has invalid raw values.")
    primary_values = np.asarray(primary_raw.col_value, dtype=float)
    if primary_values.shape != (int(base.num_col_),) or not bool(np.isfinite(primary_values).all()):
        raise RuntimeError("Primary face solve has nonfinite or misaligned raw values.")
    index = int(variable_index)
    if variable_kind == "column":
        if not 0 <= index < int(base.num_col_):
            raise IndexError(index)
        target = np.zeros(int(base.num_col_), dtype=float)
        target[index] = 1.0
        base_target_value = float(primary_values[index])
    elif variable_kind == "row_activity":
        if not 0 <= index < int(base.num_row_):
            raise IndexError(index)
        target = matrix.getrow(index).toarray().reshape(-1).astype(float)
        base_target_value = float(primary_raw.row_value[index])
    else:
        raise ValueError(f"Unsupported optimal-face target kind: {variable_kind}.")

    objective_offset = float(getattr(base, "offset_", 0.0))
    z_star = float(session.solver.getObjectiveValue())
    epsilon = max(
        float(objective_absolute_tolerance),
        float(objective_relative_tolerance) * max(1.0, abs(z_star)),
    )
    if epsilon <= 0.0:
        raise ValueError("Optimal-face objective tolerance must be positive.")
    raw_internal_objective = float(primary_cost @ primary_values + objective_offset)
    raw_internal_reconciliation = float(raw_internal_objective - z_star)
    solution_reconciliation = float(solution.objective_value - z_star)
    face_lower = z_star - epsilon - objective_offset
    face_upper = z_star + epsilon - objective_offset
    maximum_solve = _solve_secondary(
        _secondary_lp(
            base,
            primary_cost=primary_cost,
            target_cost=target,
            face_lower=face_lower,
            face_upper=face_upper,
        ),
        time_limit=time_limit,
        threads=threads,
        dual_feasibility_tolerance=dual_feasibility_tolerance,
        primal_feasibility_tolerance=primal_feasibility_tolerance,
    )
    minimum_solve = _solve_secondary(
        _secondary_lp(
            base,
            primary_cost=primary_cost,
            target_cost=-target,
            face_lower=face_lower,
            face_upper=face_upper,
        ),
        time_limit=time_limit,
        threads=threads,
        dual_feasibility_tolerance=dual_feasibility_tolerance,
        primal_feasibility_tolerance=primal_feasibility_tolerance,
    )
    maximum_values = maximum_solve.values
    minimum_values = minimum_solve.values
    minimum = float(target @ minimum_values)
    maximum = float(target @ maximum_values)
    raw_value_range = float(maximum - minimum)
    range_order_violation = float(max(-raw_value_range, 0.0))
    base_below_minimum_violation = float(max(minimum - base_target_value, 0.0))
    base_above_maximum_violation = float(max(base_target_value - maximum, 0.0))
    minimum_primary = float(primary_cost @ minimum_values + objective_offset)
    maximum_primary = float(primary_cost @ maximum_values + objective_offset)
    return {
        "variable_kind": variable_kind,
        "variable_index": index,
        "base_value": base_target_value,
        "minimum_value": minimum,
        "maximum_value": maximum,
        "raw_value_range": raw_value_range,
        "value_range": float(max(raw_value_range, 0.0)),
        "range_order_violation": range_order_violation,
        "base_below_minimum_violation": base_below_minimum_violation,
        "base_above_maximum_violation": base_above_maximum_violation,
        "maximum_range_consistency_violation": max(
            range_order_violation,
            base_below_minimum_violation,
            base_above_maximum_violation,
        ),
        "raw_primary_objective": z_star,
        "raw_internal_primary_objective": raw_internal_objective,
        "raw_internal_primary_objective_difference": raw_internal_reconciliation,
        "solution_to_raw_primary_objective_difference": solution_reconciliation,
        "objective_face_epsilon": epsilon,
        "minimum_primary_objective": minimum_primary,
        "maximum_primary_objective": maximum_primary,
        "minimum_primary_objective_difference": float(minimum_primary - z_star),
        "maximum_primary_objective_difference": float(maximum_primary - z_star),
        "minimum_solver_run_time_seconds": minimum_solve.run_time_seconds,
        "maximum_solver_run_time_seconds": maximum_solve.run_time_seconds,
        "minimum_maximum_column_bound_violation": (minimum_solve.maximum_column_bound_violation),
        "minimum_maximum_row_bound_violation": minimum_solve.maximum_row_bound_violation,
        "maximum_maximum_column_bound_violation": (maximum_solve.maximum_column_bound_violation),
        "maximum_maximum_row_bound_violation": maximum_solve.maximum_row_bound_violation,
    }
