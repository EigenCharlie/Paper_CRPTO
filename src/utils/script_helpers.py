"""Shared helpers for the publication/orchestration scripts under ``scripts/``.

These consolidate the small ``_load_json`` / ``_write_json`` / ``_write_table``
style functions that were previously copy-pasted across the paper-facing
scripts. Two properties are contractual:

1. **Byte-stable output on every OS.** JSON and table writers always emit
   LF line endings (``newline=""``) so regenerated artifacts stay bit-exact
   with the hashes recorded in ``EXTRACTION_MANIFEST.json`` regardless of
   platform. Writing with platform-default newlines on Windows produces CRLF
   files that break ``just validate-champion``.
2. **Idempotent writes.** ``write_table`` compares against the existing file
   and skips the write when the bytes are unchanged, preserving mtimes and
   keeping DVC/freeze caches quiet.

Scripts that are dependencies of protected DVC stages (``train_pd_model.py``,
``optimize_portfolio.py``, ``generate_conformal_intervals.py``,
``validate_conformal_policy.py``, ``run_portfolio_bound_exact_eval.py``) keep
their local copies until the champion-touching refactor lane migrates them
behind a drift gate.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    """Load a UTF-8 JSON file into a dict."""
    return json.loads(path.read_text(encoding="utf-8"))


def try_load_json(path: Path) -> dict[str, Any]:
    """Load a UTF-8 JSON file, returning ``{}`` when the file does not exist."""
    if not path.exists():
        return {}
    return load_json(path)


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a UTF-8 YAML file into a dict."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write ``payload`` as indented, key-sorted JSON with LF line endings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )


def write_table(
    name: str,
    frame: pd.DataFrame,
    *,
    table_dir: Path,
    root: Path = REPO_ROOT,
) -> list[Path]:
    """Write a publication table as ``<name>.csv`` and ``<name>.tex``.

    Output is LF-only and the write is skipped when the on-disk bytes already
    match, so frozen tables under ``reports/crpto/tables`` keep their manifest
    hashes when regenerated from unchanged inputs.
    """
    table_dir.mkdir(parents=True, exist_ok=True)
    csv_path = table_dir / f"{name}.csv"
    tex_path = table_dir / f"{name}.tex"
    csv_text = frame.to_csv(index=False, lineterminator="\n")
    tex_text = frame.to_latex(
        index=False,
        escape=True,
        float_format=lambda value: f"{value:.6f}",
    )
    for path, text in [(csv_path, csv_text), (tex_path, tex_text)]:
        if path.exists() and path.read_bytes().decode("utf-8") == text:
            continue
        path.write_text(text, encoding="utf-8", newline="")
    print(f"Wrote {csv_path.relative_to(root).as_posix()}")  # noqa: T201
    print(f"Wrote {tex_path.relative_to(root).as_posix()}")  # noqa: T201
    return [csv_path, tex_path]


def artifact_path(path_like: str | Path) -> Path:
    """Resolve a relative artifact path under ``GPU_REPLAY_ARTIFACT_ROOT`` if set."""
    path = Path(path_like)
    root = str(os.environ.get("GPU_REPLAY_ARTIFACT_ROOT", "")).strip()
    return (Path(root) / path) if root else path


def first_existing(*paths: Path) -> Path:
    """Return the first existing path, falling back to the last candidate."""
    if not paths:
        raise ValueError("first_existing requires at least one candidate path")
    for path in paths:
        if path.exists():
            return path
    return paths[-1]


def parse_percent_series(series: pd.Series, *, nan_percent: float = 12.0) -> np.ndarray:
    """Convert a percent-scale column (numeric or ``'12.5%'`` strings) to decimals.

    Missing values are imputed with ``nan_percent`` (in percent units) before
    dividing by 100.
    """
    if pd.api.types.is_numeric_dtype(series):
        values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    else:
        values = (
            series.astype(str)
            .str.strip()
            .str.rstrip("%")
            .pipe(pd.to_numeric, errors="coerce")
            .to_numpy(dtype=float)
        )
    values = np.nan_to_num(values, nan=nan_percent)
    return values / 100.0


def resolve_interval_columns(intervals: pd.DataFrame) -> tuple[str, str, str]:
    """Resolve the point/low/high column names of a conformal-interval frame."""
    col_point = "y_pred" if "y_pred" in intervals.columns else "pd_point"
    col_low = "pd_low_90" if "pd_low_90" in intervals.columns else "pd_low"
    col_high = "pd_high_90" if "pd_high_90" in intervals.columns else "pd_high"
    return col_point, col_low, col_high


# Full policy identity used by the promotion artifacts; scripts that compare
# against partial metric dicts pass a narrower field tuple instead.
POLICY_MATCH_FIELDS = (
    "risk_tolerance",
    "policy_mode",
    "gamma",
    "delta_cap_quantile",
    "tail_focus_quantile",
    "uncertainty_aversion",
    "min_budget_utilization",
    "pd_cap_slack_penalty",
)


def policy_matches(
    row: Any,
    policy: dict[str, Any],
    fields: tuple[str, ...] = POLICY_MATCH_FIELDS,
    *,
    atol: float = 1e-9,
) -> bool:
    """Return True when ``row`` and ``policy`` agree on every policy field.

    ``row`` may be a pandas Series or a plain mapping. String fields compare
    by string equality; numeric fields by absolute tolerance. A field missing
    on either side, or a non-coercible numeric value, is a mismatch.
    """
    for field in fields:
        if field not in row or field not in policy:
            return False
        left = row[field]
        right = policy[field]
        if isinstance(right, str):
            if str(left) != right:
                return False
            continue
        try:
            left_f = float(left)
            right_f = float(right)
        except (TypeError, ValueError):
            return False
        if math.isnan(left_f) or math.isnan(right_f) or abs(left_f - right_f) > atol:
            return False
    return True
