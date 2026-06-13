"""Read/write helpers for ``feature_config`` — Parquet/YAML alternative to the legacy pickle.

The frozen champion pipeline materializes ``data/processed/feature_config.pkl``,
a plain Python ``dict`` of feature-name lists and a few small scalars (no
custom classes, no fitted transformers). It is therefore trivially
JSON/YAML-serialisable, but the project still keeps the pickle for
backwards-compatibility with downstream stages.

This module exposes a **non-destructive** loader/writer pair that:

* reads the canonical YAML view by default,
* falls back to the legacy pickle when YAML is not available,
* never deletes the pickle on disk (writers operate on the YAML companion only
  unless ``also_pickle=True`` is passed explicitly).

The migration roadmap in ``docs/refactor/FEATURE_CONFIG_PARQUET_PLAN.md``
calls for a dual-write phase before the pickle is retired; this helper
implements the YAML side of that contract.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import joblib
import yaml

DEFAULT_PICKLE_PATH = Path("data/processed/feature_config.pkl")
DEFAULT_YAML_PATH = Path("data/processed/feature_config.yml")


def load_feature_config(
    *,
    repo_root: Path | str | None = None,
    pickle_path: Path | str | None = None,
    yaml_path: Path | str | None = None,
    prefer: str = "yaml",
) -> dict[str, Any]:
    """Load the feature configuration dictionary.

    Args:
        repo_root: If provided, resolve relative paths against this directory.
        pickle_path: Override for the legacy pickle location.
        yaml_path: Override for the YAML companion location.
        prefer: ``"yaml"`` (read YAML with pickle fallback), ``"pickle"``
            (read pickle or raise), or ``"auto"`` (legacy alias for YAML-first
            fallback).

    Returns:
        The same ``dict`` structure used by the rest of the pipeline.
    """
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    pkl = _resolve(root, pickle_path, DEFAULT_PICKLE_PATH)
    yml = _resolve(root, yaml_path, DEFAULT_YAML_PATH)

    if prefer == "yaml":
        if yml.is_file():
            return _load_yaml(yml)
        return _load_pickle(pkl)
    if prefer == "pickle":
        return _load_pickle(pkl)
    if prefer != "auto":
        raise ValueError(f"prefer must be 'auto', 'yaml' or 'pickle', got {prefer!r}")
    if yml.is_file():
        return _load_yaml(yml)
    return _load_pickle(pkl)


def save_feature_config(
    cfg: Mapping[str, Any],
    *,
    repo_root: Path | str | None = None,
    yaml_path: Path | str | None = None,
    pickle_path: Path | str | None = None,
    also_pickle: bool = False,
) -> Path:
    """Persist ``cfg`` to YAML (and optionally to the legacy pickle too).

    Returns the YAML path that was written.
    """
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    yml = _resolve(root, yaml_path, DEFAULT_YAML_PATH)
    yml.parent.mkdir(parents=True, exist_ok=True)
    yml.write_text(
        yaml.safe_dump(dict(cfg), sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )
    if also_pickle:
        pkl = _resolve(root, pickle_path, DEFAULT_PICKLE_PATH)
        pkl.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(dict(cfg), pkl)
    return yml


def pickle_to_yaml(
    pickle_path: Path | str = DEFAULT_PICKLE_PATH,
    yaml_path: Path | str = DEFAULT_YAML_PATH,
) -> Path:
    """One-shot migrator: read an existing pickle and write its YAML companion."""
    cfg = _load_pickle(Path(pickle_path))
    out = Path(yaml_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        yaml.safe_dump(cfg, sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )
    return out


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _resolve(root: Path, override: Path | str | None, default: Path) -> Path:
    candidate = default if override is None else Path(override)
    if candidate.is_absolute():
        return candidate
    return root / candidate


def _load_pickle(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    cfg = joblib.load(path)
    if not isinstance(cfg, dict):
        raise TypeError(f"feature_config pickle at {path} is {type(cfg).__name__}, expected dict.")
    return cfg


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        raise TypeError(f"feature_config YAML at {path} is {type(cfg).__name__}, expected dict.")
    return cfg
