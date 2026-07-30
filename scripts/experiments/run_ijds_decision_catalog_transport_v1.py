"""Run the locked post-inspection IJDS decision-catalog transport V1 diagnostic."""

from __future__ import annotations

import argparse
import json
import re
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.ijds_audit.decision_catalog_transport import (
    METRICS,
    POLICY_KEY,
    DecisionCatalogTransportResult,
    build_decision_catalog_transport,
    spec_from_config,
    validate_spec,
)
from src.utils.isolated_experiment import (
    OutputPaths,
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    prepare_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_isolated_run_dir,
    resolve_repo_input,
    sha256_file,
    write_csv_atomic,
)
from src.utils.pipeline_runtime import atomic_write_json, utc_now_iso

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = Path("configs/experiments/ijds_decision_catalog_transport_2026-07-29_v1.yaml")
PROTOCOL_PATH = Path("docs/research/ijds_decision_catalog_transport_v1_protocol_2026-07-29.md")
PROTOCOL_TAG = "protocol/ijds-decision-catalog-transport-2026-07-29-v1"
RUN_TAG = "ijds-decision-catalog-transport-2026-07-29-v1"
ARTIFACT_TAG = "artifacts/ijds-decision-catalog-transport-2026-07-29-v1"
PROTOCOL_STATUS = "locked_postinspection_decision_catalog_transport_candidate"
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
IMPLEMENTATION_PATHS = (
    PROTOCOL_PATH,
    Path("src/ijds_audit/decision_catalog_transport.py"),
    Path("scripts/experiments/run_ijds_decision_catalog_transport_v1.py"),
)
SOURCE_NAMES = (
    "v1c_protocol_freeze",
    "outcome_free_allocations",
    "v5_verified_manifest",
    "evaluated_portfolios",
    "joined_funded_allocations",
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


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


def _resolve_locked_config_path(config_path: Path, *, repo_root: Path) -> Path:
    resolved = resolve_repo_input(config_path, repo_root=repo_root)
    canonical = (repo_root / DEFAULT_CONFIG_PATH).resolve()
    if resolved != canonical:
        raise ValueError(f"V1 requires the canonical locked config: {canonical}.")
    return resolved


def _safe_output_name(value: Any, *, suffix: str) -> str:
    name = str(value)
    path = Path(name)
    if not name or path.name != name or path.suffix.casefold() != suffix:
        raise ValueError(f"Output filename is not a safe direct-child {suffix} name: {name!r}.")
    return name


def _validate_output_names(config: Mapping[str, Any]) -> None:
    output = config["output"]
    names = [
        _safe_output_name(output["policy_score_bounds"], suffix=".csv"),
        _safe_output_name(output["block_score_bounds"], suffix=".csv"),
        _safe_output_name(output["calibration_thresholds"], suffix=".csv"),
        _safe_output_name(output["target_classification"], suffix=".csv"),
        _safe_output_name(output["summary"], suffix=".json"),
        _safe_output_name(output["execution_receipt"], suffix=".json"),
    ]
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError("Output filenames alias after case folding.")


def _validate_artifact_transport(config: Mapping[str, Any]) -> dict[str, Any]:
    transport = config.get("artifact_transport")
    expected_fields = {
        "artifact_tag",
        "artifact_commit_relationship",
        "exact_tracked_paths",
        "pending_at_runner_exit",
        "dvc_required",
    }
    if not isinstance(transport, dict) or set(transport) != expected_fields:
        raise RuntimeError("Decision-catalog artifact-transport contract changed.")

    output = config.get("output")
    if not isinstance(output, dict):
        raise TypeError("Decision-catalog output contract must be a mapping.")
    if Path(str(output["data_root"])) != ALLOWED_DATA_ROOT or Path(
        str(output["model_root"])
    ) != ALLOWED_MODEL_ROOT:
        raise RuntimeError("Decision-catalog output roots changed.")
    _validate_output_names(config)
    data_prefix = ALLOWED_DATA_ROOT / RUN_TAG
    model_prefix = ALLOWED_MODEL_ROOT / RUN_TAG
    output_keys = (
        "policy_score_bounds",
        "block_score_bounds",
        "calibration_thresholds",
        "target_classification",
        "summary",
        "execution_receipt",
    )
    nominal_targets = _output_targets(
        config,
        OutputPaths(data_dir=data_prefix, model_dir=model_prefix),
    )
    if set(nominal_targets) != set(output_keys):
        raise RuntimeError("Decision-catalog output-key mapping changed.")
    expected_paths = [nominal_targets[key].as_posix() for key in output_keys]
    actual_paths = transport["exact_tracked_paths"]
    if not isinstance(actual_paths, list):
        raise TypeError("Decision-catalog exact tracked paths must be a list.")
    for raw in actual_paths:
        if not isinstance(raw, str):
            raise TypeError("Decision-catalog exact tracked paths must be strings.")
        path = Path(raw)
        if (
            path.is_absolute()
            or path.drive
            or path.root
            or any(part in {"", ".", ".."} for part in path.parts)
            or path.as_posix() != raw
        ):
            raise ValueError(f"Decision-catalog tracked artifact path is unsafe: {raw!r}.")
    if len({raw.casefold() for raw in actual_paths}) != len(actual_paths):
        raise RuntimeError("Decision-catalog tracked artifact paths alias case-insensitively.")
    if (
        transport["artifact_tag"] != ARTIFACT_TAG
        or transport["artifact_commit_relationship"]
        != "single_direct_child_of_protocol_commit"
        or actual_paths != expected_paths
        or transport["pending_at_runner_exit"] is not True
        or transport["dvc_required"] is not False
    ):
        raise RuntimeError("Decision-catalog artifact-transport identity changed.")
    return {
        "artifact_tag": ARTIFACT_TAG,
        "artifact_commit_relationship": "single_direct_child_of_protocol_commit",
        "exact_tracked_paths": expected_paths,
        "pending_at_runner_exit": True,
        "dvc_required": False,
    }


def _validate_descriptor(descriptor: Any, *, label: str) -> None:
    if not isinstance(descriptor, dict) or set(descriptor) != {"path", "bytes", "sha256"}:
        raise ValueError(f"{label} must be an exact path/bytes/sha256 descriptor.")
    if not isinstance(descriptor["path"], str) or not descriptor["path"]:
        raise ValueError(f"{label} path is invalid.")
    if isinstance(descriptor["bytes"], bool) or int(descriptor["bytes"]) < 1:
        raise ValueError(f"{label} byte count is invalid.")
    digest = str(descriptor["sha256"])
    if SHA256_PATTERN.fullmatch(digest) is None:
        raise ValueError(f"{label} SHA-256 is invalid.")


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Decision-catalog transport config must be a mapping.")
    identities = {
        "protocol_status": PROTOCOL_STATUS,
        "protocol_tag": PROTOCOL_TAG,
        "run_tag": RUN_TAG,
        "protocol_path": PROTOCOL_PATH.as_posix(),
    }
    for key, expected_identity in identities.items():
        if payload.get(key) != expected_identity:
            raise ValueError(f"Locked config identity {key!r} changed.")
    sources = payload.get("sources")
    if not isinstance(sources, dict) or set(sources) != set(SOURCE_NAMES):
        raise ValueError("Locked source descriptor set changed.")
    for name in SOURCE_NAMES:
        _validate_descriptor(sources[name], label=f"sources.{name}")

    design = payload.get("design")
    if not isinstance(design, dict):
        raise ValueError("Locked design section is missing.")
    spec = spec_from_config(design)
    validate_spec(spec)
    if tuple(str(value) for value in design["metrics"]) != METRICS:
        raise ValueError("Locked metric order changed.")
    expected_censuses = {
        "expected_calibration_blocks": len(spec.calibration_periods),
        "expected_target_blocks": len(spec.target_periods),
        "expected_blocks": len(spec.calibration_periods) + len(spec.target_periods),
        "expected_policy_metric_rows": spec.expected_policy_rows * len(METRICS),
        "expected_block_metric_rows": (len(spec.calibration_periods) + len(spec.target_periods))
        * len(METRICS),
        "expected_threshold_rows": len(METRICS),
        "expected_target_metric_rows": len(spec.target_periods) * len(METRICS),
    }
    for key, expected_census in expected_censuses.items():
        if int(design[key]) != expected_census:
            raise ValueError(f"Locked census {key!r} is incoherent.")
    if design.get("rank_rule") != "ceil((n_calibration_blocks + 1) * (1 - alpha))":
        raise ValueError("Locked calibration rank rule changed.")
    if design.get("shared_unresolved_completion") is not True:
        raise ValueError("V1 requires one shared unresolved completion.")

    disclosure = payload.get("post_inspection_disclosure")
    required_disclosure = {
        "outcomes_and_exploratory_scores_already_inspected": True,
        "preregistered": False,
        "confirmatory": False,
        "expected_results_must_not_gate_execution": True,
    }
    if not isinstance(disclosure, dict) or any(
        disclosure.get(key) is not expected_value
        for key, expected_value in required_disclosure.items()
    ):
        raise ValueError("Post-inspection disclosure was weakened.")
    if disclosure.get("joint_three_metric_ordering_probability_reported") is not False:
        raise ValueError("V1 must not report a joint three-metric ordering probability.")
    stop_rules = payload.get("stop_rules")
    if (
        not isinstance(stop_rules, dict)
        or not stop_rules
        or not all(value is True for value in stop_rules.values())
    ):
        raise ValueError("Every declared V1 stop rule must remain enabled.")
    claim = payload.get("claim_boundary")
    if not isinstance(claim, dict) or claim.get("active_claim") is not False:
        raise ValueError("V1 must remain a non-active diagnostic candidate.")
    if claim.get("protected_stages_run") != []:
        raise ValueError("V1 cannot authorize a protected stage.")
    _validate_output_names(payload)
    _validate_artifact_transport(payload)
    return payload


def _preflight_output_paths(config: dict[str, Any], *, repo_root: Path) -> None:
    data_dir = resolve_isolated_run_dir(
        repo_root=repo_root,
        configured_root=str(config["output"]["data_root"]),
        allowed_relative_root=ALLOWED_DATA_ROOT,
        run_tag=RUN_TAG,
    )
    model_dir = resolve_isolated_run_dir(
        repo_root=repo_root,
        configured_root=str(config["output"]["model_root"]),
        allowed_relative_root=ALLOWED_MODEL_ROOT,
        run_tag=RUN_TAG,
    )
    existing = [str(path) for path in (data_dir, model_dir) if path.exists()]
    if existing:
        raise FileExistsError(f"V1 output path already exists: {existing}.")


def _protected_root(path: Path, *, repo_root: Path) -> Path:
    protected = path.resolve()
    if not protected.is_dir():
        raise FileNotFoundError(protected)
    if protected == repo_root.resolve():
        raise ValueError(
            "--protected-read-root must be separate from the clean execution checkout."
        )
    return protected


def _protected_read_disclosure(_protected_root: Path) -> dict[str, bool]:
    """Describe isolated reads without serializing a machine-specific absolute path."""
    return {
        "protected_read_root_supplied": True,
        "protected_read_root_separate_from_execution_checkout": True,
        "absolute_materialization_paths_recorded": False,
    }


def _verified_path(descriptor: Mapping[str, Any], *, protected_root: Path) -> Path:
    path = resolve_repo_input(str(descriptor["path"]), repo_root=protected_root)
    if path.stat().st_size != int(descriptor["bytes"]):
        raise RuntimeError(f"Source byte count changed: {descriptor['path']}.")
    if sha256_file(path) != str(descriptor["sha256"]):
        raise RuntimeError(f"Source sha256 changed: {descriptor['path']}.")
    return path


def _descriptor_dict(value: Any, *, label: str) -> dict[str, Any]:
    _validate_descriptor(value, label=label)
    return {
        "path": str(value["path"]),
        "bytes": int(value["bytes"]),
        "sha256": str(value["sha256"]),
    }


def _require_same_descriptor(left: Any, right: Any, *, label: str) -> None:
    if _descriptor_dict(left, label=f"{label}.left") != _descriptor_dict(
        right, label=f"{label}.right"
    ):
        raise RuntimeError(f"Nested descriptor mismatch for {label}.")


def _load_verified_sources(
    config: Mapping[str, Any], *, protected_root: Path
) -> tuple[dict[str, Path], dict[str, Any], dict[str, Any]]:
    sources = config["sources"]
    paths = {
        name: _verified_path(sources[name], protected_root=protected_root) for name in SOURCE_NAMES
    }
    freeze = json.loads(paths["v1c_protocol_freeze"].read_text(encoding="utf-8"))
    manifest = json.loads(paths["v5_verified_manifest"].read_text(encoding="utf-8"))
    if not isinstance(freeze, dict) or not isinstance(manifest, dict):
        raise RuntimeError("Pinned JSON authorities must contain objects.")
    _require_same_descriptor(
        freeze["outcome_free_artifacts"]["allocations"],
        sources["outcome_free_allocations"],
        label="V1c freeze allocations",
    )
    _require_same_descriptor(
        manifest["source_frontier_freeze"],
        sources["v1c_protocol_freeze"],
        label="V5 source freeze",
    )
    _require_same_descriptor(
        manifest["source_artifacts"]["allocations"],
        sources["outcome_free_allocations"],
        label="V5 source allocations",
    )
    _require_same_descriptor(
        manifest["evaluation_artifacts"]["evaluated_portfolios"],
        sources["evaluated_portfolios"],
        label="V5 evaluated portfolios",
    )
    _require_same_descriptor(
        manifest["evaluation_artifacts"]["joined_funded_allocations"],
        sources["joined_funded_allocations"],
        label="V5 joined allocations",
    )
    if freeze.get("outcome_columns_passed_to_frontier") != []:
        raise RuntimeError("V1c frontier freeze is not outcome-free.")
    if manifest.get("outcome_columns_joined_after_freeze") != [
        "snapshot_default",
        "snapshot_resolution",
    ]:
        raise RuntimeError("V5 endpoint-join declaration changed.")
    if any(
        authority.get("protected_stages_run") != []
        or authority.get("protected_artifacts_written") != []
        for authority in (freeze, manifest)
    ):
        raise RuntimeError("Pinned source authority reports a protected-stage mutation.")
    return paths, freeze, manifest


def _validate_evaluated_portfolio_census(
    evaluated: pd.DataFrame,
    outcome_free: pd.DataFrame,
    *,
    expected_rows: int,
) -> dict[str, Any]:
    required = {*POLICY_KEY, "candidate_id", "total_allocated", "full_budget"}
    missing = sorted(required.difference(evaluated.columns))
    if missing:
        raise ValueError(f"Evaluated portfolios omit columns: {missing}.")
    if len(evaluated) != expected_rows or bool(evaluated[list(POLICY_KEY)].duplicated().any()):
        raise RuntimeError("Evaluated portfolio census or policy uniqueness changed.")
    frozen = outcome_free[[*POLICY_KEY, "candidate_id"]].drop_duplicates()
    joined = frozen.merge(
        evaluated[[*POLICY_KEY, "candidate_id"]],
        on=[*POLICY_KEY, "candidate_id"],
        how="outer",
        indicator=True,
        validate="one_to_one",
    )
    if len(frozen) != expected_rows or not bool(joined["_merge"].eq("both").all()):
        raise RuntimeError("Evaluated portfolios do not match the frozen policy catalog.")
    if not bool(evaluated["full_budget"].eq(True).all()):
        raise RuntimeError("V5 evaluated portfolios include a non-full-budget policy.")
    return {
        "rows": int(len(evaluated)),
        "catalog_identity_exact": True,
        "full_budget_rows": int(evaluated["full_budget"].eq(True).sum()),
    }


def _output_targets(config: Mapping[str, Any], paths: OutputPaths) -> dict[str, Path]:
    output = config["output"]
    return {
        "policy_score_bounds": paths.data_dir / str(output["policy_score_bounds"]),
        "block_score_bounds": paths.data_dir / str(output["block_score_bounds"]),
        "calibration_thresholds": paths.data_dir / str(output["calibration_thresholds"]),
        "target_classification": paths.data_dir / str(output["target_classification"]),
        "summary": paths.model_dir / str(output["summary"]),
        "execution_receipt": paths.model_dir / str(output["execution_receipt"]),
    }


def _require_output_census(
    result: DecisionCatalogTransportResult, *, design: Mapping[str, Any]
) -> None:
    observed = {
        "expected_policy_metric_rows": len(result.policy_score_bounds),
        "expected_block_metric_rows": len(result.block_score_bounds),
        "expected_threshold_rows": len(result.calibration_thresholds),
        "expected_target_metric_rows": len(result.target_classification),
    }
    for key, rows in observed.items():
        if rows != int(design[key]):
            raise RuntimeError(f"Output census {key!r} changed.")


def run(
    *,
    config_path: Path,
    protected_read_root: Path,
    repo_root: Path = ROOT,
) -> Path:
    """Execute V1 from clean tagged code while reading a separate protected source tree."""
    started_at = utc_now_iso()
    started_counter = time.perf_counter()
    root = repo_root.resolve()
    resolved_config = _resolve_locked_config_path(config_path, repo_root=root)
    config = _load_config(resolved_config)
    _preflight_output_paths(config, repo_root=root)
    protocol_commit = require_clean_tagged_head(root, PROTOCOL_TAG)
    protocol_path = resolve_repo_input(PROTOCOL_PATH, repo_root=root)
    protected = _protected_root(protected_read_root, repo_root=root)
    implementation_start = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    initial_git = git_provenance(root)

    source_paths, freeze, manifest = _load_verified_sources(config, protected_root=protected)
    outcome_free = pd.read_parquet(source_paths["outcome_free_allocations"])
    evaluated = pd.read_parquet(source_paths["evaluated_portfolios"])
    joined = pd.read_parquet(source_paths["joined_funded_allocations"])
    design = config["design"]
    portfolio_census = _validate_evaluated_portfolio_census(
        evaluated,
        outcome_free,
        expected_rows=int(design["expected_policy_rows"]),
    )
    if int(freeze["schemas"]["allocations"]["rows"]) != len(outcome_free):
        raise RuntimeError("V1c freeze allocation schema census changed.")
    if int(manifest["schemas"]["evaluated_portfolios"]["rows"]) != len(evaluated):
        raise RuntimeError("V5 evaluated-portfolio schema census changed.")
    if int(manifest["schemas"]["joined_funded_allocations"]["rows"]) != len(joined):
        raise RuntimeError("V5 joined-allocation schema census changed.")
    result = build_decision_catalog_transport(
        outcome_free,
        joined,
        spec=spec_from_config(design),
    )
    _require_output_census(result, design=design)

    implementation_end = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    if implementation_end != implementation_start:
        raise RuntimeError("V1 implementation changed during execution.")
    repeated_paths, repeated_freeze, repeated_manifest = _load_verified_sources(
        config, protected_root=protected
    )
    if repeated_paths != source_paths or repeated_freeze != freeze or repeated_manifest != manifest:
        raise RuntimeError("Protected source authority changed during execution.")
    if git_provenance(root) != initial_git:
        raise RuntimeError("Clean tagged execution checkout changed before output materialization.")

    paths = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    targets = _output_targets(config, paths)
    table_paths = {
        "policy_score_bounds": write_csv_atomic(
            result.policy_score_bounds, targets["policy_score_bounds"]
        ),
        "block_score_bounds": write_csv_atomic(
            result.block_score_bounds, targets["block_score_bounds"]
        ),
        "calibration_thresholds": write_csv_atomic(
            result.calibration_thresholds, targets["calibration_thresholds"]
        ),
        "target_classification": write_csv_atomic(
            result.target_classification, targets["target_classification"]
        ),
    }
    source_descriptors = {
        name: relative_artifact_descriptor(path, repo_root=protected)
        for name, path in source_paths.items()
    }
    artifact_descriptors = {
        name: relative_artifact_descriptor(path, repo_root=root)
        for name, path in table_paths.items()
    }
    summary = {
        "schema_version": str(config["schema_version"]),
        **result.summary,
        "status": "complete_clean_tagged_calculation_pending_git_artifact_commit_v1",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": protocol_commit,
        "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
        "source_artifacts": source_descriptors,
        "nested_source_reconciliation": {
            "v1c_freeze_to_outcome_free_allocations": True,
            "v5_manifest_to_v1c_freeze_and_allocations": True,
            "v5_manifest_to_evaluated_and_joined_allocations": True,
            "outcome_free_to_endpoint_join_decisions": True,
        },
        "evaluated_portfolio_census": portfolio_census,
        "post_inspection_disclosure": dict(config["post_inspection_disclosure"]),
        "stop_rules": dict(config["stop_rules"]),
        "schemas": {
            "policy_score_bounds": dataframe_schema(result.policy_score_bounds),
            "block_score_bounds": dataframe_schema(result.block_score_bounds),
            "calibration_thresholds": dataframe_schema(result.calibration_thresholds),
            "target_classification": dataframe_schema(result.target_classification),
        },
        "artifacts": artifact_descriptors,
        "artifact_transport": _validate_artifact_transport(config),
        "implementation_provenance": implementation_start,
        "environment": _portable_environment(root),
        "initial_git": initial_git,
        **_protected_read_disclosure(protected),
        "protected_artifacts_read": list(source_descriptors.values()),
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
        "completed_at_utc": utc_now_iso(),
        "runtime_seconds": float(time.perf_counter() - started_counter),
        "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
        "implementation_provenance": implementation_start,
        "sources": source_descriptors,
        "artifacts": artifact_descriptors,
        "artifact_transport": _validate_artifact_transport(config),
        "summary": relative_artifact_descriptor(summary_path, repo_root=root),
        "initial_git": initial_git,
        "final_git": git_provenance(root),
        "environment": _portable_environment(root),
        **_protected_read_disclosure(protected),
        "protected_stages_run": [],
        "protected_artifacts_read": list(source_descriptors.values()),
        "protected_artifacts_written": [],
    }
    atomic_write_json(targets["execution_receipt"], receipt)
    return summary_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--protected-read-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    print(
        run(
            config_path=args.config,
            protected_read_root=args.protected_read_root,
            repo_root=args.repo_root,
        )
    )


if __name__ == "__main__":
    main()
