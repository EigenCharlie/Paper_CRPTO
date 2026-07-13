"""Run DVC operations over the active IJDS pointer set."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
TARGETS_PATH = ROOT / "configs/crpto_publication_targets.yaml"


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
    values = contract.get("dvc_pointers")
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise TypeError("active_scientific_contract.dvc_pointers must be a string list.")
    run_keys = (
        "outcome_free_run_tag",
        "run_tag",
        "two_ruler_outcome_free_run_tag",
        "two_ruler_run_tag",
        "credit_control_outcome_free_run_tag",
        "credit_control_run_tag",
    )
    run_tags = [contract.get(key) for key in run_keys]
    if not all(isinstance(tag, str) and tag for tag in run_tags):
        raise TypeError("The active IJDS capsule must declare all six run tags.")
    expected = {
        f"{prefix}/experiments/ijds_audit/{tag}.dvc"
        for tag in run_tags
        for prefix in ("data/processed", "models")
    }
    if set(values) != expected or len(values) != len(expected):
        raise ValueError("The active IJDS capsule pointers do not match its six declared run tags.")

    resolved: list[Path] = []
    for value in values:
        path = (root / value).resolve()
        path.relative_to(root.resolve())
        if path.suffix != ".dvc" or not path.is_file():
            raise FileNotFoundError(f"Invalid active DVC pointer: {path}")
        resolved.append(path)
    return resolved


def run_dvc(action: str, *, cloud: bool = False) -> None:
    """Run pull or status against only the active IJDS pointers."""
    pointers = active_dvc_pointers()
    relative = [path.relative_to(ROOT).as_posix() for path in pointers]
    if action == "pull":
        command = ["dvc", "pull", *relative]
    elif action == "status":
        command = ["dvc", "status", *(["--cloud"] if cloud else ["--no-updates"]), *relative]
    else:
        raise ValueError(f"Unsupported DVC action: {action}")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("pull", "status"))
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
