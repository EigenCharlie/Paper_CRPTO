"""Outcome-free set-preserving embedding frontier and paired evaluation tools."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import product
from pathlib import Path, PurePath
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml

from src.evaluation.policy_contrast_bounds import PolicyContrastIndex
from src.evaluation.standardized_credit_payoff import expected_objective_coefficients
from src.ijds_challengers.archive import monthly_frames
from src.ijds_challengers.frontier import (
    ScoreFrontierSolution,
    common_objective_target,
    normalized_exposure_distance,
)
from src.ijds_challengers.normalized_frontier import (
    _build_gamma_states,
    _independent_diagnostic,
    _order_diagnostic,
    _solve_objective_optimum,
    _solve_rulers,
)
from src.models.binary_conformal_guardrail import apply_binary_outcome_recipe

THETA_GRID = (0.0, 0.25, 0.5, 0.75, 1.0)
GAMMA_GRID = (0.0, 0.25, 0.5, 0.75, 1.0)
COORDINATE_GRID = (0.25, 0.5, 0.75)
RULERS = ("objective_matched", "normalized_score")
ROLES = ("policy_development", "primary_oot")
CONTRAST_GAMMA = "gamma_1_minus_gamma_0_within_theta"
CONTRAST_THETA = "theta_minus_theta_0_within_gamma"
OUTPUT_BASENAME_KEYS = (
    "solve_records",
    "allocations",
    "embedding_diagnostics",
    "minimum_endpoint_diagnostics",
    "objective_optimum_diagnostics",
    "allocation_contrasts",
    "order_sensitivity",
    "independent_validation",
    "outcome_free_summary",
    "outcome_free_receipt",
    "protocol_freeze",
    "evaluated_portfolios",
    "joined_funded_allocations",
    "monthly_sharp_contrasts",
    "window_sharp_contrasts",
    "metric_direction_census",
    "outcome_join_audit",
    "evaluation_summary",
    "evaluation_receipt",
    "evaluation_manifest",
)
_WINDOW_METRICS = {
    "standardized_payoff": (
        "realized_payoff_difference_lower",
        "realized_payoff_difference_upper",
    ),
    "funded_default": (
        "weighted_default_difference_lower",
        "weighted_default_difference_upper",
    ),
    "funded_binary_miscoverage": (
        "weighted_miscoverage_difference_lower",
        "weighted_miscoverage_difference_upper",
    ),
}


@dataclass(frozen=True)
class SetPreservingFrontierBuild:
    """Complete Phase-A artifacts, all constructed without outcome columns."""

    solve_records: pd.DataFrame
    allocations: pd.DataFrame
    embedding_diagnostics: pd.DataFrame
    minimum_endpoint_diagnostics: pd.DataFrame
    objective_optimum_diagnostics: pd.DataFrame
    allocation_contrasts: pd.DataFrame
    order_sensitivity: pd.DataFrame
    independent_validation: pd.DataFrame


def _strict_float_grid(values: Sequence[Any], expected: tuple[float, ...], label: str) -> None:
    observed = tuple(float(value) for value in values)
    if observed != expected:
        raise ValueError(f"{label} must equal {expected}, not {observed}.")


def _validate_output_basename(value: Any, *, key: str) -> str:
    name = str(value)
    if not name or name in {".", ".."}:
        raise ValueError(f"Output {key!r} must be a nonempty file basename.")
    if PurePath(name).name != name or "/" in name or "\\" in name:
        raise ValueError(f"Output {key!r} must not contain a directory component.")
    if name[-1] in {" ", "."}:
        raise ValueError(f"Output {key!r} cannot end in a space or period on Windows.")
    stem = name.split(".", maxsplit=1)[0].casefold()
    reserved = {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(1, 10)),
        *(f"lpt{i}" for i in range(1, 10)),
    }
    if stem in reserved:
        raise ValueError(f"Output {key!r} uses a Windows-reserved basename.")
    return name


def _validate_hash_descriptor(value: Any, *, label: str) -> None:
    """Require one exact artifact identity without resolving it yet."""
    if not isinstance(value, dict) or set(value) != {"path", "bytes", "sha256"}:
        raise ValueError(f"{label} requires path, bytes, and sha256 authority.")
    digest = str(value["sha256"])
    try:
        int(digest, 16)
    except ValueError as error:
        raise ValueError(f"{label} contains a non-hex digest.") from error
    if (
        not isinstance(value["path"], str)
        or not value["path"]
        or not isinstance(value["bytes"], int)
        or isinstance(value["bytes"], bool)
        or value["bytes"] <= 0
        or len(digest) != 64
    ):
        raise ValueError(f"{label} contains an invalid identity.")


def load_set_preserving_config(path: Path) -> dict[str, Any]:
    """Load and fail closed on every estimand-defining V1 configuration field."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Set-preserving configuration must be a YAML mapping.")
    required = {
        "schema_version",
        "protocol_tag",
        "run_tag",
        "phase_authority",
        "parent",
        "source_ingest",
        "outcomes",
        "normalization",
        "embedding",
        "frontier",
        "solver",
        "contrasts",
        "metrics",
        "expected_census",
        "claim_boundary",
        "stop_rules",
        "output",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise KeyError(f"Set-preserving configuration is missing sections: {missing}.")

    protocol_status = payload.get("protocol_status")
    allowed_statuses = {
        "locked_candidate_two_phase_before_execution",
        "locked_hash_pinned_postfreeze_evaluation",
    }
    if protocol_status not in allowed_statuses:
        raise ValueError("The set-preserving candidate has an unsupported protocol status.")
    expected_phase_authority = {
        "tag_resolution": "explicit_refs_tags_commit_only",
        "ancestry": "parent_to_v1a_to_artifact_tag_to_direct_child_v1b_required",
        "v2_delta_whitelist": [
            "schema_version",
            "protocol_status",
            "protocol_tag",
            "run_tag",
            "source_frontier",
        ],
        "v2_source_config_descriptor": ["path", "bytes", "sha256"],
        "exact_shared_implementation_bytes": True,
        "exact_environment": True,
        "candidate_identity": ("utf8_length_prefixed_json_role_period_id_sorted_mergesort_sha256"),
        "verify_source_summary_and_receipt": True,
        "require_phase_a_artifact_tag": True,
        "require_phase_a_dvc_pointer_descriptors": True,
        "clean_clone_transport_receipt": {
            "schema": "canonical_tamper_evident_reconciliation_2026_07_29_2",
            "required_in_source_frontier": True,
            "dvc_pull_required": True,
            "exact_materialized_file_census": 11,
            "post_phase_b_clean_clone_gate": True,
            "post_phase_b_materialized_file_census": 9,
            "dvc_version": "3.67.1",
            "isolated_python_module_execution": True,
        },
    }
    if payload["phase_authority"] != expected_phase_authority:
        raise ValueError("The locked V1/V2 authority contract changed.")
    source_frontier = payload.get("source_frontier")
    if protocol_status == "locked_candidate_two_phase_before_execution":
        if source_frontier is not None:
            raise ValueError("The outcome-free V1 config cannot self-authorize evaluation.")
    else:
        if not isinstance(source_frontier, dict):
            raise ValueError("Post-freeze evaluation requires a committed source_frontier.")
        if set(source_frontier) != {
            "run_tag",
            "protocol_tag",
            "protocol_commit",
            "artifact_tag",
            "artifact_commit",
            "dvc_pointers",
            "clean_clone_transport_receipt",
            "config",
            "freeze",
        }:
            raise ValueError("The post-freeze source authority fields changed.")
        _validate_hash_descriptor(source_frontier["config"], label="The source V1 config")
        _validate_hash_descriptor(source_frontier["freeze"], label="The source freeze")
        pointers = source_frontier["dvc_pointers"]
        if not isinstance(pointers, dict) or set(pointers) != {"data", "model"}:
            raise ValueError("Post-freeze evaluation requires data/model DVC pointer authority.")
        for label, descriptor in pointers.items():
            _validate_hash_descriptor(descriptor, label=f"The source {label} DVC pointer")
        _validate_hash_descriptor(
            source_frontier["clean_clone_transport_receipt"],
            label="The clean-clone Phase-A transport receipt",
        )
        protocol_commit = str(source_frontier["protocol_commit"])
        artifact_commit = str(source_frontier["artifact_commit"])
        try:
            int(protocol_commit, 16)
            int(artifact_commit, 16)
        except ValueError as error:
            raise ValueError("A source protocol/artifact commit is not hexadecimal.") from error
        if (
            not str(source_frontier["run_tag"])
            or not str(source_frontier["protocol_tag"])
            or not str(source_frontier["artifact_tag"])
            or len(protocol_commit) != 40
            or len(artifact_commit) != 40
        ):
            raise ValueError("The source freeze authority contains an invalid identity.")
    embedding = payload["embedding"]
    if (
        embedding.get("definition") != "keep_u_at_one_else_convex_combination_of_u_and_p"
        or embedding.get("binary_support") != [0, 1]
        or embedding.get("lower_endpoint") != "unchanged"
        or embedding.get("exact_set_preservation_required") is not True
    ):
        raise ValueError("The set-preserving embedding definition changed.")

    _strict_float_grid(payload["embedding"]["theta_grid"], THETA_GRID, "theta_grid")
    _strict_float_grid(payload["frontier"]["gamma_grid"], GAMMA_GRID, "gamma_grid")
    _strict_float_grid(payload["frontier"]["coordinate_grid"], COORDINATE_GRID, "coordinate_grid")
    if tuple(str(value) for value in payload["frontier"]["rulers"]) != RULERS:
        raise ValueError(f"rulers must equal {RULERS}.")
    if tuple(str(value) for value in payload["frontier"]["roles"]) != ROLES:
        raise ValueError(f"roles must equal {ROLES}.")
    frontier = payload["frontier"]
    if (
        int(frontier["expected_development_months"]) != 11
        or int(frontier["expected_primary_months"]) != 15
        or int(frontier["expected_windows"]) != 8
    ):
        raise ValueError("The locked role-month-window census changed.")
    if (
        frontier["normalized_score"].get("definition")
        != "score_min_plus_coordinate_times_score_at_objective_minus_score_min"
        or float(frontier["normalized_score"]["minimum_score_range"]) != 1.0e-4
        or float(frontier["normalized_score"]["cap_residual_tolerance"]) != 1.0e-8
        or tuple(
            float(value) for value in frontier["normalized_score"]["minimum_endpoint_retry_slacks"]
        )
        != (1.0e-10, 1.0e-9, 1.0e-8)
        or frontier["objective_matched"].get("definition")
        != "score_minimizer_subject_to_one_common_25_score_plugin_objective_floor"
        or frontier["objective_matched"].get("common_lower_endpoint")
        != "maximum_minimum_score_portfolio_objective_over_all_theta_gamma"
        or float(frontier["objective_matched"]["minimum_objective_range_dollars"]) != 1.0e-4
        or float(frontier["objective_matched"]["floor_residual_tolerance_dollars"]) != 1.0e-5
        or frontier["objective_optimum"].get("diagnostic")
        != "nonbasic_reduced_costs_plus_reversed_id_order"
        or float(frontier["objective_optimum"]["dual_tolerance"]) != 1.0e-7
        or float(frontier["objective_optimum"]["primal_tolerance"]) != 1.0e-8
    ):
        raise ValueError("A locked ruler or objective-optimum definition changed.")
    retry = frontier["normalized_score"].get("minimum_endpoint_retry_failures")
    if retry != {
        "exact_messages": [
            "Point LP is not optimal: Infeasible.",
            "Point LP is not optimal: Unknown.",
        ],
        "message_prefixes": ["Point LP did not fill its budget:"],
    }:
        raise ValueError("The closed minimum-endpoint retry taxonomy changed.")
    if tuple(str(value) for value in payload["contrasts"]["families"]) != (
        CONTRAST_GAMMA,
        CONTRAST_THETA,
    ):
        raise ValueError("Both locked contrast families must be retained in order.")
    if tuple(float(value) for value in payload["contrasts"]["gamma_endpoints"]) != (
        1.0,
        0.0,
    ):
        raise ValueError("The gamma endpoint contrast must be 1 minus 0.")
    if float(payload["contrasts"]["theta_reference"]) != 0.0:
        raise ValueError("The theta reference must be zero.")
    if float(payload["contrasts"]["negative_control_gamma"]) != 0.0:
        raise ValueError("The negative-control gamma must be zero.")
    contrasts = payload["contrasts"]
    if (
        contrasts.get("common_outcome_assignment") != "loanwise_sharp_on_funded_union"
        or contrasts.get("window_aggregation") != "pool_15_month_numerators_before_rates"
        or float(contrasts["expected_objective_negative_control_tolerance_dollars"]) != 1.0e-8
        or float(contrasts["payoff_negative_control_tolerance_dollars"]) != 1.0e-8
        or float(contrasts["rate_negative_control_tolerance"]) != 1.0e-12
    ):
        raise ValueError("The common-outcome or temporal aggregation estimand changed.")

    expected_parent = {
        "config": "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-12.yaml",
        "protocol": "docs/research/ijds_binary_geometry_frontier_v4_protocol_2026-07-12.md",
        "run_tag": "ijds-binary-geometry-frontier-v4-2026-07-12-v1",
        "protocol_tag": "protocol/ijds-binary-geometry-frontier-v4-2026-07-12-v1",
        "protocol_commit": "2f8a7606e4eb65aa3ae3701fb3af8d9a51c953cd",
        "protocol_freeze": {
            "path": (
                "models/experiments/ijds_audit/"
                "ijds-binary-geometry-frontier-v4-2026-07-12-v1/protocol_freeze.json"
            ),
            "bytes": 20_362,
            "sha256": "c2b3dc2d18c9fed80708682d5a0369c80c89643e2d28024418522d954ebe667c",
        },
    }
    if payload["parent"] != expected_parent:
        raise ValueError("The hash-pinned outcome-free parent authority changed.")

    source = payload["source_ingest"]
    if source.get("allowed_raw_columns") != [
        "id",
        "loan_amnt",
        "int_rate",
        "purpose",
    ] or source.get("forbidden_tokens") != [
        "status",
        "outcome",
        "default",
        "pymnt",
        "realized",
        "miscoverage",
    ]:
        raise ValueError("The outcome-free raw-column allowlist changed.")
    tokens = tuple(str(token).casefold() for token in source["forbidden_tokens"])
    if any(
        token in str(column).casefold()
        for column in source["allowed_raw_columns"]
        for token in tokens
    ):
        raise ValueError("The outcome-free raw-column allowlist contains an outcome token.")
    if (
        source.get("raw_path") != "data/raw/Loan_status_2007-2020Q3.csv"
        or source.get("raw_sha256")
        != "5878af2a088f8ab5214c9337289fb8b5eb6c6338fd3f417b6cdc18513dc6f35f"
        or int(source.get("chunksize", 0)) != 100_000
        or source.get("retained_decision_columns")
        != [
            "id",
            "issue_d",
            "design_split",
            "pd_point",
            "loan_amnt",
            "purpose",
            "contractual_rate",
        ]
        or source.get("discarded_coverage_control_columns") != []
    ):
        raise ValueError("The primary-only decision-score schema changed.")
    outcomes = payload["outcomes"]
    if (
        outcomes.get("parent_config")
        != "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-15_v5.yaml"
        or outcomes.get("raw_path") != source["raw_path"]
        or outcomes.get("raw_sha256") != source["raw_sha256"]
        or outcomes.get("evaluated_role") != "primary_oot"
        or outcomes.get("endpoint") != "terminal_default_reconstructed_as_observable_by_2020-09-30"
        or outcomes.get("joined_columns")
        != [
            "snapshot_default",
            "snapshot_resolution",
        ]
    ):
        raise ValueError("Only the locked primary endpoint columns may be evaluated.")
    normalization = payload["normalization"]
    expected_normalization = {
        "capital_source": "parent_policy_budget",
        "committed_budget_per_period": 1_000_000.0,
        "monthly": "parent_committed_budget",
        "pooled": "period_count_times_parent_committed_budget",
        "common_across_policies": True,
        "solver_allocated_capital_renormalization": "forbidden",
    }
    if normalization != expected_normalization:
        raise ValueError("The common-capital rate-normalization estimand changed.")

    solver = payload["solver"]
    independent = solver["independent_validation"]
    if (
        solver.get("primary") != "highspy_exact_budget_simplex"
        or int(solver["threads"]) != 1
        or int(solver["time_limit_seconds"]) != 300
        or float(solver["allocation_tolerance"]) != 1.0e-8
        or float(solver["allocation_reconciliation_tolerance_dollars"]) != 1.0e-8
        or float(solver["weight_reconciliation_tolerance"]) != 1.0e-12
        or float(solver["contribution_reconciliation_tolerance_dollars"]) != 1.0e-8
        or float(solver["budget_residual_tolerance_dollars"]) != 1.0e-4
        or solver.get("order_rule") != "ascending_id_vs_descending_id"
        or solver.get("order_audit_scope") != "all_25_primary_cells_all_rulers_coordinates"
        or float(solver["order_exposure_distance_tolerance"]) != 1.0e-10
        or float(solver["order_objective_tolerance_dollars"]) != 1.0e-5
        or float(solver["negative_control_exposure_distance_tolerance"]) != 1.0e-12
        or float(solver["negative_control_objective_tolerance_dollars"]) != 1.0e-8
        or float(solver["negative_control_score_tolerance"]) != 1.0e-12
        or independent.get("solver") != "ortools_glop"
        or independent.get("periods") != ["2016-04", "2016-11", "2017-06"]
        or independent.get("scope") != "all_25_cells_all_windows_rulers_coordinates"
        or float(independent["objective_rate_tolerance"]) != 1.0e-7
        or float(independent["weighted_score_tolerance"]) != 1.0e-7
    ):
        raise ValueError("The complete deterministic numerical-audit contract changed.")
    positive_tolerances = (
        solver["allocation_tolerance"],
        solver["allocation_reconciliation_tolerance_dollars"],
        solver["weight_reconciliation_tolerance"],
        solver["contribution_reconciliation_tolerance_dollars"],
        solver["budget_residual_tolerance_dollars"],
        solver["order_exposure_distance_tolerance"],
        solver["order_objective_tolerance_dollars"],
        solver["negative_control_exposure_distance_tolerance"],
        solver["negative_control_objective_tolerance_dollars"],
        solver["negative_control_score_tolerance"],
        independent["objective_rate_tolerance"],
        independent["weighted_score_tolerance"],
        contrasts["expected_objective_negative_control_tolerance_dollars"],
        contrasts["payoff_negative_control_tolerance_dollars"],
        contrasts["rate_negative_control_tolerance"],
    )
    if any(float(value) <= 0.0 for value in positive_tolerances):
        raise ValueError("Every numerical tolerance must be positive.")
    expected_metrics = {
        "standardized_payoff": (
            "realized_payoff_difference_lower",
            "realized_payoff_difference_upper",
            1.0e-4,
        ),
        "funded_default": (
            "weighted_default_difference_lower",
            "weighted_default_difference_upper",
            1.0e-10,
        ),
        "funded_binary_miscoverage": (
            "weighted_miscoverage_difference_lower",
            "weighted_miscoverage_difference_upper",
            1.0e-10,
        ),
    }
    metrics = payload["metrics"]
    observed_metrics = {
        name: (
            str(metrics[name]["lower"]),
            str(metrics[name]["upper"]),
            float(metrics[name]["direction_tolerance"]),
        )
        for name in expected_metrics
    }
    if observed_metrics != expected_metrics or set(metrics) != set(expected_metrics):
        raise ValueError("The locked per-metric direction contract changed.")

    output = payload["output"]
    if set(output) != {"data_root", "model_root", "immutability", *OUTPUT_BASENAME_KEYS}:
        raise ValueError("The locked output artifact schema changed.")
    names = [_validate_output_basename(output[key], key=key) for key in OUTPUT_BASENAME_KEYS]
    folded = [name.casefold() for name in names]
    if len(folded) != len(set(folded)):
        raise ValueError("Output basenames must be case-insensitively unique.")

    expected = {
        "frontier_solves": 31_200,
        "embedding_diagnostics": 80,
        "minimum_score_endpoints": 5_200,
        "objective_optima": 26,
        "order_replays": 18_000,
        "independent_solver_cells": 3_600,
        "outcome_free_allocation_contrasts": 18_000,
        "outcome_free_negative_controls": 2_880,
        "primary_evaluated_portfolios": 18_000,
        "monthly_sharp_contrasts": 18_000,
        "monthly_negative_controls": 2_880,
        "window_sharp_contrasts": 1_200,
        "window_negative_controls": 192,
        "direction_rows": 3_600,
    }
    observed = {key: int(payload["expected_census"][key]) for key in expected}
    if observed != expected or set(payload["expected_census"]) != set(expected):
        raise ValueError(f"Expected census is not the locked complete grid: {observed}.")
    claim_keys = {
        "no_policy_selection",
        "no_window_selection",
        "no_ruler_selection",
        "no_coordinate_selection",
        "no_gamma_selection",
        "no_theta_selection",
        "no_policy_winner",
        "no_causal_claim",
        "no_conformal_guarantee_repair",
        "no_selected_set_validity",
        "no_submission_freeze",
    }
    if payload["claim_boundary"] != dict.fromkeys(claim_keys, True):
        raise ValueError("Every no-selection/no-overclaim boundary must remain true.")
    stop_keys = {
        "stop_on_occupied_output",
        "stop_on_parent_descriptor_mismatch",
        "stop_on_outcome_like_decision_column",
        "stop_on_set_preservation_failure",
        "stop_on_incomplete_cell",
        "stop_on_score_range_failure",
        "stop_on_objective_range_failure",
        "stop_on_objective_optimum_tie",
        "stop_on_budget_failure",
        "stop_on_order_sensitivity",
        "stop_on_independent_solver_mismatch",
        "stop_on_negative_control_failure",
        "stop_on_freeze_or_artifact_mismatch",
        "stop_on_v1_v2_authority_mismatch",
        "stop_on_environment_drift",
        "stop_on_candidate_identity_mismatch",
        "stop_on_outcome_alignment_failure",
        "stop_on_incomplete_contrast_census",
        "stop_on_invalid_sharp_bounds",
        "retain_all_predeclared_results",
    }
    if payload["stop_rules"] != dict.fromkeys(stop_keys, True):
        raise ValueError("Every fail-closed stop rule must remain enabled.")
    if (
        output.get("immutability") != "hard_no_overwrite_choose_fresh_run_tag"
        or output.get("data_root") != "data/processed/experiments/ijds_audit"
        or output.get("model_root") != "models/experiments/ijds_audit"
    ):
        raise ValueError("Set-preserving outputs must remain immutable.")
    return payload


def _probability_vector(values: np.ndarray, *, label: str) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if result.ndim != 1 or not bool(np.isfinite(result).all()):
        raise ValueError(f"{label} must be one finite one-dimensional probability vector.")
    if bool(((result < 0.0) | (result > 1.0)).any()):
        raise ValueError(f"{label} must lie in [0,1].")
    return result


def set_preserving_upper(
    point: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    *,
    theta: float,
) -> np.ndarray:
    """Return the locked numeric embedding while preserving the binary set exactly."""
    point_values = _probability_vector(point, label="point")
    lower_values = _probability_vector(lower, label="lower")
    upper_values = _probability_vector(upper, label="upper")
    if not (len(point_values) == len(lower_values) == len(upper_values)):
        raise ValueError("Point, lower, and upper vectors must have equal length.")
    theta_value = float(theta)
    if theta_value not in THETA_GRID:
        raise ValueError(f"theta must be one of {THETA_GRID}.")
    if bool((lower_values > point_values).any()) or bool((point_values > upper_values).any()):
        raise ValueError("The original interval must satisfy lower <= point <= upper loan-wise.")

    includes_one = upper_values == 1.0
    if theta_value == 0.0:
        embedded = upper_values.copy()
    elif theta_value == 1.0:
        embedded = np.where(includes_one, 1.0, point_values)
    else:
        contracted = point_values + (1.0 - theta_value) * (upper_values - point_values)
        embedded = np.where(includes_one, 1.0, contracted)

    ordinary = ~includes_one
    if bool((embedded[ordinary] < point_values[ordinary]).any()):
        raise RuntimeError("Set-preserving embedding fell below the point score.")
    if bool((embedded[ordinary] > upper_values[ordinary]).any()):
        raise RuntimeError("Set-preserving embedding exceeded the original upper endpoint.")
    if bool((embedded[ordinary] >= 1.0).any()):
        raise RuntimeError("An embedding acquired binary label 1 outside the original set.")
    if bool((embedded[includes_one] != 1.0).any()):
        raise RuntimeError("An embedding removed binary label 1 from the original set.")

    original_sets = (lower_values == 0.0).astype(np.int8) + 2 * includes_one.astype(np.int8)
    embedded_sets = (lower_values == 0.0).astype(np.int8) + 2 * (embedded == 1.0).astype(np.int8)
    if not np.array_equal(original_sets, embedded_sets):
        raise RuntimeError("The alternative numeric embedding changed a binary prediction set.")
    return embedded


def embedding_diagnostics(
    point: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    *,
    theta: float,
) -> dict[str, Any]:
    """Validate and summarize one complete loan-wise embedding vector."""
    embedded = set_preserving_upper(point, lower, upper, theta=theta)
    lower_values = np.asarray(lower, dtype=float)
    upper_values = np.asarray(upper, dtype=float)
    original_code = (lower_values == 0.0).astype(np.int8) + 2 * (upper_values == 1.0)
    embedded_code = (lower_values == 0.0).astype(np.int8) + 2 * (embedded == 1.0)
    return {
        "theta": float(theta),
        "loans": int(len(embedded)),
        "sets_changed": int(np.count_nonzero(original_code != embedded_code)),
        "includes_zero": int(np.count_nonzero(lower_values == 0.0)),
        "includes_one": int(np.count_nonzero(upper_values == 1.0)),
        "excludes_one": int(np.count_nonzero(upper_values < 1.0)),
        "positive_upper_contractions": int(np.count_nonzero(upper_values > embedded)),
        "empty_set": int(np.count_nonzero(original_code == 0)),
        "singleton_zero": int(np.count_nonzero(original_code == 1)),
        "singleton_one": int(np.count_nonzero(original_code == 2)),
        "doubleton": int(np.count_nonzero(original_code == 3)),
        "maximum_upper_contraction": float(np.max(upper_values - embedded, initial=0.0)),
        "maximum_theta_zero_recovery_error": (
            float(np.max(np.abs(upper_values - embedded), initial=0.0))
            if float(theta) == 0.0
            else 0.0
        ),
    }


def policy_label(ruler: str, theta: float, gamma: float, coordinate: float) -> str:
    """Return one collision-free label for the complete four-dimensional grid."""
    if ruler not in RULERS:
        raise ValueError(f"Unknown ruler {ruler!r}.")
    return (
        f"{ruler}_t{round(theta * 100):03d}_g{round(gamma * 100):03d}_"
        f"c{round(coordinate * 100):03d}"
    )


def common_25_score_objective_lower(
    states: Mapping[tuple[float, float], Any],
    *,
    objective_optimum: float,
    minimum_range: float,
) -> float:
    """Return the one locked objective lower endpoint over all theta-gamma scores."""
    expected_keys = {(theta, gamma) for theta in THETA_GRID for gamma in GAMMA_GRID}
    if set(states) != expected_keys:
        missing = sorted(expected_keys - set(states))
        extra = sorted(set(states) - expected_keys)
        raise ValueError(
            f"The global objective ruler requires all 25 scores: {missing=}, {extra=}."
        )
    lower, _ = common_objective_target(
        minimum_objectives=[float(state.minimum_objective) for state in states.values()],
        objective_optimum=float(objective_optimum),
        coordinate=0.0,
        minimum_range=float(minimum_range),
    )
    return float(lower)


def _assert_outcome_free(frame: pd.DataFrame, *, config: Mapping[str, Any]) -> None:
    tokens = tuple(str(value).casefold() for value in config["source_ingest"]["forbidden_tokens"])
    forbidden = [
        str(column)
        for column in frame.columns
        if any(token in str(column).casefold() for token in tokens)
    ]
    if forbidden:
        raise ValueError(f"Outcome-like columns reached frontier construction: {forbidden}.")


def retain_primary_decision_inputs(
    frame: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Reject every residual learner score and retain one exact primary schema."""
    source = config["source_ingest"]
    retained = [str(value) for value in source["retained_decision_columns"]]
    discarded = [str(value) for value in source["discarded_coverage_control_columns"]]
    expected = set(retained) | set(discarded)
    missing = sorted(expected - set(frame.columns))
    extra = sorted(set(frame.columns) - expected)
    if missing or extra:
        raise RuntimeError(
            f"Outcome-free decision schema drifted before the primary-only scrub: "
            f"{missing=}, {extra=}."
        )
    result = frame.loc[:, retained].copy()
    if any(column != "pd_point" and column.startswith("pd_") for column in result.columns):
        raise RuntimeError("A learner-control score survived the primary-only scrub.")
    return result


def _append_solution(
    records: list[dict[str, Any]],
    allocations: list[pd.DataFrame],
    *,
    month: pd.DataFrame,
    original_upper: np.ndarray,
    embedded_upper: np.ndarray,
    score: np.ndarray,
    objective: np.ndarray,
    solution: ScoreFrontierSolution,
    state: Any,
    window_id: str,
    role: str,
    period: str,
    theta: float,
    gamma: float,
    ruler: str,
    coordinate: float,
    cap: float | None,
    objective_target: float | None,
    common_objective_lower: float,
    unconstrained_objective: float,
    allocation_tolerance: float,
    budget: float,
) -> None:
    label = policy_label(ruler, theta, gamma, coordinate)
    if cap is not None:
        constraint_slack = float(cap - solution.weighted_score)
    elif objective_target is not None:
        constraint_slack = float(solution.objective_value - objective_target)
    else:
        raise ValueError("A frontier solution requires a score cap or objective target.")
    if bool((solution.exposure < 0.0).any()):
        raise RuntimeError("A solver returned a negative exposure.")
    # Every strictly positive exposure is part of the scientific allocation.
    # The reporting tolerance is diagnostic only and never truncates support.
    active = solution.exposure > 0.0
    above_reporting_tolerance = solution.exposure > float(allocation_tolerance)
    funded = month.loc[active].copy()
    funded["allocation_fraction"] = solution.allocation_fraction[active]
    funded["exposure"] = solution.exposure[active]
    funded["weight"] = funded["exposure"] / solution.total_allocated
    funded["embedding_upper"] = embedded_upper[active]
    funded["pd_effective"] = score[active]
    funded["expected_payoff_rate"] = objective[active]
    funded["expected_payoff_contribution"] = funded["exposure"] * objective[active]
    metadata = {
        "window_id": str(window_id),
        "role": str(role),
        "period": str(period),
        "policy_label": label,
        "candidate_id": label,
        "comparator_rule": str(ruler),
        "paired_policy_id": label,
        "frontier_ruler": str(ruler),
        "frontier_coordinate": float(coordinate),
        "frontier_cap": np.nan if cap is None else float(cap),
        "objective_target": np.nan if objective_target is None else float(objective_target),
        "theta": float(theta),
        "gamma": float(gamma),
    }
    allocations.append(funded.assign(**metadata))
    records.append(
        {
            **metadata,
            "risk_tolerance": np.nan if cap is None else float(cap),
            "uncertainty_aversion": float(gamma),
            "embedding_contraction": float(theta),
            "policy_mode": str(ruler),
            "robust_guardrail": bool(gamma > 0.0),
            "solver_status": "Optimal",
            "solver_backend_actual": "highspy_exact_budget_simplex",
            "expected_objective": float(solution.objective_value),
            "n_candidates": int(len(month)),
            "n_positive_exposure": int(active.sum()),
            "n_exposure_above_reporting_tolerance": int(above_reporting_tolerance.sum()),
            "total_allocated": float(solution.total_allocated),
            "budget_residual": float(solution.total_allocated - budget),
            "weighted_pd_point": float(
                solution.exposure @ month["pd_point"] / solution.total_allocated
            ),
            "weighted_pd_effective": float(solution.weighted_score),
            "weighted_conformal_upper": float(
                solution.exposure @ original_upper / solution.total_allocated
            ),
            "weighted_embedding_upper": float(
                solution.exposure @ embedded_upper / solution.total_allocated
            ),
            "minimum_score": float(state.minimum_score),
            "score_at_objective": float(state.score_at_objective),
            "score_range": float(state.score_range),
            "minimum_score_portfolio_objective": float(state.minimum_objective),
            "common_objective_lower": float(common_objective_lower),
            "unconstrained_objective": float(unconstrained_objective),
            "objective_retention": float(
                (solution.objective_value - common_objective_lower)
                / (unconstrained_objective - common_objective_lower)
            ),
            "constraint_slack": constraint_slack,
            "highs_simplex_iterations": int(solution.simplex_iterations),
        }
    )


def _allocation_contrast(
    solution_a: ScoreFrontierSolution,
    solution_b: ScoreFrontierSolution,
    *,
    family: str,
    window_id: str,
    period: str,
    ruler: str,
    coordinate: float,
    theta: float,
    theta_reference: float,
    gamma: float,
    gamma_reference: float,
    point: np.ndarray,
    budget: float,
) -> dict[str, Any]:
    return {
        "window_id": str(window_id),
        "role": "primary_oot",
        "period": str(period),
        "contrast_family": str(family),
        "ruler": str(ruler),
        "coordinate": float(coordinate),
        "theta": float(theta),
        "theta_reference": float(theta_reference),
        "gamma": float(gamma),
        "gamma_reference": float(gamma_reference),
        "policy_a": policy_label(ruler, theta, gamma, coordinate),
        "policy_b": policy_label(ruler, theta_reference, gamma_reference, coordinate),
        "normalized_exposure_distance": normalized_exposure_distance(
            solution_a.exposure, solution_b.exposure, budget=budget
        ),
        "objective_difference": float(solution_a.objective_value - solution_b.objective_value),
        "weighted_score_difference": float(solution_a.weighted_score - solution_b.weighted_score),
        "point_moment_difference": float(
            (solution_a.exposure - solution_b.exposure) @ point / budget
        ),
    }


def build_set_preserving_frontiers(
    base: pd.DataFrame,
    recipes: Mapping[str, Mapping[str, Mapping[int, Any]]],
    *,
    config: Mapping[str, Any],
    parent_config: Mapping[str, Any],
) -> SetPreservingFrontierBuild:
    """Solve and audit the complete 25-score family without accepting outcomes."""
    _assert_outcome_free(base, config=config)
    base = retain_primary_decision_inputs(base, config=config)
    frontier = config["frontier"]
    solver = config["solver"]
    budget = float(parent_config["policy"]["budget"])
    purpose_cap = float(parent_config["policy"]["max_concentration_by_purpose"])
    lgd = float(parent_config["payoff"]["lgd"])
    threads = int(solver["threads"])
    time_limit = int(solver["time_limit_seconds"])
    allocation_tolerance = float(solver["allocation_tolerance"])
    validation_periods = {str(value) for value in solver["independent_validation"]["periods"]}

    records: list[dict[str, Any]] = []
    allocations: list[pd.DataFrame] = []
    embedding_rows: list[dict[str, Any]] = []
    minimum_rows: list[dict[str, Any]] = []
    optimum_rows: list[dict[str, Any]] = []
    contrast_rows: list[dict[str, Any]] = []
    order_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    objective_cache: dict[tuple[str, str], Any] = {}

    windows = recipes["catboost_platt"]
    if len(windows) != int(frontier["expected_windows"]):
        raise RuntimeError("The calibration-window census changed before the embedding run.")
    for window_id, group_recipes in sorted(windows.items()):
        point_all = base["pd_point"].to_numpy(dtype=float)
        groups, lower_all, upper_all = apply_binary_outcome_recipe(point_all, group_recipes[5])
        window_base = base.assign(
            conformal_group=groups,
            conformal_lower=lower_all,
            conformal_upper=upper_all,
        )
        for role in ROLES:
            role_frame = window_base.loc[window_base["design_split"].eq(role)]
            for theta in THETA_GRID:
                diagnostic = embedding_diagnostics(
                    role_frame["pd_point"].to_numpy(dtype=float),
                    role_frame["conformal_lower"].to_numpy(dtype=float),
                    role_frame["conformal_upper"].to_numpy(dtype=float),
                    theta=theta,
                )
                embedding_rows.append({"window_id": str(window_id), "role": role, **diagnostic})

            monthly = monthly_frames(window_base, role)
            expected_months = int(
                frontier[
                    "expected_development_months"
                    if role == "policy_development"
                    else "expected_primary_months"
                ]
            )
            if len(monthly) != expected_months:
                raise RuntimeError(
                    f"{window_id} {role} has {len(monthly)} months, not {expected_months}."
                )
            for period, month in monthly:
                point = month["pd_point"].to_numpy(dtype=float)
                lower = month["conformal_lower"].to_numpy(dtype=float)
                original_upper = month["conformal_upper"].to_numpy(dtype=float)
                rates = month["contractual_rate"].to_numpy(dtype=float)
                objective = expected_objective_coefficients(point, rates, lgd=lgd)
                cache_key = (role, period)
                optimum = objective_cache.get(cache_key)
                if optimum is None:
                    optimum = _solve_objective_optimum(
                        month,
                        point_score=point,
                        objective_rate=objective,
                        budget=budget,
                        purpose_cap=purpose_cap,
                        time_limit=time_limit,
                        threads=threads,
                        role=role,
                        period=period,
                        optimum_config=frontier["objective_optimum"],
                        solver_config=solver,
                    )
                    objective_cache[cache_key] = optimum
                    optimum_rows.append(optimum.diagnostics)

                states: dict[tuple[float, float], Any] = {}
                embedded_by_theta: dict[float, np.ndarray] = {}
                for theta in THETA_GRID:
                    embedded = set_preserving_upper(point, lower, original_upper, theta=theta)
                    embedded_by_theta[theta] = embedded
                    gamma_states = _build_gamma_states(
                        month,
                        point=point,
                        upper=embedded,
                        objective=objective,
                        unconstrained=optimum.solution,
                        gamma_grid=GAMMA_GRID,
                        window_id=str(window_id),
                        role=role,
                        period=period,
                        budget=budget,
                        purpose_cap=purpose_cap,
                        time_limit=time_limit,
                        threads=threads,
                        normalized_config=frontier["normalized_score"],
                    )
                    for gamma, state in gamma_states.items():
                        states[(theta, gamma)] = state
                        minimum_rows.append(
                            {
                                "window_id": str(window_id),
                                "role": role,
                                "period": period,
                                "theta": theta,
                                "gamma": gamma,
                                "minimum_score": float(state.minimum_score),
                                "minimum_objective": float(state.minimum_objective),
                                "minimum_cap_residual": float(state.minimum_cap_residual),
                                "minimum_endpoint_retry_slack": float(
                                    state.minimum_endpoint_retry_slack
                                ),
                            }
                        )

                common_lower = common_25_score_objective_lower(
                    states,
                    objective_optimum=optimum.solution.objective_value,
                    minimum_range=float(
                        frontier["objective_matched"]["minimum_objective_range_dollars"]
                    ),
                )
                solutions: dict[tuple[str, float, float, float], ScoreFrontierSolution] = {}
                for (theta, gamma), state in sorted(states.items()):
                    for coordinate in COORDINATE_GRID:
                        solved_rulers = _solve_rulers(
                            state,
                            # The inherited helper reads only Mapping.values(); the tuple
                            # keys retain the full theta-gamma identity in this extension.
                            gamma_states=cast(Mapping[float, Any], states),
                            coordinate=coordinate,
                            unconstrained_objective=optimum.solution.objective_value,
                            window_id=str(window_id),
                            role=role,
                            period=period,
                            gamma=gamma,
                            normalized_config=frontier["normalized_score"],
                            objective_config=frontier["objective_matched"],
                        )
                        for solved in solved_rulers:
                            solutions[(solved.ruler, theta, gamma, coordinate)] = solved.solution
                            _append_solution(
                                records,
                                allocations,
                                month=month,
                                original_upper=original_upper,
                                embedded_upper=embedded_by_theta[theta],
                                score=state.score,
                                objective=objective,
                                solution=solved.solution,
                                state=state,
                                window_id=str(window_id),
                                role=role,
                                period=period,
                                theta=theta,
                                gamma=gamma,
                                ruler=solved.ruler,
                                coordinate=coordinate,
                                cap=solved.cap,
                                objective_target=solved.objective_target,
                                common_objective_lower=common_lower,
                                unconstrained_objective=optimum.solution.objective_value,
                                allocation_tolerance=allocation_tolerance,
                                budget=budget,
                            )
                            if role == "primary_oot":
                                order = _order_diagnostic(
                                    month,
                                    score=state.score,
                                    objective=objective,
                                    original=solved.solution,
                                    window_id=str(window_id),
                                    role=role,
                                    period=period,
                                    gamma=gamma,
                                    ruler=solved.ruler,
                                    coordinate=coordinate,
                                    threshold=solved.threshold,
                                    budget=budget,
                                    purpose_cap=purpose_cap,
                                    time_limit=time_limit,
                                    threads=threads,
                                )
                                order_rows.append({"theta": theta, **order})
                                if period in validation_periods:
                                    validation = _independent_diagnostic(
                                        month,
                                        score=state.score,
                                        objective=objective,
                                        original=solved.solution,
                                        window_id=str(window_id),
                                        role=role,
                                        period=period,
                                        gamma=gamma,
                                        ruler=solved.ruler,
                                        coordinate=coordinate,
                                        threshold=solved.threshold,
                                        budget=budget,
                                        purpose_cap=purpose_cap,
                                    )
                                    validation_rows.append({"theta": theta, **validation})

                if role == "primary_oot":
                    for ruler in RULERS:
                        for coordinate in COORDINATE_GRID:
                            for theta in THETA_GRID:
                                contrast_rows.append(
                                    _allocation_contrast(
                                        solutions[(ruler, theta, 1.0, coordinate)],
                                        solutions[(ruler, theta, 0.0, coordinate)],
                                        family=CONTRAST_GAMMA,
                                        window_id=str(window_id),
                                        period=period,
                                        ruler=ruler,
                                        coordinate=coordinate,
                                        theta=theta,
                                        theta_reference=theta,
                                        gamma=1.0,
                                        gamma_reference=0.0,
                                        point=point,
                                        budget=budget,
                                    )
                                )
                            for theta in THETA_GRID[1:]:
                                for gamma in GAMMA_GRID:
                                    contrast_rows.append(
                                        _allocation_contrast(
                                            solutions[(ruler, theta, gamma, coordinate)],
                                            solutions[(ruler, 0.0, gamma, coordinate)],
                                            family=CONTRAST_THETA,
                                            window_id=str(window_id),
                                            period=period,
                                            ruler=ruler,
                                            coordinate=coordinate,
                                            theta=theta,
                                            theta_reference=0.0,
                                            gamma=gamma,
                                            gamma_reference=gamma,
                                            point=point,
                                            budget=budget,
                                        )
                                    )

    build = SetPreservingFrontierBuild(
        solve_records=pd.DataFrame(records),
        allocations=pd.concat(allocations, ignore_index=True),
        embedding_diagnostics=pd.DataFrame(embedding_rows),
        minimum_endpoint_diagnostics=pd.DataFrame(minimum_rows),
        objective_optimum_diagnostics=pd.DataFrame(optimum_rows),
        allocation_contrasts=pd.DataFrame(contrast_rows),
        order_sensitivity=pd.DataFrame(order_rows),
        independent_validation=pd.DataFrame(validation_rows),
    )
    validate_complete_frontier(build, config=config, budget=budget)
    return build


def validate_complete_frontier(
    build: SetPreservingFrontierBuild,
    *,
    config: Mapping[str, Any],
    budget: float,
) -> None:
    """Fail closed on census, grid, set, budget, and numerical reconciliation."""
    expected = config["expected_census"]
    census_frames = {
        "frontier_solves": build.solve_records,
        "embedding_diagnostics": build.embedding_diagnostics,
        "minimum_score_endpoints": build.minimum_endpoint_diagnostics,
        "objective_optima": build.objective_optimum_diagnostics,
        "order_replays": build.order_sensitivity,
        "independent_solver_cells": build.independent_validation,
        "outcome_free_allocation_contrasts": build.allocation_contrasts,
    }
    for key, frame in census_frames.items():
        if len(frame) != int(expected[key]):
            raise RuntimeError(f"{key} census is {len(frame)}, not {expected[key]}.")
    numerical_frames = {**census_frames, "allocations": build.allocations}
    structural_not_applicable = {
        "frontier_solves": {"frontier_cap", "objective_target", "risk_tolerance"},
        "allocations": {"frontier_cap", "objective_target"},
    }
    for key, frame in numerical_frames.items():
        numeric = frame.select_dtypes(include=[np.number])
        checked = numeric.drop(
            columns=list(structural_not_applicable.get(key, set())), errors="ignore"
        )
        try:
            finite = np.isfinite(checked.to_numpy(dtype=float)).all()
        except (TypeError, ValueError) as error:
            raise RuntimeError(
                f"{key} contains a non-numeric value in a numeric column."
            ) from error
        if not bool(finite):
            raise RuntimeError(f"{key} contains a non-finite numerical value.")
    for key, frame, nullable in (
        (
            "frontier_solves",
            build.solve_records,
            ("frontier_cap", "objective_target", "risk_tolerance"),
        ),
        ("allocations", build.allocations, ("frontier_cap", "objective_target")),
    ):
        required = {"frontier_ruler", *nullable}
        if not required.issubset(frame):
            raise RuntimeError(f"{key} omits its explicit ruler/nullability contract.")
        ruler = frame["frontier_ruler"].astype(str)
        objective = ruler.eq("objective_matched")
        normalized = ruler.eq("normalized_score")
        if not bool((objective | normalized).all()):
            raise RuntimeError(f"{key} contains an unknown frontier ruler.")
        for column in nullable:
            values = frame[column].to_numpy(dtype=float)
            if bool(np.isinf(values).any()):
                raise RuntimeError(f"{key}.{column} contains an infinite value.")
            applicable = normalized if column != "objective_target" else objective
            if not bool(np.isfinite(values[applicable]).all()) or not bool(
                np.isnan(values[~applicable]).all()
            ):
                raise RuntimeError(
                    f"{key}.{column} violates the exact ruler-specific not-applicable pattern."
                )
    optimum = build.objective_optimum_diagnostics
    if (
        "basis_valid" not in optimum
        or not pd.api.types.is_bool_dtype(optimum["basis_valid"])
        or not bool(optimum["basis_valid"].all())
    ):
        raise RuntimeError("An objective-optimum point basis is absent or invalid.")
    records = build.solve_records
    key_columns = ["window_id", "role", "period", "policy_label", "comparator_rule"]
    if bool(records.duplicated(key_columns).any()):
        raise RuntimeError("Frontier solve-record identity is not unique.")
    grid_columns = ["theta", "gamma", "frontier_coordinate", "frontier_ruler"]
    expected_grid = {
        (theta, gamma, coordinate, ruler)
        for theta, gamma, coordinate, ruler in product(
            THETA_GRID, GAMMA_GRID, COORDINATE_GRID, RULERS
        )
    }
    observed_grid = set(records[grid_columns].itertuples(index=False, name=None))
    if observed_grid != expected_grid:
        raise RuntimeError("The frontier does not contain the exact locked 150-policy grid.")
    group_size = records.groupby(["window_id", "role", "period"], observed=True).size()
    if not bool(group_size.eq(25 * 3 * 2).all()):
        raise RuntimeError("A role-month-window does not contain all 150 frontier cells.")
    group_grid = records.groupby(["window_id", "role", "period"], observed=True)[
        grid_columns
    ].apply(lambda frame: len(frame.drop_duplicates()))
    if not bool(group_grid.eq(len(expected_grid)).all()):
        raise RuntimeError("A role-month-window duplicates or omits a locked policy cell.")
    common_lower_counts = records.groupby(["window_id", "role", "period"], observed=True)[
        "common_objective_lower"
    ].nunique(dropna=False)
    if not bool(common_lower_counts.eq(1).all()):
        raise RuntimeError("Objective-matched cells do not share one global 25-score z_L.")
    budget_tolerance = float(config["solver"]["budget_residual_tolerance_dollars"])
    if float(records["budget_residual"].abs().max()) > budget_tolerance:
        raise RuntimeError("A frontier budget residual exceeded its locked tolerance.")
    if not np.isclose(
        records["total_allocated"].to_numpy(dtype=float),
        float(budget),
        atol=budget_tolerance,
        rtol=0.0,
    ).all():
        raise RuntimeError("A frontier cell failed the exact-budget contract.")
    diagnostics = build.embedding_diagnostics
    if bool(diagnostics.duplicated(["window_id", "role", "theta"]).any()):
        raise RuntimeError("Embedding diagnostics duplicate a window-role-theta cell.")
    if int(diagnostics["sets_changed"].sum()) != 0:
        raise RuntimeError("At least one binary prediction set changed under the embedding.")
    theta_zero = diagnostics["theta"].eq(0.0)
    if float(diagnostics.loc[theta_zero, "maximum_theta_zero_recovery_error"].max()) != 0.0:
        raise RuntimeError("theta=0 did not recover the original upper endpoint exactly.")

    minimum = build.minimum_endpoint_diagnostics
    if bool(minimum.duplicated(["window_id", "role", "period", "theta", "gamma"]).any()):
        raise RuntimeError("Minimum-score endpoint identity is not unique.")
    lower_keys = ["window_id", "role", "period"]
    recomputed_lower = (
        minimum.groupby(lower_keys, observed=True)["minimum_objective"]
        .max()
        .rename("recomputed_common_objective_lower")
        .reset_index()
    )
    recorded_lower = records[[*lower_keys, "common_objective_lower"]].drop_duplicates()
    lower_audit = recorded_lower.merge(
        recomputed_lower,
        on=lower_keys,
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not bool(lower_audit["_merge"].eq("both").all()) or not np.array_equal(
        lower_audit["common_objective_lower"].to_numpy(dtype=float),
        lower_audit["recomputed_common_objective_lower"].to_numpy(dtype=float),
    ):
        raise RuntimeError("Recorded z_L is not the maximum over all 25 minimum objectives.")
    cap_tolerance = float(config["frontier"]["normalized_score"]["cap_residual_tolerance"])
    if float(minimum["minimum_cap_residual"].abs().max()) > cap_tolerance:
        raise RuntimeError("A minimum-score endpoint exceeded its cap tolerance.")
    order = build.order_sensitivity
    audit_keys = ["window_id", "period", "theta", "gamma", "ruler", "coordinate"]
    if bool(order.duplicated(audit_keys).any()) or set(order["role"].astype(str)) != {
        "primary_oot"
    }:
        raise RuntimeError("The all-cell primary ID-reversal audit is not unique.")
    if float(order["normalized_exposure_distance"].max()) > float(
        config["solver"]["order_exposure_distance_tolerance"]
    ):
        raise RuntimeError("ID reversal changed a primary allocation.")
    if float(order["objective_difference"].abs().max()) > float(
        config["solver"]["order_objective_tolerance_dollars"]
    ):
        raise RuntimeError("ID reversal changed a primary objective.")
    independent = build.independent_validation
    independent_config = config["solver"]["independent_validation"]
    if bool(independent.duplicated(audit_keys).any()) or set(
        independent["period"].astype(str)
    ) != set(independent_config["periods"]):
        raise RuntimeError("The all-cell independent-solver audit scope is incomplete.")
    if float(independent["objective_rate_difference"].abs().max()) > float(
        independent_config["objective_rate_tolerance"]
    ):
        raise RuntimeError("GLOP disagrees with HiGHS on an objective rate.")
    if float(independent["weighted_score_difference"].abs().max()) > float(
        independent_config["weighted_score_tolerance"]
    ):
        raise RuntimeError("GLOP disagrees with HiGHS on a funded score.")

    allocation_contrasts = build.allocation_contrasts
    contrast_keys = [
        "window_id",
        "period",
        "contrast_family",
        "ruler",
        "coordinate",
        "theta",
        "gamma",
    ]
    if bool(allocation_contrasts.duplicated(contrast_keys).any()):
        raise RuntimeError("Outcome-free allocation contrasts duplicate a locked cell.")
    contrast_group_size = allocation_contrasts.groupby(
        ["window_id", "period"], observed=True
    ).size()
    if not bool(contrast_group_size.eq(150).all()):
        raise RuntimeError("A primary month omits a prespecified allocation contrast.")
    _validate_contrast_specs(
        allocation_contrasts,
        group_columns=("window_id", "period"),
        label="Outcome-free allocation contrasts",
    )
    negative = allocation_contrasts.loc[
        build.allocation_contrasts["contrast_family"].eq(CONTRAST_THETA)
        & build.allocation_contrasts["gamma"].eq(0.0)
    ]
    expected_negative = int(config["expected_census"]["outcome_free_negative_controls"])
    if len(negative) != expected_negative:
        raise RuntimeError("The complete gamma=0 theta negative-control census is missing.")
    if float(negative["normalized_exposure_distance"].max()) > float(
        config["solver"]["negative_control_exposure_distance_tolerance"]
    ):
        raise RuntimeError("The gamma=0 set-embedding negative control changed an allocation.")
    if float(negative["objective_difference"].abs().max()) > float(
        config["solver"]["negative_control_objective_tolerance_dollars"]
    ):
        raise RuntimeError("The gamma=0 set-embedding negative control changed the objective.")
    score_tolerance = float(config["solver"]["negative_control_score_tolerance"])
    if (
        float(
            negative[["weighted_score_difference", "point_moment_difference"]]
            .abs()
            .to_numpy()
            .max(initial=0.0)
        )
        > score_tolerance
    ):
        raise RuntimeError("The gamma=0 set-embedding negative control changed a score moment.")

    allocations = build.allocations
    allocation_keys = ["window_id", "role", "period", "policy_label", "id"]
    if bool(allocations.duplicated(allocation_keys).any()):
        raise RuntimeError("A funded loan is duplicated within a frozen policy cell.")
    finite_allocation_columns = [
        "loan_amnt",
        "allocation_fraction",
        "exposure",
        "weight",
        "pd_point",
        "conformal_lower",
        "conformal_upper",
        "embedding_upper",
        "pd_effective",
        "expected_payoff_rate",
        "expected_payoff_contribution",
    ]
    if not bool(np.isfinite(allocations[finite_allocation_columns].to_numpy(dtype=float)).all()):
        raise RuntimeError("A funded allocation contains a non-finite numerical value.")
    if bool((allocations["exposure"] <= 0.0).any()):
        raise RuntimeError("Every persisted funded exposure must be strictly positive.")
    if bool(
        (
            (allocations["allocation_fraction"] <= 0.0) | (allocations["allocation_fraction"] > 1.0)
        ).any()
    ):
        raise RuntimeError("A persisted allocation fraction lies outside (0,1].")
    policy_keys = ["window_id", "role", "period", "policy_label", "comparator_rule"]
    policy_metadata = [
        "candidate_id",
        "paired_policy_id",
        "frontier_ruler",
        "frontier_coordinate",
        "theta",
        "gamma",
    ]
    allocation_metadata = allocations[[*policy_keys, *policy_metadata]].drop_duplicates()
    record_metadata = records[[*policy_keys, *policy_metadata]]
    metadata_audit = record_metadata.merge(
        allocation_metadata,
        on=policy_keys,
        how="outer",
        validate="one_to_one",
        suffixes=("_record", "_allocation"),
        indicator=True,
    )
    if not bool(metadata_audit["_merge"].eq("both").all()):
        raise RuntimeError("Solve records and allocations have different policy metadata keys.")
    for column in policy_metadata:
        record_values = metadata_audit[f"{column}_record"].to_numpy()
        allocation_values = metadata_audit[f"{column}_allocation"].to_numpy()
        if not np.array_equal(record_values, allocation_values):
            raise RuntimeError(f"Allocation metadata disagrees with solve records for {column}.")
    allocations = allocations.assign(
        weighted_point_numerator=allocations["exposure"] * allocations["pd_point"],
        weighted_effective_numerator=allocations["exposure"] * allocations["pd_effective"],
        weighted_original_upper_numerator=(
            allocations["exposure"] * allocations["conformal_upper"]
        ),
        weighted_embedding_upper_numerator=(
            allocations["exposure"] * allocations["embedding_upper"]
        ),
        above_reporting_tolerance=(
            allocations["exposure"] > float(config["solver"]["allocation_tolerance"])
        ).astype("int64"),
    )
    allocation_totals = (
        allocations.groupby(policy_keys, observed=True)
        .agg(
            allocation_exposure=("exposure", "sum"),
            allocation_weight=("weight", "sum"),
            allocation_expected_objective=("expected_payoff_contribution", "sum"),
            allocation_rows=("id", "size"),
            allocation_above_reporting_tolerance=("above_reporting_tolerance", "sum"),
            weighted_point_numerator=("weighted_point_numerator", "sum"),
            weighted_effective_numerator=("weighted_effective_numerator", "sum"),
            weighted_original_upper_numerator=("weighted_original_upper_numerator", "sum"),
            weighted_embedding_upper_numerator=("weighted_embedding_upper_numerator", "sum"),
        )
        .reset_index()
    )
    record_totals = records[
        [
            *policy_keys,
            "total_allocated",
            "expected_objective",
            "n_positive_exposure",
            "n_exposure_above_reporting_tolerance",
            "weighted_pd_point",
            "weighted_pd_effective",
            "weighted_conformal_upper",
            "weighted_embedding_upper",
        ]
    ].copy()
    reconciliation = record_totals.merge(
        allocation_totals,
        on=policy_keys,
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not bool(reconciliation["_merge"].eq("both").all()):
        raise RuntimeError("Solve records and funded-allocation policy identities differ.")
    exposure_tolerance = float(config["solver"]["allocation_reconciliation_tolerance_dollars"])
    contribution_tolerance = float(
        config["solver"]["contribution_reconciliation_tolerance_dollars"]
    )
    weight_tolerance = float(config["solver"]["weight_reconciliation_tolerance"])
    if not np.isclose(
        reconciliation["allocation_exposure"].to_numpy(dtype=float),
        reconciliation["total_allocated"].to_numpy(dtype=float),
        atol=exposure_tolerance,
        rtol=0.0,
    ).all():
        raise RuntimeError("Funded exposure does not reconcile to the solve record.")
    if not np.isclose(
        reconciliation["allocation_weight"].to_numpy(dtype=float),
        1.0,
        atol=weight_tolerance,
        rtol=0.0,
    ).all():
        raise RuntimeError("Funded allocation weights do not sum to one policy-wise.")
    if not np.isclose(
        reconciliation["allocation_expected_objective"].to_numpy(dtype=float),
        reconciliation["expected_objective"].to_numpy(dtype=float),
        atol=contribution_tolerance,
        rtol=0.0,
    ).all():
        raise RuntimeError("Expected contributions do not reconcile to the solve objective.")
    if not np.array_equal(
        reconciliation["allocation_rows"].to_numpy(dtype=np.int64),
        reconciliation["n_positive_exposure"].to_numpy(dtype=np.int64),
    ):
        raise RuntimeError("Persisted allocation support does not match the solve record.")
    if not np.array_equal(
        reconciliation["allocation_above_reporting_tolerance"].to_numpy(dtype=np.int64),
        reconciliation["n_exposure_above_reporting_tolerance"].to_numpy(dtype=np.int64),
    ):
        raise RuntimeError("The reporting-tolerance support diagnostic does not reconcile.")
    weighted_reconciliations = {
        "weighted_point_numerator": "weighted_pd_point",
        "weighted_effective_numerator": "weighted_pd_effective",
        "weighted_original_upper_numerator": "weighted_conformal_upper",
        "weighted_embedding_upper_numerator": "weighted_embedding_upper",
    }
    for numerator, record_column in weighted_reconciliations.items():
        allocation_moment = reconciliation[numerator].to_numpy(dtype=float) / reconciliation[
            "allocation_exposure"
        ].to_numpy(dtype=float)
        if not np.isclose(
            allocation_moment,
            reconciliation[record_column].to_numpy(dtype=float),
            atol=weight_tolerance,
            rtol=0.0,
        ).all():
            raise RuntimeError(f"Funded allocation moment does not reconcile: {record_column}.")

    exposure = allocations["exposure"].to_numpy(dtype=float)
    loan_amount = allocations["loan_amnt"].to_numpy(dtype=float)
    fraction = allocations["allocation_fraction"].to_numpy(dtype=float)
    if not np.isclose(
        exposure,
        loan_amount * fraction,
        atol=exposure_tolerance,
        rtol=0.0,
    ).all():
        raise RuntimeError("Loan-wise exposure is inconsistent with amount times allocation.")
    expected_contribution = exposure * allocations["expected_payoff_rate"].to_numpy(dtype=float)
    if not np.isclose(
        allocations["expected_payoff_contribution"].to_numpy(dtype=float),
        expected_contribution,
        atol=contribution_tolerance,
        rtol=0.0,
    ).all():
        raise RuntimeError("A loan-wise expected payoff contribution is inconsistent.")

    point = allocations["pd_point"].to_numpy(dtype=float)
    embedded = allocations["embedding_upper"].to_numpy(dtype=float)
    original = allocations["conformal_upper"].to_numpy(dtype=float)
    if bool(((embedded < point) | (embedded > original)).any()):
        raise RuntimeError("A funded embedding violates point <= embedded <= original upper.")
    if not np.array_equal(embedded == 1.0, original == 1.0):
        raise RuntimeError("A funded embedding changed binary label-1 membership.")
    expected_embedded: np.ndarray = np.empty(len(allocations), dtype=float)
    lower = allocations["conformal_lower"].to_numpy(dtype=float)
    for theta in THETA_GRID:
        theta_mask = allocations["theta"].eq(theta).to_numpy()
        expected_embedded[theta_mask] = set_preserving_upper(
            point[theta_mask], lower[theta_mask], original[theta_mask], theta=theta
        )
    if not np.array_equal(embedded, expected_embedded):
        raise RuntimeError("A funded embedding does not equal the prespecified theta formula.")
    gamma = allocations["gamma"].to_numpy(dtype=float)
    expected_score = point + gamma * (expected_embedded - point)
    if not np.array_equal(allocations["pd_effective"].to_numpy(dtype=float), expected_score):
        raise RuntimeError("A funded effective score does not equal q(theta,gamma).")
    theta_zero_allocations = allocations["theta"].eq(0.0)
    if not np.array_equal(
        allocations.loc[theta_zero_allocations, "embedding_upper"].to_numpy(dtype=float),
        allocations.loc[theta_zero_allocations, "conformal_upper"].to_numpy(dtype=float),
    ):
        raise RuntimeError("Funded theta=0 embeddings do not recover the original upper endpoint.")
    gamma_zero_allocations = allocations["gamma"].eq(0.0)
    if not np.array_equal(
        allocations.loc[gamma_zero_allocations, "pd_effective"].to_numpy(dtype=float),
        allocations.loc[gamma_zero_allocations, "pd_point"].to_numpy(dtype=float),
    ):
        raise RuntimeError("Funded gamma=0 scores are not the exact point-score control.")


def _contrast_specs() -> tuple[dict[str, Any], ...]:
    specs: list[dict[str, Any]] = []
    for ruler in RULERS:
        for coordinate in COORDINATE_GRID:
            for theta in THETA_GRID:
                specs.append(
                    {
                        "contrast_family": CONTRAST_GAMMA,
                        "ruler": ruler,
                        "coordinate": coordinate,
                        "theta": theta,
                        "theta_reference": theta,
                        "gamma": 1.0,
                        "gamma_reference": 0.0,
                    }
                )
            for theta in THETA_GRID[1:]:
                for gamma in GAMMA_GRID:
                    specs.append(
                        {
                            "contrast_family": CONTRAST_THETA,
                            "ruler": ruler,
                            "coordinate": coordinate,
                            "theta": theta,
                            "theta_reference": 0.0,
                            "gamma": gamma,
                            "gamma_reference": gamma,
                        }
                    )
    return tuple(specs)


_CONTRAST_SPEC_COLUMNS = (
    "contrast_family",
    "ruler",
    "coordinate",
    "theta",
    "theta_reference",
    "gamma",
    "gamma_reference",
    "policy_a",
    "policy_b",
)


def _expected_contrast_spec_set() -> set[tuple[Any, ...]]:
    expected: set[tuple[Any, ...]] = set()
    for spec in _contrast_specs():
        policy_a = policy_label(spec["ruler"], spec["theta"], spec["gamma"], spec["coordinate"])
        policy_b = policy_label(
            spec["ruler"],
            spec["theta_reference"],
            spec["gamma_reference"],
            spec["coordinate"],
        )
        row = {**spec, "policy_a": policy_a, "policy_b": policy_b}
        expected.add(tuple(row[column] for column in _CONTRAST_SPEC_COLUMNS))
    return expected


def _validate_contrast_specs(
    frame: pd.DataFrame,
    *,
    group_columns: Sequence[str],
    label: str,
) -> None:
    """Require the exact prespecified references and policy labels in every cell."""
    expected = _expected_contrast_spec_set()
    for group_key, group in frame.groupby(list(group_columns), observed=True, sort=True):
        observed = set(
            group.loc[:, list(_CONTRAST_SPEC_COLUMNS)].itertuples(index=False, name=None)
        )
        if observed != expected:
            raise RuntimeError(f"{label} has a mutated contrast specification: {group_key!r}.")


def _sharp_rows(
    allocations: pd.DataFrame,
    *,
    scope: str,
    window_id: str,
    period: str | None,
    lgd: float,
    committed_budget_per_period: float,
    normalization_periods: int,
) -> list[dict[str, Any]]:
    if (
        not np.isfinite(committed_budget_per_period)
        or committed_budget_per_period <= 0.0
        or isinstance(normalization_periods, bool)
        or normalization_periods <= 0
    ):
        raise ValueError("Sharp-bound normalization requires a positive budget and period count.")
    normalization_capital = float(committed_budget_per_period) * int(normalization_periods)
    normalization_rule = (
        "monthly_parent_committed_budget"
        if normalization_periods == 1
        else "pooled_period_count_times_parent_committed_budget"
    )
    index = PolicyContrastIndex(allocations, role="primary_oot")
    rows: list[dict[str, Any]] = []
    for spec in _contrast_specs():
        policy_a = policy_label(spec["ruler"], spec["theta"], spec["gamma"], spec["coordinate"])
        policy_b = policy_label(
            spec["ruler"],
            spec["theta_reference"],
            spec["gamma_reference"],
            spec["coordinate"],
        )
        rows.append(
            {
                "scope": scope,
                "window_id": str(window_id),
                "period": period,
                "normalization_rule": normalization_rule,
                "normalization_periods": int(normalization_periods),
                "committed_budget_per_period": float(committed_budget_per_period),
                **spec,
                **index.sharp_bounds(
                    policy_a=policy_a,
                    policy_b=policy_b,
                    lgd=float(lgd),
                    normalization_capital_a=normalization_capital,
                    normalization_capital_b=normalization_capital,
                ),
            }
        )
    return rows


def build_sharp_embedding_contrasts(
    joined_primary_allocations: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    lgd: float,
    budget: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build monthly and pooled-window common-outcome sharp bounds without selection."""
    if set(joined_primary_allocations["role"].astype(str)) != {"primary_oot"}:
        raise ValueError("Embedding contrasts may evaluate only the primary OOT role.")
    monthly_rows: list[dict[str, Any]] = []
    window_rows: list[dict[str, Any]] = []
    for window_id, window in joined_primary_allocations.groupby(
        "window_id", observed=True, sort=True
    ):
        periods = tuple(sorted(window["period"].astype(str).unique()))
        if len(periods) != int(config["frontier"]["expected_primary_months"]):
            raise RuntimeError(f"Window {window_id} does not contain all primary months.")
        window_rows.extend(
            _sharp_rows(
                window,
                scope="pooled_primary_window",
                window_id=str(window_id),
                period=None,
                lgd=lgd,
                committed_budget_per_period=budget,
                normalization_periods=len(periods),
            )
        )
        for period, month in window.groupby("period", observed=True, sort=True):
            monthly_rows.extend(
                _sharp_rows(
                    month,
                    scope="primary_month",
                    window_id=str(window_id),
                    period=str(period),
                    lgd=lgd,
                    committed_budget_per_period=budget,
                    normalization_periods=1,
                )
            )
    monthly = pd.DataFrame(monthly_rows)
    window = pd.DataFrame(window_rows)
    directions = metric_direction_census(window, metrics=config["metrics"])
    validate_complete_evaluation(
        monthly,
        window,
        directions,
        config=config,
    )
    return monthly, window, directions


def metric_direction_census(
    bounds: pd.DataFrame,
    *,
    metrics: Mapping[str, Mapping[str, Any]],
) -> pd.DataFrame:
    """Expand every pooled-window bound into all three prespecified metric directions."""
    rows: list[dict[str, Any]] = []
    identity = [
        "window_id",
        "contrast_family",
        "ruler",
        "coordinate",
        "theta",
        "theta_reference",
        "gamma",
        "gamma_reference",
        "policy_a",
        "policy_b",
    ]
    for item in bounds.to_dict(orient="records"):
        for metric, (lower_name, upper_name) in _WINDOW_METRICS.items():
            lower = float(item[lower_name])
            upper = float(item[upper_name])
            tolerance = float(metrics[metric]["direction_tolerance"])
            if lower > 0.0:
                geometric_direction = "positive"
            elif upper < 0.0:
                geometric_direction = "negative"
            elif lower == 0.0 and upper == 0.0:
                geometric_direction = "exact_zero"
            else:
                geometric_direction = "contains_zero"
            if lower > tolerance:
                direction_at_tolerance = "positive"
            elif upper < -tolerance:
                direction_at_tolerance = "negative"
            elif abs(lower) <= tolerance and abs(upper) <= tolerance:
                direction_at_tolerance = "within_tolerance"
            else:
                direction_at_tolerance = "not_directionally_separated_at_tolerance"
            rows.append(
                {
                    **{key: item[key] for key in identity},
                    "metric": metric,
                    "lower": lower,
                    "upper": upper,
                    "geometric_direction": geometric_direction,
                    "direction_at_tolerance": direction_at_tolerance,
                    "direction_tolerance": tolerance,
                }
            )
    return pd.DataFrame(rows)


def validate_complete_evaluation(
    monthly: pd.DataFrame,
    window: pd.DataFrame,
    directions: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> None:
    """Fail closed on complete contrasts, ordered bounds, and the negative control."""
    expected = config["expected_census"]
    observed = {
        "monthly_sharp_contrasts": len(monthly),
        "window_sharp_contrasts": len(window),
        "direction_rows": len(directions),
    }
    for key, value in observed.items():
        if value != int(expected[key]):
            raise RuntimeError(f"{key} census is {value}, not {expected[key]}.")
    for label, frame in (
        ("monthly sharp contrasts", monthly),
        ("pooled sharp contrasts", window),
        ("metric direction census", directions),
    ):
        numeric = frame.select_dtypes(include=[np.number])
        try:
            finite = np.isfinite(numeric.to_numpy(dtype=float)).all()
        except (TypeError, ValueError) as error:
            raise RuntimeError(f"{label} contains a non-numeric numeric-field value.") from error
        if not bool(finite):
            raise RuntimeError(f"{label} contains a non-finite numerical value.")
    identity = [
        "window_id",
        "contrast_family",
        "ruler",
        "coordinate",
        "theta",
        "gamma",
    ]
    if bool(monthly.duplicated(["period", *identity]).any()) or bool(
        window.duplicated(identity).any()
    ):
        raise RuntimeError("A sharp contrast identity is duplicated.")
    expected_windows = int(config["frontier"]["expected_windows"])
    expected_months = int(config["frontier"]["expected_primary_months"])
    if (
        int(monthly["window_id"].nunique()) != expected_windows
        or int(window["window_id"].nunique()) != expected_windows
    ):
        raise RuntimeError("The sharp-bound window census is incomplete.")
    monthly_per_cell = int(expected["monthly_sharp_contrasts"]) // (
        expected_windows * expected_months
    )
    window_per_cell = int(expected["window_sharp_contrasts"]) // expected_windows
    if not bool(
        monthly.groupby(["window_id", "period"], observed=True).size().eq(monthly_per_cell).all()
    ) or not bool(window.groupby("window_id", observed=True).size().eq(window_per_cell).all()):
        raise RuntimeError("A month or pooled window omits a prespecified sharp contrast.")
    _validate_contrast_specs(
        monthly,
        group_columns=("window_id", "period"),
        label="Monthly sharp contrasts",
    )
    _validate_contrast_specs(
        window,
        group_columns=("window_id",),
        label="Pooled-window sharp contrasts",
    )
    for frame in (monthly, window):
        finite_columns = [
            "normalization_periods",
            "committed_budget_per_period",
            "policy_a_capital",
            "policy_b_capital",
            "policy_a_normalization_capital",
            "policy_b_normalization_capital",
            "expected_objective_difference",
            "realized_payoff_rate_difference_lower",
            "realized_payoff_rate_difference_upper",
        ]
        finite_values = frame[finite_columns].to_numpy(dtype=float)
        if not bool(np.isfinite(finite_values).all()):
            raise RuntimeError("Sharp contrast normalization contains a non-finite value.")
        for lower_name, upper_name in _WINDOW_METRICS.values():
            values = frame[[lower_name, upper_name]].to_numpy(dtype=float)
            if not bool(np.isfinite(values).all()):
                raise RuntimeError(f"Sharp bounds contain a non-finite value for {lower_name}.")
            if bool((frame[lower_name] > frame[upper_name]).any()):
                raise RuntimeError(f"Sharp bounds are reversed for {lower_name}.")
        if set(frame["contrast_family"].astype(str)) != {CONTRAST_GAMMA, CONTRAST_THETA}:
            raise RuntimeError("A locked contrast family is missing from evaluation.")
    budget = float(config["normalization"]["committed_budget_per_period"])
    budget_tolerance = float(config["solver"]["budget_residual_tolerance_dollars"])
    normalization_checks = (
        (
            monthly,
            1,
            "monthly_parent_committed_budget",
        ),
        (
            window,
            expected_months,
            "pooled_period_count_times_parent_committed_budget",
        ),
    )
    for frame, periods, rule in normalization_checks:
        expected_normalizer = periods * budget
        if (
            set(frame["normalization_rule"].astype(str)) != {rule}
            or not bool(frame["normalization_periods"].eq(periods).all())
            or not bool(frame["committed_budget_per_period"].eq(budget).all())
            or not bool(frame["policy_a_normalization_capital"].eq(expected_normalizer).all())
            or not bool(frame["policy_b_normalization_capital"].eq(expected_normalizer).all())
        ):
            raise RuntimeError(
                "A sharp contrast used solver capital instead of the locked common capital."
            )
        allowed_residual = periods * budget_tolerance
        for column in ("policy_a_capital", "policy_b_capital"):
            if float((frame[column] - expected_normalizer).abs().max()) > allowed_residual:
                raise RuntimeError(
                    f"{column} does not reconcile to the committed common-capital normalizer."
                )
        for suffix in ("lower", "upper"):
            dollar = frame[f"realized_payoff_difference_{suffix}"].to_numpy(dtype=float)
            rate = frame[f"realized_payoff_rate_difference_{suffix}"].to_numpy(dtype=float)
            if not bool(
                np.allclose(
                    rate,
                    dollar / expected_normalizer,
                    rtol=1.0e-12,
                    atol=1.0e-12,
                )
            ):
                raise RuntimeError("Payoff-rate bounds do not equal dollars over locked capital.")
    negative = window.loc[window["contrast_family"].eq(CONTRAST_THETA) & window["gamma"].eq(0.0)]
    if len(negative) != int(expected["window_negative_controls"]):
        raise RuntimeError("The pooled-window negative-control census is incomplete.")
    monthly_negative = monthly.loc[
        monthly["contrast_family"].eq(CONTRAST_THETA) & monthly["gamma"].eq(0.0)
    ]
    if len(monthly_negative) != int(expected["monthly_negative_controls"]):
        raise RuntimeError("The monthly negative-control census is incomplete.")
    negative_tolerances = {
        "expected_objective_difference": float(
            config["contrasts"]["expected_objective_negative_control_tolerance_dollars"]
        ),
        "realized_payoff_difference_lower": float(
            config["contrasts"]["payoff_negative_control_tolerance_dollars"]
        ),
        "realized_payoff_difference_upper": float(
            config["contrasts"]["payoff_negative_control_tolerance_dollars"]
        ),
        "weighted_default_difference_lower": float(
            config["contrasts"]["rate_negative_control_tolerance"]
        ),
        "weighted_default_difference_upper": float(
            config["contrasts"]["rate_negative_control_tolerance"]
        ),
        "weighted_miscoverage_difference_lower": float(
            config["contrasts"]["rate_negative_control_tolerance"]
        ),
        "weighted_miscoverage_difference_upper": float(
            config["contrasts"]["rate_negative_control_tolerance"]
        ),
    }
    for label, frame in (("monthly", monthly_negative), ("pooled-window", negative)):
        for column, tolerance in negative_tolerances.items():
            if float(frame[column].abs().max()) > tolerance:
                raise RuntimeError(f"The gamma=0 {label} negative control is not zero: {column}.")
    negative_directions = directions.loc[
        directions["contrast_family"].eq(CONTRAST_THETA) & directions["gamma"].eq(0.0)
    ]
    if set(negative_directions["direction_at_tolerance"].astype(str)) != {"within_tolerance"}:
        raise RuntimeError("The gamma=0 direction census exceeds its declared tolerance.")
    direction_keys = [
        "window_id",
        *_CONTRAST_SPEC_COLUMNS,
        "metric",
    ]
    if bool(directions.duplicated(direction_keys).any()) or set(
        directions["metric"].astype(str)
    ) != set(_WINDOW_METRICS):
        raise RuntimeError("The metric-direction census duplicates or omits a locked cell.")
    expected_directions = metric_direction_census(window, metrics=config["metrics"])
    compare_columns = [
        *direction_keys,
        "lower",
        "upper",
        "geometric_direction",
        "direction_at_tolerance",
        "direction_tolerance",
    ]
    observed_sorted = directions.loc[:, compare_columns].sort_values(
        direction_keys, kind="mergesort"
    )
    expected_sorted = expected_directions.loc[:, compare_columns].sort_values(
        direction_keys, kind="mergesort"
    )
    if not observed_sorted.reset_index(drop=True).equals(expected_sorted.reset_index(drop=True)):
        raise RuntimeError("The metric-direction census does not reconcile to pooled bounds.")


def primary_outcome_audit(
    outcomes: pd.DataFrame,
    allocations: pd.DataFrame,
) -> pd.DataFrame:
    """Record the candidate and funded outcome census used only after the freeze."""
    primary = outcomes.loc[outcomes["role"].eq("primary_oot")].copy()
    if bool(primary["id"].duplicated().any()):
        raise RuntimeError("Primary outcome IDs are not unique.")
    rows: list[dict[str, Any]] = []
    for period, candidates in primary.groupby("period", observed=True, sort=True):
        funded = allocations.loc[allocations["period"].eq(period)]
        rows.append(
            {
                "role": "primary_oot",
                "period": str(period),
                "candidate_rows": int(len(candidates)),
                "unresolved_rows": int(candidates["snapshot_default"].isna().sum()),
                "funded_allocation_rows": int(len(funded)),
                "funded_unique_ids": int(funded["id"].nunique()),
                "policies": int(funded["policy_label"].nunique()),
            }
        )
    return pd.DataFrame(rows)
