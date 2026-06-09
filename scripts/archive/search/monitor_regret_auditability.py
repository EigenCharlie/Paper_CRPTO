"""Command Prompt friendly monitor for the regret-auditability sandbox."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_ARTIFACT_ROOT = Path(
    r"D:\crpto_experiments\regret_auditability\regret_auditability_20260513_v3_resource_tuned"
)
PHASE_TRIAL_TARGETS = {"pd-smoke": 12, "pd-broad": 1000, "pd-refine": 500}


def emit(text: str = "") -> None:
    """Write one display line to stdout."""
    sys.stdout.write(f"{text}\n")


def clear_screen() -> None:
    """Clear the Windows console."""
    os.system("cls")


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object or return an empty dict."""
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def load_command_rows(path: Path) -> list[dict[str, str]]:
    """Load command log rows."""
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def latest_command_states(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Return the latest row per command name."""
    latest: dict[str, dict[str, str]] = {}
    for row in rows:
        name = row.get("name", "")
        if name:
            latest[name] = row
    return latest


def active_commands(
    rows: list[dict[str, str]],
    live_command_names: set[str] | None = None,
) -> list[dict[str, str]]:
    """Return commands whose latest state is started."""
    latest = latest_command_states(rows)
    active = [row for row in latest.values() if row.get("state") == "started"]
    if live_command_names is None:
        return active
    return [row for row in active if row.get("name", "") in live_command_names]


def summarize_command_states(
    rows: list[dict[str, str]],
    live_command_names: set[str] | None = None,
) -> Counter[str]:
    """Count latest command states."""
    latest = latest_command_states(rows)
    states: list[str] = []
    for row in latest.values():
        state = row.get("state", "unknown")
        if (
            live_command_names is not None
            and state == "started"
            and row.get("name", "") not in live_command_names
        ):
            state = "stale_started"
        states.append(state)
    return Counter(states)


def process_count_for_run(artifact_root: Path) -> int:
    """Count live processes for the sandbox run using Windows process command lines."""
    token = artifact_root.name
    command = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { "
        "($_.CommandLine -like '*run_regret_auditability_sandbox.py*' -or "
        "$_.CommandLine -like '*train_pd_model.py*' -or "
        "$_.CommandLine -like '*generate_conformal_intervals.py*' -or "
        "$_.CommandLine -like '*run_portfolio_bound_aware_search.py*') -and "
        f"$_.CommandLine -notlike '*monitor_regret_auditability*' -and "
        f"$_.CommandLine -like '*{token}*' "
        "} | Measure-Object | Select-Object -ExpandProperty Count"
    )
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return -1
    try:
        return int(proc.stdout.strip() or "0")
    except ValueError:
        return -1


def live_process_command_lines_for_run(artifact_root: Path) -> list[str]:
    """Return live sandbox command lines excluding the monitor itself."""
    token = artifact_root.name
    command = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { "
        "($_.CommandLine -like '*run_regret_auditability_sandbox.py*' -or "
        "$_.CommandLine -like '*train_pd_model.py*' -or "
        "$_.CommandLine -like '*generate_conformal_intervals.py*' -or "
        "$_.CommandLine -like '*run_portfolio_bound_aware_search.py*') -and "
        "$_.CommandLine -notlike '*monitor_regret_auditability*' -and "
        f"$_.CommandLine -like '*{token}*' "
        "} | Select-Object -ExpandProperty CommandLine | ConvertTo-Json -Compress"
    )
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    raw = proc.stdout.strip()
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if isinstance(payload, str):
        return [payload]
    if isinstance(payload, list):
        return [str(item) for item in payload if str(item).strip()]
    return []


def live_command_names_for_run(artifact_root: Path) -> set[str]:
    """Infer active command names from live process command lines."""
    names: set[str] = set()
    pd_config_pattern = re.compile(
        r"[\\/]configs[\\/]pd_(?P<lane>.+?)_(?P<phase>pd-smoke|pd-broad|pd-refine)\.yaml"
    )
    for command_line in live_process_command_lines_for_run(artifact_root):
        match = pd_config_pattern.search(command_line)
        if match:
            names.add(f"{match.group('phase')}_{match.group('lane')}")
        if "generate_conformal_intervals.py" in command_line:
            names.add("conformal_extensive_grid")
        if "run_portfolio_bound_aware_search.py" in command_line:
            names.add("portfolio_extensive_frontier")
        if "--phase" in command_line and "metrics" in command_line:
            names.add("metrics_manifest")
    return names


def optuna_db_from_checkpoint(checkpoint: str) -> Path | None:
    """Resolve the Optuna DB path from a command checkpoint path."""
    if not checkpoint:
        return None
    checkpoint_path = Path(checkpoint)
    phase_root = checkpoint_path.parent.parent
    db_path = phase_root / "optuna_pd_catboost.db"
    return db_path if db_path.exists() else None


def optuna_summary(db_path: Path | None) -> dict[str, Any]:
    """Read the newest Optuna study summary from SQLite storage."""
    if db_path is None:
        return {"counts": Counter()}
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
        study_row = con.execute(
            "select study_id, study_name from studies order by study_id desc limit 1"
        ).fetchone()
        if study_row is None:
            con.close()
            return {"counts": Counter()}
        study_id = int(study_row[0])
        rows = con.execute(
            "select state, count(*) from trials where study_id = ? group by state",
            (study_id,),
        ).fetchall()
        best_row = con.execute(
            """
            select tv.value
            from trial_values tv
            join trials t on tv.trial_id = t.trial_id
            where t.study_id = ? and t.state = 'COMPLETE'
            order by tv.value desc
            limit 1
            """,
            (study_id,),
        ).fetchone()
        con.close()
    except sqlite3.Error:
        return {"counts": Counter()}
    return {
        "study_id": study_id,
        "study_name": str(study_row[1]),
        "counts": Counter({str(state): int(count) for state, count in rows}),
        "best_value": None if best_row is None else float(best_row[0]),
    }


def command_subphase(name: str) -> str:
    """Make command names easier to scan."""
    if "_" not in name:
        return name
    phase, lane = name.split("_", 1)
    return f"{phase} | {lane}"


def tail_lines(path: Path, n_lines: int) -> list[str]:
    """Read the last n lines from a text file."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-n_lines:]


def tail_lines_from_last_start(path: Path, n_lines: int) -> list[str]:
    """Read recent lines from the latest command START marker."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start_indexes = [index for index, line in enumerate(lines) if "] START " in line]
    if start_indexes:
        lines = lines[start_indexes[-1] :]
    return lines[-n_lines:]


def row_stderr_path(row: dict[str, str], artifact_root: Path) -> Path:
    """Resolve per-command stderr path, including legacy command_log rows."""
    raw = row.get("stderr_log", "")
    if raw:
        return Path(raw)
    phase = row.get("phase", "unknown")
    name = row.get("name", "unknown").replace("/", "_").replace("\\", "_")
    return artifact_root / "logs" / phase / f"{name}.err.log"


def classify_failure_reason(row: dict[str, str], artifact_root: Path) -> str:
    """Classify the latest known failure from stderr text."""
    stderr_path = row_stderr_path(row, artifact_root)
    lines = tail_lines(stderr_path, 120)
    start_indexes = [index for index, line in enumerate(lines) if "] START " in line]
    if start_indexes:
        lines = lines[start_indexes[-1] :]
    tail = "\n".join(lines)
    if "MissingRunTagError" in tail or "PIPELINE_RUN_TAG" in tail:
        return "missing PIPELINE_RUN_TAG before patch"
    if "fairness_policy.yaml" in tail:
        return "missing fairness policy before decision-threshold patch"
    if row.get("returncode") == "4294967295":
        return "interrupted/killed during relaunch"
    if "FileNotFoundError" in tail:
        return "FileNotFoundError"
    if "Traceback" in tail:
        return "Python exception; see stderr"
    return "see stderr"


def render(artifact_root: Path) -> None:
    """Render one monitor frame."""
    heartbeat = load_json(artifact_root / "heartbeat.json")
    manifest = load_json(artifact_root / "sandbox_manifest.json")
    rows = load_command_rows(artifact_root / "command_log.csv")
    live_command_names = live_command_names_for_run(artifact_root)
    active = active_commands(rows, live_command_names)
    state_counts = summarize_command_states(rows, live_command_names)
    process_count = process_count_for_run(artifact_root)
    running = process_count > 1

    emit("CRPTO REGRET-AUDITABILITY SANDBOX MONITOR")
    emit("=" * 78)
    emit(f"Artifact root : {artifact_root}")
    emit(f"Running       : {'YES' if running else 'NO'} ({process_count} matching processes)")
    emit(
        "Phase/state   : {} / {}".format(
            heartbeat.get("phase", "unknown"),
            heartbeat.get("state", "unknown"),
        )
    )
    emit(
        "Units         : {}/{}".format(
            heartbeat.get("completed_units", "?"),
            heartbeat.get("total_units", "?"),
        )
    )
    emit(
        "Resources     : CPU {}% | RAM free {} GB | Disk free {} GB".format(
            heartbeat.get("cpu_percent", "?"),
            _round_or_unknown(heartbeat.get("ram_available_gb")),
            _round_or_unknown(heartbeat.get("disk_free_gb")),
        )
    )
    emit(f"Last beat UTC : {heartbeat.get('captured_at_utc', 'missing')}")
    emit(f"Checkpoint    : {heartbeat.get('last_checkpoint_path', '')}")
    mlflow_tracking = manifest.get("mlflow_tracking", {})
    if isinstance(mlflow_tracking, dict) and mlflow_tracking:
        emit(f"MLflow        : {mlflow_tracking.get('tracking_uri', '?')}")
        emit(f"Experiment    : {mlflow_tracking.get('experiment_name', '?')}")
    emit()

    emit("COMMAND STATES")
    emit("-" * 78)
    if state_counts:
        emit(" | ".join(f"{state}: {count}" for state, count in sorted(state_counts.items())))
    else:
        emit("No command_log.csv yet.")
    emit()

    latest = latest_command_states(rows)
    failed_rows = [row for row in latest.values() if row.get("state") == "failed"]
    if failed_rows:
        emit("LATEST FAILED COMMANDS")
        emit("-" * 78)
        for row in sorted(failed_rows, key=lambda item: item.get("captured_at_utc", ""))[-8:]:
            emit(
                f"- {command_subphase(row.get('name', 'unknown'))}: "
                f"{classify_failure_reason(row, artifact_root)}"
            )
        emit()

    emit("ACTIVE SUBPHASES")
    emit("-" * 78)
    if not active:
        emit("No active commands in command_log.csv.")
    for row in active[:10]:
        phase = row.get("phase", "")
        target = PHASE_TRIAL_TARGETS.get(phase)
        summary = optuna_summary(optuna_db_from_checkpoint(row.get("checkpoint", "")))
        counts = summary.get("counts", Counter())
        complete = counts.get("COMPLETE", 0)
        running_trials = counts.get("RUNNING", 0)
        failed = counts.get("FAIL", 0) + counts.get("FAILED", 0)
        trial_text = "no Optuna DB yet"
        if counts:
            trial_text = (
                "Optuna trials complete/running/historical_failed: "
                f"{complete}/{running_trials}/{failed}"
            )
            if target is not None:
                trial_text += f" of target {target}"
            if failed:
                trial_text += " (failed trials are kept for resume/accounting)"
        emit(f"- {command_subphase(row.get('name', 'unknown'))}")
        emit(f"  {trial_text}")
        if summary.get("best_value") is not None:
            emit(f"  best validation AUC: {float(summary['best_value']):.6f}")
        if summary.get("study_name"):
            emit(f"  study: {summary['study_name']}")
    emit()

    emit("SELECTION FILES")
    emit("-" * 78)
    for phase in ("pd-smoke", "pd-broad", "pd-refine"):
        path = artifact_root / "pd" / "_selection" / f"{phase}_selection.json"
        status = "ready" if path.exists() else "pending"
        emit(f"{phase:9s}: {status}  {path if path.exists() else ''}")
    emit()

    emit("ACTIVE COMMAND STDERR")
    emit("-" * 78)
    active_log = row_stderr_path(active[0], artifact_root) if active else None
    lines = tail_lines_from_last_start(active_log, 10) if active_log is not None else []
    if active_log is not None:
        emit(str(active_log))
    if not lines:
        lines = tail_lines(artifact_root / "orchestrator.err.log", 12)
    for line in lines:
        emit(line[:160])
    emit()
    emit("Ctrl+C to stop monitor. The sandbox keeps running in background.")


def _round_or_unknown(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "?"


def main(argv: list[str] | None = None) -> int:
    """Run the monitor loop."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)

    artifact_root = Path(args.artifact_root).expanduser().resolve()
    interval = max(5, int(args.interval))
    while True:
        clear_screen()
        render(artifact_root)
        if args.once:
            return 0
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
