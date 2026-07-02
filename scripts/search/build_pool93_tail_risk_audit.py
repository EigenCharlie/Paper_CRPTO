"""Regenerate pool93 body-point tail-risk and cluster-bound audit tables.

This sidecar reads the selected pool93 body allocation, not the legacy robust
region. It closes the paper-facing caveat that CVaR/OCE and cluster-bound
diagnostics must be recomputed from the promoted row-level funded set before
being cited as pool93-specific evidence.
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.optimize_portfolio_tradeoff import _parse_percent_series  # noqa: E402
from src.optimization.tail_satisficing_objective import (  # noqa: E402
    entropic_oce,
    funded_loss_rate,
    weighted_cvar,
    weighted_mean,
)

DEFAULT_TAG = "champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-definitive"
DEFAULT_ALLOCATION_PATH = (
    ROOT
    / "data/processed/experiments/champion_reopen"
    / DEFAULT_TAG
    / "portfolio/pool93_body_allocation_alpha01.parquet"
)
DEFAULT_BODY_AUDIT_PATH = (
    ROOT
    / "data/processed/experiments/champion_reopen"
    / DEFAULT_TAG
    / "portfolio/pool93_body_allocation_alpha01_audit.json"
)
DEFAULT_OUTPUT_DIR = ROOT / "models/experiments/champion_reopen" / DEFAULT_TAG / "portfolio"
DEFAULT_TABLE_DIR = ROOT / "reports/crpto/tables"

TABLE_A37_NAME = "crpto_tableA37_pool93_body_tail_risk"
TABLE_A38_NAME = "crpto_tableA38_pool93_body_cluster_bound_audit"
TABLE_A39_NAME = "crpto_tableA39_pool93_body_bootstrap_metrics"
OCE_THETA = 5.0
CVAR_LEVELS = (0.90, 0.95, 0.99)
BOOTSTRAP_DRAWS = 5000
BOOTSTRAP_SEED = 20260702


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_table(table_dir: Path, name: str, frame: pd.DataFrame) -> list[str]:
    table_dir.mkdir(parents=True, exist_ok=True)
    csv_path = table_dir / f"{name}.csv"
    tex_path = table_dir / f"{name}.tex"
    csv_path.write_text(
        frame.to_csv(index=False, lineterminator="\n", float_format="%.9f"),
        encoding="utf-8",
        newline="",
    )
    tex_path.write_text(
        frame.to_latex(index=False, escape=True, float_format=lambda value: f"{value:.6f}"),
        encoding="utf-8",
        newline="",
    )
    return [str(csv_path), str(tex_path)]


def _load_allocation(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"pool93 allocation not found: {path}")
    funded = pd.read_parquet(path)
    required = {
        "funded_exposure",
        "funded_weight",
        "default_flag",
        "int_rate",
        "pd_point_alpha01",
        "pd_high_alpha01",
        "miscoverage_alpha01",
    }
    missing = sorted(required.difference(funded.columns))
    if missing:
        raise ValueError(f"pool93 allocation missing columns: {missing}")
    return funded.copy()


def _prepare_allocation(funded: pd.DataFrame) -> pd.DataFrame:
    prepared = funded.copy()
    prepared["funded_exposure"] = pd.to_numeric(
        prepared["funded_exposure"], errors="coerce"
    ).fillna(0.0)
    total_exposure = float(prepared["funded_exposure"].sum())
    if total_exposure <= 0.0:
        raise ValueError("funded exposure must be positive")
    prepared["funded_weight"] = prepared["funded_exposure"] / total_exposure
    prepared["default_flag"] = pd.to_numeric(prepared["default_flag"], errors="coerce").fillna(0.0)
    prepared["miscoverage_alpha01"] = pd.to_numeric(
        prepared["miscoverage_alpha01"], errors="coerce"
    ).fillna(0.0)
    prepared["pd_point_alpha01"] = pd.to_numeric(
        prepared["pd_point_alpha01"], errors="coerce"
    ).fillna(0.0)
    prepared["pd_high_alpha01"] = pd.to_numeric(
        prepared["pd_high_alpha01"], errors="coerce"
    ).fillna(0.0)
    prepared["int_rate_decimal"] = _parse_percent_series(prepared["int_rate"])
    if "grade_bucket" not in prepared.columns:
        grade = prepared.get("grade", pd.Series("unknown", index=prepared.index))
        prepared["grade_bucket"] = grade.fillna("unknown").astype(str).str.upper().str[:1]
    prepared["issue_period"] = _issue_period(prepared)
    return prepared


def _issue_period(frame: pd.DataFrame) -> pd.Series:
    if "issue_d" not in frame.columns:
        return pd.Series("unknown", index=frame.index, dtype="object")
    parsed = pd.to_datetime(frame["issue_d"], errors="coerce")
    return parsed.dt.to_period("Q").astype("string").fillna("unknown")


def _policy_metrics(body_audit: dict[str, Any]) -> dict[str, float]:
    metrics = body_audit.get("metrics", {})
    if not isinstance(metrics, dict):
        return {}
    return {
        key: float(metrics[key])
        for key in [
            "realized_return",
            "Gamma_CP",
            "V",
            "endpoint_budget_upper",
            "markov_cap",
            "empirical_coverage_funded",
        ]
        if key in metrics
    }


def build_tail_risk_table(
    funded: pd.DataFrame,
    *,
    body_audit: dict[str, Any],
    lgds: tuple[float, ...],
) -> pd.DataFrame:
    prepared = _prepare_allocation(funded)
    exposure = prepared["funded_exposure"].to_numpy(dtype=float)
    int_rates = prepared["int_rate_decimal"].to_numpy(dtype=float)
    default_flag = prepared["default_flag"].to_numpy(dtype=float)
    pd_high = prepared["pd_high_alpha01"].to_numpy(dtype=float)
    weights = prepared["funded_weight"].to_numpy(dtype=float)
    total_exposure = float(exposure.sum())
    policy = _policy_metrics(body_audit)

    rows: list[dict[str, Any]] = []
    for lgd in lgds:
        realized_loss = funded_loss_rate(default_flag, int_rates, lgd=float(lgd))
        decision_loss = pd_high * float(lgd) - (1.0 - pd_high) * int_rates
        row: dict[str, Any] = {
            "paper_role": "pool93_body_default",
            "lgd": float(lgd),
            "funded_rows": int(len(prepared)),
            "total_allocated": total_exposure,
            "weighted_default_rate": float(np.sum(weights * default_flag)),
            "mean_realized_loss_rate": weighted_mean(realized_loss, exposure),
            "funded_set_repriced_return": -weighted_mean(realized_loss, exposure) * total_exposure,
            "decision_time_mean_loss_rate": weighted_mean(decision_loss, exposure),
            "decision_time_oce_theta5": entropic_oce(decision_loss, exposure, theta=OCE_THETA),
            "realized_oce_theta5": entropic_oce(realized_loss, exposure, theta=OCE_THETA),
        }
        for cvar_level in CVAR_LEVELS:
            pct = int(cvar_level * 100)
            row[f"decision_time_cvar{pct}_loss_rate"] = weighted_cvar(
                decision_loss, exposure, tail=cvar_level
            )
            row[f"realized_cvar{pct}_loss_rate"] = weighted_cvar(
                realized_loss, exposure, tail=cvar_level
            )
        row.update(
            {
                "alpha01_weighted_miscoverage_V": policy.get(
                    "V", float(np.sum(weights * prepared["miscoverage_alpha01"].to_numpy()))
                ),
                "alpha01_gamma_cp": policy.get(
                    "Gamma_CP",
                    float(
                        np.sum(
                            weights
                            * np.clip(
                                prepared["pd_high_alpha01"].to_numpy(dtype=float)
                                - prepared["pd_point_alpha01"].to_numpy(dtype=float),
                                0.0,
                                1.0,
                            )
                        )
                    ),
                ),
                "endpoint_budget_upper_alpha01": policy.get("endpoint_budget_upper", np.nan),
                "markov_cap_alpha01": policy.get("markov_cap", np.nan),
                "funded_empirical_coverage": policy.get(
                    "empirical_coverage_funded",
                    float(1.0 - prepared["miscoverage_alpha01"].mean()),
                ),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def _cluster_series(frame: pd.DataFrame, partition: str) -> pd.Series:
    if partition == "period":
        return frame["issue_period"].astype(str)
    if partition == "grade_bucket":
        return frame["grade_bucket"].astype(str)
    if partition == "period_grade":
        return frame["issue_period"].astype(str) + "|" + frame["grade_bucket"].astype(str)
    if partition == "score_vintage":
        if "temporal_segment" in frame.columns:
            return frame["temporal_segment"].fillna("unknown").astype(str)
        return frame["issue_period"].astype(str)
    raise ValueError(f"unsupported partition: {partition}")


def build_cluster_bound_table(
    funded: pd.DataFrame,
    *,
    body_audit: dict[str, Any],
    alpha: float,
    delta: float,
) -> pd.DataFrame:
    prepared = _prepare_allocation(funded)
    weights = prepared["funded_weight"].to_numpy(dtype=float)
    miscoverage = prepared["miscoverage_alpha01"].to_numpy(dtype=float)
    empirical_v = float(np.sum(weights * miscoverage))
    policy = _policy_metrics(body_audit)
    empirical_v = policy.get("V", empirical_v)
    markov_threshold = float(np.sqrt(alpha))
    s2_tightening_threshold = float(2.0 * (markov_threshold - alpha) ** 2 / np.log(1.0 / delta))

    rows: list[dict[str, Any]] = []
    for partition in ("period", "grade_bucket", "period_grade", "score_vintage"):
        clusters = _cluster_series(prepared, partition)
        exposure_share = prepared.groupby(clusters)["funded_weight"].sum()
        sum_w2 = float(np.sum(np.square(exposure_share.to_numpy(dtype=float))))
        threshold = float(alpha + np.sqrt(0.5 * sum_w2 * np.log(1.0 / delta)))
        rows.append(
            {
                "cluster_type": partition,
                "n_clusters": int(exposure_share.size),
                "max_cluster_exposure_share": float(exposure_share.max()),
                "sum_cluster_exposure_sq": sum_w2,
                "alpha": float(alpha),
                "delta": float(delta),
                "empirical_weighted_miscoverage_V": empirical_v,
                "markov_threshold": markov_threshold,
                "cluster_hoeffding_threshold": threshold,
                "sum_w2_tightening_threshold": s2_tightening_threshold,
                "cluster_bound_tighter_than_markov": bool(threshold < markov_threshold),
                "paper_role": "pool93_body_cluster_sensitivity",
            }
        )
    return pd.DataFrame(rows)


def _pool93_metric_snapshot(
    frame: pd.DataFrame,
    *,
    total_exposure: float,
    lgd: float,
) -> dict[str, float]:
    weights = frame["funded_exposure"].to_numpy(dtype=float)
    weights = weights / max(float(weights.sum()), 1e-12)
    exposure = weights * float(total_exposure)
    default_flag = frame["default_flag"].to_numpy(dtype=float)
    miscoverage = frame["miscoverage_alpha01"].to_numpy(dtype=float)
    int_rates = frame["int_rate_decimal"].to_numpy(dtype=float)
    pd_point = frame["pd_point_alpha01"].to_numpy(dtype=float)
    pd_high = frame["pd_high_alpha01"].to_numpy(dtype=float)
    realized_loss = funded_loss_rate(default_flag, int_rates, lgd=float(lgd))
    decision_loss = pd_high * float(lgd) - (1.0 - pd_high) * int_rates
    gamma_cp = float(np.sum(weights * np.clip(pd_high - pd_point, 0.0, 1.0)))
    return {
        "funded_set_repriced_return_lgd45": -weighted_mean(realized_loss, exposure)
        * float(total_exposure),
        "weighted_default_rate": float(np.sum(weights * default_flag)),
        "weighted_miscoverage_V": float(np.sum(weights * miscoverage)),
        "alpha01_gamma_cp": gamma_cp,
        "realized_cvar95_loss_rate": weighted_cvar(realized_loss, exposure, tail=0.95),
        "decision_time_cvar95_loss_rate": weighted_cvar(decision_loss, exposure, tail=0.95),
        "realized_oce_theta5": entropic_oce(realized_loss, exposure, theta=OCE_THETA),
        "n_default_loans": float(np.sum(default_flag)),
        "n_miscovered_loans": float(np.sum(miscoverage)),
    }


def build_bootstrap_table(
    funded: pd.DataFrame,
    *,
    body_audit: dict[str, Any],
    n_draws: int,
    seed: int,
    lgd: float,
) -> pd.DataFrame:
    prepared = _prepare_allocation(funded)
    total_exposure = float(prepared["funded_exposure"].sum())
    observed = _pool93_metric_snapshot(prepared, total_exposure=total_exposure, lgd=lgd)
    policy = _policy_metrics(body_audit)
    if "realized_return" in policy:
        observed["funded_set_repriced_return_lgd45"] = policy["realized_return"]
    if "V" in policy:
        observed["weighted_miscoverage_V"] = policy["V"]
    if "Gamma_CP" in policy:
        observed["alpha01_gamma_cp"] = policy["Gamma_CP"]

    rng = np.random.default_rng(int(seed))
    n_rows = len(prepared)
    draws: list[dict[str, float]] = []
    for _ in range(int(n_draws)):
        sample_index = rng.integers(0, n_rows, size=n_rows)
        sample = prepared.iloc[sample_index].reset_index(drop=True)
        draws.append(_pool93_metric_snapshot(sample, total_exposure=total_exposure, lgd=lgd))

    draw_frame = pd.DataFrame(draws)
    rows: list[dict[str, Any]] = []
    note = "Funded-loan contribution bootstrap; solver input uncertainty is not resampled."
    for metric in draw_frame.columns:
        values = draw_frame[metric]
        rows.append(
            {
                "metric": metric,
                "observed": float(observed[metric]),
                "boot_mean": float(values.mean()),
                "boot_p025": float(values.quantile(0.025)),
                "boot_p50": float(values.quantile(0.50)),
                "boot_p975": float(values.quantile(0.975)),
                "n_draws": int(n_draws),
                "seed": int(seed),
                "note": note,
            }
        )
    return pd.DataFrame(rows)


def build_outputs(
    *,
    allocation_path: Path,
    body_audit_path: Path,
    table_dir: Path,
    output_dir: Path,
    lgds: tuple[float, ...],
    alpha: float,
    delta: float,
    bootstrap_draws: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    funded = _load_allocation(allocation_path)
    body_audit = _read_json(body_audit_path)
    tail_table = build_tail_risk_table(funded, body_audit=body_audit, lgds=lgds)
    cluster_table = build_cluster_bound_table(
        funded, body_audit=body_audit, alpha=alpha, delta=delta
    )
    bootstrap_table = build_bootstrap_table(
        funded,
        body_audit=body_audit,
        n_draws=bootstrap_draws,
        seed=bootstrap_seed,
        lgd=0.45,
    )
    outputs = {
        "tail_risk": _write_table(table_dir, TABLE_A37_NAME, tail_table),
        "cluster_bound": _write_table(table_dir, TABLE_A38_NAME, cluster_table),
        "bootstrap": _write_table(table_dir, TABLE_A39_NAME, bootstrap_table),
    }
    payload = {
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "allocation_path": str(allocation_path),
        "body_audit_path": str(body_audit_path),
        "alpha": float(alpha),
        "delta": float(delta),
        "lgds": list(lgds),
        "bootstrap_draws": int(bootstrap_draws),
        "bootstrap_seed": int(bootstrap_seed),
        "tables": outputs,
        "headline": {
            "baseline_lgd_return": float(
                tail_table.loc[tail_table["lgd"].eq(0.45), "funded_set_repriced_return"].iloc[0]
            )
            if tail_table["lgd"].eq(0.45).any()
            else float(tail_table["funded_set_repriced_return"].iloc[0]),
            "baseline_lgd_realized_cvar95": float(
                tail_table.loc[tail_table["lgd"].eq(0.45), "realized_cvar95_loss_rate"].iloc[0]
            )
            if tail_table["lgd"].eq(0.45).any()
            else float(tail_table["realized_cvar95_loss_rate"].iloc[0]),
            "baseline_lgd_decision_time_cvar95": float(
                tail_table.loc[tail_table["lgd"].eq(0.45), "decision_time_cvar95_loss_rate"].iloc[0]
            )
            if tail_table["lgd"].eq(0.45).any()
            else float(tail_table["decision_time_cvar95_loss_rate"].iloc[0]),
            "min_cluster_hoeffding_threshold": float(
                cluster_table["cluster_hoeffding_threshold"].min()
            ),
            "markov_threshold": float(np.sqrt(alpha)),
            "any_cluster_tighter_than_markov": bool(
                cluster_table["cluster_bound_tighter_than_markov"].any()
            ),
            "bootstrap_return_lgd45_p025": float(
                bootstrap_table.loc[
                    bootstrap_table["metric"].eq("funded_set_repriced_return_lgd45"),
                    "boot_p025",
                ].iloc[0]
            ),
            "bootstrap_return_lgd45_p975": float(
                bootstrap_table.loc[
                    bootstrap_table["metric"].eq("funded_set_repriced_return_lgd45"),
                    "boot_p975",
                ].iloc[0]
            ),
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_path = output_dir / "pool93_body_tail_risk_audit.json"
    audit_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )
    payload["audit_path"] = str(audit_path)
    return payload


def _parse_lgds(raw: str) -> tuple[float, ...]:
    values = tuple(float(part.strip()) for part in raw.split(",") if part.strip())
    if not values:
        raise ValueError("at least one LGD value is required")
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allocation", default=str(DEFAULT_ALLOCATION_PATH))
    parser.add_argument("--body-audit", default=str(DEFAULT_BODY_AUDIT_PATH))
    parser.add_argument("--table-dir", default=str(DEFAULT_TABLE_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--lgds", default="0.35,0.45,0.60")
    parser.add_argument("--alpha", type=float, default=0.01)
    parser.add_argument("--delta", type=float, default=0.10)
    parser.add_argument("--bootstrap-draws", type=int, default=BOOTSTRAP_DRAWS)
    parser.add_argument("--bootstrap-seed", type=int, default=BOOTSTRAP_SEED)
    args = parser.parse_args(argv)

    payload = build_outputs(
        allocation_path=Path(args.allocation),
        body_audit_path=Path(args.body_audit),
        table_dir=Path(args.table_dir),
        output_dir=Path(args.output_dir),
        lgds=_parse_lgds(str(args.lgds)),
        alpha=float(args.alpha),
        delta=float(args.delta),
        bootstrap_draws=int(args.bootstrap_draws),
        bootstrap_seed=int(args.bootstrap_seed),
    )
    print(json.dumps(payload["headline"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
