"""Reconcile the early and late fixed-taxonomy IJDS audit windows."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

V3_RUN_TAG = "ijds-fixed-taxonomy-c2-temporal-v3-2026-07-12-v1"
V3_PROTOCOL_TAG = "protocol/ijds-fixed-taxonomy-c2-temporal-v3-2026-07-12-v1"
V3_PROTOCOL_COMMIT = "c5ceab737ab3cda8aed7d3c1fd24a506418cfa35"

_POLICY_ORDER = [f"linear-{index:03d}" for index in range(1, 10)]
_COMPARATOR_ORDER = [
    "c0_same_numeric_cap",
    "c1_development_fixed",
    "c2_contemporaneous",
]
_METRIC_COLUMNS = {
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


@dataclass(frozen=True)
class TemporalEvidenceBundle:
    """Publication tables and manifest payload derived from V2 and V3."""

    tables: dict[str, pd.DataFrame]
    payload: dict[str, Any]


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


def _descriptor(root: Path, path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    return {
        "path": resolved.relative_to(root.resolve()).as_posix(),
        "bytes": int(resolved.stat().st_size),
        "sha256": _sha256(resolved),
    }


def _verify_descriptor(root: Path, descriptor: dict[str, Any]) -> Path:
    path = (root / str(descriptor["path"])).resolve()
    path.relative_to(root.resolve())
    actual = _descriptor(root, path)
    if any(actual[field] != descriptor[field] for field in ("path", "bytes", "sha256")):
        raise RuntimeError(f"Artifact descriptor drifted: {path}")
    return path


def _canonical_comparator(contrasts: pd.DataFrame, comparator_rule: str) -> pd.DataFrame:
    result = contrasts.loc[
        contrasts["seed"].eq(42)
        & np.isclose(contrasts["purpose_cap"], 0.25)
        & np.isclose(contrasts["lgd"], 0.45)
        & contrasts["role"].eq("primary_oot")
        & contrasts["comparator_rule"].eq(comparator_rule)
        & contrasts["paired_policy_id"].isin(_POLICY_ORDER)
    ].copy()
    if len(result) != 9:
        raise RuntimeError(
            f"Expected nine canonical {comparator_rule} contrasts, got {len(result)}."
        )
    return result


def _direction(lower: pd.Series, upper: pd.Series) -> pd.Series:
    result = pd.Series("indeterminate", index=lower.index, dtype="string")
    result.loc[upper < 0.0] = "negative"
    result.loc[lower > 0.0] = "positive"
    return result


def _primary_pooled_coverage(coverage: pd.DataFrame) -> pd.DataFrame:
    result = coverage.loc[
        coverage["design_split"].eq("primary_oot")
        & coverage["conformal_group"].eq("ALL")
        & coverage["period"].str.contains("_to_", regex=False)
    ].copy()
    if set(result["taxonomy_groups"].astype(int)) != {1, 2, 5, 10} or len(result) != 4:
        raise RuntimeError("Primary coverage does not contain one pooled row per taxonomy.")
    return result.sort_values("taxonomy_groups", kind="mergesort")


def _seed_42_prediction(summary: dict[str, Any]) -> dict[str, Any]:
    rows = [item for item in summary["prediction"] if int(item["seed"]) == 42]
    if len(rows) != 1:
        raise RuntimeError("Expected one canonical seed-42 prediction record.")
    return rows[0]


def _temporal_window_table(
    reference_summary: dict[str, Any],
    reference_coverage: pd.DataFrame,
    v3_summary: dict[str, Any],
    v3_coverage: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    windows = (
        (
            "early_2012h1",
            "2012-01_to_2012-06",
            str(reference_summary["run_tag"]),
            _seed_42_prediction(reference_summary),
            _primary_pooled_coverage(reference_coverage),
        ),
        (
            "late_2012h2_2013m1",
            "2012-07_to_2013-01",
            V3_RUN_TAG,
            _seed_42_prediction(v3_summary),
            _primary_pooled_coverage(v3_coverage),
        ),
    )
    for window_id, fit_window, run_tag, prediction, coverage in windows:
        for record in coverage.to_dict(orient="records"):
            rows.append(
                {
                    "window_id": window_id,
                    "conformal_fit_window": fit_window,
                    "run_tag": run_tag,
                    "conformal_fit_rows": int(prediction["conformal_fit_rows"]),
                    "conformal_fit_coverage": float(prediction["conformal_fit_coverage"]),
                    "taxonomy_groups": int(record["taxonomy_groups"]),
                    "primary_rows": int(record["rows"]),
                    "primary_resolved_rows": int(record["resolved_rows"]),
                    "primary_unresolved_rows": int(record["unresolved_rows"]),
                    "resolved_empirical_coverage": float(record["resolved_empirical_coverage"]),
                    "all_candidate_coverage_lower": float(record["all_candidate_coverage_lower"]),
                    "all_candidate_coverage_upper": float(record["all_candidate_coverage_upper"]),
                    "mean_interval_width": float(record["mean_interval_width"]),
                    "upper_endpoint_one_share": float(record["upper_endpoint_one_share"]),
                }
            )
    return pd.DataFrame(rows)


def _lag_table(lag_sensitivity: pd.DataFrame) -> pd.DataFrame:
    table = lag_sensitivity.loc[
        lag_sensitivity["design_split"].eq("primary_oot")
        & lag_sensitivity["conformal_group"].eq("ALL")
        & lag_sensitivity["period"].str.contains("_to_", regex=False)
    ].copy()
    if set(table["charged_off_lag_months"].astype(int)) != {0, 3, 6, 12} or len(table) != 4:
        raise RuntimeError("Label-lag evidence does not cover the locked four-point grid.")
    columns = [
        "charged_off_lag_months",
        "conformal_fit_rows",
        "conformal_fit_coverage",
        "resolved_empirical_coverage",
        "all_candidate_coverage_lower",
        "all_candidate_coverage_upper",
        "mean_interval_width",
        "upper_endpoint_one_share",
    ]
    return (
        table[columns]
        .sort_values("charged_off_lag_months", kind="mergesort")
        .reset_index(drop=True)
    )


def _timing_direction_table(
    reference_summary: dict[str, Any],
    reference_contrasts: pd.DataFrame,
    v3_contrasts: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for window_id, run_tag, frame in (
        ("early_2012h1", str(reference_summary["run_tag"]), reference_contrasts),
        ("late_2012h2_2013m1", V3_RUN_TAG, v3_contrasts),
    ):
        for comparator_rule in _COMPARATOR_ORDER:
            canonical = _canonical_comparator(frame, comparator_rule)
            for metric, (lower_column, upper_column) in _METRIC_COLUMNS.items():
                counts = _direction(canonical[lower_column], canonical[upper_column]).value_counts()
                rows.append(
                    {
                        "window_id": window_id,
                        "run_tag": run_tag,
                        "comparator_rule": comparator_rule,
                        "metric": metric,
                        "negative": int(counts.get("negative", 0)),
                        "positive": int(counts.get("positive", 0)),
                        "indeterminate": int(counts.get("indeterminate", 0)),
                        "policy_pairs": int(len(canonical)),
                    }
                )
    return pd.DataFrame(rows)


def _comparator_scope_table(v3_summary: dict[str, Any]) -> pd.DataFrame:
    envelopes = pd.DataFrame(v3_summary["canonical_comparator_envelopes"])
    expected_scopes = {"core_rules", "development_supported", "broad_stress"}
    if set(envelopes["scope"]) != expected_scopes or len(envelopes) != 81:
        raise RuntimeError("V3 comparator envelopes do not cover all locked scopes.")
    rows: list[dict[str, Any]] = []
    for group_key, group in envelopes.groupby(["scope", "metric"], sort=False):
        if not isinstance(group_key, tuple) or len(group_key) != 2:
            raise RuntimeError("Comparator-envelope group key is malformed.")
        scope, metric = group_key
        counts = group["sign"].value_counts()
        rows.append(
            {
                "scope": str(scope),
                "metric": str(metric),
                "policy_pairs": int(group["paired_policy_id"].nunique()),
                "negative": int(counts.get("negative", 0)),
                "positive": int(counts.get("positive", 0)),
                "indeterminate": int(counts.get("indeterminate", 0)),
                "minimum_lower_bound": float(group["lower"].min()),
                "maximum_upper_bound": float(group["upper"].max()),
                "records_per_policy_min": int(group["record_count"].min()),
                "records_per_policy_max": int(group["record_count"].max()),
            }
        )
    table = pd.DataFrame(rows)
    if len(table) != 9 or not table["indeterminate"].eq(9).all():
        raise RuntimeError("At least one V3 comparator-scope sign is no longer indeterminate.")
    return table.sort_values(["scope", "metric"], kind="mergesort").reset_index(drop=True)


def _comparator_scope_envelope_table(v3_summary: dict[str, Any]) -> pd.DataFrame:
    table = pd.DataFrame(v3_summary["canonical_comparator_envelopes"])
    columns = [
        "scope",
        "paired_policy_id",
        "metric",
        "lower",
        "upper",
        "sign",
        "record_count",
    ]
    if len(table) != 81 or set(table["sign"]) != {"indeterminate"}:
        raise RuntimeError("Expected 81 indeterminate policy-level scope envelopes.")
    return (
        table[columns]
        .sort_values(["scope", "paired_policy_id", "metric"], kind="mergesort")
        .reset_index(drop=True)
    )


def _late_c2_contrast_table(contrasts: pd.DataFrame) -> pd.DataFrame:
    table = _canonical_comparator(contrasts, "c2_contemporaneous")
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
    return table[columns].sort_values("paired_policy_id", kind="mergesort").reset_index(drop=True)


def _seed_purpose_direction_counts(contrasts: pd.DataFrame) -> list[dict[str, Any]]:
    table = contrasts.loc[
        contrasts["role"].eq("primary_oot")
        & contrasts["comparator_rule"].eq("c2_contemporaneous")
        & np.isclose(contrasts["lgd"], 0.45)
        & contrasts["paired_policy_id"].isin(_POLICY_ORDER)
    ]
    if len(table) != 180:
        raise RuntimeError(f"Expected 180 late-window seed-purpose contrasts, got {len(table)}.")
    rows: list[dict[str, Any]] = []
    for metric, (lower_column, upper_column) in _METRIC_COLUMNS.items():
        counts = _direction(table[lower_column], table[upper_column]).value_counts()
        rows.append(
            {
                "metric": metric,
                "negative": int(counts.get("negative", 0)),
                "positive": int(counts.get("positive", 0)),
                "indeterminate": int(counts.get("indeterminate", 0)),
                "cells": int(len(table)),
            }
        )
    return rows


def _prediction_diagnostic_table(v3_summary: dict[str, Any]) -> pd.DataFrame:
    prediction = _seed_42_prediction(v3_summary)
    rows: list[dict[str, Any]] = []
    for role, source in (
        ("pd_validation", prediction["validation"]),
        ("platt_calibration", prediction["probability_calibration"]),
    ):
        rows.append(
            {
                "role": role,
                "candidate_rows": int(source["rows"]),
                "resolved_rows": int(source["rows"]),
                "unresolved_rows": 0,
                "default_rate": float(source["default_rate"]),
                "roc_auc": float(source["roc_auc"]),
                "brier": float(source["brier"]),
                "log_loss": float(source["log_loss"]),
                "ece_10": float(source["ece_10"]),
            }
        )
    for source in v3_summary["canonical_temporal_prediction"]:
        rows.append(
            {
                "role": str(source["role"]),
                "candidate_rows": int(source["candidate_rows"]),
                "resolved_rows": int(source["resolved_rows"]),
                "unresolved_rows": int(source["unresolved_rows"]),
                "default_rate": float(source["default_rate"]),
                "roc_auc": float(source["roc_auc"]),
                "brier": float(source["brier"]),
                "log_loss": float(source["log_loss"]),
                "ece_10": float(source["ece_10"]),
            }
        )
    table = pd.DataFrame(rows)
    order = {
        "pd_validation": 0,
        "platt_calibration": 1,
        "policy_development": 2,
        "primary_oot": 3,
        "censored_extension": 4,
    }
    table["order"] = table["role"].map(order)
    if table["order"].isna().any() or len(table) != 5:
        raise RuntimeError("Unexpected temporal prediction diagnostic roles.")
    return table.sort_values("order", kind="mergesort").drop(columns="order").reset_index(drop=True)


def _prediction_equivalence(
    reference_panel: pd.DataFrame,
    v3_panel: pd.DataFrame,
) -> dict[str, Any]:
    splits = {"primary_oot", "censored_extension"}
    columns = ["id", "design_split", "pd_point"]
    left = reference_panel.loc[reference_panel["design_split"].isin(splits), columns]
    right = v3_panel.loc[v3_panel["design_split"].isin(splits), columns]
    merged = left.merge(
        right,
        on=["id", "design_split"],
        how="outer",
        suffixes=("_early", "_late"),
        indicator=True,
        validate="one_to_one",
    )
    if not merged["_merge"].eq("both").all():
        raise RuntimeError("The early and late OOT prediction panels contain different loans.")
    difference = (merged["pd_point_early"] - merged["pd_point_late"]).abs()
    maximum = float(difference.max())
    if maximum != 0.0:
        raise RuntimeError(f"Point predictions drifted between timing windows: {maximum}.")
    return {
        "common_oot_rows": int(len(merged)),
        "maximum_absolute_pd_point_difference": maximum,
        "exact": True,
    }


def _point_allocation_equivalence(
    reference_allocations: pd.DataFrame,
    v3_allocations: pd.DataFrame,
) -> dict[str, Any]:
    keys = ["candidate_id", "role", "period", "frontier_cap_key", "id"]

    def select(frame: pd.DataFrame) -> pd.DataFrame:
        point_rule = frame["comparator_rule"].eq("point_cap_frontier")
        c0_rule = frame["comparator_rule"].eq("c0_same_numeric_cap") & frame[
            "paired_policy_id"
        ].isin(_POLICY_ORDER)
        selected = frame.loc[
            frame["seed"].eq(42)
            & np.isclose(frame["purpose_cap"], 0.25)
            & np.isclose(frame["lgd"], 0.45)
            & frame["role"].eq("primary_oot")
            & (point_rule | c0_rule),
            [
                "candidate_id",
                "role",
                "period",
                "id",
                "comparator_rule",
                "frontier_cap",
                "exposure",
            ],
        ].copy()
        selected["frontier_cap_key"] = selected["frontier_cap"].fillna(-1.0)
        cells = selected[
            ["candidate_id", "role", "period", "comparator_rule", "frontier_cap_key"]
        ].drop_duplicates()
        if len(cells) != 570:
            raise RuntimeError(f"Expected 570 canonical point-policy cells, got {len(cells)}.")
        return selected.groupby(keys, as_index=False, observed=True)["exposure"].sum()

    left = select(reference_allocations)
    right = select(v3_allocations)
    merged = left.merge(
        right,
        on=keys,
        how="outer",
        suffixes=("_early", "_late"),
        validate="one_to_one",
    ).fillna({"exposure_early": 0.0, "exposure_late": 0.0})
    difference = (merged["exposure_early"] - merged["exposure_late"]).abs()
    maximum = float(difference.max())
    total_l1 = float(difference.sum())
    if maximum != 0.0 or total_l1 != 0.0:
        raise RuntimeError(
            "Canonical point-PD allocations drifted between timing windows: "
            f"max={maximum}, L1={total_l1}."
        )
    return {
        "canonical_point_policy_cells": 570,
        "allocation_union_rows": int(len(merged)),
        "maximum_absolute_exposure_difference": maximum,
        "total_allocation_l1_difference": total_l1,
        "exact": True,
    }


def build_temporal_evidence(
    *,
    root: Path,
    reference_summary: dict[str, Any],
    reference_coverage: pd.DataFrame,
    reference_contrasts: pd.DataFrame,
    reference_allocations: pd.DataFrame,
    reference_decision_panel: pd.DataFrame,
) -> TemporalEvidenceBundle:
    """Validate V3 and derive timing-sensitive evidence without promoting it."""
    model_root = root / "models/experiments/ijds_prefreeze" / V3_RUN_TAG
    summary_path = model_root / "fixed_taxonomy_c2_temporal_v3_summary.json"
    receipt_path = model_root / "execution_receipt.json"
    summary = _json(summary_path)
    receipt = _json(receipt_path)

    tagged = subprocess.run(
        ["git", "rev-list", "-n", "1", V3_PROTOCOL_TAG],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if tagged != V3_PROTOCOL_COMMIT:
        raise RuntimeError(f"V3 protocol tag resolves to {tagged}, expected {V3_PROTOCOL_COMMIT}.")
    for field, expected in (
        ("run_tag", V3_RUN_TAG),
        ("protocol_tag", V3_PROTOCOL_TAG),
        ("protocol_commit", V3_PROTOCOL_COMMIT),
    ):
        if summary.get(field) != expected:
            raise RuntimeError(f"V3 summary {field} does not match the locked protocol.")
    if summary.get("status") != "complete_retrospective_prefreeze_audit":
        raise RuntimeError("V3 summary is incomplete.")
    if summary.get("protected_stages_run") or summary.get("protected_artifacts_written"):
        raise RuntimeError("V3 reports a protected-stage mutation.")
    if receipt.get("protocol_commit") != V3_PROTOCOL_COMMIT:
        raise RuntimeError("V3 receipt is bound to the wrong protocol commit.")
    if _verify_descriptor(root, receipt["summary"]) != summary_path.resolve():
        raise RuntimeError("V3 receipt points to the wrong summary.")
    for descriptor in summary["artifacts"].values():
        _verify_descriptor(root, descriptor)

    freeze_path = _verify_descriptor(root, summary["artifacts"]["protocol_freeze"])
    freeze = _json(freeze_path)
    if freeze.get("status") != "outcome_free_allocations_frozen_before_outcome_join":
        raise RuntimeError("V3 outcome-free freeze is incomplete.")
    if freeze.get("outcome_columns_passed_to_policy_or_comparator") != []:
        raise RuntimeError("V3 freeze reports outcome leakage into policy construction.")
    if freeze.get("protocol_commit") != V3_PROTOCOL_COMMIT:
        raise RuntimeError("V3 freeze is bound to the wrong protocol commit.")

    artifacts = summary["artifacts"]
    coverage = pd.read_parquet(_verify_descriptor(root, artifacts["temporal_candidate_coverage"]))
    contrasts = pd.read_parquet(_verify_descriptor(root, artifacts["paired_sharp_contrasts"]))
    lag = pd.read_parquet(_verify_descriptor(root, artifacts["label_lag_coverage_sensitivity"]))
    outcome_free = freeze["outcome_free_artifacts"]
    allocations_path = _verify_descriptor(root, outcome_free["allocations"])
    panel_path = _verify_descriptor(root, outcome_free["canonical_decision_panel"])
    allocations = pd.read_parquet(allocations_path)
    panel = pd.read_parquet(panel_path)

    tables = {
        "crpto_ijds_ft_tableS8_temporal_windows": _temporal_window_table(
            reference_summary,
            reference_coverage,
            summary,
            coverage,
        ),
        "crpto_ijds_ft_tableS9_label_lags": _lag_table(lag),
        "crpto_ijds_ft_tableS10_timing_directions": _timing_direction_table(
            reference_summary,
            reference_contrasts,
            contrasts,
        ),
        "crpto_ijds_ft_tableS11_comparator_scopes": _comparator_scope_table(summary),
        "crpto_ijds_ft_tableS12_prediction_diagnostics": _prediction_diagnostic_table(summary),
        "crpto_ijds_ft_tableS13_late_c2_contrasts": _late_c2_contrast_table(contrasts),
        "crpto_ijds_ft_tableS14_comparator_scope_envelopes": (
            _comparator_scope_envelope_table(summary)
        ),
    }
    equivalence = {
        "point_predictions": _prediction_equivalence(reference_decision_panel, panel),
        "point_policy_allocations": _point_allocation_equivalence(
            reference_allocations,
            allocations,
        ),
    }
    payload = {
        "status": "complete_locked_design_sensitivity",
        "run_tag": V3_RUN_TAG,
        "protocol_tag": V3_PROTOCOL_TAG,
        "protocol_commit": V3_PROTOCOL_COMMIT,
        "claim_boundary": summary["claim_boundary"],
        "no_result_based_promotion": True,
        "development_supported_point_cap_range": summary["development_supported_point_cap_range"],
        "late_seed_purpose_c2_direction_counts": _seed_purpose_direction_counts(contrasts),
        "code_path_equivalence": equivalence,
        "tables": {name: table.to_dict(orient="records") for name, table in tables.items()},
        "source_artifacts": {
            "summary": _descriptor(root, summary_path),
            "receipt": _descriptor(root, receipt_path),
            "protocol_freeze": _descriptor(root, freeze_path),
            "temporal_candidate_coverage": artifacts["temporal_candidate_coverage"],
            "paired_sharp_contrasts": artifacts["paired_sharp_contrasts"],
            "label_lag_coverage_sensitivity": artifacts["label_lag_coverage_sensitivity"],
            "outcome_free_allocations": outcome_free["allocations"],
            "canonical_decision_panel": outcome_free["canonical_decision_panel"],
        },
    }
    return TemporalEvidenceBundle(tables=tables, payload=payload)
