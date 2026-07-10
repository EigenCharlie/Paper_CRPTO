"""Build deterministic paper evidence from the locked maturity-safe IJDS run."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from itertools import product
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd
from loguru import logger

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.evaluation.policy_contrast_bounds import sharp_policy_contrast_bounds
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_text

ROOT = Path(__file__).resolve().parents[1]
RUN_TAG = "champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2"
PROTOCOL_TAG = "protocol/ijds-maturity-safe-locked-bounded-h1h2-2026-07-10-v2"
PROTOCOL_COMMIT = "78a64fe67a4df46c3d19b9243deb991c56fd1ff6"
MODEL_ROOT = ROOT / "models" / "experiments" / "champion_reopen" / RUN_TAG
DATA_ROOT = ROOT / "data" / "processed" / "experiments" / "champion_reopen" / RUN_TAG
SUMMARY_PATH = MODEL_ROOT / "maturity_safe_locked_summary.json"
RECEIPT_PATH = MODEL_ROOT / "execution_receipt.json"
TABLE_ROOT = ROOT / "reports" / "crpto" / "tables"
FIGURE_ROOT = ROOT / "reports" / "crpto" / "figures"
MANIFEST_PATH = ROOT / "reports" / "crpto" / "ijds_maturity_safe_evidence.json"
LGD = 0.45

POLICY_NAMES = {
    "selected_conformal_guardrail": "Conformal guardrail",
    "matched_point_pd": "Point PD, matched tau",
    "development_selected_point_pd": "Point PD, development-selected tau",
}
POLICY_ORDER = list(POLICY_NAMES)


def _sha256(path: Path, *, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a JSON object: {path}")
    return payload


def _verify_git_binding() -> None:
    tagged = subprocess.run(
        ["git", "rev-list", "-n", "1", PROTOCOL_TAG],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if tagged != PROTOCOL_COMMIT:
        raise RuntimeError(f"Protocol tag resolves to {tagged}, expected {PROTOCOL_COMMIT}.")


def _verify_descriptor(path: Path, descriptor: dict[str, Any], *, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    if int(descriptor["bytes"]) != path.stat().st_size:
        raise RuntimeError(f"{label} byte count changed: {path}")
    if descriptor["sha256"] != _sha256(path):
        raise RuntimeError(f"{label} hash changed: {path}")


def _verify_run(summary: dict[str, Any], receipt: dict[str, Any], *, verify_raw: bool) -> None:
    _verify_git_binding()
    if summary.get("status") != "complete" or summary.get("run_tag") != RUN_TAG:
        raise RuntimeError("The maturity-safe summary is incomplete or has the wrong run tag.")
    if summary.get("protocol_commit") != PROTOCOL_COMMIT:
        raise RuntimeError("Summary protocol commit does not match the locked commit.")
    for state_name in ("initial_git", "final_git"):
        state = receipt[state_name]
        if state.get("commit") != PROTOCOL_COMMIT or state.get("dirty") is not False:
            raise RuntimeError(f"Execution receipt has invalid {state_name}: {state}")
    _verify_descriptor(
        SUMMARY_PATH,
        receipt["deterministic_summary"],
        label="Summary",
    )
    for relative, artifact in summary["artifacts"].items():
        _verify_descriptor(ROOT / relative, artifact, label="Run artifact")
    if verify_raw:
        raw = summary["raw_source"]
        _verify_descriptor(ROOT / raw["path"], raw, label="Raw source")


def _write_table(frame: pd.DataFrame, stem: str) -> list[Path]:
    TABLE_ROOT.mkdir(parents=True, exist_ok=True)
    csv_path = atomic_write_text(
        TABLE_ROOT / f"{stem}.csv",
        frame.to_csv(index=False, lineterminator="\n"),
    )
    tex = frame.to_latex(
        index=False,
        escape=True,
        float_format=lambda value: f"{value:.6f}",
    )
    tex_path = atomic_write_text(TABLE_ROOT / f"{stem}.tex", tex)
    return [csv_path, tex_path]


def _protocol_table(summary: dict[str, Any], split_inventory: pd.DataFrame) -> pd.DataFrame:
    boundaries = summary["maturity_contract"]["block_boundaries"]
    order = [
        "pd_development",
        "probability_calibration",
        "conformal_fit",
        "policy_development",
        "primary_oot",
        "censored_extension",
    ]
    inventory = split_inventory.pivot_table(
        index="design_split",
        columns="snapshot_resolution",
        values="rows",
        aggfunc="sum",
        fill_value=0,
    )
    rows: list[dict[str, Any]] = []
    for split in order:
        counts = inventory.loc[split]
        rows.append(
            {
                "block": split,
                "first_issue_month": boundaries[split]["first_issue_month"],
                "last_issue_month": boundaries[split]["last_issue_month"],
                "rows": int(counts.sum()),
                "resolved_default": int(counts.get("default", 0)),
                "resolved_nondefault": int(counts.get("nondefault", 0)),
                "unresolved": int(counts.get("unresolved", 0)),
                "role": (
                    "fit_or_select"
                    if split
                    in {
                        "pd_development",
                        "probability_calibration",
                        "conformal_fit",
                        "policy_development",
                    }
                    else "locked_evaluation"
                ),
            }
        )
    return pd.DataFrame(rows)


def _primary_policy_table(summary: dict[str, Any]) -> pd.DataFrame:
    aggregate = pd.DataFrame(summary["monthly_evaluation"]["aggregate_by_role_and_policy"])
    primary = aggregate.loc[aggregate["role"].eq("primary_oot")].copy()
    primary["policy"] = primary["policy_label"].map(POLICY_NAMES)
    primary["expected_payoff_rate"] = primary["expected_objective"] / primary["total_budget"]
    primary["realized_payoff_rate_lower"] = (
        primary["realized_payoff_lower"] / primary["total_budget"]
    )
    primary["realized_payoff_rate_upper"] = (
        primary["realized_payoff_upper"] / primary["total_budget"]
    )
    primary["coverage_lower"] = 1.0 - primary["weighted_miscoverage_upper"]
    primary["coverage_upper"] = 1.0 - primary["weighted_miscoverage_lower"]
    primary["order"] = primary["policy_label"].map({name: i for i, name in enumerate(POLICY_ORDER)})
    columns = [
        "policy",
        "months",
        "total_budget",
        "expected_objective",
        "expected_payoff_rate",
        "realized_payoff_lower",
        "realized_payoff_upper",
        "realized_payoff_rate_lower",
        "realized_payoff_rate_upper",
        "weighted_default_lower",
        "weighted_default_upper",
        "weighted_miscoverage_lower",
        "weighted_miscoverage_upper",
        "coverage_lower",
        "coverage_upper",
        "unresolved_exposure_share",
    ]
    return primary.sort_values("order", kind="mergesort")[columns].reset_index(drop=True)


def _development_to_oot_table(summary: dict[str, Any]) -> pd.DataFrame:
    selection = summary["selection"]
    guard = next(
        row
        for row in selection["guardrail_grid"]
        if row["candidate_id"] == selection["selected_guardrail"]["candidate_id"]
    )
    point = next(
        row
        for row in selection["point_grid"]
        if row["candidate_id"] == selection["development_selected_point_pd"]["candidate_id"]
    )
    primary = next(
        row
        for row in summary["monthly_evaluation"]["primary_retrospective_contrasts"]
        if row["policy_b"] == "development_selected_point_pd"
    )
    development = {
        "block": "policy_development_2012H2",
        "months": int(guard["months"]),
        "expected_payoff_difference": guard["expected_objective"] - point["expected_objective"],
        "realized_payoff_difference_lower": guard["realized_payoff"] - point["realized_payoff"],
        "realized_payoff_difference_upper": guard["realized_payoff"] - point["realized_payoff"],
        "weighted_default_difference_lower": guard["weighted_default"] - point["weighted_default"],
        "weighted_default_difference_upper": guard["weighted_default"] - point["weighted_default"],
        "weighted_miscoverage_difference_lower": guard["weighted_miscoverage"]
        - point["weighted_miscoverage"],
        "weighted_miscoverage_difference_upper": guard["weighted_miscoverage"]
        - point["weighted_miscoverage"],
        "outcome_status": "resolved_exact",
    }
    locked_primary = {
        "block": "locked_primary_2016-04_to_2017-06",
        "months": int(summary["row_counts"]["primary_oot_months"]),
        "expected_payoff_difference": primary["expected_objective_difference"],
        "realized_payoff_difference_lower": primary["realized_payoff_difference_lower"],
        "realized_payoff_difference_upper": primary["realized_payoff_difference_upper"],
        "weighted_default_difference_lower": primary["weighted_default_difference_lower"],
        "weighted_default_difference_upper": primary["weighted_default_difference_upper"],
        "weighted_miscoverage_difference_lower": primary["weighted_miscoverage_difference_lower"],
        "weighted_miscoverage_difference_upper": primary["weighted_miscoverage_difference_upper"],
        "outcome_status": "sharp_unresolved_outcome_bounds",
    }
    return pd.DataFrame([development, locked_primary])


def _contrast_tables(
    summary: dict[str, Any],
    allocations: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    pooled = pd.DataFrame(summary["monthly_evaluation"]["primary_retrospective_contrasts"])
    monthly_rows: list[dict[str, Any]] = []
    primary = allocations.loc[allocations["role"].eq("primary_oot")]
    for period in sorted(primary["period"].astype(str).unique()):
        month = primary.loc[primary["period"].astype(str).eq(period)]
        record = sharp_policy_contrast_bounds(
            month,
            policy_a="selected_conformal_guardrail",
            policy_b="development_selected_point_pd",
            role="primary_oot",
            lgd=LGD,
        )
        record["period"] = period
        monthly_rows.append(record)
    monthly = pd.DataFrame(monthly_rows).sort_values("period", kind="mergesort")
    return pooled, monthly


def _coverage_table(summary: dict[str, Any]) -> pd.DataFrame:
    fit_audit = pd.read_parquet(DATA_ROOT / "conformal/binary_outcome_fit_audit.parquet")
    fit = {
        "block": "conformal_fit_2012H1",
        "rows": summary["row_counts"]["conformal_fit_2012H1"],
        "resolved_rows": summary["row_counts"]["conformal_fit_2012H1"],
        "unresolved_rows": 0,
        "coverage_lower": summary["conformal"]["fit_empirical_coverage"],
        "coverage_upper": summary["conformal"]["fit_empirical_coverage"],
        "mean_interval_width": float(fit_audit.eval("conformal_upper - conformal_lower").mean()),
        "lower_zero_share": float((fit_audit["conformal_lower"] <= 1e-12).mean()),
        "upper_one_share": float((fit_audit["conformal_upper"] >= 1.0 - 1e-12).mean()),
    }
    rows = [fit]
    for key, block in (
        ("primary_oot_all_candidate_pooled", "primary_oot_2016-04_to_2017-06"),
        ("censored_extension_all_candidate_pooled", "extension_2017-07_to_2017-09"),
    ):
        source = summary["conformal"][key]
        rows.append(
            {
                "block": block,
                "rows": source["rows"],
                "resolved_rows": source["resolved_rows"],
                "unresolved_rows": source["unresolved_rows"],
                "coverage_lower": source["all_candidate_coverage_lower"],
                "coverage_upper": source["all_candidate_coverage_upper"],
                "mean_interval_width": source["mean_interval_width"],
                "lower_zero_share": source["lower_endpoint_zero_share"],
                "upper_one_share": source["upper_endpoint_one_share"],
            }
        )
    return pd.DataFrame(rows)


def _selection_table(summary: dict[str, Any]) -> pd.DataFrame:
    guard = pd.DataFrame(summary["selection"]["guardrail_grid"])
    guard["family"] = "conformal_guardrail"
    guard_parameters = {
        f"linear-{index:03d}": (tau, gamma)
        for index, (tau, gamma) in enumerate(
            product([0.15, 0.17, 0.19], [0.25, 0.50, 0.75]),
            start=1,
        )
    }
    guard["risk_tolerance"] = guard["candidate_id"].map(
        lambda candidate: guard_parameters[str(candidate)][0]
    )
    guard["gamma"] = guard["candidate_id"].map(
        lambda candidate: guard_parameters[str(candidate)][1]
    )
    point = pd.DataFrame(summary["selection"]["point_grid"])
    point["family"] = "point_pd"
    point["risk_tolerance"] = (
        point["candidate_id"].astype(str).str.rsplit("-", n=1).str[-1].astype(float) / 1000.0
    )
    point["gamma"] = 0.0
    combined = pd.concat([guard, point], ignore_index=True, sort=False)
    combined["selected"] = combined["candidate_id"].isin(
        [
            summary["selection"]["selected_guardrail"]["candidate_id"],
            summary["selection"]["development_selected_point_pd"]["candidate_id"],
        ]
    )
    columns = [
        "family",
        "selected",
        "candidate_id",
        "risk_tolerance",
        "gamma",
        "months",
        "expected_objective",
        "realized_payoff",
        "weighted_default",
        "weighted_miscoverage",
    ]
    return combined[columns].sort_values(
        ["family", "realized_payoff", "candidate_id"],
        ascending=[True, False, True],
        kind="mergesort",
    )


def _save_figure(figure: plt.Figure, stem: str) -> list[Path]:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for suffix in ("png", "pdf"):
        path = FIGURE_ROOT / f"{stem}.{suffix}"
        temporary = path.with_name(f".{stem}.tmp.{suffix}")
        metadata = (
            {"CreationDate": None, "ModDate": None, "Creator": "CRPTO evidence builder"}
            if suffix == "pdf"
            else {"Software": "CRPTO evidence builder"}
        )
        figure.savefig(
            temporary,
            dpi=220 if suffix == "png" else None,
            bbox_inches="tight",
            metadata=metadata,
        )
        temporary.replace(path)
        paths.append(path)
    plt.close(figure)
    return paths


def _pipeline_figure() -> plt.Figure:
    figure, axis = plt.subplots(figsize=(10.2, 2.25))
    axis.set_xlim(0.0, 10.2)
    axis.set_ylim(0.0, 2.25)
    axis.axis("off")
    boxes = (
        (1.0, "Decision-time menu\nIssue date + terms\nStatus independent", "#4C78A8"),
        (3.05, "Frozen prediction stack\nPD + Platt + Mondrian\nFrozen by June 2012", "#72B7B2"),
        (5.1, "Policy development\nNine guardrails\nSelect once in 2012H2", "#F2CF5B"),
        (7.15, "Monthly allocation\nFresh $1M budget\nOutcomes isolated", "#B279A2"),
        (9.2, "Post-decision audit\nSharp bounds + contrasts\nSelection transport", "#E45756"),
    )
    for index, (x, label, color) in enumerate(boxes):
        axis.text(
            x,
            1.30,
            label,
            ha="center",
            va="center",
            fontsize=9,
            linespacing=1.35,
            bbox={
                "boxstyle": "round,pad=0.55",
                "facecolor": color,
                "edgecolor": "white",
                "linewidth": 1.2,
                "alpha": 0.95,
            },
            color="black" if color == "#F2CF5B" else "white",
        )
        if index < len(boxes) - 1:
            end_offset = 1.02 if index == len(boxes) - 2 else 0.78
            axis.annotate(
                "",
                xy=(boxes[index + 1][0] - end_offset, 1.30),
                xytext=(x + 0.78, 1.30),
                arrowprops={"arrowstyle": "->", "color": "#333333", "lw": 1.2},
            )
    axis.text(
        5.1,
        0.22,
        "Labels are unavailable to the optimizer and enter only after each allocation is fixed.",
        ha="center",
        va="center",
        fontsize=9.5,
        color="#333333",
    )
    figure.tight_layout(pad=0.2)
    return figure


def _timeline_figure() -> plt.Figure:
    figure, axis = plt.subplots(figsize=(9.2, 3.7))
    colors = ["#4C78A8", "#72B7B2", "#F2CF5B", "#B279A2", "#E45756", "#54A24B"]
    labels = [
        "PD development",
        "Probability calibration",
        "Conformal fit",
        "Policy development",
        "Primary OOT",
        "Bounded extension",
    ]
    starts = [2007.42, 2011.0, 2012.0, 2012.5, 2016.25, 2017.5]
    ends = [2010.99, 2011.99, 2012.49, 2012.99, 2017.49, 2017.74]
    positions = np.arange(len(labels))[::-1]
    for y, start, end, color in zip(positions, starts, ends, colors, strict=True):
        axis.barh(y, end - start, left=start, height=0.58, color=color, edgecolor="white")
    axis.axvspan(2013.0, 2016.24, color="#D9D9D9", alpha=0.35, zorder=0)
    axis.annotate(
        "40-month maturity gap",
        xy=(2016.24, -0.55),
        xytext=(2013.0, -0.55),
        arrowprops={"arrowstyle": "<->", "color": "#444444"},
        ha="center",
        va="center",
        fontsize=9,
    )
    axis.set_xlim(2007.2, 2018.0)
    axis.set_ylim(-1.0, len(labels) - 0.25)
    axis.set_yticks(positions, labels)
    axis.set_xlabel("Loan issue year")
    axis.spines[["left", "right", "top"]].set_visible(False)
    axis.tick_params(axis="y", length=0)
    axis.set_title("Locked chronology: fitting and policy selection precede monthly evaluation")
    figure.tight_layout()
    return figure


def _monthly_figure(monthly: pd.DataFrame) -> plt.Figure:
    selected = monthly.loc[monthly["policy_label"].eq("selected_conformal_guardrail")].copy()
    point = monthly.loc[monthly["policy_label"].eq("development_selected_point_pd")].copy()
    selected["date"] = pd.to_datetime(selected["period"])
    point["date"] = pd.to_datetime(point["period"])
    figure, axes = plt.subplots(3, 1, figsize=(8.8, 7.2), sharex=True)
    colors = {"guard": "#0072B2", "point": "#D55E00"}
    panels = [
        ("realized_payoff", "Standardized payoff rate"),
        ("weighted_default", "Funded default rate"),
        ("weighted_miscoverage", "Funded miscoverage"),
    ]
    for axis, (prefix, ylabel) in zip(axes, panels, strict=True):
        for frame, label, color in (
            (selected, "Conformal guardrail", colors["guard"]),
            (point, "Point PD", colors["point"]),
        ):
            denominator = frame["total_allocated"] if prefix == "realized_payoff" else 1.0
            lower = frame[f"{prefix}_lower"] / denominator
            upper = frame[f"{prefix}_upper"] / denominator
            middle = (lower + upper) / 2.0
            axis.plot(frame["date"], middle, marker="o", markersize=3.5, label=label, color=color)
            axis.fill_between(frame["date"], lower, upper, color=color, alpha=0.18)
        axis.axhline(0.0 if prefix == "realized_payoff" else 0.10, color="#666666", lw=0.8, ls="--")
        axis.set_ylabel(ylabel)
        axis.grid(axis="y", alpha=0.2)
    axes[0].legend(frameon=False, ncol=2, loc="upper left")
    axes[-1].set_xlabel("Issue month")
    figure.suptitle(
        "Locked primary evaluation: performance is temporal and coverage does not transport"
    )
    figure.tight_layout()
    return figure


def _transport_figure(transport: pd.DataFrame) -> plt.Figure:
    lower = transport.loc[transport["completion"].eq("lower")].copy()
    components = [
        "row_minus_reference",
        "row_to_exposure",
        "group_composition",
        "within_group_selection",
    ]
    labels = ["Population", "Exposure", "Group mix", "Within group"]
    figure, axes = plt.subplots(1, 2, figsize=(9.0, 3.8), sharey=False)
    colors = {"selected_conformal_guardrail": "#0072B2", "development_selected_point_pd": "#D55E00"}
    for axis, metric, title in (
        (axes[0], "snapshot_default", "Default transport"),
        (axes[1], "binary_miscoverage", "Miscoverage transport"),
    ):
        metric_frame = lower.loc[lower["metric"].eq(metric)]
        x = np.arange(len(components), dtype=float)
        for offset, policy in (
            (-0.18, "selected_conformal_guardrail"),
            (0.18, "development_selected_point_pd"),
        ):
            row = metric_frame.loc[metric_frame["policy_label"].eq(policy)].iloc[0]
            axis.bar(
                x + offset,
                [float(row[column]) for column in components],
                width=0.34,
                color=colors[policy],
                label=POLICY_NAMES[policy],
            )
        axis.axhline(0.0, color="#333333", lw=0.8)
        axis.set_xticks(x, labels, rotation=24, ha="right")
        axis.set_title(title)
        axis.set_ylabel("Rate contribution")
        axis.grid(axis="y", alpha=0.2)
    axes[0].legend(frameon=False, fontsize=8)
    figure.suptitle("Selection transport is dominated by within-group optimization")
    figure.tight_layout()
    return figure


def _output_descriptor(path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def build(*, verify_raw: bool = False) -> Path:
    """Validate the locked run and regenerate all active paper evidence."""
    summary = _json(SUMMARY_PATH)
    receipt = _json(RECEIPT_PATH)
    _verify_run(summary, receipt, verify_raw=verify_raw)

    split_inventory = pd.read_csv(DATA_ROOT / "data/split_inventory.csv")
    monthly = pd.read_csv(DATA_ROOT / "portfolio/fixed_policy_monthly_evaluation.csv")
    allocations = pd.read_parquet(DATA_ROOT / "portfolio/monthly_funded_allocations.parquet")
    transport = pd.read_csv(DATA_ROOT / "portfolio/selection_transport_decomposition.csv")
    groups = pd.read_csv(DATA_ROOT / "portfolio/funded_group_exposure.csv")
    aggregate = pd.DataFrame(summary["monthly_evaluation"]["aggregate_by_role_and_policy"])

    protocol = _protocol_table(summary, split_inventory)
    primary = _primary_policy_table(summary)
    development_to_oot = _development_to_oot_table(summary)
    contrasts, monthly_contrasts = _contrast_tables(summary, allocations)
    coverage = _coverage_table(summary)
    selection = _selection_table(summary)
    primary_monthly = monthly.loc[monthly["role"].eq("primary_oot")].copy()
    extension = aggregate.loc[aggregate["role"].eq("censored_extension")].copy()
    primary_groups = groups.loc[groups["role"].eq("primary_oot")].copy()

    if not bool((transport["identity_residual"].abs() <= 1e-12).all()):
        raise RuntimeError("A transport identity no longer reconciles.")
    matched = primary.loc[primary["policy"].eq(POLICY_NAMES["matched_point_pd"])]
    selected_point = primary.loc[
        primary["policy"].eq(POLICY_NAMES["development_selected_point_pd"])
    ]
    if not np.allclose(
        matched.select_dtypes(include=[np.number]),
        selected_point.select_dtypes(include=[np.number]),
        rtol=0.0,
        atol=1e-12,
    ):
        raise RuntimeError("Matched and development-selected point policies unexpectedly differ.")

    outputs: list[Path] = []
    tables = {
        "crpto_ijds_ms_table1_protocol": protocol,
        "crpto_ijds_ms_table2_primary_policy": primary,
        "crpto_ijds_ms_table3_primary_contrast": contrasts,
        "crpto_ijds_ms_table4_development_to_oot": development_to_oot,
        "crpto_ijds_ms_tableS1_selection_grid": selection,
        "crpto_ijds_ms_tableS2_coverage": coverage,
        "crpto_ijds_ms_tableS3_monthly_primary": primary_monthly,
        "crpto_ijds_ms_tableS4_transport": transport,
        "crpto_ijds_ms_tableS5_group_exposure": primary_groups,
        "crpto_ijds_ms_tableS6_extension": extension,
        "crpto_ijds_ms_tableS7_monthly_contrast": monthly_contrasts,
    }
    for stem, frame in tables.items():
        outputs.extend(_write_table(frame, stem))
    outputs.extend(_save_figure(_pipeline_figure(), "crpto_ijds_ms_fig0_pipeline"))
    outputs.extend(_save_figure(_timeline_figure(), "crpto_ijds_ms_fig1_timeline"))
    outputs.extend(_save_figure(_monthly_figure(primary_monthly), "crpto_ijds_ms_fig2_monthly"))
    outputs.extend(_save_figure(_transport_figure(transport), "crpto_ijds_ms_fig3_transport"))

    manifest = {
        "schema_version": "2026-07-10.2",
        "status": "active_maturity_safe_ijds_evidence",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": PROTOCOL_COMMIT,
        "summary": _output_descriptor(SUMMARY_PATH),
        "receipt": _output_descriptor(RECEIPT_PATH),
        "headline": {
            "selected_policy": summary["selection"]["selected_guardrail"],
            "primary_all_candidate_coverage_lower": summary["conformal"][
                "primary_oot_all_candidate_pooled"
            ]["all_candidate_coverage_lower"],
            "primary_all_candidate_coverage_upper": summary["conformal"][
                "primary_oot_all_candidate_pooled"
            ]["all_candidate_coverage_upper"],
            "primary_contrasts": summary["monthly_evaluation"]["primary_retrospective_contrasts"],
            "development_to_oot": development_to_oot.to_dict(orient="records"),
        },
        "outputs": [_output_descriptor(path) for path in sorted(outputs)],
    }
    atomic_write_json(MANIFEST_PATH, manifest)
    logger.info("Wrote {} maturity-safe evidence artifacts", len(outputs))
    return MANIFEST_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-raw",
        action="store_true",
        help="Also rehash the 1.7 GB raw snapshot.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build(verify_raw=args.verify_raw)
