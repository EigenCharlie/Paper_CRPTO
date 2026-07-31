"""Protocol-bound observability and restart bindings for long scientific runs."""

from __future__ import annotations

import importlib
import json
import math
import os
import re
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from src.utils.artifact_descriptor import (
    relative_artifact_descriptor,
    verified_artifact_path,
)
from src.utils.pipeline_runtime import atomic_write_strict_json, utc_now_iso

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STATUS_SCHEMA = "2026-07-30.3"
_CHECKPOINT_SCHEMA = "2026-07-30.2"
_MAX_STATUS_BYTES = 16 * 1024
_MAX_CHECKPOINT_BYTES = 1024 * 1024
_MAX_IDENTIFIER_CHARS = 256
_MAX_DETAIL_FIELDS = 8
_MAX_DETAIL_KEY_CHARS = 64
_MAX_DETAIL_STRING_CHARS = 256
_MAX_DETAIL_JSON_BYTES = 2 * 1024
_MAX_FAILURE_REASON_CHARS = 256
_STATUS_STATES = frozenset({"running", "complete", "failed", "stop_requested", "cancelled"})
_ACTIVITY_SIGNALS = frozenset(
    {
        "complete",
        "unit_progress",
        "cpu_active_between_units",
        "no_recent_progress_or_cpu_signal",
        "awaiting_next_unit",
    }
)
_OPERATIONAL_DETAIL_FIELDS = frozenset(
    {
        "attempt",
        "checkpoint_count",
        "current_unit_key",
        "heartbeat_count",
        "last_checkpoint_key",
        "message",
        "operation",
        "reason",
    }
)


class StopRequested(RuntimeError):
    """Raised at a declared safe boundary after an operator requests a stop."""


def _atomic_staging_name(path: Path) -> str:
    return f".{path.name}.tmp-"


def _collides_with_atomic_target(candidate: Path, target: Path) -> bool:
    return candidate == target or (
        candidate.parent == target.parent
        and candidate.name.casefold().startswith(_atomic_staging_name(target).casefold())
    )


def _require_no_atomic_path_collision(
    *,
    target: Path,
    other_paths: Sequence[Path],
    target_label: str,
    other_label: str,
) -> None:
    for other in other_paths:
        if _collides_with_atomic_target(other, target):
            raise ValueError(
                f"{other_label} must not collide with {target_label} or its atomic staging path: "
                f"{other}"
            )


def _strict_json_object(path: Path, *, maximum_bytes: int, label: str) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    if len(raw) > maximum_bytes:
        raise RuntimeError(f"{label} exceeds the {maximum_bytes}-byte operational limit.")

    def reject_constant(value: str) -> None:
        raise ValueError(f"nonstandard JSON constant {value}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        payload = json.loads(
            raw.decode("utf-8"),
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicate_keys,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise RuntimeError(f"{label} is not strict JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise TypeError(f"{label} must be a JSON object.")
    return payload


def _validated_text(value: Any, *, field: str, maximum_chars: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string.")
    if len(value) > maximum_chars:
        raise ValueError(f"{field} exceeds {maximum_chars} characters.")
    if any(ord(character) < 32 for character in value):
        raise ValueError(f"{field} must be a single-line printable string.")
    return value


def _finite_number(
    value: Any,
    *,
    field: str,
    positive: bool = False,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number.")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite.")
    if positive and number <= 0.0:
        raise ValueError(f"{field} must be positive.")
    if not positive and number < 0.0:
        raise ValueError(f"{field} must be nonnegative.")
    return number


def _sanitize_operational_detail(
    detail: Mapping[str, Any] | None,
    *,
    allow_reason: bool = False,
) -> dict[str, Any] | None:
    if detail is None:
        return None
    if not isinstance(detail, Mapping):
        raise TypeError("detail must be a mapping.")
    if len(detail) > _MAX_DETAIL_FIELDS:
        raise ValueError(f"detail may contain at most {_MAX_DETAIL_FIELDS} fields.")

    sanitized: dict[str, Any] = {}
    for key, value in detail.items():
        if not isinstance(key, str) or not key or len(key) > _MAX_DETAIL_KEY_CHARS:
            raise ValueError(
                f"detail keys must be nonempty strings of at most {_MAX_DETAIL_KEY_CHARS} characters."
            )
        if key not in _OPERATIONAL_DETAIL_FIELDS or (key == "reason" and not allow_reason):
            raise ValueError(f"detail field {key!r} is not an allowed operational field.")
        if isinstance(value, str):
            sanitized[key] = _validated_text(
                value,
                field=f"detail[{key!r}]",
                maximum_chars=_MAX_DETAIL_STRING_CHARS,
            )
        elif value is None or isinstance(value, bool) or type(value) is int:
            sanitized[key] = value
        elif isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError(f"detail[{key!r}] must be finite.")
            sanitized[key] = value
        else:
            raise TypeError(
                f"detail[{key!r}] must be a JSON scalar; nested values are not supported."
            )

    try:
        serialized = json.dumps(
            sanitized,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:  # Defensive guard for unusual Mapping implementations.
        raise ValueError("detail must be strict JSON.") from exc
    if len(serialized) > _MAX_DETAIL_JSON_BYTES:
        raise ValueError(f"detail exceeds {_MAX_DETAIL_JSON_BYTES} encoded UTF-8 bytes.")
    return sanitized


def require_operational_paths_outside(
    paths: Sequence[Path],
    *,
    forbidden_roots: Sequence[Path],
) -> tuple[Path, ...]:
    """Resolve operational paths and reject repository or protected roots.

    Long-run status, control markers, and restart shards should live on an
    operational filesystem, not inside Git or a protected scientific-artifact
    root.  The caller supplies the roots because this utility cannot infer the
    repository or data contract safely.
    """

    resolved_paths = tuple(Path(path).resolve() for path in paths)
    resolved_roots = tuple(Path(root).resolve() for root in forbidden_roots)
    for path in resolved_paths:
        for root in resolved_roots:
            try:
                path.relative_to(root)
            except ValueError:
                continue
            raise ValueError(f"Operational path must remain outside forbidden root {root}: {path}")
    return resolved_paths


def _resident_set_bytes() -> int | None:
    """Return process RSS when an installed process backend exposes it."""

    try:
        psutil = importlib.import_module("psutil")
        value = int(psutil.Process(os.getpid()).memory_info().rss)
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return None
    return value if value >= 0 else None


def _process_create_time_epoch_seconds() -> float | None:
    """Return this process's creation time when the process backend exposes it."""

    try:
        psutil = importlib.import_module("psutil")
    except ImportError:
        return None
    try:
        value = float(psutil.Process(os.getpid()).create_time())
    except (psutil.Error, AttributeError, OSError, TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value > 0.0 else None


def _rounded(value: float) -> float:
    return round(float(value), 6)


def load_long_run_status(path: Path) -> dict[str, Any]:
    """Load and strictly validate a bounded operational progress snapshot."""

    payload = _strict_json_object(
        Path(path),
        maximum_bytes=_MAX_STATUS_BYTES,
        label="Long-run status",
    )
    if payload.get("kind") != "operational_progress_not_scientific_evidence":
        raise RuntimeError("File is not a long-run operational progress snapshot.")
    if payload.get("schema_version") != _STATUS_SCHEMA:
        raise RuntimeError("Long-run status has an unsupported schema_version.")
    required_fields = {
        "schema_version",
        "kind",
        "observer_scope",
        "resume_authorized",
        "stage_name",
        "run_tag",
        "protocol_tag",
        "phase",
        "state",
        "unit_name",
        "completed_units",
        "total_units",
        "progress_fraction",
        "elapsed_wall_seconds",
        "process_cpu_seconds",
        "average_process_cpu_cores",
        "throughput_units_per_second",
        "eta_seconds",
        "seconds_since_progress",
        "interval_wall_seconds",
        "interval_process_cpu_seconds",
        "interval_average_process_cpu_cores",
        "activity_signal",
        "no_progress_threshold_reached",
        "no_progress_without_cpu_signal",
        "no_progress_after_seconds",
        "heartbeat_seconds",
        "minimum_active_cpu_cores",
        "resident_set_bytes",
        "pid",
        "process_create_time_epoch_seconds",
        "updated_at_utc",
    }
    observed_fields = set(payload)
    missing = sorted(required_fields - observed_fields)
    extra = sorted(observed_fields - required_fields - {"detail"})
    if missing:
        raise RuntimeError(f"Long-run status omits required fields: {missing}.")
    if extra:
        raise RuntimeError(f"Long-run status contains undeclared fields: {extra}.")
    if payload.get("observer_scope") != "single_writer_same_process_worker":
        raise RuntimeError("Long-run status has an unsupported observer_scope.")
    if payload.get("resume_authorized") is not False:
        raise RuntimeError("The MVP status must state that resume is not authorized.")

    try:
        for field in ("stage_name", "run_tag", "protocol_tag", "phase", "unit_name"):
            _validated_text(
                payload.get(field),
                field=field,
                maximum_chars=_MAX_IDENTIFIER_CHARS,
            )
    except ValueError as exc:
        raise RuntimeError(f"Long-run status has invalid text: {exc}") from exc

    state = payload.get("state")
    if state not in _STATUS_STATES:
        raise RuntimeError("Long-run status has an invalid state.")
    activity_signal = payload.get("activity_signal")
    if activity_signal not in _ACTIVITY_SIGNALS:
        raise RuntimeError("Long-run status has an invalid activity_signal.")

    for field in ("completed_units", "total_units", "pid"):
        if type(payload.get(field)) is not int:
            raise RuntimeError(f"Long-run status has an invalid {field}.")
    completed_units = int(payload["completed_units"])
    total_units = int(payload["total_units"])
    if total_units <= 0:
        raise RuntimeError("Long-run status total_units must be positive.")
    if not 0 <= completed_units <= total_units:
        raise RuntimeError("Long-run status completed_units is outside [0, total_units].")
    if int(payload["pid"]) <= 0:
        raise RuntimeError("Long-run status pid must be positive.")
    process_create_time = payload.get("process_create_time_epoch_seconds")
    if process_create_time is not None:
        try:
            _finite_number(
                process_create_time,
                field="process_create_time_epoch_seconds",
                positive=True,
            )
        except ValueError as exc:
            raise RuntimeError(f"Long-run status has invalid process identity data: {exc}") from exc
    if state == "complete" and completed_units != total_units:
        raise RuntimeError("A complete status must report every unit completed.")
    if state == "complete" and activity_signal != "complete":
        raise RuntimeError("A complete status must use the complete activity signal.")
    if state != "complete" and activity_signal == "complete":
        raise RuntimeError("Only a complete status may use the complete activity signal.")

    try:
        nonnegative_fields = (
            "progress_fraction",
            "elapsed_wall_seconds",
            "process_cpu_seconds",
            "average_process_cpu_cores",
            "throughput_units_per_second",
            "seconds_since_progress",
            "interval_wall_seconds",
            "interval_process_cpu_seconds",
            "interval_average_process_cpu_cores",
        )
        for field in nonnegative_fields:
            _finite_number(payload.get(field), field=field)
        for field in ("heartbeat_seconds", "minimum_active_cpu_cores"):
            _finite_number(payload.get(field), field=field, positive=True)
        eta = payload.get("eta_seconds")
        if eta is not None:
            _finite_number(eta, field="eta_seconds")
        no_progress_after = payload.get("no_progress_after_seconds")
        if no_progress_after is not None:
            _finite_number(
                no_progress_after,
                field="no_progress_after_seconds",
                positive=True,
            )
    except ValueError as exc:
        raise RuntimeError(f"Long-run status has invalid numeric data: {exc}") from exc

    expected_fraction = _rounded(completed_units / total_units)
    if not math.isclose(
        float(payload["progress_fraction"]),
        expected_fraction,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise RuntimeError("Long-run status progress_fraction is inconsistent with unit counts.")
    for field in ("no_progress_threshold_reached", "no_progress_without_cpu_signal"):
        if type(payload.get(field)) is not bool:
            raise RuntimeError(f"Long-run status has an invalid {field}.")
    no_progress_without_cpu = bool(payload["no_progress_without_cpu_signal"])
    if no_progress_without_cpu and not bool(payload["no_progress_threshold_reached"]):
        raise RuntimeError("Long-run status no-progress threshold fields are inconsistent.")
    if no_progress_without_cpu != (activity_signal == "no_recent_progress_or_cpu_signal"):
        raise RuntimeError("Long-run status no-progress fields are inconsistent.")

    resident_set_bytes = payload.get("resident_set_bytes")
    if resident_set_bytes is not None and (
        type(resident_set_bytes) is not int or resident_set_bytes < 0
    ):
        raise RuntimeError("Long-run status has an invalid resident_set_bytes.")

    timestamp = payload.get("updated_at_utc")
    if not isinstance(timestamp, str):
        raise RuntimeError("Long-run status omits updated_at_utc.")
    try:
        updated = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise RuntimeError("Long-run status updated_at_utc is invalid.") from exc
    if updated.tzinfo is None or updated.utcoffset() != UTC.utcoffset(updated):
        raise RuntimeError("Long-run status updated_at_utc must be explicitly UTC.")

    try:
        sanitized_detail = _sanitize_operational_detail(
            payload.get("detail"),
            allow_reason=state == "failed",
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Long-run status has invalid operational detail: {exc}") from exc
    if state == "failed" and (sanitized_detail is None or "reason" not in sanitized_detail):
        raise RuntimeError("A failed status must contain a bounded operational reason.")
    return payload


def status_age_seconds(payload: Mapping[str, Any], *, now: datetime | None = None) -> float:
    """Return UTC age and reject snapshots timestamped in the future."""

    raw = payload.get("updated_at_utc")
    if not isinstance(raw, str):
        raise RuntimeError("Long-run status omits updated_at_utc.")
    updated = datetime.fromisoformat(raw)
    if updated.tzinfo is None:
        raise RuntimeError("Long-run status timestamp must include a timezone.")
    observed_now = datetime.now(UTC) if now is None else now
    if observed_now.tzinfo is None:
        raise ValueError("now must include a timezone.")
    age = (observed_now - updated).total_seconds()
    if age < 0.0:
        raise RuntimeError(f"Long-run status timestamp is {-age:.6f} seconds in the future.")
    return age


def classify_long_run_status(
    payload: Mapping[str, Any],
    *,
    process_running: bool | None,
    sampled_cpu_cores: float | None,
    observed_age_seconds: float,
) -> str:
    """Classify observable run state without diagnosing scientific progress."""

    if process_running is not None and type(process_running) is not bool:
        raise ValueError("process_running must be bool or None.")
    if sampled_cpu_cores is not None:
        sampled_cpu_cores = _finite_number(
            sampled_cpu_cores,
            field="sampled_cpu_cores",
        )
    observed_age_seconds = _finite_number(
        observed_age_seconds,
        field="observed_age_seconds",
    )
    state = str(payload.get("state", ""))
    if state in _STATUS_STATES - {"running"}:
        return f"terminal_{state}"
    if process_running is False:
        return "worker_not_running"
    heartbeat = _finite_number(
        payload.get("heartbeat_seconds", 60.0),
        field="heartbeat_seconds",
        positive=True,
    )
    if observed_age_seconds > max(120.0, 2.0 * heartbeat):
        return "status_stale"
    active_threshold = _finite_number(
        payload.get("minimum_active_cpu_cores", 0.05),
        field="minimum_active_cpu_cores",
        positive=True,
    )
    if sampled_cpu_cores is not None and sampled_cpu_cores >= active_threshold:
        return "compute_active"
    if payload.get("no_progress_without_cpu_signal") is True:
        return "no_recent_progress_or_cpu_signal"
    if str(payload.get("activity_signal")) == "unit_progress":
        return "recent_unit_progress"
    return "waiting_for_next_observation"


class LongRunObserver:
    """Write bounded, atomic progress snapshots without claiming scientific output.

    This MVP supports exactly one writer embedded in the same process as the
    worker it observes.  It has no lease, process-tree inspection, automatic
    heartbeat, or scientific resume authority.  A protocol must define the unit
    boundary and call :meth:`emit` between units.  A thread in that same process
    may call :meth:`heartbeat` during one long unit.  The optional stop marker is
    checked only by :meth:`emit` and :meth:`complete` at a safe boundary.
    """

    def __init__(
        self,
        *,
        stage_name: str,
        run_tag: str,
        protocol_tag: str,
        total_units: int,
        unit_name: str,
        status_path: Path,
        heartbeat_seconds: float = 60.0,
        minimum_eta_units: int = 3,
        no_progress_after_seconds: float | None = None,
        minimum_active_cpu_cores: float = 0.05,
        stop_marker: Path | None = None,
        forbidden_roots: Sequence[Path] = (),
        wall_clock: Callable[[], float] = time.perf_counter,
        cpu_clock: Callable[[], float] = time.process_time,
        rss_reader: Callable[[], int | None] = _resident_set_bytes,
        process_create_time_reader: Callable[[], float | None] = _process_create_time_epoch_seconds,
    ) -> None:
        for label, value in (
            ("stage_name", stage_name),
            ("run_tag", run_tag),
            ("protocol_tag", protocol_tag),
            ("unit_name", unit_name),
        ):
            _validated_text(
                value,
                field=label,
                maximum_chars=_MAX_IDENTIFIER_CHARS,
            )
        if type(total_units) is not int or total_units <= 0:
            raise ValueError("total_units must be a positive integer.")
        if type(minimum_eta_units) is not int or minimum_eta_units <= 0:
            raise ValueError("minimum_eta_units must be a positive integer.")
        heartbeat_seconds = _finite_number(
            heartbeat_seconds,
            field="heartbeat_seconds",
            positive=True,
        )
        if no_progress_after_seconds is not None:
            no_progress_after_seconds = _finite_number(
                no_progress_after_seconds,
                field="no_progress_after_seconds",
                positive=True,
            )
        minimum_active_cpu_cores = _finite_number(
            minimum_active_cpu_cores,
            field="minimum_active_cpu_cores",
            positive=True,
        )

        operational_paths = [Path(status_path)]
        if stop_marker is not None:
            operational_paths.append(Path(stop_marker))
        resolved_operational_paths = require_operational_paths_outside(
            operational_paths,
            forbidden_roots=forbidden_roots,
        )
        resolved_status = resolved_operational_paths[0]
        resolved_stop = None if stop_marker is None else resolved_operational_paths[1]
        if resolved_stop is not None:
            _require_no_atomic_path_collision(
                target=resolved_status,
                other_paths=[resolved_stop],
                target_label="status path",
                other_label="stop marker",
            )

        self.stage_name = stage_name
        self.run_tag = run_tag
        self.protocol_tag = protocol_tag
        self.total_units = int(total_units)
        self.unit_name = unit_name
        self.status_path = resolved_status
        self.heartbeat_seconds = heartbeat_seconds
        self.minimum_eta_units = minimum_eta_units
        self.no_progress_after_seconds = no_progress_after_seconds
        self.minimum_active_cpu_cores = minimum_active_cpu_cores
        self.stop_marker = resolved_stop
        self._wall_clock = wall_clock
        self._cpu_clock = cpu_clock
        self._rss_reader = rss_reader
        process_create_time = process_create_time_reader()
        self.process_create_time_epoch_seconds = (
            None
            if process_create_time is None
            else _finite_number(
                process_create_time,
                field="process_create_time_epoch_seconds",
                positive=True,
            )
        )
        self._lock = threading.RLock()
        self._started_wall = float(self._wall_clock())
        self._started_cpu = float(self._cpu_clock())
        if not math.isfinite(self._started_wall) or not math.isfinite(self._started_cpu):
            raise RuntimeError("Observer clocks must return finite values.")
        self._last_emit_wall = self._started_wall - self.heartbeat_seconds
        self._last_progress_wall = self._started_wall
        self._last_sample_wall = self._started_wall
        self._last_sample_cpu = self._started_cpu
        self._last_sample_units = 0
        self._completed_units = 0
        self._terminal_state: str | None = None

    @property
    def completed_units(self) -> int:
        with self._lock:
            return self._completed_units

    def _payload(
        self,
        *,
        completed_units: int,
        phase: str,
        state: str,
        now_wall: float,
        now_cpu: float,
        detail: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        elapsed = max(0.0, now_wall - self._started_wall)
        process_cpu = max(0.0, now_cpu - self._started_cpu)
        throughput = completed_units / elapsed if elapsed > 0.0 else 0.0
        if completed_units >= self.minimum_eta_units and throughput > 0.0:
            eta_seconds: float | None = (self.total_units - completed_units) / throughput
        else:
            eta_seconds = None
        seconds_since_progress = max(0.0, now_wall - self._last_progress_wall)
        no_progress_threshold_reached = bool(
            self.no_progress_after_seconds is not None
            and completed_units < self.total_units
            and seconds_since_progress >= self.no_progress_after_seconds
        )
        interval_wall = max(0.0, now_wall - self._last_sample_wall)
        interval_cpu = max(0.0, now_cpu - self._last_sample_cpu)
        interval_cpu_cores = interval_cpu / interval_wall if interval_wall > 0.0 else 0.0
        unit_progress = completed_units > self._last_sample_units
        cpu_active = interval_cpu_cores >= self.minimum_active_cpu_cores
        no_progress_without_cpu = (
            no_progress_threshold_reached and not unit_progress and not cpu_active
        )
        activity_signal = (
            "complete"
            if state == "complete"
            else "unit_progress"
            if unit_progress
            else "cpu_active_between_units"
            if cpu_active
            else "no_recent_progress_or_cpu_signal"
            if no_progress_without_cpu
            else "awaiting_next_unit"
        )
        rss = self._rss_reader()
        if rss is not None and (type(rss) is not int or rss < 0):
            raise RuntimeError("rss_reader must return a nonnegative integer or None.")
        payload: dict[str, Any] = {
            "schema_version": _STATUS_SCHEMA,
            "kind": "operational_progress_not_scientific_evidence",
            "observer_scope": "single_writer_same_process_worker",
            "resume_authorized": False,
            "stage_name": self.stage_name,
            "run_tag": self.run_tag,
            "protocol_tag": self.protocol_tag,
            "phase": phase,
            "state": state,
            "unit_name": self.unit_name,
            "completed_units": completed_units,
            "total_units": self.total_units,
            "progress_fraction": _rounded(completed_units / self.total_units),
            "elapsed_wall_seconds": _rounded(elapsed),
            "process_cpu_seconds": _rounded(process_cpu),
            "average_process_cpu_cores": (
                _rounded(process_cpu / elapsed) if elapsed > 0.0 else 0.0
            ),
            "throughput_units_per_second": _rounded(throughput),
            "eta_seconds": None if eta_seconds is None else _rounded(eta_seconds),
            "seconds_since_progress": _rounded(seconds_since_progress),
            "interval_wall_seconds": _rounded(interval_wall),
            "interval_process_cpu_seconds": _rounded(interval_cpu),
            "interval_average_process_cpu_cores": _rounded(interval_cpu_cores),
            "activity_signal": activity_signal,
            "no_progress_threshold_reached": no_progress_threshold_reached,
            "no_progress_without_cpu_signal": no_progress_without_cpu,
            "no_progress_after_seconds": self.no_progress_after_seconds,
            "heartbeat_seconds": self.heartbeat_seconds,
            "minimum_active_cpu_cores": self.minimum_active_cpu_cores,
            "resident_set_bytes": rss,
            "pid": os.getpid(),
            "process_create_time_epoch_seconds": self.process_create_time_epoch_seconds,
            "updated_at_utc": utc_now_iso(),
        }
        if detail is not None:
            payload["detail"] = dict(detail)
        return payload

    def emit(
        self,
        completed_units: int,
        *,
        phase: str,
        detail: Mapping[str, Any] | None = None,
        force: bool = False,
    ) -> Path | None:
        """Record monotone progress and honor a stop request at this boundary."""

        with self._lock:
            return self._emit_locked(
                completed_units,
                phase=phase,
                detail=detail,
                force=force,
                honor_stop=True,
            )

    def heartbeat(
        self,
        *,
        phase: str,
        detail: Mapping[str, Any] | None = None,
        force: bool = False,
    ) -> Path | None:
        """Refresh liveness during a long unit without honoring stop mid-unit."""

        with self._lock:
            return self._emit_locked(
                self._completed_units,
                phase=phase,
                detail=detail,
                force=force,
                honor_stop=False,
            )

    def _emit_locked(
        self,
        completed_units: int,
        *,
        phase: str,
        detail: Mapping[str, Any] | None,
        force: bool,
        honor_stop: bool,
        terminal_state: str | None = None,
    ) -> Path | None:
        if self._terminal_state is not None:
            raise RuntimeError(f"Observer is already terminal with state {self._terminal_state}.")
        if type(completed_units) is not int:
            raise TypeError("completed_units must be an integer.")
        if completed_units < self._completed_units:
            raise ValueError("completed_units cannot move backwards.")
        if completed_units > self.total_units:
            raise ValueError("completed_units cannot exceed total_units.")
        _validated_text(
            phase,
            field="phase",
            maximum_chars=_MAX_IDENTIFIER_CHARS,
        )
        safe_detail = _sanitize_operational_detail(detail)

        now_wall = float(self._wall_clock())
        now_cpu = float(self._cpu_clock())
        if not math.isfinite(now_wall) or not math.isfinite(now_cpu):
            raise RuntimeError("Observer clocks must return finite values.")
        if now_wall < self._started_wall or now_cpu < self._started_cpu:
            raise RuntimeError("Observer clocks moved backwards.")
        if completed_units > self._completed_units:
            self._completed_units = completed_units
            self._last_progress_wall = now_wall

        stop_requested = bool(
            honor_stop and self.stop_marker is not None and self.stop_marker.is_file()
        )
        due = (
            force
            or stop_requested
            or completed_units == self.total_units
            or terminal_state is not None
            or now_wall - self._last_emit_wall >= self.heartbeat_seconds
        )
        if not due:
            return None

        state = (
            "stop_requested"
            if stop_requested
            else terminal_state
            if terminal_state is not None
            else "running"
        )
        payload = self._payload(
            completed_units=completed_units,
            phase=phase,
            state=state,
            now_wall=now_wall,
            now_cpu=now_cpu,
            detail=safe_detail,
        )
        written = atomic_write_strict_json(self.status_path, payload)
        self._last_emit_wall = now_wall
        self._last_sample_wall = now_wall
        self._last_sample_cpu = now_cpu
        self._last_sample_units = completed_units
        if stop_requested:
            self._terminal_state = state
            raise StopRequested(
                f"Stop requested for {self.stage_name} at {completed_units}/"
                f"{self.total_units} {self.unit_name}."
            )
        if state in {"complete", "stop_requested"}:
            self._terminal_state = state
        return written

    def complete(
        self,
        *,
        phase: str = "complete",
        detail: Mapping[str, Any] | None = None,
    ) -> Path:
        """Write completion only after every unit was reported through ``emit``."""

        with self._lock:
            if self._terminal_state is not None:
                raise RuntimeError(
                    f"Observer is already terminal with state {self._terminal_state}."
                )
            if self._completed_units != self.total_units:
                raise RuntimeError(
                    "Cannot complete before all units have been reported through emit."
                )
            path = self._emit_locked(
                self._completed_units,
                phase=phase,
                detail=detail,
                force=True,
                honor_stop=True,
                terminal_state="complete",
            )
            if path is None:  # pragma: no cover - force=True makes this unreachable.
                raise RuntimeError("The terminal progress snapshot was not written.")
            return path

    def fail(
        self,
        *,
        phase: str,
        reason: str,
        detail: Mapping[str, Any] | None = None,
    ) -> Path:
        """Write a bounded failure snapshot without serializing a traceback."""

        with self._lock:
            safe_reason = _validated_text(
                reason,
                field="reason",
                maximum_chars=_MAX_FAILURE_REASON_CHARS,
            )
            _validated_text(
                phase,
                field="phase",
                maximum_chars=_MAX_IDENTIFIER_CHARS,
            )
            if self._terminal_state is not None:
                raise RuntimeError(
                    f"Observer is already terminal with state {self._terminal_state}."
                )
            now_wall = float(self._wall_clock())
            now_cpu = float(self._cpu_clock())
            if not math.isfinite(now_wall) or not math.isfinite(now_cpu):
                raise RuntimeError("Observer clocks must return finite values.")
            if now_wall < self._started_wall or now_cpu < self._started_cpu:
                raise RuntimeError("Observer clocks moved backwards.")
            safe_detail = _sanitize_operational_detail(detail)
            failure_detail = {} if safe_detail is None else dict(safe_detail)
            failure_detail["reason"] = safe_reason
            validated_failure_detail = _sanitize_operational_detail(
                failure_detail,
                allow_reason=True,
            )
            if validated_failure_detail is None:  # pragma: no cover - reason is always present.
                raise RuntimeError("Failure detail unexpectedly disappeared.")
            payload = self._payload(
                completed_units=self._completed_units,
                phase=phase,
                state="failed",
                now_wall=now_wall,
                now_cpu=now_cpu,
                detail=validated_failure_detail,
            )
            written = atomic_write_strict_json(self.status_path, payload)
            self._last_emit_wall = now_wall
            self._last_sample_wall = now_wall
            self._last_sample_cpu = now_cpu
            self._last_sample_units = self._completed_units
            self._terminal_state = "failed"
            return written


def write_protocol_bound_checkpoint(
    path: Path,
    *,
    artifact_root: Path,
    stage_name: str,
    protocol_tag: str,
    run_tag: str,
    plan_sha256: str,
    completed_unit_ids: Sequence[str],
    artifact_paths: Sequence[Path],
    forbidden_roots: Sequence[Path] = (),
) -> Path:
    """Write an integrity receipt that deliberately does not authorize resume."""

    resolved_operational_paths = require_operational_paths_outside(
        [path, artifact_root, *artifact_paths],
        forbidden_roots=forbidden_roots,
    )
    resolved_checkpoint = resolved_operational_paths[0]
    resolved_artifact_root = resolved_operational_paths[1]
    resolved_artifacts = resolved_operational_paths[2:]
    if resolved_checkpoint == resolved_artifact_root:
        raise ValueError("Checkpoint path cannot also be the artifact root.")
    if resolved_artifact_root.exists() and not resolved_artifact_root.is_dir():
        raise ValueError("artifact_root must be a directory.")
    if not resolved_artifacts:
        raise ValueError("artifact_paths must contain at least one completed artifact.")
    if len(resolved_artifacts) != len(set(resolved_artifacts)):
        raise ValueError("artifact_paths must resolve to unique files.")
    _require_no_atomic_path_collision(
        target=resolved_checkpoint,
        other_paths=resolved_artifacts,
        target_label="checkpoint path",
        other_label="bound artifact",
    )
    if _SHA256.fullmatch(plan_sha256) is None:
        raise ValueError("plan_sha256 must be a lowercase SHA-256 digest.")
    units: list[str] = []
    for item in completed_unit_ids:
        if not isinstance(item, str):
            raise ValueError("completed_unit_ids must contain only strings.")
        units.append(
            _validated_text(
                item,
                field="completed_unit_ids item",
                maximum_chars=_MAX_IDENTIFIER_CHARS,
            )
        )
    if not units or len(set(units)) != len(units):
        raise ValueError("completed_unit_ids must be nonempty unique strings.")
    for field, value in (
        ("stage_name", stage_name),
        ("protocol_tag", protocol_tag),
        ("run_tag", run_tag),
    ):
        _validated_text(value, field=field, maximum_chars=_MAX_IDENTIFIER_CHARS)
    descriptors = sorted(
        (
            relative_artifact_descriptor(artifact, repo_root=resolved_artifact_root)
            for artifact in resolved_artifacts
        ),
        key=lambda item: str(item["path"]),
    )
    paths = [str(item["path"]) for item in descriptors]
    if len(paths) != len(set(paths)):
        raise ValueError("artifact_paths must be unique.")
    payload = {
        "schema_version": _CHECKPOINT_SCHEMA,
        "kind": "restart_binding_not_resume_authority",
        "binding_scope": "single_writer_integrity_receipt_only",
        "resume_authorized": False,
        "stage_name": stage_name,
        "protocol_tag": protocol_tag,
        "run_tag": run_tag,
        "plan_sha256": plan_sha256,
        "completed_unit_ids": sorted(units),
        "artifacts": descriptors,
        "written_at_utc": utc_now_iso(),
    }
    encoded_payload = (
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    if len(encoded_payload) > _MAX_CHECKPOINT_BYTES:
        raise ValueError(f"Checkpoint exceeds the {_MAX_CHECKPOINT_BYTES}-byte operational limit.")
    return atomic_write_strict_json(resolved_checkpoint, payload)


def verify_protocol_bound_checkpoint(
    path: Path,
    *,
    artifact_root: Path,
    expected_stage_name: str,
    expected_protocol_tag: str,
    expected_run_tag: str,
    expected_plan_sha256: str,
    forbidden_roots: Sequence[Path] = (),
) -> dict[str, Any]:
    """Verify a non-resumable integrity receipt and every bound artifact hash."""

    resolved_control_paths = require_operational_paths_outside(
        [path, artifact_root],
        forbidden_roots=forbidden_roots,
    )
    resolved_checkpoint, resolved_artifact_root = resolved_control_paths
    if resolved_checkpoint == resolved_artifact_root:
        raise ValueError("Checkpoint path cannot also be the artifact root.")
    if not resolved_artifact_root.is_dir():
        raise ValueError("artifact_root must be an existing directory.")
    if _SHA256.fullmatch(expected_plan_sha256) is None:
        raise ValueError("expected_plan_sha256 must be a lowercase SHA-256 digest.")
    payload = _strict_json_object(
        resolved_checkpoint,
        maximum_bytes=_MAX_CHECKPOINT_BYTES,
        label="Checkpoint",
    )
    expected = {
        "schema_version": _CHECKPOINT_SCHEMA,
        "kind": "restart_binding_not_resume_authority",
        "binding_scope": "single_writer_integrity_receipt_only",
        "resume_authorized": False,
        "stage_name": expected_stage_name,
        "protocol_tag": expected_protocol_tag,
        "run_tag": expected_run_tag,
        "plan_sha256": expected_plan_sha256,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RuntimeError(f"Checkpoint identity mismatched on {key}.")
    required_fields = {
        *expected,
        "completed_unit_ids",
        "artifacts",
        "written_at_utc",
    }
    if set(payload) != required_fields:
        raise RuntimeError("Checkpoint fields do not match the bounded integrity-receipt schema.")
    timestamp = payload.get("written_at_utc")
    if not isinstance(timestamp, str):
        raise RuntimeError("Checkpoint omits written_at_utc.")
    try:
        written_at = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise RuntimeError("Checkpoint written_at_utc is invalid.") from exc
    if written_at.tzinfo is None or written_at.utcoffset() != UTC.utcoffset(written_at):
        raise RuntimeError("Checkpoint written_at_utc must be explicitly UTC.")
    units = payload.get("completed_unit_ids")
    if (
        not isinstance(units, list)
        or any(not isinstance(item, str) or not item for item in units)
        or units != sorted(set(units))
    ):
        raise RuntimeError("Checkpoint completed-unit identities are not canonical.")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise RuntimeError("Checkpoint artifact descriptors are missing or empty.")
    observed_paths: list[str] = []
    for index, descriptor in enumerate(artifacts):
        if not isinstance(descriptor, Mapping):
            raise RuntimeError(f"Checkpoint artifact {index} is not a descriptor.")
        descriptor_map = cast(Mapping[str, Any], descriptor)
        if set(descriptor_map) != {"path", "bytes", "sha256"}:
            raise RuntimeError(f"Checkpoint artifact {index} has undeclared descriptor fields.")
        path_value = descriptor_map.get("path")
        bytes_value = descriptor_map.get("bytes")
        sha256_value = descriptor_map.get("sha256")
        if (
            not isinstance(path_value, str)
            or not path_value
            or not isinstance(bytes_value, int)
            or isinstance(bytes_value, bool)
            or bytes_value < 0
            or not isinstance(sha256_value, str)
            or _SHA256.fullmatch(sha256_value) is None
        ):
            raise RuntimeError(f"Checkpoint artifact {index} has invalid descriptor fields.")
        verified = verified_artifact_path(
            descriptor_map,
            repo_root=resolved_artifact_root,
            label=f"checkpoint artifact {index}",
        )
        require_operational_paths_outside(
            [verified],
            forbidden_roots=forbidden_roots,
        )
        try:
            _require_no_atomic_path_collision(
                target=resolved_checkpoint,
                other_paths=[verified],
                target_label="checkpoint path",
                other_label="bound artifact",
            )
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc
        observed_paths.append(str(descriptor.get("path")))
    if observed_paths != sorted(set(observed_paths)):
        raise RuntimeError("Checkpoint artifact paths are not canonical and unique.")
    return payload
