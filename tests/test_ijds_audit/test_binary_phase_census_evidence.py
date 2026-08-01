"""Direct tests for the paper-facing binary phase census loader."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import yaml

from src.ijds_audit import binary_phase_census_evidence as module
from src.ijds_audit.binary_phase_census_evidence import (
    BinaryPhaseCensusEvidence,
    binary_phase_census_publication_table,
    load_binary_phase_census_evidence,
)

ROOT = Path(__file__).resolve().parents[2]


def _registered() -> dict[str, Path]:
    return {name: ROOT / relative for name, relative in module._REGISTERED_PATHS.items()}


def _identity() -> dict[str, Any]:
    return module._expected_identity()


@pytest.fixture(scope="module")
def evidence() -> BinaryPhaseCensusEvidence:
    return load_binary_phase_census_evidence(_registered(), _identity(), repo_root=ROOT)


def test_active_registry_exposes_the_exact_phase_census_identity_and_paths() -> None:
    registry = yaml.safe_load(
        (ROOT / "configs/ijds_active_evidence_sources.yaml").read_text(encoding="utf-8")
    )
    assert registry["lineages"]["diagnostics"]["binary_phase_census"] == _identity()
    for name, relative in module._REGISTERED_PATHS.items():
        assert registry["sources"][name]["path"] == relative


def test_loader_returns_the_complete_verified_table_and_findings(
    evidence: BinaryPhaseCensusEvidence,
) -> None:
    table = evidence.cell_table
    assert len(table) == 200
    assert tuple(table.columns) == tuple(module.CELL_OUTPUT_COLUMNS)
    assert not table.duplicated(["learner", "window_id", "conformal_group"]).any()
    assert table["learner"].nunique() == 5
    assert table["window_id"].nunique() == 8
    assert table["conformal_group"].nunique() == 5

    findings = evidence.findings
    assert findings["cells"] == 200
    assert findings["cells_per_conformal_group"] == 40
    ordered = findings["ordered_conformal_groups"]
    assert [row["conformal_group"] for row in ordered] == [0, 1, 2, 3, 4]
    assert [row["cells"] for row in ordered] == [40, 40, 40, 40, 40]
    assert [row["threshold_below_half"] for row in ordered] == [40, 40, 7, 0, 0]
    assert [row["phase_margin_nonpositive"] for row in ordered] == [40, 40, 7, 0, 0]
    assert [row["half_condition_applicable"] for row in ordered] == [40, 40, 40, 40, 24]
    assert [row["half_condition_inapplicable"] for row in ordered] == [0, 0, 0, 0, 16]
    assert [row["source_condition_applicable"] for row in ordered] == [40, 40, 40, 40, 28]
    assert [row["source_condition_inapplicable"] for row in ordered] == [0, 0, 0, 0, 12]
    assert all(row["half_condition_failed_when_applicable"] == 0 for row in ordered)
    assert all(row["source_condition_failed_when_applicable"] == 0 for row in ordered)
    assert findings["global"] == {
        "threshold_below_half": 87,
        "phase_margin_nonpositive": 87,
        "half_condition_applicable": 184,
        "half_condition_inapplicable": 16,
        "half_condition_failed_when_applicable": 0,
        "source_condition_applicable": 188,
        "source_condition_inapplicable": 12,
        "source_condition_failed_when_applicable": 0,
        "exact_half_failures": 0,
        "reconciliation_failures": 0,
    }


def test_publication_table_is_complete_and_defensive(
    evidence: BinaryPhaseCensusEvidence,
) -> None:
    publication = binary_phase_census_publication_table(evidence)
    assert publication.equals(evidence.cell_table)
    publication.loc[0, "phase_margin"] += 1
    assert publication.loc[0, "phase_margin"] != evidence.cell_table.loc[0, "phase_margin"]


def test_findings_and_results_emit_no_learner_or_window_breakdown(
    evidence: BinaryPhaseCensusEvidence,
) -> None:
    rendered = json.dumps(evidence.findings, sort_keys=True)
    results = json.dumps(evidence.summary["results"], sort_keys=True)
    for learner in module._LEARNERS:
        assert learner not in rendered
        assert learner not in results
    for window in module._WINDOWS:
        assert window not in rendered
        assert window not in results
    assert evidence.findings["learner_window_breakdown_emitted"] is False


def test_forbidden_downstream_column_fails_closed(evidence: BinaryPhaseCensusEvidence) -> None:
    changed = evidence.cell_table.copy()
    changed["target_coverage"] = 1.0
    with pytest.raises(RuntimeError, match="forbidden paper-facing columns"):
        module._validate_cell_table(changed)


def test_missing_or_duplicate_cell_fails_closed(evidence: BinaryPhaseCensusEvidence) -> None:
    with pytest.raises(RuntimeError, match="exactly 200 cells"):
        module._validate_cell_table(evidence.cell_table.iloc[:-1].copy())
    duplicated = pd.concat(
        [evidence.cell_table.iloc[:-1], evidence.cell_table.iloc[[0]]], ignore_index=True
    )
    with pytest.raises(RuntimeError, match="duplicate cell key"):
        module._validate_cell_table(duplicated)


@pytest.mark.parametrize(
    ("applicable_column", "pass_column", "finding_prefix"),
    [
        (
            "phase_margin_half_check_applicable",
            "phase_margin_half_check_pass",
            "half_condition",
        ),
        (
            "phase_margin_source_check_applicable",
            "phase_margin_source_check_pass",
            "source_condition",
        ),
    ],
)
def test_inapplicable_is_not_counted_as_failure(
    evidence: BinaryPhaseCensusEvidence,
    applicable_column: str,
    pass_column: str,
    finding_prefix: str,
) -> None:
    changed = evidence.cell_table.copy()
    row = changed.index[~changed[applicable_column]][0]
    changed.loc[row, pass_column] = False
    findings = module._validate_cell_table(changed)
    assert findings["global"][f"{finding_prefix}_inapplicable"] > 0
    assert findings["global"][f"{finding_prefix}_failed_when_applicable"] == 0


@pytest.mark.parametrize(
    ("applicable_column", "pass_column", "message"),
    [
        (
            "phase_margin_half_check_applicable",
            "phase_margin_half_check_pass",
            "applicable phase-margin half check failed",
        ),
        (
            "phase_margin_source_check_applicable",
            "phase_margin_source_check_pass",
            "applicable phase-margin source check failed",
        ),
    ],
)
def test_failure_where_applicable_fails_closed(
    evidence: BinaryPhaseCensusEvidence,
    applicable_column: str,
    pass_column: str,
    message: str,
) -> None:
    changed = evidence.cell_table.copy()
    row = changed.index[changed[applicable_column]][0]
    changed.loc[row, pass_column] = False
    with pytest.raises(RuntimeError, match=message):
        module._validate_cell_table(changed)


def test_global_or_stratum_summary_drift_fails_closed(
    evidence: BinaryPhaseCensusEvidence,
) -> None:
    changed = copy.deepcopy(evidence.summary)
    changed["results"]["global_counts"]["cells_threshold_below_half"] += 1
    with pytest.raises(RuntimeError, match="do not recompute from all 200 cells"):
        module._require_result_contract(changed, evidence.cell_table)

    changed = copy.deepcopy(evidence.summary)
    changed["results"]["complete_ordered_stratum_summary"][2]["cells_threshold_below_half"] += 1
    with pytest.raises(RuntimeError, match="do not recompute from all 200 cells"):
        module._require_result_contract(changed, evidence.cell_table)


def test_registry_identity_drift_fails_before_artifact_loading() -> None:
    changed = _identity()
    changed["paper_role"] = "selected_winner"
    with pytest.raises(RuntimeError, match="registry identity changed"):
        module._require_identity_and_transport(changed, repo_root=ROOT)


def test_registered_output_path_drift_fails_closed() -> None:
    changed = _registered()
    changed["binary_phase_census_table"] = ROOT / module._SUMMARY_PATH
    with pytest.raises(RuntimeError, match="changed path"):
        module._require_registered_paths(changed, repo_root=ROOT)


def test_loader_rejects_cross_output_descriptor_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    original = module._load_json_object

    def changed_loader(path: Path, *, label: str) -> dict[str, Any]:
        payload = original(path, label=label)
        if label == "phase census receipt":
            payload["artifacts"]["complete_cell_table"]["sha256"] = "0" * 64
        return payload

    monkeypatch.setattr(module, "_load_json_object", changed_loader)
    with pytest.raises(RuntimeError, match="cell-table descriptor changed"):
        load_binary_phase_census_evidence(_registered(), _identity(), repo_root=ROOT)


def test_registry_mapping_contract_is_plain_mapping() -> None:
    identity: Mapping[str, Any] = _identity()
    registered: Mapping[str, Path] = _registered()
    evidence = load_binary_phase_census_evidence(registered, identity, repo_root=ROOT)
    assert isinstance(evidence, BinaryPhaseCensusEvidence)
