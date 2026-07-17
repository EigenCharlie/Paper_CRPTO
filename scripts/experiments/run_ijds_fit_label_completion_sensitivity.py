"""Run the two-phase fitting-label completion sensitivity."""

from __future__ import annotations

import argparse
import copy
import json
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.ijds_audit.config import load_v4_config
from src.ijds_audit.evaluation import temporal_coverage_audit
from src.ijds_audit.fit_label_sensitivity import (
    FIT_LABEL_SCENARIOS,
    apply_fit_label_scenario,
    summarize_fit_label_coverage,
)
from src.ijds_audit.prediction import fit_primary_scores, fit_window_recipes, prepare_data
from src.ijds_audit.protocol import (
    configured_archive_outcomes,
    load_outcome_universe,
    load_recipes,
    recipe_payload,
    verified_freeze_artifact_paths,
)
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
DEFAULT_CONFIG = ROOT / "configs/experiments/ijds_fit_label_completion_sensitivity_2026-07-16.yaml"
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
LEARNER_PREFIX = "fit_label_"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("freeze", "evaluate"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Fitting-label completion config must be a mapping.")
    sensitivity = payload.get("fit_label_completion", {})
    if tuple(sensitivity.get("scenarios", ())) != FIT_LABEL_SCENARIOS:
        raise ValueError("Fitting-label scenarios must remain the complete declared family.")
    if sensitivity.get("outcome_based_selection") is not False:
        raise ValueError("Fitting-label completion cannot select from evaluation outcomes.")
    if int(sensitivity.get("taxonomy_groups", 0)) != 5:
        raise ValueError("Fitting-label completion must retain the canonical five-group taxonomy.")
    if sensitivity.get("evaluation_strata") != [-1, 2]:
        raise ValueError("Fitting-label completion must report overall and phase-stratum cells.")
    return payload


def _verified_descriptor(
    descriptor: Mapping[str, Any],
    *,
    repo_root: Path,
) -> Path:
    path = resolve_repo_input(str(descriptor["path"]), repo_root=repo_root)
    actual = relative_artifact_descriptor(path, repo_root=repo_root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor.get(field):
            raise RuntimeError(f"Fitting-label parent artifact mismatch for {field}.")
    return path


def _run_dirs(config: Mapping[str, Any], root: Path) -> tuple[Path, Path]:
    data_dir = resolve_isolated_run_dir(
        repo_root=root,
        configured_root=str(config["output"]["data_root"]),
        allowed_relative_root=ALLOWED_DATA_ROOT,
        run_tag=str(config["run_tag"]),
    )
    model_dir = resolve_isolated_run_dir(
        repo_root=root,
        configured_root=str(config["output"]["model_root"]),
        allowed_relative_root=ALLOWED_MODEL_ROOT,
        run_tag=str(config["run_tag"]),
    )
    return data_dir, model_dir


def _recipe_difference(
    current: Mapping[str, Mapping[int, Any]],
    reference: Mapping[str, Mapping[int, Any]],
) -> float:
    differences: list[float] = []
    if set(current) != set(reference):
        raise RuntimeError("Observed-only residual windows differ from the parent freeze.")
    for window_id in sorted(current):
        if set(current[window_id]) != {5} or 5 not in reference[window_id]:
            raise RuntimeError(f"Canonical recipe is unavailable for {window_id}.")
        left = current[window_id][5]
        right = reference[window_id][5]
        for field in ("bin_edges", "residual_quantiles"):
            differences.extend(
                np.abs(
                    np.asarray(getattr(left, field), dtype=float)
                    - np.asarray(getattr(right, field), dtype=float)
                ).tolist()
            )
        for field in ("group_counts", "finite_sample_ranks", "raw_finite_sample_ranks"):
            if tuple(getattr(left, field)) != tuple(getattr(right, field)):
                raise RuntimeError(f"Observed-only recipe changed {field} for {window_id}.")
    return max(differences, default=0.0)


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
    parent_config_path = resolve_repo_input(config["parent"]["config"], repo_root=root)
    parent = load_v4_config(parent_config_path)
    parent_freeze_path = _verified_descriptor(
        config["parent"]["outcome_freeze"],
        repo_root=root,
    )
    parent_freeze = json.loads(parent_freeze_path.read_text(encoding="utf-8"))
    parent_artifacts = verified_freeze_artifact_paths(parent_freeze, repo_root=root)
    parent_scores = pd.read_parquet(parent_artifacts["scores"])
    parent_recipes = load_recipes(parent_artifacts["recipes"])["catboost_platt"]

    raw_path = resolve_repo_input(parent["source"]["raw_path"], repo_root=root)
    data = prepare_data(parent, raw_path=raw_path)
    sensitivity_config = copy.deepcopy(parent)
    sensitivity_config["conformal"]["diagnostic_group_counts"] = [5]
    sensitivity_config["execution"]["threads"] = int(config["execution"]["threads"])

    score_frame = pd.DataFrame(
        {
            "id": data.universe["id"].astype("string"),
            "issue_d": data.universe["issue_d"],
            "design_split": data.universe["design_split"].astype("string"),
        }
    )
    scenario_audits: list[pd.DataFrame] = []
    fit_audits: list[pd.DataFrame] = []
    windows_by_learner: dict[str, Any] = {}
    model_metrics: dict[str, Any] = {}
    baseline_score_difference: float | None = None
    baseline_recipe_difference: float | None = None
    for scenario in FIT_LABEL_SCENARIOS:
        scenario_universe, scenario_audit = apply_fit_label_scenario(
            data.universe,
            scenario=scenario,
        )
        scenario_audits.append(scenario_audit)
        scenario_data = replace(data, universe=scenario_universe)
        fitted = fit_primary_scores(scenario_data, sensitivity_config)
        learner_name = f"{LEARNER_PREFIX}{scenario}"
        fitted = replace(fitted, name=learner_name)
        windows = fit_window_recipes(scenario_data, fitted, sensitivity_config)
        windows_by_learner[learner_name] = windows
        score_frame[f"pd_{learner_name}"] = fitted.probabilities
        fit_audits.extend(window.fit_audit for window in windows.values())
        model_metrics[scenario] = fitted.metrics

        if scenario == "observed_only":
            if not parent_scores["id"].astype("string").equals(score_frame["id"]):
                raise RuntimeError("Observed-only scores do not align to the parent ID census.")
            baseline_score_difference = float(
                np.max(
                    np.abs(
                        fitted.probabilities
                        - parent_scores["pd_catboost_platt"].to_numpy(dtype=float)
                    )
                )
            )
            current_recipes = {window_id: window.recipes for window_id, window in windows.items()}
            baseline_recipe_difference = _recipe_difference(current_recipes, parent_recipes)

    tolerance = float(config["fit_label_completion"]["baseline_replay_tolerance"])
    if baseline_score_difference is None or baseline_score_difference > tolerance:
        raise RuntimeError(
            f"Observed-only score replay drifted by {baseline_score_difference}; "
            f"tolerance={tolerance}."
        )
    if baseline_recipe_difference is None or baseline_recipe_difference > tolerance:
        raise RuntimeError(
            f"Observed-only recipe replay drifted by {baseline_recipe_difference}; "
            f"tolerance={tolerance}."
        )

    artifact_paths = {
        "scores": atomic_write_parquet(score_frame, paths.data_dir / "outcome_free/scores.parquet"),
        "fit_audit": atomic_write_parquet(
            pd.concat(fit_audits, ignore_index=True),
            paths.data_dir / "outcome_free/fit_audit.parquet",
        ),
        "scenario_audit": atomic_write_parquet(
            pd.concat(scenario_audits, ignore_index=True),
            paths.data_dir / "outcome_free/scenario_audit.parquet",
        ),
        "recipes": atomic_write_json(
            paths.model_dir / "outcome_free/residual_recipes.json",
            recipe_payload(windows_by_learner),
        ),
    }
    freeze_payload = {
        "schema_version": str(config["schema_version"]),
        "status": "fit_labels_completed_before_evaluation_outcome_join",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "historical_archive_previously_inspected": True,
        "outcome_based_selection": False,
        "evaluation_outcome_columns_passed_to_fitting": [],
        "scenarios": list(FIT_LABEL_SCENARIOS),
        "baseline_replay": {
            "score_max_abs_difference": baseline_score_difference,
            "recipe_max_abs_difference": baseline_recipe_difference,
            "tolerance": tolerance,
        },
        "model_metrics": model_metrics,
        "parent": {
            "config": relative_artifact_descriptor(parent_config_path, repo_root=root),
            "outcome_freeze": relative_artifact_descriptor(parent_freeze_path, repo_root=root),
        },
        "artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in artifact_paths.items()
        },
        "implementation": implementation_provenance(
            config_path=resolved_config,
            repo_root=root,
            relative_paths=[
                Path("src/ijds_audit/fit_label_sensitivity.py"),
                Path("src/ijds_audit/prediction.py"),
                Path("scripts/experiments/run_ijds_fit_label_completion_sensitivity.py"),
                Path("docs/research/ijds_fit_label_completion_sensitivity_protocol_2026-07-16.md"),
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
        raise FileNotFoundError("Run the fitting-label freeze phase first.")
    summary_path = model_dir / "fit_label_completion_summary.json"
    evaluation_dir = data_dir / "evaluation"
    if summary_path.exists() or evaluation_dir.exists():
        raise FileExistsError("Fitting-label evaluation outputs are immutable.")
    freeze_payload = json.loads(freeze_path.read_text(encoding="utf-8"))
    for field, expected in {
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "status": "fit_labels_completed_before_evaluation_outcome_join",
    }.items():
        if freeze_payload.get(field) != expected:
            raise RuntimeError(f"Fitting-label freeze mismatch for {field}.")
    if freeze_payload.get("evaluation_outcome_columns_passed_to_fitting") != []:
        raise RuntimeError("Fitting-label freeze reports evaluation-outcome leakage.")
    artifacts = {
        name: _verified_descriptor(descriptor, repo_root=root)
        for name, descriptor in freeze_payload["artifacts"].items()
    }

    parent_config_path = resolve_repo_input(config["parent"]["config"], repo_root=root)
    parent = load_v4_config(parent_config_path)
    raw_path = resolve_repo_input(parent["source"]["raw_path"], repo_root=root)
    universe = load_outcome_universe(parent, raw_path=raw_path)
    outcomes = configured_archive_outcomes(universe, parent)
    scores = pd.read_parquet(artifacts["scores"])
    recipes = load_recipes(artifacts["recipes"])
    fit_audit = pd.read_parquet(artifacts["fit_audit"])
    coverage = temporal_coverage_audit(
        scores,
        outcomes,
        recipes,
        fit_audit,
        roles=("primary_oot",),
        taxonomy_group_counts=(5,),
        strata=tuple(config["fit_label_completion"]["evaluation_strata"]),
    )
    coverage["fit_label_scenario"] = coverage["learner"].str.removeprefix(LEARNER_PREFIX)
    window_ids = tuple(str(item["id"]) for item in parent["residual_specification"]["windows"])
    nominal = 1.0 - float(parent["conformal"]["alpha"])
    summary_table = summarize_fit_label_coverage(
        coverage,
        window_ids=window_ids,
        nominal_coverage=nominal,
    )
    phase = coverage.loc[coverage["conformal_group"].eq(2)].copy()
    evaluation_paths = {
        "coverage": atomic_write_parquet(coverage, evaluation_dir / "temporal_coverage.parquet"),
        "summary_table": atomic_write_parquet(
            summary_table,
            evaluation_dir / "scenario_summary.parquet",
        ),
        "phase_stratum": atomic_write_parquet(
            phase,
            evaluation_dir / "phase_stratum.parquet",
        ),
    }
    all_below = bool(summary_table["all_windows_upper_below_nominal"].all())
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_fit_label_completion_corner_sensitivity",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "historical_archive_previously_inspected": True,
        "outcome_based_selection": False,
        "scenarios": list(FIT_LABEL_SCENARIOS),
        "scope": (
            "Four declared joint completion scenarios for 215 fitting labels unavailable "
            "at the information cutoff; nonlinear learner refits mean these are stress "
            "corners, not sharp bounds over every label assignment."
        ),
        "results": {
            "coverage_rows": int(len(coverage)),
            "overall_cells": int(coverage["conformal_group"].eq(-1).sum()),
            "phase_cells": int(coverage["conformal_group"].eq(2).sum()),
            "all_scenarios_all_windows_upper_below_nominal": all_below,
            "scenario_rows": summary_table.to_dict(orient="records"),
        },
        "freeze": relative_artifact_descriptor(freeze_path, repo_root=root),
        "artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in evaluation_paths.items()
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
