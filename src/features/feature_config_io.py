"""Read/write helpers for the feature configuration artifact.

The feature configuration is a plain Python ``dict`` of feature-name lists and
small scalars. The live pipeline stores it as human-readable YAML plus an
inspection-friendly Parquet table. Loading the legacy pickle remains available
only as an explicit audit escape hatch for old artifacts.

The Parquet representation is deliberately long-form instead of trying to
encode nested Python objects directly: each row stores one list element, dict
entry, or scalar value as JSON with a small Pandera-validated schema.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import yaml

from src.features.schemas import validate_feature_config_table

DEFAULT_PICKLE_PATH = Path("data/processed/feature_config.pkl")
DEFAULT_YAML_PATH = Path("data/processed/feature_config.yml")
DEFAULT_PARQUET_PATH = Path("data/processed/feature_config.parquet")


def load_feature_config(
    *,
    repo_root: Path | str | None = None,
    pickle_path: Path | str | None = None,
    yaml_path: Path | str | None = None,
    parquet_path: Path | str | None = None,
    prefer: str = "yaml",
) -> dict[str, Any]:
    """Load the feature configuration dictionary.

    Args:
        repo_root: If provided, resolve relative paths against this directory.
        pickle_path: Override for the legacy pickle location.
        yaml_path: Override for the YAML companion location.
        parquet_path: Override for the Parquet table location.
        prefer: ``"yaml"`` (strict YAML), ``"parquet"`` (strict Parquet),
            ``"pickle"`` (strict legacy pickle), or ``"auto"`` (best-effort
            legacy compatibility: YAML, then Parquet, then pickle).

    Returns:
        The same ``dict`` structure used by the rest of the pipeline.
    """
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    pkl = _resolve(root, pickle_path, DEFAULT_PICKLE_PATH)
    yml = _resolve(root, yaml_path, DEFAULT_YAML_PATH)
    parquet = _resolve(root, parquet_path, DEFAULT_PARQUET_PATH)

    if prefer == "yaml":
        return _load_yaml(yml)
    if prefer == "parquet":
        return _load_parquet(parquet)
    if prefer == "pickle":
        return _load_pickle(pkl)
    if prefer != "auto":
        raise ValueError(f"prefer must be 'auto', 'yaml', 'parquet' or 'pickle', got {prefer!r}")
    if yml.is_file():
        return _load_yaml(yml)
    if parquet.is_file():
        return _load_parquet(parquet)
    return _load_pickle(pkl)


def save_feature_config(
    cfg: Mapping[str, Any],
    *,
    repo_root: Path | str | None = None,
    yaml_path: Path | str | None = None,
    parquet_path: Path | str | None = None,
    pickle_path: Path | str | None = None,
    also_parquet: bool = False,
    also_pickle: bool = False,
) -> Path:
    """Persist ``cfg`` to YAML and optional companion formats.

    Returns the YAML path that was written.
    """
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    yml = _resolve(root, yaml_path, DEFAULT_YAML_PATH)
    yml.parent.mkdir(parents=True, exist_ok=True)
    yml.write_text(
        yaml.safe_dump(dict(cfg), sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )
    if also_parquet:
        parquet = _resolve(root, parquet_path, DEFAULT_PARQUET_PATH)
        parquet.parent.mkdir(parents=True, exist_ok=True)
        _config_to_frame(cfg).to_parquet(parquet, index=False)
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


def _load_parquet(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    frame = pd.read_parquet(path)
    return _frame_to_config(frame)


def _config_to_frame(cfg: Mapping[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for section in sorted(cfg):
        value = cfg[section]
        if isinstance(value, list):
            rows.extend(
                {
                    "section": section,
                    "kind": "list",
                    "ordinal": ordinal,
                    "key": None,
                    "value_json": json.dumps(item, sort_keys=True),
                }
                for ordinal, item in enumerate(value)
            )
        elif isinstance(value, dict):
            rows.extend(
                {
                    "section": section,
                    "kind": "dict",
                    "ordinal": ordinal,
                    "key": str(key),
                    "value_json": json.dumps(value[key], sort_keys=True),
                }
                for ordinal, key in enumerate(sorted(value))
            )
        else:
            rows.append(
                {
                    "section": section,
                    "kind": "scalar",
                    "ordinal": 0,
                    "key": None,
                    "value_json": json.dumps(value, sort_keys=True),
                }
            )
    return validate_feature_config_table(pd.DataFrame(rows))


def _frame_to_config(frame: pd.DataFrame) -> dict[str, Any]:
    validated = validate_feature_config_table(frame).sort_values(
        ["section", "ordinal", "key"],
        na_position="first",
    )
    cfg: dict[str, Any] = {}
    for section, group in validated.groupby("section", sort=False):
        kinds = set(group["kind"])
        if len(kinds) != 1:
            raise ValueError(f"feature_config section {section!r} has mixed kinds: {kinds}")
        kind = group["kind"].iloc[0]
        if kind == "list":
            cfg[str(section)] = [json.loads(raw) for raw in group["value_json"]]
        elif kind == "dict":
            cfg[str(section)] = {
                str(row["key"]): json.loads(str(row["value_json"]))
                for row in group.to_dict("records")
            }
        elif kind == "scalar":
            if len(group) != 1:
                raise ValueError(f"feature_config scalar section {section!r} has {len(group)} rows")
            cfg[str(section)] = json.loads(str(group["value_json"].iloc[0]))
        else:
            raise ValueError(f"Unsupported feature_config section kind: {kind}")
    return cfg
