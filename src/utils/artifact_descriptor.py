"""Lightweight repository artifact hashing without scientific dependencies."""

from __future__ import annotations

import hashlib
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
