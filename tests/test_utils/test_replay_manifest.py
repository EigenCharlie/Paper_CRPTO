from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.utils import replay_manifest


def test_replay_manifest_round_trips_sections_without_aliasing(tmp_path: Path) -> None:
    manifest_path = tmp_path / "configs" / "baselines" / "unit_manifest.json"
    payload = {"pd": {"model_path": "models/pd.cbm"}, "conformal": {"alpha": 0.1}}

    saved = replay_manifest.save_replay_manifest(payload, manifest_path)
    loaded = replay_manifest.load_replay_manifest(saved)
    section = replay_manifest.manifest_section(loaded, "pd")

    assert saved == manifest_path.resolve()
    assert loaded == payload
    assert section == {"model_path": "models/pd.cbm"}
    section["model_path"] = "changed"
    assert loaded["pd"]["model_path"] == "models/pd.cbm"
    assert replay_manifest.manifest_section(loaded, "missing") == {}
    assert replay_manifest.load_replay_manifest(tmp_path / "missing.json") == {}


def test_artifact_descriptor_reports_repo_relative_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(replay_manifest, "ROOT", tmp_path)
    artifact = tmp_path / "models" / "artifact.txt"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"frozen\n")

    descriptor = replay_manifest.artifact_descriptor("models/artifact.txt")

    assert descriptor["path"] == "models/artifact.txt"
    assert descriptor["exists"] is True
    assert descriptor["sha256"] == hashlib.sha256(b"frozen\n").hexdigest()
    assert replay_manifest.artifact_descriptor("models/missing.txt")["sha256"] is None
