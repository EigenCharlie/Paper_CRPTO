"""Tests for the frozen-score label-lag sensitivity."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.ijds_audit.lag_sensitivity import build_label_lag_phase_sensitivity
from src.models.binary_conformal_guardrail import fit_binary_outcome_recipe


def test_label_lag_sensitivity_preserves_frozen_taxonomy() -> None:
    score = np.linspace(0.02, 0.40, 20)
    outcome = np.array([0] * 16 + [1] * 4)
    frozen = fit_binary_outcome_recipe(
        score,
        outcome,
        alpha=0.10,
        n_groups=1,
        bin_edges=(0.0, 1.0),
        taxonomy_provenance="test",
        taxonomy_method="fixed_test",
    )
    universe = pd.DataFrame(
        {
            "loan_status": ["Fully Paid"] * 16 + ["Charged Off"] * 4,
            "last_pymnt_d": ["Jan-2012"] * 20,
            "design_split": ["conformal_fit"] * 20,
            "issue_d": pd.to_datetime(["2012-01-01"] * 20),
        }
    )
    config = {
        "source": {"information_cutoff": "2016-03-31"},
        "conformal": {"canonical_groups": 1, "alpha": 0.10},
        "lag_sensitivity": {
            "phase_stratum": 0,
            "minimum_monthly_label_retention": 0.99,
        },
        "residual_specification": {
            "windows": [{"id": "w01", "start": "2012-01-01", "end": "2012-06-30"}]
        },
    }
    result = build_label_lag_phase_sensitivity(
        universe,
        score,
        {"w01": {1: frozen}},
        config,
        lag_months=[0],
    )
    assert result.loc[0, "retained_rows"] == 20
    assert result.loc[0, "phase_prevalence"] == 0.20
    assert bool(result.loc[0, "passes_locked_retention"])
