from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.experiments.run_tabprep_feature_selection_catboost import (
    _build_case_features,
    _rank_pool_features,
)
from src.features.feature_engineering import TARGET


def _ranking_frame(n_rows: int = 80) -> pd.DataFrame:
    dti = np.linspace(3.0, 35.0, n_rows)
    fico = np.linspace(760.0, 620.0, n_rows)
    grade = np.where(dti > 22.0, "C", "A")
    target = ((dti > 20.0) | (grade == "C")).astype(int)
    target[np.arange(n_rows) % 7 == 0] = 0
    return pd.DataFrame(
        {
            "dti": dti,
            "fico_score": fico,
            "grade": grade,
            "noise": np.resize([0.1, 0.2, 0.3, 0.4], n_rows),
            TARGET: target,
        }
    )


def test_pooltop_cases_fail_when_pool_ranking_is_empty() -> None:
    with pytest.raises(ValueError, match="requested top 42 pool features"):
        _build_case_features(
            cases=["pooltop42_tab20"],
            core_features=["dti"],
            catboost_features=["dti", "fico_score"],
            pool_features=["dti", "fico_score"],
            pool_ranking=[],
            woe_features=[],
            generated_ranking=[f"tp_feature_{idx}" for idx in range(20)],
            business_ranking=[f"tp_feature_{idx}" for idx in range(20)],
        )


def test_pool_feature_ranking_falls_back_when_selector_has_no_pool_scores() -> None:
    frame = _ranking_frame()
    train_fit = frame.iloc[:50].copy()
    train_val = frame.iloc[50:].copy()

    ranking, diagnostics = _rank_pool_features(
        pool_features=["dti", "fico_score", "grade", "noise"],
        selector_scores={},
        train_fit=train_fit,
        train_val=train_val,
        categorical_features=["grade"],
    )

    assert ranking
    assert {"feature", "ranking_score", "ranking_source", "iv", "psi_fit_to_val"}.issubset(
        diagnostics.columns
    )
    assert diagnostics["ranking_source"].eq("fallback_univariate").all()
    assert set(ranking[:3]).intersection({"dti", "fico_score", "grade"})


def test_pool_feature_ranking_blends_selector_scores_when_present() -> None:
    frame = _ranking_frame()
    train_fit = frame.iloc[:50].copy()
    train_val = frame.iloc[50:].copy()

    ranking, diagnostics = _rank_pool_features(
        pool_features=["dti", "fico_score", "grade", "noise"],
        selector_scores={"noise": 100.0},
        train_fit=train_fit,
        train_val=train_val,
        categorical_features=["grade"],
    )

    assert ranking[0] == "noise"
    assert diagnostics.loc[diagnostics["feature"] == "noise", "ranking_source"].iloc[0] == (
        "selector_blend"
    )
