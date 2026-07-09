from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import run_crpto_vs_spo_stability as stability_mod


def test_crpto_vs_spo_stability_artifacts_exist() -> None:
    status_path = Path("data/processed/crpto_vs_spo_stability.json")
    assert status_path.exists()
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status.get("schema_version")
    assert Path("reports/crpto/figures/crpto_fig11_crpto_stability.png").exists()


def test_period_sample_seed_is_stable_and_distinct_by_period() -> None:
    seed = 42

    assert stability_mod._period_sample_seed(seed, "2018H1") == 100_042
    assert stability_mod._period_sample_seed(seed, "2018H1") == 100_042
    assert stability_mod._period_sample_seed(seed, "2020") == 500_042


def test_detail_rows_and_summary_payload_preserve_period_contract() -> None:
    periods = list(stability_mod.PERIODS)
    test = pd.DataFrame({"default_flag": [0, 1, 0, 1, 0]})
    period_masks = {
        period: np.array([idx == pos for idx in range(len(periods))])
        for pos, period in enumerate(periods)
    }
    regrets = stability_mod._init_period_regrets()
    regrets["2018H1"]["two_stage"] = [2.0, 4.0]
    regrets["2018H1"]["spo_plus"] = [1.0, 2.0]
    regrets["2018H1"]["conformal_robust"] = [3.0, float("nan")]
    coverage = {
        "2018H1": {
            "coverage_90": 0.91,
            "coverage_95": 0.96,
            "avg_width_90": 0.42,
            "min_grade_coverage_90": 0.89,
        }
    }

    rows = stability_mod._detail_rows(
        test=test,
        period_masks=period_masks,
        per_period_regrets=regrets,
        period_coverage=coverage,
    )
    summary = stability_mod._summary_payload(
        run_tag="run-test",
        args=Namespace(n_items=50, budget=15, n_train=800, epochs=50, seeds=2),
        n_features=3,
        feature_names=["a", "b", "c"],
        rows=rows,
        per_period_regrets=regrets,
        total_time=12.34,
    )

    first = rows[0]
    assert first["period"] == "2018H1"
    assert first["two_stage_mean_regret"] == 3.0
    assert first["spo_plus_mean_regret"] == 1.5
    assert first["conformal_robust_mean_regret"] == 3.0
    assert first["spo_improvement_pct"] == pytest.approx(49.999999983333336)
    assert summary["config"]["n_features"] == 3
    assert summary["per_period"]["2018H1"]["coverage_90"] == 0.91
    assert summary["per_period"]["2018H1"]["spo_improvement_vs_ts_pct"] == 50.0
    assert summary["stability_summary"]["coverage_always_above_target"] is True
