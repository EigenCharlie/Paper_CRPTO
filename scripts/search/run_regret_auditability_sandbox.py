"""Resumable CPU-only sandbox for regret-auditability search planning.

The sandbox is intentionally isolated from the frozen CRPTO champion artifacts.
Its default outputs live outside the repository under
``D:/crpto_experiments/regret_auditability/<run_tag>``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import pickle
import shutil
import sqlite3
import subprocess
import sys
import time
from collections import deque
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.features.feature_config_io import load_feature_config  # noqa: E402
from src.utils.pipeline_runtime import atomic_write_json  # noqa: E402


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return int(default)
    try:
        return int(raw)
    except ValueError:
        return int(default)


def _env_str(name: str, default: str) -> str:
    raw = os.environ.get(name, "").strip()
    return raw or default


SCHEMA_VERSION = "2026-05-12.1"
STAGE_NAME = "regret_auditability_sandbox"
DEFAULT_ARTIFACT_ROOT_BASE = Path("D:/crpto_experiments/regret_auditability")
CHAMPION_PD_CONFIG_PATH = ROOT / "configs" / "crpto_pd_model.yaml"
CHAMPION_PORTFOLIO_POLICY_PATH = ROOT / "models" / "champion_portfolio_policy.json"
DEFAULT_RESERVED_LOGICAL_CPUS = 2
DEFAULT_MIN_AVAILABLE_RAM_GB = 10.0
DEFAULT_HEARTBEAT_SECONDS = 60
DEFAULT_PD_WORKERS = 4
DEFAULT_PD_THREADS = 5
MLFLOW_LOG_SIZE_LIMIT_BYTES = 100 * 1024 * 1024
PD_SMOKE_TRIALS = _env_int("CRPTO_SANDBOX_PD_SMOKE_TRIALS", 12)
PD_BROAD_TRIALS = _env_int("CRPTO_SANDBOX_PD_BROAD_TRIALS", 300)
PD_REFINE_TRIALS = _env_int("CRPTO_SANDBOX_PD_REFINE_TRIALS", 300)
PD_BROAD_TOP_K_LANES = _env_int("CRPTO_SANDBOX_PD_BROAD_TOP_K", 6)
PD_REFINE_TOP_K_LANES = _env_int("CRPTO_SANDBOX_PD_REFINE_TOP_K", 3)
PORTFOLIO_RISK_GRID = _env_str(
    "CRPTO_SANDBOX_PORTFOLIO_RISK_GRID",
    "0.08,0.09,0.10,0.11,0.12,0.13,0.14,0.15,0.155,0.16,0.165,0.17,0.175,0.18,0.19,0.20,0.21,0.22,0.23,0.24,0.25",
)
PORTFOLIO_GAMMA_GRID = _env_str(
    "CRPTO_SANDBOX_PORTFOLIO_GAMMA_GRID",
    "0,0.10,0.20,0.30,0.40,0.425,0.45,0.475,0.50,0.525,0.55,0.575,0.60,0.70,0.80,0.90,1.0",
)
PORTFOLIO_AVERSION_GRID = _env_str(
    "CRPTO_SANDBOX_PORTFOLIO_AVERSION_GRID",
    "0,0.02,0.05,0.10,0.25,0.50",
)
PORTFOLIO_CAP_TAIL_GRID = _env_str(
    "CRPTO_SANDBOX_PORTFOLIO_CAP_TAIL_GRID",
    "0.60,0.75,0.90,1.0",
)
PORTFOLIO_RANDOM_STATES = _env_str("CRPTO_SANDBOX_PORTFOLIO_RANDOM_STATES", "42,52,62")
PORTFOLIO_MAX_CANDIDATES = _env_int("CRPTO_SANDBOX_PORTFOLIO_MAX_CANDIDATES", 100000)
PORTFOLIO_SHORTLIST_TOP_K = _env_int("CRPTO_SANDBOX_PORTFOLIO_SHORTLIST_TOP_K", 1000)

PD_PHASES = {"pd-smoke", "pd-broad", "pd-refine"}
PHASE_CHOICES = (
    "plan",
    "deps",
    "pd-smoke",
    "pd-broad",
    "pd-refine",
    "conformal",
    "portfolio",
    "metrics",
    "all",
)

MONOTONIC_POLICIES: dict[str, dict[str, int]] = {
    "canonical_4": {
        "installment": 1,
        "annual_inc": -1,
        "dti": 1,
        "loan_to_income": 1,
    },
    "affordability_rate_5": {
        "installment": 1,
        "annual_inc": -1,
        "dti": 1,
        "loan_to_income": 1,
        "int_rate": 1,
    },
    "credit_history_7": {
        "installment": 1,
        "annual_inc": -1,
        "dti": 1,
        "loan_to_income": 1,
        "int_rate": 1,
        "delinq_severity": 1,
        "delinq_recency": -1,
    },
    "bureau_utilization_11": {
        "installment": 1,
        "annual_inc": -1,
        "dti": 1,
        "loan_to_income": 1,
        "int_rate": 1,
        "rev_utilization": 1,
        "high_util_pct": 1,
        "bc_util": 1,
        "percent_bc_gt_75": 1,
        "fico_score": -1,
        "credit_age_years": -1,
    },
    "bureau_behavior_15": {
        "installment": 1,
        "annual_inc": -1,
        "dti": 1,
        "loan_to_income": 1,
        "int_rate": 1,
        "delinq_severity": 1,
        "delinq_recency": -1,
        "pub_rec": 1,
        "has_bankruptcy": 1,
        "num_accts_ever_120_pd": 1,
        "num_tl_90g_dpd_24m": 1,
        "num_tl_30dpd": 1,
        "pct_tl_nvr_dlq": -1,
        "fico_score": -1,
        "credit_age_years": -1,
    },
    "inquiry_velocity_12": {
        "installment": 1,
        "annual_inc": -1,
        "dti": 1,
        "loan_to_income": 1,
        "int_rate": 1,
        "inq_last_6mths": 1,
        "inq_last_12m": 1,
        "inq_fi": 1,
        "mths_since_recent_inq": -1,
        "acc_open_past_24mths": 1,
        "num_tl_op_past_12m": 1,
        "fico_score": -1,
    },
}

FEATURE_PROFILES: dict[str, dict[str, Any]] = {
    "core_stable": {
        "description": "Champion-like CatBoost feature set with the stable-core gate enabled.",
        "groups": ["CATBOOST_FEATURES"],
        "stable_core_enabled": True,
    },
    "core_wide": {
        "description": "Champion-like CatBoost feature set without the stable-core gate.",
        "groups": ["CATBOOST_FEATURES"],
        "stable_core_enabled": False,
    },
    "core_woe": {
        "description": "Champion-like CatBoost features plus train-only WOE transforms.",
        "groups": ["CATBOOST_FEATURES", "WOE_FEATURES"],
        "stable_core_enabled": False,
    },
    "bureau_high": {
        "description": "CatBoost core plus high-coverage bureau utilization and balance fields.",
        "groups": ["CATBOOST_FEATURES", "HIGH_COVERAGE_BUREAU_FEATURES"],
        "stable_core_enabled": False,
    },
    "full_challenger": {
        "description": "All materialized challenger features from feature_config.yml.",
        "groups": ["CHALLENGER_FEATURE_POOL_V2"],
        "stable_core_enabled": False,
    },
    "full_challenger_woe": {
        "description": "All materialized challenger features plus WOE transforms.",
        "groups": ["CHALLENGER_FEATURE_POOL_V2", "WOE_FEATURES"],
        "stable_core_enabled": False,
    },
}

AUDITABILITY_WEIGHTS: dict[str, int] = {
    "coverage90_pass": 15,
    "coverage95_pass": 10,
    "min_group_coverage_pass": 15,
    "no_critical_alerts": 10,
    "alpha01_exact_pass": 15,
    "violation_zero": 10,
    "v_within_sqrt_alpha": 10,
    "monotonic_audit_pass": 10,
    "reproducible_resume_manifest": 5,
}

PROTECTED_REPO_PATHS = (
    "EXTRACTION_MANIFEST.json",
    "models/pd_canonical.cbm",
    "models/pd_canonical_calibrator.pkl",
    "models/final_project_promotion.json",
    "models/conformal_policy_status.json",
    "data/processed/conformal_intervals_mondrian.parquet",
)
PROTECTED_REPO_DIRS = (
    "data/processed/portfolio_bound_aware",
    "data/processed/portfolio_bound_aware/rank1_alpha01_bound_aware_276k_full_2026-04-05-1734",
)
PROTECTED_REPO_GLOBS = (
    "data/processed/portfolio_bound_aware/rank1_*",
    "models/portfolio_bound_aware/rank1_*",
)


@dataclass(frozen=True)
class PhaseCommand:
    """A resumable unit the sandbox can plan or execute."""

    name: str
    phase: str
    command: list[str]
    outputs: list[str]
    checkpoint: str
    env: dict[str, str]
    max_workers: int
    cpu_threads: int
    feature_profile: str = ""
    monotonic_policy: str = ""
    lane_id: str = ""
    stdout_log: str = ""
    stderr_log: str = ""


def utc_now_iso() -> str:
    """Return an ISO timestamp in UTC."""
    return datetime.now(tz=UTC).isoformat()


def default_run_tag() -> str:
    """Create a stable human-readable run tag."""
    return datetime.now(tz=UTC).strftime("regret_auditability_%Y%m%d_%H%M%S")


def default_artifact_root(run_tag: str) -> Path:
    """Return the default external artifact root for a run tag."""
    return DEFAULT_ARTIFACT_ROOT_BASE / sanitize_tag(run_tag)


def sanitize_tag(raw: str) -> str:
    """Normalize a user-provided tag for filesystem use."""
    safe = str(raw).strip().replace("/", "_").replace("\\", "_")
    if not safe:
        raise ValueError("run tag cannot be empty")
    return safe


def resolve_artifact_root(raw: str | None, run_tag: str) -> Path:
    """Resolve the user artifact root or the D-drive default."""
    if raw:
        return Path(raw).expanduser().resolve()
    return default_artifact_root(run_tag).resolve()


def _resolve_against_repo(path: str | Path, *, repo_root: Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def assert_safe_output_path(path: str | Path, *, repo_root: Path = ROOT) -> Path:
    """Reject outputs that would overwrite frozen CRPTO artifacts."""
    resolved_repo = repo_root.resolve()
    resolved = _resolve_against_repo(path, repo_root=resolved_repo)
    protected_exact = {(resolved_repo / protected).resolve() for protected in PROTECTED_REPO_PATHS}
    if resolved in protected_exact:
        raise ValueError(f"Refusing to write protected CRPTO artifact: {resolved}")

    for protected_dir in PROTECTED_REPO_DIRS:
        resolved_dir = (resolved_repo / protected_dir).resolve()
        if resolved == resolved_dir or _is_relative_to(resolved, resolved_dir):
            raise ValueError(f"Refusing to write inside protected CRPTO directory: {resolved}")

    if _is_relative_to(resolved, resolved_repo):
        relative = resolved.relative_to(resolved_repo)
        for pattern in PROTECTED_REPO_GLOBS:
            if relative.match(pattern):
                raise ValueError(f"Refusing to write protected CRPTO glob output: {resolved}")
    return resolved


def assert_safe_output_paths(paths: Iterable[str | Path], *, repo_root: Path = ROOT) -> None:
    """Apply frozen-artifact guardrails to many output paths."""
    for path in paths:
        assert_safe_output_path(path, repo_root=repo_root)


def materialize_monotonic_policies() -> dict[str, dict[str, int]]:
    """Return the monotonic policy maps used by the sandbox."""
    return {name: dict(policy) for name, policy in MONOTONIC_POLICIES.items()}


def materialize_feature_profiles() -> dict[str, dict[str, Any]]:
    """Return the feature profile maps used by the sandbox."""
    return {name: dict(profile) for name, profile in FEATURE_PROFILES.items()}


def compute_decision_regret(
    oracle_realized_return: float,
    policy_realized_return: float,
) -> float:
    """Compute decision regret under the same budget and ex-post cap."""
    return float(oracle_realized_return) - float(policy_realized_return)


def compute_auditability_score(metrics: Mapping[str, Any]) -> dict[str, Any]:
    """Score the CRPTO auditability checks on a 0-100 scale."""
    coverage90 = float(metrics.get("coverage90", metrics.get("coverage_90", 0.0)))
    coverage95 = float(metrics.get("coverage95", metrics.get("coverage_95", 0.0)))
    min_group_coverage = float(
        metrics.get("min_group_coverage", metrics.get("min_group_coverage_90", 0.0))
    )
    target90 = float(metrics.get("target_coverage90", metrics.get("target_coverage_90", 0.90)))
    target95 = float(metrics.get("target_coverage95", metrics.get("target_coverage_95", 0.95)))
    min_group_target = float(metrics.get("min_group_coverage_target", 0.88))
    alpha = float(metrics.get("alpha", metrics.get("alpha_exact", 0.01)))
    weighted_v = float(
        metrics.get(
            "weighted_miscoverage_V",
            metrics.get("alpha01_weighted_miscoverage_V", float("inf")),
        )
    )
    violation = float(metrics.get("violation", metrics.get("alpha01_violation", 0.0)))
    checks = {
        "coverage90_pass": coverage90 >= target90,
        "coverage95_pass": coverage95 >= target95,
        "min_group_coverage_pass": min_group_coverage >= min_group_target,
        "no_critical_alerts": int(metrics.get("critical_alerts", 0)) == 0,
        "alpha01_exact_pass": bool(metrics.get("alpha01_exact_pass", False)),
        "violation_zero": abs(violation) <= 1e-12,
        "v_within_sqrt_alpha": weighted_v <= math.sqrt(alpha),
        "monotonic_audit_pass": bool(metrics.get("monotonic_audit_pass", False)),
        "reproducible_resume_manifest": bool(metrics.get("reproducible_resume_manifest", False)),
    }
    score = sum(weight for key, weight in AUDITABILITY_WEIGHTS.items() if checks[key])
    return {
        "score": int(score),
        "max_score": int(sum(AUDITABILITY_WEIGHTS.values())),
        "checks": checks,
        "weights": dict(AUDITABILITY_WEIGHTS),
    }


def load_resume_manifest(path: str | Path) -> dict[str, Any]:
    """Load a sandbox resume manifest if it exists."""
    target = Path(path)
    if not target.exists():
        return {}
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Resume manifest must be a JSON object: {target}")
    return payload


def _format_monotone_constraints(policy: Mapping[str, int]) -> str:
    return ",".join(f"{feature}:{int(direction)}" for feature, direction in policy.items())


def _command_log_files(artifact_root: Path, phase: str, name: str) -> tuple[Path, Path]:
    safe_name = sanitize_tag(name)
    log_root = artifact_root / "logs" / phase
    return log_root / f"{safe_name}.out.log", log_root / f"{safe_name}.err.log"


def _command_env(base_env: Mapping[str, str], *, phase_threads: int) -> dict[str, str]:
    env = dict(base_env)
    threads = str(max(1, int(phase_threads)))
    env.update(
        {
            "OMP_NUM_THREADS": threads,
            "MKL_NUM_THREADS": threads,
            "OPENBLAS_NUM_THREADS": threads,
            "NUMEXPR_NUM_THREADS": threads,
            "VECLIB_MAXIMUM_THREADS": threads,
            "CATBOOST_THREAD_COUNT": threads,
        }
    )
    return env


def _ordered_unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in values:
        value = str(raw)
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _load_feature_config() -> dict[str, Any]:
    return load_feature_config(
        yaml_path=ROOT / "data" / "processed" / "feature_config.yml",
        parquet_path=ROOT / "data" / "processed" / "feature_config.parquet",
        pickle_path=ROOT / "data" / "processed" / "feature_config.pkl",
        prefer="auto",
    )


def _features_from_profile(base_config: Mapping[str, Any], profile_name: str) -> list[str]:
    profile = FEATURE_PROFILES[profile_name]
    features: list[str] = []
    for group_name in profile.get("groups", []):
        values = base_config.get(str(group_name), [])
        if isinstance(values, Sequence) and not isinstance(values, str):
            features.extend(str(value) for value in values)
    return _ordered_unique(features)


def _feature_profile_config(base_config: Mapping[str, Any], profile_name: str) -> dict[str, Any]:
    profile = FEATURE_PROFILES[profile_name]
    materialized = dict(base_config)
    catboost_features = _features_from_profile(base_config, profile_name)
    materialized["CATBOOST_FEATURES"] = catboost_features

    categorical = base_config.get("CATEGORICAL_FEATURES", [])
    if isinstance(categorical, Sequence) and not isinstance(categorical, str):
        materialized["CATEGORICAL_FEATURES"] = [
            str(feature) for feature in categorical if str(feature) in set(catboost_features)
        ]

    logreg_features = list(base_config.get("LOGREG_FEATURES", []) or [])
    woe_features = list(base_config.get("WOE_FEATURES", []) or [])
    materialized["LOGREG_FEATURES"] = _ordered_unique(
        str(feature) for feature in [*logreg_features, *woe_features]
    )
    materialized["SANDBOX_FEATURE_PROFILE"] = {
        "name": profile_name,
        "description": str(profile.get("description", "")),
        "groups": [str(group) for group in profile.get("groups", [])],
        "stable_core_enabled": bool(profile.get("stable_core_enabled", False)),
        "catboost_feature_count": len(catboost_features),
    }
    return materialized


def _write_feature_profile_snapshot(*, artifact_root: Path, profile_name: str) -> Path:
    base_config = _load_feature_config()
    profile_config = _feature_profile_config(base_config, profile_name)
    feature_root = artifact_root / "configs" / "feature_profiles"
    feature_root.mkdir(parents=True, exist_ok=True)
    pkl_path = feature_root / f"{profile_name}.pkl"
    yaml_path = feature_root / f"{profile_name}.yaml"
    with pkl_path.open("wb") as fh:
        pickle.dump(profile_config, fh)
    _write_yaml(
        yaml_path,
        {
            "profile": profile_config["SANDBOX_FEATURE_PROFILE"],
            "catboost_features": profile_config["CATBOOST_FEATURES"],
            "categorical_features": profile_config.get("CATEGORICAL_FEATURES", []),
            "logreg_features": profile_config.get("LOGREG_FEATURES", []),
        },
    )
    assert_safe_output_path(pkl_path)
    assert_safe_output_path(yaml_path)
    return pkl_path


def _lane_id(feature_profile: str, monotonic_policy: str) -> str:
    return f"{feature_profile}__{monotonic_policy}"


def _monotonic_policy_for_feature_profile(
    *,
    policy_name: str,
    feature_profile_name: str,
    feature_profile_path: Path,
) -> dict[str, int]:
    with feature_profile_path.open("rb") as fh:
        feature_config = pickle.load(fh)
    features = set(feature_config.get("CATBOOST_FEATURES", []))
    profile = FEATURE_PROFILES[feature_profile_name]
    if bool(profile.get("stable_core_enabled", False)):
        stable_core_cfg = _load_yaml(ROOT / "configs" / "crpto_pd_model.yaml").get(
            "stable_core", {}
        )
        excluded = stable_core_cfg.get("exclude_features", ["rev_utilization", "high_util_pct"])
        if isinstance(excluded, Sequence) and not isinstance(excluded, str):
            features -= {str(feature) for feature in excluded}
    return {
        feature: direction
        for feature, direction in MONOTONIC_POLICIES[policy_name].items()
        if feature in features
    }


def _float_range(start: float, stop: float, step: float) -> str:
    values: list[str] = []
    current = float(start)
    while current <= stop + step / 10:
        values.append(f"{current:.3f}".rstrip("0").rstrip("."))
        current += step
    return ",".join(values)


def _resource_snapshot(artifact_root: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "captured_at_utc": utc_now_iso(),
        "logical_cpu_count": int(os.cpu_count() or 0),
    }
    try:
        import psutil

        vm = psutil.virtual_memory()
        payload.update(
            {
                "cpu_percent": float(psutil.cpu_percent(interval=0.1)),
                "ram_total_gb": float(vm.total / 1024**3),
                "ram_available_gb": float(vm.available / 1024**3),
            }
        )
    except Exception as exc:  # pragma: no cover - platform probe only
        payload["resource_probe_error"] = str(exc)
    try:
        usage = shutil.disk_usage(artifact_root.anchor or artifact_root)
        payload.update(
            {
                "artifact_root": str(artifact_root),
                "disk_total_gb": float(usage.total / 1024**3),
                "disk_free_gb": float(usage.free / 1024**3),
            }
        )
    except Exception as exc:  # pragma: no cover - platform probe only
        payload["disk_probe_error"] = str(exc)
    return payload


def _write_heartbeat(
    *,
    artifact_root: Path,
    phase: str,
    completed_units: int,
    total_units: int,
    current_best_metric: float | None,
    last_checkpoint_path: Path | None,
    state: str,
) -> Path:
    payload = _resource_snapshot(artifact_root)
    completed = int(completed_units)
    total = int(total_units)
    eta_seconds: float | None = None
    if completed > 0 and total > completed:
        eta_seconds = float((total - completed) / completed)
    payload.update(
        {
            "schema_version": SCHEMA_VERSION,
            "stage_name": STAGE_NAME,
            "phase": phase,
            "state": state,
            "completed_units": completed,
            "total_units": total,
            "eta_units_ratio": eta_seconds,
            "current_best_metric": current_best_metric,
            "last_checkpoint_path": str(last_checkpoint_path or ""),
        }
    )
    heartbeat_path = artifact_root / "heartbeat.json"
    last_error: OSError | None = None
    for attempt in range(6):
        try:
            return atomic_write_json(heartbeat_path, payload)
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.25 * (attempt + 1))
    if last_error is not None:
        fallback_path = artifact_root / f"heartbeat.{os.getpid()}.json"
        return atomic_write_json(fallback_path, payload)
    return heartbeat_path


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _write_yaml(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(dict(payload), sort_keys=False), encoding="utf-8")
    return path


OPTUNA_TRIAL_PARAM_KEYS = {
    "bootstrap_type",
    "grow_policy",
    "learning_rate",
    "l2_leaf_reg",
    "min_data_in_leaf",
    "random_strength",
    "border_count",
    "leaf_estimation_iterations",
    "rsm",
    "depth",
    "max_leaves",
    "subsample",
    "bagging_temperature",
}


def _load_champion_pd_params() -> dict[str, Any]:
    config = _load_yaml(CHAMPION_PD_CONFIG_PATH)
    return dict(_nested_get(config, "model", "params", default={}) or {})


def _sanitize_enqueue_trial_params(
    params: Mapping[str, Any],
    *,
    include_iterations: bool,
) -> dict[str, Any]:
    allowed = set(OPTUNA_TRIAL_PARAM_KEYS)
    if include_iterations:
        allowed.add("iterations")
    trial: dict[str, Any] = {}
    for key, value in dict(params or {}).items():
        key_str = str(key)
        if key_str in allowed:
            trial[key_str] = value
    if str(trial.get("grow_policy", "")).strip() != "Lossguide":
        trial.pop("max_leaves", None)
    if str(trial.get("grow_policy", "")).strip() == "Lossguide":
        trial.pop("depth", None)
    else:
        trial["grow_policy"] = "SymmetricTree"
    if str(trial.get("bootstrap_type", "")).strip() == "Bayesian":
        trial.pop("subsample", None)
    else:
        trial.pop("bagging_temperature", None)
    return {key: value for key, value in trial.items() if value is not None}


def _same_trial_params(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if set(left) != set(right):
        return False
    for key, left_value in left.items():
        right_value = right.get(key)
        if right_value is None:
            return False
        try:
            if abs(float(left_value) - float(right_value)) > 1e-12:
                return False
        except (TypeError, ValueError):
            if str(left_value) != str(right_value):
                return False
    return True


def _append_warm_start_candidate(
    rows: list[dict[str, Any]],
    *,
    source: str,
    params: Mapping[str, Any] | None,
    include_iterations: bool,
) -> None:
    if not isinstance(params, Mapping):
        return
    sanitized = _sanitize_enqueue_trial_params(params, include_iterations=include_iterations)
    if not sanitized:
        return
    if any(_same_trial_params(sanitized, row["params"]) for row in rows):
        return
    rows.append({"source": source, "params": sanitized})


def _pd_warm_start_candidates(
    *,
    artifact_root: Path,
    phase: str,
    lane_id: str,
) -> list[dict[str, Any]]:
    include_iterations = phase == "pd-refine"
    rows: list[dict[str, Any]] = []
    _append_warm_start_candidate(
        rows,
        source="frozen_champion_pd_config",
        params=_load_champion_pd_params(),
        include_iterations=include_iterations,
    )
    previous_phase = _previous_pd_phase(phase)
    if previous_phase is None:
        return rows

    selection = _load_pd_selection(artifact_root, previous_phase)
    selected = selection.get("selected", [])
    if not isinstance(selected, list):
        return rows
    for row in selected:
        if not isinstance(row, Mapping):
            continue
        if row.get("lane_id") == lane_id:
            _append_warm_start_candidate(
                rows,
                source=f"{previous_phase}:same_lane_best",
                params=row.get("best_params"),
                include_iterations=include_iterations,
            )
            break
    for index, row in enumerate(selected[:5], start=1):
        if not isinstance(row, Mapping):
            continue
        _append_warm_start_candidate(
            rows,
            source=f"{previous_phase}:top_{index}:{row.get('lane_id', 'unknown')}",
            params=row.get("best_params"),
            include_iterations=include_iterations,
        )
    return rows


def write_pd_config_snapshot(
    *,
    artifact_root: Path,
    run_tag: str,
    feature_profile_name: str,
    policy_name: str,
    phase: str,
    n_trials: int,
    cpu_threads: int,
    base_params_override: Mapping[str, Any] | None = None,
) -> Path:
    """Write an external PD config snapshot for one feature/policy lane and phase."""
    config = _load_yaml(CHAMPION_PD_CONFIG_PATH)
    feature_profile_path = _write_feature_profile_snapshot(
        artifact_root=artifact_root,
        profile_name=feature_profile_name,
    )
    policy = _monotonic_policy_for_feature_profile(
        policy_name=policy_name,
        feature_profile_name=feature_profile_name,
        feature_profile_path=feature_profile_path,
    )
    lane = _lane_id(feature_profile_name, policy_name)
    phase_root = artifact_root / "pd" / feature_profile_name / policy_name / phase
    profile = FEATURE_PROFILES[feature_profile_name]

    config["feature_source"] = dict(config.get("feature_source", {}) or {})
    config["feature_source"]["feature_config_path"] = str(feature_profile_path)
    config["stable_core"] = dict(config.get("stable_core", {}) or {})
    config["stable_core"]["enabled"] = bool(profile.get("stable_core_enabled", False))
    config["model"] = dict(config.get("model", {}) or {})
    config["model"]["params"] = dict(config["model"].get("params", {}) or {})
    if base_params_override:
        blocked_keys = {
            "task_type",
            "devices",
            "thread_count",
            "allow_writing_files",
            "monotone_constraints",
        }
        config["model"]["params"].update(
            {key: value for key, value in base_params_override.items() if key not in blocked_keys}
        )
    config["model"]["params"].update(
        {
            "task_type": "CPU",
            "devices": "",
            "thread_count": int(cpu_threads),
            "allow_writing_files": False,
            "monotone_constraints": _format_monotone_constraints(policy),
        }
    )
    config["calibration"] = dict(config.get("calibration", {}) or {})
    config["calibration"]["method"] = "venn_abers"
    config["calibration"]["candidates"] = ["venn_abers"]
    config["hpo"] = dict(config.get("hpo", {}) or {})
    config["hpo"].update(
        {
            "enabled": True,
            "n_trials": int(n_trials),
            "sampler": "tpe",
            "pruner": "median",
            "n_startup_trials": min(80, max(10, int(n_trials // 10))),
            "multivariate_tpe": True,
            "group_tpe": True,
            "constant_liar": True,
            "warn_independent_sampling": False,
            "search_space_version": "cb_space_v3_monotone_symmetric",
            "study_storage": f"sqlite:///{(phase_root / 'optuna_pd_catboost.db').as_posix()}",
            "study_name": f"pd_{run_tag}_{lane}_{phase}",
            "load_if_exists": True,
            "storage_heartbeat_interval": 60,
            "storage_grace_period": 180,
            "sqlite_timeout_seconds": 240,
            "retry_failed_trials": 2,
            "n_jobs": 1,
            "constraints_policy": {
                "max_brier_delta": 0.0025,
                "max_ece_delta": 0.0025,
                "min_auc_delta": -0.0010,
            },
        }
    )
    warm_start = _pd_warm_start_candidates(
        artifact_root=artifact_root,
        phase=phase,
        lane_id=lane,
    )
    if warm_start:
        config["hpo"]["enqueue_trials"] = [dict(row["params"]) for row in warm_start]
    if phase == "pd-refine":
        config["hpo"]["search_space_mode"] = "local_refine"
        config["hpo"]["local_refine"] = {
            "enqueue_base_trial": True,
            "iterations": {"low": 2500, "high": 5200, "step": 100},
            "learning_rate": {"low": 0.02, "high": 0.10, "log": True},
            "l2_leaf_reg": {"low": 30.0, "high": 200.0, "log": True},
            "min_data_in_leaf": {"low": 80, "high": 220, "step": 5},
            "rsm": {"low": 0.50, "high": 0.75},
            "bootstrap_type": ["MVS", "Bernoulli"],
            "grow_policy": ["SymmetricTree"],
        }
    config["validation"] = dict(config.get("validation", {}) or {})
    if phase == "pd-smoke":
        seed_replay = {"enabled": True, "top_k_trials": 1, "seeds": [42]}
        walk_forward_enabled = False
    elif phase == "pd-broad":
        seed_replay = {"enabled": True, "top_k_trials": 10, "seeds": [42, 52, 62]}
        walk_forward_enabled = True
    else:
        seed_replay = {
            "enabled": True,
            "top_k_trials": 30,
            "seeds": [42, 52, 62, 72, 82],
        }
        walk_forward_enabled = True
    config["validation"]["seed_replay"] = {
        **seed_replay,
        "prioritize_gate_pass": True,
    }
    config["validation"]["walk_forward"] = dict(config["validation"].get("walk_forward", {}) or {})
    config["validation"]["walk_forward"]["enabled"] = walk_forward_enabled
    config["output"] = {
        "model_path": str(phase_root / "models" / "pd_model.cbm"),
        "default_model_path": str(phase_root / "models" / "pd_default.cbm"),
        "tuned_model_path": str(phase_root / "models" / "pd_tuned.cbm"),
        "canonical_model_path": str(phase_root / "models" / "pd_shadow_canonical.cbm"),
        "conformal_path": str(phase_root / "models" / "pd_calibrator.pkl"),
        "canonical_calibrator_path": str(phase_root / "models" / "pd_shadow_calibrator.pkl"),
        "contract_path": str(phase_root / "models" / "pd_model_contract.json"),
        "status_path": str(phase_root / "models" / "pd_training_status.json"),
        "checkpoint_dir": str(phase_root / "models" / "pd_training_checkpoints"),
        "logreg_model_path": str(phase_root / "models" / "pd_logreg_baseline.pkl"),
        "threshold_semantics_path": str(phase_root / "models" / "threshold_semantics.json"),
        "brier_decomposition_path": str(phase_root / "data" / "brier_decomposition_test.parquet"),
        "murphy_diagram_path": str(phase_root / "data" / "murphy_diagram_test.parquet"),
        "test_predictions_path": str(phase_root / "data" / "test_predictions.parquet"),
        "training_record_path": str(phase_root / "models" / "pd_training_record.pkl"),
        "seed_replay_status_path": str(phase_root / "models" / "pd_hpo_seed_replay_status.json"),
        "shap_dir": str(phase_root / "reports" / "shap"),
        "write_legacy_model_copy": False,
    }
    config["decision_threshold"] = dict(config.get("decision_threshold", {}) or {})
    config["decision_threshold"]["enabled"] = False
    config["decision_threshold"]["fairness_policy_path"] = ""
    config["decision_threshold"]["output_path"] = str(
        phase_root / "models" / "decision_threshold.json"
    )
    config["decision_threshold"]["output_path_v2"] = str(
        phase_root / "models" / "decision_threshold_v2.json"
    )
    config["sandbox_search"] = {
        "run_tag": run_tag,
        "phase": phase,
        "feature_profile": feature_profile_name,
        "monotonic_policy": policy_name,
        "lane_id": lane,
        "effective_monotone_constraints": dict(policy),
        "base_params_from_previous_phase": bool(base_params_override),
        "hpo_warm_start": {
            "enabled": bool(warm_start),
            "n_prior_trials": len(warm_start),
            "sources": [str(row["source"]) for row in warm_start],
        },
        "skip_auxiliary_models": True,
        "skip_diagnostic_exports": True,
        "skip_shap_export": True,
    }
    target = artifact_root / "configs" / f"pd_{lane}_{phase}.yaml"
    assert_safe_output_paths(
        value for value in config["output"].values() if isinstance(value, (str, Path))
    )
    assert_safe_output_path(config["decision_threshold"]["output_path"])
    assert_safe_output_path(config["decision_threshold"]["output_path_v2"])
    return _write_yaml(target, config)


def write_pd_incumbent_config_snapshot(
    *,
    artifact_root: Path,
    run_tag: str,
    phase: str,
    cpu_threads: int,
) -> Path:
    """Write a sandbox-local replay config for the frozen PD champion."""
    config = _load_yaml(CHAMPION_PD_CONFIG_PATH)
    phase_root = artifact_root / "pd_baselines" / "champion" / phase
    config["model"] = dict(config.get("model", {}) or {})
    config["model"]["params"] = dict(config["model"].get("params", {}) or {})
    config["model"]["params"].update(
        {
            "task_type": "CPU",
            "devices": "",
            "thread_count": int(cpu_threads),
            "allow_writing_files": False,
        }
    )
    config["calibration"] = dict(config.get("calibration", {}) or {})
    config["calibration"]["method"] = "venn_abers"
    config["calibration"]["candidates"] = ["venn_abers"]
    config["hpo"] = dict(config.get("hpo", {}) or {})
    config["hpo"].update({"enabled": False, "n_trials": 0})
    config["validation"] = dict(config.get("validation", {}) or {})
    config["validation"]["seed_replay"] = {"enabled": False, "seeds": []}
    config["validation"]["walk_forward"] = dict(config["validation"].get("walk_forward", {}) or {})
    config["validation"]["walk_forward"]["enabled"] = phase != "pd-smoke"
    config["output"] = {
        "model_path": str(phase_root / "models" / "pd_model.cbm"),
        "default_model_path": str(phase_root / "models" / "pd_default.cbm"),
        "tuned_model_path": str(phase_root / "models" / "pd_tuned.cbm"),
        "canonical_model_path": str(phase_root / "models" / "pd_shadow_canonical.cbm"),
        "conformal_path": str(phase_root / "models" / "pd_calibrator.pkl"),
        "canonical_calibrator_path": str(phase_root / "models" / "pd_shadow_calibrator.pkl"),
        "contract_path": str(phase_root / "models" / "pd_model_contract.json"),
        "status_path": str(phase_root / "models" / "pd_training_status.json"),
        "checkpoint_dir": str(phase_root / "models" / "pd_training_checkpoints"),
        "logreg_model_path": str(phase_root / "models" / "pd_logreg_baseline.pkl"),
        "threshold_semantics_path": str(phase_root / "models" / "threshold_semantics.json"),
        "brier_decomposition_path": str(phase_root / "data" / "brier_decomposition_test.parquet"),
        "murphy_diagram_path": str(phase_root / "data" / "murphy_diagram_test.parquet"),
        "test_predictions_path": str(phase_root / "data" / "test_predictions.parquet"),
        "training_record_path": str(phase_root / "models" / "pd_training_record.pkl"),
        "seed_replay_status_path": str(phase_root / "models" / "pd_hpo_seed_replay_status.json"),
        "shap_dir": str(phase_root / "reports" / "shap"),
        "write_legacy_model_copy": False,
    }
    config["decision_threshold"] = dict(config.get("decision_threshold", {}) or {})
    config["decision_threshold"]["enabled"] = False
    config["decision_threshold"]["fairness_policy_path"] = ""
    config["decision_threshold"]["output_path"] = str(
        phase_root / "models" / "decision_threshold.json"
    )
    config["decision_threshold"]["output_path_v2"] = str(
        phase_root / "models" / "decision_threshold_v2.json"
    )
    config["sandbox_search"] = {
        "run_tag": run_tag,
        "phase": phase,
        "candidate_role": "frozen_champion_replay",
        "source_config": str(CHAMPION_PD_CONFIG_PATH),
        "skip_auxiliary_models": True,
        "skip_diagnostic_exports": True,
        "skip_shap_export": True,
    }
    assert_safe_output_paths(
        value for value in config["output"].values() if isinstance(value, (str, Path))
    )
    assert_safe_output_path(config["decision_threshold"]["output_path"])
    assert_safe_output_path(config["decision_threshold"]["output_path_v2"])
    target = artifact_root / "configs" / f"pd_incumbent_champion_{phase}.yaml"
    return _write_yaml(target, config)


def _pd_trials_for_phase(phase: str) -> int:
    if phase == "pd-smoke":
        return PD_SMOKE_TRIALS
    if phase == "pd-broad":
        return PD_BROAD_TRIALS
    if phase == "pd-refine":
        return PD_REFINE_TRIALS
    raise ValueError(f"Unsupported PD phase: {phase}")


def _pd_optuna_complete_trials(
    *,
    phase_root: Path,
    run_tag: str,
    lane_id: str,
    phase: str,
) -> int:
    """Return COMPLETE Optuna trials for the current PD study version."""
    db_path = phase_root / "optuna_pd_catboost.db"
    if not db_path.exists():
        return 0
    study_name = f"pd_{run_tag}_{lane_id}_{phase}__cb_space_v3_monotone_symmetric"
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
        row = con.execute(
            "select study_id from studies where study_name = ? order by study_id desc limit 1",
            (study_name,),
        ).fetchone()
        if row is None:
            con.close()
            return 0
        count = con.execute(
            "select count(*) from trials where study_id = ? and state = 'COMPLETE'",
            (int(row[0]),),
        ).fetchone()[0]
        con.close()
        return int(count)
    except sqlite3.Error:
        return 0


def _pd_remaining_trials(
    *,
    phase_root: Path,
    run_tag: str,
    lane_id: str,
    phase: str,
    target_trials: int,
) -> int:
    complete = _pd_optuna_complete_trials(
        phase_root=phase_root,
        run_tag=run_tag,
        lane_id=lane_id,
        phase=phase,
    )
    return max(0, int(target_trials) - complete)


def _pd_selection_path(artifact_root: Path, phase: str) -> Path:
    return artifact_root / "pd" / "_selection" / f"{phase}_selection.json"


def _pd_selection_limit_for_phase(phase: str) -> int | None:
    if phase == "pd-broad":
        return PD_BROAD_TOP_K_LANES
    if phase == "pd-refine":
        return PD_REFINE_TOP_K_LANES
    return None


def _previous_pd_phase(phase: str) -> str | None:
    if phase == "pd-broad":
        return "pd-smoke"
    if phase == "pd-refine":
        return "pd-broad"
    return None


def _load_pd_selection(artifact_root: Path, phase: str) -> dict[str, Any]:
    path = _pd_selection_path(artifact_root, phase)
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _selected_pd_lanes(artifact_root: Path, phase: str) -> list[tuple[str, str]]:
    all_lanes = [
        (feature_profile, monotonic_policy)
        for feature_profile in FEATURE_PROFILES
        for monotonic_policy in MONOTONIC_POLICIES
    ]
    previous_phase = _previous_pd_phase(phase)
    if previous_phase is None:
        return all_lanes
    selection = _load_pd_selection(artifact_root, previous_phase)
    rows = selection.get("selected", [])
    if not isinstance(rows, list) or not rows:
        return all_lanes
    limit = _pd_selection_limit_for_phase(phase)
    selected_ids = {
        str(row.get("lane_id"))
        for row in rows[:limit]
        if isinstance(row, Mapping) and row.get("lane_id")
    }
    filtered = [
        (feature_profile, monotonic_policy)
        for feature_profile, monotonic_policy in all_lanes
        if _lane_id(feature_profile, monotonic_policy) in selected_ids
    ]
    return filtered or all_lanes


def _load_pickle_record(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        payload = pickle.load(fh)
    return payload if isinstance(payload, dict) else {}


def _nested_get(payload: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, Mapping):
            return default
        current = current.get(key, default)
    return current


def _float_metric(payload: Mapping[str, Any], *paths: tuple[str, ...], default: float) -> float:
    for path in paths:
        value = _nested_get(payload, *path, default=None)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return float(default)


def _rank_pd_candidate_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        (dict(row) for row in rows),
        key=lambda row: (
            -float(row.get("auc_roc", float("-inf"))),
            float(row.get("brier_score", float("inf"))),
            float(row.get("ece", float("inf"))),
            -float(row.get("hpo_best_validation_auc", float("-inf"))),
            -float(row.get("walk_forward_auc_mean", float("-inf"))),
        ),
    )
    for rank, row in enumerate(ranked, start=1):
        row["selection_rank"] = rank
    return ranked


def _pd_candidate_row_from_record(record_path: Path, artifact_root: Path) -> dict[str, Any] | None:
    try:
        relative = record_path.relative_to(artifact_root)
    except ValueError:
        return None
    parts = relative.parts
    if len(parts) < 6 or parts[0] != "pd":
        return None
    feature_profile, monotonic_policy, phase = parts[1], parts[2], parts[3]
    if phase not in PD_PHASES:
        return None
    record = _load_pickle_record(record_path)
    lane = _lane_id(feature_profile, monotonic_policy)
    phase_root = artifact_root / "pd" / feature_profile / monotonic_policy / phase
    return {
        "lane_id": lane,
        "feature_profile": feature_profile,
        "monotonic_policy": monotonic_policy,
        "phase": phase,
        "record_path": str(record_path),
        "model_path": str(phase_root / "models" / "pd_shadow_canonical.cbm"),
        "calibrator_path": str(phase_root / "models" / "pd_shadow_calibrator.pkl"),
        "contract_path": str(phase_root / "models" / "pd_model_contract.json"),
        "auc_roc": _float_metric(
            record,
            ("final_test_metrics", "auc_roc"),
            ("test_metrics", "auc_roc"),
            ("metrics", "auc_roc"),
            default=float("-inf"),
        ),
        "brier_score": _float_metric(
            record,
            ("final_test_metrics", "brier_score"),
            ("test_metrics", "brier_score"),
            ("metrics", "brier_score"),
            default=float("inf"),
        ),
        "ece": _float_metric(
            record,
            ("final_test_metrics", "ece"),
            ("test_metrics", "ece"),
            ("metrics", "ece"),
            default=float("inf"),
        ),
        "hpo_best_validation_auc": _float_metric(
            record,
            ("hpo_best_validation_auc",),
            ("hpo", "best_validation_auc"),
            ("best_validation_auc",),
            default=float("-inf"),
        ),
        "walk_forward_auc_mean": _float_metric(
            record,
            ("walk_forward", "auc_roc_mean"),
            ("walk_forward_metrics", "auc_roc_mean"),
            default=float("-inf"),
        ),
        "best_params": record.get("optuna_best_params")
        or record.get("best_params")
        or _nested_get(record, "hpo", "best_params", default={}),
    }


def _pd_incumbent_row_from_record(
    record_path: Path,
    artifact_root: Path,
    phase: str,
) -> dict[str, Any] | None:
    if not record_path.exists():
        return None
    record = _load_pickle_record(record_path)
    phase_root = artifact_root / "pd_baselines" / "champion" / phase
    return {
        "candidate_role": "frozen_champion_replay",
        "lane_id": "incumbent__frozen_champion",
        "feature_profile": "incumbent",
        "monotonic_policy": "canonical_4",
        "phase": phase,
        "record_path": str(record_path),
        "model_path": str(phase_root / "models" / "pd_shadow_canonical.cbm"),
        "calibrator_path": str(phase_root / "models" / "pd_shadow_calibrator.pkl"),
        "contract_path": str(phase_root / "models" / "pd_model_contract.json"),
        "auc_roc": _float_metric(
            record,
            ("final_test_metrics", "auc_roc"),
            ("test_metrics", "auc_roc"),
            ("metrics", "auc_roc"),
            default=float("-inf"),
        ),
        "brier_score": _float_metric(
            record,
            ("final_test_metrics", "brier_score"),
            ("test_metrics", "brier_score"),
            ("metrics", "brier_score"),
            default=float("inf"),
        ),
        "ece": _float_metric(
            record,
            ("final_test_metrics", "ece"),
            ("test_metrics", "ece"),
            ("metrics", "ece"),
            default=float("inf"),
        ),
        "hpo_best_validation_auc": _float_metric(
            record,
            ("hpo_best_validation_auc",),
            ("hpo", "best_validation_auc"),
            ("best_validation_auc",),
            default=float("-inf"),
        ),
        "walk_forward_auc_mean": _float_metric(
            record,
            ("walk_forward", "auc_roc_mean"),
            ("walk_forward_metrics", "auc_roc_mean"),
            default=float("-inf"),
        ),
        "best_params": record.get("optuna_best_params")
        or record.get("best_params")
        or _nested_get(record, "hpo", "best_params", default={}),
    }


def _select_pd_phase_winners(artifact_root: Path, phase: str) -> Path | None:
    record_paths = sorted(artifact_root.glob(f"pd/*/*/{phase}/models/pd_training_record.pkl"))
    rows = [
        row
        for record_path in record_paths
        if (row := _pd_candidate_row_from_record(record_path, artifact_root)) is not None
    ]
    if not rows:
        return None
    ranked = _rank_pd_candidate_rows(rows)
    incumbent_record = (
        artifact_root / "pd_baselines" / "champion" / phase / "models" / "pd_training_record.pkl"
    )
    incumbent_baseline = _pd_incumbent_row_from_record(incumbent_record, artifact_root, phase)
    selection_path = _pd_selection_path(artifact_root, phase)
    selected_payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": utc_now_iso(),
        "phase": phase,
        "rank_criteria": ["auc_roc desc", "brier_score asc", "ece asc"],
        "incumbent_baseline": incumbent_baseline,
        "selected": ranked,
    }
    atomic_write_json(selection_path, selected_payload)

    best = ranked[0]
    best_models = artifact_root / "pd" / "best" / phase / "models"
    best_models.mkdir(parents=True, exist_ok=True)
    for source_key, target_name in {
        "model_path": "pd_shadow_canonical.cbm",
        "calibrator_path": "pd_shadow_calibrator.pkl",
        "contract_path": "pd_model_contract.json",
        "record_path": "pd_training_record.pkl",
    }.items():
        source = Path(str(best.get(source_key, "")))
        if source.exists():
            shutil.copy2(source, best_models / target_name)
    if phase == "pd-refine":
        final_best = artifact_root / "pd" / "best" / "models"
        final_best.mkdir(parents=True, exist_ok=True)
        for source in best_models.iterdir():
            if source.is_file():
                shutil.copy2(source, final_best / source.name)
    return selection_path


def _previous_best_params_for_lane(
    *,
    artifact_root: Path,
    phase: str,
    lane_id: str,
) -> Mapping[str, Any] | None:
    previous_phase = _previous_pd_phase(phase)
    if previous_phase is None:
        return None
    selection = _load_pd_selection(artifact_root, previous_phase)
    rows = selection.get("selected", [])
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, Mapping) or row.get("lane_id") != lane_id:
            continue
        params = row.get("best_params")
        return params if isinstance(params, Mapping) else None
    return None


def _resolve_pd_candidate_for_conformal(artifact_root: Path, artifact_name: str) -> Path:
    best_path = artifact_root / "pd" / "best" / "models" / artifact_name
    if best_path.exists():
        return best_path
    phase_best = artifact_root / "pd" / "best" / "pd-refine" / "models" / artifact_name
    if phase_best.exists():
        return phase_best
    refined = sorted(artifact_root.glob(f"pd/*/*/pd-refine/models/{artifact_name}"))
    if refined:
        return refined[0]
    canonical = {
        "pd_shadow_canonical.cbm": ROOT / "models" / "pd_canonical.cbm",
        "pd_shadow_calibrator.pkl": ROOT / "models" / "pd_canonical_calibrator.pkl",
    }
    return canonical[artifact_name]


def build_phase_commands(
    *,
    artifact_root: Path,
    run_tag: str,
    phase: str,
    max_workers: int,
    cpu_threads: int,
) -> list[PhaseCommand]:
    """Build commands for the requested sandbox phase."""
    safe_tag = sanitize_tag(run_tag)
    artifact_root = artifact_root.resolve()
    commands: list[PhaseCommand] = []
    base_env = {
        "CRPTO_RUN_TAG": safe_tag,
        "PIPELINE_RUN_TAG": safe_tag,
        "RUN_TAG": safe_tag,
        "CRPTO_OFFICIAL_RUN_TAG": safe_tag,
        "GPU_REPLAY_ARTIFACT_ROOT": str(artifact_root),
        "CRPTO_SANDBOX_ARTIFACT_ROOT": str(artifact_root),
    }
    selected_phases = (
        ["pd-smoke", "pd-broad", "pd-refine", "conformal", "portfolio", "metrics"]
        if phase == "all"
        else [phase]
    )
    for selected_phase in selected_phases:
        phase_workers = (
            int(max_workers) if int(max_workers) > 0 else _default_workers_for_phase(selected_phase)
        )
        phase_threads = (
            int(cpu_threads) if int(cpu_threads) > 0 else _default_threads_for_phase(selected_phase)
        )
        if selected_phase in PD_PHASES:
            incumbent_config_path = write_pd_incumbent_config_snapshot(
                artifact_root=artifact_root,
                run_tag=safe_tag,
                phase=selected_phase,
                cpu_threads=phase_threads,
            )
            incumbent_root = artifact_root / "pd_baselines" / "champion" / selected_phase
            incumbent_outputs = [
                incumbent_root / "models" / "pd_model.cbm",
                incumbent_root / "models" / "pd_training_status.json",
                incumbent_root / "models" / "pd_training_record.pkl",
            ]
            incumbent_command_name = f"{selected_phase}_incumbent__frozen_champion"
            incumbent_stdout_log, incumbent_stderr_log = _command_log_files(
                artifact_root,
                selected_phase,
                incumbent_command_name,
            )
            commands.append(
                PhaseCommand(
                    name=incumbent_command_name,
                    phase=selected_phase,
                    command=[
                        sys.executable,
                        str(ROOT / "scripts" / "train_pd_model.py"),
                        "--config",
                        str(incumbent_config_path),
                        "--hpo_enabled",
                        "false",
                        "--hpo_n_trials",
                        "0",
                        "--walk_forward_enabled",
                        "true" if selected_phase != "pd-smoke" else "false",
                        "--seed_replay_enabled",
                        "false",
                    ],
                    outputs=[str(path) for path in incumbent_outputs],
                    checkpoint=str(incumbent_root / "models" / "pd_training_checkpoints"),
                    env=_command_env(base_env, phase_threads=phase_threads),
                    max_workers=phase_workers,
                    cpu_threads=phase_threads,
                    feature_profile="incumbent",
                    monotonic_policy="canonical_4",
                    lane_id="incumbent__frozen_champion",
                    stdout_log=str(incumbent_stdout_log),
                    stderr_log=str(incumbent_stderr_log),
                )
            )
            n_trials = _pd_trials_for_phase(selected_phase)
            for feature_profile_name, policy_name in _selected_pd_lanes(
                artifact_root,
                selected_phase,
            ):
                lane = _lane_id(feature_profile_name, policy_name)
                base_params = _previous_best_params_for_lane(
                    artifact_root=artifact_root,
                    phase=selected_phase,
                    lane_id=lane,
                )
                config_path = write_pd_config_snapshot(
                    artifact_root=artifact_root,
                    run_tag=safe_tag,
                    feature_profile_name=feature_profile_name,
                    policy_name=policy_name,
                    phase=selected_phase,
                    n_trials=n_trials,
                    cpu_threads=phase_threads,
                    base_params_override=base_params,
                )
                output_root = (
                    artifact_root / "pd" / feature_profile_name / policy_name / selected_phase
                )
                remaining_trials = _pd_remaining_trials(
                    phase_root=output_root,
                    run_tag=safe_tag,
                    lane_id=lane,
                    phase=selected_phase,
                    target_trials=n_trials,
                )
                outputs = [
                    output_root / "models" / "pd_model.cbm",
                    output_root / "models" / "pd_training_status.json",
                    output_root / "models" / "pd_hpo_seed_replay_status.json",
                ]
                command_name = f"{selected_phase}_{lane}"
                stdout_log, stderr_log = _command_log_files(
                    artifact_root,
                    selected_phase,
                    command_name,
                )
                commands.append(
                    PhaseCommand(
                        name=command_name,
                        phase=selected_phase,
                        command=[
                            sys.executable,
                            str(ROOT / "scripts" / "train_pd_model.py"),
                            "--config",
                            str(config_path),
                            "--hpo_enabled",
                            "true",
                            "--hpo_n_trials",
                            str(remaining_trials),
                            "--walk_forward_enabled",
                            "true" if selected_phase != "pd-smoke" else "false",
                            "--seed_replay_enabled",
                            "true",
                        ],
                        outputs=[str(path) for path in outputs],
                        checkpoint=str(output_root / "models" / "pd_training_checkpoints"),
                        env=_command_env(base_env, phase_threads=phase_threads),
                        max_workers=phase_workers,
                        cpu_threads=phase_threads,
                        feature_profile=feature_profile_name,
                        monotonic_policy=policy_name,
                        lane_id=lane,
                        stdout_log=str(stdout_log),
                        stderr_log=str(stderr_log),
                    )
                )
        elif selected_phase == "conformal":
            conformal_root = artifact_root / "conformal" / safe_tag
            pd_model_path = _resolve_pd_candidate_for_conformal(
                artifact_root,
                "pd_shadow_canonical.cbm",
            )
            pd_calibrator_path = _resolve_pd_candidate_for_conformal(
                artifact_root,
                "pd_shadow_calibrator.pkl",
            )
            outputs = [
                conformal_root / "data" / "conformal_intervals_mondrian.parquet",
                conformal_root / "models" / "conformal_results_mondrian.pkl",
                conformal_root / "models" / "pd_conformal_width_attribution_status.json",
            ]
            command_name = "conformal_extensive_grid"
            stdout_log, stderr_log = _command_log_files(
                artifact_root,
                selected_phase,
                command_name,
            )
            commands.append(
                PhaseCommand(
                    name=command_name,
                    phase=selected_phase,
                    command=[
                        sys.executable,
                        str(ROOT / "scripts" / "generate_conformal_intervals.py"),
                        "--artifact_namespace",
                        safe_tag,
                        "--artifact_root",
                        str(artifact_root / "conformal"),
                        "--model_override_path",
                        str(pd_model_path),
                        "--alpha_candidates_90",
                        "0.05,0.075,0.09,0.095,0.10,0.105,0.11,0.125,0.15,0.20",
                        "--alpha_candidates_95",
                        "0.025,0.04,0.045,0.05,0.055,0.06,0.075",
                        "--partition_candidates",
                        "grade,score_decile_mondrian,grade_x_scoreband_mondrian",
                        "--n_score_bins_candidates",
                        "5,10,15,20,30",
                        "--min_group_sizes",
                        "100,150,250,500,1000,2000",
                        "--score_scale_families",
                        "none,bernoulli_sqrt,bernoulli_sqrt_clipped_0.02,bernoulli_sqrt_clipped_0.05",
                        "--calibrator_override_path",
                        str(pd_calibrator_path),
                    ],
                    outputs=[str(path) for path in outputs],
                    checkpoint=str(conformal_root / "checkpoints"),
                    env=_command_env(base_env, phase_threads=phase_threads),
                    max_workers=phase_workers,
                    cpu_threads=phase_threads,
                    stdout_log=str(stdout_log),
                    stderr_log=str(stderr_log),
                )
            )
        elif selected_phase == "portfolio":
            portfolio_root = artifact_root / "portfolio" / safe_tag
            conformal_path = (
                artifact_root
                / "conformal"
                / safe_tag
                / "data"
                / "conformal_intervals_mondrian.parquet"
            )
            outputs = [
                portfolio_root / "data" / "portfolio_bound_aware_frontier.parquet",
                portfolio_root / "data" / "portfolio_bound_aware_bound_eval.parquet",
                portfolio_root / "models" / "portfolio_bound_aware_selection.json",
            ]
            command_name = "portfolio_extensive_frontier"
            stdout_log, stderr_log = _command_log_files(
                artifact_root,
                selected_phase,
                command_name,
            )
            commands.append(
                PhaseCommand(
                    name=command_name,
                    phase=selected_phase,
                    command=[
                        sys.executable,
                        str(ROOT / "scripts" / "search" / "run_portfolio_bound_aware_search.py"),
                        "--config",
                        str(ROOT / "configs" / "crpto_optimization.yaml"),
                        "--conformal-intervals-path",
                        str(conformal_path),
                        "--run-label",
                        safe_tag,
                        "--output-dir",
                        str(portfolio_root / "data"),
                        "--model-dir",
                        str(portfolio_root / "models"),
                        "--incumbent-policy-path",
                        str(CHAMPION_PORTFOLIO_POLICY_PATH),
                        "--incumbent-risk-neighbors",
                        "0.155,0.16,0.165,0.17,0.175,0.18",
                        "--incumbent-gamma-neighbors",
                        "0.425,0.45,0.475,0.50,0.525,0.55,0.575",
                        "--incumbent-policy-modes",
                        "blended_uncertainty,capped_blended_uncertainty,tail_blended_uncertainty,segment_tail_blended_uncertainty,segment_relative_tail_blended_uncertainty",
                        "--risk-grid",
                        PORTFOLIO_RISK_GRID,
                        "--gamma-grid",
                        PORTFOLIO_GAMMA_GRID,
                        "--aversion-grid",
                        PORTFOLIO_AVERSION_GRID,
                        "--delta-cap-grid",
                        PORTFOLIO_CAP_TAIL_GRID,
                        "--tail-focus-grid",
                        PORTFOLIO_CAP_TAIL_GRID,
                        "--policy-modes",
                        "blended_uncertainty,capped_blended_uncertainty,tail_blended_uncertainty,segment_tail_blended_uncertainty,segment_relative_tail_blended_uncertainty",
                        "--alpha-grid",
                        "0.01,0.02,0.03,0.05,0.10,0.15,0.20",
                        "--max-candidates",
                        str(PORTFOLIO_MAX_CANDIDATES),
                        "--shortlist-top-k",
                        str(PORTFOLIO_SHORTLIST_TOP_K),
                        "--random-states",
                        PORTFOLIO_RANDOM_STATES,
                        "--solver-backend",
                        "highs",
                        "--exact-solver-backend",
                        "highs",
                    ],
                    outputs=[str(path) for path in outputs],
                    checkpoint=str(
                        portfolio_root / "models" / "portfolio_bound_aware_runtime_checkpoints"
                    ),
                    env=_command_env(base_env, phase_threads=phase_threads),
                    max_workers=phase_workers,
                    cpu_threads=phase_threads,
                    stdout_log=str(stdout_log),
                    stderr_log=str(stderr_log),
                )
            )
        elif selected_phase == "metrics":
            metrics_path = artifact_root / "metrics" / "frontier_metrics_manifest.json"
            command_name = "metrics_manifest"
            stdout_log, stderr_log = _command_log_files(
                artifact_root,
                selected_phase,
                command_name,
            )
            commands.append(
                PhaseCommand(
                    name=command_name,
                    phase=selected_phase,
                    command=[
                        sys.executable,
                        str(Path(__file__).resolve()),
                        "--run-tag",
                        safe_tag,
                        "--artifact-root",
                        str(artifact_root),
                        "--phase",
                        "plan",
                        "--resume",
                    ],
                    outputs=[str(metrics_path)],
                    checkpoint=str(artifact_root / "metrics"),
                    env=_command_env(base_env, phase_threads=1),
                    max_workers=1,
                    cpu_threads=1,
                    stdout_log=str(stdout_log),
                    stderr_log=str(stderr_log),
                )
            )
        elif selected_phase in {"plan", "deps"}:
            continue
        else:
            raise ValueError(f"Unknown sandbox phase: {selected_phase}")
    for command in commands:
        assert_safe_output_paths(command.outputs)
        assert_safe_output_path(command.checkpoint)
        if command.stdout_log:
            assert_safe_output_path(command.stdout_log)
        if command.stderr_log:
            assert_safe_output_path(command.stderr_log)
    return commands


def _write_dependency_snapshot(path: Path) -> Path:
    packages = [
        "catboost",
        "mapie",
        "optuna",
        "optuna-integration",
        "pyomo",
        "highspy",
        "venn-abers",
        "scikit-learn",
    ]
    cmd = [
        sys.executable,
        "-c",
        (
            "import importlib.metadata as m, json; "
            f"pkgs={packages!r}; "
            "print(json.dumps({p: m.version(p) for p in pkgs}, sort_keys=True))"
        ),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=True)
    payload = json.loads(proc.stdout)
    return atomic_write_json(
        path,
        {
            "schema_version": SCHEMA_VERSION,
            "captured_at_utc": utc_now_iso(),
            "versions": payload,
        },
    )


def _write_frontier_metrics_manifest(*, artifact_root: Path, run_tag: str) -> Path:
    metrics_root = artifact_root / "metrics"
    safe_tag = sanitize_tag(run_tag)
    paths = {
        "pd_incumbent_baseline": artifact_root
        / "pd_baselines"
        / "champion"
        / "pd-smoke"
        / "models"
        / "pd_training_record.pkl",
        "pd_selection": artifact_root / "pd" / "_selection" / "pd-refine_selection.json",
        "pd_model": artifact_root / "pd" / "best" / "models" / "pd_shadow_canonical.cbm",
        "pd_calibrator": artifact_root / "pd" / "best" / "models" / "pd_shadow_calibrator.pkl",
        "conformal_intervals": artifact_root
        / "conformal"
        / safe_tag
        / "data"
        / "conformal_intervals_mondrian.parquet",
        "portfolio_frontier": artifact_root
        / "portfolio"
        / safe_tag
        / "data"
        / "portfolio_bound_aware_frontier.parquet",
        "portfolio_exact": artifact_root
        / "portfolio"
        / safe_tag
        / "data"
        / "portfolio_bound_aware_bound_eval.parquet",
        "portfolio_selection": artifact_root
        / "portfolio"
        / safe_tag
        / "models"
        / "portfolio_bound_aware_selection.json",
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": utc_now_iso(),
        "run_tag": safe_tag,
        "artifact_root": str(artifact_root),
        "artifacts": {
            name: {"path": str(path), "exists": path.exists()} for name, path in paths.items()
        },
        "auditability_weights": dict(AUDITABILITY_WEIGHTS),
        "regret_formula": (
            "oracle_realized_return_same_budget_concentration_and_expost_default_cap "
            "- policy_realized_return"
        ),
    }
    selection_path = paths["pd_selection"]
    if selection_path.exists():
        payload["pd_selection"] = json.loads(selection_path.read_text(encoding="utf-8"))
    return atomic_write_json(metrics_root / "frontier_metrics_manifest.json", payload)


def _write_command_manifest(
    *,
    artifact_root: Path,
    run_tag: str,
    phase: str,
    commands: Sequence[PhaseCommand],
    resume_manifest: Mapping[str, Any],
) -> Path:
    manifest_path = artifact_root / "sandbox_manifest.json"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "stage_name": STAGE_NAME,
        "run_tag": run_tag,
        "phase": phase,
        "artifact_root": str(artifact_root),
        "generated_at_utc": utc_now_iso(),
        "resume_manifest_loaded": bool(resume_manifest),
        "resource_policy": {
            "reserve_logical_cpus": DEFAULT_RESERVED_LOGICAL_CPUS,
            "min_available_ram_gb": DEFAULT_MIN_AVAILABLE_RAM_GB,
            "heartbeat_seconds": DEFAULT_HEARTBEAT_SECONDS,
        },
        "mlflow_tracking": {
            "tracking_uri": _mlflow_tracking_uri(artifact_root),
            "experiment_name": _mlflow_experiment_name(run_tag),
            "scope": "sandbox command/lane registry; Optuna trial detail remains in per-lane storage",
            "size_limit_bytes": MLFLOW_LOG_SIZE_LIMIT_BYTES,
        },
        "monotonic_policies": materialize_monotonic_policies(),
        "feature_profiles": materialize_feature_profiles(),
        "pd_lane_selection": {
            "pd_broad_top_k_from_smoke": PD_BROAD_TOP_K_LANES,
            "pd_refine_top_k_from_broad": PD_REFINE_TOP_K_LANES,
        },
        "incumbent_replay": {
            "enabled": True,
            "pd_config_path": str(CHAMPION_PD_CONFIG_PATH),
            "portfolio_policy_path": str(CHAMPION_PORTFOLIO_POLICY_PATH),
            "pd_baseline_root": str(artifact_root / "pd_baselines" / "champion"),
            "role": "baseline only; never overwrites frozen champion artifacts",
        },
        "pd_warm_start": {
            "enabled": True,
            "sources": [
                "frozen_champion_pd_config",
                "same-lane best params from previous PD phase",
                "top previous-phase PD params as cross-lane priors",
            ],
        },
        "resource_tuned_search_budget": {
            "pd_smoke_trials_per_lane": PD_SMOKE_TRIALS,
            "pd_broad_trials_per_lane": PD_BROAD_TRIALS,
            "pd_refine_trials_per_lane": PD_REFINE_TRIALS,
            "portfolio_risk_grid": PORTFOLIO_RISK_GRID,
            "portfolio_gamma_grid": PORTFOLIO_GAMMA_GRID,
            "portfolio_aversion_grid": PORTFOLIO_AVERSION_GRID,
            "portfolio_cap_tail_grid": PORTFOLIO_CAP_TAIL_GRID,
            "portfolio_random_states": PORTFOLIO_RANDOM_STATES,
            "portfolio_max_candidates": PORTFOLIO_MAX_CANDIDATES,
            "portfolio_shortlist_top_k": PORTFOLIO_SHORTLIST_TOP_K,
        },
        "auditability_weights": dict(AUDITABILITY_WEIGHTS),
        "protected_paths": {
            "exact": list(PROTECTED_REPO_PATHS),
            "directories": list(PROTECTED_REPO_DIRS),
            "globs": list(PROTECTED_REPO_GLOBS),
        },
        "commands": [asdict(command) for command in commands],
    }
    return atomic_write_json(manifest_path, payload)


def _completed_outputs(command: PhaseCommand) -> bool:
    return all(Path(output).exists() for output in command.outputs)


def _resource_allows_launch(artifact_root: Path) -> bool:
    snapshot = _resource_snapshot(artifact_root)
    available = snapshot.get("ram_available_gb")
    if available is None:
        return True
    return float(available) >= DEFAULT_MIN_AVAILABLE_RAM_GB


def _append_command_log(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "captured_at_utc",
                "phase",
                "name",
                "state",
                "returncode",
                "checkpoint",
                "stdout_log",
                "stderr_log",
            ],
        )
        if not exists:
            writer.writeheader()
        writer.writerow(dict(row))


def _mlflow_tracking_uri(artifact_root: Path) -> str:
    configured_uri = os.environ.get("MLFLOW_TRACKING_URI", "").strip()
    if configured_uri:
        return configured_uri
    return (artifact_root / "mlruns").resolve().as_uri()


def _mlflow_experiment_name(run_tag: str) -> str:
    configured_name = os.environ.get("CRPTO_SANDBOX_MLFLOW_EXPERIMENT", "").strip()
    if configured_name:
        return configured_name
    return f"crpto_regret_auditability_sandbox_{sanitize_tag(run_tag)}"


def _log_mlflow_error(artifact_root: Path, message: str) -> None:
    log_path = artifact_root / "logs" / "mlflow_tracking_errors.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{utc_now_iso()}] {message}\n")


def _extract_command_artifact_paths(command: PhaseCommand) -> list[Path]:
    paths: list[Path] = []
    flag_names = {
        "--config",
        "--profile-config",
        "--artifact_root",
        "--artifact-root",
        "--output-dir",
        "--output_dir",
        "--model-dir",
        "--model_dir",
    }
    for index, item in enumerate(command.command[:-1]):
        if item in flag_names:
            paths.append(Path(command.command[index + 1]))
    if command.stdout_log:
        paths.append(Path(command.stdout_log))
    if command.stderr_log:
        paths.append(Path(command.stderr_log))
    if command.checkpoint:
        checkpoint = Path(command.checkpoint)
        if checkpoint.exists():
            paths.append(checkpoint)
    for output in command.outputs:
        path = Path(output)
        if path.suffix.lower() in {".json", ".yaml", ".yml", ".csv", ".parquet", ".db"}:
            paths.append(path)
    return paths


def _log_command_to_mlflow(
    *,
    artifact_root: Path,
    command: PhaseCommand,
    state: str,
    returncode: int,
) -> None:
    run_tag = command.env.get("PIPELINE_RUN_TAG") or command.env.get("CRPTO_RUN_TAG") or "unknown"
    try:
        import mlflow

        tracking_uri = _mlflow_tracking_uri(artifact_root)
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(_mlflow_experiment_name(run_tag))
        with mlflow.start_run(run_name=command.name):
            mlflow.set_tags(
                {
                    "crpto.stage": STAGE_NAME,
                    "crpto.run_tag": run_tag,
                    "crpto.phase": command.phase,
                    "crpto.state": state,
                    "crpto.lane_id": command.lane_id or "",
                    "crpto.feature_profile": command.feature_profile or "",
                    "crpto.monotonic_policy": command.monotonic_policy or "",
                }
            )
            mlflow.log_params(
                {
                    "max_workers": command.max_workers,
                    "cpu_threads": command.cpu_threads,
                    "command_name": command.name,
                    "checkpoint": command.checkpoint,
                }
            )
            mlflow.log_metric("returncode", float(returncode))
            command_payload = {
                "schema_version": SCHEMA_VERSION,
                "logged_at_utc": utc_now_iso(),
                "state": state,
                "returncode": returncode,
                "command": command.command,
                "outputs": command.outputs,
                "stdout_log": command.stdout_log,
                "stderr_log": command.stderr_log,
            }
            command_json = artifact_root / "logs" / command.phase / f"{command.name}.mlflow.json"
            atomic_write_json(command_json, command_payload)
            mlflow.log_artifact(str(command_json), artifact_path=f"commands/{command.phase}")
            seen: set[Path] = set()
            for path in _extract_command_artifact_paths(command):
                resolved = path.resolve()
                if resolved in seen or not resolved.exists():
                    continue
                seen.add(resolved)
                if resolved.is_file():
                    size = resolved.stat().st_size
                    if size <= MLFLOW_LOG_SIZE_LIMIT_BYTES:
                        mlflow.log_artifact(
                            str(resolved), artifact_path=f"artifacts/{command.phase}"
                        )
                elif resolved.is_dir():
                    for child in resolved.rglob("*"):
                        if child.is_file() and child.stat().st_size <= MLFLOW_LOG_SIZE_LIMIT_BYTES:
                            mlflow.log_artifact(
                                str(child),
                                artifact_path=f"artifacts/{command.phase}/{resolved.name}",
                            )
    except Exception as exc:
        _log_mlflow_error(artifact_root, f"{command.name}: {type(exc).__name__}: {exc}")


def _run_one_command(command: PhaseCommand) -> tuple[PhaseCommand, int]:
    env = dict(os.environ)
    env.update(command.env)
    stdout_path = Path(command.stdout_log) if command.stdout_log else None
    stderr_path = Path(command.stderr_log) if command.stderr_log else None
    if stdout_path is not None:
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
    if stderr_path is not None:
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_fh = stdout_path.open("a", encoding="utf-8", errors="replace") if stdout_path else None
    stderr_fh = stderr_path.open("a", encoding="utf-8", errors="replace") if stderr_path else None
    returncode = 1
    try:
        if stdout_fh:
            stdout_fh.write(f"\n[{utc_now_iso()}] START {' '.join(command.command)}\n")
            stdout_fh.flush()
        if stderr_fh:
            stderr_fh.write(f"\n[{utc_now_iso()}] START {' '.join(command.command)}\n")
            stderr_fh.flush()
        proc = subprocess.run(
            command.command,
            cwd=str(ROOT),
            env=env,
            stdout=stdout_fh,
            stderr=stderr_fh,
            check=False,
        )
        returncode = int(proc.returncode)
    except OSError as exc:
        if stderr_fh:
            stderr_fh.write(f"\n[{utc_now_iso()}] LAUNCH_ERROR {exc}\n")
            stderr_fh.flush()
    finally:
        if stdout_fh:
            stdout_fh.close()
        if stderr_fh:
            stderr_fh.close()
    return command, returncode


def _run_commands(
    *,
    artifact_root: Path,
    commands: Sequence[PhaseCommand],
    resume: bool,
) -> None:
    log_path = artifact_root / "command_log.csv"
    completed = 0

    phase_groups: list[list[PhaseCommand]] = []
    for command in commands:
        if not phase_groups or phase_groups[-1][0].phase != command.phase:
            phase_groups.append([command])
        else:
            phase_groups[-1].append(command)

    for group in phase_groups:
        pending: deque[PhaseCommand] = deque()
        for command in group:
            if resume and _completed_outputs(command):
                _append_command_log(
                    log_path,
                    {
                        "captured_at_utc": utc_now_iso(),
                        "phase": command.phase,
                        "name": command.name,
                        "state": "skipped_completed",
                        "returncode": 0,
                        "checkpoint": command.checkpoint,
                        "stdout_log": command.stdout_log,
                        "stderr_log": command.stderr_log,
                    },
                )
                _log_command_to_mlflow(
                    artifact_root=artifact_root,
                    command=command,
                    state="skipped_completed",
                    returncode=0,
                )
                completed += 1
                continue
            pending.append(command)

        worker_limit = max(1, max((command.max_workers for command in group), default=1))
        running: dict[Future[tuple[PhaseCommand, int]], PhaseCommand] = {}
        failed_commands: list[PhaseCommand] = []
        last_checkpoint: Path | None = None
        with ThreadPoolExecutor(max_workers=worker_limit) as executor:
            while pending or running:
                while (
                    pending
                    and len(running) < worker_limit
                    and _resource_allows_launch(artifact_root)
                ):
                    command = pending.popleft()
                    last_checkpoint = Path(command.checkpoint)
                    future = executor.submit(_run_one_command, command)
                    running[future] = command
                    _append_command_log(
                        log_path,
                        {
                            "captured_at_utc": utc_now_iso(),
                            "phase": command.phase,
                            "name": command.name,
                            "state": "started",
                            "returncode": "",
                            "checkpoint": command.checkpoint,
                            "stdout_log": command.stdout_log,
                            "stderr_log": command.stderr_log,
                        },
                    )
                _write_heartbeat(
                    artifact_root=artifact_root,
                    phase=group[0].phase if group else "waiting_for_ram",
                    completed_units=completed,
                    total_units=len(commands),
                    current_best_metric=None,
                    last_checkpoint_path=last_checkpoint,
                    state="running" if running else "waiting_for_ram",
                )
                if not running:
                    time.sleep(min(DEFAULT_HEARTBEAT_SECONDS, 5))
                    continue
                done, _ = wait(
                    running.keys(),
                    timeout=DEFAULT_HEARTBEAT_SECONDS,
                    return_when=FIRST_COMPLETED,
                )
                for future in done:
                    command = running.pop(future)
                    finished_command, returncode = future.result()
                    completed += 1
                    _append_command_log(
                        log_path,
                        {
                            "captured_at_utc": utc_now_iso(),
                            "phase": finished_command.phase,
                            "name": finished_command.name,
                            "state": "complete" if returncode == 0 else "failed",
                            "returncode": returncode,
                            "checkpoint": finished_command.checkpoint,
                            "stdout_log": finished_command.stdout_log,
                            "stderr_log": finished_command.stderr_log,
                        },
                    )
                    _log_command_to_mlflow(
                        artifact_root=artifact_root,
                        command=finished_command,
                        state="complete" if returncode == 0 else "failed",
                        returncode=returncode,
                    )
                    if returncode != 0 and finished_command.phase in PD_PHASES:
                        failed_commands.append(finished_command)
                    elif returncode != 0:
                        raise RuntimeError(
                            f"Sandbox command failed ({command.name}) with return code {returncode}"
                        )
        if group and group[0].phase in PD_PHASES:
            selection_path = _select_pd_phase_winners(artifact_root, group[0].phase)
            if selection_path is None:
                failed_names = ", ".join(command.name for command in failed_commands[:10])
                raise RuntimeError(
                    "No successful PD candidates available after phase "
                    f"{group[0].phase}. Failed lanes: {failed_names}"
                )
            _write_heartbeat(
                artifact_root=artifact_root,
                phase=group[0].phase,
                completed_units=completed,
                total_units=len(commands),
                current_best_metric=None,
                last_checkpoint_path=selection_path,
                state="selected_with_failures" if failed_commands else "selected",
            )
    _write_heartbeat(
        artifact_root=artifact_root,
        phase=commands[-1].phase if commands else "plan",
        completed_units=len(commands),
        total_units=len(commands),
        current_best_metric=None,
        last_checkpoint_path=Path(commands[-1].checkpoint) if commands else None,
        state="complete",
    )


def _default_workers_for_phase(phase: str) -> int:
    if phase in PD_PHASES:
        return DEFAULT_PD_WORKERS
    if phase == "conformal":
        return 6
    if phase == "portfolio":
        return 4
    return 1


def _default_threads_for_phase(phase: str) -> int:
    if phase in PD_PHASES:
        return DEFAULT_PD_THREADS
    if phase == "portfolio":
        return 4
    return 1


def _execution_phases(requested_phase: str) -> list[str]:
    if requested_phase == "all":
        return ["pd-smoke", "pd-broad", "pd-refine", "conformal", "portfolio", "metrics"]
    return [requested_phase]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-tag", default=None)
    parser.add_argument("--artifact-root", default=None)
    parser.add_argument("--phase", choices=PHASE_CHOICES, default="plan")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-workers", type=int, default=0)
    parser.add_argument("--cpu-threads", type=int, default=0)
    parser.add_argument("--no-gpu", action="store_true", default=True)
    args = parser.parse_args(argv)

    run_tag = sanitize_tag(args.run_tag or default_run_tag())
    artifact_root = resolve_artifact_root(args.artifact_root, run_tag)
    assert_safe_output_path(artifact_root)
    artifact_root.mkdir(parents=True, exist_ok=True)

    max_workers = int(args.max_workers)
    cpu_threads = int(args.cpu_threads)
    if max_workers < 0 or cpu_threads < 0:
        raise ValueError("--max-workers and --cpu-threads must be non-negative")
    if not bool(args.no_gpu):
        raise ValueError("This sandbox is CPU-only; pass --no-gpu or omit GPU options.")

    resume_manifest_path = artifact_root / "sandbox_manifest.json"
    resume_manifest = load_resume_manifest(resume_manifest_path) if args.resume else {}
    before_path = artifact_root / "dependency_versions_before.json"
    if not before_path.exists():
        _write_dependency_snapshot(before_path)

    commands = (
        []
        if args.phase == "all"
        else build_phase_commands(
            artifact_root=artifact_root,
            run_tag=run_tag,
            phase=args.phase,
            max_workers=max_workers,
            cpu_threads=cpu_threads,
        )
    )
    manifest_path = _write_command_manifest(
        artifact_root=artifact_root,
        run_tag=run_tag,
        phase=args.phase,
        commands=commands,
        resume_manifest=resume_manifest,
    )
    _write_heartbeat(
        artifact_root=artifact_root,
        phase=args.phase,
        completed_units=0,
        total_units=len(commands),
        current_best_metric=None,
        last_checkpoint_path=manifest_path,
        state="planned" if args.phase in {"plan", "deps"} else "ready",
    )

    if args.phase == "deps":
        atomic_write_json(
            artifact_root / "dependency_upgrade_command.json",
            {
                "schema_version": SCHEMA_VERSION,
                "generated_at_utc": utc_now_iso(),
                "command": [
                    "uv",
                    "lock",
                    "--upgrade-package",
                    "catboost",
                    "--upgrade-package",
                    "mapie",
                    "--upgrade-package",
                    "optuna",
                    "--upgrade-package",
                    "optuna-integration",
                    "--upgrade-package",
                    "pyomo",
                    "--upgrade-package",
                    "highspy",
                    "--upgrade-package",
                    "venn-abers",
                    "--upgrade-package",
                    "scikit-learn",
                ],
            },
        )
        return 0
    if args.phase == "plan":
        _write_frontier_metrics_manifest(artifact_root=artifact_root, run_tag=run_tag)
        return 0
    if args.phase != "plan":
        if args.phase == "all":
            for execution_phase in _execution_phases(args.phase):
                phase_commands = build_phase_commands(
                    artifact_root=artifact_root,
                    run_tag=run_tag,
                    phase=execution_phase,
                    max_workers=max_workers,
                    cpu_threads=cpu_threads,
                )
                _write_command_manifest(
                    artifact_root=artifact_root,
                    run_tag=run_tag,
                    phase=execution_phase,
                    commands=phase_commands,
                    resume_manifest=resume_manifest,
                )
                _run_commands(
                    artifact_root=artifact_root,
                    commands=phase_commands,
                    resume=bool(args.resume),
                )
        else:
            _run_commands(artifact_root=artifact_root, commands=commands, resume=bool(args.resume))
        if args.phase == "metrics":
            _write_frontier_metrics_manifest(artifact_root=artifact_root, run_tag=run_tag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
