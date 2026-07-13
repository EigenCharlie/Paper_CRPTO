"""Run the locked outcome-free IJDS normalized/objective frontier V1c."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ijds_audit.config import load_v4_config  # noqa: E402
from src.ijds_audit.protocol import load_recipes  # noqa: E402
from src.ijds_challengers.archive import (  # noqa: E402
    load_outcome_free_decision_base,
    verified_parent_artifacts,
)
from src.ijds_challengers.config import load_frontier_config  # noqa: E402
from src.ijds_challengers.normalized_frontier import (  # noqa: E402
    FrontierBuild,
    build_outcome_free_frontiers,
)
from src.utils.isolated_experiment import (  # noqa: E402
    OutputPaths,
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    package_version,
    prepare_output_paths as prepare_isolated_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_repo_input,
)
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    utc_now_iso,
)

DEFAULT_CONFIG_PATH = (
    ROOT / "configs/experiments/ijds_normalized_objective_frontier_2026-07-13_v1c.yaml"
)
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
IMPLEMENTATION_PATHS = (
    Path("docs/research/ijds_normalized_objective_frontier_protocol_2026-07-12.md"),
    Path("docs/research/ijds_normalized_objective_frontier_v1_stop_2026-07-13.md"),
    Path("docs/research/ijds_normalized_objective_frontier_v1b_protocol_2026-07-13.md"),
    Path("docs/research/ijds_normalized_objective_frontier_v1b_stop_2026-07-13.md"),
    Path("docs/research/ijds_normalized_objective_frontier_v1c_protocol_2026-07-13.md"),
    Path("docs/research/ijds_decision_method_applicability_2026-07-12.md"),
    Path("scripts/experiments/run_ijds_normalized_objective_frontier.py"),
    Path("src/evaluation/standardized_credit_payoff.py"),
    Path("src/ijds_audit/config.py"),
    Path("src/ijds_audit/portfolio.py"),
    Path("src/ijds_audit/protocol.py"),
    Path("src/ijds_challengers/__init__.py"),
    Path("src/ijds_challengers/archive.py"),
    Path("src/ijds_challengers/config.py"),
    Path("src/ijds_challengers/frontier.py"),
    Path("src/ijds_challengers/normalized_frontier.py"),
    Path("src/models/binary_conformal_guardrail.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("tests/test_ijds_normalized_objective_frontier.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the outcome-free V1 CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    return parser.parse_args(argv)


def prepare_output_paths(
    config: Mapping[str, Any],
    *,
    repo_root: Path = ROOT,
) -> OutputPaths:
    """Create fresh V1 output directories contained in the IJDS experiment roots."""
    return prepare_isolated_output_paths(
        dict(config),
        repo_root=repo_root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )


def _summary(
    build: FrontierBuild,
    *,
    config: Mapping[str, Any],
    parent_freeze: Mapping[str, Any],
    protocol_commit: str,
) -> dict[str, Any]:
    records = build.solve_records
    endpoints = build.endpoint_diagnostics
    optimum = build.objective_optimum_diagnostics
    order = build.order_sensitivity
    validation = build.independent_validation
    degeneracy_tolerance = float(config["solver"]["endpoint_pair_degeneracy_tolerance"])
    ruler_counts = {
        str(ruler): {
            "comparisons": int(len(frame)),
            "nonidentical_comparisons": int(
                (frame["normalized_exposure_distance"] > degeneracy_tolerance).sum()
            ),
            "maximum_exposure_distance": float(frame["normalized_exposure_distance"].max()),
        }
        for ruler, frame in endpoints.groupby("ruler", observed=True, sort=True)
    }
    degenerate_rulers = sorted(
        ruler for ruler, values in ruler_counts.items() if values["nonidentical_comparisons"] == 0
    )
    status = (
        "stopped_outcome_free_endpoint_degeneracy"
        if degenerate_rulers
        else "outcome_free_frontiers_frozen_before_archive_outcome_join"
    )
    return {
        "schema_version": str(config["schema_version"]),
        "status": status,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "lineage": dict(config["lineage"]),
        "parent_run_tag": str(config["parent"]["run_tag"]),
        "parent_protocol_freeze_sha256": str(config["parent"]["protocol_freeze"]["sha256"]),
        "parent_status": parent_freeze.get("status"),
        "counts": {
            "solve_records": int(len(records)),
            "funded_rows": int(len(build.allocations)),
            "endpoint_comparisons": int(len(endpoints)),
            "objective_optimum_diagnostics": int(len(optimum)),
            "order_reruns": int(len(order)),
            "independent_solver_cells": int(len(validation)),
            "windows": int(records["window_id"].nunique()),
            "roles": int(records["role"].nunique()),
            "periods": int(records[["role", "period"]].drop_duplicates().shape[0]),
            "gammas": int(records["gamma"].nunique()),
            "coordinates": int(records["frontier_coordinate"].nunique()),
            "rulers": int(records["frontier_ruler"].nunique()),
        },
        "frontier_ranges": {
            "minimum_score_range": float(records["score_range"].min()),
            "maximum_score_range": float(records["score_range"].max()),
            "minimum_common_objective_range_dollars": float(
                (records["unconstrained_objective"] - records["common_objective_lower"]).min()
            ),
            "maximum_common_objective_range_dollars": float(
                (records["unconstrained_objective"] - records["common_objective_lower"]).max()
            ),
        },
        "objective_optimum_stability": {
            "minimum_absolute_nonbasic_reduced_cost": float(
                optimum["minimum_absolute_nonbasic_reduced_cost"].min()
            ),
            "minimum_scaled_nonbasic_reduced_cost": float(
                optimum["minimum_scaled_nonbasic_reduced_cost"].min()
            ),
            "near_zero_nonbasic_reduced_costs": int(
                optimum["near_zero_nonbasic_reduced_costs"].sum()
            ),
            "primal_degenerate_menus": int(optimum["basis_primal_degenerate"].sum()),
            "maximum_reversed_id_exposure_distance": float(
                optimum["reversed_id_exposure_distance"].max()
            ),
            "maximum_reversed_id_objective_difference_dollars": float(
                optimum["reversed_id_objective_difference"].abs().max()
            ),
        },
        "numerical_reconciliation": {
            "maximum_budget_residual_dollars": float(records["budget_residual"].abs().max()),
            "maximum_constraint_slack_absolute": float(records["constraint_slack"].abs().max()),
            "maximum_order_exposure_distance": float(order["normalized_exposure_distance"].max()),
            "maximum_order_objective_difference_dollars": float(
                order["objective_difference"].abs().max()
            ),
            "maximum_glop_objective_rate_difference": float(
                validation["objective_rate_difference"].abs().max()
            ),
            "maximum_glop_weighted_score_difference": float(
                validation["weighted_score_difference"].abs().max()
            ),
        },
        "endpoint_comparison_by_ruler": ruler_counts,
        "degenerate_rulers": degenerate_rulers,
        "outcome_columns_passed": [],
        "policy_selection": None,
        "policy_winner": None,
        "conformal_guarantee_repair": False,
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }


def run_outcome_free(
    *,
    config_path: Path,
    repo_root: Path = ROOT,
) -> Path:
    """Verify sources, solve the complete census, and atomically freeze V1c."""
    started = time.perf_counter()
    started_at = utc_now_iso()
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_frontier_config(resolved_config)
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))
    parent_paths, parent_freeze = verified_parent_artifacts(config, repo_root=root)
    parent_config_path = resolve_repo_input(str(config["parent"]["config"]), repo_root=root)
    parent_config = load_v4_config(parent_config_path)
    raw_path = resolve_repo_input(str(config["source_ingest"]["raw_path"]), repo_root=root)
    base = load_outcome_free_decision_base(
        scores_path=parent_paths["scores"],
        raw_path=raw_path,
        config=config,
    )
    recipes = load_recipes(parent_paths["recipes"])
    build = build_outcome_free_frontiers(
        base,
        recipes,
        config=config,
        parent_config=parent_config,
    )
    summary = _summary(
        build,
        config=config,
        parent_freeze=parent_freeze,
        protocol_commit=protocol_commit,
    )
    paths = prepare_output_paths(config, repo_root=root)
    frontier_dir = paths.data_dir / "frontier"
    output = config["output"]
    artifact_files = {
        "solve_records": atomic_write_parquet(
            build.solve_records,
            frontier_dir / str(output["solve_records"]),
        ),
        "allocations": atomic_write_parquet(
            build.allocations,
            frontier_dir / str(output["allocations"]),
        ),
        "endpoint_diagnostics": atomic_write_parquet(
            build.endpoint_diagnostics,
            frontier_dir / str(output["endpoint_diagnostics"]),
        ),
        "objective_optimum_diagnostics": atomic_write_parquet(
            build.objective_optimum_diagnostics,
            frontier_dir / str(output["objective_optimum_diagnostics"]),
        ),
        "order_sensitivity": atomic_write_parquet(
            build.order_sensitivity,
            frontier_dir / str(output["order_sensitivity"]),
        ),
        "independent_validation": atomic_write_parquet(
            build.independent_validation,
            frontier_dir / str(output["independent_validation"]),
        ),
    }
    summary_path = atomic_write_json(
        paths.model_dir / str(output["deterministic_summary"]),
        summary,
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
            "outcome_columns_passed": [],
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    implementation = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    environment = environment_provenance(root)
    environment["packages"]["ortools"] = package_version("ortools")
    freeze = {
        "schema_version": str(config["schema_version"]),
        "status": summary["status"],
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "lineage": dict(config["lineage"]),
        "parent": {
            "run_tag": str(config["parent"]["run_tag"]),
            "protocol_freeze": dict(config["parent"]["protocol_freeze"]),
        },
        "outcome_columns_passed_to_frontier": [],
        "policy_selection": None,
        "window_selection": None,
        "ruler_selection": None,
        "implementation_provenance": implementation,
        "environment": environment,
        "git": git_provenance(root),
        "schemas": {
            "solve_records": dataframe_schema(build.solve_records),
            "allocations": dataframe_schema(build.allocations),
            "endpoint_diagnostics": dataframe_schema(build.endpoint_diagnostics),
            "objective_optimum_diagnostics": dataframe_schema(build.objective_optimum_diagnostics),
            "order_sensitivity": dataframe_schema(build.order_sensitivity),
            "independent_validation": dataframe_schema(build.independent_validation),
        },
        "outcome_free_artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in artifact_files.items()
        },
        "summary": relative_artifact_descriptor(summary_path, repo_root=root),
        "execution_receipt": relative_artifact_descriptor(receipt_path, repo_root=root),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    freeze_path = atomic_write_json(paths.model_dir / "protocol_freeze.json", freeze)
    logger.info(
        "Outcome-free frontier {}: {} records, {} funded rows in {:.1f}s",
        summary["status"],
        len(build.solve_records),
        len(build.allocations),
        time.perf_counter() - started,
    )
    return freeze_path


def main(argv: Sequence[str] | None = None) -> None:
    """Run the locked V1 outcome-free phase."""
    args = parse_args(argv)
    freeze = run_outcome_free(config_path=args.config, repo_root=ROOT)
    logger.info("Wrote {}", freeze)


if __name__ == "__main__":
    main()
