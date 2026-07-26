"""Run the locked two-phase IJDS set-preserving embedding sensitivity V1."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ijds_audit.config import load_v4_config  # noqa: E402
from src.ijds_audit.evaluation import evaluate_frozen_portfolios  # noqa: E402
from src.ijds_audit.protocol import (  # noqa: E402
    configured_archive_outcomes,
    load_outcome_universe,
    load_recipes,
    verified_freeze_artifact_paths,
)
from src.ijds_challengers.archive import (  # noqa: E402
    load_outcome_free_decision_base,
    verified_parent_artifacts,
)
from src.ijds_challengers.set_preserving_embedding import (  # noqa: E402
    SetPreservingFrontierBuild,
    build_set_preserving_frontiers,
    build_sharp_embedding_contrasts,
    load_set_preserving_config,
    primary_outcome_audit,
    validate_complete_frontier,
)
from src.utils.isolated_experiment import (  # noqa: E402
    OutputPaths,
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    package_version,
    prepare_output_paths as prepare_isolated_output_paths,
    relative_artifact_descriptor,
    resolve_isolated_run_dir,
    resolve_repo_input,
    sha256_file,
)
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    utc_now_iso,
)

DEFAULT_CONFIG_PATH = (
    ROOT / "configs/experiments/ijds_set_preserving_embedding_sensitivity_2026-07-26_v1.yaml"
)
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
FREEZE_STATUS = "outcome_free_set_preserving_allocations_frozen_before_outcomes"
EVALUATION_STATUS = "verified_set_preserving_embedding_evaluation_complete"
PHASE_A_ARTIFACT_KEYS = {
    "solve_records",
    "allocations",
    "embedding_diagnostics",
    "minimum_endpoint_diagnostics",
    "objective_optimum_diagnostics",
    "allocation_contrasts",
    "order_sensitivity",
    "independent_validation",
}
TRANSITIVE_PYTHON_PATHS = (
    Path("scripts/__init__.py"),
    Path("scripts/experiments/run_ijds_set_preserving_embedding_sensitivity_v1.py"),
    Path("src/__init__.py"),
    Path("src/data/__init__.py"),
    Path("src/data/outcome_observability.py"),
    Path("src/evaluation/__init__.py"),
    Path("src/evaluation/coverage_transport.py"),
    Path("src/evaluation/maturity_safe_portfolio.py"),
    Path("src/evaluation/policy_contrast_bounds.py"),
    Path("src/evaluation/standardized_credit_payoff.py"),
    Path("src/features/__init__.py"),
    Path("src/features/feature_engineering.py"),
    Path("src/ijds_audit/__init__.py"),
    Path("src/ijds_audit/allocations.py"),
    Path("src/ijds_audit/config.py"),
    Path("src/ijds_audit/endpoint_recovery.py"),
    Path("src/ijds_audit/evaluation.py"),
    Path("src/ijds_audit/geometry.py"),
    Path("src/ijds_audit/policy_support.py"),
    Path("src/ijds_audit/portfolio.py"),
    Path("src/ijds_audit/prediction.py"),
    Path("src/ijds_audit/protocol.py"),
    Path("src/ijds_audit/rhs_ranging.py"),
    Path("src/ijds_audit/simulation.py"),
    Path("src/ijds_challengers/__init__.py"),
    Path("src/ijds_challengers/archive.py"),
    Path("src/ijds_challengers/frontier.py"),
    Path("src/ijds_challengers/normalized_frontier.py"),
    Path("src/ijds_challengers/set_preserving_embedding.py"),
    Path("src/models/__init__.py"),
    Path("src/models/binary_conformal_guardrail.py"),
    Path("src/models/maturity_safe_pd.py"),
    Path("src/optimization/__init__.py"),
    Path("src/optimization/policy.py"),
    Path("src/optimization/policy_evaluation.py"),
    Path("src/optimization/policy_selection.py"),
    Path("src/optimization/portfolio_model.py"),
    Path("src/utils/__init__.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
)
IMPLEMENTATION_PATHS = (
    Path("configs/experiments/ijds_fixed_taxonomy_c2_2026-07-11.yaml"),
    Path("configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-12.yaml"),
    Path("configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-12_v2.yaml"),
    Path("configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-14_v3.yaml"),
    Path("configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-15_v4.yaml"),
    Path("configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-15_v5.yaml"),
    Path("docs/research/ijds_set_preserving_embedding_sensitivity_v1_protocol_2026-07-26.md"),
    Path("docs/research/ijds_fixed_taxonomy_c2_protocol_errata_2026-07-12.md"),
    Path("docs/research/ijds_binary_geometry_frontier_v4_protocol_2026-07-12.md"),
    Path("docs/research/ijds_binary_geometry_frontier_v4_v2_recovery_2026-07-12.md"),
    Path("docs/research/ijds_evaluation_endpoint_recovery_v3_protocol_2026-07-14.md"),
    Path("docs/research/ijds_endpoint_reason_taxonomy_v4_protocol_2026-07-15.md"),
    Path("docs/research/ijds_endpoint_reason_recovery_v5_erratum_2026-07-15.md"),
    Path("docs/research/ijds_normalized_objective_frontier_protocol_2026-07-12.md"),
    Path("docs/research/ijds_normalized_objective_frontier_v1c_protocol_2026-07-13.md"),
    Path("docs/research/ijds_two_ruler_endpoint_recovery_v3_protocol_2026-07-14.md"),
    *TRANSITIVE_PYTHON_PATHS,
    # Retained as an authority helper even though this runner imports the
    # equivalent isolated-experiment implementation directly.
    Path("src/utils/artifact_descriptor.py"),
    Path("tests/test_ijds_set_preserving_embedding_sensitivity.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse one explicit phase; evaluation can never occur implicitly."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--phase", choices=("outcome-free", "evaluate"), required=True)
    return parser.parse_args(argv)


def _output_paths(config: Mapping[str, Any], *, repo_root: Path) -> OutputPaths:
    output = config["output"]
    run_tag = str(config["run_tag"])
    return OutputPaths(
        data_dir=resolve_isolated_run_dir(
            repo_root=repo_root,
            configured_root=str(output["data_root"]),
            allowed_relative_root=ALLOWED_DATA_ROOT,
            run_tag=run_tag,
        ),
        model_dir=resolve_isolated_run_dir(
            repo_root=repo_root,
            configured_root=str(output["model_root"]),
            allowed_relative_root=ALLOWED_MODEL_ROOT,
            run_tag=run_tag,
        ),
    )


def preflight_fresh_run(config: Mapping[str, Any], *, repo_root: Path) -> OutputPaths:
    """Reject occupied run directories before any expensive Phase-A read or solve."""
    paths = _output_paths(config, repo_root=repo_root)
    occupied = [path for path in (paths.data_dir, paths.model_dir) if path.exists()]
    if occupied:
        raise FileExistsError(
            "Set-preserving run tag is occupied; choose a fresh tag: "
            + ", ".join(str(path) for path in occupied)
        )
    return paths


def prepare_output_paths(config: Mapping[str, Any], *, repo_root: Path) -> OutputPaths:
    """Create fresh directories only inside the two isolated IJDS experiment roots."""
    return prepare_isolated_output_paths(
        dict(config),
        repo_root=repo_root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )


def _implementation(config_path: Path, root: Path) -> dict[str, Any]:
    return implementation_provenance(
        config_path=config_path,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )


def _environment(root: Path) -> dict[str, Any]:
    environment = environment_provenance(root)
    environment["packages"]["ortools"] = package_version("ortools")
    environment["packages"]["PyYAML"] = package_version("PyYAML")
    environment["packages"]["loguru"] = package_version("loguru")
    return environment


def _authority_snapshot(config_path: Path, root: Path) -> dict[str, Any]:
    """Capture implementation, environment, and git authority for one run."""
    return {
        "implementation": _implementation(config_path, root),
        "environment": _environment(root),
        "git": git_provenance(root),
    }


def _resolve_strict_tag(root: Path, tag: str) -> str:
    """Resolve only an actual refs/tags name, never a Git revision expression."""
    value = str(tag)
    reference = f"refs/tags/{value}"
    valid = subprocess.run(
        ["git", "check-ref-format", reference],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if valid.returncode != 0 or value.startswith(("-", "refs/")):
        raise RuntimeError(f"Protocol tag is not a valid explicit tag name: {tag!r}.")
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", "--end-of-options", f"{reference}^{{commit}}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    commit = resolved.stdout.strip()
    if resolved.returncode != 0 or len(commit) != 40:
        raise RuntimeError(f"Required protocol tag is unavailable: {tag!r}.")
    return commit


def _require_clean_strict_tagged_head(root: Path, tag: str) -> str:
    """Require a clean HEAD equal to one explicit tag ref."""
    state = git_provenance(root)
    commit = state.get("commit")
    if not isinstance(commit, str) or not commit:
        raise RuntimeError("A readable Git HEAD is required before experiment execution.")
    if state.get("dirty") is not False:
        raise RuntimeError("Experiment execution requires a clean predeclared worktree.")
    if _resolve_strict_tag(root, tag) != commit:
        raise RuntimeError(f"Protocol tag {tag!r} does not resolve exactly to clean HEAD.")
    return commit


def _require_unchanged_authority(
    *,
    config: Mapping[str, Any],
    config_path: Path,
    protocol_commit: str,
    initial: Mapping[str, Any],
    root: Path,
) -> None:
    """Reject code, environment, branch, or worktree drift during a long run."""
    observed_commit = _require_clean_strict_tagged_head(root, str(config["protocol_tag"]))
    if observed_commit != protocol_commit:
        raise RuntimeError("Protocol commit changed during experiment execution.")
    if _authority_snapshot(config_path, root) != dict(initial):
        raise RuntimeError("Implementation, environment, or git authority drifted during the run.")


def _verified_descriptor_path(
    descriptor: Mapping[str, Any],
    *,
    label: str,
    root: Path,
) -> Path:
    """Resolve and verify one exact repository-local descriptor."""
    path = resolve_repo_input(str(descriptor["path"]), repo_root=root)
    actual = relative_artifact_descriptor(path, repo_root=root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor[field]:
            raise RuntimeError(f"{label} descriptor mismatch for {field}.")
    return path


def _require_tagged_ancestor(
    *,
    source_tag: str,
    source_commit: str,
    evaluation_commit: str,
    root: Path,
) -> None:
    """Require the source tag identity and direct Git ancestry of the evaluation."""
    if _resolve_strict_tag(root, source_tag) != source_commit:
        raise RuntimeError("The source protocol tag no longer resolves to its pinned commit.")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, evaluation_commit],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestry.returncode != 0:
        raise RuntimeError("The V1 source commit is not an ancestor of the V2 evaluation commit.")


def _require_committed_implementation(
    provenance: Mapping[str, Any],
    *,
    commit: str,
    root: Path,
) -> None:
    """Reconcile every declared implementation descriptor to its Git blob at V1."""
    source_files = provenance.get("source_files")
    if not isinstance(source_files, dict) or provenance.get("hash_algorithm") != "sha256":
        raise RuntimeError("The V1 implementation provenance schema is invalid.")
    for relative_path, descriptor in source_files.items():
        if not isinstance(descriptor, dict) or descriptor.get("path") != relative_path:
            raise RuntimeError("The V1 implementation descriptor key/path identity changed.")
        blob = subprocess.run(
            ["git", "show", f"{commit}:{relative_path}"],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if blob.returncode != 0:
            raise RuntimeError(
                f"V1 implementation path is absent from its commit: {relative_path}."
            )
        observed = {
            "path": relative_path,
            "bytes": len(blob.stdout),
            "sha256": hashlib.sha256(blob.stdout).hexdigest(),
        }
        if observed != descriptor:
            raise RuntimeError(f"V1 Git blob disagrees with provenance: {relative_path}.")


def _require_v2_implementation_equals_v1(
    source_provenance: Mapping[str, Any],
    evaluation_provenance: Mapping[str, Any],
    *,
    source_config_path: str,
    evaluation_config_path: str,
) -> None:
    """Require an exact dependency census and no V1-to-V2 implementation drift."""
    locked_paths = {path.as_posix() for path in IMPLEMENTATION_PATHS}
    source_files = source_provenance.get("source_files")
    evaluation_files = evaluation_provenance.get("source_files")
    if not isinstance(source_files, dict) or not isinstance(evaluation_files, dict):
        raise RuntimeError("V1 or V2 implementation provenance lacks source_files.")
    if set(source_files) != {*locked_paths, source_config_path}:
        raise RuntimeError("The V1 implementation provenance omits or adds a locked path.")
    if set(evaluation_files) != {*locked_paths, evaluation_config_path}:
        raise RuntimeError("The V2 implementation provenance omits or adds a locked path.")
    for path in locked_paths:
        if evaluation_files[path] != source_files[path]:
            raise RuntimeError(f"A scientific dependency changed between V1 and V2: {path}.")


def _require_v2_is_v1_plus_pin(
    evaluation: Mapping[str, Any],
    source: Mapping[str, Any],
) -> None:
    """Allow only administrative V2 fields plus the external source authority."""
    mutable = {"schema_version", "protocol_status", "protocol_tag", "run_tag", "source_frontier"}
    evaluation_science = {key: value for key, value in evaluation.items() if key not in mutable}
    source_science = {key: value for key, value in source.items() if key not in mutable}
    if evaluation_science != source_science:
        raise RuntimeError("V2 is not canonically identical to V1 outside the pin whitelist.")
    if (
        evaluation.get("protocol_status") != "locked_hash_pinned_postfreeze_evaluation"
        or source.get("protocol_status") != "locked_candidate_two_phase_before_execution"
        or evaluation.get("run_tag") == source.get("run_tag")
        or evaluation.get("protocol_tag") == source.get("protocol_tag")
    ):
        raise RuntimeError("V1/V2 administrative identities are not separated correctly.")


def _candidate_identity_contract(frame: pd.DataFrame) -> dict[str, Any]:
    """Hash the exact role-period-ID census without persisting candidate IDs."""
    required = {"id", "role", "period"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise KeyError(f"Candidate identity frame is missing columns: {missing}.")
    identity = frame.loc[:, ["role", "period", "id"]].copy()
    if bool(identity.isna().any(axis=None)):
        raise RuntimeError("Candidate identity contains a missing role, period, or ID.")
    identity = identity.astype("string")
    if bool(identity["id"].duplicated().any()):
        raise RuntimeError("Candidate identity contains duplicate loan IDs.")
    identity = identity.sort_values(["role", "period", "id"], kind="mergesort")

    def digest(rows: pd.DataFrame) -> str:
        hasher = hashlib.sha256()
        for row in rows.itertuples(index=False, name=None):
            encoded = json.dumps(list(row), ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
            hasher.update(len(encoded).to_bytes(8, byteorder="big", signed=False))
            hasher.update(encoded)
        return hasher.hexdigest()

    groups = [
        {
            "role": str(role),
            "period": str(period),
            "rows": int(len(group)),
            "sha256": digest(group),
        }
        for (role, period), group in identity.groupby(["role", "period"], observed=True, sort=True)
    ]
    return {
        "rows": int(len(identity)),
        "groups": groups,
        "sha256": digest(identity),
        "canonicalization": ("utf8_length_prefixed_json_role_period_id_sorted_mergesort_sha256"),
    }


def _outcome_free_summary(
    build: SetPreservingFrontierBuild,
    *,
    config: Mapping[str, Any],
    parent_freeze: Mapping[str, Any],
    protocol_commit: str,
) -> dict[str, Any]:
    records = build.solve_records
    negative = build.allocation_contrasts.loc[
        build.allocation_contrasts["contrast_family"].eq("theta_minus_theta_0_within_gamma")
        & build.allocation_contrasts["gamma"].eq(0.0)
    ]
    return {
        "schema_version": str(config["schema_version"]),
        "status": FREEZE_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "parent_status": parent_freeze.get("status"),
        "parent_freeze_sha256": str(config["parent"]["protocol_freeze"]["sha256"]),
        "counts": {
            "solve_records": int(len(records)),
            "funded_rows": int(len(build.allocations)),
            "embedding_diagnostics": int(len(build.embedding_diagnostics)),
            "minimum_score_endpoints": int(len(build.minimum_endpoint_diagnostics)),
            "objective_optima": int(len(build.objective_optimum_diagnostics)),
            "allocation_contrasts": int(len(build.allocation_contrasts)),
            "order_replays": int(len(build.order_sensitivity)),
            "independent_solver_cells": int(len(build.independent_validation)),
            "windows": int(records["window_id"].nunique()),
            "role_periods": int(records[["role", "period"]].drop_duplicates().shape[0]),
            "thetas": int(records["theta"].nunique()),
            "gammas": int(records["gamma"].nunique()),
            "coordinates": int(records["frontier_coordinate"].nunique()),
            "rulers": int(records["frontier_ruler"].nunique()),
        },
        "embedding_contract": {
            "sets_changed": int(build.embedding_diagnostics["sets_changed"].sum()),
            "maximum_upper_contraction": float(
                build.embedding_diagnostics["maximum_upper_contraction"].max()
            ),
            "theta_zero_maximum_recovery_error": float(
                build.embedding_diagnostics.loc[
                    build.embedding_diagnostics["theta"].eq(0.0),
                    "maximum_theta_zero_recovery_error",
                ].max()
            ),
        },
        "common_objective_ruler": {
            "lower_endpoint_scope": "one_z_L_over_all_25_theta_gamma_scores_per_cell",
            "minimum_range_dollars": float(
                (records["unconstrained_objective"] - records["common_objective_lower"]).min()
            ),
            "maximum_range_dollars": float(
                (records["unconstrained_objective"] - records["common_objective_lower"]).max()
            ),
        },
        "negative_control": {
            "cells": int(len(negative)),
            "maximum_exposure_distance": float(negative["normalized_exposure_distance"].max()),
            "maximum_absolute_objective_difference": float(
                negative["objective_difference"].abs().max()
            ),
        },
        "maximum_budget_residual_dollars": float(records["budget_residual"].abs().max()),
        "maximum_id_reversal_exposure_distance": float(
            build.order_sensitivity["normalized_exposure_distance"].max()
        ),
        "maximum_glop_objective_rate_difference": float(
            build.independent_validation["objective_rate_difference"].abs().max()
        ),
        "outcome_columns_passed": [],
        "selection": {
            "theta": None,
            "gamma": None,
            "ruler": None,
            "coordinate": None,
            "window": None,
            "policy": None,
        },
        "policy_winner": None,
        "causal_interpretation": False,
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }


def run_outcome_free(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Build the complete decision grid and freeze it before any outcome read."""
    started = time.perf_counter()
    started_at = utc_now_iso()
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_set_preserving_config(resolved_config)
    if config["protocol_status"] != "locked_candidate_two_phase_before_execution":
        raise RuntimeError("Outcome-free construction requires the locked V1 build config.")
    protocol_commit = _require_clean_strict_tagged_head(root, str(config["protocol_tag"]))
    initial_authority = _authority_snapshot(resolved_config, root)
    _require_committed_implementation(
        initial_authority["implementation"], commit=protocol_commit, root=root
    )
    preflight_fresh_run(config, repo_root=root)

    parent_paths, parent_freeze = verified_parent_artifacts(config, repo_root=root)
    parent_config_path = resolve_repo_input(str(config["parent"]["config"]), repo_root=root)
    parent_commit = str(config["parent"]["protocol_commit"])
    _require_tagged_ancestor(
        source_tag=str(config["parent"]["protocol_tag"]),
        source_commit=parent_commit,
        evaluation_commit=protocol_commit,
        root=root,
    )
    parent_provenance = parent_freeze.get("implementation_provenance")
    if not isinstance(parent_provenance, dict):
        raise RuntimeError("The historical parent freeze lacks implementation provenance.")
    parent_config_descriptor = relative_artifact_descriptor(parent_config_path, repo_root=root)
    if parent_provenance.get("source_files", {}).get(str(config["parent"]["config"])) != (
        parent_config_descriptor
    ):
        raise RuntimeError("The current parent config disagrees with its historical freeze.")
    _require_committed_implementation(parent_provenance, commit=parent_commit, root=root)
    parent_config = load_v4_config(parent_config_path)
    raw_path = resolve_repo_input(str(config["source_ingest"]["raw_path"]), repo_root=root)
    base = load_outcome_free_decision_base(
        scores_path=parent_paths["scores"],
        raw_path=raw_path,
        config=config,
    )
    candidate_identity = _candidate_identity_contract(
        base.assign(
            role=base["design_split"].astype("string"),
            period=pd.to_datetime(base["issue_d"]).dt.to_period("M").astype("string"),
        )
    )
    recipes = load_recipes(parent_paths["recipes"])
    build = build_set_preserving_frontiers(
        base,
        recipes,
        config=config,
        parent_config=parent_config,
    )
    repeated_paths, repeated_parent = verified_parent_artifacts(config, repo_root=root)
    if repeated_paths != parent_paths or repeated_parent != parent_freeze:
        raise RuntimeError("Parent freeze authority changed during Phase A.")
    if sha256_file(raw_path) != str(config["source_ingest"]["raw_sha256"]):
        raise RuntimeError("Raw decision archive changed during Phase A.")
    _require_unchanged_authority(
        config=config,
        config_path=resolved_config,
        protocol_commit=protocol_commit,
        initial=initial_authority,
        root=root,
    )
    summary = _outcome_free_summary(
        build,
        config=config,
        parent_freeze=parent_freeze,
        protocol_commit=protocol_commit,
    )

    paths = prepare_output_paths(config, repo_root=root)
    frontier_dir = paths.data_dir / "frontier"
    output = config["output"]
    artifacts = {
        "solve_records": atomic_write_parquet(
            build.solve_records, frontier_dir / str(output["solve_records"])
        ),
        "allocations": atomic_write_parquet(
            build.allocations, frontier_dir / str(output["allocations"])
        ),
        "embedding_diagnostics": atomic_write_parquet(
            build.embedding_diagnostics,
            frontier_dir / str(output["embedding_diagnostics"]),
        ),
        "minimum_endpoint_diagnostics": atomic_write_parquet(
            build.minimum_endpoint_diagnostics,
            frontier_dir / str(output["minimum_endpoint_diagnostics"]),
        ),
        "objective_optimum_diagnostics": atomic_write_parquet(
            build.objective_optimum_diagnostics,
            frontier_dir / str(output["objective_optimum_diagnostics"]),
        ),
        "allocation_contrasts": atomic_write_parquet(
            build.allocation_contrasts,
            frontier_dir / str(output["allocation_contrasts"]),
        ),
        "order_sensitivity": atomic_write_parquet(
            build.order_sensitivity,
            frontier_dir / str(output["order_sensitivity"]),
        ),
        "independent_validation": atomic_write_parquet(
            build.independent_validation,
            frontier_dir / str(output["independent_validation"]),
        ),
    }
    summary_path = atomic_write_json(paths.model_dir / str(output["outcome_free_summary"]), summary)
    receipt_path = atomic_write_json(
        paths.model_dir / str(output["outcome_free_receipt"]),
        {
            "schema_version": str(config["schema_version"]),
            "status": FREEZE_STATUS,
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "started_at_utc": started_at,
            "completed_at_utc": utc_now_iso(),
            "elapsed_seconds": float(time.perf_counter() - started),
            "outcome_columns_passed": [],
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    freeze = {
        "schema_version": str(config["schema_version"]),
        "status": FREEZE_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "parent": {
            "run_tag": str(config["parent"]["run_tag"]),
            "protocol_freeze": dict(config["parent"]["protocol_freeze"]),
        },
        "decision_contract": {
            "budget": float(parent_config["policy"]["budget"]),
            "max_concentration_by_purpose": float(
                parent_config["policy"]["max_concentration_by_purpose"]
            ),
            "lgd": float(parent_config["payoff"]["lgd"]),
            "raw_path": str(config["source_ingest"]["raw_path"]),
            "raw_sha256": str(config["source_ingest"]["raw_sha256"]),
            "roles": list(config["frontier"]["roles"]),
            "candidate_identity": candidate_identity,
        },
        "outcome_columns_passed_to_frontier": [],
        "selection": {
            "theta": None,
            "gamma": None,
            "ruler": None,
            "coordinate": None,
            "window": None,
            "policy": None,
        },
        "implementation_provenance": initial_authority["implementation"],
        "environment": initial_authority["environment"],
        "git": initial_authority["git"],
        "schemas": {name: dataframe_schema(getattr(build, name)) for name in artifacts},
        "outcome_free_artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in artifacts.items()
        },
        "summary": relative_artifact_descriptor(summary_path, repo_root=root),
        "execution_receipt": relative_artifact_descriptor(receipt_path, repo_root=root),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    repeated_paths, repeated_parent = verified_parent_artifacts(config, repo_root=root)
    if repeated_paths != parent_paths or repeated_parent != parent_freeze:
        raise RuntimeError("Parent freeze authority changed before the Phase-A seal.")
    if sha256_file(raw_path) != str(config["source_ingest"]["raw_sha256"]):
        raise RuntimeError("Raw decision archive changed before the Phase-A seal.")
    _require_unchanged_authority(
        config=config,
        config_path=resolved_config,
        protocol_commit=protocol_commit,
        initial=initial_authority,
        root=root,
    )
    for name, path in artifacts.items():
        if (
            relative_artifact_descriptor(path, repo_root=root)
            != freeze["outcome_free_artifacts"][name]
        ):
            raise RuntimeError(f"A Phase-A artifact changed before freeze seal: {name}.")
    if (
        relative_artifact_descriptor(summary_path, repo_root=root) != freeze["summary"]
        or relative_artifact_descriptor(receipt_path, repo_root=root) != freeze["execution_receipt"]
    ):
        raise RuntimeError("The Phase-A summary or receipt changed before freeze seal.")
    freeze_path = atomic_write_json(paths.model_dir / str(output["protocol_freeze"]), freeze)
    logger.info(
        "Frozen {} outcome-free embedding cells and {} funded rows in {:.1f}s",
        len(build.solve_records),
        len(build.allocations),
        time.perf_counter() - started,
    )
    return freeze_path


def _verify_frozen_phase(
    config: Mapping[str, Any],
    *,
    evaluation_commit: str,
    evaluation_config_path: Path,
    evaluation_environment: Mapping[str, Any],
    evaluation_provenance: Mapping[str, Any],
    repo_root: Path,
) -> tuple[Path, dict[str, Any], dict[str, Path]]:
    source = config["source_frontier"]
    source_config_path = _verified_descriptor_path(
        source["config"], label="Hash-pinned source V1 config", root=repo_root
    )
    source_config = load_set_preserving_config(source_config_path)
    _require_v2_is_v1_plus_pin(config, source_config)
    source_commit = str(source["protocol_commit"])
    if (
        source_config.get("run_tag") != source["run_tag"]
        or source_config.get("protocol_tag") != source["protocol_tag"]
    ):
        raise RuntimeError("The pinned V1 config identity disagrees with source_frontier.")
    _require_tagged_ancestor(
        source_tag=str(source["protocol_tag"]),
        source_commit=source_commit,
        evaluation_commit=evaluation_commit,
        root=repo_root,
    )

    freeze_path = _verified_descriptor_path(
        source["freeze"], label="Hash-pinned source freeze", root=repo_root
    )
    source_data_dir = (
        repo_root / str(source_config["output"]["data_root"]) / str(source["run_tag"])
    ).resolve()
    source_model_dir = (
        repo_root / str(source_config["output"]["model_root"]) / str(source["run_tag"])
    ).resolve()
    expected_freeze_path = (
        source_model_dir / str(source_config["output"]["protocol_freeze"])
    ).resolve()
    if freeze_path != expected_freeze_path:
        raise RuntimeError("The hash-pinned freeze is outside its exact V1 run directory.")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    expected = {
        "status": FREEZE_STATUS,
        "run_tag": str(source["run_tag"]),
        "protocol_tag": str(source["protocol_tag"]),
        "protocol_commit": str(source["protocol_commit"]),
    }
    for key, value in expected.items():
        if freeze.get(key) != value:
            raise RuntimeError(f"Outcome-free freeze mismatch for {key}.")
    expected_git = {
        "commit": source_commit,
        "dirty": False,
        "dirty_entries": 0,
        "dirty_paths": [],
    }
    if freeze.get("git") != expected_git:
        raise RuntimeError("The V1 freeze does not attest its exact clean tagged Git state.")
    if freeze.get("environment") != dict(evaluation_environment):
        raise RuntimeError("The scientific runtime changed between V1 and V2.")
    provenance = freeze.get("implementation_provenance")
    if not isinstance(provenance, dict):
        raise RuntimeError("The V1 freeze lacks implementation provenance.")
    if provenance.get("source_files", {}).get(str(source["config"]["path"])) != dict(
        source["config"]
    ):
        raise RuntimeError("The V1 freeze does not bind the hash-pinned source config.")
    evaluation_config_relative = evaluation_config_path.resolve().relative_to(repo_root).as_posix()
    _require_v2_implementation_equals_v1(
        provenance,
        evaluation_provenance,
        source_config_path=str(source["config"]["path"]),
        evaluation_config_path=evaluation_config_relative,
    )
    _require_committed_implementation(provenance, commit=source_commit, root=repo_root)
    if freeze.get("outcome_columns_passed_to_frontier") != []:
        raise RuntimeError("Outcome-free freeze reports outcome leakage.")
    null_selection = {
        "theta": None,
        "gamma": None,
        "ruler": None,
        "coordinate": None,
        "window": None,
        "policy": None,
    }
    if (
        freeze.get("selection") != null_selection
        or freeze.get("protected_stages_run") != []
        or freeze.get("protected_artifacts_written") != []
    ):
        raise RuntimeError("The V1 freeze reports selection or protected-stage execution.")
    if set(freeze.get("outcome_free_artifacts", {})) != PHASE_A_ARTIFACT_KEYS:
        raise RuntimeError("The outcome-free freeze artifact census changed.")
    if set(freeze.get("schemas", {})) != PHASE_A_ARTIFACT_KEYS:
        raise RuntimeError("The outcome-free freeze schema census changed.")
    artifacts = verified_freeze_artifact_paths(freeze, repo_root=repo_root)
    frontier_dir = (source_data_dir / "frontier").resolve()
    for name, path in artifacts.items():
        expected_path = (frontier_dir / str(source_config["output"][name])).resolve()
        if path != expected_path:
            raise RuntimeError(f"Frozen artifact escaped its exact V1 path: {name}.")

    summary_path = _verified_descriptor_path(
        freeze["summary"], label="V1 outcome-free summary", root=repo_root
    )
    receipt_path = _verified_descriptor_path(
        freeze["execution_receipt"], label="V1 execution receipt", root=repo_root
    )
    if (
        summary_path
        != (source_model_dir / str(source_config["output"]["outcome_free_summary"])).resolve()
        or receipt_path
        != (source_model_dir / str(source_config["output"]["outcome_free_receipt"])).resolve()
    ):
        raise RuntimeError("V1 summary or receipt escaped the exact source run directory.")
    for label, payload_path in (("summary", summary_path), ("receipt", receipt_path)):
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        for key, value in expected.items():
            if payload.get(key) != value:
                raise RuntimeError(f"V1 {label} disagrees with source authority for {key}.")
        if (
            payload.get("outcome_columns_passed") != []
            or payload.get("protected_stages_run") != []
            or payload.get("protected_artifacts_written") != []
        ):
            raise RuntimeError(f"V1 {label} reports outcome leakage or protected execution.")
        if label == "summary" and payload.get("selection") != null_selection:
            raise RuntimeError("V1 summary reports post-inspection selection.")
    return freeze_path, freeze, artifacts


def _evaluation_summary(
    *,
    config: Mapping[str, Any],
    protocol_commit: str,
    freeze: Mapping[str, Any],
    evaluated: pd.DataFrame,
    joined: pd.DataFrame,
    monthly: pd.DataFrame,
    window: pd.DataFrame,
    directions: pd.DataFrame,
    outcome_audit: pd.DataFrame,
) -> dict[str, Any]:
    negative = window.loc[
        window["contrast_family"].eq("theta_minus_theta_0_within_gamma") & window["gamma"].eq(0.0)
    ]
    direction_counts = (
        directions.groupby(["metric", "direction_at_tolerance"], observed=True)
        .size()
        .rename("cells")
        .reset_index()
        .to_dict(orient="records")
    )
    geometric_direction_counts = (
        directions.groupby(["metric", "geometric_direction"], observed=True)
        .size()
        .rename("cells")
        .reset_index()
        .to_dict(orient="records")
    )
    return {
        "schema_version": str(config["schema_version"]),
        "status": EVALUATION_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "source_freeze_status": freeze["status"],
        "counts": {
            "evaluated_primary_portfolios": int(len(evaluated)),
            "joined_funded_rows": int(len(joined)),
            "monthly_sharp_contrasts": int(len(monthly)),
            "window_sharp_contrasts": int(len(window)),
            "metric_direction_rows": int(len(directions)),
            "outcome_audit_rows": int(len(outcome_audit)),
        },
        "negative_control": {
            "window_cells": int(len(negative)),
            "maximum_absolute_expected_objective_difference": float(
                negative["expected_objective_difference"].abs().max()
            ),
            "maximum_absolute_realized_payoff_bound_dollars": float(
                negative[["realized_payoff_difference_lower", "realized_payoff_difference_upper"]]
                .abs()
                .to_numpy()
                .max(initial=0.0)
            ),
            "maximum_absolute_weighted_default_bound": float(
                negative[["weighted_default_difference_lower", "weighted_default_difference_upper"]]
                .abs()
                .to_numpy()
                .max(initial=0.0)
            ),
            "maximum_absolute_weighted_miscoverage_bound": float(
                negative[
                    [
                        "weighted_miscoverage_difference_lower",
                        "weighted_miscoverage_difference_upper",
                    ]
                ]
                .abs()
                .to_numpy()
                .max(initial=0.0)
            ),
        },
        "direction_counts": direction_counts,
        "geometric_direction_counts": geometric_direction_counts,
        "unresolved_primary_candidates": int(outcome_audit["unresolved_rows"].sum()),
        "window_aggregation": "pooled_15_month_union_sum_numerators_before_rates",
        "outcome_refit": False,
        "outcome_selection": False,
        "policy_selection": None,
        "theta_selection": None,
        "gamma_selection": None,
        "ruler_selection": None,
        "coordinate_selection": None,
        "policy_winner": None,
        "causal_interpretation": False,
        "conformal_guarantee_repair": False,
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }


def run_evaluation(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Verify Phase A before opening outcomes, then retain all primary contrasts."""
    started = time.perf_counter()
    started_at = utc_now_iso()
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_set_preserving_config(resolved_config)
    if config["protocol_status"] != "locked_hash_pinned_postfreeze_evaluation":
        raise RuntimeError(
            "V1 cannot authorize outcomes; create, commit, and tag a hash-pinned V2 config."
        )
    protocol_commit = _require_clean_strict_tagged_head(root, str(config["protocol_tag"]))
    initial_authority = _authority_snapshot(resolved_config, root)
    _require_committed_implementation(
        initial_authority["implementation"], commit=protocol_commit, root=root
    )
    preflight_fresh_run(config, repo_root=root)
    freeze_path, freeze, artifacts = _verify_frozen_phase(
        config,
        evaluation_commit=protocol_commit,
        evaluation_config_path=resolved_config,
        evaluation_environment=initial_authority["environment"],
        evaluation_provenance=initial_authority["implementation"],
        repo_root=root,
    )

    outcome_config_path = resolve_repo_input(
        str(config["outcomes"]["parent_config"]), repo_root=root
    )
    outcome_config = load_v4_config(outcome_config_path)
    decision_contract = freeze.get("decision_contract")
    if not isinstance(decision_contract, dict):
        raise RuntimeError("The V1 freeze lacks its decision contract.")
    expected_contract = {
        "budget": float(outcome_config["policy"]["budget"]),
        "max_concentration_by_purpose": float(
            outcome_config["policy"]["max_concentration_by_purpose"]
        ),
        "lgd": float(outcome_config["payoff"]["lgd"]),
        "raw_path": str(config["outcomes"]["raw_path"]),
        "raw_sha256": str(config["outcomes"]["raw_sha256"]),
        "roles": list(config["frontier"]["roles"]),
    }
    observed_static_contract = {key: decision_contract.get(key) for key in expected_contract}
    if observed_static_contract != expected_contract or not isinstance(
        decision_contract.get("candidate_identity"), dict
    ):
        raise RuntimeError("Phase-A and Phase-B policy/source contracts differ.")

    source_build = SetPreservingFrontierBuild(
        solve_records=pd.read_parquet(artifacts["solve_records"]),
        allocations=pd.read_parquet(artifacts["allocations"]),
        embedding_diagnostics=pd.read_parquet(artifacts["embedding_diagnostics"]),
        minimum_endpoint_diagnostics=pd.read_parquet(artifacts["minimum_endpoint_diagnostics"]),
        objective_optimum_diagnostics=pd.read_parquet(artifacts["objective_optimum_diagnostics"]),
        allocation_contrasts=pd.read_parquet(artifacts["allocation_contrasts"]),
        order_sensitivity=pd.read_parquet(artifacts["order_sensitivity"]),
        independent_validation=pd.read_parquet(artifacts["independent_validation"]),
    )
    for name in PHASE_A_ARTIFACT_KEYS:
        observed_schema = dataframe_schema(getattr(source_build, name))
        if observed_schema != freeze["schemas"][name]:
            raise RuntimeError(f"Frozen Phase-A schema changed for {name}.")
    validate_complete_frontier(
        source_build,
        config=config,
        budget=float(decision_contract["budget"]),
    )
    records = source_build.solve_records
    allocations = source_build.allocations
    del source_build
    primary_records = records.loc[records["role"].eq("primary_oot")].copy()
    primary_allocations = allocations.loc[allocations["role"].eq("primary_oot")].copy()
    del records, allocations
    if len(primary_records) != int(config["expected_census"]["primary_evaluated_portfolios"]):
        raise RuntimeError("Frozen primary portfolio census changed before outcomes.")

    if (
        str(config["source_ingest"]["raw_path"]) != str(config["outcomes"]["raw_path"])
        or str(config["source_ingest"]["raw_sha256"]) != str(config["outcomes"]["raw_sha256"])
        or str(config["outcomes"]["endpoint"]) != str(outcome_config["design"]["endpoint"])
    ):
        raise RuntimeError("The committed evaluation endpoint or raw authority diverged.")
    raw_path = resolve_repo_input(str(config["outcomes"]["raw_path"]), repo_root=root)
    if sha256_file(raw_path) != str(config["outcomes"]["raw_sha256"]):
        raise RuntimeError("The locked raw archive changed before the outcome join.")
    universe = load_outcome_universe(outcome_config, raw_path=raw_path)
    all_outcomes = configured_archive_outcomes(universe, outcome_config)
    candidate_outcomes = all_outcomes.loc[
        all_outcomes["role"].isin(decision_contract["roles"])
    ].copy()
    if _candidate_identity_contract(candidate_outcomes) != decision_contract["candidate_identity"]:
        raise RuntimeError("Phase-B candidate IDs differ from the outcome-free V1 universe.")
    outcomes = all_outcomes.loc[all_outcomes["role"].eq("primary_oot")].copy()
    evaluated, joined = evaluate_frozen_portfolios(
        primary_records,
        primary_allocations,
        outcomes,
        config=outcome_config,
    )
    if not bool(evaluated["full_budget"].all()):
        raise RuntimeError("At least one evaluated primary portfolio failed full-budget status.")
    outcome_audit = primary_outcome_audit(outcomes, primary_allocations)
    monthly, window, directions = build_sharp_embedding_contrasts(
        joined,
        config=config,
        lgd=float(outcome_config["payoff"]["lgd"]),
    )
    repeated_freeze_path, repeated_freeze, repeated_artifacts = _verify_frozen_phase(
        config,
        evaluation_commit=protocol_commit,
        evaluation_config_path=resolved_config,
        evaluation_environment=initial_authority["environment"],
        evaluation_provenance=initial_authority["implementation"],
        repo_root=root,
    )
    if (
        repeated_freeze_path != freeze_path
        or repeated_freeze != freeze
        or repeated_artifacts != artifacts
    ):
        raise RuntimeError("Hash-pinned source authority changed during Phase B.")
    if sha256_file(raw_path) != str(config["outcomes"]["raw_sha256"]):
        raise RuntimeError("Raw outcome archive changed during Phase B.")
    _require_unchanged_authority(
        config=config,
        config_path=resolved_config,
        protocol_commit=protocol_commit,
        initial=initial_authority,
        root=root,
    )
    summary = _evaluation_summary(
        config=config,
        protocol_commit=protocol_commit,
        freeze=freeze,
        evaluated=evaluated,
        joined=joined,
        monthly=monthly,
        window=window,
        directions=directions,
        outcome_audit=outcome_audit,
    )

    paths = prepare_output_paths(config, repo_root=root)
    evaluation_dir = paths.data_dir / "evaluation"
    output = config["output"]
    evaluation_files = {
        "evaluated_portfolios": atomic_write_parquet(
            evaluated, evaluation_dir / str(output["evaluated_portfolios"])
        ),
        "joined_funded_allocations": atomic_write_parquet(
            joined, evaluation_dir / str(output["joined_funded_allocations"])
        ),
        "monthly_sharp_contrasts": atomic_write_parquet(
            monthly, evaluation_dir / str(output["monthly_sharp_contrasts"])
        ),
        "window_sharp_contrasts": atomic_write_parquet(
            window, evaluation_dir / str(output["window_sharp_contrasts"])
        ),
        "metric_direction_census": atomic_write_parquet(
            directions, evaluation_dir / str(output["metric_direction_census"])
        ),
        "outcome_join_audit": atomic_write_parquet(
            outcome_audit, evaluation_dir / str(output["outcome_join_audit"])
        ),
    }
    summary_path = atomic_write_json(paths.model_dir / str(output["evaluation_summary"]), summary)
    receipt_path = atomic_write_json(
        paths.model_dir / str(output["evaluation_receipt"]),
        {
            "schema_version": str(config["schema_version"]),
            "status": EVALUATION_STATUS,
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "started_at_utc": started_at,
            "completed_at_utc": utc_now_iso(),
            "elapsed_seconds": float(time.perf_counter() - started),
            "source_freeze": relative_artifact_descriptor(freeze_path, repo_root=root),
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    manifest = {
        "schema_version": str(config["schema_version"]),
        "status": EVALUATION_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "source_freeze": relative_artifact_descriptor(freeze_path, repo_root=root),
        "source_artifacts": {
            name: dict(freeze["outcome_free_artifacts"][name]) for name in sorted(artifacts)
        },
        "outcome_source": {
            "config": relative_artifact_descriptor(outcome_config_path, repo_root=root),
            "raw_path": str(config["outcomes"]["raw_path"]),
            "raw_sha256": str(config["outcomes"]["raw_sha256"]),
            "columns_joined_after_freeze": list(config["outcomes"]["joined_columns"]),
        },
        "schemas": {
            name: dataframe_schema(frame)
            for name, frame in {
                "evaluated_portfolios": evaluated,
                "joined_funded_allocations": joined,
                "monthly_sharp_contrasts": monthly,
                "window_sharp_contrasts": window,
                "metric_direction_census": directions,
                "outcome_join_audit": outcome_audit,
            }.items()
        },
        "evaluation_artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in evaluation_files.items()
        },
        "summary": relative_artifact_descriptor(summary_path, repo_root=root),
        "execution_receipt": relative_artifact_descriptor(receipt_path, repo_root=root),
        "implementation_provenance": initial_authority["implementation"],
        "environment": initial_authority["environment"],
        "git": initial_authority["git"],
        "selection": {
            "theta": None,
            "gamma": None,
            "ruler": None,
            "coordinate": None,
            "window": None,
            "policy": None,
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    repeated_freeze_path, repeated_freeze, repeated_artifacts = _verify_frozen_phase(
        config,
        evaluation_commit=protocol_commit,
        evaluation_config_path=resolved_config,
        evaluation_environment=initial_authority["environment"],
        evaluation_provenance=initial_authority["implementation"],
        repo_root=root,
    )
    if (
        repeated_freeze_path != freeze_path
        or repeated_freeze != freeze
        or repeated_artifacts != artifacts
    ):
        raise RuntimeError("Hash-pinned source authority changed before the Phase-B seal.")
    if sha256_file(raw_path) != str(config["outcomes"]["raw_sha256"]):
        raise RuntimeError("Raw outcome archive changed before the Phase-B seal.")
    _require_unchanged_authority(
        config=config,
        config_path=resolved_config,
        protocol_commit=protocol_commit,
        initial=initial_authority,
        root=root,
    )
    for name, path in evaluation_files.items():
        if (
            relative_artifact_descriptor(path, repo_root=root)
            != manifest["evaluation_artifacts"][name]
        ):
            raise RuntimeError(f"A V2 evaluation artifact changed before seal: {name}.")
    if (
        relative_artifact_descriptor(summary_path, repo_root=root) != manifest["summary"]
        or relative_artifact_descriptor(receipt_path, repo_root=root)
        != manifest["execution_receipt"]
    ):
        raise RuntimeError("The V2 summary or receipt changed before seal.")
    manifest_path = atomic_write_json(
        paths.model_dir / str(output["evaluation_manifest"]), manifest
    )
    logger.info(
        "Evaluated {} primary policies and {} sharp window contrasts in {:.1f}s",
        len(evaluated),
        len(window),
        time.perf_counter() - started,
    )
    return manifest_path


def main(argv: Sequence[str] | None = None) -> None:
    """Dispatch exactly one locked phase."""
    args = parse_args(argv)
    if args.phase == "outcome-free":
        path = run_outcome_free(config_path=args.config, repo_root=ROOT)
    else:
        path = run_evaluation(config_path=args.config, repo_root=ROOT)
    logger.info("Wrote {}", path)


if __name__ == "__main__":
    main()
