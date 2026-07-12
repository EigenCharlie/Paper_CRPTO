"""Run the fixed-taxonomy, all-policy IJDS comparator audit.

The runner deliberately separates outcome-free allocation materialization from
outcome evaluation. It writes only to a fresh isolated run directory and never
invokes a protected historical DVC stage.
"""

from __future__ import annotations

import argparse
import copy
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from catboost import CatBoostClassifier

from src.data.outcome_observability import (
    DECISION_SPLITS,
    audit_outcome_label_availability,
    build_outcome_label_availability,
    load_design_universe,
    temporal_tail_split,
    terminal_outcome_from_status,
    validate_minimum_label_retention,
)
from src.evaluation.cashflow_payoff import (
    CASH_YIELD_ID,
    exposure_weighted_undiscounted_snapshot_cash_yield,
)
from src.evaluation.comparator_audit import (
    build_fixed_cap_grid,
    comparator_multiverse_envelope,
    contemporaneous_point_cap_target,
    development_supported_cap_range,
    exact_match_diagnostics,
)
from src.evaluation.comparator_transport_simulation import simulate_from_config
from src.evaluation.coverage_transport import build_temporal_conformal_audit
from src.evaluation.ijds_design_sensitivity import build_label_lag_coverage_sensitivity
from src.evaluation.maturity_safe_portfolio import (
    aggregate_monthly_evaluation,
    assert_outcome_free_decision_frame,
    build_decision_panel,
    evaluate_prejoined_frozen_allocation,
    solve_outcome_free_allocation,
)
from src.evaluation.policy_contrast_bounds import sharp_policy_contrast_bounds
from src.features.feature_engineering import run_feature_pipeline
from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    apply_binary_outcome_recipe,
    fit_binary_outcome_recipe,
)
from src.models.maturity_safe_pd import (
    apply_platt_calibrator,
    catboost_raw_margin,
    classification_metrics,
    fit_platt_calibrator,
    validate_model_feature_contract,
)
from src.optimization.policy_selection import LinearPolicyCandidate, build_linear_policy_grid
from src.utils.isolated_experiment import (
    OutputPaths,
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

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT / "configs/experiments/ijds_fixed_taxonomy_c2_2026-07-11.yaml"
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_prefreeze")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_prefreeze")
LABEL_FIT_SPLITS = ("pd_development", "probability_calibration", "conformal_fit")
PRIMARY_ROLE = "primary_oot"


@dataclass(frozen=True)
class PredictionStack:
    """One seed-specific predictor, fixed taxonomy, and decision panel."""

    seed: int
    model: CatBoostClassifier
    calibrator: Any
    recipe: BinaryOutcomeConformalRecipe
    decision_panel: pd.DataFrame
    fit_audit: pd.DataFrame
    metrics: dict[str, Any]
    diagnostic_recipes: dict[int, BinaryOutcomeConformalRecipe]
    diagnostic_panels: dict[int, pd.DataFrame]


@dataclass(frozen=True)
class AllocationBundle:
    """Outcome-free records and funded rows for one policy family cell."""

    records: pd.DataFrame
    allocations: pd.DataFrame


@dataclass(frozen=True)
class UpstreamOutcomeFreeBundle:
    """Verified outcome-free evidence imported from an earlier locked run."""

    records: pd.DataFrame
    allocations: pd.DataFrame
    canonical_panel: pd.DataFrame
    fit_audit: pd.DataFrame
    availability_audit: pd.DataFrame
    prediction_metrics: list[dict[str, Any]]
    diagnostic_recipes: dict[int, BinaryOutcomeConformalRecipe]
    diagnostic_panels: dict[int, pd.DataFrame]
    artifact_descriptors: dict[str, Any]
    model_artifacts: dict[str, Any]
    provenance: dict[str, Any]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def _deep_merge_config(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Merge a small protocol override without duplicating the locked base YAML."""
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if value is None:
            merged.pop(str(key), None)
        elif isinstance(value, Mapping) and isinstance(merged.get(key), dict):
            merged[str(key)] = _deep_merge_config(merged[str(key)], value)
        else:
            merged[str(key)] = copy.deepcopy(value)
    return merged


def _load_config_payload(path: Path, *, seen: frozenset[Path] = frozenset()) -> dict[str, Any]:
    resolved = path.resolve()
    if resolved in seen:
        raise ValueError(f"Protocol config inheritance cycle at {resolved}.")
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Protocol config must be a YAML mapping.")
    extends = payload.pop("extends", None)
    if extends is None:
        return payload
    base_path = (resolved.parent / str(extends)).resolve()
    base = _load_config_payload(base_path, seen=seen | {resolved})
    return _deep_merge_config(base, payload)


def load_config(path: Path) -> dict[str, Any]:
    """Load and validate the locked pre-freeze protocol."""
    payload = _load_config_payload(path)
    required = {
        "schema_version",
        "protocol_status",
        "protocol_tag",
        "run_tag",
        "source",
        "target",
        "design",
        "model",
        "probability_calibration",
        "conformal",
        "payoff",
        "policy",
        "comparators",
        "analysis",
        "simulation",
        "execution",
        "output",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise KeyError(f"Protocol config is missing sections: {missing}")
    allowed_statuses = {
        "locked_retrospective_prefreeze_audit",
        "locked_retrospective_design_sensitivity",
    }
    if payload["protocol_status"] not in allowed_statuses:
        raise ValueError("Unexpected protocol status.")
    if payload["design"].get("historical_archive_previously_inspected") is not True:
        raise ValueError("The inspected-archive disclosure must remain true.")
    if payload["policy"].get("outcome_based_selection") is not False:
        raise ValueError("Outcome-based policy selection is forbidden.")
    if payload["analysis"].get("all_nine_policies_primary") is not True:
        raise ValueError("All nine policies must remain co-primary.")
    if payload["comparators"].get("selection_from_outcomes") is not False:
        raise ValueError("Comparator selection from outcomes is forbidden.")
    if payload["simulation"].get("enabled") is not True:
        raise ValueError("The locked mechanism simulation must remain enabled.")
    sensitivity = payload.get("design_sensitivity", {})
    if sensitivity:
        lags = [int(value) for value in sensitivity.get("charged_off_lag_months", [])]
        if lags != [0, 3, 6, 12]:
            raise ValueError("Label-lag sensitivity must remain the closed 0/3/6/12 grid.")
    seeds = [int(value) for value in payload["model"]["sensitivity_seeds"]]
    if seeds != [40, 41, 42, 43, 44]:
        raise ValueError("Seed sensitivity must remain the closed 40--44 set.")
    purpose_caps = [float(value) for value in payload["policy"]["purpose_cap_sensitivity"]]
    if purpose_caps != [0.2, 0.25, 0.3, 1.0]:
        raise ValueError("Purpose-cap sensitivity grid changed.")
    frontier = payload["comparators"]["point_cap_frontier"]
    build_fixed_cap_grid(frontier["start"], frontier["stop"], frontier["step"])
    resume = payload.get("resume_outcome_free", {})
    if resume and resume.get("enabled") is not True:
        raise ValueError("resume_outcome_free must be absent or explicitly enabled.")
    if resume:
        resume_required = {
            "source_run_tag",
            "source_protocol_tag",
            "source_protocol_commit",
            "source_freeze_sha256",
        }
        resume_missing = sorted(resume_required.difference(resume))
        if resume_missing:
            raise KeyError(f"Outcome-free resume config is missing: {resume_missing}")
    return payload


def _recipe_from_json(path: Path) -> BinaryOutcomeConformalRecipe:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Conformal recipe is not a JSON mapping: {path}")
    for field in (
        "bin_edges",
        "residual_quantiles",
        "group_counts",
        "finite_sample_ranks",
        "raw_finite_sample_ranks",
    ):
        payload[field] = tuple(payload[field])
    return BinaryOutcomeConformalRecipe(**payload)


def _verified_artifact_path(
    descriptor: Mapping[str, Any],
    *,
    repo_root: Path,
) -> Path:
    relative = Path(str(descriptor["path"]))
    path = (repo_root / relative).resolve()
    path.relative_to(repo_root.resolve())
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = relative_artifact_descriptor(path, repo_root=repo_root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor[field]:
            raise RuntimeError(f"Upstream artifact descriptor mismatch for {path} field {field!r}.")
    return path


def _load_upstream_outcome_free_bundle(
    config: Mapping[str, Any],
    *,
    repo_root: Path,
    expected_availability: pd.DataFrame,
) -> UpstreamOutcomeFreeBundle:
    resume = config["resume_outcome_free"]
    source_run_tag = str(resume["source_run_tag"])
    source_model_dir = resolve_isolated_run_dir(
        repo_root=repo_root,
        configured_root=str(config["output"]["model_root"]),
        allowed_relative_root=ALLOWED_MODEL_ROOT,
        run_tag=source_run_tag,
    )
    freeze_path = source_model_dir / "protocol_freeze.json"
    if not freeze_path.is_file():
        raise FileNotFoundError(freeze_path)
    freeze_descriptor = relative_artifact_descriptor(freeze_path, repo_root=repo_root)
    if freeze_descriptor["sha256"] != str(resume["source_freeze_sha256"]):
        raise RuntimeError("Upstream protocol-freeze SHA-256 does not match the locked config.")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    expected_identity = {
        "status": "outcome_free_allocations_frozen_before_outcome_join",
        "run_tag": source_run_tag,
        "protocol_tag": str(resume["source_protocol_tag"]),
        "protocol_commit": str(resume["source_protocol_commit"]),
    }
    for field, expected in expected_identity.items():
        if freeze.get(field) != expected:
            raise RuntimeError(
                f"Upstream protocol freeze has {field}={freeze.get(field)!r}; "
                f"expected {expected!r}."
            )
    if freeze.get("outcome_columns_passed_to_policy_or_comparator") != []:
        raise RuntimeError("Upstream freeze reports outcome leakage into policy construction.")

    artifacts = freeze["outcome_free_artifacts"]
    paths = {
        name: _verified_artifact_path(descriptor, repo_root=repo_root)
        for name, descriptor in artifacts.items()
    }
    records = pd.read_parquet(paths["records"])
    allocations = pd.read_parquet(paths["allocations"])
    canonical_panel = pd.read_parquet(paths["canonical_decision_panel"])
    fit_audit = pd.read_parquet(paths["conformal_fit_audit"])
    availability = pd.read_parquet(paths["label_availability_audit"])
    pd.testing.assert_frame_equal(
        availability.reset_index(drop=True),
        expected_availability.reset_index(drop=True),
        check_dtype=False,
    )
    assert_outcome_free_decision_frame(canonical_panel.drop(columns="design_split"))
    forbidden = {"loan_status", "snapshot_default", "terminal_default", "total_pymnt"}
    if forbidden.intersection(allocations.columns.astype(str).str.casefold()):
        raise RuntimeError("Upstream funded allocations contain an outcome field.")

    model_artifacts = freeze["model_artifacts"]
    recipes: dict[int, BinaryOutcomeConformalRecipe] = {}
    prediction_metrics: list[dict[str, Any]] = []
    for seed in [int(value) for value in config["model"]["sensitivity_seeds"]]:
        seed_artifacts = model_artifacts[str(seed)]
        for descriptor in (
            seed_artifacts["model"],
            seed_artifacts["calibrator"],
            seed_artifacts["recipe"],
            *seed_artifacts["diagnostic_recipes"].values(),
        ):
            _verified_artifact_path(descriptor, repo_root=repo_root)
        recipe_path = _verified_artifact_path(
            seed_artifacts["recipe"],
            repo_root=repo_root,
        )
        recipe = _recipe_from_json(recipe_path)
        seed_fit = fit_audit.loc[fit_audit["seed"].eq(seed)]
        if len(seed_fit) != sum(recipe.group_counts):
            raise RuntimeError(f"Conformal fit rows do not reconcile for seed {seed}.")
        prediction_metrics.append(
            {
                "seed": seed,
                "source": "verified_upstream_outcome_free_freeze",
                "conformal_fit_rows": int(len(seed_fit)),
                "conformal_fit_coverage": float(seed_fit["covered"].mean()),
                "fixed_taxonomy_edges": list(recipe.bin_edges),
                "residual_group_counts": list(recipe.group_counts),
                "residual_quantiles": list(recipe.residual_quantiles),
                "numeric_features": list(config["model"]["numeric_features"]),
                "categorical_features": list(config["model"]["categorical_features"]),
            }
        )
        if seed == int(config["model"]["canonical_seed"]):
            recipes = {
                int(groups): _recipe_from_json(
                    _verified_artifact_path(descriptor, repo_root=repo_root)
                )
                for groups, descriptor in seed_artifacts["diagnostic_recipes"].items()
            }
    if not recipes:
        raise RuntimeError("Canonical diagnostic recipes are unavailable upstream.")
    probability = canonical_panel["pd_point"].to_numpy(dtype=float)
    diagnostic_panels: dict[int, pd.DataFrame] = {}
    for groups, recipe in sorted(recipes.items()):
        assigned, lower, upper = apply_binary_outcome_recipe(probability, recipe)
        panel = canonical_panel.copy()
        panel["conformal_group"] = assigned
        panel["conformal_lower"] = lower
        panel["conformal_upper"] = upper
        diagnostic_panels[groups] = panel
    canonical_groups = int(config["conformal"]["canonical_groups"])
    canonical_rebuilt = diagnostic_panels[canonical_groups]
    for column in ("conformal_group", "conformal_lower", "conformal_upper"):
        np.testing.assert_allclose(
            canonical_rebuilt[column].to_numpy(dtype=float),
            canonical_panel[column].to_numpy(dtype=float),
            rtol=0.0,
            atol=0.0,
        )
    return UpstreamOutcomeFreeBundle(
        records=records,
        allocations=allocations,
        canonical_panel=canonical_panel,
        fit_audit=fit_audit,
        availability_audit=availability,
        prediction_metrics=prediction_metrics,
        diagnostic_recipes=recipes,
        diagnostic_panels=diagnostic_panels,
        artifact_descriptors=dict(artifacts),
        model_artifacts=dict(model_artifacts),
        provenance={
            "source_run_tag": source_run_tag,
            "source_protocol_tag": freeze["protocol_tag"],
            "source_protocol_commit": freeze["protocol_commit"],
            "source_protocol_freeze": freeze_descriptor,
            "source_implementation_provenance": freeze["implementation_provenance"],
            "reuse_scope": "outcome_free_predictions_models_and_allocations_only",
        },
    )


def _terminal_resolution(outcomes: pd.Series) -> pd.Series:
    resolution = pd.Series("right_censored", index=outcomes.index, dtype="string")
    resolution.loc[outcomes.eq(0).fillna(False)] = "fully_paid"
    resolution.loc[outcomes.eq(1).fillna(False)] = "charged_off"
    return resolution


def _prepare_universe(
    config: Mapping[str, Any],
    *,
    raw_path: Path,
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    universe, source_inventory = load_design_universe(
        config,
        raw_path=raw_path,
        label_required_splits=LABEL_FIT_SPLITS,
    )
    label_info = build_outcome_label_availability(
        universe["loan_status"],
        universe["last_pymnt_d"],
        cutoff=str(config["source"]["information_cutoff"]),
        charged_off_lag_months=int(config["source"]["charged_off_reporting_lag_months"]),
    )
    universe["terminal_default"] = terminal_outcome_from_status(universe["loan_status"])
    universe["label_available"] = label_info["label_available"].astype(bool)
    universe["label_available_at"] = label_info["label_available_at"]
    audit = audit_outcome_label_availability(
        universe.loc[universe["design_split"].isin(LABEL_FIT_SPLITS)],
        cutoff=str(config["source"]["information_cutoff"]),
        charged_off_lag_months=int(config["source"]["charged_off_reporting_lag_months"]),
    )
    validate_minimum_label_retention(
        audit,
        minimum_retention=float(config["source"]["minimum_label_retention"]),
    )
    return universe, source_inventory, audit


def _engineer_features(
    universe: pd.DataFrame,
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, list[str], list[str]]:
    numeric, categorical = validate_model_feature_contract(config["model"])
    source = universe.drop(
        columns=[
            "loan_status",
            "snapshot_default",
            "snapshot_resolution",
            "terminal_default",
            "label_available",
            "label_available_at",
            "total_pymnt",
        ],
        errors="ignore",
    )
    engineered = run_feature_pipeline(source)
    output = pd.DataFrame(index=universe.index)
    for feature in numeric:
        values = engineered.get(feature, pd.Series(np.nan, index=universe.index))
        output[feature] = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan)
    for feature in categorical:
        values = engineered.get(feature, pd.Series("__MISSING__", index=universe.index))
        output[feature] = values.astype("string").fillna("__MISSING__").astype(str)
    return output, numeric, categorical


def _available_labels(frame: pd.DataFrame, *, block: str) -> np.ndarray:
    if not bool(frame["label_available"].all()):
        raise RuntimeError(f"{block} contains unavailable labels after filtering.")
    labels = frame["terminal_default"]
    if bool(labels.isna().any()):
        raise RuntimeError(f"{block} contains right-censored labels after filtering.")
    values = labels.astype(int).to_numpy(dtype=int)
    if set(np.unique(values)) != {0, 1}:
        raise RuntimeError(f"{block} must contain both terminal outcome classes.")
    return values


def _prediction_metrics(labels: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    metrics = classification_metrics(labels, probabilities)
    bins = pd.cut(probabilities, bins=np.linspace(0.0, 1.0, 11), include_lowest=True)
    audit = pd.DataFrame({"p": probabilities, "y": labels, "bin": bins})
    grouped = audit.groupby("bin", observed=True).agg(
        p=("p", "mean"), y=("y", "mean"), n=("y", "size")
    )
    metrics["ece_10"] = float(
        np.sum(grouped["n"].to_numpy() * np.abs(grouped["p"] - grouped["y"])) / len(audit)
    )
    return metrics


def _temporal_prediction_metrics(
    decision_panel: pd.DataFrame,
    outcomes: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Evaluate canonical point-PD diagnostics after the outcome-free freeze."""
    joined = decision_panel[["id", "design_split", "pd_point"]].merge(
        outcomes[["id", "snapshot_default"]],
        on="id",
        how="left",
        validate="one_to_one",
    )
    rows: list[dict[str, Any]] = []
    for role, frame in joined.groupby("design_split", sort=True):
        resolved = frame["snapshot_default"].notna()
        labels = frame.loc[resolved, "snapshot_default"].astype(int).to_numpy(dtype=int)
        probabilities = frame.loc[resolved, "pd_point"].to_numpy(dtype=float)
        metrics = _prediction_metrics(labels, probabilities)
        rows.append(
            {
                "role": str(role),
                "candidate_rows": int(len(frame)),
                "resolved_rows": int(resolved.sum()),
                "unresolved_rows": int((~resolved).sum()),
                **metrics,
            }
        )
    return rows


def _fit_prediction_stack(
    universe: pd.DataFrame,
    features: pd.DataFrame,
    *,
    numeric_features: Sequence[str],
    categorical_features: Sequence[str],
    config: Mapping[str, Any],
    seed: int,
) -> PredictionStack:
    development = universe.loc[
        universe["design_split"].eq("pd_development") & universe["label_available"]
    ].copy()
    train, validation, validation_cutoff = temporal_tail_split(
        development,
        tail_fraction=float(config["design"]["validation_tail_fraction"]),
    )
    model_params = dict(config["model"]["fixed_params"])
    model_params.update(
        random_seed=int(seed),
        thread_count=int(config["execution"]["threads"]),
    )
    model = CatBoostClassifier(**model_params)
    model.fit(
        features.loc[train.index],
        _available_labels(train, block="pd_development_train"),
        cat_features=list(categorical_features),
    )
    validation_probability = np.asarray(
        model.predict_proba(features.loc[validation.index])[:, 1], dtype=float
    )
    validation_labels = _available_labels(validation, block="pd_development_validation")

    calibration_all = universe.loc[universe["design_split"].eq("probability_calibration")]
    calibration_fit = calibration_all.loc[calibration_all["label_available"]]
    calibration_margin = catboost_raw_margin(model, features.loc[calibration_fit.index])
    calibrator_config = copy.deepcopy(config["probability_calibration"])
    calibrator_config["logistic_regression"]["random_state"] = int(seed)
    calibrator = fit_platt_calibrator(
        calibration_margin,
        _available_labels(calibration_fit, block="probability_calibration"),
        calibrator_config,
    )
    calibration_all_probability = apply_platt_calibrator(
        calibrator,
        catboost_raw_margin(model, features.loc[calibration_all.index]),
    )
    group_count = int(config["conformal"]["canonical_groups"])
    fixed_edges = np.quantile(
        calibration_all_probability,
        np.linspace(0.0, 1.0, group_count + 1),
        method="linear",
    )
    if bool(np.any(np.diff(fixed_edges) <= 0.0)):
        raise RuntimeError("Upstream 2011 taxonomy contains repeated score edges.")

    conformal = universe.loc[
        universe["design_split"].eq("conformal_fit") & universe["label_available"]
    ]
    conformal_probability = apply_platt_calibrator(
        calibrator,
        catboost_raw_margin(model, features.loc[conformal.index]),
    )
    conformal_labels = _available_labels(conformal, block="conformal_fit")
    recipe = fit_binary_outcome_recipe(
        conformal_probability,
        conformal_labels,
        alpha=float(config["conformal"]["alpha"]),
        n_groups=group_count,
        bin_edges=fixed_edges.tolist(),
        taxonomy_provenance="2011_all_status_independent_calibrated_scores",
        taxonomy_method="fixed_empirical_linear_score_quantiles",
        method=str(config["conformal"]["method"]),
    )
    minimum_group_rows = int(config["conformal"]["minimum_rows_per_group"])
    if min(recipe.group_counts) < minimum_group_rows:
        raise RuntimeError(
            f"Fixed-taxonomy residual group has fewer than {minimum_group_rows} rows."
        )
    groups, lower, upper = apply_binary_outcome_recipe(conformal_probability, recipe)
    covered = (conformal_labels >= lower) & (conformal_labels <= upper)
    fit_audit = pd.DataFrame(
        {
            "id": conformal["id"].astype("string").to_numpy(),
            "issue_d": conformal["issue_d"].to_numpy(),
            "seed": int(seed),
            "conformal_group": groups,
            "pd_point": conformal_probability,
            "conformal_lower": lower,
            "conformal_upper": upper,
            "terminal_default": conformal_labels,
            "covered": covered,
        }
    )

    decision_source = universe.loc[universe["design_split"].isin(DECISION_SPLITS)]
    decision_probability = apply_platt_calibrator(
        calibrator,
        catboost_raw_margin(model, features.loc[decision_source.index]),
    )
    decision_groups, decision_lower, decision_upper = apply_binary_outcome_recipe(
        decision_probability,
        recipe,
    )
    decision_panel = build_decision_panel(
        decision_source,
        pd_point=decision_probability,
        conformal_lower=decision_lower,
        conformal_upper=decision_upper,
        conformal_groups=decision_groups,
    )
    decision_panel["design_split"] = decision_source["design_split"].astype(str).to_numpy()
    assert_outcome_free_decision_frame(decision_panel)

    diagnostic_recipes: dict[int, BinaryOutcomeConformalRecipe] = {}
    diagnostic_panels: dict[int, pd.DataFrame] = {}
    for diagnostic_groups in [
        int(value) for value in config["conformal"]["diagnostic_group_counts"]
    ]:
        if diagnostic_groups == group_count:
            diagnostic_recipe = recipe
            diagnostic_panel = decision_panel.copy()
        else:
            diagnostic_edges = np.quantile(
                calibration_all_probability,
                np.linspace(0.0, 1.0, diagnostic_groups + 1),
                method="linear",
            )
            diagnostic_recipe = fit_binary_outcome_recipe(
                conformal_probability,
                conformal_labels,
                alpha=float(config["conformal"]["alpha"]),
                n_groups=diagnostic_groups,
                bin_edges=diagnostic_edges.tolist(),
                taxonomy_provenance="2011_all_status_independent_calibrated_scores",
                taxonomy_method="fixed_empirical_linear_score_quantiles",
                method=str(config["conformal"]["method"]),
            )
            diagnostic_group, diagnostic_lower, diagnostic_upper = apply_binary_outcome_recipe(
                decision_probability,
                diagnostic_recipe,
            )
            diagnostic_panel = decision_panel.copy()
            diagnostic_panel["conformal_group"] = diagnostic_group
            diagnostic_panel["conformal_lower"] = diagnostic_lower
            diagnostic_panel["conformal_upper"] = diagnostic_upper
        diagnostic_recipes[diagnostic_groups] = diagnostic_recipe
        diagnostic_panels[diagnostic_groups] = diagnostic_panel

    calibration_fit_probability = apply_platt_calibrator(calibrator, calibration_margin)
    metrics = {
        "seed": int(seed),
        "validation_cutoff": str(validation_cutoff.to_period("M")),
        "validation": _prediction_metrics(validation_labels, validation_probability),
        "probability_calibration": _prediction_metrics(
            _available_labels(calibration_fit, block="probability_calibration"),
            calibration_fit_probability,
        ),
        "conformal_fit_rows": int(len(conformal)),
        "conformal_fit_coverage": float(np.mean(covered)),
        "fixed_taxonomy_edges": [float(value) for value in fixed_edges],
        "residual_group_counts": [int(value) for value in recipe.group_counts],
        "residual_quantiles": [float(value) for value in recipe.residual_quantiles],
        "numeric_features": list(numeric_features),
        "categorical_features": list(categorical_features),
    }
    return PredictionStack(
        seed=int(seed),
        model=model,
        calibrator=calibrator,
        recipe=recipe,
        decision_panel=decision_panel,
        fit_audit=fit_audit,
        metrics=metrics,
        diagnostic_recipes=diagnostic_recipes,
        diagnostic_panels=diagnostic_panels,
    )


def _policy_candidates(config: Mapping[str, Any]) -> list[LinearPolicyCandidate]:
    grid = build_linear_policy_grid(
        risk_tolerances=[float(value) for value in config["policy"]["risk_tolerances"]],
        gammas=[float(value) for value in config["policy"]["gammas"]],
        uncertainty_aversions=[float(value) for value in config["policy"]["uncertainty_aversions"]],
    )
    if len(grid) != 9:
        raise RuntimeError("The closed guardrail family must contain exactly nine policies.")
    return [
        LinearPolicyCandidate(
            candidate_id=candidate.candidate_id,
            risk_tolerance=candidate.risk_tolerance,
            gamma=candidate.gamma,
            uncertainty_aversion=candidate.uncertainty_aversion,
            policy_mode=candidate.policy_mode,
            delta_cap_quantile=candidate.delta_cap_quantile,
            tail_focus_quantile=candidate.tail_focus_quantile,
            min_budget_utilization=float(config["policy"]["min_budget_utilization_solver"]),
            pd_cap_slack_penalty=candidate.pd_cap_slack_penalty,
        )
        for candidate in grid
    ]


def _point_candidate(
    candidate_id: str, cap: float, config: Mapping[str, Any]
) -> LinearPolicyCandidate:
    return LinearPolicyCandidate(
        candidate_id=candidate_id,
        risk_tolerance=float(cap),
        gamma=0.0,
        uncertainty_aversion=0.0,
        min_budget_utilization=float(config["policy"]["min_budget_utilization_solver"]),
    )


def _cell_config(
    config: Mapping[str, Any], *, seed: int, purpose_cap: float, lgd: float
) -> dict[str, Any]:
    cell = copy.deepcopy(dict(config))
    cell["execution"]["random_seed"] = int(seed)
    cell["policy"]["max_concentration_by_purpose"] = float(purpose_cap)
    cell["payoff"]["lgd"] = float(lgd)
    return cell


def _period_frames(panel: pd.DataFrame, role: str) -> list[tuple[str, pd.DataFrame]]:
    role_frame = panel.loc[panel["design_split"].eq(role)].drop(columns="design_split")
    periods = pd.to_datetime(role_frame["issue_d"]).dt.to_period("M")
    return [
        (str(period), role_frame.loc[periods.eq(period)].copy())
        for period in sorted(periods.unique())
    ]


def _solve_guardrail_family(
    panel: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    role: str,
    seed: int,
    purpose_cap: float,
    lgd: float,
    include_multiverse: bool,
) -> AllocationBundle:
    records: list[dict[str, Any]] = []
    allocations: list[pd.DataFrame] = []
    match_tolerance = float(config["comparators"]["match_tolerance"])
    policies = _policy_candidates(config)
    cell = _cell_config(config, seed=seed, purpose_cap=purpose_cap, lgd=lgd)
    for period, month in _period_frames(panel, role):
        for policy in policies:
            guard_label = f"guardrail_{policy.candidate_id}"
            guard_record, guard_allocation = solve_outcome_free_allocation(
                month,
                policy,
                config=cell,
                robust=True,
                role=role,
                period=period,
                policy_label=guard_label,
            )
            target = contemporaneous_point_cap_target(guard_allocation)
            point_label = f"c2_point_{policy.candidate_id}"
            point = _point_candidate(f"c2-{policy.candidate_id}-{period}", target, config)
            point_record, point_allocation = solve_outcome_free_allocation(
                month,
                point,
                config=cell,
                robust=False,
                role=role,
                period=period,
                policy_label=point_label,
            )
            diagnostics = exact_match_diagnostics(
                point_allocation["exposure"].to_numpy(dtype=float),
                point_allocation["pd_point"].to_numpy(dtype=float),
                target=target,
                tolerance=match_tolerance,
            )
            if not diagnostics.matched:
                raise RuntimeError(
                    f"C2 point-risk match failed for {policy.candidate_id} {period}: "
                    f"{diagnostics.absolute_difference:.3e}."
                )
            for comparator_rule, record, allocation in (
                ("guardrail", guard_record, guard_allocation),
                ("c2_contemporaneous", point_record, point_allocation),
            ):
                record.update(
                    seed=int(seed),
                    purpose_cap=float(purpose_cap),
                    lgd=float(lgd),
                    comparator_rule=comparator_rule,
                    paired_policy_id=policy.candidate_id,
                    c2_target_point_risk=target,
                    c2_match_residual=diagnostics.difference,
                )
                allocation = allocation.assign(
                    seed=int(seed),
                    purpose_cap=float(purpose_cap),
                    lgd=float(lgd),
                    comparator_rule=comparator_rule,
                    paired_policy_id=policy.candidate_id,
                    c2_target_point_risk=target,
                    c2_match_residual=diagnostics.difference,
                )
                records.append(record)
                allocations.append(allocation)
            if include_multiverse:
                same_label = f"c0_same_cap_point_{policy.candidate_id}"
                same_point = _point_candidate(
                    f"c0-{policy.candidate_id}-{period}",
                    float(policy.risk_tolerance),
                    config,
                )
                same_record, same_allocation = solve_outcome_free_allocation(
                    month,
                    same_point,
                    config=cell,
                    robust=False,
                    role=role,
                    period=period,
                    policy_label=same_label,
                )
                same_record.update(
                    seed=int(seed),
                    purpose_cap=float(purpose_cap),
                    lgd=float(lgd),
                    comparator_rule="c0_same_numeric_cap",
                    paired_policy_id=policy.candidate_id,
                    c2_target_point_risk=np.nan,
                    c2_match_residual=np.nan,
                )
                allocations.append(
                    same_allocation.assign(
                        seed=int(seed),
                        purpose_cap=float(purpose_cap),
                        lgd=float(lgd),
                        comparator_rule="c0_same_numeric_cap",
                        paired_policy_id=policy.candidate_id,
                        c2_target_point_risk=np.nan,
                        c2_match_residual=np.nan,
                    )
                )
                records.append(same_record)
    return AllocationBundle(pd.DataFrame(records), pd.concat(allocations, ignore_index=True))


def _solve_point_frontier(
    panel: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    seed: int,
    purpose_cap: float,
) -> AllocationBundle:
    frontier = config["comparators"]["point_cap_frontier"]
    caps = build_fixed_cap_grid(frontier["start"], frontier["stop"], frontier["step"])
    cell = _cell_config(
        config,
        seed=seed,
        purpose_cap=purpose_cap,
        lgd=float(config["payoff"]["lgd"]),
    )
    records: list[dict[str, Any]] = []
    allocations: list[pd.DataFrame] = []
    for period, month in _period_frames(panel, PRIMARY_ROLE):
        for index, cap in enumerate(caps):
            label = f"frontier_point_{index:02d}"
            candidate = _point_candidate(f"frontier-{index:02d}-{period}", float(cap), config)
            record, allocation = solve_outcome_free_allocation(
                month,
                candidate,
                config=cell,
                robust=False,
                role=PRIMARY_ROLE,
                period=period,
                policy_label=label,
            )
            record.update(
                seed=int(seed),
                purpose_cap=float(purpose_cap),
                lgd=float(config["payoff"]["lgd"]),
                comparator_rule="point_cap_frontier",
                paired_policy_id="frontier",
                frontier_cap=float(cap),
            )
            records.append(record)
            allocations.append(
                allocation.assign(
                    seed=int(seed),
                    purpose_cap=float(purpose_cap),
                    lgd=float(config["payoff"]["lgd"]),
                    comparator_rule="point_cap_frontier",
                    paired_policy_id="frontier",
                    frontier_cap=float(cap),
                )
            )
    return AllocationBundle(pd.DataFrame(records), pd.concat(allocations, ignore_index=True))


def _development_fixed_targets(allocations: pd.DataFrame) -> dict[str, float]:
    """Return each guardrail's outcome-free funded point-risk moment in development."""
    guardrails = allocations.loc[allocations["comparator_rule"].eq("guardrail")]
    targets = {
        str(policy_id): contemporaneous_point_cap_target(frame)
        for policy_id, frame in guardrails.groupby("paired_policy_id", observed=True, sort=True)
    }
    if len(targets) != 9:
        raise RuntimeError("Development fixed-cap construction requires all nine guardrails.")
    return targets


def _solve_development_fixed_comparators(
    panel: pd.DataFrame,
    *,
    targets: Mapping[str, float],
    config: Mapping[str, Any],
    seed: int,
    purpose_cap: float,
    lgd: float,
    role: str,
) -> AllocationBundle:
    """Apply outcome-free development-funded-PD caps to later monthly menus."""
    cell = _cell_config(config, seed=seed, purpose_cap=purpose_cap, lgd=lgd)
    records: list[dict[str, Any]] = []
    allocations: list[pd.DataFrame] = []
    for period, month in _period_frames(panel, role):
        for policy_id, target in sorted(targets.items()):
            label = f"c1_development_fixed_point_{policy_id}"
            candidate = _point_candidate(f"c1-{policy_id}-{period}", target, config)
            record, allocation = solve_outcome_free_allocation(
                month,
                candidate,
                config=cell,
                robust=False,
                role=role,
                period=period,
                policy_label=label,
            )
            record.update(
                seed=int(seed),
                purpose_cap=float(purpose_cap),
                lgd=float(lgd),
                comparator_rule="c1_development_fixed",
                paired_policy_id=policy_id,
                development_fixed_point_cap=float(target),
            )
            records.append(record)
            allocations.append(
                allocation.assign(
                    seed=int(seed),
                    purpose_cap=float(purpose_cap),
                    lgd=float(lgd),
                    comparator_rule="c1_development_fixed",
                    paired_policy_id=policy_id,
                    development_fixed_point_cap=float(target),
                )
            )
    return AllocationBundle(pd.DataFrame(records), pd.concat(allocations, ignore_index=True))


def _allocation_max_difference(left: pd.DataFrame, right: pd.DataFrame) -> float:
    union = (
        left[["id", "exposure"]]
        .merge(
            right[["id", "exposure"]],
            on="id",
            how="outer",
            suffixes=("_left", "_right"),
        )
        .fillna(0.0)
    )
    return float(np.max(np.abs(union["exposure_left"] - union["exposure_right"])))


def _pooled_residual_quantile(fit_audit: pd.DataFrame, *, alpha: float) -> float:
    residual = np.sort(
        np.abs(
            fit_audit["terminal_default"].to_numpy(dtype=float)
            - fit_audit["pd_point"].to_numpy(dtype=float)
        )
    )
    raw_rank = int(np.ceil((len(residual) + 1) * (1.0 - float(alpha))))
    return 1.0 if raw_rank > len(residual) else float(residual[raw_rank - 1])


def _solve_score_ablations(
    panel: pd.DataFrame,
    *,
    recipe: BinaryOutcomeConformalRecipe,
    fit_audit: pd.DataFrame,
    config: Mapping[str, Any],
    seed: int,
    purpose_cap: float,
    lgd: float,
) -> AllocationBundle:
    """Solve group-penalty and affine pooled-score mechanism ablations."""
    cell = _cell_config(config, seed=seed, purpose_cap=purpose_cap, lgd=lgd)
    group_penalties = np.asarray(recipe.residual_quantiles, dtype=float)
    pooled_penalty = _pooled_residual_quantile(
        fit_audit,
        alpha=float(config["conformal"]["alpha"]),
    )
    tolerance = float(config["comparators"]["match_tolerance"])
    records: list[dict[str, Any]] = []
    allocations: list[pd.DataFrame] = []
    for period, month in _period_frames(panel, PRIMARY_ROLE):
        point = month["pd_point"].to_numpy(dtype=float)
        groups = month["conformal_group"].to_numpy(dtype=int)
        for policy in _policy_candidates(config):
            group_score = point + float(policy.gamma) * group_penalties[groups]
            group_label = f"ablation_group_penalty_{policy.candidate_id}"
            group_record, group_allocation = solve_outcome_free_allocation(
                month,
                policy,
                config=cell,
                robust=True,
                role=PRIMARY_ROLE,
                period=period,
                policy_label=group_label,
                effective_score_override=group_score,
            )
            target = contemporaneous_point_cap_target(group_allocation)
            group_point_label = f"ablation_group_c2_point_{policy.candidate_id}"
            group_point = _point_candidate(
                f"ablation-group-c2-{policy.candidate_id}-{period}",
                target,
                config,
            )
            point_record, point_allocation = solve_outcome_free_allocation(
                month,
                group_point,
                config=cell,
                robust=False,
                role=PRIMARY_ROLE,
                period=period,
                policy_label=group_point_label,
            )
            diagnostics = exact_match_diagnostics(
                point_allocation["exposure"].to_numpy(dtype=float),
                point_allocation["pd_point"].to_numpy(dtype=float),
                target=target,
                tolerance=tolerance,
            )
            if not diagnostics.matched:
                raise RuntimeError("Group-penalty C2 comparator failed to match funded point risk.")
            for rule, record, allocation in (
                ("ablation_group_penalty", group_record, group_allocation),
                ("ablation_group_c2", point_record, point_allocation),
            ):
                record.update(
                    seed=int(seed),
                    purpose_cap=float(purpose_cap),
                    lgd=float(lgd),
                    comparator_rule=rule,
                    paired_policy_id=policy.candidate_id,
                    c2_target_point_risk=target,
                    c2_match_residual=diagnostics.difference,
                )
                records.append(record)
                allocations.append(
                    allocation.assign(
                        seed=int(seed),
                        purpose_cap=float(purpose_cap),
                        lgd=float(lgd),
                        comparator_rule=rule,
                        paired_policy_id=policy.candidate_id,
                        c2_target_point_risk=target,
                        c2_match_residual=diagnostics.difference,
                    )
                )

            pooled_score = point + float(policy.gamma) * pooled_penalty
            translated_cap = float(policy.risk_tolerance) + float(policy.gamma) * pooled_penalty
            pooled_candidate = LinearPolicyCandidate(
                candidate_id=f"ablation-pooled-{policy.candidate_id}",
                risk_tolerance=translated_cap,
                gamma=policy.gamma,
                uncertainty_aversion=0.0,
                min_budget_utilization=float(config["policy"]["min_budget_utilization_solver"]),
            )
            pooled_label = f"ablation_pooled_affine_{policy.candidate_id}"
            pooled_record, pooled_allocation = solve_outcome_free_allocation(
                month,
                pooled_candidate,
                config=cell,
                robust=True,
                role=PRIMARY_ROLE,
                period=period,
                policy_label=pooled_label,
                effective_score_override=pooled_score,
            )
            translated_point_label = f"ablation_pooled_point_{policy.candidate_id}"
            translated_point = _point_candidate(
                f"ablation-pooled-point-{policy.candidate_id}-{period}",
                float(policy.risk_tolerance),
                config,
            )
            translated_record, translated_allocation = solve_outcome_free_allocation(
                month,
                translated_point,
                config=cell,
                robust=False,
                role=PRIMARY_ROLE,
                period=period,
                policy_label=translated_point_label,
            )
            allocation_difference = _allocation_max_difference(
                pooled_allocation,
                translated_allocation,
            )
            if allocation_difference > 1e-5:
                raise RuntimeError(
                    "Affine pooled-score placebo did not reproduce the translated point policy."
                )
            for rule, record, allocation in (
                ("ablation_pooled_affine", pooled_record, pooled_allocation),
                ("ablation_pooled_point", translated_record, translated_allocation),
            ):
                record.update(
                    seed=int(seed),
                    purpose_cap=float(purpose_cap),
                    lgd=float(lgd),
                    comparator_rule=rule,
                    paired_policy_id=policy.candidate_id,
                    pooled_residual_penalty=pooled_penalty,
                    affine_translated_score_cap=translated_cap,
                    affine_allocation_max_difference=allocation_difference,
                )
                records.append(record)
                allocations.append(
                    allocation.assign(
                        seed=int(seed),
                        purpose_cap=float(purpose_cap),
                        lgd=float(lgd),
                        comparator_rule=rule,
                        paired_policy_id=policy.candidate_id,
                        pooled_residual_penalty=pooled_penalty,
                        affine_translated_score_cap=translated_cap,
                        affine_allocation_max_difference=allocation_difference,
                    )
                )
    return AllocationBundle(pd.DataFrame(records), pd.concat(allocations, ignore_index=True))


def _outcome_panel(universe: pd.DataFrame) -> pd.DataFrame:
    terminal = universe["terminal_default"].astype("Int8")
    return pd.DataFrame(
        {
            "id": universe["id"].astype("string"),
            "loan_status": universe["loan_status"].astype("string"),
            "snapshot_default": terminal,
            "snapshot_resolution": _terminal_resolution(terminal),
            "funded_amnt": pd.to_numeric(universe["funded_amnt"], errors="raise"),
            "total_pymnt": pd.to_numeric(universe["total_pymnt"], errors="raise"),
            "role": universe["design_split"].astype("string"),
            "period": pd.to_datetime(universe["issue_d"]).dt.to_period("M").astype(str),
        }
    )


def _evaluate_allocations(
    records: pd.DataFrame,
    allocations: pd.DataFrame,
    outcomes: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    evaluated_records: list[dict[str, Any]] = []
    joined_frames: list[pd.DataFrame] = []
    key_columns = [
        "seed",
        "purpose_cap",
        "lgd",
        "role",
        "period",
        "policy_label",
        "comparator_rule",
        "paired_policy_id",
    ]
    record_index = records.set_index(key_columns, verify_integrity=True)
    candidate_unresolved = outcomes.groupby(["role", "period"], observed=True)[
        "snapshot_default"
    ].apply(lambda values: int(values.isna().sum()))
    outcome_columns = [
        "id",
        "loan_status",
        "snapshot_default",
        "snapshot_resolution",
        "funded_amnt",
        "total_pymnt",
    ]
    joined_allocations = allocations.merge(
        outcomes[outcome_columns],
        on="id",
        how="left",
        validate="many_to_one",
    )
    if len(joined_allocations) != len(allocations):
        raise RuntimeError("Shared outcome join changed the funded-allocation row count.")
    grouped = joined_allocations.groupby(key_columns, observed=True, sort=True)
    if grouped.ngroups != len(record_index):
        raise RuntimeError(
            "Outcome-free records and funded-allocation groups have different cardinality."
        )
    for raw_keys, allocation in grouped:
        key_values = raw_keys if isinstance(raw_keys, tuple) else (raw_keys,)
        if len(key_values) != len(key_columns):
            raise RuntimeError("Funded-allocation group key has unexpected cardinality.")
        base_row = record_index.loc[key_values]
        if isinstance(base_row, pd.DataFrame):
            raise RuntimeError(f"Outcome-free record lookup is not unique for {key_values}.")
        base_record = base_row.to_dict()
        base_record.update(dict(zip(key_columns, key_values, strict=True)))
        cell = _cell_config(
            config,
            seed=int(base_record["seed"]),
            purpose_cap=float(base_record["purpose_cap"]),
            lgd=float(base_record["lgd"]),
        )
        role = str(base_record["role"])
        period = str(base_record["period"])
        unresolved_key = (role, period)
        if unresolved_key not in candidate_unresolved.index:
            raise RuntimeError(f"Candidate outcome count is unavailable for {unresolved_key}.")
        record, joined = evaluate_prejoined_frozen_allocation(
            base_record,
            allocation,
            config=cell,
            n_unresolved_candidates=int(candidate_unresolved.loc[unresolved_key]),
        )
        scaled_principal = joined["allocation_fraction"].to_numpy(dtype=float) * joined[
            "funded_amnt"
        ].to_numpy(dtype=float)
        scaled_payments = joined["allocation_fraction"].to_numpy(dtype=float) * joined[
            "total_pymnt"
        ].to_numpy(dtype=float)
        record["cash_yield_id"] = CASH_YIELD_ID
        record["undiscounted_snapshot_cash_yield"] = (
            exposure_weighted_undiscounted_snapshot_cash_yield(
                scaled_principal,
                scaled_payments,
            )
        )
        evaluated_records.append(record)
        joined_frames.append(joined)
    return pd.DataFrame(evaluated_records), pd.concat(joined_frames, ignore_index=True)


def _aggregate_monthly(frame: pd.DataFrame) -> pd.DataFrame:
    keys = [
        "seed",
        "purpose_cap",
        "lgd",
        "role",
        "policy_label",
        "comparator_rule",
        "paired_policy_id",
    ]
    rows: list[dict[str, Any]] = []
    for raw_key_values, group in frame.groupby(keys, observed=True, sort=True):
        key_values = raw_key_values if isinstance(raw_key_values, tuple) else (raw_key_values,)
        if len(key_values) != len(keys):
            raise RuntimeError("Monthly-evaluation group key has unexpected cardinality.")
        row = aggregate_monthly_evaluation(group)
        row.update(dict(zip(keys, key_values, strict=True)))
        weights = group["total_allocated"].to_numpy(dtype=float)
        row["undiscounted_snapshot_cash_yield"] = float(
            np.average(group["undiscounted_snapshot_cash_yield"], weights=weights)
        )
        rows.append(row)
    return pd.DataFrame(rows)


def _paired_contrasts(
    joined_allocations: pd.DataFrame,
    evaluated: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    policies = [candidate.candidate_id for candidate in _policy_candidates(config)]
    cells = evaluated.loc[
        evaluated["comparator_rule"].eq("guardrail"),
        ["seed", "purpose_cap", "lgd", "role"],
    ].drop_duplicates()
    for cell in cells.itertuples(index=False):
        role_allocations = joined_allocations.loc[
            joined_allocations["seed"].eq(cell.seed)
            & joined_allocations["purpose_cap"].eq(cell.purpose_cap)
            & joined_allocations["lgd"].eq(cell.lgd)
            & joined_allocations["role"].eq(cell.role)
        ]
        for policy_id in policies:
            guard_label = f"guardrail_{policy_id}"
            for comparator_rule, point_prefix in (
                ("c2_contemporaneous", "c2_point"),
                ("c0_same_numeric_cap", "c0_same_cap_point"),
                ("c1_development_fixed", "c1_development_fixed_point"),
            ):
                point_label = f"{point_prefix}_{policy_id}"
                if not bool(role_allocations["policy_label"].eq(point_label).any()):
                    continue
                bounds = sharp_policy_contrast_bounds(
                    role_allocations,
                    policy_a=guard_label,
                    policy_b=point_label,
                    role=str(cell.role),
                    lgd=float(cell.lgd),
                )
                guard_cash = evaluated.loc[
                    evaluated["seed"].eq(cell.seed)
                    & evaluated["purpose_cap"].eq(cell.purpose_cap)
                    & evaluated["lgd"].eq(cell.lgd)
                    & evaluated["role"].eq(cell.role)
                    & evaluated["policy_label"].eq(guard_label),
                    "undiscounted_snapshot_cash_yield",
                ]
                point_cash = evaluated.loc[
                    evaluated["seed"].eq(cell.seed)
                    & evaluated["purpose_cap"].eq(cell.purpose_cap)
                    & evaluated["lgd"].eq(cell.lgd)
                    & evaluated["role"].eq(cell.role)
                    & evaluated["policy_label"].eq(point_label),
                    "undiscounted_snapshot_cash_yield",
                ]
                if guard_cash.empty or point_cash.empty:
                    raise RuntimeError("Cash-yield contrast inputs are incomplete.")
                rows.append(
                    {
                        "seed": int(cell.seed),
                        "purpose_cap": float(cell.purpose_cap),
                        "lgd": float(cell.lgd),
                        "role": str(cell.role),
                        "paired_policy_id": policy_id,
                        "comparator_rule": comparator_rule,
                        **bounds,
                        "undiscounted_snapshot_cash_yield_difference": float(
                            guard_cash.mean() - point_cash.mean()
                        ),
                    }
                )
            ablation_label = f"ablation_group_penalty_{policy_id}"
            ablation_point_label = f"ablation_group_c2_point_{policy_id}"
            if bool(role_allocations["policy_label"].eq(ablation_label).any()):
                bounds = sharp_policy_contrast_bounds(
                    role_allocations,
                    policy_a=ablation_label,
                    policy_b=ablation_point_label,
                    role=str(cell.role),
                    lgd=float(cell.lgd),
                )
                ablation_cash = evaluated.loc[
                    evaluated["seed"].eq(cell.seed)
                    & evaluated["purpose_cap"].eq(cell.purpose_cap)
                    & evaluated["lgd"].eq(cell.lgd)
                    & evaluated["role"].eq(cell.role)
                    & evaluated["policy_label"].eq(ablation_label),
                    "undiscounted_snapshot_cash_yield",
                ]
                ablation_point_cash = evaluated.loc[
                    evaluated["seed"].eq(cell.seed)
                    & evaluated["purpose_cap"].eq(cell.purpose_cap)
                    & evaluated["lgd"].eq(cell.lgd)
                    & evaluated["role"].eq(cell.role)
                    & evaluated["policy_label"].eq(ablation_point_label),
                    "undiscounted_snapshot_cash_yield",
                ]
                rows.append(
                    {
                        "seed": int(cell.seed),
                        "purpose_cap": float(cell.purpose_cap),
                        "lgd": float(cell.lgd),
                        "role": str(cell.role),
                        "paired_policy_id": policy_id,
                        "comparator_rule": "ablation_group_c2",
                        **bounds,
                        "undiscounted_snapshot_cash_yield_difference": float(
                            ablation_cash.mean() - ablation_point_cash.mean()
                        ),
                    }
                )
            frontier_labels = sorted(
                role_allocations.loc[
                    role_allocations["comparator_rule"].eq("point_cap_frontier"),
                    "policy_label",
                ].unique()
            )
            for point_label in frontier_labels:
                bounds = sharp_policy_contrast_bounds(
                    role_allocations,
                    policy_a=guard_label,
                    policy_b=str(point_label),
                    role=str(cell.role),
                    lgd=float(cell.lgd),
                )
                guard_cash = evaluated.loc[
                    evaluated["seed"].eq(cell.seed)
                    & evaluated["purpose_cap"].eq(cell.purpose_cap)
                    & evaluated["lgd"].eq(cell.lgd)
                    & evaluated["role"].eq(cell.role)
                    & evaluated["policy_label"].eq(guard_label),
                    "undiscounted_snapshot_cash_yield",
                ]
                point_cash = evaluated.loc[
                    evaluated["seed"].eq(cell.seed)
                    & evaluated["purpose_cap"].eq(cell.purpose_cap)
                    & evaluated["lgd"].eq(cell.lgd)
                    & evaluated["role"].eq(cell.role)
                    & evaluated["policy_label"].eq(point_label),
                    "undiscounted_snapshot_cash_yield",
                ]
                frontier_cap = role_allocations.loc[
                    role_allocations["policy_label"].eq(point_label), "frontier_cap"
                ].iloc[0]
                rows.append(
                    {
                        "seed": int(cell.seed),
                        "purpose_cap": float(cell.purpose_cap),
                        "lgd": float(cell.lgd),
                        "role": str(cell.role),
                        "paired_policy_id": policy_id,
                        "comparator_rule": "point_cap_frontier",
                        "frontier_cap": float(frontier_cap),
                        **bounds,
                        "undiscounted_snapshot_cash_yield_difference": float(
                            guard_cash.mean() - point_cash.mean()
                        ),
                    }
                )
    return pd.DataFrame(rows)


def _canonical_envelopes(
    contrasts: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    supported_cap_lower: float,
    supported_cap_upper: float,
) -> list[dict[str, Any]]:
    canonical_seed = int(config["model"]["canonical_seed"])
    canonical_cap = float(config["policy"]["canonical_purpose_cap"])
    canonical_lgd = float(config["payoff"]["lgd"])
    canonical = contrasts.loc[
        contrasts["seed"].eq(canonical_seed)
        & contrasts["purpose_cap"].eq(canonical_cap)
        & contrasts["lgd"].eq(canonical_lgd)
        & contrasts["role"].eq(PRIMARY_ROLE)
        & ~contrasts["comparator_rule"].astype(str).str.startswith("ablation_")
    ]
    metric_columns = {
        "realized_payoff": (
            "realized_payoff_difference_lower",
            "realized_payoff_difference_upper",
        ),
        "terminal_default": (
            "weighted_default_difference_lower",
            "weighted_default_difference_upper",
        ),
        "funded_miscoverage": (
            "weighted_miscoverage_difference_lower",
            "weighted_miscoverage_difference_upper",
        ),
    }
    core_rules = {"c0_same_numeric_cap", "c1_development_fixed", "c2_contemporaneous"}
    supported = canonical.loc[
        canonical["comparator_rule"].isin({"c1_development_fixed", "c2_contemporaneous"})
        | (
            canonical["comparator_rule"].eq("point_cap_frontier")
            & canonical["frontier_cap"].between(supported_cap_lower, supported_cap_upper)
        )
    ]
    scopes = {
        "core_rules": canonical.loc[canonical["comparator_rule"].isin(core_rules)],
        "development_supported": supported,
        "broad_stress": canonical,
    }
    rows: list[dict[str, Any]] = []
    for scope, scope_frame in scopes.items():
        for policy_id, policy_frame in scope_frame.groupby("paired_policy_id", sort=True):
            for metric, (lower, upper) in metric_columns.items():
                envelope = comparator_multiverse_envelope(
                    policy_frame,
                    lower_column=lower,
                    upper_column=upper,
                )
                rows.append(
                    {
                        "scope": scope,
                        "paired_policy_id": policy_id,
                        "metric": metric,
                        **asdict(envelope),
                    }
                )
    return rows


def _persist_seed_stack(
    stack: PredictionStack,
    *,
    paths: OutputPaths,
    repo_root: Path,
) -> dict[str, Any]:
    seed_dir = paths.model_dir / f"seed_{stack.seed}"
    model_path = save_catboost_model_atomic(stack.model, seed_dir / "model.cbm")
    calibrator_path = atomic_write_pickle(seed_dir / "platt_calibrator.pkl", stack.calibrator)
    recipe_path = atomic_write_json(seed_dir / "fixed_taxonomy_recipe.json", asdict(stack.recipe))
    diagnostic_paths = {
        str(groups): relative_artifact_descriptor(
            atomic_write_json(
                seed_dir / f"fixed_taxonomy_recipe_groups_{groups}.json",
                asdict(recipe),
            ),
            repo_root=repo_root,
        )
        for groups, recipe in sorted(stack.diagnostic_recipes.items())
    }
    return {
        "model": relative_artifact_descriptor(model_path, repo_root=repo_root),
        "calibrator": relative_artifact_descriptor(calibrator_path, repo_root=repo_root),
        "recipe": relative_artifact_descriptor(recipe_path, repo_root=repo_root),
        "diagnostic_recipes": diagnostic_paths,
    }


def run_protocol(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Execute the tagged protocol and return the deterministic summary path."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_config(resolved_config)
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))
    paths = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    raw_path = resolve_repo_input(config["source"]["raw_path"], repo_root=root)
    universe, source_inventory, availability_audit = _prepare_universe(
        config,
        raw_path=raw_path,
    )
    implementation = implementation_provenance(
        config_path=resolved_config,
        repo_root=root,
        relative_paths=[
            Path("scripts/experiments/run_ijds_fixed_taxonomy_c2.py"),
            Path("src/data/outcome_observability.py"),
            Path("src/models/binary_conformal_guardrail.py"),
            Path("src/models/maturity_safe_pd.py"),
            Path("src/evaluation/maturity_safe_portfolio.py"),
            Path("src/evaluation/ijds_design_sensitivity.py"),
            Path("src/evaluation/comparator_audit.py"),
            Path("src/evaluation/comparator_transport_simulation.py"),
            Path("src/evaluation/policy_contrast_bounds.py"),
            Path("src/evaluation/standardized_credit_payoff.py"),
            Path("src/evaluation/cashflow_payoff.py"),
            Path("src/optimization/policy_evaluation.py"),
            Path("src/optimization/portfolio_model.py"),
            *[Path(value) for value in config.get("protocol_lineage_files", [])],
        ],
    )

    all_records: list[pd.DataFrame] = []
    all_allocations: list[pd.DataFrame] = []
    prediction_metrics: list[dict[str, Any]] = []
    fit_audits: list[pd.DataFrame] = []
    model_artifacts: dict[str, Any] = {}
    canonical_panel: pd.DataFrame | None = None
    canonical_diagnostic_recipes: dict[int, BinaryOutcomeConformalRecipe] = {}
    canonical_diagnostic_panels: dict[int, pd.DataFrame] = {}
    canonical_stack: PredictionStack | None = None
    canonical_seed = int(config["model"]["canonical_seed"])
    canonical_cap = float(config["policy"]["canonical_purpose_cap"])
    canonical_lgd = float(config["payoff"]["lgd"])
    resume_enabled = bool(config.get("resume_outcome_free", {}).get("enabled", False))
    upstream: UpstreamOutcomeFreeBundle | None = None
    if resume_enabled:
        upstream = _load_upstream_outcome_free_bundle(
            config,
            repo_root=root,
            expected_availability=availability_audit,
        )
        outcome_free_records = upstream.records
        outcome_free_allocations = upstream.allocations
        canonical_panel = upstream.canonical_panel
        fit_audits = [upstream.fit_audit]
        prediction_metrics = upstream.prediction_metrics
        canonical_diagnostic_recipes = upstream.diagnostic_recipes
        canonical_diagnostic_panels = upstream.diagnostic_panels
        model_artifacts = upstream.model_artifacts
        seeds_to_run: list[int] = []
        features = pd.DataFrame()
        numeric_features: list[str] = []
        categorical_features: list[str] = []
    else:
        features, numeric_features, categorical_features = _engineer_features(universe, config)
        seeds_to_run = [int(value) for value in config["model"]["sensitivity_seeds"]]

    for seed in seeds_to_run:
        stack = _fit_prediction_stack(
            universe,
            features,
            numeric_features=numeric_features,
            categorical_features=categorical_features,
            config=config,
            seed=seed,
        )
        model_artifacts[str(seed)] = _persist_seed_stack(stack, paths=paths, repo_root=root)
        prediction_metrics.append(stack.metrics)
        fit_audits.append(stack.fit_audit)
        if seed == canonical_seed:
            canonical_stack = stack
            canonical_panel = stack.decision_panel.copy()
            canonical_diagnostic_recipes = dict(stack.diagnostic_recipes)
            canonical_diagnostic_panels = {
                groups: panel.copy() for groups, panel in stack.diagnostic_panels.items()
            }
            development_bundle = _solve_guardrail_family(
                stack.decision_panel,
                config=config,
                role="policy_development",
                seed=seed,
                purpose_cap=canonical_cap,
                lgd=canonical_lgd,
                include_multiverse=False,
            )
            development_targets = _development_fixed_targets(development_bundle.allocations)
            all_records.append(development_bundle.records)
            all_allocations.append(development_bundle.allocations)
        else:
            development_targets = None
        for purpose_cap in [float(value) for value in config["policy"]["purpose_cap_sensitivity"]]:
            include_multiverse = seed == canonical_seed and purpose_cap == canonical_cap
            primary_bundle = _solve_guardrail_family(
                stack.decision_panel,
                config=config,
                role=PRIMARY_ROLE,
                seed=seed,
                purpose_cap=purpose_cap,
                lgd=canonical_lgd,
                include_multiverse=include_multiverse,
            )
            all_records.append(primary_bundle.records)
            all_allocations.append(primary_bundle.allocations)
            if include_multiverse:
                if development_targets is None:
                    raise RuntimeError("Canonical development targets were not constructed.")
                fixed_bundle = _solve_development_fixed_comparators(
                    stack.decision_panel,
                    targets=development_targets,
                    config=config,
                    seed=seed,
                    purpose_cap=purpose_cap,
                    lgd=canonical_lgd,
                    role=PRIMARY_ROLE,
                )
                all_records.append(fixed_bundle.records)
                all_allocations.append(fixed_bundle.allocations)
        if seed == canonical_seed:
            for lgd in [float(value) for value in config["payoff"]["reoptimization_lgd_grid"]]:
                if np.isclose(lgd, canonical_lgd):
                    continue
                bundle = _solve_guardrail_family(
                    stack.decision_panel,
                    config=config,
                    role=PRIMARY_ROLE,
                    seed=seed,
                    purpose_cap=canonical_cap,
                    lgd=lgd,
                    include_multiverse=False,
                )
                all_records.append(bundle.records)
                all_allocations.append(bundle.allocations)
            frontier = _solve_point_frontier(
                stack.decision_panel,
                config=config,
                seed=seed,
                purpose_cap=canonical_cap,
            )
            all_records.append(frontier.records)
            all_allocations.append(frontier.allocations)
            ablations = _solve_score_ablations(
                stack.decision_panel,
                recipe=stack.recipe,
                fit_audit=stack.fit_audit,
                config=config,
                seed=seed,
                purpose_cap=canonical_cap,
                lgd=canonical_lgd,
            )
            all_records.append(ablations.records)
            all_allocations.append(ablations.allocations)
            extension = _solve_guardrail_family(
                stack.decision_panel,
                config=config,
                role="censored_extension",
                seed=seed,
                purpose_cap=canonical_cap,
                lgd=canonical_lgd,
                include_multiverse=False,
            )
            all_records.append(extension.records)
            all_allocations.append(extension.allocations)

    if canonical_panel is None:
        raise RuntimeError("Canonical seed was not executed.")
    if upstream is None:
        outcome_free_records = pd.concat(all_records, ignore_index=True)
        outcome_free_allocations = pd.concat(all_allocations, ignore_index=True)
    if bool(
        outcome_free_allocations.columns.astype(str)
        .str.casefold()
        .isin(["loan_status", "snapshot_default", "terminal_default", "total_pymnt"])
        .any()
    ):
        raise AssertionError("Outcome-free allocation artifact contains an outcome field.")
    if upstream is None:
        records_path = atomic_write_parquet(
            outcome_free_records,
            paths.data_dir / "portfolio/outcome_free_solve_records.parquet",
        )
        allocations_path = atomic_write_parquet(
            outcome_free_allocations,
            paths.data_dir / "portfolio/outcome_free_funded_allocations.parquet",
        )
        panel_path = atomic_write_parquet(
            canonical_panel,
            paths.data_dir / "prediction/canonical_decision_panel.parquet",
        )
        fit_path = atomic_write_parquet(
            pd.concat(fit_audits, ignore_index=True),
            paths.data_dir / "prediction/conformal_fit_audit.parquet",
        )
        availability_path = atomic_write_parquet(
            availability_audit,
            paths.data_dir / "data/label_availability_audit.parquet",
        )
        outcome_free_artifacts = {
            "records": relative_artifact_descriptor(records_path, repo_root=root),
            "allocations": relative_artifact_descriptor(allocations_path, repo_root=root),
            "canonical_decision_panel": relative_artifact_descriptor(
                panel_path,
                repo_root=root,
            ),
            "conformal_fit_audit": relative_artifact_descriptor(fit_path, repo_root=root),
            "label_availability_audit": relative_artifact_descriptor(
                availability_path,
                repo_root=root,
            ),
        }
        freeze_status = "outcome_free_allocations_frozen_before_outcome_join"
        upstream_provenance = None
    else:
        outcome_free_artifacts = upstream.artifact_descriptors
        freeze_status = "verified_upstream_outcome_free_freeze_imported_before_outcome_join"
        upstream_provenance = upstream.provenance
    freeze: dict[str, Any] = {
        "schema_version": str(config["schema_version"]),
        "status": freeze_status,
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "outcome_free_lineage": (
            upstream.provenance
            if upstream is not None
            else {
                "source_run_tag": str(config["run_tag"]),
                "source_protocol_tag": str(config["protocol_tag"]),
                "source_protocol_commit": protocol_commit,
                "reuse_scope": "generated_in_current_run",
            }
        ),
        "run_tag": str(config["run_tag"]),
        "policy_selection": "none_all_nine_co_primary",
        "outcome_columns_passed_to_policy_or_comparator": [],
        "implementation_provenance": implementation,
        "environment": environment_provenance(root),
        "outcome_free_artifacts": outcome_free_artifacts,
        "model_artifacts": model_artifacts,
        "upstream_outcome_free_provenance": upstream_provenance,
    }
    freeze_path = atomic_write_json(paths.model_dir / "protocol_freeze.json", freeze)

    outcomes = _outcome_panel(universe)
    temporal_prediction = _temporal_prediction_metrics(canonical_panel, outcomes)
    evaluated, joined_allocations = _evaluate_allocations(
        outcome_free_records,
        outcome_free_allocations,
        outcomes,
        config=config,
    )
    aggregates = _aggregate_monthly(evaluated)
    contrasts = _paired_contrasts(joined_allocations, evaluated, config=config)

    temporal_outcomes = outcomes.loc[outcomes["id"].isin(canonical_panel["id"])]
    coverage_frames: list[pd.DataFrame] = []
    for groups, diagnostic_panel in sorted(canonical_diagnostic_panels.items()):
        coverage = build_temporal_conformal_audit(
            diagnostic_panel,
            temporal_outcomes,
            canonical_diagnostic_recipes[groups],
        )
        coverage.insert(0, "taxonomy_groups", int(groups))
        coverage_frames.append(coverage)
    temporal_coverage = pd.concat(coverage_frames, ignore_index=True)
    lag_sensitivity_path: Path | None = None
    sensitivity_config = config.get("design_sensitivity", {})
    if sensitivity_config:
        if canonical_stack is None or features.empty:
            raise RuntimeError("Design sensitivity requires a freshly fitted canonical stack.")
        lag_sensitivity = build_label_lag_coverage_sensitivity(
            universe=universe,
            features=features,
            model=canonical_stack.model,
            calibrator=canonical_stack.calibrator,
            fixed_edges=canonical_stack.recipe.bin_edges,
            decision_panel=canonical_panel,
            outcomes=outcomes,
            config=config,
            lag_months=sensitivity_config["charged_off_lag_months"],
        )
        lag_sensitivity_path = atomic_write_parquet(
            lag_sensitivity,
            paths.data_dir / "evaluation/label_lag_coverage_sensitivity.parquet",
        )
    simulation_results, simulation_summary = simulate_from_config(config)
    evaluated_path = atomic_write_parquet(
        evaluated,
        paths.data_dir / "evaluation/monthly_evaluation.parquet",
    )
    joined_path = atomic_write_parquet(
        joined_allocations,
        paths.data_dir / "evaluation/funded_allocations_with_outcomes.parquet",
    )
    aggregate_path = atomic_write_parquet(
        aggregates,
        paths.data_dir / "evaluation/aggregate_evaluation.parquet",
    )
    contrast_path = atomic_write_parquet(
        contrasts,
        paths.data_dir / "evaluation/paired_sharp_contrasts.parquet",
    )
    coverage_path = atomic_write_parquet(
        temporal_coverage,
        paths.data_dir / "evaluation/temporal_candidate_coverage.parquet",
    )
    simulation_results_path = atomic_write_parquet(
        simulation_results,
        paths.data_dir / "simulation/comparator_transport_repetitions.parquet",
    )
    simulation_summary_path = atomic_write_parquet(
        simulation_summary,
        paths.data_dir / "simulation/comparator_transport_summary.parquet",
    )

    canonical_contrasts = contrasts.loc[
        contrasts["seed"].eq(canonical_seed)
        & contrasts["purpose_cap"].eq(canonical_cap)
        & contrasts["lgd"].eq(canonical_lgd)
        & contrasts["role"].eq(PRIMARY_ROLE)
        & contrasts["comparator_rule"].eq("c2_contemporaneous")
    ]
    direction_counts = {
        "payoff_worse": int((canonical_contrasts["realized_payoff_difference_upper"] < 0.0).sum()),
        "default_higher": int(
            (canonical_contrasts["weighted_default_difference_lower"] > 0.0).sum()
        ),
        "miscoverage_higher": int(
            (canonical_contrasts["weighted_miscoverage_difference_lower"] > 0.0).sum()
        ),
        "policies": int(len(canonical_contrasts)),
    }
    development_allocations = outcome_free_allocations.loc[
        outcome_free_allocations["seed"].eq(canonical_seed)
        & outcome_free_allocations["purpose_cap"].eq(canonical_cap)
        & outcome_free_allocations["lgd"].eq(canonical_lgd)
        & outcome_free_allocations["role"].eq("policy_development")
        & outcome_free_allocations["comparator_rule"].eq("guardrail")
    ]
    development_targets = _development_fixed_targets(development_allocations)
    broad_frontier = config["comparators"]["point_cap_frontier"]
    supported_range = development_supported_cap_range(
        list(development_targets.values()),
        step=float(broad_frontier["step"]),
        lower_limit=float(broad_frontier["start"]),
        upper_limit=float(broad_frontier["stop"]),
    )
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_retrospective_prefreeze_audit",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "outcome_free_lineage": freeze["outcome_free_lineage"],
        "claim_boundary": {
            "previously_inspected_archive": True,
            "confirmatory": False,
            "prospective": False,
            "causal": False,
            "selected_set_validity": False,
            "all_nine_policies_primary": True,
        },
        "source_inventory": source_inventory,
        "label_availability": availability_audit.to_dict(orient="records"),
        "prediction": prediction_metrics,
        "canonical_temporal_prediction": temporal_prediction,
        "simulation": {
            "scope": "synthetic_mechanism_interpretation_only",
            "lending_club_validation": False,
            "repetitions": int(config["simulation"]["repetitions"]),
            "temporal_shift_grid": [
                float(value) for value in config["simulation"]["temporal_shift_grid"]
            ],
        },
        "canonical_c2_direction_counts": direction_counts,
        "development_supported_point_cap_range": asdict(supported_range),
        "canonical_comparator_envelopes": _canonical_envelopes(
            contrasts,
            config,
            supported_cap_lower=supported_range.lower,
            supported_cap_upper=supported_range.upper,
        ),
        "artifacts": {
            "protocol_freeze": relative_artifact_descriptor(freeze_path, repo_root=root),
            "monthly_evaluation": relative_artifact_descriptor(evaluated_path, repo_root=root),
            "funded_allocations_with_outcomes": relative_artifact_descriptor(
                joined_path,
                repo_root=root,
            ),
            "aggregate_evaluation": relative_artifact_descriptor(aggregate_path, repo_root=root),
            "paired_sharp_contrasts": relative_artifact_descriptor(contrast_path, repo_root=root),
            "temporal_candidate_coverage": relative_artifact_descriptor(
                coverage_path,
                repo_root=root,
            ),
            "comparator_transport_simulation": relative_artifact_descriptor(
                simulation_results_path,
                repo_root=root,
            ),
            "comparator_transport_simulation_summary": relative_artifact_descriptor(
                simulation_summary_path,
                repo_root=root,
            ),
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    if lag_sensitivity_path is not None:
        summary["artifacts"]["label_lag_coverage_sensitivity"] = relative_artifact_descriptor(
            lag_sensitivity_path, repo_root=root
        )
    summary_path = atomic_write_json(
        paths.model_dir / str(config["output"]["deterministic_summary"]),
        summary,
    )
    receipt = {
        "summary": relative_artifact_descriptor(summary_path, repo_root=root),
        "environment": environment_provenance(root),
        "protocol_commit": protocol_commit,
        "outcome_free_lineage": summary["outcome_free_lineage"],
    }
    atomic_write_json(paths.model_dir / str(config["output"]["execution_receipt"]), receipt)
    return summary_path


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    path = run_protocol(config_path=args.config, repo_root=args.repo_root)
    print(path)


if __name__ == "__main__":
    main()
