"""Build non-paper-facing evidence for the locked IJDS rolling-origin audit."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.evaluation.policy_contrast_bounds import sharp_policy_contrast_bounds
from src.ijds_audit.config import load_v4_config
from src.ijds_audit.evaluation import (
    build_archive_outcomes,
    comparator_envelopes,
    temporal_coverage_audit,
)
from src.ijds_audit.protocol import (
    expand_frontier_for_window,
    load_outcome_universe,
    load_recipes,
    verified_freeze_artifact_paths,
)
from src.utils.isolated_experiment import relative_artifact_descriptor
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_text

ROOT = Path(__file__).resolve().parents[1]
V4_CONFIG_PATH = ROOT / "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-12_v2.yaml"
ROLLING_CONFIG_PATH = ROOT / "configs/experiments/ijds_rolling_origin_2017_2026-07-12_v2.yaml"
V4_RUN = "ijds-binary-geometry-frontier-v4-2026-07-12-v2"
ROLLING_2015_RUN = "ijds-rolling-origin-2015-2026-07-12-v2"
ROLLING_2017_RUN = "ijds-rolling-origin-2017-2026-07-12-v2"
MODEL_ROOT = ROOT / "models/experiments/ijds_audit"
DATA_ROOT = ROOT / "data/processed/experiments/ijds_audit"
V4_SUMMARY_PATH = MODEL_ROOT / V4_RUN / "binary_geometry_frontier_v4_summary.json"
ROLLING_2015_FAILURE_PATH = MODEL_ROOT / ROLLING_2015_RUN / "freeze_failure_receipt.json"
ROLLING_2017_SUMMARY_PATH = (
    MODEL_ROOT / ROLLING_2017_RUN / "binary_geometry_frontier_v4_summary.json"
)
EVIDENCE_PATH = ROOT / "reports/crpto/ijds_rolling_origin_stability_evidence.json"
TABLE_DIR = ROOT / "reports/crpto/tables"
RESULTS_PATH = ROOT / "docs/research/ijds_rolling_origin_stability_results_2026-07-12.md"
COMMON_2016_PERIODS = ("2016-04", "2016-05", "2016-06")
COMMON_2017_PERIODS = ("2017-04", "2017-05", "2017-06")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a JSON object: {path}")
    return payload


def _verified_path(descriptor: Mapping[str, Any]) -> Path:
    path = (ROOT / str(descriptor["path"])).resolve()
    actual = relative_artifact_descriptor(path, repo_root=ROOT)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor[field]:
            raise RuntimeError(f"Rolling-origin source mismatch for {path}: {field}.")
    return path


def _window_index(identifier: str) -> int:
    match = re.fullmatch(r"w(\d{2})_.+", str(identifier))
    if match is None:
        raise ValueError(f"Unexpected residual-window id: {identifier}")
    return int(match.group(1))


def _primary_common_scores(scores: pd.DataFrame, periods: tuple[str, ...]) -> pd.DataFrame:
    result = scores.copy()
    issue_period = pd.to_datetime(result["issue_d"]).dt.to_period("M").astype(str)
    excluded = result["design_split"].eq("primary_oot") & ~issue_period.isin(periods)
    result.loc[excluded, "design_split"] = "outside_design"
    observed = set(issue_period.loc[result["design_split"].eq("primary_oot")])
    if observed != set(periods):
        raise RuntimeError(f"Common primary horizon mismatch: {sorted(observed)}")
    return result


def _canonical_coverage(frame: pd.DataFrame, *, origin: int) -> pd.DataFrame:
    result = frame.loc[
        frame["taxonomy_groups"].eq(5)
        & frame["role"].eq("primary_oot")
        & frame["conformal_group"].eq(-1)
    ].copy()
    if len(result) != 16:
        raise RuntimeError(f"Origin {origin} must contain 16 canonical coverage rows.")
    result.insert(0, "origin", int(origin))
    result.insert(1, "window_index", result["window_id"].map(_window_index))
    return result.sort_values(["origin", "learner", "window_index"]).reset_index(drop=True)


def _resolved_policy_metrics(allocations: pd.DataFrame, *, lgd: float) -> pd.DataFrame:
    """Aggregate a fully resolved allocation panel before forming policy pairs."""
    if allocations.empty:
        raise ValueError("Resolved allocation aggregation received no rows.")
    if bool(allocations["snapshot_default"].isna().any()):
        raise ValueError("Resolved allocation aggregation received censored outcomes.")
    outcome = allocations["snapshot_default"].to_numpy(dtype=float)
    if not bool(np.isin(outcome, [0.0, 1.0]).all()):
        raise ValueError("Resolved allocation outcomes must be binary.")
    exposure = allocations["exposure"].to_numpy(dtype=float)
    rate = allocations["contractual_rate"].to_numpy(dtype=float)
    lower = allocations["conformal_lower"].to_numpy(dtype=float)
    upper = allocations["conformal_upper"].to_numpy(dtype=float)
    work = allocations.assign(
        _capital=exposure,
        _payoff=exposure * np.where(outcome == 1.0, -float(lgd), rate),
        _default=exposure * outcome,
        _miscoverage=exposure * ((outcome < lower) | (outcome > upper)),
    )
    keys = ["window_id", "policy_label", "comparator_rule", "paired_policy_id"]
    result = (
        work.groupby(keys, observed=True, sort=True, dropna=False)
        .agg(
            frontier_cap=("frontier_cap", "first"),
            capital=("_capital", "sum"),
            payoff=("_payoff", "sum"),
            default_numerator=("_default", "sum"),
            miscoverage_numerator=("_miscoverage", "sum"),
        )
        .reset_index()
    )
    if bool(result["capital"].le(0.0).any()):
        raise RuntimeError("Every resolved policy must allocate positive capital.")
    result["default"] = result["default_numerator"] / result["capital"]
    result["miscoverage"] = result["miscoverage_numerator"] / result["capital"]
    return result


def _contrast_rows(guardrail: pd.DataFrame, comparator: pd.DataFrame) -> pd.DataFrame:
    frontier = comparator["comparator_rule"].eq("point_cap_frontier")
    if bool(frontier.all()):
        merged = guardrail.merge(
            comparator,
            on="window_id",
            suffixes=("_guardrail", "_point"),
            how="inner",
            validate="many_to_many",
        )
    elif not bool(frontier.any()):
        merged = guardrail.merge(
            comparator,
            on=["window_id", "paired_policy_id"],
            suffixes=("_guardrail", "_point"),
            how="inner",
            validate="one_to_many",
        )
    else:
        raise ValueError("Comparator metrics must be entirely named or entirely frontier rows.")
    paired = (
        merged["paired_policy_id_guardrail"]
        if "paired_policy_id_guardrail" in merged
        else merged["paired_policy_id"]
    )
    difference = {
        "realized_payoff_difference": merged["payoff_guardrail"] - merged["payoff_point"],
        "weighted_default_difference": merged["default_guardrail"] - merged["default_point"],
        "weighted_miscoverage_difference": (
            merged["miscoverage_guardrail"] - merged["miscoverage_point"]
        ),
    }
    return pd.DataFrame(
        {
            "window_id": merged["window_id"],
            "paired_policy_id": paired,
            "comparator_rule": merged["comparator_rule_point"],
            "frontier_cap": merged["frontier_cap_point"],
            **{
                f"{metric}_{bound}": values
                for metric, values in difference.items()
                for bound in ("lower", "upper")
            },
        }
    )


def _resolved_contrasts(metrics: pd.DataFrame) -> pd.DataFrame:
    guardrail = metrics.loc[metrics["comparator_rule"].eq("guardrail")]
    named = metrics.loc[~metrics["comparator_rule"].isin(["guardrail", "point_cap_frontier"])]
    frontier = metrics.loc[metrics["comparator_rule"].eq("point_cap_frontier")]
    if len(guardrail) != 72 or len(named) != 216 or frontier.empty:
        raise RuntimeError("Resolved metric family has an unexpected cardinality.")
    return pd.concat(
        [_contrast_rows(guardrail, named), _contrast_rows(guardrail, frontier)],
        ignore_index=True,
    )


def _assert_direct_contrast_match(
    direct_allocations: pd.DataFrame,
    contrast: pd.Series,
    *,
    guardrail_label: str,
    comparator_label: str,
    lgd: float,
) -> None:
    direct = sharp_policy_contrast_bounds(
        direct_allocations,
        policy_a=guardrail_label,
        policy_b=comparator_label,
        role="primary_oot",
        lgd=float(lgd),
    )
    pairs = (
        ("realized_payoff_difference_lower", "realized_payoff_difference_lower"),
        ("realized_payoff_difference_upper", "realized_payoff_difference_upper"),
        ("weighted_default_difference_lower", "weighted_default_difference_lower"),
        ("weighted_default_difference_upper", "weighted_default_difference_upper"),
        ("weighted_miscoverage_difference_lower", "weighted_miscoverage_difference_lower"),
        ("weighted_miscoverage_difference_upper", "weighted_miscoverage_difference_upper"),
    )
    for direct_name, vector_name in pairs:
        if not np.isclose(float(direct[direct_name]), float(contrast[vector_name]), atol=1e-12):
            raise RuntimeError(f"Resolved vector aggregation mismatch for {direct_name}.")


def _common_2016_envelopes(
    *,
    config: Mapping[str, Any],
    scores: pd.DataFrame,
    recipes: Mapping[str, Any],
    support: pd.DataFrame,
    named: pd.DataFrame,
    shared: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    lgd = float(config["payoff"]["lgd"])
    metric_parts = [_resolved_policy_metrics(named, lgd=lgd)]
    validation_expanded: pd.DataFrame | None = None
    for window_id, group_recipes in recipes["catboost_platt"].items():
        expanded = expand_frontier_for_window(
            shared,
            scores,
            group_recipes[5],
            window_id=window_id,
        )
        metric_parts.append(_resolved_policy_metrics(expanded, lgd=lgd))
        if validation_expanded is None:
            validation_expanded = expanded
    metrics = pd.concat(metric_parts, ignore_index=True)
    contrasts = _resolved_contrasts(metrics)
    frontier = config["comparators"]["exact_point_cap_frontier"]
    envelopes = comparator_envelopes(
        contrasts,
        support,
        broad_lower=float(frontier["start"]),
        broad_upper=float(frontier["stop"]),
    )

    first_window = str(support.sort_values(["window_id", "paired_policy_id"]).iloc[0]["window_id"])
    first_policy = str(
        support.loc[support["window_id"].eq(first_window)]
        .sort_values("paired_policy_id")
        .iloc[0]["paired_policy_id"]
    )
    guardrail_label = f"guardrail_{first_policy}"
    c0_label = f"c0_same_numeric_cap_{first_policy}"
    c0_row = contrasts.loc[
        contrasts["window_id"].eq(first_window)
        & contrasts["paired_policy_id"].eq(first_policy)
        & contrasts["comparator_rule"].eq("c0_same_numeric_cap")
    ].iloc[0]
    _assert_direct_contrast_match(
        named.loc[named["window_id"].eq(first_window)],
        c0_row,
        guardrail_label=guardrail_label,
        comparator_label=c0_label,
        lgd=lgd,
    )
    if validation_expanded is None:
        raise RuntimeError("Frontier validation sample is unavailable.")
    frontier_label = str(validation_expanded.sort_values("frontier_cap").iloc[0]["policy_label"])
    frontier_cap = float(
        validation_expanded.loc[
            validation_expanded["policy_label"].eq(frontier_label), "frontier_cap"
        ].iloc[0]
    )
    frontier_row = contrasts.loc[
        contrasts["window_id"].eq(first_window)
        & contrasts["paired_policy_id"].eq(first_policy)
        & contrasts["comparator_rule"].eq("point_cap_frontier")
        & np.isclose(contrasts["frontier_cap"], frontier_cap, atol=1e-12)
    ].iloc[0]
    direct_frontier = pd.concat(
        [
            named.loc[
                named["window_id"].eq(first_window) & named["policy_label"].eq(guardrail_label)
            ],
            validation_expanded.loc[validation_expanded["policy_label"].eq(frontier_label)],
        ],
        ignore_index=True,
    )
    _assert_direct_contrast_match(
        direct_frontier,
        frontier_row,
        guardrail_label=guardrail_label,
        comparator_label=frontier_label,
        lgd=lgd,
    )
    return contrasts, envelopes


def _coverage_summary(coverage: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (origin, learner), frame in coverage.groupby(
        ["origin", "learner"], observed=True, sort=True
    ):
        rows.append(
            {
                "origin": int(origin),
                "learner": str(learner),
                "candidate_rows": int(frame["candidate_rows"].iloc[0]),
                "resolved_rows": int(frame["resolved_rows"].iloc[0]),
                "unresolved_rows": int(frame["unresolved_rows"].iloc[0]),
                "coverage_resolved_min": float(frame["coverage_resolved"].min()),
                "coverage_resolved_max": float(frame["coverage_resolved"].max()),
                "coverage_lower_min": float(frame["coverage_lower"].min()),
                "coverage_upper_max": float(frame["coverage_upper"].max()),
                "all_eight_upper_below_nominal": bool(frame["coverage_upper"].lt(0.90).all()),
            }
        )
    return rows


def _direction_summary(envelopes: pd.DataFrame) -> list[dict[str, Any]]:
    result = (
        envelopes.groupby(["origin", "scope", "metric", "direction"], observed=True, sort=True)
        .size()
        .rename("cells")
        .reset_index()
    )
    return result.to_dict(orient="records")


def _c2_diagnostics(monthly: pd.DataFrame, *, origin: int) -> dict[str, Any]:
    c2 = monthly.loc[monthly["comparator_rule"].eq("c2_contemporaneous")]
    if len(c2) != 216:
        raise RuntimeError(f"Origin {origin} must contain 216 common-horizon C2 cells.")
    return {
        "origin": int(origin),
        "cells": int(len(c2)),
        "all_optimal": bool(c2["solver_status"].eq("Optimal").all()),
        "minimum_total_allocated": float(c2["total_allocated"].min()),
        "point_minus_guardrail_objective_min": float(c2["point_minus_guardrail_objective"].min()),
        "point_minus_guardrail_objective_max": float(c2["point_minus_guardrail_objective"].max()),
        "c2_match_residual_abs_max": float(c2["c2_match_residual"].abs().max()),
    }


def _render_results(evidence: Mapping[str, Any]) -> str:
    summaries = {
        (int(row["origin"]), str(row["learner"])): row for row in evidence["coverage"]["summaries"]
    }
    directions = pd.DataFrame(evidence["portfolio"]["direction_counts"])

    def coverage_line(origin: int, learner: str) -> str:
        row = summaries[(origin, learner)]
        return (
            f"{row['coverage_resolved_min']:.6f}--{row['coverage_resolved_max']:.6f} "
            f"resolved; bounds {row['coverage_lower_min']:.6f}--"
            f"{row['coverage_upper_max']:.6f}"
        )

    development = directions.loc[directions["scope"].eq("development_admissible_exact_frontier")]
    lines = [
        "# IJDS Rolling-Origin Stability Results",
        "",
        "## Status",
        "",
        "This is a locked retrospective robustness audit, not a new active claim registry,",
        "prospective validation, or submission freeze.",
        "",
        "## Feasibility",
        "",
        "The 2015 origin is infeasible under the unchanged five-stratum Mondrian",
        "requirement. Its first residual window has group counts",
        "`(1648, 1408, 1166, 927, 619)` against a minimum of 1,000. The protocol",
        "was not relaxed, and no 2015 outcome join occurred.",
        "",
        "## Common-Horizon Coverage",
        "",
        f"- 2016 CatBoost/Platt: {coverage_line(2016, 'catboost_platt')}.",
        f"- 2016 logistic/Platt: {coverage_line(2016, 'numeric_logistic_platt')}.",
        f"- 2017 CatBoost/Platt: {coverage_line(2017, 'catboost_platt')}.",
        f"- 2017 logistic/Platt: {coverage_line(2017, 'numeric_logistic_platt')}.",
        "",
        "Every upper bound is below 0.90 in both feasible origins and all eight",
        "windows. This is recurrence across two fitted origins, not three-origin",
        "stability, because the 2015 design is infeasible.",
        "",
        "## Comparator Identification",
        "",
        "Development-supported envelope direction counts:",
        "",
        "| Origin | Metric | Guardrail lower | Crosses zero | Guardrail higher |",
        "|---:|---|---:|---:|---:|",
    ]
    for (origin, metric), frame in development.groupby(["origin", "metric"], sort=True):
        counts = dict(zip(frame["direction"], frame["cells"], strict=True))
        lines.append(
            f"| {int(origin)} | {metric} | {int(counts.get('guardrail_lower', 0))} | "
            f"{int(counts.get('crosses_zero', 0))} | "
            f"{int(counts.get('guardrail_higher', 0))} |"
        )
    lines.extend(
        [
            "",
            "No metric has one identified direction in every window-policy cell at either",
            "origin. The rolling audit therefore strengthens comparator dependence and does",
            "not revive a policy-winner claim.",
            "",
            "## Simulation Audit",
            "",
            f"The inherited factorial has {evidence['simulation']['repetitions']:,} repetitions,",
            f"but same-cap allocations change in only "
            f"{evidence['simulation']['same_cap_nonzero_allocation_repetitions']} and C2",
            f"allocations in only {evidence['simulation']['c2_nonzero_allocation_repetitions']}.",
            "The guardrail score cap is slack in every repetition. The block remains useful",
            "for binary coverage geometry but is decision-degenerate and cannot support a",
            "portfolio claim.",
            "",
            "## Consequence",
            "",
            "The result supports a stronger audit narrative: below-target candidate coverage",
            "recurs under two feasible calendar origins, feasibility itself is origin-dependent,",
            "and portfolio direction remains comparator-dependent. It does not establish",
            "selected-set validity, universal temporal failure, or guardrail superiority.",
            "",
        ]
    )
    return "\n".join(lines)


def build_evidence() -> Path:
    v4_config = load_v4_config(V4_CONFIG_PATH)
    rolling_config = load_v4_config(ROLLING_CONFIG_PATH)
    failure = _read_json(ROLLING_2015_FAILURE_PATH)
    if failure.get("status") != "protocol_phase_failed_without_result_adaptation":
        raise RuntimeError("The 2015 protocol failure receipt is invalid.")
    if failure.get("protocol_details", {}).get("group_counts") != [1648, 1408, 1166, 927, 619]:
        raise RuntimeError("The locked 2015 feasibility counts changed.")

    v4_summary = _read_json(V4_SUMMARY_PATH)
    rolling_summary = _read_json(ROLLING_2017_SUMMARY_PATH)
    if v4_summary.get("status") != "complete_retrospective_binary_geometry_frontier_audit":
        raise RuntimeError("V4 source summary is incomplete.")
    if rolling_summary.get("status") != "complete_retrospective_binary_geometry_frontier_audit":
        raise RuntimeError("The 2017 rolling-origin summary is incomplete.")
    v4_artifacts = {
        name: _verified_path(descriptor) for name, descriptor in v4_summary["artifacts"].items()
    }
    rolling_artifacts = {
        name: _verified_path(descriptor)
        for name, descriptor in rolling_summary["artifacts"].items()
    }
    v4_freeze_path = _verified_path(v4_summary["outcome_free_freeze"])
    rolling_freeze_path = _verified_path(rolling_summary["outcome_free_freeze"])
    v4_freeze = _read_json(v4_freeze_path)
    rolling_freeze = _read_json(rolling_freeze_path)
    if v4_freeze.get("outcome_columns_passed_to_policy_or_comparator") != []:
        raise RuntimeError("V4 freeze reports outcome leakage.")
    if rolling_freeze.get("outcome_columns_passed_to_policy_or_comparator") != []:
        raise RuntimeError("2017 freeze reports outcome leakage.")
    v4_sources = verified_freeze_artifact_paths(v4_freeze, repo_root=ROOT)

    scores = pd.read_parquet(v4_sources["scores"])
    common_scores = _primary_common_scores(scores, COMMON_2016_PERIODS)
    recipes = load_recipes(v4_sources["recipes"])
    fit_audit = pd.read_parquet(v4_sources["fit_audit"])
    universe = load_outcome_universe(
        v4_config,
        raw_path=(ROOT / str(v4_config["source"]["raw_path"])).resolve(),
    )
    outcomes = build_archive_outcomes(universe)
    coverage_2016_all = temporal_coverage_audit(
        common_scores,
        outcomes,
        recipes,
        fit_audit,
        roles=("primary_oot",),
        taxonomy_group_counts=(5,),
        strata=(-1,),
    )
    coverage_2016 = _canonical_coverage(coverage_2016_all, origin=2016)
    coverage_2017 = _canonical_coverage(
        pd.read_parquet(rolling_artifacts["temporal_coverage"]), origin=2017
    )
    coverage = pd.concat([coverage_2016, coverage_2017], ignore_index=True)

    named_2016 = pd.read_parquet(
        v4_artifacts["funded_allocations_with_outcomes"],
        filters=[("role", "==", "primary_oot"), ("period", "in", COMMON_2016_PERIODS)],
    )
    shared_2016 = pd.read_parquet(
        v4_artifacts["shared_frontier_allocations_with_outcomes"],
        filters=[("period", "in", COMMON_2016_PERIODS)],
    )
    if bool(named_2016["snapshot_default"].isna().any()) or bool(
        shared_2016["snapshot_default"].isna().any()
    ):
        raise RuntimeError("The 2016 exact aggregation requires fully resolved funded unions.")
    support = pd.read_parquet(v4_sources["comparator_support"])
    contrasts_2016, envelopes_2016 = _common_2016_envelopes(
        config=v4_config,
        scores=common_scores,
        recipes=recipes,
        support=support,
        named=named_2016,
        shared=shared_2016,
    )
    envelopes_2016.insert(0, "origin", 2016)
    envelopes_2017 = pd.read_parquet(rolling_artifacts["comparator_envelopes"]).copy()
    envelopes_2017.insert(0, "origin", 2017)
    envelopes = pd.concat([envelopes_2016, envelopes_2017], ignore_index=True)
    envelopes.insert(1, "window_index", envelopes["window_id"].map(_window_index))

    monthly_2016 = pd.read_parquet(
        v4_artifacts["monthly_evaluation"],
        filters=[("role", "==", "primary_oot"), ("period", "in", COMMON_2016_PERIODS)],
    )
    monthly_2017 = pd.read_parquet(
        rolling_artifacts["monthly_evaluation"],
        filters=[("role", "==", "primary_oot"), ("period", "in", COMMON_2017_PERIODS)],
    )
    c2 = [_c2_diagnostics(monthly_2016, origin=2016), _c2_diagnostics(monthly_2017, origin=2017)]

    simulation_2016 = pd.read_parquet(v4_artifacts["simulation_repetitions"])
    simulation_2017 = pd.read_parquet(rolling_artifacts["simulation_repetitions"])
    pd.testing.assert_frame_equal(simulation_2016, simulation_2017, check_exact=True)
    simulation = simulation_2016
    simulation_cap = float(v4_config["simulation"]["mechanism_policy"]["risk_tolerance"])

    coverage_columns = [
        "origin",
        "window_index",
        "learner",
        "window_id",
        "candidate_rows",
        "resolved_rows",
        "unresolved_rows",
        "coverage_resolved",
        "coverage_lower",
        "coverage_upper",
        "fit_prevalence",
        "fit_residual_quantile",
        "set_empty_share",
        "set_both_share",
    ]
    direction_counts = pd.DataFrame(_direction_summary(envelopes))
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    coverage_path = atomic_write_text(
        TABLE_DIR / "crpto_ijds_rolling_origin_coverage.csv",
        coverage[coverage_columns].to_csv(index=False, lineterminator="\n"),
    )
    envelope_path = atomic_write_text(
        TABLE_DIR / "crpto_ijds_rolling_origin_envelopes.csv",
        envelopes.sort_values(
            ["origin", "scope", "metric", "window_index", "paired_policy_id"]
        ).to_csv(index=False, lineterminator="\n"),
    )
    direction_path = atomic_write_text(
        TABLE_DIR / "crpto_ijds_rolling_origin_direction_counts.csv",
        direction_counts.to_csv(index=False, lineterminator="\n"),
    )

    source_paths = {
        "v4_summary": V4_SUMMARY_PATH,
        "v4_freeze": v4_freeze_path,
        "v4_scores": v4_sources["scores"],
        "v4_recipes": v4_sources["recipes"],
        "v4_fit_audit": v4_sources["fit_audit"],
        "v4_comparator_support": v4_sources["comparator_support"],
        "v4_named_allocations_with_outcomes": v4_artifacts["funded_allocations_with_outcomes"],
        "v4_shared_frontier_with_outcomes": v4_artifacts[
            "shared_frontier_allocations_with_outcomes"
        ],
        "v4_monthly_evaluation": v4_artifacts["monthly_evaluation"],
        "v4_simulation": v4_artifacts["simulation_repetitions"],
        "rolling_2015_failure": ROLLING_2015_FAILURE_PATH,
        "rolling_2017_summary": ROLLING_2017_SUMMARY_PATH,
        "rolling_2017_freeze": rolling_freeze_path,
        "rolling_2017_coverage": rolling_artifacts["temporal_coverage"],
        "rolling_2017_envelopes": rolling_artifacts["comparator_envelopes"],
        "rolling_2017_monthly_evaluation": rolling_artifacts["monthly_evaluation"],
        "rolling_2017_simulation": rolling_artifacts["simulation_repetitions"],
    }
    implementation_paths = {
        "builder": Path(__file__).resolve(),
        "v4_config": V4_CONFIG_PATH,
        "rolling_2017_config": ROLLING_CONFIG_PATH,
        "coverage_and_envelopes": ROOT / "src/ijds_audit/evaluation.py",
        "protocol_artifact_loading": ROOT / "src/ijds_audit/protocol.py",
        "sharp_contrast_bounds": ROOT / "src/evaluation/policy_contrast_bounds.py",
        "rolling_protocol": (
            ROOT / "docs/research/ijds_rolling_origin_stability_protocol_2026-07-12.md"
        ),
        "rolling_v2_erratum": (
            ROOT / "docs/research/ijds_rolling_origin_stability_v2_erratum_2026-07-12.md"
        ),
    }
    coverage_summaries = _coverage_summary(coverage)
    universally_identified = []
    for (origin, scope, metric), frame in envelopes.groupby(
        ["origin", "scope", "metric"], observed=True, sort=True
    ):
        directions = set(frame["direction"].astype(str))
        universally_identified.append(
            {
                "origin": int(origin),
                "scope": str(scope),
                "metric": str(metric),
                "one_nonzero_direction_in_all_72_cells": bool(
                    len(frame) == 72 and len(directions) == 1 and "crosses_zero" not in directions
                ),
            }
        )
    evidence: dict[str, Any] = {
        "schema_version": "2026-07-12.1",
        "status": "retrospective_prefreeze_rolling_origin_audit_evidence",
        "protocol_tag": str(rolling_config["protocol_tag"]),
        "protocol_commit": str(rolling_summary["protocol_commit"]),
        "claim_boundary": {
            "active_claim_registry_replaced": False,
            "confirmatory": False,
            "prospective": False,
            "causal": False,
            "selected_set_validity": False,
            "policy_winner": False,
            "three_origin_stability": False,
        },
        "design": {
            "declared_origins": [2015, 2016, 2017],
            "common_primary_months_per_origin": 3,
            "origin_2015_status": "protocol_feasibility_failure_before_outcome_join",
            "origin_2016_status": "verified_v4_freeze_mechanically_restricted_to_april_june",
            "origin_2017_status": "complete_tagged_freeze_and_evaluation",
            "residual_windows_per_feasible_origin": 8,
            "learners": 2,
            "policies": 9,
            "comparator_envelopes_per_origin": 648,
        },
        "feasibility": {
            "origin_2015": dict(failure["protocol_details"]),
            "threshold_relaxed": False,
            "outcome_join_performed": False,
        },
        "coverage": {
            "three_origin_stability_assessable": False,
            "three_origin_stability_failure_reason": "2015_locked_design_infeasible",
            "both_feasible_origins_all_32_upper_bounds_below_nominal": bool(
                coverage["coverage_upper"].lt(0.90).all()
            ),
            "summaries": coverage_summaries,
            "rows": coverage[coverage_columns].to_dict(orient="records"),
        },
        "portfolio": {
            "common_2016_contrasts": int(len(contrasts_2016)),
            "envelopes_per_origin": 648,
            "direction_counts": direction_counts.to_dict(orient="records"),
            "universal_direction_checks": universally_identified,
            "every_scope_metric_lacks_one_direction_in_all_cells": bool(
                not any(
                    row["one_nonzero_direction_in_all_72_cells"] for row in universally_identified
                )
            ),
            "c2": c2,
        },
        "simulation": {
            "scope": "coverage_mechanism_only_decision_component_degenerate",
            "repetitions": int(len(simulation)),
            "cells": int(
                simulation[["score_shift", "prevalence_shift", "taxonomy_groups", "censoring_rate"]]
                .drop_duplicates()
                .shape[0]
            ),
            "guardrail_cap": simulation_cap,
            "guardrail_cap_binding_repetitions": int(
                np.isclose(
                    simulation["guardrail_weighted_effective_score"],
                    simulation_cap,
                    atol=1e-10,
                ).sum()
            ),
            "minimum_guardrail_cap_slack": float(
                simulation_cap - simulation["guardrail_weighted_effective_score"].max()
            ),
            "same_cap_nonzero_allocation_repetitions": int(
                simulation["same_cap_allocation_distance"].gt(1e-12).sum()
            ),
            "c2_nonzero_allocation_repetitions": int(
                simulation["c2_allocation_distance"].gt(1e-12).sum()
            ),
            "same_cap_allocation_distance_max": float(
                simulation["same_cap_allocation_distance"].max()
            ),
            "c2_allocation_distance_max": float(simulation["c2_allocation_distance"].max()),
            "rolling_and_v4_outputs_exactly_equal": True,
            "portfolio_claim_allowed": False,
        },
        "interpretation": {
            "positive_policy_claim_supported": False,
            "selected_set_claim_supported": False,
            "universal_temporal_failure_claim_supported": False,
            "below_nominal_bounds_recur_in_both_feasible_origins": True,
            "comparator_dependence_recurred": True,
            "recommended_role": "secondary_stability_evidence_for_the_v4_audit_narrative",
        },
        "source_artifacts": {
            name: relative_artifact_descriptor(path, repo_root=ROOT)
            for name, path in source_paths.items()
        },
        "aggregation_implementation": {
            name: relative_artifact_descriptor(path, repo_root=ROOT)
            for name, path in implementation_paths.items()
        },
        "derived_artifacts": {},
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    results_path = atomic_write_text(RESULTS_PATH, _render_results(evidence))
    evidence["derived_artifacts"] = {
        "coverage_table": relative_artifact_descriptor(coverage_path, repo_root=ROOT),
        "envelopes": relative_artifact_descriptor(envelope_path, repo_root=ROOT),
        "direction_counts": relative_artifact_descriptor(direction_path, repo_root=ROOT),
        "results_memo": relative_artifact_descriptor(results_path, repo_root=ROOT),
    }
    return atomic_write_json(EVIDENCE_PATH, evidence)


def main() -> None:
    print(build_evidence())


if __name__ == "__main__":
    main()
