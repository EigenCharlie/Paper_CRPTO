"""Inspect one long-run operational snapshot without touching scientific outputs."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import time
from pathlib import Path
from typing import Any

from src.utils.long_run_observer import (
    classify_long_run_status,
    load_long_run_status,
    status_age_seconds,
)


def _sample_process(
    pid: int,
    *,
    seconds: float,
    expected_create_time_epoch_seconds: float | None = None,
) -> dict[str, Any]:
    if type(pid) is not int or pid <= 0:
        raise ValueError("pid must be a positive integer.")
    if not math.isfinite(seconds) or not 0.0 <= seconds <= 10.0:
        raise ValueError("seconds must be finite and between 0 and 10.")
    if expected_create_time_epoch_seconds is not None and (
        not math.isfinite(expected_create_time_epoch_seconds)
        or expected_create_time_epoch_seconds <= 0.0
    ):
        raise ValueError("expected process creation time must be finite and positive.")
    try:
        psutil = importlib.import_module("psutil")
    except ImportError:
        return {
            "process_running": None,
            "sampled_cpu_cores": None,
            "process_metrics_available": False,
            "process_identity_match": None,
            "observed_process_create_time_epoch_seconds": None,
        }

    try:
        process = psutil.Process(pid)
        observed_create_time = float(process.create_time())
        if not math.isfinite(observed_create_time) or observed_create_time <= 0.0:
            raise ValueError("process backend returned an invalid creation time")
        identity_match = (
            None
            if expected_create_time_epoch_seconds is None
            else math.isclose(
                observed_create_time,
                expected_create_time_epoch_seconds,
                rel_tol=0.0,
                abs_tol=1.0e-6,
            )
        )
        if identity_match is False:
            return {
                "process_running": False,
                "sampled_cpu_cores": None,
                "process_metrics_available": True,
                "process_identity_match": False,
                "observed_process_create_time_epoch_seconds": observed_create_time,
            }
        before = process.cpu_times()
        before_cpu = float(before.user + before.system)
        before_wall = time.perf_counter()
        if seconds > 0.0:
            time.sleep(seconds)
        after = process.cpu_times()
        after_wall = time.perf_counter()
        after_cpu = float(after.user + after.system)
        elapsed = max(0.0, after_wall - before_wall)
        sampled_cpu_cores = max(0.0, after_cpu - before_cpu) / elapsed if elapsed else None
        return {
            "process_running": bool(process.is_running()),
            "sampled_cpu_cores": sampled_cpu_cores,
            "resident_set_bytes_now": int(process.memory_info().rss),
            "thread_count_now": int(process.num_threads()),
            "process_metrics_available": True,
            "process_identity_match": identity_match,
            "observed_process_create_time_epoch_seconds": observed_create_time,
        }
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return {
            "process_running": False,
            "sampled_cpu_cores": None,
            "process_metrics_available": True,
            "process_identity_match": (
                False if expected_create_time_epoch_seconds is not None else None
            ),
            "observed_process_create_time_epoch_seconds": None,
        }
    except (psutil.AccessDenied, AttributeError, OSError, TypeError, ValueError):
        return {
            "process_running": None,
            "sampled_cpu_cores": None,
            "process_metrics_available": False,
            "process_identity_match": None,
            "observed_process_create_time_epoch_seconds": None,
        }


def _inspect_status(status_path: Path, *, sample_seconds: float) -> dict[str, Any]:
    """Sample the recorded PID, then reload the snapshot before computing age."""

    initial_payload = load_long_run_status(status_path)
    sampled_pid = int(initial_payload["pid"])
    sampled_create_time = initial_payload["process_create_time_epoch_seconds"]
    process = _sample_process(
        sampled_pid,
        seconds=sample_seconds,
        expected_create_time_epoch_seconds=sampled_create_time,
    )

    # A heartbeat may replace latest.json while process CPU is sampled.  Reload
    # it so age and classification describe the newest complete snapshot.
    payload = load_long_run_status(status_path)
    current_pid = int(payload["pid"])
    current_create_time = payload["process_create_time_epoch_seconds"]
    pid_changed_during_sample = current_pid != sampled_pid
    worker_identity_changed_during_sample = (
        pid_changed_during_sample or current_create_time != sampled_create_time
    )
    if worker_identity_changed_during_sample:
        process = _sample_process(
            current_pid,
            seconds=0.0,
            expected_create_time_epoch_seconds=current_create_time,
        )
        sampled_pid = current_pid
    age = status_age_seconds(payload)
    classification = classify_long_run_status(
        payload,
        process_running=process["process_running"],
        sampled_cpu_cores=process["sampled_cpu_cores"],
        observed_age_seconds=age,
    )
    return {
        "kind": "operational_inspection_not_scientific_evidence",
        "classification": classification,
        "status_age_seconds": round(age, 3),
        "snapshot": payload,
        "process_sample": {
            **process,
            "sampled_pid": sampled_pid,
            "pid_changed_during_sample": pid_changed_during_sample,
            "worker_identity_changed_during_sample": (worker_identity_changed_during_sample),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect operational progress and process activity. The output is "
            "not scientific evidence and never modifies the run."
        )
    )
    parser.add_argument("status_path", type=Path)
    parser.add_argument(
        "--sample-seconds",
        type=float,
        default=1.0,
        help="Short process-CPU sampling interval (default: 1 second).",
    )
    args = parser.parse_args()
    if not math.isfinite(args.sample_seconds) or not 0.0 <= args.sample_seconds <= 10.0:
        parser.error("--sample-seconds must be finite and between 0 and 10.")

    result = _inspect_status(
        args.status_path,
        sample_seconds=float(args.sample_seconds),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
