"""Hash-bound two-phase protocol for the IJDS calibrator sensitivity."""

from __future__ import annotations

import json
import pickle
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml
from scipy.special import expit
from sklearn.linear_model import LogisticRegression

from src.data.outcome_observability import (
    build_outcome_label_availability,
    parse_issue_dates,
    parse_term_months,
    terminal_outcome_from_status,
)
from src.ijds_audit.calibrator_sensitivity import (
    CALIBRATOR_METHODS,
    CANONICAL_GROUPS,
    STRING_HASH_CONTRACT,
    VECTOR_HASH_CONTRACT,
    WINDOW_IDS,
    CalibratorFamily,
    CalibratorResidualRecipe,
    apply_calibrator_family,
    apply_common_taxonomy_recipe,
    assign_common_groups,
    calibration_fit_diagnostics,
    calibrator_state_audit,
    coverage_cell,
    fit_calibrator_family,
    fit_common_taxonomy_recipe,
    float_array_sha256,
    geometry_summary,
    load_recipe_payload,
    monotonicity_audit,
    recipe_payload,
    recover_catboost_base_probability,
    shared_completion_coverage_difference,
    string_array_sha256,
    transform_platt_edges_to_q_raw,
    unordered_method_pairs,
)
from src.ijds_audit.config import load_v4_config
from src.ijds_audit.prediction import binary_probability_metrics
from src.ijds_audit.protocol import (
    configured_archive_outcomes,
    load_outcome_universe,
    load_recipes,
)
from src.models.binary_conformal_guardrail import assign_conformal_groups
from src.utils.artifact_descriptor import relative_artifact_descriptor, verified_artifact_path
from src.utils.isolated_experiment import (
    environment_provenance,
    implementation_provenance,
    prepare_output_paths,
    require_clean_tagged_head,
    resolve_repo_input,
)
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_parquet, atomic_write_pickle

ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
FREEZE_RUN_TAG = "ijds-calibrator-sensitivity-2026-07-30-v1-source"
FREEZE_PROTOCOL_TAG = "protocol/ijds-calibrator-sensitivity-2026-07-30-v1"
FREEZE_SOURCE_TAG = "artifacts/ijds-calibrator-sensitivity-2026-07-30-v1-source"
EVALUATION_PROTOCOL_TAG = "protocol/ijds-calibrator-sensitivity-evaluation-2026-07-30-v1"
EVALUATION_RUN_TAG = "ijds-calibrator-sensitivity-2026-07-30-v1"
FINAL_ARTIFACT_TAG = "artifacts/ijds-calibrator-sensitivity-2026-07-30-v1"
FREEZE_STATUS = "calibrator_maps_and_common_taxonomy_frozen_before_primary_oot_outcome_evaluation"
PENDING_TOKEN = "PENDING_AFTER_PHASE_A_FREEZE"
PHASE_A_COMMIT_PATHS = frozenset(
    {
        (
            "data/processed/experiments/ijds_audit/"
            f"{FREEZE_RUN_TAG}/prediction/calibration_fit_diagnostics.parquet"
        ),
        (
            "data/processed/experiments/ijds_audit/"
            f"{FREEZE_RUN_TAG}/prediction/outcome_free_geometry.parquet"
        ),
        (f"data/processed/experiments/ijds_audit/{FREEZE_RUN_TAG}/prediction/recipe_audit.parquet"),
        (f"models/experiments/ijds_audit/{FREEZE_RUN_TAG}/execution_receipt.json"),
        (f"models/experiments/ijds_audit/{FREEZE_RUN_TAG}/prediction/calibrator_family.pkl"),
        (
            "models/experiments/ijds_audit/"
            f"{FREEZE_RUN_TAG}/prediction/calibrator_residual_recipes.json"
        ),
        (f"models/experiments/ijds_audit/{FREEZE_RUN_TAG}/prediction/common_q_raw_taxonomy.json"),
        (f"models/experiments/ijds_audit/{FREEZE_RUN_TAG}/protocol_freeze.json"),
    }
)
PHASE_B_COMMIT_PATHS = frozenset(
    {
        "configs/experiments/ijds_calibrator_sensitivity_evaluation_2026-07-30_v1.yaml",
        "docs/research/ijds_calibrator_sensitivity_v1_evaluation_lock_2026-07-30.md",
    }
)


def _validate_locked_design(config: Mapping[str, Any]) -> Mapping[str, Any]:
    design = cast(Mapping[str, Any], config["design"])
    if tuple(str(value) for value in design["methods"]) != CALIBRATOR_METHODS:
        raise RuntimeError("The locked four-calibrator family or its order changed.")
    if tuple(str(value) for value in design["window_ids"]) != WINDOW_IDS:
        raise RuntimeError("The locked complete eight-window grid or its order changed.")
    if int(design["taxonomy_groups"]) != CANONICAL_GROUPS or float(design["alpha"]) != 0.10:
        raise RuntimeError("The locked five-stratum alpha=0.10 design changed.")
    hash_fields = (
        "expected_calibrator_fit_ordered_id_sha256",
        "expected_calibrator_fit_ordered_label_sha256",
        "expected_calibrator_fit_platt_probability_sha256",
    )
    if any(
        not isinstance(design.get(field), str)
        or len(str(design[field])) != 64
        or any(character not in "0123456789abcdef" for character in str(design[field]))
        for field in hash_fields
    ):
        raise RuntimeError("The locked 2011 calibrator-fit vector hashes are invalid.")
    if (
        int(design["expected_calibrator_fit_y0"]) != 12602
        or int(design["expected_calibrator_fit_y1"]) != 1475
        or float(design["platt_fit_reconciliation_tolerance"]) != 0.0
    ):
        raise RuntimeError("The locked 2011 Platt-fit census or exact replay tolerance changed.")
    return design


def load_calibrator_sensitivity_config(path: Path) -> dict[str, Any]:
    """Load either phase after enforcing its complete top-level contract."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Calibrator-sensitivity config must be a mapping.")
    required = {
        "schema_version",
        "phase",
        "run_tag",
        "protocol_tag",
        "source",
        "design",
        "output",
        "interpretation",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise ValueError(f"Calibrator-sensitivity config omits fields: {missing}.")
    return payload


def _descriptor_equal(
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    label: str,
) -> None:
    for field in ("path", "bytes", "sha256"):
        if actual.get(field) != expected.get(field):
            raise RuntimeError(f"{label} descriptor mismatched on {field}.")


def _annotated_tag_commit(repo_root: Path, tag: str) -> str:
    """Resolve a tag only when its ref points to an annotated tag object."""
    try:
        kind = subprocess.run(
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
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"Required annotated Git tag is unavailable: {tag}") from exc
    if kind != "tag" or not commit:
        raise RuntimeError(f"Git tag {tag!r} must be annotated and resolve to one commit.")
    return commit


def _require_annotated_clean_head(repo_root: Path, tag: str) -> str:
    commit = require_clean_tagged_head(repo_root, tag)
    if _annotated_tag_commit(repo_root, tag) != commit:
        raise RuntimeError(f"Annotated tag {tag!r} does not resolve to current HEAD.")
    return commit


def _require_direct_child(repo_root: Path, *, child: str, parent: str) -> None:
    try:
        lineage = (
            subprocess.run(
                ["git", "rev-list", "--parents", "-n", "1", child],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            .stdout.strip()
            .split()
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("Could not inspect the source-freeze Git lineage.") from exc
    if len(lineage) != 2 or lineage[0] != child or lineage[1] != parent:
        raise RuntimeError(f"Commit {child} must be the single direct child of {parent}.")


def _require_exact_commit_paths(
    repo_root: Path,
    *,
    commit: str,
    expected_paths: frozenset[str],
    label: str,
) -> None:
    """Require one commit to change exactly the predeclared path set."""
    try:
        raw = subprocess.run(
            [
                "git",
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "--no-renames",
                "-r",
                "-z",
                commit,
            ],
            cwd=repo_root,
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"Could not inspect the exact changed paths for {label}.") from exc
    if not isinstance(raw, bytes):
        raise TypeError("Git changed-path inspection must return bytes.")
    parts = tuple(
        value.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        for value in raw.split(b"\0")
        if value
    )
    observed = frozenset(parts)
    if len(parts) != len(observed) or observed != expected_paths:
        missing = sorted(expected_paths.difference(observed))
        extra = sorted(observed.difference(expected_paths))
        raise RuntimeError(
            f"{label} changed paths outside its exact contract; missing={missing}, extra={extra}."
        )


def _source_artifacts(
    source: Mapping[str, Any],
    *,
    repo_root: Path,
    names: Sequence[str],
) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name in names:
        descriptor = source.get(name)
        if not isinstance(descriptor, Mapping):
            raise TypeError(f"Source config omits descriptor {name!r}.")
        paths[name] = verified_artifact_path(
            descriptor,
            repo_root=repo_root,
            label=f"calibrator sensitivity {name}",
        )
    return paths


def _load_pickle(path: Path, *, expected_type: type[Any], label: str) -> Any:
    with path.open("rb") as handle:
        value = pickle.load(handle)
    if not isinstance(value, expected_type):
        raise TypeError(f"{label} has unexpected type {type(value)!r}.")
    return value


def _available_2011_labels(
    *,
    raw_path: Path,
    calibration_scores: pd.DataFrame,
    base_config: Mapping[str, Any],
) -> pd.DataFrame:
    """Materialize only the declared 2011 labels needed to fit calibration maps."""
    source = base_config["source"]
    design = base_config["design"]
    required = ("id", "issue_d", "term", "loan_status", "last_pymnt_d")
    expected_ids = frozenset(calibration_scores["id"].astype(str))
    chunks: list[pd.DataFrame] = []
    reader = pd.read_csv(
        raw_path,
        usecols=list(required),
        dtype={"id": "string", "loan_status": "string", "term": "string"},
        chunksize=int(source["csv_chunksize"]),
        low_memory=False,
    )
    start = pd.Timestamp(str(design["probability_calibration_start"]))
    end = pd.Timestamp(str(design["probability_calibration_end"]))
    for chunk in reader:
        issue_d = parse_issue_dates(chunk["issue_d"])
        term = parse_term_months(chunk["term"])
        keep = issue_d.between(start, end) & term.eq(int(design["term_months"])).fillna(False)
        keep &= chunk["id"].astype("string").astype(str).isin(expected_ids)
        if not bool(keep.any()):
            continue
        retained = chunk.loc[keep, ["id", "loan_status", "last_pymnt_d"]].copy()
        retained["id"] = retained["id"].astype("string").str.strip()
        chunks.append(retained)
    if not chunks:
        raise RuntimeError("The narrow 2011 raw scan found no probability-calibration rows.")
    frame = pd.concat(chunks, ignore_index=True)
    if bool(frame["id"].isna().any() or frame["id"].duplicated().any()):
        raise RuntimeError("The narrow 2011 label census has missing or duplicate IDs.")
    observed_ids = frozenset(frame["id"].astype(str))
    if observed_ids != expected_ids:
        raise RuntimeError("The narrow 2011 raw label census does not match the frozen score IDs.")
    availability = build_outcome_label_availability(
        frame["loan_status"],
        frame["last_pymnt_d"],
        cutoff=str(source["information_cutoff"]),
        charged_off_lag_months=int(source["charged_off_reporting_lag_months"]),
    )
    frame["terminal_default"] = terminal_outcome_from_status(frame["loan_status"])
    frame["label_available"] = availability["label_available"].astype(bool)
    available = frame.loc[
        frame["label_available"] & frame["terminal_default"].notna(),
        ["id", "terminal_default"],
    ].copy()
    available["terminal_default"] = available["terminal_default"].astype("int8")
    return available


def _reconcile_active_platt_fit(
    *,
    calibration: pd.DataFrame,
    source_freeze: Mapping[str, Any],
    expected_ordered_id_sha256: str,
    expected_ordered_label_sha256: str,
    expected_platt_probability_sha256: str,
    expected_y0: int,
    expected_y1: int,
    tolerance: float,
) -> dict[str, Any]:
    """Prove the reconstructed 2011 panel replays the active Platt fit audit."""
    required_columns = ["id", "pd_catboost_platt", "terminal_default"]
    if list(calibration.columns) != required_columns:
        raise RuntimeError("The reconstructed Platt-fit panel changed its exact column contract.")
    labels = calibration["terminal_default"].to_numpy(dtype=int)
    probabilities = calibration["pd_catboost_platt"].to_numpy(dtype=float)
    observed_metrics = binary_probability_metrics(labels, probabilities)
    try:
        expected_metrics = cast(Mapping[str, Any], source_freeze["learner_metrics"])[
            "catboost_platt"
        ]["probability_calibration"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError("The active V4 freeze omits the Platt calibration-fit audit.") from exc
    metric_names = ("rows", "default_rate", "roc_auc", "brier", "log_loss", "ece_10")
    if set(observed_metrics) != set(metric_names) or set(expected_metrics) != set(metric_names):
        raise RuntimeError("The active Platt calibration-fit metric schema changed.")
    if int(observed_metrics["rows"]) != int(expected_metrics["rows"]):
        raise RuntimeError("The active Platt calibration-fit row count changed.")
    differences = {
        name: abs(float(observed_metrics[name]) - float(expected_metrics[name]))
        for name in metric_names
        if name != "rows"
    }
    maximum = max(differences.values(), default=0.0)
    if not np.isfinite(maximum) or maximum > float(tolerance):
        raise RuntimeError(
            "The reconstructed 2011 panel does not replay the active Platt fit metrics: "
            f"max_abs_difference={maximum:.3e}."
        )
    ordered_id_sha256 = string_array_sha256(calibration["id"].astype(str))
    ordered_label_sha256 = float_array_sha256(labels.astype(float))
    platt_probability_sha256 = float_array_sha256(probabilities)
    if ordered_id_sha256 != expected_ordered_id_sha256:
        raise RuntimeError("The ordered 2011 Platt-fit ID hash changed.")
    if ordered_label_sha256 != expected_ordered_label_sha256:
        raise RuntimeError("The ordered 2011 Platt-fit label hash changed.")
    if platt_probability_sha256 != expected_platt_probability_sha256:
        raise RuntimeError("The ordered 2011 Platt-fit probability hash changed.")
    y0 = int(np.sum(labels == 0))
    y1 = int(np.sum(labels == 1))
    if (y0, y1) != (int(expected_y0), int(expected_y1)):
        raise RuntimeError("The ordered 2011 Platt-fit binary class census changed.")
    return {
        "ordered_id_contract": STRING_HASH_CONTRACT,
        "ordered_id_sha256": ordered_id_sha256,
        "ordered_label_contract": VECTOR_HASH_CONTRACT,
        "ordered_label_sha256": ordered_label_sha256,
        "platt_probability_contract": VECTOR_HASH_CONTRACT,
        "platt_probability_sha256": platt_probability_sha256,
        "y0": y0,
        "y1": y1,
        "metrics": dict(observed_metrics),
        "metric_tolerance": float(tolerance),
        "metric_max_abs_difference": maximum,
    }


def _common_edges_from_active_recipes(
    active_recipes: Mapping[str, Mapping[str, Mapping[int, Any]]],
    *,
    platt: LogisticRegression,
    window_ids: Sequence[str],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    platt_edges: tuple[float, ...] | None = None
    for window_id in window_ids:
        recipe = active_recipes["catboost_platt"][str(window_id)][CANONICAL_GROUPS]
        candidate = tuple(float(value) for value in recipe.bin_edges)
        if platt_edges is None:
            platt_edges = candidate
        elif candidate != platt_edges:
            raise RuntimeError("The active five-stratum Platt taxonomy changed across windows.")
    if platt_edges is None:
        raise RuntimeError("No active canonical Platt taxonomy was found.")
    return platt_edges, transform_platt_edges_to_q_raw(platt_edges, platt)


def _window_fit_frames(
    fit_audit: pd.DataFrame,
    *,
    family: CalibratorFamily,
    window_ids: Sequence[str],
) -> dict[str, tuple[pd.DataFrame, dict[str, np.ndarray], np.ndarray]]:
    canonical = fit_audit.loc[
        fit_audit["learner"].astype(str).eq("catboost_platt")
        & fit_audit["taxonomy_groups"].eq(CANONICAL_GROUPS)
        & fit_audit["window_id"].astype(str).isin(tuple(window_ids))
    ].copy()
    output: dict[str, tuple[pd.DataFrame, dict[str, np.ndarray], np.ndarray]] = {}
    for window_id in window_ids:
        frame = canonical.loc[canonical["window_id"].astype(str).eq(str(window_id))].copy()
        if frame.empty or bool(frame["id"].duplicated().any()):
            raise RuntimeError(f"Active fit audit is empty or duplicated for {window_id}.")
        margin, q_raw = recover_catboost_base_probability(
            frame["pd_point"].to_numpy(dtype=float),
            family.platt,
        )
        probabilities, venn_multiprobability_pair = apply_calibrator_family(
            family,
            q_raw=q_raw,
            margin=margin,
            frozen_platt_probability=frame["pd_point"].to_numpy(dtype=float),
        )
        output[str(window_id)] = (frame, probabilities, venn_multiprobability_pair)
    return output


def _fit_recipes(
    *,
    fit_frames: Mapping[str, tuple[pd.DataFrame, dict[str, np.ndarray], np.ndarray]],
    active_recipes: Mapping[str, Mapping[str, Mapping[int, Any]]],
    platt: LogisticRegression,
    common_edges: tuple[float, ...],
    alpha: float,
    minimum_rows: int,
) -> tuple[
    dict[str, dict[str, CalibratorResidualRecipe]],
    pd.DataFrame,
]:
    recipes: dict[str, dict[str, CalibratorResidualRecipe]] = {
        method: {} for method in CALIBRATOR_METHODS
    }
    audit_rows: list[dict[str, Any]] = []
    for window_id, (frame, probabilities, _) in fit_frames.items():
        _, q_raw = recover_catboost_base_probability(
            frame["pd_point"].to_numpy(dtype=float),
            platt,
        )
        labels = frame["terminal_default"].to_numpy(dtype=int)
        stored_groups = frame["conformal_group"].to_numpy(dtype=int)
        common_groups = assign_common_groups(q_raw, common_edges)
        if not np.array_equal(common_groups, stored_groups):
            changed = int(np.sum(common_groups != stored_groups))
            raise RuntimeError(
                f"Common q_raw taxonomy changed {changed} active assignments in {window_id}."
            )
        for method in CALIBRATOR_METHODS:
            recipe = fit_common_taxonomy_recipe(
                method=method,
                window_id=window_id,
                q_raw=q_raw,
                calibrated_probability=probabilities[method],
                labels=labels,
                alpha=alpha,
                taxonomy_edges_q_raw=common_edges,
                taxonomy_provenance=(
                    "active_2011_platt_edges_exactly_transformed_through_frozen_platt_inverse"
                ),
            )
            if min(recipe.group_counts) < minimum_rows:
                raise RuntimeError(f"{method}/{window_id} violates the locked minimum group size.")
            recipes[method][window_id] = recipe
            active = active_recipes["catboost_platt"][window_id][CANONICAL_GROUPS]
            for group in range(CANONICAL_GROUPS):
                residual_difference = (
                    float(recipe.residual_quantiles[group])
                    - float(active.residual_quantiles[group])
                    if method == "platt"
                    else np.nan
                )
                if method == "platt":
                    exact_integer_fields = (
                        recipe.group_counts[group] == int(active.group_counts[group])
                        and recipe.finite_sample_ranks[group]
                        == int(active.finite_sample_ranks[group])
                        and recipe.raw_finite_sample_ranks[group]
                        == int(active.raw_finite_sample_ranks[group])
                    )
                    if not exact_integer_fields or abs(residual_difference) > 1.0e-12:
                        raise RuntimeError(
                            f"Common-taxonomy Platt recipe failed V4 replay in "
                            f"{window_id}/group{group}."
                        )
                audit_rows.append(
                    {
                        "method": method,
                        "window_id": window_id,
                        "conformal_group": group,
                        "fit_rows": int(recipe.group_counts[group]),
                        "finite_sample_rank": int(recipe.finite_sample_ranks[group]),
                        "raw_finite_sample_rank": int(recipe.raw_finite_sample_ranks[group]),
                        "residual_quantile": float(recipe.residual_quantiles[group]),
                        "platt_active_residual_quantile_difference": residual_difference,
                        "common_membership": True,
                    }
                )
    return recipes, pd.DataFrame(audit_rows)


def _outcome_free_geometry(
    *,
    scores: pd.DataFrame,
    q_raw: np.ndarray,
    probabilities: Mapping[str, np.ndarray],
    venn_multiprobability_pair: np.ndarray,
    recipes: Mapping[str, Mapping[str, CalibratorResidualRecipe]],
    roles: Sequence[str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    venn_gap = venn_multiprobability_pair[:, 1] - venn_multiprobability_pair[:, 0]
    for method in CALIBRATOR_METHODS:
        for window_id, recipe in recipes[method].items():
            groups, lower, upper = apply_common_taxonomy_recipe(
                q_raw=q_raw,
                calibrated_probability=probabilities[method],
                recipe=recipe,
            )
            for role in roles:
                role_mask = scores["design_split"].astype(str).eq(str(role)).to_numpy(dtype=bool)
                for group in (-1, *range(CANONICAL_GROUPS)):
                    mask = role_mask & ((groups == group) if group >= 0 else True)
                    if not bool(mask.any()):
                        raise RuntimeError(
                            f"Empty outcome-free geometry cell {method}/{window_id}/{role}/{group}."
                        )
                    rows.append(
                        {
                            "method": method,
                            "window_id": window_id,
                            "taxonomy_groups": CANONICAL_GROUPS,
                            "role": str(role),
                            "conformal_group": int(group),
                            "score_min": float(np.min(probabilities[method][mask])),
                            "score_max": float(np.max(probabilities[method][mask])),
                            "q_raw_min": float(np.min(q_raw[mask])),
                            "q_raw_max": float(np.max(q_raw[mask])),
                            "venn_multiprobability_gap_mean": (
                                float(np.mean(venn_gap[mask])) if method == "venn_abers" else np.nan
                            ),
                            "venn_multiprobability_gap_q50": (
                                float(np.quantile(venn_gap[mask], 0.50))
                                if method == "venn_abers"
                                else np.nan
                            ),
                            **geometry_summary(lower[mask], upper[mask]),
                        }
                    )
    return pd.DataFrame(rows)


def _implementation(
    config_path: Path,
    root: Path,
    *,
    evaluation: bool = False,
) -> dict[str, Any]:
    phase_specific = (
        [Path("docs/research/ijds_calibrator_sensitivity_v1_evaluation_lock_2026-07-30.md")]
        if evaluation
        else []
    )
    return implementation_provenance(
        config_path=config_path,
        repo_root=root,
        relative_paths=[
            Path("scripts/experiments/run_ijds_calibrator_sensitivity_v1.py"),
            Path("src/ijds_audit/calibrator_sensitivity.py"),
            Path("src/ijds_audit/calibrator_sensitivity_protocol.py"),
            Path("src/ijds_audit/geometry.py"),
            Path("src/ijds_audit/protocol.py"),
            Path("src/data/outcome_observability.py"),
            Path("src/evaluation/coverage_transport.py"),
            Path("src/models/binary_conformal_guardrail.py"),
            Path("docs/research/ijds_calibrator_sensitivity_v1_protocol_2026-07-30.md"),
            *phase_specific,
        ],
    )


def freeze_calibrator_sensitivity(*, config_path: Path, repo_root: Path) -> Path:
    """Fit/freeze all maps without retaining or using primary-OOT outcomes."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_calibrator_sensitivity_config(resolved_config)
    if (
        config["phase"] != "phase_a_target_outcome_nonuse_freeze"
        or config["run_tag"] != FREEZE_RUN_TAG
        or config["protocol_tag"] != FREEZE_PROTOCOL_TAG
    ):
        raise RuntimeError("Phase-A calibrator-sensitivity identity changed.")
    design = _validate_locked_design(config)
    protocol_commit = _require_annotated_clean_head(root, FREEZE_PROTOCOL_TAG)
    source = cast(Mapping[str, Any], config["source"])
    paths = _source_artifacts(
        source,
        repo_root=root,
        names=(
            "active_v4_config",
            "active_v4_freeze",
            "scores",
            "residual_recipes",
            "fit_audit",
            "catboost_model",
            "platt_calibrator",
            "raw_archive",
        ),
    )
    source_freeze = json.loads(paths["active_v4_freeze"].read_text(encoding="utf-8"))
    if source_freeze.get("status") != "outcome_free_allocations_frozen_before_archive_outcome_join":
        raise RuntimeError("Active V4 source freeze has an unexpected status.")
    frozen_artifacts = cast(Mapping[str, Any], source_freeze["outcome_free_artifacts"])
    frozen_models = cast(Mapping[str, Any], source_freeze["model_artifacts"])
    for name, internal_name in (
        ("scores", "scores"),
        ("residual_recipes", "recipes"),
        ("fit_audit", "fit_audit"),
    ):
        _descriptor_equal(
            cast(Mapping[str, Any], frozen_artifacts[internal_name]),
            cast(Mapping[str, Any], source[name]),
            label=f"V4 source {name}",
        )
    for name, internal_name in (
        ("catboost_model", "catboost"),
        ("platt_calibrator", "catboost_platt"),
    ):
        _descriptor_equal(
            cast(Mapping[str, Any], frozen_models[internal_name]),
            cast(Mapping[str, Any], source[name]),
            label=f"V4 source {name}",
        )

    base_config = load_v4_config(paths["active_v4_config"])
    configured_raw = (root / str(base_config["source"]["raw_path"])).resolve()
    if configured_raw != paths["raw_archive"]:
        raise RuntimeError("The active V4 config no longer resolves to the locked raw archive.")
    scores = pd.read_parquet(paths["scores"])
    required_score_columns = {"id", "issue_d", "design_split", "pd_catboost_platt"}
    if not required_score_columns.issubset(scores.columns):
        raise KeyError("Active score artifact omits the primary CatBoost columns.")
    if bool(scores["id"].isna().any() or scores["id"].duplicated().any()):
        raise RuntimeError("Active score artifact has missing or duplicate IDs.")
    expected = design["expected_score_rows"]
    if len(scores) != int(expected):
        raise RuntimeError(f"Active score row census changed: {len(scores)} != {expected}.")

    frozen_platt = cast(
        LogisticRegression,
        _load_pickle(
            paths["platt_calibrator"],
            expected_type=LogisticRegression,
            label="frozen Platt calibrator",
        ),
    )
    frozen_probability = scores["pd_catboost_platt"].to_numpy(dtype=float)
    margin, q_raw = recover_catboost_base_probability(frozen_probability, frozen_platt)
    replay = np.asarray(frozen_platt.predict_proba(margin.reshape(-1, 1))[:, 1], dtype=float)
    replay_maximum = float(np.max(np.abs(replay - frozen_probability)))
    if replay_maximum > 5.0e-14:
        raise RuntimeError("Frozen Platt inversion/replay exceeds the locked tolerance.")

    active_recipes = load_recipes(paths["residual_recipes"])
    window_ids = tuple(str(value) for value in design["window_ids"])
    platt_edges, common_edges = _common_edges_from_active_recipes(
        active_recipes,
        platt=frozen_platt,
        window_ids=window_ids,
    )
    active_groups = assign_conformal_groups(frozen_probability, platt_edges)
    common_groups = assign_common_groups(q_raw, common_edges)
    if not np.array_equal(active_groups, common_groups):
        raise RuntimeError("Transformed q_raw taxonomy changed full-panel active membership.")

    calibration_scores = scores.loc[
        scores["design_split"].astype(str).eq("probability_calibration"),
        ["id", "pd_catboost_platt"],
    ].copy()
    if len(calibration_scores) != int(design["expected_calibration_score_rows"]):
        raise RuntimeError("The complete 2011 calibration-score row census changed.")
    labels = _available_2011_labels(
        raw_path=paths["raw_archive"],
        calibration_scores=calibration_scores,
        base_config=base_config,
    )
    calibration = calibration_scores.merge(labels, on="id", how="inner", validate="one_to_one")
    if list(calibration.columns) != [
        "id",
        "pd_catboost_platt",
        "terminal_default",
    ]:
        raise RuntimeError("Calibrator-fit input contains undeclared columns.")
    if not bool(calibration["id"].astype(str).isin(calibration_scores["id"].astype(str)).all()):
        raise RuntimeError("Calibrator-fit input contains an ID outside the frozen 2011 block.")
    if len(calibration) != int(design["expected_calibrator_fit_rows"]):
        raise RuntimeError("The available 2011 calibrator-fit row census changed.")
    platt_fit_reconciliation = _reconcile_active_platt_fit(
        calibration=calibration,
        source_freeze=source_freeze,
        expected_ordered_id_sha256=str(design["expected_calibrator_fit_ordered_id_sha256"]),
        expected_ordered_label_sha256=str(design["expected_calibrator_fit_ordered_label_sha256"]),
        expected_platt_probability_sha256=str(
            design["expected_calibrator_fit_platt_probability_sha256"]
        ),
        expected_y0=int(design["expected_calibrator_fit_y0"]),
        expected_y1=int(design["expected_calibrator_fit_y1"]),
        tolerance=float(design["platt_fit_reconciliation_tolerance"]),
    )
    calibration_margin, calibration_q = recover_catboost_base_probability(
        calibration["pd_catboost_platt"].to_numpy(dtype=float),
        frozen_platt,
    )
    family = fit_calibrator_family(
        q_raw=calibration_q,
        labels=calibration["terminal_default"].to_numpy(dtype=int),
        frozen_platt=frozen_platt,
        venn_abers_precision=None,
    )
    all_probabilities, all_venn_multiprobability_pair = apply_calibrator_family(
        family,
        q_raw=q_raw,
        margin=margin,
        frozen_platt_probability=frozen_probability,
    )
    monotonicity = monotonicity_audit(q_raw, all_probabilities)
    calibration_probabilities, calibration_venn_multiprobability_pair = apply_calibrator_family(
        family,
        q_raw=calibration_q,
        margin=calibration_margin,
        frozen_platt_probability=calibration["pd_catboost_platt"].to_numpy(dtype=float),
    )
    diagnostics = calibration_fit_diagnostics(
        calibration["terminal_default"].to_numpy(dtype=int),
        calibration_probabilities,
        calibration_venn_multiprobability_pair,
    )

    fit_audit = pd.read_parquet(paths["fit_audit"])
    fit_frames = _window_fit_frames(fit_audit, family=family, window_ids=window_ids)
    recipes, recipe_audit = _fit_recipes(
        fit_frames=fit_frames,
        active_recipes=active_recipes,
        platt=family.platt,
        common_edges=common_edges,
        alpha=float(design["alpha"]),
        minimum_rows=int(design["minimum_rows_per_group"]),
    )
    expected_recipe_cells = len(CALIBRATOR_METHODS) * len(window_ids) * CANONICAL_GROUPS
    if len(recipe_audit) != expected_recipe_cells:
        raise RuntimeError("The complete four-by-eight-by-five recipe audit is incomplete.")
    geometry = _outcome_free_geometry(
        scores=scores,
        q_raw=q_raw,
        probabilities=all_probabilities,
        venn_multiprobability_pair=all_venn_multiprobability_pair,
        recipes=recipes,
        roles=tuple(str(value) for value in design["geometry_roles"]),
    )

    outputs = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    output = cast(Mapping[str, Any], config["output"])
    written = {
        "calibrator_family": atomic_write_pickle(
            outputs.model_dir / str(output["calibrator_family"]),
            family,
        ),
        "taxonomy": atomic_write_json(
            outputs.model_dir / str(output["taxonomy"]),
            {
                "taxonomy_groups": CANONICAL_GROUPS,
                "active_platt_edges": list(platt_edges),
                "common_q_raw_edges": list(common_edges),
                "method": "exact_inverse_transform_of_active_platt_edges",
                "full_panel_assignment_changes": 0,
            },
        ),
        "residual_recipes": atomic_write_json(
            outputs.model_dir / str(output["residual_recipes"]),
            recipe_payload(recipes),
        ),
        "calibration_fit_diagnostics": atomic_write_parquet(
            diagnostics,
            outputs.data_dir / str(output["calibration_fit_diagnostics"]),
        ),
        "recipe_audit": atomic_write_parquet(
            recipe_audit,
            outputs.data_dir / str(output["recipe_audit"]),
        ),
        "outcome_free_geometry": atomic_write_parquet(
            geometry,
            outputs.data_dir / str(output["outcome_free_geometry"]),
        ),
    }
    vector_hashes = {
        "contract": VECTOR_HASH_CONTRACT,
        "id_contract": STRING_HASH_CONTRACT,
        "id": string_array_sha256(scores["id"].astype(str)),
        "q_raw": float_array_sha256(q_raw),
        **{
            f"probability_{method}": float_array_sha256(all_probabilities[method])
            for method in CALIBRATOR_METHODS
        },
        "venn_abers_p0": float_array_sha256(all_venn_multiprobability_pair[:, 0]),
        "venn_abers_p1": float_array_sha256(all_venn_multiprobability_pair[:, 1]),
    }
    freeze = {
        "schema_version": str(config["schema_version"]),
        "status": FREEZE_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "source_artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root) for name, path in paths.items()
        },
        "design": {
            "methods": list(CALIBRATOR_METHODS),
            "window_ids": list(window_ids),
            "taxonomy_groups": CANONICAL_GROUPS,
            "alpha": float(design["alpha"]),
            "score_rows": int(len(scores)),
            "calibrator_fit_rows": int(len(calibration)),
            "recipe_cells": int(len(recipe_audit)),
            "geometry_cells": int(len(geometry)),
        },
        "gates": {
            "platt_roundtrip_max_abs_difference": replay_maximum,
            "platt_roundtrip_tolerance": 5.0e-14,
            "q_raw_expit_margin_max_abs_difference": float(np.max(np.abs(q_raw - expit(margin)))),
            "full_panel_common_taxonomy_assignment_changes": 0,
            "platt_v4_recipe_integer_fields_exact": True,
            "platt_v4_recipe_max_residual_quantile_difference": float(
                recipe_audit.loc[
                    recipe_audit["method"].eq("platt"),
                    "platt_active_residual_quantile_difference",
                ]
                .abs()
                .max()
            ),
            "platt_v4_recipe_float_tolerance": 1.0e-12,
            "minimum_adjacent_map_changes": monotonicity,
            "venn_abers_standard_p_prime_verified": True,
            "venn_abers_precision": None,
            "calibrator_state": calibrator_state_audit(family),
            "calibrator_fit_input_columns": list(calibration.columns),
            "calibrator_fit_input_design_split": "probability_calibration",
            "active_platt_fit_reconciliation": platt_fit_reconciliation,
        },
        "score_vector_hashes": vector_hashes,
        "outcome_free_artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in written.items()
        },
        "information_contract": {
            "retrospective_archive_previously_inspected": True,
            "raw_archive_physically_read_during_phase_a": True,
            "primary_oot_status_values_may_be_read_in_underlying_csv_chunks": True,
            "primary_oot_outcomes_retained_or_used": False,
            "primary_oot_outcomes_passed_to_calibrator_or_recipe": False,
            "only_2011_probability_calibration_rows_retained_for_calibrator_fit": True,
            "learner_calibrator_window_or_result_selected": False,
            "portfolio_optimization_run": False,
        },
        "git_transport": {
            "protocol_commit_role": "P",
            "required_phase_a_source_tag": FREEZE_SOURCE_TAG,
            "phase_a_source_commit_role": "A_single_direct_child_of_P",
            "required_phase_b_protocol_tag": EVALUATION_PROTOCOL_TAG,
            "phase_b_protocol_commit_role": "B_single_direct_child_of_A",
            "required_final_artifact_tag": FINAL_ARTIFACT_TAG,
            "final_output_commit_role": "C_single_direct_child_of_B",
            "annotated_tags_required": True,
        },
        "implementation_provenance": _implementation(resolved_config, root),
        "environment": environment_provenance(root),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    freeze_path = atomic_write_json(
        outputs.model_dir / str(output["freeze"]),
        freeze,
    )
    atomic_write_json(
        outputs.model_dir / str(output["execution_receipt"]),
        {
            "schema_version": str(config["schema_version"]),
            "status": "complete_calibrator_sensitivity_phase_a_execution_receipt",
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "freeze": relative_artifact_descriptor(freeze_path, repo_root=root),
            "environment": environment_provenance(root),
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    return freeze_path


def require_locked_evaluation_source(config: Mapping[str, Any]) -> None:
    """Reject the Phase-B template until exact Phase-A identities are inserted."""
    if (
        config["phase"] != "phase_b_hash_bound_endpoint_evaluation"
        or config["run_tag"] != EVALUATION_RUN_TAG
        or config["protocol_tag"] != EVALUATION_PROTOCOL_TAG
    ):
        raise RuntimeError("Phase-B calibrator-sensitivity identity changed.")
    interpretation = cast(Mapping[str, Any], config["interpretation"])
    if (
        interpretation.get("if_any_upper_at_or_above_nominal")
        != "uniform_closed_family_shortfall_not_established"
    ):
        raise RuntimeError("The locked nonuniform-result interpretation changed.")
    source = cast(Mapping[str, Any], config["source"])
    required = (
        "phase_a_freeze",
        "phase_a_receipt",
        "phase_a_source_commit",
        "phase_a_source_tag",
    )
    for field in required:
        value = source.get(field)
        if value in (None, -1) or PENDING_TOKEN in str(value):
            raise RuntimeError("Phase-B source identities are still pending after Phase A.")
    for name in ("phase_a_freeze", "phase_a_receipt"):
        descriptor = cast(Mapping[str, Any], source[name])
        if (
            descriptor.get("bytes") in (None, -1)
            or not isinstance(descriptor.get("sha256"), str)
            or PENDING_TOKEN in str(descriptor.get("sha256"))
        ):
            raise RuntimeError(f"Phase-B descriptor {name!r} is still pending.")


def _verify_phase_a_transport(
    *,
    config: Mapping[str, Any],
    root: Path,
    protocol_commit: str,
) -> tuple[Path, Path, dict[str, Any]]:
    source = cast(Mapping[str, Any], config["source"])
    freeze_path = verified_artifact_path(
        cast(Mapping[str, Any], source["phase_a_freeze"]),
        repo_root=root,
        label="locked Phase-A freeze",
    )
    receipt_path = verified_artifact_path(
        cast(Mapping[str, Any], source["phase_a_receipt"]),
        repo_root=root,
        label="locked Phase-A receipt",
    )
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected_freeze = {
        "status": FREEZE_STATUS,
        "run_tag": FREEZE_RUN_TAG,
        "protocol_tag": FREEZE_PROTOCOL_TAG,
    }
    for field, expected in expected_freeze.items():
        if freeze.get(field) != expected:
            raise RuntimeError(f"Locked Phase-A freeze changed {field}.")
    expected_receipt = {
        "status": "complete_calibrator_sensitivity_phase_a_execution_receipt",
        "run_tag": FREEZE_RUN_TAG,
        "protocol_tag": FREEZE_PROTOCOL_TAG,
        "protocol_commit": freeze.get("protocol_commit"),
    }
    for field, expected in expected_receipt.items():
        if receipt.get(field) != expected:
            raise RuntimeError(f"Locked Phase-A receipt changed {field}.")
    _descriptor_equal(
        cast(Mapping[str, Any], receipt["freeze"]),
        cast(Mapping[str, Any], source["phase_a_freeze"]),
        label="Phase-A receipt versus freeze",
    )
    source_tag = str(source["phase_a_source_tag"])
    source_commit = str(source["phase_a_source_commit"])
    if source_tag != FREEZE_SOURCE_TAG:
        raise RuntimeError("Phase-B source tag identity changed.")
    resolved_protocol_p = _annotated_tag_commit(root, FREEZE_PROTOCOL_TAG)
    if (
        freeze.get("protocol_commit") != resolved_protocol_p
        or receipt.get("protocol_commit") != resolved_protocol_p
    ):
        raise RuntimeError("Phase-A freeze/receipt parent is not annotated protocol P.")
    if _annotated_tag_commit(root, source_tag) != source_commit:
        raise RuntimeError("Phase-A source tag does not resolve to the locked source commit.")
    _require_direct_child(
        root,
        child=source_commit,
        parent=str(freeze["protocol_commit"]),
    )
    _require_direct_child(
        root,
        child=protocol_commit,
        parent=source_commit,
    )
    _require_exact_commit_paths(
        root,
        commit=source_commit,
        expected_paths=PHASE_A_COMMIT_PATHS,
        label="Phase-A source commit A",
    )
    _require_exact_commit_paths(
        root,
        commit=protocol_commit,
        expected_paths=PHASE_B_COMMIT_PATHS,
        label="Phase-B protocol commit B",
    )
    design = cast(Mapping[str, Any], config["design"])
    gates = freeze.get("gates")
    if not isinstance(gates, Mapping):
        raise TypeError("Phase-A freeze omits its validation gates.")
    fit_reconciliation = gates.get("active_platt_fit_reconciliation")
    if not isinstance(fit_reconciliation, Mapping):
        raise TypeError("Phase-A freeze omits the active Platt-fit reconciliation.")
    expected_fit_fields = {
        "ordered_id_contract": STRING_HASH_CONTRACT,
        "ordered_id_sha256": str(design["expected_calibrator_fit_ordered_id_sha256"]),
        "ordered_label_contract": VECTOR_HASH_CONTRACT,
        "ordered_label_sha256": str(design["expected_calibrator_fit_ordered_label_sha256"]),
        "platt_probability_contract": VECTOR_HASH_CONTRACT,
        "platt_probability_sha256": str(design["expected_calibrator_fit_platt_probability_sha256"]),
        "y0": int(design["expected_calibrator_fit_y0"]),
        "y1": int(design["expected_calibrator_fit_y1"]),
        "metric_tolerance": float(design["platt_fit_reconciliation_tolerance"]),
        "metric_max_abs_difference": 0.0,
    }
    for field, expected_field_value in expected_fit_fields.items():
        if fit_reconciliation.get(field) != expected_field_value:
            raise RuntimeError(f"Phase-A Platt-fit reconciliation changed {field}.")
    source_artifacts = freeze.get("source_artifacts")
    if not isinstance(source_artifacts, Mapping):
        raise TypeError("Phase-A freeze omits its source descriptors.")
    active_v4_freeze_path = verified_artifact_path(
        cast(Mapping[str, Any], source_artifacts["active_v4_freeze"]),
        repo_root=root,
        label="Phase-A active V4 source freeze",
    )
    active_v4_freeze = json.loads(active_v4_freeze_path.read_text(encoding="utf-8"))
    expected_metrics = cast(Mapping[str, Any], active_v4_freeze["learner_metrics"])[
        "catboost_platt"
    ]["probability_calibration"]
    if fit_reconciliation.get("metrics") != expected_metrics:
        raise RuntimeError("Phase-A Platt-fit metrics no longer equal the active V4 freeze.")
    return freeze_path, receipt_path, freeze


def _verified_freeze_artifacts(
    freeze: Mapping[str, Any],
    *,
    root: Path,
) -> dict[str, Path]:
    artifacts = freeze.get("outcome_free_artifacts")
    if not isinstance(artifacts, Mapping):
        raise TypeError("Phase-A freeze omits outcome-free artifacts.")
    expected_names = {
        "calibrator_family",
        "taxonomy",
        "residual_recipes",
        "calibration_fit_diagnostics",
        "recipe_audit",
        "outcome_free_geometry",
    }
    if {str(name) for name in artifacts} != expected_names:
        raise RuntimeError("Phase-A freeze artifact set is incomplete or contains extras.")
    return {
        str(name): verified_artifact_path(
            cast(Mapping[str, Any], descriptor),
            repo_root=root,
            label=f"Phase-A artifact {name}",
        )
        for name, descriptor in artifacts.items()
    }


def _verify_vector_replay(
    *,
    freeze: Mapping[str, Any],
    scores: pd.DataFrame,
    probabilities: Mapping[str, np.ndarray],
    q_raw: np.ndarray,
    venn_multiprobability_pair: np.ndarray,
) -> None:
    expected = cast(Mapping[str, Any], freeze["score_vector_hashes"])
    observed = {
        "contract": VECTOR_HASH_CONTRACT,
        "id_contract": STRING_HASH_CONTRACT,
        "id": string_array_sha256(scores["id"].astype(str)),
        "q_raw": float_array_sha256(q_raw),
        **{
            f"probability_{method}": float_array_sha256(probabilities[method])
            for method in CALIBRATOR_METHODS
        },
        "venn_abers_p0": float_array_sha256(venn_multiprobability_pair[:, 0]),
        "venn_abers_p1": float_array_sha256(venn_multiprobability_pair[:, 1]),
    }
    if dict(expected) != observed:
        changed = sorted(key for key, value in observed.items() if expected.get(key) != value)
        raise RuntimeError(f"Phase-B score-vector replay changed hashes: {changed}.")


def _fit_statistics(
    frame: pd.DataFrame,
    probability: np.ndarray,
    recipe: CalibratorResidualRecipe,
    *,
    group: int,
    platt: LogisticRegression,
) -> dict[str, float | int]:
    _, q_raw = recover_catboost_base_probability(
        frame["pd_point"].to_numpy(dtype=float),
        platt,
    )
    assigned = assign_common_groups(q_raw, recipe.taxonomy_edges_q_raw)
    mask = assigned == group if group >= 0 else np.ones(len(frame), dtype=bool)
    if not bool(mask.any()):
        raise RuntimeError("A requested fit-statistics scope is empty.")
    selected_probability = probability[mask]
    selected_labels = frame["terminal_default"].to_numpy(dtype=float)[mask]
    if group >= 0:
        threshold = float(recipe.residual_quantiles[group])
    else:
        residual = np.sort(np.abs(selected_labels - selected_probability))
        raw_rank = int(np.ceil((len(residual) + 1) * (1.0 - recipe.alpha)))
        threshold = 1.0 if raw_rank > len(residual) else float(residual[raw_rank - 1])
    return {
        "fit_rows": int(mask.sum()),
        "fit_prevalence": float(np.mean(selected_labels)),
        "fit_residual_quantile": threshold,
        "fit_score_min": float(np.min(selected_probability)),
        "fit_score_max": float(np.max(selected_probability)),
    }


def _evaluate_grid(
    *,
    target: pd.DataFrame,
    q_raw: np.ndarray,
    probabilities: Mapping[str, np.ndarray],
    venn_multiprobability_pair: np.ndarray,
    recipes: Mapping[str, Mapping[str, CalibratorResidualRecipe]],
    fit_frames: Mapping[str, tuple[pd.DataFrame, dict[str, np.ndarray], np.ndarray]],
    nominal_coverage: float,
    platt: LogisticRegression,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    y = pd.to_numeric(target["snapshot_default"], errors="coerce").to_numpy(dtype=float)
    venn_gap = venn_multiprobability_pair[:, 1] - venn_multiprobability_pair[:, 0]
    rows: list[dict[str, Any]] = []
    endpoints: dict[tuple[str, str], tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for method in CALIBRATOR_METHODS:
        for window_id, recipe in recipes[method].items():
            groups, lower, upper = apply_common_taxonomy_recipe(
                q_raw=q_raw,
                calibrated_probability=probabilities[method],
                recipe=recipe,
            )
            endpoints[(method, window_id)] = (groups, lower, upper)
            fit_frame, fit_probabilities, _ = fit_frames[window_id]
            for group in (-1, *range(CANONICAL_GROUPS)):
                mask = groups == group if group >= 0 else np.ones(len(groups), dtype=bool)
                fit = _fit_statistics(
                    fit_frame,
                    fit_probabilities[method],
                    recipe,
                    group=group,
                    platt=platt,
                )
                cell = coverage_cell(
                    outcomes=y[mask],
                    lower=lower[mask],
                    upper=upper[mask],
                )
                rows.append(
                    {
                        "method": method,
                        "window_id": window_id,
                        "taxonomy_groups": CANONICAL_GROUPS,
                        "role": "primary_oot",
                        "conformal_group": int(group),
                        **cell,
                        "score_min": float(np.min(probabilities[method][mask])),
                        "score_max": float(np.max(probabilities[method][mask])),
                        **fit,
                        "scores_below_fit_range": int(
                            np.sum(
                                probabilities[method][mask] < float(fit["fit_score_min"]) - 1.0e-12
                            )
                        ),
                        "scores_above_fit_range": int(
                            np.sum(
                                probabilities[method][mask] > float(fit["fit_score_max"]) + 1.0e-12
                            )
                        ),
                        "venn_multiprobability_gap_mean": (
                            float(np.mean(venn_gap[mask])) if method == "venn_abers" else np.nan
                        ),
                        "venn_multiprobability_gap_q50": (
                            float(np.quantile(venn_gap[mask], 0.50))
                            if method == "venn_abers"
                            else np.nan
                        ),
                        "coverage_upper_below_nominal": bool(
                            float(cell["coverage_upper"]) < nominal_coverage
                        ),
                    }
                )
    evaluation = pd.DataFrame(rows)

    pair_rows: list[dict[str, Any]] = []
    window_ids = tuple(recipes[CALIBRATOR_METHODS[0]])
    for method_a, method_b in unordered_method_pairs():
        for window_id in window_ids:
            groups_a, lower_a, upper_a = endpoints[(method_a, window_id)]
            groups_b, lower_b, upper_b = endpoints[(method_b, window_id)]
            if not np.array_equal(groups_a, groups_b):
                raise RuntimeError("Pairwise comparison lost common taxonomy membership.")
            for group in (-1, *range(CANONICAL_GROUPS)):
                mask = groups_a == group if group >= 0 else np.ones(len(groups_a), dtype=bool)
                pair_rows.append(
                    {
                        "method_a": method_a,
                        "method_b": method_b,
                        "window_id": window_id,
                        "taxonomy_groups": CANONICAL_GROUPS,
                        "role": "primary_oot",
                        "conformal_group": int(group),
                        **shared_completion_coverage_difference(
                            outcomes=y[mask],
                            lower_a=lower_a[mask],
                            upper_a=upper_a[mask],
                            lower_b=lower_b[mask],
                            upper_b=upper_b[mask],
                        ),
                    }
                )
    return evaluation, pd.DataFrame(pair_rows)


def _baseline_reconciliation(
    evaluation: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    tolerance: float,
) -> tuple[pd.DataFrame, float]:
    current = evaluation.loc[evaluation["method"].eq("platt")].copy()
    baseline = reference.loc[
        reference["learner"].astype(str).eq("catboost_platt")
        & reference["taxonomy_groups"].eq(CANONICAL_GROUPS)
        & reference["role"].astype(str).eq("primary_oot")
    ].copy()
    key = ["window_id", "conformal_group"]
    current = current.sort_values(key, kind="mergesort").reset_index(drop=True)
    baseline = baseline.sort_values(key, kind="mergesort").reset_index(drop=True)
    if (
        len(current) != 8 * (CANONICAL_GROUPS + 1)
        or len(baseline) != len(current)
        or not current[key].equals(baseline[key])
    ):
        raise RuntimeError("Active Platt V5 reconciliation grid changed.")
    metrics = (
        "candidate_rows",
        "resolved_rows",
        "unresolved_rows",
        "coverage_resolved",
        "coverage_lower",
        "coverage_upper",
        "score_min",
        "score_max",
        "fit_rows",
        "fit_prevalence",
        "fit_residual_quantile",
        "fit_score_min",
        "fit_score_max",
        "scores_below_fit_range",
        "scores_above_fit_range",
        "rows",
        "mean_width",
        "lower_positive_share",
        "upper_saturated_share",
        "set_empty_count",
        "set_empty_share",
        "set_zero_only_count",
        "set_zero_only_share",
        "set_one_only_count",
        "set_one_only_share",
        "set_both_count",
        "set_both_share",
        "width_q00",
        "width_q10",
        "width_q25",
        "width_q50",
        "width_q75",
        "width_q90",
        "width_q100",
    )
    output = current[key].copy()
    maximum = 0.0
    for metric in metrics:
        difference = pd.to_numeric(current[metric], errors="raise").to_numpy(
            dtype=float
        ) - pd.to_numeric(baseline[metric], errors="raise").to_numpy(dtype=float)
        output[f"{metric}_difference"] = difference
        maximum = max(maximum, float(np.max(np.abs(difference))))
    if maximum > tolerance:
        raise RuntimeError(f"Active Platt V5 reconciliation exceeded tolerance: {maximum:.3e}.")
    return output, maximum


def _validate_evaluation_outputs(
    evaluation: pd.DataFrame,
    pairwise: pd.DataFrame,
) -> None:
    evaluation_key = ("method", "window_id", "role", "conformal_group")
    pairwise_key = (
        "method_a",
        "method_b",
        "window_id",
        "role",
        "conformal_group",
    )
    if bool(evaluation.duplicated(list(evaluation_key)).any()) or bool(
        pairwise.duplicated(list(pairwise_key)).any()
    ):
        raise RuntimeError("Calibrator evaluation outputs contain duplicate cells.")
    required_numeric = (
        "candidate_rows",
        "resolved_rows",
        "unresolved_rows",
        "coverage_resolved",
        "coverage_lower",
        "coverage_upper",
        "coverage_resolved_y0",
        "coverage_resolved_y1",
        "mean_width",
        "average_set_size",
        "singleton_share",
        "set_empty_share",
        "set_zero_only_share",
        "set_one_only_share",
        "set_both_share",
    )
    values = evaluation.loc[:, required_numeric].to_numpy(dtype=float)
    if not bool(np.isfinite(values).all()):
        raise RuntimeError("Calibrator evaluation contains a non-finite required metric.")
    venn_rows = evaluation["method"].eq("venn_abers")
    venn_gap_columns = [
        "venn_multiprobability_gap_mean",
        "venn_multiprobability_gap_q50",
    ]
    if not bool(
        np.isfinite(evaluation.loc[venn_rows, venn_gap_columns].to_numpy(dtype=float)).all()
    ) or bool(evaluation.loc[~venn_rows, venn_gap_columns].notna().any().any()):
        raise RuntimeError("Venn--Abers compact multiprobability-gap diagnostics are invalid.")
    if bool(
        (evaluation["coverage_lower"] > evaluation["coverage_upper"]).any()
        or (evaluation["coverage_lower"] < 0.0).any()
        or (evaluation["coverage_upper"] > 1.0).any()
        or (
            evaluation["resolved_rows"] + evaluation["unresolved_rows"]
            != evaluation["candidate_rows"]
        ).any()
    ):
        raise RuntimeError("Calibrator coverage bounds or row identities are invalid.")
    set_counts = (
        evaluation["set_empty_count"]
        + evaluation["set_zero_only_count"]
        + evaluation["set_one_only_count"]
        + evaluation["set_both_count"]
    )
    set_shares = (
        evaluation["set_empty_share"]
        + evaluation["set_zero_only_share"]
        + evaluation["set_one_only_share"]
        + evaluation["set_both_share"]
    )
    if bool((set_counts != evaluation["candidate_rows"]).any()) or bool(
        (set_shares - 1.0).abs().gt(1.0e-12).any()
    ):
        raise RuntimeError("Binary-set partition does not reconcile.")
    pair_metrics = pairwise[
        [
            "coverage_difference_resolved",
            "coverage_difference_lower",
            "coverage_difference_upper",
        ]
    ].to_numpy(dtype=float)
    if not bool(np.isfinite(pair_metrics).all()) or bool(
        (pairwise["coverage_difference_lower"] > pairwise["coverage_difference_upper"]).any()
    ):
        raise RuntimeError("Pairwise shared-completion bounds are invalid.")


def evaluate_calibrator_sensitivity(*, config_path: Path, repo_root: Path) -> Path:
    """Evaluate the complete frozen grid against the active V5 endpoint."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_calibrator_sensitivity_config(resolved_config)
    require_locked_evaluation_source(config)
    design = _validate_locked_design(config)
    protocol_commit = _require_annotated_clean_head(root, EVALUATION_PROTOCOL_TAG)
    freeze_path, receipt_path, freeze = _verify_phase_a_transport(
        config=config,
        root=root,
        protocol_commit=protocol_commit,
    )
    artifacts = _verified_freeze_artifacts(freeze, root=root)
    family = cast(
        CalibratorFamily,
        _load_pickle(
            artifacts["calibrator_family"],
            expected_type=CalibratorFamily,
            label="Phase-A calibrator family",
        ),
    )
    calibrator_state_audit(family)
    recipes_payload = json.loads(artifacts["residual_recipes"].read_text(encoding="utf-8"))
    recipes = load_recipe_payload(recipes_payload)

    source_artifacts = cast(Mapping[str, Any], freeze["source_artifacts"])
    scores_path = verified_artifact_path(
        cast(Mapping[str, Any], source_artifacts["scores"]),
        repo_root=root,
        label="Phase-A frozen active scores",
    )
    fit_audit_path = verified_artifact_path(
        cast(Mapping[str, Any], source_artifacts["fit_audit"]),
        repo_root=root,
        label="Phase-A frozen active fit audit",
    )
    scores = pd.read_parquet(scores_path)
    frozen_probability = scores["pd_catboost_platt"].to_numpy(dtype=float)
    margin, q_raw = recover_catboost_base_probability(frozen_probability, family.platt)
    probabilities, venn_multiprobability_pair = apply_calibrator_family(
        family,
        q_raw=q_raw,
        margin=margin,
        frozen_platt_probability=frozen_probability,
    )
    _verify_vector_replay(
        freeze=freeze,
        scores=scores,
        probabilities=probabilities,
        q_raw=q_raw,
        venn_multiprobability_pair=venn_multiprobability_pair,
    )

    source = cast(Mapping[str, Any], config["source"])
    phase_b_paths = _source_artifacts(
        source,
        repo_root=root,
        names=("active_v5_config", "active_v5_summary", "active_v5_temporal_coverage"),
    )
    active_summary = json.loads(phase_b_paths["active_v5_summary"].read_text(encoding="utf-8"))
    if active_summary.get("status") != "complete_retrospective_binary_geometry_frontier_audit":
        raise RuntimeError("Active V5 evaluation summary is incomplete.")
    active_artifacts = cast(Mapping[str, Any], active_summary["artifacts"])
    _descriptor_equal(
        cast(Mapping[str, Any], active_artifacts["temporal_coverage"]),
        cast(Mapping[str, Any], source["active_v5_temporal_coverage"]),
        label="active V5 temporal coverage",
    )
    active_config = load_v4_config(phase_b_paths["active_v5_config"])
    raw_path = (root / str(active_config["source"]["raw_path"])).resolve()
    raw_descriptor = relative_artifact_descriptor(raw_path, repo_root=root)
    if raw_descriptor["sha256"] != str(source["raw_archive_sha256"]):
        raise RuntimeError("Active endpoint raw archive hash changed.")
    universe = load_outcome_universe(active_config, raw_path=raw_path)
    outcomes = configured_archive_outcomes(universe, active_config)
    target_mask = scores["design_split"].astype(str).eq("primary_oot").to_numpy(dtype=bool)
    target_scores = scores.loc[target_mask].copy()
    primary_outcomes = outcomes.loc[
        outcomes["role"].astype(str).eq("primary_oot"),
        ["id", "snapshot_default"],
    ].copy()
    if (
        bool(primary_outcomes["id"].isna().any())
        or bool(primary_outcomes["id"].duplicated().any())
        or frozenset(primary_outcomes["id"].astype(str))
        != frozenset(target_scores["id"].astype(str))
    ):
        raise RuntimeError("Active endpoint IDs do not exactly match frozen primary-OOT IDs.")
    target = target_scores[["id", "issue_d", "design_split"]].merge(
        primary_outcomes,
        on="id",
        how="left",
        validate="one_to_one",
    )
    if not np.array_equal(
        target["id"].astype(str).to_numpy(),
        target_scores["id"].astype(str).to_numpy(),
    ):
        raise RuntimeError("Outcome merge changed the frozen primary-OOT row order.")
    expected = {
        "candidate_rows": int(design["expected_candidates"]),
        "resolved_rows": int(design["expected_resolved"]),
        "unresolved_rows": int(design["expected_unresolved"]),
        "resolved_y0": int(design["expected_resolved_y0"]),
        "resolved_y1": int(design["expected_resolved_y1"]),
    }
    y = pd.to_numeric(target["snapshot_default"], errors="coerce").to_numpy(dtype=float)
    observed = np.isfinite(y)
    actual = {
        "candidate_rows": int(len(target)),
        "resolved_rows": int(observed.sum()),
        "unresolved_rows": int((~observed).sum()),
        "resolved_y0": int(np.sum(observed & (y == 0.0))),
        "resolved_y1": int(np.sum(observed & (y == 1.0))),
    }
    if actual != expected:
        raise RuntimeError(f"Active endpoint census changed: {actual} != {expected}.")
    target_q_raw = q_raw[target_mask]
    target_probabilities = {
        method: probabilities[method][target_mask] for method in CALIBRATOR_METHODS
    }
    target_venn_multiprobability_pair = venn_multiprobability_pair[target_mask]
    fit_audit = pd.read_parquet(fit_audit_path)
    window_ids = tuple(str(value) for value in design["window_ids"])
    fit_frames = _window_fit_frames(fit_audit, family=family, window_ids=window_ids)
    evaluation, pairwise = _evaluate_grid(
        target=target,
        q_raw=target_q_raw,
        probabilities=target_probabilities,
        venn_multiprobability_pair=target_venn_multiprobability_pair,
        recipes=recipes,
        fit_frames=fit_frames,
        nominal_coverage=1.0 - float(design["alpha"]),
        platt=family.platt,
    )
    _validate_evaluation_outputs(evaluation, pairwise)
    expected_cells = len(CALIBRATOR_METHODS) * len(window_ids) * (CANONICAL_GROUPS + 1)
    expected_pairs = len(unordered_method_pairs()) * len(window_ids) * (CANONICAL_GROUPS + 1)
    expected_overall = len(CALIBRATOR_METHODS) * len(window_ids)
    if (
        int(design["expected_evaluation_cells"]) != expected_cells
        or int(design["expected_overall_cells"]) != expected_overall
        or int(design["expected_pairwise_cells"]) != expected_pairs
    ):
        raise RuntimeError("Configured complete-grid censuses changed.")
    if len(evaluation) != expected_cells or len(pairwise) != expected_pairs:
        raise RuntimeError("The complete calibrator sensitivity evaluation grid is incomplete.")
    overall = evaluation.loc[evaluation["conformal_group"].eq(-1)].copy()
    if len(overall) != expected_overall:
        raise RuntimeError("The 32-cell overall calibrator summary is incomplete.")
    temporal_reference = pd.read_parquet(phase_b_paths["active_v5_temporal_coverage"])
    tolerance = float(design["platt_v5_reconciliation_tolerance"])
    reconciliation, maximum_reconciliation = _baseline_reconciliation(
        evaluation,
        temporal_reference,
        tolerance=tolerance,
    )

    outputs = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    output = cast(Mapping[str, Any], config["output"])
    written = {
        "evaluation": atomic_write_parquet(
            evaluation,
            outputs.data_dir / str(output["evaluation"]),
        ),
        "overall_summary": atomic_write_parquet(
            overall,
            outputs.data_dir / str(output["overall_summary"]),
        ),
        "pairwise_shared_completion": atomic_write_parquet(
            pairwise,
            outputs.data_dir / str(output["pairwise_shared_completion"]),
        ),
        "platt_v5_reconciliation": atomic_write_parquet(
            reconciliation,
            outputs.data_dir / str(output["platt_v5_reconciliation"]),
        ),
    }
    below_nominal = int(overall["coverage_upper_below_nominal"].astype(bool).sum())
    all_overall_below_nominal = below_nominal == len(overall)
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_retrospective_calibrator_sensitivity_evaluation",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "source_artifacts": {
            "phase_a_freeze": relative_artifact_descriptor(freeze_path, repo_root=root),
            "phase_a_receipt": relative_artifact_descriptor(receipt_path, repo_root=root),
            **{
                name: relative_artifact_descriptor(path, repo_root=root)
                for name, path in phase_b_paths.items()
            },
            "raw_archive": raw_descriptor,
        },
        "counts": {
            "methods": len(CALIBRATOR_METHODS),
            "windows": len(window_ids),
            "scopes_per_method_window": CANONICAL_GROUPS + 1,
            "evaluation_cells": int(len(evaluation)),
            "overall_cells": int(len(overall)),
            "pairwise_cells": int(len(pairwise)),
            **actual,
        },
        "gates": {
            "phase_a_vector_hash_replay_exact": True,
            "phase_a_source_is_direct_child_of_protocol": True,
            "annotated_tag_chain_verified": True,
            "platt_v5_max_abs_difference": maximum_reconciliation,
            "platt_v5_tolerance": tolerance,
            "complete_grid": True,
            "all_methods_and_windows_reported": True,
        },
        "git_transport": {
            "protocol_commit_role": "B",
            "verified_source_commit_role": "A_single_direct_child_of_P",
            "required_final_artifact_tag": FINAL_ARTIFACT_TAG,
            "final_output_commit_role": "C_single_direct_child_of_B",
            "annotated_tags_required": True,
        },
        "result_boundary": {
            "nominal_coverage": 1.0 - float(design["alpha"]),
            "overall_cells_with_coverage_upper_below_nominal": below_nominal,
            "overall_cells_with_coverage_upper_at_or_above_nominal": int(
                len(overall) - below_nominal
            ),
            "all_overall_cells_below_nominal": all_overall_below_nominal,
            "result_state": (
                "all_32_overall_upper_below_nominal"
                if all_overall_below_nominal
                else "uniform_closed_family_shortfall_not_established"
            ),
            "allowed_if_all_below": (
                "Within this closed four-calibrator family and the common q_raw taxonomy, "
                "the complete-archive coverage shortfall is calibrator-robust."
            ),
            "required_if_any_not_below": (
                "The identified complete-archive shortfall is not established uniformly "
                "across the closed calibrator family. This does not establish that true "
                "coverage itself is calibrator-dependent."
            ),
            "no_theorem_refutation_from_archive": True,
        },
        "identification": {
            "coverage_bounds": "sharp_loanwise_binary_completion_bounds",
            "pairwise_differences": "sharp_shared_loanwise_binary_completion_bounds",
            "sampling_confidence_intervals": False,
            "missing_at_random_assumption": False,
        },
        "interpretation": dict(cast(Mapping[str, Any], config["interpretation"])),
        "artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in written.items()
        },
        "implementation_provenance": _implementation(
            resolved_config,
            root,
            evaluation=True,
        ),
        "environment": environment_provenance(root),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    summary_path = atomic_write_json(
        outputs.model_dir / str(output["summary"]),
        summary,
    )
    atomic_write_json(
        outputs.model_dir / str(output["execution_receipt"]),
        {
            "schema_version": str(config["schema_version"]),
            "status": "complete_calibrator_sensitivity_phase_b_execution_receipt",
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "summary": relative_artifact_descriptor(summary_path, repo_root=root),
            "environment": environment_provenance(root),
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    return summary_path
