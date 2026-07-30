"""Run the clean-tagged direct-Git marginal score--outcome-gap V3I."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.ijds_audit.marginal_mean_score_outcome_gap_v3i import (
    ENDPOINT_REASONS,
    MarginalGapTables,
    build_marginal_gap_tables,
    build_row_level_endpoint,
    scan_primary_oot_raw_archive,
)
from src.utils.isolated_experiment import (
    OutputPaths,
    dataframe_schema,
    git_provenance,
    implementation_provenance,
    package_version,
    prepare_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_git_tag,
    resolve_isolated_run_dir,
    write_csv_atomic,
)
from src.utils.pipeline_runtime import atomic_write_json

ROOT = Path(__file__).resolve().parents[2]
RUN_TAG = "ijds-marginal-mean-score-outcome-gap-2026-07-29-v3i"
PROTOCOL_TAG = "protocol/ijds-marginal-mean-score-outcome-gap-2026-07-29-v3i"
ARTIFACT_TAG = "artifacts/ijds-marginal-mean-score-outcome-gap-2026-07-29-v3i"
LOCKED_CONFIG_PATH = Path(
    "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-29_v3i.yaml"
)
PROTOCOL_PATH = Path(
    "docs/research/ijds_marginal_mean_score_outcome_gap_v3i_protocol_2026-07-29.md"
)
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
SOURCE_KEYS = (
    "credit_control_freeze",
    "scores",
    "raw_archive",
    "raw_audit_evidence",
    "raw_audit_config",
)
LEARNERS = (
    "catboost_platt",
    "numeric_logistic_platt",
    "catboost_monotonic_platt",
    "woe_scorecard_platform_platt",
    "woe_scorecard_borrower_platt",
)
ISSUE_MONTHS = tuple(str(value) for value in pd.period_range("2016-04", "2017-06", freq="M"))
OUTPUT_SUFFIXES = {
    "table": ".csv",
    "endpoint_reason_census": ".csv",
    "monthly_endpoint_reason_census": ".csv",
    "summary": ".json",
    "execution_receipt": ".json",
}
IMPLEMENTATION_PATHS = (
    PROTOCOL_PATH,
    Path("scripts/experiments/run_ijds_marginal_mean_score_outcome_gap_v3i.py"),
    Path("src/ijds_audit/marginal_mean_score_outcome_gap_v3i.py"),
    Path("src/data/outcome_observability.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("uv.lock"),
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _resolve_locked_config_path(config_path: Path, *, repo_root: Path) -> Path:
    expected = (repo_root / LOCKED_CONFIG_PATH).resolve()
    candidate = config_path if config_path.is_absolute() else repo_root / config_path
    resolved = candidate.resolve()
    if resolved != expected:
        raise ValueError(f"V3I requires the canonical tracked config at {expected}.")
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    return resolved


def _canonical_descriptor_path(descriptor: Mapping[str, Any], *, label: str) -> Path:
    raw = descriptor.get("path")
    if not isinstance(raw, str) or not raw:
        raise TypeError(f"{label} descriptor omits a path.")
    path = Path(raw)
    if (
        path.is_absolute()
        or path.drive
        or path.root
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != raw
    ):
        raise ValueError(f"{label} descriptor path is unsafe or noncanonical: {raw!r}.")
    return path


def _validate_descriptor(descriptor: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(descriptor, Mapping) or set(descriptor) != {"path", "bytes", "sha256"}:
        raise TypeError(f"{label} must be an exact path/bytes/sha256 descriptor.")
    _canonical_descriptor_path(descriptor, label=label)
    byte_count = descriptor["bytes"]
    digest = descriptor["sha256"]
    if (
        isinstance(byte_count, bool)
        or not isinstance(byte_count, int)
        or byte_count <= 0
        or not isinstance(digest, str)
        or len(digest) != 64
        or any(value not in "0123456789abcdef" for value in digest)
    ):
        raise ValueError(f"{label} has an invalid byte count or SHA-256.")
    return descriptor


def _validate_output_names(config: Mapping[str, Any]) -> dict[str, str]:
    output = config.get("output")
    if not isinstance(output, Mapping):
        raise TypeError("V3I output contract must be a mapping.")
    if set(output) != {"data_root", "model_root", "immutability", *OUTPUT_SUFFIXES}:
        raise RuntimeError("V3I output fields changed.")
    if output["immutability"] != "hard_no_overwrite_choose_fresh_run_tag":
        raise RuntimeError("V3I output immutability changed.")
    names: dict[str, str] = {}
    for key, suffix in OUTPUT_SUFFIXES.items():
        rendered = str(output[key])
        candidate = Path(rendered)
        if candidate.name != rendered or rendered in {"", ".", ".."} or candidate.suffix != suffix:
            raise ValueError(f"V3I output {key!r} is not a safe {suffix} basename.")
        names[key] = rendered
    if len({value.casefold() for value in names.values()}) != len(names):
        raise ValueError("V3I output basenames alias case-insensitively.")
    return names


def _validate_artifact_transport(config: Mapping[str, Any]) -> dict[str, Any]:
    transport = config.get("artifact_transport")
    if not isinstance(transport, dict) or set(transport) != {
        "artifact_tag",
        "artifact_commit_relationship",
        "exact_tracked_paths",
        "pending_at_runner_exit",
        "dvc_required",
    }:
        raise RuntimeError("V3I artifact-transport contract changed.")
    output = config["output"]
    data_prefix = Path(str(output["data_root"])) / RUN_TAG
    model_prefix = Path(str(output["model_root"])) / RUN_TAG
    expected_paths = [
        *(
            data_prefix / str(output[key])
            for key in (
                "table",
                "endpoint_reason_census",
                "monthly_endpoint_reason_census",
            )
        ),
        *(model_prefix / str(output[key]) for key in ("summary", "execution_receipt")),
    ]
    expected_rendered = [path.as_posix() for path in expected_paths]
    if (
        transport["artifact_tag"] != ARTIFACT_TAG
        or transport["artifact_commit_relationship"] != "single_direct_child_of_protocol_commit"
        or transport["exact_tracked_paths"] != expected_rendered
        or transport["pending_at_runner_exit"] is not True
        or transport["dvc_required"] is not False
    ):
        raise RuntimeError("V3I artifact-transport identity changed.")
    return dict(transport)


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("V3I config must be a mapping.")
    required_top = {
        "schema_version",
        "status",
        "protocol_tag",
        "run_tag",
        "protocol_path",
        "artifact_transport",
        "source",
        "design",
        "prior_inspection",
        "interpretation",
        "stop_rules",
        "output",
    }
    if set(payload) != required_top:
        raise RuntimeError("V3I top-level config fields changed.")
    identities = {
        "schema_version": "2026-07-29.3i",
        "status": "post_inspection_direct_git_recovery_locked_before_v3i_execution",
        "protocol_tag": PROTOCOL_TAG,
        "run_tag": RUN_TAG,
        "protocol_path": PROTOCOL_PATH.as_posix(),
    }
    for key, expected_identity in identities.items():
        if payload[key] != expected_identity:
            raise RuntimeError(f"V3I identity field {key!r} changed.")
    source = payload["source"]
    if not isinstance(source, Mapping) or tuple(source) != SOURCE_KEYS:
        raise RuntimeError("V3I source registry changed or was reordered.")
    for key in SOURCE_KEYS:
        _validate_descriptor(source[key], label=f"source.{key}")

    design = payload["design"]
    if not isinstance(design, Mapping):
        raise TypeError("V3I design must be a mapping.")
    fixed_design = {
        "role": "primary_oot",
        "term_months": 36,
        "primary_oot_start_month": "2016-04",
        "primary_oot_end_month": "2017-06",
        "endpoint_cutoff": "2020-09-30",
        "charged_off_availability_lag_months": 6,
        "csv_chunksize": 100000,
        "expected_raw_rows": 2925493,
        "expected_candidates": 376890,
        "expected_candidate_id_sha256": (
            "72799b236a7e45d8746099adefba7da5683e8308959643d6ad341d3585e8fa74"
        ),
        "expected_endpoint_row_sha256": (
            "04c4d182b1223dc1c92df0898d4cd25e0a44fedded46dc1f52af62ba3d9317b6"
        ),
        "expected_resolved": 364814,
        "expected_unresolved": 12076,
        "expected_resolved_y0": 307842,
        "expected_resolved_y1": 56972,
    }
    for key, expected_value in fixed_design.items():
        if design.get(key) != expected_value:
            raise RuntimeError(f"V3I design field {key!r} changed.")
    if tuple(str(value) for value in design.get("raw_required_columns", ())) != (
        "id",
        "issue_d",
        "term",
        "loan_status",
        "last_pymnt_d",
    ):
        raise RuntimeError("V3I raw-column allowlist changed.")
    if tuple(str(value) for value in design.get("issue_months", ())) != ISSUE_MONTHS:
        raise RuntimeError("V3I issue-month domain changed.")
    if tuple(str(value) for value in design.get("learners", ())) != LEARNERS:
        raise RuntimeError("V3I learner census changed.")
    score_columns = design.get("score_columns")
    if not isinstance(score_columns, Mapping) or tuple(score_columns) != LEARNERS:
        raise RuntimeError("V3I score-column mapping changed or was reordered.")
    reason_census = design.get("endpoint_reason_census")
    monthly_census = design.get("monthly_reason_candidate_rows")
    if not isinstance(reason_census, Mapping) or tuple(reason_census) != ENDPOINT_REASONS:
        raise RuntimeError("V3I endpoint reason census changed or was reordered.")
    if not isinstance(monthly_census, Mapping) or tuple(monthly_census) != ISSUE_MONTHS:
        raise RuntimeError("V3I monthly endpoint census changed or was reordered.")
    for month in ISSUE_MONTHS:
        cell = monthly_census[month]
        if not isinstance(cell, Mapping) or tuple(cell) != ENDPOINT_REASONS:
            raise RuntimeError(f"V3I monthly endpoint reasons changed for {month}.")

    prior = payload["prior_inspection"]
    if not isinstance(prior, Mapping) or set(prior) != {
        "lineage",
        "reconciliation_absolute_tolerance",
        "outcome_mean_lower",
        "outcome_mean_upper",
        "identification_width",
        "learner_rows",
    }:
        raise RuntimeError("V3I prior-inspection disclosure fields changed.")
    if prior["lineage"] != "v3h_complete_local_arithmetic_transport_blocked_not_active":
        raise RuntimeError("V3I prior-lineage status changed.")
    if float(prior["reconciliation_absolute_tolerance"]) != 1.0e-15:
        raise RuntimeError("V3I reconciliation tolerance changed.")
    prior_rows = prior["learner_rows"]
    if not isinstance(prior_rows, Mapping) or tuple(prior_rows) != LEARNERS:
        raise RuntimeError("V3I disclosed V3H learner rows changed or were reordered.")
    for learner in LEARNERS:
        row = prior_rows[learner]
        if not isinstance(row, Mapping) or set(row) != {
            "score_sum",
            "mean_score",
            "gap_lower",
            "gap_upper",
        }:
            raise RuntimeError(f"V3I V3H disclosure fields changed for {learner}.")
        if not all(np.isfinite(float(value)) for value in row.values()):
            raise RuntimeError(f"V3I V3H disclosure contains a nonfinite value for {learner}.")

    expected_interpretation = {
        "post_inspection": True,
        "preregistered": False,
        "confirmatory": False,
        "independent_replication": False,
        "deterministic_finite_archive_partial_identification": True,
        "complete_five_learner_census": True,
        "row_level_outcomes_persisted": False,
        "no_p_values": True,
        "no_causal_or_mechanism_claim": True,
        "no_mar_mnar_claim": True,
        "no_conformal_validity_claim": True,
        "no_selected_or_funded_set_claim": True,
        "no_prospective_claim": True,
        "no_model_winner_or_ranking": True,
        "no_dvc_requirement": True,
        "protected_sources_read_only": True,
        "absolute_paths_serialized": False,
    }
    if payload["interpretation"] != expected_interpretation:
        raise RuntimeError("V3I interpretation boundary changed.")
    stop_rules = payload["stop_rules"]
    if not isinstance(stop_rules, Mapping) or set(stop_rules) != {
        "stop_on_dirty_or_untagged_head",
        "stop_on_protected_read_root_equals_execution_root",
        "stop_on_unsafe_path_or_root_escape",
        "stop_on_source_hash_or_byte_drift",
        "stop_on_frozen_lineage_or_nested_descriptor_drift",
        "stop_on_score_schema_or_census_drift",
        "stop_on_raw_archive_or_candidate_census_drift",
        "stop_on_nonbijective_join_or_month_mismatch",
        "stop_on_endpoint_reason_month_or_hash_drift",
        "stop_on_nonfinite_score_or_invalid_bound",
        "stop_on_v3h_arithmetic_nonreconciliation",
        "stop_on_implementation_drift",
        "stop_on_preexisting_output",
        "stop_on_result_sign_or_learner_order",
    }:
        raise RuntimeError("V3I stop-rule fields changed.")
    if stop_rules["stop_on_result_sign_or_learner_order"] is not False or any(
        value is not True
        for key, value in stop_rules.items()
        if key != "stop_on_result_sign_or_learner_order"
    ):
        raise RuntimeError("V3I fail-closed stop-rule values changed.")
    _validate_output_names(payload)
    _validate_artifact_transport(payload)
    return payload


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
        raise FileExistsError(f"V3I output directories already exist: {existing}.")
    _output_targets(config, paths)


def _output_targets(config: Mapping[str, Any], paths: OutputPaths) -> dict[str, Path]:
    names = _validate_output_names(config)
    return {
        key: (paths.model_dir if key in {"summary", "execution_receipt"} else paths.data_dir) / name
        for key, name in names.items()
    }


def _verified_protected_path(descriptor: Mapping[str, Any], *, protected_read_root: Path) -> Path:
    _validate_descriptor(descriptor, label="protected source")
    root = protected_read_root.resolve()
    path = (root / str(descriptor["path"])).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("Protected input escaped --protected-read-root.") from exc
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = relative_artifact_descriptor(path, repo_root=root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor[field]:
            raise RuntimeError(f"Protected source mismatched on {field}: {descriptor['path']}.")
    return path


def _source_descriptors(
    paths: Mapping[str, Path], *, protected_read_root: Path
) -> dict[str, dict[str, Any]]:
    return {
        key: relative_artifact_descriptor(path, repo_root=protected_read_root)
        for key, path in paths.items()
    }


def _require_exact_source_snapshot(
    actual: Mapping[str, Mapping[str, Any]],
    config: Mapping[str, Any],
    *,
    stage: str,
) -> None:
    source = config["source"]
    expected = {key: dict(source[key]) for key in SOURCE_KEYS}
    observed = {key: dict(actual[key]) for key in SOURCE_KEYS}
    if observed != expected:
        raise RuntimeError(
            f"The {stage} protected-source snapshot does not equal the locked V3I YAML "
            "descriptors."
        )


def _require_nested_descriptor(actual: Any, expected: Mapping[str, Any], *, label: str) -> None:
    if not isinstance(actual, Mapping):
        raise TypeError(f"{label} nested descriptor is missing.")
    for field in ("path", "bytes", "sha256"):
        if actual.get(field) != expected[field]:
            raise RuntimeError(f"{label} nested descriptor changed on {field}.")


def _verify_git_lineage(repo_root: Path, *, protocol_commit: str) -> dict[str, Any]:
    source_tag = "protocol/ijds-credit-risk-controls-2026-07-13-v1b"
    source_commit = "1776cbf8b201ae5b92756e5ea397a403d6cc7c9f"
    if resolve_git_tag(repo_root, source_tag) != source_commit:
        raise RuntimeError("The frozen credit-control protocol tag changed.")
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, protocol_commit],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError("The V1b score-freeze commit is not an ancestor of V3I.")
    return {
        "source_protocol_tag": source_tag,
        "source_protocol_commit": source_commit,
        "source_commit_is_ancestor": True,
    }


def _load_verified_sources(
    config: Mapping[str, Any],
    *,
    protected_read_root: Path,
    repo_root: Path,
    protocol_commit: str,
) -> tuple[dict[str, Path], dict[str, Any], dict[str, dict[str, Any]]]:
    source = config["source"]
    paths = {
        key: _verified_protected_path(source[key], protected_read_root=protected_read_root)
        for key in SOURCE_KEYS
    }
    source_start = _source_descriptors(paths, protected_read_root=protected_read_root)
    _require_exact_source_snapshot(source_start, config, stage="initial")
    freeze = json.loads(paths["credit_control_freeze"].read_text(encoding="utf-8"))
    if (
        freeze.get("status") != "credit_control_scores_frozen_before_primary_oot_outcome_join"
        or freeze.get("run_tag") != "ijds-credit-risk-controls-2026-07-13-v1b"
        or freeze.get("protocol_tag") != "protocol/ijds-credit-risk-controls-2026-07-13-v1b"
        or freeze.get("protocol_commit") != "1776cbf8b201ae5b92756e5ea397a403d6cc7c9f"
        or freeze.get("model_selection") != "none_all_five_reported"
        or freeze.get("window_selection") != "none_all_eight_reported"
        or freeze.get("portfolio_optimization") is not False
        or freeze.get("sampling") != "none_all_eligible_rows"
        or freeze.get("primary_oot_outcome_columns_in_frozen_scores") != []
        or freeze.get("source_inventory", {}).get("retained_rows_by_split", {}).get("primary_oot")
        != 376890
        or freeze.get("protected_stages_run") != []
        or freeze.get("protected_artifacts_written") != []
    ):
        raise RuntimeError("The outcome-free V1b score-freeze contract changed.")
    _require_nested_descriptor(
        freeze.get("outcome_free_artifacts", {}).get("scores"),
        source["scores"],
        label="V1b-freeze-to-scores",
    )
    raw_audit = json.loads(paths["raw_audit_evidence"].read_text(encoding="utf-8"))
    if (
        raw_audit.get("status") != "complete_full_archive_data_contract_audit"
        or raw_audit.get("run_tag") != "ijds-raw-data-contract-2026-07-14-v2"
        or raw_audit.get("results", {}).get("raw_rows") != 2925493
        or raw_audit.get("protected_stages_run") != []
        or raw_audit.get("protected_artifacts_written") != []
    ):
        raise RuntimeError("The registered raw-data audit contract changed.")
    _require_nested_descriptor(
        raw_audit.get("config"), source["raw_audit_config"], label="raw-audit-to-config"
    )
    _require_nested_descriptor(
        raw_audit.get("raw_source"), source["raw_archive"], label="raw-audit-to-archive"
    )
    return (
        paths,
        {
            "credit_control_freeze_verified": True,
            "freeze_to_scores_descriptor_verified": True,
            "raw_audit_to_config_and_archive_verified": True,
            "git_lineage": _verify_git_lineage(repo_root, protocol_commit=protocol_commit),
            "dvc_required": False,
        },
        source_start,
    )


def _reconcile_v3h(tables: MarginalGapTables, config: Mapping[str, Any]) -> dict[str, Any]:
    prior = config["prior_inspection"]
    tolerance = float(prior["reconciliation_absolute_tolerance"])
    rows = tables.table.set_index("learner")
    differences: list[float] = []
    for learner in LEARNERS:
        expected = prior["learner_rows"][learner]
        comparisons = {
            "score_sum": float(rows.loc[learner, "score_sum"]),
            "mean_score": float(rows.loc[learner, "mean_score"]),
            "gap_lower": float(rows.loc[learner, "marginal_mean_score_outcome_gap_lower"]),
            "gap_upper": float(rows.loc[learner, "marginal_mean_score_outcome_gap_upper"]),
        }
        for field, observed in comparisons.items():
            difference = abs(observed - float(expected[field]))
            differences.append(difference)
            if not np.isclose(observed, float(expected[field]), atol=tolerance, rtol=0.0):
                raise RuntimeError(f"V3I did not reconcile V3H on {learner}/{field}.")
    first = tables.table.iloc[0]
    global_comparisons = {
        "outcome_mean_lower": float(first["outcome_mean_lower"]),
        "outcome_mean_upper": float(first["outcome_mean_upper"]),
        "identification_width": float(first["identification_width"]),
    }
    for field, observed in global_comparisons.items():
        difference = abs(observed - float(prior[field]))
        differences.append(difference)
        if not np.isclose(observed, float(prior[field]), atol=tolerance, rtol=0.0):
            raise RuntimeError(f"V3I did not reconcile V3H on {field}.")
    return {
        "prior_lineage": str(prior["lineage"]),
        "all_five_rows_reconciled": True,
        "absolute_tolerance": tolerance,
        "maximum_absolute_difference": max(differences, default=0.0),
        "identity_gate_not_sign_or_model_selection": True,
    }


def _sanitized_environment() -> dict[str, Any]:
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "packages": {
            name: package_version(name) for name in ("numpy", "pandas", "pyarrow", "PyYAML")
        },
        "absolute_executable_path_serialized": False,
    }


def run(
    *,
    config_path: Path,
    protected_read_root: Path,
    repo_root: Path = ROOT,
) -> Path:
    """Execute V3I from exact sources under an explicit distinct read root."""
    started_at = _utc_now()
    started_counter = time.perf_counter()
    root = repo_root.resolve()
    protected_root = protected_read_root.resolve()
    if not protected_root.is_dir():
        raise NotADirectoryError(protected_root)
    if protected_root == root:
        raise RuntimeError("V3I requires --protected-read-root to differ from the run clone.")
    resolved_config = _resolve_locked_config_path(config_path, repo_root=root)
    config = _load_config(resolved_config)
    _preflight_output_paths(config, repo_root=root)
    protocol_commit = require_clean_tagged_head(root, PROTOCOL_TAG)
    protocol_path = (root / PROTOCOL_PATH).resolve()
    if not protocol_path.is_file():
        raise FileNotFoundError(protocol_path)
    implementation_start = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    initial_git = git_provenance(root)
    if initial_git.get("commit") != protocol_commit or initial_git.get("dirty") is not False:
        raise RuntimeError("V3I Git state changed after the clean-tag gate.")

    source_paths, lineage, source_start = _load_verified_sources(
        config,
        protected_read_root=protected_root,
        repo_root=root,
        protocol_commit=protocol_commit,
    )
    scores = pd.read_parquet(source_paths["scores"])
    design = config["design"]
    score_columns = tuple(str(value) for value in design["score_columns"].values())
    expected_score_columns = {"id", "issue_d", "design_split", *score_columns}
    if set(scores.columns) != expected_score_columns or len(scores.columns) != 8:
        raise RuntimeError("The frozen score table schema changed.")
    primary_ids = scores.loc[scores["design_split"].astype(str).eq("primary_oot"), "id"]
    scan = scan_primary_oot_raw_archive(
        source_paths["raw_archive"],
        required_columns=tuple(str(value) for value in design["raw_required_columns"]),
        csv_chunksize=int(design["csv_chunksize"]),
        term_months=int(design["term_months"]),
        start_month=str(design["primary_oot_start_month"]),
        end_month=str(design["primary_oot_end_month"]),
        expected_raw_rows=int(design["expected_raw_rows"]),
        expected_candidates=int(design["expected_candidates"]),
        expected_issue_months=tuple(str(value) for value in design["issue_months"]),
        expected_candidate_ids=primary_ids,
    )
    endpoint = build_row_level_endpoint(
        scan.frame,
        cutoff=str(design["endpoint_cutoff"]),
        charged_off_lag_months=int(design["charged_off_availability_lag_months"]),
    )
    tables = build_marginal_gap_tables(
        scores,
        endpoint,
        learners=tuple(str(value) for value in design["learners"]),
        score_columns={str(key): str(value) for key, value in design["score_columns"].items()},
        expected_issue_months=tuple(str(value) for value in design["issue_months"]),
        expected_candidate_id_sha256=str(design["expected_candidate_id_sha256"]),
        expected_endpoint_row_sha256=str(design["expected_endpoint_row_sha256"]),
        expected_reason_census=design["endpoint_reason_census"],
        expected_monthly_reason_candidate_rows=design["monthly_reason_candidate_rows"],
        expected_candidates=int(design["expected_candidates"]),
        expected_resolved=int(design["expected_resolved"]),
        expected_unresolved=int(design["expected_unresolved"]),
        expected_resolved_y0=int(design["expected_resolved_y0"]),
        expected_resolved_y1=int(design["expected_resolved_y1"]),
    )
    v3h_reconciliation = _reconcile_v3h(tables, config)

    source_end = _source_descriptors(source_paths, protected_read_root=protected_root)
    _require_exact_source_snapshot(source_end, config, stage="final")
    if source_end != source_start:
        raise RuntimeError("A protected V3I source changed during execution.")
    implementation_end = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    if implementation_end != implementation_start:
        raise RuntimeError("V3I implementation changed during execution.")
    final_prewrite_git = git_provenance(root)
    if final_prewrite_git != initial_git:
        raise RuntimeError("V3I Git state changed during computation.")

    paths = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    targets = _output_targets(config, paths)
    frames = {
        "table": tables.table,
        "endpoint_reason_census": tables.endpoint_reason_census,
        "monthly_endpoint_reason_census": tables.monthly_endpoint_reason_census,
    }
    written = {key: write_csv_atomic(frame, targets[key]) for key, frame in frames.items()}
    artifacts = {
        key: relative_artifact_descriptor(path, repo_root=root) for key, path in written.items()
    }
    result_table = tables.table
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_clean_tagged_calculation_pending_git_artifact_commit_v3i",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": protocol_commit,
        "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
        "post_inspection": {
            "preregistered": False,
            "confirmatory": False,
            "independent_replication": False,
            "v3h_results_disclosed_before_v3i_execution": True,
        },
        "source_artifacts": source_start,
        "source_lineage": lineage,
        "raw_scan": scan.audit,
        "candidate_identity": tables.join_audit,
        "endpoint": {
            "cutoff": str(design["endpoint_cutoff"]),
            "charged_off_availability_lag_months": int(
                design["charged_off_availability_lag_months"]
            ),
            "endpoint_row_sha256": tables.endpoint_row_sha256,
            "reason_census": tables.endpoint_reason_census.to_dict(orient="records"),
            "resolved_rows": int(design["expected_resolved"]),
            "resolved_nondefaults": int(design["expected_resolved_y0"]),
            "resolved_defaults": int(design["expected_resolved_y1"]),
            "unresolved_rows": int(design["expected_unresolved"]),
        },
        "identification": {
            "estimand": "marginal_mean_score_outcome_gap",
            "completion_class": "unrestricted_binary_assignments_to_unresolved_rows",
            "outcome_mean_interval": [
                float(result_table["outcome_mean_lower"].iloc[0]),
                float(result_table["outcome_mean_upper"].iloc[0]),
            ],
            "identification_width": float(result_table["identification_width"].iloc[0]),
            "identified_grid_points": int(result_table["identified_grid_points"].iloc[0]),
            "identified_grid_step": float(result_table["identified_grid_step"].iloc[0]),
            "reported_interval_is_hull": True,
            "joint_exact_set_is_shared_collinear_grid_not_cartesian_product": True,
        },
        "results": {
            "learners": int(len(result_table)),
            "learner_order": result_table["learner"].astype(str).tolist(),
            "mean_score_range": [
                float(result_table["mean_score"].min()),
                float(result_table["mean_score"].max()),
            ],
            "gap_lower_range": [
                float(result_table["marginal_mean_score_outcome_gap_lower"].min()),
                float(result_table["marginal_mean_score_outcome_gap_lower"].max()),
            ],
            "gap_upper_range": [
                float(result_table["marginal_mean_score_outcome_gap_upper"].min()),
                float(result_table["marginal_mean_score_outcome_gap_upper"].max()),
            ],
            "all_rows_reported_without_sign_or_ranking_selection": True,
        },
        "v3h_arithmetic_reconciliation": v3h_reconciliation,
        "schemas": {key: dataframe_schema(frame) for key, frame in frames.items()},
        "artifacts": artifacts,
        "artifact_transport": _validate_artifact_transport(config),
        "interpretation": dict(config["interpretation"]),
        "implementation": implementation_start,
        "environment": _sanitized_environment(),
        "git": initial_git,
        "transport": {
            "source_materialization": "explicit_distinct_hash_bound_source_root",
            "dvc_required": False,
            "git_small_outputs": True,
            "absolute_paths_serialized": False,
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    summary_path = atomic_write_json(targets["summary"], summary)
    receipt = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_calculation_pending_git_artifact_commit",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": protocol_commit,
        "started_at_utc": started_at,
        "completed_at_utc": _utc_now(),
        "elapsed_seconds": time.perf_counter() - started_counter,
        "summary": relative_artifact_descriptor(summary_path, repo_root=root),
        "artifacts": artifacts,
        "artifact_transport": _validate_artifact_transport(config),
        "v3h_arithmetic_reconciliation": v3h_reconciliation,
        "dvc_commands_run": [],
        "protected_stages_run": [],
        "protected_artifacts_written": [],
        "absolute_paths_serialized": False,
    }
    atomic_write_json(targets["execution_receipt"], receipt)
    return summary_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=LOCKED_CONFIG_PATH)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument(
        "--protected-read-root",
        type=Path,
        required=True,
        help="Separate repository-shaped root containing the exact registered sources.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary_path = run(
        config_path=args.config,
        protected_read_root=args.protected_read_root,
        repo_root=args.repo_root,
    )
    print(summary_path)


if __name__ == "__main__":
    main()
