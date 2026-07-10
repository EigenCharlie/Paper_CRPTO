"""Exact alpha-grid replay for a frozen Mondrian conformal recipe."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.models.conformal import (
    build_mondrian_partition_labels,
    create_pd_intervals_mondrian_from_predictions,
)
from src.models.conformal_tuning import apply_group_multipliers, build_group_temporal_segments


@dataclass(frozen=True)
class FrozenConformalRecipe:
    """Selected interval design and holdout-learned widening policy."""

    partition: str
    partition_probability_source: str
    n_score_bins: int
    fallback_mode: str
    score_scale_family: str
    min_group_size: int
    reference_target_alpha: float
    reference_used_alpha: float
    calibration_fraction: float
    tuning_holdout_ratio: float
    tuning_random_state: int
    group_multipliers: dict[str, float]
    temporal_segment_multipliers: dict[str, float]
    temporal_segment_freq: str
    global_rebalance_factor: float

    @classmethod
    def from_results_payload(cls, payload: dict[str, Any]) -> FrozenConformalRecipe:
        """Build a replay recipe from ``conformal_results_mondrian.pkl``."""
        selected = payload["tuning_90_best"]
        split = payload["calibration_split"]
        global_rebalance = payload.get("global_rebalance", {}) or {}
        factor = (
            float(global_rebalance.get("factor", 1.0))
            if bool(global_rebalance.get("applied", False))
            else 1.0
        )
        recipe = cls(
            partition=str(selected["partition"]),
            partition_probability_source=str(selected["partition_probability_source"]),
            n_score_bins=int(selected["n_score_bins"]),
            fallback_mode=str(selected["fallback_mode"]),
            score_scale_family=str(selected["score_scale_family"]),
            min_group_size=int(selected["min_group_size"]),
            reference_target_alpha=float(selected["alpha_target_90"]),
            reference_used_alpha=float(selected["alpha_used_90"]),
            calibration_fraction=float(split["calibration_fraction"]),
            tuning_holdout_ratio=float(split["holdout_ratio"]),
            tuning_random_state=int(split["random_state"]),
            group_multipliers={
                str(key): float(value)
                for key, value in (payload.get("group_coverage_multipliers", {}) or {}).items()
            },
            temporal_segment_multipliers={
                str(key): float(value)
                for key, value in (payload.get("temporal_segment_multipliers", {}) or {}).items()
            },
            temporal_segment_freq=str(payload.get("temporal_segment_freq", "Q")),
            global_rebalance_factor=factor,
        )
        recipe.validate()
        return recipe

    def validate(self) -> None:
        """Reject recipe settings that could narrow a nominal interval silently."""
        if not 0.0 < self.reference_target_alpha < 1.0:
            raise ValueError("reference_target_alpha must lie in (0, 1).")
        if not 0.0 < self.reference_used_alpha <= self.reference_target_alpha:
            raise ValueError(
                "reference_used_alpha must be positive and no larger than the target alpha."
            )
        multipliers = [
            *self.group_multipliers.values(),
            *self.temporal_segment_multipliers.values(),
            self.global_rebalance_factor,
        ]
        if any(value < 1.0 for value in multipliers):
            raise ValueError("Frozen alpha-grid replay only supports widening adjustments.")

    def used_alpha(self, target_alpha: float) -> float:
        """Apply the frozen conservative alpha ratio selected at the reference level."""
        target = float(target_alpha)
        if not 0.0 < target < 1.0:
            raise ValueError("target_alpha must lie in (0, 1).")
        ratio = self.reference_used_alpha / self.reference_target_alpha
        return target * ratio


@dataclass(frozen=True)
class ExactAlphaIntervals:
    """One exact conformal interval vector and its replay metadata."""

    target_alpha: float
    used_alpha: float
    point: np.ndarray
    low: np.ndarray
    high: np.ndarray
    partition_labels: pd.Series
    partition_metadata: dict[str, Any]
    diagnostics: dict[str, Any]


def alpha_column_token(alpha: float) -> str:
    """Return a stable column-safe token such as ``0p010``."""
    return f"{float(alpha):.3f}".replace(".", "p")


def alpha_interval_columns(alpha: float) -> tuple[str, str]:
    """Return the low/high column names for an exact alpha-grid artifact."""
    token = alpha_column_token(alpha)
    return f"pd_low_alpha_{token}", f"pd_high_alpha_{token}"


def _scale_around_prediction(
    point: np.ndarray,
    intervals: np.ndarray,
    factor: float,
) -> np.ndarray:
    radius = np.maximum(point - intervals[:, 0], intervals[:, 1] - point)
    return np.column_stack(
        [
            np.clip(point - radius * factor, 0.0, 1.0),
            np.clip(point + radius * factor, 0.0, 1.0),
        ]
    )


def compute_exact_alpha_intervals(
    *,
    recipe: FrozenConformalRecipe,
    target_alpha: float,
    y_cal: pd.Series | np.ndarray,
    interval_probability_cal: np.ndarray,
    interval_probability_eval: np.ndarray,
    partition_probability_cal: np.ndarray,
    partition_probability_eval: np.ndarray,
    base_groups_cal: pd.Series | np.ndarray,
    base_groups_eval: pd.Series | np.ndarray,
    issue_dates_eval: pd.Series | np.ndarray | None = None,
) -> ExactAlphaIntervals:
    """Recompute one alpha exactly under a frozen partition and widening recipe."""
    group_cal, group_eval, partition_metadata = build_mondrian_partition_labels(
        y_prob_cal=partition_probability_cal,
        y_prob_eval=partition_probability_eval,
        partition=recipe.partition,
        base_groups_cal=base_groups_cal,
        base_groups_eval=base_groups_eval,
        n_score_bins=recipe.n_score_bins,
        min_group_size=recipe.min_group_size,
        fallback_mode=recipe.fallback_mode,
    )
    used_alpha = recipe.used_alpha(target_alpha)
    point, intervals, diagnostics = create_pd_intervals_mondrian_from_predictions(
        y_cal_pred=interval_probability_cal,
        y_test_pred=interval_probability_eval,
        y_cal=y_cal,
        group_cal=group_cal,
        group_test=group_eval,
        alpha=used_alpha,
        min_group_size=recipe.min_group_size,
        score_scale_family=recipe.score_scale_family,
        log_summary=False,
    )
    if recipe.group_multipliers:
        intervals = apply_group_multipliers(
            point,
            intervals,
            group_eval,
            recipe.group_multipliers,
        )
    if recipe.temporal_segment_multipliers:
        if issue_dates_eval is None:
            raise ValueError("issue_dates_eval is required by the frozen temporal multipliers.")
        temporal_segments = build_group_temporal_segments(
            group_eval,
            issue_dates_eval,
            freq=recipe.temporal_segment_freq,
        )
        intervals = apply_group_multipliers(
            point,
            intervals,
            temporal_segments,
            recipe.temporal_segment_multipliers,
        )
    if not np.isclose(recipe.global_rebalance_factor, 1.0):
        intervals = _scale_around_prediction(
            point,
            intervals,
            recipe.global_rebalance_factor,
        )
    return ExactAlphaIntervals(
        target_alpha=float(target_alpha),
        used_alpha=used_alpha,
        point=point,
        low=intervals[:, 0],
        high=intervals[:, 1],
        partition_labels=group_eval,
        partition_metadata=partition_metadata,
        diagnostics=diagnostics,
    )
