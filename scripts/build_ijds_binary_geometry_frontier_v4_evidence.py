"""Build the single paper-facing IJDS V4 evidence package."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from loguru import logger
from matplotlib.colors import (
    BoundaryNorm,
    LinearSegmentedColormap,
    ListedColormap,
    SymLogNorm,
    TwoSlopeNorm,
)
from matplotlib.ticker import FixedFormatter, FixedLocator

from src.ijds_audit.binary_phase_census_evidence import (
    binary_phase_census_publication_table,
    load_binary_phase_census_evidence,
)
from src.ijds_audit.calibrator_sensitivity_evidence import (
    CalibratorSensitivityEvidence,
    calibrator_method_publication_table,
    calibrator_overall_publication_table,
    calibrator_pairwise_publication_table,
    load_calibrator_sensitivity_evidence,
)
from src.ijds_audit.claim_ledger import materialize_claim_ledger
from src.ijds_audit.config import load_v4_config
from src.ijds_audit.decision_representation_evidence import (
    dual_coefficient_publication_table,
    load_decision_representation_evidence,
    score_equivalence_publication_table,
    set_native_direction_publication_table,
)
from src.ijds_audit.frontier_evidence import load_frontier_evidence
from src.ijds_audit.grid_contracts import (
    require_exact_grid,
    require_finite,
    require_unique_row,
    require_unique_value,
)
from src.ijds_audit.publication_generation import (
    promote_publication_generation,
    publication_implementation_descriptors,
    require_historical_git_blob_descriptor,
    staged_artifact_descriptor,
    staged_output_path,
)
from src.ijds_audit.publication_schemas import (
    S6B_PUBLICATION_COLUMNS,
    S6B_QUARANTINED_COLUMNS,
    S6B_RETIRED_COLUMNS,
)
from src.ijds_audit.publication_sources import load_verified_source_registry
from src.ijds_audit.robustness_evidence import (
    allocation_granularity_publication_table,
    fit_label_completion_publication_table,
    load_allocation_granularity_evidence,
    load_fit_label_completion_evidence,
)
from src.ijds_audit.sensitivity_evidence import (
    endpoint_publication_table,
    load_endpoint_sensitivity_evidence,
)
from src.ijds_audit.structural_evidence import (
    load_structural_sensitivity_evidence,
    structural_publication_table,
)
from src.utils.artifact_descriptor import relative_artifact_descriptor
from src.utils.pipeline_runtime import atomic_write_strict_json, atomic_write_text

plt.switch_backend("Agg")

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
    "calibrator_fit_diagnostics": (
        TABLE_DIR / "crpto_ijds_v4_tableS2C_calibrator_fit_diagnostics.csv"
    ),
    "woe_iv_psi": TABLE_DIR / "crpto_ijds_v4_tableS3_woe_iv_psi.csv",
    "score_psi": TABLE_DIR / "crpto_ijds_v4_tableS4_score_psi.csv",
    "label_lag_sensitivity": TABLE_DIR / "crpto_ijds_v4_tableS5_label_lag_sensitivity.csv",
    "endpoint_availability_sensitivity": (
        TABLE_DIR / "crpto_ijds_v4_tableS6_endpoint_availability_sensitivity.csv"
    ),
    "portfolio_structure_sensitivity": (
        TABLE_DIR / "crpto_ijds_v4_tableS7_portfolio_structure_sensitivity.csv"
    ),
    "endpoint_resolution": TABLE_DIR / "crpto_ijds_v4_tableS8_endpoint_resolution.csv",
    "missingness_encoding": (
        TABLE_DIR / "crpto_ijds_v4_tableS9_missingness_encoding_sensitivity.csv"
    ),
    "rolling_origin": TABLE_DIR / "crpto_ijds_v4_tableS7C_rolling_origin_recurrence.csv",
    "conformal_set_diagnostics": (
        TABLE_DIR / "crpto_ijds_v4_tableS6A_conformal_set_diagnostics.csv"
    ),
    "exchangeability_cells": (TABLE_DIR / "crpto_ijds_v4_tableS6B_exchangeability_cells.csv"),
    "exchangeability_strata": (TABLE_DIR / "crpto_ijds_v4_tableS6C_exchangeability_strata.csv"),
    "label_mondrian_cells": (TABLE_DIR / "crpto_ijds_v4_tableS6D_label_mondrian_cells.csv"),
    "label_mondrian_strata": (TABLE_DIR / "crpto_ijds_v4_tableS6E_label_mondrian_strata.csv"),
    "label_mondrian_categories": (
        TABLE_DIR / "crpto_ijds_v4_tableS6F_label_mondrian_categories.csv"
    ),
    "taxonomy_diagnostics": (TABLE_DIR / "crpto_ijds_v4_tableS6G_taxonomy_diagnostics.csv"),
    "censored_extension_coverage": (
        TABLE_DIR / "crpto_ijds_v4_tableS6H_censored_extension_coverage.csv"
    ),
    "rolling_individual_age_census": (
        TABLE_DIR / "crpto_ijds_v4_tableS7D_individual_age_endpoint_census.csv"
    ),
    "fit_label_completion": (TABLE_DIR / "crpto_ijds_v4_tableS11_fit_label_completion.csv"),
    "allocation_granularity": (TABLE_DIR / "crpto_ijds_v4_tableS12_allocation_granularity.csv"),
    "common_panel_threshold_response_strata": (
        TABLE_DIR / "crpto_ijds_v4_tableS6J_common_panel_threshold_response_strata.csv"
    ),
    "common_panel_threshold_response_learners": (
        TABLE_DIR / "crpto_ijds_v4_tableS6K_common_panel_threshold_response_learners.csv"
    ),
    "residual_transport_summary": (
        TABLE_DIR / "crpto_ijds_v4_tableS6L_residual_transport_summary.csv"
    ),
    "residual_transport_pooled": (
        TABLE_DIR / "crpto_ijds_v4_tableS6M_residual_transport_pooled.csv"
    ),
    "marginal_score_outcome_gap": (
        TABLE_DIR / "crpto_ijds_v4_tableS6N_marginal_score_outcome_gap.csv"
    ),
    "calibrator_sensitivity_cells": (
        TABLE_DIR / "crpto_ijds_v4_tableS6O_calibrator_sensitivity_cells.csv"
    ),
    "calibrator_pairwise_shared_completion": (
        TABLE_DIR / "crpto_ijds_v4_tableS6P_calibrator_pairwise_shared_completion.csv"
    ),
    "decision_catalog_metric_separation": (
        TABLE_DIR / "crpto_ijds_v4_tableS9G_decision_catalog_metric_separation.csv"
    ),
    "decision_catalog_target_blocks": (
        TABLE_DIR / "crpto_ijds_v4_tableS9H_decision_catalog_target_blocks.csv"
    ),
    "funded_selection_track_estimands": (
        TABLE_DIR / "crpto_ijds_v4_tableS9I_funded_selection_track_estimands.csv"
    ),
    "funded_selection_gamma_contrasts": (
        TABLE_DIR / "crpto_ijds_v4_tableS9J_funded_selection_gamma_contrasts.csv"
    ),
    "set_preserving_embedding_allocation_summary": (
        TABLE_DIR / "crpto_ijds_v4_tableS9K_set_preserving_embedding_allocation_summary.csv"
    ),
    "set_preserving_embedding_direction_census": (
        TABLE_DIR / "crpto_ijds_v4_tableS9L_set_preserving_embedding_direction_census.csv"
    ),
    "score_equivalence_complete_hull": (
        TABLE_DIR / "crpto_ijds_v4_tableS9M_score_equivalence_complete_hull.csv"
    ),
    "set_native_robust_minus_embedding": (
        TABLE_DIR / "crpto_ijds_v4_tableS9N_set_native_robust_minus_embedding.csv"
    ),
    "binary_phase_census": (TABLE_DIR / "crpto_ijds_v4_tableS6I_binary_phase_census.csv"),
    "dual_coefficient_binary_set_native": (
        TABLE_DIR / "crpto_ijds_v4_tableS9O_dual_coefficient_binary_set_native.csv"
    ),
}
FIGURE_STEMS = {
    "coverage": "crpto_ijds_v4_fig1_coverage",
    "phase_transition": "crpto_ijds_v4_fig2_phase_transition",
    "development_envelopes": "crpto_ijds_v4_fig3_envelopes",
    "common_panel_threshold_response": "crpto_ijds_v4_fig4_common_panel_threshold_response",
    "common_panel_threshold_response_census": (
        "crpto_ijds_v4_figS1_common_panel_threshold_response_census"
    ),
}

CALIBRATOR_SOURCE_KEYS = (
    "calibrator_sensitivity_freeze_config",
    "calibrator_sensitivity_evaluation_config",
    "calibrator_sensitivity_protocol",
    "calibrator_sensitivity_evaluation_lock",
    "calibrator_sensitivity_runner",
    "calibrator_sensitivity_implementation",
    "calibrator_sensitivity_protocol_runner",
    "calibrator_sensitivity_source_freeze",
    "calibrator_sensitivity_source_receipt",
    "calibrator_sensitivity_calibrator_family",
    "calibrator_sensitivity_taxonomy",
    "calibrator_sensitivity_residual_recipes",
    "calibrator_sensitivity_calibration_fit_diagnostics",
    "calibrator_sensitivity_recipe_audit",
    "calibrator_sensitivity_outcome_free_geometry",
    "calibrator_sensitivity_evaluation_summary",
    "calibrator_sensitivity_evaluation_receipt",
    "calibrator_sensitivity_evaluation",
    "calibrator_sensitivity_overall",
    "calibrator_sensitivity_pairwise",
    "calibrator_sensitivity_platt_v5_reconciliation",
)
CALIBRATOR_METHODS = ("platt", "isotonic", "beta", "venn_abers")

DECISION_REPRESENTATION_SOURCE_KEYS = (
    "score_equivalence_config",
    "score_equivalence_protocol",
    "score_equivalence_runner",
    "score_equivalence_implementation",
    "score_equivalence_hulls",
    "score_equivalence_v1d",
    "score_equivalence_calibrators",
    "score_equivalence_controls",
    "score_equivalence_summary",
    "score_equivalence_receipt",
    "set_native_phase_a_config",
    "set_native_phase_b_config",
    "set_native_phase_b_blocked_template",
    "set_native_protocol",
    "set_native_runner",
    "set_native_implementation",
    "set_native_phase_a_solve_records",
    "set_native_phase_a_allocations",
    "set_native_phase_a_taxonomy",
    "set_native_phase_a_solver_audit",
    "set_native_phase_a_freeze",
    "set_native_phase_a_summary",
    "set_native_phase_a_receipt",
    "set_native_phase_a_manifest",
    "set_native_evaluated_portfolios",
    "set_native_monthly_contrasts",
    "set_native_window_contrasts",
    "set_native_evaluation_summary",
    "set_native_evaluation_receipt",
    "set_native_evaluation_manifest",
    "dual_coefficient_config",
    "dual_coefficient_protocol",
    "dual_coefficient_runner",
    "dual_coefficient_implementation",
    "dual_coefficient_certificates",
    "dual_coefficient_receipt",
    "dual_coefficient_summary",
    "dual_coefficient_freeze",
    "dual_coefficient_manifest",
)

BINARY_PHASE_CENSUS_SOURCE_KEYS = (
    "binary_phase_census_config",
    "binary_phase_census_protocol",
    "binary_phase_census_runner",
    "binary_phase_census_implementation",
    "binary_phase_census_table",
    "binary_phase_census_summary",
    "binary_phase_census_receipt",
)

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
CREDIT_LEARNER_SHORT_LABELS = {
    "catboost_platt": "CatBoost",
    "numeric_logistic_platt": "Logistic",
    "catboost_monotonic_platt": "Monotonic CB",
    "woe_scorecard_platform_platt": "Platform WOE",
    "woe_scorecard_borrower_platt": "Pricing-excl. WOE",
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
ROLLING_WINDOW_IDS = (
    "w01_2013m01_m06",
    "w02_2013m02_m07",
    "w03_2013m03_m08",
    "w04_2013m04_m09",
    "w05_2013m05_m10",
    "w06_2013m06_m11",
    "w07_2013m07_m12",
    "w08_2013m08_2014m01",
)
WINDOW_ORDINALS = tuple(f"W{index}" for index in range(1, 9))
PRIMARY_ROLLING_PERIODS = ("2016-04", "2016-05", "2016-06")
LATER_ROLLING_PERIODS = ("2017-04", "2017-05", "2017-06")
PRIMARY_ROLLING_CENSUS = (74537, 74443, 94)
LATER_ROLLING_CENSUS = (77105, 66091, 11014)
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
EXPECTED_TWO_RULER_COUNTS = {
    "evaluated_portfolios": 6240,
    "joined_funded_rows": 622455,
    "window_endpoint_contrasts": 48,
    "monthly_endpoint_contrasts": 720,
    "metric_direction_cells": 144,
    "outcome_audit_rows": 8,
}
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


def _require_machine_tolerance_recovery(
    recovery: Mapping[str, Any] | None,
    *,
    label: str,
) -> dict[str, float]:
    """Validate a V5 reason-only recovery and return its observed drift maxima."""
    if not isinstance(recovery, Mapping):
        raise RuntimeError(f"{label} omits the endpoint-recovery audit.")
    if recovery.get("status") != "reference_column_equivalence_verified_with_float_tolerance":
        raise RuntimeError(f"{label} endpoint-recovery status changed.")
    equivalence = recovery.get("equivalence")
    if (
        not isinstance(equivalence, Mapping)
        or equivalence.get("non_float_columns_exact") is not True
    ):
        raise RuntimeError(f"{label} does not retain exact non-floating equivalence.")
    float_atol = float(equivalence.get("float_atol", -1.0))
    float_rtol = float(equivalence.get("float_rtol", -1.0))
    if not (0.0 <= float_atol <= 1.0e-12 and 0.0 <= float_rtol <= 1.0e-12):
        raise RuntimeError(f"{label} float tolerances exceed the publication ceiling.")
    frames = recovery.get("frames")
    if not isinstance(frames, Mapping) or not frames:
        raise RuntimeError(f"{label} endpoint recovery has no reconciled frames.")
    maximum_absolute = 0.0
    maximum_relative = 0.0
    for frame_name, raw_frame in frames.items():
        if not isinstance(raw_frame, Mapping):
            raise TypeError(f"{label} recovery frame {frame_name!r} must be a mapping.")
        drift = raw_frame.get("float_drift")
        if not isinstance(drift, Mapping):
            raise RuntimeError(f"{label} recovery frame {frame_name!r} omits float drift.")
        for column, raw_values in drift.items():
            if not isinstance(raw_values, Mapping):
                raise TypeError(
                    f"{label} drift record {frame_name!r}/{column!r} must be a mapping."
                )
            absolute = float(raw_values.get("maximum_absolute", float("nan")))
            relative = float(raw_values.get("maximum_relative", float("nan")))
            if not np.isfinite(absolute) or not np.isfinite(relative):
                raise RuntimeError(f"{label} endpoint-recovery drift is not finite.")
            if absolute < 0.0 or relative < 0.0 or absolute > 1.0e-12 or relative > 1.0e-12:
                raise RuntimeError(f"{label} endpoint-recovery drift exceeds machine scale.")
            maximum_absolute = max(maximum_absolute, absolute)
            maximum_relative = max(maximum_relative, relative)
    return {
        "float_atol": float_atol,
        "float_rtol": float_rtol,
        "maximum_absolute_drift": maximum_absolute,
        "maximum_relative_drift": maximum_relative,
    }


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{label} must contain a JSON object.")
    return payload


def _verified_artifact_paths(
    descriptors: Mapping[str, Mapping[str, Any]],
) -> dict[str, Path]:
    return {name: _verified_path(descriptor) for name, descriptor in descriptors.items()}


def _require_clean_execution(payload: Mapping[str, Any], *, label: str) -> None:
    if (
        payload.get("protected_stages_run") != []
        or payload.get("protected_artifacts_written") != []
    ):
        raise RuntimeError(f"{label} reports a protected-stage side effect.")


@dataclass(frozen=True)
class V4Inputs:
    config_path: Path
    summary_path: Path
    receipt_path: Path
    config: dict[str, Any]
    summary: dict[str, Any]
    recovery: dict[str, float]
    artifacts: dict[str, Path]
    freeze_path: Path
    source_freeze_path: Path
    source_artifacts: dict[str, Path]


def _load_v4_inputs(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
) -> V4Inputs:
    config_path = registered["v4_config"]
    summary_path = registered["v4_summary"]
    receipt_path = registered["v4_receipt"]
    config = load_v4_config(config_path)
    summary = _read_json(summary_path, label="V4 summary")
    if summary.get("status") != "complete_retrospective_binary_geometry_frontier_audit":
        raise RuntimeError("V4 deterministic summary is incomplete.")
    _require_identity(summary, lineage["evaluation"], label="V4 evaluation")
    recovery = _require_machine_tolerance_recovery(
        summary.get("endpoint_reason_recovery"),
        label="V4 evaluation",
    )
    receipt = _read_json(receipt_path, label="V4 execution receipt")
    if receipt.get("protocol_commit") != lineage["evaluation"]["protocol_commit"]:
        raise RuntimeError("V4 receipt protocol commit changed.")
    if receipt.get("summary") != relative_artifact_descriptor(summary_path, repo_root=ROOT):
        raise RuntimeError("V4 receipt no longer binds the registered summary.")
    artifacts = _verified_artifact_paths(summary["artifacts"])
    freeze_path = _verified_path(summary["outcome_free_freeze"])
    freeze = _read_json(freeze_path, label="V4 outcome-free freeze")
    _require_identity(
        freeze["outcome_free_lineage"],
        lineage["outcome_free"],
        label="V4 outcome-free freeze",
    )
    source_freeze = freeze["outcome_free_lineage"]["source_protocol_freeze"]
    source_freeze_path = _verified_path(source_freeze)
    if source_freeze["sha256"] != lineage["outcome_free"]["freeze_sha256"]:
        raise RuntimeError("V4 outcome-free freeze hash changed.")
    return V4Inputs(
        config_path=config_path,
        summary_path=summary_path,
        receipt_path=receipt_path,
        config=config,
        summary=summary,
        recovery=recovery,
        artifacts=artifacts,
        freeze_path=freeze_path,
        source_freeze_path=source_freeze_path,
        source_artifacts=_verified_artifact_paths(freeze["outcome_free_artifacts"]),
    )


@dataclass(frozen=True)
class TwoRulerInputs:
    manifest_path: Path
    freeze_path: Path
    summary_path: Path
    receipt_path: Path
    source_artifacts: dict[str, Path]
    evaluation_artifacts: dict[str, Path]
    summary: dict[str, Any]
    recovery: dict[str, float]


def _load_two_ruler_inputs(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
) -> TwoRulerInputs:
    manifest_path = registered["two_ruler_manifest"]
    manifest = _read_json(manifest_path, label="Two-ruler manifest")
    if manifest.get("status") != "verified_post_freeze_outcome_evaluation_complete":
        raise RuntimeError("The verified two-ruler evaluation is incomplete.")
    _require_identity(manifest, lineage["evaluation"], label="Two-ruler evaluation")
    freeze_path = _verified_path(manifest["source_frontier_freeze"])
    freeze = _read_json(freeze_path, label="Two-ruler outcome-free freeze")
    _require_identity(freeze, lineage["outcome_free"], label="Two-ruler outcome-free freeze")
    if manifest["source_frontier_freeze"]["sha256"] != lineage["outcome_free"]["freeze_sha256"]:
        raise RuntimeError("Two-ruler outcome-free freeze hash changed.")
    if any(value is not None for value in manifest["selection"].values()):
        raise RuntimeError("The active manifest reports a selected two-ruler result.")
    _require_clean_execution(manifest, label="The active two-ruler manifest")
    summary_path = _verified_path(manifest["summary"])
    receipt_path = _verified_path(manifest["execution_receipt"])
    summary = _read_json(summary_path, label="Two-ruler summary")
    if summary.get("counts") != EXPECTED_TWO_RULER_COUNTS:
        raise RuntimeError("The active two-ruler evaluation census changed.")
    recovery = _require_machine_tolerance_recovery(
        summary.get("endpoint_reason_recovery"),
        label="Two-ruler evaluation",
    )
    return TwoRulerInputs(
        manifest_path=manifest_path,
        freeze_path=freeze_path,
        summary_path=summary_path,
        receipt_path=receipt_path,
        source_artifacts=_verified_artifact_paths(manifest["source_artifacts"]),
        evaluation_artifacts=_verified_artifact_paths(manifest["evaluation_artifacts"]),
        summary=summary,
        recovery=recovery,
    )


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
                "payoff_identification_width_usd_min": float(
                    frame["realized_payoff_identification_width"].min()
                ),
                "payoff_identification_width_usd_max": float(
                    frame["realized_payoff_identification_width"].max()
                ),
                "default_bound_pp_lower_min": float(
                    100.0 * frame["weighted_default_difference_lower"].min()
                ),
                "default_bound_pp_upper_max": float(
                    100.0 * frame["weighted_default_difference_upper"].max()
                ),
                "default_identification_width_pp_min": float(
                    100.0 * frame["weighted_default_identification_width"].min()
                ),
                "default_identification_width_pp_max": float(
                    100.0 * frame["weighted_default_identification_width"].max()
                ),
                "miscoverage_bound_pp_lower_min": float(
                    100.0 * frame["weighted_miscoverage_difference_lower"].min()
                ),
                "miscoverage_bound_pp_upper_max": float(
                    100.0 * frame["weighted_miscoverage_difference_upper"].max()
                ),
                "miscoverage_identification_width_pp_min": float(
                    100.0 * frame["weighted_miscoverage_identification_width"].min()
                ),
                "miscoverage_identification_width_pp_max": float(
                    100.0 * frame["weighted_miscoverage_identification_width"].max()
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


def _integer_coverage_hits(frame: pd.DataFrame, *, label: str) -> pd.Series:
    """Recover and validate the integer resolved-hit numerator in every row."""
    resolved = frame["resolved_rows"].to_numpy(dtype=float)
    if bool(np.any(resolved <= 0.0)):
        raise RuntimeError(f"{label} contains a nonpositive resolved denominator.")
    raw_hits = frame["coverage_resolved"].to_numpy(dtype=float) * resolved
    rounded_hits = np.rint(raw_hits)
    if not bool(np.allclose(raw_hits, rounded_hits, rtol=0.0, atol=1.0e-8)):
        raise RuntimeError(f"{label} does not imply integer resolved-hit numerators.")
    return pd.Series(rounded_hits.astype(np.int64), index=frame.index, dtype="int64")


def _integer_sharp_numerator(
    frame: pd.DataFrame,
    *,
    column: str,
    label: str,
) -> pd.Series:
    """Recover one integer all-candidate numerator from a sharp coverage rate."""
    raw = frame[column].to_numpy(dtype=float) * frame["candidate_rows"].to_numpy(dtype=float)
    rounded = np.rint(raw)
    if not bool(np.allclose(raw, rounded, rtol=0.0, atol=1.0e-8)):
        raise RuntimeError(f"{label} does not imply integer {column} numerators.")
    return pd.Series(rounded.astype(np.int64), index=frame.index, dtype="int64")


def _require_coverage_contract(
    frame: pd.DataFrame,
    *,
    label: str,
    constant_within: tuple[str, ...],
    expected_counts: tuple[int, int, int] | None = None,
) -> None:
    """Fail closed on counts, exact sharp arithmetic, and probability bounds."""
    count_columns = ("candidate_rows", "resolved_rows", "unresolved_rows")
    counts = frame.loc[:, count_columns].to_numpy(dtype=float)
    if bool(np.any(counts < 0.0)) or not bool(np.equal(counts, np.round(counts)).all()):
        raise RuntimeError(f"{label} contains a negative or nonintegral count.")
    if not bool(
        frame["resolved_rows"].add(frame["unresolved_rows"]).eq(frame["candidate_rows"]).all()
    ):
        raise RuntimeError(f"{label} does not partition candidates into resolved/unresolved rows.")
    for column in ("coverage_resolved", "coverage_lower", "coverage_upper"):
        if not bool(frame[column].between(0.0, 1.0, inclusive="both").all()):
            raise RuntimeError(f"{label} has {column} outside [0, 1].")
    if not bool(frame["coverage_lower"].le(frame["coverage_upper"]).all()):
        raise RuntimeError(f"{label} has a lower coverage bound above its upper bound.")
    hits = _integer_coverage_hits(frame, label=label)
    lower_hits = _integer_sharp_numerator(frame, column="coverage_lower", label=label)
    upper_hits = _integer_sharp_numerator(frame, column="coverage_upper", label=label)
    candidate = frame["candidate_rows"].to_numpy(dtype=float)
    resolved = frame["resolved_rows"].to_numpy(dtype=float)
    unresolved = frame["unresolved_rows"].to_numpy(dtype=float)
    if bool(np.any(candidate <= 0.0)):
        raise RuntimeError(f"{label} contains a nonpositive candidate denominator.")
    hit_values = hits.to_numpy(dtype=float)
    lower_values = lower_hits.to_numpy(dtype=float)
    upper_values = upper_hits.to_numpy(dtype=float)
    if bool(
        np.any(lower_values < hit_values)
        or np.any(upper_values < lower_values)
        or np.any(upper_values > hit_values + unresolved)
    ):
        raise RuntimeError(f"{label} has infeasible sharp completion numerators.")
    for column, expected in (
        ("coverage_resolved", hit_values / resolved),
        ("coverage_lower", lower_values / candidate),
        ("coverage_upper", upper_values / candidate),
    ):
        if not bool(
            np.allclose(
                frame[column].to_numpy(dtype=float),
                expected,
                rtol=0.0,
                atol=1.0e-12,
            )
        ):
            raise RuntimeError(f"{label} has {column} inconsistent with its exact counts.")
    if expected_counts is not None:
        expected = np.asarray(expected_counts, dtype=float)
        if expected.shape != (3,) or not bool(np.equal(counts, expected).all()):
            raise RuntimeError(f"{label} changed its locked global candidate census.")
    denominator_variation = frame.groupby(list(constant_within), observed=True)[
        list(count_columns)
    ].nunique()
    if bool(np.any(denominator_variation.to_numpy(dtype=int) > 1)):
        raise RuntimeError(
            f"{label} changes its candidate denominators within a declared cell family."
        )


def _require_coverage_aggregate_reconciliation(
    frame: pd.DataFrame,
    *,
    label: str,
    expected_counts: tuple[int, int, int],
) -> None:
    """Require each aggregate coverage row to equal the sum of its frozen strata."""
    count_columns = ("candidate_rows", "resolved_rows", "unresolved_rows")
    counts = frame.loc[:, count_columns].to_numpy(dtype=float)
    if bool(np.any(counts < 0.0)) or not bool(np.equal(counts, np.round(counts)).all()):
        raise RuntimeError(f"{label} contains a negative or nonintegral count.")
    if not bool(
        frame["resolved_rows"].add(frame["unresolved_rows"]).eq(frame["candidate_rows"]).all()
    ):
        raise RuntimeError(f"{label} does not partition candidates into resolved/unresolved rows.")
    for column in ("coverage_resolved", "coverage_lower", "coverage_upper"):
        if not bool(frame[column].between(0.0, 1.0, inclusive="both").all()):
            raise RuntimeError(f"{label} has {column} outside [0, 1].")
    hits = _integer_coverage_hits(frame, label=label)
    lower_hits = _integer_sharp_numerator(frame, column="coverage_lower", label=label)
    upper_hits = _integer_sharp_numerator(frame, column="coverage_upper", label=label)
    candidate = frame["candidate_rows"].to_numpy(dtype=float)
    resolved = frame["resolved_rows"].to_numpy(dtype=float)
    unresolved = frame["unresolved_rows"].to_numpy(dtype=float)
    if bool(np.any(candidate <= 0.0)):
        raise RuntimeError(f"{label} contains a nonpositive candidate denominator.")
    hit_values = hits.to_numpy(dtype=float)
    lower_values = lower_hits.to_numpy(dtype=float)
    upper_values = upper_hits.to_numpy(dtype=float)
    if bool(
        np.any(lower_values < hit_values)
        or np.any(upper_values < lower_values)
        or np.any(upper_values > hit_values + unresolved)
    ):
        raise RuntimeError(f"{label} has infeasible sharp completion numerators.")
    for column, expected in (
        ("coverage_resolved", hit_values / resolved),
        ("coverage_lower", lower_values / candidate),
        ("coverage_upper", upper_values / candidate),
    ):
        if not bool(
            np.allclose(
                frame[column].to_numpy(dtype=float),
                expected,
                rtol=0.0,
                atol=1.0e-12,
            )
        ):
            raise RuntimeError(f"{label} has {column} inconsistent with its exact counts.")
    work = frame.assign(
        _resolved_hits=hits,
        _lower_hits=lower_hits,
        _upper_hits=upper_hits,
    )
    cell_columns = ("learner", "taxonomy_groups", "role", "window_id")
    for cell_key, cell in work.groupby(list(cell_columns), observed=True, sort=False):
        aggregate = cell.loc[cell["conformal_group"].eq(-1)]
        strata = cell.loc[cell["conformal_group"].ge(0)]
        if len(aggregate) != 1:
            raise RuntimeError(f"{label} has no unique aggregate row for {cell_key}.")
        taxonomy_groups = int(aggregate["taxonomy_groups"].iloc[0])
        actual_groups = set(strata["conformal_group"].astype(int))
        if actual_groups != set(range(taxonomy_groups)) or len(strata) != taxonomy_groups:
            raise RuntimeError(f"{label} has an incomplete frozen stratum grid for {cell_key}.")
        aggregate_counts = aggregate.loc[:, list(count_columns)].iloc[0].to_numpy(dtype=np.int64)
        if not bool(np.equal(aggregate_counts, np.asarray(expected_counts, dtype=np.int64)).all()):
            raise RuntimeError(f"{label} changed its locked global candidate census.")
        stratum_counts = strata.loc[:, list(count_columns)].sum().to_numpy(dtype=np.int64)
        if not bool(np.equal(aggregate_counts, stratum_counts).all()):
            raise RuntimeError(f"{label} aggregate counts do not reconcile to frozen strata.")
        for numerator in ("_resolved_hits", "_lower_hits", "_upper_hits"):
            aggregate_hits = int(aggregate[numerator].iloc[0])
            if aggregate_hits != int(strata[numerator].sum()):
                raise RuntimeError(
                    f"{label} aggregate coverage hits do not reconcile to frozen strata."
                )


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


def _closed_coverage_diagnostic_tables(
    temporal_coverage: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Summarize every locked V4 taxonomy and the declared censored extension."""
    learners = ("catboost_platt", "numeric_logistic_platt")
    taxonomies = (1, 2, 5, 10)
    primary_all_groups = temporal_coverage.loc[
        temporal_coverage["learner"].isin(learners)
        & temporal_coverage["taxonomy_groups"].isin(taxonomies)
        & temporal_coverage["role"].eq("primary_oot")
    ].copy()
    primary = primary_all_groups.loc[primary_all_groups["conformal_group"].eq(-1)].copy()
    require_exact_grid(
        primary,
        domains={
            "learner": learners,
            "taxonomy_groups": taxonomies,
            "window_id": WINDOW_IDS,
        },
        label="closed V4 taxonomy diagnostics",
    )
    require_finite(
        primary,
        (
            "candidate_rows",
            "resolved_rows",
            "unresolved_rows",
            "coverage_resolved",
            "coverage_lower",
            "coverage_upper",
        ),
        label="closed V4 taxonomy diagnostics",
    )
    _require_coverage_contract(
        primary,
        label="closed V4 taxonomy diagnostics",
        constant_within=("learner", "taxonomy_groups"),
        expected_counts=(376_890, 364_814, 12_076),
    )
    _require_coverage_aggregate_reconciliation(
        primary_all_groups,
        label="closed V4 taxonomy diagnostics",
        expected_counts=(376_890, 364_814, 12_076),
    )
    learner_order = {learner: index for index, learner in enumerate(learners)}
    primary.insert(1, "learner_label", primary["learner"].map(CREDIT_LEARNER_LABELS))
    primary["_learner_order"] = primary["learner"].map(learner_order)
    primary = primary.sort_values(
        ["_learner_order", "taxonomy_groups", "window_id"], kind="mergesort"
    ).drop(columns="_learner_order")
    taxonomy_table = primary[
        [
            "learner",
            "learner_label",
            "taxonomy_groups",
            "role",
            "conformal_group",
            "window_id",
            "candidate_rows",
            "resolved_rows",
            "unresolved_rows",
            "coverage_resolved",
            "coverage_lower",
            "coverage_upper",
        ]
    ].copy()
    taxonomy_rows: list[dict[str, Any]] = []
    for learner in learners:
        for taxonomy in taxonomies:
            frame = primary.loc[
                primary["learner"].eq(learner) & primary["taxonomy_groups"].eq(taxonomy)
            ]
            taxonomy_rows.append(
                {
                    "learner": learner,
                    "learner_label": CREDIT_LEARNER_LABELS[learner],
                    "taxonomy_groups": taxonomy,
                    "windows": int(len(frame)),
                    "candidate_rows": int(frame["candidate_rows"].iloc[0]),
                    "resolved_rows": int(frame["resolved_rows"].iloc[0]),
                    "unresolved_rows": int(frame["unresolved_rows"].iloc[0]),
                    "coverage_lower_min": float(frame["coverage_lower"].min()),
                    "coverage_upper_max": float(frame["coverage_upper"].max()),
                    "windows_upper_below_0_90": int(frame["coverage_upper"].lt(0.90).sum()),
                }
            )
    taxonomy_summary = pd.DataFrame(taxonomy_rows)

    extension_all_groups = temporal_coverage.loc[
        temporal_coverage["learner"].isin(learners)
        & temporal_coverage["taxonomy_groups"].eq(5)
        & temporal_coverage["role"].eq("censored_extension")
    ].copy()
    extension = extension_all_groups.loc[extension_all_groups["conformal_group"].eq(-1)].copy()
    require_exact_grid(
        extension,
        domains={"learner": learners, "window_id": WINDOW_IDS},
        label="declared censored-extension coverage",
    )
    require_finite(
        extension,
        (
            "candidate_rows",
            "resolved_rows",
            "unresolved_rows",
            "coverage_resolved",
            "coverage_lower",
            "coverage_upper",
        ),
        label="declared censored-extension coverage",
    )
    _require_coverage_contract(
        extension,
        label="declared censored-extension coverage",
        constant_within=("learner",),
        expected_counts=(88_227, 59_291, 28_936),
    )
    _require_coverage_aggregate_reconciliation(
        extension_all_groups,
        label="declared censored-extension coverage",
        expected_counts=(88_227, 59_291, 28_936),
    )
    extension.insert(1, "learner_label", extension["learner"].map(CREDIT_LEARNER_LABELS))
    extension["_learner_order"] = extension["learner"].map(learner_order)
    extension = extension.sort_values(["_learner_order", "window_id"]).drop(
        columns="_learner_order"
    )
    extension_table = extension[
        [
            "learner",
            "learner_label",
            "taxonomy_groups",
            "role",
            "conformal_group",
            "window_id",
            "candidate_rows",
            "resolved_rows",
            "unresolved_rows",
            "coverage_lower",
            "coverage_upper",
        ]
    ].copy()
    return {
        "taxonomy_diagnostics": taxonomy_table,
        "taxonomy_summary": taxonomy_summary,
        "censored_extension_coverage": extension_table,
    }


@dataclass(frozen=True)
class CreditInputs:
    summary_path: Path
    receipt_path: Path
    summary: dict[str, Any]
    recovery: dict[str, float]
    freeze_path: Path
    freeze: dict[str, Any]
    evaluation_artifacts: dict[str, Path]
    outcome_free_artifacts: dict[str, Path]
    model_artifacts: dict[str, Path]
    prediction_metrics: pd.DataFrame
    temporal_coverage: pd.DataFrame
    woe_summary: pd.DataFrame
    feature_psi: pd.DataFrame
    score_psi: pd.DataFrame
    feature_variation: pd.DataFrame
    tables: dict[str, pd.DataFrame]


def _load_credit_inputs(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
) -> CreditInputs:
    summary_path = registered["credit_summary"]
    receipt_path = registered["credit_receipt"]
    summary = _read_json(summary_path, label="Credit-control summary")
    if summary.get("status") != "complete_no_model_selection_credit_risk_control_evaluation":
        raise RuntimeError("The verified credit-control evaluation is incomplete.")
    receipt = _read_json(receipt_path, label="Credit-control execution receipt")
    _require_identity(receipt, lineage["evaluation"], label="Credit-control evaluation")
    expected_interpretation = {
        "model_or_feature_selected_from_oot": False,
        "portfolio_claim_authorized": False,
        "scorecard_superiority_claim_authorized": False,
        "universal_transport_claim_authorized": False,
    }
    if summary.get("interpretation") != expected_interpretation:
        raise RuntimeError("The active credit-control claim boundary changed.")
    _require_clean_execution(summary, label="The active credit controls")
    if summary.get("coverage_recovery") is not None:
        raise RuntimeError("Credit controls unexpectedly report a coverage-recovery block.")
    recovery = _require_machine_tolerance_recovery(
        summary.get("endpoint_reason_recovery"),
        label="Credit-control evaluation",
    )
    freeze_path = _verified_path(summary["source_freeze"])
    freeze = _read_json(freeze_path, label="Credit-control outcome-free freeze")
    if freeze.get("status") != "credit_control_scores_frozen_before_primary_oot_outcome_join":
        raise RuntimeError("The V1b credit-control freeze is incomplete.")
    _require_identity(freeze, lineage["outcome_free"], label="Credit-control outcome-free freeze")
    if summary["source_freeze"]["sha256"] != lineage["outcome_free"]["freeze_sha256"]:
        raise RuntimeError("Credit-control outcome-free freeze hash changed.")
    if freeze.get("co_primary_learners") != list(CREDIT_LEARNER_ORDER):
        raise RuntimeError("The frozen five-model specification changed.")
    if (
        freeze.get("model_selection") != "none_all_five_reported"
        or freeze.get("window_selection") != "none_all_eight_reported"
        or freeze.get("portfolio_optimization") is not False
        or freeze.get("sampling") != "none_all_eligible_rows"
        or freeze.get("primary_oot_outcome_columns_in_frozen_scores") != []
    ):
        raise RuntimeError("The frozen credit-control selection boundary changed.")
    evaluation_artifacts = _verified_artifact_paths(summary["evaluation_artifacts"])
    outcome_free_artifacts = _verified_artifact_paths(freeze["outcome_free_artifacts"])
    model_artifacts = _verified_artifact_paths(freeze["model_artifacts"])
    prediction_metrics = pd.read_parquet(evaluation_artifacts["prediction_metrics"])
    temporal_coverage = pd.read_parquet(evaluation_artifacts["temporal_coverage"])
    woe_summary = pd.read_parquet(outcome_free_artifacts["woe_summary"])
    feature_psi = pd.read_parquet(outcome_free_artifacts["scorecard_feature_psi"])
    score_psi = pd.read_parquet(outcome_free_artifacts["score_psi"])
    feature_variation = pd.read_parquet(outcome_free_artifacts["feature_variation"])
    return CreditInputs(
        summary_path=summary_path,
        receipt_path=receipt_path,
        summary=summary,
        recovery=recovery,
        freeze_path=freeze_path,
        freeze=freeze,
        evaluation_artifacts=evaluation_artifacts,
        outcome_free_artifacts=outcome_free_artifacts,
        model_artifacts=model_artifacts,
        prediction_metrics=prediction_metrics,
        temporal_coverage=temporal_coverage,
        woe_summary=woe_summary,
        feature_psi=feature_psi,
        score_psi=score_psi,
        feature_variation=feature_variation,
        tables=_credit_control_tables(
            prediction_metrics,
            temporal_coverage,
            woe_summary,
            feature_psi,
            score_psi,
        ),
    )


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


def _coverage_figure(
    coverage: pd.DataFrame,
    exchangeability_cells: pd.DataFrame,
    *,
    output_dir: Path,
) -> dict[str, Path]:
    _style()
    canonical = coverage.loc[
        coverage["taxonomy_groups"].eq(5)
        & coverage["role"].eq("primary_oot")
        & coverage["conformal_group"].eq(-1)
    ].copy()
    require_exact_grid(
        canonical,
        domains={"learner": CREDIT_LEARNER_ORDER, "window_id": WINDOW_IDS},
        label="five-model coverage figure",
    )
    require_exact_grid(
        exchangeability_cells,
        domains={"learner": CREDIT_LEARNER_ORDER, "window_id": WINDOW_IDS},
        label="joint-block rank-reference threshold heatmap",
    )
    window_labels = [f"W{index}" for index in range(1, 9)]
    x = np.arange(8, dtype=float)
    figure = plt.figure(figsize=(10.8, 7.2))
    grid = figure.add_gridspec(5, 2, width_ratios=(2.9, 1.8), hspace=0.12, wspace=0.24)
    palette = (BLUE, ORANGE, "#2A9D8F", "#8E5EA2", GOLD)
    for index, (learner, color) in enumerate(zip(CREDIT_LEARNER_ORDER, palette, strict=True)):
        axis = figure.add_subplot(grid[index, 0])
        frame = canonical.loc[canonical["learner"].eq(learner)].sort_values("window_id")
        lower = frame["coverage_lower"].to_numpy(dtype=float)
        upper = frame["coverage_upper"].to_numpy(dtype=float)
        resolved = frame["coverage_resolved"].to_numpy(dtype=float)
        axis.vlines(x, lower, upper, color=color, linewidth=2.3, alpha=0.9)
        axis.scatter(
            x,
            resolved,
            s=23,
            facecolors="white",
            edgecolors=color,
            linewidths=1.2,
            zorder=3,
        )
        axis.axhline(0.90, color=INK, linestyle="--", linewidth=0.9)
        axis.set_ylim(0.83, 0.905)
        axis.set_xlim(-0.45, 7.45)
        axis.set_ylabel(CREDIT_LEARNER_SHORT_LABELS[learner], rotation=0, ha="right", va="center")
        axis.spines[["top", "right"]].set_visible(False)
        if index == 0:
            axis.set_title(
                "A. Resolved coverage (open dots) and sharp completion bounds (segments)",
                loc="left",
            )
        if index == 4:
            axis.set_xticks(x, window_labels)
            axis.set_xlabel("Six-month residual window")
        else:
            axis.set_xticks(x, [])

    heat_axis = figure.add_subplot(grid[:, 1])
    decisions = np.zeros((5, 8), dtype=float)
    for row_index, learner in enumerate(CREDIT_LEARNER_ORDER):
        frame = exchangeability_cells.loc[exchangeability_cells["learner"].eq(learner)].sort_values(
            "window_id"
        )
        decisions[row_index, :] = frame["holm_reject_exchangeability_null"].astype(int)
    flag_cmap = ListedColormap(("#E5E7EB", "#8B1E3F"))
    heat_axis.imshow(decisions, cmap=flag_cmap, vmin=0, vmax=1, aspect="auto")
    for row_index in range(5):
        for column_index in range(8):
            flagged = bool(decisions[row_index, column_index])
            heat_axis.text(
                column_index,
                row_index,
                "F" if flagged else "NF",
                ha="center",
                va="center",
                color="white" if flagged else INK,
                fontsize=8.5,
                fontweight="bold",
            )
    heat_axis.set_xticks(x, window_labels)
    heat_axis.set_yticks(
        np.arange(5),
        [CREDIT_LEARNER_SHORT_LABELS[learner] for learner in CREDIT_LEARNER_ORDER],
    )
    heat_axis.set_xlabel("Six-month residual window")
    heat_axis.set_title("B. Cells meeting locked nominal reporting thresholds", loc="left")
    heat_axis.tick_params(length=0)
    figure.suptitle(
        "Finite-archive coverage and joint-block rank-reference flags",
        y=0.995,
        fontsize=12,
        fontweight="bold",
    )
    figure.text(
        0.01,
        0.006,
        "Focused coverage scale. Bounds are sharp completion intervals, not sampling intervals; "
        "F/NF denotes meets/does not meet the locked nominal Bonferroni--Holm thresholds. "
        "The post-inspection family has no selective-FWER claim.",
        fontsize=7.8,
        color=MID,
    )
    figure.subplots_adjust(left=0.13, right=0.98, top=0.93, bottom=0.09)
    return _save_figure(figure, FIGURE_STEMS["coverage"], output_dir=output_dir)


def _phase_transition_publication_table(
    phase: pd.DataFrame,
    *,
    alpha: float,
) -> pd.DataFrame:
    """Add the exact finite-sample phase coordinate to the S3 path."""
    if not np.isfinite(alpha) or not 0.0 < alpha < 1.0:
        raise ValueError("The phase-transition alpha must lie strictly between zero and one.")
    columns = [
        "window_id",
        "fit_rows",
        "fit_prevalence",
        "fit_score_min",
        "fit_score_max",
        "score_min",
        "score_max",
        "fit_residual_quantile",
        "coverage_lower",
        "coverage_upper",
        "mean_width",
        "set_empty_share",
        "set_zero_only_share",
        "set_both_share",
    ]
    missing = sorted(set(columns).difference(phase.columns))
    if missing:
        raise KeyError(f"The phase-transition source omits columns: {missing}.")
    table = phase.loc[:, columns].copy()
    require_finite(
        table,
        tuple(column for column in columns if column != "window_id"),
        label="phase-transition publication table",
    )

    fit_rows_float = table["fit_rows"].to_numpy(dtype=float)
    fit_rows = np.rint(fit_rows_float).astype(np.int64)
    if (fit_rows <= 0).any() or not np.array_equal(fit_rows_float, fit_rows.astype(float)):
        raise RuntimeError("The phase-transition fit-row counts are not positive integers.")
    prevalence = table["fit_prevalence"].to_numpy(dtype=float)
    if ((prevalence < 0.0) | (prevalence > 1.0)).any():
        raise RuntimeError("The phase-transition fit prevalence leaves [0, 1].")
    default_rows_float = fit_rows * prevalence
    default_rows = np.rint(default_rows_float).astype(np.int64)
    if not np.allclose(default_rows_float, default_rows, rtol=0.0, atol=1.0e-8):
        raise RuntimeError("Fit prevalence does not reconstruct an integer default count.")
    if ((default_rows < 0) | (default_rows > fit_rows)).any():
        raise RuntimeError("The reconstructed default count leaves its fit block.")
    finite_sample_rank = np.ceil((fit_rows + 1) * (1.0 - alpha)).astype(np.int64)
    if ((finite_sample_rank < 1) | (finite_sample_rank > fit_rows)).any():
        raise RuntimeError("The phase-transition finite-sample rank leaves [1, n].")
    finite_phase_allowance = fit_rows - finite_sample_rank
    phase_margin = default_rows - finite_phase_allowance
    bounded_columns = (
        "fit_score_min",
        "fit_score_max",
        "score_min",
        "score_max",
        "fit_residual_quantile",
    )
    if any(
        (
            (table[column].to_numpy(dtype=float) < 0.0)
            | (table[column].to_numpy(dtype=float) > 1.0)
        ).any()
        for column in bounded_columns
    ):
        raise RuntimeError("The phase-transition scores or threshold leave [0, 1].")
    if (table["fit_score_min"] > table["fit_score_max"]).any() or (
        table["score_min"] > table["score_max"]
    ).any():
        raise RuntimeError("The phase-transition score minima exceed their maxima.")
    calibration_scores_below_half = table["fit_score_max"].to_numpy(dtype=float) < 0.5
    if not calibration_scores_below_half.all():
        raise RuntimeError(
            "The CatBoost S3 phase path no longer satisfies the below-half calibration condition."
        )
    observed_low_regime = table["fit_residual_quantile"].to_numpy(dtype=float) < 0.5
    if not np.array_equal(observed_low_regime, phase_margin <= 0):
        raise RuntimeError("The exact phase margin no longer matches the fitted threshold regime.")

    insert_at = table.columns.get_loc("fit_prevalence") + 1
    derived = (
        ("fit_default_rows", default_rows),
        ("finite_sample_rank", finite_sample_rank),
        ("finite_phase_allowance", finite_phase_allowance),
        ("phase_margin", phase_margin),
        ("phase_boundary_rate", finite_phase_allowance / fit_rows),
        ("calibration_scores_below_half", calibration_scores_below_half),
    )
    for offset, (name, values) in enumerate(derived):
        table.insert(insert_at + offset, name, values)
    return table


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
    x = np.arange(1, len(frame) + 1, dtype=float)
    # Keep the two x axes independent.  With a shared Matplotlib axis, assigning
    # the same formatted labels to both panels can overprint one raster label
    # (observed as W3 rendered on top of W5 in the left-hand PNG).
    figure, axes = plt.subplots(1, 2, figsize=(7.2, 3.35), sharex=False)
    axes[0].plot(x, frame["fit_prevalence"], color=BLUE, marker="o", linewidth=1.5)
    axes[0].plot(
        x,
        frame["phase_boundary_rate"],
        color=ORANGE,
        linestyle="--",
        linewidth=1.3,
        label=r"finite boundary $(n-k)/n$",
    )
    axes[0].axhline(
        0.10,
        color=MID,
        linestyle=":",
        linewidth=1.0,
        label=r"nominal $\alpha=0.10$",
    )
    axes[0].set_ylabel("Fit default prevalence")
    axes[0].set_title("CatBoost S3 prevalence and phase boundary")
    axes[0].legend(
        loc="lower left",
        frameon=True,
        facecolor="white",
        edgecolor="none",
        framealpha=0.92,
    )
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
        axis.set_xticks(x)
        axis.set_xlabel("Window index (W)")
        axis.spines[["top", "right"]].set_visible(False)
    axes[0].annotate(
        f"W7: 0.1017; m={int(w7['phase_margin']):+d}",
        xy=(7, float(w7["fit_prevalence"])),
        xytext=(5.6, 0.111),
        arrowprops={"arrowstyle": "-", "color": MID},
        fontsize=8,
    )
    axes[0].annotate(
        f"W8: 0.0971; m={int(w8['phase_margin']):+d}",
        xy=(8, float(w8["fit_prevalence"])),
        xytext=(6.5, 0.0975),
        arrowprops={"arrowstyle": "-", "color": MID},
        fontsize=8,
    )
    axes[1].annotate(
        "0.8884 to 0.1118",
        xy=(8, float(w8["fit_residual_quantile"])),
        xytext=(4.8, 0.35),
        arrowprops={"arrowstyle": "->", "color": MID},
        fontsize=8,
    )
    figure.suptitle("Post-inspection CatBoost S3 finite-sample illustration")
    figure.tight_layout()
    return _save_figure(figure, FIGURE_STEMS["phase_transition"], output_dir=output_dir)


def _envelope_figure(envelopes: pd.DataFrame, *, output_dir: Path) -> dict[str, Path]:
    _style()
    metrics = ("standardized_payoff", "funded_miscoverage")
    direction_code = {"guardrail_lower": -1, "crosses_zero": 0, "guardrail_higher": 1}
    colors = [BLUE, "#F3F4F6", ORANGE]
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
            "Status-indexed payoff proxy"
            if metric == "standardized_payoff"
            else "Funded miscoverage"
        )
        axis.grid(False)
        for row in range(matrix.shape[0]):
            for column in range(matrix.shape[1]):
                value = int(matrix.iloc[row, column])
                axis.text(
                    column,
                    row,
                    {1: "+", 0: "×", -1: "-"}[value],
                    ha="center",
                    va="center",
                    color=INK if value == 0 else "white",
                    fontsize=8,
                    fontweight="bold",
                )
    axes[-1].set_xticks(np.arange(8), [f"W{index}" for index in range(1, 9)])
    axes[-1].set_xlabel("Residual window")
    figure.suptitle(
        "Full-upper-score minus point-score envelopes at registered development-admissible cap values"
    )
    figure.text(
        0.5,
        0.015,
        "- full-upper-score lower; × envelope contains zero; + full-upper-score higher. Default contains zero in every cell.",
        ha="center",
        fontsize=8,
        color=MID,
    )
    figure.tight_layout(rect=(0, 0.04, 1, 0.96))
    return _save_figure(figure, FIGURE_STEMS["development_envelopes"], output_dir=output_dir)


@dataclass(frozen=True)
class CommonPanelFigureData:
    """Validated common-panel values shared by the main and supplemental figures."""

    frame: pd.DataFrame
    ordered_rows: tuple[tuple[str, int], ...]
    threshold: np.ndarray
    resolved_pp: np.ndarray
    sharp_width_pp: np.ndarray
    focal: pd.Series
    exact_zero_cells: pd.DataFrame
    fixed_candidate_rows: int
    fixed_resolved_rows: int


def _prepare_common_panel_figure_data(strata: pd.DataFrame) -> CommonPanelFigureData:
    """Validate and arrange the exact 175-cell response census once."""
    require_exact_grid(
        strata,
        domains={
            "learner": CREDIT_LEARNER_ORDER,
            "pair_index": tuple(range(7)),
            "conformal_group": tuple(range(5)),
        },
        label="common-panel threshold-response figure",
    )
    numeric_columns = (
        "candidate_rows",
        "resolved_rows",
        "unresolved_rows",
        "threshold_delta",
        "resolved_delta_rate",
        "delta_lower",
        "delta_upper",
        "delta_width",
    )
    missing = sorted(set(numeric_columns).difference(strata.columns))
    if missing:
        raise RuntimeError(f"The common-panel figure is missing columns: {missing}.")
    require_finite(strata, numeric_columns, label="common-panel threshold-response figure")
    frame = strata.copy()
    counts = frame.loc[:, ["candidate_rows", "resolved_rows", "unresolved_rows"]]
    if (
        bool(np.any(counts.to_numpy(dtype=float) < 0.0))
        or not np.allclose(counts.to_numpy(dtype=float), np.rint(counts.to_numpy(dtype=float)))
        or bool(frame["candidate_rows"].le(0).any())
        or bool(frame["resolved_rows"].le(0).any())
        or not frame["resolved_rows"]
        .add(frame["unresolved_rows"])
        .eq(frame["candidate_rows"])
        .all()
    ):
        raise RuntimeError("The common-panel figure has invalid candidate denominators.")
    if (
        bool(frame["delta_lower"].gt(frame["delta_upper"]).any())
        or bool(frame["delta_width"].lt(0.0).any())
        or not np.allclose(
            frame["delta_upper"].sub(frame["delta_lower"]).to_numpy(dtype=float),
            frame["delta_width"].to_numpy(dtype=float),
            rtol=1e-9,
            atol=1e-12,
        )
    ):
        raise RuntimeError("The common-panel sharp-response bounds are inconsistent.")

    totals = (
        frame.groupby(["learner", "pair_index"], observed=True)[
            ["candidate_rows", "resolved_rows", "unresolved_rows"]
        ]
        .sum()
        .reset_index(drop=True)
    )
    if any(totals[column].nunique(dropna=False) != 1 for column in totals.columns):
        raise RuntimeError("The common-panel fixed-panel denominators changed across contrasts.")
    fixed_candidate_rows = int(totals["candidate_rows"].iloc[0])
    fixed_resolved_rows = int(totals["resolved_rows"].iloc[0])

    learner_rank = {learner: rank for rank, learner in enumerate(CREDIT_LEARNER_ORDER)}
    frame["_learner_rank"] = frame["learner"].map(learner_rank)
    frame = frame.sort_values(["_learner_rank", "conformal_group", "pair_index"]).drop(
        columns="_learner_rank"
    )
    ordered_rows = tuple((learner, group) for learner in CREDIT_LEARNER_ORDER for group in range(5))
    threshold = np.empty((len(ordered_rows), 7), dtype=float)
    response = np.empty_like(threshold)
    sharp_width = np.empty_like(threshold)
    for row_index, (learner, group) in enumerate(ordered_rows):
        cell_frame = frame.loc[
            frame["learner"].eq(learner) & frame["conformal_group"].eq(group)
        ].sort_values("pair_index")
        threshold[row_index, :] = cell_frame["threshold_delta"].to_numpy(dtype=float)
        response[row_index, :] = 100.0 * cell_frame["resolved_delta_rate"].to_numpy(dtype=float)
        sharp_width[row_index, :] = 100.0 * cell_frame["delta_width"].to_numpy(dtype=float)
    if (
        not np.isfinite(threshold).all()
        or not np.isfinite(response).all()
        or not np.isfinite(sharp_width).all()
        or np.any(sharp_width < 0.0)
    ):
        raise RuntimeError("The common-panel figure contains invalid arranged values.")
    focal = require_unique_row(
        frame,
        key={"learner": "catboost_platt", "conformal_group": 2, "pair_index": 6},
        label="previously disclosed common-panel illustration",
    )
    exact_zero_cells = frame.loc[
        frame["resolved_delta_rate"].eq(0.0)
        & frame["delta_lower"].eq(0.0)
        & frame["delta_upper"].eq(0.0)
    ].copy()
    if len(exact_zero_cells) != 5:
        raise RuntimeError("The common-panel five-cell exact-zero census changed.")
    return CommonPanelFigureData(
        frame=frame,
        ordered_rows=ordered_rows,
        threshold=threshold,
        resolved_pp=response,
        sharp_width_pp=sharp_width,
        focal=focal,
        exact_zero_cells=exact_zero_cells,
        fixed_candidate_rows=fixed_candidate_rows,
        fixed_resolved_rows=fixed_resolved_rows,
    )


def _common_panel_threshold_response_figure(
    strata: pd.DataFrame, *, output_dir: Path
) -> dict[str, Path]:
    """Plot detached resolved and all-candidate responses for all 175 cells."""
    _style()
    data = _prepare_common_panel_figure_data(strata)
    frame = data.frame.assign(
        resolved_pp=100.0 * data.frame["resolved_delta_rate"],
        lower_pp=100.0 * data.frame["delta_lower"],
        upper_pp=100.0 * data.frame["delta_upper"],
    )
    if frame["threshold_delta"].min() < -1.08 or frame["threshold_delta"].max() > 0.00225:
        raise RuntimeError("The common-panel threshold axis would clip a census cell.")
    focal_mask = (
        frame["learner"].eq("catboost_platt")
        & frame["conformal_group"].eq(2)
        & frame["pair_index"].eq(6)
    )
    zero_mask = frame.index.isin(data.exact_zero_cells.index)
    context = frame.loc[~focal_mask & ~zero_mask]
    focal = frame.loc[focal_mask].iloc[0]
    zero_positions = frame.loc[zero_mask, "threshold_delta"].value_counts().sort_index()

    figure, axes = plt.subplots(2, 1, figsize=(6.6, 8.4), sharex=True, sharey=True)
    y_abs = float(
        np.max(np.abs(frame.loc[:, ["resolved_pp", "lower_pp", "upper_pp"]].to_numpy(dtype=float)))
    )
    y_limit = max(0.5, np.ceil((y_abs + 0.05) * 2.0) / 2.0)
    for axis in axes:
        axis.set_xscale("symlog", linthresh=1e-5, linscale=0.8, base=10)
        axis.set_xlim(-1.08, 0.00225)
        axis.set_ylim(-y_limit, y_limit)
        axis.grid(False)
        axis.grid(axis="y", color=LIGHT, linewidth=0.7, alpha=0.8)
        axis.axhline(0.0, color=INK, linewidth=0.9, zorder=0)
        axis.axvline(0.0, color=INK, linewidth=0.9, zorder=0)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
    resolved_axis, bounds_axis = axes
    resolved_axis.scatter(
        context["threshold_delta"],
        context["resolved_pp"],
        s=22,
        facecolor="white",
        edgecolor=BLUE,
        linewidth=0.9,
        alpha=0.84,
        zorder=2,
    )
    resolved_axis.scatter(
        [float(focal["threshold_delta"])],
        [float(focal["resolved_pp"])],
        marker="D",
        s=66,
        facecolor=ORANGE,
        edgecolor=INK,
        linewidth=1.0,
        zorder=5,
    )
    bounds_axis.vlines(
        context["threshold_delta"],
        context["lower_pp"],
        context["upper_pp"],
        color=BLUE,
        alpha=0.52,
        linewidth=0.95,
        zorder=1,
    )
    for endpoint in ("lower_pp", "upper_pp"):
        bounds_axis.scatter(
            context["threshold_delta"],
            context[endpoint],
            marker="_",
            s=24,
            color=BLUE,
            linewidth=0.8,
            alpha=0.68,
            zorder=2,
        )
    bounds_axis.vlines(
        float(focal["threshold_delta"]),
        float(focal["lower_pp"]),
        float(focal["upper_pp"]),
        color=ORANGE,
        linewidth=2.2,
        zorder=4,
    )
    bounds_axis.scatter(
        [float(focal["threshold_delta"]), float(focal["threshold_delta"])],
        [float(focal["lower_pp"]), float(focal["upper_pp"])],
        marker="_",
        s=55,
        color=ORANGE,
        linewidth=1.5,
        zorder=5,
    )
    for axis in axes:
        axis.scatter(
            zero_positions.index.to_numpy(dtype=float),
            np.zeros(len(zero_positions), dtype=float),
            marker="P",
            s=58,
            facecolor=INK,
            edgecolor="white",
            linewidth=0.8,
            zorder=6,
        )
    resolved_axis.annotate(
        "Post-inspection illustration\nCatBoost S3, W7\N{RIGHTWARDS ARROW}W8",
        xy=(float(focal["threshold_delta"]), float(focal["resolved_pp"])),
        xytext=(48, 76),
        textcoords="offset points",
        fontsize=8.2,
        ha="left",
        va="bottom",
        linespacing=1.2,
        arrowprops={"arrowstyle": "-", "color": ORANGE, "linewidth": 1.1},
        bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "edgecolor": "#FED7AA"},
        zorder=7,
    )
    bounds_axis.annotate(
        "5 exact [0,0] cells",
        xy=(float(zero_positions.index.max()), 0.0),
        xytext=(20, -18),
        textcoords="offset points",
        fontsize=8.1,
        ha="left",
        va="top",
        arrowprops={"arrowstyle": "-", "color": MID, "linewidth": 0.8},
        zorder=7,
    )
    resolved_axis.text(
        0.012,
        0.965,
        "A. Exact resolved-panel response",
        transform=resolved_axis.transAxes,
        ha="left",
        va="top",
        fontsize=10.2,
        fontweight="bold",
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.1},
        zorder=10,
    )
    bounds_axis.text(
        0.012,
        0.965,
        "B. Sharp all-candidate response bounds (not CIs)",
        transform=bounds_axis.transAxes,
        ha="left",
        va="top",
        fontsize=10.2,
        fontweight="bold",
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.1},
        zorder=10,
    )
    resolved_axis.set_ylabel("Resolved response (percentage points)", labelpad=9)
    bounds_axis.set_ylabel("All-candidate response (percentage points)", labelpad=9)
    bounds_axis.set_xlabel(
        "Fitted-threshold change, \N{GREEK CAPITAL LETTER DELTA}c  (symmetric-log x scale)",
        labelpad=9,
    )
    xticks = (-1.0, -0.1, -0.01, -0.001, -0.0001, 0.0, 0.0001, 0.001)
    xlabels = (
        "\N{MINUS SIGN}1",
        "\N{MINUS SIGN}0.1",
        "\N{MINUS SIGN}0.01",
        "\N{MINUS SIGN}0.001",
        "\N{MINUS SIGN}10\N{SUPERSCRIPT MINUS}\N{SUPERSCRIPT FOUR}",
        "0",
        "10\N{SUPERSCRIPT MINUS}\N{SUPERSCRIPT FOUR}",
        "0.001",
    )
    bounds_axis.xaxis.set_major_locator(FixedLocator(xticks))
    bounds_axis.xaxis.set_major_formatter(FixedFormatter(xlabels))
    resolved_axis.tick_params(labelbottom=False)
    figure.suptitle(
        "Common-panel response to adjacent thresholds",
        x=0.105,
        y=0.975,
        ha="left",
        fontsize=14.5,
        fontweight="bold",
    )
    figure.text(
        0.105,
        0.937,
        "Complete 175-cell census in both panels; different denominators are shown separately.\n"
        "One post-inspection illustration is disclosed; no fitted line, ranking, "
        "or confirmatory comparison.",
        ha="left",
        va="top",
        color=MID,
        fontsize=8.8,
        linespacing=1.3,
    )
    resolved_range = (
        int(frame["resolved_rows"].min()),
        int(frame["resolved_rows"].max()),
    )
    candidate_range = (
        int(frame["candidate_rows"].min()),
        int(frame["candidate_rows"].max()),
    )
    figure.text(
        0.105,
        0.014,
        f"The fixed panel contains {data.fixed_candidate_rows:,} candidates "
        f"({data.fixed_resolved_rows:,} resolved). Panel A uses cellwise resolved denominators "
        f"({resolved_range[0]:,}\N{EN DASH}{resolved_range[1]:,});\nPanel B uses cellwise "
        f"candidate denominators ({candidate_range[0]:,}\N{EN DASH}{candidate_range[1]:,}) and "
        "gives identification bounds, not uncertainty around Panel A.\n"
        "Sharpness is cellwise; endpoints need not be jointly attainable across contrasts.",
        ha="left",
        va="bottom",
        color=MID,
        fontsize=7.2,
        linespacing=1.22,
    )
    figure.subplots_adjust(left=0.16, right=0.965, top=0.865, bottom=0.145, hspace=0.14)
    return _save_figure(
        figure,
        FIGURE_STEMS["common_panel_threshold_response"],
        output_dir=output_dir,
    )


def _common_panel_threshold_response_census_figure(
    strata: pd.DataFrame, *, output_dir: Path
) -> dict[str, Path]:
    """Plot the full locked-order 25-by-7 census as a supplemental index."""
    _style()
    data = _prepare_common_panel_figure_data(strata)
    threshold = data.threshold
    response = data.resolved_pp
    sharp_width = data.sharp_width_pp
    diverging = LinearSegmentedColormap.from_list(
        "blue_orange", [BLUE, "#BFDBFE", "#F8FAFC", "#FED7AA", ORANGE]
    )
    sequential = LinearSegmentedColormap.from_list(
        "blue_width", ["#F8FAFC", "#BFDBFE", BLUE, "#1E3A8A"]
    )
    threshold_limit = float(np.max(np.abs(threshold)))
    response_limit = float(np.max(np.abs(response)))
    width_limit = float(np.max(sharp_width))
    if min(threshold_limit, response_limit, width_limit) <= 0.0:
        raise RuntimeError("The common-panel supplemental color scale is degenerate.")
    figure, axes = plt.subplots(1, 3, figsize=(11.0, 7.3), sharey=True)
    threshold_image = axes[0].imshow(
        threshold,
        aspect="auto",
        cmap=diverging,
        norm=SymLogNorm(
            linthresh=1.0e-6,
            linscale=0.7,
            vmin=-threshold_limit,
            vmax=threshold_limit,
            base=10,
        ),
    )
    response_image = axes[1].imshow(
        response,
        aspect="auto",
        cmap=diverging,
        norm=TwoSlopeNorm(vmin=-response_limit, vcenter=0.0, vmax=response_limit),
    )
    width_image = axes[2].imshow(
        sharp_width,
        aspect="auto",
        cmap=sequential,
        vmin=0.0,
        vmax=width_limit,
    )
    transitions = [f"W{index}\u2192W{index + 1}" for index in range(1, 8)]
    row_labels = [
        f"{CREDIT_LEARNER_SHORT_LABELS[learner]}  S{group + 1}"
        for learner, group in data.ordered_rows
    ]
    for axis in axes:
        axis.set_xticks(range(7), transitions, rotation=45, ha="right")
        axis.set_yticks(range(len(row_labels)), row_labels)
        axis.set_xticks(np.arange(-0.5, 7, 1), minor=True)
        axis.set_yticks(np.arange(-0.5, len(row_labels), 1), minor=True)
        axis.grid(False)
        axis.grid(which="minor", color="white", linewidth=0.45, alpha=0.85)
        axis.tick_params(which="minor", bottom=False, left=False)
        for boundary in (4.5, 9.5, 14.5, 19.5):
            axis.axhline(boundary, color="#111827", linewidth=0.9)
        axis.add_patch(
            plt.Rectangle(
                (5.5, 1.5),
                1.0,
                1.0,
                fill=False,
                edgecolor="#111827",
                linewidth=2.0,
            )
        )
    axes[0].set_title("A. Threshold change", loc="left")
    axes[1].set_title("B. Resolved response (pp)", loc="left")
    axes[2].set_title("C. Sharp width (pp)", loc="left")
    axes[0].set_ylabel("Learner and fixed score stratum")
    interior_threshold_ticks = (1.0e-6, 1.0e-5, 1.0e-4, 1.0e-3, 1.0e-2, 1.0e-1)
    positive_threshold_ticks = {
        threshold_limit,
        *(tick for tick in interior_threshold_ticks if tick < threshold_limit),
    }
    threshold_ticks = sorted(
        {-value for value in positive_threshold_ticks} | {0.0} | positive_threshold_ticks
    )
    threshold_colorbar = figure.colorbar(
        threshold_image,
        ax=axes[0],
        fraction=0.046,
        pad=0.04,
        label="Threshold change (symmetric log)",
        ticks=threshold_ticks,
    )
    threshold_colorbar.ax.set_yticklabels(
        [
            "0"
            if value == 0.0
            else (
                f"{value:.3g}"
                if np.isclose(abs(value), threshold_limit)
                else f"{value:.0e}".replace("e-0", "e-").replace("e+0", "e+")
            )
            for value in threshold_ticks
        ]
    )
    figure.colorbar(
        response_image,
        ax=axes[1],
        fraction=0.046,
        pad=0.04,
        label="Resolved coverage change (pp)",
    )
    figure.colorbar(
        width_image,
        ax=axes[2],
        fraction=0.046,
        pad=0.04,
        label="Identification width (pp)",
    )
    figure.suptitle("Locked-order common-panel census (supplemental index)", y=0.995)
    figure.text(
        0.5,
        0.008,
        "All 175 cells are retained. Panel A uses a symmetric-log color scale, linear within "
        f"±1e-6 and spanning ±{threshold_limit:.3f}. "
        "The outline marks the previously disclosed CatBoost S3 "
        "W7\N{RIGHTWARDS ARROW}W8 illustration; Table S6J provides exact values.",
        ha="center",
        va="bottom",
        fontsize=8.5,
    )
    figure.tight_layout(rect=(0.0, 0.03, 1.0, 0.98))
    return _save_figure(
        figure,
        FIGURE_STEMS["common_panel_threshold_response_census"],
        output_dir=output_dir,
    )


@dataclass(frozen=True)
class DiagnosticInputs:
    raw_audit_path: Path
    raw_audit: dict[str, Any]
    raw_artifacts: dict[str, Path]
    raw_coverage_exceptions: pd.DataFrame
    lag_evidence_path: Path
    lag_evidence: dict[str, Any]
    lag_table_path: Path
    lag_table: pd.DataFrame
    admissible_lag_table: pd.DataFrame
    nonadmissible_lag_table: pd.DataFrame
    lag_w7_w8: pd.DataFrame
    tie_evidence_path: Path
    policy_evidence_path: Path
    policy_evidence: dict[str, Any]


def _load_diagnostic_inputs(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
) -> DiagnosticInputs:
    raw_audit_path = registered["raw_data_audit"]
    raw_audit = _read_json(raw_audit_path, label="Raw-data audit")
    if raw_audit.get("status") != "complete_full_archive_data_contract_audit":
        raise RuntimeError("The full-archive data audit is incomplete.")
    if raw_audit.get("run_tag") != lineage["raw_data_audit"]["run_tag"]:
        raise RuntimeError("The raw-data audit identity changed.")
    _require_clean_execution(raw_audit, label="The raw-data audit")
    raw_artifacts = _verified_artifact_paths(raw_audit["artifacts"])
    raw_feature_contract = pd.read_csv(raw_artifacts["feature_contract"])
    raw_coverage_exceptions = raw_feature_contract.loc[
        raw_feature_contract["coverage_exception"].notna()
        & raw_feature_contract["requires_sensitivity"].eq(True)
    ].copy()
    if len(raw_coverage_exceptions) != 2:
        raise RuntimeError("The declared raw-feature coverage exceptions changed.")

    lag_evidence_path = registered["label_lag_sensitivity"]
    lag_evidence = _read_json(lag_evidence_path, label="Label-lag sensitivity")
    if lag_evidence.get("status") != "complete_frozen_score_label_lag_sensitivity":
        raise RuntimeError("The label-lag sensitivity is incomplete.")
    _require_identity(
        lag_evidence,
        lineage["label_lag_sensitivity"],
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
    tie_evidence = _read_json(tie_evidence_path, label="Solver-tie audit")
    if tie_evidence.get("status") != "complete_prefreeze_structural_evidence":
        raise RuntimeError("The solver-tie audit is incomplete.")
    _require_identity(tie_evidence, lineage["solver_tie_audit"], label="Solver-tie audit")
    _require_clean_execution(tie_evidence, label="The legacy solver-tie audit")

    policy_evidence_path = registered["policy_support_optimal_face_evidence"]
    policy_evidence = _read_json(
        policy_evidence_path,
        label="Policy-support optimal-face evidence",
    )
    if (
        policy_evidence.get("schema_version") != "2026-07-21.1"
        or policy_evidence.get("status")
        != "complete_outcome_free_policy_support_optimal_face_evidence"
        or policy_evidence.get("certification_status")
        != "rhs_support_coverage_recovered_numerical_uniqueness_claim_blocked"
    ):
        raise RuntimeError("The policy-support optimal-face evidence is incomplete.")
    if (
        policy_evidence.get("publication_role")
        != "registered_intermediate_source_for_single_primary_evidence_manifest"
        or policy_evidence.get("paper_facing_numeric_authority") is not False
    ):
        raise RuntimeError("The policy-support evidence publication role changed.")
    _require_clean_execution(policy_evidence, label="The policy-support optimal-face evidence")
    if policy_evidence.get("outcome_columns_passed") != []:
        raise RuntimeError("The policy-support evidence is no longer outcome-free.")
    policy_lineage = policy_evidence.get("lineage")
    if not isinstance(policy_lineage, Mapping):
        raise TypeError("The policy-support evidence lineage is not a mapping.")
    for key, registry_key in (
        ("v2", "policy_support_optimal_face_v2"),
        ("v3a", "policy_support_rhs_semantics_recovery"),
    ):
        identity = policy_lineage.get(key)
        if not isinstance(identity, Mapping):
            raise TypeError(f"The policy-support {key} identity is not a mapping.")
        _require_identity(identity, lineage[registry_key], label=f"Policy-support {key}")
    policy_results = policy_evidence.get("results")
    policy_boundary = policy_evidence.get("claim_boundary")
    if not isinstance(policy_results, Mapping) or not isinstance(policy_boundary, Mapping):
        raise TypeError("The policy-support results or claim boundary is not a mapping.")
    coverage = policy_results.get("rhs_support_coverage")
    warnings = policy_results.get("warnings_and_mobility")
    status_aware = policy_results.get("status_aware_rhs_semantics")
    frozen = policy_results.get("frozen_allocation_reconciliation")
    lateral = policy_results.get("corrected_lateral_stability")
    numerical = policy_results.get("numerical_contracts")
    if not all(
        isinstance(value, Mapping)
        for value in (coverage, warnings, status_aware, frozen, lateral, numerical)
    ):
        raise TypeError("A policy-support result contract is not a mapping.")
    coverage = cast(Mapping[str, Any], coverage)
    warnings = cast(Mapping[str, Any], warnings)
    status_aware = cast(Mapping[str, Any], status_aware)
    frozen = cast(Mapping[str, Any], frozen)
    lateral = cast(Mapping[str, Any], lateral)
    numerical = cast(Mapping[str, Any], numerical)
    numerical_passes = all(
        isinstance(contract, Mapping)
        and contract.get(
            "numerical_contract_passed",
            contract.get("row_contract_passed"),
        )
        is True
        for contract in numerical.values()
    )
    if (
        status_aware.get("status_aware_semantics_gate_passed") is not True
        or coverage.get("rhs_support_coverage_gate_passed") is not True
        or float(coverage.get("absolute_gap_tolerance", -1.0)) != 1.0e-10
        or int(coverage.get("registered_gap_seed_solves", -1)) != 196
        or int(coverage.get("upper_status_gap_seed_solves", -1)) != 196
        or int(coverage.get("basic_status_gap_seed_solves", -1)) != 0
        or int(coverage.get("strictly_interior_gap_seed_solves", -1)) != 196
        or float(coverage.get("maximum_seed_midpoint_match_distance", float("inf"))) > 1.0e-12
        or float(coverage.get("maximum_v2_seed_expected_objective_difference", float("inf")))
        > 1.0e-5
        or float(coverage.get("maximum_v2_seed_weighted_point_difference", float("inf"))) > 1.0e-10
        or int(coverage.get("status_aware_seed_cap_containment_passes", -1)) != 196
        or int(coverage.get("recomputed_target_gap_coverage_passes", -1)) != 196
        or int(coverage.get("zero_tolerance_positive_seams", -1)) != 465
        or int(coverage.get("positive_gaps_at_1e_15", -1)) != 0
        or frozen.get("frozen_allocation_reconciliation_gate_passed") is not True
        or int(frozen.get("rows", -1)) != 7_297
        or int(frozen.get("passed_rows", -1)) != 7_297
        or lateral.get("corrected_lateral_gate_passed") is not True
        or not numerical_passes
        or warnings.get("strict_numerical_uniqueness_gate_passed") is not False
        or warnings.get("epsilon_near_optimal_mobility_is_exact_alternate_optimum") is not False
        or policy_results.get("rhs_coverage_recovered_without_uniqueness_promotion") is not True
    ):
        raise RuntimeError("The bounded policy-support conclusion changed.")
    forbidden_promotions = (
        "strict_numerical_uniqueness_claim_active",
        "exact_symbolic_optimal_face_claim_active",
        "exact_nonuniqueness_claim_active",
        "global_optimal_face_diameter_claim_active",
        "continuous_joint_frontier_uniqueness_claim_active",
        "exact_continuous_outcome_envelope_over_all_optimal_allocations_claim_active",
        "allocation_continuity_or_seam_conditioning_claim_active",
    )
    if any(policy_boundary.get(field) is not False for field in forbidden_promotions):
        raise RuntimeError("The policy-support evidence promotes a forbidden inference.")
    if policy_boundary.get("epsilon_mobility_is_exact_nonuniqueness_evidence") is not False:
        raise RuntimeError("Epsilon mobility is promoted as exact nonuniqueness evidence.")
    if (
        policy_boundary.get("retrospective") is not True
        or policy_boundary.get("rhs_coverage_is_numerical_and_support_bounded") is not True
        or any(
            policy_boundary.get(field) is not False
            for field in (
                "preregistered",
                "confirmatory",
                "prospective",
                "policy_cap_or_tie_break_selected",
                "empirical_outcome_direction_claim_active",
                "selected_or_funded_set_conformal_claim_active",
            )
        )
    ):
        raise RuntimeError("The policy-support retrospective or selection boundary changed.")
    return DiagnosticInputs(
        raw_audit_path=raw_audit_path,
        raw_audit=raw_audit,
        raw_artifacts=raw_artifacts,
        raw_coverage_exceptions=raw_coverage_exceptions,
        lag_evidence_path=lag_evidence_path,
        lag_evidence=lag_evidence,
        lag_table_path=lag_table_path,
        lag_table=lag_table,
        admissible_lag_table=admissible_lag_table,
        nonadmissible_lag_table=nonadmissible_lag_table,
        lag_w7_w8=lag_w7_w8,
        tie_evidence_path=tie_evidence_path,
        policy_evidence_path=policy_evidence_path,
        policy_evidence=policy_evidence,
    )


@dataclass(frozen=True)
class RollingInputs:
    summary_path: Path
    receipt_path: Path
    freeze_path: Path
    score_path: Path
    summary: dict[str, Any]
    artifacts: dict[str, Path]
    coverage: pd.DataFrame


def _load_rolling_inputs(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
) -> RollingInputs:
    summary_path = registered["rolling_origin_summary"]
    receipt_path = registered["rolling_origin_receipt"]
    summary = _read_json(summary_path, label="Rolling-origin summary")
    if summary.get("status") != "complete_retrospective_binary_geometry_frontier_audit":
        raise RuntimeError("The rolling-origin evaluation is incomplete.")
    _require_identity(summary, lineage, label="Rolling-origin evaluation")
    receipt = _read_json(receipt_path, label="Rolling-origin execution receipt")
    if receipt.get("protocol_commit") != lineage["protocol_commit"]:
        raise RuntimeError("The rolling-origin receipt protocol commit changed.")
    if receipt.get("summary") != relative_artifact_descriptor(summary_path, repo_root=ROOT):
        raise RuntimeError("The rolling-origin receipt no longer binds its summary.")
    _require_clean_execution(summary, label="The rolling-origin run")
    if summary.get("endpoint_reason_recovery") is not None:
        raise RuntimeError("The rolling-origin run violates its fresh-run boundary.")
    freeze_path = _verified_path(summary["outcome_free_freeze"])
    freeze = _read_json(freeze_path, label="Rolling-origin outcome-free freeze")
    if (
        freeze.get("status") != "verified_outcome_free_freeze_imported_before_archive_outcome_join"
        or freeze.get("run_tag") != lineage["run_tag"]
        or freeze.get("protocol_tag") != lineage["protocol_tag"]
        or freeze.get("protocol_commit") != lineage["protocol_commit"]
    ):
        raise RuntimeError("The rolling-origin outcome-free freeze identity changed.")
    score_path = _verified_path(freeze["outcome_free_artifacts"]["scores"])
    rolling_scores = pd.read_parquet(
        score_path,
        columns=["id", "issue_d", "design_split"],
    )
    primary_scores = rolling_scores.loc[rolling_scores["design_split"].eq("primary_oot")].copy()
    periods = tuple(
        sorted(pd.to_datetime(primary_scores["issue_d"]).dt.to_period("M").astype(str).unique())
    )
    if (
        periods != LATER_ROLLING_PERIODS
        or len(primary_scores) != LATER_ROLLING_CENSUS[0]
        or primary_scores["id"].duplicated().any()
    ):
        raise RuntimeError("The 2017 rolling-origin April--June candidate horizon changed.")
    artifacts = _verified_artifact_paths(summary["artifacts"])
    coverage_all = pd.read_parquet(artifacts["temporal_coverage"])
    coverage = coverage_all.loc[
        coverage_all["learner"].eq("catboost_platt")
        & coverage_all["taxonomy_groups"].eq(5)
        & coverage_all["role"].eq("primary_oot")
        & coverage_all["conformal_group"].eq(-1)
    ].sort_values("window_id")
    require_exact_grid(
        coverage,
        domains={"window_id": ROLLING_WINDOW_IDS},
        label="rolling-origin primary coverage",
    )
    require_finite(
        coverage,
        ("candidate_rows", "resolved_rows", "unresolved_rows", "coverage_lower", "coverage_upper"),
        label="rolling-origin primary coverage",
    )
    for column, expected in zip(
        ("candidate_rows", "resolved_rows", "unresolved_rows"),
        LATER_ROLLING_CENSUS,
        strict=True,
    ):
        if not coverage[column].eq(expected).all():
            raise RuntimeError(f"The 2017 rolling-origin {column} census changed.")
    if not coverage["coverage_upper"].lt(0.90).all():
        raise RuntimeError("The complete 2017 rolling-origin coverage result changed.")
    return RollingInputs(
        summary_path=summary_path,
        receipt_path=receipt_path,
        freeze_path=freeze_path,
        score_path=score_path,
        summary=summary,
        artifacts=artifacts,
        coverage=coverage,
    )


@dataclass(frozen=True)
class RollingPrimaryRecoveryInputs:
    summary_path: Path
    receipt_path: Path
    summary: dict[str, Any]
    artifacts: dict[str, Path]
    coverage: pd.DataFrame


def _load_rolling_primary_recovery_inputs(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
) -> RollingPrimaryRecoveryInputs:
    summary_path = registered["rolling_primary_recovery_summary"]
    receipt_path = registered["rolling_primary_recovery_receipt"]
    summary = _read_json(summary_path, label="Primary rolling-origin recovery summary")
    if summary.get("status") != "complete_retrospective_primary_origin_horizon_recovery":
        raise RuntimeError("The primary rolling-origin horizon recovery is incomplete.")
    _require_identity(summary, lineage, label="Primary rolling-origin horizon recovery")
    receipt = _read_json(receipt_path, label="Primary rolling-origin recovery receipt")
    _require_identity(receipt, lineage, label="Primary rolling-origin recovery receipt")
    if receipt.get("summary") != relative_artifact_descriptor(summary_path, repo_root=ROOT):
        raise RuntimeError("The primary rolling-origin receipt no longer binds its summary.")
    _require_clean_execution(summary, label="The primary rolling-origin recovery")
    _require_clean_execution(receipt, label="The primary rolling-origin recovery receipt")

    horizon = summary.get("primary_horizon", {})
    if (
        tuple(horizon.get("periods", ())) != PRIMARY_ROLLING_PERIODS
        or tuple(
            int(horizon[field]) for field in ("candidate_rows", "resolved_rows", "unresolved_rows")
        )
        != PRIMARY_ROLLING_CENSUS
        or int(horizon.get("historical_full_primary_rows_rejected", -1)) != 376890
        or int(horizon.get("historical_full_primary_months_rejected", -1)) != 15
    ):
        raise RuntimeError("The recovered 2016 April--June rolling horizon changed.")
    monthly = pd.DataFrame(summary.get("monthly_endpoint_census", []))
    require_exact_grid(
        monthly,
        domains={"period": PRIMARY_ROLLING_PERIODS},
        label="primary rolling-origin monthly census",
    )
    if (
        tuple(monthly.sort_values("period")["candidate_rows"].astype(int)) != (28106, 21831, 24600)
        or tuple(monthly.sort_values("period")["resolved_rows"].astype(int))
        != (28071, 21803, 24569)
        or tuple(monthly.sort_values("period")["unresolved_rows"].astype(int)) != (35, 28, 31)
    ):
        raise RuntimeError("The recovered 2016 monthly endpoint census changed.")
    if summary.get("all_eight_upper_below_nominal") is not True:
        raise RuntimeError("The recovered 2016 complete coverage result changed.")

    artifacts = _verified_artifact_paths(summary["artifacts"])
    coverage = pd.read_parquet(artifacts["primary_2016_temporal_coverage"]).sort_values("window_id")
    require_exact_grid(
        coverage,
        domains={"window_id": WINDOW_IDS},
        label="recovered primary rolling-origin coverage",
    )
    require_finite(
        coverage,
        (
            "candidate_rows",
            "resolved_rows",
            "unresolved_rows",
            "coverage_resolved",
            "coverage_lower",
            "coverage_upper",
            "mean_width",
        ),
        label="recovered primary rolling-origin coverage",
    )
    for column, expected in zip(
        ("candidate_rows", "resolved_rows", "unresolved_rows"),
        PRIMARY_ROLLING_CENSUS,
        strict=True,
    ):
        if not coverage[column].eq(expected).all():
            raise RuntimeError(f"The recovered 2016 rolling-origin {column} census changed.")
    if len(coverage) != 8 or not coverage["coverage_upper"].lt(0.90).all():
        raise RuntimeError("The recovered 2016 eight-window coverage result changed.")
    if np.isclose(float(summary["coverage_upper_max"]), 0.8825970442304121):
        raise RuntimeError("The stale 15-month primary maximum entered the rolling recovery.")
    if not np.isclose(
        float(summary["coverage_upper_max"]),
        float(coverage["coverage_upper"].max()),
        atol=0.0,
        rtol=0.0,
    ):
        raise RuntimeError("The recovered 2016 maximum no longer matches its complete table.")
    return RollingPrimaryRecoveryInputs(
        summary_path=summary_path,
        receipt_path=receipt_path,
        summary=summary,
        artifacts=artifacts,
        coverage=coverage,
    )


@dataclass(frozen=True)
class ConformalSetDiagnosticInputs:
    summary_path: Path
    receipt_path: Path
    summary: dict[str, Any]
    artifacts: dict[str, Path]
    table: pd.DataFrame
    publication_table: pd.DataFrame


def _load_conformal_set_diagnostic_inputs(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
) -> ConformalSetDiagnosticInputs:
    summary_path = registered["conformal_set_diagnostics_summary"]
    receipt_path = registered["conformal_set_diagnostics_receipt"]
    summary = _read_json(summary_path, label="Conformal-set diagnostic summary")
    if summary.get("status") != "complete_retrospective_conformal_set_diagnostic":
        raise RuntimeError("The conformal-set diagnostic is incomplete.")
    _require_identity(summary, lineage, label="Conformal-set diagnostic")
    receipt = _read_json(receipt_path, label="Conformal-set diagnostic receipt")
    _require_identity(receipt, lineage, label="Conformal-set diagnostic receipt")
    if receipt.get("summary") != relative_artifact_descriptor(summary_path, repo_root=ROOT):
        raise RuntimeError("The conformal-set diagnostic receipt no longer binds its summary.")
    _require_clean_execution(summary, label="The conformal-set diagnostic")
    _require_clean_execution(receipt, label="The conformal-set diagnostic receipt")
    expected_interpretation = {
        "learner_or_window_selected": False,
        "label_conditional_guarantee": False,
        "selected_set_guarantee": False,
        "funded_set_guarantee": False,
        "latent_pd_interval": False,
    }
    if summary.get("interpretation") != expected_interpretation:
        raise RuntimeError("The conformal-set diagnostic interpretation boundary changed.")
    expected_counts = {
        "learner_window_cells": 40,
        "learners": 5,
        "windows_per_learner": 8,
        "candidate_rows": 376890,
        "resolved_rows": 364814,
        "unresolved_rows": 12076,
        "resolved_y0_rows": 307842,
        "resolved_y1_rows": 56972,
    }
    if summary.get("counts") != expected_counts:
        raise RuntimeError("The conformal-set diagnostic census changed.")
    if (
        summary.get("reference_reconciliation", {}).get("canonical_coverage_and_geometry_match")
        is not True
    ):
        raise RuntimeError("The conformal-set diagnostic no longer reconciles to active coverage.")

    artifacts = _verified_artifact_paths(summary["artifacts"])
    table = pd.read_parquet(artifacts["conformal_set_diagnostics"])
    require_exact_grid(
        table,
        domains={"learner": CREDIT_LEARNER_ORDER, "window_id": WINDOW_IDS},
        label="complete conformal-set diagnostic",
    )
    numeric = (
        "coverage_resolved",
        "coverage_resolved_y0",
        "coverage_resolved_y1",
        "average_set_size",
        "singleton_share",
        "set_empty_share",
        "set_zero_only_share",
        "set_one_only_share",
        "set_both_share",
        "mean_width",
    )
    require_finite(table, numeric, label="complete conformal-set diagnostic")
    if (
        not table["candidate_rows"].eq(376890).all()
        or not table["resolved_rows"].eq(364814).all()
        or not table["unresolved_rows"].eq(12076).all()
        or not table["resolved_y0_rows"].eq(307842).all()
        or not table["resolved_y1_rows"].eq(56972).all()
        or not table["coverage_resolved_y0"].gt(table["coverage_resolved_y1"]).all()
    ):
        raise RuntimeError("The complete resolved-label diagnostic pattern changed.")
    if not np.allclose(
        table["average_set_size"],
        1.0 - table["set_empty_share"] + table["set_both_share"],
        atol=5.0e-14,
        rtol=5.0e-14,
    ) or not np.allclose(
        table["singleton_share"],
        table["set_zero_only_share"] + table["set_one_only_share"],
        atol=5.0e-14,
        rtol=5.0e-14,
    ):
        raise RuntimeError("The conformal-set cardinality identities changed.")
    publication = table.copy()
    publication.insert(1, "learner_label", publication["learner"].map(CREDIT_LEARNER_LABELS))
    publication.insert(
        2,
        "window",
        publication["window_id"].map(dict(zip(WINDOW_IDS, WINDOW_ORDINALS, strict=True))),
    )
    return ConformalSetDiagnosticInputs(
        summary_path=summary_path,
        receipt_path=receipt_path,
        summary=summary,
        artifacts=artifacts,
        table=table,
        publication_table=publication,
    )


@dataclass(frozen=True)
class ExchangeabilityTransportInputs:
    summary_path: Path
    receipt_path: Path
    summary: dict[str, Any]
    artifacts: dict[str, Path]
    strata: pd.DataFrame
    cells: pd.DataFrame
    publication_strata: pd.DataFrame
    publication_cells: pd.DataFrame


def _load_exchangeability_transport_inputs(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
) -> ExchangeabilityTransportInputs:
    summary_path = registered["exchangeability_transport_summary"]
    receipt_path = registered["exchangeability_transport_receipt"]
    summary = _read_json(summary_path, label="Exchangeability transport summary")
    if summary.get("status") != "complete_retrospective_exchangeability_transport_test":
        raise RuntimeError("The exact exchangeability transport test is incomplete.")
    _require_identity(summary, lineage, label="Exchangeability transport test")
    receipt = _read_json(receipt_path, label="Exchangeability transport receipt")
    _require_identity(receipt, lineage, label="Exchangeability transport receipt")
    if receipt.get("summary") != relative_artifact_descriptor(summary_path, repo_root=ROOT):
        raise RuntimeError("The exchangeability receipt no longer binds its summary.")
    _require_clean_execution(summary, label="The exchangeability transport test")
    _require_clean_execution(receipt, label="The exchangeability transport receipt")
    if (
        summary.get("counts", {}).get("stratum_tests") != 200
        or summary.get("counts", {}).get("learner_window_cells") != 40
        or summary.get("results", {}).get("holm_rejected_cells") != 31
        or summary.get("multiplicity", {}).get("formal_rejection_family")
        != "forty_learner_window_intersection_nulls"
        or summary.get("interpretation", {}).get("preregistered") is not False
        or summary.get("interpretation", {}).get("confirmatory") is not False
    ):
        raise RuntimeError("The exact exchangeability result or claim boundary changed.")

    artifacts = _verified_artifact_paths(summary["artifacts"])
    strata = pd.read_parquet(artifacts["stratum_tests"])
    cells = pd.read_parquet(artifacts["learner_window_cells"])
    require_exact_grid(
        strata,
        domains={
            "learner": CREDIT_LEARNER_ORDER,
            "window_id": WINDOW_IDS,
            "conformal_group": tuple(range(5)),
        },
        label="exchangeability transport strata",
    )
    require_exact_grid(
        cells,
        domains={"learner": CREDIT_LEARNER_ORDER, "window_id": WINDOW_IDS},
        label="exchangeability transport cells",
    )
    require_finite(
        strata,
        (
            "fit_rows",
            "finite_sample_rank",
            "candidate_rows",
            "misses_min",
            "misses_max",
            "null_expected_miss_rate",
            "exact_log_p_value",
            "bonferroni_log_p_value",
        ),
        label="exchangeability transport strata",
    )
    require_finite(
        cells,
        (
            "cell_bonferroni_log_p_value",
            "holm_adjusted_log_p_value",
            "holm_critical_value",
        ),
        label="exchangeability transport cells",
    )
    if (
        int(cells["holm_reject_exchangeability_null"].sum()) != 31
        or not cells["holm_reject"].eq(cells["holm_reject_exchangeability_null"]).all()
        or int(strata["continuous_threshold_tie_singleton"].sum()) != 200
        or int(strata["resolved_target_residual_equal_threshold"].sum()) != 0
    ):
        raise RuntimeError("The exact exchangeability decisions or tie audit changed.")

    window_map = dict(zip(WINDOW_IDS, WINDOW_ORDINALS, strict=True))
    publication_cells = cells.rename(
        columns={
            "cell_bonferroni_log_p_value": "source_cell_bonferroni_log_p_value",
            "cell_bonferroni_p_value": "source_cell_bonferroni_p_value",
            "holm_rank": "source_holm_rank",
            "holm_critical_value": "locked_nominal_holm_critical_value",
            "holm_adjusted_log_p_value": "source_holm_adjusted_log_p_value",
            "holm_adjusted_p_value": "source_holm_adjusted_p_value",
            "holm_reject": "source_holm_reject_flag",
            "holm_reject_exchangeability_null": "meets_locked_nominal_holm_threshold",
            "hierarchical_fwer_alpha": "source_declared_hierarchical_fwer_alpha",
        }
    ).copy()
    publication_cells.insert(
        1, "learner_label", publication_cells["learner"].map(CREDIT_LEARNER_LABELS)
    )
    publication_cells.insert(2, "window", publication_cells["window_id"].map(window_map))
    quarantined = S6B_QUARANTINED_COLUMNS.intersection(publication_cells.columns)
    if quarantined:
        raise RuntimeError(f"Quarantined candidate fields entered S6B: {sorted(quarantined)}.")
    publication_cells = publication_cells.drop(
        columns=sorted(S6B_RETIRED_COLUMNS),
        errors="raise",
    )
    if tuple(publication_cells.columns) != S6B_PUBLICATION_COLUMNS:
        raise RuntimeError(
            f"Unexpected S6B publication schema: {tuple(publication_cells.columns)!r}."
        )
    if (
        len(publication_cells) != 40
        or publication_cells["source_holm_rank"].astype(int).nunique() != 40
        or set(publication_cells["source_holm_rank"].astype(int)) != set(range(1, 41))
        or int(publication_cells["meets_locked_nominal_holm_threshold"].sum()) != 31
        or int(publication_cells["strata_with_non_singleton_calibration_threshold_ties"].sum()) != 0
        or not bool(
            publication_cells["all_calibration_threshold_ties_singleton"].astype(bool).all()
        )
    ):
        raise RuntimeError("The exact S6B publication census or decision audit changed.")
    publication_strata = strata.rename(
        columns={
            "exact_log_p_value": "joint_block_reference_exact_log_p_value",
            "exact_p_value": "joint_block_reference_exact_p_value",
            "exact_neg_log10_p_value": "joint_block_reference_exact_neg_log10_p_value",
            "bonferroni_log_p_value": "source_within_cell_bonferroni_log_p_value",
            "bonferroni_p_value": "source_within_cell_bonferroni_p_value",
            "within_cell_bonferroni_reject_at_cell_alpha": (
                "meets_locked_nominal_within_cell_threshold"
            ),
        }
    ).copy()
    publication_strata.insert(
        1, "learner_label", publication_strata["learner"].map(CREDIT_LEARNER_LABELS)
    )
    publication_strata.insert(2, "window", publication_strata["window_id"].map(window_map))
    publication_strata.insert(
        5, "score_stratum", publication_strata["conformal_group"].astype(int) + 1
    )
    return ExchangeabilityTransportInputs(
        summary_path=summary_path,
        receipt_path=receipt_path,
        summary=summary,
        artifacts=artifacts,
        strata=strata,
        cells=cells,
        publication_strata=publication_strata,
        publication_cells=publication_cells,
    )


@dataclass(frozen=True)
class CommonPanelThresholdResponseInputs:
    summary_path: Path
    receipt_path: Path
    config_path: Path
    summary: dict[str, Any]
    artifacts: dict[str, Path]
    strata: pd.DataFrame
    learners: pd.DataFrame
    publication_strata: pd.DataFrame
    publication_learners: pd.DataFrame


def _load_common_panel_threshold_response_inputs(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
) -> CommonPanelThresholdResponseInputs:
    """Load the complete clean-tagged V8 fixed-panel adjacent response."""
    summary_path = registered["common_panel_threshold_response_summary"]
    receipt_path = registered["common_panel_threshold_response_receipt"]
    config_path = registered["common_panel_threshold_response_config"]
    summary = _read_json(summary_path, label="Common-panel threshold-response summary")
    if summary.get("status") != "complete_clean_tagged_common_panel_threshold_response_v8":
        raise RuntimeError("The common-panel threshold-response replay is incomplete.")
    _require_identity(summary, lineage, label="Common-panel threshold-response replay")
    receipt = _read_json(receipt_path, label="Common-panel threshold-response receipt")
    _require_identity(receipt, lineage, label="Common-panel threshold-response receipt")
    if receipt.get("summary") != relative_artifact_descriptor(summary_path, repo_root=ROOT):
        raise RuntimeError("The common-panel receipt no longer binds its summary.")
    _require_clean_execution(summary, label="The common-panel threshold-response replay")
    _require_clean_execution(receipt, label="The common-panel threshold-response receipt")
    if receipt.get("artifacts") != summary.get("artifacts"):
        raise RuntimeError("The common-panel summary and receipt bind different artifacts.")
    raw_archive = relative_artifact_descriptor(
        ROOT / "data/raw/Loan_status_2007-2020Q3.csv", repo_root=ROOT
    )
    if summary.get("protected_artifacts_read") != [raw_archive]:
        raise RuntimeError("The V8 summary does not disclose its protected raw-archive read.")
    if receipt.get("protected_artifacts_read") != [raw_archive]:
        raise RuntimeError("The V8 receipt does not disclose its protected raw-archive read.")
    if (
        summary.get("protected_artifacts_written") != []
        or receipt.get("protected_artifacts_written") != []
    ):
        raise RuntimeError("The V8 replay wrote a protected artifact.")

    census = summary.get("census", {})
    identities = summary.get("identities", {})
    results = summary.get("results", {})
    module_audit = summary.get("module_audit", {})
    if (
        census.get("candidate_rows") != 376890
        or census.get("resolved_rows") != 364814
        or census.get("unresolved_rows") != 12076
        or census.get("stratum_rows") != 175
        or census.get("learner_rows") != 35
        or census.get("full_census_reported_without_selection") is not True
        or identities.get("resolved_signed_crossed_band_integer_identity_all_rows") is not True
        or identities.get("sharp_shared_completion_bounds_all_rows") is not True
        or identities.get("sharp_width_integer_identity_all_rows") is not True
        or identities.get("learner_aggregates_sum_integer_numerators_before_division") is not True
        or identities.get("separately_extremized_coverage_intervals_subtracted") is not False
        or results.get("threshold_increase_rows") != 49
        or results.get("threshold_equal_rows") != 4
        or results.get("threshold_decrease_rows") != 122
        or module_audit.get("fit_audit", {}).get("fit_audit_cells") != 200
        or module_audit.get("fit_audit", {}).get("fit_audit_rows") != 909665
        or module_audit.get("fit_audit", {}).get("capped_cells") != 0
        or module_audit.get("fit_audit", {}).get("tied_threshold_cells") != 0
    ):
        raise RuntimeError("The exact V8 census, identity, or fit-threshold audit changed.")

    implementation = summary.get("implementation_provenance", {}).get("source_files")
    if not isinstance(implementation, Mapping):
        raise TypeError("The V8 summary omits implementation provenance.")
    required_implementation = {
        "configs/experiments/ijds_common_panel_threshold_response_2026-07-26_v8.yaml",
        "docs/research/ijds_common_panel_threshold_response_v8_protocol_2026-07-26.md",
        "scripts/experiments/run_ijds_common_panel_threshold_response_v8.py",
        "src/ijds_audit/common_panel_threshold_response.py",
        "src/models/binary_conformal_guardrail.py",
        "src/ijds_audit/grid_contracts.py",
        "uv.lock",
    }
    if not required_implementation.issubset(implementation):
        raise RuntimeError("The V8 implementation-provenance surface is incomplete.")
    for relative in required_implementation:
        descriptor = implementation[relative]
        if not isinstance(descriptor, Mapping):
            raise TypeError(f"The V8 implementation descriptor is invalid: {relative!r}.")
        require_historical_git_blob_descriptor(
            descriptor,
            commit=str(lineage["protocol_commit"]),
            relative_path=relative,
            repo_root=ROOT,
            label=f"V8 execution-time implementation {relative}",
        )
    if implementation[
        "configs/experiments/ijds_common_panel_threshold_response_2026-07-26_v8.yaml"
    ] != relative_artifact_descriptor(config_path, repo_root=ROOT):
        raise RuntimeError("The registered V8 config differs from the executed config.")

    artifacts = _verified_artifact_paths(
        cast(Mapping[str, Mapping[str, Any]], summary["artifacts"])
    )
    registered_artifacts = {
        "adjacent_stratum_threshold_response": registered["common_panel_threshold_response_strata"],
        "adjacent_learner_threshold_response": registered[
            "common_panel_threshold_response_learners"
        ],
    }
    if artifacts != registered_artifacts:
        raise RuntimeError("The registered V8 table paths differ from the executed artifacts.")
    strata = pd.read_csv(artifacts["adjacent_stratum_threshold_response"])
    learners = pd.read_csv(artifacts["adjacent_learner_threshold_response"])
    require_exact_grid(
        strata,
        domains={
            "learner": CREDIT_LEARNER_ORDER,
            "pair_index": tuple(range(7)),
            "conformal_group": tuple(range(5)),
        },
        label="common-panel threshold-response strata",
    )
    require_exact_grid(
        learners,
        domains={"learner": CREDIT_LEARNER_ORDER, "pair_index": tuple(range(7))},
        label="common-panel threshold-response learners",
    )
    require_finite(
        strata,
        (
            "threshold_from",
            "threshold_to",
            "threshold_delta",
            "resolved_delta_numerator",
            "resolved_delta_rate",
            "delta_lower_numerator",
            "delta_upper_numerator",
            "delta_width_numerator",
            "delta_lower",
            "delta_upper",
            "delta_width",
        ),
        label="common-panel threshold-response strata",
    )
    require_finite(
        learners,
        (
            "resolved_delta_numerator",
            "resolved_delta_rate",
            "delta_lower_numerator",
            "delta_upper_numerator",
            "delta_width_numerator",
            "delta_lower",
            "delta_upper",
            "delta_width",
        ),
        label="common-panel threshold-response learners",
    )
    if (
        not strata["resolved_delta_numerator"]
        .eq(
            strata["threshold_sign"]
            * (strata["resolved_y0_crossed_rows"] + strata["resolved_y1_crossed_rows"])
        )
        .all()
        or not (strata["delta_upper_numerator"] - strata["delta_lower_numerator"])
        .eq(strata["delta_width_numerator"])
        .all()
        or int(strata["delta_upper"].lt(0.0).sum()) != 122
        or int(strata["delta_lower"].gt(0.0).sum()) != 48
        or int((strata["delta_lower"].eq(0.0) & strata["delta_upper"].eq(0.0)).sum()) != 5
        or int((strata["delta_lower"].lt(0.0) & strata["delta_upper"].gt(0.0)).sum()) != 0
        or int(
            (
                (strata["delta_lower"].eq(0.0) & strata["delta_upper"].gt(0.0))
                | (strata["delta_lower"].lt(0.0) & strata["delta_upper"].eq(0.0))
            ).sum()
        )
        != 0
        or int(learners["delta_upper"].lt(0.0).sum()) != 31
        or int(learners["delta_lower"].gt(0.0).sum()) != 4
        or bool((learners["delta_lower"].le(0.0) & learners["delta_upper"].ge(0.0)).any())
    ):
        raise RuntimeError("The V8 exact response identities or sign census changed.")
    disclosed = require_unique_row(
        strata,
        key={
            "learner": "catboost_platt",
            "pair_index": 6,
            "conformal_group": 2,
        },
        label="V8 disclosed W7--W8 CatBoost stratum",
    )
    if (
        int(disclosed["resolved_delta_numerator"]) != -281
        or int(disclosed["delta_lower_numerator"]) != -312
        or int(disclosed["delta_upper_numerator"]) != -290
        or not np.isclose(float(disclosed["threshold_from"]), 0.8884345991499274)
        or not np.isclose(float(disclosed["threshold_to"]), 0.1118010883671265)
    ):
        raise RuntimeError("The disclosed V8 fixed-panel response changed.")

    transition_labels = {index: f"W{index + 1}--W{index + 2}" for index in range(7)}
    publication_strata = strata.copy()
    publication_strata.insert(
        1, "learner_label", publication_strata["learner"].map(CREDIT_LEARNER_LABELS)
    )
    publication_strata.insert(
        3, "transition", publication_strata["pair_index"].map(transition_labels)
    )
    publication_strata = publication_strata.drop(
        columns=["ids_sha256", "scores_sha256", "assignments_sha256"],
        errors="raise",
    )
    publication_learners = learners.copy()
    publication_learners.insert(
        1, "learner_label", publication_learners["learner"].map(CREDIT_LEARNER_LABELS)
    )
    publication_learners.insert(
        3, "transition", publication_learners["pair_index"].map(transition_labels)
    )
    return CommonPanelThresholdResponseInputs(
        summary_path=summary_path,
        receipt_path=receipt_path,
        config_path=config_path,
        summary=summary,
        artifacts=artifacts,
        strata=strata,
        learners=learners,
        publication_strata=publication_strata,
        publication_learners=publication_learners,
    )


@dataclass(frozen=True)
class EqualFollowupInputs:
    summary_path: Path
    receipt_path: Path
    summary: dict[str, Any]
    artifacts: dict[str, Path]
    coverage: pd.DataFrame
    publication_coverage: pd.DataFrame
    publication_census: pd.DataFrame


def _load_equal_followup_inputs(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
) -> EqualFollowupInputs:
    summary_path = registered["rolling_equal_followup_summary"]
    receipt_path = registered["rolling_equal_followup_receipt"]
    summary = _read_json(summary_path, label="Equal-follow-up summary")
    if (
        summary.get("status")
        != "complete_retrospective_equal_relative_followup_coverage_evaluation"
    ):
        raise RuntimeError("The equal-follow-up evaluation is incomplete.")
    _require_identity(summary, lineage, label="Equal-follow-up evaluation")
    receipt = _read_json(receipt_path, label="Equal-follow-up receipt")
    _require_identity(receipt, lineage, label="Equal-follow-up receipt")
    if receipt.get("summary") != relative_artifact_descriptor(summary_path, repo_root=ROOT):
        raise RuntimeError("The equal-follow-up receipt no longer binds its summary.")
    _require_clean_execution(summary, label="The equal-follow-up evaluation")
    _require_clean_execution(receipt, label="The equal-follow-up receipt")
    if (
        summary.get("design", {}).get("common_followup_months_after_issue_quarter_end") != 39
        or summary.get("coverage_cells") != 16
        or summary.get("all_sixteen_upper_below_nominal") is not True
        or summary.get("claim_boundary", {}).get("independent_replication") is not False
    ):
        raise RuntimeError("The equal-follow-up design or result changed.")

    artifacts = _verified_artifact_paths(summary["artifacts"])
    coverage = pd.read_parquet(artifacts["temporal_coverage"])
    require_exact_grid(
        coverage,
        domains={
            "origin_id": ("primary_2016", "rolling_2017"),
            "window_ordinal": tuple(range(1, 9)),
        },
        label="equal-follow-up coverage",
    )
    require_finite(
        coverage,
        (
            "candidate_rows",
            "resolved_rows",
            "unresolved_rows",
            "coverage_resolved",
            "coverage_lower",
            "coverage_upper",
            "mean_width",
        ),
        label="equal-follow-up coverage",
    )
    if (
        not coverage["common_followup_months"].eq(39).all()
        or not coverage["coverage_upper"].lt(0.90).all()
        or not coverage.loc[coverage["origin_id"].eq("primary_2016"), "candidate_rows"]
        .eq(74537)
        .all()
        or not coverage.loc[coverage["origin_id"].eq("primary_2016"), "resolved_rows"]
        .eq(74120)
        .all()
        or not coverage.loc[coverage["origin_id"].eq("rolling_2017"), "candidate_rows"]
        .eq(77105)
        .all()
        or not coverage.loc[coverage["origin_id"].eq("rolling_2017"), "resolved_rows"]
        .eq(66091)
        .all()
    ):
        raise RuntimeError("The equal-follow-up coverage or census changed.")
    publication_coverage = coverage.copy()
    publication_coverage.insert(
        1,
        "origin",
        publication_coverage["origin_id"].map(
            {"primary_2016": "2016 origin", "rolling_2017": "2017 origin"}
        ),
    )
    publication_coverage.insert(
        2, "window", publication_coverage["window_ordinal"].map(lambda value: f"W{int(value)}")
    )
    reason = pd.read_parquet(artifacts["origin_endpoint_reason_census"])
    require_exact_grid(
        reason,
        domains={
            "origin_id": ("primary_2016", "rolling_2017"),
            "snapshot_resolution": (
                "fully_paid_by_reconstructed_cutoff",
                "charged_off_by_reconstructed_cutoff",
                "nonterminal_or_unresolved_status",
                "terminal_after_reconstructed_cutoff",
                "terminal_availability_date_missing",
            ),
        },
        label="equal-follow-up endpoint-reason census",
    )
    publication_census = reason.copy()
    publication_census.insert(
        1,
        "origin",
        publication_census["origin_id"].map(
            {"primary_2016": "2016 origin", "rolling_2017": "2017 origin"}
        ),
    )
    return EqualFollowupInputs(
        summary_path=summary_path,
        receipt_path=receipt_path,
        summary=summary,
        artifacts=artifacts,
        coverage=coverage,
        publication_coverage=publication_coverage,
        publication_census=publication_census,
    )


@dataclass(frozen=True)
class IndividualAgeFollowupInputs:
    summary_path: Path
    receipt_path: Path
    summary: dict[str, Any]
    artifacts: dict[str, Path]
    coverage: pd.DataFrame
    publication_coverage: pd.DataFrame
    publication_census: pd.DataFrame
    publication_reason_census: pd.DataFrame


def _load_individual_age_followup_inputs(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
) -> IndividualAgeFollowupInputs:
    summary_path = registered["rolling_individual_age_followup_summary"]
    receipt_path = registered["rolling_individual_age_followup_receipt"]
    summary = _read_json(summary_path, label="Individual-age follow-up summary")
    receipt = _read_json(receipt_path, label="Individual-age follow-up receipt")
    _require_identity(summary, lineage, label="Individual-age follow-up evaluation")
    _require_identity(receipt, lineage, label="Individual-age follow-up receipt")
    if receipt.get("summary") != relative_artifact_descriptor(summary_path, repo_root=ROOT):
        raise RuntimeError("The individual-age receipt no longer binds its summary.")
    _require_clean_execution(summary, label="The individual-age follow-up evaluation")
    _require_clean_execution(receipt, label="The individual-age follow-up receipt")
    if (
        summary.get("status") != "complete_retrospective_individual_age_followup_sensitivity"
        or summary.get("design", {}).get("individual_followup_months_after_issue_month_end") != 39
        or summary.get("design", {}).get("issue_date_resolution") != "calendar_month"
        or summary.get("design", {}).get("endpoint_rule")
        != "issue_month_end_plus_39_calendar_months"
        or summary.get("coverage_cells") != 16
        or summary.get("all_sixteen_upper_below_nominal") is not True
        or summary.get("claim_boundary", {}).get("independent_replication") is not False
        or summary.get("claim_boundary", {}).get("error_controlled") is not False
    ):
        raise RuntimeError("The individual-age follow-up design or result changed.")

    artifacts = _verified_artifact_paths(summary["artifacts"])
    coverage = pd.read_parquet(artifacts["temporal_coverage"])
    require_exact_grid(
        coverage,
        domains={
            "origin_id": ("primary_2016", "rolling_2017"),
            "window_ordinal": tuple(range(1, 9)),
        },
        label="individual-age follow-up coverage",
    )
    require_finite(
        coverage,
        (
            "candidate_rows",
            "resolved_rows",
            "unresolved_rows",
            "coverage_resolved",
            "coverage_lower",
            "coverage_upper",
            "mean_width",
        ),
        label="individual-age follow-up coverage",
    )
    expected_censuses = {
        "primary_2016": (74_537, 73_934, 603),
        "rolling_2017": (77_105, 66_037, 11_068),
    }
    for origin_id, (candidate_rows, resolved_rows, unresolved_rows) in expected_censuses.items():
        origin = coverage.loc[coverage["origin_id"].eq(origin_id)]
        if (
            not origin["candidate_rows"].eq(candidate_rows).all()
            or not origin["resolved_rows"].eq(resolved_rows).all()
            or not origin["unresolved_rows"].eq(unresolved_rows).all()
        ):
            raise RuntimeError(f"The {origin_id} individual-age census changed.")
    if (
        not coverage["individual_followup_months"].eq(39).all()
        or not coverage["coverage_upper"].lt(0.90).all()
    ):
        raise RuntimeError("The individual-age coverage endpoints changed.")

    publication_coverage = coverage.copy()
    publication_coverage.insert(
        1,
        "origin",
        publication_coverage["origin_id"].map(
            {"primary_2016": "2016 origin", "rolling_2017": "2017 origin"}
        ),
    )
    publication_coverage.insert(
        2, "window", publication_coverage["window_ordinal"].map(lambda value: f"W{int(value)}")
    )

    monthly = pd.read_parquet(artifacts["monthly_endpoint_census"])
    monthly_reason = pd.read_parquet(artifacts["monthly_endpoint_reason_census"])
    expected_origin_periods = (
        "primary_2016:2016-04",
        "primary_2016:2016-05",
        "primary_2016:2016-06",
        "rolling_2017:2017-04",
        "rolling_2017:2017-05",
        "rolling_2017:2017-06",
    )
    endpoint_reasons = (
        "fully_paid_by_reconstructed_cutoff",
        "charged_off_by_reconstructed_cutoff",
        "nonterminal_or_unresolved_status",
        "terminal_after_reconstructed_cutoff",
        "terminal_availability_date_missing",
    )
    monthly_reason = monthly_reason.assign(
        origin_period=(
            monthly_reason["origin_id"].astype(str) + ":" + monthly_reason["period"].astype(str)
        )
    )
    require_exact_grid(
        monthly_reason,
        domains={
            "origin_period": expected_origin_periods,
            "snapshot_resolution": endpoint_reasons,
        },
        label="individual-age monthly endpoint-reason census",
    )
    expected_cutoffs = {
        "2016-04": "2019-07-31",
        "2016-05": "2019-08-31",
        "2016-06": "2019-09-30",
        "2017-04": "2020-07-31",
        "2017-05": "2020-08-31",
        "2017-06": "2020-09-30",
    }
    observed_cutoffs = {
        str(period): str(pd.Timestamp(cutoff).date())
        for period, cutoff in zip(
            monthly["period"], monthly["individual_evaluation_cutoff"], strict=True
        )
    }
    if (
        len(monthly) != 6
        or observed_cutoffs != expected_cutoffs
        or not monthly["individual_followup_months"].eq(39).all()
        or int(monthly["candidate_rows"].sum()) != 151_642
        or int(monthly["resolved_rows"].sum()) != 139_971
        or int(monthly["unresolved_rows"].sum()) != 11_671
    ):
        raise RuntimeError("The individual-age monthly endpoint census changed.")

    reason_wide = (
        monthly_reason.pivot(
            index=["origin_id", "origin_year", "period"],
            columns="snapshot_resolution",
            values="candidate_rows",
        )
        .reset_index()
        .rename_axis(columns=None)
    )
    publication_census = monthly.merge(
        reason_wide,
        on=["origin_id", "origin_year", "period"],
        how="left",
        validate="one_to_one",
    )
    for column in ("issue_month_end", "individual_evaluation_cutoff"):
        publication_census[column] = pd.to_datetime(
            publication_census[column], errors="raise"
        ).dt.strftime("%Y-%m-%d")
    publication_census.insert(
        1,
        "origin",
        publication_census["origin_id"].map(
            {"primary_2016": "2016 origin", "rolling_2017": "2017 origin"}
        ),
    )
    publication_reason_census = monthly_reason.drop(columns="origin_period").copy()
    for column in ("issue_month_end", "individual_evaluation_cutoff"):
        publication_reason_census[column] = pd.to_datetime(
            publication_reason_census[column], errors="raise"
        ).dt.strftime("%Y-%m-%d")
    publication_reason_census.insert(
        1,
        "origin",
        publication_reason_census["origin_id"].map(
            {"primary_2016": "2016 origin", "rolling_2017": "2017 origin"}
        ),
    )
    return IndividualAgeFollowupInputs(
        summary_path=summary_path,
        receipt_path=receipt_path,
        summary=summary,
        artifacts=artifacts,
        coverage=coverage,
        publication_coverage=publication_coverage,
        publication_census=publication_census,
        publication_reason_census=publication_reason_census,
    )


@dataclass(frozen=True)
class LabelMondrianInputs:
    freeze_path: Path
    freeze_receipt_path: Path
    summary_path: Path
    receipt_path: Path
    summary: dict[str, Any]
    freeze_artifacts: dict[str, Path]
    artifacts: dict[str, Path]
    cells: pd.DataFrame
    strata: pd.DataFrame
    categories: pd.DataFrame
    reconciliation: pd.DataFrame
    publication_cells: pd.DataFrame
    publication_strata: pd.DataFrame
    publication_categories: pd.DataFrame


def _load_label_mondrian_inputs(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
) -> LabelMondrianInputs:
    freeze_identity = cast(Mapping[str, Any], lineage["outcome_free"])
    evaluation_identity = cast(Mapping[str, Any], lineage["evaluation"])
    freeze_path = registered["label_mondrian_freeze"]
    freeze_receipt_path = registered["label_mondrian_freeze_receipt"]
    summary_path = registered["label_mondrian_evaluation_summary"]
    receipt_path = registered["label_mondrian_evaluation_receipt"]
    freeze = _read_json(freeze_path, label="Label-Mondrian freeze")
    freeze_receipt = _read_json(freeze_receipt_path, label="Label-Mondrian freeze receipt")
    summary = _read_json(summary_path, label="Label-Mondrian evaluation summary")
    receipt = _read_json(receipt_path, label="Label-Mondrian evaluation receipt")
    _require_identity(freeze, freeze_identity, label="Label-Mondrian freeze")
    _require_identity(freeze_receipt, freeze_identity, label="Label-Mondrian freeze receipt")
    _require_identity(summary, evaluation_identity, label="Label-Mondrian evaluation")
    _require_identity(receipt, evaluation_identity, label="Label-Mondrian evaluation receipt")
    if (
        freeze_receipt.get("freeze") != relative_artifact_descriptor(freeze_path, repo_root=ROOT)
        or receipt.get("summary") != relative_artifact_descriptor(summary_path, repo_root=ROOT)
        or summary.get("source_artifacts", {}).get("label_mondrian_freeze")
        != relative_artifact_descriptor(freeze_path, repo_root=ROOT)
        or summary.get("source_artifacts", {}).get("label_mondrian_freeze_receipt")
        != relative_artifact_descriptor(freeze_receipt_path, repo_root=ROOT)
    ):
        raise RuntimeError("The Label-Mondrian freeze/evaluation descriptor chain changed.")
    _require_clean_execution(freeze, label="The Label-Mondrian freeze")
    _require_clean_execution(freeze_receipt, label="The Label-Mondrian freeze receipt")
    _require_clean_execution(summary, label="The Label-Mondrian evaluation")
    _require_clean_execution(receipt, label="The Label-Mondrian evaluation receipt")
    if (
        summary.get("status") != "complete_retrospective_label_mondrian_evaluation"
        or summary.get("counts", {}).get("learner_window_cells") != 40
        or summary.get("counts", {}).get("target_stratum_cells") != 200
        or summary.get("counts", {}).get("target_category_cells") != 400
        or summary.get("baseline_reconciliation", {}).get("maximum_absolute_difference", 1.0)
        > 5.0e-14
        or summary.get("interpretation", {}).get("label_conditional_transport_guarantee")
        is not False
    ):
        raise RuntimeError("The Label-Mondrian result or interpretation boundary changed.")

    freeze_artifacts = _verified_artifact_paths(freeze["outcome_free_artifacts"])
    artifacts = _verified_artifact_paths(summary["artifacts"])
    cells = pd.read_parquet(artifacts["label_mondrian_diagnostics"])
    strata = pd.read_parquet(artifacts["label_mondrian_stratum_diagnostics"])
    categories = pd.read_parquet(artifacts["label_mondrian_category_diagnostics"])
    reconciliation = pd.read_parquet(artifacts["marginal_baseline_reconciliation"])
    require_exact_grid(
        cells,
        domains={"learner": CREDIT_LEARNER_ORDER, "window_id": WINDOW_IDS},
        label="Label-Mondrian learner-window cells",
    )
    require_exact_grid(
        strata,
        domains={
            "learner": CREDIT_LEARNER_ORDER,
            "window_id": WINDOW_IDS,
            "score_stratum": tuple(range(5)),
        },
        label="Label-Mondrian target strata",
    )
    require_exact_grid(
        categories,
        domains={
            "learner": CREDIT_LEARNER_ORDER,
            "window_id": WINDOW_IDS,
            "score_stratum": tuple(range(5)),
            "label": (0, 1),
        },
        label="Label-Mondrian target categories",
    )
    require_exact_grid(
        reconciliation,
        domains={"learner": CREDIT_LEARNER_ORDER, "window_id": WINDOW_IDS},
        label="Label-Mondrian baseline reconciliation",
    )
    cell_state = pd.Series("crosses_nominal", index=cells.index)
    cell_state.loc[cells["coverage_upper"].lt(0.90)] = "robust_shortfall"
    cell_state.loc[cells["coverage_lower"].ge(0.90)] = "robust_at_or_above_nominal"
    if (
        cell_state.value_counts().to_dict()
        != {"robust_shortfall": 27, "crosses_nominal": 12, "robust_at_or_above_nominal": 1}
        or categories["identification_state_at_nominal"].value_counts().to_dict()
        != {"crosses_nominal": 185, "robust_shortfall": 109, "robust_at_or_above_nominal": 106}
        or not cells["set_empty_share"].eq(0.0).all()
        or not categories["sharp_endpoint_delta_reported"].eq(False).all()
        or not strata["sharp_endpoint_delta_reported"].eq(False).all()
    ):
        raise RuntimeError("The Label-Mondrian identification or geometry pattern changed.")

    window_map = dict(zip(WINDOW_IDS, WINDOW_ORDINALS, strict=True))
    publication_cells = cells.copy()
    publication_cells.insert(
        1, "learner_label", publication_cells["learner"].map(CREDIT_LEARNER_LABELS)
    )
    publication_cells.insert(2, "window", publication_cells["window_id"].map(window_map))
    publication_cells.insert(5, "identification_state_at_nominal", cell_state)
    publication_strata = strata.copy()
    publication_strata.insert(
        1, "learner_label", publication_strata["learner"].map(CREDIT_LEARNER_LABELS)
    )
    publication_strata.insert(2, "window", publication_strata["window_id"].map(window_map))
    publication_categories = categories.copy()
    publication_categories.insert(
        1, "learner_label", publication_categories["learner"].map(CREDIT_LEARNER_LABELS)
    )
    publication_categories.insert(2, "window", publication_categories["window_id"].map(window_map))
    return LabelMondrianInputs(
        freeze_path=freeze_path,
        freeze_receipt_path=freeze_receipt_path,
        summary_path=summary_path,
        receipt_path=receipt_path,
        summary=summary,
        freeze_artifacts=freeze_artifacts,
        artifacts=artifacts,
        cells=cells,
        strata=strata,
        categories=categories,
        reconciliation=reconciliation,
        publication_cells=publication_cells,
        publication_strata=publication_strata,
        publication_categories=publication_categories,
    )


@dataclass(frozen=True)
class MissingnessInputs:
    summary_path: Path
    receipt_path: Path
    summary: dict[str, Any]
    freeze_path: Path
    artifacts: dict[str, Path]
    freeze_artifacts: dict[str, Path]
    model_artifacts: dict[str, Path]
    publication_table: pd.DataFrame


@dataclass(frozen=True)
class StagedPublicationGeneration:
    """One complete set of staged paper-facing tables and figures."""

    table_paths: dict[str, Path]
    figures: dict[str, dict[str, Path]]
    figure_targets: dict[str, dict[str, Path]]
    outputs: dict[Path, Path]


def _load_missingness_inputs(
    registered: Mapping[str, Path],
    lineage: Mapping[str, Any],
) -> MissingnessInputs:
    summary_path = registered["missingness_summary"]
    receipt_path = registered["missingness_receipt"]
    summary = _read_json(summary_path, label="Missingness summary")
    if summary.get("status") != "complete_no_selection_missingness_sensitivity":
        raise RuntimeError("The missingness-encoding sensitivity is incomplete.")
    _require_identity(summary, lineage, label="Missingness sensitivity")
    receipt = _read_json(receipt_path, label="Missingness execution receipt")
    _require_identity(receipt, lineage, label="Missingness receipt")
    if receipt.get("summary") != relative_artifact_descriptor(summary_path, repo_root=ROOT):
        raise RuntimeError("The missingness receipt no longer binds its summary.")
    expected_interpretation = {
        "model_or_encoding_selected": False,
        "portfolio_claim_authorized": False,
        "missing_at_random_claim_authorized": False,
        "robustness_scope": "three_declared_feature_semantics_preserving_missingness_encodings_only",
    }
    if summary.get("interpretation") != expected_interpretation:
        raise RuntimeError("The missingness sensitivity claim boundary changed.")
    _require_clean_execution(summary, label="The missingness sensitivity")
    freeze_path = _verified_path(summary["source_freeze"])
    freeze = _read_json(freeze_path, label="Missingness outcome-free freeze")
    if (
        freeze.get("status") != "missingness_scores_frozen_before_primary_oot_outcome_join"
        or freeze.get("primary_oot_outcome_columns_in_frozen_scores") != []
        or any(value is not None for value in freeze.get("selection", {}).values())
    ):
        raise RuntimeError("The missingness outcome-free freeze boundary changed.")
    artifacts = _verified_artifact_paths(summary["evaluation_artifacts"])
    freeze_artifacts = _verified_artifact_paths(freeze["outcome_free_artifacts"])
    model_artifacts = _verified_artifact_paths(freeze["model_artifacts"])
    coverage_all = pd.read_parquet(artifacts["temporal_coverage"])
    coverage = coverage_all.loc[
        coverage_all["taxonomy_groups"].eq(5)
        & coverage_all["role"].eq("primary_oot")
        & coverage_all["conformal_group"].eq(-1)
    ].sort_values(["learner", "window_id"])
    learners = tuple(str(item["id"]) for item in summary["specifications"])
    require_exact_grid(
        coverage,
        domains={"learner": learners, "window_id": WINDOW_IDS},
        label="missingness-encoding coverage",
    )
    prediction = pd.read_parquet(artifacts["prediction_metrics"])
    if set(prediction["learner"].astype(str)) != set(learners):
        raise RuntimeError("The missingness prediction-metric family changed.")
    publication_table = pd.DataFrame(summary["coverage"]).merge(
        prediction[["learner", "roc_auc", "brier", "log_loss", "ece_10", "calibration_slope"]],
        on="learner",
        how="left",
        validate="one_to_one",
    )
    return MissingnessInputs(
        summary_path=summary_path,
        receipt_path=receipt_path,
        summary=summary,
        freeze_path=freeze_path,
        artifacts=artifacts,
        freeze_artifacts=freeze_artifacts,
        model_artifacts=model_artifacts,
        publication_table=publication_table,
    )


def _json_safe_records(frame: pd.DataFrame, *, label: str) -> list[dict[str, Any]]:
    """Convert publication rows to strict JSON, retaining inapplicable cells as null."""
    numeric = frame.select_dtypes(include=[np.number])
    for column in numeric:
        values = pd.to_numeric(numeric[column], errors="raise").to_numpy(dtype=float)
        if bool(np.isinf(values).any()):
            raise RuntimeError(f"{label} contains an infinite value in {column!r}.")
    cleaned = frame.astype(object).where(pd.notna(frame), None)
    return cast(list[dict[str, Any]], cleaned.to_dict(orient="records"))


def _calibrator_sensitivity_manifest_payload(
    evidence: CalibratorSensitivityEvidence,
    *,
    identities: Mapping[str, Any],
    method_fit_table: pd.DataFrame,
    cell_table: pd.DataFrame,
    pairwise_table: pd.DataFrame,
) -> dict[str, Any]:
    """Materialize the closed-family result without selecting a map or policy."""
    counts = evidence.summary.get("counts")
    expected_counts = {
        "methods": 4,
        "windows": 8,
        "scopes_per_method_window": 6,
        "evaluation_cells": 192,
        "overall_cells": 32,
        "pairwise_cells": 288,
        "candidate_rows": 376890,
        "resolved_rows": 364814,
        "unresolved_rows": 12076,
        "resolved_y0": 307842,
        "resolved_y1": 56972,
    }
    if not isinstance(counts, Mapping) or any(
        counts.get(name) != expected for name, expected in expected_counts.items()
    ):
        raise RuntimeError("The calibrator-sensitivity manifest census changed.")
    if (
        len(method_fit_table) != 4
        or len(cell_table) != 192
        or len(pairwise_table) != 288
        or set(method_fit_table["method"].astype(str)) != set(CALIBRATOR_METHODS)
    ):
        raise RuntimeError("The public calibrator-sensitivity table family is incomplete.")
    forbidden_public_column_tokens = ("allocation", "portfolio", "objective", "net_return")
    public_columns = {
        str(column).lower()
        for frame in (method_fit_table, cell_table, pairwise_table)
        for column in frame.columns
    }
    if any(
        token in column for column in public_columns for token in forbidden_public_column_tokens
    ):
        raise RuntimeError("The calibrator sensitivity leaked portfolio fields.")

    overall = evidence.frames["overall"]
    if (
        len(overall) != 32
        or set(overall["method"].astype(str)) != set(CALIBRATOR_METHODS)
        or not overall["conformal_group"].eq(-1).all()
    ):
        raise RuntimeError("The calibrator-sensitivity overall grid changed.")
    indicator = overall["coverage_upper_below_nominal"]
    if not pd.api.types.is_bool_dtype(indicator.dtype) or bool(indicator.isna().any()):
        raise RuntimeError("The calibrator-sensitivity result indicator is not exact boolean.")
    below = indicator.astype(bool)
    below_count = int(below.sum())
    at_or_above_count = int((~below).sum())
    derived_result_state = (
        "all_32_overall_upper_below_nominal"
        if below_count == len(overall)
        else "uniform_closed_family_shortfall_not_established"
    )
    method_census = {
        method: {
            "upper_below_nominal": int(below.loc[overall["method"].astype(str).eq(method)].sum()),
            "upper_at_or_above_nominal": int(
                (~below.loc[overall["method"].astype(str).eq(method)]).sum()
            ),
        }
        for method in CALIBRATOR_METHODS
    }
    expected_method_census = {
        "platt": {"upper_below_nominal": 8, "upper_at_or_above_nominal": 0},
        "isotonic": {"upper_below_nominal": 1, "upper_at_or_above_nominal": 7},
        "beta": {"upper_below_nominal": 8, "upper_at_or_above_nominal": 0},
        "venn_abers": {"upper_below_nominal": 1, "upper_at_or_above_nominal": 7},
    }
    if method_census != expected_method_census:
        raise RuntimeError("The complete calibrator-sensitivity result census changed.")

    result = evidence.summary.get("result_boundary")
    if not isinstance(result, Mapping) or (
        derived_result_state != "uniform_closed_family_shortfall_not_established"
        or below_count != 18
        or at_or_above_count != 14
        or result.get("result_state") != derived_result_state
        or result.get("overall_cells_with_coverage_upper_below_nominal") != below_count
        or result.get("overall_cells_with_coverage_upper_at_or_above_nominal") != at_or_above_count
        or result.get("all_overall_cells_below_nominal") is not False
    ):
        raise RuntimeError("The calibrator-sensitivity identified result boundary changed.")

    interpretation = evidence.summary.get("interpretation")
    required_false = (
        "learner_calibrator_window_or_result_selected",
        "sampling_confidence_interval",
        "missing_at_random_assumption",
        "venn_abers_multiprobability_guarantee_transported_to_scalarization",
        "latent_pd_interval",
        "policy_claim",
        "portfolio_optimization",
        "selected_set_guarantee",
        "funded_set_guarantee",
    )
    if not isinstance(interpretation, Mapping) or any(
        interpretation.get(field) is not False for field in required_false
    ):
        raise RuntimeError("The calibrator-sensitivity selection or portfolio boundary changed.")
    freeze_contract = evidence.freeze.get("information_contract")
    if not isinstance(freeze_contract, Mapping) or (
        freeze_contract.get("learner_calibrator_window_or_result_selected") is not False
        or freeze_contract.get("portfolio_optimization_run") is not False
    ):
        raise RuntimeError("The outcome-free calibrator freeze permits selection or optimization.")
    if (
        evidence.summary.get("protected_stages_run") != []
        or evidence.summary.get("protected_artifacts_written") != []
    ):
        raise RuntimeError("The calibrator sensitivity reports a protected side effect.")

    return {
        "scope": (
            "four_fixed_calibration_maps_by_eight_windows_by_pooled_plus_five_"
            "common_uncalibrated_probability_q_raw_strata"
        ),
        "result_state": derived_result_state,
        "run_tag": str(evidence.summary["run_tag"]),
        "protocol_tag": str(evidence.summary["protocol_tag"]),
        "protocol_commit": str(evidence.summary["protocol_commit"]),
        "outcome_free_lineage": dict(cast(Mapping[str, Any], identities["outcome_free"])),
        "evaluation_lineage": dict(cast(Mapping[str, Any], identities["evaluation"])),
        "methods": list(CALIBRATOR_METHODS),
        "counts": dict(counts),
        "overall_cells_with_coverage_upper_below_nominal": below_count,
        "overall_cells_with_coverage_upper_at_or_above_nominal": at_or_above_count,
        "overall_result_census_by_method": method_census,
        "findings": dict(evidence.findings),
        "method_fit_rows": _json_safe_records(
            method_fit_table,
            label="calibrator fit diagnostics",
        ),
        "cell_rows": _json_safe_records(
            cell_table,
            label="calibrator complete cells",
        ),
        "pairwise_rows": _json_safe_records(
            pairwise_table,
            label="calibrator pairwise cells",
        ),
        "interpretation": {
            **dict(interpretation),
            "closed_family_complete_reporting": True,
            "fit_metrics_same_sample_descriptive_only": True,
            "common_q_raw_taxonomy": True,
            "shared_loanwise_completion_for_pairwise_bounds": True,
            "uniform_shortfall_not_established_is_not_true_coverage_dependence": True,
            "temporal_transport_established": False,
            "prospective_transport_established": False,
            "calibrator_winner": None,
            "selected_calibrator": None,
            "portfolio_score_changed": False,
            "portfolio_optimization_run": False,
            "pre_existing_platt_score_remains_primary_portfolio_score": True,
            "alternative_calibrator_maps_propagated_to_portfolio": False,
        },
    }


def _stage_publication_generation(
    staging_root: Path,
    *,
    tables: Mapping[str, pd.DataFrame],
    coverage: pd.DataFrame,
    exchangeability_cells: pd.DataFrame,
    phase: pd.DataFrame,
    development_envelopes: pd.DataFrame,
    common_panel_threshold_response: pd.DataFrame,
) -> StagedPublicationGeneration:
    """Write one complete staged generation and validate its exact surface."""
    if set(tables) != set(TABLE_TARGETS):
        missing = sorted(set(TABLE_TARGETS).difference(tables))
        unexpected = sorted(set(tables).difference(TABLE_TARGETS))
        raise RuntimeError(
            f"The publication table family changed: missing={missing}, unexpected={unexpected}."
        )
    staged_table_targets = {
        name: staged_output_path(staging_root, target, repo_root=ROOT)
        for name, target in TABLE_TARGETS.items()
    }
    table_paths = {
        name: _write_csv(tables[name], staged_table_targets[name]) for name in TABLE_TARGETS
    }
    staged_figure_dir = staging_root / "outputs" / FIGURE_DIR.relative_to(ROOT)
    figures = {
        "coverage": _coverage_figure(
            coverage,
            exchangeability_cells,
            output_dir=staged_figure_dir,
        ),
        "phase_transition": _phase_figure(phase, output_dir=staged_figure_dir),
        "development_envelopes": _envelope_figure(
            development_envelopes,
            output_dir=staged_figure_dir,
        ),
        "common_panel_threshold_response": _common_panel_threshold_response_figure(
            common_panel_threshold_response,
            output_dir=staged_figure_dir,
        ),
        "common_panel_threshold_response_census": (
            _common_panel_threshold_response_census_figure(
                common_panel_threshold_response,
                output_dir=staged_figure_dir,
            )
        ),
    }
    figure_targets = {
        name: {kind: FIGURE_DIR / f"{FIGURE_STEMS[name]}.{kind}" for kind in ("png", "pdf")}
        for name in FIGURE_STEMS
    }
    outputs = {
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
    expected_artifact_count = len(TABLE_TARGETS) + 2 * len(FIGURE_STEMS)
    expected_figure_files = 2 * len(FIGURE_STEMS)
    if len(outputs) != expected_artifact_count or set(outputs) != expected_targets:
        raise RuntimeError(
            "The staged publication generation is not exactly "
            f"{len(TABLE_TARGETS)} CSVs and {expected_figure_files} figure files."
        )
    return StagedPublicationGeneration(
        table_paths=table_paths,
        figures=figures,
        figure_targets=figure_targets,
        outputs=outputs,
    )


def _without_simulation_artifacts(artifacts: Mapping[str, Path]) -> dict[str, Path]:
    """Exclude the historical synthetic mechanism outputs from paper evidence."""
    return {name: path for name, path in artifacts.items() if not name.startswith("simulation_")}


def _publication_source_descriptors(
    *,
    direct_paths: Mapping[str, Path],
    artifact_groups: Mapping[str, Mapping[str, Path]],
) -> dict[str, dict[str, Any]]:
    """Describe every implementation and scientific source exactly once."""
    descriptors = dict(publication_implementation_descriptors(ROOT))

    def add(name: str, path: Path) -> None:
        if name in descriptors:
            raise RuntimeError(f"Duplicate publication source descriptor: {name!r}.")
        descriptors[name] = relative_artifact_descriptor(path, repo_root=ROOT)

    for name, path in direct_paths.items():
        add(name, path)
    for prefix, paths in artifact_groups.items():
        for name, path in paths.items():
            add(f"{prefix}/{name}", path)
    return descriptors


def _paper_artifact_descriptors(
    generation: StagedPublicationGeneration,
) -> dict[str, dict[str, Any]]:
    """Bind staged outputs to their final paper-facing paths."""
    descriptors = {
        f"table/{name}": staged_artifact_descriptor(
            path,
            TABLE_TARGETS[name],
            repo_root=ROOT,
        )
        for name, path in generation.table_paths.items()
    }
    descriptors.update(
        {
            f"figure/{name}/{kind}": staged_artifact_descriptor(
                path,
                generation.figure_targets[name][kind],
                repo_root=ROOT,
            )
            for name, paths in generation.figures.items()
            for kind, path in paths.items()
        }
    )
    return descriptors


def _build_evidence(staging_root: Path, *, promote: bool = True) -> Path:
    registry, registered = load_verified_source_registry(
        SOURCE_REGISTRY_PATH,
        repo_root=ROOT,
    )
    lineages = cast(dict[str, Any], registry["lineages"])
    v4_lineage = cast(dict[str, Any], lineages["binary_geometry"])
    two_ruler_lineage = cast(dict[str, Any], lineages["two_ruler"])
    credit_lineage = cast(dict[str, Any], lineages["credit_controls"])
    diagnostic_lineage = cast(dict[str, Any], lineages["diagnostics"])
    decision_representation_identities = {
        "score_equivalence_complete_hull": cast(
            dict[str, Any], diagnostic_lineage["score_equivalence_complete_hull"]
        ),
        "set_native_binary_robust_counterpart": cast(
            dict[str, Any], diagnostic_lineage["set_native_binary_robust_counterpart"]
        ),
        "dual_coefficient_binary_set_native": cast(
            dict[str, Any], diagnostic_lineage["dual_coefficient_binary_set_native"]
        ),
    }
    decision_representation = load_decision_representation_evidence(
        registered,
        decision_representation_identities,
        repo_root=ROOT,
    )
    score_equivalence_table = score_equivalence_publication_table(
        decision_representation.score_equivalence
    )
    set_native_direction_table = set_native_direction_publication_table(
        decision_representation.set_native
    )
    dual_coefficient_table = dual_coefficient_publication_table(
        decision_representation.dual_coefficient
    )
    binary_phase_census = load_binary_phase_census_evidence(
        registered,
        cast(dict[str, Any], diagnostic_lineage["binary_phase_census"]),
        repo_root=ROOT,
    )
    binary_phase_census_table = binary_phase_census_publication_table(binary_phase_census)
    sensitivities = cast(dict[str, Any], registry["sensitivities"])
    replay_dependencies = cast(dict[str, Any], registry["replay_dependencies"])
    endpoint_lineage = cast(dict[str, Any], sensitivities["endpoint_availability"])
    structural_lineage = cast(dict[str, Any], sensitivities["portfolio_structure"])
    rolling_lineage = cast(dict[str, Any], replay_dependencies["rolling_origin_unequal_followup"])
    rolling_primary_lineage = cast(
        dict[str, Any],
        replay_dependencies["rolling_origin_primary_recovery_unequal_followup"],
    )
    rolling_equal_lineage = cast(
        dict[str, Any], replay_dependencies["rolling_origin_equal_followup_parent"]
    )
    rolling_individual_lineage = cast(
        dict[str, Any], sensitivities["rolling_origin_individual_age_followup"]
    )
    missingness_lineage = cast(dict[str, Any], sensitivities["missingness_encoding"])
    fit_label_lineage = cast(dict[str, Any], sensitivities["fit_label_completion"])
    granularity_lineage = cast(dict[str, Any], sensitivities["allocation_granularity"])
    label_mondrian_lineage = cast(dict[str, Any], sensitivities["label_mondrian"])
    calibrator_lineage = cast(dict[str, Any], sensitivities["calibrator_family"])
    calibrator_evidence = load_calibrator_sensitivity_evidence(
        registered,
        calibrator_lineage,
        repo_root=ROOT,
    )
    calibrator_method_table = calibrator_method_publication_table(calibrator_evidence)
    calibrator_cell_table = calibrator_overall_publication_table(calibrator_evidence)
    calibrator_pairwise_table = calibrator_pairwise_publication_table(calibrator_evidence)
    v4 = _load_v4_inputs(registered, v4_lineage)
    config_path = v4.config_path
    summary_path = v4.summary_path
    v4_receipt_path = v4.receipt_path
    config = v4.config
    summary = v4.summary
    v4_recovery = v4.recovery
    artifacts = v4.artifacts
    freeze_path = v4.freeze_path
    v4_source_freeze_path = v4.source_freeze_path
    source_artifacts = v4.source_artifacts

    two_ruler = _load_two_ruler_inputs(registered, two_ruler_lineage)
    two_ruler_manifest_path = two_ruler.manifest_path
    two_ruler_freeze_path = two_ruler.freeze_path
    two_ruler_summary_path = two_ruler.summary_path
    two_ruler_receipt_path = two_ruler.receipt_path
    two_ruler_evaluation_artifacts = two_ruler.evaluation_artifacts
    two_ruler_source_artifacts = two_ruler.source_artifacts
    two_ruler_summary = two_ruler.summary
    two_ruler_recovery = two_ruler.recovery
    expected_two_ruler_counts = EXPECTED_TWO_RULER_COUNTS

    credit = _load_credit_inputs(registered, credit_lineage)
    credit_summary_path = credit.summary_path
    credit_receipt_path = credit.receipt_path
    credit_summary = credit.summary
    credit_recovery = credit.recovery
    credit_freeze_path = credit.freeze_path
    credit_freeze = credit.freeze
    credit_evaluation_artifacts = credit.evaluation_artifacts
    credit_outcome_free_artifacts = credit.outcome_free_artifacts
    credit_model_artifacts = credit.model_artifacts
    diagnostics = _load_diagnostic_inputs(registered, diagnostic_lineage)
    raw_audit_path = diagnostics.raw_audit_path
    raw_audit = diagnostics.raw_audit
    raw_audit_artifacts = diagnostics.raw_artifacts
    raw_coverage_exceptions = diagnostics.raw_coverage_exceptions
    lag_evidence_path = diagnostics.lag_evidence_path
    lag_evidence = diagnostics.lag_evidence
    lag_table_path = diagnostics.lag_table_path
    lag_table = diagnostics.lag_table
    admissible_lag_table = diagnostics.admissible_lag_table
    nonadmissible_lag_table = diagnostics.nonadmissible_lag_table
    lag_w7_w8 = diagnostics.lag_w7_w8
    tie_evidence_path = diagnostics.tie_evidence_path
    policy_evidence_path = diagnostics.policy_evidence_path
    policy_evidence = diagnostics.policy_evidence
    policy_results = cast(dict[str, Any], policy_evidence["results"])
    policy_status_aware = cast(dict[str, Any], policy_results["status_aware_rhs_semantics"])
    policy_coverage = cast(dict[str, Any], policy_results["rhs_support_coverage"])
    policy_numerical = cast(dict[str, Any], policy_results["numerical_contracts"])
    policy_frozen = cast(
        dict[str, Any],
        policy_results["frozen_allocation_reconciliation"],
    )
    policy_lateral = cast(dict[str, Any], policy_results["corrected_lateral_stability"])
    policy_warnings = cast(dict[str, Any], policy_results["warnings_and_mobility"])
    policy_boundary = cast(dict[str, Any], policy_evidence["claim_boundary"])

    credit_prediction_metrics = credit.prediction_metrics
    credit_temporal_coverage = credit.temporal_coverage
    credit_woe_summary = credit.woe_summary
    credit_feature_psi = credit.feature_psi
    credit_score_psi = credit.score_psi
    credit_feature_variation = credit.feature_variation
    credit_tables = credit.tables

    two_ruler_windows = pd.read_parquet(two_ruler_evaluation_artifacts["window_endpoint_contrasts"])
    two_ruler_monthly = pd.read_parquet(
        two_ruler_evaluation_artifacts["monthly_endpoint_contrasts"]
    )
    two_ruler_directions = pd.read_parquet(
        two_ruler_evaluation_artifacts["metric_direction_census"]
    )
    two_ruler_joined = pd.read_parquet(two_ruler_evaluation_artifacts["joined_funded_allocations"])
    structural_config_path = registered["structural_sensitivity_config"]
    structural_freeze_path = registered["structural_sensitivity_freeze"]
    structural_summary_path = registered["structural_sensitivity_summary"]
    structural_evidence = load_structural_sensitivity_evidence(
        structural_summary_path,
        freeze_path=structural_freeze_path,
        config_path=structural_config_path,
        identity=structural_lineage,
        repo_root=ROOT,
        reference_two_ruler=two_ruler_windows,
    )
    structural_table = structural_publication_table(structural_evidence)

    rolling = _load_rolling_inputs(registered, rolling_lineage)
    rolling_summary_path = rolling.summary_path
    rolling_receipt_path = rolling.receipt_path
    rolling_summary = rolling.summary
    rolling_artifacts = rolling.artifacts
    rolling_primary = _load_rolling_primary_recovery_inputs(
        registered,
        rolling_primary_lineage,
    )
    rolling_primary_summary_path = rolling_primary.summary_path
    rolling_primary_receipt_path = rolling_primary.receipt_path
    rolling_primary_summary = rolling_primary.summary
    rolling_primary_artifacts = rolling_primary.artifacts

    conformal_set_diagnostics = _load_conformal_set_diagnostic_inputs(
        registered,
        cast(dict[str, Any], diagnostic_lineage["conformal_set_diagnostics"]),
    )
    conformal_set_summary_path = conformal_set_diagnostics.summary_path
    conformal_set_receipt_path = conformal_set_diagnostics.receipt_path
    conformal_set_summary = conformal_set_diagnostics.summary
    conformal_set_artifacts = conformal_set_diagnostics.artifacts
    conformal_set_table = conformal_set_diagnostics.table
    conformal_set_publication_table = conformal_set_diagnostics.publication_table

    exchangeability = _load_exchangeability_transport_inputs(
        registered,
        cast(dict[str, Any], diagnostic_lineage["exchangeability_transport_test"]),
    )
    exchangeability_summary_path = exchangeability.summary_path
    exchangeability_receipt_path = exchangeability.receipt_path
    exchangeability_summary = exchangeability.summary
    exchangeability_artifacts = exchangeability.artifacts
    exchangeability_cells = exchangeability.cells
    common_panel = _load_common_panel_threshold_response_inputs(
        registered,
        cast(dict[str, Any], diagnostic_lineage["common_panel_threshold_response"]),
    )
    common_panel_summary_path = common_panel.summary_path
    common_panel_receipt_path = common_panel.receipt_path
    common_panel_config_path = common_panel.config_path
    common_panel_summary = common_panel.summary
    common_panel_artifacts = common_panel.artifacts
    common_panel_strata = common_panel.strata
    common_panel_learners = common_panel.learners
    frontiers = load_frontier_evidence(
        registered,
        diagnostic_lineage,
        repo_root=ROOT,
    )
    equal_followup = _load_equal_followup_inputs(registered, rolling_equal_lineage)
    equal_followup_summary_path = equal_followup.summary_path
    equal_followup_receipt_path = equal_followup.receipt_path
    equal_followup_summary = equal_followup.summary
    equal_followup_artifacts = equal_followup.artifacts
    individual_followup = _load_individual_age_followup_inputs(
        registered, rolling_individual_lineage
    )
    individual_followup_summary_path = individual_followup.summary_path
    individual_followup_receipt_path = individual_followup.receipt_path
    individual_followup_summary = individual_followup.summary
    individual_followup_artifacts = individual_followup.artifacts

    label_mondrian = _load_label_mondrian_inputs(registered, label_mondrian_lineage)
    label_mondrian_summary = label_mondrian.summary

    missingness = _load_missingness_inputs(registered, missingness_lineage)
    missingness_summary_path = missingness.summary_path
    missingness_receipt_path = missingness.receipt_path
    missingness_summary = missingness.summary
    missingness_freeze_path = missingness.freeze_path
    missingness_artifacts = missingness.artifacts
    missingness_freeze_artifacts = missingness.freeze_artifacts
    missingness_model_artifacts = missingness.model_artifacts
    missingness_table = missingness.publication_table
    fit_label_freeze_path = registered["fit_label_completion_freeze"]
    fit_label_summary_path = registered["fit_label_completion_summary"]
    fit_label_evidence = load_fit_label_completion_evidence(
        fit_label_summary_path,
        freeze_path=fit_label_freeze_path,
        identity=fit_label_lineage,
        repo_root=ROOT,
    )
    fit_label_table = fit_label_completion_publication_table(fit_label_evidence)
    granularity_freeze_path = registered["allocation_granularity_freeze"]
    granularity_summary_path = registered["allocation_granularity_summary"]
    granularity_evidence = load_allocation_granularity_evidence(
        granularity_summary_path,
        freeze_path=granularity_freeze_path,
        identity=granularity_lineage,
        repo_root=ROOT,
    )
    granularity_table = allocation_granularity_publication_table(granularity_evidence)
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
    closed_coverage_tables = _closed_coverage_diagnostic_tables(coverage_all)
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
            "fit_score_max",
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
        float_atol=5.0e-14,
        float_rtol=5.0e-14,
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

    endpoint_resolution_table = pd.DataFrame(summary["endpoint_resolution_audit"])
    endpoint_resolution_table = endpoint_resolution_table.loc[
        endpoint_resolution_table["role"].eq("primary_oot")
    ].sort_values("snapshot_resolution")
    expected_endpoint_reasons = {
        "charged_off_by_reconstructed_cutoff",
        "fully_paid_by_reconstructed_cutoff",
        "nonterminal_or_unresolved_status",
        "terminal_after_reconstructed_cutoff",
        "terminal_availability_date_missing",
    }
    if (
        set(endpoint_resolution_table["snapshot_resolution"].astype(str))
        != expected_endpoint_reasons
        or int(endpoint_resolution_table["candidate_rows"].sum()) != 376890
        or int(endpoint_resolution_table["resolved_rows"].sum()) != 364814
        or int(endpoint_resolution_table["unresolved_rows"].sum()) != 12076
    ):
        raise RuntimeError("The primary endpoint-reason census changed.")
    rolling_individual_coverage = individual_followup.publication_coverage.copy()
    rolling_table_columns = [
        "origin_id",
        "origin",
        "origin_year",
        "window",
        "window_id",
        "evaluation_cutoff_min",
        "evaluation_cutoff_max",
        "individual_followup_months",
        "candidate_rows",
        "resolved_rows",
        "unresolved_rows",
        "coverage_resolved",
        "coverage_lower",
        "coverage_upper",
        "mean_width",
    ]
    rolling_table = rolling_individual_coverage[rolling_table_columns].copy()
    require_exact_grid(
        rolling_table,
        domains={
            "origin_id": ("primary_2016", "rolling_2017"),
            "window": WINDOW_ORDINALS,
        },
        label="individual-age two-origin rolling coverage",
    )
    if (
        len(rolling_table) != 16
        or not rolling_table["coverage_upper"].lt(0.90).all()
        or not rolling_table["individual_followup_months"].eq(39).all()
    ):
        raise RuntimeError("The individual-age retrospective recurrence contract changed.")

    fit_coverage = (
        fit_audit.loc[fit_audit["taxonomy_groups"].eq(5)]
        .groupby(["learner", "window_id"], observed=True)["covered"]
        .mean()
        .rename("fit_coverage")
        .reset_index()
    )
    diagnostic_columns = [
        "learner",
        "window_id",
        "coverage_resolved_y0",
        "coverage_resolved_y1",
        "average_set_size",
        "singleton_share",
    ]
    coverage_table = coverage.merge(
        fit_coverage,
        on=["learner", "window_id"],
        how="left",
        validate="one_to_one",
    ).merge(
        conformal_set_table.loc[
            conformal_set_table["learner"].isin(("catboost_platt", "numeric_logistic_platt")),
            diagnostic_columns,
        ],
        on=["learner", "window_id"],
        how="left",
        validate="one_to_one",
    )
    require_finite(
        coverage_table,
        (
            "coverage_resolved_y0",
            "coverage_resolved_y1",
            "average_set_size",
            "singleton_share",
        ),
        label="paper-facing coverage and set diagnostics",
    )
    conformal_config = v4.config.get("conformal")
    if not isinstance(conformal_config, Mapping):
        raise TypeError("The active V4 conformal configuration is not a mapping.")
    phase_table = _phase_transition_publication_table(
        phase,
        alpha=float(conformal_config["alpha"]),
    )
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

    publication_generation = _stage_publication_generation(
        staging_root,
        tables={
            "coverage": coverage_table,
            "phase_transition": phase_table,
            "development_envelopes": development_envelopes,
            "direction_summary": direction_table,
            "two_ruler_tracks": two_ruler_table,
            "named_comparators": named_table,
            "credit_controls": credit_tables["credit_controls"],
            "credit_prediction_metrics": credit_tables["credit_prediction_metrics"],
            "calibrator_fit_diagnostics": calibrator_method_table,
            "woe_iv_psi": credit_tables["woe_iv_psi"],
            "score_psi": credit_tables["score_psi"],
            "label_lag_sensitivity": lag_table.sort_values(["charged_off_lag_months", "window_id"]),
            "endpoint_availability_sensitivity": endpoint_table,
            "portfolio_structure_sensitivity": structural_table,
            "endpoint_resolution": endpoint_resolution_table,
            "missingness_encoding": missingness_table,
            "rolling_origin": rolling_table,
            "conformal_set_diagnostics": conformal_set_publication_table,
            "exchangeability_cells": exchangeability.publication_cells,
            "exchangeability_strata": exchangeability.publication_strata,
            "label_mondrian_cells": label_mondrian.publication_cells,
            "label_mondrian_strata": label_mondrian.publication_strata,
            "label_mondrian_categories": label_mondrian.publication_categories,
            "taxonomy_diagnostics": closed_coverage_tables["taxonomy_diagnostics"],
            "censored_extension_coverage": closed_coverage_tables["censored_extension_coverage"],
            "rolling_individual_age_census": individual_followup.publication_census,
            "fit_label_completion": fit_label_table,
            "allocation_granularity": granularity_table,
            "common_panel_threshold_response_strata": common_panel.publication_strata,
            "common_panel_threshold_response_learners": common_panel.publication_learners,
            "residual_transport_summary": (
                frontiers.residual_transport.publication_tables["summary"]
            ),
            "residual_transport_pooled": (
                frontiers.residual_transport.publication_tables["pooled"]
            ),
            "marginal_score_outcome_gap": (
                frontiers.marginal_score_outcome_gap.publication_tables["gap"]
            ),
            "calibrator_sensitivity_cells": calibrator_cell_table,
            "calibrator_pairwise_shared_completion": calibrator_pairwise_table,
            "decision_catalog_metric_separation": (
                frontiers.decision_catalog_transport.publication_tables["metric_separation"]
            ),
            "decision_catalog_target_blocks": (
                frontiers.decision_catalog_transport.publication_tables["target_blocks"]
            ),
            "funded_selection_track_estimands": (
                frontiers.funded_selection_estimands.publication_tables["track_estimands"]
            ),
            "funded_selection_gamma_contrasts": (
                frontiers.funded_selection_estimands.publication_tables["gamma_contrasts"]
            ),
            "set_preserving_embedding_allocation_summary": (
                frontiers.set_preserving_embedding.publication_tables["allocation_summary"]
            ),
            "set_preserving_embedding_direction_census": (
                frontiers.set_preserving_embedding.publication_tables["direction_census"]
            ),
            "score_equivalence_complete_hull": score_equivalence_table,
            "set_native_robust_minus_embedding": set_native_direction_table,
            "binary_phase_census": binary_phase_census_table,
            "dual_coefficient_binary_set_native": dual_coefficient_table,
        },
        coverage=credit_temporal_coverage,
        exchangeability_cells=exchangeability_cells,
        phase=phase_table,
        development_envelopes=development_envelopes,
        common_panel_threshold_response=common_panel_strata,
    )

    c2 = solve_records.loc[solve_records["comparator_rule"].eq("c2_contemporaneous")]
    broad = envelopes.loc[envelopes["scope"].eq("broad_stress_exact_frontier")]
    w8_development = development_envelopes.loc[
        development_envelopes["window_id"].eq("w08_2012m08_2013m01")
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
        phase_table,
        key={"window_id": "w07_2012m07_m12"},
        label="binary phase transition W7",
    )
    phase_w8 = require_unique_row(
        phase_table,
        key={"window_id": "w08_2012m08_2013m01"},
        label="binary phase transition W8",
    )
    endpoint_by_reason = endpoint_resolution_table.set_index("snapshot_resolution")
    structural_artifacts = _verified_artifact_paths(
        cast(Mapping[str, Mapping[str, Any]], structural_evidence.summary["artifacts"])
    )
    source_artifact_descriptors = _publication_source_descriptors(
        direct_paths={
            "config": config_path,
            "outcome_free/source_protocol_freeze": v4_source_freeze_path,
            "freeze": freeze_path,
            "summary": summary_path,
            "execution_receipt": v4_receipt_path,
            **{
                f"calibrator_family/{name.removeprefix('calibrator_sensitivity_')}": (
                    registered[name]
                )
                for name in CALIBRATOR_SOURCE_KEYS
            },
            **{
                f"decision_representation/{name}": registered[name]
                for name in DECISION_REPRESENTATION_SOURCE_KEYS
            },
            **{
                f"binary_phase_census/{name}": registered[name]
                for name in BINARY_PHASE_CENSUS_SOURCE_KEYS
            },
            "two_ruler/outcome_free/freeze": two_ruler_freeze_path,
            "two_ruler/manifest": two_ruler_manifest_path,
            "two_ruler/summary": two_ruler_summary_path,
            "two_ruler/execution_receipt": two_ruler_receipt_path,
            "credit_controls/summary": credit_summary_path,
            "credit_controls/execution_receipt": credit_receipt_path,
            "credit_controls/freeze": credit_freeze_path,
            "raw_data_audit/manifest": raw_audit_path,
            "label_lag_sensitivity/manifest": lag_evidence_path,
            "label_lag_sensitivity/table": lag_table_path,
            "endpoint_availability_sensitivity/summary": endpoint_summary_path,
            "portfolio_structure_sensitivity/config": structural_config_path,
            "portfolio_structure_sensitivity/freeze": structural_freeze_path,
            "portfolio_structure_sensitivity/summary": structural_summary_path,
            "rolling_origin/summary": rolling_summary_path,
            "rolling_origin/execution_receipt": rolling_receipt_path,
            "rolling_origin/outcome_free_freeze": rolling.freeze_path,
            "rolling_origin/outcome_free_scores": rolling.score_path,
            "rolling_origin_primary_recovery/summary": rolling_primary_summary_path,
            "rolling_origin_primary_recovery/execution_receipt": (rolling_primary_receipt_path),
            "conformal_set_diagnostics/summary": conformal_set_summary_path,
            "conformal_set_diagnostics/execution_receipt": conformal_set_receipt_path,
            "exchangeability_transport/summary": exchangeability_summary_path,
            "exchangeability_transport/config": registered["exchangeability_transport_config"],
            "exchangeability_transport/execution_receipt": exchangeability_receipt_path,
            "common_panel_threshold_response/summary": common_panel_summary_path,
            "common_panel_threshold_response/config": common_panel_config_path,
            "common_panel_threshold_response/execution_receipt": common_panel_receipt_path,
            "common_panel_threshold_response/protocol": ROOT
            / "docs/research/ijds_common_panel_threshold_response_v8_protocol_2026-07-26.md",
            "common_panel_threshold_response/runner": ROOT
            / "scripts/experiments/run_ijds_common_panel_threshold_response_v8.py",
            "common_panel_threshold_response/implementation": ROOT
            / "src/ijds_audit/common_panel_threshold_response.py",
            "residual_transport_frontier/config": (frontiers.residual_transport.config_path),
            "residual_transport_frontier/summary": (frontiers.residual_transport.summary_path),
            "residual_transport_frontier/execution_receipt": (
                frontiers.residual_transport.receipt_path
            ),
            "residual_transport_frontier/protocol": (frontiers.residual_transport.protocol_path),
            "residual_transport_frontier/runner": (frontiers.residual_transport.runner_path),
            "residual_transport_frontier/implementation": (
                frontiers.residual_transport.implementation_path
            ),
            "marginal_score_outcome_gap/config": (frontiers.marginal_score_outcome_gap.config_path),
            "marginal_score_outcome_gap/summary": (
                frontiers.marginal_score_outcome_gap.summary_path
            ),
            "marginal_score_outcome_gap/execution_receipt": (
                frontiers.marginal_score_outcome_gap.receipt_path
            ),
            "marginal_score_outcome_gap/protocol": (
                frontiers.marginal_score_outcome_gap.protocol_path
            ),
            "marginal_score_outcome_gap/runner": (frontiers.marginal_score_outcome_gap.runner_path),
            "marginal_score_outcome_gap/implementation": (
                frontiers.marginal_score_outcome_gap.implementation_path
            ),
            "decision_catalog_transport/config": (frontiers.decision_catalog_transport.config_path),
            "decision_catalog_transport/summary": (
                frontiers.decision_catalog_transport.summary_path
            ),
            "decision_catalog_transport/execution_receipt": (
                frontiers.decision_catalog_transport.receipt_path
            ),
            "decision_catalog_transport/protocol": (
                frontiers.decision_catalog_transport.protocol_path
            ),
            "decision_catalog_transport/runner": (frontiers.decision_catalog_transport.runner_path),
            "decision_catalog_transport/implementation": (
                frontiers.decision_catalog_transport.implementation_path
            ),
            "funded_selection_estimands/config": (frontiers.funded_selection_estimands.config_path),
            "funded_selection_estimands/summary": (
                frontiers.funded_selection_estimands.summary_path
            ),
            "funded_selection_estimands/execution_receipt": (
                frontiers.funded_selection_estimands.receipt_path
            ),
            "funded_selection_estimands/protocol": (
                frontiers.funded_selection_estimands.protocol_path
            ),
            "funded_selection_estimands/runner": (frontiers.funded_selection_estimands.runner_path),
            "funded_selection_estimands/implementation": (
                frontiers.funded_selection_estimands.implementation_path
            ),
            "set_preserving_embedding/config": frontiers.set_preserving_embedding.config_path,
            "set_preserving_embedding/base_config": registered[
                "set_preserving_embedding_base_config"
            ],
            "set_preserving_embedding/protocol": (frontiers.set_preserving_embedding.protocol_path),
            "set_preserving_embedding/v1c_no_go": registered["set_preserving_embedding_v1c_no_go"],
            "set_preserving_embedding/runner": frontiers.set_preserving_embedding.runner_path,
            "set_preserving_embedding/implementation": (
                frontiers.set_preserving_embedding.implementation_path
            ),
            "rolling_origin_equal_followup/summary": equal_followup_summary_path,
            "rolling_origin_equal_followup/config": registered["rolling_equal_followup_config"],
            "rolling_origin_equal_followup/execution_receipt": equal_followup_receipt_path,
            "rolling_origin_individual_age_followup/summary": (individual_followup_summary_path),
            "rolling_origin_individual_age_followup/config": registered[
                "rolling_individual_age_followup_config"
            ],
            "rolling_origin_individual_age_followup/execution_receipt": (
                individual_followup_receipt_path
            ),
            "label_mondrian/outcome_free/freeze": label_mondrian.freeze_path,
            "label_mondrian/outcome_free/config": registered["label_mondrian_freeze_config"],
            "label_mondrian/outcome_free/execution_receipt": (label_mondrian.freeze_receipt_path),
            "label_mondrian/evaluation/summary": label_mondrian.summary_path,
            "label_mondrian/evaluation/config": registered["label_mondrian_evaluation_config"],
            "label_mondrian/evaluation/execution_receipt": label_mondrian.receipt_path,
            "missingness_encoding/summary": missingness_summary_path,
            "missingness_encoding/execution_receipt": missingness_receipt_path,
            "missingness_encoding/freeze": missingness_freeze_path,
            "fit_label_completion/freeze": fit_label_freeze_path,
            "fit_label_completion/summary": fit_label_summary_path,
            "allocation_granularity/freeze": granularity_freeze_path,
            "allocation_granularity/summary": granularity_summary_path,
            "solver_tie_audit/manifest": tie_evidence_path,
            "policy_support_optimal_face/manifest": policy_evidence_path,
        },
        artifact_groups={
            "outcome_free": source_artifacts,
            "evaluation": _without_simulation_artifacts(artifacts),
            "two_ruler/outcome_free": two_ruler_source_artifacts,
            "two_ruler/evaluation": two_ruler_evaluation_artifacts,
            "credit_controls/outcome_free": credit_outcome_free_artifacts,
            "credit_controls/models": credit_model_artifacts,
            "credit_controls/evaluation": credit_evaluation_artifacts,
            "raw_data_audit": raw_audit_artifacts,
            "endpoint_availability_sensitivity": endpoint_sensitivity_artifacts,
            "portfolio_structure_sensitivity": structural_artifacts,
            "rolling_origin": _without_simulation_artifacts(rolling_artifacts),
            "rolling_origin_primary_recovery": rolling_primary_artifacts,
            "conformal_set_diagnostics": conformal_set_artifacts,
            "exchangeability_transport": exchangeability_artifacts,
            "common_panel_threshold_response": common_panel_artifacts,
            "residual_transport_frontier": frontiers.residual_transport.artifacts,
            "marginal_score_outcome_gap": (frontiers.marginal_score_outcome_gap.artifacts),
            "decision_catalog_transport": (frontiers.decision_catalog_transport.artifacts),
            "funded_selection_estimands": frontiers.funded_selection_estimands.artifacts,
            "set_preserving_embedding": frontiers.set_preserving_embedding.artifacts,
            "rolling_origin_equal_followup": equal_followup_artifacts,
            "rolling_origin_individual_age_followup": individual_followup_artifacts,
            "label_mondrian/outcome_free": label_mondrian.freeze_artifacts,
            "label_mondrian/evaluation": label_mondrian.artifacts,
            "missingness_encoding/evaluation": missingness_artifacts,
            "missingness_encoding/outcome_free": missingness_freeze_artifacts,
            "missingness_encoding/models": missingness_model_artifacts,
            "fit_label_completion/outcome_free": fit_label_evidence.outcome_free_artifacts,
            "fit_label_completion/evaluation": fit_label_evidence.evaluation_artifacts,
            "allocation_granularity/outcome_free": (granularity_evidence.outcome_free_artifacts),
            "allocation_granularity/evaluation": granularity_evidence.evaluation_artifacts,
        },
    )
    extension_rows = closed_coverage_tables["censored_extension_coverage"]
    catboost_extension = extension_rows.loc[extension_rows["learner"].eq("catboost_platt")]
    logistic_extension = extension_rows.loc[extension_rows["learner"].eq("numeric_logistic_platt")]
    catboost_below_windows = set(
        catboost_extension.loc[catboost_extension["coverage_upper"].lt(0.90), "window_id"].astype(
            str
        )
    )
    logistic_below_windows = set(
        logistic_extension.loc[logistic_extension["coverage_upper"].lt(0.90), "window_id"].astype(
            str
        )
    )
    logistic_contains_windows = set(
        logistic_extension.loc[
            logistic_extension["coverage_lower"].le(0.90)
            & logistic_extension["coverage_upper"].ge(0.90),
            "window_id",
        ].astype(str)
    )
    censored_extension_pattern = bool(
        catboost_below_windows == set(WINDOW_IDS)
        and logistic_contains_windows == set(WINDOW_IDS[:6])
        and logistic_below_windows == set(WINDOW_IDS[6:])
    )
    paper_artifact_descriptors = _paper_artifact_descriptors(publication_generation)
    evidence = {
        "schema_version": "2026-08-01.1",
        "status": "active_ijds_v5_phase_and_dual_set_native_paper_facing_evidence",
        "source_registry": {
            "schema_version": str(registry["schema_version"]),
            "status": str(registry["status"]),
            "sources": sorted(registered),
        },
        "lineages": lineages,
        "sensitivities": sensitivities,
        "replay_dependencies": dict(registry.get("replay_dependencies", {})),
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
        "closed_coverage_diagnostics": {
            "taxonomy_scope": "two_v4_learners_by_four_locked_taxonomies_by_eight_windows",
            "extension_scope": "two_v4_learners_by_eight_windows_censored_extension",
            "all_sixty_four_primary_upper_below_nominal": bool(
                len(closed_coverage_tables["taxonomy_diagnostics"]) == 64
                and closed_coverage_tables["taxonomy_diagnostics"]["coverage_upper"].lt(0.90).all()
            ),
            "censored_extension_mixed_stress_pattern": censored_extension_pattern,
            "censored_extension_catboost_below_nominal_windows": sorted(catboost_below_windows),
            "censored_extension_logistic_contains_nominal_windows": sorted(
                logistic_contains_windows
            ),
            "censored_extension_logistic_below_nominal_windows": sorted(logistic_below_windows),
            "taxonomy_rows": closed_coverage_tables["taxonomy_diagnostics"].to_dict(
                orient="records"
            ),
            "taxonomy_summary_rows": closed_coverage_tables["taxonomy_summary"].to_dict(
                orient="records"
            ),
            "censored_extension_rows": closed_coverage_tables[
                "censored_extension_coverage"
            ].to_dict(orient="records"),
            "joint_block_rank_reference_extended_to_these_rows": False,
            "independent_replication_claimed": False,
            "extension_is_primary_oot": False,
        },
        "conformal_set_diagnostics": {
            "scope": "all_five_learners_all_eight_windows_primary_oot",
            "run_tag": str(conformal_set_summary["run_tag"]),
            "protocol_tag": str(conformal_set_summary["protocol_tag"]),
            "protocol_commit": str(conformal_set_summary["protocol_commit"]),
            "learner_window_cells": int(len(conformal_set_table)),
            "all_forty_resolved_y0_coverage_above_y1": bool(
                conformal_set_table["coverage_resolved_y0"]
                .gt(conformal_set_table["coverage_resolved_y1"])
                .all()
            ),
            "resolved_y0_coverage_min": float(conformal_set_table["coverage_resolved_y0"].min()),
            "resolved_y0_coverage_max": float(conformal_set_table["coverage_resolved_y0"].max()),
            "resolved_y1_coverage_min": float(conformal_set_table["coverage_resolved_y1"].min()),
            "resolved_y1_coverage_max": float(conformal_set_table["coverage_resolved_y1"].max()),
            "ranges": list(conformal_set_summary["ranges"]),
            "reference_reconciliation": dict(conformal_set_summary["reference_reconciliation"]),
            "interpretation": {
                **dict(conformal_set_summary["interpretation"]),
                "conditions_on_administrative_resolution": True,
                "unresolved_classes_known": False,
                "all_candidate_label_conditional_coverage_estimated": False,
                "label_mondrian_method": False,
                "fairness_or_equalized_coverage_claim": False,
            },
            "rows": conformal_set_publication_table.to_dict(orient="records"),
        },
        "exchangeability_transport_test": {
            "scope": "five_learners_by_eight_windows_by_five_frozen_score_strata",
            "run_tag": str(exchangeability_summary["run_tag"]),
            "protocol_tag": str(exchangeability_summary["protocol_tag"]),
            "protocol_commit": str(exchangeability_summary["protocol_commit"]),
            "rank_null": {
                **dict(exchangeability_summary["rank_null"]),
                "active_name": "joint_block_exchangeability_of_calibration_and_all_targets",
                "stronger_than_single_future_point_split_conformal_condition": True,
                "rejection_need_not_refute_pointwise_marginal_split_conformal_validity": True,
                "target_target_dependence_or_heterogeneity_can_contribute": True,
            },
            "unresolved_endpoint_rule": dict(exchangeability_summary["unresolved_endpoint_rule"]),
            "multiplicity": {
                **dict(exchangeability_summary["multiplicity"]),
                "active_role": "locked_nominal_reporting_thresholds",
                "would_control_fwer_if_family_fixed_ex_ante": True,
                "family_and_pattern_inspected_before_lock": True,
                "post_selection_fwer_control_claimed": False,
                "study_wide_fwer_control_claimed": False,
            },
            "source_protocol_results": dict(exchangeability_summary["results"]),
            "results": {
                "cells_meeting_locked_nominal_thresholds": int(
                    exchangeability_cells["holm_reject_exchangeability_null"].sum()
                ),
                "interpret_as_post_selection_controlled_rejections": False,
            },
            "cells_meeting_locked_nominal_thresholds": int(
                exchangeability_cells["holm_reject_exchangeability_null"].sum()
            ),
            "thirty_one_of_forty_meet_locked_nominal_thresholds": bool(
                exchangeability_cells["holm_reject_exchangeability_null"].sum() == 31
            ),
            "cells_not_meeting_locked_nominal_thresholds": int(
                (~exchangeability_cells["holm_reject_exchangeability_null"]).sum()
            ),
            "nominal_flags_by_learner": {
                learner: int(
                    exchangeability_cells.loc[
                        exchangeability_cells["learner"].eq(learner),
                        "holm_reject_exchangeability_null",
                    ].sum()
                )
                for learner in CREDIT_LEARNER_ORDER
            },
            "source_protocol_interpretation": dict(exchangeability_summary["interpretation"]),
            "interpretation": {
                "retrospective_after_archive_inspection": True,
                "exploratory_test_implementation_and_pattern_seen_before_lock": True,
                "preregistered": False,
                "confirmatory": False,
                "active_null_is_joint_block_exchangeability": True,
                "usual_single_future_point_condition_tested_directly": False,
                "usual_pointwise_split_conformal_theorem_refuted": False,
                "post_selection_fwer_control_claimed": False,
                "study_wide_fwer_control_claimed": False,
                "locked_threshold_flags_are_confirmatory_rejections": False,
                "nonflag_establishes_exchangeability": False,
                "flag_identifies_cause_of_shift": False,
                "selected_set_or_funded_set_validity": False,
            },
            "cell_rows": exchangeability.publication_cells.to_dict(orient="records"),
            "stratum_rows": exchangeability.publication_strata.to_dict(orient="records"),
        },
        "common_panel_threshold_response": {
            "scope": "five_learners_by_five_score_strata_by_seven_adjacent_transitions",
            "run_tag": str(common_panel_summary["run_tag"]),
            "protocol_tag": str(common_panel_summary["protocol_tag"]),
            "protocol_commit": str(common_panel_summary["protocol_commit"]),
            "retrospective_after_archive_and_v6_inspection": True,
            "preregistered": False,
            "confirmatory": False,
            "fixed_target_panel": True,
            "stratum_rows": int(len(common_panel_strata)),
            "learner_rows": int(len(common_panel_learners)),
            "full_census_and_identities_verified": bool(
                len(common_panel_strata) == 175
                and len(common_panel_learners) == 35
                and common_panel_summary["census"]["full_census_reported_without_selection"] is True
                and common_panel_summary["identities"][
                    "resolved_signed_crossed_band_integer_identity_all_rows"
                ]
                is True
                and common_panel_summary["identities"]["sharp_shared_completion_bounds_all_rows"]
                is True
            ),
            "stratum_sharp_sign_census": {
                "negative": int(common_panel_strata["delta_upper"].lt(0.0).sum()),
                "exactly_zero": int(
                    (
                        common_panel_strata["delta_lower"].eq(0.0)
                        & common_panel_strata["delta_upper"].eq(0.0)
                    ).sum()
                ),
                "positive": int(common_panel_strata["delta_lower"].gt(0.0).sum()),
            },
            "learner_transition_sharp_sign_census": {
                "negative": int(common_panel_learners["delta_upper"].lt(0.0).sum()),
                "exactly_zero": int(
                    (
                        common_panel_learners["delta_lower"].eq(0.0)
                        & common_panel_learners["delta_upper"].eq(0.0)
                    ).sum()
                ),
                "positive": int(common_panel_learners["delta_lower"].gt(0.0).sum()),
            },
            "resolved_delta_rate_range": [
                float(common_panel_strata["resolved_delta_rate"].min()),
                float(common_panel_strata["resolved_delta_rate"].max()),
            ],
            "cellwise_identification_width": {
                "median": float(common_panel_strata["delta_width"].quantile(0.5)),
                "p90": float(common_panel_strata["delta_width"].quantile(0.9)),
                "maximum": float(common_panel_strata["delta_width"].max()),
            },
            "disclosed_w7_w8_catboost_zero_based_group_2": dict(
                common_panel_summary["results"]["disclosed_w7_w8_catboost_stratum_2"]
            ),
            "interpretation": {
                **dict(common_panel_summary["interpretation"]),
                "all_candidate_bounds_use_one_shared_completion_per_loan": True,
                "sharpness_is_cellwise": True,
                "joint_attainability_of_all_cell_endpoints_claimed": False,
                "separate_coverage_bound_subtraction_used": False,
                "stratum_sign_census_is_substantive_discovery": False,
                "threshold_distance_is_a_coverage_bound": False,
                "slope_or_continuity_claimed": False,
                "learner_window_or_stratum_winner_claimed": False,
                "temporal_validity_transferred": False,
                "selected_or_funded_set_validity": False,
            },
            "learner_rows_data": common_panel.publication_learners.to_dict(orient="records"),
            "stratum_rows_data": common_panel.publication_strata.to_dict(orient="records"),
        },
        "binary_phase_census": {
            "scope": "five_learners_by_eight_windows_by_five_frozen_score_strata",
            "run_tag": binary_phase_census.summary["run_tag"],
            "protocol_tag": binary_phase_census.summary["protocol_tag"],
            "protocol_commit": binary_phase_census.summary["protocol_commit"],
            "artifact_tag": diagnostic_lineage["binary_phase_census"]["artifact_tag"],
            "artifact_commit": diagnostic_lineage["binary_phase_census"]["artifact_commit"],
            "complete_census_verified": True,
            **dict(binary_phase_census.findings),
            "rows": binary_phase_census_table.to_dict(orient="records"),
            "interpretation": {
                "retrospective_complete_calibration_grid": True,
                "target_or_evaluation_endpoint_read": False,
                "all_strata_reported_without_selection": True,
                "condition_inapplicability_is_not_failure": True,
                "universal_phase_law_claimed": False,
                "coverage_transport_or_validity_claimed": False,
                "optimization_or_funded_policy_claimed": False,
                "causal_or_prospective_claimed": False,
            },
        },
        "residual_transport_frontier": {
            "scope": "five_learners_by_eight_windows_by_five_strata_primary_oot",
            "run_tag": frontiers.residual_transport.summary["run_tag"],
            "protocol_tag": frontiers.residual_transport.summary["protocol_tag"],
            "protocol_commit": frontiers.residual_transport.summary["protocol_commit"],
            **frontiers.residual_transport.findings,
            "learner_census_rows": frontiers.residual_transport.publication_tables[
                "summary"
            ].to_dict(orient="records"),
            "interpretation": {
                "finite_archive_retrospective_full_census": True,
                "unresolved_completion_extrema_are_cellwise_sharp": True,
                "stochastic_dominance_claimed": False,
                "ks_test_or_p_value_reported": False,
                "exchangeability_or_mechanism_claimed": False,
                "model_ranking_or_winner_claimed": False,
                "joint_endpoint_attainability_claimed": False,
            },
        },
        "marginal_score_outcome_gap": {
            "scope": "five_frozen_learners_complete_primary_oot_candidate_panel",
            "run_tag": frontiers.marginal_score_outcome_gap.summary["run_tag"],
            "protocol_tag": frontiers.marginal_score_outcome_gap.summary["protocol_tag"],
            "protocol_commit": frontiers.marginal_score_outcome_gap.summary["protocol_commit"],
            **frontiers.marginal_score_outcome_gap.findings,
            "learner_rows": frontiers.marginal_score_outcome_gap.publication_tables["gap"].to_dict(
                orient="records"
            ),
            "interpretation": {
                "finite_archive_partial_identification": True,
                "shared_collinear_binary_completion_grid": True,
                "sampling_confidence_interval": False,
                "individual_or_conditional_calibration_claimed": False,
                "model_ranking_or_winner_claimed": False,
                "conformal_mechanism_claimed": False,
                "causal_or_prospective_claimed": False,
            },
        },
        "decision_catalog_transport": {
            "scope": "eleven_development_and_fifteen_target_blocks_by_three_losses",
            "run_tag": frontiers.decision_catalog_transport.summary["run_tag"],
            "protocol_tag": frontiers.decision_catalog_transport.summary["protocol_tag"],
            "protocol_commit": frontiers.decision_catalog_transport.summary["protocol_commit"],
            **frontiers.decision_catalog_transport.findings,
            "metric_rows": frontiers.decision_catalog_transport.publication_tables[
                "metric_separation"
            ].to_dict(orient="records"),
            "target_block_rows": frontiers.decision_catalog_transport.publication_tables[
                "target_blocks"
            ].to_dict(orient="records"),
            "interpretation": {
                "complete_frozen_catalog_retrospective_diagnostic": True,
                "block_object_is_maximum_over_240_policies": True,
                "every_policy_deteriorated_claimed": False,
                "ordering_probability_or_p_value_reported": False,
                "exchangeability_or_temporal_validity_claimed": False,
                "selected_policy_or_winner_claimed": False,
                "causal_or_prospective_claimed": False,
            },
        },
        "funded_selection_estimands": {
            "scope": "ninety_six_fixed_usd25_support_policy_tracks",
            "run_tag": frontiers.funded_selection_estimands.summary["run_tag"],
            "protocol_tag": frontiers.funded_selection_estimands.summary["protocol_tag"],
            "protocol_commit": frontiers.funded_selection_estimands.summary["protocol_commit"],
            **frontiers.funded_selection_estimands.findings,
            "coverage_and_contrast_ranges": dict(
                frontiers.funded_selection_estimands.summary["results"]
            ),
            "interpretation": {
                "fixed_support_shared_completion_contrasts": True,
                "count_vs_dollar_gap_uses_covariance_identity": True,
                "invested_dollar_and_fixed_capital_are_distinct_estimands": True,
                "selected_set_or_funded_set_validity_claimed": False,
                "fcr_or_jomi_guarantee_claimed": False,
                "preferred_weighting_or_policy_claimed": False,
                "joint_sharpness_across_tracks_claimed": False,
            },
        },
        "set_preserving_embedding": {
            "scope": (
                "complete_five_theta_by_five_gamma_by_two_ruler_by_three_coordinate_"
                "eight_window_retrospective_grid"
            ),
            "run_tag": frontiers.set_preserving_embedding.summary["run_tag"],
            "protocol_tag": frontiers.set_preserving_embedding.summary["protocol_tag"],
            "protocol_commit": frontiers.set_preserving_embedding.summary["protocol_commit"],
            "source_artifact_tag": frontiers.set_preserving_embedding.summary[
                "source_artifact_tag"
            ],
            "source_artifact_commit": frontiers.set_preserving_embedding.summary[
                "source_artifact_commit"
            ],
            **frontiers.set_preserving_embedding.findings,
            "allocation_rows": frontiers.set_preserving_embedding.publication_tables[
                "allocation_summary"
            ].to_dict(orient="records"),
            "direction_rows": frontiers.set_preserving_embedding.publication_tables[
                "direction_census"
            ].to_dict(orient="records"),
            "interpretation": {
                "finite_archive_retrospective_postinspection_diagnostic": True,
                "binary_sets_are_identical_over_declared_theta_grid": True,
                "identical_sets_imply_allocation_invariance_claimed": False,
                "outcome_direction_invariant_to_theta_claimed": False,
                "theta_gamma_ruler_coordinate_window_or_policy_selected": False,
                "p_value_or_confirmatory_claimed": False,
                "causal_or_prospective_claimed": False,
                "selected_set_or_funded_set_validity_claimed": False,
            },
        },
        "score_equivalence_complete_hull": {
            "scope": (
                "all_twenty_six_complete_candidate_full_budget_affine_hulls_and_"
                "all_declared_v1d_and_closed_calibrator_score_comparisons"
            ),
            "run_tag": decision_representation.score_equivalence.summary["run_tag"],
            "protocol_tag": decision_representation.score_equivalence.summary["protocol_tag"],
            "protocol_commit": decision_representation.score_equivalence.summary["protocol_commit"],
            "artifact_tag": decision_representation_identities["score_equivalence_complete_hull"][
                "artifact_tag"
            ],
            "artifact_commit": decision_representation_identities[
                "score_equivalence_complete_hull"
            ]["artifact_commit"],
            "complete_census_verified": True,
            **dict(decision_representation.score_equivalence.findings),
            "rows": score_equivalence_table.to_dict(orient="records"),
            "interpretation": {
                "complete_candidate_menu_not_funded_support": True,
                "outcome_free": True,
                "optimization_run": False,
                "failed_certificate_means_fixed_cell_allocation_change": False,
                "common_solver_output_means_equal_optimal_faces": False,
                "calibrator_common_objective_established": False,
                "selected_embedding_or_calibrator": False,
                "selected_or_funded_set_validity_claimed": False,
            },
        },
        "set_native_binary_robust_counterpart": {
            "scope": (
                "complete_nonempty_set_exact_worst_label_with_declared_empty_"
                "set_fail_closure_frontier_and_all_"
                "primary_robust_minus_v1d_embedding_comparisons"
            ),
            "phase_a_run_tag": decision_representation.set_native.phase_a_summary["run_tag"],
            "phase_a_protocol": dict(
                decision_representation.set_native.phase_a_summary["protocol"]
            ),
            "phase_a_artifact_tag": decision_representation_identities[
                "set_native_binary_robust_counterpart"
            ]["outcome_free"]["artifact_tag"],
            "phase_a_artifact_commit": decision_representation_identities[
                "set_native_binary_robust_counterpart"
            ]["outcome_free"]["artifact_commit"],
            "evaluation_run_tag": decision_representation.set_native.evaluation_summary["run_tag"],
            "evaluation_protocol": dict(
                decision_representation.set_native.evaluation_summary["protocol"]
            ),
            "evaluation_artifact_tag": decision_representation_identities[
                "set_native_binary_robust_counterpart"
            ]["evaluation"]["artifact_tag"],
            "evaluation_artifact_commit": decision_representation_identities[
                "set_native_binary_robust_counterpart"
            ]["evaluation"]["artifact_commit"],
            "complete_census_verified": True,
            **dict(decision_representation.set_native.findings),
            "direction_rows": set_native_direction_table.to_dict(orient="records"),
            "interpretation": {
                "set_native_score_uses_exact_binary_worst_label": True,
                "empty_set_is_declared_fail_closed_convention": True,
                "cartesian_product_joint_coverage_guarantee_established": False,
                "probabilistic_robustness_claimed": False,
                "conformal_validity_repair_claimed": False,
                "selected_result_or_policy": False,
                "causal_or_prospective_claimed": False,
                "independent_replications_or_p_value_claimed": False,
            },
        },
        "dual_coefficient_binary_set_native": {
            "scope": (
                "complete_outcome_free_dual_set_native_risk_and_maximin_payoff_"
                "certificate_census_over_all_frozen_primary_catboost_platt_menus"
            ),
            "run_tag": decision_representation.dual_coefficient.summary["run_tag"],
            "protocol": dict(decision_representation.dual_coefficient.summary["protocol"]),
            "artifact_tag": decision_representation_identities[
                "dual_coefficient_binary_set_native"
            ]["artifact_tag"],
            "artifact_commit": decision_representation_identities[
                "dual_coefficient_binary_set_native"
            ]["artifact_commit"],
            "complete_certificate_census_verified": True,
            **dict(decision_representation.dual_coefficient.findings),
            "role_rows": dual_coefficient_table.to_dict(orient="records"),
            "interpretation": {
                "conditional_substitution_theorem": True,
                "both_risk_and_payoff_coefficients_are_set_native": True,
                "empty_set_is_declared_fail_closed_convention": True,
                "continuous_cap_domain_certified": [0.0, 1.0],
                "new_optimization_run": False,
                "true_zero_default_risk_claimed": False,
                "cartesian_product_joint_coverage_guarantee_established": False,
                "probabilistic_robustness_claimed": False,
                "conformal_validity_repair_claimed": False,
                "optimizer_uniqueness_claimed": False,
                "selected_result_or_policy": False,
                "outcome_causal_or_prospective_claimed": False,
            },
        },
        "evaluation_endpoint": {
            **dict(config["target"]["evaluation_outcome_contract"]),
            "role": str(config["source"]["snapshot_date_role"]),
            "terminal_statuses_after_cutoff_reclassified_unresolved": True,
            "primary_oot_candidates": primary_oot_candidates,
            "primary_oot_resolved": primary_oot_resolved,
            "primary_oot_unresolved": primary_oot_unresolved,
            "reason_census": endpoint_resolution_table.to_dict(orient="records"),
            "reason_census_partitions_primary_candidates": bool(
                endpoint_resolution_table["candidate_rows"].sum() == primary_oot_candidates
                and endpoint_resolution_table["resolved_rows"].sum() == primary_oot_resolved
                and endpoint_resolution_table["unresolved_rows"].sum() == primary_oot_unresolved
            ),
            "primary_oot_nonterminal_or_unresolved_status": int(
                endpoint_by_reason.loc["nonterminal_or_unresolved_status", "candidate_rows"]
            ),
            "primary_oot_terminal_after_cutoff": int(
                endpoint_by_reason.loc["terminal_after_reconstructed_cutoff", "candidate_rows"]
            ),
            "primary_oot_terminal_availability_date_missing": int(
                endpoint_by_reason.loc["terminal_availability_date_missing", "candidate_rows"]
            ),
            "missingness_mechanism_identified": False,
            "operational_event_dates_identified": False,
            "recovery_audit": v4_recovery,
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
            "calibrator_family": _calibrator_sensitivity_manifest_payload(
                calibrator_evidence,
                identities=calibrator_lineage,
                method_fit_table=calibrator_method_table,
                cell_table=calibrator_cell_table,
                pairwise_table=calibrator_pairwise_table,
            ),
            "evaluation_endpoint_availability": {
                "scope": "complete_nonselective_retrospective_lag_grid",
                "run_tag": str(endpoint_evidence.summary["run_tag"]),
                "protocol_tag": str(endpoint_evidence.summary["protocol_tag"]),
                "protocol_commit": str(endpoint_evidence.summary["protocol_commit"]),
                "charged_off_lags_months": list(endpoint_evidence.summary["lags"]),
                "endpoint_or_result_selected": False,
                "allocation_refit": False,
                "six_month_endpoint_reconciles_to_active_evaluation": True,
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
            "portfolio_structure": {
                "scope": "complete_nonselective_budget_by_purpose_cap_by_lgd_grid",
                "run_tag": str(structural_evidence.summary["run_tag"]),
                "protocol_tag": str(structural_evidence.summary["protocol_tag"]),
                "protocol_commit": str(structural_evidence.summary["protocol_commit"]),
                "scenario_or_result_selected": False,
                "baseline_reconciles_to_active_evaluation": True,
                **dict(structural_evidence.findings),
                "estimand_boundary": (
                    "This complete retrospective assumption sensitivity changes budget, "
                    "purpose concentration, and LGD without selecting a scenario. Direction "
                    "remains conditional on ruler, coordinate, window, metric, and scenario."
                ),
                "rows": structural_table.to_dict(orient="records"),
            },
            "rolling_origin": {
                "scope": "two_origin_individual_issue_month_age_equalized_retrospective_sensitivity_not_replication",
                "run_tag": str(individual_followup_summary["run_tag"]),
                "protocol_tag": str(individual_followup_summary["protocol_tag"]),
                "protocol_commit": str(individual_followup_summary["protocol_commit"]),
                "origins": ["primary_2016", "rolling_2017"],
                "primary_2016_periods": list(PRIMARY_ROLLING_PERIODS),
                "rolling_2017_periods": list(LATER_ROLLING_PERIODS),
                "primary_2016_census": {
                    "candidate_rows": 74537,
                    "resolved_rows": 73934,
                    "unresolved_rows": 603,
                },
                "rolling_2017_census": {
                    "candidate_rows": 77105,
                    "resolved_rows": 66037,
                    "unresolved_rows": 11068,
                },
                "common_issue_months": ["April", "May", "June"],
                "issue_date_resolution": "calendar_month",
                "individual_followup_months_after_issue_month_end": 39,
                "exact_calendar_month_age_matched": True,
                "exact_day_level_age_matched": False,
                "cutoff_by_issue_period": dict(
                    individual_followup_summary["design"]["cutoffs_by_issue_period"]
                ),
                "window_alignment": "ordinal_W1_through_W8_with_origin_specific_fit_dates",
                "origin_count": 2,
                "window_cells": int(len(rolling_table)),
                "all_sixteen_upper_below_nominal": bool(
                    rolling_table["coverage_upper"].lt(0.90).all()
                ),
                "primary_2016_upper_max": float(
                    rolling_table.loc[
                        rolling_table["origin_id"].eq("primary_2016"), "coverage_upper"
                    ].max()
                ),
                "rolling_2017_upper_max": float(
                    rolling_table.loc[
                        rolling_table["origin_id"].eq("rolling_2017"), "coverage_upper"
                    ].max()
                ),
                "model_or_origin_selected": False,
                "independent_replication_claim_authorized": False,
                "coarser_equal_quarter_followup_retained_as_provenance": {
                    "run_tag": str(equal_followup_summary["run_tag"]),
                    "protocol_tag": str(equal_followup_summary["protocol_tag"]),
                    "all_sixteen_upper_below_nominal": bool(
                        equal_followup.coverage["coverage_upper"].lt(0.90).all()
                    ),
                    "approximate_followup_months_by_issue_month": {
                        "April": 41,
                        "May": 40,
                        "June": 39,
                    },
                },
                "unequal_followup_runs_retained_as_provenance": {
                    "rolling_2017_run_tag": str(rolling_summary["run_tag"]),
                    "primary_2016_recovery_run_tag": str(rolling_primary_summary["run_tag"]),
                },
                "monthly_endpoint_census": individual_followup.publication_census.to_dict(
                    orient="records"
                ),
                "monthly_endpoint_reason_census": (
                    individual_followup.publication_reason_census.to_dict(orient="records")
                ),
                "rows": rolling_table.to_dict(orient="records"),
            },
            "label_mondrian": {
                "scope": "complete_retrospective_label_by_score_stratum_sensitivity",
                "freeze_run_tag": str(label_mondrian_lineage["outcome_free"]["run_tag"]),
                "run_tag": str(label_mondrian_summary["run_tag"]),
                "protocol_tag": str(label_mondrian_summary["protocol_tag"]),
                "protocol_commit": str(label_mondrian_summary["protocol_commit"]),
                "counts": dict(label_mondrian_summary["counts"]),
                "baseline_reconciliation": dict(label_mondrian_summary["baseline_reconciliation"]),
                "learner_window_states": {
                    "robust_shortfall": int(label_mondrian.cells["coverage_upper"].lt(0.90).sum()),
                    "robust_at_or_above_nominal": int(
                        label_mondrian.cells["coverage_lower"].ge(0.90).sum()
                    ),
                    "crosses_nominal": int(
                        (
                            label_mondrian.cells["coverage_lower"].lt(0.90)
                            & label_mondrian.cells["coverage_upper"].ge(0.90)
                        ).sum()
                    ),
                },
                "category_states": dict(
                    label_mondrian_summary["target_categories"]["identification_state_counts"]
                ),
                "twenty_seven_of_forty_marginal_upper_endpoints_below_nominal": bool(
                    label_mondrian.cells["coverage_upper"].lt(0.90).sum() == 27
                ),
                "one_hundred_nine_of_four_hundred_category_upper_endpoints_below_nominal": bool(
                    label_mondrian.categories["coverage_upper_below_nominal"].sum() == 109
                ),
                "mixed_category_identification_states": bool(
                    label_mondrian.categories["identification_state_at_nominal"].nunique() == 3
                ),
                "all_forty_aggregate_class_gap_bounds_cross_zero": bool(
                    label_mondrian.cells["coverage_gap_y0_minus_y1_lower"].le(0.0).all()
                    and label_mondrian.cells["coverage_gap_y0_minus_y1_upper"].ge(0.0).all()
                ),
                "average_set_size_min": float(label_mondrian.cells["average_set_size"].min()),
                "average_set_size_max": float(label_mondrian.cells["average_set_size"].max()),
                "set_both_share_min": float(label_mondrian.cells["set_both_share"].min()),
                "set_both_share_max": float(label_mondrian.cells["set_both_share"].max()),
                "resolved_y0_coverage_min": float(
                    label_mondrian.cells["coverage_resolved_y0"].min()
                ),
                "resolved_y0_coverage_max": float(
                    label_mondrian.cells["coverage_resolved_y0"].max()
                ),
                "resolved_y1_coverage_min": float(
                    label_mondrian.cells["coverage_resolved_y1"].min()
                ),
                "resolved_y1_coverage_max": float(
                    label_mondrian.cells["coverage_resolved_y1"].max()
                ),
                "identification": dict(label_mondrian_summary["identification"]),
                "interpretation": dict(label_mondrian_summary["interpretation"]),
                "cell_rows": label_mondrian.publication_cells.to_dict(orient="records"),
                "stratum_rows": label_mondrian.publication_strata.to_dict(orient="records"),
                "category_rows": label_mondrian.publication_categories.to_dict(orient="records"),
            },
            "missingness_encoding": {
                "scope": ("three_declared_feature_semantics_preserving_catboost_encodings"),
                "run_tag": str(missingness_summary["run_tag"]),
                "protocol_tag": str(missingness_summary["protocol_tag"]),
                "protocol_commit": str(missingness_summary["protocol_commit"]),
                "specifications": list(missingness_summary["specifications"]),
                "all_three_all_eight_upper_below_nominal": bool(
                    missingness_table["all_windows_upper_below_nominal"].all()
                    and missingness_table["windows_with_upper_below_nominal"].eq(8).all()
                ),
                "model_or_encoding_selected": False,
                "missingness_mechanism_identified": False,
                "portfolio_claim_authorized": False,
                "rows": missingness_table.to_dict(orient="records"),
            },
            "fit_label_completion": {
                "scope": "observed_only_plus_three_declared_fit_label_stress_rules",
                "run_tag": str(fit_label_evidence.summary["run_tag"]),
                "protocol_tag": str(fit_label_evidence.summary["protocol_tag"]),
                "protocol_commit": str(fit_label_evidence.summary["protocol_commit"]),
                **dict(fit_label_evidence.findings),
                "scenario_or_result_selected": False,
                "evaluation_outcomes_passed_to_fitting": False,
                "scenarios_are_sharp_bounds_over_all_label_assignments": False,
                "observed_only_active_replay": dict(
                    fit_label_evidence.summary["results"]["observed_only_active_replay"]
                ),
                "estimand_boundary": (
                    "The observed-only fit and three declared stress rules vary 215 fit "
                    "labels that were unavailable at their information cutoffs. Every "
                    "scenario retains "
                    "all eight overall coverage upper bounds below 0.90, but the W7--W8 "
                    "CatBoost S3 crossing fails under the all-default scenario. Nonlinear "
                    "refitting means these scenarios are not sharp bounds over all 2^215 "
                    "label assignments."
                ),
                "rows": fit_label_table.to_dict(orient="records"),
            },
            "allocation_granularity": {
                "scope": "deterministic_usd25_floor_with_residual_cash",
                "run_tag": str(granularity_evidence.summary["run_tag"]),
                "protocol_tag": str(granularity_evidence.summary["protocol_tag"]),
                "protocol_commit": str(granularity_evidence.summary["protocol_commit"]),
                **dict(granularity_evidence.findings),
                "scenario_or_result_selected": False,
                "outcomes_passed_to_rounding": False,
                "integer_policy_or_reoptimization_claim_authorized": False,
                "estimand_boundary": (
                    "This deterministic diagnostic floors each continuous exposure to a "
                    "USD 25 lot and holds the residual as cash. It supports numerical "
                    "adequacy of the continuous relaxation for this archive, not optimality "
                    "of an integer policy or robustness to other lot rules."
                ),
                "rows": granularity_table.to_dict(orient="records"),
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
            "scope": "complete_five_model_finite_archive_coverage_audit",
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
            "endpoint_recovery_audit": credit_recovery,
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
            "alpha": float(conformal_config["alpha"]),
            "w7_fit_rows": int(phase_w7["fit_rows"]),
            "w8_fit_rows": int(phase_w8["fit_rows"]),
            "w7_fit_default_rows": int(phase_w7["fit_default_rows"]),
            "w8_fit_default_rows": int(phase_w8["fit_default_rows"]),
            "w7_fit_prevalence": float(phase_w7["fit_prevalence"]),
            "w8_fit_prevalence": float(phase_w8["fit_prevalence"]),
            "w7_finite_sample_rank": int(phase_w7["finite_sample_rank"]),
            "w8_finite_sample_rank": int(phase_w8["finite_sample_rank"]),
            "w7_finite_phase_allowance": int(phase_w7["finite_phase_allowance"]),
            "w8_finite_phase_allowance": int(phase_w8["finite_phase_allowance"]),
            "w7_phase_margin": int(phase_w7["phase_margin"]),
            "w8_phase_margin": int(phase_w8["phase_margin"]),
            "w7_phase_boundary_rate": float(phase_w7["phase_boundary_rate"]),
            "w8_phase_boundary_rate": float(phase_w8["phase_boundary_rate"]),
            "calibration_scores_below_half_all_windows": bool(
                phase_table["calibration_scores_below_half"].all()
            ),
            "w7_calibration_score_max": float(phase_w7["fit_score_max"]),
            "w8_calibration_score_max": float(phase_w8["fit_score_max"]),
            "w7_threshold_branch": (
                f"one_minus_{int(phase_w7['phase_margin'])}th_largest_default_score"
            ),
            "w8_fit_nondefault_rows": int(phase_w8["fit_rows"] - phase_w8["fit_default_rows"]),
            "w8_threshold_branch": (
                f"{int(phase_w8['finite_sample_rank'])}th_smallest_of_"
                f"{int(phase_w8['fit_rows'] - phase_w8['fit_default_rows'])}_"
                "nondefault_scores"
            ),
            "w8_target_score_max": float(phase_w8["score_max"]),
            "w8_positive_label_coverage_boundary": float(1.0 - phase_w8["fit_residual_quantile"]),
            "w8_all_target_scores_below_positive_label_coverage_boundary": bool(
                phase_w8["score_max"] < 1.0 - phase_w8["fit_residual_quantile"]
            ),
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
            "registered_cap_values_all_envelopes_include_zero": bool(
                broad["direction"].eq("crosses_zero").all()
            ),
            "broad_stress_cells": int(len(broad)),
            "development_direction_counts": direction_table.to_dict(orient="records"),
            "w8_development_all_envelopes_cross_zero": bool(
                w8_development["direction"].eq("crosses_zero").all()
            ),
            "named_direction_counts": named_table.to_dict(orient="records"),
            "policy_support_rhs_semantics": {
                "scope": (
                    "retrospective_outcome_free_active_upper_solver_reported_rhs_ranges_"
                    "plus_analytically_derived_zero_dual_basic_row_safe_rays_and_196_"
                    "v2_midpoint_seeds_retrospectively_registered_in_v3a_at_absolute_"
                    "tolerance_1e_10"
                ),
                "source_role": str(policy_evidence["publication_role"]),
                "v2_run_tag": str(policy_evidence["lineage"]["v2"]["run_tag"]),
                "v3a_run_tag": str(policy_evidence["lineage"]["v3a"]["run_tag"]),
                "central_rows": int(policy_status_aware["rows"]),
                "upper_status_rows": int(policy_status_aware["upper_rows"]),
                "basic_status_rows": int(policy_status_aware["basic_rows"]),
                "v2_semantic_false_failures": int(
                    policy_status_aware["v2_reported_domain_clipped_cap_containment_failures"]
                ),
                "status_aware_cap_containment_passes": int(
                    policy_status_aware["status_aware_cap_containment_passes"]
                ),
                "registered_support_lower": float(policy_coverage["registered_support_lower"]),
                "registered_support_upper": float(policy_coverage["registered_support_upper"]),
                "absolute_gap_tolerance": float(policy_coverage["absolute_gap_tolerance"]),
                "initial_positive_gaps": int(policy_coverage["initial_positive_gaps"]),
                "registered_gap_seed_solves": int(policy_coverage["registered_gap_seed_solves"]),
                "upper_status_gap_seed_solves": int(
                    policy_coverage["upper_status_gap_seed_solves"]
                ),
                "basic_status_gap_seed_solves": int(
                    policy_coverage["basic_status_gap_seed_solves"]
                ),
                "strictly_interior_gap_seed_solves": int(
                    policy_coverage["strictly_interior_gap_seed_solves"]
                ),
                "maximum_seed_midpoint_match_distance": float(
                    policy_coverage["maximum_seed_midpoint_match_distance"]
                ),
                "maximum_v2_seed_expected_objective_difference": float(
                    policy_coverage["maximum_v2_seed_expected_objective_difference"]
                ),
                "maximum_v2_seed_weighted_point_difference": float(
                    policy_coverage["maximum_v2_seed_weighted_point_difference"]
                ),
                "status_aware_seed_cap_containment_passes": int(
                    policy_coverage["status_aware_seed_cap_containment_passes"]
                ),
                "recomputed_target_gap_coverage_passes": int(
                    policy_coverage["recomputed_target_gap_coverage_passes"]
                ),
                "covered_periods": int(policy_coverage["covered_periods"]),
                "zero_tolerance_positive_seams": int(
                    policy_coverage["zero_tolerance_positive_seams"]
                ),
                "maximum_zero_tolerance_seam_width": float(
                    policy_coverage["maximum_zero_tolerance_seam_width"]
                ),
                "total_zero_tolerance_seam_width": float(
                    policy_coverage["total_zero_tolerance_seam_width"]
                ),
                "positive_gaps_at_1e_15": int(policy_coverage["positive_gaps_at_1e_15"]),
                "rhs_support_coverage_gate_passed": bool(
                    policy_coverage["rhs_support_coverage_gate_passed"]
                ),
                "freeze_reconciliation_rows": int(policy_frozen["rows"]),
                "freeze_reconciliation_passes": int(policy_frozen["passed_rows"]),
                "freeze_reconciliation_gate_passed": bool(
                    policy_frozen["frozen_allocation_reconciliation_gate_passed"]
                ),
                "all_basis_dual_feasibility_contracts_passed": bool(
                    all(
                        contract.get(
                            "numerical_contract_passed",
                            contract.get("row_contract_passed"),
                        )
                        is True
                        for contract in policy_numerical.values()
                    )
                ),
                "lateral_breakpoint_rows": int(policy_lateral["breakpoint_rows"]),
                "lateral_probe_paths": int(policy_numerical["v2_lateral_probes"]["rows"]),
                "lateral_allocation_difference_rows": int(
                    policy_lateral["allocation_difference_rows"]
                ),
                "maximum_pairwise_allocation_distance": float(
                    policy_lateral["maximum_pairwise_allocation_distance"]
                ),
                "corrected_lateral_gate_passed": bool(
                    policy_lateral["corrected_lateral_gate_passed"]
                ),
                "v2_warning_rows": int(policy_warnings["v2_warning_rows"]),
                "v2_unique_warning_targets": int(policy_warnings["v2_unique_cap_variable_targets"]),
                "v3a_gap_seed_warning_rows": int(policy_warnings["v3a_gap_seed_warning_rows"]),
                "v3a_warning_repeats_same_v2_variable_at_both_neighbor_endpoints": bool(
                    policy_warnings[
                        "v3a_warning_repeats_same_v2_variable_at_both_neighbor_endpoints"
                    ]
                ),
                "maximum_coordinate_exposure_mobility_dollars": float(
                    policy_warnings["maximum_v2_coordinate_exposure_mobility_dollars"]
                ),
                "strict_numerical_uniqueness_gate_passed": bool(
                    policy_warnings["strict_numerical_uniqueness_gate_passed"]
                ),
                "rhs_coverage_recovered_without_uniqueness_promotion": bool(
                    policy_results["rhs_coverage_recovered_without_uniqueness_promotion"]
                ),
                "epsilon_mobility_is_exact_nonuniqueness_evidence": bool(
                    policy_boundary["epsilon_mobility_is_exact_nonuniqueness_evidence"]
                ),
                "exact_symbolic_optimal_face_claim_active": bool(
                    policy_boundary["exact_symbolic_optimal_face_claim_active"]
                ),
                "exact_nonuniqueness_claim_active": bool(
                    policy_boundary["exact_nonuniqueness_claim_active"]
                ),
                "allocation_continuity_claim_active": bool(
                    policy_boundary["allocation_continuity_or_seam_conditioning_claim_active"]
                ),
                "continuous_outcome_envelope_claim_active": bool(
                    policy_boundary[
                        "exact_continuous_outcome_envelope_over_all_optimal_allocations_claim_active"
                    ]
                ),
                "permissible_conclusion": str(policy_boundary["permissible_conclusion"]),
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
            "endpoint_recovery_audit": two_ruler_recovery,
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
        "audit_thesis": (
            "All 40 finite-archive sharp coverage upper endpoints are below 0.90 under the "
            "active six-month endpoint; this deterministic completion statement is not by "
            "itself a rejection of conformal validity. A separate retrospectively locked "
            "joint-block rank-reference diagnostic places 31 of 40 learner-window cells past "
            "the locked nominal Bonferroni--Holm thresholds. Its null is stronger than the "
            "usual single-future-point split-conformal condition, and the post-inspection "
            "family has no selective-FWER claim. The CatBoost shortfall recurs "
            "at two origins with cutoffs 39 months after each issue-month end, under three missing-value "
            "encodings, and under four declared fit-label scenarios. A complete label-Mondrian "
            "sensitivity redistributes resolved coverage from nondefault toward default but "
            "leaves 27 of 40 learner-window and 109 of 400 label-stratum upper endpoints below "
            "0.90 while expanding two-label sets to 72.4%--78.5%; it is not a restored "
            "transport guarantee. A "
            "clean calibration-only census reconciles the exact threshold geometry in all "
            "200 learner-window-stratum cells, with 87 below-half thresholds distributed "
            "40/40/7/0/0 across ordered strata; it supplies no target or transport claim. A "
            "prevalence-threshold crossing explains one observed geometry change but is "
            "not invariant to every fit-label scenario. Portfolio direction is not identified "
            "without outcome-free comparator support and is not invariant to the declared "
            "ruler or interior coordinate; USD 25 floor rounding produces only negligible "
            "rate perturbations in the evaluated archive. Status-aware numerical basis "
            "intervals leave no registered support gap above 1e-10, but scale-aware warnings "
            "block any exact or strict numerical uniqueness conclusion. A conditional "
            "dual-coefficient theorem and 208 outcome-free menu certificates show that the "
            "maximin full optimal face collapses to singleton-zero support over the "
            "continuous cap domain [0,1]; this is decision algebra, not true zero risk, "
            "joint conformal validity, outcome dominance, or a selected policy."
        ),
        "source_artifacts": source_artifact_descriptors,
        "paper_artifacts": paper_artifact_descriptors,
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
    if promote:
        promote_publication_generation(
            publication_generation.outputs,
            staged_manifest=staged_manifest,
            manifest_target=EVIDENCE_PATH,
            repo_root=ROOT,
            transaction_root=staging_root,
        )
        logger.info("Built one transactional active IJDS evidence generation: {}", EVIDENCE_PATH)
        return EVIDENCE_PATH
    logger.info("Staged active IJDS evidence without promotion: {}", staged_manifest)
    return staged_manifest


def build_evidence(*, stage_only_root: Path | None = None) -> Path:
    """Build one complete generation, optionally without promoting it."""
    if stage_only_root is not None:
        resolved = stage_only_root.resolve()
        try:
            resolved.relative_to(ROOT)
        except ValueError as exc:
            raise ValueError("Stage-only output must remain inside the repository.") from exc
        if resolved.exists() and any(resolved.iterdir()):
            raise FileExistsError(f"Stage-only output is not empty: {resolved}")
        resolved.mkdir(parents=True, exist_ok=True)
        return _build_evidence(resolved, promote=False)

    staging_parent = ROOT / "reports/crpto"
    staging_parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".ijds-v4-generation-", dir=staging_parent) as staging:
        return _build_evidence(Path(staging))


def promote_staged_evidence(stage_root: Path) -> Path:
    """Promote a verified retained generation while preserving target DACLs."""
    resolved = stage_root.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("Staged promotion input must remain inside the repository.") from exc
    staged_manifest = resolved / "outputs" / EVIDENCE_PATH.relative_to(ROOT)
    if not staged_manifest.is_file():
        raise FileNotFoundError(f"Staged publication manifest is missing: {staged_manifest}")
    manifest = _read_json(staged_manifest, label="Staged publication manifest")
    paper_artifacts = manifest.get("paper_artifacts")
    source_artifacts = manifest.get("source_artifacts")
    if not isinstance(paper_artifacts, Mapping) or not isinstance(source_artifacts, Mapping):
        raise TypeError("Staged publication manifest omits artifact descriptor mappings.")

    figure_targets = {
        name: {kind: FIGURE_DIR / f"{FIGURE_STEMS[name]}.{kind}" for kind in ("png", "pdf")}
        for name in FIGURE_STEMS
    }
    targets = (
        *TABLE_TARGETS.values(),
        *(target for group in figure_targets.values() for target in group.values()),
    )
    expected_artifact_count = len(TABLE_TARGETS) + 2 * len(FIGURE_STEMS)
    if len(targets) != expected_artifact_count or len(set(targets)) != expected_artifact_count:
        raise RuntimeError("The canonical staged-promotion inventory changed.")
    outputs = {target: resolved / "outputs" / target.relative_to(ROOT) for target in targets}
    expected_paths = {target.relative_to(ROOT).as_posix() for target in targets}
    actual_paths = {
        str(descriptor.get("path"))
        for descriptor in paper_artifacts.values()
        if isinstance(descriptor, Mapping)
    }
    if actual_paths != expected_paths or len(paper_artifacts) != expected_artifact_count:
        raise RuntimeError(
            "The staged manifest left the exact "
            f"{expected_artifact_count}-artifact paper inventory."
        )
    descriptors_by_path = {
        str(descriptor["path"]): descriptor
        for descriptor in paper_artifacts.values()
        if isinstance(descriptor, Mapping)
    }
    for target, staged in outputs.items():
        actual = staged_artifact_descriptor(staged, target, repo_root=ROOT)
        if actual != descriptors_by_path[actual["path"]]:
            raise RuntimeError(f"Staged paper artifact drifted after generation: {staged}")

    for name, descriptor in source_artifacts.items():
        if not isinstance(descriptor, Mapping) or not {"path", "bytes", "sha256"}.issubset(
            descriptor
        ):
            raise TypeError(f"Staged source descriptor is invalid: {name!r}.")
        source = (ROOT / str(descriptor["path"])).resolve()
        source.relative_to(ROOT)
        if relative_artifact_descriptor(source, repo_root=ROOT) != dict(descriptor):
            raise RuntimeError(f"A staged-evidence source drifted before promotion: {name!r}.")

    promote_publication_generation(
        outputs,
        staged_manifest=staged_manifest,
        manifest_target=EVIDENCE_PATH,
        repo_root=ROOT,
        transaction_root=resolved,
        preserve_target_permissions=True,
    )
    logger.info("Promoted retained IJDS evidence while preserving target permissions: {}", resolved)
    return EVIDENCE_PATH


def verify_staged_evidence_matches_canonical(stage_root: Path) -> Path:
    """Require a clean rebuild to match every canonical publication byte."""
    resolved = stage_root.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("Staged verification input must remain inside the repository.") from exc
    staged_outputs = resolved / "outputs"
    staged_manifest = staged_outputs / EVIDENCE_PATH.relative_to(ROOT)
    if not staged_manifest.is_file():
        raise FileNotFoundError(f"Staged publication manifest is missing: {staged_manifest}")
    if not EVIDENCE_PATH.is_file():
        raise FileNotFoundError(f"Canonical publication manifest is missing: {EVIDENCE_PATH}")
    if staged_manifest.read_bytes() != EVIDENCE_PATH.read_bytes():
        raise RuntimeError(
            "The clean rebuild manifest is not byte-identical to the canonical manifest."
        )

    manifest = _read_json(staged_manifest, label="Staged publication manifest")
    paper_artifacts = manifest.get("paper_artifacts")
    if not isinstance(paper_artifacts, Mapping):
        raise TypeError("Staged publication manifest omits paper-artifact descriptors.")
    figure_targets = {
        name: {kind: FIGURE_DIR / f"{FIGURE_STEMS[name]}.{kind}" for kind in ("png", "pdf")}
        for name in FIGURE_STEMS
    }
    targets = (
        *TABLE_TARGETS.values(),
        *(target for group in figure_targets.values() for target in group.values()),
    )
    expected_paths = {target.relative_to(ROOT).as_posix() for target in targets}
    described_paths = {
        str(descriptor.get("path"))
        for descriptor in paper_artifacts.values()
        if isinstance(descriptor, Mapping)
    }
    if described_paths != expected_paths or len(paper_artifacts) != len(expected_paths):
        raise RuntimeError("The clean rebuild manifest has a different publication inventory.")

    expected_staged_files = {
        EVIDENCE_PATH.relative_to(ROOT).as_posix(),
        *expected_paths,
    }
    actual_staged_files = {
        path.relative_to(staged_outputs).as_posix()
        for path in staged_outputs.rglob("*")
        if path.is_file()
    }
    if actual_staged_files != expected_staged_files:
        missing = sorted(expected_staged_files.difference(actual_staged_files))
        unexpected = sorted(actual_staged_files.difference(expected_staged_files))
        raise RuntimeError(
            f"The clean rebuild output inventory changed: missing={missing}, unexpected={unexpected}."
        )
    for target in targets:
        staged = staged_outputs / target.relative_to(ROOT)
        if not target.is_file():
            raise FileNotFoundError(f"Canonical publication artifact is missing: {target}")
        if staged.read_bytes() != target.read_bytes():
            raise RuntimeError(f"Clean rebuild differs from canonical artifact: {target}")
    logger.info(
        "Clean rebuild is byte-identical to all canonical publication evidence: {}", resolved
    )
    return staged_manifest


def main(argv: list[str] | None = None) -> int:
    """Build and promote active evidence, or retain a nonpromoted generation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage-only",
        type=Path,
        help="Write a complete generation under this repository-local directory without promotion.",
    )
    parser.add_argument(
        "--promote-from-stage",
        type=Path,
        help="Verify and promote a retained generation while preserving existing target permissions.",
    )
    parser.add_argument(
        "--verify-stage-against-canonical",
        type=Path,
        help="Verify that a retained clean rebuild is byte-identical to the canonical package.",
    )
    args = parser.parse_args(argv)
    selected_modes = sum(
        value is not None
        for value in (
            args.stage_only,
            args.promote_from_stage,
            args.verify_stage_against_canonical,
        )
    )
    if selected_modes > 1:
        parser.error(
            "--stage-only, --promote-from-stage, and --verify-stage-against-canonical "
            "are mutually exclusive"
        )
    if args.promote_from_stage is not None:
        output = promote_staged_evidence(args.promote_from_stage)
    elif args.verify_stage_against_canonical is not None:
        output = verify_staged_evidence_matches_canonical(args.verify_stage_against_canonical)
    else:
        output = build_evidence(stage_only_root=args.stage_only)
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
