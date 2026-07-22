"""Equal-relative-follow-up coverage audit for the frozen 2016 and 2017 origins."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml

from src.data.outcome_observability import (
    build_outcome_label_availability,
    parse_issue_dates,
    parse_term_months,
)
from src.ijds_audit.config import load_v4_config
from src.ijds_audit.evaluation import (
    RESOLUTION_CHARGED_OFF_BY_CUTOFF,
    RESOLUTION_FULLY_PAID_BY_CUTOFF,
    RESOLUTION_NONTERMINAL,
    RESOLUTION_TERMINAL_AFTER_CUTOFF,
    RESOLUTION_TERMINAL_DATE_MISSING,
    build_archive_outcomes,
    endpoint_resolution_audit,
    temporal_coverage_audit,
)
from src.ijds_audit.protocol import load_recipes
from src.utils.isolated_experiment import (
    environment_provenance,
    implementation_provenance,
    prepare_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_repo_input,
)
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_parquet

ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")

RUN_TAG = "ijds-rolling-origin-equal-followup-2026-07-21-v1"
PROTOCOL_TAG = "protocol/ijds-rolling-origin-equal-followup-2026-07-21-v1"
SCHEMA_VERSION = "2026-07-21.1"
PROTOCOL_STATUS = "locked_retrospective_equal_followup_coverage_evaluation"

COMMON_FOLLOWUP_MONTHS = 39
CHARGED_OFF_LAG_MONTHS = 6
CANONICAL_GROUPS = 5
EXPECTED_WINDOWS_PER_ORIGIN = 8
EXPECTED_COVERAGE_CELLS = 16
NOMINAL_COVERAGE = 0.90
LEARNER = "catboost_platt"
SCORE_COLUMN = "pd_catboost_platt"

COMPLETE_ENDPOINT_REASONS = (
    RESOLUTION_FULLY_PAID_BY_CUTOFF,
    RESOLUTION_CHARGED_OFF_BY_CUTOFF,
    RESOLUTION_NONTERMINAL,
    RESOLUTION_TERMINAL_AFTER_CUTOFF,
    RESOLUTION_TERMINAL_DATE_MISSING,
)
RESOLVED_REASONS = frozenset({RESOLUTION_FULLY_PAID_BY_CUTOFF, RESOLUTION_CHARGED_OFF_BY_CUTOFF})

OUTCOME_COLUMNS = frozenset(
    {
        "loan_status",
        "snapshot_default",
        "snapshot_resolution",
        "terminal_default",
        "terminal_outcome",
        "label_available",
        "label_available_at",
        "last_pymnt_d",
        "outcome_available_at",
        "total_pymnt",
    }
)

_WINDOWS_2016 = (
    "w01_2012m01_m06",
    "w02_2012m02_m07",
    "w03_2012m03_m08",
    "w04_2012m04_m09",
    "w05_2012m05_m10",
    "w06_2012m06_m11",
    "w07_2012m07_m12",
    "w08_2012m08_2013m01",
)
_WINDOWS_2017 = (
    "w01_2013m01_m06",
    "w02_2013m02_m07",
    "w03_2013m03_m08",
    "w04_2013m04_m09",
    "w05_2013m05_m10",
    "w06_2013m06_m11",
    "w07_2013m07_m12",
    "w08_2013m08_2014m01",
)

_ORIGIN_CONTRACTS: dict[str, dict[str, Any]] = {
    "primary_2016": {
        "year": 2016,
        "issue_periods": ("2016-04", "2016-05", "2016-06"),
        "issue_quarter_end": "2016-06-30",
        "evaluation_cutoff": "2019-09-30",
        "expected_candidate_rows": 74_537,
        "base_config": "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-12.yaml",
        "window_ids": _WINDOWS_2016,
        "freeze_path": (
            "models/experiments/ijds_audit/"
            "ijds-binary-geometry-frontier-v4-2026-07-12-v1/protocol_freeze.json"
        ),
        "freeze_bytes": 20_362,
        "freeze_sha256": ("c2b3dc2d18c9fed80708682d5a0369c80c89643e2d28024418522d954ebe667c"),
        "source_run_tag": "ijds-binary-geometry-frontier-v4-2026-07-12-v1",
        "source_protocol_tag": "protocol/ijds-binary-geometry-frontier-v4-2026-07-12-v1",
        "source_protocol_commit": "2f8a7606e4eb65aa3ae3701fb3af8d9a51c953cd",
    },
    "rolling_2017": {
        "year": 2017,
        "issue_periods": ("2017-04", "2017-05", "2017-06"),
        "issue_quarter_end": "2017-06-30",
        "evaluation_cutoff": "2020-09-30",
        "expected_candidate_rows": 77_105,
        "base_config": ("configs/experiments/ijds_rolling_origin_2017_2026-07-12_v2.yaml"),
        "window_ids": _WINDOWS_2017,
        "freeze_path": (
            "models/experiments/ijds_audit/"
            "ijds-rolling-origin-2017-2026-07-12-v2/protocol_freeze.json"
        ),
        "freeze_bytes": 21_068,
        "freeze_sha256": ("e224e1ae534435d1b166a07c50fb1ce907b07d36257f37e826ee41a0cb086759"),
        "source_run_tag": "ijds-rolling-origin-2017-2026-07-12-v2",
        "source_protocol_tag": "protocol/ijds-rolling-origin-stability-2026-07-12-v2",
        "source_protocol_commit": "9e689b2e3ca18aae5a2a967cc186da5dcd140891",
    },
}

_EXPECTED_EVALUATION = {
    "origin_ids": ["primary_2016", "rolling_2017"],
    "origin_years": [2016, 2017],
    "common_issue_month_numbers": [4, 5, 6],
    "common_primary_months": 3,
    "common_followup_months_after_quarter_end": COMMON_FOLLOWUP_MONTHS,
    "charged_off_reporting_lag_months": CHARGED_OFF_LAG_MONTHS,
    "alpha": 0.10,
    "nominal_coverage": NOMINAL_COVERAGE,
    "learner": LEARNER,
    "score_column": SCORE_COLUMN,
    "taxonomy_groups": CANONICAL_GROUPS,
    "aggregate_stratum": -1,
    "expected_windows_per_origin": EXPECTED_WINDOWS_PER_ORIGIN,
    "expected_coverage_cells": EXPECTED_COVERAGE_CELLS,
    "complete_endpoint_reason_rows_per_origin": len(COMPLETE_ENDPOINT_REASONS),
    "no_model_selection": True,
    "no_origin_selection": True,
    "no_window_selection": True,
    "no_pooling": True,
    "no_portfolio_evaluation": True,
}


@dataclass(frozen=True)
class OriginSpec:
    """One predeclared frozen origin and its relative endpoint."""

    origin_id: str
    year: int
    issue_periods: tuple[str, ...]
    issue_quarter_end: str
    evaluation_cutoff: str
    expected_candidate_rows: int
    base_config: str
    window_ids: tuple[str, ...]
    source_freeze: dict[str, Any]


@dataclass(frozen=True)
class VerifiedOriginSource:
    """Hash-verified coverage-only imports from one outcome-free freeze."""

    spec: OriginSpec
    base_config: dict[str, Any]
    base_config_descriptor: dict[str, Any]
    freeze: dict[str, Any]
    freeze_descriptor: dict[str, Any]
    artifact_paths: dict[str, Path]
    artifact_descriptors: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class EqualFollowupComputation:
    """Validated in-memory result before fresh artifacts are written."""

    config: dict[str, Any]
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


def validate_common_followup_cutoff(
    *, issue_quarter_end: str, evaluation_cutoff: str, followup_months: int
) -> None:
    """Require the endpoint to be exactly the declared month offset from quarter end."""
    if int(followup_months) != COMMON_FOLLOWUP_MONTHS:
        raise RuntimeError(
            f"Common relative follow-up changed: {followup_months} != {COMMON_FOLLOWUP_MONTHS}."
        )
    quarter_end = pd.Timestamp(issue_quarter_end)
    cutoff = pd.Timestamp(evaluation_cutoff)
    expected = quarter_end + pd.DateOffset(months=COMMON_FOLLOWUP_MONTHS)
    if cutoff != expected:
        raise RuntimeError(f"Equal-follow-up cutoff changed: {cutoff.date()} != {expected.date()}.")


def _parse_origin(value: Mapping[str, Any]) -> OriginSpec:
    expected_keys = {
        "id",
        "year",
        "issue_periods",
        "issue_quarter_end",
        "evaluation_cutoff",
        "expected_candidate_rows",
        "base_config",
        "window_ids",
        "source_freeze",
    }
    _require_exact_keys(value, expected_keys, context="origin")
    origin_id = str(value["id"])
    if origin_id not in _ORIGIN_CONTRACTS:
        raise ValueError(f"Unexpected equal-follow-up origin: {origin_id!r}.")
    locked = _ORIGIN_CONTRACTS[origin_id]
    source = value["source_freeze"]
    if not isinstance(source, Mapping):
        raise TypeError(f"{origin_id} source_freeze must be a mapping.")
    _require_exact_keys(
        source,
        {
            "path",
            "bytes",
            "sha256",
            "run_tag",
            "protocol_tag",
            "protocol_commit",
            "required_artifacts",
        },
        context=f"{origin_id} source freeze",
    )
    artifacts = source["required_artifacts"]
    if not isinstance(artifacts, Mapping):
        raise TypeError(f"{origin_id} required_artifacts must be a mapping.")
    _require_exact_keys(
        artifacts, {"scores", "recipes", "fit_audit"}, context=f"{origin_id} artifacts"
    )
    for name, descriptor in artifacts.items():
        if not isinstance(descriptor, Mapping):
            raise TypeError(f"{origin_id}/{name} descriptor must be a mapping.")
        _validate_descriptor(descriptor, context=f"{origin_id}/{name}")

    year = int(value["year"])
    issue_periods = tuple(str(item) for item in value["issue_periods"])
    issue_quarter_end = str(value["issue_quarter_end"])
    evaluation_cutoff = str(value["evaluation_cutoff"])
    expected_candidate_rows = int(value["expected_candidate_rows"])
    base_config = str(value["base_config"])
    window_ids = tuple(str(item) for item in value["window_ids"])
    observed: dict[str, Any] = {
        "year": year,
        "issue_periods": issue_periods,
        "issue_quarter_end": issue_quarter_end,
        "evaluation_cutoff": evaluation_cutoff,
        "expected_candidate_rows": expected_candidate_rows,
        "base_config": base_config,
        "window_ids": window_ids,
        "freeze_path": str(source["path"]),
        "freeze_bytes": int(source["bytes"]),
        "freeze_sha256": str(source["sha256"]),
        "source_run_tag": str(source["run_tag"]),
        "source_protocol_tag": str(source["protocol_tag"]),
        "source_protocol_commit": str(source["protocol_commit"]),
    }
    for field, expected in locked.items():
        if observed[field] != expected:
            raise RuntimeError(
                f"{origin_id} locked field {field} changed: {observed[field]!r} != {expected!r}."
            )
    validate_common_followup_cutoff(
        issue_quarter_end=issue_quarter_end,
        evaluation_cutoff=evaluation_cutoff,
        followup_months=COMMON_FOLLOWUP_MONTHS,
    )
    return OriginSpec(
        origin_id=origin_id,
        year=year,
        issue_periods=issue_periods,
        issue_quarter_end=issue_quarter_end,
        evaluation_cutoff=evaluation_cutoff,
        expected_candidate_rows=expected_candidate_rows,
        base_config=base_config,
        window_ids=window_ids,
        source_freeze=dict(source),
    )


def load_equal_followup_config(path: Path, *, repo_root: Path) -> dict[str, Any]:
    """Load and strictly validate the isolated equal-follow-up protocol config."""
    resolved = resolve_repo_input(path, repo_root=repo_root)
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Equal-follow-up config must be a YAML mapping.")
    _require_exact_keys(
        payload,
        {
            "schema_version",
            "protocol_status",
            "protocol_tag",
            "run_tag",
            "protocol_document",
            "protocol_lineage_files",
            "raw_source",
            "evaluation",
            "origins",
            "output",
        },
        context="equal-follow-up config",
    )
    identities = {
        "schema_version": SCHEMA_VERSION,
        "protocol_status": PROTOCOL_STATUS,
        "protocol_tag": PROTOCOL_TAG,
        "run_tag": RUN_TAG,
    }
    for field, expected in identities.items():
        if str(payload[field]) != expected:
            raise RuntimeError(f"Equal-follow-up {field} changed.")

    evaluation = payload["evaluation"]
    if not isinstance(evaluation, Mapping) or dict(evaluation) != _EXPECTED_EVALUATION:
        raise RuntimeError("The complete equal-follow-up evaluation contract changed.")

    raw_source = payload["raw_source"]
    if not isinstance(raw_source, Mapping):
        raise TypeError("raw_source must be a mapping.")
    _require_exact_keys(
        raw_source,
        {"path", "bytes", "sha256", "csv_chunksize", "membership_uses_status"},
        context="raw source",
    )
    if {
        "path": str(raw_source["path"]),
        "bytes": int(raw_source["bytes"]),
        "sha256": str(raw_source["sha256"]),
        "membership_uses_status": raw_source["membership_uses_status"],
    } != {
        "path": "data/raw/Loan_status_2007-2020Q3.csv",
        "bytes": 1_773_470_505,
        "sha256": "5878af2a088f8ab5214c9337289fb8b5eb6c6338fd3f417b6cdc18513dc6f35f",
        "membership_uses_status": False,
    }:
        raise RuntimeError("The equal-follow-up raw archive contract changed.")
    if int(raw_source["csv_chunksize"]) <= 0:
        raise ValueError("raw_source.csv_chunksize must be positive.")

    origins_value = payload["origins"]
    if not isinstance(origins_value, list):
        raise TypeError("origins must be a list.")
    origins = tuple(_parse_origin(item) for item in origins_value)
    if tuple(origin.origin_id for origin in origins) != ("primary_2016", "rolling_2017"):
        raise RuntimeError("The origin order or complete two-origin family changed.")

    root = repo_root.resolve()
    protocol_document = resolve_repo_input(str(payload["protocol_document"]), repo_root=root)
    if protocol_document.name != "ijds_rolling_origin_equal_followup_protocol_2026-07-21.md":
        raise RuntimeError("The equal-follow-up protocol document changed.")
    lineage = payload["protocol_lineage_files"]
    if not isinstance(lineage, list) or not lineage:
        raise TypeError("protocol_lineage_files must be a nonempty list.")
    for lineage_path in lineage:
        resolve_repo_input(str(lineage_path), repo_root=root)

    for origin in origins:
        base_path = resolve_repo_input(origin.base_config, repo_root=root)
        base = load_v4_config(base_path)
        if str(base["source"]["raw_path"]) != str(raw_source["path"]):
            raise RuntimeError(f"{origin.origin_id} base config changed the raw archive.")
        if int(base["source"]["charged_off_reporting_lag_months"]) != CHARGED_OFF_LAG_MONTHS:
            raise RuntimeError(f"{origin.origin_id} base config changed the charged-off lag.")
        if float(base["conformal"]["alpha"]) != 0.10:
            raise RuntimeError(f"{origin.origin_id} base config changed alpha.")
        if int(base["conformal"]["canonical_groups"]) != CANONICAL_GROUPS:
            raise RuntimeError(f"{origin.origin_id} base config changed the canonical taxonomy.")
        base_windows = tuple(
            str(window["id"]) for window in base["residual_specification"]["windows"]
        )
        if base_windows != origin.window_ids:
            raise RuntimeError(f"{origin.origin_id} base config changed the eight windows.")

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
        context="output",
    )
    if output != {
        "data_root": ALLOWED_DATA_ROOT.as_posix(),
        "model_root": ALLOWED_MODEL_ROOT.as_posix(),
        "deterministic_summary": "rolling_origin_equal_followup_summary.json",
        "execution_receipt": "execution_receipt.json",
        "immutability": "hard_no_overwrite_choose_fresh_run_tag",
    }:
        raise RuntimeError("The isolated equal-follow-up output contract changed.")
    return payload


def origin_specs(config: Mapping[str, Any]) -> tuple[OriginSpec, ...]:
    """Return the already validated origin specifications."""
    origins = config.get("origins")
    if not isinstance(origins, list):
        raise TypeError("Equal-follow-up origins must be a list.")
    return tuple(_parse_origin(item) for item in origins)


def _descriptor_matches(
    observed: Mapping[str, Any], expected: Mapping[str, Any], *, context: str
) -> None:
    for field in ("path", "bytes", "sha256"):
        if observed.get(field) != expected.get(field):
            raise RuntimeError(f"{context} descriptor mismatch for {field}.")


def verify_origin_freeze(spec: OriginSpec, *, repo_root: Path) -> VerifiedOriginSource:
    """Verify one freeze and only its three coverage-required artifacts."""
    root = repo_root.resolve()
    source = spec.source_freeze
    freeze_path = resolve_repo_input(str(source["path"]), repo_root=root)
    freeze_descriptor = relative_artifact_descriptor(freeze_path, repo_root=root)
    _descriptor_matches(freeze_descriptor, source, context=f"{spec.origin_id} freeze")
    freeze_payload = json.loads(freeze_path.read_text(encoding="utf-8"))
    if not isinstance(freeze_payload, dict):
        raise TypeError(f"{spec.origin_id} source freeze must be a JSON mapping.")
    expected_identity = {
        "status": "outcome_free_allocations_frozen_before_archive_outcome_join",
        "run_tag": str(source["run_tag"]),
        "protocol_tag": str(source["protocol_tag"]),
        "protocol_commit": str(source["protocol_commit"]),
    }
    for field, expected in expected_identity.items():
        if freeze_payload.get(field) != expected:
            raise RuntimeError(f"{spec.origin_id} source freeze mismatch for {field}.")
    if freeze_payload.get("outcome_columns_passed_to_policy_or_comparator") != []:
        raise RuntimeError(f"{spec.origin_id} source freeze reports outcome leakage.")
    if freeze_payload.get("window_selection") != "none_all_eight_co_primary":
        raise RuntimeError(f"{spec.origin_id} source freeze changed window selection.")

    frozen_artifacts = freeze_payload.get("outcome_free_artifacts")
    if not isinstance(frozen_artifacts, Mapping):
        raise KeyError(f"{spec.origin_id} source freeze lacks outcome_free_artifacts.")
    required = source["required_artifacts"]
    artifact_paths: dict[str, Path] = {}
    artifact_descriptors: dict[str, dict[str, Any]] = {}
    for name in ("scores", "recipes", "fit_audit"):
        declared = required[name]
        embedded = frozen_artifacts.get(name)
        if not isinstance(embedded, Mapping):
            raise KeyError(f"{spec.origin_id} freeze lacks required artifact {name}.")
        _descriptor_matches(embedded, declared, context=f"{spec.origin_id}/{name} embedded")
        artifact_path = resolve_repo_input(str(declared["path"]), repo_root=root)
        actual = relative_artifact_descriptor(artifact_path, repo_root=root)
        _descriptor_matches(actual, declared, context=f"{spec.origin_id}/{name} on disk")
        artifact_paths[name] = artifact_path
        artifact_descriptors[name] = actual

    base_path = resolve_repo_input(spec.base_config, repo_root=root)
    base_config = load_v4_config(base_path)
    return VerifiedOriginSource(
        spec=spec,
        base_config=base_config,
        base_config_descriptor=relative_artifact_descriptor(base_path, repo_root=root),
        freeze=freeze_payload,
        freeze_descriptor=freeze_descriptor,
        artifact_paths=artifact_paths,
        artifact_descriptors=artifact_descriptors,
    )


def select_origin_scores(scores: pd.DataFrame, spec: OriginSpec) -> pd.DataFrame:
    """Select one frozen April--June CatBoost candidate census without outcomes."""
    required = {"id", "issue_d", "design_split", SCORE_COLUMN}
    missing = sorted(required.difference(scores.columns))
    if missing:
        raise KeyError(f"{spec.origin_id} frozen scores are missing columns: {missing}.")
    forbidden = sorted(OUTCOME_COLUMNS.intersection(scores.columns))
    if forbidden:
        raise RuntimeError(f"Outcome columns entered {spec.origin_id} frozen scores: {forbidden}.")
    if bool(scores["id"].isna().any()) or bool(scores["id"].duplicated().any()):
        raise RuntimeError(f"{spec.origin_id} frozen score IDs must be complete and unique.")
    issue_dates = pd.to_datetime(scores["issue_d"], errors="coerce")
    if bool(issue_dates.isna().any()):
        raise RuntimeError(f"{spec.origin_id} frozen scores contain an invalid issue date.")
    periods = issue_dates.dt.to_period("M").astype(str)
    mask = scores["design_split"].astype(str).eq("primary_oot") & periods.isin(spec.issue_periods)
    selected = scores.loc[mask, ["id", "issue_d", "design_split", SCORE_COLUMN]].copy()
    selected["id"] = selected["id"].astype("string").str.strip()
    selected["issue_d"] = pd.to_datetime(selected["issue_d"], errors="raise")
    selected["period"] = selected["issue_d"].dt.to_period("M").astype("string")
    selected["origin_id"] = spec.origin_id
    selected["origin_year"] = spec.year
    selected = selected.sort_values(["issue_d", "id"], kind="mergesort").reset_index(drop=True)

    observed_periods = tuple(sorted(selected["period"].astype(str).unique()))
    if observed_periods != spec.issue_periods:
        raise RuntimeError(
            f"{spec.origin_id} candidate periods changed: {observed_periods} != "
            f"{spec.issue_periods}."
        )
    if len(selected) != spec.expected_candidate_rows:
        raise RuntimeError(
            f"{spec.origin_id} candidate census changed: {len(selected)} != "
            f"{spec.expected_candidate_rows}."
        )
    if bool(selected["id"].eq("").any()) or bool(selected["id"].duplicated().any()):
        raise RuntimeError(f"{spec.origin_id} selected score IDs are invalid.")
    probability = pd.to_numeric(selected[SCORE_COLUMN], errors="coerce").to_numpy(dtype=float)
    if not bool(np.isfinite(probability).all()) or bool(
        ((probability < 0) | (probability > 1)).any()
    ):
        raise RuntimeError(f"{spec.origin_id} CatBoost probabilities are invalid.")
    return selected


def load_raw_candidate_rows(
    raw_path: Path,
    frozen_scores: pd.DataFrame,
    *,
    csv_chunksize: int,
) -> pd.DataFrame:
    """Load raw endpoint fields for exactly the status-independent frozen IDs."""
    required_scores = {"id", "origin_id", "origin_year", "period"}
    missing_scores = sorted(required_scores.difference(frozen_scores.columns))
    if missing_scores:
        raise KeyError(f"Frozen candidate census is missing columns: {missing_scores}.")
    if bool(frozen_scores["id"].isna().any()) or bool(frozen_scores["id"].duplicated().any()):
        raise RuntimeError("The combined frozen candidate census must have unique complete IDs.")
    frozen = frozen_scores.loc[:, ["id", "origin_id", "origin_year", "period"]].copy()
    frozen["id"] = frozen["id"].astype("string").str.strip()
    frozen = frozen.rename(columns={"period": "frozen_period"})
    candidate_ids = frozenset(frozen["id"].astype(str))

    columns = ["id", "issue_d", "term", "loan_status", "last_pymnt_d"]
    header = pd.read_csv(raw_path, nrows=0)
    missing_raw = sorted(set(columns).difference(header.columns))
    if missing_raw:
        raise KeyError(f"Raw archive is missing equal-follow-up columns: {missing_raw}.")
    chunks: list[pd.DataFrame] = []
    for chunk in pd.read_csv(
        raw_path,
        usecols=columns,
        dtype={
            "id": "string",
            "issue_d": "string",
            "term": "string",
            "loan_status": "string",
            "last_pymnt_d": "string",
        },
        chunksize=int(csv_chunksize),
        low_memory=False,
    ):
        normalized_ids = chunk["id"].astype("string").str.strip()
        keep = normalized_ids.astype(str).isin(candidate_ids)
        if not bool(keep.any()):
            continue
        retained = chunk.loc[keep].copy()
        retained["id"] = normalized_ids.loc[keep]
        chunks.append(retained)
    if not chunks:
        raise RuntimeError("Raw archive scan found none of the frozen candidate IDs.")
    raw = pd.concat(chunks, ignore_index=True)
    if bool(raw["id"].isna().any()) or bool(raw["id"].duplicated().any()):
        raise RuntimeError("Raw candidate endpoint rows must have unique complete IDs.")
    joined = frozen.merge(raw, on="id", how="outer", validate="one_to_one", indicator=True)
    missing = int(joined["_merge"].eq("left_only").sum())
    extra = int(joined["_merge"].eq("right_only").sum())
    if missing or extra:
        raise RuntimeError(f"Raw candidate ID census mismatch: missing={missing}, extra={extra}.")
    joined = joined.drop(columns="_merge")
    issue_dates = parse_issue_dates(joined["issue_d"])
    if bool(issue_dates.isna().any()):
        raise RuntimeError("Raw candidate endpoint rows contain an invalid issue date.")
    raw_period = issue_dates.dt.to_period("M").astype("string")
    if not raw_period.astype(str).equals(joined["frozen_period"].astype(str)):
        bad = joined.loc[raw_period.astype(str).ne(joined["frozen_period"].astype(str)), "id"]
        raise RuntimeError(f"Raw issue month disagrees with frozen scores: {bad.head(5).tolist()}.")
    terms = parse_term_months(joined["term"])
    if not bool(terms.eq(36).fillna(False).all()):
        bad = joined.loc[~terms.eq(36).fillna(False), "id"].head(5).tolist()
        raise RuntimeError(f"Raw candidate term disagrees with the 36-month design: {bad}.")
    joined["issue_d"] = issue_dates
    joined["period"] = raw_period
    return joined.sort_values(["origin_year", "issue_d", "id"], kind="mergesort").reset_index(
        drop=True
    )


def reconstruct_origin_outcomes(
    raw_candidates: pd.DataFrame,
    spec: OriginSpec,
    *,
    charged_off_lag_months: int = CHARGED_OFF_LAG_MONTHS,
) -> pd.DataFrame:
    """Reconstruct one origin endpoint at its locked relative cutoff."""
    if int(charged_off_lag_months) != CHARGED_OFF_LAG_MONTHS:
        raise RuntimeError("The frozen six-month charged-off lag changed.")
    validate_common_followup_cutoff(
        issue_quarter_end=spec.issue_quarter_end,
        evaluation_cutoff=spec.evaluation_cutoff,
        followup_months=COMMON_FOLLOWUP_MONTHS,
    )
    selected = raw_candidates.loc[raw_candidates["origin_id"].astype(str).eq(spec.origin_id)].copy()
    if len(selected) != spec.expected_candidate_rows:
        raise RuntimeError(f"{spec.origin_id} raw endpoint census changed.")
    if tuple(sorted(selected["period"].astype(str).unique())) != spec.issue_periods:
        raise RuntimeError(f"{spec.origin_id} raw endpoint periods changed.")
    labels = build_outcome_label_availability(
        selected["loan_status"],
        selected["last_pymnt_d"],
        cutoff=spec.evaluation_cutoff,
        charged_off_lag_months=CHARGED_OFF_LAG_MONTHS,
    )
    universe = pd.DataFrame(
        {
            "id": selected["id"].astype("string"),
            "issue_d": pd.to_datetime(selected["issue_d"], errors="raise"),
            "design_split": pd.Series("primary_oot", index=selected.index, dtype="string"),
            "terminal_default": labels["terminal_outcome"].astype("Int8"),
            "label_available_at": labels["label_available_at"],
        },
        index=selected.index,
    )
    outcomes = build_archive_outcomes(universe, evaluation_cutoff=spec.evaluation_cutoff)
    outcomes["origin_id"] = spec.origin_id
    outcomes["origin_year"] = spec.year
    outcomes["issue_quarter_end"] = spec.issue_quarter_end
    outcomes["evaluation_cutoff"] = spec.evaluation_cutoff
    outcomes["common_followup_months"] = COMMON_FOLLOWUP_MONTHS
    observed_reasons = set(outcomes["snapshot_resolution"].astype(str))
    unexpected = sorted(observed_reasons.difference(COMPLETE_ENDPOINT_REASONS))
    if unexpected:
        raise RuntimeError(f"{spec.origin_id} produced unexpected endpoint reasons: {unexpected}.")
    if bool(outcomes["id"].isna().any()) or bool(outcomes["id"].duplicated().any()):
        raise RuntimeError(f"{spec.origin_id} reconstructed outcome IDs are invalid.")
    return outcomes.sort_values(["period", "id"], kind="mergesort").reset_index(drop=True)


def _complete_reason_rows(
    grouped: pd.DataFrame,
    *,
    index: pd.Index | pd.MultiIndex,
) -> pd.DataFrame:
    completed = grouped.set_index(list(index.names)).reindex(index, fill_value=0).reset_index()
    for column in ("candidate_rows", "resolved_rows", "unresolved_rows"):
        completed[column] = completed[column].astype("int64")
    return completed


def build_endpoint_census_tables(
    outcomes: pd.DataFrame, spec: OriginSpec
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build and validate complete origin/month/reason endpoint censuses."""
    if len(outcomes) != spec.expected_candidate_rows:
        raise RuntimeError(f"{spec.origin_id} endpoint census changed before reporting.")
    resolved_mask = outcomes["snapshot_default"].notna()
    origin_census = pd.DataFrame(
        [
            {
                "origin_id": spec.origin_id,
                "origin_year": spec.year,
                "issue_quarter_end": spec.issue_quarter_end,
                "evaluation_cutoff": spec.evaluation_cutoff,
                "common_followup_months": COMMON_FOLLOWUP_MONTHS,
                "candidate_rows": int(len(outcomes)),
                "resolved_rows": int(resolved_mask.sum()),
                "unresolved_rows": int((~resolved_mask).sum()),
            }
        ]
    )

    monthly = (
        outcomes.assign(__resolved=resolved_mask)
        .groupby("period", observed=True, sort=True)
        .agg(candidate_rows=("id", "size"), resolved_rows=("__resolved", "sum"))
    )
    monthly = monthly.reindex(
        pd.Index(spec.issue_periods, name="period"), fill_value=0
    ).reset_index()
    monthly["resolved_rows"] = monthly["resolved_rows"].astype("int64")
    monthly["candidate_rows"] = monthly["candidate_rows"].astype("int64")
    monthly["unresolved_rows"] = monthly["candidate_rows"] - monthly["resolved_rows"]
    monthly.insert(0, "origin_year", spec.year)
    monthly.insert(0, "origin_id", spec.origin_id)
    monthly["evaluation_cutoff"] = spec.evaluation_cutoff
    monthly["common_followup_months"] = COMMON_FOLLOWUP_MONTHS
    if bool(monthly["candidate_rows"].le(0).any()):
        raise RuntimeError(f"{spec.origin_id} has an empty declared issue month.")

    observed_reason = endpoint_resolution_audit(outcomes, roles=("primary_oot",)).drop(
        columns="role"
    )
    reason_index = pd.Index(COMPLETE_ENDPOINT_REASONS, name="snapshot_resolution")
    reason = _complete_reason_rows(observed_reason, index=reason_index)
    reason.insert(0, "origin_year", spec.year)
    reason.insert(0, "origin_id", spec.origin_id)
    reason["evaluation_cutoff"] = spec.evaluation_cutoff
    reason["common_followup_months"] = COMMON_FOLLOWUP_MONTHS

    monthly_observed = (
        outcomes.assign(__resolved=resolved_mask)
        .groupby(["period", "snapshot_resolution"], observed=True, sort=True)
        .agg(candidate_rows=("id", "size"), resolved_rows=("__resolved", "sum"))
        .reset_index()
    )
    monthly_observed["resolved_rows"] = monthly_observed["resolved_rows"].astype("int64")
    monthly_observed["unresolved_rows"] = (
        monthly_observed["candidate_rows"] - monthly_observed["resolved_rows"]
    )
    monthly_reason_index = pd.MultiIndex.from_product(
        [spec.issue_periods, COMPLETE_ENDPOINT_REASONS],
        names=["period", "snapshot_resolution"],
    )
    monthly_reason = _complete_reason_rows(monthly_observed, index=monthly_reason_index)
    monthly_reason.insert(0, "origin_year", spec.year)
    monthly_reason.insert(0, "origin_id", spec.origin_id)
    monthly_reason["evaluation_cutoff"] = spec.evaluation_cutoff
    monthly_reason["common_followup_months"] = COMMON_FOLLOWUP_MONTHS

    if int(reason["candidate_rows"].sum()) != len(outcomes):
        raise RuntimeError(f"{spec.origin_id} endpoint reasons do not partition candidates.")
    if int(monthly["candidate_rows"].sum()) != len(outcomes):
        raise RuntimeError(f"{spec.origin_id} monthly census does not partition candidates.")
    if int(monthly_reason["candidate_rows"].sum()) != len(outcomes):
        raise RuntimeError(f"{spec.origin_id} monthly reasons do not partition candidates.")
    reason_columns = [
        "snapshot_resolution",
        "candidate_rows",
        "resolved_rows",
        "unresolved_rows",
    ]
    for snapshot_resolution, candidate_rows, resolved_rows, unresolved_rows in reason.loc[
        :, reason_columns
    ].itertuples(index=False, name=None):
        should_resolve = str(snapshot_resolution) in RESOLVED_REASONS
        expected_resolved = int(candidate_rows) if should_resolve else 0
        if int(resolved_rows) != expected_resolved:
            raise RuntimeError(
                f"{spec.origin_id}/{snapshot_resolution} has inconsistent resolution."
            )
        if int(unresolved_rows) != int(candidate_rows) - expected_resolved:
            raise RuntimeError(
                f"{spec.origin_id}/{snapshot_resolution} has inconsistent nonresolution."
            )
    aggregate_from_months = (
        monthly_reason.groupby("snapshot_resolution", observed=True, sort=False)[
            ["candidate_rows", "resolved_rows", "unresolved_rows"]
        ]
        .sum()
        .reindex(COMPLETE_ENDPOINT_REASONS)
        .reset_index()
    )
    comparison_columns = [
        "snapshot_resolution",
        "candidate_rows",
        "resolved_rows",
        "unresolved_rows",
    ]
    expected_reason = reason.loc[:, comparison_columns].reset_index(drop=True)
    actual_reason = aggregate_from_months.loc[:, comparison_columns].reset_index(drop=True)
    if not expected_reason.equals(actual_reason):
        raise RuntimeError(f"{spec.origin_id} monthly and aggregate reasons disagree.")
    return origin_census, monthly, reason, monthly_reason


def evaluate_origin_coverage(
    scores: pd.DataFrame,
    outcomes: pd.DataFrame,
    source: VerifiedOriginSource,
) -> pd.DataFrame:
    """Evaluate all eight frozen CatBoost windows for one origin."""
    spec = source.spec
    recipes = load_recipes(source.artifact_paths["recipes"])
    if LEARNER not in recipes:
        raise RuntimeError(f"{spec.origin_id} freeze lacks the CatBoost recipe family.")
    learner_recipes = recipes[LEARNER]
    if tuple(learner_recipes) != spec.window_ids:
        raise RuntimeError(f"{spec.origin_id} frozen CatBoost windows changed.")
    for window_id, group_recipes in learner_recipes.items():
        if CANONICAL_GROUPS not in group_recipes:
            raise RuntimeError(f"{spec.origin_id}/{window_id} lacks the five-stratum recipe.")
    fit_audit = pd.read_parquet(source.artifact_paths["fit_audit"])
    coverage = temporal_coverage_audit(
        scores,
        outcomes,
        {LEARNER: learner_recipes},
        fit_audit,
        roles=("primary_oot",),
        taxonomy_group_counts=(CANONICAL_GROUPS,),
        strata=(-1,),
    )
    ordinal = {window_id: index for index, window_id in enumerate(spec.window_ids, start=1)}
    coverage["window_ordinal"] = coverage["window_id"].map(ordinal)
    coverage["origin_id"] = spec.origin_id
    coverage["origin_year"] = spec.year
    coverage["issue_period_start"] = spec.issue_periods[0]
    coverage["issue_period_end"] = spec.issue_periods[-1]
    coverage["issue_quarter_end"] = spec.issue_quarter_end
    coverage["evaluation_cutoff"] = spec.evaluation_cutoff
    coverage["common_followup_months"] = COMMON_FOLLOWUP_MONTHS
    coverage = coverage.sort_values("window_ordinal", kind="mergesort").reset_index(drop=True)

    if len(coverage) != EXPECTED_WINDOWS_PER_ORIGIN:
        raise RuntimeError(f"{spec.origin_id} coverage grid does not contain eight cells.")
    if tuple(coverage["window_id"].astype(str)) != spec.window_ids:
        raise RuntimeError(f"{spec.origin_id} coverage output changed window order or identity.")
    fixed_checks = {
        "learner": LEARNER,
        "taxonomy_groups": CANONICAL_GROUPS,
        "role": "primary_oot",
        "conformal_group": -1,
        "candidate_rows": spec.expected_candidate_rows,
    }
    for column, expected in fixed_checks.items():
        if not coverage[column].eq(expected).all():
            raise RuntimeError(f"{spec.origin_id} coverage {column} changed.")
    bounded = (
        "coverage_resolved",
        "coverage_lower",
        "coverage_upper",
        "mean_width",
        "set_empty_share",
        "set_zero_only_share",
        "set_one_only_share",
        "set_both_share",
    )
    values = coverage.loc[:, list(bounded)].apply(pd.to_numeric, errors="coerce")
    if (
        bool(values.isna().any().any())
        or not values.ge(0.0).all().all()
        or not values.le(1.0).all().all()
    ):
        raise RuntimeError(f"{spec.origin_id} coverage contains nonfinite/out-of-range values.")
    if not coverage["coverage_lower"].le(coverage["coverage_upper"]).all():
        raise RuntimeError(f"{spec.origin_id} sharp coverage bounds are inverted.")
    set_sum = coverage.loc[
        :, ["set_empty_share", "set_zero_only_share", "set_one_only_share", "set_both_share"]
    ].sum(axis=1)
    if not np.allclose(set_sum.to_numpy(dtype=float), 1.0, atol=1e-12, rtol=1e-12):
        raise RuntimeError(f"{spec.origin_id} binary-set shares do not partition one.")
    return coverage


def compute_equal_followup(*, config_path: Path, repo_root: Path) -> EqualFollowupComputation:
    """Compute the complete two-origin evaluation in memory without writing outputs."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_equal_followup_config(resolved_config, repo_root=root)
    specs = origin_specs(config)
    sources = {spec.origin_id: verify_origin_freeze(spec, repo_root=root) for spec in specs}

    score_frames: dict[str, pd.DataFrame] = {}
    for spec in specs:
        source = sources[spec.origin_id]
        scores = pd.read_parquet(source.artifact_paths["scores"])
        score_frames[spec.origin_id] = select_origin_scores(scores, spec)
    combined_scores = pd.concat(score_frames.values(), ignore_index=True)
    if bool(combined_scores["id"].duplicated().any()):
        raise RuntimeError("The frozen 2016 and 2017 candidate identities overlap.")

    raw_path = resolve_repo_input(str(config["raw_source"]["path"]), repo_root=root)
    raw_descriptor = relative_artifact_descriptor(raw_path, repo_root=root)
    _descriptor_matches(raw_descriptor, config["raw_source"], context="raw archive")
    raw_candidates = load_raw_candidate_rows(
        raw_path,
        combined_scores,
        csv_chunksize=int(config["raw_source"]["csv_chunksize"]),
    )

    coverage_frames: list[pd.DataFrame] = []
    origin_censuses: list[pd.DataFrame] = []
    monthly_censuses: list[pd.DataFrame] = []
    reason_censuses: list[pd.DataFrame] = []
    monthly_reason_censuses: list[pd.DataFrame] = []
    for spec in specs:
        outcomes = reconstruct_origin_outcomes(raw_candidates, spec)
        origin_census, monthly, reasons, monthly_reasons = build_endpoint_census_tables(
            outcomes, spec
        )
        coverage = evaluate_origin_coverage(
            score_frames[spec.origin_id], outcomes, sources[spec.origin_id]
        )
        resolved = int(origin_census.iloc[0]["resolved_rows"])
        unresolved = int(origin_census.iloc[0]["unresolved_rows"])
        if not coverage["resolved_rows"].eq(resolved).all():
            raise RuntimeError(f"{spec.origin_id} coverage resolved census disagrees.")
        if not coverage["unresolved_rows"].eq(unresolved).all():
            raise RuntimeError(f"{spec.origin_id} coverage unresolved census disagrees.")
        coverage_frames.append(coverage)
        origin_censuses.append(origin_census)
        monthly_censuses.append(monthly)
        reason_censuses.append(reasons)
        monthly_reason_censuses.append(monthly_reasons)

    coverage = pd.concat(coverage_frames, ignore_index=True).sort_values(
        ["origin_year", "window_ordinal"], kind="mergesort"
    )
    if len(coverage) != EXPECTED_COVERAGE_CELLS:
        raise RuntimeError("The equal-follow-up coverage grid is not the locked 16-cell family.")
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
    if len(origin_census) != 2 or len(monthly_census) != 6:
        raise RuntimeError("The equal-follow-up origin/month census grid is incomplete.")
    if len(reason_census) != 10 or len(monthly_reason_census) != 30:
        raise RuntimeError("The complete equal-follow-up reason grid is incomplete.")

    return EqualFollowupComputation(
        config=config,
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
    config_path: Path, config: Mapping[str, Any], repo_root: Path
) -> dict[str, Any]:
    paths = [
        Path("scripts/experiments/run_ijds_rolling_origin_equal_followup.py"),
        Path("src/ijds_audit/rolling_origin_equal_followup.py"),
        Path("src/ijds_audit/config.py"),
        Path("src/ijds_audit/evaluation.py"),
        Path("src/ijds_audit/protocol.py"),
        Path("src/data/outcome_observability.py"),
        Path("src/models/binary_conformal_guardrail.py"),
        Path("src/evaluation/coverage_transport.py"),
        *[Path(value) for value in config["protocol_lineage_files"]],
        *[Path(str(origin["base_config"])) for origin in config["origins"]],
    ]
    return implementation_provenance(
        config_path=config_path,
        repo_root=repo_root,
        relative_paths=paths,
    )


def _origin_coverage_summary(coverage: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_key, frame in coverage.groupby(["origin_id", "origin_year"], observed=True, sort=True):
        origin_id, origin_year = cast(tuple[str, int], raw_key)
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


def run_equal_followup(*, config_path: Path, repo_root: Path) -> Path:
    """Require a clean protocol tag and write one fresh immutable evaluation."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    load_equal_followup_config(resolved_config, repo_root=root)
    protocol_commit = require_clean_tagged_head(root, PROTOCOL_TAG)
    result = compute_equal_followup(config_path=resolved_config, repo_root=root)
    paths = prepare_output_paths(
        result.config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    artifact_paths = {
        "temporal_coverage": atomic_write_parquet(
            result.coverage,
            paths.data_dir / "evaluation/equal_followup_temporal_coverage.parquet",
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
            "base_config": source.base_config_descriptor,
            "outcome_free_freeze": source.freeze_descriptor,
            "coverage_required_artifacts": source.artifact_descriptors,
            "outcome_columns_passed_to_fitting_or_selection": [],
            "portfolio_artifacts_imported_for_evaluation": [],
        }
        for origin_id, source in result.sources.items()
    }
    summary = {
        "schema_version": SCHEMA_VERSION,
        "status": "complete_retrospective_equal_relative_followup_coverage_evaluation",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": protocol_commit,
        "claim_boundary": {
            "archive_and_previous_results_inspected": True,
            "retrospectively_locked": True,
            "preregistered": False,
            "confirmatory": False,
            "prospective": False,
            "independent_replication": False,
            "temporal_invariance": False,
            "selected_set_validity": False,
            "model_origin_or_window_selection": False,
            "pooled_origin_estimand": False,
            "portfolio_evaluated": False,
        },
        "design": {
            "origin_ids": [spec.origin_id for spec in result.origins],
            "origin_years": [spec.year for spec in result.origins],
            "common_issue_months": ["April", "May", "June"],
            "common_followup_months_after_issue_quarter_end": COMMON_FOLLOWUP_MONTHS,
            "charged_off_reporting_lag_months": CHARGED_OFF_LAG_MONTHS,
            "relative_cutoffs": {spec.origin_id: spec.evaluation_cutoff for spec in result.origins},
            "learner": LEARNER,
            "taxonomy_groups": CANONICAL_GROUPS,
            "windows_per_origin": EXPECTED_WINDOWS_PER_ORIGIN,
            "nominal_coverage": NOMINAL_COVERAGE,
        },
        "origin_endpoint_census": result.origin_census.to_dict(orient="records"),
        "monthly_endpoint_census": result.monthly_census.to_dict(orient="records"),
        "origin_endpoint_reason_census": result.reason_census.to_dict(orient="records"),
        "monthly_endpoint_reason_census": result.monthly_reason_census.to_dict(orient="records"),
        "canonical_equal_followup_coverage": result.coverage.to_dict(orient="records"),
        "coverage_summary_by_origin": _origin_coverage_summary(result.coverage),
        "coverage_cells": int(len(result.coverage)),
        "upper_below_nominal_cells": int(
            result.coverage["coverage_upper"].lt(NOMINAL_COVERAGE).sum()
        ),
        "all_sixteen_upper_below_nominal": bool(
            result.coverage["coverage_upper"].lt(NOMINAL_COVERAGE).all()
        ),
        "selection": {"learner": None, "origin": None, "window": None, "endpoint": None},
        "source_imports": source_imports,
        "raw_archive": result.raw_descriptor,
        "implementation_provenance": _implementation(resolved_config, result.config, root),
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
            "status": "complete_equal_followup_execution_receipt",
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
    "CHARGED_OFF_LAG_MONTHS",
    "COMMON_FOLLOWUP_MONTHS",
    "COMPLETE_ENDPOINT_REASONS",
    "EXPECTED_COVERAGE_CELLS",
    "NOMINAL_COVERAGE",
    "PROTOCOL_TAG",
    "RUN_TAG",
    "OriginSpec",
    "build_endpoint_census_tables",
    "compute_equal_followup",
    "load_equal_followup_config",
    "load_raw_candidate_rows",
    "origin_specs",
    "reconstruct_origin_outcomes",
    "run_equal_followup",
    "select_origin_scores",
    "validate_common_followup_cutoff",
    "verify_origin_freeze",
)
