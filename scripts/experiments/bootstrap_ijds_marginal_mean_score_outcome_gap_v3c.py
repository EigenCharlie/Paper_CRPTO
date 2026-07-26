"""Stdlib-only authenticated launcher for the V3C marginal-gap replay."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.machinery
import importlib.metadata
import importlib.util
import json
import locale
import os
import platform
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_PATH = Path("scripts/experiments/bootstrap_ijds_marginal_mean_score_outcome_gap_v3c.py")
RUNNER_PATH = Path("scripts/experiments/run_ijds_marginal_mean_score_outcome_gap_v3c.py")
CONFIG_PATH = Path("configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3c.yaml")
RUNTIME_MANIFEST_PATH = Path(
    "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3c_runtime.json"
)
CALIBRE_GLOBAL_TEMPLATE_PATH = Path(
    "configs/runtime/ijds_marginal_mean_score_outcome_gap_v3c_calibre_global.json"
)
PROTOCOL_PATH = Path(
    "docs/research/ijds_marginal_mean_score_outcome_gap_v3c_protocol_2026-07-26.md"
)
PROTOCOL_TAG = "protocol/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3c"
ARTIFACT_TAG = "artifacts/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3c"
ABORTED_V3B_PROTOCOL_COMMIT = "0a7b184d5d82748fb57d37c734268fc096259976"
EXPECTED_V3C_PROTOCOL_DIFF_PATHS = tuple(
    sorted(
        (
            "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3c.yaml",
            "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3c_runtime.json",
            "configs/runtime/ijds_marginal_mean_score_outcome_gap_v3c_calibre_global.json",
            "docs/research/ijds_marginal_mean_score_outcome_gap_v3c_protocol_2026-07-26.md",
            "scripts/experiments/bootstrap_ijds_marginal_mean_score_outcome_gap_v3c.py",
            "scripts/experiments/run_ijds_marginal_mean_score_outcome_gap_v3c.py",
            "src/ijds_audit/marginal_mean_score_outcome_gap_v3c.py",
            "tests/test_experiments/test_ijds_marginal_mean_score_outcome_gap_v3c.py",
            "tests/test_ijds_audit/test_marginal_mean_score_outcome_gap_v3c.py",
        )
    )
)
PROJECT_SITE_PACKAGES = ROOT / ".venv" / "Lib" / "site-packages"
CALIBRE_NATIVE_ROOT = Path("C:/Program Files/Calibre2/app/bin")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
GIT_EXECUTABLE = Path("C:/Program Files/Git/mingw64/bin/git.exe")
GIT_VERSION = "git version 2.52.0.windows.1"
ROOT_TRUST_FILES = (
    {
        "path": "C:/Program Files/Git/mingw64/bin/git.exe",
        "bytes": 4_321_168,
        "sha256": "fc0f1cae1304fcdcf4d0749f421c5ed21471efc856301f92f56d4b844be84363",
    },
    {
        "path": "C:/Program Files/Git/mingw64/bin/libiconv-2.dll",
        "bytes": 1_136_529,
        "sha256": "ff31fa811f9c07cc7fdaa68c9e8bca3a7b4fdf6e0a079a58175ea58ba139c7ae",
    },
    {
        "path": "C:/Program Files/Git/mingw64/bin/libintl-8.dll",
        "bytes": 298_055,
        "sha256": "7744fde3df3320fda0e3b599b4aa5349b1281f93d1e5c52865a52d0d3e4a7d39",
    },
    {
        "path": "C:/Program Files/Git/mingw64/bin/libpcre2-8-0.dll",
        "bytes": 717_955,
        "sha256": "c135a87ed0f11eae8ffc4cb469671ff0b3f5d71fab5fb024e9b1e7241ca25b52",
    },
    {
        "path": "C:/Program Files/Git/mingw64/bin/libzstd.dll",
        "bytes": 1_196_744,
        "sha256": "b13d4f30b93c96823473d742dda0075f7334cba03a40c33d8a7dc282e37b1500",
    },
    {
        "path": "C:/Program Files/Git/mingw64/bin/zlib1.dll",
        "bytes": 120_814,
        "sha256": "cb7ab3788d10940df874acd97b1821bbb5ee4a91f3eec11982bb5bf7a3c96443",
    },
    {
        "path": "C:/Program Files/Calibre2/calibre-debug.exe",
        "bytes": 32_368,
        "sha256": "f06cbc79c233457bf8bf1c3603981f685a727e7f68c1381c5e56c9cdb592d36b",
    },
    {
        "path": "C:/Program Files/Calibre2/app/bin/calibre-launcher.dll",
        "bytes": 429_168,
        "sha256": "a6037891c67e6d26be656ab7d8ef5dd03a45cbbce1e82bcce12c5f93b825ad73",
    },
    {
        "path": "C:/Program Files/Calibre2/app/bin/python3.dll",
        "bytes": 63_600,
        "sha256": "ee505b8f9757e92c8e0428105f548e4b030074e3337af8edf0ee08c48dd13568",
    },
    {
        "path": "C:/Program Files/Calibre2/app/bin/python311.dll",
        "bytes": 5_780_080,
        "sha256": "38373701aa805509e79e35a1ce61435b40e04fdc0572dfe459bc512bfdf74d23",
    },
    {
        "path": "C:/Program Files/Calibre2/app/bin/python-lib.bypy.frozen",
        "bytes": 65_192_617,
        "sha256": "fe1e602f84baeb10702f85f847019ea424fa10e7f9a38c7b3159e987c76b6d84",
    },
    {
        "path": "C:/Program Files/Calibre2/app/bin/_hashlib.pyd",
        "bytes": 53_248,
        "sha256": "78a39ecfdcd85a54a43c6b81a1f331e0677a46acdb4cf83e79a50f2b808a718d",
    },
    {
        "path": "C:/Program Files/Calibre2/app/bin/libcrypto-3-x64.dll",
        "bytes": 6_169_712,
        "sha256": "823d99212253c389ca6c34a35f373b3e6c3c048fac38f2ee5155fc005054224b",
    },
)
EXPECTED_SCIENTIFIC_CLOSURE = (
    Path("scripts/__init__.py"),
    RUNNER_PATH,
    Path("src/__init__.py"),
    Path("src/data/__init__.py"),
    Path("src/data/outcome_observability.py"),
    Path("src/ijds_audit/__init__.py"),
    Path("src/ijds_audit/config.py"),
    Path("src/ijds_audit/geometry.py"),
    Path("src/ijds_audit/marginal_mean_score_outcome_gap_v3c.py"),
    Path("src/ijds_audit/portfolio.py"),
    Path("src/ijds_audit/rhs_ranging.py"),
    Path("src/utils/__init__.py"),
    Path("src/utils/artifact_descriptor.py"),
)
NONPYTHON_AUTHORITY = (
    CONFIG_PATH,
    RUNTIME_MANIFEST_PATH,
    CALIBRE_GLOBAL_TEMPLATE_PATH,
    PROTOCOL_PATH,
    Path("tests/test_ijds_audit/test_marginal_mean_score_outcome_gap_v3c.py"),
    Path("tests/test_experiments/test_ijds_marginal_mean_score_outcome_gap_v3c.py"),
    Path(".gitignore"),
    Path(".gitattributes"),
    Path(".python-version"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)
_ACTIVE_SEALED_AUTHORITY_BYTES: dict[Path, bytes] = {}


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase", choices=("attest-only", "compute", "verify-artifact"), required=True
    )
    parser.add_argument("--config", type=Path, required=True)
    return parser.parse_args(argv)


def _sha256_file(path: Path, *, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def _stable_file_bytes(path: Path) -> bytes:
    """Read one regular file once and reject identity drift around that handle."""
    if path.is_symlink():
        raise RuntimeError(f"V3C sealed file is symlinked: {path}.")
    resolved = path.resolve()
    if not resolved.is_file():
        raise RuntimeError(f"V3C sealed file is missing, nonregular, or symlinked: {resolved}.")
    before = resolved.stat()
    with resolved.open("rb") as handle:
        handle_before = os.fstat(handle.fileno())
        payload = handle.read()
        handle_after = os.fstat(handle.fileno())
    after = resolved.stat()
    identities = {
        (
            value.st_dev,
            value.st_ino,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )
        for value in (before, handle_before, handle_after, after)
    }
    if len(identities) != 1 or len(payload) != after.st_size:
        raise RuntimeError(f"V3C sealed file changed while read: {resolved}.")
    return payload


def _descriptor_from_bytes(payload: bytes, *, relative_path: str) -> dict[str, Any]:
    return {
        "path": relative_path,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _file_descriptor(path: Path, *, relative_to: Path | None = None) -> dict[str, Any]:
    resolved = path.resolve()
    label = (
        resolved.relative_to(relative_to.resolve()).as_posix()
        if relative_to is not None
        else resolved.as_posix()
    )
    return _descriptor_from_bytes(_stable_file_bytes(path), relative_path=label)


def _require_file_descriptor(specification: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    path = Path(str(specification.get("path"))).resolve()
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"{label} is missing or symlinked: {path}.")
    observed = _file_descriptor(path)
    expected = {
        "path": path.as_posix(),
        "bytes": int(specification.get("bytes", -1)),
        "sha256": str(specification.get("sha256", "")),
    }
    if observed != expected:
        raise RuntimeError(f"{label} bytes changed: {observed} != {expected}.")
    return observed


def _git_environment() -> dict[str, str]:
    retained = (
        "APPDATA",
        "COMSPEC",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "PATHEXT",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "WINDIR",
    )
    environment = {key: os.environ[key] for key in retained if key in os.environ}
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "NUL",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
            "LANG": "C",
        }
    )
    return environment


def git_command(
    args: Sequence[str],
    *,
    repo_root: Path,
    binary: bool = False,
    check: bool = True,
) -> bytes | str:
    command = [
        str(GIT_EXECUTABLE),
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.untrackedCache=false",
        "-c",
        "core.excludesFile=NUL",
        *args,
    ]
    process = subprocess.run(
        command,
        cwd=repo_root,
        env=_git_environment(),
        check=False,
        capture_output=True,
        text=not binary,
    )
    if check and process.returncode != 0:
        stderr = process.stderr if isinstance(process.stderr, str) else process.stderr.decode()
        raise RuntimeError(f"Authenticated Git command failed ({args}): {stderr.strip()}.")
    return process.stdout


def _resolve_strict_tag(repo_root: Path, tag: str) -> str:
    value = str(tag)
    reference = f"refs/tags/{value}"
    if value.startswith(("-", "refs/")) or any(token in value for token in ("^", "~", ":")):
        raise RuntimeError(f"Tag is not an explicit safe tag name: {tag!r}.")
    valid = subprocess.run(
        [str(GIT_EXECUTABLE), "check-ref-format", reference],
        cwd=repo_root,
        env=_git_environment(),
        check=False,
        capture_output=True,
        text=True,
    )
    if valid.returncode != 0:
        raise RuntimeError(f"Tag is not a valid explicit ref: {tag!r}.")
    commit = str(
        git_command(
            ["rev-parse", "--verify", "--end-of-options", f"{reference}^{{commit}}"],
            repo_root=repo_root,
        )
    ).strip()
    if not HEX40.fullmatch(commit):
        raise RuntimeError(f"Tag {tag!r} did not resolve to a full commit.")
    return commit


def _require_v3c_protocol_parent(*, protocol_commit: str, repo_root: Path) -> None:
    parent_line = str(
        git_command(["rev-list", "--parents", "-n", "1", protocol_commit], repo_root=repo_root)
    ).strip()
    if parent_line.split() != [protocol_commit, ABORTED_V3B_PROTOCOL_COMMIT]:
        raise RuntimeError("V3C protocol commit must be the direct child of aborted V3B.")
    raw = git_command(
        ["diff", "--name-only", "-z", ABORTED_V3B_PROTOCOL_COMMIT, protocol_commit, "--"],
        repo_root=repo_root,
        binary=True,
    )
    if not isinstance(raw, bytes):
        raise TypeError("V3C protocol diff was not captured as bytes.")
    observed = tuple(sorted(value.decode("utf-8") for value in raw.split(b"\0") if value))
    if observed != EXPECTED_V3C_PROTOCOL_DIFF_PATHS:
        raise RuntimeError("V3C protocol commit must contain exactly nine authorized paths.")


def _git_snapshot(repo_root: Path) -> dict[str, Any]:
    commit = str(git_command(["rev-parse", "HEAD"], repo_root=repo_root)).strip()
    if not HEX40.fullmatch(commit):
        raise RuntimeError("Authenticated Git HEAD is unavailable or abbreviated.")
    status = git_command(
        ["status", "--porcelain=v2", "-z", "--untracked-files=all"],
        repo_root=repo_root,
        binary=True,
    )
    if not isinstance(status, bytes):
        raise TypeError("Authenticated Git porcelain was not captured as bytes.")
    return {
        "commit": commit,
        "porcelain_v2_sha256": hashlib.sha256(status).hexdigest(),
        "porcelain_v2_bytes": len(status),
        "clean": len(status) == 0,
    }


def _require_git_root(repo_root: Path) -> dict[str, Any]:
    top = Path(
        str(git_command(["rev-parse", "--show-toplevel"], repo_root=repo_root)).strip()
    ).resolve()
    git_dir = Path(
        str(git_command(["rev-parse", "--absolute-git-dir"], repo_root=repo_root)).strip()
    ).resolve()
    object_format = str(
        git_command(["rev-parse", "--show-object-format"], repo_root=repo_root)
    ).strip()
    replacements = str(git_command(["replace", "-l"], repo_root=repo_root)).strip()
    if (
        top != repo_root.resolve()
        or git_dir != (repo_root / ".git").resolve()
        or object_format != "sha1"
        or replacements
    ):
        raise RuntimeError(
            "Authenticated Git repository root, object format, or replacements changed."
        )
    return {
        "executable": _file_descriptor(GIT_EXECUTABLE),
        "version": GIT_VERSION,
        "top_level": ".",
        "git_dir": ".git",
        "object_format": object_format,
        "replace_refs": [],
        "environment_sanitized": True,
    }


def _require_clean_tag(repo_root: Path, tag: str) -> dict[str, Any]:
    snapshot = _git_snapshot(repo_root)
    if snapshot["clean"] is not True:
        raise RuntimeError("V3C bootstrap requires an exactly clean worktree and index.")
    if snapshot["commit"] != _resolve_strict_tag(repo_root, tag):
        raise RuntimeError(f"V3C bootstrap HEAD is not the explicit tag {tag!r}.")
    return snapshot


def _git_blob(repo_root: Path, *, commit: str, relative_path: Path) -> bytes:
    relative = relative_path.as_posix()
    listing = git_command(
        ["ls-tree", "-z", commit, "--", relative],
        repo_root=repo_root,
        binary=True,
    )
    if not isinstance(listing, bytes):
        raise TypeError("Authenticated Git tree listing was not captured as bytes.")
    records = [value for value in listing.split(b"\0") if value]
    if len(records) != 1 or b"\t" not in records[0]:
        raise RuntimeError(f"Authenticated Git blob path is absent or ambiguous: {relative}.")
    header, listed_path = records[0].split(b"\t", 1)
    fields = header.decode("ascii").split()
    if listed_path.decode("utf-8") != relative or len(fields) != 3 or fields[1] != "blob":
        raise RuntimeError(f"Authenticated Git tree entry changed: {relative}.")
    object_id = fields[2]
    if not HEX40.fullmatch(object_id):
        raise RuntimeError(f"Authenticated Git blob ID is malformed: {relative}.")
    output = git_command(["cat-file", "blob", object_id], repo_root=repo_root, binary=True)
    if not isinstance(output, bytes):
        raise TypeError("Authenticated Git blob was not captured as bytes.")
    return output


def _module_path(
    module_name: str,
    *,
    repo_root: Path,
    sealed_sources: Mapping[Path, bytes] | None = None,
) -> Path | None:
    if module_name != "src" and not module_name.startswith("src."):
        return None
    relative = Path(*module_name.split("."))
    module_relative = relative.with_suffix(".py")
    package_relative = relative / "__init__.py"
    if sealed_sources is not None:
        if module_relative in sealed_sources:
            return module_relative
        if package_relative in sealed_sources:
            return package_relative
        raise RuntimeError(f"Local import escaped the sealed V3C census: {module_name}.")
    module_file = repo_root / module_relative
    package_file = repo_root / package_relative
    if module_file.is_file():
        return module_relative
    if package_file.is_file():
        return package_relative
    raise RuntimeError(f"Local import cannot be resolved before import: {module_name}.")


def _module_package(relative: Path) -> str:
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    else:
        parts.pop()
    return ".".join(parts)


def _package_initializers(
    relative: Path,
    *,
    repo_root: Path,
    sealed_sources: Mapping[Path, bytes] | None = None,
) -> tuple[Path, ...]:
    parts = relative.parts[:-1]
    values: list[Path] = []
    for index in range(1, len(parts) + 1):
        candidate = Path(*parts[:index]) / "__init__.py"
        if (
            candidate in sealed_sources
            if sealed_sources is not None
            else (repo_root / candidate).is_file()
        ):
            values.append(candidate)
    return tuple(values)


def derive_local_python_closure(
    *, repo_root: Path, sealed_sources: Mapping[Path, bytes] | None = None
) -> tuple[Path, ...]:
    """Derive absolute/relative local imports and process every initializer."""
    pending = [RUNNER_PATH]
    observed: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in observed:
            continue
        path = repo_root / relative
        if sealed_sources is None and not path.is_file():
            raise FileNotFoundError(path)
        if sealed_sources is not None and relative not in sealed_sources:
            raise RuntimeError(f"V3C closure source is absent from its sealed census: {relative}.")
        observed.add(relative)
        for initializer in _package_initializers(
            relative, repo_root=repo_root, sealed_sources=sealed_sources
        ):
            if initializer not in observed:
                pending.append(initializer)
        source = (
            sealed_sources[relative].decode("utf-8")
            if sealed_sources is not None
            else path.read_text(encoding="utf-8")
        )
        tree = ast.parse(source, filename=str(path))
        modules: set[str] = set()
        package = _module_package(relative)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    if not package:
                        raise RuntimeError(f"Relative import outside a package: {relative}.")
                    request = "." * node.level + (node.module or "")
                    modules.add(importlib.util.resolve_name(request, package))
                elif node.module:
                    modules.add(node.module)
            elif isinstance(node, ast.Call):
                name = ""
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                if name in {"__import__", "import_module"}:
                    raise RuntimeError(f"Dynamic import is forbidden in V3C closure: {relative}.")
        for module in modules:
            resolved = _module_path(module, repo_root=repo_root, sealed_sources=sealed_sources)
            if resolved is not None and resolved not in observed:
                pending.append(resolved)
    return tuple(sorted(observed, key=lambda value: value.as_posix()))


def _require_authority_blobs(
    *, repo_root: Path, protocol_commit: str
) -> tuple[dict[str, Any], dict[Path, bytes]]:
    expected_paths = (
        BOOTSTRAP_PATH,
        *EXPECTED_SCIENTIFIC_CLOSURE,
        *NONPYTHON_AUTHORITY,
    )
    if len(expected_paths) != len(set(expected_paths)):
        raise RuntimeError("V3C bootstrap authority paths contain duplicates.")
    sealed: dict[Path, bytes] = {}
    descriptors: dict[str, dict[str, Any]] = {}
    for relative in expected_paths:
        payload = _stable_file_bytes(repo_root / relative)
        blob = _git_blob(repo_root, commit=protocol_commit, relative_path=relative)
        if payload != blob:
            raise RuntimeError(f"V3C bootstrap authority differs from Git blob: {relative}.")
        sealed[relative] = payload
        descriptors[relative.as_posix()] = _descriptor_from_bytes(
            payload, relative_path=relative.as_posix()
        )
    closure = derive_local_python_closure(repo_root=repo_root, sealed_sources=sealed)
    expected = tuple(sorted(EXPECTED_SCIENTIFIC_CLOSURE, key=lambda value: value.as_posix()))
    if closure != expected:
        raise RuntimeError(f"Bootstrap local closure changed: {closure} != {expected}.")
    python_paths = (BOOTSTRAP_PATH, *closure)
    violations: list[str] = []
    for relative in python_paths:
        tree = ast.parse(sealed[relative].decode("utf-8"), filename=str(relative))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                violations.append(f"{relative.as_posix()}:{node.lineno}")
    if violations:
        raise RuntimeError(f"Optimized V3C authority contains assert statements: {violations}.")
    return (
        {
            "protocol_commit": protocol_commit,
            "scientific_closure": [path.as_posix() for path in closure],
            "source_files": descriptors,
            "assert_statements": 0,
            "dynamic_imports": 0,
            "executed_from_sealed_git_bytes": True,
        },
        sealed,
    )


def _load_runtime_manifest(*, repo_root: Path, sealed_bytes: bytes | None = None) -> dict[str, Any]:
    data = (
        sealed_bytes
        if sealed_bytes is not None
        else _stable_file_bytes(repo_root / RUNTIME_MANIFEST_PATH)
    )
    payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != (
        "2026-07-26.3c-runtime-1"
    ):
        raise RuntimeError("V3C runtime manifest schema changed.")
    if set(payload) != {
        "schema_version",
        "bootstrap",
        "git",
        "calibre",
        "distributions",
        "module_paths",
    }:
        raise RuntimeError("V3C runtime manifest top-level fields changed.")
    return payload


def _find_distribution(name: str, *, venv: Path) -> importlib.metadata.Distribution:
    site = (venv / "Lib" / "site-packages").resolve()
    canonical = name.casefold().replace("_", "-")
    matches = [
        distribution
        for distribution in importlib.metadata.distributions(path=[str(site)])
        if str(distribution.metadata["Name"] or "").casefold().replace("_", "-") == canonical
    ]
    if len(matches) != 1:
        raise RuntimeError(f"V3C distribution discovery is not unique for {name!r}.")
    return matches[0]


def _distribution_seal_at_venv(name: str, *, venv: Path) -> dict[str, Any]:
    venv = venv.resolve()
    distribution = _find_distribution(name, venv=venv)
    records: list[list[str | int]] = []
    total = 0
    for entry in sorted(distribution.files or (), key=lambda value: str(value).replace("\\", "/")):
        path = Path(str(distribution.locate_file(entry))).resolve()
        try:
            relative = path.relative_to(venv).as_posix()
        except ValueError as exc:
            raise RuntimeError(f"Distribution {name!r} escaped the project venv: {path}.") from exc
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"Distribution {name!r} file is missing or symlinked: {path}.")
        payload = _stable_file_bytes(path)
        records.append([relative, len(payload), hashlib.sha256(payload).hexdigest()])
        total += len(payload)
    encoded = json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {
        "version": distribution.version,
        "files": len(records),
        "bytes": total,
        "composite_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _distribution_seal(name: str, *, repo_root: Path) -> dict[str, Any]:
    return _distribution_seal_at_venv(name, venv=(repo_root / ".venv").resolve())


def _directory_file_seal(directory: Path) -> dict[str, Any]:
    """Hash a complete immutable runtime directory with an exact path census."""
    root = directory.resolve()
    if not root.is_dir() or directory.is_symlink():
        raise RuntimeError(f"V3C runtime directory is missing or symlinked: {directory}.")
    records: list[list[str | int]] = []
    total = 0
    for candidate in sorted(root.rglob("*"), key=lambda value: value.as_posix().casefold()):
        if candidate.is_symlink():
            raise RuntimeError(f"V3C runtime directory contains a symlink: {candidate}.")
        if candidate.is_dir():
            continue
        if not candidate.is_file():
            raise RuntimeError(f"V3C runtime directory contains a nonregular entry: {candidate}.")
        payload = _stable_file_bytes(candidate)
        relative = candidate.relative_to(root).as_posix()
        records.append([relative, len(payload), hashlib.sha256(payload).hexdigest()])
        total += len(payload)
    encoded = json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {
        "path": root.as_posix(),
        "files": len(records),
        "bytes": total,
        "composite_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _distribution_file_paths(name: str, *, repo_root: Path) -> set[Path]:
    venv = (repo_root / ".venv").resolve()
    distribution = _find_distribution(name, venv=venv)
    paths: set[Path] = set()
    for entry in distribution.files or ():
        candidate = Path(str(distribution.locate_file(entry))).resolve()
        if candidate.is_file():
            paths.add(candidate)
    return paths


def materialize_locked_project_venv(source_venv: Path, *, repo_root: Path) -> dict[str, Any]:
    """Copy only the seven manifest-sealed RECORD closures into a fresh clone."""
    root = repo_root.resolve()
    source = source_venv.resolve()
    target = (root / ".venv").resolve()
    if not source.is_dir() or source_venv.is_symlink():
        raise RuntimeError(f"V3C source venv is missing or symlinked: {source_venv}.")
    if target.exists() or target == source:
        raise RuntimeError("V3C target .venv must be absent and distinct from the source venv.")
    runtime_bytes = _stable_file_bytes(root / RUNTIME_MANIFEST_PATH)
    manifest = _load_runtime_manifest(repo_root=root, sealed_bytes=runtime_bytes)
    payloads: dict[Path, bytes] = {}
    source_seals: dict[str, Any] = {}
    for name, expected in manifest["distributions"].items():
        observed = _distribution_seal_at_venv(str(name), venv=source)
        if observed != expected:
            raise RuntimeError(f"V3C source venv distribution drifted before copy: {name}.")
        source_seals[str(name)] = observed
        distribution = _find_distribution(str(name), venv=source)
        for entry in distribution.files or ():
            path = Path(str(distribution.locate_file(entry)))
            if path.is_symlink():
                raise RuntimeError(f"V3C source venv contains a symlinked RECORD file: {path}.")
            resolved = path.resolve()
            try:
                relative = resolved.relative_to(source)
            except ValueError as exc:
                raise RuntimeError(
                    f"V3C source distribution escaped its venv: {resolved}."
                ) from exc
            payload = _stable_file_bytes(resolved)
            previous = payloads.get(relative)
            if previous is not None and previous != payload:
                raise RuntimeError(f"V3C distribution RECORD collision changed bytes: {relative}.")
            payloads[relative] = payload
    for relative, payload in sorted(payloads.items(), key=lambda value: value[0].as_posix()):
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    target_seals = {
        str(name): _distribution_seal(str(name), repo_root=root)
        for name in manifest["distributions"]
    }
    if target_seals != manifest["distributions"] or target_seals != source_seals:
        raise RuntimeError("V3C materialized venv differs from the locked distribution composites.")
    return {
        "transport": "seven_distribution_record_closure_copy",
        "target": ".venv",
        "files": len(payloads),
        "bytes": sum(len(payload) for payload in payloads.values()),
        "distributions": target_seals,
    }


def require_loaded_native_modules(
    manifest: Mapping[str, Any], *, repo_root: Path
) -> dict[str, dict[str, Any]]:
    """Reject a loaded native extension outside the sealed Calibre/venv inventories."""
    calibre_root = CALIBRE_NATIVE_ROOT.resolve()
    allowed_venv: set[Path] = set()
    for distribution_name in manifest["distributions"]:
        allowed_venv.update(_distribution_file_paths(str(distribution_name), repo_root=repo_root))
    suffixes = tuple(value.casefold() for value in importlib.machinery.EXTENSION_SUFFIXES)
    observed: dict[str, dict[str, Any]] = {}
    for module_name, module in sorted(sys.modules.items()):
        raw_path = getattr(module, "__file__", None)
        if not raw_path:
            continue
        path = Path(str(raw_path)).resolve()
        normalized = path.as_posix().casefold()
        if not normalized.endswith(suffixes):
            continue
        try:
            path.relative_to(calibre_root)
            allowed = True
        except ValueError:
            allowed = path in allowed_venv
        if not allowed:
            raise RuntimeError(
                f"Loaded native module escaped the sealed V3C inventories: {module_name}={path}."
            )
        payload = _stable_file_bytes(path)
        label = (
            path.relative_to(repo_root.resolve()).as_posix()
            if path.is_relative_to(repo_root.resolve())
            else path.as_posix()
        )
        observed[str(module_name)] = _descriptor_from_bytes(payload, relative_path=label)
    return observed


def require_calibre_entrypoint_carrier(
    manifest: Mapping[str, Any],
    sealed_sources: Mapping[Path, bytes],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    """Authenticate Calibre's exact ``-e`` module carrier without a broad exemption."""
    expected = manifest["bootstrap"].get("calibre_entrypoint_carrier")
    expected_keys = {
        "module_key",
        "aliases",
        "module_name",
        "bootstrap_path",
        "package",
        "cached",
        "loader_module",
        "loader_class",
        "spec_name",
        "spec_origin",
        "spec_loader_is_module_loader",
        "spec_has_location",
        "spec_submodule_search_locations",
        "carrier_is_executing_globals",
    }
    if not isinstance(expected, Mapping) or set(expected) != expected_keys:
        raise RuntimeError("V3C Calibre entrypoint-carrier contract changed.")
    if Path(str(expected["bootstrap_path"])).as_posix() != BOOTSTRAP_PATH.as_posix():
        raise RuntimeError("V3C Calibre entrypoint bootstrap path changed.")
    if BOOTSTRAP_PATH not in sealed_sources:
        raise RuntimeError("V3C bootstrap is absent from the sealed authority census.")
    root = repo_root.resolve()
    expected_path = (root / BOOTSTRAP_PATH).resolve()
    module_key = str(expected["module_key"])
    carrier = sys.modules.get(module_key)
    if carrier is None:
        raise RuntimeError("V3C Calibre entrypoint carrier is absent.")
    aliases = sorted(name for name, module in sys.modules.items() if module is carrier)
    if aliases != list(expected["aliases"]) or aliases != [module_key]:
        raise RuntimeError(f"V3C Calibre entrypoint carrier aliases changed: {aliases}.")
    loader = getattr(carrier, "__loader__", None)
    spec = getattr(carrier, "__spec__", None)
    if spec is None:
        raise RuntimeError("V3C Calibre entrypoint carrier spec is absent.")
    raw_file = getattr(carrier, "__file__", None)
    if raw_file is None or Path(str(raw_file)).resolve() != expected_path:
        raise RuntimeError("V3C Calibre entrypoint carrier path changed.")
    raw_origin = getattr(spec, "origin", None)
    if (
        raw_origin is None
        or Path(str(raw_origin)).resolve() != Path(str(expected["spec_origin"])).resolve()
    ):
        raise RuntimeError("V3C Calibre entrypoint carrier spec origin changed.")
    observed = {
        "module_key": module_key,
        "aliases": aliases,
        "module_name": getattr(carrier, "__name__", None),
        "bootstrap_path": BOOTSTRAP_PATH.as_posix(),
        "package": getattr(carrier, "__package__", None),
        "cached": getattr(carrier, "__cached__", None),
        "loader_module": type(loader).__module__,
        "loader_class": type(loader).__name__,
        "spec_name": getattr(spec, "name", None),
        "spec_origin": Path(str(raw_origin)).as_posix(),
        "spec_loader_is_module_loader": getattr(spec, "loader", None) is loader,
        "spec_has_location": getattr(spec, "has_location", None),
        "spec_submodule_search_locations": getattr(spec, "submodule_search_locations", None),
        "carrier_is_executing_globals": vars(carrier) is globals(),
    }
    comparable = dict(observed)
    comparable["spec_origin"] = Path(str(comparable["spec_origin"])).resolve().as_posix()
    expected_comparable = dict(expected)
    expected_comparable["spec_origin"] = (
        Path(str(expected_comparable["spec_origin"])).resolve().as_posix()
    )
    if comparable != expected_comparable:
        raise RuntimeError(f"V3C Calibre entrypoint carrier identity changed: {comparable}.")
    bootstrap_payload = _stable_file_bytes(expected_path)
    if bootstrap_payload != sealed_sources[BOOTSTRAP_PATH]:
        raise RuntimeError("V3C Calibre entrypoint carrier file differs from sealed Git bytes.")
    observed["bootstrap_sha256"] = hashlib.sha256(bootstrap_payload).hexdigest()
    return observed


def require_loaded_module_origins(
    manifest: Mapping[str, Any],
    sealed_sources: Mapping[Path, bytes],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    """Reject loaded repo/site modules outside the sealed local and RECORD closures."""
    root = repo_root.resolve()
    site = (root / ".venv" / "Lib" / "site-packages").resolve()
    carrier_observation = require_calibre_entrypoint_carrier(
        manifest, sealed_sources, repo_root=repo_root
    )
    carrier = sys.modules[str(carrier_observation["module_key"])]
    site_observation = require_loaded_site_modules(manifest, repo_root=repo_root)
    loaded_site = list(site_observation["loaded_site_modules"])
    loaded_local: list[str] = []
    allowed_local = {
        (root / relative).resolve() for relative in sealed_sources if relative.suffix == ".py"
    }
    for module_name, module in sorted(sys.modules.items()):
        raw_path = getattr(module, "__file__", None)
        if not raw_path:
            continue
        path = Path(str(raw_path)).resolve()
        if path.is_relative_to(site):
            continue
        if path.is_relative_to(root):
            if str(module_name) == carrier_observation["module_key"] and module is carrier:
                loaded_local.append(str(module_name))
                continue
            if path not in allowed_local or not getattr(
                getattr(module, "__loader__", None), "_ijds_v3c_sealed_loader", False
            ):
                raise RuntimeError(
                    f"Loaded repository module escaped the sealed local loader: "
                    f"{module_name}={path}."
                )
            loaded_local.append(str(module_name))
    require_loaded_native_modules(manifest, repo_root=repo_root)
    return {
        "all_loaded_repo_and_site_modules_sealed": True,
        "loaded_site_modules": loaded_site,
        "loaded_local_modules": loaded_local,
        "calibre_entrypoint_carrier": carrier_observation,
    }


def require_loaded_site_modules(manifest: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    """Reject any loaded site-packages file outside the seven RECORD closures."""
    root = repo_root.resolve()
    site = (root / ".venv" / "Lib" / "site-packages").resolve()
    allowed_site: set[Path] = set()
    for distribution_name in manifest["distributions"]:
        allowed_site.update(_distribution_file_paths(str(distribution_name), repo_root=repo_root))
    loaded_site: list[str] = []
    for module_name, module in sorted(sys.modules.items()):
        raw_path = getattr(module, "__file__", None)
        if not raw_path:
            continue
        path = Path(str(raw_path)).resolve()
        if path.is_relative_to(site):
            if path not in allowed_site:
                raise RuntimeError(
                    f"Loaded site module escaped the seven sealed RECORD closures: "
                    f"{module_name}={path}."
                )
            loaded_site.append(str(module_name))
    return {
        "all_loaded_site_modules_sealed": True,
        "loaded_site_modules": loaded_site,
    }


def _require_directory_empty(path: Path, *, label: str) -> None:
    if not path.is_dir() or path.is_symlink():
        raise RuntimeError(f"{label} is missing or symlinked: {path}.")
    entries = list(path.iterdir())
    if entries:
        raise RuntimeError(f"{label} is not empty: {entries[:5]}.")


def _calibre_config_seal(manifest: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    bootstrap = manifest["bootstrap"]
    directory = (repo_root / str(bootstrap["calibre_config_directory"])).resolve()
    if not directory.is_dir() or directory.is_symlink():
        raise RuntimeError("Dedicated V3C Calibre config directory is missing or symlinked.")
    top = {path.name: path for path in directory.iterdir()}
    if set(top) != {"caches", "plugins", "global.py.json"}:
        raise RuntimeError(f"Dedicated V3C Calibre config inventory changed: {sorted(top)}.")
    _require_directory_empty(top["caches"], label="V3C Calibre cache directory")
    _require_directory_empty(top["plugins"], label="V3C Calibre plugin directory")
    template = (repo_root / str(bootstrap["calibre_global_template"])).resolve()
    template_payload = _ACTIVE_SEALED_AUTHORITY_BYTES.get(CALIBRE_GLOBAL_TEMPLATE_PATH)
    if template_payload is None:
        template_payload = _stable_file_bytes(template)
    global_payload = _stable_file_bytes(top["global.py.json"])
    if global_payload != template_payload:
        raise RuntimeError("V3C Calibre global configuration differs from its Git-bound template.")
    return {
        "directory": directory.relative_to(repo_root).as_posix(),
        "inventory": ["caches/", "global.py.json", "plugins/"],
        "global": _descriptor_from_bytes(
            global_payload,
            relative_path=top["global.py.json"].relative_to(repo_root).as_posix(),
        ),
        "caches_empty": True,
        "plugins_empty": True,
    }


def _calibre_cache_seal(manifest: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    relative = str(manifest["bootstrap"]["calibre_cache_directory"])
    directory = (repo_root / relative).resolve()
    if Path(os.environ.get("CALIBRE_CACHE_DIRECTORY", "")).resolve() != directory:
        raise RuntimeError("V3C CALIBRE_CACHE_DIRECTORY changed.")
    _require_directory_empty(directory, label="Dedicated V3C Calibre cache directory")
    return {"directory": directory.relative_to(repo_root).as_posix(), "empty": True}


def _require_forbidden_environment(manifest: Mapping[str, Any]) -> dict[str, Any]:
    forbidden = tuple(str(value) for value in manifest["bootstrap"]["forbidden_environment"])
    forbidden_names = tuple(
        str(value) for value in manifest["bootstrap"]["forbidden_environment_names"]
    )
    forbidden_prefixes = tuple(
        str(value) for value in manifest["bootstrap"]["forbidden_environment_prefixes"]
    )
    present_names = sorted(
        key
        for key in os.environ
        if key.upper() in forbidden
        or key.upper() in forbidden_names
        or any(key.upper().startswith(prefix) for prefix in forbidden_prefixes)
    )
    present = {key: os.environ[key] for key in present_names}
    if present:
        raise RuntimeError(
            f"V3C bootstrap inherited forbidden environment variables: {sorted(present)}."
        )
    return {
        "forbidden_variables_absent": list(forbidden),
        "forbidden_names_absent": list(forbidden_names),
        "forbidden_prefixes_absent": list(forbidden_prefixes),
    }


def _require_runtime_files(manifest: Mapping[str, Any]) -> dict[str, Any]:
    observed: dict[str, Any] = {}
    for family in ("git", "calibre"):
        for specification in manifest[family]["files"]:
            descriptor = _require_file_descriptor(specification, label=f"V3C {family} runtime file")
            observed[descriptor["path"]] = descriptor
    version = str(
        subprocess.run(
            [str(GIT_EXECUTABLE), "--version"],
            env=_git_environment(),
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    ).strip()
    if version != manifest["git"]["version"] or version != GIT_VERSION:
        raise RuntimeError("Authenticated Git version changed.")
    if (
        platform.python_implementation() != manifest["calibre"]["python_implementation"]
        or platform.python_version() != manifest["calibre"]["python_version"]
    ):
        raise RuntimeError("Embedded Calibre Python identity changed.")
    return {"files": observed, "git_version": version}


def _require_sys_flags(manifest: Mapping[str, Any]) -> dict[str, Any]:
    required = manifest["bootstrap"]["required_flags"]
    observed = {key: getattr(sys.flags, key) for key in required}
    if observed != dict(required) or bool(__debug__) is not False:
        raise RuntimeError(f"V3C isolated Python flags changed: {observed} != {required}.")
    return observed


def _require_orig_argv(*, phase: str) -> list[str]:
    expected = [
        "C:/Program Files/Calibre2/calibre-debug.exe",
        "-e",
        BOOTSTRAP_PATH.as_posix(),
        "--",
        "--phase",
        phase,
        "--config",
        CONFIG_PATH.as_posix(),
    ]
    observed = [str(value) for value in getattr(sys, "orig_argv", ())]
    if len(observed) != len(expected):
        raise RuntimeError(f"V3C bootstrap orig_argv length changed: {observed}.")
    if Path(observed[0]).resolve() != Path(expected[0]).resolve() or observed[1:] != expected[1:]:
        raise RuntimeError(f"V3C bootstrap was not launched by the canonical argv: {observed}.")
    return observed


def _scientific_module_census(modules: Mapping[str, Any], *, repo_root: Path = ROOT) -> list[str]:
    forbidden = (
        "dateutil",
        "numpy",
        "pandas",
        "pyarrow",
        "scripts",
        "six",
        "src",
        "tzdata",
        "yaml",
    )
    scientific_paths = {
        (repo_root / relative).resolve() for relative in EXPECTED_SCIENTIFIC_CLOSURE
    }
    loaded: list[str] = []
    for name, module in modules.items():
        by_name = any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden)
        raw_path = getattr(module, "__file__", None)
        by_path = raw_path is not None and Path(str(raw_path)).resolve() in scientific_paths
        if by_name or by_path:
            loaded.append(str(name))
    loaded.sort()
    return loaded


def _require_module_absence() -> list[str]:
    loaded = _scientific_module_census(sys.modules, repo_root=ROOT)
    if loaded:
        raise RuntimeError(f"Scientific modules loaded before V3C attestation: {loaded[:10]}.")
    if "sitecustomize" in sys.modules or "usercustomize" in sys.modules:
        raise RuntimeError("A site customization module ran before V3C attestation.")
    return loaded


def _activate_import_paths(manifest: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    _require_module_absence()
    site = (repo_root / ".venv" / "Lib" / "site-packages").resolve()
    if any((site / name).exists() for name in ("numpy.py", "pandas.py", "pyarrow.py", "src.py")):
        raise RuntimeError("Project site-packages contains a forbidden scientific shadow module.")
    if (site / "src").exists():
        raise RuntimeError("Project site-packages contains a forbidden shadow src package.")
    pycache = (repo_root / str(manifest["bootstrap"]["empty_pycache_directory"])).resolve()
    _require_directory_empty(pycache, label="V3C isolated pycache directory")
    sys.dont_write_bytecode = True
    sys.pycache_prefix = str(pycache)
    expected_pre = [
        str((repo_root / str(value)).resolve())
        for value in manifest["bootstrap"]["preimport_sys_path"]
    ]
    if [str(value) for value in sys.path] != expected_pre:
        raise RuntimeError(f"V3C preimport sys.path changed: {sys.path} != {expected_pre}.")
    original_meta = list(sys.meta_path)
    standard: list[Any] = [
        importlib.machinery.BuiltinImporter,
        importlib.machinery.FrozenImporter,
        importlib.machinery.PathFinder,
    ]
    custom = [finder for finder in original_meta if finder not in standard]
    sys.meta_path[:] = [*standard, *custom]
    sys.path[:] = [str(repo_root.resolve()), str(site)]
    expected_scientific = [
        str((repo_root / value).resolve()) for value in manifest["bootstrap"]["scientific_sys_path"]
    ]
    if sys.path != expected_scientific:
        raise RuntimeError("V3C scientific sys.path activation changed.")
    return {
        "preimport_sys_path": expected_pre,
        "scientific_sys_path": [
            str(value) for value in manifest["bootstrap"]["scientific_sys_path"]
        ],
        "pycache_directory": pycache.relative_to(repo_root).as_posix(),
        "pycache_empty": True,
        "meta_path_standard_precedence": [
            "BuiltinImporter",
            "FrozenImporter",
            "PathFinder",
        ],
    }


def _module_name_from_path(relative: Path) -> tuple[str, bool]:
    parts = list(relative.with_suffix("").parts)
    is_package = parts[-1] == "__init__"
    if is_package:
        parts.pop()
    return ".".join(parts), is_package


class _SealedSourceLoader:
    """Compile one authenticated local module from its already-sealed bytes."""

    _ijds_v3c_sealed_loader = True

    def __init__(
        self,
        *,
        fullname: str,
        relative: Path,
        payload: bytes,
        is_package: bool,
        all_sources: Mapping[Path, bytes],
        repo_root: Path,
    ) -> None:
        self.fullname = fullname
        self.relative = relative
        self.payload = payload
        self.package = is_package
        self.all_sources = all_sources
        self.repo_root = repo_root.resolve()

    def create_module(self, _spec: Any) -> None:
        return None

    def is_package(self, _fullname: str) -> bool:
        return self.package

    def exec_module(self, module: Any) -> None:
        filename = str((self.repo_root / self.relative).resolve())
        module.__file__ = filename
        module.__cached__ = None
        module.__dict__["_IJDS_V3C_SEALED_SOURCE_SHA256"] = hashlib.sha256(self.payload).hexdigest()
        code = compile(
            self.payload,
            filename,
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        )
        exec(code, module.__dict__)
        if self.relative == BOOTSTRAP_PATH:
            module.__dict__["_ACTIVE_SEALED_AUTHORITY_BYTES"] = dict(self.all_sources)


class _SealedSourceFinder:
    """Resolve every protocol-local import only from authenticated in-memory bytes."""

    _ijds_v3c_sealed_finder = True

    def __init__(self, sources: Mapping[Path, bytes], *, repo_root: Path) -> None:
        self.sources = dict(sources)
        self.repo_root = repo_root.resolve()
        self.modules: dict[str, tuple[Path, bytes, bool]] = {}
        for relative, payload in self.sources.items():
            if relative.suffix != ".py":
                continue
            fullname, is_package = _module_name_from_path(relative)
            self.modules[fullname] = (relative, payload, is_package)
        canonical = json.dumps(
            [
                [relative.as_posix(), len(payload), hashlib.sha256(payload).hexdigest()]
                for relative, payload in sorted(
                    self.sources.items(), key=lambda value: value[0].as_posix()
                )
            ],
            separators=(",", ":"),
        ).encode("utf-8")
        self.composite_sha256 = hashlib.sha256(canonical).hexdigest()

    def find_spec(
        self, fullname: str, _path: Any = None, _target: Any = None
    ) -> importlib.machinery.ModuleSpec | None:
        entry = self.modules.get(fullname)
        if fullname == "scripts.experiments":
            specification = importlib.machinery.ModuleSpec(
                fullname, loader=None, origin="v3c-sealed-namespace", is_package=True
            )
            specification.submodule_search_locations = []
            return specification
        if entry is None:
            if fullname == "src" or fullname.startswith("src."):
                raise ImportError(f"Local src import escaped the sealed V3C census: {fullname}.")
            if fullname == "scripts" or fullname.startswith("scripts."):
                raise ImportError(
                    f"Local scripts import escaped the sealed V3C census: {fullname}."
                )
            return None
        relative, payload, is_package = entry
        loader: Any = _SealedSourceLoader(
            fullname=fullname,
            relative=relative,
            payload=payload,
            is_package=is_package,
            all_sources=self.sources,
            repo_root=self.repo_root,
        )
        return importlib.util.spec_from_loader(
            fullname,
            loader,
            origin=str((self.repo_root / relative).resolve()),
            is_package=is_package,
        )


def _install_sealed_importer(
    sources: Mapping[Path, bytes], *, repo_root: Path
) -> _SealedSourceFinder:
    if any(getattr(value, "_ijds_v3c_sealed_finder", False) for value in sys.meta_path):
        raise RuntimeError("V3C sealed importer was installed more than once.")
    finder = _SealedSourceFinder(sources, repo_root=repo_root)
    pathfinder_index = sys.meta_path.index(importlib.machinery.PathFinder)
    sys.meta_path.insert(pathfinder_index, finder)
    return finder


def require_sealed_import_runtime(
    sealed_sources: Mapping[Path, bytes], *, repo_root: Path
) -> dict[str, Any]:
    finders = [value for value in sys.meta_path if getattr(value, "_ijds_v3c_sealed_finder", False)]
    if len(finders) != 1:
        raise RuntimeError("V3C sealed importer is missing or ambiguous.")
    expected = _SealedSourceFinder(sealed_sources, repo_root=repo_root)
    observed = finders[0]
    if (
        getattr(observed, "composite_sha256", None) != expected.composite_sha256
        or getattr(observed, "repo_root", None) != repo_root.resolve()
    ):
        raise RuntimeError("V3C sealed importer bytes or repository root changed.")
    loaded: dict[str, str] = {}
    namespace = sys.modules.get("scripts.experiments")
    if namespace is not None and (
        getattr(getattr(namespace, "__spec__", None), "origin", None) != "v3c-sealed-namespace"
        or list(getattr(namespace, "__path__", ())) != []
    ):
        raise RuntimeError("V3C scripts.experiments namespace was not sealed explicitly.")
    for relative in (BOOTSTRAP_PATH, *EXPECTED_SCIENTIFIC_CLOSURE):
        if relative == RUNNER_PATH:
            continue
        fullname, _is_package = _module_name_from_path(relative)
        module = sys.modules.get(fullname)
        if module is None:
            continue
        loader = getattr(module, "__loader__", None)
        expected_sha = hashlib.sha256(sealed_sources[relative]).hexdigest()
        if (
            not getattr(loader, "_ijds_v3c_sealed_loader", False)
            or getattr(module, "_IJDS_V3C_SEALED_SOURCE_SHA256", None) != expected_sha
            or Path(str(getattr(module, "__file__", ""))).resolve()
            != (repo_root / relative).resolve()
        ):
            raise RuntimeError(f"V3C local module did not execute from sealed bytes: {fullname}.")
        loaded[fullname] = relative.as_posix()
    return {
        "finder_composite_sha256": expected.composite_sha256,
        "loaded_sealed_modules": loaded,
    }


def build_bootstrap_attestation(
    *, phase: str, config_path: Path, repo_root: Path = ROOT
) -> dict[str, Any]:
    """Authenticate the execution substrate without importing scientific code."""
    root = repo_root.resolve()
    if Path.cwd().resolve() != root:
        raise RuntimeError(f"V3C bootstrap requires cwd={root}.")
    if config_path.as_posix() != CONFIG_PATH.as_posix():
        raise RuntimeError(f"V3C bootstrap accepts only {CONFIG_PATH.as_posix()}.")
    expected_entrypoint_path = [str((root / BOOTSTRAP_PATH.parent).resolve())]
    observed_entrypoint_path = [str(Path(value).resolve()) for value in sys.path]
    if observed_entrypoint_path != expected_entrypoint_path:
        raise RuntimeError(
            "V3C bootstrap requires only Calibre -e's root-bound script directory: "
            f"{observed_entrypoint_path} != {expected_entrypoint_path}."
        )
    initial_scientific_modules = _require_module_absence()
    for specification in ROOT_TRUST_FILES:
        _require_file_descriptor(specification, label="V3C bootstrap root-of-trust file")
    if (
        str(
            subprocess.run(
                [str(GIT_EXECUTABLE), "--version"],
                env=_git_environment(),
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        ).strip()
        != GIT_VERSION
    ):
        raise RuntimeError("V3C bootstrap root Git version changed.")
    git_root = _require_git_root(root)
    head_tag = PROTOCOL_TAG if phase in {"attest-only", "compute"} else ARTIFACT_TAG
    head = _require_clean_tag(root, head_tag)
    protocol_commit = _resolve_strict_tag(root, PROTOCOL_TAG)
    _require_v3c_protocol_parent(protocol_commit=protocol_commit, repo_root=root)
    authority, sealed = _require_authority_blobs(repo_root=root, protocol_commit=protocol_commit)
    _ACTIVE_SEALED_AUTHORITY_BYTES.clear()
    _ACTIVE_SEALED_AUTHORITY_BYTES.update(sealed)
    manifest = _load_runtime_manifest(repo_root=root, sealed_bytes=sealed[RUNTIME_MANIFEST_PATH])
    environment = _require_forbidden_environment(manifest)
    flags = _require_sys_flags(manifest)
    orig_argv = _require_orig_argv(phase=phase)
    locale.setlocale(locale.LC_TIME, "C")
    locale.setlocale(locale.LC_NUMERIC, "C")
    locale_observed = {
        "lc_time": locale.setlocale(locale.LC_TIME),
        "lc_numeric": locale.setlocale(locale.LC_NUMERIC),
        "timezone_names": list(time.tzname),
    }
    if locale_observed != manifest["bootstrap"]["locale"]:
        raise RuntimeError(f"V3C locale or timezone changed: {locale_observed}.")
    runtime_files = _require_runtime_files(manifest)
    calibre_native_directory = _directory_file_seal(CALIBRE_NATIVE_ROOT)
    if calibre_native_directory != manifest["calibre"]["native_directory"]:
        raise RuntimeError("Complete Calibre native directory inventory changed.")
    initial_native_modules = require_loaded_native_modules(manifest, repo_root=root)
    config_directory = (root / str(manifest["bootstrap"]["calibre_config_directory"])).resolve()
    if Path(os.environ.get("CALIBRE_CONFIG_DIRECTORY", "")).resolve() != config_directory:
        raise RuntimeError("V3C CALIBRE_CONFIG_DIRECTORY changed.")
    calibre_config = _calibre_config_seal(manifest, repo_root=root)
    calibre_cache = _calibre_cache_seal(manifest, repo_root=root)
    distributions = {
        name: _distribution_seal(name, repo_root=root) for name in manifest["distributions"]
    }
    if distributions != manifest["distributions"]:
        raise RuntimeError("V3C installed distribution files changed before import.")
    path_activation = _activate_import_paths(manifest, repo_root=root)
    _install_sealed_importer(sealed, repo_root=root)
    sealed_importer = require_sealed_import_runtime(sealed, repo_root=root)
    initial_module_origins = require_loaded_module_origins(manifest, sealed, repo_root=root)
    attestation = {
        "schema_version": "2026-07-26.3c-bootstrap-1",
        "phase": phase,
        "protocol_commit": protocol_commit,
        "head_tag": head_tag,
        "head": head,
        "git_root": git_root,
        "authority": authority,
        "runtime_manifest": _descriptor_from_bytes(
            sealed[RUNTIME_MANIFEST_PATH], relative_path=RUNTIME_MANIFEST_PATH.as_posix()
        ),
        "runtime_files": runtime_files,
        "calibre_native_directory": calibre_native_directory,
        "initial_native_modules": initial_native_modules,
        "environment": environment,
        "flags": flags,
        "orig_argv": orig_argv,
        "locale": locale_observed,
        "calibre_config": calibre_config,
        "calibre_cache": calibre_cache,
        "distributions": distributions,
        "path_activation": path_activation,
        "sealed_importer": sealed_importer,
        "initial_module_origins": initial_module_origins,
        "initial_scientific_modules": initial_scientific_modules,
    }
    return attestation


def revalidate_bootstrap_attestation(
    attestation: Mapping[str, Any], *, repo_root: Path = ROOT
) -> dict[str, Any]:
    """Repeat the byte/environment substrate checks before a terminal seal."""
    root = repo_root.resolve()
    if attestation.get("schema_version") != "2026-07-26.3c-bootstrap-1":
        raise RuntimeError("V3C bootstrap attestation is absent or malformed.")
    phase = str(attestation.get("phase", ""))
    if phase not in {"compute", "verify-artifact"}:
        raise RuntimeError("V3C bootstrap attestation phase is invalid.")
    protocol_commit = _resolve_strict_tag(root, PROTOCOL_TAG)
    _require_v3c_protocol_parent(protocol_commit=protocol_commit, repo_root=root)
    authority, current_sealed = _require_authority_blobs(
        repo_root=root, protocol_commit=protocol_commit
    )
    if current_sealed != _ACTIVE_SEALED_AUTHORITY_BYTES:
        raise RuntimeError("V3C executing sealed bytes differ from the current Git authority.")
    manifest = _load_runtime_manifest(
        repo_root=root, sealed_bytes=current_sealed[RUNTIME_MANIFEST_PATH]
    )
    for specification in ROOT_TRUST_FILES:
        _require_file_descriptor(specification, label="V3C bootstrap root-of-trust file")
    git_root = _require_git_root(root)
    head_tag = PROTOCOL_TAG if phase == "compute" else ARTIFACT_TAG
    head = _require_clean_tag(root, head_tag)
    runtime_files = _require_runtime_files(manifest)
    calibre_native_directory = _directory_file_seal(CALIBRE_NATIVE_ROOT)
    if calibre_native_directory != manifest["calibre"]["native_directory"]:
        raise RuntimeError("Complete Calibre native directory inventory drifted after import.")
    native_modules = require_loaded_native_modules(manifest, repo_root=root)
    module_origins = require_loaded_module_origins(manifest, current_sealed, repo_root=root)
    environment = _require_forbidden_environment(manifest)
    flags = _require_sys_flags(manifest)
    calibre_config = _calibre_config_seal(manifest, repo_root=root)
    calibre_cache = _calibre_cache_seal(manifest, repo_root=root)
    distributions = {
        name: _distribution_seal(name, repo_root=root) for name in manifest["distributions"]
    }
    if distributions != manifest["distributions"]:
        raise RuntimeError("V3C installed distribution files drifted after import.")
    pycache = (root / str(manifest["bootstrap"]["empty_pycache_directory"])).resolve()
    _require_directory_empty(pycache, label="V3C isolated pycache directory")
    orig_argv = _require_orig_argv(phase=phase)
    locale.setlocale(locale.LC_TIME, "C")
    locale.setlocale(locale.LC_NUMERIC, "C")
    locale_observed = {
        "lc_time": locale.setlocale(locale.LC_TIME),
        "lc_numeric": locale.setlocale(locale.LC_NUMERIC),
        "timezone_names": list(time.tzname),
    }
    sealed_importer = require_sealed_import_runtime(current_sealed, repo_root=root)
    runtime_manifest = _descriptor_from_bytes(
        current_sealed[RUNTIME_MANIFEST_PATH], relative_path=RUNTIME_MANIFEST_PATH.as_posix()
    )
    observed = {
        "protocol_commit": protocol_commit,
        "head_tag": head_tag,
        "head": head,
        "git_root": git_root,
        "authority": authority,
        "runtime_manifest": runtime_manifest,
        "runtime_files": runtime_files,
        "calibre_native_directory": calibre_native_directory,
        "environment": environment,
        "flags": flags,
        "orig_argv": orig_argv,
        "locale": locale_observed,
        "calibre_config": calibre_config,
        "calibre_cache": calibre_cache,
        "distributions": distributions,
    }
    for key, value in observed.items():
        if attestation.get(key) != value:
            raise RuntimeError(f"V3C bootstrap attestation drifted on {key}.")
    initial_native = attestation.get("initial_native_modules")
    if not isinstance(initial_native, Mapping) or any(
        native_modules.get(str(name)) != descriptor for name, descriptor in initial_native.items()
    ):
        raise RuntimeError("V3C initially loaded native-module inventory drifted.")
    initial_importer = attestation.get("sealed_importer")
    if (
        not isinstance(initial_importer, Mapping)
        or initial_importer.get("finder_composite_sha256")
        != sealed_importer["finder_composite_sha256"]
    ):
        raise RuntimeError("V3C sealed importer drifted after scientific imports.")
    terminal = dict(attestation)
    terminal["terminal_native_modules"] = native_modules
    terminal["terminal_module_origins"] = module_origins
    terminal["terminal_sealed_importer"] = sealed_importer
    terminal["terminal_revalidated"] = True
    return terminal


def revalidate_attest_only_entrypoint(
    attestation: Mapping[str, Any], *, repo_root: Path = ROOT
) -> dict[str, Any]:
    """Re-measure the pre-science carrier and all no-mutation attest-only state."""
    root = repo_root.resolve()
    terminal_scientific_modules = _require_module_absence()
    protocol_commit = str(attestation["protocol_commit"])
    _authority, current_sealed = _require_authority_blobs(
        repo_root=root, protocol_commit=protocol_commit
    )
    if current_sealed != _ACTIVE_SEALED_AUTHORITY_BYTES:
        raise RuntimeError("V3C authority bytes changed during attest-only.")
    manifest = _load_runtime_manifest(
        repo_root=root, sealed_bytes=current_sealed[RUNTIME_MANIFEST_PATH]
    )
    terminal_origins = require_loaded_module_origins(manifest, current_sealed, repo_root=root)
    if terminal_origins != attestation["initial_module_origins"]:
        raise RuntimeError("V3C module origins changed during attest-only.")
    if terminal_scientific_modules != attestation["initial_scientific_modules"]:
        raise RuntimeError("V3C scientific-module census changed during attest-only.")
    if _calibre_config_seal(manifest, repo_root=root) != attestation["calibre_config"]:
        raise RuntimeError("V3C Calibre configuration changed during attest-only.")
    if _calibre_cache_seal(manifest, repo_root=root) != attestation["calibre_cache"]:
        raise RuntimeError("V3C Calibre cache changed during attest-only.")
    pycache = (root / str(manifest["bootstrap"]["empty_pycache_directory"])).resolve()
    _require_directory_empty(pycache, label="V3C isolated pycache directory")
    if _require_clean_tag(root, PROTOCOL_TAG) != attestation["head"]:
        raise RuntimeError("V3C Git state changed during attest-only.")
    return {
        "module_origins": terminal_origins,
        "scientific_modules": terminal_scientific_modules,
    }


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    attestation = build_bootstrap_attestation(
        phase=str(args.phase), config_path=args.config, repo_root=ROOT
    )
    if args.phase == "attest-only":
        terminal = revalidate_attest_only_entrypoint(attestation, repo_root=ROOT)
        terminal_origins = terminal["module_origins"]
        terminal_scientific_modules = terminal["scientific_modules"]
        print(
            json.dumps(
                {
                    "status": "complete_pre_science_entrypoint_attestation",
                    "schema_version": attestation["schema_version"],
                    "phase": attestation["phase"],
                    "protocol_commit": attestation["protocol_commit"],
                    "head_tag": attestation["head_tag"],
                    "authority_files": len(attestation["authority"]["source_files"]),
                    "calibre_global": attestation["calibre_config"]["global"],
                    "calibre_entrypoint_carrier": terminal_origins["calibre_entrypoint_carrier"],
                    "preimport_sys_path": [BOOTSTRAP_PATH.parent.as_posix()],
                    "scientific_module_census": terminal_scientific_modules,
                    "scientific_modules_loaded": bool(terminal_scientific_modules),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return
    sys.argv = [
        RUNNER_PATH.as_posix(),
        "--phase",
        str(args.phase),
        "--config",
        CONFIG_PATH.as_posix(),
    ]
    runner_payload = _ACTIVE_SEALED_AUTHORITY_BYTES[RUNNER_PATH]
    runner_filename = str((ROOT / RUNNER_PATH).resolve())
    runner_globals: dict[str, Any] = {
        "__name__": "__main__",
        "__file__": runner_filename,
        "__package__": None,
        "__cached__": None,
        "__builtins__": __builtins__,
        "_IJDS_V3C_BOOTSTRAP_ATTESTATION": attestation,
        "_IJDS_V3C_SEALED_AUTHORITY_BYTES": {
            path.as_posix(): payload for path, payload in _ACTIVE_SEALED_AUTHORITY_BYTES.items()
        },
        "_IJDS_V3C_RUNNER_EXECUTED_FROM_SEALED_BYTES": True,
    }
    exec(
        compile(
            runner_payload,
            runner_filename,
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        ),
        runner_globals,
    )


if __name__ == "__main__":
    main()
