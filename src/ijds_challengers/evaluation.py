"""Hash-verified post-freeze evaluation for the two-ruler challenger."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.evaluation.policy_contrast_bounds import sharp_policy_contrast_bounds
from src.utils.isolated_experiment import relative_artifact_descriptor


@dataclass(frozen=True)
class FrozenFrontier:
    """Verified V1c paths and metadata available before the outcome join."""

    artifacts: dict[str, Path]
    freeze: dict[str, Any]
    summary: dict[str, Any]


def verify_frontier_freeze(
    config: Mapping[str, Any],
    *,
    repo_root: Path,
) -> FrozenFrontier:
    """Verify the exact V1c freeze and every outcome-free artifact descriptor."""
    source = config["source_frontier"]
    descriptor = source["freeze"]
    freeze_path = (repo_root / str(descriptor["path"])).resolve()
    actual = relative_artifact_descriptor(freeze_path, repo_root=repo_root)
    if actual != descriptor:
        raise RuntimeError("The V1c freeze descriptor does not match the V2 protocol.")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if not isinstance(freeze, dict):
        raise TypeError("The V1c freeze must be a JSON object.")
    expected = {
        "status": str(source["status"]),
        "run_tag": str(source["run_tag"]),
        "protocol_tag": str(source["protocol_tag"]),
        "protocol_commit": str(source["protocol_commit"]),
    }
    for field, value in expected.items():
        if freeze.get(field) != value:
            raise RuntimeError(f"V1c freeze field mismatch: {field}.")
    if freeze.get("outcome_columns_passed_to_frontier") != []:
        raise RuntimeError("The V1c freeze reports outcome leakage.")
    for field in ("policy_selection", "window_selection", "ruler_selection"):
        if freeze.get(field) is not None:
            raise RuntimeError(f"The V1c freeze reports forbidden selection: {field}.")

    expected_artifacts = {
        "solve_records",
        "allocations",
        "endpoint_diagnostics",
        "objective_optimum_diagnostics",
        "order_sensitivity",
        "independent_validation",
    }
    descriptors = freeze.get("outcome_free_artifacts")
    if not isinstance(descriptors, dict) or set(descriptors) != expected_artifacts:
        raise RuntimeError("The V1c outcome-free artifact inventory changed.")
    artifacts: dict[str, Path] = {}
    for name, artifact_descriptor in descriptors.items():
        path = (repo_root / str(artifact_descriptor["path"])).resolve()
        if relative_artifact_descriptor(path, repo_root=repo_root) != artifact_descriptor:
            raise RuntimeError(f"V1c artifact descriptor mismatch: {name}.")
        artifacts[str(name)] = path
    for name in ("summary", "execution_receipt"):
        item = freeze.get(name)
        if not isinstance(item, dict):
            raise RuntimeError(f"V1c freeze is missing {name} metadata.")
        path = (repo_root / str(item["path"])).resolve()
        if relative_artifact_descriptor(path, repo_root=repo_root) != item:
            raise RuntimeError(f"V1c {name} descriptor mismatch.")
    summary_descriptor = freeze["summary"]
    summary_path = (repo_root / str(summary_descriptor["path"])).resolve()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict) or summary.get("status") != str(source["status"]):
        raise RuntimeError("The V1c summary status is not evaluation eligible.")
    expected_counts = config["evaluation"]
    if int(summary["counts"]["solve_records"]) != int(
        expected_counts["expected_solve_records"]
    ) or int(summary["counts"]["funded_rows"]) != int(expected_counts["expected_funded_rows"]):
        raise RuntimeError("The V1c summary census changed.")
    return FrozenFrontier(artifacts=artifacts, freeze=freeze, summary=summary)


def validate_outcome_alignment(
    allocations: pd.DataFrame,
    outcomes: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Validate one ID/role/period outcome universe before portfolio evaluation."""
    if bool(outcomes["id"].duplicated().any()):
        raise RuntimeError("The outcome universe contains duplicate IDs.")
    observed = pd.to_numeric(outcomes["snapshot_default"], errors="coerce")
    finite = observed.notna()
    if not bool(observed.loc[finite].isin([0, 1]).all()):
        raise RuntimeError("The outcome universe contains a nonbinary observed outcome.")
    roles = [str(value) for value in config["evaluation"]["evaluated_roles"]]
    selected = outcomes.loc[outcomes["role"].isin(roles)].copy()
    counts = selected["role"].value_counts().to_dict()
    expected = {
        str(role): int(value)
        for role, value in config["evaluation"]["expected_candidate_counts"].items()
    }
    if counts != expected:
        raise RuntimeError(f"The V2 candidate outcome census changed: {counts}.")

    funded_keys = allocations[["id", "role", "period"]].drop_duplicates()
    if bool(funded_keys["id"].duplicated().any()):
        raise RuntimeError("A funded ID maps to multiple decision role/period keys.")
    outcome_keys = outcomes[["id", "role", "period"]].rename(
        columns={"role": "outcome_role", "period": "outcome_period"}
    )
    aligned = funded_keys.merge(outcome_keys, on="id", how="left", validate="one_to_one")
    if bool(aligned[["outcome_role", "outcome_period"]].isna().any().any()):
        raise RuntimeError("At least one funded ID has no archive outcome row.")
    if not bool(
        aligned["role"].astype(str).eq(aligned["outcome_role"].astype(str)).all()
        and aligned["period"].astype(str).eq(aligned["outcome_period"].astype(str)).all()
    ):
        raise RuntimeError("Funded role/period keys do not align with archive outcomes.")

    audit = (
        selected.groupby(["role", "snapshot_resolution"], observed=True, sort=True)
        .agg(candidate_rows=("id", "size"), resolved_rows=("snapshot_default", "count"))
        .reset_index()
    )
    audit["unresolved_rows"] = audit["candidate_rows"] - audit["resolved_rows"]
    return audit


def build_endpoint_contrasts(
    joined_allocations: pd.DataFrame,
    endpoint_diagnostics: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    lgd: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build every locked monthly and complete-window gamma endpoint contrast."""
    evaluation = config["evaluation"]
    role = str(evaluation["primary_contrast_role"])
    rulers = tuple(str(value) for value in evaluation["rulers"])
    coordinates = tuple(float(value) for value in evaluation["coordinates"])
    windows = tuple(sorted(endpoint_diagnostics["window_id"].astype(str).unique()))
    monthly_rows: list[dict[str, Any]] = []
    window_rows: list[dict[str, Any]] = []
    for window_id in windows:
        window_allocations = joined_allocations.loc[
            joined_allocations["window_id"].eq(window_id) & joined_allocations["role"].eq(role)
        ]
        window_structure = endpoint_diagnostics.loc[
            endpoint_diagnostics["window_id"].eq(window_id) & endpoint_diagnostics["role"].eq(role)
        ]
        for ruler in rulers:
            for coordinate in coordinates:
                policy_a = _policy_label(ruler, 1.0, coordinate)
                policy_b = _policy_label(ruler, 0.0, coordinate)
                pair = window_allocations.loc[
                    window_allocations["policy_label"].isin([policy_a, policy_b])
                ]
                _validate_policy_pair_attributes(pair)
                structure = window_structure.loc[
                    window_structure["ruler"].eq(ruler)
                    & np.isclose(
                        window_structure["coordinate"].to_numpy(dtype=float),
                        coordinate,
                        atol=0.0,
                        rtol=0.0,
                    )
                ]
                if len(structure) != int(evaluation["expected_primary_months"]):
                    raise RuntimeError(
                        f"Endpoint structure is incomplete for {window_id}/{ruler}/{coordinate}."
                    )
                window_rows.append(
                    {
                        "window_id": window_id,
                        "ruler": ruler,
                        "coordinate": coordinate,
                        "months": int(len(structure)),
                        "nonidentical_months": int(
                            structure["normalized_exposure_distance"].gt(1.0e-6).sum()
                        ),
                        "monthly_exposure_distance_sum": float(
                            structure["normalized_exposure_distance"].sum()
                        ),
                        "monthly_exposure_distance_mean": float(
                            structure["normalized_exposure_distance"].mean()
                        ),
                        "monthly_exposure_distance_maximum": float(
                            structure["normalized_exposure_distance"].max()
                        ),
                        **sharp_policy_contrast_bounds(
                            pair,
                            policy_a=policy_a,
                            policy_b=policy_b,
                            role=role,
                            lgd=lgd,
                        ),
                    }
                )
                for period, month_pair in pair.groupby("period", observed=True, sort=True):
                    period_structure = structure.loc[structure["period"].eq(str(period))]
                    if len(period_structure) != 1:
                        raise RuntimeError(
                            f"Monthly structure is incomplete for {window_id}/{period}."
                        )
                    monthly_rows.append(
                        {
                            "window_id": window_id,
                            "period": str(period),
                            "ruler": ruler,
                            "coordinate": coordinate,
                            "normalized_exposure_distance": float(
                                period_structure["normalized_exposure_distance"].iloc[0]
                            ),
                            **sharp_policy_contrast_bounds(
                                month_pair,
                                policy_a=policy_a,
                                policy_b=policy_b,
                                role=role,
                                lgd=lgd,
                            ),
                        }
                    )
    return pd.DataFrame(window_rows), pd.DataFrame(monthly_rows)


def build_metric_directions(
    window_contrasts: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Classify every predeclared metric bound without selecting a subset."""
    rows: list[dict[str, Any]] = []
    for contrast in window_contrasts.to_dict(orient="records"):
        for metric, spec in config["metrics"].items():
            lower = float(contrast[str(spec["lower"])])
            upper = float(contrast[str(spec["upper"])])
            tolerance = float(spec["direction_tolerance"])
            rows.append(
                {
                    "window_id": str(contrast["window_id"]),
                    "ruler": str(contrast["ruler"]),
                    "coordinate": float(contrast["coordinate"]),
                    "metric": str(metric),
                    "lower": lower,
                    "upper": upper,
                    "direction_tolerance": tolerance,
                    "direction": direction_from_bounds(
                        lower,
                        upper,
                        tolerance=tolerance,
                    ),
                }
            )
    return pd.DataFrame(rows)


def direction_from_bounds(lower: float, upper: float, *, tolerance: float) -> str:
    """Classify one ordered interval with an explicit zero tolerance."""
    low = float(lower)
    high = float(upper)
    tol = float(tolerance)
    if not np.isfinite(low) or not np.isfinite(high) or low > high + tol:
        raise ValueError("Direction classification requires an ordered finite interval.")
    if low > tol:
        return "gamma_1_higher"
    if high < -tol:
        return "gamma_1_lower"
    if abs(low) <= tol and abs(high) <= tol:
        return "exact_zero"
    return "crosses_zero"


def validate_complete_evaluation(
    evaluated: pd.DataFrame,
    joined: pd.DataFrame,
    window_contrasts: pd.DataFrame,
    monthly_contrasts: pd.DataFrame,
    directions: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> None:
    """Fail unless every frozen portfolio and endpoint contrast is retained."""
    expected = config["evaluation"]
    actual = {
        "evaluated": len(evaluated),
        "joined": len(joined),
        "window": len(window_contrasts),
        "monthly": len(monthly_contrasts),
        "directions": len(directions),
    }
    required = {
        "evaluated": int(expected["expected_solve_records"]),
        "joined": int(expected["expected_funded_rows"]),
        "window": int(expected["expected_window_contrasts"]),
        "monthly": int(expected["expected_monthly_contrasts"]),
        "directions": int(expected["expected_metric_directions"]),
    }
    if actual != required:
        raise RuntimeError(f"The V2 evaluation census is incomplete: {actual} != {required}.")
    if window_contrasts["window_id"].nunique() != int(expected["expected_windows"]):
        raise RuntimeError("The V2 window census is incomplete.")
    keys = ["window_id", "ruler", "coordinate"]
    if bool(window_contrasts.duplicated(keys).any()):
        raise RuntimeError("The V2 window contrast grid contains duplicates.")
    direction_keys = [*keys, "metric"]
    if bool(directions.duplicated(direction_keys).any()):
        raise RuntimeError("The V2 metric-direction grid contains duplicates.")


def _policy_label(ruler: str, gamma: float, coordinate: float) -> str:
    return f"{ruler}_g{round(gamma * 100):03d}_c{round(coordinate * 100):03d}"


def _validate_policy_pair_attributes(allocations: pd.DataFrame) -> None:
    """Require loan attributes to agree across the two frozen endpoints."""
    attributes = [
        "contractual_rate",
        "conformal_lower",
        "conformal_upper",
        "snapshot_default",
    ]
    counts = allocations.groupby("id", observed=True)[attributes].nunique(dropna=False)
    if bool(counts.gt(1).any(axis=1).any()):
        raise RuntimeError("Loan attributes disagree across frozen endpoint policies.")
