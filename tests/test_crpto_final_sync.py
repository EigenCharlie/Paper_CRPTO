from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

EXPECTED_RUN_TAG = "paper-thesis-final-economic-2026-04-06"
EXPECTED_LABEL = "bound_aware_276k_economic_champion"
EXPECTED_RETURN = 170464.5429284627
EXPECTED_V = 0.03645
EXPECTED_GAMMA_CP = 0.18591
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
    assert registry_portfolio["selection_stage"] == "paper_thesis_final_economic_v1"

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
    for path in ["models/crpto_evidence_status.json", "models/crpto_journal_package_status.json"]:
        text = Path(path).read_text(encoding="utf-8").lower()
        assert not any(token in text for token in LEGACY_TOKENS)


def test_crpto_tables_and_figures_exist() -> None:
    required = [
        "reports/crpto/tables/crpto_table0_key_metrics.csv",
        "reports/crpto/tables/crpto_tableA7_funded_set_loans.csv",
        "reports/crpto/tables/crpto_tableA18_robust_region_policy_family.csv",
        "reports/crpto/figures/crpto_fig12_crpto_conceptual_pipeline.png",
        "reports/crpto/figures/crpto_fig14_robust_region_heatmap.png",
    ]
    for item in required:
        assert Path(item).exists(), item
