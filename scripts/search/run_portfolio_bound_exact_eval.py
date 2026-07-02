"""Exact bound reranking helper for bound-aware portfolio search."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.search.run_portfolio_bound_aware_search import (  # noqa: E402
    SCHEMA_VERSION,
    STAGE_NAME,
    _aggregate_exact_results,
    _policy_from_row,
    _region_summary,
    _resource_snapshot,
    _selection_reason,
)
from scripts.validate_alpha_gamma_bound import (  # noqa: E402
    DEFAULT_THREADS,
    _load_aligned_dataset,
    _validate_single_alpha,
)
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    load_runtime_status,
    write_runtime_checkpoint,
    write_runtime_status,
)

CONTEXT_PATH_KEYS = (
    "conformal_intervals_path",
    "frontier_raw_path",
    "frontier_path",
    "shortlist_path",
    "shortlist_exact_path",
    "bound_eval_path",
    "region_summary_path",
    "selection_path",
    "runtime_status_path",
    "runtime_checkpoint_dir",
    "resource_snapshot_path",
)


def _resolve_repo_path(raw_path: object) -> Path:
    path_text = str(raw_path)
    path = Path(path_text)
    if path.is_absolute():
        return path
    return ROOT / path


def _repo_relative(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _shortlist_exact_path(context: dict[str, object]) -> Path:
    return Path(str(context.get("shortlist_exact_path", context["shortlist_path"])))


def _normalize_context_paths(context: dict[str, object]) -> None:
    for key in CONTEXT_PATH_KEYS:
        if key in context:
            context[key] = str(_resolve_repo_path(context[key]))


def _eta_seconds(elapsed_sec: float, completed: int, total: int) -> float | None:
    if completed <= 0 or total <= 0 or completed >= total:
        return 0.0 if total > 0 and completed >= total else None
    return (elapsed_sec / max(completed, 1)) * max(total - completed, 0)


def _load_completed_bound_eval(
    *,
    bound_eval_path: Path,
    expected_checks: int,
) -> pd.DataFrame | None:
    if not bound_eval_path.exists():
        return None
    bound_eval = pd.read_parquet(bound_eval_path)
    required_cols = {"alpha", "all_bounds_hold", "gamma_cp", "weighted_miscoverage_V"}
    if len(bound_eval) != expected_checks or not required_cols.issubset(bound_eval.columns):
        logger.warning(
            "Ignoring incomplete bound_eval cache at {}: rows={} expected={}",
            bound_eval_path,
            len(bound_eval),
            expected_checks,
        )
        return None
    logger.info(
        "Reusing completed exact bound cache: {} ({} rows)",
        bound_eval_path,
        len(bound_eval),
    )
    return bound_eval


def _load_partial_bound_eval(*, bound_eval_path: Path) -> pd.DataFrame:
    if not bound_eval_path.exists():
        return pd.DataFrame()
    try:
        bound_eval = pd.read_parquet(bound_eval_path)
    except Exception as exc:  # pragma: no cover - defensive resume guard
        logger.warning("Unable to reuse partial bound_eval cache at {}: {}", bound_eval_path, exc)
        return pd.DataFrame()
    required_cols = {"candidate_rank", "eval_random_state", "alpha", "all_bounds_hold"}
    if bound_eval.empty or not required_cols.issubset(bound_eval.columns):
        return pd.DataFrame()
    if "allocator_solver_backend" not in bound_eval.columns and "solver_status" in bound_eval.columns:
        status = bound_eval["solver_status"].astype(str)
        bound_eval["allocator_solver_backend"] = status.map(
            lambda value: "highspy_fallback_highs_sparse"
            if value == "optimal"
            else "highspy"
        )
    if "allocator_native_solver_error" not in bound_eval.columns:
        bound_eval["allocator_native_solver_error"] = ""
    before = len(bound_eval)
    bound_eval = bound_eval.drop_duplicates(
        subset=["candidate_rank", "eval_random_state", "alpha"],
        keep="last",
    ).reset_index(drop=True)
    logger.info(
        "Resuming exact bound cache: {} usable rows ({} raw)",
        len(bound_eval),
        before,
    )
    return bound_eval


def _context_random_states(context: dict[str, object]) -> list[int]:
    raw = context.get("exact_random_states", context["random_states"])
    if isinstance(raw, str):
        values = [part.strip() for part in raw.split(",") if part.strip()]
    else:
        values = list(raw)  # type: ignore[arg-type]
    return [int(v) for v in values]


def _context_max_candidates(context: dict[str, object]) -> int:
    return int(context.get("exact_max_candidates", context["max_candidates"]))


def _context_exact_threads(context: dict[str, object]) -> int:
    raw = os.environ.get("EXACT_THREADS", context.get("exact_threads", DEFAULT_THREADS))
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return DEFAULT_THREADS


def _validate_alpha_grid_supported(alpha_grid: list[float]) -> None:
    sweep_path = ROOT / "data" / "processed" / "alpha_sweep_pareto_mondrian.parquet"
    if not sweep_path.exists():
        logger.warning(
            "Alpha sweep artifact not found at {}; exact rerank cannot verify alpha support.",
            sweep_path,
        )
        return
    sweep = pd.read_parquet(sweep_path, columns=["alpha"])
    supported = [float(value) for value in sweep["alpha"].dropna().unique()]
    missing = [
        float(alpha)
        for alpha in alpha_grid
        if not any(abs(float(alpha) - candidate) <= 1e-9 for candidate in supported)
    ]
    if missing:
        raise ValueError(
            "Exact bound alpha_grid contains values absent from "
            f"{_repo_relative(sweep_path)}: {missing}. Supported values are {sorted(supported)}."
        )


def _as_float(value: Any) -> float:
    return float(value)


def _as_int(value: Any) -> int:
    return int(value)


def _write_exact_status(
    *,
    context: dict[str, object],
    base_elapsed_sec: float,
    bound_completed_checks: int,
    state: str,
    phase: str,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    started = _as_float(context["helper_started_monotonic"])
    frontier_total = _as_int(context["frontier_total_units"])
    frontier_completed = _as_int(context["frontier_completed_units"])
    bound_total = _as_int(context["bound_total_checks"])
    resume_completed = int(context.get("resume_completed_checks", 0) or 0)
    exact_elapsed_sec = time.monotonic() - started
    elapsed_sec = base_elapsed_sec + exact_elapsed_sec
    global_total = frontier_total + bound_total
    global_completed = frontier_completed + bound_completed_checks
    completed_since_resume = max(0, int(bound_completed_checks) - resume_completed)
    remaining_checks = max(0, int(bound_total) - int(bound_completed_checks))
    exact_eta_sec = (
        (exact_elapsed_sec / completed_since_resume) * remaining_checks
        if completed_since_resume > 0 and remaining_checks > 0
        else (0.0 if remaining_checks == 0 else None)
    )
    payload: dict[str, object] = {
        "frontier_total_units": frontier_total,
        "frontier_completed_units": frontier_completed,
        "frontier_pct_complete": float(frontier_completed / max(frontier_total, 1))
        if frontier_total > 0
        else 1.0,
        "bound_total_checks": bound_total,
        "bound_completed_checks": int(bound_completed_checks),
        "bound_pct_complete": float(bound_completed_checks / max(bound_total, 1))
        if bound_total > 0
        else 0.0,
        "global_total_units": global_total,
        "global_completed_units": global_completed,
        "global_pct_complete": float(global_completed / max(global_total, 1))
        if global_total > 0
        else 1.0,
        "elapsed_sec": float(elapsed_sec),
        "exact_elapsed_sec": float(exact_elapsed_sec),
        "exact_eta_sec": exact_eta_sec,
        "eta_sec": exact_eta_sec,
        "eta_method": "exact_bound_only",
        "resume_completed_checks": int(resume_completed),
        "completed_since_resume": int(completed_since_resume),
    }
    if extra:
        payload.update(extra)
    write_runtime_status(
        STAGE_NAME,
        phase=phase,
        state=state,
        run_tag=str(context["run_label"]),
        status_path=str(context["runtime_status_path"]),
        extra=payload,
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context-path", required=True)
    args = parser.parse_args(argv)

    context_path = Path(args.context_path).resolve()
    context = json.loads(context_path.read_text(encoding="utf-8"))
    _normalize_context_paths(context)
    status_path = Path(str(context["runtime_status_path"]))
    checkpoint_dir = Path(str(context["runtime_checkpoint_dir"]))
    resource_snapshot_path = Path(str(context["resource_snapshot_path"]))
    shortlist_path = Path(str(context["shortlist_path"]))
    shortlist_exact_path = _shortlist_exact_path(context)
    bound_eval_path = Path(str(context["bound_eval_path"]))
    selection_path = Path(str(context["selection_path"]))

    prior_status = load_runtime_status(status_path)
    base_elapsed_sec = (
        float(prior_status.get("elapsed_sec", 0.0))
        if prior_status.get("phase") == "frontier_complete"
        else 0.0
    )
    context["frontier_total_units"] = int(prior_status.get("frontier_total_units", 0))
    context["frontier_completed_units"] = int(prior_status.get("frontier_completed_units", 0))
    context["bound_total_checks"] = int(prior_status.get("bound_total_checks", 0))
    context["helper_started_monotonic"] = time.monotonic()

    shortlist = pd.read_parquet(shortlist_path)
    alpha_grid = [float(v) for v in context["alpha_grid"]]
    _validate_alpha_grid_supported(alpha_grid)
    exact_max_candidates = _context_max_candidates(context)
    requested_random_states_raw = context.get("requested_exact_random_states")
    if requested_random_states_raw is None:
        requested_random_states = _context_random_states(context)
    elif isinstance(requested_random_states_raw, str):
        requested_random_states = [
            int(part.strip()) for part in requested_random_states_raw.split(",") if part.strip()
        ]
    else:
        requested_random_states = [int(value) for value in requested_random_states_raw]  # type: ignore[arg-type]
    random_states = list(requested_random_states)
    full_universe_seed_deduped = False
    if exact_max_candidates <= 0 and len(random_states) > 1:
        random_states = [int(random_states[0])]
        full_universe_seed_deduped = True
        logger.info(
            "Deduplicating exact_random_states for full-universe exact rerank: requested={} "
            "effective={}. With exact_max_candidates<=0 there is no sampling, so seeds are "
            "identical.",
            requested_random_states,
            random_states,
        )
    expected_checks = int(len(shortlist) * len(random_states) * len(alpha_grid))
    context["bound_total_checks"] = expected_checks
    exact_threads = _context_exact_threads(context)
    checkpoint_every = max(1, int(context.get("exact_checkpoint_every", 100)))

    bound_eval = _load_completed_bound_eval(
        bound_eval_path=bound_eval_path,
        expected_checks=expected_checks,
    )
    if bound_eval is None:
        partial_bound_eval = _load_partial_bound_eval(bound_eval_path=bound_eval_path)
        if not partial_bound_eval.empty:
            partial_bound_eval = partial_bound_eval[
                partial_bound_eval["eval_random_state"].astype(int).isin(random_states)
            ].reset_index(drop=True)
        completed_keys = {
            (int(row.candidate_rank), int(row.eval_random_state), float(row.alpha))
            for row in partial_bound_eval.itertuples(index=False)
        }
        bound_rows: list[dict[str, object]] = (
            partial_bound_eval.to_dict(orient="records") if not partial_bound_eval.empty else []
        )
        completed_checks = len(completed_keys)
        context["resume_completed_checks"] = int(completed_checks)
        if completed_checks:
            _write_exact_status(
                context=context,
                base_elapsed_sec=base_elapsed_sec,
                bound_completed_checks=completed_checks,
                phase="exact_bound_running",
                state="running",
                extra={
                    "resume_cache_rows": int(completed_checks),
                    "checkpoint_every": int(checkpoint_every),
                    "exact_max_candidates": int(exact_max_candidates),
                    "exact_random_states": random_states,
                    "requested_exact_random_states": requested_random_states,
                    "full_universe_seed_deduped": bool(full_universe_seed_deduped),
                    "exact_threads": int(exact_threads),
                },
            )
        aligned_by_seed = {
            int(seed): _load_aligned_dataset(
                conformal_intervals_path=str(context["conformal_intervals_path"]),
                max_candidates=int(exact_max_candidates),
                random_state=int(seed),
            )
            for seed in random_states
        }

        for _, row in shortlist.iterrows():
            policy = _policy_from_row(
                row,
                solver_backend_override=str(context["exact_solver_backend"]),
            )
            candidate_payload = row.to_dict()
            for eval_seed in random_states:
                aligned = aligned_by_seed[int(eval_seed)]
                for alpha in alpha_grid:
                    cache_key = (
                        int(candidate_payload["candidate_rank"]),
                        int(eval_seed),
                        float(alpha),
                    )
                    if cache_key in completed_keys:
                        continue
                    result = _validate_single_alpha(
                        aligned,
                        alpha=float(alpha),
                        policy=policy,
                        allocator_mode="exact",
                        budget=float(context["budget"]),
                        t_eval=float(context["t_eval"]),
                        threads=int(exact_threads),
                    )
                    bound_rows.append(
                        {
                            "candidate_rank": int(candidate_payload["candidate_rank"]),
                            "eval_random_state": int(eval_seed),
                            "frontier_solver_backend": str(context["frontier_solver_backend"]),
                            "exact_solver_backend": str(context["exact_solver_backend"]),
                            **candidate_payload,
                            **result,
                        }
                    )
                    completed_checks += 1
                    completed_keys.add(cache_key)
                    _write_exact_status(
                        context=context,
                        base_elapsed_sec=base_elapsed_sec,
                        bound_completed_checks=completed_checks,
                        phase="exact_bound_running",
                        state="running",
                        extra={
                            "candidate_rank": int(candidate_payload["candidate_rank"]),
                            "eval_random_state": int(eval_seed),
                            "current_alpha": float(alpha),
                            "checkpoint_every": int(checkpoint_every),
                            "exact_max_candidates": int(exact_max_candidates),
                            "exact_random_states": random_states,
                            "requested_exact_random_states": requested_random_states,
                            "full_universe_seed_deduped": bool(full_universe_seed_deduped),
                            "exact_threads": int(exact_threads),
                        },
                    )
                    if completed_checks % checkpoint_every == 0:
                        atomic_write_parquet(
                            pd.DataFrame(bound_rows),
                            bound_eval_path,
                            index=False,
                        )

        bound_eval = pd.DataFrame(bound_rows)
        atomic_write_parquet(bound_eval, bound_eval_path, index=False)
    shortlist_eval = _aggregate_exact_results(shortlist=shortlist, bound_eval=bound_eval)
    region_payload = _region_summary(shortlist_eval, bound_eval)
    selected = shortlist_eval.iloc[0].copy()
    selected_policy = _policy_from_row(
        selected,
        solver_backend_override=str(context["exact_solver_backend"]),
    )

    search_space_payload = dict(context["search_space"])  # type: ignore[arg-type]
    requested_search_alpha_grid = search_space_payload.get("alpha_grid")
    search_space_payload["alpha_grid"] = alpha_grid
    if requested_search_alpha_grid != alpha_grid:
        search_space_payload["requested_alpha_grid"] = requested_search_alpha_grid
        search_space_payload["effective_alpha_grid"] = alpha_grid

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "run_label": str(context["run_label"]),
        "conformal_intervals_path": _repo_relative(str(context["conformal_intervals_path"])),
        "search_space": search_space_payload,
        "selection_policy": context["selection_policy"],
        "selected_policy": selected_policy,
        "selected_metrics": selected.to_dict(),
        "selection_reason": _selection_reason(selected),
        "frontier_raw_path": _repo_relative(str(context["frontier_raw_path"])),
        "frontier_path": _repo_relative(str(context["frontier_path"])),
        "shortlist_path": _repo_relative(str(context["shortlist_path"])),
        "shortlist_exact_path": _repo_relative(shortlist_exact_path),
        "bound_eval_path": _repo_relative(str(context["bound_eval_path"])),
        "region_summary_path": _repo_relative(str(context["region_summary_path"])),
        "robust_region_summary": region_payload,
        "runtime_status_path": _repo_relative(str(context["runtime_status_path"])),
        "runtime_checkpoint_dir": _repo_relative(str(context["runtime_checkpoint_dir"])),
        "resource_snapshot_path": _repo_relative(str(context["resource_snapshot_path"])),
        "frontier_solver_backend": str(context["frontier_solver_backend"]),
        "exact_solver_backend": str(context["exact_solver_backend"]),
        "exact_threads": int(exact_threads),
        "requested_exact_random_states": requested_random_states,
        "effective_exact_random_states": random_states,
        "full_universe_seed_deduped": bool(full_universe_seed_deduped),
    }

    atomic_write_parquet(shortlist_eval, shortlist_exact_path, index=False)
    atomic_write_json(Path(str(context["region_summary_path"])), region_payload)
    atomic_write_json(selection_path, payload)

    resource_payload = json.loads(resource_snapshot_path.read_text(encoding="utf-8"))
    resource_payload["exact_helper_python"] = _repo_relative(sys.executable)
    resource_payload["exact_helper_end"] = _resource_snapshot()
    atomic_write_json(resource_snapshot_path, resource_payload)

    final_payload = _write_exact_status(
        context=context,
        base_elapsed_sec=base_elapsed_sec,
        bound_completed_checks=int(context["bound_total_checks"]),
        phase="selection_complete",
        state="completed",
        extra={
            "selection_reason": str(payload["selection_reason"]),
            "selected_alpha01_exact_pass": bool(selected["alpha01_exact_pass"]),
            "selected_realized_total_return": float(selected["realized_total_return"]),
        },
    )
    write_runtime_checkpoint(
        STAGE_NAME,
        "003_selection_complete",
        final_payload,
        checkpoint_dir=checkpoint_dir,
    )

    logger.info(
        "External exact bound stage complete: selected risk_tolerance={}, mode={}, gamma={}, alpha01_pass={}",
        selected["risk_tolerance"],
        selected["policy_mode"],
        selected["gamma"],
        selected["alpha01_exact_pass"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
