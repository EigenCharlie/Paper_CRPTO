"""Freeze and evaluate the complete IJDS portfolio-structure sensitivity grid."""

from __future__ import annotations

import argparse
import copy
import json
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from loguru import logger

from src.ijds_audit.config import load_v4_config
from src.ijds_audit.endpoint_sensitivity import rebuild_archive_outcomes
from src.ijds_audit.evaluation import evaluate_frozen_portfolios
from src.ijds_audit.protocol import load_outcome_universe, load_recipes
from src.ijds_audit.structural_sensitivity import (
    allocation_activity,
    declared_scenarios,
    scenario_result_summary,
)
from src.ijds_challengers.archive import (
    load_outcome_free_decision_base,
    verified_parent_artifacts,
)
from src.ijds_challengers.config import load_frontier_config
from src.ijds_challengers.evaluation import build_endpoint_contrasts, build_metric_directions
from src.ijds_challengers.evaluation_config import load_v2_config
from src.ijds_challengers.normalized_frontier import build_outcome_free_frontiers
from src.utils.isolated_experiment import (
    OutputPaths,
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    prepare_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_isolated_run_dir,
    resolve_repo_input,
    sha256_file,
)
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_parquet, utc_now_iso

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = (
    ROOT / "configs/experiments/ijds_portfolio_structure_sensitivity_2026-07-15_v2.yaml"
)
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
ARTIFACT_NAMES = (
    "solve_records",
    "allocations",
    "endpoint_diagnostics",
    "minimum_endpoint_diagnostics",
    "objective_optimum_diagnostics",
    "order_sensitivity",
    "independent_validation",
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the structural-sensitivity CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--phase", choices=("freeze", "evaluate"), required=True)
    return parser.parse_args(argv)


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Structural-sensitivity config must be a mapping.")
    allowed_statuses = {
        "locked_retrospective_outcome_free_structural_sensitivity",
        "locked_retrospective_outcome_free_structural_sensitivity_v2",
    }
    if payload.get("protocol_status") not in allowed_statuses:
        raise ValueError("Structural-sensitivity protocol is not locked.")
    scenarios = declared_scenarios(payload)
    if int(payload["structural_grid"].get("scenarios", -1)) != len(scenarios):
        raise ValueError("Declared structural scenario count changed.")
    boundary = payload.get("claim_boundary", {})
    required_false = {
        "preregistered",
        "confirmatory",
        "prospective",
        "outcome_based_scenario_selection",
        "model_refit",
        "conformal_refit",
        "ruler_selection",
        "scenario_selection",
        "policy_winner",
    }
    if any(boundary.get(field) is not False for field in required_false):
        raise ValueError("Structural-sensitivity claim boundary changed.")
    if (
        payload.get("protocol_status")
        == "locked_retrospective_outcome_free_structural_sensitivity_v2"
    ):
        numerics = payload.get("numerics", {})
        if float(numerics.get("minimum_endpoint_retry_slack", -1.0)) != 1.0e-12:
            raise ValueError("V2 must retain the locked 1e-12 endpoint retry slack.")
        if numerics.get("retry_scope") != "known_exact_minimum_boundary_failure_only":
            raise ValueError("V2 endpoint retry scope changed.")
    return payload


def _run_paths(config: Mapping[str, Any], *, repo_root: Path) -> OutputPaths:
    output = config["output"]
    run_tag = str(config["run_tag"])
    return OutputPaths(
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


def _frontier_config(base: Mapping[str, Any], structural: Mapping[str, Any]) -> dict[str, Any]:
    config = copy.deepcopy(dict(base))
    grid = structural["structural_grid"]
    config["frontier"]["roles"] = [str(value) for value in grid["roles"]]
    config["frontier"]["gamma_grid"] = [float(value) for value in grid["state_gamma_grid"]]
    config["frontier"]["reported_gamma_grid"] = [
        float(value) for value in grid["reported_gamma_grid"]
    ]
    config["frontier"]["coordinate_grid"] = [float(value) for value in grid["coordinates"]]
    retry_slack = float(structural.get("numerics", {}).get("minimum_endpoint_retry_slack", 0.0))
    config["frontier"]["normalized_score"]["minimum_endpoint_retry_slack"] = retry_slack
    return config


def _scenario_parent(base: Mapping[str, Any], scenario: Mapping[str, Any]) -> dict[str, Any]:
    config = copy.deepcopy(dict(base))
    config["policy"]["budget"] = float(scenario["budget"])
    config["policy"]["max_concentration_by_purpose"] = float(scenario["purpose_cap"])
    config["payoff"]["lgd"] = float(scenario["lgd"])
    return config


def _tag(frame: pd.DataFrame, scenario: Mapping[str, Any]) -> pd.DataFrame:
    return frame.assign(
        scenario_id=str(scenario["scenario_id"]),
        scenario_budget=float(scenario["budget"]),
        scenario_purpose_cap=float(scenario["purpose_cap"]),
        scenario_lgd=float(scenario["lgd"]),
        scenario_is_baseline=bool(scenario["is_baseline"]),
    )


def _write_build(
    build: Any,
    *,
    data_dir: Path,
    scenario: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    scenario_dir = data_dir / "scenarios" / str(scenario["scenario_id"]) / "frontier"
    frames = {
        "solve_records": build.solve_records,
        "allocations": build.allocations,
        "endpoint_diagnostics": build.endpoint_diagnostics,
        "minimum_endpoint_diagnostics": build.minimum_endpoint_diagnostics,
        "objective_optimum_diagnostics": build.objective_optimum_diagnostics,
        "order_sensitivity": build.order_sensitivity,
        "independent_validation": build.independent_validation,
    }
    descriptors: dict[str, Any] = {}
    for name, frame in frames.items():
        path = atomic_write_parquet(_tag(frame, scenario), scenario_dir / f"{name}.parquet")
        descriptors[name] = relative_artifact_descriptor(path, repo_root=repo_root)
    return descriptors


def freeze(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Build and hash-freeze every structural allocation before outcomes."""
    started = time.perf_counter()
    started_at = utc_now_iso()
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
    parent = config["parent"]
    raw_path = resolve_repo_input(str(parent["raw_path"]), repo_root=root)
    if sha256_file(raw_path) != str(parent["raw_sha256"]):
        raise RuntimeError("Raw archive hash changed before structural freeze.")
    source_frontier_config = load_frontier_config(
        resolve_repo_input(str(parent["frontier_config"]), repo_root=root)
    )
    parent_paths, parent_freeze = verified_parent_artifacts(source_frontier_config, repo_root=root)
    v4_config = load_v4_config(resolve_repo_input(str(parent["v4_config"]), repo_root=root))
    base = load_outcome_free_decision_base(
        scores_path=parent_paths["scores"],
        raw_path=raw_path,
        config=source_frontier_config,
    )
    recipes = load_recipes(parent_paths["recipes"])
    build_config = _frontier_config(source_frontier_config, config)
    scenario_artifacts: dict[str, Any] = {}
    scenario_counts: list[dict[str, Any]] = []
    for index, scenario in enumerate(declared_scenarios(config), start=1):
        logger.info("Structural freeze scenario {}/36: {}", index, scenario["scenario_id"])
        build = build_outcome_free_frontiers(
            base,
            recipes,
            config=build_config,
            parent_config=_scenario_parent(v4_config, scenario),
        )
        scenario_artifacts[str(scenario["scenario_id"])] = _write_build(
            build,
            data_dir=paths.data_dir,
            scenario=scenario,
            repo_root=root,
        )
        scenario_counts.append(
            {
                **dict(scenario),
                "solve_records": int(len(build.solve_records)),
                "funded_rows": int(len(build.allocations)),
                "endpoint_cells": int(len(build.endpoint_diagnostics)),
                "minimum_endpoint_cells": int(len(build.minimum_endpoint_diagnostics)),
                "minimum_endpoint_retries": int(
                    build.minimum_endpoint_diagnostics["minimum_endpoint_retried"].sum()
                ),
                "maximum_minimum_endpoint_retry_slack": float(
                    build.minimum_endpoint_diagnostics["minimum_endpoint_retry_slack"].max()
                ),
                "outcome_columns_passed": [],
            }
        )
    counts_path = atomic_write_parquet(
        pd.DataFrame(scenario_counts), paths.data_dir / "frontier/scenario_counts.parquet"
    )
    freeze_payload = {
        "schema_version": str(config["schema_version"]),
        "status": "outcome_free_structural_grid_frozen_before_endpoint_join",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "started_at_utc": started_at,
        "completed_at_utc": utc_now_iso(),
        "elapsed_seconds": float(time.perf_counter() - started),
        "claim_boundary": dict(config["claim_boundary"]),
        "numerics": dict(config.get("numerics", {})),
        "source_frontier_freeze": {
            "status": parent_freeze["status"],
            "run_tag": parent_freeze["run_tag"],
            "sha256": source_frontier_config["parent"]["protocol_freeze"]["sha256"],
        },
        "scenario_count": len(scenario_artifacts),
        "outcome_columns_passed_to_frontier": [],
        "scenario_artifacts": scenario_artifacts,
        "scenario_counts": relative_artifact_descriptor(counts_path, repo_root=root),
        "implementation": implementation_provenance(
            config_path=resolved_config,
            repo_root=root,
            relative_paths=(
                Path("src/ijds_audit/structural_sensitivity.py"),
                Path("src/ijds_challengers/normalized_frontier.py"),
                Path("scripts/experiments/run_ijds_portfolio_structure_sensitivity.py"),
                Path(
                    str(
                        config.get(
                            "protocol_document",
                            "docs/research/ijds_portfolio_structure_sensitivity_protocol_2026-07-14.md",
                        )
                    )
                ),
            ),
        ),
        "environment": environment_provenance(root),
        "git": git_provenance(root),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    freeze_path = atomic_write_json(paths.model_dir / "protocol_freeze.json", freeze_payload)
    logger.info("Structural grid frozen at {}", freeze_path)
    return freeze_path


def _verified_structural_freeze(
    config: Mapping[str, Any], *, repo_root: Path
) -> tuple[OutputPaths, dict[str, Any]]:
    paths = _run_paths(config, repo_root=repo_root)
    freeze_path = paths.model_dir / "protocol_freeze.json"
    payload = json.loads(freeze_path.read_text(encoding="utf-8"))
    expected = {
        "status": "outcome_free_structural_grid_frozen_before_endpoint_join",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise RuntimeError(f"Structural freeze mismatch for {field}.")
    if payload.get("outcome_columns_passed_to_frontier") != []:
        raise RuntimeError("Structural freeze reports outcome leakage.")
    if int(payload.get("scenario_count", -1)) != len(declared_scenarios(config)):
        raise RuntimeError("Structural freeze scenario census changed.")
    for artifacts in payload["scenario_artifacts"].values():
        if set(artifacts) != set(ARTIFACT_NAMES):
            raise RuntimeError("Structural scenario artifact inventory changed.")
        for descriptor in artifacts.values():
            path = resolve_repo_input(str(descriptor["path"]), repo_root=repo_root)
            if relative_artifact_descriptor(path, repo_root=repo_root) != descriptor:
                raise RuntimeError(f"Structural artifact changed: {descriptor['path']}.")
    return paths, payload


def _evaluation_contract(base: Mapping[str, Any]) -> dict[str, Any]:
    config = copy.deepcopy(dict(base))
    config["evaluation"]["evaluated_roles"] = ["primary_oot"]
    config["evaluation"]["expected_solve_records"] = 8 * 15 * 2 * 3 * 2
    config["evaluation"]["expected_window_contrasts"] = 8 * 3 * 2
    config["evaluation"]["expected_monthly_contrasts"] = 8 * 15 * 3 * 2
    config["evaluation"]["expected_metric_directions"] = 8 * 3 * 2 * 3
    config["evaluation"]["expected_candidate_counts"] = {"primary_oot": 376_890}
    return config


def _baseline_reconciliation(
    baseline: pd.DataFrame,
    *,
    active_run_tag: str,
    repo_root: Path,
) -> dict[str, float]:
    active_path = (
        repo_root
        / "data/processed/experiments/ijds_audit"
        / active_run_tag
        / "evaluation/window_endpoint_contrasts.parquet"
    )
    active = pd.read_parquet(active_path)
    keys = ["window_id", "ruler", "coordinate"]
    left = baseline.sort_values(keys).reset_index(drop=True)
    right = active.sort_values(keys).reset_index(drop=True)
    if not left[keys].equals(right[keys]):
        raise RuntimeError("Structural baseline keys differ from the active two-ruler result.")
    columns = [
        "realized_payoff_difference_lower",
        "realized_payoff_difference_upper",
        "weighted_default_difference_lower",
        "weighted_default_difference_upper",
        "weighted_miscoverage_difference_lower",
        "weighted_miscoverage_difference_upper",
    ]
    differences = {
        column: float(
            np.max(np.abs(left[column].to_numpy(dtype=float) - right[column].to_numpy(dtype=float)))
        )
        for column in columns
    }
    if max(differences.values()) > 1e-8:
        raise RuntimeError(f"Structural baseline failed active reconciliation: {differences}.")
    return differences


def evaluate(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Verify the structural freeze, join one endpoint, and report every scenario."""
    started = time.perf_counter()
    started_at = utc_now_iso()
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = _load_config(resolved_config)
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))
    paths, frozen = _verified_structural_freeze(config, repo_root=root)
    summary_path = paths.model_dir / "structural_sensitivity_summary.json"
    if summary_path.exists() or (paths.data_dir / "evaluation").exists():
        raise FileExistsError("Structural evaluation already exists; choose a fresh run tag.")
    parent = config["parent"]
    raw_path = resolve_repo_input(str(parent["raw_path"]), repo_root=root)
    if sha256_file(raw_path) != str(parent["raw_sha256"]):
        raise RuntimeError("Raw archive hash changed before structural evaluation.")
    v4_config = load_v4_config(resolve_repo_input(str(parent["v4_config"]), repo_root=root))
    active_evaluation = load_v2_config(
        resolve_repo_input(str(parent["evaluation_config"]), repo_root=root)
    )
    evaluation_config = _evaluation_contract(active_evaluation)
    universe = load_outcome_universe(v4_config, raw_path=raw_path)
    outcomes = rebuild_archive_outcomes(
        universe,
        evaluation_cutoff=str(config["endpoint"]["evaluation_cutoff"]),
        charged_off_lag_months=int(config["endpoint"]["charged_off_lag_months"]),
    )
    scenario_results: list[dict[str, Any]] = []
    activity_rows: list[dict[str, Any]] = []
    contrast_frames: list[pd.DataFrame] = []
    direction_frames: list[pd.DataFrame] = []
    evaluation_artifacts: dict[str, Any] = {}
    scenarios = declared_scenarios(config)
    scenario_lookup = {str(item["scenario_id"]): item for item in scenarios}
    for index, scenario_id in enumerate(sorted(frozen["scenario_artifacts"]), start=1):
        scenario = scenario_lookup[scenario_id]
        logger.info("Structural evaluation scenario {}/36: {}", index, scenario_id)
        descriptors = frozen["scenario_artifacts"][scenario_id]
        records = pd.read_parquet(
            resolve_repo_input(descriptors["solve_records"]["path"], repo_root=root)
        )
        allocations = pd.read_parquet(
            resolve_repo_input(descriptors["allocations"]["path"], repo_root=root)
        )
        endpoints = pd.read_parquet(
            resolve_repo_input(descriptors["endpoint_diagnostics"]["path"], repo_root=root)
        )
        scenario_parent = _scenario_parent(v4_config, scenario)
        evaluated, joined = evaluate_frozen_portfolios(
            records,
            allocations,
            outcomes,
            config=scenario_parent,
        )
        window, monthly = build_endpoint_contrasts(
            joined,
            endpoints,
            config=evaluation_config,
            lgd=float(scenario["lgd"]),
        )
        directions = build_metric_directions(window, config=evaluation_config)
        expected = {
            "evaluated": 8 * 15 * 2 * 3 * 2,
            "window": 8 * 3 * 2,
            "monthly": 8 * 15 * 3 * 2,
            "directions": 8 * 3 * 2 * 3,
        }
        actual = {
            "evaluated": len(evaluated),
            "window": len(window),
            "monthly": len(monthly),
            "directions": len(directions),
        }
        if actual != expected:
            raise RuntimeError(f"Incomplete structural evaluation for {scenario_id}: {actual}.")
        activity = allocation_activity(
            records,
            allocations,
            scenario=scenario,
            allocation_tolerance=float(
                load_frontier_config(
                    resolve_repo_input(str(parent["frontier_config"]), repo_root=root)
                )["solver"]["allocation_tolerance"]
            ),
        )
        activity_rows.append(activity)
        scenario_results.append(
            {
                **scenario_result_summary(window, directions, scenario=scenario),
                **{
                    f"activity_{key}": value
                    for key, value in activity.items()
                    if key not in scenario
                },
            }
        )
        tagged_window = _tag(window, scenario)
        tagged_directions = _tag(directions, scenario)
        contrast_frames.append(tagged_window)
        direction_frames.append(tagged_directions)
        scenario_dir = paths.data_dir / "evaluation/scenarios" / scenario_id
        window_path = atomic_write_parquet(tagged_window, scenario_dir / "window_contrasts.parquet")
        direction_path = atomic_write_parquet(
            tagged_directions, scenario_dir / "metric_directions.parquet"
        )
        evaluation_artifacts[scenario_id] = {
            "window_contrasts": relative_artifact_descriptor(window_path, repo_root=root),
            "metric_directions": relative_artifact_descriptor(direction_path, repo_root=root),
        }
    summary_table = pd.DataFrame(scenario_results).sort_values("scenario_id").reset_index(drop=True)
    activity_table = pd.DataFrame(activity_rows).sort_values("scenario_id").reset_index(drop=True)
    contrast_table = pd.concat(contrast_frames, ignore_index=True)
    direction_table = pd.concat(direction_frames, ignore_index=True)
    consolidated = {
        "scenario_summary": atomic_write_parquet(
            summary_table, paths.data_dir / "evaluation/scenario_summary.parquet"
        ),
        "allocation_activity": atomic_write_parquet(
            activity_table, paths.data_dir / "evaluation/allocation_activity.parquet"
        ),
        "window_contrasts": atomic_write_parquet(
            contrast_table, paths.data_dir / "evaluation/window_contrasts.parquet"
        ),
        "metric_directions": atomic_write_parquet(
            direction_table, paths.data_dir / "evaluation/metric_directions.parquet"
        ),
    }
    baseline = contrast_table.loc[contrast_table["scenario_is_baseline"]]
    reconciliation = _baseline_reconciliation(
        baseline,
        active_run_tag=str(active_evaluation["run_tag"]),
        repo_root=root,
    )
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_post_freeze_structural_sensitivity_evaluation",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "started_at_utc": started_at,
        "completed_at_utc": utc_now_iso(),
        "elapsed_seconds": float(time.perf_counter() - started),
        "claim_boundary": dict(config["claim_boundary"]),
        "scenario_count": int(len(summary_table)),
        "baseline_reconciliation_maxima": reconciliation,
        "outcome_columns_joined_after_freeze": ["snapshot_default", "snapshot_resolution"],
        "artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in consolidated.items()
        },
        "schemas": {
            "scenario_summary": dataframe_schema(summary_table),
            "allocation_activity": dataframe_schema(activity_table),
            "window_contrasts": dataframe_schema(contrast_table),
            "metric_directions": dataframe_schema(direction_table),
        },
        "selection": {"scenario": None, "budget": None, "purpose_cap": None, "lgd": None},
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    written = atomic_write_json(summary_path, summary)
    atomic_write_json(
        paths.model_dir / "verified_evaluation_manifest.json",
        {
            **summary,
            "source_freeze": relative_artifact_descriptor(
                paths.model_dir / "protocol_freeze.json", repo_root=root
            ),
            "scenario_artifacts": evaluation_artifacts,
            "implementation": implementation_provenance(
                config_path=resolved_config,
                repo_root=root,
                relative_paths=(
                    Path("src/ijds_audit/structural_sensitivity.py"),
                    Path("scripts/experiments/run_ijds_portfolio_structure_sensitivity.py"),
                    Path(
                        str(
                            config.get(
                                "protocol_document",
                                "docs/research/ijds_portfolio_structure_sensitivity_protocol_2026-07-14.md",
                            )
                        )
                    ),
                ),
            ),
            "environment": environment_provenance(root),
            "git": git_provenance(root),
        },
    )
    logger.info("Wrote structural sensitivity {}", written)
    return written


def main(argv: Sequence[str] | None = None) -> None:
    """Run one structural-sensitivity phase."""
    args = parse_args(argv)
    if args.phase == "freeze":
        freeze(config_path=args.config, repo_root=ROOT)
    else:
        evaluate(config_path=args.config, repo_root=ROOT)


if __name__ == "__main__":
    main()
