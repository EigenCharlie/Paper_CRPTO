"""Sync hand-authored supplement summaries to active IJDS evidence tables."""

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
        "standardized_payoff": "Status-indexed payoff proxy",
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
        assert f"{float(row['payoff_identification_width_usd_min']):,.0f}" in supplement
        assert f"{float(row['payoff_identification_width_usd_max']):,.0f}" in supplement
    normalized = re.sub(r"\s+", " ", supplement.lower())
    assert "44 loan-month positions" in normalized
    assert "155,937.27" in normalized
    assert "one repeated allocation, not eight independent confirmations" in normalized
    assert "all three sharp intervals cross zero in all eight windows" in normalized
    assert "exact identification-width ranges" in normalized
    assert "endpoint-recovery direction reconciliation" not in normalized


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


def test_endpoint_availability_grid_is_visible_and_kept_separate() -> None:
    rows = _rows("crpto_ijds_v4_tableS6_endpoint_availability_sensitivity.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")

    assert len(rows) == 5
    assert {int(row["charged_off_lag_months"]) for row in rows} == {0, 3, 6, 8, 12}
    for row in rows:
        lag = int(row["charged_off_lag_months"])
        resolved = int(row["primary_resolved"])
        unresolved = int(row["primary_unresolved"])
        below = int(row["coverage_upper_below_0_90_cells"])
        maximum = float(row["coverage_upper_max"])
        payoff_lower = int(row["two_ruler_payoff_gamma_1_lower_cells"])
        payoff_cross = int(row["two_ruler_payoff_crosses_zero_cells"])
        default_higher = int(row["two_ruler_default_gamma_1_higher_cells"])
        default_cross = int(row["two_ruler_default_crosses_zero_cells"])
        miscoverage_higher = int(row["two_ruler_miscoverage_gamma_1_higher_cells"])
        miscoverage_cross = int(row["two_ruler_miscoverage_crosses_zero_cells"])
        expected = (
            f"| {lag} | {resolved:,} / {unresolved:,} | {below} / 40 | {maximum:.6f} | "
            f"{payoff_lower} / {payoff_cross} | {default_higher} / {default_cross} | "
            f"{miscoverage_higher} / {miscoverage_cross} |"
        )
        assert expected in supplement

    normalized = re.sub(r"\s+", " ", supplement.lower())
    assert "fit-label-by-endpoint combinations had been evaluated" in normalized
    assert "active six-month result remains the declared endpoint" in normalized


def test_complete_portfolio_structure_grid_is_visible_in_supplement() -> None:
    rows = _rows("crpto_ijds_v4_tableS7_portfolio_structure_sensitivity.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")

    assert len(rows) == 36
    assert {float(row["budget"]) for row in rows} == {500_000.0, 1_000_000.0, 2_000_000.0}
    assert {float(row["purpose_cap"]) for row in rows} == {0.2, 0.25, 0.3, 1.0}
    assert {float(row["lgd"]) for row in rows} == {0.25, 0.45, 0.65}
    assert {int(row["activity_portfolios"]) for row in rows} == {1440}
    assert {float(row["activity_frontier_constraint_binding_share"]) for row in rows} == {1.0}
    for row in rows:
        payoff = "/".join(
            row[column]
            for column in (
                "standardized_payoff_gamma_1_lower_cells",
                "standardized_payoff_gamma_1_higher_cells",
                "standardized_payoff_crosses_zero_cells",
                "standardized_payoff_exact_zero_cells",
            )
        )
        default = "/".join(
            row[column]
            for column in (
                "funded_default_gamma_1_higher_cells",
                "funded_default_gamma_1_lower_cells",
                "funded_default_crosses_zero_cells",
                "funded_default_exact_zero_cells",
            )
        )
        miscoverage = "/".join(
            row[column]
            for column in (
                "funded_binary_miscoverage_gamma_1_higher_cells",
                "funded_binary_miscoverage_gamma_1_lower_cells",
                "funded_binary_miscoverage_crosses_zero_cells",
                "funded_binary_miscoverage_exact_zero_cells",
            )
        )
        expected = (
            f"| {float(row['budget']) / 1_000_000:.1f} | "
            f"{float(row['purpose_cap']):.2f} | {float(row['lgd']):.2f} | "
            f"{payoff} | {default} | {miscoverage} | "
            f"{float(row['activity_purpose_cap_binding_share']):.0%} |"
        )
        assert expected in supplement

    normalized = re.sub(r"\s+", " ", supplement.lower())
    assert "zero scenarios are favorable on all three metrics" in normalized
    assert "zero are adverse on all three metrics" in normalized
    assert "share of the 1,440 portfolios" in normalized
    assert "baseline scenario reproduces the active two-ruler bounds exactly" in normalized


def test_endpoint_reason_missingness_and_second_origin_tables_are_visible() -> None:
    endpoint = _rows("crpto_ijds_v4_tableS8_endpoint_resolution.csv")
    missingness = _rows("crpto_ijds_v4_tableS9_missingness_encoding_sensitivity.csv")
    rolling = _rows("crpto_ijds_v4_tableS10_rolling_origin_recurrence.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")

    assert len(endpoint) == 5
    assert sum(int(row["candidate_rows"]) for row in endpoint) == 376890
    for row in endpoint:
        assert f"{int(row['candidate_rows']):,}" in supplement

    assert len(missingness) == 3
    for row in missingness:
        assert f"{float(row['roc_auc']):.6f}" in supplement
        assert f"{float(row['coverage_upper_max']):.6f}" in supplement

    assert len(rolling) == 16
    assert {row["origin"] for row in rolling} == {"primary_2016", "rolling_2017"}
    for row in rolling:
        assert f"{float(row['coverage_lower']):.6f}" in supplement
        assert f"{float(row['coverage_upper']):.6f}" in supplement

    normalized = re.sub(r"\s+", " ", supplement.lower())
    assert "not an independent replication" in normalized
    assert "does not identify a missingness mechanism" in normalized
