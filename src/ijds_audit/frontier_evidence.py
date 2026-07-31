"""Verified evidence for the post-inspection IJDS scientific frontiers.

The promoted runs are Git-transported scientific artifacts.  This surface also
supports the larger two-stage set-preserving embedding lineage.  They
remain retrospective finite-archive diagnostics: this loader verifies their
sealed identities, exact censuses, arithmetic contracts, and publication
tables without converting them into sampling, causal, or prospective claims.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from src.ijds_audit.grid_contracts import require_exact_grid, require_finite
from src.utils.artifact_descriptor import (
    relative_artifact_descriptor,
    verified_artifact_path,
)

LEARNERS = (
    "catboost_platt",
    "numeric_logistic_platt",
    "catboost_monotonic_platt",
    "woe_scorecard_platform_platt",
    "woe_scorecard_borrower_platt",
)
LEARNER_LABELS = {
    "catboost_platt": "CatBoost",
    "numeric_logistic_platt": "Numeric logistic",
    "catboost_monotonic_platt": "Monotonic CatBoost",
    "woe_scorecard_platform_platt": "Platform-signal WOE scorecard",
    "woe_scorecard_borrower_platt": "Pricing-excluded application WOE scorecard",
}
WINDOW_IDS = (
    *(f"w{index:02d}_2012m{index:02d}_m{index + 5:02d}" for index in range(1, 8)),
    "w08_2012m08_2013m01",
)
ISSUE_MONTHS = tuple(str(period) for period in pd.period_range("2016-04", "2017-06", freq="M"))
DEVELOPMENT_MONTHS = tuple(
    str(period) for period in pd.period_range("2013-02", "2013-12", freq="M")
)
RULERS = ("objective_matched", "normalized_score")
COORDINATES = (0.25, 0.50, 0.75)
GAMMAS = (0.0, 1.0)
EMBEDDING_LEVELS = (0.0, 0.25, 0.50, 0.75, 1.0)
METRICS = ("payoff_shortfall", "default_gap", "miscoverage_excess")
EMBEDDING_METRICS = ("standardized_payoff", "funded_default", "funded_binary_miscoverage")
EMBEDDING_CONTRAST_FAMILIES = (
    "theta_minus_theta_0_within_gamma",
    "gamma_1_minus_gamma_0_within_theta",
)
RESIDUAL_DIRECTIONS = (
    "larger_target_residual_discrepancy_dominates",
    "smaller_target_residual_discrepancy_dominates",
    "directional_discrepancies_not_robustly_ordered",
)


@dataclass(frozen=True)
class VerifiedFrontierRun:
    """One sealed frontier run and its publication-facing derivatives."""

    config_path: Path
    summary_path: Path
    receipt_path: Path
    protocol_path: Path
    runner_path: Path
    implementation_path: Path
    summary: dict[str, Any]
    receipt: dict[str, Any]
    artifacts: dict[str, Path]
    frames: dict[str, pd.DataFrame]
    publication_tables: dict[str, pd.DataFrame]
    findings: dict[str, Any]


@dataclass(frozen=True)
class FrontierEvidence:
    """All independently gated scientific frontier runs."""

    residual_transport: VerifiedFrontierRun
    marginal_score_outcome_gap: VerifiedFrontierRun
    decision_catalog_transport: VerifiedFrontierRun
    funded_selection_estimands: VerifiedFrontierRun
    set_preserving_embedding: VerifiedFrontierRun


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not all(isinstance(key, str) for key in raw):
        raise TypeError(f"{label} must be a JSON object with string keys.")
    return cast(dict[str, Any], raw)


def _require_identity(
    payload: Mapping[str, Any],
    identity: Mapping[str, Any],
    *,
    label: str,
) -> None:
    for field in ("run_tag", "protocol_tag", "protocol_commit"):
        if payload.get(field) != identity.get(field):
            raise RuntimeError(f"{label} identity changed on {field}.")


def _require_clean_execution(payload: Mapping[str, Any], *, label: str) -> None:
    boundary = payload.get("claim_boundary", {})
    nested = boundary if isinstance(boundary, Mapping) else {}
    stages = payload.get("protected_stages_run", nested.get("protected_stages_run"))
    written = payload.get("protected_artifacts_written", nested.get("protected_artifacts_written"))
    if stages != []:
        raise RuntimeError(f"{label} reports a protected-stage execution.")
    if written != []:
        raise RuntimeError(f"{label} reports a protected-artifact write.")


def _verified_inventory(
    raw: object,
    *,
    expected_names: Sequence[str],
    repo_root: Path,
    label: str,
) -> dict[str, Path]:
    if not isinstance(raw, Mapping) or set(raw) != set(expected_names):
        raise RuntimeError(f"{label} artifact inventory changed.")
    paths: dict[str, Path] = {}
    for name, descriptor in raw.items():
        if not isinstance(name, str) or not isinstance(descriptor, Mapping):
            raise TypeError(f"{label} contains an invalid artifact descriptor.")
        paths[name] = verified_artifact_path(
            cast(Mapping[str, Any], descriptor),
            repo_root=repo_root,
            label=f"{label} {name}",
        )
    return paths


def _require_registered_paths(
    registered: Mapping[str, Path],
    expected: Mapping[str, Path],
    *,
    label: str,
) -> None:
    for name, path in expected.items():
        registered_path = registered.get(name)
        if registered_path is None or registered_path.resolve() != path.resolve():
            raise RuntimeError(f"{label} source registry changed on {name!r}.")


def _require_implementation(
    summary: Mapping[str, Any],
    *,
    container: str,
    required_paths: Sequence[str],
    repo_root: Path,
    label: str,
) -> None:
    implementation = summary.get(container)
    if not isinstance(implementation, Mapping):
        raise TypeError(f"{label} omits implementation provenance.")
    sources = implementation.get("source_files")
    if not isinstance(sources, Mapping):
        raise TypeError(f"{label} implementation provenance omits source files.")
    if not set(required_paths).issubset(sources):
        raise RuntimeError(f"{label} implementation surface is incomplete.")
    for relative in required_paths:
        descriptor = sources[relative]
        if not isinstance(descriptor, Mapping):
            raise TypeError(f"{label} implementation descriptor is invalid: {relative!r}.")
        actual = relative_artifact_descriptor(repo_root / relative, repo_root=repo_root)
        if actual != dict(descriptor):
            raise RuntimeError(f"{label} implementation dependency drifted: {relative!r}.")


def _load_run_contract(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
    *,
    prefix: str,
    expected_summary_status: str,
    expected_artifact_names: Sequence[str],
    implementation_container: str,
    required_implementation: Sequence[str],
    repo_root: Path,
) -> tuple[
    Path,
    Path,
    Path,
    Path,
    Path,
    Path,
    dict[str, Any],
    dict[str, Any],
    dict[str, Path],
]:
    config_path = registered[f"{prefix}_config"]
    summary_path = registered[f"{prefix}_summary"]
    receipt_path = registered[f"{prefix}_receipt"]
    protocol_path = repo_root / required_implementation[1]
    runner_path = repo_root / required_implementation[2]
    implementation_path = repo_root / required_implementation[3]
    summary = _load_json_object(summary_path, label=f"{prefix} summary")
    receipt = _load_json_object(receipt_path, label=f"{prefix} receipt")
    if summary.get("status") != expected_summary_status:
        raise RuntimeError(f"{prefix} summary is not complete.")
    if receipt.get("status") != "complete_calculation_pending_git_artifact_commit":
        raise RuntimeError(f"{prefix} receipt is not complete.")
    _require_identity(summary, lineage, label=f"{prefix} summary")
    _require_identity(receipt, lineage, label=f"{prefix} receipt")
    _require_clean_execution(summary, label=f"{prefix} summary")
    _require_clean_execution(receipt, label=f"{prefix} receipt")
    if receipt.get("summary") != relative_artifact_descriptor(summary_path, repo_root=repo_root):
        raise RuntimeError(f"{prefix} receipt no longer binds its summary.")
    if receipt.get("artifacts") != summary.get("artifacts"):
        raise RuntimeError(f"{prefix} summary and receipt bind different artifacts.")
    summary_transport = summary.get("artifact_transport")
    receipt_transport = receipt.get("artifact_transport")
    if not isinstance(summary_transport, Mapping) or not isinstance(receipt_transport, Mapping):
        raise TypeError(f"{prefix} omits its Git artifact transport contract.")
    expected_paths = tuple(cast(Sequence[str], lineage.get("artifact_paths", ())))
    for transport in (summary_transport, receipt_transport):
        if (
            transport.get("artifact_tag") != lineage.get("artifact_tag")
            or transport.get("artifact_commit_relationship")
            != "single_direct_child_of_protocol_commit"
            or transport.get("pending_at_runner_exit") is not True
            or transport.get("dvc_required") is not False
            or set(cast(Sequence[str], transport.get("exact_tracked_paths", ())))
            != set(expected_paths)
        ):
            raise RuntimeError(f"{prefix} Git artifact transport contract changed.")
    artifacts = _verified_inventory(
        summary.get("artifacts"),
        expected_names=expected_artifact_names,
        repo_root=repo_root,
        label=f"{prefix} scientific artifacts",
    )
    registered_expected = {f"{prefix}_{name}": path for name, path in artifacts.items()} | {
        f"{prefix}_config": config_path,
        f"{prefix}_summary": summary_path,
        f"{prefix}_receipt": receipt_path,
    }
    _require_registered_paths(
        registered,
        registered_expected,
        label=f"{prefix} publication",
    )
    _require_implementation(
        summary,
        container=implementation_container,
        required_paths=required_implementation,
        repo_root=repo_root,
        label=prefix,
    )
    return (
        config_path,
        summary_path,
        receipt_path,
        protocol_path,
        runner_path,
        implementation_path,
        summary,
        receipt,
        artifacts,
    )


def _residual_direction(frame: pd.DataFrame) -> pd.Series:
    larger = frame["calibration_minus_target_ks_min_numerator"].gt(
        frame["target_minus_calibration_ks_max_numerator"]
    )
    smaller = frame["target_minus_calibration_ks_min_numerator"].gt(
        frame["calibration_minus_target_ks_max_numerator"]
    )
    return pd.Series(
        np.select(
            [larger, smaller],
            RESIDUAL_DIRECTIONS[:2],
            default=RESIDUAL_DIRECTIONS[2],
        ),
        index=frame.index,
        dtype="string",
    )


def _load_residual(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
    *,
    repo_root: Path,
) -> VerifiedFrontierRun:
    prefix = "residual_transport_frontier"
    loaded = _load_run_contract(
        registered,
        lineage,
        prefix=prefix,
        expected_summary_status="complete_clean_tagged_calculation_pending_git_artifact_commit_v1",
        expected_artifact_names=(
            "monthly_residual_transport_frontier",
            "pooled_residual_transport_frontier",
        ),
        implementation_container="implementation_provenance",
        required_implementation=(
            "configs/experiments/ijds_residual_transport_frontier_2026-07-29_v1.yaml",
            "docs/research/ijds_residual_transport_frontier_v1_protocol_2026-07-29.md",
            "scripts/experiments/run_ijds_residual_transport_frontier.py",
            "src/ijds_audit/residual_transport_frontier.py",
            "uv.lock",
        ),
        repo_root=repo_root,
    )
    (
        config_path,
        summary_path,
        receipt_path,
        protocol_path,
        runner_path,
        implementation_path,
        summary,
        receipt,
        artifacts,
    ) = loaded
    monthly = pd.read_csv(artifacts["monthly_residual_transport_frontier"])
    pooled = pd.read_csv(artifacts["pooled_residual_transport_frontier"])
    require_exact_grid(
        monthly,
        domains={
            "learner": LEARNERS,
            "window_id": WINDOW_IDS,
            "score_stratum": (1, 2, 3, 4, 5),
            "issue_month": ISSUE_MONTHS,
        },
        label="monthly residual-transport frontier",
    )
    require_exact_grid(
        pooled,
        domains={
            "learner": LEARNERS,
            "window_id": WINDOW_IDS,
            "score_stratum": (1, 2, 3, 4, 5),
        },
        label="pooled residual-transport frontier",
    )
    numeric = (
        "target_rows",
        "resolved_rows",
        "unresolved_rows",
        "calibration_minus_target_ks_min",
        "calibration_minus_target_ks_max",
        "target_minus_calibration_ks_min",
        "target_minus_calibration_ks_max",
        "completion_directional_ks_denominator",
    )
    require_finite(monthly, numeric, label="monthly residual-transport frontier")
    require_finite(pooled, numeric, label="pooled residual-transport frontier")
    for frame, label in ((monthly, "monthly"), (pooled, "pooled")):
        if (
            not frame["role"].eq("primary_oot").all()
            or not frame["taxonomy_groups"].eq(5).all()
            or not frame["conformal_group"].eq(frame["score_stratum"] - 1).all()
            or not frame["calibration_minus_target_ks_min"]
            .le(frame["calibration_minus_target_ks_max"])
            .all()
            or not frame["target_minus_calibration_ks_min"]
            .le(frame["target_minus_calibration_ks_max"])
            .all()
            or not frame["sharp_directional_discrepancy_comparison"]
            .astype("string")
            .eq(_residual_direction(frame))
            .all()
        ):
            raise RuntimeError(f"The {label} residual frontier contract changed.")
    if not pooled["v5_q_and_coverage_reconciled"].astype(bool).all():
        raise RuntimeError("The pooled residual frontier no longer reconciles active V5.")
    grouping = ["learner", "window_id", "score_stratum"]
    summed = monthly.groupby(grouping, sort=True, observed=True)[
        ["target_rows", "resolved_rows", "unresolved_rows", "misses_min", "misses_max"]
    ].sum()
    pooled_counts = pooled.set_index(grouping)[
        ["target_rows", "resolved_rows", "unresolved_rows", "misses_min", "misses_max"]
    ].sort_index()
    if not summed.sort_index().equals(pooled_counts):
        raise RuntimeError("Monthly residual counts no longer sum to the pooled frontier.")
    monthly_counts = monthly["sharp_directional_discrepancy_comparison"].value_counts()
    pooled_counts_direction = pooled["sharp_directional_discrepancy_comparison"].value_counts()
    expected_monthly = {
        RESIDUAL_DIRECTIONS[0]: 2140,
        RESIDUAL_DIRECTIONS[1]: 488,
        RESIDUAL_DIRECTIONS[2]: 372,
    }
    expected_pooled = {
        RESIDUAL_DIRECTIONS[0]: 158,
        RESIDUAL_DIRECTIONS[1]: 8,
        RESIDUAL_DIRECTIONS[2]: 34,
    }
    if (
        monthly_counts.to_dict() != expected_monthly
        or pooled_counts_direction.to_dict() != expected_pooled
    ):
        raise RuntimeError("The residual directional frontier census changed.")
    descriptive = cast(Mapping[str, Any], summary.get("descriptive_ranges", {}))
    if (
        descriptive.get("monthly_sharp_directional_discrepancy_counts") != expected_monthly
        or descriptive.get("pooled_sharp_directional_discrepancy_counts") != expected_pooled
        or summary.get("census", {}).get("monthly_rows") != 3000
        or summary.get("census", {}).get("pooled_rows") != 200
    ):
        raise RuntimeError("The residual summary no longer reconciles its full census.")
    summary_counts = cast(
        pd.DataFrame,
        pooled.groupby("learner", sort=False, observed=True)[
            "sharp_directional_discrepancy_comparison"
        ]
        .value_counts()
        .unstack(fill_value=0),
    )
    summary_table = summary_counts.reindex(
        index=LEARNERS, columns=RESIDUAL_DIRECTIONS, fill_value=0
    ).reset_index()
    summary_table.insert(1, "learner_label", summary_table["learner"].map(LEARNER_LABELS))
    summary_table.insert(2, "pooled_cells", 40)
    pooled_publication = pooled[
        [
            "learner",
            "window_id",
            "score_stratum",
            "fit_rows",
            "target_rows",
            "resolved_rows",
            "unresolved_rows",
            "completion_directional_ks_denominator",
            "calibration_minus_target_ks_min",
            "calibration_minus_target_ks_max",
            "target_minus_calibration_ks_min",
            "target_minus_calibration_ks_max",
            "calibration_minus_target_ks_min_numerator",
            "calibration_minus_target_ks_max_numerator",
            "target_minus_calibration_ks_min_numerator",
            "target_minus_calibration_ks_max_numerator",
            "sharp_directional_discrepancy_comparison",
            "v5_q_and_coverage_reconciled",
        ]
    ].copy()
    pooled_publication.insert(1, "learner_label", pooled_publication["learner"].map(LEARNER_LABELS))
    findings = {
        "full_pooled_census_and_sharp_frontier_verified": True,
        "monthly_cells": 3000,
        "pooled_cells": 200,
        "monthly_direction_census": expected_monthly,
        "pooled_direction_census": expected_pooled,
        "cellwise_sharp_not_joint_stochastic_order": True,
        "p_values_computed": False,
    }
    return VerifiedFrontierRun(
        config_path,
        summary_path,
        receipt_path,
        protocol_path,
        runner_path,
        implementation_path,
        summary,
        receipt,
        artifacts,
        {"monthly": monthly, "pooled": pooled},
        {"summary": summary_table, "pooled": pooled_publication},
        findings,
    )


def _load_marginal(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
    *,
    repo_root: Path,
) -> VerifiedFrontierRun:
    prefix = "marginal_score_outcome_gap"
    loaded = _load_run_contract(
        registered,
        lineage,
        prefix=prefix,
        expected_summary_status="complete_clean_tagged_calculation_pending_git_artifact_commit_v3i",
        expected_artifact_names=(
            "table",
            "endpoint_reason_census",
            "monthly_endpoint_reason_census",
        ),
        implementation_container="implementation",
        required_implementation=(
            "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-29_v3i.yaml",
            "docs/research/ijds_marginal_mean_score_outcome_gap_v3i_protocol_2026-07-29.md",
            "scripts/experiments/run_ijds_marginal_mean_score_outcome_gap_v3i.py",
            "src/ijds_audit/marginal_mean_score_outcome_gap_v3i.py",
            "uv.lock",
        ),
        repo_root=repo_root,
    )
    (
        config_path,
        summary_path,
        receipt_path,
        protocol_path,
        runner_path,
        implementation_path,
        summary,
        receipt,
        artifacts,
    ) = loaded
    table = pd.read_csv(artifacts["table"])
    reasons = pd.read_csv(artifacts["endpoint_reason_census"])
    monthly_reasons = pd.read_csv(artifacts["monthly_endpoint_reason_census"])
    require_exact_grid(table, domains={"learner": LEARNERS}, label="marginal score-outcome gap")
    reason_names = tuple(str(value) for value in reasons["snapshot_resolution"].tolist())
    require_exact_grid(
        reasons,
        domains={"snapshot_resolution": reason_names},
        label="marginal endpoint-reason census",
    )
    require_exact_grid(
        monthly_reasons,
        domains={"period": ISSUE_MONTHS, "snapshot_resolution": reason_names},
        label="monthly marginal endpoint-reason census",
    )
    require_finite(
        table,
        (
            "mean_score",
            "outcome_mean_lower",
            "outcome_mean_upper",
            "marginal_mean_score_outcome_gap_lower",
            "marginal_mean_score_outcome_gap_upper",
            "identification_width",
        ),
        label="marginal score-outcome gap",
    )
    if (
        tuple(table.sort_values("learner_order")["learner"].astype(str)) != LEARNERS
        or not table["candidate_rows"].eq(376890).all()
        or not table["resolved_rows"].eq(364814).all()
        or not table["unresolved_outcomes"].eq(12076).all()
        or not table["reported_interval_is_identified_set_hull"].astype(bool).all()
        or not table["sharp_binary_completion"].astype(bool).all()
        or not table["joint_endpoint_attainment"].astype(bool).all()
        or not table["marginal_mean_score_outcome_gap_upper"].lt(0.0).all()
        or not np.allclose(
            table["mean_score"] - table["outcome_mean_upper"],
            table["marginal_mean_score_outcome_gap_lower"],
            rtol=0.0,
            atol=1e-15,
        )
        or not np.allclose(
            table["mean_score"] - table["outcome_mean_lower"],
            table["marginal_mean_score_outcome_gap_upper"],
            rtol=0.0,
            atol=1e-15,
        )
    ):
        raise RuntimeError("The marginal score-outcome identification contract changed.")
    monthly_totals = monthly_reasons.groupby("snapshot_resolution", sort=False)[
        ["candidate_rows", "resolved_rows", "unresolved_rows"]
    ].sum()
    reason_totals = reasons.set_index("snapshot_resolution")[
        ["candidate_rows", "resolved_rows", "unresolved_rows"]
    ]
    if not monthly_totals.sort_index().equals(reason_totals.sort_index()):
        raise RuntimeError("Monthly endpoint reasons no longer reconcile the marginal census.")
    identification = cast(Mapping[str, Any], summary.get("identification", {}))
    outcome_interval = [
        float(table["outcome_mean_lower"].iloc[0]),
        float(table["outcome_mean_upper"].iloc[0]),
    ]
    if (
        not np.allclose(
            cast(Sequence[float], identification.get("outcome_mean_interval", ())),
            outcome_interval,
            rtol=0.0,
            atol=1e-15,
        )
        or summary.get("results", {}).get("learners") != 5
        or summary.get("v3h_arithmetic_reconciliation", {}).get("all_five_rows_reconciled")
        is not True
        or receipt.get("dvc_commands_run") != []
    ):
        raise RuntimeError("The marginal summary or clean transport reconciliation changed.")
    publication = table[
        [
            "learner_order",
            "learner",
            "candidate_rows",
            "resolved_rows",
            "unresolved_outcomes",
            "mean_score",
            "outcome_mean_lower",
            "outcome_mean_upper",
            "marginal_mean_score_outcome_gap_lower",
            "marginal_mean_score_outcome_gap_upper",
            "identification_width",
            "identified_grid_points",
            "identified_grid_step",
            "joint_endpoint_attainment",
        ]
    ].copy()
    publication.insert(2, "learner_label", publication["learner"].map(LEARNER_LABELS))
    findings = {
        "all_five_gap_upper_endpoints_negative": True,
        "outcome_prevalence_sharp_interval": outcome_interval,
        "least_negative_gap_upper_endpoint": float(
            table["marginal_mean_score_outcome_gap_upper"].max()
        ),
        "shared_collinear_completion_grid_not_cartesian_product": True,
        "individual_or_conditional_calibration_claimed": False,
    }
    return VerifiedFrontierRun(
        config_path,
        summary_path,
        receipt_path,
        protocol_path,
        runner_path,
        implementation_path,
        summary,
        receipt,
        artifacts,
        {"table": table, "endpoint_reasons": reasons, "monthly_endpoint_reasons": monthly_reasons},
        {"gap": publication},
        findings,
    )


def _load_decision(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
    *,
    repo_root: Path,
) -> VerifiedFrontierRun:
    prefix = "decision_catalog_transport"
    loaded = _load_run_contract(
        registered,
        lineage,
        prefix=prefix,
        expected_summary_status="complete_clean_tagged_calculation_pending_git_artifact_commit_v1",
        expected_artifact_names=(
            "policy_score_bounds",
            "block_score_bounds",
            "calibration_thresholds",
            "target_classification",
        ),
        implementation_container="implementation_provenance",
        required_implementation=(
            "configs/experiments/ijds_decision_catalog_transport_2026-07-29_v1.yaml",
            "docs/research/ijds_decision_catalog_transport_v1_protocol_2026-07-29.md",
            "scripts/experiments/run_ijds_decision_catalog_transport_v1.py",
            "src/ijds_audit/decision_catalog_transport.py",
        ),
        repo_root=repo_root,
    )
    (
        config_path,
        summary_path,
        receipt_path,
        protocol_path,
        runner_path,
        implementation_path,
        summary,
        receipt,
        artifacts,
    ) = loaded
    frames = {name: pd.read_csv(path) for name, path in artifacts.items()}
    policy = frames["policy_score_bounds"]
    blocks = frames["block_score_bounds"]
    thresholds = frames["calibration_thresholds"]
    targets = frames["target_classification"]
    policy_axes = {
        "window_id": WINDOW_IDS,
        "frontier_ruler": RULERS,
        "frontier_coordinate": COORDINATES,
        "gamma": (0.0, 0.25, 0.5, 0.75, 1.0),
        "metric": METRICS,
    }
    require_exact_grid(
        policy.loc[policy["role"].eq("policy_development")],
        domains={"period": DEVELOPMENT_MONTHS, **policy_axes},
        label="development decision catalog policy scores",
    )
    require_exact_grid(
        policy.loc[policy["role"].eq("primary_oot")],
        domains={"period": ISSUE_MONTHS, **policy_axes},
        label="target decision catalog policy scores",
    )
    require_exact_grid(
        blocks.loc[blocks["role"].eq("policy_development")],
        domains={"period": DEVELOPMENT_MONTHS, "metric": METRICS},
        label="development decision catalog block scores",
    )
    require_exact_grid(
        blocks.loc[blocks["role"].eq("primary_oot")],
        domains={"period": ISSUE_MONTHS, "metric": METRICS},
        label="target decision catalog block scores",
    )
    require_exact_grid(thresholds, domains={"metric": METRICS}, label="decision thresholds")
    require_exact_grid(
        targets,
        domains={"period": ISSUE_MONTHS, "metric": METRICS},
        label="decision target classification",
    )
    require_finite(
        policy,
        ("score_lower", "score_upper", "raw_gap_lower", "raw_gap_upper"),
        label="decision catalog policy scores",
    )
    if (
        len(policy) != 18720
        or len(blocks) != 78
        or len(thresholds) != 3
        or len(targets) != 45
        or not policy["score_lower"].le(policy["score_upper"]).all()
        or not targets["classification"].eq("definitely_exceeds").all()
        or not targets["exceeds_all_development_upper"].astype(bool).all()
        or not targets["score_lower"].gt(targets["development_max_upper"]).all()
        or summary.get("post_inspection_disclosure", {}).get(
            "joint_three_metric_ordering_probability_reported"
        )
        is not False
    ):
        raise RuntimeError("The complete decision-catalog transport contract changed.")
    metric_summary = (
        targets.groupby("metric", sort=False, observed=True)
        .agg(
            target_blocks=("period", "nunique"),
            minimum_target_lower=("score_lower", "min"),
            development_maximum_upper=("development_max_upper", "max"),
            all_target_blocks_exceed_development=("exceeds_all_development_upper", "all"),
        )
        .reindex(METRICS)
        .reset_index()
    )
    metric_summary["minimum_separation_margin"] = (
        metric_summary["minimum_target_lower"] - metric_summary["development_maximum_upper"]
    )
    expected_margins = {
        "payoff_shortfall": 0.014412526678490106,
        "default_gap": 0.009545127375628987,
        "miscoverage_excess": 0.006825000000000581,
    }
    observed_margins = metric_summary.set_index("metric")["minimum_separation_margin"]
    if not all(
        np.isclose(observed_margins.loc[name], value, rtol=0.0, atol=1e-12)
        for name, value in expected_margins.items()
    ):
        raise RuntimeError("The decision-catalog minimum separation margins changed.")
    target_publication = targets[
        [
            "period",
            "metric",
            "score_lower",
            "score_upper",
            "policies",
            "development_max_upper",
            "classification",
            "exceeds_all_development_upper",
        ]
    ].copy()
    findings = {
        "all_three_metrics_all_fifteen_target_lower_exceed_all_development_upper": True,
        "target_metric_blocks": 45,
        "policies_per_block": 240,
        "minimum_separation_margins": expected_margins,
        "object_is_worst_catalog_maximum_not_every_policy": True,
        "ordering_probability_reported": False,
    }
    return VerifiedFrontierRun(
        config_path,
        summary_path,
        receipt_path,
        protocol_path,
        runner_path,
        implementation_path,
        summary,
        receipt,
        artifacts,
        frames,
        {"metric_separation": metric_summary, "target_blocks": target_publication},
        findings,
    )


def _load_funded(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
    *,
    repo_root: Path,
) -> VerifiedFrontierRun:
    prefix = "funded_selection_estimands"
    loaded = _load_run_contract(
        registered,
        lineage,
        prefix=prefix,
        expected_summary_status="complete_clean_tagged_calculation_pending_git_artifact_commit_v1",
        expected_artifact_names=(
            "monthly_bounds",
            "track_bounds",
            "monthly_gamma_contrasts",
            "track_gamma_contrasts",
            "support_and_fixed_capital_reconciliation",
        ),
        implementation_container="implementation",
        required_implementation=(
            "configs/experiments/ijds_funded_selection_estimand_audit_2026-07-29_v1.yaml",
            "docs/research/ijds_funded_selection_estimand_audit_v1_protocol_2026-07-29.md",
            "scripts/experiments/run_ijds_funded_selection_estimand_audit_v1.py",
            "src/ijds_audit/funded_selection_estimand.py",
            "uv.lock",
        ),
        repo_root=repo_root,
    )
    (
        config_path,
        summary_path,
        receipt_path,
        protocol_path,
        runner_path,
        implementation_path,
        summary,
        receipt,
        artifacts,
    ) = loaded
    frames = {name: pd.read_parquet(path) for name, path in artifacts.items()}
    monthly = frames["monthly_bounds"]
    tracks = frames["track_bounds"]
    monthly_gamma = frames["monthly_gamma_contrasts"]
    track_gamma = frames["track_gamma_contrasts"]
    reconciliation = frames["support_and_fixed_capital_reconciliation"]
    track_axes = {
        "window_id": WINDOW_IDS,
        "frontier_ruler": RULERS,
        "frontier_coordinate": COORDINATES,
        "gamma": GAMMAS,
    }
    require_exact_grid(
        monthly,
        domains={**track_axes, "period": ISSUE_MONTHS},
        label="monthly funded-selection estimands",
    )
    require_exact_grid(tracks, domains=track_axes, label="pooled funded-selection estimands")
    gamma_axes = {
        "window_id": WINDOW_IDS,
        "frontier_ruler": RULERS,
        "frontier_coordinate": COORDINATES,
    }
    require_exact_grid(
        monthly_gamma,
        domains={**gamma_axes, "period": ISSUE_MONTHS},
        label="monthly funded gamma contrasts",
    )
    require_exact_grid(track_gamma, domains=gamma_axes, label="pooled funded gamma contrasts")
    require_exact_grid(reconciliation, domains=track_axes, label="funded V3 reconciliation")
    gap_columns = (
        "count_selected_minus_invested_dollar_selected_coverage_lower",
        "count_selected_minus_invested_dollar_selected_coverage_upper",
        "count_selected_minus_fixed_capital_decision_coverage_lower",
        "count_selected_minus_fixed_capital_decision_coverage_upper",
    )
    require_finite(tracks, gap_columns, label="pooled funded-selection estimands")
    count_gap = "count_selected_minus_invested_dollar_selected_coverage_lower"
    fixed_gap = "count_selected_minus_fixed_capital_decision_coverage_lower"
    if (
        len(monthly) != 1440
        or len(tracks) != 96
        or len(monthly_gamma) != 720
        or len(track_gamma) != 48
        or len(reconciliation) != 96
        or not tracks[count_gap].gt(0.0).all()
        or not tracks[fixed_gap].gt(0.0).all()
        or not tracks["sharpness"].eq("cellwise_shared_binary_completion").all()
        or not tracks["periods"].eq(15).all()
        or int(tracks["count_selected_coverage_upper"].lt(0.90).sum()) != 80
        or int(tracks["count_selected_coverage_lower"].lt(0.90).sum()) != 96
        or not reconciliation["exact_within_locked_tolerance"].astype(bool).all()
    ):
        raise RuntimeError("The funded-selection estimand census or sharp gap changed.")
    direction_columns = {
        "count_selected": "gamma1_minus_gamma0_count_selected_fcp_direction",
        "invested_dollar_selected": ("gamma1_minus_gamma0_invested_dollar_selected_fcp_direction"),
        "fixed_capital_decision": ("gamma1_minus_gamma0_fixed_capital_decision_fcp_direction"),
    }
    direction_census = {
        name: track_gamma[column].value_counts().sort_index().to_dict()
        for name, column in direction_columns.items()
    }
    expected_direction_census = {
        "count_selected": {"higher": 40, "lower": 8},
        "invested_dollar_selected": {"crossing": 8, "higher": 40},
        "fixed_capital_decision": {"crossing": 8, "higher": 40},
    }
    results = cast(Mapping[str, Any], summary.get("results", {}))
    if (
        direction_census != expected_direction_census
        or not np.isclose(float(tracks[count_gap].min()), 0.008536795630709675, atol=1e-15)
        or not np.isclose(float(tracks[fixed_gap].min()), 0.008534305110113329, atol=1e-15)
        or results.get("count_selected_upper_below_point90_tracks") != 80
        or results.get("count_selected_lower_below_point90_tracks") != 96
        or float(results.get("v3_fixed_capital_reconciliation_maximum_absolute_difference", 1.0))
        > 1e-18
    ):
        raise RuntimeError("The funded-selection summary or gamma census changed.")
    track_publication = tracks.copy()
    gamma_publication = track_gamma.copy()
    findings = {
        "all_ninety_six_count_minus_invested_dollar_coverage_lower_endpoints_positive": True,
        "all_ninety_six_count_minus_fixed_capital_coverage_lower_endpoints_positive": True,
        "minimum_count_minus_invested_dollar_coverage_lower": float(tracks[count_gap].min()),
        "minimum_count_minus_fixed_capital_coverage_lower": float(tracks[fixed_gap].min()),
        "count_selected_upper_below_point90_tracks": 80,
        "count_selected_lower_below_point90_tracks": 96,
        "gamma_direction_census": expected_direction_census,
        "cellwise_not_joint_across_tracks": True,
        "selected_set_or_fcr_validity_claimed": False,
    }
    return VerifiedFrontierRun(
        config_path,
        summary_path,
        receipt_path,
        protocol_path,
        runner_path,
        implementation_path,
        summary,
        receipt,
        artifacts,
        frames,
        {"track_estimands": track_publication, "gamma_contrasts": gamma_publication},
        findings,
    )


def _require_embedding_schema(
    frame: pd.DataFrame,
    schema: Mapping[str, Any],
    *,
    name: str,
) -> None:
    """Validate the V1d persisted schema and its sole structural NA pattern."""
    dtypes = schema.get("dtypes")
    if not isinstance(dtypes, Mapping):
        raise TypeError(f"Set-preserving embedding schema {name!r} omits dtypes.")
    expected_columns = tuple(str(column) for column in dtypes)
    actual_dtypes = {column: str(frame[column].dtype) for column in frame.columns}
    if (
        schema.get("rows") != len(frame)
        or schema.get("columns") != len(frame.columns)
        or tuple(frame.columns) != expected_columns
        or actual_dtypes != dict(dtypes)
    ):
        raise RuntimeError(f"Set-preserving embedding persisted schema {name!r} changed.")

    structural = (
        {"frontier_cap", "objective_target", "risk_tolerance"}
        if name == ("evaluated_portfolios")
        else set()
    )
    ordinary = [column for column in frame.columns if column not in structural]
    if bool(frame.loc[:, ordinary].isna().any().any()):
        raise RuntimeError(f"Set-preserving embedding table {name!r} has undeclared missingness.")
    for column in structural:
        expected_missing = (
            frame["frontier_ruler"].eq("objective_matched")
            if column in {"frontier_cap", "risk_tolerance"}
            else frame["frontier_ruler"].eq("normalized_score")
        )
        if int(frame[column].isna().sum()) != 9000 or not frame[column].isna().equals(
            expected_missing
        ):
            raise RuntimeError(
                f"Set-preserving embedding structural missingness changed for {column!r}."
            )

    for column in frame.select_dtypes(include=[np.number]).columns:
        values = frame[column].dropna().to_numpy()
        if not bool(np.isfinite(values).all()):
            raise RuntimeError(
                f"Set-preserving embedding table {name!r} contains nonfinite {column!r}."
            )


def _require_embedding_grid(frames: Mapping[str, pd.DataFrame]) -> None:
    evaluated = frames["evaluated_portfolios"]
    base_axes = {
        "window_id": WINDOW_IDS,
        "period": ISSUE_MONTHS,
        "frontier_ruler": RULERS,
        "frontier_coordinate": COORDINATES,
        "theta": EMBEDDING_LEVELS,
        "gamma": EMBEDDING_LEVELS,
    }
    require_exact_grid(evaluated, domains=base_axes, label="set-preserving evaluated portfolios")
    if (
        not evaluated["role"].eq("primary_oot").all()
        or not evaluated["full_budget"].astype(bool).all()
        or "realized_payoff_exact" in evaluated
    ):
        raise RuntimeError("The set-preserving evaluated-portfolio contract changed.")

    axes = {
        "window_id": WINDOW_IDS,
        "ruler": RULERS,
        "coordinate": COORDINATES,
    }
    for name in ("monthly_sharp_contrasts", "window_sharp_contrasts"):
        frame = frames[name]
        gamma = frame.loc[frame["contrast_family"].eq(EMBEDDING_CONTRAST_FAMILIES[1])]
        theta = frame.loc[frame["contrast_family"].eq(EMBEDDING_CONTRAST_FAMILIES[0])]
        period_axis: dict[str, Sequence[Any]] = (
            {"period": ISSUE_MONTHS} if name == "monthly_sharp_contrasts" else {}
        )
        require_exact_grid(
            gamma,
            domains={**axes, **period_axis, "theta": EMBEDDING_LEVELS},
            label=f"{name} gamma contrasts",
        )
        require_exact_grid(
            theta,
            domains={
                **axes,
                **period_axis,
                "theta": EMBEDDING_LEVELS[1:],
                "gamma": EMBEDDING_LEVELS,
            },
            label=f"{name} theta contrasts",
        )
        if (
            not frame["role"].eq("primary_oot").all()
            or frame["causal_interpretation"].astype(bool).any()
            or not gamma["gamma"].eq(1.0).all()
            or not gamma["gamma_reference"].eq(0.0).all()
            or not gamma["theta_reference"].eq(gamma["theta"]).all()
            or not theta["theta_reference"].eq(0.0).all()
            or not theta["gamma_reference"].eq(theta["gamma"]).all()
        ):
            raise RuntimeError(f"The set-preserving {name} contrast semantics changed.")

    directions = frames["direction_census"]
    gamma_directions = directions.loc[
        directions["contrast_family"].eq(EMBEDDING_CONTRAST_FAMILIES[1])
    ]
    theta_directions = directions.loc[
        directions["contrast_family"].eq(EMBEDDING_CONTRAST_FAMILIES[0])
    ]
    require_exact_grid(
        gamma_directions,
        domains={**axes, "theta": EMBEDDING_LEVELS, "metric": EMBEDDING_METRICS},
        label="set-preserving gamma direction census",
    )
    require_exact_grid(
        theta_directions,
        domains={
            **axes,
            "theta": EMBEDDING_LEVELS[1:],
            "gamma": EMBEDDING_LEVELS,
            "metric": EMBEDDING_METRICS,
        },
        label="set-preserving theta direction census",
    )
    allowed_geometric = {"negative", "positive", "contains_zero", "exact_zero"}
    allowed_tolerance = {
        "negative",
        "positive",
        "not_directionally_separated_at_tolerance",
        "within_tolerance",
    }
    if (
        set(directions["geometric_direction"].astype(str)) != allowed_geometric
        or set(directions["direction_at_tolerance"].astype(str)) != allowed_tolerance
    ):
        raise RuntimeError("The set-preserving direction taxonomy changed.")

    audit = frames["outcome_audit"]
    require_exact_grid(audit, domains={"period": ISSUE_MONTHS}, label="embedding outcome audit")
    if (
        not audit["role"].eq("primary_oot").all()
        or int(audit["candidate_rows"].sum()) != 376890
        or int(audit["unresolved_rows"].sum()) != 12076
        or int(audit["funded_allocation_rows"].sum()) != 1783274
        or not audit["policies"].eq(150).all()
    ):
        raise RuntimeError("The set-preserving outcome-join audit changed.")


def _embedding_direction_table(directions: pd.DataFrame) -> pd.DataFrame:
    expected = {
        ("theta_minus_theta_0_within_gamma", "standardized_payoff"): (768, 128, 338, 230, 72),
        ("theta_minus_theta_0_within_gamma", "funded_default"): (768, 350, 157, 173, 88),
        ("theta_minus_theta_0_within_gamma", "funded_binary_miscoverage"): (
            768,
            340,
            259,
            81,
            88,
        ),
        ("gamma_1_minus_gamma_0_within_theta", "standardized_payoff"): (240, 149, 0, 74, 17),
        ("gamma_1_minus_gamma_0_within_theta", "funded_default"): (240, 0, 153, 70, 17),
        ("gamma_1_minus_gamma_0_within_theta", "funded_binary_miscoverage"): (
            240,
            0,
            191,
            32,
            17,
        ),
    }
    rows: list[dict[str, Any]] = []
    for family in EMBEDDING_CONTRAST_FAMILIES:
        for metric in EMBEDDING_METRICS:
            subset = directions.loc[
                directions["contrast_family"].eq(family) & directions["metric"].eq(metric)
            ]
            if family == EMBEDDING_CONTRAST_FAMILIES[0]:
                subset = subset.loc[subset["gamma"].gt(0.0)]
            counts = subset["direction_at_tolerance"].value_counts().to_dict()
            observed = (
                len(subset),
                int(counts.get("negative", 0)),
                int(counts.get("positive", 0)),
                int(counts.get("not_directionally_separated_at_tolerance", 0)),
                int(counts.get("within_tolerance", 0)),
            )
            if observed != expected[(family, metric)]:
                raise RuntimeError(
                    "The set-preserving embedding direction-at-tolerance census changed."
                )
            rows.append(
                {
                    "contrast_family": family,
                    "metric": metric,
                    "cells": observed[0],
                    "negative": observed[1],
                    "positive": observed[2],
                    "not_directionally_separated_at_tolerance": observed[3],
                    "within_tolerance": observed[4],
                }
            )
    return pd.DataFrame(rows)


def _load_embedding(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
    *,
    repo_root: Path,
) -> VerifiedFrontierRun:
    prefix = "set_preserving_embedding"
    config_path = registered[f"{prefix}_config"]
    summary_path = registered[f"{prefix}_evaluation_summary"]
    receipt_path = registered[f"{prefix}_evaluation_receipt"]
    manifest_path = registered[f"{prefix}_manifest"]
    protocol_path = registered[f"{prefix}_protocol"]
    runner_path = registered[f"{prefix}_runner"]
    implementation_path = registered[f"{prefix}_implementation"]
    summary = _load_json_object(summary_path, label="set-preserving embedding summary")
    receipt = _load_json_object(receipt_path, label="set-preserving embedding receipt")
    manifest = _load_json_object(manifest_path, label="set-preserving embedding manifest")
    status = "retrospective_post_inspection_v1d_phase_b_complete_not_confirmatory"
    for label, payload in (("summary", summary), ("receipt", receipt), ("manifest", manifest)):
        if payload.get("status") != status:
            raise RuntimeError(f"Set-preserving embedding {label} is not complete.")
        if label == "manifest":
            if payload.get("run_tag") != lineage.get("run_tag"):
                raise RuntimeError("Set-preserving embedding manifest run identity changed.")
        else:
            _require_identity(payload, lineage, label=f"set-preserving embedding {label}")
        _require_clean_execution(payload, label=f"set-preserving embedding {label}")
        if payload.get("artifact_status") != "pending_git_artifact_commit_and_annotated_tag":
            raise RuntimeError(f"Set-preserving embedding {label} artifact boundary changed.")

    source_names = {
        "solve_records": "frontier_solve_records",
        "allocations": "frontier_funded_allocations",
        "embedding_diagnostics": "embedding_set_preservation",
        "minimum_endpoint_diagnostics": "minimum_endpoint_diagnostics",
        "objective_optimum_diagnostics": "objective_optimum_diagnostics",
        "allocation_contrasts": "outcome_free_allocation_contrasts",
        "order_sensitivity": "frontier_order_sensitivity",
        "independent_validation": "frontier_independent_solver_validation",
        "freeze": "protocol_freeze",
        "summary": "outcome_free_summary",
        "receipt": "outcome_free_receipt",
    }
    evaluation_names = {
        "evaluated_portfolios": "evaluated_portfolios",
        "evaluation_receipt": "evaluation_receipt",
        "evaluation_summary": "evaluation_summary",
        "join_identity": "join_identity",
        "metric_direction_census": "direction_census",
        "monthly_sharp_contrasts": "monthly_contrasts",
        "outcome_join_audit": "outcome_audit",
        "window_sharp_contrasts": "window_contrasts",
    }
    source_artifacts = _verified_inventory(
        manifest.get("source_v1a_artifacts"),
        expected_names=tuple(source_names),
        repo_root=repo_root,
        label="set-preserving Phase-A artifacts",
    )
    evaluation_artifacts = _verified_inventory(
        manifest.get("evaluation_artifacts"),
        expected_names=tuple(evaluation_names),
        repo_root=repo_root,
        label="set-preserving V1d artifacts",
    )
    expected_registered = (
        {
            f"{prefix}_{registered_name}": source_artifacts[manifest_name]
            for manifest_name, registered_name in source_names.items()
        }
        | {
            f"{prefix}_{registered_name}": evaluation_artifacts[manifest_name]
            for manifest_name, registered_name in evaluation_names.items()
        }
        | {f"{prefix}_manifest": manifest_path}
    )
    _require_registered_paths(registered, expected_registered, label="set-preserving embedding")

    protocol_identity = manifest.get("protocol")
    source_identity = manifest.get("source_artifact")
    contract = manifest.get("artifact_contract")
    if (
        not isinstance(protocol_identity, Mapping)
        or not isinstance(source_identity, Mapping)
        or not isinstance(contract, Mapping)
    ):
        raise TypeError("Set-preserving embedding manifest omits Git identities.")
    if (
        protocol_identity.get("tag") != lineage.get("protocol_tag")
        or protocol_identity.get("commit") != lineage.get("protocol_commit")
        or source_identity.get("tag") != lineage.get("source_artifact_tag")
        or source_identity.get("commit") != lineage.get("source_artifact_commit")
        or contract.get("expected_tag") != lineage.get("artifact_tag")
        or contract.get("expected_parent") != lineage.get("artifact_parent_commit")
        or set(cast(Sequence[str], contract.get("exact_added_paths", ())))
        != set(cast(Sequence[str], lineage.get("artifact_paths", ())))
        or contract.get("direct_child_required") is not True
        or contract.get("annotated_tag_required") is not True
        or contract.get("dvc_required") is not False
    ):
        raise RuntimeError("The set-preserving embedding Git artifact contract changed.")

    implementation = manifest.get("implementation")
    if not isinstance(implementation, Mapping) or len(implementation) != 20:
        raise RuntimeError("Set-preserving embedding implementation inventory changed.")
    for relative, descriptor in implementation.items():
        if not isinstance(relative, str) or not isinstance(descriptor, Mapping):
            raise TypeError("Set-preserving embedding implementation descriptor is invalid.")
        if relative_artifact_descriptor(repo_root / relative, repo_root=repo_root) != dict(
            descriptor
        ):
            raise RuntimeError(f"Set-preserving embedding implementation drifted: {relative!r}.")
    for registered_name, relative in {
        "config": "configs/experiments/ijds_set_preserving_embedding_sensitivity_2026-07-30_v1d.yaml",
        "base_config": "configs/experiments/ijds_set_preserving_embedding_sensitivity_2026-07-29_v1c.yaml",
        "protocol": "docs/research/ijds_set_preserving_embedding_sensitivity_v1d_protocol_2026-07-30.md",
        "v1c_no_go": "docs/research/ijds_set_preserving_embedding_sensitivity_v1c_no_go_2026-07-30.md",
        "runner": "scripts/experiments/run_ijds_set_preserving_embedding_sensitivity_v1d.py",
        "implementation": "src/ijds_challengers/set_preserving_embedding_v1d.py",
    }.items():
        if registered[f"{prefix}_{registered_name}"].resolve() != (repo_root / relative).resolve():
            raise RuntimeError("The set-preserving embedding publication input route changed.")
        if dict(cast(Mapping[str, Any], implementation[relative])) != relative_artifact_descriptor(
            registered[f"{prefix}_{registered_name}"], repo_root=repo_root
        ):
            raise RuntimeError("The set-preserving embedding publication input hash changed.")

    phase_summary = _load_json_object(
        source_artifacts["summary"], label="set-preserving outcome-free summary"
    )
    phase_receipt = _load_json_object(
        source_artifacts["receipt"], label="set-preserving outcome-free receipt"
    )
    phase_freeze = _load_json_object(
        source_artifacts["freeze"], label="set-preserving outcome-free freeze"
    )
    for label, payload in (
        ("Phase-A summary", phase_summary),
        ("Phase-A receipt", phase_receipt),
        ("Phase-A freeze", phase_freeze),
    ):
        _require_clean_execution(payload, label=f"set-preserving {label}")
        if (
            payload.get("status")
            != "outcome_free_set_preserving_allocations_frozen_before_outcomes"
        ):
            raise RuntimeError(f"Set-preserving {label} status changed.")
    null_selection = {
        "theta": None,
        "gamma": None,
        "ruler": None,
        "coordinate": None,
        "window": None,
        "policy": None,
    }
    if (
        summary.get("selection") != null_selection
        or phase_summary.get("selection") != null_selection
        or phase_freeze.get("selection") != null_selection
        or summary.get("policy_winner") is not None
        or summary.get("p_values_computed") is not False
        or summary.get("confirmatory") is not False
        or summary.get("replay_clean") is not False
        or summary.get("v1a_is_evidence") is not False
        or summary.get("v1c_is_evidence") is not False
        or manifest.get("confirmatory") is not False
        or manifest.get("replay_clean") is not False
        or manifest.get("v1a_is_evidence") is not False
        or manifest.get("v1c_is_evidence") is not False
        or summary.get("v1c_phase_b_outputs_reused") is not False
        or manifest.get("v1c_phase_b_outputs_reused") is not False
        or receipt.get("v1c_phase_b_outputs_reused") is not False
        or phase_summary.get("causal_interpretation") is not False
        or phase_receipt.get("outcome_columns_passed") != []
    ):
        raise RuntimeError("The set-preserving selection or interpretation boundary changed.")

    frames = {
        "evaluated_portfolios": pd.read_parquet(evaluation_artifacts["evaluated_portfolios"]),
        "monthly_sharp_contrasts": pd.read_parquet(evaluation_artifacts["monthly_sharp_contrasts"]),
        "window_sharp_contrasts": pd.read_parquet(evaluation_artifacts["window_sharp_contrasts"]),
        "direction_census": pd.read_parquet(evaluation_artifacts["metric_direction_census"]),
        "outcome_audit": pd.read_parquet(evaluation_artifacts["outcome_join_audit"]),
        "set_preservation": pd.read_parquet(source_artifacts["embedding_diagnostics"]),
        "allocation_contrasts": pd.read_parquet(source_artifacts["allocation_contrasts"]),
    }
    schemas = manifest.get("schemas")
    if not isinstance(schemas, Mapping) or set(schemas) != {
        "evaluated_portfolios",
        "monthly_sharp_contrasts",
        "window_sharp_contrasts",
        "metric_direction_census",
        "outcome_join_audit",
    }:
        raise RuntimeError("Set-preserving embedding persisted schema inventory changed.")
    schema_frame_names = {
        "evaluated_portfolios": "evaluated_portfolios",
        "monthly_sharp_contrasts": "monthly_sharp_contrasts",
        "window_sharp_contrasts": "window_sharp_contrasts",
        "metric_direction_census": "direction_census",
        "outcome_join_audit": "outcome_audit",
    }
    for schema_name, frame_name in schema_frame_names.items():
        raw_schema = schemas[schema_name]
        if not isinstance(raw_schema, Mapping):
            raise TypeError("Set-preserving embedding schema descriptor is invalid.")
        _require_embedding_schema(frames[frame_name], raw_schema, name=schema_name)
    _require_embedding_grid(frames)

    sets = frames["set_preservation"]
    require_exact_grid(
        sets,
        domains={
            "window_id": WINDOW_IDS,
            "role": ("policy_development", "primary_oot"),
            "theta": EMBEDDING_LEVELS,
        },
        label="set-preserving embedding diagnostics",
    )
    require_finite(
        sets,
        ("maximum_upper_contraction", "maximum_theta_zero_recovery_error"),
        label="set-preserving embedding diagnostics",
    )
    if (
        len(sets) != 80
        or int(sets["sets_changed"].sum()) != 0
        or not np.isclose(
            float(sets["maximum_upper_contraction"].max()),
            0.8920116585417792,
            rtol=0.0,
            atol=1e-15,
        )
        or not sets["maximum_theta_zero_recovery_error"].eq(0.0).all()
    ):
        raise RuntimeError("The set-preservation census changed.")

    allocations = frames["allocation_contrasts"]
    gamma_allocations = allocations.loc[
        allocations["contrast_family"].eq(EMBEDDING_CONTRAST_FAMILIES[1])
    ]
    theta_allocations = allocations.loc[
        allocations["contrast_family"].eq(EMBEDDING_CONTRAST_FAMILIES[0])
    ]
    allocation_axes = {
        "window_id": WINDOW_IDS,
        "period": ISSUE_MONTHS,
        "ruler": RULERS,
        "coordinate": COORDINATES,
    }
    require_exact_grid(
        gamma_allocations,
        domains={**allocation_axes, "theta": EMBEDDING_LEVELS},
        label="outcome-free gamma allocation contrasts",
    )
    require_exact_grid(
        theta_allocations,
        domains={
            **allocation_axes,
            "theta": EMBEDDING_LEVELS[1:],
            "gamma": EMBEDDING_LEVELS,
        },
        label="outcome-free theta allocation contrasts",
    )
    require_finite(
        allocations,
        (
            "normalized_exposure_distance",
            "objective_difference",
            "weighted_score_difference",
            "point_moment_difference",
        ),
        label="outcome-free allocation contrasts",
    )
    phase_controls = theta_allocations.loc[theta_allocations["gamma"].eq(0.0)]
    if (
        len(phase_controls) != 2880
        or not phase_controls["normalized_exposure_distance"].eq(0.0).all()
        or not phase_controls["objective_difference"].eq(0.0).all()
    ):
        raise RuntimeError("The outcome-free gamma-zero negative control changed.")

    noncontrol = theta_allocations.loc[theta_allocations["gamma"].gt(0.0)]
    allocation_rows: list[dict[str, Any]] = []
    for ruler, subset in (
        ("all_rulers", noncontrol),
        ("objective_matched", noncontrol.loc[noncontrol["ruler"].eq("objective_matched")]),
        ("normalized_score", noncontrol.loc[noncontrol["ruler"].eq("normalized_score")]),
    ):
        changes = int(subset["normalized_exposure_distance"].gt(1e-10).sum())
        allocation_rows.append(
            {
                "ruler": ruler,
                "noncontrol_theta_contrasts": len(subset),
                "allocation_changes_gt_1e10": changes,
                "allocation_change_fraction": changes / len(subset),
                "maximum_normalized_exposure_distance": float(
                    subset["normalized_exposure_distance"].max()
                ),
                "set_diagnostic_rows": 80,
                "sets_changed": 0,
                "maximum_upper_contraction": 0.8920116585417792,
            }
        )
    allocation_table = pd.DataFrame(allocation_rows)
    if (
        allocation_table["noncontrol_theta_contrasts"].tolist() != [11520, 5760, 5760]
        or allocation_table["allocation_changes_gt_1e10"].tolist() != [9659, 3899, 5760]
        or not np.isclose(
            allocation_table.loc[0, "maximum_normalized_exposure_distance"],
            0.684049776890922,
            rtol=0.0,
            atol=1e-15,
        )
        or not np.isclose(
            allocation_table.loc[1, "maximum_normalized_exposure_distance"],
            0.5758632511294073,
            rtol=0.0,
            atol=1e-15,
        )
        or not np.isclose(
            allocation_table.loc[2, "maximum_normalized_exposure_distance"],
            0.684049776890922,
            rtol=0.0,
            atol=1e-15,
        )
        or bool(allocation_table.isna().any().any())
    ):
        raise RuntimeError("The set-preserving allocation-change census changed.")

    monthly_controls = frames["monthly_sharp_contrasts"].loc[
        frames["monthly_sharp_contrasts"]["contrast_family"].eq(EMBEDDING_CONTRAST_FAMILIES[0])
        & frames["monthly_sharp_contrasts"]["gamma"].eq(0.0)
    ]
    pooled_controls = frames["window_sharp_contrasts"].loc[
        frames["window_sharp_contrasts"]["contrast_family"].eq(EMBEDDING_CONTRAST_FAMILIES[0])
        & frames["window_sharp_contrasts"]["gamma"].eq(0.0)
    ]
    control_columns = (
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
    )
    if (
        len(monthly_controls) != 2880
        or not monthly_controls.loc[:, control_columns].eq(0.0).all().all()
        or len(pooled_controls) != 192
        or not pooled_controls.loc[:, control_columns].eq(0.0).all().all()
    ):
        raise RuntimeError("The monthly or pooled gamma-zero negative control changed.")

    direction_table = _embedding_direction_table(frames["direction_census"])
    theta_directions = frames["direction_census"].loc[
        frames["direction_census"]["contrast_family"].eq(EMBEDDING_CONTRAST_FAMILIES[0])
        & frames["direction_census"]["gamma"].gt(0.0)
    ]
    track_categories = theta_directions.groupby(
        ["window_id", "ruler", "coordinate", "gamma", "metric"], observed=True, sort=False
    )
    tracks = 0
    tracks_changing = 0
    tracks_with_both_tolerance_signs = 0
    tracks_with_both_geometric_signs = 0
    for _, group in track_categories:
        tracks += 1
        tolerance = set(group["direction_at_tolerance"].astype(str))
        geometric = set(group["geometric_direction"].astype(str))
        tracks_changing += int(len(tolerance) > 1)
        tracks_with_both_tolerance_signs += int({"negative", "positive"}.issubset(tolerance))
        tracks_with_both_geometric_signs += int({"negative", "positive"}.issubset(geometric))
    if (
        tracks,
        tracks_changing,
        tracks_with_both_tolerance_signs,
        tracks_with_both_geometric_signs,
    ) != (
        576,
        324,
        77,
        96,
    ):
        raise RuntimeError("The theta direction-noninvariance track census changed.")

    findings = {
        "set_preservation_and_allocation_change_verified": True,
        "theta_direction_noninvariance_verified": True,
        "set_diagnostic_rows": 80,
        "sets_changed": 0,
        "maximum_upper_contraction": 0.8920116585417792,
        "noncontrol_theta_allocation_contrasts": 11520,
        "allocation_changes_gt_1e10": 9659,
        "maximum_normalized_exposure_distance": 0.684049776890922,
        "theta_direction_tracks": 576,
        "theta_tracks_changing_direction_category": 324,
        "theta_tracks_with_both_separated_signs_at_tolerance": 77,
        "theta_tracks_with_both_geometric_signs": 96,
        "phase_a_gamma_zero_control_cells": 2880,
        "pooled_gamma_zero_control_cells": 192,
        "retrospective_postinspection_nonconfirmatory": True,
        "selected_theta_gamma_ruler_coordinate_window_or_policy": False,
        "p_values_computed": False,
        "causal_or_prospective_claimed": False,
    }
    all_artifacts = {
        **{f"source_{name}": path for name, path in source_artifacts.items()},
        **{f"evaluation_{name}": path for name, path in evaluation_artifacts.items()},
        "evaluation_manifest": manifest_path,
    }
    return VerifiedFrontierRun(
        config_path,
        summary_path,
        receipt_path,
        protocol_path,
        runner_path,
        implementation_path,
        summary,
        receipt,
        all_artifacts,
        frames,
        {"allocation_summary": allocation_table, "direction_census": direction_table},
        findings,
    )


def load_frontier_evidence(
    registered: Mapping[str, Path],
    diagnostics: Mapping[str, Any],
    *,
    repo_root: Path,
) -> FrontierEvidence:
    """Load every active Git-transported frontier lineage fail-closed."""
    return FrontierEvidence(
        residual_transport=_load_residual(
            registered,
            cast(Mapping[str, Any], diagnostics["residual_transport_frontier"]),
            repo_root=repo_root,
        ),
        marginal_score_outcome_gap=_load_marginal(
            registered,
            cast(Mapping[str, Any], diagnostics["marginal_score_outcome_gap"]),
            repo_root=repo_root,
        ),
        decision_catalog_transport=_load_decision(
            registered,
            cast(Mapping[str, Any], diagnostics["decision_catalog_transport"]),
            repo_root=repo_root,
        ),
        funded_selection_estimands=_load_funded(
            registered,
            cast(Mapping[str, Any], diagnostics["funded_selection_estimands"]),
            repo_root=repo_root,
        ),
        set_preserving_embedding=_load_embedding(
            registered,
            cast(Mapping[str, Any], diagnostics["set_preserving_embedding"]),
            repo_root=repo_root,
        ),
    )
