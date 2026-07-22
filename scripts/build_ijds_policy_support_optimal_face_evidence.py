"""Build registered intermediate evidence from immutable V2 and V3a audits."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.utils.isolated_experiment import relative_artifact_descriptor
from src.utils.pipeline_runtime import atomic_write_strict_json

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "reports/crpto/ijds_policy_support_optimal_face_evidence.json"

V2_RUN_TAG = "ijds-policy-support-optimal-face-audit-2026-07-21-v2"
V2_PROTOCOL_TAG = "protocol/ijds-policy-support-optimal-face-audit-2026-07-21-v2"
V2_PROTOCOL_COMMIT = "86fddefdcf4d40a971866b2d9acf1d34f5c3bca2"
V2_MODEL_DIR = ROOT / "models/experiments/ijds_audit" / V2_RUN_TAG
V2_DATA_DIR = ROOT / "data/processed/experiments/ijds_audit" / V2_RUN_TAG
V2_SUMMARY_PATH = V2_MODEL_DIR / "optimal_face_audit_summary.json"
V2_RECEIPT_PATH = V2_MODEL_DIR / "execution_receipt.json"

V3A_RUN_TAG = "ijds-policy-support-rhs-semantics-recovery-2026-07-21-v3a"
V3A_PROTOCOL_TAG = "protocol/ijds-policy-support-rhs-semantics-recovery-2026-07-21-v3a"
V3A_PROTOCOL_COMMIT = "388927ebfe34e872fc5d1085ece63300734d5b47"
V3A_MODEL_DIR = ROOT / "models/experiments/ijds_audit" / V3A_RUN_TAG
V3A_DATA_DIR = ROOT / "data/processed/experiments/ijds_audit" / V3A_RUN_TAG
V3A_SUMMARY_PATH = V3A_MODEL_DIR / "rhs_semantics_recovery_summary.json"
V3A_RECEIPT_PATH = V3A_MODEL_DIR / "execution_receipt.json"

SUPPORT_LOWER = 0.05
SUPPORT_UPPER = 0.12
GAP_TOLERANCE = 1.0e-10
DUAL_SIGN_TOLERANCE = 1.0e-9
PRIMAL_FEASIBILITY_TOLERANCE = 1.0e-9
OBJECTIVE_RECONCILIATION_TOLERANCE = 1.0e-5
POLICY_FEASIBILITY_TOLERANCE = 1.0e-8
ALLOCATION_DISTANCE_TOLERANCE = 1.0e-10
LATERAL_OBJECTIVE_TOLERANCE = 1.0e-5
LATERAL_POINT_TOLERANCE = 1.0e-10
NEAR_ZERO_SCALED_THRESHOLD = 1.0e-7 + 1.0e-12
BUDGET_DOLLARS = 1_000_000.0

V2_ARTIFACT_BASENAMES = (
    "protocol_freeze.json",
    "central_full_basis_diagnostics.parquet",
    "frozen_allocation_reconciliation.parquet",
    "fresh_rhs_basis_range_coverage.parquet",
    "column_registry.parquet",
    "row_slack_basis_details.parquet",
    "breakpoint_lateral_probe_diagnostics.parquet",
    "breakpoint_allocation_comparisons.parquet",
    "flagged_nonbasic_variables.parquet",
    "conditional_optimal_face_ranges.parquet",
)
V3A_ARTIFACT_BASENAMES = (
    "protocol_freeze.json",
    "corrected_central_rhs_ranges.parquet",
    "gap_fill_basis_diagnostics.parquet",
    "gap_fill_row_slack_details.parquet",
    "gap_fill_flagged_nonbasic_variables.parquet",
    "corrected_rhs_coverage_by_period.parquet",
    "corrected_lateral_comparisons.parquet",
)


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a JSON object at {path}.")
    return payload


def _expected_artifact_paths(
    *, model_dir: Path, data_dir: Path, basenames: Sequence[str]
) -> set[str]:
    paths: set[str] = set()
    for basename in basenames:
        parent = model_dir if basename.endswith(".json") else data_dir
        paths.add((parent / basename).resolve().relative_to(ROOT.resolve()).as_posix())
    return paths


def _verify_descriptor(descriptor: Mapping[str, Any], *, expected_path: str | None = None) -> Path:
    """Resolve and hash-check one repository-contained descriptor."""
    if set(descriptor) != {"path", "bytes", "sha256"}:
        raise RuntimeError("Artifact descriptor fields changed.")
    relative = Path(str(descriptor["path"]))
    if relative.is_absolute():
        raise RuntimeError("Artifact descriptor must be repository-relative.")
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise RuntimeError("Artifact descriptor escaped the repository.") from exc
    if expected_path is not None and relative.as_posix() != expected_path:
        raise RuntimeError(f"Artifact descriptor path mismatch: {relative.as_posix()}.")
    actual = relative_artifact_descriptor(path, repo_root=ROOT)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor[field]:
            raise RuntimeError(f"Artifact descriptor mismatch for {path}: {field}.")
    return path


def _verify_artifact_map(
    artifacts: Mapping[str, Any], *, expected_paths: set[str]
) -> dict[str, Path]:
    if set(artifacts) != expected_paths:
        missing = sorted(expected_paths.difference(artifacts))
        extra = sorted(set(artifacts).difference(expected_paths))
        raise RuntimeError(f"Artifact census changed; missing={missing}, extra={extra}.")
    verified: dict[str, Path] = {}
    for key in sorted(artifacts):
        descriptor = artifacts[key]
        if not isinstance(descriptor, Mapping):
            raise TypeError(f"Artifact descriptor is not a mapping: {key}.")
        verified[key] = _verify_descriptor(descriptor, expected_path=key)
    return verified


def _git_tag_commit(tag: str) -> str:
    completed = subprocess.run(
        ["git", "rev-list", "-n", "1", tag],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    commit = completed.stdout.strip()
    if not commit:
        raise RuntimeError(f"Protocol tag has no commit: {tag}.")
    return commit


def _require_identity(
    payload: Mapping[str, Any],
    *,
    label: str,
    run_tag: str,
    protocol_tag: str,
    protocol_commit: str,
) -> None:
    expected = {
        "run_tag": run_tag,
        "protocol_tag": protocol_tag,
        "protocol_commit": protocol_commit,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise RuntimeError(f"{label} {field} identity mismatch.")


def _require_outcome_free(payload: Mapping[str, Any], *, label: str) -> None:
    if payload.get("outcome_columns_passed") != []:
        raise RuntimeError(f"{label} reports an outcome-bearing input.")
    if payload.get("protected_stages_run") != []:
        raise RuntimeError(f"{label} reports a protected stage execution.")
    if payload.get("protected_artifacts_written") != []:
        raise RuntimeError(f"{label} reports a protected artifact write.")
    boundary = payload.get("claim_boundary")
    if not isinstance(boundary, Mapping) or boundary.get("outcome_columns_passed") != []:
        raise RuntimeError(f"{label} claim boundary is not outcome-free.")
    required_true = (
        "retrospective",
        "no_empirical_metric_or_direction",
        "no_policy_or_cap_selection",
        "no_exact_symbolic_optimal_face_claim",
        "no_global_optimal_face_diameter_claim",
    )
    required_false = ("preregistered", "confirmatory", "prospective")
    if any(boundary.get(field) is not True for field in required_true):
        raise RuntimeError(f"{label} claim boundary changed.")
    if any(boundary.get(field) is not False for field in required_false):
        raise RuntimeError(f"{label} retrospective status changed.")


def _require_receipt(
    receipt: Mapping[str, Any],
    *,
    run_tag: str,
    protocol_commit: str,
    summary_path: Path,
) -> None:
    if receipt.get("run_tag") != run_tag:
        raise RuntimeError(f"Execution receipt run identity changed: {run_tag}.")
    descriptor = receipt.get("deterministic_summary")
    if not isinstance(descriptor, Mapping):
        raise TypeError("Execution receipt summary descriptor is invalid.")
    _verify_descriptor(
        descriptor,
        expected_path=summary_path.resolve().relative_to(ROOT.resolve()).as_posix(),
    )
    for phase in ("initial_git", "final_git"):
        git = receipt.get(phase)
        if not isinstance(git, Mapping):
            raise TypeError(f"Execution receipt {phase} is invalid.")
        if git.get("commit") != protocol_commit or git.get("dirty") is not False:
            raise RuntimeError(f"Execution receipt {phase} provenance changed.")
        if git.get("dirty_entries") != 0 or git.get("dirty_paths") != []:
            raise RuntimeError(f"Execution receipt {phase} was not clean.")


def _require_solver_contract(
    summary: Mapping[str, Any], freeze: Mapping[str, Any], receipt: Mapping[str, Any]
) -> None:
    contracts = [
        summary.get("solver_contract"),
        freeze.get("solver_contract"),
        receipt.get("solver_contract"),
    ]
    if not all(isinstance(contract, Mapping) for contract in contracts):
        raise TypeError("A solver contract is not a mapping.")
    if contracts[0] != contracts[1] or contracts[0] != contracts[2]:
        raise RuntimeError("Solver contracts disagree within a run.")
    contract = contracts[0]
    assert isinstance(contract, Mapping)
    expected = {
        "highspy_version": "1.15.1",
        "highs_native_version": "1.15.1",
        "highs_githash": "04024d7",
        "solver": "simplex",
        "presolve": "on",
        "threads": 1,
        "dual_feasibility_tolerance": DUAL_SIGN_TOLERANCE,
        "primal_feasibility_tolerance": PRIMAL_FEASIBILITY_TOLERANCE,
    }
    for field, value in expected.items():
        if contract.get(field) != value:
            raise RuntimeError(f"Solver contract changed: {field}.")


def _verify_schema(path: Path, frame: pd.DataFrame, schema: Mapping[str, Any]) -> None:
    actual = {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "dtypes": {str(name): str(dtype) for name, dtype in frame.dtypes.items()},
    }
    if actual != schema:
        raise RuntimeError(f"Persisted parquet schema changed: {path}.")


def _load_parquets(
    paths: Mapping[str, Path], *, schemas: Mapping[str, Any]
) -> dict[str, pd.DataFrame]:
    parquet_paths = {key: path for key, path in paths.items() if path.suffix == ".parquet"}
    if set(parquet_paths) != set(schemas):
        raise RuntimeError("Summary schema census does not match artifact census.")
    frames: dict[str, pd.DataFrame] = {}
    forbidden = (
        "loan_status",
        "default",
        "charged_off",
        "pymnt",
        "realized",
        "miscoverage",
        "payoff",
    )
    for key in sorted(parquet_paths):
        schema = schemas[key]
        if not isinstance(schema, Mapping):
            raise TypeError(f"Schema is not a mapping: {key}.")
        frame = pd.read_parquet(parquet_paths[key])
        _verify_schema(parquet_paths[key], frame, schema)
        contaminated = [
            str(column)
            for column in frame.columns
            if any(token in str(column).lower() for token in forbidden)
        ]
        if contaminated:
            raise RuntimeError(f"Outcome-like columns found in {key}: {contaminated}.")
        stem = parquet_paths[key].stem
        if stem in frames:
            raise RuntimeError(f"Duplicate parquet basename: {stem}.")
        frames[stem] = frame
    return frames


def _max_abs(frame: pd.DataFrame, columns: Sequence[str]) -> float:
    values = frame.loc[:, list(columns)].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise RuntimeError(f"Nonfinite numerical values in {list(columns)}.")
    return float(np.max(np.abs(values))) if values.size else 0.0


def _max_value(frame: pd.DataFrame, column: str) -> float:
    values = frame[column].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise RuntimeError(f"Nonfinite numerical values in {column}.")
    return float(np.max(values)) if values.size else 0.0


def _all_true(frame: pd.DataFrame, columns: Sequence[str]) -> bool:
    return bool(frame.loc[:, list(columns)].to_numpy(dtype=bool).all())


def _basis_contract(frame: pd.DataFrame) -> dict[str, Any]:
    validity_columns = ("basis_valid", "basis_dimension_valid", "value_valid", "dual_valid")
    validity_passed = _all_true(frame, validity_columns)
    unsupported = int(
        frame[["unsupported_nonbasic_columns", "unsupported_movable_nonbasic_rows"]]
        .to_numpy(dtype=np.int64)
        .sum()
    )
    maximum_dual_sign_violation = _max_abs(
        frame, ("maximum_dual_sign_violation", "maximum_scaled_dual_sign_violation")
    )
    maximum_objective_reconciliation_error = _max_abs(
        frame,
        (
            "raw_objective_internal_reconciliation_error",
            "objective_reconciliation_error",
            "solution_to_raw_solver_objective_error",
        ),
    )
    maximum_policy_violation = _max_value(frame, "maximum_normalized_policy_constraint_violation")
    maximum_primal_bound_violation = _max_value(frame, "maximum_primal_bound_violation")
    passed = bool(
        validity_passed
        and unsupported == 0
        and maximum_dual_sign_violation <= DUAL_SIGN_TOLERANCE
        and maximum_objective_reconciliation_error <= OBJECTIVE_RECONCILIATION_TOLERANCE
        and maximum_policy_violation <= POLICY_FEASIBILITY_TOLERANCE
        and maximum_primal_bound_violation <= PRIMAL_FEASIBILITY_TOLERANCE
    )
    return {
        "rows": int(len(frame)),
        "periods": int(frame["period"].nunique()),
        "valid_basis_solution_rows": int(
            frame.loc[:, list(validity_columns)].astype(bool).all(axis=1).sum()
        ),
        "unsupported_nonbasic_statuses": unsupported,
        "maximum_dual_sign_violation": maximum_dual_sign_violation,
        "maximum_absolute_objective_reconciliation_error": maximum_objective_reconciliation_error,
        "maximum_normalized_policy_constraint_violation": maximum_policy_violation,
        "maximum_primal_bound_violation": maximum_primal_bound_violation,
        "numerical_contract_passed": passed,
    }


def _row_detail_contract(frame: pd.DataFrame) -> dict[str, Any]:
    statuses = sorted(str(value) for value in frame["basis_status"].unique())
    maximum_bound_violation = _max_abs(frame, ("lower_bound_violation", "upper_bound_violation"))
    passed = bool(
        set(statuses).issubset({"basic", "upper"})
        and maximum_bound_violation <= PRIMAL_FEASIBILITY_TOLERANCE
    )
    return {
        "rows": int(len(frame)),
        "basis_statuses": statuses,
        "near_zero_nonbasic_rows": int(frame["is_near_zero_nonbasic"].sum()),
        "maximum_row_bound_violation": maximum_bound_violation,
        "row_contract_passed": passed,
    }


def _merge_intervals(
    intervals: Sequence[tuple[float, float]], *, tolerance: float
) -> tuple[tuple[float, float], ...]:
    ordered = sorted((float(left), float(right)) for left, right in intervals)
    if tolerance < 0.0 or any(
        not np.isfinite([left, right]).all() or left > right for left, right in ordered
    ):
        raise RuntimeError("Coverage intervals are invalid.")
    merged: list[list[float]] = []
    for left, right in ordered:
        if not merged or left > merged[-1][1] + tolerance:
            merged.append([left, right])
        else:
            merged[-1][1] = max(merged[-1][1], right)
    return tuple((left, right) for left, right in merged)


def _support_gaps(
    intervals: Sequence[tuple[float, float]], *, tolerance: float
) -> tuple[tuple[float, float], ...]:
    clipped = [
        (max(left, SUPPORT_LOWER), min(right, SUPPORT_UPPER))
        for left, right in _merge_intervals(intervals, tolerance=tolerance)
        if right >= SUPPORT_LOWER - tolerance and left <= SUPPORT_UPPER + tolerance
    ]
    cursor = SUPPORT_LOWER
    gaps: list[tuple[float, float]] = []
    for left, right in clipped:
        if left > cursor + tolerance:
            gaps.append((cursor, left))
        cursor = max(cursor, right)
    if cursor < SUPPORT_UPPER - tolerance:
        gaps.append((cursor, SUPPORT_UPPER))
    return tuple(gaps)


def _coverage_results(
    corrected: pd.DataFrame,
    gap_diagnostics: pd.DataFrame,
    persisted: pd.DataFrame,
) -> dict[str, Any]:
    periods = sorted(str(value) for value in corrected["period"].unique())
    if len(periods) != 15 or set(periods) != set(gap_diagnostics["period"].unique()):
        raise RuntimeError("RHS coverage period census changed.")
    if len(gap_diagnostics) != 196:
        raise RuntimeError("Registered gap-seed census changed.")
    seed_status_counts = gap_diagnostics["risk_row_basis_status"].value_counts().to_dict()
    if not set(seed_status_counts).issubset({"upper", "basic"}):
        raise RuntimeError("A gap seed has an unsupported risk-row basis status.")
    upper_seeds = gap_diagnostics.loc[gap_diagnostics["risk_row_basis_status"].eq("upper")]
    basic_seeds = gap_diagnostics.loc[gap_diagnostics["risk_row_basis_status"].eq("basic")]
    if not np.allclose(
        upper_seeds[["status_aware_rhs_lower", "status_aware_rhs_upper"]],
        upper_seeds[["reported_activity_range_lower", "reported_activity_range_upper"]],
        rtol=0.0,
        atol=0.0,
    ):
        raise RuntimeError("An upper-row gap seed changed its HiGHS RHS-range semantics.")
    if len(basic_seeds) and (
        not np.allclose(
            basic_seeds["status_aware_rhs_lower"],
            basic_seeds["risk_row_value_dollars"] / BUDGET_DOLLARS,
            rtol=0.0,
            atol=1.0e-15,
        )
        or not np.allclose(
            basic_seeds["status_aware_rhs_upper"],
            1.0,
            rtol=0.0,
            atol=0.0,
        )
        or _max_abs(basic_seeds, ("risk_row_dual",)) > 1.0e-12
    ):
        raise RuntimeError("A basic-row gap seed changed its zero-dual safe-ray semantics.")
    target_midpoints = (
        gap_diagnostics["target_gap_lower"].to_numpy(dtype=float)
        + gap_diagnostics["target_gap_upper"].to_numpy(dtype=float)
    ) / 2.0
    registered_seeds = gap_diagnostics["registered_seed_cap"].to_numpy(dtype=float)
    recomputed_midpoint_distance = np.abs(registered_seeds - target_midpoints)
    if not np.allclose(
        gap_diagnostics["target_gap_midpoint"].to_numpy(dtype=float),
        target_midpoints,
        rtol=0.0,
        atol=1.0e-15,
    ) or not np.allclose(
        gap_diagnostics["seed_midpoint_match_distance"].to_numpy(dtype=float),
        recomputed_midpoint_distance,
        rtol=0.0,
        atol=1.0e-18,
    ):
        raise RuntimeError("Registered gap seeds do not reconcile to their midpoints.")
    maximum_seed_midpoint_match_distance = float(recomputed_midpoint_distance.max())
    maximum_v2_seed_expected_objective_difference = _max_abs(
        gap_diagnostics,
        ("v2_seed_expected_objective_difference",),
    )
    maximum_v2_seed_weighted_point_difference = _max_abs(
        gap_diagnostics,
        ("v2_seed_weighted_point_difference",),
    )
    strict_interior_seed = (
        registered_seeds > gap_diagnostics["target_gap_lower"].to_numpy(dtype=float)
    ) & (registered_seeds < gap_diagnostics["target_gap_upper"].to_numpy(dtype=float))
    recomputed_cap_containment = (
        gap_diagnostics["status_aware_rhs_lower"].to_numpy(dtype=float)
        <= registered_seeds + GAP_TOLERANCE
    ) & (
        registered_seeds
        <= gap_diagnostics["status_aware_rhs_upper"].to_numpy(dtype=float) + GAP_TOLERANCE
    )
    recomputed_target_coverage = (
        gap_diagnostics["status_aware_rhs_lower"].to_numpy(dtype=float)
        <= gap_diagnostics["target_gap_lower"].to_numpy(dtype=float) + GAP_TOLERANCE
    ) & (
        gap_diagnostics["status_aware_rhs_upper"].to_numpy(dtype=float)
        >= gap_diagnostics["target_gap_upper"].to_numpy(dtype=float) - GAP_TOLERANCE
    )
    if (
        maximum_seed_midpoint_match_distance > 1.0e-12
        or maximum_v2_seed_expected_objective_difference > OBJECTIVE_RECONCILIATION_TOLERANCE
        or maximum_v2_seed_weighted_point_difference > LATERAL_POINT_TOLERANCE
        or not bool(strict_interior_seed.all())
        or not np.array_equal(
            recomputed_cap_containment,
            gap_diagnostics["status_aware_cap_contained"].to_numpy(dtype=bool),
        )
        or not bool(recomputed_cap_containment.all())
        or not np.array_equal(
            recomputed_target_coverage,
            gap_diagnostics["target_gap_covered"].to_numpy(dtype=bool),
        )
        or not bool(recomputed_target_coverage.all())
    ):
        raise RuntimeError("A registered gap seed fails its midpoint or interval contract.")
    rows: list[dict[str, Any]] = []
    reconstructed_gaps: list[tuple[str, int, float, float]] = []
    zero_tolerance_seam_widths: list[float] = []
    positive_gaps_at_1e_15 = 0
    for period in periods:
        central = corrected.loc[corrected["period"].eq(period)]
        seeds = gap_diagnostics.loc[gap_diagnostics["period"].eq(period)].sort_values("gap_index")
        central_intervals = list(
            zip(
                central["status_aware_rhs_lower"].astype(float),
                central["status_aware_rhs_upper"].astype(float),
                strict=True,
            )
        )
        seed_intervals = list(
            zip(
                seeds["status_aware_rhs_lower"].astype(float),
                seeds["status_aware_rhs_upper"].astype(float),
                strict=True,
            )
        )
        initial_merged = _merge_intervals(central_intervals, tolerance=GAP_TOLERANCE)
        final_merged = _merge_intervals(
            [*central_intervals, *seed_intervals], tolerance=GAP_TOLERANCE
        )
        all_intervals = [*central_intervals, *seed_intervals]
        zero_tolerance_gaps = _support_gaps(
            _merge_intervals(all_intervals, tolerance=0.0),
            tolerance=0.0,
        )
        zero_tolerance_seam_widths.extend(right - left for left, right in zero_tolerance_gaps)
        positive_gaps_at_1e_15 += len(
            _support_gaps(
                _merge_intervals(all_intervals, tolerance=1.0e-15),
                tolerance=1.0e-15,
            )
        )
        initial_gaps = _support_gaps(initial_merged, tolerance=GAP_TOLERANCE)
        final_gaps = _support_gaps(final_merged, tolerance=GAP_TOLERANCE)
        for gap_index, (left, right) in enumerate(initial_gaps, start=1):
            reconstructed_gaps.append((period, gap_index, left, right))
        rows.append(
            {
                "period": period,
                "support_lower": SUPPORT_LOWER,
                "support_upper": SUPPORT_UPPER,
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
    recomputed = pd.DataFrame(rows).sort_values("period").reset_index(drop=True)
    persisted_sorted = persisted.sort_values("period").reset_index(drop=True)
    if list(recomputed.columns) != list(persisted_sorted.columns):
        raise RuntimeError("Persisted coverage columns changed.")
    for column in recomputed.columns:
        left = recomputed[column]
        right = persisted_sorted[column]
        if pd.api.types.is_float_dtype(left):
            if not np.allclose(left, right, rtol=0.0, atol=1.0e-15):
                raise RuntimeError(f"Persisted coverage differs from recomputation: {column}.")
        elif not left.equals(right):
            raise RuntimeError(f"Persisted coverage differs from recomputation: {column}.")

    target = gap_diagnostics.sort_values(["period", "gap_index"]).reset_index(drop=True)
    reconstructed = pd.DataFrame(
        reconstructed_gaps, columns=["period", "gap_index", "target_gap_lower", "target_gap_upper"]
    )
    if len(reconstructed) != 196 or len(target) != 196:
        raise RuntimeError("Initial positive-gap census changed.")
    if not reconstructed[["period", "gap_index"]].equals(target[["period", "gap_index"]]):
        raise RuntimeError("Gap keys do not reconcile to the central interval union.")
    maximum_gap_reconstruction_difference = _max_abs(
        reconstructed.assign(
            lower_difference=(reconstructed["target_gap_lower"] - target["target_gap_lower"]),
            upper_difference=(reconstructed["target_gap_upper"] - target["target_gap_upper"]),
        ),
        ("lower_difference", "upper_difference"),
    )
    if maximum_gap_reconstruction_difference > 1.0e-15:
        raise RuntimeError("Registered gaps do not match the recomputed initial gaps.")
    return {
        "periods": int(len(recomputed)),
        "registered_support_lower": SUPPORT_LOWER,
        "registered_support_upper": SUPPORT_UPPER,
        "absolute_gap_tolerance": GAP_TOLERANCE,
        "initial_positive_gaps": int(recomputed["initial_positive_gaps"].sum()),
        "maximum_initial_positive_gap": float(recomputed["initial_maximum_positive_gap"].max()),
        "initial_total_uncovered_width": float(recomputed["initial_total_uncovered_width"].sum()),
        "registered_gap_seed_solves": int(recomputed["registered_gap_seed_rows"].sum()),
        "upper_status_gap_seed_solves": int(len(upper_seeds)),
        "basic_status_gap_seed_solves": int(len(basic_seeds)),
        "strictly_interior_gap_seed_solves": int(strict_interior_seed.sum()),
        "maximum_seed_midpoint_match_distance": maximum_seed_midpoint_match_distance,
        "maximum_v2_seed_expected_objective_difference": (
            maximum_v2_seed_expected_objective_difference
        ),
        "maximum_v2_seed_weighted_point_difference": (maximum_v2_seed_weighted_point_difference),
        "status_aware_seed_cap_containment_passes": int(recomputed_cap_containment.sum()),
        "targeted_gap_coverage_passes": int(gap_diagnostics["target_gap_covered"].sum()),
        "recomputed_target_gap_coverage_passes": int(recomputed_target_coverage.sum()),
        "final_positive_gaps": int(recomputed["final_positive_gaps"].sum()),
        "maximum_final_positive_gap": float(recomputed["final_maximum_positive_gap"].max()),
        "covered_periods": int(recomputed["registered_support_covered"].sum()),
        "zero_tolerance_positive_seams": int(len(zero_tolerance_seam_widths)),
        "maximum_zero_tolerance_seam_width": float(max(zero_tolerance_seam_widths)),
        "total_zero_tolerance_seam_width": float(sum(zero_tolerance_seam_widths)),
        "positive_gaps_at_1e_15": int(positive_gaps_at_1e_15),
        "maximum_gap_reconstruction_difference": maximum_gap_reconstruction_difference,
        "persisted_coverage_table_reconciled": True,
        "rhs_support_coverage_gate_passed": bool(
            recomputed["registered_support_covered"].all()
            and recomputed["all_targeted_gaps_covered"].all()
            and int(recomputed["final_positive_gaps"].sum()) == 0
        ),
    }


def _status_aware_results(corrected: pd.DataFrame) -> dict[str, Any]:
    if len(corrected) != 7_297 or corrected["period"].nunique() != 15:
        raise RuntimeError("Corrected central RHS census changed.")
    status_counts = corrected["risk_row_basis_status"].value_counts().to_dict()
    if status_counts != {"upper": 7_228, "basic": 69}:
        raise RuntimeError("Central risk-row status census changed.")
    upper = corrected.loc[corrected["risk_row_basis_status"].eq("upper")]
    basic = corrected.loc[corrected["risk_row_basis_status"].eq("basic")]
    if not np.allclose(
        upper[["status_aware_rhs_lower", "status_aware_rhs_upper"]],
        upper[
            [
                "v2_reported_domain_clipped_range_lower",
                "v2_reported_domain_clipped_range_upper",
            ]
        ],
        rtol=0.0,
        atol=0.0,
    ):
        raise RuntimeError("Active upper-row RHS interpretation changed.")
    if not np.allclose(
        basic["status_aware_rhs_lower"],
        basic["risk_row_value_dollars"] / BUDGET_DOLLARS,
        rtol=0.0,
        atol=1.0e-15,
    ) or not np.allclose(basic["status_aware_rhs_upper"], 1.0, rtol=0.0, atol=0.0):
        raise RuntimeError("Basic-row upper-RHS ray is inconsistent with activity.")
    if _max_abs(basic, ("risk_row_dual",)) > 1.0e-12:
        raise RuntimeError("A basic risk row has a nonzero dual multiplier.")
    cap = corrected["point_cap"].to_numpy(dtype=float)
    lower = corrected["status_aware_rhs_lower"].to_numpy(dtype=float)
    upper_bound = corrected["status_aware_rhs_upper"].to_numpy(dtype=float)
    maximum_containment_violation = float(
        np.maximum.reduce([lower - cap, cap - upper_bound, np.zeros(len(corrected))]).max()
    )
    corrected_passes = int(corrected["status_aware_cap_contained"].sum())
    if corrected_passes != 7_297 or maximum_containment_violation > GAP_TOLERANCE:
        raise RuntimeError("Status-aware central cap containment failed.")
    return {
        "rows": int(len(corrected)),
        "periods": int(corrected["period"].nunique()),
        "upper_rows": int(status_counts["upper"]),
        "basic_rows": int(status_counts["basic"]),
        "v2_reported_domain_clipped_cap_containment_failures": int(
            (~corrected["v2_reported_domain_clipped_cap_contained"]).sum()
        ),
        "status_aware_cap_containment_passes": corrected_passes,
        "maximum_status_aware_cap_containment_violation": maximum_containment_violation,
        "basic_row_maximum_absolute_dual": _max_abs(basic, ("risk_row_dual",)),
        "status_aware_semantics_gate_passed": True,
    }


def _warning_and_mobility_results(
    v2_warnings: pd.DataFrame,
    v3a_warnings: pd.DataFrame,
    v2_central: pd.DataFrame,
    v2_lateral: pd.DataFrame,
    v3a_gaps: pd.DataFrame,
    face_ranges: pd.DataFrame,
    column_registry: pd.DataFrame,
) -> dict[str, Any]:
    if len(v2_warnings) != 13 or len(v3a_warnings) != 1 or len(face_ranges) != 8:
        raise RuntimeError("Scale-aware warning or conditional-range census changed.")
    if int(v2_central["near_zero_nonbasic_total"].sum()) != 5:
        raise RuntimeError("V2 central warning count does not reconcile.")
    if int(v2_lateral["near_zero_nonbasic_total"].sum()) != 8:
        raise RuntimeError("V2 lateral warning count does not reconcile.")
    if int(v3a_gaps["near_zero_nonbasic_total"].sum()) != 1:
        raise RuntimeError("V3a gap warning count does not reconcile.")
    for warnings in (v2_warnings, v3a_warnings):
        if not bool(
            (warnings["scaled_absolute_dual_or_reduced_cost"] <= NEAR_ZERO_SCALED_THRESHOLD).all()
        ):
            raise RuntimeError("A persisted warning lies outside the locked scaled band.")
        if not bool(
            (
                warnings["absolute_dual_or_reduced_cost"]
                <= warnings["near_zero_threshold"] + np.finfo(float).eps
            ).all()
        ):
            raise RuntimeError("A persisted warning lies outside its absolute band.")
    unique_v2_targets = int(
        v2_warnings.drop_duplicates(
            ["period", "point_cap", "variable_kind", "variable_index"]
        ).shape[0]
    )
    if unique_v2_targets != 8:
        raise RuntimeError("V2 warning-target census changed.")
    gap_warning = v3a_warnings.iloc[0]
    same_variable = v2_warnings.loc[
        v2_warnings["period"].eq(gap_warning["period"])
        & v2_warnings["variable_kind"].eq(gap_warning["variable_kind"])
        & v2_warnings["variable_index"].eq(gap_warning["variable_index"])
        & v2_warnings["variable_name"].astype(str).eq(str(gap_warning["variable_name"]))
    ]
    lower_neighbor = same_variable.loc[
        same_variable["solve_origin"].eq("right")
        & np.isclose(
            same_variable["point_cap"],
            float(gap_warning["target_gap_lower"]),
            rtol=0.0,
            atol=1.0e-12,
        )
        & np.isclose(
            same_variable["seed_cap"],
            float(gap_warning["registered_seed_cap"]),
            rtol=0.0,
            atol=1.0e-12,
        )
    ]
    upper_neighbor = same_variable.loc[
        same_variable["solve_origin"].eq("left")
        & np.isclose(
            same_variable["point_cap"],
            float(gap_warning["target_gap_upper"]),
            rtol=0.0,
            atol=1.0e-12,
        )
        & np.isclose(
            same_variable["seed_cap"],
            float(gap_warning["registered_seed_cap"]),
            rtol=0.0,
            atol=1.0e-12,
        )
    ]
    warning_repeats_neighbor_variable = bool(len(lower_neighbor) == 1 and len(upper_neighbor) == 1)
    if not warning_repeats_neighbor_variable:
        raise RuntimeError("The V3a gap warning no longer matches both warned V2 endpoints.")
    required_face_flags = (
        "primary_objective_reconciliation_passed",
        "objective_band_passed",
        "face_range_consistency_passed",
        "epsilon_near_optimal_mobility_detected",
    )
    if not _all_true(face_ranges, required_face_flags):
        raise RuntimeError("A conditional epsilon-near-optimal range failed its contract.")
    face_numeric_columns = (
        "minimum_solver_run_time_seconds",
        "maximum_solver_run_time_seconds",
        "minimum_maximum_column_bound_violation",
        "minimum_maximum_row_bound_violation",
        "maximum_maximum_column_bound_violation",
        "maximum_maximum_row_bound_violation",
    )
    if not np.isfinite(face_ranges[list(face_numeric_columns)].to_numpy(dtype=float)).all():
        raise RuntimeError("A conditional range has a non-finite runtime or bound audit.")
    if not bool(
        face_ranges[["minimum_solver_run_time_seconds", "maximum_solver_run_time_seconds"]]
        .ge(0.0)
        .all()
        .all()
    ):
        raise RuntimeError("A conditional range has a negative solver runtime.")
    maximum_face_primal_bound_violation = _max_abs(
        face_ranges,
        (
            "minimum_maximum_column_bound_violation",
            "minimum_maximum_row_bound_violation",
            "maximum_maximum_column_bound_violation",
            "maximum_maximum_row_bound_violation",
        ),
    )
    if maximum_face_primal_bound_violation > PRIMAL_FEASIBILITY_TOLERANCE:
        raise RuntimeError("A conditional range violates its primal bound contract.")
    if not face_ranges["variable_kind"].eq("column").all():
        raise RuntimeError("The V2 mobility conversion only supports structural columns.")
    mobility = face_ranges.merge(
        column_registry[["period", "column_index", "loan_amount", "candidate_id"]],
        left_on=["period", "variable_index"],
        right_on=["period", "column_index"],
        how="left",
        validate="many_to_one",
    )
    if mobility["loan_amount"].isna().any():
        raise RuntimeError("A conditional range lacks its column-registry exposure scale.")
    if not mobility["variable_name"].astype(str).eq(mobility["candidate_id"].astype(str)).all():
        raise RuntimeError("Conditional range candidate identity changed.")
    mobility["coordinate_exposure_mobility_dollars"] = mobility["value_range"].astype(
        float
    ) * mobility["loan_amount"].astype(float)
    normalized_dollars = mobility["normalized_mobility"].astype(float) * BUDGET_DOLLARS
    if not np.allclose(
        mobility["coordinate_exposure_mobility_dollars"],
        normalized_dollars,
        rtol=0.0,
        atol=1.0e-10,
    ):
        raise RuntimeError("Conditional mobility normalization changed.")
    return {
        "v2_warning_rows": int(len(v2_warnings)),
        "v2_central_warning_rows": int(v2_warnings["solve_origin"].eq("central").sum()),
        "v2_lateral_warning_rows": int(v2_warnings["solve_origin"].isin(["left", "right"]).sum()),
        "v2_unique_cap_variable_targets": unique_v2_targets,
        "v3a_gap_seed_warning_rows": int(len(v3a_warnings)),
        "v3a_warning_repeats_same_v2_variable_at_both_neighbor_endpoints": True,
        "v3a_warning_period": str(gap_warning["period"]),
        "v3a_warning_variable_name": str(gap_warning["variable_name"]),
        "v3a_warning_registered_seed_cap": float(gap_warning["registered_seed_cap"]),
        "combined_warning_rows": int(len(v2_warnings) + len(v3a_warnings)),
        "v2_conditional_range_rows": int(len(face_ranges)),
        "minimum_conditional_solver_run_time_seconds": float(
            face_ranges[["minimum_solver_run_time_seconds", "maximum_solver_run_time_seconds"]]
            .min()
            .min()
        ),
        "maximum_conditional_solver_run_time_seconds": float(
            face_ranges[["minimum_solver_run_time_seconds", "maximum_solver_run_time_seconds"]]
            .max()
            .max()
        ),
        "maximum_conditional_face_primal_bound_violation": (maximum_face_primal_bound_violation),
        "maximum_v2_normalized_coordinate_mobility": float(
            face_ranges["normalized_mobility"].max()
        ),
        "maximum_v2_coordinate_exposure_mobility_dollars": float(
            mobility["coordinate_exposure_mobility_dollars"].max()
        ),
        "epsilon_near_optimal_mobility_is_exact_alternate_optimum": False,
        "warnings_block_strict_numerical_uniqueness_promotion": True,
        "strict_numerical_uniqueness_gate_passed": False,
    }


def _lateral_results(original: pd.DataFrame, corrected: pd.DataFrame) -> dict[str, Any]:
    keys = ["period", "point_cap"]
    original_sorted = original.sort_values(keys).reset_index(drop=True)
    corrected_sorted = corrected.sort_values(keys).reset_index(drop=True)
    if len(original_sorted) != 2_952 or len(corrected_sorted) != 2_952:
        raise RuntimeError("Breakpoint comparison census changed.")
    corrected_field = "allocation_difference_cooccurs_with_same_cap_epsilon_mobility"
    unchanged = [column for column in original_sorted.columns if column != corrected_field]
    if not original_sorted[unchanged].equals(corrected_sorted[unchanged]):
        raise RuntimeError("V3a changed a lateral field other than the registered correction.")
    allocation_differs = (
        corrected_sorted["maximum_pairwise_allocation_distance"] > ALLOCATION_DISTANCE_TOLERANCE
    )
    expected_cooccurrence = allocation_differs & original_sorted[corrected_field].astype(bool)
    if not corrected_sorted[corrected_field].astype(bool).equals(expected_cooccurrence):
        raise RuntimeError("Corrected lateral cooccurrence field is inconsistent.")
    expected_without = allocation_differs & ~original_sorted[corrected_field].astype(bool)
    if (
        not corrected_sorted["allocation_difference_without_same_cap_epsilon_mobility"]
        .astype(bool)
        .equals(expected_without)
    ):
        raise RuntimeError("Corrected lateral difference-without-mobility field is inconsistent.")
    expected_objective = (
        corrected_sorted["maximum_pairwise_objective_difference"] > LATERAL_OBJECTIVE_TOLERANCE
    )
    expected_point = (
        corrected_sorted["maximum_pairwise_weighted_point_difference"] > LATERAL_POINT_TOLERANCE
    )
    expected_numerical = allocation_differs | expected_objective | expected_point
    if (
        not corrected_sorted["lateral_objective_discrepancy"]
        .astype(bool)
        .equals(expected_objective)
    ):
        raise RuntimeError("Lateral objective discrepancy field is inconsistent.")
    if (
        not corrected_sorted["lateral_weighted_point_discrepancy"]
        .astype(bool)
        .equals(expected_point)
    ):
        raise RuntimeError("Lateral point discrepancy field is inconsistent.")
    if (
        not corrected_sorted["lateral_numerical_discrepancy"]
        .astype(bool)
        .equals(expected_numerical)
    ):
        raise RuntimeError("Lateral composite discrepancy field is inconsistent.")
    return {
        "breakpoint_rows": int(len(corrected_sorted)),
        "allocation_difference_rows": int(allocation_differs.sum()),
        "corrected_same_cap_mobility_cooccurrence_rows": int(expected_cooccurrence.sum()),
        "allocation_difference_without_same_cap_mobility_rows": int(expected_without.sum()),
        "lateral_objective_discrepancy_rows": int(expected_objective.sum()),
        "lateral_weighted_point_discrepancy_rows": int(expected_point.sum()),
        "maximum_pairwise_allocation_distance": float(
            corrected_sorted["maximum_pairwise_allocation_distance"].max()
        ),
        "maximum_pairwise_objective_difference": float(
            corrected_sorted["maximum_pairwise_objective_difference"].max()
        ),
        "maximum_pairwise_weighted_point_difference": float(
            corrected_sorted["maximum_pairwise_weighted_point_difference"].max()
        ),
        "v2_misreported_cooccurrence_rows": int(original_sorted[corrected_field].sum()),
        "corrected_lateral_gate_passed": bool(not expected_numerical.any()),
    }


def _frozen_reconciliation_results(frame: pd.DataFrame) -> dict[str, Any]:
    if len(frame) != 7_297 or not bool(frame["frozen_allocation_reconciliation_passed"].all()):
        raise RuntimeError("Frozen-allocation reconciliation census failed.")
    return {
        "rows": int(len(frame)),
        "passed_rows": int(frame["frozen_allocation_reconciliation_passed"].sum()),
        "maximum_l1_exposure_dollars": _max_value(frame, "fresh_vs_frozen_l1_exposure_dollars"),
        "maximum_normalized_l1_exposure": _max_value(
            frame, "fresh_vs_frozen_normalized_l1_exposure"
        ),
        "maximum_absolute_objective_difference": _max_abs(
            frame, ("fresh_vs_frozen_expected_objective_difference",)
        ),
        "maximum_absolute_weighted_point_difference": _max_abs(
            frame, ("fresh_vs_frozen_weighted_point_difference",)
        ),
        "frozen_allocation_reconciliation_gate_passed": True,
    }


def _reconcile_source_summaries(
    v2_summary: Mapping[str, Any], v3a_summary: Mapping[str, Any], results: Mapping[str, Any]
) -> None:
    v2 = v2_summary["results"]
    v3a = v3a_summary["results"]
    checks = {
        "v2 central rows": (
            v2["central"]["rows"],
            results["numerical_contracts"]["v2_central"]["rows"],
        ),
        "v2 warning rows": (
            v2["conditional_face"]["warning_rows"],
            results["warnings_and_mobility"]["v2_warning_rows"],
        ),
        "v2 range rows": (
            v2["conditional_face"]["range_rows"],
            results["warnings_and_mobility"]["v2_conditional_range_rows"],
        ),
        "v3a corrected rows": (
            v3a["status_aware_central"]["rows"],
            results["status_aware_rhs_semantics"]["rows"],
        ),
        "v3a gap rows": (
            v3a["gap_replay"]["rows"],
            results["rhs_support_coverage"]["registered_gap_seed_solves"],
        ),
        "v3a covered periods": (
            v3a["gap_replay"]["final_covered_periods"],
            results["rhs_support_coverage"]["covered_periods"],
        ),
        "v3a warning rows": (
            v3a["gap_replay"]["scale_aware_warning_entities"],
            results["warnings_and_mobility"]["v3a_gap_seed_warning_rows"],
        ),
        "v3a lateral rows": (
            v3a["lateral_reporting_correction"]["breakpoint_rows"],
            results["corrected_lateral_stability"]["breakpoint_rows"],
        ),
    }
    for label, (reported, recomputed) in checks.items():
        if reported != recomputed:
            raise RuntimeError(f"Source summary does not reconcile: {label}.")
    if v2.get("finite_grid_numerical_uniqueness_gate_passed") is not False:
        raise RuntimeError("V2 uniqueness gate was unexpectedly promoted.")
    if v3a.get("strict_numerical_uniqueness_gate_passed") is not False:
        raise RuntimeError("V3a uniqueness gate was unexpectedly promoted.")
    if v3a.get("rhs_support_coverage_gate_passed") is not True:
        raise RuntimeError("V3a RHS support gate does not report recovery.")


def _source_bundle(
    *,
    summary_path: Path,
    receipt_path: Path,
    summary: Mapping[str, Any],
    artifacts: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "run_tag": summary["run_tag"],
        "protocol_tag": summary["protocol_tag"],
        "protocol_commit": summary["protocol_commit"],
        "summary": relative_artifact_descriptor(summary_path, repo_root=ROOT),
        "execution_receipt": relative_artifact_descriptor(receipt_path, repo_root=ROOT),
        "verified_artifacts": {key: artifacts[key] for key in sorted(artifacts)},
    }


def build() -> Path:
    """Verify immutable lineages, recompute every gate, and atomically emit evidence."""
    v2_summary = _json(V2_SUMMARY_PATH)
    v2_receipt = _json(V2_RECEIPT_PATH)
    v3a_summary = _json(V3A_SUMMARY_PATH)
    v3a_receipt = _json(V3A_RECEIPT_PATH)

    _require_identity(
        v2_summary,
        label="V2 summary",
        run_tag=V2_RUN_TAG,
        protocol_tag=V2_PROTOCOL_TAG,
        protocol_commit=V2_PROTOCOL_COMMIT,
    )
    _require_identity(
        v3a_summary,
        label="V3a summary",
        run_tag=V3A_RUN_TAG,
        protocol_tag=V3A_PROTOCOL_TAG,
        protocol_commit=V3A_PROTOCOL_COMMIT,
    )
    if _git_tag_commit(V2_PROTOCOL_TAG) != V2_PROTOCOL_COMMIT:
        raise RuntimeError("V2 protocol tag no longer resolves to its locked commit.")
    if _git_tag_commit(V3A_PROTOCOL_TAG) != V3A_PROTOCOL_COMMIT:
        raise RuntimeError("V3a protocol tag no longer resolves to its locked commit.")
    _require_receipt(
        v2_receipt,
        run_tag=V2_RUN_TAG,
        protocol_commit=V2_PROTOCOL_COMMIT,
        summary_path=V2_SUMMARY_PATH,
    )
    _require_receipt(
        v3a_receipt,
        run_tag=V3A_RUN_TAG,
        protocol_commit=V3A_PROTOCOL_COMMIT,
        summary_path=V3A_SUMMARY_PATH,
    )
    _require_outcome_free(v2_summary, label="V2 summary")
    _require_outcome_free(v3a_summary, label="V3a summary")

    v2_artifacts = v2_summary.get("artifacts")
    v3a_artifacts = v3a_summary.get("artifacts")
    if not isinstance(v2_artifacts, Mapping) or not isinstance(v3a_artifacts, Mapping):
        raise TypeError("A result artifact census is not a mapping.")
    v2_paths = _verify_artifact_map(
        v2_artifacts,
        expected_paths=_expected_artifact_paths(
            model_dir=V2_MODEL_DIR,
            data_dir=V2_DATA_DIR,
            basenames=V2_ARTIFACT_BASENAMES,
        ),
    )
    v3a_paths = _verify_artifact_map(
        v3a_artifacts,
        expected_paths=_expected_artifact_paths(
            model_dir=V3A_MODEL_DIR,
            data_dir=V3A_DATA_DIR,
            basenames=V3A_ARTIFACT_BASENAMES,
        ),
    )
    if v3a_summary.get("v2_source_artifacts") != v2_summary.get("artifacts"):
        raise RuntimeError("V3a does not retain the exact V2 artifact descriptor census.")
    v2_source_summary = v3a_summary.get("v2_source_summary")
    if not isinstance(v2_source_summary, Mapping):
        raise TypeError("V3a V2 source-summary descriptor is invalid.")
    _verify_descriptor(
        v2_source_summary,
        expected_path=V2_SUMMARY_PATH.resolve().relative_to(ROOT.resolve()).as_posix(),
    )

    v2_freeze = _json(V2_MODEL_DIR / "protocol_freeze.json")
    v3a_freeze = _json(V3A_MODEL_DIR / "protocol_freeze.json")
    _require_identity(
        v2_freeze,
        label="V2 protocol freeze",
        run_tag=V2_RUN_TAG,
        protocol_tag=V2_PROTOCOL_TAG,
        protocol_commit=V2_PROTOCOL_COMMIT,
    )
    _require_identity(
        v3a_freeze,
        label="V3a protocol freeze",
        run_tag=V3A_RUN_TAG,
        protocol_tag=V3A_PROTOCOL_TAG,
        protocol_commit=V3A_PROTOCOL_COMMIT,
    )
    _require_outcome_free(v2_freeze, label="V2 protocol freeze")
    _require_outcome_free(v3a_freeze, label="V3a protocol freeze")
    if v3a_freeze.get("v2_protocol_commit") != V2_PROTOCOL_COMMIT:
        raise RuntimeError("V3a protocol freeze does not identify the locked V2 commit.")
    if v3a_freeze.get("v2_summary") != v2_source_summary:
        raise RuntimeError("V3a source-summary descriptor differs across its freeze and summary.")
    expected_statuses = {
        "v2_summary": (
            v2_summary.get("schema_version"),
            v2_summary.get("status"),
            "2026-07-21.1",
            "complete_outcome_free_optimal_face_v2_audit",
        ),
        "v2_freeze": (
            v2_freeze.get("schema_version"),
            v2_freeze.get("status"),
            "2026-07-21.1",
            "outcome_free_optimal_face_v2_audit_frozen",
        ),
        "v3a_summary": (
            v3a_summary.get("schema_version"),
            v3a_summary.get("status"),
            "2026-07-21.3",
            "complete_outcome_free_rhs_semantics_recovery_v3a",
        ),
        "v3a_freeze": (
            v3a_freeze.get("schema_version"),
            v3a_freeze.get("status"),
            "2026-07-21.3",
            "outcome_free_rhs_semantics_recovery_v3a_frozen",
        ),
    }
    for label, (schema, status, expected_schema, expected_status) in expected_statuses.items():
        if schema != expected_schema or status != expected_status:
            raise RuntimeError(f"{label} schema or completion status changed.")
    if v2_summary.get("selection") != {
        "cap": None,
        "breakpoint": None,
        "basis": None,
        "tie_break": None,
        "outcome": None,
    }:
        raise RuntimeError("V2 selection boundary changed.")
    if v3a_summary.get("selection") != {
        "cap": None,
        "basis": None,
        "gap": "all_locked_initial_positive_gaps",
        "policy": None,
        "outcome": None,
    }:
        raise RuntimeError("V3a selection boundary changed.")
    _require_solver_contract(v2_summary, v2_freeze, v2_receipt)
    _require_solver_contract(v3a_summary, v3a_freeze, v3a_receipt)

    v2_schemas = v2_summary.get("schemas")
    v3a_schemas = v3a_summary.get("schemas")
    if not isinstance(v2_schemas, Mapping) or not isinstance(v3a_schemas, Mapping):
        raise TypeError("A parquet schema census is not a mapping.")
    v2_frames = _load_parquets(v2_paths, schemas=v2_schemas)
    v3a_frames = _load_parquets(v3a_paths, schemas=v3a_schemas)

    central = v2_frames["central_full_basis_diagnostics"]
    lateral_probes = v2_frames["breakpoint_lateral_probe_diagnostics"]
    v2_rows = v2_frames["row_slack_basis_details"]
    gap_diagnostics = v3a_frames["gap_fill_basis_diagnostics"]
    v3a_rows = v3a_frames["gap_fill_row_slack_details"]
    corrected = v3a_frames["corrected_central_rhs_ranges"]
    coverage = v3a_frames["corrected_rhs_coverage_by_period"]

    numerical_contracts = {
        "v2_central": _basis_contract(central),
        "v2_lateral_probes": _basis_contract(lateral_probes),
        "v3a_gap_replay": _basis_contract(gap_diagnostics),
        "v2_all_row_slack_details": _row_detail_contract(v2_rows),
        "v3a_all_gap_row_slack_details": _row_detail_contract(v3a_rows),
    }
    if not all(
        contract.get("numerical_contract_passed", contract.get("row_contract_passed"))
        for contract in numerical_contracts.values()
    ):
        raise RuntimeError("A recomputed basis, dual, or feasibility contract failed.")

    results: dict[str, Any] = {
        "status_aware_rhs_semantics": _status_aware_results(corrected),
        "rhs_support_coverage": _coverage_results(corrected, gap_diagnostics, coverage),
        "numerical_contracts": numerical_contracts,
        "frozen_allocation_reconciliation": _frozen_reconciliation_results(
            v2_frames["frozen_allocation_reconciliation"]
        ),
        "corrected_lateral_stability": _lateral_results(
            v2_frames["breakpoint_allocation_comparisons"],
            v3a_frames["corrected_lateral_comparisons"],
        ),
        "warnings_and_mobility": _warning_and_mobility_results(
            v2_frames["flagged_nonbasic_variables"],
            v3a_frames["gap_fill_flagged_nonbasic_variables"],
            central,
            lateral_probes,
            gap_diagnostics,
            v2_frames["conditional_optimal_face_ranges"],
            v2_frames["column_registry"],
        ),
    }
    results["rhs_coverage_recovered_without_uniqueness_promotion"] = bool(
        results["rhs_support_coverage"]["rhs_support_coverage_gate_passed"]
        and not results["warnings_and_mobility"]["strict_numerical_uniqueness_gate_passed"]
    )
    _reconcile_source_summaries(v2_summary, v3a_summary, results)
    if results["rhs_support_coverage"]["rhs_support_coverage_gate_passed"] is not True:
        raise RuntimeError("Recomputed RHS support coverage did not pass.")
    if results["warnings_and_mobility"]["strict_numerical_uniqueness_gate_passed"] is not False:
        raise RuntimeError("Strict numerical uniqueness was improperly promoted.")

    evidence = {
        "schema_version": "2026-07-21.1",
        "status": "complete_outcome_free_policy_support_optimal_face_evidence",
        "certification_status": "rhs_support_coverage_recovered_numerical_uniqueness_claim_blocked",
        "publication_role": "registered_intermediate_source_for_single_primary_evidence_manifest",
        "paper_facing_numeric_authority": False,
        "lineage": {
            "v2": _source_bundle(
                summary_path=V2_SUMMARY_PATH,
                receipt_path=V2_RECEIPT_PATH,
                summary=v2_summary,
                artifacts=v2_artifacts,
            ),
            "v3a": _source_bundle(
                summary_path=V3A_SUMMARY_PATH,
                receipt_path=V3A_RECEIPT_PATH,
                summary=v3a_summary,
                artifacts=v3a_artifacts,
            ),
            "verified_result_artifact_descriptors": int(len(v2_artifacts) + len(v3a_artifacts)),
            "verified_deterministic_summary_descriptors": 2,
            "verified_execution_receipt_identity_contracts": 2,
            "lineage_files_described": int(len(v2_artifacts) + len(v3a_artifacts) + 4),
            "protocol_tags_resolve_to_locked_commits": True,
            "v3a_retains_exact_v2_descriptor_census": True,
        },
        "results": results,
        "claim_boundary": {
            "retrospective": True,
            "preregistered": False,
            "confirmatory": False,
            "prospective": False,
            "outcome_columns_passed": [],
            "permissible_conclusion": (
                "Solver-reported RHS ranges for active upper rows, analytically derived "
                "zero-dual safe rays for basic rows, and one nonadaptive replay of all "
                "196 V2 midpoint seeds retrospectively registered in V3a leave no gap "
                "above 1e-10 on the locked [0.05, 0.12] support in all 15 months."
            ),
            "rhs_coverage_is_numerical_and_support_bounded": True,
            "strict_numerical_uniqueness_claim_active": False,
            "exact_symbolic_optimal_face_claim_active": False,
            "exact_nonuniqueness_claim_active": False,
            "global_optimal_face_diameter_claim_active": False,
            "continuous_joint_frontier_uniqueness_claim_active": False,
            "exact_continuous_outcome_envelope_over_all_optimal_allocations_claim_active": False,
            "allocation_continuity_or_seam_conditioning_claim_active": False,
            "epsilon_mobility_is_exact_nonuniqueness_evidence": False,
            "policy_cap_or_tie_break_selected": False,
            "empirical_outcome_direction_claim_active": False,
            "selected_or_funded_set_conformal_claim_active": False,
            "forbidden_inferences": [
                "symbolic or continuous-frontier uniqueness",
                "an exact alternate optimum from epsilon-near-optimal mobility",
                "a global optimal-face diameter bound",
                "an exact continuous outcome envelope over all optimal allocations",
                "allocation continuity or seam conditioning",
                "policy, cap, comparator, or tie-break selection",
                "an empirical outcome direction or selected-set conformal validity",
            ],
        },
        "outcome_columns_passed": [],
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    atomic_write_strict_json(EVIDENCE_PATH, evidence)
    return EVIDENCE_PATH


if __name__ == "__main__":
    build()
