from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from optbinning import BinningProcess
from sklearn.linear_model import LogisticRegression

from src.ijds_audit.config import load_credit_control_config
from src.ijds_audit.credit_controls import WOELogisticModel, scorecard_binning_table

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/experiments/ijds_credit_risk_controls_2026-07-13_v1.yaml"


def test_credit_control_config_is_closed_and_uses_all_rows() -> None:
    config = load_credit_control_config(CONFIG)
    controls = config["credit_risk_controls"]

    assert controls["selection_from_oot"] is False
    assert controls["portfolio_optimization"] is False
    assert controls["sampling"] == "none_all_eligible_rows"
    assert len(controls["co_primary_models"]) == 5
    assert not set(controls["platform_signal_features"]).intersection(
        controls["scorecards"]["borrower"]["features"]
    )


def test_credit_control_config_rejects_platform_signal_in_borrower_scorecard(
    tmp_path: Path,
) -> None:
    payload = CONFIG.read_text(encoding="utf-8").replace(
        'extends: "ijds_binary_geometry_frontier_v4_2026-07-12.yaml"',
        f'extends: "{(CONFIG.parent / "ijds_binary_geometry_frontier_v4_2026-07-12.yaml").as_posix()}"',
    )
    payload = payload.replace(
        '    borrower:\n      name: "woe_scorecard_borrower_platt"\n      features:',
        '    borrower:\n      name: "woe_scorecard_borrower_platt"\n      features:\n        - "int_rate"',
    )
    path = tmp_path / "invalid.yaml"
    path.write_text(payload, encoding="utf-8")

    with pytest.raises(ValueError, match="borrower scorecard"):
        load_credit_control_config(path)


def test_woe_model_handles_unknown_missing_and_parquet_serialization(tmp_path: Path) -> None:
    generator = np.random.default_rng(7)
    features = pd.DataFrame(
        {
            "numeric": generator.normal(size=400),
            "category": generator.choice(["a", "b", "c"], size=400),
        }
    )
    labels = (
        features["numeric"]
        + features["category"].eq("c").astype(float) * 0.8
        + generator.normal(size=400)
        > 0
    ).astype(int)
    process = BinningProcess(
        ["numeric", "category"],
        categorical_variables=["category"],
        min_n_bins=2,
        max_n_bins=5,
        min_bin_size=0.05,
        n_jobs=1,
    ).fit(features, labels)
    transformed = process.transform(
        features,
        metric="woe",
        metric_missing=0,
        metric_special=0,
    )
    estimator = LogisticRegression(max_iter=1000).fit(transformed, labels)
    model = WOELogisticModel(
        name="synthetic",
        features=("numeric", "category"),
        categorical_features=("category",),
        binning_process=process,
        logistic_regression=estimator,
    )
    restored = pickle.loads(pickle.dumps(model))
    probe = pd.DataFrame(
        {
            "numeric": [0.0, np.nan],
            "category": ["unseen", None],
        }
    )

    probabilities = restored.predict_proba(probe)
    assert probabilities.shape == (2, 2)
    assert np.isfinite(probabilities).all()
    assert np.allclose(probabilities.sum(axis=1), 1.0)
    binning_table = scorecard_binning_table(restored)
    binning_table.to_parquet(tmp_path / "woe_binning_table.parquet", index=False)
    assert pd.api.types.is_numeric_dtype(binning_table["WoE"])
