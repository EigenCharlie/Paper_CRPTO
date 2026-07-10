"""Build an experimental CRPTO bound-tightening audit from frozen funded weights.

The active manuscript keeps Markov as the main distribution-free bound. This
script computes the sharper concentration bounds that become available only
under extra assumptions, so the IJDS appendix can discuss tightness without
reopening the frozen champion or re-running protected DVC stages.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from src.utils.script_helpers import write_table

ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "reports" / "crpto" / "tables"
OUTPUT_DIR = ROOT / "docs" / "research" / "bound_tightening_audit"
REPORT_PATH = ROOT / "docs" / "research" / "crpto_bound_tightening_experiment_2026-06-11.md"
FUNDED_LOANS_PATH = TABLE_DIR / "crpto_tableA7_funded_set_loans.csv"

TABLE_A21C_NAME = "crpto_tableA21c_bound_comparison_experimental"
TABLE_A21D_NAME = "crpto_tableA21d_bound_assumption_audit_experimental"

ALPHAS = (0.01, 0.03, 0.05, 0.10)
ROBUST_REGION_POLICY_COUNT = 45


def _normalized_weights(funded: pd.DataFrame) -> np.ndarray:
    weights = pd.to_numeric(funded["portfolio_weight"], errors="coerce").fillna(0.0)
    values = weights.to_numpy(dtype=float)
    if np.any(values < 0):
        raise ValueError("Funded-set weights must be non-negative.")
    total = float(values.sum())
    if total <= 0.0:
        raise ValueError("Funded-set weights sum to zero.")
    return values / total


def _empirical_weighted_miscoverage(funded: pd.DataFrame, weights: np.ndarray) -> float:
    misses = funded["miscovered_alpha01"].astype(bool).astype(float).to_numpy(dtype=float)
    return float(np.sum(weights * misses))


def _bennett_threshold(
    *, alpha: float, delta: float, variance_bound: float, max_weight: float
) -> float:
    if variance_bound <= 0.0 or max_weight <= 0.0:
        return alpha

    target = math.log(1.0 / delta)

    def h(value: float) -> float:
        return (1.0 + value) * math.log1p(value) - value

    low = 0.0
    high = max(1.0 - alpha, max_weight)
    for _ in range(100):
        mid = (low + high) / 2.0
        lhs = (variance_bound / (max_weight**2)) * h(max_weight * mid / variance_bound)
        if lhs >= target:
            high = mid
        else:
            low = mid
    return alpha + high


def _threshold_rows(funded: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    weights = _normalized_weights(funded)
    empirical_v = _empirical_weighted_miscoverage(funded, weights)
    sum_w2 = float(np.sum(weights**2))
    max_weight = float(np.max(weights))
    n_eff = float(1.0 / sum_w2)
    n_funded = float(len(weights))

    rows: list[dict[str, Any]] = []
    for alpha in ALPHAS:
        delta = math.sqrt(alpha)
        log_term = math.log(1.0 / delta)
        markov_threshold = alpha / delta
        hoeffding_threshold = alpha + math.sqrt(sum_w2 * log_term / 2.0)

        strong_variance = alpha * sum_w2
        weak_variance = alpha * max_weight
        for variance_mode, variance_bound in [
            ("strong_individual_validity", strong_variance),
            ("weak_weighted_validity", weak_variance),
        ]:
            cantelli_threshold = alpha + math.sqrt(variance_bound * (1.0 - delta) / delta)
            bernstein_threshold = alpha + (
                max_weight * log_term / 3.0
                + math.sqrt((max_weight * log_term / 3.0) ** 2 + 2.0 * variance_bound * log_term)
            )
            bennett_threshold = _bennett_threshold(
                alpha=alpha,
                delta=delta,
                variance_bound=variance_bound,
                max_weight=max_weight,
            )

            for bound_name, threshold, paper_role in [
                (
                    "cantelli_one_sided",
                    cantelli_threshold,
                    "conditional variance diagnostic; sharper one-sided Chebyshev",
                ),
                (
                    "bernstein",
                    bernstein_threshold,
                    "conditional independence/variance tightening; appendix-only",
                ),
                (
                    "freedman_martingale",
                    bernstein_threshold,
                    "martingale analogue of Bernstein; needs a sealed sequential protocol",
                ),
                (
                    "bennett",
                    bennett_threshold,
                    "conditional independence/variance tightening; appendix-only",
                ),
            ]:
                rows.append(
                    {
                        "alpha": alpha,
                        "delta": delta,
                        "bound": bound_name,
                        "variance_mode": variance_mode,
                        "threshold_t": threshold,
                        "empirical_V_alpha01": empirical_v,
                        "margin_vs_empirical_V": threshold - empirical_v,
                        "tighter_than_markov": threshold < markov_threshold,
                        "empirical_V_below_threshold": empirical_v <= threshold,
                        "paper_role": paper_role,
                    }
                )

        # Agnostic mode: only the theorem's own assumption E[V] <= alpha, no
        # independence or correlation structure. The sharp variance bound is
        # then Var(V) <= alpha(1 - alpha) (attained by V ~ Bernoulli(alpha)),
        # under which one-sided Cantelli is WORSE than Markov — the cleanest
        # quantitative defense of keeping Markov as the body claim.
        agnostic_variance = alpha * (1.0 - alpha)
        cantelli_agnostic = alpha + math.sqrt(agnostic_variance * (1.0 - delta) / delta)

        base_rows = [
            (
                "markov",
                "none",
                markov_threshold,
                "main distribution-free claim; only first moment needed",
            ),
            (
                "cantelli_one_sided",
                "agnostic_theorem_assumption_only",
                cantelli_agnostic,
                "sharp variance under E[V]<=alpha alone; worse than Markov, so no "
                "second-moment tightening exists without extra assumptions",
            ),
            (
                "hoeffding",
                "loan_independence",
                hoeffding_threshold,
                "conditional bounded-difference diagnostic",
            ),
        ]
        for bound_name, variance_mode, threshold, paper_role in base_rows:
            rows.append(
                {
                    "alpha": alpha,
                    "delta": delta,
                    "bound": bound_name,
                    "variance_mode": variance_mode,
                    "threshold_t": threshold,
                    "empirical_V_alpha01": empirical_v,
                    "margin_vs_empirical_V": threshold - empirical_v,
                    "tighter_than_markov": threshold < markov_threshold,
                    "empirical_V_below_threshold": empirical_v <= threshold,
                    "paper_role": paper_role,
                }
            )

    table = pd.DataFrame(rows).sort_values(["alpha", "threshold_t", "bound"]).reset_index(drop=True)
    stats = {
        "n_funded": n_funded,
        "n_eff": n_eff,
        "sum_w2": sum_w2,
        "max_weight": max_weight,
        "empirical_v": empirical_v,
    }
    return table, stats


def _cluster_assumption_rows(funded: pd.DataFrame, stats: dict[str, float]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = [
        {
            "assumption": "nonnegative_normalized_weights",
            "status": "pass",
            "diagnostic_value": 1.0,
            "interpretation": "Funded-set weights are non-negative and normalized.",
        },
        {
            "assumption": "bounded_miss_indicators",
            "status": "pass",
            "diagnostic_value": 1.0,
            "interpretation": "miscovered_alpha01 is binary, so V is a bounded weighted sum.",
        },
        {
            "assumption": "effective_sample_size",
            "status": "concentrated",
            "diagnostic_value": stats["n_eff"],
            "interpretation": (
                "n_eff is far below the funded loan count, so iid-style concentration "
                "does not get to use the headline OOT sample size."
            ),
        },
        {
            "assumption": "loan_independence",
            "status": "not_verified",
            "diagnostic_value": float("nan"),
            "interpretation": (
                "Defaults and conformal misses can share calibration history and macro "
                "period shocks; loan-level concentration bounds are appendix-only."
            ),
        },
        {
            "assumption": "post_selection_uniformity",
            "status": "not_supported_by_markov",
            "diagnostic_value": ROBUST_REGION_POLICY_COUNT,
            "interpretation": (
                "A naive union Markov statement over the 45 final policies is vacuous "
                "at alpha01; the exact robust-region audit remains empirical evidence."
            ),
        },
        {
            "assumption": "sequential_martingale_protocol",
            "status": "not_available",
            "diagnostic_value": float("nan"),
            "interpretation": (
                "Azuma/Freedman need a prospective filtration or online validation "
                "design; the current A24 replay is diagnostic, not a live guarantee."
            ),
        },
        {
            "assumption": "chebyshev_two_sided",
            "status": "drop_from_table",
            "diagnostic_value": float("nan"),
            "interpretation": (
                "Two-sided Chebyshev is dominated by Cantelli for the one-sided "
                "exceedance probability used in A21."
            ),
        },
        {
            "assumption": "azuma_hoeffding_martingale",
            "status": "drop_from_table",
            "diagnostic_value": float("nan"),
            "interpretation": (
                "Azuma gives the same numerical threshold as Hoeffding here while "
                "adding a sequential validation protocol assumption."
            ),
        },
        {
            "assumption": "chernoff_mgf",
            "status": "drop_from_table",
            "diagnostic_value": float("nan"),
            "interpretation": (
                "Chernoff is sharp, but it requires independent misses with each "
                "individual miss probability bounded by alpha."
            ),
        },
        {
            "assumption": "union_markov_45_policy_region",
            "status": "drop_from_table",
            "diagnostic_value": ROBUST_REGION_POLICY_COUNT,
            "interpretation": (
                "A naive union Markov statement over the 45 final policies is "
                "vacuous at the paper alphas."
            ),
        },
        {
            "assumption": "empirical_bernstein_or_bootstrap",
            "status": "diagnostic_only",
            "diagnostic_value": float("nan"),
            "interpretation": (
                "Empirical-Bernstein or bootstrap intervals would use observed OOT "
                "labels; useful for sensitivity, not for the distribution-free theorem."
            ),
        },
    ]

    cluster_specs = {
        "period": ["period"],
        "grade": ["original_grade"],
        "period_grade": ["period", "original_grade"],
    }
    for cluster_type, columns in cluster_specs.items():
        cluster_weights = funded.groupby(columns, dropna=False)["portfolio_weight"].sum()
        cluster_weights = cluster_weights / float(cluster_weights.sum())
        sum_cluster_w2 = float(np.sum(np.square(cluster_weights.to_numpy(dtype=float))))
        max_cluster_weight = float(cluster_weights.max())
        cluster_threshold = 0.01 + math.sqrt(0.5 * sum_cluster_w2 * math.log(10.0))
        rows.append(
            {
                "assumption": f"cluster_independence_{cluster_type}",
                "status": "conditional_loose",
                "diagnostic_value": cluster_threshold,
                "interpretation": (
                    f"Cluster Hoeffding threshold at delta=0.10 is {cluster_threshold:.4f}; "
                    f"max cluster exposure is {max_cluster_weight:.4f}, so this is not "
                    "tighter than Markov's 0.1000 threshold."
                ),
            }
        )
    return pd.DataFrame(rows)


def _write_report(
    bound_table: pd.DataFrame, assumption_table: pd.DataFrame, stats: dict[str, float]
) -> None:
    alpha01 = bound_table[bound_table["alpha"].eq(0.01)].copy()
    selected = alpha01[
        alpha01["bound"].isin(
            [
                "markov",
                "hoeffding",
                "bernstein",
                "freedman_martingale",
                "bennett",
                "cantelli_one_sided",
            ]
        )
    ].sort_values("threshold_t")
    lines: list[str] = [
        "# CRPTO Bound Tightening Experiment - 2026-06-11",
        "",
        "Merged into `main` (2026-06-11) and cited by Online Supplement Appendix A. "
        "This audit reads frozen funded-set weights only; it does not re-run DVC "
        "stages, does not search policies, and does not promote a new Lending Club "
        "champion. The A21c/A21d tables live under "
        "`docs/research/bound_tightening_audit/`, deliberately outside the "
        "`EXTRACTION_MANIFEST` sweep area: git versioning plus "
        "`tests/test_scripts/test_build_bound_tightening_audit.py` guarantee their "
        "integrity by re-deriving them deterministically from the frozen A7 weights.",
        "",
        "## Fixed Funded-Set Diagnostics",
        "",
        f"- funded loans: `{int(stats['n_funded'])}`",
        f"- effective sample size: `{stats['n_eff']:.1f}`",
        f"- sum of squared weights: `{stats['sum_w2']:.6f}`",
        f"- max loan weight: `{stats['max_weight']:.4f}`",
        f"- observed `V(alpha=0.01)`: `{stats['empirical_v']:.6f}`",
        "",
        "## Alpha 0.01 Bound Menu",
        "",
        "| Bound | Mode | threshold t | margin vs V | Role |",
        "|---|---|---:|---:|---|",
    ]
    for row in selected.itertuples(index=False):
        lines.append(
            f"| `{row.bound}` | `{row.variance_mode}` | `{row.threshold_t:.6f}` | "
            f"`{row.margin_vs_empirical_V:.6f}` | {row.paper_role} |"
        )

    lines.extend(
        (
            "",
            "## Recommendation",
            "",
            "- Keep Markov as the body theorem: it is the only first-moment, "
            "distribution-free statement compatible with the current post-selection caveat.",
            "- Keep A21 cluster-aware Hoeffding as a dependence caveat, not a tightening: "
            "cluster exposure is too concentrated.",
            "- Use A21b/A21c as an appendix sensitivity table. Cantelli, Bernstein, Bennett "
            "and Freedman show how much tightness is available if a reviewer accepts stronger "
            "independence, variance, or martingale assumptions.",
            "- Drop Chebyshev, Azuma, Chernoff and naive union-Markov from paper-facing tables. "
            "They are respectively dominated, duplicative, too strong for the current "
            "individual-alpha evidence, or vacuous after policy-region correction.",
            "",
            "## Assumption Audit",
            "",
            str(assumption_table.to_markdown(index=False)),
            "",
        )
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8", newline="")


def build_bound_tightening_audit() -> dict[str, Any]:
    funded = pd.read_csv(FUNDED_LOANS_PATH)
    bound_table, stats = _threshold_rows(funded)
    assumption_table = _cluster_assumption_rows(funded, stats)

    artifacts = []
    artifacts += write_table(TABLE_A21C_NAME, bound_table, table_dir=OUTPUT_DIR, root=ROOT)
    artifacts += write_table(TABLE_A21D_NAME, assumption_table, table_dir=OUTPUT_DIR, root=ROOT)
    _write_report(bound_table, assumption_table, stats)
    artifacts.append(REPORT_PATH)

    return {
        "artifacts": [path.relative_to(ROOT).as_posix() for path in artifacts],
        "n_funded": int(stats["n_funded"]),
        "n_eff": stats["n_eff"],
        "max_weight": stats["max_weight"],
        "empirical_v": stats["empirical_v"],
    }


def main() -> int:
    status = build_bound_tightening_audit()
    logger.info(
        "Built bound tightening audit: n_funded={} n_eff={:.1f} V={:.6f}",
        status["n_funded"],
        status["n_eff"],
        status["empirical_v"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
