"""Load and verify the single active paper-evidence source registry."""

from __future__ import annotations

import hashlib
import posixpath
import re
import subprocess
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from src.utils.artifact_descriptor import relative_artifact_descriptor

_REGISTRY_SECTIONS = ("lineages", "diagnostics", "sensitivities", "replay_dependencies")
_IDENTITY_MARKERS = frozenset(
    {
        "run_tag",
        "protocol_tag",
        "protocol_commit",
        "scientific_uv_lock_sha256",
        "status",
        "paper_role",
        "dvc_tracked",
        "dvc_roots",
        "freeze_sha256",
    }
)
_LEGACY_DVC_PHASES = frozenset({"outcome_free", "evaluation"})
_DVC_ROOTS = ("data/processed", "models")
_PROTOCOL_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_DVC_DIRECTORY_MD5_PATTERN = re.compile(r"[0-9a-f]{32}\.dir")


@dataclass(frozen=True)
class _RegistryUnit:
    location: tuple[str, ...]
    run_tag: str
    protocol_tag: str | None
    protocol_commit: str | None
    scientific_uv_lock_sha256: str | None
    paper_role: str | None
    declared_dvc_tracked: bool | None
    dvc_roots: tuple[str, ...] | None


def load_source_registry(
    path: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Load and structurally validate the active source registry.

    Passing ``repo_root`` additionally validates the contents of every declared
    DVC pointer. The optional argument preserves the structural-only API used by
    lightweight DVC target discovery.
    """
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Active evidence source registry must be a mapping.")
    if payload.get("status") != "active_ijds_paper_evidence_source_registry":
        raise ValueError("Unexpected active evidence source registry status.")

    units = _validated_registry_units(payload)
    tracked_units = _dvc_tracked_units(units)
    pointers = payload.get("dvc_pointers")
    if not isinstance(pointers, list) or not all(
        isinstance(item, str) and bool(item) for item in pointers
    ):
        raise TypeError("Active evidence source registry dvc_pointers must be a string list.")

    expected = {
        f"{prefix}/experiments/ijds_audit/{unit.run_tag}.dvc"
        for unit in tracked_units
        for prefix in (unit.dvc_roots or _DVC_ROOTS)
    }
    actual = set(pointers)
    if actual != expected or len(pointers) != len(expected):
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        details = f" Missing: {missing}; unexpected: {unexpected}."
        raise ValueError(
            "Active DVC pointers do not match the DVC-tracked registry units." + details
        )

    if repo_root is not None:
        _verify_dvc_pointers(pointers, repo_root=repo_root)
        _verify_protocol_replay_contracts(units, repo_root=repo_root)
    return payload


def active_lineage_run_tags(payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Return DVC-tracked run tags in causal/config declaration order."""
    units = _validated_registry_units(payload)
    return tuple(unit.run_tag for unit in _dvc_tracked_units(units))


def load_verified_source_registry(
    path: Path,
    *,
    repo_root: Path,
) -> tuple[dict[str, Any], dict[str, Path]]:
    """Return registry metadata and hash-verified source paths."""
    payload = load_source_registry(path, repo_root=repo_root)
    sources = payload.get("sources")
    if not isinstance(sources, Mapping) or not sources:
        raise ValueError("Active evidence source registry is empty.")
    verified: dict[str, Path] = {}
    seen_paths: set[str] = set()
    for name, raw_descriptor in sources.items():
        if not isinstance(raw_descriptor, Mapping):
            raise TypeError(f"Evidence source descriptor {name!r} must be a mapping.")
        descriptor = dict(raw_descriptor)
        descriptor_path = descriptor.get("path")
        if not isinstance(descriptor_path, str) or not descriptor_path:
            raise TypeError(f"Evidence source descriptor {name!r} omits path.")
        source_path = (repo_root / descriptor_path).resolve()
        source_path.relative_to(repo_root.resolve())
        actual = relative_artifact_descriptor(source_path, repo_root=repo_root)
        for field in ("path", "bytes", "sha256"):
            if actual[field] != descriptor.get(field):
                raise RuntimeError(f"Evidence source {name!r} mismatched on {field}.")
        if actual["path"] in seen_paths:
            raise ValueError(f"Duplicate active evidence source path: {actual['path']}")
        seen_paths.add(str(actual["path"]))
        verified[str(name)] = source_path
    return payload, verified


def _validated_registry_units(payload: Mapping[str, Any]) -> tuple[_RegistryUnit, ...]:
    lineages = payload.get("lineages")
    if not isinstance(lineages, Mapping):
        raise TypeError("Active evidence source registry omits lineages.")

    units = list(_walk_registry_group(lineages, location=("lineages",)))
    for section in _REGISTRY_SECTIONS[1:]:
        if section not in payload:
            continue
        section_payload = payload[section]
        if not isinstance(section_payload, Mapping):
            raise TypeError(f"Active evidence source registry {section} must be a mapping.")
        units.extend(_walk_registry_group(section_payload, location=(section,)))
    if not units:
        raise ValueError("Active evidence source registry declares no identities.")

    uses_explicit_contract = any(
        unit.paper_role is not None or unit.declared_dvc_tracked is not None for unit in units
    )
    if uses_explicit_contract:
        incomplete = [
            _format_location(unit.location)
            for unit in units
            if unit.paper_role is None or unit.declared_dvc_tracked is None
        ]
        if incomplete:
            raise TypeError(
                "Explicit registry identities require both paper_role and dvc_tracked: "
                f"{incomplete}."
            )

    seen_run_tags: dict[str, tuple[str, ...]] = {}
    seen_protocol_tags: dict[str, tuple[str, ...]] = {}
    for unit in units:
        previous = seen_run_tags.get(unit.run_tag)
        if previous is not None:
            raise ValueError(
                "Active evidence registry run tags must be globally unique: "
                f"{unit.run_tag!r} appears at {_format_location(previous)} and "
                f"{_format_location(unit.location)}."
            )
        seen_run_tags[unit.run_tag] = unit.location
        if unit.protocol_tag is None:
            continue
        previous = seen_protocol_tags.get(unit.protocol_tag)
        if previous is not None:
            raise ValueError(
                "Active evidence registry protocol tags must be globally unique: "
                f"{unit.protocol_tag!r} appears at {_format_location(previous)} and "
                f"{_format_location(unit.location)}."
            )
        seen_protocol_tags[unit.protocol_tag] = unit.location
    return tuple(units)


def _walk_registry_group(
    group: Mapping[str, Any],
    *,
    location: tuple[str, ...],
) -> Iterator[_RegistryUnit]:
    if _looks_like_identity(group):
        yield _parse_registry_unit(group, location=location)
        return
    if not group:
        raise TypeError(f"Registry identity group {_format_location(location)} is empty.")

    for raw_name, child in group.items():
        if not isinstance(raw_name, str) or not raw_name:
            raise TypeError(
                f"Registry identity group {_format_location(location)} has an invalid name."
            )
        child_location = (*location, raw_name)
        if not isinstance(child, Mapping):
            raise TypeError(
                f"Registry identity {_format_location(child_location)} must be a mapping."
            )
        yield from _walk_registry_group(child, location=child_location)


def _looks_like_identity(payload: Mapping[str, Any]) -> bool:
    return not payload or any(field in payload for field in _IDENTITY_MARKERS)


def _parse_registry_unit(
    identity: Mapping[str, Any],
    *,
    location: tuple[str, ...],
) -> _RegistryUnit:
    run_tag = _required_text(identity, "run_tag", location=location)
    if run_tag in {".", ".."} or "/" in run_tag or "\\" in run_tag:
        raise ValueError(
            f"Registry identity {_format_location(location)}.run_tag must name one directory."
        )

    has_protocol_tag = "protocol_tag" in identity
    has_protocol_commit = "protocol_commit" in identity
    if has_protocol_tag != has_protocol_commit:
        missing_field = "protocol_commit" if has_protocol_tag else "protocol_tag"
        raise TypeError(
            f"Missing registry identity: {_format_location((*location, missing_field))}."
        )

    protocol_tag: str | None = None
    protocol_commit: str | None = None
    scientific_uv_lock_sha256: str | None = None
    if has_protocol_tag:
        protocol_tag = _required_text(identity, "protocol_tag", location=location)
        protocol_commit = _required_text(identity, "protocol_commit", location=location)
        if _PROTOCOL_COMMIT_PATTERN.fullmatch(protocol_commit) is None:
            raise ValueError(
                f"Registry identity {_format_location(location)}.protocol_commit "
                "must be a 40-character lowercase hexadecimal commit."
            )
        scientific_uv_lock_sha256 = _required_text(
            identity,
            "scientific_uv_lock_sha256",
            location=location,
        )
        if _SHA256_PATTERN.fullmatch(scientific_uv_lock_sha256) is None:
            raise ValueError(
                f"Registry identity {_format_location(location)}.scientific_uv_lock_sha256 "
                "must be a 64-character lowercase hexadecimal digest."
            )
    else:
        _required_text(identity, "status", location=location)
        if "scientific_uv_lock_sha256" in identity:
            raise ValueError(
                f"Registry identity {_format_location(location)} cannot declare a scientific "
                "lock without a protocol commit."
            )

    if "status" in identity:
        _required_text(identity, "status", location=location)
    paper_role = None
    if "paper_role" in identity:
        paper_role = _required_text(identity, "paper_role", location=location)

    declared_dvc_tracked: bool | None = None
    if "dvc_tracked" in identity:
        raw_dvc_tracked = identity["dvc_tracked"]
        if not isinstance(raw_dvc_tracked, bool):
            raise TypeError(
                f"Registry identity {_format_location(location)}.dvc_tracked must be boolean."
            )
        declared_dvc_tracked = raw_dvc_tracked
    dvc_roots: tuple[str, ...] | None = None
    if "dvc_roots" in identity:
        raw_roots = identity["dvc_roots"]
        if declared_dvc_tracked is not True:
            raise ValueError(
                f"Registry identity {_format_location(location)}.dvc_roots requires "
                "dvc_tracked=true."
            )
        if (
            not isinstance(raw_roots, list)
            or not raw_roots
            or not all(isinstance(value, str) and value in _DVC_ROOTS for value in raw_roots)
            or len(raw_roots) != len(set(raw_roots))
        ):
            raise ValueError(
                f"Registry identity {_format_location(location)}.dvc_roots must be a "
                f"nonempty unique subset of {list(_DVC_ROOTS)}."
            )
        dvc_roots = tuple(raw_roots)
    return _RegistryUnit(
        location=location,
        run_tag=run_tag,
        protocol_tag=protocol_tag,
        protocol_commit=protocol_commit,
        scientific_uv_lock_sha256=scientific_uv_lock_sha256,
        paper_role=paper_role,
        declared_dvc_tracked=declared_dvc_tracked,
        dvc_roots=dvc_roots,
    )


def _required_text(
    payload: Mapping[str, Any],
    field: str,
    *,
    location: tuple[str, ...],
) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value or value != value.strip():
        raise TypeError(f"Missing registry identity: {_format_location((*location, field))}.")
    return value


def _dvc_tracked_units(units: tuple[_RegistryUnit, ...]) -> tuple[_RegistryUnit, ...]:
    uses_explicit_tracking = any(unit.declared_dvc_tracked is not None for unit in units)
    if uses_explicit_tracking:
        return tuple(unit for unit in units if unit.declared_dvc_tracked is True)
    return tuple(unit for unit in units if _legacy_dvc_tracked(unit))


def _legacy_dvc_tracked(unit: _RegistryUnit) -> bool:
    middle = set(unit.location[1:-1])
    return (
        unit.location[0] == "lineages"
        and unit.location[-1] in _LEGACY_DVC_PHASES
        and not middle.intersection({"diagnostics", "sensitivities"})
    )


def _verify_dvc_pointers(pointers: list[str], *, repo_root: Path) -> None:
    resolved_root = repo_root.resolve()
    for pointer in pointers:
        pointer_path = (resolved_root / pointer).resolve()
        try:
            pointer_path.relative_to(resolved_root)
        except ValueError as exc:
            raise ValueError(f"Active DVC pointer escapes the repository: {pointer}") from exc
        if pointer_path.suffix != ".dvc" or not pointer_path.is_file():
            raise FileNotFoundError(f"Invalid active DVC pointer: {pointer_path}")
        _verify_dvc_pointer(pointer_path, display_path=pointer)


def _verify_protocol_replay_contracts(units: tuple[_RegistryUnit, ...], *, repo_root: Path) -> None:
    """Verify every protocol tag and the environment lock stored at that commit."""
    if not (repo_root / ".git").exists():
        return
    for unit in units:
        if (
            unit.protocol_tag is None
            or unit.protocol_commit is None
            or unit.scientific_uv_lock_sha256 is None
        ):
            continue
        tag_result = subprocess.run(
            ["git", "rev-list", "-n", "1", unit.protocol_tag],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        resolved = tag_result.stdout.strip()
        if tag_result.returncode != 0 or resolved != unit.protocol_commit:
            raise RuntimeError(
                f"Registry protocol tag {unit.protocol_tag!r} does not resolve to "
                f"declared commit {unit.protocol_commit}."
            )
        lock_result = subprocess.run(
            ["git", "show", f"{unit.protocol_commit}:uv.lock"],
            cwd=repo_root,
            check=False,
            capture_output=True,
        )
        if lock_result.returncode != 0:
            raise RuntimeError(
                f"Registry protocol commit {unit.protocol_commit} does not contain uv.lock."
            )
        actual_lock_sha256 = hashlib.sha256(lock_result.stdout).hexdigest()
        if actual_lock_sha256 != unit.scientific_uv_lock_sha256:
            raise RuntimeError(
                f"Registry protocol tag {unit.protocol_tag!r} declares uv.lock "
                f"{unit.scientific_uv_lock_sha256}, but its commit contains "
                f"{actual_lock_sha256}."
            )


def _verify_dvc_pointer(path: Path, *, display_path: str) -> None:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed active DVC pointer YAML: {display_path}") from exc
    if not isinstance(payload, Mapping):
        raise TypeError(f"Active DVC pointer {display_path} must be a mapping.")

    outs = payload.get("outs")
    if not isinstance(outs, list) or len(outs) != 1:
        raise ValueError(f"Active DVC pointer {display_path} must declare exactly one out.")
    out = outs[0]
    if not isinstance(out, Mapping):
        raise TypeError(f"Active DVC pointer {display_path} out must be a mapping.")

    raw_out_path = out.get("path")
    if not isinstance(raw_out_path, str) or not raw_out_path:
        raise TypeError(f"Active DVC pointer {display_path} out path must be a string.")
    normalized_out_path = _normalize_dvc_out_path(raw_out_path, display_path=display_path)
    if normalized_out_path != path.stem:
        raise ValueError(
            f"Active DVC pointer {display_path} out path {normalized_out_path!r} "
            f"does not match run directory {path.stem!r}."
        )

    md5 = out.get("md5")
    if not isinstance(md5, str) or _DVC_DIRECTORY_MD5_PATTERN.fullmatch(md5) is None:
        raise ValueError(
            f"Active DVC pointer {display_path} md5 must be a lowercase DVC directory hash."
        )
    if "hash" in out and out["hash"] != "md5":
        raise ValueError(f"Active DVC pointer {display_path} hash must be 'md5'.")
    _validate_nonnegative_integer(out, "size", display_path=display_path)
    _validate_nonnegative_integer(out, "nfiles", display_path=display_path)


def _normalize_dvc_out_path(value: str, *, display_path: str) -> str:
    normalized = posixpath.normpath(value.replace("\\", "/"))
    normalized_path = PurePosixPath(normalized)
    if (
        normalized in {"", ".", ".."}
        or normalized_path.is_absolute()
        or normalized.startswith("../")
    ):
        raise ValueError(f"Active DVC pointer {display_path} out path must be relative.")
    return normalized_path.as_posix()


def _validate_nonnegative_integer(
    payload: Mapping[str, Any],
    field: str,
    *,
    display_path: str,
) -> None:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(
            f"Active DVC pointer {display_path} {field} must be a non-negative integer."
        )


def _format_location(location: tuple[str, ...]) -> str:
    return ".".join(location)
