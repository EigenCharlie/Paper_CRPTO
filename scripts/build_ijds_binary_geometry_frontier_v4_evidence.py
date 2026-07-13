"""Build the single paper-facing IJDS V4 evidence package."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from loguru import logger

from src.ijds_audit.config import load_v4_config
from src.utils.isolated_experiment import relative_artifact_descriptor
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_text

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-12_v2.yaml"
MODEL_DIR = ROOT / "models/experiments/ijds_audit/ijds-binary-geometry-frontier-v4-2026-07-12-v2"
SUMMARY_PATH = MODEL_DIR / "binary_geometry_frontier_v4_summary.json"
V2_MODEL_DIR = (
    ROOT / "models/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v2"
)
V2_MANIFEST_PATH = V2_MODEL_DIR / "verified_evaluation_manifest.json"
V2_MANIFEST_DESCRIPTOR = {
    "path": (
        "models/experiments/ijds_audit/"
        "ijds-normalized-objective-frontier-2026-07-13-v2/verified_evaluation_manifest.json"
    ),
    "bytes": 16325,
    "sha256": "d3808ce7c7a8e6fee3ef51aefd031e8abf55e11ef3536745ee213fd04752588a",
}
EVIDENCE_PATH = ROOT / "reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json"
TABLE_DIR = ROOT / "reports/crpto/tables"
FIGURE_DIR = ROOT / "reports/crpto/figures"

BLUE = "#2F6690"
ORANGE = "#D97706"
GOLD = "#C8A951"
INK = "#20262E"
MID = "#6B7280"
LIGHT = "#E5E7EB"


def _verified_path(descriptor: Mapping[str, Any]) -> Path:
    path = (ROOT / str(descriptor["path"])).resolve()
    actual = relative_artifact_descriptor(path, repo_root=ROOT)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor[field]:
            raise RuntimeError(f"Paper-facing artifact mismatch for {path}: {field}.")
    return path


def _direction_pattern(directions: pd.DataFrame, metric: str) -> str:
    counts = directions.loc[directions["metric"].eq(metric), "direction"].value_counts()
    order = ("gamma_1_higher", "gamma_1_lower", "crosses_zero", "exact_zero")
    return ";".join(f"{name}:{int(counts[name])}" for name in order if name in counts)


def _two_ruler_track_table(
    window_contrasts: pd.DataFrame,
    directions: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    ruler_order = {"objective_matched": 0, "normalized_score": 1}
    for group_key, frame in window_contrasts.groupby(
        ["ruler", "coordinate"], observed=True, sort=True
    ):
        if not isinstance(group_key, tuple) or len(group_key) != 2:
            raise RuntimeError("Unexpected two-ruler group key.")
        ruler, coordinate = group_key
        coordinate_value = float(cast(Any, coordinate))
        scoped = directions.loc[
            directions["ruler"].eq(ruler) & directions["coordinate"].eq(coordinate)
        ]
        rows.append(
            {
                "ruler": str(ruler),
                "coordinate": coordinate_value,
                "ruler_semantics": (
                    "common_plugin_objective_floor"
                    if str(ruler) == "objective_matched"
                    else "common_relative_score_relaxation"
                ),
                "window_cells": int(len(frame)),
                "active_months_per_window_min": int(frame["nonidentical_months"].min()),
                "active_months_per_window_max": int(frame["nonidentical_months"].max()),
                "expected_objective_difference_usd_min": float(
                    frame["expected_objective_difference"].min()
                ),
                "expected_objective_difference_usd_max": float(
                    frame["expected_objective_difference"].max()
                ),
                "payoff_bound_usd_lower_min": float(
                    frame["realized_payoff_difference_lower"].min()
                ),
                "payoff_bound_usd_upper_max": float(
                    frame["realized_payoff_difference_upper"].max()
                ),
                "default_bound_pp_lower_min": float(
                    100.0 * frame["weighted_default_difference_lower"].min()
                ),
                "default_bound_pp_upper_max": float(
                    100.0 * frame["weighted_default_difference_upper"].max()
                ),
                "miscoverage_bound_pp_lower_min": float(
                    100.0 * frame["weighted_miscoverage_difference_lower"].min()
                ),
                "miscoverage_bound_pp_upper_max": float(
                    100.0 * frame["weighted_miscoverage_difference_upper"].max()
                ),
                "payoff_direction_pattern": _direction_pattern(scoped, "standardized_payoff"),
                "default_direction_pattern": _direction_pattern(scoped, "funded_default"),
                "miscoverage_direction_pattern": _direction_pattern(
                    scoped, "funded_binary_miscoverage"
                ),
            }
        )
    table = pd.DataFrame(rows)
    table["_ruler_order"] = table["ruler"].map(ruler_order)
    return table.sort_values(["_ruler_order", "coordinate"]).drop(columns="_ruler_order")


def _objective_quarter_repetition(joined: pd.DataFrame) -> dict[str, Any]:
    labels = ("objective_matched_g100_c025", "objective_matched_g000_c025")
    scoped = joined.loc[joined["role"].eq("primary_oot") & joined["policy_label"].isin(labels)]
    audits: list[dict[str, Any]] = []
    reference: pd.DataFrame | None = None
    identical_to_cents = True
    for window_id, frame in scoped.groupby("window_id", observed=True, sort=True):
        exposures = (
            frame.pivot(index=["period", "id"], columns="policy_label", values="exposure")
            .fillna(0.0)
            .sort_index()
        )
        delta = exposures[labels[0]] - exposures[labels[1]]
        rounded = exposures[list(labels)].round(2)
        if reference is None:
            reference = rounded
        else:
            identical_to_cents = bool(identical_to_cents and rounded.equals(reference))
        audits.append(
            {
                "window_id": str(window_id),
                "changed_loan_month_positions": int(delta.abs().gt(1.0e-8).sum()),
                "one_way_turnover_usd": float(delta.abs().sum() / 2.0),
            }
        )
    audit = pd.DataFrame(audits)
    return {
        "allocations_identical_across_windows_to_cents": identical_to_cents,
        "changed_loan_month_positions_min": int(audit["changed_loan_month_positions"].min()),
        "changed_loan_month_positions_max": int(audit["changed_loan_month_positions"].max()),
        "one_way_turnover_usd_min": float(audit["one_way_turnover_usd"].min()),
        "one_way_turnover_usd_max": float(audit["one_way_turnover_usd"].max()),
    }


def _write_csv(frame: pd.DataFrame, path: Path) -> Path:
    return atomic_write_text(path, frame.to_csv(index=False, lineterminator="\n"))


def _direction(lower: pd.Series, upper: pd.Series) -> pd.Series:
    return pd.Series(
        np.where(
            lower > 0.0,
            "guardrail_higher",
            np.where(upper < 0.0, "guardrail_lower", "crosses_zero"),
        ),
        index=lower.index,
        dtype="string",
    )


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "axes.edgecolor": MID,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "text.color": INK,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.grid": True,
            "grid.color": LIGHT,
            "grid.linewidth": 0.7,
            "grid.alpha": 0.8,
            "legend.frameon": False,
        }
    )


def _save_figure(figure: plt.Figure, stem: str) -> dict[str, Path]:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    png = FIGURE_DIR / f"{stem}.png"
    pdf = FIGURE_DIR / f"{stem}.pdf"
    figure.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    figure.savefig(
        pdf,
        bbox_inches="tight",
        facecolor="white",
        metadata={"CreationDate": None, "ModDate": None},
    )
    plt.close(figure)
    return {"png": png, "pdf": pdf}


def _coverage_figure(coverage: pd.DataFrame) -> dict[str, Path]:
    _style()
    figure, axis = plt.subplots(figsize=(7.2, 3.7))
    labels = [f"W{index}" for index in range(1, 9)]
    x = np.arange(8, dtype=float)
    specifications = (
        ("catboost_platt", "CatBoost + Platt", BLUE, "o", -0.08),
        ("numeric_logistic_platt", "Logistic + Platt", ORANGE, "s", 0.08),
    )
    for learner, label, color, marker, offset in specifications:
        frame = coverage.loc[coverage["learner"].eq(learner)].sort_values("window_id")
        center = frame["coverage_resolved"].to_numpy(dtype=float)
        lower = frame["coverage_lower"].to_numpy(dtype=float)
        upper = frame["coverage_upper"].to_numpy(dtype=float)
        axis.errorbar(
            x + offset,
            center,
            yerr=np.vstack([center - lower, upper - center]),
            color=color,
            marker=marker,
            markersize=4.5,
            linewidth=1.4,
            capsize=2.5,
            label=label,
        )
    axis.axhline(0.90, color=INK, linestyle="--", linewidth=1.1, label="Nominal 0.90")
    axis.set_xticks(x, labels)
    axis.set_ylim(0.83, 0.905)
    axis.set_ylabel("Coverage")
    axis.set_xlabel("Six-month residual window (W1 = Jan-Jun 2012; W8 = Aug 2012-Jan 2013)")
    axis.set_title("Primary OOT binary-outcome coverage across the complete window specification")
    axis.legend(ncol=3, loc="lower left")
    axis.spines[["top", "right"]].set_visible(False)
    figure.tight_layout()
    return _save_figure(figure, "crpto_ijds_v4_fig1_coverage")


def _phase_figure(phase: pd.DataFrame) -> dict[str, Path]:
    _style()
    frame = phase.sort_values("window_id")
    x = np.arange(len(frame), dtype=float)
    labels = [f"W{index}" for index in range(1, 9)]
    figure, axes = plt.subplots(1, 2, figsize=(7.2, 3.35), sharex=True)
    axes[0].plot(x, frame["fit_prevalence"], color=BLUE, marker="o", linewidth=1.5)
    axes[0].axhline(0.10, color=INK, linestyle="--", linewidth=1.1, label=r"$\alpha=0.10$")
    axes[0].set_ylabel("Fit default prevalence")
    axes[0].set_title("Stratum-2 prevalence")
    axes[0].legend(loc="lower left")
    axes[1].plot(
        x,
        frame["fit_residual_quantile"],
        color=GOLD,
        marker="s",
        linewidth=1.5,
    )
    axes[1].set_ylabel("Residual quantile")
    axes[1].set_title("Applied conformal quantile")
    for axis in axes:
        axis.set_xticks(x, labels)
        axis.set_xlabel("Residual window")
        axis.spines[["top", "right"]].set_visible(False)
    axes[0].annotate(
        "W7: 0.1017",
        xy=(6, float(frame.iloc[6]["fit_prevalence"])),
        xytext=(4.6, 0.111),
        arrowprops={"arrowstyle": "-", "color": MID},
        fontsize=8,
    )
    axes[0].annotate(
        "W8: 0.0971",
        xy=(7, float(frame.iloc[7]["fit_prevalence"])),
        xytext=(5.5, 0.0975),
        arrowprops={"arrowstyle": "-", "color": MID},
        fontsize=8,
    )
    axes[1].annotate(
        "0.8884 to 0.1118",
        xy=(7, float(frame.iloc[7]["fit_residual_quantile"])),
        xytext=(3.8, 0.35),
        arrowprops={"arrowstyle": "->", "color": MID},
        fontsize=8,
    )
    figure.suptitle("Binary residual geometry changes discontinuously at the prevalence threshold")
    figure.tight_layout()
    return _save_figure(figure, "crpto_ijds_v4_fig2_phase_transition")


def _envelope_figure(envelopes: pd.DataFrame) -> dict[str, Path]:
    _style()
    metrics = ("standardized_payoff", "funded_miscoverage")
    direction_code = {"guardrail_lower": -1, "crosses_zero": 0, "guardrail_higher": 1}
    colors = [BLUE, "#F3F4F6", ORANGE]
    from matplotlib.colors import BoundaryNorm, ListedColormap

    cmap = ListedColormap(colors)
    norm = BoundaryNorm([-1.5, -0.5, 0.5, 1.5], cmap.N)
    figure, axes = plt.subplots(2, 1, figsize=(7.2, 5.2), sharex=True)
    for axis, metric in zip(axes, metrics, strict=True):
        frame = envelopes.loc[envelopes["metric"].eq(metric)].copy()
        matrix = (
            frame.assign(code=frame["direction"].map(direction_code))
            .pivot(index="paired_policy_id", columns="window_id", values="code")
            .sort_index()
        )
        axis.imshow(matrix.to_numpy(dtype=float), cmap=cmap, norm=norm, aspect="auto")
        axis.set_yticks(np.arange(9), [f"P{index}" for index in range(1, 10)])
        axis.set_ylabel("Policy")
        axis.set_title(
            "Standardized payoff" if metric == "standardized_payoff" else "Funded miscoverage"
        )
        axis.grid(False)
        for row in range(matrix.shape[0]):
            for column in range(matrix.shape[1]):
                value = int(matrix.iloc[row, column])
                axis.text(
                    column,
                    row,
                    {1: "+", 0: "0", -1: "-"}[value],
                    ha="center",
                    va="center",
                    color=INK if value == 0 else "white",
                    fontsize=8,
                    fontweight="bold",
                )
    axes[-1].set_xticks(np.arange(8), [f"W{index}" for index in range(1, 9)])
    axes[-1].set_xlabel("Residual window")
    figure.suptitle("Guardrail-minus-point envelopes over the development-admissible cap frontier")
    figure.text(
        0.5,
        0.015,
        "- guardrail lower; 0 envelope crosses zero; + guardrail higher. Default crosses zero in every cell.",
        ha="center",
        fontsize=8,
        color=MID,
    )
    figure.tight_layout(rect=(0, 0.04, 1, 0.96))
    return _save_figure(figure, "crpto_ijds_v4_fig3_envelopes")


def build_evidence() -> Path:
    config = load_v4_config(CONFIG_PATH)
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    if summary.get("status") != "complete_retrospective_binary_geometry_frontier_audit":
        raise RuntimeError("V4 deterministic summary is incomplete.")
    artifacts = {name: _verified_path(value) for name, value in summary["artifacts"].items()}
    freeze_path = _verified_path(summary["outcome_free_freeze"])
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    source_artifacts = {
        name: _verified_path(value) for name, value in freeze["outcome_free_artifacts"].items()
    }

    v2_manifest_path = _verified_path(V2_MANIFEST_DESCRIPTOR)
    v2_manifest = json.loads(v2_manifest_path.read_text(encoding="utf-8"))
    expected_v2_identity = {
        "status": "verified_post_freeze_outcome_evaluation_complete",
        "run_tag": "ijds-normalized-objective-frontier-2026-07-13-v2",
        "protocol_tag": "protocol/ijds-normalized-objective-frontier-2026-07-13-v2",
        "protocol_commit": "d3041e5233ee74a6b1d38f678def75d8d5ef0169",
    }
    if any(v2_manifest.get(field) != value for field, value in expected_v2_identity.items()):
        raise RuntimeError("The verified V2 two-ruler identity changed.")
    if any(value is not None for value in v2_manifest["selection"].values()):
        raise RuntimeError("The V2 manifest reports a selected two-ruler result.")
    if (
        v2_manifest.get("protected_stages_run") != []
        or v2_manifest.get("protected_artifacts_written") != []
    ):
        raise RuntimeError("The V2 manifest reports a protected-stage side effect.")
    v2_evaluation_artifacts = {
        name: _verified_path(value) for name, value in v2_manifest["evaluation_artifacts"].items()
    }
    v2_source_artifacts = {
        name: _verified_path(value) for name, value in v2_manifest["source_artifacts"].items()
    }
    v2_summary_path = _verified_path(v2_manifest["summary"])
    v2_receipt_path = _verified_path(v2_manifest["execution_receipt"])
    v2_summary = json.loads(v2_summary_path.read_text(encoding="utf-8"))
    expected_v2_counts = {
        "evaluated_portfolios": 6240,
        "joined_funded_rows": 622455,
        "window_endpoint_contrasts": 48,
        "monthly_endpoint_contrasts": 720,
        "metric_direction_cells": 144,
        "outcome_audit_rows": 5,
    }
    if v2_summary.get("counts") != expected_v2_counts:
        raise RuntimeError("The V2 two-ruler evaluation census changed.")

    two_ruler_windows = pd.read_parquet(v2_evaluation_artifacts["window_endpoint_contrasts"])
    two_ruler_monthly = pd.read_parquet(v2_evaluation_artifacts["monthly_endpoint_contrasts"])
    two_ruler_directions = pd.read_parquet(v2_evaluation_artifacts["metric_direction_census"])
    two_ruler_joined = pd.read_parquet(v2_evaluation_artifacts["joined_funded_allocations"])
    two_ruler_table = _two_ruler_track_table(two_ruler_windows, two_ruler_directions)
    if len(two_ruler_table) != 6 or len(two_ruler_monthly) != 720:
        raise RuntimeError("The paper-facing two-ruler track census is incomplete.")
    objective_quarter = _objective_quarter_repetition(two_ruler_joined)

    coverage_all = pd.read_parquet(artifacts["temporal_coverage"])
    coverage = coverage_all.loc[
        coverage_all["taxonomy_groups"].eq(5)
        & coverage_all["role"].eq("primary_oot")
        & coverage_all["conformal_group"].eq(-1)
    ].sort_values(["learner", "window_id"])
    phase = coverage_all.loc[
        coverage_all["learner"].eq("catboost_platt")
        & coverage_all["taxonomy_groups"].eq(5)
        & coverage_all["role"].eq("primary_oot")
        & coverage_all["conformal_group"].eq(2)
    ].sort_values("window_id")
    contrasts = pd.read_parquet(artifacts["paired_contrasts"])
    envelopes = pd.read_parquet(artifacts["comparator_envelopes"])
    development_envelopes = envelopes.loc[
        envelopes["scope"].eq("development_admissible_exact_frontier")
    ].copy()
    simulation = pd.read_parquet(artifacts["simulation_repetitions"])
    fit_audit = pd.read_parquet(source_artifacts["fit_audit"])
    solve_records = pd.read_parquet(source_artifacts["solve_records"])
    support = pd.read_parquet(source_artifacts["comparator_support"])

    fit_coverage = (
        fit_audit.loc[fit_audit["taxonomy_groups"].eq(5)]
        .groupby(["learner", "window_id"], observed=True)["covered"]
        .mean()
        .rename("fit_coverage")
        .reset_index()
    )
    coverage_table = coverage.merge(fit_coverage, on=["learner", "window_id"], how="left")
    phase_table = phase[
        [
            "window_id",
            "fit_rows",
            "fit_prevalence",
            "fit_residual_quantile",
            "coverage_lower",
            "coverage_upper",
            "mean_width",
            "set_empty_share",
            "set_zero_only_share",
            "set_both_share",
        ]
    ].copy()
    direction_table = (
        development_envelopes.groupby(["metric", "direction"], observed=True)
        .size()
        .rename("cells")
        .reset_index()
    )
    named = contrasts.loc[~contrasts["comparator_rule"].eq("point_cap_frontier")].copy()
    named["payoff_direction"] = _direction(
        named["realized_payoff_difference_lower"], named["realized_payoff_difference_upper"]
    )
    named["default_direction"] = _direction(
        named["weighted_default_difference_lower"], named["weighted_default_difference_upper"]
    )
    named["miscoverage_direction"] = _direction(
        named["weighted_miscoverage_difference_lower"],
        named["weighted_miscoverage_difference_upper"],
    )
    named_counts: list[dict[str, Any]] = []
    for rule, frame in named.groupby("comparator_rule", observed=True, sort=True):
        for metric in ("payoff", "default", "miscoverage"):
            counts = frame[f"{metric}_direction"].value_counts()
            named_counts.append(
                {
                    "comparator_rule": str(rule),
                    "metric": metric,
                    "guardrail_lower": int(counts.get("guardrail_lower", 0)),
                    "crosses_zero": int(counts.get("crosses_zero", 0)),
                    "guardrail_higher": int(counts.get("guardrail_higher", 0)),
                }
            )
    named_table = pd.DataFrame(named_counts)

    table_paths = {
        "coverage": _write_csv(
            coverage_table,
            TABLE_DIR / "crpto_ijds_v4_table1_coverage_windows.csv",
        ),
        "phase_transition": _write_csv(
            phase_table,
            TABLE_DIR / "crpto_ijds_v4_table2_phase_transition.csv",
        ),
        "development_envelopes": _write_csv(
            development_envelopes,
            TABLE_DIR / "crpto_ijds_v4_table3_development_envelopes.csv",
        ),
        "direction_summary": _write_csv(
            direction_table,
            TABLE_DIR / "crpto_ijds_v4_table4_direction_summary.csv",
        ),
        "two_ruler_tracks": _write_csv(
            two_ruler_table,
            TABLE_DIR / "crpto_ijds_v4_table5_two_ruler_tracks.csv",
        ),
        "named_comparators": _write_csv(
            named_table,
            TABLE_DIR / "crpto_ijds_v4_tableS1_named_comparators.csv",
        ),
    }
    figures = {
        "coverage": _coverage_figure(coverage),
        "phase_transition": _phase_figure(phase),
        "development_envelopes": _envelope_figure(development_envelopes),
    }

    c2 = solve_records.loc[solve_records["comparator_rule"].eq("c2_contemporaneous")]
    broad = envelopes.loc[envelopes["scope"].eq("broad_stress_exact_frontier")]
    w8_development = development_envelopes.loc[
        development_envelopes["window_id"].eq("w08_2012m08_2013m01")
    ]
    simulation_allocation = simulation[
        [
            "same_cap_allocation_distance",
            "c2_allocation_distance",
            "point_minus_guardrail_objective",
        ]
    ]
    evidence = {
        "schema_version": "2026-07-13.1",
        "status": "active_ijds_v4_with_two_ruler_paper_facing_evidence",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": str(summary["protocol_commit"]),
        "claim_boundary": dict(summary["claim_boundary"]),
        "design": {
            "primary_oot_candidates": int(coverage.iloc[0]["candidate_rows"]),
            "primary_oot_resolved": int(coverage.iloc[0]["resolved_rows"]),
            "primary_oot_unresolved": int(coverage.iloc[0]["unresolved_rows"]),
            "residual_windows": 8,
            "learners": 2,
            "taxonomy_diagnostics": [1, 2, 5, 10],
            "policies": 9,
            "v4_policies_are_supporting_not_closed_family": True,
            "oot_months": 15,
            "development_months": 11,
            "two_ruler_gamma_grid": [0.0, 0.25, 0.5, 0.75, 1.0],
            "two_ruler_primary_contrast": "gamma_1_minus_gamma_0",
            "two_ruler_interior_coordinates": [0.25, 0.5, 0.75],
            "two_ruler_tracks": 6,
            "frontier_caps": int(
                contrasts.loc[
                    contrasts["comparator_rule"].eq("point_cap_frontier"), "frontier_cap"
                ].nunique()
            ),
            "development_support_lower": float(support["support_lower"].min()),
            "development_support_upper": float(support["support_upper"].max()),
        },
        "coverage": {
            "catboost_all_eight_upper_below_nominal": bool(
                (
                    coverage.loc[coverage["learner"].eq("catboost_platt"), "coverage_upper"] < 0.90
                ).all()
            ),
            "logistic_all_eight_upper_below_nominal": bool(
                (
                    coverage.loc[coverage["learner"].eq("numeric_logistic_platt"), "coverage_upper"]
                    < 0.90
                ).all()
            ),
            "catboost_bound_min": float(
                coverage.loc[coverage["learner"].eq("catboost_platt"), "coverage_lower"].min()
            ),
            "catboost_bound_max": float(
                coverage.loc[coverage["learner"].eq("catboost_platt"), "coverage_upper"].max()
            ),
            "logistic_bound_min": float(
                coverage.loc[
                    coverage["learner"].eq("numeric_logistic_platt"), "coverage_lower"
                ].min()
            ),
            "logistic_bound_max": float(
                coverage.loc[
                    coverage["learner"].eq("numeric_logistic_platt"), "coverage_upper"
                ].max()
            ),
            "rows": coverage_table.to_dict(orient="records"),
        },
        "binary_phase_transition": {
            "stratum": 2,
            "w7_fit_prevalence": float(phase.iloc[6]["fit_prevalence"]),
            "w8_fit_prevalence": float(phase.iloc[7]["fit_prevalence"]),
            "w7_residual_quantile": float(phase.iloc[6]["fit_residual_quantile"]),
            "w8_residual_quantile": float(phase.iloc[7]["fit_residual_quantile"]),
            "w7_mean_width": float(phase.iloc[6]["mean_width"]),
            "w8_mean_width": float(phase.iloc[7]["mean_width"]),
            "w8_oot_coverage_bound": [
                float(phase.iloc[7]["coverage_lower"]),
                float(phase.iloc[7]["coverage_upper"]),
            ],
            "rows": phase_table.to_dict(orient="records"),
        },
        "portfolio": {
            "c2_cells": int(len(c2)),
            "c2_match_residual_abs_max": float(c2["c2_match_residual"].abs().max()),
            "c2_point_minus_guardrail_objective_min": float(
                c2["point_minus_guardrail_objective"].min()
            ),
            "broad_stress_all_envelopes_cross_zero": bool(
                broad["direction"].eq("crosses_zero").all()
            ),
            "broad_stress_cells": int(len(broad)),
            "development_direction_counts": direction_table.to_dict(orient="records"),
            "w8_development_all_envelopes_cross_zero": bool(
                w8_development["direction"].eq("crosses_zero").all()
            ),
            "named_direction_counts": named_table.to_dict(orient="records"),
        },
        "decision_challenger": {
            "scope": "finite_two_ruler_three_interior_coordinate_diagnostic",
            "continuous_frontier_claim": False,
            "tracks_are_independent_replications": False,
            "primary_ruler": "objective_matched",
            "secondary_ruler": "normalized_score",
            "endpoint_contrast": "gamma_1_minus_gamma_0",
            "run_tag": expected_v2_identity["run_tag"],
            "protocol_tag": expected_v2_identity["protocol_tag"],
            "protocol_commit": expected_v2_identity["protocol_commit"],
            "manifest": relative_artifact_descriptor(v2_manifest_path, repo_root=ROOT),
            "counts": dict(expected_v2_counts),
            "primary_oot_unresolved": int(
                v2_summary["outcomes"]["candidate_unresolved_by_role"]["primary_oot"]
            ),
            "metric_directions": dict(v2_summary["metric_directions"]),
            "objective_matched_coordinate_025_repetition": objective_quarter,
            "rows": two_ruler_table.to_dict(orient="records"),
            "interpretation": {
                "coordinate_one_is_structural_null": True,
                "objective_matched_equalizes_plugin_objective_floor": True,
                "normalized_score_equalizes_relative_score_relaxation": True,
                "normalized_score_equalizes_opportunity_cost": False,
                "objective_matched_coordinate_025_is_one_repeated_allocation_contrast": True,
                "preferred_gamma": None,
                "preferred_ruler": None,
                "preferred_coordinate": None,
                "policy_winner": None,
                "permitted_conclusion": (
                    "Within the predeclared finite grid, the gamma endpoint allocation "
                    "contrast is not invariant to the outcome-free ruler or interior "
                    "coordinate."
                ),
            },
        },
        "simulation": {
            "scope": "coverage_mechanism_only_portfolio_component_degenerate",
            "repetitions": int(len(simulation)),
            "cells": int(
                len(
                    simulation[
                        [
                            "score_shift",
                            "prevalence_shift",
                            "taxonomy_groups",
                            "censoring_rate",
                        ]
                    ].drop_duplicates()
                )
            ),
            "same_cap_allocation_distance_mean": float(
                simulation_allocation["same_cap_allocation_distance"].mean()
            ),
            "c2_allocation_distance_mean": float(
                simulation_allocation["c2_allocation_distance"].mean()
            ),
            "point_minus_guardrail_objective_mean": float(
                simulation_allocation["point_minus_guardrail_objective"].mean()
            ),
            "portfolio_claim_allowed": False,
        },
        "audit_thesis": (
            "Binary absolute-residual conformal guardrails can change discontinuously when "
            "a score stratum crosses the alpha prevalence threshold; candidate coverage "
            "does not transport to the later archive; and portfolio direction is not "
            "identified without an outcome-free comparator support and is not invariant "
            "to the declared ruler or interior coordinate."
        ),
        "source_artifacts": {
            "summary": relative_artifact_descriptor(SUMMARY_PATH, repo_root=ROOT),
            "freeze": relative_artifact_descriptor(freeze_path, repo_root=ROOT),
            "two_ruler/manifest": relative_artifact_descriptor(v2_manifest_path, repo_root=ROOT),
            "two_ruler/summary": relative_artifact_descriptor(v2_summary_path, repo_root=ROOT),
            "two_ruler/execution_receipt": relative_artifact_descriptor(
                v2_receipt_path, repo_root=ROOT
            ),
            **{
                f"evaluation/{name}": relative_artifact_descriptor(path, repo_root=ROOT)
                for name, path in artifacts.items()
            },
            **{
                f"outcome_free/{name}": relative_artifact_descriptor(path, repo_root=ROOT)
                for name, path in source_artifacts.items()
            },
            **{
                f"two_ruler/evaluation/{name}": relative_artifact_descriptor(path, repo_root=ROOT)
                for name, path in v2_evaluation_artifacts.items()
            },
            **{
                f"two_ruler/outcome_free/{name}": relative_artifact_descriptor(path, repo_root=ROOT)
                for name, path in v2_source_artifacts.items()
            },
        },
        "paper_artifacts": {
            **{
                f"table/{name}": relative_artifact_descriptor(path, repo_root=ROOT)
                for name, path in table_paths.items()
            },
            **{
                f"figure/{name}/{kind}": relative_artifact_descriptor(path, repo_root=ROOT)
                for name, paths in figures.items()
                for kind, path in paths.items()
            },
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    written = atomic_write_json(EVIDENCE_PATH, evidence)
    logger.info("Built active IJDS V4 evidence: {}", written)
    return written


if __name__ == "__main__":
    build_evidence()
