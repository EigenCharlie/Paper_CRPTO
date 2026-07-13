"""Shared prediction stack and complete residual-window construction."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.data.outcome_observability import (
    audit_outcome_label_availability,
    build_outcome_label_availability,
    load_design_universe,
    temporal_tail_split,
    terminal_outcome_from_status,
    validate_minimum_label_retention,
)
from src.evaluation.maturity_safe_portfolio import build_decision_panel
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

LABEL_FIT_SPLITS = ("pd_development", "probability_calibration", "conformal_fit")
DECISION_SPLITS = ("policy_development", "primary_oot", "censored_extension")


class ProtocolFeasibilityError(RuntimeError):
    """A locked scientific requirement failed without authorizing adaptation."""

    def __init__(self, message: str, *, details: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.protocol_details = dict(details)


@dataclass(frozen=True)
class PreparedData:
    """One status-independent universe and its model matrix."""

    universe: pd.DataFrame
    features: pd.DataFrame
    numeric_features: tuple[str, ...]
    categorical_features: tuple[str, ...]
    source_inventory: dict[str, Any]
    availability_audit: pd.DataFrame
    monthly_residual_availability: pd.DataFrame


@dataclass(frozen=True)
class LearnerScores:
    """Outcome-free scores and a learner-specific fixed 2011 taxonomy."""

    name: str
    model: Any
    calibrator: LogisticRegression
    probabilities: np.ndarray
    taxonomy_edges: dict[int, tuple[float, ...]]
    metrics: dict[str, Any]


@dataclass(frozen=True)
class WindowRecipe:
    """One residual window and all closed taxonomy diagnostics."""

    window_id: str
    start: pd.Timestamp
    end: pd.Timestamp
    recipes: dict[int, BinaryOutcomeConformalRecipe]
    fit_audit: pd.DataFrame


def _available_labels(frame: pd.DataFrame, *, block: str) -> np.ndarray:
    if not bool(frame["label_available"].all()):
        raise RuntimeError(f"{block} contains unavailable labels.")
    labels = frame["terminal_default"]
    if bool(labels.isna().any()):
        raise RuntimeError(f"{block} contains unresolved terminal outcomes.")
    values = labels.astype(int).to_numpy(dtype=int)
    if set(np.unique(values)) != {0, 1}:
        raise RuntimeError(f"{block} must contain both outcome classes.")
    return values


def _engineer_features(
    universe: pd.DataFrame, config: Mapping[str, Any]
) -> tuple[pd.DataFrame, tuple[str, ...], tuple[str, ...]]:
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
    return output, tuple(numeric), tuple(categorical)


def _monthly_availability(universe: pd.DataFrame, config: Mapping[str, Any]) -> pd.DataFrame:
    conformal = universe.loc[universe["design_split"].eq("conformal_fit")].copy()
    conformal["issue_month"] = conformal["issue_d"].dt.to_period("M").astype(str)
    audit = audit_outcome_label_availability(
        conformal,
        cutoff=str(config["source"]["information_cutoff"]),
        charged_off_lag_months=int(config["source"]["charged_off_reporting_lag_months"]),
        block_column="issue_month",
    )
    validate_minimum_label_retention(
        audit,
        minimum_retention=float(
            config["residual_specification"]["minimum_monthly_label_retention"]
        ),
        block_column="issue_month",
    )
    return audit


def prepare_data(config: Mapping[str, Any], *, raw_path: Path) -> PreparedData:
    """Load the status-independent archive and prepare all fixed features."""
    universe, source_inventory = load_design_universe(
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
    availability = audit_outcome_label_availability(
        universe.loc[universe["design_split"].isin(LABEL_FIT_SPLITS)],
        cutoff=str(config["source"]["information_cutoff"]),
        charged_off_lag_months=int(config["source"]["charged_off_reporting_lag_months"]),
    )
    validate_minimum_label_retention(
        availability,
        minimum_retention=float(config["source"]["minimum_label_retention"]),
    )
    monthly = _monthly_availability(universe, config)
    features, numeric, categorical = _engineer_features(universe, config)
    return PreparedData(
        universe=universe,
        features=features,
        numeric_features=numeric,
        categorical_features=categorical,
        source_inventory=source_inventory,
        availability_audit=availability,
        monthly_residual_availability=monthly,
    )


def _taxonomy_edges(
    probabilities: np.ndarray, groups: Sequence[int]
) -> dict[int, tuple[float, ...]]:
    output: dict[int, tuple[float, ...]] = {}
    for group_count in groups:
        edges = np.quantile(
            probabilities,
            np.linspace(0.0, 1.0, int(group_count) + 1),
            method="linear",
        )
        if bool(np.any(np.diff(edges) <= 0.0)):
            raise RuntimeError(f"The fixed {group_count}-group taxonomy has repeated edges.")
        output[int(group_count)] = tuple(float(value) for value in edges)
    return output


def _calibration_metrics(labels: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    metrics = classification_metrics(labels, probabilities)
    bins = pd.cut(probabilities, bins=np.linspace(0.0, 1.0, 11), include_lowest=True)
    grouped = (
        pd.DataFrame({"p": probabilities, "y": labels, "bin": bins})
        .groupby("bin", observed=True)
        .agg(p=("p", "mean"), y=("y", "mean"), n=("y", "size"))
    )
    metrics["ece_10"] = float(
        np.sum(grouped["n"].to_numpy() * np.abs(grouped["p"] - grouped["y"])) / len(labels)
    )
    return metrics


def fit_primary_scores(data: PreparedData, config: Mapping[str, Any]) -> LearnerScores:
    """Fit the inherited CatBoost/Platt stack once and score the full universe."""
    universe = data.universe
    development = universe.loc[
        universe["design_split"].eq("pd_development") & universe["label_available"]
    ]
    train, validation, validation_cutoff = temporal_tail_split(
        development,
        tail_fraction=float(config["design"]["validation_tail_fraction"]),
    )
    parameters = dict(config["model"]["fixed_params"])
    parameters.update(
        random_seed=int(config["model"]["canonical_seed"]),
        thread_count=int(config["execution"]["threads"]),
    )
    model = CatBoostClassifier(**parameters)
    model.fit(
        data.features.loc[train.index],
        _available_labels(train, block="pd_development_train"),
        cat_features=list(data.categorical_features),
    )
    validation_labels = _available_labels(validation, block="pd_development_validation")
    validation_probability = np.asarray(
        model.predict_proba(data.features.loc[validation.index])[:, 1], dtype=float
    )
    calibration_all = universe.loc[universe["design_split"].eq("probability_calibration")]
    calibration_fit = calibration_all.loc[calibration_all["label_available"]]
    calibration_margin = catboost_raw_margin(model, data.features.loc[calibration_fit.index])
    calibrator_config = copy.deepcopy(config["probability_calibration"])
    calibrator_config["logistic_regression"]["random_state"] = int(
        config["model"]["canonical_seed"]
    )
    calibrator = fit_platt_calibrator(
        calibration_margin,
        _available_labels(calibration_fit, block="probability_calibration"),
        calibrator_config,
    )
    all_probability = apply_platt_calibrator(
        calibrator,
        catboost_raw_margin(model, data.features),
    )
    calibration_probability = all_probability[calibration_all.index]
    groups = [int(value) for value in config["conformal"]["diagnostic_group_counts"]]
    return LearnerScores(
        name="catboost_platt",
        model=model,
        calibrator=calibrator,
        probabilities=all_probability,
        taxonomy_edges=_taxonomy_edges(calibration_probability, groups),
        metrics={
            "validation_cutoff": str(validation_cutoff.to_period("M")),
            "validation": _calibration_metrics(validation_labels, validation_probability),
            "probability_calibration": _calibration_metrics(
                _available_labels(calibration_fit, block="probability_calibration"),
                all_probability[calibration_fit.index],
            ),
        },
    )


def fit_logistic_control(data: PreparedData, config: Mapping[str, Any]) -> LearnerScores:
    """Fit the independently calibrated numeric logistic coverage control."""
    universe = data.universe
    development = universe.loc[
        universe["design_split"].eq("pd_development") & universe["label_available"]
    ]
    train, validation, validation_cutoff = temporal_tail_split(
        development,
        tail_fraction=float(config["design"]["validation_tail_fraction"]),
    )
    control = config["learner_control"]["logistic_regression"]
    numeric = list(data.numeric_features)
    pipeline = Pipeline(
        [
            (
                "preprocess",
                ColumnTransformer(
                    [
                        (
                            "numeric",
                            Pipeline(
                                [
                                    ("imputer", SimpleImputer(strategy="median")),
                                    ("scaler", StandardScaler()),
                                ]
                            ),
                            numeric,
                        )
                    ],
                    remainder="drop",
                ),
            ),
            (
                "model",
                LogisticRegression(
                    C=float(control["C"]),
                    class_weight=str(control["class_weight"]),
                    solver=str(control["solver"]),
                    max_iter=int(control["max_iter"]),
                    random_state=int(control["random_state"]),
                ),
            ),
        ]
    )
    pipeline.fit(
        data.features.loc[train.index, numeric], _available_labels(train, block="logit_train")
    )
    validation_margin = np.asarray(
        pipeline.decision_function(data.features.loc[validation.index, numeric]), dtype=float
    )
    validation_probability = np.asarray(
        pipeline.predict_proba(data.features.loc[validation.index, numeric])[:, 1], dtype=float
    )
    calibration_all = universe.loc[universe["design_split"].eq("probability_calibration")]
    calibration_fit = calibration_all.loc[calibration_all["label_available"]]
    calibration_margin = np.asarray(
        pipeline.decision_function(data.features.loc[calibration_fit.index, numeric]), dtype=float
    )
    calibrator_config = copy.deepcopy(config["probability_calibration"])
    calibrator_config["logistic_regression"]["random_state"] = int(control["random_state"])
    calibrator = fit_platt_calibrator(
        calibration_margin,
        _available_labels(calibration_fit, block="logit_probability_calibration"),
        calibrator_config,
    )
    all_margin = np.asarray(pipeline.decision_function(data.features[numeric]), dtype=float)
    all_probability = apply_platt_calibrator(calibrator, all_margin)
    calibration_probability = all_probability[calibration_all.index]
    groups = [int(value) for value in config["conformal"]["diagnostic_group_counts"]]
    return LearnerScores(
        name="numeric_logistic_platt",
        model=pipeline,
        calibrator=calibrator,
        probabilities=all_probability,
        taxonomy_edges=_taxonomy_edges(calibration_probability, groups),
        metrics={
            "validation_cutoff": str(validation_cutoff.to_period("M")),
            "validation_uncalibrated": _calibration_metrics(
                _available_labels(validation, block="logit_validation"),
                validation_probability,
            ),
            "validation_margin_mean": float(np.mean(validation_margin)),
            "probability_calibration": _calibration_metrics(
                _available_labels(calibration_fit, block="logit_probability_calibration"),
                all_probability[calibration_fit.index],
            ),
        },
    )


def fit_window_recipes(
    data: PreparedData,
    scores: LearnerScores,
    config: Mapping[str, Any],
) -> dict[str, WindowRecipe]:
    """Fit every declared residual window under every closed taxonomy size."""
    universe = data.universe
    output: dict[str, WindowRecipe] = {}
    group_counts = [int(value) for value in config["conformal"]["diagnostic_group_counts"]]
    alpha = float(config["conformal"]["alpha"])
    calibration_start = pd.Timestamp(config["design"]["probability_calibration_start"])
    calibration_end = pd.Timestamp(config["design"]["probability_calibration_end"])
    taxonomy_provenance = (
        f"{scores.name}_{calibration_start:%Y%m}_{calibration_end:%Y%m}"
        "_all_status_independent_scores"
    )
    for specification in config["residual_specification"]["windows"]:
        identifier = str(specification["id"])
        start = pd.Timestamp(specification["start"])
        end = pd.Timestamp(specification["end"])
        if pd.isna(start) or pd.isna(end):
            raise ValueError(f"Residual window {identifier} has an invalid boundary.")
        start = cast(pd.Timestamp, start)
        end = cast(pd.Timestamp, end)
        mask = (
            universe["design_split"].eq("conformal_fit")
            & universe["issue_d"].between(start, end)
            & universe["label_available"]
        )
        frame = universe.loc[mask]
        labels = _available_labels(frame, block=f"{scores.name}_{identifier}")
        probability = scores.probabilities[frame.index]
        recipes: dict[int, BinaryOutcomeConformalRecipe] = {}
        fit_rows: list[pd.DataFrame] = []
        for groups in group_counts:
            recipe = fit_binary_outcome_recipe(
                probability,
                labels,
                alpha=alpha,
                n_groups=groups,
                bin_edges=scores.taxonomy_edges[groups],
                taxonomy_provenance=taxonomy_provenance,
                taxonomy_method="fixed_empirical_linear_score_quantiles",
                method="fixed_taxonomy_split_mondrian_absolute_residual",
            )
            minimum = int(config["conformal"]["minimum_rows_per_group"])
            if (
                groups == int(config["conformal"]["canonical_groups"])
                and min(recipe.group_counts) < minimum
            ):
                counts = tuple(int(value) for value in recipe.group_counts)
                raise ProtocolFeasibilityError(
                    f"{identifier} has canonical residual group counts {counts}; "
                    f"the locked minimum is {minimum}.",
                    details={
                        "stage": "canonical_residual_group_size",
                        "learner": scores.name,
                        "window_id": identifier,
                        "taxonomy_groups": groups,
                        "group_counts": list(counts),
                        "minimum_rows_per_group": minimum,
                    },
                )
            assigned, lower, upper = apply_binary_outcome_recipe(probability, recipe)
            recipes[groups] = recipe
            fit_rows.append(
                pd.DataFrame(
                    {
                        "id": frame["id"].astype("string").to_numpy(),
                        "issue_d": frame["issue_d"].to_numpy(),
                        "learner": scores.name,
                        "window_id": identifier,
                        "taxonomy_groups": groups,
                        "conformal_group": assigned,
                        "pd_point": probability,
                        "conformal_lower": lower,
                        "conformal_upper": upper,
                        "terminal_default": labels,
                        "covered": (labels >= lower) & (labels <= upper),
                    }
                )
            )
        output[identifier] = WindowRecipe(
            window_id=identifier,
            start=start,
            end=end,
            recipes=recipes,
            fit_audit=pd.concat(fit_rows, ignore_index=True),
        )
    return output


def decision_panel_for_window(
    data: PreparedData,
    scores: LearnerScores,
    window: WindowRecipe,
    *,
    groups: int = 5,
) -> pd.DataFrame:
    """Build one outcome-free panel for a frozen learner/window recipe."""
    universe = data.universe
    source = universe.loc[universe["design_split"].isin(DECISION_SPLITS)]
    probability = scores.probabilities[source.index]
    assigned, lower, upper = apply_binary_outcome_recipe(probability, window.recipes[int(groups)])
    panel = build_decision_panel(
        source,
        pd_point=probability,
        conformal_lower=lower,
        conformal_upper=upper,
        conformal_groups=assigned,
    )
    panel["design_split"] = source["design_split"].astype(str).to_numpy()
    panel["learner"] = scores.name
    panel["window_id"] = window.window_id
    panel["taxonomy_groups"] = int(groups)
    return panel
