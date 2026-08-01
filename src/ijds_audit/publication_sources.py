"""Load and verify the single active paper-evidence source registry."""

from __future__ import annotations

import hashlib
import posixpath
import re
import subprocess
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Any, cast

import yaml

from src.utils.artifact_descriptor import relative_artifact_descriptor

_REGISTRY_SECTIONS = ("lineages", "diagnostics", "sensitivities", "replay_dependencies")
_IDENTITY_MARKERS = frozenset(
    {
        "run_tag",
        "protocol_tag",
        "protocol_commit",
        "protocol_bundle",
        "scientific_uv_lock_sha256",
        "status",
        "paper_role",
        "dvc_tracked",
        "dvc_roots",
        "freeze_sha256",
        "artifact_tag",
        "artifact_commit",
        "artifact_parent_commit",
        "artifact_transport",
        "artifact_paths",
        "source_artifact_tag",
        "source_artifact_commit",
        "source_artifact_parent_commit",
        "source_artifact_transport",
        "source_artifact_paths",
    }
)
_LEGACY_DVC_PHASES = frozenset({"outcome_free", "evaluation"})
_DVC_ROOTS = ("data/processed", "models")
_PROTOCOL_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_DVC_DIRECTORY_MD5_PATTERN = re.compile(r"[0-9a-f]{32}\.dir")
_GIT_ARTIFACT_TRANSPORT = "git_force_tracked_direct_child_commit"


@dataclass(frozen=True)
class _RegistryUnit:
    location: tuple[str, ...]
    run_tag: str
    protocol_tag: str | None
    protocol_commit: str | None
    protocol_bundle: str | None
    scientific_uv_lock_sha256: str | None
    paper_role: str | None
    declared_dvc_tracked: bool | None
    dvc_roots: tuple[str, ...] | None
    source_artifact_tag: str | None
    source_artifact_commit: str | None
    source_artifact_parent_commit: str | None
    source_artifact_transport: str | None
    source_artifact_paths: tuple[str, ...] | None
    artifact_tag: str | None
    artifact_commit: str | None
    artifact_parent_commit: str | None
    artifact_transport: str | None
    artifact_paths: tuple[str, ...] | None


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
    descriptors_by_path: dict[str, Mapping[str, Any]] = {}
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
        descriptors_by_path[str(actual["path"])] = descriptor
        verified[str(name)] = source_path
    units = _validated_registry_units(payload)
    _verify_source_transport(
        source_paths=tuple(seen_paths),
        dvc_pointers=payload["dvc_pointers"],
        git_artifact_paths=tuple(
            path
            for unit in units
            for path in (*(unit.source_artifact_paths or ()), *(unit.artifact_paths or ()))
        ),
        repo_root=repo_root,
    )
    _verify_two_stage_git_blob_descriptors(
        units=units,
        descriptors_by_path=descriptors_by_path,
        repo_root=repo_root,
    )
    return payload, verified


def load_verified_or_sealed_source_registry(
    path: Path,
    *,
    repo_root: Path,
    sealed_parent_commit: str,
    sealed_parent_registry_path: str,
) -> tuple[dict[str, Any], dict[str, Path], tuple[str, ...]]:
    """Verify present sources and pin absent DVC sources to a sealed registry.

    This is a narrow development-time bridge for an additive Git-native
    publication extension when the historical DVC cache is unavailable.  It
    never accepts an absent Git source, a changed descriptor, or a source
    outside an active DVC output.  Strict submission rebuilds continue to use
    :func:`load_verified_source_registry` and therefore require all bytes.
    """
    if _PROTOCOL_COMMIT_PATTERN.fullmatch(sealed_parent_commit) is None:
        raise ValueError("The sealed parent registry commit must be a full Git commit.")
    relative_parent = PurePosixPath(sealed_parent_registry_path)
    if (
        not sealed_parent_registry_path
        or relative_parent.is_absolute()
        or ".." in relative_parent.parts
        or relative_parent.as_posix() != sealed_parent_registry_path
    ):
        raise ValueError("The sealed parent registry path must be repository-relative.")

    parent_probe = subprocess.run(
        ["git", "show", f"{sealed_parent_commit}:{sealed_parent_registry_path}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if parent_probe.returncode != 0:
        raise RuntimeError("The sealed parent source registry Git blob is absent.")
    parent = yaml.safe_load(parent_probe.stdout)
    if not isinstance(parent, Mapping) or not isinstance(parent.get("sources"), Mapping):
        raise TypeError("The sealed parent source registry is malformed.")
    parent_sources = cast(Mapping[str, Any], parent["sources"])

    payload = load_source_registry(path, repo_root=repo_root)
    sources = payload.get("sources")
    if not isinstance(sources, Mapping) or not sources:
        raise ValueError("Active evidence source registry is empty.")
    dvc_roots = tuple(
        PurePosixPath(pointer).parent.joinpath(PurePosixPath(pointer).stem).as_posix()
        for pointer in payload["dvc_pointers"]
    )
    registered: dict[str, Path] = {}
    missing: list[str] = []
    seen_paths: set[str] = set()
    descriptors_by_path: dict[str, Mapping[str, Any]] = {}
    for name, raw_descriptor in sources.items():
        if not isinstance(raw_descriptor, Mapping):
            raise TypeError(f"Evidence source descriptor {name!r} must be a mapping.")
        descriptor = dict(raw_descriptor)
        descriptor_path = descriptor.get("path")
        if not isinstance(descriptor_path, str) or not descriptor_path:
            raise TypeError(f"Evidence source descriptor {name!r} omits path.")
        source_path = (repo_root / descriptor_path).resolve()
        source_path.relative_to(repo_root.resolve())
        if descriptor_path in seen_paths:
            raise ValueError(f"Duplicate active evidence source path: {descriptor_path}")
        seen_paths.add(descriptor_path)
        descriptors_by_path[descriptor_path] = descriptor
        registered[str(name)] = source_path
        if source_path.is_file():
            if relative_artifact_descriptor(source_path, repo_root=repo_root) != descriptor:
                raise RuntimeError(f"Evidence source {name!r} mismatched its descriptor.")
            continue
        if not any(
            descriptor_path == root or descriptor_path.startswith(f"{root}/") for root in dvc_roots
        ):
            raise FileNotFoundError(
                f"Absent evidence source {name!r} is not under an active DVC output."
            )
        if parent_sources.get(name) != descriptor:
            raise RuntimeError(
                f"Absent evidence source {name!r} differs from the sealed parent registry."
            )
        missing.append(str(name))

    units = _validated_registry_units(payload)
    _verify_source_transport(
        source_paths=tuple(seen_paths),
        dvc_pointers=payload["dvc_pointers"],
        git_artifact_paths=tuple(
            artifact_path
            for unit in units
            for artifact_path in (
                *(unit.source_artifact_paths or ()),
                *(unit.artifact_paths or ()),
            )
        ),
        repo_root=repo_root,
    )
    _verify_two_stage_git_blob_descriptors(
        units=units,
        descriptors_by_path=descriptors_by_path,
        repo_root=repo_root,
    )
    return payload, registered, tuple(sorted(missing))


def _verify_source_transport(
    *,
    source_paths: tuple[str, ...],
    dvc_pointers: list[str],
    git_artifact_paths: tuple[str, ...],
    repo_root: Path,
) -> None:
    """Require every active source to travel through Git or an active DVC output.

    Hash verification proves that the local bytes are the declared bytes.  This
    second gate proves that a fresh checkout has a declared transport for those
    bytes, preventing a locally present ignored artifact from becoming active
    paper evidence.
    """
    resolved_root = repo_root.resolve()
    probe = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=resolved_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        return
    git_root = Path(probe.stdout.strip()).resolve()
    if git_root != resolved_root:
        raise RuntimeError(
            f"Evidence registry root {resolved_root} is not the Git root {git_root}."
        )

    listing = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=resolved_root,
        check=True,
        capture_output=True,
    ).stdout
    tracked = {
        item.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        for item in listing.split(b"\0")
        if item
    }
    missing_pointers = sorted(set(dvc_pointers).difference(tracked))
    if missing_pointers:
        raise RuntimeError(
            "Active DVC pointers are not Git-tracked: " + ", ".join(missing_pointers)
        )

    undescribed_artifacts = sorted(set(git_artifact_paths).difference(source_paths))
    if undescribed_artifacts:
        raise RuntimeError(
            "Git artifact contract paths lack active hash descriptors: "
            + ", ".join(undescribed_artifacts)
        )

    dvc_roots = tuple(
        PurePosixPath(pointer).parent.joinpath(PurePosixPath(pointer).stem).as_posix()
        for pointer in dvc_pointers
    )
    undeliverable = sorted(
        source
        for source in source_paths
        if source not in tracked
        and not any(source == root or source.startswith(f"{root}/") for root in dvc_roots)
    )
    if undeliverable:
        raise RuntimeError(
            "Active evidence sources lack Git or active-DVC transport: " + ", ".join(undeliverable)
        )


def _verify_two_stage_git_blob_descriptors(
    *,
    units: tuple[_RegistryUnit, ...],
    descriptors_by_path: Mapping[str, Mapping[str, Any]],
    repo_root: Path,
) -> None:
    """Tie every two-stage hash descriptor to the bytes at its pinned Git stage."""
    for unit in units:
        if unit.source_artifact_commit is None:
            continue
        if (
            unit.source_artifact_paths is None
            or unit.artifact_commit is None
            or unit.artifact_paths is None
        ):
            raise RuntimeError("Parsed two-stage Git artifact identity is incomplete.")
        stages = (
            ("source artifact", unit.source_artifact_commit, unit.source_artifact_paths),
            ("evaluation artifact", unit.artifact_commit, unit.artifact_paths),
        )
        for stage_label, commit, paths in stages:
            for path in paths:
                descriptor = descriptors_by_path.get(path)
                if descriptor is None:
                    raise RuntimeError(
                        f"Two-stage {stage_label} path {path} lacks an active hash descriptor."
                    )
                blob = subprocess.run(
                    ["git", "cat-file", "blob", f"{commit}:{path}"],
                    cwd=repo_root,
                    check=False,
                    capture_output=True,
                )
                if blob.returncode != 0:
                    raise RuntimeError(
                        f"Cannot read two-stage {stage_label} path {path} from commit {commit}."
                    )
                actual_bytes = len(blob.stdout)
                actual_sha256 = hashlib.sha256(blob.stdout).hexdigest()
                if (
                    descriptor.get("bytes") != actual_bytes
                    or descriptor.get("sha256") != actual_sha256
                ):
                    raise RuntimeError(
                        f"Two-stage {stage_label} path {path} hash descriptor does not match "
                        f"the pinned Git blob at {commit}."
                    )


def _validated_registry_units(payload: Mapping[str, Any]) -> tuple[_RegistryUnit, ...]:
    units = _collect_registry_units(payload)
    _require_complete_explicit_contract(units)
    _require_unique_identity_values(units)
    return units


def _collect_registry_units(payload: Mapping[str, Any]) -> tuple[_RegistryUnit, ...]:
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
    return tuple(units)


def _require_complete_explicit_contract(units: tuple[_RegistryUnit, ...]) -> None:
    uses_explicit_contract = any(
        unit.paper_role is not None or unit.declared_dvc_tracked is not None for unit in units
    )
    if not uses_explicit_contract:
        return
    incomplete = [
        _format_location(unit.location)
        for unit in units
        if unit.paper_role is None or unit.declared_dvc_tracked is None
    ]
    if incomplete:
        raise TypeError(
            f"Explicit registry identities require both paper_role and dvc_tracked: {incomplete}."
        )


def _require_unique_identity_values(units: tuple[_RegistryUnit, ...]) -> None:
    _require_unique_identity_field(units, field="run_tag", label="run tags")
    _require_unique_identity_field(units, field="protocol_tag", label="protocol tags")


def _require_unique_identity_field(
    units: tuple[_RegistryUnit, ...],
    *,
    field: str,
    label: str,
) -> None:
    seen: dict[str, tuple[str, ...]] = {}
    for unit in units:
        value = getattr(unit, field)
        if value is None:
            continue
        previous = seen.get(value)
        if previous is not None:
            raise ValueError(
                f"Active evidence registry {label} must be globally unique: "
                f"{value!r} appears at {_format_location(previous)} and "
                f"{_format_location(unit.location)}."
            )
        seen[value] = unit.location


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

    protocol_tag, protocol_commit, protocol_bundle, scientific_uv_lock_sha256 = (
        _parse_protocol_identity(
            identity,
            location=location,
        )
    )
    if "status" in identity:
        _required_text(identity, "status", location=location)
    paper_role = (
        _required_text(identity, "paper_role", location=location)
        if "paper_role" in identity
        else None
    )
    declared_dvc_tracked, dvc_roots = _parse_dvc_metadata(identity, location=location)
    (
        source_artifact_tag,
        source_artifact_commit,
        source_artifact_parent_commit,
        source_artifact_transport,
        source_artifact_paths,
    ) = _parse_source_git_artifact_identity(
        identity,
        protocol_commit=protocol_commit,
        location=location,
    )
    (
        artifact_tag,
        artifact_commit,
        artifact_parent_commit,
        artifact_transport,
        artifact_paths,
    ) = _parse_git_artifact_identity(
        identity,
        protocol_commit=protocol_commit,
        source_artifact_commit=source_artifact_commit,
        location=location,
    )
    if source_artifact_tag is not None and artifact_tag is None:
        raise TypeError(
            f"Registry identity {_format_location(location)} cannot declare a source Git "
            "artifact without a complete evaluation Git artifact contract."
        )
    if source_artifact_paths is not None and artifact_paths is not None:
        overlap = sorted(set(source_artifact_paths).intersection(artifact_paths))
        if overlap:
            raise ValueError(
                f"Registry identity {_format_location(location)} source and evaluation Git "
                f"artifact paths must be disjoint; overlap {overlap}."
            )
    return _RegistryUnit(
        location=location,
        run_tag=run_tag,
        protocol_tag=protocol_tag,
        protocol_commit=protocol_commit,
        protocol_bundle=protocol_bundle,
        scientific_uv_lock_sha256=scientific_uv_lock_sha256,
        paper_role=paper_role,
        declared_dvc_tracked=declared_dvc_tracked,
        dvc_roots=dvc_roots,
        source_artifact_tag=source_artifact_tag,
        source_artifact_commit=source_artifact_commit,
        source_artifact_parent_commit=source_artifact_parent_commit,
        source_artifact_transport=source_artifact_transport,
        source_artifact_paths=source_artifact_paths,
        artifact_tag=artifact_tag,
        artifact_commit=artifact_commit,
        artifact_parent_commit=artifact_parent_commit,
        artifact_transport=artifact_transport,
        artifact_paths=artifact_paths,
    )


def _parse_git_artifact_identity(
    identity: Mapping[str, Any],
    *,
    protocol_commit: str | None,
    source_artifact_commit: str | None,
    location: tuple[str, ...],
) -> tuple[str | None, str | None, str | None, str | None, tuple[str, ...] | None]:
    fields = {
        "artifact_tag",
        "artifact_commit",
        "artifact_parent_commit",
        "artifact_transport",
        "artifact_paths",
    }
    present = fields.intersection(identity)
    if not present:
        return None, None, None, None, None
    if present != fields:
        missing = sorted(fields.difference(present))
        raise TypeError(
            f"Registry identity {_format_location(location)} has an incomplete Git artifact "
            f"contract; missing {missing}."
        )
    if protocol_commit is None:
        raise ValueError(
            f"Registry identity {_format_location(location)} cannot pin artifacts without "
            "a protocol commit."
        )
    if identity.get("dvc_tracked") is not False:
        raise ValueError(
            f"Registry identity {_format_location(location)} Git artifacts require "
            "dvc_tracked=false."
        )
    if "protocol_bundle" in identity:
        raise ValueError(
            f"Registry identity {_format_location(location)} cannot combine a local exact "
            "Git artifact commit with a protocol bundle."
        )

    tag = _required_text(identity, "artifact_tag", location=location)
    commit = _required_text(identity, "artifact_commit", location=location)
    parent = _required_text(identity, "artifact_parent_commit", location=location)
    transport = _required_text(identity, "artifact_transport", location=location)
    if _PROTOCOL_COMMIT_PATTERN.fullmatch(commit) is None:
        raise ValueError(
            f"Registry identity {_format_location(location)}.artifact_commit must be a "
            "40-character lowercase hexadecimal commit."
        )
    if _PROTOCOL_COMMIT_PATTERN.fullmatch(parent) is None:
        raise ValueError(
            f"Registry identity {_format_location(location)}.artifact_parent_commit must be a "
            "40-character lowercase hexadecimal commit."
        )
    expected_parent = source_artifact_commit or protocol_commit
    if parent != expected_parent:
        if source_artifact_commit is None:
            raise ValueError(
                f"Registry identity {_format_location(location)} must pin its protocol "
                "commit as the artifact commit's sole parent."
            )
        raise ValueError(
            f"Registry identity {_format_location(location)} must pin its source artifact commit as "
            "the evaluation artifact commit's sole parent."
        )
    if transport != _GIT_ARTIFACT_TRANSPORT:
        raise ValueError(
            f"Registry identity {_format_location(location)}.artifact_transport must be "
            f"{_GIT_ARTIFACT_TRANSPORT!r}."
        )

    paths = _parse_git_artifact_paths(
        identity["artifact_paths"],
        field="artifact_paths",
        location=location,
    )
    return tag, commit, parent, transport, paths


def _parse_source_git_artifact_identity(
    identity: Mapping[str, Any],
    *,
    protocol_commit: str | None,
    location: tuple[str, ...],
) -> tuple[str | None, str | None, str | None, str | None, tuple[str, ...] | None]:
    fields = {
        "source_artifact_tag",
        "source_artifact_commit",
        "source_artifact_parent_commit",
        "source_artifact_transport",
        "source_artifact_paths",
    }
    present = fields.intersection(identity)
    if not present:
        return None, None, None, None, None
    if present != fields:
        missing = sorted(fields.difference(present))
        raise TypeError(
            f"Registry identity {_format_location(location)} has an incomplete source Git "
            f"artifact contract; missing {missing}."
        )
    if protocol_commit is None:
        raise ValueError(
            f"Registry identity {_format_location(location)} cannot pin source artifacts "
            "without a protocol commit."
        )
    if identity.get("dvc_tracked") is not False:
        raise ValueError(
            f"Registry identity {_format_location(location)} source Git artifacts require "
            "dvc_tracked=false."
        )
    if "protocol_bundle" in identity:
        raise ValueError(
            f"Registry identity {_format_location(location)} cannot combine a local exact "
            "source Git artifact commit with a protocol bundle."
        )

    tag = _required_text(identity, "source_artifact_tag", location=location)
    commit = _required_text(identity, "source_artifact_commit", location=location)
    parent = _required_text(identity, "source_artifact_parent_commit", location=location)
    transport = _required_text(identity, "source_artifact_transport", location=location)
    if _PROTOCOL_COMMIT_PATTERN.fullmatch(commit) is None:
        raise ValueError(
            f"Registry identity {_format_location(location)}.source_artifact_commit must be a "
            "40-character lowercase hexadecimal commit."
        )
    if _PROTOCOL_COMMIT_PATTERN.fullmatch(parent) is None:
        raise ValueError(
            f"Registry identity {_format_location(location)}.source_artifact_parent_commit "
            "must be a 40-character lowercase hexadecimal commit."
        )
    if parent != protocol_commit:
        raise ValueError(
            f"Registry identity {_format_location(location)} must pin its protocol commit as "
            "the source artifact commit's sole parent."
        )
    if transport != _GIT_ARTIFACT_TRANSPORT:
        raise ValueError(
            f"Registry identity {_format_location(location)}.source_artifact_transport must "
            f"be {_GIT_ARTIFACT_TRANSPORT!r}."
        )
    paths = _parse_git_artifact_paths(
        identity["source_artifact_paths"],
        field="source_artifact_paths",
        location=location,
    )
    return tag, commit, parent, transport, paths


def _parse_git_artifact_paths(
    raw_paths: Any,
    *,
    field: str,
    location: tuple[str, ...],
) -> tuple[str, ...]:
    if (
        not isinstance(raw_paths, list)
        or not raw_paths
        or not all(isinstance(path, str) and path for path in raw_paths)
        or raw_paths != sorted(set(raw_paths))
    ):
        raise TypeError(
            f"Registry identity {_format_location(location)}.{field} must be a "
            "nonempty sorted unique string list."
        )
    paths: list[str] = []
    for raw_path in raw_paths:
        normalized = PurePosixPath(posixpath.normpath(raw_path.replace("\\", "/")))
        if (
            normalized.is_absolute()
            or str(normalized) in {"", ".", ".."}
            or str(normalized).startswith("../")
            or normalized.as_posix() != raw_path
        ):
            raise ValueError(
                f"Registry identity {_format_location(location)}.{field} contains an "
                f"unsafe or non-normalized path: {raw_path!r}."
            )
        paths.append(raw_path)
    return tuple(paths)


def _parse_protocol_identity(
    identity: Mapping[str, Any],
    *,
    location: tuple[str, ...],
) -> tuple[str | None, str | None, str | None, str | None]:
    has_protocol_tag = "protocol_tag" in identity
    has_protocol_commit = "protocol_commit" in identity
    if has_protocol_tag != has_protocol_commit:
        missing_field = "protocol_commit" if has_protocol_tag else "protocol_tag"
        raise TypeError(
            f"Missing registry identity: {_format_location((*location, missing_field))}."
        )

    if not has_protocol_tag:
        _required_text(identity, "status", location=location)
        if "scientific_uv_lock_sha256" in identity:
            raise ValueError(
                f"Registry identity {_format_location(location)} cannot declare a scientific "
                "lock without a protocol commit."
            )
        if "protocol_bundle" in identity:
            raise ValueError(
                f"Registry identity {_format_location(location)} cannot declare a protocol "
                "bundle without a protocol commit."
            )
        return None, None, None, None

    protocol_tag = _required_text(identity, "protocol_tag", location=location)
    protocol_commit = _required_text(identity, "protocol_commit", location=location)
    if _PROTOCOL_COMMIT_PATTERN.fullmatch(protocol_commit) is None:
        raise ValueError(
            f"Registry identity {_format_location(location)}.protocol_commit "
            "must be a 40-character lowercase hexadecimal commit."
        )
    protocol_bundle: str | None = None
    if "protocol_bundle" in identity:
        protocol_bundle = _required_text(identity, "protocol_bundle", location=location)
        normalized = PurePosixPath(posixpath.normpath(protocol_bundle.replace("\\", "/")))
        if (
            normalized.is_absolute()
            or str(normalized) in {"", ".", ".."}
            or str(normalized).startswith("../")
            or normalized.suffix != ".bundle"
            or normalized.as_posix() != protocol_bundle
        ):
            raise ValueError(
                f"Registry identity {_format_location(location)}.protocol_bundle must be a "
                "normalized repository-relative .bundle path."
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
    return protocol_tag, protocol_commit, protocol_bundle, scientific_uv_lock_sha256


def _parse_dvc_metadata(
    identity: Mapping[str, Any],
    *,
    location: tuple[str, ...],
) -> tuple[bool | None, tuple[str, ...] | None]:
    declared_dvc_tracked: bool | None = None
    if "dvc_tracked" in identity:
        raw_dvc_tracked = identity["dvc_tracked"]
        if not isinstance(raw_dvc_tracked, bool):
            raise TypeError(
                f"Registry identity {_format_location(location)}.dvc_tracked must be boolean."
            )
        declared_dvc_tracked = raw_dvc_tracked

    if "dvc_roots" not in identity:
        return declared_dvc_tracked, None
    raw_roots = identity["dvc_roots"]
    if declared_dvc_tracked is not True:
        raise ValueError(
            f"Registry identity {_format_location(location)}.dvc_roots requires dvc_tracked=true."
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
    return declared_dvc_tracked, tuple(raw_roots)


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
        resolved = _resolve_local_tag_commit(unit.protocol_tag, repo_root=repo_root)
        if resolved is not None and resolved != unit.protocol_commit:
            raise RuntimeError(
                f"Registry protocol tag {unit.protocol_tag!r} does not resolve to "
                f"declared commit {unit.protocol_commit}."
            )
        if resolved is not None:
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
            lock_bytes = lock_result.stdout
        elif unit.protocol_bundle is not None:
            lock_bytes = _verify_protocol_bundle(unit, repo_root=repo_root)
        else:
            raise RuntimeError(
                f"Registry protocol tag {unit.protocol_tag!r} does not resolve to "
                f"declared commit {unit.protocol_commit}."
            )
        actual_lock_sha256 = hashlib.sha256(lock_bytes).hexdigest()
        if actual_lock_sha256 != unit.scientific_uv_lock_sha256:
            raise RuntimeError(
                f"Registry protocol tag {unit.protocol_tag!r} declares uv.lock "
                f"{unit.scientific_uv_lock_sha256}, but its commit contains "
                f"{actual_lock_sha256}."
            )
        _verify_git_artifact_contract(unit, repo_root=repo_root)


def _verify_git_artifact_contract(unit: _RegistryUnit, *, repo_root: Path) -> None:
    if unit.artifact_tag is None:
        return
    if (
        unit.protocol_commit is None
        or unit.artifact_commit is None
        or unit.artifact_parent_commit is None
        or unit.artifact_transport != _GIT_ARTIFACT_TRANSPORT
        or unit.artifact_paths is None
    ):
        raise RuntimeError("Parsed Git artifact identity is incomplete.")

    if unit.source_artifact_tag is None:
        _verify_exact_git_artifact_stage(
            tag=unit.artifact_tag,
            commit=unit.artifact_commit,
            parent_commit=unit.artifact_parent_commit,
            paths=unit.artifact_paths,
            stage_label="artifact",
            parent_label="protocol commit",
            require_annotated_tag=False,
            repo_root=repo_root,
        )
        return

    if (
        unit.source_artifact_commit is None
        or unit.source_artifact_parent_commit is None
        or unit.source_artifact_transport != _GIT_ARTIFACT_TRANSPORT
        or unit.source_artifact_paths is None
    ):
        raise RuntimeError("Parsed source Git artifact identity is incomplete.")
    _verify_exact_git_artifact_stage(
        tag=unit.source_artifact_tag,
        commit=unit.source_artifact_commit,
        parent_commit=unit.source_artifact_parent_commit,
        paths=unit.source_artifact_paths,
        stage_label="source artifact",
        parent_label="protocol commit",
        require_annotated_tag=True,
        repo_root=repo_root,
    )
    _verify_exact_git_artifact_stage(
        tag=unit.artifact_tag,
        commit=unit.artifact_commit,
        parent_commit=unit.artifact_parent_commit,
        paths=unit.artifact_paths,
        stage_label="evaluation artifact",
        parent_label="source artifact commit",
        require_annotated_tag=True,
        repo_root=repo_root,
    )


def _verify_exact_git_artifact_stage(
    *,
    tag: str,
    commit: str,
    parent_commit: str,
    paths: tuple[str, ...],
    stage_label: str,
    parent_label: str,
    require_annotated_tag: bool,
    repo_root: Path,
) -> None:
    if require_annotated_tag:
        _require_annotated_tag(tag, repo_root=repo_root)
    resolved = _resolve_local_tag_commit(tag, repo_root=repo_root)
    if resolved != commit:
        raise RuntimeError(
            f"Registry {stage_label} tag {tag!r} does not resolve to declared commit {commit}."
        )

    parents = (
        subprocess.run(
            ["git", "rev-list", "--parents", "-n", "1", commit],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
        .split()
    )
    if parents != [commit, parent_commit]:
        raise RuntimeError(
            f"Registry {stage_label} commit {commit} is not the declared direct child of "
            f"{parent_label} {parent_commit}."
        )

    changed = subprocess.run(
        [
            "git",
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "--no-renames",
            "-r",
            commit,
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    if changed != list(paths):
        raise RuntimeError(
            f"Registry {stage_label} commit {commit} changed {changed}, not the declared "
            f"exact {stage_label} paths {list(paths)}."
        )
    for path in paths:
        exists = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}:{path}"],
            cwd=repo_root,
            check=False,
            capture_output=True,
        )
        if exists.returncode != 0:
            raise RuntimeError(f"Registry {stage_label} commit {commit} does not contain {path}.")


def _require_annotated_tag(tag: str, *, repo_root: Path) -> None:
    """Reject a missing or lightweight tag for a two-stage Git artifact edge."""
    reference = f"refs/tags/{tag}"
    tag_type = subprocess.run(
        ["git", "cat-file", "-t", reference],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if tag_type.returncode != 0 or tag_type.stdout.strip() != "tag":
        raise RuntimeError(f"Registry two-stage artifact tag {tag!r} must be annotated.")


def _resolve_local_tag_commit(tag: str, *, repo_root: Path) -> str | None:
    """Resolve one explicit local tag ref, peeling annotated tags to a commit."""
    reference = f"refs/tags/{tag}"
    valid = subprocess.run(
        ["git", "check-ref-format", reference],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if valid.returncode != 0:
        raise RuntimeError(f"Registry tag is not an explicit valid tag ref: {tag!r}.")
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", "--end-of-options", f"{reference}^{{commit}}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if resolved.returncode != 0:
        return None
    commit = resolved.stdout.strip()
    if _PROTOCOL_COMMIT_PATTERN.fullmatch(commit) is None:
        raise RuntimeError(f"Registry tag {tag!r} did not resolve to a full commit.")
    return commit


def _verify_protocol_bundle(unit: _RegistryUnit, *, repo_root: Path) -> bytes:
    """Verify a portable clean-tag commit when the current checkout lacks its ref."""
    if unit.protocol_bundle is None or unit.protocol_tag is None or unit.protocol_commit is None:
        raise RuntimeError("Protocol-bundle verification requires a complete protocol identity.")
    root = repo_root.resolve()
    bundle = (root / unit.protocol_bundle).resolve()
    try:
        bundle.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Protocol bundle escapes the repository: {bundle}") from exc
    if not bundle.is_file():
        raise FileNotFoundError(f"Protocol bundle is missing: {bundle}")
    verified = subprocess.run(
        ["git", "bundle", "verify", str(bundle)],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if verified.returncode != 0:
        raise RuntimeError(f"Protocol bundle failed Git verification: {bundle}")
    with TemporaryDirectory(prefix=".protocol-bundle-verify-", dir=root) as temporary:
        repository = Path(temporary)
        subprocess.run(
            ["git", "init", "--bare", "--quiet", str(repository)],
            cwd=root,
            check=True,
            capture_output=True,
        )
        ref = f"refs/tags/{unit.protocol_tag}"
        fetched = subprocess.run(
            ["git", "--git-dir", str(repository), "fetch", "--quiet", str(bundle), f"{ref}:{ref}"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        if fetched.returncode != 0:
            raise RuntimeError(
                f"Protocol bundle does not expose declared tag {unit.protocol_tag!r}."
            )
        resolved = subprocess.run(
            ["git", "--git-dir", str(repository), "rev-list", "-n", "1", unit.protocol_tag],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if resolved != unit.protocol_commit:
            raise RuntimeError(
                f"Protocol bundle tag {unit.protocol_tag!r} resolves to {resolved!r}, "
                f"not {unit.protocol_commit!r}."
            )
        lock = subprocess.run(
            ["git", "--git-dir", str(repository), "show", f"{unit.protocol_commit}:uv.lock"],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if lock.returncode != 0:
            raise RuntimeError(
                f"Protocol-bundle commit {unit.protocol_commit} does not contain uv.lock."
            )
        return lock.stdout


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
