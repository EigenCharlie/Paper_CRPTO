"""Rebuild ``data/processed/test_predictions.parquet`` from frozen PD binaries.

Regenerates the canonical test-prediction surface WITHOUT retraining: it
loads an existing frozen model bundle (champion candidate, default-params
CatBoost baseline, logistic baseline, probability calibrator) and replays
the exact feature preparation used by ``train_pd_model.py`` (training
regime, temporal fit/val split for imputation medians, feature resolution
with stable core). This is the unification tool for keeping the canonical
prediction surface bit-consistent with the conformal certificate lineage.

The script refuses to write unless the recomputed calibrated scores match
the frozen conformal intervals' ``y_pred`` within 1e-9, which ties the new
parquet to the exact funded-set certificate.

Usage:
    uv run python scripts/rebuild_test_predictions_from_frozen.py \
        --frozen-dir models/search_pd/pd-hpo-local-2026-04-03-1325
"""

from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from catboost import CatBoostClassifier
from loguru import logger

from scripts.train_pd_model import _prepare_catboost_frame, _prepare_logreg_frame
from src.models.calibration import load_probability_calibrator
from src.models.conformal import apply_probability_calibrator
from src.utils.io_utils import read_with_fallback

ROOT = Path(__file__).resolve().parents[1]
TARGET = "default_flag"
FROZEN_INTERVALS_PATH = ROOT / "data" / "processed" / "conformal_intervals_mondrian.parquet"
CERTIFICATE_CONSISTENCY_TOL = 1e-9


def main(
    frozen_dir: str = "models/search_pd/pd-hpo-local-2026-04-03-1325",
    config_path: str = "configs/crpto_pd_model.yaml",
    output_path: str = "data/processed/test_predictions.parquet",
    skip_certificate_check: bool = False,
) -> int:
    frozen = ROOT / frozen_dir
    config = yaml.safe_load((ROOT / config_path).read_text(encoding="utf-8"))

    tuned_path = frozen / "pd_candidate_model.cbm"
    default_path = frozen / "pd_local_hpo_default.cbm"
    logreg_path = frozen / "pd_logreg_baseline.pkl"
    calibrator_path = frozen / "pd_candidate_calibrator.pkl"
    for path in (tuned_path, default_path, logreg_path, calibrator_path):
        if not path.is_file():
            raise FileNotFoundError(f"Missing frozen artifact: {path}")

    logger.info("Loading frozen PD bundle from {}", frozen)
    tuned = CatBoostClassifier()
    tuned.load_model(str(tuned_path))
    default = CatBoostClassifier()
    default.load_model(str(default_path))
    with logreg_path.open("rb") as fh:
        lr_bundle = pickle.load(fh)
    lr_model = lr_bundle["model"]
    logreg_features = [str(c) for c in lr_bundle["feature_names"]]
    lr_fill = lr_bundle["fill_values"]
    calibrator = load_probability_calibrator(str(calibrator_path))

    data_cfg = config.get("data", {})
    test = read_with_fallback(
        data_cfg.get("test_path", "data/processed/test_fe.parquet"),
        "data/processed/test.parquet",
    )

    # CatBoost features come from the model's own metadata (the frozen
    # binary records its training feature order and categorical indices),
    # which is exactly what the conformal layer consumed.
    catboost_features = list(tuned.feature_names_)
    cat_idx = set(tuned.get_cat_feature_indices())
    categorical_features = [f for i, f in enumerate(catboost_features) if i in cat_idx]
    logger.info(
        "Frozen-bundle features: catboost={} logreg={} categorical={}",
        len(catboost_features),
        len(logreg_features),
        len(categorical_features),
    )

    X_test_cb = _prepare_catboost_frame(test, catboost_features, categorical_features)
    # The logistic baseline pickle carries its own training-median fill
    # values, so the imputation is the literal April one, not a recompute.
    X_test_lr, _ = _prepare_logreg_frame(test, logreg_features, fill_values=lr_fill)

    y_test = test[TARGET].astype(int)
    y_prob_tuned = tuned.predict_proba(X_test_cb)[:, 1]
    y_prob_default = default.predict_proba(X_test_cb)[:, 1]
    y_prob_lr = lr_model.predict_proba(X_test_lr)[:, 1]
    y_prob_final = apply_probability_calibrator(calibrator, y_prob_tuned)

    if not skip_certificate_check:
        if not FROZEN_INTERVALS_PATH.is_file():
            raise FileNotFoundError(
                f"Certificate consistency check needs {FROZEN_INTERVALS_PATH}; "
                "pass --skip-certificate-check only for non-champion bundles."
            )
        frozen_pred = pd.read_parquet(FROZEN_INTERVALS_PATH, columns=["y_pred"])["y_pred"].to_numpy(
            dtype=float
        )
        max_diff = float(np.max(np.abs(frozen_pred - np.asarray(y_prob_final, dtype=float))))
        logger.info(
            "Certificate consistency: max |pd_calibrated - frozen y_pred| = {:.3e}", max_diff
        )
        if max_diff > CERTIFICATE_CONSISTENCY_TOL:
            raise AssertionError(
                f"Rebuilt calibrated scores drift {max_diff:.3e} from the frozen "
                f"conformal y_pred (tol {CERTIFICATE_CONSISTENCY_TOL:g}). The frozen "
                "bundle does not match the certificate lineage; aborting write."
            )

    preds_df = pd.DataFrame(
        {
            "loan_id": test["id"].astype(str) if "id" in test.columns else test.index.astype(str),
            "y_true": y_test.values.astype(float),
            "y_prob_lr": y_prob_lr.astype(float),
            "y_prob_cb_default": y_prob_default.astype(float),
            "y_prob_cb_tuned": y_prob_tuned.astype(float),
            "y_prob_final": np.asarray(y_prob_final, dtype=float),
            "pd_calibrated": np.asarray(y_prob_final, dtype=float),
            "pd_logreg": y_prob_lr.astype(float),
        }
    )
    out = ROOT / output_path
    out.parent.mkdir(parents=True, exist_ok=True)
    preds_df.to_parquet(out, index=False)
    logger.info("Wrote {} ({} rows)", out, len(preds_df))

    from sklearn.metrics import brier_score_loss, roc_auc_score

    auc = roc_auc_score(y_test, preds_df["pd_calibrated"])
    brier = brier_score_loss(y_test, preds_df["pd_calibrated"])
    logger.info("pd_calibrated metrics: AUC={:.4f} Brier={:.4f}", auc, brier)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-dir", default="models/search_pd/pd-hpo-local-2026-04-03-1325")
    parser.add_argument("--config", default="configs/crpto_pd_model.yaml")
    parser.add_argument("--output", default="data/processed/test_predictions.parquet")
    parser.add_argument("--skip-certificate-check", action="store_true")
    args = parser.parse_args()
    raise SystemExit(
        main(
            frozen_dir=args.frozen_dir,
            config_path=args.config,
            output_path=args.output,
            skip_certificate_check=args.skip_certificate_check,
        )
    )
