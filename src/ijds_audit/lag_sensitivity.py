"""Outcome-label lag sensitivity for frozen scores and taxonomies."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from src.data.outcome_observability import build_outcome_label_availability
from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    apply_binary_outcome_recipe,
    fit_binary_outcome_recipe,
)


def build_label_lag_phase_sensitivity(
    universe: pd.DataFrame,
    probabilities: np.ndarray,
    frozen_recipes: Mapping[str, Mapping[int, BinaryOutcomeConformalRecipe]],
    config: Mapping[str, Any],
    *,
    lag_months: Sequence[int],
) -> pd.DataFrame:
    """Refit residual recipes only, preserving frozen scores and taxonomy edges."""
    if len(universe) != len(probabilities):
        raise ValueError("Universe and frozen probabilities must align row-for-row.")
    canonical_groups = int(config["conformal"]["canonical_groups"])
    phase_stratum = int(config["lag_sensitivity"]["phase_stratum"])
    if not 0 <= phase_stratum < canonical_groups:
        raise ValueError("Phase stratum is outside the canonical taxonomy.")
    conformal = universe["design_split"].eq("conformal_fit")
    cutoff = str(config["source"]["information_cutoff"])
    alpha = float(config["conformal"]["alpha"])
    threshold = float(config["lag_sensitivity"]["minimum_monthly_label_retention"])
    rows: list[dict[str, Any]] = []
    for lag in lag_months:
        labels = build_outcome_label_availability(
            universe["loan_status"],
            universe["last_pymnt_d"],
            cutoff=cutoff,
            charged_off_lag_months=int(lag),
        )
        available = labels["label_available"].astype(bool)
        conformal_frame = universe.loc[conformal, ["issue_d"]].copy()
        conformal_frame["label_available"] = available.loc[conformal].to_numpy()
        monthly_retention = (
            conformal_frame.assign(month=conformal_frame["issue_d"].dt.to_period("M"))
            .groupby("month", observed=True)["label_available"]
            .mean()
        )
        minimum_monthly_retention = float(monthly_retention.min())
        for specification in config["residual_specification"]["windows"]:
            window_id = str(specification["id"])
            window = universe["issue_d"].between(
                pd.Timestamp(specification["start"]),
                pd.Timestamp(specification["end"]),
            )
            eligible = conformal & window
            retained = eligible & available
            frozen = frozen_recipes[window_id][canonical_groups]
            score = probabilities[retained.to_numpy(dtype=bool)]
            outcome = labels.loc[retained, "terminal_outcome"].astype("int8").to_numpy(dtype=int)
            recipe = fit_binary_outcome_recipe(
                score,
                outcome,
                alpha=alpha,
                n_groups=canonical_groups,
                bin_edges=frozen.bin_edges,
                taxonomy_provenance=frozen.taxonomy_provenance,
                taxonomy_method=frozen.taxonomy_method,
                method=frozen.method,
            )
            assigned, lower, upper = apply_binary_outcome_recipe(score, recipe)
            phase = assigned == phase_stratum
            rows.append(
                {
                    "charged_off_lag_months": int(lag),
                    "window_id": window_id,
                    "window_rows": int(eligible.sum()),
                    "retained_rows": int(retained.sum()),
                    "window_retention": float(retained.sum() / eligible.sum()),
                    "minimum_monthly_retention": minimum_monthly_retention,
                    "passes_locked_retention": bool(minimum_monthly_retention > threshold),
                    "phase_stratum": phase_stratum,
                    "phase_rows": int(phase.sum()),
                    "phase_prevalence": float(outcome[phase].mean()),
                    "phase_residual_quantile": float(recipe.residual_quantiles[phase_stratum]),
                    "phase_interval_width_mean": float((upper[phase] - lower[phase]).mean()),
                    "phase_set_both_share": float(
                        np.mean((lower[phase] <= 0.0) & (upper[phase] >= 1.0))
                    ),
                }
            )
    return (
        pd.DataFrame(rows)
        .sort_values(["charged_off_lag_months", "window_id"], kind="stable")
        .reset_index(drop=True)
    )
