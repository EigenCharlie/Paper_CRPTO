from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.models.conformal_alpha_grid import (
    FrozenConformalRecipe,
    alpha_interval_columns,
    compute_exact_alpha_intervals,
)


def _payload() -> dict:
    return {
        "tuning_90_best": {
            "partition": "grade",
            "partition_probability_source": "calibrated",
            "n_score_bins": 5,
            "fallback_mode": "global_only",
            "score_scale_family": "none",
            "min_group_size": 1,
            "alpha_target_90": 0.10,
            "alpha_used_90": 0.095,
        },
        "calibration_split": {
            "calibration_fraction": 0.75,
            "holdout_ratio": 0.20,
            "random_state": 42,
        },
        "group_coverage_multipliers": {"A": 1.05},
        "temporal_segment_multipliers": {},
        "global_rebalance": {"enabled": False, "applied": False},
    }


def test_recipe_scales_alpha_by_frozen_conservative_ratio() -> None:
    recipe = FrozenConformalRecipe.from_results_payload(_payload())

    assert recipe.used_alpha(0.01) == pytest.approx(0.0095)
    assert alpha_interval_columns(0.01) == (
        "pd_low_alpha_0p010",
        "pd_high_alpha_0p010",
    )


def test_recipe_rejects_narrowing_adjustments() -> None:
    payload = _payload()
    payload["global_rebalance"] = {"applied": True, "factor": 0.95}

    with pytest.raises(ValueError, match="widening"):
        FrozenConformalRecipe.from_results_payload(payload)


def test_exact_alpha_intervals_use_frozen_partition_and_multiplier() -> None:
    recipe = FrozenConformalRecipe.from_results_payload(_payload())
    y_cal = np.array([0.0, 1.0, 0.0, 1.0])
    p_cal = np.array([0.1, 0.8, 0.2, 0.7])
    p_eval = np.array([0.15, 0.75])
    groups_cal = pd.Series(["A", "A", "B", "B"])
    groups_eval = pd.Series(["A", "B"])

    result = compute_exact_alpha_intervals(
        recipe=recipe,
        target_alpha=0.10,
        y_cal=y_cal,
        interval_probability_cal=p_cal,
        interval_probability_eval=p_eval,
        partition_probability_cal=p_cal,
        partition_probability_eval=p_eval,
        base_groups_cal=groups_cal,
        base_groups_eval=groups_eval,
    )

    assert result.used_alpha == pytest.approx(0.095)
    assert result.partition_labels.tolist() == ["A", "B"]
    assert np.all(result.low <= result.point)
    assert np.all(result.high >= result.point)
    assert result.high[0] == pytest.approx(0.36)
