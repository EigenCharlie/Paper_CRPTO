"""Build the CVaR/OCE tail-constrained re-optimization frontier (Table A22).

This closes the P2 roadmap item "funded-set risk OCE/CVaR as a re-optimized
constraint" by turning the A12 tail-risk *diagnostic* into an **active
selection constraint** over the bound-aware robust region.

What it does, concretely:

1. Re-solves the 45 alpha01-safe robust-region policies with the Windows-safe
   HiGHS backend (same machinery as the A20 audit). The decision is made from
   conformal intervals only (``compute_effective_pd`` uses ``pd_point``/
   ``pd_high``); observed labels are never used to choose loans.
2. For each funded set, computes the *decision-time* worst-case loss rate
   ``l_i = pd_high_i * LGD - (1 - pd_high_i) * int_rate_i`` (the ex-ante
   quantity a risk committee can constrain), and its exposure-weighted CVaR_95
   and entropic OCE. It also reports the realized (label-based) CVaR for
   comparison with the A20 audit.
3. Sweeps a CVaR_95 cap and, at each cap, selects the alpha01-passing,
   CVaR-feasible policy with the highest *frozen* realized return. This is a
   genuine re-optimization of the selection under an added tail constraint and
   traces the return kept as the tail budget tightens.

Authoritative return / V / Gamma_CP / exact-pass values are read from the
frozen shortlist and, for promoted/editorial comparator roles, overlaid from
``final_project_promotion.json``. The re-solve is used only to recover
allocations for tail scoring. No frozen artifact is overwritten and the
economic champion remains the official champion: the CVaR-constrained policy is
reported as a journal challenger.

Usage::

    uv run python scripts/build_tail_constrained_reoptimization.py
    uv run python scripts/build_tail_constrained_reoptimization.py --max-policies 3  # fast dev
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_tail_satisficing_challenger_audit import (  # noqa: E402
    CONFORMAL_INTERVALS_PATH,
    DEFAULT_ALPHA,
    DEFAULT_LGD,
    OPTIMIZATION_CONFIG_PATH,
    PROMOTION_PATH,
    SHORTLIST_PATH,
    _policy_role,
    _prepare_portfolio_inputs,
)
from scripts.optimize_portfolio_tradeoff import _solve_single  # noqa: E402
from src.optimization.tail_satisficing_objective import (  # noqa: E402
    entropic_oce,
    funded_loss_rate,
    weighted_cvar,
    weighted_mean,
)

TABLE_DIR = ROOT / "reports" / "crpto" / "tables"
MODEL_DIR = ROOT / "models"
STATUS_PATH = MODEL_DIR / "crpto_tail_constrained_reopt_status.json"
TABLE_A22_NAME = "crpto_tableA22_tail_constrained_reoptimization"

OCE_THETA = 5.0
CVAR_TAIL = 0.95
# Operating-point rule for the headline challenger: tightest tail cap whose
# selected policy stays within this fraction of the economic champion return.
RETURN_TOLERANCE_PCT = 2.0
PROMOTION_ROLE_KEYS = {
    "economic_champion": "final_champion",
    "theorem_tight_comparator": "theorem_tight_comparator",
    "balanced_comparator": "balanced_comparator",
}
PROMOTION_METRIC_FIELDS = (
    "realized_total_return",
    "alpha01_exact_pass",
    "alpha01_weighted_miscoverage_V",
    "alpha01_gamma_cp",
    "alpha01_violation",
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


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
    csv_path.write_text(
        frame.to_csv(index=False, lineterminator="\n"), encoding="utf-8", newline=""
    )
    tex_path.write_text(
        frame.to_latex(index=False, escape=True, float_format=lambda value: f"{value:.6f}"),
        encoding="utf-8",
        newline="",
    )
    logger.info("Wrote {}", csv_path.relative_to(ROOT))
    logger.info("Wrote {}", tex_path.relative_to(ROOT))
    return [csv_path, tex_path]


def _sync_official_promotion_metrics(
    frame: pd.DataFrame,
    promotion: dict[str, Any],
    *,
    role_col: str,
    prefix: str = "",
) -> pd.DataFrame:
    """Overlay official rebaseline metrics for promoted editorial roles.

    The robust-region shortlist is retained as provenance, but promoted roles
    may have updated V/Gamma values after a formal replay. Applying the promotion
    JSON here keeps A22 aligned without mutating the frozen search artifact.
    """
    synced = frame.copy()
    if role_col not in synced.columns:
        return synced
    for role, record_key in PROMOTION_ROLE_KEYS.items():
        record = promotion.get(record_key, {})
        if not isinstance(record, dict):
            continue
        mask = synced[role_col].astype(str).eq(role)
        if not mask.any():
            continue
        for field in PROMOTION_METRIC_FIELDS:
            target_col = f"{prefix}{field}"
            if target_col in synced.columns and field in record:
                synced.loc[mask, target_col] = record[field]
    return synced


def worst_case_loss_rate(pd_high: np.ndarray, int_rates: np.ndarray, *, lgd: float) -> np.ndarray:
    """Decision-time worst-case net loss rate per unit of exposure.

    Mirrors ``funded_loss_rate`` but replaces the observed default flag with the
    conformal upper bound ``pd_high`` (= u_i), so the quantity is available
    before labels are observed and is the legitimate object for an ex-ante tail
    constraint.
    """
    pd_high_array = np.clip(np.asarray(pd_high, dtype=float), 0.0, 1.0)
    int_rate_array = np.asarray(int_rates, dtype=float)
    return pd_high_array * float(lgd) - (1.0 - pd_high_array) * int_rate_array


def _solve_and_score_policy(
    *,
    row: pd.Series,
    loans: pd.DataFrame,
    pd_point: np.ndarray,
    pd_low: np.ndarray,
    pd_high: np.ndarray,
    lgd: np.ndarray,
    int_rates: np.ndarray,
    default_flag: np.ndarray,
    optimization_config: dict[str, Any],
    promotion: dict[str, Any],
) -> dict[str, Any]:
    solved, allocation = _solve_single(
        loans=loans,
        pd_point=pd_point,
        pd_low=pd_low,
        pd_high=pd_high,
        lgd=lgd,
        int_rates=int_rates,
        default_flag=default_flag,
        total_budget=float(optimization_config["portfolio"]["total_budget"]),
        max_concentration=float(optimization_config["portfolio"]["max_concentration"]),
        risk_tolerance=float(row["risk_tolerance"]),
        robust=True,
        uncertainty_aversion=float(row["uncertainty_aversion"]),
        min_budget_utilization=float(row["min_budget_utilization"]),
        pd_cap_slack_penalty=float(row["pd_cap_slack_penalty"]),
        time_limit=int(optimization_config["optimization"]["time_limit"]),
        threads=int(optimization_config["optimization"]["threads"]),
        solver_backend="highs",
        policy_mode=str(row["policy_mode"]),
        gamma=float(row["gamma"]),
        delta_cap_quantile=float(row["delta_cap_quantile"]),
        tail_focus_quantile=float(row["tail_focus_quantile"]),
        random_seed=42,
    )
    loan_amounts = (
        loans["loan_amnt"].to_numpy(dtype=float)
        if "loan_amnt" in loans.columns
        else np.full(len(loans), 10_000.0)
    )
    exposure = allocation * loan_amounts
    decision_loss = worst_case_loss_rate(pd_high, int_rates, lgd=DEFAULT_LGD)
    realized_loss = funded_loss_rate(default_flag, int_rates, lgd=DEFAULT_LGD)
    return {
        "candidate_rank": int(row["candidate_rank"]),
        "paper_role": _policy_role(row, promotion),
        "policy_mode": str(row["policy_mode"]),
        "risk_tolerance": float(row["risk_tolerance"]),
        "gamma": float(row["gamma"]),
        "uncertainty_aversion": float(row["uncertainty_aversion"]),
        # Authoritative frozen metrics (agree with final_project_promotion.json).
        "realized_total_return": float(row["realized_total_return"]),
        "alpha01_exact_pass": bool(row["alpha01_exact_pass"]),
        "alpha01_weighted_miscoverage_V": float(row["alpha01_weighted_miscoverage_V"]),
        "alpha01_gamma_cp": float(row["alpha01_gamma_cp"]),
        "n_funded": int(solved["n_funded"]),
        "total_allocated": float(solved["total_allocated"]),
        "solver_status": str(solved["solver_status"]),
        # Decision-time (pd_high-based) tail risk: the constrainable ex-ante object.
        "decision_time_cvar95": weighted_cvar(decision_loss, exposure, tail=CVAR_TAIL),
        "decision_time_oce_theta5": entropic_oce(decision_loss, exposure, theta=OCE_THETA),
        "decision_time_mean_loss_rate": weighted_mean(decision_loss, exposure),
        # Realized (label-based) CVaR, comparable to the A20 audit.
        "realized_cvar95": weighted_cvar(realized_loss, exposure, tail=CVAR_TAIL),
    }


def _build_cap_frontier(
    scored: pd.DataFrame, champion_return: float
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Trace the efficient return-vs-CVaR frontier under an active tail cap.

    Each alpha01-safe policy's own decision-time CVaR is used as a natural cap
    breakpoint; at each cap we select the highest-return feasible policy. Keeping
    the first occurrence of each distinct winner yields the efficient-frontier
    corners (tightest cap at which a given policy becomes the return-maximizer).
    """
    feasible_pool = scored.loc[scored["alpha01_exact_pass"]].copy()
    cvar_values = feasible_pool["decision_time_cvar95"].to_numpy(dtype=float)
    cvar_min = float(np.min(cvar_values))
    cvar_max = float(np.max(cvar_values))
    caps = np.sort(np.unique(cvar_values))

    rows: list[dict[str, Any]] = []
    for cap in caps:
        admissible = feasible_pool.loc[feasible_pool["decision_time_cvar95"] <= cap + 1e-12]
        if admissible.empty:
            continue
        winner = admissible.sort_values(
            ["realized_total_return", "decision_time_cvar95"], ascending=[False, True]
        ).iloc[0]
        rows.append(
            {
                "cvar95_cap": float(cap),
                "n_feasible_policies": int(len(admissible)),
                "selected_candidate_rank": int(winner["candidate_rank"]),
                "selected_paper_role": str(winner["paper_role"]),
                "selected_policy_mode": str(winner["policy_mode"]),
                "selected_risk_tolerance": float(winner["risk_tolerance"]),
                "selected_gamma": float(winner["gamma"]),
                "selected_uncertainty_aversion": float(winner["uncertainty_aversion"]),
                "selected_realized_total_return": float(winner["realized_total_return"]),
                "return_delta_vs_champion_pct": (
                    (float(winner["realized_total_return"]) - champion_return)
                    / abs(champion_return)
                    * 100.0
                ),
                "selected_decision_time_cvar95": float(winner["decision_time_cvar95"]),
                "selected_decision_time_oce_theta5": float(winner["decision_time_oce_theta5"]),
                "selected_realized_cvar95": float(winner["realized_cvar95"]),
                "selected_alpha01_weighted_miscoverage_V": float(
                    winner["alpha01_weighted_miscoverage_V"]
                ),
                "selected_alpha01_gamma_cp": float(winner["alpha01_gamma_cp"]),
                "selected_n_funded": int(winner["n_funded"]),
            }
        )
    frontier = (
        pd.DataFrame(rows)
        .drop_duplicates(subset=["selected_candidate_rank"], keep="first")
        .reset_index(drop=True)
    )

    # Headline challenger: tightest cap whose pick stays within tolerance of champion.
    within = frontier.loc[
        frontier["return_delta_vs_champion_pct"] >= -RETURN_TOLERANCE_PCT
    ].sort_values("selected_decision_time_cvar95")
    challenger = (within.iloc[0] if not within.empty else frontier.iloc[-1]).to_dict()
    summary = {
        "n_alpha01_policies": int(len(feasible_pool)),
        "decision_time_cvar95_min": cvar_min,
        "decision_time_cvar95_max": cvar_max,
        "return_tolerance_pct": RETURN_TOLERANCE_PCT,
        "tail_constrained_challenger": challenger,
        "selection_rule": (
            "max realized_total_return s.t. alpha01_exact_pass and "
            "decision_time_cvar95 <= cap; cap swept over the robust region range"
        ),
        "promotion_status": "journal_reoptimization_challenger_not_champion",
    }
    return frontier, summary


def build_tail_constrained_reoptimization(max_policies: int = 0) -> dict[str, Any]:
    start = datetime.now(tz=UTC)
    promotion = _load_json(PROMOTION_PATH)
    optimization_config = _load_yaml(OPTIMIZATION_CONFIG_PATH)
    shortlist = pd.read_parquet(SHORTLIST_PATH).sort_values("candidate_rank").reset_index(drop=True)
    if max_policies and max_policies > 0:
        # Dev mode: keep the champion + comparators + a spread of the region.
        head = shortlist.head(max_policies)
        shortlist = head.reset_index(drop=True)
        logger.warning("DEV MODE: scoring only {} policies", len(shortlist))

    loans, pd_point, pd_low, pd_high, lgd, int_rates, default_flag = _prepare_portfolio_inputs()
    champion_return = float(promotion["final_champion"]["realized_total_return"])

    scored_rows: list[dict[str, Any]] = []
    for idx, row in shortlist.iterrows():
        logger.info(
            "Re-solving policy {}/{} (candidate_rank={}, mode={}, gamma={})",
            idx + 1,
            len(shortlist),
            row["candidate_rank"],
            row["policy_mode"],
            row["gamma"],
        )
        scored_rows.append(
            _solve_and_score_policy(
                row=row,
                loans=loans,
                pd_point=pd_point,
                pd_low=pd_low,
                pd_high=pd_high,
                lgd=lgd,
                int_rates=int_rates,
                default_flag=default_flag,
                optimization_config=optimization_config,
                promotion=promotion,
            )
        )
    scored = _sync_official_promotion_metrics(
        pd.DataFrame(scored_rows),
        promotion,
        role_col="paper_role",
    )
    frontier, summary = _build_cap_frontier(scored, champion_return)
    frontier = _sync_official_promotion_metrics(
        frontier,
        promotion,
        role_col="selected_paper_role",
        prefix="selected_",
    )

    artifacts = _write_table(TABLE_A22_NAME, frontier)
    status = {
        "schema_version": "2026-06-07.1",
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "elapsed_sec": (datetime.now(tz=UTC) - start).total_seconds(),
        "alpha": DEFAULT_ALPHA,
        "lgd": DEFAULT_LGD,
        "cvar_tail": CVAR_TAIL,
        "oce_theta": OCE_THETA,
        "champion_label": promotion["final_champion"]["label"],
        "champion_realized_total_return": champion_return,
        "n_policies_scored": int(len(scored)),
        "generated_artifacts": [
            str(path.relative_to(ROOT)).replace("\\", "/") for path in artifacts
        ],
        "source_shortlist": str(SHORTLIST_PATH.relative_to(ROOT)).replace("\\", "/"),
        "source_conformal_intervals": str(CONFORMAL_INTERVALS_PATH.relative_to(ROOT)).replace(
            "\\", "/"
        ),
        "reoptimization_summary": summary,
        "per_policy_tail_metrics": scored.sort_values("decision_time_cvar95")
        .round(6)
        .to_dict(orient="records"),
        "champion_promotion_changed": False,
        "notes": [
            "Decision uses conformal intervals only; labels enter solely via "
            "the frozen realized-return diagnostic.",
            "Tail risk is the decision-time worst-case loss (pd_high-based), the "
            "ex-ante object a risk committee can constrain.",
            "No champion search was reopened beyond the 45 frozen robust-region "
            "policies; the economic champion stays official.",
            "For promoted/editorial comparator rows, V/Gamma/return metrics are "
            "overlaid from the current final_project_promotion.json rebaseline "
            "while tail-risk quantities remain from the HiGHS re-solve.",
        ],
    }
    _write_json(STATUS_PATH, status)
    logger.info("Wrote {}", STATUS_PATH.relative_to(ROOT))
    logger.info(
        "Tail-constrained challenger: candidate_rank={} return_delta={:.2f}% cvar95={:.4f}",
        summary["tail_constrained_challenger"]["selected_candidate_rank"],
        summary["tail_constrained_challenger"]["return_delta_vs_champion_pct"],
        summary["tail_constrained_challenger"]["selected_decision_time_cvar95"],
    )
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-policies",
        type=int,
        default=0,
        help="Limit number of policies scored (dev mode); 0 = all 45.",
    )
    args = parser.parse_args()
    build_tail_constrained_reoptimization(max_policies=args.max_policies)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
