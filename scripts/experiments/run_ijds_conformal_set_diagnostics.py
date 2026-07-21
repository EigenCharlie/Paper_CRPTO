"""Build the tagged complete IJDS conformal-set reporting diagnostic."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.ijds_audit.config import load_v4_config
from src.ijds_audit.conformal_set_diagnostics import (
    build_conformal_set_diagnostics,
    conformal_set_diagnostic_ranges,
)
from src.ijds_audit.protocol import (
    configured_archive_outcomes,
    load_outcome_universe,
    load_recipes,
)
from src.utils.artifact_descriptor import relative_artifact_descriptor
from src.utils.isolated_experiment import (
    environment_provenance,
    implementation_provenance,
    prepare_output_paths,
    require_clean_tagged_head,
    resolve_repo_input,
)
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_parquet

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Conformal-set diagnostic config must be a mapping.")
    for field in ("schema_version", "run_tag", "protocol_tag", "source", "design", "output"):
        if field not in payload:
            raise ValueError(f"Conformal-set diagnostic config omits {field!r}.")
    return payload


def _verified_path(descriptor: Mapping[str, Any], *, repo_root: Path) -> Path:
    path = resolve_repo_input(str(descriptor["path"]), repo_root=repo_root)
    actual = relative_artifact_descriptor(path, repo_root=repo_root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor.get(field):
            raise RuntimeError(f"Conformal-set diagnostic source mismatched on {field}: {path}.")
    return path


def _verified_artifact(descriptor: Mapping[str, Any], *, repo_root: Path) -> Path:
    return _verified_path(descriptor, repo_root=repo_root)


def run(*, config_path: Path, repo_root: Path) -> Path:
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = _load_config(resolved_config)
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))

    source = config["source"]
    active_config_path = _verified_path(source["active_v5_config"], repo_root=root)
    active_config = load_v4_config(active_config_path)
    credit_summary_path = _verified_path(source["credit_control_summary"], repo_root=root)
    credit_summary = json.loads(credit_summary_path.read_text(encoding="utf-8"))
    if credit_summary.get("status") != "complete_no_model_selection_credit_risk_control_evaluation":
        raise RuntimeError("The source five-model evaluation is incomplete.")
    freeze_descriptor = credit_summary.get("source_freeze")
    if not isinstance(freeze_descriptor, Mapping):
        raise TypeError("The source five-model summary omits its outcome-free freeze.")
    if freeze_descriptor.get("sha256") != source["credit_control_freeze_sha256"]:
        raise RuntimeError("The declared five-model source-freeze hash changed.")
    freeze_path = _verified_artifact(freeze_descriptor, repo_root=root)
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("status") != "credit_control_scores_frozen_before_primary_oot_outcome_join":
        raise RuntimeError("The source five-model outcome-free freeze is incomplete.")
    if freeze.get("primary_oot_outcome_columns_in_frozen_scores") != []:
        raise RuntimeError("The frozen five-model scores report outcome leakage.")

    evaluation_artifacts = credit_summary.get("evaluation_artifacts")
    if not isinstance(evaluation_artifacts, Mapping):
        raise TypeError("The source five-model summary omits evaluation artifacts.")
    temporal_descriptor = evaluation_artifacts.get("temporal_coverage")
    if not isinstance(temporal_descriptor, Mapping):
        raise TypeError("The source five-model summary omits temporal coverage.")
    if temporal_descriptor.get("sha256") != source["temporal_coverage_sha256"]:
        raise RuntimeError("The declared five-model temporal-coverage hash changed.")
    temporal_path = _verified_artifact(temporal_descriptor, repo_root=root)

    frozen_artifacts = freeze.get("outcome_free_artifacts")
    if not isinstance(frozen_artifacts, Mapping):
        raise TypeError("The source five-model freeze omits outcome-free artifacts.")
    scores_descriptor = frozen_artifacts.get("scores")
    recipes_descriptor = frozen_artifacts.get("recipes")
    if not isinstance(scores_descriptor, Mapping) or not isinstance(recipes_descriptor, Mapping):
        raise TypeError("The source five-model freeze omits scores or recipes.")
    scores_path = _verified_artifact(scores_descriptor, repo_root=root)
    recipes_path = _verified_artifact(recipes_descriptor, repo_root=root)

    scores = pd.read_parquet(scores_path)
    recipes = load_recipes(recipes_path)
    reference_coverage = pd.read_parquet(temporal_path)
    raw_path = resolve_repo_input(active_config["source"]["raw_path"], repo_root=root)
    raw_descriptor = relative_artifact_descriptor(raw_path, repo_root=root)
    if raw_descriptor["sha256"] != source["raw_archive_sha256"]:
        raise RuntimeError("The predeclared raw archive digest changed.")
    universe = load_outcome_universe(active_config, raw_path=raw_path)
    outcomes = configured_archive_outcomes(universe, active_config)
    design = config["design"]
    table = build_conformal_set_diagnostics(
        scores,
        outcomes,
        recipes,
        reference_coverage,
        learners=tuple(str(value) for value in design["learners"]),
        window_ids=tuple(str(value) for value in design["window_ids"]),
        role=str(design["role"]),
        taxonomy_groups=int(design["taxonomy_groups"]),
        expected_issue_months=tuple(str(value) for value in design["issue_months"]),
        expected_candidates=int(design["expected_candidates"]),
        expected_resolved=int(design["expected_resolved"]),
        expected_unresolved=int(design["expected_unresolved"]),
        expected_resolved_y0=int(design["expected_resolved_y0"]),
        expected_resolved_y1=int(design["expected_resolved_y1"]),
    )

    outputs = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    table_path = atomic_write_parquet(table, outputs.data_dir / str(config["output"]["table"]))
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_retrospective_conformal_set_diagnostic",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "scope": "all_five_learners_all_eight_windows_primary_oot",
        "source_artifacts": {
            "active_v5_config": relative_artifact_descriptor(active_config_path, repo_root=root),
            "credit_control_summary": relative_artifact_descriptor(
                credit_summary_path, repo_root=root
            ),
            "credit_control_freeze": relative_artifact_descriptor(freeze_path, repo_root=root),
            "scores": relative_artifact_descriptor(scores_path, repo_root=root),
            "recipes": relative_artifact_descriptor(recipes_path, repo_root=root),
            "temporal_coverage": relative_artifact_descriptor(temporal_path, repo_root=root),
            "raw_archive": raw_descriptor,
        },
        "counts": {
            "learner_window_cells": int(len(table)),
            "learners": int(table["learner"].nunique()),
            "windows_per_learner": int(table["window_id"].nunique()),
            "candidate_rows": int(table["candidate_rows"].iloc[0]),
            "resolved_rows": int(table["resolved_rows"].iloc[0]),
            "unresolved_rows": int(table["unresolved_rows"].iloc[0]),
            "resolved_y0_rows": int(table["resolved_y0_rows"].iloc[0]),
            "resolved_y1_rows": int(table["resolved_y1_rows"].iloc[0]),
        },
        "reference_reconciliation": {
            "canonical_coverage_and_geometry_match": True,
            "absolute_and_relative_tolerance": 5.0e-14,
        },
        "metric_definitions": {
            "canonical_set": "{y in {0,1}: abs(y-p) <= c_g} = [lower,upper] intersect {0,1}",
            "average_set_size": "mean(cardinality(canonical_set))",
            "singleton_share": "mean(cardinality(canonical_set) == 1)",
            "resolved_label_coverage": "descriptive coverage conditional on reconstructed resolved Y",
        },
        "ranges": conformal_set_diagnostic_ranges(table),
        "interpretation": dict(config["interpretation"]),
        "artifacts": {
            "conformal_set_diagnostics": relative_artifact_descriptor(table_path, repo_root=root)
        },
        "implementation_provenance": implementation_provenance(
            config_path=resolved_config,
            repo_root=root,
            relative_paths=[
                Path("scripts/experiments/run_ijds_conformal_set_diagnostics.py"),
                Path("src/ijds_audit/conformal_set_diagnostics.py"),
                Path("src/ijds_audit/protocol.py"),
                Path("src/data/outcome_observability.py"),
                Path("src/models/binary_conformal_guardrail.py"),
                Path("docs/research/ijds_conformal_set_diagnostics_protocol_2026-07-21.md"),
            ],
        ),
        "environment": environment_provenance(root),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    summary_path = atomic_write_json(outputs.model_dir / str(config["output"]["summary"]), summary)
    atomic_write_json(
        outputs.model_dir / str(config["output"]["execution_receipt"]),
        {
            "schema_version": str(config["schema_version"]),
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "summary": relative_artifact_descriptor(summary_path, repo_root=root),
            "environment": environment_provenance(root),
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    return summary_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    print(run(config_path=args.config, repo_root=args.repo_root))


if __name__ == "__main__":
    main()
