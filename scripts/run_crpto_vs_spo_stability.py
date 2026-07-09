"""CRPTO vs SPO+ stability under distributional shift — CRPTO.

Evaluates decision regret (SPO+, two-stage, conformal robust) AND conformal
coverage per temporal period in the OOT test set (2018-2020).  The natural
regime change (default rate 24.5% → 1.35%) provides a quasi-experiment for
distributional shift stability.

Key design: SPO+ is trained ONCE per seed on full training data (2007-2017),
then evaluated on each period separately — mirroring production deployment.

Output artifacts:
  - data/processed/crpto_vs_spo_stability.json
  - data/processed/crpto_vs_spo_stability_detail.parquet
  - reports/crpto/figures/crpto_fig11_crpto_stability.{pdf,png}

Usage:
    uv run python scripts/run_crpto_vs_spo_stability.py
    uv run python scripts/run_crpto_vs_spo_stability.py --n-items 50 --budget 15
"""

from __future__ import annotations

import argparse
import importlib
import json
import shutil
import time
from collections import OrderedDict
from numbers import Real
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from loguru import logger

from src.utils.artifact_metadata import build_artifact_metadata, resolve_run_tag

matplotlib.use("Agg")

SCHEMA_VERSION = "2026-03-22.1"
LGD = 0.40
RANDOM_SEED = 42

NUMERIC_FEATURES = [
    "loan_amnt",
    "int_rate",
    "annual_inc",
    "dti",
    "fico_range_low",
    "open_acc",
    "revol_bal",
    "revol_util",
    "total_acc",
    "installment",
    "emp_length",
    "pub_rec",
    "delinq_2yrs",
    "inq_last_6mths",
    "mths_since_last_delinq",
]

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "processed"
OUT_DIR = REPO_ROOT / "reports" / "crpto" / "figures"
BOOK_FIG_DIR = REPO_ROOT / "book" / "assets" / "figures" / "publication"

PERIODS = OrderedDict(
    [
        ("2018H1", ("2018-01-01", "2018-07-01")),
        ("2018H2", ("2018-07-01", "2019-01-01")),
        ("2019H1", ("2019-01-01", "2019-07-01")),
        ("2019H2", ("2019-07-01", "2020-01-01")),
        ("2020", ("2020-01-01", "2021-01-01")),
    ]
)

# ── Publication style (matches generate_crpto_figures.py) ────────────────────

COL2 = 7.0
HEIGHT_M = 3.2

PALETTE = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "red": "#D55E00",
    "gray": "#999999",
    "sky": "#56B4E9",
}

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif", "serif"],
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "legend.framealpha": 0.85,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linestyle": "--",
        "lines.linewidth": 1.5,
    }
)


def _require_optional_module(module_name: str) -> Any:
    """Import an optional SPO dependency with an explicit experiment-level error."""
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise RuntimeError(
            "SPO stability is an optional experiment. Install the `spo` extras "
            f"before running this script; missing module: {module_name}."
        ) from exc


# ── Period assignment ────────────────────────────────────────────────────────


def _load_spo_real_module() -> Any:
    """Load SPO helpers lazily so this module remains importable without PyEPO."""
    try:
        return importlib.import_module("scripts.run_spo_real")
    except RuntimeError as exc:
        raise RuntimeError(
            "SPO stability is an optional experiment. Install the `spo` extras "
            "before running this script."
        ) from exc


def _assign_periods(issue_d: pd.Series) -> pd.Series:
    """Assign each loan to a temporal period based on issue_d."""
    dt = pd.to_datetime(issue_d)
    result = pd.Series("", index=dt.index, dtype=str)
    for name, (start, end) in PERIODS.items():
        mask = (dt >= pd.Timestamp(start)) & (dt < pd.Timestamp(end))
        result[mask] = name
    return result


# ── Conformal coverage evaluation ────────────────────────────────────────────


def _evaluate_period_coverage(ci_slice: pd.DataFrame) -> dict:
    """Compute conformal coverage metrics for a slice of conformal intervals."""
    y = ci_slice["y_true"].values
    low_90 = ci_slice["pd_low_90"].values
    high_90 = ci_slice["pd_high_90"].values

    covered_90 = ((y >= low_90) & (y <= high_90)).astype(float)
    coverage_90 = float(covered_90.mean())
    avg_width_90 = float((high_90 - low_90).mean())

    # Coverage 95 if available
    coverage_95 = None
    if "pd_low_95" in ci_slice.columns and "pd_high_95" in ci_slice.columns:
        low_95 = ci_slice["pd_low_95"].values
        high_95 = ci_slice["pd_high_95"].values
        covered_95 = ((y >= low_95) & (y <= high_95)).astype(float)
        coverage_95 = float(covered_95.mean())

    # Min coverage by grade (Mondrian guarantee)
    min_grade_coverage_90 = None
    if "grade" in ci_slice.columns:
        grade_cov = ci_slice.assign(covered=covered_90).groupby("grade")["covered"].mean()
        if len(grade_cov) > 0:
            min_grade_coverage_90 = float(grade_cov.min())

    return {
        "coverage_90": coverage_90,
        "coverage_95": coverage_95,
        "avg_width_90": avg_width_90,
        "min_grade_coverage_90": min_grade_coverage_90,
    }


# ── Figure generation ────────────────────────────────────────────────────────


def _available_numeric_features(train: pd.DataFrame, test: pd.DataFrame) -> list[str]:
    return [
        feature
        for feature in NUMERIC_FEATURES
        if feature in train.columns and feature in test.columns
    ]


def _period_masks(test_periods: pd.Series) -> dict[str, np.ndarray]:
    return {name: (test_periods.values == name) for name in PERIODS}


def _period_default_rate(test: pd.DataFrame, mask: np.ndarray) -> float:
    n_loans = int(mask.sum())
    return float(test.loc[mask, "default_flag"].mean()) if n_loans > 0 else 0.0


def _init_period_regrets() -> dict[str, dict[str, list[float]]]:
    return {name: {"two_stage": [], "spo_plus": [], "conformal_robust": []} for name in PERIODS}


def _period_sample_seed(seed: int, period_name: str) -> int:
    """Stable per-period seed; avoids Python's process-randomized hash()."""
    period_offset = list(PERIODS).index(period_name) + 1
    return int(seed + period_offset * 100_000)


def _period_test_instance_count(n_period: int, n_items: int) -> int:
    return max(min(80, n_period // n_items), 5)


def _valid_regret_values(values: list[float]) -> list[float]:
    return [value for value in values if not np.isnan(value)]


def _mean_std(values: list[float]) -> tuple[float, float]:
    valid = _valid_regret_values(values)
    if not valid:
        return float("nan"), float("nan")
    return float(np.mean(valid)), float(np.std(valid))


def _spo_improvement_pct(two_stage_mean: float, spo_mean: float, has_values: bool) -> float | None:
    if not has_values:
        return None
    return (two_stage_mean - spo_mean) / (abs(two_stage_mean) + 1e-9) * 100


def _coverage_by_period(
    ci: pd.DataFrame,
    period_masks: dict[str, np.ndarray],
) -> dict[str, dict[str, Any]]:
    period_coverage: dict[str, dict[str, Any]] = {}
    for period_name, mask in period_masks.items():
        ci_slice = ci.loc[mask]
        if len(ci_slice) == 0:
            continue
        period_coverage[period_name] = _evaluate_period_coverage(ci_slice)
        logger.info(
            "  {} coverage: 90%={:.2%} width={:.4f} min_grade={:.2%}",
            period_name,
            period_coverage[period_name]["coverage_90"],
            period_coverage[period_name]["avg_width_90"],
            period_coverage[period_name].get("min_grade_coverage_90", 0) or 0,
        )
    return period_coverage


def _detail_rows(
    *,
    test: pd.DataFrame,
    period_masks: dict[str, np.ndarray],
    per_period_regrets: dict[str, dict[str, list[float]]],
    period_coverage: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for period_name in PERIODS:
        mask = period_masks[period_name]
        n_loans = int(mask.sum())
        regrets = per_period_regrets[period_name]
        cov = period_coverage.get(period_name, {})

        ts_mean, ts_std = _mean_std(regrets["two_stage"])
        spo_mean, spo_std = _mean_std(regrets["spo_plus"])
        cr_mean, cr_std = _mean_std(regrets["conformal_robust"])
        has_spo_comparison = bool(
            _valid_regret_values(regrets["two_stage"]) and _valid_regret_values(regrets["spo_plus"])
        )

        rows.append(
            {
                "period": period_name,
                "n_loans": n_loans,
                "default_rate": _period_default_rate(test, mask),
                "two_stage_mean_regret": ts_mean,
                "two_stage_std_regret": ts_std,
                "spo_plus_mean_regret": spo_mean,
                "spo_plus_std_regret": spo_std,
                "conformal_robust_mean_regret": cr_mean,
                "conformal_robust_std_regret": cr_std,
                "spo_improvement_pct": _spo_improvement_pct(
                    ts_mean,
                    spo_mean,
                    has_spo_comparison,
                ),
                "coverage_90": cov.get("coverage_90"),
                "coverage_95": cov.get("coverage_95"),
                "avg_width_90": cov.get("avg_width_90"),
                "min_grade_coverage_90": cov.get("min_grade_coverage_90"),
            }
        )
    return rows


def _round_optional(value: object, digits: int) -> float | None:
    if isinstance(value, Real):
        return round(float(value), digits)
    return None


def _period_summary_row(
    row: dict[str, Any],
    regrets: dict[str, list[float]],
) -> dict[str, Any]:
    return {
        "n_loans": int(row["n_loans"]),
        "default_rate": round(float(row["default_rate"]), 4),
        "regret": {
            "two_stage": {
                "mean": round(float(row["two_stage_mean_regret"]), 6),
                "std": round(float(row["two_stage_std_regret"]), 6),
                "per_seed": regrets["two_stage"],
            },
            "spo_plus": {
                "mean": round(float(row["spo_plus_mean_regret"]), 6),
                "std": round(float(row["spo_plus_std_regret"]), 6),
                "per_seed": regrets["spo_plus"],
            },
            "conformal_robust": {
                "mean": round(float(row["conformal_robust_mean_regret"]), 6),
                "std": round(float(row["conformal_robust_std_regret"]), 6),
                "per_seed": regrets["conformal_robust"],
            },
        },
        "spo_improvement_vs_ts_pct": _round_optional(row["spo_improvement_pct"], 2),
        "coverage_90": _round_optional(row["coverage_90"], 4),
        "coverage_95": _round_optional(row["coverage_95"], 4),
        "avg_width_90": _round_optional(row["avg_width_90"], 4),
        "min_grade_coverage_90": _round_optional(row["min_grade_coverage_90"], 4),
    }


def _per_period_json(
    rows: list[dict[str, Any]],
    per_period_regrets: dict[str, dict[str, list[float]]],
) -> dict[str, Any]:
    return {
        str(row["period"]): _period_summary_row(
            row,
            per_period_regrets[str(row["period"])],
        )
        for row in rows
    }


def _non_null_float_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    return [float(row[key]) for row in rows if row[key] is not None]


def _stability_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    coverages_90 = _non_null_float_values(rows, "coverage_90")
    spo_improvements = _non_null_float_values(rows, "spo_improvement_pct")
    return {
        "coverage_always_above_target": all(c >= 0.90 for c in coverages_90),
        "coverage_range": [round(min(coverages_90), 4), round(max(coverages_90), 4)],
        "spo_improvement_range_pct": (
            [round(min(spo_improvements), 2), round(max(spo_improvements), 2)]
            if spo_improvements
            else None
        ),
    }


def _summary_payload(
    *,
    run_tag: str,
    args: argparse.Namespace,
    n_features: int,
    feature_names: list[str],
    rows: list[dict[str, Any]],
    per_period_regrets: dict[str, dict[str, list[float]]],
    total_time: float,
) -> dict[str, Any]:
    return {
        **build_artifact_metadata(
            schema_version=SCHEMA_VERSION, run_tag=run_tag, allow_untracked=True
        ),
        "config": {
            "n_items": args.n_items,
            "budget": args.budget,
            "n_train_instances": args.n_train,
            "epochs": args.epochs,
            "n_seeds": args.seeds,
            "n_features": n_features,
            "feature_names": feature_names,
            "lgd": LGD,
        },
        "per_period": _per_period_json(rows, per_period_regrets),
        "stability_summary": _stability_summary(rows),
        "train_time_seconds": round(total_time, 1),
    }


def _generate_stability_figure(detail_df: pd.DataFrame, out_dir: Path) -> None:
    """Two-panel figure: Panel A = regret by period, Panel B = coverage by period."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(COL2, HEIGHT_M))

    periods = detail_df["period"].values
    x = np.arange(len(periods))

    # ── Panel A: Decision Regret by Period ──────────────────────────────────
    methods = [
        ("two_stage_mean_regret", "two_stage_std_regret", "Two-Stage", PALETTE["orange"], "-"),
        ("spo_plus_mean_regret", "spo_plus_std_regret", "SPO+", PALETTE["blue"], "-"),
        (
            "conformal_robust_mean_regret",
            "conformal_robust_std_regret",
            "CRPTO",
            PALETTE["green"],
            "-",
        ),
    ]

    for mean_col, std_col, label, color, ls in methods:
        y_mean = detail_df[mean_col].values
        y_std = detail_df[std_col].values
        ax1.plot(x, y_mean, ls, color=color, label=label, marker="o", markersize=4)
        ax1.fill_between(x, y_mean - y_std, y_mean + y_std, alpha=0.15, color=color)

    # Annotate default rates above
    ax1_top = ax1.twiny()
    ax1_top.set_xlim(ax1.get_xlim())
    ax1_top.set_xticks(x)
    default_labels = [f"{r:.1f}%" for r in detail_df["default_rate"].values * 100]
    ax1_top.set_xticklabels(default_labels, fontsize=7, color=PALETTE["gray"])
    ax1_top.set_xlabel("Default Rate", fontsize=8, color=PALETTE["gray"])
    ax1_top.spines["top"].set_visible(True)
    ax1_top.spines["top"].set_color(PALETTE["gray"])
    ax1_top.spines["top"].set_alpha(0.3)
    ax1_top.tick_params(axis="x", colors=PALETTE["gray"])

    ax1.set_xticks(x)
    ax1.set_xticklabels(periods, fontsize=8)
    ax1.set_ylabel("Mean Decision Regret")
    ax1.set_title("A. Decision Regret by Period")
    ax1.legend(loc="upper right", fontsize=7)

    # ── Panel B: Conformal Coverage by Period ───────────────────────────────
    cov = detail_df["coverage_90"].values * 100
    width = detail_df["avg_width_90"].values

    ax2.plot(x, cov, "-o", color=PALETTE["blue"], label="Coverage 90%", markersize=5)
    ax2.axhline(y=90, color=PALETTE["red"], linestyle="--", linewidth=1.0, label="Target 90%")
    ax2.set_xticks(x)
    ax2.set_xticklabels(periods, fontsize=8)
    ax2.set_ylabel("Coverage (%)", color=PALETTE["blue"])
    ax2.set_ylim(85, 105)
    ax2.tick_params(axis="y", labelcolor=PALETTE["blue"])

    # Secondary axis: width
    ax2r = ax2.twinx()
    ax2r.plot(x, width, "--s", color=PALETTE["orange"], label="Avg Width", markersize=4)
    ax2r.set_ylabel("Avg Interval Width", color=PALETTE["orange"])
    ax2r.tick_params(axis="y", labelcolor=PALETTE["orange"])
    ax2r.spines["right"].set_visible(True)

    # Combined legend
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2r.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc="lower left", fontsize=7)

    ax2.set_title("B. Conformal Coverage by Period")

    fig.suptitle(
        "CRPTO vs SPO+ Stability Under Distributional Shift (OOT 2018–2020)",
        fontsize=10,
        y=1.05,
    )
    fig.tight_layout()

    name = "crpto_fig11_crpto_stability"
    out_dir.mkdir(parents=True, exist_ok=True)
    BOOK_FIG_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        path = out_dir / f"{name}.{ext}"
        fig.savefig(path)
        shutil.copy2(path, BOOK_FIG_DIR / f"{name}.{ext}")
    logger.info(f"Saved: {name}.pdf / .png")
    plt.close(fig)


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CRPTO vs SPO+ stability under distributional shift"
    )
    parser.add_argument("--n-items", type=int, default=50, help="Loans per instance (default 50)")
    parser.add_argument("--budget", type=int, default=15, help="Loans to select (default 15)")
    parser.add_argument(
        "--n-train", type=int, default=800, help="Training instances per seed (default 800)"
    )
    parser.add_argument("--epochs", type=int, default=50, help="SPO+ training epochs (default 50)")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate (default 0.001)")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size (default 32)")
    parser.add_argument("--seeds", type=int, default=5, help="Number of random seeds (default 5)")
    args = parser.parse_args()

    run_tag = resolve_run_tag(None, allow_untracked=True)
    logger.info(
        "CRPTO stability | n_items={} budget={} epochs={} seeds={} run_tag={}",
        args.n_items,
        args.budget,
        args.epochs,
        args.seeds,
        run_tag,
    )

    # ── 1. Load data ────────────────────────────────────────────────────────
    spo_real = _load_spo_real_module()
    CreditPortfolioLP = spo_real.CreditPortfolioLP
    _compute_regret = spo_real._compute_regret
    _compute_true_optima = spo_real._compute_true_optima
    _index_costs = spo_real._index_costs
    _load_pd_artifacts = spo_real._load_pd_artifacts
    _predict_calibrated_costs = spo_real._predict_calibrated_costs
    _prep_features = spo_real._prep_features
    _sample_instances = spo_real._sample_instances
    _train_spo = spo_real._train_spo

    train = pd.read_parquet(DATA_DIR / "train_fe.parquet")
    test = pd.read_parquet(DATA_DIR / "test_fe.parquet")
    ci = pd.read_parquet(DATA_DIR / "conformal_intervals_mondrian.parquet")
    logger.info("Loaded: train {:,} | test {:,} | ci {:,}", len(train), len(test), len(ci))

    # Verify alignment
    assert len(ci) == len(test), f"ci ({len(ci)}) != test ({len(test)}) — row alignment broken"

    # Assign periods
    test_periods = _assign_periods(test["issue_d"])
    ci["_period"] = test_periods.values

    period_counts = test_periods.value_counts().to_dict()
    logger.info("Period counts: {}", period_counts)

    # ── 2. Prepare features and costs ───────────────────────────────────────
    avail = _available_numeric_features(train, test)
    n_features = len(avail)
    logger.info("Using {} features: {}", n_features, avail)

    X_tr_all, mu, sigma = _prep_features(train, avail)
    X_te_all, _, _ = _prep_features(test, avail, mu=mu, sigma=sigma)

    # Calibrated costs
    pd_arts = _load_pd_artifacts()
    if pd_arts is None:
        logger.error("PD artifacts required — run train_pd_model.py first")
        return 1
    cb_model, calibrator, feat_names, cat_feats = pd_arts

    logger.info("Predicting calibrated PD costs...")
    t0 = time.time()
    c_tr_all = _predict_calibrated_costs(train, cb_model, calibrator, feat_names, cat_feats)
    c_te_all = _predict_calibrated_costs(test, cb_model, calibrator, feat_names, cat_feats)
    logger.info("  Done in {:.1f}s", time.time() - t0)

    # Two-stage: Ridge on full train
    from sklearn.linear_model import Ridge

    ridge = Ridge(alpha=1.0)
    ridge.fit(X_tr_all, c_tr_all)
    c_ts_te_all = ridge.predict(X_te_all).astype(np.float32)
    logger.info("Two-stage Ridge: train R²={:.4f}", ridge.score(X_tr_all, c_tr_all))

    # Conformal robust costs
    pd_high = ci["pd_high_90"].values.astype(np.float32)
    int_rate_te = pd.to_numeric(test["int_rate"], errors="coerce").fillna(12.0).values / 100.0
    c_robust_te_all = (pd_high * LGD - int_rate_te).astype(np.float32)

    # ── 3. Build period masks ───────────────────────────────────────────────
    period_masks = _period_masks(test_periods)
    for name, mask in period_masks.items():
        n_loans = int(mask.sum())
        default_rate = _period_default_rate(test, mask)
        logger.info("  {} : {:,} loans, default rate {:.2%}", name, n_loans, default_rate)

    # ── 4. Multi-seed × multi-period evaluation ─────────────────────────────
    # Structure: per_period[period][method] = list of per-seed mean regrets
    per_period_regrets = _init_period_regrets()

    t_total = time.time()

    for seed_idx in range(args.seeds):
        seed = RANDOM_SEED + seed_idx * 1000
        logger.info("=== Seed {}/{} (seed={}) ===", seed_idx + 1, args.seeds, seed)
        rng = np.random.RandomState(seed)

        # Sample training instances (from FULL train, same as original)
        X_tr_inst, c_tr_inst, _ = _sample_instances(
            X_tr_all, c_tr_all, args.n_items, args.n_train, rng
        )

        # Train SPO+ ONCE per seed on full training data
        optmodel_train = CreditPortfolioLP(n_items=args.n_items, budget=args.budget)
        spo_model, _ = _train_spo(
            X_tr_inst,
            c_tr_inst,
            optmodel_train,
            n_features=n_features,
            n_items=args.n_items,
            epochs=args.epochs,
            lr=args.lr,
            batch_size=args.batch_size,
            seed=seed,
        )
        spo_model.eval()

        # Evaluate on each temporal period
        for period_name, mask in period_masks.items():
            n_period = int(mask.sum())
            if n_period < args.n_items:
                logger.warning("  {} : only {} loans, skipping", period_name, n_period)
                for method in per_period_regrets[period_name]:
                    per_period_regrets[period_name][method].append(float("nan"))
                continue

            n_test_period = _period_test_instance_count(n_period, args.n_items)

            # Slice arrays to this period
            period_idx = np.where(mask)[0]
            X_period = X_te_all[period_idx]
            c_period = c_te_all[period_idx]
            c_ts_period = c_ts_te_all[period_idx]
            c_robust_period = c_robust_te_all[period_idx]

            # Sample test instances within this period
            rng_period = np.random.RandomState(_period_sample_seed(seed, period_name))
            X_inst, c_inst, idx_inst = _sample_instances(
                X_period, c_period, args.n_items, n_test_period, rng_period
            )
            c_ts_inst = _index_costs(c_ts_period, idx_inst)
            c_robust_inst = _index_costs(c_robust_period, idx_inst)

            # SPO+ predictions
            torch = _require_optional_module("torch")
            n_input = args.n_items * n_features
            X_flat = X_inst.reshape(n_test_period, n_input)
            with torch.no_grad():
                c_spo_inst = spo_model(torch.tensor(X_flat, dtype=torch.float32)).numpy()

            # Compute true optima + regrets
            optmodel_eval = CreditPortfolioLP(n_items=args.n_items, budget=args.budget)
            true_optima = _compute_true_optima(c_inst, optmodel_eval)

            regrets_ts = _compute_regret(c_ts_inst, c_inst, optmodel_eval.copy(), true_optima)
            regrets_spo = _compute_regret(c_spo_inst, c_inst, optmodel_eval.copy(), true_optima)
            regrets_robust = _compute_regret(
                c_robust_inst, c_inst, optmodel_eval.copy(), true_optima
            )

            per_period_regrets[period_name]["two_stage"].append(float(regrets_ts.mean()))
            per_period_regrets[period_name]["spo_plus"].append(float(regrets_spo.mean()))
            per_period_regrets[period_name]["conformal_robust"].append(float(regrets_robust.mean()))

            logger.info(
                "  {} (n_test={}): ts={:.4f} spo={:.4f} crpto={:.4f}",
                period_name,
                n_test_period,
                regrets_ts.mean(),
                regrets_spo.mean(),
                regrets_robust.mean(),
            )

    total_time = time.time() - t_total
    logger.info("All seeds done in {:.1f}s", total_time)

    # ── 5. Conformal coverage per period (deterministic, no seed) ───────────
    period_coverage = _coverage_by_period(ci, period_masks)

    # ── 6. Aggregate into detail DataFrame ──────────────────────────────────
    rows = _detail_rows(
        test=test,
        period_masks=period_masks,
        per_period_regrets=per_period_regrets,
        period_coverage=period_coverage,
    )

    detail_df = pd.DataFrame(rows)
    detail_path = DATA_DIR / "crpto_vs_spo_stability_detail.parquet"
    detail_df.to_parquet(detail_path, index=False)
    logger.info("Saved: {}", detail_path)

    # ── 7. Summary JSON ─────────────────────────────────────────────────────
    summary = _summary_payload(
        run_tag=run_tag,
        args=args,
        n_features=n_features,
        feature_names=avail,
        rows=rows,
        per_period_regrets=per_period_regrets,
        total_time=total_time,
    )

    json_path = DATA_DIR / "crpto_vs_spo_stability.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    logger.info("Saved: {}", json_path)

    # ── 8. Generate publication figure ──────────────────────────────────────
    _generate_stability_figure(detail_df, OUT_DIR)

    logger.info("Done. Artifacts: {} + {} + fig11", json_path, detail_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
