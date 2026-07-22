"""Run the locked outcome-free IJDS upper-RHS semantics recovery V3 audit."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

import highspy
import numpy as np
import pandas as pd
import yaml
from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.experiments import run_ijds_policy_support_optimal_face_v2 as v2  # noqa: E402
from src.evaluation.standardized_credit_payoff import (  # noqa: E402
    expected_objective_coefficients,
)
from src.ijds_audit.config import load_v4_config  # noqa: E402
from src.ijds_audit.optimal_face_certification import (  # noqa: E402
    audit_full_basis,
    basis_status_name,
)
from src.ijds_audit.rhs_ranging import interpret_upper_only_rhs_ranging  # noqa: E402
from src.ijds_challengers.archive import (  # noqa: E402
    load_outcome_free_decision_base,
    monthly_frames,
    verified_parent_artifacts,
)
from src.utils.isolated_experiment import (  # noqa: E402
    OutputPaths,
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    prepare_output_paths as prepare_isolated_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_isolated_run_dir,
    resolve_repo_input,
)
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    utc_now_iso,
)

CONFIG_RELATIVE_PATH = Path(
    "configs/experiments/ijds_policy_support_rhs_semantics_recovery_2026-07-21_v3.yaml"
)
DEFAULT_CONFIG_PATH = ROOT / CONFIG_RELATIVE_PATH
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
IMPLEMENTATION_PATHS = (
    Path("configs/experiments/ijds_policy_support_optimal_face_2026-07-21_v2.yaml"),
    Path("docs/research/ijds_policy_support_rhs_semantics_recovery_v3_protocol_2026-07-21.md"),
    Path("scripts/experiments/run_ijds_policy_support_rhs_semantics_recovery_v3.py"),
    Path("scripts/experiments/run_ijds_policy_support_optimal_face_v2.py"),
    Path("src/evaluation/standardized_credit_payoff.py"),
    Path("src/ijds_audit/optimal_face_certification.py"),
    Path("src/ijds_audit/portfolio.py"),
    Path("src/ijds_audit/rhs_ranging.py"),
    Path("src/ijds_challengers/archive.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("tests/test_ijds_policy_support_rhs_semantics_recovery_v3.py"),
    Path("tests/test_ijds_rhs_ranging.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)
DATA_OUTPUT_KEYS = (
    "corrected_central_rhs_ranges",
    "gap_fill_basis_diagnostics",
    "gap_fill_row_slack_details",
    "gap_fill_flagged_nonbasic_variables",
    "corrected_rhs_coverage",
    "corrected_lateral_comparisons",
)
MODEL_OUTPUT_KEYS = ("deterministic_result", "execution_receipt")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the V3 audit CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    return parser.parse_args(argv)


def _resolve_locked_config_path(config_path: Path, *, repo_root: Path) -> Path:
    resolved = resolve_repo_input(config_path, repo_root=repo_root)
    expected = (repo_root / CONFIG_RELATIVE_PATH).resolve()
    if resolved != expected:
        raise RuntimeError(f"V3 execution requires the locked config at {CONFIG_RELATIVE_PATH}.")
    return resolved


def load_config(path: Path) -> dict[str, Any]:
    """Load and fail closed on the exact V3 recovery contract."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("RHS recovery V3 config must be a YAML mapping.")
    required = {
        "schema_version",
        "protocol_status",
        "protocol_tag",
        "run_tag",
        "hypothesis",
        "v2_source",
        "source_ingest",
        "rhs_semantics",
        "coverage",
        "solver",
        "tolerances",
        "full_basis_gap_audit",
        "v2_corrections",
        "claim_boundary",
        "stop_rules",
        "output",
    }
    if missing := sorted(required.difference(payload)):
        raise ValueError(f"RHS recovery V3 config is missing sections: {missing}.")
    if payload["schema_version"] != "2026-07-21.2":
        raise ValueError("RHS recovery V3 schema version changed.")
    expected_run = "ijds-policy-support-rhs-semantics-recovery-2026-07-21-v3"
    if payload["run_tag"] != expected_run:
        raise ValueError("RHS recovery V3 run tag changed.")
    if payload["protocol_tag"] != f"protocol/{expected_run}":
        raise ValueError("RHS recovery V3 protocol tag changed.")
    if payload["protocol_status"] != (
        "locked_retrospective_outcome_free_rhs_semantics_recovery_v3_before_execution"
    ):
        raise ValueError("RHS recovery V3 protocol is not locked.")
    if not isinstance(payload["hypothesis"], str) or not payload["hypothesis"].strip():
        raise ValueError("RHS recovery V3 hypothesis must be nonempty.")

    source = payload["v2_source"]
    expected_source = {
        "run_tag": "ijds-policy-support-optimal-face-audit-2026-07-21-v2",
        "protocol_tag": "protocol/ijds-policy-support-optimal-face-audit-2026-07-21-v2",
        "protocol_commit": "86fddefdcf4d40a971866b2d9acf1d34f5c3bca2",
    }
    if any(source.get(key) != value for key, value in expected_source.items()):
        raise ValueError("RHS recovery V3 source identity changed.")
    descriptor = source.get("deterministic_summary")
    if not isinstance(descriptor, dict) or set(descriptor) != {"path", "bytes", "sha256"}:
        raise ValueError("RHS recovery V3 summary descriptor is incomplete.")
    expected_counts = {
        "central_rows": 7_297,
        "periods": 15,
        "v2_lateral_probe_rows": 5_874,
        "v2_breakpoint_rows": 2_952,
        "v2_optimal_face_targets": 8,
        "central_risk_upper_rows": 7_228,
        "central_risk_basic_rows": 69,
        "v2_domain_clipped_cap_containment_failures": 66,
        "corrected_cap_containment_passes": 7_297,
        "initial_positive_gaps": 196,
        "unique_gap_seed_solves": 196,
        "gap_midpoints_matching_registered_v2_seeds": 196,
    }
    if any(int(source["expected"].get(key, -1)) != value for key, value in expected_counts.items()):
        raise ValueError("RHS recovery V3 source census changed.")
    expected_basenames = {
        "central_basis_diagnostics": "central_full_basis_diagnostics.parquet",
        "row_slack_details": "row_slack_basis_details.parquet",
        "lateral_probe_diagnostics": "breakpoint_lateral_probe_diagnostics.parquet",
        "breakpoint_comparisons": "breakpoint_allocation_comparisons.parquet",
        "optimal_face_ranges": "conditional_optimal_face_ranges.parquet",
    }
    if source.get("required_artifact_basenames") != expected_basenames:
        raise ValueError("RHS recovery V3 artifact names changed.")

    ingest = payload["source_ingest"]
    expected_ingest = {
        "inherit_exact_v2_parent_and_allowlist": True,
        "allowed_raw_columns": ["id", "loan_amnt", "int_rate", "purpose"],
        "outcome_columns_passed": [],
        "forbidden_tokens": [
            "loan_status",
            "default",
            "charged_off",
            "outcome",
            "label",
            "target",
            "evaluation",
            "coverage",
            "miscoverage",
            "payoff",
        ],
    }
    if ingest != expected_ingest:
        raise ValueError("RHS recovery V3 source-ingest contract changed.")
    forbidden = tuple(str(value).casefold() for value in ingest["forbidden_tokens"])
    if not forbidden or any(
        token in str(column).casefold()
        for column in ingest["allowed_raw_columns"]
        for token in forbidden
    ):
        raise ValueError("RHS recovery V3 allowlist contains an outcome-like token.")

    semantics = payload["rhs_semantics"]
    expected_semantics = {
        "row_role": "point_risk_cap",
        "model_form": "negative_infinity_leq_row_activity_leq_upper_rhs",
        "budget_dollars": 1_000_000.0,
        "normalized_cap_domain": [0.0, 1.0],
        "upper_nonbasic_rule": "raw_row_bound_dn_up_are_upper_rhs_range",
        "basic_rule": "upper_rhs_ray_from_raw_row_activity_to_normalized_domain_upper",
        "basic_requires_zero_row_dual": True,
        "persist_raw_ranging_as_activity_range_for_basic_rows": True,
        "fail_closed_statuses": ["lower", "zero", "nonbasic"],
        "official_highs_version": "1.15.1",
        "official_highs_githash": "04024d7",
    }
    if semantics != expected_semantics:
        raise ValueError("RHS recovery V3 row-ranging semantics changed.")

    coverage = payload["coverage"]
    expected_coverage = {
        "registered_support": [0.05, 0.12],
        "gap_tolerance": 1.0e-10,
        "seed_match_tolerance": 1.0e-12,
        "cap_containment_tolerance": 1.0e-10,
        "targeted_gap_coverage_tolerance": 1.0e-10,
        "initial_gap_definition": (
            "positive_components_of_registered_support_not_covered_by_status_aware_v2_central_intervals"
        ),
        "gap_seed": "exact_registered_v2_midpoint_seed_nearest_to_each_initial_gap_midpoint",
        "gap_fill_passes": 1,
        "adaptive_additional_solves_after_registered_pass": False,
        "require_every_initial_gap_targeted_once": True,
        "require_every_gap_seed_strictly_inside_target_gap": True,
        "require_final_connected_coverage": True,
        "require_zero_final_positive_gaps": True,
        "require_all_solved_caps_contained": True,
    }
    if coverage != expected_coverage:
        raise ValueError("RHS recovery V3 coverage contract changed.")

    solver = payload["solver"]
    expected_solver = {
        "highspy_version": "1.15.1",
        "highs_native_version": "1.15.1",
        "highs_githash": "04024d7",
        "solver": "simplex",
        "presolve": "on",
        "threads": 1,
        "time_limit_seconds": 300,
        "dual_feasibility_tolerance": 1.0e-9,
        "primal_feasibility_tolerance": 1.0e-9,
        "reset_global_scheduler_if_available": True,
        "zero_all_clocks_if_available": True,
        "zero_all_clocks_required": False,
        "session_scope": "one_fresh_highs_session_per_registered_gap_midpoint_seed",
        "deterministic_candidate_order": ["issue_d", "id"],
        "persist_get_run_time": True,
    }
    if any(solver.get(key) != value for key, value in expected_solver.items()):
        raise ValueError("RHS recovery V3 HiGHS contract changed.")
    expected_tolerances = {
        "dual_near_zero_scaled_absolute": 1.0e-7,
        "dual_near_zero_relative": 1.0e-12,
        "dual_sign_scaled_violation": 1.0e-9,
        "primal_degeneracy": 1.0e-9,
        "objective_reconciliation_dollars": 1.0e-5,
        "policy_constraint_normalized": 1.0e-8,
        "allocation_distance": 1.0e-10,
        "basic_row_dual": 1.0e-12,
        "row_activity_normalized": 1.0e-10,
    }
    if payload["tolerances"] != expected_tolerances:
        raise ValueError("RHS recovery V3 tolerance contract changed.")

    expected_basis_audit = {
        "audit_every_gap_seed": True,
        "persist_all_row_slack_details": True,
        "persist_all_scale_aware_warnings": True,
        "warnings_block_uniqueness_promotion": True,
        "warnings_do_not_block_rhs_coverage": True,
        "no_conditional_face_solves": True,
        "no_global_l1_diameter_claim": True,
    }
    if payload["full_basis_gap_audit"] != expected_basis_audit:
        raise ValueError("RHS recovery V3 full-basis audit contract changed.")

    expected_corrections = {
        "corrected_lateral_cooccurrence_definition": (
            "allocation_differs_and_same_cap_epsilon_mobility"
        ),
        "preserve_v2_fields_without_overwrite": True,
        "epsilon_mobility_interpretation": (
            "epsilon_near_optimal_conditioning_not_exact_alternate_optimum"
        ),
    }
    if payload["v2_corrections"] != expected_corrections:
        raise ValueError("RHS recovery V3 correction contract changed.")

    boundary = payload["claim_boundary"]
    required_true = {
        "no_empirical_metric_or_direction",
        "no_policy_or_cap_selection",
        "no_tie_or_exact_alternate_optimum_claim",
        "no_exact_symbolic_optimal_face_claim",
        "no_global_optimal_face_diameter_claim",
        "no_continuous_joint_frontier_uniqueness",
        "no_allocation_continuity_or_seam_conditioning_claim",
        "no_universal_comparator_support",
        "no_selected_or_funded_set_claim",
        "rhs_coverage_is_numerical_and_support_bounded",
        "v2_remains_immutable_and_fail_closed",
        "epsilon_mobility_is_not_nonuniqueness",
    }
    if boundary.get("outcome_columns_passed") != [] or any(
        boundary.get(key) is not True for key in required_true
    ):
        raise ValueError("RHS recovery V3 claim boundary changed.")
    expected_boundary_flags = {
        "retrospective": True,
        "preregistered": False,
        "confirmatory": False,
        "prospective": False,
    }
    if any(boundary.get(key) is not value for key, value in expected_boundary_flags.items()):
        raise ValueError("RHS recovery V3 temporal claim boundary changed.")

    expected_stop_rules = {
        "stop_on_source_hash_mismatch",
        "stop_on_dirty_or_untagged_head",
        "stop_on_outcome_like_input",
        "stop_on_preexisting_output_path",
        "stop_on_solver_identity_or_option_drift",
        "stop_on_implementation_drift",
        "stop_on_v2_census_or_schema_drift",
        "stop_on_unexpected_risk_row_status",
        "stop_on_basic_row_nonzero_dual",
        "stop_on_cap_containment_failure",
        "stop_on_gap_seed_census_or_match_failure",
        "stop_on_gap_seed_outside_target_gap",
        "stop_on_nonoptimal_or_nonfinite_solve",
        "stop_on_invalid_or_unsupported_gap_basis",
        "stop_on_gap_basis_dual_sign_violation",
        "stop_on_gap_basis_objective_reconciliation_failure",
        "stop_on_gap_basis_policy_feasibility_failure",
        "scientific_claim_gate_on_final_rhs_coverage_failure",
        "scientific_claim_gate_on_any_scale_aware_warning_for_uniqueness",
        "retain_complete_results_after_scientific_stop",
    }
    stop_rules = payload["stop_rules"]
    if set(stop_rules) != expected_stop_rules or any(
        stop_rules.get(key) is not True for key in expected_stop_rules
    ):
        raise ValueError("RHS recovery V3 stop-rule contract changed.")

    output = payload["output"]
    if output.get("immutability") != "hard_no_overwrite_choose_fresh_run_tag":
        raise ValueError("RHS recovery V3 outputs must be immutable.")
    names: list[str] = []
    for key in (*DATA_OUTPUT_KEYS, *MODEL_OUTPUT_KEYS):
        value = output.get(key)
        if not isinstance(value, str) or Path(value).name != value:
            raise ValueError(f"RHS recovery V3 output {key} must be a contained basename.")
        suffix = ".parquet" if key in DATA_OUTPUT_KEYS else ".json"
        if not value.endswith(suffix):
            raise ValueError(f"RHS recovery V3 output {key} must end in {suffix}.")
        names.append(value.casefold())
    if len(names) != len(set(names)) or "protocol_freeze.json" in names:
        raise ValueError("RHS recovery V3 output filenames must be distinct.")
    return cast(dict[str, Any], payload)


def preflight_output_paths(config: Mapping[str, Any], *, repo_root: Path = ROOT) -> OutputPaths:
    """Validate immutable V3 output locations without creating them."""
    output = config["output"]
    run_tag = str(config["run_tag"])
    paths = OutputPaths(
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
    if existing := [path for path in (paths.data_dir, paths.model_dir) if path.exists()]:
        raise FileExistsError(f"V3 output already exists: {existing}; choose a fresh run tag.")
    return paths


def prepare_output_paths(config: Mapping[str, Any], *, repo_root: Path = ROOT) -> OutputPaths:
    """Create fresh, contained V3 output directories."""
    return prepare_isolated_output_paths(
        dict(config),
        repo_root=repo_root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a JSON object at {path}.")
    return payload


def _verify_descriptor(descriptor: Mapping[str, Any], *, repo_root: Path) -> Path:
    path = resolve_repo_input(str(descriptor["path"]), repo_root=repo_root)
    actual = relative_artifact_descriptor(path, repo_root=repo_root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor[field]:
            raise RuntimeError(f"V3 source descriptor mismatch for {field}: {path}.")
    return path


def _artifact_path(summary: Mapping[str, Any], basename: str, *, repo_root: Path) -> Path:
    artifacts = summary.get("artifacts")
    if not isinstance(artifacts, dict):
        raise TypeError("V2 summary has no artifact mapping.")
    matches = [value for value in artifacts.values() if Path(str(value["path"])).name == basename]
    if len(matches) != 1 or not isinstance(matches[0], dict):
        raise RuntimeError(f"V2 summary does not identify exactly one {basename} artifact.")
    return _verify_descriptor(matches[0], repo_root=repo_root)


def _frozen_v2_config_path(summary: Mapping[str, Any], *, repo_root: Path) -> Path:
    """Verify the V2 config against its immutable protocol-freeze descriptor."""
    freeze = _json(_artifact_path(summary, "protocol_freeze.json", repo_root=repo_root))
    implementation = freeze.get("implementation_provenance")
    if not isinstance(implementation, dict):
        raise TypeError("V2 protocol freeze has no implementation provenance.")
    sources = implementation.get("source_files")
    if not isinstance(sources, dict):
        raise TypeError("V2 protocol freeze has no source-file descriptors.")
    key = v2.CONFIG_RELATIVE_PATH.as_posix()
    descriptor = sources.get(key)
    if not isinstance(descriptor, dict):
        raise RuntimeError("V2 protocol freeze does not hash-lock its config.")
    path = _verify_descriptor(descriptor, repo_root=repo_root)
    expected = (repo_root / v2.CONFIG_RELATIVE_PATH).resolve()
    if path != expected:
        raise RuntimeError("V2 protocol freeze points to an unexpected config path.")
    return path


def verify_v2_source(
    config: Mapping[str, Any], *, repo_root: Path = ROOT
) -> tuple[dict[str, Any], dict[str, Path]]:
    """Verify the complete immutable V2 artifact set and return required paths."""
    source = config["v2_source"]
    summary_path = _verify_descriptor(source["deterministic_summary"], repo_root=repo_root)
    summary = _json(summary_path)
    expected = {
        "status": "complete_outcome_free_optimal_face_v2_audit",
        "run_tag": source["run_tag"],
        "protocol_tag": source["protocol_tag"],
        "protocol_commit": source["protocol_commit"],
        "outcome_columns_passed": [],
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    for field, value in expected.items():
        if summary.get(field) != value:
            raise RuntimeError(f"V2 summary identity mismatch: {field}.")
    artifacts = summary.get("artifacts")
    if not isinstance(artifacts, dict) or len(artifacts) != 10:
        raise RuntimeError("V2 summary must hash-lock its protocol freeze and nine parquets.")
    for descriptor in artifacts.values():
        if not isinstance(descriptor, dict):
            raise TypeError("V2 artifact descriptor is not a mapping.")
        _verify_descriptor(descriptor, repo_root=repo_root)
    _frozen_v2_config_path(summary, repo_root=repo_root)
    paths = {
        key: _artifact_path(summary, basename, repo_root=repo_root)
        for key, basename in source["required_artifact_basenames"].items()
    }
    return summary, paths


def merge_intervals(
    intervals: Sequence[tuple[float, float]], *, tolerance: float
) -> tuple[tuple[float, float], ...]:
    """Merge finite, ordered intervals at the registered absolute tolerance."""
    tol = float(tolerance)
    if tol < 0.0:
        raise ValueError("Interval tolerance cannot be negative.")
    ordered = sorted((float(left), float(right)) for left, right in intervals)
    if any(not np.isfinite([left, right]).all() or left > right for left, right in ordered):
        raise ValueError("Intervals must be finite and ordered.")
    merged: list[list[float]] = []
    for left, right in ordered:
        if not merged or left > merged[-1][1] + tol:
            merged.append([left, right])
        else:
            merged[-1][1] = max(merged[-1][1], right)
    return tuple((left, right) for left, right in merged)


def support_gaps(
    intervals: Sequence[tuple[float, float]],
    *,
    support_lower: float,
    support_upper: float,
    tolerance: float,
) -> tuple[tuple[float, float], ...]:
    """Return positive uncovered components of one closed support interval."""
    lower = float(support_lower)
    upper = float(support_upper)
    tol = float(tolerance)
    if not 0.0 <= lower < upper <= 1.0:
        raise ValueError("Registered support must be a nonempty subset of [0, 1].")
    clipped = [
        (max(left, lower), min(right, upper))
        for left, right in merge_intervals(intervals, tolerance=tol)
        if right >= lower - tol and left <= upper + tol
    ]
    cursor = lower
    gaps: list[tuple[float, float]] = []
    for left, right in clipped:
        if left > cursor + tol:
            gaps.append((cursor, left))
        cursor = max(cursor, right)
    if cursor < upper - tol:
        gaps.append((cursor, upper))
    return tuple(gaps)


def _basis_status(value: str) -> highspy.HighsBasisStatus:
    statuses = {
        "upper": highspy.HighsBasisStatus.kUpper,
        "basic": highspy.HighsBasisStatus.kBasic,
    }
    try:
        return statuses[str(value)]
    except KeyError as exc:
        raise RuntimeError(f"Unsupported V2 risk-row basis status: {value!r}.") from exc


def corrected_central_rhs_ranges(
    central: pd.DataFrame,
    row_details: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Apply status-aware upper-RHS semantics to every immutable V2 central row."""
    expected = config["v2_source"]["expected"]
    budget = float(config["rhs_semantics"]["budget_dollars"])
    cap_tol = float(config["coverage"]["cap_containment_tolerance"])
    dual_tol = float(config["tolerances"]["basic_row_dual"])
    risk = row_details.loc[
        row_details["solve_origin"].eq("central")
        & row_details["row_name"].eq(str(config["rhs_semantics"]["row_role"])),
        [
            "period",
            "point_cap",
            "basis_status",
            "row_value",
            "row_lower",
            "row_upper",
            "row_dual",
        ],
    ].copy()
    if bool(risk.duplicated(["period", "point_cap"]).any()):
        raise RuntimeError("V2 central risk-row details contain duplicate cap keys.")
    selected = central[
        [
            "period",
            "point_cap",
            "fresh_basis_cap_lower",
            "fresh_basis_cap_upper",
        ]
    ].merge(risk, on=["period", "point_cap"], validate="one_to_one")
    if len(selected) != int(expected["central_rows"]):
        raise RuntimeError("V2 central risk-row census changed.")

    rows: list[dict[str, Any]] = []
    for item in selected.itertuples(index=False):
        status = _basis_status(str(item.basis_status))
        interpreted = interpret_upper_only_rhs_ranging(
            row_status=status,
            row_value=float(item.row_value),
            row_dual=float(item.row_dual),
            raw_bound_down=float(item.fresh_basis_cap_lower) * budget,
            raw_bound_up=float(item.fresh_basis_cap_upper) * budget,
            domain_upper=budget,
            basic_dual_tolerance=dual_tol,
        )
        effective_lower = float(interpreted.effective_rhs_lower / budget)
        effective_upper = float(interpreted.effective_rhs_upper / budget)
        cap = float(item.point_cap)
        raw_contained = bool(
            float(item.fresh_basis_cap_lower) <= cap + cap_tol
            and float(item.fresh_basis_cap_upper) >= cap - cap_tol
        )
        corrected_contained = bool(
            effective_lower <= cap + cap_tol and effective_upper >= cap - cap_tol
        )
        if abs(float(item.row_upper) / budget - cap) > cap_tol:
            raise RuntimeError("V2 risk-row upper bound does not equal its normalized cap.")
        if float(item.row_value) > float(item.row_upper) + cap_tol * budget:
            raise RuntimeError("V2 risk-row activity exceeds its upper bound.")
        if status == highspy.HighsBasisStatus.kBasic and abs(float(item.row_dual)) > dual_tol:
            raise RuntimeError("A V2 basic risk row has a nonzero multiplier.")
        if not corrected_contained:
            raise RuntimeError("A status-aware V2 central RHS interval misses its own cap.")
        rows.append(
            {
                "period": str(item.period),
                "point_cap": cap,
                "risk_row_basis_status": str(item.basis_status),
                "risk_row_value_dollars": float(item.row_value),
                "risk_row_upper_dollars": float(item.row_upper),
                "risk_row_slack_dollars": float(item.row_upper - item.row_value),
                "risk_row_dual": float(item.row_dual),
                "v2_reported_domain_clipped_range_lower": float(item.fresh_basis_cap_lower),
                "v2_reported_domain_clipped_range_upper": float(item.fresh_basis_cap_upper),
                "status_aware_rhs_lower": effective_lower,
                "status_aware_rhs_upper": effective_upper,
                "semantic_mode": (
                    "active_upper_rhs_range"
                    if status == highspy.HighsBasisStatus.kUpper
                    else "basic_row_activity_to_domain_upper_ray"
                ),
                "v2_reported_domain_clipped_cap_contained": raw_contained,
                "status_aware_cap_contained": corrected_contained,
            }
        )
    corrected = pd.DataFrame(rows)
    status_counts = corrected["risk_row_basis_status"].value_counts().to_dict()
    if status_counts != {
        "upper": int(expected["central_risk_upper_rows"]),
        "basic": int(expected["central_risk_basic_rows"]),
    }:
        raise RuntimeError(f"V2 central risk-row status census changed: {status_counts}.")
    clipped_failures = int((~corrected["v2_reported_domain_clipped_cap_contained"]).sum())
    if clipped_failures != int(expected["v2_domain_clipped_cap_containment_failures"]):
        raise RuntimeError("V2 domain-clipped cap-containment failure census changed.")
    if int(corrected["status_aware_cap_contained"].sum()) != int(
        expected["corrected_cap_containment_passes"]
    ):
        raise RuntimeError("V3 status-aware cap containment is incomplete.")
    return corrected


def initial_gap_census(
    corrected: pd.DataFrame,
    probes: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Construct and lock every initial support gap to one registered V2 seed."""
    support_lower, support_upper = map(float, config["coverage"]["registered_support"])
    gap_tol = float(config["coverage"]["gap_tolerance"])
    match_tol = float(config["coverage"]["seed_match_tolerance"])
    rows: list[dict[str, Any]] = []
    for period, group in corrected.groupby("period", sort=True):
        intervals = list(
            zip(
                group["status_aware_rhs_lower"].astype(float),
                group["status_aware_rhs_upper"].astype(float),
                strict=True,
            )
        )
        gaps = support_gaps(
            intervals,
            support_lower=support_lower,
            support_upper=support_upper,
            tolerance=gap_tol,
        )
        left_probes = probes.loc[
            probes["period"].eq(period) & probes["probe_side"].eq("left"),
            ["point_cap", "seed_cap", "seed_expected_objective", "seed_weighted_point_score"],
        ].drop_duplicates(["point_cap", "seed_cap"])
        for index, (left, right) in enumerate(gaps, start=1):
            midpoint = float((left + right) / 2.0)
            distances = (left_probes["seed_cap"].astype(float) - midpoint).abs()
            if distances.empty:
                raise RuntimeError(f"No registered V2 left seed is available for {period}.")
            minimum = float(distances.min())
            matched = left_probes.loc[distances.le(minimum + np.finfo(float).eps)]
            if minimum > match_tol or len(matched) != 1:
                raise RuntimeError(f"V2 gap midpoint has no unique registered seed: {period}.")
            seed = matched.iloc[0]
            seed_cap = float(seed["seed_cap"])
            if not left < seed_cap < right:
                raise RuntimeError("A registered V2 gap seed is not strictly inside its gap.")
            rows.append(
                {
                    "period": str(period),
                    "gap_index": index,
                    "target_gap_lower": float(left),
                    "target_gap_upper": float(right),
                    "target_gap_width": float(right - left),
                    "target_gap_midpoint": midpoint,
                    "registered_seed_cap": seed_cap,
                    "seed_midpoint_match_distance": minimum,
                    "registered_right_breakpoint_cap": float(seed["point_cap"]),
                    "v2_seed_expected_objective": float(seed["seed_expected_objective"]),
                    "v2_seed_weighted_point_score": float(seed["seed_weighted_point_score"]),
                }
            )
    census = pd.DataFrame(rows)
    expected = int(config["v2_source"]["expected"]["initial_positive_gaps"])
    unique_period_seeds = census[["period", "registered_seed_cap"]].drop_duplicates()
    if len(census) != expected or len(unique_period_seeds) != expected:
        raise RuntimeError("V3 initial gap or unique seed census changed.")
    if float(census["seed_midpoint_match_distance"].max()) > match_tol:
        raise RuntimeError("A V3 gap midpoint does not match its registered V2 seed.")
    return census


def _load_decision_base(
    config: Mapping[str, Any],
    v2_summary: Mapping[str, Any],
    *,
    repo_root: Path,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any], Path]:
    """Reconstruct the exact V2 outcome-free decision base for 196 seed solves."""
    v2_config = v2.load_config(_frozen_v2_config_path(v2_summary, repo_root=repo_root))
    inherited_allowlist = list(v2_config["source_ingest"]["allowed_raw_columns"])
    locked_allowlist = list(config["source_ingest"]["allowed_raw_columns"])
    if inherited_allowlist != locked_allowlist:
        raise RuntimeError("V3 raw-column allowlist differs from the frozen V2 allowlist.")
    parent_paths, parent_freeze = verified_parent_artifacts(v2_config, repo_root=repo_root)
    parent_config_path, _ = v2._verify_parent_config_from_freeze(
        v2_config, parent_freeze, repo_root=repo_root
    )
    parent_config = load_v4_config(parent_config_path)
    raw_path = resolve_repo_input(v2_config["source_ingest"]["raw_path"], repo_root=repo_root)
    base = load_outcome_free_decision_base(
        scores_path=parent_paths["scores"],
        raw_path=raw_path,
        config=v2_config,
    )
    forbidden_tokens = tuple(
        str(token).casefold() for token in config["source_ingest"]["forbidden_tokens"]
    )
    forbidden_columns = [
        str(column)
        for column in base.columns
        if any(token in str(column).casefold() for token in forbidden_tokens)
    ]
    if forbidden_columns:
        raise RuntimeError(
            f"V3 reconstructed base contains forbidden columns: {forbidden_columns}."
        )
    return base, parent_config, parent_freeze, raw_path


def run_gap_seed_audit(
    gap_census: pd.DataFrame,
    base: pd.DataFrame,
    *,
    parent_config: Mapping[str, Any],
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Solve and fully audit every registered V2 gap midpoint in a fresh session."""
    months = dict(monthly_frames(base, "primary_oot"))
    if len(months) != int(config["v2_source"]["expected"]["periods"]):
        raise RuntimeError("Primary monthly decision-panel census changed.")
    budget = float(parent_config["policy"]["budget"])
    if budget != float(config["rhs_semantics"]["budget_dollars"]):
        raise RuntimeError("V3 inherited budget differs from its locked semantic scale.")
    tolerances = config["tolerances"]
    cap_tol = float(config["coverage"]["cap_containment_tolerance"])
    gap_tol = float(config["coverage"]["targeted_gap_coverage_tolerance"])
    diagnostics: list[dict[str, Any]] = []
    row_rows: list[dict[str, Any]] = []
    flag_rows: list[dict[str, Any]] = []
    for ordinal, gap in enumerate(gap_census.itertuples(index=False), start=1):
        if ordinal == 1 or ordinal % 25 == 0 or ordinal == len(gap_census):
            logger.info("RHS recovery V3 gap seed {}/196: {}", ordinal, gap.period)
        month = months[str(gap.period)]
        point = month["pd_point"].to_numpy(dtype=float)
        objective = expected_objective_coefficients(
            point,
            month["contractual_rate"].to_numpy(dtype=float),
            lgd=float(parent_config["payoff"]["lgd"]),
        )
        column_names = tuple(month["id"].astype("string").astype(str))
        row_names = v2._row_names(month)
        session = v2._new_session(
            month,
            point=point,
            objective=objective,
            parent_config=parent_config,
            audit_config=config,
        )
        seed_cap = float(gap.registered_seed_cap)
        solution = session.solve(seed_cap)
        audit = audit_full_basis(
            session,
            solution,
            dual_absolute_tolerance=float(tolerances["dual_near_zero_scaled_absolute"]),
            dual_relative_tolerance=float(tolerances["dual_near_zero_relative"]),
            primal_tolerance=float(tolerances["primal_degeneracy"]),
            column_names=column_names,
            row_names=row_names,
        )
        feasibility = v2._policy_feasibility_fields(audit, budget=budget)
        raw = session.solver.getSolution()
        risk_index = int(session.risk_row)
        risk_status = basis_status_name(session.solver.getBasis().row_status[risk_index])
        risk_value = float(raw.row_value[risk_index])
        risk_upper = float(session.solver.getLp().row_upper_[risk_index])
        risk_dual = float(raw.row_dual[risk_index])
        if risk_status == "basic" and abs(risk_dual) > float(tolerances["basic_row_dual"]):
            raise RuntimeError("A V3 gap-seed basic risk row has a nonzero multiplier.")
        cap_contained = bool(
            solution.basis_cap_lower <= seed_cap + cap_tol
            and solution.basis_cap_upper >= seed_cap - cap_tol
        )
        if not cap_contained:
            raise RuntimeError("A V3 gap-seed effective RHS range misses its own cap.")
        target_covered = bool(
            solution.basis_cap_lower <= float(gap.target_gap_lower) + gap_tol
            and solution.basis_cap_upper >= float(gap.target_gap_upper) - gap_tol
        )
        objective_difference = float(
            solution.objective_value - float(gap.v2_seed_expected_objective)
        )
        point_difference = float(
            solution.weighted_point_score - float(gap.v2_seed_weighted_point_score)
        )
        diagnostics.append(
            {
                **gap._asdict(),
                "risk_row_basis_status": risk_status,
                "risk_row_value_dollars": risk_value,
                "risk_row_upper_dollars": risk_upper,
                "risk_row_slack_dollars": float(risk_upper - risk_value),
                "risk_row_dual": risk_dual,
                "reported_activity_range_lower": float(solution.basis_activity_lower),
                "reported_activity_range_upper": float(solution.basis_activity_upper),
                "status_aware_rhs_lower": float(solution.basis_cap_lower),
                "status_aware_rhs_upper": float(solution.basis_cap_upper),
                "status_aware_cap_contained": cap_contained,
                "target_gap_covered": target_covered,
                "expected_objective": float(solution.objective_value),
                "weighted_point_score": float(solution.weighted_point_score),
                "v2_seed_expected_objective_difference": objective_difference,
                "v2_seed_weighted_point_difference": point_difference,
                "solver_run_time_seconds": float(session.solver.getRunTime()),
                **feasibility,
                **audit.summary,
            }
        )
        prefix = {
            "period": str(gap.period),
            "gap_index": int(gap.gap_index),
            "registered_seed_cap": seed_cap,
            "target_gap_lower": float(gap.target_gap_lower),
            "target_gap_upper": float(gap.target_gap_upper),
        }
        row_rows.extend({**prefix, **item} for item in audit.row_details)
        flag_rows.extend({**prefix, **item} for item in audit.flagged_nonbasic)
    diagnostic_frame = pd.DataFrame(diagnostics)
    row_frame = pd.DataFrame(row_rows)
    flag_columns = [
        "period",
        "gap_index",
        "registered_seed_cap",
        "target_gap_lower",
        "target_gap_upper",
        *v2.FLAG_COLUMNS[4:],
    ]
    flag_frame = pd.DataFrame(flag_rows, columns=flag_columns)
    return diagnostic_frame, row_frame, flag_frame


def coverage_by_period(
    corrected: pd.DataFrame,
    gap_diagnostics: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Report initial and final connected support coverage for all 15 months."""
    lower, upper = map(float, config["coverage"]["registered_support"])
    tolerance = float(config["coverage"]["gap_tolerance"])
    rows: list[dict[str, Any]] = []
    for period, central in corrected.groupby("period", sort=True):
        central_intervals = list(
            zip(
                central["status_aware_rhs_lower"].astype(float),
                central["status_aware_rhs_upper"].astype(float),
                strict=True,
            )
        )
        seeds = gap_diagnostics.loc[gap_diagnostics["period"].eq(period)]
        seed_intervals = list(
            zip(
                seeds["status_aware_rhs_lower"].astype(float),
                seeds["status_aware_rhs_upper"].astype(float),
                strict=True,
            )
        )
        initial_merged = merge_intervals(central_intervals, tolerance=tolerance)
        final_merged = merge_intervals([*central_intervals, *seed_intervals], tolerance=tolerance)
        initial_gaps = support_gaps(
            initial_merged,
            support_lower=lower,
            support_upper=upper,
            tolerance=tolerance,
        )
        final_gaps = support_gaps(
            final_merged,
            support_lower=lower,
            support_upper=upper,
            tolerance=tolerance,
        )
        rows.append(
            {
                "period": str(period),
                "support_lower": lower,
                "support_upper": upper,
                "corrected_central_interval_rows": int(len(central_intervals)),
                "registered_gap_seed_rows": int(len(seed_intervals)),
                "initial_merged_segments": int(len(initial_merged)),
                "initial_positive_gaps": int(len(initial_gaps)),
                "initial_maximum_positive_gap": float(
                    max((right - left for left, right in initial_gaps), default=0.0)
                ),
                "initial_total_uncovered_width": float(
                    sum(right - left for left, right in initial_gaps)
                ),
                "final_merged_segments": int(len(final_merged)),
                "final_positive_gaps": int(len(final_gaps)),
                "final_maximum_positive_gap": float(
                    max((right - left for left, right in final_gaps), default=0.0)
                ),
                "final_total_uncovered_width": float(
                    sum(right - left for left, right in final_gaps)
                ),
                "all_targeted_gaps_covered": bool(seeds["target_gap_covered"].all()),
                "registered_support_covered": bool(not final_gaps),
            }
        )
    return pd.DataFrame(rows)


def _validate_gap_basis_contract(
    diagnostics: pd.DataFrame, *, config: Mapping[str, Any]
) -> dict[str, Any]:
    tolerances = config["tolerances"]
    expected = int(config["v2_source"]["expected"]["unique_gap_seed_solves"])
    if len(diagnostics) != expected:
        raise RuntimeError("V3 gap-seed diagnostic census is incomplete.")
    if not bool(
        diagnostics[["basis_valid", "basis_dimension_valid", "value_valid", "dual_valid"]]
        .astype(bool)
        .all(axis=None)
    ):
        raise RuntimeError("A V3 gap-seed basis or solution is invalid.")
    if bool(
        diagnostics[["unsupported_nonbasic_columns", "unsupported_movable_nonbasic_rows"]]
        .gt(0)
        .any(axis=None)
    ):
        raise RuntimeError("A V3 gap-seed basis has an unsupported nonbasic status.")
    max_dual = float(diagnostics["maximum_scaled_dual_sign_violation"].max())
    if max_dual > float(tolerances["dual_sign_scaled_violation"]):
        raise RuntimeError("A V3 gap-seed basis violates the registered dual sign contract.")
    max_objective = float(
        diagnostics[
            [
                "solution_to_raw_solver_objective_error",
                "raw_objective_internal_reconciliation_error",
            ]
        ]
        .abs()
        .max(axis=None)
    )
    if max_objective > float(tolerances["objective_reconciliation_dollars"]):
        raise RuntimeError("A V3 gap-seed objective fails reconciliation.")
    max_policy = float(diagnostics["maximum_normalized_policy_constraint_violation"].max())
    if max_policy > float(tolerances["policy_constraint_normalized"]):
        raise RuntimeError("A V3 gap-seed solution violates a policy constraint.")
    max_v2_objective = float(diagnostics["v2_seed_expected_objective_difference"].abs().max())
    max_v2_point = float(diagnostics["v2_seed_weighted_point_difference"].abs().max())
    if max_v2_objective > float(tolerances["objective_reconciliation_dollars"]):
        raise RuntimeError("A V3 gap seed does not reproduce its V2 stored objective.")
    if max_v2_point > float(tolerances["row_activity_normalized"]):
        raise RuntimeError("A V3 gap seed does not reproduce its V2 stored point score.")
    return {
        "rows": int(len(diagnostics)),
        "basis_contract_passed": True,
        "maximum_scaled_dual_sign_violation": max_dual,
        "maximum_absolute_objective_reconciliation_error": max_objective,
        "maximum_normalized_policy_constraint_violation": max_policy,
        "maximum_v2_seed_objective_difference": max_v2_objective,
        "maximum_v2_seed_weighted_point_difference": max_v2_point,
        "scale_aware_warning_bases": int(diagnostics["near_zero_nonbasic_total"].gt(0).sum()),
        "scale_aware_warning_entities": int(diagnostics["near_zero_nonbasic_total"].sum()),
    }


def _correct_lateral_comparisons(
    comparisons: pd.DataFrame,
    faces: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    corrected = v2._reconcile_breakpoint_comparisons(
        comparisons,
        faces,
        tolerances=config["tolerances"],
    )
    allocation_differs = corrected["maximum_pairwise_allocation_distance"].gt(
        float(config["tolerances"]["allocation_distance"])
    )
    cooccurs = corrected["allocation_difference_cooccurs_with_same_cap_epsilon_mobility"].astype(
        bool
    )
    if bool((cooccurs & ~allocation_differs).any()):
        raise RuntimeError(
            "Corrected lateral cooccurrence exists without an allocation difference."
        )
    return corrected


def _result_summary(
    *,
    corrected: pd.DataFrame,
    gap_census: pd.DataFrame,
    gap_diagnostics: pd.DataFrame,
    gap_flags: pd.DataFrame,
    coverage: pd.DataFrame,
    lateral: pd.DataFrame,
    faces: pd.DataFrame,
    gap_contract: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    rhs_passed = bool(
        corrected["status_aware_cap_contained"].all()
        and gap_diagnostics["status_aware_cap_contained"].all()
        and gap_diagnostics["target_gap_covered"].all()
        and coverage["registered_support_covered"].all()
        and int(coverage["final_positive_gaps"].sum()) == 0
    )
    existing_warning_targets = int(len(faces))
    new_warning_entities = int(len(gap_flags))
    uniqueness_blocked = bool(existing_warning_targets or new_warning_entities)
    allocation_differs = lateral["maximum_pairwise_allocation_distance"].gt(
        float(config["tolerances"]["allocation_distance"])
    )
    cooccurs = lateral["allocation_difference_cooccurs_with_same_cap_epsilon_mobility"].astype(bool)
    without = lateral["allocation_difference_without_same_cap_epsilon_mobility"].astype(bool)
    maximum_face_mobility = float(faces["normalized_mobility"].max() if not faces.empty else 0.0)
    return {
        "certification_status": (
            "rhs_support_coverage_recovered_numerical_uniqueness_claim_blocked"
            if rhs_passed and uniqueness_blocked
            else (
                "rhs_support_coverage_recovered_no_exact_uniqueness_claim"
                if rhs_passed
                else "rhs_support_coverage_recovery_failed_claim_blocked"
            )
        ),
        "rhs_support_coverage_gate_passed": rhs_passed,
        "strict_numerical_uniqueness_gate_passed": False,
        "exact_symbolic_optimal_face_claim_made": False,
        "global_optimal_face_diameter_claim_made": False,
        "continuous_joint_frontier_uniqueness_claim_made": False,
        "allocation_continuity_claim_made": False,
        "status_aware_central": {
            "rows": int(len(corrected)),
            "upper_rows": int(corrected["risk_row_basis_status"].eq("upper").sum()),
            "basic_rows": int(corrected["risk_row_basis_status"].eq("basic").sum()),
            "v2_reported_domain_clipped_cap_containment_failures": int(
                (~corrected["v2_reported_domain_clipped_cap_contained"]).sum()
            ),
            "corrected_cap_containment_passes": int(corrected["status_aware_cap_contained"].sum()),
            "maximum_corrected_cap_containment_violation": float(
                max(
                    (corrected["status_aware_rhs_lower"] - corrected["point_cap"])
                    .clip(lower=0.0)
                    .max(),
                    (corrected["point_cap"] - corrected["status_aware_rhs_upper"])
                    .clip(lower=0.0)
                    .max(),
                )
            ),
        },
        "gap_replay": {
            **dict(gap_contract),
            "initial_gap_rows": int(len(gap_census)),
            "initial_gap_months": int(gap_census["period"].nunique()),
            "maximum_initial_gap": float(gap_census["target_gap_width"].max()),
            "maximum_seed_midpoint_match_distance": float(
                gap_census["seed_midpoint_match_distance"].max()
            ),
            "targeted_gap_coverage_passes": int(gap_diagnostics["target_gap_covered"].sum()),
            "final_covered_periods": int(coverage["registered_support_covered"].sum()),
            "final_positive_gaps": int(coverage["final_positive_gaps"].sum()),
            "maximum_final_positive_gap": float(coverage["final_maximum_positive_gap"].max()),
        },
        "lateral_reporting_correction": {
            "breakpoint_rows": int(len(lateral)),
            "allocation_difference_rows": int(allocation_differs.sum()),
            "corrected_same_cap_mobility_cooccurrence_rows": int(cooccurs.sum()),
            "allocation_difference_without_same_cap_mobility_rows": int(without.sum()),
            "maximum_pairwise_allocation_distance": float(
                lateral["maximum_pairwise_allocation_distance"].max()
            ),
            "v2_reported_cooccurrence_rows": 7,
        },
        "epsilon_conditioning_boundary": {
            "v2_warning_targets": existing_warning_targets,
            "v3_gap_seed_warning_entities": new_warning_entities,
            "maximum_v2_normalized_coordinate_mobility": maximum_face_mobility,
            "maximum_v2_coordinate_exposure_mobility_dollars": float(
                maximum_face_mobility * config["rhs_semantics"]["budget_dollars"]
            ),
            "epsilon_mobility_is_exact_alternate_optimum": False,
            "warnings_block_numerical_uniqueness_promotion": uniqueness_blocked,
        },
        "scientific_stop_flags": {
            "rhs_support_coverage_failure": not rhs_passed,
            "scale_aware_warning_blocks_uniqueness": uniqueness_blocked,
        },
    }


def run_audit(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Execute the tagged V3 recovery and return its deterministic summary."""
    started_at = utc_now_iso()
    started_counter = time.perf_counter()
    resolved_config = _resolve_locked_config_path(config_path, repo_root=repo_root)
    config = load_config(resolved_config)
    protocol_commit = require_clean_tagged_head(repo_root, str(config["protocol_tag"]))
    preflight_output_paths(config, repo_root=repo_root)
    initial_git = git_provenance(repo_root)
    implementation_start = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=repo_root,
    )
    solver_identity = v2._solver_identity(config)
    v2_summary, source_paths = verify_v2_source(config, repo_root=repo_root)
    central = pd.read_parquet(source_paths["central_basis_diagnostics"])
    row_details = pd.read_parquet(source_paths["row_slack_details"])
    probes = pd.read_parquet(source_paths["lateral_probe_diagnostics"])
    comparisons = pd.read_parquet(source_paths["breakpoint_comparisons"])
    faces = pd.read_parquet(source_paths["optimal_face_ranges"])
    expected = config["v2_source"]["expected"]
    actual = {
        "central_rows": len(central),
        "periods": central["period"].nunique(),
        "v2_lateral_probe_rows": len(probes),
        "v2_breakpoint_rows": len(comparisons),
        "v2_optimal_face_targets": len(faces),
    }
    if any(int(actual[key]) != int(expected[key]) for key in actual):
        raise RuntimeError(f"V2 source census drifted: {actual}.")

    corrected = corrected_central_rhs_ranges(central, row_details, config=config)
    gaps = initial_gap_census(corrected, probes, config=config)
    base, parent_config, parent_freeze, raw_path = _load_decision_base(
        config, v2_summary, repo_root=repo_root
    )
    gap_diagnostics, gap_rows, gap_flags = run_gap_seed_audit(
        gaps,
        base,
        parent_config=parent_config,
        config=config,
    )
    gap_contract = _validate_gap_basis_contract(gap_diagnostics, config=config)
    coverage = coverage_by_period(corrected, gap_diagnostics, config=config)
    lateral = _correct_lateral_comparisons(comparisons, faces, config=config)
    result_summary = _result_summary(
        corrected=corrected,
        gap_census=gaps,
        gap_diagnostics=gap_diagnostics,
        gap_flags=gap_flags,
        coverage=coverage,
        lateral=lateral,
        faces=faces,
        gap_contract=gap_contract,
        config=config,
    )
    implementation_end = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=repo_root,
    )
    if implementation_end != implementation_start:
        raise RuntimeError("RHS recovery V3 implementation changed during execution.")

    paths = prepare_output_paths(config, repo_root=repo_root)
    protocol_freeze = atomic_write_json(
        paths.model_dir / "protocol_freeze.json",
        {
            "schema_version": str(config["schema_version"]),
            "status": "outcome_free_rhs_semantics_recovery_v3_frozen",
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "hypothesis": str(config["hypothesis"]),
            "claim_boundary": dict(config["claim_boundary"]),
            "outcome_columns_passed": [],
            "v2_summary": relative_artifact_descriptor(
                resolve_repo_input(
                    str(config["v2_source"]["deterministic_summary"]["path"]),
                    repo_root=repo_root,
                ),
                repo_root=repo_root,
            ),
            "v2_protocol_commit": str(v2_summary["protocol_commit"]),
            "parent_outcome_free_artifacts": parent_freeze["outcome_free_artifacts"],
            "solver_contract": solver_identity,
            "implementation_provenance": implementation_start,
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    frames = {
        "corrected_central_rhs_ranges": corrected,
        "gap_fill_basis_diagnostics": gap_diagnostics,
        "gap_fill_row_slack_details": gap_rows,
        "gap_fill_flagged_nonbasic_variables": gap_flags,
        "corrected_rhs_coverage": coverage,
        "corrected_lateral_comparisons": lateral,
    }
    output = config["output"]
    written: dict[Path, pd.DataFrame] = {}
    for key, frame in frames.items():
        path = atomic_write_parquet(frame, paths.data_dir / str(output[key]), index=False)
        written[path] = frame
    artifacts = {
        descriptor["path"]: descriptor
        for descriptor in [
            relative_artifact_descriptor(protocol_freeze, repo_root=repo_root),
            *(relative_artifact_descriptor(path, repo_root=repo_root) for path in written),
        ]
    }
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_outcome_free_rhs_semantics_recovery_v3",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "hypothesis": str(config["hypothesis"]),
        "claim_boundary": dict(config["claim_boundary"]),
        "outcome_columns_passed": [],
        "solver_contract": solver_identity,
        "results": result_summary,
        "v2_source_summary": relative_artifact_descriptor(
            resolve_repo_input(
                str(config["v2_source"]["deterministic_summary"]["path"]),
                repo_root=repo_root,
            ),
            repo_root=repo_root,
        ),
        "v2_source_artifacts": v2_summary["artifacts"],
        "raw_source": relative_artifact_descriptor(raw_path, repo_root=repo_root),
        "implementation_provenance": implementation_start,
        "artifacts": artifacts,
        "schemas": {
            relative_artifact_descriptor(path, repo_root=repo_root)["path"]: dataframe_schema(frame)
            for path, frame in written.items()
        },
        "selection": {
            "cap": None,
            "basis": None,
            "gap": "all_locked_initial_positive_gaps",
            "policy": None,
            "outcome": None,
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    summary_path = atomic_write_json(paths.model_dir / str(output["deterministic_result"]), summary)
    atomic_write_json(
        paths.model_dir / str(output["execution_receipt"]),
        {
            "run_tag": str(config["run_tag"]),
            "started_at_utc": started_at,
            "completed_at_utc": utc_now_iso(),
            "runtime_seconds": float(time.perf_counter() - started_counter),
            "initial_git": initial_git,
            "final_git": git_provenance(repo_root),
            "environment": environment_provenance(repo_root),
            "solver_contract": solver_identity,
            "deterministic_summary": relative_artifact_descriptor(
                summary_path, repo_root=repo_root
            ),
        },
    )
    logger.info("RHS semantics recovery V3 complete: {}", summary_path)
    return summary_path


def main(argv: Sequence[str] | None = None) -> None:
    """Run the CLI entry point."""
    args = parse_args(argv)
    run_audit(config_path=args.config)


if __name__ == "__main__":
    main()
