"""Run DVC operations over active and publication-required IJDS targets."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from src.ijds_audit.publication_sources import (
    active_lineage_run_tags,
    load_source_registry,
)
from src.utils.protected_manifest import strict_manifest_paths

ROOT = Path(__file__).resolve().parents[1]
TARGETS_PATH = ROOT / "configs/crpto_publication_targets.yaml"
EXTRACTION_MANIFEST_PATH = ROOT / "EXTRACTION_MANIFEST.json"
DVC_LOCK_PATH = ROOT / "dvc.lock"
DVC_REMOTE = "dagshub"


def active_dvc_pointers(
    *,
    root: Path = ROOT,
    targets_path: Path = TARGETS_PATH,
) -> list[Path]:
    """Load and validate the data/model pointers for every active run tag."""
    payload: Any = yaml.safe_load(targets_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Publication targets must be a YAML mapping.")
    contract = payload.get("active_scientific_contract")
    if not isinstance(contract, dict):
        raise TypeError("Publication targets omit active_scientific_contract.")
    registry_value = contract.get("source_registry")
    if not isinstance(registry_value, str) or not registry_value:
        raise TypeError("Publication targets omit the active source_registry path.")
    registry_path = (root / registry_value).resolve()
    registry_path.relative_to(root.resolve())
    registry = load_source_registry(registry_path, repo_root=root)
    active_lineage_run_tags(registry)
    values = registry["dvc_pointers"]

    resolved: list[Path] = []
    for value in values:
        path = (root / value).resolve()
        path.relative_to(root.resolve())
        if path.suffix != ".dvc" or not path.is_file():
            raise FileNotFoundError(f"Invalid active DVC pointer: {path}")
        resolved.append(path)
    return resolved


def _pointer_arguments(pointers: Sequence[Path], *, root: Path) -> list[str]:
    root_resolved = root.resolve()
    return [path.resolve().relative_to(root_resolved).as_posix() for path in pointers]


def _git_tracked_paths(*, root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return {value for value in result.stdout.split("\0") if value}


def _standalone_dvc_outputs(
    *,
    root: Path,
    tracked_paths: set[str],
) -> list[tuple[str, str]]:
    outputs: list[tuple[str, str]] = []
    resolved_root = root.resolve()
    for relative_pointer in sorted(path for path in tracked_paths if path.endswith(".dvc")):
        pointer = (resolved_root / relative_pointer).resolve()
        pointer.relative_to(resolved_root)
        payload = yaml.safe_load(pointer.read_text(encoding="utf-8"))
        outs = payload.get("outs") if isinstance(payload, Mapping) else None
        if not isinstance(outs, list) or not outs:
            raise ValueError(f"DVC pointer has no outputs: {relative_pointer}")
        for out in outs:
            raw_path = out.get("path") if isinstance(out, Mapping) else None
            if not isinstance(raw_path, str) or not raw_path:
                raise ValueError(f"DVC pointer has an invalid output path: {relative_pointer}")
            output = (pointer.parent / raw_path).resolve()
            output_relative = output.relative_to(resolved_root).as_posix()
            outputs.append((output_relative, relative_pointer))
    return outputs


def _locked_dvc_outputs(*, root: Path, dvc_lock_path: Path) -> list[tuple[str, str]]:
    payload = yaml.safe_load(dvc_lock_path.read_text(encoding="utf-8"))
    stages = payload.get("stages") if isinstance(payload, Mapping) else None
    if not isinstance(stages, Mapping):
        raise TypeError("dvc.lock omits its stages mapping.")
    outputs: list[tuple[str, str]] = []
    for stage_name, stage in stages.items():
        raw_outs = stage.get("outs") if isinstance(stage, Mapping) else None
        if raw_outs is None:
            continue
        if not isinstance(raw_outs, list):
            raise TypeError(f"dvc.lock stage {stage_name!r} has invalid outputs.")
        for out in raw_outs:
            raw_path = out.get("path") if isinstance(out, Mapping) else None
            if not isinstance(raw_path, str) or not raw_path:
                raise ValueError(f"dvc.lock stage {stage_name!r} has an invalid output path.")
            output = (root / raw_path).resolve()
            output_relative = output.relative_to(root.resolve()).as_posix()
            outputs.append((output_relative, output_relative))
    return outputs


def _covers_artifact(output: str, artifact: str) -> bool:
    return artifact == output or artifact.startswith(output.rstrip("/") + "/")


def protected_dvc_targets(
    *,
    root: Path = ROOT,
    manifest_path: Path = EXTRACTION_MANIFEST_PATH,
    dvc_lock_path: Path = DVC_LOCK_PATH,
) -> list[str]:
    """Return the minimal DVC targets needed by the strict manifest gate."""
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    critical_hashes = payload.get("critical_hashes") if isinstance(payload, Mapping) else None
    if not isinstance(critical_hashes, Mapping) or not critical_hashes:
        raise TypeError("Extraction manifest omits critical_hashes.")

    tracked_paths = _git_tracked_paths(root=root)
    outputs = [
        *_standalone_dvc_outputs(root=root, tracked_paths=tracked_paths),
        *_locked_dvc_outputs(root=root, dvc_lock_path=dvc_lock_path),
    ]
    selected: list[str] = []
    for artifact in strict_manifest_paths(critical_hashes):
        if artifact in tracked_paths:
            continue
        candidates = [entry for entry in outputs if _covers_artifact(entry[0], artifact)]
        if not candidates:
            raise FileNotFoundError(
                f"Strict manifest artifact has no Git or DVC source: {artifact}"
            )
        _, target = max(candidates, key=lambda entry: len(entry[0]))
        selected.append(target)
    return list(dict.fromkeys(selected))


def publication_dvc_targets(
    *,
    root: Path = ROOT,
    targets_path: Path = TARGETS_PATH,
    manifest_path: Path = EXTRACTION_MANIFEST_PATH,
    dvc_lock_path: Path = DVC_LOCK_PATH,
) -> list[str]:
    """Return active-evidence and strict-manifest targets for a clean clone."""
    active = _pointer_arguments(
        active_dvc_pointers(root=root, targets_path=targets_path),
        root=root,
    )
    protected = protected_dvc_targets(
        root=root,
        manifest_path=manifest_path,
        dvc_lock_path=dvc_lock_path,
    )
    return list(dict.fromkeys([*active, *protected]))


def cloud_status_payload(
    *,
    root: Path = ROOT,
    targets_path: Path = TARGETS_PATH,
    pointers: Sequence[Path] | None = None,
) -> Any:
    """Return DVC's machine-readable local-cache versus remote status."""
    selected = (
        list(pointers)
        if pointers is not None
        else active_dvc_pointers(root=root, targets_path=targets_path)
    )
    command = [
        "dvc",
        "status",
        "--cloud",
        "--remote",
        DVC_REMOTE,
        "--json",
        *_pointer_arguments(selected, root=root),
    ]
    result = subprocess.run(
        command,
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    if not output:
        raise RuntimeError("DVC returned no JSON while verifying the active IJDS capsule.")
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "DVC returned invalid JSON while verifying the active IJDS capsule."
        ) from exc


def verify_remote(
    *,
    root: Path = ROOT,
    targets_path: Path = TARGETS_PATH,
    pointers: Sequence[Path] | None = None,
) -> None:
    """Fail unless every active IJDS object is present and equal in the remote."""
    payload = cloud_status_payload(root=root, targets_path=targets_path, pointers=pointers)
    if payload:
        if isinstance(payload, dict):
            items = list(payload.items())
            excerpt: Any = dict(items[:25])
            omitted = max(0, len(items) - len(excerpt))
        elif isinstance(payload, list):
            excerpt = payload[:25]
            omitted = max(0, len(payload) - len(excerpt))
        else:
            excerpt = payload
            omitted = 0
        detail = json.dumps(excerpt, indent=2, sort_keys=True)
        suffix = f"\n... {omitted} additional status entries omitted." if omitted else ""
        raise RuntimeError(
            "Active IJDS DVC objects differ from or are absent in the configured remote:\n"
            f"{detail}{suffix}"
        )


def run_dvc(action: str, *, cloud: bool = False) -> None:
    """Run a declared DVC operation without executing any scientific stage."""
    if action == "pull-publication":
        targets = publication_dvc_targets()
        pointer_targets = [target for target in targets if target.endswith(".dvc")]
        locked_output_targets = [target for target in targets if not target.endswith(".dvc")]
        if pointer_targets:
            subprocess.run(
                [
                    "dvc",
                    "pull",
                    "--remote",
                    DVC_REMOTE,
                    "--no-run-cache",
                    *pointer_targets,
                ],
                cwd=ROOT,
                check=True,
            )
        for target in locked_output_targets:
            subprocess.run(
                [
                    "dvc",
                    "pull",
                    "--remote",
                    DVC_REMOTE,
                    "--no-run-cache",
                    target,
                ],
                cwd=ROOT,
                check=True,
            )
        return

    pointers = active_dvc_pointers()
    relative = _pointer_arguments(pointers, root=ROOT)
    if action == "pull":
        command = ["dvc", "pull", "--remote", DVC_REMOTE, *relative]
    elif action == "push":
        command = ["dvc", "push", "--remote", DVC_REMOTE, *relative]
    elif action == "status":
        command = ["dvc", "status", *(["--cloud"] if cloud else ["--no-updates"]), *relative]
    elif action == "verify-remote":
        verify_remote(pointers=pointers)
        print(f"Active IJDS DVC capsule is fully available in remote {DVC_REMOTE!r}.")
        return
    else:
        raise ValueError(f"Unsupported DVC action: {action}")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("pull", "pull-publication", "push", "status", "verify-remote"),
    )
    parser.add_argument(
        "--cloud",
        action="store_true",
        help="Compare the local cache with the configured remote during status.",
    )
    args = parser.parse_args()
    if args.cloud and args.action != "status":
        parser.error("--cloud is valid only with the status action")
    run_dvc(args.action, cloud=bool(args.cloud))


if __name__ == "__main__":
    main()
