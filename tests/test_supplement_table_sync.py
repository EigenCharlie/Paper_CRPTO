"""Sync hand-authored supplement summaries to active V4 evidence tables."""

from __future__ import annotations

import csv
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TABLES = REPO / "reports/crpto/tables"
SUPPLEMENT = REPO / "paper/supplement_ijds.qmd"


def _rows(name: str) -> list[dict[str, str]]:
    with (TABLES / name).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_all_primary_coverage_bounds_are_visible_in_supplement() -> None:
    rows = _rows("crpto_ijds_v4_table1_coverage_windows.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")

    assert len(rows) == 16
    assert {row["learner"] for row in rows} == {
        "catboost_platt",
        "numeric_logistic_platt",
    }
    for row in rows:
        assert f"{float(row['coverage_lower']):.6f}" in supplement
        assert f"{float(row['coverage_upper']):.6f}" in supplement
        assert f"{float(row['coverage_resolved']):.6f}" in supplement


def test_complete_phase_path_is_visible_in_supplement() -> None:
    rows = _rows("crpto_ijds_v4_table2_phase_transition.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")

    assert len(rows) == 8
    for row in rows:
        for field in ("fit_prevalence", "fit_residual_quantile", "mean_width"):
            assert f"{float(row[field]):.6f}" in supplement


def test_credit_control_metrics_and_shift_diagnostics_are_visible() -> None:
    controls = _rows("crpto_ijds_v4_table6_credit_controls.csv")
    woe = _rows("crpto_ijds_v4_tableS3_woe_iv_psi.csv")
    score_psi = _rows("crpto_ijds_v4_tableS4_score_psi.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")

    assert len(controls) == 5
    assert len(woe) == 45
    assert len(score_psi) == 25
    for row in controls:
        assert row["learner_label"] in supplement
        assert f"{float(row['roc_auc']):.6f}" in supplement
        assert f"{float(row['brier']):.6f}" in supplement
        assert f"{float(row['calibration_slope']):.6f}" in supplement
        assert f"{float(row['coverage_upper_max']):.6f}" in supplement

    top_iv = sorted(woe, key=lambda row: float(row["iv"]), reverse=True)[:5]
    for row in top_iv:
        assert row["feature"] in supplement
        assert f"{float(row['iv']):.6f}" in supplement
        assert f"{float(row['primary_oot_psi']):.6f}" in supplement

    primary_psi = [row for row in score_psi if row["comparison_role"] == "primary_oot"]
    assert len(primary_psi) == 5
    for row in primary_psi:
        assert f"{float(row['psi']):.6f}" in supplement


def test_named_and_exact_direction_counts_are_visible_in_supplement() -> None:
    named = _rows("crpto_ijds_v4_tableS1_named_comparators.csv")
    directions = _rows("crpto_ijds_v4_table4_direction_summary.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")

    assert len(named) == 9
    assert len(directions) == 5
    for row in named:
        for field in ("guardrail_lower", "crosses_zero", "guardrail_higher"):
            assert f"| {int(row[field])} |" in supplement
    labels = {
        "standardized_payoff": "Standardized payoff",
        "terminal_default": "Terminal default",
        "funded_miscoverage": "Funded miscoverage",
    }
    by_metric = {
        metric: {
            row["direction"]: int(row["cells"]) for row in directions if row["metric"] == metric
        }
        for metric in labels
    }
    for metric, label in labels.items():
        counts = by_metric[metric]
        lower = counts.get("guardrail_lower", 0)
        crossing = counts.get("crosses_zero", 0)
        higher = counts.get("guardrail_higher", 0)
        assert f"| {label} | {lower} | {crossing} | {higher} | 72 |" in supplement


def test_two_ruler_tracks_and_repeated_quarter_contrast_are_visible() -> None:
    rows = _rows("crpto_ijds_v4_table5_two_ruler_tracks.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")

    assert len(rows) == 6
    assert {(row["ruler"], float(row["coordinate"])) for row in rows} == {
        (ruler, coordinate)
        for ruler in ("objective_matched", "normalized_score")
        for coordinate in (0.25, 0.5, 0.75)
    }
    for row in rows:
        assert f"{float(row['payoff_bound_usd_lower_min']):,.2f}" in supplement
        assert f"{float(row['payoff_bound_usd_upper_max']):,.2f}" in supplement
        assert f"{float(row['default_bound_pp_lower_min']):.4f}" in supplement
        assert f"{float(row['default_bound_pp_upper_max']):.4f}" in supplement
    normalized = re.sub(r"\s+", " ", supplement.lower())
    assert "44 loan-month positions" in normalized
    assert "155,937.27" in normalized
    assert "one repeated allocation, not eight independent confirmations" in normalized
    assert "all three sharp intervals cross zero in all eight windows" in normalized
    assert "s9a endpoint-recovery direction reconciliation" in normalized
    assert "| 8 / 33 / 7 | 0 / 32 / 16 |" in normalized
    assert "| 8 / 33 / 7 | 0 / 33 / 15 |" in normalized
    assert "| 8 / 40 / 0 | 0 / 40 / 8 |" in normalized


def test_label_lag_sensitivity_is_visible_in_supplement() -> None:
    rows = _rows("crpto_ijds_v4_tableS5_label_lag_sensitivity.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")

    assert len(rows) == 40
    assert {int(row["charged_off_lag_months"]) for row in rows} == {0, 3, 6, 8, 12}
    scoped = [row for row in rows if row["window_id"].startswith(("w07_", "w08_"))]
    assert len(scoped) == 10
    for row in scoped:
        assert f"{float(row['phase_prevalence']):.6f}" in supplement
        assert f"{float(row['phase_residual_quantile']):.6f}" in supplement


def test_supplement_discloses_negative_simulation_and_recovery() -> None:
    supplement = re.sub(r"\s+", " ", SUPPLEMENT.read_text(encoding="utf-8").lower())

    assert "portfolio component is uninformative" in supplement
    assert "no portfolio claim uses this simulation" in supplement
    assert "no outcome evaluation artifact had been written" in supplement
    assert "changes no model" in supplement
