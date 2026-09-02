"""Sync hand-authored supplement summaries to active IJDS evidence tables."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

from src.ijds_audit.publication_schemas import S6B_PUBLICATION_COLUMNS

REPO = Path(__file__).resolve().parents[1]
TABLES = REPO / "reports/crpto/tables"
BODY = REPO / "paper/CRPTO_ijds.qmd"
SUPPLEMENT = REPO / "paper/supplement_ijds.qmd"
IJDS_CSS = REPO / "paper/ijds.css"


def _rows(name: str) -> list[dict[str, str]]:
    with (TABLES / name).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def test_wide_prose_tables_keep_the_pdf_overlap_mitigation() -> None:
    supplement = SUPPLEMENT.read_text(encoding="utf-8")
    css = IJDS_CSS.read_text(encoding="utf-8")
    wrapped_blocks = re.findall(
        r"^::: \{\.wide-prose-table\}\s*(.*?)^:::\s*$",
        supplement,
        flags=re.MULTILINE | re.DOTALL,
    )

    required_captions = (
        "**Table S12A.**",
        "**Table S12B.**",
        "**Table S12C.**",
        "**Table S13B, Panel A.**",
        "**Table S13B, Panel B.**",
    )
    for caption in required_captions:
        assert supplement.count(caption) == 1
        assert any(caption in block for block in wrapped_blocks)

    assert "**Table S12, Panel" not in supplement
    assert ".supplement-ijds .wide-prose-table table" in css
    assert "table-layout: fixed !important;" in css
    assert "width: 100% !important;" in css
    assert ".supplement-ijds .wide-prose-table td" in css
    assert "overflow-wrap: anywhere;" in css
    assert "white-space: normal !important;" in css


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
        for field in (
            "fit_rows",
            "fit_default_rows",
            "finite_sample_rank",
            "finite_phase_allowance",
        ):
            assert f"{int(row[field]):,}" in supplement
        assert f"{float(row['phase_boundary_rate']):.6f}" in supplement
        assert f"{int(row['phase_margin']):+d}" in supplement
    by_window = {row["window_id"]: row for row in rows}
    w7 = by_window["w07_2012m07_m12"]
    w8 = by_window["w08_2012m08_2013m01"]
    assert (int(w7["fit_default_rows"]), int(w7["finite_sample_rank"])) == (603, 5337)
    assert (int(w7["finite_phase_allowance"]), int(w7["phase_margin"])) == (592, 11)
    assert (int(w8["fit_default_rows"]), int(w8["finite_sample_rank"])) == (606, 5616)
    assert (int(w8["finite_phase_allowance"]), int(w8["phase_margin"])) == (622, -16)
    for token in ("5,337", "5,616", "0.099848", "0.099711", "+11", "-16"):
        assert token in supplement


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


def test_calibrator_tables_are_complete_and_pooled_rows_match_the_supplement() -> None:
    fit = _rows("crpto_ijds_v4_tableS2C_calibrator_fit_diagnostics.csv")
    cells = _rows("crpto_ijds_v4_tableS6O_calibrator_sensitivity_cells.csv")
    pairwise = _rows("crpto_ijds_v4_tableS6P_calibrator_pairwise_shared_completion.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")

    labels = {
        "platt": "Platt",
        "isotonic": "Isotonic",
        "beta": "Beta (`abm`)",
        "venn_abers": "IVAP Venn--Abers scalar",
    }
    assert len(fit) == 4
    assert {row["method"] for row in fit} == set(labels)
    assert {row["same_sample_descriptive_only"] for row in fit} == {"True"}
    assert {row["selection_metric"] for row in fit} == {"False"}
    for row in fit:
        gap = (
            f"{float(row['venn_multiprobability_gap_mean']):.6f}"
            if row["venn_multiprobability_gap_mean"]
            else "--"
        )
        expected = (
            f"| {labels[row['method']]} | {int(row['rows']):,} | "
            f"{float(row['roc_auc']):.6f} | {float(row['brier']):.6f} | "
            f"{float(row['log_loss']):.6f} | {float(row['ece_10']):.6f} | {gap} |"
        )
        assert expected in supplement

    assert len(cells) == 192
    overall = [row for row in cells if row["conformal_group"] == "-1"]
    assert len(overall) == 32
    assert sum(row["coverage_upper_below_nominal"] == "True" for row in overall) == 18
    assert sum(row["coverage_upper_below_nominal"] == "False" for row in overall) == 14
    for row in overall:
        window = f"W{int(row['window_id'][1:3])}"
        expected = (
            f"| {labels[row['method']]} | {window} | "
            f"{float(row['coverage_resolved']):.6f} | "
            f"[{float(row['coverage_lower']):.6f}, {float(row['coverage_upper']):.6f}] | "
            f"{float(row['average_set_size']):.6f} | "
            f"{float(row['set_empty_share']):.6f} | "
            f"{float(row['set_both_share']):.6f} |"
        )
        assert expected in supplement

    assert len(pairwise) == 288
    assert {row["shared_loanwise_completion"] for row in pairwise} == {"True"}
    assert (
        len(
            {
                (
                    row["method_a"],
                    row["method_b"],
                    row["window_id"],
                    row["conformal_group"],
                )
                for row in pairwise
            }
        )
        == 288
    )
    forbidden = ("allocation", "portfolio", "objective", "net_return")
    assert not any(
        token in column.lower()
        for rows in (fit, cells, pairwise)
        for column in rows[0]
        for token in forbidden
    )


def test_binary_phase_target_support_table_is_complete_and_matches_the_supplement() -> None:
    rows = _rows("crpto_ijds_v4_tableS6Q_binary_phase_target_support.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")

    assert len(rows) == 200
    assert len({(row["learner"], row["window_id"], row["conformal_group"]) for row in rows}) == 200
    excluded = [
        row for row in rows if row["positive_label_excluded_from_every_target_set"] == "True"
    ]
    assert len(excluded) == 87
    assert [
        sum(
            row["positive_label_excluded_from_every_target_set"] == "True"
            for row in rows
            if row["conformal_group"] == str(group)
        )
        for group in range(5)
    ] == [40, 40, 7, 0, 0]
    assert all(
        float(row["target_score_max"]) < float(row["positive_label_boundary"])
        and row["threshold_below_half"] == "True"
        for row in excluded
    )
    learner_window_rows = {(row["learner"], row["window_id"]): row for row in rows}
    fractions = [
        float(row["exclusion_strata_resolved_miss_fraction"])
        for row in learner_window_rows.values()
    ]
    assert min(fractions) == pytest.approx(0.2397794701677335)
    assert max(fractions) == pytest.approx(0.5845764027953737)
    assert "**Table S6Q.**" in supplement
    assert "**87** | **87** | **87**" in supplement
    assert "23.98%--58.46%" in supplement


def test_calibrator_body_summary_and_named_pairwise_ranges_are_derived() -> None:
    cells = _rows("crpto_ijds_v4_tableS6O_calibrator_sensitivity_cells.csv")
    pairwise = _rows("crpto_ijds_v4_tableS6P_calibrator_pairwise_shared_completion.csv")
    body = BODY.read_text(encoding="utf-8")
    supplement = _normalize(SUPPLEMENT.read_text(encoding="utf-8"))
    overall = [row for row in cells if row["conformal_group"] == "-1"]
    labels = {
        "platt": "Platt",
        "isotonic": "Isotonic",
        "beta": "Beta (`abm`)",
        "venn_abers": "IVAP Venn--Abers scalar",
    }

    for method, label in labels.items():
        rows = [row for row in overall if row["method"] == method]
        assert len(rows) == 8
        below = sum(row["coverage_upper_below_nominal"] == "True" for row in rows)
        expected = (
            f"| {label} | {below}/8 | "
            f"{min(float(row['coverage_lower']) for row in rows):.6f} | "
            f"{max(float(row['coverage_upper']) for row in rows):.6f} | "
            f"{min(float(row['coverage_resolved']) for row in rows):.6f}--"
            f"{max(float(row['coverage_resolved']) for row in rows):.6f} | "
            f"{min(float(row['average_set_size']) for row in rows):.6f}--"
            f"{max(float(row['average_set_size']) for row in rows):.6f} |"
        )
        assert expected in body

    pooled_pairs = [row for row in pairwise if row["conformal_group"] == "-1"]

    def oriented_bounds(method_a: str, method_b: str) -> tuple[float, float]:
        direct = [
            row
            for row in pooled_pairs
            if row["method_a"] == method_a and row["method_b"] == method_b
        ]
        if direct:
            return (
                min(float(row["coverage_difference_lower"]) for row in direct),
                max(float(row["coverage_difference_upper"]) for row in direct),
            )
        reverse = [
            row
            for row in pooled_pairs
            if row["method_a"] == method_b and row["method_b"] == method_a
        ]
        assert reverse
        return (
            -max(float(row["coverage_difference_upper"]) for row in reverse),
            -min(float(row["coverage_difference_lower"]) for row in reverse),
        )

    named = {
        ("isotonic", "platt"): "isotonic-minus-platt",
        ("venn_abers", "platt"): "ivap-minus-platt",
        ("isotonic", "venn_abers"): "isotonic-minus-ivap",
    }
    for pair, normalized_label in named.items():
        lower, upper = oriented_bounds(*pair)
        assert lower > 0.0
        assert upper > 0.0
        assert f"{lower:.6f}" in supplement
        assert f"{upper:.6f}" in supplement
        assert normalized_label in supplement
        if pair != ("isotonic", "venn_abers"):
            assert f"{lower:.6f}--{upper:.6f}" in body

    zero = [row for row in pairwise if row["method_a"] == "platt" and row["method_b"] == "beta"]
    assert len(zero) == 48
    assert all(
        float(row[column]) == 0.0
        for row in zero
        for column in (
            "coverage_difference_resolved",
            "coverage_difference_lower",
            "coverage_difference_upper",
        )
    )


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
    body = BODY.read_text(encoding="utf-8")
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

    table_start = body.index("| Ruler / coordinate |")
    table_end = body.index("\n\n: Six protocol-locked path-end tracks", table_start)
    body_table_lines = body[table_start:table_end].splitlines()
    assert len(body_table_lines[2:]) == 6
    ruler_labels = {
        "objective_matched": "Objective matched",
        "normalized_score": "Normalized score",
    }
    for row in rows:
        coordinate = f"{float(row['coordinate']):.2f}".removeprefix("0")
        expected = (
            f"| {ruler_labels[row['ruler']]} {coordinate} "
            f"| [{float(row['payoff_bound_usd_lower_min']):,.2f}, "
            f"{float(row['payoff_bound_usd_upper_max']):,.2f}] "
            f"| [{float(row['default_bound_pp_lower_min']):.4f}, "
            f"{float(row['default_bound_pp_upper_max']):.4f}] "
            f"| [{float(row['miscoverage_bound_pp_lower_min']):.4f}, "
            f"{float(row['miscoverage_bound_pp_upper_max']):.4f}] |"
        )
        assert expected in body_table_lines

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
    assert "fit-label-by-outcome-availability combinations had been evaluated" in normalized
    assert "active six-month result remains the declared outcome-availability" in normalized


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
    assert "share of the 1,440 path-end portfolios per scenario" in normalized
    assert "baseline scenario reproduces the active two-ruler bounds exactly" in normalized


def test_endpoint_reason_missingness_and_second_origin_tables_are_visible() -> None:
    endpoint = _rows("crpto_ijds_v4_tableS8_endpoint_resolution.csv")
    missingness = _rows("crpto_ijds_v4_tableS9_missingness_encoding_sensitivity.csv")
    rolling = _rows("crpto_ijds_v4_tableS7C_rolling_origin_recurrence.csv")
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
    assert {row["origin_id"] for row in rolling} == {"primary_2016", "rolling_2017"}
    assert {(row["origin_id"], row["window"]) for row in rolling} == {
        (origin, f"W{window}")
        for origin in ("primary_2016", "rolling_2017")
        for window in range(1, 9)
    }
    assert {
        (row["candidate_rows"], row["resolved_rows"], row["unresolved_rows"])
        for row in rolling
        if row["origin_id"] == "primary_2016"
    } == {("74537", "73934", "603")}
    assert {
        (row["candidate_rows"], row["resolved_rows"], row["unresolved_rows"])
        for row in rolling
        if row["origin_id"] == "rolling_2017"
    } == {("77105", "66037", "11068")}
    assert not any(
        int(row["candidate_rows"]) == 376890
        for row in rolling
        if row["origin_id"] == "primary_2016"
    )
    assert {int(row["individual_followup_months"]) for row in rolling} == {39}
    assert {
        (row["origin_id"], row["evaluation_cutoff_min"], row["evaluation_cutoff_max"])
        for row in rolling
    } == {
        ("primary_2016", "2019-07-31", "2019-09-30"),
        ("rolling_2017", "2020-07-31", "2020-09-30"),
    }
    for row in rolling:
        assert f"{float(row['coverage_lower']):.6f}" in supplement
        assert f"{float(row['coverage_upper']):.6f}" in supplement

    normalized = re.sub(r"\s+", " ", supplement.lower())
    assert "not an independent replication" in normalized
    assert "does not identify a missingness mechanism" in normalized


def test_complete_conformal_set_diagnostic_is_visible_and_bounded() -> None:
    rows = _rows("crpto_ijds_v4_tableS6A_conformal_set_diagnostics.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")
    assert len(rows) == 40
    assert len({row["learner"] for row in rows}) == 5
    assert len({row["window_id"] for row in rows}) == 8
    assert all(
        float(row["coverage_resolved_y0"]) > float(row["coverage_resolved_y1"]) for row in rows
    )
    for row in rows:
        for column in (
            "coverage_resolved_y0",
            "coverage_resolved_y1",
            "average_set_size",
            "singleton_share",
            "set_empty_share",
            "set_zero_only_share",
            "set_one_only_share",
            "set_both_share",
        ):
            assert f"{float(row[column]):.6f}" in supplement
    normalized = re.sub(r"\s+", " ", supplement.lower())
    assert "condition on administrative resolution" in normalized
    assert "does not estimate all-candidate label-conditional validity" in normalized
    assert "fairness result" in normalized


def test_closed_taxonomies_and_censored_extension_are_visible_and_scoped() -> None:
    taxonomies = _rows("crpto_ijds_v4_tableS6G_taxonomy_diagnostics.csv")
    extension = _rows("crpto_ijds_v4_tableS6H_censored_extension_coverage.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")
    normalized = _normalize(supplement)

    assert len(taxonomies) == 64
    assert {int(row["taxonomy_groups"]) for row in taxonomies} == {1, 2, 5, 10}
    assert {row["learner"] for row in taxonomies} == {
        "catboost_platt",
        "numeric_logistic_platt",
    }
    assert all(float(row["coverage_upper"]) < 0.90 for row in taxonomies)
    grouped: dict[tuple[str, int], list[dict[str, str]]] = {}
    for row in taxonomies:
        grouped.setdefault((row["learner"], int(row["taxonomy_groups"])), []).append(row)
    assert all(len(rows) == 8 for rows in grouped.values())
    for rows in grouped.values():
        assert f"{min(float(row['coverage_lower']) for row in rows):.6f}" in supplement
        assert f"{max(float(row['coverage_upper']) for row in rows):.6f}" in supplement

    assert len(extension) == 16
    assert {row["learner"] for row in extension} == {
        "catboost_platt",
        "numeric_logistic_platt",
    }
    assert {int(row["candidate_rows"]) for row in extension} == {88_227}
    assert {int(row["resolved_rows"]) for row in extension} == {59_291}
    assert {int(row["unresolved_rows"]) for row in extension} == {28_936}
    assert {int(row["taxonomy_groups"]) for row in extension} == {5}
    assert {row["role"] for row in extension} == {"censored_extension"}
    for count in (88_227, 59_291, 28_936):
        assert f"{count:,}" in supplement
    extension_by_learner: dict[str, list[dict[str, str]]] = {}
    for row in extension:
        extension_by_learner.setdefault(row["learner"], []).append(row)
    for rows in extension_by_learner.values():
        assert f"{min(float(row['coverage_lower']) for row in rows):.6f}" in supplement
        assert f"{max(float(row['coverage_upper']) for row in rows):.6f}" in supplement
    below = {
        learner: sum(
            float(row["coverage_upper"]) < 0.90 for row in extension if row["learner"] == learner
        )
        for learner in {row["learner"] for row in extension}
    }
    assert below == {"catboost_platt": 8, "numeric_logistic_platt": 2}
    catboost_rows = sorted(extension_by_learner["catboost_platt"], key=lambda row: row["window_id"])
    logistic_rows = sorted(
        extension_by_learner["numeric_logistic_platt"],
        key=lambda row: row["window_id"],
    )
    assert all(float(row["coverage_upper"]) < 0.90 for row in catboost_rows)
    assert [float(row["coverage_upper"]) < 0.90 for row in logistic_rows] == [
        False,
        False,
        False,
        False,
        False,
        False,
        True,
        True,
    ]
    assert [
        float(row["coverage_lower"]) <= 0.90 <= float(row["coverage_upper"])
        for row in logistic_rows
    ] == [True, True, True, True, True, True, False, False]
    for token in (
        "no alternative taxonomy is selected",
        "joint-block rank-reference result is not extended",
        "highly unresolved extension",
        "not primary oot evidence",
        "independent replication",
        "not a conformal-theorem or exchangeability test",
        "w1--w6",
        "w7--w8",
    ):
        assert token in normalized


def test_exact_exchangeability_tables_are_complete_and_scoped() -> None:
    cells = _rows("crpto_ijds_v4_tableS6B_exchangeability_cells.csv")
    strata = _rows("crpto_ijds_v4_tableS6C_exchangeability_strata.csv")
    supplement = _normalize(SUPPLEMENT.read_text(encoding="utf-8"))

    assert len(cells) == 40
    assert tuple(cells[0]) == S6B_PUBLICATION_COLUMNS
    assert len(strata) == 200
    assert len({row["learner"] for row in cells}) == 5
    assert len({row["window"] for row in cells}) == 8
    assert sum(row["meets_locked_nominal_holm_threshold"] == "True" for row in cells) == 31
    flagged = {
        learner: [
            row["window"]
            for row in cells
            if row["learner"] == learner and row["meets_locked_nominal_holm_threshold"] == "True"
        ]
        for learner in {row["learner"] for row in cells}
    }
    assert flagged == {
        "catboost_platt": [f"W{index}" for index in range(1, 9)],
        "numeric_logistic_platt": [f"W{index}" for index in range(5, 9)],
        "catboost_monotonic_platt": [f"W{index}" for index in range(1, 9)],
        "woe_scorecard_platform_platt": [f"W{index}" for index in range(3, 9)],
        "woe_scorecard_borrower_platt": [f"W{index}" for index in range(4, 9)],
    }
    assert {int(row["score_stratum"]) for row in strata} == {1, 2, 3, 4, 5}
    assert all(row["continuous_threshold_tie_singleton"] == "True" for row in strata)
    assert all(int(row["resolved_target_residual_equal_threshold"]) == 0 for row in strata)
    for token in (
        "beta--binomial",
        "bonferroni",
        "holm",
        "31 of 40",
        "joint block-exchangeability",
        "post-inspection",
        "post-selection",
        "exchangeability established by nonflag",
    ):
        assert token in supplement


def test_label_mondrian_tables_are_complete_and_bounded() -> None:
    cells = _rows("crpto_ijds_v4_tableS6D_label_mondrian_cells.csv")
    strata = _rows("crpto_ijds_v4_tableS6E_label_mondrian_strata.csv")
    categories = _rows("crpto_ijds_v4_tableS6F_label_mondrian_categories.csv")
    supplement = _normalize(SUPPLEMENT.read_text(encoding="utf-8"))

    assert len(cells) == 40
    assert len(strata) == 200
    assert len(categories) == 400
    assert sum(row["identification_state_at_nominal"] == "robust_shortfall" for row in cells) == 27
    assert sum(row["identification_state_at_nominal"] == "crosses_nominal" for row in cells) == 12
    assert (
        sum(row["identification_state_at_nominal"] == "robust_at_or_above_nominal" for row in cells)
        == 1
    )
    assert (
        sum(row["identification_state_at_nominal"] == "robust_shortfall" for row in categories)
        == 109
    )
    assert all(float(row["set_empty_share"]) == 0.0 for row in cells)
    assert all(
        float(row["coverage_gap_y0_minus_y1_lower"])
        <= 0
        <= float(row["coverage_gap_y0_minus_y1_upper"])
        for row in cells
    )
    for token in (
        "label-mondrian",
        "27",
        "109",
        "400",
        "shared by both class ratios",
        "restored exchangeability",
    ):
        assert token in supplement


def test_individual_age_endpoint_census_is_complete() -> None:
    census = _rows("crpto_ijds_v4_tableS7D_individual_age_endpoint_census.csv")
    supplement = _normalize(SUPPLEMENT.read_text(encoding="utf-8"))

    assert len(census) == 6
    assert {row["origin_id"] for row in census} == {"primary_2016", "rolling_2017"}
    assert {int(row["individual_followup_months"]) for row in census} == {39}
    assert {(row["period"], row["individual_evaluation_cutoff"]) for row in census} == {
        ("2016-04", "2019-07-31"),
        ("2016-05", "2019-08-31"),
        ("2016-06", "2019-09-30"),
        ("2017-04", "2020-07-31"),
        ("2017-05", "2020-08-31"),
        ("2017-06", "2020-09-30"),
    }
    for origin, expected in {
        "primary_2016": (74537, 73934, 603),
        "rolling_2017": (77105, 66037, 11068),
    }.items():
        scoped = [row for row in census if row["origin_id"] == origin]
        assert sum(int(row["candidate_rows"]) for row in scoped) == expected[0]
        assert sum(int(row["resolved_rows"]) for row in scoped) == expected[1]
        assert sum(int(row["unresolved_rows"]) for row in scoped) == expected[2]
    for row in census:
        assert sum(
            int(row[field])
            for field in (
                "charged_off_by_reconstructed_cutoff",
                "fully_paid_by_reconstructed_cutoff",
                "nonterminal_or_unresolved_status",
                "terminal_after_reconstructed_cutoff",
                "terminal_availability_date_missing",
            )
        ) == int(row["candidate_rows"])
    for token in (
        "individual-age",
        "39-month",
        "2019-07-31",
        "2019-08-31",
        "2019-09-30",
        "2020-07-31",
        "2020-08-31",
        "2020-09-30",
    ):
        assert token in supplement


def test_fit_completion_and_allocation_granularity_tables_are_visible() -> None:
    fit = _rows("crpto_ijds_v4_tableS11_fit_label_completion.csv")
    granularity = _rows("crpto_ijds_v4_tableS12_allocation_granularity.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")

    assert len(fit) == 4
    assert sum(row["w7_w8_stratum2_crossing"] == "True" for row in fit) == 3
    for row in fit:
        assert f"{float(row['coverage_lower_min']):.6f}" in supplement
        assert f"{float(row['coverage_upper_max']):.6f}" in supplement

    assert len(granularity) == 1
    row = granularity[0]
    assert int(row["portfolios"]) == 1440
    assert int(row["changed_rows"]) == 2985
    assert f"{float(row['default_rate_perturbation_abs_max']):.9f}" in supplement

    normalized = re.sub(r"\s+", " ", supplement.lower())
    assert "declared stresses rather than sharp bounds" in normalized
    assert "does not establish adequacy or optimality of the continuous relaxation" in normalized
