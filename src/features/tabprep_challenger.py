"""TabPrep-inspired feature generators for isolated CRPTO challengers.

The implementation is intentionally local to CRPTO instead of importing the
reference TabPrep/AutoGluon stack.  That keeps the frozen thesis environment
stable while still exercising the useful feature families described in the
TabPrep paper: arithmetic combinations, relative group-by features,
out-of-fold target encodings, categorical interactions, and random subset
feature compression.
"""

from __future__ import annotations

import hashlib
import itertools
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from src.features.feature_engineering import (
    CATEGORICAL_FEATURES,
    FLAG_FEATURES,
    INTERACTION_FEATURES,
    MISSINGNESS_INDICATOR_SUFFIX,
    TARGET,
    build_feature_config,
)

MISSING_TOKEN = "__MISSING__"
UNKNOWN_TOKEN = "__UNKNOWN__"
TABPREP_FEATURE_PREFIX = "tp_"

FORBIDDEN_FEATURES = {
    "id",
    "url",
    "loan_status",
    "emp_title",
    "title",
    "zip_code",
    "addr_state",
    "next_pymnt_d",
    "pymnt_plan",
    "application_type",
    "verification_status_joint",
    "settlement_status",
    "hardship_status",
    "debt_settlement_flag",
    "last_pymnt_d",
    "last_pymnt_amnt",
    "last_credit_pull_d",
    "out_prncp",
    "out_prncp_inv",
    "total_pymnt",
    "total_pymnt_inv",
    "total_rec_prncp",
    "total_rec_int",
    "total_rec_late_fee",
    "recoveries",
    "collection_recovery_fee",
}
FORBIDDEN_PREFIXES = ("sec_app_",)
FORBIDDEN_CONTAINS = ("url", "title", "emp_title", "next_pymnt")


@dataclass(frozen=True)
class TabPrepVariantConfig:
    """Feature budgets for one TabPrep challenger variant."""

    name: str
    max_generated_features: int
    arithmetic_features: int
    groupby_features: int
    target_encoding_features: int
    interaction_encoding_features: int
    rsfc_features: int
    max_numeric_base_features: int
    max_groupby_numeric_features: int
    max_categorical_base_features: int
    max_scoring_rows: int = 100_000
    n_oof_folds: int = 5
    smoothing: float = 20.0
    min_group_support: int = 50
    rsfc_candidate_multiplier: int = 2


TABPREP_VARIANTS: dict[str, TabPrepVariantConfig] = {
    "safe_500": TabPrepVariantConfig(
        name="safe_500",
        max_generated_features=500,
        arithmetic_features=300,
        groupby_features=100,
        target_encoding_features=60,
        interaction_encoding_features=30,
        rsfc_features=10,
        max_numeric_base_features=60,
        max_groupby_numeric_features=40,
        max_categorical_base_features=10,
    ),
    "balanced_1500": TabPrepVariantConfig(
        name="balanced_1500",
        max_generated_features=1500,
        arithmetic_features=800,
        groupby_features=300,
        target_encoding_features=100,
        interaction_encoding_features=150,
        rsfc_features=150,
        max_numeric_base_features=100,
        max_groupby_numeric_features=75,
        max_categorical_base_features=10,
    ),
    "full_3000": TabPrepVariantConfig(
        name="full_3000",
        max_generated_features=3000,
        arithmetic_features=1500,
        groupby_features=700,
        target_encoding_features=150,
        interaction_encoding_features=300,
        rsfc_features=350,
        max_numeric_base_features=150,
        max_groupby_numeric_features=100,
        max_categorical_base_features=10,
    ),
}


@dataclass(frozen=True)
class FeatureSpec:
    """Selected generated feature and its provenance."""

    name: str
    generator: str
    operation: str
    source_features: tuple[str, ...]
    score: float
    selected_rank: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        """Return a JSON/parquet-friendly manifest row."""
        return {
            "feature": self.name,
            "generator": self.generator,
            "operation": self.operation,
            "source_features": "|".join(self.source_features),
            "n_source_features": len(self.source_features),
            "score": float(self.score),
            "selected_rank": int(self.selected_rank),
            **{f"meta_{key}": value for key, value in self.metadata.items()},
        }


@dataclass
class TargetEncodingState:
    """Full-train state used to transform target-encoded features."""

    sources: tuple[str, ...]
    mapping: dict[str, float]
    default_value: float
    smoothing: float
    min_count: int
    round_numeric: bool = False
    numeric_sources: tuple[str, ...] = ()
    round_decimals: int = 2


@dataclass
class GroupByState:
    """Train-only state for relative group-by features."""

    category: str
    numeric: str
    operation: str
    group_mean: dict[str, float]
    global_mean: float
    group_quantiles: dict[str, list[float]] = field(default_factory=dict)
    global_quantiles: list[float] = field(default_factory=list)


def get_tabprep_variant(name: str) -> TabPrepVariantConfig:
    """Return a known TabPrep challenger variant."""
    try:
        return TABPREP_VARIANTS[name]
    except KeyError as exc:
        options = ", ".join(sorted(TABPREP_VARIANTS))
        raise ValueError(f"Unknown TabPrep variant {name!r}. Expected one of: {options}") from exc


def is_forbidden_feature(feature: str, *, extra_blacklist: Iterable[str] = ()) -> bool:
    """Return True when a feature is unsafe for TabPrep generation."""
    lowered = feature.lower()
    exact = FORBIDDEN_FEATURES | {item.lower() for item in extra_blacklist}
    return (
        lowered == TARGET
        or lowered in exact
        or any(lowered.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)
        or any(token in lowered for token in FORBIDDEN_CONTAINS)
    )


def validate_no_forbidden_features(
    features: Sequence[str],
    *,
    extra_blacklist: Iterable[str] = (),
) -> None:
    """Fail fast if any candidate feature violates the TabPrep blacklist."""
    hits = [
        feature
        for feature in features
        if is_forbidden_feature(feature, extra_blacklist=extra_blacklist)
    ]
    if hits:
        raise ValueError(f"Forbidden TabPrep input features detected: {sorted(hits)}")


def resolve_tabprep_input_features(
    frame: pd.DataFrame,
    *,
    feature_config: Mapping[str, Any] | None = None,
    extra_blacklist: Iterable[str] = (),
) -> list[str]:
    """Resolve vetted CRPTO feature columns for TabPrep generation."""
    cfg = dict(feature_config or build_feature_config(frame))
    pool = list(cfg.get("CHALLENGER_FEATURE_POOL_V2") or [])
    if not pool:
        pool = list(cfg.get("CATBOOST_FEATURES") or [])

    resolved: list[str] = []
    for feature in pool:
        if feature not in frame.columns:
            continue
        if is_forbidden_feature(str(feature), extra_blacklist=extra_blacklist):
            continue
        if feature == TARGET:
            continue
        resolved.append(str(feature))
    return list(dict.fromkeys(resolved))


def resolve_tabprep_categorical_features(
    features: Sequence[str],
    *,
    feature_config: Mapping[str, Any] | None = None,
) -> list[str]:
    """Return TabPrep-safe categorical features from the selected feature pool."""
    cfg = dict(feature_config or {})
    configured = set(cfg.get("CATEGORICAL_FEATURES") or CATEGORICAL_FEATURES)
    configured.update(cfg.get("INTERACTION_FEATURES") or INTERACTION_FEATURES)
    feature_set = set(features)
    return [feature for feature in features if feature in configured and feature in feature_set]


class TabPrepChallengerTransformer:
    """Generate TabPrep-like features with train-only state.

    Target-aware features use out-of-fold values for ``fit_transform`` and
    full-train smoothed mappings for later ``transform`` calls.
    """

    def __init__(
        self,
        *,
        variant: str | TabPrepVariantConfig = "safe_500",
        input_features: Sequence[str],
        categorical_features: Sequence[str],
        target: str = TARGET,
        random_state: int = 42,
        extra_blacklist: Iterable[str] = (),
    ) -> None:
        self.variant = get_tabprep_variant(variant) if isinstance(variant, str) else variant
        self.input_features = list(dict.fromkeys(input_features))
        self.categorical_features = list(dict.fromkeys(categorical_features))
        self.target = target
        self.random_state = int(random_state)
        self.extra_blacklist = tuple(extra_blacklist)

        self.feature_specs_: list[FeatureSpec] = []
        self.numeric_features_: list[str] = []
        self.rsfc_base_features_: list[str] = []
        self.target_states_: dict[str, TargetEncodingState] = {}
        self.groupby_states_: dict[str, GroupByState] = {}
        self.generated_features_: list[str] = []
        self.global_target_mean_: float = 0.0
        self._is_fitted = False

    def fit_transform(
        self,
        frame: pd.DataFrame,
        y: pd.Series | np.ndarray,
        *,
        issue_dates: pd.Series | None = None,
    ) -> pd.DataFrame:
        """Fit all generators on train-fit data and return OOF-safe generated features."""
        validate_no_forbidden_features(self.input_features, extra_blacklist=self.extra_blacklist)
        x = frame.copy()
        y_series = pd.Series(y, index=x.index, dtype=float)
        self.global_target_mean_ = float(y_series.mean())

        available = [feature for feature in self.input_features if feature in x.columns]
        self.categorical_features = [
            feature for feature in self.categorical_features if feature in available
        ][: self.variant.max_categorical_base_features]
        self.numeric_features_ = self._select_numeric_features(x, y_series, available)
        self.rsfc_base_features_ = self._select_rsfc_base_features(x, available)

        logger.info(
            "TabPrep {} input: {} numeric, {} categorical, {} RSFC base features",
            self.variant.name,
            len(self.numeric_features_),
            len(self.categorical_features),
            len(self.rsfc_base_features_),
        )

        generated_train: dict[str, pd.Series] = {}
        specs: list[FeatureSpec] = []

        ar_specs = self._select_arithmetic_specs(x, y_series)
        specs.extend(ar_specs)
        generated_train.update({spec.name: self._apply_arithmetic(x, spec) for spec in ar_specs})

        group_specs = self._select_groupby_specs(x, y_series)
        specs.extend(group_specs)
        generated_train.update({spec.name: self._apply_groupby(x, spec) for spec in group_specs})

        te_specs, te_train = self._select_target_encoding_specs(
            x,
            y_series,
            issue_dates=issue_dates,
        )
        specs.extend(te_specs)
        generated_train.update(te_train)

        rsfc_specs, rsfc_train = self._select_rsfc_specs(
            x,
            y_series,
            issue_dates=issue_dates,
        )
        specs.extend(rsfc_specs)
        generated_train.update(rsfc_train)

        ranked = sorted(specs, key=lambda spec: (-spec.score, spec.generator, spec.name))
        ranked = ranked[: self.variant.max_generated_features]
        rank_by_name = {spec.name: idx + 1 for idx, spec in enumerate(ranked)}
        self.feature_specs_ = [
            FeatureSpec(
                name=spec.name,
                generator=spec.generator,
                operation=spec.operation,
                source_features=spec.source_features,
                score=spec.score,
                selected_rank=rank_by_name[spec.name],
                metadata=spec.metadata,
            )
            for spec in ranked
        ]
        self.generated_features_ = [spec.name for spec in self.feature_specs_]
        self._is_fitted = True

        return pd.DataFrame(
            {
                feature: _clean_numeric(generated_train[feature]).astype("float32")
                for feature in self.generated_features_
            },
            index=x.index,
        )

    def fit(
        self,
        frame: pd.DataFrame,
        y: pd.Series | np.ndarray,
        *,
        issue_dates: pd.Series | None = None,
    ) -> TabPrepChallengerTransformer:
        """Fit the transformer and discard the training matrix."""
        self.fit_transform(frame, y, issue_dates=issue_dates)
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Transform a new split using train-fit state only."""
        if not self._is_fitted:
            raise RuntimeError("TabPrepChallengerTransformer must be fitted before transform().")
        return pd.DataFrame(
            {
                spec.name: _clean_numeric(self._apply_spec(frame, spec)).astype("float32")
                for spec in self.feature_specs_
            },
            index=frame.index,
        )

    def feature_manifest(self) -> pd.DataFrame:
        """Return selected generated feature provenance."""
        return pd.DataFrame([spec.to_row() for spec in self.feature_specs_]).sort_values(
            "selected_rank",
        )

    def state_summary(self) -> dict[str, Any]:
        """Return compact serializable metadata about the fitted transformer."""
        return {
            "variant": self.variant.name,
            "random_state": self.random_state,
            "input_features": self.input_features,
            "categorical_features": self.categorical_features,
            "numeric_features": self.numeric_features_,
            "rsfc_base_features": self.rsfc_base_features_,
            "generated_features": self.generated_features_,
            "global_target_mean": self.global_target_mean_,
        }

    def _select_numeric_features(
        self,
        frame: pd.DataFrame,
        y: pd.Series,
        available: Sequence[str],
    ) -> list[str]:
        candidates: list[tuple[float, int, str]] = []
        categorical_set = set(self.categorical_features)
        for feature in available:
            if feature in categorical_set:
                continue
            series = pd.to_numeric(frame[feature], errors="coerce")
            if series.notna().mean() < 0.20:
                continue
            nunique = int(series.nunique(dropna=True))
            if nunique < 3:
                continue
            score = _safe_abs_corr(series, y)
            candidates.append((score, nunique, feature))
        candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
        return [feature for _, _, feature in candidates[: self.variant.max_numeric_base_features]]

    def _select_rsfc_base_features(
        self, frame: pd.DataFrame, available: Sequence[str]
    ) -> list[str]:
        categorical_set = set(self.categorical_features)
        allowed: list[str] = []
        for feature in available:
            if feature in categorical_set or feature in FLAG_FEATURES:
                allowed.append(feature)
                continue
            if feature.endswith(MISSINGNESS_INDICATOR_SUFFIX):
                allowed.append(feature)
                continue
            series = pd.to_numeric(frame[feature], errors="coerce")
            nunique = int(series.nunique(dropna=True))
            if 2 <= nunique <= 25:
                allowed.append(feature)
        return list(dict.fromkeys(allowed))[:150]

    def _sample_for_scoring(
        self,
        frame: pd.DataFrame,
        y: pd.Series,
    ) -> tuple[pd.DataFrame, pd.Series]:
        if len(frame) <= self.variant.max_scoring_rows:
            return frame, y
        sample = frame.sample(n=self.variant.max_scoring_rows, random_state=self.random_state)
        return sample, y.loc[sample.index]

    def _select_arithmetic_specs(self, frame: pd.DataFrame, y: pd.Series) -> list[FeatureSpec]:
        if not self.numeric_features_ or self.variant.arithmetic_features <= 0:
            return []
        x_sample, y_sample = self._sample_for_scoring(frame[self.numeric_features_], y)
        numeric = self.numeric_features_
        pair_candidates: list[FeatureSpec] = []
        operations = ("ratio", "diff", "product", "sum")
        for left, right in itertools.combinations(numeric, 2):
            for operation in operations:
                source_orders = [(left, right)]
                if operation in {"ratio", "diff"}:
                    source_orders.append((right, left))
                for sources in source_orders:
                    name = _make_feature_name("tp_ar", operation, sources)
                    spec = FeatureSpec(
                        name=name,
                        generator="arithmetic",
                        operation=operation,
                        source_features=sources,
                        score=0.0,
                        selected_rank=0,
                    )
                    score = _safe_abs_corr(self._apply_arithmetic(x_sample, spec), y_sample)
                    if score > 0:
                        pair_candidates.append(_replace_score(spec, score))

        triple_candidates: list[FeatureSpec] = []
        triple_base = numeric[: min(20, len(numeric))]
        for sources in itertools.combinations(triple_base, 3):
            for operation in ("product3", "sum3", "ratio_sum"):
                name = _make_feature_name("tp_ar", operation, sources)
                spec = FeatureSpec(
                    name=name,
                    generator="arithmetic",
                    operation=operation,
                    source_features=sources,
                    score=0.0,
                    selected_rank=0,
                )
                score = _safe_abs_corr(self._apply_arithmetic(x_sample, spec), y_sample)
                if score > 0:
                    triple_candidates.append(_replace_score(spec, score))

        candidates = pair_candidates + triple_candidates
        candidates.sort(key=lambda spec: (-spec.score, spec.name))
        selected = candidates[: self.variant.arithmetic_features]
        logger.info("Selected {} arithmetic TabPrep features", len(selected))
        return selected

    def _select_groupby_specs(self, frame: pd.DataFrame, y: pd.Series) -> list[FeatureSpec]:
        if (
            not self.categorical_features
            or not self.numeric_features_
            or self.variant.groupby_features <= 0
        ):
            return []
        groupby_numeric = self.numeric_features_[: self.variant.max_groupby_numeric_features]
        x_sample, y_sample = self._sample_for_scoring(
            frame[[*self.categorical_features, *groupby_numeric]],
            y,
        )
        candidates: list[FeatureSpec] = []
        for category in self.categorical_features:
            if int(frame[category].nunique(dropna=True)) < 2:
                continue
            for numeric in groupby_numeric:
                for operation in ("mean_ratio", "mean_diff", "pct_rank"):
                    name = _make_feature_name("tp_gb", operation, (numeric, category))
                    spec = FeatureSpec(
                        name=name,
                        generator="groupby",
                        operation=operation,
                        source_features=(numeric, category),
                        score=0.0,
                        selected_rank=0,
                        metadata={"category": category, "numeric": numeric},
                    )
                    state = _fit_groupby_state(
                        x_sample,
                        category=category,
                        numeric=numeric,
                        operation=operation,
                        min_support=max(2, min(self.variant.min_group_support, len(x_sample))),
                    )
                    score = _safe_abs_corr(_apply_groupby_state(x_sample, state), y_sample)
                    if score > 0:
                        candidates.append(_replace_score(spec, score))
        candidates.sort(key=lambda spec: (-spec.score, spec.name))
        selected = candidates[: self.variant.groupby_features]
        for spec in selected:
            category = str(spec.metadata["category"])
            numeric = str(spec.metadata["numeric"])
            self.groupby_states_[spec.name] = _fit_groupby_state(
                frame,
                category=category,
                numeric=numeric,
                operation=spec.operation,
                min_support=self.variant.min_group_support,
            )
        logger.info("Selected {} group-by TabPrep features", len(selected))
        return selected

    def _select_target_encoding_specs(
        self,
        frame: pd.DataFrame,
        y: pd.Series,
        *,
        issue_dates: pd.Series | None,
    ) -> tuple[list[FeatureSpec], dict[str, pd.Series]]:
        if not self.categorical_features:
            return [], {}
        base_sources = [(feature,) for feature in self.categorical_features]
        interaction_sources: list[tuple[str, ...]] = []
        for order in (2, 3):
            interaction_sources.extend(itertools.combinations(self.categorical_features, order))

        selected_specs: list[FeatureSpec] = []
        train_features: dict[str, pd.Series] = {}
        selected_base, base_train = self._score_target_encoding_sources(
            frame,
            y,
            base_sources,
            generator="target_encoding",
            operation="oof_target_mean",
            budget=self.variant.target_encoding_features,
            issue_dates=issue_dates,
            round_numeric=False,
        )
        selected_interactions, interaction_train = self._score_target_encoding_sources(
            frame,
            y,
            interaction_sources,
            generator="categorical_interaction",
            operation="oof_target_mean_interaction",
            budget=self.variant.interaction_encoding_features,
            issue_dates=issue_dates,
            round_numeric=False,
        )
        selected_specs.extend(selected_base)
        selected_specs.extend(selected_interactions)
        train_features.update(base_train)
        train_features.update(interaction_train)
        logger.info(
            "Selected {} target/categorical-interaction TabPrep features",
            len(selected_specs),
        )
        return selected_specs, train_features

    def _select_rsfc_specs(
        self,
        frame: pd.DataFrame,
        y: pd.Series,
        *,
        issue_dates: pd.Series | None,
    ) -> tuple[list[FeatureSpec], dict[str, pd.Series]]:
        if len(self.rsfc_base_features_) < 2 or self.variant.rsfc_features <= 0:
            return [], {}
        rng = np.random.default_rng(self.random_state)
        candidate_count = self.variant.rsfc_features * self.variant.rsfc_candidate_multiplier
        source_sets: list[tuple[str, ...]] = []
        seen: set[tuple[str, ...]] = set()
        max_size = min(4, len(self.rsfc_base_features_))
        attempts = 0
        while len(source_sets) < candidate_count and attempts < candidate_count * 10:
            attempts += 1
            size = int(rng.integers(2, max_size + 1))
            sources = tuple(sorted(rng.choice(self.rsfc_base_features_, size=size, replace=False)))
            if sources in seen:
                continue
            seen.add(sources)
            source_sets.append(sources)
        selected, train_features = self._score_target_encoding_sources(
            frame,
            y,
            source_sets,
            generator="rsfc",
            operation="random_subset_target_mean",
            budget=self.variant.rsfc_features,
            issue_dates=issue_dates,
            round_numeric=True,
        )
        logger.info("Selected {} RSFC TabPrep features", len(selected))
        return selected, train_features

    def _score_target_encoding_sources(
        self,
        frame: pd.DataFrame,
        y: pd.Series,
        sources_list: Sequence[tuple[str, ...]],
        *,
        generator: str,
        operation: str,
        budget: int,
        issue_dates: pd.Series | None,
        round_numeric: bool,
    ) -> tuple[list[FeatureSpec], dict[str, pd.Series]]:
        if budget <= 0:
            return [], {}
        candidates: list[tuple[FeatureSpec, TargetEncodingState, pd.Series]] = []
        numeric_sources = tuple(self.numeric_features_)
        for sources in sources_list:
            if any(source not in frame.columns for source in sources):
                continue
            name = _make_feature_name(
                "tp_te" if generator != "rsfc" else "tp_rsfc",
                operation,
                sources,
            )
            state, oof = _fit_oof_target_encoder(
                frame,
                y,
                sources=sources,
                n_folds=self.variant.n_oof_folds,
                smoothing=self.variant.smoothing,
                min_count=2,
                issue_dates=issue_dates,
                round_numeric=round_numeric,
                numeric_sources=numeric_sources,
            )
            score = _safe_abs_corr(oof, y)
            if score <= 0:
                continue
            spec = FeatureSpec(
                name=name,
                generator=generator,
                operation=operation,
                source_features=sources,
                score=score,
                selected_rank=0,
                metadata={"round_numeric": round_numeric},
            )
            candidates.append((spec, state, oof.rename(name)))
        candidates.sort(key=lambda item: (-item[0].score, item[0].name))
        selected = candidates[:budget]
        train_features: dict[str, pd.Series] = {}
        specs: list[FeatureSpec] = []
        for spec, state, train_series in selected:
            self.target_states_[spec.name] = state
            specs.append(spec)
            train_features[spec.name] = train_series
        return specs, train_features

    def _apply_spec(self, frame: pd.DataFrame, spec: FeatureSpec) -> pd.Series:
        if spec.generator == "arithmetic":
            return self._apply_arithmetic(frame, spec)
        if spec.generator == "groupby":
            return self._apply_groupby(frame, spec)
        if spec.generator in {"target_encoding", "categorical_interaction", "rsfc"}:
            return self._apply_target_encoding(frame, spec)
        raise ValueError(f"Unsupported TabPrep generator: {spec.generator}")

    def _apply_arithmetic(self, frame: pd.DataFrame, spec: FeatureSpec) -> pd.Series:
        sources = spec.source_features
        values = [_numeric_series(frame, source) for source in sources]
        if spec.operation == "ratio":
            return _safe_divide(values[0], values[1])
        if spec.operation == "diff":
            return values[0] - values[1]
        if spec.operation == "product":
            return values[0] * values[1]
        if spec.operation == "sum":
            return values[0] + values[1]
        if spec.operation == "product3":
            return values[0] * values[1] * values[2]
        if spec.operation == "sum3":
            return values[0] + values[1] + values[2]
        if spec.operation == "ratio_sum":
            return _safe_divide(values[0], values[1] + values[2])
        raise ValueError(f"Unsupported arithmetic operation: {spec.operation}")

    def _apply_groupby(self, frame: pd.DataFrame, spec: FeatureSpec) -> pd.Series:
        state = self.groupby_states_.get(spec.name)
        if state is None:
            raise RuntimeError(f"Missing group-by state for generated feature {spec.name!r}")
        return _apply_groupby_state(frame, state)

    def _apply_target_encoding(self, frame: pd.DataFrame, spec: FeatureSpec) -> pd.Series:
        state = self.target_states_.get(spec.name)
        if state is None:
            raise RuntimeError(f"Missing target encoder state for generated feature {spec.name!r}")
        keys = _make_key(
            frame,
            state.sources,
            round_numeric=state.round_numeric,
            numeric_sources=set(state.numeric_sources),
            round_decimals=state.round_decimals,
        )
        return keys.map(state.mapping).fillna(state.default_value).astype(float)


def _replace_score(spec: FeatureSpec, score: float) -> FeatureSpec:
    return FeatureSpec(
        name=spec.name,
        generator=spec.generator,
        operation=spec.operation,
        source_features=spec.source_features,
        score=float(score),
        selected_rank=spec.selected_rank,
        metadata=spec.metadata,
    )


def _numeric_series(frame: pd.DataFrame, feature: str) -> pd.Series:
    if feature not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[feature], errors="coerce").astype(float)


def _clean_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    den = denominator.replace(0, np.nan)
    return numerator / den


def _safe_abs_corr(series: pd.Series, y: pd.Series) -> float:
    values = _clean_numeric(series)
    target = pd.to_numeric(y.loc[values.index], errors="coerce").astype(float)
    if values.notna().sum() < 3 or target.nunique(dropna=True) < 2:
        return 0.0
    fill = values.median()
    if not np.isfinite(fill):
        fill = 0.0
    filled = values.fillna(float(fill))
    if filled.nunique(dropna=True) < 2:
        return 0.0
    corr = np.corrcoef(filled.to_numpy(dtype=float), target.to_numpy(dtype=float))[0, 1]
    if not np.isfinite(corr):
        return 0.0
    return float(abs(corr))


def _make_feature_name(prefix: str, operation: str, sources: Sequence[str]) -> str:
    cleaned_sources = [_clean_name(source) for source in sources]
    base = "__".join([prefix, _clean_name(operation), *cleaned_sources])
    if len(base) <= 120:
        return base
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]
    return "__".join([prefix, _clean_name(operation), *cleaned_sources[:3], digest])[:120]


def _clean_name(value: str) -> str:
    cleaned = "".join(char if char.isalnum() else "_" for char in str(value).lower())
    return "_".join(part for part in cleaned.split("_") if part)


def _category_key(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna(MISSING_TOKEN).astype(str)


def _make_key(
    frame: pd.DataFrame,
    sources: Sequence[str],
    *,
    round_numeric: bool = False,
    numeric_sources: set[str] | None = None,
    round_decimals: int = 2,
) -> pd.Series:
    if not sources:
        return pd.Series("", index=frame.index, dtype=str)
    numeric_sources = numeric_sources or set()
    pieces: list[pd.Series] = []
    for source in sources:
        if source not in frame.columns:
            piece = pd.Series(UNKNOWN_TOKEN, index=frame.index, dtype=str)
        elif round_numeric and source in numeric_sources:
            rounded = pd.to_numeric(frame[source], errors="coerce").round(round_decimals)
            piece = rounded.astype("string").fillna(MISSING_TOKEN).astype(str)
        else:
            piece = _category_key(frame[source])
        pieces.append(piece)
    key = pieces[0]
    for piece in pieces[1:]:
        key = key + "|" + piece
    return key.astype(str)


def _fit_mapping(
    keys: pd.Series,
    y: pd.Series,
    *,
    smoothing: float,
    default_value: float,
    min_count: int,
) -> dict[str, float]:
    tmp = pd.DataFrame({"key": keys.astype(str), "target": y.astype(float)})
    agg = tmp.groupby("key", dropna=False, observed=True)["target"].agg(["count", "sum"])
    encoded = (agg["sum"] + float(smoothing) * default_value) / (agg["count"] + float(smoothing))
    encoded = encoded[agg["count"] >= int(min_count)]
    return {str(key): float(value) for key, value in encoded.items()}


def _fit_oof_target_encoder(
    frame: pd.DataFrame,
    y: pd.Series,
    *,
    sources: tuple[str, ...],
    n_folds: int,
    smoothing: float,
    min_count: int,
    issue_dates: pd.Series | None,
    round_numeric: bool,
    numeric_sources: tuple[str, ...],
) -> tuple[TargetEncodingState, pd.Series]:
    numeric_source_set = set(numeric_sources)
    keys = _make_key(
        frame,
        sources,
        round_numeric=round_numeric,
        numeric_sources=numeric_source_set,
    )
    y_series = y.astype(float)
    default_value = float(y_series.mean())
    encoded = pd.Series(default_value, index=frame.index, dtype=float)
    folds = _temporal_fold_indices(frame, issue_dates=issue_dates, n_folds=n_folds)
    for fold_idx in folds:
        if len(fold_idx) == 0 or len(fold_idx) == len(frame):
            continue
        fold_index = frame.index[fold_idx]
        fit_index = frame.index.difference(fold_index)
        fold_default = float(y_series.loc[fit_index].mean()) if len(fit_index) else default_value
        mapping = _fit_mapping(
            keys.loc[fit_index],
            y_series.loc[fit_index],
            smoothing=smoothing,
            default_value=fold_default,
            min_count=min_count,
        )
        encoded.loc[fold_index] = keys.loc[fold_index].map(mapping).fillna(fold_default)

    mapping = _fit_mapping(
        keys,
        y_series,
        smoothing=smoothing,
        default_value=default_value,
        min_count=min_count,
    )
    state = TargetEncodingState(
        sources=sources,
        mapping=mapping,
        default_value=default_value,
        smoothing=float(smoothing),
        min_count=int(min_count),
        round_numeric=round_numeric,
        numeric_sources=numeric_sources,
    )
    return state, encoded


def _temporal_fold_indices(
    frame: pd.DataFrame,
    *,
    issue_dates: pd.Series | None,
    n_folds: int,
) -> list[np.ndarray]:
    n_folds = max(2, int(n_folds))
    if issue_dates is not None:
        ordered = issue_dates.loc[frame.index].sort_values(kind="mergesort").index
        positions = frame.index.get_indexer(ordered)
    else:
        positions = np.arange(len(frame), dtype=int)
    return [fold.astype(int) for fold in np.array_split(positions, n_folds) if len(fold) > 0]


def _fit_groupby_state(
    frame: pd.DataFrame,
    *,
    category: str,
    numeric: str,
    operation: str,
    min_support: int,
) -> GroupByState:
    groups = (
        _category_key(frame[category])
        if category in frame.columns
        else pd.Series(MISSING_TOKEN, index=frame.index)
    )
    values = _numeric_series(frame, numeric)
    global_mean = float(values.mean()) if values.notna().any() else 0.0
    tmp = pd.DataFrame({"group": groups, "value": values})
    agg = tmp.groupby("group", observed=True)["value"].agg(["count", "mean"])
    supported = agg[agg["count"] >= int(min_support)]
    group_mean = {str(key): float(value) for key, value in supported["mean"].dropna().items()}
    state = GroupByState(
        category=category,
        numeric=numeric,
        operation=operation,
        group_mean=group_mean,
        global_mean=global_mean,
    )
    if operation == "pct_rank":
        state.global_quantiles = _quantile_grid(values)
        for group, group_values in tmp.groupby("group", observed=True)["value"]:
            if len(group_values) >= int(min_support):
                state.group_quantiles[str(group)] = _quantile_grid(group_values)
    return state


def _apply_groupby_state(frame: pd.DataFrame, state: GroupByState) -> pd.Series:
    groups = (
        _category_key(frame[state.category])
        if state.category in frame.columns
        else pd.Series(MISSING_TOKEN, index=frame.index)
    )
    values = _numeric_series(frame, state.numeric)
    if state.operation in {"mean_ratio", "mean_diff"}:
        means = groups.map(state.group_mean).fillna(state.global_mean).astype(float)
        if state.operation == "mean_ratio":
            return _safe_divide(values, means)
        return values - means
    if state.operation == "pct_rank":
        return _apply_quantile_rank(values, groups, state)
    raise ValueError(f"Unsupported group-by operation: {state.operation}")


def _quantile_grid(values: pd.Series, *, n_quantiles: int = 21) -> list[float]:
    clean = _clean_numeric(values).dropna()
    if len(clean) < 2:
        return []
    quantiles = np.nanquantile(clean.to_numpy(dtype=float), np.linspace(0.0, 1.0, n_quantiles))
    return np.unique(quantiles.astype(float)).tolist()


def _apply_quantile_rank(values: pd.Series, groups: pd.Series, state: GroupByState) -> pd.Series:
    result = pd.Series(np.nan, index=values.index, dtype=float)
    global_bins = np.asarray(state.global_quantiles, dtype=float)
    for group, idx in groups.groupby(groups, sort=False).groups.items():
        bins = np.asarray(
            state.group_quantiles.get(str(group), state.global_quantiles), dtype=float
        )
        if len(bins) < 2:
            bins = global_bins
        group_values = values.loc[idx].to_numpy(dtype=float)
        if len(bins) < 2:
            result.loc[idx] = np.nan
            continue
        ranks = np.searchsorted(bins, group_values, side="right") - 1
        denom = max(len(bins) - 1, 1)
        result.loc[idx] = np.clip(ranks / denom, 0.0, 1.0)
    return result
