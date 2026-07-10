"""Recompute the IJDS alpha grid from the frozen conformal recipe."""

from __future__ import annotations

import argparse
import hashlib
import os
import pickle
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.generate_conformal_intervals import (  # noqa: E402
    _build_probability_lookups,
    _build_tuning_split,
    _load_conformal_inputs,
)
from src.models.conformal import conditional_coverage_by_group  # noqa: E402
from src.models.conformal_alpha_grid import (  # noqa: E402
    ExactAlphaIntervals,
    FrozenConformalRecipe,
    alpha_interval_columns,
    compute_exact_alpha_intervals,
)
from src.utils.script_helpers import (  # noqa: E402
    ensure_contained_output_dir,
    resolve_repo_artifact_path,
    write_json,
)

DEFAULT_CONFIG = ROOT / "configs/experiments/champion_reopen_ijds_exact_alpha_grid_v1.yaml"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Experiment config must contain a mapping.")
    return payload


def _experiment_paths(run_tag: str) -> tuple[Path, Path]:
    data_dir = ensure_contained_output_dir(
        ROOT / "data/processed/experiments/champion_reopen", run_tag, "conformal"
    )
    model_dir = ensure_contained_output_dir(
        ROOT / "models/experiments/champion_reopen", run_tag, "conformal"
    )
    return data_dir, model_dir


def _load_results_payload(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        payload = pickle.load(handle)
    if not isinstance(payload, dict):
        raise TypeError("Frozen conformal results must contain a mapping.")
    return payload


def _coverage_summary(
    result: ExactAlphaIntervals,
    *,
    y_true: np.ndarray,
    grades: pd.Series,
) -> dict[str, Any]:
    covered = (y_true >= result.low) & (y_true <= result.high)
    partition_metrics = conditional_coverage_by_group(
        y_true,
        np.column_stack([result.low, result.high]),
        result.partition_labels,
    )
    grade_metrics = conditional_coverage_by_group(
        y_true,
        np.column_stack([result.low, result.high]),
        grades,
    )
    return {
        "target_alpha": result.target_alpha,
        "used_alpha": result.used_alpha,
        "target_coverage": 1.0 - result.target_alpha,
        "empirical_coverage": float(covered.mean()),
        "coverage_gap": float(covered.mean() - (1.0 - result.target_alpha)),
        "avg_width": float(np.mean(result.high - result.low)),
        "median_width": float(np.median(result.high - result.low)),
        "min_partition_coverage": float(partition_metrics["coverage"].min()),
        "min_grade_coverage": float(grade_metrics["coverage"].min()),
        "high_endpoint_mean": float(result.high.mean()),
        "high_endpoint_min": float(result.high.min()),
        "high_endpoint_p01": float(np.quantile(result.high, 0.01)),
        "high_endpoint_p10": float(np.quantile(result.high, 0.10)),
        "high_endpoint_at_one_rate": float(np.mean(result.high >= 1.0 - 1e-12)),
        "partition_count": int(result.partition_labels.nunique()),
        "group_quantiles": {
            str(key): float(value)
            for key, value in result.diagnostics.get("group_quantiles", {}).items()
        },
    }


def _base_grid_frame(source_intervals: pd.DataFrame) -> pd.DataFrame:
    preferred = [
        "_row_number",
        "id",
        "y_true",
        "grade",
        "loan_amnt",
        "temporal_segment",
    ]
    columns = [column for column in preferred if column in source_intervals.columns]
    return source_intervals.loc[:, columns].copy()


def _add_alpha_result(frame: pd.DataFrame, result: ExactAlphaIntervals) -> None:
    low_column, high_column = alpha_interval_columns(result.target_alpha)
    frame[low_column] = result.low
    frame[high_column] = result.high


def _replay_differences(
    result: ExactAlphaIntervals,
    source_intervals: pd.DataFrame,
) -> dict[str, float]:
    return {
        "point_max_abs": float(
            np.max(np.abs(result.point - source_intervals["y_pred"].to_numpy(dtype=float)))
        ),
        "low_max_abs": float(
            np.max(np.abs(result.low - source_intervals["pd_low_90"].to_numpy(dtype=float)))
        ),
        "high_max_abs": float(
            np.max(np.abs(result.high - source_intervals["pd_high_90"].to_numpy(dtype=float)))
        ),
    }


def run(config_path: Path) -> dict[str, Any]:
    config = _load_config(config_path)
    source = config["source"]
    design = config["design"]
    run_tag = str(config["run_tag"])
    results_path = resolve_repo_artifact_path(source["conformal_results_path"], root=ROOT)
    intervals_path = resolve_repo_artifact_path(source["conformal_intervals_path"], root=ROOT)
    os.environ["UPSTREAM_CANONICAL_RUN_TAG"] = str(source["upstream_canonical_run_tag"])

    results_payload = _load_results_payload(results_path)
    recipe = FrozenConformalRecipe.from_results_payload(results_payload)
    inputs = _load_conformal_inputs(
        calibration_fraction=recipe.calibration_fraction,
        calibrator_override_path=(
            str(results_payload.get("calibrator_override_path", "")).strip() or None
        ),
    )
    split = _build_tuning_split(
        cal_df=inputs.cal_df,
        test_df=inputs.test_df,
        X_cal=inputs.X_cal,
        y_cal=inputs.y_cal,
        group_cal_base=inputs.group_cal_base,
        y_prob_cal_raw=inputs.y_prob_cal_raw,
        tuning_holdout_ratio=recipe.tuning_holdout_ratio,
        tuning_random_state=recipe.tuning_random_state,
    )
    probability_fit, _probability_tune, probability_test = _build_probability_lookups(
        inputs,
        split,
    )
    source_intervals = pd.read_parquet(intervals_path)
    if len(source_intervals) != len(inputs.y_test):
        raise ValueError("Source conformal intervals and evaluation rows differ in length.")

    grid = _base_grid_frame(source_intervals)
    grid["y_pred"] = np.nan
    alpha_summaries: list[dict[str, Any]] = []
    results: dict[float, ExactAlphaIntervals] = {}
    for alpha in [float(value) for value in design["alpha_grid"]]:
        result = compute_exact_alpha_intervals(
            recipe=recipe,
            target_alpha=alpha,
            y_cal=split.y_cal_fit,
            interval_probability_cal=probability_fit["calibrated"],
            interval_probability_eval=probability_test["calibrated"],
            partition_probability_cal=probability_fit[recipe.partition_probability_source],
            partition_probability_eval=probability_test[recipe.partition_probability_source],
            base_groups_cal=split.group_cal_fit_base,
            base_groups_eval=inputs.group_test_base,
            issue_dates_eval=split.issue_test,
        )
        results[alpha] = result
        if grid["y_pred"].isna().all():
            grid["y_pred"] = result.point
        elif not np.array_equal(grid["y_pred"].to_numpy(dtype=float), result.point):
            raise AssertionError("Point predictions changed across alpha levels.")
        _add_alpha_result(grid, result)
        summary = _coverage_summary(
            result,
            y_true=inputs.y_test.to_numpy(dtype=float),
            grades=inputs.group_test_base.reset_index(drop=True),
        )
        alpha_summaries.append(summary)
        logger.info(
            "Exact alpha={:.3f} (used={:.4f}): coverage={:.4f}, width={:.4f}, high=1 rate={:.2%}",
            alpha,
            result.used_alpha,
            summary["empirical_coverage"],
            summary["avg_width"],
            summary["high_endpoint_at_one_rate"],
        )

    reference_alpha = recipe.reference_target_alpha
    reference_result = next(
        (result for alpha, result in results.items() if np.isclose(alpha, reference_alpha)),
        None,
    )
    if reference_result is None:
        raise ValueError("Alpha grid must contain the recipe reference target alpha.")
    replay = _replay_differences(reference_result, source_intervals)
    tolerance = float(design["replay_tolerance"])
    replay["tolerance"] = tolerance
    replay["pass"] = bool(max(replay.values()) <= tolerance)
    if not replay["pass"]:
        raise AssertionError(f"Frozen 90% interval replay drifted: {replay}")

    data_dir, model_dir = _experiment_paths(run_tag)
    grid_path = data_dir / "exact_alpha_grid.parquet"
    summary_path = model_dir / "exact_alpha_grid_summary.json"
    grid.to_parquet(grid_path, index=False)
    summary_payload: dict[str, Any] = {
        "schema_version": str(config["schema_version"]),
        "run_tag": run_tag,
        "config_path": str(config_path.relative_to(ROOT)),
        "config_sha256": _sha256(config_path),
        "source": {
            **source,
            "conformal_results_sha256": _sha256(results_path),
            "conformal_intervals_sha256": _sha256(intervals_path),
        },
        "recipe": asdict(recipe),
        "alpha_mapping": str(design["alpha_mapping"]),
        "reference_replay": replay,
        "alpha_summaries": alpha_summaries,
        "grid_path": str(grid_path.relative_to(ROOT)),
        "grid_rows": int(len(grid)),
        "claim_boundary": str(config["claim_boundary"]),
    }
    write_json(summary_path, summary_payload)
    logger.info("Wrote exact alpha grid to {}", grid_path)
    logger.info("Wrote exact alpha summary to {}", summary_path)
    return summary_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    run(config_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
