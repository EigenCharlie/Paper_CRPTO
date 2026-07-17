from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from scripts.build_ijds_policy_support_tie_evidence import EVIDENCE_PATH, MEMO_PATH, build
from src.utils.isolated_experiment import sha256_file

ROOT = Path(__file__).resolve().parents[1]


def _evidence() -> dict[str, Any]:
    payload = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Policy-support evidence must be a JSON object.")
    return payload


def test_policy_support_evidence_build_is_byte_idempotent() -> None:
    build()
    first = sha256_file(EVIDENCE_PATH), sha256_file(MEMO_PATH)
    build()
    assert (sha256_file(EVIDENCE_PATH), sha256_file(MEMO_PATH)) == first


def test_policy_support_evidence_is_outcome_free_and_not_promoted() -> None:
    evidence = _evidence()
    assert evidence["outcome_columns_passed"] == []
    assert evidence["active_claim_status"] == "not_active_until_family_redesign_decision"
    assert evidence["protected_stages_run"] == []
    assert evidence["protected_artifacts_written"] == []


def test_policy_family_endpoint_and_reconstruction_results() -> None:
    family = _evidence()["results"]["family"]
    assert family["rows"] == 3_120
    assert family["inherited_rows"] == 1_872
    assert family["inherited_infeasible"] == 0
    assert family["inherited_decision_active"] == 1_846
    assert family["inherited_slack"] == 26
    assert family["gamma_zero_objective_slack"] == 624
    assert family["gamma_one_decision_active"] == 624
    assert family["gamma_one_minus_075_objective_max"] < -500.0
    assert family["maximum_absolute_parent_score_difference"] < 3e-16
    assert family["maximum_absolute_parent_objective_difference"] < 1e-9


def test_tie_census_corrects_the_exploratory_counts() -> None:
    results = _evidence()["results"]
    point = results["point_cap_census"]
    order = results["order_sensitivity"]
    assert point["rows"] == 7_297
    assert point["named_unique_cap_months"] == 2_204
    assert point["near_zero_bases"] == 0
    assert point["primal_degenerate_bases"] == 2_941
    assert point["minimum_absolute_nonbasic_reduced_cost"] == pytest.approx(0.00038757301081204787)
    assert order["triggered_rows"] == 2_941
    assert order["tie_sensitive_rows"] == 0
    assert order["maximum_allocation_distance"] < 2e-14


def test_policy_support_tables_keep_the_declared_domains() -> None:
    tables = _evidence()["tables"]
    family = pd.read_csv(ROOT / tables["family"]["path"])
    endpoint = pd.read_csv(ROOT / tables["gamma_endpoint"]["path"])
    support = pd.read_csv(ROOT / tables["comparator_support"]["path"])
    assert int(family["cells"].sum()) == 3_120
    assert int(endpoint["cells"].sum()) == 624
    assert endpoint["gamma_100_decision_active"].eq(endpoint["cells"]).all()
    c0 = support.loc[support["source"].eq("named_c0")].iloc[0]
    assert int(c0["cap_month_rows"]) == 45
    assert int(c0["objective_slack"]) == 45
