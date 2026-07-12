"""Sync hand-authored supplement summaries to active fixed-taxonomy evidence."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TABLES = REPO / "reports/crpto/tables"
SUPPLEMENT = REPO / "paper/supplement_ijds.qmd"


def _rows(name: str) -> list[dict[str, str]]:
    with (TABLES / name).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_primary_taxonomy_coverage_is_visible_in_supplement() -> None:
    rows = _rows("crpto_ijds_ft_table2_coverage.csv")
    primary = [row for row in rows if row["design_split"] == "primary_oot"]
    supplement = SUPPLEMENT.read_text(encoding="utf-8")

    assert {int(row["taxonomy_groups"]) for row in primary} == {1, 2, 5, 10}
    for row in primary:
        lower = f"{float(row['all_candidate_coverage_lower']):.6f}"
        upper = f"{float(row['all_candidate_coverage_upper']):.6f}"
        assert lower in supplement
        assert upper in supplement

    temporal = _rows("crpto_ijds_ft_tableS8_temporal_windows.csv")
    assert len(temporal) == 8
    for row in temporal:
        lower = f"{float(row['all_candidate_coverage_lower']):.6f}"
        upper = f"{float(row['all_candidate_coverage_upper']):.6f}"
        assert lower in supplement
        assert upper in supplement


def test_canonical_c2_policy_bounds_are_visible_in_supplement() -> None:
    rows = _rows("crpto_ijds_ft_table3_comparator_contrasts.csv")
    canonical = [row for row in rows if row["comparator_rule"] == "c2_contemporaneous"]
    supplement = SUPPLEMENT.read_text(encoding="utf-8")

    assert len(canonical) == 9
    for row in canonical:
        assert row["paired_policy_id"] in supplement
        payoff_lower = f"{abs(float(row['realized_payoff_difference_lower'])):,.0f}"
        miscoverage_upper = f"{float(row['weighted_miscoverage_difference_upper']):.6f}"
        assert payoff_lower in supplement
        assert miscoverage_upper in supplement

    late = _rows("crpto_ijds_ft_tableS13_late_c2_contrasts.csv")
    assert len(late) == 9
    for row in late:
        payoff_lower = f"{abs(float(row['realized_payoff_difference_lower'])):,.0f}"
        miscoverage_upper = f"{float(row['weighted_miscoverage_difference_upper']):.6f}"
        assert payoff_lower in supplement
        assert miscoverage_upper in supplement


def test_seed_cap_census_is_visible_in_supplement() -> None:
    rows = _rows("crpto_ijds_ft_tableS1_seed_cap_sensitivity.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")

    assert len(rows) == 180
    for metric, directions in {
        "payoff": (59, 37, 84),
        "default": (50, 33, 97),
        "miscoverage": (33, 64, 83),
    }.items():
        counts = tuple(
            sum(row[f"{metric}_direction"] == direction for row in rows)
            for direction in ("negative", "positive", "indeterminate")
        )
        assert counts == directions
        for count in counts:
            assert f"| {count} |" in supplement

    evidence = _rows("crpto_ijds_ft_tableS10_timing_directions.csv")
    assert len(evidence) == 18
    for count in (56, 36, 88, 51, 33, 96, 27, 85, 68):
        assert f"| {count} |" in supplement


def test_comparator_scope_and_lag_evidence_are_visible_in_supplement() -> None:
    supplement = SUPPLEMENT.read_text(encoding="utf-8")
    scopes = _rows("crpto_ijds_ft_tableS11_comparator_scopes.csv")
    envelopes = _rows("crpto_ijds_ft_tableS14_comparator_scope_envelopes.csv")
    lags = _rows("crpto_ijds_ft_tableS9_label_lags.csv")

    assert len(scopes) == 9
    assert len(envelopes) == 81
    assert {row["sign"] for row in envelopes} == {"indeterminate"}
    assert "0.0600--0.0825" in supplement
    for row in lags:
        assert f"{float(row['all_candidate_coverage_upper']):.6f}" in supplement


def test_simulation_transport_means_are_visible_in_supplement() -> None:
    rows = _rows("crpto_ijds_ft_tableS6_simulation.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")

    for shift in (0.0, 0.05, 0.10, 0.15):
        shifted = [row for row in rows if float(row["temporal_shift"]) == pytest.approx(shift)]
        metrics = {row["metric"]: float(row["mean"]) for row in shifted}
        for metric in (
            "calibration_coverage",
            "transported_coverage",
            "upper_endpoint_saturation",
            "taxonomy_allocation_l1",
            "guard_minus_same_cap_default",
            "guard_minus_matched_default",
        ):
            assert f"{metrics[metric]:.6f}" in supplement


def test_historical_policy_results_are_absent_from_supplement() -> None:
    supplement = SUPPLEMENT.read_text(encoding="utf-8").lower()
    for token in (
        "0.854923",
        "0.879692",
        "0.068313",
        "506,587.03",
        "295,967.17",
        "selected guardrail",
    ):
        assert token not in supplement
