"""Run the clean tagged V2 marginal mean-score--outcome gap replay."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.ijds_audit.marginal_mean_score_outcome_gap import (
    ENDPOINT_COLUMNS,
    ESTIMAND,
    marginal_mean_score_outcome_gap,
    normalize_endpoint_resolution_table,
)
from src.utils.artifact_descriptor import relative_artifact_descriptor
from src.utils.isolated_experiment import (
    OutputPaths,
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    prepare_output_paths,
    require_clean_tagged_head,
    resolve_isolated_run_dir,
    resolve_repo_input,
)
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_parquet

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = Path(
    "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v2.yaml"
)
PROTOCOL_PATH = Path("docs/research/ijds_marginal_mean_score_outcome_gap_v2_protocol_2026-07-26.md")
RUN_TAG = "ijds-marginal-mean-score-outcome-gap-2026-07-26-v2"
PROTOCOL_TAG = "protocol/ijds-marginal-mean-score-outcome-gap-2026-07-26-v2"
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
IMPLEMENTATION_PATHS = (
    Path("scripts/experiments/run_ijds_marginal_mean_score_outcome_gap_v2.py"),
    Path("src/ijds_audit/marginal_mean_score_outcome_gap.py"),
    PROTOCOL_PATH,
)
SOURCE_KEYS = {
    "credit_control_receipt",
    "credit_control_summary",
    "credit_control_freeze",
    "scores",
    "endpoint_resolution_audit",
}
LEARNERS = (
    "catboost_platt",
    "numeric_logistic_platt",
    "catboost_monotonic_platt",
    "woe_scorecard_platform_platt",
    "woe_scorecard_borrower_platt",
)
SCORE_COLUMNS = {learner: f"pd_{learner}" for learner in LEARNERS}
ISSUE_MONTHS = tuple(
    f"{year:04d}-{month:02d}"
    for year, month in (
        (2016, 4),
        (2016, 5),
        (2016, 6),
        (2016, 7),
        (2016, 8),
        (2016, 9),
        (2016, 10),
        (2016, 11),
        (2016, 12),
        (2017, 1),
        (2017, 2),
        (2017, 3),
        (2017, 4),
        (2017, 5),
        (2017, 6),
    )
)
EXPECTED_COUNTS = {
    "expected_candidates": 376_890,
    "expected_resolved": 364_814,
    "expected_unresolved": 12_076,
    "expected_resolved_y0": 307_842,
    "expected_resolved_y1": 56_972,
}
EXPECTED_REASON_CENSUS = {
    "charged_off_by_reconstructed_cutoff": {
        "candidate_rows": 56_972,
        "resolved_rows": 56_972,
        "unresolved_rows": 0,
    },
    "fully_paid_by_reconstructed_cutoff": {
        "candidate_rows": 307_842,
        "resolved_rows": 307_842,
        "unresolved_rows": 0,
    },
    "nonterminal_or_unresolved_status": {
        "candidate_rows": 11_551,
        "resolved_rows": 0,
        "unresolved_rows": 11_551,
    },
    "terminal_after_reconstructed_cutoff": {
        "candidate_rows": 47,
        "resolved_rows": 0,
        "unresolved_rows": 47,
    },
    "terminal_availability_date_missing": {
        "candidate_rows": 478,
        "resolved_rows": 0,
        "unresolved_rows": 478,
    },
}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _resolve_locked_config_path(path: Path, *, repo_root: Path) -> Path:
    resolved = resolve_repo_input(path, repo_root=repo_root)
    expected = (repo_root.resolve() / DEFAULT_CONFIG_PATH).resolve()
    if resolved != expected:
        raise RuntimeError(f"V2 accepts only the canonical tracked config: {expected}.")
    return resolved


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Marginal mean-score--outcome gap config must be a mapping.")
    required = {
        "schema_version",
        "protocol_status",
        "run_tag",
        "protocol_tag",
        "protocol_path",
        "estimand",
        "source",
        "source_identity",
        "design",
        "output",
        "reporting_contract",
        "stop_rules",
    }
    if missing := required.difference(payload):
        raise ValueError(f"V2 config omits fields: {sorted(missing)}")
    if payload["schema_version"] != "2026-07-26.2":
        raise RuntimeError("V2 config schema changed.")
    if payload["protocol_status"] != "retrospectively_locked_before_v2_execution":
        raise RuntimeError("V2 protocol status changed.")
    if payload["run_tag"] != RUN_TAG or payload["protocol_tag"] != PROTOCOL_TAG:
        raise RuntimeError("V2 run or protocol identity changed.")
    if payload["protocol_path"] != PROTOCOL_PATH.as_posix():
        raise RuntimeError("V2 protocol path changed.")
    if payload["estimand"] != ESTIMAND:
        raise RuntimeError("V2 estimand name changed.")
    source = payload["source"]
    if not isinstance(source, Mapping) or set(source) != SOURCE_KEYS:
        raise RuntimeError("V2 source family changed.")
    if any(not isinstance(descriptor, Mapping) for descriptor in source.values()):
        raise TypeError("Every V2 source descriptor must be a mapping.")
    descriptor_fields = {"path", "bytes", "sha256"}
    if any(set(descriptor) != descriptor_fields for descriptor in source.values()):
        raise RuntimeError("A V2 source descriptor changed fields.")
    design = payload["design"]
    if not isinstance(design, Mapping):
        raise TypeError("V2 design contract must be a mapping.")
    learners = tuple(str(value) for value in design.get("learners", ()))
    score_columns = design.get("score_columns")
    if learners != LEARNERS:
        raise RuntimeError("V2 learner census changed.")
    if not isinstance(score_columns, Mapping) or dict(score_columns) != SCORE_COLUMNS:
        raise RuntimeError("V2 learner and score-column censuses differ.")
    if str(design.get("role")) != "primary_oot":
        raise RuntimeError("V2 target role changed.")
    if str(design.get("endpoint_cutoff")) != "2020-09-30":
        raise RuntimeError("V2 active endpoint cutoff changed.")
    if design.get("charged_off_availability_lag_months") != 6:
        raise RuntimeError("V2 Charged Off availability lag changed.")
    if tuple(str(value) for value in design.get("issue_months", ())) != ISSUE_MONTHS:
        raise RuntimeError("V2 target issue-month census changed.")
    for field, expected in EXPECTED_COUNTS.items():
        if design.get(field) != expected:
            raise RuntimeError(f"V2 endpoint contract changed on {field}.")
    if design.get("endpoint_reason_census") != EXPECTED_REASON_CENSUS:
        raise RuntimeError("V2 endpoint-reason census changed.")
    source_identity = payload["source_identity"]
    if not isinstance(source_identity, Mapping):
        raise TypeError("V2 source identity contract must be a mapping.")
    expected_source_identity = {
        "credit_control_receipt_status": "credit_risk_control_evaluation_complete",
        "credit_control_summary_status": (
            "complete_no_model_selection_credit_risk_control_evaluation"
        ),
        "credit_control_summary_run_tag": "ijds-credit-risk-controls-2026-07-15-v5",
        "credit_control_protocol_tag": "protocol/ijds-credit-risk-controls-2026-07-15-v5",
        "credit_control_protocol_commit": "e2bba580a0b07c145bd64ff61440973d6e31349b",
        "credit_control_freeze_status": (
            "credit_control_scores_frozen_before_primary_oot_outcome_join"
        ),
        "credit_control_freeze_run_tag": "ijds-credit-risk-controls-2026-07-13-v1b",
        "credit_control_freeze_protocol_tag": ("protocol/ijds-credit-risk-controls-2026-07-13-v1b"),
        "credit_control_freeze_protocol_commit": ("1776cbf8b201ae5b92756e5ea397a403d6cc7c9f"),
    }
    if dict(source_identity) != expected_source_identity:
        raise RuntimeError("V2 source identity contract changed.")
    reporting = payload["reporting_contract"]
    if not isinstance(reporting, Mapping):
        raise TypeError("V2 reporting contract must be a mapping.")
    expected_reporting = {
        "complete_five_learner_census": True,
        "select_or_rank_learner": False,
        "result_sign_is_stop_condition": False,
        "binary_completion_bounds_are_sampling_intervals": False,
        "verified_point_in_time_snapshot_claim": False,
        "row_level_evaluation_outcomes_loaded": False,
        "refit_recalibrate_or_optimize": False,
        "selected_or_funded_set_validity": False,
        "causal_or_prospective_interpretation": False,
    }
    if dict(reporting) != expected_reporting:
        raise RuntimeError("V2 reporting boundary changed.")
    stop_rules = payload["stop_rules"]
    if not isinstance(stop_rules, Mapping):
        raise TypeError("V2 stop-rule contract must be a mapping.")
    expected_stop_rules = {
        "stop_on_dirty_or_untagged_head": True,
        "stop_on_noncanonical_config": True,
        "stop_on_source_or_nested_descriptor_mismatch": True,
        "stop_on_implementation_drift": True,
        "stop_on_candidate_id_or_issue_month_drift": True,
        "stop_on_invalid_or_incomplete_score_census": True,
        "stop_on_endpoint_reason_or_total_drift": True,
        "stop_on_nonfinite_or_reversed_bound": True,
        "stop_on_preexisting_or_escaping_output_path": True,
        "stop_on_result_sign_or_ordering": False,
    }
    if dict(stop_rules) != expected_stop_rules:
        raise RuntimeError("V2 fail-closed stop contract changed.")
    output = payload["output"]
    expected_output = {
        "data_root": "data/processed/experiments/ijds_audit",
        "model_root": "models/experiments/ijds_audit",
        "table": "evaluation/marginal_mean_score_outcome_gap.parquet",
        "summary": "marginal_mean_score_outcome_gap_summary.json",
        "execution_receipt": "execution_receipt.json",
        "immutability": "hard_no_overwrite_choose_fresh_run_tag",
    }
    if not isinstance(output, Mapping) or dict(output) != expected_output:
        raise RuntimeError("V2 immutable output contract changed.")
    return payload


def _verified_path(descriptor: Mapping[str, Any], *, repo_root: Path) -> Path:
    for field in ("path", "bytes", "sha256"):
        if field not in descriptor:
            raise ValueError(f"V2 source descriptor omits {field!r}.")
    path = resolve_repo_input(str(descriptor["path"]), repo_root=repo_root)
    actual = relative_artifact_descriptor(path, repo_root=repo_root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor[field]:
            raise RuntimeError(f"V2 source mismatched on {field}: {path}.")
    return path


def _require_same_descriptor(
    actual: Mapping[str, Any], expected: Mapping[str, Any], *, label: str
) -> None:
    for field in ("path", "bytes", "sha256"):
        if actual.get(field) != expected.get(field):
            raise RuntimeError(f"{label} nested descriptor changed on {field}.")


def _reconcile_embedded_endpoint_rows(
    embedded_rows: Any, endpoint_table: pd.DataFrame
) -> pd.DataFrame:
    if not isinstance(embedded_rows, list) or not embedded_rows:
        raise TypeError("The active evaluation summary omits endpoint-reason rows.")
    embedded = normalize_endpoint_resolution_table(pd.DataFrame.from_records(embedded_rows))
    artifact = normalize_endpoint_resolution_table(endpoint_table)
    if not embedded.equals(artifact):
        raise RuntimeError(
            "Embedded endpoint-reason rows do not match the hash-verified endpoint artifact."
        )
    return artifact


def _contained_output_target(base: Path, configured: Any, *, suffix: str) -> Path:
    relative = Path(str(configured))
    if relative.is_absolute() or str(relative) in {"", ".", ".."}:
        raise ValueError(f"Unsafe V2 output path: {configured!r}.")
    target = (base / relative).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError as exc:
        raise ValueError(f"V2 output escapes its run directory: {target}.") from exc
    if target.suffix.lower() != suffix:
        raise ValueError(f"V2 output {target} must use suffix {suffix!r}.")
    return target


def _output_targets(config: Mapping[str, Any], paths: OutputPaths) -> dict[str, Path]:
    output = config["output"]
    targets = {
        "table": _contained_output_target(paths.data_dir, output["table"], suffix=".parquet"),
        "summary": _contained_output_target(paths.model_dir, output["summary"], suffix=".json"),
        "execution_receipt": _contained_output_target(
            paths.model_dir, output["execution_receipt"], suffix=".json"
        ),
    }
    rendered = [str(path).casefold() for path in targets.values()]
    if len(rendered) != len(set(rendered)):
        raise ValueError("V2 output paths alias one another.")
    return targets


def _preflight_output_paths(config: Mapping[str, Any], *, repo_root: Path) -> None:
    output = config["output"]
    paths = OutputPaths(
        data_dir=resolve_isolated_run_dir(
            repo_root=repo_root,
            configured_root=output["data_root"],
            allowed_relative_root=ALLOWED_DATA_ROOT,
            run_tag=RUN_TAG,
        ),
        model_dir=resolve_isolated_run_dir(
            repo_root=repo_root,
            configured_root=output["model_root"],
            allowed_relative_root=ALLOWED_MODEL_ROOT,
            run_tag=RUN_TAG,
        ),
    )
    existing = [path for path in (paths.data_dir, paths.model_dir) if path.exists()]
    if existing:
        raise FileExistsError(f"V2 output directories already exist: {existing}.")
    _output_targets(config, paths)


def _load_verified_sources(
    config: Mapping[str, Any], *, repo_root: Path
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Path], dict[str, Any], dict[str, Any]]:
    source = config["source"]
    paths = {
        name: _verified_path(descriptor, repo_root=repo_root) for name, descriptor in source.items()
    }
    summary = json.loads(paths["credit_control_summary"].read_text(encoding="utf-8"))
    identity = config["source_identity"]
    receipt = json.loads(paths["credit_control_receipt"].read_text(encoding="utf-8"))
    if receipt.get("status") != identity["credit_control_receipt_status"]:
        raise RuntimeError("The active five-learner evaluation receipt status changed.")
    if receipt.get("run_tag") != identity["credit_control_summary_run_tag"]:
        raise RuntimeError("The active five-learner evaluation receipt run changed.")
    if receipt.get("protocol_tag") != identity["credit_control_protocol_tag"]:
        raise RuntimeError("The active five-learner evaluation protocol tag changed.")
    if receipt.get("protocol_commit") != identity["credit_control_protocol_commit"]:
        raise RuntimeError("The active five-learner evaluation protocol commit changed.")
    receipt_summary = receipt.get("summary")
    receipt_freeze = receipt.get("source_freeze")
    if not isinstance(receipt_summary, Mapping) or not isinstance(receipt_freeze, Mapping):
        raise TypeError("The active evaluation receipt omits nested source descriptors.")
    _require_same_descriptor(
        receipt_summary,
        source["credit_control_summary"],
        label="Receipt-to-summary",
    )
    _require_same_descriptor(
        receipt_freeze,
        source["credit_control_freeze"],
        label="Receipt-to-freeze",
    )
    if summary.get("status") != identity["credit_control_summary_status"]:
        raise RuntimeError("The active five-learner evaluation status changed.")
    if summary.get("run_tag") != identity["credit_control_summary_run_tag"]:
        raise RuntimeError("The active five-learner evaluation run changed.")
    expected_source_protocol = {
        "status": identity["credit_control_freeze_status"],
        "run_tag": identity["credit_control_freeze_run_tag"],
        "protocol_tag": identity["credit_control_freeze_protocol_tag"],
        "protocol_commit": identity["credit_control_freeze_protocol_commit"],
    }
    if summary.get("source_protocol") != expected_source_protocol:
        raise RuntimeError("The evaluation-to-freeze protocol identity changed.")
    nested_freeze = summary.get("source_freeze")
    if not isinstance(nested_freeze, Mapping):
        raise TypeError("The active evaluation summary omits its source-freeze descriptor.")
    _require_same_descriptor(
        nested_freeze,
        source["credit_control_freeze"],
        label="Evaluation-to-freeze",
    )
    evaluation_artifacts = summary.get("evaluation_artifacts")
    if not isinstance(evaluation_artifacts, Mapping):
        raise TypeError("The active evaluation summary omits its artifact descriptors.")
    nested_endpoint = evaluation_artifacts.get("endpoint_resolution_audit")
    if not isinstance(nested_endpoint, Mapping):
        raise TypeError("The active evaluation summary omits its endpoint descriptor.")
    _require_same_descriptor(
        nested_endpoint,
        source["endpoint_resolution_audit"],
        label="Evaluation-to-endpoint",
    )

    freeze = json.loads(paths["credit_control_freeze"].read_text(encoding="utf-8"))
    if freeze.get("status") != identity["credit_control_freeze_status"]:
        raise RuntimeError("The outcome-free five-learner freeze status changed.")
    if freeze.get("run_tag") != identity["credit_control_freeze_run_tag"]:
        raise RuntimeError("The outcome-free five-learner freeze run changed.")
    if freeze.get("protocol_tag") != identity["credit_control_freeze_protocol_tag"]:
        raise RuntimeError("The outcome-free five-learner freeze protocol tag changed.")
    if freeze.get("protocol_commit") != identity["credit_control_freeze_protocol_commit"]:
        raise RuntimeError("The outcome-free five-learner freeze protocol commit changed.")
    if freeze.get("primary_oot_outcome_columns_in_frozen_scores") != []:
        raise RuntimeError("The frozen score artifact reports target outcome columns.")
    frozen_artifacts = freeze.get("outcome_free_artifacts")
    if not isinstance(frozen_artifacts, Mapping):
        raise TypeError("The outcome-free freeze omits artifact descriptors.")
    nested_scores = frozen_artifacts.get("scores")
    if not isinstance(nested_scores, Mapping):
        raise TypeError("The outcome-free freeze omits its score descriptor.")
    _require_same_descriptor(nested_scores, source["scores"], label="Freeze-to-scores")

    design = config["design"]
    learners = tuple(str(value) for value in design["learners"])
    if tuple(str(value) for value in freeze.get("co_primary_learners", ())) != learners:
        raise RuntimeError("The frozen five-learner census changed.")
    summary_learners = summary.get("co_primary_learners")
    if not isinstance(summary_learners, Mapping) or tuple(summary_learners) != learners:
        raise RuntimeError("The evaluated five-learner census changed.")
    inventory = freeze.get("source_inventory")
    if not isinstance(inventory, Mapping):
        raise TypeError("The score freeze omits its source inventory.")
    retained = inventory.get("retained_rows_by_split")
    if not isinstance(retained, Mapping):
        raise TypeError("The score freeze omits its split census.")
    if int(retained.get(str(design["role"]), -1)) != int(design["expected_candidates"]):
        raise RuntimeError("The frozen target split census changed.")
    if freeze.get("sampling") != "none_all_eligible_rows":
        raise RuntimeError("The frozen population census is no longer exhaustive.")
    if freeze.get("model_selection") != "none_all_five_reported":
        raise RuntimeError("The frozen learner family reports model selection.")

    score_allowlist = [
        "id",
        "issue_d",
        "design_split",
        *(str(value) for value in design["score_columns"].values()),
    ]
    scores = pd.read_parquet(paths["scores"], columns=score_allowlist)
    endpoint_artifact = pd.read_parquet(
        paths["endpoint_resolution_audit"], columns=list(ENDPOINT_COLUMNS)
    )
    endpoint = _reconcile_embedded_endpoint_rows(
        summary.get("endpoint_resolution_audit"), endpoint_artifact
    )
    return scores, endpoint, paths, summary, freeze


def run(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Execute the complete V2 replay after a separate clean protocol tag exists."""
    started_at = _utc_now()
    started_counter = time.perf_counter()
    root = repo_root.resolve()
    resolved_config = _resolve_locked_config_path(config_path, repo_root=root)
    config = _load_config(resolved_config)
    protocol_commit = require_clean_tagged_head(root, PROTOCOL_TAG)
    protocol_path = resolve_repo_input(PROTOCOL_PATH, repo_root=root)
    _preflight_output_paths(config, repo_root=root)
    implementation_start = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    initial_git = git_provenance(root)

    scores, endpoint, source_paths, _summary_source, _freeze = _load_verified_sources(
        config, repo_root=root
    )
    design = config["design"]
    result = marginal_mean_score_outcome_gap(
        scores,
        endpoint,
        learners=tuple(str(value) for value in design["learners"]),
        score_columns={str(key): str(value) for key, value in design["score_columns"].items()},
        role=str(design["role"]),
        expected_issue_months=tuple(str(value) for value in design["issue_months"]),
        expected_reason_census=design["endpoint_reason_census"],
        expected_candidates=int(design["expected_candidates"]),
        expected_resolved=int(design["expected_resolved"]),
        expected_unresolved=int(design["expected_unresolved"]),
        expected_resolved_y0=int(design["expected_resolved_y0"]),
        expected_resolved_y1=int(design["expected_resolved_y1"]),
    )
    table = result.table

    implementation_end = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    if implementation_end != implementation_start:
        raise RuntimeError("V2 implementation changed during execution.")
    source_descriptors = {
        name: relative_artifact_descriptor(path, repo_root=root)
        for name, path in source_paths.items()
    }
    for name, descriptor in source_descriptors.items():
        _require_same_descriptor(
            descriptor,
            config["source"][name],
            label=f"Post-computation source {name}",
        )

    output_paths = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    targets = _output_targets(config, output_paths)
    table_path = atomic_write_parquet(table, targets["table"])
    table_descriptor = relative_artifact_descriptor(table_path, repo_root=root)
    lower_column = "marginal_mean_score_outcome_gap_lower"
    upper_column = "marginal_mean_score_outcome_gap_upper"
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_clean_tagged_marginal_mean_score_outcome_gap_v2",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": protocol_commit,
        "estimand": ESTIMAND,
        "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
        "source_artifacts": source_descriptors,
        "nested_source_reconciliation": {
            "receipt_to_summary": True,
            "receipt_to_freeze": True,
            "evaluation_to_freeze": True,
            "evaluation_to_freeze_protocol_identity": True,
            "freeze_to_scores": True,
            "evaluation_to_endpoint_artifact": True,
            "embedded_endpoint_rows_to_artifact": True,
        },
        "source_column_allowlists": {
            "scores": [
                "id",
                "issue_d",
                "design_split",
                *(str(value) for value in design["score_columns"].values()),
            ],
            "endpoint_resolution_audit": list(ENDPOINT_COLUMNS),
            "row_level_evaluation_outcomes_loaded": False,
        },
        "candidate_census": {
            "role": str(design["role"]),
            "rows": int(design["expected_candidates"]),
            "unique_nonmissing_ids": int(design["expected_candidates"]),
            "candidate_id_sha256": result.candidate_id_sha256,
            "issue_months": list(result.issue_months),
            "all_five_scores_share_the_same_rows": True,
        },
        "endpoint_census": {
            "cutoff": str(design["endpoint_cutoff"]),
            "charged_off_availability_lag_months": int(
                design["charged_off_availability_lag_months"]
            ),
            "resolved_rows": int(design["expected_resolved"]),
            "resolved_nondefaults": int(design["expected_resolved_y0"]),
            "resolved_defaults": int(design["expected_resolved_y1"]),
            "unresolved_rows": int(design["expected_unresolved"]),
            "reason_census": list(result.endpoint_reason_census),
        },
        "results": {
            "learners": int(len(table)),
            "learner_order": table["learner"].astype(str).tolist(),
            "outcome_mean_identification_interval": [
                float(table["outcome_mean_lower"].iloc[0]),
                float(table["outcome_mean_upper"].iloc[0]),
            ],
            "identification_width": float(table["identification_width"].iloc[0]),
            "mean_score_range": [
                float(table["mean_score"].min()),
                float(table["mean_score"].max()),
            ],
            "gap_lower_range": [
                float(table[lower_column].min()),
                float(table[lower_column].max()),
            ],
            "gap_upper_range": [
                float(table[upper_column].min()),
                float(table[upper_column].max()),
            ],
            "all_results_reported_without_sign_condition": True,
        },
        "identification": {
            "lower_endpoint": "mean_score - (resolved_defaults + unresolved_outcomes) / N",
            "upper_endpoint": "mean_score - resolved_defaults / N",
            "sharp_binary_completions": True,
            "sampling_interval": False,
        },
        "reporting_contract": dict(config["reporting_contract"]),
        "schema": dataframe_schema(table),
        "artifacts": {"marginal_mean_score_outcome_gap": table_descriptor},
        "implementation_provenance": implementation_start,
        "environment": environment_provenance(root),
        "initial_git": initial_git,
        "protected_stages_run": [],
        "protected_artifacts_read": [],
        "protected_artifacts_written": [],
    }
    summary_path = atomic_write_json(targets["summary"], summary)
    summary_descriptor = relative_artifact_descriptor(summary_path, repo_root=root)
    final_git = git_provenance(root)
    receipt = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_clean_tagged_marginal_mean_score_outcome_gap_v2_receipt",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": protocol_commit,
        "started_at_utc": started_at,
        "completed_at_utc": _utc_now(),
        "runtime_seconds": float(time.perf_counter() - started_counter),
        "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
        "implementation_provenance": implementation_start,
        "sources": source_descriptors,
        "summary": summary_descriptor,
        "artifacts": {"marginal_mean_score_outcome_gap": table_descriptor},
        "initial_git": initial_git,
        "final_git": final_git,
        "environment": environment_provenance(root),
        "protected_stages_run": [],
        "protected_artifacts_read": [],
        "protected_artifacts_written": [],
    }
    atomic_write_json(targets["execution_receipt"], receipt)
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
