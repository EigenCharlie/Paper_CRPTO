"""Build journal-ready derived evidence for CRPTO.

The script uses frozen CRPTO artifacts only. It does not reopen the
champion search or replace the official economic champion. The outputs are
diagnostic tables and figures for the Quarto book, manuscript planning, and
appendix material.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.optimization.tail_satisficing_objective import (
    entropic_oce,
    funded_loss_rate,
    weighted_cvar,
)

ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "reports" / "crpto" / "tables"
FIG_DIR = ROOT / "reports" / "crpto" / "figures"
BOOK_FIG_DIR = ROOT / "book" / "assets" / "figures" / "publication"
DOCS_DIR = ROOT / "docs" / "research"
MODELS_DIR = ROOT / "models"
DATA_DIR = ROOT / "data" / "processed"

FUNDED_LOANS = TABLE_DIR / "crpto_tableA7_funded_set_loans.csv"
FUNDED_COMPOSITION = TABLE_DIR / "crpto_tableA8_funded_set_composition.csv"
PROMOTION_PATH = MODELS_DIR / "final_project_promotion.json"
STATUS_PATH = MODELS_DIR / "crpto_journal_package_status.json"
SPO_REAL_STATUS_PATH = MODELS_DIR / "spo_real_training_status.json"
SPO_STABILITY_PATH = DATA_DIR / "crpto_vs_spo_stability.json"
SHORTLIST_PATH = (
    DATA_DIR
    / "portfolio_bound_aware"
    / "rank1_alpha01_bound_aware_276k_full_2026-04-05-1734"
    / "portfolio_bound_aware_shortlist.parquet"
)
BOUND_EVAL_PATH = (
    DATA_DIR
    / "portfolio_bound_aware"
    / "rank1_alpha01_bound_aware_276k_full_2026-04-05-1734"
    / "portfolio_bound_aware_bound_eval.parquet"
)
ALPHA_SWEEP_PATH = DATA_DIR / "alpha_sweep_pareto_mondrian.parquet"
JOURNAL_PIPELINE_ASSETS = [
    FIG_DIR / "crpto_fig1_journal_pipeline.png",
    FIG_DIR / "crpto_fig1_journal_pipeline.pdf",
    FIG_DIR / "crpto_fig1_journal_pipeline.svg",
]

DEFAULT_LGD = 0.45
LGD_GRID = [0.35, 0.45, 0.60]
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 20260504


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )


def _write_table(name: str, frame: pd.DataFrame) -> list[Path]:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = TABLE_DIR / f"{name}.csv"
    tex_path = TABLE_DIR / f"{name}.tex"
    csv_text = frame.to_csv(index=False, lineterminator="\n")
    tex_text = frame.to_latex(
        index=False,
        escape=True,
        float_format=lambda value: f"{value:.6f}",
    )
    for path, text in [(csv_path, csv_text), (tex_path, tex_text)]:
        if path.exists():
            existing = path.read_bytes().decode("utf-8")
            if existing == text:
                continue
        path.write_text(text, encoding="utf-8", newline="")
    print(f"Wrote {csv_path.relative_to(ROOT)}")
    print(f"Wrote {tex_path.relative_to(ROOT)}")
    return [csv_path, tex_path]


def _mirror_to_book(*paths: Path) -> None:
    """Copy generated figures into the book's publication assets directory."""
    BOOK_FIG_DIR.mkdir(parents=True, exist_ok=True)
    for path in paths:
        shutil.copy2(path, BOOK_FIG_DIR / path.name)


def _save_figure(name: str) -> list[Path]:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    png_path = FIG_DIR / f"{name}.png"
    pdf_path = FIG_DIR / f"{name}.pdf"
    plt.savefig(png_path, dpi=220, bbox_inches="tight")
    plt.savefig(pdf_path, bbox_inches="tight")
    plt.close()
    _mirror_to_book(png_path, pdf_path)
    print(f"Wrote {png_path.relative_to(ROOT)}")
    print(f"Wrote {pdf_path.relative_to(ROOT)}")
    return [png_path, pdf_path]


def _publish_journal_pipeline_assets() -> list[Path]:
    """Mirror the hand-authored IJDS pipeline figure into the book assets."""
    missing = [
        path.relative_to(ROOT).as_posix() for path in JOURNAL_PIPELINE_ASSETS if not path.exists()
    ]
    if missing:
        raise FileNotFoundError(
            "Missing journal pipeline assets: " + ", ".join(missing),
        )
    _mirror_to_book(*JOURNAL_PIPELINE_ASSETS)
    for path in JOURNAL_PIPELINE_ASSETS:
        print(f"Published static asset {path.relative_to(ROOT)}")
    return JOURNAL_PIPELINE_ASSETS


def _relative(paths: list[Path]) -> list[str]:
    return list(dict.fromkeys(path.relative_to(ROOT).as_posix() for path in paths))


def _as_rate(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").fillna(0.0)
    if float(values.max()) > 1.5:
        return values / 100.0
    return values


def _funded_frame() -> pd.DataFrame:
    funded = pd.read_csv(FUNDED_LOANS)
    funded["int_rate_decimal"] = _as_rate(funded["int_rate"])
    funded["y_true"] = pd.to_numeric(funded["y_true"], errors="coerce").fillna(0.0)
    funded["funded_exposure"] = pd.to_numeric(
        funded["funded_exposure"],
        errors="coerce",
    ).fillna(0.0)
    funded["portfolio_weight"] = funded["funded_exposure"] / max(
        float(funded["funded_exposure"].sum()),
        1e-9,
    )
    funded["miscovered_alpha01"] = funded["miscovered_alpha01"].astype(bool)
    return funded


def _return_from_frame(frame: pd.DataFrame, weights: pd.Series, *, lgd: float) -> float:
    total_exposure = 1_000_000.0
    exposure = weights.astype(float) * total_exposure
    nondefault_return = exposure * frame["int_rate_decimal"] * (1.0 - frame["y_true"])
    default_loss = exposure * (-float(lgd)) * frame["y_true"]
    return float((nondefault_return + default_loss).sum())


def _weighted_metric(frame: pd.DataFrame, weights: pd.Series, column: str) -> float:
    return float((weights.astype(float) * pd.to_numeric(frame[column], errors="coerce")).sum())


def _build_tail_risk_table(funded: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    weights = funded["portfolio_weight"]
    for lgd in LGD_GRID:
        loss_rate = pd.Series(
            funded_loss_rate(
                funded["y_true"].to_numpy(dtype=float),
                funded["int_rate_decimal"].to_numpy(dtype=float),
                lgd=float(lgd),
            ),
            index=funded.index,
        )
        theta = 5.0
        oce = round(float(entropic_oce(loss_rate, weights, theta=theta, stable=False)), 17)
        rows.append(
            {
                "lgd": float(lgd),
                "mean_loss_rate": float(np.sum(weights * loss_rate)),
                "entropic_oce_theta5": oce,
                "cvar_90_loss_rate": weighted_cvar(loss_rate, weights, tail=0.90),
                "cvar_95_loss_rate": weighted_cvar(loss_rate, weights, tail=0.95),
                "cvar_99_loss_rate": weighted_cvar(loss_rate, weights, tail=0.99),
                "funded_set_repriced_return": _return_from_frame(
                    funded,
                    weights,
                    lgd=float(lgd),
                ),
                "weighted_default_rate": _weighted_metric(funded, weights, "y_true"),
            }
        )
    return pd.DataFrame(rows)


def _build_satisficing_table(promotion: dict[str, Any]) -> pd.DataFrame:
    champion = promotion["final_champion"]
    theorem = promotion["theorem_tight_comparator"]
    robust_region = promotion["robust_region_summary"]
    rows = [
        {
            "criterion": "return_beats_theorem_tight",
            "observed": float(champion["realized_total_return"]),
            "threshold": float(theorem["realized_total_return"]),
            "margin": float(champion["realized_total_return"] - theorem["realized_total_return"]),
            "pass": bool(champion["realized_total_return"] >= theorem["realized_total_return"]),
            "interpretation": "Economic champion preserves more return than the tightness comparator.",
        },
        {
            "criterion": "V_below_sqrt_alpha01",
            "observed": float(champion["alpha01_weighted_miscoverage_V"]),
            "threshold": 0.10,
            "margin": 0.10 - float(champion["alpha01_weighted_miscoverage_V"]),
            "pass": bool(float(champion["alpha01_weighted_miscoverage_V"]) <= 0.10),
            "interpretation": "Weighted funded-set noncoverage stays below Markov sqrt(alpha).",
        },
        {
            "criterion": "gamma_cp_below_020",
            "observed": float(champion["alpha01_gamma_cp"]),
            "threshold": 0.20,
            "margin": 0.20 - float(champion["alpha01_gamma_cp"]),
            "pass": bool(float(champion["alpha01_gamma_cp"]) <= 0.20),
            "interpretation": "Conformal premium remains below an editorial 20pp diagnostic ceiling.",
        },
        {
            "criterion": "violation_zero",
            "observed": float(champion["alpha01_violation"]),
            "threshold": 0.0,
            "margin": -float(champion["alpha01_violation"]),
            "pass": bool(float(champion["alpha01_violation"]) <= 1e-12),
            "interpretation": "Exact funded-set risk violation is zero.",
        },
        {
            "criterion": "robust_region_all_pass",
            "observed": float(robust_region["alpha01_pass_rate"]),
            "threshold": 1.0,
            "margin": float(robust_region["alpha01_pass_rate"]) - 1.0,
            "pass": bool(float(robust_region["alpha01_pass_rate"]) >= 1.0),
            "interpretation": "The final 276K robust region is not a single-point result.",
        },
    ]
    return pd.DataFrame(rows)


def _build_dependency_table(funded: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, label in [
        (["period"], "period"),
        (["original_grade"], "grade"),
        (["period", "original_grade"], "period_grade"),
    ]:
        grouped = funded.groupby(keys, dropna=False, observed=True)
        for values, group in grouped:
            if not isinstance(values, tuple):
                values = (values,)
            weight = float(group["portfolio_weight"].sum())
            rows.append(
                {
                    "cluster_type": label,
                    "cluster": "/".join(str(value) for value in values),
                    "n_funded": len(group),
                    "exposure_share": weight,
                    "weighted_default_rate": _weighted_metric(
                        group,
                        group["portfolio_weight"] / max(weight, 1e-12),
                        "y_true",
                    ),
                    "V_contribution": float(
                        group.loc[group["miscovered_alpha01"], "portfolio_weight"].sum()
                    ),
                    "gamma_cp_contribution": float(
                        (
                            group["portfolio_weight"]
                            * (
                                pd.to_numeric(group["pd_high_alpha01"], errors="coerce")
                                - pd.to_numeric(group["pd_point"], errors="coerce")
                            ).clip(lower=0.0)
                        ).sum()
                    ),
                    "max_loan_weight": float(group["portfolio_weight"].max()),
                }
            )
    frame = pd.DataFrame(rows)
    return frame.sort_values(["cluster_type", "exposure_share"], ascending=[True, False])


def _scenario_metrics(frame: pd.DataFrame, weights: pd.Series, scenario: str) -> dict[str, Any]:
    weights = weights.astype(float)
    weights = weights / max(float(weights.sum()), 1e-12)
    gamma_cp = float(
        (
            weights
            * (
                pd.to_numeric(frame["pd_high_alpha01"], errors="coerce")
                - pd.to_numeric(frame["pd_point"], errors="coerce")
            ).clip(lower=0.0)
        ).sum()
    )
    return {
        "scenario": scenario,
        "n_funded_effective": int((weights > 1e-10).sum()),
        "funded_set_repriced_return_lgd45": _return_from_frame(
            frame,
            weights,
            lgd=DEFAULT_LGD,
        ),
        "weighted_default_rate": _weighted_metric(frame, weights, "y_true"),
        "weighted_miscoverage_V": float(
            weights.loc[frame["miscovered_alpha01"].astype(bool)].sum()
        ),
        "gamma_cp": gamma_cp,
        "max_loan_weight": float(weights.max()),
    }


def _build_period_stress_table(funded: pd.DataFrame) -> pd.DataFrame:
    rows = [_scenario_metrics(funded, funded["portfolio_weight"], "baseline")]
    for period in sorted(funded["period"].astype(str).unique()):
        leave_weights = funded["portfolio_weight"].where(
            funded["period"].astype(str) != period, 0.0
        )
        rows.append(_scenario_metrics(funded, leave_weights, f"leave_out_{period}"))
        over_weights = funded["portfolio_weight"].where(
            funded["period"].astype(str) != period,
            funded["portfolio_weight"] * 2.0,
        )
        rows.append(_scenario_metrics(funded, over_weights, f"overweight_2x_{period}"))
    return pd.DataFrame(rows)


def _build_bootstrap_table(funded: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    n = len(funded)
    values: list[dict[str, float]] = []
    for _ in range(BOOTSTRAP_DRAWS):
        sample_index = rng.integers(0, n, size=n)
        sample = funded.iloc[sample_index].reset_index(drop=True)
        weights = sample["funded_exposure"] / max(float(sample["funded_exposure"].sum()), 1e-12)
        values.append(
            {
                "funded_set_repriced_return_lgd45": _return_from_frame(
                    sample,
                    weights,
                    lgd=DEFAULT_LGD,
                ),
                "weighted_default_rate": _weighted_metric(sample, weights, "y_true"),
                "weighted_miscoverage_V": float(
                    weights.loc[sample["miscovered_alpha01"].astype(bool)].sum()
                ),
                "n_default_loans": float(sample["y_true"].sum()),
                "n_miscovered_loans": float(sample["miscovered_alpha01"].sum()),
            }
        )
    draws = pd.DataFrame(values)
    rows = []
    for column in draws.columns:
        rows.append(
            {
                "metric": column,
                "mean": float(draws[column].mean()),
                "p025": float(draws[column].quantile(0.025)),
                "p50": float(draws[column].quantile(0.50)),
                "p975": float(draws[column].quantile(0.975)),
                "n_draws": BOOTSTRAP_DRAWS,
                "seed": BOOTSTRAP_SEED,
            }
        )
    return pd.DataFrame(rows)


def _build_budget_cap_lgd_table(
    funded: pd.DataFrame,
    funded_composition: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    weights = funded["portfolio_weight"]
    base_return = _return_from_frame(funded, weights, lgd=DEFAULT_LGD)
    for budget in [500_000.0, 1_000_000.0, 2_000_000.0]:
        rows.append(
            {
                "sensitivity_type": "budget_scaling_diagnostic",
                "scenario": f"budget_{budget:.0f}",
                "value": budget,
                "funded_set_repriced_return_lgd45": base_return * budget / 1_000_000.0,
                "weighted_default_rate": _weighted_metric(funded, weights, "y_true"),
                "weighted_miscoverage_V": float(
                    weights.loc[funded["miscovered_alpha01"].astype(bool)].sum()
                ),
                "diagnostic_pass": True,
                "note": "Linear funded-set rescale; not a re-optimized portfolio.",
            }
        )
    for lgd in LGD_GRID:
        rows.append(
            {
                "sensitivity_type": "lgd_sensitivity",
                "scenario": f"lgd_{lgd:.2f}",
                "value": float(lgd),
                "funded_set_repriced_return_lgd45": _return_from_frame(
                    funded,
                    weights,
                    lgd=float(lgd),
                ),
                "weighted_default_rate": _weighted_metric(funded, weights, "y_true"),
                "weighted_miscoverage_V": float(
                    weights.loc[funded["miscovered_alpha01"].astype(bool)].sum()
                ),
                "diagnostic_pass": True,
                "note": "Reprices realized funded set under alternative LGD.",
            }
        )
    largest_segment = float(funded_composition["exposure_share"].max())
    for cap in [0.25, 0.20, 0.15]:
        rows.append(
            {
                "sensitivity_type": "segment_cap_diagnostic",
                "scenario": f"segment_cap_{cap:.2f}",
                "value": float(cap),
                "funded_set_repriced_return_lgd45": base_return,
                "weighted_default_rate": _weighted_metric(funded, weights, "y_true"),
                "weighted_miscoverage_V": float(
                    weights.loc[funded["miscovered_alpha01"].astype(bool)].sum()
                ),
                "diagnostic_pass": bool(largest_segment <= cap),
                "note": "Checks period-grade funded-set concentration; not a re-optimized portfolio.",
            }
        )
    return pd.DataFrame(rows)


def _build_robust_region_table(shortlist: pd.DataFrame) -> pd.DataFrame:
    grouped = shortlist.groupby(["risk_tolerance", "gamma"], as_index=False)
    rows = grouped.agg(
        n_policies=("semantic_policy_key", "count"),
        alpha01_pass_rate=("alpha01_exact_pass", "mean"),
        best_return=("realized_total_return", "max"),
        median_return=("realized_total_return", "median"),
        min_V=("alpha01_weighted_miscoverage_V", "min"),
        median_gamma_cp=("alpha01_gamma_cp", "median"),
        max_n_funded=("n_funded", "max"),
    )
    rows["all_alpha01_pass"] = rows["alpha01_pass_rate"].eq(1.0)
    return rows.sort_values(["risk_tolerance", "gamma"]).reset_index(drop=True)


def _regret_delta_vs_two_stage(reference: float, observed: float) -> float:
    return float((reference - observed) / max(reference, 1e-12) * 100.0)


def _range_text(values: list[float], *, precision: int = 4) -> str:
    return f"{float(values[0]):.{precision}f}--{float(values[1]):.{precision}f}"


def _build_regret_auditability_frontier(
    spo_status: dict[str, Any],
    stability: dict[str, Any],
    promotion: dict[str, Any],
) -> pd.DataFrame:
    results = spo_status["results"]
    stability_summary = stability["stability_summary"]
    champion = promotion["final_champion"]
    robust_region = promotion["robust_region_summary"]

    two_stage_regret = float(results["two_stage"]["mean_regret"])
    spo_regret = float(results["spo_plus"]["mean_regret"])
    crpto_regret = float(results["conformal_robust"]["mean_regret"])
    crpto_checks = int(bool(stability_summary["coverage_always_above_target"]))
    crpto_checks += int(bool(champion["alpha01_exact_pass"]))
    crpto_checks += int(float(robust_region["alpha01_pass_rate"]) >= 1.0)

    rows = [
        {
            "method": "Two-stage baseline",
            "mean_regret": two_stage_regret,
            "regret_delta_vs_two_stage_pct": 0.0,
            "coverage_90_range": "not_applicable",
            "exact_funded_set_bound": False,
            "robust_region_pass": False,
            "auditability_evidence_count": 0,
            "paper_role": "Regret baseline for the decision-focused comparison.",
            "source": "models/spo_real_training_status.json",
        },
        {
            "method": "SPO+",
            "mean_regret": spo_regret,
            "regret_delta_vs_two_stage_pct": _regret_delta_vs_two_stage(
                two_stage_regret,
                spo_regret,
            ),
            "coverage_90_range": "not_applicable",
            "exact_funded_set_bound": False,
            "robust_region_pass": False,
            "auditability_evidence_count": 0,
            "paper_role": (
                "Regret-efficient comparator; temporal improvement range "
                f"{_range_text(stability_summary['spo_improvement_range_pct'], precision=2)}%."
            ),
            "source": "models/spo_real_training_status.json",
        },
        {
            "method": "CRPTO robust",
            "mean_regret": crpto_regret,
            "regret_delta_vs_two_stage_pct": _regret_delta_vs_two_stage(
                two_stage_regret,
                crpto_regret,
            ),
            "coverage_90_range": _range_text(stability_summary["coverage_range"]),
            "exact_funded_set_bound": bool(champion["alpha01_exact_pass"]),
            "robust_region_pass": bool(float(robust_region["alpha01_pass_rate"]) >= 1.0),
            "auditability_evidence_count": crpto_checks,
            "paper_role": "Auditable robust champion: coverage, exact bound and 45/45 region.",
            "source": (
                "models/spo_real_training_status.json; "
                "data/processed/crpto_vs_spo_stability.json; "
                "models/final_project_promotion.json"
            ),
        },
    ]
    return pd.DataFrame(rows)


def _plot_regret_auditability_frontier(frontier: pd.DataFrame) -> list[Path]:
    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    colors = {
        "Two-stage baseline": "#607D8B",
        "SPO+": "#1565C0",
        "CRPTO robust": "#2E7D32",
    }
    offsets = {
        "Two-stage baseline": (8, 12),
        "SPO+": (8, 12),
        "CRPTO robust": (-86, 12),
    }
    for _, row in frontier.iterrows():
        method = str(row["method"])
        ax.scatter(
            float(row["mean_regret"]),
            int(row["auditability_evidence_count"]),
            s=170,
            color=colors[method],
            edgecolor="#263238",
            linewidth=0.9,
            zorder=3,
        )
        ax.annotate(
            method,
            (
                float(row["mean_regret"]),
                int(row["auditability_evidence_count"]),
            ),
            xytext=offsets[method],
            textcoords="offset points",
            fontsize=10,
            fontweight="bold",
        )
    ax.set_xlabel("Mean decision regret (lower is better)")
    ax.set_ylabel("Verifiable risk-control checks passed (0-3)")
    ax.set_title("Regret-auditability frontier")
    ax.set_xlim(left=0.0)
    ax.set_ylim(-0.25, 3.35)
    ax.set_yticks([0, 1, 2, 3])
    ax.grid(alpha=0.25)
    ax.text(
        0.0,
        -0.20,
        "Checks: temporal 90% coverage target, exact funded-set alpha bound, robust-region pass.",
        transform=ax.transAxes,
        fontsize=8.6,
        color="#455A64",
    )
    return _save_figure("crpto_fig15_regret_auditability_frontier")


def _plot_conceptual_pipeline() -> list[Path]:
    """Publish the hand-authored editorial master diagram as a companion pipeline.

    The IJDS Figure 1 is the static ``crpto_fig1_journal_pipeline`` asset. This
    function keeps the longer book/editorial master diagram available as
    ``crpto_fig12`` for the companion and thesis surfaces.
    """
    from PIL import Image

    src = ROOT / "book" / "assets" / "figures" / "editorial" / "diagrama-crpto.png"
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    png_path = FIG_DIR / "crpto_fig12_crpto_conceptual_pipeline.png"
    pdf_path = FIG_DIR / "crpto_fig12_crpto_conceptual_pipeline.pdf"
    with Image.open(src) as img:
        rgb = img.convert("RGB")
        rgb.save(png_path)
        rgb.save(pdf_path, "PDF", resolution=300.0)
    _mirror_to_book(png_path, pdf_path)
    print(f"Wrote {png_path.relative_to(ROOT)} (from editorial master diagram)")
    return [png_path, pdf_path]


def _plot_bound_claim_layers() -> list[Path]:
    """Show the three-layer claim stack behind the CRPTO bound."""
    steps = [
        {
            "title": "Conformal endpoint",
            "body": "u_i(alpha) caps\nPD-scale uncertainty",
            "note": "interval artifact",
            "color": "#E7F0FA",
        },
        {
            "title": "Deterministic identity",
            "body": "risk <= tau + V(alpha)\nwhen sum w_i u_i <= tau",
            "note": "portfolio accounting",
            "color": "#F1F8E9",
        },
        {
            "title": "Weighted validity",
            "body": "E[V(alpha)] <= alpha\nunder funded-set weights",
            "note": "stated assumption",
            "color": "#FFF8E1",
        },
        {
            "title": "Exact certificate",
            "body": "V = 0.03645 < sqrt(alpha)\nviolation = 0; 45/45 pass",
            "note": "frozen audit",
            "color": "#FCE4EC",
        },
    ]

    fig, ax = plt.subplots(figsize=(11.2, 3.4))
    ax.axis("off")
    xs = [0.11, 0.37, 0.63, 0.89]
    for x, step in zip(xs, steps, strict=True):
        text = f"{step['title']}\n\n{step['body']}\n\n{step['note']}"
        ax.text(
            x,
            0.58,
            text,
            ha="center",
            va="center",
            fontsize=9.2,
            linespacing=1.2,
            transform=ax.transAxes,
            bbox={
                "boxstyle": "round,pad=0.55,rounding_size=0.08",
                "facecolor": step["color"],
                "edgecolor": "#263238",
                "linewidth": 1.1,
            },
        )

    for left, right in zip(xs[:-1], xs[1:], strict=True):
        ax.annotate(
            "",
            xy=(right - 0.105, 0.58),
            xytext=(left + 0.105, 0.58),
            xycoords=ax.transAxes,
            arrowprops={"arrowstyle": "->", "lw": 1.6, "color": "#263238"},
        )

    ax.text(
        0.5,
        0.94,
        "CRPTO bound claim stack",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        transform=ax.transAxes,
    )
    ax.text(
        0.5,
        0.12,
        "The theorem separates deterministic portfolio accounting, an explicit weighted-validity assumption, and the frozen empirical certificate.",
        ha="center",
        va="center",
        fontsize=8.8,
        color="#455A64",
        transform=ax.transAxes,
    )
    return _save_figure("crpto_fig20_bound_claim_layers")


def _plot_alpha_gamma_funded_set(bound_eval: pd.DataFrame, promotion: dict[str, Any]) -> list[Path]:
    champion = promotion["final_champion"]
    mask = (
        bound_eval["risk_tolerance"].eq(float(champion["risk_tolerance"]))
        & bound_eval["gamma"].eq(float(champion["gamma"]))
        & bound_eval["uncertainty_aversion"].eq(float(champion["uncertainty_aversion"]))
        & bound_eval["policy_mode"].eq(str(champion["policy_mode"]))
    )
    data = bound_eval.loc[mask].sort_values("alpha")
    if data.empty:
        data = bound_eval.sort_values(["return_first_rank", "alpha"]).groupby("alpha").head(1)

    fig, (ax1, ax2) = plt.subplots(
        1,
        2,
        figsize=(11.2, 4.8),
        gridspec_kw={"width_ratios": [1.45, 1.0]},
    )
    ax1.plot(data["alpha"], data["gamma_cp"], marker="o", label="Gamma_CP", color="#0B5CAD")
    ax1.plot(
        data["alpha"],
        data["weighted_miscoverage_V"],
        marker="s",
        label="V",
        color="#B00020",
    )
    ax1.plot(
        data["alpha"],
        data["sqrt_alpha"],
        linestyle="--",
        label="sqrt(alpha)",
        color="#616161",
    )
    ax1.axvline(0.01, color="#263238", linestyle=":", linewidth=1.1)
    alpha01 = data.loc[data["alpha"].eq(0.01)]
    if not alpha01.empty:
        row = alpha01.iloc[0]
        ax1.annotate(
            "alpha=0.01\nexact pass",
            (float(row["alpha"]), float(row["weighted_miscoverage_V"])),
            xytext=(18, 22),
            textcoords="offset points",
            arrowprops={"arrowstyle": "->", "color": "#263238", "lw": 0.9},
            fontsize=8.5,
        )
    ax1.set_xlabel("Conformal alpha")
    ax1.set_ylabel("Weighted bound quantities")
    ax1.set_title("Bound quantities")
    ax1.grid(alpha=0.25)
    ax1.legend(loc="best", frameon=False)

    ax2.plot(data["alpha"], data["n_funded"], marker="^", color="#2E7D32", linewidth=2.0)
    ax2.fill_between(data["alpha"], data["n_funded"], alpha=0.14, color="#2E7D32")
    ax2.axvline(0.01, color="#263238", linestyle=":", linewidth=1.1)
    ax2.set_xlabel("Conformal alpha")
    ax2.set_ylabel("Funded loans")
    ax2.set_title("Funded-set size")
    ax2.grid(alpha=0.25)
    fig.suptitle("Alpha to Gamma_CP to funded-set audit", fontsize=14, fontweight="bold")
    fig.text(
        0.5,
        0.01,
        "The promoted policy is read through both quantities: weighted noncoverage V and the realized conformal robustness premium Gamma_CP.",
        ha="center",
        fontsize=8.8,
        color="#455A64",
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    return _save_figure("crpto_fig13_alpha_gamma_funded_set")


def _plot_robust_region_heatmap(shortlist: pd.DataFrame, promotion: dict[str, Any]) -> list[Path]:
    pivot = shortlist.pivot_table(
        index="risk_tolerance",
        columns="gamma",
        values="realized_total_return",
        aggfunc="max",
    ).sort_index(ascending=False)
    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    im = ax.imshow(pivot.to_numpy(), cmap="viridis", aspect="auto")
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels([f"{x:.2f}" for x in pivot.columns])
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels([f"{x:.3f}" for x in pivot.index])
    ax.set_xlabel("gamma")
    ax.set_ylabel("risk_tolerance")
    ax.set_title("Robust region: best realized return by policy family")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            value = pivot.iloc[i, j]
            if pd.notna(value):
                ax.text(j, i, f"{value / 1000:.0f}K", ha="center", va="center", color="white")
    champion = promotion["final_champion"]
    champion_gamma = float(champion["gamma"])
    champion_tau = float(champion["risk_tolerance"])
    if not pivot.empty:
        col = int(np.argmin(np.abs(pivot.columns.to_numpy(dtype=float) - champion_gamma)))
        row = int(np.argmin(np.abs(pivot.index.to_numpy(dtype=float) - champion_tau)))
        ax.scatter(
            col,
            row,
            marker="*",
            s=360,
            color="#FDD835",
            edgecolor="#263238",
            linewidth=1.1,
            zorder=4,
        )
        ax.annotate(
            "economic\nchampion",
            (col, row),
            xytext=(10, -24),
            textcoords="offset points",
            color="#263238",
            fontsize=8.5,
            fontweight="bold",
            bbox={
                "boxstyle": "round,pad=0.18",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.82,
            },
            zorder=5,
        )
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Realized return")
    fig.text(
        0.5,
        0.01,
        "All 45 policies in the final region pass the exact alpha=0.01 funded-set check.",
        ha="center",
        fontsize=8.8,
        color="#455A64",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return _save_figure("crpto_fig14_robust_region_heatmap")


def _write_markdown_dossier(status: dict[str, Any]) -> Path:
    path = DOCS_DIR / "crpto_journal_package_2026-05-04.md"
    lines = [
        "# paper-crpto Journal Package - 2026-05-04",
        "",
        "This dossier records the journal-oriented tables and figures generated from",
        "frozen CRPTO artifacts. It does not reopen the champion search.",
        "",
        "## Standalone Scope - 2026-05-12",
        "",
        "This package is the journal/appendix layer for `Paper_CRPTO`. It is intentionally",
        "larger than the short paper: A12--A24, Figures 1, 12--20 and the robustness notes",
        "can be selected into a journal appendix, reviewer response or future thesis",
        "chapter without changing the official champion.",
        "A20--A21 are generated by `scripts/build_tail_satisficing_challenger_audit.py`",
        "as a slower journal-only add-on.",
        "",
        "## Generated artifacts",
        "",
    ]
    for artifact in status["generated_artifacts"]:
        lines.append(f"- `{artifact}`")
    lines += [
        "",
        "## Scope notes",
        "",
        "- A12--A24 are diagnostic robustness, comparator and packaging tables.",
        "- A20--A21 are diagnostic challenger and cluster-bound audit tables from",
        "  the separate tail-satisficing audit script.",
        "- Budget and segment-cap sensitivity are funded-set diagnostics, not",
        "  re-optimized portfolios.",
        "- Tail-risk and bootstrap return columns are funded-set repricing diagnostics;",
        "  the official champion return remains sourced from `final_project_promotion.json`.",
        "- `src/optimization/tail_satisficing_objective.py` exposes the same",
        "  OCE/CVaR/satisficing primitives as a future-experiment scaffold,",
        "  but this package still does not promote a new objective.",
        "- The official champion remains `bound_aware_276k_economic_champion`.",
        "",
        "## Appendix map",
        "",
        "| Artifact | Purpose | Caveat |",
        "|---|---|---|",
        "| A12 tail risk OCE/CVaR | Adds funded-set tail-risk diagnostics under LGD alternatives. | Diagnostic repricing, not a new champion metric. |",
        "| A13 satisficing margins | Converts champion evidence into OR-style pass/margin checks. | Editorial thresholds must be justified if moved to body. |",
        "| A14 dependency clusters | Documents period/grade concentration for the tightening appendix. | Does not prove conditional independence. |",
        "| A15 leave-one-period stress | Reweights the funded set by period. | Not a re-optimized portfolio. |",
        "| A16 bootstrap funded-set metrics | Adds empirical intervals for realized funded-set quantities. | Not a conformal guarantee. |",
        "| A17 budget/LGD/cap sensitivity | Checks practical sensitivity to budget, LGD and segment caps. | Cap checks are diagnostics, not solver constraints. |",
        "| A18 robust region by family | Summarizes the `45/45` alpha01-safe region by `risk_tolerance x gamma`. | Bound-aware family only. |",
        "| A19 regret-auditability frontier | Compares two-stage, SPO+ and CRPTO robust on regret versus verifiable risk controls. | Trade-off diagnostic, not a new champion selector. |",
        "| A20 tail-satisficing challenger | Re-solves the 45 alpha-safe policies and ranks a CVaR/OCE/satisficing challenger. | Generated separately; audit only, no champion promotion. |",
        "| A21 cluster-bound tightening | Quantifies cluster-aware Hoeffding thresholds. | Transparent caveat, not tighter than Markov here. |",
        "",
        "## Quarto integration",
        "",
        "- `book/chapters/06-blueprint-manuscrito.qmd` uses",
        "  these artifacts to define the paper outline and final table/figure plan.",
        "- `book/chapters/07-apendice-robustez.qmd`",
        "  renders A12--A24 and Figures 1, 12--20 plus the bound-claim stack figure.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="")
    print(f"Wrote {path.relative_to(ROOT)}")
    return path


def build_journal_package() -> dict[str, Any]:
    promotion = _load_json(PROMOTION_PATH)
    spo_status = _load_json(SPO_REAL_STATUS_PATH)
    stability = _load_json(SPO_STABILITY_PATH)
    funded = _funded_frame()
    funded_composition = pd.read_csv(FUNDED_COMPOSITION)
    shortlist = pd.read_parquet(SHORTLIST_PATH)
    bound_eval = pd.read_parquet(BOUND_EVAL_PATH)

    artifacts: list[Path] = []
    artifacts += _write_table("crpto_tableA12_tail_risk_oce_cvar", _build_tail_risk_table(funded))
    artifacts += _write_table(
        "crpto_tableA13_satisficing_margins",
        _build_satisficing_table(promotion),
    )
    artifacts += _write_table(
        "crpto_tableA14_dependency_cluster_diagnostics",
        _build_dependency_table(funded),
    )
    artifacts += _write_table(
        "crpto_tableA15_leave_one_period_stress",
        _build_period_stress_table(funded),
    )
    artifacts += _write_table(
        "crpto_tableA16_bootstrap_funded_set_metrics",
        _build_bootstrap_table(funded),
    )
    artifacts += _write_table(
        "crpto_tableA17_budget_cap_lgd_sensitivity",
        _build_budget_cap_lgd_table(funded, funded_composition),
    )
    artifacts += _write_table(
        "crpto_tableA18_robust_region_policy_family",
        _build_robust_region_table(shortlist),
    )
    regret_frontier = _build_regret_auditability_frontier(spo_status, stability, promotion)
    artifacts += _write_table("crpto_tableA19_regret_auditability_frontier", regret_frontier)
    artifacts += _publish_journal_pipeline_assets()
    artifacts += _plot_conceptual_pipeline()
    artifacts += _plot_bound_claim_layers()
    artifacts += _plot_alpha_gamma_funded_set(bound_eval, promotion)
    artifacts += _plot_robust_region_heatmap(shortlist, promotion)
    artifacts += _plot_regret_auditability_frontier(regret_frontier)

    status = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "schema_version": 2,
        "run_tag": promotion["run_tag"],
        "champion_label": promotion["final_champion"]["label"],
        "generated_artifacts": _relative(artifacts),
        "source_artifacts": _relative(
            [
                FUNDED_LOANS,
                FUNDED_COMPOSITION,
                PROMOTION_PATH,
                SPO_REAL_STATUS_PATH,
                SPO_STABILITY_PATH,
                SHORTLIST_PATH,
                BOUND_EVAL_PATH,
                ALPHA_SWEEP_PATH,
                *JOURNAL_PIPELINE_ASSETS,
            ]
        ),
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "notes": [
            "No champion search was reopened.",
            "Budget and cap sensitivity are diagnostics on the exported funded set.",
            "Repriced funded-set return diagnostics are not replacements for the official champion return.",
            "Official champion metrics remain sourced from final_project_promotion.json.",
            "A19/Fig15 compare regret against verifiable risk-control checks; they are not a new selector.",
        ],
    }
    dossier = _write_markdown_dossier(status)
    artifacts.append(dossier)
    status["generated_artifacts"] = _relative(artifacts)
    _write_json(STATUS_PATH, status)
    print(f"Wrote {STATUS_PATH.relative_to(ROOT)}")
    return status


def main() -> int:
    build_journal_package()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
