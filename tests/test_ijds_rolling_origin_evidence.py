from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from scripts.build_ijds_rolling_origin_stability_evidence import (
    _contrast_rows,
    _resolved_policy_metrics,
)
from src.evaluation.policy_contrast_bounds import sharp_policy_contrast_bounds

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "reports/crpto/ijds_rolling_origin_stability_evidence.json"


def _evidence() -> dict[str, Any]:
    payload = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def test_rolling_origin_lineage_and_feasibility_are_locked() -> None:
    evidence = _evidence()
    assert evidence["status"] == "retrospective_prefreeze_rolling_origin_audit_evidence"
    assert evidence["protocol_tag"] == "protocol/ijds-rolling-origin-stability-2026-07-12-v2"
    assert evidence["protocol_commit"] == "9e689b2e3ca18aae5a2a967cc186da5dcd140891"
    assert evidence["design"]["declared_origins"] == [2015, 2016, 2017]
    assert evidence["feasibility"] == {
        "origin_2015": {
            "stage": "canonical_residual_group_size",
            "learner": "catboost_platt",
            "window_id": "w01_2011m01_m06",
            "taxonomy_groups": 5,
            "group_counts": [1648, 1408, 1166, 927, 619],
            "minimum_rows_per_group": 1000,
        },
        "threshold_relaxed": False,
        "outcome_join_performed": False,
    }
    assert evidence["claim_boundary"]["three_origin_stability"] is False


def test_feasible_origin_coverage_recurrence_is_exact_and_narrowly_scoped() -> None:
    coverage = _evidence()["coverage"]
    assert coverage["three_origin_stability_assessable"] is False
    assert coverage["both_feasible_origins_all_32_upper_bounds_below_nominal"] is True
    summaries = {(row["origin"], row["learner"]): row for row in coverage["summaries"]}
    assert summaries[(2016, "catboost_platt")]["candidate_rows"] == 74537
    assert summaries[(2016, "catboost_platt")]["unresolved_rows"] == 0
    assert summaries[(2016, "catboost_platt")]["coverage_resolved_min"] == pytest.approx(
        0.8608610488750553
    )
    assert summaries[(2016, "numeric_logistic_platt")]["coverage_upper_max"] == pytest.approx(
        0.8886190750902236
    )
    assert summaries[(2017, "catboost_platt")]["candidate_rows"] == 77105
    assert summaries[(2017, "catboost_platt")]["unresolved_rows"] == 10888
    assert summaries[(2017, "catboost_platt")]["coverage_upper_max"] == pytest.approx(
        0.8762466766098178
    )
    assert summaries[(2017, "numeric_logistic_platt")]["coverage_upper_max"] == pytest.approx(
        0.8774009467609104
    )
    assert len(coverage["rows"]) == 32


def test_portfolio_direction_remains_unidentified_in_both_feasible_origins() -> None:
    portfolio = _evidence()["portfolio"]
    assert portfolio["common_2016_contrasts"] == 221040
    assert portfolio["envelopes_per_origin"] == 648
    assert portfolio["every_scope_metric_lacks_one_direction_in_all_cells"] is True
    development = {
        (row["origin"], row["metric"], row["direction"]): row["cells"]
        for row in portfolio["direction_counts"]
        if row["scope"] == "development_admissible_exact_frontier"
    }
    assert development == {
        (2016, "funded_miscoverage", "crosses_zero"): 10,
        (2016, "funded_miscoverage", "guardrail_higher"): 54,
        (2016, "funded_miscoverage", "guardrail_lower"): 8,
        (2016, "standardized_payoff", "crosses_zero"): 32,
        (2016, "standardized_payoff", "guardrail_higher"): 8,
        (2016, "standardized_payoff", "guardrail_lower"): 32,
        (2016, "terminal_default", "crosses_zero"): 42,
        (2016, "terminal_default", "guardrail_higher"): 23,
        (2016, "terminal_default", "guardrail_lower"): 7,
        (2017, "funded_miscoverage", "crosses_zero"): 56,
        (2017, "funded_miscoverage", "guardrail_higher"): 16,
        (2017, "standardized_payoff", "crosses_zero"): 72,
        (2017, "terminal_default", "crosses_zero"): 64,
        (2017, "terminal_default", "guardrail_higher"): 8,
    }
    c2 = {row["origin"]: row for row in portfolio["c2"]}
    assert c2[2016]["cells"] == c2[2017]["cells"] == 216
    assert c2[2016]["point_minus_guardrail_objective_min"] >= -1e-5
    assert c2[2017]["point_minus_guardrail_objective_min"] > 0.0
    assert c2[2016]["c2_match_residual_abs_max"] < 1e-16
    assert c2[2017]["c2_match_residual_abs_max"] < 1e-16


def test_inherited_simulation_is_decision_degenerate() -> None:
    simulation = _evidence()["simulation"]
    assert simulation["repetitions"] == 19200
    assert simulation["cells"] == 192
    assert simulation["guardrail_cap_binding_repetitions"] == 0
    assert simulation["minimum_guardrail_cap_slack"] == pytest.approx(0.0004992314849223689)
    assert simulation["same_cap_nonzero_allocation_repetitions"] == 2
    assert simulation["c2_nonzero_allocation_repetitions"] == 1
    assert simulation["portfolio_claim_allowed"] is False


def test_evidence_hashes_frozen_inputs_and_derived_artifacts() -> None:
    evidence = _evidence()
    for descriptor in (
        *evidence["source_artifacts"].values(),
        *evidence["derived_artifacts"].values(),
    ):
        path = ROOT / descriptor["path"]
        assert path.is_file(), path
        assert path.stat().st_size == descriptor["bytes"]
        assert _sha256(path) == descriptor["sha256"]


def test_historical_implementation_descriptors_remain_well_formed() -> None:
    evidence = _evidence()
    for descriptor in evidence["aggregation_implementation"].values():
        path = ROOT / descriptor["path"]
        fingerprint = descriptor["sha256"]
        assert path.is_file(), path
        assert descriptor["bytes"] > 0
        assert len(fingerprint) == 64
        assert set(fingerprint) <= set("0123456789abcdef")


def test_resolved_vector_aggregation_matches_original_sharp_bound() -> None:
    rows = [
        ("a", "guardrail_p1", "guardrail", 60.0, 0.10, 0.0, 0.0, 0.8),
        ("b", "guardrail_p1", "guardrail", 40.0, 0.18, 1.0, 0.2, 1.0),
        ("a", "c0_same_numeric_cap_p1", "c0_same_numeric_cap", 25.0, 0.10, 0.0, 0.0, 0.8),
        ("c", "c0_same_numeric_cap_p1", "c0_same_numeric_cap", 75.0, 0.15, 0.0, 0.1, 0.9),
    ]
    allocations = pd.DataFrame(
        rows,
        columns=[
            "id",
            "policy_label",
            "comparator_rule",
            "exposure",
            "contractual_rate",
            "snapshot_default",
            "conformal_lower",
            "conformal_upper",
        ],
    ).assign(
        window_id="w01_test",
        paired_policy_id="p1",
        frontier_cap=0.1,
        role="primary_oot",
        expected_payoff_contribution=0.0,
    )
    metrics = _resolved_policy_metrics(allocations, lgd=0.45)
    guardrail = metrics.loc[metrics["comparator_rule"].eq("guardrail")]
    comparator = metrics.loc[metrics["comparator_rule"].eq("c0_same_numeric_cap")]
    vector = _contrast_rows(guardrail, comparator).iloc[0]
    direct = sharp_policy_contrast_bounds(
        allocations,
        policy_a="guardrail_p1",
        policy_b="c0_same_numeric_cap_p1",
        role="primary_oot",
        lgd=0.45,
    )
    for field in (
        "realized_payoff_difference_lower",
        "realized_payoff_difference_upper",
        "weighted_default_difference_lower",
        "weighted_default_difference_upper",
        "weighted_miscoverage_difference_lower",
        "weighted_miscoverage_difference_upper",
    ):
        assert vector[field] == pytest.approx(direct[field], abs=1e-12)
