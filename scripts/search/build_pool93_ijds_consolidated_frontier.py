"""Build a consolidated IJDS frontier across pool93 refinement runs."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.optimization.certificate_semantics import add_policy_aware_bound_columns

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_TAG = "champion-reopen-2026-06-19__pool93__ijds-certificate-semantics-v2"
DEFAULT_RUN_TAGS = [
    "champion-reopen-2026-06-19__pool93__ijds-claim-expanded-refine",
    "champion-reopen-2026-06-19__pool93__ijds-claim-micro-refine",
    "champion-reopen-2026-06-19__pool93__ijds-claim-micro-ext",
    "champion-reopen-2026-06-19__pool93__ijds-claim-bound-closure",
    "champion-reopen-2026-06-19__pool93__ijds-claim-bound-floor-closure",
    "champion-reopen-2026-06-19__pool93__ijds-claim-bound-terminal",
]
DEFAULT_CAPS = [0.30, 0.32, 0.345, 0.36, 0.45]
DEFAULT_BODY_MARKOV_THRESHOLD = 0.35


def _leaderboard_path(run_tag: str) -> Path:
    return (
        ROOT
        / "data/processed/experiments/champion_reopen"
        / run_tag
        / "portfolio/pool93_ijds_local_refinement_leaderboard.parquet"
    )


def _bound_eval_path(run_tag: str) -> Path:
    return (
        ROOT
        / "data/processed/experiments/champion_reopen"
        / run_tag
        / "portfolio/pool93_ijds_local_refinement_bound_eval.parquet"
    )


def _output_path(output_tag: str) -> Path:
    return (
        ROOT
        / "models/experiments/champion_reopen"
        / output_tag
        / "portfolio/pool93_ijds_consolidated_frontier.json"
    )


def _short_run_label(run_tag: str) -> str:
    if run_tag.endswith("__pool93__ijds-claim-expanded-refine"):
        return "expanded"
    if run_tag.endswith("__pool93__ijds-claim-micro-refine"):
        return "micro"
    if run_tag.endswith("__pool93__ijds-claim-micro-ext"):
        return "micro_ext"
    if run_tag.endswith("__pool93__ijds-claim-bound-closure"):
        return "bound_closure"
    if run_tag.endswith("__pool93__ijds-claim-bound-floor-closure"):
        return "bound_floor"
    if run_tag.endswith("__pool93__ijds-claim-bound-terminal"):
        return "bound_terminal"
    return run_tag


def _row_payload(row: pd.Series, role: str) -> dict[str, Any]:
    return {
        "role": role,
        "run_label": str(row["run_label"]),
        "run_tag": str(row["run_tag"]),
        "local_candidate_id": int(row["local_candidate_id"]),
        "family": str(row["local_family"]),
        "anchor_rank": int(row["anchor_rank"]),
        "source_reason": str(row["source_reason"]),
        "risk_tolerance": round(float(row["risk_tolerance"]), 6),
        "policy_mode": str(row["policy_mode"]),
        "gamma": round(float(row["gamma"]), 6),
        "delta_cap_quantile": round(float(row["delta_cap_quantile"]), 6),
        "tail_focus_quantile": round(float(row["tail_focus_quantile"]), 6),
        "uncertainty_aversion": round(float(row["uncertainty_aversion"]), 6),
        "return": round(float(row["alpha01_realized_total_return"]), 6),
        "return_floor_surplus": round(float(row["return_floor_surplus"]), 6),
        "Gamma_CP": round(float(row["alpha01_gamma_cp"]), 6),
        "Gamma_internalized": round(float(row["alpha01_gamma_internalized"]), 6),
        "Gamma_residual": round(float(row["alpha01_gamma_residual"]), 6),
        "V": round(float(row["alpha01_weighted_miscoverage_V"]), 6),
        "endpoint_budget": round(float(row["alpha01_endpoint_budget"]), 9),
        "endpoint_budget_upper": round(float(row["alpha01_endpoint_budget_upper"]), 9),
        "Markov_threshold": round(float(row["alpha01_markov_loss_threshold"]), 9),
        "Markov_cap": round(float(row["alpha01_markov_loss_cap"]), 9),
        "alpha_pass": f"{int(row['alpha_exact_pass_count'])}/{int(row['alpha_exact_check_count'])}",
        "n_funded_mean": round(float(row["n_funded_mean"]), 3),
        "semantic_policy_key": str(row["semantic_policy_key"]),
    }


def _eligible(df: pd.DataFrame) -> pd.DataFrame:
    return df[
        (df["alpha_exact_pass_count"] == df["alpha_exact_check_count"])
        & (df["return_floor_surplus"] >= 0)
    ].copy()


def _score_body_candidate(eligible: pd.DataFrame) -> pd.Series:
    work = eligible.copy()
    score_specs = {
        "return_score": ("alpha01_realized_total_return", False),
        "bound_score": ("alpha01_markov_loss_threshold", True),
        "v_score": ("alpha01_weighted_miscoverage_V", True),
    }
    for score_col, (metric_col, inverse) in score_specs.items():
        lo = float(work[metric_col].min())
        hi = float(work[metric_col].max())
        if hi == lo:
            work[score_col] = 1.0
        elif inverse:
            work[score_col] = (hi - work[metric_col]) / (hi - lo)
        else:
            work[score_col] = (work[metric_col] - lo) / (hi - lo)
    work["ijds_balanced_score"] = (
        0.40 * work["return_score"] + 0.40 * work["bound_score"] + 0.20 * work["v_score"]
    )
    return work.sort_values(
        [
            "ijds_balanced_score",
            "alpha01_realized_total_return",
            "alpha01_markov_loss_threshold",
        ],
        ascending=[False, False, True],
    ).iloc[0]


def _body_candidate(eligible: pd.DataFrame, *, markov_threshold: float) -> pd.Series:
    """Select the paper-body point from the exact finite-grid frontier.

    The body point is intentionally not the global max-return endpoint and not
    the minimum-bound endpoint. It is the highest-return policy below a declared
    exact Markov-loss threshold, which matches the paper-facing return-bound
    claim and remains valid for linear, capped and tail-focused policies.
    """
    under_threshold = _best_under_threshold(eligible, markov_threshold)
    if under_threshold is not None:
        return under_threshold
    return _score_body_candidate(eligible)


def _best_under_threshold(eligible: pd.DataFrame, threshold: float) -> pd.Series | None:
    candidates = eligible[eligible["alpha01_markov_loss_threshold"] <= threshold]
    if candidates.empty:
        return None
    return candidates.sort_values(
        ["alpha01_realized_total_return", "alpha01_markov_loss_threshold"],
        ascending=[False, True],
    ).iloc[0]


def _append_row(rows: list[dict[str, Any]], row: pd.Series | None, role: str) -> None:
    if row is None:
        return
    payload = _row_payload(row, role)
    key = (payload["role"], payload["semantic_policy_key"])
    existing = {(item["role"], item["semantic_policy_key"]) for item in rows}
    if key not in existing:
        rows.append(payload)


def _load_leaderboards(run_tags: list[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for run_tag in run_tags:
        path = _leaderboard_path(run_tag)
        bound_path = _bound_eval_path(run_tag)
        if not path.exists():
            raise FileNotFoundError(path)
        if not bound_path.exists():
            raise FileNotFoundError(bound_path)
        frame = pd.read_parquet(path)
        bound_eval = pd.read_parquet(bound_path)
        alpha01 = add_policy_aware_bound_columns(
            bound_eval[np.isclose(bound_eval["alpha"], 0.01)].copy()
        )
        alpha01_columns = {
            "gamma_internalized": "alpha01_gamma_internalized",
            "gamma_residual": "alpha01_gamma_residual",
            "weighted_pd_constraint_used": "alpha01_weighted_pd_constraint_used",
            "weighted_pd_high": "alpha01_weighted_pd_high",
            "weighted_pd_point": "alpha01_weighted_pd_point",
            "endpoint_budget": "alpha01_endpoint_budget",
            "endpoint_budget_upper": "alpha01_endpoint_budget_upper",
            "markov_loss_threshold": "alpha01_markov_loss_threshold",
            "markov_loss_cap": "alpha01_markov_loss_cap",
        }
        alpha01 = alpha01[["local_candidate_id", "semantic_policy_key", *alpha01_columns]].rename(
            columns=alpha01_columns
        )
        legacy_columns = {
            "alpha01_endpoint_budget_upper": "legacy_alpha01_endpoint_budget_upper",
            "alpha01_markov_loss_cap": "legacy_alpha01_markov_loss_cap",
        }
        frame = frame.rename(
            columns={
                source: target
                for source, target in legacy_columns.items()
                if source in frame.columns
            }
        )
        stale_columns = [
            column
            for column in alpha01_columns.values()
            if column in frame.columns and column not in legacy_columns.values()
        ]
        if stale_columns:
            frame = frame.drop(columns=stale_columns)
        frame = frame.merge(
            alpha01,
            on=["local_candidate_id", "semantic_policy_key"],
            how="left",
            validate="one_to_one",
        )
        if frame["alpha01_markov_loss_threshold"].isna().any():
            raise ValueError(f"Missing alpha=0.01 certificate rows for {run_tag}")
        frame["run_tag"] = run_tag
        frame["run_label"] = _short_run_label(run_tag)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def build_consolidated_frontier(run_tags: list[str], caps: list[float]) -> dict[str, Any]:
    raw = _load_leaderboards(run_tags)
    deduped = (
        raw.sort_values(
            [
                "semantic_policy_key",
                "alpha_exact_pass_count",
                "alpha01_realized_total_return",
                "alpha01_markov_loss_threshold",
            ],
            ascending=[True, False, False, True],
        )
        .drop_duplicates("semantic_policy_key", keep="first")
        .reset_index(drop=True)
    )
    eligible = _eligible(deduped)

    body = _body_candidate(eligible, markov_threshold=DEFAULT_BODY_MARKOV_THRESHOLD)
    semantics_audit: dict[str, Any] = {
        "status": "not_available",
        "selection_metric": "alpha01_markov_loss_threshold",
    }
    if "legacy_alpha01_markov_loss_cap" in deduped.columns:
        legacy = pd.to_numeric(deduped["legacy_alpha01_markov_loss_cap"], errors="coerce")
        exact = pd.to_numeric(deduped["alpha01_markov_loss_threshold"], errors="coerce")
        delta = exact - legacy
        tolerance = 1e-5
        legacy_eligible = eligible[eligible["legacy_alpha01_markov_loss_cap"] <= 0.35]
        legacy_body = legacy_eligible.sort_values(
            ["alpha01_realized_total_return", "legacy_alpha01_markov_loss_cap"],
            ascending=[False, True],
        ).iloc[0]
        semantics_audit = {
            "status": "corrected_from_existing_exact_bound_evaluations",
            "selection_metric": "alpha01_markov_loss_threshold",
            "legacy_metric": "tau + (1 - gamma) * Gamma_CP + sqrt(alpha)",
            "material_difference_tolerance": tolerance,
            "materially_changed_policies": int((delta.abs() > tolerance).sum()),
            "materially_understated_policies": int((delta > tolerance).sum()),
            "maximum_legacy_understatement": round(float(delta.max()), 9),
            "legacy_under_0_50_excluded_by_exact_threshold": int(
                ((legacy <= 0.50) & (exact > 0.50)).sum()
            ),
            "body_selection_unchanged": bool(
                str(legacy_body["semantic_policy_key"]) == str(body["semantic_policy_key"])
            ),
            "affected_policy_modes": sorted(
                deduped.loc[delta > tolerance, "policy_mode"].astype(str).unique().tolist()
            ),
        }
    rows: list[dict[str, Any]] = []
    _append_row(
        rows,
        eligible.sort_values("alpha01_markov_loss_threshold").iloc[0],
        "minimum Markov-threshold endpoint",
    )
    _append_row(rows, body, "body/default balanced return-bound point")
    _append_row(
        rows,
        eligible.sort_values(
            ["alpha01_weighted_miscoverage_V", "alpha01_realized_total_return"],
            ascending=[True, False],
        ).iloc[0],
        "lowest realized V return-bound point",
    )
    _append_row(
        rows,
        eligible.sort_values(
            ["alpha01_realized_total_return", "alpha01_markov_loss_threshold"],
            ascending=[False, True],
        ).iloc[0],
        "max-return economic endpoint",
    )
    for cap in caps:
        _append_row(
            rows,
            _best_under_threshold(eligible, cap),
            f"highest return under threshold<={cap:g}",
        )

    by_run = []
    for run_tag, run_df in raw.groupby("run_tag", sort=False):
        by_run.append(
            {
                "run_label": _short_run_label(str(run_tag)),
                "run_tag": str(run_tag),
                "rows": int(len(run_df)),
                "all_alpha_passers": int(
                    (run_df["alpha_exact_pass_count"] == run_df["alpha_exact_check_count"]).sum()
                ),
                "all_alpha_pass_rate": round(
                    float(
                        (
                            run_df["alpha_exact_pass_count"] == run_df["alpha_exact_check_count"]
                        ).mean()
                    ),
                    9,
                ),
                "best_return": round(float(run_df["alpha01_realized_total_return"].max()), 6),
                "min_markov_threshold": round(
                    float(run_df["alpha01_markov_loss_threshold"].min()), 9
                ),
            }
        )

    return {
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "source_run_tags": run_tags,
        "selection_rule": {
            "eligible": "all-alpha pass and nonnegative return_floor_surplus",
            "dedupe_key": "semantic_policy_key",
            "dedupe_semantics": (
                "duplicate semantic policies across refinement runs have identical metrics; "
                "one representative row is retained for the consolidated table"
            ),
            "body_selection": (
                f"highest realized return among eligible finite-grid policies with "
                f"exact Markov_threshold <= {DEFAULT_BODY_MARKOV_THRESHOLD:g}; "
                "falls back to the legacy "
                "balanced normalized return/bound/V score only if no eligible policy "
                "exists under that declared threshold"
            ),
            "bound_semantics": (
                "Markov_threshold = weighted endpoint budget B_u + sqrt(alpha); "
                "Markov_cap = tau + residual endpoint premium + solver slack + sqrt(alpha). "
                "The exact threshold drives selection."
            ),
            "caps": caps,
            "role_semantics": "finite-grid frontier roles, not continuous optima",
        },
        "counts": {
            "raw_rows": int(len(raw)),
            "deduped_semantic_policies": int(len(deduped)),
            "duplicate_rows_removed": int(len(raw) - len(deduped)),
            "eligible_all_alpha_return_floor_policies": int(len(eligible)),
            "nonpass_or_below_floor_policies": int(len(deduped) - len(eligible)),
        },
        "certificate_semantics_audit": semantics_audit,
        "by_run": by_run,
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-tag", default=DEFAULT_OUTPUT_TAG)
    parser.add_argument("--output", default="")
    parser.add_argument("--run-tag", action="append", dest="run_tags", default=[])
    parser.add_argument("--caps", default=",".join(str(cap) for cap in DEFAULT_CAPS))
    args = parser.parse_args(argv)

    run_tags = [str(tag) for tag in args.run_tags] or DEFAULT_RUN_TAGS
    caps = [float(part.strip()) for part in str(args.caps).split(",") if part.strip()]
    payload = build_consolidated_frontier(run_tags, caps)
    output = Path(args.output) if args.output else _output_path(str(args.output_tag))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
