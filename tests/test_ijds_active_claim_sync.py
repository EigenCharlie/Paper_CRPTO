"""Drift guard for the active calibration-selected IJDS policy."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
TABLES = REPO / "reports/crpto/tables"
RUN_TAG = "champion-reopen-2026-06-19__pool93__ijds-calibration-selected-endpoint28-v7"
GOVERNANCE = (
    REPO / "models/experiments/champion_reopen" / RUN_TAG / "portfolio/ijds_policy_governance.json"
)
SUMMARY = GOVERNANCE.with_name("calibration_selected_policy_summary.json")
SURFACES = (
    REPO / "paper/CRPTO_ijds.qmd",
    REPO / "paper/supplement_ijds.qmd",
    REPO / "paper/submission/CRPTO_ijds_submission.tex",
)
TABLE_STEMS = (
    "crpto_tableA35_exact_alpha_grid",
    "crpto_tableA36_calibration_policy_selector",
    "crpto_tableA37_calibration_selected_temporal_evaluation",
    "crpto_tableA38_calibration_selected_grade_audit",
    "crpto_tableA39_calibration_selected_bootstrap",
    "crpto_tableA40_calibration_selected_point_baseline",
)


def _json(path: Path) -> dict[str, Any]:
    assert path.is_file(), f"Missing active governance: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(stem: str) -> list[dict[str, str]]:
    with (TABLES / f"{stem}.csv").open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _surface_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace(r"\$", "$").replace("{,}", ",")


def test_active_governance_locks_simple_policy_and_selector() -> None:
    payload = _json(GOVERNANCE)
    summary = _json(SUMMARY)
    policy = payload["selected_policy"]
    selector = payload["selection_protocol"]

    assert payload["status"] == "active_ijds_policy"
    assert payload["run_tag"] == RUN_TAG
    assert payload["generated_at_utc"] == summary["generated_at_utc"]
    assert policy["policy_mode"] == "blended_uncertainty"
    assert policy["risk_tolerance"] == pytest.approx(0.17)
    assert policy["gamma"] == pytest.approx(0.50)
    assert policy["uncertainty_aversion"] == pytest.approx(0.0)
    assert policy["min_budget_utilization"] == pytest.approx(0.0)
    assert selector["min_budget_utilization"] == pytest.approx(0.999)
    assert selector["n_total"] == 9
    assert selector["n_eligible"] == 5
    assert selector["outcome_columns_used"] == 0
    assert selector["statistical_assumption_columns_used"] == 0
    assert selector["endpoint_budget_cap"] == pytest.approx(0.28)
    assert selector["selector_forbidden_columns_present"] == []
    assert selector["calibration_metadata"]["target_alpha"] == pytest.approx(0.10)
    assert selector["calibration_metadata"]["selection_period"] == "2017-11"
    assert selector["calibration_metadata"]["selection_rows"] == 14943
    assert selector["calibration_metadata"]["audit_period"] == "2017-12"
    assert selector["calibration_metadata"]["audit_rows"] == 20695
    assert selector["calibration_metadata"]["outcomes_isolated_until_post_selection_audit"] is True
    assert "_outcome" not in selector["selector_input_columns"]
    assert selector["endpoint_cap_stability"]["cap_lower_inclusive"] == pytest.approx(
        0.25903604939435104
    )
    assert selector["endpoint_cap_stability"]["cap_upper_exclusive"] == pytest.approx(
        0.29049078888716334
    )
    assert selector["calibration_audit"]["same_policy_selected"] is True
    assert selector["calibration_audit"]["selected_policy"][
        "weighted_miscoverage"
    ] == pytest.approx(0.124925)
    assert payload["exact_alpha_reference_replay"]["pass"] is True


def test_active_tables_agree_with_governance() -> None:
    payload = _json(GOVERNANCE)
    full = payload["full_oot"]
    selected = next(
        row
        for row in _rows("crpto_tableA40_calibration_selected_point_baseline")
        if row["policy"] == "Calibration-selected 50/50 CRPTO"
    )
    alpha = next(
        row
        for row in _rows("crpto_tableA35_exact_alpha_grid")
        if row["selected_for_policy"] == "True"
    )

    assert float(selected["realized_return"]) == pytest.approx(full["realized_return"])
    assert float(selected["weighted_outcome"]) == pytest.approx(full["weighted_default_rate"])
    assert float(selected["weighted_miscoverage"]) == pytest.approx(full["weighted_miscoverage"])
    assert float(selected["endpoint_budget"]) == pytest.approx(full["endpoint_budget"])
    assert float(selected["markov_loss_threshold"]) == pytest.approx(full["markov_loss_threshold"])
    assert float(alpha["target_alpha"]) == pytest.approx(0.10)
    assert float(alpha["empirical_coverage"]) == pytest.approx(0.9348356081757077)


def test_active_a35_to_a40_exist_in_csv_and_tex() -> None:
    missing = [
        f"{stem}.{suffix}"
        for stem in TABLE_STEMS
        for suffix in ("csv", "tex")
        if not (TABLES / f"{stem}.{suffix}").is_file()
    ]
    assert not missing, "Missing active IJDS evidence: " + ", ".join(missing)


def test_active_manuscript_surfaces_share_numeric_anchors() -> None:
    payload = _json(GOVERNANCE)
    full = payload["full_oot"]
    contrast = payload["point_pd_contrast"]
    anchors = (
        f"${full['realized_return']:,.2f}",
        f"{full['weighted_default_rate']:.6f}",
        f"{full['weighted_miscoverage']:.6f}",
        f"{full['Gamma_CP']:.6f}",
        f"{full['Gamma_residual']:.6f}",
        f"{full['endpoint_budget']:.6f}",
        f"{full['observed_accounting_bound']:.6f}",
        f"{full['markov_loss_threshold']:.6f}",
        f"{contrast['realized_return']:,.2f}",
        f"{100 * contrast['selected_return_cost_pct']:.3f}",
        f"{100 * contrast['selected_default_reduction']:.4f}",
        "0.28",
        "0.124925",
        "$163,421.14",
    )
    for surface in SURFACES:
        text = _surface_text(surface)
        missing = [anchor for anchor in anchors if anchor not in text]
        assert not missing, f"{surface.name} missing active anchors: {missing}"


def test_retired_headline_numbers_do_not_appear_in_active_surfaces() -> None:
    retired = ("0.345084", "50,010", "27,508", "capped_blended_uncertainty")
    for surface in SURFACES:
        text = _surface_text(surface)
        present = [token for token in retired if token in text]
        assert not present, f"{surface.name} retains retired claims: {present}"
