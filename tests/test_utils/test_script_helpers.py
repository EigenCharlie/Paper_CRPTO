"""Tests for the consolidated script helpers in ``src/utils/script_helpers.py``."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.utils.script_helpers import (
    artifact_path,
    first_existing,
    load_json,
    load_yaml,
    parse_percent_series,
    resolve_interval_columns,
    try_load_json,
    write_json,
    write_table,
)


def test_load_json_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "payload.json"
    write_json(path, {"b": 2, "a": 1})
    assert load_json(path) == {"a": 1, "b": 2}


def test_write_json_is_lf_only_and_key_sorted(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "payload.json"
    write_json(path, {"z": 1, "a": {"y": 2, "b": 3}})
    raw = path.read_bytes()
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    assert (
        raw.decode("utf-8")
        == json.dumps({"z": 1, "a": {"y": 2, "b": 3}}, indent=2, sort_keys=True) + "\n"
    )


def test_try_load_json_missing_returns_empty(tmp_path: Path) -> None:
    assert try_load_json(tmp_path / "missing.json") == {}


def test_load_yaml(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("alpha: 0.01\nmodes: [a, b]\n", encoding="utf-8")
    assert load_yaml(path) == {"alpha": 0.01, "modes": ["a", "b"]}


def test_write_table_emits_lf_csv_and_tex(tmp_path: Path) -> None:
    frame = pd.DataFrame({"metric": ["auc", "brier"], "value": [0.7127, 0.1546]})
    paths = write_table("t_demo", frame, table_dir=tmp_path, root=tmp_path)
    assert [p.name for p in paths] == ["t_demo.csv", "t_demo.tex"]
    for path in paths:
        assert b"\r" not in path.read_bytes()


def test_write_table_is_idempotent(tmp_path: Path) -> None:
    frame = pd.DataFrame({"a": [1, 2]})
    first = write_table("t_idem", frame, table_dir=tmp_path, root=tmp_path)
    mtimes = [p.stat().st_mtime_ns for p in first]
    second = write_table("t_idem", frame, table_dir=tmp_path, root=tmp_path)
    assert [p.stat().st_mtime_ns for p in second] == mtimes


def test_artifact_path_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GPU_REPLAY_ARTIFACT_ROOT", raising=False)
    assert artifact_path("data/processed/x.parquet") == Path("data/processed/x.parquet")


def test_artifact_path_with_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GPU_REPLAY_ARTIFACT_ROOT", str(tmp_path))
    assert artifact_path("models/x.json") == tmp_path / "models/x.json"


def test_first_existing_prefers_existing(tmp_path: Path) -> None:
    existing = tmp_path / "exact.parquet"
    existing.touch()
    missing = tmp_path / "fallback.parquet"
    assert first_existing(existing, missing) == existing
    assert first_existing(missing, existing) == existing
    assert first_existing(missing) == missing
    with pytest.raises(ValueError, match="at least one"):
        first_existing()


def test_parse_percent_series_numeric_and_strings() -> None:
    numeric = parse_percent_series(pd.Series([12.0, np.nan, 25.0]))
    np.testing.assert_allclose(numeric, [0.12, 0.12, 0.25])
    strings = parse_percent_series(pd.Series([" 12.5% ", "bad", "7%"]))
    np.testing.assert_allclose(strings, [0.125, 0.12, 0.07])


def test_resolve_interval_columns_variants() -> None:
    modern = pd.DataFrame(columns=["y_pred", "pd_low_90", "pd_high_90"])
    assert resolve_interval_columns(modern) == ("y_pred", "pd_low_90", "pd_high_90")
    legacy = pd.DataFrame(columns=["pd_point", "pd_low", "pd_high"])
    assert resolve_interval_columns(legacy) == ("pd_point", "pd_low", "pd_high")
