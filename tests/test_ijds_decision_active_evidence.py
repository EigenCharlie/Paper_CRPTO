from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from scripts.build_ijds_decision_active_evidence import EVIDENCE_PATH, MEMO_PATH, build
from src.utils.isolated_experiment import sha256_file

ROOT = Path(__file__).resolve().parents[1]


def _evidence() -> dict[str, Any]:
    payload = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Decision-active evidence must be a JSON object.")
    return payload


def test_decision_active_evidence_build_is_byte_idempotent() -> None:
    build()
    first = sha256_file(EVIDENCE_PATH), sha256_file(MEMO_PATH)
    build()
    assert (sha256_file(EVIDENCE_PATH), sha256_file(MEMO_PATH)) == first


def test_decision_active_evidence_retains_claim_boundary_and_structure() -> None:
    evidence = _evidence()
    assert evidence["active_claim_status"] == "not_active_until_manuscript_promotion_decision"
    assert evidence["protected_stages_run"] == []
    assert evidence["protected_artifacts_written"] == []
    checks = evidence["structural_checks"]
    assert checks["factorial_rows"] == 3_600
    assert checks["factorial_cells"] == 72
    assert checks["all_guardrail_caps_binding"] is True
    assert checks["maximum_absolute_c2_match_residual"] < 2e-16


def test_decision_active_results_are_complete_not_selected() -> None:
    results = _evidence()["results"]
    assert results["c0_changed_count"] == 3_600
    assert results["c2_changed_count"] == 1_866
    assert results["c2_one_group_changed_count"] == 66
    assert results["c2_five_group_changed_count"] == 1_800
    assert results["c0_positive_slack_cells"] == 11
    assert results["baseline_coverage_one_group"] == pytest.approx(0.9007666666666667)
    assert results["strong_calibration_shift_coverage_one_group"] == pytest.approx(
        0.6967166666666667
    )


def test_decision_active_tables_keep_every_factor_cell() -> None:
    tables = _evidence()["tables"]
    coverage = pd.read_csv(ROOT / tables["coverage"]["path"])
    allocation = pd.read_csv(ROOT / tables["allocation"]["path"])
    directions = pd.read_csv(ROOT / tables["directions"]["path"])
    assert len(coverage) == 12
    assert len(allocation) == 12
    assert coverage["repetitions"].eq(50).all()
    assert allocation["repetitions"].eq(50).all()
    totals = directions.groupby(["comparator", "metric", "censoring_rate", "taxonomy_groups"])[
        "repetitions"
    ].sum()
    assert totals.eq(900).all()
