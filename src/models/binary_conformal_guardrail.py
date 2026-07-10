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


def assign_conformal_groups(
    probabilities: np.ndarray,
    bin_edges: Sequence[float],
) -> np.ndarray:
    """Assign calibrated scores to the frozen Mondrian strata."""
    values = np.asarray(probabilities, dtype=float)
    edges = np.asarray(tuple(bin_edges), dtype=float)
    if edges.ndim != 1 or len(edges) < 2 or bool(np.any(np.diff(edges) < 0.0)):
        raise ValueError("Conformal bin edges must be a sorted one-dimensional vector.")
    return np.searchsorted(edges[1:-1], values, side="right").astype(int)


def fit_binary_outcome_recipe(
    probabilities: np.ndarray,
    outcomes: np.ndarray,
    *,
    alpha: float,
    n_groups: int,
) -> BinaryOutcomeConformalRecipe:
    """Fit exact finite-sample absolute-residual quantiles by score stratum."""
    point = np.asarray(probabilities, dtype=float)
    y_true = np.asarray(outcomes, dtype=int)
    if len(point) != len(y_true) or len(point) == 0:
        raise ValueError("Conformal fit arrays must be nonempty and aligned.")
    if not 0.0 < float(alpha) < 1.0:
        raise ValueError("alpha must lie in (0, 1).")
    if int(n_groups) < 1:
        raise ValueError("n_groups must be positive.")
    edges = np.quantile(
        point,
        np.linspace(0.0, 1.0, int(n_groups) + 1),
        method="linear",
    )
    if bool(np.any(np.diff(edges) <= 0.0)):
        raise RuntimeError("Calibrated-score quantiles do not define distinct groups.")
    groups = assign_conformal_groups(point, tuple(float(value) for value in edges))
    residual = np.abs(y_true.astype(float) - point)
    quantiles: list[float] = []
    counts: list[int] = []
    ranks: list[int] = []
    raw_ranks: list[int] = []
    for group in range(int(n_groups)):
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
        requested_groups=int(n_groups),
        bin_edges=tuple(float(value) for value in edges),
        residual_quantiles=tuple(quantiles),
        group_counts=tuple(counts),
        finite_sample_ranks=tuple(ranks),
        raw_finite_sample_ranks=tuple(raw_ranks),
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
