"""Smoke tests for ``src.utils.mlflow_tracing``.

The module must degrade gracefully when MLflow is not installed AND remain
importable even with MLflow present. Real run/artifact logging is exercised by
the scripts themselves; here we only test the public surface contracts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.utils import mlflow_tracing
from src.utils.mlflow_tracing import (
    PAPER_RUN_TAG,
    paper_run,
    register_parquet_dataset,
    set_paper_tags,
    trace,
)


def test_paper_run_tag_constant_matches_champion() -> None:
    assert PAPER_RUN_TAG == "paper-thesis-final-economic-2026-04-06"


def test_trace_decorator_is_transparent_when_mlflow_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When MLflow is unavailable, ``@trace`` must return the function unchanged."""
    monkeypatch.setattr(mlflow_tracing, "_HAS_MLFLOW", False)

    @trace(name="op")
    def f(x: int) -> int:
        return x * 2

    assert f(3) == 6
    # Must not wrap the function (same identity, same docstring/name)
    assert f.__name__ == "f"


def test_set_paper_tags_no_op_when_mlflow_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mlflow_tracing, "_HAS_MLFLOW", False)
    # Should silently no-op without raising.
    set_paper_tags(section="results", policy="bound_aware_276k_economic_champion")


def test_paper_run_yields_none_when_mlflow_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mlflow_tracing, "_HAS_MLFLOW", False)
    with paper_run("smoke") as run:
        assert run is None


def test_register_parquet_dataset_no_op_when_mlflow_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mlflow_tracing, "_HAS_MLFLOW", False)
    # Even if MLflow is present at install time, _HAS_MLFLOW=False must short-circuit.
    assert register_parquet_dataset(tmp_path / "absent.parquet") is None


def test_sha256_of_file_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "blob.bin"
    path.write_bytes(b"crpto" * 1024)
    a = mlflow_tracing._sha256_of_file(path)
    b = mlflow_tracing._sha256_of_file(path)
    assert a == b
    assert len(a) == 64  # SHA256 hex


def test_set_paper_tags_uses_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    """When MLflow is present, ``extra`` keys must be prefixed with ``paper.``."""
    monkeypatch.setattr(mlflow_tracing, "_HAS_MLFLOW", True)
    captured: dict[str, Any] = {}

    class _StubMlflow:
        @staticmethod
        def set_tags(tags: dict[str, Any]) -> None:
            captured.update(tags)

        @staticmethod
        def log_param(key: str, value: Any) -> None:
            captured[key] = value

    monkeypatch.setattr(mlflow_tracing, "mlflow", _StubMlflow)
    set_paper_tags(section="results", policy="point", extra={"variant": "A"})
    assert captured["paper.run_tag"] == PAPER_RUN_TAG
    assert captured["paper.section"] == "results"
    assert captured["paper.policy"] == "point"
    assert captured["paper.variant"] == "A"
