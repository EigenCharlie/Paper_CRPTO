from __future__ import annotations

from pathlib import Path

import pytest

from scripts.experiments.run_tabprep_challenger import (
    _assert_isolated_output,
    _model_params,
)


def test_tabprep_output_guard_allows_only_experiment_roots() -> None:
    _assert_isolated_output(Path("models/experiments/tabprep/run/model.cbm"))
    _assert_isolated_output(Path("models/experiments/champion_search/run/model.cbm"))
    _assert_isolated_output(Path("data/processed/experiments/tabprep/run/predictions.parquet"))
    _assert_isolated_output(
        Path("data/processed/experiments/champion_search/run/predictions.parquet")
    )
    _assert_isolated_output(Path("reports/crpto/experiments/tabprep/run/audit.json"))
    _assert_isolated_output(Path("reports/crpto/experiments/champion_search/run/audit.json"))

    with pytest.raises(ValueError, match="protected CRPTO artifact"):
        _assert_isolated_output(Path("models/pd_canonical.cbm"))

    with pytest.raises(ValueError, match="outputs must stay"):
        _assert_isolated_output(Path("models/not_tabprep/model.cbm"))


def test_model_params_keep_monotone_constraints_only_for_existing_features() -> None:
    config = {
        "model": {
            "params": {
                "iterations": 10,
                "monotone_constraints": "installment:1,annual_inc:-1,dti:1",
                "feature_weights": {"installment": 1.5, "missing": 2.0},
            }
        },
        "tabprep": {"monotonic_constraints": {"loan_to_income": 1}},
    }

    params = _model_params(
        config,
        model_features=["installment", "annual_inc", "tp_ar__ratio__a__b"],
        seed=52,
    )

    assert params["random_seed"] == 52
    assert params["monotone_constraints"] == "(1,-1,0)"
    assert params["feature_weights"] == [1.5, 1.0, 1.0]
