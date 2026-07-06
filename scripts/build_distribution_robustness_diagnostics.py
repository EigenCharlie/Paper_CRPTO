"""Build the P2 distribution-robustness diagnostics (Tables A23 and A24).

These close the two remaining P2 roadmap items that do NOT require reopening the
frozen champion search, using only the frozen Mondrian conformal intervals:

* A23 -- Multi-distribution coverage robustness (MDCP / group-weighted spirit,
  [@yang2026multidistribution; @bhattacharyya2026groupweighted]). Reports the
  worst-case one-/two-sided coverage across grade groups and grade x vintage
  cells, i.e. whether the 90% guarantee survives when an unknown test-time group
  or source distribution dominates.

* A24 -- Online conformal stability over the OOT vintage sequence (ACI,
  [@gibbs2021aci; @angelopoulos2025gradient; @liu2026portfolio]). Reports
  per-vintage coverage, the cumulative ("streaming") coverage, and the adaptive
  conformal inference (ACI) target trajectory ``alpha_t`` that an online
  controller would follow. The OOT dataset is static, so this is a diagnostic of
  how hard an online controller would have to work, not a streaming validation.

The script reads only ``data/processed/conformal_intervals_mondrian.parquet``
(a frozen artifact) and writes journal-only tables. It does not touch the
champion or any optimization artifact.

Usage::

    uv run python scripts/build_distribution_robustness_diagnostics.py
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from src.utils.script_helpers import write_json, write_table

ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "reports" / "crpto" / "tables"
MODEL_DIR = ROOT / "models"
INTERVALS_PATH = ROOT / "data" / "processed" / "conformal_intervals_mondrian.parquet"
STATUS_PATH = MODEL_DIR / "crpto_distribution_robustness_status.json"

TABLE_A23_NAME = "crpto_tableA23_multidistribution_robustness"
TABLE_A24_NAME = "crpto_tableA24_online_conformal_stability"

TARGET_COVERAGE = 0.90
TARGET_ALPHA = 1.0 - TARGET_COVERAGE
ACI_STEP = 0.05  # Gibbs-Candes learning rate gamma.
EPS = 1e-9


def _load_intervals() -> pd.DataFrame:
    df = pd.read_parquet(INTERVALS_PATH)
    df = df.copy()
    df["period"] = df["temporal_segment"].astype(str).str.split("vintage=").str[-1]
    df["y_true"] = pd.to_numeric(df["y_true"], errors="coerce").astype(float)
    df["covered_90"] = (
        (df["pd_low_90"] - EPS <= df["y_true"]) & (df["y_true"] <= df["pd_high_90"] + EPS)
    ).astype(float)
    df["width_90"] = (df["pd_high_90"] - df["pd_low_90"]).astype(float)
    logger.info(
        "Loaded {} conformal intervals ({} periods, {} grades)",
        len(df),
        df["period"].nunique(),
        df["grade"].nunique(),
    )
    return df


def _slice_coverage(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    grouped = df.groupby(columns, dropna=False)
    out = grouped.agg(
        n=("y_true", "size"),
        coverage_90=("covered_90", "mean"),
        default_rate=("y_true", "mean"),
        mean_width_90=("width_90", "mean"),
    ).reset_index()
    return out


def _build_a23(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    marginal = float(df["covered_90"].mean())
    by_grade = _slice_coverage(df, ["grade"]).sort_values("grade")
    by_period = _slice_coverage(df, ["period"])
    by_cell = _slice_coverage(df, ["grade", "period"])

    rows: list[dict[str, Any]] = [
        {
            "slice_type": "marginal",
            "slice": "all",
            "n": int(len(df)),
            "coverage_90": marginal,
            "default_rate": float(df["y_true"].mean()),
            "mean_width_90": float(df["width_90"].mean()),
            "robust_gap_vs_target": max(0.0, TARGET_COVERAGE - marginal),
            "meets_target_90": bool(marginal >= TARGET_COVERAGE),
        }
    ]
    for _, r in by_grade.iterrows():
        rows.append(
            {
                "slice_type": "grade",
                "slice": str(r["grade"]),
                "n": int(r["n"]),
                "coverage_90": float(r["coverage_90"]),
                "default_rate": float(r["default_rate"]),
                "mean_width_90": float(r["mean_width_90"]),
                "robust_gap_vs_target": max(0.0, TARGET_COVERAGE - float(r["coverage_90"])),
                "meets_target_90": bool(float(r["coverage_90"]) >= TARGET_COVERAGE),
            }
        )
    # Worst grade x vintage cell with non-trivial support (unknown-group stress).
    by_cell_supported = by_cell.loc[by_cell["n"] >= 200]
    worst_cell = by_cell_supported.sort_values("coverage_90").iloc[0]
    rows.append(
        {
            "slice_type": "worst_grade_x_period_cell",
            "slice": f"{worst_cell['grade']}|{worst_cell['period']}",
            "n": int(worst_cell["n"]),
            "coverage_90": float(worst_cell["coverage_90"]),
            "default_rate": float(worst_cell["default_rate"]),
            "mean_width_90": float(worst_cell["mean_width_90"]),
            "robust_gap_vs_target": max(0.0, TARGET_COVERAGE - float(worst_cell["coverage_90"])),
            "meets_target_90": bool(float(worst_cell["coverage_90"]) >= TARGET_COVERAGE),
        }
    )
    frame = pd.DataFrame(rows)

    worst_grade = by_grade.sort_values("coverage_90").iloc[0]
    worst_period = by_period.sort_values("coverage_90").iloc[0]
    summary = {
        "marginal_coverage_90": marginal,
        "min_grade_coverage_90": float(worst_grade["coverage_90"]),
        "worst_grade": str(worst_grade["grade"]),
        "min_period_coverage_90": float(worst_period["coverage_90"]),
        "worst_period": str(worst_period["period"]),
        "min_grade_period_cell_coverage_90": float(worst_cell["coverage_90"]),
        "worst_grade_period_cell": f"{worst_cell['grade']}|{worst_cell['period']}",
        "robust_coverage_gap": max(0.0, TARGET_COVERAGE - float(worst_cell["coverage_90"])),
        "all_grades_meet_target": bool((by_grade["coverage_90"] >= TARGET_COVERAGE).all()),
        "all_supported_cells_meet_target": bool(
            (by_cell_supported["coverage_90"] >= TARGET_COVERAGE).all()
        ),
        "n_supported_cells": int(len(by_cell_supported)),
    }
    return frame, summary


def _build_a24(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    by_period = _slice_coverage(df, ["period"]).sort_values("period").reset_index(drop=True)
    rows: list[dict[str, Any]] = []
    cum_n = 0.0
    cum_cov = 0.0
    alpha_t = TARGET_ALPHA  # ACI controller target before the first vintage.
    for _, r in by_period.iterrows():
        n = int(r["n"])
        cov = float(r["coverage_90"])
        miscov = 1.0 - cov
        cum_n += n
        cum_cov += cov * n
        rows.append(
            {
                "period": str(r["period"]),
                "n": n,
                "default_rate": float(r["default_rate"]),
                "coverage_90": cov,
                "miscoverage_90": miscov,
                "mean_width_90": float(r["mean_width_90"]),
                "cumulative_coverage_90": cum_cov / max(cum_n, 1.0),
                "aci_alpha_target_before": alpha_t,
            }
        )
        # Gibbs-Candes ACI update on the realized vintage miscoverage.
        alpha_t = float(np.clip(alpha_t + ACI_STEP * (TARGET_ALPHA - miscov), 0.0, 1.0))
    frame = pd.DataFrame(rows)
    alpha_traj = frame["aci_alpha_target_before"].to_numpy(dtype=float)
    summary = {
        "n_periods": int(len(frame)),
        "first_period": str(frame["period"].iloc[0]),
        "last_period": str(frame["period"].iloc[-1]),
        "min_period_coverage_90": float(frame["coverage_90"].min()),
        "max_period_coverage_90": float(frame["coverage_90"].max()),
        "final_cumulative_coverage_90": float(frame["cumulative_coverage_90"].iloc[-1]),
        "all_periods_meet_target": bool((frame["coverage_90"] >= TARGET_COVERAGE).all()),
        "aci_step_gamma": ACI_STEP,
        "aci_alpha_target_max_abs_deviation": float(np.max(np.abs(alpha_traj - TARGET_ALPHA))),
        "default_rate_first": float(frame["default_rate"].iloc[0]),
        "default_rate_last": float(frame["default_rate"].iloc[-1]),
    }
    return frame, summary


def build_distribution_robustness_diagnostics() -> dict[str, Any]:
    start = datetime.now(tz=UTC)
    df = _load_intervals()
    a23, a23_summary = _build_a23(df)
    a24, a24_summary = _build_a24(df)
    artifacts = write_table(
        TABLE_A23_NAME, a23, table_dir=TABLE_DIR, root=ROOT, float_precision=4
    ) + write_table(TABLE_A24_NAME, a24, table_dir=TABLE_DIR, root=ROOT, float_precision=4)
    status = {
        "schema_version": "2026-05-28.1",
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "elapsed_sec": (datetime.now(tz=UTC) - start).total_seconds(),
        "target_coverage_90": TARGET_COVERAGE,
        "source_intervals": str(INTERVALS_PATH.relative_to(ROOT)).replace("\\", "/"),
        "generated_artifacts": [str(p.relative_to(ROOT)).replace("\\", "/") for p in artifacts],
        "multidistribution_robustness": a23_summary,
        "online_conformal_stability": a24_summary,
        "champion_promotion_changed": False,
        "notes": [
            "Read-only diagnostics on frozen Mondrian conformal intervals.",
            "A23 stresses coverage across unknown groups (grade, grade x vintage).",
            "A24 is a static-OOT online-control diagnostic, not streaming validation.",
        ],
    }
    write_json(STATUS_PATH, status)
    logger.info("Wrote {}", STATUS_PATH.relative_to(ROOT))
    logger.info(
        "A23 worst grade={} cov={:.4f}; worst cell={} cov={:.4f}",
        a23_summary["worst_grade"],
        a23_summary["min_grade_coverage_90"],
        a23_summary["worst_grade_period_cell"],
        a23_summary["min_grade_period_cell_coverage_90"],
    )
    logger.info(
        "A24 periods={} min_cov={:.4f} final_cum_cov={:.4f} aci_alpha_max_dev={:.4f}",
        a24_summary["n_periods"],
        a24_summary["min_period_coverage_90"],
        a24_summary["final_cumulative_coverage_90"],
        a24_summary["aci_alpha_target_max_abs_deviation"],
    )
    return status


def main() -> int:
    build_distribution_robustness_diagnostics()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
