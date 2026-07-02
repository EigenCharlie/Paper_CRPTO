"""Run resumable CatBoost HPO for champion-reopen feature finalists.

This runner stays paper-facing by writing only experiment/search artifacts. It
reuses the exact TabPrep feature construction and feature-subset resolver used
by the seed replay, then mirrors each tuned candidate into ``models/search_pd``
so downstream conformal/portfolio scripts can consume it through
``UPSTREAM_CANONICAL_RUN_TAG`` without touching canonical artifacts.
"""

from __future__ import annotations

import argparse
import gc
import json
import shutil
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.experiments.run_tabprep_challenger import (  # noqa: E402
    _apply_calibrator,
    _build_fairness_report,
    _case_dir,
    _combine_features,
    _model_params,
    _prediction_frame,
    _prepare_catboost_frame,
    _resolve_sample_rows,
    _sample_split,
    _select_calibrator,
    _validate_output_roots,
)
from scripts.experiments.run_tabprep_feature_selection_catboost import (  # noqa: E402
    _build_case_features,
    _business_ranking,
    _feature_importance_frame,
    _load_config,
    _load_selector_rankings,
    _resolve_catboost_features,
    _resolve_core_features,
    _resolve_woe_features,
)
from src.evaluation.metrics import classification_metrics  # noqa: E402
from src.features.feature_config_io import load_feature_config  # noqa: E402
from src.features.feature_engineering import TARGET  # noqa: E402
from src.features.tabprep_challenger import (  # noqa: E402
    TabPrepChallengerTransformer,
    resolve_tabprep_categorical_features,
    resolve_tabprep_input_features,
    validate_no_forbidden_features,
)
from src.models.optuna_tuning import train_catboost_tuned_optuna  # noqa: E402
from src.models.pd_contract import build_contract_payload  # noqa: E402
from src.models.pd_model import temporal_train_val_split  # noqa: E402
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    atomic_write_pickle,
    write_runtime_checkpoint,
    write_runtime_status,
)

DEFAULT_HPO_CASES = [
    "pool93",
    "pool93_business80",
    "pool93_woe",
    "pooltop72_tab60",
    "pooltop80_tab90",
    "pooltop93_tab120",
    "pooltop80_business80",
    "pooltop72_business80",
]

DEFAULT_LOCAL_REFINE: dict[str, Any] = {
    "enqueue_base_trial": True,
    "fixed_params": {
        "bootstrap_type": "MVS",
        "grow_policy": "SymmetricTree",
    },
    "iterations": {"low": 2600, "high": 5400, "step": 100},
    "learning_rate": {"low": 0.012, "high": 0.075, "log": True},
    "depth": {"choices": [7, 8, 9, 10]},
    "l2_leaf_reg": {"low": 25.0, "high": 320.0, "log": True},
    "min_data_in_leaf": {"low": 80, "high": 340, "step": 5},
    "rsm": {"low": 0.50, "high": 0.92},
    "random_strength": {"low": 1.0e-9, "high": 0.005, "log": True},
    "border_count": {"choices": [128, 148, 192, 254]},
    "subsample": {"low": 0.60, "high": 0.93},
    "leaf_estimation_iterations": {"choices": [2, 3, 4, 5, 6]},
    "penalties_coefficient": [0.50, 0.75, 1.0, 1.25, 1.5],
    "feature_weights": {
        "loan_to_income": [1.0, 1.15, 1.30],
        "annual_inc": [1.0, 1.10, 1.20],
        "dti": [1.0, 1.10, 1.20],
        "installment_burden": [1.0, 1.10, 1.20],
        "fico_score": [1.0, 1.10, 1.20],
    },
    "first_feature_use_penalties": {
        "delinq_recency": [0.0, 0.20, 0.50],
        "recent_chargeoff": [0.0, 0.20, 0.50],
    },
}

INCUMBENT_ENQUEUE_TRIALS = [
    {
        "iterations": 3450,
        "learning_rate": 0.030590100735681216,
        "depth": 9,
        "l2_leaf_reg": 125.73596604846647,
        "min_data_in_leaf": 185,
        "rsm": 0.66554189303626,
        "random_strength": 1.7202215535069166e-06,
        "border_count": 148,
        "bootstrap_type": "MVS",
        "subsample": 0.771052860633893,
        "grow_policy": "SymmetricTree",
        "leaf_estimation_iterations": 3,
    },
    {
        "iterations": 4200,
        "learning_rate": 0.057321202729872456,
        "depth": 8,
        "l2_leaf_reg": 119.37272987133554,
        "min_data_in_leaf": 135,
        "rsm": 0.5716653769355704,
        "random_strength": 1.3208942645900998e-07,
        "border_count": 254,
        "bootstrap_type": "MVS",
        "subsample": 0.678878683066026,
        "grow_policy": "SymmetricTree",
        "leaf_estimation_iterations": 5,
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/experiments/champion_reopen.yaml")
    parser.add_argument("--run-tag", default="champion-reopen-2026-06-19__hpo-wave1")
    parser.add_argument("--cases", default="")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--tabprep-seed", type=int, default=42)
    parser.add_argument("--variant", default="balanced_1500")
    parser.add_argument(
        "--selector-model",
        default=(
            "models/experiments/tabprep/tabprep-catboost-full-2026-06-17/"
            "balanced_1500/seed_42/pd_tabprep_challenger.cbm"
        ),
    )
    parser.add_argument("--ranking-method", choices=["pvc", "shap_blend"], default="pvc")
    parser.add_argument("--shap-rows", type=int, default=30000)
    parser.add_argument("--n-trials", type=int, default=None)
    parser.add_argument("--timeout-minutes", type=int, default=None)
    parser.add_argument("--sample-rows", type=int, default=None)
    parser.add_argument("--full-data", action="store_true")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = _load_config(Path(args.config))
    hpo_cfg = _resolve_hpo_cfg(config, args=args)
    cases = _resolve_cases(config, args=args)
    sample_rows = 0 if args.full_data else _resolve_sample_rows(config, args.sample_rows)
    run_tag = str(args.run_tag)
    seed = int(args.seed)
    tabprep_seed = int(args.tabprep_seed)
    started = time.perf_counter()
    runtime_paths = _runtime_paths(config, run_tag=run_tag, seed=seed)
    _write_runtime(
        runtime_paths=runtime_paths,
        phase="start",
        state="running",
        run_tag=run_tag,
        extra={
            "seed": seed,
            "tabprep_seed": tabprep_seed,
            "variant": str(args.variant),
            "cases": cases,
            "sample_rows": sample_rows,
            "hpo": hpo_cfg,
        },
    )

    train = pd.read_parquet(config["data"]["train_path"])
    calibration = pd.read_parquet(config["data"]["calibration_path"])
    test = pd.read_parquet(config["data"]["test_path"])
    if sample_rows > 0:
        train = _sample_split(train, sample_rows=sample_rows, seed=seed)
        calibration = _sample_split(calibration, sample_rows=sample_rows, seed=seed)
        test = _sample_split(test, sample_rows=sample_rows, seed=seed)

    feature_config = load_feature_config(
        yaml_path=Path(config["data"]["feature_config_path"]),
        prefer="yaml",
    )
    pool_features = resolve_tabprep_input_features(
        train,
        feature_config=feature_config,
        extra_blacklist=config["tabprep"].get("extra_blacklist", []),
    )
    validate_no_forbidden_features(
        pool_features,
        extra_blacklist=config["tabprep"].get("extra_blacklist", []),
    )
    categorical_features = resolve_tabprep_categorical_features(
        pool_features,
        feature_config=feature_config,
    )
    core_features = _resolve_core_features(feature_config, train.columns)
    catboost_features = _resolve_catboost_features(feature_config, train.columns)
    woe_features = _resolve_woe_features(feature_config, train.columns)

    train_fit, train_val = temporal_train_val_split(
        train,
        val_fraction=float(config["validation"]["val_fraction"]),
        date_col=str(config["validation"]["date_col"]),
    )
    del train
    gc.collect()

    cache_payload = (
        _load_selected_tabprep_cache(
            config=config,
            run_tag=run_tag,
            seed=seed,
            tabprep_seed=tabprep_seed,
            variant=str(args.variant),
            sample_rows=sample_rows,
            cases=cases,
            expected_rows={
                "train_fit": len(train_fit),
                "train_val": len(train_val),
                "calibration": len(calibration),
                "test": len(test),
            },
        )
        if args.resume
        else None
    )
    if cache_payload is not None:
        logger.info(
            "Loaded selected TabPrep cache for {}: {} generated columns",
            run_tag,
            len(cache_payload["generated_features"]),
        )
        generated_train_fit = cache_payload["generated_train_fit"]
        generated_train_val = cache_payload["generated_train_val"]
        generated_calibration = cache_payload["generated_calibration"]
        generated_test = cache_payload["generated_test"]
        generated_features = cache_payload["generated_features"]
        case_features = cache_payload["case_features"]
    else:
        transformer = TabPrepChallengerTransformer(
            variant=str(args.variant),
            input_features=pool_features,
            categorical_features=categorical_features,
            target=TARGET,
            random_state=tabprep_seed,
            extra_blacklist=config["tabprep"].get("extra_blacklist", []),
        )
        logger.info("Fitting TabPrep {} once for HPO finalists", args.variant)
        generated_train_fit = transformer.fit_transform(
            train_fit,
            train_fit[TARGET].astype(int),
            issue_dates=train_fit.get(str(config["validation"]["date_col"])),
        )
        generated_train_val = transformer.transform(train_val)
        generated_calibration = transformer.transform(calibration)
        generated_test = transformer.transform(test)
        generated_features_full = list(generated_train_fit.columns)
        manifest = transformer.feature_manifest()

        pool_ranking, generated_ranking, ranking_diagnostics = _load_selector_rankings(
            selector_model_path=Path(args.selector_model),
            pool_features=pool_features,
            generated_features=generated_features_full,
            ranking_method=str(args.ranking_method),
            shap_rows=int(args.shap_rows),
            train_val=train_val,
            train_fit=train_fit,
            generated_train_val=generated_train_val,
            categorical_features=categorical_features,
        )
        business_ranking = _business_ranking(generated_ranking, manifest)
        case_features = _build_case_features(
            cases=cases,
            core_features=core_features,
            catboost_features=catboost_features,
            pool_features=pool_features,
            pool_ranking=pool_ranking,
            woe_features=woe_features,
            generated_ranking=generated_ranking,
            business_ranking=business_ranking,
        )
        _write_hpo_manifest(
            config=config,
            run_tag=run_tag,
            seed=seed,
            tabprep_seed=tabprep_seed,
            case_features=case_features,
            ranking_diagnostics=ranking_diagnostics,
            manifest=manifest,
            hpo_cfg=hpo_cfg,
        )
        selected_generated_features = _selected_generated_features(
            case_features=case_features,
            generated_features=generated_features_full,
        )
        generated_train_fit = generated_train_fit.loc[:, selected_generated_features].copy()
        generated_train_val = generated_train_val.loc[:, selected_generated_features].copy()
        generated_calibration = generated_calibration.loc[:, selected_generated_features].copy()
        generated_test = generated_test.loc[:, selected_generated_features].copy()
        generated_features = selected_generated_features
        _write_selected_tabprep_cache(
            config=config,
            run_tag=run_tag,
            seed=seed,
            tabprep_seed=tabprep_seed,
            variant=str(args.variant),
            sample_rows=sample_rows,
            cases=cases,
            case_features=case_features,
            generated_features=generated_features,
            matrices={
                "train_fit": generated_train_fit,
                "train_val": generated_train_val,
                "calibration": generated_calibration,
                "test": generated_test,
            },
        )
        gc.collect()

    results: list[dict[str, Any]] = []
    for case_name, feature_set in case_features.items():
        status_path = (
            _case_dir(
                Path(config["output"]["model_dir"]),
                run_tag=run_tag,
                case_name=case_name,
                seed=seed,
            )
            / "hpo_training_status.json"
        )
        if args.resume and status_path.exists():
            logger.info("Skipping {} because status exists: {}", case_name, status_path)
            results.append(json.loads(status_path.read_text(encoding="utf-8")))
            continue
        _write_runtime(
            runtime_paths=runtime_paths,
            phase="case_running",
            state="running",
            run_tag=run_tag,
            extra={
                "latest_case": case_name,
                "completed_cases": [row["case_name"] for row in results],
                "elapsed_seconds": time.perf_counter() - started,
            },
        )
        generated_subset = [feature for feature in feature_set if feature in generated_features]
        base_subset = [feature for feature in feature_set if feature not in generated_features]
        result = _run_hpo_case(
            case_name=case_name,
            run_tag=run_tag,
            seed=seed,
            tabprep_seed=tabprep_seed,
            config=config,
            hpo_cfg=hpo_cfg,
            train_fit=train_fit,
            train_val=train_val,
            calibration=calibration,
            test=test,
            base_features=base_subset,
            categorical_features=categorical_features,
            generated_train_fit=generated_train_fit[generated_subset],
            generated_train_val=generated_train_val[generated_subset],
            generated_calibration=generated_calibration[generated_subset],
            generated_test=generated_test[generated_subset],
            selection_sources={
                "core_features": core_features,
                "pool_features": pool_features,
                "woe_features": woe_features,
                "generated_features": generated_subset,
            },
        )
        results.append(result)
        _write_runtime(
            runtime_paths=runtime_paths,
            phase="case_complete",
            state="running",
            run_tag=run_tag,
            extra={
                "latest_case": case_name,
                "completed_cases": [row["case_name"] for row in results],
                "latest_auc": result.get("test_metrics", {}).get("auc_roc"),
                "best_auc": max(
                    float(row.get("test_metrics", {}).get("auc_roc", float("-inf")))
                    for row in results
                ),
                "elapsed_seconds": time.perf_counter() - started,
            },
        )
        gc.collect()

    summary_dir = _case_dir(
        Path(config["output"]["report_dir"]),
        run_tag=run_tag,
        case_name="summary",
        seed=seed,
    )
    summary = {
        "run_tag": run_tag,
        "seed": seed,
        "tabprep_seed": tabprep_seed,
        "elapsed_seconds": time.perf_counter() - started,
        "cases": list(case_features),
        "results": results,
    }
    atomic_write_json(summary_dir / "hpo_experiment_summary.json", _json_ready(summary))
    _write_checkpoint(
        runtime_paths=runtime_paths,
        checkpoint_name="summary",
        payload=summary,
    )
    _write_runtime(
        runtime_paths=runtime_paths,
        phase="complete",
        state="completed",
        run_tag=run_tag,
        extra={
            "elapsed_seconds": time.perf_counter() - started,
            "summary_path": str(summary_dir / "hpo_experiment_summary.json"),
            "completed_cases": [row["case_name"] for row in results],
        },
    )


def _resolve_cases(config: Mapping[str, Any], *, args: argparse.Namespace) -> list[str]:
    if str(args.cases).strip():
        return [case.strip() for case in str(args.cases).split(",") if case.strip()]
    configured = config.get("champion_reopen_hpo", {}).get("cases")
    if configured:
        return [str(case).strip() for case in configured if str(case).strip()]
    return list(DEFAULT_HPO_CASES)


def _resolve_hpo_cfg(config: Mapping[str, Any], *, args: argparse.Namespace) -> dict[str, Any]:
    raw = dict(config.get("champion_reopen_hpo", {}) or {})
    hpo = dict(raw.get("optuna", {}) or {})
    hpo.setdefault("n_trials", 180)
    hpo.setdefault("timeout_minutes", 0)
    hpo.setdefault("sampler", "tpe")
    hpo.setdefault("pruner", "median")
    hpo.setdefault("n_startup_trials", 40)
    hpo.setdefault("multivariate_tpe", True)
    hpo.setdefault("group_tpe", True)
    hpo.setdefault("constant_liar", True)
    hpo.setdefault("pruner_n_startup_trials", 20)
    hpo.setdefault("pruner_n_warmup_steps", 75)
    hpo.setdefault("use_pruning_callback", True)
    hpo.setdefault("load_if_exists", True)
    hpo.setdefault("refit_full_train", True)
    hpo.setdefault("gc_after_trial", True)
    hpo.setdefault("storage_heartbeat_interval", 60)
    hpo.setdefault("storage_grace_period", 240)
    hpo.setdefault("sqlite_timeout_seconds", 180)
    hpo.setdefault("retry_failed_trials", 2)
    hpo.setdefault("n_jobs", 1)
    hpo.setdefault("search_space_mode", "local_refine")
    hpo.setdefault("search_space_version", "cb_local_refine_champion_reopen_v1")
    hpo.setdefault("local_refine", DEFAULT_LOCAL_REFINE)
    hpo.setdefault(
        "constraints_policy",
        {
            "max_brier_delta": 0.001,
            "max_ece_delta": 0.0025,
            "min_auc_delta": -0.001,
        },
    )
    hpo.setdefault("enqueue_trials", INCUMBENT_ENQUEUE_TRIALS)
    if args.n_trials is not None:
        hpo["n_trials"] = int(args.n_trials)
    if args.timeout_minutes is not None:
        hpo["timeout_minutes"] = int(args.timeout_minutes)
    return hpo


def _runtime_paths(config: Mapping[str, Any], *, run_tag: str, seed: int) -> dict[str, Path]:
    model_dir = _case_dir(
        Path(config["output"]["model_dir"]),
        run_tag=run_tag,
        case_name="runtime",
        seed=seed,
    )
    _validate_output_roots([model_dir])
    return {
        "status": model_dir / "runtime_status.json",
        "checkpoints": model_dir / "checkpoints",
    }


def _write_runtime(
    *,
    runtime_paths: Mapping[str, Path],
    phase: str,
    state: str,
    run_tag: str,
    extra: Mapping[str, Any] | None = None,
) -> None:
    write_runtime_status(
        "champion_reopen_hpo",
        phase=phase,
        state=state,
        run_tag=run_tag,
        status_path=runtime_paths["status"],
        extra=_json_ready(dict(extra or {})),
    )


def _write_checkpoint(
    *,
    runtime_paths: Mapping[str, Path],
    checkpoint_name: str,
    payload: Mapping[str, Any],
) -> None:
    write_runtime_checkpoint(
        "champion_reopen_hpo",
        checkpoint_name,
        _json_ready(dict(payload)),
        checkpoint_dir=runtime_paths["checkpoints"],
    )


def _selected_generated_features(
    *,
    case_features: Mapping[str, Sequence[str]],
    generated_features: Sequence[str],
) -> list[str]:
    generated_set = set(map(str, generated_features))
    selected = {
        str(feature)
        for features in case_features.values()
        for feature in features
        if str(feature) in generated_set
    }
    return [feature for feature in generated_features if feature in selected]


def _tabprep_cache_dir(config: Mapping[str, Any], *, run_tag: str, seed: int) -> Path:
    cache_dir = _case_dir(
        Path(config["output"]["data_dir"]),
        run_tag=run_tag,
        case_name="tabprep_selected_cache",
        seed=seed,
    )
    _validate_output_roots([cache_dir])
    return cache_dir


def _tabprep_cache_paths(config: Mapping[str, Any], *, run_tag: str, seed: int) -> dict[str, Path]:
    cache_dir = _tabprep_cache_dir(config, run_tag=run_tag, seed=seed)
    return {
        "dir": cache_dir,
        "meta": cache_dir / "cache_meta.json",
        "train_fit": cache_dir / "generated_train_fit.parquet",
        "train_val": cache_dir / "generated_train_val.parquet",
        "calibration": cache_dir / "generated_calibration.parquet",
        "test": cache_dir / "generated_test.parquet",
    }


def _cache_signature(
    *,
    run_tag: str,
    seed: int,
    tabprep_seed: int,
    variant: str,
    sample_rows: int,
    cases: Sequence[str],
) -> dict[str, Any]:
    return {
        "run_tag": str(run_tag),
        "seed": int(seed),
        "tabprep_seed": int(tabprep_seed),
        "variant": str(variant),
        "sample_rows": int(sample_rows),
        "cases": [str(case) for case in cases],
    }


def _load_selected_tabprep_cache(
    *,
    config: Mapping[str, Any],
    run_tag: str,
    seed: int,
    tabprep_seed: int,
    variant: str,
    sample_rows: int,
    cases: Sequence[str],
    expected_rows: Mapping[str, int],
) -> dict[str, Any] | None:
    paths = _tabprep_cache_paths(config, run_tag=run_tag, seed=seed)
    required = [paths[key] for key in ["meta", "train_fit", "train_val", "calibration", "test"]]
    if not all(path.exists() for path in required):
        return None
    try:
        meta = json.loads(paths["meta"].read_text(encoding="utf-8"))
        expected = _cache_signature(
            run_tag=run_tag,
            seed=seed,
            tabprep_seed=tabprep_seed,
            variant=variant,
            sample_rows=sample_rows,
            cases=cases,
        )
        for key, value in expected.items():
            if meta.get(key) != value:
                logger.warning(
                    "Ignoring selected TabPrep cache because {} differs: cached={} expected={}",
                    key,
                    meta.get(key),
                    value,
                )
                return None
        matrices = {
            split: pd.read_parquet(paths[split])
            for split in ["train_fit", "train_val", "calibration", "test"]
        }
        row_counts = {split: len(frame) for split, frame in matrices.items()}
        for split, expected_count in expected_rows.items():
            if int(row_counts.get(split, -1)) != int(expected_count):
                logger.warning(
                    "Ignoring selected TabPrep cache because {} rows differ: cached={} expected={}",
                    split,
                    row_counts.get(split),
                    expected_count,
                )
                return None
        generated_features = [str(feature) for feature in meta.get("generated_features", [])]
        case_features = {
            str(case): [str(feature) for feature in features]
            for case, features in dict(meta.get("case_features", {}) or {}).items()
        }
        if not generated_features and any(
            feature.startswith("tabprep__")
            for features in case_features.values()
            for feature in features
        ):
            return None
        return {
            "generated_train_fit": matrices["train_fit"],
            "generated_train_val": matrices["train_val"],
            "generated_calibration": matrices["calibration"],
            "generated_test": matrices["test"],
            "generated_features": generated_features,
            "case_features": case_features,
            "meta": meta,
        }
    except Exception as exc:
        logger.warning("Failed to load selected TabPrep cache; recomputing. reason={}", exc)
        return None


def _write_selected_tabprep_cache(
    *,
    config: Mapping[str, Any],
    run_tag: str,
    seed: int,
    tabprep_seed: int,
    variant: str,
    sample_rows: int,
    cases: Sequence[str],
    case_features: Mapping[str, Sequence[str]],
    generated_features: Sequence[str],
    matrices: Mapping[str, pd.DataFrame],
) -> None:
    paths = _tabprep_cache_paths(config, run_tag=run_tag, seed=seed)
    logger.info(
        "Writing selected TabPrep cache for {} with {} generated columns",
        run_tag,
        len(generated_features),
    )
    for split in ["train_fit", "train_val", "calibration", "test"]:
        atomic_write_parquet(matrices[split], paths[split], index=False)
    meta = {
        **_cache_signature(
            run_tag=run_tag,
            seed=seed,
            tabprep_seed=tabprep_seed,
            variant=variant,
            sample_rows=sample_rows,
            cases=cases,
        ),
        "generated_features": [str(feature) for feature in generated_features],
        "n_generated_features": int(len(generated_features)),
        "case_features": {
            str(case): [str(feature) for feature in features]
            for case, features in case_features.items()
        },
        "row_counts": {split: int(len(frame)) for split, frame in matrices.items()},
        "paths": {key: str(path) for key, path in paths.items() if key != "dir"},
    }
    atomic_write_json(paths["meta"], _json_ready(meta))


def _run_hpo_case(
    *,
    case_name: str,
    run_tag: str,
    seed: int,
    tabprep_seed: int,
    config: Mapping[str, Any],
    hpo_cfg: Mapping[str, Any],
    train_fit: pd.DataFrame,
    train_val: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    base_features: Sequence[str],
    categorical_features: Sequence[str],
    generated_train_fit: pd.DataFrame,
    generated_train_val: pd.DataFrame,
    generated_calibration: pd.DataFrame,
    generated_test: pd.DataFrame,
    selection_sources: Mapping[str, Any],
) -> dict[str, Any]:
    model_dir = _case_dir(
        Path(config["output"]["model_dir"]), run_tag=run_tag, case_name=case_name, seed=seed
    )
    data_dir = _case_dir(
        Path(config["output"]["data_dir"]), run_tag=run_tag, case_name=case_name, seed=seed
    )
    report_dir = _case_dir(
        Path(config["output"]["report_dir"]), run_tag=run_tag, case_name=case_name, seed=seed
    )
    _validate_output_roots([model_dir, data_dir, report_dir])

    generated_features = list(generated_train_fit.columns)
    model_features = [*base_features, *generated_features]
    cat_features = [feature for feature in categorical_features if feature in model_features]

    x_train = _combine_features(train_fit, base_features, generated_train_fit)
    x_val = _combine_features(train_val, base_features, generated_train_val)
    x_cal = _combine_features(calibration, base_features, generated_calibration)
    x_test = _combine_features(test, base_features, generated_test)

    x_train_cb = _prepare_catboost_frame(x_train, model_features, cat_features)
    x_val_cb = _prepare_catboost_frame(x_val, model_features, cat_features)
    x_cal_cb = _prepare_catboost_frame(x_cal, model_features, cat_features)
    x_test_cb = _prepare_catboost_frame(x_test, model_features, cat_features)

    params = _model_params(config, model_features=model_features, seed=seed)
    storage_db = (model_dir / "optuna_study.db").resolve()
    storage_db.parent.mkdir(parents=True, exist_ok=True)
    study_storage = f"sqlite:///{storage_db.as_posix()}"
    study_name = f"champion_reopen_hpo_{case_name}_seed{seed}"
    model, train_metrics = train_catboost_tuned_optuna(
        x_train_cb,
        train_fit[TARGET].astype(int),
        x_val_cb,
        train_val[TARGET].astype(int),
        X_test=x_test_cb,
        y_test=test[TARGET].astype(int),
        cat_features=cat_features,
        base_params=params,
        n_trials=int(hpo_cfg["n_trials"]),
        sampler=str(hpo_cfg["sampler"]),
        pruner=str(hpo_cfg["pruner"]),
        timeout_minutes=int(hpo_cfg["timeout_minutes"]),
        n_startup_trials=int(hpo_cfg["n_startup_trials"]),
        multivariate_tpe=bool(hpo_cfg["multivariate_tpe"]),
        group_tpe=bool(hpo_cfg["group_tpe"]),
        constant_liar=bool(hpo_cfg["constant_liar"]),
        pruner_n_startup_trials=int(hpo_cfg["pruner_n_startup_trials"]),
        pruner_n_warmup_steps=int(hpo_cfg["pruner_n_warmup_steps"]),
        use_pruning_callback=bool(hpo_cfg["use_pruning_callback"]),
        study_storage=study_storage,
        study_name=study_name,
        load_if_exists=bool(hpo_cfg["load_if_exists"]),
        refit_full_train=bool(hpo_cfg["refit_full_train"]),
        gc_after_trial=bool(hpo_cfg["gc_after_trial"]),
        storage_heartbeat_interval=int(hpo_cfg["storage_heartbeat_interval"]),
        storage_grace_period=int(hpo_cfg["storage_grace_period"]),
        sqlite_timeout_seconds=int(hpo_cfg["sqlite_timeout_seconds"]),
        retry_failed_trials=int(hpo_cfg["retry_failed_trials"]),
        n_jobs=int(hpo_cfg["n_jobs"]),
        search_space_mode=str(hpo_cfg["search_space_mode"]),
        local_refine_space=dict(hpo_cfg["local_refine"]),
        constraints_policy=dict(hpo_cfg["constraints_policy"]),
        search_space_version=str(hpo_cfg["search_space_version"]),
        enqueue_trials=list(hpo_cfg["enqueue_trials"]),
    )

    raw_cal = model.predict_proba(x_cal_cb)[:, 1]
    raw_test = model.predict_proba(x_test_cb)[:, 1]
    calibrator, calibration_report = _select_calibrator(
        method=str(config["calibration"]["method"]),
        candidates=[str(item) for item in config["calibration"]["candidates"]],
        y_cal=calibration[TARGET].astype(int).to_numpy(),
        raw_cal=raw_cal,
    )
    calibrated_test = np.asarray(_apply_calibrator(calibrator, raw_test), dtype=float)
    calibrated_cal = np.asarray(_apply_calibrator(calibrator, raw_cal), dtype=float)
    test_metrics = classification_metrics(test[TARGET].astype(int).to_numpy(), calibrated_test)
    cal_metrics = classification_metrics(
        calibration[TARGET].astype(int).to_numpy(),
        calibrated_cal,
    )
    fairness = _build_fairness_report(test, y_prob=calibrated_test, config=config)

    model_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    model_path = model_dir / "pd_selected_tabprep_hpo.cbm"
    calibrator_path = model_dir / "pd_selected_tabprep_hpo_calibrator.pkl"
    prediction_path = data_dir / "test_predictions.parquet"
    status_path = model_dir / "hpo_training_status.json"
    model.save_model(str(model_path))
    atomic_write_pickle(calibrator_path, calibrator)
    predictions = _prediction_frame(
        test,
        raw_prob=raw_test,
        calibrated_prob=calibrated_test,
        case_name=case_name,
        seed=seed,
    )
    atomic_write_parquet(predictions, prediction_path)
    if not fairness.empty:
        atomic_write_parquet(fairness, report_dir / "fairness_report.parquet")
    atomic_write_parquet(
        _feature_importance_frame(model), report_dir / "feature_importance.parquet"
    )

    candidate_run_tag = _candidate_run_tag(run_tag=run_tag, case_name=case_name, seed=seed)
    search_pd_dir = Path("models/search_pd") / candidate_run_tag
    search_data_dir = Path("data/processed/search_pd") / candidate_run_tag
    search_pd_dir.mkdir(parents=True, exist_ok=True)
    search_data_dir.mkdir(parents=True, exist_ok=True)
    candidate_model_path = search_pd_dir / "pd_candidate_model.cbm"
    candidate_calibrator_path = search_pd_dir / "pd_candidate_calibrator.pkl"
    shutil.copy2(model_path, candidate_model_path)
    shutil.copy2(model_path, search_pd_dir / "pd_local_hpo_tuned.cbm")
    shutil.copy2(calibrator_path, candidate_calibrator_path)
    shutil.copy2(calibrator_path, search_pd_dir / "pd_local_hpo_calibrator.pkl")

    calibration_matrix_path = search_data_dir / "calibration_model_matrix.parquet"
    test_matrix_path = search_data_dir / "test_model_matrix.parquet"
    atomic_write_parquet(
        _matrix_with_identity(x_cal_cb, calibration),
        calibration_matrix_path,
        index=False,
    )
    atomic_write_parquet(
        _matrix_with_identity(x_test_cb, test),
        test_matrix_path,
        index=False,
    )
    atomic_write_parquet(predictions, search_data_dir / "test_predictions.parquet")
    contract = build_contract_payload(
        model_path=candidate_model_path,
        calibrator_path=candidate_calibrator_path,
        feature_names=list(model_features),
        categorical_features=list(cat_features),
        split_shapes={
            "train_fit": tuple(x_train_cb.shape),
            "train_val": tuple(x_val_cb.shape),
            "calibration": tuple(x_cal_cb.shape),
            "test": tuple(x_test_cb.shape),
        },
    )
    contract["run_tag"] = candidate_run_tag
    contract["source_experiment_run_tag"] = run_tag
    contract["case_name"] = case_name
    contract["seed"] = int(seed)
    contract["tabprep_seed"] = int(tabprep_seed)
    contract["model_matrix_paths"] = {
        "calibration": str(calibration_matrix_path),
        "test": str(test_matrix_path),
    }
    atomic_write_json(search_pd_dir / "pd_model_contract.json", _json_ready(contract))

    status = {
        "run_tag": run_tag,
        "candidate_run_tag": candidate_run_tag,
        "case_name": case_name,
        "seed": seed,
        "tabprep_seed": tabprep_seed,
        "model_path": str(model_path),
        "calibrator_path": str(calibrator_path),
        "prediction_path": str(prediction_path),
        "search_pd_dir": str(search_pd_dir),
        "search_data_dir": str(search_data_dir),
        "upstream_canonical_run_tag": candidate_run_tag,
        "n_base_features": len(base_features),
        "n_generated_features": len(generated_features),
        "n_model_features": len(model_features),
        "categorical_features": cat_features,
        "generated_features": generated_features,
        "training_metrics": train_metrics,
        "test_metrics": test_metrics,
        "calibration_metrics": cal_metrics,
        "calibration_selection": calibration_report,
        "selection_sources": selection_sources,
        "optuna_storage": study_storage,
        "optuna_study_name": study_name,
        "hpo": dict(hpo_cfg),
    }
    atomic_write_json(status_path, _json_ready(status))
    atomic_write_json(search_pd_dir / "pd_training_status.json", _json_ready(status))
    logger.info(
        "{} HPO seed {} done: test AUC={:.6f}, Brier={:.6f}, ECE={:.6f}, features={} generated={}",
        case_name,
        seed,
        test_metrics["auc_roc"],
        test_metrics["brier_score"],
        test_metrics["ece"],
        len(model_features),
        len(generated_features),
    )
    return status


def _matrix_with_identity(matrix: pd.DataFrame, source: pd.DataFrame) -> pd.DataFrame:
    out = matrix.reset_index(drop=True).copy()
    source_reset = source.reset_index(drop=True)
    for col in ["id", "issue_d", "grade", TARGET]:
        if col in source_reset.columns and col not in out.columns:
            out[col] = source_reset[col].to_numpy()
    return out


def _candidate_run_tag(*, run_tag: str, case_name: str, seed: int) -> str:
    raw = f"{run_tag}__{case_name}__seed{int(seed)}"
    return raw.replace("/", "_").replace(" ", "_")


def _write_hpo_manifest(
    *,
    config: Mapping[str, Any],
    run_tag: str,
    seed: int,
    tabprep_seed: int,
    case_features: Mapping[str, Sequence[str]],
    ranking_diagnostics: pd.DataFrame,
    manifest: pd.DataFrame,
    hpo_cfg: Mapping[str, Any],
) -> None:
    report_dir = _case_dir(
        Path(config["output"]["report_dir"]),
        run_tag=run_tag,
        case_name="hpo_manifest",
        seed=seed,
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        report_dir / "hpo_manifest.json",
        _json_ready(
            {
                "run_tag": run_tag,
                "seed": seed,
                "tabprep_seed": tabprep_seed,
                "cases": {name: list(features) for name, features in case_features.items()},
                "hpo": dict(hpo_cfg),
            }
        ),
    )
    if not ranking_diagnostics.empty:
        atomic_write_parquet(ranking_diagnostics, report_dir / "pool_ranking_diagnostics.parquet")
    atomic_write_parquet(manifest, report_dir / "generated_feature_manifest.parquet")


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return [_json_ready(item) for item in value.tolist()]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


if __name__ == "__main__":
    main()
