"""Read-only design sensitivities for the active IJDS audit."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from src.data.outcome_observability import build_outcome_label_availability
from src.evaluation.coverage_transport import build_temporal_conformal_audit
from src.models.binary_conformal_guardrail import (
    apply_binary_outcome_recipe,
    fit_binary_outcome_recipe,
)
from src.models.maturity_safe_pd import apply_platt_calibrator, catboost_raw_margin


def build_label_lag_coverage_sensitivity(
    *,
    universe: pd.DataFrame,
    features: pd.DataFrame,
    model: Any,
    calibrator: Any,
    fixed_edges: Sequence[float],
    decision_panel: pd.DataFrame,
    outcomes: pd.DataFrame,
    config: Mapping[str, Any],
    lag_months: Sequence[int],
) -> pd.DataFrame:
    """Recompute fixed-taxonomy coverage over a closed label-lag grid."""
    conformal = universe.loc[universe["design_split"].eq("conformal_fit")].copy()
    probabilities = apply_platt_calibrator(
        calibrator,
        catboost_raw_margin(model, features.loc[conformal.index]),
    )
    alpha = float(config["conformal"]["alpha"])
    group_count = int(config["conformal"]["canonical_groups"])
    minimum_rows = int(config["conformal"]["minimum_rows_per_group"])
    rows: list[pd.DataFrame] = []
    for lag in [int(value) for value in lag_months]:
        labels = build_outcome_label_availability(
            conformal["loan_status"],
            conformal["last_pymnt_d"],
            cutoff=str(config["source"]["information_cutoff"]),
            charged_off_lag_months=lag,
        )
        available = labels["label_available"].to_numpy(dtype=bool)
        fit_labels = labels.loc[available, "terminal_outcome"].astype(int).to_numpy(dtype=int)
        fit_probabilities = np.asarray(probabilities, dtype=float)[available]
        recipe = fit_binary_outcome_recipe(
            fit_probabilities,
            fit_labels,
            alpha=alpha,
            n_groups=group_count,
            bin_edges=fixed_edges,
            taxonomy_provenance="2011_all_status_independent_calibrated_scores",
            taxonomy_method="fixed_empirical_linear_score_quantiles",
            method=str(config["conformal"]["method"]),
        )
        if min(recipe.group_counts) < minimum_rows:
            raise RuntimeError(f"Lag {lag} produced a residual group below {minimum_rows} rows.")
        groups, lower, upper = apply_binary_outcome_recipe(
            decision_panel["pd_point"].to_numpy(dtype=float),
            recipe,
        )
        panel = decision_panel.copy()
        panel["conformal_group"] = groups
        panel["conformal_lower"] = lower
        panel["conformal_upper"] = upper
        coverage = build_temporal_conformal_audit(panel, outcomes, recipe)
        fit_group, fit_lower, fit_upper = apply_binary_outcome_recipe(
            fit_probabilities,
            recipe,
        )
        del fit_group
        fit_coverage = float(np.mean((fit_labels >= fit_lower) & (fit_labels <= fit_upper)))
        coverage.insert(0, "charged_off_lag_months", lag)
        coverage.insert(1, "conformal_fit_rows", int(len(fit_labels)))
        coverage.insert(2, "conformal_fit_coverage", fit_coverage)
        coverage.insert(3, "residual_group_counts", json.dumps(list(recipe.group_counts)))
        coverage.insert(4, "residual_quantiles", json.dumps(list(recipe.residual_quantiles)))
        rows.append(coverage)
    return pd.concat(rows, ignore_index=True)
