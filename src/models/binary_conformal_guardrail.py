"""Mondrian split-conformal intervals for the observed binary outcome.

These intervals predict the binary repayment outcome. They are not confidence
intervals for a latent probability of default. Their upper endpoint may be
used as a decision score, but that use does not transport marginal coverage to
an optimizer-selected portfolio.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BinaryOutcomeConformalRecipe:
    """Exact absolute-residual quantiles fitted within score strata."""

    alpha: float
    requested_groups: int
    bin_edges: tuple[float, ...]
    residual_quantiles: tuple[float, ...]
    group_counts: tuple[int, ...]
    finite_sample_ranks: tuple[int, ...]
    raw_finite_sample_ranks: tuple[int, ...]
    estimand: str = "binary_outcome_prediction_interval"
    method: str = "exact_split_mondrian_absolute_residual"
    learned_widening: bool = False
    learned_floor: bool = False
    taxonomy_provenance: str = "unspecified_legacy_recipe"
    taxonomy_method: str = "unspecified_legacy_taxonomy"


def _validated_bin_edges(bin_edges: Sequence[float]) -> np.ndarray:
    edges = np.asarray(tuple(bin_edges), dtype=float)
    if (
        edges.ndim != 1
        or len(edges) < 2
        or not bool(np.isfinite(edges).all())
        or bool(np.any(np.diff(edges) <= 0.0))
    ):
        raise ValueError(
            "Conformal bin edges must be a finite, strictly increasing one-dimensional vector."
        )
    return edges


def assign_conformal_groups(
    probabilities: np.ndarray,
    bin_edges: Sequence[float],
) -> np.ndarray:
    """Assign calibrated scores to the frozen Mondrian strata."""
    values = np.asarray(probabilities, dtype=float)
    edges = _validated_bin_edges(bin_edges)
    return np.searchsorted(edges[1:-1], values, side="right").astype(int)


def fit_binary_outcome_recipe(
    probabilities: np.ndarray,
    outcomes: np.ndarray,
    *,
    alpha: float,
    n_groups: int | None = None,
    bin_edges: Sequence[float] | None = None,
    taxonomy_provenance: str | None = None,
    taxonomy_method: str | None = None,
    method: str | None = None,
) -> BinaryOutcomeConformalRecipe:
    """Fit exact residual quantiles within a fixed or legacy score taxonomy.

    When ``bin_edges`` is supplied, the taxonomy is treated as an upstream,
    outcome-free input. Only residuals from ``probabilities`` and ``outcomes``
    determine the group counts, ranks, and quantiles. Omitting ``bin_edges``
    preserves the historical behavior that learns score quantiles from this
    same calibration sample.
    """
    point = np.asarray(probabilities, dtype=float)
    raw_outcomes = np.asarray(outcomes)
    if len(point) != len(raw_outcomes) or len(point) == 0:
        raise ValueError("Conformal fit arrays must be nonempty and aligned.")
    if not bool(np.isfinite(point).all()):
        raise ValueError("Conformal probabilities must be finite.")
    if not bool(np.isin(raw_outcomes, (0, 1)).all()):
        raise ValueError("Conformal outcomes must contain only binary labels 0 and 1.")
    y_true = raw_outcomes.astype(int)
    if not 0.0 < float(alpha) < 1.0:
        raise ValueError("alpha must lie in (0, 1).")
    if bin_edges is None:
        if n_groups is None or int(n_groups) < 1:
            raise ValueError("n_groups must be positive when bin_edges are not supplied.")
        group_count = int(n_groups)
        edges = np.quantile(
            point,
            np.linspace(0.0, 1.0, group_count + 1),
            method="linear",
        )
        if bool(np.any(np.diff(edges) <= 0.0)):
            raise RuntimeError("Calibrated-score quantiles do not define distinct groups.")
        provenance = taxonomy_provenance or "conformal_calibration_sample"
        taxonomy = taxonomy_method or "empirical_linear_score_quantiles"
        recipe_method = method or "exact_split_mondrian_absolute_residual"
    else:
        edges = _validated_bin_edges(bin_edges)
        group_count = len(edges) - 1
        if n_groups is not None and int(n_groups) != group_count:
            raise ValueError("n_groups must match the number of supplied score bins.")
        provenance = taxonomy_provenance or "externally_supplied"
        taxonomy = taxonomy_method or "fixed_strictly_increasing_score_bin_edges"
        recipe_method = method or "fixed_taxonomy_split_mondrian_absolute_residual"
    groups = assign_conformal_groups(point, tuple(float(value) for value in edges))
    residual = np.abs(y_true.astype(float) - point)
    quantiles: list[float] = []
    counts: list[int] = []
    ranks: list[int] = []
    raw_ranks: list[int] = []
    for group in range(group_count):
        scores = np.sort(residual[groups == group])
        count = int(len(scores))
        if count == 0:
            raise RuntimeError(f"Conformal group {group} is empty.")
        raw_rank = int(np.ceil((count + 1) * (1.0 - float(alpha))))
        rank = min(max(raw_rank, 1), count)
        quantile = 1.0 if raw_rank > count else float(scores[rank - 1])
        counts.append(count)
        raw_ranks.append(raw_rank)
        ranks.append(rank)
        quantiles.append(float(np.clip(quantile, 0.0, 1.0)))
    return BinaryOutcomeConformalRecipe(
        alpha=float(alpha),
        requested_groups=group_count,
        bin_edges=tuple(float(value) for value in edges),
        residual_quantiles=tuple(quantiles),
        group_counts=tuple(counts),
        finite_sample_ranks=tuple(ranks),
        raw_finite_sample_ranks=tuple(raw_ranks),
        method=recipe_method,
        taxonomy_provenance=provenance,
        taxonomy_method=taxonomy,
    )


def apply_binary_outcome_recipe(
    probabilities: np.ndarray,
    recipe: BinaryOutcomeConformalRecipe,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Apply the frozen recipe without holdout-learned widening or floors."""
    point = np.asarray(probabilities, dtype=float)
    groups = assign_conformal_groups(point, recipe.bin_edges)
    quantiles = np.asarray(recipe.residual_quantiles, dtype=float)[groups]
    lower = np.clip(point - quantiles, 0.0, 1.0)
    upper = np.clip(point + quantiles, 0.0, 1.0)
    return groups, lower, upper
