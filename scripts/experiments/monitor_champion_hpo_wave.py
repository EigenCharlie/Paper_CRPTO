"""Lightweight Optuna/Champion HPO progress monitor.

This script is intentionally read-only with respect to Optuna studies. It
polls per-case SQLite studies and writes a compact JSON status so long HPO
trials do not look stalled between CatBoost log lines.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


def _duration_seconds(start: str | None, end: str | None) -> float | None:
    started = _parse_dt(start)
    finished = _parse_dt(end)
    if started is None or finished is None:
        return None
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    if finished.tzinfo is None:
        finished = finished.replace(tzinfo=UTC)
    return max(0.0, (finished - started).total_seconds())


def _elapsed_since_start_seconds(start: str | None) -> float | None:
    started = _parse_dt(start)
    if started is None:
        return None
    if started.tzinfo is None:
        return max(0.0, (datetime.now() - started).total_seconds())
    return max(0.0, (datetime.now(tz=UTC) - started).total_seconds())


def _study_payload(db_path: Path, *, target_trials: int) -> dict[str, Any]:
    if not db_path.exists():
        return {
            "case_name": db_path.parents[1].name,
            "optuna_db_path": str(db_path),
            "exists": False,
        }
    con = sqlite3.connect(str(db_path))
    try:
        state_rows = con.execute(
            "select state, count(*) from trials group by state order by state"
        ).fetchall()
        trials = con.execute(
            """
            select number, state, datetime_start, datetime_complete
            from trials
            order by number
            """
        ).fetchall()
    finally:
        con.close()

    counts = {str(state): int(count) for state, count in state_rows}
    done_count = int(counts.get("COMPLETE", 0) + counts.get("PRUNED", 0) + counts.get("FAIL", 0))
    durations = [
        value
        for _, state, started, finished in trials
        if state in {"COMPLETE", "PRUNED"} and (value := _duration_seconds(started, finished))
    ]
    median_trial_sec = float(median(durations)) if durations else None
    remaining_trials = max(0, int(target_trials) - done_count)
    eta_sec = (
        float(remaining_trials * median_trial_sec)
        if median_trial_sec is not None and remaining_trials > 0
        else 0.0
        if remaining_trials == 0
        else None
    )
    running = [
        {
            "number": int(number),
            "datetime_start": started,
            "elapsed_sec": _elapsed_since_start_seconds(started),
        }
        for number, state, started, _ in trials
        if state == "RUNNING"
    ]
    return {
        "case_name": db_path.parents[1].name,
        "optuna_db_path": str(db_path),
        "exists": True,
        "target_trials": int(target_trials),
        "state_counts": counts,
        "done_trials": done_count,
        "remaining_trials": remaining_trials,
        "median_finished_trial_sec": median_trial_sec,
        "eta_sec_from_median_finished_trials": eta_sec,
        "running_trials": running,
        "last_trials": [
            {
                "number": int(number),
                "state": str(state),
                "datetime_start": started,
                "datetime_complete": finished,
            }
            for number, state, started, finished in trials[-5:]
        ],
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _collect(run_tag: str, *, seed: int, target_trials: int) -> dict[str, Any]:
    root = REPO_ROOT / "models" / "experiments" / "champion_reopen" / run_tag
    studies = [
        _study_payload(path, target_trials=target_trials)
        for path in sorted(root.glob(f"*/seed_{int(seed)}/optuna_study.db"))
    ]
    active = [
        study
        for study in studies
        if study.get("exists") and int(study.get("remaining_trials", 0)) > 0
    ]
    return {
        "updated_at_utc": _utc_now(),
        "run_tag": run_tag,
        "seed": int(seed),
        "target_trials": int(target_trials),
        "n_studies": len(studies),
        "active_cases": [str(study["case_name"]) for study in active],
        "studies": studies,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-tag", default="champion-reopen-2026-06-19__hpo-wave1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--target-trials", type=int, default=96)
    parser.add_argument("--poll-seconds", type=int, default=300)
    parser.add_argument(
        "--output-path",
        default="",
        help="Defaults to reports/.../<run_tag>/hpo_live_status.json.",
    )
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    output_path = (
        Path(args.output_path)
        if str(args.output_path).strip()
        else REPO_ROOT
        / "reports"
        / "crpto"
        / "experiments"
        / "champion_reopen"
        / str(args.run_tag)
        / "hpo_live_status.json"
    )
    while True:
        _write_json(
            output_path,
            _collect(str(args.run_tag), seed=int(args.seed), target_trials=int(args.target_trials)),
        )
        if args.once:
            break
        time.sleep(max(30, int(args.poll_seconds)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
