"""Verified complete-grid portfolio-structure sensitivity evidence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pandas as pd
import yaml

from src.ijds_audit.grid_contracts import require_exact_frame, require_exact_grid, require_finite
from src.ijds_audit.structural_checkpoint import ARTIFACT_FILES
from src.ijds_audit.structural_sensitivity import declared_scenarios
from src.utils.artifact_descriptor import verified_artifact_path

WINDOW_IDS = (
    *(f"w{index:02d}_2012m{index:02d}_m{index + 5:02d}" for index in range(1, 8)),
    "w08_2012m08_2013m01",
)
RULERS = ("objective_matched", "normalized_score")
COORDINATES = (0.25, 0.50, 0.75)
METRICS = ("standardized_payoff", "funded_default", "funded_binary_miscoverage")
DIRECTIONS = ("gamma_1_lower", "gamma_1_higher", "crosses_zero", "exact_zero")
SUMMARY_ARTIFACTS = (
    "scenario_summary",
    "allocation_activity",
    "window_contrasts",
    "metric_directions",
)
SCENARIO_COLUMNS = ("scenario_id", "budget", "purpose_cap", "lgd", "is_baseline")
SCENARIO_TAG_COLUMNS = (
    "scenario_id",
    "scenario_budget",
    "scenario_purpose_cap",
    "scenario_lgd",
    "scenario_is_baseline",
)
DIRECTION_SUMMARY_COLUMNS = {
    "standardized_payoff": {
        "gamma_1_lower": "standardized_payoff_gamma_1_lower_cells",
        "gamma_1_higher": "standardized_payoff_gamma_1_higher_cells",
        "crosses_zero": "standardized_payoff_crosses_zero_cells",
        "exact_zero": "standardized_payoff_exact_zero_cells",
    },
    "funded_default": {
        "gamma_1_lower": "funded_default_gamma_1_lower_cells",
        "gamma_1_higher": "funded_default_gamma_1_higher_cells",
        "crosses_zero": "funded_default_crosses_zero_cells",
        "exact_zero": "funded_default_exact_zero_cells",
    },
    "funded_binary_miscoverage": {
        "gamma_1_lower": "funded_binary_miscoverage_gamma_1_lower_cells",
        "gamma_1_higher": "funded_binary_miscoverage_gamma_1_higher_cells",
        "crosses_zero": "funded_binary_miscoverage_crosses_zero_cells",
        "exact_zero": "funded_binary_miscoverage_exact_zero_cells",
    },
}


@dataclass(frozen=True)
class StructuralSensitivityEvidence:
    """Hash-verified V6 freeze, evaluation, frames, and derived findings."""

    config: dict[str, Any]
    freeze: dict[str, Any]
    summary: dict[str, Any]
    frames: dict[str, pd.DataFrame]
    findings: dict[str, Any]


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not all(isinstance(key, str) for key in raw):
        raise TypeError(f"{label} must be a JSON object with string keys.")
    return cast(dict[str, Any], raw)


def _load_config(path: Path) -> dict[str, Any]:
    raw: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not all(isinstance(key, str) for key in raw):
        raise TypeError("Structural sensitivity config must be a mapping with string keys.")
    config = cast(dict[str, Any], raw)
    if config.get("protocol_status") != (
        "locked_retrospective_outcome_free_structural_sensitivity_v6_order_tolerance"
    ):
        raise RuntimeError("Paper-facing structural sensitivity is not locked V6.")
    return config


def _require_identity(
    payload: Mapping[str, Any],
    identity: Mapping[str, Any],
    *,
    label: str,
    fields: tuple[str, ...] = ("run_tag", "protocol_tag", "protocol_commit"),
) -> None:
    for field in fields:
        if payload.get(field) != identity.get(field):
            raise RuntimeError(f"{label} identity changed on {field}.")


def _require_freeze_contract(
    freeze: Mapping[str, Any],
    *,
    identity: Mapping[str, Any],
    scenario_ids: tuple[str, ...],
) -> None:
    _require_identity(freeze, identity, label="Structural freeze")
    if freeze.get("status") != "outcome_free_structural_grid_frozen_before_endpoint_join":
        raise RuntimeError("Structural freeze is incomplete.")
    if int(freeze.get("scenario_count", -1)) != len(scenario_ids):
        raise RuntimeError("Structural freeze scenario count changed.")
    if freeze.get("outcome_columns_passed_to_frontier") != []:
        raise RuntimeError("Structural freeze reports outcome leakage.")
    if freeze.get("protected_stages_run") != [] or freeze.get("protected_artifacts_written") != []:
        raise RuntimeError("Structural freeze reports a protected-stage side effect.")
    recovery = freeze.get("recovery")
    if not isinstance(recovery, Mapping) or (
        recovery.get("recovered_scenarios") != 35
        or recovery.get("recomputed_scenarios") != 1
        or recovery.get("missing_scenario_ids") != ["b0500k_p020_l025"]
    ):
        raise RuntimeError("Structural freeze recovery contract changed.")


def _verify_scenario_artifacts(
    freeze: Mapping[str, Any],
    *,
    scenario_ids: tuple[str, ...],
    repo_root: Path,
) -> None:
    artifacts = freeze.get("scenario_artifacts")
    if not isinstance(artifacts, Mapping) or set(artifacts) != set(scenario_ids):
        raise RuntimeError("Structural freeze scenario inventory changed.")
    for scenario_id, raw_inventory in artifacts.items():
        if not isinstance(raw_inventory, Mapping) or set(raw_inventory) != set(ARTIFACT_FILES):
            raise RuntimeError(f"Structural shard inventory changed for {scenario_id}.")
        for name, descriptor in raw_inventory.items():
            if not isinstance(descriptor, Mapping):
                raise TypeError(f"Structural shard descriptor {scenario_id}/{name} is invalid.")
            verified_artifact_path(
                descriptor,
                repo_root=repo_root,
                label=f"Structural shard {scenario_id}/{name}",
            )


def _verify_freeze_sources(freeze: Mapping[str, Any], *, repo_root: Path) -> None:
    for name in ("outcome_free_decision_base", "scenario_counts"):
        descriptor = freeze.get(name)
        if not isinstance(descriptor, Mapping):
            raise TypeError(f"Structural freeze omits {name}.")
        verified_artifact_path(descriptor, repo_root=repo_root, label=f"Structural {name}")


def _verify_freeze(
    freeze_path: Path,
    *,
    identity: Mapping[str, Any],
    scenario_ids: tuple[str, ...],
    repo_root: Path,
) -> dict[str, Any]:
    freeze = _load_json_object(freeze_path, label="Structural freeze")
    _require_freeze_contract(freeze, identity=identity, scenario_ids=scenario_ids)
    _verify_scenario_artifacts(freeze, scenario_ids=scenario_ids, repo_root=repo_root)
    _verify_freeze_sources(freeze, repo_root=repo_root)
    return freeze


def _verified_summary_artifacts(summary: Mapping[str, Any], *, repo_root: Path) -> dict[str, Path]:
    artifacts = summary.get("artifacts")
    if not isinstance(artifacts, Mapping) or set(artifacts) != set(SUMMARY_ARTIFACTS):
        raise RuntimeError("Structural evaluation artifact inventory changed.")
    verified: dict[str, Path] = {}
    for name, descriptor in artifacts.items():
        if not isinstance(descriptor, Mapping):
            raise TypeError(f"Structural evaluation descriptor {name!r} is invalid.")
        verified[str(name)] = verified_artifact_path(
            descriptor,
            repo_root=repo_root,
            label=f"Structural evaluation {name}",
        )
    return verified


def _scenario_frame(config: Mapping[str, Any]) -> pd.DataFrame:
    scenarios = declared_scenarios(config)
    frame = pd.DataFrame(scenarios).rename(
        columns={
            "scenario_budget": "budget",
            "scenario_purpose_cap": "purpose_cap",
            "scenario_lgd": "lgd",
            "scenario_is_baseline": "is_baseline",
        }
    )
    return frame.loc[:, list(SCENARIO_COLUMNS)].sort_values("scenario_id").reset_index(drop=True)


def _require_scenario_columns(
    frame: pd.DataFrame,
    expected: pd.DataFrame,
    *,
    label: str,
) -> None:
    require_exact_frame(
        frame.loc[:, list(SCENARIO_COLUMNS)].drop_duplicates(),
        expected,
        keys=("scenario_id",),
        label=label,
    )


def _validate_direction_counts(summary: pd.DataFrame, directions: pd.DataFrame) -> None:
    counts = (
        directions.groupby(["scenario_id", "metric", "direction"], observed=True, sort=True)
        .size()
        .to_dict()
    )
    for row_index in summary.index:
        scenario_id = str(summary.at[row_index, "scenario_id"])
        for metric, columns in DIRECTION_SUMMARY_COLUMNS.items():
            total = 0
            for direction, column in columns.items():
                expected = int(counts.get((scenario_id, metric, direction), 0))
                actual = int(summary.at[row_index, column])
                if actual != expected:
                    raise RuntimeError(
                        f"Structural direction count changed for {scenario_id}/{metric}/{direction}."
                    )
                total += actual
            if total != 48:
                raise RuntimeError(f"Structural scenario {scenario_id}/{metric} is incomplete.")


def _validate_summary_bounds(summary: pd.DataFrame, directions: pd.DataFrame) -> None:
    mappings = {
        "standardized_payoff": ("payoff_lower_min", "payoff_upper_max"),
        "funded_default": ("default_lower_min", "default_upper_max"),
        "funded_binary_miscoverage": ("miscoverage_lower_min", "miscoverage_upper_max"),
    }
    for metric, (lower_column, upper_column) in mappings.items():
        scoped = directions.loc[directions["metric"].eq(metric)]
        derived = (
            scoped.groupby("scenario_id", observed=True, sort=True)
            .agg(**{lower_column: ("lower", "min"), upper_column: ("upper", "max")})
            .reset_index()
        )
        require_exact_frame(
            summary.loc[:, ["scenario_id", lower_column, upper_column]],
            derived,
            keys=("scenario_id",),
            label=f"Structural {metric} bounds",
        )


def _validate_activity_summary(summary: pd.DataFrame, activity: pd.DataFrame) -> None:
    value_columns = [column for column in activity if column not in SCENARIO_COLUMNS]
    renamed = {column: f"activity_{column}" for column in value_columns}
    expected = activity.loc[:, ["scenario_id", *value_columns]].rename(columns=renamed)
    require_exact_frame(
        summary.loc[:, ["scenario_id", *renamed.values()]],
        expected,
        keys=("scenario_id",),
        label="Structural allocation-activity summary",
    )


def _validate_frames(
    frames: Mapping[str, pd.DataFrame],
    *,
    expected_scenarios: pd.DataFrame,
    reference_two_ruler: pd.DataFrame,
) -> None:
    scenario_ids = tuple(expected_scenarios["scenario_id"].astype(str))
    summary = frames["scenario_summary"]
    activity = frames["allocation_activity"]
    contrasts = frames["window_contrasts"]
    directions = frames["metric_directions"]

    require_exact_grid(summary, domains={"scenario_id": scenario_ids}, label="structural summary")
    require_exact_grid(activity, domains={"scenario_id": scenario_ids}, label="structural activity")
    _require_scenario_columns(summary, expected_scenarios, label="structural summary scenarios")
    _require_scenario_columns(activity, expected_scenarios, label="structural activity scenarios")
    require_exact_grid(
        contrasts,
        domains={
            "scenario_id": scenario_ids,
            "window_id": WINDOW_IDS,
            "ruler": RULERS,
            "coordinate": COORDINATES,
        },
        label="structural window contrasts",
    )
    require_exact_grid(
        directions,
        domains={
            "scenario_id": scenario_ids,
            "window_id": WINDOW_IDS,
            "ruler": RULERS,
            "coordinate": COORDINATES,
            "metric": METRICS,
        },
        label="structural metric directions",
    )
    if not set(directions["direction"]).issubset(DIRECTIONS):
        raise RuntimeError("Structural direction vocabulary changed.")
    require_finite(directions, ("lower", "upper"), label="structural metric directions")
    if not directions["lower"].le(directions["upper"]).all():
        raise RuntimeError("Structural metric bounds are reversed.")
    if bool(contrasts["causal_interpretation"].any()):
        raise RuntimeError("Structural contrasts are incorrectly marked causal.")
    require_finite(
        activity,
        (
            "purpose_cap_binding_share",
            "frontier_constraint_binding_share",
            "hhi_mean",
            "maximum_loan_weight",
            "maximum_purpose_share",
        ),
        label="structural allocation activity",
    )
    if not (
        activity["purpose_cap_binding_share"].between(0.0, 1.0).all()
        and activity["frontier_constraint_binding_share"].between(0.0, 1.0).all()
    ):
        raise RuntimeError("Structural binding shares lie outside [0, 1].")
    if not activity["portfolios"].eq(1440).all():
        raise RuntimeError("Structural scenario portfolio census changed.")
    _validate_activity_summary(summary, activity)
    _validate_direction_counts(summary, directions)
    _validate_summary_bounds(summary, directions)

    baseline = contrasts.loc[contrasts["scenario_is_baseline"]].drop(
        columns=list(SCENARIO_TAG_COLUMNS)
    )
    require_exact_frame(
        baseline,
        reference_two_ruler,
        keys=("window_id", "ruler", "coordinate"),
        label="structural baseline two-ruler reconciliation",
    )


def _group_scalar_map(
    frame: pd.DataFrame,
    *,
    group_column: str,
    value_column: str,
    key_format: str,
) -> dict[str, float]:
    result: dict[str, float] = {}
    for group, scoped in frame.groupby(group_column, observed=True, sort=True):
        values = scoped[value_column].drop_duplicates()
        if len(values) != 1:
            raise RuntimeError(f"Structural {value_column} varies within {group_column}={group}.")
        result[format(float(str(group)), key_format)] = float(values.iloc[0])
    return result


def _group_rounded_max_map(
    frame: pd.DataFrame,
    *,
    group_column: str,
    value_column: str,
    key_format: str,
    decimals: int,
) -> dict[str, float]:
    return {
        format(float(str(group)), key_format): round(float(scoped[value_column].max()), decimals)
        for group, scoped in frame.groupby(group_column, observed=True, sort=True)
    }


def structural_findings(summary: pd.DataFrame, directions: pd.DataFrame) -> dict[str, Any]:
    """Derive nonselective invariants over all 36 declared scenarios."""
    payoff_adverse = DIRECTION_SUMMARY_COLUMNS["standardized_payoff"]["gamma_1_lower"]
    payoff_favorable = DIRECTION_SUMMARY_COLUMNS["standardized_payoff"]["gamma_1_higher"]
    default_adverse = DIRECTION_SUMMARY_COLUMNS["funded_default"]["gamma_1_higher"]
    default_favorable = DIRECTION_SUMMARY_COLUMNS["funded_default"]["gamma_1_lower"]
    miscoverage_adverse = DIRECTION_SUMMARY_COLUMNS["funded_binary_miscoverage"]["gamma_1_higher"]
    miscoverage_favorable = DIRECTION_SUMMARY_COLUMNS["funded_binary_miscoverage"]["gamma_1_lower"]
    universally_favorable = (
        summary[payoff_favorable].eq(48)
        & summary[default_favorable].eq(48)
        & summary[miscoverage_favorable].eq(48)
    )
    universally_adverse = (
        summary[payoff_adverse].eq(48)
        & summary[default_adverse].eq(48)
        & summary[miscoverage_adverse].eq(48)
    )
    direction_totals = (
        directions.groupby(["metric", "direction"], observed=True, sort=True).size().to_dict()
    )
    return {
        "scenario_count": int(len(summary)),
        "complete_cartesian_grid": int(len(summary)) == 36,
        "every_scenario_has_adverse_default_and_miscoverage_cells": bool(
            summary[default_adverse].gt(0).all() and summary[miscoverage_adverse].gt(0).all()
        ),
        "minimum_adverse_default_cells_per_scenario": int(summary[default_adverse].min()),
        "minimum_adverse_miscoverage_cells_per_scenario": int(summary[miscoverage_adverse].min()),
        "universally_favorable_scenarios": int(universally_favorable.sum()),
        "universally_adverse_scenarios": int(universally_adverse.sum()),
        "scenarios_with_any_favorable_payoff_cell": int(summary[payoff_favorable].gt(0).sum()),
        "scenarios_with_any_favorable_default_cell": int(summary[default_favorable].gt(0).sum()),
        "scenarios_with_any_favorable_miscoverage_cell": int(
            summary[miscoverage_favorable].gt(0).sum()
        ),
        "portfolios_per_scenario": int(summary["activity_portfolios"].iloc[0]),
        "purpose_cap_binding_share_by_cap": _group_scalar_map(
            summary,
            group_column="purpose_cap",
            value_column="activity_purpose_cap_binding_share",
            key_format=".2f",
        ),
        "frontier_constraint_binding_share_by_budget": _group_scalar_map(
            summary,
            group_column="budget",
            value_column="activity_frontier_constraint_binding_share",
            key_format=".0f",
        ),
        "maximum_loan_weight_by_budget": _group_rounded_max_map(
            summary,
            group_column="budget",
            value_column="activity_maximum_loan_weight",
            key_format=".0f",
            decimals=12,
        ),
        "direction_totals": {
            metric: {
                direction: int(direction_totals.get((metric, direction), 0))
                for direction in DIRECTIONS
            }
            for metric in METRICS
        },
        "interpretation": (
            "The complete structural grid rules out universal favorable direction, while "
            "one-sided favorable cells in many scenarios also rule out universal adversity."
        ),
    }


def structural_publication_table(evidence: StructuralSensitivityEvidence) -> pd.DataFrame:
    """Return every scenario with complete metric-direction counts."""
    summary = evidence.frames["scenario_summary"]
    columns = [
        *SCENARIO_COLUMNS,
        DIRECTION_SUMMARY_COLUMNS["standardized_payoff"]["gamma_1_lower"],
        DIRECTION_SUMMARY_COLUMNS["standardized_payoff"]["gamma_1_higher"],
        DIRECTION_SUMMARY_COLUMNS["standardized_payoff"]["crosses_zero"],
        DIRECTION_SUMMARY_COLUMNS["standardized_payoff"]["exact_zero"],
        DIRECTION_SUMMARY_COLUMNS["funded_default"]["gamma_1_higher"],
        DIRECTION_SUMMARY_COLUMNS["funded_default"]["gamma_1_lower"],
        DIRECTION_SUMMARY_COLUMNS["funded_default"]["crosses_zero"],
        DIRECTION_SUMMARY_COLUMNS["funded_default"]["exact_zero"],
        DIRECTION_SUMMARY_COLUMNS["funded_binary_miscoverage"]["gamma_1_higher"],
        DIRECTION_SUMMARY_COLUMNS["funded_binary_miscoverage"]["gamma_1_lower"],
        DIRECTION_SUMMARY_COLUMNS["funded_binary_miscoverage"]["crosses_zero"],
        DIRECTION_SUMMARY_COLUMNS["funded_binary_miscoverage"]["exact_zero"],
        "activity_purpose_cap_binding_share",
        "activity_frontier_constraint_binding_share",
        "activity_portfolios",
        "activity_maximum_loan_weight",
    ]
    return (
        summary.loc[:, columns]
        .sort_values(["budget", "purpose_cap", "lgd"], kind="stable")
        .reset_index(drop=True)
    )


def load_structural_sensitivity_evidence(
    summary_path: Path,
    *,
    freeze_path: Path,
    config_path: Path,
    identity: Mapping[str, Any],
    repo_root: Path,
    reference_two_ruler: pd.DataFrame,
) -> StructuralSensitivityEvidence:
    """Load, hash-verify, and reconcile the complete structural V6 result."""
    config = _load_config(config_path)
    _require_identity(
        config,
        identity,
        label="Structural config",
        fields=("run_tag", "protocol_tag"),
    )
    expected_scenarios = _scenario_frame(config)
    scenario_ids = tuple(expected_scenarios["scenario_id"].astype(str))
    freeze = _verify_freeze(
        freeze_path,
        identity=identity,
        scenario_ids=scenario_ids,
        repo_root=repo_root,
    )
    summary = _load_json_object(summary_path, label="Structural evaluation summary")
    _require_identity(summary, identity, label="Structural evaluation")
    if summary.get("status") != "complete_post_freeze_structural_sensitivity_evaluation":
        raise RuntimeError("Structural sensitivity evaluation is incomplete.")
    if int(summary.get("scenario_count", -1)) != len(scenario_ids):
        raise RuntimeError("Structural evaluation scenario count changed.")
    if summary.get("selection") != {
        "scenario": None,
        "budget": None,
        "purpose_cap": None,
        "lgd": None,
    }:
        raise RuntimeError("Structural evaluation reports a selected scenario.")
    if (
        summary.get("protected_stages_run") != []
        or summary.get("protected_artifacts_written") != []
    ):
        raise RuntimeError("Structural evaluation reports a protected-stage side effect.")
    if summary.get("baseline_reconciliation_maxima") != {
        "realized_payoff_difference_lower": 0.0,
        "realized_payoff_difference_upper": 0.0,
        "weighted_default_difference_lower": 0.0,
        "weighted_default_difference_upper": 0.0,
        "weighted_miscoverage_difference_lower": 0.0,
        "weighted_miscoverage_difference_upper": 0.0,
    }:
        raise RuntimeError("Structural baseline reconciliation is no longer exact.")

    paths = _verified_summary_artifacts(summary, repo_root=repo_root)
    frames = {name: pd.read_parquet(path) for name, path in paths.items()}
    _validate_frames(
        frames,
        expected_scenarios=expected_scenarios,
        reference_two_ruler=reference_two_ruler,
    )
    findings = structural_findings(frames["scenario_summary"], frames["metric_directions"])
    if findings["complete_cartesian_grid"] is not True:
        raise RuntimeError("Structural sensitivity grid is incomplete.")
    return StructuralSensitivityEvidence(
        config=config,
        freeze=freeze,
        summary=summary,
        frames=frames,
        findings=findings,
    )
