"""Outcome-free complete-hull diagnostics for downstream score equivalence.

The exact decision-invariance theorem is stated in
``docs/research/ijds_decision_invariance_theory_2026-07-30.md``.  This module
implements two finite numerical certificates used by the locked 2026-07-31
audit:

* a constructive certificate that the allocation polytope's affine hull is
  the complete fixed-budget hyperplane; and
* a direct positive-affine score certificate on that complete hyperplane.

Neither certificate solves an optimization problem or consumes outcomes.
Failure of score equivalence removes a global invariance guarantee; it is not
evidence that any particular optimizer output changes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True)
class CompleteBudgetHullCertificate:
    """Constructive relative-interior certificate for one monthly menu."""

    full_budget_hull_certified: bool
    ambient_dimension: int
    affine_dimension: int | None
    purpose_count: int
    budget: float
    purpose_cap: float
    total_loan_capacity: float
    total_strict_group_capacity: float
    witness_budget_residual: float | None
    minimum_witness_exposure: float | None
    minimum_loan_upper_slack: float | None
    minimum_purpose_cap_slack: float | None


@dataclass(frozen=True)
class FullBudgetScoreCertificate:
    """Positive-affine score certificate on a complete fixed-budget hull."""

    equivalent_on_complete_budget_hull: bool
    estimated_scale: float
    positive_scale: bool
    estimated_unit_intercept: float
    portfolio_score_offset: float
    ambient_dimension: int
    affine_dimension: int
    source_centered_norm: float
    target_centered_norm: float
    relation_residual_norm: float
    maximum_coordinate_relation_error: float
    relation_tolerance: float


def _finite_vector(values: npt.ArrayLike, *, label: str) -> npt.NDArray[np.float64]:
    result = np.asarray(values, dtype=np.float64)
    if result.ndim != 1 or result.size == 0:
        raise ValueError(f"{label} must be a nonempty one-dimensional vector.")
    if not bool(np.isfinite(result).all()):
        raise ValueError(f"{label} must contain only finite values.")
    return result


def _validated_tolerances(
    *,
    absolute_tolerance: float,
    relative_tolerance: float,
) -> tuple[float, float]:
    absolute = float(absolute_tolerance)
    relative = float(relative_tolerance)
    if not np.isfinite(absolute) or absolute < 0.0:
        raise ValueError("absolute_tolerance must be finite and nonnegative.")
    if not np.isfinite(relative) or relative < 0.0:
        raise ValueError("relative_tolerance must be finite and nonnegative.")
    return absolute, relative


def certify_complete_budget_hull(
    loan_amount: npt.ArrayLike,
    purpose: npt.ArrayLike,
    *,
    budget: float,
    purpose_cap: float,
    absolute_tolerance: float = 1.0e-8,
    relative_tolerance: float = 1.0e-12,
) -> CompleteBudgetHullCertificate:
    """Certify the full fixed-budget affine hull with a strict feasible point.

    The exposure polytope is

    ``0 <= x_i <= amount_i``, ``sum(x)=budget``, and
    ``sum_{i in purpose g}(x_i) <= purpose_cap * budget``.

    For each purpose, let ``U_g`` be its total loan capacity and
    ``W_g=min(U_g, purpose_cap*budget)``.  If ``sum_g W_g > budget``, setting
    purpose total ``y_g = budget*W_g/sum(W)`` and distributing ``y_g``
    proportionally to loan capacity gives one point strict in every
    inequality.  A relative-open neighbourhood of that point therefore spans
    every direction orthogonal to the budget vector, proving affine dimension
    ``n-1``.  The returned scalar margins make the construction auditable
    without persisting a loan-level witness.
    """

    amounts = _finite_vector(loan_amount, label="loan_amount")
    raw_purpose = np.asarray(purpose, dtype=object)
    if raw_purpose.ndim != 1 or raw_purpose.shape != amounts.shape:
        raise ValueError("purpose must be a one-dimensional vector aligned to loan_amount.")
    if bool(np.any(amounts <= 0.0)):
        raise ValueError("loan_amount must be strictly positive loan-wise.")
    if any(value is None for value in raw_purpose.tolist()):
        raise ValueError("purpose must not contain missing values.")
    purposes = np.asarray([str(value).strip() for value in raw_purpose], dtype=object)
    if bool(np.any(purposes == "")) or bool(np.any(purposes == "nan")):
        raise ValueError("purpose must contain nonempty, nonmissing labels.")

    fixed_budget = float(budget)
    cap = float(purpose_cap)
    if not np.isfinite(fixed_budget) or fixed_budget <= 0.0:
        raise ValueError("budget must be finite and strictly positive.")
    if not np.isfinite(cap) or not 0.0 < cap <= 1.0:
        raise ValueError("purpose_cap must be finite and lie in (0, 1].")
    absolute, relative = _validated_tolerances(
        absolute_tolerance=absolute_tolerance,
        relative_tolerance=relative_tolerance,
    )
    scale_tolerance = absolute + relative * max(1.0, fixed_budget, float(amounts.sum()))

    labels, inverse = np.unique(purposes.astype(str), return_inverse=True)
    group_capacity = np.bincount(inverse, weights=amounts, minlength=len(labels)).astype(float)
    cap_dollars = cap * fixed_budget
    strict_group_capacity = np.minimum(group_capacity, cap_dollars)
    total_strict_group_capacity = float(strict_group_capacity.sum())
    total_capacity = float(amounts.sum())

    if total_strict_group_capacity <= fixed_budget + scale_tolerance:
        return CompleteBudgetHullCertificate(
            full_budget_hull_certified=False,
            ambient_dimension=int(len(amounts)),
            affine_dimension=None,
            purpose_count=int(len(labels)),
            budget=fixed_budget,
            purpose_cap=cap,
            total_loan_capacity=total_capacity,
            total_strict_group_capacity=total_strict_group_capacity,
            witness_budget_residual=None,
            minimum_witness_exposure=None,
            minimum_loan_upper_slack=None,
            minimum_purpose_cap_slack=None,
        )

    group_total = fixed_budget * strict_group_capacity / total_strict_group_capacity
    witness = group_total[inverse] * amounts / group_capacity[inverse]
    purpose_totals = np.bincount(inverse, weights=witness, minlength=len(labels)).astype(float)
    budget_residual = float(abs(float(witness.sum()) - fixed_budget))
    minimum_exposure = float(np.min(witness))
    minimum_upper_slack = float(np.min(amounts - witness))
    minimum_purpose_slack = float(np.min(cap_dollars - purpose_totals))

    certified = bool(
        budget_residual <= scale_tolerance
        and minimum_exposure > scale_tolerance
        and minimum_upper_slack > scale_tolerance
        and minimum_purpose_slack > scale_tolerance
    )
    return CompleteBudgetHullCertificate(
        full_budget_hull_certified=certified,
        ambient_dimension=int(len(amounts)),
        affine_dimension=int(len(amounts) - 1) if certified else None,
        purpose_count=int(len(labels)),
        budget=fixed_budget,
        purpose_cap=cap,
        total_loan_capacity=total_capacity,
        total_strict_group_capacity=total_strict_group_capacity,
        witness_budget_residual=budget_residual,
        minimum_witness_exposure=minimum_exposure,
        minimum_loan_upper_slack=minimum_upper_slack,
        minimum_purpose_cap_slack=minimum_purpose_slack,
    )


def certify_full_budget_score_equivalence(
    source_score: npt.ArrayLike,
    target_score: npt.ArrayLike,
    *,
    budget: float,
    absolute_tolerance: float = 1.0e-12,
    relative_tolerance: float = 1.0e-10,
) -> FullBudgetScoreCertificate:
    """Check ``target = kappa*source + b*1`` with ``kappa > 0``.

    This direct centered-vector calculation is the complete-hull counterpart
    of :func:`certify_score_order_equivalence`.  It avoids an infeasible
    ``n``-vertex allocation matrix when a separate constructive certificate
    has already established that the affine hull is the full-budget
    hyperplane.
    """

    source = _finite_vector(source_score, label="source_score")
    target = _finite_vector(target_score, label="target_score")
    if source.shape != target.shape:
        raise ValueError("source_score and target_score must have identical dimensions.")
    fixed_budget = float(budget)
    if not np.isfinite(fixed_budget) or fixed_budget <= 0.0:
        raise ValueError("budget must be finite and strictly positive.")
    absolute, relative = _validated_tolerances(
        absolute_tolerance=absolute_tolerance,
        relative_tolerance=relative_tolerance,
    )

    source_mean = float(np.mean(source))
    target_mean = float(np.mean(target))
    source_centered = source - source_mean
    target_centered = target - target_mean
    source_norm = float(np.linalg.norm(source_centered))
    target_norm = float(np.linalg.norm(target_centered))
    relation_tolerance = absolute + relative * max(
        1.0,
        float(np.max(np.abs(source))),
        float(np.max(np.abs(target))),
    )

    source_is_constant = bool(float(np.max(np.abs(source_centered))) <= relation_tolerance)
    if source_is_constant:
        scale = 1.0
        intercept = target_mean - source_mean
        residual = target - (source + intercept)
    else:
        denominator = float(np.dot(source_centered, source_centered))
        if not np.isfinite(denominator) or denominator <= 0.0:
            raise RuntimeError("The centered source norm is numerically invalid.")
        scale = float(np.dot(source_centered, target_centered) / denominator)
        intercept = target_mean - scale * source_mean
        residual = target - (scale * source + intercept)

    residual_norm = float(np.linalg.norm(residual))
    maximum_error = float(np.max(np.abs(residual)))
    positive_scale = bool(np.isfinite(scale) and scale > 0.0)
    equivalent = bool(positive_scale and maximum_error <= relation_tolerance)
    return FullBudgetScoreCertificate(
        equivalent_on_complete_budget_hull=equivalent,
        estimated_scale=scale,
        positive_scale=positive_scale,
        estimated_unit_intercept=float(intercept),
        portfolio_score_offset=float(intercept * fixed_budget),
        ambient_dimension=int(len(source)),
        affine_dimension=int(len(source) - 1),
        source_centered_norm=source_norm,
        target_centered_norm=target_norm,
        relation_residual_norm=residual_norm,
        maximum_coordinate_relation_error=maximum_error,
        relation_tolerance=relation_tolerance,
    )


def deterministic_nonaffine_control(
    source_score: npt.ArrayLike,
    *,
    amplitude: float = 1.0e-3,
) -> npt.NDArray[np.float64]:
    """Construct a deterministic target outside ``span{1, source}``.

    The vector is used only as a runtime negative control.  It is not a
    scientific score.  Projection of a coordinate vector onto the orthogonal
    complement of ``span{1, source}`` makes non-affinity algebraic rather than
    dependent on a fortuitous square/nonlinear transformation.
    """

    source = _finite_vector(source_score, label="source_score")
    magnitude = float(amplitude)
    if not np.isfinite(magnitude) or magnitude <= 0.0:
        raise ValueError("amplitude must be finite and strictly positive.")
    if len(source) < 3:
        raise ValueError("A non-affine control requires at least three coordinates.")

    constant = np.ones(len(source), dtype=float)
    centered = source - float(np.mean(source))
    basis: list[np.ndarray] = [constant / float(np.linalg.norm(constant))]
    centered_norm = float(np.linalg.norm(centered))
    if centered_norm > 1.0e-14:
        basis.append(centered / centered_norm)

    residual: np.ndarray | None = None
    for index in range(min(len(source), 8)):
        candidate = np.zeros(len(source), dtype=float)
        candidate[index] = 1.0
        for vector in basis:
            candidate = candidate - float(np.dot(candidate, vector)) * vector
        maximum = float(np.max(np.abs(candidate)))
        if maximum > 1.0e-8:
            residual = candidate / maximum
            break
    if residual is None:
        raise RuntimeError("Could not construct the deterministic non-affine control.")
    target = 1.75 * source + 0.125 + magnitude * residual
    if not bool(np.isfinite(target).all()):
        raise RuntimeError("The deterministic non-affine control is non-finite.")
    return np.asarray(target, dtype=float)


def certificate_record(certificate: Any) -> dict[str, Any]:
    """Return a JSON/Parquet-friendly dataclass record."""

    if not hasattr(certificate, "__dataclass_fields__"):
        raise TypeError("certificate_record requires one certificate dataclass.")
    return dict(asdict(certificate))
