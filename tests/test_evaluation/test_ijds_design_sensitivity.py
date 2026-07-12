from __future__ import annotations

import numpy as np
import pandas as pd

from src.evaluation import ijds_design_sensitivity as sensitivity


def test_label_lag_sensitivity_reports_closed_grid(monkeypatch) -> None:
    scores = np.linspace(0.05, 0.95, 10)
    universe = pd.DataFrame(
        {
            "design_split": ["conformal_fit"] * 10,
            "loan_status": ["Fully Paid", "Charged Off"] * 5,
            "last_pymnt_d": ["Jan-2014"] * 10,
        }
    )
    features = pd.DataFrame({"score": scores})
    panel = pd.DataFrame(
        {
            "id": ["d1", "d2", "d3", "d4"],
            "issue_d": pd.to_datetime(["2016-04-01"] * 4),
            "design_split": ["primary_oot"] * 4,
            "pd_point": [0.1, 0.4, 0.6, 0.9],
            "conformal_group": [0, 0, 1, 1],
            "conformal_lower": [0.0] * 4,
            "conformal_upper": [1.0] * 4,
        }
    )
    outcomes = pd.DataFrame(
        {
            "id": ["d1", "d2", "d3", "d4"],
            "snapshot_default": pd.Series([0, 1, 0, 1], dtype="Int8"),
            "snapshot_resolution": ["fully_paid", "charged_off"] * 2,
        }
    )
    config = {
        "source": {"information_cutoff": "2016-03-31"},
        "conformal": {
            "alpha": 0.1,
            "canonical_groups": 2,
            "minimum_rows_per_group": 1,
            "method": "fixed_taxonomy_split_mondrian_absolute_residual",
        },
    }
    monkeypatch.setattr(
        sensitivity,
        "catboost_raw_margin",
        lambda _model, frame: frame["score"].to_numpy(dtype=float),
    )
    monkeypatch.setattr(
        sensitivity,
        "apply_platt_calibrator",
        lambda _calibrator, values: np.asarray(values, dtype=float),
    )

    result = sensitivity.build_label_lag_coverage_sensitivity(
        universe=universe,
        features=features,
        model=object(),
        calibrator=object(),
        fixed_edges=[0.0, 0.5, 1.0],
        decision_panel=panel,
        outcomes=outcomes,
        config=config,
        lag_months=[0, 3, 6, 12],
    )

    assert sorted(result["charged_off_lag_months"].unique().tolist()) == [0, 3, 6, 12]
    pooled = result.loc[
        result["period"].eq("2016-04_to_2016-04") & result["conformal_group"].eq("ALL")
    ]
    assert len(pooled) == 4
    assert pooled["conformal_fit_rows"].eq(10).all()
