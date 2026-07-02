"""Run a full-data TabPFN-3 + TabPrep challenger.

The script is intentionally isolated from DVC and champion artifacts. It fails
before heavy CRPTO data work if TabPFN-3 model access has not been authorized.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml
from loguru import logger
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.evaluation.metrics import classification_metrics  # noqa: E402
from src.features.feature_config_io import load_feature_config  # noqa: E402
from src.features.feature_engineering import TARGET  # noqa: E402
from src.features.tabprep_challenger import (  # noqa: E402
    TABPREP_VARIANTS,
    TabPrepChallengerTransformer,
    TabPrepVariantConfig,
    resolve_tabprep_categorical_features,
    resolve_tabprep_input_features,
    validate_no_forbidden_features,
)
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    atomic_write_pickle,
)

ALLOWED_OUTPUT_PREFIXES = {
    Path("data/processed/experiments/tabpfn_tabprep"),
    Path("models/experiments/tabpfn_tabprep"),
    Path("reports/crpto/experiments/tabpfn_tabprep"),
}
PROTECTED_PATHS = {
    Path("models/pd_canonical.cbm"),
    Path("models/pd_canonical_calibrator.pkl"),
    Path("models/conformal_policy_status.json"),
    Path("data/processed/conformal_intervals_mondrian.parquet"),
    Path("EXTRACTION_MANIFEST.json"),
}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/experiments/tabpfn_tabprep_full.yaml",
        help="Path to the TabPFN + TabPrep experiment config.",
    )
    parser.add_argument(
        "--access-check-only",
        action="store_true",
        help="Only verify TabPFN-3 model access and CUDA setup.",
    )
    parser.add_argument(
        "--force-outside-limits",
        action="store_true",
        help="Proceed even though full CRPTO exceeds public TabPFN-3 recommended limits.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the full-data experiment or fail with a concrete blocking reason."""
    args = parse_args()
    config = _load_config(Path(args.config))
    _check_tabpfn_access(config)
    if args.access_check_only:
        logger.info("TabPFN access check passed.")
        return

    _preflight_dataset_limits(config=config, force=args.force_outside_limits)
    run_tag = str(config["run_tag"])
    data_dir = Path(config["output"]["data_dir"]) / run_tag
    model_dir = Path(config["output"]["model_dir"]) / run_tag
    report_dir = Path(config["output"]["report_dir"]) / run_tag
    _validate_output_roots([data_dir, model_dir, report_dir])

    started = time.perf_counter()
    train = pd.read_parquet(config["data"]["train_path"])
    feature_config = load_feature_config(
        yaml_path=Path(config["data"]["feature_config_path"]),
        prefer="yaml",
    )
    base_features = resolve_tabprep_input_features(
        train,
        feature_config=feature_config,
        extra_blacklist=config["tabprep"].get("extra_blacklist", []),
    )
    validate_no_forbidden_features(
        base_features,
        extra_blacklist=config["tabprep"].get("extra_blacklist", []),
    )
    categorical_features = resolve_tabprep_categorical_features(
        base_features,
        feature_config=feature_config,
    )
    categorical_maps = _fit_category_maps(train, categorical_features)
    max_features = int(config["tabprep"]["max_tabpfn_features"])
    variant = _resolve_tabprep_variant_for_tabpfn(
        str(config["tabprep"]["variant"]),
        max_generated=max(0, max_features - len(base_features)),
    )
    transformer = TabPrepChallengerTransformer(
        variant=variant,
        input_features=base_features,
        categorical_features=categorical_features,
        target=TARGET,
        random_state=42,
        extra_blacklist=config["tabprep"].get("extra_blacklist", []),
    )
    logger.info("Fitting TabPrep {} on full train rows={:,}", variant.name, len(train))
    generated_train = transformer.fit_transform(
        train,
        train[TARGET].astype(int),
        issue_dates=train.get("issue_d"),
    )
    generated_features = transformer.generated_features_[
        : max(0, max_features - len(base_features))
    ]
    model_features = [*base_features, *generated_features]
    generated_train = generated_train[generated_features]
    x_train = _combine_features(
        train,
        generated_train,
        model_features,
        categorical_maps=categorical_maps,
    )
    y_train = train[TARGET].astype(int).to_numpy()
    train_rows = len(x_train)
    encoded_categorical_indices = [
        idx for idx, feature in enumerate(model_features) if feature in categorical_features
    ]
    use_native_categoricals = bool(config["tabpfn"].get("use_native_categorical_features", False))
    categorical_indices = encoded_categorical_indices if use_native_categoricals else []

    atomic_write_parquet(
        transformer.feature_manifest(), report_dir / "generated_feature_manifest.parquet"
    )
    atomic_write_json(
        report_dir / "pre_tabpfn_matrix_status.json",
        {
            "run_tag": run_tag,
            "rows": {
                "train": int(train_rows),
                "calibration": None,
                "test": None,
            },
            "n_base_features": len(base_features),
            "n_generated_features": len(generated_features),
            "n_model_features": len(model_features),
            "n_encoded_categorical_features": len(encoded_categorical_indices),
            "n_native_categorical_features": len(categorical_indices),
            "use_native_categorical_features": use_native_categoricals,
            "matrix_dtype": str(x_train.dtype),
            "matrix_gb": {
                "train": _array_gb(x_train),
                "calibration": None,
                "test": None,
            },
        },
    )

    del train, generated_train
    gc.collect()

    from tabpfn import TabPFNClassifier

    clf = TabPFNClassifier(
        n_estimators=int(config["tabpfn"]["n_estimators"]),
        categorical_features_indices=categorical_indices,
        device=str(config["tabpfn"]["device"]),
        ignore_pretraining_limits=bool(config["tabpfn"]["ignore_pretraining_limits"]),
        inference_precision=config["tabpfn"]["inference_precision"],
        fit_mode=str(config["tabpfn"]["fit_mode"]),
        memory_saving_mode=config["tabpfn"]["memory_saving_mode"],
        keep_cache_on_device=bool(config["tabpfn"]["keep_cache_on_device"]),
        n_preprocessing_jobs=int(config["tabpfn"]["n_preprocessing_jobs"]),
        inference_config=dict(config["tabpfn"].get("inference_config") or {}),
        show_progress_bar=bool(config["tabpfn"]["show_progress_bar"]),
        random_state=42,
    )
    logger.info(
        "Fitting TabPFN on full matrix rows={:,}, features={:,}, native_categorical={}",
        len(x_train),
        len(model_features),
        len(categorical_indices),
    )
    clf.fit(x_train, y_train)
    del x_train, y_train
    gc.collect()

    chunk_rows = int(config["tabpfn"]["prediction_chunk_rows"])
    calibration = pd.read_parquet(config["data"]["calibration_path"])
    generated_cal = transformer.transform(calibration)[generated_features]
    x_cal = _combine_features(
        calibration,
        generated_cal,
        model_features,
        categorical_maps=categorical_maps,
    )
    y_cal = calibration[TARGET].astype(int).to_numpy()
    cal_rows = len(x_cal)
    raw_cal = _predict_proba_chunks(clf, x_cal, chunk_rows=chunk_rows)
    calibrator = _fit_platt(y_cal, raw_cal)
    del calibration, generated_cal, x_cal, y_cal, raw_cal
    gc.collect()

    test = pd.read_parquet(config["data"]["test_path"])
    generated_test = transformer.transform(test)[generated_features]
    x_test = _combine_features(
        test,
        generated_test,
        model_features,
        categorical_maps=categorical_maps,
    )
    y_test = test[TARGET].astype(int).to_numpy()
    test_rows = len(x_test)
    raw_test = _predict_proba_chunks(clf, x_test, chunk_rows=chunk_rows)
    calibrated_test = calibrator.predict_proba(raw_test.reshape(-1, 1))[:, 1]

    metrics = classification_metrics(y_test, calibrated_test)
    raw_metrics = {
        "auc_roc": float(roc_auc_score(y_test, raw_test)),
        "brier_score": float(brier_score_loss(y_test, raw_test)),
        "log_loss": float(log_loss(y_test, raw_test)),
    }
    predictions = _prediction_frame(test, raw_prob=raw_test, calibrated_prob=calibrated_test)
    atomic_write_parquet(predictions, data_dir / "test_predictions.parquet")
    classifier_path = None
    if bool(config["output"].get("save_classifier_pickle", False)):
        classifier_path = model_dir / "tabpfn_classifier.pkl"
        atomic_write_pickle(classifier_path, clf)
    atomic_write_pickle(model_dir / "tabpfn_platt_calibrator.pkl", calibrator)
    status = {
        "run_tag": run_tag,
        "elapsed_seconds": time.perf_counter() - started,
        "rows": {
            "train": train_rows,
            "calibration": cal_rows,
            "test": test_rows,
        },
        "n_base_features": len(base_features),
        "n_generated_features": len(generated_features),
        "n_model_features": len(model_features),
        "categorical_features": categorical_features,
        "encoded_categorical_indices": encoded_categorical_indices,
        "native_categorical_indices": categorical_indices,
        "use_native_categorical_features": use_native_categoricals,
        "raw_test_metrics": raw_metrics,
        "calibrated_test_metrics": metrics,
        "classifier_path": str(classifier_path) if classifier_path is not None else None,
        "tabpfn_config": config["tabpfn"],
        "tabprep_summary": transformer.state_summary(),
    }
    atomic_write_json(model_dir / "tabpfn_tabprep_status.json", status)
    logger.info(
        "TabPFN + TabPrep done: calibrated AUC={:.6f}, Brier={:.6f}",
        metrics["auc_roc"],
        metrics["brier_score"],
    )


def _load_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise TypeError(f"Config must be a mapping: {path}")
    _validate_output_roots(_output_path_values(config["output"]))
    return config


def _check_tabpfn_access(config: Mapping[str, Any]) -> None:
    """Fail before loading CRPTO data if TabPFN-3 weights are not accessible."""
    from sklearn.datasets import make_classification
    from tabpfn import TabPFNClassifier

    x, y = make_classification(n_samples=80, n_features=8, random_state=42)
    clf = TabPFNClassifier(
        n_estimators=1,
        device=str(config["tabpfn"]["device"]),
        ignore_pretraining_limits=True,
        fit_mode="low_memory",
        memory_saving_mode=True,
        keep_cache_on_device=False,
        show_progress_bar=False,
        random_state=42,
    )
    try:
        clf.fit(x[:40], y[:40])
        clf.predict_proba(x[40:45])
    except Exception as exc:
        token_set = bool(os.getenv("TABPFN_TOKEN"))
        raise RuntimeError(
            "TabPFN-3 model access failed before CRPTO data loading. "
            f"TABPFN_TOKEN set={token_set}. Accept the PriorLabs license and set "
            "TABPFN_TOKEN, then rerun this script."
        ) from exc


def _preflight_dataset_limits(*, config: Mapping[str, Any], force: bool) -> None:
    """Check full-data shape against public TabPFN-3 limits."""
    parquet_file = pq.ParquetFile(config["data"]["train_path"])
    train_rows = int(parquet_file.metadata.num_rows)
    schema_columns = list(parquet_file.schema_arrow.names)
    schema_frame = pd.DataFrame(columns=schema_columns)
    feature_config = load_feature_config(
        yaml_path=Path(config["data"]["feature_config_path"]),
        prefer="yaml",
    )
    base_feature_count = len(
        resolve_tabprep_input_features(
            schema_frame,
            feature_config=feature_config,
            extra_blacklist=config["tabprep"].get("extra_blacklist", []),
        )
    )
    max_features = int(config["tabprep"]["max_tabpfn_features"])
    cells = train_rows * max_features
    status = {
        "train_rows": train_rows,
        "base_feature_count_head_resolved": base_feature_count,
        "max_tabpfn_features": max_features,
        "train_cells": cells,
        "public_recommended_rows_at_200_features": 1_000_000,
        "public_recommended_rows_at_2000_features": 100_000,
        "outside_public_recommended_limits": train_rows > 1_000_000 or max_features > 2_000,
    }
    logger.info("TabPFN full-data preflight: {}", json.dumps(status, sort_keys=True))
    if status["outside_public_recommended_limits"] and not force:
        raise RuntimeError(
            "Full CRPTO + TabPrep is outside public TabPFN-3 limits. "
            "Rerun with --force-outside-limits to attempt it anyway."
        )


def _resolve_tabprep_variant_for_tabpfn(name: str, *, max_generated: int) -> TabPrepVariantConfig:
    base = TABPREP_VARIANTS[name]
    if max_generated >= base.max_generated_features:
        return base
    scale = max_generated / max(base.max_generated_features, 1)
    return TabPrepVariantConfig(
        name=f"{base.name}_tabpfn_cap_{max_generated}",
        max_generated_features=max_generated,
        arithmetic_features=max(0, int(round(base.arithmetic_features * scale))),
        groupby_features=max(0, int(round(base.groupby_features * scale))),
        target_encoding_features=max(0, int(round(base.target_encoding_features * scale))),
        interaction_encoding_features=max(
            0, int(round(base.interaction_encoding_features * scale))
        ),
        rsfc_features=max(0, int(round(base.rsfc_features * scale))),
        max_numeric_base_features=base.max_numeric_base_features,
        max_groupby_numeric_features=base.max_groupby_numeric_features,
        max_categorical_base_features=base.max_categorical_base_features,
        max_scoring_rows=base.max_scoring_rows,
        n_oof_folds=base.n_oof_folds,
        smoothing=base.smoothing,
        min_group_support=base.min_group_support,
        rsfc_candidate_multiplier=base.rsfc_candidate_multiplier,
    )


def _combine_features(
    frame: pd.DataFrame,
    generated: pd.DataFrame,
    model_features: Sequence[str],
    *,
    categorical_maps: Mapping[str, Mapping[str, int]],
) -> np.ndarray:
    matrix = np.empty((len(frame), len(model_features)), dtype=np.float32)
    generated_columns = set(generated.columns)
    for idx, feature in enumerate(model_features):
        if feature in generated_columns:
            values = generated[feature]
        elif feature in categorical_maps:
            values = _apply_category_map(frame[feature], categorical_maps[feature])
        else:
            values = pd.to_numeric(frame[feature], errors="coerce")
        matrix[:, idx] = pd.Series(values).to_numpy(dtype=np.float32, na_value=np.nan)
    return matrix


def _fit_category_maps(
    frame: pd.DataFrame,
    categorical_features: Sequence[str],
) -> dict[str, dict[str, int]]:
    maps: dict[str, dict[str, int]] = {}
    for feature in categorical_features:
        if feature not in frame.columns:
            continue
        values = _normalized_category_series(frame[feature])
        categories = pd.Index(values.dropna().unique()).sort_values()
        maps[feature] = {str(category): idx for idx, category in enumerate(categories)}
    return maps


def _apply_category_map(
    series: pd.Series,
    category_map: Mapping[str, int],
) -> pd.Series:
    values = _normalized_category_series(series)
    return values.map(category_map).fillna(-1).astype("float32")


def _normalized_category_series(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("__MISSING__")


def _array_gb(array: np.ndarray) -> float:
    return float(array.nbytes / (1024**3))


def _predict_proba_chunks(model: Any, frame: np.ndarray, *, chunk_rows: int) -> np.ndarray:
    chunks: list[np.ndarray] = []
    for start in range(0, len(frame), chunk_rows):
        stop = min(start + chunk_rows, len(frame))
        logger.info("Predicting TabPFN rows {:,}-{:,} / {:,}", start, stop, len(frame))
        chunks.append(model.predict_proba(frame[start:stop])[:, 1].astype("float32"))
    return np.concatenate(chunks)


def _fit_platt(y_true: np.ndarray, raw_prob: np.ndarray) -> LogisticRegression:
    calibrator = LogisticRegression(max_iter=1000)
    calibrator.fit(raw_prob.reshape(-1, 1), y_true)
    return calibrator


def _prediction_frame(
    frame: pd.DataFrame,
    *,
    raw_prob: np.ndarray,
    calibrated_prob: np.ndarray,
) -> pd.DataFrame:
    cols = [col for col in ["id", "issue_d", TARGET] if col in frame.columns]
    out = frame[cols].copy()
    out["pd_raw_tabpfn_tabprep"] = raw_prob
    out["pd_calibrated_tabpfn_tabprep"] = calibrated_prob
    return out


def _validate_output_roots(paths: Iterable[Any]) -> None:
    for raw_path in paths:
        _assert_isolated_output(Path(raw_path))


def _output_path_values(output_cfg: Mapping[str, Any]) -> list[Any]:
    return [value for key, value in output_cfg.items() if key.endswith(("_dir", "_path", "_root"))]


def _assert_isolated_output(path: Path) -> None:
    normalized = _normalize_repo_path(path)
    if normalized in PROTECTED_PATHS:
        raise ValueError(f"Refusing to write protected artifact: {path}")
    if not any(_is_relative_to(normalized, allowed) for allowed in ALLOWED_OUTPUT_PREFIXES):
        raise ValueError(
            "TabPFN + TabPrep outputs must stay under "
            f"{sorted(str(root) for root in ALLOWED_OUTPUT_PREFIXES)}; got {path}"
        )


def _normalize_repo_path(path: Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        try:
            return Path(path.relative_to(Path.cwd()).as_posix())
        except ValueError:
            return path
    return Path(path.as_posix())


def _is_relative_to(path: Path | str, parent: Path) -> bool:
    try:
        Path(path).relative_to(parent)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    main()
