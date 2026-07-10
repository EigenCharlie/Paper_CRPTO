"""Containment, provenance, and atomic I/O for isolated experiments."""

from __future__ import annotations

import hashlib
import importlib.metadata
import os
import platform
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from catboost import CatBoostClassifier

from src.utils.pipeline_runtime import atomic_write_text

RUN_TAG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")


@dataclass(frozen=True)
class OutputPaths:
    """Validated versioned output directories for one experiment run."""

    data_dir: Path
    model_dir: Path


def validate_run_tag(run_tag: str) -> str:
    """Reject separator-bearing or traversal-capable experiment tags."""
    value = str(run_tag).strip()
    if not RUN_TAG_PATTERN.fullmatch(value) or value in {".", ".."}:
        raise ValueError(f"Unsafe run_tag: {run_tag!r}")
    return value


def resolve_isolated_run_dir(
    *,
    repo_root: Path,
    configured_root: str | Path,
    allowed_relative_root: Path,
    run_tag: str,
) -> Path:
    """Resolve one direct child under an exact allowlisted experiment root."""
    safe_tag = validate_run_tag(run_tag)
    root = repo_root.resolve()
    configured = Path(configured_root)
    resolved_base = (
        (root / configured).resolve() if not configured.is_absolute() else configured.resolve()
    )
    allowed_base = (root / allowed_relative_root).resolve()
    if resolved_base != allowed_base:
        raise ValueError(
            f"Output root {resolved_base} is not the allowlisted experiment root {allowed_base}."
        )
    candidate = (resolved_base / safe_tag).resolve()
    relative = candidate.relative_to(resolved_base)
    if len(relative.parts) != 1 or relative.name != safe_tag:
        raise ValueError("Experiment output must be a direct run-tag child.")
    return candidate


def prepare_output_paths(
    config: dict[str, Any],
    *,
    repo_root: Path,
    allowed_data_root: Path,
    allowed_model_root: Path,
) -> OutputPaths:
    """Validate containment and enforce immutable no-overwrite outputs."""
    output = config["output"]
    run_tag = str(config["run_tag"])
    data_dir = resolve_isolated_run_dir(
        repo_root=repo_root,
        configured_root=str(output["data_root"]),
        allowed_relative_root=allowed_data_root,
        run_tag=run_tag,
    )
    model_dir = resolve_isolated_run_dir(
        repo_root=repo_root,
        configured_root=str(output["model_root"]),
        allowed_relative_root=allowed_model_root,
        run_tag=run_tag,
    )
    existing = [path for path in (data_dir, model_dir) if path.exists()]
    if existing:
        rendered = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            f"Experiment output already exists ({rendered}); choose a fresh run tag."
        )
    data_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    return OutputPaths(data_dir=data_dir, model_dir=model_dir)


def resolve_repo_input(path_like: str | Path, *, repo_root: Path) -> Path:
    """Resolve a required input and reject paths outside the repository."""
    root = repo_root.resolve()
    raw = Path(path_like)
    path = (root / raw).resolve() if not raw.is_absolute() else raw.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Input path must remain inside the repository: {path}") from exc
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def sha256_file(path: Path, *, block_size: int = 8 * 1024 * 1024) -> str:
    """Compute a streaming SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def relative_artifact_descriptor(path: Path, *, repo_root: Path) -> dict[str, Any]:
    """Describe an artifact with a repository-relative path and hash."""
    resolved = path.resolve()
    relative = resolved.relative_to(repo_root.resolve()).as_posix()
    return {
        "path": relative,
        "bytes": int(resolved.stat().st_size),
        "sha256": sha256_file(resolved),
    }


def implementation_provenance(
    *,
    config_path: Path,
    relative_paths: Sequence[Path],
    repo_root: Path,
) -> dict[str, Any]:
    """Bind deterministic results to every scientific implementation file."""
    files = [config_path.resolve(), *((repo_root / path).resolve() for path in relative_paths)]
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Implementation provenance files are missing: {missing}")
    descriptors = [relative_artifact_descriptor(path, repo_root=repo_root) for path in files]
    return {
        "source_files": {str(item["path"]): item for item in descriptors},
        "hash_algorithm": "sha256",
    }


def package_version(distribution: str) -> str | None:
    """Return an installed distribution version when available."""
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def git_provenance(repo_root: Path) -> dict[str, Any]:
    """Capture commit and dirty state without mutating Git."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        return {
            "commit": commit,
            "dirty": bool(status),
            "dirty_entries": len(status),
            "dirty_paths": status,
        }
    except (OSError, subprocess.CalledProcessError) as exc:
        return {"commit": None, "dirty": None, "error": str(exc)}


def require_clean_tagged_head(repo_root: Path, tag: str) -> str:
    """Require the protocol tag to resolve exactly to a clean current HEAD."""
    state = git_provenance(repo_root)
    commit = state.get("commit")
    if not isinstance(commit, str) or not commit:
        raise RuntimeError("A readable Git HEAD is required before experiment execution.")
    if state.get("dirty") is not False:
        raise RuntimeError("Experiment execution requires a clean predeclared worktree.")
    try:
        tagged_commit = subprocess.run(
            ["git", "rev-list", "-n", "1", str(tag)],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"Required protocol tag is unavailable: {tag}") from exc
    if tagged_commit != commit:
        raise RuntimeError(
            f"Protocol tag {tag!r} points to {tagged_commit!r}, not current HEAD {commit!r}."
        )
    return commit


def environment_provenance(repo_root: Path) -> dict[str, Any]:
    """Capture scientific runtime and solver-relevant metadata."""
    distributions = [
        "catboost",
        "highspy",
        "numpy",
        "pandas",
        "pyarrow",
        "scikit-learn",
        "scipy",
    ]
    highs_env_names = [
        "HIGHS_NATIVE_FALLBACK_SCIPY",
        "HIGHS_PARALLEL",
        "HIGHS_PRESOLVE",
        "HIGHS_RESET_GLOBAL_SCHEDULER",
        "HIGHS_SIMPLEX_STRATEGY",
        "HIGHS_SOLVER",
    ]
    lock_path = repo_root / "uv.lock"
    return {
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "packages": {name: package_version(name) for name in distributions},
        "solver_environment": {name: os.environ.get(name) for name in highs_env_names},
        "uv_lock_sha256": sha256_file(lock_path) if lock_path.exists() else None,
    }


def dataframe_schema(frame: pd.DataFrame) -> dict[str, Any]:
    """Return a compact row, column, and dtype descriptor."""
    return {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "dtypes": {str(column): str(dtype) for column, dtype in frame.dtypes.items()},
    }


def write_csv_atomic(frame: pd.DataFrame, path: Path) -> Path:
    """Write stable LF-delimited CSV through the atomic writer."""
    return atomic_write_text(path, frame.to_csv(index=False, lineterminator="\n"))


def save_catboost_model_atomic(model: CatBoostClassifier, path: Path) -> Path:
    """Save a CatBoost model without exposing a partial target."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    model.save_model(str(temporary), format="cbm")
    temporary.replace(path)
    return path
