"""Lightweight repository artifact hashing without scientific dependencies."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def sha256_file(path: Path, *, block_size: int = 8 * 1024 * 1024) -> str:
    """Compute a streaming SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def relative_artifact_descriptor(path: Path, *, repo_root: Path) -> dict[str, Any]:
    """Describe one repository-contained artifact by path, size, and hash."""
    resolved = path.resolve()
    relative = resolved.relative_to(repo_root.resolve()).as_posix()
    return {
        "path": relative,
        "bytes": int(resolved.stat().st_size),
        "sha256": sha256_file(resolved),
    }


def verified_artifact_path(
    descriptor: Mapping[str, Any],
    *,
    repo_root: Path,
    label: str,
) -> Path:
    """Resolve one repository artifact only after path, size, and hash agree."""
    raw_path = descriptor.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise TypeError(f"{label} descriptor omits a path.")
    path = (repo_root / raw_path).resolve()
    path.relative_to(repo_root.resolve())
    if not path.is_file():
        raise FileNotFoundError(f"{label} artifact is missing: {path}")
    actual = relative_artifact_descriptor(path, repo_root=repo_root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor.get(field):
            raise RuntimeError(f"{label} artifact mismatched on {field}.")
    return path
