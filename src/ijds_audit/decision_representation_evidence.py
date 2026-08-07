"""Fail-closed paper loader for the three decision-representation audits.

The module verifies three immutable Git-native lineages before exposing any
paper-facing result:

* the outcome-blind complete-hull score-equivalence audit (``P -> A``); and
* the set-native binary robust-counterpart audit (``P1 -> A1 -> P2 -> B1``); and
* the outcome-free dual-coefficient logical-certificate audit (``P -> A``).

The loader intentionally keeps the large funded-allocation table out of its
returned objects.  It reads that table once to reconcile every Phase-A solve
record, then retains only the compact result frames needed by publication code.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path, PurePosixPath
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml

from src.ijds_audit.grid_contracts import require_exact_frame, require_exact_grid, require_finite
from src.utils.artifact_descriptor import relative_artifact_descriptor
from src.utils.isolated_experiment import dataframe_schema

_UV_LOCK_SHA256 = "41a982834374d96995457704ff291d2f6dc4a9ae9d9809cd3dc0a21b23b25367"
_TRANSPORT = "git_force_tracked_direct_child_commit"

_SCORE_PROTOCOL_COMMIT = "2066363ab0d09e25dade0f582a0c36c6aa7bee5c"
_SCORE_ARTIFACT_COMMIT = "e31310090179ee96893c92adec3aa0bbc54f5a95"
_SCORE_PROTOCOL_TAG = "protocol/ijds-score-equivalence-complete-hull-2026-07-31-v1"
_SCORE_ARTIFACT_TAG = "artifacts/ijds-score-equivalence-complete-hull-2026-07-31-v1"
_SCORE_RUN_TAG = "ijds-score-equivalence-complete-hull-2026-07-31-v1"
_SCORE_STATUS = "complete_outcome_free_score_equivalence_complete_hull_audit"

_SET_P1_COMMIT = _SCORE_PROTOCOL_COMMIT
_SET_A1_COMMIT = "3ef847491e1ecdf55315774ddb295a634e441a54"
_SET_P2_COMMIT = "e3d91660f5c337b3a45713b02ad2ca6ec303b31e"
_SET_B1_COMMIT = "b13718008cd23b444d1165d14f0fb78101d9f017"
_SET_P1_TAG = "protocol/ijds-set-native-binary-robust-counterpart-2026-07-31-v1"
_SET_A1_TAG = "artifacts/ijds-set-native-binary-robust-counterpart-2026-07-31-v1-phase-a"
_SET_P2_TAG = "protocol/ijds-set-native-binary-robust-counterpart-2026-07-31-v1-phase-b"
_SET_B1_TAG = "artifacts/ijds-set-native-binary-robust-counterpart-2026-07-31-v1-phase-b"
_SET_PHASE_A_RUN_TAG = "ijds-set-native-binary-robust-counterpart-2026-07-31-v1"
_SET_PHASE_B_RUN_TAG = "ijds-set-native-binary-robust-counterpart-2026-07-31-v1-phase-b"
_SET_PHASE_A_STATUS = "outcome_free_set_native_binary_robust_counterpart_complete"
_SET_PHASE_B_STATUS = "set_native_binary_robust_counterpart_evaluation_complete"

_DUAL_PROTOCOL_COMMIT = "8d0f912023ce61765e15d2370680eb09cfb3a6af"
_DUAL_ARTIFACT_COMMIT = "79c378366d394e4835183ed19f332f0cf0e28f77"
_DUAL_PROTOCOL_TAG = "protocol/ijds-dual-coefficient-binary-set-native-2026-08-01-v1"
_DUAL_ARTIFACT_TAG = "artifacts/ijds-dual-coefficient-binary-set-native-2026-08-01-v1"
_DUAL_RUN_TAG = "ijds-dual-coefficient-binary-set-native-2026-08-01-v1"
_DUAL_STATUS = "outcome_free_dual_coefficient_binary_set_native_certificates_complete"
_DUAL_PAPER_ROLE = (
    "complete_outcome_free_dual_coefficient_binary_set_native_menu_certificate_census"
)

_WINDOWS = (
    "w01_2012m01_m06",
    "w02_2012m02_m07",
    "w03_2012m03_m08",
    "w04_2012m04_m09",
    "w05_2012m05_m10",
    "w06_2012m06_m11",
    "w07_2012m07_m12",
    "w08_2012m08_2013m01",
)
_ROLES = ("policy_development", "primary_oot")
_THETA_GAMMA = (0.0, 0.25, 0.5, 0.75, 1.0)
_RULERS = ("objective_matched", "normalized_score")
_COORDINATES = (0.25, 0.5, 0.75)
_CALIBRATORS = ("platt", "isotonic", "beta", "venn_abers")

_SCORE_DATA_PREFIX = (
    "data/processed/experiments/ijds_audit/ijds-score-equivalence-complete-hull-2026-07-31-v1/"
)
_SCORE_MODEL_PREFIX = (
    "models/experiments/ijds_audit/ijds-score-equivalence-complete-hull-2026-07-31-v1/"
)
_SCORE_ARTIFACT_PATHS = (
    f"{_SCORE_DATA_PREFIX}calibrator_score_equivalence.parquet",
    f"{_SCORE_DATA_PREFIX}complete_hull_certificates.parquet",
    f"{_SCORE_DATA_PREFIX}runtime_controls.parquet",
    f"{_SCORE_DATA_PREFIX}v1d_embedding_score_equivalence.parquet",
    f"{_SCORE_MODEL_PREFIX}execution_receipt.json",
    f"{_SCORE_MODEL_PREFIX}score_equivalence_summary.json",
)

_SET_PHASE_A_DATA_PREFIX = (
    "data/processed/experiments/ijds_audit/"
    "ijds-set-native-binary-robust-counterpart-2026-07-31-v1/frontier/"
)
_SET_PHASE_A_MODEL_PREFIX = (
    "models/experiments/ijds_audit/ijds-set-native-binary-robust-counterpart-2026-07-31-v1/"
)
_SET_PHASE_A_PATHS = (
    f"{_SET_PHASE_A_DATA_PREFIX}frontier_funded_allocations.parquet",
    f"{_SET_PHASE_A_DATA_PREFIX}frontier_solve_records.parquet",
    f"{_SET_PHASE_A_DATA_PREFIX}set_taxonomy_diagnostics.parquet",
    f"{_SET_PHASE_A_DATA_PREFIX}solver_audit.parquet",
    f"{_SET_PHASE_A_MODEL_PREFIX}outcome_free_execution_receipt.json",
    f"{_SET_PHASE_A_MODEL_PREFIX}outcome_free_summary.json",
    f"{_SET_PHASE_A_MODEL_PREFIX}protocol_freeze.json",
    f"{_SET_PHASE_A_MODEL_PREFIX}verified_phase_a_manifest.json",
)
_SET_P2_PATHS = (
    "configs/experiments/ijds_set_native_binary_robust_counterpart_2026-07-31_v1_phase_b.yaml",
)
_SET_PHASE_B_DATA_PREFIX = (
    "data/processed/experiments/ijds_audit/"
    "ijds-set-native-binary-robust-counterpart-2026-07-31-v1-phase-b/evaluation/"
)
_SET_PHASE_B_MODEL_PREFIX = (
    "models/experiments/ijds_audit/ijds-set-native-binary-robust-counterpart-2026-07-31-v1-phase-b/"
)
_SET_PHASE_B_PATHS = (
    f"{_SET_PHASE_B_DATA_PREFIX}evaluated_primary_portfolios.parquet",
    f"{_SET_PHASE_B_DATA_PREFIX}monthly_robust_minus_v1d_contrasts.parquet",
    f"{_SET_PHASE_B_DATA_PREFIX}window_robust_minus_v1d_contrasts.parquet",
    f"{_SET_PHASE_B_MODEL_PREFIX}evaluation_execution_receipt.json",
    f"{_SET_PHASE_B_MODEL_PREFIX}evaluation_summary.json",
    f"{_SET_PHASE_B_MODEL_PREFIX}verified_evaluation_manifest.json",
)

_DUAL_DATA_PREFIX = (
    "data/processed/experiments/ijds_audit/ijds-dual-coefficient-binary-set-native-2026-08-01-v1/"
)
_DUAL_MODEL_PREFIX = (
    "models/experiments/ijds_audit/ijds-dual-coefficient-binary-set-native-2026-08-01-v1/"
)
_DUAL_ARTIFACT_PATHS = (
    f"{_DUAL_DATA_PREFIX}dual_coefficient_binary_set_native_menu_certificates.parquet",
    f"{_DUAL_MODEL_PREFIX}outcome_free_execution_receipt.json",
    f"{_DUAL_MODEL_PREFIX}outcome_free_summary.json",
    f"{_DUAL_MODEL_PREFIX}protocol_freeze.json",
    f"{_DUAL_MODEL_PREFIX}verified_outcome_free_manifest.json",
)
_DUAL_IMPLEMENTATION_PATHS = (
    "configs/experiments/ijds_dual_coefficient_binary_set_native_2026-08-01_v1.yaml",
    "docs/research/ijds_dual_coefficient_binary_set_native_v1_protocol_2026-08-01.md",
    "scripts/experiments/run_ijds_dual_coefficient_binary_set_native_v1.py",
    "src/ijds_challengers/dual_coefficient_binary_set_native.py",
    "tests/test_ijds_dual_coefficient_binary_set_native_v1.py",
    "src/utils/isolated_experiment.py",
    "src/utils/pipeline_runtime.py",
    "pyproject.toml",
    "uv.lock",
)

_REGISTERED_PATHS = {
    "score_equivalence_config": (
        "configs/experiments/ijds_score_equivalence_complete_hull_2026-07-31_v1.yaml"
    ),
    "score_equivalence_protocol": (
        "docs/research/ijds_score_equivalence_complete_hull_v1_protocol_2026-07-31.md"
    ),
    "score_equivalence_runner": (
        "scripts/experiments/run_ijds_score_equivalence_complete_hull_v1.py"
    ),
    "score_equivalence_implementation": "src/ijds_audit/score_equivalence_complete_hull.py",
    "score_equivalence_hulls": f"{_SCORE_DATA_PREFIX}complete_hull_certificates.parquet",
    "score_equivalence_v1d": f"{_SCORE_DATA_PREFIX}v1d_embedding_score_equivalence.parquet",
    "score_equivalence_calibrators": (f"{_SCORE_DATA_PREFIX}calibrator_score_equivalence.parquet"),
    "score_equivalence_controls": f"{_SCORE_DATA_PREFIX}runtime_controls.parquet",
    "score_equivalence_summary": f"{_SCORE_MODEL_PREFIX}score_equivalence_summary.json",
    "score_equivalence_receipt": f"{_SCORE_MODEL_PREFIX}execution_receipt.json",
    "set_native_phase_a_config": (
        "configs/experiments/ijds_set_native_binary_robust_counterpart_2026-07-31_v1.yaml"
    ),
    "set_native_phase_b_config": _SET_P2_PATHS[0],
    "set_native_phase_b_blocked_template": (
        "configs/experiments/"
        "ijds_set_native_binary_robust_counterpart_2026-07-31_v1_phase_b_blocked.yaml"
    ),
    "set_native_protocol": (
        "docs/research/ijds_set_native_binary_robust_counterpart_v1_protocol_2026-07-31.md"
    ),
    "set_native_runner": (
        "scripts/experiments/run_ijds_set_native_binary_robust_counterpart_v1.py"
    ),
    "set_native_implementation": "src/ijds_challengers/set_native_binary_robust.py",
    "set_native_phase_a_solve_records": f"{_SET_PHASE_A_DATA_PREFIX}frontier_solve_records.parquet",
    "set_native_phase_a_allocations": (
        f"{_SET_PHASE_A_DATA_PREFIX}frontier_funded_allocations.parquet"
    ),
    "set_native_phase_a_taxonomy": (f"{_SET_PHASE_A_DATA_PREFIX}set_taxonomy_diagnostics.parquet"),
    "set_native_phase_a_solver_audit": f"{_SET_PHASE_A_DATA_PREFIX}solver_audit.parquet",
    "set_native_phase_a_freeze": f"{_SET_PHASE_A_MODEL_PREFIX}protocol_freeze.json",
    "set_native_phase_a_summary": f"{_SET_PHASE_A_MODEL_PREFIX}outcome_free_summary.json",
    "set_native_phase_a_receipt": (
        f"{_SET_PHASE_A_MODEL_PREFIX}outcome_free_execution_receipt.json"
    ),
    "set_native_phase_a_manifest": (f"{_SET_PHASE_A_MODEL_PREFIX}verified_phase_a_manifest.json"),
    "set_native_evaluated_portfolios": (
        f"{_SET_PHASE_B_DATA_PREFIX}evaluated_primary_portfolios.parquet"
    ),
    "set_native_monthly_contrasts": (
        f"{_SET_PHASE_B_DATA_PREFIX}monthly_robust_minus_v1d_contrasts.parquet"
    ),
    "set_native_window_contrasts": (
        f"{_SET_PHASE_B_DATA_PREFIX}window_robust_minus_v1d_contrasts.parquet"
    ),
    "set_native_evaluation_summary": f"{_SET_PHASE_B_MODEL_PREFIX}evaluation_summary.json",
    "set_native_evaluation_receipt": (
        f"{_SET_PHASE_B_MODEL_PREFIX}evaluation_execution_receipt.json"
    ),
    "set_native_evaluation_manifest": (
        f"{_SET_PHASE_B_MODEL_PREFIX}verified_evaluation_manifest.json"
    ),
    "dual_coefficient_config": (
        "configs/experiments/ijds_dual_coefficient_binary_set_native_2026-08-01_v1.yaml"
    ),
    "dual_coefficient_protocol": (
        "docs/research/ijds_dual_coefficient_binary_set_native_v1_protocol_2026-08-01.md"
    ),
    "dual_coefficient_runner": (
        "scripts/experiments/run_ijds_dual_coefficient_binary_set_native_v1.py"
    ),
    "dual_coefficient_implementation": (
        "src/ijds_challengers/dual_coefficient_binary_set_native.py"
    ),
    "dual_coefficient_certificates": _DUAL_ARTIFACT_PATHS[0],
    "dual_coefficient_receipt": _DUAL_ARTIFACT_PATHS[1],
    "dual_coefficient_summary": _DUAL_ARTIFACT_PATHS[2],
    "dual_coefficient_freeze": _DUAL_ARTIFACT_PATHS[3],
    "dual_coefficient_manifest": _DUAL_ARTIFACT_PATHS[4],
}

_HULL_COLUMNS = (
    "role",
    "period",
    "rows",
    "full_budget_hull_certified",
    "ambient_dimension",
    "affine_dimension",
    "purpose_count",
    "budget",
    "purpose_cap",
    "total_loan_capacity",
    "total_strict_group_capacity",
    "witness_budget_residual",
    "minimum_witness_exposure",
    "minimum_loan_upper_slack",
    "minimum_purpose_cap_slack",
)
_SCORE_CERTIFICATE_COLUMNS = (
    "equivalent_on_complete_budget_hull",
    "estimated_scale",
    "positive_scale",
    "estimated_unit_intercept",
    "portfolio_score_offset",
    "ambient_dimension",
    "affine_dimension",
    "source_centered_norm",
    "target_centered_norm",
    "relation_residual_norm",
    "maximum_coordinate_relation_error",
    "relation_tolerance",
)
_V1D_COLUMNS = (
    "family",
    "window_id",
    "role",
    "period",
    "rows",
    "theta",
    "theta_reference",
    "gamma",
    "theta_zero_self_control",
    "gamma_zero_identity_control",
    *_SCORE_CERTIFICATE_COLUMNS,
)
_CALIBRATOR_COLUMNS = (
    "family",
    "window_id",
    "role",
    "period",
    "rows",
    "method_a",
    "method_b",
    "gamma",
    "gamma_zero_probability_reconciliation",
    *_SCORE_CERTIFICATE_COLUMNS,
)
_CONTROL_COLUMNS = (
    "role",
    "period",
    "rows",
    "control_type",
    "expected_equivalent",
    "observed_equivalent",
    "control_passed",
    *_SCORE_CERTIFICATE_COLUMNS,
)

_DUAL_COLUMNS = (
    "window_id",
    "role",
    "period",
    "predecessor_rows",
    "minimum_score",
    "minimum_n_candidates",
    "maximum_n_candidates",
    "maximum_abs_budget_residual",
    "minimum_total_allocated",
    "maximum_total_allocated",
    "minimum_score_portfolio_objective",
    "n_candidates",
    "n_empty",
    "n_singleton_zero",
    "n_singleton_one",
    "n_two_label",
    "n_risk_zero",
    "n_risk_one",
    "empty_set_score",
    "budget_dollars",
    "purpose_cap",
    "lgd",
    "contractual_rate_lower",
    "contractual_rate_upper",
    "condition_budget_equality",
    "condition_no_cash",
    "condition_disjoint_purpose_partition",
    "condition_upper_only_purpose_caps",
    "condition_nonnegative_contractual_rates",
    "condition_positive_lgd",
    "condition_singleton_zero_capacity_at_least_budget",
    "condition_exact_binary_set_labels",
    "capacity_lower_bound_dollars",
    "capacity_certificate",
    "payoff_definition",
    "all_maximin_optimizers_singleton_zero",
    "continuous_cap_frontier_collapses",
    "cap_domain_lower",
    "cap_domain_upper",
    "new_optimization_executed",
    "raw_archive_read",
    "optimizer_unique_certified",
    "policy_selected",
    "validity_claim_established",
)
_DUAL_CONDITION_COLUMNS = (
    "condition_budget_equality",
    "condition_no_cash",
    "condition_disjoint_purpose_partition",
    "condition_upper_only_purpose_caps",
    "condition_nonnegative_contractual_rates",
    "condition_positive_lgd",
    "condition_singleton_zero_capacity_at_least_budget",
    "condition_exact_binary_set_labels",
)
_DUAL_CLAIM_BOUNDARY_KEYS = (
    "no_raw_read",
    "no_new_optimization",
    "no_phase_b",
    "no_1248_ruler_coordinate_grid",
    "no_selected_cap_window_or_policy",
    "no_policy_winner",
    "no_conformal_validity_repair",
    "no_joint_cartesian_product_coverage",
    "no_probabilistic_robustness_guarantee",
    "no_funded_or_selected_set_validity",
    "no_causal_or_prospective_claim",
    "no_optimizer_uniqueness_claim",
)

_EVALUATED_COLUMNS = (
    "candidate_id",
    "paired_policy_id",
    "frontier_ruler",
    "frontier_coordinate",
    "frontier_cap",
    "objective_target",
    "risk_tolerance",
    "policy_mode",
    "robust_guardrail",
    "set_native_score",
    "empty_set_convention",
    "solver_status",
    "solver_backend_actual",
    "expected_objective",
    "n_candidates",
    "n_positive_exposure",
    "total_allocated",
    "budget_residual",
    "cash_variable_present",
    "weighted_pd_point",
    "weighted_pd_effective",
    "weighted_set_risk",
    "weighted_conformal_upper",
    "minimum_score",
    "score_at_objective",
    "score_range",
    "minimum_score_portfolio_objective",
    "unconstrained_objective",
    "objective_retention",
    "constraint_slack",
    "highs_simplex_iterations",
    "window_id",
    "role",
    "period",
    "policy_label",
    "comparator_rule",
    "n_unresolved_candidates",
    "n_unresolved_positive_exposure",
    "unresolved_exposure_share",
    "realized_payoff_lower",
    "realized_payoff_upper",
    "realized_payoff_exact",
    "weighted_default_lower",
    "weighted_default_upper",
    "weighted_miscoverage_lower",
    "weighted_miscoverage_upper",
    "full_budget",
)
_CONTRAST_COMMON_COLUMNS = (
    "scope",
    "window_id",
    "frontier_ruler",
    "frontier_coordinate",
    "theta",
    "gamma",
    "robust_policy",
    "embedding_policy",
    "contrast",
    "role",
    "policy_a",
    "policy_b",
    "policy_a_capital",
    "policy_b_capital",
    "policy_a_normalization_capital",
    "policy_b_normalization_capital",
    "funded_union_loans",
    "unresolved_union_loans",
    "expected_objective_difference",
    "realized_payoff_difference_lower",
    "realized_payoff_difference_upper",
    "realized_payoff_rate_difference_lower",
    "realized_payoff_rate_difference_upper",
    "weighted_default_difference_lower",
    "weighted_default_difference_upper",
    "weighted_miscoverage_difference_lower",
    "weighted_miscoverage_difference_upper",
    "realized_payoff_identification_width",
    "realized_payoff_rate_identification_width",
    "weighted_default_identification_width",
    "weighted_miscoverage_identification_width",
    "payoff_direction_sign_robust",
    "default_direction_sign_robust",
    "miscoverage_direction_sign_robust",
    "causal_interpretation",
)
_MONTHLY_COLUMNS = (
    "scope",
    "window_id",
    "period",
    *_CONTRAST_COMMON_COLUMNS[2:],
)
_POOLED_COLUMNS = _CONTRAST_COMMON_COLUMNS

_METRICS = {
    "standardized_payoff": (
        "realized_payoff_rate_difference_lower",
        "realized_payoff_rate_difference_upper",
        "payoff_direction_sign_robust",
    ),
    "funded_default": (
        "weighted_default_difference_lower",
        "weighted_default_difference_upper",
        "default_direction_sign_robust",
    ),
    "funded_binary_miscoverage": (
        "weighted_miscoverage_difference_lower",
        "weighted_miscoverage_difference_upper",
        "miscoverage_direction_sign_robust",
    ),
}
_EXPECTED_SIGN_TOTALS = {
    "monthly": {
        "standardized_payoff": (5840, 9853, 2307),
        "funded_default": (13992, 2462, 1546),
        "funded_binary_miscoverage": (11947, 4355, 1698),
    },
    "pooled": {
        "standardized_payoff": (15, 1065, 120),
        "funded_default": (1196, 0, 4),
        "funded_binary_miscoverage": (1009, 120, 71),
    },
}


@dataclass(frozen=True)
class ScoreEquivalenceEvidence:
    """Verified complete-hull score-equivalence evidence."""

    summary: Mapping[str, Any]
    receipt: Mapping[str, Any]
    hulls: pd.DataFrame
    v1d: pd.DataFrame
    calibrators: pd.DataFrame
    controls: pd.DataFrame
    findings: Mapping[str, Any]


@dataclass(frozen=True)
class SetNativeEvidence:
    """Verified set-native Phase-A and Phase-B evidence."""

    phase_a_freeze: Mapping[str, Any]
    phase_a_summary: Mapping[str, Any]
    phase_a_receipt: Mapping[str, Any]
    phase_a_manifest: Mapping[str, Any]
    evaluation_summary: Mapping[str, Any]
    evaluation_receipt: Mapping[str, Any]
    evaluation_manifest: Mapping[str, Any]
    solve_records: pd.DataFrame
    taxonomy: pd.DataFrame
    solver_audit: pd.DataFrame
    evaluated_portfolios: pd.DataFrame
    monthly_contrasts: pd.DataFrame
    window_contrasts: pd.DataFrame
    findings: Mapping[str, Any]


@dataclass(frozen=True)
class DualCoefficientEvidence:
    """Verified dual-coefficient logical certificates and claim boundary."""

    freeze: Mapping[str, Any]
    summary: Mapping[str, Any]
    receipt: Mapping[str, Any]
    manifest: Mapping[str, Any]
    certificates: pd.DataFrame
    findings: Mapping[str, Any]


@dataclass(frozen=True)
class DecisionRepresentationEvidence:
    """Compact verified evidence for all three decision-representation lineages."""

    score_equivalence: ScoreEquivalenceEvidence
    set_native: SetNativeEvidence
    dual_coefficient: DualCoefficientEvidence


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{label} must be a JSON object.")
    return payload


def _load_yaml_object(path: Path, *, label: str) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{label} must be a YAML mapping.")
    return cast(dict[str, Any], payload)


def _mapping(payload: Mapping[str, Any], key: str, *, label: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise TypeError(f"{label}.{key} must be a mapping.")
    return cast(Mapping[str, Any], value)


def _require_registered_paths(registered: Mapping[str, Path], *, repo_root: Path) -> None:
    missing = sorted(set(_REGISTERED_PATHS).difference(registered))
    if missing:
        raise KeyError(f"Decision-representation registry keys are missing: {missing}.")
    root = repo_root.resolve()
    for name, relative in _REGISTERED_PATHS.items():
        actual = registered[name].resolve()
        expected = (root / relative).resolve()
        try:
            actual.relative_to(root)
        except ValueError as error:
            raise RuntimeError(f"Registered source {name!r} escapes the repository.") from error
        if actual != expected:
            raise RuntimeError(f"Registered source {name!r} changed path.")


def _git_text(repo_root: Path, arguments: Sequence[str], *, label: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git verification failed for {label}: {result.stderr.strip()}")
    return result.stdout.strip()


def _require_annotated_tag(
    tag: str,
    commit: str,
    *,
    repo_root: Path,
    label: str,
) -> None:
    kind = _git_text(
        repo_root,
        ("cat-file", "-t", f"refs/tags/{tag}"),
        label=f"{label} tag object",
    )
    if kind != "tag":
        raise RuntimeError(f"{label} tag {tag!r} is missing or lightweight.")
    resolved = _git_text(
        repo_root,
        ("rev-parse", "--verify", "--end-of-options", f"refs/tags/{tag}^{{commit}}"),
        label=f"{label} tag target",
    )
    if resolved != commit:
        raise RuntimeError(f"{label} tag {tag!r} no longer resolves to {commit}.")


def _require_git_stage(
    *,
    tag: str,
    commit: str,
    parent: str,
    paths: Sequence[str],
    repo_root: Path,
    label: str,
) -> None:
    _require_annotated_tag(tag, commit, repo_root=repo_root, label=label)
    ancestry = _git_text(
        repo_root,
        ("rev-list", "--parents", "-n", "1", commit),
        label=f"{label} ancestry",
    ).split()
    if ancestry != [commit, parent]:
        raise RuntimeError(f"{label} is not the required single direct child of {parent}.")
    changed = _git_text(
        repo_root,
        ("diff-tree", "--no-commit-id", "--name-only", "--no-renames", "-r", commit),
        label=f"{label} exact diff",
    ).splitlines()
    if changed != list(paths):
        raise RuntimeError(f"{label} changed {changed}, not the exact locked path list.")
    for path in paths:
        _git_text(
            repo_root,
            ("cat-file", "-e", f"{commit}:{path}"),
            label=f"{label} blob {path}",
        )


def _require_exact_identity(
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    label: str,
) -> None:
    changed = {key: actual.get(key) for key, value in expected.items() if actual.get(key) != value}
    if changed:
        raise RuntimeError(f"{label} registry identity changed: {changed}.")


def _require_lineages(
    identities: Mapping[str, Any],
    *,
    repo_root: Path,
) -> None:
    if set(identities) != {
        "score_equivalence_complete_hull",
        "set_native_binary_robust_counterpart",
        "dual_coefficient_binary_set_native",
    }:
        raise RuntimeError(
            "Decision-representation identities must contain exactly "
            "score_equivalence_complete_hull, set_native_binary_robust_counterpart, "
            "and dual_coefficient_binary_set_native."
        )
    score = identities.get("score_equivalence_complete_hull")
    set_native = identities.get("set_native_binary_robust_counterpart")
    dual = identities.get("dual_coefficient_binary_set_native")
    if (
        not isinstance(score, Mapping)
        or not isinstance(set_native, Mapping)
        or not isinstance(dual, Mapping)
    ):
        raise TypeError("Decision-representation lineage identities must be mappings.")
    if set(set_native) != {"outcome_free", "evaluation"}:
        raise RuntimeError("Set-native identity must contain exactly outcome_free and evaluation.")
    phase_a = set_native.get("outcome_free")
    evaluation = set_native.get("evaluation")
    if not isinstance(phase_a, Mapping) or not isinstance(evaluation, Mapping):
        raise TypeError("Set-native phase identities must be mappings.")

    _require_exact_identity(
        score,
        {
            "run_tag": _SCORE_RUN_TAG,
            "protocol_tag": _SCORE_PROTOCOL_TAG,
            "protocol_commit": _SCORE_PROTOCOL_COMMIT,
            "scientific_uv_lock_sha256": _UV_LOCK_SHA256,
            "paper_role": (
                "complete_outcome_free_complete_candidate_hull_score_equivalence_census"
            ),
            "dvc_tracked": False,
            "artifact_tag": _SCORE_ARTIFACT_TAG,
            "artifact_commit": _SCORE_ARTIFACT_COMMIT,
            "artifact_parent_commit": _SCORE_PROTOCOL_COMMIT,
            "artifact_transport": _TRANSPORT,
            "artifact_paths": list(_SCORE_ARTIFACT_PATHS),
        },
        label="score-equivalence lineage",
    )
    _require_exact_identity(
        phase_a,
        {
            "run_tag": _SET_PHASE_A_RUN_TAG,
            "protocol_tag": _SET_P1_TAG,
            "protocol_commit": _SET_P1_COMMIT,
            "scientific_uv_lock_sha256": _UV_LOCK_SHA256,
            "paper_role": "outcome_free_complete_set_native_frontier_and_solver_audit",
            "dvc_tracked": False,
            "artifact_tag": _SET_A1_TAG,
            "artifact_commit": _SET_A1_COMMIT,
            "artifact_parent_commit": _SET_P1_COMMIT,
            "artifact_transport": _TRANSPORT,
            "artifact_paths": list(_SET_PHASE_A_PATHS),
        },
        label="set-native Phase-A lineage",
    )
    _require_exact_identity(
        evaluation,
        {
            "run_tag": _SET_PHASE_B_RUN_TAG,
            "protocol_tag": _SET_P2_TAG,
            "protocol_commit": _SET_P2_COMMIT,
            "scientific_uv_lock_sha256": _UV_LOCK_SHA256,
            "paper_role": "complete_retrospective_set_native_robust_minus_embedding_census",
            "dvc_tracked": False,
            "artifact_tag": _SET_B1_TAG,
            "artifact_commit": _SET_B1_COMMIT,
            "artifact_parent_commit": _SET_P2_COMMIT,
            "artifact_transport": _TRANSPORT,
            "artifact_paths": list(_SET_PHASE_B_PATHS),
        },
        label="set-native Phase-B lineage",
    )
    _require_exact_identity(
        dual,
        {
            "run_tag": _DUAL_RUN_TAG,
            "protocol_tag": _DUAL_PROTOCOL_TAG,
            "protocol_commit": _DUAL_PROTOCOL_COMMIT,
            "scientific_uv_lock_sha256": _UV_LOCK_SHA256,
            "paper_role": _DUAL_PAPER_ROLE,
            "dvc_tracked": False,
            "artifact_tag": _DUAL_ARTIFACT_TAG,
            "artifact_commit": _DUAL_ARTIFACT_COMMIT,
            "artifact_parent_commit": _DUAL_PROTOCOL_COMMIT,
            "artifact_transport": _TRANSPORT,
            "artifact_paths": list(_DUAL_ARTIFACT_PATHS),
        },
        label="dual-coefficient lineage",
    )

    _require_annotated_tag(
        _SCORE_PROTOCOL_TAG,
        _SCORE_PROTOCOL_COMMIT,
        repo_root=repo_root,
        label="score-equivalence protocol",
    )
    _require_git_stage(
        tag=_SCORE_ARTIFACT_TAG,
        commit=_SCORE_ARTIFACT_COMMIT,
        parent=_SCORE_PROTOCOL_COMMIT,
        paths=_SCORE_ARTIFACT_PATHS,
        repo_root=repo_root,
        label="score-equivalence artifact",
    )
    _require_annotated_tag(
        _SET_P1_TAG,
        _SET_P1_COMMIT,
        repo_root=repo_root,
        label="set-native P1 protocol",
    )
    _require_git_stage(
        tag=_SET_A1_TAG,
        commit=_SET_A1_COMMIT,
        parent=_SET_P1_COMMIT,
        paths=_SET_PHASE_A_PATHS,
        repo_root=repo_root,
        label="set-native A1 artifact",
    )
    _require_git_stage(
        tag=_SET_P2_TAG,
        commit=_SET_P2_COMMIT,
        parent=_SET_A1_COMMIT,
        paths=_SET_P2_PATHS,
        repo_root=repo_root,
        label="set-native P2 protocol",
    )
    _require_git_stage(
        tag=_SET_B1_TAG,
        commit=_SET_B1_COMMIT,
        parent=_SET_P2_COMMIT,
        paths=_SET_PHASE_B_PATHS,
        repo_root=repo_root,
        label="set-native B1 artifact",
    )
    _require_annotated_tag(
        _DUAL_PROTOCOL_TAG,
        _DUAL_PROTOCOL_COMMIT,
        repo_root=repo_root,
        label="dual-coefficient protocol",
    )
    _require_git_stage(
        tag=_DUAL_ARTIFACT_TAG,
        commit=_DUAL_ARTIFACT_COMMIT,
        parent=_DUAL_PROTOCOL_COMMIT,
        paths=_DUAL_ARTIFACT_PATHS,
        repo_root=repo_root,
        label="dual-coefficient artifact",
    )


def _exact_descriptor(raw: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != {"path", "bytes", "sha256"}:
        raise TypeError(f"{label} must be an exact path/bytes/sha256 descriptor.")
    relative = raw.get("path")
    size = raw.get("bytes")
    digest = raw.get("sha256")
    if not isinstance(relative, str) or not isinstance(size, int) or not isinstance(digest, str):
        raise TypeError(f"{label} descriptor fields have invalid types.")
    normalized = PurePosixPath(relative)
    if normalized.is_absolute() or ".." in normalized.parts or normalized.as_posix() != relative:
        raise ValueError(f"{label}.path is not a safe normalized repository path.")
    if size < 0 or len(digest) != 64:
        raise ValueError(f"{label} descriptor size or SHA-256 is invalid.")
    return {"path": relative, "bytes": size, "sha256": digest}


def _descriptor_path(
    raw: Any,
    *,
    repo_root: Path,
    label: str,
    cache: dict[tuple[str, int, str], Path],
) -> Path:
    descriptor = _exact_descriptor(raw, label=label)
    key = (str(descriptor["path"]), int(descriptor["bytes"]), str(descriptor["sha256"]))
    cached = cache.get(key)
    if cached is not None:
        return cached
    path = (repo_root / str(descriptor["path"])).resolve()
    try:
        path.relative_to(repo_root.resolve())
    except ValueError as error:
        raise ValueError(f"{label}.path escapes the repository.") from error
    if relative_artifact_descriptor(path, repo_root=repo_root) != descriptor:
        raise RuntimeError(f"{label} no longer matches its path/bytes/SHA-256 descriptor.")
    cache[key] = path
    return path


def _require_git_blob_descriptor(
    *,
    commit: str,
    descriptor: Mapping[str, Any],
    repo_root: Path,
    label: str,
) -> None:
    relative = descriptor.get("path")
    if not isinstance(relative, str):
        raise TypeError(f"{label} descriptor path must be text.")
    result = subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relative}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{label} is absent from pinned commit {commit}.")
    if len(result.stdout) != descriptor.get("bytes") or hashlib.sha256(
        result.stdout
    ).hexdigest() != descriptor.get("sha256"):
        raise RuntimeError(f"{label} descriptor differs from its pinned Git blob.")


def _require_implementation_provenance(
    payload: Mapping[str, Any],
    *,
    commit: str,
    repo_root: Path,
    label: str,
) -> None:
    provenance = _mapping(payload, "implementation_provenance", label=label)
    if provenance.get("hash_algorithm") != "sha256":
        raise RuntimeError(f"{label} implementation hash algorithm changed.")
    source_files = provenance.get("source_files")
    if not isinstance(source_files, Mapping) or not source_files:
        raise TypeError(f"{label} implementation inventory is absent.")
    for relative, raw in source_files.items():
        if not isinstance(relative, str):
            raise TypeError(f"{label} implementation key must be text.")
        descriptor = _exact_descriptor(raw, label=f"{label} implementation {relative}")
        if descriptor["path"] != relative:
            raise RuntimeError(f"{label} implementation key and path disagree.")
        _require_git_blob_descriptor(
            commit=commit,
            descriptor=descriptor,
            repo_root=repo_root,
            label=f"{label} implementation {relative}",
        )


def _require_protocol_identity(
    payload: Mapping[str, Any],
    *,
    schema: str,
    status: str,
    run_tag: str,
    protocol_tag: str,
    protocol_commit: str,
    label: str,
) -> None:
    if (
        payload.get("schema_version") != schema
        or payload.get("status") != status
        or payload.get("run_tag") != run_tag
    ):
        raise RuntimeError(f"{label} schema, status, or run identity changed.")
    protocol = _mapping(payload, "protocol", label=label)
    if protocol.get("tag") != protocol_tag or protocol.get("commit") != protocol_commit:
        raise RuntimeError(f"{label} protocol identity changed.")


def _require_no_side_effects(payload: Mapping[str, Any], *, label: str) -> None:
    if payload.get("protected_stages_run") != []:
        raise RuntimeError(f"{label} reports a protected stage execution.")
    if payload.get("protected_artifacts_written") != []:
        raise RuntimeError(f"{label} reports a protected artifact write.")


def _require_exact_columns(frame: pd.DataFrame, columns: Sequence[str], *, label: str) -> None:
    if tuple(frame.columns) != tuple(columns):
        raise RuntimeError(f"{label} columns or column order changed.")


def _require_dtype_groups(
    frame: pd.DataFrame,
    *,
    strings: Sequence[str] = (),
    floats: Sequence[str] = (),
    integers: Sequence[str] = (),
    booleans: Sequence[str] = (),
    label: str,
) -> None:
    expected = {
        **dict.fromkeys(strings, "str"),
        **dict.fromkeys(floats, "float64"),
        **dict.fromkeys(integers, "int64"),
        **dict.fromkeys(booleans, "bool"),
    }
    changed = {
        column: str(frame[column].dtype)
        for column, dtype in expected.items()
        if str(frame[column].dtype) != dtype
    }
    if changed:
        raise RuntimeError(f"{label} dtypes changed: {changed}.")


def _score_menu_domains(hulls: pd.DataFrame) -> dict[str, tuple[str, ...]]:
    development = tuple(
        sorted(hulls.loc[hulls["role"].eq("policy_development"), "period"].astype(str))
    )
    primary = tuple(sorted(hulls.loc[hulls["role"].eq("primary_oot"), "period"].astype(str)))
    if len(development) != 11 or len(primary) != 15:
        raise RuntimeError("Complete-hull role/month census is not 11/15.")
    return {"policy_development": development, "primary_oot": primary}


def _validate_score_frames(
    hulls: pd.DataFrame,
    v1d: pd.DataFrame,
    calibrators: pd.DataFrame,
    controls: pd.DataFrame,
    *,
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    _require_exact_columns(hulls, _HULL_COLUMNS, label="complete-hull certificates")
    _require_exact_columns(v1d, _V1D_COLUMNS, label="V1d score equivalence")
    _require_exact_columns(calibrators, _CALIBRATOR_COLUMNS, label="calibrator equivalence")
    _require_exact_columns(controls, _CONTROL_COLUMNS, label="score runtime controls")
    _require_dtype_groups(
        hulls,
        strings=("role", "period"),
        integers=("rows", "ambient_dimension", "affine_dimension", "purpose_count"),
        booleans=("full_budget_hull_certified",),
        floats=_HULL_COLUMNS[7:],
        label="complete-hull certificates",
    )
    for frame, label in (
        (v1d, "V1d score equivalence"),
        (calibrators, "calibrator equivalence"),
        (controls, "score runtime controls"),
    ):
        numeric = [
            column
            for column in frame.columns
            if pd.api.types.is_numeric_dtype(frame[column].dtype)
            and not pd.api.types.is_bool_dtype(frame[column].dtype)
        ]
        require_finite(frame, numeric, label=label)

    if len(hulls) != 26 or bool(hulls.duplicated(["role", "period"]).any()):
        raise RuntimeError("Complete-hull certificate census is not exactly 26 menus.")
    menus = _score_menu_domains(hulls)
    if (
        set(hulls["role"].astype(str)) != set(_ROLES)
        or not hulls["full_budget_hull_certified"].eq(True).all()
        or not hulls["rows"].eq(hulls["ambient_dimension"]).all()
        or not hulls["affine_dimension"].eq(hulls["ambient_dimension"] - 1).all()
        or not hulls["budget"].eq(1_000_000.0).all()
        or not hulls["purpose_cap"].eq(0.25).all()
        or not hulls["witness_budget_residual"].abs().le(1.0e-6).all()
        or not hulls[
            [
                "minimum_witness_exposure",
                "minimum_loan_upper_slack",
                "minimum_purpose_cap_slack",
            ]
        ]
        .gt(0.0)
        .all(axis=None)
    ):
        raise RuntimeError("Complete-hull certificates no longer establish the locked hull.")

    expected_menu_keys = {(role, period) for role, periods in menus.items() for period in periods}
    expected_v1d = {
        (window, role, period, theta, gamma)
        for window in _WINDOWS
        for role, periods in menus.items()
        for period in periods
        for theta in _THETA_GAMMA
        for gamma in _THETA_GAMMA
    }
    v1d_keys = set(
        v1d[["window_id", "role", "period", "theta", "gamma"]].itertuples(index=False, name=None)
    )
    if len(v1d) != 5200 or v1d_keys != expected_v1d:
        raise RuntimeError("V1d complete-hull grid changed from its 5,200-cell census.")
    theta_zero = v1d["theta"].eq(0.0)
    gamma_zero = v1d["gamma"].eq(0.0)
    identity = theta_zero | gamma_zero
    if (
        not v1d["family"].eq("v1d_set_preserving_embedding").all()
        or not v1d["theta_reference"].eq(0.0).all()
        or not v1d["theta_zero_self_control"].eq(theta_zero).all()
        or not v1d["gamma_zero_identity_control"].eq(gamma_zero).all()
        or not v1d["equivalent_on_complete_budget_hull"].eq(identity).all()
        or not v1d["positive_scale"].eq(True).all()
        or int(identity.sum()) != 1872
        or int((~identity).sum()) != 3328
    ):
        raise RuntimeError("V1d equivalence is no longer exactly the declared identity union.")
    if not (
        v1d.loc[identity, "estimated_scale"].eq(1.0).all()
        and v1d.loc[identity, "estimated_unit_intercept"].eq(0.0).all()
        and v1d.loc[identity, "maximum_coordinate_relation_error"].eq(0.0).all()
    ):
        raise RuntimeError("V1d identity controls are no longer exact identities.")

    expected_pairs = tuple(combinations(_CALIBRATORS, 2))
    expected_calibrator = {
        (window, role, period, method_a, method_b, gamma)
        for window in _WINDOWS
        for role, periods in menus.items()
        for period in periods
        for method_a, method_b in expected_pairs
        for gamma in _THETA_GAMMA
    }
    calibrator_keys = set(
        calibrators[["window_id", "role", "period", "method_a", "method_b", "gamma"]].itertuples(
            index=False, name=None
        )
    )
    if len(calibrators) != 6240 or calibrator_keys != expected_calibrator:
        raise RuntimeError("Closed-calibrator complete-hull grid changed from 6,240 cells.")
    if (
        not calibrators["family"].eq("closed_calibrator_q_gamma").all()
        or not calibrators["gamma_zero_probability_reconciliation"]
        .eq(calibrators["gamma"].eq(0.0))
        .all()
        or calibrators["equivalent_on_complete_budget_hull"].any()
        or not calibrators["positive_scale"].eq(True).all()
    ):
        raise RuntimeError("A calibrator pair gained an unsupported equivalence certificate.")

    expected_controls = {
        (role, period, control)
        for role, period in expected_menu_keys
        for control in ("positive_affine", "negative_nonaffine")
    }
    control_keys = set(
        controls[["role", "period", "control_type"]].itertuples(index=False, name=None)
    )
    positive = controls["control_type"].eq("positive_affine")
    if (
        len(controls) != 52
        or control_keys != expected_controls
        or not controls["control_passed"].eq(True).all()
        or not controls["expected_equivalent"].eq(positive).all()
        or not controls["observed_equivalent"].eq(positive).all()
        or not controls["equivalent_on_complete_budget_hull"].eq(positive).all()
    ):
        raise RuntimeError("Complete-hull positive/negative runtime controls changed.")

    hull_dimensions = hulls.set_index(["role", "period"])[
        ["rows", "ambient_dimension", "affine_dimension"]
    ]
    for frame, label in ((v1d, "V1d"), (calibrators, "calibrator"), (controls, "control")):
        joined = frame.merge(
            hull_dimensions.reset_index(),
            on=["role", "period"],
            how="left",
            validate="many_to_one",
            suffixes=("", "_hull"),
        )
        if not (
            joined["rows"].eq(joined["rows_hull"]).all()
            and joined["ambient_dimension"].eq(joined["ambient_dimension_hull"]).all()
            and joined["affine_dimension"].eq(joined["affine_dimension_hull"]).all()
        ):
            raise RuntimeError(f"{label} dimensions do not reconcile to certified hulls.")

    counts = _mapping(summary, "counts", label="score-equivalence summary")
    expected_counts = {
        "complete_hull_certificates": 26,
        "v1d_embedding_comparisons": 5200,
        "calibrator_comparisons": 6240,
        "runtime_controls": 52,
        "v1d_equivalent_cells": 1872,
        "v1d_nonequivalent_cells": 3328,
        "calibrator_equivalent_cells": 0,
        "calibrator_nonequivalent_cells": 6240,
    }
    if dict(counts) != expected_counts:
        raise RuntimeError("Score-equivalence summary counts changed.")
    gates = _mapping(summary, "gates", label="score-equivalence summary")
    expected_true_gates = {
        "complete_hull_all_26_months",
        "v1d_candidate_identity_exact",
        "v1d_set_preservation_80_rows_exact",
        "calibrator_full_vector_hash_replay_exact",
        "theta_zero_self_controls_pass",
        "gamma_zero_embedding_identity_controls_pass",
        "synthetic_positive_and_negative_controls_pass",
        "complete_grids_and_finite_outputs",
    }
    if any(gates.get(key) is not True for key in expected_true_gates):
        raise RuntimeError("A score-equivalence execution gate is no longer true.")
    if gates.get("outcome_columns_passed") != [] or gates.get("optimization_run") is not False:
        raise RuntimeError("Score-equivalence evidence reports outcomes or optimization.")
    boundary = _mapping(summary, "result_boundary", label="score-equivalence summary")
    if (
        boundary.get("failure_means_global_invariance_not_certified") is not True
        or boundary.get("failure_implies_fixed_cell_allocation_change") is not False
        or boundary.get("passing_requires_translated_caps") is not True
        or boundary.get("calibrator_common_objective_established") is not False
        or boundary.get("calibrator_score_equivalence_certifies_full_optimizer_invariance")
        is not False
        or boundary.get("portfolio_performance_claim") is not False
        or boundary.get("selected_or_funded_set_validity") is not False
    ):
        raise RuntimeError("Score-equivalence interpretation boundary changed.")

    substantive = v1d.loc[~identity]
    return {
        "complete_hulls": 26,
        "v1d_cells": 5200,
        "v1d_identity_equivalent_cells": 1872,
        "v1d_substantive_without_certificate": 3328,
        "calibrator_cells_without_certificate": 6240,
        "smallest_v1d_failing_max_coordinate_error": float(
            substantive["maximum_coordinate_relation_error"].min()
        ),
        "smallest_calibrator_failing_max_coordinate_error": float(
            calibrators["maximum_coordinate_relation_error"].min()
        ),
        "relation_tolerance": float(v1d["relation_tolerance"].max()),
        "outcome_columns_passed": [],
        "optimization_run": False,
    }


def _load_score_equivalence(
    registered: Mapping[str, Path],
    *,
    repo_root: Path,
    cache: dict[tuple[str, int, str], Path],
) -> ScoreEquivalenceEvidence:
    summary = _load_json_object(
        registered["score_equivalence_summary"], label="score-equivalence summary"
    )
    receipt = _load_json_object(
        registered["score_equivalence_receipt"], label="score-equivalence receipt"
    )
    for payload, label in ((summary, "score-equivalence summary"), (receipt, "receipt")):
        if (
            payload.get("schema_version") != "2026-07-31.1"
            or payload.get("status") != _SCORE_STATUS
            or payload.get("run_tag") != _SCORE_RUN_TAG
            or payload.get("protocol_tag") != _SCORE_PROTOCOL_TAG
            or payload.get("protocol_commit") != _SCORE_PROTOCOL_COMMIT
        ):
            raise RuntimeError(f"{label} identity changed.")
        _require_no_side_effects(payload, label=label)
    if (
        summary.get("artifact_status")
        != "pending_single_direct_child_commit_and_annotated_artifact_tag"
        or summary.get("required_artifact_tag") != _SCORE_ARTIFACT_TAG
        or receipt.get("artifact_status")
        != "pending_single_direct_child_commit_and_annotated_artifact_tag"
        or receipt.get("required_artifact_tag") != _SCORE_ARTIFACT_TAG
    ):
        raise RuntimeError("Score-equivalence artifact seal contract changed.")
    environment = _mapping(summary, "environment", label="score-equivalence summary")
    if environment.get("uv_lock_sha256") != _UV_LOCK_SHA256:
        raise RuntimeError("Score-equivalence scientific lock changed.")
    git = _mapping(summary, "git", label="score-equivalence summary")
    if (
        git.get("commit") != _SCORE_PROTOCOL_COMMIT
        or git.get("dirty") is not False
        or git.get("dirty_entries") != 0
        or git.get("dirty_paths") != []
    ):
        raise RuntimeError("Score-equivalence execution was not clean at P.")
    _require_implementation_provenance(
        summary,
        commit=_SCORE_PROTOCOL_COMMIT,
        repo_root=repo_root,
        label="score-equivalence summary",
    )

    artifact_descriptors = _mapping(summary, "artifacts", label="score-equivalence summary")
    descriptor_by_key = {
        "complete_hull_certificates": "score_equivalence_hulls",
        "v1d_embedding_score_equivalence": "score_equivalence_v1d",
        "calibrator_score_equivalence": "score_equivalence_calibrators",
        "runtime_controls": "score_equivalence_controls",
    }
    for artifact_name, registered_name in descriptor_by_key.items():
        descriptor = _exact_descriptor(
            artifact_descriptors.get(artifact_name), label=f"score {artifact_name}"
        )
        path = _descriptor_path(
            descriptor,
            repo_root=repo_root,
            label=f"score {artifact_name}",
            cache=cache,
        )
        if path != registered[registered_name].resolve():
            raise RuntimeError(f"Score artifact {artifact_name} registry path changed.")
        _require_git_blob_descriptor(
            commit=_SCORE_ARTIFACT_COMMIT,
            descriptor=descriptor,
            repo_root=repo_root,
            label=f"score {artifact_name}",
        )
    receipt_summary = _exact_descriptor(
        receipt.get("summary"), label="score-equivalence receipt summary"
    )
    summary_descriptor = relative_artifact_descriptor(
        registered["score_equivalence_summary"], repo_root=repo_root
    )
    if receipt_summary != summary_descriptor:
        raise RuntimeError("Score-equivalence receipt no longer binds the summary.")
    _require_git_blob_descriptor(
        commit=_SCORE_ARTIFACT_COMMIT,
        descriptor=receipt_summary,
        repo_root=repo_root,
        label="score-equivalence summary",
    )

    hulls = pd.read_parquet(registered["score_equivalence_hulls"])
    v1d = pd.read_parquet(registered["score_equivalence_v1d"])
    calibrators = pd.read_parquet(registered["score_equivalence_calibrators"])
    controls = pd.read_parquet(registered["score_equivalence_controls"])
    findings = _validate_score_frames(
        hulls,
        v1d,
        calibrators,
        controls,
        summary=summary,
    )
    return ScoreEquivalenceEvidence(
        summary=summary,
        receipt=receipt,
        hulls=hulls,
        v1d=v1d,
        calibrators=calibrators,
        controls=controls,
        findings=findings,
    )


def _require_descriptor_equals_registered(
    raw: Any,
    registered_path: Path,
    *,
    repo_root: Path,
    label: str,
    commit: str | None,
    cache: dict[tuple[str, int, str], Path],
) -> dict[str, Any]:
    descriptor = _exact_descriptor(raw, label=label)
    path = _descriptor_path(
        descriptor,
        repo_root=repo_root,
        label=label,
        cache=cache,
    )
    if path != registered_path.resolve():
        raise RuntimeError(f"{label} path differs from the registry.")
    if commit is not None:
        _require_git_blob_descriptor(
            commit=commit,
            descriptor=descriptor,
            repo_root=repo_root,
            label=label,
        )
    return descriptor


def _validate_phase_a_frames(
    records: pd.DataFrame,
    allocations: pd.DataFrame,
    taxonomy: pd.DataFrame,
    audits: pd.DataFrame,
    *,
    summary: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    observed_schemas = {
        "solve_records": dataframe_schema(records),
        "allocations": dataframe_schema(allocations),
        "set_taxonomy": dataframe_schema(taxonomy),
        "solver_audit": dataframe_schema(audits),
    }
    if _mapping(manifest, "official_schemas", label="Phase-A manifest") != observed_schemas:
        raise RuntimeError("Set-native Phase-A schemas differ from the sealed manifest.")
    cell_keys = ["window_id", "role", "period", "frontier_ruler", "frontier_coordinate"]
    audit_keys = ["window_id", "role", "period", "ruler", "coordinate"]
    taxonomy_keys = ["window_id", "role", "period"]
    if len(records) != 1248 or bool(records.duplicated(cell_keys).any()):
        raise RuntimeError("Set-native Phase-A solve census is not 1,248 unique cells.")
    if len(audits) != 1248 or bool(audits.duplicated(audit_keys).any()):
        raise RuntimeError("Set-native Phase-A solver-audit census is not 1,248 cells.")
    if len(taxonomy) != 208 or bool(taxonomy.duplicated(taxonomy_keys).any()):
        raise RuntimeError("Set-native Phase-A taxonomy census is not 208 menus.")
    if len(records.loc[records["role"].eq("primary_oot")]) != 720:
        raise RuntimeError("Set-native Phase-A primary census is not 720 cells.")
    if (
        set(records["window_id"].astype(str)) != set(_WINDOWS)
        or set(records["role"].astype(str)) != set(_ROLES)
        or set(records["frontier_ruler"].astype(str)) != set(_RULERS)
        or set(pd.to_numeric(records["frontier_coordinate"], errors="raise")) != set(_COORDINATES)
    ):
        raise RuntimeError("Set-native Phase-A design domains changed.")
    role_months = records[["role", "period"]].drop_duplicates().groupby("role").size().to_dict()
    if role_months != {"policy_development": 11, "primary_oot": 15}:
        raise RuntimeError("Set-native Phase-A role/month census is not 11/15.")
    per_menu = records.groupby(["window_id", "role", "period"], observed=True).size()
    if len(per_menu) != 208 or not per_menu.eq(6).all():
        raise RuntimeError("Every set-native menu must contain two rulers by three coordinates.")

    if (
        not records["policy_mode"].eq(records["frontier_ruler"]).all()
        or not records["comparator_rule"].eq(records["frontier_ruler"]).all()
        or not records["robust_guardrail"].eq(True).all()
        or not records["set_native_score"].eq("zero_iff_exact_singleton_zero_else_one").all()
        or not records["empty_set_convention"].eq("fail_closed_one").all()
        or not records["solver_status"].eq("Optimal").all()
        or not records["solver_backend_actual"].eq("highspy_exact_budget_simplex").all()
        or not records["cash_variable_present"].eq(False).all()
        or not np.isclose(records["total_allocated"], 1_000_000.0, rtol=0.0, atol=1.0e-8).all()
        or not records["budget_residual"].abs().le(1.0e-4).all()
    ):
        raise RuntimeError("Set-native Phase-A decision or solver contract changed.")
    normalized = records["frontier_ruler"].eq("normalized_score")
    if not (
        records.loc[normalized, "frontier_cap"].notna().all()
        and records.loc[normalized, "risk_tolerance"].notna().all()
        and records.loc[normalized, "objective_target"].isna().all()
        and records.loc[~normalized, "frontier_cap"].isna().all()
        and records.loc[~normalized, "risk_tolerance"].isna().all()
        and records.loc[~normalized, "objective_target"].notna().all()
    ):
        raise RuntimeError("Set-native ruler-specific cap fields changed semantics.")

    if len(allocations) != 126686:
        raise RuntimeError("Set-native funded allocation census is not 126,686 rows.")
    if (
        allocations["exposure"].le(0.0).any()
        or not allocations["set_risk"].isin((0.0, 1.0)).all()
        or not allocations["binary_set_type"]
        .isin(("empty", "singleton_zero", "singleton_one", "two_label"))
        .all()
        or not allocations["set_risk"]
        .eq(np.where(allocations["binary_set_type"].eq("singleton_zero"), 0.0, 1.0))
        .all()
        or not allocations["pd_effective"].eq(allocations["set_risk"]).all()
    ):
        raise RuntimeError("Set-native funded rows violate the binary-set score convention.")
    allocation_totals = (
        allocations.groupby(cell_keys, observed=True, sort=False)
        .agg(
            allocation_total=("exposure", "sum"),
            funded_rows=("id", "size"),
            expected_objective_from_allocations=("expected_payoff_contribution", "sum"),
            weighted_set_risk_from_allocations=(
                "set_risk",
                lambda values: float(
                    np.dot(
                        values.to_numpy(dtype=float),
                        allocations.loc[values.index, "exposure"].to_numpy(dtype=float),
                    )
                    / 1_000_000.0
                ),
            ),
        )
        .reset_index()
    )
    reconciled = records.merge(
        allocation_totals,
        on=cell_keys,
        how="outer",
        validate="one_to_one",
        indicator="_merge",
    )
    if set(reconciled["_merge"].astype(str)) != {"both"}:
        raise RuntimeError("Set-native allocations do not cover every Phase-A solve cell.")
    for observed, expected, tolerance in (
        ("allocation_total", "total_allocated", 1.0e-8),
        ("expected_objective_from_allocations", "expected_objective", 1.0e-8),
        ("weighted_set_risk_from_allocations", "weighted_set_risk", 1.0e-12),
    ):
        if not np.allclose(reconciled[observed], reconciled[expected], rtol=0.0, atol=tolerance):
            raise RuntimeError(f"Set-native allocation reconciliation failed for {expected}.")
    if not reconciled["funded_rows"].eq(reconciled["n_positive_exposure"]).all():
        raise RuntimeError("Set-native funded row counts do not match solve records.")

    taxonomy_counts = taxonomy[["n_empty", "n_singleton_zero", "n_singleton_one", "n_two_label"]]
    if (
        not taxonomy_counts.sum(axis=1).eq(taxonomy["n_candidates"]).all()
        or not taxonomy["n_risk_zero"].eq(taxonomy["n_singleton_zero"]).all()
        or not taxonomy["n_risk_one"]
        .eq(taxonomy["n_candidates"] - taxonomy["n_singleton_zero"])
        .all()
        or not taxonomy["empty_set_score"].eq(1.0).all()
    ):
        raise RuntimeError("Set-native taxonomy no longer partitions every candidate menu.")
    taxonomy_reconciliation = records.merge(
        taxonomy,
        on=taxonomy_keys,
        how="left",
        validate="many_to_one",
        suffixes=("", "_taxonomy"),
    )
    if (
        not taxonomy_reconciliation["n_candidates"]
        .eq(taxonomy_reconciliation["n_candidates_taxonomy"])
        .all()
    ):
        raise RuntimeError("Set-native solve records do not reconcile to taxonomy menus.")

    audit_renamed = audits.rename(
        columns={"ruler": "frontier_ruler", "coordinate": "frontier_coordinate"}
    )
    audit_join = records[cell_keys].merge(
        audit_renamed,
        on=cell_keys,
        how="outer",
        validate="one_to_one",
        indicator="_merge",
    )
    if set(audit_join["_merge"].astype(str)) != {"both"}:
        raise RuntimeError("Set-native solver audits do not reconcile to solve cells.")
    audit_columns = [column for column in audits.columns if column not in audit_keys]
    require_finite(audits, audit_columns, label="set-native solver audit")
    maxima = _mapping(summary, "audit_maxima", label="set-native Phase-A summary")
    for column in audit_columns:
        if not np.isclose(
            float(audits[column].abs().max()),
            float(maxima[column]),
            rtol=0.0,
            atol=1.0e-18,
        ):
            raise RuntimeError(f"Set-native solver-audit maximum changed for {column}.")

    counts = _mapping(summary, "counts", label="set-native Phase-A summary")
    if dict(counts) != {
        "cells": 1248,
        "primary_cells": 720,
        "funded_rows": 126686,
        "taxonomy_rows": 208,
        "solver_audit_rows": 1248,
    }:
        raise RuntimeError("Set-native Phase-A summary census changed.")
    set_counts = _mapping(summary, "set_counts", label="set-native Phase-A summary")
    observed_set_counts = {
        "n_empty": int(taxonomy["n_empty"].sum()),
        "n_singleton_zero": int(taxonomy["n_singleton_zero"].sum()),
        "n_singleton_one": int(taxonomy["n_singleton_one"].sum()),
        "n_two_label": int(taxonomy["n_two_label"].sum()),
        "n_risk_zero": int(taxonomy["n_risk_zero"].sum()),
        "n_risk_one": int(taxonomy["n_risk_one"].sum()),
    }
    if dict(set_counts) != observed_set_counts:
        raise RuntimeError("Set-native Phase-A taxonomy totals changed.")
    return {
        "phase_a_cells": 1248,
        "primary_cells": 720,
        "taxonomy_rows": 208,
        "solver_audit_rows": 1248,
        "funded_rows": 126686,
        "set_counts": observed_set_counts,
    }


def _validate_evaluated_reconciliation(
    records: pd.DataFrame,
    evaluated: pd.DataFrame,
) -> None:
    _require_exact_columns(evaluated, _EVALUATED_COLUMNS, label="set-native evaluated portfolios")
    if len(evaluated) != 720:
        raise RuntimeError("Set-native evaluated portfolio census is not 720.")
    keys = ["window_id", "role", "period", "frontier_ruler", "frontier_coordinate"]
    primary = records.loc[records["role"].eq("primary_oot")].copy()
    require_exact_frame(
        evaluated.loc[:, list(records.columns)],
        primary,
        keys=keys,
        label="Phase-A to evaluated set-native reconciliation",
    )
    if (
        not evaluated["role"].eq("primary_oot").all()
        or not evaluated["full_budget"].eq(True).all()
        or not np.isclose(evaluated["total_allocated"], 1_000_000.0, rtol=0.0, atol=1.0e-8).all()
        or not evaluated["realized_payoff_lower"].le(evaluated["realized_payoff_upper"]).all()
        or not evaluated["weighted_default_lower"].le(evaluated["weighted_default_upper"]).all()
        or not evaluated["weighted_miscoverage_lower"]
        .le(evaluated["weighted_miscoverage_upper"])
        .all()
    ):
        raise RuntimeError("Set-native evaluated portfolio bounds or role changed.")


def _validate_contrast_frame(
    frame: pd.DataFrame,
    *,
    pooled: bool,
) -> dict[str, tuple[int, int, int]]:
    label = "pooled set-native contrasts" if pooled else "monthly set-native contrasts"
    expected_columns = _POOLED_COLUMNS if pooled else _MONTHLY_COLUMNS
    _require_exact_columns(frame, expected_columns, label=label)
    expected_rows = 1200 if pooled else 18000
    if len(frame) != expected_rows:
        raise RuntimeError(f"{label} census changed from {expected_rows}.")
    keys = ["window_id", "frontier_ruler", "frontier_coordinate", "theta", "gamma"]
    domains: dict[str, Sequence[Any]] = {
        "window_id": _WINDOWS,
        "frontier_ruler": _RULERS,
        "frontier_coordinate": _COORDINATES,
        "theta": _THETA_GAMMA,
        "gamma": _THETA_GAMMA,
    }
    if not pooled:
        periods = tuple(sorted(frame["period"].astype(str).unique()))
        if len(periods) != 15:
            raise RuntimeError("Monthly set-native contrasts no longer cover 15 periods.")
        keys.insert(1, "period")
        domains = {
            "window_id": _WINDOWS,
            "period": periods,
            "frontier_ruler": _RULERS,
            "frontier_coordinate": _COORDINATES,
            "theta": _THETA_GAMMA,
            "gamma": _THETA_GAMMA,
        }
    require_exact_grid(frame, domains=domains, label=label)
    expected_scope = "pooled_primary_window" if pooled else "primary_month"
    expected_capital = 15_000_000.0 if pooled else 1_000_000.0
    if (
        not frame["scope"].eq(expected_scope).all()
        or not frame["role"].eq("primary_oot").all()
        or not frame["policy_a"].eq(frame["robust_policy"]).all()
        or not frame["policy_b"].eq(frame["embedding_policy"]).all()
        or not frame["contrast"]
        .eq(frame["robust_policy"].astype(str) + "_minus_" + frame["embedding_policy"].astype(str))
        .all()
        or not frame["policy_a_normalization_capital"].eq(expected_capital).all()
        or not frame["policy_b_normalization_capital"].eq(expected_capital).all()
        or not frame["causal_interpretation"].eq(False).all()
    ):
        raise RuntimeError(f"{label} identity, normalization, or causal boundary changed.")

    width_specs = (
        (
            "realized_payoff_difference_lower",
            "realized_payoff_difference_upper",
            "realized_payoff_identification_width",
        ),
        (
            "realized_payoff_rate_difference_lower",
            "realized_payoff_rate_difference_upper",
            "realized_payoff_rate_identification_width",
        ),
        (
            "weighted_default_difference_lower",
            "weighted_default_difference_upper",
            "weighted_default_identification_width",
        ),
        (
            "weighted_miscoverage_difference_lower",
            "weighted_miscoverage_difference_upper",
            "weighted_miscoverage_identification_width",
        ),
    )
    numeric = [
        column
        for column in frame.columns
        if pd.api.types.is_numeric_dtype(frame[column].dtype)
        and not pd.api.types.is_bool_dtype(frame[column].dtype)
    ]
    require_finite(frame, numeric, label=label)
    for lower, upper, width in width_specs:
        if (
            not frame[lower].le(frame[upper]).all()
            or not np.allclose(
                frame[upper] - frame[lower], frame[width], rtol=1.0e-12, atol=1.0e-10
            )
            or frame[width].lt(-1.0e-12).any()
        ):
            raise RuntimeError(f"{label} sharp-bound reconciliation failed for {width}.")
    if not (
        np.allclose(
            frame["realized_payoff_difference_lower"] / expected_capital,
            frame["realized_payoff_rate_difference_lower"],
            rtol=1.0e-12,
            atol=1.0e-12,
        )
        and np.allclose(
            frame["realized_payoff_difference_upper"] / expected_capital,
            frame["realized_payoff_rate_difference_upper"],
            rtol=1.0e-12,
            atol=1.0e-12,
        )
    ):
        raise RuntimeError(f"{label} payoff dollars do not reconcile to standardized rates.")

    totals: dict[str, tuple[int, int, int]] = {}
    for metric, (lower, upper, robust_flag) in _METRICS.items():
        positive = frame[lower].gt(0.0)
        negative = frame[upper].lt(0.0)
        includes_zero = ~(positive | negative)
        if (positive & negative).any() or not frame[robust_flag].eq(positive | negative).all():
            raise RuntimeError(f"{label} sign partition changed for {metric}.")
        totals[metric] = (
            int(positive.sum()),
            int(negative.sum()),
            int(includes_zero.sum()),
        )
    expected = _EXPECTED_SIGN_TOTALS["pooled" if pooled else "monthly"]
    if totals != expected:
        raise RuntimeError(f"{label} exact sign census changed: {totals}.")
    return totals


def _validate_set_native_boundaries(
    *,
    phase_a_freeze: Mapping[str, Any],
    phase_a_summary: Mapping[str, Any],
    phase_a_receipt: Mapping[str, Any],
    phase_a_manifest: Mapping[str, Any],
    evaluation_summary: Mapping[str, Any],
    evaluation_receipt: Mapping[str, Any],
    evaluation_manifest: Mapping[str, Any],
) -> None:
    for payload, label in (
        (phase_a_freeze, "set-native Phase-A freeze"),
        (phase_a_summary, "set-native Phase-A summary"),
        (phase_a_receipt, "set-native Phase-A receipt"),
        (phase_a_manifest, "set-native Phase-A manifest"),
    ):
        _require_protocol_identity(
            payload,
            schema="2026-07-31.v1.1",
            status=_SET_PHASE_A_STATUS,
            run_tag=_SET_PHASE_A_RUN_TAG,
            protocol_tag=_SET_P1_TAG,
            protocol_commit=_SET_P1_COMMIT,
            label=label,
        ) if "protocol" in payload else None
        _require_no_side_effects(
            payload, label=label
        ) if "protected_stages_run" in payload else None
    for payload, label in (
        (evaluation_summary, "set-native evaluation summary"),
        (evaluation_receipt, "set-native evaluation receipt"),
        (evaluation_manifest, "set-native evaluation manifest"),
    ):
        _require_protocol_identity(
            payload,
            schema="2026-07-31.v1.phase-b.1",
            status=_SET_PHASE_B_STATUS,
            run_tag=_SET_PHASE_B_RUN_TAG,
            protocol_tag=_SET_P2_TAG,
            protocol_commit=_SET_P2_COMMIT,
            label=label,
        )
        _require_no_side_effects(
            payload, label=label
        ) if "protected_stages_run" in payload else None
    if (
        phase_a_freeze.get("outcome_columns_passed_to_frontier") != []
        or phase_a_summary.get("outcome_columns_passed") != []
        or phase_a_receipt.get("outcome_columns_passed") != []
    ):
        raise RuntimeError("Set-native Phase A reports outcome leakage.")
    for payload, label in (
        (phase_a_freeze, "Phase-A freeze"),
        (phase_a_summary, "Phase-A summary"),
        (evaluation_summary, "evaluation summary"),
        (evaluation_manifest, "evaluation manifest"),
    ):
        selection = _mapping(payload, "selection", label=label)
        if any(value is not None for value in selection.values()):
            raise RuntimeError(f"{label} reports a selected result.")
    # The tagged manifest's legacy ``joint_coverage_for_cartesian_product``
    # field is a fail-closed claim boundary: false means that no joint-coverage
    # guarantee was established, not that realized joint noncoverage was proved.
    if (
        evaluation_summary.get("policy_winner") is not None
        or evaluation_summary.get("causal_interpretation") is not False
        or evaluation_manifest.get("policy_winner") is not None
        or evaluation_manifest.get("causal_interpretation") is not False
        or evaluation_manifest.get("conformal_guarantee_repair") is not False
        or evaluation_manifest.get("joint_coverage_for_cartesian_product") is not False
        or evaluation_manifest.get("probabilistic_robustness_guarantee") is not False
        or evaluation_receipt.get("outcome_refit") is not False
        or evaluation_receipt.get("outcome_selection") is not False
    ):
        raise RuntimeError("Set-native evaluation claim boundary changed.")


def _load_set_native(
    registered: Mapping[str, Path],
    *,
    repo_root: Path,
    cache: dict[tuple[str, int, str], Path],
) -> SetNativeEvidence:
    phase_a_freeze = _load_json_object(
        registered["set_native_phase_a_freeze"], label="set-native Phase-A freeze"
    )
    phase_a_summary = _load_json_object(
        registered["set_native_phase_a_summary"], label="set-native Phase-A summary"
    )
    phase_a_receipt = _load_json_object(
        registered["set_native_phase_a_receipt"], label="set-native Phase-A receipt"
    )
    phase_a_manifest = _load_json_object(
        registered["set_native_phase_a_manifest"], label="set-native Phase-A manifest"
    )
    evaluation_summary = _load_json_object(
        registered["set_native_evaluation_summary"], label="set-native evaluation summary"
    )
    evaluation_receipt = _load_json_object(
        registered["set_native_evaluation_receipt"], label="set-native evaluation receipt"
    )
    evaluation_manifest = _load_json_object(
        registered["set_native_evaluation_manifest"], label="set-native evaluation manifest"
    )
    _validate_set_native_boundaries(
        phase_a_freeze=phase_a_freeze,
        phase_a_summary=phase_a_summary,
        phase_a_receipt=phase_a_receipt,
        phase_a_manifest=phase_a_manifest,
        evaluation_summary=evaluation_summary,
        evaluation_receipt=evaluation_receipt,
        evaluation_manifest=evaluation_manifest,
    )
    if phase_a_freeze.get("artifact_status") != "pending_git_artifact_commit_and_annotated_tag":
        raise RuntimeError("Set-native Phase-A artifact status changed.")
    if (
        evaluation_manifest.get("artifact_status")
        != "pending_git_artifact_commit_and_annotated_tag"
    ):
        raise RuntimeError("Set-native Phase-B artifact status changed.")
    for payload, label, commit in (
        (phase_a_freeze, "set-native Phase-A freeze", _SET_P1_COMMIT),
        (evaluation_manifest, "set-native evaluation manifest", _SET_P2_COMMIT),
    ):
        environment = _mapping(payload, "environment", label=label)
        if environment.get("uv_lock_sha256") != _UV_LOCK_SHA256:
            raise RuntimeError(f"{label} scientific lock changed.")
        git = _mapping(payload, "git", label=label)
        if (
            git.get("commit") != commit
            or git.get("dirty") is not False
            or git.get("dirty_entries") != 0
            or git.get("dirty_paths") != []
        ):
            raise RuntimeError(f"{label} was not executed from its clean protocol commit.")
        _require_implementation_provenance(
            payload,
            commit=commit,
            repo_root=repo_root,
            label=label,
        )
    if _mapping(phase_a_freeze, "environment", label="Phase-A freeze") != _mapping(
        evaluation_manifest, "environment", label="evaluation manifest"
    ):
        raise RuntimeError("Set-native scientific environment changed from Phase A to Phase B.")

    phase_a_descriptor_map = {
        "solve_records": "set_native_phase_a_solve_records",
        "allocations": "set_native_phase_a_allocations",
        "set_taxonomy": "set_native_phase_a_taxonomy",
        "solver_audit": "set_native_phase_a_solver_audit",
    }
    official = _mapping(phase_a_manifest, "official_artifacts", label="Phase-A manifest")
    if official != _mapping(phase_a_freeze, "official_artifacts", label="Phase-A freeze"):
        raise RuntimeError("Set-native Phase-A freeze and manifest descriptors disagree.")
    phase_a_descriptors: dict[str, dict[str, Any]] = {}
    for artifact_name, registered_name in phase_a_descriptor_map.items():
        descriptor = _require_descriptor_equals_registered(
            official.get(artifact_name),
            registered[registered_name],
            repo_root=repo_root,
            label=f"set-native Phase-A {artifact_name}",
            commit=_SET_A1_COMMIT,
            cache=cache,
        )
        phase_a_descriptors[artifact_name] = descriptor
    phase_a_meta = {
        "freeze": "set_native_phase_a_freeze",
        "summary": "set_native_phase_a_summary",
        "receipt": "set_native_phase_a_receipt",
        "phase_a_manifest": "set_native_phase_a_manifest",
    }
    source_phase_a: dict[str, Any] = {
        "artifact_tag": _SET_A1_TAG,
        "artifact_commit": _SET_A1_COMMIT,
    }
    for name, registered_name in phase_a_meta.items():
        descriptor = relative_artifact_descriptor(registered[registered_name], repo_root=repo_root)
        _require_git_blob_descriptor(
            commit=_SET_A1_COMMIT,
            descriptor=descriptor,
            repo_root=repo_root,
            label=f"set-native Phase-A {name}",
        )
        source_phase_a[name] = descriptor
    source_phase_a |= {
        "solve_records": phase_a_descriptors["solve_records"],
        "allocation": phase_a_descriptors["allocations"],
        "set_taxonomy": phase_a_descriptors["set_taxonomy"],
        "solver_audit": phase_a_descriptors["solver_audit"],
    }

    phase_b_descriptor_map = {
        "evaluated_portfolios": "set_native_evaluated_portfolios",
        "monthly_v1d_contrasts": "set_native_monthly_contrasts",
        "window_v1d_contrasts": "set_native_window_contrasts",
        "summary": "set_native_evaluation_summary",
        "receipt": "set_native_evaluation_receipt",
    }
    for artifact_name, registered_name in phase_b_descriptor_map.items():
        _require_descriptor_equals_registered(
            evaluation_manifest.get(artifact_name),
            registered[registered_name],
            repo_root=repo_root,
            label=f"set-native Phase-B {artifact_name}",
            commit=_SET_B1_COMMIT,
            cache=cache,
        )
    manifest_descriptor = relative_artifact_descriptor(
        registered["set_native_evaluation_manifest"], repo_root=repo_root
    )
    _require_git_blob_descriptor(
        commit=_SET_B1_COMMIT,
        descriptor=manifest_descriptor,
        repo_root=repo_root,
        label="set-native Phase-B manifest",
    )

    phase_b_config = _load_yaml_object(
        registered["set_native_phase_b_config"], label="set-native Phase-B config"
    )
    blocked = _load_yaml_object(
        registered["set_native_phase_b_blocked_template"],
        label="set-native blocked Phase-B template",
    )
    if (
        phase_b_config.get("protocol_status") != "locked_hash_pinned_phase_b_before_outcomes"
        or phase_b_config.get("protocol_tag") != _SET_P2_TAG
        or phase_b_config.get("run_tag") != _SET_PHASE_B_RUN_TAG
        or blocked.get("protocol_status") != "blocked_pending_phase_a_artifact_hashes"
        or _mapping(blocked, "phase_chain", label="blocked template").get("phase_a_protocol_commit")
        is not None
        or _mapping(blocked, "source_phase_a", label="blocked template").get("artifact_commit")
        is not None
    ):
        raise RuntimeError("Set-native Phase-B lock or blocked template changed.")
    if _mapping(phase_b_config, "source_phase_a", label="Phase-B config") != source_phase_a:
        raise RuntimeError("Set-native P2 config no longer hash-pins the exact Phase-A source.")
    for payload, label in (
        (evaluation_receipt, "evaluation receipt"),
        (evaluation_manifest, "evaluation manifest"),
    ):
        if _mapping(payload, "source_phase_a", label=label) != source_phase_a:
            raise RuntimeError(f"Set-native {label} Phase-A source changed.")
        if _mapping(payload, "source_v1d", label=label) != _mapping(
            phase_b_config, "source_v1d", label="Phase-B config"
        ):
            raise RuntimeError(f"Set-native {label} V1d source changed.")
        if _mapping(payload, "endpoint_source", label=label) != _mapping(
            phase_b_config, "endpoint_source", label="Phase-B config"
        ):
            raise RuntimeError(f"Set-native {label} endpoint source changed.")

    records = pd.read_parquet(registered["set_native_phase_a_solve_records"])
    allocations = pd.read_parquet(registered["set_native_phase_a_allocations"])
    taxonomy = pd.read_parquet(registered["set_native_phase_a_taxonomy"])
    audits = pd.read_parquet(registered["set_native_phase_a_solver_audit"])
    phase_a_findings = _validate_phase_a_frames(
        records,
        allocations,
        taxonomy,
        audits,
        summary=phase_a_summary,
        manifest=phase_a_manifest,
    )
    evaluated = pd.read_parquet(registered["set_native_evaluated_portfolios"])
    monthly = pd.read_parquet(registered["set_native_monthly_contrasts"])
    pooled = pd.read_parquet(registered["set_native_window_contrasts"])
    _validate_evaluated_reconciliation(records, evaluated)
    monthly_signs = _validate_contrast_frame(monthly, pooled=False)
    pooled_signs = _validate_contrast_frame(pooled, pooled=True)
    if (
        evaluation_summary.get("evaluated_robust_cells") != 720
        or evaluation_summary.get("monthly_robust_minus_v1d_contrasts") != 18000
        or evaluation_summary.get("pooled_robust_minus_v1d_contrasts") != 1200
        or evaluation_manifest.get("evaluated_robust_cells") != 720
        or evaluation_manifest.get("monthly_robust_minus_v1d_contrasts") != 18000
        or evaluation_manifest.get("pooled_robust_minus_v1d_contrasts") != 1200
        or evaluation_summary.get("comparison")
        != "same_window_month_ruler_coordinate_all_25_v1d_theta_gamma_cells"
        or evaluation_summary.get("common_outcome_assignment") != "loanwise_sharp_on_funded_union"
    ):
        raise RuntimeError("Set-native Phase-B census or comparison contract changed.")
    findings = {
        **phase_a_findings,
        "evaluated_robust_cells": 720,
        "monthly_contrasts": 18000,
        "pooled_contrasts": 1200,
        "monthly_sign_totals": monthly_signs,
        "pooled_sign_totals": pooled_signs,
        "sign_order": ["positive", "negative", "includes_zero"],
        "selected_result": None,
        "policy_winner": None,
        "conformal_guarantee_repair": False,
        "joint_coverage_guarantee_established": False,
        "probabilistic_robustness_guarantee": False,
        "causal_interpretation": False,
    }
    return SetNativeEvidence(
        phase_a_freeze=phase_a_freeze,
        phase_a_summary=phase_a_summary,
        phase_a_receipt=phase_a_receipt,
        phase_a_manifest=phase_a_manifest,
        evaluation_summary=evaluation_summary,
        evaluation_receipt=evaluation_receipt,
        evaluation_manifest=evaluation_manifest,
        solve_records=records,
        taxonomy=taxonomy,
        solver_audit=audits,
        evaluated_portfolios=evaluated,
        monthly_contrasts=monthly,
        window_contrasts=pooled,
        findings=findings,
    )


def _validate_dual_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("schema_version") != "2026-08-01.v1.1"
        or config.get("protocol_status") != "locked_candidate_outcome_free_before_execution"
        or config.get("protocol_tag") != _DUAL_PROTOCOL_TAG
        or config.get("run_tag") != _DUAL_RUN_TAG
    ):
        raise RuntimeError("Dual-coefficient locked config identity changed.")
    predecessor = _mapping(config, "predecessor", label="dual-coefficient config")
    expected_predecessor_identity = {
        "run_tag": _SET_PHASE_A_RUN_TAG,
        "protocol_tag": _SET_P1_TAG,
        "protocol_commit": _SET_P1_COMMIT,
        "artifact_tag": _SET_A1_TAG,
        "artifact_commit": _SET_A1_COMMIT,
    }
    changed = {
        key: predecessor.get(key)
        for key, value in expected_predecessor_identity.items()
        if predecessor.get(key) != value
    }
    if changed:
        raise RuntimeError(f"Dual-coefficient predecessor identity changed: {changed}.")
    inherited = _mapping(config, "inherited_contract", label="dual-coefficient config")
    expected_inherited = {
        "budget_rule": "exact_equality",
        "budget_dollars": 1_000_000.0,
        "cash_variable_present": False,
        "loan_bounds": "zero_to_requested_amount",
        "purpose_partition": "one_exhaustive_disjoint_group_per_candidate",
        "purpose_constraints": "upper_only",
        "maximum_concentration_by_purpose": 0.25,
        "contractual_rate_domain": [0.0, 1.0],
        "lgd": 0.45,
        "exact_set_score": "zero_iff_singleton_zero_else_one",
        "empty_set_semantics": "declared_fail_closed_completion_to_both_labels",
    }
    if dict(inherited) != expected_inherited:
        raise RuntimeError("Dual-coefficient inherited optimization contract changed.")
    theorem = _mapping(config, "conditional_theorem", label="dual-coefficient config")
    if (
        theorem.get("name") != "singleton_zero_substitution_and_continuous_frontier_collapse"
        or theorem.get("singleton_zero_payoff") != "contractual_rate"
        or theorem.get("non_singleton_zero_payoff") != "negative_lgd"
        or theorem.get("cap_domain") != [0.0, 1.0]
        or theorem.get("conclusion")
        != "every_maximin_optimizer_has_zero_non_singleton_zero_exposure"
        or theorem.get("frontier_conclusion")
        != "same_singleton_zero_maximin_optimal_face_and_value_for_every_cap"
    ):
        raise RuntimeError("Dual-coefficient conditional theorem contract changed.")
    claim_boundary = _mapping(config, "claim_boundary", label="dual-coefficient config")
    expected_boundary = dict.fromkeys(_DUAL_CLAIM_BOUNDARY_KEYS, True)
    if dict(claim_boundary) != expected_boundary:
        raise RuntimeError("Dual-coefficient claim boundary changed.")
    census = _mapping(config, "expected_census", label="dual-coefficient config")
    if dict(census) != {
        "predecessor_rows": 1248,
        "rows_per_menu": 6,
        "windows": 8,
        "role_months_per_window": 26,
        "development_months_per_window": 11,
        "primary_months_per_window": 15,
        "menu_certificates": 208,
        "taxonomy_rows": 208,
    }:
        raise RuntimeError("Dual-coefficient locked census changed.")
    output = _mapping(config, "output", label="dual-coefficient config")
    if output.get("artifact_tag") != _DUAL_ARTIFACT_TAG or output.get("dvc_required") is not False:
        raise RuntimeError("Dual-coefficient artifact contract changed.")


def _validate_dual_boundaries(
    *,
    config: Mapping[str, Any],
    freeze: Mapping[str, Any],
    summary: Mapping[str, Any],
    receipt: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> None:
    _validate_dual_config(config)
    for payload, label in (
        (freeze, "dual-coefficient freeze"),
        (summary, "dual-coefficient summary"),
        (receipt, "dual-coefficient receipt"),
    ):
        _require_protocol_identity(
            payload,
            schema="2026-08-01.v1.1",
            status=_DUAL_STATUS,
            run_tag=_DUAL_RUN_TAG,
            protocol_tag=_DUAL_PROTOCOL_TAG,
            protocol_commit=_DUAL_PROTOCOL_COMMIT,
            label=label,
        )
        _require_no_side_effects(payload, label=label)
    if (
        manifest.get("schema_version") != "2026-08-01.v1.1"
        or manifest.get("status") != _DUAL_STATUS
        or manifest.get("run_tag") != _DUAL_RUN_TAG
    ):
        raise RuntimeError("Dual-coefficient manifest identity changed.")
    if (
        freeze.get("artifact_status") != "pending_git_artifact_commit_and_annotated_tag"
        or freeze.get("outcome_columns_passed") != []
        or freeze.get("new_optimizations") != 0
        or receipt.get("predecessor_rows_read") != 1456
        or receipt.get("new_optimizations") != 0
        or receipt.get("raw_archive_read") is not False
        or receipt.get("outcome_columns_passed") != []
        or summary.get("raw_archive_read") is not False
        or summary.get("outcome_columns_passed") != []
        or summary.get("validity_claim_established") is not False
    ):
        raise RuntimeError("Dual-coefficient outcome-free execution boundary changed.")
    if dict(_mapping(summary, "selection", label="dual-coefficient summary")) != {
        "cap": None,
        "window": None,
        "policy": None,
    }:
        raise RuntimeError("Dual-coefficient summary reports a selected result.")
    if dict(_mapping(summary, "counts", label="dual-coefficient summary")) != {
        "menu_certificates": 208,
        "new_optimizations": 0,
    }:
        raise RuntimeError("Dual-coefficient summary census changed.")
    if (
        summary.get("all_conditions_certified") is not True
        or summary.get("all_maximin_optimizers_singleton_zero") is not True
        or summary.get("continuous_cap_frontier_collapses") is not True
        or summary.get("cap_domain") != [0.0, 1.0]
    ):
        raise RuntimeError("Dual-coefficient conditional conclusion changed.")
    if dict(_mapping(freeze, "artifact_contract", label="dual-coefficient freeze")) != {
        "expected_tag": _DUAL_ARTIFACT_TAG,
        "dvc_required": False,
    }:
        raise RuntimeError("Dual-coefficient freeze artifact contract changed.")
    if dict(_mapping(freeze, "predecessor", label="dual-coefficient freeze")) != {
        "run_tag": _SET_PHASE_A_RUN_TAG,
        "artifact_tag": _SET_A1_TAG,
        "artifact_commit": _SET_A1_COMMIT,
    }:
        raise RuntimeError("Dual-coefficient frozen predecessor changed.")


def _dual_certificate_digest(frame: pd.DataFrame) -> str:
    ordered = frame.sort_values(["window_id", "role", "period"], kind="mergesort")
    payload = json.dumps(
        ordered.to_dict(orient="records"),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_dual_certificates(
    certificates: pd.DataFrame,
    *,
    summary: Mapping[str, Any],
    manifest: Mapping[str, Any],
    expected_menu_keys: set[tuple[str, str, str]],
) -> dict[str, Any]:
    _require_exact_columns(certificates, _DUAL_COLUMNS, label="dual-coefficient certificates")
    schemas = _mapping(manifest, "official_schemas", label="dual-coefficient manifest")
    if set(schemas) != {"menu_certificates"} or schemas.get(
        "menu_certificates"
    ) != dataframe_schema(certificates):
        raise RuntimeError("Dual-coefficient certificate schema differs from the sealed manifest.")
    if (
        len(certificates) != 208
        or bool(certificates.duplicated(["window_id", "role", "period"]).any())
        or set(certificates[["window_id", "role", "period"]].itertuples(index=False, name=None))
        != expected_menu_keys
    ):
        raise RuntimeError("Dual-coefficient census is not the exact 208 predecessor menus.")
    if set(certificates["window_id"].astype(str)) != set(_WINDOWS):
        raise RuntimeError("Dual-coefficient certificate window domain changed.")
    role_counts = certificates.groupby("role", observed=True).size().to_dict()
    if role_counts != {"policy_development": 88, "primary_oot": 120}:
        raise RuntimeError("Dual-coefficient role census changed from 88/120.")
    window_roles = certificates.groupby(["window_id", "role"], observed=True).size().unstack()
    if (
        set(window_roles.columns.astype(str)) != set(_ROLES)
        or not window_roles["policy_development"].eq(11).all()
        or not window_roles["primary_oot"].eq(15).all()
    ):
        raise RuntimeError("Dual-coefficient within-window role census changed from 11/15.")

    numeric = [
        column
        for column in certificates.columns
        if pd.api.types.is_numeric_dtype(certificates[column].dtype)
        and not pd.api.types.is_bool_dtype(certificates[column].dtype)
    ]
    require_finite(certificates, numeric, label="dual-coefficient certificates")
    count_columns = (
        "predecessor_rows",
        "minimum_n_candidates",
        "maximum_n_candidates",
        "n_candidates",
        "n_empty",
        "n_singleton_zero",
        "n_singleton_one",
        "n_two_label",
        "n_risk_zero",
        "n_risk_one",
    )
    if certificates[list(count_columns)].lt(0).any(axis=None):
        raise RuntimeError("Dual-coefficient certificate contains a negative count.")
    taxonomy_total = certificates[
        ["n_empty", "n_singleton_zero", "n_singleton_one", "n_two_label"]
    ].sum(axis=1)
    if (
        not certificates["predecessor_rows"].eq(6).all()
        or not certificates["minimum_score"].abs().le(1.0e-12).all()
        or not certificates["minimum_n_candidates"].eq(certificates["maximum_n_candidates"]).all()
        or not certificates["minimum_n_candidates"].eq(certificates["n_candidates"]).all()
        or not taxonomy_total.eq(certificates["n_candidates"]).all()
        or not certificates["n_risk_zero"].eq(certificates["n_singleton_zero"]).all()
        or not certificates["n_risk_one"]
        .eq(certificates["n_candidates"] - certificates["n_singleton_zero"])
        .all()
    ):
        raise RuntimeError(
            "Dual-coefficient predecessor or binary-set taxonomy failed to reconcile."
        )
    if (
        not certificates["maximum_abs_budget_residual"].le(1.0e-4).all()
        or not certificates["minimum_total_allocated"].sub(1_000_000.0).abs().le(1.0e-4).all()
        or not certificates["maximum_total_allocated"].sub(1_000_000.0).abs().le(1.0e-4).all()
        or not certificates["budget_dollars"].eq(1_000_000.0).all()
        or not certificates["purpose_cap"].eq(0.25).all()
        or not certificates["lgd"].eq(0.45).all()
        or not certificates["contractual_rate_lower"].eq(0.0).all()
        or not certificates["contractual_rate_upper"].eq(1.0).all()
        or not certificates["empty_set_score"].eq(1.0).all()
        or not certificates["capacity_lower_bound_dollars"].eq(1_000_000.0).all()
    ):
        raise RuntimeError("Dual-coefficient numerical theorem conditions changed.")
    if (
        not certificates[list(_DUAL_CONDITION_COLUMNS)].eq(True).all(axis=None)
        or not certificates["capacity_certificate"]
        .eq("feasible_exact_budget_zero_minimum_set_score")
        .all()
        or not certificates["payoff_definition"]
        .eq("min_standardized_payoff_over_completed_nonempty_set_with_declared_empty_fail_closure")
        .all()
        or not certificates["all_maximin_optimizers_singleton_zero"].eq(True).all()
        or not certificates["continuous_cap_frontier_collapses"].eq(True).all()
        or not certificates["cap_domain_lower"].eq(0.0).all()
        or not certificates["cap_domain_upper"].eq(1.0).all()
    ):
        raise RuntimeError("Dual-coefficient logical certificate conclusion changed.")
    forbidden_true = (
        "new_optimization_executed",
        "raw_archive_read",
        "optimizer_unique_certified",
        "policy_selected",
        "validity_claim_established",
    )
    if certificates[list(forbidden_true)].eq(True).any(axis=None):
        raise RuntimeError("Dual-coefficient certificate exceeds its claim boundary.")
    digest = _dual_certificate_digest(certificates)
    if summary.get("certificate_sha256") != digest:
        raise RuntimeError("Dual-coefficient canonical certificate digest changed.")
    return {
        "menu_certificates": 208,
        "role_menu_certificates": {"policy_development": 88, "primary_oot": 120},
        "new_optimizations": 0,
        "all_conditions_certified": True,
        "all_maximin_optimizers_singleton_zero": True,
        "continuous_cap_frontier_collapses": True,
        "cap_domain": [0.0, 1.0],
        "conditional_on_inherited_constraint_and_payoff_contract": True,
        "raw_archive_read": False,
        "outcome_columns_passed": [],
        "selected_result": None,
        "policy_winner": None,
        "optimizer_unique_certified": False,
        "conformal_validity_repair": False,
        "joint_cartesian_product_coverage_established": False,
        "probabilistic_robustness_guarantee": False,
        "funded_or_selected_set_validity": False,
        "causal_or_prospective_claim": False,
    }


def _load_dual_coefficient(
    registered: Mapping[str, Path],
    *,
    repo_root: Path,
    cache: dict[tuple[str, int, str], Path],
) -> DualCoefficientEvidence:
    config = _load_yaml_object(
        registered["dual_coefficient_config"], label="dual-coefficient config"
    )
    freeze = _load_json_object(
        registered["dual_coefficient_freeze"], label="dual-coefficient freeze"
    )
    summary = _load_json_object(
        registered["dual_coefficient_summary"], label="dual-coefficient summary"
    )
    receipt = _load_json_object(
        registered["dual_coefficient_receipt"], label="dual-coefficient receipt"
    )
    manifest = _load_json_object(
        registered["dual_coefficient_manifest"], label="dual-coefficient manifest"
    )
    _validate_dual_boundaries(
        config=config,
        freeze=freeze,
        summary=summary,
        receipt=receipt,
        manifest=manifest,
    )
    environment = _mapping(freeze, "environment", label="dual-coefficient freeze")
    if environment.get("uv_lock_sha256") != _UV_LOCK_SHA256:
        raise RuntimeError("Dual-coefficient scientific lock changed.")
    git = _mapping(freeze, "git", label="dual-coefficient freeze")
    if (
        git.get("commit") != _DUAL_PROTOCOL_COMMIT
        or git.get("dirty") is not False
        or git.get("dirty_entries") != 0
        or git.get("dirty_paths") != []
    ):
        raise RuntimeError("Dual-coefficient execution was not clean at its protocol commit.")
    implementation = _mapping(freeze, "implementation_provenance", label="dual-coefficient freeze")
    source_files = _mapping(
        implementation, "source_files", label="dual-coefficient implementation provenance"
    )
    if set(source_files) != set(_DUAL_IMPLEMENTATION_PATHS):
        raise RuntimeError("Dual-coefficient implementation inventory changed.")
    _require_implementation_provenance(
        freeze,
        commit=_DUAL_PROTOCOL_COMMIT,
        repo_root=repo_root,
        label="dual-coefficient freeze",
    )

    official_freeze = _mapping(freeze, "official_artifacts", label="dual-coefficient freeze")
    official_manifest = _mapping(manifest, "official_artifacts", label="dual-coefficient manifest")
    if set(official_freeze) != {"menu_certificates"} or official_freeze != official_manifest:
        raise RuntimeError("Dual-coefficient freeze and manifest artifact descriptors disagree.")
    _require_descriptor_equals_registered(
        official_manifest.get("menu_certificates"),
        registered["dual_coefficient_certificates"],
        repo_root=repo_root,
        label="dual-coefficient menu certificates",
        commit=_DUAL_ARTIFACT_COMMIT,
        cache=cache,
    )
    for descriptor_name, registered_name in (
        ("summary", "dual_coefficient_summary"),
        ("execution_receipt", "dual_coefficient_receipt"),
        ("manifest", "dual_coefficient_manifest"),
    ):
        _require_descriptor_equals_registered(
            freeze.get(descriptor_name),
            registered[registered_name],
            repo_root=repo_root,
            label=f"dual-coefficient {descriptor_name}",
            commit=_DUAL_ARTIFACT_COMMIT,
            cache=cache,
        )
    freeze_descriptor = relative_artifact_descriptor(
        registered["dual_coefficient_freeze"], repo_root=repo_root
    )
    _require_git_blob_descriptor(
        commit=_DUAL_ARTIFACT_COMMIT,
        descriptor=freeze_descriptor,
        repo_root=repo_root,
        label="dual-coefficient freeze",
    )

    source_artifacts = _mapping(manifest, "source_artifacts", label="dual-coefficient manifest")
    source_registry = {
        "solve_records": "set_native_phase_a_solve_records",
        "taxonomy": "set_native_phase_a_taxonomy",
        "summary": "set_native_phase_a_summary",
        "manifest": "set_native_phase_a_manifest",
    }
    if set(source_artifacts) != set(source_registry):
        raise RuntimeError("Dual-coefficient predecessor artifact inventory changed.")
    predecessor = _mapping(config, "predecessor", label="dual-coefficient config")
    for source_name, registered_name in source_registry.items():
        descriptor = _require_descriptor_equals_registered(
            source_artifacts.get(source_name),
            registered[registered_name],
            repo_root=repo_root,
            label=f"dual-coefficient predecessor {source_name}",
            commit=_SET_A1_COMMIT,
            cache=cache,
        )
        if predecessor.get(source_name) != descriptor:
            raise RuntimeError(
                f"Dual-coefficient config and manifest disagree on predecessor {source_name}."
            )

    certificates = pd.read_parquet(registered["dual_coefficient_certificates"])
    taxonomy = pd.read_parquet(registered["set_native_phase_a_taxonomy"])
    if not {"window_id", "role", "period"}.issubset(taxonomy.columns):
        raise RuntimeError("Dual-coefficient predecessor taxonomy lacks menu identities.")
    expected_menu_keys = set(
        taxonomy[["window_id", "role", "period"]].itertuples(index=False, name=None)
    )
    if len(taxonomy) != 208 or len(expected_menu_keys) != 208:
        raise RuntimeError("Dual-coefficient predecessor taxonomy is not 208 unique menus.")
    findings = _validate_dual_certificates(
        certificates,
        summary=summary,
        manifest=manifest,
        expected_menu_keys=expected_menu_keys,
    )
    return DualCoefficientEvidence(
        freeze=freeze,
        summary=summary,
        receipt=receipt,
        manifest=manifest,
        certificates=certificates,
        findings=findings,
    )


def load_decision_representation_evidence(
    registered: Mapping[str, Path],
    identities: Mapping[str, Any],
    *,
    repo_root: Path,
) -> DecisionRepresentationEvidence:
    """Verify and load all three active decision-representation audit lineages."""
    root = repo_root.resolve()
    _require_registered_paths(registered, repo_root=root)
    _require_lineages(identities, repo_root=root)
    cache: dict[tuple[str, int, str], Path] = {}
    score = _load_score_equivalence(registered, repo_root=root, cache=cache)
    set_native = _load_set_native(registered, repo_root=root, cache=cache)
    dual = _load_dual_coefficient(registered, repo_root=root, cache=cache)
    return DecisionRepresentationEvidence(
        score_equivalence=score,
        set_native=set_native,
        dual_coefficient=dual,
    )


def score_equivalence_publication_table(evidence: ScoreEquivalenceEvidence) -> pd.DataFrame:
    """Return five disjoint complete-hull score-equivalence census rows."""
    v1d = evidence.v1d
    calibrators = evidence.calibrators
    rows = [
        {
            "family": "v1d_embedding",
            "cell_group": "theta_zero_self",
            "cells": int(v1d["theta"].eq(0.0).sum()),
            "equivalent_cells": int(
                v1d.loc[v1d["theta"].eq(0.0), "equivalent_on_complete_budget_hull"].sum()
            ),
        },
        {
            "family": "v1d_embedding",
            "cell_group": "theta_positive_gamma_zero",
            "cells": int((v1d["theta"].gt(0.0) & v1d["gamma"].eq(0.0)).sum()),
            "equivalent_cells": int(
                v1d.loc[
                    v1d["theta"].gt(0.0) & v1d["gamma"].eq(0.0),
                    "equivalent_on_complete_budget_hull",
                ].sum()
            ),
        },
        {
            "family": "v1d_embedding",
            "cell_group": "theta_positive_gamma_positive",
            "cells": int((v1d["theta"].gt(0.0) & v1d["gamma"].gt(0.0)).sum()),
            "equivalent_cells": int(
                v1d.loc[
                    v1d["theta"].gt(0.0) & v1d["gamma"].gt(0.0),
                    "equivalent_on_complete_budget_hull",
                ].sum()
            ),
        },
        {
            "family": "closed_calibrator_q_gamma",
            "cell_group": "gamma_zero",
            "cells": int(calibrators["gamma"].eq(0.0).sum()),
            "equivalent_cells": int(
                calibrators.loc[
                    calibrators["gamma"].eq(0.0), "equivalent_on_complete_budget_hull"
                ].sum()
            ),
        },
        {
            "family": "closed_calibrator_q_gamma",
            "cell_group": "gamma_positive",
            "cells": int(calibrators["gamma"].gt(0.0).sum()),
            "equivalent_cells": int(
                calibrators.loc[
                    calibrators["gamma"].gt(0.0), "equivalent_on_complete_budget_hull"
                ].sum()
            ),
        },
    ]
    table = pd.DataFrame(rows)
    table["without_complete_hull_certificate"] = table["cells"] - table["equivalent_cells"]
    expected = [
        (1040, 1040, 0),
        (832, 832, 0),
        (3328, 0, 3328),
        (1248, 0, 1248),
        (4992, 0, 4992),
    ]
    observed = list(
        table[["cells", "equivalent_cells", "without_complete_hull_certificate"]].itertuples(
            index=False, name=None
        )
    )
    if observed != expected:
        raise RuntimeError("Score-equivalence publication census changed.")
    return table


def set_native_direction_publication_table(evidence: SetNativeEvidence) -> pd.DataFrame:
    """Return 75 theta-by-gamma-by-metric monthly and pooled sign censuses."""
    rows: list[dict[str, Any]] = []
    for theta in _THETA_GAMMA:
        for gamma in _THETA_GAMMA:
            monthly = evidence.monthly_contrasts.loc[
                evidence.monthly_contrasts["theta"].eq(theta)
                & evidence.monthly_contrasts["gamma"].eq(gamma)
            ]
            pooled = evidence.window_contrasts.loc[
                evidence.window_contrasts["theta"].eq(theta)
                & evidence.window_contrasts["gamma"].eq(gamma)
            ]
            if len(monthly) != 720 or len(pooled) != 48:
                raise RuntimeError("A set-native theta/gamma publication slice is incomplete.")
            for metric, (lower, upper, _) in _METRICS.items():
                monthly_positive = int(monthly[lower].gt(0.0).sum())
                monthly_negative = int(monthly[upper].lt(0.0).sum())
                pooled_positive = int(pooled[lower].gt(0.0).sum())
                pooled_negative = int(pooled[upper].lt(0.0).sum())
                rows.append(
                    {
                        "theta": theta,
                        "gamma": gamma,
                        "metric": metric,
                        "monthly_cells": 720,
                        "monthly_positive": monthly_positive,
                        "monthly_negative": monthly_negative,
                        "monthly_includes_zero": 720 - monthly_positive - monthly_negative,
                        "pooled_cells": 48,
                        "pooled_positive": pooled_positive,
                        "pooled_negative": pooled_negative,
                        "pooled_includes_zero": 48 - pooled_positive - pooled_negative,
                    }
                )
    table = pd.DataFrame(rows)
    if len(table) != 75 or bool(table.duplicated(["theta", "gamma", "metric"]).any()):
        raise RuntimeError("Set-native direction publication table is not 75 unique rows.")
    if not (
        table[["monthly_positive", "monthly_negative", "monthly_includes_zero"]]
        .sum(axis=1)
        .eq(720)
        .all()
        and table[["pooled_positive", "pooled_negative", "pooled_includes_zero"]]
        .sum(axis=1)
        .eq(48)
        .all()
    ):
        raise RuntimeError("Set-native publication sign categories do not partition each slice.")
    return table


def dual_coefficient_publication_table(evidence: DualCoefficientEvidence) -> pd.DataFrame:
    """Return the compact disjoint 88/120 role certificate census."""
    rows: list[dict[str, Any]] = []
    certificates = evidence.certificates
    for role in _ROLES:
        group = certificates.loc[certificates["role"].eq(role)]
        per_window = group.groupby("window_id", observed=True).size()
        if per_window.nunique() != 1:
            raise RuntimeError("Dual-coefficient role menus are not balanced across windows.")
        rows.append(
            {
                "role": role,
                "menu_certificates": int(len(group)),
                "windows": int(group["window_id"].nunique()),
                "months_per_window": int(per_window.iloc[0]),
                "all_conditions_certified": bool(
                    group[list(_DUAL_CONDITION_COLUMNS)].all(axis=None)
                ),
                "all_maximin_optimizers_singleton_zero": bool(
                    group["all_maximin_optimizers_singleton_zero"].all()
                ),
                "continuous_cap_frontier_collapses": bool(
                    group["continuous_cap_frontier_collapses"].all()
                ),
                "cap_domain_lower": float(group["cap_domain_lower"].min()),
                "cap_domain_upper": float(group["cap_domain_upper"].max()),
                "new_optimizations": int(group["new_optimization_executed"].sum()),
                "optimizer_unique_certified": bool(group["optimizer_unique_certified"].any()),
                "validity_claim_established": bool(group["validity_claim_established"].any()),
            }
        )
    table = pd.DataFrame(rows)
    observed = list(
        table[["role", "menu_certificates", "windows", "months_per_window"]].itertuples(
            index=False, name=None
        )
    )
    if observed != [
        ("policy_development", 88, 8, 11),
        ("primary_oot", 120, 8, 15),
    ]:
        raise RuntimeError("Dual-coefficient publication role census changed.")
    if (
        not table["all_conditions_certified"].eq(True).all()
        or not table["all_maximin_optimizers_singleton_zero"].eq(True).all()
        or not table["continuous_cap_frontier_collapses"].eq(True).all()
        or not table["cap_domain_lower"].eq(0.0).all()
        or not table["cap_domain_upper"].eq(1.0).all()
        or not table["new_optimizations"].eq(0).all()
        or table["optimizer_unique_certified"].any()
        or table["validity_claim_established"].any()
    ):
        raise RuntimeError("Dual-coefficient publication boundary changed.")
    return table


__all__ = [
    "DecisionRepresentationEvidence",
    "DualCoefficientEvidence",
    "ScoreEquivalenceEvidence",
    "SetNativeEvidence",
    "dual_coefficient_publication_table",
    "load_decision_representation_evidence",
    "score_equivalence_publication_table",
    "set_native_direction_publication_table",
]
