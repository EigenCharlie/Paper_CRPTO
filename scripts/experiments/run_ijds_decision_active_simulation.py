"""Run the locked decision-active IJDS mechanism simulation."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ijds_audit.config import load_v4_config  # noqa: E402
from src.ijds_audit.decision_simulation import (  # noqa: E402
    FACTOR_COLUMNS,
    run_decision_active_simulation,
    validate_locked_decision_active_config,
)
from src.utils.isolated_experiment import (  # noqa: E402
    OutputPaths,
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
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

DEFAULT_CONFIG_PATH = ROOT / "configs/experiments/ijds_decision_active_simulation_2026-07-12.yaml"
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
IMPLEMENTATION_PATHS = (
    Path("configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-12.yaml"),
    Path("docs/research/ijds_binary_geometry_frontier_v4_protocol_2026-07-12.md"),
    Path("docs/research/ijds_decision_active_simulation_protocol_2026-07-12.md"),
    Path("scripts/experiments/run_ijds_decision_active_simulation.py"),
    Path("src/evaluation/standardized_credit_payoff.py"),
    Path("src/ijds_audit/config.py"),
    Path("src/ijds_audit/decision_simulation.py"),
    Path("src/ijds_audit/geometry.py"),
    Path("src/ijds_audit/portfolio.py"),
    Path("src/models/binary_conformal_guardrail.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("tests/test_ijds_decision_active_simulation.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)
METRICS = ("payoff", "default", "miscoverage")
COMPARATORS = ("c0", "c2")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the locked simulation CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    return parser.parse_args(argv)


def prepare_output_paths(config: Mapping[str, Any], *, repo_root: Path = ROOT) -> OutputPaths:
    """Create fresh, contained experiment directories."""
    return prepare_isolated_output_paths(
        dict(config),
        repo_root=repo_root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return json.loads(frame.to_json(orient="records", double_precision=15))


def _direction_counts(repetitions: pd.DataFrame, *, tolerance: float) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for comparator in COMPARATORS:
        for metric in METRICS:
            lower = repetitions[f"guardrail_minus_{comparator}_{metric}_lower"]
            upper = repetitions[f"guardrail_minus_{comparator}_{metric}_upper"]
            direction = np.select(
                [lower > tolerance, upper < -tolerance],
                ["guardrail_higher", "guardrail_lower"],
                default="crosses_zero",
            )
            work = repetitions.loc[:, list(FACTOR_COLUMNS)].assign(direction=direction)
            counts = (
                work.groupby([*FACTOR_COLUMNS, "direction"], observed=True, sort=True)
                .size()
                .rename("repetitions")
                .reset_index()
            )
            counts.insert(0, "metric", metric)
            counts.insert(0, "comparator", comparator.upper())
            parts.append(counts)
    return pd.concat(parts, ignore_index=True)


def _assert_complete(
    repetitions: pd.DataFrame,
    cell_summary: pd.DataFrame,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    simulation = config["decision_active_simulation"]
    if len(repetitions) != 3_600 or len(cell_summary) != 72:
        raise RuntimeError(
            f"Incomplete decision-active factorial: {len(repetitions)} rows, "
            f"{len(cell_summary)} cells."
        )
    cell_sizes = repetitions.groupby(list(FACTOR_COLUMNS), observed=True).size()
    if not bool(cell_sizes.eq(50).all()):
        raise RuntimeError("Every decision-active cell must contain 50 repetitions.")

    binding_tolerance = float(simulation["binding_tolerance"])
    c2_tolerance = float(simulation["c2_match_tolerance"])
    dominance_tolerance = float(simulation["objective_dominance_tolerance"])
    maximum_budget_residual = float(
        repetitions[["guardrail_budget_residual", "c0_budget_residual", "c2_budget_residual"]]
        .abs()
        .to_numpy()
        .max()
    )
    checks = {
        "factorial_rows": int(len(repetitions)),
        "factorial_cells": int(len(cell_summary)),
        "repetitions_per_cell_min": int(cell_sizes.min()),
        "repetitions_per_cell_max": int(cell_sizes.max()),
        "all_guardrail_caps_binding": bool(repetitions["guardrail_cap_binding"].all()),
        "maximum_absolute_guardrail_cap_slack": float(
            repetitions["guardrail_cap_slack"].abs().max()
        ),
        "maximum_absolute_budget_residual": maximum_budget_residual,
        "maximum_absolute_c2_match_residual": float(repetitions["c2_match_residual"].abs().max()),
        "minimum_c0_point_objective_dominance": float(
            repetitions["c0_point_minus_guardrail_objective"].min()
        ),
        "minimum_c2_point_objective_dominance": float(
            repetitions["point_minus_guardrail_objective"].min()
        ),
        "paired_fit_prevalence": bool(
            repetitions.groupby("repetition")["fit_prevalence"].nunique().eq(1).all()
        ),
        "paired_outcome_free_geometry": bool(
            repetitions.groupby(["repetition", "score_shift", "taxonomy_groups"], observed=True)[
                ["mean_width", "upper_saturated_share"]
            ]
            .nunique()
            .eq(1)
            .all()
            .all()
        ),
        "paired_complete_outcomes_across_cap_and_censoring": bool(
            repetitions.groupby(
                [
                    "repetition",
                    "score_shift",
                    "calibration_log_odds_shift",
                    "taxonomy_groups",
                ],
                observed=True,
            )[["candidate_outcome_prevalence", "candidate_coverage_full"]]
            .nunique()
            .eq(1)
            .all()
            .all()
        ),
    }
    failures = []
    if not checks["all_guardrail_caps_binding"]:
        failures.append("guardrail cap binding")
    if checks["maximum_absolute_guardrail_cap_slack"] > binding_tolerance:
        failures.append("guardrail cap tolerance")
    if maximum_budget_residual > 1e-8:
        failures.append("full budget")
    if checks["maximum_absolute_c2_match_residual"] > c2_tolerance:
        failures.append("C2 moment match")
    if checks["minimum_c0_point_objective_dominance"] < -dominance_tolerance:
        failures.append("C0 objective dominance")
    if checks["minimum_c2_point_objective_dominance"] < -dominance_tolerance:
        failures.append("C2 objective dominance")
    for key in (
        "paired_fit_prevalence",
        "paired_outcome_free_geometry",
        "paired_complete_outcomes_across_cap_and_censoring",
    ):
        if not checks[key]:
            failures.append(key)
    if failures:
        raise RuntimeError(f"Decision-active structural checks failed: {failures}.")
    return checks


def _compact_results(repetitions: pd.DataFrame, direction_counts: pd.DataFrame) -> dict[str, Any]:
    allocation = (
        repetitions.groupby(
            ["taxonomy_groups", "normalized_cap_position"], observed=True, sort=True
        )
        .agg(
            c0_distance_mean=("c0_allocation_distance", "mean"),
            c0_changed_rate=("c0_allocation_changed", "mean"),
            c2_distance_mean=("c2_allocation_distance", "mean"),
            c2_changed_rate=("c2_allocation_changed", "mean"),
            c0_same_numeric_cap_slack_mean=("c0_same_numeric_cap_slack", "mean"),
        )
        .reset_index()
    )
    coverage = (
        repetitions.groupby(
            ["score_shift", "calibration_log_odds_shift", "taxonomy_groups"],
            observed=True,
            sort=True,
        )
        .agg(
            full_coverage_mean=("candidate_coverage_full", "mean"),
            full_coverage_min=("candidate_coverage_full", "min"),
            full_coverage_max=("candidate_coverage_full", "max"),
            mean_width=("mean_width", "mean"),
            both_set_share=("set_both_share", "mean"),
        )
        .reset_index()
    )
    global_directions = (
        direction_counts.groupby(["comparator", "metric", "direction"], observed=True)[
            "repetitions"
        ]
        .sum()
        .reset_index()
    )
    return {
        "allocation_by_taxonomy_and_cap": _records(allocation),
        "coverage_by_shift_and_taxonomy": _records(coverage),
        "global_bound_direction_census": _records(global_directions),
        "c0_allocation_changed_rate": float(repetitions["c0_allocation_changed"].mean()),
        "c2_allocation_changed_rate": float(repetitions["c2_allocation_changed"].mean()),
    }


def run_simulation(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Execute the tagged full factorial and return its deterministic summary."""
    started_at = utc_now_iso()
    started_counter = time.perf_counter()
    config_path = resolve_repo_input(config_path, repo_root=repo_root)
    config = load_v4_config(config_path)
    validate_locked_decision_active_config(config)
    protocol_commit = require_clean_tagged_head(repo_root, str(config["protocol_tag"]))
    initial_git = git_provenance(repo_root)
    implementation_start = implementation_provenance(
        config_path=config_path,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=repo_root,
    )
    paths = prepare_output_paths(config, repo_root=repo_root)
    protocol_freeze = atomic_write_json(
        paths.model_dir / "protocol_freeze.json",
        {
            "schema_version": str(config["schema_version"]),
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "hypothesis": str(config["hypothesis"]),
            "decision_active_simulation": dict(config["decision_active_simulation"]),
            "implementation_provenance": implementation_start,
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )

    logger.info("Running 72 paired cells and 3,600 decision-active repetitions")
    repetitions, cell_summary = run_decision_active_simulation(config)
    checks = _assert_complete(repetitions, cell_summary, config)
    direction_counts = _direction_counts(repetitions, tolerance=1e-12)

    output = config["output"]
    frames = {
        str(output["repetitions"]): repetitions,
        str(output["cell_summary"]): cell_summary,
        str(output["direction_counts"]): direction_counts,
    }
    written: dict[Path, pd.DataFrame] = {}
    for filename, frame in frames.items():
        path = atomic_write_parquet(frame, paths.data_dir / filename, index=False)
        written[path] = frame
    artifacts = {
        descriptor["path"]: descriptor
        for descriptor in [
            relative_artifact_descriptor(protocol_freeze, repo_root=repo_root),
            *(relative_artifact_descriptor(path, repo_root=repo_root) for path in written),
        ]
    }
    schemas = {
        relative_artifact_descriptor(path, repo_root=repo_root)["path"]: dataframe_schema(frame)
        for path, frame in written.items()
    }
    implementation_end = implementation_provenance(
        config_path=config_path,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=repo_root,
    )
    if implementation_end != implementation_start:
        raise RuntimeError("Decision-active implementation changed during execution.")

    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "hypothesis": str(config["hypothesis"]),
        "claim_boundary": (
            "Synthetic mechanism evidence only. It cannot validate an empirical sign, "
            "a policy winner, selected-set conformal coverage, a causal effect, or an "
            "investor return in Lending Club."
        ),
        "factor_pairing": str(config["decision_active_simulation"]["factor_pairing"]),
        "structural_checks": checks,
        "results": _compact_results(repetitions, direction_counts),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
        "config": relative_artifact_descriptor(config_path, repo_root=repo_root),
        "implementation_provenance": implementation_start,
        "artifacts": artifacts,
        "schemas": schemas,
    }
    summary_path = atomic_write_json(paths.model_dir / str(output["deterministic_result"]), summary)
    receipt = {
        "run_tag": str(config["run_tag"]),
        "started_at_utc": started_at,
        "completed_at_utc": utc_now_iso(),
        "runtime_seconds": float(time.perf_counter() - started_counter),
        "initial_git": initial_git,
        "final_git": git_provenance(repo_root),
        "environment": environment_provenance(repo_root),
        "deterministic_summary": relative_artifact_descriptor(summary_path, repo_root=repo_root),
    }
    atomic_write_json(paths.model_dir / str(output["execution_receipt"]), receipt)
    logger.info("Decision-active simulation complete: {}", summary_path)
    return summary_path


def main(argv: Sequence[str] | None = None) -> None:
    """Run the CLI entry point."""
    args = parse_args(argv)
    run_simulation(config_path=args.config)


if __name__ == "__main__":
    main()
