"""Verified evidence for the post-inspection IJDS scientific frontiers.

The four promoted runs are small Git-transported scientific artifacts.  They
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
METRICS = ("payoff_shortfall", "default_gap", "miscoverage_excess")
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
    """All four independently gated scientific frontier runs."""

    residual_transport: VerifiedFrontierRun
    marginal_score_outcome_gap: VerifiedFrontierRun
    decision_catalog_transport: VerifiedFrontierRun
    funded_selection_estimands: VerifiedFrontierRun


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
    summary_table = (
        pooled.groupby("learner", sort=False, observed=True)[
            "sharp_directional_discrepancy_comparison"
        ]
        .value_counts()
        .unstack(fill_value=0)
        .reindex(index=LEARNERS, columns=RESIDUAL_DIRECTIONS, fill_value=0)
        .reset_index()
    )
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


def load_frontier_evidence(
    registered: Mapping[str, Path],
    diagnostics: Mapping[str, Any],
    *,
    repo_root: Path,
) -> FrontierEvidence:
    """Load all four clean Git-transported frontier lineages fail-closed."""
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
    )
