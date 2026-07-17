"""Run one phase of the tagged IJDS V4 binary-geometry audit."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from src.ijds_audit.config import load_v4_config
from src.ijds_audit.protocol import evaluate_frozen, freeze_outcome_free
from src.utils.isolated_experiment import (
    git_provenance,
    resolve_isolated_run_dir,
    resolve_repo_input,
)
from src.utils.pipeline_runtime import atomic_write_json

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("freeze", "evaluate"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def _write_failure_receipt(
    *,
    config_path: Path,
    repo_root: Path,
    phase: str,
    error: Exception,
) -> Path:
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_v4_config(resolved_config)
    model_dir = resolve_isolated_run_dir(
        repo_root=root,
        configured_root=str(config["output"]["model_root"]),
        allowed_relative_root=ALLOWED_MODEL_ROOT,
        run_tag=str(config["run_tag"]),
    )
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / f"{phase}_failure_receipt.json"
    if path.exists():
        raise FileExistsError(f"Failure receipt already exists: {path}") from error
    details = getattr(error, "protocol_details", {})
    if not isinstance(details, dict):
        details = {"unstructured_details": str(details)}
    payload: dict[str, Any] = {
        "schema_version": str(config["schema_version"]),
        "status": "protocol_phase_failed_without_result_adaptation",
        "phase": str(phase),
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "protocol_details": details,
        "git": git_provenance(root),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    return atomic_write_json(path, payload)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    runner = freeze_outcome_free if args.phase == "freeze" else evaluate_frozen
    try:
        print(runner(config_path=args.config, repo_root=args.repo_root))
    except Exception as error:
        receipt = _write_failure_receipt(
            config_path=args.config,
            repo_root=args.repo_root,
            phase=str(args.phase),
            error=error,
        )
        print(receipt)
        raise


if __name__ == "__main__":
    main()
