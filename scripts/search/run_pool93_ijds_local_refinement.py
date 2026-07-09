"""Local exact refinement of pool93 portfolio claims for IJDS.

This stage starts from the exact pool93 surface and searches a dense local
neighborhood around three paper-facing policies:

* max-return policy (rank 96),
* low-bound policy above the declared return floor (rank 219),
* low-miscoverage policy with stronger return (rank 223).

Unlike the broad frontier search, this runner ranks policies using metrics
computed from the exact full-universe allocation itself.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.optimize_portfolio_tradeoff import _parse_percent_series  # noqa: E402
from scripts.search.run_portfolio_bound_aware_search import (  # noqa: E402
    SCHEMA_VERSION,
    SEMANTIC_POLICY_FIELDS,
    _policy_semantic_key,
)
from scripts.validate_alpha_gamma_bound import (  # noqa: E402
    DEFAULT_LGD,
    DEFAULT_MAX_CONCENTRATION,
    DEFAULT_T_EVAL,
    DEFAULT_TIME_LIMIT,
    _compute_effective_pd_vector,
    _compute_intervals_at_alpha,
    _load_aligned_dataset,
)
from src.optimization.certificate_semantics import (  # noqa: E402
    IJDS_DECLARED_ALPHA_GRID,
    add_policy_aware_bound_columns,
    compute_funded_certificate_metrics,
)
from src.optimization.portfolio_model import (  # noqa: E402
    optimize_portfolio_allocation,
    solution_allocation_vector,
)
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    write_runtime_checkpoint,
    write_runtime_status,
)

STAGE_NAME = "pool93_ijds_local_refinement"
DECLARED_RETURN_FLOOR = 170464.54
DEFAULT_ALPHA_GRID = list(IJDS_DECLARED_ALPHA_GRID)
VALID_PROFILES = {
    "stage1",
    "expanded",
    "claim_expanded",
    "claim_micro",
    "claim_micro_ext",
    "claim_bound_closure",
    "claim_bound_floor_closure",
    "claim_bound_terminal",
}
ANCHOR_REASONS = (
    (96, "source_exact_max_return"),
    (219, "source_low_gamma_cp_return_floor"),
    (223, "source_low_weighted_miscoverage_high_return"),
)
CLAIM_ROW_FIELDS = (
    "claim_rank",
    "local_candidate_id",
    "local_family",
    "anchor_rank",
    "source_reason",
    "risk_tolerance",
    "policy_mode",
    "gamma",
    "delta_cap_quantile",
    "tail_focus_quantile",
    "uncertainty_aversion",
    "alpha01_realized_total_return",
    "return_floor_surplus",
    "alpha01_gamma_cp",
    "alpha01_gamma_internalized",
    "alpha01_gamma_residual",
    "alpha01_weighted_miscoverage_V",
    "alpha01_endpoint_budget",
    "alpha01_endpoint_budget_upper",
    "alpha01_markov_loss_threshold",
    "alpha01_markov_loss_cap",
    "alpha01_weighted_pd_true",
    "alpha01_empirical_coverage_funded",
    "alpha_exact_pass_count",
    "alpha_exact_check_count",
    "alpha_mean_gamma_cp",
    "alpha_mean_weighted_miscoverage_V",
    "return_score",
    "bound_score",
    "v_score",
    "ijds_balanced_score",
    "n_funded_mean",
    "allocator_backends",
)
DEFAULT_SOURCE_BOUND_EVAL = (
    ROOT / "data/processed/experiments/champion_reopen/"
    "champion-reopen-2026-06-19__hpo-wave1__pool93__portfolio-stage1-fast1-claim-26-06/"
    "portfolio/portfolio_bound_aware_bound_eval_highspy.parquet"
)
DEFAULT_SOURCE_SELECTION = (
    ROOT / "models/experiments/champion_reopen/"
    "champion-reopen-2026-06-19__hpo-wave1__pool93__portfolio-stage1-fast1-claim-26-06/"
    "portfolio/portfolio_bound_aware_selection_highspy.json"
)


@dataclass(frozen=True)
class Pool93Paths:
    output_dir: Path
    model_dir: Path
    checkpoint_dir: Path
    status_path: Path
    candidates_path: Path
    bound_eval_path: Path
    leaderboard_path: Path
    claim_summary_path: Path
    manifest_path: Path


_WORKER_ALIGNED: pd.DataFrame | None = None


def _init_exact_worker(aligned: pd.DataFrame) -> None:
    global _WORKER_ALIGNED
    _WORKER_ALIGNED = aligned


def _exact_policy_alpha_task(
    candidate: dict[str, Any],
    alpha: float,
    budget: float,
    t_eval: float,
    threads: int,
) -> dict[str, Any]:
    if _WORKER_ALIGNED is None:
        raise RuntimeError("Exact-refinement worker was not initialized.")
    policy = {field: candidate[field] for field in SEMANTIC_POLICY_FIELDS}
    result = _exact_policy_alpha(
        _WORKER_ALIGNED,
        policy=policy,
        alpha=float(alpha),
        budget=float(budget),
        t_eval=float(t_eval),
        threads=max(1, int(threads)),
    )
    return {**candidate, **result}


def _coerce_float_grid(raw: str | None, fallback: list[float]) -> list[float]:
    if not raw:
        return list(fallback)
    values = [float(part.strip()) for part in str(raw).split(",") if part.strip()]
    return values or list(fallback)


def _coerce_int_grid(raw: str | None, fallback: list[int]) -> list[int]:
    if not raw:
        return list(fallback)
    values = [int(part.strip()) for part in str(raw).split(",") if part.strip()]
    return values or list(fallback)


def _round_grid(
    values: list[float], *, lo: float | None = None, hi: float | None = None
) -> list[float]:
    clean: set[float] = set()
    for value in values:
        v = float(value)
        if lo is not None:
            v = max(float(lo), v)
        if hi is not None:
            v = min(float(hi), v)
        clean.add(round(v, 6))
    return sorted(clean)


def _source_anchor_rows(source_bound_eval: Path, anchor_ranks: list[int]) -> pd.DataFrame:
    df = pd.read_parquet(source_bound_eval)
    if "alpha" in df.columns:
        df = df[np.isclose(pd.to_numeric(df["alpha"], errors="coerce"), 0.01)].copy()
    anchors = df[df["candidate_rank"].astype(int).isin(anchor_ranks)].copy()
    if anchors.empty:
        raise ValueError(f"No anchor ranks found in {source_bound_eval}: {anchor_ranks}")
    anchors = anchors.drop_duplicates("candidate_rank", keep="first")
    missing = sorted(set(anchor_ranks) - set(anchors["candidate_rank"].astype(int)))
    if missing:
        raise ValueError(f"Missing anchor ranks in {source_bound_eval}: {missing}")
    return anchors.reset_index(drop=True)


def _policy_base(
    *,
    risk_tolerance: float,
    policy_mode: str,
    gamma: float,
    uncertainty_aversion: float,
    delta_cap_quantile: float = 1.0,
    tail_focus_quantile: float = 1.0,
    min_budget_utilization: float = 0.0,
    pd_cap_slack_penalty: float = 0.0,
    solver_backend: str = "highspy",
) -> dict[str, Any]:
    return {
        "risk_tolerance": round(float(risk_tolerance), 6),
        "policy_mode": str(policy_mode),
        "gamma": round(float(gamma), 6),
        "delta_cap_quantile": round(float(delta_cap_quantile), 6),
        "tail_focus_quantile": round(float(tail_focus_quantile), 6),
        "uncertainty_aversion": round(float(uncertainty_aversion), 6),
        "min_budget_utilization": round(float(min_budget_utilization), 6),
        "pd_cap_slack_penalty": round(float(pd_cap_slack_penalty), 6),
        "solver_backend": str(solver_backend),
    }


def _add_candidate(
    rows: list[dict[str, Any]],
    seen: set[str],
    *,
    family: str,
    anchor_rank: int,
    source_reason: str,
    policy: dict[str, Any],
) -> None:
    key = _policy_semantic_key(policy)
    if key in seen:
        return
    payload = dict(policy)
    payload["semantic_policy_key"] = key
    payload["local_family"] = family
    payload["anchor_rank"] = int(anchor_rank)
    payload["source_reason"] = str(source_reason)
    rows.append(payload)
    seen.add(key)


def _candidate_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    candidates = pd.DataFrame(rows).reset_index(drop=True)
    candidates.insert(0, "local_candidate_id", np.arange(1, len(candidates) + 1, dtype=int))
    return candidates


def _anchor_policy(
    anchor_by_rank: dict[int, dict[str, Any]],
    rank: int,
    *,
    solver_backend: str,
) -> dict[str, Any]:
    row = anchor_by_rank[rank]
    return _policy_base(
        risk_tolerance=float(row["risk_tolerance"]),
        policy_mode=str(row["policy_mode"]),
        gamma=float(row["gamma"]),
        uncertainty_aversion=float(row["uncertainty_aversion"]),
        delta_cap_quantile=float(row["delta_cap_quantile"]),
        tail_focus_quantile=float(row["tail_focus_quantile"]),
        min_budget_utilization=float(row["min_budget_utilization"]),
        pd_cap_slack_penalty=float(row["pd_cap_slack_penalty"]),
        solver_backend=solver_backend,
    )


def _add_anchor_candidates(
    rows: list[dict[str, Any]],
    seen: set[str],
    *,
    anchor_by_rank: dict[int, dict[str, Any]],
    solver_backend: str,
) -> None:
    for rank, reason in ANCHOR_REASONS:
        if rank in anchor_by_rank:
            _add_candidate(
                rows,
                seen,
                family="anchor_policy",
                anchor_rank=rank,
                source_reason=reason,
                policy=_anchor_policy(anchor_by_rank, rank, solver_backend=solver_backend),
            )


def _capped_delta_values(mode: str, capped_values: tuple[float, ...]) -> tuple[float, ...]:
    return (1.0,) if mode == "blended_uncertainty" else capped_values


def _add_blended_grid(
    rows: list[dict[str, Any]],
    seen: set[str],
    *,
    family: str,
    anchor_rank: int,
    source_reason: str,
    risks: list[float],
    gammas: list[float],
    aversions: list[float],
    solver_backend: str,
    capped_delta_values: tuple[float, ...] = (0.95, 1.0),
) -> None:
    for risk, gamma, aversion, mode in product(
        risks,
        gammas,
        aversions,
        ["blended_uncertainty", "capped_blended_uncertainty"],
    ):
        for delta_cap in _capped_delta_values(str(mode), capped_delta_values):
            _add_candidate(
                rows,
                seen,
                family=family,
                anchor_rank=anchor_rank,
                source_reason=source_reason,
                policy=_policy_base(
                    risk_tolerance=risk,
                    policy_mode=str(mode),
                    gamma=gamma,
                    uncertainty_aversion=aversion,
                    delta_cap_quantile=delta_cap,
                    solver_backend=solver_backend,
                ),
            )


def _add_tail_grid(
    rows: list[dict[str, Any]],
    seen: set[str],
    *,
    family: str,
    anchor_rank: int,
    source_reason: str,
    risks: list[float],
    gammas: list[float],
    aversions: list[float],
    tail_focus_values: list[float],
    solver_backend: str,
) -> None:
    for risk, gamma, aversion, tail_focus in product(
        risks,
        gammas,
        aversions,
        tail_focus_values,
    ):
        _add_candidate(
            rows,
            seen,
            family=family,
            anchor_rank=anchor_rank,
            source_reason=source_reason,
            policy=_policy_base(
                risk_tolerance=risk,
                policy_mode="tail_blended_uncertainty",
                gamma=gamma,
                uncertainty_aversion=aversion,
                tail_focus_quantile=tail_focus,
                solver_backend=solver_backend,
            ),
        )


def _append_claim_micro_candidates(
    rows: list[dict[str, Any]], seen: set[str], *, solver_backend: str
) -> None:
    _add_blended_grid(
        rows,
        seen,
        family="claim_micro_body_low_v",
        anchor_rank=219,
        source_reason="candidate1665_1667_body_default_micro",
        risks=_round_grid([0.1715 + 0.00025 * idx for idx in range(5)], lo=0.14, hi=0.24),
        gammas=_round_grid([0.545 + 0.005 * idx for idx in range(7)], lo=0.0, hi=1.0),
        aversions=[0.0, 0.0125, 0.025, 0.0375, 0.05, 0.0625, 0.075, 0.10],
        capped_delta_values=(0.95, 1.0),
        solver_backend=solver_backend,
    )
    _add_blended_grid(
        rows,
        seen,
        family="claim_micro_bound_tight",
        anchor_rank=219,
        source_reason="candidate1206_tight_cap_micro",
        risks=_round_grid([0.1700 + 0.00025 * idx for idx in range(5)], lo=0.14, hi=0.24),
        gammas=_round_grid([0.575 + 0.005 * idx for idx in range(6)], lo=0.0, hi=1.0),
        aversions=[0.15, 0.1625, 0.175, 0.1875, 0.20, 0.225],
        capped_delta_values=(0.95, 1.0),
        solver_backend=solver_backend,
    )
    _add_blended_grid(
        rows,
        seen,
        family="claim_micro_high_return_cap036",
        anchor_rank=219,
        source_reason="candidate1922_return_cap036_micro",
        risks=_round_grid([0.1725 + 0.00025 * idx for idx in range(7)], lo=0.14, hi=0.24),
        gammas=_round_grid([0.500 + 0.005 * idx for idx in range(6)], lo=0.0, hi=1.0),
        aversions=[0.05, 0.0625, 0.075, 0.0875, 0.10],
        capped_delta_values=(0.95, 1.0),
        solver_backend=solver_backend,
    )
    _add_tail_grid(
        rows,
        seen,
        family="claim_micro_economic_endpoint",
        anchor_rank=96,
        source_reason="candidate2777_2857_economic_endpoint_micro",
        risks=_round_grid([0.1565 + 0.00025 * idx for idx in range(9)], lo=0.12, hi=0.22),
        gammas=_round_grid([0.44 + 0.005 * idx for idx in range(13)], lo=0.0, hi=1.0),
        aversions=[0.1125, 0.125, 0.1375, 0.15],
        tail_focus_values=[0.95, 1.0],
        solver_backend=solver_backend,
    )


def _append_claim_micro_ext_candidates(
    rows: list[dict[str, Any]], seen: set[str], *, solver_backend: str
) -> None:
    _add_blended_grid(
        rows,
        seen,
        family="claim_micro_ext_body_cap345",
        anchor_rank=219,
        source_reason="candidate37_205_body_cap345_extension",
        risks=_round_grid([0.17125 + 0.000125 * idx for idx in range(11)], lo=0.14, hi=0.24),
        gammas=_round_grid([0.5475, 0.55, 0.5525, 0.555, 0.5575], lo=0.0, hi=1.0),
        aversions=[0.025, 0.0375, 0.05, 0.0625],
        capped_delta_values=(0.975, 1.0),
        solver_backend=solver_backend,
    )
    _add_blended_grid(
        rows,
        seen,
        family="claim_micro_ext_bound_tight",
        anchor_rank=219,
        source_reason="candidate949_bound_tight_extension",
        risks=_round_grid([0.1690 + 0.00025 * idx for idx in range(8)], lo=0.14, hi=0.24),
        gammas=_round_grid([0.600 + 0.005 * idx for idx in range(11)], lo=0.0, hi=1.0),
        aversions=[0.2125, 0.225, 0.2375, 0.25, 0.2625, 0.275],
        capped_delta_values=(0.95, 1.0),
        solver_backend=solver_backend,
    )
    _add_blended_grid(
        rows,
        seen,
        family="claim_micro_ext_cap036_return",
        anchor_rank=219,
        source_reason="candidate1975_cap036_return_extension",
        risks=_round_grid([0.17375 + 0.00025 * idx for idx in range(10)], lo=0.14, hi=0.24),
        gammas=_round_grid([0.505 + 0.0025 * idx for idx in range(9)], lo=0.0, hi=1.0),
        aversions=[0.0625, 0.075, 0.0875, 0.10],
        capped_delta_values=(0.95, 1.0),
        solver_backend=solver_backend,
    )
    _add_tail_grid(
        rows,
        seen,
        family="claim_micro_ext_economic_endpoint",
        anchor_rank=96,
        source_reason="candidate2122_economic_endpoint_extension",
        risks=_round_grid([0.15625 + 0.000125 * idx for idx in range(9)], lo=0.12, hi=0.22),
        gammas=_round_grid([0.400 + 0.005 * idx for idx in range(10)], lo=0.0, hi=1.0),
        aversions=[0.125, 0.1375, 0.15],
        tail_focus_values=[0.90, 0.925, 0.95, 1.0],
        solver_backend=solver_backend,
    )


def _append_bound_closure_candidates(
    rows: list[dict[str, Any]],
    seen: set[str],
    *,
    profile: str,
    solver_backend: str,
) -> None:
    if profile == "claim_bound_closure":
        _add_blended_grid(
            rows,
            seen,
            family="claim_bound_closure_low_cap",
            anchor_rank=219,
            source_reason="micro_ext_min_markov_cap_endpoint_closure",
            risks=_round_grid([0.1685 + 0.00025 * idx for idx in range(10)], lo=0.14, hi=0.24),
            gammas=_round_grid([0.65 + 0.01 * idx for idx in range(11)], lo=0.0, hi=1.0),
            aversions=[0.25, 0.275, 0.30, 0.325, 0.35],
            capped_delta_values=(0.95, 1.0),
            solver_backend=solver_backend,
        )
        return
    if profile == "claim_bound_floor_closure":
        _add_blended_grid(
            rows,
            seen,
            family="claim_bound_floor_closure_low_cap",
            anchor_rank=219,
            source_reason="bound_closure_cap029_floor_threshold",
            risks=_round_grid([0.16775 + 0.000125 * idx for idx in range(13)], lo=0.14, hi=0.24),
            gammas=_round_grid([0.75 + 0.01 * idx for idx in range(10)], lo=0.0, hi=1.0),
            aversions=[0.325, 0.35, 0.375, 0.40, 0.425, 0.45],
            capped_delta_values=(0.95, 1.0),
            solver_backend=solver_backend,
        )


def _append_bound_terminal_candidates(
    rows: list[dict[str, Any]], seen: set[str], *, solver_backend: str
) -> None:
    _add_blended_grid(
        rows,
        seen,
        family="claim_bound_terminal_ultra_low_cap",
        anchor_rank=219,
        source_reason="terminal_cap_threshold_search",
        risks=_round_grid([0.16675 + 0.000125 * idx for idx in range(29)], lo=0.14, hi=0.24),
        gammas=_round_grid([0.84 + 0.005 * idx for idx in range(31)], lo=0.0, hi=1.0),
        aversions=[0.40, 0.425, 0.45, 0.475, 0.50, 0.55, 0.60, 0.65, 0.70],
        capped_delta_values=(0.95, 1.0),
        solver_backend=solver_backend,
    )
    _add_blended_grid(
        rows,
        seen,
        family="claim_bound_terminal_return_recovery",
        anchor_rank=219,
        source_reason="terminal_best_return_under_low_cap",
        risks=_round_grid([0.1680 + 0.000125 * idx for idx in range(29)], lo=0.14, hi=0.24),
        gammas=_round_grid([0.80 + 0.005 * idx for idx in range(25)], lo=0.0, hi=1.0),
        aversions=[0.35, 0.375, 0.40, 0.425, 0.45, 0.475, 0.50, 0.55, 0.60],
        capped_delta_values=(0.95, 1.0),
        solver_backend=solver_backend,
    )


def _append_max_return_neighborhood(
    rows: list[dict[str, Any]],
    seen: set[str],
    *,
    anchor_by_rank: dict[int, dict[str, Any]],
    profile: str,
    solver_backend: str,
) -> None:
    if 96 not in anchor_by_rank:
        return
    base = anchor_by_rank[96]
    risk_offsets = [-0.004, -0.002, -0.001, 0.0, 0.001, 0.002, 0.004]
    gamma_offsets = [-0.05, -0.025, -0.01, 0.0, 0.01, 0.025, 0.05]
    aversions = [0.05, 0.075, 0.10, 0.125, 0.15]
    if profile == "expanded":
        risk_offsets = [
            -0.006,
            -0.004,
            -0.003,
            -0.002,
            -0.001,
            0.0,
            0.001,
            0.002,
            0.003,
            0.004,
            0.006,
        ]
        gamma_offsets = [-0.075, -0.05, -0.035, -0.025, -0.01, 0.0, 0.01, 0.025, 0.035, 0.05, 0.075]
        aversions = [0.025, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20]
    risks = _round_grid([float(base["risk_tolerance"]) + x for x in risk_offsets], lo=0.12, hi=0.22)
    gammas = _round_grid([float(base["gamma"]) + x for x in gamma_offsets], lo=0.0, hi=1.0)

    for risk, gamma, aversion in product(risks, gammas, aversions):
        _add_candidate(
            rows,
            seen,
            family="max_return_segment_relative_local",
            anchor_rank=96,
            source_reason="rank96_local_dense",
            policy=_policy_base(
                risk_tolerance=risk,
                policy_mode="segment_relative_tail_blended_uncertainty",
                gamma=gamma,
                uncertainty_aversion=aversion,
                solver_backend=solver_backend,
            ),
        )

    _add_tail_grid(
        rows,
        seen,
        family="max_return_tail_local",
        anchor_rank=96,
        source_reason="rank96_tail_sensitivity",
        risks=risks[1:-1] if len(risks) > 2 else risks,
        gammas=gammas[1:-1] if len(gammas) > 2 else gammas,
        aversions=[0.075, 0.10, 0.125] if profile == "stage1" else aversions,
        tail_focus_values=[0.95, 1.0] if profile == "stage1" else [0.90, 0.95, 1.0],
        solver_backend=solver_backend,
    )


def _append_bound_neighborhood(
    rows: list[dict[str, Any]],
    seen: set[str],
    *,
    anchor_by_rank: dict[int, dict[str, Any]],
    profile: str,
    solver_backend: str,
) -> None:
    risk_centers = []
    gamma_centers = []
    for rank in (219, 223):
        if rank in anchor_by_rank:
            row = anchor_by_rank[rank]
            risk_centers.append(float(row["risk_tolerance"]))
            gamma_centers.append(float(row["gamma"]))
    if not risk_centers:
        return
    risk_offsets = [-0.0075, -0.005, -0.0025, 0.0, 0.0025, 0.005]
    gamma_offsets = [-0.05, -0.025, 0.0, 0.025, 0.05]
    aversions = [0.05, 0.075, 0.10, 0.125, 0.15]
    capped_delta_values: tuple[float, ...] = (1.0,)
    if profile == "expanded":
        risk_offsets = [-0.01, -0.0075, -0.005, -0.0025, 0.0, 0.0025, 0.005, 0.0075, 0.01]
        gamma_offsets = [-0.075, -0.05, -0.025, -0.01, 0.0, 0.01, 0.025, 0.05, 0.075]
        aversions = [0.025, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20]
        capped_delta_values = (0.90, 1.0)
    risks = _round_grid(
        [center + offset for center in risk_centers for offset in risk_offsets], lo=0.14, hi=0.24
    )
    gammas = _round_grid(
        [center + offset for center in gamma_centers for offset in gamma_offsets], lo=0.0, hi=1.0
    )
    for risk, gamma, aversion, mode in product(
        risks,
        gammas,
        aversions,
        ["blended_uncertainty", "capped_blended_uncertainty"],
    ):
        for delta_cap in _capped_delta_values(str(mode), capped_delta_values):
            _add_candidate(
                rows,
                seen,
                family="bound_efficient_local",
                anchor_rank=219 if abs(gamma - 0.45) <= abs(gamma - 0.40) else 223,
                source_reason="rank219_rank223_bound_frontier",
                policy=_policy_base(
                    risk_tolerance=risk,
                    policy_mode=str(mode),
                    gamma=gamma,
                    uncertainty_aversion=aversion,
                    delta_cap_quantile=delta_cap,
                    solver_backend=solver_backend,
                ),
            )


def _append_claim_expanded_candidates(
    rows: list[dict[str, Any]], seen: set[str], *, solver_backend: str
) -> None:
    _add_blended_grid(
        rows,
        seen,
        family="bound_claim_refined_local",
        anchor_rank=219,
        source_reason="candidate462_466_return_bound_ridge",
        risks=_round_grid(
            [0.1705 + 0.0005 * idx for idx in range(10)] + [0.1750], lo=0.14, hi=0.24
        ),
        gammas=_round_grid([0.49, 0.50, 0.51, 0.52, 0.535, 0.55, 0.575], lo=0.0, hi=1.0),
        aversions=[0.05, 0.075, 0.10, 0.1125, 0.125, 0.1375, 0.15, 0.175],
        capped_delta_values=(0.95, 1.0),
        solver_backend=solver_backend,
    )
    _add_tail_grid(
        rows,
        seen,
        family="max_return_claim_refined_local",
        anchor_rank=96,
        source_reason="candidate264_economic_frontier_endpoint",
        risks=_round_grid([0.1560 + 0.0005 * idx for idx in range(9)], lo=0.12, hi=0.22),
        gammas=_round_grid([0.44, 0.45, 0.46, 0.47, 0.475, 0.485, 0.495], lo=0.0, hi=1.0),
        aversions=[0.10, 0.1125, 0.125, 0.1375, 0.15],
        tail_focus_values=[0.95, 1.0],
        solver_backend=solver_backend,
    )


def _generate_candidate_grid(
    anchors: pd.DataFrame,
    *,
    profile: str,
    solver_backend: str,
) -> pd.DataFrame:
    profile = str(profile).strip().lower()
    if profile not in VALID_PROFILES:
        raise ValueError(f"profile must be one of {sorted(VALID_PROFILES)}")

    anchor_by_rank = {int(row["candidate_rank"]): row for row in anchors.to_dict(orient="records")}
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    _add_anchor_candidates(
        rows,
        seen,
        anchor_by_rank=anchor_by_rank,
        solver_backend=solver_backend,
    )

    if profile == "claim_micro":
        _append_claim_micro_candidates(rows, seen, solver_backend=solver_backend)
        return _candidate_frame(rows)
    if profile == "claim_micro_ext":
        _append_claim_micro_ext_candidates(rows, seen, solver_backend=solver_backend)
        return _candidate_frame(rows)
    if profile in {"claim_bound_closure", "claim_bound_floor_closure"}:
        _append_bound_closure_candidates(
            rows,
            seen,
            profile=profile,
            solver_backend=solver_backend,
        )
        return _candidate_frame(rows)
    if profile == "claim_bound_terminal":
        _append_bound_terminal_candidates(rows, seen, solver_backend=solver_backend)
        return _candidate_frame(rows)

    _append_max_return_neighborhood(
        rows,
        seen,
        anchor_by_rank=anchor_by_rank,
        profile=profile,
        solver_backend=solver_backend,
    )
    _append_bound_neighborhood(
        rows,
        seen,
        anchor_by_rank=anchor_by_rank,
        profile=profile,
        solver_backend=solver_backend,
    )
    if profile == "claim_expanded":
        _append_claim_expanded_candidates(rows, seen, solver_backend=solver_backend)
    return _candidate_frame(rows)


def _exact_policy_alpha(
    aligned: pd.DataFrame,
    *,
    policy: dict[str, Any],
    alpha: float,
    budget: float,
    t_eval: float,
    threads: int,
) -> dict[str, Any]:
    pd_point, pd_low, pd_high = _compute_intervals_at_alpha(aligned, alpha)
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
    lgd = np.full(len(aligned), DEFAULT_LGD, dtype=float)
    solution = optimize_portfolio_allocation(
        loans=aligned,
        pd_point=pd_point,
        pd_low=pd_low,
        pd_high=pd_high,
        lgd=lgd,
        int_rates=int_rates,
        total_budget=float(budget),
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
    alloc = solution_allocation_vector(solution, len(aligned))
    total_allocated = float(np.sum(alloc * loan_amounts))
    weights = (alloc * loan_amounts) / max(total_allocated, 1e-6)
    certificate = compute_funded_certificate_metrics(
        weights,
        outcomes=y_true,
        pd_point=pd_point,
        pd_high=pd_high,
        pd_effective=effective_pd,
        alpha=alpha,
        risk_tolerance=float(policy["risk_tolerance"]),
        pd_cap_slack=float(solution.get("pd_cap_slack", 0.0)),
    )
    realized_total_return = float(
        np.sum(
            np.where(
                (alloc > 0.01) & (default_flag.astype(int) == 1),
                alloc * loan_amounts * (-DEFAULT_LGD),
                np.where(alloc > 0.01, alloc * loan_amounts * int_rates, 0.0),
            )
        )
    )
    expected_return_gross = float(np.sum(alloc * loan_amounts * int_rates))
    expected_loss_point = float(np.sum(alloc * loan_amounts * pd_point * lgd))
    expected_return_net_point = expected_return_gross - expected_loss_point
    pd_cap_slack = float(solution.get("pd_cap_slack", 0.0))
    risk_excess = round(certificate.realized_risk_tolerance_excess, 6)
    empirical_risk_screen = bool(certificate.realized_risk_tolerance_excess <= alpha + 1e-8)
    markov_screen = bool(certificate.sqrt_alpha + 1e-8 >= certificate.weighted_miscoverage)

    return {
        "alpha": float(alpha),
        "confidence": float(1.0 - alpha),
        "gamma_cp": round(certificate.gamma_cp, 6),
        "gamma_internalized": round(certificate.gamma_internalized, 6),
        "gamma_residual": round(certificate.gamma_residual, 6),
        "n_funded": int(solution.get("n_funded", int(np.sum(alloc > 0.01)))),
        "total_allocated": round(total_allocated, 2),
        "objective_value": round(float(solution.get("objective_value", 0.0)), 6),
        "expected_return_gross": round(expected_return_gross, 6),
        "expected_loss_point": round(expected_loss_point, 6),
        "expected_return_net_point": round(expected_return_net_point, 6),
        "realized_total_return": round(realized_total_return, 6),
        "weighted_pd_true": round(certificate.weighted_outcome, 6),
        "weighted_pd_constraint_used": round(certificate.weighted_pd_effective, 6),
        "weighted_pd_high": round(certificate.endpoint_budget, 6),
        "weighted_pd_point": round(certificate.weighted_pd_point, 6),
        "worst_case_pd": round(certificate.endpoint_budget, 6),
        "point_pd": round(certificate.weighted_pd_point, 6),
        "endpoint_budget": round(certificate.endpoint_budget, 9),
        "endpoint_budget_upper": round(certificate.endpoint_budget_upper, 9),
        "markov_loss_threshold": round(certificate.markov_loss_threshold, 9),
        "markov_loss_cap": round(certificate.markov_loss_cap, 9),
        "tau": float(policy["risk_tolerance"]),
        "realized_risk_tolerance_excess": risk_excess,
        "violation": risk_excess,
        "weighted_miscoverage_V": round(certificate.weighted_miscoverage, 6),
        "weighted_coverage_funded": round(certificate.weighted_coverage, 6),
        "sqrt_alpha": round(certificate.sqrt_alpha, 6),
        "empirical_coverage_funded": round(certificate.empirical_coverage_funded, 4),
        "empirical_risk_excess_leq_alpha": empirical_risk_screen,
        "bound_a_expected_violation_leq_alpha": empirical_risk_screen,
        "bound_b_prob_violation_gt_t": round(float(min(1.0, alpha / max(t_eval, 1e-8))), 4),
        "bound_b_t_eval": float(t_eval),
        "bound_b_is_vacuous": bool(min(1.0, alpha / max(t_eval, 1e-8)) >= 1.0),
        "markov_miscoverage_screen_pass": markov_screen,
        "bound_c_V_leq_sqrt_alpha": markov_screen,
        "certificate_screen_pass": empirical_risk_screen and markov_screen,
        "all_bounds_hold": empirical_risk_screen and markov_screen,
        "allocator_mode": "exact",
        "solver_status": str(solution.get("solver_status", "unknown")),
        "allocator_solver_backend": str(solution.get("solver_backend", policy["solver_backend"])),
        "allocator_native_solver_error": str(solution.get("native_solver_error", "")),
        "pd_cap_slack": round(pd_cap_slack, 6),
    }


def _aggregate_leaderboard(candidates: pd.DataFrame, bound_eval: pd.DataFrame) -> pd.DataFrame:
    if bound_eval.empty:
        return candidates.copy()
    bound_eval = add_policy_aware_bound_columns(bound_eval)
    grouped = bound_eval.groupby("local_candidate_id", dropna=False)
    agg = grouped.agg(
        alpha_exact_pass_count=("all_bounds_hold", "sum"),
        alpha_exact_check_count=("all_bounds_hold", "size"),
        alpha_exact_pass_rate=("all_bounds_hold", "mean"),
        alpha_max_realized_risk_tolerance_excess=(
            "realized_risk_tolerance_excess",
            "max",
        ),
        alpha_max_violation=("realized_risk_tolerance_excess", "max"),
        alpha_mean_gamma_cp=("gamma_cp", "mean"),
        alpha_mean_weighted_miscoverage_V=("weighted_miscoverage_V", "mean"),
        alpha_mean_weighted_pd_true=("weighted_pd_true", "mean"),
        alpha_mean_empirical_coverage_funded=("empirical_coverage_funded", "mean"),
        exact_return_mean=("realized_total_return", "mean"),
        exact_return_max=("realized_total_return", "max"),
        exact_return_min=("realized_total_return", "min"),
        exact_expected_return_net_point_mean=("expected_return_net_point", "mean"),
        n_funded_mean=("n_funded", "mean"),
        total_allocated_mean=("total_allocated", "mean"),
        allocator_backends=(
            "allocator_solver_backend",
            lambda s: ",".join(sorted(set(map(str, s)))),
        ),
    ).reset_index()
    alpha01 = (
        bound_eval[np.isclose(bound_eval["alpha"], 0.01)]
        .groupby("local_candidate_id", dropna=False)
        .agg(
            alpha01_exact_pass=("all_bounds_hold", "all"),
            alpha01_realized_total_return=("realized_total_return", "mean"),
            alpha01_gamma_cp=("gamma_cp", "mean"),
            alpha01_gamma_internalized=("gamma_internalized", "mean"),
            alpha01_gamma_residual=("gamma_residual", "mean"),
            alpha01_weighted_miscoverage_V=("weighted_miscoverage_V", "mean"),
            alpha01_realized_risk_tolerance_excess=(
                "realized_risk_tolerance_excess",
                "max",
            ),
            alpha01_violation=("realized_risk_tolerance_excess", "max"),
            alpha01_weighted_pd_true=("weighted_pd_true", "mean"),
            alpha01_weighted_pd_constraint_used=("weighted_pd_constraint_used", "mean"),
            alpha01_weighted_pd_high=("weighted_pd_high", "mean"),
            alpha01_weighted_pd_point=("weighted_pd_point", "mean"),
            alpha01_endpoint_budget=("endpoint_budget", "mean"),
            alpha01_endpoint_budget_upper=("endpoint_budget_upper", "mean"),
            alpha01_markov_loss_threshold=("markov_loss_threshold", "mean"),
            alpha01_markov_loss_cap=("markov_loss_cap", "mean"),
            alpha01_empirical_coverage_funded=("empirical_coverage_funded", "mean"),
            alpha01_n_funded=("n_funded", "mean"),
        )
        .reset_index()
    )
    work = candidates.merge(agg, on="local_candidate_id", how="left")
    work = work.merge(alpha01, on="local_candidate_id", how="left")
    for col in ["alpha01_exact_pass"]:
        if col in work:
            work[col] = work[col].fillna(False).infer_objects(copy=False).astype(bool)
    work["all_alpha_pass"] = work["alpha_exact_pass_count"].fillna(0) >= work[
        "alpha_exact_check_count"
    ].fillna(1)
    work["return_floor_surplus"] = (
        work["alpha01_realized_total_return"].fillna(float("-inf")) - DECLARED_RETURN_FLOOR
    )
    work = work.sort_values(
        by=[
            "alpha01_exact_pass",
            "all_alpha_pass",
            "alpha_exact_pass_count",
            "alpha01_realized_total_return",
            "alpha01_weighted_miscoverage_V",
            "alpha01_gamma_cp",
        ],
        ascending=[False, False, False, False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    work.insert(0, "claim_rank", np.arange(1, len(work) + 1, dtype=int))
    return work


def _ensure_claim_summary_columns(leaderboard: pd.DataFrame) -> pd.DataFrame:
    work = leaderboard.copy()
    if "alpha01_endpoint_budget" not in work.columns and "alpha01_weighted_pd_high" in work.columns:
        work["alpha01_endpoint_budget"] = pd.to_numeric(
            work["alpha01_weighted_pd_high"], errors="coerce"
        )
    if "alpha01_endpoint_budget_upper" not in work.columns:
        if {
            "alpha01_weighted_pd_high",
            "alpha01_weighted_pd_constraint_used",
        }.issubset(work.columns):
            residual = pd.to_numeric(
                work["alpha01_weighted_pd_high"], errors="coerce"
            ) - pd.to_numeric(work["alpha01_weighted_pd_constraint_used"], errors="coerce")
            work["alpha01_gamma_residual"] = residual.clip(lower=0.0)
            work["alpha01_endpoint_budget_upper"] = pd.to_numeric(
                work["risk_tolerance"], errors="coerce"
            ) + residual.clip(lower=0.0)
        else:
            alpha01_gamma = pd.to_numeric(work["alpha01_gamma_cp"], errors="coerce")
            risk = pd.to_numeric(work["risk_tolerance"], errors="coerce")
            gamma = pd.to_numeric(work["gamma"], errors="coerce")
            work["alpha01_endpoint_budget_upper"] = risk + (1.0 - gamma) * alpha01_gamma
    if "alpha01_markov_loss_threshold" not in work.columns and "alpha01_endpoint_budget" in work:
        work["alpha01_markov_loss_threshold"] = pd.to_numeric(
            work["alpha01_endpoint_budget"], errors="coerce"
        ) + float(np.sqrt(0.01))
    if "alpha01_markov_loss_cap" not in work.columns:
        work["alpha01_markov_loss_cap"] = pd.to_numeric(
            work["alpha01_endpoint_budget_upper"], errors="coerce"
        ) + float(np.sqrt(0.01))
    if "return_floor_surplus" not in work.columns:
        if "champion_return_surplus" in work.columns:
            work["return_floor_surplus"] = work["champion_return_surplus"]
        else:
            work["return_floor_surplus"] = (
                work["alpha01_realized_total_return"].fillna(float("-inf")) - DECLARED_RETURN_FLOOR
            )
    return work


def _all_alpha_eligible(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[
        frame["alpha01_exact_pass"].fillna(False).astype(bool)
        & frame["all_alpha_pass"].fillna(False).astype(bool)
    ].copy()


def _row_payload(frame: pd.DataFrame) -> dict[str, Any] | None:
    if frame.empty:
        return None
    row = frame.iloc[0]
    return {
        field: row[field].item() if hasattr(row[field], "item") else row[field]
        for field in CLAIM_ROW_FIELDS
        if field in row.index
    }


def _add_normalized_score(
    frame: pd.DataFrame,
    *,
    source: str,
    target: str,
    higher_better: bool,
) -> None:
    vals = pd.to_numeric(frame[source], errors="coerce")
    lo, hi = float(vals.min()), float(vals.max())
    if hi <= lo:
        frame[target] = 1.0
    elif higher_better:
        frame[target] = (vals - lo) / (hi - lo)
    else:
        frame[target] = (hi - vals) / (hi - lo)


def _balanced_claim_candidates(above_return_floor: pd.DataFrame) -> pd.DataFrame:
    balanced = above_return_floor.copy()
    if balanced.empty:
        return balanced
    for source, target, higher_better in [
        ("alpha01_realized_total_return", "return_score", True),
        ("alpha01_markov_loss_cap", "bound_score", False),
        ("alpha01_weighted_miscoverage_V", "v_score", False),
    ]:
        _add_normalized_score(
            balanced,
            source=source,
            target=target,
            higher_better=higher_better,
        )
    balanced["ijds_balanced_score"] = (
        0.40 * balanced["return_score"]
        + 0.40 * balanced["bound_score"]
        + 0.20 * balanced["v_score"]
    )
    return balanced


def _family_claim_summary(leaderboard: pd.DataFrame) -> dict[str, Any]:
    by_family: dict[str, Any] = {}
    if leaderboard.empty:
        return by_family
    for family, frame in leaderboard.groupby("local_family", dropna=False):
        fam_eligible = _all_alpha_eligible(frame)
        fam_above_floor = fam_eligible[
            fam_eligible["alpha01_realized_total_return"] >= DECLARED_RETURN_FLOOR
        ]
        by_family[str(family)] = {
            "n_policies": int(len(frame)),
            "n_all_alpha_passers": int(len(fam_eligible)),
            "all_alpha_pass_rate": float(len(fam_eligible) / max(len(frame), 1)),
            "best_return": float(fam_eligible["alpha01_realized_total_return"].max())
            if not fam_eligible.empty
            else None,
            "min_gamma_cp_above_return_floor": float(fam_above_floor["alpha01_gamma_cp"].min())
            if not fam_above_floor.empty
            else None,
            "min_v_above_return_floor": float(
                fam_above_floor["alpha01_weighted_miscoverage_V"].min()
            )
            if not fam_above_floor.empty
            else None,
        }
    return by_family


def _alpha_claim_summary(bound_eval: pd.DataFrame) -> dict[str, Any]:
    by_alpha: dict[str, Any] = {}
    if bound_eval.empty:
        return by_alpha
    risk_excess_column = (
        "realized_risk_tolerance_excess"
        if "realized_risk_tolerance_excess" in bound_eval.columns
        else "violation"
    )
    for alpha, frame in bound_eval.groupby("alpha", dropna=False):
        alpha_value = float(str(alpha))
        by_alpha[str(alpha_value)] = {
            "n_checks": int(len(frame)),
            "pass_rate": float(frame["all_bounds_hold"].fillna(False).mean()),
            "max_realized_risk_tolerance_excess": float(frame[risk_excess_column].max()),
            "max_violation": float(frame[risk_excess_column].max()),
            "mean_gamma_cp": float(frame["gamma_cp"].mean()),
            "mean_weighted_miscoverage_V": float(frame["weighted_miscoverage_V"].mean()),
        }
    return by_alpha


def _claim_alpha_values(bound_eval: pd.DataFrame, alpha_grid: list[float] | None) -> list[float]:
    if alpha_grid is not None:
        values = [float(value) for value in alpha_grid]
    elif "alpha" in bound_eval:
        values = sorted(float(value) for value in bound_eval["alpha"].dropna().unique())
    else:
        values = list(DEFAULT_ALPHA_GRID)
    return sorted(dict.fromkeys(values))


def _finite_grid_policy(alpha_values: list[float]) -> dict[str, Any]:
    return {
        "alpha_grid": alpha_values,
        "alpha_grid_size": int(len(alpha_values)),
        "alpha_grid_semantics": (
            "finite_predeclared_grid; all-alpha pass counts only the listed levels "
            "and is not a universal alpha or conditional-coverage guarantee"
        ),
        "region_semantics": (
            "finite_policy_grid; candidate denominators describe evaluated policies, "
            "not a continuous robust region"
        ),
    }


def _claim_selection_protocol() -> dict[str, Any]:
    return {
        "body_default": "balanced_return_bound_claim",
        "frontier_endpoints": [
            "max_return_claim",
            "best_gamma_cp_return_floor_claim",
            "best_weighted_miscoverage_return_floor_claim",
        ],
        "required_filters": [
            "alpha01_exact_pass",
            "all_alpha_pass over the finite alpha_grid",
            "return_floor_surplus >= 0 for declared-return-floor claims",
        ],
        "balanced_score": (
            "0.40 * normalized return surplus + 0.40 * normalized inverse "
            "alpha01 Markov loss cap + 0.20 * normalized inverse "
            "weighted_miscoverage_V among all-alpha above-return-floor candidates"
        ),
        "promotion_caveat": (
            "Realized-return maxima are frontier endpoints; paper promotion should "
            "prefer a declared return-bound lens unless the manuscript explicitly "
            "frames the point as an economic endpoint."
        ),
    }


def _claim_summary(
    leaderboard: pd.DataFrame,
    bound_eval: pd.DataFrame,
    *,
    alpha_grid: list[float] | None = None,
) -> dict[str, Any]:
    leaderboard = _ensure_claim_summary_columns(leaderboard)
    eligible = _all_alpha_eligible(leaderboard)
    above_return_floor = eligible[
        eligible["alpha01_realized_total_return"] >= DECLARED_RETURN_FLOOR
    ].copy()

    max_return = _row_payload(
        eligible.sort_values("alpha01_realized_total_return", ascending=False)
    )
    best_gamma = _row_payload(
        above_return_floor.sort_values(
            ["alpha01_gamma_cp", "alpha01_realized_total_return"],
            ascending=[True, False],
        )
    )
    best_v = _row_payload(
        above_return_floor.sort_values(
            ["alpha01_weighted_miscoverage_V", "alpha01_realized_total_return"],
            ascending=[True, False],
        )
    )
    balanced = _balanced_claim_candidates(above_return_floor)
    balanced_claim = _row_payload(
        balanced.sort_values("ijds_balanced_score", ascending=False)
        if not balanced.empty
        else balanced
    )
    alpha_values = _claim_alpha_values(bound_eval, alpha_grid)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "declared_return_floor": DECLARED_RETURN_FLOOR,
        "finite_grid_policy": _finite_grid_policy(alpha_values),
        "claim_selection_protocol": _claim_selection_protocol(),
        "n_policies": int(len(leaderboard)),
        "n_all_alpha_passers": int(len(eligible)),
        "n_all_alpha_passers_above_return_floor": int(len(above_return_floor)),
        "max_return_claim": max_return,
        "best_gamma_cp_return_floor_claim": best_gamma,
        "best_weighted_miscoverage_return_floor_claim": best_v,
        "balanced_return_bound_claim": balanced_claim,
        "by_family": _family_claim_summary(leaderboard),
        "by_alpha": _alpha_claim_summary(bound_eval),
        "interpretation": {
            "max_return_claim": "Use when the paper emphasizes certified economic return.",
            "best_gamma_cp_return_floor_claim": "Use when the paper emphasizes a tighter conformal robustness budget while preserving the declared return floor.",
            "best_weighted_miscoverage_return_floor_claim": "Use when the paper emphasizes lower realized weighted miscoverage while preserving the declared return floor.",
            "balanced_return_bound_claim": "Use as the default IJDS narrative if return and bound should be presented as a frontier rather than a single leaderboard point.",
        },
    }


def _write_status(
    *,
    run_tag: str,
    status_path: Path,
    start_monotonic: float,
    completed: int,
    total: int,
    phase: str,
    state: str,
    initial_completed: int = 0,
    extra: dict[str, Any] | None = None,
) -> None:
    elapsed = time.monotonic() - start_monotonic
    remaining = max(0, int(total) - int(completed))
    completed_this_run = max(0, int(completed) - int(initial_completed))
    eta = (
        (elapsed / completed_this_run) * remaining
        if completed_this_run > 0 and remaining > 0
        else (0.0 if remaining == 0 else None)
    )
    payload: dict[str, Any] = {
        "total_checks": int(total),
        "completed_checks": int(completed),
        "completed_checks_at_start": int(initial_completed),
        "completed_checks_this_run": int(completed_this_run),
        "pct_complete": float(completed / max(total, 1)),
        "elapsed_sec": float(elapsed),
        "eta_sec": eta,
    }
    if extra:
        payload.update(extra)
    write_runtime_status(
        STAGE_NAME,
        phase=phase,
        state=state,
        run_tag=run_tag,
        status_path=str(status_path),
        extra=payload,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-tag", default="pool93_ijds_local_refine_stage1")
    parser.add_argument(
        "--profile",
        choices=[
            "stage1",
            "expanded",
            "claim_expanded",
            "claim_micro",
            "claim_micro_ext",
            "claim_bound_closure",
            "claim_bound_floor_closure",
            "claim_bound_terminal",
        ],
        default="stage1",
    )
    parser.add_argument("--source-bound-eval", default=str(DEFAULT_SOURCE_BOUND_EVAL))
    parser.add_argument("--source-selection", default=str(DEFAULT_SOURCE_SELECTION))
    parser.add_argument("--conformal-intervals-path", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--model-dir", default="")
    parser.add_argument("--anchor-ranks", default="96,219,223")
    parser.add_argument("--alpha-grid", default="")
    parser.add_argument("--budget", type=float, default=1_000_000.0)
    parser.add_argument("--t-eval", type=float, default=DEFAULT_T_EVAL)
    parser.add_argument("--exact-threads", type=int, default=8)
    parser.add_argument("--solver-backend", default="highspy")
    parser.add_argument("--max-candidates", type=int, default=0)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--checkpoint-every", type=int, default=25)
    parser.add_argument(
        "--parallel-workers",
        type=int,
        default=1,
        help=(
            "Number of independent candidate-alpha solves to run in parallel. "
            "Use --exact-threads 1 with multiple workers to avoid solver oversubscription."
        ),
    )
    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=0,
        help="Debug/smoke option: keep only the first N generated policies when positive.",
    )
    return parser


def _resolve_paths(args: argparse.Namespace, *, run_tag: str) -> Pool93Paths:
    output_dir = (
        Path(args.output_dir)
        if str(args.output_dir).strip()
        else ROOT / "data/processed/experiments/champion_reopen" / run_tag / "portfolio"
    )
    model_dir = (
        Path(args.model_dir)
        if str(args.model_dir).strip()
        else ROOT / "models/experiments/champion_reopen" / run_tag / "portfolio"
    )
    return Pool93Paths(
        output_dir=output_dir,
        model_dir=model_dir,
        checkpoint_dir=model_dir / "runtime_checkpoints",
        status_path=model_dir / "runtime_status.json",
        candidates_path=output_dir / "pool93_ijds_local_refinement_candidates.parquet",
        bound_eval_path=output_dir / "pool93_ijds_local_refinement_bound_eval.parquet",
        leaderboard_path=output_dir / "pool93_ijds_local_refinement_leaderboard.parquet",
        claim_summary_path=model_dir / "pool93_ijds_local_refinement_claim_summary.json",
        manifest_path=model_dir / "pool93_ijds_local_refinement_manifest.json",
    )


def _ensure_pool93_dirs(paths: Pool93Paths) -> None:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    paths.model_dir.mkdir(parents=True, exist_ok=True)
    paths.checkpoint_dir.mkdir(parents=True, exist_ok=True)


def _conformal_intervals_from_selection(
    *,
    explicit_path: str,
    source_selection: Path,
) -> str:
    if str(explicit_path).strip():
        return str(explicit_path).strip()
    source_selection_payload = json.loads(source_selection.read_text(encoding="utf-8"))
    return str(ROOT / source_selection_payload["conformal_intervals_path"])


def _load_or_generate_candidates(
    *,
    args: argparse.Namespace,
    paths: Pool93Paths,
    source_bound_eval: Path,
    anchor_ranks: list[int],
) -> pd.DataFrame:
    if paths.candidates_path.exists():
        candidates = pd.read_parquet(paths.candidates_path)
        logger.info(
            "Reusing candidate manifest: {} rows from {}",
            len(candidates),
            paths.candidates_path,
        )
        return candidates
    anchors = _source_anchor_rows(source_bound_eval, anchor_ranks)
    candidates = _generate_candidate_grid(
        anchors,
        profile=str(args.profile),
        solver_backend=str(args.solver_backend),
    )
    if int(args.candidate_limit) > 0:
        candidates = candidates.head(int(args.candidate_limit)).copy().reset_index(drop=True)
        candidates["local_candidate_id"] = np.arange(1, len(candidates) + 1, dtype=int)
    atomic_write_parquet(candidates, paths.candidates_path, index=False)
    logger.info(
        "Wrote candidate manifest: {} policies to {}",
        len(candidates),
        paths.candidates_path,
    )
    return candidates


def _manifest_payload(
    *,
    args: argparse.Namespace,
    paths: Pool93Paths,
    run_tag: str,
    source_bound_eval: Path,
    source_selection: Path,
    conformal_intervals_path: str,
    anchor_ranks: list[int],
    alpha_grid: list[float],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "run_tag": run_tag,
        "profile": str(args.profile),
        "source_bound_eval": str(source_bound_eval),
        "source_selection": str(source_selection),
        "conformal_intervals_path": conformal_intervals_path,
        "anchor_ranks": anchor_ranks,
        "alpha_grid": alpha_grid,
        "budget": float(args.budget),
        "t_eval": float(args.t_eval),
        "exact_threads": int(args.exact_threads),
        "solver_backend": str(args.solver_backend),
        "max_candidates": int(args.max_candidates),
        "random_state": int(args.random_state),
        "checkpoint_every": int(args.checkpoint_every),
        "parallel_workers": int(args.parallel_workers),
        "candidates_path": str(paths.candidates_path),
        "bound_eval_path": str(paths.bound_eval_path),
        "leaderboard_path": str(paths.leaderboard_path),
        "claim_summary_path": str(paths.claim_summary_path),
    }


def _load_partial_bound_eval(path: Path) -> tuple[pd.DataFrame, set[tuple[int, float]]]:
    partial = pd.DataFrame()
    if path.exists():
        partial = pd.read_parquet(path)
        if not partial.empty:
            partial = partial.drop_duplicates(
                ["local_candidate_id", "alpha"],
                keep="last",
            ).reset_index(drop=True)
            logger.info("Resuming local refinement from {} rows", len(partial))
    completed_keys = {
        (int(row["local_candidate_id"]), float(row["alpha"]))
        for row in partial.to_dict(orient="records")
    }
    return partial, completed_keys


def _pending_refinement_tasks(
    *,
    candidates: pd.DataFrame,
    alpha_grid: list[float],
    completed_keys: set[tuple[int, float]],
) -> list[tuple[dict[str, Any], float]]:
    return [
        (candidate, float(alpha))
        for candidate in candidates.to_dict(orient="records")
        for alpha in alpha_grid
        if (int(candidate["local_candidate_id"]), float(alpha)) not in completed_keys
    ]


def _persist_refinement_progress(
    *,
    paths: Pool93Paths,
    candidates: pd.DataFrame,
    rows: list[dict[str, Any]],
    alpha_grid: list[float],
) -> None:
    bound_eval = pd.DataFrame(rows)
    atomic_write_parquet(bound_eval, paths.bound_eval_path, index=False)
    leaderboard = _aggregate_leaderboard(candidates, bound_eval)
    atomic_write_parquet(leaderboard, paths.leaderboard_path, index=False)
    atomic_write_json(
        paths.claim_summary_path,
        _claim_summary(leaderboard, bound_eval, alpha_grid=alpha_grid),
    )


def _run_serial_refinement(
    *,
    pending_tasks: list[tuple[dict[str, Any], float]],
    aligned: pd.DataFrame,
    budget: float,
    t_eval: float,
    exact_threads: int,
    record_result: Any,
) -> None:
    for candidate, alpha in pending_tasks:
        policy = {field: candidate[field] for field in SEMANTIC_POLICY_FIELDS}
        result = _exact_policy_alpha(
            aligned,
            policy=policy,
            alpha=float(alpha),
            budget=float(budget),
            t_eval=float(t_eval),
            threads=int(exact_threads),
        )
        record_result(candidate, alpha, result)


def _run_parallel_refinement(
    *,
    pending_tasks: list[tuple[dict[str, Any], float]],
    aligned: pd.DataFrame,
    parallel_workers: int,
    budget: float,
    t_eval: float,
    exact_threads: int,
    persist_progress: Any,
    record_result: Any,
) -> None:
    logger.info(
        "Running exact refinement with {} parallel workers and {} solver thread(s) per worker",
        parallel_workers,
        int(exact_threads),
    )
    mp_context = mp.get_context("fork") if sys.platform != "win32" else None
    max_in_flight = max(parallel_workers, parallel_workers * 2)
    next_task_idx = 0
    futures: dict[Any, tuple[dict[str, Any], float]] = {}
    with ProcessPoolExecutor(
        max_workers=parallel_workers,
        mp_context=mp_context,
        initializer=_init_exact_worker,
        initargs=(aligned,),
    ) as executor:
        while next_task_idx < len(pending_tasks) or futures:
            while next_task_idx < len(pending_tasks) and len(futures) < max_in_flight:
                candidate, alpha = pending_tasks[next_task_idx]
                future = executor.submit(
                    _exact_policy_alpha_task,
                    candidate,
                    alpha,
                    float(budget),
                    float(t_eval),
                    int(exact_threads),
                )
                futures[future] = (candidate, alpha)
                next_task_idx += 1
            done, _ = wait(futures, return_when=FIRST_COMPLETED)
            for future in done:
                candidate, alpha = futures.pop(future)
                try:
                    result = future.result()
                except Exception:
                    persist_progress()
                    raise
                result_only = {
                    key: value
                    for key, value in result.items()
                    if key not in candidate or key in {"alpha", "confidence"}
                }
                record_result(candidate, alpha, result_only)


def _write_final_outputs(
    *,
    paths: Pool93Paths,
    candidates: pd.DataFrame,
    rows: list[dict[str, Any]],
    alpha_grid: list[float],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    bound_eval = pd.DataFrame(rows)
    atomic_write_parquet(bound_eval, paths.bound_eval_path, index=False)
    leaderboard = _aggregate_leaderboard(candidates, bound_eval)
    atomic_write_parquet(leaderboard, paths.leaderboard_path, index=False)
    claim_summary = _claim_summary(leaderboard, bound_eval, alpha_grid=alpha_grid)
    atomic_write_json(paths.claim_summary_path, claim_summary)
    return leaderboard, claim_summary


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    run_tag = str(args.run_tag).strip().replace("/", "_")
    paths = _resolve_paths(args, run_tag=run_tag)
    _ensure_pool93_dirs(paths)

    source_bound_eval = Path(args.source_bound_eval)
    source_selection = Path(args.source_selection)
    conformal_intervals_path = _conformal_intervals_from_selection(
        explicit_path=args.conformal_intervals_path,
        source_selection=source_selection,
    )
    alpha_grid = _coerce_float_grid(args.alpha_grid, DEFAULT_ALPHA_GRID)
    anchor_ranks = _coerce_int_grid(args.anchor_ranks, [96, 219, 223])

    candidates = _load_or_generate_candidates(
        args=args,
        paths=paths,
        source_bound_eval=source_bound_eval,
        anchor_ranks=anchor_ranks,
    )
    atomic_write_json(
        paths.manifest_path,
        _manifest_payload(
            args=args,
            paths=paths,
            run_tag=run_tag,
            source_bound_eval=source_bound_eval,
            source_selection=source_selection,
            conformal_intervals_path=conformal_intervals_path,
            anchor_ranks=anchor_ranks,
            alpha_grid=alpha_grid,
        ),
    )

    partial, completed_keys = _load_partial_bound_eval(paths.bound_eval_path)
    rows: list[dict[str, Any]] = partial.to_dict(orient="records") if not partial.empty else []

    total_checks = int(len(candidates) * len(alpha_grid))
    start = time.monotonic()
    initial_completed = int(len(completed_keys))
    _write_status(
        run_tag=run_tag,
        status_path=paths.status_path,
        start_monotonic=start,
        completed=len(completed_keys),
        total=total_checks,
        phase="exact_refinement_running",
        state="running",
        initial_completed=initial_completed,
        extra={"n_policies": int(len(candidates)), "profile": str(args.profile)},
    )

    aligned = _load_aligned_dataset(
        conformal_intervals_path=conformal_intervals_path,
        max_candidates=int(args.max_candidates),
        random_state=int(args.random_state),
    )
    logger.info("Loaded aligned full universe: {} rows", len(aligned))
    completed = len(completed_keys)

    def persist_progress() -> None:
        _persist_refinement_progress(
            paths=paths,
            candidates=candidates,
            rows=rows,
            alpha_grid=alpha_grid,
        )

    def record_result(candidate: dict[str, Any], alpha: float, result: dict[str, Any]) -> None:
        nonlocal completed
        row = {
            **candidate,
            **result,
        }
        rows.append(row)
        completed += 1
        completed_keys.add((int(candidate["local_candidate_id"]), float(alpha)))
        _write_status(
            run_tag=run_tag,
            status_path=paths.status_path,
            start_monotonic=start,
            completed=completed,
            total=total_checks,
            phase="exact_refinement_running",
            state="running",
            initial_completed=initial_completed,
            extra={
                "n_policies": int(len(candidates)),
                "profile": str(args.profile),
                "parallel_workers": int(args.parallel_workers),
                "local_candidate_id": int(candidate["local_candidate_id"]),
                "current_alpha": float(alpha),
                "local_family": str(candidate["local_family"]),
                "anchor_rank": int(candidate["anchor_rank"]),
            },
        )
        if completed % max(1, int(args.checkpoint_every)) == 0:
            persist_progress()

    pending_tasks = _pending_refinement_tasks(
        candidates=candidates,
        alpha_grid=alpha_grid,
        completed_keys=completed_keys,
    )

    parallel_workers = max(1, int(args.parallel_workers))
    if parallel_workers <= 1:
        _run_serial_refinement(
            pending_tasks=pending_tasks,
            aligned=aligned,
            budget=float(args.budget),
            t_eval=float(args.t_eval),
            exact_threads=int(args.exact_threads),
            record_result=record_result,
        )
    else:
        _run_parallel_refinement(
            pending_tasks=pending_tasks,
            aligned=aligned,
            parallel_workers=parallel_workers,
            budget=float(args.budget),
            t_eval=float(args.t_eval),
            exact_threads=int(args.exact_threads),
            persist_progress=persist_progress,
            record_result=record_result,
        )

    leaderboard, claim_summary = _write_final_outputs(
        paths=paths,
        candidates=candidates,
        rows=rows,
        alpha_grid=alpha_grid,
    )

    _write_status(
        run_tag=run_tag,
        status_path=paths.status_path,
        start_monotonic=start,
        completed=total_checks,
        total=total_checks,
        phase="selection_complete",
        state="completed",
        initial_completed=initial_completed,
        extra={
            "n_policies": int(len(candidates)),
            "n_all_alpha_passers": int(claim_summary["n_all_alpha_passers"]),
            "n_all_alpha_passers_above_return_floor": int(
                claim_summary["n_all_alpha_passers_above_return_floor"]
            ),
            "claim_summary_path": str(paths.claim_summary_path),
            "leaderboard_path": str(paths.leaderboard_path),
        },
    )
    write_runtime_checkpoint(
        STAGE_NAME,
        "selection_complete",
        {
            "run_tag": run_tag,
            "completed_at_utc": datetime.now(tz=UTC).isoformat(),
            "claim_summary_path": str(paths.claim_summary_path),
            "leaderboard_path": str(paths.leaderboard_path),
        },
        checkpoint_dir=paths.checkpoint_dir,
    )
    logger.info("Local IJDS refinement complete: {}", paths.claim_summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
