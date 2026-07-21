"""Loan-age-equalized coverage audit for the frozen 2016 and 2017 origins."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.data.outcome_observability import build_outcome_label_availability
from src.ijds_audit.rolling_origin_equal_followup import (
    ALLOWED_DATA_ROOT,
    ALLOWED_MODEL_ROOT,
    CANONICAL_GROUPS,
    CHARGED_OFF_LAG_MONTHS,
    COMPLETE_ENDPOINT_REASONS,
    EXPECTED_COVERAGE_CELLS,
    EXPECTED_WINDOWS_PER_ORIGIN,
    LEARNER,
    NOMINAL_COVERAGE,
    RESOLVED_REASONS,
    SCORE_COLUMN,
    OriginSpec,
    VerifiedOriginSource,
    evaluate_origin_coverage,
    load_equal_followup_config,
    load_raw_candidate_rows,
    origin_specs,
    select_origin_scores,
    verify_origin_freeze,
)
from src.utils.isolated_experiment import (
    environment_provenance,
    implementation_provenance,
    prepare_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_repo_input,
)
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_parquet

RUN_TAG = "ijds-rolling-origin-individual-age-followup-2026-07-21-v1"
PROTOCOL_TAG = "protocol/ijds-rolling-origin-individual-age-followup-2026-07-21-v1"
SCHEMA_VERSION = "2026-07-21.1"
PROTOCOL_STATUS = "locked_preexecution_retrospective_individual_age_followup_sensitivity"

INDIVIDUAL_FOLLOWUP_MONTHS = 39
MAXIMUM_SUPPORTED_CUTOFF = "2020-09-30"
ENDPOINT_RULE = "issue_month_end_plus_39_calendar_months"
EXPECTED_ISSUE_MONTH_CELLS = 6

PARENT_CONFIG_PATH = Path(
    "configs/experiments/ijds_rolling_origin_equal_followup_2026-07-21_v1.yaml"
)
PARENT_CONFIG_BYTES = 5_502
PARENT_CONFIG_SHA256 = "5a3d8369a371b346b2268377a195028e84ed8efca74a9e55e468b4df0ed0828a"

EXPECTED_CUTOFFS_BY_PERIOD = {
    "2016-04": "2019-07-31",
    "2016-05": "2019-08-31",
    "2016-06": "2019-09-30",
    "2017-04": "2020-07-31",
    "2017-05": "2020-08-31",
    "2017-06": "2020-09-30",
}

_EXPECTED_EVALUATION: dict[str, Any] = {
    "origin_ids": ["primary_2016", "rolling_2017"],
    "origin_years": [2016, 2017],
    "common_issue_month_numbers": [4, 5, 6],
    "common_primary_months": 3,
    "individual_followup_months_after_issue_month_end": INDIVIDUAL_FOLLOWUP_MONTHS,
    "issue_date_resolution": "calendar_month",
    "expected_cutoffs_by_issue_period": EXPECTED_CUTOFFS_BY_PERIOD,
    "maximum_supported_cutoff": MAXIMUM_SUPPORTED_CUTOFF,
    "charged_off_reporting_lag_months": CHARGED_OFF_LAG_MONTHS,
    "alpha": 0.10,
    "nominal_coverage": NOMINAL_COVERAGE,
    "learner": LEARNER,
    "score_column": SCORE_COLUMN,
    "taxonomy_groups": CANONICAL_GROUPS,
    "aggregate_stratum": -1,
    "expected_windows_per_origin": EXPECTED_WINDOWS_PER_ORIGIN,
    "expected_coverage_cells": EXPECTED_COVERAGE_CELLS,
    "expected_issue_month_cells": EXPECTED_ISSUE_MONTH_CELLS,
    "complete_endpoint_reason_rows_per_origin": len(COMPLETE_ENDPOINT_REASONS),
    "complete_descriptive_family": True,
    "error_controlled": False,
    "hypothesis_tests": False,
    "multiplicity_adjustment": False,
    "no_model_selection": True,
    "no_origin_selection": True,
    "no_month_selection": True,
    "no_window_selection": True,
    "no_pooling": True,
    "no_portfolio_evaluation": True,
}


@dataclass(frozen=True)
class IndividualAgeFollowupComputation:
    """Validated in-memory individual-age sensitivity before fresh writes."""

    config: dict[str, Any]
    parent_config: dict[str, Any]
    parent_config_descriptor: dict[str, Any]
    origins: tuple[OriginSpec, ...]
    sources: dict[str, VerifiedOriginSource]
    raw_descriptor: dict[str, Any]
    coverage: pd.DataFrame
    origin_census: pd.DataFrame
    monthly_census: pd.DataFrame
    reason_census: pd.DataFrame
    monthly_reason_census: pd.DataFrame


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], *, context: str) -> None:
    observed = {str(key) for key in value}
    missing = sorted(expected.difference(observed))
    extra = sorted(observed.difference(expected))
    if missing or extra:
        raise KeyError(f"{context} keys changed: missing={missing}, extra={extra}.")


def _validate_descriptor(value: Mapping[str, Any], *, context: str) -> None:
    _require_exact_keys(value, {"path", "bytes", "sha256"}, context=context)
    if not str(value["path"]).strip():
        raise ValueError(f"{context} path is empty.")
    if int(value["bytes"]) <= 0:
        raise ValueError(f"{context} byte count must be positive.")
    digest = str(value["sha256"])
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError(f"{context} SHA-256 is invalid.")


def _descriptor_matches(
    observed: Mapping[str, Any], expected: Mapping[str, Any], *, context: str
) -> None:
    for field in ("path", "bytes", "sha256"):
        if observed.get(field) != expected.get(field):
            raise RuntimeError(f"{context} descriptor mismatch for {field}.")


def load_individual_age_followup_config(
    path: Path, *, repo_root: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Load the sensitivity config and its hash-locked equal-follow-up parent."""
    root = repo_root.resolve()
    resolved = resolve_repo_input(path, repo_root=root)
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Individual-age follow-up config must be a YAML mapping.")
    _require_exact_keys(
        payload,
        {
            "schema_version",
            "protocol_status",
            "protocol_tag",
            "run_tag",
            "protocol_document",
            "protocol_lineage_files",
            "parent_equal_followup_config",
            "evaluation",
            "output",
        },
        context="individual-age follow-up config",
    )
    identities = {
        "schema_version": SCHEMA_VERSION,
        "protocol_status": PROTOCOL_STATUS,
        "protocol_tag": PROTOCOL_TAG,
        "run_tag": RUN_TAG,
    }
    for field, expected in identities.items():
        if str(payload[field]) != expected:
            raise RuntimeError(f"Individual-age follow-up {field} changed.")

    evaluation = payload["evaluation"]
    if not isinstance(evaluation, Mapping) or dict(evaluation) != _EXPECTED_EVALUATION:
        raise RuntimeError("The complete individual-age evaluation contract changed.")

    protocol_document = resolve_repo_input(str(payload["protocol_document"]), repo_root=root)
    if protocol_document.name != (
        "ijds_rolling_origin_individual_age_followup_protocol_2026-07-21.md"
    ):
        raise RuntimeError("The individual-age protocol document changed.")
    lineage = payload["protocol_lineage_files"]
    if not isinstance(lineage, list) or not lineage:
        raise TypeError("protocol_lineage_files must be a nonempty list.")
    for lineage_path in lineage:
        resolve_repo_input(str(lineage_path), repo_root=root)

    parent = payload["parent_equal_followup_config"]
    if not isinstance(parent, Mapping):
        raise TypeError("parent_equal_followup_config must be a mapping.")
    _validate_descriptor(parent, context="parent equal-follow-up config")
    expected_parent = {
        "path": PARENT_CONFIG_PATH.as_posix(),
        "bytes": PARENT_CONFIG_BYTES,
        "sha256": PARENT_CONFIG_SHA256,
    }
    if dict(parent) != expected_parent:
        raise RuntimeError("The hash-locked equal-follow-up parent config changed.")
    parent_path = resolve_repo_input(str(parent["path"]), repo_root=root)
    parent_descriptor = relative_artifact_descriptor(parent_path, repo_root=root)
    _descriptor_matches(parent_descriptor, parent, context="parent equal-follow-up config")
    parent_config = load_equal_followup_config(parent_path, repo_root=root)

    output = payload["output"]
    if not isinstance(output, Mapping):
        raise TypeError("output must be a mapping.")
    _require_exact_keys(
        output,
        {
            "data_root",
            "model_root",
            "deterministic_summary",
            "execution_receipt",
            "immutability",
        },
        context="individual-age output",
    )
    if output != {
        "data_root": ALLOWED_DATA_ROOT.as_posix(),
        "model_root": ALLOWED_MODEL_ROOT.as_posix(),
        "deterministic_summary": "rolling_origin_individual_age_followup_summary.json",
        "execution_receipt": "execution_receipt.json",
        "immutability": "hard_no_overwrite_choose_fresh_run_tag",
    }:
        raise RuntimeError("The isolated individual-age output contract changed.")
    return payload, parent_config, parent_descriptor


def loan_specific_cutoff_frame(
    issue_dates: pd.Series,
    *,
    followup_months: int = INDIVIDUAL_FOLLOWUP_MONTHS,
) -> pd.DataFrame:
    """Map issue months to month-end cutoffs exactly 39 month indices later."""
    if int(followup_months) != INDIVIDUAL_FOLLOWUP_MONTHS:
        raise RuntimeError(
            "Individual follow-up horizon changed: "
            f"{followup_months} != {INDIVIDUAL_FOLLOWUP_MONTHS}."
        )
    parsed = pd.to_datetime(issue_dates, errors="coerce")
    if bool(parsed.isna().any()):
        raise ValueError("Individual-age endpoint received an invalid issue date.")
    issue_period = parsed.dt.to_period("M")
    cutoff_period = issue_period + INDIVIDUAL_FOLLOWUP_MONTHS
    month_difference = cutoff_period.astype("int64") - issue_period.astype("int64")
    if not month_difference.eq(INDIVIDUAL_FOLLOWUP_MONTHS).all():
        raise RuntimeError("A loan-specific cutoff does not have the locked month-index age.")
    issue_month_end = issue_period.dt.to_timestamp(how="end").dt.normalize()
    cutoff = cutoff_period.dt.to_timestamp(how="end").dt.normalize()
    if not issue_month_end.dt.is_month_end.all() or not cutoff.dt.is_month_end.all():
        raise RuntimeError("Individual-age endpoints must be calendar month ends.")
    if bool(cutoff.gt(pd.Timestamp(MAXIMUM_SUPPORTED_CUTOFF)).any()):
        raise RuntimeError("A loan-specific cutoff exceeds the declared endpoint support.")
    return pd.DataFrame(
        {
            "period": issue_period.astype("string"),
            "issue_month_end": issue_month_end,
            "individual_evaluation_cutoff": cutoff,
            "individual_followup_months": INDIVIDUAL_FOLLOWUP_MONTHS,
        },
        index=issue_dates.index,
    )


def _validate_locked_cutoff_map(cutoffs: pd.DataFrame, spec: OriginSpec) -> None:
    observed = (
        cutoffs.loc[:, ["period", "individual_evaluation_cutoff"]]
        .drop_duplicates()
        .sort_values("period", kind="mergesort")
    )
    observed_map = {
        str(row.period): str(pd.Timestamp(row.individual_evaluation_cutoff).date())
        for row in observed.itertuples(index=False)
    }
    expected = {period: EXPECTED_CUTOFFS_BY_PERIOD[period] for period in spec.issue_periods}
    if observed_map != expected:
        raise RuntimeError(
            f"{spec.origin_id} loan-specific cutoff map changed: {observed_map} != {expected}."
        )


def reconstruct_individual_age_outcomes(
    raw_candidates: pd.DataFrame,
    spec: OriginSpec,
    *,
    charged_off_lag_months: int = CHARGED_OFF_LAG_MONTHS,
) -> pd.DataFrame:
    """Reconstruct one origin using each loan's issue-month-relative cutoff."""
    if int(charged_off_lag_months) != CHARGED_OFF_LAG_MONTHS:
        raise RuntimeError("The frozen six-month charged-off lag changed.")
    selected = raw_candidates.loc[raw_candidates["origin_id"].astype(str).eq(spec.origin_id)].copy()
    selected = selected.sort_values(["issue_d", "id"], kind="mergesort").reset_index(drop=True)
    if len(selected) != spec.expected_candidate_rows:
        raise RuntimeError(f"{spec.origin_id} raw endpoint census changed.")
    if tuple(sorted(selected["period"].astype(str).unique())) != spec.issue_periods:
        raise RuntimeError(f"{spec.origin_id} raw endpoint periods changed.")

    cutoffs = loan_specific_cutoff_frame(selected["issue_d"])
    _validate_locked_cutoff_map(cutoffs, spec)
    labels = build_outcome_label_availability(
        selected["loan_status"],
        selected["last_pymnt_d"],
        cutoff=MAXIMUM_SUPPORTED_CUTOFF,
        charged_off_lag_months=CHARGED_OFF_LAG_MONTHS,
    )
    terminal = labels["terminal_outcome"].astype("Int8")
    available_at = pd.to_datetime(labels["label_available_at"], errors="coerce")
    individual_cutoff = pd.to_datetime(cutoffs["individual_evaluation_cutoff"], errors="raise")
    observed = terminal.notna() & available_at.notna() & available_at.le(individual_cutoff)
    snapshot = terminal.where(observed).astype("Int8")

    resolution = pd.Series("nonterminal_or_unresolved_status", index=selected.index, dtype="string")
    resolution.loc[snapshot.eq(0).fillna(False)] = "fully_paid_by_reconstructed_cutoff"
    resolution.loc[snapshot.eq(1).fillna(False)] = "charged_off_by_reconstructed_cutoff"
    resolution.loc[terminal.notna() & available_at.isna()] = "terminal_availability_date_missing"
    resolution.loc[terminal.notna() & available_at.notna() & available_at.gt(individual_cutoff)] = (
        "terminal_after_reconstructed_cutoff"
    )

    outcomes = pd.DataFrame(
        {
            "id": selected["id"].astype("string"),
            "snapshot_default": snapshot,
            "snapshot_resolution": resolution,
            "outcome_available_at": available_at,
            "role": pd.Series("primary_oot", index=selected.index, dtype="string"),
            "period": cutoffs["period"].astype("string"),
            "issue_month_end": cutoffs["issue_month_end"],
            "individual_evaluation_cutoff": individual_cutoff,
            "individual_followup_months": INDIVIDUAL_FOLLOWUP_MONTHS,
            "origin_id": spec.origin_id,
            "origin_year": spec.year,
            "endpoint_rule": ENDPOINT_RULE,
        }
    )
    observed_reasons = set(outcomes["snapshot_resolution"].astype(str))
    unexpected = sorted(observed_reasons.difference(COMPLETE_ENDPOINT_REASONS))
    if unexpected:
        raise RuntimeError(f"{spec.origin_id} produced unexpected endpoint reasons: {unexpected}.")
    if bool(outcomes["id"].isna().any()) or bool(outcomes["id"].duplicated().any()):
        raise RuntimeError(f"{spec.origin_id} reconstructed outcome IDs are invalid.")
    return outcomes.sort_values(["period", "id"], kind="mergesort").reset_index(drop=True)


def _complete_reason_rows(
    grouped: pd.DataFrame, *, index: pd.Index | pd.MultiIndex
) -> pd.DataFrame:
    completed = grouped.set_index(list(index.names)).reindex(index, fill_value=0).reset_index()
    for column in ("candidate_rows", "resolved_rows", "unresolved_rows"):
        completed[column] = completed[column].astype("int64")
    return completed


def build_individual_age_census_tables(
    outcomes: pd.DataFrame, spec: OriginSpec
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build complete origin/month/reason censuses under loan-specific cutoffs."""
    if len(outcomes) != spec.expected_candidate_rows:
        raise RuntimeError(f"{spec.origin_id} endpoint census changed before reporting.")
    resolved = outcomes["snapshot_default"].notna()
    cutoff_min = pd.Timestamp(outcomes["individual_evaluation_cutoff"].min())
    cutoff_max = pd.Timestamp(outcomes["individual_evaluation_cutoff"].max())
    origin_census = pd.DataFrame(
        [
            {
                "origin_id": spec.origin_id,
                "origin_year": spec.year,
                "issue_period_start": spec.issue_periods[0],
                "issue_period_end": spec.issue_periods[-1],
                "evaluation_cutoff_min": str(cutoff_min.date()),
                "evaluation_cutoff_max": str(cutoff_max.date()),
                "individual_followup_months": INDIVIDUAL_FOLLOWUP_MONTHS,
                "candidate_rows": int(len(outcomes)),
                "resolved_rows": int(resolved.sum()),
                "unresolved_rows": int((~resolved).sum()),
            }
        ]
    )

    monthly = (
        outcomes.assign(__resolved=resolved)
        .groupby("period", observed=True, sort=True)
        .agg(
            issue_month_end=("issue_month_end", "first"),
            individual_evaluation_cutoff=("individual_evaluation_cutoff", "first"),
            candidate_rows=("id", "size"),
            resolved_rows=("__resolved", "sum"),
        )
    )
    monthly = monthly.reindex(pd.Index(spec.issue_periods, name="period")).reset_index()
    if bool(monthly["candidate_rows"].isna().any()):
        raise RuntimeError(f"{spec.origin_id} has an empty declared issue month.")
    monthly["candidate_rows"] = monthly["candidate_rows"].astype("int64")
    monthly["resolved_rows"] = monthly["resolved_rows"].astype("int64")
    monthly["unresolved_rows"] = monthly["candidate_rows"] - monthly["resolved_rows"]
    monthly.insert(0, "origin_year", spec.year)
    monthly.insert(0, "origin_id", spec.origin_id)
    monthly["individual_followup_months"] = INDIVIDUAL_FOLLOWUP_MONTHS

    observed_reason = (
        outcomes.assign(__resolved=resolved)
        .groupby("snapshot_resolution", observed=True, sort=True)
        .agg(candidate_rows=("id", "size"), resolved_rows=("__resolved", "sum"))
        .reset_index()
    )
    observed_reason["unresolved_rows"] = (
        observed_reason["candidate_rows"] - observed_reason["resolved_rows"]
    )
    reason_index = pd.Index(COMPLETE_ENDPOINT_REASONS, name="snapshot_resolution")
    reason = _complete_reason_rows(observed_reason, index=reason_index)
    reason.insert(0, "origin_year", spec.year)
    reason.insert(0, "origin_id", spec.origin_id)
    reason["evaluation_cutoff_min"] = str(cutoff_min.date())
    reason["evaluation_cutoff_max"] = str(cutoff_max.date())
    reason["individual_followup_months"] = INDIVIDUAL_FOLLOWUP_MONTHS

    monthly_observed = (
        outcomes.assign(__resolved=resolved)
        .groupby(["period", "snapshot_resolution"], observed=True, sort=True)
        .agg(candidate_rows=("id", "size"), resolved_rows=("__resolved", "sum"))
        .reset_index()
    )
    monthly_observed["unresolved_rows"] = (
        monthly_observed["candidate_rows"] - monthly_observed["resolved_rows"]
    )
    monthly_reason_index = pd.MultiIndex.from_product(
        [spec.issue_periods, COMPLETE_ENDPOINT_REASONS],
        names=["period", "snapshot_resolution"],
    )
    monthly_reason = _complete_reason_rows(monthly_observed, index=monthly_reason_index)
    cutoff_lookup = monthly.set_index("period")[["issue_month_end", "individual_evaluation_cutoff"]]
    monthly_reason = monthly_reason.join(cutoff_lookup, on="period")
    monthly_reason.insert(0, "origin_year", spec.year)
    monthly_reason.insert(0, "origin_id", spec.origin_id)
    monthly_reason["individual_followup_months"] = INDIVIDUAL_FOLLOWUP_MONTHS

    if int(reason["candidate_rows"].sum()) != len(outcomes):
        raise RuntimeError(f"{spec.origin_id} endpoint reasons do not partition candidates.")
    if int(monthly["candidate_rows"].sum()) != len(outcomes):
        raise RuntimeError(f"{spec.origin_id} monthly census does not partition candidates.")
    if int(monthly_reason["candidate_rows"].sum()) != len(outcomes):
        raise RuntimeError(f"{spec.origin_id} monthly reasons do not partition candidates.")
    for row in reason.itertuples(index=False):
        should_resolve = str(row.snapshot_resolution) in RESOLVED_REASONS
        expected_resolved = int(row.candidate_rows) if should_resolve else 0
        if int(row.resolved_rows) != expected_resolved:
            raise RuntimeError(
                f"{spec.origin_id}/{row.snapshot_resolution} has inconsistent resolution."
            )
        if int(row.unresolved_rows) != int(row.candidate_rows) - expected_resolved:
            raise RuntimeError(
                f"{spec.origin_id}/{row.snapshot_resolution} has inconsistent nonresolution."
            )
    aggregate_from_months = (
        monthly_reason.groupby("snapshot_resolution", observed=True, sort=False)[
            ["candidate_rows", "resolved_rows", "unresolved_rows"]
        ]
        .sum()
        .reindex(COMPLETE_ENDPOINT_REASONS)
        .reset_index()
    )
    columns = ["snapshot_resolution", "candidate_rows", "resolved_rows", "unresolved_rows"]
    if (
        not reason.loc[:, columns]
        .reset_index(drop=True)
        .equals(aggregate_from_months.loc[:, columns].reset_index(drop=True))
    ):
        raise RuntimeError(f"{spec.origin_id} monthly and aggregate reasons disagree.")
    _validate_locked_cutoff_map(monthly, spec)
    return origin_census, monthly, reason, monthly_reason


def evaluate_individual_age_coverage(
    scores: pd.DataFrame,
    outcomes: pd.DataFrame,
    source: VerifiedOriginSource,
) -> pd.DataFrame:
    """Reuse the frozen eight-window evaluator and replace quarter-cutoff metadata."""
    coverage = evaluate_origin_coverage(scores, outcomes, source).drop(
        columns=["issue_quarter_end", "evaluation_cutoff", "common_followup_months"],
        errors="raise",
    )
    cutoffs = pd.to_datetime(outcomes["individual_evaluation_cutoff"], errors="raise")
    coverage["endpoint_rule"] = ENDPOINT_RULE
    coverage["issue_date_resolution"] = "calendar_month"
    coverage["evaluation_cutoff_min"] = str(pd.Timestamp(cutoffs.min()).date())
    coverage["evaluation_cutoff_max"] = str(pd.Timestamp(cutoffs.max()).date())
    coverage["individual_followup_months"] = INDIVIDUAL_FOLLOWUP_MONTHS
    return coverage


def compute_individual_age_followup(
    *, config_path: Path, repo_root: Path
) -> IndividualAgeFollowupComputation:
    """Compute the complete two-origin sensitivity in memory without writes."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config, parent_config, parent_descriptor = load_individual_age_followup_config(
        resolved_config, repo_root=root
    )
    specs = origin_specs(parent_config)
    sources = {spec.origin_id: verify_origin_freeze(spec, repo_root=root) for spec in specs}

    score_frames: dict[str, pd.DataFrame] = {}
    for spec in specs:
        source = sources[spec.origin_id]
        frozen_scores = pd.read_parquet(source.artifact_paths["scores"])
        score_frames[spec.origin_id] = select_origin_scores(frozen_scores, spec)
    combined_scores = pd.concat(score_frames.values(), ignore_index=True)
    if bool(combined_scores["id"].duplicated().any()):
        raise RuntimeError("The frozen 2016 and 2017 candidate identities overlap.")

    raw_path = resolve_repo_input(str(parent_config["raw_source"]["path"]), repo_root=root)
    raw_descriptor = relative_artifact_descriptor(raw_path, repo_root=root)
    _descriptor_matches(raw_descriptor, parent_config["raw_source"], context="raw archive")
    raw_candidates = load_raw_candidate_rows(
        raw_path,
        combined_scores,
        csv_chunksize=int(parent_config["raw_source"]["csv_chunksize"]),
    )

    coverage_frames: list[pd.DataFrame] = []
    origin_censuses: list[pd.DataFrame] = []
    monthly_censuses: list[pd.DataFrame] = []
    reason_censuses: list[pd.DataFrame] = []
    monthly_reason_censuses: list[pd.DataFrame] = []
    for spec in specs:
        outcomes = reconstruct_individual_age_outcomes(raw_candidates, spec)
        origin, monthly, reasons, monthly_reasons = build_individual_age_census_tables(
            outcomes, spec
        )
        coverage = evaluate_individual_age_coverage(
            score_frames[spec.origin_id], outcomes, sources[spec.origin_id]
        )
        if not coverage["resolved_rows"].eq(int(origin.iloc[0]["resolved_rows"])).all():
            raise RuntimeError(f"{spec.origin_id} coverage resolved census disagrees.")
        if not coverage["unresolved_rows"].eq(int(origin.iloc[0]["unresolved_rows"])).all():
            raise RuntimeError(f"{spec.origin_id} coverage unresolved census disagrees.")
        coverage_frames.append(coverage)
        origin_censuses.append(origin)
        monthly_censuses.append(monthly)
        reason_censuses.append(reasons)
        monthly_reason_censuses.append(monthly_reasons)

    coverage = pd.concat(coverage_frames, ignore_index=True).sort_values(
        ["origin_year", "window_ordinal"], kind="mergesort"
    )
    origin_census = pd.concat(origin_censuses, ignore_index=True).sort_values(
        "origin_year", kind="mergesort"
    )
    monthly_census = pd.concat(monthly_censuses, ignore_index=True).sort_values(
        ["origin_year", "period"], kind="mergesort"
    )
    reason_order = {reason: index for index, reason in enumerate(COMPLETE_ENDPOINT_REASONS)}
    reason_census = pd.concat(reason_censuses, ignore_index=True)
    reason_census["__reason_order"] = reason_census["snapshot_resolution"].map(reason_order)
    reason_census = reason_census.sort_values(
        ["origin_year", "__reason_order"], kind="mergesort"
    ).drop(columns="__reason_order")
    monthly_reason_census = pd.concat(monthly_reason_censuses, ignore_index=True)
    monthly_reason_census["__reason_order"] = monthly_reason_census["snapshot_resolution"].map(
        reason_order
    )
    monthly_reason_census = monthly_reason_census.sort_values(
        ["origin_year", "period", "__reason_order"], kind="mergesort"
    ).drop(columns="__reason_order")

    if len(coverage) != EXPECTED_COVERAGE_CELLS:
        raise RuntimeError("The individual-age coverage grid is not the complete 16-cell family.")
    if len(origin_census) != 2 or len(monthly_census) != EXPECTED_ISSUE_MONTH_CELLS:
        raise RuntimeError("The individual-age origin/month census grid is incomplete.")
    if len(reason_census) != 10 or len(monthly_reason_census) != 30:
        raise RuntimeError("The complete individual-age reason grid is incomplete.")

    return IndividualAgeFollowupComputation(
        config=config,
        parent_config=parent_config,
        parent_config_descriptor=parent_descriptor,
        origins=specs,
        sources=sources,
        raw_descriptor=raw_descriptor,
        coverage=coverage.reset_index(drop=True),
        origin_census=origin_census.reset_index(drop=True),
        monthly_census=monthly_census.reset_index(drop=True),
        reason_census=reason_census.reset_index(drop=True),
        monthly_reason_census=monthly_reason_census.reset_index(drop=True),
    )


def _implementation(
    config_path: Path,
    config: Mapping[str, Any],
    parent_config: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    paths = [
        Path("scripts/experiments/run_ijds_rolling_origin_individual_age_followup.py"),
        Path("src/ijds_audit/rolling_origin_individual_age_followup.py"),
        Path("src/ijds_audit/rolling_origin_equal_followup.py"),
        Path("src/ijds_audit/evaluation.py"),
        Path("src/ijds_audit/protocol.py"),
        Path("src/data/outcome_observability.py"),
        PARENT_CONFIG_PATH,
        *[Path(value) for value in config["protocol_lineage_files"]],
        *[Path(str(origin["base_config"])) for origin in parent_config["origins"]],
    ]
    return implementation_provenance(
        config_path=config_path,
        repo_root=repo_root,
        relative_paths=paths,
    )


def _origin_coverage_summary(coverage: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (origin_id, origin_year), frame in coverage.groupby(
        ["origin_id", "origin_year"], observed=True, sort=True
    ):
        rows.append(
            {
                "origin_id": str(origin_id),
                "origin_year": int(origin_year),
                "coverage_cells": int(len(frame)),
                "upper_below_nominal_cells": int(
                    frame["coverage_upper"].lt(NOMINAL_COVERAGE).sum()
                ),
                "all_upper_below_nominal": bool(frame["coverage_upper"].lt(NOMINAL_COVERAGE).all()),
                "coverage_lower_min": float(frame["coverage_lower"].min()),
                "coverage_upper_max": float(frame["coverage_upper"].max()),
            }
        )
    return rows


def run_individual_age_followup(*, config_path: Path, repo_root: Path) -> Path:
    """Require the future clean protocol tag and write one fresh sensitivity."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    load_individual_age_followup_config(resolved_config, repo_root=root)
    protocol_commit = require_clean_tagged_head(root, PROTOCOL_TAG)
    result = compute_individual_age_followup(config_path=resolved_config, repo_root=root)
    paths = prepare_output_paths(
        result.config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    artifact_paths = {
        "temporal_coverage": atomic_write_parquet(
            result.coverage,
            paths.data_dir / "evaluation/individual_age_temporal_coverage.parquet",
        ),
        "origin_endpoint_census": atomic_write_parquet(
            result.origin_census,
            paths.data_dir / "evaluation/origin_endpoint_census.parquet",
        ),
        "monthly_endpoint_census": atomic_write_parquet(
            result.monthly_census,
            paths.data_dir / "evaluation/monthly_endpoint_census.parquet",
        ),
        "origin_endpoint_reason_census": atomic_write_parquet(
            result.reason_census,
            paths.data_dir / "evaluation/origin_endpoint_reason_census.parquet",
        ),
        "monthly_endpoint_reason_census": atomic_write_parquet(
            result.monthly_reason_census,
            paths.data_dir / "evaluation/monthly_endpoint_reason_census.parquet",
        ),
    }
    source_imports = {
        origin_id: {
            "outcome_free_freeze": source.freeze_descriptor,
            "coverage_required_artifacts": source.artifact_descriptors,
            "outcome_columns_passed_to_fitting_or_selection": [],
            "portfolio_artifacts_imported_for_evaluation": [],
        }
        for origin_id, source in result.sources.items()
    }
    summary = {
        "schema_version": SCHEMA_VERSION,
        "status": "complete_retrospective_individual_age_followup_sensitivity",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": protocol_commit,
        "claim_boundary": {
            "archive_and_previous_results_inspected": True,
            "retrospectively_locked": True,
            "complete_descriptive_family": True,
            "error_controlled": False,
            "hypothesis_tests": False,
            "multiplicity_adjustment": False,
            "preregistered": False,
            "confirmatory": False,
            "prospective": False,
            "independent_replication": False,
            "temporal_invariance": False,
            "selected_set_validity": False,
            "model_origin_month_or_window_selection": False,
            "pooled_origin_estimand": False,
            "portfolio_evaluated": False,
        },
        "design": {
            "origin_ids": [spec.origin_id for spec in result.origins],
            "origin_years": [spec.year for spec in result.origins],
            "common_issue_months": ["April", "May", "June"],
            "endpoint_rule": ENDPOINT_RULE,
            "issue_date_resolution": "calendar_month",
            "individual_followup_months_after_issue_month_end": INDIVIDUAL_FOLLOWUP_MONTHS,
            "cutoffs_by_issue_period": EXPECTED_CUTOFFS_BY_PERIOD,
            "maximum_supported_cutoff": MAXIMUM_SUPPORTED_CUTOFF,
            "charged_off_reporting_lag_months": CHARGED_OFF_LAG_MONTHS,
            "learner": LEARNER,
            "taxonomy_groups": CANONICAL_GROUPS,
            "windows_per_origin": EXPECTED_WINDOWS_PER_ORIGIN,
            "nominal_coverage_descriptive_reference": NOMINAL_COVERAGE,
        },
        "origin_endpoint_census": result.origin_census.to_dict(orient="records"),
        "monthly_endpoint_census": result.monthly_census.to_dict(orient="records"),
        "origin_endpoint_reason_census": result.reason_census.to_dict(orient="records"),
        "monthly_endpoint_reason_census": result.monthly_reason_census.to_dict(orient="records"),
        "canonical_individual_age_coverage": result.coverage.to_dict(orient="records"),
        "coverage_summary_by_origin": _origin_coverage_summary(result.coverage),
        "coverage_cells": int(len(result.coverage)),
        "upper_below_nominal_cells": int(
            result.coverage["coverage_upper"].lt(NOMINAL_COVERAGE).sum()
        ),
        "all_sixteen_upper_below_nominal": bool(
            result.coverage["coverage_upper"].lt(NOMINAL_COVERAGE).all()
        ),
        "selection": {
            "learner": None,
            "origin": None,
            "issue_month": None,
            "window": None,
            "endpoint": None,
        },
        "parent_equal_followup_config": result.parent_config_descriptor,
        "source_imports": source_imports,
        "raw_archive": result.raw_descriptor,
        "implementation_provenance": _implementation(
            resolved_config, result.config, result.parent_config, root
        ),
        "artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in artifact_paths.items()
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    summary_path = atomic_write_json(
        paths.model_dir / str(result.config["output"]["deterministic_summary"]), summary
    )
    atomic_write_json(
        paths.model_dir / str(result.config["output"]["execution_receipt"]),
        {
            "schema_version": SCHEMA_VERSION,
            "status": "complete_individual_age_followup_execution_receipt",
            "run_tag": RUN_TAG,
            "protocol_tag": PROTOCOL_TAG,
            "protocol_commit": protocol_commit,
            "summary": relative_artifact_descriptor(summary_path, repo_root=root),
            "environment": environment_provenance(root),
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    return summary_path


__all__: Sequence[str] = (
    "ENDPOINT_RULE",
    "EXPECTED_CUTOFFS_BY_PERIOD",
    "INDIVIDUAL_FOLLOWUP_MONTHS",
    "PROTOCOL_TAG",
    "RUN_TAG",
    "build_individual_age_census_tables",
    "compute_individual_age_followup",
    "evaluate_individual_age_coverage",
    "load_individual_age_followup_config",
    "loan_specific_cutoff_frame",
    "reconstruct_individual_age_outcomes",
    "run_individual_age_followup",
)
