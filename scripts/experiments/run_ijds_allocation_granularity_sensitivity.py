"""Run the two-phase USD 25 allocation-granularity sensitivity."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.ijds_audit.allocation_granularity import (
    floor_allocations_to_lot,
    granularity_contrast_bounds,
    rounded_solve_records,
)
from src.ijds_audit.config import load_v4_config
from src.ijds_audit.protocol import configured_archive_outcomes, load_outcome_universe
from src.utils.isolated_experiment import (
    environment_provenance,
    implementation_provenance,
    prepare_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_isolated_run_dir,
    resolve_repo_input,
)
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_parquet

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = (
    ROOT / "configs/experiments/ijds_allocation_granularity_sensitivity_2026-07-16.yaml"
)
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("freeze", "evaluate"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Allocation-granularity config must be a mapping.")
    sensitivity = payload.get("allocation_granularity", {})
    if float(sensitivity.get("lot_size_usd", 0.0)) != 25.0:
        raise ValueError("The allocation-granularity lot must remain USD 25.")
    if float(sensitivity.get("committed_budget_usd", 0.0)) != 1_000_000.0:
        raise ValueError("The allocation-granularity budget must remain USD 1 million.")
    if sensitivity.get("rounding_rule") != "floor_each_exposure_hold_residual_as_cash":
        raise ValueError("Allocation-granularity rounding rule changed.")
    if sensitivity.get("outcome_based_selection") is not False:
        raise ValueError("Allocation granularity cannot select from outcomes.")
    periods = tuple(str(value) for value in sensitivity.get("periods", ()))
    if len(periods) != 15 or len(set(periods)) != 15:
        raise ValueError("Allocation granularity must retain all 15 primary OOT months.")
    return payload


def _verified_descriptor(descriptor: Mapping[str, Any], *, repo_root: Path) -> Path:
    path = resolve_repo_input(str(descriptor["path"]), repo_root=repo_root)
    actual = relative_artifact_descriptor(path, repo_root=repo_root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor.get(field):
            raise RuntimeError(f"Allocation-granularity parent mismatch for {field}.")
    return path


def _run_dirs(config: Mapping[str, Any], root: Path) -> tuple[Path, Path]:
    return (
        resolve_isolated_run_dir(
            repo_root=root,
            configured_root=str(config["output"]["data_root"]),
            allowed_relative_root=ALLOWED_DATA_ROOT,
            run_tag=str(config["run_tag"]),
        ),
        resolve_isolated_run_dir(
            repo_root=root,
            configured_root=str(config["output"]["model_root"]),
            allowed_relative_root=ALLOWED_MODEL_ROOT,
            run_tag=str(config["run_tag"]),
        ),
    )


def freeze(config_path: Path, *, repo_root: Path) -> Path:
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = _load_config(resolved_config)
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))
    paths = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    allocation_path = _verified_descriptor(config["parent"]["allocations"], repo_root=root)
    record_path = _verified_descriptor(config["parent"]["solve_records"], repo_root=root)
    allocations = pd.read_parquet(allocation_path)
    records = pd.read_parquet(record_path)
    sensitivity = config["allocation_granularity"]
    budget = float(sensitivity["committed_budget_usd"])
    rounded, audit = floor_allocations_to_lot(
        allocations,
        lot_size=float(sensitivity["lot_size_usd"]),
        committed_budget=budget,
        tolerance=float(sensitivity["numerical_tolerance"]),
    )
    rounded_records = rounded_solve_records(
        records,
        rounded,
        audit,
        committed_budget=budget,
    )
    if len(audit) != int(sensitivity["expected_portfolios"]):
        raise RuntimeError("Allocation-granularity portfolio census changed.")
    artifact_paths = {
        "rounded_allocations": atomic_write_parquet(
            rounded,
            paths.data_dir / "outcome_free/rounded_allocations.parquet",
        ),
        "rounded_solve_records": atomic_write_parquet(
            rounded_records,
            paths.data_dir / "outcome_free/rounded_solve_records.parquet",
        ),
        "granularity_audit": atomic_write_parquet(
            audit,
            paths.data_dir / "outcome_free/granularity_audit.parquet",
        ),
    }
    freeze_payload = {
        "schema_version": str(config["schema_version"]),
        "status": "allocation_granularity_frozen_before_outcome_join",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "historical_archive_previously_inspected": True,
        "outcome_based_selection": False,
        "outcome_columns_passed_to_rounding": [],
        "rounding_rule": str(sensitivity["rounding_rule"]),
        "lot_size_usd": float(sensitivity["lot_size_usd"]),
        "committed_budget_usd": budget,
        "results": {
            "portfolios": int(len(audit)),
            "source_rows": int(len(allocations)),
            "rounded_positive_rows": int(len(rounded)),
            "changed_rows": int(audit["changed_positions"].sum()),
            "cash_residual_min": float(audit["cash_residual"].min()),
            "cash_residual_mean": float(audit["cash_residual"].mean()),
            "cash_residual_max": float(audit["cash_residual"].max()),
            "cash_share_max": float(audit["cash_share"].max()),
        },
        "parent": {
            "allocations": relative_artifact_descriptor(allocation_path, repo_root=root),
            "solve_records": relative_artifact_descriptor(record_path, repo_root=root),
        },
        "artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in artifact_paths.items()
        },
        "implementation": implementation_provenance(
            config_path=resolved_config,
            repo_root=root,
            relative_paths=[
                Path("src/ijds_audit/allocation_granularity.py"),
                Path("src/evaluation/policy_contrast_bounds.py"),
                Path("scripts/experiments/run_ijds_allocation_granularity_sensitivity.py"),
                Path(
                    "docs/research/ijds_allocation_granularity_sensitivity_protocol_2026-07-16.md"
                ),
            ],
        ),
        "environment": environment_provenance(root),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    return atomic_write_json(paths.model_dir / "protocol_freeze.json", freeze_payload)


def evaluate(config_path: Path, *, repo_root: Path) -> Path:
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = _load_config(resolved_config)
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))
    data_dir, model_dir = _run_dirs(config, root)
    freeze_path = model_dir / "protocol_freeze.json"
    if not freeze_path.is_file():
        raise FileNotFoundError("Run the allocation-granularity freeze phase first.")
    summary_path = model_dir / "allocation_granularity_summary.json"
    evaluation_dir = data_dir / "evaluation"
    if summary_path.exists() or evaluation_dir.exists():
        raise FileExistsError("Allocation-granularity evaluation outputs are immutable.")
    freeze_payload = json.loads(freeze_path.read_text(encoding="utf-8"))
    for field, expected in {
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "status": "allocation_granularity_frozen_before_outcome_join",
    }.items():
        if freeze_payload.get(field) != expected:
            raise RuntimeError(f"Allocation-granularity freeze mismatch for {field}.")
    if freeze_payload.get("outcome_columns_passed_to_rounding") != []:
        raise RuntimeError("Allocation-granularity freeze reports outcome leakage.")
    rounded_path = _verified_descriptor(
        freeze_payload["artifacts"]["rounded_allocations"],
        repo_root=root,
    )
    continuous_path = _verified_descriptor(config["parent"]["allocations"], repo_root=root)
    continuous = pd.read_parquet(continuous_path)
    rounded = pd.read_parquet(rounded_path)

    v4_config_path = resolve_repo_input(config["parent"]["v4_config"], repo_root=root)
    parent = load_v4_config(v4_config_path)
    raw_path = resolve_repo_input(parent["source"]["raw_path"], repo_root=root)
    universe = load_outcome_universe(parent, raw_path=raw_path)
    outcomes = configured_archive_outcomes(universe, parent)
    sensitivity = config["allocation_granularity"]
    contrasts = granularity_contrast_bounds(
        continuous,
        rounded,
        outcomes,
        committed_budget=float(sensitivity["committed_budget_usd"]),
        periods=tuple(str(value) for value in sensitivity["periods"]),
        lgd=float(sensitivity["lgd"]),
    )
    if len(contrasts) != int(sensitivity["expected_tracks"]):
        raise RuntimeError("Allocation-granularity track census changed.")
    numeric_bounds = [
        "realized_payoff_rate_difference_lower",
        "realized_payoff_rate_difference_upper",
        "weighted_default_difference_lower",
        "weighted_default_difference_upper",
        "weighted_miscoverage_difference_lower",
        "weighted_miscoverage_difference_upper",
    ]
    if not bool(np.isfinite(contrasts[numeric_bounds].to_numpy(dtype=float)).all()):
        raise RuntimeError("Allocation-granularity contrasts contain non-finite bounds.")
    contrast_path = atomic_write_parquet(
        contrasts,
        evaluation_dir / "granularity_contrasts.parquet",
    )
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_allocation_granularity_sensitivity",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "outcome_based_selection": False,
        "scope": (
            "Deterministic floor to USD 25 lots with residual cash; this diagnoses the "
            "continuous relaxation and is not a new optimized integer policy."
        ),
        "results": {
            "tracks": int(len(contrasts)),
            "cash_share_max": float(contrasts["cash_share"].max()),
            "payoff_rate_perturbation_abs_max": float(
                contrasts[
                    [
                        "realized_payoff_rate_difference_lower",
                        "realized_payoff_rate_difference_upper",
                    ]
                ]
                .abs()
                .to_numpy(dtype=float)
                .max()
            ),
            "default_rate_perturbation_abs_max": float(
                contrasts[
                    ["weighted_default_difference_lower", "weighted_default_difference_upper"]
                ]
                .abs()
                .to_numpy(dtype=float)
                .max()
            ),
            "miscoverage_rate_perturbation_abs_max": float(
                contrasts[
                    [
                        "weighted_miscoverage_difference_lower",
                        "weighted_miscoverage_difference_upper",
                    ]
                ]
                .abs()
                .to_numpy(dtype=float)
                .max()
            ),
        },
        "freeze": relative_artifact_descriptor(freeze_path, repo_root=root),
        "artifacts": {
            "granularity_contrasts": relative_artifact_descriptor(contrast_path, repo_root=root)
        },
        "environment": environment_provenance(root),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    return atomic_write_json(summary_path, summary)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    path = (
        freeze(args.config, repo_root=args.repo_root)
        if args.phase == "freeze"
        else evaluate(args.config, repo_root=args.repo_root)
    )
    print(path)


if __name__ == "__main__":
    main()
