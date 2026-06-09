"""Build the tail-risk robust-region audit from frozen CRPTO policies.

This script re-solves the 45 already-shortlisted bound-aware policies with the
Windows-safe HiGHS solver, scores each funded set with OCE/CVaR/satisficing
diagnostics, and writes journal-only audit tables. It does not promote a new
champion and does not overwrite frozen portfolio artifacts.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.optimize_portfolio_tradeoff import (  # noqa: E402
    _align_loans_and_intervals,
    _load_candidates,
    _load_intervals,
    _parse_percent_series,
    _resolve_interval_columns,
    _solve_single,
)
from src.optimization.tail_satisficing_objective import (  # noqa: E402
    SatisficingThreshold,
    entropic_oce,
    funded_loss_rate,
    score_tail_satisficing_objective,
    weighted_cvar,
    weighted_mean,
)
from src.utils.script_helpers import (  # noqa: E402
    first_existing,
    load_json,
    load_yaml,
    write_json,
    write_table,
)

TABLE_DIR = ROOT / "reports" / "crpto" / "tables"
MODEL_DIR = ROOT / "models"
DATA_DIR = ROOT / "data" / "processed"

PROMOTION_PATH = MODEL_DIR / "final_project_promotion.json"
OPTIMIZATION_CONFIG_PATH = ROOT / "configs" / "crpto_optimization.yaml"
OBJECTIVE_CONFIG_PATH = ROOT / "configs" / "crpto_tail_satisficing_objective.yaml"
FUNDED_LOANS_PATH = TABLE_DIR / "crpto_tableA7_funded_set_loans.csv"
SHORTLIST_PATH = (
    DATA_DIR
    / "portfolio_bound_aware"
    / "rank1_alpha01_bound_aware_276k_full_2026-04-05-1734"
    / "portfolio_bound_aware_shortlist.parquet"
)
SHORTLIST_EXACT_PATH = SHORTLIST_PATH.with_name("portfolio_bound_aware_shortlist_exact.parquet")
CONFORMAL_INTERVALS_PATH = (
    DATA_DIR
    / "conformal_gap"
    / "conformal-reopen-2026-04-03-2149__resume__2026-04-05-1612__phase1__final__rank-1"
    / "conformal_intervals_mondrian.parquet"
)
STATUS_PATH = MODEL_DIR / "crpto_tail_satisficing_audit_status.json"

TABLE_A20_NAME = "crpto_tableA20_tail_satisficing_challenger_audit"
TABLE_A21_NAME = "crpto_tableA21_cluster_bound_tightening"
TABLE_A20_CSV = TABLE_DIR / f"{TABLE_A20_NAME}.csv"
DEFAULT_LGD = 0.45
DEFAULT_ALPHA = 0.01
STATUS_SCHEMA_VERSION = "2026-05-12.2"
REPRODUCIBLE_STATUS_TIMESTAMP = "2026-06-07T00:00:00+00:00"


def _portfolio_shortlist_path() -> Path:
    return first_existing(SHORTLIST_EXACT_PATH, SHORTLIST_PATH)


def _write_table(name: str, frame: pd.DataFrame) -> list[Path]:
    return write_table(name, frame, table_dir=TABLE_DIR, root=ROOT)


def _cached_a20_status(frame: pd.DataFrame) -> dict[str, Any]:
    challenger = frame.iloc[0].to_dict()
    champion_rank = int(
        frame.loc[frame["paper_role"].eq("economic_champion"), "tail_satisficing_rank"].iloc[0]
    )
    return {
        "n_policies_audited": int(len(frame)),
        "champion_tail_satisficing_rank": champion_rank,
        "selected_audit_challenger": challenger,
        "selection_rule": (
            "satisficing_pass desc; cvar_95_loss_rate asc; "
            "entropic_oce_theta5 asc; realized_total_return desc"
        ),
        "promotion_status": "journal_audit_only_not_champion",
        "cache_status": "reused_complete_a20_table",
    }


def _load_cached_a20_table(shortlist: pd.DataFrame) -> pd.DataFrame | None:
    if not TABLE_A20_CSV.exists():
        return None
    cached = pd.read_csv(TABLE_A20_CSV)
    required_cols = {
        "tail_satisficing_rank",
        "candidate_rank",
        "paper_role",
        "realized_total_return",
        "alpha01_weighted_miscoverage_V",
        "alpha01_gamma_cp",
    }
    if not required_cols.issubset(cached.columns):
        return None
    source_cols = [
        "candidate_rank",
        "realized_total_return",
        "alpha01_weighted_miscoverage_V",
        "alpha01_gamma_cp",
    ]
    merged = cached[source_cols].merge(
        shortlist[source_cols],
        on="candidate_rank",
        how="inner",
        suffixes=("_cached", "_source"),
    )
    if len(merged) != len(shortlist):
        return None
    numeric_cols = [
        "realized_total_return",
        "alpha01_weighted_miscoverage_V",
        "alpha01_gamma_cp",
    ]
    for col in numeric_cols:
        if not np.allclose(
            merged[f"{col}_cached"].to_numpy(dtype=float),
            merged[f"{col}_source"].to_numpy(dtype=float),
            rtol=1e-10,
            atol=1e-10,
        ):
            return None
    if not cached["paper_role"].eq("economic_champion").any():
        return None
    logger.info("Reusing complete cached A20 tail audit table: {}", TABLE_A20_CSV)
    return cached


def _thresholds_from_config(config: dict[str, Any]) -> tuple[SatisficingThreshold, ...]:
    raw = config.get("satisficing_thresholds", {})
    thresholds: list[SatisficingThreshold] = []
    for metric, spec in raw.items():
        thresholds.append(
            SatisficingThreshold(
                metric=str(metric),
                sense=str(spec["sense"]),  # type: ignore[arg-type]
                threshold=spec["threshold"],
            )
        )
    return tuple(thresholds)


def _policy_matches(row: pd.Series, policy: dict[str, Any]) -> bool:
    fields = [
        "risk_tolerance",
        "gamma",
        "delta_cap_quantile",
        "tail_focus_quantile",
        "uncertainty_aversion",
        "min_budget_utilization",
        "pd_cap_slack_penalty",
    ]
    for field in fields:
        if abs(float(row[field]) - float(policy[field])) > 1e-9:
            return False
    return str(row["policy_mode"]) == str(policy["policy_mode"])


def _policy_role(row: pd.Series, promotion: dict[str, Any]) -> str:
    if _policy_matches(row, promotion["final_champion"]):
        return "economic_champion"
    if _policy_matches(row, promotion["theorem_tight_comparator"]):
        return "theorem_tight_comparator"
    if _policy_matches(row, promotion["balanced_comparator"]):
        return "balanced_comparator"
    return "robust_region_policy"


def _prepare_portfolio_inputs() -> tuple[
    pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray
]:
    candidates = _load_candidates().reset_index(drop=True)
    intervals = _load_intervals(conformal_intervals_path=str(CONFORMAL_INTERVALS_PATH)).reset_index(
        drop=True
    )
    loans, ints = _align_loans_and_intervals(
        candidates=candidates,
        intervals=intervals,
        max_candidates=0,
        random_state=42,
    )
    col_point, col_low, col_high = _resolve_interval_columns(ints)
    n = len(loans)
    pd_point = ints[col_point].to_numpy(dtype=float)
    pd_low = ints[col_low].to_numpy(dtype=float)
    pd_high = ints[col_high].to_numpy(dtype=float)
    lgd = np.full(n, DEFAULT_LGD, dtype=float)
    int_rates = (
        _parse_percent_series(loans["int_rate"])
        if "int_rate" in loans.columns
        else np.full(n, 0.12, dtype=float)
    )
    default_flag = (
        pd.to_numeric(loans["default_flag"], errors="coerce").fillna(0).to_numpy(dtype=int)
        if "default_flag" in loans.columns
        else pd.to_numeric(ints["y_true"], errors="coerce").fillna(0).to_numpy(dtype=int)
    )
    return loans, pd_point, pd_low, pd_high, lgd, int_rates, default_flag


def _score_policy(
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
    objective_config: dict[str, Any],
    thresholds: tuple[SatisficingThreshold, ...],
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
        else np.ones(len(loans), dtype=float) * 10_000.0
    )
    exposure = allocation * loan_amounts
    loss_rates = funded_loss_rate(default_flag, int_rates, lgd=DEFAULT_LGD)
    extra_metrics = {
        "weighted_miscoverage": float(row["alpha01_weighted_miscoverage_V"]),
        "gamma_cp": float(row["alpha01_gamma_cp"]),
        "exact_pass": bool(row["alpha01_exact_pass"]),
        "robust_region_pass": bool(row["alpha01_exact_pass"]),
    }
    objective_settings = objective_config["objective_score"]
    scored = score_tail_satisficing_objective(
        expected_return=float(row["realized_total_return"]),
        loss_rates=loss_rates,
        weights=exposure,
        thresholds=thresholds,
        extra_metrics=extra_metrics,
        cvar_tail=float(objective_config["tail_risk"]["cvar_tail"]),
        oce_theta=float(objective_config["tail_risk"]["entropic_oce_theta"]),
        cvar_penalty=float(objective_settings["cvar_penalty"]),
        oce_penalty=float(objective_settings["oce_penalty"]),
        satisficing_shortfall_penalty=float(objective_settings["satisficing_shortfall_penalty"]),
        risk_scale=float(objective_settings["risk_scale"]),
    )
    return {
        "candidate_rank": int(row["candidate_rank"]),
        "risk_tolerance": float(row["risk_tolerance"]),
        "policy_mode": str(row["policy_mode"]),
        "gamma": float(row["gamma"]),
        "uncertainty_aversion": float(row["uncertainty_aversion"]),
        "realized_total_return": float(row["realized_total_return"]),
        "return_first_rank": int(row["return_first_rank"]),
        "alpha01_exact_pass": bool(row["alpha01_exact_pass"]),
        "alpha01_weighted_miscoverage_V": float(row["alpha01_weighted_miscoverage_V"]),
        "alpha01_gamma_cp": float(row["alpha01_gamma_cp"]),
        "audit_solver_status": str(solved["solver_status"]),
        "audit_solver_backend": "highs",
        "audit_total_allocated": float(solved["total_allocated"]),
        "audit_n_funded": int(solved["n_funded"]),
        "mean_loss_rate": weighted_mean(loss_rates, exposure),
        "cvar_95_loss_rate": weighted_cvar(loss_rates, exposure, tail=0.95),
        "entropic_oce_theta5": entropic_oce(loss_rates, exposure, theta=5.0),
        "satisficing_pass": bool(scored.satisficing_pass),
        "min_satisficing_margin": float(scored.min_satisficing_margin),
        "satisficing_shortfall": float(scored.satisficing_shortfall),
        "tail_satisficing_objective_value": float(scored.objective_value),
    }


def _build_a20_table() -> tuple[pd.DataFrame, dict[str, Any]]:
    promotion = load_json(PROMOTION_PATH)
    optimization_config = load_yaml(OPTIMIZATION_CONFIG_PATH)
    objective_config = load_yaml(OBJECTIVE_CONFIG_PATH)
    thresholds = _thresholds_from_config(objective_config)
    shortlist = (
        pd.read_parquet(_portfolio_shortlist_path())
        .sort_values("candidate_rank")
        .reset_index(drop=True)
    )
    cached = _load_cached_a20_table(shortlist)
    if cached is not None:
        return cached, _cached_a20_status(cached)
    loans, pd_point, pd_low, pd_high, lgd, int_rates, default_flag = _prepare_portfolio_inputs()

    rows: list[dict[str, Any]] = []
    for idx, row in shortlist.iterrows():
        logger.info(
            "Auditing policy {}/{} (candidate_rank={})",
            idx + 1,
            len(shortlist),
            row["candidate_rank"],
        )
        scored = _score_policy(
            row=row,
            loans=loans,
            pd_point=pd_point,
            pd_low=pd_low,
            pd_high=pd_high,
            lgd=lgd,
            int_rates=int_rates,
            default_flag=default_flag,
            optimization_config=optimization_config,
            objective_config=objective_config,
            thresholds=thresholds,
        )
        scored["paper_role"] = _policy_role(row, promotion)
        rows.append(scored)

    frame = pd.DataFrame(rows)
    frame = frame.sort_values(
        ["satisficing_pass", "cvar_95_loss_rate", "entropic_oce_theta5", "realized_total_return"],
        ascending=[False, True, True, False],
    ).reset_index(drop=True)
    frame["tail_satisficing_rank"] = np.arange(1, len(frame) + 1, dtype=int)
    champion = frame.loc[frame["paper_role"].eq("economic_champion")].iloc[0]
    frame["return_delta_vs_champion_pct"] = (
        (frame["realized_total_return"] - float(champion["realized_total_return"]))
        / abs(float(champion["realized_total_return"]))
        * 100.0
    )
    frame["cvar_delta_vs_champion_pct"] = (
        (frame["cvar_95_loss_rate"] - float(champion["cvar_95_loss_rate"]))
        / abs(float(champion["cvar_95_loss_rate"]))
        * 100.0
    )
    cols = [
        "tail_satisficing_rank",
        "candidate_rank",
        "paper_role",
        "risk_tolerance",
        "gamma",
        "uncertainty_aversion",
        "realized_total_return",
        "return_delta_vs_champion_pct",
        "cvar_95_loss_rate",
        "cvar_delta_vs_champion_pct",
        "entropic_oce_theta5",
        "mean_loss_rate",
        "alpha01_weighted_miscoverage_V",
        "alpha01_gamma_cp",
        "satisficing_pass",
        "min_satisficing_margin",
        "satisficing_shortfall",
        "audit_n_funded",
        "audit_solver_backend",
        "audit_solver_status",
    ]
    frame = frame.loc[:, cols]
    status = _cached_a20_status(frame)
    status["cache_status"] = "fresh_solve"
    return frame, status


def _build_cluster_bound_table(funded: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    cluster_specs = {
        "period": ["period"],
        "grade": ["original_grade"],
        "period_grade": ["period", "original_grade"],
    }
    empirical_v = float(
        (funded["portfolio_weight"] * funded["miscovered_alpha01"].astype(bool).astype(float)).sum()
    )
    for cluster_type, columns in cluster_specs.items():
        weights = funded.groupby(columns, dropna=False)["portfolio_weight"].sum()
        sum_w2 = float(np.sum(np.square(weights.to_numpy(dtype=float))))
        max_w = float(weights.max())
        for delta in [0.10, 0.05]:
            ho = math.sqrt(0.5 * sum_w2 * math.log(1.0 / delta))
            cluster_bound = float(DEFAULT_ALPHA + ho)
            rows.append(
                {
                    "cluster_type": cluster_type,
                    "n_clusters": int(len(weights)),
                    "max_cluster_exposure_share": max_w,
                    "sum_cluster_exposure_sq": sum_w2,
                    "alpha": DEFAULT_ALPHA,
                    "delta": float(delta),
                    "empirical_weighted_miscoverage_V": empirical_v,
                    "markov_sqrt_alpha_threshold": math.sqrt(DEFAULT_ALPHA),
                    "cluster_hoeffding_threshold": cluster_bound,
                    "cluster_bound_tighter_than_markov": bool(
                        cluster_bound < math.sqrt(DEFAULT_ALPHA)
                    ),
                    "paper_role": (
                        "conditional caveat: transparent but not tighter than "
                        "Markov when exposure is concentrated"
                    ),
                }
            )
    return pd.DataFrame(rows)


def build_tail_satisficing_audit() -> dict[str, Any]:
    a20, a20_status = _build_a20_table()
    a21 = _build_cluster_bound_table(pd.read_csv(FUNDED_LOANS_PATH))
    artifacts = []
    artifacts += _write_table(TABLE_A20_NAME, a20)
    artifacts += _write_table(TABLE_A21_NAME, a21)
    status = {
        "schema_version": STATUS_SCHEMA_VERSION,
        "generated_at_utc": REPRODUCIBLE_STATUS_TIMESTAMP,
        "elapsed_sec": 0.0,
        "timestamp_policy": "fixed_for_bit_reproducible_manifest",
        "generated_artifacts": [
            str(path.relative_to(ROOT)).replace("\\", "/") for path in artifacts
        ],
        "source_shortlist": str(_portfolio_shortlist_path().relative_to(ROOT)).replace("\\", "/"),
        "source_conformal_intervals": str(CONFORMAL_INTERVALS_PATH.relative_to(ROOT)).replace(
            "\\", "/"
        ),
        "tail_satisficing_audit": a20_status,
        "cluster_bound_audit": {
            "n_rows": int(len(a21)),
            "all_cluster_bounds_tighter_than_markov": bool(
                a21["cluster_bound_tighter_than_markov"].all()
            ),
            "interpretation": (
                "Cluster-aware Hoeffding is transparent but empirically looser "
                "than the Markov sqrt(alpha) threshold for this funded-set "
                "exposure concentration."
            ),
        },
        "champion_promotion_changed": False,
    }
    write_json(STATUS_PATH, status)
    logger.info("Wrote {}", STATUS_PATH.relative_to(ROOT))
    return status


def main() -> int:
    build_tail_satisficing_audit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
