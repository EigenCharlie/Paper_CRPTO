from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.build_ijds_calibration_selected_evidence import (
    build_baseline_table,
    build_bootstrap_table,
    build_grade_table,
)


def _allocations() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "role": ["calibration_selected", "calibration_selected", "point_pd_matched_tau"],
            "issue_d": ["2020-01-01", "2020-02-01", "2020-01-01"],
            "grade": ["A", "B", "A"],
            "funded_exposure": [100.0, 100.0, 200.0],
            "funded_weight": [0.5, 0.5, 1.0],
            "outcome": [0.0, 1.0, 0.0],
            "miscoverage": [0.0, 1.0, 0.0],
            "pd_point": [0.1, 0.2, 0.2],
            "pd_effective": [0.2, 0.3, 0.2],
            "pd_high": [0.4, 0.6, 0.8],
            "int_rate": [0.1, 0.2, 0.1],
            "realized_return_contribution": [10.0, -45.0, 20.0],
        }
    )


def _evaluation() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "period": "full_oot",
                "role": "calibration_selected",
                "n_panel": 10,
                "n_funded": 2,
                "total_allocated": 200.0,
                "expected_objective": 5.0,
                "realized_return": -35.0,
                "weighted_outcome": 0.5,
                "weighted_miscoverage": 0.5,
                "weighted_pd_point": 0.15,
                "weighted_pd_effective": 0.25,
                "gamma_cp": 0.35,
                "gamma_internalized": 0.10,
                "gamma_residual": 0.25,
                "endpoint_budget": 0.50,
                "markov_loss_threshold": 0.80,
            },
            {
                "period": "full_oot",
                "role": "point_pd_matched_tau",
                "n_panel": 10,
                "n_funded": 1,
                "total_allocated": 200.0,
                "expected_objective": 10.0,
                "realized_return": 20.0,
                "weighted_outcome": 0.0,
                "weighted_miscoverage": 0.0,
                "weighted_pd_point": 0.20,
                "weighted_pd_effective": 0.20,
                "gamma_cp": 0.60,
                "gamma_internalized": 0.0,
                "gamma_residual": 0.60,
                "endpoint_budget": 0.80,
                "markov_loss_threshold": 1.10,
            },
        ]
    )


def test_grade_table_preserves_selected_exposure() -> None:
    table = build_grade_table(_allocations())

    assert table["exposure"].sum() == 200.0
    assert table["exposure_share"].sum() == 1.0


def test_bootstrap_is_deterministic_and_uses_official_observed_values() -> None:
    first = build_bootstrap_table(_allocations(), _evaluation(), n_draws=100, seed=7)
    second = build_bootstrap_table(_allocations(), _evaluation(), n_draws=100, seed=7)

    pd.testing.assert_frame_equal(first, second)
    assert set(first["bootstrap_unit"]) == {"origination_month", "funded_loan"}
    observed = first.loc[first["bootstrap_unit"].eq("origination_month")].set_index("metric")[
        "observed"
    ]
    assert observed["realized_return"] == -35.0
    assert observed["Gamma_CP"] == 0.35


def test_bootstrap_rejects_allocation_evaluation_drift() -> None:
    evaluation = _evaluation()
    evaluation.loc[evaluation["role"].eq("calibration_selected"), "realized_return"] = 1.0

    with pytest.raises(ValueError, match="realized_return"):
        build_bootstrap_table(_allocations(), evaluation, n_draws=10, seed=7)


def test_baseline_table_uses_selected_policy_as_zero_delta() -> None:
    table = build_baseline_table(_evaluation())
    selected = table.loc[table["policy"].eq("Calibration-selected 50/50 CRPTO")].iloc[0]

    assert np.isclose(selected["return_delta_vs_selected"], 0.0)
    assert np.isclose(selected["default_delta_vs_selected"], 0.0)
