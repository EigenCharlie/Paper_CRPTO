"""Build the single paper-facing IJDS V4 evidence package."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from loguru import logger

from src.ijds_audit.claim_ledger import materialize_claim_ledger
from src.ijds_audit.config import load_v4_config
from src.ijds_audit.grid_contracts import (
    require_exact_grid,
    require_finite,
    require_unique_row,
    require_unique_value,
)
from src.ijds_audit.publication_generation import (
    promote_publication_generation,
    publication_implementation_descriptors,
    staged_artifact_descriptor,
    staged_output_path,
)
from src.ijds_audit.publication_sources import load_verified_source_registry
from src.ijds_audit.sensitivity_evidence import (
    endpoint_publication_table,
    load_endpoint_sensitivity_evidence,
)
from src.utils.artifact_descriptor import relative_artifact_descriptor
from src.utils.pipeline_runtime import atomic_write_strict_json, atomic_write_text

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REGISTRY_PATH = ROOT / "configs/ijds_active_evidence_sources.yaml"
CLAIM_LEDGER_PATH = ROOT / "configs/ijds_claim_ledger.yaml"
EVIDENCE_PATH = ROOT / "reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json"
TABLE_DIR = ROOT / "reports/crpto/tables"
FIGURE_DIR = ROOT / "reports/crpto/figures"

TABLE_TARGETS = {
    "coverage": TABLE_DIR / "crpto_ijds_v4_table1_coverage_windows.csv",
    "phase_transition": TABLE_DIR / "crpto_ijds_v4_table2_phase_transition.csv",
    "development_envelopes": TABLE_DIR / "crpto_ijds_v4_table3_development_envelopes.csv",
    "direction_summary": TABLE_DIR / "crpto_ijds_v4_table4_direction_summary.csv",
    "two_ruler_tracks": TABLE_DIR / "crpto_ijds_v4_table5_two_ruler_tracks.csv",
    "named_comparators": TABLE_DIR / "crpto_ijds_v4_tableS1_named_comparators.csv",
    "credit_controls": TABLE_DIR / "crpto_ijds_v4_table6_credit_controls.csv",
    "credit_prediction_metrics": TABLE_DIR / "crpto_ijds_v4_tableS2_credit_prediction_metrics.csv",
    "woe_iv_psi": TABLE_DIR / "crpto_ijds_v4_tableS3_woe_iv_psi.csv",
    "score_psi": TABLE_DIR / "crpto_ijds_v4_tableS4_score_psi.csv",
    "label_lag_sensitivity": TABLE_DIR / "crpto_ijds_v4_tableS5_label_lag_sensitivity.csv",
    "endpoint_availability_sensitivity": (
        TABLE_DIR / "crpto_ijds_v4_tableS6_endpoint_availability_sensitivity.csv"
    ),
}
FIGURE_STEMS = {
    "coverage": "crpto_ijds_v4_fig1_coverage",
    "phase_transition": "crpto_ijds_v4_fig2_phase_transition",
    "development_envelopes": "crpto_ijds_v4_fig3_envelopes",
}

CREDIT_LEARNER_ORDER = (
    "catboost_platt",
    "numeric_logistic_platt",
    "catboost_monotonic_platt",
    "woe_scorecard_platform_platt",
    "woe_scorecard_borrower_platt",
)
CREDIT_LEARNER_LABELS = {
    "catboost_platt": "CatBoost",
    "numeric_logistic_platt": "Numeric logistic",
    "catboost_monotonic_platt": "Monotonic CatBoost",
    "woe_scorecard_platform_platt": "Platform-signal WOE scorecard",
    "woe_scorecard_borrower_platt": "Pricing-excluded application WOE scorecard",
}
WINDOW_IDS = (
    "w01_2012m01_m06",
    "w02_2012m02_m07",
    "w03_2012m03_m08",
    "w04_2012m04_m09",
    "w05_2012m05_m10",
    "w06_2012m06_m11",
    "w07_2012m07_m12",
    "w08_2012m08_2013m01",
)
PREDICTION_ROLES = (
    "pd_development",
    "probability_calibration",
    "conformal_fit",
    "policy_development",
    "primary_oot",
    "censored_extension",
)
SCORE_PSI_ROLES = PREDICTION_ROLES[1:]
RULERS = ("objective_matched", "normalized_score")
COORDINATES = (0.25, 0.50, 0.75)
TWO_RULER_METRICS = (
    "standardized_payoff",
    "funded_default",
    "funded_binary_miscoverage",
)
POLICY_IDS = tuple(f"linear-{index:03d}" for index in range(1, 10))
PRIMARY_PERIODS = tuple(str(period) for period in pd.period_range("2016-04", "2017-06", freq="M"))
SUPPORT_SCOPES = (
    "named_c0_c1_c2",
    "development_admissible_exact_frontier",
    "broad_stress_exact_frontier",
)
SUPPORT_METRICS = ("standardized_payoff", "terminal_default", "funded_miscoverage")

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


def _require_identity(
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    label: str,
) -> None:
    """Fail when a registered run identity differs from its frozen artifact."""
    fields = ("run_tag", "protocol_tag", "protocol_commit")
    mismatches = [field for field in fields if actual.get(field) != expected.get(field)]
    if mismatches:
        raise RuntimeError(f"{label} identity changed: {', '.join(mismatches)}.")


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


def _credit_control_tables(
    prediction_metrics: pd.DataFrame,
    temporal_coverage: pd.DataFrame,
    woe_summary: pd.DataFrame,
    feature_psi: pd.DataFrame,
    score_psi: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    metrics = prediction_metrics.copy()
    require_exact_grid(
        metrics,
        domains={"learner": CREDIT_LEARNER_ORDER, "role": PREDICTION_ROLES},
        label="five-model prediction metrics",
    )
    require_finite(
        metrics,
        (
            "candidate_rows",
            "resolved_rows",
            "unresolved_rows",
            "default_rate",
            "roc_auc",
            "gini",
            "ks",
            "average_precision",
            "brier",
            "log_loss",
            "ece_10",
            "calibration_in_the_large",
            "calibration_intercept",
            "calibration_slope",
        ),
        label="five-model prediction metrics",
    )
    if not metrics["calibration_optimizer_success"].all():
        raise RuntimeError("A declared calibration diagnostic did not converge.")

    canonical = temporal_coverage.loc[
        temporal_coverage["taxonomy_groups"].eq(5)
        & temporal_coverage["role"].eq("primary_oot")
        & temporal_coverage["conformal_group"].eq(-1)
    ].copy()
    require_exact_grid(
        canonical,
        domains={"learner": CREDIT_LEARNER_ORDER, "window_id": WINDOW_IDS},
        label="five-model canonical coverage",
    )
    require_finite(
        canonical,
        ("candidate_rows", "resolved_rows", "unresolved_rows", "coverage_lower", "coverage_upper"),
        label="five-model canonical coverage",
    )

    primary_rows: list[dict[str, Any]] = []
    for learner in CREDIT_LEARNER_ORDER:
        metric = metrics.loc[metrics["learner"].eq(learner) & metrics["role"].eq("primary_oot")]
        coverage = canonical.loc[canonical["learner"].eq(learner)]
        row = require_unique_row(
            metric,
            key={"learner": learner, "role": "primary_oot"},
            label="primary OOT prediction metrics",
        )
        require_exact_grid(
            coverage,
            domains={"learner": (learner,), "window_id": WINDOW_IDS},
            label=f"primary OOT coverage for {learner}",
        )
        primary_rows.append(
            {
                "learner": learner,
                "learner_label": CREDIT_LEARNER_LABELS[learner],
                "candidate_rows": int(row["candidate_rows"]),
                "resolved_rows": int(row["resolved_rows"]),
                "unresolved_rows": int(row["unresolved_rows"]),
                "default_rate": float(row["default_rate"]),
                "roc_auc": float(row["roc_auc"]),
                "gini": float(row["gini"]),
                "ks": float(row["ks"]),
                "average_precision": float(row["average_precision"]),
                "brier": float(row["brier"]),
                "log_loss": float(row["log_loss"]),
                "ece_10": float(row["ece_10"]),
                "mean_calibration_error": float(row["calibration_in_the_large"]),
                "calibration_intercept": float(row["calibration_intercept"]),
                "calibration_slope": float(row["calibration_slope"]),
                "coverage_lower_min": float(coverage["coverage_lower"].min()),
                "coverage_upper_max": float(coverage["coverage_upper"].max()),
                "windows_upper_below_0_90": int(coverage["coverage_upper"].lt(0.90).sum()),
            }
        )
    primary = pd.DataFrame(primary_rows)

    role_order = {
        role: index
        for index, role in enumerate(
            (
                "pd_development",
                "probability_calibration",
                "conformal_fit",
                "policy_development",
                "primary_oot",
                "censored_extension",
            )
        )
    }
    learner_order = {learner: index for index, learner in enumerate(CREDIT_LEARNER_ORDER)}
    metrics.insert(1, "learner_label", metrics["learner"].map(CREDIT_LEARNER_LABELS))
    metrics["_learner_order"] = metrics["learner"].map(learner_order)
    metrics["_role_order"] = metrics["role"].map(role_order)
    metrics = metrics.sort_values(["_learner_order", "_role_order"]).drop(
        columns=["_learner_order", "_role_order"]
    )
    metrics = metrics.rename(columns={"calibration_in_the_large": "mean_calibration_error"})

    primary_feature_psi = feature_psi.loc[
        feature_psi["comparison_role"].eq("primary_oot"),
        ["learner", "feature", "psi"],
    ].rename(columns={"psi": "primary_oot_psi"})
    woe = woe_summary.rename(columns={"name": "feature"}).merge(
        primary_feature_psi,
        on=["learner", "feature"],
        how="left",
        validate="one_to_one",
    )
    if len(woe) != 45 or woe["primary_oot_psi"].isna().any():
        raise RuntimeError("The WOE/IV and primary OOT PSI census changed.")
    woe["_learner_order"] = woe["learner"].map(learner_order)
    woe = woe.sort_values(["_learner_order", "iv"], ascending=[True, False]).drop(
        columns="_learner_order"
    )

    score = score_psi.copy()
    require_exact_grid(
        score,
        domains={"learner": CREDIT_LEARNER_ORDER, "comparison_role": SCORE_PSI_ROLES},
        label="five-model score PSI",
    )
    require_finite(score, ("psi",), label="five-model score PSI")
    score.insert(1, "learner_label", score["learner"].map(CREDIT_LEARNER_LABELS))
    score["_learner_order"] = score["learner"].map(learner_order)
    score["_role_order"] = score["comparison_role"].map(role_order)
    score = score.sort_values(["_learner_order", "_role_order"]).drop(
        columns=["_learner_order", "_role_order"]
    )
    return {
        "credit_controls": primary,
        "credit_prediction_metrics": metrics,
        "woe_iv_psi": woe,
        "score_psi": score,
    }


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


def _save_figure(figure: plt.Figure, stem: str, *, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    png = output_dir / f"{stem}.png"
    pdf = output_dir / f"{stem}.pdf"
    figure.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    figure.savefig(
        pdf,
        bbox_inches="tight",
        facecolor="white",
        metadata={"CreationDate": None, "ModDate": None},
    )
    plt.close(figure)
    return {"png": png, "pdf": pdf}


def _coverage_figure(coverage: pd.DataFrame, *, output_dir: Path) -> dict[str, Path]:
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
    return _save_figure(figure, FIGURE_STEMS["coverage"], output_dir=output_dir)


def _phase_figure(phase: pd.DataFrame, *, output_dir: Path) -> dict[str, Path]:
    _style()
    frame = phase.sort_values("window_id")
    require_exact_grid(
        frame,
        domains={"window_id": WINDOW_IDS},
        label="phase-transition figure",
    )
    w7 = require_unique_row(
        frame,
        key={"window_id": "w07_2012m07_m12"},
        label="phase-transition W7",
    )
    w8 = require_unique_row(
        frame,
        key={"window_id": "w08_2012m08_2013m01"},
        label="phase-transition W8",
    )
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
        xy=(6, float(w7["fit_prevalence"])),
        xytext=(4.6, 0.111),
        arrowprops={"arrowstyle": "-", "color": MID},
        fontsize=8,
    )
    axes[0].annotate(
        "W8: 0.0971",
        xy=(7, float(w8["fit_prevalence"])),
        xytext=(5.5, 0.0975),
        arrowprops={"arrowstyle": "-", "color": MID},
        fontsize=8,
    )
    axes[1].annotate(
        "0.8884 to 0.1118",
        xy=(7, float(w8["fit_residual_quantile"])),
        xytext=(3.8, 0.35),
        arrowprops={"arrowstyle": "->", "color": MID},
        fontsize=8,
    )
    figure.suptitle("Binary residual geometry changes discontinuously at the prevalence threshold")
    figure.tight_layout()
    return _save_figure(figure, FIGURE_STEMS["phase_transition"], output_dir=output_dir)


def _envelope_figure(envelopes: pd.DataFrame, *, output_dir: Path) -> dict[str, Path]:
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
    return _save_figure(figure, FIGURE_STEMS["development_envelopes"], output_dir=output_dir)


def _build_evidence(staging_root: Path) -> Path:
    registry, registered = load_verified_source_registry(
        SOURCE_REGISTRY_PATH,
        repo_root=ROOT,
    )
    lineages = cast(dict[str, Any], registry["lineages"])
    v4_lineage = cast(dict[str, Any], lineages["binary_geometry"])
    two_ruler_lineage = cast(dict[str, Any], lineages["two_ruler"])
    credit_lineage = cast(dict[str, Any], lineages["credit_controls"])
    diagnostic_lineage = cast(dict[str, Any], lineages["diagnostics"])
    sensitivities = cast(dict[str, Any], registry["sensitivities"])
    endpoint_lineage = cast(dict[str, Any], sensitivities["endpoint_availability"])
    config_path = registered["v4_config"]
    summary_path = registered["v4_summary"]
    v4_receipt_path = registered["v4_receipt"]
    config = load_v4_config(config_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "complete_retrospective_binary_geometry_frontier_audit":
        raise RuntimeError("V4 deterministic summary is incomplete.")
    _require_identity(summary, v4_lineage["evaluation"], label="V4 evaluation")
    v4_receipt = json.loads(v4_receipt_path.read_text(encoding="utf-8"))
    if v4_receipt.get("protocol_commit") != v4_lineage["evaluation"]["protocol_commit"]:
        raise RuntimeError("V4 receipt protocol commit changed.")
    if v4_receipt.get("summary") != relative_artifact_descriptor(summary_path, repo_root=ROOT):
        raise RuntimeError("V4 receipt no longer binds the registered summary.")
    artifacts = {name: _verified_path(value) for name, value in summary["artifacts"].items()}
    freeze_path = _verified_path(summary["outcome_free_freeze"])
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    _require_identity(
        freeze["outcome_free_lineage"],
        v4_lineage["outcome_free"],
        label="V4 outcome-free freeze",
    )
    v4_source_freeze_path = _verified_path(freeze["outcome_free_lineage"]["source_protocol_freeze"])
    if (
        freeze["outcome_free_lineage"]["source_protocol_freeze"]["sha256"]
        != v4_lineage["outcome_free"]["freeze_sha256"]
    ):
        raise RuntimeError("V4 outcome-free freeze hash changed.")
    source_artifacts = {
        name: _verified_path(value) for name, value in freeze["outcome_free_artifacts"].items()
    }

    two_ruler_manifest_path = registered["two_ruler_manifest"]
    two_ruler_manifest = json.loads(two_ruler_manifest_path.read_text(encoding="utf-8"))
    if two_ruler_manifest.get("status") != "verified_post_freeze_outcome_evaluation_complete":
        raise RuntimeError("The verified V3 two-ruler evaluation is incomplete.")
    _require_identity(
        two_ruler_manifest,
        two_ruler_lineage["evaluation"],
        label="Two-ruler evaluation",
    )
    two_ruler_freeze_path = _verified_path(two_ruler_manifest["source_frontier_freeze"])
    two_ruler_freeze = json.loads(two_ruler_freeze_path.read_text(encoding="utf-8"))
    _require_identity(
        two_ruler_freeze,
        two_ruler_lineage["outcome_free"],
        label="Two-ruler outcome-free freeze",
    )
    if (
        two_ruler_manifest["source_frontier_freeze"]["sha256"]
        != two_ruler_lineage["outcome_free"]["freeze_sha256"]
    ):
        raise RuntimeError("Two-ruler outcome-free freeze hash changed.")
    if any(value is not None for value in two_ruler_manifest["selection"].values()):
        raise RuntimeError("The V3 manifest reports a selected two-ruler result.")
    if (
        two_ruler_manifest.get("protected_stages_run") != []
        or two_ruler_manifest.get("protected_artifacts_written") != []
    ):
        raise RuntimeError("The V3 manifest reports a protected-stage side effect.")
    two_ruler_evaluation_artifacts = {
        name: _verified_path(value)
        for name, value in two_ruler_manifest["evaluation_artifacts"].items()
    }
    two_ruler_source_artifacts = {
        name: _verified_path(value)
        for name, value in two_ruler_manifest["source_artifacts"].items()
    }
    two_ruler_summary_path = _verified_path(two_ruler_manifest["summary"])
    two_ruler_receipt_path = _verified_path(two_ruler_manifest["execution_receipt"])
    two_ruler_summary = json.loads(two_ruler_summary_path.read_text(encoding="utf-8"))
    expected_two_ruler_counts = {
        "evaluated_portfolios": 6240,
        "joined_funded_rows": 622455,
        "window_endpoint_contrasts": 48,
        "monthly_endpoint_contrasts": 720,
        "metric_direction_cells": 144,
        "outcome_audit_rows": 7,
    }
    if two_ruler_summary.get("counts") != expected_two_ruler_counts:
        raise RuntimeError("The V3 two-ruler evaluation census changed.")

    credit_summary_path = registered["credit_summary"]
    credit_receipt_path = registered["credit_receipt"]
    credit_summary = json.loads(credit_summary_path.read_text(encoding="utf-8"))
    if credit_summary.get("status") != "complete_no_model_selection_credit_risk_control_evaluation":
        raise RuntimeError("The verified V3 credit-control evaluation is incomplete.")
    credit_receipt = json.loads(credit_receipt_path.read_text(encoding="utf-8"))
    _require_identity(
        credit_receipt,
        credit_lineage["evaluation"],
        label="Credit-control evaluation",
    )
    expected_interpretation = {
        "model_or_feature_selected_from_oot": False,
        "portfolio_claim_authorized": False,
        "scorecard_superiority_claim_authorized": False,
        "universal_transport_claim_authorized": False,
    }
    if credit_summary.get("interpretation") != expected_interpretation:
        raise RuntimeError("The V3 credit-control claim boundary changed.")
    if (
        credit_summary.get("protected_stages_run") != []
        or credit_summary.get("protected_artifacts_written") != []
    ):
        raise RuntimeError("The V3 credit controls report a protected-stage side effect.")
    if credit_summary.get("coverage_recovery") is not None:
        raise RuntimeError("V3 credit controls unexpectedly report a numerical recovery block.")

    credit_freeze_path = _verified_path(credit_summary["source_freeze"])
    credit_freeze = json.loads(credit_freeze_path.read_text(encoding="utf-8"))
    if (
        credit_freeze.get("status")
        != "credit_control_scores_frozen_before_primary_oot_outcome_join"
    ):
        raise RuntimeError("The V1b credit-control freeze is incomplete.")
    _require_identity(
        credit_freeze,
        credit_lineage["outcome_free"],
        label="Credit-control outcome-free freeze",
    )
    if credit_summary["source_freeze"]["sha256"] != credit_lineage["outcome_free"]["freeze_sha256"]:
        raise RuntimeError("Credit-control outcome-free freeze hash changed.")
    if credit_freeze.get("co_primary_learners") != list(CREDIT_LEARNER_ORDER):
        raise RuntimeError("The frozen five-model specification changed.")
    if (
        credit_freeze.get("model_selection") != "none_all_five_reported"
        or credit_freeze.get("window_selection") != "none_all_eight_reported"
        or credit_freeze.get("portfolio_optimization") is not False
        or credit_freeze.get("sampling") != "none_all_eligible_rows"
        or credit_freeze.get("primary_oot_outcome_columns_in_frozen_scores") != []
    ):
        raise RuntimeError("The frozen credit-control selection boundary changed.")

    credit_evaluation_artifacts = {
        name: _verified_path(value)
        for name, value in credit_summary["evaluation_artifacts"].items()
    }
    credit_outcome_free_artifacts = {
        name: _verified_path(value)
        for name, value in credit_freeze["outcome_free_artifacts"].items()
    }
    credit_model_artifacts = {
        name: _verified_path(value) for name, value in credit_freeze["model_artifacts"].items()
    }
    raw_audit_path = registered["raw_data_audit"]
    raw_audit = json.loads(raw_audit_path.read_text(encoding="utf-8"))
    if raw_audit.get("status") != "complete_full_archive_data_contract_audit":
        raise RuntimeError("The full-archive data audit is incomplete.")
    if raw_audit.get("run_tag") != diagnostic_lineage["raw_data_audit"]["run_tag"]:
        raise RuntimeError("The raw-data audit identity changed.")
    if (
        raw_audit.get("protected_stages_run") != []
        or raw_audit.get("protected_artifacts_written") != []
    ):
        raise RuntimeError("The raw-data audit reports a protected-stage side effect.")
    raw_audit_artifacts = {
        name: _verified_path(value) for name, value in raw_audit["artifacts"].items()
    }
    raw_feature_contract = pd.read_csv(raw_audit_artifacts["feature_contract"])
    raw_coverage_exceptions = raw_feature_contract.loc[
        raw_feature_contract["coverage_exception"].notna()
        & raw_feature_contract["requires_sensitivity"].eq(True)
    ].copy()
    if len(raw_coverage_exceptions) != 2:
        raise RuntimeError("The declared raw-feature coverage exceptions changed.")
    lag_evidence_path = registered["label_lag_sensitivity"]
    lag_evidence = json.loads(lag_evidence_path.read_text(encoding="utf-8"))
    if lag_evidence.get("status") != "complete_frozen_score_label_lag_sensitivity":
        raise RuntimeError("The label-lag sensitivity is incomplete.")
    _require_identity(
        lag_evidence,
        diagnostic_lineage["label_lag_sensitivity"],
        label="Label-lag sensitivity",
    )
    lag_table_path = _verified_path(lag_evidence["artifact"])
    lag_table = pd.read_csv(lag_table_path)
    require_exact_grid(
        lag_table,
        domains={"charged_off_lag_months": (0, 3, 6, 8, 12), "window_id": WINDOW_IDS},
        label="fit-label lag sensitivity",
    )
    require_finite(
        lag_table,
        ("minimum_monthly_retention", "phase_prevalence", "phase_residual_quantile"),
        label="fit-label lag sensitivity",
    )
    admissible_lag_table = lag_table.loc[lag_table["passes_locked_retention"]].copy()
    nonadmissible_lag_table = lag_table.loc[~lag_table["passes_locked_retention"]].copy()
    if set(admissible_lag_table["charged_off_lag_months"]) != {0, 3, 6}:
        raise RuntimeError("The admissible label-lag set changed.")
    lag_w7_w8 = lag_table.loc[
        lag_table["window_id"].isin(("w07_2012m07_m12", "w08_2012m08_2013m01"))
    ].copy()

    tie_evidence_path = registered["solver_tie_audit"]
    tie_evidence = json.loads(tie_evidence_path.read_text(encoding="utf-8"))
    if tie_evidence.get("status") != "complete_prefreeze_structural_evidence":
        raise RuntimeError("The solver-tie audit is incomplete.")
    _require_identity(
        tie_evidence,
        diagnostic_lineage["solver_tie_audit"],
        label="Solver-tie audit",
    )
    tie_census = tie_evidence["results"]["point_cap_census"]
    tie_order = tie_evidence["results"]["order_sensitivity"]
    if int(tie_census["near_zero_bases"]) != 0 or int(tie_order["tie_sensitive_rows"]) != 0:
        raise RuntimeError("The evaluated point-cap census contains an unresolved solver tie.")

    credit_prediction_metrics = pd.read_parquet(credit_evaluation_artifacts["prediction_metrics"])
    credit_temporal_coverage = pd.read_parquet(credit_evaluation_artifacts["temporal_coverage"])
    credit_woe_summary = pd.read_parquet(credit_outcome_free_artifacts["woe_summary"])
    credit_feature_psi = pd.read_parquet(credit_outcome_free_artifacts["scorecard_feature_psi"])
    credit_score_psi = pd.read_parquet(credit_outcome_free_artifacts["score_psi"])
    credit_feature_variation = pd.read_parquet(credit_outcome_free_artifacts["feature_variation"])
    credit_tables = _credit_control_tables(
        credit_prediction_metrics,
        credit_temporal_coverage,
        credit_woe_summary,
        credit_feature_psi,
        credit_score_psi,
    )

    two_ruler_windows = pd.read_parquet(two_ruler_evaluation_artifacts["window_endpoint_contrasts"])
    two_ruler_monthly = pd.read_parquet(
        two_ruler_evaluation_artifacts["monthly_endpoint_contrasts"]
    )
    two_ruler_directions = pd.read_parquet(
        two_ruler_evaluation_artifacts["metric_direction_census"]
    )
    two_ruler_joined = pd.read_parquet(two_ruler_evaluation_artifacts["joined_funded_allocations"])
    require_exact_grid(
        two_ruler_windows,
        domains={"window_id": WINDOW_IDS, "ruler": RULERS, "coordinate": COORDINATES},
        label="two-ruler window contrasts",
    )
    require_exact_grid(
        two_ruler_monthly,
        domains={
            "window_id": WINDOW_IDS,
            "ruler": RULERS,
            "coordinate": COORDINATES,
            "period": PRIMARY_PERIODS,
        },
        label="two-ruler monthly contrasts",
    )
    require_exact_grid(
        two_ruler_directions,
        domains={
            "window_id": WINDOW_IDS,
            "ruler": RULERS,
            "coordinate": COORDINATES,
            "metric": TWO_RULER_METRICS,
        },
        label="two-ruler metric directions",
    )
    two_ruler_table = _two_ruler_track_table(two_ruler_windows, two_ruler_directions)
    require_exact_grid(
        two_ruler_table,
        domains={"ruler": RULERS, "coordinate": COORDINATES},
        label="paper-facing two-ruler tracks",
    )
    objective_quarter = _objective_quarter_repetition(two_ruler_joined)

    coverage_all = pd.read_parquet(artifacts["temporal_coverage"])
    coverage = coverage_all.loc[
        coverage_all["taxonomy_groups"].eq(5)
        & coverage_all["role"].eq("primary_oot")
        & coverage_all["conformal_group"].eq(-1)
    ].sort_values(["learner", "window_id"])
    require_exact_grid(
        coverage,
        domains={
            "learner": ("catboost_platt", "numeric_logistic_platt"),
            "window_id": WINDOW_IDS,
        },
        label="detailed V4 canonical coverage",
    )
    require_finite(
        coverage,
        ("candidate_rows", "resolved_rows", "unresolved_rows", "coverage_lower", "coverage_upper"),
        label="detailed V4 canonical coverage",
    )
    phase = coverage_all.loc[
        coverage_all["learner"].eq("catboost_platt")
        & coverage_all["taxonomy_groups"].eq(5)
        & coverage_all["role"].eq("primary_oot")
        & coverage_all["conformal_group"].eq(2)
    ].sort_values("window_id")
    require_exact_grid(
        phase,
        domains={"window_id": WINDOW_IDS},
        label="binary phase transition",
    )
    require_finite(
        phase,
        (
            "fit_prevalence",
            "fit_residual_quantile",
            "mean_width",
            "coverage_lower",
            "coverage_upper",
        ),
        label="binary phase transition",
    )
    contrasts = pd.read_parquet(artifacts["paired_contrasts"])
    envelopes = pd.read_parquet(artifacts["comparator_envelopes"])
    require_exact_grid(
        envelopes,
        domains={
            "window_id": WINDOW_IDS,
            "paired_policy_id": POLICY_IDS,
            "scope": SUPPORT_SCOPES,
            "metric": SUPPORT_METRICS,
        },
        label="exact comparator envelopes",
    )
    require_finite(envelopes, ("lower", "upper"), label="exact comparator envelopes")
    if not envelopes["lower"].le(envelopes["upper"]).all():
        raise RuntimeError("An exact comparator envelope has reversed bounds.")
    endpoint_summary_path = registered["endpoint_sensitivity_summary"]
    endpoint_evidence = load_endpoint_sensitivity_evidence(
        endpoint_summary_path,
        identity=endpoint_lineage,
        repo_root=ROOT,
        reference_coverage=credit_temporal_coverage,
        reference_two_ruler=two_ruler_windows,
        reference_envelopes=envelopes,
    )
    endpoint_table = endpoint_publication_table(endpoint_evidence)
    require_exact_grid(
        endpoint_table,
        domains={"charged_off_lag_months": (0, 3, 6, 8, 12)},
        label="paper-facing endpoint availability sensitivity",
    )
    endpoint_sensitivity_artifacts = {
        name: _verified_path(descriptor)
        for name, descriptor in endpoint_evidence.summary["artifacts"].items()
    }
    development_envelopes = envelopes.loc[
        envelopes["scope"].eq("development_admissible_exact_frontier")
    ].copy()
    simulation = pd.read_parquet(artifacts["simulation_repetitions"])
    fit_audit = pd.read_parquet(source_artifacts["fit_audit"])
    solve_records = pd.read_parquet(source_artifacts["solve_records"])
    support = pd.read_parquet(source_artifacts["comparator_support"])
    require_exact_grid(
        support,
        domains={"window_id": WINDOW_IDS, "paired_policy_id": POLICY_IDS},
        label="development comparator support",
    )
    require_finite(
        support,
        ("development_months", "c1_cap", "support_lower", "support_upper"),
        label="development comparator support",
    )
    if not support["support_lower"].le(support["support_upper"]).all():
        raise RuntimeError("Development comparator support has reversed bounds.")

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

    staged_table_targets = {
        name: staged_output_path(staging_root, target, repo_root=ROOT)
        for name, target in TABLE_TARGETS.items()
    }
    table_paths = {
        "coverage": _write_csv(
            coverage_table,
            staged_table_targets["coverage"],
        ),
        "phase_transition": _write_csv(
            phase_table,
            staged_table_targets["phase_transition"],
        ),
        "development_envelopes": _write_csv(
            development_envelopes,
            staged_table_targets["development_envelopes"],
        ),
        "direction_summary": _write_csv(
            direction_table,
            staged_table_targets["direction_summary"],
        ),
        "two_ruler_tracks": _write_csv(
            two_ruler_table,
            staged_table_targets["two_ruler_tracks"],
        ),
        "named_comparators": _write_csv(
            named_table,
            staged_table_targets["named_comparators"],
        ),
        "credit_controls": _write_csv(
            credit_tables["credit_controls"],
            staged_table_targets["credit_controls"],
        ),
        "credit_prediction_metrics": _write_csv(
            credit_tables["credit_prediction_metrics"],
            staged_table_targets["credit_prediction_metrics"],
        ),
        "woe_iv_psi": _write_csv(
            credit_tables["woe_iv_psi"],
            staged_table_targets["woe_iv_psi"],
        ),
        "score_psi": _write_csv(
            credit_tables["score_psi"],
            staged_table_targets["score_psi"],
        ),
        "label_lag_sensitivity": _write_csv(
            lag_table.sort_values(["charged_off_lag_months", "window_id"]),
            staged_table_targets["label_lag_sensitivity"],
        ),
        "endpoint_availability_sensitivity": _write_csv(
            endpoint_table,
            staged_table_targets["endpoint_availability_sensitivity"],
        ),
    }
    staged_figure_dir = staging_root / "outputs" / FIGURE_DIR.relative_to(ROOT)
    figures = {
        "coverage": _coverage_figure(coverage, output_dir=staged_figure_dir),
        "phase_transition": _phase_figure(phase, output_dir=staged_figure_dir),
        "development_envelopes": _envelope_figure(
            development_envelopes,
            output_dir=staged_figure_dir,
        ),
    }
    figure_targets = {
        name: {kind: FIGURE_DIR / f"{FIGURE_STEMS[name]}.{kind}" for kind in ("png", "pdf")}
        for name in FIGURE_STEMS
    }
    publication_outputs = {
        **{TABLE_TARGETS[name]: path for name, path in table_paths.items()},
        **{
            figure_targets[name][kind]: path
            for name, paths in figures.items()
            for kind, path in paths.items()
        },
    }
    expected_targets = {
        *TABLE_TARGETS.values(),
        *(target for targets in figure_targets.values() for target in targets.values()),
    }
    if len(publication_outputs) != 18 or set(publication_outputs) != expected_targets:
        raise RuntimeError(
            "The staged publication generation is not exactly 12 CSVs and 6 figures."
        )

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
    credit_primary = credit_tables["credit_controls"]
    primary_score_psi = credit_score_psi.loc[
        credit_score_psi["comparison_role"].eq("primary_oot")
    ].set_index("learner")["psi"]
    primary_feature_psi = credit_feature_psi.loc[
        credit_feature_psi["comparison_role"].eq("primary_oot")
    ].sort_values("psi", ascending=False)
    top_platform_iv = (
        credit_woe_summary.loc[credit_woe_summary["learner"].eq("woe_scorecard_platform_platt")]
        .sort_values("iv", ascending=False)
        .head(5)[["name", "iv"]]
        .to_dict(orient="records")
    )
    top_borrower_iv = (
        credit_woe_summary.loc[credit_woe_summary["learner"].eq("woe_scorecard_borrower_platt")]
        .sort_values("iv", ascending=False)
        .head(5)[["name", "iv"]]
        .to_dict(orient="records")
    )
    recent_chargeoff_variation = credit_feature_variation.loc[
        credit_feature_variation["feature"].eq("recent_chargeoff")
        & credit_feature_variation["role"].isin(["pd_development", "probability_calibration"])
    ][["role", "rows", "unique_observed", "constant_observed"]]
    primary_oot_candidates = int(
        require_unique_value(coverage, "candidate_rows", label="detailed V4 canonical coverage")
    )
    primary_oot_resolved = int(
        require_unique_value(coverage, "resolved_rows", label="detailed V4 canonical coverage")
    )
    primary_oot_unresolved = int(
        require_unique_value(coverage, "unresolved_rows", label="detailed V4 canonical coverage")
    )
    phase_w7 = require_unique_row(
        phase,
        key={"window_id": "w07_2012m07_m12"},
        label="binary phase transition W7",
    )
    phase_w8 = require_unique_row(
        phase,
        key={"window_id": "w08_2012m08_2013m01"},
        label="binary phase transition W8",
    )
    evidence = {
        "schema_version": "2026-07-15.1",
        "status": "active_ijds_v4_endpoint_corrected_paper_facing_evidence",
        "source_registry": {
            "schema_version": str(registry["schema_version"]),
            "status": str(registry["status"]),
            "sources": sorted(registered),
        },
        "lineages": lineages,
        "sensitivities": sensitivities,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": str(summary["protocol_commit"]),
        "claim_boundary": dict(summary["claim_boundary"]),
        "design": {
            "primary_oot_candidates": primary_oot_candidates,
            "primary_oot_resolved": primary_oot_resolved,
            "primary_oot_unresolved": primary_oot_unresolved,
            "residual_windows": 8,
            "learners": 5,
            "v4_detailed_coverage_learners": 2,
            "credit_control_learners": 5,
            "portfolio_learners": 1,
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
            "evaluation_endpoint": str(config["design"]["endpoint"]),
            "archive_is_verified_point_in_time_snapshot": bool(
                config["target"]["evaluation_outcome_contract"][
                    "archive_is_verified_point_in_time_snapshot"
                ]
            ),
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
        "evaluation_endpoint": {
            **dict(config["target"]["evaluation_outcome_contract"]),
            "role": str(config["source"]["snapshot_date_role"]),
            "terminal_statuses_after_cutoff_reclassified_unresolved": True,
            "primary_oot_candidates": primary_oot_candidates,
            "primary_oot_resolved": primary_oot_resolved,
            "primary_oot_unresolved": primary_oot_unresolved,
            "last_payment_date_max": str(raw_audit["results"]["last_payment_date_max"]),
            "last_credit_pull_date_max": str(raw_audit["results"]["last_credit_pull_date_max"]),
            "last_payment_rows_after_cutoff": int(
                raw_audit["results"]["last_payment_rows_after_cutoff"]
            ),
            "last_credit_pull_rows_after_cutoff": int(
                raw_audit["results"]["last_credit_pull_rows_after_cutoff"]
            ),
        },
        "sensitivity": {
            "evaluation_endpoint_availability": {
                "scope": "complete_nonselective_retrospective_lag_grid",
                "run_tag": str(endpoint_evidence.summary["run_tag"]),
                "protocol_tag": str(endpoint_evidence.summary["protocol_tag"]),
                "protocol_commit": str(endpoint_evidence.summary["protocol_commit"]),
                "charged_off_lags_months": list(endpoint_evidence.summary["lags"]),
                "endpoint_or_result_selected": False,
                "allocation_refit": False,
                "six_month_endpoint_reconciles_exactly_to_active_v3": True,
                "reconciliation": dict(endpoint_evidence.reconciliation),
                "fit_label_lag_crossed_factorially": False,
                "estimand_boundary": (
                    "This family changes evaluation-outcome availability while holding "
                    "scores, fitted residual recipes, supports, and allocations fixed. "
                    "The separate label-lag family changes conformal-fit labels and was "
                    "not crossed factorially with endpoint availability."
                ),
                "rows": endpoint_table.to_dict(orient="records"),
            },
        },
        "data_contract": {
            "raw_rows": int(raw_audit["results"]["raw_rows"]),
            "valid_loan_rows": int(raw_audit["results"]["valid_loan_rows"]),
            "raw_schema_columns": int(raw_audit["results"]["raw_schema_columns"]),
            "term36_rows_all_dates": int(raw_audit["results"]["term36_rows_all_dates"]),
            "term60_rows_all_dates": int(raw_audit["results"]["term60_rows_all_dates"]),
            "active_design_rows": int(raw_audit["results"]["term36_active_design_rows"]),
            "eligible_raw_features": int(raw_audit["results"]["eligible_raw_features"]),
            "late_schema_features": int(raw_audit["results"]["late_schema_features"]),
            "declared_coverage_exceptions": int(
                raw_audit["results"]["declared_coverage_exceptions"]
            ),
            "coverage_exceptions_requiring_sensitivity": int(
                raw_audit["results"]["coverage_exceptions_requiring_sensitivity"]
            ),
            "coverage_exception_rows": raw_coverage_exceptions[
                [
                    "feature",
                    "minimum_fitting_coverage",
                    "primary_oot_coverage",
                    "coverage_exception",
                    "missingness_semantics",
                    "requires_sensitivity",
                ]
            ].to_dict(orient="records"),
            "primary_oot_funded_ratio": float(raw_audit["results"]["primary_oot_funded_ratio"]),
            "primary_oot_requested_minus_funded_usd": float(
                raw_audit["results"]["primary_oot_total_requested_minus_funded"]
            ),
            "sampling": "none_all_eligible_rows_within_each_declared_temporal_role",
            "population_boundary": (
                "The active 640,543-row design is the exhaustive eligible 36-month "
                "population for the declared dates, horizon, schema, and observability "
                "rules; it is not a sample from the raw archive."
            ),
            "excluded_scope": (
                "Sixty-month contracts, immature issue dates, and late-schema fields "
                "define different horizons, censoring regimes, or temporal feature support."
            ),
            "manifest": relative_artifact_descriptor(raw_audit_path, repo_root=ROOT),
        },
        "credit_risk_controls": {
            "scope": "coverage_only_five_model_temporal_transport_robustness",
            "outcome_free_run_tag": str(credit_freeze["run_tag"]),
            "verified_evaluation_run_tag": str(credit_summary["run_tag"]),
            "all_five_all_eight_upper_below_nominal": bool(
                credit_primary["windows_upper_below_0_90"].eq(8).all()
                and credit_primary["coverage_upper_max"].lt(0.90).all()
            ),
            "learners_reported": list(CREDIT_LEARNER_ORDER),
            "portfolio_learner": "catboost_platt",
            "controls_enter_portfolio_optimization": False,
            "model_or_feature_selected_from_oot": False,
            "scorecard_superiority_claim_authorized": False,
            "rows": credit_primary.to_dict(orient="records"),
            "declared_descriptive_differences": dict(credit_summary["declared_diagnostics"]),
            "calibration": {
                "all_primary_oot_mean_calibration_error_negative": bool(
                    credit_primary["mean_calibration_error"].lt(0.0).all()
                ),
                "all_primary_oot_slopes_below_one": bool(
                    credit_primary["calibration_slope"].lt(1.0).all()
                ),
                "optimizer_success_rows": int(
                    credit_prediction_metrics["calibration_optimizer_success"].sum()
                ),
                "optimizer_total_rows": int(len(credit_prediction_metrics)),
            },
            "woe_iv": {
                "optbinning_problems": int(len(credit_woe_summary)),
                "all_optimal": bool(credit_woe_summary["status"].eq("OPTIMAL").all()),
                "platform_features": int(
                    credit_woe_summary["learner"].eq("woe_scorecard_platform_platt").sum()
                ),
                "pricing_excluded_application_features": int(
                    credit_woe_summary["learner"].eq("woe_scorecard_borrower_platt").sum()
                ),
                "top_platform_iv": top_platform_iv,
                "top_pricing_excluded_application_iv": top_borrower_iv,
            },
            "temporal_shift": {
                "primary_oot_score_psi": {
                    learner: float(primary_score_psi.loc[learner])
                    for learner in CREDIT_LEARNER_ORDER
                },
                "top_primary_oot_feature_psi": primary_feature_psi.head(5)[
                    ["learner", "feature", "psi"]
                ].to_dict(orient="records"),
                "recent_chargeoff_early_role_variation": recent_chargeoff_variation.to_dict(
                    orient="records"
                ),
            },
            "interpretation": (
                "WOE/IV, a pricing-excluded application scorecard, and domain-safe "
                "monotonic constraints are predeclared coverage-only specification "
                "controls. They strengthen model-class robustness but do not define the "
                "paper's novelty, select a learner, or authorize a portfolio policy."
            ),
        },
        "binary_phase_transition": {
            "stratum": 2,
            "w7_fit_prevalence": float(phase_w7["fit_prevalence"]),
            "w8_fit_prevalence": float(phase_w8["fit_prevalence"]),
            "w7_residual_quantile": float(phase_w7["fit_residual_quantile"]),
            "w8_residual_quantile": float(phase_w8["fit_residual_quantile"]),
            "w7_mean_width": float(phase_w7["mean_width"]),
            "w8_mean_width": float(phase_w8["mean_width"]),
            "w8_oot_coverage_bound": [
                float(phase_w8["coverage_lower"]),
                float(phase_w8["coverage_upper"]),
            ],
            "label_lag_sensitivity": {
                "admissible_lags_months": sorted(
                    int(value) for value in admissible_lag_table["charged_off_lag_months"].unique()
                ),
                "nonadmissible_lags_months": sorted(
                    int(value)
                    for value in nonadmissible_lag_table["charged_off_lag_months"].unique()
                ),
                "minimum_monthly_retention_by_lag": dict(
                    lag_evidence["results"]["minimum_monthly_retention_by_lag"]
                ),
                "locked_retention_threshold": 0.99,
                "w7_to_w8_threshold_crossing_at_all_admissible_lags": bool(
                    lag_w7_w8.loc[
                        lag_w7_w8["passes_locked_retention"]
                        & lag_w7_w8["window_id"].eq("w07_2012m07_m12"),
                        "phase_residual_quantile",
                    ]
                    .gt(0.5)
                    .all()
                    and lag_w7_w8.loc[
                        lag_w7_w8["passes_locked_retention"]
                        & lag_w7_w8["window_id"].eq("w08_2012m08_2013m01"),
                        "phase_residual_quantile",
                    ]
                    .lt(0.5)
                    .all()
                ),
                "crossing_disappears_outside_locked_retention_scope": bool(
                    lag_w7_w8.loc[~lag_w7_w8["passes_locked_retention"], "phase_residual_quantile"]
                    .lt(0.5)
                    .all()
                ),
                "causal_interpretation_authorized": False,
                "rows": lag_w7_w8.to_dict(orient="records"),
            },
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
            "evaluated_point_cap_solver_stability": {
                "scope": "evaluated_point_caps_only_not_continuous_uniqueness",
                "point_cap_rows": int(tie_census["rows"]),
                "named_unique_cap_months": int(tie_census["named_unique_cap_months"]),
                "minimum_absolute_nonbasic_reduced_cost": float(
                    tie_census["minimum_absolute_nonbasic_reduced_cost"]
                ),
                "near_zero_bases": int(tie_census["near_zero_bases"]),
                "primal_degenerate_bases": int(tie_census["primal_degenerate_bases"]),
                "reversed_order_reruns": int(tie_order["triggered_rows"]),
                "tie_sensitive_rows": int(tie_order["tie_sensitive_rows"]),
                "maximum_allocation_distance": float(tie_order["maximum_allocation_distance"]),
                "maximum_absolute_objective_difference": float(
                    tie_order["maximum_absolute_objective_difference"]
                ),
                "continuous_frontier_uniqueness_claim": False,
            },
        },
        "decision_challenger": {
            "scope": "finite_two_ruler_three_interior_coordinate_diagnostic",
            "continuous_frontier_claim": False,
            "tracks_are_independent_replications": False,
            "primary_ruler": "objective_matched",
            "secondary_ruler": "normalized_score",
            "endpoint_contrast": "gamma_1_minus_gamma_0",
            "run_tag": two_ruler_lineage["evaluation"]["run_tag"],
            "protocol_tag": two_ruler_lineage["evaluation"]["protocol_tag"],
            "protocol_commit": two_ruler_lineage["evaluation"]["protocol_commit"],
            "manifest": relative_artifact_descriptor(two_ruler_manifest_path, repo_root=ROOT),
            "counts": dict(expected_two_ruler_counts),
            "primary_oot_unresolved": int(
                two_ruler_summary["outcomes"]["candidate_unresolved_by_role"]["primary_oot"]
            ),
            "metric_directions": dict(two_ruler_summary["metric_directions"]),
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
            "does not transport to the later archive under five predeclared credit-risk "
            "model specifications; and portfolio direction is not identified without an "
            "outcome-free comparator support and is not invariant to the declared ruler "
            "or interior coordinate."
        ),
        "source_artifacts": {
            **publication_implementation_descriptors(ROOT),
            "config": relative_artifact_descriptor(config_path, repo_root=ROOT),
            "outcome_free/source_protocol_freeze": relative_artifact_descriptor(
                v4_source_freeze_path, repo_root=ROOT
            ),
            "freeze": relative_artifact_descriptor(freeze_path, repo_root=ROOT),
            **{
                f"outcome_free/{name}": relative_artifact_descriptor(path, repo_root=ROOT)
                for name, path in source_artifacts.items()
            },
            "summary": relative_artifact_descriptor(summary_path, repo_root=ROOT),
            "execution_receipt": relative_artifact_descriptor(v4_receipt_path, repo_root=ROOT),
            **{
                f"evaluation/{name}": relative_artifact_descriptor(path, repo_root=ROOT)
                for name, path in artifacts.items()
            },
            "two_ruler/outcome_free/freeze": relative_artifact_descriptor(
                two_ruler_freeze_path, repo_root=ROOT
            ),
            **{
                f"two_ruler/outcome_free/{name}": relative_artifact_descriptor(path, repo_root=ROOT)
                for name, path in two_ruler_source_artifacts.items()
            },
            "two_ruler/manifest": relative_artifact_descriptor(
                two_ruler_manifest_path, repo_root=ROOT
            ),
            "two_ruler/summary": relative_artifact_descriptor(
                two_ruler_summary_path, repo_root=ROOT
            ),
            "two_ruler/execution_receipt": relative_artifact_descriptor(
                two_ruler_receipt_path, repo_root=ROOT
            ),
            "credit_controls/summary": relative_artifact_descriptor(
                credit_summary_path, repo_root=ROOT
            ),
            "credit_controls/execution_receipt": relative_artifact_descriptor(
                credit_receipt_path, repo_root=ROOT
            ),
            "credit_controls/freeze": relative_artifact_descriptor(
                credit_freeze_path, repo_root=ROOT
            ),
            **{
                f"credit_controls/outcome_free/{name}": relative_artifact_descriptor(
                    path, repo_root=ROOT
                )
                for name, path in credit_outcome_free_artifacts.items()
            },
            **{
                f"credit_controls/models/{name}": relative_artifact_descriptor(path, repo_root=ROOT)
                for name, path in credit_model_artifacts.items()
            },
            "raw_data_audit/manifest": relative_artifact_descriptor(raw_audit_path, repo_root=ROOT),
            "label_lag_sensitivity/manifest": relative_artifact_descriptor(
                lag_evidence_path, repo_root=ROOT
            ),
            "label_lag_sensitivity/table": relative_artifact_descriptor(
                lag_table_path, repo_root=ROOT
            ),
            "endpoint_availability_sensitivity/summary": relative_artifact_descriptor(
                endpoint_summary_path, repo_root=ROOT
            ),
            **{
                f"endpoint_availability_sensitivity/{name}": relative_artifact_descriptor(
                    path, repo_root=ROOT
                )
                for name, path in endpoint_sensitivity_artifacts.items()
            },
            "solver_tie_audit/manifest": relative_artifact_descriptor(
                tie_evidence_path, repo_root=ROOT
            ),
            **{
                f"two_ruler/evaluation/{name}": relative_artifact_descriptor(path, repo_root=ROOT)
                for name, path in two_ruler_evaluation_artifacts.items()
            },
            **{
                f"credit_controls/evaluation/{name}": relative_artifact_descriptor(
                    path, repo_root=ROOT
                )
                for name, path in credit_evaluation_artifacts.items()
            },
            **{
                f"raw_data_audit/{name}": relative_artifact_descriptor(path, repo_root=ROOT)
                for name, path in raw_audit_artifacts.items()
            },
        },
        "paper_artifacts": {
            **{
                f"table/{name}": staged_artifact_descriptor(
                    path,
                    TABLE_TARGETS[name],
                    repo_root=ROOT,
                )
                for name, path in table_paths.items()
            },
            **{
                f"figure/{name}/{kind}": staged_artifact_descriptor(
                    path,
                    figure_targets[name][kind],
                    repo_root=ROOT,
                )
                for name, paths in figures.items()
                for kind, path in paths.items()
            },
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    evidence["claim_ledger"] = materialize_claim_ledger(
        CLAIM_LEDGER_PATH,
        evidence=evidence,
        repo_root=ROOT,
    )
    staged_manifest = staged_output_path(staging_root, EVIDENCE_PATH, repo_root=ROOT)
    atomic_write_strict_json(staged_manifest, evidence)
    promote_publication_generation(
        publication_outputs,
        staged_manifest=staged_manifest,
        manifest_target=EVIDENCE_PATH,
        repo_root=ROOT,
        transaction_root=staging_root,
    )
    logger.info("Built one transactional active IJDS V4 evidence generation: {}", EVIDENCE_PATH)
    return EVIDENCE_PATH


def build_evidence() -> Path:
    """Build and atomically promote one complete paper-facing generation."""
    staging_parent = ROOT / "reports/crpto"
    staging_parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".ijds-v4-generation-", dir=staging_parent) as staging:
        return _build_evidence(Path(staging))


if __name__ == "__main__":
    build_evidence()
