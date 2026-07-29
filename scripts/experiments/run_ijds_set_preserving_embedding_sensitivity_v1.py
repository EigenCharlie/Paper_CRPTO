"""Run the locked two-phase IJDS set-preserving embedding sensitivity V1a/V1b."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

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
    verified_freeze_artifact_paths,
)
from src.ijds_challengers.archive import (  # noqa: E402
    load_outcome_free_decision_base,
    verified_parent_artifacts,
)
from src.ijds_challengers.set_preserving_embedding import (  # noqa: E402
    SetPreservingFrontierBuild,
    build_set_preserving_frontiers,
    build_sharp_embedding_contrasts,
    load_set_preserving_config,
    primary_outcome_audit,
    validate_complete_frontier,
)
from src.utils.isolated_experiment import (  # noqa: E402
    OutputPaths,
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    package_version,
    prepare_output_paths as prepare_isolated_output_paths,
    relative_artifact_descriptor,
    resolve_isolated_run_dir,
    resolve_repo_input,
    sha256_file,
)
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    atomic_write_text,
    utc_now_iso,
)

DEFAULT_CONFIG_PATH = (
    ROOT / "configs/experiments/ijds_set_preserving_embedding_sensitivity_2026-07-29_v1a.yaml"
)
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
FREEZE_STATUS = "outcome_free_set_preserving_allocations_frozen_before_outcomes"
EVALUATION_STATUS = "verified_set_preserving_embedding_evaluation_complete"
TRANSPORT_STATUS = "verified_clean_clone_phase_a_dvc_transport"
PHASE_B_TRANSPORT_STATUS = "verified_clean_clone_phase_b_dvc_transport"
TRANSPORT_SCHEMA_VERSION = "2026-07-29.2"
LOCKED_DVC_VERSION = "3.67.1"
TRANSPORT_RECEIPT_PATH = Path(
    "reports/crpto/"
    "ijds_set_preserving_embedding_sensitivity_2026-07-29_v1a_"
    "clean_clone_transport_receipt.json"
)
RUNNER_PATH = Path("scripts/experiments/run_ijds_set_preserving_embedding_sensitivity_v1.py")
UV_LOCK_PATH = Path("uv.lock")
PHASE_A_ARTIFACT_KEYS = {
    "solve_records",
    "allocations",
    "embedding_diagnostics",
    "minimum_endpoint_diagnostics",
    "objective_optimum_diagnostics",
    "allocation_contrasts",
    "order_sensitivity",
    "independent_validation",
}
PHASE_B_ARTIFACT_KEYS = {
    "evaluated_portfolios",
    "joined_funded_allocations",
    "monthly_sharp_contrasts",
    "window_sharp_contrasts",
    "metric_direction_census",
    "outcome_join_audit",
}
TRANSITIVE_PYTHON_PATHS = (
    Path("scripts/__init__.py"),
    Path("scripts/experiments/run_ijds_set_preserving_embedding_sensitivity_v1.py"),
    Path("src/__init__.py"),
    Path("src/data/__init__.py"),
    Path("src/data/outcome_observability.py"),
    Path("src/evaluation/__init__.py"),
    Path("src/evaluation/coverage_transport.py"),
    Path("src/evaluation/maturity_safe_portfolio.py"),
    Path("src/evaluation/policy_contrast_bounds.py"),
    Path("src/evaluation/standardized_credit_payoff.py"),
    Path("src/features/__init__.py"),
    Path("src/features/feature_engineering.py"),
    Path("src/ijds_audit/__init__.py"),
    Path("src/ijds_audit/allocations.py"),
    Path("src/ijds_audit/config.py"),
    Path("src/ijds_audit/endpoint_recovery.py"),
    Path("src/ijds_audit/evaluation.py"),
    Path("src/ijds_audit/geometry.py"),
    Path("src/ijds_audit/policy_support.py"),
    Path("src/ijds_audit/portfolio.py"),
    Path("src/ijds_audit/prediction.py"),
    Path("src/ijds_audit/protocol.py"),
    Path("src/ijds_audit/rhs_ranging.py"),
    Path("src/ijds_audit/simulation.py"),
    Path("src/ijds_challengers/__init__.py"),
    Path("src/ijds_challengers/archive.py"),
    Path("src/ijds_challengers/frontier.py"),
    Path("src/ijds_challengers/normalized_frontier.py"),
    Path("src/ijds_challengers/set_preserving_embedding.py"),
    Path("src/models/__init__.py"),
    Path("src/models/binary_conformal_guardrail.py"),
    Path("src/models/maturity_safe_pd.py"),
    Path("src/optimization/__init__.py"),
    Path("src/optimization/policy.py"),
    Path("src/optimization/policy_evaluation.py"),
    Path("src/optimization/policy_selection.py"),
    Path("src/optimization/portfolio_model.py"),
    Path("src/utils/__init__.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
)
IMPLEMENTATION_PATHS = (
    Path("configs/experiments/ijds_fixed_taxonomy_c2_2026-07-11.yaml"),
    Path("configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-12.yaml"),
    Path("configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-12_v2.yaml"),
    Path("configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-14_v3.yaml"),
    Path("configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-15_v4.yaml"),
    Path("configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-15_v5.yaml"),
    Path("docs/research/ijds_set_preserving_embedding_sensitivity_v1_protocol_2026-07-26.md"),
    Path("docs/research/ijds_set_preserving_embedding_sensitivity_v1a_protocol_2026-07-29.md"),
    Path("docs/research/ijds_fixed_taxonomy_c2_protocol_errata_2026-07-12.md"),
    Path("docs/research/ijds_binary_geometry_frontier_v4_protocol_2026-07-12.md"),
    Path("docs/research/ijds_binary_geometry_frontier_v4_v2_recovery_2026-07-12.md"),
    Path("docs/research/ijds_evaluation_endpoint_recovery_v3_protocol_2026-07-14.md"),
    Path("docs/research/ijds_endpoint_reason_taxonomy_v4_protocol_2026-07-15.md"),
    Path("docs/research/ijds_endpoint_reason_recovery_v5_erratum_2026-07-15.md"),
    Path("docs/research/ijds_normalized_objective_frontier_protocol_2026-07-12.md"),
    Path("docs/research/ijds_normalized_objective_frontier_v1c_protocol_2026-07-13.md"),
    Path("docs/research/ijds_two_ruler_endpoint_recovery_v3_protocol_2026-07-14.md"),
    *TRANSITIVE_PYTHON_PATHS,
    # Retained as an authority helper even though this runner imports the
    # equivalent isolated-experiment implementation directly.
    Path("src/utils/artifact_descriptor.py"),
    Path("tests/test_ijds_set_preserving_embedding_sensitivity.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse one explicit phase; evaluation can never occur implicitly."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument(
        "--phase",
        choices=(
            "outcome-free",
            "verify-phase-a-transport",
            "evaluate",
            "verify-phase-b-transport",
        ),
        required=True,
    )
    parser.add_argument("--artifact-tag")
    args = parser.parse_args(argv)
    transport_phases = {"verify-phase-a-transport", "verify-phase-b-transport"}
    if args.phase in transport_phases and not args.artifact_tag:
        parser.error("--artifact-tag is required for clean-clone transport verification")
    if args.phase not in transport_phases and args.artifact_tag:
        parser.error("--artifact-tag is valid only for clean-clone transport verification")
    return args


def _output_paths(config: Mapping[str, Any], *, repo_root: Path) -> OutputPaths:
    output = config["output"]
    run_tag = str(config["run_tag"])
    return OutputPaths(
        data_dir=resolve_isolated_run_dir(
            repo_root=repo_root,
            configured_root=str(output["data_root"]),
            allowed_relative_root=ALLOWED_DATA_ROOT,
            run_tag=run_tag,
        ),
        model_dir=resolve_isolated_run_dir(
            repo_root=repo_root,
            configured_root=str(output["model_root"]),
            allowed_relative_root=ALLOWED_MODEL_ROOT,
            run_tag=run_tag,
        ),
    )


def preflight_fresh_run(config: Mapping[str, Any], *, repo_root: Path) -> OutputPaths:
    """Reject occupied run directories before any expensive Phase-A read or solve."""
    paths = _output_paths(config, repo_root=repo_root)
    occupied = [path for path in (paths.data_dir, paths.model_dir) if path.exists()]
    if occupied:
        raise FileExistsError(
            "Set-preserving run tag is occupied; choose a fresh tag: "
            + ", ".join(str(path) for path in occupied)
        )
    return paths


def prepare_output_paths(config: Mapping[str, Any], *, repo_root: Path) -> OutputPaths:
    """Create fresh directories only inside the two isolated IJDS experiment roots."""
    return prepare_isolated_output_paths(
        dict(config),
        repo_root=repo_root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )


def _implementation(config_path: Path, root: Path) -> dict[str, Any]:
    return implementation_provenance(
        config_path=config_path,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )


def _environment(root: Path) -> dict[str, Any]:
    environment = environment_provenance(root)
    executable = Path(str(environment.pop("executable"))).read_bytes()
    environment["executable"] = {
        "binding": "sys.executable",
        **_bytes_descriptor(executable),
    }
    environment["packages"]["ortools"] = package_version("ortools")
    environment["packages"]["PyYAML"] = package_version("PyYAML")
    environment["packages"]["loguru"] = package_version("loguru")
    return environment


def _authority_snapshot(config_path: Path, root: Path) -> dict[str, Any]:
    """Capture implementation, environment, and git authority for one run."""
    return {
        "implementation": _implementation(config_path, root),
        "environment": _environment(root),
        "git": git_provenance(root),
    }


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Serialize the transport receipt in its one accepted byte representation."""
    return (
        json.dumps(
            dict(payload),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_canonical_json(path: Path, payload: Mapping[str, Any]) -> Path:
    """Write canonical UTF-8, compact, sorted JSON with exactly one LF."""
    content = _canonical_json_bytes(payload)
    return atomic_write_text(path, content.decode("utf-8"), encoding="utf-8")


def _bytes_descriptor(payload: bytes) -> dict[str, Any]:
    return {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _git_blob_descriptor(*, commit: str, relative_path: Path, root: Path) -> dict[str, Any]:
    payload = _git_blob_bytes(
        commit=commit,
        relative_path=relative_path.as_posix(),
        root=root,
        label=relative_path.as_posix(),
    )
    return {"path": relative_path.as_posix(), **_bytes_descriptor(payload)}


def _tag_authority(root: Path, tag: str) -> dict[str, str]:
    """Return an annotated tag object's identity and its peeled commit."""
    value = str(tag)
    reference = f"refs/tags/{value}"
    valid = subprocess.run(
        ["git", "check-ref-format", reference],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if valid.returncode != 0 or value.startswith(("-", "refs/")):
        raise RuntimeError(f"Protocol tag is not a valid explicit tag name: {tag!r}.")
    object_type = subprocess.run(
        ["git", "cat-file", "-t", reference],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    object_id_result = subprocess.run(
        ["git", "rev-parse", "--verify", "--end-of-options", reference],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    peeled_result = subprocess.run(
        ["git", "rev-parse", "--verify", "--end-of-options", f"{reference}^{{commit}}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    object_id = object_id_result.stdout.strip()
    peeled = peeled_result.stdout.strip()
    if (
        object_type.returncode != 0
        or object_type.stdout.strip() != "tag"
        or object_id_result.returncode != 0
        or peeled_result.returncode != 0
        or len(object_id) != 40
        or len(peeled) != 40
    ):
        raise RuntimeError(f"Required authority tag must be annotated: {tag!r}.")
    try:
        int(object_id, 16)
        int(peeled, 16)
    except ValueError as error:
        raise RuntimeError(
            f"Required authority tag has an invalid object identity: {tag!r}."
        ) from error
    return {
        "name": value,
        "ref": reference,
        "object_type": "tag",
        "object_id": object_id,
        "peeled_commit": peeled,
    }


def _tracked_git_state(root: Path) -> dict[str, Any]:
    """Capture deterministic tracked state without absolute paths or branch names."""
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=False,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=no"],
        cwd=root,
        check=True,
        capture_output=True,
        text=False,
    ).stdout
    decoded_head = head.decode("ascii")
    entries = [line for line in status.splitlines() if line]
    return {
        "head": decoded_head,
        "tracked_clean": not entries,
        "tracked_entries": len(entries),
        "porcelain": _bytes_descriptor(status),
    }


def _dvc_record_descriptor() -> dict[str, Any]:
    """Verify and hash the installed DVC wheel RECORD without exposing local paths."""
    distribution = importlib.metadata.distribution("dvc")
    candidates = [
        item
        for item in (distribution.files or ())
        if item.name == "RECORD" and item.parent.name.endswith(".dist-info")
    ]
    if len(candidates) != 1:
        raise RuntimeError("The installed DVC distribution has no unique RECORD authority.")
    record = Path(str(distribution.locate_file(candidates[0]))).resolve()
    payload = record.read_bytes()
    try:
        rows = list(csv.reader(payload.decode("utf-8").splitlines()))
    except (UnicodeDecodeError, csv.Error) as error:
        raise RuntimeError("The installed DVC RECORD is not valid UTF-8 CSV.") from error
    verified = 0
    unhashed: list[str] = []
    for row in rows:
        if len(row) != 3:
            raise RuntimeError("The installed DVC RECORD has an invalid row schema.")
        relative_path, encoded_digest, encoded_size = row
        installed = Path(str(distribution.locate_file(relative_path))).resolve()
        if not encoded_digest:
            unhashed.append(relative_path)
            continue
        algorithm, separator, expected_digest = encoded_digest.partition("=")
        if not separator or not expected_digest or not installed.is_file():
            raise RuntimeError("An installed DVC RECORD entry is missing or malformed.")
        installed_payload = installed.read_bytes()
        try:
            observed_digest = (
                base64.urlsafe_b64encode(hashlib.new(algorithm, installed_payload).digest())
                .rstrip(b"=")
                .decode("ascii")
            )
            expected_size = int(encoded_size)
        except (ValueError, TypeError) as error:
            raise RuntimeError("An installed DVC RECORD digest or size is invalid.") from error
        if observed_digest != expected_digest or len(installed_payload) != expected_size:
            raise RuntimeError("An installed DVC file disagrees with its wheel RECORD.")
        verified += 1
    if unhashed != [candidates[0].as_posix()] or verified <= 0:
        raise RuntimeError("The installed DVC wheel has an unexpected unhashed RECORD census.")
    return {
        "distribution_relative_path": candidates[0].as_posix(),
        "record_rows": len(rows),
        "verified_hashed_files": verified,
        "unhashed_files": unhashed,
        **_bytes_descriptor(payload),
    }


def _transport_runtime_contract() -> dict[str, Any]:
    """Bind transport to one Python runtime and the locked DVC wheel."""
    dvc_version = importlib.metadata.version("dvc")
    if dvc_version != LOCKED_DVC_VERSION:
        raise RuntimeError(
            f"Clean-clone transport requires dvc=={LOCKED_DVC_VERSION}, observed {dvc_version}."
        )
    return {
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "full_version": sys.version,
            "cache_tag": str(sys.implementation.cache_tag),
            "executable": _bytes_descriptor(Path(sys.executable).read_bytes()),
        },
        "dvc": {
            "distribution": "dvc",
            "version": dvc_version,
            "record": _dvc_record_descriptor(),
        },
    }


def _subprocess_transcript(
    *, argv: Sequence[str], result: subprocess.CompletedProcess[bytes]
) -> dict[str, Any]:
    """Describe the observed subprocess result without embedding volatile output text."""
    stdout = bytes(result.stdout or b"")
    stderr = bytes(result.stderr or b"")
    logical_argv = [str(value) for value in argv]
    if logical_argv and logical_argv[0] == sys.executable:
        logical_argv[0] = "{sys.executable}"
    body = {
        "argv": logical_argv,
        "cwd": ".",
        "shell": False,
        "returncode": int(result.returncode),
        "stdout": _bytes_descriptor(stdout),
        "stderr": _bytes_descriptor(stderr),
    }
    return {
        **body,
        "transcript_sha256": hashlib.sha256(_canonical_json_bytes(body)).hexdigest(),
    }


def _dvc_argv(*arguments: str) -> list[str]:
    """Build an isolated DVC module invocation bound to ``sys.executable``.

    ``-I`` removes the working directory and user site from Python's import
    search path.  A clean tracked worktree alone cannot exclude an ignored or
    untracked ``dvc.py``/``dvc`` package, so transport must not permit local
    module shadowing of the hash-bound installed distribution.
    """
    return [sys.executable, "-I", "-m", "dvc", *arguments]


def _verify_transcript(record: Mapping[str, Any], *, expected_argv: Sequence[str]) -> None:
    """Fail closed unless one receipt transcript is internally canonical and successful."""
    expected_keys = {
        "argv",
        "cwd",
        "shell",
        "returncode",
        "stdout",
        "stderr",
        "transcript_sha256",
    }
    if set(record) != expected_keys:
        raise RuntimeError("A transport subprocess transcript has an unexpected schema.")
    body = {key: record[key] for key in expected_keys - {"transcript_sha256"}}
    expected_hash = hashlib.sha256(_canonical_json_bytes(body)).hexdigest()
    descriptors_valid = all(
        isinstance(record[name], dict)
        and set(record[name]) == {"bytes", "sha256"}
        and isinstance(record[name]["bytes"], int)
        and not isinstance(record[name]["bytes"], bool)
        and int(record[name]["bytes"]) >= 0
        and isinstance(record[name]["sha256"], str)
        and len(record[name]["sha256"]) == 64
        for name in ("stdout", "stderr")
    )
    try:
        for name in ("stdout", "stderr"):
            int(str(record[name]["sha256"]), 16)
        int(str(record["transcript_sha256"]), 16)
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("A transport subprocess transcript has a non-hex digest.") from error
    logical_argv = [str(value) for value in expected_argv]
    if logical_argv and logical_argv[0] == sys.executable:
        logical_argv[0] = "{sys.executable}"
    if (
        list(record["argv"]) != logical_argv
        or record["cwd"] != "."
        or record["shell"] is not False
        or not isinstance(record["returncode"], int)
        or isinstance(record["returncode"], bool)
        or record["returncode"] != 0
        or not descriptors_valid
        or len(str(record["transcript_sha256"])) != 64
        or record["transcript_sha256"] != expected_hash
    ):
        raise RuntimeError("A transport subprocess transcript does not reconcile exactly.")


def _status_payload_is_clean(payload: Any) -> bool:
    if payload in ({}, []):
        return True
    if isinstance(payload, dict):
        return all(value in ({}, [], None) for value in payload.values())
    return False


def _resolve_strict_tag(root: Path, tag: str) -> str:
    """Resolve only an annotated refs/tags object, never a revision expression."""
    return _tag_authority(root, tag)["peeled_commit"]


def _require_clean_strict_tagged_head(root: Path, tag: str) -> str:
    """Require a clean HEAD equal to one explicit tag ref."""
    state = git_provenance(root)
    commit = state.get("commit")
    if not isinstance(commit, str) or not commit:
        raise RuntimeError("A readable Git HEAD is required before experiment execution.")
    if state.get("dirty") is not False:
        raise RuntimeError("Experiment execution requires a clean predeclared worktree.")
    if _resolve_strict_tag(root, tag) != commit:
        raise RuntimeError(f"Protocol tag {tag!r} does not resolve exactly to clean HEAD.")
    return commit


def _require_unchanged_authority(
    *,
    config: Mapping[str, Any],
    config_path: Path,
    protocol_commit: str,
    initial: Mapping[str, Any],
    root: Path,
) -> None:
    """Reject code, environment, branch, or worktree drift during a long run."""
    observed_commit = _require_clean_strict_tagged_head(root, str(config["protocol_tag"]))
    if observed_commit != protocol_commit:
        raise RuntimeError("Protocol commit changed during experiment execution.")
    if _authority_snapshot(config_path, root) != dict(initial):
        raise RuntimeError("Implementation, environment, or git authority drifted during the run.")


def _verified_descriptor_path(
    descriptor: Mapping[str, Any],
    *,
    label: str,
    root: Path,
) -> Path:
    """Resolve and verify one exact repository-local descriptor."""
    path = resolve_repo_input(str(descriptor["path"]), repo_root=root)
    actual = relative_artifact_descriptor(path, repo_root=root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor[field]:
            raise RuntimeError(f"{label} descriptor mismatch for {field}.")
    return path


def _git_blob_bytes(*, commit: str, relative_path: str, root: Path, label: str) -> bytes:
    """Read one exact Git blob from a hexadecimal commit authority."""
    if len(commit) != 40:
        raise RuntimeError(f"{label} commit identity is not a full SHA-1.")
    try:
        int(commit, 16)
    except ValueError as error:
        raise RuntimeError(f"{label} commit identity is not hexadecimal.") from error
    blob = subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relative_path}"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if blob.returncode != 0:
        raise RuntimeError(f"{label} is absent from its pinned Git commit.")
    return blob.stdout


def _dvc_pointer_out_contract(
    descriptor: Mapping[str, Any],
    *,
    commit: str,
    run_tag: str,
    expected_nfiles: int,
    label: str,
    root: Path,
) -> dict[str, Any]:
    """Verify one newly committed DVC directory pointer and its exact output census."""
    _verified_descriptor_path(descriptor, label=label, root=root)
    _require_descriptor_at_commit(descriptor, commit=commit, label=label, root=root)
    payload = yaml.safe_load(
        _git_blob_bytes(
            commit=commit,
            relative_path=str(descriptor["path"]),
            root=root,
            label=label,
        )
    )
    if not isinstance(payload, dict) or set(payload) != {"outs"}:
        raise RuntimeError(f"{label} must contain exactly one outs census.")
    outs = payload["outs"]
    if not isinstance(outs, list) or len(outs) != 1 or not isinstance(outs[0], dict):
        raise RuntimeError(f"{label} must contain exactly one DVC output.")
    out = outs[0]
    if set(out) != {"md5", "size", "nfiles", "hash", "path"}:
        raise RuntimeError(f"{label} output schema changed.")
    digest = str(out["md5"])
    digest_prefix, separator, suffix = digest.partition(".")
    try:
        int(digest_prefix, 16)
    except ValueError as error:
        raise RuntimeError(f"{label} has a non-hex DVC directory digest.") from error
    if (
        separator != "."
        or suffix != "dir"
        or len(digest_prefix) != 32
        or out["hash"] != "md5"
        or out["path"] != run_tag
        or not isinstance(out["size"], int)
        or isinstance(out["size"], bool)
        or int(out["size"]) <= 0
        or not isinstance(out["nfiles"], int)
        or isinstance(out["nfiles"], bool)
        or int(out["nfiles"]) != expected_nfiles
    ):
        raise RuntimeError(f"{label} output path, digest, or file census changed.")
    return {
        "md5": digest,
        "size": int(out["size"]),
        "nfiles": int(out["nfiles"]),
        "hash": "md5",
        "path": run_tag,
    }


def _phase_a_materialized_paths(
    config: Mapping[str, Any], *, repo_root: Path
) -> tuple[dict[str, Path], dict[str, Path]]:
    """Return the exact eight data and three model files produced by Phase A."""
    run_tag = str(config["run_tag"])
    output = config["output"]
    data_dir = (repo_root / str(output["data_root"]) / run_tag).resolve()
    model_dir = (repo_root / str(output["model_root"]) / run_tag).resolve()
    artifacts = {
        name: (data_dir / "frontier" / str(output[name])).resolve()
        for name in sorted(PHASE_A_ARTIFACT_KEYS)
    }
    metadata = {
        "protocol_freeze": (model_dir / str(output["protocol_freeze"])).resolve(),
        "summary": (model_dir / str(output["outcome_free_summary"])).resolve(),
        "execution_receipt": (model_dir / str(output["outcome_free_receipt"])).resolve(),
    }
    return artifacts, metadata


def _directory_content_descriptor(
    directory: Path, files: Sequence[Path], *, repo_root: Path
) -> dict[str, Any]:
    """Describe one exact tree with SHA-256 identities and DVC 3.67.1 MD5."""
    entries = []
    dvc_entries = []
    total_bytes = 0
    for path in sorted(files, key=lambda item: item.relative_to(directory).as_posix()):
        path.relative_to(repo_root)
        payload = path.read_bytes()
        descriptor = _bytes_descriptor(payload)
        total_bytes += int(descriptor["bytes"])
        relative_path = path.relative_to(directory).as_posix()
        entries.append(
            {
                "relative_path": relative_path,
                "bytes": int(descriptor["bytes"]),
                "sha256": str(descriptor["sha256"]),
            }
        )
        dvc_entries.append(
            {
                "md5": hashlib.md5(payload, usedforsecurity=False).hexdigest(),
                "relpath": relative_path,
            }
        )
    # DVC 3.67.1 Tree.as_bytes serializes its relpath-sorted list with
    # json.dumps(..., sort_keys=True) and default separators before hashing.
    dvc_tree_bytes = json.dumps(dvc_entries, sort_keys=True).encode("utf-8")
    return {
        "nfiles": len(entries),
        "size": total_bytes,
        "dvc_md5": (hashlib.md5(dvc_tree_bytes, usedforsecurity=False).hexdigest() + ".dir"),
        "content_sha256": hashlib.sha256(_canonical_json_bytes({"files": entries})).hexdigest(),
        "files": entries,
    }


def _verified_phase_a_materialization(
    config: Mapping[str, Any],
    *,
    protocol_commit: str,
    repo_root: Path,
    pointer_outs: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Verify the exact 8+3 Phase-A file census and all freeze descriptors."""
    artifacts, metadata = _phase_a_materialized_paths(config, repo_root=repo_root)
    data_dir = next(iter(artifacts.values())).parents[1]
    model_dir = next(iter(metadata.values())).parent
    if not data_dir.is_dir() or not model_dir.is_dir():
        raise RuntimeError("Both DVC Phase-A run directories must be materialized.")
    expected_files = {*artifacts.values(), *metadata.values()}
    observed_files = {
        path.resolve()
        for root in (data_dir, model_dir)
        for path in root.rglob("*")
        if path.is_file()
    }
    if observed_files != expected_files:
        raise RuntimeError(
            "The materialized Phase-A file census is not exactly 8 data + 3 model files."
        )

    freeze = json.loads(metadata["protocol_freeze"].read_text(encoding="utf-8"))
    expected_identity = {
        "status": FREEZE_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
    }
    if any(freeze.get(key) != value for key, value in expected_identity.items()):
        raise RuntimeError("The materialized Phase-A freeze identity changed.")
    if (
        set(freeze.get("outcome_free_artifacts", {})) != PHASE_A_ARTIFACT_KEYS
        or set(freeze.get("schemas", {})) != PHASE_A_ARTIFACT_KEYS
    ):
        raise RuntimeError("The materialized Phase-A freeze omits an artifact or schema.")

    artifact_descriptors = {
        name: relative_artifact_descriptor(path, repo_root=repo_root)
        for name, path in artifacts.items()
    }
    metadata_descriptors = {
        name: relative_artifact_descriptor(path, repo_root=repo_root)
        for name, path in metadata.items()
    }
    if freeze["outcome_free_artifacts"] != artifact_descriptors:
        raise RuntimeError("A materialized Phase-A artifact disagrees with the freeze.")
    if (
        freeze.get("summary") != metadata_descriptors["summary"]
        or freeze.get("execution_receipt") != metadata_descriptors["execution_receipt"]
    ):
        raise RuntimeError("The materialized Phase-A summary or receipt disagrees with the freeze.")
    for label in ("summary", "execution_receipt"):
        payload = json.loads(metadata[label].read_text(encoding="utf-8"))
        if any(payload.get(key) != value for key, value in expected_identity.items()):
            raise RuntimeError(f"The materialized Phase-A {label} identity changed.")
    trees = {
        "data": _directory_content_descriptor(
            data_dir, sorted(artifacts.values()), repo_root=repo_root
        ),
        "model": _directory_content_descriptor(
            model_dir, sorted(metadata.values()), repo_root=repo_root
        ),
    }
    if pointer_outs is not None:
        if set(pointer_outs) != {"data", "model"}:
            raise RuntimeError("Both DVC pointer outputs are required for materialization audit.")
        for key in ("data", "model"):
            if int(pointer_outs[key]["nfiles"]) != int(trees[key]["nfiles"]) or int(
                pointer_outs[key]["size"]
            ) != int(trees[key]["size"]):
                raise RuntimeError(
                    f"The Phase-A {key} DVC out.size/nfiles disagree with real materialization."
                )
            if str(pointer_outs[key]["md5"]) != str(trees[key]["dvc_md5"]):
                raise RuntimeError(
                    f"The Phase-A {key} DVC directory digest disagrees with real content."
                )
    return {
        "census": {
            "phase_a_artifacts": 8,
            "summary": 1,
            "execution_receipt": 1,
            "protocol_freeze": 1,
            "data_files": 8,
            "model_files": 3,
            "total_files": 11,
        },
        "protocol_freeze": metadata_descriptors["protocol_freeze"],
        "summary": metadata_descriptors["summary"],
        "execution_receipt": metadata_descriptors["execution_receipt"],
        "artifacts": artifact_descriptors,
        "trees": trees,
    }


def _phase_b_materialized_paths(
    config: Mapping[str, Any], *, repo_root: Path
) -> tuple[dict[str, Path], dict[str, Path]]:
    """Return the exact six data and three model files produced by Phase B."""
    run_tag = str(config["run_tag"])
    output = config["output"]
    data_dir = (repo_root / str(output["data_root"]) / run_tag).resolve()
    model_dir = (repo_root / str(output["model_root"]) / run_tag).resolve()
    artifacts = {
        name: (data_dir / "evaluation" / str(output[name])).resolve()
        for name in sorted(PHASE_B_ARTIFACT_KEYS)
    }
    metadata = {
        "summary": (model_dir / str(output["evaluation_summary"])).resolve(),
        "execution_receipt": (model_dir / str(output["evaluation_receipt"])).resolve(),
        "manifest": (model_dir / str(output["evaluation_manifest"])).resolve(),
    }
    return artifacts, metadata


def _verified_phase_b_materialization(
    config: Mapping[str, Any],
    *,
    protocol_commit: str,
    repo_root: Path,
    pointer_outs: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Verify the exact 6+3 Phase-B file census and its sealed manifest."""
    artifacts, metadata = _phase_b_materialized_paths(config, repo_root=repo_root)
    data_dir = next(iter(artifacts.values())).parents[1]
    model_dir = next(iter(metadata.values())).parent
    expected_files = {*artifacts.values(), *metadata.values()}
    observed_files = {
        path.resolve()
        for directory in (data_dir, model_dir)
        for path in directory.rglob("*")
        if path.is_file()
    }
    if observed_files != expected_files:
        raise RuntimeError(
            "The materialized Phase-B file census is not exactly 6 data + 3 model files."
        )
    identity = {
        "status": EVALUATION_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
    }
    for label, path in metadata.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if any(payload.get(key) != value for key, value in identity.items()):
            raise RuntimeError(f"The materialized Phase-B {label} identity changed.")
    artifact_descriptors = {
        name: relative_artifact_descriptor(path, repo_root=repo_root)
        for name, path in artifacts.items()
    }
    metadata_descriptors = {
        name: relative_artifact_descriptor(path, repo_root=repo_root)
        for name, path in metadata.items()
    }
    manifest = json.loads(metadata["manifest"].read_text(encoding="utf-8"))
    if manifest.get("evaluation_artifacts") != artifact_descriptors:
        raise RuntimeError("A materialized Phase-B artifact disagrees with its manifest.")
    if (
        manifest.get("summary") != metadata_descriptors["summary"]
        or manifest.get("execution_receipt") != metadata_descriptors["execution_receipt"]
    ):
        raise RuntimeError("The Phase-B summary or receipt disagrees with its manifest.")
    trees = {
        "data": _directory_content_descriptor(
            data_dir, sorted(artifacts.values()), repo_root=repo_root
        ),
        "model": _directory_content_descriptor(
            model_dir, sorted(metadata.values()), repo_root=repo_root
        ),
    }
    for key in ("data", "model"):
        if int(pointer_outs[key]["nfiles"]) != int(trees[key]["nfiles"]) or int(
            pointer_outs[key]["size"]
        ) != int(trees[key]["size"]):
            raise RuntimeError(
                f"The Phase-B {key} DVC out.size/nfiles disagree with real materialization."
            )
        if str(pointer_outs[key]["md5"]) != str(trees[key]["dvc_md5"]):
            raise RuntimeError(
                f"The Phase-B {key} DVC directory digest disagrees with real content."
            )
    return {
        "census": {"data_files": 6, "model_files": 3, "total_files": 9},
        "artifacts": artifact_descriptors,
        **metadata_descriptors,
        "trees": trees,
    }


def _require_tagged_ancestor(
    *,
    source_tag: str,
    source_commit: str,
    evaluation_commit: str,
    root: Path,
) -> None:
    """Require the source tag identity and direct Git ancestry of the evaluation."""
    if _resolve_strict_tag(root, source_tag) != source_commit:
        raise RuntimeError("The source protocol tag no longer resolves to its pinned commit.")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, evaluation_commit],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestry.returncode != 0:
        raise RuntimeError("The V1 source commit is not an ancestor of the V2 evaluation commit.")


def _require_descriptor_at_commit(
    descriptor: Mapping[str, Any],
    *,
    commit: str,
    label: str,
    root: Path,
) -> None:
    """Require an exact descriptor to equal its Git blob at one pinned commit."""
    relative_path = str(descriptor["path"])
    blob_bytes = _git_blob_bytes(
        commit=commit,
        relative_path=relative_path,
        root=root,
        label=label,
    )
    observed = {
        "path": relative_path,
        "bytes": len(blob_bytes),
        "sha256": hashlib.sha256(blob_bytes).hexdigest(),
    }
    if observed != dict(descriptor):
        raise RuntimeError(f"{label} disagrees with its pinned Git blob.")


def _require_phase_artifact_transport(
    source: Mapping[str, Any],
    *,
    evaluation_commit: str,
    root: Path,
    phase_label: str,
    expected_nfiles: Mapping[str, int],
    require_materialized: bool = True,
) -> dict[str, dict[str, Any]]:
    """Require a direct, tag-bound, two-pointer DVC promotion between phases."""
    protocol_commit = str(source["protocol_commit"])
    artifact_commit = str(source["artifact_commit"])
    parent_line = subprocess.run(
        ["git", "rev-list", "--parents", "-n", "1", artifact_commit],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    commit_and_parents = parent_line.stdout.strip().split()
    if (
        parent_line.returncode != 0
        or len(commit_and_parents) != 2
        or commit_and_parents != [artifact_commit, protocol_commit]
    ):
        raise RuntimeError(
            f"The Phase-{phase_label} artifact commit must have exactly one parent: its protocol."
        )
    _require_tagged_ancestor(
        source_tag=str(source["protocol_tag"]),
        source_commit=protocol_commit,
        evaluation_commit=artifact_commit,
        root=root,
    )
    _require_tagged_ancestor(
        source_tag=str(source["artifact_tag"]),
        source_commit=artifact_commit,
        evaluation_commit=evaluation_commit,
        root=root,
    )
    if evaluation_commit != artifact_commit:
        evaluation_parent_line = subprocess.run(
            ["git", "rev-list", "--parents", "-n", "1", evaluation_commit],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        evaluation_and_parents = evaluation_parent_line.stdout.strip().split()
        if evaluation_parent_line.returncode != 0 or evaluation_and_parents != [
            evaluation_commit,
            artifact_commit,
        ]:
            raise RuntimeError(
                f"The phase after Phase-{phase_label} artifacts must be their "
                "single-parent direct child."
            )
    expected_paths = {
        "data": ("data/processed/experiments/ijds_audit/" + str(source["run_tag"]) + ".dvc"),
        "model": ("models/experiments/ijds_audit/" + str(source["run_tag"]) + ".dvc"),
    }
    pointers = source["dvc_pointers"]
    observed_paths = {key: str(pointers[key]["path"]) for key in expected_paths}
    if observed_paths != expected_paths:
        raise RuntimeError(f"The Phase-{phase_label} DVC pointer paths changed.")
    changed = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", artifact_commit],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    changed_paths = {line.strip() for line in changed.stdout.splitlines() if line.strip()}
    if changed_paths != set(expected_paths.values()):
        raise RuntimeError(
            f"The Phase-{phase_label} artifact commit contains paths other than two DVC pointers."
        )
    for relative_path in expected_paths.values():
        preexisting = subprocess.run(
            ["git", "cat-file", "-e", f"{protocol_commit}:{relative_path}"],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if preexisting.returncode == 0:
            raise RuntimeError(
                f"A Phase-{phase_label} DVC pointer already existed at the protocol commit."
            )

    pointer_outs = {
        key: _dvc_pointer_out_contract(
            descriptor,
            commit=artifact_commit,
            run_tag=str(source["run_tag"]),
            expected_nfiles=int(expected_nfiles[key]),
            label=f"Phase-{phase_label} {key} DVC pointer",
            root=root,
        )
        for key, descriptor in pointers.items()
    }
    materialized = {
        key: (root / str(descriptor["path"])).resolve().with_suffix("")
        for key, descriptor in pointers.items()
    }
    if require_materialized and not all(path.is_dir() for path in materialized.values()):
        raise RuntimeError(f"Both Phase-{phase_label} DVC output paths must be occupied.")
    return pointer_outs


def _require_phase_a_artifact_transport(
    source: Mapping[str, Any],
    *,
    evaluation_commit: str,
    root: Path,
    require_materialized: bool = True,
) -> dict[str, dict[str, Any]]:
    """Compatibility wrapper for the locked 8+3 Phase-A transport contract."""
    return _require_phase_artifact_transport(
        source,
        evaluation_commit=evaluation_commit,
        root=root,
        phase_label="A",
        expected_nfiles={"data": 8, "model": 3},
        require_materialized=require_materialized,
    )


def _transport_authority_payload(
    source: Mapping[str, Any],
    *,
    pointer_outs: Mapping[str, Mapping[str, Any]],
    repo_root: Path,
) -> dict[str, Any]:
    """Build tag-object, commit, pointer, and implementation authority."""
    protocol_commit = str(source["protocol_commit"])
    artifact_commit = str(source["artifact_commit"])
    protocol_tag = _tag_authority(repo_root, str(source["protocol_tag"]))
    artifact_tag = _tag_authority(repo_root, str(source["artifact_tag"]))
    if protocol_tag["peeled_commit"] != protocol_commit:
        raise RuntimeError("The protocol tag object no longer peels to the pinned commit.")
    if artifact_tag["peeled_commit"] != artifact_commit:
        raise RuntimeError("The artifact tag object no longer peels to the pinned commit.")
    return {
        "protocol": protocol_tag,
        "artifact": {
            **artifact_tag,
            "parents": [protocol_commit],
            "changed_paths": [
                str(source["dvc_pointers"][key]["path"]) for key in ("data", "model")
            ],
        },
        "source_config": dict(source["config"]),
        "implementation_blobs": {
            "runner": _git_blob_descriptor(
                commit=artifact_commit, relative_path=RUNNER_PATH, root=repo_root
            ),
            "uv_lock": _git_blob_descriptor(
                commit=artifact_commit, relative_path=UV_LOCK_PATH, root=repo_root
            ),
        },
        "dvc_pointers": {
            key: {
                "descriptor": dict(source["dvc_pointers"][key]),
                "out": dict(pointer_outs[key]),
            }
            for key in ("data", "model")
        },
    }


def _phase_a_transport_receipt_payload(
    source: Mapping[str, Any],
    *,
    pointer_outs: Mapping[str, Mapping[str, Any]],
    source_config: Mapping[str, Any],
    repo_root: Path,
    pre_git: Mapping[str, Any],
    post_git: Mapping[str, Any],
    pull_argv: Sequence[str],
    pull_result: subprocess.CompletedProcess[bytes],
    status_argv: Sequence[str],
    status_result: subprocess.CompletedProcess[bytes],
) -> dict[str, Any]:
    """Build a canonical tamper-evident reconciliation from observed subprocess results."""
    protocol_commit = str(source["protocol_commit"])
    artifact_commit = str(source["artifact_commit"])
    expected_clean = {
        "head": artifact_commit,
        "tracked_clean": True,
        "tracked_entries": 0,
        "porcelain": _bytes_descriptor(b""),
    }
    if dict(pre_git) != expected_clean or dict(post_git) != expected_clean:
        raise RuntimeError("Tracked Git authority changed during clean-clone transport.")
    if pull_result.returncode != 0:
        raise RuntimeError(
            f"Exact two-pointer DVC pull failed with return code {pull_result.returncode}."
        )
    if status_result.returncode != 0:
        raise RuntimeError(
            f"Post-pull DVC status failed with return code {status_result.returncode}."
        )
    try:
        status_payload = json.loads(bytes(status_result.stdout or b"").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Post-pull DVC status did not emit valid UTF-8 JSON.") from error
    if not _status_payload_is_clean(status_payload):
        raise RuntimeError("Post-pull DVC status reports content drift.")
    return {
        "schema_version": TRANSPORT_SCHEMA_VERSION,
        "status": TRANSPORT_STATUS,
        "phase": "A",
        "run_tag": str(source["run_tag"]),
        "evidence_characterization": (
            "tamper_evident_reconciliation_record_not_independent_execution_proof"
        ),
        "authority": _transport_authority_payload(
            source, pointer_outs=pointer_outs, repo_root=repo_root
        ),
        "runtime": _transport_runtime_contract(),
        "preconditions": {
            "git": dict(pre_git),
            "output_paths_absent": True,
            "receipt_path_absent": True,
        },
        "execution": {
            "dvc_pull": {
                "succeeded": True,
                "transcript": _subprocess_transcript(argv=pull_argv, result=pull_result),
            },
            "dvc_status": {
                "clean": True,
                "transcript": _subprocess_transcript(argv=status_argv, result=status_result),
            },
        },
        "postconditions": {
            "git": dict(post_git),
            "dvc_status_clean": True,
        },
        "materialized_phase_a": _verified_phase_a_materialization(
            source_config,
            protocol_commit=protocol_commit,
            repo_root=repo_root,
            pointer_outs=pointer_outs,
        ),
    }


def verify_phase_a_clean_clone_transport(
    *,
    config_path: Path,
    artifact_tag: str,
    repo_root: Path = ROOT,
) -> Path:
    """Pull Phase A at its artifact tag and emit a deterministic, hash-pinnable receipt."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_set_preserving_config(resolved_config)
    if config["protocol_status"] != "locked_candidate_two_phase_before_execution":
        raise RuntimeError("Transport verification requires the locked V1a source config.")
    run_tag = str(config["run_tag"])
    materialized_dirs = {
        (root / str(config["output"][key]) / run_tag).resolve()
        for key in ("data_root", "model_root")
    }
    if any(path.exists() for path in materialized_dirs):
        raise RuntimeError(
            "Clean-clone transport requires both Phase-A outputs absent before pull."
        )
    receipt_path = (root / TRANSPORT_RECEIPT_PATH).resolve()
    if receipt_path.exists():
        raise FileExistsError("The deterministic Phase-A transport receipt path is occupied.")
    protocol_commit = _resolve_strict_tag(root, str(config["protocol_tag"]))
    artifact_commit = _require_clean_strict_tagged_head(root, artifact_tag)
    pointer_paths = {
        "data": f"data/processed/experiments/ijds_audit/{run_tag}.dvc",
        "model": f"models/experiments/ijds_audit/{run_tag}.dvc",
    }
    pointers = {
        key: relative_artifact_descriptor(
            resolve_repo_input(relative_path, repo_root=root), repo_root=root
        )
        for key, relative_path in pointer_paths.items()
    }
    source = {
        "run_tag": run_tag,
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "artifact_tag": str(artifact_tag),
        "artifact_commit": artifact_commit,
        "dvc_pointers": pointers,
        "config": relative_artifact_descriptor(resolved_config, repo_root=root),
    }
    pointer_outs = _require_phase_a_artifact_transport(
        source,
        evaluation_commit=artifact_commit,
        root=root,
        require_materialized=False,
    )
    pre_git = _tracked_git_state(root)
    pull_argv = _dvc_argv("pull", *(str(pointers[key]["path"]) for key in ("data", "model")))
    pull = subprocess.run(
        pull_argv,
        cwd=root,
        check=False,
        capture_output=True,
        text=False,
        shell=False,
    )
    if pull.returncode != 0:
        raise RuntimeError(f"Exact two-pointer DVC pull failed with return code {pull.returncode}.")
    if not all(path.is_dir() for path in materialized_dirs):
        raise RuntimeError("Exact two-pointer DVC pull did not materialize both output trees.")
    status_argv = _dvc_argv(
        "status", "--json", *(str(pointers[key]["path"]) for key in ("data", "model"))
    )
    status = subprocess.run(
        status_argv,
        cwd=root,
        check=False,
        capture_output=True,
        text=False,
        shell=False,
    )
    post_git = _tracked_git_state(root)
    receipt = _phase_a_transport_receipt_payload(
        source,
        pointer_outs=pointer_outs,
        source_config=config,
        repo_root=root,
        pre_git=pre_git,
        post_git=post_git,
        pull_argv=pull_argv,
        pull_result=pull,
        status_argv=status_argv,
        status_result=status,
    )
    return _write_canonical_json(receipt_path, receipt)


def _phase_b_transport_receipt_path(run_tag: str) -> Path:
    return Path("reports/crpto") / f"{run_tag}_clean_clone_transport_receipt.json"


def verify_phase_b_clean_clone_transport(
    *,
    config_path: Path,
    artifact_tag: str,
    repo_root: Path = ROOT,
) -> Path:
    """Clean-clone pull and reconcile the sealed 6+3 Phase-B output capsule."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_set_preserving_config(resolved_config)
    if config["protocol_status"] != "locked_hash_pinned_postfreeze_evaluation":
        raise RuntimeError("Phase-B transport verification requires the locked V1b config.")
    run_tag = str(config["run_tag"])
    materialized_dirs = {
        (root / str(config["output"][key]) / run_tag).resolve()
        for key in ("data_root", "model_root")
    }
    if any(path.exists() for path in materialized_dirs):
        raise RuntimeError("Clean-clone Phase-B transport requires absent output paths.")
    receipt_path = (root / _phase_b_transport_receipt_path(run_tag)).resolve()
    if receipt_path.exists():
        raise FileExistsError("The deterministic Phase-B transport receipt path is occupied.")
    protocol_commit = _resolve_strict_tag(root, str(config["protocol_tag"]))
    artifact_commit = _require_clean_strict_tagged_head(root, artifact_tag)
    pointer_paths = {
        "data": f"data/processed/experiments/ijds_audit/{run_tag}.dvc",
        "model": f"models/experiments/ijds_audit/{run_tag}.dvc",
    }
    pointers = {
        key: relative_artifact_descriptor(
            resolve_repo_input(relative_path, repo_root=root), repo_root=root
        )
        for key, relative_path in pointer_paths.items()
    }
    source = {
        "run_tag": run_tag,
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "artifact_tag": str(artifact_tag),
        "artifact_commit": artifact_commit,
        "dvc_pointers": pointers,
        "config": relative_artifact_descriptor(resolved_config, repo_root=root),
    }
    pointer_outs = _require_phase_artifact_transport(
        source,
        evaluation_commit=artifact_commit,
        root=root,
        phase_label="B",
        expected_nfiles={"data": 6, "model": 3},
        require_materialized=False,
    )
    pre_git = _tracked_git_state(root)
    pull_argv = _dvc_argv("pull", *(str(pointers[key]["path"]) for key in ("data", "model")))
    pull = subprocess.run(
        pull_argv,
        cwd=root,
        check=False,
        capture_output=True,
        text=False,
        shell=False,
    )
    if pull.returncode != 0:
        raise RuntimeError(f"Exact Phase-B DVC pull failed with return code {pull.returncode}.")
    if not all(path.is_dir() for path in materialized_dirs):
        raise RuntimeError("Exact Phase-B DVC pull did not materialize both output trees.")
    status_argv = _dvc_argv(
        "status", "--json", *(str(pointers[key]["path"]) for key in ("data", "model"))
    )
    status = subprocess.run(
        status_argv,
        cwd=root,
        check=False,
        capture_output=True,
        text=False,
        shell=False,
    )
    post_git = _tracked_git_state(root)
    expected_clean = {
        "head": artifact_commit,
        "tracked_clean": True,
        "tracked_entries": 0,
        "porcelain": _bytes_descriptor(b""),
    }
    if pre_git != expected_clean or post_git != expected_clean:
        raise RuntimeError("Tracked Git authority changed during Phase-B clean-clone transport.")
    if status.returncode != 0:
        raise RuntimeError(f"Phase-B DVC status failed with return code {status.returncode}.")
    try:
        status_payload = json.loads(bytes(status.stdout or b"").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Phase-B DVC status did not emit valid UTF-8 JSON.") from error
    if not _status_payload_is_clean(status_payload):
        raise RuntimeError("Phase-B DVC status reports content drift.")
    receipt = {
        "schema_version": TRANSPORT_SCHEMA_VERSION,
        "status": PHASE_B_TRANSPORT_STATUS,
        "phase": "B",
        "run_tag": run_tag,
        "evidence_characterization": (
            "tamper_evident_reconciliation_record_not_independent_execution_proof"
        ),
        "authority": _transport_authority_payload(
            source, pointer_outs=pointer_outs, repo_root=root
        ),
        "runtime": _transport_runtime_contract(),
        "preconditions": {
            "git": pre_git,
            "output_paths_absent": True,
            "receipt_path_absent": True,
        },
        "execution": {
            "dvc_pull": {
                "succeeded": True,
                "transcript": _subprocess_transcript(argv=pull_argv, result=pull),
            },
            "dvc_status": {
                "clean": True,
                "transcript": _subprocess_transcript(argv=status_argv, result=status),
            },
        },
        "postconditions": {"git": post_git, "dvc_status_clean": True},
        "materialized_phase_b": _verified_phase_b_materialization(
            config,
            protocol_commit=protocol_commit,
            repo_root=root,
            pointer_outs=pointer_outs,
        ),
    }
    return _write_canonical_json(receipt_path, receipt)


def _verify_phase_a_transport_receipt(
    source: Mapping[str, Any],
    *,
    source_config: Mapping[str, Any],
    pointer_outs: Mapping[str, Mapping[str, Any]],
    evaluation_commit: str,
    evaluation_tag: str,
    root: Path,
) -> None:
    """Verify canonical receipt bytes and current materialization before outcomes."""
    if _require_clean_strict_tagged_head(root, evaluation_tag) != evaluation_commit:
        raise RuntimeError("Phase B must run at its clean annotated V1b authority.")
    descriptor = source["clean_clone_transport_receipt"]
    if str(descriptor["path"]) != TRANSPORT_RECEIPT_PATH.as_posix():
        raise RuntimeError("The clean-clone transport receipt escaped its locked path.")
    receipt_path = _verified_descriptor_path(
        descriptor,
        label="Clean-clone Phase-A transport receipt",
        root=root,
    )
    _require_descriptor_at_commit(
        descriptor,
        commit=evaluation_commit,
        label="Clean-clone Phase-A transport receipt",
        root=root,
    )
    receipt_bytes = receipt_path.read_bytes()
    try:
        observed = json.loads(receipt_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("The clean-clone receipt is not strict UTF-8 JSON.") from error
    if not isinstance(observed, dict) or receipt_bytes != _canonical_json_bytes(observed):
        raise RuntimeError("The clean-clone receipt bytes are not canonical schema 2026-07-29.2.")
    expected_authority = _transport_authority_payload(
        source, pointer_outs=pointer_outs, repo_root=root
    )
    expected_materialization = _verified_phase_a_materialization(
        source_config,
        protocol_commit=str(source["protocol_commit"]),
        repo_root=root,
        pointer_outs=pointer_outs,
    )
    static_expected = {
        "schema_version": TRANSPORT_SCHEMA_VERSION,
        "status": TRANSPORT_STATUS,
        "phase": "A",
        "run_tag": str(source["run_tag"]),
        "evidence_characterization": (
            "tamper_evident_reconciliation_record_not_independent_execution_proof"
        ),
        "authority": expected_authority,
        "runtime": _transport_runtime_contract(),
        "materialized_phase_a": expected_materialization,
    }
    expected_top_level = {
        *static_expected,
        "preconditions",
        "execution",
        "postconditions",
    }
    if set(observed) != expected_top_level or any(
        observed.get(key) != value for key, value in static_expected.items()
    ):
        raise RuntimeError("The clean-clone DVC transport receipt does not reconcile exactly.")
    artifact_commit = str(source["artifact_commit"])
    expected_git = {
        "head": artifact_commit,
        "tracked_clean": True,
        "tracked_entries": 0,
        "porcelain": _bytes_descriptor(b""),
    }
    if observed.get("preconditions") != {
        "git": expected_git,
        "output_paths_absent": True,
        "receipt_path_absent": True,
    } or observed.get("postconditions") != {
        "git": expected_git,
        "dvc_status_clean": True,
    }:
        raise RuntimeError("The clean-clone receipt pre/post state is invalid.")
    pointer_paths = [str(source["dvc_pointers"][key]["path"]) for key in ("data", "model")]
    pull_argv = _dvc_argv("pull", *pointer_paths)
    status_argv = _dvc_argv("status", "--json", *pointer_paths)
    execution = observed.get("execution")
    if not isinstance(execution, dict) or set(execution) != {"dvc_pull", "dvc_status"}:
        raise RuntimeError("The clean-clone receipt execution schema changed.")
    pull = execution["dvc_pull"]
    status = execution["dvc_status"]
    if not isinstance(pull, dict) or not isinstance(status, dict):
        raise RuntimeError("The clean-clone receipt subprocess entries must be mappings.")
    if set(pull) != {"succeeded", "transcript"} or set(status) != {"clean", "transcript"}:
        raise RuntimeError("The clean-clone receipt subprocess entry schema changed.")
    if pull.get("succeeded") is not True or status.get("clean") is not True:
        raise RuntimeError("The clean-clone receipt does not record successful transport.")
    _verify_transcript(pull.get("transcript", {}), expected_argv=pull_argv)
    _verify_transcript(status.get("transcript", {}), expected_argv=status_argv)
    current_status = subprocess.run(
        status_argv,
        cwd=root,
        check=False,
        capture_output=True,
        text=False,
        shell=False,
    )
    if current_status.returncode != 0:
        raise RuntimeError("Current Phase-A DVC status invocation failed before Phase B.")
    try:
        current_status_payload = json.loads(bytes(current_status.stdout or b"").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Current Phase-A DVC status is not valid UTF-8 JSON.") from error
    if not _status_payload_is_clean(current_status_payload):
        raise RuntimeError("Current Phase-A DVC materialization is not clean before Phase B.")
    forbidden = (b"C:/Users/", b"C:\\Users\\", b"/home/")
    if any(token.lower() in receipt_bytes.lower() for token in forbidden):
        raise RuntimeError("The clean-clone receipt serializes a personal absolute path.")


def _require_committed_implementation(
    provenance: Mapping[str, Any],
    *,
    commit: str,
    root: Path,
) -> None:
    """Reconcile every declared implementation descriptor to its Git blob at V1."""
    source_files = provenance.get("source_files")
    if not isinstance(source_files, dict) or provenance.get("hash_algorithm") != "sha256":
        raise RuntimeError("The V1 implementation provenance schema is invalid.")
    for relative_path, descriptor in source_files.items():
        if not isinstance(descriptor, dict) or descriptor.get("path") != relative_path:
            raise RuntimeError("The V1 implementation descriptor key/path identity changed.")
        blob = subprocess.run(
            ["git", "show", f"{commit}:{relative_path}"],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if blob.returncode != 0:
            raise RuntimeError(
                f"V1 implementation path is absent from its commit: {relative_path}."
            )
        observed = {
            "path": relative_path,
            "bytes": len(blob.stdout),
            "sha256": hashlib.sha256(blob.stdout).hexdigest(),
        }
        if observed != descriptor:
            raise RuntimeError(f"V1 Git blob disagrees with provenance: {relative_path}.")


def _require_v2_implementation_equals_v1(
    source_provenance: Mapping[str, Any],
    evaluation_provenance: Mapping[str, Any],
    *,
    source_config_path: str,
    evaluation_config_path: str,
) -> None:
    """Require an exact dependency census and no V1-to-V2 implementation drift."""
    locked_paths = {path.as_posix() for path in IMPLEMENTATION_PATHS}
    source_files = source_provenance.get("source_files")
    evaluation_files = evaluation_provenance.get("source_files")
    if not isinstance(source_files, dict) or not isinstance(evaluation_files, dict):
        raise RuntimeError("V1 or V2 implementation provenance lacks source_files.")
    if set(source_files) != {*locked_paths, source_config_path}:
        raise RuntimeError("The V1 implementation provenance omits or adds a locked path.")
    if set(evaluation_files) != {*locked_paths, evaluation_config_path}:
        raise RuntimeError("The V2 implementation provenance omits or adds a locked path.")
    for path in locked_paths:
        if evaluation_files[path] != source_files[path]:
            raise RuntimeError(f"A scientific dependency changed between V1 and V2: {path}.")


def _require_v2_is_v1_plus_pin(
    evaluation: Mapping[str, Any],
    source: Mapping[str, Any],
) -> None:
    """Allow only administrative V2 fields plus the external source authority."""
    mutable = {"schema_version", "protocol_status", "protocol_tag", "run_tag", "source_frontier"}
    evaluation_science = {key: value for key, value in evaluation.items() if key not in mutable}
    source_science = {key: value for key, value in source.items() if key not in mutable}
    if evaluation_science != source_science:
        raise RuntimeError("V2 is not canonically identical to V1 outside the pin whitelist.")
    if (
        evaluation.get("protocol_status") != "locked_hash_pinned_postfreeze_evaluation"
        or source.get("protocol_status") != "locked_candidate_two_phase_before_execution"
        or evaluation.get("run_tag") == source.get("run_tag")
        or evaluation.get("protocol_tag") == source.get("protocol_tag")
    ):
        raise RuntimeError("V1/V2 administrative identities are not separated correctly.")


def _candidate_identity_contract(frame: pd.DataFrame) -> dict[str, Any]:
    """Hash the exact role-period-ID census without persisting candidate IDs."""
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


def _outcome_free_summary(
    build: SetPreservingFrontierBuild,
    *,
    config: Mapping[str, Any],
    parent_freeze: Mapping[str, Any],
    protocol_commit: str,
    protected_reads: list[dict[str, Any]],
) -> dict[str, Any]:
    records = build.solve_records
    negative = build.allocation_contrasts.loc[
        build.allocation_contrasts["contrast_family"].eq("theta_minus_theta_0_within_gamma")
        & build.allocation_contrasts["gamma"].eq(0.0)
    ]
    budget = float(config["normalization"]["committed_budget_per_period"])
    periods = int(config["frontier"]["expected_primary_months"])
    budget_tolerance = float(config["solver"]["budget_residual_tolerance_dollars"])
    maximum_budget_residual = float(records["budget_residual"].abs().max())
    return {
        "schema_version": str(config["schema_version"]),
        "status": FREEZE_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "parent_status": parent_freeze.get("status"),
        "parent_freeze_sha256": str(config["parent"]["protocol_freeze"]["sha256"]),
        "counts": {
            "solve_records": int(len(records)),
            "funded_rows": int(len(build.allocations)),
            "embedding_diagnostics": int(len(build.embedding_diagnostics)),
            "minimum_score_endpoints": int(len(build.minimum_endpoint_diagnostics)),
            "objective_optima": int(len(build.objective_optimum_diagnostics)),
            "allocation_contrasts": int(len(build.allocation_contrasts)),
            "order_replays": int(len(build.order_sensitivity)),
            "independent_solver_cells": int(len(build.independent_validation)),
            "windows": int(records["window_id"].nunique()),
            "role_periods": int(records[["role", "period"]].drop_duplicates().shape[0]),
            "thetas": int(records["theta"].nunique()),
            "gammas": int(records["gamma"].nunique()),
            "coordinates": int(records["frontier_coordinate"].nunique()),
            "rulers": int(records["frontier_ruler"].nunique()),
        },
        "embedding_contract": {
            "sets_changed": int(build.embedding_diagnostics["sets_changed"].sum()),
            "maximum_upper_contraction": float(
                build.embedding_diagnostics["maximum_upper_contraction"].max()
            ),
            "theta_zero_maximum_recovery_error": float(
                build.embedding_diagnostics.loc[
                    build.embedding_diagnostics["theta"].eq(0.0),
                    "maximum_theta_zero_recovery_error",
                ].max()
            ),
        },
        "common_objective_ruler": {
            "lower_endpoint_scope": "one_z_L_over_all_25_theta_gamma_scores_per_cell",
            "minimum_range_dollars": float(
                (records["unconstrained_objective"] - records["common_objective_lower"]).min()
            ),
            "maximum_range_dollars": float(
                (records["unconstrained_objective"] - records["common_objective_lower"]).max()
            ),
        },
        "negative_control": {
            "cells": int(len(negative)),
            "maximum_exposure_distance": float(negative["normalized_exposure_distance"].max()),
            "maximum_absolute_objective_difference": float(
                negative["objective_difference"].abs().max()
            ),
        },
        "normalization": {
            "committed_budget_B_dollars": budget,
            "primary_periods_T": periods,
            "pooled_capital_TB_dollars": periods * budget,
            "monthly_budget_residual_tolerance_dollars": budget_tolerance,
            "pooled_budget_residual_tolerance_dollars": periods * budget_tolerance,
            "maximum_absolute_solver_budget_residual_dollars": maximum_budget_residual,
            "solver_capital_reconciles_to_B": maximum_budget_residual <= budget_tolerance,
            "common_across_policies": True,
            "solver_capital_renormalization": False,
        },
        "maximum_budget_residual_dollars": maximum_budget_residual,
        "maximum_id_reversal_exposure_distance": float(
            build.order_sensitivity["normalized_exposure_distance"].max()
        ),
        "maximum_glop_objective_rate_difference": float(
            build.independent_validation["objective_rate_difference"].abs().max()
        ),
        "outcome_columns_passed": [],
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
        "protected_stages_run": [],
        "protected_artifacts_read": protected_reads,
        "protected_artifacts_written": [],
    }


def run_outcome_free(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Build the complete decision grid and freeze it before any outcome read."""
    started = time.perf_counter()
    started_at = utc_now_iso()
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_set_preserving_config(resolved_config)
    if config["protocol_status"] != "locked_candidate_two_phase_before_execution":
        raise RuntimeError("Outcome-free construction requires the locked V1 build config.")
    protocol_commit = _require_clean_strict_tagged_head(root, str(config["protocol_tag"]))
    initial_authority = _authority_snapshot(resolved_config, root)
    _require_committed_implementation(
        initial_authority["implementation"], commit=protocol_commit, root=root
    )
    preflight_fresh_run(config, repo_root=root)

    parent_paths, parent_freeze = verified_parent_artifacts(config, repo_root=root)
    parent_config_path = resolve_repo_input(str(config["parent"]["config"]), repo_root=root)
    parent_commit = str(config["parent"]["protocol_commit"])
    _require_tagged_ancestor(
        source_tag=str(config["parent"]["protocol_tag"]),
        source_commit=parent_commit,
        evaluation_commit=protocol_commit,
        root=root,
    )
    parent_provenance = parent_freeze.get("implementation_provenance")
    if not isinstance(parent_provenance, dict):
        raise RuntimeError("The historical parent freeze lacks implementation provenance.")
    parent_config_descriptor = relative_artifact_descriptor(parent_config_path, repo_root=root)
    if parent_provenance.get("source_files", {}).get(str(config["parent"]["config"])) != (
        parent_config_descriptor
    ):
        raise RuntimeError("The current parent config disagrees with its historical freeze.")
    _require_committed_implementation(parent_provenance, commit=parent_commit, root=root)
    parent_config = load_v4_config(parent_config_path)
    if float(config["normalization"]["committed_budget_per_period"]) != float(
        parent_config["policy"]["budget"]
    ):
        raise RuntimeError("The locked common-capital normalizer differs from the parent budget.")
    raw_path = resolve_repo_input(str(config["source_ingest"]["raw_path"]), repo_root=root)
    raw_digest = sha256_file(raw_path)
    if raw_digest != str(config["source_ingest"]["raw_sha256"]):
        raise RuntimeError("The locked raw decision archive changed before Phase-A construction.")
    protected_reads = [
        {
            "path": raw_path.relative_to(root).as_posix(),
            "bytes": int(raw_path.stat().st_size),
            "sha256": raw_digest,
        }
    ]
    base = load_outcome_free_decision_base(
        scores_path=parent_paths["scores"],
        raw_path=raw_path,
        config=config,
    )
    candidate_identity = _candidate_identity_contract(
        base.assign(
            role=base["design_split"].astype("string"),
            period=pd.to_datetime(base["issue_d"]).dt.to_period("M").astype("string"),
        )
    )
    recipes = load_recipes(parent_paths["recipes"])
    build = build_set_preserving_frontiers(
        base,
        recipes,
        config=config,
        parent_config=parent_config,
    )
    repeated_paths, repeated_parent = verified_parent_artifacts(config, repo_root=root)
    if repeated_paths != parent_paths or repeated_parent != parent_freeze:
        raise RuntimeError("Parent freeze authority changed during Phase A.")
    if sha256_file(raw_path) != str(config["source_ingest"]["raw_sha256"]):
        raise RuntimeError("Raw decision archive changed during Phase A.")
    _require_unchanged_authority(
        config=config,
        config_path=resolved_config,
        protocol_commit=protocol_commit,
        initial=initial_authority,
        root=root,
    )
    summary = _outcome_free_summary(
        build,
        config=config,
        parent_freeze=parent_freeze,
        protocol_commit=protocol_commit,
        protected_reads=protected_reads,
    )

    paths = prepare_output_paths(config, repo_root=root)
    frontier_dir = paths.data_dir / "frontier"
    output = config["output"]
    artifacts = {
        "solve_records": atomic_write_parquet(
            build.solve_records, frontier_dir / str(output["solve_records"])
        ),
        "allocations": atomic_write_parquet(
            build.allocations, frontier_dir / str(output["allocations"])
        ),
        "embedding_diagnostics": atomic_write_parquet(
            build.embedding_diagnostics,
            frontier_dir / str(output["embedding_diagnostics"]),
        ),
        "minimum_endpoint_diagnostics": atomic_write_parquet(
            build.minimum_endpoint_diagnostics,
            frontier_dir / str(output["minimum_endpoint_diagnostics"]),
        ),
        "objective_optimum_diagnostics": atomic_write_parquet(
            build.objective_optimum_diagnostics,
            frontier_dir / str(output["objective_optimum_diagnostics"]),
        ),
        "allocation_contrasts": atomic_write_parquet(
            build.allocation_contrasts,
            frontier_dir / str(output["allocation_contrasts"]),
        ),
        "order_sensitivity": atomic_write_parquet(
            build.order_sensitivity,
            frontier_dir / str(output["order_sensitivity"]),
        ),
        "independent_validation": atomic_write_parquet(
            build.independent_validation,
            frontier_dir / str(output["independent_validation"]),
        ),
    }
    summary_path = atomic_write_json(paths.model_dir / str(output["outcome_free_summary"]), summary)
    receipt_path = atomic_write_json(
        paths.model_dir / str(output["outcome_free_receipt"]),
        {
            "schema_version": str(config["schema_version"]),
            "status": FREEZE_STATUS,
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "started_at_utc": started_at,
            "completed_at_utc": utc_now_iso(),
            "elapsed_seconds": float(time.perf_counter() - started),
            "outcome_columns_passed": [],
            "protected_stages_run": [],
            "protected_artifacts_read": protected_reads,
            "protected_artifacts_written": [],
        },
    )
    freeze = {
        "schema_version": str(config["schema_version"]),
        "status": FREEZE_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "parent": {
            "run_tag": str(config["parent"]["run_tag"]),
            "protocol_freeze": dict(config["parent"]["protocol_freeze"]),
        },
        "decision_contract": {
            "budget": float(parent_config["policy"]["budget"]),
            "max_concentration_by_purpose": float(
                parent_config["policy"]["max_concentration_by_purpose"]
            ),
            "lgd": float(parent_config["payoff"]["lgd"]),
            "raw_path": str(config["source_ingest"]["raw_path"]),
            "raw_sha256": str(config["source_ingest"]["raw_sha256"]),
            "roles": list(config["frontier"]["roles"]),
            "candidate_identity": candidate_identity,
        },
        "outcome_columns_passed_to_frontier": [],
        "selection": {
            "theta": None,
            "gamma": None,
            "ruler": None,
            "coordinate": None,
            "window": None,
            "policy": None,
        },
        "implementation_provenance": initial_authority["implementation"],
        "environment": initial_authority["environment"],
        "git": initial_authority["git"],
        "schemas": {name: dataframe_schema(getattr(build, name)) for name in artifacts},
        "outcome_free_artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in artifacts.items()
        },
        "summary": relative_artifact_descriptor(summary_path, repo_root=root),
        "execution_receipt": relative_artifact_descriptor(receipt_path, repo_root=root),
        "protected_stages_run": [],
        "protected_artifacts_read": protected_reads,
        "protected_artifacts_written": [],
    }
    repeated_paths, repeated_parent = verified_parent_artifacts(config, repo_root=root)
    if repeated_paths != parent_paths or repeated_parent != parent_freeze:
        raise RuntimeError("Parent freeze authority changed before the Phase-A seal.")
    if sha256_file(raw_path) != str(config["source_ingest"]["raw_sha256"]):
        raise RuntimeError("Raw decision archive changed before the Phase-A seal.")
    _require_unchanged_authority(
        config=config,
        config_path=resolved_config,
        protocol_commit=protocol_commit,
        initial=initial_authority,
        root=root,
    )
    for name, path in artifacts.items():
        if (
            relative_artifact_descriptor(path, repo_root=root)
            != freeze["outcome_free_artifacts"][name]
        ):
            raise RuntimeError(f"A Phase-A artifact changed before freeze seal: {name}.")
    if (
        relative_artifact_descriptor(summary_path, repo_root=root) != freeze["summary"]
        or relative_artifact_descriptor(receipt_path, repo_root=root) != freeze["execution_receipt"]
    ):
        raise RuntimeError("The Phase-A summary or receipt changed before freeze seal.")
    freeze_path = atomic_write_json(paths.model_dir / str(output["protocol_freeze"]), freeze)
    logger.info(
        "Frozen {} outcome-free embedding cells and {} funded rows in {:.1f}s",
        len(build.solve_records),
        len(build.allocations),
        time.perf_counter() - started,
    )
    return freeze_path


def _verify_frozen_phase(
    config: Mapping[str, Any],
    *,
    evaluation_commit: str,
    evaluation_config_path: Path,
    evaluation_environment: Mapping[str, Any],
    evaluation_provenance: Mapping[str, Any],
    repo_root: Path,
) -> tuple[Path, dict[str, Any], dict[str, Path]]:
    source = config["source_frontier"]
    source_config_path = _verified_descriptor_path(
        source["config"], label="Hash-pinned source V1 config", root=repo_root
    )
    source_config = load_set_preserving_config(source_config_path)
    _require_v2_is_v1_plus_pin(config, source_config)
    source_commit = str(source["protocol_commit"])
    if (
        source_config.get("run_tag") != source["run_tag"]
        or source_config.get("protocol_tag") != source["protocol_tag"]
    ):
        raise RuntimeError("The pinned V1 config identity disagrees with source_frontier.")
    _require_tagged_ancestor(
        source_tag=str(source["protocol_tag"]),
        source_commit=source_commit,
        evaluation_commit=evaluation_commit,
        root=repo_root,
    )
    pointer_outs = _require_phase_a_artifact_transport(
        source,
        evaluation_commit=evaluation_commit,
        root=repo_root,
    )
    _verify_phase_a_transport_receipt(
        source,
        source_config=source_config,
        pointer_outs=pointer_outs,
        evaluation_commit=evaluation_commit,
        evaluation_tag=str(config["protocol_tag"]),
        root=repo_root,
    )

    freeze_path = _verified_descriptor_path(
        source["freeze"], label="Hash-pinned source freeze", root=repo_root
    )
    source_data_dir = (
        repo_root / str(source_config["output"]["data_root"]) / str(source["run_tag"])
    ).resolve()
    source_model_dir = (
        repo_root / str(source_config["output"]["model_root"]) / str(source["run_tag"])
    ).resolve()
    expected_freeze_path = (
        source_model_dir / str(source_config["output"]["protocol_freeze"])
    ).resolve()
    if freeze_path != expected_freeze_path:
        raise RuntimeError("The hash-pinned freeze is outside its exact V1 run directory.")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    expected = {
        "status": FREEZE_STATUS,
        "run_tag": str(source["run_tag"]),
        "protocol_tag": str(source["protocol_tag"]),
        "protocol_commit": str(source["protocol_commit"]),
    }
    for key, value in expected.items():
        if freeze.get(key) != value:
            raise RuntimeError(f"Outcome-free freeze mismatch for {key}.")
    expected_git = {
        "commit": source_commit,
        "dirty": False,
        "dirty_entries": 0,
        "dirty_paths": [],
    }
    if freeze.get("git") != expected_git:
        raise RuntimeError("The V1 freeze does not attest its exact clean tagged Git state.")
    if freeze.get("environment") != dict(evaluation_environment):
        raise RuntimeError("The scientific runtime changed between V1 and V2.")
    provenance = freeze.get("implementation_provenance")
    if not isinstance(provenance, dict):
        raise RuntimeError("The V1 freeze lacks implementation provenance.")
    if provenance.get("source_files", {}).get(str(source["config"]["path"])) != dict(
        source["config"]
    ):
        raise RuntimeError("The V1 freeze does not bind the hash-pinned source config.")
    evaluation_config_relative = evaluation_config_path.resolve().relative_to(repo_root).as_posix()
    _require_v2_implementation_equals_v1(
        provenance,
        evaluation_provenance,
        source_config_path=str(source["config"]["path"]),
        evaluation_config_path=evaluation_config_relative,
    )
    _require_committed_implementation(provenance, commit=source_commit, root=repo_root)
    if freeze.get("outcome_columns_passed_to_frontier") != []:
        raise RuntimeError("Outcome-free freeze reports outcome leakage.")
    source_raw_path = resolve_repo_input(
        str(source_config["source_ingest"]["raw_path"]), repo_root=repo_root
    )
    protected_reads = [relative_artifact_descriptor(source_raw_path, repo_root=repo_root)]
    null_selection = {
        "theta": None,
        "gamma": None,
        "ruler": None,
        "coordinate": None,
        "window": None,
        "policy": None,
    }
    if (
        freeze.get("selection") != null_selection
        or freeze.get("protected_stages_run") != []
        or freeze.get("protected_artifacts_read") != protected_reads
        or freeze.get("protected_artifacts_written") != []
    ):
        raise RuntimeError("The V1 freeze reports selection or protected-stage execution.")
    if set(freeze.get("outcome_free_artifacts", {})) != PHASE_A_ARTIFACT_KEYS:
        raise RuntimeError("The outcome-free freeze artifact census changed.")
    if set(freeze.get("schemas", {})) != PHASE_A_ARTIFACT_KEYS:
        raise RuntimeError("The outcome-free freeze schema census changed.")
    artifacts = verified_freeze_artifact_paths(freeze, repo_root=repo_root)
    frontier_dir = (source_data_dir / "frontier").resolve()
    for name, path in artifacts.items():
        expected_path = (frontier_dir / str(source_config["output"][name])).resolve()
        if path != expected_path:
            raise RuntimeError(f"Frozen artifact escaped its exact V1 path: {name}.")

    summary_path = _verified_descriptor_path(
        freeze["summary"], label="V1 outcome-free summary", root=repo_root
    )
    receipt_path = _verified_descriptor_path(
        freeze["execution_receipt"], label="V1 execution receipt", root=repo_root
    )
    if (
        summary_path
        != (source_model_dir / str(source_config["output"]["outcome_free_summary"])).resolve()
        or receipt_path
        != (source_model_dir / str(source_config["output"]["outcome_free_receipt"])).resolve()
    ):
        raise RuntimeError("V1 summary or receipt escaped the exact source run directory.")
    for label, payload_path in (("summary", summary_path), ("receipt", receipt_path)):
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        for key, value in expected.items():
            if payload.get(key) != value:
                raise RuntimeError(f"V1 {label} disagrees with source authority for {key}.")
        if (
            payload.get("outcome_columns_passed") != []
            or payload.get("protected_stages_run") != []
            or payload.get("protected_artifacts_read") != protected_reads
            or payload.get("protected_artifacts_written") != []
        ):
            raise RuntimeError(f"V1 {label} reports outcome leakage or protected execution.")
        if label == "summary" and payload.get("selection") != null_selection:
            raise RuntimeError("V1 summary reports post-inspection selection.")
    return freeze_path, freeze, artifacts


def _evaluation_summary(
    *,
    config: Mapping[str, Any],
    protocol_commit: str,
    freeze: Mapping[str, Any],
    evaluated: pd.DataFrame,
    joined: pd.DataFrame,
    monthly: pd.DataFrame,
    window: pd.DataFrame,
    directions: pd.DataFrame,
    outcome_audit: pd.DataFrame,
    protected_reads: list[dict[str, Any]],
) -> dict[str, Any]:
    negative = window.loc[
        window["contrast_family"].eq("theta_minus_theta_0_within_gamma") & window["gamma"].eq(0.0)
    ]
    direction_counts = (
        directions.groupby(["metric", "direction_at_tolerance"], observed=True)
        .size()
        .rename("cells")
        .reset_index()
        .to_dict(orient="records")
    )
    geometric_direction_counts = (
        directions.groupby(["metric", "geometric_direction"], observed=True)
        .size()
        .rename("cells")
        .reset_index()
        .to_dict(orient="records")
    )
    budget = float(config["normalization"]["committed_budget_per_period"])
    periods = int(config["frontier"]["expected_primary_months"])
    pooled_capital = periods * budget
    budget_tolerance = float(config["solver"]["budget_residual_tolerance_dollars"])

    def maximum_capital_residual(frame: pd.DataFrame, expected_capital: float) -> float:
        values = frame[["policy_a_capital", "policy_b_capital"]].to_numpy(dtype=float)
        return float(abs(values - expected_capital).max(initial=0.0))

    def maximum_payoff_reconciliation(frame: pd.DataFrame, normalizer: float) -> float:
        errors = []
        for suffix in ("lower", "upper"):
            dollars = frame[f"realized_payoff_difference_{suffix}"].to_numpy(dtype=float)
            rates = frame[f"realized_payoff_rate_difference_{suffix}"].to_numpy(dtype=float)
            errors.append(abs(rates - dollars / normalizer).max(initial=0.0))
        return float(max(errors, default=0.0))

    monthly_capital_residual = maximum_capital_residual(monthly, budget)
    pooled_capital_residual = maximum_capital_residual(window, pooled_capital)
    monthly_payoff_reconciliation = maximum_payoff_reconciliation(monthly, budget)
    pooled_payoff_reconciliation = maximum_payoff_reconciliation(window, pooled_capital)
    return {
        "schema_version": str(config["schema_version"]),
        "status": EVALUATION_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "source_freeze_status": freeze["status"],
        "counts": {
            "evaluated_primary_portfolios": int(len(evaluated)),
            "joined_funded_rows": int(len(joined)),
            "monthly_sharp_contrasts": int(len(monthly)),
            "window_sharp_contrasts": int(len(window)),
            "metric_direction_rows": int(len(directions)),
            "outcome_audit_rows": int(len(outcome_audit)),
        },
        "negative_control": {
            "window_cells": int(len(negative)),
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
        },
        "normalization": {
            "committed_budget_B_dollars": budget,
            "primary_periods_T": periods,
            "pooled_capital_TB_dollars": pooled_capital,
            "monthly_budget_residual_tolerance_dollars": budget_tolerance,
            "pooled_budget_residual_tolerance_dollars": periods * budget_tolerance,
            "maximum_monthly_policy_capital_residual_dollars": monthly_capital_residual,
            "maximum_pooled_policy_capital_residual_dollars": pooled_capital_residual,
            "maximum_monthly_payoff_rate_reconciliation_error": (monthly_payoff_reconciliation),
            "maximum_pooled_payoff_rate_reconciliation_error": pooled_payoff_reconciliation,
            "monthly_policy_capital_reconciles_to_B": (
                monthly_capital_residual <= budget_tolerance
            ),
            "pooled_policy_capital_reconciles_to_TB": (
                pooled_capital_residual <= periods * budget_tolerance
            ),
            "payoff_rates_reconcile_to_common_capital": max(
                monthly_payoff_reconciliation, pooled_payoff_reconciliation
            )
            <= 1.0e-12,
            "common_across_policies": True,
            "solver_capital_renormalization": False,
        },
        "direction_counts": direction_counts,
        "geometric_direction_counts": geometric_direction_counts,
        "unresolved_primary_candidates": int(outcome_audit["unresolved_rows"].sum()),
        "window_aggregation": "pooled_15_month_union_sum_numerators_before_rates",
        "outcome_refit": False,
        "outcome_selection": False,
        "policy_selection": None,
        "theta_selection": None,
        "gamma_selection": None,
        "ruler_selection": None,
        "coordinate_selection": None,
        "policy_winner": None,
        "causal_interpretation": False,
        "conformal_guarantee_repair": False,
        "protected_stages_run": [],
        "protected_artifacts_read": protected_reads,
        "protected_artifacts_written": [],
    }


def run_evaluation(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Verify Phase A before opening outcomes, then retain all primary contrasts."""
    started = time.perf_counter()
    started_at = utc_now_iso()
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_set_preserving_config(resolved_config)
    if config["protocol_status"] != "locked_hash_pinned_postfreeze_evaluation":
        raise RuntimeError(
            "V1 cannot authorize outcomes; create, commit, and tag a hash-pinned V2 config."
        )
    protocol_commit = _require_clean_strict_tagged_head(root, str(config["protocol_tag"]))
    initial_authority = _authority_snapshot(resolved_config, root)
    _require_committed_implementation(
        initial_authority["implementation"], commit=protocol_commit, root=root
    )
    preflight_fresh_run(config, repo_root=root)
    freeze_path, freeze, artifacts = _verify_frozen_phase(
        config,
        evaluation_commit=protocol_commit,
        evaluation_config_path=resolved_config,
        evaluation_environment=initial_authority["environment"],
        evaluation_provenance=initial_authority["implementation"],
        repo_root=root,
    )

    outcome_config_path = resolve_repo_input(
        str(config["outcomes"]["parent_config"]), repo_root=root
    )
    outcome_config = load_v4_config(outcome_config_path)
    decision_contract = freeze.get("decision_contract")
    if not isinstance(decision_contract, dict):
        raise RuntimeError("The V1 freeze lacks its decision contract.")
    expected_contract = {
        "budget": float(outcome_config["policy"]["budget"]),
        "max_concentration_by_purpose": float(
            outcome_config["policy"]["max_concentration_by_purpose"]
        ),
        "lgd": float(outcome_config["payoff"]["lgd"]),
        "raw_path": str(config["outcomes"]["raw_path"]),
        "raw_sha256": str(config["outcomes"]["raw_sha256"]),
        "roles": list(config["frontier"]["roles"]),
    }
    observed_static_contract = {key: decision_contract.get(key) for key in expected_contract}
    if observed_static_contract != expected_contract or not isinstance(
        decision_contract.get("candidate_identity"), dict
    ):
        raise RuntimeError("Phase-A and Phase-B policy/source contracts differ.")

    source_build = SetPreservingFrontierBuild(
        solve_records=pd.read_parquet(artifacts["solve_records"]),
        allocations=pd.read_parquet(artifacts["allocations"]),
        embedding_diagnostics=pd.read_parquet(artifacts["embedding_diagnostics"]),
        minimum_endpoint_diagnostics=pd.read_parquet(artifacts["minimum_endpoint_diagnostics"]),
        objective_optimum_diagnostics=pd.read_parquet(artifacts["objective_optimum_diagnostics"]),
        allocation_contrasts=pd.read_parquet(artifacts["allocation_contrasts"]),
        order_sensitivity=pd.read_parquet(artifacts["order_sensitivity"]),
        independent_validation=pd.read_parquet(artifacts["independent_validation"]),
    )
    for name in PHASE_A_ARTIFACT_KEYS:
        observed_schema = dataframe_schema(getattr(source_build, name))
        if observed_schema != freeze["schemas"][name]:
            raise RuntimeError(f"Frozen Phase-A schema changed for {name}.")
    validate_complete_frontier(
        source_build,
        config=config,
        budget=float(decision_contract["budget"]),
    )
    records = source_build.solve_records
    allocations = source_build.allocations
    del source_build
    primary_records = records.loc[records["role"].eq("primary_oot")].copy()
    primary_allocations = allocations.loc[allocations["role"].eq("primary_oot")].copy()
    del records, allocations
    if len(primary_records) != int(config["expected_census"]["primary_evaluated_portfolios"]):
        raise RuntimeError("Frozen primary portfolio census changed before outcomes.")

    if (
        str(config["source_ingest"]["raw_path"]) != str(config["outcomes"]["raw_path"])
        or str(config["source_ingest"]["raw_sha256"]) != str(config["outcomes"]["raw_sha256"])
        or str(config["outcomes"]["endpoint"]) != str(outcome_config["design"]["endpoint"])
    ):
        raise RuntimeError("The committed evaluation endpoint or raw authority diverged.")
    raw_path = resolve_repo_input(str(config["outcomes"]["raw_path"]), repo_root=root)
    if sha256_file(raw_path) != str(config["outcomes"]["raw_sha256"]):
        raise RuntimeError("The locked raw archive changed before the outcome join.")
    protected_reads = [relative_artifact_descriptor(raw_path, repo_root=root)]
    universe = load_outcome_universe(outcome_config, raw_path=raw_path)
    all_outcomes = configured_archive_outcomes(universe, outcome_config)
    candidate_outcomes = all_outcomes.loc[
        all_outcomes["role"].isin(decision_contract["roles"])
    ].copy()
    if _candidate_identity_contract(candidate_outcomes) != decision_contract["candidate_identity"]:
        raise RuntimeError("Phase-B candidate IDs differ from the outcome-free V1 universe.")
    outcomes = all_outcomes.loc[all_outcomes["role"].eq("primary_oot")].copy()
    evaluated, joined = evaluate_frozen_portfolios(
        primary_records,
        primary_allocations,
        outcomes,
        config=outcome_config,
    )
    if not bool(evaluated["full_budget"].all()):
        raise RuntimeError("At least one evaluated primary portfolio failed full-budget status.")
    outcome_audit = primary_outcome_audit(outcomes, primary_allocations)
    monthly, window, directions = build_sharp_embedding_contrasts(
        joined,
        config=config,
        lgd=float(outcome_config["payoff"]["lgd"]),
        budget=float(decision_contract["budget"]),
    )
    repeated_freeze_path, repeated_freeze, repeated_artifacts = _verify_frozen_phase(
        config,
        evaluation_commit=protocol_commit,
        evaluation_config_path=resolved_config,
        evaluation_environment=initial_authority["environment"],
        evaluation_provenance=initial_authority["implementation"],
        repo_root=root,
    )
    if (
        repeated_freeze_path != freeze_path
        or repeated_freeze != freeze
        or repeated_artifacts != artifacts
    ):
        raise RuntimeError("Hash-pinned source authority changed during Phase B.")
    if sha256_file(raw_path) != str(config["outcomes"]["raw_sha256"]):
        raise RuntimeError("Raw outcome archive changed during Phase B.")
    _require_unchanged_authority(
        config=config,
        config_path=resolved_config,
        protocol_commit=protocol_commit,
        initial=initial_authority,
        root=root,
    )
    summary = _evaluation_summary(
        config=config,
        protocol_commit=protocol_commit,
        freeze=freeze,
        evaluated=evaluated,
        joined=joined,
        monthly=monthly,
        window=window,
        directions=directions,
        outcome_audit=outcome_audit,
        protected_reads=protected_reads,
    )

    paths = prepare_output_paths(config, repo_root=root)
    evaluation_dir = paths.data_dir / "evaluation"
    output = config["output"]
    evaluation_files = {
        "evaluated_portfolios": atomic_write_parquet(
            evaluated, evaluation_dir / str(output["evaluated_portfolios"])
        ),
        "joined_funded_allocations": atomic_write_parquet(
            joined, evaluation_dir / str(output["joined_funded_allocations"])
        ),
        "monthly_sharp_contrasts": atomic_write_parquet(
            monthly, evaluation_dir / str(output["monthly_sharp_contrasts"])
        ),
        "window_sharp_contrasts": atomic_write_parquet(
            window, evaluation_dir / str(output["window_sharp_contrasts"])
        ),
        "metric_direction_census": atomic_write_parquet(
            directions, evaluation_dir / str(output["metric_direction_census"])
        ),
        "outcome_join_audit": atomic_write_parquet(
            outcome_audit, evaluation_dir / str(output["outcome_join_audit"])
        ),
    }
    summary_path = atomic_write_json(paths.model_dir / str(output["evaluation_summary"]), summary)
    receipt_path = atomic_write_json(
        paths.model_dir / str(output["evaluation_receipt"]),
        {
            "schema_version": str(config["schema_version"]),
            "status": EVALUATION_STATUS,
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "started_at_utc": started_at,
            "completed_at_utc": utc_now_iso(),
            "elapsed_seconds": float(time.perf_counter() - started),
            "source_freeze": relative_artifact_descriptor(freeze_path, repo_root=root),
            "protected_stages_run": [],
            "protected_artifacts_read": protected_reads,
            "protected_artifacts_written": [],
        },
    )
    manifest = {
        "schema_version": str(config["schema_version"]),
        "status": EVALUATION_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "source_freeze": relative_artifact_descriptor(freeze_path, repo_root=root),
        "source_artifacts": {
            name: dict(freeze["outcome_free_artifacts"][name]) for name in sorted(artifacts)
        },
        "outcome_source": {
            "config": relative_artifact_descriptor(outcome_config_path, repo_root=root),
            "raw_path": str(config["outcomes"]["raw_path"]),
            "raw_sha256": str(config["outcomes"]["raw_sha256"]),
            "columns_joined_after_freeze": list(config["outcomes"]["joined_columns"]),
        },
        "schemas": {
            name: dataframe_schema(frame)
            for name, frame in {
                "evaluated_portfolios": evaluated,
                "joined_funded_allocations": joined,
                "monthly_sharp_contrasts": monthly,
                "window_sharp_contrasts": window,
                "metric_direction_census": directions,
                "outcome_join_audit": outcome_audit,
            }.items()
        },
        "evaluation_artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in evaluation_files.items()
        },
        "summary": relative_artifact_descriptor(summary_path, repo_root=root),
        "execution_receipt": relative_artifact_descriptor(receipt_path, repo_root=root),
        "implementation_provenance": initial_authority["implementation"],
        "environment": initial_authority["environment"],
        "git": initial_authority["git"],
        "selection": {
            "theta": None,
            "gamma": None,
            "ruler": None,
            "coordinate": None,
            "window": None,
            "policy": None,
        },
        "protected_stages_run": [],
        "protected_artifacts_read": protected_reads,
        "protected_artifacts_written": [],
    }
    repeated_freeze_path, repeated_freeze, repeated_artifacts = _verify_frozen_phase(
        config,
        evaluation_commit=protocol_commit,
        evaluation_config_path=resolved_config,
        evaluation_environment=initial_authority["environment"],
        evaluation_provenance=initial_authority["implementation"],
        repo_root=root,
    )
    if (
        repeated_freeze_path != freeze_path
        or repeated_freeze != freeze
        or repeated_artifacts != artifacts
    ):
        raise RuntimeError("Hash-pinned source authority changed before the Phase-B seal.")
    if sha256_file(raw_path) != str(config["outcomes"]["raw_sha256"]):
        raise RuntimeError("Raw outcome archive changed before the Phase-B seal.")
    _require_unchanged_authority(
        config=config,
        config_path=resolved_config,
        protocol_commit=protocol_commit,
        initial=initial_authority,
        root=root,
    )
    for name, path in evaluation_files.items():
        if (
            relative_artifact_descriptor(path, repo_root=root)
            != manifest["evaluation_artifacts"][name]
        ):
            raise RuntimeError(f"A V2 evaluation artifact changed before seal: {name}.")
    if (
        relative_artifact_descriptor(summary_path, repo_root=root) != manifest["summary"]
        or relative_artifact_descriptor(receipt_path, repo_root=root)
        != manifest["execution_receipt"]
    ):
        raise RuntimeError("The V2 summary or receipt changed before seal.")
    manifest_path = atomic_write_json(
        paths.model_dir / str(output["evaluation_manifest"]), manifest
    )
    logger.info(
        "Evaluated {} primary policies and {} sharp window contrasts in {:.1f}s",
        len(evaluated),
        len(window),
        time.perf_counter() - started,
    )
    return manifest_path


def main(argv: Sequence[str] | None = None) -> None:
    """Dispatch exactly one locked phase."""
    args = parse_args(argv)
    if args.phase == "outcome-free":
        path = run_outcome_free(config_path=args.config, repo_root=ROOT)
    elif args.phase == "verify-phase-a-transport":
        path = verify_phase_a_clean_clone_transport(
            config_path=args.config,
            artifact_tag=str(args.artifact_tag),
            repo_root=ROOT,
        )
    elif args.phase == "verify-phase-b-transport":
        path = verify_phase_b_clean_clone_transport(
            config_path=args.config,
            artifact_tag=str(args.artifact_tag),
            repo_root=ROOT,
        )
    else:
        path = run_evaluation(config_path=args.config, repo_root=ROOT)
    logger.info("Wrote {}", path)


if __name__ == "__main__":
    main()
