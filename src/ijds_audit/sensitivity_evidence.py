"""Verified derivations for retrospective IJDS sensitivity evidence."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any, cast

import pandas as pd

from src.ijds_audit.grid_contracts import require_exact_frame, require_exact_grid, require_finite
from src.utils.artifact_descriptor import verified_artifact_path

ENDPOINT_LAGS = (0, 3, 6, 8, 12)
COVERAGE_LEARNERS = (
    "catboost_platt",
    "numeric_logistic_platt",
    "catboost_monotonic_platt",
    "woe_scorecard_platform_platt",
    "woe_scorecard_borrower_platt",
)
COVERAGE_ROLES = ("policy_development", "primary_oot", "censored_extension")
ENDPOINT_CENSUS_ROLES = (
    "pd_development",
    "probability_calibration",
    "conformal_fit",
    "policy_development",
    "primary_oot",
    "censored_extension",
)
WINDOW_IDS = (
    *(f"w{index:02d}_2012m{index:02d}_m{index + 5:02d}" for index in range(1, 8)),
    "w08_2012m08_2013m01",
)
RULERS = ("objective_matched", "normalized_score")
COORDINATES = (0.25, 0.50, 0.75)
TWO_RULER_METRICS = (
    "standardized_payoff",
    "funded_default",
    "funded_binary_miscoverage",
)
TWO_RULER_DIRECTIONS = ("gamma_1_lower", "gamma_1_higher", "crosses_zero", "exact_zero")
POLICY_IDS = tuple(f"linear-{index:03d}" for index in range(1, 10))
SUPPORT_SCOPES = (
    "named_c0_c1_c2",
    "development_admissible_exact_frontier",
    "broad_stress_exact_frontier",
)
SUPPORT_METRICS = ("standardized_payoff", "terminal_default", "funded_miscoverage")


@dataclass(frozen=True)
class EndpointSensitivityEvidence:
    """Hash-verified endpoint sensitivity and exact V3 reconciliation."""

    summary: dict[str, Any]
    frames: dict[str, pd.DataFrame]
    reconciliation: dict[str, Any]


def _verified_artifacts(
    summary: Mapping[str, Any],
    *,
    repo_root: Path,
    expected_names: Iterable[str],
) -> dict[str, Path]:
    artifacts = summary.get("artifacts")
    if not isinstance(artifacts, Mapping) or set(artifacts) != set(expected_names):
        raise RuntimeError("Endpoint sensitivity artifact inventory changed.")
    verified: dict[str, Path] = {}
    for name, raw in artifacts.items():
        if not isinstance(raw, Mapping):
            raise TypeError(f"Endpoint artifact {name!r} is not a descriptor.")
        verified[str(name)] = verified_artifact_path(
            raw,
            repo_root=repo_root,
            label=f"Endpoint {name}",
        )
    return verified


def _validate_endpoint_frames(frames: Mapping[str, pd.DataFrame]) -> None:
    census = frames["endpoint_census"]
    require_exact_grid(
        census,
        domains={
            "charged_off_lag_months": ENDPOINT_LAGS,
            "role": ENDPOINT_CENSUS_ROLES,
        },
        label="endpoint census",
    )
    require_finite(
        census,
        (
            "candidate_rows",
            "resolved_rows",
            "unresolved_rows",
            "default_rows",
            "nondefault_rows",
        ),
        label="endpoint census",
    )
    if not (
        census["candidate_rows"].eq(census["resolved_rows"] + census["unresolved_rows"]).all()
        and census["resolved_rows"].eq(census["default_rows"] + census["nondefault_rows"]).all()
    ):
        raise RuntimeError("Endpoint census arithmetic does not reconcile.")

    coverage = frames["coverage_cells"]
    require_exact_grid(
        coverage,
        domains={
            "charged_off_lag_months": ENDPOINT_LAGS,
            "learner": COVERAGE_LEARNERS,
            "window_id": WINDOW_IDS,
            "role": COVERAGE_ROLES,
            "taxonomy_groups": (5,),
            "conformal_group": (-1,),
        },
        label="endpoint coverage",
    )
    require_finite(
        coverage,
        (
            "candidate_rows",
            "resolved_rows",
            "unresolved_rows",
            "coverage_resolved",
            "coverage_lower",
            "coverage_upper",
        ),
        label="endpoint coverage",
    )
    if not (
        coverage["candidate_rows"].eq(coverage["resolved_rows"] + coverage["unresolved_rows"]).all()
        and coverage["coverage_lower"].le(coverage["coverage_upper"]).all()
        and coverage[["coverage_resolved", "coverage_lower", "coverage_upper"]]
        .ge(0.0)
        .all(axis=None)
        and coverage[["coverage_resolved", "coverage_lower", "coverage_upper"]]
        .le(1.0)
        .all(axis=None)
    ):
        raise RuntimeError("Endpoint coverage bounds or censuses are incoherent.")

    coverage_summary = frames["coverage_summary"]
    require_exact_grid(
        coverage_summary,
        domains={
            "charged_off_lag_months": ENDPOINT_LAGS,
            "learner": COVERAGE_LEARNERS,
            "role": COVERAGE_ROLES,
        },
        label="endpoint coverage summary",
    )
    derived_coverage = (
        coverage.groupby(["charged_off_lag_months", "learner", "role"], observed=True, sort=True)
        .agg(
            windows=("window_id", "nunique"),
            coverage_lower_min=("coverage_lower", "min"),
            coverage_upper_max=("coverage_upper", "max"),
        )
        .reset_index()
    )
    require_exact_frame(
        coverage_summary,
        derived_coverage,
        keys=("charged_off_lag_months", "learner", "role"),
        label="endpoint coverage summary",
    )

    contrasts = frames["two_ruler_window_contrasts"]
    require_exact_grid(
        contrasts,
        domains={
            "charged_off_lag_months": ENDPOINT_LAGS,
            "window_id": WINDOW_IDS,
            "ruler": RULERS,
            "coordinate": COORDINATES,
        },
        label="endpoint two-ruler contrasts",
    )
    directions = frames["two_ruler_directions"]
    require_exact_grid(
        directions,
        domains={
            "charged_off_lag_months": ENDPOINT_LAGS,
            "window_id": WINDOW_IDS,
            "ruler": RULERS,
            "coordinate": COORDINATES,
            "metric": TWO_RULER_METRICS,
        },
        label="endpoint two-ruler directions",
    )
    if not set(directions["direction"]).issubset(TWO_RULER_DIRECTIONS):
        raise RuntimeError("Endpoint two-ruler direction vocabulary changed.")
    direction_census = frames["two_ruler_direction_census"]
    require_exact_grid(
        direction_census,
        domains={
            "charged_off_lag_months": ENDPOINT_LAGS,
            "metric": TWO_RULER_METRICS,
            "direction": TWO_RULER_DIRECTIONS,
        },
        label="endpoint two-ruler direction census",
    )
    derived_direction_rows: list[dict[str, Any]] = []
    for lag, metric in product(ENDPOINT_LAGS, TWO_RULER_METRICS):
        scoped = directions.loc[
            directions["charged_off_lag_months"].eq(lag) & directions["metric"].eq(metric)
        ]
        counts = scoped["direction"].value_counts().to_dict()
        derived_direction_rows.extend(
            {
                "charged_off_lag_months": lag,
                "metric": metric,
                "direction": direction,
                "cells": int(counts.get(direction, 0)),
            }
            for direction in TWO_RULER_DIRECTIONS
        )
    require_exact_frame(
        direction_census,
        pd.DataFrame(derived_direction_rows),
        keys=("charged_off_lag_months", "metric", "direction"),
        label="endpoint two-ruler direction census",
    )

    envelopes = frames["exact_support_envelopes"]
    require_exact_grid(
        envelopes,
        domains={
            "charged_off_lag_months": ENDPOINT_LAGS,
            "window_id": WINDOW_IDS,
            "paired_policy_id": POLICY_IDS,
            "scope": SUPPORT_SCOPES,
            "metric": SUPPORT_METRICS,
        },
        label="endpoint exact-support envelopes",
    )
    if bool(envelopes["nested_scope_independent_replications"].any()):
        raise RuntimeError("Endpoint support scopes are incorrectly marked as replications.")
    support_census = frames["exact_support_census"]
    derived_support = (
        envelopes.groupby(
            ["scope", "metric", "direction", "charged_off_lag_months"],
            observed=True,
            sort=True,
        )
        .size()
        .reset_index()
    )
    derived_support.columns = [
        "scope",
        "metric",
        "direction",
        "charged_off_lag_months",
        "cells",
    ]
    require_exact_frame(
        support_census,
        derived_support,
        keys=("charged_off_lag_months", "scope", "metric", "direction"),
        label="endpoint exact-support census",
    )


def load_endpoint_sensitivity_evidence(
    summary_path: Path,
    *,
    identity: Mapping[str, Any],
    repo_root: Path,
    reference_coverage: pd.DataFrame,
    reference_two_ruler: pd.DataFrame,
    reference_envelopes: pd.DataFrame,
) -> EndpointSensitivityEvidence:
    """Load endpoint V1, verify all grids, and reconcile its six-month slice."""
    summary_raw: object = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(summary_raw, dict):
        raise TypeError("Endpoint sensitivity summary must be a JSON object.")
    if not all(isinstance(key, str) for key in summary_raw):
        raise TypeError("Endpoint sensitivity summary keys must be strings.")
    summary = cast(dict[str, Any], summary_raw)
    if summary.get("status") != "complete_retrospective_endpoint_availability_sensitivity":
        raise RuntimeError("Endpoint sensitivity is incomplete.")
    for field in ("run_tag", "protocol_tag", "protocol_commit"):
        if summary.get(field) != identity.get(field):
            raise RuntimeError(f"Endpoint sensitivity identity changed on {field}.")
    if tuple(summary.get("lags", ())) != ENDPOINT_LAGS:
        raise RuntimeError("Endpoint sensitivity lag grid changed.")
    if (
        int(summary.get("coverage_cells", -1)) != 600
        or int(summary.get("two_ruler_direction_cells", -1)) != 720
        or int(summary.get("exact_support_envelopes", -1)) != 3240
    ):
        raise RuntimeError("Endpoint sensitivity top-level census changed.")
    boundary = summary.get("claim_boundary", {})
    for field in (
        "preregistered",
        "confirmatory",
        "prospective",
        "outcome_based_selection",
        "allocation_refit",
        "policy_selection",
        "model_selection",
        "endpoint_selection",
    ):
        if boundary.get(field) is not False:
            raise RuntimeError(f"Endpoint sensitivity unexpectedly allows {field}.")
    if (
        summary.get("protected_stages_run") != []
        or summary.get("protected_artifacts_written") != []
    ):
        raise RuntimeError("Endpoint sensitivity reports a protected-stage side effect.")
    if any(value is not None for value in summary.get("selection", {}).values()):
        raise RuntimeError("Endpoint sensitivity reports a selected result.")

    artifact_names = (
        "endpoint_census",
        "coverage_cells",
        "coverage_summary",
        "two_ruler_window_contrasts",
        "two_ruler_directions",
        "two_ruler_direction_census",
        "exact_support_envelopes",
        "exact_support_census",
    )
    paths = _verified_artifacts(summary, repo_root=repo_root, expected_names=artifact_names)
    frames = {name: pd.read_parquet(path) for name, path in paths.items()}
    _validate_endpoint_frames(frames)

    lag6_coverage = (
        frames["coverage_cells"]
        .loc[frames["coverage_cells"]["charged_off_lag_months"].eq(6)]
        .drop(columns="charged_off_lag_months")
    )
    reference_coverage_slice = reference_coverage.loc[
        reference_coverage["learner"].isin(COVERAGE_LEARNERS)
        & reference_coverage["window_id"].isin(WINDOW_IDS)
        & reference_coverage["role"].isin(COVERAGE_ROLES)
        & reference_coverage["taxonomy_groups"].eq(5)
        & reference_coverage["conformal_group"].eq(-1)
    ]
    coverage_keys = (
        "learner",
        "window_id",
        "taxonomy_groups",
        "role",
        "conformal_group",
    )
    require_exact_grid(
        reference_coverage_slice,
        domains={
            "learner": COVERAGE_LEARNERS,
            "window_id": WINDOW_IDS,
            "taxonomy_groups": (5,),
            "role": COVERAGE_ROLES,
            "conformal_group": (-1,),
        },
        label="active V3 coverage reference",
    )
    require_exact_frame(
        lag6_coverage,
        reference_coverage_slice,
        keys=coverage_keys,
        label="endpoint lag-6 coverage",
    )

    lag6_two_ruler = (
        frames["two_ruler_window_contrasts"]
        .loc[frames["two_ruler_window_contrasts"]["charged_off_lag_months"].eq(6)]
        .drop(columns="charged_off_lag_months")
    )
    contrast_keys = ("window_id", "ruler", "coordinate")
    require_exact_frame(
        lag6_two_ruler,
        reference_two_ruler,
        keys=contrast_keys,
        label="endpoint lag-6 two-ruler contrasts",
    )

    lag6_envelopes = (
        frames["exact_support_envelopes"]
        .loc[frames["exact_support_envelopes"]["charged_off_lag_months"].eq(6)]
        .drop(columns="charged_off_lag_months")
    )
    envelope_keys = ("window_id", "paired_policy_id", "scope", "metric")
    require_exact_frame(
        lag6_envelopes,
        reference_envelopes,
        keys=envelope_keys,
        label="endpoint lag-6 exact-support envelopes",
    )
    reconciliation = {
        "charged_off_lag_months": 6,
        "coverage_cells_exact": int(len(lag6_coverage)),
        "two_ruler_contrasts_exact": int(len(lag6_two_ruler)),
        "exact_support_envelopes_exact": int(len(lag6_envelopes)),
        "byte_value_equal_after_lag_column_removed": True,
    }
    return EndpointSensitivityEvidence(
        summary=summary,
        frames=frames,
        reconciliation=reconciliation,
    )


def endpoint_publication_table(evidence: EndpointSensitivityEvidence) -> pd.DataFrame:
    """Derive one complete, nonselective paper row per endpoint lag."""
    census = evidence.frames["endpoint_census"]
    coverage = evidence.frames["coverage_cells"]
    directions = evidence.frames["two_ruler_directions"]
    support = evidence.frames["exact_support_envelopes"]
    rows: list[dict[str, Any]] = []
    for lag in ENDPOINT_LAGS:
        primary_census = census.loc[
            census["charged_off_lag_months"].eq(lag) & census["role"].eq("primary_oot")
        ]
        if len(primary_census) != 1:
            raise RuntimeError(f"Endpoint lag {lag} has no unique primary census.")
        primary_coverage = coverage.loc[
            coverage["charged_off_lag_months"].eq(lag) & coverage["role"].eq("primary_oot")
        ]
        if len(primary_coverage) != 40:
            raise RuntimeError(f"Endpoint lag {lag} has an incomplete primary coverage grid.")
        maximum = primary_coverage.loc[
            primary_coverage["coverage_upper"].eq(primary_coverage["coverage_upper"].max())
        ].sort_values(["learner", "window_id"])
        direction_counts = (
            directions.loc[directions["charged_off_lag_months"].eq(lag)]
            .groupby(["metric", "direction"], observed=True)
            .size()
            .to_dict()
        )
        support_counts = (
            support.loc[support["charged_off_lag_months"].eq(lag)]
            .groupby(["scope", "metric", "direction"], observed=True)
            .size()
            .to_dict()
        )
        census_row = primary_census.iloc[0]
        row: dict[str, Any] = {
            "charged_off_lag_months": lag,
            "primary_candidates": int(census_row["candidate_rows"]),
            "primary_resolved": int(census_row["resolved_rows"]),
            "primary_unresolved": int(census_row["unresolved_rows"]),
            "primary_defaults": int(census_row["default_rows"]),
            "coverage_cells": int(len(primary_coverage)),
            "coverage_upper_below_0_90_cells": int(
                primary_coverage["coverage_upper"].lt(0.90).sum()
            ),
            "coverage_upper_at_or_above_0_90_cells": int(
                primary_coverage["coverage_upper"].ge(0.90).sum()
            ),
            "coverage_upper_max": float(maximum["coverage_upper"].iloc[0]),
            "coverage_upper_max_learner": ";".join(maximum["learner"].astype(str)),
            "coverage_upper_max_window": ";".join(maximum["window_id"].astype(str)),
        }
        for metric in TWO_RULER_METRICS:
            prefix = {
                "standardized_payoff": "two_ruler_payoff",
                "funded_default": "two_ruler_default",
                "funded_binary_miscoverage": "two_ruler_miscoverage",
            }[metric]
            for direction in TWO_RULER_DIRECTIONS:
                row[f"{prefix}_{direction}_cells"] = int(
                    direction_counts.get((metric, direction), 0)
                )
        for metric in SUPPORT_METRICS:
            for scope in ("development_admissible_exact_frontier", "broad_stress_exact_frontier"):
                for direction in ("guardrail_lower", "guardrail_higher", "crosses_zero"):
                    key = f"{scope}_{metric}_{direction}_cells"
                    row[key] = int(support_counts.get((scope, metric, direction), 0))
        rows.append(row)
    return pd.DataFrame(rows)
