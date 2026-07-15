"""Evaluate the hash-verified V1c two-ruler frontier after one outcome join."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ijds_audit.config import load_v4_config  # noqa: E402
from src.ijds_audit.endpoint_recovery import reconcile_from_json_reference  # noqa: E402
from src.ijds_audit.evaluation import evaluate_frozen_portfolios  # noqa: E402
from src.ijds_audit.protocol import (  # noqa: E402
    configured_archive_outcomes,
    load_outcome_universe,
)
from src.ijds_challengers.evaluation import (  # noqa: E402
    FrozenFrontier,
    build_endpoint_contrasts,
    build_metric_directions,
    validate_complete_evaluation,
    validate_outcome_alignment,
    verify_frontier_freeze,
)
from src.ijds_challengers.evaluation_config import load_v2_config  # noqa: E402
from src.utils.isolated_experiment import (  # noqa: E402
    OutputPaths,
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    prepare_output_paths as prepare_isolated_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_isolated_run_dir,
    resolve_repo_input,
    sha256_file,
)
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    utc_now_iso,
)

ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
IMPLEMENTATION_PATHS = (
    Path("docs/research/ijds_normalized_objective_frontier_v2_protocol_2026-07-13.md"),
    Path("docs/research/ijds_normalized_objective_frontier_v1c_results_2026-07-13.md"),
    Path("scripts/experiments/run_ijds_normalized_objective_frontier_v2.py"),
    Path("src/evaluation/maturity_safe_portfolio.py"),
    Path("src/evaluation/policy_contrast_bounds.py"),
    Path("src/evaluation/standardized_credit_payoff.py"),
    Path("src/ijds_audit/evaluation.py"),
    Path("src/ijds_audit/endpoint_recovery.py"),
    Path("src/ijds_audit/protocol.py"),
    Path("src/ijds_challengers/evaluation.py"),
    Path("src/ijds_challengers/evaluation_config.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("tests/test_ijds_normalized_objective_frontier_v2.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse one explicit hash-verified evaluation configuration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    return parser.parse_args(argv)


def prepare_output_paths(
    config: Mapping[str, Any],
    *,
    repo_root: Path = ROOT,
) -> OutputPaths:
    """Create fresh V2 output directories inside the IJDS experiment roots."""
    return prepare_isolated_output_paths(
        dict(config),
        repo_root=repo_root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )


def preflight_output_paths(
    config: Mapping[str, Any],
    *,
    repo_root: Path = ROOT,
) -> OutputPaths:
    """Reject an occupied run tag before reading any archive outcome."""
    output = config["output"]
    run_tag = str(config["run_tag"])
    paths = OutputPaths(
        data_dir=resolve_isolated_run_dir(
            repo_root=repo_root,
            configured_root=str(output["data_root"]),
            allowed_relative_root=ALLOWED_DATA_ROOT,
            run_tag=run_tag,
        ),
        model_dir=resolve_isolated_run_dir(
            repo_root=repo_root,
            configured_root=str(output["model_root"]),
            allowed_relative_root=ALLOWED_MODEL_ROOT,
            run_tag=run_tag,
        ),
    )
    existing = [path for path in (paths.data_dir, paths.model_dir) if path.exists()]
    if existing:
        rendered = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            f"Experiment output already exists ({rendered}); choose a fresh run tag."
        )
    return paths


def _direction_summary(directions: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for metric, frame in directions.groupby("metric", observed=True, sort=True):
        counts = frame["direction"].value_counts().sort_index().to_dict()
        observed = {str(value) for value in frame["direction"]}
        universal = (
            next(iter(observed))
            if len(observed) == 1 and observed.isdisjoint({"crosses_zero", "exact_zero"})
            else None
        )
        result[str(metric)] = {
            "cells": int(len(frame)),
            "direction_counts": {str(key): int(value) for key, value in counts.items()},
            "universal_nonzero_direction": universal,
            "eligible_for_separate_rolling_origin_challenger": bool(universal is not None),
        }
    return result


def _summary(
    *,
    config: Mapping[str, Any],
    protocol_commit: str,
    frontier: FrozenFrontier,
    evaluated: pd.DataFrame,
    joined: pd.DataFrame,
    window_contrasts: pd.DataFrame,
    monthly_contrasts: pd.DataFrame,
    directions: pd.DataFrame,
    outcome_audit: pd.DataFrame,
) -> dict[str, Any]:
    return {
        "schema_version": str(config["schema_version"]),
        "status": "verified_post_freeze_outcome_evaluation_complete",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "source_frontier": {
            "run_tag": str(config["source_frontier"]["run_tag"]),
            "freeze": dict(config["source_frontier"]["freeze"]),
            "source_counts": dict(frontier.summary["counts"]),
        },
        "counts": {
            "evaluated_portfolios": int(len(evaluated)),
            "joined_funded_rows": int(len(joined)),
            "window_endpoint_contrasts": int(len(window_contrasts)),
            "monthly_endpoint_contrasts": int(len(monthly_contrasts)),
            "metric_direction_cells": int(len(directions)),
            "outcome_audit_rows": int(len(outcome_audit)),
        },
        "outcomes": {
            "joined_columns": list(config["outcomes"]["joined_columns"]),
            "candidate_unresolved_by_role": {
                str(role): int(frame["unresolved_rows"].sum())
                for role, frame in outcome_audit.groupby("role", observed=True, sort=True)
            },
            "outcome_refit": False,
            "outcome_resolution": False,
            "outcome_selection": False,
        },
        "structural_activity": {
            "nonidentical_months": int(window_contrasts["nonidentical_months"].sum()),
            "minimum_nonidentical_months_per_window_cell": int(
                window_contrasts["nonidentical_months"].min()
            ),
            "maximum_nonidentical_months_per_window_cell": int(
                window_contrasts["nonidentical_months"].max()
            ),
        },
        "metric_directions": _direction_summary(directions),
        "policy_selection": None,
        "window_selection": None,
        "ruler_selection": None,
        "coordinate_selection": None,
        "gamma_selection": None,
        "policy_winner": None,
        "causal_interpretation": False,
        "conformal_guarantee_repair": False,
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }


def run_evaluation(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Verify V1c before loading outcomes, then evaluate the complete fixed grid."""
    started = time.perf_counter()
    started_at = utc_now_iso()
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_v2_config(resolved_config)
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))
    preflight_output_paths(config, repo_root=root)

    frontier = verify_frontier_freeze(config, repo_root=root)
    records = pd.read_parquet(frontier.artifacts["solve_records"])
    allocations = pd.read_parquet(frontier.artifacts["allocations"])
    endpoints = pd.read_parquet(frontier.artifacts["endpoint_diagnostics"])

    parent_config_path = resolve_repo_input(str(config["parent"]["config"]), repo_root=root)
    parent_config = load_v4_config(parent_config_path)
    raw_path = resolve_repo_input(str(config["parent"]["raw_path"]), repo_root=root)
    if sha256_file(raw_path) != str(config["parent"]["raw_sha256"]):
        raise RuntimeError("The locked raw archive hash changed before the V2 outcome join.")
    universe = load_outcome_universe(parent_config, raw_path=raw_path)
    outcomes = configured_archive_outcomes(universe, parent_config)
    outcome_audit = validate_outcome_alignment(allocations, outcomes, config=config)

    evaluated, joined = evaluate_frozen_portfolios(
        records,
        allocations,
        outcomes,
        config=parent_config,
    )
    window_contrasts, monthly_contrasts = build_endpoint_contrasts(
        joined,
        endpoints,
        config=config,
        lgd=float(parent_config["payoff"]["lgd"]),
    )
    directions = build_metric_directions(window_contrasts, config=config)
    validate_complete_evaluation(
        evaluated,
        joined,
        window_contrasts,
        monthly_contrasts,
        directions,
        config=config,
    )
    endpoint_recovery = config.get("endpoint_reason_recovery")
    recovery_audit = None
    if endpoint_recovery:
        recovery_audit = reconcile_from_json_reference(
            {
                "evaluated_portfolios": evaluated,
                "window_endpoint_contrasts": window_contrasts,
                "monthly_endpoint_contrasts": monthly_contrasts,
                "metric_direction_census": directions,
            },
            reference_json=endpoint_recovery["reference_json"],
            artifact_section=str(endpoint_recovery["artifact_section"]),
            repo_root=root,
        )
    summary = _summary(
        config=config,
        protocol_commit=protocol_commit,
        frontier=frontier,
        evaluated=evaluated,
        joined=joined,
        window_contrasts=window_contrasts,
        monthly_contrasts=monthly_contrasts,
        directions=directions,
        outcome_audit=outcome_audit,
    )
    summary["endpoint_reason_recovery"] = recovery_audit

    paths = prepare_output_paths(config, repo_root=root)
    evaluation_dir = paths.data_dir / "evaluation"
    output = config["output"]
    artifact_files = {
        "evaluated_portfolios": atomic_write_parquet(
            evaluated, evaluation_dir / str(output["evaluated_portfolios"])
        ),
        "joined_funded_allocations": atomic_write_parquet(
            joined, evaluation_dir / str(output["joined_funded_allocations"])
        ),
        "window_endpoint_contrasts": atomic_write_parquet(
            window_contrasts, evaluation_dir / str(output["window_endpoint_contrasts"])
        ),
        "monthly_endpoint_contrasts": atomic_write_parquet(
            monthly_contrasts, evaluation_dir / str(output["monthly_endpoint_contrasts"])
        ),
        "metric_direction_census": atomic_write_parquet(
            directions, evaluation_dir / str(output["metric_direction_census"])
        ),
        "outcome_join_audit": atomic_write_parquet(
            outcome_audit, evaluation_dir / str(output["outcome_join_audit"])
        ),
    }
    summary_path = atomic_write_json(
        paths.model_dir / str(output["deterministic_summary"]), summary
    )
    receipt_path = atomic_write_json(
        paths.model_dir / str(output["execution_receipt"]),
        {
            "schema_version": str(config["schema_version"]),
            "status": summary["status"],
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "started_at_utc": started_at,
            "completed_at_utc": utc_now_iso(),
            "elapsed_seconds": float(time.perf_counter() - started),
            "source_frontier_freeze_sha256": str(config["source_frontier"]["freeze"]["sha256"]),
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    manifest = {
        "schema_version": str(config["schema_version"]),
        "status": summary["status"],
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "source_frontier_freeze": dict(config["source_frontier"]["freeze"]),
        "source_artifacts": {
            name: dict(frontier.freeze["outcome_free_artifacts"][name])
            for name in sorted(frontier.artifacts)
        },
        "outcome_columns_joined_after_freeze": list(config["outcomes"]["joined_columns"]),
        "schemas": {
            "evaluated_portfolios": dataframe_schema(evaluated),
            "joined_funded_allocations": dataframe_schema(joined),
            "window_endpoint_contrasts": dataframe_schema(window_contrasts),
            "monthly_endpoint_contrasts": dataframe_schema(monthly_contrasts),
            "metric_direction_census": dataframe_schema(directions),
            "outcome_join_audit": dataframe_schema(outcome_audit),
        },
        "evaluation_artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in artifact_files.items()
        },
        "summary": relative_artifact_descriptor(summary_path, repo_root=root),
        "execution_receipt": relative_artifact_descriptor(receipt_path, repo_root=root),
        "implementation_provenance": implementation_provenance(
            config_path=resolved_config,
            relative_paths=(
                *IMPLEMENTATION_PATHS,
                *[Path(value) for value in config.get("protocol_lineage_files", [])],
            ),
            repo_root=root,
        ),
        "environment": environment_provenance(root),
        "git": git_provenance(root),
        "selection": {
            "policy": None,
            "window": None,
            "ruler": None,
            "coordinate": None,
            "gamma": None,
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    manifest_path = atomic_write_json(
        paths.model_dir / str(output["evaluation_manifest"]), manifest
    )
    logger.info(
        "Frontier evaluation complete: {} portfolios, {} window contrasts in {:.1f}s",
        len(evaluated),
        len(window_contrasts),
        time.perf_counter() - started,
    )
    return manifest_path


def main(argv: Sequence[str] | None = None) -> None:
    """Run the locked post-freeze evaluation."""
    args = parse_args(argv)
    manifest = run_evaluation(config_path=args.config, repo_root=ROOT)
    logger.info("Wrote {}", manifest)


if __name__ == "__main__":
    main()
