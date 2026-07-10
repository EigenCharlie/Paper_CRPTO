"""Run portfolio optimization with conformal prediction uncertainty sets.

Usage:
    uv run python scripts/optimize_portfolio.py --risk_tolerance 0.05 --uncertainty_aversion 0.5
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from loguru import logger

from src.models.conformal_artifacts import load_conformal_intervals
from src.optimization.input_alignment import align_candidate_intervals
from src.optimization.portfolio_model import (
    optimize_portfolio_allocation,
    solution_allocation_vector,
)
from src.optimization.robust_opt import scenario_analysis
from src.utils.pipeline_runtime import (
    atomic_write_parquet,
    atomic_write_pickle,
    write_last_valid_artifact,
    write_runtime_checkpoint,
    write_runtime_status,
)
from src.utils.script_helpers import artifact_path


def _parse_percent_series(series: pd.Series) -> np.ndarray:
    """Parse Lending Club style percentages into decimals."""
    if pd.api.types.is_numeric_dtype(series):
        values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    else:
        values = (
            series.astype(str)
            .str.strip()
            .str.rstrip("%")
            .pipe(pd.to_numeric, errors="coerce")
            .to_numpy(dtype=float)
        )
    values = np.nan_to_num(values, nan=12.0)  # default annual rate (%)
    return values / 100.0


def _load_candidates() -> pd.DataFrame:
    """Load portfolio candidate pool, preferring feature-engineered data."""
    fe_path = Path("data/processed/test_fe.parquet")
    raw_path = Path("data/processed/test.parquet")
    if fe_path.exists():
        return pd.read_parquet(fe_path)
    return pd.read_parquet(raw_path)


def _load_interval_artifact() -> pd.DataFrame:
    """Load conformal interval artifact (canonical first)."""
    intervals, intervals_path, is_legacy = load_conformal_intervals()
    logger.info(
        f"Loaded conformal intervals from {intervals_path} "
        f"(legacy={is_legacy}, rows={len(intervals):,})"
    )
    return intervals.reset_index(drop=True)


def _resolve_interval_columns(intervals: pd.DataFrame) -> tuple[str, str, str]:
    col_point = "y_pred" if "y_pred" in intervals.columns else "pd_point"
    col_low = "pd_low_90" if "pd_low_90" in intervals.columns else "pd_low"
    col_high = "pd_high_90" if "pd_high_90" in intervals.columns else "pd_high"
    return col_point, col_low, col_high


def _align_candidates_and_intervals(
    candidates: pd.DataFrame,
    intervals: pd.DataFrame,
    max_candidates: int | None = 5_000,
    random_state: int = 42,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    """Align loans with PD intervals using ID when available, with legacy fallback."""
    aligned = align_candidate_intervals(
        candidates,
        intervals,
        max_candidates=max_candidates,
        random_state=random_state,
    )
    col_point, col_low, col_high = _resolve_interval_columns(aligned.intervals)
    if aligned.mode == "position":
        logger.warning(
            "Conformal interval artifact has no id or _row_number alignment key; "
            "using reproducible positional sampling for optimization."
        )
    logger.info(
        "Aligned candidates and intervals by {}: n={:,} "
        "(alignable_rows={:,}, candidate_rows={:,}, interval_rows={:,})",
        aligned.mode,
        aligned.selected_rows,
        aligned.available_rows,
        len(candidates),
        len(intervals),
    )
    return (
        aligned.candidates,
        aligned.intervals[col_point].to_numpy(dtype=float),
        aligned.intervals[col_low].to_numpy(dtype=float),
        aligned.intervals[col_high].to_numpy(dtype=float),
    )


def main(
    config_path: str = "configs/optimization.yaml",
    risk_tolerance: float = 0.10,
    uncertainty_aversion: float = 0.0,
    min_budget_utilization: float = 0.0,
    pd_cap_slack_penalty: float = 0.0,
    max_candidates: int | None = 5_000,
    random_state: int = 42,
    solver_backend: str | None = None,
):
    stage_name = "portfolio_optimization"
    write_runtime_status(stage_name, phase="loading_inputs", state="running")
    with open(config_path) as f:
        config = yaml.safe_load(f)

    test = _load_candidates()
    intervals = _load_interval_artifact()
    test_sample, pd_point, pd_low, pd_high = _align_candidates_and_intervals(
        test, intervals, max_candidates=max_candidates, random_state=random_state
    )
    n = len(test_sample)
    write_runtime_checkpoint(
        stage_name,
        "candidate_pool_prepared",
        {
            "candidate_rows_available": len(test),
            "interval_rows_available": len(intervals),
            "candidate_rows_used": int(n),
            "max_candidates_requested": None
            if max_candidates is None or int(max_candidates) <= 0
            else int(max_candidates),
        },
    )

    lgd = np.full(n, 0.45)
    if "int_rate" in test_sample.columns:
        int_rates = _parse_percent_series(test_sample["int_rate"])
    else:
        int_rates = np.full(n, 0.12)

    write_runtime_status(stage_name, phase="solving_portfolio", state="running")
    solution = optimize_portfolio_allocation(
        loans=test_sample,
        pd_point=pd_point,
        pd_low=pd_low,
        pd_high=pd_high,
        lgd=lgd,
        int_rates=int_rates,
        total_budget=config["portfolio"]["total_budget"],
        max_concentration=config["portfolio"]["max_concentration"],
        max_portfolio_pd=risk_tolerance,
        robust=config["portfolio"]["robust"],
        uncertainty_aversion=uncertainty_aversion,
        min_budget_utilization=min_budget_utilization,
        pd_cap_slack_penalty=pd_cap_slack_penalty,
        time_limit=config["optimization"]["time_limit"],
        threads=config["optimization"]["threads"],
        solver_backend=solver_backend or config.get("optimization", {}).get("solver", "highs"),
    )
    write_runtime_status(stage_name, phase="optimization_complete", state="running")

    allocation = solution_allocation_vector(solution, n)
    loan_amounts = (
        test_sample["loan_amnt"].to_numpy(dtype=float)
        if "loan_amnt" in test_sample.columns
        else np.ones(n, dtype=float) * 10_000
    )
    scenarios = scenario_analysis(allocation, loan_amounts, pd_low, pd_point, pd_high, lgd)

    logger.info(f"Optimization complete: {solution['solver_status']}")
    logger.info(f"Objective value: {solution['objective_value']:,.2f}")
    logger.info(f"Scenarios:\n{scenarios}")

    # Persist artifacts for downstream reporting.
    model_dir = artifact_path("models")
    data_dir = artifact_path("data/processed")
    model_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    atomic_write_pickle(
        model_dir / "portfolio_results.pkl",
        {
            "solution": solution,
            "scenario_analysis": scenarios.to_dict(orient="records")[0],
            "n_candidates": n,
            "risk_tolerance": risk_tolerance,
            "uncertainty_aversion": uncertainty_aversion,
            "min_budget_utilization": min_budget_utilization,
            "pd_cap_slack_penalty": pd_cap_slack_penalty,
            "n_candidates_available": int(min(len(test), len(intervals))),
            "n_candidates_used": int(n),
            "max_candidates_requested": None
            if max_candidates is None or int(max_candidates) <= 0
            else int(max_candidates),
            "dataset_scope": "full_candidates"
            if max_candidates is None or int(max_candidates) <= 0
            else "sampled_candidates",
            "solver_backend_requested": solver_backend
            or config.get("optimization", {}).get("solver", "highs"),
        },
    )

    alloc_df = pd.DataFrame(
        {
            "loan_idx": np.arange(n),
            "alloc": allocation,
            "loan_amnt": loan_amounts,
            "pd_point": pd_point,
            "pd_low": pd_low,
            "pd_high": pd_high,
            "int_rate": int_rates,
        }
    )
    atomic_write_parquet(alloc_df, data_dir / "portfolio_allocations.parquet", index=False)
    write_last_valid_artifact(
        stage_name,
        artifact_key="portfolio_allocations",
        artifact_path=data_dir / "portfolio_allocations.parquet",
        extra={
            "solver_status": str(solution["solver_status"]),
            "n_candidates_used": int(n),
            "objective_value": float(solution["objective_value"]),
        },
    )
    write_runtime_status(
        stage_name,
        phase="completed",
        state="completed",
        extra={
            "portfolio_results_path": str(model_dir / "portfolio_results.pkl"),
            "portfolio_allocations_path": str(data_dir / "portfolio_allocations.parquet"),
            "solver_status": str(solution["solver_status"]),
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/optimization.yaml")
    parser.add_argument("--risk_tolerance", type=float, default=0.10)
    parser.add_argument("--uncertainty_aversion", type=float, default=0.0)
    parser.add_argument("--min_budget_utilization", type=float, default=0.0)
    parser.add_argument("--pd_cap_slack_penalty", type=float, default=0.0)
    parser.add_argument("--max_candidates", type=int, default=5_000)
    parser.add_argument("--random_state", type=int, default=42)
    parser.add_argument("--solver_backend", choices=["highs", "cuopt"], default=None)
    args = parser.parse_args()
    main(
        args.config,
        args.risk_tolerance,
        args.uncertainty_aversion,
        args.min_budget_utilization,
        args.pd_cap_slack_penalty,
        args.max_candidates,
        args.random_state,
        args.solver_backend,
    )
