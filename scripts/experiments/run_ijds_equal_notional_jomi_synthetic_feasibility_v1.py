"""Run the sealed equal-notional fixed-K JOMI synthetic feasibility study."""

from __future__ import annotations

import argparse
import hashlib
import math
import os
import shutil
import subprocess
import threading
import time
import warnings
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd
import yaml
from scipy.special import expit
from scipy.stats import betabinom
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits

from src.ijds_audit.jomi_fixed_k import (
    beta_binomial_reference_size_law,
    deterministic_binary_prediction_sets,
    exact_conformal_rank,
    generic_swap_reference_set,
    reference_resolution_size,
    select_top_k,
    top_k_reference_set,
)
from src.utils.isolated_experiment import (
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    sha256_file,
    validate_run_tag,
)
from src.utils.long_run_observer import LongRunObserver, require_operational_paths_outside
from src.utils.pipeline_runtime import (
    atomic_write_bytes,
    atomic_write_parquet,
    atomic_write_strict_json,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(
    "configs/experiments/ijds_equal_notional_jomi_synthetic_feasibility_2026-08-08_v1.yaml"
)
PROTOCOL_PATH = Path(
    "docs/research/ijds_equal_notional_jomi_synthetic_feasibility_v1_protocol_2026-08-08.md"
)
EXPECTED_SCHEMA_VERSION = "2026-08-08.1"
EXPECTED_RUN_TAG = "ijds-equal-notional-jomi-synthetic-feasibility-2026-08-08-v1"
EXPECTED_PROTOCOL_TAG = "protocol/ijds-equal-notional-jomi-synthetic-feasibility-2026-08-08-v1"
EXPECTED_ARTIFACT_TAG = "artifacts/ijds-equal-notional-jomi-synthetic-feasibility-2026-08-08-v1"
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")

DATA_FILENAMES = (
    "replications.parquet",
    "focal_results.parquet",
    "analytic_reference_frontier.parquet",
    "oracle_reconciliation.parquet",
    "scale_fixtures.parquet",
    "crc_ltt_feasibility.parquet",
    "monotonicity_counterexample.parquet",
)
SUMMARY_FILENAME = "jomi_synthetic_summary.json"
RECEIPT_FILENAME = "execution_receipt.json"
EXPECTED_OUTPUT_PATHS = (
    *(
        f"{ALLOWED_DATA_ROOT.as_posix()}/{EXPECTED_RUN_TAG}/{filename}"
        for filename in DATA_FILENAMES
    ),
    f"{ALLOWED_MODEL_ROOT.as_posix()}/{EXPECTED_RUN_TAG}/{SUMMARY_FILENAME}",
    f"{ALLOWED_MODEL_ROOT.as_posix()}/{EXPECTED_RUN_TAG}/{RECEIPT_FILENAME}",
)
IMPLEMENTATION_PATHS = (
    PROTOCOL_PATH,
    Path("src/ijds_audit/jomi_fixed_k.py"),
    Path("scripts/experiments/run_ijds_equal_notional_jomi_synthetic_feasibility_v1.py"),
    Path("tests/test_ijds_jomi_fixed_k.py"),
    Path("tests/test_ijds_equal_notional_jomi_synthetic_feasibility_v1.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/long_run_observer.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)

EXPECTED_TOP_LEVEL_KEYS = {
    "schema_version",
    "protocol_status",
    "protocol_tag",
    "artifact_tag",
    "run_tag",
    "protocol_path",
    "git_transport",
    "design",
    "analytic_reference_frontier",
    "oracle_reconciliation",
    "scale_fixtures",
    "crc_ltt_feasibility",
    "runtime",
    "stop_rules",
    "output",
    "interpretation",
}
EXPECTED_DESIGN_SCALARS: dict[str, Any] = {
    "alpha": 0.10,
    "repetitions": 2000,
    "master_seed": 20260808,
    "train_size": 50000,
    "design_size": 20000,
    "calibration_size": 5000,
    "test_size": 2000,
    "selected_k": 100,
    "budget_units": 1.0,
    "allocation_per_selected_unit": 0.01,
    "feature_count": 8,
    "candidate_labels": [0, 1],
    "selector": "highest_synthetic_expected_margin_top_k",
    "taxonomy": "exact_selected_size_k",
    "tie_rule": "independent_continuous_priority_preassigned_before_labels",
    "nonconformity_score": "absolute_binary_residual_abs_y_minus_q",
    "learner": "linear_logistic_regression_deliberately_misspecified",
    "calibrator": "independent_design_split_platt_on_frozen_logit",
    "learner_solver": "lbfgs",
    "learner_c": 1.0,
    "learner_max_iter": 500,
    "platt_solver": "lbfgs",
    "platt_c": 1000000.0,
    "platt_max_iter": 500,
    "learner_fit_once_then_frozen": True,
    "deterministic_jomi_only": True,
    "vanilla_split_conformal_diagnostic_only": True,
}
EXPECTED_DGP = {
    "feature_law": "eight_independent_standard_gaussians",
    "true_logit": (
        "-1.4 + 1.2*x0 - 0.8*x1 + 0.65*x2*x3 + 0.9*sin(x4) + 0.7*I(x5>0) - 0.35*x6^2 + 0.2*x7"
    ),
    "synthetic_rate": "0.04 + 0.08*sigmoid(0.6*x1 - 0.3*x2 + 0.2*x7)",
    "synthetic_lgd": 0.45,
    "selection_utility": "(1-q)*synthetic_rate - q*synthetic_lgd",
}
EXPECTED_RNG_STREAMS = [
    "training_features",
    "training_labels",
    "design_features",
    "design_labels",
    "replication_calibration_features",
    "replication_calibration_labels",
    "replication_test_features",
    "replication_test_labels",
    "replication_tie_priorities",
]
REPLICATION_RNG_STREAMS = tuple(EXPECTED_RNG_STREAMS[4:])


@dataclass(frozen=True)
class FrozenProbabilityModel:
    """One frozen linear learner and independent Platt map."""

    learner: LogisticRegression
    platt: LogisticRegression
    fingerprint: str

    def predict(self, features: np.ndarray) -> np.ndarray:
        matrix = _feature_matrix(features, expected_columns=8)
        margin = np.asarray(self.learner.decision_function(matrix), dtype=float)
        probability = np.asarray(
            self.platt.predict_proba(margin.reshape(-1, 1))[:, 1],
            dtype=float,
        )
        if probability.shape != (len(matrix),) or not bool(np.isfinite(probability).all()):
            raise RuntimeError("The frozen learner produced invalid probabilities.")
        if bool(np.any(probability < 0.0) or np.any(probability > 1.0)):
            raise RuntimeError("The frozen learner produced probabilities outside [0, 1].")
        return probability


class ObserverHeartbeat:
    """Refresh a LongRunObserver during units longer than one heartbeat."""

    def __init__(self, observer: LongRunObserver, *, seconds: float) -> None:
        if not math.isfinite(seconds) or seconds <= 0.0:
            raise ValueError("Heartbeat interval must be finite and positive.")
        self._observer = observer
        self._seconds = float(seconds)
        self._phase = "preflight"
        self._operation = "initializing"
        self._state_lock = threading.Lock()
        self._stop = threading.Event()
        self._failure: BaseException | None = None
        self._thread = threading.Thread(
            target=self._loop,
            name="jomi-operational-heartbeat",
            daemon=True,
        )

    def set_phase(self, phase: str, operation: str) -> None:
        with self._state_lock:
            self._phase = str(phase)
            self._operation = str(operation)

    def _loop(self) -> None:
        while not self._stop.wait(self._seconds):
            with self._state_lock:
                phase = self._phase
                operation = self._operation
            try:
                self._observer.heartbeat(
                    phase=phase,
                    detail={"operation": operation},
                    force=True,
                )
            except BaseException as error:  # The main worker re-raises at a safe boundary.
                self._failure = error
                self._stop.set()

    def start(self) -> None:
        self._thread.start()

    def check(self) -> None:
        if self._failure is not None:
            raise RuntimeError("The operational heartbeat failed.") from self._failure

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=max(5.0, 2.0 * self._seconds))
        if self._thread.is_alive():
            raise RuntimeError("The operational heartbeat thread did not stop.")
        self.check()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping.")
    return value


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("JOMI synthetic feasibility config must be a mapping.")
    if set(payload) != EXPECTED_TOP_LEVEL_KEYS:
        raise ValueError(
            "The exact JOMI config surface changed; "
            f"missing={sorted(EXPECTED_TOP_LEVEL_KEYS.difference(payload))}, "
            f"extra={sorted(set(payload).difference(EXPECTED_TOP_LEVEL_KEYS))}."
        )
    return payload


def _require_exact_mapping(
    observed: Mapping[str, Any], expected: Mapping[str, Any], *, label: str
) -> None:
    if dict(observed) != dict(expected):
        raise RuntimeError(f"The locked {label} contract changed.")


def _require_fixed_contract(config: Mapping[str, Any]) -> None:
    exact_values = {
        "schema_version": EXPECTED_SCHEMA_VERSION,
        "protocol_status": "locked_synthetic_theorem_to_code_validation_not_active_empirical_evidence",
        "protocol_tag": EXPECTED_PROTOCOL_TAG,
        "artifact_tag": EXPECTED_ARTIFACT_TAG,
        "run_tag": EXPECTED_RUN_TAG,
        "protocol_path": PROTOCOL_PATH.as_posix(),
    }
    for field, expected in exact_values.items():
        if config.get(field) != expected:
            raise RuntimeError(f"The locked {field} contract changed.")

    transport = _mapping(config.get("git_transport"), label="git_transport")
    _require_exact_mapping(
        transport,
        {
            "artifact_commit_relationship": "single_direct_child_of_protocol_commit",
            "annotated_tags_required": True,
            "exact_output_paths": list(EXPECTED_OUTPUT_PATHS),
        },
        label="Git transport",
    )

    design = _mapping(config.get("design"), label="design")
    if set(design) != {*EXPECTED_DESIGN_SCALARS, "rng_streams", "primary_dgp"}:
        raise RuntimeError("The exact locked design schema changed.")
    for field, expected in EXPECTED_DESIGN_SCALARS.items():
        if design.get(field) != expected:
            raise RuntimeError(f"The locked design field {field!r} changed.")
    if design.get("rng_streams") != EXPECTED_RNG_STREAMS:
        raise RuntimeError("The locked RNG-stream partition changed.")
    _require_exact_mapping(
        _mapping(design.get("primary_dgp"), label="primary_dgp"),
        EXPECTED_DGP,
        label="primary DGP",
    )

    analytic = _mapping(
        config.get("analytic_reference_frontier"),
        label="analytic_reference_frontier",
    )
    _require_exact_mapping(
        analytic,
        {
            "finite_threshold_probability_targets": [0.95, 0.99],
            "cells": [
                {"calibration_size": 100, "test_size": 100, "selected_k": 5},
                {"calibration_size": 500, "test_size": 100, "selected_k": 5},
                {"calibration_size": 500, "test_size": 100, "selected_k": 10},
                {"calibration_size": 500, "test_size": 100, "selected_k": 2},
                {"calibration_size": 5000, "test_size": 2000, "selected_k": 100},
                {"calibration_size": 5000, "test_size": 6011, "selected_k": 100},
                {"calibration_size": 5000, "test_size": 10000, "selected_k": 100},
                {"calibration_size": 5000, "test_size": 28106, "selected_k": 100},
            ],
            "minimum_calibration_search": [
                {"test_size": 100, "selected_k": 5},
                {"test_size": 100, "selected_k": 10},
                {"test_size": 100, "selected_k": 20},
                {"test_size": 500, "selected_k": 25},
                {"test_size": 500, "selected_k": 50},
            ],
            "maximum_calibration_size_searched": 10000,
        },
        label="analytic reference frontier",
    )
    _require_exact_mapping(
        _mapping(config.get("oracle_reconciliation"), label="oracle_reconciliation"),
        {
            "exhaustive_enumeration": (
                "canonical_calibration_test_rank_interleavings_choose_n_plus_m_n"
            ),
            "exhaustive_cases": [
                {"calibration_size": 5, "test_size": 4, "selected_k": 1},
                {"calibration_size": 6, "test_size": 5, "selected_k": 2},
                {"calibration_size": 8, "test_size": 4, "selected_k": 2},
            ],
            "random_cases": 250,
            "random_seed": 20260809,
            "require_both_candidate_labels": True,
            "require_shortcut_equals_swap_oracle": True,
        },
        label="oracle reconciliation",
    )
    _require_exact_mapping(
        _mapping(config.get("scale_fixtures"), label="scale_fixtures"),
        {
            "calibration_size": 5000,
            "selected_k": 100,
            "test_sizes": [6011, 10000, 28106],
            "repetitions_per_size": 10,
            "random_seed": 20260810,
            "outcome_free": True,
        },
        label="scale fixtures",
    )
    _require_exact_mapping(
        _mapping(config.get("crc_ltt_feasibility"), label="crc_ltt_feasibility"),
        {
            "alpha_risk": 0.10,
            "ltt_delta_cert": 0.10,
            "loss_lower_bound": 0.0,
            "loss_upper_bound": 1.0,
            "crc_catalog_sizes": [2, 10, 25, 100],
            "crc_excess_targets": [0.10, 0.025],
            "ltt_catalog_size": 10,
            "ltt_empirical_losses": [0.0, 0.02, 0.05, 0.075, 0.08],
            "ltt_multiplicity_routes": ["bonferroni", "fixed_sequence"],
            "require_pointwise_zero_loss_terminal": True,
        },
        label="CRC/LTT feasibility",
    )
    _require_exact_mapping(
        _mapping(config.get("runtime"), label="runtime"),
        {
            "runtime_root_must_be_external": True,
            "preferred_runtime_root": "D:/CRPTO/runtime",
            "single_process": True,
            "workers": 1,
            "heartbeat_seconds": 30,
            "wall_deadline_seconds": 1800,
            "minimum_free_space_gib": 5,
            "resume_authorized": False,
            "atomic_unit": "one_complete_replication",
            "partial_scientific_results_in_status": False,
            "process_priority": "below_normal_when_supported",
        },
        label="runtime",
    )
    stop_rules = _mapping(config.get("stop_rules"), label="stop_rules")
    if not stop_rules or not all(value is True for value in stop_rules.values()):
        raise RuntimeError("Every locked stop rule must remain enabled.")
    expected_stop_names = {
        "require_clean_exact_annotated_protocol_tag",
        "hard_no_overwrite",
        "stop_on_oracle_shortcut_mismatch",
        "stop_on_calibration_permutation_change",
        "stop_on_test_permutation_nonequivariance",
        "stop_on_visible_id_reversal_change",
        "stop_on_repeat_change",
        "stop_on_selected_size_not_k",
        "stop_on_primary_reference_size_below_resolution",
        "stop_on_missing_or_duplicate_replication",
        "stop_on_any_nonfinite_value",
        "stop_on_equal_notional_fcp_inequality",
        "stop_if_one_sided_999_lower_bound_exceeds_alpha",
        "stop_on_deadline",
        "no_parameter_or_dgp_change_after_protocol_tag",
    }
    if set(stop_rules) != expected_stop_names:
        raise RuntimeError("The exact locked stop-rule names changed.")
    _require_exact_mapping(
        _mapping(config.get("output"), label="output"),
        {
            "data_root": ALLOWED_DATA_ROOT.as_posix(),
            "model_root": ALLOWED_MODEL_ROOT.as_posix(),
            "runtime_subdir": EXPECTED_RUN_TAG,
            "immutability": "hard_no_overwrite",
        },
        label="output",
    )
    interpretation = _mapping(config.get("interpretation"), label="interpretation")
    expected_interpretation = {
        "synthetic_only": True,
        "active_empirical_evidence": False,
        "lendingclub_validity_claimed": False,
        "temporal_transport_claimed": False,
        "fractional_lp_validity_claimed": False,
        "joint_label_coverage_claimed": False,
        "prospective_confirmation_claimed": False,
        "permitted_claims": [
            "theorem_to_code_reconciliation_under_enumerated_top_k_cases",
            "exact_equal_notional_count_and_dollar_fcp_identity",
            "beta_binomial_reference_size_finite_threshold_corollary_under_iid_continuous_scores",
            "monte_carlo_behavior_under_the_single_locked_synthetic_iid_dgp",
        ],
    }
    _require_exact_mapping(interpretation, expected_interpretation, label="interpretation")


def _annotated_tag_commit(repo_root: Path, tag: str) -> str:
    try:
        object_type = subprocess.run(
            ["git", "cat-file", "-t", f"refs/tags/{tag}"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        commit = subprocess.run(
            ["git", "rev-list", "-n", "1", tag],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError(f"Required annotated protocol tag is unavailable: {tag}") from error
    if object_type != "tag" or not commit:
        raise RuntimeError(f"Protocol tag {tag!r} must be an annotated tag object.")
    return commit


def _require_clean_annotated_head(repo_root: Path, tag: str) -> str:
    commit = require_clean_tagged_head(repo_root, tag)
    if _annotated_tag_commit(repo_root, tag) != commit:
        raise RuntimeError("The annotated protocol tag does not resolve to clean HEAD.")
    return commit


def _require_fresh_official_outputs(config: Mapping[str, Any], *, repo_root: Path) -> None:
    transport = _mapping(config["git_transport"], label="git_transport")
    paths = tuple((repo_root / str(value)).resolve() for value in transport["exact_output_paths"])
    for path in paths:
        try:
            path.relative_to(repo_root.resolve())
        except ValueError as error:
            raise ValueError(f"Official output escaped the repository: {path}") from error
    run_directories = {
        (repo_root / ALLOWED_DATA_ROOT / EXPECTED_RUN_TAG).resolve(),
        (repo_root / ALLOWED_MODEL_ROOT / EXPECTED_RUN_TAG).resolve(),
    }
    occupied = sorted(str(path) for path in (*paths, *run_directories) if path.exists())
    if occupied:
        raise FileExistsError(f"Official JOMI output paths already exist: {occupied}")


def _nearest_existing_ancestor(path: Path) -> Path:
    candidate = path.resolve()
    while not candidate.exists():
        parent = candidate.parent
        if parent == candidate:
            raise FileNotFoundError(f"No existing ancestor for runtime path {path}.")
        candidate = parent
    return candidate


def _prepare_runtime_directory(
    configured_root: Path,
    *,
    repo_root: Path,
    config: Mapping[str, Any],
) -> Path:
    runtime = _mapping(config["runtime"], label="runtime")
    output = _mapping(config["output"], label="output")
    run_tag = validate_run_tag(str(config["run_tag"]))
    base = Path(configured_root).resolve()
    run_directory = (base / str(output["runtime_subdir"])).resolve()
    if run_directory.parent != base or run_directory.name != run_tag:
        raise ValueError("Runtime directory must be one fresh direct run-tag child.")
    forbidden = [repo_root.resolve()]
    legacy = Path("D:/crpto_legacy")
    if legacy.exists():
        forbidden.append(legacy.resolve())
    require_operational_paths_outside(
        (run_directory / "status" / "latest.json", run_directory / "staging"),
        forbidden_roots=forbidden,
    )
    if run_directory.exists():
        raise FileExistsError(f"Runtime directory already exists: {run_directory}")
    existing = _nearest_existing_ancestor(base)
    free_bytes = int(shutil.disk_usage(existing).free)
    minimum = int(runtime["minimum_free_space_gib"]) * 1024**3
    if free_bytes < minimum:
        raise RuntimeError(
            f"Runtime volume has {free_bytes} free bytes, below the locked reserve {minimum}."
        )
    base.mkdir(parents=True, exist_ok=True)
    run_directory.mkdir()
    return run_directory


def _set_below_normal_priority() -> str:
    if os.name != "nt":
        return "unsupported_non_windows"
    try:
        import psutil
    except ImportError:
        return "supported_but_not_applied"
    try:
        psutil.Process(os.getpid()).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    except (AttributeError, OSError, psutil.Error):
        return "supported_but_not_applied"
    return "below_normal_applied"


def _feature_matrix(features: np.ndarray, *, expected_columns: int) -> np.ndarray:
    matrix = np.asarray(features, dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != expected_columns:
        raise ValueError(f"Features must have shape (n, {expected_columns}).")
    if not bool(np.isfinite(matrix).all()):
        raise ValueError("Features must be finite.")
    return matrix


def _core_sequence(values: np.ndarray) -> tuple[object, ...]:
    """Convert a one-dimensional NumPy vector at the typed core boundary."""

    vector = np.asarray(values)
    if vector.ndim != 1:
        raise ValueError("The fixed-K core boundary requires a one-dimensional vector.")
    return tuple(vector.tolist())


def _true_probability(features: np.ndarray) -> np.ndarray:
    x = _feature_matrix(features, expected_columns=8)
    logit = (
        -1.4
        + 1.2 * x[:, 0]
        - 0.8 * x[:, 1]
        + 0.65 * x[:, 2] * x[:, 3]
        + 0.9 * np.sin(x[:, 4])
        + 0.7 * (x[:, 5] > 0.0)
        - 0.35 * np.square(x[:, 6])
        + 0.2 * x[:, 7]
    )
    probability = np.asarray(expit(logit), dtype=float)
    if not bool(np.isfinite(probability).all()):
        raise RuntimeError("The locked nonlinear DGP produced nonfinite probabilities.")
    return probability


def _synthetic_rate(features: np.ndarray) -> np.ndarray:
    x = _feature_matrix(features, expected_columns=8)
    rate = 0.04 + 0.08 * expit(0.6 * x[:, 1] - 0.3 * x[:, 2] + 0.2 * x[:, 7])
    rate = np.asarray(rate, dtype=float)
    if not bool(np.isfinite(rate).all()):
        raise RuntimeError("The locked synthetic rate produced nonfinite values.")
    return rate


def _draw_labeled_features(
    size: int,
    *,
    feature_count: int,
    feature_rng: np.random.Generator,
    label_rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    if size <= 0 or feature_count != 8:
        raise ValueError("The locked synthetic draw requires a positive size and eight features.")
    features = feature_rng.standard_normal((size, feature_count))
    labels = label_rng.binomial(1, _true_probability(features)).astype(np.int8)
    if set(np.unique(labels)).difference({0, 1}):
        raise RuntimeError("The synthetic DGP emitted a nonbinary label.")
    return features, labels


def _model_fingerprint(learner: LogisticRegression, platt: LogisticRegression) -> str:
    digest = hashlib.sha256()
    for array in (learner.coef_, learner.intercept_, platt.coef_, platt.intercept_):
        values = np.ascontiguousarray(np.asarray(array, dtype=np.float64))
        digest.update(str(values.shape).encode("ascii"))
        digest.update(values.tobytes())
    return digest.hexdigest()


def _fit_frozen_model(
    *,
    train_feature_rng: np.random.Generator,
    train_label_rng: np.random.Generator,
    design_feature_rng: np.random.Generator,
    design_label_rng: np.random.Generator,
    design: Mapping[str, Any],
) -> FrozenProbabilityModel:
    feature_count = int(design["feature_count"])
    train_x, train_y = _draw_labeled_features(
        int(design["train_size"]),
        feature_count=feature_count,
        feature_rng=train_feature_rng,
        label_rng=train_label_rng,
    )
    design_x, design_y = _draw_labeled_features(
        int(design["design_size"]),
        feature_count=feature_count,
        feature_rng=design_feature_rng,
        label_rng=design_label_rng,
    )
    if len(np.unique(train_y)) != 2 or len(np.unique(design_y)) != 2:
        raise RuntimeError("Training and Platt design draws must each contain both labels.")
    learner = LogisticRegression(
        C=float(design["learner_c"]),
        solver=str(design["learner_solver"]),
        max_iter=int(design["learner_max_iter"]),
        random_state=int(design["master_seed"]),
    )
    platt = LogisticRegression(
        C=float(design["platt_c"]),
        solver=str(design["platt_solver"]),
        max_iter=int(design["platt_max_iter"]),
        random_state=int(design["master_seed"]),
    )
    try:
        with warnings.catch_warnings(), threadpool_limits(limits=1):
            warnings.simplefilter("error", category=ConvergenceWarning)
            learner.fit(train_x, train_y)
            train_margin = np.asarray(learner.decision_function(design_x), dtype=float)
            platt.fit(train_margin.reshape(-1, 1), design_y)
    except ConvergenceWarning as error:
        raise RuntimeError("A locked learner or Platt fit emitted ConvergenceWarning.") from error
    if int(np.max(learner.n_iter_)) >= int(design["learner_max_iter"]):
        raise RuntimeError("The locked linear learner reached its iteration limit.")
    if int(np.max(platt.n_iter_)) >= int(design["platt_max_iter"]):
        raise RuntimeError("The locked Platt map reached its iteration limit.")
    fingerprint = _model_fingerprint(learner, platt)
    frozen = FrozenProbabilityModel(learner=learner, platt=platt, fingerprint=fingerprint)
    frozen.predict(design_x[:32])
    return frozen


def _spawn_locked_rng_streams(
    design: Mapping[str, Any],
) -> tuple[
    dict[str, np.random.Generator],
    dict[str, tuple[np.random.SeedSequence, ...]],
]:
    """Spawn every declared stochastic role from a distinct named root stream."""

    stream_names = design.get("rng_streams")
    if stream_names != EXPECTED_RNG_STREAMS:
        raise RuntimeError("The locked RNG-stream partition changed.")
    roots = np.random.SeedSequence(int(design["master_seed"])).spawn(len(stream_names))
    by_name = dict(zip(stream_names, roots, strict=True))
    fixed = {name: np.random.default_rng(by_name[name]) for name in EXPECTED_RNG_STREAMS[:4]}
    repetitions = int(design["repetitions"])
    replicated = {name: tuple(by_name[name].spawn(repetitions)) for name in REPLICATION_RNG_STREAMS}
    if set(fixed) != set(EXPECTED_RNG_STREAMS[:4]) or set(replicated) != set(
        REPLICATION_RNG_STREAMS
    ):
        raise RuntimeError("A locked RNG stream was omitted or duplicated.")
    return fixed, replicated


def _finite_conformal_threshold(scores: np.ndarray, *, alpha: float) -> float:
    values = np.asarray(scores, dtype=float)
    if values.ndim != 1 or not bool(np.isfinite(values).all()):
        raise ValueError("Nonconformity scores must be a finite one-dimensional array.")
    rank = exact_conformal_rank(len(values), alpha=alpha)
    if rank > len(values):
        raise RuntimeError("The reference set cannot attain a finite conformal threshold.")
    return float(np.partition(values, rank - 1)[rank - 1])


def _prediction_membership(
    probability: np.ndarray, threshold: float
) -> tuple[np.ndarray, np.ndarray]:
    q = np.asarray(probability, dtype=float)
    include_zero = q <= threshold
    include_one = (1.0 - q) <= threshold
    return include_zero, include_one


def _misses(labels: np.ndarray, include_zero: np.ndarray, include_one: np.ndarray) -> np.ndarray:
    y = np.asarray(labels, dtype=np.int8)
    if y.shape != include_zero.shape or y.shape != include_one.shape:
        raise ValueError("Labels and binary prediction-set indicators must align.")
    return np.where(y == 0, ~include_zero, ~include_one).astype(np.int8)


def _exhaustive_rank_interleavings(
    calibration_size: int, test_size: int
) -> Sequence[tuple[int, ...]]:
    import itertools

    return tuple(itertools.combinations(range(calibration_size + test_size), calibration_size))


def _oracle_fixture_rows(
    *,
    fixture_kind: str,
    fixture_id: str,
    calibration_scores: np.ndarray,
    calibration_priorities: np.ndarray,
    test_scores: np.ndarray,
    test_priorities: np.ndarray,
    selected_k: int,
    rng: np.random.Generator,
) -> list[dict[str, Any]]:
    calibration_score_values = _core_sequence(calibration_scores)
    calibration_priority_values = _core_sequence(calibration_priorities)
    test_score_values = _core_sequence(test_scores)
    test_priority_values = _core_sequence(test_priorities)
    selected = select_top_k(test_score_values, test_priority_values, selected_k)
    shortcut = top_k_reference_set(
        calibration_score_values,
        calibration_priority_values,
        test_score_values,
        test_priority_values,
        selected_k,
    )
    repeated = top_k_reference_set(
        calibration_score_values,
        calibration_priority_values,
        test_score_values,
        test_priority_values,
        selected_k,
    )
    if repeated != shortcut:
        raise RuntimeError("Repeat execution changed the Proposition-6 reference set.")

    calibration_permutation = rng.permutation(len(calibration_scores))
    permuted_reference = top_k_reference_set(
        _core_sequence(calibration_scores[calibration_permutation]),
        _core_sequence(calibration_priorities[calibration_permutation]),
        test_score_values,
        test_priority_values,
        selected_k,
    )
    recovered_reference = tuple(
        sorted(int(calibration_permutation[index]) for index in permuted_reference)
    )
    if recovered_reference != tuple(sorted(shortcut)):
        raise RuntimeError("A calibration permutation changed reference membership.")

    test_permutation = rng.permutation(len(test_scores))
    permuted_selected = select_top_k(
        _core_sequence(test_scores[test_permutation]),
        _core_sequence(test_priorities[test_permutation]),
        selected_k,
    )
    recovered_selected = tuple(sorted(int(test_permutation[index]) for index in permuted_selected))
    if recovered_selected != tuple(sorted(selected)):
        raise RuntimeError("A test permutation changed selected unit identities.")
    test_permuted_reference = top_k_reference_set(
        calibration_score_values,
        calibration_priority_values,
        _core_sequence(test_scores[test_permutation]),
        _core_sequence(test_priorities[test_permutation]),
        selected_k,
    )
    if test_permuted_reference != shortcut:
        raise RuntimeError("A test permutation changed reference membership.")

    visible_ids = np.arange(len(test_scores), dtype=np.int64)
    reversed_visible_ids = visible_ids[::-1]
    if np.array_equal(visible_ids, reversed_visible_ids) and len(visible_ids) > 1:
        raise RuntimeError("The visible-ID reversal fixture did not change visible IDs.")
    id_reversal_unchanged = (
        select_top_k(test_score_values, test_priority_values, selected_k) == selected
        and top_k_reference_set(
            calibration_score_values,
            calibration_priority_values,
            test_score_values,
            test_priority_values,
            selected_k,
        )
        == shortcut
    )
    if not id_reversal_unchanged:
        raise RuntimeError("Visible-ID reversal changed an ID-free selection calculation.")

    def fixed_size_taxonomy(support: frozenset[int]) -> bool:
        return len(support) == selected_k

    rows: list[dict[str, Any]] = []
    for focal_rank, focal in enumerate(selected):
        oracle = generic_swap_reference_set(
            calibration_score_values,
            calibration_priority_values,
            test_score_values,
            test_priority_values,
            selected_k,
            focal_index=focal,
            taxonomy=fixed_size_taxonomy,
        )
        if oracle != shortcut:
            raise RuntimeError("The generic swap reference differs from Proposition 6.")
        for candidate_label in (0, 1):
            rows.append(
                {
                    "fixture_kind": fixture_kind,
                    "fixture_id": fixture_id,
                    "calibration_size": int(len(calibration_scores)),
                    "test_size": int(len(test_scores)),
                    "selected_k": int(selected_k),
                    "focal_rank": int(focal_rank),
                    "focal_index": int(focal),
                    "candidate_label": int(candidate_label),
                    "reference_size": int(len(shortcut)),
                    "shortcut_equals_oracle": True,
                    "calibration_permutation_invariant": True,
                    "test_permutation_equivariant": True,
                    "visible_id_reversal_invariant": True,
                    "repeat_invariant": True,
                }
            )
    return rows


def _build_oracle_reconciliation(config: Mapping[str, Any]) -> pd.DataFrame:
    oracle = _mapping(config["oracle_reconciliation"], label="oracle_reconciliation")
    rng = np.random.default_rng(int(oracle["random_seed"]))
    rows: list[dict[str, Any]] = []
    for case_index, case_raw in enumerate(oracle["exhaustive_cases"]):
        case = _mapping(case_raw, label="exhaustive oracle case")
        n = int(case["calibration_size"])
        m = int(case["test_size"])
        k = int(case["selected_k"])
        total = n + m
        priorities = np.arange(1, total + 1, dtype=float) / (total + 1)
        for ordering_index, calibration_ranks in enumerate(_exhaustive_rank_interleavings(n, m)):
            calibration_rank_set = set(calibration_ranks)
            test_ranks = tuple(rank for rank in range(total) if rank not in calibration_rank_set)
            rows.extend(
                _oracle_fixture_rows(
                    fixture_kind="exhaustive_rank_interleaving",
                    fixture_id=f"e{case_index:02d}-{ordering_index:05d}",
                    calibration_scores=np.asarray(calibration_ranks, dtype=float),
                    calibration_priorities=priorities[:n],
                    test_scores=np.asarray(test_ranks, dtype=float),
                    test_priorities=priorities[n:],
                    selected_k=k,
                    rng=rng,
                )
            )

    for random_index in range(int(oracle["random_cases"])):
        n = int(rng.integers(3, 21))
        m = int(rng.integers(2, 16))
        k = int(rng.integers(1, m))
        # Rounded scores exercise actual ties; globally unique continuous
        # priorities retain one total, permutation-equivariant order.
        calibration_scores = np.round(rng.normal(size=n), 1)
        test_scores = np.round(rng.normal(size=m), 1)
        priorities = rng.random(n + m)
        if len(np.unique(priorities)) != n + m:
            raise RuntimeError("A seeded continuous priority fixture contained an exact tie.")
        rows.extend(
            _oracle_fixture_rows(
                fixture_kind="seeded_random_with_score_ties",
                fixture_id=f"r{random_index:04d}",
                calibration_scores=calibration_scores,
                calibration_priorities=priorities[:n],
                test_scores=test_scores,
                test_priorities=priorities[n:],
                selected_k=k,
                rng=rng,
            )
        )

    tie_scores = np.full(12, 0.5)
    tie_priorities = np.linspace(0.01, 0.99, 12)
    rows.extend(
        _oracle_fixture_rows(
            fixture_kind="complete_score_tie_priority_control",
            fixture_id="tie-0000",
            calibration_scores=tie_scores[:7],
            calibration_priorities=tie_priorities[:7],
            test_scores=tie_scores[7:],
            test_priorities=tie_priorities[7:],
            selected_k=2,
            rng=rng,
        )
    )
    frame = pd.DataFrame(rows)
    if frame.empty or set(frame["candidate_label"].unique()) != {0, 1}:
        raise RuntimeError("The oracle fixture bank did not enumerate both binary labels.")
    boolean_columns = [
        "shortcut_equals_oracle",
        "calibration_permutation_invariant",
        "test_permutation_equivariant",
        "visible_id_reversal_invariant",
        "repeat_invariant",
    ]
    if not bool(frame[boolean_columns].to_numpy(dtype=bool).all()):
        raise RuntimeError("An oracle reconciliation control failed.")
    return frame.sort_values(
        ["fixture_kind", "fixture_id", "focal_rank", "candidate_label"],
        kind="stable",
    ).reset_index(drop=True)


def _beta_binomial_scipy_statistics(
    calibration_size: int,
    test_size: int,
    selected_k: int,
    resolution_size: int,
) -> dict[str, Any]:
    if not 1 <= selected_k < test_size:
        raise ValueError("The beta-binomial frontier requires 1 <= K < test size.")
    support = np.arange(calibration_size + 1, dtype=int)
    a = selected_k + 1
    b = test_size - selected_k
    pmf = np.asarray(betabinom.pmf(support, calibration_size, a, b), dtype=float)
    if not bool(np.isfinite(pmf).all()):
        raise RuntimeError("SciPy beta-binomial PMF produced nonfinite values.")
    mass = float(math.fsum(float(value) for value in pmf))
    mean = float(np.dot(support, pmf))
    variance = float(np.dot(np.square(support - mean), pmf))
    closed_mean = calibration_size * (selected_k + 1) / (test_size + 1)
    closed_variance = (
        calibration_size
        * (selected_k + 1)
        * (test_size - selected_k)
        * (test_size + 1 + calibration_size)
        / ((test_size + 1) ** 2 * (test_size + 2))
    )
    if not math.isclose(mass, 1.0, rel_tol=0.0, abs_tol=2.0e-10):
        raise RuntimeError("SciPy beta-binomial PMF failed to normalize.")
    if not math.isclose(mean, closed_mean, rel_tol=2.0e-10, abs_tol=2.0e-10):
        raise RuntimeError("SciPy beta-binomial PMF failed its mean identity.")
    if not math.isclose(variance, closed_variance, rel_tol=5.0e-9, abs_tol=5.0e-9):
        raise RuntimeError("SciPy beta-binomial PMF failed its variance identity.")
    resolution_probability = float(betabinom.sf(resolution_size - 1, calibration_size, a, b))
    if not math.isfinite(resolution_probability) or not 0.0 <= resolution_probability <= 1.0:
        raise RuntimeError("SciPy beta-binomial survival probability is invalid.")
    failure_probability = float(betabinom.cdf(resolution_size - 1, calibration_size, a, b))
    log_failure_probability = float(betabinom.logcdf(resolution_size - 1, calibration_size, a, b))
    if (
        not math.isfinite(failure_probability)
        or not 0.0 <= failure_probability <= 1.0
        or not math.isfinite(log_failure_probability)
    ):
        raise RuntimeError("SciPy beta-binomial lower-tail probability is invalid.")
    survival_saturated = resolution_probability == 1.0 and failure_probability > 0.0
    return {
        "pmf_mass": mass,
        "mean_reference_size": closed_mean,
        "variance_reference_size": closed_variance,
        "resolution_probability": resolution_probability,
        "failure_probability_below_resolution": failure_probability,
        "log_failure_probability_below_resolution": log_failure_probability,
        "resolution_probability_saturated_at_one": survival_saturated,
    }


def _minimum_calibration_for_resolution(
    *,
    test_size: int,
    selected_k: int,
    resolution_size: int,
    target_probability: float,
    maximum: int,
) -> tuple[int, float]:
    def probability(n: int) -> float:
        return float(
            betabinom.sf(
                resolution_size - 1,
                n,
                selected_k + 1,
                test_size - selected_k,
            )
        )

    if probability(maximum) < target_probability:
        raise RuntimeError("The calibration search maximum cannot attain its locked target.")
    lower, upper = 0, maximum
    while lower < upper:
        midpoint = (lower + upper) // 2
        if probability(midpoint) >= target_probability:
            upper = midpoint
        else:
            lower = midpoint + 1
    achieved = probability(lower)
    if lower > 0 and probability(lower - 1) >= target_probability:
        raise RuntimeError("The resolution search did not return the first qualifying size.")
    return lower, achieved


def _build_analytic_reference_frontier(config: Mapping[str, Any]) -> pd.DataFrame:
    design = _mapping(config["design"], label="design")
    analytic = _mapping(
        config["analytic_reference_frontier"],
        label="analytic_reference_frontier",
    )
    alpha = float(design["alpha"])
    resolution_size = reference_resolution_size(alpha)
    exact_control = beta_binomial_reference_size_law(25, 20, 3)
    if sum(exact_control.pmf) != 1:
        raise RuntimeError("The exact small beta-binomial control failed to normalize.")
    rows: list[dict[str, Any]] = []
    for cell_raw in analytic["cells"]:
        cell = _mapping(cell_raw, label="analytic reference cell")
        n = int(cell["calibration_size"])
        m = int(cell["test_size"])
        k = int(cell["selected_k"])
        stats = _beta_binomial_scipy_statistics(n, m, k, resolution_size)
        rows.append(
            {
                "row_type": "declared_frontier_cell",
                "calibration_size": n,
                "test_size": m,
                "selected_k": k,
                "alpha": alpha,
                "resolution_size": resolution_size,
                "probability_target": 0.0,
                "pmf_mass": stats["pmf_mass"],
                "mean_reference_size": stats["mean_reference_size"],
                "variance_reference_size": stats["variance_reference_size"],
                "resolution_probability": stats["resolution_probability"],
                "failure_probability_below_resolution": stats[
                    "failure_probability_below_resolution"
                ],
                "log_failure_probability_below_resolution": stats[
                    "log_failure_probability_below_resolution"
                ],
                "resolution_probability_saturated_at_one": stats[
                    "resolution_probability_saturated_at_one"
                ],
                "minimum_search_succeeded": False,
            }
        )
    maximum = int(analytic["maximum_calibration_size_searched"])
    for search_raw in analytic["minimum_calibration_search"]:
        search = _mapping(search_raw, label="minimum calibration search")
        m = int(search["test_size"])
        k = int(search["selected_k"])
        for target in analytic["finite_threshold_probability_targets"]:
            n, achieved = _minimum_calibration_for_resolution(
                test_size=m,
                selected_k=k,
                resolution_size=resolution_size,
                target_probability=float(target),
                maximum=maximum,
            )
            stats = _beta_binomial_scipy_statistics(n, m, k, resolution_size)
            if not math.isclose(
                achieved,
                stats["resolution_probability"],
                rel_tol=0.0,
                abs_tol=1.0e-15,
            ):
                raise RuntimeError("Minimum-search probability did not reconcile.")
            rows.append(
                {
                    "row_type": "minimum_calibration_search",
                    "calibration_size": n,
                    "test_size": m,
                    "selected_k": k,
                    "alpha": alpha,
                    "resolution_size": resolution_size,
                    "probability_target": float(target),
                    "pmf_mass": stats["pmf_mass"],
                    "mean_reference_size": stats["mean_reference_size"],
                    "variance_reference_size": stats["variance_reference_size"],
                    "resolution_probability": achieved,
                    "failure_probability_below_resolution": stats[
                        "failure_probability_below_resolution"
                    ],
                    "log_failure_probability_below_resolution": stats[
                        "log_failure_probability_below_resolution"
                    ],
                    "resolution_probability_saturated_at_one": stats[
                        "resolution_probability_saturated_at_one"
                    ],
                    "minimum_search_succeeded": True,
                }
            )
    frame = pd.DataFrame(rows)
    expected_rows = len(analytic["cells"]) + len(analytic["minimum_calibration_search"]) * len(
        analytic["finite_threshold_probability_targets"]
    )
    if len(frame) != expected_rows:
        raise RuntimeError("The analytic reference frontier is incomplete.")
    return frame.sort_values(
        ["row_type", "test_size", "selected_k", "probability_target"], kind="stable"
    ).reset_index(drop=True)


def _build_scale_fixtures(config: Mapping[str, Any]) -> pd.DataFrame:
    scale = _mapping(config["scale_fixtures"], label="scale_fixtures")
    rng = np.random.default_rng(int(scale["random_seed"]))
    n = int(scale["calibration_size"])
    k = int(scale["selected_k"])
    rows: list[dict[str, Any]] = []
    for test_size in scale["test_sizes"]:
        m = int(test_size)
        for fixture_index in range(int(scale["repetitions_per_size"])):
            calibration_scores = rng.standard_normal(n)
            test_scores = rng.standard_normal(m)
            priorities = rng.random(n + m)
            calibration_score_values = _core_sequence(calibration_scores)
            calibration_priority_values = _core_sequence(priorities[:n])
            test_score_values = _core_sequence(test_scores)
            test_priority_values = _core_sequence(priorities[n:])
            selected = select_top_k(test_score_values, test_priority_values, k)
            reference = top_k_reference_set(
                calibration_score_values,
                calibration_priority_values,
                test_score_values,
                test_priority_values,
                k,
            )
            if len(selected) != k:
                raise RuntimeError("A scale fixture did not select exactly K units.")
            if reference != top_k_reference_set(
                calibration_score_values,
                calibration_priority_values,
                test_score_values,
                test_priority_values,
                k,
            ):
                raise RuntimeError("A scale fixture changed on repeat execution.")
            rows.append(
                {
                    "fixture_index": fixture_index,
                    "calibration_size": n,
                    "test_size": m,
                    "selected_k": k,
                    "selected_size": len(selected),
                    "reference_size": len(reference),
                    "resolution_size": reference_resolution_size(
                        float(_mapping(config["design"], label="design")["alpha"])
                    ),
                    "finite_threshold_possible": len(reference)
                    >= reference_resolution_size(
                        float(_mapping(config["design"], label="design")["alpha"])
                    ),
                    "outcome_rows_read": 0,
                    "repeat_invariant": True,
                }
            )
    frame = pd.DataFrame(rows)
    expected = len(scale["test_sizes"]) * int(scale["repetitions_per_size"])
    if len(frame) != expected or int(frame["outcome_rows_read"].sum()) != 0:
        raise RuntimeError("The complete outcome-free scale fixture grid is absent.")
    return frame.sort_values(["test_size", "fixture_index"], kind="stable").reset_index(drop=True)


def _crc_excess(catalog_size: int, contexts: int, *, loss_bound: float) -> float:
    if catalog_size < 2 or contexts < 1 or loss_bound <= 0.0:
        raise ValueError("CRC excess requires catalog size >=2, positive contexts, and B>0.")
    log_term = math.log(2.0 * catalog_size)
    return loss_bound * math.sqrt(log_term / (2.0 * contexts)) + loss_bound / (
        2.0 * math.sqrt(2.0 * contexts * log_term)
    )


def _minimum_crc_contexts(
    catalog_size: int,
    excess_target: float,
    *,
    loss_bound: float,
) -> int:
    if not 0.0 < excess_target < 1.0:
        raise ValueError("CRC excess target must lie inside (0, 1).")
    lower, upper = 1, 1
    while _crc_excess(catalog_size, upper, loss_bound=loss_bound) >= excess_target:
        upper *= 2
    while lower < upper:
        midpoint = (lower + upper) // 2
        if _crc_excess(catalog_size, midpoint, loss_bound=loss_bound) < excess_target:
            upper = midpoint
        else:
            lower = midpoint + 1
    if lower > 1 and _crc_excess(catalog_size, lower - 1, loss_bound=loss_bound) < excess_target:
        raise RuntimeError("CRC context search did not return the first strict crossing.")
    return lower


def _binary_kl(lower: float, upper: float) -> float:
    if not 0.0 <= lower < upper <= 1.0:
        raise ValueError("Binary KL requires 0 <= lower < upper <= 1.")
    first = 0.0 if lower == 0.0 else lower * math.log(lower / upper)
    second = 0.0 if lower == 1.0 else (1.0 - lower) * math.log((1.0 - lower) / (1.0 - upper))
    return first + second


def _build_crc_ltt_feasibility(config: Mapping[str, Any]) -> pd.DataFrame:
    contract = _mapping(config["crc_ltt_feasibility"], label="crc_ltt_feasibility")
    alpha = float(contract["alpha_risk"])
    delta = float(contract["ltt_delta_cert"])
    loss_lower = float(contract["loss_lower_bound"])
    loss_upper = float(contract["loss_upper_bound"])
    loss_bound = loss_upper - loss_lower
    if loss_lower != 0.0 or loss_upper != 1.0 or loss_bound != 1.0:
        raise RuntimeError("The locked CRC/LTT design requires loss L in [0, 1].")
    rows: list[dict[str, Any]] = []
    for catalog_size in contract["crc_catalog_sizes"]:
        for excess_target in contract["crc_excess_targets"]:
            contexts = _minimum_crc_contexts(
                int(catalog_size),
                float(excess_target),
                loss_bound=loss_bound,
            )
            rows.append(
                {
                    "study": "finite_grid_nonmonotone_crc_design_only",
                    "method": "crc_expected_excess_upper_bound",
                    "risk_bound_mode": "expected_risk_bound_no_delta_parameter",
                    "catalog_size": int(catalog_size),
                    "target_risk": alpha,
                    "loss_lower_bound": loss_lower,
                    "loss_upper_bound": loss_upper,
                    "empirical_loss": 0.0,
                    "margin_or_excess_target": float(excess_target),
                    "multiplicity_route": "not_applicable",
                    "nominal_tail_probability": "not_applicable",
                    "per_policy_tail_probability": "not_applicable",
                    "required_contexts": contexts,
                    "bound_at_required_contexts": _crc_excess(
                        int(catalog_size), contexts, loss_bound=loss_bound
                    ),
                    "pointwise_zero_loss_terminal_required": True,
                    "power_guarantee": False,
                }
            )
    ltt_catalog = int(contract["ltt_catalog_size"])
    for route in contract["ltt_multiplicity_routes"]:
        per_policy_delta = delta / ltt_catalog if route == "bonferroni" else delta
        for empirical_loss in contract["ltt_empirical_losses"]:
            observed = float(empirical_loss)
            gap = alpha - observed
            if gap <= 0.0:
                raise RuntimeError("A locked LTT empirical-loss row has no positive risk margin.")
            hoeffding_n = math.ceil(math.log(1.0 / per_policy_delta) / (2.0 * gap**2))
            hoeffding_bound = observed + math.sqrt(
                math.log(1.0 / per_policy_delta) / (2.0 * hoeffding_n)
            )
            rows.append(
                {
                    "study": "ltt_optimistic_bounded_loss_design_only",
                    "method": "hoeffding_upper_mean_bound",
                    "risk_bound_mode": "single_policy_tail_bound",
                    "catalog_size": ltt_catalog,
                    "target_risk": alpha,
                    "loss_lower_bound": loss_lower,
                    "loss_upper_bound": loss_upper,
                    "empirical_loss": observed,
                    "margin_or_excess_target": gap,
                    "multiplicity_route": str(route),
                    "nominal_tail_probability": str(delta),
                    "per_policy_tail_probability": str(per_policy_delta),
                    "required_contexts": hoeffding_n,
                    "bound_at_required_contexts": hoeffding_bound,
                    "pointwise_zero_loss_terminal_required": False,
                    "power_guarantee": False,
                }
            )
            divergence = _binary_kl(observed, alpha)
            kl_n = math.ceil(math.log(1.0 / per_policy_delta) / divergence)
            kl_p_value_bound = math.exp(-kl_n * divergence)
            rows.append(
                {
                    "study": "ltt_optimistic_bounded_loss_design_only",
                    "method": "kl_chernoff_p_value_bound",
                    "risk_bound_mode": "single_policy_tail_bound",
                    "catalog_size": ltt_catalog,
                    "target_risk": alpha,
                    "loss_lower_bound": loss_lower,
                    "loss_upper_bound": loss_upper,
                    "empirical_loss": observed,
                    "margin_or_excess_target": gap,
                    "multiplicity_route": str(route),
                    "nominal_tail_probability": str(delta),
                    "per_policy_tail_probability": str(per_policy_delta),
                    "required_contexts": kl_n,
                    "bound_at_required_contexts": kl_p_value_bound,
                    "pointwise_zero_loss_terminal_required": False,
                    "power_guarantee": False,
                }
            )
    frame = pd.DataFrame(rows)
    expected = len(contract["crc_catalog_sizes"]) * len(contract["crc_excess_targets"]) + (
        len(contract["ltt_multiplicity_routes"]) * len(contract["ltt_empirical_losses"]) * 2
    )
    if len(frame) != expected:
        raise RuntimeError("The CRC/LTT analytic grid is incomplete.")
    return frame.sort_values(
        ["study", "catalog_size", "method", "multiplicity_route", "empirical_loss"],
        kind="stable",
    ).reset_index(drop=True)


def _build_monotonicity_counterexample() -> pd.DataFrame:
    rows = [
        {
            "lambda_index": 0,
            "loan_id": "A",
            "prediction_set": "{0}",
            "set_size": 1,
            "objective_value": 2.0,
            "worst_label_coefficient": 0.0,
            "upper_cap": 0.0,
            "feasible": True,
            "selected": True,
            "allocation": 1.0,
            "realized_label": 0,
            "unit_miss": 0,
            "portfolio_loss_contribution": 0.0,
        },
        {
            "lambda_index": 0,
            "loan_id": "B",
            "prediction_set": "{0}",
            "set_size": 1,
            "objective_value": 1.0,
            "worst_label_coefficient": 0.0,
            "upper_cap": 0.0,
            "feasible": True,
            "selected": False,
            "allocation": 0.0,
            "realized_label": 1,
            "unit_miss": 1,
            "portfolio_loss_contribution": 0.0,
        },
        {
            "lambda_index": 1,
            "loan_id": "A",
            "prediction_set": "{0,1}",
            "set_size": 2,
            "objective_value": 2.0,
            "worst_label_coefficient": 1.0,
            "upper_cap": 0.0,
            "feasible": False,
            "selected": False,
            "allocation": 0.0,
            "realized_label": 0,
            "unit_miss": 0,
            "portfolio_loss_contribution": 0.0,
        },
        {
            "lambda_index": 1,
            "loan_id": "B",
            "prediction_set": "{0}",
            "set_size": 1,
            "objective_value": 1.0,
            "worst_label_coefficient": 0.0,
            "upper_cap": 0.0,
            "feasible": True,
            "selected": True,
            "allocation": 1.0,
            "realized_label": 1,
            "unit_miss": 1,
            "portfolio_loss_contribution": 1.0,
        },
    ]
    frame = pd.DataFrame(rows)
    if not frame["allocation"].eq(frame["selected"].astype(float)).all():
        raise RuntimeError("The counterexample allocation and selected flags disagree.")
    if frame.groupby("lambda_index")["allocation"].sum().to_dict() != {0: 1.0, 1: 1.0}:
        raise RuntimeError("The counterexample does not allocate one unit at each lambda.")
    if not frame["portfolio_loss_contribution"].eq(frame["allocation"] * frame["unit_miss"]).all():
        raise RuntimeError("A counterexample contribution is not allocation times unit miss.")
    portfolio_loss = frame.groupby("lambda_index")["portfolio_loss_contribution"].transform("sum")
    frame["portfolio_loss"] = portfolio_loss
    if frame.groupby("lambda_index")["portfolio_loss"].first().to_dict() != {
        0: 0.0,
        1: 1.0,
    }:
        raise RuntimeError("The locked reoptimization counterexample changed.")
    sets = frame.pivot(index="loan_id", columns="lambda_index", values="prediction_set")
    if sets.loc["A", 0] != "{0}" or sets.loc["A", 1] != "{0,1}":
        raise RuntimeError("Loan A prediction sets are not the locked nested pair.")
    if sets.loc["B", 0] != "{0}" or sets.loc["B", 1] != "{0}":
        raise RuntimeError("Loan B prediction sets are not the locked nested pair.")
    return frame


def _count_and_dollar_fcp_from_allocations(
    miss_indicators: Sequence[int],
    allocations: Sequence[float],
    *,
    budget: float,
) -> tuple[Fraction, Fraction]:
    """Compute count and dollar FCP on independent arithmetic paths."""

    misses = tuple(int(value) for value in miss_indicators)
    if not misses or any(value not in {0, 1} for value in misses):
        raise ValueError("Miss indicators must be a nonempty binary sequence.")
    if len(allocations) != len(misses):
        raise ValueError("Allocations and miss indicators must align.")
    weights = tuple(Fraction(str(float(value))) for value in allocations)
    if any(weight <= 0 for weight in weights):
        raise ValueError("Every selected allocation must be strictly positive.")
    capital = Fraction(str(float(budget)))
    if capital <= 0:
        raise ValueError("Budget must be strictly positive.")
    invested = sum(weights, Fraction(0, 1))
    if invested != capital:
        raise RuntimeError("Actual selected allocations do not sum exactly to budget B.")
    count_fcp = Fraction(sum(misses), len(misses))
    weighted_misses = sum(
        (weight * miss for weight, miss in zip(weights, misses, strict=True)),
        Fraction(0, 1),
    )
    dollar_fcp = weighted_misses / invested
    return count_fcp, dollar_fcp


def _run_primary_replications(
    *,
    design: Mapping[str, Any],
    model: FrozenProbabilityModel,
    replication_seed_streams: Mapping[str, Sequence[np.random.SeedSequence]],
    observer: LongRunObserver,
    heartbeat: ObserverHeartbeat | None,
    run_started: float,
    wall_deadline_seconds: float,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    repetitions = int(design["repetitions"])
    if set(replication_seed_streams) != set(REPLICATION_RNG_STREAMS):
        raise ValueError("Replication RNG streams differ from the locked role partition.")
    if any(len(replication_seed_streams[name]) != repetitions for name in REPLICATION_RNG_STREAMS):
        raise ValueError("Replication seed count differs from the locked denominator.")
    n = int(design["calibration_size"])
    m = int(design["test_size"])
    k = int(design["selected_k"])
    alpha = float(design["alpha"])
    budget = float(design["budget_units"])
    feature_count = int(design["feature_count"])
    lgd = float(_mapping(design["primary_dgp"], label="primary_dgp")["synthetic_lgd"])
    resolution = reference_resolution_size(alpha)
    allocation = float(design["allocation_per_selected_unit"])
    if Fraction(str(allocation)) != Fraction(str(budget)) / k:
        raise RuntimeError("The equal-notional allocation does not reconcile to B/K.")
    actual_allocations = tuple(allocation for _ in range(k))

    replication_rows: list[dict[str, Any]] = []
    focal_columns: dict[str, list[Any]] = {
        "replication_id": [],
        "selected_rank": [],
        "test_index": [],
        "reference_size": [],
        "jomi_threshold": [],
        "jomi_include_0": [],
        "jomi_include_1": [],
        "jomi_set_size": [],
        "outcome": [],
        "jomi_miss": [],
        "vanilla_threshold": [],
        "vanilla_include_0": [],
        "vanilla_include_1": [],
        "vanilla_set_size": [],
        "vanilla_miss": [],
        "allocation": [],
    }
    for replication_id in range(repetitions):
        if time.perf_counter() - run_started >= wall_deadline_seconds:
            raise TimeoutError("The locked wall deadline was reached at a replication boundary.")
        if heartbeat is not None:
            heartbeat.check()
        replication_rng = {
            name: np.random.default_rng(replication_seed_streams[name][replication_id])
            for name in REPLICATION_RNG_STREAMS
        }
        calibration_x = replication_rng["replication_calibration_features"].standard_normal(
            (n, feature_count)
        )
        test_x = replication_rng["replication_test_features"].standard_normal((m, feature_count))
        # Priorities are assigned before either label vector is sampled.
        priorities = replication_rng["replication_tie_priorities"].random(n + m)
        if len(np.unique(priorities)) != n + m:
            raise RuntimeError("A primary replication contained an exact priority tie.")
        calibration_y = (
            replication_rng["replication_calibration_labels"]
            .binomial(1, _true_probability(calibration_x))
            .astype(np.int8)
        )
        test_y = (
            replication_rng["replication_test_labels"]
            .binomial(1, _true_probability(test_x))
            .astype(np.int8)
        )
        calibration_q = model.predict(calibration_x)
        test_q = model.predict(test_x)
        calibration_score = (1.0 - calibration_q) * _synthetic_rate(
            calibration_x
        ) - lgd * calibration_q
        test_score = (1.0 - test_q) * _synthetic_rate(test_x) - lgd * test_q

        calibration_score_values = _core_sequence(calibration_score)
        calibration_priority_values = _core_sequence(priorities[:n])
        test_score_values = _core_sequence(test_score)
        test_priority_values = _core_sequence(priorities[n:])
        selected = select_top_k(test_score_values, test_priority_values, k)
        if len(selected) != k:
            raise RuntimeError("A primary replication did not select exactly K test units.")
        reference = top_k_reference_set(
            calibration_score_values,
            calibration_priority_values,
            test_score_values,
            test_priority_values,
            k,
        )
        reference_size = len(reference)
        if reference_size < resolution:
            raise RuntimeError(
                f"Primary replication {replication_id} has reference size "
                f"{reference_size} below r_alpha={resolution}."
            )
        reference_indices = np.asarray(reference, dtype=int)
        calibration_nonconformity = np.abs(calibration_y - calibration_q)
        jomi_threshold = _finite_conformal_threshold(
            calibration_nonconformity[reference_indices],
            alpha=alpha,
        )
        vanilla_threshold = _finite_conformal_threshold(calibration_nonconformity, alpha=alpha)
        selected_indices = np.asarray(selected, dtype=int)
        selected_q = test_q[selected_indices]
        selected_y = test_y[selected_indices]
        jomi_zero, jomi_one = _prediction_membership(selected_q, jomi_threshold)
        vanilla_zero, vanilla_one = _prediction_membership(selected_q, vanilla_threshold)
        jomi_miss = _misses(selected_y, jomi_zero, jomi_one)
        vanilla_miss = _misses(selected_y, vanilla_zero, vanilla_one)

        # Exercise the public two-label inversion on one focal unit each time.
        include_zero, include_one, reconciled_threshold = deterministic_binary_prediction_sets(
            (selected_q[0], 1.0 - selected_q[0]),
            calibration_nonconformity[reference_indices],
            alpha,
        )
        if (
            include_zero != bool(jomi_zero[0])
            or include_one != bool(jomi_one[0])
            or reconciled_threshold != jomi_threshold
        ):
            raise RuntimeError("The vectorized primary inversion differs from the exact core.")

        jomi_count_fcp, jomi_dollar_fcp = _count_and_dollar_fcp_from_allocations(
            jomi_miss.tolist(),
            actual_allocations,
            budget=budget,
        )
        vanilla_count_fcp, vanilla_dollar_fcp = _count_and_dollar_fcp_from_allocations(
            vanilla_miss.tolist(),
            actual_allocations,
            budget=budget,
        )
        if jomi_count_fcp != jomi_dollar_fcp:
            raise RuntimeError("Equal-notional JOMI count and dollar FCP differ.")
        if vanilla_count_fcp != vanilla_dollar_fcp:
            raise RuntimeError("Equal-notional vanilla count and dollar FCP differ.")
        replication_rows.append(
            {
                "replication_id": replication_id,
                "reference_size": reference_size,
                "selected_count": k,
                "jomi_miss_count": int(jomi_miss.sum()),
                "jomi_count_fcp": float(jomi_count_fcp),
                "jomi_dollar_fcp": float(jomi_dollar_fcp),
                "jomi_average_set_size": float(np.mean(jomi_zero.astype(int) + jomi_one)),
                "vanilla_miss_count": int(vanilla_miss.sum()),
                "vanilla_count_fcp": float(vanilla_count_fcp),
                "vanilla_dollar_fcp": float(vanilla_dollar_fcp),
                "vanilla_average_set_size": float(np.mean(vanilla_zero.astype(int) + vanilla_one)),
            }
        )
        focal_columns["replication_id"].extend([replication_id] * k)
        focal_columns["selected_rank"].extend(range(k))
        focal_columns["test_index"].extend(int(value) for value in selected_indices)
        focal_columns["reference_size"].extend([reference_size] * k)
        focal_columns["jomi_threshold"].extend([jomi_threshold] * k)
        focal_columns["jomi_include_0"].extend(bool(value) for value in jomi_zero)
        focal_columns["jomi_include_1"].extend(bool(value) for value in jomi_one)
        focal_columns["jomi_set_size"].extend(
            int(value) for value in jomi_zero.astype(int) + jomi_one.astype(int)
        )
        focal_columns["outcome"].extend(int(value) for value in selected_y)
        focal_columns["jomi_miss"].extend(int(value) for value in jomi_miss)
        focal_columns["vanilla_threshold"].extend([vanilla_threshold] * k)
        focal_columns["vanilla_include_0"].extend(bool(value) for value in vanilla_zero)
        focal_columns["vanilla_include_1"].extend(bool(value) for value in vanilla_one)
        focal_columns["vanilla_set_size"].extend(
            int(value) for value in vanilla_zero.astype(int) + vanilla_one.astype(int)
        )
        focal_columns["vanilla_miss"].extend(int(value) for value in vanilla_miss)
        focal_columns["allocation"].extend(actual_allocations)
        observer.emit(
            replication_id + 1,
            phase="computing_primary_replications",
            detail={"current_unit_key": f"replication/{replication_id + 1}"},
        )

    replications = pd.DataFrame(replication_rows)
    focal = pd.DataFrame(focal_columns)
    expected_ids = np.arange(repetitions, dtype=int)
    if not np.array_equal(replications["replication_id"].to_numpy(dtype=int), expected_ids):
        raise RuntimeError("Primary replication IDs are missing, duplicated, or out of order.")
    focal_counts = focal.groupby("replication_id", sort=True).size().to_numpy(dtype=int)
    if not np.array_equal(focal_counts, np.full(repetitions, k, dtype=int)):
        raise RuntimeError("Focal output does not contain exactly K rows per replication.")
    if not bool(replications["jomi_count_fcp"].equals(replications["jomi_dollar_fcp"])):
        raise RuntimeError("Primary count and dollar JOMI FCP columns differ.")
    if not bool(replications["vanilla_count_fcp"].equals(replications["vanilla_dollar_fcp"])):
        raise RuntimeError("Comparator count and dollar FCP columns differ.")
    mean_fcp = float(replications["jomi_count_fcp"].mean())
    delta = 0.001
    hoeffding_radius = math.sqrt(math.log(1.0 / delta) / (2.0 * repetitions))
    lower_bound = max(0.0, mean_fcp - hoeffding_radius)
    if lower_bound > alpha:
        raise RuntimeError("The locked 99.9% Hoeffding implementation-warning bound exceeds alpha.")
    summary = {
        "mean_replication_jomi_fcp": mean_fcp,
        "one_sided_999_hoeffding_lower_bound": lower_bound,
        "hoeffding_radius": hoeffding_radius,
        "mean_replication_vanilla_fcp": float(replications["vanilla_count_fcp"].mean()),
        "minimum_reference_size": float(replications["reference_size"].min()),
        "maximum_reference_size": float(replications["reference_size"].max()),
        "mean_reference_size": float(replications["reference_size"].mean()),
    }
    return replications, focal, summary


def _require_finite_frame(frame: pd.DataFrame, *, label: str) -> None:
    if frame.empty:
        raise RuntimeError(f"{label} must not be empty.")
    if bool(frame.columns.duplicated().any()):
        raise RuntimeError(f"{label} contains duplicate columns.")
    numeric = frame.select_dtypes(include=[np.number])
    if numeric.size and not bool(np.isfinite(numeric.to_numpy(dtype=float)).all()):
        raise RuntimeError(f"{label} contains a nonfinite numeric value.")
    if bool(frame.isna().any().any()):
        raise RuntimeError(f"{label} contains a missing value.")


def _stage_frames(
    frames: Mapping[str, pd.DataFrame], *, staging_directory: Path
) -> dict[str, Path]:
    staging_directory.mkdir(parents=True, exist_ok=False)
    staged: dict[str, Path] = {}
    for filename in DATA_FILENAMES:
        frame = frames.get(filename)
        if frame is None:
            raise RuntimeError(f"Missing staged frame for {filename}.")
        _require_finite_frame(frame, label=filename)
        target = staging_directory / filename
        if target.exists():
            raise FileExistsError(target)
        staged[filename] = atomic_write_parquet(frame, target, index=False)
        recovered = pd.read_parquet(target)
        pd.testing.assert_frame_equal(recovered, frame, check_exact=True)
    if set(frames) != set(DATA_FILENAMES):
        raise RuntimeError(
            "The staged scientific frame family differs from the locked seven files."
        )
    return staged


def _portable_descriptor(staged: Path, *, official_relative_path: str) -> dict[str, Any]:
    return {
        "path": official_relative_path,
        "bytes": int(staged.stat().st_size),
        "sha256": sha256_file(staged),
    }


def _materialize_staged_outputs(
    staged: Mapping[str, Path],
    *,
    config: Mapping[str, Any],
    repo_root: Path,
    on_promoted: Callable[[Mapping[str, Path]], None] | None = None,
) -> dict[str, Path]:
    _require_fresh_official_outputs(config, repo_root=repo_root)
    expected_names = {*DATA_FILENAMES, SUMMARY_FILENAME, RECEIPT_FILENAME}
    if set(staged) != expected_names:
        raise RuntimeError("The staged artifact family differs from the locked nine files.")

    root = repo_root.resolve()
    data_parent = (root / ALLOWED_DATA_ROOT).resolve()
    model_parent = (root / ALLOWED_MODEL_ROOT).resolve()
    for parent in (data_parent, model_parent):
        try:
            parent.relative_to(root)
        except ValueError as error:
            raise ValueError(
                f"Official artifact parent escaped the repository: {parent}"
            ) from error
        parent.mkdir(parents=True, exist_ok=True)

    final_data = data_parent / EXPECTED_RUN_TAG
    final_model = model_parent / EXPECTED_RUN_TAG
    transaction = uuid4().hex
    # Keep transaction names short enough for Windows MAX_PATH even under the
    # deeply nested temporary roots used by the test suite.
    transaction_prefix = ".jomi-txn-"
    temporary_data = data_parent / f"{transaction_prefix}{transaction}"
    temporary_model = model_parent / f"{transaction_prefix}{transaction}"
    promoted_data = False
    promoted_model = False

    def remove_transaction_directory(path: Path, *, parent: Path) -> None:
        resolved = path.resolve()
        if resolved.parent != parent or not resolved.name.startswith(transaction_prefix):
            raise RuntimeError(f"Refusing to clean an unexpected transaction path: {resolved}")
        if resolved.exists():
            shutil.rmtree(resolved)

    try:
        temporary_data.mkdir()
        temporary_model.mkdir()
        temporary_written: dict[str, Path] = {}
        for filename in DATA_FILENAMES:
            temporary_written[filename] = atomic_write_bytes(
                temporary_data / filename,
                staged[filename].read_bytes(),
            )
        for filename in (SUMMARY_FILENAME, RECEIPT_FILENAME):
            temporary_written[filename] = atomic_write_bytes(
                temporary_model / filename,
                staged[filename].read_bytes(),
            )
        for filename, path in temporary_written.items():
            if sha256_file(path) != sha256_file(staged[filename]):
                raise RuntimeError(f"Transactional artifact hash mismatch for {filename}.")

        _require_fresh_official_outputs(config, repo_root=root)
        os.replace(temporary_data, final_data)
        promoted_data = True
        os.replace(temporary_model, final_model)
        promoted_model = True
        written = {
            **{filename: final_data / filename for filename in DATA_FILENAMES},
            SUMMARY_FILENAME: final_model / SUMMARY_FILENAME,
            RECEIPT_FILENAME: final_model / RECEIPT_FILENAME,
        }
        if (
            tuple(
                relative_artifact_descriptor(written[Path(path).name], repo_root=root)["path"]
                for path in EXPECTED_OUTPUT_PATHS
            )
            != EXPECTED_OUTPUT_PATHS
        ):
            raise RuntimeError("Materialized output paths differ from the locked transport list.")
        for filename, path in written.items():
            if sha256_file(path) != sha256_file(staged[filename]):
                raise RuntimeError(f"Materialized artifact hash mismatch for {filename}.")
        if on_promoted is not None:
            on_promoted(written)
        return written
    except BaseException:
        rollback_errors: list[BaseException] = []
        for promoted, final, temporary in (
            (promoted_model, final_model, temporary_model),
            (promoted_data, final_data, temporary_data),
        ):
            if promoted and final.exists():
                try:
                    os.replace(final, temporary)
                except BaseException as error:
                    # Both final paths are exact fresh directories created by
                    # this transaction.  If rename-back itself is unavailable,
                    # remove that transaction-owned partial family fail-closed.
                    try:
                        if final.resolve().parent not in {data_parent, model_parent}:
                            raise RuntimeError("Unexpected official rollback target.")
                        shutil.rmtree(final)
                    except BaseException:
                        rollback_errors.append(error)
        if rollback_errors:
            raise RuntimeError(
                "Official artifact transaction failed and could not be rolled back cleanly."
            ) from rollback_errors[0]
        raise
    finally:
        remove_transaction_directory(temporary_data, parent=data_parent)
        remove_transaction_directory(temporary_model, parent=model_parent)


def run(
    *,
    config_path: Path = CONFIG_PATH,
    repo_root: Path = ROOT,
    runtime_root: Path | None = None,
) -> Path:
    """Execute the complete sealed study and return the official summary path."""

    started_at = _utc_now()
    run_started = time.perf_counter()
    root = Path(repo_root).resolve()
    resolved_config = (
        (root / config_path).resolve() if not config_path.is_absolute() else config_path.resolve()
    )
    try:
        resolved_config.relative_to(root)
    except ValueError as error:
        raise ValueError("The experiment config must remain inside the repository.") from error
    config = _load_config(resolved_config)
    _require_fixed_contract(config)
    protocol_path = (root / str(config["protocol_path"])).resolve()
    if not protocol_path.is_file():
        raise FileNotFoundError(protocol_path)
    protocol_commit = _require_clean_annotated_head(root, str(config["protocol_tag"]))
    _require_fresh_official_outputs(config, repo_root=root)
    initial_git = git_provenance(root)
    implementation_start = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    runtime_contract = _mapping(config["runtime"], label="runtime")
    chosen_runtime_root = (
        Path(str(runtime_contract["preferred_runtime_root"]))
        if runtime_root is None
        else Path(runtime_root)
    )
    runtime_directory = _prepare_runtime_directory(
        chosen_runtime_root,
        repo_root=root,
        config=config,
    )
    priority_state = _set_below_normal_priority()
    observer = LongRunObserver(
        stage_name="equal-notional-fixed-k-jomi-synthetic-feasibility",
        run_tag=str(config["run_tag"]),
        protocol_tag=str(config["protocol_tag"]),
        total_units=int(_mapping(config["design"], label="design")["repetitions"]),
        unit_name="complete_replications",
        status_path=runtime_directory / "status" / "latest.json",
        heartbeat_seconds=float(runtime_contract["heartbeat_seconds"]),
        minimum_eta_units=10,
        no_progress_after_seconds=180.0,
        forbidden_roots=(root,),
    )
    heartbeat = ObserverHeartbeat(observer, seconds=float(runtime_contract["heartbeat_seconds"]))
    heartbeat.start()
    phase_seconds: dict[str, float] = {}
    current_phase = "preflight"
    try:
        observer.emit(
            0,
            phase=current_phase,
            detail={"operation": "sealed authority and runtime checks"},
            force=True,
        )
        current_phase = "validating_controls"
        heartbeat.set_phase("validating_controls", "theorem-to-code controls")
        phase_started = time.perf_counter()
        oracle = _build_oracle_reconciliation(config)
        analytic = _build_analytic_reference_frontier(config)
        scale = _build_scale_fixtures(config)
        crc_ltt = _build_crc_ltt_feasibility(config)
        counterexample = _build_monotonicity_counterexample()
        phase_seconds["validating_controls"] = time.perf_counter() - phase_started
        heartbeat.check()

        current_phase = "fitting_frozen_model"
        heartbeat.set_phase(current_phase, "one learner and one Platt fit")
        observer.emit(
            0,
            phase=current_phase,
            detail={"operation": "fitting frozen synthetic learner"},
            force=True,
        )
        design_contract = _mapping(config["design"], label="design")
        fixed_rng, replication_seed_streams = _spawn_locked_rng_streams(design_contract)
        phase_started = time.perf_counter()
        model = _fit_frozen_model(
            train_feature_rng=fixed_rng["training_features"],
            train_label_rng=fixed_rng["training_labels"],
            design_feature_rng=fixed_rng["design_features"],
            design_label_rng=fixed_rng["design_labels"],
            design=design_contract,
        )
        model_fingerprint = model.fingerprint
        phase_seconds[current_phase] = time.perf_counter() - phase_started

        current_phase = "computing_primary_replications"
        heartbeat.set_phase(current_phase, "complete synthetic replications")
        observer.emit(
            0,
            phase=current_phase,
            detail={"operation": "starting primary replication census"},
            force=True,
        )
        phase_started = time.perf_counter()
        with threadpool_limits(limits=1):
            replications, focal, primary_summary = _run_primary_replications(
                design=design_contract,
                model=model,
                replication_seed_streams=replication_seed_streams,
                observer=observer,
                heartbeat=heartbeat,
                run_started=run_started,
                wall_deadline_seconds=float(runtime_contract["wall_deadline_seconds"]),
            )
        phase_seconds[current_phase] = time.perf_counter() - phase_started
        if _model_fingerprint(model.learner, model.platt) != model_fingerprint:
            raise RuntimeError(
                "The frozen probability model changed during replication evaluation."
            )

        current_phase = "validating_scientific_state"
        heartbeat.set_phase(current_phase, "complete-frame scientific gates")
        observer.emit(
            int(_mapping(config["design"], label="design")["repetitions"]),
            phase=current_phase,
            detail={"operation": "validating complete scientific frames"},
            force=True,
        )
        phase_started = time.perf_counter()
        frames = {
            "replications.parquet": replications,
            "focal_results.parquet": focal,
            "analytic_reference_frontier.parquet": analytic,
            "oracle_reconciliation.parquet": oracle,
            "scale_fixtures.parquet": scale,
            "crc_ltt_feasibility.parquet": crc_ltt,
            "monotonicity_counterexample.parquet": counterexample,
        }
        for filename, frame in frames.items():
            _require_finite_frame(frame, label=filename)
        if time.perf_counter() - run_started >= float(runtime_contract["wall_deadline_seconds"]):
            raise TimeoutError("The locked wall deadline was reached before staging.")
        implementation_end = implementation_provenance(
            config_path=resolved_config,
            relative_paths=IMPLEMENTATION_PATHS,
            repo_root=root,
        )
        if implementation_end != implementation_start:
            raise RuntimeError("The JOMI implementation changed during execution.")
        if _require_clean_annotated_head(root, str(config["protocol_tag"])) != protocol_commit:
            raise RuntimeError("Git authority changed during execution.")
        phase_seconds[current_phase] = time.perf_counter() - phase_started

        current_phase = "staging"
        heartbeat.set_phase(current_phase, "external atomic staging")
        phase_started = time.perf_counter()
        staged = _stage_frames(frames, staging_directory=runtime_directory / "staging")
        data_descriptors = {
            filename: _portable_descriptor(
                staged[filename],
                official_relative_path=(ALLOWED_DATA_ROOT / EXPECTED_RUN_TAG / filename).as_posix(),
            )
            for filename in DATA_FILENAMES
        }
        summary_payload = {
            "schema_version": str(config["schema_version"]),
            "status": "complete_synthetic_theorem_to_code_validation_pending_git_transport",
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "planned_artifact_tag": str(config["artifact_tag"]),
            "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
            "config": relative_artifact_descriptor(resolved_config, repo_root=root),
            "design": dict(_mapping(config["design"], label="design")),
            "primary_results": primary_summary,
            "control_census": {
                "oracle_rows": len(oracle),
                "analytic_frontier_rows": len(analytic),
                "scale_fixture_rows": len(scale),
                "crc_ltt_rows": len(crc_ltt),
                "counterexample_rows": len(counterexample),
            },
            "model": {
                "fingerprint_sha256": model_fingerprint,
                "learner_coefficients": model.learner.coef_.astype(float).tolist(),
                "learner_intercept": model.learner.intercept_.astype(float).tolist(),
                "platt_coefficients": model.platt.coef_.astype(float).tolist(),
                "platt_intercept": model.platt.intercept_.astype(float).tolist(),
                "fit_once_then_frozen": True,
            },
            "artifacts": data_descriptors,
            "frame_schemas": {name: dataframe_schema(frame) for name, frame in frames.items()},
            "interpretation": dict(_mapping(config["interpretation"], label="interpretation")),
            "implementation_provenance": implementation_start,
            "environment": environment_provenance(root),
            "initial_git": initial_git,
            "artifact_commit_status": "pending_single_direct_child_commit_and_annotated_tag",
            "protected_stages_run": [],
            "protected_artifacts_read": [],
            "protected_artifacts_written": [],
        }
        summary_staged = runtime_directory / "staging" / SUMMARY_FILENAME
        atomic_write_strict_json(summary_staged, summary_payload)
        staged[SUMMARY_FILENAME] = summary_staged
        summary_descriptor = _portable_descriptor(
            summary_staged,
            official_relative_path=(
                ALLOWED_MODEL_ROOT / EXPECTED_RUN_TAG / SUMMARY_FILENAME
            ).as_posix(),
        )
        # The receipt cannot include the time required to serialize itself, but it
        # must not omit the substantial frame-and-summary staging phase.
        phase_seconds[current_phase] = time.perf_counter() - phase_started
        completed_at = _utc_now()
        receipt_payload = {
            "schema_version": str(config["schema_version"]),
            "status": "complete_protocol_tagged_synthetic_execution_receipt",
            "run_tag": str(config["run_tag"]),
            "started_at_utc": started_at,
            "completed_at_utc": completed_at,
            "runtime_seconds": float(time.perf_counter() - run_started),
            "phase_seconds": phase_seconds,
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "planned_artifact_tag": str(config["artifact_tag"]),
            "summary": summary_descriptor,
            "artifacts": data_descriptors,
            "implementation_provenance": implementation_start,
            "initial_git": initial_git,
            "final_prewrite_git": git_provenance(root),
            "environment": environment_provenance(root),
            "runtime": {
                "observer": "LongRunObserver",
                "atomic_units_completed": int(
                    _mapping(config["design"], label="design")["repetitions"]
                ),
                "resume_used": False,
                "resume_authorized": False,
                "workers": 1,
                "process_priority_state": priority_state,
                "absolute_runtime_path_serialized": False,
            },
            "promotion_boundary": (
                "Synthetic theorem-to-code validation only; one direct-child artifact commit "
                "and annotated artifact tag remain pending. No active-paper or real-data "
                "selected-set validity is promoted."
            ),
            "protected_stages_run": [],
            "protected_artifacts_read": [],
            "protected_artifacts_written": [],
        }
        receipt_staged = runtime_directory / "staging" / RECEIPT_FILENAME
        atomic_write_strict_json(receipt_staged, receipt_payload)
        staged[RECEIPT_FILENAME] = receipt_staged

        current_phase = "materializing"
        heartbeat.set_phase(current_phase, "official no-overwrite materialization")
        if time.perf_counter() - run_started >= float(runtime_contract["wall_deadline_seconds"]):
            raise TimeoutError(
                "The locked wall deadline was reached before official materialization."
            )
        heartbeat.check()
        if (
            implementation_provenance(
                config_path=resolved_config,
                relative_paths=IMPLEMENTATION_PATHS,
                repo_root=root,
            )
            != implementation_start
        ):
            raise RuntimeError("The JOMI implementation changed before materialization.")
        if _require_clean_annotated_head(root, str(config["protocol_tag"])) != protocol_commit:
            raise RuntimeError("Git authority changed before materialization.")
        _require_fresh_official_outputs(config, repo_root=root)

        def seal_observer(_written: Mapping[str, Path]) -> None:
            if (
                implementation_provenance(
                    config_path=resolved_config,
                    relative_paths=IMPLEMENTATION_PATHS,
                    repo_root=root,
                )
                != implementation_start
            ):
                raise RuntimeError("The JOMI implementation changed during materialization.")
            if _require_clean_annotated_head(root, str(config["protocol_tag"])) != protocol_commit:
                raise RuntimeError("Git authority changed during materialization.")
            heartbeat.stop()
            observer.complete(
                phase="sealing",
                detail={"operation": "official outputs sealed"},
            )

        written = _materialize_staged_outputs(
            staged,
            config=config,
            repo_root=root,
            on_promoted=seal_observer,
        )
        return written[SUMMARY_FILENAME]
    except BaseException as error:
        with suppress(BaseException):
            heartbeat.stop()
        with suppress(BaseException):
            observer.fail(
                phase=current_phase,
                reason=f"{type(error).__name__}: {str(error)[:180]}",
                detail={"operation": "failed before complete seal"},
            )
        raise


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=Path("D:/CRPTO/runtime"),
        help="External operational root; the run tag is appended as one fresh child.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    print(
        run(
            config_path=args.config,
            repo_root=args.repo_root,
            runtime_root=args.runtime_root,
        )
    )


if __name__ == "__main__":
    main()
