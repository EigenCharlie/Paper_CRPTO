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
from src.optimization.portfolio_model import optimize_portfolio_allocation  # noqa: E402
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    write_runtime_checkpoint,
    write_runtime_status,
)

STAGE_NAME = "pool93_ijds_local_refinement"
DECLARED_RETURN_FLOOR = 170464.54
DEFAULT_ALPHA_GRID = [0.01, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.20]
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


def _generate_candidate_grid(
    anchors: pd.DataFrame,
    *,
    profile: str,
    solver_backend: str,
) -> pd.DataFrame:
    profile = str(profile).strip().lower()
    valid_profiles = {
        "stage1",
        "expanded",
        "claim_expanded",
        "claim_micro",
        "claim_micro_ext",
        "claim_bound_closure",
        "claim_bound_floor_closure",
        "claim_bound_terminal",
    }
    if profile not in valid_profiles:
        raise ValueError(f"profile must be one of {sorted(valid_profiles)}")

    anchor_by_rank = {int(row.candidate_rank): row for row in anchors.itertuples(index=False)}
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def anchor_policy(rank: int) -> dict[str, Any]:
        row = anchor_by_rank[rank]
        return _policy_base(
            risk_tolerance=float(row.risk_tolerance),
            policy_mode=str(row.policy_mode),
            gamma=float(row.gamma),
            uncertainty_aversion=float(row.uncertainty_aversion),
            delta_cap_quantile=float(row.delta_cap_quantile),
            tail_focus_quantile=float(row.tail_focus_quantile),
            min_budget_utilization=float(row.min_budget_utilization),
            pd_cap_slack_penalty=float(row.pd_cap_slack_penalty),
            solver_backend=solver_backend,
        )

    for rank, reason in [
        (96, "source_exact_max_return"),
        (219, "source_low_gamma_cp_return_floor"),
        (223, "source_low_weighted_miscoverage_high_return"),
    ]:
        if rank in anchor_by_rank:
            _add_candidate(
                rows,
                seen,
                family="anchor_policy",
                anchor_rank=rank,
                source_reason=reason,
                policy=anchor_policy(rank),
            )

    if profile == "claim_micro":
        # Final IJDS micro-refinement around the completed expanded frontier:
        # - candidate 1206: tightest Markov cap above the declared return floor,
        # - candidate 1665/1667: body/default low-V return-bound point,
        # - candidate 1922: highest return under Markov cap <= 0.36,
        # - candidate 2777/2857: economic endpoint.
        # The grid is intentionally local and paper-facing, not a new generic
        # champion search.
        body_risks = _round_grid(
            [0.1715 + 0.00025 * idx for idx in range(5)],
            lo=0.14,
            hi=0.24,
        )
        body_gammas = _round_grid(
            [0.545 + 0.005 * idx for idx in range(7)],
            lo=0.0,
            hi=1.0,
        )
        body_aversions = [0.0, 0.0125, 0.025, 0.0375, 0.05, 0.0625, 0.075, 0.10]
        for risk, gamma, aversion, mode in product(
            body_risks,
            body_gammas,
            body_aversions,
            ["blended_uncertainty", "capped_blended_uncertainty"],
        ):
            delta_values = [1.0] if mode == "blended_uncertainty" else [0.95, 1.0]
            for delta_cap in delta_values:
                _add_candidate(
                    rows,
                    seen,
                    family="claim_micro_body_low_v",
                    anchor_rank=219,
                    source_reason="candidate1665_1667_body_default_micro",
                    policy=_policy_base(
                        risk_tolerance=risk,
                        policy_mode=mode,
                        gamma=gamma,
                        uncertainty_aversion=aversion,
                        delta_cap_quantile=delta_cap,
                        solver_backend=solver_backend,
                    ),
                )

        tight_risks = _round_grid(
            [0.1700 + 0.00025 * idx for idx in range(5)],
            lo=0.14,
            hi=0.24,
        )
        tight_gammas = _round_grid(
            [0.575 + 0.005 * idx for idx in range(6)],
            lo=0.0,
            hi=1.0,
        )
        tight_aversions = [0.15, 0.1625, 0.175, 0.1875, 0.20, 0.225]
        for risk, gamma, aversion, mode in product(
            tight_risks,
            tight_gammas,
            tight_aversions,
            ["blended_uncertainty", "capped_blended_uncertainty"],
        ):
            delta_values = [1.0] if mode == "blended_uncertainty" else [0.95, 1.0]
            for delta_cap in delta_values:
                _add_candidate(
                    rows,
                    seen,
                    family="claim_micro_bound_tight",
                    anchor_rank=219,
                    source_reason="candidate1206_tight_cap_micro",
                    policy=_policy_base(
                        risk_tolerance=risk,
                        policy_mode=mode,
                        gamma=gamma,
                        uncertainty_aversion=aversion,
                        delta_cap_quantile=delta_cap,
                        solver_backend=solver_backend,
                    ),
                )

        high_return_risks = _round_grid(
            [0.1725 + 0.00025 * idx for idx in range(7)],
            lo=0.14,
            hi=0.24,
        )
        high_return_gammas = _round_grid(
            [0.500 + 0.005 * idx for idx in range(6)],
            lo=0.0,
            hi=1.0,
        )
        high_return_aversions = [0.05, 0.0625, 0.075, 0.0875, 0.10]
        for risk, gamma, aversion, mode in product(
            high_return_risks,
            high_return_gammas,
            high_return_aversions,
            ["blended_uncertainty", "capped_blended_uncertainty"],
        ):
            delta_values = [1.0] if mode == "blended_uncertainty" else [0.95, 1.0]
            for delta_cap in delta_values:
                _add_candidate(
                    rows,
                    seen,
                    family="claim_micro_high_return_cap036",
                    anchor_rank=219,
                    source_reason="candidate1922_return_cap036_micro",
                    policy=_policy_base(
                        risk_tolerance=risk,
                        policy_mode=mode,
                        gamma=gamma,
                        uncertainty_aversion=aversion,
                        delta_cap_quantile=delta_cap,
                        solver_backend=solver_backend,
                    ),
                )

        econ_risks = _round_grid(
            [0.1565 + 0.00025 * idx for idx in range(9)],
            lo=0.12,
            hi=0.22,
        )
        econ_gammas = _round_grid(
            [0.44 + 0.005 * idx for idx in range(13)],
            lo=0.0,
            hi=1.0,
        )
        econ_aversions = [0.1125, 0.125, 0.1375, 0.15]
        for risk, gamma, aversion, tail_focus in product(
            econ_risks,
            econ_gammas,
            econ_aversions,
            [0.95, 1.0],
        ):
            _add_candidate(
                rows,
                seen,
                family="claim_micro_economic_endpoint",
                anchor_rank=96,
                source_reason="candidate2777_2857_economic_endpoint_micro",
                policy=_policy_base(
                    risk_tolerance=risk,
                    policy_mode="tail_blended_uncertainty",
                    gamma=gamma,
                    uncertainty_aversion=aversion,
                    tail_focus_quantile=tail_focus,
                    solver_backend=solver_backend,
                ),
            )

        candidates = pd.DataFrame(rows).reset_index(drop=True)
        candidates.insert(0, "local_candidate_id", range(1, len(candidates) + 1))
        return candidates

    if profile == "claim_micro_ext":
        # Surgical extensions from the completed claim_micro frontier. These
        # neighborhoods target only exposed claim boundaries, not a fresh broad
        # portfolio search:
        # - body/cap<=0.345 polish around candidates 37/205,
        # - bound-tight endpoint around candidate 949,
        # - cap<=0.36 return endpoint around candidate 1975,
        # - economic endpoint around candidate 2122.
        body_risks = _round_grid(
            [0.17125 + 0.000125 * idx for idx in range(11)],
            lo=0.14,
            hi=0.24,
        )
        body_gammas = _round_grid(
            [0.5475, 0.55, 0.5525, 0.555, 0.5575],
            lo=0.0,
            hi=1.0,
        )
        body_aversions = [0.025, 0.0375, 0.05, 0.0625]
        for risk, gamma, aversion, mode in product(
            body_risks,
            body_gammas,
            body_aversions,
            ["blended_uncertainty", "capped_blended_uncertainty"],
        ):
            delta_values = [1.0] if mode == "blended_uncertainty" else [0.975, 1.0]
            for delta_cap in delta_values:
                _add_candidate(
                    rows,
                    seen,
                    family="claim_micro_ext_body_cap345",
                    anchor_rank=219,
                    source_reason="candidate37_205_body_cap345_extension",
                    policy=_policy_base(
                        risk_tolerance=risk,
                        policy_mode=mode,
                        gamma=gamma,
                        uncertainty_aversion=aversion,
                        delta_cap_quantile=delta_cap,
                        solver_backend=solver_backend,
                    ),
                )

        tight_risks = _round_grid(
            [0.1690 + 0.00025 * idx for idx in range(8)],
            lo=0.14,
            hi=0.24,
        )
        tight_gammas = _round_grid(
            [0.600 + 0.005 * idx for idx in range(11)],
            lo=0.0,
            hi=1.0,
        )
        tight_aversions = [0.2125, 0.225, 0.2375, 0.25, 0.2625, 0.275]
        for risk, gamma, aversion, mode in product(
            tight_risks,
            tight_gammas,
            tight_aversions,
            ["blended_uncertainty", "capped_blended_uncertainty"],
        ):
            delta_values = [1.0] if mode == "blended_uncertainty" else [0.95, 1.0]
            for delta_cap in delta_values:
                _add_candidate(
                    rows,
                    seen,
                    family="claim_micro_ext_bound_tight",
                    anchor_rank=219,
                    source_reason="candidate949_bound_tight_extension",
                    policy=_policy_base(
                        risk_tolerance=risk,
                        policy_mode=mode,
                        gamma=gamma,
                        uncertainty_aversion=aversion,
                        delta_cap_quantile=delta_cap,
                        solver_backend=solver_backend,
                    ),
                )

        cap036_risks = _round_grid(
            [0.17375 + 0.00025 * idx for idx in range(10)],
            lo=0.14,
            hi=0.24,
        )
        cap036_gammas = _round_grid(
            [0.505 + 0.0025 * idx for idx in range(9)],
            lo=0.0,
            hi=1.0,
        )
        cap036_aversions = [0.0625, 0.075, 0.0875, 0.10]
        for risk, gamma, aversion, mode in product(
            cap036_risks,
            cap036_gammas,
            cap036_aversions,
            ["blended_uncertainty", "capped_blended_uncertainty"],
        ):
            delta_values = [1.0] if mode == "blended_uncertainty" else [0.95, 1.0]
            for delta_cap in delta_values:
                _add_candidate(
                    rows,
                    seen,
                    family="claim_micro_ext_cap036_return",
                    anchor_rank=219,
                    source_reason="candidate1975_cap036_return_extension",
                    policy=_policy_base(
                        risk_tolerance=risk,
                        policy_mode=mode,
                        gamma=gamma,
                        uncertainty_aversion=aversion,
                        delta_cap_quantile=delta_cap,
                        solver_backend=solver_backend,
                    ),
                )

        econ_risks = _round_grid(
            [0.15625 + 0.000125 * idx for idx in range(9)],
            lo=0.12,
            hi=0.22,
        )
        econ_gammas = _round_grid(
            [0.400 + 0.005 * idx for idx in range(10)],
            lo=0.0,
            hi=1.0,
        )
        econ_aversions = [0.125, 0.1375, 0.15]
        for risk, gamma, aversion, tail_focus in product(
            econ_risks,
            econ_gammas,
            econ_aversions,
            [0.90, 0.925, 0.95, 1.0],
        ):
            _add_candidate(
                rows,
                seen,
                family="claim_micro_ext_economic_endpoint",
                anchor_rank=96,
                source_reason="candidate2122_economic_endpoint_extension",
                policy=_policy_base(
                    risk_tolerance=risk,
                    policy_mode="tail_blended_uncertainty",
                    gamma=gamma,
                    uncertainty_aversion=aversion,
                    tail_focus_quantile=tail_focus,
                    solver_backend=solver_backend,
                ),
            )

        candidates = pd.DataFrame(rows).reset_index(drop=True)
        candidates.insert(0, "local_candidate_id", range(1, len(candidates) + 1))
        return candidates

    if profile == "claim_bound_closure":
        # Final IJDS bound-endpoint closure. The completed claim_micro_ext run
        # found a monotone-looking cap reduction up to gamma=0.65, while
        # uncertainty_aversion was already mostly saturated. This tiny extension
        # tests only whether the lower-bound endpoint can move; it is not a new
        # body-policy or economic-endpoint search.
        closure_risks = _round_grid(
            [0.1685 + 0.00025 * idx for idx in range(10)],
            lo=0.14,
            hi=0.24,
        )
        closure_gammas = _round_grid(
            [0.65 + 0.01 * idx for idx in range(11)],
            lo=0.0,
            hi=1.0,
        )
        closure_aversions = [0.25, 0.275, 0.30, 0.325, 0.35]
        for risk, gamma, aversion, mode in product(
            closure_risks,
            closure_gammas,
            closure_aversions,
            ["blended_uncertainty", "capped_blended_uncertainty"],
        ):
            delta_values = [1.0] if mode == "blended_uncertainty" else [0.95, 1.0]
            for delta_cap in delta_values:
                _add_candidate(
                    rows,
                    seen,
                    family="claim_bound_closure_low_cap",
                    anchor_rank=219,
                    source_reason="micro_ext_min_markov_cap_endpoint_closure",
                    policy=_policy_base(
                        risk_tolerance=risk,
                        policy_mode=mode,
                        gamma=gamma,
                        uncertainty_aversion=aversion,
                        delta_cap_quantile=delta_cap,
                        solver_backend=solver_backend,
                    ),
                )

        candidates = pd.DataFrame(rows).reset_index(drop=True)
        candidates.insert(0, "local_candidate_id", range(1, len(candidates) + 1))
        return candidates

    if profile == "claim_bound_floor_closure":
        # Last bounded IJDS endpoint check: the completed bound closure lowered
        # the Markov cap to 0.298369 at the grid boundary (low tau, high gamma,
        # high aversion) while still preserving a positive return-floor surplus.
        # This profile tests whether the appendix/theory endpoint can cross the
        # cleaner cap<0.29 threshold; it should not be used to replace the paper
        # body/default policy.
        floor_risks = _round_grid(
            [0.16775 + 0.000125 * idx for idx in range(13)],
            lo=0.14,
            hi=0.24,
        )
        floor_gammas = _round_grid(
            [0.75 + 0.01 * idx for idx in range(10)],
            lo=0.0,
            hi=1.0,
        )
        floor_aversions = [0.325, 0.35, 0.375, 0.40, 0.425, 0.45]
        for risk, gamma, aversion, mode in product(
            floor_risks,
            floor_gammas,
            floor_aversions,
            ["blended_uncertainty", "capped_blended_uncertainty"],
        ):
            delta_values = [1.0] if mode == "blended_uncertainty" else [0.95, 1.0]
            for delta_cap in delta_values:
                _add_candidate(
                    rows,
                    seen,
                    family="claim_bound_floor_closure_low_cap",
                    anchor_rank=219,
                    source_reason="bound_closure_cap029_floor_threshold",
                    policy=_policy_base(
                        risk_tolerance=risk,
                        policy_mode=mode,
                        gamma=gamma,
                        uncertainty_aversion=aversion,
                        delta_cap_quantile=delta_cap,
                        solver_backend=solver_backend,
                    ),
                )

        candidates = pd.DataFrame(rows).reset_index(drop=True)
        candidates.insert(0, "local_candidate_id", range(1, len(candidates) + 1))
        return candidates

    if profile == "claim_bound_terminal":
        # Terminal IJDS endpoint search. This is intentionally wider than the
        # prior closures, but still only targets the final bound-tight endpoint:
        # cap<0.285/0.280/0.275 if feasible, with positive return-floor surplus.
        # It should not be used to replace the body/default or economic endpoint.
        ultra_risks = _round_grid(
            [0.16675 + 0.000125 * idx for idx in range(29)],
            lo=0.14,
            hi=0.24,
        )
        ultra_gammas = _round_grid(
            [0.84 + 0.005 * idx for idx in range(31)],
            lo=0.0,
            hi=1.0,
        )
        ultra_aversions = [0.40, 0.425, 0.45, 0.475, 0.50, 0.55, 0.60, 0.65, 0.70]
        for risk, gamma, aversion, mode in product(
            ultra_risks,
            ultra_gammas,
            ultra_aversions,
            ["blended_uncertainty", "capped_blended_uncertainty"],
        ):
            delta_values = [1.0] if mode == "blended_uncertainty" else [0.95, 1.0]
            for delta_cap in delta_values:
                _add_candidate(
                    rows,
                    seen,
                    family="claim_bound_terminal_ultra_low_cap",
                    anchor_rank=219,
                    source_reason="terminal_cap_threshold_search",
                    policy=_policy_base(
                        risk_tolerance=risk,
                        policy_mode=mode,
                        gamma=gamma,
                        uncertainty_aversion=aversion,
                        delta_cap_quantile=delta_cap,
                        solver_backend=solver_backend,
                    ),
                )

        recovery_risks = _round_grid(
            [0.1680 + 0.000125 * idx for idx in range(29)],
            lo=0.14,
            hi=0.24,
        )
        recovery_gammas = _round_grid(
            [0.80 + 0.005 * idx for idx in range(25)],
            lo=0.0,
            hi=1.0,
        )
        recovery_aversions = [0.35, 0.375, 0.40, 0.425, 0.45, 0.475, 0.50, 0.55, 0.60]
        for risk, gamma, aversion, mode in product(
            recovery_risks,
            recovery_gammas,
            recovery_aversions,
            ["blended_uncertainty", "capped_blended_uncertainty"],
        ):
            delta_values = [1.0] if mode == "blended_uncertainty" else [0.95, 1.0]
            for delta_cap in delta_values:
                _add_candidate(
                    rows,
                    seen,
                    family="claim_bound_terminal_return_recovery",
                    anchor_rank=219,
                    source_reason="terminal_best_return_under_low_cap",
                    policy=_policy_base(
                        risk_tolerance=risk,
                        policy_mode=mode,
                        gamma=gamma,
                        uncertainty_aversion=aversion,
                        delta_cap_quantile=delta_cap,
                        solver_backend=solver_backend,
                    ),
                )

        candidates = pd.DataFrame(rows).reset_index(drop=True)
        candidates.insert(0, "local_candidate_id", range(1, len(candidates) + 1))
        return candidates

    if 96 in anchor_by_rank:
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
            gamma_offsets = [
                -0.075,
                -0.05,
                -0.035,
                -0.025,
                -0.01,
                0.0,
                0.01,
                0.025,
                0.035,
                0.05,
                0.075,
            ]
            aversions = [0.025, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20]
        risks = _round_grid(
            [float(base.risk_tolerance) + x for x in risk_offsets], lo=0.12, hi=0.22
        )
        gammas = _round_grid([float(base.gamma) + x for x in gamma_offsets], lo=0.0, hi=1.0)

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

        tail_risks = risks[1:-1] if len(risks) > 2 else risks
        tail_gammas = gammas[1:-1] if len(gammas) > 2 else gammas
        tail_focus_values = [0.95, 1.0] if profile == "stage1" else [0.90, 0.95, 1.0]
        tail_aversions = [0.075, 0.10, 0.125] if profile == "stage1" else aversions
        for risk, gamma, aversion, tail_focus in product(
            tail_risks, tail_gammas, tail_aversions, tail_focus_values
        ):
            _add_candidate(
                rows,
                seen,
                family="max_return_tail_local",
                anchor_rank=96,
                source_reason="rank96_tail_sensitivity",
                policy=_policy_base(
                    risk_tolerance=risk,
                    policy_mode="tail_blended_uncertainty",
                    gamma=gamma,
                    uncertainty_aversion=aversion,
                    tail_focus_quantile=tail_focus,
                    solver_backend=solver_backend,
                ),
            )

    bound_risk_centers = []
    bound_gamma_centers = []
    for rank in (219, 223):
        if rank in anchor_by_rank:
            row = anchor_by_rank[rank]
            bound_risk_centers.append(float(row.risk_tolerance))
            bound_gamma_centers.append(float(row.gamma))
    if bound_risk_centers:
        risk_offsets = [-0.0075, -0.005, -0.0025, 0.0, 0.0025, 0.005]
        gamma_offsets = [-0.05, -0.025, 0.0, 0.025, 0.05]
        aversions = [0.05, 0.075, 0.10, 0.125, 0.15]
        if profile == "expanded":
            risk_offsets = [-0.01, -0.0075, -0.005, -0.0025, 0.0, 0.0025, 0.005, 0.0075, 0.01]
            gamma_offsets = [-0.075, -0.05, -0.025, -0.01, 0.0, 0.01, 0.025, 0.05, 0.075]
            aversions = [0.025, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20]
        risks = _round_grid(
            [center + offset for center in bound_risk_centers for offset in risk_offsets],
            lo=0.14,
            hi=0.24,
        )
        gammas = _round_grid(
            [center + offset for center in bound_gamma_centers for offset in gamma_offsets],
            lo=0.0,
            hi=1.0,
        )
        for risk, gamma, aversion, mode in product(
            risks,
            gammas,
            aversions,
            ["blended_uncertainty", "capped_blended_uncertainty"],
        ):
            delta_values = [1.0]
            if mode == "capped_blended_uncertainty" and profile == "expanded":
                delta_values = [0.90, 1.0]
            for delta_cap in delta_values:
                _add_candidate(
                    rows,
                    seen,
                    family="bound_efficient_local",
                    anchor_rank=219 if abs(gamma - 0.45) <= abs(gamma - 0.40) else 223,
                    source_reason="rank219_rank223_bound_frontier",
                    policy=_policy_base(
                        risk_tolerance=risk,
                        policy_mode=mode,
                        gamma=gamma,
                        uncertainty_aversion=aversion,
                        delta_cap_quantile=delta_cap,
                        solver_backend=solver_backend,
                    ),
                )

    if profile == "claim_expanded":
        # Densify only the claim-bearing neighborhoods discovered by stage1:
        # the low-cap return-bound ridge around local candidates 462/466 and
        # the economic frontier endpoint around local candidate 264.
        bound_risks = _round_grid(
            [0.1705 + 0.0005 * idx for idx in range(10)] + [0.1750],
            lo=0.14,
            hi=0.24,
        )
        bound_gammas = _round_grid(
            [0.49, 0.50, 0.51, 0.52, 0.535, 0.55, 0.575],
            lo=0.0,
            hi=1.0,
        )
        bound_aversions = [0.05, 0.075, 0.10, 0.1125, 0.125, 0.1375, 0.15, 0.175]
        for risk, gamma, aversion, mode in product(
            bound_risks,
            bound_gammas,
            bound_aversions,
            ["blended_uncertainty", "capped_blended_uncertainty"],
        ):
            delta_values = [1.0] if mode == "blended_uncertainty" else [0.95, 1.0]
            for delta_cap in delta_values:
                _add_candidate(
                    rows,
                    seen,
                    family="bound_claim_refined_local",
                    anchor_rank=219,
                    source_reason="candidate462_466_return_bound_ridge",
                    policy=_policy_base(
                        risk_tolerance=risk,
                        policy_mode=mode,
                        gamma=gamma,
                        uncertainty_aversion=aversion,
                        delta_cap_quantile=delta_cap,
                        solver_backend=solver_backend,
                    ),
                )

        return_risks = _round_grid(
            [0.1560 + 0.0005 * idx for idx in range(9)],
            lo=0.12,
            hi=0.22,
        )
        return_gammas = _round_grid(
            [0.44, 0.45, 0.46, 0.47, 0.475, 0.485, 0.495],
            lo=0.0,
            hi=1.0,
        )
        return_aversions = [0.10, 0.1125, 0.125, 0.1375, 0.15]
        for risk, gamma, aversion, tail_focus in product(
            return_risks,
            return_gammas,
            return_aversions,
            [0.95, 1.0],
        ):
            _add_candidate(
                rows,
                seen,
                family="max_return_claim_refined_local",
                anchor_rank=96,
                source_reason="candidate264_economic_frontier_endpoint",
                policy=_policy_base(
                    risk_tolerance=risk,
                    policy_mode="tail_blended_uncertainty",
                    gamma=gamma,
                    uncertainty_aversion=aversion,
                    tail_focus_quantile=tail_focus,
                    solver_backend=solver_backend,
                ),
            )

    candidates = pd.DataFrame(rows).reset_index(drop=True)
    candidates.insert(0, "local_candidate_id", range(1, len(candidates) + 1))
    return candidates


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
    if "allocation_vector" in solution:
        alloc = np.asarray(solution["allocation_vector"], dtype=float)
    else:
        alloc = np.array(
            [float(solution["allocation"].get(i, 0.0)) for i in range(len(aligned))],
            dtype=float,
        )
    total_allocated = float(np.sum(alloc * loan_amounts))
    weights = (alloc * loan_amounts) / max(total_allocated, 1e-6)
    funded_mask = weights > 1e-8
    miscoverage = (y_true > pd_high).astype(float)
    weighted_miscoverage_v = float(np.sum(weights * miscoverage))
    weighted_pd_true = float(np.sum(weights * y_true))
    violation = max(0.0, weighted_pd_true - float(policy["risk_tolerance"]))
    sqrt_alpha = float(np.sqrt(alpha))
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

    return {
        "alpha": float(alpha),
        "confidence": float(1.0 - alpha),
        "gamma_cp": round(float(np.sum(weights * np.clip(pd_high - pd_point, 0.0, 1.0))), 6),
        "n_funded": int(solution.get("n_funded", int(np.sum(alloc > 0.01)))),
        "total_allocated": round(total_allocated, 2),
        "objective_value": round(float(solution.get("objective_value", 0.0)), 6),
        "expected_return_gross": round(expected_return_gross, 6),
        "expected_loss_point": round(expected_loss_point, 6),
        "expected_return_net_point": round(expected_return_net_point, 6),
        "realized_total_return": round(realized_total_return, 6),
        "weighted_pd_true": round(weighted_pd_true, 6),
        "weighted_pd_constraint_used": round(float(np.sum(weights * effective_pd)), 6),
        "weighted_pd_high": round(float(np.sum(weights * pd_high)), 6),
        "weighted_pd_point": round(float(np.sum(weights * pd_point)), 6),
        "worst_case_pd": round(float(np.sum(weights * pd_high)), 6),
        "point_pd": round(float(np.sum(weights * pd_point)), 6),
        "tau": float(policy["risk_tolerance"]),
        "violation": round(violation, 6),
        "weighted_miscoverage_V": round(weighted_miscoverage_v, 6),
        "sqrt_alpha": round(sqrt_alpha, 6),
        "empirical_coverage_funded": round(
            float(1.0 - miscoverage[funded_mask].mean()) if funded_mask.any() else float("nan"),
            4,
        ),
        "bound_a_expected_violation_leq_alpha": bool(violation <= alpha + 1e-8),
        "bound_b_prob_violation_gt_t": round(float(min(1.0, alpha / max(t_eval, 1e-8))), 4),
        "bound_b_t_eval": float(t_eval),
        "bound_b_is_vacuous": bool(min(1.0, alpha / max(t_eval, 1e-8)) >= 1.0),
        "bound_c_V_leq_sqrt_alpha": bool(sqrt_alpha + 1e-8 >= weighted_miscoverage_v),
        "all_bounds_hold": bool(
            (violation <= alpha + 1e-8) and (sqrt_alpha + 1e-8 >= weighted_miscoverage_v)
        ),
        "allocator_mode": "exact",
        "solver_status": str(solution.get("solver_status", "unknown")),
        "allocator_solver_backend": str(solution.get("solver_backend", policy["solver_backend"])),
        "allocator_native_solver_error": str(solution.get("native_solver_error", "")),
        "pd_cap_slack": round(pd_cap_slack, 6),
    }


def _aggregate_leaderboard(candidates: pd.DataFrame, bound_eval: pd.DataFrame) -> pd.DataFrame:
    if bound_eval.empty:
        return candidates.copy()
    grouped = bound_eval.groupby("local_candidate_id", dropna=False)
    agg = grouped.agg(
        alpha_exact_pass_count=("all_bounds_hold", "sum"),
        alpha_exact_check_count=("all_bounds_hold", "size"),
        alpha_exact_pass_rate=("all_bounds_hold", "mean"),
        alpha_max_violation=("violation", "max"),
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
            alpha01_weighted_miscoverage_V=("weighted_miscoverage_V", "mean"),
            alpha01_violation=("violation", "max"),
            alpha01_weighted_pd_true=("weighted_pd_true", "mean"),
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
    alpha01_gamma = pd.to_numeric(work["alpha01_gamma_cp"], errors="coerce")
    risk = pd.to_numeric(work["risk_tolerance"], errors="coerce")
    gamma = pd.to_numeric(work["gamma"], errors="coerce")
    work["alpha01_endpoint_budget_upper"] = risk + (1.0 - gamma) * alpha01_gamma
    work["alpha01_markov_loss_cap"] = work["alpha01_endpoint_budget_upper"] + float(np.sqrt(0.01))
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
    work.insert(0, "claim_rank", range(1, len(work) + 1))
    return work


def _claim_summary(
    leaderboard: pd.DataFrame,
    bound_eval: pd.DataFrame,
    *,
    alpha_grid: list[float] | None = None,
) -> dict[str, Any]:
    leaderboard = leaderboard.copy()
    if "alpha01_endpoint_budget_upper" not in leaderboard.columns:
        alpha01_gamma = pd.to_numeric(leaderboard["alpha01_gamma_cp"], errors="coerce")
        risk = pd.to_numeric(leaderboard["risk_tolerance"], errors="coerce")
        gamma = pd.to_numeric(leaderboard["gamma"], errors="coerce")
        leaderboard["alpha01_endpoint_budget_upper"] = risk + (1.0 - gamma) * alpha01_gamma
    if "alpha01_markov_loss_cap" not in leaderboard.columns:
        leaderboard["alpha01_markov_loss_cap"] = pd.to_numeric(
            leaderboard["alpha01_endpoint_budget_upper"], errors="coerce"
        ) + float(np.sqrt(0.01))
    eligible = leaderboard[
        leaderboard["alpha01_exact_pass"].fillna(False).astype(bool)
        & leaderboard["all_alpha_pass"].fillna(False).astype(bool)
    ].copy()
    if "return_floor_surplus" not in leaderboard.columns:
        if "champion_return_surplus" in leaderboard.columns:
            leaderboard["return_floor_surplus"] = leaderboard["champion_return_surplus"]
        else:
            leaderboard["return_floor_surplus"] = (
                leaderboard["alpha01_realized_total_return"].fillna(float("-inf"))
                - DECLARED_RETURN_FLOOR
            )
    above_return_floor = eligible[
        eligible["alpha01_realized_total_return"] >= DECLARED_RETURN_FLOOR
    ].copy()

    def row_payload(frame: pd.DataFrame) -> dict[str, Any] | None:
        if frame.empty:
            return None
        row = frame.iloc[0]
        fields = [
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
            "alpha01_weighted_miscoverage_V",
            "alpha01_endpoint_budget_upper",
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
        ]
        return {
            field: row[field].item() if hasattr(row[field], "item") else row[field]
            for field in fields
            if field in row.index
        }

    max_return = row_payload(eligible.sort_values("alpha01_realized_total_return", ascending=False))
    best_gamma = row_payload(
        above_return_floor.sort_values(
            ["alpha01_gamma_cp", "alpha01_realized_total_return"],
            ascending=[True, False],
        )
    )
    best_v = row_payload(
        above_return_floor.sort_values(
            ["alpha01_weighted_miscoverage_V", "alpha01_realized_total_return"],
            ascending=[True, False],
        )
    )
    balanced = above_return_floor.copy()
    if not balanced.empty:
        for source, target, higher_better in [
            ("alpha01_realized_total_return", "return_score", True),
            ("alpha01_markov_loss_cap", "bound_score", False),
            ("alpha01_weighted_miscoverage_V", "v_score", False),
        ]:
            vals = pd.to_numeric(balanced[source], errors="coerce")
            lo, hi = float(vals.min()), float(vals.max())
            if hi <= lo:
                balanced[target] = 1.0
            elif higher_better:
                balanced[target] = (vals - lo) / (hi - lo)
            else:
                balanced[target] = (hi - vals) / (hi - lo)
        balanced["ijds_balanced_score"] = (
            0.40 * balanced["return_score"]
            + 0.40 * balanced["bound_score"]
            + 0.20 * balanced["v_score"]
        )
    balanced_claim = row_payload(
        balanced.sort_values("ijds_balanced_score", ascending=False)
        if not balanced.empty
        else balanced
    )

    by_family: dict[str, Any] = {}
    if not leaderboard.empty:
        for family, frame in leaderboard.groupby("local_family", dropna=False):
            fam_eligible = frame[
                frame["alpha01_exact_pass"].fillna(False).astype(bool)
                & frame["all_alpha_pass"].fillna(False).astype(bool)
            ]
            by_family[str(family)] = {
                "n_policies": int(len(frame)),
                "n_all_alpha_passers": int(len(fam_eligible)),
                "all_alpha_pass_rate": float(len(fam_eligible) / max(len(frame), 1)),
                "best_return": float(fam_eligible["alpha01_realized_total_return"].max())
                if not fam_eligible.empty
                else None,
                "min_gamma_cp_above_return_floor": float(
                    fam_eligible.loc[
                        fam_eligible["alpha01_realized_total_return"] >= DECLARED_RETURN_FLOOR,
                        "alpha01_gamma_cp",
                    ].min()
                )
                if not fam_eligible[
                    fam_eligible["alpha01_realized_total_return"] >= DECLARED_RETURN_FLOOR
                ].empty
                else None,
                "min_v_above_return_floor": float(
                    fam_eligible.loc[
                        fam_eligible["alpha01_realized_total_return"] >= DECLARED_RETURN_FLOOR,
                        "alpha01_weighted_miscoverage_V",
                    ].min()
                )
                if not fam_eligible[
                    fam_eligible["alpha01_realized_total_return"] >= DECLARED_RETURN_FLOOR
                ].empty
                else None,
            }

    by_alpha: dict[str, Any] = {}
    if not bound_eval.empty:
        for alpha, frame in bound_eval.groupby("alpha", dropna=False):
            by_alpha[str(float(alpha))] = {
                "n_checks": int(len(frame)),
                "pass_rate": float(frame["all_bounds_hold"].fillna(False).mean()),
                "max_violation": float(frame["violation"].max()),
                "mean_gamma_cp": float(frame["gamma_cp"].mean()),
                "mean_weighted_miscoverage_V": float(frame["weighted_miscoverage_V"].mean()),
            }

    alpha_values = (
        [float(value) for value in alpha_grid]
        if alpha_grid is not None
        else sorted(float(value) for value in bound_eval["alpha"].dropna().unique())
        if "alpha" in bound_eval
        else list(DEFAULT_ALPHA_GRID)
    )
    alpha_values = sorted(dict.fromkeys(alpha_values))
    finite_grid_policy = {
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
    claim_selection_protocol = {
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

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "declared_return_floor": DECLARED_RETURN_FLOOR,
        "finite_grid_policy": finite_grid_policy,
        "claim_selection_protocol": claim_selection_protocol,
        "n_policies": int(len(leaderboard)),
        "n_all_alpha_passers": int(len(eligible)),
        "n_all_alpha_passers_above_return_floor": int(len(above_return_floor)),
        "max_return_claim": max_return,
        "best_gamma_cp_return_floor_claim": best_gamma,
        "best_weighted_miscoverage_return_floor_claim": best_v,
        "balanced_return_bound_claim": balanced_claim,
        "by_family": by_family,
        "by_alpha": by_alpha,
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


def main(argv: list[str] | None = None) -> int:
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
    args = parser.parse_args(argv)

    run_tag = str(args.run_tag).strip().replace("/", "_")
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
    output_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = model_dir / "runtime_checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    status_path = model_dir / "runtime_status.json"
    candidates_path = output_dir / "pool93_ijds_local_refinement_candidates.parquet"
    bound_eval_path = output_dir / "pool93_ijds_local_refinement_bound_eval.parquet"
    leaderboard_path = output_dir / "pool93_ijds_local_refinement_leaderboard.parquet"
    claim_summary_path = model_dir / "pool93_ijds_local_refinement_claim_summary.json"
    manifest_path = model_dir / "pool93_ijds_local_refinement_manifest.json"

    source_bound_eval = Path(args.source_bound_eval)
    source_selection = Path(args.source_selection)
    source_selection_payload = json.loads(source_selection.read_text(encoding="utf-8"))
    conformal_intervals_path = str(args.conformal_intervals_path).strip() or str(
        ROOT / source_selection_payload["conformal_intervals_path"]
    )
    alpha_grid = _coerce_float_grid(args.alpha_grid, DEFAULT_ALPHA_GRID)
    anchor_ranks = _coerce_int_grid(args.anchor_ranks, [96, 219, 223])

    if candidates_path.exists():
        candidates = pd.read_parquet(candidates_path)
        logger.info("Reusing candidate manifest: {} rows from {}", len(candidates), candidates_path)
    else:
        anchors = _source_anchor_rows(source_bound_eval, anchor_ranks)
        candidates = _generate_candidate_grid(
            anchors,
            profile=str(args.profile),
            solver_backend=str(args.solver_backend),
        )
        if int(args.candidate_limit) > 0:
            candidates = candidates.head(int(args.candidate_limit)).copy().reset_index(drop=True)
            candidates["local_candidate_id"] = range(1, len(candidates) + 1)
        atomic_write_parquet(candidates, candidates_path, index=False)
        logger.info("Wrote candidate manifest: {} policies to {}", len(candidates), candidates_path)

    manifest = {
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
        "candidates_path": str(candidates_path),
        "bound_eval_path": str(bound_eval_path),
        "leaderboard_path": str(leaderboard_path),
        "claim_summary_path": str(claim_summary_path),
    }
    atomic_write_json(manifest_path, manifest)

    partial = pd.DataFrame()
    if bound_eval_path.exists():
        partial = pd.read_parquet(bound_eval_path)
        if not partial.empty:
            partial = partial.drop_duplicates(
                ["local_candidate_id", "alpha"],
                keep="last",
            ).reset_index(drop=True)
            logger.info("Resuming local refinement from {} rows", len(partial))
    completed_keys = set()
    if not partial.empty:
        completed_keys = {
            (int(row.local_candidate_id), float(row.alpha))
            for row in partial.itertuples(index=False)
        }
    rows: list[dict[str, Any]] = partial.to_dict(orient="records") if not partial.empty else []

    total_checks = int(len(candidates) * len(alpha_grid))
    start = time.monotonic()
    initial_completed = int(len(completed_keys))
    _write_status(
        run_tag=run_tag,
        status_path=status_path,
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

    def persist_progress() -> None:
        bound_eval = pd.DataFrame(rows)
        atomic_write_parquet(bound_eval, bound_eval_path, index=False)
        leaderboard = _aggregate_leaderboard(candidates, bound_eval)
        atomic_write_parquet(leaderboard, leaderboard_path, index=False)
        atomic_write_json(
            claim_summary_path,
            _claim_summary(leaderboard, bound_eval, alpha_grid=alpha_grid),
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
            status_path=status_path,
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

    completed = len(completed_keys)
    pending_tasks: list[tuple[dict[str, Any], float]] = []
    for candidate in candidates.to_dict(orient="records"):
        for alpha in alpha_grid:
            key = (int(candidate["local_candidate_id"]), float(alpha))
            if key not in completed_keys:
                pending_tasks.append((candidate, float(alpha)))

    parallel_workers = max(1, int(args.parallel_workers))
    if parallel_workers <= 1:
        for candidate, alpha in pending_tasks:
            policy = {field: candidate[field] for field in SEMANTIC_POLICY_FIELDS}
            result = _exact_policy_alpha(
                aligned,
                policy=policy,
                alpha=float(alpha),
                budget=float(args.budget),
                t_eval=float(args.t_eval),
                threads=int(args.exact_threads),
            )
            record_result(candidate, alpha, result)
    else:
        logger.info(
            "Running exact refinement with {} parallel workers and {} solver thread(s) per worker",
            parallel_workers,
            int(args.exact_threads),
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
                        float(args.budget),
                        float(args.t_eval),
                        int(args.exact_threads),
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

    bound_eval = pd.DataFrame(rows)
    atomic_write_parquet(bound_eval, bound_eval_path, index=False)
    leaderboard = _aggregate_leaderboard(candidates, bound_eval)
    atomic_write_parquet(leaderboard, leaderboard_path, index=False)
    claim_summary = _claim_summary(leaderboard, bound_eval, alpha_grid=alpha_grid)
    atomic_write_json(claim_summary_path, claim_summary)

    _write_status(
        run_tag=run_tag,
        status_path=status_path,
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
            "claim_summary_path": str(claim_summary_path),
            "leaderboard_path": str(leaderboard_path),
        },
    )
    write_runtime_checkpoint(
        STAGE_NAME,
        "selection_complete",
        {
            "run_tag": run_tag,
            "completed_at_utc": datetime.now(tz=UTC).isoformat(),
            "claim_summary_path": str(claim_summary_path),
            "leaderboard_path": str(leaderboard_path),
        },
        checkpoint_dir=checkpoint_dir,
    )
    logger.info("Local IJDS refinement complete: {}", claim_summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
