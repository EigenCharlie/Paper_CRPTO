"""Aggregator over the many ``models/*_status.json`` files.

The CRPTO pipeline writes one JSON per stage (conformal policy, fairness audit,
SPO comparison, alpha sweep, paper figures, ...). Twenty-plus files end up in
``models/`` with different schemas and overlapping concerns. This module exposes
a single namespaced view that helps both Quarto chapters and Claude Code skills
locate the right slice of state without hard-coding paths in every chunk.

The default read path is safe against a frozen champion build. The writer is
additive for new stage statuses and refuses protected champion status files
unless the caller opts in explicitly.

Example:
    >>> from src.utils.pipeline_state import load_pipeline_state
    >>> state = load_pipeline_state()
    >>> state["conformal"]["policy"]["coverage"]["target"]
    0.9
    >>> state["paper"]["evidence"]["status"]
    'pass'

Reads ``EXTRACTION_MANIFEST.json`` plus every ``models/*_status.json`` that
exists. Missing files are reported under ``state["_missing"]`` rather than
raising — chapters often run in partial environments and should degrade
gracefully.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]


# Namespaced map: target_namespace -> filename(s). ``None`` means optional.
# The first match wins; later entries are tried only if the earlier ones are absent.
_STATE_LAYOUT: dict[tuple[str, ...], list[str]] = {
    ("models", "pd"): ["pd_training_status.json"],
    ("conformal", "policy"): ["conformal_policy_status.json"],
    ("conformal", "variant"): ["conformal_variant_selection_status.json"],
    ("conformal", "sensitivity"): ["conformal_policy_sensitivity_status.json"],
    ("conformal", "width_attribution"): ["pd_conformal_width_attribution_status.json"],
    ("conformal", "cqr"): ["cqr_comparison_status.json"],
    ("conformal", "cqr_mondrian"): ["cqr_mondrian_status.json"],
    ("conformal", "uncertainty_baselines"): ["uncertainty_baselines_status.json"],
    ("conformal", "alpha_sweep"): ["alpha_sweep_status.json"],
    ("portfolio", "optimization"): ["portfolio_optimization_runtime_status.json"],
    ("portfolio", "tradeoff"): ["portfolio_tradeoff_runtime_status.json"],
    ("portfolio", "ab_attribution"): ["ab_attribution_status.json"],
    ("portfolio", "spo_real"): ["spo_real_training_status.json"],
    ("portfolio", "spo_comparison"): ["spo_comparison_status.json"],
    ("fairness", "audit"): ["fairness_audit_status.json"],
    ("fairness", "fairlearn"): ["fairlearn_fairness_status.json"],
    ("governance", "general"): ["governance_status.json"],
    ("governance", "mrm"): ["mrm_report_status.json"],
    ("paper", "promotion"): ["final_project_promotion.json"],
    ("paper", "evidence"): ["crpto_evidence_status.json"],
    ("paper", "journal_package"): ["crpto_journal_package_status.json"],
    ("paper", "figures"): ["paper_figures_status.json"],
}


@dataclass
class PipelineState:
    """Container with the merged state plus diagnostics on what was missing."""

    state: dict[str, Any] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    manifest: dict[str, Any] = field(default_factory=dict)
    repo_root: Path = field(default_factory=lambda: DEFAULT_REPO_ROOT)

    def get(self, *keys: str, default: Any = None) -> Any:
        """Tunnel into the namespaced state, returning ``default`` for any missing key."""
        node: Any = self.state
        for k in keys:
            if isinstance(node, Mapping) and k in node:
                node = node[k]
            else:
                return default
        return node

    def to_dict(self) -> dict[str, Any]:
        """Plain-dict snapshot useful for ``mlflow.log_dict`` or Quarto chunks."""
        return {
            "state": self.state,
            "missing": list(self.missing),
            "manifest": self.manifest,
            "repo_root": str(self.repo_root),
        }


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        return {"_parse_error": str(err), "_path": str(path)}


# Reverse map for the writer: namespace -> canonical filename. The first filename
# of each ``_STATE_LAYOUT`` entry is the writer target so the loader can read it
# back round-trip.
_WRITE_TARGETS: dict[tuple[str, ...], str] = {ns: files[0] for ns, files in _STATE_LAYOUT.items()}

_PROTECTED_WRITE_TARGETS = {
    "final_project_promotion.json",
    "pd_training_status.json",
    "conformal_policy_status.json",
}


def _deep_merge(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = dict(left)
    for key, value in right.items():
        previous = merged.get(key)
        if isinstance(previous, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(previous, value)
        else:
            merged[key] = value
    return merged


def write_pipeline_state(
    namespace: str | tuple[str, ...],
    payload: dict[str, Any],
    *,
    repo_root: Path | str | None = None,
    models_dir: str = "models",
    merge: bool = False,
    allow_protected: bool = False,
) -> Path:
    """Write a status JSON for ``namespace`` and return the path it landed on.

    Use either a tuple (``("conformal", "policy")``) or the slash form
    (``"conformal/policy"``). Unknown namespaces fall back to
    ``models/<namespace>_status.json`` so callers don't have to declare ahead.

    Args:
        namespace: Identifier as it would appear in :func:`load_pipeline_state`.
        payload: JSON-serialisable dict to persist.
        repo_root: Defaults to the repository root inferred from this file.
        models_dir: Sub-directory holding status JSONs.
        merge: When True and the target file exists, recursively merges
            ``payload`` into the previous content. When False, overwrites.
        allow_protected: Must be True to write status files tied to the frozen
            champion/promotion contract.

    Returns:
        The :class:`pathlib.Path` the JSON was written to.
    """
    if isinstance(namespace, str):
        parts = tuple(p for p in namespace.split("/") if p)
    else:
        parts = tuple(namespace)
    if not parts:
        raise ValueError("namespace must be a non-empty tuple or 'a/b' string.")

    target_name = _WRITE_TARGETS.get(parts)
    if target_name is None:
        target_name = "_".join(parts) + "_status.json"

    root = Path(repo_root) if repo_root else DEFAULT_REPO_ROOT
    target_path = root / models_dir / target_name
    if target_name in _PROTECTED_WRITE_TARGETS and not allow_protected:
        raise PermissionError(
            f"{target_name} is a protected CRPTO champion status. "
            "Pass allow_protected=True only in an explicit revalidation workflow."
        )
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if merge and target_path.is_file():
        prev = _load_json(target_path)
        if isinstance(prev, dict):
            payload = _deep_merge(prev, payload)

    target_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return target_path


def load_pipeline_state(
    *,
    repo_root: Path | str | None = None,
    models_dir: str = "models",
) -> PipelineState:
    """Merge every known ``models/*_status.json`` into a namespaced dictionary.

    Args:
        repo_root: Defaults to the repository root inferred from this file's path.
        models_dir: Sub-directory holding the JSONs. ``"models"`` by default.
    """
    root = Path(repo_root) if repo_root else DEFAULT_REPO_ROOT
    models = root / models_dir

    state: dict[str, Any] = {}
    missing: list[str] = []

    for ns, files in _STATE_LAYOUT.items():
        loaded: Any = None
        for fname in files:
            candidate = models / fname
            if candidate.is_file():
                loaded = _load_json(candidate)
                break
        if loaded is None:
            missing.append("/".join(ns))
            continue
        _assign(state, ns, loaded)

    manifest_path = root / "EXTRACTION_MANIFEST.json"
    manifest: dict[str, Any] = {}
    if manifest_path.is_file():
        parsed = _load_json(manifest_path)
        if isinstance(parsed, dict):
            manifest = parsed

    return PipelineState(state=state, missing=missing, manifest=manifest, repo_root=root)


def _assign(target: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    node = target
    for k in path[:-1]:
        node = node.setdefault(k, {})
    node[path[-1]] = value
