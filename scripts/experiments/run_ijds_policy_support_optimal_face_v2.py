"""Run the locked outcome-free IJDS full-basis and optimal-face V2 audit."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
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

from src.evaluation.standardized_credit_payoff import (  # noqa: E402
    expected_objective_coefficients,
)
from src.ijds_audit.config import load_v4_config  # noqa: E402
from src.ijds_audit.optimal_face_certification import (  # noqa: E402
    FullBasisAudit,
    audit_full_basis,
    breakpoint_probe_plan,
    normalized_exposure_distance,
    optimal_face_range,
)
from src.ijds_audit.portfolio import PointPortfolioSession  # noqa: E402
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
    "configs/experiments/ijds_policy_support_optimal_face_2026-07-21_v2.yaml"
)
DEFAULT_CONFIG_PATH = ROOT / CONFIG_RELATIVE_PATH
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
IMPLEMENTATION_PATHS = (
    Path("docs/research/ijds_policy_support_optimal_face_v2_protocol_2026-07-21.md"),
    Path("scripts/experiments/run_ijds_policy_support_optimal_face_v2.py"),
    Path("src/evaluation/standardized_credit_payoff.py"),
    Path("src/ijds_audit/config.py"),
    Path("src/ijds_audit/optimal_face_certification.py"),
    Path("src/ijds_audit/portfolio.py"),
    Path("src/ijds_audit/protocol.py"),
    Path("src/ijds_challengers/archive.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("tests/test_ijds_policy_support_optimal_face_v2.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)

COLUMN_REGISTRY_COLUMNS = (
    "period",
    "column_index",
    "candidate_id",
    "loan_amount",
    "objective_cost",
    "column_lower",
    "column_upper",
    "dual_reference_scale",
    "near_zero_threshold",
)
ROW_DETAIL_COLUMNS = (
    "period",
    "point_cap",
    "solve_origin",
    "seed_cap",
    "row_index",
    "row_name",
    "basis_status",
    "row_value",
    "row_lower",
    "row_upper",
    "row_dual",
    "absolute_row_dual",
    "row_dual_reference_scale",
    "row_near_zero_threshold",
    "is_equality",
    "is_nonbasic",
    "is_movable_nonbasic",
    "is_near_zero_nonbasic",
    "lower_bound_violation",
    "upper_bound_violation",
)
FLAG_COLUMNS = (
    "period",
    "point_cap",
    "solve_origin",
    "seed_cap",
    "variable_kind",
    "variable_index",
    "variable_name",
    "basis_status",
    "base_value",
    "lower_bound",
    "upper_bound",
    "dual_or_reduced_cost",
    "absolute_dual_or_reduced_cost",
    "scaled_absolute_dual_or_reduced_cost",
    "dual_reference_scale",
    "near_zero_threshold",
    "objective_cost",
)
FACE_COLUMNS = (
    "period",
    "point_cap",
    "variable_kind",
    "variable_index",
    "variable_name",
    "warning_origins",
    "base_value",
    "minimum_value",
    "maximum_value",
    "raw_value_range",
    "value_range",
    "range_order_violation",
    "base_below_minimum_violation",
    "base_above_maximum_violation",
    "maximum_range_consistency_violation",
    "normalized_mobility",
    "raw_primary_objective",
    "raw_internal_primary_objective",
    "raw_internal_primary_objective_difference",
    "solution_to_raw_primary_objective_difference",
    "objective_face_epsilon",
    "minimum_primary_objective",
    "maximum_primary_objective",
    "minimum_primary_objective_difference",
    "maximum_primary_objective_difference",
    "minimum_solver_run_time_seconds",
    "maximum_solver_run_time_seconds",
    "minimum_maximum_column_bound_violation",
    "minimum_maximum_row_bound_violation",
    "maximum_maximum_column_bound_violation",
    "maximum_maximum_row_bound_violation",
    "primary_objective_reconciliation_passed",
    "objective_band_passed",
    "face_range_consistency_passed",
    "epsilon_near_optimal_mobility_detected",
)

FROZEN_POINT_RULES = (
    "point_cap_frontier",
    "c0_same_numeric_cap",
    "c1_development_mean",
    "c2_contemporaneous",
)
FROZEN_SOURCE_FIELDS = (
    "period",
    "window_id",
    "candidate_id",
    "comparator_rule",
    "policy_label",
    "paired_policy_id",
    "frontier_cap",
)
DATA_OUTPUT_KEYS = (
    "central_basis_diagnostics",
    "frozen_allocation_reconciliation",
    "fresh_rhs_basis_range_coverage",
    "column_registry",
    "row_slack_details",
    "lateral_probe_diagnostics",
    "breakpoint_comparisons",
    "flagged_nonbasic_variables",
    "optimal_face_ranges",
)
MODEL_OUTPUT_KEYS = ("deterministic_result", "execution_receipt")


@dataclass(frozen=True)
class FrozenAllocationVector:
    """One canonical positive-exposure vector from the V4 outcome-free freeze."""

    ids: tuple[str, ...]
    exposure: np.ndarray
    pd_point: np.ndarray
    expected_payoff_rate: np.ndarray
    source_key_count: int


@dataclass(frozen=True)
class FrozenAllocationReference:
    """Complete V1-cap mapping into the hash-verified V4 allocation freeze."""

    vectors: dict[tuple[str, float], FrozenAllocationVector]
    diagnostics: dict[str, Any]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the V2 audit CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    return parser.parse_args(argv)


def _resolve_locked_config_path(config_path: Path, *, repo_root: Path) -> Path:
    """Require execution from the one tracked V2 config location."""
    resolved = resolve_repo_input(config_path, repo_root=repo_root)
    expected = (repo_root / CONFIG_RELATIVE_PATH).resolve()
    if resolved != expected:
        raise RuntimeError(f"V2 execution requires the locked config at {CONFIG_RELATIVE_PATH}.")
    return resolved


def load_config(path: Path) -> dict[str, Any]:
    """Load and fail closed on the exact V2 protocol contract."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Optimal-face V2 config must be a YAML mapping.")
    required = {
        "schema_version",
        "protocol_status",
        "protocol_tag",
        "run_tag",
        "hypothesis",
        "parent",
        "parent_v1_audit",
        "source_ingest",
        "frontier",
        "census",
        "frozen_allocation_reconciliation",
        "rhs_basis_range_coverage",
        "solver",
        "tolerances",
        "optimal_face",
        "claim_boundary",
        "stop_rules",
        "output",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise ValueError(f"Optimal-face V2 config is missing sections: {missing}.")
    if payload["schema_version"] != "2026-07-21.1":
        raise ValueError("Optimal-face V2 schema version changed.")
    if not isinstance(payload["hypothesis"], str) or not payload["hypothesis"].strip():
        raise ValueError("Optimal-face V2 hypothesis must be a nonempty string.")
    if (
        payload["protocol_status"]
        != "locked_retrospective_outcome_free_optimal_face_audit_v2_before_execution"
    ):
        raise ValueError("Optimal-face V2 protocol is not locked.")
    expected_run = "ijds-policy-support-optimal-face-audit-2026-07-21-v2"
    expected_tag = f"protocol/{expected_run}"
    if payload["run_tag"] != expected_run or payload["protocol_tag"] != expected_tag:
        raise ValueError("Optimal-face V2 run or protocol identity changed.")
    source = payload["source_ingest"]
    if source["allowed_raw_columns"] != ["id", "loan_amnt", "int_rate", "purpose"]:
        raise ValueError("Optimal-face V2 raw-column allowlist changed.")
    forbidden = tuple(str(value).casefold() for value in source["forbidden_tokens"])
    if not forbidden or any(
        token in str(column).casefold()
        for column in source["allowed_raw_columns"]
        for token in forbidden
    ):
        raise ValueError("Optimal-face V2 allowlist contains an outcome-like name.")
    census = payload["census"]
    expected_counts = {
        "expected_rows": 7_297,
        "expected_periods": 15,
        "expected_basis_breakpoints": 2_952,
        "expected_lateral_probe_rows": 5_874,
    }
    if any(int(census.get(field, -1)) != value for field, value in expected_counts.items()):
        raise ValueError("Optimal-face V2 census contract changed.")
    if (
        census.get("key_columns") != ["period", "point_cap"]
        or census.get("breakpoint_column") != "is_period_basis_breakpoint"
        or census.get("complete_census_required") is not True
    ):
        raise ValueError("Optimal-face V2 V1-census key contract changed.")
    expected_value_columns = [
        "expected_objective",
        "weighted_point_score",
        "basis_cap_lower",
        "basis_cap_upper",
        "is_development_support_lower",
        "is_development_support_upper",
    ]
    if census.get("required_value_columns") != expected_value_columns:
        raise ValueError("Optimal-face V2 V1-census value-column contract changed.")
    frozen = payload["frozen_allocation_reconciliation"]
    if frozen.get("comparator_rules") != list(FROZEN_POINT_RULES):
        raise ValueError("Frozen point-allocation rule priority changed.")
    if (
        frozen.get("parent_artifact_key") != "allocations"
        or frozen.get("parent_solve_records_key") != "solve_records"
        or frozen.get("role") != "primary_oot"
        or int(frozen.get("expected_mapped_v1_caps", -1)) != 7_297
        or frozen.get("source_identity_columns") != list(FROZEN_SOURCE_FIELDS)
        or frozen.get("canonical_collapse_unit") != "complete_source_vector"
        or frozen.get("absent_candidate_ids_are_zero_exposure") is not True
        or frozen.get("positive_exposure_rows_only") is not True
        or frozen.get("comparator_rules_are_deterministic_priority_order") is not True
        or frozen.get("cap_match_method") != "nearest_within_period"
    ):
        raise ValueError("Frozen allocation reconciliation contract changed.")
    if (
        float(frozen.get("cap_match_tolerance", -1.0)) != 1.0e-10
        or float(frozen.get("duplicate_exposure_tolerance_dollars", -1.0)) != 1.0e-7
        or float(frozen.get("coefficient_tolerance", -1.0)) != 1.0e-12
    ):
        raise ValueError("Frozen allocation reconciliation tolerances changed.")
    coverage = payload["rhs_basis_range_coverage"]
    if (
        coverage.get("broad_support") != [0.05, 0.12]
        or coverage.get("require_v1_basis_identity") is not False
        or coverage.get("include_complete_development_support_hull") is not True
        or coverage.get("persist_raw_uncollapsed_gap") is not True
        or float(coverage.get("gap_tolerance", -1.0)) != 1.0e-10
    ):
        raise ValueError("Fresh RHS basis-range coverage contract changed.")
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
        "persist_get_run_time": True,
        "session_scope": (
            "central_by_month_and_each_bilateral_probe_in_a_fresh_midpoint_to_cap_session"
        ),
    }
    if any(solver.get(field) != value for field, value in expected_solver.items()):
        raise ValueError("Optimal-face V2 HiGHS contract changed.")
    if solver.get("zero_all_clocks_required") is not False:
        raise ValueError("zeroAllClocks cannot be required under highspy 1.15.1.")
    if solver.get("deterministic_candidate_order") != ["issue_d", "id"]:
        raise ValueError("Optimal-face V2 candidate ordering changed.")
    tolerances = payload["tolerances"]
    if any(float(value) <= 0.0 for value in tolerances.values()):
        raise ValueError("Optimal-face V2 tolerances must be positive.")
    face = payload["optimal_face"]
    if face.get("trigger") != (
        "nonbasic_standard_variable_scaled_absolute_dual_at_most_"
        "scaled_absolute_plus_relative_tolerance"
    ):
        raise ValueError("Optimal-face V2 trigger changed.")
    if (
        face.get("column_dual_reference_scale") != "max_j(abs(c_j))"
        or face.get("row_slack_dual_reference_scale") != "max_j(abs(c_j))/max_j(abs(A_ij))"
    ):
        raise ValueError("Optimal-face V2 dual reference scale changed.")
    if face.get("no_untriggered_face_solves") is not True:
        raise ValueError("Untriggered optimal-face solves must remain forbidden.")
    if face.get("no_tie_break_selection") is not True:
        raise ValueError("V2 cannot select a tie-break.")
    if face.get("individual_ranges_do_not_bound_global_l1_face_diameter") is not True:
        raise ValueError("V2 cannot promote coordinate ranges to a global diameter claim.")
    boundary = payload["claim_boundary"]
    if boundary.get("outcome_columns_passed") != []:
        raise ValueError("Optimal-face V2 cannot accept outcomes.")
    required_true = {
        "no_empirical_metric_or_direction",
        "no_policy_or_cap_selection",
        "no_tie_break_selection",
        "no_continuous_joint_frontier_uniqueness",
        "no_universal_comparator_support",
        "no_selected_set_claim",
        "no_exact_symbolic_optimal_face_claim",
        "no_global_optimal_face_diameter_claim",
        "certificate_requires_complete_frozen_allocation_reconciliation",
        "fresh_rhs_basis_range_coverage_at_registered_tolerance_only",
        "no_allocation_continuity_or_seam_conditioning_claim",
        "bilateral_midpoint_probes_are_path_stresses_not_exhaustive_fresh_basis_enumeration",
        "no_symbolic_continuous_frontier_claim",
        "no_historical_extrema_claim_if_freeze_or_rhs_coverage_fails",
    }
    if any(boundary.get(field) is not True for field in required_true):
        raise ValueError("Optimal-face V2 claim boundary changed.")
    replay = payload.get("replay_provenance_context")
    if not isinstance(replay, dict) or replay.get("input_to_this_outcome_free_audit") is not False:
        raise ValueError("Equal-quarter replay provenance cannot become a V2 input.")
    stop = payload["stop_rules"]
    if stop.get("stop_on_unsupported_basis_status") is not False:
        raise ValueError("Unsupported statuses must be retained and claim-gated.")
    if stop.get("claim_gate_on_invalid_or_unsupported_basis") is not True:
        raise ValueError("Invalid or unsupported bases must gate the V2 certificate.")
    if stop.get("claim_gate_on_any_registered_warning_without_global_face_diameter") is not True:
        raise ValueError("Any unresolved warning must gate finite-grid uniqueness.")
    if (
        stop.get("claim_gate_on_allocation_difference_without_same_cap_epsilon_mobility")
        is not True
    ):
        raise ValueError("Lateral allocation differences without same-cap mobility must gate.")
    if (
        stop.get("claim_gate_on_incomplete_or_failed_frozen_allocation_reconciliation") is not True
        or stop.get("claim_gate_on_fresh_rhs_basis_range_coverage_failure") is not True
    ):
        raise ValueError("Freeze reconciliation and fresh RHS coverage must gate the certificate.")
    if stop.get("stop_on_preexisting_output_path") is not True:
        raise ValueError("Preexisting immutable output paths must block execution.")
    output = payload["output"]
    if output.get("immutability") != "hard_no_overwrite_choose_fresh_run_tag":
        raise ValueError("Optimal-face V2 outputs must remain immutable.")
    names: list[str] = []
    for key in (*DATA_OUTPUT_KEYS, *MODEL_OUTPUT_KEYS):
        value = output.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"Optimal-face V2 output {key} must be a filename.")
        filename = Path(value)
        if filename.is_absolute() or filename.name != value or value in {".", ".."}:
            raise ValueError(f"Optimal-face V2 output {key} must be a contained basename.")
        expected_suffix = ".parquet" if key in DATA_OUTPUT_KEYS else ".json"
        if filename.suffix.casefold() != expected_suffix:
            raise ValueError(f"Optimal-face V2 output {key} must end in {expected_suffix}.")
        names.append(value.casefold())
    if len(names) != len(set(names)) or "protocol_freeze.json" in names:
        raise ValueError("Optimal-face V2 output filenames must be distinct.")
    return cast(dict[str, Any], payload)


def prepare_output_paths(config: Mapping[str, Any], *, repo_root: Path = ROOT) -> OutputPaths:
    """Create fresh contained output directories."""
    return prepare_isolated_output_paths(
        dict(config),
        repo_root=repo_root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )


def preflight_output_paths(config: Mapping[str, Any], *, repo_root: Path = ROOT) -> OutputPaths:
    """Validate immutable output targets without creating them."""
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
    existing = [path for path in (paths.data_dir, paths.model_dir) if path.exists()]
    if existing:
        rendered = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            f"Experiment output already exists ({rendered}); choose a fresh run tag."
        )
    return paths


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a JSON object at {path}.")
    return payload


def _verify_descriptor(
    descriptor: Mapping[str, Any],
    *,
    repo_root: Path,
) -> Path:
    path = resolve_repo_input(str(descriptor["path"]), repo_root=repo_root)
    actual = relative_artifact_descriptor(path, repo_root=repo_root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor[field]:
            raise RuntimeError(f"Artifact descriptor mismatch for {field}: {path}.")
    return path


def _verify_parent_config_from_freeze(
    config: Mapping[str, Any],
    parent_freeze: Mapping[str, Any],
    *,
    repo_root: Path,
) -> tuple[Path, dict[str, Any]]:
    """Verify the exact V4 config that defines budget, caps, and LGD."""
    relative = str(config["parent"]["config"])
    provenance = parent_freeze.get("implementation_provenance")
    if not isinstance(provenance, dict):
        raise TypeError("Parent freeze has no implementation provenance mapping.")
    sources = provenance.get("source_files")
    if not isinstance(sources, dict):
        raise TypeError("Parent freeze has no source-file descriptor mapping.")
    descriptor = sources.get(relative)
    if not isinstance(descriptor, dict):
        raise RuntimeError("Parent freeze does not hash-lock its declared V4 config.")
    verified = _verify_descriptor(descriptor, repo_root=repo_root)
    declared = resolve_repo_input(relative, repo_root=repo_root)
    if verified != declared:
        raise RuntimeError("Parent V4 config descriptor resolves to the wrong path.")
    return verified, dict(descriptor)


def _validate_v1_census_frame(
    frame: pd.DataFrame,
    *,
    contract: Mapping[str, Any],
) -> None:
    """Fail early on every V1 census field consumed by the long V2 run."""
    key_columns = [str(value) for value in contract["key_columns"]]
    breakpoint_column = str(contract["breakpoint_column"])
    value_columns = [str(value) for value in contract["required_value_columns"]]
    required = {*key_columns, breakpoint_column, *value_columns}
    if missing := sorted(required.difference(frame.columns)):
        raise RuntimeError(f"V1 cap census is missing columns: {missing}.")

    if frame[key_columns].isna().any().any():
        raise RuntimeError("V1 cap census contains null period-cap keys.")
    period = frame["period"].astype("string")
    if bool(period.str.strip().eq("").any()):
        raise RuntimeError("V1 cap census contains an empty period key.")

    numeric_columns = [
        "point_cap",
        "expected_objective",
        "weighted_point_score",
        "basis_cap_lower",
        "basis_cap_upper",
    ]
    for column in numeric_columns:
        numeric = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
        if numeric.shape != (len(frame),) or not bool(np.isfinite(numeric).all()):
            raise RuntimeError(f"V1 cap census column {column!r} is not finite numeric data.")

    boolean_columns = [
        breakpoint_column,
        "is_development_support_lower",
        "is_development_support_upper",
    ]
    for column in boolean_columns:
        values = frame[column]
        if (
            bool(values.isna().any())
            or not pd.api.types.is_bool_dtype(values.dtype)
            or not bool(values.isin([True, False]).all())
        ):
            raise RuntimeError(f"V1 cap census column {column!r} is not complete Boolean data.")

    for column in ("is_development_support_lower", "is_development_support_upper"):
        per_period = frame.groupby("period", sort=False)[column].any()
        if per_period.empty or not bool(per_period.all()):
            raise RuntimeError(f"V1 cap census lacks {column!r} in at least one period.")


def _load_v1_census(config: Mapping[str, Any], *, repo_root: Path) -> pd.DataFrame:
    parent = config["parent_v1_audit"]
    summary_path = _verify_descriptor(parent["deterministic_summary"], repo_root=repo_root)
    summary = _json(summary_path)
    expected = {
        "status": "complete",
        "run_tag": str(parent["run_tag"]),
        "protocol_tag": str(parent["protocol_tag"]),
        "protocol_commit": str(parent["protocol_commit"]),
    }
    for field, value in expected.items():
        if summary.get(field) != value:
            raise RuntimeError(f"V1 audit summary identity mismatch: {field}.")
    if summary.get("outcome_columns_passed") != []:
        raise RuntimeError("V1 audit summary reports outcome columns.")
    artifacts = summary.get("artifacts")
    if not isinstance(artifacts, dict):
        raise TypeError("V1 audit summary has no artifact mapping.")
    suffix = str(parent["census_artifact_name"])
    matches = [value for key, value in artifacts.items() if str(key).endswith(suffix)]
    if len(matches) != 1 or not isinstance(matches[0], dict):
        raise RuntimeError("V1 audit summary does not identify one cap census artifact.")
    census_path = _verify_descriptor(matches[0], repo_root=repo_root)
    frame = pd.read_parquet(census_path)
    contract = config["census"]
    _validate_v1_census_frame(frame, contract=contract)
    keys = [str(value) for value in contract["key_columns"]]
    if bool(frame.duplicated(keys).any()):
        raise RuntimeError("V1 cap census contains duplicate period-cap keys.")
    actual = {
        "rows": int(len(frame)),
        "periods": int(frame["period"].nunique()),
        "breakpoints": int(frame[str(contract["breakpoint_column"])].sum()),
    }
    expected_actual = {
        "rows": int(contract["expected_rows"]),
        "periods": int(contract["expected_periods"]),
        "breakpoints": int(contract["expected_basis_breakpoints"]),
    }
    if actual != expected_actual:
        raise RuntimeError(f"V1 cap census drifted: {actual}, expected {expected_actual}.")
    return frame.sort_values(["period", "point_cap"], kind="mergesort").reset_index(drop=True)


def _load_frozen_allocation_reference(
    allocations_path: Path,
    solve_records_path: Path,
    census: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> FrozenAllocationReference:
    """Map every V1 cap to a canonical vector in the verified V4 freeze."""
    contract = config["frozen_allocation_reconciliation"]
    columns = [
        "role",
        "period",
        "window_id",
        "candidate_id",
        "comparator_rule",
        "policy_label",
        "paired_policy_id",
        "frontier_cap",
        "id",
        "exposure",
        "pd_point",
        "expected_payoff_rate",
    ]
    source_fields = list(FROZEN_SOURCE_FIELDS)
    rules = tuple(str(value) for value in contract["comparator_rules"])
    records = pd.read_parquet(
        solve_records_path,
        columns=["role", *source_fields],
    )
    source_caps = records.loc[
        records["role"].eq(str(contract["role"])) & records["comparator_rule"].isin(rules),
        source_fields,
    ].drop_duplicates()
    if source_caps.empty or bool(source_caps[source_fields].isna().any(axis=None)):
        raise RuntimeError("Frozen solve-record source identities are empty or incomplete.")
    source_caps["period"] = source_caps["period"].astype(str)
    for column in (
        "window_id",
        "candidate_id",
        "comparator_rule",
        "policy_label",
        "paired_policy_id",
    ):
        source_caps[column] = source_caps[column].astype(str)
    source_caps["frontier_cap"] = pd.to_numeric(source_caps["frontier_cap"], errors="raise").astype(
        float
    )
    mappings: list[pd.DataFrame] = []
    cap_tolerance = float(contract["cap_match_tolerance"])
    for period, period_census in census.groupby("period", sort=True):
        period_sources = source_caps.loc[source_caps["period"].eq(str(period))].sort_values(
            "frontier_cap", kind="mergesort"
        )
        if period_sources.empty:
            raise RuntimeError(f"Frozen allocation source has no caps for {period}.")
        targets = period_census[["period", "point_cap"]].copy()
        targets["period"] = targets["period"].astype(str)
        targets = targets.sort_values("point_cap", kind="mergesort")
        mapped = pd.merge_asof(
            period_sources,
            targets,
            left_on="frontier_cap",
            right_on="point_cap",
            by="period",
            direction="nearest",
            tolerance=cast(Any, cap_tolerance),
        ).dropna(subset=["point_cap"])
        mapped["cap_match_distance"] = (mapped["frontier_cap"] - mapped["point_cap"]).abs()
        mappings.append(mapped)
    mapping = pd.concat(mappings, ignore_index=True)
    mapped_keys = mapping[["period", "point_cap"]].drop_duplicates()
    expected_keys = census[["period", "point_cap"]].copy()
    expected_keys["period"] = expected_keys["period"].astype(str)
    coverage = expected_keys.merge(
        mapped_keys,
        on=["period", "point_cap"],
        how="left",
        indicator=True,
        validate="one_to_one",
    )
    if bool(coverage["_merge"].ne("both").any()):
        raise RuntimeError("The frozen allocation source does not cover the complete V1 census.")

    filters: list[list[tuple[str, str, Any]]] = []
    for period, group in mapping.groupby("period", sort=True):
        filters.append(
            [
                ("role", "==", str(contract["role"])),
                ("period", "==", str(period)),
                ("comparator_rule", "in", list(rules)),
                ("frontier_cap", "in", sorted(group["frontier_cap"].unique().tolist())),
            ]
        )
    selected = pd.read_parquet(allocations_path, columns=columns, filters=filters)
    if selected.empty or bool(selected[[*source_fields, "id"]].isna().any(axis=None)):
        raise RuntimeError("Frozen allocation source identities are empty or incomplete.")
    selected["period"] = selected["period"].astype(str)
    selected["id"] = selected["id"].astype("string").astype(str)
    for column in (
        "window_id",
        "candidate_id",
        "comparator_rule",
        "policy_label",
        "paired_policy_id",
    ):
        selected[column] = selected[column].astype(str)
    for column in ("frontier_cap", "exposure", "pd_point", "expected_payoff_rate"):
        selected[column] = pd.to_numeric(selected[column], errors="raise").astype(float)
    if not bool(
        np.isfinite(selected[["frontier_cap", "exposure", "pd_point", "expected_payoff_rate"]]).all(
            axis=None
        )
    ):
        raise RuntimeError("Frozen point allocations are empty or nonfinite.")
    if bool(selected["exposure"].le(0.0).any()):
        raise RuntimeError("Frozen point allocation rows must contain positive exposure only.")

    matched = selected.merge(
        mapping[[*source_fields, "point_cap"]],
        on=source_fields,
        how="inner",
        validate="many_to_one",
    )
    source_coverage = mapping[[*source_fields, "point_cap"]].merge(
        matched[[*source_fields, "point_cap"]].drop_duplicates(),
        on=[*source_fields, "point_cap"],
        how="left",
        indicator=True,
        validate="one_to_one",
    )
    if bool(source_coverage["_merge"].ne("both").any()):
        raise RuntimeError("A frozen solve-record source has no positive allocation vector.")
    source_vector_keys = [*source_fields, "point_cap", "id"]
    if bool(matched.duplicated(source_vector_keys).any()):
        raise RuntimeError("A frozen source vector contains duplicate candidate IDs.")

    keys = ["period", "point_cap", "id"]
    duplicate = matched.groupby(keys, sort=False).agg(
        exposure_min=("exposure", "min"),
        exposure_max=("exposure", "max"),
        positive_source_rows=("exposure", "size"),
        pd_point_min=("pd_point", "min"),
        pd_point_max=("pd_point", "max"),
        payoff_rate_min=("expected_payoff_rate", "min"),
        payoff_rate_max=("expected_payoff_rate", "max"),
    )
    source_count_series = mapping.groupby(["period", "point_cap"], sort=False).size()
    duplicate = duplicate.reset_index().merge(
        source_count_series.to_frame(name="source_key_count").reset_index(),
        on=["period", "point_cap"],
        how="left",
        validate="many_to_one",
    )
    has_implicit_zero = duplicate["positive_source_rows"].lt(duplicate["source_key_count"])
    duplicate["exposure_min_with_implicit_zero"] = duplicate["exposure_min"].where(
        ~has_implicit_zero, 0.0
    )
    maximum_exposure_spread = float(
        (duplicate["exposure_max"] - duplicate["exposure_min_with_implicit_zero"]).max()
    )
    maximum_coefficient_spread = float(
        max(
            (duplicate["pd_point_max"] - duplicate["pd_point_min"]).max(),
            (duplicate["payoff_rate_max"] - duplicate["payoff_rate_min"]).max(),
        )
    )
    if maximum_exposure_spread > float(contract["duplicate_exposure_tolerance_dollars"]):
        raise RuntimeError("Duplicate frozen allocation representations disagree.")
    if maximum_coefficient_spread > float(contract["coefficient_tolerance"]):
        raise RuntimeError("Duplicate frozen allocation coefficients disagree.")

    priority = {rule: index for index, rule in enumerate(rules)}
    mapping["_rule_priority"] = mapping["comparator_rule"].map(priority).astype(int)
    canonical_sources = mapping.sort_values(
        [
            "period",
            "point_cap",
            "_rule_priority",
            "policy_label",
            "paired_policy_id",
            "window_id",
            "candidate_id",
            "frontier_cap",
        ],
        kind="mergesort",
    ).drop_duplicates(["period", "point_cap"], keep="first")[[*source_fields, "point_cap"]]
    canonical = matched.merge(
        canonical_sources,
        on=[*source_fields, "point_cap"],
        how="inner",
        validate="many_to_one",
    ).sort_values(["period", "point_cap", "id"], kind="mergesort")
    if canonical.groupby(["period", "point_cap"], sort=False).ngroups != len(mapped_keys):
        raise RuntimeError("Canonical frozen allocation vector census is incomplete.")
    source_counts = source_count_series.to_dict()
    vectors: dict[tuple[str, float], FrozenAllocationVector] = {}
    for raw_key, group in canonical.groupby(["period", "point_cap"], sort=True):
        period, point_cap = cast(tuple[Any, Any], raw_key)
        key = (str(period), float(point_cap))
        vectors[key] = FrozenAllocationVector(
            ids=tuple(group["id"].astype(str)),
            exposure=group["exposure"].to_numpy(dtype=float),
            pd_point=group["pd_point"].to_numpy(dtype=float),
            expected_payoff_rate=group["expected_payoff_rate"].to_numpy(dtype=float),
            source_key_count=int(source_counts[key]),
        )
    if len(vectors) != int(config["census"]["expected_rows"]):
        raise RuntimeError("Frozen allocation vector census is incomplete.")
    return FrozenAllocationReference(
        vectors=vectors,
        diagnostics={
            "frozen_rows_loaded": int(len(selected)),
            "relevant_solve_record_cap_keys": int(len(source_caps)),
            "matched_positive_rows": int(len(matched)),
            "matched_source_cap_keys": int(len(mapping)),
            "mapped_v1_cap_keys": int(len(vectors)),
            "candidate_ids_with_implicit_zero_in_at_least_one_duplicate_source": int(
                has_implicit_zero.sum()
            ),
            "maximum_cap_match_distance": float(mapping["cap_match_distance"].max()),
            "maximum_duplicate_exposure_spread_dollars": maximum_exposure_spread,
            "maximum_duplicate_coefficient_spread": maximum_coefficient_spread,
        },
    )


def _set_and_verify_highs_option(
    solver: highspy.Highs, option: str, expected: str | int | float
) -> str | int | float:
    """Set one HiGHS option and fail if its effective value drifts."""
    if solver.setOptionValue(option, expected) != highspy.HighsStatus.kOk:
        raise RuntimeError(f"HiGHS rejected registered option {option}.")
    result = solver.getOptionValue(option)
    if not isinstance(result, tuple) or len(result) != 2:
        raise RuntimeError(f"HiGHS did not expose effective option {option}.")
    status, actual = result
    if status != highspy.HighsStatus.kOk:
        raise RuntimeError(f"HiGHS did not return registered option {option}.")
    matches = (
        str(actual) == expected if isinstance(expected, str) else float(actual) == float(expected)
    )
    if not matches:
        raise RuntimeError(f"HiGHS effective option drifted: {option}={actual!r}.")
    return actual


def _solver_identity(config: Mapping[str, Any]) -> dict[str, Any]:
    declared = config["solver"]
    package_version = importlib.metadata.version("highspy")
    probe = highspy.Highs()
    native_version = str(probe.version())
    githash = str(probe.githash())
    actual = {
        "highspy_version": package_version,
        "highs_native_version": native_version,
        "highs_githash": githash,
    }
    expected = {field: str(declared[field]) for field in actual}
    if actual != expected:
        raise RuntimeError(f"HiGHS identity drifted: {actual}, expected {expected}.")
    effective_options = {
        option: _set_and_verify_highs_option(probe, option, value)
        for option, value in (
            ("solver", str(declared["solver"])),
            ("presolve", str(declared["presolve"])),
            ("threads", int(declared["threads"])),
            ("time_limit", float(declared["time_limit_seconds"])),
            ("dual_feasibility_tolerance", float(declared["dual_feasibility_tolerance"])),
            ("primal_feasibility_tolerance", float(declared["primal_feasibility_tolerance"])),
        )
    }
    return {
        **actual,
        "solver": str(effective_options["solver"]),
        "presolve": str(effective_options["presolve"]),
        "threads": int(effective_options["threads"]),
        "time_limit_seconds": float(effective_options["time_limit"]),
        "dual_feasibility_tolerance": float(effective_options["dual_feasibility_tolerance"]),
        "primal_feasibility_tolerance": float(effective_options["primal_feasibility_tolerance"]),
        "zero_all_clocks_available": bool(hasattr(probe, "zeroAllClocks")),
        "session_scope": str(declared["session_scope"]),
    }


def _new_session(
    month: pd.DataFrame,
    *,
    point: np.ndarray,
    objective: np.ndarray,
    parent_config: Mapping[str, Any],
    audit_config: Mapping[str, Any],
) -> PointPortfolioSession:
    solver = audit_config["solver"]
    session = PointPortfolioSession(
        month,
        point_score=point,
        objective_rate=objective,
        budget=float(parent_config["policy"]["budget"]),
        purpose_cap=float(parent_config["policy"]["max_concentration_by_purpose"]),
        time_limit=int(solver["time_limit_seconds"]),
        threads=int(solver["threads"]),
    )
    if hasattr(session.solver, "zeroAllClocks"):
        cast(Any, session.solver.zeroAllClocks)()
    for option, value in (
        ("solver", str(solver["solver"])),
        ("presolve", str(solver["presolve"])),
        ("threads", int(solver["threads"])),
        ("time_limit", float(solver["time_limit_seconds"])),
        ("dual_feasibility_tolerance", float(solver["dual_feasibility_tolerance"])),
        ("primal_feasibility_tolerance", float(solver["primal_feasibility_tolerance"])),
    ):
        _set_and_verify_highs_option(session.solver, option, value)
    return session


def _row_names(month: pd.DataFrame) -> tuple[str, ...]:
    purposes = sorted(month["purpose"].astype("string").fillna("unknown").unique())
    return ("budget_equality", "point_risk_cap", *(f"purpose:{value}" for value in purposes))


def _attach_audit_details(
    audit: FullBasisAudit,
    *,
    period: str,
    point_cap: float,
    solve_origin: str,
    seed_cap: float | None,
    row_rows: list[dict[str, Any]],
    flag_rows: list[dict[str, Any]],
) -> None:
    prefix = {
        "period": period,
        "point_cap": float(point_cap),
        "solve_origin": solve_origin,
        "seed_cap": float("nan") if seed_cap is None else float(seed_cap),
    }
    row_rows.extend({**prefix, **item} for item in audit.row_details)
    flag_rows.extend({**prefix, **item} for item in audit.flagged_nonbasic)


def _frame(rows: list[dict[str, Any]], columns: Sequence[str]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=list(columns))


def _policy_feasibility_fields(audit: FullBasisAudit, *, budget: float) -> dict[str, float]:
    """Return raw normalized budget, risk-cap, and purpose-cap violations."""
    if len(audit.row_details) < 2:
        raise RuntimeError("Point LP has no budget and risk rows.")
    budget_row = audit.row_details[0]
    risk_row = audit.row_details[1]
    if budget_row["row_name"] != "budget_equality" or risk_row["row_name"] != "point_risk_cap":
        raise RuntimeError("Point LP row-role ordering changed.")
    budget_residual = float(budget_row["row_value"] - budget_row["row_lower"])
    risk_violation = float(risk_row["upper_bound_violation"])
    purpose_violations = [
        float(item["upper_bound_violation"])
        for item in audit.row_details[2:]
        if str(item["row_name"]).startswith("purpose:")
    ]
    maximum_purpose_violation = max(purpose_violations, default=0.0)
    normalized = max(abs(budget_residual), risk_violation, maximum_purpose_violation) / float(
        budget
    )
    return {
        "raw_budget_equality_residual_dollars": budget_residual,
        "raw_risk_cap_violation_dollars": risk_violation,
        "raw_maximum_purpose_cap_violation_dollars": maximum_purpose_violation,
        "maximum_normalized_policy_constraint_violation": normalized,
        "raw_weighted_point_score": float(risk_row["row_value"]) / float(budget),
    }


def _frozen_allocation_reconciliation_fields(
    reference: FrozenAllocationVector,
    *,
    candidate_ids: tuple[str, ...],
    raw_exposure: np.ndarray,
    point: np.ndarray,
    objective: np.ndarray,
    raw_objective: float,
    raw_weighted_point: float,
    v1_objective: float,
    v1_weighted_point: float,
    budget: float,
    tolerances: Mapping[str, Any],
) -> dict[str, Any]:
    """Reconcile one fresh raw LP allocation to one frozen positive vector."""
    if len(set(candidate_ids)) != len(candidate_ids):
        raise RuntimeError("Fresh monthly candidate IDs are not unique.")
    index = {candidate_id: position for position, candidate_id in enumerate(candidate_ids)}
    missing = sorted(set(reference.ids).difference(index))
    if missing:
        raise RuntimeError(f"Frozen allocation IDs are absent from the fresh menu: {missing[:3]}.")
    frozen_exposure = np.zeros(len(candidate_ids), dtype=float)
    positions = np.asarray([index[value] for value in reference.ids], dtype=np.int64)
    frozen_exposure[positions] = reference.exposure
    current_point = point[positions]
    current_objective = objective[positions]
    maximum_point_coefficient_difference = float(
        np.abs(current_point - reference.pd_point).max(initial=0.0)
    )
    maximum_objective_coefficient_difference = float(
        np.abs(current_objective - reference.expected_payoff_rate).max(initial=0.0)
    )
    frozen_total = float(frozen_exposure.sum())
    fresh_total = float(raw_exposure.sum())
    if frozen_total <= 0.0 or fresh_total <= 0.0:
        raise RuntimeError("Fresh and frozen allocations must commit positive capital.")
    l1_dollars = float(np.abs(raw_exposure - frozen_exposure).sum())
    normalized_l1 = float(l1_dollars / (fresh_total + frozen_total))
    frozen_objective_stored = float(reference.exposure @ reference.expected_payoff_rate)
    frozen_objective_current = float(reference.exposure @ current_objective)
    frozen_weighted_point_stored = float(reference.exposure @ reference.pd_point / frozen_total)
    frozen_weighted_point_current = float(reference.exposure @ current_point / frozen_total)
    fresh_objective_difference = float(raw_objective - frozen_objective_stored)
    fresh_point_difference = float(raw_weighted_point - frozen_weighted_point_stored)
    frozen_v1_objective_difference = float(frozen_objective_stored - v1_objective)
    frozen_v1_point_difference = float(frozen_weighted_point_stored - v1_weighted_point)
    coefficient_tolerance = float(tolerances["freeze_coefficient"])
    passed = bool(
        l1_dollars <= float(tolerances["freeze_l1_exposure_dollars"])
        and normalized_l1 <= float(tolerances["allocation_distance"])
        and abs(fresh_objective_difference)
        <= float(tolerances["freeze_objective_difference_dollars"])
        and abs(fresh_point_difference) <= float(tolerances["freeze_weighted_point_difference"])
        and abs(frozen_v1_objective_difference)
        <= float(tolerances["freeze_objective_difference_dollars"])
        and abs(frozen_v1_point_difference) <= float(tolerances["freeze_weighted_point_difference"])
        and maximum_point_coefficient_difference <= coefficient_tolerance
        and maximum_objective_coefficient_difference <= coefficient_tolerance
        and abs(frozen_total - budget) / budget <= float(tolerances["cap_residual"])
    )
    return {
        "frozen_positive_candidate_count": int(len(reference.ids)),
        "frozen_source_key_count": int(reference.source_key_count),
        "frozen_total_allocated": frozen_total,
        "fresh_total_allocated_raw": fresh_total,
        "fresh_vs_frozen_l1_exposure_dollars": l1_dollars,
        "fresh_vs_frozen_normalized_l1_exposure": normalized_l1,
        "frozen_expected_objective_stored": frozen_objective_stored,
        "frozen_expected_objective_current_coefficients": frozen_objective_current,
        "fresh_vs_frozen_expected_objective_difference": fresh_objective_difference,
        "frozen_weighted_point_stored": frozen_weighted_point_stored,
        "frozen_weighted_point_current_coefficients": frozen_weighted_point_current,
        "fresh_vs_frozen_weighted_point_difference": fresh_point_difference,
        "frozen_vs_v1_expected_objective_difference": frozen_v1_objective_difference,
        "frozen_vs_v1_weighted_point_difference": frozen_v1_point_difference,
        "maximum_frozen_point_coefficient_difference": (maximum_point_coefficient_difference),
        "maximum_frozen_objective_coefficient_difference": (
            maximum_objective_coefficient_difference
        ),
        "frozen_allocation_reconciliation_passed": passed,
    }


def _rhs_basis_range_coverage_diagnostics(
    central: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Check fresh RHS basis ranges cover support at the registered tolerance."""
    contract = config["rhs_basis_range_coverage"]
    tolerance = float(contract["gap_tolerance"])
    broad_lower, broad_upper = (float(value) for value in contract["broad_support"])
    rows: list[dict[str, Any]] = []
    for period, group in central.groupby("period", sort=True):
        lower = group["fresh_basis_cap_lower"].to_numpy(dtype=float)
        upper = group["fresh_basis_cap_upper"].to_numpy(dtype=float)
        caps = group["point_cap"].to_numpy(dtype=float)
        finite = bool(np.isfinite(lower).all() and np.isfinite(upper).all())
        interval_order_valid = bool(finite and np.all(lower <= upper + tolerance))
        cap_containment_violation = float(
            max(
                np.maximum(lower - caps, 0.0).max(initial=0.0),
                np.maximum(caps - upper, 0.0).max(initial=0.0),
            )
        )
        intervals = sorted(
            (float(left), float(right)) for left, right in zip(lower, upper, strict=True)
        )
        merged: list[list[float]] = []
        raw_merged: list[list[float]] = []
        for left, right in intervals:
            if not merged or left > merged[-1][1] + tolerance:
                merged.append([left, right])
            else:
                merged[-1][1] = max(merged[-1][1], right)
            if not raw_merged or left > raw_merged[-1][1]:
                raw_merged.append([left, right])
            else:
                raw_merged[-1][1] = max(raw_merged[-1][1], right)

        development_lower_caps = group.loc[
            group["is_development_support_lower"].astype(bool), "point_cap"
        ].to_numpy(dtype=float)
        development_upper_caps = group.loc[
            group["is_development_support_upper"].astype(bool), "point_cap"
        ].to_numpy(dtype=float)
        if not development_lower_caps.size or not development_upper_caps.size:
            raise RuntimeError(f"V1 census has no development-support endpoints for {period}.")
        development_lower = float(development_lower_caps.min())
        development_upper = float(development_upper_caps.max())
        required_lower = min(broad_lower, development_lower)
        required_upper = max(broad_upper, development_upper)

        def _covering_segment(
            left: float, right: float, segments: list[list[float]]
        ) -> tuple[bool, float, float]:
            for segment_left, segment_right in segments:
                if segment_left <= left + tolerance and segment_right >= left - tolerance:
                    return (
                        bool(segment_right >= right - tolerance),
                        float(segment_left),
                        float(segment_right),
                    )
            return False, float("nan"), float("nan")

        broad_covered, _, _ = _covering_segment(broad_lower, broad_upper, merged)
        required_covered, covered_lower, covered_upper = _covering_segment(
            required_lower, required_upper, merged
        )
        clipped_segments = [
            (max(left, required_lower), min(right, required_upper))
            for left, right in merged
            if right >= required_lower - tolerance and left <= required_upper + tolerance
        ]
        gaps = (
            [max(clipped_segments[0][0] - required_lower, 0.0)]
            if clipped_segments
            else [required_upper - required_lower]
        )
        gaps.extend(
            max(clipped_segments[index][0] - clipped_segments[index - 1][1], 0.0)
            for index in range(1, len(clipped_segments))
        )
        if clipped_segments:
            gaps.append(max(required_upper - clipped_segments[-1][1], 0.0))
        maximum_gap = float(max(gaps, default=0.0))
        raw_clipped_segments = [
            (max(left, required_lower), min(right, required_upper))
            for left, right in raw_merged
            if right >= required_lower and left <= required_upper
        ]
        raw_gaps = (
            [max(raw_clipped_segments[0][0] - required_lower, 0.0)]
            if raw_clipped_segments
            else [required_upper - required_lower]
        )
        raw_gaps.extend(
            max(raw_clipped_segments[index][0] - raw_clipped_segments[index - 1][1], 0.0)
            for index in range(1, len(raw_clipped_segments))
        )
        if raw_clipped_segments:
            raw_gaps.append(max(required_upper - raw_clipped_segments[-1][1], 0.0))
        maximum_raw_gap = float(max(raw_gaps, default=0.0))
        rows.append(
            {
                "period": str(period),
                "fresh_interval_rows": int(len(intervals)),
                "fresh_merged_segments": int(len(merged)),
                "fresh_raw_merged_segments": int(len(raw_merged)),
                "broad_support_lower": broad_lower,
                "broad_support_upper": broad_upper,
                "development_support_lower": development_lower,
                "development_support_upper": development_upper,
                "required_coverage_lower": required_lower,
                "required_coverage_upper": required_upper,
                "covering_segment_lower": covered_lower,
                "covering_segment_upper": covered_upper,
                "maximum_positive_gap": maximum_gap,
                "maximum_raw_positive_gap": maximum_raw_gap,
                "maximum_cap_containment_violation": cap_containment_violation,
                "basis_interval_order_valid": interval_order_valid,
                "broad_support_covered": broad_covered,
                "development_support_hull_covered": required_covered,
                "fresh_rhs_basis_range_coverage_passed": bool(
                    interval_order_valid
                    and cap_containment_violation <= tolerance
                    and maximum_gap <= tolerance
                    and broad_covered
                    and required_covered
                ),
                "maximum_fresh_vs_v1_basis_lower_difference": float(
                    (group["fresh_basis_cap_lower"] - group["basis_cap_lower"]).abs().max()
                ),
                "maximum_fresh_vs_v1_basis_upper_difference": float(
                    (group["fresh_basis_cap_upper"] - group["basis_cap_upper"]).abs().max()
                ),
                "v1_basis_identity_required": False,
            }
        )
    return pd.DataFrame(rows)


def _reconcile_breakpoint_comparisons(
    comparisons: pd.DataFrame,
    faces: pd.DataFrame,
    *,
    tolerances: Mapping[str, Any],
) -> pd.DataFrame:
    """Record same-cap cooccurrence without claiming the face range explains a gap."""
    compared = comparisons.copy()
    mobile_faces = faces.loc[faces["epsilon_near_optimal_mobility_detected"].astype(bool)]
    mobile_keys = {
        (str(period), float(point_cap))
        for period, point_cap in zip(mobile_faces["period"], mobile_faces["point_cap"], strict=True)
    }
    same_cap_mobility = pd.Series(
        [
            (str(period), float(point_cap)) in mobile_keys
            for period, point_cap in zip(compared["period"], compared["point_cap"], strict=True)
        ],
        index=compared.index,
        dtype=bool,
    )
    allocation_differs = compared["maximum_pairwise_allocation_distance"].gt(
        float(tolerances["allocation_distance"])
    )
    compared["allocation_difference_cooccurs_with_same_cap_epsilon_mobility"] = (
        allocation_differs & same_cap_mobility
    )
    compared["allocation_difference_without_same_cap_epsilon_mobility"] = (
        allocation_differs
        & ~compared["allocation_difference_cooccurs_with_same_cap_epsilon_mobility"]
    )
    compared["lateral_objective_discrepancy"] = compared[
        "maximum_pairwise_objective_difference"
    ].gt(float(tolerances["lateral_objective_difference_dollars"]))
    compared["lateral_weighted_point_discrepancy"] = compared[
        "maximum_pairwise_weighted_point_difference"
    ].gt(float(tolerances["lateral_weighted_point_difference"]))
    compared["lateral_numerical_discrepancy"] = (
        compared["allocation_difference_without_same_cap_epsilon_mobility"]
        | compared["lateral_objective_discrepancy"]
        | compared["lateral_weighted_point_discrepancy"]
    )
    return compared


def _run_full_audit(
    base: pd.DataFrame,
    census: pd.DataFrame,
    *,
    frozen_reference: FrozenAllocationReference,
    config: Mapping[str, Any],
    parent_config: Mapping[str, Any],
) -> dict[str, pd.DataFrame]:
    tolerances = config["tolerances"]
    budget = float(parent_config["policy"]["budget"])
    central_rows: list[dict[str, Any]] = []
    freeze_rows: list[dict[str, Any]] = []
    column_registry_rows: list[dict[str, Any]] = []
    row_rows: list[dict[str, Any]] = []
    probe_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    flag_rows: list[dict[str, Any]] = []
    face_rows: list[dict[str, Any]] = []

    primary = monthly_frames(base, "primary_oot")
    if len(primary) != int(config["census"]["expected_periods"]):
        raise RuntimeError("Primary monthly decision panels changed.")
    for month_index, (period, month) in enumerate(primary, start=1):
        logger.info("Optimal-face V2 month {}/15: {}", month_index, period)
        period_census = census.loc[census["period"].eq(period)].sort_values(
            "point_cap", kind="mergesort"
        )
        if period_census.empty:
            raise RuntimeError(f"V1 census has no caps for {period}.")
        point = month["pd_point"].to_numpy(dtype=float)
        objective = expected_objective_coefficients(
            point,
            month["contractual_rate"].to_numpy(dtype=float),
            lgd=float(parent_config["payoff"]["lgd"]),
        )
        column_names = tuple(month["id"].astype("string").astype(str))
        row_names = _row_names(month)
        central_session = _new_session(
            month,
            point=point,
            objective=objective,
            parent_config=parent_config,
            audit_config=config,
        )
        lp = central_session.solver.getLp()
        column_costs = np.asarray(lp.col_cost_, dtype=float)
        column_lower = np.asarray(lp.col_lower_, dtype=float)
        column_upper = np.asarray(lp.col_upper_, dtype=float)
        objective_reference = float(np.abs(column_costs).max(initial=0.0))
        column_scales = np.full(len(column_costs), objective_reference, dtype=float)
        column_thresholds = (
            float(tolerances["dual_near_zero_scaled_absolute"])
            + float(tolerances["dual_near_zero_relative"])
        ) * column_scales
        column_registry_rows.extend(
            {
                "period": period,
                "column_index": int(index),
                "candidate_id": column_names[index],
                "loan_amount": float(central_session.amount[index]),
                "objective_cost": float(column_costs[index]),
                "column_lower": float(column_lower[index]),
                "column_upper": float(column_upper[index]),
                "dual_reference_scale": float(column_scales[index]),
                "near_zero_threshold": float(column_thresholds[index]),
            }
            for index in range(len(column_names))
        )
        central_breakpoints: dict[float, dict[str, Any]] = {}
        for cap_row in period_census.itertuples(index=False):
            cap = float(cap_row.point_cap)
            solution = central_session.solve(cap)
            audit = audit_full_basis(
                central_session,
                solution,
                dual_absolute_tolerance=float(tolerances["dual_near_zero_scaled_absolute"]),
                dual_relative_tolerance=float(tolerances["dual_near_zero_relative"]),
                primal_tolerance=float(tolerances["primal_degeneracy"]),
                column_names=column_names,
                row_names=row_names,
            )
            feasibility = _policy_feasibility_fields(audit, budget=budget)
            raw_exposure = central_session.amount * audit.column_values
            frozen = frozen_reference.vectors.get((str(period), cap))
            if frozen is None:
                raise RuntimeError(f"Frozen allocation reference is missing {period} at {cap}.")
            freeze_reconciliation = _frozen_allocation_reconciliation_fields(
                frozen,
                candidate_ids=column_names,
                raw_exposure=raw_exposure,
                point=point,
                objective=objective,
                raw_objective=float(audit.summary["raw_solver_objective"]),
                raw_weighted_point=float(feasibility["raw_weighted_point_score"]),
                v1_objective=float(cap_row.expected_objective),
                v1_weighted_point=float(cap_row.weighted_point_score),
                budget=budget,
                tolerances=tolerances,
            )
            central_rows.append(
                {
                    **cap_row._asdict(),
                    "expected_objective": float(solution.objective_value),
                    "raw_expected_objective": float(audit.summary["raw_solver_objective"]),
                    "weighted_point_score": float(solution.weighted_point_score),
                    "raw_point_cap_slack": float(cap - feasibility["raw_weighted_point_score"]),
                    "total_allocated": float(solution.total_allocated),
                    "point_cap_slack": float(cap - solution.weighted_point_score),
                    "fresh_basis_cap_lower": float(solution.basis_cap_lower),
                    "fresh_basis_cap_upper": float(solution.basis_cap_upper),
                    "solver_run_time_seconds": float(central_session.solver.getRunTime()),
                    **freeze_reconciliation,
                    **feasibility,
                    **audit.summary,
                }
            )
            freeze_rows.append(
                {
                    "period": str(period),
                    "point_cap": cap,
                    **freeze_reconciliation,
                }
            )
            _attach_audit_details(
                audit,
                period=period,
                point_cap=cap,
                solve_origin="central",
                seed_cap=None,
                row_rows=row_rows,
                flag_rows=flag_rows,
            )
            if bool(getattr(cap_row, str(config["census"]["breakpoint_column"]))):
                central_breakpoints[cap] = {
                    "exposure": raw_exposure,
                    "objective": float(audit.summary["raw_solver_objective"]),
                    "weighted_point": float(feasibility["raw_weighted_point_score"]),
                    "audit": audit,
                }

        breakpoint_caps = np.asarray(sorted(central_breakpoints), dtype=float)
        plans = breakpoint_probe_plan(breakpoint_caps)
        expected_period_probes = 2 * len(breakpoint_caps) - 2
        if len(plans) != expected_period_probes:
            raise RuntimeError(f"Breakpoint probe plan is incomplete for {period}.")
        side_results: dict[tuple[float, str], dict[str, Any]] = {}
        for side in ("left", "right"):
            selected = [item for item in plans if item["probe_side"] == side]
            selected.sort(key=lambda item: float(item["point_cap"]), reverse=side == "right")
            for plan in selected:
                # Each bilateral path starts in a fresh solver: midpoint -> c.
                # No basis state leaks from the central, opposite-side, or prior
                # breakpoint path, and getRunTime() is local to this probe.
                side_session = _new_session(
                    month,
                    point=point,
                    objective=objective,
                    parent_config=parent_config,
                    audit_config=config,
                )
                cap = float(plan["point_cap"])
                seed_cap = float(plan["seed_cap"])
                if side == "left" and not seed_cap < cap:
                    raise RuntimeError("Left breakpoint seed is not strictly interior.")
                if side == "right" and not seed_cap > cap:
                    raise RuntimeError("Right breakpoint seed is not strictly interior.")
                seed = side_session.solve(seed_cap)
                exact = side_session.solve(cap)
                audit = audit_full_basis(
                    side_session,
                    exact,
                    dual_absolute_tolerance=float(tolerances["dual_near_zero_scaled_absolute"]),
                    dual_relative_tolerance=float(tolerances["dual_near_zero_relative"]),
                    primal_tolerance=float(tolerances["primal_degeneracy"]),
                    column_names=column_names,
                    row_names=row_names,
                )
                feasibility = _policy_feasibility_fields(audit, budget=budget)
                raw_exposure = side_session.amount * audit.column_values
                central = central_breakpoints[cap]
                distance = normalized_exposure_distance(
                    np.asarray(central["exposure"], dtype=float), raw_exposure
                )
                probe_rows.append(
                    {
                        "period": period,
                        "point_cap": cap,
                        "probe_side": side,
                        "seed_cap": seed_cap,
                        "seed_expected_objective": float(seed.objective_value),
                        "seed_weighted_point_score": float(seed.weighted_point_score),
                        "exact_expected_objective": float(exact.objective_value),
                        "exact_weighted_point_score": float(exact.weighted_point_score),
                        "raw_exact_expected_objective": float(
                            audit.summary["raw_solver_objective"]
                        ),
                        "raw_exact_weighted_point_score": float(
                            feasibility["raw_weighted_point_score"]
                        ),
                        "central_allocation_distance": distance,
                        "central_objective_difference": float(
                            audit.summary["raw_solver_objective"] - float(central["objective"])
                        ),
                        "central_weighted_point_difference": float(
                            feasibility["raw_weighted_point_score"]
                            - float(central["weighted_point"])
                        ),
                        "solver_run_time_seconds": float(side_session.solver.getRunTime()),
                        **feasibility,
                        **audit.summary,
                    }
                )
                _attach_audit_details(
                    audit,
                    period=period,
                    point_cap=cap,
                    solve_origin=side,
                    seed_cap=seed_cap,
                    row_rows=row_rows,
                    flag_rows=flag_rows,
                )
                side_results[(cap, side)] = {
                    "exposure": raw_exposure,
                    "objective": float(audit.summary["raw_solver_objective"]),
                    "weighted_point": float(feasibility["raw_weighted_point_score"]),
                    "audit": audit,
                    "seed_cap": seed_cap,
                }

        for cap in breakpoint_caps:
            cap_value = float(cap)
            central = central_breakpoints[cap_value]
            available = {
                origin: side_results[(cap_value, origin)]
                for origin in ("left", "right")
                if (cap_value, origin) in side_results
            }
            states = {"central": central, **available}
            pairs = list(combinations(sorted(states), 2))
            pair_distances = {
                f"{left}_vs_{right}": normalized_exposure_distance(
                    np.asarray(states[left]["exposure"], dtype=float),
                    np.asarray(states[right]["exposure"], dtype=float),
                )
                for left, right in pairs
            }
            pair_objectives = {
                f"{left}_vs_{right}": abs(
                    float(states[left]["objective"]) - float(states[right]["objective"])
                )
                for left, right in pairs
            }
            pair_points = {
                f"{left}_vs_{right}": abs(
                    float(states[left]["weighted_point"]) - float(states[right]["weighted_point"])
                )
                for left, right in pairs
            }
            warning_count = int(central["audit"].summary["near_zero_nonbasic_total"]) + sum(
                int(item["audit"].summary["near_zero_nonbasic_total"])
                for item in available.values()
            )
            max_distance = max(pair_distances.values(), default=0.0)
            comparison_rows.append(
                {
                    "period": period,
                    "point_cap": cap_value,
                    "available_sides": "+".join(sorted(available)),
                    "complete_basis_warning_count": warning_count,
                    "maximum_pairwise_allocation_distance": max_distance,
                    "maximum_pairwise_objective_difference": max(
                        pair_objectives.values(), default=0.0
                    ),
                    "maximum_pairwise_weighted_point_difference": max(
                        pair_points.values(), default=0.0
                    ),
                    "central_left_allocation_distance": pair_distances.get(
                        "central_vs_left", float("nan")
                    ),
                    "central_right_allocation_distance": pair_distances.get(
                        "central_vs_right", float("nan")
                    ),
                    "left_right_allocation_distance": pair_distances.get(
                        "left_vs_right", float("nan")
                    ),
                    "central_left_objective_difference": pair_objectives.get(
                        "central_vs_left", float("nan")
                    ),
                    "central_right_objective_difference": pair_objectives.get(
                        "central_vs_right", float("nan")
                    ),
                    "left_right_objective_difference": pair_objectives.get(
                        "left_vs_right", float("nan")
                    ),
                    "central_left_weighted_point_difference": pair_points.get(
                        "central_vs_left", float("nan")
                    ),
                    "central_right_weighted_point_difference": pair_points.get(
                        "central_vs_right", float("nan")
                    ),
                    "left_right_weighted_point_difference": pair_points.get(
                        "left_vs_right", float("nan")
                    ),
                    "central_column_basis_state_sha256": central["audit"].summary[
                        "column_basis_state_sha256"
                    ],
                    "central_row_basis_state_sha256": central["audit"].summary[
                        "row_basis_state_sha256"
                    ],
                    "left_column_basis_state_sha256": (
                        available["left"]["audit"].summary["column_basis_state_sha256"]
                        if "left" in available
                        else None
                    ),
                    "left_row_basis_state_sha256": (
                        available["left"]["audit"].summary["row_basis_state_sha256"]
                        if "left" in available
                        else None
                    ),
                    "right_column_basis_state_sha256": (
                        available["right"]["audit"].summary["column_basis_state_sha256"]
                        if "right" in available
                        else None
                    ),
                    "right_row_basis_state_sha256": (
                        available["right"]["audit"].summary["row_basis_state_sha256"]
                        if "right" in available
                        else None
                    ),
                }
            )

        month_flags = [item for item in flag_rows if item["period"] == period]
        targets: dict[tuple[float, str, int], dict[str, Any]] = {}
        for item in month_flags:
            key = (
                float(item["point_cap"]),
                str(item["variable_kind"]),
                int(item["variable_index"]),
            )
            target = targets.setdefault(
                key,
                {
                    "variable_name": str(item["variable_name"]),
                    "origins": set(),
                },
            )
            cast(set[str], target["origins"]).add(str(item["solve_origin"]))
        for (cap, variable_kind, variable_index), target in sorted(targets.items()):
            face_session = _new_session(
                month,
                point=point,
                objective=objective,
                parent_config=parent_config,
                audit_config=config,
            )
            face_solution = face_session.solve(cap)
            result = optimal_face_range(
                face_session,
                face_solution,
                variable_kind=variable_kind,
                variable_index=variable_index,
                objective_absolute_tolerance=float(tolerances["face_objective_absolute_dollars"]),
                objective_relative_tolerance=float(tolerances["face_objective_relative"]),
                time_limit=int(config["solver"]["time_limit_seconds"]),
                threads=int(config["solver"]["threads"]),
                dual_feasibility_tolerance=float(config["solver"]["dual_feasibility_tolerance"]),
                primal_feasibility_tolerance=float(
                    config["solver"]["primal_feasibility_tolerance"]
                ),
            )
            normalized = float(result["value_range"]) / budget
            if variable_kind == "column":
                normalized *= float(face_session.amount[variable_index])
            epsilon = float(result["objective_face_epsilon"])
            band_slack = float(config["solver"]["primal_feasibility_tolerance"])
            differences = (
                float(result["minimum_primary_objective_difference"]),
                float(result["maximum_primary_objective_difference"]),
            )
            primary_reconciliation_passed = bool(
                abs(float(result["raw_internal_primary_objective_difference"])) <= epsilon
                and abs(float(result["solution_to_raw_primary_objective_difference"])) <= epsilon
            )
            band_passed = bool(
                primary_reconciliation_passed
                and all(
                    -epsilon - band_slack <= value <= epsilon + band_slack for value in differences
                )
            )
            face_rows.append(
                {
                    "period": period,
                    "point_cap": cap,
                    "variable_kind": variable_kind,
                    "variable_index": variable_index,
                    "variable_name": str(target["variable_name"]),
                    "warning_origins": "+".join(sorted(cast(set[str], target["origins"]))),
                    **result,
                    "normalized_mobility": normalized,
                    "primary_objective_reconciliation_passed": primary_reconciliation_passed,
                    "objective_band_passed": band_passed,
                    "face_range_consistency_passed": bool(
                        float(result["maximum_range_consistency_violation"])
                        <= float(tolerances["face_range_consistency"])
                    ),
                    "epsilon_near_optimal_mobility_detected": bool(
                        normalized > float(tolerances["face_normalized_mobility"])
                    ),
                }
            )

    central = pd.DataFrame(central_rows)
    freeze_reconciliation = pd.DataFrame(freeze_rows)
    rhs_coverage = _rhs_basis_range_coverage_diagnostics(central, config=config)
    column_registry = _frame(column_registry_rows, COLUMN_REGISTRY_COLUMNS)
    rows = _frame(row_rows, ROW_DETAIL_COLUMNS)
    probes = pd.DataFrame(probe_rows)
    comparisons = pd.DataFrame(comparison_rows)
    flags = _frame(flag_rows, FLAG_COLUMNS)
    faces = _frame(face_rows, FACE_COLUMNS)
    comparisons = _reconcile_breakpoint_comparisons(
        comparisons,
        faces,
        tolerances=tolerances,
    )
    expected = config["census"]
    actual = {
        "central": len(central),
        "breakpoints": len(comparisons),
        "probes": len(probes),
        "frozen_reconciliations": len(freeze_reconciliation),
        "rhs_coverage_periods": len(rhs_coverage),
    }
    declared = {
        "central": int(expected["expected_rows"]),
        "breakpoints": int(expected["expected_basis_breakpoints"]),
        "probes": int(expected["expected_lateral_probe_rows"]),
        "frozen_reconciliations": int(expected["expected_rows"]),
        "rhs_coverage_periods": int(expected["expected_periods"]),
    }
    if actual != declared:
        raise RuntimeError(f"Optimal-face V2 output census is incomplete: {actual}.")
    if int(flags["period"].notna().sum()) == 0 and len(faces) != 0:
        raise RuntimeError("Optimal-face ranges were solved without a reduced-cost warning.")
    unique_targets = int(
        flags[["period", "point_cap", "variable_kind", "variable_index"]].drop_duplicates().shape[0]
        if not flags.empty
        else 0
    )
    if len(faces) != unique_targets:
        raise RuntimeError(
            "Conditional face reporting is incomplete for the registered warning union."
        )
    return {
        "central_basis_diagnostics": central,
        "frozen_allocation_reconciliation": freeze_reconciliation,
        "fresh_rhs_basis_range_coverage": rhs_coverage,
        "column_registry": column_registry,
        "row_slack_details": rows,
        "lateral_probe_diagnostics": probes,
        "breakpoint_comparisons": comparisons,
        "flagged_nonbasic_variables": flags,
        "optimal_face_ranges": faces,
    }


def _summary(frames: Mapping[str, pd.DataFrame], config: Mapping[str, Any]) -> dict[str, Any]:
    central = frames["central_basis_diagnostics"]
    probes = frames["lateral_probe_diagnostics"]
    comparisons = frames["breakpoint_comparisons"]
    flags = frames["flagged_nonbasic_variables"]
    faces = frames["optimal_face_ranges"]
    freeze = frames["frozen_allocation_reconciliation"]
    rhs_coverage = frames["fresh_rhs_basis_range_coverage"]
    tolerance = config["tolerances"]
    all_bases = pd.concat((central, probes), ignore_index=True)
    complete_warning_count = int(
        all_bases["near_zero_nonbasic_columns"].sum() + all_bases["near_zero_nonbasic_rows"].sum()
    )
    warning_reporting_failure = len(flags) != complete_warning_count
    has_registered_warnings = bool(complete_warning_count > 0 or not flags.empty)
    basis_failure = bool(
        (~all_bases["basis_valid"].astype(bool)).any()
        or (~all_bases["basis_dimension_valid"].astype(bool)).any()
        or (~all_bases["value_valid"].astype(bool)).any()
        or (~all_bases["dual_valid"].astype(bool)).any()
        or all_bases["unsupported_nonbasic_columns"].gt(0).any()
        or all_bases["unsupported_movable_nonbasic_rows"].gt(0).any()
    )
    dual_failure = bool(
        all_bases["maximum_scaled_dual_sign_violation"].max()
        > float(tolerance["dual_sign_scaled_violation"])
    )
    objective_failure = bool(
        all_bases["objective_reconciliation_error"].abs().max()
        > float(tolerance["objective_reconciliation_dollars"])
        or all_bases["raw_objective_internal_reconciliation_error"].abs().max()
        > float(tolerance["face_objective_absolute_dollars"])
        or all_bases["solution_to_raw_solver_objective_error"].abs().max()
        > float(tolerance["face_objective_absolute_dollars"])
    )
    policy_feasibility_failure = bool(
        all_bases["maximum_normalized_policy_constraint_violation"].max()
        > float(tolerance["cap_residual"])
        or all_bases["maximum_primal_bound_violation"].max()
        > float(config["solver"]["primal_feasibility_tolerance"])
    )
    frozen_allocation_failure = bool(
        len(freeze) != int(config["census"]["expected_rows"])
        or not freeze["frozen_allocation_reconciliation_passed"].astype(bool).all()
    )
    rhs_coverage_failure = bool(
        len(rhs_coverage) != int(config["census"]["expected_periods"])
        or not rhs_coverage["fresh_rhs_basis_range_coverage_passed"].astype(bool).all()
    )
    lateral_allocation_without_same_cap_mobility = bool(
        comparisons["allocation_difference_without_same_cap_epsilon_mobility"].any()
    )
    lateral_objective_failure = bool(comparisons["lateral_objective_discrepancy"].any())
    lateral_point_failure = bool(comparisons["lateral_weighted_point_discrepancy"].any())
    band_failure = bool(not faces.empty and not faces["objective_band_passed"].all())
    range_consistency_failure = bool(
        not faces.empty and not faces["face_range_consistency_passed"].all()
    )
    face_primal_failure = bool(
        not faces.empty
        and max(
            faces["minimum_maximum_column_bound_violation"].max(),
            faces["minimum_maximum_row_bound_violation"].max(),
            faces["maximum_maximum_column_bound_violation"].max(),
            faces["maximum_maximum_row_bound_violation"].max(),
        )
        > float(config["solver"]["primal_feasibility_tolerance"])
    )
    runtime_failure = bool(
        not faces.empty
        and (
            not np.isfinite(faces["minimum_solver_run_time_seconds"]).all()
            or not np.isfinite(faces["maximum_solver_run_time_seconds"]).all()
            or faces["minimum_solver_run_time_seconds"].lt(0.0).any()
            or faces["maximum_solver_run_time_seconds"].lt(0.0).any()
        )
    )
    epsilon_mobility = bool(
        not faces.empty and faces["epsilon_near_optimal_mobility_detected"].any()
    )
    registered_warning_inconclusive = bool(has_registered_warnings and not epsilon_mobility)
    numerical_failure = (
        basis_failure
        or dual_failure
        or objective_failure
        or policy_feasibility_failure
        or lateral_allocation_without_same_cap_mobility
        or lateral_objective_failure
        or lateral_point_failure
        or band_failure
        or range_consistency_failure
        or face_primal_failure
        or runtime_failure
        or warning_reporting_failure
        or frozen_allocation_failure
        or rhs_coverage_failure
    )
    if numerical_failure:
        status = "numerical_contract_failed_claim_blocked"
    elif epsilon_mobility:
        status = "epsilon_near_optimal_mobility_detected_claim_blocked"
    elif not has_registered_warnings:
        status = "strict_full_basis_freeze_and_fresh_rhs_range_coverage_numeric_certificate"
    else:
        status = "registered_warnings_without_global_face_diameter_claim_inconclusive"
    return {
        "certification_status": status,
        "strict_numeric_certificate_gate_passed": bool(
            not numerical_failure and not has_registered_warnings
        ),
        "finite_grid_numerical_uniqueness_gate_passed": bool(
            not numerical_failure and not has_registered_warnings
        ),
        "fresh_rhs_basis_range_coverage_gate_passed": bool(not rhs_coverage_failure),
        "exact_symbolic_optimal_face_claim_made": False,
        "global_optimal_face_diameter_claim_made": False,
        "symbolic_continuous_frontier_claim_made": False,
        "allocation_continuity_claim_made": False,
        "seam_conditioning_claim_made": False,
        "exhaustive_fresh_lateral_basis_enumeration_claim_made": False,
        "central": {
            "rows": int(len(central)),
            "periods": int(central["period"].nunique()),
            "basis_breakpoints": int(central["is_period_basis_breakpoint"].sum()),
            "near_zero_nonbasic_column_bases": int(
                central["near_zero_nonbasic_columns"].gt(0).sum()
            ),
            "near_zero_nonbasic_row_bases": int(central["near_zero_nonbasic_rows"].gt(0).sum()),
            "minimum_absolute_nonbasic_column_reduced_cost": float(
                central["minimum_absolute_nonbasic_column_reduced_cost"].min()
            ),
            "minimum_absolute_nonbasic_row_dual": float(
                central["minimum_absolute_nonbasic_row_dual"].min()
            ),
            "maximum_dual_sign_violation": float(central["maximum_dual_sign_violation"].max()),
            "maximum_absolute_objective_reconciliation_error": float(
                central["objective_reconciliation_error"].abs().max()
            ),
            "maximum_normalized_policy_constraint_violation": float(
                central["maximum_normalized_policy_constraint_violation"].max()
            ),
        },
        "breakpoints": {
            "rows": int(len(comparisons)),
            "probe_rows": int(len(probes)),
            "maximum_pairwise_allocation_distance": float(
                comparisons["maximum_pairwise_allocation_distance"].max()
            ),
            "allocation_difference_without_same_cap_epsilon_mobility_rows": int(
                comparisons["allocation_difference_without_same_cap_epsilon_mobility"].sum()
            ),
            "allocation_difference_with_same_cap_epsilon_mobility_cooccurrence_rows": int(
                comparisons["allocation_difference_cooccurs_with_same_cap_epsilon_mobility"].sum()
            ),
            "lateral_objective_discrepancy_rows": int(
                comparisons["lateral_objective_discrepancy"].sum()
            ),
            "lateral_weighted_point_discrepancy_rows": int(
                comparisons["lateral_weighted_point_discrepancy"].sum()
            ),
        },
        "frozen_allocation_reconciliation": {
            "rows": int(len(freeze)),
            "passed_rows": int(
                freeze["frozen_allocation_reconciliation_passed"].astype(bool).sum()
            ),
            "maximum_l1_exposure_dollars": float(
                freeze["fresh_vs_frozen_l1_exposure_dollars"].max()
            ),
            "maximum_normalized_l1_exposure": float(
                freeze["fresh_vs_frozen_normalized_l1_exposure"].max()
            ),
            "maximum_absolute_objective_difference": float(
                freeze["fresh_vs_frozen_expected_objective_difference"].abs().max()
            ),
            "maximum_absolute_weighted_point_difference": float(
                freeze["fresh_vs_frozen_weighted_point_difference"].abs().max()
            ),
        },
        "fresh_rhs_basis_range_coverage": {
            "periods": int(len(rhs_coverage)),
            "passed_periods": int(
                rhs_coverage["fresh_rhs_basis_range_coverage_passed"].astype(bool).sum()
            ),
            "maximum_positive_gap": float(rhs_coverage["maximum_positive_gap"].max()),
            "maximum_raw_positive_gap": float(rhs_coverage["maximum_raw_positive_gap"].max()),
            "maximum_cap_containment_violation": float(
                rhs_coverage["maximum_cap_containment_violation"].max()
            ),
            "v1_basis_identity_required": False,
        },
        "conditional_face": {
            "warning_rows": int(len(flags)),
            "complete_basis_warning_count": complete_warning_count,
            "unique_targets": int(
                flags[["period", "point_cap", "variable_kind", "variable_index"]]
                .drop_duplicates()
                .shape[0]
                if not flags.empty
                else 0
            ),
            "range_rows": int(len(faces)),
            "epsilon_near_optimal_mobility_rows": int(
                faces["epsilon_near_optimal_mobility_detected"].sum() if not faces.empty else 0
            ),
            "objective_band_failure_rows": int(
                (~faces["objective_band_passed"]).sum() if not faces.empty else 0
            ),
            "primary_objective_reconciliation_failure_rows": int(
                (~faces["primary_objective_reconciliation_passed"]).sum() if not faces.empty else 0
            ),
            "range_consistency_failure_rows": int(
                (~faces["face_range_consistency_passed"]).sum() if not faces.empty else 0
            ),
        },
        "scientific_stop_flags": {
            "basis_contract_failure": basis_failure,
            "dual_sign_failure": dual_failure,
            "objective_reconciliation_failure": objective_failure,
            "policy_feasibility_failure": policy_feasibility_failure,
            "allocation_difference_without_same_cap_epsilon_mobility": (
                lateral_allocation_without_same_cap_mobility
            ),
            "lateral_objective_discrepancy": lateral_objective_failure,
            "lateral_weighted_point_discrepancy": lateral_point_failure,
            "face_objective_band_failure": band_failure,
            "face_range_consistency_failure": range_consistency_failure,
            "face_primal_feasibility_failure": face_primal_failure,
            "face_runtime_reporting_failure": runtime_failure,
            "epsilon_near_optimal_mobility": epsilon_mobility,
            "registered_warning_without_global_face_diameter": (registered_warning_inconclusive),
            "warning_reporting_failure": warning_reporting_failure,
            "frozen_allocation_reconciliation_failure": frozen_allocation_failure,
            "fresh_rhs_basis_range_coverage_failure": rhs_coverage_failure,
        },
    }


def run_audit(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Execute the tagged V2 audit and return its deterministic summary path."""
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
    solver_identity = _solver_identity(config)
    parent_paths, parent_freeze = verified_parent_artifacts(config, repo_root=repo_root)
    parent_config_path, parent_config_descriptor = _verify_parent_config_from_freeze(
        config, parent_freeze, repo_root=repo_root
    )
    parent_config = load_v4_config(parent_config_path)
    raw_path = resolve_repo_input(config["source_ingest"]["raw_path"], repo_root=repo_root)
    base = load_outcome_free_decision_base(
        scores_path=parent_paths["scores"],
        raw_path=raw_path,
        config=config,
    )
    census = _load_v1_census(config, repo_root=repo_root)
    frozen_reference = _load_frozen_allocation_reference(
        parent_paths["allocations"],
        parent_paths["solve_records"],
        census,
        config=config,
    )
    frames = _run_full_audit(
        base,
        census,
        frozen_reference=frozen_reference,
        config=config,
        parent_config=parent_config,
    )
    result_summary = _summary(frames, config)
    implementation_end = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=repo_root,
    )
    if implementation_end != implementation_start:
        raise RuntimeError("Optimal-face V2 implementation changed during execution.")

    # Delay final-directory creation until every solve, census check, claim gate,
    # and implementation-drift check has completed. A technical stop therefore
    # does not consume the immutable run path.
    paths = prepare_output_paths(config, repo_root=repo_root)
    protocol_freeze = atomic_write_json(
        paths.model_dir / "protocol_freeze.json",
        {
            "schema_version": str(config["schema_version"]),
            "status": "outcome_free_optimal_face_v2_audit_frozen",
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "claim_boundary": dict(config["claim_boundary"]),
            "outcome_columns_passed": [],
            "parent_protocol_freeze": config["parent"]["protocol_freeze"],
            "parent_config": parent_config_descriptor,
            "parent_outcome_free_artifacts": parent_freeze["outcome_free_artifacts"],
            "frozen_allocation_reference_diagnostics": frozen_reference.diagnostics,
            "parent_v1_audit": config["parent_v1_audit"],
            "solver_contract": solver_identity,
            "implementation_provenance": implementation_start,
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    output = config["output"]
    output_names = {
        "central_basis_diagnostics": str(output["central_basis_diagnostics"]),
        "frozen_allocation_reconciliation": str(output["frozen_allocation_reconciliation"]),
        "fresh_rhs_basis_range_coverage": str(output["fresh_rhs_basis_range_coverage"]),
        "column_registry": str(output["column_registry"]),
        "row_slack_details": str(output["row_slack_details"]),
        "lateral_probe_diagnostics": str(output["lateral_probe_diagnostics"]),
        "breakpoint_comparisons": str(output["breakpoint_comparisons"]),
        "flagged_nonbasic_variables": str(output["flagged_nonbasic_variables"]),
        "optimal_face_ranges": str(output["optimal_face_ranges"]),
    }
    written: dict[Path, pd.DataFrame] = {}
    for label, frame in frames.items():
        path = atomic_write_parquet(frame, paths.data_dir / output_names[label], index=False)
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
        "status": "complete_outcome_free_optimal_face_v2_audit",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "hypothesis": str(config["hypothesis"]),
        "claim_boundary": dict(config["claim_boundary"]),
        "outcome_columns_passed": [],
        "solver_contract": solver_identity,
        "results": result_summary,
        "parent_protocol_freeze": config["parent"]["protocol_freeze"],
        "parent_config": parent_config_descriptor,
        "parent_v1_audit": config["parent_v1_audit"],
        "frozen_allocation_reference": {
            "allocations": relative_artifact_descriptor(
                parent_paths["allocations"], repo_root=repo_root
            ),
            "solve_records": relative_artifact_descriptor(
                parent_paths["solve_records"], repo_root=repo_root
            ),
            "diagnostics": frozen_reference.diagnostics,
        },
        "raw_source": relative_artifact_descriptor(raw_path, repo_root=repo_root),
        "implementation_provenance": implementation_start,
        "artifacts": artifacts,
        "schemas": {
            relative_artifact_descriptor(path, repo_root=repo_root)["path"]: dataframe_schema(frame)
            for path, frame in written.items()
        },
        "selection": {
            "cap": None,
            "breakpoint": None,
            "basis": None,
            "tie_break": None,
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
    logger.info("Optimal-face V2 audit complete: {}", summary_path)
    return summary_path


def main(argv: Sequence[str] | None = None) -> None:
    """Run the CLI entry point."""
    args = parse_args(argv)
    run_audit(config_path=args.config)


if __name__ == "__main__":
    main()
