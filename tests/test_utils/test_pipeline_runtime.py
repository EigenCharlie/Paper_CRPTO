from __future__ import annotations

import json
from pathlib import Path

from src.utils.pipeline_runtime import (
    atomic_write_json,
    load_runtime_status,
    runtime_checkpoint_dir,
    runtime_last_artifact_path,
    runtime_status_path,
    write_last_valid_artifact,
    write_runtime_checkpoint,
    write_runtime_status,
)


def _tmp_files(path: Path) -> list[Path]:
    return list(path.parent.glob(f".{path.name}.tmp-*"))


def test_atomic_write_json_replaces_existing_file_without_tmp_leak(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "status.json"

    atomic_write_json(target, {"step": 1})
    atomic_write_json(target, {"step": 2, "ok": True})

    assert json.loads(target.read_text(encoding="utf-8")) == {"step": 2, "ok": True}
    assert target.read_text(encoding="utf-8").endswith("\n")
    assert _tmp_files(target) == []


def test_runtime_status_helpers_write_named_artifacts(tmp_path: Path) -> None:
    assert runtime_status_path("unit_stage") == Path("models/unit_stage_runtime_status.json")

    explicit_status = tmp_path / "models" / "unit_runtime_status.json"
    write_runtime_status(
        "unit_stage",
        phase="complete",
        state="success",
        run_tag="unit-run",
        status_path=explicit_status,
        extra={"rows": 3},
    )
    loaded = load_runtime_status(explicit_status)
    assert loaded["stage_name"] == "unit_stage"
    assert loaded["phase"] == "complete"
    assert loaded["state"] == "success"
    assert loaded["run_tag"] == "unit-run"
    assert loaded["rows"] == 3

    checkpoint = write_runtime_checkpoint(
        "unit_stage",
        "after_load",
        {"rows": 3},
        checkpoint_dir=tmp_path / "checkpoints",
    )
    assert checkpoint.name == "after_load.json"
    assert json.loads(checkpoint.read_text(encoding="utf-8"))["checkpoint_name"] == "after_load"

    last_valid = write_last_valid_artifact(
        "unit_stage",
        artifact_key="table",
        artifact_path="data/processed/unit.parquet",
        run_tag="unit-run",
        manifest_path=tmp_path / "last_valid.json",
    )
    assert json.loads(last_valid.read_text(encoding="utf-8"))["artifact_key"] == "table"
    assert runtime_checkpoint_dir("unit_stage") == Path("models/unit_stage_runtime_checkpoints")
    assert runtime_last_artifact_path("unit_stage") == Path(
        "models/unit_stage_last_valid_artifact.json"
    )


def test_load_runtime_status_is_empty_for_missing_or_corrupt_json(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not-json", encoding="utf-8")

    assert load_runtime_status(missing) == {}
    assert load_runtime_status(corrupt) == {}
