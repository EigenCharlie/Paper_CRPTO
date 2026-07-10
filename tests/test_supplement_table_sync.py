"""Sync active supplement mechanism tables to generated CSV evidence."""

from __future__ import annotations

import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TABLES = REPO / "reports/crpto/tables"
SUPPLEMENT = REPO / "paper/supplement_ijds.qmd"
PAPER = REPO / "paper/CRPTO_ijds.qmd"


def _rows(name: str) -> list[dict[str, str]]:
    with (TABLES / name).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_group_exposure_values_are_visible_in_body_and_supplement() -> None:
    rows = _rows("crpto_ijds_ms_tableS5_group_exposure.csv")
    body = PAPER.read_text(encoding="utf-8")
    supplement = SUPPLEMENT.read_text(encoding="utf-8").lower()
    for policy, group in (("selected_conformal_guardrail", "0"), ("matched_point_pd", "0")):
        row = next(
            item
            for item in rows
            if item["policy_label"] == policy and item["conformal_group"] == group
        )
        token = f"{float(row['exposure_share']):.6f}"
        assert token in body
        assert token in supplement


def test_transport_mechanism_values_are_visible_in_supplement() -> None:
    rows = _rows("crpto_ijds_ms_tableS4_transport.csv")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")
    selected = next(
        row
        for row in rows
        if row["policy_label"] == "selected_conformal_guardrail"
        and row["metric"] == "binary_miscoverage"
        and row["completion"] == "lower"
    )
    for field in ("group_composition", "within_group_selection", "funded_exposure_weighted"):
        assert f"{float(selected[field]):.6f}" in supplement


def test_development_to_oot_reversal_is_visible_in_body_and_supplement() -> None:
    rows = _rows("crpto_ijds_ms_table4_development_to_oot.csv")
    development = next(row for row in rows if row["block"] == "policy_development_2012H2")
    realized = f"{float(development['realized_payoff_difference_lower']):,.2f}"
    expected = f"{abs(float(development['expected_payoff_difference'])):,.2f}"
    for path in (PAPER, SUPPLEMENT):
        text = path.read_text(encoding="utf-8").lower()
        assert realized in text
        assert expected in text
        assert "development-to-oot" in text


def test_extension_is_reported_as_bounded_stress_not_active_promotion() -> None:
    rows = _rows("crpto_ijds_ms_tableS6_extension.csv")
    guard = next(row for row in rows if row["policy_label"] == "selected_conformal_guardrail")
    supplement = SUPPLEMENT.read_text(encoding="utf-8").lower()
    assert f"{float(guard['unresolved_exposure_share']):.6f}" in supplement
    assert "stress evidence only" in supplement
    assert "no directional promotion claim" in supplement


def test_historical_external_work_is_firewalled() -> None:
    supplement = SUPPLEMENT.read_text(encoding="utf-8")
    for token in ("OCE/CVaR", "SPO+", "Prosper", "Freddie/Mendeley", "A25--A34"):
        assert token in supplement
    assert "historical diagnostics" in supplement
    assert "differ from the active maturity-safe protocol" in supplement
