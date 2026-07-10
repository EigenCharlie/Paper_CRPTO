"""Benchmark conformal variants for coverage/efficiency trade-offs.

Usage:
    uv run python scripts/benchmark_conformal_variants.py
"""

from __future__ import annotations

import argparse
import json
import pickle
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from loguru import logger

from scripts.generate_conformal_intervals import (
    _build_feature_matrix,
    _load_calibrator,
    _load_model,
    _resolve_features,
    _subset_calibration_frame,
)
from src.evaluation.backtesting import winkler_interval_score
from src.models.conformal import (
    apply_probability_calibrator,
    build_mondrian_partition_labels,
    conditional_coverage_by_group,
    create_cross_conformal_score_intervals,
    create_pd_intervals,
    create_pd_intervals_mondrian_from_predictions,
    validate_coverage,
)
from src.utils.io_utils import read_with_fallback

TARGET_COL = "default_flag"
GROUP_COL = "grade"
DEFAULT_POLICY_CONFIG = "configs/crpto_conformal_policy.yaml"


@dataclass(frozen=True)
class BenchmarkData:
    model: Any
    calibrator: Any | None
    cal_df: pd.DataFrame
    test_df: pd.DataFrame
    features: list[str]
    categorical: list[str]
    X_cal: pd.DataFrame
    y_cal: pd.Series
    X_test: pd.DataFrame
    y_test: np.ndarray
    group_cal: pd.Series
    group_test: pd.Series
    issue_test: pd.Series
    y_prob_cal_raw: np.ndarray
    y_prob_test_raw: np.ndarray
    y_prob_calibrated: np.ndarray
    y_prob_test_calibrated: np.ndarray
    prob_cal_lookup: dict[str, np.ndarray]
    prob_test_lookup: dict[str, np.ndarray]


@dataclass(frozen=True)
class SearchSpace:
    partition_candidates: tuple[str, ...]
    partition_probability_sources: tuple[str, ...]
    n_score_bins_candidates: tuple[int, ...]
    fallback_modes: tuple[str, ...]
    score_scale_families: tuple[str, ...]
    min_group_sizes: tuple[int, ...]
    calibration_size_fractions: tuple[float, ...]


@dataclass
class VariantResults:
    rows: list[dict[str, Any]] = field(default_factory=list)
    by_group_rows: list[pd.DataFrame] = field(default_factory=list)
    temporal_rows: list[pd.DataFrame] = field(default_factory=list)
    local_rows: list[pd.DataFrame] = field(default_factory=list)


def _summarize_variant(
    name: str,
    y_true: np.ndarray,
    y_intervals: np.ndarray,
    groups: pd.Series,
    alpha: float,
) -> tuple[dict[str, Any], pd.DataFrame]:
    metrics = validate_coverage(y_true, y_intervals, alpha=alpha, log_summary=False)
    by_group = conditional_coverage_by_group(y_true, y_intervals, groups)
    widths = y_intervals[:, 1] - y_intervals[:, 0]
    winkler_90 = float(
        np.mean(winkler_interval_score(y_true, y_intervals[:, 0], y_intervals[:, 1], alpha=alpha))
    )
    row = {
        "variant": name,
        "alpha": float(alpha),
        "target_coverage": float(1.0 - alpha),
        "coverage": float(metrics["empirical_coverage"]),
        "coverage_gap": float(metrics["coverage_gap"]),
        "avg_width": float(metrics["avg_interval_width"]),
        "median_width": float(metrics["median_interval_width"]),
        "winkler_90": winkler_90,
        "p90_width": float(np.quantile(widths, 0.90)),
        "p95_width": float(np.quantile(widths, 0.95)),
        "min_group_coverage": float(by_group["coverage"].min()),
        "max_group_coverage": float(by_group["coverage"].max()),
        "std_group_coverage": float(by_group["coverage"].std(ddof=0)),
    }
    by_group = by_group.copy()
    by_group["variant"] = name
    by_group["alpha"] = float(alpha)
    return row, by_group


def _summarize_temporal_stability(
    name: str,
    y_true: np.ndarray,
    y_intervals: np.ndarray,
    issue_dates: pd.Series,
) -> tuple[dict[str, float], pd.DataFrame]:
    dates = pd.to_datetime(issue_dates, errors="coerce")
    frame = pd.DataFrame(
        {
            "variant": name,
            "month": dates.dt.to_period("M").dt.to_timestamp(),
            "y_true": np.asarray(y_true, dtype=float),
            "low": np.asarray(y_intervals[:, 0], dtype=float),
            "high": np.asarray(y_intervals[:, 1], dtype=float),
        }
    ).dropna(subset=["month"])
    if frame.empty:
        return (
            {
                "min_monthly_coverage": float("nan"),
                "last_monthly_coverage": float("nan"),
                "max_monthly_gap": float("nan"),
                "stability_over_time": float("inf"),
            },
            pd.DataFrame(
                {
                    "variant": pd.Series(dtype="object"),
                    "month": pd.Series(dtype="object"),
                    "n": pd.Series(dtype="int64"),
                    "coverage_90": pd.Series(dtype="float64"),
                    "avg_width_90": pd.Series(dtype="float64"),
                    "coverage_gap_90": pd.Series(dtype="float64"),
                }
            ),
        )

    frame["covered"] = (
        (frame["y_true"] >= frame["low"]) & (frame["y_true"] <= frame["high"])
    ).astype(float)
    frame["width"] = frame["high"] - frame["low"]
    monthly = (
        frame.groupby("month", observed=True)
        .agg(
            n=("covered", "size"),
            coverage_90=("covered", "mean"),
            avg_width_90=("width", "mean"),
        )
        .reset_index()
        .sort_values("month")
    )
    monthly["coverage_gap_90"] = (monthly["coverage_90"] - 0.90).abs()
    stability = {
        "min_monthly_coverage": float(monthly["coverage_90"].min()),
        "last_monthly_coverage": float(monthly["coverage_90"].iloc[-1]),
        "max_monthly_gap": float(monthly["coverage_gap_90"].max()),
        "stability_over_time": float(monthly["coverage_gap_90"].mean()),
    }
    monthly.insert(0, "variant", name)
    return stability, monthly


def _load_policy_config(path: str = DEFAULT_POLICY_CONFIG) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _promotion_pass(row: pd.Series, policy: dict[str, Any]) -> bool:
    return bool(
        float(row.get("coverage", 0.0)) >= float(policy.get("target_coverage_90_min", 0.90))
        and float(row.get("min_group_coverage", 0.0))
        >= float(policy.get("min_group_coverage_90_min", 0.88))
        and float(row.get("winkler_90", float("inf"))) <= float(policy.get("max_winkler_90", 1.20))
        and float(row.get("avg_width", float("inf"))) <= float(policy.get("max_avg_width_90", 0.80))
    )


def _build_output_paths(namespace: str | None = None) -> dict[str, Path]:
    if namespace:
        ns = str(namespace).strip().replace("/", "_")
        data_dir = Path("data/processed/conformal_gap") / ns
        models_dir = Path("models/conformal_gap") / ns
    else:
        data_dir = Path("data/processed")
        models_dir = Path("models")
    data_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    return {
        "data_dir": data_dir,
        "models_dir": models_dir,
        "benchmark": data_dir / "conformal_variant_benchmark.parquet",
        "benchmark_by_group": data_dir / "conformal_variant_benchmark_by_group.parquet",
        "selection_report": data_dir / "conformal_variant_selection_report.parquet",
        "temporal_diagnostics": data_dir / "conformal_temporal_diagnostics.parquet",
        "local_diagnostics": data_dir / "conformal_local_diagnostics.parquet",
        "selection_status": models_dir / "conformal_variant_selection_status.json",
        "selected_intervals": data_dir / "conformal_intervals_mondrian.parquet",
    }


def _coerce_csv_tuple(raw: str | None, *, cast=str) -> tuple[Any, ...]:
    if raw is None:
        return ()
    values = []
    for token in str(raw).split(","):
        token = token.strip()
        if not token:
            continue
        values.append(cast(token))
    return tuple(values)


def _variant_name(
    *,
    partition: str,
    partition_probability_source: str,
    n_score_bins: int,
    fallback_mode: str,
    score_scale_family: str,
    min_group_size: int,
    calibration_fraction: float | None = None,
) -> str:
    parts = [
        str(partition),
        f"prob={partition_probability_source}",
        f"bins={int(n_score_bins)}",
        f"fallback={fallback_mode}",
        f"scale={score_scale_family}",
        f"mgs={int(min_group_size)}",
    ]
    if calibration_fraction is not None:
        parts.append(f"calfrac={float(calibration_fraction):.2f}")
    return "::".join(parts)


def _load_benchmark_data(calibrator_override_path: str | None) -> BenchmarkData:
    model, _ = _load_model()
    calibrator = _load_calibrator(calibrator_override_path)
    cal_df = read_with_fallback(
        "data/processed/calibration_fe.parquet", "data/processed/calibration.parquet"
    )
    test_df = read_with_fallback("data/processed/test_fe.parquet", "data/processed/test.parquet")
    features, categorical = _resolve_features(model, cal_df, test_df)
    X_cal = _build_feature_matrix(cal_df, features, categorical)
    y_cal = cal_df[TARGET_COL].astype(float)
    X_test = _build_feature_matrix(test_df, features, categorical)
    y_test = test_df[TARGET_COL].astype(float).to_numpy(dtype=float)
    group_cal = cal_df[GROUP_COL].fillna("UNKNOWN").astype(str).reset_index(drop=True)
    group_test = test_df[GROUP_COL].fillna("UNKNOWN").astype(str).reset_index(drop=True)
    issue_test = test_df.get("issue_d", pd.Series([pd.NaT] * len(test_df))).reset_index(drop=True)
    y_prob_cal_raw = model.predict_proba(X_cal)[:, 1]
    y_prob_test_raw = model.predict_proba(X_test)[:, 1]
    y_prob_calibrated = (
        apply_probability_calibrator(calibrator, y_prob_cal_raw)
        if calibrator is not None
        else np.asarray(y_prob_cal_raw, dtype=float)
    )
    y_prob_test_calibrated = (
        apply_probability_calibrator(calibrator, y_prob_test_raw)
        if calibrator is not None
        else np.asarray(y_prob_test_raw, dtype=float)
    )
    return BenchmarkData(
        model=model,
        calibrator=calibrator,
        cal_df=cal_df,
        test_df=test_df,
        features=features,
        categorical=categorical,
        X_cal=X_cal,
        y_cal=y_cal,
        X_test=X_test,
        y_test=y_test,
        group_cal=group_cal,
        group_test=group_test,
        issue_test=issue_test,
        y_prob_cal_raw=y_prob_cal_raw,
        y_prob_test_raw=y_prob_test_raw,
        y_prob_calibrated=y_prob_calibrated,
        y_prob_test_calibrated=y_prob_test_calibrated,
        prob_cal_lookup={"raw": y_prob_cal_raw, "calibrated": y_prob_calibrated},
        prob_test_lookup={"raw": y_prob_test_raw, "calibrated": y_prob_test_calibrated},
    )


def _unique_clean_strings(values: tuple[str, ...], fallback: tuple[str, ...]) -> tuple[str, ...]:
    cleaned = tuple(dict.fromkeys(str(x).strip() for x in values if str(x).strip()))
    return cleaned or fallback


def _unique_clean_lower_strings(
    values: tuple[str, ...],
    fallback: tuple[str, ...],
) -> tuple[str, ...]:
    cleaned = tuple(dict.fromkeys(str(x).strip().lower() for x in values if str(x).strip()))
    return cleaned or fallback


def _positive_int_tuple(values: tuple[int, ...], fallback: tuple[int, ...]) -> tuple[int, ...]:
    cleaned = tuple(int(x) for x in values if int(x) > 0)
    return cleaned or fallback


def _min_group_size_tuple(
    values: tuple[int, ...] | None,
    default: int,
) -> tuple[int, ...]:
    return _positive_int_tuple(values or (default,), (int(default),))


def _valid_fraction_tuple(values: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(float(x) for x in values if 0 < float(x) <= 1)


def _normalize_search_space(
    *,
    calibration_size_fractions: tuple[float, ...],
    partition_candidates: tuple[str, ...],
    partition_probability_sources: tuple[str, ...],
    n_score_bins_candidates: tuple[int, ...],
    fallback_modes: tuple[str, ...],
    score_scale_families: tuple[str, ...],
    min_group_sizes: tuple[int, ...] | None,
    min_group_size_default: int,
) -> SearchSpace:
    return SearchSpace(
        partition_candidates=_unique_clean_strings(partition_candidates, ("grade",)),
        partition_probability_sources=_unique_clean_lower_strings(
            partition_probability_sources, ("raw",)
        ),
        n_score_bins_candidates=_positive_int_tuple(n_score_bins_candidates, (10,)),
        fallback_modes=_unique_clean_lower_strings(fallback_modes, ("grade_then_global",)),
        score_scale_families=_unique_clean_lower_strings(score_scale_families, ("none",)),
        min_group_sizes=_min_group_size_tuple(min_group_sizes, min_group_size_default),
        calibration_size_fractions=_valid_fraction_tuple(calibration_size_fractions),
    )


def _append_global_variant(
    *,
    data: BenchmarkData,
    results: VariantResults,
    alpha: float,
) -> None:
    _y_pred_global, y_int_global = create_pd_intervals(
        classifier=data.model,
        X_cal=data.X_cal,
        y_cal=data.y_cal,
        X_test=data.X_test,
        alpha=alpha,
        calibrator=data.calibrator,
    )
    row, by_group = _summarize_variant(
        "global_split", data.y_test, y_int_global, data.group_test, alpha
    )
    temporal_meta, temporal_monthly = _summarize_temporal_stability(
        "global_split", data.y_test, y_int_global, data.issue_test
    )
    row.update(temporal_meta)
    results.rows.append(row)
    results.by_group_rows.append(by_group)
    results.temporal_rows.append(temporal_monthly)


def _append_mondrian_variant(
    *,
    data: BenchmarkData,
    results: VariantResults,
    partition_cache: dict[
        tuple[str, str, int, str, int, float, int],
        tuple[pd.Series, pd.Series, dict[str, Any]],
    ],
    name: str,
    partition: str,
    partition_probability_source: str,
    n_score_bins: int,
    fallback_mode: str,
    score_scale_family: str,
    alpha: float,
    alpha_used: float,
    min_group_size: int,
    collect_local_diagnostics: bool,
    y_cal_variant: pd.Series | None = None,
    y_prob_cal_variant: np.ndarray | None = None,
    base_groups_cal_variant: pd.Series | None = None,
    calibration_fraction: float | None = None,
) -> None:
    y_cal_use = data.y_cal if y_cal_variant is None else y_cal_variant
    y_prob_cal_use = (
        data.prob_cal_lookup[partition_probability_source]
        if y_prob_cal_variant is None
        else y_prob_cal_variant
    )
    y_interval_cal_pred = (
        data.y_prob_calibrated if y_prob_cal_variant is None else y_prob_cal_variant
    )
    base_groups_cal_use = (
        data.group_cal if base_groups_cal_variant is None else base_groups_cal_variant
    )
    cache_key = (
        str(partition),
        str(partition_probability_source),
        int(n_score_bins),
        str(fallback_mode),
        int(min_group_size),
        float(calibration_fraction or 1.0),
        int(len(y_cal_use)),
    )
    if cache_key in partition_cache:
        group_cal_part, group_test_part, partition_meta = partition_cache[cache_key]
    else:
        group_cal_part, group_test_part, partition_meta = build_mondrian_partition_labels(
            y_prob_cal=y_prob_cal_use,
            y_prob_eval=data.prob_test_lookup[partition_probability_source],
            partition=partition,
            base_groups_cal=base_groups_cal_use.iloc[: len(y_cal_use)].reset_index(drop=True),
            base_groups_eval=data.group_test,
            n_score_bins=n_score_bins,
            min_group_size=min_group_size,
            fallback_mode=fallback_mode,
        )
        partition_cache[cache_key] = (group_cal_part, group_test_part, partition_meta)
    _y_pred, y_int, _ = create_pd_intervals_mondrian_from_predictions(
        y_cal_pred=y_interval_cal_pred,
        y_test_pred=data.y_prob_test_calibrated,
        y_cal=y_cal_use,
        group_cal=group_cal_part,
        group_test=group_test_part,
        alpha=alpha_used,
        min_group_size=min_group_size,
        score_scale_family=score_scale_family,
        log_summary=False,
    )
    row, by_group = _summarize_variant(name, data.y_test, y_int, group_test_part, alpha)
    temporal_meta, temporal_monthly = _summarize_temporal_stability(
        name, data.y_test, y_int, data.issue_test
    )
    row.update(temporal_meta)
    row["partition"] = partition_meta.get("partition", partition)
    row["partition_probability_source"] = partition_probability_source
    row["n_score_bins"] = int(n_score_bins)
    row["fallback_mode"] = str(partition_meta.get("fallback_mode", fallback_mode))
    row["scaled_scores"] = bool(score_scale_family != "none")
    row["score_scale_family"] = score_scale_family
    row["min_group_size"] = int(min_group_size)
    row["selected_alpha_used"] = float(alpha_used)
    row["fallback_groups_n"] = len(partition_meta.get("fallback_groups", []))
    row["calibration_fraction"] = float(calibration_fraction or 1.0)
    results.rows.append(row)
    results.by_group_rows.append(by_group)
    results.temporal_rows.append(temporal_monthly)

    if collect_local_diagnostics:
        local_diag = pd.DataFrame(
            {
                "record_type": "local_partition_summary",
                "variant": name,
                "partition": row["partition"],
                "group": pd.Series(group_test_part).astype(str),
                "y_true": data.y_test,
                "low": y_int[:, 0],
                "high": y_int[:, 1],
            }
        )
        local_diag["covered"] = (
            (local_diag["y_true"] >= local_diag["low"])
            & (local_diag["y_true"] <= local_diag["high"])
        ).astype(float)
        local_diag["width"] = local_diag["high"] - local_diag["low"]
        results.local_rows.append(local_diag)


def _append_search_space_variants(
    *,
    data: BenchmarkData,
    results: VariantResults,
    partition_cache: dict[
        tuple[str, str, int, str, int, float, int],
        tuple[pd.Series, pd.Series, dict[str, Any]],
    ],
    space: SearchSpace,
    alpha: float,
    collect_local_diagnostics: bool,
) -> None:
    for partition in space.partition_candidates:
        for partition_probability_source in space.partition_probability_sources:
            for n_score_bins in space.n_score_bins_candidates:
                for fallback_mode in space.fallback_modes:
                    for score_scale_family in space.score_scale_families:
                        for min_group_size in space.min_group_sizes:
                            _append_mondrian_variant(
                                data=data,
                                results=results,
                                partition_cache=partition_cache,
                                name=_variant_name(
                                    partition=partition,
                                    partition_probability_source=partition_probability_source,
                                    n_score_bins=n_score_bins,
                                    fallback_mode=fallback_mode,
                                    score_scale_family=score_scale_family,
                                    min_group_size=min_group_size,
                                ),
                                partition=partition,
                                partition_probability_source=partition_probability_source,
                                n_score_bins=n_score_bins,
                                fallback_mode=fallback_mode,
                                score_scale_family=score_scale_family,
                                alpha=alpha,
                                alpha_used=alpha,
                                min_group_size=min_group_size,
                                collect_local_diagnostics=collect_local_diagnostics,
                            )


def _sample_indices(n_rows: int, sample_size: int, rng: np.random.RandomState) -> np.ndarray:
    return (
        rng.choice(n_rows, size=min(int(sample_size), n_rows), replace=False)
        if n_rows > int(sample_size)
        else np.arange(n_rows)
    )


def _append_cross_conformal_variant(
    *,
    data: BenchmarkData,
    results: VariantResults,
    alpha: float,
    cross_cal_sample_size: int,
    cross_test_sample_size: int,
) -> None:
    rng = np.random.RandomState(42)
    cal_idx = _sample_indices(len(data.y_cal), cross_cal_sample_size, rng)
    test_idx = _sample_indices(len(data.y_test), cross_test_sample_size, rng)
    _y_pred_cross, y_int_cross = create_cross_conformal_score_intervals(
        y_cal=data.y_cal.iloc[cal_idx].reset_index(drop=True),
        y_prob_cal=data.y_prob_calibrated[cal_idx],
        y_prob_test=data.y_prob_test_calibrated[test_idx],
        alpha=alpha,
        method="plus",
        cv=5,
    )
    row, by_group = _summarize_variant(
        "cross_conformal_score_space",
        data.y_test[test_idx],
        y_int_cross,
        data.group_test.iloc[test_idx].reset_index(drop=True),
        alpha,
    )
    temporal_meta, temporal_monthly = _summarize_temporal_stability(
        "cross_conformal_score_space",
        data.y_test[test_idx],
        y_int_cross,
        data.issue_test.iloc[test_idx].reset_index(drop=True),
    )
    row.update(temporal_meta)
    row["implementation_note"] = (
        "Cross conformal executed on calibrated score space with a lightweight linear regressor."
    )
    row["evaluation_sample_n_cal"] = len(cal_idx)
    row["evaluation_sample_n_test"] = len(test_idx)
    results.rows.append(row)
    results.by_group_rows.append(by_group)
    results.temporal_rows.append(temporal_monthly)


def _append_selected_config_variant(
    *,
    data: BenchmarkData,
    results: VariantResults,
    partition_cache: dict[
        tuple[str, str, int, str, int, float, int],
        tuple[pd.Series, pd.Series, dict[str, Any]],
    ],
    selected_config_path: str,
    alpha: float,
    min_group_size_default: int,
    collect_local_diagnostics: bool,
) -> None:
    cfg_path = Path(selected_config_path)
    if not cfg_path.exists():
        return
    with open(cfg_path, "rb") as f:
        payload = pickle.load(f)
    best = payload.get("tuning_90_best", {}) if isinstance(payload, dict) else {}
    _append_mondrian_variant(
        data=data,
        results=results,
        partition_cache=partition_cache,
        name="mondrian_selected_cfg",
        partition=str(best.get("partition", "grade")),
        partition_probability_source=str(best.get("partition_probability_source", "raw")),
        n_score_bins=int(best.get("n_score_bins", 10)),
        fallback_mode=str(best.get("fallback_mode", "grade_then_global")),
        score_scale_family=str(best.get("score_scale_family", "none")),
        alpha=alpha,
        alpha_used=float(best.get("alpha_used_90", alpha)),
        min_group_size=int(best.get("min_group_size", min_group_size_default)),
        collect_local_diagnostics=collect_local_diagnostics,
    )


def _calibration_sensitivity_rows(
    *,
    data: BenchmarkData,
    space: SearchSpace,
    alpha: float,
) -> list[dict[str, Any]]:
    sensitivity_rows: list[dict[str, Any]] = []
    for frac in space.calibration_size_fractions:
        cal_df_sub = _subset_calibration_frame(data.cal_df, calibration_fraction=float(frac))
        X_cal_sub = _build_feature_matrix(cal_df_sub, data.features, data.categorical)
        y_cal_sub = cal_df_sub[TARGET_COL].astype(float).reset_index(drop=True)
        group_cal_sub = cal_df_sub[GROUP_COL].fillna("UNKNOWN").astype(str).reset_index(drop=True)
        y_prob_cal_sub_raw = data.model.predict_proba(X_cal_sub)[:, 1]
        y_prob_cal_sub_calibrated = (
            apply_probability_calibrator(data.calibrator, y_prob_cal_sub_raw)
            if data.calibrator is not None
            else np.asarray(y_prob_cal_sub_raw, dtype=float)
        )
        prob_cal_sub_lookup = {"raw": y_prob_cal_sub_raw, "calibrated": y_prob_cal_sub_calibrated}
        for partition in ("score_decile_mondrian", "grade_x_scoreband_mondrian"):
            for partition_probability_source in space.partition_probability_sources:
                sensitivity_rows.append(
                    _calibration_sensitivity_row(
                        data=data,
                        space=space,
                        alpha=alpha,
                        partition=partition,
                        partition_probability_source=partition_probability_source,
                        calibration_fraction=float(frac),
                        X_cal_sub=X_cal_sub,
                        y_cal_sub=y_cal_sub,
                        group_cal_sub=group_cal_sub,
                        y_prob_cal_sub_calibrated=y_prob_cal_sub_calibrated,
                        y_prob_cal_sub=prob_cal_sub_lookup[partition_probability_source],
                    )
                )
    return sensitivity_rows


def _calibration_sensitivity_row(
    *,
    data: BenchmarkData,
    space: SearchSpace,
    alpha: float,
    partition: str,
    partition_probability_source: str,
    calibration_fraction: float,
    X_cal_sub: pd.DataFrame,
    y_cal_sub: pd.Series,
    group_cal_sub: pd.Series,
    y_prob_cal_sub_calibrated: np.ndarray,
    y_prob_cal_sub: np.ndarray,
) -> dict[str, Any]:
    group_cal_part, group_test_part, partition_meta = build_mondrian_partition_labels(
        y_prob_cal=y_prob_cal_sub,
        y_prob_eval=data.prob_test_lookup[partition_probability_source],
        partition=partition,
        base_groups_cal=group_cal_sub,
        base_groups_eval=data.group_test,
        n_score_bins=space.n_score_bins_candidates[0],
        min_group_size=space.min_group_sizes[0],
        fallback_mode=space.fallback_modes[0],
    )
    _y_pred_sub, y_int_sub, _ = create_pd_intervals_mondrian_from_predictions(
        y_cal_pred=y_prob_cal_sub_calibrated,
        y_test_pred=data.y_prob_test_calibrated,
        y_cal=y_cal_sub,
        group_cal=group_cal_part,
        group_test=group_test_part,
        alpha=alpha,
        min_group_size=space.min_group_sizes[0],
        score_scale_family=space.score_scale_families[0],
        log_summary=False,
    )
    metrics = validate_coverage(data.y_test, y_int_sub, alpha=alpha, log_summary=False)
    by_group_sub = conditional_coverage_by_group(data.y_test, y_int_sub, group_test_part)
    stability_sub, _ = _summarize_temporal_stability(
        partition, data.y_test, y_int_sub, data.issue_test
    )
    return {
        "record_type": "calibration_size_sensitivity",
        "variant": _variant_name(
            partition=partition,
            partition_probability_source=partition_probability_source,
            n_score_bins=space.n_score_bins_candidates[0],
            fallback_mode=space.fallback_modes[0],
            score_scale_family=space.score_scale_families[0],
            min_group_size=space.min_group_sizes[0],
            calibration_fraction=calibration_fraction,
        ),
        "partition": partition_meta.get("partition", partition),
        "partition_probability_source": partition_probability_source,
        "calibration_fraction": calibration_fraction,
        "n_calibration_rows": len(X_cal_sub),
        "coverage": float(metrics["empirical_coverage"]),
        "coverage_gap": float(metrics["coverage_gap"]),
        "avg_width": float(metrics["avg_interval_width"]),
        "min_group_coverage": float(by_group_sub["coverage"].min()),
        "winkler_90": float(
            np.mean(
                winkler_interval_score(data.y_test, y_int_sub[:, 0], y_int_sub[:, 1], alpha=alpha)
            )
        ),
        "stability_over_time": float(stability_sub["stability_over_time"]),
    }


def _final_benchmark_frames(
    *,
    results: VariantResults,
    sensitivity_rows: list[dict[str, Any]],
    policy: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    bench = pd.DataFrame(results.rows)
    bench["promotion_pass"] = bench.apply(lambda row: _promotion_pass(row, policy), axis=1)
    bench = bench.sort_values(
        [
            "promotion_pass",
            "coverage_gap",
            "min_group_coverage",
            "winkler_90",
            "avg_width",
            "stability_over_time",
        ],
        ascending=[False, True, False, True, True, True],
    ).reset_index(drop=True)
    bench["selection_rank"] = np.arange(1, len(bench) + 1, dtype=int)
    bench_by_group = (
        pd.concat(results.by_group_rows, ignore_index=True)
        .sort_values(["variant", "group"])
        .reset_index(drop=True)
    )
    temporal_diagnostics = (
        pd.concat(results.temporal_rows, ignore_index=True)
        .sort_values(["variant", "month"])
        .reset_index(drop=True)
    )
    local_diagnostics = (
        pd.concat(results.local_rows, ignore_index=True) if results.local_rows else pd.DataFrame()
    )
    if sensitivity_rows:
        local_diagnostics = pd.concat(
            [local_diagnostics, pd.DataFrame(sensitivity_rows)],
            ignore_index=True,
            sort=False,
        )
    return bench, bench_by_group, temporal_diagnostics, local_diagnostics


def _selected_config_local_diagnostics(
    *,
    selected_config_path: str,
    selected_intervals_path: Path,
) -> pd.DataFrame:
    selected_cfg_path = Path(selected_config_path)
    if not selected_cfg_path.exists() or not selected_intervals_path.exists():
        return pd.DataFrame()
    with open(selected_cfg_path, "rb") as f:
        selected_payload = pickle.load(f)
    selected_intervals = pd.read_parquet(selected_intervals_path)
    if not {"y_true", "pd_low_90", "pd_high_90", GROUP_COL}.issubset(selected_intervals.columns):
        return pd.DataFrame()
    selected_local = pd.DataFrame(
        {
            "record_type": "local_partition_summary",
            "variant": "mondrian_selected_cfg",
            "partition": str(selected_payload.get("partition", "grade")),
            "group": selected_intervals[GROUP_COL].fillna("UNKNOWN").astype(str),
            "y_true": pd.to_numeric(selected_intervals["y_true"], errors="coerce"),
            "low": pd.to_numeric(selected_intervals["pd_low_90"], errors="coerce"),
            "high": pd.to_numeric(selected_intervals["pd_high_90"], errors="coerce"),
        }
    )
    selected_local["covered"] = (
        (selected_local["y_true"] >= selected_local["low"])
        & (selected_local["y_true"] <= selected_local["high"])
    ).astype(float)
    selected_local["width"] = selected_local["high"] - selected_local["low"]
    return selected_local


def _append_selected_local_diagnostics(
    *,
    local_diagnostics: pd.DataFrame,
    selected_config_path: str,
    selected_intervals_path: Path,
) -> pd.DataFrame:
    selected_local = _selected_config_local_diagnostics(
        selected_config_path=selected_config_path,
        selected_intervals_path=selected_intervals_path,
    )
    if selected_local.empty:
        return local_diagnostics
    return pd.concat([local_diagnostics, selected_local], ignore_index=True, sort=False)


def _selection_status_payload(
    *,
    bench: pd.DataFrame,
    output_paths: dict[str, Path],
    artifact_namespace: str | None,
    calibrator_override_path: str | None,
    policy_config_path: str,
    collect_local_diagnostics: bool,
    space: SearchSpace,
) -> dict[str, Any]:
    selected = bench.iloc[0].to_dict()
    return {
        "schema_version": "2026-04-03.1",
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "artifact_namespace": artifact_namespace or "",
        "calibrator_override_path": str(calibrator_override_path or ""),
        "policy_config_path": str(policy_config_path),
        "selected_variant": str(selected.get("variant", "")),
        "selection_rank": int(selected.get("selection_rank", 1)),
        "promotion_pass": bool(selected.get("promotion_pass", False)),
        "selection_criteria": [
            "promotion_pass",
            "coverage_gap",
            "min_group_coverage",
            "winkler_90",
            "avg_width",
            "stability_over_time",
        ],
        "retired_backtest_role": (
            "Kupiec/Christoffersen are research diagnostics outside the IJDS "
            "promotion gate; validate_conformal_policy.py promotes on material "
            "coverage, group coverage, width, alert, and Winkler checks."
        ),
        "local_diagnostics_mode": (
            "all_variants" if collect_local_diagnostics else "selected_config_plus_sensitivity"
        ),
        "variants_tested": bench["variant"].astype(str).tolist(),
        "report_path": str(output_paths["selection_report"]),
        "summary_path": str(output_paths["benchmark"]),
        "temporal_diagnostics_path": str(output_paths["temporal_diagnostics"]),
        "local_diagnostics_path": str(output_paths["local_diagnostics"]),
        "selected_metrics": {
            "coverage": float(selected.get("coverage", 0.0)),
            "coverage_gap": float(selected.get("coverage_gap", 0.0)),
            "avg_width": float(selected.get("avg_width", 0.0)),
            "min_group_coverage": float(selected.get("min_group_coverage", 0.0)),
            "winkler_90": float(selected.get("winkler_90", 0.0)),
            "stability_over_time": float(selected.get("stability_over_time", 0.0)),
        },
        "search_space": {
            "partition_candidates": list(space.partition_candidates),
            "partition_probability_sources": list(space.partition_probability_sources),
            "n_score_bins_candidates": [int(x) for x in space.n_score_bins_candidates],
            "fallback_modes": list(space.fallback_modes),
            "score_scale_families": list(space.score_scale_families),
            "min_group_sizes": [int(x) for x in space.min_group_sizes],
            "calibration_size_fractions": [float(x) for x in space.calibration_size_fractions],
        },
        "top_variants": bench.head(5).to_dict(orient="records"),
    }


def _write_benchmark_outputs(
    *,
    output_paths: dict[str, Path],
    bench: pd.DataFrame,
    bench_by_group: pd.DataFrame,
    temporal_diagnostics: pd.DataFrame,
    local_diagnostics: pd.DataFrame,
    status_payload: dict[str, Any],
) -> None:
    bench_path = output_paths["benchmark"]
    bench_group_path = output_paths["benchmark_by_group"]
    selection_path = output_paths["selection_report"]
    temporal_path = output_paths["temporal_diagnostics"]
    local_path = output_paths["local_diagnostics"]
    bench.to_parquet(bench_path, index=False)
    bench_by_group.to_parquet(bench_group_path, index=False)
    bench.to_parquet(selection_path, index=False)
    temporal_diagnostics.to_parquet(temporal_path, index=False)
    if not local_diagnostics.empty:
        local_diagnostics.to_parquet(local_path, index=False)

    status_path = output_paths["selection_status"]
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(status_payload, indent=2, default=str), encoding="utf-8")
    logger.info("Saved conformal benchmark summary: {} ({})", bench_path, bench.shape)
    logger.info(
        "Saved conformal benchmark by-group: {} ({})", bench_group_path, bench_by_group.shape
    )
    logger.info(
        "Saved conformal temporal diagnostics: {} ({})", temporal_path, temporal_diagnostics.shape
    )
    if not local_diagnostics.empty:
        logger.info(
            "Saved conformal local diagnostics: {} ({})", local_path, local_diagnostics.shape
        )
    logger.info("Saved conformal variant selection report: {}", selection_path)
    logger.info("Saved conformal variant selection status: {}", status_path)


def main(
    alpha: float = 0.10,
    selected_config_path: str = "models/conformal_results_mondrian.pkl",
    min_group_size_default: int = 500,
    cross_cal_sample_size: int = 5000,
    cross_test_sample_size: int = 5000,
    calibration_size_fractions: tuple[float, ...] = (0.25, 0.50, 0.75, 1.0),
    partition_candidates: tuple[str, ...] = (
        "grade",
        "score_decile_mondrian",
        "grade_x_scoreband_mondrian",
    ),
    partition_probability_sources: tuple[str, ...] = ("raw",),
    n_score_bins_candidates: tuple[int, ...] = (10,),
    fallback_modes: tuple[str, ...] = ("grade_then_global",),
    score_scale_families: tuple[str, ...] = ("none", "bernoulli_sqrt"),
    min_group_sizes: tuple[int, ...] | None = None,
    artifact_namespace: str | None = None,
    calibrator_override_path: str | None = None,
    policy_config_path: str = DEFAULT_POLICY_CONFIG,
    collect_local_diagnostics: bool = False,
) -> None:
    policy = _load_policy_config(policy_config_path).get("policy", {}) or {}
    data = _load_benchmark_data(calibrator_override_path)
    space = _normalize_search_space(
        calibration_size_fractions=calibration_size_fractions,
        partition_candidates=partition_candidates,
        partition_probability_sources=partition_probability_sources,
        n_score_bins_candidates=n_score_bins_candidates,
        fallback_modes=fallback_modes,
        score_scale_families=score_scale_families,
        min_group_sizes=min_group_sizes,
        min_group_size_default=min_group_size_default,
    )
    results = VariantResults()
    partition_cache: dict[
        tuple[str, str, int, str, int, float, int],
        tuple[pd.Series, pd.Series, dict[str, Any]],
    ] = {}

    _append_global_variant(data=data, results=results, alpha=alpha)
    _append_search_space_variants(
        data=data,
        results=results,
        partition_cache=partition_cache,
        space=space,
        alpha=alpha,
        collect_local_diagnostics=collect_local_diagnostics,
    )
    _append_cross_conformal_variant(
        data=data,
        results=results,
        alpha=alpha,
        cross_cal_sample_size=cross_cal_sample_size,
        cross_test_sample_size=cross_test_sample_size,
    )
    _append_selected_config_variant(
        data=data,
        results=results,
        partition_cache=partition_cache,
        selected_config_path=selected_config_path,
        alpha=alpha,
        min_group_size_default=min_group_size_default,
        collect_local_diagnostics=collect_local_diagnostics,
    )
    sensitivity_rows = _calibration_sensitivity_rows(data=data, space=space, alpha=alpha)
    bench, bench_by_group, temporal_diagnostics, local_diagnostics = _final_benchmark_frames(
        results=results,
        sensitivity_rows=sensitivity_rows,
        policy=policy,
    )

    output_paths = _build_output_paths(artifact_namespace)
    local_diagnostics = _append_selected_local_diagnostics(
        local_diagnostics=local_diagnostics,
        selected_config_path=selected_config_path,
        selected_intervals_path=output_paths["selected_intervals"],
    )
    status_payload = _selection_status_payload(
        bench=bench,
        output_paths=output_paths,
        artifact_namespace=artifact_namespace,
        calibrator_override_path=calibrator_override_path,
        policy_config_path=policy_config_path,
        collect_local_diagnostics=collect_local_diagnostics,
        space=space,
    )
    _write_benchmark_outputs(
        output_paths=output_paths,
        bench=bench,
        bench_by_group=bench_by_group,
        temporal_diagnostics=temporal_diagnostics,
        local_diagnostics=local_diagnostics,
        status_payload=status_payload,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--alpha", type=float, default=0.10)
    parser.add_argument("--selected_config_path", default="models/conformal_results_mondrian.pkl")
    parser.add_argument("--min_group_size_default", type=int, default=500)
    parser.add_argument("--cross_cal_sample_size", type=int, default=5000)
    parser.add_argument("--cross_test_sample_size", type=int, default=5000)
    parser.add_argument("--calibration_size_fractions", default="0.25,0.50,0.75,1.0")
    parser.add_argument(
        "--partition_candidates",
        default="grade,score_decile_mondrian,grade_x_scoreband_mondrian",
    )
    parser.add_argument("--partition_probability_sources", default="raw")
    parser.add_argument("--n_score_bins_candidates", default="10")
    parser.add_argument("--fallback_modes", default="grade_then_global")
    parser.add_argument("--score_scale_families", default="none,bernoulli_sqrt")
    parser.add_argument("--min_group_sizes", default=None)
    parser.add_argument("--artifact_namespace", default=None)
    parser.add_argument("--calibrator_override_path", default=None)
    parser.add_argument("--policy_config_path", default=DEFAULT_POLICY_CONFIG)
    parser.add_argument(
        "--collect_local_diagnostics",
        action="store_true",
        help=(
            "Persist row-level local diagnostics for every benchmark variant. "
            "Disabled by default because exhaustive searches can create tens of "
            "millions of diagnostic rows."
        ),
    )
    args = parser.parse_args()
    calibration_size_fractions = tuple(
        float(x.strip()) for x in str(args.calibration_size_fractions).split(",") if x.strip()
    )
    main(
        alpha=args.alpha,
        selected_config_path=args.selected_config_path,
        min_group_size_default=args.min_group_size_default,
        cross_cal_sample_size=args.cross_cal_sample_size,
        cross_test_sample_size=args.cross_test_sample_size,
        calibration_size_fractions=calibration_size_fractions,
        partition_candidates=_coerce_csv_tuple(args.partition_candidates, cast=str),
        partition_probability_sources=_coerce_csv_tuple(
            args.partition_probability_sources, cast=str
        ),
        n_score_bins_candidates=_coerce_csv_tuple(args.n_score_bins_candidates, cast=int),
        fallback_modes=_coerce_csv_tuple(args.fallback_modes, cast=str),
        score_scale_families=_coerce_csv_tuple(args.score_scale_families, cast=str),
        min_group_sizes=(
            _coerce_csv_tuple(args.min_group_sizes, cast=int)
            if args.min_group_sizes is not None
            else None
        ),
        artifact_namespace=args.artifact_namespace,
        calibrator_override_path=args.calibrator_override_path,
        policy_config_path=args.policy_config_path,
        collect_local_diagnostics=bool(args.collect_local_diagnostics),
    )
