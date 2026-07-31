"""Finite diagnostics for score-order equivalence on a declared allocation span.

The mathematical result documented in the IJDS manuscript is exact.  This
module is only a numerical diagnostic for a finite collection of allocations:
passing it certifies the positive-affine relation on the span of the supplied
allocation differences, not on an unobserved feasible polytope.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True)
class ScoreOrderCertificate:
    """Numerical certificate on the affine span of supplied allocations."""

    equivalent_on_declared_span: bool
    estimated_positive_scale: float | None
    offset_at_reference: float | None
    affine_dimension: int
    ambient_dimension: int
    projected_source_norm: float
    projected_target_norm: float
    projected_relation_residual_norm: float
    maximum_declared_relation_error: float | None
    constant_budget: bool
    spans_full_budget_hull: bool


def _finite_vector(values: npt.ArrayLike, *, label: str) -> npt.NDArray[np.float64]:
    result = np.asarray(values, dtype=np.float64)
    if result.ndim != 1 or result.size == 0:
        raise ValueError(f"{label} must be a nonempty one-dimensional vector.")
    if not bool(np.isfinite(result).all()):
        raise ValueError(f"{label} must contain only finite values.")
    return result


def _finite_allocations(values: npt.ArrayLike) -> npt.NDArray[np.float64]:
    result = np.asarray(values, dtype=np.float64)
    if result.ndim != 2 or result.shape[0] == 0 or result.shape[1] == 0:
        raise ValueError("allocations must be a nonempty two-dimensional matrix.")
    if not bool(np.isfinite(result).all()):
        raise ValueError("allocations must contain only finite values.")
    return result


def certify_score_order_equivalence(
    allocations: npt.ArrayLike,
    source_score: npt.ArrayLike,
    target_score: npt.ArrayLike,
    *,
    absolute_tolerance: float = 1.0e-10,
    relative_tolerance: float = 1.0e-10,
    rank_tolerance: float | None = None,
    budget_tolerance: float = 1.0e-8,
) -> ScoreOrderCertificate:
    """Check a positive-affine score relation on a declared allocation span.

    Let ``D`` be the span of all differences among the supplied allocation
    rows.  The diagnostic passes exactly when the restrictions of the two
    score functionals to the numerically identified ``D`` are positive
    multiples, up to the declared tolerances.  If the rows span the complete
    exact-budget affine hull, this is the numerical counterpart of
    ``target = scale * source + constant * 1`` on that hull.
    """

    matrix = _finite_allocations(allocations)
    source = _finite_vector(source_score, label="source_score")
    target = _finite_vector(target_score, label="target_score")
    if source.shape != target.shape or source.size != matrix.shape[1]:
        raise ValueError("Scores and allocation columns must have matching dimensions.")
    for label, value in (
        ("absolute_tolerance", absolute_tolerance),
        ("relative_tolerance", relative_tolerance),
        ("budget_tolerance", budget_tolerance),
    ):
        if not np.isfinite(value) or value < 0.0:
            raise ValueError(f"{label} must be finite and nonnegative.")
    if rank_tolerance is not None and (not np.isfinite(rank_tolerance) or rank_tolerance < 0.0):
        raise ValueError("rank_tolerance must be finite and nonnegative when supplied.")

    reference = matrix[0]
    differences = matrix - reference
    _, singular_values, right_vectors = np.linalg.svd(differences, full_matrices=False)
    if singular_values.size == 0:
        numerical_rank = 0
    else:
        default_rank_tolerance = (
            max(differences.shape) * np.finfo(np.float64).eps * float(singular_values[0])
        )
        effective_rank_tolerance = (
            default_rank_tolerance if rank_tolerance is None else float(rank_tolerance)
        )
        numerical_rank = int(np.sum(singular_values > effective_rank_tolerance))

    basis = right_vectors[:numerical_rank]
    source_projection = basis @ source
    target_projection = basis @ target
    source_norm = float(np.linalg.norm(source_projection))
    target_norm = float(np.linalg.norm(target_projection))
    relation_tolerance = float(absolute_tolerance) + float(relative_tolerance) * max(
        1.0,
        source_norm,
        target_norm,
    )

    estimated_scale: float | None
    residual_norm: float
    equivalent: bool
    if source_norm <= relation_tolerance:
        estimated_scale = 1.0 if target_norm <= relation_tolerance else None
        residual_norm = target_norm
        equivalent = target_norm <= relation_tolerance
    else:
        estimated_scale = float(
            np.dot(source_projection, target_projection)
            / np.dot(source_projection, source_projection)
        )
        residual = target_projection - estimated_scale * source_projection
        residual_norm = float(np.linalg.norm(residual))
        equivalent = estimated_scale > 0.0 and residual_norm <= relation_tolerance

    offset: float | None = None
    maximum_error: float | None = None
    if equivalent and estimated_scale is not None:
        # This is the constant offset of the *portfolio score* on the supplied
        # affine span.  Under budget B and a unit-level intercept b it equals
        # b*B; it is a unit-level intercept only when B=1.
        offset = float(target @ reference - estimated_scale * (source @ reference))
        errors = matrix @ target - (estimated_scale * (matrix @ source) + offset)
        maximum_error = float(np.max(np.abs(errors)))
        pointwise_tolerance = float(absolute_tolerance) + float(relative_tolerance) * max(
            1.0,
            float(np.max(np.abs(matrix @ target))),
            float(np.max(np.abs(estimated_scale * (matrix @ source) + offset))),
        )
        if maximum_error > pointwise_tolerance:
            equivalent = False

    budgets = matrix.sum(axis=1)
    constant_budget = bool(
        np.max(np.abs(budgets - budgets[0]))
        <= float(budget_tolerance) + float(relative_tolerance) * max(1.0, abs(float(budgets[0])))
    )
    ambient_dimension = int(matrix.shape[1])
    return ScoreOrderCertificate(
        equivalent_on_declared_span=equivalent,
        estimated_positive_scale=estimated_scale if equivalent else None,
        offset_at_reference=offset if equivalent else None,
        affine_dimension=numerical_rank,
        ambient_dimension=ambient_dimension,
        projected_source_norm=source_norm,
        projected_target_norm=target_norm,
        projected_relation_residual_norm=residual_norm,
        maximum_declared_relation_error=maximum_error if equivalent else None,
        constant_budget=constant_budget,
        spans_full_budget_hull=constant_budget and numerical_rank == ambient_dimension - 1,
    )


def first_declared_order_disagreement(
    allocations: npt.ArrayLike,
    source_score: npt.ArrayLike,
    target_score: npt.ArrayLike,
    *,
    tolerance: float = 1.0e-10,
) -> tuple[int, int] | None:
    """Return the first supplied allocation pair with a different weak order."""

    matrix = _finite_allocations(allocations)
    source = _finite_vector(source_score, label="source_score")
    target = _finite_vector(target_score, label="target_score")
    if source.shape != target.shape or source.size != matrix.shape[1]:
        raise ValueError("Scores and allocation columns must have matching dimensions.")
    if not np.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("tolerance must be finite and nonnegative.")

    source_values = matrix @ source
    target_values = matrix @ target

    def relation(value: float) -> int:
        if value < -tolerance:
            return -1
        if value > tolerance:
            return 1
        return 0

    for left in range(matrix.shape[0]):
        for right in range(left + 1, matrix.shape[0]):
            if relation(float(source_values[left] - source_values[right])) != relation(
                float(target_values[left] - target_values[right])
            ):
                return left, right
    return None
