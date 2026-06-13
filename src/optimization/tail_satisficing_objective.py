"""Tail-risk and satisficing scoring utilities for portfolio experiments."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, cast

import numpy as np

SatisficingSense = Literal["min", "max", "equals"]


@dataclass(frozen=True)
class SatisficingThreshold:
    """A pass/fail threshold for an OR-style satisficing metric."""

    metric: str
    sense: SatisficingSense
    threshold: float | bool
    tolerance: float = 1e-12


@dataclass(frozen=True)
class SatisficingMargin:
    """Observed margin against a satisficing threshold."""

    metric: str
    sense: SatisficingSense
    observed: float
    threshold: float
    margin: float
    passed: bool


@dataclass(frozen=True)
class TailSatisficingObjectiveResult:
    """Scalar score plus interpretable tail-risk and satisficing diagnostics."""

    expected_return: float
    mean_loss_rate: float
    cvar_loss_rate: float
    entropic_oce: float
    objective_value: float
    satisficing_pass: bool
    min_satisficing_margin: float
    satisficing_shortfall: float
    margins: tuple[SatisficingMargin, ...]

    def to_dict(self) -> dict[str, float | bool]:
        """Return scalar result fields for tables or JSON status files."""
        return {
            "expected_return": self.expected_return,
            "mean_loss_rate": self.mean_loss_rate,
            "cvar_loss_rate": self.cvar_loss_rate,
            "entropic_oce": self.entropic_oce,
            "objective_value": self.objective_value,
            "satisficing_pass": self.satisficing_pass,
            "min_satisficing_margin": self.min_satisficing_margin,
            "satisficing_shortfall": self.satisficing_shortfall,
        }


def normalize_weights(weights: Sequence[float] | np.ndarray) -> np.ndarray:
    """Return non-negative weights normalized to sum to one."""
    array = np.asarray(weights, dtype=float)
    if array.ndim != 1:
        raise ValueError("weights must be one-dimensional")
    if len(array) == 0:
        raise ValueError("weights must not be empty")
    if np.any(~np.isfinite(array)):
        raise ValueError("weights must be finite")
    if np.any(array < 0):
        raise ValueError("weights must be non-negative")
    total = float(array.sum())
    if total <= 0:
        raise ValueError("weights must have positive total mass")
    return array / total


def weighted_mean(
    values: Sequence[float] | np.ndarray, weights: Sequence[float] | np.ndarray
) -> float:
    """Compute a finite weighted mean with normalized portfolio weights."""
    value_array = _coerce_values(values, weights)
    weight_array = normalize_weights(weights)
    return float(np.sum(weight_array * value_array))


def weighted_cvar(
    losses: Sequence[float] | np.ndarray,
    weights: Sequence[float] | np.ndarray,
    *,
    tail: float = 0.95,
) -> float:
    """Compute weighted CVaR over the upper loss tail.

    Args:
        losses: Per-loan or per-scenario loss rates where larger is worse.
        weights: Portfolio weights or scenario probabilities.
        tail: Confidence level. ``tail=0.95`` averages the worst 5% mass.
    """
    if not 0.0 < float(tail) < 1.0:
        raise ValueError("tail must be in (0, 1)")

    loss_array = _coerce_values(losses, weights)
    weight_array = normalize_weights(weights)
    order = np.argsort(-loss_array)
    sorted_loss = loss_array[order]
    sorted_weight = weight_array[order]

    target_mass = 1.0 - float(tail)
    used_mass = 0.0
    weighted_total = 0.0
    for loss, weight in zip(sorted_loss, sorted_weight, strict=False):
        if used_mass >= target_mass:
            break
        take = min(float(weight), target_mass - used_mass)
        weighted_total += float(loss) * take
        used_mass += take
    return weighted_total / max(used_mass, 1e-12)


def entropic_oce(
    losses: Sequence[float] | np.ndarray,
    weights: Sequence[float] | np.ndarray,
    *,
    theta: float = 5.0,
    stable: bool = True,
) -> float:
    """Compute the entropic optimized certainty equivalent for losses."""
    if float(theta) <= 0:
        raise ValueError("theta must be positive")

    loss_array = _coerce_values(losses, weights)
    weight_array = normalize_weights(weights)
    scaled = float(theta) * loss_array
    if not stable:
        return float(np.log(np.sum(weight_array * np.exp(scaled))) / float(theta))
    shift = float(np.max(scaled))
    log_weighted_exp = shift + float(np.log(np.sum(weight_array * np.exp(scaled - shift))))
    return log_weighted_exp / float(theta)


def evaluate_satisficing_margins(
    metrics: Mapping[str, float | bool],
    thresholds: Sequence[SatisficingThreshold],
) -> tuple[SatisficingMargin, ...]:
    """Evaluate pass/fail margins for named metrics."""
    margins: list[SatisficingMargin] = []
    for threshold in thresholds:
        if threshold.metric not in metrics:
            raise KeyError(f"Missing satisficing metric: {threshold.metric}")
        observed = _as_float(metrics[threshold.metric])
        target = _as_float(threshold.threshold)
        tolerance = float(threshold.tolerance)
        if threshold.sense == "min":
            margin = observed - target
            passed = margin >= -tolerance
        elif threshold.sense == "max":
            margin = target - observed
            passed = margin >= -tolerance
        elif threshold.sense == "equals":
            margin = -abs(observed - target)
            passed = abs(observed - target) <= tolerance
        else:
            raise ValueError(f"Unsupported satisficing sense: {threshold.sense}")
        margins.append(
            SatisficingMargin(
                metric=threshold.metric,
                sense=threshold.sense,
                observed=observed,
                threshold=target,
                margin=float(margin),
                passed=bool(passed),
            )
        )
    return tuple(margins)


def score_tail_satisficing_objective(
    *,
    expected_return: float,
    loss_rates: Sequence[float] | np.ndarray,
    weights: Sequence[float] | np.ndarray,
    thresholds: Sequence[SatisficingThreshold] = (),
    extra_metrics: Mapping[str, float | bool] | None = None,
    cvar_tail: float = 0.95,
    oce_theta: float = 5.0,
    cvar_penalty: float = 0.0,
    oce_penalty: float = 0.0,
    satisficing_shortfall_penalty: float = 1.0,
    risk_scale: float = 1.0,
) -> TailSatisficingObjectiveResult:
    """Score a portfolio with tail-risk penalties and satisficing shortfalls.

    The score is intentionally post-hoc and side-effect free. It can rank future
    experimental policies, but it does not alter the frozen CRPTO champion.
    """
    mean_loss_rate = weighted_mean(loss_rates, weights)
    cvar_loss_rate = weighted_cvar(loss_rates, weights, tail=cvar_tail)
    oce_loss = entropic_oce(loss_rates, weights, theta=oce_theta)
    metrics: dict[str, float | bool] = {
        "expected_return": float(expected_return),
        "mean_loss_rate": mean_loss_rate,
        "cvar_loss_rate": cvar_loss_rate,
        "entropic_oce": oce_loss,
    }
    if extra_metrics is not None:
        metrics.update(extra_metrics)

    margins = evaluate_satisficing_margins(metrics, thresholds)
    shortfall = float(sum(max(0.0, -margin.margin) for margin in margins))
    min_margin = min((margin.margin for margin in margins), default=0.0)
    objective_value = float(expected_return) - float(risk_scale) * (
        float(cvar_penalty) * cvar_loss_rate
        + float(oce_penalty) * oce_loss
        + float(satisficing_shortfall_penalty) * shortfall
    )
    return TailSatisficingObjectiveResult(
        expected_return=float(expected_return),
        mean_loss_rate=mean_loss_rate,
        cvar_loss_rate=cvar_loss_rate,
        entropic_oce=oce_loss,
        objective_value=objective_value,
        satisficing_pass=all(margin.passed for margin in margins),
        min_satisficing_margin=float(min_margin),
        satisficing_shortfall=shortfall,
        margins=margins,
    )


def funded_loss_rate(
    default_flag: Sequence[float] | np.ndarray,
    int_rates: Sequence[float] | np.ndarray,
    *,
    lgd: float,
) -> np.ndarray:
    """Return per-loan realized loss rates under a loss-given-default value."""
    default_array = np.asarray(default_flag, dtype=float)
    int_rate_array = _coerce_values(int_rates, default_array)
    if np.any((default_array < 0) | (default_array > 1)):
        raise ValueError("default_flag values must be in [0, 1]")
    return cast(np.ndarray, default_array * float(lgd) - (1.0 - default_array) * int_rate_array)


def _coerce_values(
    values: Sequence[float] | np.ndarray,
    weights_or_like: Sequence[float] | np.ndarray,
) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    like = np.asarray(weights_or_like)
    if array.ndim != 1:
        raise ValueError("values must be one-dimensional")
    if len(array) != len(like):
        raise ValueError("values and weights must have the same length")
    if len(array) == 0:
        raise ValueError("values must not be empty")
    if np.any(~np.isfinite(array)):
        raise ValueError("values must be finite")
    return array


def _as_float(value: float | bool | Any) -> float:
    if isinstance(value, bool):
        return float(value)
    return float(value)
