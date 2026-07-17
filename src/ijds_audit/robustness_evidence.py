"""Hash-verified fit-label and allocation-granularity evidence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from src.ijds_audit.grid_contracts import require_exact_frame, require_exact_grid, require_finite
from src.utils.artifact_descriptor import verified_artifact_path

WINDOW_IDS = (
    *(f"w{index:02d}_2012m{index:02d}_m{index + 5:02d}" for index in range(1, 8)),
    "w08_2012m08_2013m01",
)
FIT_LABEL_SCENARIOS = (
    "observed_only",
    "all_unavailable_nondefault",
    "all_unavailable_default",
    "hindsight_terminal",
)
FIT_EVALUATION_ARTIFACTS = ("coverage", "summary_table", "phase_stratum")
FIT_OUTCOME_FREE_ARTIFACTS = ("scores", "fit_audit", "scenario_audit", "recipes")
GRANULARITY_EVALUATION_ARTIFACTS = ("granularity_contrasts",)
GRANULARITY_OUTCOME_FREE_ARTIFACTS = (
    "rounded_allocations",
    "rounded_solve_records",
    "granularity_audit",
)
RULERS = ("objective_matched", "normalized_score")
COORDINATES = (0.25, 0.50, 0.75)
GAMMAS = (0.0, 1.0)
FIT_DESIGN_SPLITS = ("pd_development", "probability_calibration", "conformal_fit")


@dataclass(frozen=True)
class FitLabelCompletionEvidence:
    """Verified completion-scenario freeze, evaluation, and derived findings."""

    freeze: dict[str, Any]
    summary: dict[str, Any]
    frames: dict[str, pd.DataFrame]
    outcome_free_artifacts: dict[str, Path]
    evaluation_artifacts: dict[str, Path]
    findings: dict[str, Any]


@dataclass(frozen=True)
class AllocationGranularityEvidence:
    """Verified deterministic lot-rounding freeze, evaluation, and findings."""

    freeze: dict[str, Any]
    summary: dict[str, Any]
    frames: dict[str, pd.DataFrame]
    outcome_free_artifacts: dict[str, Path]
    evaluation_artifacts: dict[str, Path]
    findings: dict[str, Any]


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


def _require_no_side_effects(payload: Mapping[str, Any], *, label: str) -> None:
    if payload.get("outcome_based_selection") is not False:
        raise RuntimeError(f"{label} reports outcome-based selection.")
    if payload.get("protected_stages_run") != []:
        raise RuntimeError(f"{label} reports a protected-stage execution.")
    if payload.get("protected_artifacts_written") != []:
        raise RuntimeError(f"{label} reports a protected-artifact write.")


def _verified_inventory(
    raw: object,
    *,
    expected_names: tuple[str, ...],
    repo_root: Path,
    label: str,
) -> dict[str, Path]:
    if not isinstance(raw, Mapping) or set(raw) != set(expected_names):
        raise RuntimeError(f"{label} artifact inventory changed.")
    paths: dict[str, Path] = {}
    for name, descriptor in raw.items():
        if not isinstance(descriptor, Mapping):
            raise TypeError(f"{label} descriptor {name!r} is invalid.")
        paths[str(name)] = verified_artifact_path(
            cast(Mapping[str, Any], descriptor),
            repo_root=repo_root,
            label=f"{label} {name}",
        )
    return paths


def _require_summary_freeze_descriptor(
    summary: Mapping[str, Any],
    *,
    freeze_path: Path,
    repo_root: Path,
    label: str,
) -> None:
    descriptor = summary.get("freeze")
    if not isinstance(descriptor, Mapping):
        raise TypeError(f"{label} summary omits its freeze descriptor.")
    verified = verified_artifact_path(
        descriptor,
        repo_root=repo_root,
        label=f"{label} freeze",
    )
    if verified.resolve() != freeze_path.resolve():
        raise RuntimeError(f"{label} summary points to a different freeze.")


def _validate_fit_frames(frames: Mapping[str, pd.DataFrame]) -> dict[str, Any]:
    coverage = frames["coverage"]
    summary_table = frames["summary_table"]
    phase = frames["phase_stratum"]
    require_exact_grid(
        coverage,
        domains={
            "fit_label_scenario": FIT_LABEL_SCENARIOS,
            "window_id": WINDOW_IDS,
            "conformal_group": (-1, 2),
        },
        label="fit-label completion coverage",
    )
    require_exact_grid(
        phase,
        domains={
            "fit_label_scenario": FIT_LABEL_SCENARIOS,
            "window_id": WINDOW_IDS,
        },
        label="fit-label completion phase stratum",
    )
    if not phase["conformal_group"].eq(2).all():
        raise RuntimeError("Fit-label phase table is not restricted to conformal stratum 2.")
    require_exact_grid(
        summary_table,
        domains={"fit_label_scenario": FIT_LABEL_SCENARIOS},
        label="fit-label completion summary",
    )
    require_finite(
        coverage,
        (
            "candidate_rows",
            "resolved_rows",
            "unresolved_rows",
            "coverage_lower",
            "coverage_upper",
            "mean_width",
            "fit_prevalence",
            "fit_residual_quantile",
        ),
        label="fit-label completion coverage",
    )
    if not (
        coverage["candidate_rows"].eq(coverage["resolved_rows"] + coverage["unresolved_rows"]).all()
        and coverage["coverage_lower"].le(coverage["coverage_upper"]).all()
        and coverage[["coverage_lower", "coverage_upper"]].ge(0.0).all(axis=None)
        and coverage[["coverage_lower", "coverage_upper"]].le(1.0).all(axis=None)
    ):
        raise RuntimeError("Fit-label completion coverage bounds are incoherent.")
    overall = coverage.loc[coverage["conformal_group"].eq(-1)]
    derived = (
        overall.groupby("fit_label_scenario", observed=True, sort=True)
        .agg(
            windows=("window_id", "nunique"),
            coverage_lower_min=("coverage_lower", "min"),
            coverage_upper_max=("coverage_upper", "max"),
            windows_upper_below_nominal=(
                "coverage_upper",
                lambda values: int((values < 0.90).sum()),
            ),
            all_windows_upper_below_nominal=(
                "coverage_upper",
                lambda values: bool((values < 0.90).all()),
            ),
            mean_width_min=("mean_width", "min"),
            mean_width_max=("mean_width", "max"),
        )
        .reset_index()
    )
    require_exact_frame(
        summary_table,
        derived,
        keys=("fit_label_scenario",),
        label="fit-label completion derived summary",
    )
    crossing_by_scenario: dict[str, bool] = {}
    for scenario in FIT_LABEL_SCENARIOS:
        scoped = phase.loc[phase["fit_label_scenario"].eq(scenario)].set_index("window_id")
        w7 = scoped.loc["w07_2012m07_m12"]
        w8 = scoped.loc["w08_2012m08_2013m01"]
        crossing_by_scenario[scenario] = bool(
            float(w7["fit_prevalence"]) >= 0.10 > float(w8["fit_prevalence"])
            and float(w7["fit_residual_quantile"]) > 0.5
            and float(w8["fit_residual_quantile"]) < 0.5
        )
    return {
        "coverage_cells": int(len(overall)),
        "phase_cells": int(len(phase)),
        "all_scenarios_all_windows_upper_below_nominal": bool(
            summary_table["all_windows_upper_below_nominal"].all()
        ),
        "w7_w8_crossing_by_scenario": crossing_by_scenario,
        "w7_w8_crossing_scenarios": int(sum(crossing_by_scenario.values())),
        "w7_w8_crossing_in_all_scenarios": bool(all(crossing_by_scenario.values())),
    }


def _validate_fit_scenario_audit(frame: pd.DataFrame) -> dict[str, int]:
    require_exact_grid(
        frame,
        domains={"scenario": FIT_LABEL_SCENARIOS, "design_split": FIT_DESIGN_SPLITS},
        label="fit-label completion scenario audit",
    )
    require_finite(
        frame,
        (
            "rows",
            "source_available_rows",
            "source_unavailable_rows",
            "active_available_rows",
            "completed_rows",
            "source_available_prevalence",
            "active_prevalence",
        ),
        label="fit-label completion scenario audit",
    )
    if (
        not frame["rows"]
        .eq(frame["source_available_rows"] + frame["source_unavailable_rows"])
        .all()
    ):
        raise RuntimeError("Fit-label completion source-label census does not reconcile.")
    observed = frame.loc[frame["scenario"].eq("observed_only")]
    if not (
        observed["active_available_rows"].eq(observed["source_available_rows"]).all()
        and observed["completed_rows"].eq(0).all()
    ):
        raise RuntimeError("Observed-only fit-label scenario unexpectedly completes labels.")
    completed = frame.loc[~frame["scenario"].eq("observed_only")]
    if not (
        completed["active_available_rows"].eq(completed["rows"]).all()
        and completed["completed_rows"].eq(completed["source_unavailable_rows"]).all()
    ):
        raise RuntimeError("Fit-label completion scenarios do not fill every unavailable label.")
    counts = (
        frame.groupby("design_split", observed=True)["source_unavailable_rows"].nunique().to_dict()
    )
    if any(value != 1 for value in counts.values()):
        raise RuntimeError("Unavailable fit-label counts vary by completion scenario.")
    by_split = observed.set_index("design_split")["source_unavailable_rows"].astype(int).to_dict()
    return {str(key): int(value) for key, value in by_split.items()}


def load_fit_label_completion_evidence(
    summary_path: Path,
    *,
    freeze_path: Path,
    identity: Mapping[str, Any],
    repo_root: Path,
) -> FitLabelCompletionEvidence:
    """Load and verify the four declared fit-label scenarios."""
    freeze = _load_json_object(freeze_path, label="Fit-label completion freeze")
    summary = _load_json_object(summary_path, label="Fit-label completion summary")
    _require_identity(freeze, identity, label="Fit-label completion freeze")
    _require_identity(summary, identity, label="Fit-label completion summary")
    _require_no_side_effects(freeze, label="Fit-label completion freeze")
    _require_no_side_effects(summary, label="Fit-label completion summary")
    if freeze.get("status") != "fit_labels_completed_before_evaluation_outcome_join":
        raise RuntimeError("Fit-label completion freeze is incomplete.")
    if summary.get("status") != "complete_fit_label_completion_corner_sensitivity":
        raise RuntimeError("Fit-label completion evaluation is incomplete.")
    if tuple(freeze.get("scenarios", ())) != FIT_LABEL_SCENARIOS:
        raise RuntimeError("Fit-label completion freeze scenario order changed.")
    if tuple(summary.get("scenarios", ())) != FIT_LABEL_SCENARIOS:
        raise RuntimeError("Fit-label completion summary scenario order changed.")
    if freeze.get("evaluation_outcome_columns_passed_to_fitting") != []:
        raise RuntimeError("Fit-label completion freeze reports evaluation-outcome leakage.")
    _require_summary_freeze_descriptor(
        summary,
        freeze_path=freeze_path,
        repo_root=repo_root,
        label="Fit-label completion",
    )
    outcome_free = _verified_inventory(
        freeze.get("artifacts"),
        expected_names=FIT_OUTCOME_FREE_ARTIFACTS,
        repo_root=repo_root,
        label="Fit-label completion outcome-free",
    )
    evaluation = _verified_inventory(
        summary.get("artifacts"),
        expected_names=FIT_EVALUATION_ARTIFACTS,
        repo_root=repo_root,
        label="Fit-label completion evaluation",
    )
    frames = {name: pd.read_parquet(path) for name, path in evaluation.items()}
    findings = _validate_fit_frames(frames)
    unavailable_by_split = _validate_fit_scenario_audit(
        pd.read_parquet(outcome_free["scenario_audit"])
    )
    findings = {
        **findings,
        "unavailable_fit_labels_by_split": unavailable_by_split,
        "unavailable_fit_labels_total": int(sum(unavailable_by_split.values())),
    }
    results = summary.get("results")
    if not isinstance(results, Mapping):
        raise TypeError("Fit-label completion summary omits results.")
    if (
        int(results.get("coverage_rows", -1)) != 64
        or int(results.get("overall_cells", -1)) != findings["coverage_cells"]
        or int(results.get("phase_cells", -1)) != findings["phase_cells"]
        or results.get("all_scenarios_all_windows_upper_below_nominal")
        is not findings["all_scenarios_all_windows_upper_below_nominal"]
    ):
        raise RuntimeError("Fit-label completion top-level census changed.")
    return FitLabelCompletionEvidence(
        freeze=freeze,
        summary=summary,
        frames=frames,
        outcome_free_artifacts=outcome_free,
        evaluation_artifacts=evaluation,
        findings=findings,
    )


def fit_label_completion_publication_table(
    evidence: FitLabelCompletionEvidence,
) -> pd.DataFrame:
    """Return one complete, nonselective paper row per completion scenario."""
    table = evidence.frames["summary_table"].copy()
    crossing = evidence.findings["w7_w8_crossing_by_scenario"]
    table["w7_w8_stratum2_crossing"] = table["fit_label_scenario"].map(crossing)
    return table.sort_values("fit_label_scenario").reset_index(drop=True)


def _validate_granularity_frame(frame: pd.DataFrame) -> dict[str, Any]:
    require_exact_grid(
        frame,
        domains={
            "window_id": WINDOW_IDS,
            "frontier_ruler": RULERS,
            "frontier_coordinate": COORDINATES,
            "gamma": GAMMAS,
        },
        label="allocation granularity contrasts",
    )
    require_finite(
        frame,
        (
            "periods",
            "cash_residual_total",
            "cash_share",
            "policy_a_capital",
            "policy_b_capital",
            "policy_a_normalization_capital",
            "policy_b_normalization_capital",
            "realized_payoff_rate_difference_lower",
            "realized_payoff_rate_difference_upper",
            "weighted_default_difference_lower",
            "weighted_default_difference_upper",
            "weighted_miscoverage_difference_lower",
            "weighted_miscoverage_difference_upper",
        ),
        label="allocation granularity contrasts",
    )
    if not (
        frame["contrast"].eq("rounded_lot_minus_continuous").all()
        and frame["role"].eq("primary_oot").all()
        and frame["policy_a"].eq("rounded_lot").all()
        and frame["policy_b"].eq("continuous").all()
        and frame["periods"].eq(15).all()
        and frame["causal_interpretation"].eq(False).all()
    ):
        raise RuntimeError("Allocation granularity contrast semantics changed.")
    for lower, upper in (
        ("realized_payoff_rate_difference_lower", "realized_payoff_rate_difference_upper"),
        ("weighted_default_difference_lower", "weighted_default_difference_upper"),
        ("weighted_miscoverage_difference_lower", "weighted_miscoverage_difference_upper"),
    ):
        if not frame[lower].le(frame[upper]).all():
            raise RuntimeError(f"Allocation granularity bounds are reversed for {lower}.")
    if not np.isclose(frame["policy_a_normalization_capital"], 15_000_000.0).all():
        raise RuntimeError("Rounded policies are not normalized by committed capital.")
    if not np.isclose(frame["policy_b_normalization_capital"], 15_000_000.0).all():
        raise RuntimeError("Continuous policies are not normalized by committed capital.")
    return {
        "tracks": int(len(frame)),
        "cash_share_max": float(frame["cash_share"].max()),
        "payoff_rate_perturbation_abs_max": float(
            frame[
                [
                    "realized_payoff_rate_difference_lower",
                    "realized_payoff_rate_difference_upper",
                ]
            ]
            .abs()
            .to_numpy()
            .max()
        ),
        "default_rate_perturbation_abs_max": float(
            frame[["weighted_default_difference_lower", "weighted_default_difference_upper"]]
            .abs()
            .to_numpy()
            .max()
        ),
        "miscoverage_rate_perturbation_abs_max": float(
            frame[
                [
                    "weighted_miscoverage_difference_lower",
                    "weighted_miscoverage_difference_upper",
                ]
            ]
            .abs()
            .to_numpy()
            .max()
        ),
    }


def load_allocation_granularity_evidence(
    summary_path: Path,
    *,
    freeze_path: Path,
    identity: Mapping[str, Any],
    repo_root: Path,
) -> AllocationGranularityEvidence:
    """Load and verify the deterministic USD-25 lot-rounding sensitivity."""
    freeze = _load_json_object(freeze_path, label="Allocation granularity freeze")
    summary = _load_json_object(summary_path, label="Allocation granularity summary")
    _require_identity(freeze, identity, label="Allocation granularity freeze")
    _require_identity(summary, identity, label="Allocation granularity summary")
    _require_no_side_effects(freeze, label="Allocation granularity freeze")
    _require_no_side_effects(summary, label="Allocation granularity summary")
    if freeze.get("status") != "allocation_granularity_frozen_before_outcome_join":
        raise RuntimeError("Allocation granularity freeze is incomplete.")
    if summary.get("status") != "complete_allocation_granularity_sensitivity":
        raise RuntimeError("Allocation granularity evaluation is incomplete.")
    if freeze.get("outcome_columns_passed_to_rounding") != []:
        raise RuntimeError("Allocation rounding reports evaluation-outcome leakage.")
    if (
        freeze.get("rounding_rule") != "floor_each_exposure_hold_residual_as_cash"
        or float(freeze.get("lot_size_usd", -1.0)) != 25.0
        or float(freeze.get("committed_budget_usd", -1.0)) != 1_000_000.0
    ):
        raise RuntimeError("Allocation granularity rounding contract changed.")
    _require_summary_freeze_descriptor(
        summary,
        freeze_path=freeze_path,
        repo_root=repo_root,
        label="Allocation granularity",
    )
    outcome_free = _verified_inventory(
        freeze.get("artifacts"),
        expected_names=GRANULARITY_OUTCOME_FREE_ARTIFACTS,
        repo_root=repo_root,
        label="Allocation granularity outcome-free",
    )
    evaluation = _verified_inventory(
        summary.get("artifacts"),
        expected_names=GRANULARITY_EVALUATION_ARTIFACTS,
        repo_root=repo_root,
        label="Allocation granularity evaluation",
    )
    frames = {name: pd.read_parquet(path) for name, path in evaluation.items()}
    findings = _validate_granularity_frame(frames["granularity_contrasts"])
    results = summary.get("results")
    if not isinstance(results, Mapping):
        raise TypeError("Allocation granularity summary omits results.")
    for key, value in findings.items():
        if not np.isclose(float(results.get(key, np.nan)), float(value), rtol=0.0, atol=1e-15):
            raise RuntimeError(f"Allocation granularity summary changed on {key}.")
    freeze_results = freeze.get("results")
    if not isinstance(freeze_results, Mapping) or (
        int(freeze_results.get("portfolios", -1)) != 1440
        or int(freeze_results.get("source_rows", -1)) != 143_175
        or int(freeze_results.get("rounded_positive_rows", -1)) != 143_167
        or int(freeze_results.get("changed_rows", -1)) != 2_985
    ):
        raise RuntimeError("Allocation granularity outcome-free census changed.")
    findings = {
        **findings,
        "portfolios": int(freeze_results["portfolios"]),
        "source_rows": int(freeze_results["source_rows"]),
        "rounded_positive_rows": int(freeze_results["rounded_positive_rows"]),
        "changed_rows": int(freeze_results["changed_rows"]),
        "cash_residual_min": float(freeze_results["cash_residual_min"]),
        "cash_residual_mean": float(freeze_results["cash_residual_mean"]),
        "cash_residual_max": float(freeze_results["cash_residual_max"]),
        "monthly_cash_share_max": float(freeze_results["cash_share_max"]),
    }
    return AllocationGranularityEvidence(
        freeze=freeze,
        summary=summary,
        frames=frames,
        outcome_free_artifacts=outcome_free,
        evaluation_artifacts=evaluation,
        findings=findings,
    )


def allocation_granularity_publication_table(
    evidence: AllocationGranularityEvidence,
) -> pd.DataFrame:
    """Return one compact row for the complete deterministic rounding diagnostic."""
    return pd.DataFrame([evidence.findings])
