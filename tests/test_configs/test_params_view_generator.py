"""Tests for the generated ``params.yaml`` DVC view."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from scripts.build_params_view import build_params_view

ROOT = Path(__file__).resolve().parents[2]


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    assert isinstance(payload, dict)
    return payload


def test_generated_params_view_matches_tracked_params() -> None:
    assert build_params_view(ROOT) == _load_yaml(ROOT / "params.yaml")
