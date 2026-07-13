"""Auditable credit-risk learner controls for the V4 temporal design."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from optbinning import BinningProcess
from scipy.optimize import minimize
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_curve

from src.data.outcome_observability import temporal_tail_split
from src.ijds_audit.prediction import (
    LearnerScores,
    PreparedData,
    available_binary_labels,
    binary_probability_metrics,
    fixed_taxonomy_edges,
)
from src.models.maturity_safe_pd import (
    apply_platt_calibrator,
    catboost_raw_margin,
    fit_platt_calibrator,
)

STABILITY_ROLES = (
    "probability_calibration",
    "conformal_fit",
    "policy_development",
    "primary_oot",
    "censored_extension",
)


def credit_prediction_metrics(labels: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    """Return fixed discrimination and calibration diagnostics for credit PD."""
    y = np.asarray(labels, dtype=int)
    probability = np.clip(np.asarray(probabilities, dtype=float), 1e-8, 1.0 - 1e-8)
    if len(y) != len(probability) or set(np.unique(y)) != {0, 1}:
        raise ValueError("Credit prediction metrics require aligned binary classes.")
    metrics: dict[str, Any] = dict(binary_probability_metrics(y, probability))
    false_positive_rate, true_positive_rate, _ = roc_curve(y, probability)
    logits = np.log(probability / (1.0 - probability))

    def objective(beta: np.ndarray) -> float:
        linear = beta[0] + beta[1] * logits
        return float(np.sum(np.logaddexp(0.0, linear) - y * linear))

    def gradient(beta: np.ndarray) -> np.ndarray:
        linear = beta[0] + beta[1] * logits
        fitted = 1.0 / (1.0 + np.exp(-np.clip(linear, -40.0, 40.0)))
        residual = fitted - y
        return np.asarray([np.sum(residual), np.sum(residual * logits)], dtype=float)

    calibration = minimize(
        objective,
        x0=np.asarray([0.0, 1.0], dtype=float),
        jac=gradient,
        method="BFGS",
        options={"gtol": 1e-8, "maxiter": 2000},
    )
    if not bool(np.isfinite(calibration.x).all()):
        raise RuntimeError("Calibration intercept/slope optimization returned non-finite values.")
    metrics.update(
        {
            "gini": float(2.0 * float(metrics["roc_auc"]) - 1.0),
            "ks": float(np.max(true_positive_rate - false_positive_rate)),
            "average_precision": float(average_precision_score(y, probability)),
            "calibration_in_the_large": float(np.mean(probability) - np.mean(y)),
            "calibration_intercept": float(calibration.x[0]),
            "calibration_slope": float(calibration.x[1]),
            "calibration_optimizer_success": bool(calibration.success),
        }
    )
    return metrics


@dataclass
class WOELogisticModel:
    """Pickle-safe OptBinning transformer and regularized logistic model."""

    name: str
    features: tuple[str, ...]
    categorical_features: tuple[str, ...]
    binning_process: BinningProcess
    logistic_regression: LogisticRegression

    def transform(self, frame: pd.DataFrame, *, metric: str = "woe") -> pd.DataFrame:
        """Apply the frozen binning process with neutral missing and special values."""
        transformed = self.binning_process.transform(
            frame.loc[:, self.features],
            metric=metric,
            metric_missing=0,
            metric_special=0,
            check_input=False,
        )
        if isinstance(transformed, pd.DataFrame):
            return transformed
        return pd.DataFrame(transformed, index=frame.index, columns=pd.Index(self.features))

    def decision_function(self, frame: pd.DataFrame) -> np.ndarray:
        """Return the uncalibrated scorecard log-odds margin."""
        return np.asarray(
            self.logistic_regression.decision_function(self.transform(frame)),
            dtype=float,
        )

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        """Return the uncalibrated scorecard class probabilities."""
        return np.asarray(
            self.logistic_regression.predict_proba(self.transform(frame)), dtype=float
        )


@dataclass(frozen=True)
class ScorecardFit:
    """One scorecard learner and its auditable WOE/IV artifacts."""

    scores: LearnerScores
    model: WOELogisticModel
    summary: pd.DataFrame
    coefficients: pd.DataFrame
    binning_table: pd.DataFrame


def _calibrated_scores(
    *,
    data: PreparedData,
    config: Mapping[str, Any],
    name: str,
    model: Any,
    validation: pd.DataFrame,
    validation_probability: np.ndarray,
    margin_predictor: Any,
    random_state: int,
) -> LearnerScores:
    universe = data.universe
    calibration_all = universe.loc[universe["design_split"].eq("probability_calibration")]
    calibration_fit = calibration_all.loc[calibration_all["label_available"]]
    calibration_margin = np.asarray(
        margin_predictor(data.features.loc[calibration_fit.index]), dtype=float
    )
    calibrator_config = copy.deepcopy(config["probability_calibration"])
    calibrator_config["logistic_regression"]["random_state"] = int(random_state)
    calibrator = fit_platt_calibrator(
        calibration_margin,
        available_binary_labels(calibration_fit, block=f"{name}_probability_calibration"),
        calibrator_config,
    )
    all_margin = np.asarray(margin_predictor(data.features), dtype=float)
    all_probability = apply_platt_calibrator(calibrator, all_margin)
    groups = [int(value) for value in config["conformal"]["diagnostic_group_counts"]]
    return LearnerScores(
        name=name,
        model=model,
        calibrator=calibrator,
        probabilities=all_probability,
        taxonomy_edges=fixed_taxonomy_edges(
            all_probability[calibration_all.index],
            groups,
        ),
        metrics={
            "validation_uncalibrated": binary_probability_metrics(
                available_binary_labels(validation, block=f"{name}_validation"),
                validation_probability,
            ),
            "probability_calibration": binary_probability_metrics(
                available_binary_labels(
                    calibration_fit,
                    block=f"{name}_probability_calibration",
                ),
                all_probability[calibration_fit.index],
            ),
        },
    )


def fit_monotonic_catboost_control(data: PreparedData, config: Mapping[str, Any]) -> LearnerScores:
    """Fit CatBoost with only the predeclared domain-safe monotonic constraints."""
    universe = data.universe
    development = universe.loc[
        universe["design_split"].eq("pd_development") & universe["label_available"]
    ]
    train, validation, validation_cutoff = temporal_tail_split(
        development,
        tail_fraction=float(config["design"]["validation_tail_fraction"]),
    )
    control = config["credit_risk_controls"]["monotonic_catboost"]
    constraints = {str(key): int(value) for key, value in control["constraints"].items()}
    parameters = dict(config["model"]["fixed_params"])
    parameters.update(
        random_seed=int(config["model"]["canonical_seed"]),
        thread_count=int(config["execution"]["threads"]),
        monotone_constraints=constraints,
    )
    model = CatBoostClassifier(**parameters)
    model.fit(
        data.features.loc[train.index],
        available_binary_labels(train, block="monotonic_catboost_train"),
        cat_features=list(data.categorical_features),
    )
    validation_probability = np.asarray(
        model.predict_proba(data.features.loc[validation.index])[:, 1], dtype=float
    )
    scores = _calibrated_scores(
        data=data,
        config=config,
        name="catboost_monotonic_platt",
        model=model,
        validation=validation,
        validation_probability=validation_probability,
        margin_predictor=lambda frame: catboost_raw_margin(model, frame),
        random_state=int(config["model"]["canonical_seed"]),
    )
    scores.metrics["validation_cutoff"] = str(validation_cutoff.to_period("M"))
    scores.metrics["monotonic_constraints"] = constraints
    return scores


def _scorecard_binning_process(
    *,
    features: Sequence[str],
    categorical_features: Sequence[str],
    config: Mapping[str, Any],
) -> BinningProcess:
    options = config["credit_risk_controls"]["optbinning"]
    return BinningProcess(
        variable_names=list(features),
        categorical_variables=list(categorical_features),
        max_n_prebins=int(options["max_n_prebins"]),
        min_prebin_size=float(options["min_prebin_size"]),
        min_n_bins=int(options["min_n_bins"]),
        max_n_bins=int(options["max_n_bins"]),
        min_bin_size=float(options["min_bin_size"]),
        n_jobs=int(options["n_jobs"]),
        verbose=False,
    )


def scorecard_binning_table(model: WOELogisticModel) -> pd.DataFrame:
    """Return a Parquet-safe long table for every frozen WOE bin."""
    tables: list[pd.DataFrame] = []
    numeric_columns = (
        "Count",
        "Count (%)",
        "Non-event",
        "Event",
        "Event rate",
        "WoE",
        "IV",
        "JS",
    )
    for feature in model.features:
        table = model.binning_process.get_binned_variable(feature).binning_table.build().copy()
        table.insert(0, "feature", feature)
        table.insert(0, "learner", model.name)
        table["Bin"] = table["Bin"].map(str)
        for column in numeric_columns:
            if column in table:
                table[column] = pd.to_numeric(table[column], errors="coerce")
        tables.append(table)
    return pd.concat(tables, ignore_index=True)


def fit_woe_scorecard_control(
    data: PreparedData,
    config: Mapping[str, Any],
    *,
    specification: str,
) -> ScorecardFit:
    """Fit one closed OptBinning WOE/IV scorecard on the temporal train block."""
    controls = config["credit_risk_controls"]
    scorecard = controls["scorecards"][specification]
    name = str(scorecard["name"])
    features = tuple(str(value) for value in scorecard["features"])
    missing = sorted(set(features).difference(data.features.columns))
    if missing:
        raise KeyError(f"Scorecard {name} is missing active features: {missing}.")
    categorical = tuple(value for value in features if value in data.categorical_features)

    universe = data.universe
    development = universe.loc[
        universe["design_split"].eq("pd_development") & universe["label_available"]
    ]
    train, validation, validation_cutoff = temporal_tail_split(
        development,
        tail_fraction=float(config["design"]["validation_tail_fraction"]),
    )
    labels = available_binary_labels(train, block=f"{name}_train")
    process = _scorecard_binning_process(
        features=features,
        categorical_features=categorical,
        config=config,
    )
    process.fit(data.features.loc[train.index, features], labels)
    train_woe = process.transform(
        data.features.loc[train.index, features],
        metric="woe",
        metric_missing=0,
        metric_special=0,
        check_input=False,
    )
    logistic = controls["scorecard_logistic"]
    estimator = LogisticRegression(
        C=float(logistic["C"]),
        class_weight=str(logistic["class_weight"]),
        solver=str(logistic["solver"]),
        max_iter=int(logistic["max_iter"]),
        random_state=int(logistic["random_state"]),
    )
    estimator.fit(train_woe, labels)
    model = WOELogisticModel(
        name=name,
        features=features,
        categorical_features=categorical,
        binning_process=process,
        logistic_regression=estimator,
    )
    validation_probability = model.predict_proba(data.features.loc[validation.index])[:, 1]
    scores = _calibrated_scores(
        data=data,
        config=config,
        name=name,
        model=model,
        validation=validation,
        validation_probability=validation_probability,
        margin_predictor=model.decision_function,
        random_state=int(logistic["random_state"]),
    )
    scores.metrics["validation_cutoff"] = str(validation_cutoff.to_period("M"))
    scores.metrics["scorecard_features"] = list(features)
    summary = process.summary().copy()
    summary.insert(0, "learner", name)
    selected = [str(value) for value in process.get_support(names=True)]
    coefficients = pd.DataFrame(
        {
            "learner": name,
            "feature": selected,
            "logistic_coefficient": estimator.coef_.reshape(-1),
        }
    )
    coefficients["logistic_intercept"] = float(estimator.intercept_[0])
    return ScorecardFit(
        scores=scores,
        model=model,
        summary=summary,
        coefficients=coefficients,
        binning_table=scorecard_binning_table(model),
    )


def feature_variation_audit(data: PreparedData) -> pd.DataFrame:
    """Describe missingness and support for every active feature by temporal role."""
    rows: list[dict[str, Any]] = []
    roles = (
        "pd_development",
        "probability_calibration",
        "conformal_fit",
        "policy_development",
        "primary_oot",
        "censored_extension",
    )
    categorical = set(data.categorical_features)
    for role in roles:
        mask = data.universe["design_split"].eq(role)
        frame = data.features.loc[mask]
        for feature in data.features.columns:
            series = frame[feature]
            if feature in categorical:
                missing = series.astype(str).eq("__MISSING__")
                observed = series.loc[~missing]
                standard_deviation = np.nan
                minimum = None
                maximum = None
            else:
                numeric = pd.to_numeric(series, errors="coerce")
                missing = numeric.isna()
                observed = numeric.loc[~missing]
                standard_deviation = float(observed.std(ddof=0)) if len(observed) else np.nan
                minimum = float(observed.min()) if len(observed) else None
                maximum = float(observed.max()) if len(observed) else None
            rows.append(
                {
                    "role": role,
                    "feature": feature,
                    "feature_type": "categorical" if feature in categorical else "numeric",
                    "rows": int(len(series)),
                    "missing_rows": int(missing.sum()),
                    "missing_share": float(missing.mean()),
                    "unique_observed": int(observed.nunique(dropna=True)),
                    "constant_observed": bool(observed.nunique(dropna=True) <= 1),
                    "minimum": minimum,
                    "maximum": maximum,
                    "standard_deviation": standard_deviation,
                }
            )
    return pd.DataFrame(rows)


def _population_stability_index(
    reference: pd.Series, comparison: pd.Series, *, epsilon: float = 1e-6
) -> float:
    categories = sorted(set(reference.astype(str)).union(comparison.astype(str)))
    reference_share = (
        reference.astype(str).value_counts(normalize=True).reindex(categories, fill_value=0)
    )
    comparison_share = (
        comparison.astype(str).value_counts(normalize=True).reindex(categories, fill_value=0)
    )
    reference_safe = np.maximum(reference_share.to_numpy(dtype=float), epsilon)
    comparison_safe = np.maximum(comparison_share.to_numpy(dtype=float), epsilon)
    return float(
        np.sum((comparison_safe - reference_safe) * np.log(comparison_safe / reference_safe))
    )


def score_psi_audit(
    data: PreparedData,
    learners: Sequence[LearnerScores],
    *,
    bins: int,
) -> pd.DataFrame:
    """Compute outcome-free score PSI against the PD-development population."""
    reference_mask = data.universe["design_split"].eq("pd_development").to_numpy(dtype=bool)
    rows: list[dict[str, Any]] = []
    for learner in learners:
        reference_scores = learner.probabilities[reference_mask]
        edges = np.unique(
            np.quantile(reference_scores, np.linspace(0.0, 1.0, bins + 1), method="linear")
        )
        if len(edges) < 3:
            raise RuntimeError(f"{learner.name} has insufficient score variation for PSI.")
        edges[0] = -np.inf
        edges[-1] = np.inf
        reference_bins = pd.Series(pd.cut(reference_scores, bins=edges, include_lowest=True))
        for role in STABILITY_ROLES:
            role_mask = data.universe["design_split"].eq(role).to_numpy(dtype=bool)
            comparison_bins = pd.Series(
                pd.cut(learner.probabilities[role_mask], bins=edges, include_lowest=True)
            )
            rows.append(
                {
                    "learner": learner.name,
                    "reference_role": "pd_development",
                    "comparison_role": role,
                    "reference_rows": int(reference_mask.sum()),
                    "comparison_rows": int(role_mask.sum()),
                    "psi": _population_stability_index(reference_bins, comparison_bins),
                    "bin_edges": json.dumps([float(value) for value in edges]),
                }
            )
    return pd.DataFrame(rows)


def scorecard_feature_psi_audit(data: PreparedData, model: WOELogisticModel) -> pd.DataFrame:
    """Compute outcome-free PSI on each scorecard's frozen optimal-bin indices."""
    indices = model.transform(data.features, metric="indices")
    reference_mask = data.universe["design_split"].eq("pd_development").to_numpy(dtype=bool)
    rows: list[dict[str, Any]] = []
    for feature in model.features:
        reference = indices.loc[reference_mask, feature]
        for role in STABILITY_ROLES:
            role_mask = data.universe["design_split"].eq(role).to_numpy(dtype=bool)
            comparison = indices.loc[role_mask, feature]
            rows.append(
                {
                    "learner": model.name,
                    "feature": feature,
                    "reference_role": "pd_development",
                    "comparison_role": role,
                    "reference_rows": int(reference_mask.sum()),
                    "comparison_rows": int(role_mask.sum()),
                    "reference_bins": int(reference.nunique(dropna=False)),
                    "comparison_bins": int(comparison.nunique(dropna=False)),
                    "psi": _population_stability_index(reference, comparison),
                }
            )
    return pd.DataFrame(rows)
