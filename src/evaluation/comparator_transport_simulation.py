"""Controlled simulation of score transport and comparator geometry.

The simulation is deliberately synthetic.  It isolates mechanisms that can
occur when a fixed, groupwise conformal score is transported through time; it
does not reproduce or validate any Lending Club result.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SimulationDesign:
    """Locked computational inputs plus declared synthetic design constants."""

    random_seed: int
    repetitions: int
    sample_size: int
    temporal_shift_grid: tuple[float, ...]
    groups: int = 5
    alpha: float = 0.10
    gamma: float = 0.25
    score_cap: float = 0.25
    funded_fraction: float = 0.10
    lgd: float = 0.45

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> SimulationDesign:
        """Build a design from the locked config's ``simulation`` block."""
        simulation = config.get("simulation")
        if not isinstance(simulation, Mapping):
            raise ValueError("Config must contain a simulation mapping.")
        try:
            design = cls(
                random_seed=int(simulation["random_seed"]),
                repetitions=int(simulation["repetitions"]),
                sample_size=int(simulation["sample_size"]),
                temporal_shift_grid=tuple(
                    float(value) for value in simulation["temporal_shift_grid"]
                ),
            )
        except (KeyError, TypeError) as exc:
            raise ValueError("Simulation config is missing a locked input.") from exc
        design.validate()
        return design

    def validate(self) -> None:
        """Reject invalid or computationally ambiguous designs."""
        if self.repetitions < 1 or self.sample_size < 20:
            raise ValueError("repetitions must be positive and sample_size must be at least 20.")
        if not self.temporal_shift_grid:
            raise ValueError("temporal_shift_grid must not be empty.")
        numeric = np.asarray(self.temporal_shift_grid, dtype=float)
        if not bool(np.all(np.isfinite(numeric))):
            raise ValueError("temporal_shift_grid must contain finite values.")
        if self.groups < 1 or self.groups >= self.sample_size:
            raise ValueError("groups must lie between one and sample_size - 1.")
        if not 0.0 < self.alpha < 1.0:
            raise ValueError("alpha must lie strictly between zero and one.")
        if not 0.0 <= self.gamma <= 1.0:
            raise ValueError("gamma must lie in [0, 1].")
        if not 0.0 < self.funded_fraction < 1.0:
            raise ValueError("funded_fraction must lie strictly between zero and one.")


def expit(values: object) -> np.ndarray:
    """Numerically stable logistic transform."""
    array = np.asarray(values, dtype=float)
    result = np.empty_like(array)
    positive = array >= 0.0
    result[positive] = 1.0 / (1.0 + np.exp(-array[positive]))
    exponential = np.exp(array[~positive])
    result[~positive] = exponential / (1.0 + exponential)
    return result


def _top_k_allocation(values: np.ndarray, count: int) -> np.ndarray:
    order = np.lexsort((np.arange(values.size), -values))
    allocation = np.zeros(values.size, dtype=float)
    allocation[order[:count]] = 1.0
    return allocation


def solve_full_budget_allocation(
    objective: object,
    scores: object,
    *,
    funded_count: int,
    score_cap: float,
    tolerance: float = 1e-12,
) -> np.ndarray:
    """Solve a continuous equal-notional portfolio with one average-score cap.

    The Lagrangian path selects the top ``funded_count`` values of
    ``objective - lambda * score``.  At a path breakpoint, a convex mixture of
    the bracketing portfolios attains the binding score moment exactly.
    """
    objective_values = np.asarray(objective, dtype=float)
    score_values = np.asarray(scores, dtype=float)
    if objective_values.ndim != 1 or score_values.ndim != 1:
        raise ValueError("objective and scores must be one-dimensional.")
    if objective_values.shape != score_values.shape or objective_values.size == 0:
        raise ValueError("objective and scores must be nonempty and aligned.")
    if not bool(np.all(np.isfinite(objective_values))) or not bool(
        np.all(np.isfinite(score_values))
    ):
        raise ValueError("objective and scores must be finite.")
    if not 1 <= funded_count < objective_values.size:
        raise ValueError("funded_count must lie between one and n - 1.")
    cap = float(score_cap)
    if not np.isfinite(cap):
        raise ValueError("score_cap must be finite.")

    unrestricted = _top_k_allocation(objective_values, funded_count)
    unrestricted_moment = float(unrestricted @ score_values / funded_count)
    if unrestricted_moment <= cap + tolerance:
        return unrestricted

    minimum_score = _top_k_allocation(-score_values, funded_count)
    minimum_moment = float(minimum_score @ score_values / funded_count)
    if minimum_moment > cap + tolerance:
        raise ValueError("The requested average-score cap is infeasible.")

    low_lambda = 0.0
    low_allocation = unrestricted
    high_lambda = 1.0
    high_allocation = _top_k_allocation(objective_values - high_lambda * score_values, funded_count)
    high_moment = float(high_allocation @ score_values / funded_count)
    while high_moment > cap:
        low_lambda = high_lambda
        low_allocation = high_allocation
        high_lambda *= 2.0
        high_allocation = _top_k_allocation(
            objective_values - high_lambda * score_values, funded_count
        )
        high_moment = float(high_allocation @ score_values / funded_count)
        if high_lambda > 2.0**50:
            raise RuntimeError("Could not bracket the score-cap solution.")

    for _ in range(48):
        middle = (low_lambda + high_lambda) / 2.0
        candidate = _top_k_allocation(objective_values - middle * score_values, funded_count)
        candidate_moment = float(candidate @ score_values / funded_count)
        if candidate_moment > cap:
            low_lambda = middle
            low_allocation = candidate
        else:
            high_lambda = middle
            high_allocation = candidate

    low_moment = float(low_allocation @ score_values / funded_count)
    high_moment = float(high_allocation @ score_values / funded_count)
    if low_moment <= cap + tolerance:
        return low_allocation
    if abs(high_moment - cap) <= tolerance:
        return high_allocation
    mixing_weight = (cap - high_moment) / (low_moment - high_moment)
    allocation = mixing_weight * low_allocation + (1.0 - mixing_weight) * high_allocation
    achieved = float(allocation @ score_values / funded_count)
    if abs(achieved - cap) > max(tolerance, 1e-11):
        raise AssertionError("Score-cap interpolation did not reconcile.")
    return allocation


def _fixed_taxonomy(scores: np.ndarray, groups: int) -> tuple[np.ndarray, np.ndarray]:
    edges = np.quantile(scores, np.linspace(0.0, 1.0, groups + 1)[1:-1])
    if np.unique(edges).size != edges.size:
        raise ValueError("Fixed taxonomy edges repeat.")
    return edges, np.searchsorted(edges, scores, side="right")


def _exact_group_penalties(
    residuals: np.ndarray, labels: np.ndarray, groups: int, alpha: float
) -> np.ndarray:
    penalties = np.empty(groups, dtype=float)
    for group in range(groups):
        values = np.sort(residuals[labels == group])
        rank = min(int(np.ceil((values.size + 1) * (1.0 - alpha))), values.size)
        penalties[group] = values[rank - 1]
    return penalties


def _weighted_mean(values: np.ndarray, allocation: np.ndarray) -> float:
    return float(allocation @ values / allocation.sum())


def _coverage(y: np.ndarray, low: np.ndarray, high: np.ndarray) -> float:
    return float(np.mean((y >= low) & (y <= high)))


def _portfolio_metrics(
    allocation: np.ndarray,
    *,
    point: np.ndarray,
    outcome: np.ndarray,
    payoff: np.ndarray,
) -> tuple[float, float, float]:
    return (
        _weighted_mean(point, allocation),
        _weighted_mean(outcome, allocation),
        _weighted_mean(payoff, allocation),
    )


def _simulate_repetition(
    rng: np.random.Generator,
    *,
    design: SimulationDesign,
    repetition: int,
    shift: float,
) -> dict[str, float | int]:
    n = design.sample_size
    taxonomy_feature = rng.normal(size=n)
    taxonomy_point = expit(-3.0 + 1.35 * taxonomy_feature)
    edges, _ = _fixed_taxonomy(taxonomy_point, design.groups)

    calibration_feature = rng.normal(size=n)
    calibration_point = expit(-3.0 + 1.35 * calibration_feature)
    calibration_outcome = rng.binomial(1, calibration_point)
    calibration_group = np.searchsorted(edges, calibration_point, side="right")
    residual = np.abs(calibration_outcome - calibration_point)
    group_penalty = _exact_group_penalties(residual, calibration_group, design.groups, design.alpha)
    pooled_penalty = _exact_group_penalties(residual, np.zeros(n, dtype=int), 1, design.alpha)[0]

    feature = rng.normal(loc=shift, size=n)
    point = expit(-3.0 + 1.35 * feature)
    true_probability_score_only = point
    true_probability_joint = expit(-3.0 + 1.35 * feature + shift)
    common_uniform = rng.random(n)
    outcome_score_only = (common_uniform < true_probability_score_only).astype(float)
    outcome_joint = (common_uniform < true_probability_joint).astype(float)

    group = np.searchsorted(edges, point, side="right")
    penalty = group_penalty[group]
    calibration_low = np.clip(calibration_point - group_penalty[calibration_group], 0.0, 1.0)
    calibration_high = np.clip(calibration_point + group_penalty[calibration_group], 0.0, 1.0)
    low = np.clip(point - penalty, 0.0, 1.0)
    high = np.clip(point + penalty, 0.0, 1.0)
    clipped_score = (1.0 - design.gamma) * point + design.gamma * high
    unclipped_score = point + design.gamma * penalty
    pooled_score = point + design.gamma * min(float(pooled_penalty), 1.0)

    rate_noise = rng.normal(scale=0.012, size=n)
    interest_rate = np.clip(0.035 + 1.05 * point + rate_noise, 0.01, 0.35)
    objective = (1.0 - point) * interest_rate - point * design.lgd
    realized_payoff = (1.0 - outcome_joint) * interest_rate - outcome_joint * design.lgd
    funded_count = max(1, int(round(design.funded_fraction * n)))

    guard = solve_full_budget_allocation(
        objective,
        clipped_score,
        funded_count=funded_count,
        score_cap=design.score_cap,
    )
    unclipped = solve_full_budget_allocation(
        objective,
        unclipped_score,
        funded_count=funded_count,
        score_cap=design.score_cap,
    )
    pooled = solve_full_budget_allocation(
        objective,
        pooled_score,
        funded_count=funded_count,
        score_cap=design.score_cap,
    )
    same_cap = solve_full_budget_allocation(
        objective, point, funded_count=funded_count, score_cap=design.score_cap
    )
    guard_point_moment = _weighted_mean(point, guard)
    matched = solve_full_budget_allocation(
        objective, point, funded_count=funded_count, score_cap=guard_point_moment
    )
    matched_residual = _weighted_mean(point, matched) - guard_point_moment
    if abs(matched_residual) > 1e-10:
        raise AssertionError("Moment-matched comparator failed its numerical contract.")

    guard_metrics = _portfolio_metrics(
        guard, point=point, outcome=outcome_joint, payoff=realized_payoff
    )
    same_metrics = _portfolio_metrics(
        same_cap, point=point, outcome=outcome_joint, payoff=realized_payoff
    )
    matched_metrics = _portfolio_metrics(
        matched, point=point, outcome=outcome_joint, payoff=realized_payoff
    )
    score_only_coverage = _coverage(outcome_score_only, low, high)
    transported_coverage = _coverage(outcome_joint, low, high)
    return {
        "repetition": repetition,
        "temporal_shift": shift,
        "calibration_coverage": _coverage(calibration_outcome, calibration_low, calibration_high),
        "zero_base_drift_coverage": score_only_coverage,
        "transported_coverage": transported_coverage,
        "base_rate_drift_coverage_effect": transported_coverage - score_only_coverage,
        "calibration_score_mean": float(calibration_point.mean()),
        "evaluation_score_mean": float(point.mean()),
        "score_drift": float(point.mean() - calibration_point.mean()),
        "group_penalty_sd": float(np.std(group_penalty)),
        "pooled_penalty": float(pooled_penalty),
        "upper_endpoint_saturation": float(np.mean(high >= 1.0 - 1e-12)),
        "clipping_score_reduction": float(np.mean(unclipped_score - clipped_score)),
        "taxonomy_allocation_l1": float(np.mean(np.abs(guard - pooled))),
        "saturation_allocation_l1": float(np.mean(np.abs(guard - unclipped))),
        "guard_point_moment": guard_metrics[0],
        "same_cap_point_moment": same_metrics[0],
        "matched_point_moment": matched_metrics[0],
        "matched_moment_residual": matched_residual,
        "guard_default": guard_metrics[1],
        "same_cap_default": same_metrics[1],
        "matched_default": matched_metrics[1],
        "guard_minus_same_cap_default": guard_metrics[1] - same_metrics[1],
        "guard_minus_matched_default": guard_metrics[1] - matched_metrics[1],
        "guard_payoff": guard_metrics[2],
        "same_cap_payoff": same_metrics[2],
        "matched_payoff": matched_metrics[2],
        "guard_minus_same_cap_payoff": guard_metrics[2] - same_metrics[2],
        "guard_minus_matched_payoff": guard_metrics[2] - matched_metrics[2],
    }


def run_simulation(design: SimulationDesign) -> pd.DataFrame:
    """Run all locked repetitions and shifts with independent deterministic streams."""
    design.validate()
    seed_sequence = np.random.SeedSequence(design.random_seed)
    stream_count = design.repetitions * len(design.temporal_shift_grid)
    streams = iter(seed_sequence.spawn(stream_count))
    rows: list[dict[str, float | int]] = []
    for repetition in range(design.repetitions):
        for shift in design.temporal_shift_grid:
            rows.append(
                _simulate_repetition(
                    np.random.default_rng(next(streams)),
                    design=design,
                    repetition=repetition,
                    shift=shift,
                )
            )
    return pd.DataFrame(rows).sort_values(
        ["temporal_shift", "repetition"], kind="mergesort", ignore_index=True
    )


def summarize_simulation(results: pd.DataFrame) -> pd.DataFrame:
    """Return deterministic shift-level means and Monte Carlo quantiles."""
    required = {"temporal_shift", "repetition"}
    if results.empty or not required.issubset(results.columns):
        raise ValueError("Simulation results are empty or malformed.")
    metrics = [column for column in results.columns if column not in required]
    rows: list[dict[str, float | int | str]] = []
    for shift, group in results.groupby("temporal_shift", sort=True):
        shift_value = float(cast(float, shift))
        for metric in metrics:
            values = group[metric].to_numpy(dtype=float)
            rows.append(
                {
                    "temporal_shift": shift_value,
                    "metric": metric,
                    "mean": float(np.mean(values)),
                    "q05": float(np.quantile(values, 0.05)),
                    "q50": float(np.quantile(values, 0.50)),
                    "q95": float(np.quantile(values, 0.95)),
                    "repetitions": int(values.size),
                }
            )
    return pd.DataFrame(rows)


def simulate_from_config(config: Mapping[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run and summarize the simulation block of an experiment config."""
    results = run_simulation(SimulationDesign.from_config(config))
    return results, summarize_simulation(results)


def affine_transformed_cap(score_cap: float, *, slope: float, intercept: float) -> float:
    """Translate a cap under a positive affine score transformation."""
    if not np.isfinite(slope) or slope <= 0.0 or not np.isfinite(intercept):
        raise ValueError("Affine slope must be positive and parameters must be finite.")
    return float(slope * score_cap + intercept)
