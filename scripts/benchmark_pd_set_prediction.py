"""Benchmark binary conformal prediction sets for PD ambiguity/abstention analysis."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from scripts.generate_conformal_intervals import (
    _build_feature_matrix,
    _load_calibrator,
    _load_model,
    _resolve_features,
    _subset_calibration_frame,
)
from src.models.conformal import (
    apply_probability_calibrator,
    build_mondrian_partition_labels,
    create_classification_sets,
    create_classification_sets_mondrian,
    summarize_prediction_sets,
)
from src.utils.io_utils import read_with_fallback

TARGET_COL = "default_flag"
GROUP_COL = "grade"


@dataclass(frozen=True)
class SetBenchmarkData:
    model: Any
    calibrator: Any | None
    calibrator_name: str
    cal_df: pd.DataFrame
    test_df: pd.DataFrame
    features: list[str]
    categorical: list[str]
    X_cal: pd.DataFrame
    y_cal: pd.Series
    X_test: pd.DataFrame
    y_test: pd.Series
    group_cal: pd.Series
    group_test: pd.Series
    prob_cal_lookup: dict[str, np.ndarray]
    prob_test_lookup: dict[str, np.ndarray]


@dataclass(frozen=True)
class SetBenchmarkSettings:
    alpha: float
    methods: tuple[str, ...]
    partitions: tuple[str, ...]
    partition_probability_source: str
    n_score_bins: int
    min_group_size: int
    requested_fallback_mode: str
    effective_fallback_mode: str
    calibration_size_fractions: tuple[float, ...]


@dataclass(frozen=True)
class VariantPrediction:
    method: str
    partition: str
    y_pred: np.ndarray
    y_sets: np.ndarray


def _build_output_paths(namespace: str | None = None) -> dict[str, Path]:
    if namespace:
        ns = str(namespace).strip().replace("/", "_")
        data_dir = Path("data/processed/conformal_gap") / ns
        model_dir = Path("models/conformal_gap") / ns
    else:
        data_dir = Path("data/processed")
        model_dir = Path("models")
    data_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    return {
        "cases": data_dir / "pd_set_prediction_cases.parquet",
        "by_slice": data_dir / "pd_set_prediction_by_slice.parquet",
        "sensitivity": data_dir / "pd_set_prediction_sensitivity.parquet",
        "benchmark": data_dir / "pd_set_prediction_benchmark.parquet",
        "status": model_dir / "pd_set_prediction_status.json",
    }


def _build_paths(namespace: str | None = None) -> dict[str, Path]:
    return _build_output_paths(namespace)


def _slice_summary(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    work = frame.loc[frame[column].notna()].copy()
    if work.empty:
        return pd.DataFrame()
    work[column] = work[column].astype(str)
    summary = (
        work.groupby(column, observed=True)
        .agg(
            n_obs=("y_true", "size"),
            set_coverage=("covered", "mean"),
            singleton_rate=("singleton", "mean"),
            ambiguity_rate=("ambiguous", "mean"),
            empty_set_rate=("empty_set", "mean"),
            default_rate=("y_true", "mean"),
        )
        .reset_index()
        .rename(columns={column: "slice_value"})
    )
    ambiguous_rates = (
        work.loc[work["ambiguous"] == 1]
        .groupby(column, observed=True)["y_true"]
        .mean()
        .rename("default_rate_ambiguous")
        .reset_index()
        .rename(columns={column: "slice_value"})
    )
    summary = summary.merge(ambiguous_rates, on="slice_value", how="left")
    summary.insert(0, "slice_name", column)
    return summary


def _rank_variant(row: pd.Series) -> tuple[float, float, float, float]:
    return (
        float(row.get("set_coverage", 0.0)),
        float(row.get("singleton_rate", 0.0)),
        -float(row.get("ambiguity_rate", 1.0)),
        -float(row.get("empty_set_rate", 1.0)),
    )


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


def _normalize_sidecar_fallback_mode(fallback_mode: str) -> str:
    mode = str(fallback_mode or "grade_then_global").strip().lower()
    if mode in {"grade_then_global", "global_only"}:
        return mode
    if mode == "score_only":
        logger.warning(
            "Sidecar fallback_mode=score_only is not supported for hybrid set partitions; "
            "using global_only instead."
        )
        return "global_only"
    logger.warning("Unknown sidecar fallback_mode={!r}; using grade_then_global.", fallback_mode)
    return "grade_then_global"


def _unique_csv_values(values: tuple[str, ...], fallback: tuple[str, ...]) -> tuple[str, ...]:
    cleaned = tuple(dict.fromkeys(str(x).strip() for x in values if str(x).strip()))
    return cleaned or fallback


def _valid_calibration_fractions(values: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(float(x) for x in values if 0 < float(x) <= 1)


def _calibrator_name(calibrator: Any | None, calibrator_override_path: str | None) -> str:
    if calibrator_override_path:
        return Path(str(calibrator_override_path)).stem
    if calibrator is not None:
        return type(calibrator).__name__
    return "raw"


def _load_set_benchmark_data(calibrator_override_path: str | None) -> SetBenchmarkData:
    model, _ = _load_model()
    calibrator = _load_calibrator(calibrator_override_path)
    cal_df = read_with_fallback(
        "data/processed/calibration_fe.parquet", "data/processed/calibration.parquet"
    )
    test_df = read_with_fallback("data/processed/test_fe.parquet", "data/processed/test.parquet")
    features, categorical = _resolve_features(model, cal_df, test_df)
    X_cal = _build_feature_matrix(cal_df, features, categorical)
    y_cal = cal_df[TARGET_COL].astype(int).reset_index(drop=True)
    X_test = _build_feature_matrix(test_df, features, categorical)
    y_test = test_df[TARGET_COL].astype(int).reset_index(drop=True)
    group_cal = cal_df[GROUP_COL].fillna("UNKNOWN").astype(str).reset_index(drop=True)
    group_test = test_df[GROUP_COL].fillna("UNKNOWN").astype(str).reset_index(drop=True)
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
    return SetBenchmarkData(
        model=model,
        calibrator=calibrator,
        calibrator_name=_calibrator_name(calibrator, calibrator_override_path),
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
        prob_cal_lookup={"raw": y_prob_cal_raw, "calibrated": y_prob_calibrated},
        prob_test_lookup={"raw": y_prob_test_raw, "calibrated": y_prob_test_calibrated},
    )


def _set_benchmark_settings(
    *,
    alpha: float,
    method: str,
    methods: tuple[str, ...] | None,
    partitions: tuple[str, ...],
    partition_probability_source: str,
    n_score_bins: int,
    min_group_size: int,
    fallback_mode: str,
    calibration_size_fractions: tuple[float, ...],
    prob_cal_lookup: dict[str, np.ndarray],
) -> SetBenchmarkSettings:
    source = str(partition_probability_source).strip().lower() or "raw"
    if source not in prob_cal_lookup:
        raise ValueError(f"Unsupported partition_probability_source: {source}")
    return SetBenchmarkSettings(
        alpha=float(alpha),
        methods=_unique_csv_values(methods or (method,), ("lac",)),
        partitions=_unique_csv_values(partitions, ("global",)),
        partition_probability_source=source,
        n_score_bins=int(n_score_bins),
        min_group_size=int(min_group_size),
        requested_fallback_mode=str(fallback_mode),
        effective_fallback_mode=_normalize_sidecar_fallback_mode(fallback_mode),
        calibration_size_fractions=_valid_calibration_fractions(calibration_size_fractions),
    )


def _make_cases(
    *,
    y_true: pd.Series,
    y_pred: np.ndarray,
    y_sets: np.ndarray,
    test_df: pd.DataFrame,
    method: str,
    partition: str,
    partition_probability_source: str,
    calibrator_name: str,
) -> pd.DataFrame:
    cases = pd.DataFrame(
        {
            "y_true": y_true.to_numpy(dtype=int),
            "y_pred_label": np.asarray(y_pred, dtype=int),
            "set_contains_0": y_sets[:, 0].astype(int),
            "set_contains_1": y_sets[:, 1].astype(int),
            "set_size": y_sets.sum(axis=1).astype(int),
            "ambiguous": (y_sets.sum(axis=1) > 1).astype(int),
            "singleton": (y_sets.sum(axis=1) == 1).astype(int),
            "empty_set": (y_sets.sum(axis=1) == 0).astype(int),
            "method": str(method),
            "partition": str(partition),
            "partition_probability_source": str(partition_probability_source),
            "calibrator": str(calibrator_name),
        }
    )
    cases["covered"] = y_sets[np.arange(len(y_true)), y_true.to_numpy(dtype=int)].astype(int)
    for col in ("grade", "term", "home_ownership", "issue_d"):
        if col in test_df.columns:
            cases[col] = test_df[col].reset_index(drop=True)
    if "id" in test_df.columns:
        cases["id"] = test_df["id"].astype(str).reset_index(drop=True)
    elif "loan_id" in test_df.columns:
        cases["loan_id"] = test_df["loan_id"].astype(str).reset_index(drop=True)
    if "issue_d" in cases.columns:
        cases["issue_quarter"] = (
            pd.to_datetime(cases["issue_d"], errors="coerce").dt.to_period("Q").astype(str)
        )
    return cases


def _is_global_partition(partition: str) -> bool:
    return str(partition).strip().lower() == "global"


def _predict_variant(
    *,
    data: SetBenchmarkData,
    settings: SetBenchmarkSettings,
    method_name: str,
    partition_name: str,
    X_cal: pd.DataFrame,
    y_cal: pd.Series,
    group_cal: pd.Series,
    y_prob_cal: np.ndarray,
) -> VariantPrediction:
    if _is_global_partition(partition_name):
        y_pred, y_sets = create_classification_sets(
            classifier=data.model,
            X_cal=X_cal,
            y_cal=y_cal,
            X_test=data.X_test,
            alpha=settings.alpha,
            method=method_name,
            calibrator=data.calibrator,
        )
        return VariantPrediction(
            method=str(method_name),
            partition=str(partition_name),
            y_pred=y_pred,
            y_sets=y_sets,
        )

    group_cal_part, group_test_part, partition_meta = build_mondrian_partition_labels(
        y_prob_cal=y_prob_cal,
        y_prob_eval=data.prob_test_lookup[settings.partition_probability_source],
        partition=partition_name,
        base_groups_cal=group_cal,
        base_groups_eval=data.group_test,
        n_score_bins=settings.n_score_bins,
        min_group_size=settings.min_group_size,
        fallback_mode=settings.effective_fallback_mode,
    )
    y_pred, y_sets, _ = create_classification_sets_mondrian(
        classifier=data.model,
        X_cal=X_cal,
        y_cal=y_cal,
        X_test=data.X_test,
        group_cal=group_cal_part,
        group_test=group_test_part,
        alpha=settings.alpha,
        method=method_name,
        min_group_size=settings.min_group_size,
        calibrator=data.calibrator,
    )
    return VariantPrediction(
        method=str(method_name),
        partition=str(partition_meta.get("partition", partition_name)),
        y_pred=y_pred,
        y_sets=y_sets,
    )


def _benchmark_row(
    *,
    data: SetBenchmarkData,
    settings: SetBenchmarkSettings,
    prediction: VariantPrediction,
) -> dict[str, Any]:
    summary = summarize_prediction_sets(
        data.y_test.to_numpy(), prediction.y_pred, prediction.y_sets
    )
    return {
        "method": prediction.method,
        "partition": prediction.partition,
        "partition_probability_source": settings.partition_probability_source,
        "calibrator": data.calibrator_name,
        "alpha": settings.alpha,
        **{k: float(v) for k, v in summary.items()},
    }


def _subsample_calibration_data(
    *,
    data: SetBenchmarkData,
    calibration_fraction: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, np.ndarray, np.ndarray]:
    cal_df_sub = _subset_calibration_frame(data.cal_df, calibration_fraction=calibration_fraction)
    X_cal_sub = _build_feature_matrix(cal_df_sub, data.features, data.categorical)
    y_cal_sub = cal_df_sub[TARGET_COL].astype(int).reset_index(drop=True)
    group_cal_sub = cal_df_sub[GROUP_COL].fillna("UNKNOWN").astype(str).reset_index(drop=True)
    y_prob_cal_sub_raw = data.model.predict_proba(X_cal_sub)[:, 1]
    y_prob_cal_sub_calibrated = (
        apply_probability_calibrator(data.calibrator, y_prob_cal_sub_raw)
        if data.calibrator is not None
        else np.asarray(y_prob_cal_sub_raw, dtype=float)
    )
    return (
        cal_df_sub,
        X_cal_sub,
        y_cal_sub,
        group_cal_sub,
        y_prob_cal_sub_raw,
        y_prob_cal_sub_calibrated,
    )


def _sensitivity_row(
    *,
    data: SetBenchmarkData,
    settings: SetBenchmarkSettings,
    method_name: str,
    partition_name: str,
    calibration_fraction: float,
) -> dict[str, Any]:
    _cal_df_sub, X_cal_sub, y_cal_sub, group_cal_sub, y_prob_raw, y_prob_calibrated = (
        _subsample_calibration_data(data=data, calibration_fraction=calibration_fraction)
    )
    y_prob_cal = y_prob_raw if settings.partition_probability_source == "raw" else y_prob_calibrated
    prediction = _predict_variant(
        data=data,
        settings=settings,
        method_name=method_name,
        partition_name=partition_name,
        X_cal=X_cal_sub,
        y_cal=y_cal_sub,
        group_cal=group_cal_sub,
        y_prob_cal=y_prob_cal,
    )
    summary_sub = summarize_prediction_sets(
        data.y_test.to_numpy(), prediction.y_pred, prediction.y_sets
    )
    return {
        "method": str(method_name),
        "partition": str(prediction.partition),
        "partition_probability_source": settings.partition_probability_source,
        "calibrator": data.calibrator_name,
        "calibration_fraction": float(calibration_fraction),
        "n_calibration_rows": int(len(X_cal_sub)),
        "set_coverage": float(summary_sub["set_coverage"]),
        "singleton_rate": float(summary_sub["singleton_rate"]),
        "ambiguity_rate": float(summary_sub["ambiguity_rate"]),
        "empty_set_rate": float(summary_sub["empty_set_rate"]),
        "default_rate_ambiguous": float(summary_sub["default_rate_ambiguous"]),
    }


def _sensitivity_rows_for_variant(
    *,
    data: SetBenchmarkData,
    settings: SetBenchmarkSettings,
    method_name: str,
    partition_name: str,
) -> list[dict[str, Any]]:
    return [
        _sensitivity_row(
            data=data,
            settings=settings,
            method_name=method_name,
            partition_name=partition_name,
            calibration_fraction=float(frac),
        )
        for frac in settings.calibration_size_fractions
    ]


def _run_benchmark_matrix(
    *,
    data: SetBenchmarkData,
    settings: SetBenchmarkSettings,
) -> tuple[
    pd.DataFrame,
    dict[tuple[str, str], pd.DataFrame],
    dict[tuple[str, str], list[dict[str, Any]]],
]:
    benchmark_rows: list[dict[str, Any]] = []
    cases_by_variant: dict[tuple[str, str], pd.DataFrame] = {}
    sensitivity_by_variant: dict[tuple[str, str], list[dict[str, Any]]] = {}

    for method_name in settings.methods:
        for partition_name in settings.partitions:
            prediction = _predict_variant(
                data=data,
                settings=settings,
                method_name=method_name,
                partition_name=partition_name,
                X_cal=data.X_cal,
                y_cal=data.y_cal,
                group_cal=data.group_cal,
                y_prob_cal=data.prob_cal_lookup[settings.partition_probability_source],
            )
            benchmark_rows.append(
                _benchmark_row(data=data, settings=settings, prediction=prediction)
            )
            key = (prediction.method, prediction.partition)
            cases_by_variant[key] = _make_cases(
                y_true=data.y_test,
                y_pred=prediction.y_pred,
                y_sets=prediction.y_sets,
                test_df=data.test_df,
                method=prediction.method,
                partition=prediction.partition,
                partition_probability_source=settings.partition_probability_source,
                calibrator_name=data.calibrator_name,
            )
            sensitivity_by_variant[key] = _sensitivity_rows_for_variant(
                data=data,
                settings=settings,
                method_name=method_name,
                partition_name=prediction.partition,
            )

    benchmark_df = pd.DataFrame(benchmark_rows)
    if benchmark_df.empty:
        raise RuntimeError("No set-prediction variants were benchmarked.")
    return (
        benchmark_df.sort_values(
            by=["set_coverage", "singleton_rate", "ambiguity_rate", "empty_set_rate"],
            ascending=[False, False, True, True],
        ).reset_index(drop=True),
        cases_by_variant,
        sensitivity_by_variant,
    )


def _slice_reports(cases: pd.DataFrame) -> pd.DataFrame:
    slice_reports = []
    for col in ("grade", "term", "issue_quarter"):
        if col in cases.columns:
            report = _slice_summary(cases, col)
            if not report.empty:
                slice_reports.append(report)
    return pd.concat(slice_reports, ignore_index=True) if slice_reports else pd.DataFrame()


def _grade_slices(by_slice: pd.DataFrame) -> list[dict[str, Any]]:
    if by_slice.empty or "slice_name" not in by_slice.columns:
        return []
    return by_slice.loc[by_slice["slice_name"] == "grade"].to_dict(orient="records")


def _slice_records(by_slice: pd.DataFrame, slice_name: str) -> list[dict[str, Any]]:
    if by_slice.empty or "slice_name" not in by_slice.columns:
        return []
    return by_slice.loc[by_slice["slice_name"] == slice_name].to_dict(orient="records")


def _promotion_gate(summary: dict[str, Any], grade_slices: list[dict[str, Any]]) -> dict[str, Any]:
    gate_coverage = float(summary.get("set_coverage", 0))
    gate_grade_a_singleton = 0.0
    gate_grades_above_40 = 0
    for gs in grade_slices:
        singleton_rate = float(gs.get("singleton_rate", 0))
        if str(gs.get("slice_value", "")) == "A":
            gate_grade_a_singleton = singleton_rate
        if singleton_rate > 0.40:
            gate_grades_above_40 += 1
    gate_pass = bool(
        gate_coverage >= 0.85 and gate_grade_a_singleton >= 0.80 and gate_grades_above_40 >= 3
    )
    return {
        "coverage": gate_coverage,
        "min_coverage": 0.85,
        "grade_a_singleton_rate": gate_grade_a_singleton,
        "min_grade_a_singleton": 0.80,
        "grades_with_singleton_above_40pct": gate_grades_above_40,
        "min_grades_above_40pct": 3,
        "pass": gate_pass,
    }


def _selected_summary(cases: pd.DataFrame) -> dict[str, float]:
    return {
        k: float(v)
        for k, v in summarize_prediction_sets(
            cases["y_true"].to_numpy(dtype=int),
            cases["y_pred_label"].to_numpy(dtype=int),
            cases[["set_contains_0", "set_contains_1"]].to_numpy(dtype=int),
        ).items()
    }


def _status_payload(
    *,
    settings: SetBenchmarkSettings,
    selected: pd.Series,
    summary: dict[str, float],
    gate: dict[str, Any],
    by_slice: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    outputs: dict[str, Path],
    artifact_namespace: str | None,
) -> dict[str, Any]:
    gate_pass = bool(gate["pass"])
    promotion_status = "promoted_guardrail" if gate_pass else "research_sidecar"
    return {
        "schema_version": "2026-04-03.1",
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "run_tag": os.environ.get("PIPELINE_RUN_TAG", "untracked"),
        "artifact_namespace": artifact_namespace or "",
        "status": promotion_status,
        "promoted": gate_pass,
        "method": str(selected["method"]),
        "selected_method": str(selected["method"]),
        "selected_partition": str(selected["partition"]),
        "selected_partition_probability_source": str(selected["partition_probability_source"]),
        "selected_calibrator": str(selected["calibrator"]),
        "requested_fallback_mode": settings.requested_fallback_mode,
        "effective_fallback_mode": settings.effective_fallback_mode,
        "alpha": settings.alpha,
        "confidence_level": float(1.0 - settings.alpha),
        "summary": summary,
        "promotion_gate": gate,
        "artifact_path": str(outputs["cases"]),
        "by_slice_path": str(outputs["by_slice"]),
        "calibration_size_sensitivity_path": str(outputs["sensitivity"]),
        "benchmark_matrix_path": str(outputs["benchmark"]),
        "slice_metrics": {
            "grade": _grade_slices(by_slice),
            "term": _slice_records(by_slice, "term"),
            "issue_quarter": _slice_records(by_slice, "issue_quarter"),
        },
        "benchmark_matrix": benchmark_df.to_dict(orient="records"),
        "decision_use_case": {
            "probability_first": True,
            "set_first": False,
            "recommended_guardrail": "selective_ambiguity_defer",
        },
        "promotion_rationale": (
            f"Binary conformal sets selected via {selected['method']} + {selected['partition']} "
            f"with set coverage {gate['coverage']:.1%} and ambiguity {summary['ambiguity_rate']:.1%}."
        ),
        "promotion_note": (
            "Binary set prediction remains a sidecar triage/abstention signal; it does not replace "
            "the interval-first conformal stack."
        ),
    }


def _write_outputs(
    *,
    outputs: dict[str, Path],
    cases: pd.DataFrame,
    by_slice: pd.DataFrame,
    sensitivity_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    status: dict[str, Any],
) -> None:
    cases.to_parquet(outputs["cases"], index=False)
    if not by_slice.empty:
        by_slice.to_parquet(outputs["by_slice"], index=False)
    sensitivity_df.to_parquet(outputs["sensitivity"], index=False)
    benchmark_df.to_parquet(outputs["benchmark"], index=False)
    outputs["status"].write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    logger.info("Saved PD set prediction cases: {}", outputs["cases"])
    logger.info("Saved PD set prediction status: {}", outputs["status"])


def main(
    alpha: float = 0.10,
    method: str = "lac",
    methods: tuple[str, ...] | None = None,
    partitions: tuple[str, ...] = ("global",),
    partition_probability_source: str = "raw",
    n_score_bins: int = 10,
    min_group_size: int = 500,
    fallback_mode: str = "grade_then_global",
    calibration_size_fractions: tuple[float, ...] = (0.25, 0.50, 0.75, 1.0),
    artifact_namespace: str | None = None,
    calibrator_override_path: str | None = None,
) -> None:
    data = _load_set_benchmark_data(calibrator_override_path)
    settings = _set_benchmark_settings(
        alpha=alpha,
        method=method,
        methods=methods,
        partitions=partitions,
        partition_probability_source=partition_probability_source,
        n_score_bins=n_score_bins,
        min_group_size=min_group_size,
        fallback_mode=fallback_mode,
        calibration_size_fractions=calibration_size_fractions,
        prob_cal_lookup=data.prob_cal_lookup,
    )
    benchmark_df, cases_by_variant, sensitivity_by_variant = _run_benchmark_matrix(
        data=data,
        settings=settings,
    )
    selected = benchmark_df.iloc[0]
    selected_key = (str(selected["method"]), str(selected["partition"]))
    cases = cases_by_variant[selected_key]
    by_slice = _slice_reports(cases)
    sensitivity_df = pd.DataFrame(sensitivity_by_variant[selected_key])
    summary = _selected_summary(cases)
    gate = _promotion_gate(summary, _grade_slices(by_slice))
    outputs = _build_output_paths(artifact_namespace)
    status = _status_payload(
        settings=settings,
        selected=selected,
        summary=summary,
        gate=gate,
        by_slice=by_slice,
        benchmark_df=benchmark_df,
        outputs=outputs,
        artifact_namespace=artifact_namespace,
    )
    _write_outputs(
        outputs=outputs,
        cases=cases,
        by_slice=by_slice,
        sensitivity_df=sensitivity_df,
        benchmark_df=benchmark_df,
        status=status,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--alpha", type=float, default=0.10)
    parser.add_argument("--method", default="lac")
    parser.add_argument("--methods", default=None)
    parser.add_argument("--partitions", default="global")
    parser.add_argument("--partition_probability_source", default="raw")
    parser.add_argument("--n_score_bins", type=int, default=10)
    parser.add_argument("--min_group_size", type=int, default=500)
    parser.add_argument("--fallback_mode", default="grade_then_global")
    parser.add_argument("--calibration-size-fractions", default="0.25,0.50,0.75,1.0")
    parser.add_argument("--artifact_namespace", default=None)
    parser.add_argument("--calibrator_override_path", default=None)
    args = parser.parse_args()
    main(
        alpha=args.alpha,
        method=args.method,
        methods=_coerce_csv_tuple(args.methods, cast=str) if args.methods else None,
        partitions=_coerce_csv_tuple(args.partitions, cast=str),
        partition_probability_source=args.partition_probability_source,
        n_score_bins=args.n_score_bins,
        min_group_size=args.min_group_size,
        fallback_mode=args.fallback_mode,
        calibration_size_fractions=tuple(
            float(x.strip()) for x in str(args.calibration_size_fractions).split(",") if x.strip()
        ),
        artifact_namespace=args.artifact_namespace,
        calibrator_override_path=args.calibrator_override_path,
    )
