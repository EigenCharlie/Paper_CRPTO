"""Two-phase orchestration for the active V4 retrospective audit."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.data.outcome_observability import (
    build_outcome_label_availability,
    load_design_universe,
    terminal_outcome_from_status,
)
from src.ijds_audit.allocations import build_outcome_free_portfolios, policy_family
from src.ijds_audit.config import load_v4_config
from src.ijds_audit.evaluation import (
    aggregate_portfolios,
    build_archive_outcomes,
    comparator_envelopes,
    evaluate_frozen_portfolios,
    paired_portfolio_contrasts,
    temporal_coverage_audit,
)
from src.ijds_audit.geometry import summarize_binary_geometry
from src.ijds_audit.prediction import (
    LABEL_FIT_SPLITS,
    LearnerScores,
    WindowRecipe,
    decision_panel_for_window,
    fit_logistic_control,
    fit_primary_scores,
    fit_window_recipes,
    prepare_data,
)
from src.ijds_audit.simulation import run_factorial_simulation
from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    apply_binary_outcome_recipe,
)
from src.utils.isolated_experiment import (
    environment_provenance,
    implementation_provenance,
    prepare_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_isolated_run_dir,
    resolve_repo_input,
    save_catboost_model_atomic,
)
from src.utils.pipeline_runtime import (
    atomic_write_json,
    atomic_write_parquet,
    atomic_write_pickle,
)

ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")


def _recipe_payload(
    learners: Mapping[str, Mapping[str, WindowRecipe]],
) -> dict[str, dict[str, dict[str, Any]]]:
    return {
        learner: {
            window_id: {str(groups): asdict(recipe) for groups, recipe in window.recipes.items()}
            for window_id, window in windows.items()
        }
        for learner, windows in learners.items()
    }


def _recipe_from_payload(payload: Mapping[str, Any]) -> BinaryOutcomeConformalRecipe:
    values = dict(payload)
    for field in (
        "bin_edges",
        "residual_quantiles",
        "group_counts",
        "finite_sample_ranks",
        "raw_finite_sample_ranks",
    ):
        values[field] = tuple(values[field])
    return BinaryOutcomeConformalRecipe(**values)


def _load_recipes(
    path: Path,
) -> dict[str, dict[str, dict[int, BinaryOutcomeConformalRecipe]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("V4 recipe artifact must be a JSON mapping.")
    return {
        str(learner): {
            str(window_id): {
                int(groups): _recipe_from_payload(recipe)
                for groups, recipe in group_recipes.items()
            }
            for window_id, group_recipes in windows.items()
        }
        for learner, windows in payload.items()
    }


def _score_frame(data: Any, learners: tuple[LearnerScores, ...]) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "id": data.universe["id"].astype("string"),
            "issue_d": data.universe["issue_d"],
            "design_split": data.universe["design_split"].astype("string"),
        }
    )
    for learner in learners:
        frame[f"pd_{learner.name}"] = learner.probabilities
    return frame


def _outcome_free_geometry(
    scores: pd.DataFrame,
    recipes: Mapping[str, Mapping[str, WindowRecipe]],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for learner, windows in recipes.items():
        probability = scores[f"pd_{learner}"].to_numpy(dtype=float)
        for window_id, window in windows.items():
            for groups, recipe in sorted(window.recipes.items()):
                assigned, lower, upper = apply_binary_outcome_recipe(probability, recipe)
                for role in (
                    "conformal_fit",
                    "policy_development",
                    "primary_oot",
                    "censored_extension",
                ):
                    role_mask = scores["design_split"].eq(role).to_numpy(dtype=bool)
                    for stratum in (-1, *range(groups)):
                        mask = role_mask & ((assigned == stratum) if stratum >= 0 else True)
                        if not bool(mask.any()):
                            raise RuntimeError(
                                f"Empty geometry cell: {learner}/{window_id}/{groups}/{role}/{stratum}."
                            )
                        rows.append(
                            {
                                "learner": learner,
                                "window_id": window_id,
                                "taxonomy_groups": groups,
                                "role": role,
                                "conformal_group": stratum,
                                "score_min": float(np.min(probability[mask])),
                                "score_max": float(np.max(probability[mask])),
                                **summarize_binary_geometry(lower[mask], upper[mask]),
                            }
                        )
    return pd.DataFrame(rows)


def _artifact_paths(freeze: Mapping[str, Any], *, repo_root: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, descriptor in freeze["outcome_free_artifacts"].items():
        path = (repo_root / str(descriptor["path"])).resolve()
        path.relative_to(repo_root)
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = relative_artifact_descriptor(path, repo_root=repo_root)
        for field in ("path", "bytes", "sha256"):
            if actual[field] != descriptor[field]:
                raise RuntimeError(f"Frozen artifact mismatch for {name}: {field}.")
        paths[str(name)] = path
    return paths


def _implementation(config_path: Path, repo_root: Path) -> dict[str, Any]:
    return implementation_provenance(
        config_path=config_path,
        repo_root=repo_root,
        relative_paths=[
            Path("scripts/experiments/run_ijds_binary_geometry_frontier_v4.py"),
            Path("src/ijds_audit/config.py"),
            Path("src/ijds_audit/geometry.py"),
            Path("src/ijds_audit/prediction.py"),
            Path("src/ijds_audit/portfolio.py"),
            Path("src/ijds_audit/allocations.py"),
            Path("src/ijds_audit/evaluation.py"),
            Path("src/ijds_audit/simulation.py"),
            Path("src/ijds_audit/protocol.py"),
            Path("src/data/outcome_observability.py"),
            Path("src/models/binary_conformal_guardrail.py"),
            Path("src/models/maturity_safe_pd.py"),
            Path("src/evaluation/maturity_safe_portfolio.py"),
            Path("src/evaluation/policy_contrast_bounds.py"),
            Path("src/evaluation/standardized_credit_payoff.py"),
            Path("src/optimization/portfolio_model.py"),
            *[
                Path(value)
                for value in load_v4_config(config_path).get("protocol_lineage_files", [])
            ],
        ],
    )


def freeze_outcome_free(
    *,
    config_path: Path,
    repo_root: Path,
) -> Path:
    """Fit, solve, persist, and hash all objects before the archive outcome join."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_v4_config(resolved_config)
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))
    paths = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    raw_path = resolve_repo_input(config["source"]["raw_path"], repo_root=root)
    data = prepare_data(config, raw_path=raw_path)
    primary = fit_primary_scores(data, config)
    logistic = fit_logistic_control(data, config)
    learner_scores = (primary, logistic)
    windows = {
        primary.name: fit_window_recipes(data, primary, config),
        logistic.name: fit_window_recipes(data, logistic, config),
    }
    primary_panels = {
        window_id: decision_panel_for_window(data, primary, recipe)
        for window_id, recipe in windows[primary.name].items()
    }
    portfolio = build_outcome_free_portfolios(primary_panels, config)
    scores = _score_frame(data, learner_scores)
    geometry = _outcome_free_geometry(scores, windows)
    fit_audits = pd.concat(
        [window.fit_audit for learner in windows.values() for window in learner.values()],
        ignore_index=True,
    )

    artifact_files = {
        "scores": atomic_write_parquet(scores, paths.data_dir / "prediction/scores.parquet"),
        "recipes": atomic_write_json(
            paths.model_dir / "prediction/residual_recipes.json", _recipe_payload(windows)
        ),
        "fit_audit": atomic_write_parquet(
            fit_audits, paths.data_dir / "prediction/residual_fit_audit.parquet"
        ),
        "outcome_free_geometry": atomic_write_parquet(
            geometry, paths.data_dir / "prediction/outcome_free_geometry.parquet"
        ),
        "availability_audit": atomic_write_parquet(
            data.availability_audit, paths.data_dir / "data/label_availability_audit.parquet"
        ),
        "monthly_residual_availability": atomic_write_parquet(
            data.monthly_residual_availability,
            paths.data_dir / "data/monthly_residual_availability.parquet",
        ),
        "solve_records": atomic_write_parquet(
            portfolio.records, paths.data_dir / "portfolio/outcome_free_solve_records.parquet"
        ),
        "allocations": atomic_write_parquet(
            portfolio.allocations,
            paths.data_dir / "portfolio/outcome_free_funded_allocations.parquet",
        ),
        "comparator_support": atomic_write_parquet(
            portfolio.comparator_support,
            paths.data_dir / "portfolio/development_comparator_support.parquet",
        ),
        "frontier_breakpoints": atomic_write_parquet(
            portfolio.frontier_breakpoints,
            paths.data_dir / "portfolio/exact_frontier_breakpoints.parquet",
        ),
    }
    primary_model = save_catboost_model_atomic(
        primary.model, paths.model_dir / "prediction/catboost_seed42.cbm"
    )
    primary_calibrator = atomic_write_pickle(
        paths.model_dir / "prediction/catboost_platt.pkl", primary.calibrator
    )
    logistic_model = atomic_write_pickle(
        paths.model_dir / "prediction/numeric_logistic.pkl", logistic.model
    )
    logistic_calibrator = atomic_write_pickle(
        paths.model_dir / "prediction/numeric_logistic_platt.pkl", logistic.calibrator
    )
    model_artifacts = {
        "catboost": relative_artifact_descriptor(primary_model, repo_root=root),
        "catboost_platt": relative_artifact_descriptor(primary_calibrator, repo_root=root),
        "numeric_logistic": relative_artifact_descriptor(logistic_model, repo_root=root),
        "numeric_logistic_platt": relative_artifact_descriptor(logistic_calibrator, repo_root=root),
    }
    freeze = {
        "schema_version": str(config["schema_version"]),
        "status": "outcome_free_allocations_frozen_before_archive_outcome_join",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "source_inventory": data.source_inventory,
        "learner_metrics": {learner.name: learner.metrics for learner in learner_scores},
        "outcome_columns_passed_to_policy_or_comparator": [],
        "policy_selection": "none_all_nine_co_primary",
        "window_selection": "none_all_eight_co_primary",
        "implementation_provenance": _implementation(resolved_config, root),
        "environment": environment_provenance(root),
        "outcome_free_artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in artifact_files.items()
        },
        "model_artifacts": model_artifacts,
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    return atomic_write_json(paths.model_dir / "protocol_freeze.json", freeze)


def _load_outcome_universe(config: Mapping[str, Any], *, raw_path: Path) -> pd.DataFrame:
    universe, _ = load_design_universe(
        config,
        raw_path=raw_path,
        label_required_splits=LABEL_FIT_SPLITS,
    )
    labels = build_outcome_label_availability(
        universe["loan_status"],
        universe["last_pymnt_d"],
        cutoff=str(config["source"]["information_cutoff"]),
        charged_off_lag_months=int(config["source"]["charged_off_reporting_lag_months"]),
    )
    universe["terminal_default"] = terminal_outcome_from_status(universe["loan_status"])
    universe["label_available"] = labels["label_available"].astype(bool)
    universe["label_available_at"] = labels["label_available_at"]
    return universe


def _frontier_for_window(
    shared: pd.DataFrame,
    scores: pd.DataFrame,
    recipe: BinaryOutcomeConformalRecipe,
    *,
    window_id: str,
) -> pd.DataFrame:
    primary = scores.loc[scores["design_split"].eq("primary_oot")]
    probability = primary["pd_catboost_platt"].to_numpy(dtype=float)
    assigned, lower, upper = apply_binary_outcome_recipe(probability, recipe)
    endpoints = pd.DataFrame(
        {
            "id": primary["id"].astype("string"),
            "conformal_lower": lower,
            "conformal_upper": upper,
            "conformal_group": assigned,
        }
    )
    expanded = shared.merge(endpoints, on="id", how="left", validate="many_to_one")
    if bool(expanded["conformal_lower"].isna().any()):
        raise RuntimeError(f"Shared frontier could not be aligned to window {window_id}.")
    expanded["window_id"] = str(window_id)
    expanded["learner"] = "catboost_platt"
    expanded["taxonomy_groups"] = 5
    return expanded


def evaluate_frozen(
    *,
    config_path: Path,
    repo_root: Path,
) -> Path:
    """Verify the freeze, join archive outcomes once, and build V4 evidence."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_v4_config(resolved_config)
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))
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
    freeze_path = model_dir / "protocol_freeze.json"
    if not freeze_path.is_file():
        raise FileNotFoundError("Run the outcome-free freeze phase first.")
    summary_path = model_dir / str(config["output"]["deterministic_summary"])
    if summary_path.exists() or (data_dir / "evaluation").exists():
        raise FileExistsError("V4 evaluation already exists; experiment outputs are immutable.")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    expected = {
        "status": "outcome_free_allocations_frozen_before_archive_outcome_join",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
    }
    for field, value in expected.items():
        if freeze.get(field) != value:
            raise RuntimeError(f"Protocol freeze mismatch for {field}.")
    if freeze.get("outcome_columns_passed_to_policy_or_comparator") != []:
        raise RuntimeError("Protocol freeze reports outcome leakage.")
    artifacts = _artifact_paths(freeze, repo_root=root)
    raw_path = resolve_repo_input(config["source"]["raw_path"], repo_root=root)
    universe = _load_outcome_universe(config, raw_path=raw_path)
    outcomes = build_archive_outcomes(universe)
    scores = pd.read_parquet(artifacts["scores"])
    recipes = _load_recipes(artifacts["recipes"])
    fit_audit = pd.read_parquet(artifacts["fit_audit"])
    records = pd.read_parquet(artifacts["solve_records"])
    allocations = pd.read_parquet(artifacts["allocations"])
    support = pd.read_parquet(artifacts["comparator_support"])

    coverage = temporal_coverage_audit(scores, outcomes, recipes, fit_audit)
    frontier_mask = records["comparator_rule"].eq("point_cap_frontier")
    shared_records = records.loc[frontier_mask]
    named_records = records.loc[~frontier_mask]
    shared_allocations = allocations.loc[allocations["comparator_rule"].eq("point_cap_frontier")]
    named_allocations = allocations.loc[~allocations["comparator_rule"].eq("point_cap_frontier")]
    if not bool(shared_records["window_id"].eq("__shared_point_frontier__").all()):
        raise RuntimeError("Point frontier is not stored under its shared freeze identity.")
    evaluated, joined = evaluate_frozen_portfolios(
        named_records, named_allocations, outcomes, config=config
    )
    aggregates = aggregate_portfolios(evaluated)
    policy_ids = tuple(candidate.candidate_id for candidate in policy_family(config))
    shared_joined = shared_allocations.merge(
        outcomes[["id", "snapshot_default", "snapshot_resolution"]],
        on="id",
        how="left",
        validate="many_to_one",
    )
    if bool(shared_joined["snapshot_resolution"].isna().any()):
        raise RuntimeError("Shared frontier outcome join is incomplete.")
    contrast_frames: list[pd.DataFrame] = []
    primary_recipes = recipes["catboost_platt"]
    for window_id, group_recipes in primary_recipes.items():
        expanded_frontier = _frontier_for_window(
            shared_joined,
            scores,
            group_recipes[5],
            window_id=window_id,
        )
        window_allocations = pd.concat(
            [joined.loc[joined["window_id"].eq(window_id)], expanded_frontier],
            ignore_index=True,
        )
        contrast_frames.append(
            paired_portfolio_contrasts(
                window_allocations,
                policy_ids=policy_ids,
                lgd=float(config["payoff"]["lgd"]),
            )
        )
    contrasts = pd.concat(contrast_frames, ignore_index=True)
    frontier = config["comparators"]["exact_point_cap_frontier"]
    envelopes = comparator_envelopes(
        contrasts,
        support,
        broad_lower=float(frontier["start"]),
        broad_upper=float(frontier["stop"]),
    )
    simulation, simulation_summary = run_factorial_simulation(config)

    evaluation_files = {
        "temporal_coverage": atomic_write_parquet(
            coverage, data_dir / "evaluation/temporal_coverage.parquet"
        ),
        "monthly_evaluation": atomic_write_parquet(
            evaluated, data_dir / "evaluation/monthly_evaluation.parquet"
        ),
        "funded_allocations_with_outcomes": atomic_write_parquet(
            joined, data_dir / "evaluation/funded_allocations_with_outcomes.parquet"
        ),
        "shared_frontier_allocations_with_outcomes": atomic_write_parquet(
            shared_joined,
            data_dir / "evaluation/shared_frontier_allocations_with_outcomes.parquet",
        ),
        "aggregate_evaluation": atomic_write_parquet(
            aggregates, data_dir / "evaluation/aggregate_evaluation.parquet"
        ),
        "paired_contrasts": atomic_write_parquet(
            contrasts, data_dir / "evaluation/paired_sharp_contrasts.parquet"
        ),
        "comparator_envelopes": atomic_write_parquet(
            envelopes, data_dir / "evaluation/comparator_envelopes.parquet"
        ),
        "simulation_repetitions": atomic_write_parquet(
            simulation, data_dir / "simulation/factorial_repetitions.parquet"
        ),
        "simulation_summary": atomic_write_parquet(
            simulation_summary, data_dir / "simulation/factorial_summary.parquet"
        ),
    }
    canonical_coverage = coverage.loc[
        coverage["learner"].eq("catboost_platt")
        & coverage["taxonomy_groups"].eq(5)
        & coverage["role"].eq("primary_oot")
        & coverage["conformal_group"].eq(-1)
    ]
    envelope_counts: list[dict[str, Any]] = []
    for raw_keys, frame in envelopes.groupby(
        ["scope", "metric", "direction"], observed=True, sort=True
    ):
        key_values = raw_keys if isinstance(raw_keys, tuple) else (raw_keys,)
        if len(key_values) != 3:
            raise RuntimeError("Envelope summary key has unexpected cardinality.")
        scope, metric, direction = key_values
        envelope_counts.append(
            {
                "scope": str(scope),
                "metric": str(metric),
                "direction": str(direction),
                "cells": int(len(frame)),
            }
        )
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_retrospective_binary_geometry_frontier_audit",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "claim_boundary": {
            "previously_inspected_archive": True,
            "confirmatory": False,
            "prospective": False,
            "causal": False,
            "selected_set_validity": False,
            "policy_winner": False,
            "nested_scopes_are_independent_replications": False,
        },
        "canonical_primary_oot_coverage": canonical_coverage.to_dict(orient="records"),
        "comparator_envelope_direction_counts": envelope_counts,
        "c2_objective_dominance_minimum": float(
            records.loc[
                records["comparator_rule"].eq("c2_contemporaneous"),
                "point_minus_guardrail_objective",
            ].min()
        ),
        "simulation_scope": "synthetic_mechanism_interpretation_only",
        "outcome_free_freeze": relative_artifact_descriptor(freeze_path, repo_root=root),
        "artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in evaluation_files.items()
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    written_summary = atomic_write_json(summary_path, summary)
    atomic_write_json(
        model_dir / str(config["output"]["execution_receipt"]),
        {
            "summary": relative_artifact_descriptor(written_summary, repo_root=root),
            "protocol_commit": protocol_commit,
            "environment": environment_provenance(root),
        },
    )
    return written_summary
