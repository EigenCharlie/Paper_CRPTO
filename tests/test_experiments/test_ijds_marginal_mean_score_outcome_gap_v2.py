from __future__ import annotations

import copy
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.experiments.run_ijds_marginal_mean_score_outcome_gap_v2 import (
    DEFAULT_CONFIG_PATH,
    IMPLEMENTATION_PATHS,
    PROTOCOL_TAG,
    RUN_TAG,
    _load_config,
    _output_targets,
    _reconcile_embedded_endpoint_rows,
    _resolve_locked_config_path,
)
from src.utils.artifact_descriptor import relative_artifact_descriptor
from src.utils.isolated_experiment import OutputPaths

ROOT = Path(__file__).resolve().parents[2]


def test_v2_config_is_canonical_complete_and_result_unconditioned() -> None:
    config_path = ROOT / DEFAULT_CONFIG_PATH
    assert _resolve_locked_config_path(config_path, repo_root=ROOT) == config_path.resolve()
    config = _load_config(config_path)
    assert config["run_tag"] == RUN_TAG
    assert config["protocol_tag"] == PROTOCOL_TAG
    assert config["estimand"] == "marginal_mean_score_outcome_gap"
    assert len(config["design"]["learners"]) == 5
    assert list(config["design"]["score_columns"]) == config["design"]["learners"]
    assert config["design"]["expected_candidates"] == 376_890
    assert config["design"]["expected_resolved_y1"] == 56_972
    assert config["design"]["expected_unresolved"] == 12_076
    assert config["reporting_contract"]["result_sign_is_stop_condition"] is False
    assert config["stop_rules"]["stop_on_result_sign_or_ordering"] is False
    assert set(config["output"]) == {
        "data_root",
        "model_root",
        "table",
        "summary",
        "execution_receipt",
        "immutability",
    }


def test_v2_config_reconciles_outer_and_nested_source_descriptors() -> None:
    config = _load_config(ROOT / DEFAULT_CONFIG_PATH)
    source = config["source"]
    for descriptor in source.values():
        path = ROOT / descriptor["path"]
        assert relative_artifact_descriptor(path, repo_root=ROOT) == descriptor

    summary = json.loads(
        (ROOT / source["credit_control_summary"]["path"]).read_text(encoding="utf-8")
    )
    receipt = json.loads(
        (ROOT / source["credit_control_receipt"]["path"]).read_text(encoding="utf-8")
    )
    freeze = json.loads(
        (ROOT / source["credit_control_freeze"]["path"]).read_text(encoding="utf-8")
    )
    assert receipt["summary"] == source["credit_control_summary"]
    assert receipt["source_freeze"] == source["credit_control_freeze"]
    assert summary["source_freeze"] == source["credit_control_freeze"]
    assert summary["source_protocol"] == {
        "status": config["source_identity"]["credit_control_freeze_status"],
        "run_tag": config["source_identity"]["credit_control_freeze_run_tag"],
        "protocol_tag": config["source_identity"]["credit_control_freeze_protocol_tag"],
        "protocol_commit": config["source_identity"]["credit_control_freeze_protocol_commit"],
    }
    assert (
        summary["evaluation_artifacts"]["endpoint_resolution_audit"]
        == source["endpoint_resolution_audit"]
    )
    assert freeze["outcome_free_artifacts"]["scores"] == source["scores"]
    assert freeze["primary_oot_outcome_columns_in_frozen_scores"] == []


def test_v2_family_contains_only_the_single_declared_product() -> None:
    paths = [ROOT / DEFAULT_CONFIG_PATH, *(ROOT / path for path in IMPLEMENTATION_PATHS)]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    source_only = "\n".join(
        path.read_text(encoding="utf-8") for path in paths if path.suffix in {".py", ".yaml"}
    )
    forbidden_products = (
        "all_candidate_" + "calibration" + "_" + "bias",
        "resolved_coverage_" + "breakeven",
        "minimum_reference_" + "stratum_effect",
    )
    assert all(value not in source_only for value in forbidden_products)
    assert "postfreeze_" + "derived_diagnostics" not in text
    assert text.count("marginal_mean_score_outcome_gap") > 0


def test_embedded_endpoint_rows_must_equal_the_hash_verified_table() -> None:
    rows = [
        {
            "role": "primary_oot",
            "snapshot_resolution": "fully_paid_by_reconstructed_cutoff",
            "candidate_rows": 2,
            "resolved_rows": 2,
            "unresolved_rows": 0,
        }
    ]
    artifact = pd.DataFrame(rows)
    for column in ("candidate_rows", "resolved_rows", "unresolved_rows"):
        artifact[column] = artifact[column].astype("Int64")
    reconciled = _reconcile_embedded_endpoint_rows(rows, artifact)
    assert len(reconciled) == 1
    changed = artifact.copy()
    changed.loc[0, "candidate_rows"] = 3
    changed.loc[0, "resolved_rows"] = 3
    with pytest.raises(RuntimeError, match="do not match"):
        _reconcile_embedded_endpoint_rows(rows, changed)


def test_output_contract_rejects_escape_and_alias(tmp_path: Path) -> None:
    config = _load_config(ROOT / DEFAULT_CONFIG_PATH)
    paths = OutputPaths(data_dir=tmp_path / "data", model_dir=tmp_path / "model")
    targets = _output_targets(config, paths)
    assert targets["table"].is_relative_to(paths.data_dir)
    assert targets["summary"].is_relative_to(paths.model_dir)

    escaping = copy.deepcopy(config)
    escaping["output"]["table"] = "../escape.parquet"
    with pytest.raises(ValueError, match="escapes"):
        _output_targets(escaping, paths)

    aliasing = copy.deepcopy(config)
    aliasing["output"]["execution_receipt"] = aliasing["output"]["summary"]
    with pytest.raises(ValueError, match="alias"):
        _output_targets(aliasing, paths)
