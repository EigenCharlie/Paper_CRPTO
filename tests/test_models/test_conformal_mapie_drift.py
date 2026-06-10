"""Champion conformal drift harness (Track B gate).

Recomputes the frozen champion conformal intervals from scratch under the
CURRENT dependency stack (MAPIE 1.x runtime, current numpy/pandas/catboost/
sklearn) using the exact frozen recipe recorded in
``models/conformal_results_mondrian.pkl``, and compares against the frozen
``data/processed/conformal_intervals_mondrian.parquet``.

This is the acceptance gate of ``docs/refactor/MAPIE_MIGRATION_PLAN.md``:

* per-loan max abs diff on y_pred / interval endpoints <= 1e-6
* per-Mondrian-cell coverage delta <= 5e-4

It does NOT rerun any protected DVC stage and writes nothing; it is a pure
in-memory recomputation. Marked ``slow`` because it scores ~514k rows with
the champion CatBoost model twice (calibration + test).

GATE STATUS (2026-06-09): RED, by a known cause documented in
``docs/refactor/drift_report_mapie_2026-06.md``. The frozen intervals were
produced by the April search candidate
(``models/search_pd/pd-hpo-local-2026-04-03-1325/pd_candidate_model.cbm``,
recorded in the frozen results pkl and not present in the local checkout),
while ``models/pd_canonical.cbm`` is the June ``ijds-rebaseline-2026-06-07``
retrain of the same config — similar (corr 0.9917) but not bit-exact. The
drift is therefore upstream of the conformal layer and unrelated to MAPIE.
Because the gate is expected to fail until the April binary is restored or a
new run-tag re-promotes the chain, the harness only runs when explicitly
requested::

    CRPTO_RUN_CHAMPION_DRIFT=1 uv run pytest \
        tests/test_models/test_conformal_mapie_drift.py -q -s
"""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]

if os.getenv("CRPTO_RUN_CHAMPION_DRIFT", "").lower() not in {"1", "true", "yes"}:
    pytest.skip(
        "Champion drift harness is opt-in (set CRPTO_RUN_CHAMPION_DRIFT=1). "
        "Known-red gate: see docs/refactor/drift_report_mapie_2026-06.md.",
        allow_module_level=True,
    )

FROZEN_INTERVALS_PATH = ROOT / "data" / "processed" / "conformal_intervals_mondrian.parquet"
FROZEN_RESULTS_PATH = ROOT / "models" / "conformal_results_mondrian.pkl"
REQUIRED_ARTIFACTS = (
    FROZEN_INTERVALS_PATH,
    FROZEN_RESULTS_PATH,
    ROOT / "models" / "pd_canonical.cbm",
    ROOT / "models" / "pd_canonical_calibrator.pkl",
    ROOT / "data" / "processed" / "calibration_fe.parquet",
    ROOT / "data" / "processed" / "test_fe.parquet",
)

MAX_ABS_ENDPOINT_DIFF = 1e-6
MAX_CELL_COVERAGE_DELTA = 5e-4

pytestmark = pytest.mark.slow


def _require_artifacts() -> None:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED_ARTIFACTS if not p.is_file()]
    if missing:
        pytest.skip(f"Frozen artifacts not available locally (run `dvc pull`): {missing}")


@pytest.fixture(scope="module")
def frozen() -> dict[str, Any]:
    _require_artifacts()
    with FROZEN_RESULTS_PATH.open("rb") as fh:
        results = pickle.load(fh)
    intervals = pd.read_parquet(FROZEN_INTERVALS_PATH)
    return {"results": results, "intervals": intervals}


@pytest.fixture(scope="module")
def recomputed(frozen: dict[str, Any]) -> dict[str, Any]:
    """Recompute the frozen interval table from the recorded recipe."""
    from scripts.generate_conformal_intervals import (
        GROUP_COL,
        TARGET_COL,
        _build_feature_matrix,
        _load_calibrator,
        _load_model,
        _resolve_features,
    )
    from src.models.conformal import (
        apply_probability_calibrator,
        build_mondrian_partition_labels,
        create_pd_intervals_mondrian,
    )
    from src.models.conformal_tuning import (
        apply_group_multipliers,
        split_calibration_for_tuning,
    )
    from src.utils.io_utils import read_with_fallback

    results = frozen["results"]
    best_cfg = results["tuning_90_best"]

    # Preconditions: the harness reproduces exactly the frozen post-processing
    # chain. If a future re-promotion changes these switches the harness must
    # be revisited rather than silently mis-reproducing.
    assert best_cfg["partition"] == "score_decile_mondrian"
    assert best_cfg["partition_probability_source"] == "raw"
    assert not results.get("temporal_segment_multipliers"), (
        "Frozen run applied temporal multipliers; harness does not model them."
    )
    assert not results.get("shrinkback_enabled"), (
        "Frozen run used shrinkback; harness does not model it."
    )
    assert not results.get("global_rebalance", {}).get("applied"), (
        "Frozen run applied global rebalance; harness does not model it."
    )

    model, _ = _load_model()
    calibrator = _load_calibrator(results.get("calibrator_override_path") or None)

    cal_df = read_with_fallback(
        "data/processed/calibration_fe.parquet", "data/processed/calibration.parquet"
    ).reset_index(drop=True)
    test_df = read_with_fallback(
        "data/processed/test_fe.parquet", "data/processed/test.parquet"
    ).reset_index(drop=True)

    features, categorical = _resolve_features(model, cal_df, test_df)
    X_cal = _build_feature_matrix(cal_df, features, categorical)
    y_cal = cal_df[TARGET_COL].astype(float)
    X_test = _build_feature_matrix(test_df, features, categorical)
    group_cal_base = cal_df[GROUP_COL].fillna("UNKNOWN").astype(str)
    group_test_base = test_df[GROUP_COL].fillna("UNKNOWN").astype(str)

    y_prob_cal_raw = model.predict_proba(X_cal)[:, 1]
    y_prob_test_raw = model.predict_proba(X_test)[:, 1]

    split_meta = results["calibration_split"]
    idx_fit, idx_tune = split_calibration_for_tuning(
        y_cal=y_cal,
        group_cal=group_cal_base,
        issue_dates=cal_df.get("issue_d"),
        holdout_ratio=float(split_meta["holdout_ratio"]),
        random_state=int(split_meta["random_state"]),
    )
    assert len(idx_fit) == int(split_meta["fit_n"]), (
        f"Calibration fit split drifted: {len(idx_fit)} vs frozen {split_meta['fit_n']}"
    )
    assert len(idx_tune) == int(split_meta["holdout_n"]), (
        f"Calibration holdout split drifted: {len(idx_tune)} vs frozen {split_meta['holdout_n']}"
    )

    X_cal_fit = X_cal.iloc[idx_fit].reset_index(drop=True)
    y_cal_fit = y_cal.iloc[idx_fit].reset_index(drop=True)
    group_cal_fit_base = group_cal_base.iloc[idx_fit].reset_index(drop=True)
    prob_fit_raw = y_prob_cal_raw[idx_fit]

    group_cal_fit, group_test, partition_meta = build_mondrian_partition_labels(
        y_prob_cal=prob_fit_raw,
        y_prob_eval=y_prob_test_raw,
        partition=best_cfg["partition"],
        base_groups_cal=group_cal_fit_base,
        base_groups_eval=group_test_base,
        n_score_bins=int(best_cfg["n_score_bins"]),
        min_group_size=int(best_cfg["min_group_size"]),
        fallback_mode=str(best_cfg["fallback_mode"]),
    )
    frozen_edges = np.asarray(results["partition_meta"]["score_band_edges"], dtype=float)
    recomputed_edges = np.asarray(partition_meta["score_band_edges"], dtype=float)
    assert len(frozen_edges) == len(recomputed_edges), "Score band count drifted."
    edge_drift = float(np.max(np.abs(frozen_edges - recomputed_edges)))

    y_pred_90, y_int_90, _ = create_pd_intervals_mondrian(
        classifier=model,
        X_cal=X_cal_fit,
        y_cal=y_cal_fit,
        X_test=X_test,
        group_cal=group_cal_fit,
        group_test=group_test,
        alpha=float(best_cfg["alpha_used_90"]),
        min_group_size=int(best_cfg["min_group_size"]),
        calibrator=calibrator,
        scaled_scores=bool(best_cfg["scaled_scores"]),
        score_scale_family=str(best_cfg["score_scale_family"]),
    )
    y_pred_95, y_int_95, _ = create_pd_intervals_mondrian(
        classifier=model,
        X_cal=X_cal_fit,
        y_cal=y_cal_fit,
        X_test=X_test,
        group_cal=group_cal_fit,
        group_test=group_test,
        alpha=float(results["alpha_used_95"]),
        min_group_size=int(best_cfg["min_group_size"]),
        calibrator=calibrator,
        scaled_scores=bool(best_cfg["scaled_scores"]),
        score_scale_family=str(best_cfg["score_scale_family"]),
    )

    multipliers = {str(k): float(v) for k, v in results["group_coverage_multipliers"].items()}
    if multipliers:
        y_int_90 = apply_group_multipliers(y_pred_90, y_int_90, group_test, multipliers)
        y_int_95 = apply_group_multipliers(y_pred_95, y_int_95, group_test, multipliers)

    y_prob_test_calibrated = (
        apply_probability_calibrator(calibrator, y_prob_test_raw)
        if calibrator is not None
        else np.asarray(y_prob_test_raw, dtype=float)
    )

    return {
        "y_pred": np.asarray(y_pred_90, dtype=float),
        "y_pred_95": np.asarray(y_pred_95, dtype=float),
        "y_pred_calibrated_direct": np.asarray(y_prob_test_calibrated, dtype=float),
        "intervals_90": np.asarray(y_int_90, dtype=float),
        "intervals_95": np.asarray(y_int_95, dtype=float),
        "groups": pd.Series(group_test).astype(str).reset_index(drop=True),
        "y_true": test_df[TARGET_COL].astype(float).to_numpy(),
        "edge_drift": edge_drift,
        "multipliers": multipliers,
        "idx_tune": idx_tune,
        "y_cal": y_cal,
        "cal_df": cal_df,
        "X_cal": X_cal,
        "group_cal_fit_base": group_cal_fit_base,
        "prob_fit_raw": prob_fit_raw,
        "y_prob_cal_raw": y_prob_cal_raw,
        "model": model,
        "calibrator": calibrator,
        "best_cfg": best_cfg,
        "X_cal_fit": X_cal_fit,
        "y_cal_fit": y_cal_fit,
    }


def test_recomputed_intervals_match_frozen_parquet(
    frozen: dict[str, Any], recomputed: dict[str, Any]
) -> None:
    table = frozen["intervals"]
    assert len(table) == len(recomputed["y_pred"]), (
        f"Row count drifted: frozen {len(table)} vs recomputed {len(recomputed['y_pred'])}"
    )

    diffs = {
        "y_pred": np.max(np.abs(table["y_pred"].to_numpy(dtype=float) - recomputed["y_pred"])),
        "pd_low_90": np.max(
            np.abs(table["pd_low_90"].to_numpy(dtype=float) - recomputed["intervals_90"][:, 0])
        ),
        "pd_high_90": np.max(
            np.abs(table["pd_high_90"].to_numpy(dtype=float) - recomputed["intervals_90"][:, 1])
        ),
        "pd_low_95": np.max(
            np.abs(table["pd_low_95"].to_numpy(dtype=float) - recomputed["intervals_95"][:, 0])
        ),
        "pd_high_95": np.max(
            np.abs(table["pd_high_95"].to_numpy(dtype=float) - recomputed["intervals_95"][:, 1])
        ),
        "score_band_edges": recomputed["edge_drift"],
    }
    print("\nDrift report (max abs diff per column):")
    for name, value in diffs.items():
        print(f"  {name:18s} {value:.3e}")

    violations = {k: v for k, v in diffs.items() if v > MAX_ABS_ENDPOINT_DIFF}
    assert not violations, (
        f"Champion conformal drift above {MAX_ABS_ENDPOINT_DIFF:g}: {violations}. "
        "Per docs/refactor/MAPIE_MIGRATION_PLAN.md this is a model change, not a "
        "refactor — STOP Track B and open a revalidation decision."
    )


def test_recomputed_partition_labels_match_frozen(
    frozen: dict[str, Any], recomputed: dict[str, Any]
) -> None:
    table = frozen["intervals"]
    frozen_labels = table["grade"].astype(str).reset_index(drop=True)
    mismatches = int((frozen_labels != recomputed["groups"]).sum())
    assert mismatches == 0, f"{mismatches} Mondrian partition labels drifted."


def test_per_cell_coverage_within_tolerance(
    frozen: dict[str, Any], recomputed: dict[str, Any]
) -> None:
    from src.models.conformal import conditional_coverage_by_group

    table = frozen["intervals"]
    y_true = table["y_true"].to_numpy(dtype=float)
    frozen_cov = conditional_coverage_by_group(
        y_true,
        table[["pd_low_90", "pd_high_90"]].to_numpy(dtype=float),
        table["grade"],
    ).set_index("group")["coverage"]
    new_cov = conditional_coverage_by_group(
        recomputed["y_true"],
        recomputed["intervals_90"],
        recomputed["groups"],
    ).set_index("group")["coverage"]

    aligned = pd.concat([frozen_cov, new_cov], axis=1, keys=["frozen", "new"]).dropna()
    deltas = (aligned["frozen"] - aligned["new"]).abs()
    print("\nPer-cell 90% coverage deltas:")
    for group, delta in deltas.items():
        print(f"  {group:12s} {delta:.3e}")
    worst = float(deltas.max())
    assert worst <= MAX_CELL_COVERAGE_DELTA, (
        f"Per-cell coverage drift {worst:.3e} exceeds {MAX_CELL_COVERAGE_DELTA:g}."
    )


def test_recomputed_floor_multipliers_match_frozen(
    frozen: dict[str, Any], recomputed: dict[str, Any]
) -> None:
    """Re-learn the group coverage floor multipliers on the holdout split.

    The frozen run learned ``group_coverage_multipliers`` on the calibration
    holdout via a fixed grid; reproducing the exact dict shows the tuning
    path is stable, not just the base intervals.
    """
    from src.models.conformal import build_mondrian_partition_labels, create_pd_intervals_mondrian
    from src.models.conformal_tuning import enforce_group_coverage_floor

    results = frozen["results"]
    best_cfg = recomputed["best_cfg"]
    idx_tune = recomputed["idx_tune"]
    cal_df = recomputed["cal_df"]
    X_cal = recomputed["X_cal"]
    y_cal = recomputed["y_cal"]
    prob_tune_raw = recomputed["y_prob_cal_raw"][idx_tune]
    group_tune_base = (
        cal_df["grade"].fillna("UNKNOWN").astype(str).iloc[idx_tune].reset_index(drop=True)
    )

    group_cal_fit_holdout, group_tune, _ = build_mondrian_partition_labels(
        y_prob_cal=recomputed["prob_fit_raw"],
        y_prob_eval=prob_tune_raw,
        partition=best_cfg["partition"],
        base_groups_cal=recomputed["group_cal_fit_base"],
        base_groups_eval=group_tune_base,
        n_score_bins=int(best_cfg["n_score_bins"]),
        min_group_size=int(best_cfg["min_group_size"]),
        fallback_mode=str(best_cfg["fallback_mode"]),
    )
    X_tune = X_cal.iloc[idx_tune].reset_index(drop=True)
    y_tune = y_cal.iloc[idx_tune].reset_index(drop=True)
    y_pred_tune, y_int_tune, _ = create_pd_intervals_mondrian(
        classifier=recomputed["model"],
        X_cal=recomputed["X_cal_fit"],
        y_cal=recomputed["y_cal_fit"],
        X_test=X_tune,
        group_cal=group_cal_fit_holdout,
        group_test=group_tune,
        alpha=float(best_cfg["alpha_used_90"]),
        min_group_size=int(best_cfg["min_group_size"]),
        calibrator=recomputed["calibrator"],
        scaled_scores=bool(best_cfg["scaled_scores"]),
        score_scale_family=str(best_cfg["score_scale_family"]),
    )
    _, learned, _ = enforce_group_coverage_floor(
        y_true=y_tune.to_numpy(dtype=float),
        y_pred=y_pred_tune,
        y_intervals=y_int_tune,
        groups=group_tune,
        target_coverage=float(results["group_coverage_floor_target_90"]),
        multiplier_grid=(1.0, 1.02, 1.05, 1.08, 1.12, 1.16, 1.20),
    )
    learned_clean = {str(k): float(v) for k, v in learned.items() if float(v) > 1.0}
    frozen_mult = {
        str(k): float(v) for k, v in results["group_coverage_multipliers"].items() if float(v) > 1.0
    }
    print(f"\nFloor multipliers — frozen: {frozen_mult} / relearned: {learned_clean}")
    assert learned_clean == frozen_mult, (
        "Group coverage floor multipliers drifted between the frozen run and "
        "the recomputation on the current stack."
    )
