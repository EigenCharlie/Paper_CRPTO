"""Generate publication-quality matplotlib figures for CRPTO.

Outputs PDF + PNG (300 DPI) under reports/crpto/figures/.

Papers:
  - Paper 3: Mondrian Conformal Prediction (COPA 2026)
  - Paper 2: IFRS9 E2E with CP (JBF/JORS)
  - CRPTO: Predict-then-Optimize (MS/OR/EJOR)

Usage:
    uv run python scripts/generate_crpto_figures.py
    uv run python scripts/generate_crpto_figures.py --paper 3
    uv run python scripts/generate_crpto_figures.py --paper 2
    uv run python scripts/generate_crpto_figures.py --CRPTO
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from loguru import logger

from src.utils.artifact_metadata import build_artifact_metadata

matplotlib.use("Agg")

# ── Publication style ─────────────────────────────────────────────────────────

# IEEE/Springer two-column format: 3.5" per column, 7" full-width
COL1 = 3.5  # single column (inches)
COL2 = 7.0  # double column (inches)
HEIGHT_S = 2.4  # short panel
HEIGHT_M = 3.2  # medium panel
HEIGHT_T = 4.2  # tall panel

# Colorblind-safe palette (Wong 2011 + Nature palette)
PALETTE = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "red": "#D55E00",
    "purple": "#CC79A7",
    "sky": "#56B4E9",
    "yellow": "#F0E442",
    "black": "#000000",
    "gray": "#999999",
    "lgray": "#CCCCCC",
}
COLORS = list(PALETTE.values())

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
        "patch.linewidth": 0.8,
    }
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "processed"
MODELS_DIR = REPO_ROOT / "models"
OUT_DIR = REPO_ROOT / "reports" / "crpto" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)
BOOK_FIG_DIR = REPO_ROOT / "book" / "assets" / "figures" / "publication"
BOOK_FIG_DIR.mkdir(parents=True, exist_ok=True)
BOOK_OUTPUT_FIG_DIR = REPO_ROOT / "book" / "_output" / "assets" / "figures" / "publication"
# Dossier figures (PD curves, etc.) referenced by the Spanish book chapters live
# here; we regenerate them in the journal house style and overwrite in place so
# the chapter `.png` references need no edits.
EDITORIAL_FIG_DIR = REPO_ROOT / "book" / "assets" / "figures" / "editorial"


def _save(fig: plt.Figure, name: str) -> None:
    for ext in ("pdf", "png"):
        path = OUT_DIR / f"{name}.{ext}"
        fig.savefig(path)
        shutil.copy2(path, BOOK_FIG_DIR / f"{name}.{ext}")
        if BOOK_OUTPUT_FIG_DIR.exists():
            BOOK_OUTPUT_FIG_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, BOOK_OUTPUT_FIG_DIR / f"{name}.{ext}")
    logger.info(f"Saved: {name}.pdf / .png")
    plt.close(fig)


def _save_editorial(fig: plt.Figure, name: str) -> None:
    """Overwrite a dossier figure in book/assets/figures/editorial (PNG, 300 DPI).

    The editorial dir is PNG-only by convention and the chapters include the
    ``.png`` files directly, so we keep a single 300 DPI raster (print standard).
    """
    EDITORIAL_FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(EDITORIAL_FIG_DIR / f"{name}.png")
    logger.info(f"Saved editorial: {name}.png")
    plt.close(fig)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ── Paper 3: Mondrian CP ──────────────────────────────────────────────────────

METHOD_LABELS = {
    "global_split": "Global Split-CP",
    "mondrian_scaled": "Mondrian (scaled)",
    "mondrian_unscaled": "Mondrian (unscaled)",
    "score_decile_mondrian": "Score-Decile Mondrian",
    "grade_x_scoreband_mondrian": "Grade×Scoreband",
    "cross_conformal_score_space": "Cross-Conformal",
    "mondrian_selected_cfg": "Mondrian (cfg-selected)",
}


def _paper3_fig1_variant_scatter() -> None:
    """Fig 1 — Efficiency–coverage Pareto scatter for 6 CP variants."""
    df = pd.read_parquet(DATA_DIR / "conformal_variant_benchmark.parquet")

    # Column is "variant", not "method"
    var_col = "variant" if "variant" in df.columns else "method"

    agg = (
        df.groupby(var_col)
        .agg(coverage=("coverage", "mean"), width=("avg_width", "mean"))
        .reset_index()
        .rename(columns={var_col: "method"})
    )

    fig, ax = plt.subplots(figsize=(COL2, HEIGHT_M))

    target_cov = 0.90
    ax.axvline(target_cov, color=PALETTE["red"], lw=1.0, ls="--", label="Target 90%")
    ax.axhline(agg["width"].min(), color=PALETTE["lgray"], lw=0.7, ls=":")

    offset_map = {
        "mondrian_selected_cfg": (6, 2),
        "grade_x_scoreband_mondrian": (6, 0),
        "score_decile_mondrian": (6, -8),
        "cross_conformal_score_space": (6, 4),
        "global_split": (6, -8),
        "mondrian_scaled": (6, -2),
        "mondrian_unscaled": (6, 8),
    }

    for _i, row in agg.iterrows():
        color = PALETTE["blue"] if row["coverage"] >= target_cov else PALETTE["gray"]
        ax.scatter(
            row["coverage"],
            row["width"],
            color=color,
            s=70,
            zorder=5,
            edgecolors="white",
            linewidths=0.5,
        )
        label = METHOD_LABELS.get(row["method"], row["method"])
        xoff, yoff = offset_map.get(row["method"], (6, 0))
        ax.annotate(
            label,
            (row["coverage"], row["width"]),
            textcoords="offset points",
            xytext=(xoff, yoff),
            fontsize=7.3,
            ha="left",
            va="center",
            bbox={
                "boxstyle": "round,pad=0.15",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.8,
            },
        )

    ax.set_xlabel("Empirical Coverage")
    ax.set_ylabel("Mean Interval Width")
    ax.set_title("Conformal Variants: Coverage–Efficiency Trade-off (OOT, $n=276{,}869$)")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=1))
    ax.set_xlim(0.893, 0.937)
    ax.set_ylim(max(0.71, agg["width"].min() - 0.01), agg["width"].max() + 0.02)
    from matplotlib.patches import Patch

    ax.legend(
        handles=[
            Patch(color=PALETTE["blue"], label="Coverage ≥ 90% (valid)"),
            Patch(color=PALETTE["gray"], label="Coverage < 90% (invalid)"),
            plt.Line2D([0], [0], color=PALETTE["red"], ls="--", label="Target 90%"),
        ],
        loc="upper left",
    )
    fig.tight_layout()
    _save(fig, "p3_fig1_variant_scatter")


def _paper3_fig2_grade_coverage_heatmap() -> None:
    """Fig 2 — Per-grade coverage heatmap across 6 CP variants."""
    df = pd.read_parquet(DATA_DIR / "conformal_variant_benchmark_by_group.parquet")

    # Columns: group, variant (not method/grade)
    var_col = "variant" if "variant" in df.columns else "method"
    grp_col = "group" if "group" in df.columns else "grade"

    df = df[df[grp_col].astype(str).str.fullmatch(r"[A-G]")]
    pivot = df.pivot_table(index=var_col, columns=grp_col, values="coverage", aggfunc="mean")
    pivot.index = [METHOD_LABELS.get(m, m) for m in pivot.index]
    desired_order = [
        "mondrian_selected_cfg",
        "score_decile_mondrian",
        "grade_x_scoreband_mondrian",
        "cross_conformal_score_space",
        "mondrian_scaled",
        "mondrian_unscaled",
        "global_split",
    ]
    ordered_labels = [METHOD_LABELS.get(m, m) for m in desired_order if m in df[var_col].unique()]
    pivot = pivot.reindex(ordered_labels)
    pivot = pivot.reindex(sorted(pivot.columns), axis=1)

    fig, ax = plt.subplots(figsize=(COL2, HEIGHT_M))
    cmap = plt.cm.RdYlGn
    im = ax.imshow(pivot.values, cmap=cmap, vmin=0.70, vmax=1.00, aspect="auto")

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, fontsize=8)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=8)
    ax.set_xlabel("Grade")
    ax.set_ylabel("Conformal Method")
    ax.set_title("Per-Grade Coverage (nominal = 90%, OOT)")

    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            if pd.isna(val):
                continue
            color = "white" if val < 0.80 or val > 0.97 else "black"
            ax.text(j, i, f"{val:.0%}", ha="center", va="center", fontsize=7.2, color=color)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label("Empirical Coverage", fontsize=8)
    cbar.ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))
    ax.grid(False)
    fig.tight_layout()
    _save(fig, "p3_fig2_grade_coverage_heatmap")


def _paper3_fig3_temporal_stability() -> None:
    """Fig 3 — Temporal coverage stability for top 3 variants."""
    df = pd.read_parquet(DATA_DIR / "conformal_temporal_diagnostics.parquet")

    if df.empty:
        logger.warning("conformal_temporal_diagnostics empty — skipping fig3")
        return

    # Pick top methods (by availability)
    method_col = "method" if "method" in df.columns else "variant"
    methods_available = df[method_col].dropna().unique().tolist()
    preferred = ["mondrian_selected_cfg", "score_decile_mondrian", "cross_conformal_score_space"]
    methods = [m for m in preferred if m in methods_available][:3]
    if not methods:
        methods = methods_available[:3]

    time_col = (
        "temporal_segment"
        if "temporal_segment" in df.columns
        else ("period" if "period" in df.columns else "month")
    )
    cov_col = (
        "coverage"
        if "coverage" in df.columns
        else ("coverage_90" if "coverage_90" in df.columns else df.columns[-1])
    )

    fig, ax = plt.subplots(figsize=(COL2, HEIGHT_M))
    ax.axhline(0.90, color=PALETTE["red"], lw=1.0, ls="--", label="Target 90%", zorder=1)

    color_cycle = [PALETTE["blue"], PALETTE["orange"], PALETTE["green"]]
    for i, method in enumerate(methods):
        sub = df[df[method_col] == method].sort_values(time_col)
        label = METHOD_LABELS.get(method, method)
        ax.plot(
            pd.to_datetime(sub[time_col]),
            sub[cov_col].values,
            marker="o",
            ms=4,
            color=color_cycle[i],
            label=label,
            zorder=3,
        )

    ax.set_xlabel("Month (OOT)")
    ax.set_ylabel("Empirical Coverage")
    ax.set_title("Temporal Coverage Stability — Top Conformal Variants")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))
    ax.set_ylim(0.70, 1.01)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(8))
    ax.legend(loc="lower right")
    fig.tight_layout()
    _save(fig, "p3_fig3_temporal_stability")


# ── Paper 2: IFRS9 E2E ────────────────────────────────────────────────────────


def _paper2_fig4_sicr_grid() -> None:
    """Fig 4 — SICR trigger optimization: F1/recall/precision vs width threshold."""
    df = pd.read_parquet(DATA_DIR / "sicr_conformal_grid.parquet")

    if df.empty:
        logger.warning("sicr_conformal_grid empty — skipping fig4")
        return

    # Filter to one PD threshold (use the row with best F1)
    # Actual columns: f1_width, precision_width, recall_width_of_missed, ecl_additional
    f1_col = "f1_width" if "f1_width" in df.columns else "f1"
    prec_col = "precision_width" if "precision_width" in df.columns else "precision"
    rec_col = "recall_width_of_missed" if "recall_width_of_missed" in df.columns else "recall"

    best_pd_thr = (
        df.loc[df[f1_col].idxmax(), "pd_threshold"] if "pd_threshold" in df.columns else None
    )
    if best_pd_thr is not None:
        sub = df[df["pd_threshold"] == best_pd_thr].sort_values("width_threshold")
    else:
        sub = df.sort_values("width_threshold")

    fig, ax1 = plt.subplots(figsize=(COL2, HEIGHT_M))
    ax2 = ax1.twinx()
    ax2.spines["right"].set_visible(True)

    ax1.plot(
        sub["width_threshold"],
        sub[f1_col],
        color=PALETTE["blue"],
        marker="o",
        ms=4,
        label="F1 Score",
        zorder=5,
    )
    ax1.plot(
        sub["width_threshold"],
        sub[prec_col],
        color=PALETTE["orange"],
        marker="s",
        ms=4,
        ls="--",
        label="Precision",
    )
    ax1.plot(
        sub["width_threshold"],
        sub[rec_col],
        color=PALETTE["green"],
        marker="^",
        ms=4,
        ls=":",
        label="Recall",
    )

    if "ecl_additional" in sub.columns:
        ax2.fill_between(
            sub["width_threshold"], sub["ecl_additional"] / 1e6, alpha=0.12, color=PALETTE["red"]
        )
        ax2.plot(
            sub["width_threshold"],
            sub["ecl_additional"] / 1e6,
            color=PALETTE["red"],
            lw=1.0,
            ls="-.",
            label="ECL add. ($M)",
        )
        ax2.set_ylabel("Additional ECL (USD M)", color=PALETTE["red"], fontsize=9)
        ax2.tick_params(axis="y", colors=PALETTE["red"])

    # Mark optimal t*
    best_idx = sub[f1_col].idxmax()
    t_star = sub.loc[best_idx, "width_threshold"]
    ax1.axvline(
        t_star, color=PALETTE["purple"], lw=1.0, ls="--", alpha=0.7, label=f"$t^* = {t_star:.2f}$"
    )

    ax1.set_xlabel("Conformal Width Threshold $t$")
    ax1.set_ylabel("Score")
    ax1.set_title(f"SICR Trigger Optimization via Conformal Width (PD thr = {best_pd_thr:.2f})")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=7.5)
    fig.tight_layout()
    _save(fig, "p2_fig4_sicr_grid")


def _paper2_fig5_ecl_alpha_sensitivity() -> None:
    """Fig 5 — ECL additional vs confidence level (alpha sensitivity)."""
    df = pd.read_parquet(DATA_DIR / "ecl_alpha_sensitivity.parquet")

    if df.empty:
        logger.warning("ecl_alpha_sensitivity empty — skipping fig5")
        return

    # Identify alpha/confidence and ECL columns
    alpha_col = next((c for c in df.columns if "alpha" in c.lower()), None)
    conf_col = next(
        (c for c in df.columns if "confidence" in c.lower() or "conf_level" in c.lower()), None
    )
    ecl_col = next((c for c in df.columns if "ecl" in c.lower() and "add" in c.lower()), None)

    if ecl_col is None:
        ecl_col = (
            [c for c in df.columns if "ecl" in c.lower()][0]
            if any("ecl" in c.lower() for c in df.columns)
            else df.columns[-1]
        )
    x_col = conf_col or alpha_col or df.columns[0]

    sub = df.sort_values(x_col)

    fig, ax = plt.subplots(figsize=(COL1 * 1.5, HEIGHT_M))

    ax.fill_between(sub[x_col], sub[ecl_col] / 1e6, alpha=0.15, color=PALETTE["blue"])
    ax.plot(
        sub[x_col],
        sub[ecl_col] / 1e6,
        color=PALETTE["blue"],
        marker="o",
        ms=5,
        label="ECL additional (SICR trigger)",
    )

    # Mark 90% level
    row_90 = sub[sub[x_col].between(0.89, 0.91)]
    if not row_90.empty:
        v90 = row_90.iloc[0][ecl_col] / 1e6
        ax.axhline(v90, color=PALETTE["gray"], lw=0.8, ls=":")
        ax.annotate(
            f"\\$${v90:.1f}M\n@ 90%",
            xy=(row_90.iloc[0][x_col], v90),
            xytext=(10, 8),
            textcoords="offset points",
            fontsize=7.5,
            color=PALETTE["gray"],
        )

    ax.set_xlabel("Confidence Level $1 - \\alpha$")
    ax.set_ylabel("Additional ECL (USD M)")
    ax.set_title("IFRS9: Additional ECL vs.\nConfidence Level")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    _save(fig, "p2_fig5_ecl_alpha_sensitivity")


def _paper2_fig6_bma_vs_cp() -> None:
    """Fig 6 — BMA vs Conformal Mondrian: coverage / width / min-group comparison."""
    status = _load_json(MODELS_DIR / "bma_comparison_status.json")
    # Actual structure: status["results"]["equal"]["overall_bma_coverage", ...]
    res = status.get("results", {}).get("equal", status.get("results", {}))

    labels = ["Empirical Coverage", "Mean Width", "Min-Grade Coverage"]
    cp_vals = [
        res.get("overall_cp_coverage", 0),
        res.get("mean_cp_width", 0),
        res.get("min_grade_cp_coverage", 0),
    ]
    bma_vals = [
        res.get("overall_bma_coverage", 0),
        res.get("mean_bma_width", 0),
        res.get("min_grade_bma_coverage", 0),
    ]

    x = np.arange(len(labels))
    width = 0.32

    fig, ax = plt.subplots(figsize=(COL1 * 1.5, HEIGHT_M))
    bars_cp = ax.bar(
        x - width / 2,
        cp_vals,
        width,
        label="Conformal Mondrian",
        color=PALETTE["blue"],
        edgecolor="white",
        linewidth=0.5,
    )
    bars_bm = ax.bar(
        x + width / 2,
        bma_vals,
        width,
        label="BMA",
        color=PALETTE["orange"],
        edgecolor="white",
        linewidth=0.5,
    )

    def _label_bars(bars: list, vals: list) -> None:
        for bar, v in zip(bars, vals, strict=False):
            if v:
                h = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    h + 0.005,
                    f"{v:.3f}",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                )

    _label_bars(list(bars_cp), cp_vals)
    _label_bars(list(bars_bm), bma_vals)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Value")
    ax.set_title("BMA vs. Conformal Mondrian:\nUncertainty Interval Comparison")
    ax.legend(loc="upper right")
    ax.set_ylim(0, max(cp_vals + bma_vals) * 1.18)
    fig.tight_layout()
    _save(fig, "p2_fig6_bma_vs_cp")


# ── CRPTO: Predict-then-Optimize ─────────────────────────────────────


def _crpto_fig7_uncertainty_baselines() -> None:
    """Fig 7 — 4 uncertainty set methods: coverage / width / min-group bar chart."""
    status = _load_json(MODELS_DIR / "uncertainty_baselines_status.json")

    results = status.get("results", {})
    methods_order = ["conformal_mondrian", "bootstrap", "parametric_gaussian", "ellipsoidal_grade"]
    method_labels_map = {
        "conformal_mondrian": "Mondrian\nCP",
        "bootstrap": "Bootstrap\nset",
        "parametric_gaussian": "Gaussian\nparametric",
        "ellipsoidal_grade": "Ellipsoidal\ngrade",
    }

    metrics = ["empirical_coverage", "avg_width", "min_group_coverage"]
    metric_labels = ["Empirical Coverage", "Mean Width", "Min-Grade Coverage"]
    colors_m = [PALETTE["blue"], PALETTE["orange"], PALETTE["green"], PALETTE["red"]]

    fig, axes = plt.subplots(1, 3, figsize=(COL2 * 1.12, HEIGHT_M))
    nominal = 0.90

    for ax, metric, mlabel in zip(axes, metrics, metric_labels, strict=False):
        vals = [results.get(m, {}).get(metric, 0) for m in methods_order]
        bars = ax.bar(
            range(len(methods_order)), vals, color=colors_m, edgecolor="white", linewidth=0.5
        )

        if metric == "empirical_coverage":
            ax.axhline(nominal, color=PALETTE["red"], lw=1.0, ls="--", label="Target 90%")
        if metric == "avg_width":
            ax.axhline(min(v for v in vals if v > 0), color=PALETTE["lgray"], lw=0.7, ls=":")

        for bar, v in zip(bars, vals, strict=False):
            if v > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.005,
                    f"{v:.3f}",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                )

        ax.set_xticks(range(len(methods_order)))
        ax.set_xticklabels(
            [method_labels_map[m] for m in methods_order], rotation=0, ha="center", fontsize=6.7
        )
        ax.tick_params(axis="x", pad=2)
        ax.set_ylabel(mlabel, fontsize=8)
        ax.set_title(mlabel, fontsize=9)
        if metric == "empirical_coverage":
            ax.legend(fontsize=7)

    fig.suptitle(
        "Uncertainty Set Methods: Coverage, Width, and Group Guarantee\n(OOT $n=276{,}869$, nominal 90%)",
        fontsize=10,
        y=1.02,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    _save(fig, "crpto_fig7_uncertainty_baselines")


def _crpto_fig8_alpha_pareto() -> None:
    """Fig 8 — Alpha sweep Pareto: Mondrian vs Global (coverage × width × eligible loans)."""
    df = pd.read_parquet(DATA_DIR / "alpha_sweep_pareto_both.parquet")

    if df.empty:
        logger.warning("alpha_sweep_pareto_both empty — skipping fig8")
        return

    # Detect variant column
    variant_col = next(
        (c for c in df.columns if "variant" in c.lower() or "method" in c.lower()), None
    )
    alpha_col = next((c for c in df.columns if "alpha" in c.lower()), None)
    cov_col = next((c for c in df.columns if "coverage" in c.lower()), None)
    width_col = next((c for c in df.columns if "width" in c.lower()), None)
    elig_col = next(
        (c for c in df.columns if "eligible" in c.lower() or "n_eligible" in c.lower()), None
    )

    if not all([variant_col, alpha_col, cov_col, width_col]):
        logger.warning(f"alpha_sweep_pareto_both missing columns. Got: {list(df.columns)}")
        return

    fig, axes = plt.subplots(1, 2, figsize=(COL2, HEIGHT_M))

    variants = df[variant_col].unique() if variant_col else ["global", "mondrian"]
    var_colors = {
        v: PALETTE["blue"] if "mond" in str(v).lower() else PALETTE["orange"] for v in variants
    }
    var_labels = {
        v: "Mondrian CP" if "mond" in str(v).lower() else "Global Split-CP" for v in variants
    }

    # Left: width vs coverage scatter (Pareto)
    ax = axes[0]
    ax.axvline(0.90, color=PALETTE["red"], lw=0.8, ls="--", alpha=0.6, label="90% target")
    for var in variants:
        sub = df[df[variant_col] == var].sort_values(alpha_col)
        ax.plot(
            sub[cov_col],
            sub[width_col],
            marker="o",
            ms=5,
            color=var_colors[var],
            label=var_labels[var],
        )
        for idx, (_, row) in enumerate(sub.iterrows()):
            offset_y = 4 if idx % 2 == 0 else -8
            offset_x = 4 if idx < len(sub) - 1 else -24
            ax.annotate(
                f"α={row[alpha_col]:.2f}",
                (row[cov_col], row[width_col]),
                fontsize=6.5,
                xytext=(offset_x, offset_y),
                textcoords="offset points",
                va="center",
            )
    ax.set_xlabel("Empirical Coverage")
    ax.set_ylabel("Mean Interval Width")
    ax.set_title("Coverage–Width Pareto Frontier")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))
    ax.legend(loc="upper left", fontsize=7.5)

    # Right: eligible loans vs alpha
    ax2 = axes[1]
    if elig_col:
        for var in variants:
            sub = df[df[variant_col] == var].sort_values(alpha_col)
            ax2.bar(
                [str(round(a, 2)) for a in sub[alpha_col]],
                sub[elig_col],
                label=var_labels[var],
                color=var_colors[var],
                alpha=0.85,
                edgecolor="white",
            )
        ax2.set_xlabel("Alpha Level")
        ax2.set_ylabel("Eligible Loans (PD-high < 0.10)")
        ax2.set_title("Eligible Loans vs. Alpha")
        ax2.legend(loc="upper right", fontsize=7.5)
        ax2.tick_params(axis="x", rotation=30)
    else:
        axes[1].set_visible(False)

    fig.suptitle(
        "Alpha Sweep: Coverage–Width–Eligibility Trade-off\n(Mondrian vs. Global, $n_{cal}=237{,}584$)",
        fontsize=10,
        y=1.02,
    )
    fig.tight_layout()
    _save(fig, "crpto_fig8_alpha_pareto")


def _crpto_fig9_spo_regret() -> None:
    """Fig 9 — SPO+ decision regret comparison (bar + violin from per-seed data)."""
    status = _load_json(MODELS_DIR / "spo_real_training_status.json")
    results = status.get("results", {})

    # Structure: results.{two_stage, spo_plus, conformal_robust}.{mean_regret, std_regret, per_seed_means}
    display = [
        ("Two-Stage", "two_stage", PALETTE["orange"]),
        ("SPO+", "spo_plus", PALETTE["blue"]),
        ("Conformal\nRobust", "conformal_robust", PALETTE["gray"]),
    ]

    names = [d[0] for d in display]
    means = [results.get(d[1], {}).get("mean_regret", 0) for d in display]
    stds = [results.get(d[1], {}).get("std_regret", 0) for d in display]
    colors = [d[2] for d in display]
    per_seed = [results.get(d[1], {}).get("per_seed_means", []) for d in display]

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(COL2, HEIGHT_M))

    # Left: bar with error bars
    bars = ax.bar(
        names,
        means,
        yerr=stds,
        color=colors,
        edgecolor="white",
        linewidth=0.5,
        capsize=4,
        error_kw={"elinewidth": 1.0, "capthick": 1.0},
    )
    for _i, (bar, mean, std) in enumerate(zip(bars, means, stds, strict=False)):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            mean + std + 0.015,
            f"{mean:.4f}",
            ha="center",
            va="bottom",
            fontsize=7.5,
        )

    if means[0] > 0 and means[1] > 0:
        improvement = (1 - means[1] / means[0]) * 100
        ax.annotate(
            f"−{improvement:.1f}%",
            xy=(0.95, (means[0] + means[1]) / 2),
            xytext=(15, 0),
            textcoords="offset points",
            fontsize=9,
            color=PALETTE["blue"],
            fontweight="bold",
            ha="left",
            va="center",
            arrowprops={"arrowstyle": "-", "color": PALETTE["blue"], "lw": 0.8},
        )
    ax.set_ylabel("Mean Decision Regret")
    ax.set_title("Decision Regret\n(mean ± std, 5 seeds)")

    # Right: per-seed violin (if available)
    if any(len(ps) > 1 for ps in per_seed):
        parts = ax2.violinplot(
            [ps for ps in per_seed if ps],
            positions=list(range(1, sum(1 for ps in per_seed if ps) + 1)),
            showmedians=True,
            showextrema=True,
        )
        for i, pc in enumerate(parts["bodies"]):
            pc.set_facecolor(colors[i])
            pc.set_alpha(0.75)
        valid_names = [n for n, ps in zip(names, per_seed, strict=False) if ps]
        ax2.set_xticks(range(1, len(valid_names) + 1))
        ax2.set_xticklabels(valid_names, fontsize=8)
        ax2.set_ylabel("Per-Seed Mean Regret")
        ax2.set_title("Per-Seed Distribution\n(5 seeds)")
    else:
        ax2.set_visible(False)

    fig.suptitle(
        "SPO+ vs. Two-Stage vs. Conformal Robust: Decision Regret\n"
        "($n_{train}=1000$, $n_{test}=200$ instances/seed, 5 seeds, $n_{items}=100$)",
        fontsize=10,
        y=1.03,
    )
    fig.tight_layout()
    _save(fig, "crpto_fig9_spo_regret")


def _crpto_fig10_cqr_comparison() -> None:
    """Fig 10 — CQR vs Mondrian per-grade coverage comparison."""
    status = _load_json(MODELS_DIR / "cqr_comparison_status.json")
    per_group = status.get("per_group_coverage", {})

    methods_to_plot = {
        "mondrian_splitconf": "Mondrian Split-CP",
        "cqr_asymmetric": "CQR (Asymmetric)",
        "global_splitconf": "Global Split-CP",
    }
    grades = sorted(set().union(*[set(v.keys()) for v in per_group.values()]))

    fig, ax = plt.subplots(figsize=(COL2 * 0.75, HEIGHT_M))
    x = np.arange(len(grades))
    bar_w = 0.25
    colors_b = [PALETTE["blue"], PALETTE["orange"], PALETTE["gray"]]
    offset_map = {m: (i - 1) * bar_w for i, m in enumerate(methods_to_plot)}

    for (method_key, label), color in zip(methods_to_plot.items(), colors_b, strict=False):
        vals = [per_group.get(method_key, {}).get(g, 0) for g in grades]
        ax.bar(
            x + offset_map[method_key],
            vals,
            bar_w,
            label=label,
            color=color,
            edgecolor="white",
            linewidth=0.5,
            alpha=0.9,
        )

    ax.axhline(0.90, color=PALETTE["red"], lw=1.0, ls="--", label="Target 90%")
    ax.set_xticks(x)
    ax.set_xticklabels(grades)
    ax.set_xlabel("Grade")
    ax.set_ylabel("Empirical Coverage")
    ax.set_title("CQR vs. Mondrian CP: Per-Grade Coverage\n(OOT, $\\alpha = 0.10$)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))
    ax.set_ylim(0.40, 1.08)
    ax.legend(loc="lower left", fontsize=7.5)
    fig.tight_layout()
    _save(fig, "crpto_fig10_cqr_per_grade")


def _crpto_fig11_crpto_stability() -> None:
    """Fig 11 — CRPTO vs SPO+ stability under distributional shift."""
    detail_path = DATA_DIR / "crpto_vs_spo_stability_detail.parquet"
    if not detail_path.exists():
        logger.warning("Skipping fig11: {} not found", detail_path)
        return

    detail_df = pd.read_parquet(detail_path)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(COL2, HEIGHT_M))
    periods = detail_df["period"].values
    x = np.arange(len(periods))
    methods = [
        ("two_stage_mean_regret", "two_stage_std_regret", "Two-Stage", PALETTE["orange"]),
        ("spo_plus_mean_regret", "spo_plus_std_regret", "SPO+", PALETTE["blue"]),
        ("conformal_robust_mean_regret", "conformal_robust_std_regret", "CRPTO", PALETTE["green"]),
    ]
    for mean_col, std_col, label, color in methods:
        y_mean = detail_df[mean_col].values
        y_std = detail_df[std_col].values
        ax1.plot(x, y_mean, "-", color=color, label=label, marker="o", markersize=4)
        ax1.fill_between(x, y_mean - y_std, y_mean + y_std, alpha=0.15, color=color)
    ax1_top = ax1.twiny()
    ax1_top.set_xlim(ax1.get_xlim())
    ax1_top.set_xticks(x)
    ax1_top.set_xticklabels([f"{r:.1f}%" for r in detail_df["default_rate"].values * 100])
    ax1_top.set_xlabel("Default Rate")
    ax1.set_xticks(x)
    ax1.set_xticklabels(periods)
    ax1.set_ylabel("Mean Decision Regret")
    ax1.set_title("A. Decision Regret by Period")
    ax1.legend(loc="upper right", fontsize=7)

    cov = detail_df["coverage_90"].values * 100
    width = detail_df["avg_width_90"].values
    ax2.plot(x, cov, "-o", color=PALETTE["blue"], label="Coverage 90%", markersize=5)
    ax2.axhline(y=90, color=PALETTE["red"], linestyle="--", linewidth=1.0, label="Target 90%")
    ax2.set_xticks(x)
    ax2.set_xticklabels(periods)
    ax2.set_ylabel("Coverage (%)", color=PALETTE["blue"])
    ax2.set_ylim(85, 105)
    ax2.tick_params(axis="y", labelcolor=PALETTE["blue"])
    ax2r = ax2.twinx()
    ax2r.plot(x, width, "--s", color=PALETTE["orange"], label="Avg Width", markersize=4)
    ax2r.set_ylabel("Avg Interval Width", color=PALETTE["orange"])
    ax2r.tick_params(axis="y", labelcolor=PALETTE["orange"])
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2r.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc="lower left", fontsize=7)
    ax2.set_title("B. Conformal Coverage by Period")
    fig.suptitle("CRPTO vs SPO+ Stability Under Distributional Shift (OOT 2018-2020)")
    fig.tight_layout()
    _save(fig, "crpto_fig11_crpto_stability")


def _paper3_fig2_global_vs_mondrian() -> None:
    """Fig 2 — Global vs Mondrian per-grade coverage (paired bar chart).

    The single most powerful visual: shows 59% vs 88%+ min-group coverage
    side by side for each credit grade.
    """
    # Global split per-grade coverage from variant benchmark
    df = pd.read_parquet(DATA_DIR / "conformal_variant_benchmark_by_group.parquet")
    var_col = "variant" if "variant" in df.columns else "method"
    grp_col = "group" if "group" in df.columns else "grade"

    grades = ["A", "B", "C", "D", "E", "F", "G"]
    df = df[df[grp_col].astype(str).isin(grades)]
    global_df = df[df[var_col] == "global_split"].set_index(grp_col)["coverage"]

    # Mondrian per-grade coverage from the promoted group metrics
    gm = pd.read_parquet(DATA_DIR / "conformal_group_metrics_mondrian.parquet")
    gm_grp = "group" if "group" in gm.columns else "grade"
    gm_cov = "coverage_90" if "coverage_90" in gm.columns else "coverage"
    mondrian_df = gm.set_index(gm_grp)[gm_cov]

    x = np.arange(len(grades))
    width = 0.35

    fig, ax = plt.subplots(figsize=(COL2, HEIGHT_M))
    bars_g = ax.bar(
        x - width / 2,
        [global_df.get(g, 0) for g in grades],
        width,
        label="Global Split-CP",
        color=PALETTE["gray"],
        edgecolor="white",
        linewidth=0.5,
    )
    bars_m = ax.bar(
        x + width / 2,
        [mondrian_df.get(g, 0) for g in grades],
        width,
        label="Score-Decile Mondrian",
        color=PALETTE["blue"],
        edgecolor="white",
        linewidth=0.5,
    )

    ax.axhline(0.90, color=PALETTE["red"], lw=1.2, ls="--", label="Target 90%", zorder=4)

    # Annotate bars
    for bar in bars_g:
        h = bar.get_height()
        if h > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.005,
                f"{h:.0%}",
                ha="center",
                va="bottom",
                fontsize=6.5,
                color=PALETTE["gray"],
            )
    for bar in bars_m:
        h = bar.get_height()
        if h > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.005,
                f"{h:.0%}",
                ha="center",
                va="bottom",
                fontsize=6.5,
                color=PALETTE["blue"],
            )

    ax.set_xticks(x)
    ax.set_xticklabels(grades)
    ax.set_xlabel("Credit Grade")
    ax.set_ylabel("Empirical Coverage")
    ax.set_title("Per-Grade Coverage: Global Split-CP vs Mondrian ($\\alpha=0.10$, OOT)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))
    ax.set_ylim(0.50, 1.02)
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    _save(fig, "p3_fig2_global_vs_mondrian")


def _paper3_fig6_efficiency_paradox() -> None:
    """Fig 6 — Width-Coverage efficiency paradox scatter.

    Per-grade scatter (x=coverage, y=avg_width) for Global vs Mondrian
    with arrows showing improvement direction.  Demonstrates the
    counter-intuitive finding: Mondrian has BOTH better coverage AND
    narrower intervals.
    """
    # Global split coverage per grade
    by_group = pd.read_parquet(DATA_DIR / "conformal_variant_benchmark_by_group.parquet")
    var_col = "variant" if "variant" in by_group.columns else "method"
    grp_col = "group" if "group" in by_group.columns else "grade"

    grades = ["A", "B", "C", "D", "E", "F", "G"]
    by_group = by_group[by_group[grp_col].astype(str).isin(grades)]
    global_cov = by_group[by_group[var_col] == "global_split"].set_index(grp_col)["coverage"]

    # Mondrian coverage AND width per grade from promoted group metrics
    group_metrics = pd.read_parquet(DATA_DIR / "conformal_group_metrics_mondrian.parquet")
    grp_col2 = "group" if "group" in group_metrics.columns else "grade"
    mondrian_width = group_metrics.set_index(grp_col2)["avg_width_90"].to_dict()
    gm_cov_col = "coverage_90" if "coverage_90" in group_metrics.columns else "coverage"
    mondrian_cov = group_metrics.set_index(grp_col2)[gm_cov_col]

    # Global split has same width for all grades (single quantile)
    global_width_val = 0.9521  # from conformal_variant_selection_status.json

    grade_colors = {
        "A": PALETTE["green"],
        "B": PALETTE["sky"],
        "C": PALETTE["blue"],
        "D": PALETTE["orange"],
        "E": PALETTE["yellow"],
        "F": PALETTE["red"],
        "G": PALETTE["purple"],
    }

    fig, ax = plt.subplots(figsize=(COL1, COL1))

    for g in grades:
        gc = global_cov.get(g, np.nan)
        mc = mondrian_cov.get(g, np.nan)
        gw = global_width_val
        mw = mondrian_width.get(g, np.nan)
        color = grade_colors.get(g, PALETTE["blue"])

        if pd.isna(gc) or pd.isna(mc) or pd.isna(mw):
            continue

        # Global point (hollow circle)
        ax.scatter(gc, gw, s=50, facecolors="none", edgecolors=color, lw=1.2, zorder=5)
        # Mondrian point (filled)
        ax.scatter(mc, mw, s=50, color=color, zorder=6, edgecolors="white", lw=0.5)
        # Arrow from Global to Mondrian
        ax.annotate(
            "",
            xy=(mc, mw),
            xytext=(gc, gw),
            arrowprops={"arrowstyle": "->", "color": color, "lw": 0.8, "alpha": 0.6},
        )
        # Label at Mondrian point
        ax.annotate(
            g,
            (mc, mw),
            textcoords="offset points",
            xytext=(5, 3),
            fontsize=7,
            fontweight="bold",
            color=color,
        )

    ax.axvline(0.90, color=PALETTE["red"], lw=0.8, ls="--", alpha=0.5, label="Target 90%")
    ax.set_xlabel("Empirical Coverage")
    ax.set_ylabel("Mean Interval Width")
    ax.set_title("Efficiency Paradox:\nGlobal (○) → Mondrian (●)")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))

    from matplotlib.lines import Line2D

    ax.legend(
        handles=[
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="none",
                markeredgecolor="k",
                label="Global",
                ms=7,
            ),
            Line2D([0], [0], marker="o", color="w", markerfacecolor="k", ms=7, label="Mondrian"),
        ],
        loc="upper left",
        fontsize=7,
    )
    fig.tight_layout()
    _save(fig, "p3_fig6_efficiency_paradox")


def _paper3_figA1_monthly_coverage_by_grade() -> None:
    """Fig A1 — Faceted monthly coverage by grade (7 panels).

    Shows temporal stability per grade, more granular than the aggregate
    temporal stability figure.
    """
    df = pd.read_parquet(DATA_DIR / "conformal_backtest_monthly_grade.parquet")

    if df.empty:
        logger.warning("conformal_backtest_monthly_grade empty — skipping figA1")
        return

    grades = [g for g in ["A", "B", "C", "D", "E", "F", "G"] if g in df["grade"].unique()]
    n_grades = len(grades)
    if n_grades == 0:
        return

    grade_colors = {
        "A": PALETTE["green"],
        "B": PALETTE["sky"],
        "C": PALETTE["blue"],
        "D": PALETTE["orange"],
        "E": PALETTE["yellow"],
        "F": PALETTE["red"],
        "G": PALETTE["purple"],
    }

    cov_col = "coverage_90" if "coverage_90" in df.columns else "coverage"
    month_col = "month" if "month" in df.columns else "temporal_segment"

    fig, axes = plt.subplots(1, n_grades, figsize=(COL2, HEIGHT_M), sharey=True)
    if n_grades == 1:
        axes = [axes]

    for ax, grade in zip(axes, grades, strict=False):
        sub = df[df["grade"] == grade].sort_values(month_col)
        color = grade_colors.get(grade, PALETTE["blue"])
        ax.plot(
            pd.to_datetime(sub[month_col]),
            sub[cov_col].values,
            color=color,
            marker=".",
            ms=3,
            lw=1.0,
        )
        ax.axhline(0.90, color=PALETTE["red"], lw=0.7, ls="--", alpha=0.5)
        ax.set_title(f"Grade {grade}", fontsize=7)
        ax.tick_params(labelsize=5, axis="x", rotation=90)
        ax.tick_params(labelsize=6, axis="y")
        ax.set_ylim(0.60, 1.05)
        if grade == grades[0]:
            ax.set_ylabel("Coverage", fontsize=7)

    fig.suptitle("Monthly Coverage by Grade — Mondrian CP (OOT)", fontsize=9)
    fig.tight_layout()
    _save(fig, "p3_figA1_monthly_coverage_by_grade")


def _paper3_figA2_coverage_floor_multiplier() -> None:
    """Fig A2 — Coverage floor multiplier adjustment (before/after per grade).

    Shows how multiplier adjustments (A:1.20x, B:1.05x, G:1.05x) push
    coverage above the 90% floor.
    """
    df = pd.read_parquet(DATA_DIR / "conformal_group_coverage_floor_report.parquet")

    if df.empty:
        logger.warning("conformal_group_coverage_floor_report empty — skipping figA2")
        return

    grp_col = "group" if "group" in df.columns else "grade"
    grades = df[grp_col].tolist()
    n = len(grades)

    fig, ax = plt.subplots(figsize=(COL1, HEIGHT_M))

    y = np.arange(n)
    before = df["coverage_before"].values
    after = df["coverage_after"].values
    adjusted = df["adjusted"].values if "adjusted" in df.columns else [False] * n

    for i in range(n):
        color = PALETTE["blue"] if adjusted[i] else PALETTE["gray"]
        ax.plot([before[i], after[i]], [y[i], y[i]], color=color, lw=1.5, zorder=3)
        ax.scatter(before[i], y[i], color="white", edgecolors=color, s=40, zorder=4, lw=1.2)
        ax.scatter(
            after[i],
            y[i],
            color=color,
            s=40,
            zorder=5,
            marker="D",
            edgecolors="white",
            lw=0.5,
        )
        mult = df["multiplier"].iloc[i]
        if adjusted[i]:
            ax.annotate(
                f"×{mult:.2f}",
                (after[i], y[i]),
                textcoords="offset points",
                xytext=(8, 0),
                fontsize=7,
                color=color,
                fontweight="bold",
            )

    ax.axvline(0.90, color=PALETTE["red"], lw=1.0, ls="--", alpha=0.5, label="Target 90%")
    ax.set_yticks(y)
    ax.set_yticklabels(grades)
    ax.set_xlabel("Empirical Coverage")
    ax.set_ylabel("Grade")
    ax.set_title("Coverage Floor Adjustment\n(○ before → ◆ after)")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))

    from matplotlib.lines import Line2D

    ax.legend(
        handles=[
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="none",
                markeredgecolor="k",
                ms=7,
                label="Before",
            ),
            Line2D([0], [0], marker="D", color="w", markerfacecolor="k", ms=6, label="After"),
        ],
        loc="lower right",
        fontsize=7,
    )
    fig.tight_layout()
    _save(fig, "p3_figA2_coverage_floor_multiplier")


def _paper3_fig_nonconformity_scores_by_grade() -> None:
    """Fig — Nonconformity score distribution by grade with quantile thresholds.

    Illustrates WHY Mondrian is necessary: residual distributions differ
    substantially across grades, so a single global quantile leads to systematic
    under-coverage in high-risk grades and over-coverage in low-risk grades.
    """
    df = pd.read_parquet(DATA_DIR / "conformal_intervals_mondrian.parquet")
    required = {"y_true", "y_pred", "grade"}
    if not required.issubset(df.columns):
        logger.warning(
            "nonconformity_scores figure skipped — missing columns in intervals parquet."
        )
        return

    grades = [g for g in ["A", "B", "C", "D", "E", "F", "G"] if g in df["grade"].unique()]
    n_grades = len(grades)
    if n_grades == 0:
        return

    grade_colors = {
        "A": PALETTE["green"],
        "B": PALETTE["sky"],
        "C": PALETTE["blue"],
        "D": PALETTE["orange"],
        "E": PALETTE["yellow"],
        "F": PALETTE["red"],
        "G": PALETTE["purple"],
    }

    fig, axes = plt.subplots(1, n_grades, figsize=(COL2, HEIGHT_M), sharey=False)
    if n_grades == 1:
        axes = [axes]

    global_scores = np.abs(df["y_true"].to_numpy(float) - df["y_pred"].to_numpy(float))
    global_q90 = float(np.quantile(global_scores, 0.90))

    for ax, grade in zip(axes, grades, strict=False):
        sub = df[df["grade"] == grade]
        scores = np.abs(sub["y_true"].to_numpy(float) - sub["y_pred"].to_numpy(float))
        group_q90 = float(np.quantile(scores, 0.90))
        color = grade_colors.get(grade, PALETTE["blue"])

        ax.hist(scores, bins=30, color=color, alpha=0.75, density=True, edgecolor="none")
        ax.axvline(group_q90, color=color, lw=1.4, ls="-", label=f"q̂ᵍ={group_q90:.3f}")
        ax.axvline(global_q90, color=PALETTE["gray"], lw=1.0, ls="--", label=f"q̂={global_q90:.3f}")
        ax.set_title(f"Grade {grade}\n(n={len(sub):,})", fontsize=8)
        ax.set_xlabel("Score", fontsize=7)
        ax.tick_params(labelsize=6)
        if grade == grades[0]:
            ax.set_ylabel("Density", fontsize=7)
        ax.legend(fontsize=5.5, loc="upper right")

    fig.suptitle(
        "Nonconformity Score Distributions by Grade — Motivation for Mondrian CP",
        fontsize=9,
    )
    fig.tight_layout()
    _save(fig, "p3_fig_nonconformity_scores_by_grade")


def _paper3_fig_calibration_stat_tests() -> None:
    """Fig — Cumulative differences plot (MAPIE calibration hypothesis test).

    Reproduces the MAPIE tutorial figure with our Lending Club OOT data.
    Curve within ±2σ bands supports H₀: calibrated. Used in Paper 3 / Cap 06c.
    """
    path = DATA_DIR / "calibration_cumulative_diffs.parquet"
    if not path.exists():
        logger.warning(
            "calibration_cumulative_diffs.parquet not found — run train_pd_model.py first."
        )
        return

    df = pd.read_parquet(path)
    stat_path = DATA_DIR / "statistical_calibration_tests.json"
    stat_tests: dict = {}
    if stat_path.exists():
        import json as _json

        stat_tests = _json.loads(stat_path.read_text(encoding="utf-8"))

    fig, ax = plt.subplots(figsize=(COL2, HEIGHT_M))

    if "cum_diff_uncalibrated" in df.columns:
        ks_raw = stat_tests.get("uncalibrated", {}).get("ks_pvalue", float("nan"))
        ax.plot(
            df["k"],
            df["cum_diff_uncalibrated"],
            color=PALETTE["orange"],
            lw=1.4,
            alpha=0.85,
            label=f"Uncalibrated (KS p={ks_raw:.3f})",
        )
    if "cum_diff_calibrated" in df.columns:
        ks_cal = stat_tests.get("calibrated", {}).get("ks_pvalue", float("nan"))
        ax.plot(
            df["k"],
            df["cum_diff_calibrated"],
            color=PALETTE["blue"],
            lw=1.6,
            label=f"Venn-Abers calibrated (KS p={ks_cal:.3f})",
        )
    if "sigma_upper" in df.columns:
        ax.fill_between(
            df["k"],
            df["sigma_lower"],
            df["sigma_upper"],
            color=PALETTE["gray"],
            alpha=0.12,
            label="±2σ band (H₀: calibrated)",
        )
        ax.plot(df["k"], df["sigma_upper"], color=PALETTE["gray"], lw=0.8, ls="--")
        ax.plot(df["k"], df["sigma_lower"], color=PALETTE["gray"], lw=0.8, ls="--")
    ax.axhline(0, color=PALETTE["gray"], lw=0.7, alpha=0.5)

    ax.set_xlabel("Proportion of Sorted Scores")
    ax.set_ylabel("Cumulative Differences")
    ax.set_title("Calibration Hypothesis Test: Cumulative Differences (OOT, $n=276{,}869$)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    _save(fig, "p3_fig_calibration_stat_tests")


def _crpto_fig16_tail_risk_frontier() -> None:
    """Fig 16 — Tail-risk (CVaR95) vs realized return across the 45-policy robust region.

    Reads the committed Table A20 CSV (no DVC dependency). Visualizes the
    journal-strengthening tail-risk/return trade-off and where the frozen
    economic champion sits relative to the satisficing pass/fail policies.
    """
    csv = (
        REPO_ROOT
        / "reports"
        / "crpto"
        / "tables"
        / "crpto_tableA20_tail_satisficing_challenger_audit.csv"
    )
    if not csv.exists():
        logger.warning("A20 CSV not found — skipping fig16")
        return
    df = pd.read_csv(csv)
    ret = df["realized_total_return"].to_numpy(float) / 1e3
    cvar = df["cvar_95_loss_rate"].to_numpy(float)
    passed = df["satisficing_pass"].astype(bool).to_numpy()
    role = df["paper_role"].astype(str).to_numpy()

    fig, ax = plt.subplots(figsize=(COL2, HEIGHT_M))
    ax.scatter(
        ret[~passed],
        cvar[~passed],
        s=45,
        facecolors="none",
        edgecolors=PALETTE["gray"],
        linewidths=1.0,
        label=f"Satisficing fail (n={int((~passed).sum())})",
        zorder=3,
    )
    ax.scatter(
        ret[passed],
        cvar[passed],
        s=55,
        color=PALETTE["blue"],
        edgecolors="white",
        linewidths=0.5,
        label=f"Satisficing pass (n={int(passed.sum())})",
        zorder=4,
    )
    champ = role == "economic_champion"
    if champ.any():
        cx, cy = float(ret[champ][0]), float(cvar[champ][0])
        ax.scatter(
            [cx],
            [cy],
            s=260,
            marker="*",
            color=PALETTE["orange"],
            edgecolors="black",
            linewidths=0.6,
            label="Frozen economic champion",
            zorder=6,
        )
        ax.annotate(
            f"Champion: ${cx:.1f}K\n" + r"CVaR$_{95}$=" + f"{cy:.3f}",
            (cx, cy),
            textcoords="offset points",
            xytext=(-58, 8),
            fontsize=7.5,
            fontweight="bold",
            color=PALETTE["orange"],
            ha="right",
            bbox={
                "boxstyle": "round,pad=0.18",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.75,
            },
        )
    if passed.any():
        idx = np.where(passed)[0]
        j = int(idx[np.argmin(cvar[idx])])
        ax.annotate(
            "lowest tail-risk\n(satisficing pass)",
            (ret[j], cvar[j]),
            textcoords="offset points",
            xytext=(8, 14),
            fontsize=7,
            color=PALETTE["blue"],
            arrowprops={"arrowstyle": "->", "color": PALETTE["blue"], "lw": 0.7},
        )
    ax.set_xlabel("Realized portfolio return (USD thousands)")
    ax.set_ylabel(r"CVaR$_{95}$ loss rate (tail risk)")
    ax.set_title(r"Tail-Risk vs. Return Across the 45-Policy Robust Region (OOT, $\alpha=0.01$)")
    ax.legend(loc="upper left", fontsize=7.2)
    fig.tight_layout()
    _save(fig, "crpto_fig16_tail_risk_frontier")


def _crpto_fig17_tail_risk_lgd() -> None:
    """Fig 17 — Funded-set tail-risk measures (CVaR / OCE) vs LGD assumption (Table A12)."""
    csv = REPO_ROOT / "reports" / "crpto" / "tables" / "crpto_tableA12_tail_risk_oce_cvar.csv"
    if not csv.exists():
        logger.warning("A12 CSV not found — skipping fig17")
        return
    df = pd.read_csv(csv).sort_values("lgd")
    lgd = df["lgd"].to_numpy(float)

    fig, ax = plt.subplots(figsize=(COL1 * 1.7, HEIGHT_M))
    series = [
        ("cvar_90_loss_rate", r"CVaR$_{90}$", PALETTE["sky"], "o"),
        ("cvar_95_loss_rate", r"CVaR$_{95}$", PALETTE["blue"], "s"),
        ("cvar_99_loss_rate", r"CVaR$_{99}$", PALETTE["red"], "^"),
        ("entropic_oce_theta5", r"OCE ($\theta=5$)", PALETTE["green"], "D"),
        ("mean_loss_rate", "Mean (no tail)", PALETTE["gray"], "v"),
    ]
    for col, lab, c, mk in series:
        if col in df.columns:
            ax.plot(lgd, df[col].to_numpy(float), marker=mk, color=c, label=lab, ms=5)
    ax.axvline(0.45, color=PALETTE["black"], lw=0.8, ls=":", label="Champion LGD = 0.45")
    ax.axhline(0.0, color=PALETTE["lgray"], lw=0.7)
    ax.set_xlabel("Loss Given Default (LGD)")
    ax.set_ylabel("Funded-set loss rate")
    ax.set_title("Tail Risk of the Frozen Funded Set vs. LGD Assumption")
    ax.legend(loc="upper left", fontsize=7.0)
    fig.tight_layout()
    _save(fig, "crpto_fig17_tail_risk_lgd")


def _crpto_fig18_tail_constrained_frontier() -> None:
    """Fig 18 — A22 efficient return-vs-CVaR frontier under the tail constraint.

    Reads the committed Table A22 CSV (no DVC dependency). Each point is the
    highest-return alpha01-safe policy admissible under a decision-time CVaR cap;
    the frozen economic champion sits at the high-return, high-CVaR corner.
    """
    csv = (
        REPO_ROOT
        / "reports"
        / "crpto"
        / "tables"
        / "crpto_tableA22_tail_constrained_reoptimization.csv"
    )
    if not csv.exists():
        logger.warning("A22 CSV not found — skipping fig18")
        return
    df = pd.read_csv(csv).sort_values("selected_decision_time_cvar95")
    cvar = df["selected_decision_time_cvar95"].to_numpy(float)
    ret = df["selected_realized_total_return"].to_numpy(float) / 1e3
    role = df["selected_paper_role"].astype(str).to_numpy()

    fig, ax = plt.subplots(figsize=(COL2, HEIGHT_M))
    ax.plot(
        cvar,
        ret,
        "-o",
        color=PALETTE["blue"],
        ms=5,
        lw=1.3,
        label=r"Efficient frontier (max return $\mid$ CVaR$_{95}\leq$ cap)",
        zorder=3,
    )
    ax.scatter(
        [float(cvar[0])],
        [float(ret[0])],
        s=80,
        marker="D",
        color=PALETTE["green"],
        edgecolors="white",
        linewidths=0.5,
        label="Tightest tail cap (challenger end)",
        zorder=5,
    )
    champ = role == "economic_champion"
    if champ.any():
        cx, cy = float(cvar[champ][0]), float(ret[champ][0])
        ax.scatter(
            [cx],
            [cy],
            s=260,
            marker="*",
            color=PALETTE["orange"],
            edgecolors="black",
            linewidths=0.6,
            label="Economic champion (official)",
            zorder=6,
        )
        ax.annotate(
            f"Champion: ${cy:.1f}K\n" + r"CVaR$_{95}$=" + f"{cx:.3f}",
            (cx, cy),
            textcoords="offset points",
            xytext=(-44, -28),
            ha="right",
            va="top",
            fontsize=7.5,
            fontweight="bold",
            color=PALETTE["orange"],
            bbox={
                "boxstyle": "round,pad=0.18",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.75,
            },
        )
    ax.set_xlabel(r"Decision-time CVaR$_{95}$ cap (conformal worst case)")
    ax.set_ylabel("Realized portfolio return (USD thousands)")
    ax.set_title(r"A22 — Return vs. Tail-Risk Frontier Under the CVaR Constraint ($\alpha=0.01$)")
    ax.legend(loc="lower right", fontsize=7.2)
    fig.tight_layout()
    _save(fig, "crpto_fig18_tail_constrained_frontier")


def _crpto_fig19_online_coverage_aci() -> None:
    """Fig 19 — A24 per-vintage coverage, cumulative coverage and ACI alpha_t.

    Reads the committed Table A24 CSV. Shows that coverage holds across the OOT
    vintage sequence and that the Gibbs-Candes ACI target barely drifts, i.e. an
    online controller would have little to do on this static OOT.
    """
    csv = (
        REPO_ROOT / "reports" / "crpto" / "tables" / "crpto_tableA24_online_conformal_stability.csv"
    )
    if not csv.exists():
        logger.warning("A24 CSV not found — skipping fig19")
        return
    df = pd.read_csv(csv)
    x = np.arange(len(df))
    periods = df["period"].astype(str).to_numpy()
    cov = df["coverage_90"].to_numpy(float)
    cum = df["cumulative_coverage_90"].to_numpy(float)
    alpha_t = df["aci_alpha_target_before"].to_numpy(float)

    fig, ax = plt.subplots(figsize=(COL2, HEIGHT_M))
    ax.plot(x, cov, "-o", color=PALETTE["blue"], ms=5, label="Per-vintage coverage")
    ax.plot(x, cum, "--s", color=PALETTE["green"], ms=4, label="Cumulative (streaming) coverage")
    ax.axhline(0.90, color=PALETTE["red"], lw=0.9, ls=":", label="Target 90%")
    ax.set_ylim(0.88, 1.005)
    ax.set_xticks(x)
    ax.set_xticklabels(periods, rotation=45, ha="right", fontsize=6.5)
    ax.set_xlabel("")
    ax.set_ylabel("Conformal coverage (90% target)")

    ax2 = ax.twinx()
    ax2.plot(
        x, alpha_t, "-^", color=PALETTE["orange"], ms=4, lw=0.9, label=r"ACI target $\alpha_t$"
    )
    ax2.set_ylabel(r"ACI target $\alpha_t$", color=PALETTE["orange"])
    ax2.tick_params(axis="y", labelcolor=PALETTE["orange"])

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.26),
        ncol=2,
        fontsize=7.0,
    )
    ax.set_title("A24 — Online Conformal Stability Across the OOT Vintage Sequence")
    fig.subplots_adjust(left=0.10, right=0.90, bottom=0.27, top=0.86)
    _save(fig, "crpto_fig19_online_coverage_aci")


# ── Dispatch ──────────────────────────────────────────────────────────────────

PAPER3_FIGS = [
    _paper3_fig1_variant_scatter,
    _paper3_fig2_global_vs_mondrian,
    _paper3_fig2_grade_coverage_heatmap,
    _paper3_fig3_temporal_stability,
    _paper3_fig6_efficiency_paradox,
    _paper3_fig_nonconformity_scores_by_grade,
    _paper3_fig_calibration_stat_tests,
    _paper3_figA1_monthly_coverage_by_grade,
    _paper3_figA2_coverage_floor_multiplier,
]
PAPER2_FIGS = [
    _paper2_fig4_sicr_grid,
    _paper2_fig5_ecl_alpha_sensitivity,
    _paper2_fig6_bma_vs_cp,
]
# ── Dossier figures (Spanish book chapters; house-style restyle) ───────────────

_PD_MODELS = [
    ("LogReg baseline", "y_prob_lr", PALETTE["gray"]),
    ("CatBoost tuned", "y_prob_cb_tuned", PALETTE["blue"]),
    ("CatBoost calibrado", "pd_calibrated", PALETTE["red"]),
]


def _dossier_pd_roc() -> None:
    """ROC OOT for the candidate PD models (restyled, AUC-annotated)."""
    from sklearn.metrics import roc_auc_score, roc_curve

    df = pd.read_parquet(DATA_DIR / "test_predictions.parquet")
    y = df["y_true"].to_numpy()
    fig, ax = plt.subplots(figsize=(COL2 * 0.7, HEIGHT_M))
    ax.plot([0, 1], [0, 1], color=PALETTE["lgray"], linestyle="--", linewidth=1.0)
    for label, col, color in _PD_MODELS:
        fpr, tpr, _ = roc_curve(y, df[col].to_numpy())
        auc = roc_auc_score(y, df[col].to_numpy())
        ax.plot(fpr, tpr, color=color, label=f"{label} (AUC = {auc:.4f})")
    ax.set_xlabel("Tasa de falsos positivos")
    ax.set_ylabel("Tasa de verdaderos positivos")
    ax.set_title("ROC OOT — modelos PD candidatos")
    ax.legend(loc="lower right", fontsize=7.5)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    fig.tight_layout()
    _save_editorial(fig, "pd_roc_curve")


def _dossier_pd_pr() -> None:
    """Precision–recall OOT for the candidate PD models (AP-annotated)."""
    from sklearn.metrics import average_precision_score, precision_recall_curve

    df = pd.read_parquet(DATA_DIR / "test_predictions.parquet")
    y = df["y_true"].to_numpy()
    prevalence = float(y.mean())
    fig, ax = plt.subplots(figsize=(COL2 * 0.7, HEIGHT_M))
    for label, col, color in _PD_MODELS:
        prec, rec, _ = precision_recall_curve(y, df[col].to_numpy())
        ap = average_precision_score(y, df[col].to_numpy())
        ax.plot(rec, prec, color=color, label=f"{label} (AP = {ap:.4f})")
    ax.axhline(
        prevalence,
        color=PALETTE["lgray"],
        linestyle="--",
        linewidth=1.0,
        label=f"Prevalencia ({prevalence:.3f})",
    )
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precisión")
    ax.set_title("Curva precisión–recall OOT — modelos PD")
    ax.legend(loc="upper right", fontsize=7.5)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    fig.tight_layout()
    _save_editorial(fig, "pd_pr_curve")


def _dossier_pd_reliability() -> None:
    """Reliability curve before/after calibration (quantile bins, restyled).

    Recomputed from the frozen ``test_predictions.parquet`` with quantile bins so
    the high-PD tail is stable (the uniform-bin artifact is noisy where few loans
    fall), keeping the same source as the ROC/PR panels.
    """
    from sklearn.calibration import calibration_curve

    df = pd.read_parquet(DATA_DIR / "test_predictions.parquet")
    y = df["y_true"].to_numpy()
    series = [
        ("CatBoost sin calibrar", "y_prob_cb_tuned", PALETTE["orange"]),
        ("CatBoost calibrado", "pd_calibrated", PALETTE["blue"]),
    ]
    top = 0.0
    curves = []
    for label, col, color in series:
        frac_pos, mean_pred = calibration_curve(
            y, df[col].to_numpy(), n_bins=15, strategy="quantile"
        )
        curves.append((label, mean_pred, frac_pos, color))
        top = max(top, float(mean_pred.max()), float(frac_pos.max()))
    top *= 1.05
    fig, ax = plt.subplots(figsize=(COL2 * 0.58, HEIGHT_M))
    ax.plot(
        [0, top],
        [0, top],
        color=PALETTE["lgray"],
        linestyle="--",
        linewidth=1.0,
        label="Calibración perfecta",
    )
    for label, mean_pred, frac_pos, color in curves:
        ax.plot(mean_pred, frac_pos, marker="o", markersize=3, color=color, label=label)
    ax.set_xlabel("Probabilidad media predicha")
    ax.set_ylabel("Frecuencia observada")
    ax.set_title("Curva de fiabilidad — calibración PD")
    ax.legend(loc="upper left", fontsize=7.5)
    ax.set_xlim(0, top)
    ax.set_ylim(0, top)
    fig.tight_layout()
    _save_editorial(fig, "pd_reliability_curve")


def _crpto_fig21_end_to_end_arc() -> None:
    """Fig 21 — end-to-end CRPTO arc: PD -> conformal -> robust LP -> funded set -> ECL.

    Hand-laid flow diagram (no data dependency) summarizing the full thesis arc
    with the frozen headline number at each stage. Title-style house figure.
    """
    stages = [
        ("Calibrated PD", "CatBoost + Venn-Abers", "AUC 0.7124\nECE 0.0064", PALETTE["blue"]),
        (
            "Mondrian\nconformal",
            "Upper endpoint u(α)",
            "cov 92.97%\nmin-grp 91.90%",
            PALETTE["sky"],
        ),
        ("Robust\nportfolio LP", "ũ(α,γ) as risk cap", "τ=0.175  γ=0.45", PALETTE["green"]),
        (
            "Funded set\n+ certificate",
            "Exact α-safe audit",
            "$170,464.54\nV=0.03645",
            PALETTE["orange"],
        ),
        ("IFRS9 ECL\nprovision", "SICR conformal", "$875.9M\n[455.4, 1563.3]", PALETTE["red"]),
    ]
    n = len(stages)
    fig, ax = plt.subplots(figsize=(COL2, HEIGHT_M))
    ax.set_xlim(0, n)
    ax.set_ylim(0, 1)
    ax.axis("off")
    box_w, box_h, y0 = 0.78, 0.42, 0.29
    for i, (title, sub, metric, color) in enumerate(stages):
        x = i + 0.5
        rect = plt.Rectangle(
            (x - box_w / 2, y0),
            box_w,
            box_h,
            facecolor=color,
            alpha=0.16,
            edgecolor=color,
            linewidth=1.4,
            zorder=2,
        )
        ax.add_patch(rect)
        ax.text(
            x,
            y0 + box_h - 0.075,
            title,
            ha="center",
            va="center",
            fontsize=8.3,
            fontweight="bold",
            color="black",
            zorder=3,
        )
        ax.text(
            x,
            y0 + box_h / 2 - 0.02,
            sub,
            ha="center",
            va="center",
            fontsize=6.6,
            color="#333333",
            style="italic",
            zorder=3,
        )
        ax.text(
            x,
            y0 + 0.06,
            metric,
            ha="center",
            va="center",
            fontsize=6.8,
            color=color,
            fontweight="bold",
            zorder=3,
        )
        if i < n - 1:
            ax.annotate(
                "",
                xy=(x + box_w / 2 + 0.21, y0 + box_h / 2),
                xytext=(x + box_w / 2 + 0.01, y0 + box_h / 2),
                arrowprops={"arrowstyle": "-|>", "color": PALETTE["gray"], "lw": 1.6},
                zorder=1,
            )
    ax.text(
        n / 2,
        0.93,
        "The CRPTO arc: from calibrated PD to auditable provision",
        ha="center",
        va="center",
        fontsize=9.5,
        fontweight="bold",
    )
    ax.text(
        n / 2,
        0.10,
        "Conformal uncertainty (interval width) drives both the funded-set decision "
        "and the IFRS9 staging signal.",
        ha="center",
        va="center",
        fontsize=7.0,
        color="#444444",
    )
    fig.tight_layout()
    _save(fig, "crpto_fig21_end_to_end_arc")


def _crpto_fig25_price_of_robustness_scaling() -> None:
    """Fig 25 — price of robustness scales with panel default rate (A34).

    Frozen external applications (Freddie green/combined/red and Prosper) show a
    positive premium that increases monotonically with the panel default rate.
    The selected Lending Club champion is drawn as a contrasting favorable
    reference line (it is a single selected point, not part of the default-rate
    series). Data: models/crpto_multidataset_external_status.json.
    """
    status = _load_json(MODELS_DIR / "crpto_multidataset_external_status.json")
    seg_label = {
        "green": "Freddie green",
        "both": "Freddie combined",
        "red": "Freddie red",
    }
    pts: list[tuple[str, float, float]] = []
    for seg in status["freddie_segment_sensitivity"]:
        if seg["segment"] in seg_label:
            pts.append(
                (
                    seg_label[seg["segment"]],
                    float(seg["default_rate"]) * 100.0,
                    float(seg["price_of_robustness_pct"]) * 100.0,
                )
            )
    for rep in status["external_replications"]:
        if rep["dataset"] == "Prosper":
            pts.append(
                (
                    "Prosper",
                    float(rep["default_rate"]) * 100.0,
                    float(rep["price_of_robustness_pct"]) * 100.0,
                )
            )
    pts.sort(key=lambda r: r[1])
    labels = [p[0] for p in pts]
    x = np.array([p[1] for p in pts])
    y = np.array([p[2] for p in pts])

    lc_price = -10.56  # selected Lending Club champion (frozen field)

    fig, ax = plt.subplots(figsize=(COL2, HEIGHT_M))
    ax.set_xscale("log")
    ax.set_xlim(0.4, 55)
    ax.set_ylim(-13.5, 12.5)
    ax.axhline(0.0, color=PALETTE["gray"], lw=1.0, ls="--", zorder=1)
    ax.axhline(
        lc_price,
        color=PALETTE["orange"],
        lw=1.4,
        ls=":",
        zorder=2,
        label="Lending Club selected champion (−10.56%)",
    )
    ax.plot(
        x,
        y,
        "-o",
        color=PALETTE["green"],
        lw=1.7,
        ms=7,
        zorder=3,
        label="Frozen application (no champion search)",
    )
    for lab, xi, yi in zip(labels, x, y, strict=True):
        ax.annotate(
            f"{lab}\n+{yi:.2f}%",
            (xi, yi),
            textcoords="offset points",
            xytext=(7, 7),
            fontsize=6.5,
            color=PALETTE["green"],
            fontweight="bold",
        )
    ax.text(0.46, 1.2, "robustness costs a premium", fontsize=6.4, color="#666", style="italic")
    ax.text(0.46, -2.6, "robustness adds value", fontsize=6.4, color="#666", style="italic")
    ax.set_xticks([0.5, 1, 2, 5, 10, 30])
    ax.set_xticklabels(["0.5", "1", "2", "5", "10", "30"])
    ax.tick_params(which="minor", bottom=False)
    ax.set_xlabel("Panel default rate (%, log scale)")
    ax.set_ylabel("Price of robustness (%)")
    ax.set_title("Price of robustness scales with panel default risk")
    ax.legend(loc="lower right", fontsize=6.6)
    fig.tight_layout()
    _save(fig, "crpto_fig25_price_of_robustness_scaling")


DOSSIER_FIGS = [
    _dossier_pd_roc,
    _dossier_pd_pr,
    _dossier_pd_reliability,
]


CRPTO_FIGS = [
    _crpto_fig7_uncertainty_baselines,
    _crpto_fig8_alpha_pareto,
    _crpto_fig9_spo_regret,
    _crpto_fig10_cqr_comparison,
    _crpto_fig11_crpto_stability,
    _crpto_fig16_tail_risk_frontier,
    _crpto_fig17_tail_risk_lgd,
    _crpto_fig18_tail_constrained_frontier,
    _crpto_fig19_online_coverage_aci,
    _crpto_fig21_end_to_end_arc,
    _crpto_fig25_price_of_robustness_scaling,
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate publication-quality figures.")
    parser.add_argument("--paper", choices=["crpto", "all"], default="crpto")
    args = parser.parse_args()

    figs_to_run: list = []
    if args.paper in ("crpto", "all"):
        figs_to_run.extend(CRPTO_FIGS)
        figs_to_run.extend(DOSSIER_FIGS)

    logger.info(f"Generating {len(figs_to_run)} figures → {OUT_DIR}")
    errors = []
    for fn in figs_to_run:
        try:
            fn()
        except Exception as exc:
            logger.error(f"{fn.__name__}: {exc}")
            errors.append((fn.__name__, str(exc)))

    logger.info(f"Done. {len(figs_to_run) - len(errors)} figures saved, {len(errors)} errors.")
    if errors:
        for name, err in errors:
            logger.warning(f"  FAILED: {name} — {err}")

    status = {
        **build_artifact_metadata(schema_version="2026-03-21.1"),
        "generated_at_utc": pd.Timestamp.utcnow().isoformat(),
        "output_dir": OUT_DIR.relative_to(REPO_ROOT).as_posix(),
        "figures_attempted": len(figs_to_run),
        "figures_succeeded": len(figs_to_run) - len(errors),
        "errors": dict(errors),
        "files": sorted(str(p.name) for p in OUT_DIR.glob("*.pdf")),
    }
    out_json = MODELS_DIR / "paper_figures_status.json"
    out_json.write_text(
        __import__("json").dumps(status, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info(f"Status written → {out_json}")


if __name__ == "__main__":
    main()
