"""Run DVC operations over the active IJDS pointer set."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from src.ijds_audit.publication_sources import (
    active_lineage_run_tags,
    load_source_registry,
)

ROOT = Path(__file__).resolve().parents[1]
TARGETS_PATH = ROOT / "configs/crpto_publication_targets.yaml"
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
    """Run pull or status against only the active IJDS pointers."""
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
    parser.add_argument("action", choices=("pull", "push", "status", "verify-remote"))
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
