"""Run claim-max conformal and portfolio searches after champion HPO.

This orchestration layer consumes paper-facing HPO candidate contracts under
``models/search_pd`` and writes only isolated experiment artifacts. It is meant
to wait behind a long HPO tmux run and then evaluate the best PD candidates on
the claims that matter for the paper: return, bound, robust region size, clean
region definition, and return-bound frontier.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

CHAMPION_AUC = 0.7138518124963467
CHAMPION_BRIER = 0.15439302183275685
CHAMPION_ECE = 0.006998009158194006

CUOPT_FLAG_MAP = {
    "presolve": "--cuopt-presolve",
    "method": "--cuopt-method",
    "pdlp_solver_mode": "--cuopt-pdlp-solver-mode",
    "pdlp_precision": "--cuopt-pdlp-precision",
    "crossover": "--cuopt-crossover",
    "first_primal_feasible": "--cuopt-first-primal-feasible",
    "save_best_primal_solution": "--cuopt-save-best-primal-solution",
    "infeasibility_detection": "--cuopt-infeasibility-detection",
    "strict_infeasibility": "--cuopt-strict-infeasibility",
    "per_constraint_residual": "--cuopt-per-constraint-residual",
    "dual_postsolve": "--cuopt-dual-postsolve",
    "dualize": "--cuopt-dualize",
    "folding": "--cuopt-folding",
    "augmented": "--cuopt-augmented",
    "ordering": "--cuopt-ordering",
    "cudss_deterministic": "--cuopt-cudss-deterministic",
    "eliminate_dense_columns": "--cuopt-eliminate-dense-columns",
    "iteration_limit": "--cuopt-iteration-limit",
    "num_cpu_threads": "--cuopt-num-cpu-threads",
    "num_gpus": "--cuopt-num-gpus",
    "log_to_console": "--cuopt-log-to-console",
    "log_dir": "--cuopt-log-dir",
}


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sanitize(raw: str) -> str:
    return str(raw).strip().replace("/", "_").replace("\\", "_").replace(" ", "_")


def _parse_case_list(raw: str) -> list[str]:
    return [_sanitize(part) for part in str(raw or "").split(",") if str(part).strip()]


def _is_paper_facing_case(case_name: str) -> bool:
    name = _sanitize(case_name).lower()
    return (
        name == "pool93"
        or name.startswith("pool93_")
        or name == "catboost44"
        or name in {"canonical_4", "bureau_behavior_15"}
        or "business" in name
    )


def _hpo_summary_path(hpo_run_tag: str, seed: int) -> Path:
    return (
        REPO_ROOT
        / "reports"
        / "crpto"
        / "experiments"
        / "champion_reopen"
        / hpo_run_tag
        / "summary"
        / f"seed_{int(seed)}"
        / "hpo_experiment_summary.json"
    )


def _status_root(run_tag: str) -> Path:
    return (
        REPO_ROOT
        / "reports"
        / "crpto"
        / "experiments"
        / "champion_reopen"
        / run_tag
        / "claim_max_downstream"
    )


def _log_root(run_tag: str) -> Path:
    return REPO_ROOT / "reports" / "run_logs" / "champion_reopen" / run_tag / "claim_max"


def _load_hpo_candidates(hpo_run_tag: str, seed: int) -> list[dict[str, Any]]:
    root = REPO_ROOT / "models" / "experiments" / "champion_reopen" / hpo_run_tag
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob(f"*/seed_{int(seed)}/hpo_training_status.json")):
        payload = _read_json(path)
        metrics = dict(payload.get("test_metrics", {}) or {})
        if not metrics:
            continue
        case_name = str(payload.get("case_name", path.parents[1].name))
        paper_facing = _is_paper_facing_case(case_name)
        auc = float(metrics.get("auc_roc", 0.0))
        brier = float(metrics.get("brier_score", 1.0))
        ece = float(metrics.get("ece", 1.0))
        score = (
            (auc - CHAMPION_AUC) * 1000.0
            - max(0.0, brier - CHAMPION_BRIER) * 80.0
            - max(0.0, ece - CHAMPION_ECE) * 8.0
            + (0.20 if paper_facing else 0.0)
        )
        rows.append(
            {
                "case_name": case_name,
                "candidate_run_tag": str(payload["candidate_run_tag"]),
                "search_pd_dir": str(payload.get("search_pd_dir", "")),
                "n_model_features": int(payload.get("n_model_features", 0)),
                "n_generated_features": int(payload.get("n_generated_features", 0)),
                "paper_facing": bool(paper_facing),
                "auc_roc": auc,
                "brier_score": brier,
                "ece": ece,
                "claim_pd_score": float(score),
                "status_path": str(path),
            }
        )
    rows.sort(
        key=lambda row: (
            float(row["claim_pd_score"]),
            bool(row["paper_facing"]),
            float(row["auc_roc"]),
            -float(row["brier_score"]),
            -float(row["ece"]),
        ),
        reverse=True,
    )
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def _select_downstream_candidates(
    candidates: list[dict[str, Any]],
    *,
    top_k: int,
    mandatory_cases: list[str] | tuple[str, ...] = (),
    paper_facing_top_k: int = 0,
    skip_cases: list[str] | tuple[str, ...] = (),
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select PD candidates for downstream without losing paper-facing cases.

    The score rank is still the primary gate, but downstream effects can reverse
    a small PD ranking difference. This keeps the best ranked candidates and
    explicitly preserves candidates that are important for paper interpretation.
    """

    skip_set = {_sanitize(case_name) for case_name in skip_cases}
    eligible_candidates = [
        row for row in candidates if _sanitize(str(row["case_name"])) not in skip_set
    ]
    case_to_row = {_sanitize(str(row["case_name"])): row for row in eligible_candidates}
    reasons: dict[str, list[str]] = {}
    missing_mandatory: list[str] = []

    def add(case_name: str, reason: str) -> None:
        key = _sanitize(case_name)
        if key in skip_set:
            return
        if key not in case_to_row:
            if reason == "mandatory_case":
                missing_mandatory.append(key)
            return
        reasons.setdefault(key, [])
        if reason not in reasons[key]:
            reasons[key].append(reason)

    for row in eligible_candidates[: max(1, int(top_k))]:
        add(str(row["case_name"]), "top_k_pd_score")

    for case_name in mandatory_cases:
        add(case_name, "mandatory_case")

    if int(paper_facing_top_k) > 0:
        n_added = 0
        for row in eligible_candidates:
            if not bool(row.get("paper_facing")):
                continue
            add(str(row["case_name"]), "paper_facing_top_k")
            n_added += 1
            if n_added >= int(paper_facing_top_k):
                break

    selected: list[dict[str, Any]] = []
    for row in eligible_candidates:
        key = _sanitize(str(row["case_name"]))
        if key not in reasons:
            continue
        selected_row = dict(row)
        selected_row["selection_reasons"] = reasons[key]
        selected.append(selected_row)

    policy = {
        "top_k": max(1, int(top_k)),
        "mandatory_cases": list(mandatory_cases),
        "paper_facing_top_k": max(0, int(paper_facing_top_k)),
        "skip_cases": sorted(skip_set),
        "missing_mandatory_cases": missing_mandatory,
        "selected_case_names": [str(row["case_name"]) for row in selected],
        "n_selected": len(selected),
    }
    return selected, policy


def _load_profile(path: str | Path) -> dict[str, Any]:
    target = REPO_ROOT / path if not Path(path).is_absolute() else Path(path)
    payload = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    return dict(payload) if isinstance(payload, dict) else {}


def _run_logged(
    *,
    command: list[str],
    log_path: Path,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\nCOMMAND_START {_utc_now()}\n")
        log.write(" ".join(command) + "\n")
        log.flush()
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            check=False,
        )
        log.write(f"COMMAND_EXIT {proc.returncode} {_utc_now()}\n")
        return int(proc.returncode)


def _conformal_status_path(conformal_run_tag: str) -> Path:
    return (
        REPO_ROOT / "models" / "conformal_gap" / conformal_run_tag / "conformal_reopen_status.json"
    )


def _conformal_intervals_for_status(status: dict[str, Any]) -> Path:
    namespace = str(status["final_namespace"])
    return (
        REPO_ROOT
        / "data"
        / "processed"
        / "conformal_gap"
        / namespace
        / "conformal_intervals_mondrian.parquet"
    )


def _profile_section(portfolio_profile: dict[str, Any], key: str) -> dict[str, Any]:
    return dict(portfolio_profile.get(key, {}) or {})


def _append_option(command: list[str], flag: str, value: Any) -> None:
    if value is not None and str(value).strip():
        command.extend([flag, str(value)])


def _append_int_option(command: list[str], flag: str, value: Any) -> None:
    if value is not None and str(value).strip():
        command.extend([flag, str(int(value))])


def _portfolio_base_command(
    *,
    portfolio_profile: dict[str, Any],
    conformal_intervals_path: Path,
    run_label: str,
    output_dir: Path,
    model_dir: Path,
    grids: dict[str, Any],
    frontier: dict[str, Any],
    incumbent: dict[str, Any],
    execution: dict[str, Any],
) -> list[str]:
    python_executable = str(execution.get("python_executable") or sys.executable)
    policy_modes = ",".join(str(x) for x in portfolio_profile.get("candidate_policy_families", []))
    return [
        python_executable,
        "scripts/search/run_portfolio_bound_aware_search.py",
        "--config",
        "configs/crpto_optimization.yaml",
        "--conformal-intervals-path",
        str(conformal_intervals_path),
        "--run-label",
        run_label,
        "--output-dir",
        str(output_dir),
        "--model-dir",
        str(model_dir),
        "--incumbent-policy-path",
        "models/champion_portfolio_policy.json",
        "--risk-grid",
        str(grids["risk_grid"]),
        "--gamma-grid",
        str(grids["gamma_grid"]),
        "--aversion-grid",
        str(grids["aversion_grid"]),
        "--delta-cap-grid",
        str(grids["delta_cap_grid"]),
        "--tail-focus-grid",
        str(grids["tail_focus_grid"]),
        "--alpha-grid",
        str(grids["alpha_grid"]),
        "--random-states",
        str(grids["random_states"]),
        "--max-candidates",
        str(int(frontier.get("proxy_candidates_per_conformal_finalist", 100000))),
        "--shortlist-top-k",
        str(int(frontier.get("exact_rerank_top_k", 1000))),
        "--bucket-return-k",
        str(int(frontier.get("bucket_return_k", 200))),
        "--bucket-proxy-k",
        str(int(frontier.get("bucket_proxy_k", 200))),
        "--bucket-family-k",
        str(int(frontier.get("bucket_family_k", 100))),
        "--bucket-region-k",
        str(int(frontier.get("bucket_region_k", 200))),
        "--incumbent-risk-neighbors",
        str(incumbent["risk_neighbors"]),
        "--incumbent-gamma-neighbors",
        str(incumbent["gamma_neighbors"]),
        "--incumbent-policy-modes",
        str(incumbent["policy_modes"]),
        "--policy-modes",
        policy_modes,
        "--solver-backend",
        str(execution.get("solver_backend", "highs")),
        "--exact-solver-backend",
        str(execution.get("exact_solver_backend", "highs")),
    ]


def _append_frontier_options(
    command: list[str],
    *,
    grids: dict[str, Any],
    frontier: dict[str, Any],
) -> None:
    _append_int_option(command, "--exact-max-candidates", frontier.get("exact_max_candidates"))
    exact_random_states = frontier.get("exact_random_states", grids.get("exact_random_states"))
    _append_option(command, "--exact-random-states", exact_random_states)
    _append_int_option(command, "--exact-checkpoint-every", frontier.get("exact_checkpoint_every"))
    _append_int_option(command, "--exact-threads", frontier.get("exact_threads"))
    _append_option(command, "--budget-profiles", grids.get("budget_profiles"))


def _append_execution_options(command: list[str], *, execution: dict[str, Any]) -> None:
    if bool(execution.get("frontier_only", False)):
        command.append("--frontier-only")
    _append_option(command, "--exact-python-executable", execution.get("exact_python_executable"))


def _append_cuopt_options(command: list[str], *, cuopt: dict[str, Any]) -> None:
    for key, flag in CUOPT_FLAG_MAP.items():
        _append_option(command, flag, cuopt.get(key))
    for key, value in dict(cuopt.get("extra_parameters", {}) or {}).items():
        command.extend(["--cuopt-extra-parameter", f"{key}={value}"])


def _portfolio_command(
    *,
    portfolio_profile: dict[str, Any],
    conformal_intervals_path: Path,
    run_label: str,
    output_dir: Path,
    model_dir: Path,
) -> list[str]:
    grids = _profile_section(portfolio_profile, "grids")
    frontier = _profile_section(portfolio_profile, "frontier")
    incumbent = _profile_section(portfolio_profile, "incumbent_region")
    execution = _profile_section(portfolio_profile, "execution")
    cuopt = _profile_section(portfolio_profile, "cuopt")
    command = _portfolio_base_command(
        portfolio_profile=portfolio_profile,
        conformal_intervals_path=conformal_intervals_path,
        run_label=run_label,
        output_dir=output_dir,
        model_dir=model_dir,
        grids=grids,
        frontier=frontier,
        incumbent=incumbent,
        execution=execution,
    )
    _append_frontier_options(command, grids=grids, frontier=frontier)
    _append_execution_options(command, execution=execution)
    _append_cuopt_options(command, cuopt=cuopt)
    return command


def _write_status(status_path: Path, payload: dict[str, Any]) -> None:
    payload = {"updated_at_utc": _utc_now(), **payload}
    _write_json(status_path, payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hpo-run-tag", default="champion-reopen-2026-06-19__hpo-wave1")
    parser.add_argument("--run-tag", default="")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument(
        "--mandatory-cases",
        default="pool93",
        help="Comma-separated cases that must run downstream if their HPO artifacts exist.",
    )
    parser.add_argument(
        "--paper-facing-top-k",
        type=int,
        default=3,
        help="Also include this many paper-facing cases by PD score, deduplicated with top-k.",
    )
    parser.add_argument(
        "--skip-cases",
        default="",
        help="Comma-separated cases managed by another lane and excluded from this watcher.",
    )
    parser.add_argument("--wait-for-hpo-complete", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=300)
    parser.add_argument("--conformal-profile", default="search_conformal_claim_max")
    parser.add_argument(
        "--portfolio-profile-path",
        default="configs/profiles/search_portfolio_claim_max.yaml",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-portfolio", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    hpo_run_tag = _sanitize(args.hpo_run_tag)
    run_tag = _sanitize(args.run_tag or f"{hpo_run_tag}__claim-max-downstream")
    status_dir = _status_root(run_tag)
    log_dir = _log_root(run_tag)
    status_path = status_dir / "runtime_status.json"
    portfolio_profile = _load_profile(args.portfolio_profile_path)
    mandatory_cases = _parse_case_list(args.mandatory_cases)
    skip_cases = _parse_case_list(args.skip_cases)

    while args.wait_for_hpo_complete and not _hpo_summary_path(hpo_run_tag, args.seed).exists():
        candidates = _load_hpo_candidates(hpo_run_tag, args.seed)
        selected_preview, selection_policy_preview = _select_downstream_candidates(
            candidates,
            top_k=args.top_k,
            mandatory_cases=mandatory_cases,
            paper_facing_top_k=args.paper_facing_top_k,
            skip_cases=skip_cases,
        )
        _write_status(
            status_path,
            {
                "stage_name": "champion_claim_max_downstream",
                "state": "waiting",
                "phase": "waiting_for_hpo_summary",
                "hpo_run_tag": hpo_run_tag,
                "completed_hpo_candidates": len(candidates),
                "hpo_summary_path": str(_hpo_summary_path(hpo_run_tag, args.seed)),
                "selection_policy_preview": selection_policy_preview,
                "selected_candidate_preview": selected_preview,
            },
        )
        time.sleep(max(30, int(args.poll_seconds)))

    candidates = _load_hpo_candidates(hpo_run_tag, args.seed)
    selected, selection_policy = _select_downstream_candidates(
        candidates,
        top_k=args.top_k,
        mandatory_cases=mandatory_cases,
        paper_facing_top_k=args.paper_facing_top_k,
        skip_cases=skip_cases,
    )
    _write_status(
        status_path,
        {
            "stage_name": "champion_claim_max_downstream",
            "state": "completed"
            if args.dry_run and selected
            else ("running" if selected else "blocked"),
            "phase": "selected_pd_candidates",
            "hpo_run_tag": hpo_run_tag,
            "run_tag": run_tag,
            "selected_candidates": selected,
            "selection_policy": selection_policy,
            "n_available_hpo_candidates": len(candidates),
            "dry_run": bool(args.dry_run),
        },
    )
    if not selected:
        return 2
    if args.dry_run:
        return 0

    results: list[dict[str, Any]] = []
    for candidate in selected:
        case_name = _sanitize(str(candidate["case_name"]))
        conformal_run_tag = _sanitize(f"{run_tag}__{case_name}__conformal")
        conformal_status_path = _conformal_status_path(conformal_run_tag)
        conformal_log = log_dir / f"{case_name}__conformal.log"
        candidate_result: dict[str, Any] = {
            "candidate": candidate,
            "conformal_run_tag": conformal_run_tag,
            "conformal_status_path": str(conformal_status_path),
        }
        if not conformal_status_path.exists():
            command = [
                sys.executable,
                "scripts/search/run_conformal_reopen_search.py",
                "--run-tag",
                conformal_run_tag,
                "--pipeline-profile",
                str(args.conformal_profile),
                "--upstream-canonical-run-tag",
                str(candidate["candidate_run_tag"]),
            ]
            code = _run_logged(command=command, log_path=conformal_log, cwd=REPO_ROOT)
            candidate_result["conformal_exit_code"] = int(code)
            if code != 0:
                candidate_result["state"] = "conformal_failed"
                results.append(candidate_result)
                _write_status(
                    status_path,
                    {
                        "stage_name": "champion_claim_max_downstream",
                        "state": "running",
                        "phase": "candidate_failed",
                        "latest_result": candidate_result,
                        "results": results,
                    },
                )
                continue
        conformal_status = _read_json(conformal_status_path)
        intervals_path = _conformal_intervals_for_status(conformal_status)
        candidate_result["conformal_status"] = conformal_status
        candidate_result["conformal_intervals_path"] = str(intervals_path)
        if args.skip_portfolio:
            candidate_result["state"] = "conformal_complete_portfolio_skipped"
            results.append(candidate_result)
            continue
        portfolio_label = _sanitize(f"{run_tag}__{case_name}__portfolio")
        portfolio_output = (
            REPO_ROOT
            / "data"
            / "processed"
            / "experiments"
            / "champion_reopen"
            / run_tag
            / case_name
            / "portfolio"
        )
        portfolio_model = (
            REPO_ROOT
            / "models"
            / "experiments"
            / "champion_reopen"
            / run_tag
            / case_name
            / "portfolio"
        )
        selection_path = portfolio_model / "portfolio_bound_aware_selection.json"
        if not selection_path.exists():
            command = _portfolio_command(
                portfolio_profile=portfolio_profile,
                conformal_intervals_path=intervals_path,
                run_label=portfolio_label,
                output_dir=portfolio_output,
                model_dir=portfolio_model,
            )
            code = _run_logged(
                command=command,
                log_path=log_dir / f"{case_name}__portfolio.log",
                cwd=REPO_ROOT,
            )
            candidate_result["portfolio_exit_code"] = int(code)
            if code != 0:
                candidate_result["state"] = "portfolio_failed"
                results.append(candidate_result)
                continue
        candidate_result["portfolio_selection_path"] = str(selection_path)
        candidate_result["state"] = "portfolio_complete"
        if selection_path.exists():
            selection = _read_json(selection_path)
            candidate_result["portfolio_selection"] = {
                "selection_reason": selection.get("selection_reason"),
                "selected_policy": selection.get("selected_policy"),
                "selected_metrics": selection.get("selected_metrics"),
                "region_summary_path": selection.get("region_summary_path"),
            }
        results.append(candidate_result)
        _write_status(
            status_path,
            {
                "stage_name": "champion_claim_max_downstream",
                "state": "running",
                "phase": "candidate_complete",
                "latest_result": candidate_result,
                "results": results,
            },
        )

    _write_status(
        status_path,
        {
            "stage_name": "champion_claim_max_downstream",
            "state": "completed",
            "phase": "complete",
            "hpo_run_tag": hpo_run_tag,
            "run_tag": run_tag,
            "selected_candidates": selected,
            "selection_policy": selection_policy,
            "results": results,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
