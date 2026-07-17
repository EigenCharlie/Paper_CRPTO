"""Evaluate frozen IJDS evidence under every declared endpoint-availability lag."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from loguru import logger

from src.ijds_audit.allocations import policy_family
from src.ijds_audit.config import load_v4_config
from src.ijds_audit.endpoint_sensitivity import (
    direction_census,
    endpoint_census,
    exact_support_census,
    rebuild_archive_outcomes,
    summarize_coverage_sensitivity,
)
from src.ijds_audit.evaluation import (
    comparator_envelopes,
    evaluate_frozen_portfolios,
    indexed_portfolio_contrasts,
    temporal_coverage_audit,
)
from src.ijds_audit.protocol import (
    load_outcome_universe,
    load_recipes,
    verified_freeze_artifact_paths,
)
from src.ijds_challengers.evaluation import (
    build_endpoint_contrasts,
    build_metric_directions,
    validate_complete_evaluation,
    validate_outcome_alignment,
    verify_frontier_freeze,
)
from src.ijds_challengers.evaluation_config import load_v2_config
from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    apply_binary_outcome_recipe,
)
from src.utils.isolated_experiment import (
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    prepare_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_repo_input,
    sha256_file,
)
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_parquet, utc_now_iso

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs/experiments/ijds_endpoint_availability_sensitivity_2026-07-14.yaml"
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
_INDEX_ALLOCATION_COLUMNS = [
    "id",
    "role",
    "policy_label",
    "exposure",
    "expected_payoff_contribution",
    "comparator_rule",
    "frontier_cap",
]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the endpoint-sensitivity CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args(argv)


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Endpoint-sensitivity config must be a mapping.")
    if payload.get("protocol_status") != "locked_retrospective_endpoint_assumption_sensitivity":
        raise ValueError("Endpoint-sensitivity protocol is not locked.")
    endpoint = payload.get("endpoint", {})
    if [int(value) for value in endpoint.get("charged_off_lag_months", [])] != [0, 3, 6, 8, 12]:
        raise ValueError("Endpoint lag grid must remain 0/3/6/8/12 months.")
    if int(endpoint.get("fully_paid_lag_months", -1)) != 0:
        raise ValueError("Fully Paid must retain the declared zero administrative lag.")
    boundary = payload.get("claim_boundary", {})
    required_false = {
        "preregistered",
        "confirmatory",
        "prospective",
        "outcome_based_selection",
        "allocation_refit",
        "policy_selection",
        "model_selection",
        "endpoint_selection",
    }
    if any(boundary.get(field) is not False for field in required_false):
        raise ValueError("Endpoint-sensitivity claim boundary changed.")
    return payload


def _verified_freeze(
    descriptor: Mapping[str, Any],
    *,
    repo_root: Path,
    expected_status: str,
) -> tuple[dict[str, Any], dict[str, Path]]:
    path = resolve_repo_input(str(descriptor["path"]), repo_root=repo_root)
    if relative_artifact_descriptor(path, repo_root=repo_root) != dict(descriptor):
        raise RuntimeError(f"Freeze descriptor changed: {descriptor['path']}.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != expected_status:
        raise RuntimeError(f"Unexpected freeze status for {descriptor['path']}.")
    artifacts = verified_freeze_artifact_paths(payload, repo_root=repo_root)
    return payload, artifacts


def _primary_loan_facts(
    allocations: pd.DataFrame,
    outcomes: pd.DataFrame,
) -> pd.DataFrame:
    required_allocations = {"id", "role", "period", "contractual_rate"}
    missing_allocations = sorted(required_allocations - set(allocations.columns))
    if missing_allocations:
        raise KeyError(f"Allocations are missing primary fact columns: {missing_allocations}.")
    required_outcomes = {
        "id",
        "role",
        "period",
        "snapshot_default",
        "snapshot_resolution",
    }
    missing_outcomes = sorted(required_outcomes - set(outcomes.columns))
    if missing_outcomes:
        raise KeyError(f"Outcomes are missing primary fact columns: {missing_outcomes}.")
    if bool(outcomes["id"].isna().any()) or bool(outcomes["id"].duplicated().any()):
        raise RuntimeError("Endpoint outcomes must contain one nonmissing row per ID.")

    primary = allocations.loc[
        allocations["role"].eq("primary_oot"),
        ["id", "role", "period", "contractual_rate"],
    ].copy()
    if primary.empty or bool(primary["id"].isna().any()):
        raise RuntimeError("Primary allocation facts are empty or contain missing IDs.")
    conflicts = primary.groupby("id", observed=True, dropna=False)[
        ["role", "period", "contractual_rate"]
    ].nunique(dropna=False)
    if bool(conflicts.gt(1).any(axis=None)):
        raise RuntimeError("Primary allocations contain conflicting per-loan facts.")
    primary = primary.drop_duplicates()
    if bool(primary["id"].duplicated().any()):
        raise RuntimeError("Primary allocation facts do not reduce to one row per ID.")

    endpoint = outcomes.loc[
        outcomes["id"].isin(primary["id"]),
        ["id", "role", "period", "snapshot_default", "snapshot_resolution"],
    ].rename(columns={"role": "outcome_role", "period": "outcome_period"})
    joined = primary.merge(
        endpoint,
        on="id",
        how="left",
        validate="one_to_one",
        indicator="outcome_join",
        sort=False,
    )
    missing = int(joined["outcome_join"].eq("left_only").sum())
    if missing:
        raise RuntimeError(f"Exact-frontier funded outcome ID mismatch: missing={missing}.")
    role_mismatch = joined["role"].astype("string").ne(joined["outcome_role"].astype("string"))
    period_mismatch = (
        joined["period"].astype("string").ne(joined["outcome_period"].astype("string"))
    )
    if bool(role_mismatch.fillna(True).any()) or bool(period_mismatch.fillna(True).any()):
        raise RuntimeError("Exact-frontier outcome role or period disagrees with allocations.")
    if bool(joined["snapshot_resolution"].isna().any()):
        raise RuntimeError("Exact-frontier outcome resolution is incomplete.")
    return joined[["id", "contractual_rate", "snapshot_default"]]


def _window_loan_facts(
    base_facts: pd.DataFrame,
    scores: pd.DataFrame,
    recipe: BinaryOutcomeConformalRecipe,
) -> pd.DataFrame:
    required_scores = {"id", "design_split", "pd_catboost_platt"}
    missing = sorted(required_scores - set(scores.columns))
    if missing:
        raise KeyError(f"Scores are missing endpoint columns: {missing}.")
    primary = scores.loc[
        scores["design_split"].eq("primary_oot"), ["id", "pd_catboost_platt"]
    ].copy()
    if bool(primary["id"].isna().any()) or bool(primary["id"].duplicated().any()):
        raise RuntimeError("Primary score census must contain one nonmissing row per ID.")
    probability = primary["pd_catboost_platt"].to_numpy(dtype=float)
    _, lower, upper = apply_binary_outcome_recipe(probability, recipe)
    endpoints = pd.DataFrame(
        {
            "id": primary["id"].astype("string"),
            "conformal_lower": lower,
            "conformal_upper": upper,
        }
    )
    facts = base_facts.merge(
        endpoints,
        on="id",
        how="left",
        validate="one_to_one",
        indicator="score_join",
        sort=False,
    )
    missing_scores = int(facts["score_join"].eq("left_only").sum())
    if missing_scores:
        raise RuntimeError(f"Exact-frontier score ID mismatch: missing={missing_scores}.")
    return facts[
        [
            "id",
            "contractual_rate",
            "conformal_lower",
            "conformal_upper",
            "snapshot_default",
        ]
    ]


def _exact_support(
    *,
    records: pd.DataFrame,
    allocations: pd.DataFrame,
    support: pd.DataFrame,
    scores: pd.DataFrame,
    recipes: Mapping[str, Any],
    outcomes: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    frontier_mask = records["comparator_rule"].eq("point_cap_frontier")
    named_records = records.loc[~frontier_mask]
    named_allocations = allocations.loc[~allocations["comparator_rule"].eq("point_cap_frontier")]
    shared_allocations = allocations.loc[allocations["comparator_rule"].eq("point_cap_frontier")]
    _, named_joined = evaluate_frozen_portfolios(
        named_records, named_allocations, outcomes, config=config
    )
    base_facts = _primary_loan_facts(allocations, outcomes)
    shared_index_allocations = shared_allocations[_INDEX_ALLOCATION_COLUMNS]
    policy_ids = tuple(candidate.candidate_id for candidate in policy_family(config))
    frames: list[pd.DataFrame] = []
    for window_id, group_recipes in recipes["catboost_platt"].items():
        loan_facts = _window_loan_facts(base_facts, scores, group_recipes[5])
        named_window = named_joined.loc[
            named_joined["window_id"].eq(window_id), _INDEX_ALLOCATION_COLUMNS
        ]
        window_allocations = pd.concat(
            [named_window, shared_index_allocations],
            ignore_index=True,
            copy=False,
        )
        frames.append(
            indexed_portfolio_contrasts(
                window_allocations,
                loan_facts=loan_facts,
                window_id=str(window_id),
                policy_ids=policy_ids,
                lgd=float(config["payoff"]["lgd"]),
            )
        )
    contrasts = pd.concat(frames, ignore_index=True)
    frontier = config["comparators"]["exact_point_cap_frontier"]
    return comparator_envelopes(
        contrasts,
        support,
        broad_lower=float(frontier["start"]),
        broad_upper=float(frontier["stop"]),
    )


def run(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Run the complete frozen endpoint sensitivity and write immutable artifacts."""
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
        raise RuntimeError("Raw archive hash changed before endpoint sensitivity.")
    v4_config = load_v4_config(resolve_repo_input(str(parent["v4_config"]), repo_root=root))
    two_ruler_config = load_v2_config(
        resolve_repo_input(str(parent["two_ruler_config"]), repo_root=root)
    )
    _, v4_paths = _verified_freeze(
        parent["v4_freeze"],
        repo_root=root,
        expected_status="outcome_free_allocations_frozen_before_archive_outcome_join",
    )
    _, credit_paths = _verified_freeze(
        parent["credit_freeze"],
        repo_root=root,
        expected_status="credit_control_scores_frozen_before_primary_oot_outcome_join",
    )
    two_ruler = verify_frontier_freeze(two_ruler_config, repo_root=root)
    universe = load_outcome_universe(v4_config, raw_path=raw_path)
    v4_scores = pd.read_parquet(v4_paths["scores"])
    v4_recipes = load_recipes(v4_paths["recipes"])
    credit_scores = pd.read_parquet(credit_paths["scores"])
    credit_recipes = load_recipes(credit_paths["recipes"])
    credit_fit = pd.read_parquet(credit_paths["fit_audit"])
    two_records = pd.read_parquet(two_ruler.artifacts["solve_records"])
    two_allocations = pd.read_parquet(two_ruler.artifacts["allocations"])
    two_endpoints = pd.read_parquet(two_ruler.artifacts["endpoint_diagnostics"])
    v4_records = pd.read_parquet(v4_paths["solve_records"])
    v4_allocations = pd.read_parquet(v4_paths["allocations"])
    v4_support = pd.read_parquet(v4_paths["comparator_support"])

    endpoint_frames: list[pd.DataFrame] = []
    coverage_frames: list[pd.DataFrame] = []
    contrast_frames: list[pd.DataFrame] = []
    direction_frames: list[pd.DataFrame] = []
    direction_census_frames: list[pd.DataFrame] = []
    envelope_frames: list[pd.DataFrame] = []
    envelope_census_frames: list[pd.DataFrame] = []
    lags = [int(value) for value in config["endpoint"]["charged_off_lag_months"]]
    for lag in lags:
        logger.info("Endpoint sensitivity lag {} months", lag)
        outcomes = rebuild_archive_outcomes(
            universe,
            evaluation_cutoff=str(config["endpoint"]["evaluation_cutoff"]),
            charged_off_lag_months=lag,
        )
        endpoint_frames.append(endpoint_census(outcomes, lag_months=lag))
        coverage = temporal_coverage_audit(
            credit_scores,
            outcomes,
            credit_recipes,
            credit_fit,
            roles=[str(value) for value in config["endpoint"]["roles"]],
            taxonomy_group_counts=[int(config["endpoint"]["canonical_taxonomy_groups"])],
            strata=[-1],
        ).assign(charged_off_lag_months=lag)
        coverage_frames.append(coverage)
        outcome_audit = validate_outcome_alignment(
            two_allocations,
            outcomes,
            config=two_ruler_config,
        )
        evaluated, joined = evaluate_frozen_portfolios(
            two_records,
            two_allocations,
            outcomes,
            config=v4_config,
        )
        window, monthly = build_endpoint_contrasts(
            joined,
            two_endpoints,
            config=two_ruler_config,
            lgd=float(v4_config["payoff"]["lgd"]),
        )
        directions = build_metric_directions(window, config=two_ruler_config)
        validate_complete_evaluation(
            evaluated,
            joined,
            window,
            monthly,
            directions,
            config=two_ruler_config,
        )
        if outcome_audit.empty:
            raise RuntimeError("Endpoint sensitivity produced no outcome audit rows.")
        contrast_frames.append(window.assign(charged_off_lag_months=lag))
        direction_frames.append(directions.assign(charged_off_lag_months=lag))
        direction_census_frames.append(direction_census(directions, lag_months=lag))
        envelopes = _exact_support(
            records=v4_records,
            allocations=v4_allocations,
            support=v4_support,
            scores=v4_scores,
            recipes=v4_recipes,
            outcomes=outcomes,
            config=v4_config,
        ).assign(charged_off_lag_months=lag)
        envelope_frames.append(envelopes)
        envelope_census_frames.append(exact_support_census(envelopes, lag_months=lag))

    endpoint_table = pd.concat(endpoint_frames, ignore_index=True)
    coverage_table = pd.concat(coverage_frames, ignore_index=True)
    coverage_summary = summarize_coverage_sensitivity(coverage_table)
    contrast_table = pd.concat(contrast_frames, ignore_index=True)
    direction_table = pd.concat(direction_frames, ignore_index=True)
    direction_counts = pd.concat(direction_census_frames, ignore_index=True)
    envelope_table = pd.concat(envelope_frames, ignore_index=True)
    envelope_counts = pd.concat(envelope_census_frames, ignore_index=True)
    artifacts = {
        "endpoint_census": atomic_write_parquet(
            endpoint_table, paths.data_dir / "evaluation/endpoint_census.parquet"
        ),
        "coverage_cells": atomic_write_parquet(
            coverage_table, paths.data_dir / "evaluation/coverage_cells.parquet"
        ),
        "coverage_summary": atomic_write_parquet(
            coverage_summary, paths.data_dir / "evaluation/coverage_summary.parquet"
        ),
        "two_ruler_window_contrasts": atomic_write_parquet(
            contrast_table, paths.data_dir / "evaluation/two_ruler_window_contrasts.parquet"
        ),
        "two_ruler_directions": atomic_write_parquet(
            direction_table, paths.data_dir / "evaluation/two_ruler_directions.parquet"
        ),
        "two_ruler_direction_census": atomic_write_parquet(
            direction_counts, paths.data_dir / "evaluation/two_ruler_direction_census.parquet"
        ),
        "exact_support_envelopes": atomic_write_parquet(
            envelope_table, paths.data_dir / "evaluation/exact_support_envelopes.parquet"
        ),
        "exact_support_census": atomic_write_parquet(
            envelope_counts, paths.data_dir / "evaluation/exact_support_census.parquet"
        ),
    }
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_retrospective_endpoint_availability_sensitivity",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "started_at_utc": started_at,
        "completed_at_utc": utc_now_iso(),
        "elapsed_seconds": float(time.perf_counter() - started),
        "claim_boundary": dict(config["claim_boundary"]),
        "lags": lags,
        "coverage_cells": int(len(coverage_table)),
        "two_ruler_direction_cells": int(len(direction_table)),
        "exact_support_envelopes": int(len(envelope_table)),
        "artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in artifacts.items()
        },
        "schemas": {
            name: dataframe_schema(pd.read_parquet(path)) for name, path in artifacts.items()
        },
        "implementation": implementation_provenance(
            config_path=resolved_config,
            repo_root=root,
            relative_paths=(
                Path("src/ijds_audit/endpoint_sensitivity.py"),
                Path("scripts/experiments/run_ijds_endpoint_availability_sensitivity.py"),
                Path("docs/research/ijds_endpoint_availability_sensitivity_protocol_2026-07-14.md"),
            ),
        ),
        "environment": environment_provenance(root),
        "git": git_provenance(root),
        "selection": {
            "lag": None,
            "learner": None,
            "window": None,
            "ruler": None,
            "coordinate": None,
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    summary_path = atomic_write_json(paths.model_dir / "endpoint_sensitivity_summary.json", summary)
    logger.info("Wrote endpoint sensitivity {}", summary_path)
    return summary_path


def main(argv: Sequence[str] | None = None) -> None:
    """Run the endpoint sensitivity."""
    args = parse_args(argv)
    run(config_path=args.config, repo_root=ROOT)


if __name__ == "__main__":
    main()
