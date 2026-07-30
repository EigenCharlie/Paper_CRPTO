"""Run retrospective Phase B for IJDS set-preserving embedding sensitivity V1c."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import numpy as np
import pandas as pd
import yaml
from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ijds_audit.config import load_v4_config  # noqa: E402
from src.ijds_audit.evaluation import (  # noqa: E402
    RESOLUTION_CHARGED_OFF_BY_CUTOFF,
    RESOLUTION_FULLY_PAID_BY_CUTOFF,
    RESOLUTION_NONTERMINAL,
    RESOLUTION_TERMINAL_AFTER_CUTOFF,
    RESOLUTION_TERMINAL_DATE_MISSING,
    evaluate_frozen_portfolios,
)
from src.ijds_audit.protocol import (  # noqa: E402
    configured_archive_outcomes,
    load_outcome_universe,
)
from src.ijds_challengers.set_preserving_embedding import (  # noqa: E402
    SetPreservingFrontierBuild,
    primary_outcome_audit,
)
from src.ijds_challengers.set_preserving_embedding_v1c import (  # noqa: E402
    build_v1c_sharp_embedding_contrasts,
    validate_v1c_complete_frontier,
)
from src.utils.isolated_experiment import (  # noqa: E402
    dataframe_schema,
    environment_provenance,
    package_version,
    sha256_file,
)
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    utc_now_iso,
)

DEFAULT_CONFIG_PATH = (
    ROOT / "configs/experiments/ijds_set_preserving_embedding_sensitivity_2026-07-29_v1c.yaml"
)
CONFIG_RELATIVE = Path(
    "configs/experiments/ijds_set_preserving_embedding_sensitivity_2026-07-29_v1c.yaml"
)
PROTOCOL_RELATIVE = Path(
    "docs/research/ijds_set_preserving_embedding_sensitivity_v1c_protocol_2026-07-29.md"
)
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
FREEZE_STATUS = "outcome_free_set_preserving_allocations_frozen_before_outcomes"
EVALUATION_STATUS = "retrospective_post_inspection_phase_b_complete_not_confirmatory"
PENDING_ARTIFACT_STATUS = "pending_git_artifact_commit_and_annotated_tag"
SOURCE_KEYS = (
    "solve_records",
    "allocations",
    "embedding_diagnostics",
    "minimum_endpoint_diagnostics",
    "objective_optimum_diagnostics",
    "allocation_contrasts",
    "order_sensitivity",
    "independent_validation",
    "freeze",
    "summary",
    "receipt",
)
PHASE_A_FRAME_KEYS = SOURCE_KEYS[:8]
DATA_OUTPUT_KEYS = (
    "evaluated_portfolios",
    "monthly_sharp_contrasts",
    "window_sharp_contrasts",
    "metric_direction_census",
    "outcome_join_audit",
)
MODEL_OUTPUT_KEYS = (
    "join_identity",
    "evaluation_summary",
    "evaluation_receipt",
    "evaluation_manifest",
)
IMPLEMENTATION_PATHS = (
    CONFIG_RELATIVE,
    PROTOCOL_RELATIVE,
    Path("docs/research/ijds_set_preserving_embedding_sensitivity_v1a_stop_2026-07-29.md"),
    Path("scripts/experiments/run_ijds_set_preserving_embedding_sensitivity_v1c.py"),
    Path("src/evaluation/policy_contrast_bounds.py"),
    Path("src/ijds_audit/evaluation.py"),
    Path("src/ijds_audit/policy_support.py"),
    Path("src/ijds_audit/protocol.py"),
    Path("src/ijds_challengers/normalized_frontier.py"),
    Path("src/ijds_challengers/set_preserving_embedding.py"),
    Path("src/ijds_challengers/set_preserving_embedding_v1c.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the Phase-B-only runner and the later read-only B verifier."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--protected-read-root", type=Path)
    parser.add_argument("--verify-artifact-commit", action="store_true")
    args = parser.parse_args(argv)
    if not args.verify_artifact_commit and args.protected_read_root is None:
        parser.error("--protected-read-root is required for Phase B")
    return args


def _validated_relative_path(value: Any, *, label: str) -> str:
    text = str(value)
    posix = PurePosixPath(text)
    if (
        not text
        or "\\" in text
        or posix.is_absolute()
        or PureWindowsPath(text).is_absolute()
        or any(part in {"", ".", ".."} for part in posix.parts)
        or posix.as_posix() != text
    ):
        raise ValueError(f"{label} must be one canonical repository-relative POSIX path.")
    return text


def _validated_basename(value: Any, *, label: str) -> str:
    text = str(value)
    if not text or Path(text).name != text or "/" in text or "\\" in text or text in {".", ".."}:
        raise ValueError(f"{label} must be one plain output basename.")
    return text


def _validated_descriptor(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"path", "bytes", "sha256"}:
        raise ValueError(f"{label} must contain exactly path/bytes/sha256.")
    path = _validated_relative_path(value["path"], label=f"{label}.path")
    size = value["bytes"]
    digest = str(value["sha256"])
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ValueError(f"{label}.bytes must be a nonnegative integer.")
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError(f"{label}.sha256 must be a lowercase SHA-256 digest.")
    return {"path": path, "bytes": size, "sha256": digest}


def _expected_output_paths(config: Mapping[str, Any]) -> tuple[str, ...]:
    output = config["output"]
    run_tag = str(config["run_tag"])
    data_root = _validated_relative_path(output["data_root"], label="output.data_root")
    model_root = _validated_relative_path(output["model_root"], label="output.model_root")
    subdir = _validated_basename(output["evaluation_subdir"], label="evaluation_subdir")
    data_paths = [
        PurePosixPath(data_root, run_tag, subdir, _validated_basename(output[key], label=key))
        for key in DATA_OUTPUT_KEYS
    ]
    model_paths = [
        PurePosixPath(model_root, run_tag, _validated_basename(output[key], label=key))
        for key in MODEL_OUTPUT_KEYS
    ]
    return tuple(path.as_posix() for path in (*data_paths, *model_paths))


def load_v1c_config(path: Path) -> dict[str, Any]:
    """Load the singular retrospective V1c contract and reject scope drift."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("V1c config root must be a mapping.")
    required = {
        "schema_version",
        "protocol_status",
        "protocol_tag",
        "run_tag",
        "hypothesis",
        "inspection_context",
        "scientific_reconciliation",
        "git_transport",
        "original_v1a",
        "source_v1a_artifacts",
        "outcomes",
        "protected_source",
        "normalization",
        "embedding",
        "frontier",
        "solver",
        "contrasts",
        "metrics",
        "claim_boundary",
        "expected_census",
        "output",
    }
    if not required.issubset(payload):
        raise ValueError(f"V1c config is missing fields: {sorted(required - set(payload))}.")
    if payload["protocol_status"] != "retrospective_post_inspection_phase_b_only":
        raise ValueError("V1c must remain explicitly retrospective and Phase-B-only.")
    inspected = payload["inspection_context"]
    expected_flags = {
        "classification": "retrospective_post_inspection_recovery",
        "replay_clean": False,
        "confirmatory": False,
        "v1a_is_evidence": False,
        "phase_a_rerun": False,
    }
    if any(inspected.get(key) != value for key, value in expected_flags.items()):
        raise ValueError("V1c inspection chronology or non-confirmatory boundary changed.")
    stop_note = inspected.get("superseded_operational_stop", {})
    if (
        stop_note.get("contemporaneous_git_evidence") is not False
        or stop_note.get("treatment")
        != "reconstructed_local_note_of_earlier_decision_transparently_superseded_by_v1c"
    ):
        raise ValueError("V1c must not present the reconstructed stop note as contemporaneous.")
    scope = inspected.get("scope", {})
    if not all(
        scope.get(key) is True
        for key in (
            "phase_b_only",
            "no_winner",
            "no_selection",
            "no_p_values",
            "no_confirmatory_language",
        )
    ):
        raise ValueError("V1c cannot relax its complete-grid/no-selection boundary.")
    reconciliation = payload["scientific_reconciliation"]
    expected_reconciliation = {
        "exact_v1a_sections": [
            "hypothesis",
            "outcomes",
            "normalization",
            "embedding",
            "frontier",
            "solver",
            "contrasts",
            "metrics",
            "claim_boundary",
        ],
        "expected_census_allowed_additions": {
            "joined_primary_funded_rows": 1_783_274,
            "outcome_audit_rows": 15,
        },
        "v1a_phase_a_or_transport_sections_not_reused": [
            "phase_authority",
            "parent",
            "source_ingest",
            "stop_rules",
            "output",
        ],
    }
    if reconciliation != expected_reconciliation:
        raise ValueError("The declarative V1a/V1c scientific reconciliation contract changed.")
    if payload["protected_source"] != {
        "binding": "explicit_distinct_hash_bound_source_root",
        "raw_bytes": 1_773_470_505,
    }:
        raise ValueError("The explicit distinct protected-source binding changed.")
    transport = payload["git_transport"]
    if (
        transport.get("topology")
        != "annotated_protocol_P_to_direct_child_source_A_to_direct_child_evaluation_B"
        or transport.get("annotated_tags_required") is not True
        or transport.get("single_parent_required") is not True
        or transport.get("exact_diff_required") is not True
        or transport.get("paths_absent_in_parent_required") is not True
        or transport.get("dvc_required") is not False
        or transport.get("protocol_tag") != payload["protocol_tag"]
    ):
        raise ValueError("The Git-native P-to-A-to-B transport contract changed.")
    tags = [
        str(transport[key])
        for key in ("protocol_tag", "source_artifact_tag", "evaluation_artifact_tag")
    ]
    if any(not tag for tag in tags) or len(set(tags)) != 3:
        raise ValueError("Protocol/source/evaluation tags must be three distinct names.")
    artifacts = payload["source_v1a_artifacts"]
    if not isinstance(artifacts, dict) or set(artifacts) != set(SOURCE_KEYS):
        raise ValueError("V1c must bind exactly the eleven V1a source files.")
    descriptors = {
        key: _validated_descriptor(artifacts[key], label=f"source_v1a_artifacts.{key}")
        for key in SOURCE_KEYS
    }
    source_paths = tuple(str(item) for item in transport.get("protocol_to_source_paths", []))
    if len(source_paths) != len(set(source_paths)) or set(source_paths) != {
        descriptor["path"] for descriptor in descriptors.values()
    }:
        raise ValueError("The P-to-A diff is not exactly the eleven V1a descriptors.")
    for path_value in source_paths:
        _validated_relative_path(path_value, label="protocol_to_source_paths")
    original = payload["original_v1a"]
    for key in ("tag_object", "protocol_commit", "protocol_parent"):
        value = str(original.get(key, ""))
        if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError(f"original_v1a.{key} is not one SHA-1 object ID.")
    _validated_descriptor(original.get("config"), label="original_v1a.config")
    _validated_descriptor(original.get("protocol"), label="original_v1a.protocol")
    normalization = payload["normalization"]
    if normalization != {
        "capital_source": "parent_policy_budget",
        "committed_budget_per_period": 1_000_000.0,
        "monthly": "parent_committed_budget",
        "pooled": "period_count_times_parent_committed_budget",
        "common_across_policies": True,
        "solver_allocated_capital_renormalization": "forbidden",
    }:
        raise ValueError("The fixed common-capital estimand changed.")
    output = payload["output"]
    if (
        output.get("data_root") != ALLOWED_DATA_ROOT.as_posix()
        or output.get("model_root") != ALLOWED_MODEL_ROOT.as_posix()
    ):
        raise ValueError("V1c outputs escaped the isolated IJDS audit roots.")
    if output.get("artifact_status_at_runner_exit") != PENDING_ARTIFACT_STATUS:
        raise ValueError("The runner cannot pre-attest a future artifact commit.")
    expected_outputs = _expected_output_paths(payload)
    configured_outputs = tuple(
        str(item) for item in transport.get("source_to_evaluation_paths", [])
    )
    if len(configured_outputs) != len(set(configured_outputs)) or set(configured_outputs) != set(
        expected_outputs
    ):
        raise ValueError("The A-to-B diff is not exactly the nine compact V1c outputs.")
    for path_value in configured_outputs:
        _validated_relative_path(path_value, label="source_to_evaluation_paths")
    return payload


def _git(
    root: Path, arguments: Sequence[str], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"Git command failed ({' '.join(arguments)}): {result.stderr.strip()}")
    return result


def _tag_authority(root: Path, tag: str) -> dict[str, str]:
    """Resolve only one explicit annotated refs/tags object and peeled commit."""
    value = str(tag)
    reference = f"refs/tags/{value}"
    if (
        value.startswith(("-", "refs/"))
        or _git(root, ["check-ref-format", reference], check=False).returncode != 0
    ):
        raise RuntimeError(f"Invalid explicit tag name: {tag!r}.")
    object_id = _git(root, ["rev-parse", "--verify", "--end-of-options", reference]).stdout.strip()
    object_type = _git(root, ["cat-file", "-t", object_id]).stdout.strip()
    commit = _git(
        root,
        ["rev-parse", "--verify", "--end-of-options", f"{reference}^{{commit}}"],
    ).stdout.strip()
    if object_type != "tag" or len(object_id) != 40 or len(commit) != 40:
        raise RuntimeError(f"Tag {tag!r} must be an annotated SHA-1 tag object.")
    return {"tag": value, "tag_object": object_id, "commit": commit}


def _head_commit(root: Path) -> str:
    commit = _git(root, ["rev-parse", "--verify", "HEAD^{commit}"]).stdout.strip()
    if len(commit) != 40:
        raise RuntimeError("A readable SHA-1 HEAD commit is required.")
    return commit


def _commit_parents(root: Path, commit: str) -> tuple[str, ...]:
    fields = _git(root, ["rev-list", "--parents", "-n", "1", commit]).stdout.strip().split()
    if not fields or fields[0] != commit:
        raise RuntimeError(f"Could not read commit parentage for {commit}.")
    return tuple(fields[1:])


def _commit_additions(root: Path, commit: str) -> tuple[str, ...]:
    output = _git(
        root,
        ["diff-tree", "--no-commit-id", "--name-status", "-r", "--no-renames", commit],
    ).stdout
    paths: list[str] = []
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) != 2 or fields[0] != "A":
            raise RuntimeError(f"Commit {commit} contains a non-addition diff entry: {line!r}.")
        paths.append(_validated_relative_path(fields[1], label="Git diff path"))
    if len(paths) != len(set(paths)):
        raise RuntimeError(f"Commit {commit} contains duplicate diff paths.")
    return tuple(paths)


def _path_exists_at_commit(root: Path, commit: str, relative_path: str) -> bool:
    return _git(root, ["cat-file", "-e", f"{commit}:{relative_path}"], check=False).returncode == 0


def _git_blob_bytes(root: Path, commit: str, relative_path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git blob is unavailable at {commit}:{relative_path}.")
    return result.stdout


def _bytes_descriptor(payload: bytes, *, path: str) -> dict[str, Any]:
    return {"path": path, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _blob_descriptor(root: Path, commit: str, relative_path: str) -> dict[str, Any]:
    return _bytes_descriptor(
        _git_blob_bytes(root, commit, relative_path),
        path=_validated_relative_path(relative_path, label="Git blob path"),
    )


def _resolve_repo_path(root: Path, relative_path: str) -> Path:
    relative = _validated_relative_path(relative_path, label="repository path")
    target = (root / Path(relative)).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as error:
        raise RuntimeError(f"Repository path escaped its root: {relative}.") from error
    return target


def _file_descriptor(path: Path, *, logical_path: str) -> dict[str, Any]:
    logical = _validated_relative_path(logical_path, label="artifact logical path")
    if not path.is_file():
        raise RuntimeError(f"Required artifact is not a file: {logical}.")
    return {"path": logical, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def _require_descriptor_match(
    observed: Mapping[str, Any], expected: Mapping[str, Any], *, label: str
) -> None:
    if dict(observed) != dict(expected):
        raise RuntimeError(f"Descriptor mismatch for {label}.")


def _git_state(root: Path, *, include_untracked: bool) -> dict[str, Any]:
    mode = "all" if include_untracked else "no"
    lines = tuple(
        line
        for line in _git(
            root, ["status", "--porcelain=v1", f"--untracked-files={mode}"], check=True
        ).stdout.splitlines()
        if line
    )
    return {
        "commit": _head_commit(root),
        "dirty": bool(lines),
        "entries": len(lines),
        "lines": list(lines),
    }


def _require_exact_addition_commit(
    root: Path,
    *,
    child: str,
    parent: str,
    expected_paths: Sequence[str],
) -> None:
    if _commit_parents(root, child) != (parent,):
        raise RuntimeError(f"Commit {child} is not the required single-parent direct child.")
    additions = _commit_additions(root, child)
    if set(additions) != set(expected_paths) or len(additions) != len(expected_paths):
        raise RuntimeError(f"Commit {child} does not add exactly its locked path set.")
    preexisting = [path for path in expected_paths if _path_exists_at_commit(root, parent, path)]
    if preexisting:
        raise RuntimeError(f"Artifact paths already existed at parent {parent}: {preexisting}.")


def _portable_environment(root: Path) -> dict[str, Any]:
    """Reproduce V1a's privacy-safe runtime binding exactly."""
    environment = environment_provenance(root)
    executable = Path(str(environment.pop("executable"))).read_bytes()
    environment["executable"] = {
        "binding": "sys.executable",
        "bytes": len(executable),
        "sha256": hashlib.sha256(executable).hexdigest(),
    }
    environment["packages"]["ortools"] = package_version("ortools")
    environment["packages"]["PyYAML"] = package_version("PyYAML")
    environment["packages"]["loguru"] = package_version("loguru")
    return environment


def _require_implementation_bound_to_protocol(
    root: Path,
    *,
    protocol_commit: str,
    source_commit: str,
) -> dict[str, dict[str, Any]]:
    """Bind current Phase-B code to identical blobs at P and A."""
    descriptors: dict[str, dict[str, Any]] = {}
    for relative in IMPLEMENTATION_PATHS:
        name = relative.as_posix()
        at_protocol = _blob_descriptor(root, protocol_commit, name)
        at_source = _blob_descriptor(root, source_commit, name)
        if at_protocol != at_source:
            raise RuntimeError(f"Implementation path changed between P and A: {name}.")
        current = _file_descriptor(_resolve_repo_path(root, name), logical_path=name)
        if current != at_source:
            raise RuntimeError(f"Worktree implementation differs from source commit A: {name}.")
        descriptors[name] = current
    return descriptors


def _require_scientific_reconciliation(
    config: Mapping[str, Any], original_v1a_config: Mapping[str, Any]
) -> None:
    """Fail closed unless every shared scientific field equals the V1a blob."""
    contract = config["scientific_reconciliation"]
    for section in contract["exact_v1a_sections"]:
        if config.get(section) != original_v1a_config.get(section):
            raise RuntimeError(
                f"V1c scientific section {section!r} differs from the original V1a config blob."
            )
    additions = contract["expected_census_allowed_additions"]
    current_census = dict(config["expected_census"])
    for key, value in additions.items():
        if current_census.pop(key, None) != value:
            raise RuntimeError(f"V1c expected-census addition changed for {key}.")
    if current_census != original_v1a_config.get("expected_census"):
        raise RuntimeError("V1c shared expected census differs from the original V1a config blob.")


def _verify_original_v1a_authority(config: Mapping[str, Any], root: Path) -> dict[str, str]:
    original = config["original_v1a"]
    authority = _tag_authority(root, str(original["protocol_tag"]))
    if authority["tag_object"] != str(original["tag_object"]) or authority["commit"] != str(
        original["protocol_commit"]
    ):
        raise RuntimeError("The original V1a annotated tag object or peeled commit changed.")
    if _commit_parents(root, authority["commit"]) != (str(original["protocol_parent"]),):
        raise RuntimeError("The original V1a commit no longer has its locked single parent.")
    for label in ("config", "protocol"):
        expected = _validated_descriptor(original[label], label=f"original_v1a.{label}")
        if _blob_descriptor(root, authority["commit"], expected["path"]) != expected:
            raise RuntimeError(f"The original V1a {label} Git blob descriptor changed.")
    config_descriptor = _validated_descriptor(original["config"], label="original_v1a.config")
    original_payload = yaml.safe_load(
        _git_blob_bytes(root, authority["commit"], config_descriptor["path"])
    )
    if not isinstance(original_payload, dict):
        raise RuntimeError("The original V1a config Git blob is not a mapping.")
    _require_scientific_reconciliation(config, original_payload)
    return authority


def _verify_source_payloads(
    config: Mapping[str, Any],
    *,
    root: Path,
    paths: Mapping[str, Path],
) -> dict[str, Any]:
    """Audit all V1a freeze identities, descriptors, schemas, and chronology fields."""
    freeze = json.loads(paths["freeze"].read_text(encoding="utf-8"))
    summary = json.loads(paths["summary"].read_text(encoding="utf-8"))
    receipt = json.loads(paths["receipt"].read_text(encoding="utf-8"))
    original = config["original_v1a"]
    expected_identity = {
        "schema_version": "2026-07-29.2",
        "run_tag": str(original["run_tag"]),
        "protocol_tag": str(original["protocol_tag"]),
        "protocol_commit": str(original["protocol_commit"]),
    }
    for label, payload in (("freeze", freeze), ("summary", summary), ("receipt", receipt)):
        for key, value in expected_identity.items():
            if payload.get(key) != value:
                raise RuntimeError(f"V1a {label} identity mismatch for {key}.")
        if payload.get("status") != FREEZE_STATUS:
            raise RuntimeError(f"V1a {label} has an unexpected scientific status.")
        if (
            payload.get("protected_stages_run") != []
            or payload.get("protected_artifacts_written") != []
        ):
            raise RuntimeError(f"V1a {label} reports protected execution or writes.")
        protected = payload.get("protected_artifacts_read")
        expected_protected = {
            "path": str(config["outcomes"]["raw_path"]),
            "bytes": int(config["protected_source"]["raw_bytes"]),
            "sha256": str(config["outcomes"]["raw_sha256"]),
        }
        if protected != [expected_protected]:
            raise RuntimeError(f"V1a {label} protected-read descriptor changed.")
    if (
        freeze.get("outcome_columns_passed_to_frontier") != []
        or summary.get("outcome_columns_passed") != []
        or receipt.get("outcome_columns_passed") != []
    ):
        raise RuntimeError("V1a reports outcome leakage into Phase A.")
    null_selection = {
        "theta": None,
        "gamma": None,
        "ruler": None,
        "coordinate": None,
        "window": None,
        "policy": None,
    }
    if freeze.get("selection") != null_selection or summary.get("selection") != null_selection:
        raise RuntimeError("V1a reports a post-inspection policy/grid selection.")
    expected_git = {
        "commit": str(original["protocol_commit"]),
        "dirty": False,
        "dirty_entries": 0,
        "dirty_paths": [],
    }
    if freeze.get("git") != expected_git:
        raise RuntimeError("V1a freeze does not retain its exact clean Git state.")
    if freeze.get("environment") != _portable_environment(root):
        raise RuntimeError("The scientific runtime differs from the V1a frozen runtime.")
    artifacts = config["source_v1a_artifacts"]
    if set(freeze.get("outcome_free_artifacts", {})) != set(PHASE_A_FRAME_KEYS) or set(
        freeze.get("schemas", {})
    ) != set(PHASE_A_FRAME_KEYS):
        raise RuntimeError("V1a freeze has an incomplete Phase-A artifact/schema census.")
    for key in PHASE_A_FRAME_KEYS:
        if freeze["outcome_free_artifacts"].get(key) != artifacts[key]:
            raise RuntimeError(f"V1a freeze descriptor mismatch for {key}.")
    if (
        freeze.get("summary") != artifacts["summary"]
        or freeze.get("execution_receipt") != artifacts["receipt"]
    ):
        raise RuntimeError("V1a freeze summary/receipt descriptors changed.")
    source_config = _validated_descriptor(original["config"], label="original_v1a.config")
    provenance = freeze.get("implementation_provenance", {}).get("source_files", {})
    if provenance.get(source_config["path"]) != source_config:
        raise RuntimeError("V1a freeze does not bind its original config bytes.")
    decision = freeze.get("decision_contract")
    expected_decision = {
        "budget": 1_000_000.0,
        "max_concentration_by_purpose": 0.25,
        "lgd": 0.45,
        "raw_path": str(config["outcomes"]["raw_path"]),
        "raw_sha256": str(config["outcomes"]["raw_sha256"]),
        "roles": list(config["frontier"]["roles"]),
    }
    if (
        not isinstance(decision, dict)
        or {key: decision.get(key) for key in expected_decision} != expected_decision
        or not isinstance(decision.get("candidate_identity"), dict)
    ):
        raise RuntimeError("V1a decision/source contract differs from V1c.")
    return freeze


def verify_source_authority(
    config: Mapping[str, Any],
    *,
    repo_root: Path,
    required_head: str,
    require_untracked_clean: bool,
) -> dict[str, Any]:
    """Verify P -> A and all eleven source bytes; safe to repeat for TOCTOU gates."""
    root = repo_root.resolve()
    transport = config["git_transport"]
    protocol = _tag_authority(root, str(transport["protocol_tag"]))
    source = _tag_authority(root, str(transport["source_artifact_tag"]))
    head = _head_commit(root)
    if head != required_head:
        raise RuntimeError(f"HEAD {head} differs from the required authority {required_head}.")
    state = _git_state(root, include_untracked=require_untracked_clean)
    if state["dirty"]:
        cleanliness = "full" if require_untracked_clean else "tracked"
        raise RuntimeError(f"V1c requires a clean {cleanliness} worktree: {state['lines']}.")
    source_paths = tuple(str(item) for item in transport["protocol_to_source_paths"])
    _require_exact_addition_commit(
        root,
        child=source["commit"],
        parent=protocol["commit"],
        expected_paths=source_paths,
    )
    expected_descriptors = config["source_v1a_artifacts"]
    materialized: dict[str, Path] = {}
    for key in SOURCE_KEYS:
        expected = _validated_descriptor(
            expected_descriptors[key], label=f"source_v1a_artifacts.{key}"
        )
        _require_descriptor_match(
            _blob_descriptor(root, source["commit"], expected["path"]),
            expected,
            label=f"source artifact Git blob {key}",
        )
        path = _resolve_repo_path(root, expected["path"])
        _require_descriptor_match(
            _file_descriptor(path, logical_path=expected["path"]),
            expected,
            label=f"source artifact worktree {key}",
        )
        materialized[key] = path
    original = _verify_original_v1a_authority(config, root)
    implementation = _require_implementation_bound_to_protocol(
        root,
        protocol_commit=protocol["commit"],
        source_commit=source["commit"],
    )
    freeze = _verify_source_payloads(config, root=root, paths=materialized)
    return {
        "protocol": protocol,
        "source": source,
        "original_v1a": original,
        "git": state,
        "implementation": implementation,
        "paths": materialized,
        "freeze": freeze,
    }


def _load_and_validate_phase_a(
    config: Mapping[str, Any], source_authority: Mapping[str, Any]
) -> SetPreservingFrontierBuild:
    paths = source_authority["paths"]
    build = SetPreservingFrontierBuild(
        solve_records=pd.read_parquet(paths["solve_records"]),
        allocations=pd.read_parquet(paths["allocations"]),
        embedding_diagnostics=pd.read_parquet(paths["embedding_diagnostics"]),
        minimum_endpoint_diagnostics=pd.read_parquet(paths["minimum_endpoint_diagnostics"]),
        objective_optimum_diagnostics=pd.read_parquet(paths["objective_optimum_diagnostics"]),
        allocation_contrasts=pd.read_parquet(paths["allocation_contrasts"]),
        order_sensitivity=pd.read_parquet(paths["order_sensitivity"]),
        independent_validation=pd.read_parquet(paths["independent_validation"]),
    )
    freeze = source_authority["freeze"]
    for key in PHASE_A_FRAME_KEYS:
        if dataframe_schema(getattr(build, key)) != freeze["schemas"][key]:
            raise RuntimeError(f"V1a materialized schema mismatch for {key}.")
    validate_v1c_complete_frontier(
        build,
        config=config,
        budget=float(config["normalization"]["committed_budget_per_period"]),
    )
    return build


def _candidate_identity_contract(frame: pd.DataFrame) -> dict[str, Any]:
    """Recompute V1a's exact role-period-ID identity without persisting IDs."""
    required = {"id", "role", "period"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise KeyError(f"Candidate identity frame is missing columns: {missing}.")
    identity = frame.loc[:, ["role", "period", "id"]].copy()
    if bool(identity.isna().any(axis=None)):
        raise RuntimeError("Candidate identity contains a missing role, period, or ID.")
    identity = identity.astype("string")
    if bool(identity["id"].duplicated().any()):
        raise RuntimeError("Candidate identity contains duplicate loan IDs.")
    identity = identity.sort_values(["role", "period", "id"], kind="mergesort")

    def digest(rows: pd.DataFrame) -> str:
        hasher = hashlib.sha256()
        for row in rows.itertuples(index=False, name=None):
            encoded = json.dumps(list(row), ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
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


def _validate_endpoint_values(frame: pd.DataFrame, *, label: str) -> dict[str, int]:
    """Allow only true missing endpoints or finite binary values with matching reasons."""
    required = {"snapshot_default", "snapshot_resolution"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise RuntimeError(f"{label} endpoint is missing columns: {missing}.")
    original = frame["snapshot_default"]
    nonmissing = original.notna()
    invalid_scalar_type = original.loc[nonmissing].map(
        lambda value: isinstance(value, (str, bytes, bool, np.bool_))
    )
    if bool(invalid_scalar_type.any()):
        raise RuntimeError(f"{label} endpoint contains a string/boolean binary label.")
    numeric = pd.to_numeric(original, errors="coerce")
    values = numeric.to_numpy(dtype=float, na_value=np.nan)
    if bool((nonmissing & numeric.isna()).any()) or not bool(np.isfinite(values[nonmissing]).all()):
        raise RuntimeError(f"{label} endpoint contains an invalid or non-finite label.")
    if not bool(numeric.loc[nonmissing].isin([0, 1]).all()):
        raise RuntimeError(f"{label} endpoint contains a non-binary observed label.")
    resolution = frame["snapshot_resolution"]
    if bool(resolution.isna().any()):
        raise RuntimeError(f"{label} endpoint contains a missing resolution reason.")
    reasons = resolution.astype(str)
    unresolved_reasons = {
        RESOLUTION_TERMINAL_DATE_MISSING,
        RESOLUTION_TERMINAL_AFTER_CUTOFF,
        RESOLUTION_NONTERMINAL,
    }
    allowed = {
        RESOLUTION_FULLY_PAID_BY_CUTOFF,
        RESOLUTION_CHARGED_OFF_BY_CUTOFF,
        *unresolved_reasons,
    }
    if not set(reasons).issubset(allowed):
        raise RuntimeError(f"{label} endpoint contains an unknown resolution reason.")
    zero = numeric.eq(0).fillna(False)
    one = numeric.eq(1).fillna(False)
    unresolved = numeric.isna()
    if (
        not bool(reasons.loc[zero].eq(RESOLUTION_FULLY_PAID_BY_CUTOFF).all())
        or not bool(reasons.loc[one].eq(RESOLUTION_CHARGED_OFF_BY_CUTOFF).all())
        or not set(reasons.loc[unresolved]).issubset(unresolved_reasons)
    ):
        raise RuntimeError(f"{label} labels and resolution reasons are inconsistent.")
    return {
        "rows": int(len(frame)),
        "resolved_rows": int(nonmissing.sum()),
        "unresolved_rows": int((~nonmissing).sum()),
    }


def _resolve_protected_raw(
    config: Mapping[str, Any], *, protected_read_root: Path, repo_root: Path
) -> tuple[Path, dict[str, Any]]:
    root = protected_read_root.resolve()
    if not root.is_dir():
        raise RuntimeError("The protected-read root is not an existing directory.")
    if root == repo_root.resolve():
        raise RuntimeError(
            "--protected-read-root must be distinct from the V1c execution checkout."
        )
    logical = _validated_relative_path(config["outcomes"]["raw_path"], label="outcomes.raw_path")
    path = (root / Path(logical)).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise RuntimeError("The protected raw path escaped --protected-read-root.") from error
    observed = _file_descriptor(path, logical_path=logical)
    expected = {
        "path": logical,
        "bytes": int(config["protected_source"]["raw_bytes"]),
        "sha256": str(config["outcomes"]["raw_sha256"]),
    }
    if observed != expected:
        raise RuntimeError("The protected raw archive descriptor changed.")
    return path, observed


def _dataframe_content_identity(frame: pd.DataFrame) -> dict[str, Any]:
    """Hash the in-memory joined table compactly under the frozen pandas runtime."""
    keys = ["window_id", "period", "policy_label", "id"]
    missing = sorted(set(keys) - set(frame.columns))
    if missing:
        raise RuntimeError(f"Joined table cannot be identity-hashed; missing {missing}.")
    if bool(frame.duplicated(keys).any()):
        raise RuntimeError("Joined funded-allocation identity is not unique.")
    columns = sorted(str(column) for column in frame.columns)
    ordered = frame.sort_values(keys, kind="mergesort").loc[:, columns]
    hashes = pd.util.hash_pandas_object(ordered, index=False, categorize=True).to_numpy(
        dtype="<u8", copy=False
    )
    return {
        "rows": int(len(frame)),
        "columns": columns,
        "schema": dataframe_schema(frame),
        "sha256": hashlib.sha256(hashes.tobytes(order="C")).hexdigest(),
        "canonicalization": (
            "pandas_hash_pandas_object_index_false_categorize_true_uint64_le_"
            "after_window_period_policy_id_mergesort_all_columns_lexicographic"
        ),
        "pandas_version": package_version("pandas"),
    }


def _output_directories(config: Mapping[str, Any], root: Path) -> tuple[Path, Path, Path]:
    output = config["output"]
    run_tag = str(config["run_tag"])
    data_dir = _resolve_repo_path(root, f"{output['data_root']}/{run_tag}")
    model_dir = _resolve_repo_path(root, f"{output['model_root']}/{run_tag}")
    evaluation_dir = data_dir / str(output["evaluation_subdir"])
    return data_dir, model_dir, evaluation_dir


def _preflight_fresh_outputs(config: Mapping[str, Any], *, root: Path) -> None:
    data_dir, model_dir, _ = _output_directories(config, root)
    occupied = [path for path in (data_dir, model_dir) if path.exists()]
    if occupied:
        raise FileExistsError(
            "V1c run tag is occupied; no overwrite is permitted: "
            + ", ".join(path.relative_to(root).as_posix() for path in occupied)
        )


def _relative_descriptor(path: Path, *, root: Path) -> dict[str, Any]:
    try:
        logical = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise RuntimeError("Output artifact escaped the repository root.") from error
    return _file_descriptor(path, logical_path=logical)


def _negative_control_summary(window: pd.DataFrame) -> dict[str, Any]:
    negative = window.loc[
        window["contrast_family"].eq("theta_minus_theta_0_within_gamma") & window["gamma"].eq(0.0)
    ]
    return {
        "cells": int(len(negative)),
        "maximum_absolute_expected_objective_difference": float(
            negative["expected_objective_difference"].abs().max()
        ),
        "maximum_absolute_realized_payoff_bound_dollars": float(
            negative[["realized_payoff_difference_lower", "realized_payoff_difference_upper"]]
            .abs()
            .to_numpy()
            .max(initial=0.0)
        ),
        "maximum_absolute_weighted_default_bound": float(
            negative[["weighted_default_difference_lower", "weighted_default_difference_upper"]]
            .abs()
            .to_numpy()
            .max(initial=0.0)
        ),
        "maximum_absolute_weighted_miscoverage_bound": float(
            negative[
                [
                    "weighted_miscoverage_difference_lower",
                    "weighted_miscoverage_difference_upper",
                ]
            ]
            .abs()
            .to_numpy()
            .max(initial=0.0)
        ),
    }


def _direction_counts(directions: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    return (
        directions.groupby(["metric", column], observed=True)
        .size()
        .rename("cells")
        .reset_index()
        .sort_values(["metric", column], kind="mergesort")
        .to_dict(orient="records")
    )


def _phase_b_summary(
    *,
    config: Mapping[str, Any],
    source_authority: Mapping[str, Any],
    evaluated: pd.DataFrame,
    joined: pd.DataFrame,
    monthly: pd.DataFrame,
    window: pd.DataFrame,
    directions: pd.DataFrame,
    outcome_audit: pd.DataFrame,
    protected_descriptor: Mapping[str, Any],
) -> dict[str, Any]:
    transport = config["git_transport"]
    periods = int(config["frontier"]["expected_primary_months"])
    budget = float(config["normalization"]["committed_budget_per_period"])
    return {
        "schema_version": str(config["schema_version"]),
        "status": EVALUATION_STATUS,
        "artifact_status": PENDING_ARTIFACT_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": source_authority["protocol"]["commit"],
        "source_artifact_tag": str(transport["source_artifact_tag"]),
        "source_artifact_commit": source_authority["source"]["commit"],
        "expected_evaluation_artifact_tag": str(transport["evaluation_artifact_tag"]),
        "classification": "retrospective_post_inspection_recovery",
        "replay_clean": False,
        "confirmatory": False,
        "v1a_is_evidence": False,
        "phase_a_rerun": False,
        "counts": {
            "evaluated_primary_portfolios": int(len(evaluated)),
            "joined_primary_funded_rows_in_memory": int(len(joined)),
            "monthly_sharp_contrasts": int(len(monthly)),
            "window_sharp_contrasts": int(len(window)),
            "metric_direction_rows": int(len(directions)),
            "outcome_audit_rows": int(len(outcome_audit)),
        },
        "normalization": {
            "committed_budget_B_dollars": budget,
            "primary_periods_T": periods,
            "pooled_capital_TB_dollars": periods * budget,
            "common_across_policies": True,
            "solver_capital_renormalization": False,
        },
        "negative_control": _negative_control_summary(window),
        "direction_counts": _direction_counts(directions, "direction_at_tolerance"),
        "geometric_direction_counts": _direction_counts(directions, "geometric_direction"),
        "unresolved_primary_candidates": int(outcome_audit["unresolved_rows"].sum()),
        "joined_row_level_table_persisted": False,
        "selection": {
            "theta": None,
            "gamma": None,
            "ruler": None,
            "coordinate": None,
            "window": None,
            "policy": None,
        },
        "policy_winner": None,
        "p_values_computed": False,
        "causal_interpretation": False,
        "conformal_guarantee_repair": False,
        "protected_stages_run": [],
        "protected_source_root_binding": "explicit_distinct_hash_bound_source_root",
        "protected_source_root_distinct_from_execution_checkout": True,
        "protected_artifacts_read": [dict(protected_descriptor)],
        "protected_artifacts_written": [],
    }


def _source_snapshot(authority: Mapping[str, Any], *, root: Path) -> dict[str, Any]:
    return {
        "protocol": dict(authority["protocol"]),
        "source": dict(authority["source"]),
        "original_v1a": dict(authority["original_v1a"]),
        "git_commit": authority["git"]["commit"],
        "source_files": {
            key: _relative_descriptor(path, root=root)
            for key, path in sorted(authority["paths"].items())
        },
        "implementation": dict(authority["implementation"]),
    }


def _require_unchanged_source_snapshot(
    initial: Mapping[str, Any], repeated: Mapping[str, Any]
) -> None:
    if dict(repeated) != dict(initial):
        raise RuntimeError("V1a source authority changed during a V1c TOCTOU window.")


def _require_output_census(
    config: Mapping[str, Any],
    *,
    evaluated: pd.DataFrame,
    joined: pd.DataFrame,
    monthly: pd.DataFrame,
    window: pd.DataFrame,
    directions: pd.DataFrame,
    outcome_audit: pd.DataFrame,
) -> None:
    expected = config["expected_census"]
    observed = {
        "primary_evaluated_portfolios": len(evaluated),
        "joined_primary_funded_rows": len(joined),
        "monthly_sharp_contrasts": len(monthly),
        "window_sharp_contrasts": len(window),
        "direction_rows": len(directions),
        "outcome_audit_rows": len(outcome_audit),
    }
    for key, value in observed.items():
        if int(value) != int(expected[key]):
            raise RuntimeError(f"V1c {key} census is {value}, not {expected[key]}.")


def _resolved_locked_config(config_path: Path, root: Path) -> Path:
    candidate = config_path if config_path.is_absolute() else root / config_path
    resolved = candidate.resolve()
    expected = (root / CONFIG_RELATIVE).resolve()
    if resolved != expected:
        raise RuntimeError("V1c execution accepts only its singular repository config path.")
    return resolved


def run_phase_b(
    *,
    config_path: Path,
    protected_read_root: Path,
    repo_root: Path = ROOT,
) -> Path:
    """Evaluate outcomes once from A; no Phase-A solver path exists in V1c."""
    started = time.perf_counter()
    started_at = utc_now_iso()
    root = repo_root.resolve()
    resolved_config = _resolved_locked_config(config_path, root)
    config = load_v1c_config(resolved_config)
    source_tag = _tag_authority(root, str(config["git_transport"]["source_artifact_tag"]))
    initial = verify_source_authority(
        config,
        repo_root=root,
        required_head=source_tag["commit"],
        require_untracked_clean=True,
    )
    initial_snapshot = _source_snapshot(initial, root=root)
    _preflight_fresh_outputs(config, root=root)
    raw_path, raw_descriptor = _resolve_protected_raw(
        config, protected_read_root=protected_read_root, repo_root=root
    )

    build = _load_and_validate_phase_a(config, initial)
    records = build.solve_records
    allocations = build.allocations
    primary_records = records.loc[records["role"].eq("primary_oot")].copy()
    primary_allocations = allocations.loc[allocations["role"].eq("primary_oot")].copy()
    del build, records, allocations
    if len(primary_records) != int(config["expected_census"]["primary_evaluated_portfolios"]):
        raise RuntimeError("Frozen primary portfolio census changed before outcome evaluation.")

    outcome_config_path = _resolve_repo_path(root, str(config["outcomes"]["parent_config"]))
    outcome_config = load_v4_config(outcome_config_path)
    decision_contract = initial["freeze"]["decision_contract"]
    if (
        str(config["outcomes"]["endpoint"]) != str(outcome_config["design"]["endpoint"])
        or float(decision_contract["budget"])
        != float(config["normalization"]["committed_budget_per_period"])
        or float(decision_contract["lgd"]) != float(outcome_config["payoff"]["lgd"])
    ):
        raise RuntimeError("V1a decision contract and V1c endpoint/budget/LGD diverged.")
    universe = load_outcome_universe(outcome_config, raw_path=raw_path)
    all_outcomes = configured_archive_outcomes(universe, outcome_config)
    endpoint_audit = _validate_endpoint_values(all_outcomes, label="Configured archive")
    candidate_outcomes = all_outcomes.loc[
        all_outcomes["role"].isin(decision_contract["roles"])
    ].copy()
    if _candidate_identity_contract(candidate_outcomes) != decision_contract["candidate_identity"]:
        raise RuntimeError("Phase-B candidate identity differs from the V1a frozen universe.")
    outcomes = all_outcomes.loc[all_outcomes["role"].eq("primary_oot")].copy()
    evaluated, joined = evaluate_frozen_portfolios(
        primary_records,
        primary_allocations,
        outcomes,
        config=outcome_config,
    )
    joined_endpoint_audit = _validate_endpoint_values(joined, label="Joined funded allocation")
    if not bool(evaluated["full_budget"].all()):
        raise RuntimeError("At least one evaluated primary portfolio failed full-budget status.")
    outcome_audit = primary_outcome_audit(outcomes, primary_allocations)
    monthly, window, directions = build_v1c_sharp_embedding_contrasts(
        joined,
        config=config,
        lgd=float(outcome_config["payoff"]["lgd"]),
        budget=float(config["normalization"]["committed_budget_per_period"]),
    )
    _require_output_census(
        config,
        evaluated=evaluated,
        joined=joined,
        monthly=monthly,
        window=window,
        directions=directions,
        outcome_audit=outcome_audit,
    )
    join_identity = {
        "schema_version": str(config["schema_version"]),
        "status": EVALUATION_STATUS,
        "artifact_status": PENDING_ARTIFACT_STATUS,
        "run_tag": str(config["run_tag"]),
        "joined_table": _dataframe_content_identity(joined),
        "source_allocation": dict(config["source_v1a_artifacts"]["allocations"]),
        "outcome_source": dict(raw_descriptor),
        "primary_candidate_identity": _candidate_identity_contract(outcomes),
        "endpoint_value_audit": endpoint_audit,
        "joined_endpoint_value_audit": joined_endpoint_audit,
        "joined_row_level_table_persisted": False,
        "protected_source_root_binding": "explicit_distinct_hash_bound_source_root",
        "protected_source_root_distinct_from_execution_checkout": True,
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }

    repeated = verify_source_authority(
        config,
        repo_root=root,
        required_head=initial["source"]["commit"],
        require_untracked_clean=True,
    )
    _require_unchanged_source_snapshot(initial_snapshot, _source_snapshot(repeated, root=root))
    if _file_descriptor(raw_path, logical_path=raw_descriptor["path"]) != raw_descriptor:
        raise RuntimeError("Protected raw archive changed during Phase-B calculation.")

    summary = _phase_b_summary(
        config=config,
        source_authority=initial,
        evaluated=evaluated,
        joined=joined,
        monthly=monthly,
        window=window,
        directions=directions,
        outcome_audit=outcome_audit,
        protected_descriptor=raw_descriptor,
    )
    data_dir, model_dir, evaluation_dir = _output_directories(config, root)
    evaluation_dir.mkdir(parents=True, exist_ok=False)
    model_dir.mkdir(parents=True, exist_ok=False)
    output = config["output"]
    frames = {
        "evaluated_portfolios": evaluated,
        "monthly_sharp_contrasts": monthly,
        "window_sharp_contrasts": window,
        "metric_direction_census": directions,
        "outcome_join_audit": outcome_audit,
    }
    written: dict[str, Path] = {
        key: atomic_write_parquet(frame, evaluation_dir / str(output[key]))
        for key, frame in frames.items()
    }
    written["join_identity"] = atomic_write_json(
        model_dir / str(output["join_identity"]), join_identity
    )
    written["evaluation_summary"] = atomic_write_json(
        model_dir / str(output["evaluation_summary"]), summary
    )
    receipt = {
        "schema_version": str(config["schema_version"]),
        "status": EVALUATION_STATUS,
        "artifact_status": PENDING_ARTIFACT_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": initial["protocol"]["commit"],
        "source_artifact_tag": initial["source"]["tag"],
        "source_artifact_commit": initial["source"]["commit"],
        "started_at_utc": started_at,
        "completed_at_utc": utc_now_iso(),
        "elapsed_seconds": float(time.perf_counter() - started),
        "classification": "retrospective_post_inspection_recovery",
        "phase_a_rerun": False,
        "source_files_verified": len(SOURCE_KEYS),
        "protected_source_root_binding": "explicit_distinct_hash_bound_source_root",
        "protected_source_root_distinct_from_execution_checkout": True,
        "protected_stages_run": [],
        "protected_artifacts_read": [dict(raw_descriptor)],
        "protected_artifacts_written": [],
    }
    written["evaluation_receipt"] = atomic_write_json(
        model_dir / str(output["evaluation_receipt"]), receipt
    )

    after_write = verify_source_authority(
        config,
        repo_root=root,
        required_head=initial["source"]["commit"],
        require_untracked_clean=False,
    )
    _require_unchanged_source_snapshot(initial_snapshot, _source_snapshot(after_write, root=root))
    if _file_descriptor(raw_path, logical_path=raw_descriptor["path"]) != raw_descriptor:
        raise RuntimeError("Protected raw archive changed before the Phase-B seal.")
    artifact_descriptors = {
        key: _relative_descriptor(path, root=root) for key, path in sorted(written.items())
    }
    expected_nonmanifest_paths = set(config["git_transport"]["source_to_evaluation_paths"]) - {
        f"{output['model_root']}/{config['run_tag']}/{output['evaluation_manifest']}"
    }
    if {item["path"] for item in artifact_descriptors.values()} != expected_nonmanifest_paths:
        raise RuntimeError("Written V1c files differ from the locked compact output paths.")
    manifest = {
        "schema_version": str(config["schema_version"]),
        "status": EVALUATION_STATUS,
        "artifact_status": PENDING_ARTIFACT_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol": dict(initial["protocol"]),
        "source_artifact": dict(initial["source"]),
        "original_v1a": dict(initial["original_v1a"]),
        "source_v1a_artifacts": {
            key: dict(config["source_v1a_artifacts"][key]) for key in SOURCE_KEYS
        },
        "outcome_source": {
            "config": _relative_descriptor(outcome_config_path, root=root),
            "protected_artifact": dict(raw_descriptor),
            "columns_joined_after_freeze": list(config["outcomes"]["joined_columns"]),
        },
        "schemas": {key: dataframe_schema(frame) for key, frame in frames.items()},
        "evaluation_artifacts": artifact_descriptors,
        "artifact_contract": {
            "expected_tag": str(config["git_transport"]["evaluation_artifact_tag"]),
            "expected_parent": initial["source"]["commit"],
            "exact_added_paths": list(config["git_transport"]["source_to_evaluation_paths"]),
            "direct_child": True,
            "annotated_tag": True,
            "dvc_required": False,
        },
        "implementation": dict(initial["implementation"]),
        "environment": _portable_environment(root),
        "classification": "retrospective_post_inspection_recovery",
        "replay_clean": False,
        "confirmatory": False,
        "v1a_is_evidence": False,
        "selection": summary["selection"],
        "policy_winner": None,
        "p_values_computed": False,
        "protected_source_root_binding": "explicit_distinct_hash_bound_source_root",
        "protected_source_root_distinct_from_execution_checkout": True,
        "protected_stages_run": [],
        "protected_artifacts_read": [dict(raw_descriptor)],
        "protected_artifacts_written": [],
    }
    manifest_path = atomic_write_json(model_dir / str(output["evaluation_manifest"]), manifest)
    final = verify_source_authority(
        config,
        repo_root=root,
        required_head=initial["source"]["commit"],
        require_untracked_clean=False,
    )
    _require_unchanged_source_snapshot(initial_snapshot, _source_snapshot(final, root=root))
    if _file_descriptor(raw_path, logical_path=raw_descriptor["path"]) != raw_descriptor:
        raise RuntimeError("Protected raw archive changed after the Phase-B seal.")
    all_written = {*written.values(), manifest_path}
    observed_paths = {path.resolve().relative_to(root).as_posix() for path in all_written}
    if observed_paths != set(config["git_transport"]["source_to_evaluation_paths"]):
        raise RuntimeError("Final V1c output census differs from the locked nine paths.")
    logger.info(
        "V1c evaluated {} primary policies and {} pooled contrasts in {:.1f}s",
        len(evaluated),
        len(window),
        time.perf_counter() - started,
    )
    return manifest_path


def _reject_absolute_serialized_paths(value: Any, *, location: str = "root") -> None:
    """Ensure receipts never leak host-specific filesystem bindings."""
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_absolute_serialized_paths(item, location=f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_absolute_serialized_paths(item, location=f"{location}[{index}]")
    elif isinstance(value, str) and (
        value.startswith(("/", "\\")) or PureWindowsPath(value).is_absolute()
    ):
        raise RuntimeError(f"Serialized payload leaks an absolute path at {location}.")


def verify_evaluation_artifact_commit(
    *, config_path: Path, repo_root: Path = ROOT
) -> dict[str, Any]:
    """Read-only verification of the final A -> B commit and annotated artifact tag."""
    root = repo_root.resolve()
    resolved_config = _resolved_locked_config(config_path, root)
    config = load_v1c_config(resolved_config)
    transport = config["git_transport"]
    evaluation = _tag_authority(root, str(transport["evaluation_artifact_tag"]))
    if _head_commit(root) != evaluation["commit"]:
        raise RuntimeError("Evaluation artifact tag B must resolve exactly to current HEAD.")
    state = _git_state(root, include_untracked=True)
    if state["dirty"]:
        raise RuntimeError(f"Artifact verification requires a fully clean B worktree: {state}.")
    source = _tag_authority(root, str(transport["source_artifact_tag"]))
    expected_paths = tuple(str(item) for item in transport["source_to_evaluation_paths"])
    _require_exact_addition_commit(
        root,
        child=evaluation["commit"],
        parent=source["commit"],
        expected_paths=expected_paths,
    )
    source_authority = verify_source_authority(
        config,
        repo_root=root,
        required_head=evaluation["commit"],
        require_untracked_clean=True,
    )
    output = config["output"]
    _, model_dir, _ = _output_directories(config, root)
    manifest_path = model_dir / str(output["evaluation_manifest"])
    summary_path = model_dir / str(output["evaluation_summary"])
    receipt_path = model_dir / str(output["evaluation_receipt"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    for label, payload in (("manifest", manifest), ("summary", summary), ("receipt", receipt)):
        if (
            payload.get("schema_version") != config["schema_version"]
            or payload.get("status") != EVALUATION_STATUS
            or payload.get("artifact_status") != PENDING_ARTIFACT_STATUS
            or payload.get("run_tag") != config["run_tag"]
        ):
            raise RuntimeError(f"V1c {label} identity or pending-at-exit status changed.")
        _reject_absolute_serialized_paths(payload, location=label)
    if (
        manifest.get("protocol") != source_authority["protocol"]
        or manifest.get("source_artifact") != source_authority["source"]
    ):
        raise RuntimeError("V1c manifest P/A authority differs from the verified tag chain.")
    expected_contract = {
        "expected_tag": str(transport["evaluation_artifact_tag"]),
        "expected_parent": source["commit"],
        "exact_added_paths": list(expected_paths),
        "direct_child": True,
        "annotated_tag": True,
        "dvc_required": False,
    }
    if manifest.get("artifact_contract") != expected_contract:
        raise RuntimeError("V1c manifest artifact contract changed.")
    expected_artifact_keys = {
        *DATA_OUTPUT_KEYS,
        "join_identity",
        "evaluation_summary",
        "evaluation_receipt",
    }
    recorded = manifest.get("evaluation_artifacts")
    if not isinstance(recorded, dict) or set(recorded) != expected_artifact_keys:
        raise RuntimeError("V1c manifest has an incomplete nonmanifest artifact census.")
    for key, descriptor_value in recorded.items():
        descriptor = _validated_descriptor(descriptor_value, label=f"evaluation_artifacts.{key}")
        path = _resolve_repo_path(root, descriptor["path"])
        if _file_descriptor(path, logical_path=descriptor["path"]) != descriptor:
            raise RuntimeError(f"V1c worktree artifact descriptor mismatch for {key}.")
        if _blob_descriptor(root, evaluation["commit"], descriptor["path"]) != descriptor:
            raise RuntimeError(f"V1c Git-blob artifact descriptor mismatch for {key}.")
    manifest_descriptor = _relative_descriptor(manifest_path, root=root)
    if (
        _blob_descriptor(root, evaluation["commit"], manifest_descriptor["path"])
        != manifest_descriptor
    ):
        raise RuntimeError("V1c manifest Git blob differs from its worktree bytes.")
    all_recorded_paths = {descriptor["path"] for descriptor in recorded.values()} | {
        manifest_descriptor["path"]
    }
    if all_recorded_paths != set(expected_paths):
        raise RuntimeError("V1c manifest paths do not equal the exact A-to-B diff.")
    if manifest.get("source_v1a_artifacts") != {
        key: config["source_v1a_artifacts"][key] for key in SOURCE_KEYS
    }:
        raise RuntimeError("V1c manifest changed a source V1a descriptor.")
    return {
        "status": "verified_git_native_evaluation_artifact_commit",
        "protocol": source_authority["protocol"],
        "source": source_authority["source"],
        "evaluation": evaluation,
        "added_paths": list(expected_paths),
        "dvc_required": False,
    }


def main(argv: Sequence[str] | None = None) -> None:
    """Run Phase B at A or verify the eventual artifact commit B."""
    args = parse_args(argv)
    if args.verify_artifact_commit:
        result = verify_evaluation_artifact_commit(config_path=args.config, repo_root=ROOT)
        logger.info("Verified {}", result["evaluation"]["commit"])
    else:
        path = run_phase_b(
            config_path=args.config,
            protected_read_root=args.protected_read_root,
            repo_root=ROOT,
        )
        logger.info("Wrote {}", path)


if __name__ == "__main__":
    main()
