"""Run the clean-tagged fixed-support funded-selection estimand audit V1."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.ijds_audit.funded_selection_estimand import (
    FundedSelectionTables,
    build_funded_selection_estimand_audit,
)
from src.utils.isolated_experiment import (
    OutputPaths,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    prepare_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_isolated_run_dir,
    sha256_file,
)
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_parquet

ROOT = Path(__file__).resolve().parents[2]
RUN_TAG = "ijds-funded-selection-estimand-audit-2026-07-29-v1"
PROTOCOL_TAG = "protocol/ijds-funded-selection-estimand-audit-2026-07-29-v1"
ARTIFACT_TAG = "artifacts/ijds-funded-selection-estimand-audit-2026-07-29-v1"
LOCKED_CONFIG_PATH = Path(
    "configs/experiments/ijds_funded_selection_estimand_audit_2026-07-29_v1.yaml"
)
PROTOCOL_PATH = Path("docs/research/ijds_funded_selection_estimand_audit_v1_protocol_2026-07-29.md")
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
IMPLEMENTATION_PATHS = (
    PROTOCOL_PATH,
    Path("src/ijds_audit/funded_selection_estimand.py"),
    Path("src/evaluation/coverage_transport.py"),
    Path("scripts/experiments/run_ijds_funded_selection_estimand_audit_v1.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("uv.lock"),
)
SOURCE_KEYS = (
    "allocation_freeze",
    "continuous_parent_allocations",
    "rounded_allocations",
    "granularity_summary",
    "granularity_contrasts",
    "evaluation_manifest",
    "joined_funded_allocations",
)
OUTPUT_SUFFIXES = {
    "monthly_bounds": ".parquet",
    "track_bounds": ".parquet",
    "monthly_gamma_contrasts": ".parquet",
    "track_gamma_contrasts": ".parquet",
    "support_and_fixed_capital_reconciliation": ".parquet",
    "summary": ".json",
    "execution_receipt": ".json",
}
MANIFEST_IDENTITY_KEYS = (
    "schema_version",
    "status",
    "run_tag",
    "protocol_tag",
    "protocol_commit",
)


def _portable_environment(repo_root: Path) -> dict[str, Any]:
    """Bind the interpreter bytes without serializing a machine-specific path."""
    payload = dict(environment_provenance(repo_root))
    executable = Path(str(payload.pop("executable")))
    if not executable.is_file():
        raise FileNotFoundError(executable)
    payload["executable"] = {
        "basename": executable.name,
        "bytes": int(executable.stat().st_size),
        "sha256": sha256_file(executable),
    }
    payload["absolute_paths_recorded"] = False
    return payload


def _manifest_identity(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Keep lineage identities while excluding historical machine-local payloads."""
    return {key: payload.get(key) for key in MANIFEST_IDENTITY_KEYS}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _resolve_locked_config_path(config_path: Path, *, repo_root: Path) -> Path:
    expected = (repo_root / LOCKED_CONFIG_PATH).resolve()
    candidate = config_path if config_path.is_absolute() else repo_root / config_path
    resolved = candidate.resolve()
    if resolved != expected:
        raise ValueError(f"V1 requires the locked config at {expected}.")
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    return resolved


def _validate_descriptor(descriptor: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(descriptor, Mapping) or set(descriptor) != {"path", "bytes", "sha256"}:
        raise TypeError(f"{label} must be an exact path/bytes/sha256 descriptor.")
    path = Path(str(descriptor["path"]))
    digest = str(descriptor["sha256"])
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} path must be repository-relative and traversal-free.")
    if int(descriptor["bytes"]) <= 0 or len(digest) != 64:
        raise ValueError(f"{label} has an invalid byte count or SHA-256 digest.")
    return descriptor


def _validate_output_names(config: Mapping[str, Any]) -> dict[str, str]:
    output = config.get("output")
    if not isinstance(output, Mapping):
        raise TypeError("V1 output contract must be a mapping.")
    expected = {"data_root", "model_root", "immutability", *OUTPUT_SUFFIXES}
    if set(output) != expected:
        raise RuntimeError("V1 output contract fields changed.")
    if output["immutability"] != "hard_no_overwrite_choose_fresh_run_tag":
        raise RuntimeError("V1 output immutability contract changed.")
    names: dict[str, str] = {}
    for key, suffix in OUTPUT_SUFFIXES.items():
        rendered = str(output[key])
        candidate = Path(rendered)
        if candidate.name != rendered or rendered in {"", ".", ".."} or candidate.suffix != suffix:
            raise ValueError(f"V1 output {key!r} is not a safe {suffix} basename.")
        names[key] = rendered
    if len({value.casefold() for value in names.values()}) != len(names):
        raise ValueError("V1 output basenames alias case-insensitively.")
    return names


def _validate_artifact_transport(config: Mapping[str, Any]) -> dict[str, Any]:
    transport = config.get("artifact_transport")
    expected_fields = {
        "artifact_tag",
        "artifact_commit_relationship",
        "exact_tracked_paths",
        "pending_at_runner_exit",
        "dvc_required",
    }
    if not isinstance(transport, Mapping) or set(transport) != expected_fields:
        raise RuntimeError("V1 artifact-transport contract changed.")

    output = config.get("output")
    if not isinstance(output, Mapping):
        raise TypeError("V1 output contract must be a mapping.")
    if Path(str(output["data_root"])) != ALLOWED_DATA_ROOT or Path(
        str(output["model_root"])
    ) != ALLOWED_MODEL_ROOT:
        raise RuntimeError("V1 output roots changed.")
    _validate_output_names(config)
    data_prefix = ALLOWED_DATA_ROOT / RUN_TAG
    model_prefix = ALLOWED_MODEL_ROOT / RUN_TAG
    nominal_targets = _output_targets(
        config,
        OutputPaths(data_dir=data_prefix, model_dir=model_prefix),
    )
    if set(nominal_targets) != set(OUTPUT_SUFFIXES):
        raise RuntimeError("V1 output-key mapping changed.")
    expected_paths = [nominal_targets[key].as_posix() for key in OUTPUT_SUFFIXES]
    actual_paths = transport["exact_tracked_paths"]
    if not isinstance(actual_paths, list):
        raise TypeError("V1 exact tracked paths must be a list.")
    for raw in actual_paths:
        if not isinstance(raw, str):
            raise TypeError("V1 exact tracked paths must be strings.")
        path = Path(raw)
        if (
            path.is_absolute()
            or path.drive
            or path.root
            or any(part in {"", ".", ".."} for part in path.parts)
            or path.as_posix() != raw
        ):
            raise ValueError(f"V1 tracked artifact path is unsafe: {raw!r}.")
    if len({raw.casefold() for raw in actual_paths}) != len(actual_paths):
        raise RuntimeError("V1 tracked artifact paths alias case-insensitively.")
    if (
        transport["artifact_tag"] != ARTIFACT_TAG
        or transport["artifact_commit_relationship"]
        != "single_direct_child_of_protocol_commit"
        or actual_paths != expected_paths
        or transport["pending_at_runner_exit"] is not True
        or transport["dvc_required"] is not False
    ):
        raise RuntimeError("V1 artifact-transport identity changed.")
    return {
        "artifact_tag": ARTIFACT_TAG,
        "artifact_commit_relationship": "single_direct_child_of_protocol_commit",
        "exact_tracked_paths": expected_paths,
        "pending_at_runner_exit": True,
        "dvc_required": False,
    }


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("V1 config must be a mapping.")
    expected_top = {
        "schema_version",
        "status",
        "protocol_tag",
        "run_tag",
        "artifact_transport",
        "source",
        "design",
        "interpretation",
        "stop_rules",
        "output",
    }
    if set(payload) != expected_top:
        raise RuntimeError("V1 top-level config fields changed.")
    identities = {
        "schema_version": "2026-07-29.1",
        "status": (
            "retrospectively_locked_after_complete_result_inspection_before_clean_tagged_execution"
        ),
        "protocol_tag": PROTOCOL_TAG,
        "run_tag": RUN_TAG,
    }
    for key, expected_identity in identities.items():
        if payload[key] != expected_identity:
            raise RuntimeError(f"V1 locked identity {key!r} changed.")
    source = payload["source"]
    if not isinstance(source, Mapping) or set(source) != set(SOURCE_KEYS):
        raise RuntimeError("V1 protected source registry changed.")
    for key in SOURCE_KEYS:
        _validate_descriptor(source[key], label=f"source.{key}")

    design = payload["design"]
    if not isinstance(design, Mapping):
        raise TypeError("V1 design contract must be a mapping.")
    exact_design: dict[str, object] = {
        "estimand_population": "fixed_usd25_positive_funded_loan_positions",
        "binary_selection_unit": "unique_loan_within_issue_month_and_policy",
        "role": "primary_oot",
        "lot_size_usd": 25.0,
        "committed_budget_usd_per_month": 1_000_000.0,
        "pooling": "pool_selected_loan_positions_over_all_15_months_before_division",
        "count_minus_invested_dollar_contrast": (
            "shared_binary_completion_within_each_policy_track"
        ),
        "count_minus_fixed_capital_contrast": ("shared_binary_completion_within_each_policy_track"),
        "support_and_fixed_capital_reconciliation": (
            "exact_support_lineage_plus_shared_completion_fixed_capital_reconciliation"
        ),
        "gamma_contrast": "gamma1_minus_gamma0_shared_binary_completion",
        "sharpness_scope": "cellwise_not_joint_across_tracks",
        "expected_source_positive_positions": 143175,
        "expected_rounded_positive_positions": 143167,
        "expected_removed_positions": 8,
        "expected_changed_positions": 2985,
        "expected_monthly_portfolios": 1440,
        "expected_policy_tracks": 96,
        "expected_monthly_gamma_contrasts": 720,
        "expected_track_gamma_contrasts": 48,
        "expected_support_and_fixed_capital_reconciliation_tracks": 96,
        "source_rounding_tolerance": 1.0e-8,
        "descriptive_coverage_reference": 0.90,
        "all_cells_reported_without_selection": True,
        "historical_results_previously_inspected": True,
    }
    for key, expected_value in exact_design.items():
        if design.get(key) != expected_value:
            raise RuntimeError(f"V1 design field {key!r} changed.")
    if len(design.get("periods", [])) != 15 or len(design.get("window_ids", [])) != 8:
        raise RuntimeError("V1 period or calibration-window grid changed.")
    if design.get("rulers") != ["objective_matched", "normalized_score"]:
        raise RuntimeError("V1 two-ruler grid changed.")
    if design.get("coordinates") != [0.25, 0.5, 0.75] or design.get("gamma_endpoints") != [
        0.0,
        1.0,
    ]:
        raise RuntimeError("V1 coordinate or gamma endpoint grid changed.")
    tolerance = float(design.get("numerical_tolerance", np.nan))
    if not np.isfinite(tolerance) or tolerance != 1.0e-12:
        raise RuntimeError("V1 numerical tolerance changed.")

    interpretation = payload["interpretation"]
    if not isinstance(interpretation, Mapping):
        raise TypeError("V1 interpretation contract must be a mapping.")
    true_fields = {
        "finite_archive_fixed_support_audit",
        "fcp_compatible_binary_estimand",
        "invested_dollar_selected_weighting_is_a_distinct_estimand",
        "fixed_capital_decision_weighting_is_the_active_granularity_estimand",
        "fixed_capital_is_not_silently_renamed_invested_dollar_coverage",
        "unresolved_outcomes_are_sharply_bounded",
        "continuous_parent_and_outcome_join_are_exactly_reconciled",
    }
    false_fields = {
        "selected_set_conformal_validity",
        "false_coverage_rate_control",
        "jomi_guarantee",
        "exchangeability_claim",
        "prospective_deployment_claim",
        "causal_claim",
        "policy_or_track_selection",
    }
    if any(interpretation.get(key) is not True for key in true_fields) or any(
        interpretation.get(key) is not False for key in false_fields
    ):
        raise RuntimeError("V1 interpretation boundary changed.")
    stop_rules = payload["stop_rules"]
    if (
        not isinstance(stop_rules, Mapping)
        or not stop_rules
        or not all(value is True for value in stop_rules.values())
    ):
        raise RuntimeError("V1 fail-closed stop rules changed.")
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
        raise FileExistsError(f"V1 output directories already exist: {existing}.")
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
            raise RuntimeError(f"Protected source mismatched on {field}: {path}.")
    return path


def _require_nested_descriptor(actual: Any, expected: Mapping[str, Any], *, label: str) -> None:
    if not isinstance(actual, Mapping):
        raise TypeError(f"{label} nested descriptor is missing.")
    for field in ("path", "bytes", "sha256"):
        if actual.get(field) != expected[field]:
            raise RuntimeError(f"{label} nested descriptor changed on {field}.")


def _load_verified_sources(
    config: Mapping[str, Any], *, protected_read_root: Path
) -> tuple[dict[str, Path], dict[str, Any]]:
    source = config["source"]
    paths = {
        key: _verified_protected_path(source[key], protected_read_root=protected_read_root)
        for key in SOURCE_KEYS
    }
    freeze = json.loads(paths["allocation_freeze"].read_text(encoding="utf-8"))
    if (
        freeze.get("status") != "allocation_granularity_frozen_before_outcome_join"
        or freeze.get("run_tag") != "ijds-allocation-granularity-sensitivity-2026-07-16-v3"
        or freeze.get("protocol_tag")
        != "protocol/ijds-allocation-granularity-sensitivity-2026-07-16-v3"
        or freeze.get("outcome_based_selection") is not False
        or freeze.get("outcome_columns_passed_to_rounding") != []
        or float(freeze.get("lot_size_usd", np.nan)) != 25.0
        or float(freeze.get("committed_budget_usd", np.nan)) != 1_000_000.0
    ):
        raise RuntimeError("The registered V3 outcome-free freeze contract changed.")
    expected_results = {
        "portfolios": 1440,
        "source_rows": 143175,
        "rounded_positive_rows": 143167,
        "changed_rows": 2985,
    }
    results = freeze.get("results")
    if not isinstance(results, Mapping) or any(
        results.get(key) != value for key, value in expected_results.items()
    ):
        raise RuntimeError("The registered V3 freeze census changed.")
    _require_nested_descriptor(
        freeze.get("parent", {}).get("allocations"),
        source["continuous_parent_allocations"],
        label="V3-freeze-to-continuous-parent-allocations",
    )
    _require_nested_descriptor(
        freeze.get("artifacts", {}).get("rounded_allocations"),
        source["rounded_allocations"],
        label="V3-freeze-to-rounded-allocations",
    )
    if freeze.get("protected_stages_run") != [] or freeze.get("protected_artifacts_written") != []:
        raise RuntimeError("The V3 freeze reports protected mutations.")

    granularity = json.loads(paths["granularity_summary"].read_text(encoding="utf-8"))
    if (
        granularity.get("status") != "complete_allocation_granularity_sensitivity"
        or granularity.get("run_tag") != "ijds-allocation-granularity-sensitivity-2026-07-16-v3"
        or granularity.get("outcome_based_selection") is not False
        or granularity.get("results", {}).get("tracks") != 96
    ):
        raise RuntimeError("The registered V3 evaluation summary contract changed.")
    _require_nested_descriptor(
        granularity.get("freeze"), source["allocation_freeze"], label="V3-summary-to-freeze"
    )
    _require_nested_descriptor(
        granularity.get("artifacts", {}).get("granularity_contrasts"),
        source["granularity_contrasts"],
        label="V3-summary-to-granularity-contrasts",
    )
    if (
        granularity.get("protected_stages_run") != []
        or granularity.get("protected_artifacts_written") != []
    ):
        raise RuntimeError("The V3 evaluation reports protected mutations.")

    evaluation = json.loads(paths["evaluation_manifest"].read_text(encoding="utf-8"))
    if (
        evaluation.get("status") != "verified_post_freeze_outcome_evaluation_complete"
        or evaluation.get("run_tag") != "ijds-normalized-objective-frontier-2026-07-15-v5"
        or evaluation.get("outcome_columns_joined_after_freeze")
        != ["snapshot_default", "snapshot_resolution"]
    ):
        raise RuntimeError("The registered V5 evaluation contract changed.")
    _require_nested_descriptor(
        evaluation.get("evaluation_artifacts", {}).get("joined_funded_allocations"),
        source["joined_funded_allocations"],
        label="V5-evaluation-to-joined-funded-allocations",
    )
    if (
        evaluation.get("protected_stages_run") != []
        or evaluation.get("protected_artifacts_written") != []
    ):
        raise RuntimeError("The V5 evaluation reports protected mutations.")
    return paths, {
        "v3_freeze": _manifest_identity(freeze),
        "v3_evaluation_summary": _manifest_identity(granularity),
        "v5_evaluation_manifest": _manifest_identity(evaluation),
        "nested_descriptors_verified": True,
        "absolute_source_manifest_payloads_serialized": False,
    }


def _source_descriptors(
    paths: Mapping[str, Path], *, protected_read_root: Path
) -> dict[str, dict[str, Any]]:
    return {
        key: relative_artifact_descriptor(path, repo_root=protected_read_root)
        for key, path in paths.items()
    }


def _validate_census(tables: FundedSelectionTables, config: Mapping[str, Any]) -> None:
    design = config["design"]
    expected = {
        "monthly_bounds": int(design["expected_monthly_portfolios"]),
        "track_bounds": int(design["expected_policy_tracks"]),
        "monthly_gamma_contrasts": int(design["expected_monthly_gamma_contrasts"]),
        "track_gamma_contrasts": int(design["expected_track_gamma_contrasts"]),
        "support_and_fixed_capital_reconciliation": int(
            design["expected_support_and_fixed_capital_reconciliation_tracks"]
        ),
    }
    for key, expected_rows in expected.items():
        if len(getattr(tables, key)) != expected_rows:
            raise RuntimeError(f"V1 {key} census changed.")
    monthly_grid = tables.monthly_bounds
    for column, values in (
        ("window_id", design["window_ids"]),
        ("period", design["periods"]),
        ("frontier_ruler", design["rulers"]),
        ("frontier_coordinate", design["coordinates"]),
        ("gamma", design["gamma_endpoints"]),
    ):
        if set(monthly_grid[column]) != set(values):
            raise RuntimeError(f"V1 complete grid changed on {column!r}.")
    if (
        not tables.track_bounds["periods"].eq(15).all()
        or not tables.track_gamma_contrasts["periods"].eq(15).all()
    ):
        raise RuntimeError("V1 pooled outputs do not contain all 15 issue months.")
    reconciliation = tables.support_and_fixed_capital_reconciliation
    if not reconciliation["exact_within_locked_tolerance"].all():
        raise RuntimeError("V1 fixed-capital reconciliation failed.")
    expected_support_counts = {
        "continuous_selected_positions": int(design["expected_source_positive_positions"]),
        "rounded_selected_positions": int(design["expected_rounded_positive_positions"]),
        "removed_selected_positions": int(design["expected_removed_positions"]),
        "added_selected_positions": 0,
        "rounding_changed_positions": int(design["expected_changed_positions"]),
    }
    for column, expected_count in expected_support_counts.items():
        if int(reconciliation[column].sum()) != expected_count:
            raise RuntimeError(f"V1 support reconciliation changed on {column!r}.")
    count_lower = pd.to_numeric(
        reconciliation["rounded_minus_continuous_count_selected_fcp_lower"], errors="raise"
    ).to_numpy(dtype=float)
    count_upper = pd.to_numeric(
        reconciliation["rounded_minus_continuous_count_selected_fcp_upper"], errors="raise"
    ).to_numpy(dtype=float)
    if not bool(np.isfinite(count_lower).all() and np.isfinite(count_upper).all()):
        raise RuntimeError("V1 count-selected support contrasts contain nonfinite values.")
    if bool((count_lower > count_upper + float(design["numerical_tolerance"])).any()):
        raise RuntimeError("V1 count-selected support contrast bounds are reversed.")


def _direction_census(frame: pd.DataFrame, column: str) -> dict[str, int]:
    counts = frame[column].value_counts(dropna=False).to_dict()
    return {
        str(key): int(value) for key, value in sorted(counts.items(), key=lambda item: str(item[0]))
    }


def run(
    *,
    config_path: Path,
    protected_read_root: Path,
    repo_root: Path = ROOT,
) -> Path:
    """Execute V1 from one explicit protected source root and clean tagged HEAD."""
    started_at = _utc_now()
    started_counter = time.perf_counter()
    root = repo_root.resolve()
    protected_root = protected_read_root.resolve()
    if not protected_root.is_dir():
        raise NotADirectoryError(protected_root)
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
        raise RuntimeError("V1 Git state changed after the clean-tag gate.")

    source_paths, lineage = _load_verified_sources(config, protected_read_root=protected_root)
    source_start = _source_descriptors(source_paths, protected_read_root=protected_root)
    continuous_parent = pd.read_parquet(source_paths["continuous_parent_allocations"])
    rounded = pd.read_parquet(source_paths["rounded_allocations"])
    if len(rounded) != int(config["design"]["expected_rounded_positive_positions"]):
        raise RuntimeError("V1 rounded-support row census changed.")
    joined = pd.read_parquet(source_paths["joined_funded_allocations"])
    registered = pd.read_parquet(source_paths["granularity_contrasts"])
    design = config["design"]
    tables = build_funded_selection_estimand_audit(
        rounded,
        continuous_parent,
        joined,
        registered,
        periods=tuple(str(value) for value in design["periods"]),
        role=str(design["role"]),
        lot_size_usd=float(design["lot_size_usd"]),
        committed_budget_usd=float(design["committed_budget_usd_per_month"]),
        tolerance=float(design["numerical_tolerance"]),
        source_rounding_tolerance=float(design["source_rounding_tolerance"]),
        expected_source_positive_positions=int(design["expected_source_positive_positions"]),
        expected_rounded_positive_positions=int(design["expected_rounded_positive_positions"]),
        expected_removed_positions=int(design["expected_removed_positions"]),
        expected_changed_positions=int(design["expected_changed_positions"]),
    )
    _validate_census(tables, config)

    source_end = _source_descriptors(source_paths, protected_read_root=protected_root)
    if source_end != source_start:
        raise RuntimeError("A protected V1 source changed during execution.")
    implementation_end = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    if implementation_end != implementation_start:
        raise RuntimeError("V1 implementation changed during execution.")
    final_prewrite_git = git_provenance(root)
    if final_prewrite_git != initial_git:
        raise RuntimeError("V1 Git state changed during computation.")

    output_paths = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    targets = _output_targets(config, output_paths)
    frame_map = {
        "monthly_bounds": tables.monthly_bounds,
        "track_bounds": tables.track_bounds,
        "monthly_gamma_contrasts": tables.monthly_gamma_contrasts,
        "track_gamma_contrasts": tables.track_gamma_contrasts,
        "support_and_fixed_capital_reconciliation": (
            tables.support_and_fixed_capital_reconciliation
        ),
    }
    written = {
        key: atomic_write_parquet(frame, targets[key], index=False)
        for key, frame in frame_map.items()
    }
    artifact_descriptors = {
        key: relative_artifact_descriptor(path, repo_root=root) for key, path in written.items()
    }
    tracks = tables.track_bounds
    gamma = tables.track_gamma_contrasts
    reconciliation = tables.support_and_fixed_capital_reconciliation
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_clean_tagged_calculation_pending_git_artifact_commit_v1",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": protocol_commit,
        "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
        "retrospective_lock": {
            "complete_results_previously_inspected": True,
            "confirmatory": False,
            "preregistered": False,
            "all_96_tracks_and_48_gamma_pairs_retained": True,
        },
        "source_artifacts": source_start,
        "nested_source_lineage_verified": {
            "v3_freeze_to_rounded_support": True,
            "v3_summary_to_freeze_and_granularity_contrasts": True,
            "v5_manifest_to_joined_funded_allocations": True,
            "source_manifests": lineage,
        },
        "estimands": {
            "count_selected": "equal_weight_per_funded_loan_month_position",
            "invested_dollar_selected": "exposure_weight_conditional_on_invested_dollars",
            "fixed_capital_decision": (
                "exposure_weight_over_common_committed_capital_with_cash_retained"
            ),
            "active_granularity_estimand": "fixed_capital_decision",
        },
        "census": {
            "rounded_positive_positions": len(rounded),
            "monthly_policy_rows": len(tables.monthly_bounds),
            "pooled_track_rows": len(tracks),
            "monthly_gamma_contrast_rows": len(tables.monthly_gamma_contrasts),
            "pooled_gamma_contrast_rows": len(gamma),
            "support_and_fixed_capital_reconciliation_rows": len(reconciliation),
            "all_cells_reported_without_selection": True,
        },
        "results": {
            "count_selected_coverage_lower_range": [
                float(tracks["count_selected_coverage_lower"].min()),
                float(tracks["count_selected_coverage_lower"].max()),
            ],
            "count_selected_coverage_upper_range": [
                float(tracks["count_selected_coverage_upper"].min()),
                float(tracks["count_selected_coverage_upper"].max()),
            ],
            "invested_dollar_selected_coverage_lower_range": [
                float(tracks["invested_dollar_selected_coverage_lower"].min()),
                float(tracks["invested_dollar_selected_coverage_lower"].max()),
            ],
            "invested_dollar_selected_coverage_upper_range": [
                float(tracks["invested_dollar_selected_coverage_upper"].min()),
                float(tracks["invested_dollar_selected_coverage_upper"].max()),
            ],
            "fixed_capital_decision_coverage_lower_range": [
                float(tracks["fixed_capital_decision_coverage_lower"].min()),
                float(tracks["fixed_capital_decision_coverage_lower"].max()),
            ],
            "fixed_capital_decision_coverage_upper_range": [
                float(tracks["fixed_capital_decision_coverage_upper"].min()),
                float(tracks["fixed_capital_decision_coverage_upper"].max()),
            ],
            "count_selected_minus_invested_dollar_selected_coverage_lower_range": [
                float(tracks["count_selected_minus_invested_dollar_selected_coverage_lower"].min()),
                float(tracks["count_selected_minus_invested_dollar_selected_coverage_lower"].max()),
            ],
            "count_selected_minus_invested_dollar_selected_coverage_upper_range": [
                float(tracks["count_selected_minus_invested_dollar_selected_coverage_upper"].min()),
                float(tracks["count_selected_minus_invested_dollar_selected_coverage_upper"].max()),
            ],
            "count_selected_minus_fixed_capital_decision_coverage_lower_range": [
                float(tracks["count_selected_minus_fixed_capital_decision_coverage_lower"].min()),
                float(tracks["count_selected_minus_fixed_capital_decision_coverage_lower"].max()),
            ],
            "count_selected_minus_fixed_capital_decision_coverage_upper_range": [
                float(tracks["count_selected_minus_fixed_capital_decision_coverage_upper"].min()),
                float(tracks["count_selected_minus_fixed_capital_decision_coverage_upper"].max()),
            ],
            "count_selected_upper_below_point90_tracks": int(
                tracks["count_selected_coverage_upper"]
                .lt(float(design["descriptive_coverage_reference"]))
                .sum()
            ),
            "count_selected_lower_below_point90_tracks": int(
                tracks["count_selected_coverage_lower"]
                .lt(float(design["descriptive_coverage_reference"]))
                .sum()
            ),
            "gamma_count_selected_fcp_direction_census": _direction_census(
                gamma, "gamma1_minus_gamma0_count_selected_fcp_direction"
            ),
            "gamma_invested_dollar_selected_fcp_direction_census": _direction_census(
                gamma, "gamma1_minus_gamma0_invested_dollar_selected_fcp_direction"
            ),
            "gamma_fixed_capital_decision_fcp_direction_census": _direction_census(
                gamma, "gamma1_minus_gamma0_fixed_capital_decision_fcp_direction"
            ),
            "v3_fixed_capital_reconciliation_maximum_absolute_difference": float(
                max(
                    reconciliation["lower_absolute_difference"].max(),
                    reconciliation["upper_absolute_difference"].max(),
                )
            ),
            "source_positive_positions": int(reconciliation["continuous_selected_positions"].sum()),
            "rounded_positive_positions": int(reconciliation["rounded_selected_positions"].sum()),
            "removed_positions": int(reconciliation["removed_selected_positions"].sum()),
            "added_positions": int(reconciliation["added_selected_positions"].sum()),
            "rounding_changed_positions_at_source_tolerance": int(
                reconciliation["rounding_changed_positions"].sum()
            ),
            "rounded_minus_continuous_count_selected_fcp_direction_census": (
                _direction_census(
                    reconciliation,
                    "rounded_minus_continuous_count_selected_fcp_direction",
                )
            ),
        },
        "interpretation": dict(config["interpretation"]),
        "sharpness": {
            "unresolved_labels_shared_within_every_reported_contrast": True,
            "cellwise_not_joint_across_tracks": True,
            "separately_extremized_intervals_subtracted": False,
        },
        "artifacts": artifact_descriptors,
        "artifact_transport": _validate_artifact_transport(config),
        "implementation": implementation_start,
        "environment": _portable_environment(root),
        "git": initial_git,
        "protected_artifacts_read": list(source_start.values()),
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
        "artifacts": artifact_descriptors,
        "artifact_transport": _validate_artifact_transport(config),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
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
        help="Explicit read-only repository-shaped root containing all registered sources.",
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
