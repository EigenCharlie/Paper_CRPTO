"""Tests for long-run progress and protocol-bound restart metadata."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.inspect_scientific_run import _inspect_status, _sample_process
from src.utils.long_run_observer import (
    LongRunObserver,
    StopRequested,
    classify_long_run_status,
    load_long_run_status,
    require_operational_paths_outside,
    status_age_seconds,
    verify_protocol_bound_checkpoint,
    write_protocol_bound_checkpoint,
)


class FakeClock:
    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def _observer(
    tmp_path: Path,
    wall: FakeClock,
    cpu: FakeClock,
    *,
    stop_marker: Path | None = None,
    minimum_active_cpu_cores: float = 0.05,
) -> LongRunObserver:
    return LongRunObserver(
        stage_name="unit-stage",
        run_tag="unit-run",
        protocol_tag="protocol/unit",
        total_units=10,
        unit_name="cells",
        status_path=tmp_path / "runtime" / "status.json",
        heartbeat_seconds=30.0,
        minimum_eta_units=2,
        no_progress_after_seconds=120.0,
        minimum_active_cpu_cores=minimum_active_cpu_cores,
        stop_marker=stop_marker,
        wall_clock=wall,
        cpu_clock=cpu,
        rss_reader=lambda: 2_500_000_000,
        process_create_time_reader=lambda: 1_750_000_000.25,
    )


def test_observer_reports_single_core_progress_and_eta(tmp_path: Path) -> None:
    wall = FakeClock()
    cpu = FakeClock()
    observer = _observer(tmp_path, wall, cpu)

    initial = observer.emit(0, phase="solve", force=True)
    wall.value = 60.0
    cpu.value = 59.0
    progress = observer.emit(2, phase="solve")

    assert initial is not None
    assert progress is not None
    payload = json.loads(progress.read_text(encoding="utf-8"))
    assert payload["completed_units"] == 2
    assert payload["progress_fraction"] == pytest.approx(0.2)
    assert payload["average_process_cpu_cores"] == pytest.approx(59.0 / 60.0)
    assert payload["interval_average_process_cpu_cores"] == pytest.approx(59.0 / 60.0)
    assert payload["activity_signal"] == "unit_progress"
    assert payload["no_progress_without_cpu_signal"] is False
    assert payload["observer_scope"] == "single_writer_same_process_worker"
    assert payload["resume_authorized"] is False
    assert payload["eta_seconds"] == pytest.approx(240.0)
    assert payload["resident_set_bytes"] == 2_500_000_000
    assert payload["process_create_time_epoch_seconds"] == pytest.approx(1_750_000_000.25)
    assert payload["kind"] == "operational_progress_not_scientific_evidence"


def test_observer_throttles_writes_and_rejects_backward_progress(tmp_path: Path) -> None:
    wall = FakeClock()
    cpu = FakeClock()
    observer = _observer(tmp_path, wall, cpu)
    observer.emit(1, phase="solve", force=True)

    wall.value = 5.0
    cpu.value = 5.0
    assert observer.emit(2, phase="solve") is None
    with pytest.raises(ValueError, match="backwards"):
        observer.emit(1, phase="solve")


def test_observer_rejects_boolean_completed_units_before_writing(tmp_path: Path) -> None:
    observer = _observer(tmp_path, FakeClock(), FakeClock())
    with pytest.raises(TypeError, match="integer"):
        observer.emit(True, phase="solve", force=True)
    assert not (tmp_path / "runtime" / "status.json").exists()


def test_observer_honors_stop_marker_at_safe_boundary(tmp_path: Path) -> None:
    wall = FakeClock()
    cpu = FakeClock()
    marker = tmp_path / "control" / "stop"
    observer = _observer(tmp_path, wall, cpu, stop_marker=marker)
    marker.parent.mkdir(parents=True)
    marker.write_text("stop\n", encoding="utf-8")

    with pytest.raises(StopRequested, match="1/10"):
        observer.emit(1, phase="solve")

    payload = json.loads((tmp_path / "runtime" / "status.json").read_text(encoding="utf-8"))
    assert payload["state"] == "stop_requested"


def test_heartbeat_reports_busy_solver_without_stopping_mid_unit(tmp_path: Path) -> None:
    wall = FakeClock()
    cpu = FakeClock()
    marker = tmp_path / "control" / "stop"
    observer = _observer(tmp_path, wall, cpu, stop_marker=marker)
    observer.emit(1, phase="solve", force=True)
    marker.parent.mkdir(parents=True)
    marker.write_text("stop\n", encoding="utf-8")

    wall.value = 60.0
    cpu.value = 58.0
    heartbeat = observer.heartbeat(phase="solve", force=True)
    assert heartbeat is not None
    payload = json.loads(heartbeat.read_text(encoding="utf-8"))
    assert payload["completed_units"] == 1
    assert payload["state"] == "running"
    assert payload["activity_signal"] == "cpu_active_between_units"

    with pytest.raises(StopRequested):
        observer.emit(2, phase="solve")


def test_observer_uses_neutral_label_when_cpu_and_progress_are_unobserved(
    tmp_path: Path,
) -> None:
    wall = FakeClock()
    cpu = FakeClock()
    observer = _observer(tmp_path, wall, cpu)
    observer.emit(0, phase="solve", force=True)

    wall.value = 180.0
    cpu.value = 179.0
    busy = observer.emit(0, phase="solve", force=True)
    assert busy is not None
    busy_payload = json.loads(busy.read_text(encoding="utf-8"))
    assert busy_payload["no_progress_threshold_reached"] is True
    assert busy_payload["activity_signal"] == "cpu_active_between_units"
    assert busy_payload["no_progress_without_cpu_signal"] is False

    wall.value = 360.0
    cpu.value = 179.0
    quiet = observer.emit(0, phase="solve", force=True)
    assert quiet is not None
    quiet_payload = json.loads(quiet.read_text(encoding="utf-8"))
    assert quiet_payload["activity_signal"] == "no_recent_progress_or_cpu_signal"
    assert quiet_payload["no_progress_without_cpu_signal"] is True


def test_complete_requires_every_unit_to_have_been_reported(tmp_path: Path) -> None:
    wall = FakeClock()
    cpu = FakeClock()
    observer = _observer(tmp_path, wall, cpu)
    observer.emit(9, phase="solve", force=True)

    with pytest.raises(RuntimeError, match="before all units"):
        observer.complete()
    assert observer.completed_units == 9

    final_progress = observer.emit(10, phase="solve")
    assert final_progress is not None
    assert json.loads(final_progress.read_text(encoding="utf-8"))["state"] == "running"

    completed = observer.complete()
    completed_payload = load_long_run_status(completed)
    assert completed_payload["state"] == "complete"
    assert completed_payload["activity_signal"] == "complete"


@pytest.mark.parametrize("threshold", [0.0, -1.0, float("nan"), float("inf"), True])
def test_observer_requires_positive_finite_cpu_threshold(
    tmp_path: Path,
    threshold: float,
) -> None:
    with pytest.raises(ValueError, match="minimum_active_cpu_cores"):
        _observer(
            tmp_path,
            FakeClock(),
            FakeClock(),
            minimum_active_cpu_cores=threshold,
        )


def test_detail_and_failure_reason_are_bounded_json_scalars(tmp_path: Path) -> None:
    wall = FakeClock()
    cpu = FakeClock()
    observer = _observer(tmp_path, wall, cpu)
    status = observer.emit(
        1,
        phase="solve",
        detail={
            "operation": "frontier solve",
            "current_unit_key": "W1/target/2020-01",
            "attempt": 1,
        },
        force=True,
    )
    assert status is not None
    assert load_long_run_status(status)["detail"]["attempt"] == 1

    with pytest.raises(ValueError, match="not an allowed operational field"):
        observer.emit(
            2,
            phase="solve",
            detail={"objective_value": 0.25},
            force=True,
        )
    assert observer.completed_units == 1
    with pytest.raises(TypeError, match="JSON scalar"):
        observer.emit(
            2,
            phase="solve",
            detail={"message": ["nested values are forbidden"]},
            force=True,
        )
    with pytest.raises(ValueError, match="finite"):
        observer.emit(
            2,
            phase="solve",
            detail={"attempt": float("nan")},
            force=True,
        )
    with pytest.raises(ValueError, match="256 characters"):
        observer.fail(phase="solve", reason="x" * 257)
    with pytest.raises(ValueError, match="single-line"):
        observer.fail(phase="solve", reason="line one\nline two")

    failed = observer.fail(phase="solve", reason="bounded synthetic failure")
    failed_payload = load_long_run_status(failed)
    assert failed_payload["detail"] == {"reason": "bounded synthetic failure"}


def test_terminal_failure_cannot_be_overwritten_by_heartbeat(tmp_path: Path) -> None:
    wall = FakeClock()
    cpu = FakeClock()
    observer = _observer(tmp_path, wall, cpu)
    failed = observer.fail(phase="solve", reason="synthetic failure")
    before = failed.read_bytes()

    with pytest.raises(RuntimeError, match="already terminal"):
        observer.heartbeat(phase="solve", force=True)
    with pytest.raises(RuntimeError, match="already terminal"):
        observer.complete()
    assert failed.read_bytes() == before
    assert json.loads(before)["state"] == "failed"

    completed_observer = _observer(tmp_path / "complete", wall, cpu)
    completed_observer.emit(10, phase="solve")
    completed_observer.complete()
    with pytest.raises(RuntimeError, match="already terminal"):
        completed_observer.heartbeat(phase="complete", force=True)


def test_process_inspector_handles_pid_disappearance(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeNoSuchProcess(Exception):
        pass

    class FakePsutil:
        AccessDenied = PermissionError
        NoSuchProcess = FakeNoSuchProcess
        ZombieProcess = ChildProcessError

        @staticmethod
        def Process(pid: int) -> object:
            raise FakeNoSuchProcess(pid)

    monkeypatch.setattr(
        "scripts.inspect_scientific_run.importlib.import_module",
        lambda name: FakePsutil,
    )

    sample = _sample_process(999_999, seconds=0.0)
    assert sample == {
        "process_running": False,
        "sampled_cpu_cores": None,
        "process_metrics_available": True,
        "process_identity_match": None,
        "observed_process_create_time_epoch_seconds": None,
    }


def test_process_inspector_rejects_recycled_pid(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeProcess:
        @staticmethod
        def create_time() -> float:
            return 2_000.0

        @staticmethod
        def cpu_times() -> object:
            raise AssertionError("CPU must not be sampled for a mismatched process identity.")

    class FakePsutil:
        AccessDenied = PermissionError
        NoSuchProcess = ProcessLookupError
        ZombieProcess = ChildProcessError

        @staticmethod
        def Process(pid: int) -> FakeProcess:
            assert pid == 77
            return FakeProcess()

    monkeypatch.setattr(
        "scripts.inspect_scientific_run.importlib.import_module",
        lambda name: FakePsutil,
    )

    sample = _sample_process(
        77,
        seconds=0.0,
        expected_create_time_epoch_seconds=1_000.0,
    )
    assert sample == {
        "process_running": False,
        "sampled_cpu_cores": None,
        "process_metrics_available": True,
        "process_identity_match": False,
        "observed_process_create_time_epoch_seconds": 2_000.0,
    }


def test_inspector_reloads_status_after_sampling(monkeypatch: pytest.MonkeyPatch) -> None:
    initial_payload = {
        "pid": 101,
        "run_tag": "initial",
        "process_create_time_epoch_seconds": 1_000.0,
    }
    latest_payload = {
        "pid": 101,
        "run_tag": "latest",
        "process_create_time_epoch_seconds": 1_000.0,
    }
    payloads = iter([initial_payload, latest_payload])
    aged_payloads: list[dict[str, object]] = []

    monkeypatch.setattr(
        "scripts.inspect_scientific_run.load_long_run_status",
        lambda path: next(payloads),
    )
    monkeypatch.setattr(
        "scripts.inspect_scientific_run._sample_process",
        lambda pid, seconds, expected_create_time_epoch_seconds: {
            "process_running": True,
            "sampled_cpu_cores": 0.5,
            "process_metrics_available": True,
            "process_identity_match": True,
            "observed_process_create_time_epoch_seconds": 1_000.0,
        },
    )

    def fake_age(payload: dict[str, object]) -> float:
        aged_payloads.append(payload)
        return 3.0

    monkeypatch.setattr(
        "scripts.inspect_scientific_run.status_age_seconds",
        fake_age,
    )
    monkeypatch.setattr(
        "scripts.inspect_scientific_run.classify_long_run_status",
        lambda payload, **kwargs: "compute_active",
    )

    result = _inspect_status(Path("unused.json"), sample_seconds=0.1)
    assert result["snapshot"] is latest_payload
    assert aged_payloads == [latest_payload]
    assert result["status_age_seconds"] == 3.0
    assert result["process_sample"]["pid_changed_during_sample"] is False
    assert result["process_sample"]["worker_identity_changed_during_sample"] is False


def test_operational_paths_reject_repository_or_protected_roots(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    outside = require_operational_paths_outside(
        [runtime_root / "status.json"],
        forbidden_roots=[repo_root],
    )
    assert outside == ((runtime_root / "status.json").resolve(),)

    with pytest.raises(ValueError, match="forbidden root"):
        require_operational_paths_outside(
            [repo_root / "models" / "status.json"],
            forbidden_roots=[repo_root],
        )


def test_observer_rejects_status_stop_and_atomic_staging_collisions(
    tmp_path: Path,
) -> None:
    status = tmp_path / "runtime" / "status.json"
    with pytest.raises(ValueError, match="must not collide"):
        _observer(
            tmp_path,
            FakeClock(),
            FakeClock(),
            stop_marker=status,
        )
    with pytest.raises(ValueError, match="must not collide"):
        _observer(
            tmp_path,
            FakeClock(),
            FakeClock(),
            stop_marker=status.with_name(".status.json.tmp-999"),
        )


def test_status_loader_age_and_classification(tmp_path: Path) -> None:
    wall = FakeClock()
    cpu = FakeClock()
    status_path = _observer(tmp_path, wall, cpu).emit(0, phase="solve", force=True)
    assert status_path is not None
    payload = load_long_run_status(status_path)
    updated = datetime.fromisoformat(payload["updated_at_utc"])

    assert status_age_seconds(
        payload,
        now=updated + timedelta(seconds=15),
    ) == pytest.approx(15.0)
    assert (
        classify_long_run_status(
            payload,
            process_running=True,
            sampled_cpu_cores=0.95,
            observed_age_seconds=15.0,
        )
        == "compute_active"
    )
    assert (
        classify_long_run_status(
            {
                **payload,
                "activity_signal": "no_recent_progress_or_cpu_signal",
                "no_progress_without_cpu_signal": True,
            },
            process_running=True,
            sampled_cpu_cores=0.0,
            observed_age_seconds=60.0,
        )
        == "no_recent_progress_or_cpu_signal"
    )
    assert (
        classify_long_run_status(
            payload,
            process_running=False,
            sampled_cpu_cores=None,
            observed_age_seconds=15.0,
        )
        == "worker_not_running"
    )
    assert (
        classify_long_run_status(
            {
                **payload,
                "activity_signal": "no_recent_progress_or_cpu_signal",
                "no_progress_without_cpu_signal": True,
            },
            process_running=True,
            sampled_cpu_cores=0.95,
            observed_age_seconds=24 * 60 * 60,
        )
        == "status_stale"
    )

    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"kind": "scientific_result"}\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="not a long-run"):
        load_long_run_status(invalid)
    with pytest.raises(ValueError, match="timezone"):
        status_age_seconds(payload, now=datetime(2026, 7, 30))
    with pytest.raises(RuntimeError, match="future"):
        status_age_seconds(payload, now=updated - timedelta(microseconds=1))
    assert updated.tzinfo is not None
    assert updated.tzinfo.utcoffset(updated) == UTC.utcoffset(updated)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "unknown", "schema_version"),
        ("completed_units", -1, r"outside \[0, total_units\]"),
        ("completed_units", 11, r"outside \[0, total_units\]"),
        ("total_units", 0, "must be positive"),
        ("pid", True, "invalid pid"),
        ("process_create_time_epoch_seconds", 0.0, "identity data"),
        ("minimum_active_cpu_cores", 0.0, "must be positive"),
        ("minimum_active_cpu_cores", float("inf"), "strict JSON"),
        ("state", "mystery", "invalid state"),
        ("progress_fraction", 0.75, "inconsistent"),
    ],
)
def test_status_loader_rejects_invalid_or_inconsistent_fields(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    status_path = _observer(tmp_path, FakeClock(), FakeClock()).emit(
        0,
        phase="solve",
        force=True,
    )
    assert status_path is not None
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload[field] = value
    status_path.write_text(
        json.dumps(payload, allow_nan=True),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match=message):
        load_long_run_status(status_path)


def test_status_loader_rejects_undeclared_fields_and_duplicate_json_keys(
    tmp_path: Path,
) -> None:
    status_path = _observer(tmp_path, FakeClock(), FakeClock()).emit(
        0,
        phase="solve",
        force=True,
    )
    assert status_path is not None
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload["score"] = 0.7
    status_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="undeclared fields"):
        load_long_run_status(status_path)

    status_path.write_text('{"kind":"x","kind":"y"}', encoding="utf-8")
    with pytest.raises(RuntimeError, match="duplicate JSON key"):
        load_long_run_status(status_path)


def test_checkpoint_binds_identity_and_artifact_hashes(tmp_path: Path) -> None:
    artifact = tmp_path / "partial" / "shard.json"
    artifact.parent.mkdir()
    artifact.write_text('{"rows": 4}\n', encoding="utf-8")
    checkpoint = tmp_path / "runtime" / "checkpoint.json"
    plan_sha256 = "a" * 64

    write_protocol_bound_checkpoint(
        checkpoint,
        artifact_root=tmp_path,
        stage_name="unit-stage",
        protocol_tag="protocol/unit",
        run_tag="unit-run",
        plan_sha256=plan_sha256,
        completed_unit_ids=["cell-002", "cell-001"],
        artifact_paths=[artifact],
    )
    verified = verify_protocol_bound_checkpoint(
        checkpoint,
        artifact_root=tmp_path,
        expected_stage_name="unit-stage",
        expected_protocol_tag="protocol/unit",
        expected_run_tag="unit-run",
        expected_plan_sha256=plan_sha256,
    )
    assert verified["completed_unit_ids"] == ["cell-001", "cell-002"]
    assert verified["resume_authorized"] is False
    assert verified["binding_scope"] == "single_writer_integrity_receipt_only"

    artifact.write_text('{"rows": 5}\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="mismatched"):
        verify_protocol_bound_checkpoint(
            checkpoint,
            artifact_root=tmp_path,
            expected_stage_name="unit-stage",
            expected_protocol_tag="protocol/unit",
            expected_run_tag="unit-run",
            expected_plan_sha256=plan_sha256,
        )


def test_checkpoint_writer_enforces_reader_size_limit_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("x", encoding="utf-8")
    checkpoint = tmp_path / "checkpoint.json"
    monkeypatch.setattr(
        "src.utils.long_run_observer._MAX_CHECKPOINT_BYTES",
        128,
    )

    with pytest.raises(ValueError, match="128-byte"):
        write_protocol_bound_checkpoint(
            checkpoint,
            artifact_root=tmp_path,
            stage_name="unit-stage",
            protocol_tag="protocol/unit",
            run_tag="unit-run",
            plan_sha256="a" * 64,
            completed_unit_ids=["cell-001"],
            artifact_paths=[artifact],
        )
    assert not checkpoint.exists()


def test_checkpoint_verifier_requires_explicit_utc_timestamp(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("x", encoding="utf-8")
    checkpoint = write_protocol_bound_checkpoint(
        tmp_path / "checkpoint.json",
        artifact_root=tmp_path,
        stage_name="unit-stage",
        protocol_tag="protocol/unit",
        run_tag="unit-run",
        plan_sha256="a" * 64,
        completed_unit_ids=["cell-001"],
        artifact_paths=[artifact],
    )
    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    payload["written_at_utc"] = "2026-07-30T00:00:00"
    checkpoint.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="explicitly UTC"):
        verify_protocol_bound_checkpoint(
            checkpoint,
            artifact_root=tmp_path,
            expected_stage_name="unit-stage",
            expected_protocol_tag="protocol/unit",
            expected_run_tag="unit-run",
            expected_plan_sha256="a" * 64,
        )


def test_checkpoint_verifier_rejects_empty_artifact_list(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("x", encoding="utf-8")
    checkpoint = write_protocol_bound_checkpoint(
        tmp_path / "checkpoint.json",
        artifact_root=tmp_path,
        stage_name="unit-stage",
        protocol_tag="protocol/unit",
        run_tag="unit-run",
        plan_sha256="a" * 64,
        completed_unit_ids=["cell-001"],
        artifact_paths=[artifact],
    )
    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    payload["artifacts"] = []
    checkpoint.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="missing or empty"):
        verify_protocol_bound_checkpoint(
            checkpoint,
            artifact_root=tmp_path,
            expected_stage_name="unit-stage",
            expected_protocol_tag="protocol/unit",
            expected_run_tag="unit-run",
            expected_plan_sha256="a" * 64,
        )


def test_checkpoint_rejects_invalid_plan_hash_and_duplicate_units(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="SHA-256"):
        write_protocol_bound_checkpoint(
            tmp_path / "checkpoint.json",
            artifact_root=tmp_path,
            stage_name="unit-stage",
            protocol_tag="protocol/unit",
            run_tag="unit-run",
            plan_sha256="bad",
            completed_unit_ids=["cell-001"],
            artifact_paths=[artifact],
        )
    with pytest.raises(ValueError, match="unique"):
        write_protocol_bound_checkpoint(
            tmp_path / "checkpoint.json",
            artifact_root=tmp_path,
            stage_name="unit-stage",
            protocol_tag="protocol/unit",
            run_tag="unit-run",
            plan_sha256="a" * 64,
            completed_unit_ids=["cell-001", "cell-001"],
            artifact_paths=[artifact],
        )

    with pytest.raises(ValueError, match="must not collide"):
        write_protocol_bound_checkpoint(
            artifact,
            artifact_root=tmp_path,
            stage_name="unit-stage",
            protocol_tag="protocol/unit",
            run_tag="unit-run",
            plan_sha256="a" * 64,
            completed_unit_ids=["cell-001"],
            artifact_paths=[artifact],
        )

    staging_collision = tmp_path / ".checkpoint.json.tmp-999"
    staging_collision.write_text("operational collision", encoding="utf-8")
    with pytest.raises(ValueError, match="must not collide"):
        write_protocol_bound_checkpoint(
            tmp_path / "checkpoint.json",
            artifact_root=tmp_path,
            stage_name="unit-stage",
            protocol_tag="protocol/unit",
            run_tag="unit-run",
            plan_sha256="a" * 64,
            completed_unit_ids=["cell-001"],
            artifact_paths=[staging_collision],
        )


def test_checkpoint_verifier_rejects_artifact_inside_forbidden_root(
    tmp_path: Path,
) -> None:
    protected_root = tmp_path / "repo"
    protected_root.mkdir()
    artifact = protected_root / "protected.json"
    artifact.write_text('{"rows": 4}\n', encoding="utf-8")
    checkpoint = tmp_path / "runtime" / "checkpoint.json"
    write_protocol_bound_checkpoint(
        checkpoint,
        artifact_root=tmp_path,
        stage_name="unit-stage",
        protocol_tag="protocol/unit",
        run_tag="unit-run",
        plan_sha256="a" * 64,
        completed_unit_ids=["cell-001"],
        artifact_paths=[artifact],
    )

    with pytest.raises(ValueError, match="forbidden root"):
        verify_protocol_bound_checkpoint(
            checkpoint,
            artifact_root=tmp_path,
            expected_stage_name="unit-stage",
            expected_protocol_tag="protocol/unit",
            expected_run_tag="unit-run",
            expected_plan_sha256="a" * 64,
            forbidden_roots=[protected_root],
        )
