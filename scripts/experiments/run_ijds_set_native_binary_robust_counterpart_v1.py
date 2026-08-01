"""Run the hash-gated two-phase binary-set-native robust counterpart V1."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ijds_audit.config import load_v4_config  # noqa: E402
from src.ijds_audit.evaluation import evaluate_frozen_portfolios  # noqa: E402
from src.ijds_audit.protocol import (  # noqa: E402
    configured_archive_outcomes,
    load_outcome_universe,
    load_recipes,
)
from src.ijds_challengers.archive import (  # noqa: E402
    load_outcome_free_decision_base,
    verified_parent_artifacts,
)
from src.ijds_challengers.set_native_binary_robust import (  # noqa: E402
    SetNativeCell,
    build_robust_minus_v1d_contrasts,
    cell_from_shard_frame,
    cell_to_shard_frame,
    iter_set_native_cells,
    load_set_native_config,
    shard_relative_path,
    validate_phase_a_metadata,
)
from src.utils.isolated_experiment import (  # noqa: E402
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    package_version,
    relative_artifact_descriptor,
    resolve_isolated_run_dir,
    resolve_repo_input,
    sha256_file,
)
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    utc_now_iso,
)

DEFAULT_PHASE_A_CONFIG = (
    ROOT / "configs/experiments/ijds_set_native_binary_robust_counterpart_2026-07-31_v1.yaml"
)
DEFAULT_PHASE_B_CONFIG = (
    ROOT / "configs/experiments/"
    "ijds_set_native_binary_robust_counterpart_2026-07-31_v1_phase_b_blocked.yaml"
)
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
PHASE_A_STATUS = "outcome_free_set_native_binary_robust_counterpart_complete"
PHASE_B_STATUS = "set_native_binary_robust_counterpart_evaluation_complete"
IMPLEMENTATION_PATHS = (
    Path("configs/experiments/ijds_set_native_binary_robust_counterpart_2026-07-31_v1.yaml"),
    Path(
        "configs/experiments/"
        "ijds_set_native_binary_robust_counterpart_2026-07-31_v1_phase_b_blocked.yaml"
    ),
    Path("docs/research/ijds_set_native_binary_robust_counterpart_v1_protocol_2026-07-31.md"),
    Path("scripts/experiments/run_ijds_set_native_binary_robust_counterpart_v1.py"),
    Path("src/ijds_challengers/set_native_binary_robust.py"),
    Path("src/ijds_challengers/archive.py"),
    Path("src/ijds_challengers/frontier.py"),
    Path("src/ijds_challengers/normalized_frontier.py"),
    Path("src/ijds_audit/config.py"),
    Path("src/ijds_audit/evaluation.py"),
    Path("src/ijds_audit/policy_support.py"),
    Path("src/ijds_audit/portfolio.py"),
    Path("src/ijds_audit/protocol.py"),
    Path("src/evaluation/policy_contrast_bounds.py"),
    Path("src/evaluation/standardized_credit_payoff.py"),
    Path("src/models/binary_conformal_guardrail.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("tests/test_ijds_set_native_binary_robust_counterpart_v1.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("outcome-free", "evaluate"), required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument(
        "--runtime-root",
        type=Path,
        help="External base for resumable Phase-A checkpoints; never an official artifact.",
    )
    return parser.parse_args(argv)


def _resolve_annotated_tag(root: Path, tag: str) -> tuple[str, str]:
    reference = f"refs/tags/{tag}"
    valid = subprocess.run(
        ["git", "check-ref-format", reference],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if valid.returncode != 0 or str(tag).startswith(("-", "refs/")):
        raise RuntimeError(f"Invalid explicit tag name: {tag!r}.")
    object_id = subprocess.run(
        ["git", "rev-parse", "--verify", "--end-of-options", reference],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    object_type = subprocess.run(
        ["git", "cat-file", "-t", object_id],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    commit = subprocess.run(
        ["git", "rev-parse", "--verify", "--end-of-options", f"{reference}^{{commit}}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(object_id) != 40 or object_type != "tag" or len(commit) != 40:
        raise RuntimeError(f"An annotated tag is required: {tag!r}.")
    return object_id, commit


def _require_clean_annotated_tagged_head(root: Path, tag: str) -> dict[str, str]:
    state = git_provenance(root)
    if state.get("dirty") is not False:
        raise RuntimeError("Experiment execution requires a clean predeclared worktree.")
    commit = state.get("commit")
    object_id, tagged_commit = _resolve_annotated_tag(root, tag)
    if not isinstance(commit, str) or commit != tagged_commit:
        raise RuntimeError(f"Annotated protocol tag {tag!r} must resolve exactly to HEAD.")
    return {"tag": str(tag), "tag_object": object_id, "commit": commit}


def _require_direct_parent(*, child: str, parent: str, root: Path, label: str) -> None:
    line = (
        subprocess.run(
            ["git", "rev-list", "--parents", "-n", "1", child],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
        .split()
    )
    if line != [child, parent]:
        raise RuntimeError(f"{label} is not the required single-parent direct child.")


def _require_ancestor(*, descendant: str, ancestor: str, root: Path, label: str) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{label} is not an ancestor of the tagged experiment commit.")


def _implementation(config_path: Path, root: Path) -> dict[str, Any]:
    return implementation_provenance(
        config_path=config_path,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )


def _environment(root: Path) -> dict[str, Any]:
    environment = environment_provenance(root)
    environment["packages"]["ortools"] = package_version("ortools")
    environment["packages"]["PyYAML"] = package_version("PyYAML")
    environment["packages"]["loguru"] = package_version("loguru")
    return environment


def _authority(config_path: Path, root: Path) -> dict[str, Any]:
    return {
        "implementation": _implementation(config_path, root),
        "environment": _environment(root),
        "git": git_provenance(root),
    }


def _require_committed_implementation(
    provenance: Mapping[str, Any], *, commit: str, root: Path
) -> None:
    source_files = provenance.get("source_files")
    if not isinstance(source_files, dict) or provenance.get("hash_algorithm") != "sha256":
        raise RuntimeError("Implementation provenance schema is invalid.")
    for relative, descriptor in source_files.items():
        blob = subprocess.run(
            ["git", "show", f"{commit}:{relative}"],
            cwd=root,
            check=False,
            capture_output=True,
        )
        observed = {
            "path": relative,
            "bytes": len(blob.stdout),
            "sha256": hashlib.sha256(blob.stdout).hexdigest(),
        }
        if blob.returncode != 0 or observed != descriptor:
            raise RuntimeError(f"Git blob disagrees with implementation authority: {relative}.")


def _candidate_identity(frame: pd.DataFrame) -> dict[str, Any]:
    identity = frame.loc[:, ["role", "period", "id"]].astype("string")
    if bool(identity.isna().any(axis=None)) or bool(identity["id"].duplicated().any()):
        raise RuntimeError("Candidate identity contains missing or duplicate values.")
    identity = identity.sort_values(["role", "period", "id"], kind="mergesort")

    def digest(rows: pd.DataFrame) -> str:
        hasher = hashlib.sha256()
        for row in rows.itertuples(index=False, name=None):
            encoded = json.dumps(list(row), separators=(",", ":")).encode("utf-8")
            hasher.update(len(encoded).to_bytes(8, byteorder="big", signed=False))
            hasher.update(encoded)
        return hasher.hexdigest()

    groups = [
        {
            "role": str(role),
            "period": str(period),
            "rows": int(len(group)),
            "sha256": digest(group),
        }
        for (role, period), group in identity.groupby(["role", "period"], observed=True, sort=True)
    ]
    return {
        "rows": int(len(identity)),
        "groups": groups,
        "sha256": digest(identity),
        "canonicalization": ("utf8_length_prefixed_json_role_period_id_sorted_mergesort_sha256"),
    }


def _run_dirs(config: Mapping[str, Any], root: Path) -> tuple[Path, Path]:
    output = config["output"]
    run_tag = str(config["run_tag"])
    data_dir = resolve_isolated_run_dir(
        repo_root=root,
        configured_root=str(output["data_root"]),
        allowed_relative_root=ALLOWED_DATA_ROOT,
        run_tag=run_tag,
    )
    model_dir = resolve_isolated_run_dir(
        repo_root=root,
        configured_root=str(output["model_root"]),
        allowed_relative_root=ALLOWED_MODEL_ROOT,
        run_tag=run_tag,
    )
    return data_dir, model_dir


def _checkpoint_root(
    config: Mapping[str, Any], root: Path, *, runtime_root: Path | None = None
) -> Path:
    if config["output"]["runtime_checkpoint_root"] != (
        "localappdata_crpto_runtime_or_explicit_cli"
    ):
        raise ValueError("Runtime checkpoint-root semantics changed.")
    if runtime_root is None:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError("LOCALAPPDATA is unavailable; pass an explicit --runtime-root.")
        configured = (Path(local_app_data) / "CRPTO/runtime").resolve()
    else:
        configured = runtime_root.resolve()
    candidate = (configured / str(config["run_tag"])).resolve()
    relative = candidate.relative_to(configured)
    if len(relative.parts) != 1 or relative.name != str(config["run_tag"]):
        raise ValueError("Runtime checkpoint run directory is not one safe direct child.")
    repository_roots = tuple(
        candidate_root.resolve()
        for candidate_root in (root, *root.parents)
        if (candidate_root / ".git").exists()
    )
    forbidden_roots = (
        *repository_roots,
        (root / "data/raw").resolve(),
        (root / ALLOWED_DATA_ROOT).resolve(),
        (root / ALLOWED_MODEL_ROOT).resolve(),
    )
    if any(candidate.is_relative_to(forbidden) for forbidden in forbidden_roots):
        raise ValueError("Runtime checkpoints must remain outside repository and protected roots.")
    return candidate


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"JSON authority must be an object: {path}.")
    return payload


def _stable_intent(
    *,
    config: Mapping[str, Any],
    protocol: Mapping[str, str],
    authority: Mapping[str, Any],
    parent_freeze: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": str(config["schema_version"]),
        "status": "phase_a_atomic_shards_in_progress",
        "run_tag": str(config["run_tag"]),
        "protocol": dict(protocol),
        "implementation": authority["implementation"],
        "environment": authority["environment"],
        "git": authority["git"],
        "parent": {
            "run_tag": parent_freeze["run_tag"],
            "protocol_commit": parent_freeze["protocol_commit"],
        },
        "expected_cells": int(config["expected_census"]["phase_a_cells"]),
        "outcome_columns_passed": [],
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }


def _prepare_or_resume(
    *,
    config: Mapping[str, Any],
    checkpoint_root: Path,
    expected_intent: Mapping[str, Any],
) -> Path:
    output = config["output"]
    intent_path = checkpoint_root / str(output["phase_a_intent"])
    if checkpoint_root.exists():
        if not checkpoint_root.is_dir() or not intent_path.is_file():
            raise FileExistsError("Occupied Phase-A path lacks its exact resumable intent.")
        if _json(intent_path) != dict(expected_intent):
            raise RuntimeError("Existing Phase-A intent differs from current tagged authority.")
        return intent_path
    checkpoint_root.mkdir(parents=True, exist_ok=False)
    return atomic_write_json(intent_path, dict(expected_intent))


def _load_existing_shards(shard_root: Path) -> dict[tuple[str, str, str, str, float], Path]:
    found: dict[tuple[str, str, str, str, float], Path] = {}
    if not shard_root.exists():
        return found
    for path in sorted(shard_root.rglob("*.parquet")):
        cell = cell_from_shard_frame(pd.read_parquet(path))
        expected = (shard_root / shard_relative_path(cell)).resolve()
        if path.resolve() != expected:
            raise RuntimeError(f"Atomic shard escaped its canonical identity path: {path}.")
        if cell.identity in found:
            raise RuntimeError(f"Duplicate atomic shard identity: {cell.identity}.")
        found[cell.identity] = path
    return found


def _write_new_cell(cell: SetNativeCell, *, shard_root: Path) -> Path:
    path = shard_root / shard_relative_path(cell)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite an atomic cell shard: {path}.")
    written = atomic_write_parquet(cell_to_shard_frame(cell), path)
    verified = cell_from_shard_frame(pd.read_parquet(written))
    if verified.identity != cell.identity:
        raise RuntimeError("Atomic cell identity changed across persistence.")
    return written


def _terminal_tables(
    paths: Sequence[Path],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    records: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    allocations: list[pd.DataFrame] = []
    taxonomy_by_menu: dict[tuple[str, str, str], dict[str, Any]] = {}
    schemas: dict[str, Any] = {}
    for path in sorted(paths):
        frame = pd.read_parquet(path)
        cell = cell_from_shard_frame(frame)
        records.append(cell.record)
        audits.append(cell.audit)
        allocations.append(cell.allocations)
        key = (
            str(cell.taxonomy["window_id"]),
            str(cell.taxonomy["role"]),
            str(cell.taxonomy["period"]),
        )
        prior = taxonomy_by_menu.setdefault(key, cell.taxonomy)
        if prior != cell.taxonomy:
            raise RuntimeError(f"Taxonomy metadata differs within menu {key}.")
        schema = dataframe_schema(frame)
        schema_key = hashlib.sha256(json.dumps(schema, sort_keys=True).encode("utf-8")).hexdigest()
        schemas.setdefault(schema_key, schema)
    return (
        pd.DataFrame(records),
        pd.concat(allocations, ignore_index=True),
        pd.DataFrame(audits),
        pd.DataFrame(taxonomy_by_menu.values()),
        {"distinct_schemas": len(schemas), "schemas": schemas},
    )


def run_phase_a(
    *,
    config_path: Path,
    repo_root: Path = ROOT,
    runtime_root: Path | None = None,
) -> Path:
    """Materialize and freeze all 1,248 outcome-free atomic cell shards."""
    started = time.perf_counter()
    started_at = utc_now_iso()
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_set_native_config(resolved_config)
    protocol = _require_clean_annotated_tagged_head(root, str(config["protocol_tag"]))
    parent_tag = _resolve_annotated_tag(root, str(config["parent"]["protocol_tag"]))
    if parent_tag[1] != str(config["parent"]["protocol_commit"]):
        raise RuntimeError("Frozen V4 parent tag does not match its pinned commit.")
    _require_ancestor(
        descendant=protocol["commit"],
        ancestor=parent_tag[1],
        root=root,
        label="Frozen V4 parent",
    )
    authority = _authority(resolved_config, root)
    _require_committed_implementation(
        authority["implementation"], commit=protocol["commit"], root=root
    )
    parent_paths, parent_freeze = verified_parent_artifacts(config, repo_root=root)
    parent_config_path = resolve_repo_input(str(config["parent"]["config"]), repo_root=root)
    parent_provenance = parent_freeze.get("implementation_provenance")
    if not isinstance(parent_provenance, dict):
        raise RuntimeError("Frozen V4 parent lacks implementation provenance.")
    parent_descriptor = relative_artifact_descriptor(parent_config_path, repo_root=root)
    if parent_provenance.get("source_files", {}).get(str(config["parent"]["config"])) != (
        parent_descriptor
    ):
        raise RuntimeError("Current V4 parent config differs from its historical freeze.")
    _require_committed_implementation(
        parent_provenance, commit=str(config["parent"]["protocol_commit"]), root=root
    )
    data_dir, model_dir = _run_dirs(config, root)
    if data_dir.exists() or model_dir.exists():
        raise FileExistsError(
            "Official Phase-A output paths are occupied; no overwrite is allowed."
        )
    checkpoint_root = _checkpoint_root(config, root, runtime_root=runtime_root)
    intent = _stable_intent(
        config=config,
        protocol=protocol,
        authority=authority,
        parent_freeze=parent_freeze,
    )
    _prepare_or_resume(
        config=config,
        checkpoint_root=checkpoint_root,
        expected_intent=intent,
    )
    shard_root = checkpoint_root / str(config["output"]["shard_directory"])
    existing = _load_existing_shards(shard_root)
    initial_existing_count = len(existing)
    logger.info("Resuming Phase A with {}/1248 verified atomic shards", len(existing))

    # load_v4_config recursively resolves ``extends`` via load_config_payload;
    # the visible V4 YAML inherits the USD 1m budget and payoff contract.
    parent_config = load_v4_config(parent_config_path)
    if float(parent_config["policy"]["budget"]) != 1_000_000.0:
        raise RuntimeError("Inherited V4 policy budget is not the locked USD 1 million.")
    raw_path = resolve_repo_input(str(config["source_ingest"]["raw_path"]), repo_root=root)
    base = load_outcome_free_decision_base(
        scores_path=parent_paths["scores"],
        raw_path=raw_path,
        config=config,
    )
    candidate_identity = _candidate_identity(
        base.assign(
            role=base["design_split"].astype("string"),
            period=pd.to_datetime(base["issue_d"]).dt.to_period("M").astype("string"),
        )
    )
    recipes = load_recipes(parent_paths["recipes"])
    for cell in iter_set_native_cells(
        base,
        recipes,
        config=config,
        parent_config=parent_config,
        skip_identities=set(existing),
    ):
        path = _write_new_cell(cell, shard_root=shard_root)
        existing[cell.identity] = path
        logger.info("Atomic Phase-A shard {}/1248: {}", len(existing), cell.identity)

    if len(existing) != int(config["expected_census"]["phase_a_cells"]):
        raise RuntimeError(f"Phase A stopped with {len(existing)} of 1248 atomic shards.")
    records, allocations, audits, taxonomy, shard_schemas = _terminal_tables(
        tuple(existing.values())
    )
    validate_phase_a_metadata(records, audits, taxonomy, config=config)
    repeated_parent_paths, repeated_parent_freeze = verified_parent_artifacts(
        config, repo_root=root
    )
    if repeated_parent_paths != parent_paths or repeated_parent_freeze != parent_freeze:
        raise RuntimeError("Parent authority changed during Phase A.")
    if sha256_file(raw_path) != str(config["source_ingest"]["raw_sha256"]):
        raise RuntimeError("Raw decision archive changed during Phase A.")
    if _authority(resolved_config, root) != authority:
        raise RuntimeError("Implementation, environment, or Git authority changed during Phase A.")

    summary = {
        "schema_version": str(config["schema_version"]),
        "status": PHASE_A_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol": protocol,
        "counts": {
            "cells": int(len(records)),
            "primary_cells": int(records["role"].eq("primary_oot").sum()),
            "funded_rows": int(len(allocations)),
            "taxonomy_rows": int(len(taxonomy)),
            "solver_audit_rows": int(len(audits)),
        },
        "set_counts": {
            column: int(taxonomy[column].sum())
            for column in (
                "n_empty",
                "n_singleton_zero",
                "n_singleton_one",
                "n_two_label",
                "n_risk_zero",
                "n_risk_one",
            )
        },
        "audit_maxima": {
            column: float(audits[column].abs().max())
            for column in (
                "deterministic_exposure_distance",
                "deterministic_objective_difference",
                "deterministic_weighted_score_difference",
                "reversal_exposure_distance",
                "reversal_objective_difference",
                "reversal_weighted_score_difference",
                "independent_objective_rate_difference",
                "independent_weighted_score_difference",
            )
        },
        "selection": {"ruler": None, "coordinate": None, "window": None, "policy": None},
        "outcome_columns_passed": [],
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    output = config["output"]
    data_dir.mkdir(parents=True, exist_ok=False)
    model_dir.mkdir(parents=True, exist_ok=False)
    frontier_dir = data_dir / "frontier"
    official_paths = {
        "solve_records": atomic_write_parquet(records, frontier_dir / str(output["solve_records"])),
        "allocations": atomic_write_parquet(allocations, frontier_dir / str(output["allocations"])),
        "set_taxonomy": atomic_write_parquet(taxonomy, frontier_dir / str(output["set_taxonomy"])),
        "solver_audit": atomic_write_parquet(audits, frontier_dir / str(output["solver_audit"])),
    }
    official_descriptors = {
        key: relative_artifact_descriptor(path, repo_root=root)
        for key, path in official_paths.items()
    }
    summary_path = atomic_write_json(model_dir / str(output["outcome_free_summary"]), summary)
    receipt_path = atomic_write_json(
        model_dir / str(output["outcome_free_receipt"]),
        {
            "schema_version": str(config["schema_version"]),
            "status": PHASE_A_STATUS,
            "run_tag": str(config["run_tag"]),
            "protocol": protocol,
            "started_at_utc": started_at,
            "completed_at_utc": utc_now_iso(),
            "elapsed_seconds": float(time.perf_counter() - started),
            "resumed_verified_shards": int(initial_existing_count),
            "outcome_columns_passed": [],
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    phase_a_manifest_path = atomic_write_json(
        model_dir / str(output["phase_a_manifest"]),
        {
            "schema_version": str(config["schema_version"]),
            "status": PHASE_A_STATUS,
            "run_tag": str(config["run_tag"]),
            "official_artifacts": official_descriptors,
            "official_schemas": {
                "solve_records": dataframe_schema(records),
                "allocations": dataframe_schema(allocations),
                "set_taxonomy": dataframe_schema(taxonomy),
                "solver_audit": dataframe_schema(audits),
            },
            "runtime_checkpoint_contract": {
                "cells": int(len(existing)),
                "cell_identity": ["window_id", "role", "period", "ruler", "coordinate"],
                "schema_contract": shard_schemas,
                "git_artifact": False,
                "phase_b_authority": False,
                "external_runtime_root": str(config["output"]["runtime_checkpoint_root"]),
                "absolute_runtime_path_serialized": False,
            },
        },
    )
    freeze = {
        "schema_version": str(config["schema_version"]),
        "status": PHASE_A_STATUS,
        "artifact_status": "pending_git_artifact_commit_and_annotated_tag",
        "run_tag": str(config["run_tag"]),
        "protocol": protocol,
        "parent": {
            "run_tag": str(config["parent"]["run_tag"]),
            "freeze": dict(config["parent"]["protocol_freeze"]),
        },
        "decision_contract": {
            "budget": float(parent_config["policy"]["budget"]),
            "max_concentration_by_purpose": float(
                parent_config["policy"]["max_concentration_by_purpose"]
            ),
            "cash_variable_present": False,
            "candidate_identity": candidate_identity,
        },
        "set_native_score": dict(config["set_native_score"]),
        "outcome_columns_passed_to_frontier": [],
        "phase_a_manifest": relative_artifact_descriptor(phase_a_manifest_path, repo_root=root),
        "official_artifacts": official_descriptors,
        "summary": relative_artifact_descriptor(summary_path, repo_root=root),
        "execution_receipt": relative_artifact_descriptor(receipt_path, repo_root=root),
        "implementation_provenance": authority["implementation"],
        "environment": authority["environment"],
        "git": authority["git"],
        "selection": {"ruler": None, "coordinate": None, "window": None, "policy": None},
        "artifact_contract": {
            "expected_tag": config["phase_authority"]["phase_a_artifact_tag"],
            "exact_added_paths": [
                *sorted(str(item["path"]) for item in official_descriptors.values()),
                (model_dir / str(output["phase_a_manifest"])).relative_to(root).as_posix(),
                (model_dir / str(output["outcome_free_summary"])).relative_to(root).as_posix(),
                (model_dir / str(output["outcome_free_receipt"])).relative_to(root).as_posix(),
                (model_dir / str(output["protocol_freeze"])).relative_to(root).as_posix(),
            ],
            "direct_child_required": True,
            "annotated_tag_required": True,
            "dvc_required": False,
        },
        "phase_b_status": "blocked_until_hash_pinned_P2",
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    for descriptor in official_descriptors.values():
        path = resolve_repo_input(str(descriptor["path"]), repo_root=root)
        if relative_artifact_descriptor(path, repo_root=root) != descriptor:
            raise RuntimeError("Consolidated artifact changed before the terminal Phase-A seal.")
    freeze_path = atomic_write_json(model_dir / str(output["protocol_freeze"]), freeze)
    logger.info(
        "Frozen {} set-native cells in {:.1f}s", len(records), time.perf_counter() - started
    )
    return freeze_path


def _valid_descriptor(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"path", "bytes", "sha256"}:
        raise ValueError(f"{label} requires path, bytes, and sha256.")
    digest = str(value["sha256"])
    if (
        not isinstance(value["path"], str)
        or not isinstance(value["bytes"], int)
        or isinstance(value["bytes"], bool)
        or int(value["bytes"]) <= 0
        or len(digest) != 64
    ):
        raise ValueError(f"{label} has an invalid descriptor.")
    try:
        int(digest, 16)
    except ValueError as error:
        raise ValueError(f"{label} digest is not hexadecimal.") from error
    return dict(value)


def load_phase_b_config(path: Path) -> dict[str, Any]:
    """Load the separate evaluation config; blocked templates remain non-executable."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Phase-B config must be a YAML mapping.")
    expected_top = {
        "schema_version",
        "protocol_status",
        "protocol_tag",
        "run_tag",
        "phase_chain",
        "source_phase_a",
        "source_v1d",
        "endpoint_source",
        "evaluation",
        "claim_boundary",
        "output",
    }
    if set(payload) != expected_top:
        raise ValueError("Phase-B top-level contract changed.")
    if (
        payload["protocol_tag"]
        != "protocol/ijds-set-native-binary-robust-counterpart-2026-07-31-v1-phase-b"
        or payload["run_tag"] != "ijds-set-native-binary-robust-counterpart-2026-07-31-v1-phase-b"
    ):
        raise ValueError("Phase-B protocol or run identity changed.")
    chain = payload["phase_chain"]
    if set(chain) != {
        "phase_a_protocol_tag",
        "phase_a_protocol_commit",
        "phase_a_artifact_tag",
        "phase_b_protocol_tag",
        "phase_b_artifact_tag",
        "require_p1_direct_parent_of_a1",
        "require_a1_direct_parent_of_p2",
    } or {
        "phase_a_protocol_tag": chain["phase_a_protocol_tag"],
        "phase_a_artifact_tag": chain["phase_a_artifact_tag"],
        "phase_b_protocol_tag": chain["phase_b_protocol_tag"],
        "phase_b_artifact_tag": chain["phase_b_artifact_tag"],
        "require_p1_direct_parent_of_a1": chain["require_p1_direct_parent_of_a1"],
        "require_a1_direct_parent_of_p2": chain["require_a1_direct_parent_of_p2"],
    } != {
        "phase_a_protocol_tag": (
            "protocol/ijds-set-native-binary-robust-counterpart-2026-07-31-v1"
        ),
        "phase_a_artifact_tag": (
            "artifacts/ijds-set-native-binary-robust-counterpart-2026-07-31-v1-phase-a"
        ),
        "phase_b_protocol_tag": (
            "protocol/ijds-set-native-binary-robust-counterpart-2026-07-31-v1-phase-b"
        ),
        "phase_b_artifact_tag": (
            "artifacts/ijds-set-native-binary-robust-counterpart-2026-07-31-v1-phase-b"
        ),
        "require_p1_direct_parent_of_a1": True,
        "require_a1_direct_parent_of_p2": True,
    }:
        raise ValueError("Phase-B P1-A1-P2 topology changed.")
    source = payload["source_phase_a"]
    v1d = payload["source_v1d"]
    endpoint = payload["endpoint_source"]
    if not isinstance(source, dict) or not isinstance(v1d, dict) or not isinstance(endpoint, dict):
        raise ValueError("Phase B lacks a source authority mapping.")
    if (
        set(source)
        != {
            "artifact_tag",
            "artifact_commit",
            "freeze",
            "summary",
            "receipt",
            "phase_a_manifest",
            "solve_records",
            "allocation",
            "set_taxonomy",
            "solver_audit",
        }
        or source["artifact_tag"] != chain["phase_a_artifact_tag"]
    ):
        raise ValueError("Phase-A source authority fields or tag changed.")
    expected_v1d_tag = "artifacts/ijds-set-preserving-embedding-sensitivity-2026-07-30-v1d"
    if (
        set(v1d) != {"artifact_tag", "artifact_commit", "solve_records", "allocation"}
        or v1d["artifact_tag"] != expected_v1d_tag
    ):
        raise ValueError("V1d source authority fields or tag changed.")
    expected_v1d = {
        "artifact_tag": expected_v1d_tag,
        "artifact_commit": "276a5db8772262aad2edd8936dbe226926e412b5",
        "solve_records": {
            "path": (
                "data/processed/experiments/ijds_audit/"
                "ijds-set-preserving-embedding-sensitivity-2026-07-29-v1a/frontier/"
                "frontier_solve_records.parquet"
            ),
            "bytes": 1_782_252,
            "sha256": "c89bad6e9a7f9513f871be66da3950b3b690051915c51963936718314ea6598a",
        },
        "allocation": {
            "path": (
                "data/processed/experiments/ijds_audit/"
                "ijds-set-preserving-embedding-sensitivity-2026-07-29-v1a/frontier/"
                "frontier_funded_allocations.parquet"
            ),
            "bytes": 49_246_668,
            "sha256": "f192a70512f2fed01bb64c2b302cb47ecfd264648b7407b9b5aa50c5d666cf51",
        },
    }
    if v1d != expected_v1d:
        raise ValueError("V1d tag, commit, or exact Phase-A artifact descriptors changed.")
    if set(endpoint) != {"config", "raw_archive"}:
        raise ValueError("Endpoint source authority fields changed.")
    expected_endpoint = {
        "config": {
            "path": "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-15_v5.yaml",
            "bytes": 1371,
            "sha256": "c749befbd0ab7e0f8d6fcded7e7c730cae998032f897f65c7e7673d2a12c3715",
        },
        "raw_archive": {
            "path": "data/raw/Loan_status_2007-2020Q3.csv",
            "bytes": 1_773_470_505,
            "sha256": "5878af2a088f8ab5214c9337289fb8b5eb6c6338fd3f417b6cdc18513dc6f35f",
        },
    }
    if endpoint != expected_endpoint:
        raise ValueError("Endpoint V5 config or raw-archive descriptor changed.")
    evaluation = payload["evaluation"]
    if evaluation != {
        "role": "primary_oot",
        "expected_robust_cells": 720,
        "expected_v1d_cells_per_robust_cell": 25,
        "expected_contrasts": 18000,
        "common_outcome_assignment": "loanwise_sharp_on_funded_union",
        "inspected_v1d_evaluation_tables_reused": False,
    }:
        raise ValueError("The complete Phase-B comparison contract changed.")
    if payload["claim_boundary"] != {
        "no_selection": True,
        "no_policy_winner": True,
        "no_causal_claim": True,
        "no_conformal_guarantee_repair": True,
        "no_joint_coverage_for_cartesian_product_of_marginal_sets": True,
        "no_probabilistic_robustness_guarantee": True,
        "no_reuse_of_inspected_v1d_evaluation_tables": True,
    }:
        raise ValueError("Phase-B claim boundary changed.")
    if payload["output"] != {
        "data_root": "data/processed/experiments/ijds_audit",
        "model_root": "models/experiments/ijds_audit",
        "immutability": "hard_no_overwrite_choose_fresh_run_tag",
        "evaluated_portfolios": "evaluated_primary_portfolios.parquet",
        "monthly_v1d_contrasts": "monthly_robust_minus_v1d_contrasts.parquet",
        "window_v1d_contrasts": "window_robust_minus_v1d_contrasts.parquet",
        "evaluation_summary": "evaluation_summary.json",
        "evaluation_receipt": "evaluation_execution_receipt.json",
        "evaluation_manifest": "verified_evaluation_manifest.json",
    }:
        raise ValueError("Phase-B output contract changed.")
    status = payload.get("protocol_status")
    if status == "blocked_pending_phase_a_artifact_hashes":
        if payload["schema_version"] != "2026-07-31.v1.phase-b-template.1":
            raise ValueError("Blocked Phase-B template schema changed.")
        if chain["phase_a_protocol_commit"] is not None or any(
            source[key] is not None
            for key in (
                "artifact_commit",
                "freeze",
                "summary",
                "receipt",
                "phase_a_manifest",
                "solve_records",
                "allocation",
                "set_taxonomy",
                "solver_audit",
            )
        ):
            raise ValueError("Blocked Phase-B template contains premature Phase-A hashes.")
        return payload
    if status != "locked_hash_pinned_phase_b_before_outcomes":
        raise ValueError("Phase-B status is neither blocked nor hash-pinned.")
    if payload["schema_version"] != "2026-07-31.v1.phase-b.1":
        raise ValueError("Locked Phase-B schema version changed.")
    for key in (
        "freeze",
        "summary",
        "receipt",
        "phase_a_manifest",
        "solve_records",
        "allocation",
        "set_taxonomy",
        "solver_audit",
    ):
        _valid_descriptor(source[key], label=f"Phase-A {key}")
    for key in ("solve_records", "allocation"):
        _valid_descriptor(v1d[key], label=f"V1d {key}")
    for label, commit in (
        ("Phase-A", source["artifact_commit"]),
        ("Phase-A protocol", chain["phase_a_protocol_commit"]),
        ("V1d", v1d["artifact_commit"]),
    ):
        try:
            int(str(commit), 16)
        except ValueError as error:
            raise ValueError(f"{label} artifact commit is not hexadecimal.") from error
        if len(str(commit)) != 40:
            raise ValueError(f"{label} artifact commit must have 40 hex characters.")
    return payload


def _verified_path(descriptor: Mapping[str, Any], *, root: Path, label: str) -> Path:
    path = resolve_repo_input(str(descriptor["path"]), repo_root=root)
    if relative_artifact_descriptor(path, repo_root=root) != dict(descriptor):
        raise RuntimeError(f"{label} descriptor mismatch.")
    return path


def run_phase_b(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Evaluate only a separately tagged, exact-hash Phase-A artifact."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_phase_b_config(resolved_config)
    if config.get("protocol_status") == "blocked_pending_phase_a_artifact_hashes":
        raise RuntimeError(
            "Phase B is blocked: fill every Phase-A/V1d hash in a new config, commit it, "
            "and create the annotated P2 tag before any outcome read."
        )
    p2_protocol = _require_clean_annotated_tagged_head(root, str(config["protocol_tag"]))
    evaluation_authority = _authority(resolved_config, root)
    _require_committed_implementation(
        evaluation_authority["implementation"], commit=p2_protocol["commit"], root=root
    )
    chain = config["phase_chain"]
    p1_tag = _resolve_annotated_tag(root, str(chain["phase_a_protocol_tag"]))
    if p1_tag[1] != str(chain["phase_a_protocol_commit"]):
        raise RuntimeError("P1 protocol tag does not match its pinned commit.")
    source = config["source_phase_a"]
    source_tag = _resolve_annotated_tag(root, str(source["artifact_tag"]))
    if source_tag[1] != str(source["artifact_commit"]):
        raise RuntimeError("Phase-A artifact tag does not match its pinned commit.")
    _require_direct_parent(
        child=source_tag[1],
        parent=p1_tag[1],
        root=root,
        label="A1 Phase-A artifact commit",
    )
    _require_direct_parent(
        child=p2_protocol["commit"],
        parent=source_tag[1],
        root=root,
        label="P2 evaluation protocol commit",
    )
    v1d = config["source_v1d"]
    v1d_tag = _resolve_annotated_tag(root, str(v1d["artifact_tag"]))
    if v1d_tag[1] != str(v1d["artifact_commit"]):
        raise RuntimeError("V1d artifact tag does not match its pinned commit.")
    freeze_path = _verified_path(source["freeze"], root=root, label="Phase-A freeze")
    summary_path = _verified_path(source["summary"], root=root, label="Phase-A summary")
    receipt_path = _verified_path(source["receipt"], root=root, label="Phase-A receipt")
    manifest_path = _verified_path(source["phase_a_manifest"], root=root, label="Phase-A manifest")
    freeze = _json(freeze_path)
    manifest = _json(manifest_path)
    if (
        freeze.get("status") != PHASE_A_STATUS
        or _json(summary_path).get("status") != PHASE_A_STATUS
        or _json(receipt_path).get("status") != PHASE_A_STATUS
        or manifest.get("status") != PHASE_A_STATUS
    ):
        raise RuntimeError("Phase-A hash authorities do not attest a complete freeze.")
    if freeze.get("outcome_columns_passed_to_frontier") != []:
        raise RuntimeError("Phase-A freeze reports outcome leakage.")
    if freeze.get("protocol", {}).get("commit") != p1_tag[1]:
        raise RuntimeError("Phase-A freeze does not bind the pinned P1 commit.")
    if freeze.get("environment") != evaluation_authority["environment"]:
        raise RuntimeError("Scientific environment changed between Phase A and Phase B.")
    phase_a_implementation = freeze.get("implementation_provenance", {}).get("source_files")
    phase_b_implementation = evaluation_authority["implementation"].get("source_files")
    if not isinstance(phase_a_implementation, dict) or not isinstance(phase_b_implementation, dict):
        raise RuntimeError("Phase-A or Phase-B implementation authority is absent.")
    for path in IMPLEMENTATION_PATHS:
        relative = path.as_posix()
        if phase_a_implementation.get(relative) != phase_b_implementation.get(relative):
            raise RuntimeError(f"Scientific dependency changed from Phase A to B: {relative}.")
    official = manifest.get("official_artifacts")
    if not isinstance(official, dict) or set(official) != {
        "solve_records",
        "allocations",
        "set_taxonomy",
        "solver_audit",
    }:
        raise RuntimeError("Phase-A consolidated artifact manifest is incomplete.")
    source_official = {
        "solve_records": source["solve_records"],
        "allocations": source["allocation"],
        "set_taxonomy": source["set_taxonomy"],
        "solver_audit": source["solver_audit"],
    }
    if official != source_official or freeze.get("official_artifacts") != source_official:
        raise RuntimeError("Phase-A config, manifest, and freeze descriptors disagree.")
    robust_records_path = _verified_path(
        source["solve_records"], root=root, label="Phase-A solve records"
    )
    robust_allocation_path = _verified_path(
        source["allocation"], root=root, label="Phase-A allocation"
    )
    taxonomy_path = _verified_path(source["set_taxonomy"], root=root, label="Phase-A set taxonomy")
    audit_path = _verified_path(source["solver_audit"], root=root, label="Phase-A solver audit")
    robust_records = pd.read_parquet(robust_records_path)
    robust_allocations = pd.read_parquet(robust_allocation_path)
    taxonomy = pd.read_parquet(taxonomy_path)
    audits = pd.read_parquet(audit_path)
    phase_a_config = load_set_native_config(DEFAULT_PHASE_A_CONFIG)
    validate_phase_a_metadata(robust_records, audits, taxonomy, config=phase_a_config)
    observed_schemas = {
        "solve_records": dataframe_schema(robust_records),
        "allocations": dataframe_schema(robust_allocations),
        "set_taxonomy": dataframe_schema(taxonomy),
        "solver_audit": dataframe_schema(audits),
    }
    if manifest.get("official_schemas") != observed_schemas:
        raise RuntimeError("Phase-A consolidated schemas changed before evaluation.")
    cell_keys = [
        "window_id",
        "role",
        "period",
        "frontier_ruler",
        "frontier_coordinate",
    ]
    allocation_totals = (
        robust_allocations.groupby(cell_keys, observed=True, sort=False)["exposure"]
        .sum()
        .rename("allocation_total")
        .reset_index()
    )
    reconciled = robust_records.merge(
        allocation_totals,
        on=cell_keys,
        how="outer",
        validate="one_to_one",
        indicator="__allocation_join",
    )
    if set(reconciled["__allocation_join"].astype(str)) != {"both"} or not bool(
        np.isclose(
            pd.to_numeric(reconciled["total_allocated"], errors="raise"),
            pd.to_numeric(reconciled["allocation_total"], errors="raise"),
            rtol=0.0,
            atol=1.0e-8,
        ).all()
    ):
        raise RuntimeError("Phase-A consolidated allocations do not reconcile to records.")
    robust_records = robust_records.loc[robust_records["role"].eq("primary_oot")].copy()
    robust_allocations = robust_allocations.loc[robust_allocations["role"].eq("primary_oot")].copy()
    if len(robust_records) != int(config["evaluation"]["expected_robust_cells"]):
        raise RuntimeError("Phase-B robust primary census is incomplete.")
    v1d_records_path = _verified_path(v1d["solve_records"], root=root, label="V1d solve records")
    v1d_allocation_path = _verified_path(v1d["allocation"], root=root, label="V1d allocation")

    endpoint = config["endpoint_source"]
    endpoint_config_path = _verified_path(endpoint["config"], root=root, label="Endpoint V5 config")
    raw_path = _verified_path(endpoint["raw_archive"], root=root, label="Raw endpoint archive")

    # Outcome parsing is deliberately below every config, tag, lineage,
    # environment, consolidated-artifact, V1d, endpoint-config, and raw-hash
    # gate above. The blocked template can never reach this line.
    endpoint_config = load_v4_config(endpoint_config_path)
    if float(endpoint_config["policy"]["budget"]) != 1_000_000.0:
        raise RuntimeError("Inherited V4 evaluation budget is not the locked USD 1 million.")
    universe = load_outcome_universe(endpoint_config, raw_path=raw_path)
    outcomes = configured_archive_outcomes(universe, endpoint_config)
    primary_outcomes = outcomes.loc[outcomes["role"].eq("primary_oot")].copy()
    evaluated, robust_joined = evaluate_frozen_portfolios(
        robust_records,
        robust_allocations,
        primary_outcomes,
        config=endpoint_config,
    )
    if len(evaluated) != int(config["evaluation"]["expected_robust_cells"]):
        raise RuntimeError("Phase-B evaluated robust census is incomplete.")
    v1d_records = pd.read_parquet(v1d_records_path)
    v1d_allocations = pd.read_parquet(v1d_allocation_path)
    v1d_records = v1d_records.loc[v1d_records["role"].eq("primary_oot")].copy()
    v1d_allocations = v1d_allocations.loc[v1d_allocations["role"].eq("primary_oot")].copy()
    if len(v1d_records) != 18_000:
        raise RuntimeError("Hash-pinned V1d primary solve-record census is not 18,000.")
    _, v1d_joined = evaluate_frozen_portfolios(
        v1d_records,
        v1d_allocations,
        primary_outcomes,
        config=endpoint_config,
    )
    monthly, pooled = build_robust_minus_v1d_contrasts(
        robust_joined,
        v1d_joined,
        robust_records,
        v1d_records,
        budget=float(endpoint_config["policy"]["budget"]),
        lgd=float(endpoint_config["payoff"]["lgd"]),
    )
    if len(monthly) != 18_000 or len(pooled) != 1_200:
        raise RuntimeError("Complete robust-minus-V1d contrast census failed.")
    if any(
        _verified_path(source[key], root=root, label=f"Repeated Phase-A {key}") != original
        for key, original in (
            ("freeze", freeze_path),
            ("summary", summary_path),
            ("receipt", receipt_path),
            ("phase_a_manifest", manifest_path),
        )
    ):
        raise RuntimeError("Phase-A hash authority changed during evaluation.")
    _verified_path(v1d["solve_records"], root=root, label="Repeated V1d solve records")
    _verified_path(v1d["allocation"], root=root, label="Repeated V1d allocation")
    for key, descriptor in source_official.items():
        _verified_path(descriptor, root=root, label=f"Repeated Phase-A {key}")
    _verified_path(endpoint["config"], root=root, label="Repeated endpoint V5 config")
    _verified_path(endpoint["raw_archive"], root=root, label="Repeated raw endpoint archive")
    if _authority(resolved_config, root) != evaluation_authority:
        raise RuntimeError("Implementation, environment, or Git authority changed in Phase B.")
    data_dir, model_dir = _run_dirs(config, root)
    if data_dir.exists() or model_dir.exists():
        raise FileExistsError("Phase-B output paths are occupied.")
    data_dir.mkdir(parents=True)
    model_dir.mkdir(parents=True)
    output = config["output"]
    evaluated_path = atomic_write_parquet(
        evaluated, data_dir / "evaluation" / str(output["evaluated_portfolios"])
    )
    monthly_path = atomic_write_parquet(
        monthly, data_dir / "evaluation" / str(output["monthly_v1d_contrasts"])
    )
    pooled_path = atomic_write_parquet(
        pooled, data_dir / "evaluation" / str(output["window_v1d_contrasts"])
    )
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": PHASE_B_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol": p2_protocol,
        "evaluated_robust_cells": int(len(evaluated)),
        "monthly_robust_minus_v1d_contrasts": int(len(monthly)),
        "pooled_robust_minus_v1d_contrasts": int(len(pooled)),
        "comparison": "same_window_month_ruler_coordinate_all_25_v1d_theta_gamma_cells",
        "common_outcome_assignment": "loanwise_sharp_on_funded_union",
        "selection": {"ruler": None, "coordinate": None, "window": None, "policy": None},
        "policy_winner": None,
        "causal_interpretation": False,
    }
    summary_file = atomic_write_json(model_dir / str(output["evaluation_summary"]), summary)
    receipt_file = atomic_write_json(
        model_dir / str(output["evaluation_receipt"]),
        {
            "schema_version": str(config["schema_version"]),
            "status": PHASE_B_STATUS,
            "run_tag": str(config["run_tag"]),
            "protocol": p2_protocol,
            "completed_at_utc": utc_now_iso(),
            "source_phase_a": source,
            "source_v1d": v1d,
            "endpoint_source": endpoint,
            "outcome_refit": False,
            "outcome_selection": False,
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    manifest_file = atomic_write_json(
        model_dir / str(output["evaluation_manifest"]),
        {
            **summary,
            "artifact_status": "pending_git_artifact_commit_and_annotated_tag",
            "evaluated_portfolios": relative_artifact_descriptor(evaluated_path, repo_root=root),
            "monthly_v1d_contrasts": relative_artifact_descriptor(monthly_path, repo_root=root),
            "window_v1d_contrasts": relative_artifact_descriptor(pooled_path, repo_root=root),
            "summary": relative_artifact_descriptor(summary_file, repo_root=root),
            "receipt": relative_artifact_descriptor(receipt_file, repo_root=root),
            "source_phase_a": source,
            "source_v1d": v1d,
            "endpoint_source": endpoint,
            "implementation_provenance": evaluation_authority["implementation"],
            "environment": evaluation_authority["environment"],
            "git": evaluation_authority["git"],
            "selection": {
                "theta": None,
                "gamma": None,
                "ruler": None,
                "coordinate": None,
                "window": None,
                "policy": None,
            },
            "policy_winner": None,
            "causal_interpretation": False,
            "conformal_guarantee_repair": False,
            "joint_coverage_for_cartesian_product": False,
            "probabilistic_robustness_guarantee": False,
            "artifact_contract": {
                "expected_tag": chain["phase_b_artifact_tag"],
                "expected_parent": p2_protocol["commit"],
                "exact_added_paths": [
                    evaluated_path.relative_to(root).as_posix(),
                    monthly_path.relative_to(root).as_posix(),
                    pooled_path.relative_to(root).as_posix(),
                    summary_file.relative_to(root).as_posix(),
                    receipt_file.relative_to(root).as_posix(),
                    (model_dir / str(output["evaluation_manifest"])).relative_to(root).as_posix(),
                ],
                "direct_child_required": True,
                "annotated_tag_required": True,
                "dvc_required": False,
            },
        },
    )
    return manifest_file


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    config = args.config
    if config is None:
        config = DEFAULT_PHASE_A_CONFIG if args.phase == "outcome-free" else DEFAULT_PHASE_B_CONFIG
    if args.phase == "outcome-free":
        path = run_phase_a(config_path=config, repo_root=ROOT, runtime_root=args.runtime_root)
    else:
        path = run_phase_b(config_path=config, repo_root=ROOT)
    logger.info("Wrote {}", path)


if __name__ == "__main__":
    main()
