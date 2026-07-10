from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

EXPECTED_RUN_TAG = "ijds-rebaseline-2026-06-07"
EXPECTED_LABEL = "bound_aware_276k_economic_champion"
EXPECTED_RETURN = 170464.5429284627
EXPECTED_V = 0.028875
EXPECTED_GAMMA_CP = 0.187987
LEGACY_TOKENS = [
    "paper_" + "estrella",
    "paper-" + "estrella",
    "reports/paper_" + "material",
    "paper1" + "_table",
    "estrella" + "_fig",
]


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_key_metrics() -> dict[str, str]:
    with Path("reports/crpto/tables/crpto_table0_key_metrics.csv").open(encoding="utf-8") as handle:
        return {row["metric"]: row["value"] for row in csv.DictReader(handle)}


def test_crpto_champion_artifacts_agree() -> None:
    """Validate the historical frozen rebaseline chain (two-tag scheme).

    This run tag remains the frozen upstream provenance chain. The active
    manuscript policy is guarded by tests/test_ijds_active_claim_sync.py.
    """
    assert Path("data/processed/final_project_summary.parquet.dvc").exists()
    promotion = load_json("models/final_project_promotion.json")
    policy = load_json("models/champion_portfolio_policy.json")
    registry = load_json("models/champion_registry.json")
    metrics = load_json("reports/dvc/metrics_summary.json")
    table0 = load_key_metrics()

    champion = promotion["final_champion"]
    selected_policy = policy["selected_policy"]
    registry_portfolio = registry["portfolio"]

    assert promotion["run_tag"] == EXPECTED_RUN_TAG
    assert champion["label"] == EXPECTED_LABEL
    assert policy["run_tag"] == EXPECTED_RUN_TAG
    assert registry_portfolio["run_tag"] == EXPECTED_RUN_TAG
    assert registry_portfolio["selection_stage"] == "ijds_rebaseline_economic_v1"

    for field in ("risk_tolerance", "gamma", "uncertainty_aversion"):
        assert selected_policy[field] == pytest.approx(champion[field])
        assert registry_portfolio["selected_policy"][field] == pytest.approx(champion[field])
    assert selected_policy["policy_mode"] == champion["policy_mode"]
    assert registry_portfolio["selected_policy"]["policy_mode"] == champion["policy_mode"]

    assert champion["realized_total_return"] == pytest.approx(EXPECTED_RETURN)
    assert champion["alpha01_exact_pass"] is True
    assert champion["alpha01_weighted_miscoverage_V"] == pytest.approx(EXPECTED_V)
    assert champion["alpha01_gamma_cp"] == pytest.approx(EXPECTED_GAMMA_CP)

    assert metrics["crpto.final.robust_return"] == pytest.approx(EXPECTED_RETURN)
    assert metrics["crpto.final.alpha01_exact_pass"] == 1.0
    assert metrics["crpto.final.alpha01_weighted_miscoverage_V"] == pytest.approx(EXPECTED_V)
    assert metrics["crpto.final.alpha01_gamma_cp"] == pytest.approx(EXPECTED_GAMMA_CP)
    assert metrics["crpto.final.robust_region_n_policies"] == 45.0
    assert metrics["crpto.final.robust_region_alpha01_pass_rate"] == 1.0

    assert table0["run_tag"] == EXPECTED_RUN_TAG
    assert table0["champion_label"] == EXPECTED_LABEL
    assert float(table0["robust_return"]) == pytest.approx(EXPECTED_RETURN)
    assert table0["alpha01_exact_pass"] == "True"
    assert float(table0["alpha01_weighted_miscoverage_V"]) == pytest.approx(EXPECTED_V)
    assert float(table0["alpha01_gamma_cp"]) == pytest.approx(EXPECTED_GAMMA_CP)


def test_crpto_status_paths_are_sanitized() -> None:
    for path in [
        "models/crpto_evidence_status.json",
        "models/crpto_journal_package_status.json",
        "models/crpto_tail_constrained_reopt_status.json",
        "models/crpto_distribution_robustness_status.json",
    ]:
        text = Path(path).read_text(encoding="utf-8").lower()
        assert not any(token in text for token in LEGACY_TOKENS)


def test_crpto_tables_and_figures_exist() -> None:
    required = [
        "reports/crpto/tables/crpto_table0_key_metrics.csv",
        "reports/crpto/tables/crpto_tableA7_funded_set_loans.csv",
        "reports/crpto/tables/crpto_tableA18_robust_region_policy_family.csv",
        "reports/crpto/tables/crpto_tableA22_tail_constrained_reoptimization.csv",
        "reports/crpto/tables/crpto_tableA23_multidistribution_robustness.csv",
        "reports/crpto/tables/crpto_tableA24_online_conformal_stability.csv",
        "reports/crpto/tables/crpto_tableA35_exact_alpha_grid.csv",
        "reports/crpto/tables/crpto_tableA36_calibration_policy_selector.csv",
        "reports/crpto/tables/crpto_tableA37_calibration_selected_temporal_evaluation.csv",
        "reports/crpto/tables/crpto_tableA38_calibration_selected_grade_audit.csv",
        "reports/crpto/tables/crpto_tableA39_calibration_selected_bootstrap.csv",
        "reports/crpto/tables/crpto_tableA40_calibration_selected_point_baseline.csv",
        "reports/crpto/figures/crpto_fig1_journal_pipeline.png",
        "reports/crpto/figures/crpto_fig1_journal_pipeline.pdf",
        "reports/crpto/figures/crpto_fig1_journal_pipeline.svg",
        "book/assets/figures/publication/crpto_fig1_journal_pipeline.png",
        "book/assets/figures/publication/crpto_fig1_journal_pipeline.pdf",
        "book/assets/figures/publication/crpto_fig1_journal_pipeline.svg",
        "reports/crpto/figures/crpto_fig12_crpto_conceptual_pipeline.png",
        "reports/crpto/figures/crpto_fig15_regret_auditability_frontier.png",
        "reports/crpto/figures/crpto_fig20_bound_claim_layers.png",
    ]
    for item in required:
        assert Path(item).exists(), item
