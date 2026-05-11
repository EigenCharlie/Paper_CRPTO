"""Smoke tests for ``src.utils.pipeline_state``.

The module is read-only and tolerates missing files. These tests verify that
behaviour: no crashes on a partial environment, namespaced lookups work, and
``EXTRACTION_MANIFEST.json`` is merged when present.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.utils.pipeline_state import PipelineState, load_pipeline_state


def test_load_pipeline_state_against_repo_root() -> None:
    state = load_pipeline_state()
    assert isinstance(state, PipelineState)
    # Repo manifest exists in the curated CRPTO export; if it's absent the test
    # still passes as long as the loader did not crash.
    if (state.repo_root / "EXTRACTION_MANIFEST.json").exists():
        assert state.manifest, "manifest should be loaded when the file exists"


def test_get_returns_default_for_missing_path() -> None:
    state = load_pipeline_state()
    assert state.get("does", "not", "exist", default="fallback") == "fallback"
    assert state.get("paper", "evidence", "this_key_is_made_up", default=None) is None


def test_to_dict_is_json_serialisable() -> None:
    state = load_pipeline_state()
    snap = state.to_dict()
    json.dumps(snap)  # must not raise
    assert {"state", "missing", "manifest", "repo_root"} <= snap.keys()


def test_missing_dir_yields_all_files_missing(tmp_path: Path) -> None:
    """A non-existent models dir should report every namespace as missing without raising."""
    state = load_pipeline_state(repo_root=tmp_path, models_dir="nope")
    assert state.state == {}
    assert state.missing, "all configured namespaces should be marked missing"


def test_synthetic_namespace_round_trip(tmp_path: Path) -> None:
    """When a single status JSON exists in tmp_path, it must surface in the namespaced state."""
    models = tmp_path / "models"
    models.mkdir(parents=True)
    payload = {"coverage": {"target": 0.9, "observed": 0.9123}}
    (models / "conformal_policy_status.json").write_text(json.dumps(payload))

    state = load_pipeline_state(repo_root=tmp_path)
    assert state.get("conformal", "policy") == payload
    assert "conformal/policy" not in state.missing
    # The other namespaces remain reported as missing.
    assert state.missing


@pytest.mark.parametrize(
    "namespace",
    [
        ("paper", "evidence"),
        ("paper", "promotion"),
        ("conformal", "policy"),
        ("portfolio", "optimization"),
    ],
)
def test_namespaces_are_addressable(namespace: tuple[str, str]) -> None:
    state = load_pipeline_state()
    # No assertion on truthiness — these may be missing in a partial extract,
    # we just make sure addressing them doesn't blow up.
    _ = state.get(*namespace, default=None)
