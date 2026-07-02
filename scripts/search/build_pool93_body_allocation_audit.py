"""Export the pool93 body-point funded set and compact grade audit.

This is a paper-facing sidecar, not a new portfolio search. It re-solves the
selected finite-grid body policy from the consolidated frontier at alpha=0.01
and writes row-level funded allocations plus a small grade-bucket table.
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
from scripts.validate_alpha_gamma_bound import (  # noqa: E402
    DEFAULT_LGD,
    DEFAULT_MAX_CONCENTRATION,
    DEFAULT_TIME_LIMIT,
    _compute_effective_pd_vector,
    _compute_intervals_at_alpha,
    _load_aligned_dataset,
)
from src.optimization.portfolio_model import optimize_portfolio_allocation  # noqa: E402

DEFAULT_CONSOLIDATED_TAG = "champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-definitive"
DEFAULT_BODY_ROLE = "body/default balanced return-bound point"


def _default_frontier_path(consolidated_tag: str) -> Path:
    return (
        ROOT
        / "models/experiments/champion_reopen"
        / consolidated_tag
        / "portfolio/pool93_ijds_consolidated_frontier.json"
    )


def _manifest_path(run_tag: str) -> Path:
    return (
        ROOT
        / "models/experiments/champion_reopen"
        / run_tag
        / "portfolio/pool93_ijds_local_refinement_manifest.json"
    )


def _load_role_row(frontier_path: Path, role: str) -> dict[str, Any]:
    payload = json.loads(frontier_path.read_text(encoding="utf-8"))
    matches = [row for row in payload.get("rows", []) if str(row.get("role")) == role]
    if not matches:
        raise ValueError(f"Role {role!r} not found in {frontier_path}")
    return dict(matches[0])


def _policy_from_row(row: dict[str, Any]) -> dict[str, Any]:
    semantic = row.get("semantic_policy_key")
    policy: dict[str, Any] = (
        json.loads(semantic) if isinstance(semantic, str) and semantic.strip() else {}
    )
    for key in [
        "risk_tolerance",
        "policy_mode",
        "gamma",
        "delta_cap_quantile",
        "tail_focus_quantile",
        "uncertainty_aversion",
    ]:
        if key in row:
            policy[key] = row[key]
    policy.setdefault("delta_cap_quantile", 1.0)
    policy.setdefault("tail_focus_quantile", 1.0)
    policy.setdefault("min_budget_utilization", 0.0)
    policy.setdefault("pd_cap_slack_penalty", 0.0)
    policy.setdefault("solver_backend", "highspy")
    return policy


def _grade_bucket(series: pd.Series) -> pd.Series:
    grade = series.fillna("unknown").astype(str).str.upper().str[:1]
    return np.select(
        [grade.isin(["A", "B"]), grade.eq("C"), grade.eq("D"), grade.isin(["E", "F", "G"])],
        ["A-B", "C", "D", "E-G"],
        default="unknown",
    )


def _format_tex_table(summary: pd.DataFrame) -> str:
    lines = [
        "\\begin{tabular}{lrrrrr}",
        "\\toprule",
        "Grade bucket & Funded rows & Exposure share & Default rate & $V$ contribution & Mean $u_i(0.01)$ \\\\",
        "\\midrule",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            f"{row.grade_bucket} & {row.funded_rows:,.0f} & {row.exposure_share:.2%} & {row.default_rate:.2%} & {row.v_contribution:.5f} & {row.mean_pd_high_alpha01:.5f} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", ""])
    return "\n".join(lines)


def build_audit(
    *,
    frontier_path: Path,
    role: str,
    alpha: float,
    output_dir: Path,
    report_table_dir: Path,
    threads: int,
    solver_backend: str | None,
) -> dict[str, Any]:
    row = _load_role_row(frontier_path, role)
    policy = _policy_from_row(row)
    if solver_backend:
        policy["solver_backend"] = solver_backend

    manifest = json.loads(_manifest_path(str(row["run_tag"])).read_text(encoding="utf-8"))
    conformal_intervals_path = str(manifest["conformal_intervals_path"])
    aligned = _load_aligned_dataset(
        conformal_intervals_path=conformal_intervals_path,
        max_candidates=int(manifest.get("max_candidates", 0) or 0),
        random_state=int(manifest.get("random_state", 42)),
    )
    pd_point, pd_low, pd_high = _compute_intervals_at_alpha(aligned, alpha)
    effective_pd = _compute_effective_pd_vector(aligned, pd_point, pd_high, policy)
    int_rates = (
        _parse_percent_series(aligned["int_rate"])
        if "int_rate" in aligned.columns
        else np.full(len(aligned), 0.12)
    )
    loan_amounts = (
        pd.to_numeric(aligned["loan_amnt"], errors="coerce").fillna(1.0).to_numpy(dtype=float)
        if "loan_amnt" in aligned.columns
        else np.ones(len(aligned), dtype=float)
    )
    y_true = (
        pd.to_numeric(aligned["y_true"], errors="coerce").fillna(0).to_numpy(dtype=float)
        if "y_true" in aligned.columns
        else pd.to_numeric(aligned["default_flag"], errors="coerce").fillna(0).to_numpy(dtype=float)
    )
    default_flag = (
        pd.to_numeric(aligned["default_flag"], errors="coerce").fillna(0).to_numpy(dtype=int)
        if "default_flag" in aligned.columns
        else y_true.astype(int)
    )

    solution = optimize_portfolio_allocation(
        loans=aligned,
        pd_point=pd_point,
        pd_low=pd_low,
        pd_high=pd_high,
        lgd=np.full(len(aligned), DEFAULT_LGD, dtype=float),
        int_rates=int_rates,
        total_budget=float(manifest.get("budget", 1_000_000.0)),
        max_concentration=DEFAULT_MAX_CONCENTRATION,
        max_portfolio_pd=float(policy["risk_tolerance"]),
        robust=True,
        uncertainty_aversion=float(policy["uncertainty_aversion"]),
        min_budget_utilization=float(policy["min_budget_utilization"]),
        pd_cap_slack_penalty=float(policy["pd_cap_slack_penalty"]),
        pd_constraint_override=effective_pd,
        time_limit=DEFAULT_TIME_LIMIT,
        threads=max(1, int(threads)),
        solver_backend=str(policy["solver_backend"]),
    )
    if "allocation_vector" in solution:
        alloc = np.asarray(solution["allocation_vector"], dtype=float)
    else:
        alloc = np.array(
            [float(solution["allocation"].get(i, 0.0)) for i in range(len(aligned))],
            dtype=float,
        )

    exposure = alloc * loan_amounts
    total_allocated = float(exposure.sum())
    weights = exposure / max(total_allocated, 1e-6)
    funded = alloc > 0.01
    miscoverage = (y_true > pd_high).astype(float)
    realized_return = np.where(
        funded & (default_flag.astype(int) == 1),
        exposure * (-DEFAULT_LGD),
        np.where(funded, exposure * int_rates, 0.0),
    )
    funded_df = aligned.loc[funded].copy()
    funded_idx = np.flatnonzero(funded)
    funded_df["allocation"] = alloc[funded]
    funded_df["funded_exposure"] = exposure[funded]
    funded_df["funded_weight"] = weights[funded]
    funded_df["pd_point_alpha01"] = pd_point[funded]
    funded_df["pd_low_alpha01"] = pd_low[funded]
    funded_df["pd_high_alpha01"] = pd_high[funded]
    funded_df["effective_pd"] = effective_pd[funded]
    funded_df["miscoverage_alpha01"] = miscoverage[funded]
    funded_df["realized_return"] = realized_return[funded]
    funded_df["grade_bucket"] = (
        _grade_bucket(funded_df["grade"]) if "grade" in funded_df else "unknown"
    )
    funded_df["source_row_position"] = funded_idx

    summary = (
        funded_df.groupby("grade_bucket", dropna=False)
        .agg(
            funded_rows=("allocation", "size"),
            exposure=("funded_exposure", "sum"),
            default_rate=("default_flag", "mean"),
            weighted_default_rate=("funded_weight", lambda s: float(np.sum(s * y_true[s.index]))),
            v_contribution=("funded_weight", lambda s: float(np.sum(s * miscoverage[s.index]))),
            mean_pd_high_alpha01=("pd_high_alpha01", "mean"),
            realized_return=("realized_return", "sum"),
        )
        .reset_index()
    )
    summary["exposure_share"] = summary["exposure"] / max(total_allocated, 1e-6)
    order = pd.Categorical(
        summary["grade_bucket"], ["A-B", "C", "D", "E-G", "unknown"], ordered=True
    )
    summary = summary.assign(_order=order).sort_values("_order").drop(columns="_order")

    output_dir.mkdir(parents=True, exist_ok=True)
    report_table_dir.mkdir(parents=True, exist_ok=True)
    funded_path = output_dir / "pool93_body_allocation_alpha01.parquet"
    summary_path = output_dir / "pool93_body_allocation_alpha01_grade_summary.parquet"
    json_path = output_dir / "pool93_body_allocation_alpha01_audit.json"
    csv_path = report_table_dir / "crpto_tableA36_pool93_body_funded_grade_audit.csv"
    tex_path = report_table_dir / "crpto_tableA36_pool93_body_funded_grade_audit.tex"
    funded_df.to_parquet(funded_path, index=False)
    summary.to_parquet(summary_path, index=False)
    summary.to_csv(csv_path, index=False, float_format="%.9f")
    tex_path.write_text(_format_tex_table(summary), encoding="utf-8")

    payload = {
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "frontier_path": str(frontier_path),
        "role": role,
        "frontier_row": row,
        "manifest_path": str(_manifest_path(str(row["run_tag"]))),
        "conformal_intervals_path": conformal_intervals_path,
        "alpha": float(alpha),
        "policy": policy,
        "solver": {
            "status": str(solution.get("solver_status", "unknown")),
            "backend": str(solution.get("solver_backend", policy["solver_backend"])),
            "threads": int(threads),
        },
        "metrics": {
            "n_funded": int(funded.sum()),
            "total_allocated": round(total_allocated, 6),
            "realized_return": round(float(realized_return.sum()), 6),
            "Gamma_CP": round(float(np.sum(weights * np.clip(pd_high - pd_point, 0.0, 1.0))), 6),
            "V": round(float(np.sum(weights * miscoverage)), 6),
            "weighted_pd_true": round(float(np.sum(weights * y_true)), 6),
            "endpoint_budget_upper": round(
                float(policy["risk_tolerance"])
                + (1.0 - float(policy["gamma"]))
                * float(np.sum(weights * np.clip(pd_high - pd_point, 0.0, 1.0))),
                9,
            ),
            "markov_cap": round(
                float(policy["risk_tolerance"])
                + (1.0 - float(policy["gamma"]))
                * float(np.sum(weights * np.clip(pd_high - pd_point, 0.0, 1.0)))
                + float(np.sqrt(alpha)),
                9,
            ),
            "empirical_coverage_funded": round(float(1.0 - miscoverage[funded].mean()), 6),
        },
        "outputs": {
            "funded_rows": str(funded_path),
            "grade_summary_parquet": str(summary_path),
            "grade_summary_csv": str(csv_path),
            "grade_summary_tex": str(tex_path),
        },
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--consolidated-tag", default=DEFAULT_CONSOLIDATED_TAG)
    parser.add_argument("--frontier", default="")
    parser.add_argument("--role", default=DEFAULT_BODY_ROLE)
    parser.add_argument("--alpha", type=float, default=0.01)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--solver-backend", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--report-table-dir", default=str(ROOT / "reports/crpto/tables"))
    args = parser.parse_args(argv)

    frontier_path = (
        Path(args.frontier) if args.frontier else _default_frontier_path(args.consolidated_tag)
    )
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else ROOT
        / "data/processed/experiments/champion_reopen"
        / args.consolidated_tag
        / "portfolio"
    )
    payload = build_audit(
        frontier_path=frontier_path,
        role=str(args.role),
        alpha=float(args.alpha),
        output_dir=output_dir,
        report_table_dir=Path(args.report_table_dir),
        threads=int(args.threads),
        solver_backend=str(args.solver_backend).strip() or None,
    )
    print(json.dumps(payload["metrics"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
