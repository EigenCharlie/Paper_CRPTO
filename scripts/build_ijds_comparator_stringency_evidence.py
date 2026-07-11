"""Build paper-facing evidence for the locked comparator-stringency audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
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
RUN_TAG = "champion-reopen-2026-07-10__maturity-safe-v2-comparator-stringency-audit-v1"
PROTOCOL_TAG = "protocol/ijds-maturity-safe-v2-comparator-stringency-audit-2026-07-10-v1"
PROTOCOL_COMMIT = "ca632ccfbbfaec0e6cdf482a279468665cdb62c0"
DATA_ROOT = ROOT / "data" / "processed" / "experiments" / "champion_reopen" / RUN_TAG
MODEL_ROOT = ROOT / "models" / "experiments" / "champion_reopen" / RUN_TAG
SUMMARY_PATH = MODEL_ROOT / "comparator_stringency_audit_summary.json"
RECEIPT_PATH = MODEL_ROOT / "execution_receipt.json"
TABLE_ROOT = ROOT / "reports" / "crpto" / "tables"
FIGURE_ROOT = ROOT / "reports" / "crpto" / "figures"
MANIFEST_PATH = ROOT / "reports" / "crpto" / "ijds_comparator_stringency_evidence.json"
LGD = 0.45

SELECTED_LABEL = "selected_conformal_guardrail"
SAME_THRESHOLD_LABEL = "same_threshold_point_pd"
MATCHED_LABEL = "development_matched_point_pd"
LOW_LABEL = "development_matched_point_pd_low"
HIGH_LABEL = "development_matched_point_pd_high"
SELECTED_ORDER = [SELECTED_LABEL, SAME_THRESHOLD_LABEL, LOW_LABEL, MATCHED_LABEL, HIGH_LABEL]
POLICY_NAMES = {
    SELECTED_LABEL: "Conformal guardrail",
    SAME_THRESHOLD_LABEL: "Point PD, same numeric threshold",
    LOW_LABEL: "Point PD, development match (low)",
    MATCHED_LABEL: "Point PD, development match (mean)",
    HIGH_LABEL: "Point PD, development match (high)",
}


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


def _verify_descriptor(path: Path, descriptor: dict[str, Any], *, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    if int(descriptor["bytes"]) != path.stat().st_size:
        raise RuntimeError(f"{label} byte count changed: {path}")
    if str(descriptor["sha256"]) != _sha256(path):
        raise RuntimeError(f"{label} hash changed: {path}")


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


def _verify_run(summary: dict[str, Any], receipt: dict[str, Any]) -> None:
    _verify_git_binding()
    if summary.get("status") != "complete" or summary.get("run_tag") != RUN_TAG:
        raise RuntimeError("Comparator audit summary is incomplete or has the wrong run tag.")
    if summary.get("protocol_commit") != PROTOCOL_COMMIT:
        raise RuntimeError("Comparator audit summary is bound to the wrong protocol commit.")
    if summary.get("posthoc_diagnostic_after_active_results") is not True:
        raise RuntimeError("The comparator audit must remain explicitly post hoc.")
    if summary.get("protected_stages_run") or summary.get("protected_artifacts_written"):
        raise RuntimeError("The comparator audit reports a protected-stage mutation.")
    for state_name in ("initial_git", "final_git"):
        state = receipt[state_name]
        if state.get("commit") != PROTOCOL_COMMIT or state.get("dirty") is not False:
            raise RuntimeError(f"Execution receipt has invalid {state_name}: {state}")
    _verify_descriptor(SUMMARY_PATH, receipt["deterministic_summary"], label="Summary")
    for relative, artifact in summary["artifacts"].items():
        if relative != artifact["path"]:
            raise RuntimeError(f"Artifact descriptor path mismatch: {relative}")
        _verify_descriptor(ROOT / relative, artifact, label="Run artifact")
    replay = summary["parent"]["allocation_replay_max_abs_difference"]
    if any(abs(float(value)) > 1e-12 for value in replay.values()):
        raise RuntimeError(f"Parent allocation replay drifted: {replay}")
    gate = summary["primary"]["decision_gate"]
    if gate.get("headline_eligible") is not True:
        raise RuntimeError("The locked selected-policy decision gate did not pass.")
    if summary["family_census"].get("family_direction_claim_allowed") is not False:
        raise RuntimeError("The evidence builder expects the locked 9-of-9 family gate to fail.")


def _write_table(frame: pd.DataFrame, stem: str) -> list[Path]:
    TABLE_ROOT.mkdir(parents=True, exist_ok=True)
    csv_path = atomic_write_text(
        TABLE_ROOT / f"{stem}.csv",
        frame.to_csv(index=False, lineterminator="\n"),
    )
    tex_path = atomic_write_text(
        TABLE_ROOT / f"{stem}.tex",
        frame.to_latex(
            index=False,
            escape=True,
            float_format=lambda value: f"{value:.6f}",
        ),
    )
    return [csv_path, tex_path]


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


def _selected_aggregates(aggregate: pd.DataFrame) -> pd.DataFrame:
    primary = aggregate.loc[
        aggregate["role"].eq("primary_oot") & aggregate["policy_label"].isin(SELECTED_ORDER)
    ].copy()
    thresholds = {
        SELECTED_LABEL: 0.17,
        SAME_THRESHOLD_LABEL: 0.17,
        LOW_LABEL: 0.06503179389092847,
        MATCHED_LABEL: 0.06831339893217318,
        HIGH_LABEL: 0.07170531506384897,
    }
    score = dict.fromkeys(SELECTED_ORDER, "point_pd")
    score[SELECTED_LABEL] = "blended_conformal_score"
    primary["policy"] = primary["policy_label"].map(POLICY_NAMES)
    primary["constraint_score"] = primary["policy_label"].map(score)
    primary["risk_tolerance"] = primary["policy_label"].map(thresholds)
    primary["risk_cap_slack"] = primary["risk_tolerance"] - primary["weighted_pd_effective"]
    primary["expected_payoff_rate"] = primary["expected_objective"] / primary["total_budget"]
    primary["realized_payoff_rate_lower"] = (
        primary["realized_payoff_lower"] / primary["total_budget"]
    )
    primary["realized_payoff_rate_upper"] = (
        primary["realized_payoff_upper"] / primary["total_budget"]
    )
    primary["order"] = primary["policy_label"].map(
        {label: index for index, label in enumerate(SELECTED_ORDER)}
    )
    columns = [
        "policy_label",
        "policy",
        "constraint_score",
        "risk_tolerance",
        "risk_cap_slack",
        "months",
        "total_budget",
        "expected_objective",
        "expected_payoff_rate",
        "realized_payoff_lower",
        "realized_payoff_upper",
        "realized_payoff_rate_lower",
        "realized_payoff_rate_upper",
        "weighted_pd_point",
        "weighted_pd_effective",
        "weighted_default_lower",
        "weighted_default_upper",
        "weighted_miscoverage_lower",
        "weighted_miscoverage_upper",
        "unresolved_exposure_share",
    ]
    return primary.sort_values("order", kind="mergesort")[columns].reset_index(drop=True)


def _baseline_inversion(
    selected_contrasts: pd.DataFrame,
    selected_aggregates: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label, role in (
        (SAME_THRESHOLD_LABEL, "same_numeric_threshold_secondary"),
        (MATCHED_LABEL, "development_mean_point_risk_primary"),
    ):
        contrast = selected_contrasts.loc[selected_contrasts["policy_b"].eq(label)].iloc[0]
        baseline = selected_aggregates.loc[selected_aggregates["policy_label"].eq(label)].iloc[0]
        rows.append(
            {
                "baseline": label,
                "comparison_role": role,
                "baseline_risk_tolerance": baseline["risk_tolerance"],
                "baseline_weighted_point_pd": baseline["weighted_pd_point"],
                "baseline_risk_cap_slack": baseline["risk_cap_slack"],
                "expected_payoff_difference": contrast["expected_objective_difference"],
                "realized_payoff_difference_lower": contrast["realized_payoff_difference_lower"],
                "realized_payoff_difference_upper": contrast["realized_payoff_difference_upper"],
                "weighted_default_difference_lower": contrast["weighted_default_difference_lower"],
                "weighted_default_difference_upper": contrast["weighted_default_difference_upper"],
                "weighted_miscoverage_difference_lower": contrast[
                    "weighted_miscoverage_difference_lower"
                ],
                "weighted_miscoverage_difference_upper": contrast[
                    "weighted_miscoverage_difference_upper"
                ],
            }
        )
    return pd.DataFrame(rows)


def _development_table(aggregate: pd.DataFrame) -> pd.DataFrame:
    selected = aggregate.loc[
        aggregate["role"].eq("policy_development") & aggregate["policy_label"].isin(SELECTED_ORDER)
    ].copy()
    selected["policy"] = selected["policy_label"].map(POLICY_NAMES)
    selected["order"] = selected["policy_label"].map(
        {label: index for index, label in enumerate(SELECTED_ORDER)}
    )
    columns = [
        "policy_label",
        "policy",
        "months",
        "expected_objective",
        "realized_payoff_lower",
        "weighted_pd_point",
        "weighted_pd_effective",
        "weighted_default_lower",
        "weighted_miscoverage_lower",
    ]
    return selected.sort_values("order", kind="mergesort")[columns].reset_index(drop=True)


def _family_table(family: pd.DataFrame, thresholds: pd.DataFrame) -> pd.DataFrame:
    joined = family.merge(
        thresholds[
            [
                "candidate_id",
                "guardrail_risk_tolerance",
                "gamma",
                "matched_point_pd_mean",
            ]
        ],
        on="candidate_id",
        validate="one_to_one",
    )
    columns = [
        "candidate_id",
        "guardrail_risk_tolerance",
        "gamma",
        "matched_point_pd_mean",
        "expected_objective_difference",
        "realized_payoff_difference_lower",
        "realized_payoff_difference_upper",
        "weighted_default_difference_lower",
        "weighted_default_difference_upper",
        "weighted_miscoverage_difference_lower",
        "weighted_miscoverage_difference_upper",
        "payoff_guardrail_worse",
        "default_guardrail_worse",
        "miscoverage_guardrail_worse",
    ]
    return joined.sort_values("candidate_id", kind="mergesort")[columns].reset_index(drop=True)


def _monthly_contrasts(allocations: pd.DataFrame) -> pd.DataFrame:
    primary = allocations.loc[allocations["role"].eq("primary_oot")]
    rows: list[dict[str, Any]] = []
    for baseline in (SAME_THRESHOLD_LABEL, MATCHED_LABEL):
        for period in sorted(primary["period"].astype(str).unique()):
            month = primary.loc[primary["period"].astype(str).eq(period)]
            contrast = sharp_policy_contrast_bounds(
                month,
                policy_a=SELECTED_LABEL,
                policy_b=baseline,
                role="primary_oot",
                lgd=LGD,
            )
            contrast["period"] = period
            rows.append(contrast)
    return pd.DataFrame(rows).sort_values(["policy_b", "period"], kind="mergesort")


def _extension_table(aggregate: pd.DataFrame) -> pd.DataFrame:
    return aggregate.loc[
        aggregate["role"].eq("censored_extension")
        & aggregate["policy_label"].isin((SELECTED_LABEL, SAME_THRESHOLD_LABEL, MATCHED_LABEL))
    ].sort_values("policy_label", kind="mergesort")


def _alignment_figure(selected: pd.DataFrame) -> plt.Figure:
    labels = [SELECTED_LABEL, SAME_THRESHOLD_LABEL, MATCHED_LABEL]
    frame = selected.set_index("policy_label").loc[labels]
    names = ["Guardrail\nq cap", "Point PD\nsame tau", "Point PD\ndev.-matched"]
    colors = ["#246A73", "#D97941", "#4F6D9A"]
    x = np.arange(len(labels))
    figure, axis = plt.subplots(figsize=(7.8, 3.7))
    axis.bar(x, frame["weighted_pd_effective"], width=0.58, color=colors)
    axis.scatter(
        x,
        frame["risk_tolerance"],
        marker="_",
        s=900,
        linewidths=3,
        color="#202020",
        label="Configured cap",
        zorder=3,
    )
    for index, row in enumerate(frame.itertuples()):
        axis.text(
            index,
            float(row.weighted_pd_effective) + 0.005,
            f"{float(row.weighted_pd_effective):.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    axis.set_xticks(x, names)
    axis.set_ylabel("Exposure-weighted constraint score")
    axis.set_ylim(0.0, 0.195)
    axis.set_title("Equal numeric thresholds do not imply equal decision stringency")
    axis.grid(axis="y", alpha=0.2)
    axis.legend(frameon=False, loc="upper right")
    figure.tight_layout()
    return figure


def _selected_contrast_figure(contrasts: pd.DataFrame) -> plt.Figure:
    order = [SAME_THRESHOLD_LABEL, LOW_LABEL, MATCHED_LABEL, HIGH_LABEL]
    frame = contrasts.set_index("policy_b").loc[order]
    names = ["Same tau", "Dev. low", "Dev. mean", "Dev. high"]
    metrics = (
        (
            "realized_payoff_rate_difference_lower",
            "realized_payoff_rate_difference_upper",
            "Payoff rate",
        ),
        ("weighted_default_difference_lower", "weighted_default_difference_upper", "Default"),
        (
            "weighted_miscoverage_difference_lower",
            "weighted_miscoverage_difference_upper",
            "Miscoverage",
        ),
    )
    figure, axes = plt.subplots(1, 3, figsize=(11.2, 4.0), sharey=True)
    y = np.arange(len(frame))
    for axis, (lower_name, upper_name, title) in zip(axes, metrics, strict=True):
        lower = frame[lower_name].to_numpy(dtype=float)
        upper = frame[upper_name].to_numpy(dtype=float)
        midpoint = (lower + upper) / 2.0
        errors = np.vstack((midpoint - lower, upper - midpoint))
        colors = ["#D97941" if name == SAME_THRESHOLD_LABEL else "#246A73" for name in order]
        for index in range(len(frame)):
            axis.errorbar(
                midpoint[index],
                y[index],
                xerr=errors[:, index : index + 1],
                fmt="o",
                color=colors[index],
                capsize=3,
            )
        axis.axvline(0.0, color="#202020", lw=0.9)
        axis.set_title(title)
        axis.grid(axis="x", alpha=0.2)
    axes[0].set_yticks(y, names)
    axes[0].invert_yaxis()
    figure.suptitle("Guardrail-minus-point conclusions reverse after development matching")
    figure.tight_layout()
    return figure


def _family_figure(family: pd.DataFrame) -> plt.Figure:
    frame = family.sort_values("candidate_id", kind="mergesort")
    names = [value.replace("linear-00", "L") for value in frame["candidate_id"]]
    metrics = (
        (
            "realized_payoff_difference_lower",
            "realized_payoff_difference_upper",
            "Payoff ($ thousands)",
            0.001,
        ),
        ("weighted_default_difference_lower", "weighted_default_difference_upper", "Default", 1.0),
        (
            "weighted_miscoverage_difference_lower",
            "weighted_miscoverage_difference_upper",
            "Miscoverage",
            1.0,
        ),
    )
    figure, axes = plt.subplots(1, 3, figsize=(11.4, 4.5), sharey=True)
    y = np.arange(len(frame))
    for axis, (lower_name, upper_name, title, scale) in zip(axes, metrics, strict=True):
        lower = frame[lower_name].to_numpy(dtype=float) * scale
        upper = frame[upper_name].to_numpy(dtype=float) * scale
        midpoint = (lower + upper) / 2.0
        errors = np.vstack((midpoint - lower, upper - midpoint))
        for index in range(len(frame)):
            sign_robust = lower[index] > 0.0 or upper[index] < 0.0
            axis.errorbar(
                midpoint[index],
                y[index],
                xerr=errors[:, index : index + 1],
                fmt="o",
                color="#246A73" if sign_robust else "#9A9A9A",
                capsize=2.5,
            )
        axis.axvline(0.0, color="#202020", lw=0.9)
        axis.set_title(title)
        axis.grid(axis="x", alpha=0.2)
    axes[0].set_yticks(y, names)
    axes[0].invert_yaxis()
    figure.suptitle("The post hoc family census is heterogeneous, not 9-of-9")
    figure.tight_layout()
    return figure


def _monthly_figure(monthly: pd.DataFrame) -> plt.Figure:
    frame = monthly.loc[monthly["policy_b"].eq(MATCHED_LABEL)].sort_values(
        "period", kind="mergesort"
    )
    metrics = (
        (
            "realized_payoff_rate_difference_lower",
            "realized_payoff_rate_difference_upper",
            "Payoff rate",
        ),
        ("weighted_default_difference_lower", "weighted_default_difference_upper", "Default"),
        (
            "weighted_miscoverage_difference_lower",
            "weighted_miscoverage_difference_upper",
            "Miscoverage",
        ),
    )
    x = np.arange(len(frame))
    figure, axes = plt.subplots(3, 1, figsize=(10.4, 7.0), sharex=True)
    for axis, (lower_name, upper_name, title) in zip(axes, metrics, strict=True):
        lower = frame[lower_name].to_numpy(dtype=float)
        upper = frame[upper_name].to_numpy(dtype=float)
        midpoint = (lower + upper) / 2.0
        axis.vlines(x, lower, upper, color="#246A73", lw=2)
        axis.scatter(x, midpoint, color="#246A73", s=18, zorder=3)
        axis.axhline(0.0, color="#202020", lw=0.9)
        axis.set_ylabel(title)
        axis.grid(axis="y", alpha=0.2)
    axes[-1].set_xticks(x, frame["period"], rotation=45, ha="right")
    figure.suptitle("Monthly guardrail-minus-development-matched point-PD contrasts")
    figure.tight_layout()
    return figure


def _output_descriptor(path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def build() -> Path:
    """Validate the locked run and regenerate comparator-audit evidence."""
    summary = _json(SUMMARY_PATH)
    receipt = _json(RECEIPT_PATH)
    _verify_run(summary, receipt)

    portfolio_root = DATA_ROOT / "portfolio"
    aggregate = pd.read_csv(portfolio_root / "comparator_aggregate.csv")
    selected_contrasts = pd.read_csv(portfolio_root / "selected_primary_contrasts.csv")
    family = pd.read_csv(portfolio_root / "family_primary_contrasts.csv")
    thresholds = pd.read_csv(portfolio_root / "matched_thresholds.csv")
    allocations = pd.read_parquet(portfolio_root / "comparator_monthly_funded_allocations.parquet")
    primary_lomo = pd.read_csv(portfolio_root / "primary_leave_one_month_out.csv")
    selector_lomo = pd.read_csv(portfolio_root / "selector_leave_one_month_out.csv")
    payoff = pd.read_csv(portfolio_root / "payoff_decomposition.csv")
    lgd_break_even = pd.read_csv(portfolio_root / "lgd_break_even.csv")
    geometry = pd.read_csv(portfolio_root / "score_geometry.csv")
    transport = pd.read_csv(portfolio_root / "selected_transport_decomposition.csv")
    groups = pd.read_csv(portfolio_root / "funded_group_exposure.csv")

    selected = _selected_aggregates(aggregate)
    inversion = _baseline_inversion(selected_contrasts, selected)
    development = _development_table(aggregate)
    family_table = _family_table(family, thresholds)
    monthly = _monthly_contrasts(allocations)
    extension = _extension_table(aggregate)
    primary_groups = groups.loc[
        groups["role"].eq("primary_oot")
        & groups["policy_label"].isin((SELECTED_LABEL, SAME_THRESHOLD_LABEL, MATCHED_LABEL))
    ].copy()

    if not bool((transport["identity_residual"].abs() <= 1e-12).all()):
        raise RuntimeError("A comparator transport identity no longer reconciles.")
    matched = selected_contrasts.loc[selected_contrasts["policy_b"].eq(MATCHED_LABEL)].iloc[0]
    if not (
        float(matched["realized_payoff_difference_upper"]) < 0.0
        and float(matched["weighted_default_difference_lower"]) > 0.0
        and float(matched["weighted_miscoverage_difference_lower"]) > 0.0
    ):
        raise RuntimeError("The selected development-matched contrast no longer passes.")

    outputs: list[Path] = []
    tables = {
        "crpto_ijds_cs_table1_baseline_alignment": selected,
        "crpto_ijds_cs_table2_primary_inversion": inversion,
        "crpto_ijds_cs_table3_family_census": family_table,
        "crpto_ijds_cs_tableS1_matched_thresholds": thresholds,
        "crpto_ijds_cs_tableS2_development_aggregates": development,
        "crpto_ijds_cs_tableS3_selected_sensitivity": selected_contrasts,
        "crpto_ijds_cs_tableS4_primary_leave_one_month_out": primary_lomo,
        "crpto_ijds_cs_tableS5_selector_leave_one_month_out": selector_lomo,
        "crpto_ijds_cs_tableS6_payoff_decomposition": payoff,
        "crpto_ijds_cs_tableS7_lgd_break_even": lgd_break_even,
        "crpto_ijds_cs_tableS8_score_geometry": geometry,
        "crpto_ijds_cs_tableS9_transport": transport,
        "crpto_ijds_cs_tableS10_group_exposure": primary_groups,
        "crpto_ijds_cs_tableS11_monthly_contrasts": monthly,
        "crpto_ijds_cs_tableS12_extension": extension,
    }
    for stem, frame in tables.items():
        outputs.extend(_write_table(frame, stem))
    outputs.extend(_save_figure(_alignment_figure(selected), "crpto_ijds_cs_fig1_alignment"))
    outputs.extend(
        _save_figure(
            _selected_contrast_figure(selected_contrasts),
            "crpto_ijds_cs_fig2_selected_contrasts",
        )
    )
    outputs.extend(_save_figure(_family_figure(family_table), "crpto_ijds_cs_fig3_family"))
    outputs.extend(_save_figure(_monthly_figure(monthly), "crpto_ijds_cs_fig4_monthly"))

    manifest = {
        "schema_version": "2026-07-10.1",
        "status": "active_posthoc_comparator_stringency_evidence",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": PROTOCOL_COMMIT,
        "posthoc_diagnostic_after_active_results": True,
        "summary": _output_descriptor(SUMMARY_PATH),
        "receipt": _output_descriptor(RECEIPT_PATH),
        "parent": summary["parent"],
        "headline": {
            "decision_gate": summary["primary"]["decision_gate"],
            "same_threshold_contrast": summary["primary"]["same_threshold_contrast"],
            "development_matched_contrast": summary["primary"]["development_matched_contrast"],
            "threshold_sensitivity_contrasts": summary["primary"][
                "threshold_sensitivity_contrasts"
            ],
            "family_census": {
                key: value
                for key, value in summary["family_census"].items()
                if key != "primary_contrasts"
            },
            "selected_thresholds": summary["matching"]["selected_thresholds"],
        },
        "outputs": [_output_descriptor(path) for path in sorted(outputs)],
    }
    atomic_write_json(MANIFEST_PATH, manifest)
    logger.info("Wrote {} comparator-stringency evidence artifacts", len(outputs))
    return MANIFEST_PATH


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description=__doc__).parse_args()


if __name__ == "__main__":
    parse_args()
    build()
