"""Run the retrospective V1d Phase-B persistence recovery."""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.experiments import (  # noqa: E402
    run_ijds_set_preserving_embedding_sensitivity_v1c as v1c,
)
from src.ijds_audit.config import load_v4_config  # noqa: E402
from src.ijds_audit.evaluation import evaluate_frozen_portfolios  # noqa: E402
from src.ijds_audit.protocol import (  # noqa: E402
    configured_archive_outcomes,
    load_outcome_universe,
)
from src.ijds_challengers.set_preserving_embedding import primary_outcome_audit  # noqa: E402
from src.ijds_challengers.set_preserving_embedding_v1c import (  # noqa: E402
    build_v1c_sharp_embedding_contrasts,
)
from src.ijds_challengers.set_preserving_embedding_v1d import (  # noqa: E402
    PERSISTED_SCHEMA_DTYPES,
    expected_v1d_persisted_schemas,
    prepare_v1d_evaluated_portfolios,
    prepare_v1d_window_sharp_contrasts,
    validate_v1d_persisted_numeric_finiteness,
)
from src.utils.isolated_experiment import dataframe_schema  # noqa: E402
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    utc_now_iso,
)

DEFAULT_CONFIG_PATH = (
    ROOT / "configs/experiments/ijds_set_preserving_embedding_sensitivity_2026-07-30_v1d.yaml"
)
CONFIG_RELATIVE = Path(
    "configs/experiments/ijds_set_preserving_embedding_sensitivity_2026-07-30_v1d.yaml"
)
PROTOCOL_RELATIVE = Path(
    "docs/research/ijds_set_preserving_embedding_sensitivity_v1d_protocol_2026-07-30.md"
)
NO_GO_RELATIVE = Path(
    "docs/research/ijds_set_preserving_embedding_sensitivity_v1c_no_go_2026-07-30.md"
)
BASE_CONFIG_RELATIVE = Path(
    "configs/experiments/ijds_set_preserving_embedding_sensitivity_2026-07-29_v1c.yaml"
)
EVALUATION_STATUS = "retrospective_post_inspection_v1d_phase_b_complete_not_confirmatory"
PENDING_ARTIFACT_STATUS = v1c.PENDING_ARTIFACT_STATUS
SOURCE_KEYS = v1c.SOURCE_KEYS
DATA_OUTPUT_KEYS = v1c.DATA_OUTPUT_KEYS
MODEL_OUTPUT_KEYS = v1c.MODEL_OUTPUT_KEYS
IMPLEMENTATION_PATHS = tuple(
    dict.fromkeys(
        (
            *v1c.IMPLEMENTATION_PATHS,
            CONFIG_RELATIVE,
            PROTOCOL_RELATIVE,
            NO_GO_RELATIVE,
            Path("scripts/experiments/run_ijds_set_preserving_embedding_sensitivity_v1d.py"),
            Path("src/ijds_challengers/set_preserving_embedding_v1d.py"),
        )
    )
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--protected-read-root", type=Path)
    parser.add_argument("--verify-artifact-commit", action="store_true")
    args = parser.parse_args(argv)
    if not args.verify_artifact_commit and args.protected_read_root is None:
        parser.error("--protected-read-root is required for V1d Phase B")
    return args


def _resolved_locked_config(config_path: Path, root: Path) -> Path:
    candidate = config_path if config_path.is_absolute() else root / config_path
    resolved = candidate.resolve()
    if resolved != (root / CONFIG_RELATIVE).resolve():
        raise RuntimeError("V1d execution accepts only its singular repository config path.")
    return resolved


def _expected_delta_contract() -> dict[str, Any]:
    return {
        "schema_version": "2026-07-30.v1d.1",
        "protocol_status": ("retrospective_post_inspection_v1c_no_go_recovery_phase_b_only"),
        "protocol_tag": ("protocol/ijds-set-preserving-embedding-sensitivity-2026-07-30-v1d"),
        "run_tag": "ijds-set-preserving-embedding-sensitivity-2026-07-30-v1d",
    }


def load_v1d_config(path: Path, *, repo_root: Path = ROOT) -> dict[str, Any]:
    """Load the V1d delta and materialize its inherited V1a/V1c scientific contract."""
    delta = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(delta, dict):
        raise ValueError("V1d config root must be a mapping.")
    required = {
        "schema_version",
        "protocol_status",
        "protocol_tag",
        "run_tag",
        "base_v1c_contract",
        "v1c_no_go",
        "git_transport",
        "persistence_contract",
        "windows_preflight",
        "output",
    }
    if set(delta) != required:
        raise ValueError(f"V1d delta fields changed: {sorted(set(delta) ^ required)}.")
    identities = _expected_delta_contract()
    if any(delta.get(key) != value for key, value in identities.items()):
        raise ValueError("V1d identity/status drifted from the locked recovery.")
    base_raw = delta["base_v1c_contract"]
    if not isinstance(base_raw, dict) or set(base_raw) != {
        "path",
        "bytes",
        "sha256",
        "reuse",
    }:
        raise ValueError("V1d base V1c contract fields changed.")
    base_descriptor = v1c._validated_descriptor(
        {key: base_raw[key] for key in ("path", "bytes", "sha256")},
        label="base_v1c_contract",
    )
    expected_base = {
        "path": BASE_CONFIG_RELATIVE.as_posix(),
        "bytes": 14_468,
        "sha256": "60fc48e82f8c7be6431212085cb0e573a2f32376618970b9a66d7519e9100661",
    }
    if (
        base_descriptor != expected_base
        or base_raw.get("reuse") != "scientific_sections_and_git_native_source_contract_only"
    ):
        raise ValueError("V1d base V1c descriptor/reuse boundary changed.")
    base_path = v1c._resolve_repo_path(repo_root.resolve(), base_descriptor["path"])
    v1c._require_descriptor_match(
        v1c._file_descriptor(base_path, logical_path=base_descriptor["path"]),
        base_descriptor,
        label="V1d base V1c config",
    )
    base = v1c.load_v1c_config(base_path)

    no_go = delta["v1c_no_go"]
    expected_no_go = {
        "status_note": NO_GO_RELATIVE.as_posix(),
        "classification": "retrospective_post_inspection_non_evidence",
        "first_launch": "windows_max_path_pre_outcome_prewrite",
        "retry": "ephemeral_windows_longpaths_then_phase_b_materialized",
        "elapsed_seconds": 167.8,
        "materialized_output_files": 9,
        "evaluation_rows": 18_000,
        "evaluation_columns": 50,
        "undeclared_nonfinite_field": "realized_payoff_exact",
        "undeclared_missing_rows": 8_325,
        "missing_iff": "n_unresolved_positive_exposure_gt_zero",
        "resolved_exact_rows": 9_675,
        "outputs_committed": False,
        "artifact_tag_created": False,
        "outputs_are_evidence": False,
    }
    if no_go != expected_no_go:
        raise ValueError("V1d does not retain the exact V1c NO-GO facts.")
    transport_delta = delta["git_transport"]
    expected_transport_delta = {
        "topology": (
            "annotated_protocol_P2_to_direct_child_source_A2_to_direct_child_evaluation_B2"
        ),
        "source_artifact_tag": (
            "artifacts/ijds-set-preserving-embedding-sensitivity-2026-07-30-v1a-recovery-v1d"
        ),
        "evaluation_artifact_tag": (
            "artifacts/ijds-set-preserving-embedding-sensitivity-2026-07-30-v1d"
        ),
        "source_paths": "inherit_exact_eleven_v1a_descriptors_from_v1c",
        "evaluation_paths": "derive_exact_nine_compact_paths_from_v1d_run_tag",
        "annotated_tags_required": True,
        "single_parent_required": True,
        "exact_diff_required": True,
        "paths_absent_in_parent_required": True,
        "dvc_required": False,
    }
    if transport_delta != expected_transport_delta:
        raise ValueError("V1d P2-to-A2-to-B2 transport delta changed.")
    expected_windows = {
        "timing": "before_protected_archive_read_and_before_outcomes",
        "windows_requirement": "effective_git_core_longpaths_true",
        "non_windows": "not_applicable",
        "serialize_absolute_paths": False,
    }
    if delta["windows_preflight"] != expected_windows:
        raise ValueError("V1d Windows pre-outcome long-path gate changed.")

    config = copy.deepcopy(base)
    config.update(identities)
    config["inspection_context"] = {
        "classification": "retrospective_post_inspection_v1c_no_go_recovery",
        "replay_clean": False,
        "confirmatory": False,
        "v1a_is_evidence": False,
        "v1c_is_evidence": False,
        "phase_a_rerun": False,
        "v1c_phase_b_outputs_reused": False,
    }
    config["v1c_no_go"] = copy.deepcopy(no_go)
    config["persistence_contract"] = copy.deepcopy(delta["persistence_contract"])
    config["windows_preflight"] = copy.deepcopy(delta["windows_preflight"])
    config["base_v1c_contract"] = copy.deepcopy(delta["base_v1c_contract"])
    config["git_transport"]["topology"] = transport_delta["topology"]
    config["git_transport"]["protocol_tag"] = identities["protocol_tag"]
    config["git_transport"]["source_artifact_tag"] = transport_delta["source_artifact_tag"]
    config["git_transport"]["evaluation_artifact_tag"] = transport_delta["evaluation_artifact_tag"]
    old_run = str(base["run_tag"])
    new_run = str(identities["run_tag"])
    config["git_transport"]["source_to_evaluation_paths"] = [
        str(item).replace(old_run, new_run)
        for item in base["git_transport"]["source_to_evaluation_paths"]
    ]
    config["output"].update(delta["output"])
    expected_outputs = v1c._expected_output_paths(config)
    if (
        set(expected_outputs) != set(config["git_transport"]["source_to_evaluation_paths"])
        or len(expected_outputs) != 9
    ):
        raise ValueError("V1d does not derive exactly nine compact B2 paths.")
    _validate_persistence_contract(config["persistence_contract"])
    return config


def _validate_persistence_contract(contract: Mapping[str, Any]) -> None:
    expected = {
        "evaluated_portfolios": {
            "source_columns": 50,
            "persisted_columns": 49,
            "drop_columns": ["realized_payoff_exact"],
            "retained_identified_set": [
                "realized_payoff_lower",
                "realized_payoff_upper",
            ],
            "exact_missing_rows_observed_in_v1c": 8_325,
            "exact_resolved_rows_observed_in_v1c": 9_675,
        },
        "pooled_window_contrasts": {
            "source_columns": 40,
            "persisted_columns": 39,
            "drop_columns": ["period"],
            "source_period_missing_rows_observed_in_v1c": 1_200,
            "period_semantics": "pooled_scope_has_no_single_month_period",
        },
        "exact_persisted_schema_columns": {
            "evaluated_portfolios": 49,
            "monthly_sharp_contrasts": 40,
            "window_sharp_contrasts": 39,
            "metric_direction_census": 16,
            "outcome_join_audit": 7,
        },
        "exact_persisted_schema_rows": {
            "evaluated_portfolios": 18_000,
            "monthly_sharp_contrasts": 18_000,
            "window_sharp_contrasts": 1_200,
            "metric_direction_census": 3_600,
            "outcome_join_audit": 15,
        },
        "numeric_finiteness": {
            "all_persisted_numeric_finite": True,
            "all_other_persisted_values_nonmissing": True,
            "sole_exceptions": {
                "frontier_cap": "missing_exactly_for_objective_matched",
                "objective_target": "missing_exactly_for_normalized_score",
                "risk_tolerance": "missing_exactly_for_objective_matched",
            },
            "expected_missing_each": 9_000,
            "snapshot_default_unresolved_allowed_only_in_memory": True,
        },
    }
    if dict(contract) != expected:
        raise ValueError("V1d exact-column/finiteness persistence contract changed.")
    for key, ordered_dtypes in PERSISTED_SCHEMA_DTYPES.items():
        if int(contract["exact_persisted_schema_columns"][key]) != len(ordered_dtypes):
            raise ValueError(f"V1d {key} width differs from its hash-bound schema.")


def _require_exact_schema_descriptors(
    schemas: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    label: str,
) -> None:
    expected = expected_v1d_persisted_schemas(contract)
    if set(schemas) != set(expected):
        raise RuntimeError(f"V1d {label} schema table census changed.")
    for key, expected_schema in expected.items():
        observed = schemas[key]
        if not isinstance(observed, Mapping) or set(observed) != {
            "rows",
            "columns",
            "dtypes",
        }:
            raise RuntimeError(f"V1d {label} {key} schema descriptor changed shape.")
        observed_dtypes = observed["dtypes"]
        if (
            not isinstance(observed_dtypes, Mapping)
            or int(observed["rows"]) != int(expected_schema["rows"])
            or int(observed["columns"]) != int(expected_schema["columns"])
            or list(observed_dtypes.items()) != list(expected_schema["dtypes"].items())
        ):
            raise RuntimeError(
                f"V1d {label} {key} row/name/order/dtype schema differs from the lock."
            )


def windows_longpaths_preflight(
    repo_root: Path, *, platform_name: str | None = None
) -> dict[str, Any]:
    """Fail before outcomes unless effective Windows Git long paths are enabled."""
    platform = os.name if platform_name is None else str(platform_name)
    if platform != "nt":
        return {
            "platform": "non_windows",
            "status": "not_applicable",
            "checked_before_outcomes": True,
        }
    result = v1c._git(repo_root.resolve(), ["config", "--bool", "core.longpaths"], check=False)
    if result.returncode != 0 or result.stdout.strip().casefold() != "true":
        raise RuntimeError(
            "V1d Windows pre-outcome gate requires effective Git core.longpaths=true."
        )
    return {
        "platform": "windows",
        "status": "effective_git_core_longpaths_true",
        "checked_before_outcomes": True,
    }


def _require_implementation_bound_to_protocol(
    root: Path, *, protocol_commit: str, source_commit: str
) -> dict[str, dict[str, Any]]:
    descriptors: dict[str, dict[str, Any]] = {}
    for relative in IMPLEMENTATION_PATHS:
        name = relative.as_posix()
        at_protocol = v1c._blob_descriptor(root, protocol_commit, name)
        at_source = v1c._blob_descriptor(root, source_commit, name)
        if at_protocol != at_source:
            raise RuntimeError(f"V1d implementation changed between P2 and A2: {name}.")
        current = v1c._file_descriptor(v1c._resolve_repo_path(root, name), logical_path=name)
        if current != at_source:
            raise RuntimeError(f"V1d worktree implementation differs from A2: {name}.")
        descriptors[name] = current
    return descriptors


def verify_source_authority(
    config: Mapping[str, Any],
    *,
    repo_root: Path,
    required_head: str,
    require_untracked_clean: bool,
) -> dict[str, Any]:
    """Verify P2 -> A2 plus the eleven inherited V1a source bytes."""
    root = repo_root.resolve()
    transport = config["git_transport"]
    protocol = v1c._tag_authority(root, str(transport["protocol_tag"]))
    source = v1c._tag_authority(root, str(transport["source_artifact_tag"]))
    if v1c._head_commit(root) != required_head:
        raise RuntimeError("V1d HEAD differs from its required P2/A2/B2 authority.")
    state = v1c._git_state(root, include_untracked=require_untracked_clean)
    if state["dirty"]:
        cleanliness = "full" if require_untracked_clean else "tracked"
        raise RuntimeError(f"V1d requires a clean {cleanliness} worktree: {state['lines']}.")
    source_paths = tuple(str(item) for item in transport["protocol_to_source_paths"])
    v1c._require_exact_addition_commit(
        root,
        child=source["commit"],
        parent=protocol["commit"],
        expected_paths=source_paths,
    )
    materialized: dict[str, Path] = {}
    for key in SOURCE_KEYS:
        expected = v1c._validated_descriptor(
            config["source_v1a_artifacts"][key],
            label=f"source_v1a_artifacts.{key}",
        )
        v1c._require_descriptor_match(
            v1c._blob_descriptor(root, source["commit"], expected["path"]),
            expected,
            label=f"V1d source Git blob {key}",
        )
        path = v1c._resolve_repo_path(root, expected["path"])
        v1c._require_descriptor_match(
            v1c._file_descriptor(path, logical_path=expected["path"]),
            expected,
            label=f"V1d source worktree {key}",
        )
        materialized[key] = path
    original = v1c._verify_original_v1a_authority(config, root)
    implementation = _require_implementation_bound_to_protocol(
        root,
        protocol_commit=protocol["commit"],
        source_commit=source["commit"],
    )
    freeze = v1c._verify_source_payloads(config, root=root, paths=materialized)
    return {
        "protocol": protocol,
        "source": source,
        "original_v1a": original,
        "git": state,
        "implementation": implementation,
        "paths": materialized,
        "freeze": freeze,
    }


def _source_snapshot(authority: Mapping[str, Any], *, root: Path) -> dict[str, Any]:
    return {
        "protocol": dict(authority["protocol"]),
        "source": dict(authority["source"]),
        "original_v1a": dict(authority["original_v1a"]),
        "git_commit": authority["git"]["commit"],
        "source_files": {
            key: v1c._relative_descriptor(path, root=root)
            for key, path in sorted(authority["paths"].items())
        },
        "implementation": dict(authority["implementation"]),
    }


def _summary(
    *,
    config: Mapping[str, Any],
    authority: Mapping[str, Any],
    evaluated: pd.DataFrame,
    joined: pd.DataFrame,
    monthly: pd.DataFrame,
    window: pd.DataFrame,
    directions: pd.DataFrame,
    outcome_audit: pd.DataFrame,
    protected_descriptor: Mapping[str, Any],
    longpaths: Mapping[str, Any],
) -> dict[str, Any]:
    periods = int(config["frontier"]["expected_primary_months"])
    budget = float(config["normalization"]["committed_budget_per_period"])
    return {
        "schema_version": str(config["schema_version"]),
        "status": EVALUATION_STATUS,
        "artifact_status": PENDING_ARTIFACT_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": authority["protocol"]["commit"],
        "source_artifact_tag": authority["source"]["tag"],
        "source_artifact_commit": authority["source"]["commit"],
        "expected_evaluation_artifact_tag": str(config["git_transport"]["evaluation_artifact_tag"]),
        "classification": "retrospective_post_inspection_v1c_no_go_recovery",
        "replay_clean": False,
        "confirmatory": False,
        "v1a_is_evidence": False,
        "v1c_is_evidence": False,
        "v1c_phase_b_outputs_reused": False,
        "v1c_no_go": copy.deepcopy(config["v1c_no_go"]),
        "counts": {
            "evaluated_primary_portfolios": int(len(evaluated)),
            "evaluated_persisted_columns": int(len(evaluated.columns)),
            "joined_primary_funded_rows_in_memory": int(len(joined)),
            "monthly_sharp_contrasts": int(len(monthly)),
            "window_sharp_contrasts": int(len(window)),
            "metric_direction_rows": int(len(directions)),
            "outcome_audit_rows": int(len(outcome_audit)),
        },
        "persistence_repair": {
            "dropped_by_output": {
                "evaluated_portfolios": ["realized_payoff_exact"],
                "window_sharp_contrasts": ["period"],
            },
            "retained": ["realized_payoff_lower", "realized_payoff_upper"],
            "all_other_persisted_numeric_finite": True,
            "all_other_persisted_values_nonmissing": True,
            "ruler_structural_na_fields": [
                "frontier_cap",
                "objective_target",
                "risk_tolerance",
            ],
        },
        "normalization": {
            "committed_budget_B_dollars": budget,
            "primary_periods_T": periods,
            "pooled_capital_TB_dollars": periods * budget,
            "common_across_policies": True,
            "solver_capital_renormalization": False,
        },
        "negative_control": v1c._negative_control_summary(window),
        "direction_counts": v1c._direction_counts(directions, "direction_at_tolerance"),
        "geometric_direction_counts": v1c._direction_counts(directions, "geometric_direction"),
        "windows_longpaths_preflight": dict(longpaths),
        "joined_row_level_table_persisted": False,
        "selection": {
            "theta": None,
            "gamma": None,
            "ruler": None,
            "coordinate": None,
            "window": None,
            "policy": None,
        },
        "policy_winner": None,
        "p_values_computed": False,
        "protected_source_root_binding": "explicit_distinct_hash_bound_source_root",
        "protected_source_root_distinct_from_execution_checkout": True,
        "protected_stages_run": [],
        "protected_artifacts_read": [dict(protected_descriptor)],
        "protected_artifacts_written": [],
    }


def run_phase_b(
    *,
    config_path: Path,
    protected_read_root: Path,
    repo_root: Path = ROOT,
) -> Path:
    """Replay Phase B from A2 and persist the repaired 49-column evaluation."""
    started = time.perf_counter()
    started_at = utc_now_iso()
    root = repo_root.resolve()
    resolved_config = _resolved_locked_config(config_path, root)
    config = load_v1d_config(resolved_config, repo_root=root)
    longpaths = windows_longpaths_preflight(root)
    source_tag = v1c._tag_authority(root, str(config["git_transport"]["source_artifact_tag"]))
    initial = verify_source_authority(
        config,
        repo_root=root,
        required_head=source_tag["commit"],
        require_untracked_clean=True,
    )
    initial_snapshot = _source_snapshot(initial, root=root)
    v1c._preflight_fresh_outputs(config, root=root)
    raw_path, raw_descriptor = v1c._resolve_protected_raw(
        config, protected_read_root=protected_read_root, repo_root=root
    )

    build = v1c._load_and_validate_phase_a(config, initial)
    records = build.solve_records
    allocations = build.allocations
    primary_records = records.loc[records["role"].eq("primary_oot")].copy()
    primary_allocations = allocations.loc[allocations["role"].eq("primary_oot")].copy()
    del build, records, allocations
    if len(primary_records) != int(config["expected_census"]["primary_evaluated_portfolios"]):
        raise RuntimeError("V1d frozen primary portfolio census changed before outcomes.")

    outcome_config_path = v1c._resolve_repo_path(root, str(config["outcomes"]["parent_config"]))
    outcome_config = load_v4_config(outcome_config_path)
    decision_contract = initial["freeze"]["decision_contract"]
    if (
        str(config["outcomes"]["endpoint"]) != str(outcome_config["design"]["endpoint"])
        or float(decision_contract["budget"])
        != float(config["normalization"]["committed_budget_per_period"])
        or float(decision_contract["lgd"]) != float(outcome_config["payoff"]["lgd"])
    ):
        raise RuntimeError("V1d source decision contract and endpoint/budget/LGD diverged.")
    universe = load_outcome_universe(outcome_config, raw_path=raw_path)
    all_outcomes = configured_archive_outcomes(universe, outcome_config)
    endpoint_audit = v1c._validate_endpoint_values(all_outcomes, label="V1d configured archive")
    candidate_outcomes = all_outcomes.loc[
        all_outcomes["role"].isin(decision_contract["roles"])
    ].copy()
    if (
        v1c._candidate_identity_contract(candidate_outcomes)
        != decision_contract["candidate_identity"]
    ):
        raise RuntimeError("V1d candidate identity differs from the V1a frozen universe.")
    outcomes = all_outcomes.loc[all_outcomes["role"].eq("primary_oot")].copy()
    evaluated_full, joined = evaluate_frozen_portfolios(
        primary_records,
        primary_allocations,
        outcomes,
        config=outcome_config,
    )
    joined_endpoint_audit = v1c._validate_endpoint_values(
        joined, label="V1d joined funded allocation"
    )
    if not bool(evaluated_full["full_budget"].all()):
        raise RuntimeError("A V1d evaluated primary portfolio failed full-budget status.")
    evaluated = prepare_v1d_evaluated_portfolios(
        evaluated_full, contract=config["persistence_contract"]
    )
    outcome_audit = primary_outcome_audit(outcomes, primary_allocations)
    monthly, window_full, directions = build_v1c_sharp_embedding_contrasts(
        joined,
        config=config,
        lgd=float(outcome_config["payoff"]["lgd"]),
        budget=float(config["normalization"]["committed_budget_per_period"]),
    )
    window = prepare_v1d_window_sharp_contrasts(
        window_full, contract=config["persistence_contract"]
    )
    frames = {
        "evaluated_portfolios": evaluated,
        "monthly_sharp_contrasts": monthly,
        "window_sharp_contrasts": window,
        "metric_direction_census": directions,
        "outcome_join_audit": outcome_audit,
    }
    validate_v1d_persisted_numeric_finiteness(frames, contract=config["persistence_contract"])
    schemas = {key: dataframe_schema(frame) for key, frame in frames.items()}
    _require_exact_schema_descriptors(
        schemas,
        contract=config["persistence_contract"],
        label="prewrite",
    )
    v1c._require_output_census(
        config,
        evaluated=evaluated,
        joined=joined,
        monthly=monthly,
        window=window,
        directions=directions,
        outcome_audit=outcome_audit,
    )
    join_identity = {
        "schema_version": str(config["schema_version"]),
        "status": EVALUATION_STATUS,
        "artifact_status": PENDING_ARTIFACT_STATUS,
        "run_tag": str(config["run_tag"]),
        "joined_table": v1c._dataframe_content_identity(joined),
        "source_allocation": dict(config["source_v1a_artifacts"]["allocations"]),
        "outcome_source": dict(raw_descriptor),
        "primary_candidate_identity": v1c._candidate_identity_contract(outcomes),
        "endpoint_value_audit": endpoint_audit,
        "joined_endpoint_value_audit": joined_endpoint_audit,
        "joined_row_level_table_persisted": False,
        "v1c_phase_b_outputs_reused": False,
        "protected_source_root_binding": "explicit_distinct_hash_bound_source_root",
        "protected_source_root_distinct_from_execution_checkout": True,
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }

    repeated = verify_source_authority(
        config,
        repo_root=root,
        required_head=initial["source"]["commit"],
        require_untracked_clean=True,
    )
    v1c._require_unchanged_source_snapshot(initial_snapshot, _source_snapshot(repeated, root=root))
    if v1c._file_descriptor(raw_path, logical_path=raw_descriptor["path"]) != raw_descriptor:
        raise RuntimeError("V1d protected raw archive changed during Phase B.")

    summary = _summary(
        config=config,
        authority=initial,
        evaluated=evaluated,
        joined=joined,
        monthly=monthly,
        window=window,
        directions=directions,
        outcome_audit=outcome_audit,
        protected_descriptor=raw_descriptor,
        longpaths=longpaths,
    )
    _, model_dir, evaluation_dir = v1c._output_directories(config, root)
    evaluation_dir.mkdir(parents=True, exist_ok=False)
    model_dir.mkdir(parents=True, exist_ok=False)
    output = config["output"]
    written: dict[str, Path] = {
        key: atomic_write_parquet(frame, evaluation_dir / str(output[key]))
        for key, frame in frames.items()
    }
    written["join_identity"] = atomic_write_json(
        model_dir / str(output["join_identity"]), join_identity
    )
    written["evaluation_summary"] = atomic_write_json(
        model_dir / str(output["evaluation_summary"]), summary
    )
    receipt = {
        "schema_version": str(config["schema_version"]),
        "status": EVALUATION_STATUS,
        "artifact_status": PENDING_ARTIFACT_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": initial["protocol"]["commit"],
        "source_artifact_tag": initial["source"]["tag"],
        "source_artifact_commit": initial["source"]["commit"],
        "started_at_utc": started_at,
        "scientific_calculation_completed_at_utc": utc_now_iso(),
        "elapsed_seconds": float(time.perf_counter() - started),
        "classification": "retrospective_post_inspection_v1c_no_go_recovery",
        "v1c_phase_b_outputs_reused": False,
        "persistence_repair": (
            "drop_realized_payoff_exact_and_pooled_period_retain_payoff_lower_upper"
        ),
        "windows_longpaths_preflight": dict(longpaths),
        "source_files_verified": len(SOURCE_KEYS),
        "protected_source_root_binding": "explicit_distinct_hash_bound_source_root",
        "protected_source_root_distinct_from_execution_checkout": True,
        "protected_stages_run": [],
        "protected_artifacts_read": [dict(raw_descriptor)],
        "protected_artifacts_written": [],
    }
    written["evaluation_receipt"] = atomic_write_json(
        model_dir / str(output["evaluation_receipt"]), receipt
    )

    after_write = verify_source_authority(
        config,
        repo_root=root,
        required_head=initial["source"]["commit"],
        require_untracked_clean=False,
    )
    v1c._require_unchanged_source_snapshot(
        initial_snapshot, _source_snapshot(after_write, root=root)
    )
    if v1c._file_descriptor(raw_path, logical_path=raw_descriptor["path"]) != raw_descriptor:
        raise RuntimeError("V1d protected raw archive changed before its output seal.")
    artifact_descriptors = {
        key: v1c._relative_descriptor(path, root=root) for key, path in sorted(written.items())
    }
    manifest_relative = (
        f"{output['model_root']}/{config['run_tag']}/{output['evaluation_manifest']}"
    )
    expected_nonmanifest = set(config["git_transport"]["source_to_evaluation_paths"]) - {
        manifest_relative
    }
    if {item["path"] for item in artifact_descriptors.values()} != expected_nonmanifest:
        raise RuntimeError("V1d written files differ from its locked compact paths.")
    manifest = {
        "schema_version": str(config["schema_version"]),
        "status": EVALUATION_STATUS,
        "artifact_status": PENDING_ARTIFACT_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol": dict(initial["protocol"]),
        "source_artifact": dict(initial["source"]),
        "original_v1a": dict(initial["original_v1a"]),
        "base_v1c_contract": copy.deepcopy(config["base_v1c_contract"]),
        "v1c_no_go": copy.deepcopy(config["v1c_no_go"]),
        "source_v1a_artifacts": {
            key: dict(config["source_v1a_artifacts"][key]) for key in SOURCE_KEYS
        },
        "outcome_source": {
            "config": v1c._relative_descriptor(outcome_config_path, root=root),
            "protected_artifact": dict(raw_descriptor),
            "columns_joined_after_freeze": list(config["outcomes"]["joined_columns"]),
        },
        "schemas": schemas,
        "evaluation_artifacts": artifact_descriptors,
        "artifact_contract": {
            "expected_tag": str(config["git_transport"]["evaluation_artifact_tag"]),
            "expected_parent": initial["source"]["commit"],
            "exact_added_paths": list(config["git_transport"]["source_to_evaluation_paths"]),
            "direct_child_required": True,
            "annotated_tag_required": True,
            "dvc_required": False,
        },
        "implementation": dict(initial["implementation"]),
        "environment": v1c._portable_environment(root),
        "classification": "retrospective_post_inspection_v1c_no_go_recovery",
        "replay_clean": False,
        "confirmatory": False,
        "v1a_is_evidence": False,
        "v1c_is_evidence": False,
        "v1c_phase_b_outputs_reused": False,
        "persistence_repair": copy.deepcopy(config["persistence_contract"]),
        "windows_longpaths_preflight": dict(longpaths),
        "selection": summary["selection"],
        "policy_winner": None,
        "p_values_computed": False,
        "protected_source_root_binding": "explicit_distinct_hash_bound_source_root",
        "protected_source_root_distinct_from_execution_checkout": True,
        "protected_stages_run": [],
        "protected_artifacts_read": [dict(raw_descriptor)],
        "protected_artifacts_written": [],
    }
    manifest_path = atomic_write_json(model_dir / str(output["evaluation_manifest"]), manifest)
    final = verify_source_authority(
        config,
        repo_root=root,
        required_head=initial["source"]["commit"],
        require_untracked_clean=False,
    )
    v1c._require_unchanged_source_snapshot(initial_snapshot, _source_snapshot(final, root=root))
    if v1c._file_descriptor(raw_path, logical_path=raw_descriptor["path"]) != raw_descriptor:
        raise RuntimeError("V1d protected raw archive changed after its output seal.")
    all_written = {*written.values(), manifest_path}
    observed_paths = {path.resolve().relative_to(root).as_posix() for path in all_written}
    if observed_paths != set(config["git_transport"]["source_to_evaluation_paths"]):
        raise RuntimeError("V1d final output census differs from the locked nine B2 paths.")
    logger.info(
        "V1d evaluated {} policies into {} persisted columns in {:.1f}s",
        len(evaluated),
        len(evaluated.columns),
        time.perf_counter() - started,
    )
    return manifest_path


def verify_evaluation_artifact_commit(
    *, config_path: Path, repo_root: Path = ROOT
) -> dict[str, Any]:
    """Read-only verification of the final A2 -> B2 commit and annotated tag."""
    root = repo_root.resolve()
    resolved_config = _resolved_locked_config(config_path, root)
    config = load_v1d_config(resolved_config, repo_root=root)
    transport = config["git_transport"]
    evaluation = v1c._tag_authority(root, str(transport["evaluation_artifact_tag"]))
    if v1c._head_commit(root) != evaluation["commit"]:
        raise RuntimeError("V1d B2 tag must resolve exactly to current HEAD.")
    state = v1c._git_state(root, include_untracked=True)
    if state["dirty"]:
        raise RuntimeError(f"V1d B2 verification requires a fully clean worktree: {state}.")
    source = v1c._tag_authority(root, str(transport["source_artifact_tag"]))
    expected_paths = tuple(str(item) for item in transport["source_to_evaluation_paths"])
    v1c._require_exact_addition_commit(
        root,
        child=evaluation["commit"],
        parent=source["commit"],
        expected_paths=expected_paths,
    )
    source_authority = verify_source_authority(
        config,
        repo_root=root,
        required_head=evaluation["commit"],
        require_untracked_clean=True,
    )
    _, model_dir, _ = v1c._output_directories(config, root)
    output = config["output"]
    manifest_path = model_dir / str(output["evaluation_manifest"])
    summary_path = model_dir / str(output["evaluation_summary"])
    receipt_path = model_dir / str(output["evaluation_receipt"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    for label, payload in (("manifest", manifest), ("summary", summary), ("receipt", receipt)):
        if (
            payload.get("schema_version") != config["schema_version"]
            or payload.get("status") != EVALUATION_STATUS
            or payload.get("artifact_status") != PENDING_ARTIFACT_STATUS
            or payload.get("run_tag") != config["run_tag"]
        ):
            raise RuntimeError(f"V1d {label} identity or pending-at-exit status changed.")
        v1c._reject_absolute_serialized_paths(payload, location=f"v1d.{label}")
    if (
        manifest.get("protocol") != source_authority["protocol"]
        or manifest.get("source_artifact") != source_authority["source"]
    ):
        raise RuntimeError("V1d manifest P2/A2 authority differs from the tag chain.")
    expected_contract = {
        "expected_tag": str(transport["evaluation_artifact_tag"]),
        "expected_parent": source["commit"],
        "exact_added_paths": list(expected_paths),
        "direct_child_required": True,
        "annotated_tag_required": True,
        "dvc_required": False,
    }
    if manifest.get("artifact_contract") != expected_contract:
        raise RuntimeError("V1d manifest B2 requirement contract changed.")
    expected_artifact_keys = {
        *DATA_OUTPUT_KEYS,
        "join_identity",
        "evaluation_summary",
        "evaluation_receipt",
    }
    recorded = manifest.get("evaluation_artifacts")
    if not isinstance(recorded, dict) or set(recorded) != expected_artifact_keys:
        raise RuntimeError("V1d manifest has an incomplete nonmanifest artifact census.")
    persisted_frames: dict[str, pd.DataFrame] = {}
    for key, descriptor_value in recorded.items():
        descriptor = v1c._validated_descriptor(
            descriptor_value, label=f"v1d.evaluation_artifacts.{key}"
        )
        path = v1c._resolve_repo_path(root, descriptor["path"])
        v1c._require_descriptor_match(
            v1c._file_descriptor(path, logical_path=descriptor["path"]),
            descriptor,
            label=f"V1d B2 worktree {key}",
        )
        v1c._require_descriptor_match(
            v1c._blob_descriptor(root, evaluation["commit"], descriptor["path"]),
            descriptor,
            label=f"V1d B2 Git blob {key}",
        )
        if key in DATA_OUTPUT_KEYS:
            persisted_frames[key] = pd.read_parquet(path)
    manifest_descriptor = v1c._relative_descriptor(manifest_path, root=root)
    v1c._require_descriptor_match(
        v1c._blob_descriptor(root, evaluation["commit"], manifest_descriptor["path"]),
        manifest_descriptor,
        label="V1d B2 manifest",
    )
    all_paths = {descriptor["path"] for descriptor in recorded.values()} | {
        manifest_descriptor["path"]
    }
    if all_paths != set(expected_paths):
        raise RuntimeError("V1d manifest paths do not equal the exact A2-to-B2 diff.")
    validate_v1d_persisted_numeric_finiteness(
        persisted_frames, contract=config["persistence_contract"]
    )
    observed_schemas = {key: dataframe_schema(frame) for key, frame in persisted_frames.items()}
    _require_exact_schema_descriptors(
        observed_schemas,
        contract=config["persistence_contract"],
        label="B2 parquet",
    )
    schemas = manifest.get("schemas", {})
    if not isinstance(schemas, Mapping):
        raise RuntimeError("V1d manifest schemas are not a mapping.")
    _require_exact_schema_descriptors(
        schemas,
        contract=config["persistence_contract"],
        label="manifest",
    )
    if schemas != observed_schemas:
        raise RuntimeError("V1d manifest schemas differ from the B2 parquet files.")
    if (
        manifest.get("v1c_no_go") != config["v1c_no_go"]
        or manifest.get("v1c_phase_b_outputs_reused") is not False
    ):
        raise RuntimeError("V1d manifest obscures or reuses the V1c NO-GO.")
    return {
        "status": "verified_git_native_v1d_evaluation_artifact_commit",
        "protocol": source_authority["protocol"],
        "source": source_authority["source"],
        "evaluation": evaluation,
        "added_paths": list(expected_paths),
        "dvc_required": False,
    }


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    if args.verify_artifact_commit:
        result = verify_evaluation_artifact_commit(config_path=args.config, repo_root=ROOT)
        logger.info("Verified V1d B2 {}", result["evaluation"]["commit"])
    else:
        path = run_phase_b(
            config_path=args.config,
            protected_read_root=args.protected_read_root,
            repo_root=ROOT,
        )
        logger.info("Wrote {}", path)


if __name__ == "__main__":
    main()
