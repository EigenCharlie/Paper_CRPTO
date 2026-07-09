from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.generate_governance_status import (
    GovernanceOutputPaths,
    GovernanceThresholds,
    _build_explanation_drift_report,
    _build_governance_status,
    _drift_breach_metrics,
)


def _test_thresholds() -> GovernanceThresholds:
    return GovernanceThresholds(
        psi_threshold=0.25,
        ks_pvalue_min=0.01,
        cvm_pvalue_min=0.01,
        c2st_auc_max=0.60,
        max_feature_breach_ratio=0.60,
        c2st_max_rows=50_000,
        score_psi_max=0.15,
        auc_delta_max=0.05,
        brier_increase_max=0.02,
        calibration_gap_delta_max=0.02,
        performance_max_rows=100_000,
        min_rank_overlap_top10=0.60,
        max_explanation_shap_psi=0.25,
        min_reason_code_stability=0.55,
        explanation_min_rows_per_slice=80,
        psi_bins=10,
        random_state=42,
    )


def _test_paths() -> GovernanceOutputPaths:
    return GovernanceOutputPaths(
        drift_path=Path("data/processed/drift_monitoring.parquet"),
        status_path=Path("models/governance_status.json"),
        explanation_drift_path=Path("data/processed/explanation_drift.parquet"),
        fairness_status_path=Path("models/fairness_audit_status.json"),
        fairness_frontier_path=Path("data/processed/fairness_threshold_frontier.parquet"),
        challenger_report_path=Path("models/challenger_promotion_report.json"),
        model_shift_status_path=Path("models/model_shift_status.json"),
    )


def test_build_explanation_drift_report_emits_overall_and_grade_rows() -> None:
    rows: list[dict[str, object]] = []
    periods = ["2020Q1", "2020Q2", "2020Q3"]
    for period in periods:
        for grade in ["A", "B"]:
            for idx in range(20):
                rows.append(
                    {
                        "issue_quarter": period,
                        "grade": grade,
                        "pd_calibrated": 0.20,
                        "shap_dti": 0.30 + 0.001 * idx,
                        "shap_income": 0.10 + 0.001 * idx,
                    }
                )
    shap_raw = pd.DataFrame(rows)

    report = _build_explanation_drift_report(
        shap_raw,
        primary_threshold=0.50,
        min_rank_overlap_top10=0.50,
        max_shap_psi=10.0,
        min_reason_code_stability=0.50,
        min_rows_per_slice=20,
    )

    assert set(report["segment_type"]) == {"overall", "grade"}
    assert set(report["segment"]) == {"all", "A", "B"}
    assert set(report["comparison_period"]) == {"2020Q3"}
    assert report["passed_all"].all()
    assert np.isfinite(report["max_shap_psi_top5"]).all()

    details = json.loads(str(report.loc[report["segment"] == "all", "feature_psi_details"].iloc[0]))
    assert {row["feature"] for row in details} == {"dti", "income"}


def test_governance_status_helpers_preserve_public_contract() -> None:
    thresholds = _test_thresholds()
    drift_df = pd.DataFrame(
        {
            "pass_psi": [True, False],
            "pass_ks": [True, True],
            "pass_cvm": [True, False],
            "psi": [0.05, 0.20],
            "ks_pvalue": [0.50, 0.40],
            "cvm_pvalue": [0.60, 0.30],
            "feature": ["a", "b"],
        }
    )
    c2st = {
        "c2st_auc": 0.55,
        "materiality": "moderate",
        "effective_driver_count": 1,
        "top_drivers": ["a"],
        "n_rows": 100,
    }
    performance = {
        "score_psi": 0.10,
        "auc_delta_train_to_test": 0.02,
        "brier_increase_train_to_test": 0.01,
        "calibration_gap_delta": 0.01,
    }
    metrics = _drift_breach_metrics(drift_df, c2st, performance, thresholds)
    explanation_drift = pd.DataFrame(
        {
            "passed_all": [True],
            "pass_reason_code_stability": [True],
            "rank_overlap_top10": [0.80],
            "max_shap_psi_top5": [0.10],
            "reason_code_match_rate": [0.90],
        }
    )
    status = _build_governance_status(
        config_path="configs/mrm_policy.yaml",
        resolved_run_tag="test-run",
        paths=_test_paths(),
        thresholds=thresholds,
        drift_df=drift_df,
        explanation_drift=explanation_drift,
        fairness_status={"overall_pass": True, "primary_threshold": 0.42},
        challenger_report={"challenger_promotable": True},
        metrics=metrics,
        model_shift={"shift_type": "stable", "governance_posture": "monitor"},
    )

    assert metrics["psi_breaches"] == 1
    assert metrics["pass_predictive_drift"] is True
    assert status["overall_pass"] is True
    assert status["checks"]["pass_explainability"] is True
    assert status["summary"]["fairness_primary_threshold"] == 0.42
    assert status["summary"]["challenger_promotable"] is True
    assert Path(status["artifacts"]["model_shift_status_path"]) == Path(
        "models/model_shift_status.json"
    )


def test_build_explanation_drift_report_requires_enough_recent_rows() -> None:
    shap_raw = pd.DataFrame(
        {
            "issue_quarter": ["2020Q1", "2020Q2"],
            "pd_calibrated": [0.20, 0.20],
            "shap_dti": [0.1, 0.2],
        }
    )

    report = _build_explanation_drift_report(
        shap_raw,
        primary_threshold=0.50,
        min_rank_overlap_top10=0.50,
        max_shap_psi=10.0,
        min_reason_code_stability=0.50,
        min_rows_per_slice=20,
    )

    assert report.empty
