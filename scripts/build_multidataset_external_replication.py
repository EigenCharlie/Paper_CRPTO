"""Build curated multidataset external-replication tables and figures.

This script reads only local, curated CSV inputs under
``reports/crpto/multidataset/source``. It does not point back to the exploratory
laboratory, does not use credentials, and does not touch the Lending Club
champion artifacts.

Usage:
    uv run python scripts/build_multidataset_external_replication.py
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from loguru import logger

from src.utils.script_helpers import write_json, write_table

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "reports" / "crpto" / "multidataset" / "source"
TABLE_DIR = ROOT / "reports" / "crpto" / "tables"
FIGURE_DIR = ROOT / "reports" / "crpto" / "figures"
BOOK_FIGURE_DIR = ROOT / "book" / "assets" / "figures" / "publication"
STATUS_PATH = ROOT / "models" / "crpto_multidataset_external_status.json"

TABLE_A25 = "crpto_tableA25_external_replication_gate"
TABLE_A26 = "crpto_tableA26_external_candidate_sensitivity"
TABLE_A27 = "crpto_tableA27_freddie_horizon_sensitivity"
TABLE_A28 = "crpto_tableA28_external_lp_exhaustiveness"
TABLE_A29 = "crpto_tableA29_freddie_mondrian_sparse_group_audit"
TABLE_A30 = "crpto_tableA30_external_metric_intervals"
TABLE_A31 = "crpto_tableA31_external_subperiod_metrics"
TABLE_A32 = "crpto_tableA32_prosper_default_definition_sensitivity"
TABLE_A33 = "crpto_tableA33_freddie_segment_sensitivity"
FIG22 = "crpto_fig22_external_replication"
FIG23 = "crpto_fig23_external_candidate_sensitivity"
FIG24 = "crpto_fig24_freddie_all_candidate_certificate"

PALETTE = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "red": "#D55E00",
    "purple": "#CC79A7",
    "gray": "#666666",
    "light_gray": "#DDDDDD",
}


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


plt.rcParams.update(
    {
        # TrueType (Type 42) keeps PDF text selectable/extractable and avoids
        # Type 3 subset glyphs that publisher font checkers flag.
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif", "serif"],
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linestyle": "--",
        "lines.linewidth": 1.6,
    }
)


def _read_source(name: str) -> pd.DataFrame:
    path = SOURCE_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing curated multidataset source: {path}")
    return pd.read_csv(path)


def _save_figure(fig: plt.Figure, name: str) -> list[Path]:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    BOOK_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for ext in ("png", "pdf"):
        path = FIGURE_DIR / f"{name}.{ext}"
        fig.savefig(path)
        shutil.copy2(path, BOOK_FIGURE_DIR / path.name)
        logger.info("Wrote {}", path.relative_to(ROOT))
        written.append(path)
    plt.close(fig)
    return written


def _label_dataset(name: str) -> str:
    if "Prosper" in name:
        return "Prosper"
    if "Freddie" in name:
        return "Freddie FM48"
    return name


def _candidate_cap_to_number(value: Any, available: int) -> int:
    if str(value).lower() == "all":
        return int(available)
    return int(value)


def _build_external_gate_table(main: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in main.iterrows():
        dataset = _label_dataset(str(row["dataset"]))
        rows.append(
            {
                "dataset": dataset,
                "credit_product": (
                    "Marketplace personal loans"
                    if dataset == "Prosper"
                    else "Single-family mortgages"
                ),
                "external_role": "main external economic replication",
                "n_rows": int(row["rows_total"]),
                "default_rate": float(row["default_rate"]),
                "auc_roc": float(row["auc_roc"]),
                "pr_auc": float(row["pr_auc"]),
                "brier": float(row["brier"]),
                "coverage_90": float(row["coverage_90"]),
                "min_group_coverage_90": float(row["min_group_coverage_90"]),
                "alpha01_coverage": float(row["coverage_alpha01"]),
                "oot_candidates": int(row["available_oot_candidates"]),
                "lp_candidate_cap": str(row["lp_candidate_cap"]),
                "robust_objective": float(row["robust_objective_best"]),
                "price_of_robustness_pct": float(row["price_of_robustness_pct"]),
                "gate": "pass",
            }
        )
    return pd.DataFrame(rows)


def _build_candidate_table(compact: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in compact.iterrows():
        dataset = _label_dataset(str(row["dataset"]))
        rows.append(
            {
                "dataset": dataset,
                "screen": row["strategy"],
                "candidate_cap": str(row["candidate_cap"]),
                "available_candidates": int(row["available_candidates"]),
                "runs": int(row["runs"]),
                "robust_objective_mean": float(row["robust_objective_mean"]),
                "robust_objective_min": float(row["robust_objective_min"]),
                "robust_objective_max": float(row["robust_objective_max"]),
                "nonrobust_objective_mean": float(row["nonrobust_objective_mean"]),
                "robust_n_funded_mean": float(row["robust_n_funded_mean"]),
            }
        )
    return pd.DataFrame(rows)


def _build_freddie_horizon_table(freddie: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in freddie.iterrows():
        rows.append(
            {
                "variant": row["run_label"],
                "color_group": row["variant"],
                "window_months": int(row["window_months"]),
                "n_rows": int(row["rows_total"]),
                "default_rate": float(row["default_rate"]),
                "auc_roc": float(row["auc_roc"]),
                "pr_auc": float(row["pr_auc"]),
                "coverage_90": float(row["coverage_90"]),
                "alpha01_coverage": float(row["coverage_alpha01"]),
                "coverage90_pass": bool(row["coverage90_pass"]),
                "alpha01_pass": bool(row["alpha01_pass"]),
                "screening_robust_objective": float(row["robust_objective"]),
                "recommendation": row["recommendation"],
            }
        )
    return pd.DataFrame(rows).sort_values(["window_months", "color_group"])


def _build_lp_exhaustiveness_table(lp: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in lp.iterrows():
        dataset = "Prosper" if row["dataset"] == "prosper" else "Freddie FM48"
        rows.append(
            {
                "dataset": dataset,
                "candidate_cap": str(row["candidate_cap"]),
                "available_candidates": int(row["available_candidates"]),
                "n_candidates": int(row["n_candidates"]),
                "robust_objective": float(row["robust_objective"]),
                "nonrobust_objective": float(row["nonrobust_objective"]),
                "price_of_robustness_pct": float(row["price_of_robustness_pct"]),
                "robust_objective_boot_low": float(row["robust_objective_boot_low"]),
                "robust_objective_boot_high": float(row["robust_objective_boot_high"]),
                "robust_n_funded": int(row["robust_n_funded"]),
                "robust_max_funded_rank": int(row["robust_max_funded_rank"]),
                "solver_success": bool(row["robust_solver_success"])
                and bool(row["nonrobust_solver_success"]),
            }
        )
    return pd.DataFrame(rows)


def _build_mondrian_sparse_table(summary: pd.DataFrame) -> pd.DataFrame:
    return summary[
        ["scope", "n_groups", "min_coverage_90", "min_coverage_alpha01", "test_rows"]
    ].copy()


def _build_metric_intervals_table(intervals: pd.DataFrame) -> pd.DataFrame:
    return intervals[["dataset", "metric", "estimate", "ci_low", "ci_high", "method", "n"]].copy()


def _build_subperiod_table(subperiods: pd.DataFrame) -> pd.DataFrame:
    return subperiods[
        [
            "dataset",
            "period",
            "n",
            "defaults",
            "default_rate",
            "auc_roc",
            "pr_auc",
            "coverage_90",
            "coverage_alpha01",
            "economic_candidates",
        ]
    ].copy()


def _build_prosper_default_table(prosper_defaults: pd.DataFrame) -> pd.DataFrame:
    return prosper_defaults[
        [
            "variant",
            "rows_total",
            "default_rate",
            "auc_roc",
            "coverage_90",
            "min_group_coverage_90",
            "alpha01_coverage",
            "coverage90_pass",
            "alpha01_pass",
            "available_oot_candidates",
            "robust_objective_all_candidates",
            "price_of_robustness_pct",
        ]
    ].copy()


def _build_freddie_segment_table(segments: pd.DataFrame) -> pd.DataFrame:
    return segments[
        [
            "segment",
            "rows_total",
            "default_rate",
            "auc_roc",
            "coverage_90",
            "min_group_coverage_90",
            "alpha01_coverage",
            "coverage90_pass",
            "alpha01_pass",
            "available_oot_candidates",
            "robust_objective_all_candidates",
            "price_of_robustness_pct",
            "all_lp_solved",
            "max_funded_rank",
            "funded_outside_top250k",
        ]
    ].copy()


def _plot_external_replication(table: pd.DataFrame) -> list[Path]:
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4))
    labels = table["dataset"].tolist()
    colors = [PALETTE["orange"], PALETTE["blue"]]

    ax = axes[0]
    x = range(len(table))
    ax.bar(
        [i - 0.18 for i in x], table["coverage_90"], width=0.34, label="90% coverage", color=colors
    )
    ax.bar(
        [i + 0.18 for i in x],
        table["alpha01_coverage"],
        width=0.34,
        label="alpha 0.01 coverage",
        color=[PALETTE["green"], PALETTE["purple"]],
    )
    ax.axhline(0.90, color=PALETTE["red"], linestyle="--", linewidth=1.0, label="90% target")
    ax.axhline(0.99, color=PALETTE["gray"], linestyle=":", linewidth=1.0, label="99% target")
    ax.set_ylim(0.86, 1.01)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))
    ax.set_xticks(list(x), labels)
    ax.set_ylabel("Empirical coverage")
    ax.set_title("Conformal gates")

    ax = axes[1]
    objective_m = table["robust_objective"] / 1_000_000
    bars = ax.bar(labels, objective_m, color=colors)
    for bar, candidates in zip(bars, table["oot_candidates"], strict=False):
        ax.annotate(
            f"{candidates:,.0f} OOT",
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7,
        )
    ax.set_ylabel("Robust LP objective (millions)")
    ax.set_title("Economic replication")
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("${x:.1f}M"))

    fig.suptitle("External CRPTO replications preserve conformal gates and positive LP value")
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        legend_labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.02),
        ncol=4,
        frameon=True,
    )
    fig.tight_layout(rect=(0, 0.18, 1, 0.93))
    return _save_figure(fig, FIG22)


def _plot_candidate_sensitivity(candidate: pd.DataFrame) -> list[Path]:
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=False)
    for ax, dataset in zip(axes, ["Prosper", "Freddie FM48"], strict=True):
        subset = candidate.loc[candidate["dataset"] == dataset].copy()
        available = int(subset["available_candidates"].max())
        subset["cap_n"] = subset["candidate_cap"].map(
            lambda value, available=available: _candidate_cap_to_number(value, available)
        )
        for strategy, color, marker in [
            ("top_net_return", PALETTE["blue"], "o"),
            ("random", PALETTE["orange"], "s"),
        ]:
            s = subset.loc[subset["screen"] == strategy].sort_values("cap_n")
            if s.empty:
                continue
            ax.plot(
                s["cap_n"],
                s["robust_objective_mean"],
                marker=marker,
                color=color,
                label=strategy.replace("_", " "),
            )
            if strategy == "random":
                ax.fill_between(
                    s["cap_n"].to_numpy(dtype=float),
                    s["robust_objective_min"].to_numpy(dtype=float),
                    s["robust_objective_max"].to_numpy(dtype=float),
                    color=color,
                    alpha=0.15,
                    linewidth=0,
                )
        ax.set_xscale("log")
        ax.set_title(dataset)
        ax.set_xlabel("Candidate cap")
        ax.set_ylabel("Robust objective")
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda value, _: f"${value / 1_000:.0f}K")
        )
        ax.legend(loc="lower right", frameon=True)
    fig.suptitle("Portfolio value stabilizes as candidate pools expand")
    fig.tight_layout()
    return _save_figure(fig, FIG23)


def _plot_freddie_all_candidate_certificate(lp: pd.DataFrame) -> list[Path]:
    freddie = lp.loc[lp["dataset"] == "Freddie FM48"].copy()
    freddie["cap_n"] = freddie["candidate_cap"].map(
        lambda value: _candidate_cap_to_number(value, int(freddie["available_candidates"].max()))
    )
    freddie = freddie.sort_values("cap_n")

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    ax = axes[0]
    ax.plot(
        freddie["cap_n"],
        freddie["robust_objective"] / 1_000_000,
        marker="o",
        color=PALETTE["blue"],
        label="Robust",
    )
    ax.plot(
        freddie["cap_n"],
        freddie["nonrobust_objective"] / 1_000_000,
        marker="s",
        color=PALETTE["orange"],
        label="Nonrobust",
    )
    ax.set_xscale("log")
    ax.set_xlabel("Freddie candidate cap")
    ax.set_ylabel("Objective (millions)")
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("${x:.3f}M"))
    ax.set_title("Objective is unchanged")
    ax.legend(frameon=True, loc="lower right")

    ax = axes[1]
    all_row = freddie.loc[freddie["candidate_cap"].astype(str).str.lower() == "all"].iloc[0]
    bars = ax.bar(
        ["All OOT candidates", "Worst funded rank"],
        [all_row["available_candidates"], all_row["robust_max_funded_rank"]],
        color=[PALETTE["gray"], PALETTE["green"]],
    )
    ax.set_yscale("log")
    ax.set_ylim(300, float(all_row["available_candidates"]) * 3.0)
    ax.set_ylabel("Count / rank (log scale)")
    ax.set_title("All-candidate certificate")
    for bar in bars:
        value = bar.get_height()
        ax.annotate(
            f"{value:,.0f}",
            xy=(bar.get_x() + bar.get_width() / 2, value),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    fig.suptitle("Freddie FM48 all-candidate LP validates the top-screen result")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    return _save_figure(fig, FIG24)


def _write_source_log() -> Path:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    source_log = SOURCE_DIR / "source_log.md"
    source_log.write_text(
        "\n".join(
            [
                "# Multidataset External Replication Source Log",
                "",
                "This folder contains only curated, local CSV summaries used by the paper and book.",
                "It intentionally does not contain credentials, browser-session references, or paths to the exploratory laboratory.",
                "",
                "## Public Dataset Sources",
                "",
                "- Prosper loan-level data access documentation: https://help.prosper.com/hc/en-us/articles/210013083-Where-can-I-download-data-about-loans-through-Prosper",
                "- Freddie Mac Single Family Loan-Level Dataset: https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset",
                "- Freddie/Mendeley processed mortgage windows: https://data.mendeley.com/datasets/bzr2rxttvz/3",
                "- Home Credit Default Risk page, archived only and not used in the main external claim: https://www.kaggle.com/competitions/home-credit-default-risk/data",
                "",
                "## Editorial Decision",
                "",
                "Prosper final-status loans and Freddie FM48 both are promoted as external economic replications. Home Credit is discarded from the IJDS main claim because it lacks a clean investment-return and exposure contract comparable to Lending Club, Prosper, and Freddie.",
                "",
                "## Extended Audit Layer",
                "",
                "A28 solves the Freddie FM48 LP on the full OOT candidate universe and certifies that the all-candidate optimum funds only loans inside the top-return screen. A29 isolates sparse Mondrian groups. A30--A33 report confidence intervals, OOT subperiods, Prosper default-definition sensitivity, and Freddie red/green segment sensitivity.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    logger.info("Wrote {}", source_log.relative_to(ROOT))
    return source_log


def build_multidataset_external_replication() -> dict[str, Any]:
    start = datetime.now(tz=UTC)
    main = _read_source("table_main_external_replications.csv")
    compact = _read_source("table_portfolio_candidate_sensitivity_compact.csv")
    freddie = _read_source("table_freddie_window_sensitivity.csv")
    full_gate = _read_source("table_full_multidataset_gate_audit.csv")
    lp_exhaustiveness_source = _read_source("table_external_lp_exhaustiveness.csv")
    mondrian_sparse_source = _read_source("table_freddie_mondrian_eligible_summary.csv")
    metric_intervals_source = _read_source("table_external_metric_intervals.csv")
    subperiod_source = _read_source("table_external_subperiod_metrics.csv")
    prosper_default_source = _read_source("table_prosper_default_definition_sensitivity.csv")
    freddie_segment_source = _read_source("table_freddie_segment_sensitivity.csv")

    external_gate = _build_external_gate_table(main)
    candidate = _build_candidate_table(compact)
    freddie_horizon = _build_freddie_horizon_table(freddie)
    lp_exhaustiveness = _build_lp_exhaustiveness_table(lp_exhaustiveness_source)
    freddie_all = lp_exhaustiveness.loc[
        (lp_exhaustiveness["dataset"] == "Freddie FM48")
        & (lp_exhaustiveness["candidate_cap"].astype(str).str.lower() == "all")
        & (lp_exhaustiveness["solver_success"])
    ]
    if not freddie_all.empty:
        all_row = freddie_all.iloc[0]
        freddie_mask = external_gate["dataset"] == "Freddie FM48"
        external_gate.loc[freddie_mask, "lp_candidate_cap"] = "all"
        external_gate.loc[freddie_mask, "robust_objective"] = float(all_row["robust_objective"])
        external_gate.loc[freddie_mask, "price_of_robustness_pct"] = float(
            all_row["price_of_robustness_pct"]
        )
    mondrian_sparse = _build_mondrian_sparse_table(mondrian_sparse_source)
    metric_intervals = _build_metric_intervals_table(metric_intervals_source)
    subperiods = _build_subperiod_table(subperiod_source)
    prosper_default = _build_prosper_default_table(prosper_default_source)
    freddie_segment = _build_freddie_segment_table(freddie_segment_source)

    outputs: list[Path] = []
    outputs.extend(
        write_table(TABLE_A25, external_gate, table_dir=TABLE_DIR, root=ROOT, float_precision=4)
    )
    outputs.extend(
        write_table(TABLE_A26, candidate, table_dir=TABLE_DIR, root=ROOT, float_precision=4)
    )
    outputs.extend(
        write_table(TABLE_A27, freddie_horizon, table_dir=TABLE_DIR, root=ROOT, float_precision=4)
    )
    outputs.extend(
        write_table(TABLE_A28, lp_exhaustiveness, table_dir=TABLE_DIR, root=ROOT, float_precision=4)
    )
    outputs.extend(
        write_table(TABLE_A29, mondrian_sparse, table_dir=TABLE_DIR, root=ROOT, float_precision=4)
    )
    outputs.extend(
        write_table(TABLE_A30, metric_intervals, table_dir=TABLE_DIR, root=ROOT, float_precision=4)
    )
    outputs.extend(
        write_table(TABLE_A31, subperiods, table_dir=TABLE_DIR, root=ROOT, float_precision=4)
    )
    outputs.extend(
        write_table(TABLE_A32, prosper_default, table_dir=TABLE_DIR, root=ROOT, float_precision=4)
    )
    outputs.extend(
        write_table(TABLE_A33, freddie_segment, table_dir=TABLE_DIR, root=ROOT, float_precision=4)
    )
    outputs.extend(_plot_external_replication(external_gate))
    outputs.extend(_plot_candidate_sensitivity(candidate))
    outputs.extend(_plot_freddie_all_candidate_certificate(lp_exhaustiveness))
    outputs.append(_write_source_log())

    home_credit = full_gate.loc[full_gate["run_label"] == "home_credit_full"].iloc[0]
    status = {
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "duration_seconds": (datetime.now(tz=UTC) - start).total_seconds(),
        "source_dir": _rel(SOURCE_DIR),
        "home_credit_policy": "discarded_from_main_claim_archived_only",
        "home_credit_archive_metrics": {
            "rows_total": int(home_credit["rows_total"]),
            "auc_roc": float(home_credit["auc_roc"]),
            "coverage_90": float(home_credit["coverage_90"]),
            "alpha01_coverage": float(home_credit["coverage_alpha01"]),
        },
        "external_replications": external_gate.to_dict(orient="records"),
        "freddie_selected_variant": "freddie_fm48_both",
        "freddie_all_candidate_lp": {
            "available_candidates": int(
                lp_exhaustiveness.loc[
                    (lp_exhaustiveness["dataset"] == "Freddie FM48")
                    & (lp_exhaustiveness["candidate_cap"].astype(str).str.lower() == "all"),
                    "available_candidates",
                ].iloc[0]
            ),
            "robust_objective": float(
                lp_exhaustiveness.loc[
                    (lp_exhaustiveness["dataset"] == "Freddie FM48")
                    & (lp_exhaustiveness["candidate_cap"].astype(str).str.lower() == "all"),
                    "robust_objective",
                ].iloc[0]
            ),
            "max_funded_rank": int(
                lp_exhaustiveness.loc[
                    (lp_exhaustiveness["dataset"] == "Freddie FM48")
                    & (lp_exhaustiveness["candidate_cap"].astype(str).str.lower() == "all"),
                    "robust_max_funded_rank",
                ].iloc[0]
            ),
        },
        "freddie_top_screen_stable_through_candidates": "all",
        "prosper_default_definition_sensitivity": prosper_default.to_dict(orient="records"),
        "freddie_segment_sensitivity": freddie_segment.to_dict(orient="records"),
        "outputs": [_rel(path) for path in outputs],
    }
    write_json(STATUS_PATH, status)
    logger.info("Wrote {}", STATUS_PATH.relative_to(ROOT))
    return status


if __name__ == "__main__":
    build_multidataset_external_replication()
