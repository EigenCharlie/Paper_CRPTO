from __future__ import annotations

import pandas as pd

from scripts.search.run_portfolio_bound_exact_eval import (
    ROOT,
    _load_completed_bound_eval,
    _repo_relative,
    _shortlist_exact_path,
)


def test_load_completed_bound_eval_reuses_complete_cache(tmp_path) -> None:
    path = tmp_path / "bound_eval.parquet"
    expected = pd.DataFrame(
        {
            "alpha": [0.01, 0.03],
            "all_bounds_hold": [True, True],
            "gamma_cp": [0.18, 0.18],
            "weighted_miscoverage_V": [0.03, 0.03],
        }
    )
    expected.to_parquet(path, index=False)

    cached = _load_completed_bound_eval(bound_eval_path=path, expected_checks=2)

    assert cached is not None
    assert cached.equals(expected)


def test_load_completed_bound_eval_rejects_incomplete_cache(tmp_path) -> None:
    path = tmp_path / "bound_eval.parquet"
    pd.DataFrame(
        {
            "alpha": [0.01],
            "all_bounds_hold": [True],
            "gamma_cp": [0.18],
            "weighted_miscoverage_V": [0.03],
        }
    ).to_parquet(path, index=False)

    assert _load_completed_bound_eval(bound_eval_path=path, expected_checks=2) is None


def test_shortlist_exact_path_uses_explicit_output() -> None:
    expected = ROOT / "data" / "processed" / "portfolio_bound_aware_shortlist_exact.parquet"
    context = {
        "shortlist_path": str(
            ROOT / "data" / "processed" / "portfolio_bound_aware_shortlist.parquet"
        ),
        "shortlist_exact_path": str(expected),
    }

    assert _shortlist_exact_path(context) == expected


def test_repo_relative_keeps_artifact_paths_standalone() -> None:
    path = ROOT / "models" / "portfolio_bound_aware" / "selection.json"

    assert _repo_relative(path) == "models/portfolio_bound_aware/selection.json"
