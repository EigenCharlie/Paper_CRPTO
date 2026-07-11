"""Drift guards for the post hoc comparator-stringency evidence bundle."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
TABLES = REPO / "reports/crpto/tables"
EVIDENCE = REPO / "reports/crpto/ijds_comparator_stringency_evidence.json"
RUN_TAG = "champion-reopen-2026-07-10__maturity-safe-v2-comparator-stringency-audit-v1"
PROTOCOL_TAG = "protocol/ijds-maturity-safe-v2-comparator-stringency-audit-2026-07-10-v1"
PROTOCOL_COMMIT = "ca632ccfbbfaec0e6cdf482a279468665cdb62c0"


def _json(path: Path) -> dict[str, Any]:
    assert path.is_file(), path
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(stem: str) -> list[dict[str, str]]:
    with (TABLES / f"{stem}.csv").open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def test_comparator_evidence_is_bound_to_clean_posthoc_protocol() -> None:
    evidence = _json(EVIDENCE)
    summary = _json(REPO / evidence["summary"]["path"])
    receipt = _json(REPO / evidence["receipt"]["path"])

    assert evidence["status"] == "active_posthoc_comparator_stringency_evidence"
    assert evidence["run_tag"] == RUN_TAG
    assert evidence["protocol_tag"] == PROTOCOL_TAG
    assert evidence["protocol_commit"] == PROTOCOL_COMMIT
    assert evidence["posthoc_diagnostic_after_active_results"] is True
    assert summary["status"] == "complete"
    assert summary["posthoc_diagnostic_after_active_results"] is True
    assert summary["protected_stages_run"] == []
    assert summary["protected_artifacts_written"] == []
    assert receipt["initial_git"]["commit"] == PROTOCOL_COMMIT
    assert receipt["final_git"]["commit"] == PROTOCOL_COMMIT
    assert receipt["initial_git"]["dirty"] is False
    assert receipt["final_git"]["dirty"] is False
    assert _sha256(REPO / evidence["summary"]["path"]) == evidence["summary"]["sha256"]
    assert _sha256(REPO / evidence["receipt"]["path"]) == evidence["receipt"]["sha256"]


def test_same_threshold_and_development_matched_conclusions_invert() -> None:
    rows = _rows("crpto_ijds_cs_table2_primary_inversion")
    same = next(row for row in rows if row["baseline"] == "same_threshold_point_pd")
    matched = next(row for row in rows if row["baseline"] == "development_matched_point_pd")

    assert float(same["baseline_risk_cap_slack"]) == pytest.approx(0.054241790967)
    assert float(same["realized_payoff_difference_upper"]) < 0.0
    assert float(same["weighted_default_difference_upper"]) < 0.0
    assert float(same["weighted_miscoverage_difference_lower"]) > 0.0

    assert float(matched["baseline_risk_tolerance"]) == pytest.approx(0.068313398932)
    assert float(matched["baseline_risk_cap_slack"]) == pytest.approx(0.0, abs=1e-12)
    assert float(matched["expected_payoff_difference"]) == pytest.approx(8479.178169)
    assert float(matched["realized_payoff_difference_lower"]) == pytest.approx(-506587.033840)
    assert float(matched["realized_payoff_difference_upper"]) == pytest.approx(-295967.166488)
    assert float(matched["weighted_default_difference_lower"]) == pytest.approx(0.034430728841)
    assert float(matched["weighted_default_difference_upper"]) == pytest.approx(0.056287022189)
    assert float(matched["weighted_miscoverage_difference_lower"]) == pytest.approx(0.027093262550)
    assert float(matched["weighted_miscoverage_difference_upper"]) == pytest.approx(0.046282889231)


def test_selected_sensitivity_and_leave_one_month_out_are_sign_robust() -> None:
    sensitivity = _rows("crpto_ijds_cs_tableS3_selected_sensitivity")
    for baseline in (
        "development_matched_point_pd_low",
        "development_matched_point_pd",
        "development_matched_point_pd_high",
    ):
        row = next(item for item in sensitivity if item["policy_b"] == baseline)
        assert float(row["realized_payoff_difference_upper"]) < 0.0
        assert float(row["weighted_default_difference_lower"]) > 0.0
        assert float(row["weighted_miscoverage_difference_lower"]) > 0.0

    leave_one_out = _rows("crpto_ijds_cs_tableS4_primary_leave_one_month_out")
    matched = [row for row in leave_one_out if row["policy_b"] == "development_matched_point_pd"]
    assert len(matched) == 15
    assert all(float(row["realized_payoff_difference_upper"]) < 0.0 for row in matched)
    assert all(float(row["weighted_default_difference_lower"]) > 0.0 for row in matched)
    assert all(float(row["weighted_miscoverage_difference_lower"]) > 0.0 for row in matched)


def test_family_census_reports_heterogeneity_without_reselection() -> None:
    evidence = _json(EVIDENCE)
    headline = evidence["headline"]["family_census"]
    rows = _rows("crpto_ijds_cs_table3_family_census")

    assert len(rows) == 9
    assert headline["pairs"] == 9
    assert headline["payoff_guardrail_worse"] == 7
    assert headline["default_guardrail_worse"] == 7
    assert headline["miscoverage_guardrail_worse"] == 9
    assert headline["all_three_guardrail_worse"] == 7
    assert headline["family_direction_claim_allowed"] is False
    ambiguous = {
        row["candidate_id"]
        for row in rows
        if row["payoff_guardrail_worse"] == "False" or row["default_guardrail_worse"] == "False"
    }
    assert ambiguous == {"linear-003", "linear-006"}


def test_comparator_manifest_hashes_all_publication_outputs() -> None:
    evidence = _json(EVIDENCE)
    paths = {item["path"] for item in evidence["outputs"]}
    required_tables = {
        "crpto_ijds_cs_table1_baseline_alignment",
        "crpto_ijds_cs_table2_primary_inversion",
        "crpto_ijds_cs_table3_family_census",
        *{
            f"crpto_ijds_cs_tableS{index}_{suffix}"
            for index, suffix in (
                (1, "matched_thresholds"),
                (2, "development_aggregates"),
                (3, "selected_sensitivity"),
                (4, "primary_leave_one_month_out"),
                (5, "selector_leave_one_month_out"),
                (6, "payoff_decomposition"),
                (7, "lgd_break_even"),
                (8, "score_geometry"),
                (9, "transport"),
                (10, "group_exposure"),
                (11, "monthly_contrasts"),
                (12, "extension"),
            )
        },
    }
    for stem in required_tables:
        assert f"reports/crpto/tables/{stem}.csv" in paths
        assert f"reports/crpto/tables/{stem}.tex" in paths
    for index, suffix in (
        (1, "alignment"),
        (2, "selected_contrasts"),
        (3, "family"),
        (4, "monthly"),
    ):
        stem = f"reports/crpto/figures/crpto_ijds_cs_fig{index}_{suffix}"
        assert f"{stem}.png" in paths
        assert f"{stem}.pdf" in paths
    for item in evidence["outputs"]:
        path = REPO / item["path"]
        assert path.is_file(), path
        assert path.stat().st_size == item["bytes"]
        assert _sha256(path) == item["sha256"]
