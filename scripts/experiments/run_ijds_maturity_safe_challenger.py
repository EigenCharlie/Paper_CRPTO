"""Run the locked maturity-safe IJDS experiment.

The protocol uses status-independent candidate menus, mature 2012 blocks for
all fitting and policy selection, monthly 2016-2017 decisions, coherent payoff,
and a post-selection audit of how marginal binary-outcome conformal coverage
changes under exposure weighting and optimization.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml
from catboost import CatBoostClassifier
from loguru import logger
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.outcome_observability import (  # noqa: E402
    DECISION_SPLITS,
    assign_design_split,
    load_design_universe,
    maturity_gap_months,
    normalize_loan_status,
    snapshot_default_from_status,
    snapshot_resolution_from_status,
    temporal_tail_split,
    validate_maturity_contract,
)
from src.evaluation.coverage_transport import (  # noqa: E402
    binary_miscoverage_bounds,
    build_temporal_conformal_audit,
    coverage_and_default_transport_bounds,
)
from src.evaluation.maturity_safe_portfolio import (  # noqa: E402
    aggregate_monthly_evaluation,
    assert_outcome_free_decision_frame,
    build_decision_panel,
    build_outcome_panel,
    evaluation_record_and_allocations,
    select_policy_on_development,
    solve_coherent_policy,
)
from src.evaluation.policy_contrast_bounds import sharp_policy_contrast_bounds  # noqa: E402
from src.evaluation.standardized_credit_payoff import (  # noqa: E402
    PAYOFF_ID,
    expected_standardized_payoff_rate,
    realized_standardized_payoff_bounds,
)
from src.models.binary_conformal_guardrail import (  # noqa: E402
    BinaryOutcomeConformalRecipe,
    apply_binary_outcome_recipe,
    assign_conformal_groups,
    fit_binary_outcome_recipe,
)
from src.models.maturity_safe_pd import (  # noqa: E402
    apply_platt_calibrator,
    catboost_raw_margin,
    classification_metrics,
    engineer_model_matrix,
    fit_platt_calibrator,
    require_binary_labels,
    validate_model_feature_contract,
)
from src.optimization.policy_selection import (  # noqa: E402
    LinearPolicyCandidate,
    build_linear_policy_grid,
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
    save_catboost_model_atomic,
    write_csv_atomic,
)
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    atomic_write_pickle,
    utc_now_iso,
)

DEFAULT_CONFIG_PATH = (
    ROOT / "configs" / "experiments" / "ijds_maturity_safe_locked_bounded_h1h2_2026-07-10.yaml"
)
ALLOWED_DATA_ROOT = Path("data/processed/experiments/champion_reopen")
ALLOWED_MODEL_ROOT = Path("models/experiments/champion_reopen")
IMPLEMENTATION_PATHS = (
    Path("scripts/experiments/run_ijds_maturity_safe_challenger.py"),
    Path("src/data/outcome_observability.py"),
    Path("src/evaluation/coverage_transport.py"),
    Path("src/evaluation/maturity_safe_portfolio.py"),
    Path("src/evaluation/policy_contrast_bounds.py"),
    Path("src/evaluation/standardized_credit_payoff.py"),
    Path("src/models/binary_conformal_guardrail.py"),
    Path("src/models/maturity_safe_pd.py"),
    Path("src/features/feature_engineering.py"),
    Path("src/optimization/policy.py"),
    Path("src/optimization/policy_evaluation.py"),
    Path("src/optimization/policy_selection.py"),
    Path("src/optimization/portfolio_model.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("tests/test_experiments/test_ijds_maturity_safe_challenger.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)

__all__ = [
    "ALLOWED_DATA_ROOT",
    "ALLOWED_MODEL_ROOT",
    "DEFAULT_CONFIG_PATH",
    "MondrianRecipe",
    "aggregate_monthly_evaluation",
    "apply_mondrian_recipe",
    "assert_outcome_free_decision_frame",
    "assign_design_split",
    "assign_mondrian_groups",
    "build_temporal_conformal_audit",
    "expected_standardized_payoff_rate",
    "fit_exact_mondrian_recipe",
    "load_config",
    "maturity_gap_months",
    "miscoverage_bounds",
    "normalize_loan_status",
    "prepare_output_paths",
    "realized_standardized_payoff_bounds",
    "run_experiment",
    "snapshot_default_from_status",
    "snapshot_resolution_from_status",
    "solve_coherent_policy",
    "temporal_tail_split",
    "validate_maturity_contract",
]

# Compatibility exports for focused tests and old audit notebooks.
MondrianRecipe = BinaryOutcomeConformalRecipe
assign_mondrian_groups = assign_conformal_groups
fit_exact_mondrian_recipe = fit_binary_outcome_recipe
apply_mondrian_recipe = apply_binary_outcome_recipe
miscoverage_bounds = binary_miscoverage_bounds


@dataclass(frozen=True)
class PredictionBundle:
    """Frozen model, calibration, conformal recipe, and fit diagnostics."""

    features: pd.DataFrame
    model: CatBoostClassifier
    calibrator: LogisticRegression
    recipe: BinaryOutcomeConformalRecipe
    numeric_features: list[str]
    categorical_features: list[str]
    model_train_rows: int
    model_validation_rows: int
    validation_cutoff: pd.Timestamp
    validation_metrics: dict[str, float | int]
    calibration_rows: int
    calibration_metrics: dict[str, Any]
    conformal_frame: pd.DataFrame
    conformal_probability: np.ndarray
    conformal_covered: np.ndarray
    conformal_fit_audit: pd.DataFrame
    conformal_group_metrics: pd.DataFrame


@dataclass(frozen=True)
class PolicyBundle:
    """Policies selected on 2012H2 and their complete development evidence."""

    selected_guardrail: LinearPolicyCandidate
    matched_point: LinearPolicyCandidate
    selected_point: LinearPolicyCandidate
    development_decision: pd.DataFrame
    development_outcomes: pd.DataFrame
    guardrail_grid: pd.DataFrame
    guardrail_monthly: pd.DataFrame
    point_grid: pd.DataFrame
    point_monthly: pd.DataFrame

    def evaluation_specs(self) -> list[tuple[LinearPolicyCandidate, bool, str]]:
        """Return the three frozen policies evaluated in every future month."""
        return [
            (self.selected_guardrail, True, "selected_conformal_guardrail"),
            (self.matched_point, False, "matched_point_pd"),
            (self.selected_point, False, "development_selected_point_pd"),
        ]


@dataclass(frozen=True)
class EvaluationBundle:
    """Future monthly results and exact primary transport diagnostics."""

    future_outcomes: pd.DataFrame
    outcome_panel: pd.DataFrame
    temporal_conformal_audit: pd.DataFrame
    evaluation: pd.DataFrame
    allocations: pd.DataFrame
    aggregate: pd.DataFrame
    primary_candidates: pd.DataFrame
    primary_with_outcomes: pd.DataFrame
    extension_candidates: pd.DataFrame
    extension_with_outcomes: pd.DataFrame
    transport_decomposition: pd.DataFrame
    group_exposure: pd.DataFrame


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the experiment CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    """Load and validate the complete locked protocol contract."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Experiment config must be a YAML mapping.")
    required = {
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
        "analysis",
        "execution",
        "output",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise ValueError(f"Experiment config is missing sections: {missing}")
    if payload["protocol_status"] != "locked_before_primary_outcome_analysis":
        raise ValueError("The experiment config is not marked as locked.")
    if str(payload["payoff"].get("id")) != PAYOFF_ID:
        raise ValueError(f"payoff.id must be {PAYOFF_ID!r}.")
    design = payload["design"]
    expected_dates = {
        "conformal_fit_start": "2012-01-01",
        "conformal_fit_end": "2012-06-30",
        "policy_development_start": "2012-07-01",
        "policy_development_end": "2012-12-31",
        "primary_oot_start_month": "2016-04",
        "primary_oot_end_month": "2017-06",
        "censored_extension_start_month": "2017-07",
        "censored_extension_end_month": "2017-09",
    }
    mismatches = {
        key: design.get(key)
        for key, expected in expected_dates.items()
        if str(design.get(key)) != expected
    }
    if mismatches:
        raise ValueError(f"Locked temporal boundaries changed: {mismatches}")
    if int(design.get("term_months", 0)) != 36:
        raise ValueError("This protocol is locked to 36-month loans.")
    if design.get("unresolved_outcome_handling") != (
        "sharp_binary_bounds_in_all_evaluation_blocks"
    ):
        raise ValueError("All evaluation blocks must retain unresolved outcomes with bounds.")
    primary_months = pd.period_range(
        str(design["primary_oot_start_month"]),
        str(design["primary_oot_end_month"]),
        freq="M",
    )
    extension_months = pd.period_range(
        str(design["censored_extension_start_month"]),
        str(design["censored_extension_end_month"]),
        freq="M",
    )
    if len(primary_months) != 15 or len(extension_months) != 3:
        raise ValueError("The locked evaluation must contain 15 primary and 3 extension months.")
    if bool(payload["conformal"].get("learned_widening", True)) or bool(
        payload["conformal"].get("learned_floor", True)
    ):
        raise ValueError("Holdout-learned conformal corrections are forbidden.")
    if payload["policy"].get("endpoint_budget_cap") is not None:
        raise ValueError("The historical endpoint cap is forbidden in the locked protocol.")
    if str(payload["output"].get("immutability")) != ("hard_no_overwrite_choose_fresh_run_tag"):
        raise ValueError("Experiment outputs must use the hard no-overwrite contract.")
    return cast(dict[str, Any], payload)


def prepare_output_paths(
    config: Mapping[str, Any],
    *,
    repo_root: Path = ROOT,
) -> OutputPaths:
    """Expose the experiment-specific containment contract."""
    return prepare_isolated_output_paths(
        dict(config),
        repo_root=repo_root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )


def _policy_candidates(config: Mapping[str, Any]) -> list[LinearPolicyCandidate]:
    candidates = build_linear_policy_grid(
        risk_tolerances=[float(value) for value in config["policy"]["risk_tolerances"]],
        gammas=[float(value) for value in config["policy"]["gammas"]],
        uncertainty_aversions=[float(value) for value in config["policy"]["uncertainty_aversions"]],
    )
    expected = (
        len(config["policy"]["risk_tolerances"])
        * len(config["policy"]["gammas"])
        * len(config["policy"]["uncertainty_aversions"])
    )
    if len(candidates) != expected:
        raise RuntimeError("Policy grid cardinality does not match its Cartesian product.")
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
        for candidate in candidates
    ]


def _point_candidate(
    tau: float, config: Mapping[str, Any], *, prefix: str
) -> LinearPolicyCandidate:
    return LinearPolicyCandidate(
        candidate_id=f"{prefix}-tau-{int(round(float(tau) * 1000)):03d}",
        risk_tolerance=float(tau),
        gamma=0.0,
        uncertainty_aversion=0.0,
        min_budget_utilization=float(config["policy"]["min_budget_utilization_solver"]),
    )


def _expected_calibration_error(
    outcomes: np.ndarray,
    probabilities: np.ndarray,
    *,
    bins: int = 10,
) -> float:
    y_true = np.asarray(outcomes, dtype=float)
    point = np.asarray(probabilities, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    memberships = np.clip(np.digitize(point, edges[1:-1], right=False), 0, bins - 1)
    result = 0.0
    for index in range(bins):
        mask = memberships == index
        if bool(mask.any()):
            result += float(mask.mean()) * abs(float(y_true[mask].mean() - point[mask].mean()))
    return result


def _prediction_metrics(outcomes: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    observed = np.isfinite(outcomes)
    if not bool(observed.any()):
        return {"rows": int(len(outcomes)), "resolved_rows": 0}
    labels = outcomes[observed].astype(int)
    point = probabilities[observed]
    return {
        **classification_metrics(labels, point),
        "resolved_rows": int(observed.sum()),
        "unresolved_rows": int((~observed).sum()),
        "ece_10": _expected_calibration_error(labels, point, bins=10),
    }


def _aggregate_evaluations(evaluation: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for role in sorted(evaluation["role"].astype(str).unique()):
        role_frame = evaluation.loc[evaluation["role"].astype(str).eq(role)]
        for label in sorted(role_frame["policy_label"].astype(str).unique()):
            record = aggregate_monthly_evaluation(
                role_frame.loc[role_frame["policy_label"].astype(str).eq(label)]
            )
            record["role"] = role
            rows.append(record)
    return pd.DataFrame(rows).sort_values(["role", "policy_label"], kind="mergesort")


def _primary_contrasts(allocations: pd.DataFrame, *, lgd: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for baseline in ("matched_point_pd", "development_selected_point_pd"):
        rows.append(
            sharp_policy_contrast_bounds(
                allocations,
                policy_a="selected_conformal_guardrail",
                policy_b=baseline,
                role="primary_oot",
                lgd=lgd,
            )
        )
    return rows


def _pooled_coverage_record(audit: pd.DataFrame, split: str) -> dict[str, Any]:
    split_rows = audit.loc[
        audit["design_split"].eq(split) & audit["conformal_group"].eq("ALL")
    ].copy()
    pooled = split_rows.loc[split_rows["period"].astype(str).str.contains("_to_")]
    if len(pooled) != 1:
        raise RuntimeError(f"Expected one pooled coverage row for {split}.")
    return cast(dict[str, Any], pooled.iloc[0].to_dict())


def _build_source_inventories(universe: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    split_inventory = (
        universe.groupby(["design_split", "snapshot_resolution"], observed=True)
        .size()
        .to_frame("rows")
        .reset_index()
        .sort_values(["design_split", "snapshot_resolution"], kind="mergesort")
    )
    status_inventory = (
        universe.assign(normalized_status=normalize_loan_status(universe["loan_status"]))
        .groupby(["design_split", "normalized_status"], observed=True)
        .size()
        .to_frame("rows")
        .reset_index()
        .sort_values(["design_split", "normalized_status"], kind="mergesort")
    )
    return split_inventory, status_inventory


def _fit_prediction_bundle(
    universe: pd.DataFrame,
    config: Mapping[str, Any],
) -> PredictionBundle:
    numeric_features, categorical_features = validate_model_feature_contract(config["model"])
    features = engineer_model_matrix(
        universe,
        numeric_features=numeric_features,
        categorical_features=categorical_features,
    )
    development = universe.loc[universe["design_split"].eq("pd_development")].copy()
    model_train, model_validation, validation_cutoff = temporal_tail_split(
        development,
        tail_fraction=float(config["design"]["validation_tail_fraction"]),
    )
    train_indices = model_train.index.to_numpy(dtype=int)
    validation_indices = model_validation.index.to_numpy(dtype=int)
    y_train = require_binary_labels(model_train, block="pd_development_train")
    y_validation = require_binary_labels(model_validation, block="pd_development_validation")
    model_params = dict(config["model"]["fixed_params"])
    model_params["thread_count"] = int(config["execution"]["threads"])
    model = CatBoostClassifier(**model_params)
    model.fit(features.loc[train_indices], y_train, cat_features=categorical_features)
    validation_probability = np.asarray(
        model.predict_proba(features.loc[validation_indices])[:, 1],
        dtype=float,
    )
    validation_metrics = classification_metrics(y_validation, validation_probability)

    calibration_frame = universe.loc[universe["design_split"].eq("probability_calibration")]
    calibration_indices = calibration_frame.index.to_numpy(dtype=int)
    y_calibration = require_binary_labels(calibration_frame, block="probability_calibration")
    calibration_margin = catboost_raw_margin(model, features.loc[calibration_indices])
    calibrator = fit_platt_calibrator(
        calibration_margin,
        y_calibration,
        config["probability_calibration"],
    )
    calibration_raw = np.asarray(
        model.predict_proba(features.loc[calibration_indices])[:, 1],
        dtype=float,
    )
    calibration_probability = apply_platt_calibrator(calibrator, calibration_margin)
    calibration_metrics = {
        "raw": _prediction_metrics(y_calibration.astype(float), calibration_raw),
        "calibrated": _prediction_metrics(y_calibration.astype(float), calibration_probability),
    }

    conformal_frame = universe.loc[universe["design_split"].eq("conformal_fit")]
    conformal_indices = conformal_frame.index.to_numpy(dtype=int)
    y_conformal = require_binary_labels(conformal_frame, block="conformal_fit")
    conformal_probability = apply_platt_calibrator(
        calibrator,
        catboost_raw_margin(model, features.loc[conformal_indices]),
    )
    recipe = fit_binary_outcome_recipe(
        conformal_probability,
        y_conformal,
        alpha=float(config["conformal"]["alpha"]),
        n_groups=int(config["conformal"]["mondrian_groups"]),
    )
    groups, lower, upper = apply_binary_outcome_recipe(conformal_probability, recipe)
    covered = (y_conformal >= lower) & (y_conformal <= upper)
    fit_audit = pd.DataFrame(
        {
            "id": conformal_frame["id"].astype("string").to_numpy(),
            "issue_d": conformal_frame["issue_d"].to_numpy(),
            "conformal_group": groups,
            "pd_point": conformal_probability,
            "conformal_lower": lower,
            "conformal_upper": upper,
            "snapshot_default": y_conformal,
            "absolute_residual": np.abs(y_conformal - conformal_probability),
            "covered": covered,
        }
    )
    group_metrics = (
        fit_audit.groupby("conformal_group", observed=True)
        .agg(rows=("id", "size"), empirical_coverage=("covered", "mean"))
        .reset_index()
    )
    return PredictionBundle(
        features=features,
        model=model,
        calibrator=calibrator,
        recipe=recipe,
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        model_train_rows=len(model_train),
        model_validation_rows=len(model_validation),
        validation_cutoff=validation_cutoff,
        validation_metrics=validation_metrics,
        calibration_rows=len(calibration_frame),
        calibration_metrics=calibration_metrics,
        conformal_frame=conformal_frame,
        conformal_probability=conformal_probability,
        conformal_covered=covered,
        conformal_fit_audit=fit_audit,
        conformal_group_metrics=group_metrics,
    )


def _build_frozen_decision_panel(
    universe: pd.DataFrame,
    prediction: PredictionBundle,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    decision_source = universe.loc[universe["design_split"].isin(DECISION_SPLITS)].copy()
    decision_indices = decision_source.index.to_numpy(dtype=int)
    probability = apply_platt_calibrator(
        prediction.calibrator,
        catboost_raw_margin(prediction.model, prediction.features.loc[decision_indices]),
    )
    groups, lower, upper = apply_binary_outcome_recipe(probability, prediction.recipe)
    panel = build_decision_panel(
        decision_source,
        pd_point=probability,
        conformal_lower=lower,
        conformal_upper=upper,
        conformal_groups=groups,
    )
    panel["design_split"] = decision_source["design_split"].astype(str).to_numpy()
    assert_outcome_free_decision_frame(panel)
    return decision_source, panel


def _select_policy_bundle(
    decision_source: pd.DataFrame,
    decision_panel: pd.DataFrame,
    config: Mapping[str, Any],
) -> PolicyBundle:
    development_decision = decision_panel.loc[
        decision_panel["design_split"].eq("policy_development")
    ].drop(columns="design_split")
    development_source = decision_source.loc[
        decision_source["design_split"].eq("policy_development")
    ]
    development_outcomes = build_outcome_panel(development_source)
    guardrail_candidates = _policy_candidates(config)
    selected_guardrail, guardrail_grid, guardrail_monthly = select_policy_on_development(
        development_decision,
        development_outcomes,
        [(candidate, True, "conformal_guardrail_grid") for candidate in guardrail_candidates],
        config=config,
    )
    point_candidates = [
        _point_candidate(float(tau), config, prefix="point")
        for tau in config["policy"]["risk_tolerances"]
    ]
    selected_point, point_grid, point_monthly = select_policy_on_development(
        development_decision,
        development_outcomes,
        [(candidate, False, "point_pd_grid") for candidate in point_candidates],
        config=config,
    )
    matched_point = _point_candidate(
        selected_guardrail.risk_tolerance,
        config,
        prefix="matched-point",
    )
    logger.info(
        "2012H2 selected guardrail {} and independent point policy {}",
        selected_guardrail.candidate_id,
        selected_point.candidate_id,
    )
    return PolicyBundle(
        selected_guardrail=selected_guardrail,
        matched_point=matched_point,
        selected_point=selected_point,
        development_decision=development_decision,
        development_outcomes=development_outcomes,
        guardrail_grid=guardrail_grid,
        guardrail_monthly=guardrail_monthly,
        point_grid=point_grid,
        point_monthly=point_monthly,
    )


def _write_protocol_freeze(
    *,
    paths: OutputPaths,
    config: Mapping[str, Any],
    config_path: Path,
    repo_root: Path,
    protocol_commit: str,
    implementation: Mapping[str, Any],
    policies: PolicyBundle,
) -> Path:
    payload = {
        "schema_version": str(config["schema_version"]),
        "protocol_status": "policy_frozen_before_primary_outcome_materialization",
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "run_tag": str(config["run_tag"]),
        "config": relative_artifact_descriptor(config_path, repo_root=repo_root),
        "implementation_provenance": dict(implementation),
        "selected_guardrail": policies.selected_guardrail.to_record(),
        "matched_point_pd": policies.matched_point.to_record(),
        "development_selected_point_pd": policies.selected_point.to_record(),
        "selection_period": "2012-07_to_2012-12",
        "selection_metric": "summed_realized_coherent_standardized_payoff",
        "future_outcome_columns_passed_to_selector": [],
        "endpoint_cap_used": False,
    }
    return atomic_write_json(paths.model_dir / "protocol_freeze.json", payload)


def _evaluate_fixed_policies(
    *,
    decision_source: pd.DataFrame,
    decision_panel: pd.DataFrame,
    policies: PolicyBundle,
    recipe: BinaryOutcomeConformalRecipe,
    config: Mapping[str, Any],
) -> EvaluationBundle:
    future_source = decision_source.loc[
        decision_source["design_split"].isin(["primary_oot", "censored_extension"])
    ]
    future_outcomes = build_outcome_panel(future_source)
    outcome_panel = pd.concat([policies.development_outcomes, future_outcomes], ignore_index=True)
    temporal_audit = build_temporal_conformal_audit(decision_panel, outcome_panel, recipe)

    evaluation_rows: list[dict[str, Any]] = []
    allocation_frames: list[pd.DataFrame] = []
    specs = policies.evaluation_specs()
    for role in ("primary_oot", "censored_extension"):
        role_decision = decision_panel.loc[decision_panel["design_split"].eq(role)].drop(
            columns="design_split"
        )
        periods = sorted(pd.to_datetime(role_decision["issue_d"]).dt.to_period("M").unique())
        for period_value in periods:
            period = str(period_value)
            month = role_decision.loc[
                pd.to_datetime(role_decision["issue_d"]).dt.to_period("M").eq(period_value)
            ].copy()
            month_outcomes = future_outcomes.loc[future_outcomes["id"].isin(month["id"])].copy()
            for candidate, robust, label in specs:
                record, funded = evaluation_record_and_allocations(
                    month,
                    month_outcomes,
                    candidate,
                    config=config,
                    robust=robust,
                    role=role,
                    period=period,
                    policy_label=label,
                )
                evaluation_rows.append(record)
                allocation_frames.append(funded)
    evaluation = pd.DataFrame(evaluation_rows)
    allocations = pd.concat(allocation_frames, ignore_index=True)
    if len(evaluation) != 54 or not bool(evaluation["full_budget"].all()):
        raise RuntimeError("The fixed monthly evaluation is incomplete or underfunded.")
    aggregate = _aggregate_evaluations(evaluation)

    primary_candidates = decision_panel.loc[decision_panel["design_split"].eq("primary_oot")].drop(
        columns="design_split"
    )
    primary_outcomes = future_outcomes.loc[future_outcomes["id"].isin(primary_candidates["id"])]
    primary_with_outcomes = primary_candidates.merge(
        primary_outcomes, on="id", how="left", validate="one_to_one"
    )
    transport_frames: list[pd.DataFrame] = []
    for _, _, label in specs:
        funded = allocations.loc[
            allocations["role"].eq("primary_oot") & allocations["policy_label"].eq(label)
        ]
        transport = coverage_and_default_transport_bounds(
            primary_with_outcomes,
            funded,
            alpha=float(config["conformal"]["alpha"]),
        )
        transport.insert(0, "policy_label", label)
        transport_frames.append(transport)
    transport_decomposition = pd.concat(transport_frames, ignore_index=True)
    group_exposure = (
        allocations.groupby(
            ["role", "policy_label", "conformal_group"], observed=True, as_index=False
        )["exposure"]
        .sum()
        .sort_values(["role", "policy_label", "conformal_group"], kind="mergesort")
    )
    group_exposure["exposure_share"] = group_exposure["exposure"] / group_exposure.groupby(
        ["role", "policy_label"], observed=True
    )["exposure"].transform("sum")
    extension_candidates = decision_panel.loc[
        decision_panel["design_split"].eq("censored_extension")
    ].drop(columns="design_split")
    extension_with_outcomes = extension_candidates.merge(
        future_outcomes, on="id", how="left", validate="one_to_one"
    )
    return EvaluationBundle(
        future_outcomes=future_outcomes,
        outcome_panel=outcome_panel,
        temporal_conformal_audit=temporal_audit,
        evaluation=evaluation,
        allocations=allocations,
        aggregate=aggregate,
        primary_candidates=primary_candidates,
        primary_with_outcomes=primary_with_outcomes,
        extension_candidates=extension_candidates,
        extension_with_outcomes=extension_with_outcomes,
        transport_decomposition=transport_decomposition,
        group_exposure=group_exposure,
    )


def _persist_run_artifacts(
    *,
    paths: OutputPaths,
    repo_root: Path,
    config: Mapping[str, Any],
    split_inventory: pd.DataFrame,
    status_inventory: pd.DataFrame,
    decision_panel: pd.DataFrame,
    prediction: PredictionBundle,
    policies: PolicyBundle,
    evaluation: EvaluationBundle,
    freeze_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    frames = {
        paths.data_dir / "data" / "split_inventory.csv": split_inventory,
        paths.data_dir / "data" / "status_inventory.csv": status_inventory,
        paths.data_dir
        / "conformal"
        / "binary_outcome_fit_audit.parquet": prediction.conformal_fit_audit,
        paths.data_dir
        / "conformal"
        / "binary_outcome_fit_group_metrics.csv": prediction.conformal_group_metrics,
        paths.data_dir
        / "conformal"
        / "temporal_all_candidate_coverage_audit.csv": evaluation.temporal_conformal_audit,
        paths.data_dir / "portfolio" / "decision_panel_outcome_free.parquet": decision_panel,
        paths.data_dir
        / "portfolio"
        / "outcomes_post_decision_boundary.parquet": evaluation.outcome_panel,
        paths.data_dir
        / "portfolio"
        / "development_guardrail_selection_grid.csv": policies.guardrail_grid,
        paths.data_dir
        / "portfolio"
        / "development_guardrail_monthly.csv": policies.guardrail_monthly,
        paths.data_dir / "portfolio" / "development_point_selection_grid.csv": policies.point_grid,
        paths.data_dir / "portfolio" / "development_point_monthly.csv": policies.point_monthly,
        paths.data_dir / "portfolio" / "fixed_policy_monthly_evaluation.csv": evaluation.evaluation,
        paths.data_dir / "portfolio" / "fixed_policy_aggregate.csv": evaluation.aggregate,
        paths.data_dir / "portfolio" / "monthly_funded_allocations.parquet": evaluation.allocations,
        paths.data_dir
        / "portfolio"
        / "selection_transport_decomposition.csv": evaluation.transport_decomposition,
        paths.data_dir / "portfolio" / "funded_group_exposure.csv": evaluation.group_exposure,
    }
    written: dict[Path, pd.DataFrame] = {}
    for path, frame in frames.items():
        written_path = (
            atomic_write_parquet(frame, path, index=False)
            if path.suffix == ".parquet"
            else write_csv_atomic(frame, path)
        )
        written[written_path] = frame
    model_path = save_catboost_model_atomic(prediction.model, paths.model_dir / "pd" / "model.cbm")
    calibrator_path = atomic_write_pickle(
        paths.model_dir / "pd" / "platt_calibrator.pkl", prediction.calibrator
    )
    recipe_path = atomic_write_json(
        paths.model_dir / "conformal" / "binary_outcome_recipe.json",
        {
            **asdict(prediction.recipe),
            "fit_start": str(config["design"]["conformal_fit_start"]),
            "fit_end": str(config["design"]["conformal_fit_end"]),
            "interpretation": (
                "Prediction interval for the observed binary outcome; not a confidence "
                "interval for latent PD and not selected-set coverage."
            ),
        },
    )
    nonframes = [freeze_path, model_path, calibrator_path, recipe_path]
    descriptors = [
        *(relative_artifact_descriptor(path, repo_root=repo_root) for path in written),
        *(relative_artifact_descriptor(path, repo_root=repo_root) for path in nonframes),
    ]
    artifacts = {descriptor["path"]: descriptor for descriptor in descriptors}
    schemas = {
        relative_artifact_descriptor(path, repo_root=repo_root)["path"]: dataframe_schema(frame)
        for path, frame in written.items()
    }
    return artifacts, schemas


def run_experiment(
    *,
    config_path: Path,
    repo_root: Path = ROOT,
) -> Path:
    """Execute the locked protocol and return the deterministic summary path."""
    started_at = utc_now_iso()
    started_counter = time.perf_counter()
    config_path = resolve_repo_input(config_path, repo_root=repo_root)
    config = load_config(config_path)
    protocol_commit = require_clean_tagged_head(repo_root, str(config["protocol_tag"]))
    initial_git = git_provenance(repo_root)
    implementation_start = implementation_provenance(
        config_path=config_path,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=repo_root,
    )
    paths = prepare_output_paths(config, repo_root=repo_root)
    logger.info("Starting locked IJDS protocol {}", config["run_tag"])

    raw_path = resolve_repo_input(str(config["source"]["raw_path"]), repo_root=repo_root)
    raw_descriptor = relative_artifact_descriptor(raw_path, repo_root=repo_root)
    universe, source_inventory = load_design_universe(config, raw_path=raw_path)
    maturity_contract = validate_maturity_contract(
        universe,
        config["design"],
        config["source"],
    )
    logger.info(
        "Loaded {:,} status-independent design rows; unresolved={:,}",
        len(universe),
        int(universe["snapshot_default"].isna().sum()),
    )

    split_inventory, status_inventory = _build_source_inventories(universe)
    prediction = _fit_prediction_bundle(universe, config)
    decision_source, decision_panel = _build_frozen_decision_panel(universe, prediction)
    policies = _select_policy_bundle(decision_source, decision_panel, config)
    freeze_path = _write_protocol_freeze(
        paths=paths,
        config=config,
        config_path=config_path,
        repo_root=repo_root,
        protocol_commit=protocol_commit,
        implementation=implementation_start,
        policies=policies,
    )
    evaluation = _evaluate_fixed_policies(
        decision_source=decision_source,
        decision_panel=decision_panel,
        policies=policies,
        recipe=prediction.recipe,
        config=config,
    )
    artifacts, schemas = _persist_run_artifacts(
        paths=paths,
        repo_root=repo_root,
        config=config,
        split_inventory=split_inventory,
        status_inventory=status_inventory,
        decision_panel=decision_panel,
        prediction=prediction,
        policies=policies,
        evaluation=evaluation,
        freeze_path=freeze_path,
    )
    implementation_end = implementation_provenance(
        config_path=config_path,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=repo_root,
    )
    if implementation_end != implementation_start:
        raise RuntimeError("Scientific implementation changed during execution.")

    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "hypothesis": str(config["hypothesis"]),
        "claim_boundary": (
            "Retrospective maturity-safe temporal decision audit. The conformal object "
            "predicts a binary outcome; marginal coverage is not a selected-set guarantee. "
            "Nullable snapshot outcomes remain in every menu and are reported with sharp "
            "bounds. Standardized payoff is neither cash-flow IRR nor causal return."
        ),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
        "config": relative_artifact_descriptor(config_path, repo_root=repo_root),
        "raw_source": raw_descriptor,
        "source_inventory": source_inventory,
        "maturity_contract": maturity_contract,
        "row_counts": {
            "universe": int(len(universe)),
            "model_train": prediction.model_train_rows,
            "model_validation": prediction.model_validation_rows,
            "probability_calibration": prediction.calibration_rows,
            "conformal_fit_2012H1": int(len(prediction.conformal_frame)),
            "policy_development_2012H2": int(len(policies.development_decision)),
            "primary_oot": int(len(evaluation.primary_candidates)),
            "censored_extension": int(len(evaluation.extension_candidates)),
            "primary_oot_months": 15,
            "censored_extension_months": 3,
        },
        "model": {
            "type": "CatBoostClassifier",
            "fixed_params_declared": dict(config["model"]["fixed_params"]),
            "fixed_params_effective": prediction.model.get_all_params(),
            "numeric_features": prediction.numeric_features,
            "categorical_features": prediction.categorical_features,
            "validation_cutoff_month": str(prediction.validation_cutoff.to_period("M")),
            "validation_metrics_raw": prediction.validation_metrics,
            "probability_calibration_metrics": prediction.calibration_metrics,
            "primary_oot_all_candidate_metrics": _prediction_metrics(
                pd.to_numeric(
                    evaluation.primary_with_outcomes["snapshot_default"], errors="raise"
                ).to_numpy(dtype=float),
                evaluation.primary_with_outcomes["pd_point"].to_numpy(dtype=float),
            ),
            "extension_resolved_candidate_metrics": _prediction_metrics(
                pd.to_numeric(
                    evaluation.extension_with_outcomes["snapshot_default"], errors="coerce"
                ).to_numpy(dtype=float),
                evaluation.extension_with_outcomes["pd_point"].to_numpy(dtype=float),
            ),
        },
        "probability_calibration": {
            "method": str(config["probability_calibration"]["method"]),
            "fit_period": "2011",
            "coefficient": prediction.calibrator.coef_.reshape(-1).tolist(),
            "intercept": prediction.calibrator.intercept_.reshape(-1).tolist(),
        },
        "conformal": {
            **asdict(prediction.recipe),
            "fit_period": "2012H1",
            "fit_empirical_coverage": float(prediction.conformal_covered.mean()),
            "fit_group_metrics": prediction.conformal_group_metrics.to_dict(orient="records"),
            "primary_oot_all_candidate_pooled": _pooled_coverage_record(
                evaluation.temporal_conformal_audit,
                "primary_oot",
            ),
            "censored_extension_all_candidate_pooled": _pooled_coverage_record(
                evaluation.temporal_conformal_audit,
                "censored_extension",
            ),
        },
        "payoff": {
            **dict(config["payoff"]),
            "solver_reconciliation": "exposure*((1-p)*r-p*LGD), checked after every solve",
        },
        "selection": {
            "period": "2012-07_to_2012-12",
            "rule": str(config["policy"]["development_selection_rule"]),
            "selected_guardrail": policies.selected_guardrail.to_record(),
            "matched_point_pd": policies.matched_point.to_record(),
            "development_selected_point_pd": policies.selected_point.to_record(),
            "guardrail_grid": policies.guardrail_grid.to_dict(orient="records"),
            "point_grid": policies.point_grid.to_dict(orient="records"),
            "endpoint_cap_used": False,
            "primary_or_extension_outcomes_used": False,
        },
        "monthly_evaluation": {
            "fresh_budget_per_policy_month": float(config["policy"]["budget"]),
            "aggregate_by_role_and_policy": evaluation.aggregate.to_dict(orient="records"),
            "primary_retrospective_contrasts": _primary_contrasts(
                evaluation.allocations,
                lgd=float(config["payoff"]["lgd"]),
            ),
            "all_evaluation_blocks_use_sharp_unresolved_bounds": True,
            "positive_claim_requires_sign_robust_primary_bounds": True,
            "causal_interpretation": False,
        },
        "selection_transport": {
            "interpretation": (
                "Funded endpoints are sharp aggregate bounds; intermediate terms are "
                "completion-specific transport identities, not confidence bounds."
            ),
            "rows": evaluation.transport_decomposition.to_dict(orient="records"),
        },
        "implementation_provenance": implementation_start,
        "artifacts": artifacts,
        "schemas": schemas,
    }
    summary_path = atomic_write_json(
        paths.model_dir / str(config["output"]["deterministic_result"]),
        summary,
    )
    receipt = {
        "run_tag": str(config["run_tag"]),
        "started_at_utc": started_at,
        "completed_at_utc": utc_now_iso(),
        "runtime_seconds": float(time.perf_counter() - started_counter),
        "initial_git": initial_git,
        "final_git": git_provenance(repo_root),
        "environment": environment_provenance(repo_root),
        "deterministic_summary": relative_artifact_descriptor(
            summary_path,
            repo_root=repo_root,
        ),
    }
    atomic_write_json(paths.model_dir / str(config["output"]["execution_receipt"]), receipt)
    logger.info("Completed locked protocol and wrote {}", summary_path)
    return summary_path


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entry point."""
    args = parse_args(argv)
    run_experiment(config_path=args.config)


if __name__ == "__main__":
    main()
