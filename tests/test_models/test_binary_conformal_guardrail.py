from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    assign_conformal_groups,
    fit_binary_outcome_recipe,
)


def test_fixed_edges_are_not_relearned_from_residual_sample() -> None:
    fixed_edges = (0.0, 0.2, 0.5, 1.0)

    first = fit_binary_outcome_recipe(
        np.array([0.05, 0.10, 0.30, 0.40, 0.60, 0.90]),
        np.array([0, 1, 0, 1, 0, 1]),
        alpha=0.5,
        bin_edges=fixed_edges,
        taxonomy_provenance="pd_calibration_2011",
        taxonomy_method="upstream_score_quantiles",
    )
    second = fit_binary_outcome_recipe(
        np.array([0.15, 0.19, 0.21, 0.49, 0.51, 0.99]),
        np.array([1, 0, 1, 0, 1, 0]),
        alpha=0.5,
        bin_edges=fixed_edges,
        taxonomy_provenance="pd_calibration_2011",
        taxonomy_method="upstream_score_quantiles",
    )

    assert first.bin_edges == second.bin_edges == fixed_edges
    assert first.taxonomy_provenance == "pd_calibration_2011"
    assert first.taxonomy_method == "upstream_score_quantiles"
    assert first.method == "fixed_taxonomy_split_mondrian_absolute_residual"
    assert first.group_counts == second.group_counts == (2, 2, 2)
    assert first.residual_quantiles != second.residual_quantiles


def test_fixed_edge_recipe_uses_exact_finite_sample_rank() -> None:
    recipe = fit_binary_outcome_recipe(
        np.array([0.1, 0.2, 0.3, 0.4]),
        np.array([0, 0, 1, 1]),
        alpha=0.4,
        bin_edges=(0.0, 1.0),
    )

    # ceil((4 + 1) * (1 - 0.4)) = 3; sorted residuals are 0.1, 0.2, 0.6, 0.7.
    assert recipe.raw_finite_sample_ranks == (3,)
    assert recipe.finite_sample_ranks == (3,)
    assert recipe.residual_quantiles == pytest.approx((0.6,))


def test_bin_edges_must_be_strictly_increasing() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        assign_conformal_groups(np.array([0.2]), (0.0, 0.5, 0.5, 1.0))


def test_old_recipe_payload_deserializes_with_provenance_defaults() -> None:
    payload: dict[str, Any] = {
        "alpha": 0.1,
        "requested_groups": 1,
        "bin_edges": (0.0, 1.0),
        "residual_quantiles": (0.4,),
        "group_counts": (10,),
        "finite_sample_ranks": (10,),
        "raw_finite_sample_ranks": (10,),
    }

    recipe = BinaryOutcomeConformalRecipe(**payload)

    assert recipe.taxonomy_provenance == "unspecified_legacy_recipe"
    assert recipe.taxonomy_method == "unspecified_legacy_taxonomy"
