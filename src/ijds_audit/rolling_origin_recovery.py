"""Three-month 2016 primary-origin coverage recovery from the frozen V4 lineage."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.ijds_audit.config import load_v4_config
from src.ijds_audit.evaluation import endpoint_resolution_audit, temporal_coverage_audit
from src.ijds_audit.protocol import (
    configured_archive_outcomes,
    load_outcome_universe,
    load_recipes,
    verified_freeze_artifact_paths,
)
from src.utils.isolated_experiment import (
    environment_provenance,
    implementation_provenance,
    prepare_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_isolated_run_dir,
    resolve_repo_input,
)
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_parquet

ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")

RUN_TAG = "ijds-rolling-origin-primary-recovery-2026-07-21-v1"
PROTOCOL_TAG = "protocol/ijds-rolling-origin-primary-recovery-2026-07-21-v1"
SOURCE_RUN_TAG = "ijds-binary-geometry-frontier-v4-2026-07-12-v1"
SOURCE_PROTOCOL_TAG = "protocol/ijds-binary-geometry-frontier-v4-2026-07-12-v1"
SOURCE_PROTOCOL_COMMIT = "2f8a7606e4eb65aa3ae3701fb3af8d9a51c953cd"
SOURCE_FREEZE_SHA256 = "c2b3dc2d18c9fed80708682d5a0369c80c89643e2d28024418522d954ebe667c"
RAW_ARCHIVE_SHA256 = "5878af2a088f8ab5214c9337289fb8b5eb6c6338fd3f417b6cdc18513dc6f35f"

PRIMARY_PERIODS = ("2016-04", "2016-05", "2016-06")
EXPECTED_MONTHLY_CENSUS = {
    "2016-04": (28_106, 28_071, 35),
    "2016-05": (21_831, 21_803, 28),
    "2016-06": (24_600, 24_569, 31),
}
EXPECTED_CENSUS = (74_537, 74_443, 94)
EXPECTED_REASON_CENSUS = {
    "fully_paid_by_reconstructed_cutoff": 62_498,
    "charged_off_by_reconstructed_cutoff": 11_945,
    "terminal_availability_date_missing": 94,
}
FORBIDDEN_FULL_PRIMARY_ROWS = 376_890
CANONICAL_GROUPS = 5
EXPECTED_WINDOWS = 8

OUTCOME_COLUMNS = frozenset(
    {
        "loan_status",
        "snapshot_default",
        "snapshot_resolution",
        "terminal_default",
        "terminal_outcome",
        "label_available",
        "label_available_at",
        "total_pymnt",
    }
)


@dataclass(frozen=True)
class PrimaryOriginRecovery:
    """Validated in-memory result before any new lineage artifact is written."""

    config: dict[str, Any]
    source_freeze: dict[str, Any]
    source_freeze_descriptor: dict[str, Any]
    source_artifacts: dict[str, dict[str, Any]]
    raw_archive_descriptor: dict[str, Any]
    coverage: pd.DataFrame
    endpoint_audit: pd.DataFrame
    monthly_census: pd.DataFrame


def validate_primary_horizon_identity(
    *, candidate_rows: int, observed_periods: Sequence[str]
) -> None:
    """Reject the historical full horizon and require the locked three-month identity."""
    periods = tuple(sorted(set(map(str, observed_periods))))
    rows = int(candidate_rows)
    if rows == FORBIDDEN_FULL_PRIMARY_ROWS or len(periods) == 15:
        raise RuntimeError(
            "The historical 376,890-row/15-month primary horizon is forbidden in the "
            "rolling-origin recurrence comparison."
        )
    if periods != PRIMARY_PERIODS:
        raise RuntimeError(
            f"Primary-origin recovery periods changed: observed={periods}, "
            f"expected={PRIMARY_PERIODS}."
        )
    if rows != EXPECTED_CENSUS[0]:
        raise RuntimeError(
            f"Primary-origin recovery candidate census changed: {rows} != {EXPECTED_CENSUS[0]}."
        )


def select_primary_origin_scores(scores: pd.DataFrame) -> pd.DataFrame:
    """Mechanically restrict the frozen V4 primary scores to April--June 2016."""
    required = {"id", "issue_d", "design_split", "pd_catboost_platt"}
    missing = sorted(required.difference(scores.columns))
    if missing:
        raise KeyError(f"Frozen score artifact is missing columns: {missing}.")
    forbidden = sorted(OUTCOME_COLUMNS.intersection(scores.columns))
    if forbidden:
        raise RuntimeError(f"Outcome columns entered the frozen score artifact: {forbidden}.")
    if bool(scores["id"].isna().any()) or bool(scores["id"].duplicated().any()):
        raise RuntimeError("Frozen score identities must be complete and unique.")

    issue_dates = pd.to_datetime(scores["issue_d"], errors="coerce")
    if bool(issue_dates.isna().any()):
        raise RuntimeError("Frozen scores contain an invalid issue date.")
    periods = issue_dates.dt.to_period("M").astype(str)
    selected = scores.loc[
        scores["design_split"].astype(str).eq("primary_oot") & periods.isin(PRIMARY_PERIODS),
        ["id", "issue_d", "design_split", "pd_catboost_platt"],
    ].copy()
    selected["id"] = selected["id"].astype("string")
    selected["design_split"] = "primary_oot"
    selected = selected.sort_values(["issue_d", "id"], kind="mergesort").reset_index(drop=True)
    selected_periods = pd.to_datetime(selected["issue_d"]).dt.to_period("M").astype(str)
    validate_primary_horizon_identity(
        candidate_rows=len(selected), observed_periods=selected_periods.unique().tolist()
    )
    observed_monthly = selected_periods.value_counts().sort_index().to_dict()
    expected_monthly = {month: counts[0] for month, counts in EXPECTED_MONTHLY_CENSUS.items()}
    if observed_monthly != expected_monthly:
        raise RuntimeError(
            f"Frozen score monthly census changed: {observed_monthly} != {expected_monthly}."
        )
    return selected


def _monthly_endpoint_census(outcomes: pd.DataFrame) -> pd.DataFrame:
    selected = outcomes.copy()
    selected["resolved"] = selected["snapshot_default"].notna()
    monthly = (
        selected.groupby("period", observed=True, sort=True)
        .agg(candidate_rows=("id", "size"), resolved_rows=("resolved", "sum"))
        .reset_index()
    )
    monthly["resolved_rows"] = monthly["resolved_rows"].astype("int64")
    monthly["unresolved_rows"] = monthly["candidate_rows"] - monthly["resolved_rows"]
    observed = {
        str(row.period): (
            int(row.candidate_rows),
            int(row.resolved_rows),
            int(row.unresolved_rows),
        )
        for row in monthly.itertuples(index=False)
    }
    if observed != EXPECTED_MONTHLY_CENSUS:
        raise RuntimeError(
            f"Primary-origin endpoint monthly census changed: {observed} "
            f"!= {EXPECTED_MONTHLY_CENSUS}."
        )
    return monthly


def _validate_endpoint_census(outcomes: pd.DataFrame, endpoint_audit: pd.DataFrame) -> pd.DataFrame:
    periods = tuple(sorted(outcomes["period"].astype(str).unique()))
    validate_primary_horizon_identity(candidate_rows=len(outcomes), observed_periods=periods)
    resolved = int(outcomes["snapshot_default"].notna().sum())
    observed_census = (len(outcomes), resolved, len(outcomes) - resolved)
    if observed_census != EXPECTED_CENSUS:
        raise RuntimeError(
            f"Primary-origin endpoint census changed: {observed_census} != {EXPECTED_CENSUS}."
        )
    reasons = {
        str(row.snapshot_resolution): int(row.candidate_rows)
        for row in endpoint_audit.itertuples(index=False)
    }
    if reasons != EXPECTED_REASON_CENSUS:
        raise RuntimeError(
            f"Primary-origin endpoint reason census changed: {reasons} != {EXPECTED_REASON_CENSUS}."
        )
    return _monthly_endpoint_census(outcomes)


def _verify_source_freeze(
    config: Mapping[str, Any], *, repo_root: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path]]:
    resume = config.get("resume_outcome_free")
    expected_resume = {
        "source_run_tag": SOURCE_RUN_TAG,
        "source_protocol_tag": SOURCE_PROTOCOL_TAG,
        "source_protocol_commit": SOURCE_PROTOCOL_COMMIT,
        "source_freeze_sha256": SOURCE_FREEZE_SHA256,
    }
    if resume != expected_resume:
        raise RuntimeError("The 2016 recovery no longer imports the exact V4-v1 freeze.")
    model_dir = resolve_isolated_run_dir(
        repo_root=repo_root,
        configured_root=str(config["output"]["model_root"]),
        allowed_relative_root=ALLOWED_MODEL_ROOT,
        run_tag=SOURCE_RUN_TAG,
    )
    freeze_path = model_dir / "protocol_freeze.json"
    descriptor = relative_artifact_descriptor(freeze_path, repo_root=repo_root)
    if descriptor["sha256"] != SOURCE_FREEZE_SHA256:
        raise RuntimeError("The imported V4-v1 protocol freeze digest changed.")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    expected_fields = {
        "status": "outcome_free_allocations_frozen_before_archive_outcome_join",
        "run_tag": SOURCE_RUN_TAG,
        "protocol_tag": SOURCE_PROTOCOL_TAG,
        "protocol_commit": SOURCE_PROTOCOL_COMMIT,
    }
    for field, expected in expected_fields.items():
        if freeze.get(field) != expected:
            raise RuntimeError(f"Imported V4-v1 freeze mismatch for {field}.")
    if freeze.get("outcome_columns_passed_to_policy_or_comparator") != []:
        raise RuntimeError("The imported V4-v1 freeze reports outcome leakage.")
    artifacts = verified_freeze_artifact_paths(freeze, repo_root=repo_root)
    required_artifacts = {"scores", "recipes", "fit_audit"}
    missing = sorted(required_artifacts.difference(artifacts))
    if missing:
        raise RuntimeError(f"Imported V4-v1 freeze lacks recovery artifacts: {missing}.")
    return freeze, descriptor, artifacts


def _validate_config(config: Mapping[str, Any]) -> None:
    if config.get("run_tag") != RUN_TAG or config.get("protocol_tag") != PROTOCOL_TAG:
        raise RuntimeError("Unexpected primary-origin recovery run or protocol identity.")
    rolling = config.get("rolling_origin", {})
    if (
        int(rolling.get("origin_year", -1)) != 2016
        or int(rolling.get("common_primary_months", -1)) != 3
        or rolling.get("outcome_based_origin_selection") is not False
        or rolling.get("pooled_origin_claims") is not False
    ):
        raise RuntimeError("The primary-origin recovery rolling contract changed.")
    design = config["design"]
    declared = tuple(
        pd.period_range(
            str(design["primary_oot_start_month"]),
            str(design["primary_oot_end_month"]),
            freq="M",
        ).astype(str)
    )
    if declared != PRIMARY_PERIODS:
        raise RuntimeError(f"Configured primary-origin horizon changed: {declared}.")
    if config.get("endpoint_reason_recovery") is not None:
        raise RuntimeError("The horizon recovery cannot inherit the V5 reason-only replay mode.")


def compute_primary_origin_recovery(*, config_path: Path, repo_root: Path) -> PrimaryOriginRecovery:
    """Compute and validate the recovery in memory without writing outputs."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_v4_config(resolved_config)
    _validate_config(config)
    freeze, freeze_descriptor, artifact_paths = _verify_source_freeze(config, repo_root=root)

    scores = pd.read_parquet(artifact_paths["scores"])
    selected_scores = select_primary_origin_scores(scores)
    raw_path = resolve_repo_input(config["source"]["raw_path"], repo_root=root)
    universe = load_outcome_universe(config, raw_path=raw_path)
    all_outcomes = configured_archive_outcomes(universe, config)
    outcomes = all_outcomes.loc[
        all_outcomes["role"].astype(str).eq("primary_oot")
        & all_outcomes["period"].astype(str).isin(PRIMARY_PERIODS)
    ].copy()
    endpoint_audit = endpoint_resolution_audit(outcomes, roles=("primary_oot",))
    monthly_census = _validate_endpoint_census(outcomes, endpoint_audit)

    recipes = load_recipes(artifact_paths["recipes"])
    if set(recipes) != {"catboost_platt", "numeric_logistic_platt"}:
        raise RuntimeError("The frozen V4-v1 learner recipe family changed.")
    primary_recipes = {"catboost_platt": recipes["catboost_platt"]}
    if len(primary_recipes["catboost_platt"]) != EXPECTED_WINDOWS:
        raise RuntimeError("The frozen CatBoost recipe family no longer contains eight windows.")
    fit_audit = pd.read_parquet(artifact_paths["fit_audit"])
    coverage = (
        temporal_coverage_audit(
            selected_scores,
            outcomes,
            primary_recipes,
            fit_audit,
            roles=("primary_oot",),
            taxonomy_group_counts=(CANONICAL_GROUPS,),
            strata=(-1,),
        )
        .sort_values("window_id", kind="mergesort")
        .reset_index(drop=True)
    )
    if (
        len(coverage) != EXPECTED_WINDOWS
        or coverage["window_id"].nunique() != EXPECTED_WINDOWS
        or not coverage["learner"].eq("catboost_platt").all()
        or not coverage["taxonomy_groups"].eq(CANONICAL_GROUPS).all()
        or not coverage["role"].eq("primary_oot").all()
        or not coverage["conformal_group"].eq(-1).all()
    ):
        raise RuntimeError("The recovered coverage grid is not the locked 8-cell family.")
    census_columns = ("candidate_rows", "resolved_rows", "unresolved_rows")
    expected_values = dict(zip(census_columns, EXPECTED_CENSUS, strict=True))
    for column, expected in expected_values.items():
        if not coverage[column].eq(expected).all():
            raise RuntimeError(f"Recovered coverage {column} does not reconcile to {expected}.")
    bounded_columns = ("coverage_resolved", "coverage_lower", "coverage_upper", "mean_width")
    if (
        bool(coverage.loc[:, list(bounded_columns)].isna().any().any())
        or not coverage.loc[:, list(bounded_columns)].ge(0.0).all().all()
        or not coverage.loc[:, list(bounded_columns)].le(1.0).all().all()
    ):
        raise RuntimeError("Recovered coverage contains a nonfinite or out-of-range value.")
    if not coverage["coverage_lower"].le(coverage["coverage_upper"]).all():
        raise RuntimeError("Recovered sharp coverage bounds are inverted.")

    source_artifacts = {
        name: relative_artifact_descriptor(artifact_paths[name], repo_root=root)
        for name in ("scores", "recipes", "fit_audit")
    }
    raw_archive_descriptor = relative_artifact_descriptor(raw_path, repo_root=root)
    if raw_archive_descriptor["sha256"] != RAW_ARCHIVE_SHA256:
        raise RuntimeError("The predeclared raw archive digest changed.")
    return PrimaryOriginRecovery(
        config=config,
        source_freeze=freeze,
        source_freeze_descriptor=freeze_descriptor,
        source_artifacts=source_artifacts,
        raw_archive_descriptor=raw_archive_descriptor,
        coverage=coverage,
        endpoint_audit=endpoint_audit,
        monthly_census=monthly_census,
    )


def _implementation(config_path: Path, repo_root: Path) -> dict[str, Any]:
    config = load_v4_config(config_path)
    return implementation_provenance(
        config_path=config_path,
        repo_root=repo_root,
        relative_paths=[
            Path("scripts/experiments/run_ijds_rolling_origin_primary_recovery.py"),
            Path("src/ijds_audit/rolling_origin_recovery.py"),
            Path("src/ijds_audit/config.py"),
            Path("src/ijds_audit/protocol.py"),
            Path("src/ijds_audit/evaluation.py"),
            Path("src/ijds_audit/geometry.py"),
            Path("src/data/outcome_observability.py"),
            Path("src/models/binary_conformal_guardrail.py"),
            Path("src/evaluation/coverage_transport.py"),
            *[Path(value) for value in config.get("protocol_lineage_files", [])],
        ],
    )


def run_primary_origin_recovery(*, config_path: Path, repo_root: Path) -> Path:
    """Require the protocol tag, compute once, and write fresh immutable artifacts."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_v4_config(resolved_config)
    _validate_config(config)
    protocol_commit = require_clean_tagged_head(root, PROTOCOL_TAG)
    result = compute_primary_origin_recovery(config_path=resolved_config, repo_root=root)
    paths = prepare_output_paths(
        result.config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    artifacts = {
        "primary_2016_temporal_coverage": atomic_write_parquet(
            result.coverage,
            paths.data_dir / "evaluation/primary_2016_temporal_coverage.parquet",
        ),
        "primary_2016_endpoint_resolution_audit": atomic_write_parquet(
            result.endpoint_audit,
            paths.data_dir / "evaluation/primary_2016_endpoint_resolution_audit.parquet",
        ),
        "primary_2016_monthly_endpoint_census": atomic_write_parquet(
            result.monthly_census,
            paths.data_dir / "evaluation/primary_2016_monthly_endpoint_census.parquet",
        ),
    }
    nominal = 1.0 - float(result.config["conformal"]["alpha"])
    summary = {
        "schema_version": str(result.config["schema_version"]),
        "status": "complete_retrospective_primary_origin_horizon_recovery",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": protocol_commit,
        "claim_boundary": {
            "previously_inspected_archive": True,
            "confirmatory": False,
            "prospective": False,
            "independent_replication": False,
            "temporal_invariance": False,
            "selected_set_validity": False,
            "model_or_window_selection": False,
        },
        "recovery_defect": "primary_2016_full_15_month_horizon_compared_with_2017_three_month_horizon",
        "primary_horizon": {
            "origin_year": 2016,
            "periods": list(PRIMARY_PERIODS),
            "candidate_rows": EXPECTED_CENSUS[0],
            "resolved_rows": EXPECTED_CENSUS[1],
            "unresolved_rows": EXPECTED_CENSUS[2],
            "historical_full_primary_rows_rejected": FORBIDDEN_FULL_PRIMARY_ROWS,
            "historical_full_primary_months_rejected": 15,
        },
        "monthly_endpoint_census": result.monthly_census.to_dict(orient="records"),
        "endpoint_resolution_audit": result.endpoint_audit.to_dict(orient="records"),
        "canonical_primary_oot_coverage": result.coverage.to_dict(orient="records"),
        "all_eight_upper_below_nominal": bool(result.coverage["coverage_upper"].lt(nominal).all()),
        "coverage_upper_max": float(result.coverage["coverage_upper"].max()),
        "nominal_coverage": nominal,
        "source_imports": {
            "outcome_free_freeze": result.source_freeze_descriptor,
            "artifacts": result.source_artifacts,
            "raw_archive": result.raw_archive_descriptor,
            "outcome_columns_passed_to_fitting_or_selection": [],
        },
        "implementation_provenance": _implementation(resolved_config, root),
        "artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in artifacts.items()
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
            "schema_version": str(result.config["schema_version"]),
            "status": "complete_horizon_recovery_execution_receipt",
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
