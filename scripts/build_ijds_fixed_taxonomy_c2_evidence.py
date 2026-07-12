"""Build paper-facing evidence for the fixed-taxonomy comparator multiverse."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.utils.pipeline_runtime import atomic_write_json, atomic_write_text

ROOT = Path(__file__).resolve().parents[1]
RUN_TAG = "ijds-fixed-taxonomy-c2-2026-07-11-v2"
PROTOCOL_TAG = "protocol/ijds-fixed-taxonomy-c2-2026-07-11-v2"
PROTOCOL_COMMIT = "a88839dfe14875fca2c02c43725291bc49d98611"
SOURCE_RUN_TAG = "ijds-fixed-taxonomy-c2-2026-07-11-v1"
SOURCE_FREEZE_SHA256 = "93690082880ef4ff1375dcd5b26d2df79f80e6ebe09a6d83b7fd99a9abb4cfae"

DATA_ROOT = ROOT / "data/processed/experiments/ijds_prefreeze" / RUN_TAG
SOURCE_DATA_ROOT = ROOT / "data/processed/experiments/ijds_prefreeze" / SOURCE_RUN_TAG
MODEL_ROOT = ROOT / "models/experiments/ijds_prefreeze" / RUN_TAG
SUMMARY_PATH = MODEL_ROOT / "fixed_taxonomy_c2_summary.json"
RECEIPT_PATH = MODEL_ROOT / "execution_receipt.json"
SOURCE_RECORDS_PATH = SOURCE_DATA_ROOT / "portfolio/outcome_free_solve_records.parquet"
SOURCE_ALLOCATIONS_PATH = SOURCE_DATA_ROOT / "portfolio/outcome_free_funded_allocations.parquet"
TABLE_ROOT = ROOT / "reports/crpto/tables"
FIGURE_ROOT = ROOT / "reports/crpto/figures"
MANIFEST_PATH = ROOT / "reports/crpto/ijds_fixed_taxonomy_c2_evidence.json"

EXPECTED_ROWS = {
    "monthly_evaluation": 7347,
    "aggregate_evaluation": 515,
    "paired_sharp_contrasts": 504,
    "temporal_candidate_coverage": 594,
    "simulation_repetitions": 800,
}

POLICY_ORDER = [f"linear-{index:03d}" for index in range(1, 10)]
COMPARATOR_ORDER = ["c0_same_numeric_cap", "c1_development_fixed", "c2_contemporaneous"]
COMPARATOR_NAMES = {
    "c0_same_numeric_cap": "C0: same numeric cap",
    "c1_development_fixed": "C1: fixed development cap",
    "c2_contemporaneous": "C2: contemporaneous funded-PD match",
}


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a JSON object: {path}")
    return payload


def _sha256(path: Path, *, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def _descriptor(path: Path) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(ROOT).as_posix(),
        "bytes": int(path.stat().st_size),
        "sha256": _sha256(path),
    }


def _verify_descriptor(descriptor: dict[str, Any]) -> Path:
    path = (ROOT / str(descriptor["path"])).resolve()
    path.relative_to(ROOT.resolve())
    actual = _descriptor(path)
    if any(actual[field] != descriptor[field] for field in ("path", "bytes", "sha256")):
        raise RuntimeError(f"Artifact descriptor drifted: {path}")
    return path


def _verify_run(summary: dict[str, Any], receipt: dict[str, Any]) -> None:
    tagged = subprocess.run(
        ["git", "rev-list", "-n", "1", PROTOCOL_TAG],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if tagged != PROTOCOL_COMMIT:
        raise RuntimeError(f"Protocol tag resolves to {tagged}, expected {PROTOCOL_COMMIT}.")
    if summary.get("status") != "complete_retrospective_prefreeze_audit":
        raise RuntimeError("Fixed-taxonomy audit summary is incomplete.")
    for field, expected in (
        ("run_tag", RUN_TAG),
        ("protocol_tag", PROTOCOL_TAG),
        ("protocol_commit", PROTOCOL_COMMIT),
    ):
        if summary.get(field) != expected:
            raise RuntimeError(f"Summary {field} does not match the locked protocol.")
    if summary.get("protected_stages_run") or summary.get("protected_artifacts_written"):
        raise RuntimeError("The run reports a protected-stage mutation.")
    lineage = summary["outcome_free_lineage"]
    if lineage.get("source_run_tag") != SOURCE_RUN_TAG:
        raise RuntimeError("Unexpected outcome-free source run.")
    source_freeze = lineage["source_protocol_freeze"]
    if source_freeze.get("sha256") != SOURCE_FREEZE_SHA256:
        raise RuntimeError("Outcome-free source freeze hash changed.")
    _verify_descriptor(source_freeze)
    summary_descriptor = receipt["summary"]
    if _verify_descriptor(summary_descriptor) != SUMMARY_PATH.resolve():
        raise RuntimeError("Receipt points to the wrong summary.")
    if receipt.get("protocol_commit") != PROTOCOL_COMMIT:
        raise RuntimeError("Receipt is bound to the wrong protocol commit.")
    for descriptor in summary["artifacts"].values():
        _verify_descriptor(descriptor)


def _read_inputs(summary: dict[str, Any]) -> dict[str, pd.DataFrame]:
    paths = {
        "monthly": "monthly_evaluation",
        "aggregate": "aggregate_evaluation",
        "contrasts": "paired_sharp_contrasts",
        "coverage": "temporal_candidate_coverage",
        "simulation": "comparator_transport_simulation",
        "simulation_summary": "comparator_transport_simulation_summary",
    }
    frames = {
        name: pd.read_parquet(_verify_descriptor(summary["artifacts"][artifact]))
        for name, artifact in paths.items()
    }
    source_freeze_path = _verify_descriptor(
        summary["outcome_free_lineage"]["source_protocol_freeze"]
    )
    source_freeze = _json(source_freeze_path)
    records_path = _verify_descriptor(source_freeze["outcome_free_artifacts"]["records"])
    if records_path != SOURCE_RECORDS_PATH.resolve():
        raise RuntimeError("Source freeze points to an unexpected solve-record artifact.")
    frames["records"] = pd.read_parquet(records_path)
    allocations_path = _verify_descriptor(source_freeze["outcome_free_artifacts"]["allocations"])
    if allocations_path != SOURCE_ALLOCATIONS_PATH.resolve():
        raise RuntimeError("Source freeze points to an unexpected allocation artifact.")
    frames["allocations"] = pd.read_parquet(allocations_path)
    return frames


def _direction(lower: pd.Series, upper: pd.Series) -> pd.Series:
    result = pd.Series("indeterminate", index=lower.index, dtype="string")
    result.loc[upper < 0.0] = "negative"
    result.loc[lower > 0.0] = "positive"
    return result


def _direction_scalar(lower: float, upper: float) -> str:
    if upper < 0.0:
        return "negative"
    if lower > 0.0:
        return "positive"
    return "indeterminate"


def _comparator_envelopes(contrasts: pd.DataFrame) -> pd.DataFrame:
    """Derive finite-multiverse signs from every canonical comparator record."""
    canonical = _canonical_contrasts(contrasts)
    canonical = canonical.loc[
        canonical["comparator_rule"].isin([*COMPARATOR_ORDER, "point_cap_frontier"])
    ]
    metric_columns = {
        "realized_payoff": (
            "realized_payoff_difference_lower",
            "realized_payoff_difference_upper",
        ),
        "terminal_default": (
            "weighted_default_difference_lower",
            "weighted_default_difference_upper",
        ),
        "funded_miscoverage": (
            "weighted_miscoverage_difference_lower",
            "weighted_miscoverage_difference_upper",
        ),
    }
    rows: list[dict[str, Any]] = []
    for policy in POLICY_ORDER:
        group = canonical.loc[canonical["paired_policy_id"].eq(policy)]
        if len(group) != 32:
            raise RuntimeError(f"Expected 32 multiverse records for {policy}, got {len(group)}.")
        for metric, (lower_column, upper_column) in metric_columns.items():
            lower = float(group[lower_column].min())
            upper = float(group[upper_column].max())
            rows.append(
                {
                    "paired_policy_id": policy,
                    "metric": metric,
                    "lower": lower,
                    "upper": upper,
                    "sign": _direction_scalar(lower, upper),
                    "record_count": int(len(group)),
                }
            )
    return pd.DataFrame(rows)


def _allocation_distances(allocations: pd.DataFrame) -> pd.DataFrame:
    """Recompute canonical score-ablation L1 distances from frozen exposures."""
    rules = (
        "guardrail",
        "ablation_group_penalty",
        "ablation_pooled_affine",
        "ablation_pooled_point",
    )
    frame = allocations.loc[
        allocations["seed"].eq(42)
        & np.isclose(allocations["purpose_cap"], 0.25)
        & np.isclose(allocations["lgd"], 0.45)
        & allocations["role"].eq("primary_oot")
        & allocations["paired_policy_id"].isin(POLICY_ORDER)
        & allocations["comparator_rule"].isin(rules),
        ["paired_policy_id", "comparator_rule", "period", "id", "exposure"],
    ]
    exposure = (
        frame.groupby(
            ["paired_policy_id", "period", "id", "comparator_rule"],
            observed=True,
        )["exposure"]
        .sum()
        .unstack("comparator_rule", fill_value=0.0)
        .reindex(columns=rules, fill_value=0.0)
    )
    distances = pd.DataFrame(index=exposure.index)
    distances["clipped_vs_unclipped_allocation_l1"] = (
        exposure["guardrail"] - exposure["ablation_group_penalty"]
    ).abs()
    distances["unclipped_group_vs_pooled_allocation_l1"] = (
        exposure["ablation_group_penalty"] - exposure["ablation_pooled_affine"]
    ).abs()
    distances["pooled_affine_vs_point_allocation_l1"] = (
        exposure["ablation_pooled_affine"] - exposure["ablation_pooled_point"]
    ).abs()
    result = distances.groupby(level="paired_policy_id", observed=True).sum().reset_index()
    if result["paired_policy_id"].tolist() != POLICY_ORDER:
        raise RuntimeError("Allocation ablations do not cover the complete policy family.")
    if float(result["pooled_affine_vs_point_allocation_l1"].max()) > 1e-8:
        raise RuntimeError("The pooled affine placebo no longer reproduces point PD.")
    return result


def _purpose_cap_binding(allocations: pd.DataFrame) -> dict[str, Any]:
    """Derive binding purpose-cap counts from frozen guardrail allocations."""
    keys = ["seed", "purpose_cap", "paired_policy_id", "period"]
    frame = allocations.loc[
        allocations["comparator_rule"].eq("guardrail")
        & allocations["role"].eq("primary_oot")
        & allocations["paired_policy_id"].isin(POLICY_ORDER)
        & allocations["purpose_cap"].lt(1.0)
        & np.isclose(allocations["lgd"], 0.45),
        [*keys, "purpose", "exposure"],
    ]
    purpose_exposure = frame.groupby([*keys, "purpose"], observed=True)["exposure"].sum()
    total_exposure = purpose_exposure.groupby(level=keys, observed=True).sum()
    max_share = (purpose_exposure / total_exposure).groupby(level=keys, observed=True).max()
    caps = max_share.index.get_level_values("purpose_cap").to_numpy(dtype=float)
    binding = np.isclose(max_share.to_numpy(dtype=float), caps, atol=1e-10, rtol=0.0)
    expected_groups = 5 * 3 * len(POLICY_ORDER) * 15
    if len(max_share) != expected_groups:
        raise RuntimeError(
            f"Purpose-cap audit expected {expected_groups} guardrail-months, got {len(max_share)}."
        )
    return {
        "guardrail_months": int(len(max_share)),
        "binding_guardrail_months": int(binding.sum()),
        "all_bind": bool(binding.all()),
        "maximum_absolute_cap_residual": float(np.abs(max_share.to_numpy() - caps).max()),
    }


def _endpoint_inventory(coverage: pd.DataFrame, summary: dict[str, Any]) -> dict[str, Any]:
    """Reconcile the terminal endpoint with the frozen status diagnostic."""
    by_split: dict[str, dict[str, int]] = {}
    for item in summary["label_availability"]:
        by_split[str(item["design_split"])] = {
            "rows": int(item["total_rows"]),
            "resolved_rows": int(item["terminal_outcome_rows"]),
            "unresolved_rows": int(item["unresolved_outcome_rows"]),
        }
    pooled = coverage.loc[
        coverage["taxonomy_groups"].eq(5)
        & coverage["conformal_group"].eq("ALL")
        & coverage["period"].str.contains("_to_"),
        ["design_split", "rows", "resolved_rows", "unresolved_rows"],
    ]
    for item in pooled.to_dict(orient="records"):
        by_split[str(item["design_split"])] = {
            "rows": int(item["rows"]),
            "resolved_rows": int(item["resolved_rows"]),
            "unresolved_rows": int(item["unresolved_rows"]),
        }
    terminal_resolved = sum(item["resolved_rows"] for item in by_split.values())
    terminal_unresolved = sum(item["unresolved_rows"] for item in by_split.values())
    status_resolved = int(summary["source_inventory"]["resolved_rows"])
    status_unresolved = int(summary["source_inventory"]["unresolved_rows"])
    reclassified = status_resolved - terminal_resolved
    if terminal_resolved + terminal_unresolved != int(summary["source_inventory"]["retained_rows"]):
        raise RuntimeError("Terminal endpoint inventory does not reconcile to retained rows.")
    if reclassified <= 0 or terminal_unresolved - status_unresolved != reclassified:
        raise RuntimeError("Status and terminal endpoint diagnostics no longer reconcile.")
    return {
        "terminal_endpoint": {
            "resolved_rows": terminal_resolved,
            "unresolved_rows": terminal_unresolved,
            "by_split": by_split,
        },
        "frozen_status_diagnostic": {
            "resolved_rows": status_resolved,
            "unresolved_rows": status_unresolved,
        },
        "literal_default_rows_reclassified_unresolved": reclassified,
    }


def _validate_frames(frames: dict[str, pd.DataFrame], summary: dict[str, Any]) -> None:
    actual_rows = {
        "monthly_evaluation": len(frames["monthly"]),
        "aggregate_evaluation": len(frames["aggregate"]),
        "paired_sharp_contrasts": len(frames["contrasts"]),
        "temporal_candidate_coverage": len(frames["coverage"]),
        "simulation_repetitions": len(frames["simulation"]),
    }
    if actual_rows != EXPECTED_ROWS:
        raise RuntimeError(f"Run cardinalities changed: {actual_rows}")
    if not bool(frames["monthly"]["full_budget"].all()):
        raise RuntimeError("At least one monthly policy failed to invest the full budget.")
    records = frames["records"]
    if set(records["solver_backend_actual"].astype(str)) != {"highspy"}:
        raise RuntimeError("The outcome-free run mixed solver backends.")
    residual = pd.to_numeric(records["c2_match_residual"], errors="coerce").abs().max()
    if float(residual) > 1e-10:
        raise RuntimeError(f"C2 funded-PD match exceeded tolerance: {residual}")
    canonical = _canonical_contrasts(frames["contrasts"])
    c2 = canonical.loc[canonical["comparator_rule"].eq("c2_contemporaneous")]
    recomputed = {
        "payoff_worse": int((c2["realized_payoff_difference_upper"] < 0.0).sum()),
        "default_higher": int((c2["weighted_default_difference_lower"] > 0.0).sum()),
        "miscoverage_higher": int((c2["weighted_miscoverage_difference_lower"] > 0.0).sum()),
        "policies": int(len(c2)),
    }
    if recomputed != summary["canonical_c2_direction_counts"]:
        raise RuntimeError("Canonical C2 direction counts do not reconcile.")
    envelopes = _comparator_envelopes(frames["contrasts"])
    envelope_signs = set(envelopes["sign"])
    if envelope_signs != {"indeterminate"} or len(envelopes) != 27:
        raise RuntimeError("Comparator multiverse unexpectedly admits a universal sign.")
    frozen_envelopes = pd.DataFrame(summary["canonical_comparator_envelopes"])
    reconciled = envelopes.merge(
        frozen_envelopes,
        on=["paired_policy_id", "metric"],
        suffixes=("_derived", "_frozen"),
        validate="one_to_one",
    )
    if len(reconciled) != 27 or not (
        np.allclose(reconciled["lower_derived"], reconciled["lower_frozen"], atol=1e-12)
        and np.allclose(reconciled["upper_derived"], reconciled["upper_frozen"], atol=1e-12)
        and reconciled["sign_derived"].equals(reconciled["sign_frozen"])
    ):
        raise RuntimeError("Derived comparator envelopes do not match the frozen summary.")
    _allocation_distances(frames["allocations"])
    binding = _purpose_cap_binding(frames["allocations"])
    if not binding["all_bind"]:
        raise RuntimeError("At least one sub-100% purpose cap is no longer binding.")
    _endpoint_inventory(frames["coverage"], summary)


def _write_table(frame: pd.DataFrame, stem: str) -> list[Path]:
    TABLE_ROOT.mkdir(parents=True, exist_ok=True)
    csv_path = atomic_write_text(
        TABLE_ROOT / f"{stem}.csv",
        frame.to_csv(index=False, lineterminator="\n"),
    )
    tex_path = atomic_write_text(
        TABLE_ROOT / f"{stem}.tex",
        frame.to_latex(index=False, escape=True, float_format=lambda value: f"{value:.6f}"),
    )
    markdown = frame.to_markdown(index=False, floatfmt=".6f") or ""
    md_path = atomic_write_text(
        TABLE_ROOT / f"{stem}.md",
        markdown + "\n",
    )
    return [csv_path, tex_path, md_path]


def _save_figure(figure: plt.Figure, stem: str) -> list[Path]:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
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
        outputs.append(path)
    plt.close(figure)
    return outputs


def _canonical_contrasts(contrasts: pd.DataFrame) -> pd.DataFrame:
    return contrasts.loc[
        contrasts["seed"].eq(42)
        & np.isclose(contrasts["purpose_cap"], 0.25)
        & np.isclose(contrasts["lgd"], 0.45)
        & contrasts["role"].eq("primary_oot")
    ].copy()


def _policy_grid(records: pd.DataFrame) -> pd.DataFrame:
    return (
        records.loc[records["comparator_rule"].eq("guardrail")][
            ["paired_policy_id", "risk_tolerance", "gamma"]
        ]
        .drop_duplicates()
        .loc[lambda frame: frame["paired_policy_id"].isin(POLICY_ORDER)]
        .sort_values("paired_policy_id", kind="mergesort")
        .reset_index(drop=True)
    )


def _coverage_table(coverage: pd.DataFrame) -> pd.DataFrame:
    pooled = coverage.loc[
        coverage["conformal_group"].eq("ALL") & coverage["period"].str.contains("_to_")
    ].copy()
    columns = [
        "taxonomy_groups",
        "design_split",
        "rows",
        "resolved_rows",
        "unresolved_rows",
        "resolved_empirical_coverage",
        "all_candidate_coverage_lower",
        "all_candidate_coverage_upper",
        "mean_interval_width",
        "upper_endpoint_one_share",
    ]
    return (
        pooled[columns]
        .sort_values(["taxonomy_groups", "design_split"], kind="mergesort")
        .reset_index(drop=True)
    )


def _canonical_comparator_table(contrasts: pd.DataFrame) -> pd.DataFrame:
    canonical = _canonical_contrasts(contrasts)
    table = canonical.loc[canonical["comparator_rule"].isin(COMPARATOR_ORDER)].copy()
    table["comparator"] = table["comparator_rule"].map(COMPARATOR_NAMES)
    table["payoff_direction"] = _direction(
        table["realized_payoff_difference_lower"],
        table["realized_payoff_difference_upper"],
    )
    table["default_direction"] = _direction(
        table["weighted_default_difference_lower"],
        table["weighted_default_difference_upper"],
    )
    table["miscoverage_direction"] = _direction(
        table["weighted_miscoverage_difference_lower"],
        table["weighted_miscoverage_difference_upper"],
    )
    order = {name: index for index, name in enumerate(COMPARATOR_ORDER)}
    table["comparator_order"] = table["comparator_rule"].map(order)
    columns = [
        "paired_policy_id",
        "comparator_rule",
        "comparator",
        "realized_payoff_difference_lower",
        "realized_payoff_difference_upper",
        "weighted_default_difference_lower",
        "weighted_default_difference_upper",
        "weighted_miscoverage_difference_lower",
        "weighted_miscoverage_difference_upper",
        "undiscounted_snapshot_cash_yield_difference",
        "payoff_direction",
        "default_direction",
        "miscoverage_direction",
    ]
    return table.sort_values(["comparator_order", "paired_policy_id"], kind="mergesort")[
        columns
    ].reset_index(drop=True)


def _direction_summary(comparator_table: pd.DataFrame, envelopes: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for rule in COMPARATOR_ORDER:
        group = comparator_table.loc[comparator_table["comparator_rule"].eq(rule)]
        row: dict[str, Any] = {
            "comparator_rule": rule,
            "comparator": COMPARATOR_NAMES[rule],
            "policy_pairs": int(len(group)),
        }
        for metric in ("payoff", "default", "miscoverage"):
            counts = group[f"{metric}_direction"].value_counts()
            for direction in ("negative", "positive", "indeterminate"):
                row[f"{metric}_{direction}"] = int(counts.get(direction, 0))
        rows.append(row)
    envelope_row: dict[str, Any] = {
        "comparator_rule": "finite_multiverse_envelope",
        "comparator": "Envelope over C0, C1, C2, and 29 point caps",
        "policy_pairs": int(envelopes["paired_policy_id"].nunique()),
    }
    for output_name, metric_name in (
        ("payoff", "realized_payoff"),
        ("default", "terminal_default"),
        ("miscoverage", "funded_miscoverage"),
    ):
        counts = envelopes.loc[envelopes["metric"].eq(metric_name), "sign"].value_counts()
        for direction in ("negative", "positive", "indeterminate"):
            envelope_row[f"{output_name}_{direction}"] = int(counts.get(direction, 0))
    rows.append(envelope_row)
    return pd.DataFrame(rows)


def _sensitivity_table(contrasts: pd.DataFrame) -> pd.DataFrame:
    sensitivity = contrasts.loc[
        contrasts["role"].eq("primary_oot")
        & contrasts["comparator_rule"].eq("c2_contemporaneous")
        & np.isclose(contrasts["lgd"], 0.45)
    ].copy()
    sensitivity["payoff_direction"] = _direction(
        sensitivity["realized_payoff_difference_lower"],
        sensitivity["realized_payoff_difference_upper"],
    )
    sensitivity["default_direction"] = _direction(
        sensitivity["weighted_default_difference_lower"],
        sensitivity["weighted_default_difference_upper"],
    )
    sensitivity["miscoverage_direction"] = _direction(
        sensitivity["weighted_miscoverage_difference_lower"],
        sensitivity["weighted_miscoverage_difference_upper"],
    )
    rows: list[dict[str, Any]] = []
    for (policy, seed, cap), group in sensitivity.groupby(
        ["paired_policy_id", "seed", "purpose_cap"], observed=True, sort=True
    ):
        if len(group) != 1:
            raise RuntimeError("C2 sensitivity cell is not unique.")
        item = group.iloc[0]
        rows.append(
            {
                "paired_policy_id": policy,
                "seed": int(seed),
                "purpose_cap": float(cap),
                "payoff_direction": item["payoff_direction"],
                "default_direction": item["default_direction"],
                "miscoverage_direction": item["miscoverage_direction"],
                "payoff_lower": item["realized_payoff_difference_lower"],
                "payoff_upper": item["realized_payoff_difference_upper"],
                "default_lower": item["weighted_default_difference_lower"],
                "default_upper": item["weighted_default_difference_upper"],
                "miscoverage_lower": item["weighted_miscoverage_difference_lower"],
                "miscoverage_upper": item["weighted_miscoverage_difference_upper"],
            }
        )
    result = pd.DataFrame(rows)
    if len(result) != 180:
        raise RuntimeError(f"Expected 180 C2 sensitivity cells, found {len(result)}.")
    return result


def _frontier_table(contrasts: pd.DataFrame) -> pd.DataFrame:
    frontier = _canonical_contrasts(contrasts)
    frontier = frontier.loc[frontier["comparator_rule"].eq("point_cap_frontier")].copy()
    for metric, lower, upper in (
        ("payoff", "realized_payoff_difference_lower", "realized_payoff_difference_upper"),
        ("default", "weighted_default_difference_lower", "weighted_default_difference_upper"),
        (
            "miscoverage",
            "weighted_miscoverage_difference_lower",
            "weighted_miscoverage_difference_upper",
        ),
    ):
        frontier[f"{metric}_direction"] = _direction(frontier[lower], frontier[upper])
    rows: list[dict[str, Any]] = []
    for cap, group in frontier.groupby("frontier_cap", sort=True):
        row: dict[str, Any] = {"point_cap": float(cap), "policy_pairs": int(len(group))}
        for metric in ("payoff", "default", "miscoverage"):
            counts = group[f"{metric}_direction"].value_counts()
            for direction in ("negative", "positive", "indeterminate"):
                row[f"{metric}_{direction}"] = int(counts.get(direction, 0))
        rows.append(row)
    return pd.DataFrame(rows)


def _lgd_table(contrasts: pd.DataFrame) -> pd.DataFrame:
    frame = contrasts.loc[
        contrasts["seed"].eq(42)
        & np.isclose(contrasts["purpose_cap"], 0.25)
        & contrasts["role"].eq("primary_oot")
        & contrasts["comparator_rule"].eq("c2_contemporaneous")
    ].copy()
    columns = [
        "paired_policy_id",
        "lgd",
        "realized_payoff_difference_lower",
        "realized_payoff_difference_upper",
        "weighted_default_difference_lower",
        "weighted_default_difference_upper",
        "weighted_miscoverage_difference_lower",
        "weighted_miscoverage_difference_upper",
    ]
    return frame[columns].sort_values(["lgd", "paired_policy_id"], kind="mergesort")


def _ablation_table(contrasts: pd.DataFrame, allocations: pd.DataFrame) -> pd.DataFrame:
    frame = _canonical_contrasts(contrasts)
    columns = [
        "paired_policy_id",
        "realized_payoff_difference_lower",
        "realized_payoff_difference_upper",
        "weighted_default_difference_lower",
        "weighted_default_difference_upper",
        "weighted_miscoverage_difference_lower",
        "weighted_miscoverage_difference_upper",
        "undiscounted_snapshot_cash_yield_difference",
    ]
    contrasts_table = frame.loc[frame["comparator_rule"].eq("ablation_group_c2"), columns]
    return contrasts_table.merge(
        _allocation_distances(allocations),
        on="paired_policy_id",
        validate="one_to_one",
    ).sort_values(
        "paired_policy_id",
        kind="mergesort",
    )


def _aggregate_levels(aggregate: pd.DataFrame) -> pd.DataFrame:
    frame = aggregate.loc[
        aggregate["seed"].eq(42)
        & np.isclose(aggregate["purpose_cap"], 0.25)
        & np.isclose(aggregate["lgd"], 0.45)
        & aggregate["role"].eq("primary_oot")
        & aggregate["comparator_rule"].isin(["guardrail", "c2_contemporaneous"])
    ].copy()
    columns = [
        "paired_policy_id",
        "comparator_rule",
        "expected_objective",
        "realized_payoff_lower",
        "realized_payoff_upper",
        "weighted_default_lower",
        "weighted_default_upper",
        "weighted_miscoverage_lower",
        "weighted_miscoverage_upper",
        "unresolved_exposure_share",
        "undiscounted_snapshot_cash_yield",
    ]
    return frame[columns].sort_values(["paired_policy_id", "comparator_rule"], kind="mergesort")


def _plot_coverage(table: pd.DataFrame) -> plt.Figure:
    primary = table.loc[table["design_split"].eq("primary_oot")].sort_values("taxonomy_groups")
    x = np.arange(len(primary))
    lower = primary["all_candidate_coverage_lower"].to_numpy(dtype=float)
    upper = primary["all_candidate_coverage_upper"].to_numpy(dtype=float)
    midpoint = (lower + upper) / 2.0
    figure, axis = plt.subplots(figsize=(7.2, 3.8))
    axis.errorbar(
        x,
        midpoint,
        yerr=np.vstack((midpoint - lower, upper - midpoint)),
        fmt="o",
        color="#1f6f8b",
        ecolor="#1f6f8b",
        capsize=5,
        linewidth=2,
        label="Primary OOT sharp coverage interval",
    )
    axis.axhline(0.90, color="#b33a3a", linestyle="--", linewidth=1.5, label="90% target")
    axis.set_xticks(x, primary["taxonomy_groups"].astype(int).astype(str))
    axis.set_xlabel("Fixed score strata")
    axis.set_ylabel("Coverage")
    axis.set_ylim(0.84, 0.91)
    axis.grid(axis="y", alpha=0.25)
    axis.legend(frameon=False, loc="lower right")
    figure.tight_layout()
    return figure


def _plot_comparators(table: pd.DataFrame) -> plt.Figure:
    metrics = (
        (
            "realized_payoff_difference_lower",
            "realized_payoff_difference_upper",
            "Payoff / $15M",
            15e6,
        ),
        (
            "weighted_default_difference_lower",
            "weighted_default_difference_upper",
            "Default difference",
            1.0,
        ),
        (
            "weighted_miscoverage_difference_lower",
            "weighted_miscoverage_difference_upper",
            "Miscoverage difference",
            1.0,
        ),
    )
    colors = {
        "c0_same_numeric_cap": "#cf6a32",
        "c1_development_fixed": "#6c757d",
        "c2_contemporaneous": "#1f6f8b",
    }
    figure, axes = plt.subplots(1, 3, figsize=(12.8, 5.4), sharey=True)
    y = np.arange(len(POLICY_ORDER))
    offsets = {-1: -0.20, 0: 0.0, 1: 0.20}
    for axis, (lower_name, upper_name, title, scale) in zip(axes, metrics, strict=True):
        for comparator_index, rule in enumerate(COMPARATOR_ORDER):
            group = table.loc[table["comparator_rule"].eq(rule)].set_index("paired_policy_id")
            lower = group.loc[POLICY_ORDER, lower_name].to_numpy(dtype=float) / scale
            upper = group.loc[POLICY_ORDER, upper_name].to_numpy(dtype=float) / scale
            midpoint = (lower + upper) / 2.0
            axis.errorbar(
                midpoint,
                y + offsets[comparator_index - 1],
                xerr=np.vstack((midpoint - lower, upper - midpoint)),
                fmt="o",
                markersize=3.5,
                capsize=2,
                linewidth=1.2,
                color=colors[rule],
                label=COMPARATOR_NAMES[rule] if axis is axes[0] else None,
            )
        axis.axvline(0.0, color="black", linewidth=0.9)
        axis.set_title(title)
        axis.grid(axis="x", alpha=0.2)
    axes[0].set_yticks(y, POLICY_ORDER)
    axes[0].invert_yaxis()
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        frameon=False,
        fontsize=8,
        loc="lower center",
        ncol=3,
        bbox_to_anchor=(0.5, 0.01),
    )
    figure.tight_layout(rect=(0.0, 0.08, 1.0, 1.0))
    return figure


def _plot_frontier(table: pd.DataFrame) -> plt.Figure:
    figure, axes = plt.subplots(1, 3, figsize=(11.4, 3.6), sharex=True, sharey=True)
    colors = {"negative": "#b33a3a", "positive": "#1f6f8b", "indeterminate": "#8a8f98"}
    for axis, metric in zip(axes, ("payoff", "default", "miscoverage"), strict=True):
        bottom = np.zeros(len(table), dtype=float)
        for direction in ("negative", "indeterminate", "positive"):
            values = table[f"{metric}_{direction}"].to_numpy(dtype=float)
            axis.bar(
                table["point_cap"],
                values,
                width=0.0021,
                bottom=bottom,
                color=colors[direction],
                label=direction.title() if axis is axes[0] else None,
            )
            bottom += values
        axis.set_title(metric.title())
        axis.axvline(0.0825, color="black", linestyle=":", linewidth=1.0)
        axis.set_xlabel("Point-PD cap")
        axis.grid(axis="y", alpha=0.2)
    axes[0].set_ylabel("Policy pairs (of 9)")
    axes[0].legend(frameon=False, fontsize=8)
    figure.tight_layout()
    return figure


def _plot_simulation(summary: pd.DataFrame) -> plt.Figure:
    frame = summary.loc[summary["metric"].eq("transported_coverage")].sort_values("temporal_shift")
    x = frame["temporal_shift"].to_numpy(dtype=float)
    mean = frame["mean"].to_numpy(dtype=float)
    lower = frame["q05"].to_numpy(dtype=float)
    upper = frame["q95"].to_numpy(dtype=float)
    figure, axis = plt.subplots(figsize=(7.0, 3.8))
    axis.fill_between(x, lower, upper, color="#9ec6d4", alpha=0.45, label="5%-95% Monte Carlo")
    axis.plot(x, mean, marker="o", color="#1f6f8b", linewidth=2, label="Mean transported coverage")
    axis.axhline(0.90, color="#b33a3a", linestyle="--", linewidth=1.5, label="90% target")
    axis.set_xlabel("Synthetic temporal shift")
    axis.set_ylabel("Coverage")
    axis.set_ylim(0.87, 0.92)
    axis.grid(axis="y", alpha=0.25)
    axis.legend(frameon=False)
    figure.tight_layout()
    return figure


def build_evidence() -> Path:
    summary = _json(SUMMARY_PATH)
    receipt = _json(RECEIPT_PATH)
    _verify_run(summary, receipt)
    frames = _read_inputs(summary)
    _validate_frames(frames, summary)

    policy_grid = _policy_grid(frames["records"])
    coverage = _coverage_table(frames["coverage"])
    comparator = _canonical_comparator_table(frames["contrasts"])
    envelopes = _comparator_envelopes(frames["contrasts"])
    directions = _direction_summary(comparator, envelopes)
    sensitivity = _sensitivity_table(frames["contrasts"])
    frontier = _frontier_table(frames["contrasts"])
    lgd = _lgd_table(frames["contrasts"])
    ablation = _ablation_table(frames["contrasts"], frames["allocations"])
    levels = _aggregate_levels(frames["aggregate"])
    simulation = frames["simulation_summary"].copy()
    availability = pd.DataFrame(summary["label_availability"])
    purpose_binding = _purpose_cap_binding(frames["allocations"])
    endpoint_inventory = _endpoint_inventory(frames["coverage"], summary)

    outputs: list[Path] = []
    outputs += _write_table(policy_grid, "crpto_ijds_ft_table1_policy_grid")
    outputs += _write_table(coverage, "crpto_ijds_ft_table2_coverage")
    outputs += _write_table(comparator, "crpto_ijds_ft_table3_comparator_contrasts")
    outputs += _write_table(directions, "crpto_ijds_ft_table4_direction_summary")
    outputs += _write_table(sensitivity, "crpto_ijds_ft_tableS1_seed_cap_sensitivity")
    outputs += _write_table(frontier, "crpto_ijds_ft_tableS2_point_cap_frontier")
    outputs += _write_table(lgd, "crpto_ijds_ft_tableS3_lgd")
    outputs += _write_table(ablation, "crpto_ijds_ft_tableS4_group_ablation")
    outputs += _write_table(levels, "crpto_ijds_ft_tableS5_policy_levels")
    outputs += _write_table(simulation, "crpto_ijds_ft_tableS6_simulation")
    outputs += _write_table(availability, "crpto_ijds_ft_tableS7_label_availability")
    outputs += _save_figure(_plot_coverage(coverage), "crpto_ijds_ft_fig1_coverage")
    outputs += _save_figure(_plot_comparators(comparator), "crpto_ijds_ft_fig2_comparators")
    outputs += _save_figure(_plot_frontier(frontier), "crpto_ijds_ft_fig3_frontier")
    outputs += _save_figure(
        _plot_simulation(frames["simulation_summary"]),
        "crpto_ijds_ft_fig4_simulation",
    )

    canonical_c2 = comparator.loc[comparator["comparator_rule"].eq("c2_contemporaneous")]
    primary_coverage = coverage.loc[
        coverage["taxonomy_groups"].eq(5) & coverage["design_split"].eq("primary_oot")
    ].iloc[0]
    sensitivity_counts = {
        metric: sensitivity[f"{metric}_direction"].value_counts().to_dict()
        for metric in ("payoff", "default", "miscoverage")
    }
    canonical_counts = {
        "payoff_worse": int(canonical_c2["payoff_direction"].eq("negative").sum()),
        "default_higher": int(canonical_c2["default_direction"].eq("positive").sum()),
        "miscoverage_higher": int(canonical_c2["miscoverage_direction"].eq("positive").sum()),
        "policies": int(len(canonical_c2)),
    }
    evidence = {
        "schema_version": "2026-07-11.3",
        "status": "complete_reconciled_paper_evidence",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": PROTOCOL_COMMIT,
        "outcome_free_source": summary["outcome_free_lineage"],
        "claim_boundary": summary["claim_boundary"],
        "headline": {
            "conformal_fit_coverage_seed_42": float(
                next(item for item in summary["prediction"] if item["seed"] == 42)[
                    "conformal_fit_coverage"
                ]
            ),
            "primary_all_candidate_coverage": [
                float(primary_coverage["all_candidate_coverage_lower"]),
                float(primary_coverage["all_candidate_coverage_upper"]),
            ],
            "canonical_c2_direction_counts": canonical_counts,
            "seed_cap_c2_direction_counts": sensitivity_counts,
            "comparator_multiverse_envelopes_indeterminate": int(
                envelopes["sign"].eq("indeterminate").sum()
            ),
            "comparator_multiverse_envelopes_total": int(len(envelopes)),
            "c2_max_funded_pd_match_residual": float(
                pd.to_numeric(frames["records"]["c2_match_residual"], errors="coerce").abs().max()
            ),
            "purpose_caps_below_one_bind_every_guardrail_month": purpose_binding["all_bind"],
        },
        "decision": {
            "universal_guardrail_direction_allowed": False,
            "policy_winner_allowed": False,
            "selected_set_validity_allowed": False,
            "current_superiority_submission_go": False,
            "ijds_audit_narrative_go": True,
            "post_result_audit_framing": True,
            "prespecified_negative_fallback": False,
            "audit_thesis": (
                "Temporal coverage failure is robust, but portfolio conclusions are not "
                "invariant to comparator stringency or binding operational constraints."
            ),
        },
        "canonical_c2": canonical_c2.to_dict(orient="records"),
        "canonical_comparator_envelopes": envelopes.to_dict(orient="records"),
        "direction_summary": directions.to_dict(orient="records"),
        "purpose_cap_binding": purpose_binding,
        "endpoint_inventory": endpoint_inventory,
        "mechanism_allocation_distances": ablation[
            [
                "paired_policy_id",
                "clipped_vs_unclipped_allocation_l1",
                "unclipped_group_vs_pooled_allocation_l1",
                "pooled_affine_vs_point_allocation_l1",
            ]
        ].to_dict(orient="records"),
        "source_artifacts": summary["artifacts"],
        "publication_artifacts": {
            path.resolve().relative_to(ROOT).as_posix(): _descriptor(path) for path in outputs
        },
    }
    return atomic_write_json(MANIFEST_PATH, evidence)


def main() -> None:
    print(build_evidence())


if __name__ == "__main__":
    main()
