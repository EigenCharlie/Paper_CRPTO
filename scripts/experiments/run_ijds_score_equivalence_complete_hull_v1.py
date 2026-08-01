"""Run the locked outcome-free IJDS complete-hull score-equivalence audit V1."""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from itertools import combinations
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ijds_audit.calibrator_sensitivity import (  # noqa: E402
    CALIBRATOR_METHODS,
    CalibratorFamily,
    apply_calibrator_family,
    apply_common_taxonomy_recipe,
    float_array_sha256,
    load_recipe_payload,
    recover_catboost_base_probability,
    string_array_sha256,
    unordered_method_pairs,
)
from src.ijds_audit.protocol import load_recipes, verified_freeze_artifact_paths  # noqa: E402
from src.ijds_audit.score_equivalence_complete_hull import (  # noqa: E402
    certificate_record,
    certify_complete_budget_hull,
    certify_full_budget_score_equivalence,
    deterministic_nonaffine_control,
)
from src.ijds_challengers.archive import (  # noqa: E402
    load_outcome_free_decision_base,
    verified_parent_artifacts,
)
from src.ijds_challengers.set_preserving_embedding import (  # noqa: E402
    embedding_diagnostics,
    load_set_preserving_config,
    set_preserving_upper,
)
from src.models.binary_conformal_guardrail import apply_binary_outcome_recipe  # noqa: E402
from src.utils.artifact_descriptor import (  # noqa: E402
    relative_artifact_descriptor,
    verified_artifact_path,
)
from src.utils.isolated_experiment import (  # noqa: E402
    environment_provenance,
    git_provenance,
    implementation_provenance,
    prepare_output_paths,
    require_clean_tagged_head,
    resolve_repo_input,
)
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    utc_now_iso,
)

DEFAULT_CONFIG_PATH = (
    ROOT / "configs/experiments/ijds_score_equivalence_complete_hull_2026-07-31_v1.yaml"
)
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
RUN_STATUS = "complete_outcome_free_score_equivalence_complete_hull_audit"
ARTIFACT_STATUS = "pending_single_direct_child_commit_and_annotated_artifact_tag"
IMPLEMENTATION_PATHS = (
    Path("scripts/experiments/run_ijds_score_equivalence_complete_hull_v1.py"),
    Path("src/ijds_audit/score_equivalence_complete_hull.py"),
    Path("src/ijds_audit/calibrator_sensitivity.py"),
    Path("src/ijds_audit/protocol.py"),
    Path("src/ijds_challengers/archive.py"),
    Path("src/ijds_challengers/set_preserving_embedding.py"),
    Path("src/models/binary_conformal_guardrail.py"),
    Path("src/utils/artifact_descriptor.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("docs/research/ijds_score_equivalence_complete_hull_v1_protocol_2026-07-31.md"),
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def _descriptor(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"path", "bytes", "sha256"}:
        raise ValueError(f"{label} must be an exact path/bytes/sha256 descriptor.")
    path = value.get("path")
    size = value.get("bytes")
    digest = value.get("sha256")
    if (
        not isinstance(path, str)
        or not path
        or Path(path).is_absolute()
        or ".." in Path(path).parts
        or not isinstance(size, int)
        or size <= 0
        or not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError(f"{label} descriptor is invalid.")
    return {"path": path, "bytes": size, "sha256": digest}


def load_complete_hull_config(path: Path) -> dict[str, Any]:
    """Load V1 and reject any scientific or output-scope drift."""

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Complete-hull config must be a mapping.")
    expected_top = {
        "schema_version",
        "protocol_status",
        "protocol_tag",
        "artifact_tag",
        "run_tag",
        "protocol_path",
        "git_transport",
        "sources",
        "design",
        "numerics",
        "expected_census",
        "stop_rules",
        "output",
        "interpretation",
    }
    if set(payload) != expected_top:
        raise ValueError("Complete-hull config top-level schema changed.")
    expected_identity = {
        "schema_version": "2026-07-31.1",
        "protocol_status": "locked_retrospective_outcome_free_complete_hull_audit",
        "protocol_tag": "protocol/ijds-score-equivalence-complete-hull-2026-07-31-v1",
        "artifact_tag": "artifacts/ijds-score-equivalence-complete-hull-2026-07-31-v1",
        "run_tag": "ijds-score-equivalence-complete-hull-2026-07-31-v1",
        "protocol_path": (
            "docs/research/ijds_score_equivalence_complete_hull_v1_protocol_2026-07-31.md"
        ),
    }
    if any(payload[key] != value for key, value in expected_identity.items()):
        raise ValueError("Complete-hull protocol identity changed.")

    transport = payload["git_transport"]
    expected_source_tags = {
        "v1d_source": {
            "tag": (
                "artifacts/ijds-set-preserving-embedding-sensitivity-2026-07-30-v1a-recovery-v1d"
            ),
            "commit": "95e39f05bb990429025d0115a0e55c53b1fb1ea8",
        },
        "v1d_evaluation": {
            "tag": "artifacts/ijds-set-preserving-embedding-sensitivity-2026-07-30-v1d",
            "commit": "276a5db8772262aad2edd8936dbe226926e412b5",
        },
        "calibrator_source": {
            "tag": "artifacts/ijds-calibrator-sensitivity-2026-07-30-v1-source",
            "commit": "ea3e7326afc38ccc1b99b09de30792986640e3c3",
        },
        "calibrator_evaluation": {
            "tag": "artifacts/ijds-calibrator-sensitivity-2026-07-30-v1",
            "commit": "6552524eae5a22ce66b50689900383d16df1ff13",
        },
    }
    data_prefix = (
        "data/processed/experiments/ijds_audit/ijds-score-equivalence-complete-hull-2026-07-31-v1/"
    )
    model_prefix = (
        "models/experiments/ijds_audit/ijds-score-equivalence-complete-hull-2026-07-31-v1/"
    )
    expected_transport_paths = [
        f"{data_prefix}complete_hull_certificates.parquet",
        f"{data_prefix}v1d_embedding_score_equivalence.parquet",
        f"{data_prefix}calibrator_score_equivalence.parquet",
        f"{data_prefix}runtime_controls.parquet",
        f"{model_prefix}score_equivalence_summary.json",
        f"{model_prefix}execution_receipt.json",
    ]
    if (
        set(transport)
        != {
            "artifact_commit_relationship",
            "annotated_tags_required",
            "source_tags",
            "exact_output_paths",
        }
        or transport.get("artifact_commit_relationship") != "single_direct_child_of_protocol_commit"
        or transport.get("annotated_tags_required") is not True
        or transport.get("source_tags") != expected_source_tags
        or transport.get("exact_output_paths") != expected_transport_paths
    ):
        raise ValueError("Complete-hull Git transport contract changed.")

    source_keys = {
        "v1d_scientific_config",
        "v1d_active_delta_config",
        "v1d_outcome_free_freeze",
        "v1d_active_evaluation_manifest",
        "calibrator_phase_a_freeze",
        "scores",
        "v4_residual_recipes",
        "raw_decision_archive",
        "calibrator_family",
        "calibrator_residual_recipes",
    }
    if set(payload["sources"]) != source_keys:
        raise ValueError("Complete-hull source census changed.")
    for name, value in payload["sources"].items():
        _descriptor(value, label=f"sources.{name}")

    design = payload["design"]
    expected_windows = (
        "w01_2012m01_m06",
        "w02_2012m02_m07",
        "w03_2012m03_m08",
        "w04_2012m04_m09",
        "w05_2012m05_m10",
        "w06_2012m06_m11",
        "w07_2012m07_m12",
        "w08_2012m08_2013m01",
    )
    if (
        tuple(design.get("roles", ())) != ("policy_development", "primary_oot")
        or int(design.get("expected_policy_development_months", -1)) != 11
        or int(design.get("expected_primary_oot_months", -1)) != 15
        or int(design.get("expected_total_months", -1)) != 26
        or tuple(design.get("windows", ())) != expected_windows
        or tuple(float(value) for value in design.get("theta_grid", ()))
        != (0.0, 0.25, 0.5, 0.75, 1.0)
        or float(design.get("theta_reference", np.nan)) != 0.0
        or tuple(float(value) for value in design.get("gamma_grid", ()))
        != (0.0, 0.25, 0.5, 0.75, 1.0)
        or tuple(design.get("calibrator_methods", ())) != CALIBRATOR_METHODS
        or design.get("calibrator_pairing") != "all_six_unordered_pairs"
        or design.get("score_definition") != "q_gamma_equals_p_plus_gamma_times_upper_minus_p"
        or float(design.get("budget_dollars", np.nan)) != 1_000_000.0
        or float(design.get("purpose_cap", np.nan)) != 0.25
        or tuple(design.get("raw_allowed_columns", ()))
        != ("id", "loan_amnt", "int_rate", "purpose")
        or tuple(design.get("raw_forbidden_tokens", ()))
        != ("status", "outcome", "default", "pymnt", "realized", "miscoverage")
        or design.get("outcome_columns_passed") != []
    ):
        raise ValueError("Complete-hull scientific design changed.")

    numerics = payload["numerics"]
    numeric_expectation = {
        "hull_absolute_tolerance_dollars": 1.0e-8,
        "hull_relative_tolerance": 1.0e-12,
        "score_absolute_tolerance": 1.0e-12,
        "score_relative_tolerance": 1.0e-10,
        "vector_replay_tolerance": 5.0e-14,
        "v1d_diagnostic_float_tolerance": 1.0e-12,
        "synthetic_positive_scale": 1.75,
        "synthetic_positive_intercept": 0.125,
        "synthetic_negative_amplitude": 1.0e-3,
    }
    if set(numerics) != set(numeric_expectation) or any(
        float(numerics[key]) != value for key, value in numeric_expectation.items()
    ):
        raise ValueError("Complete-hull numerical contract changed.")

    census_expectation = {
        "complete_hull_certificates": 26,
        "v1d_embedding_comparisons": 5200,
        "v1d_theta_zero_self_controls": 1040,
        "v1d_gamma_zero_controls": 1040,
        "v1d_nonzero_theta_gamma_zero_controls": 832,
        "calibrator_comparisons": 6240,
        "calibrator_pairs": 6,
        "runtime_controls": 52,
        "runtime_positive_controls": 26,
        "runtime_negative_controls": 26,
        "v1d_set_preservation_rows": 80,
    }
    if payload["expected_census"] != census_expectation:
        raise ValueError("Complete-hull expected census changed.")
    expected_stop_rules = {
        "require_clean_exact_annotated_protocol_tag",
        "require_annotated_source_tags_and_ancestry",
        "stop_on_source_descriptor_or_hash_drift",
        "stop_on_candidate_identity_or_census_drift",
        "stop_on_outcome_like_decision_column",
        "stop_on_calibrator_vector_hash_mismatch",
        "stop_on_v1d_set_preservation_replay_mismatch",
        "stop_on_incomplete_hull_certificate",
        "stop_on_positive_or_negative_control_failure",
        "stop_on_incomplete_or_duplicate_grid",
        "stop_on_nonfinite_persisted_numeric",
        "hard_no_overwrite",
    }
    if payload["stop_rules"] != dict.fromkeys(expected_stop_rules, True):
        raise ValueError("Every complete-hull stop rule must remain enabled.")

    output = payload["output"]
    expected_output_keys = {
        "data_root",
        "model_root",
        "complete_hull_certificates",
        "v1d_embedding_score_equivalence",
        "calibrator_score_equivalence",
        "runtime_controls",
        "summary",
        "execution_receipt",
        "immutability",
    }
    if (
        set(output) != expected_output_keys
        or output.get("data_root") != ALLOWED_DATA_ROOT.as_posix()
        or output.get("model_root") != ALLOWED_MODEL_ROOT.as_posix()
        or output.get("immutability") != "hard_no_overwrite_choose_fresh_run_tag"
    ):
        raise ValueError("Complete-hull output contract changed.")
    for key in expected_output_keys - {"data_root", "model_root", "immutability"}:
        value = str(output[key])
        if Path(value).name != value or value in {"", ".", ".."}:
            raise ValueError(f"Output {key} must be one basename.")
    if (
        len(
            {
                str(output[key]).casefold()
                for key in expected_output_keys - {"data_root", "model_root", "immutability"}
            }
        )
        != 6
    ):
        raise ValueError("Complete-hull output basenames collide.")
    expected_interpretation = {
        "retrospective": True,
        "outcome_free": True,
        "complete_candidate_menu_not_funded_subset": True,
        "optimization_run": False,
        "protected_stages_run": [],
        "protected_artifacts_written": [],
        "calibrator_embedding_gamma_window_role_or_month_selected": False,
        "failure_means_global_invariance_not_certified": True,
        "failure_implies_fixed_cell_allocation_change": False,
        "common_objective_across_calibrator_maps_established": False,
        "calibrator_score_equivalence_certifies_full_optimizer_invariance": False,
        "common_solver_output_certifies_equal_optimal_faces": False,
        "selected_or_funded_set_validity": False,
        "portfolio_performance_claim": False,
        "causal_claim": False,
    }
    if payload["interpretation"] != expected_interpretation:
        raise ValueError("Complete-hull interpretation boundary changed.")
    return payload


def _annotated_tag_commit(repo_root: Path, tag: str) -> str:
    try:
        tag_type = subprocess.run(
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
        raise RuntimeError(f"Required annotated tag is unavailable: {tag}") from exc
    if tag_type != "tag" or not commit:
        raise RuntimeError(f"Tag {tag!r} must be annotated and resolve to one commit.")
    return commit


def _require_ancestor(repo_root: Path, *, ancestor: str, descendant: str) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Frozen source commit {ancestor} is not an ancestor of {descendant}.")


def _require_descriptor_at_commit(
    repo_root: Path,
    *,
    commit: str,
    descriptor: Mapping[str, Any],
    label: str,
) -> None:
    """Require a configured source descriptor to exist byte-for-byte at its tag commit."""

    logical = str(descriptor["path"])
    try:
        payload = subprocess.run(
            ["git", "show", f"{commit}:{logical}"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"Could not read {label} from its frozen source commit.") from exc
    actual = {
        "path": logical,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    if actual != dict(descriptor):
        raise RuntimeError(f"{label} descriptor differs from its frozen source commit.")


def _candidate_identity_contract(frame: pd.DataFrame) -> dict[str, Any]:
    identity = frame.loc[:, ["role", "period", "id"]].copy()
    if bool(identity.isna().any(axis=None)):
        raise RuntimeError("Candidate identity contains a missing role, period, or ID.")
    identity = identity.astype("string")
    if bool(identity["id"].duplicated().any()):
        raise RuntimeError("Candidate identity contains duplicate loan IDs.")
    identity = identity.sort_values(["role", "period", "id"], kind="mergesort")

    def digest(rows: pd.DataFrame) -> str:
        hasher = hashlib.sha256()
        for row in rows.itertuples(index=False, name=None):
            encoded = json.dumps(list(row), ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
            hasher.update(len(encoded).to_bytes(8, byteorder="big", signed=False))
            hasher.update(encoded)
        return hasher.hexdigest()

    groups = [
        {
            "role": str(role),
            "period": str(period),
            "rows": int(len(group)),
            "sha256": digest(group),
        }
        for (role, period), group in identity.groupby(["role", "period"], observed=True, sort=True)
    ]
    return {
        "rows": int(len(identity)),
        "groups": groups,
        "sha256": digest(identity),
        "canonicalization": "utf8_length_prefixed_json_role_period_id_sorted_mergesort_sha256",
    }


def _month_indices(base: pd.DataFrame, roles: Sequence[str]) -> dict[tuple[str, str], np.ndarray]:
    role_values = base["design_split"].astype(str)
    period_values = pd.to_datetime(base["issue_d"]).dt.to_period("M").astype(str)
    output: dict[tuple[str, str], np.ndarray] = {}
    for role in roles:
        periods = sorted(period_values.loc[role_values.eq(role)].unique())
        for period in periods:
            mask = role_values.eq(role) & period_values.eq(period)
            output[(str(role), str(period))] = np.flatnonzero(mask.to_numpy(dtype=bool))
    return output


def _verify_source_tags(
    config: Mapping[str, Any], *, repo_root: Path, protocol_commit: str
) -> dict[str, str]:
    observed: dict[str, str] = {}
    source_tags = cast(Mapping[str, Any], config["git_transport"])["source_tags"]
    for name, raw in cast(Mapping[str, Any], source_tags).items():
        source = cast(Mapping[str, Any], raw)
        tag = str(source["tag"])
        expected_commit = str(source["commit"])
        actual_commit = _annotated_tag_commit(repo_root, tag)
        if actual_commit != expected_commit:
            raise RuntimeError(f"Frozen source tag {name} changed commit.")
        _require_ancestor(repo_root, ancestor=actual_commit, descendant=protocol_commit)
        observed[str(name)] = actual_commit
    return observed


def _verify_configured_sources(
    config: Mapping[str, Any],
    *,
    repo_root: Path,
    include_raw_hash: bool,
) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    sources = cast(Mapping[str, Any], config["sources"])
    for name, raw_descriptor in sources.items():
        descriptor = _descriptor(raw_descriptor, label=f"sources.{name}")
        if name == "raw_decision_archive" and not include_raw_hash:
            path = resolve_repo_input(descriptor["path"], repo_root=repo_root)
            if int(path.stat().st_size) != int(descriptor["bytes"]):
                raise RuntimeError("Raw decision archive changed byte size.")
        else:
            path = verified_artifact_path(
                descriptor,
                repo_root=repo_root,
                label=f"complete-hull {name}",
            )
        paths[str(name)] = path
    return paths


def _load_verified_sources(
    config: Mapping[str, Any],
    *,
    paths: Mapping[str, Path],
    repo_root: Path,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Path],
    dict[str, Any],
    dict[str, Path],
]:
    v1_config = load_set_preserving_config(paths["v1d_scientific_config"])
    parent_paths, parent_freeze = verified_parent_artifacts(v1_config, repo_root=repo_root)
    for configured, parent_name in (("scores", "scores"), ("v4_residual_recipes", "recipes")):
        if paths[configured] != parent_paths[parent_name]:
            raise RuntimeError(f"Configured {configured} is not the V1d frozen parent source.")

    v1d_freeze = json.loads(paths["v1d_outcome_free_freeze"].read_text(encoding="utf-8"))
    if (
        v1d_freeze.get("status") != "outcome_free_set_preserving_allocations_frozen_before_outcomes"
        or v1d_freeze.get("outcome_columns_passed_to_frontier") != []
        or v1d_freeze.get("protected_stages_run") != []
        or v1d_freeze.get("protected_artifacts_written") != []
    ):
        raise RuntimeError("V1d outcome-free freeze boundary changed.")
    v1d_artifacts = verified_freeze_artifact_paths(v1d_freeze, repo_root=repo_root)
    if "embedding_diagnostics" not in v1d_artifacts:
        raise RuntimeError("V1d source freeze omits embedding diagnostics.")

    v1d_manifest = json.loads(paths["v1d_active_evaluation_manifest"].read_text(encoding="utf-8"))
    if (
        v1d_manifest.get("status")
        != "retrospective_post_inspection_v1d_phase_b_complete_not_confirmatory"
        or v1d_manifest.get("run_tag") != "ijds-set-preserving-embedding-sensitivity-2026-07-30-v1d"
    ):
        raise RuntimeError("Active V1d evaluation manifest changed status or run identity.")

    calibrator_freeze = json.loads(paths["calibrator_phase_a_freeze"].read_text(encoding="utf-8"))
    if (
        calibrator_freeze.get("status")
        != "calibrator_maps_and_common_taxonomy_frozen_before_primary_oot_outcome_evaluation"
        or calibrator_freeze.get("protected_stages_run") != []
        or calibrator_freeze.get("protected_artifacts_written") != []
    ):
        raise RuntimeError("Calibrator Phase-A freeze boundary changed.")
    calibrator_artifacts: dict[str, Path] = {}
    for name, descriptor in cast(
        Mapping[str, Any], calibrator_freeze["outcome_free_artifacts"]
    ).items():
        calibrator_artifacts[str(name)] = verified_artifact_path(
            cast(Mapping[str, Any], descriptor),
            repo_root=repo_root,
            label=f"calibrator Phase-A {name}",
        )
    if (
        calibrator_artifacts.get("calibrator_family") != paths["calibrator_family"]
        or calibrator_artifacts.get("residual_recipes") != paths["calibrator_residual_recipes"]
    ):
        raise RuntimeError("Configured calibrator artifacts differ from the Phase-A freeze.")
    source_artifacts = cast(Mapping[str, Any], calibrator_freeze["source_artifacts"])
    for configured, frozen_name in (
        ("scores", "scores"),
        ("v4_residual_recipes", "residual_recipes"),
        ("raw_decision_archive", "raw_archive"),
    ):
        if dict(cast(Mapping[str, Any], config["sources"])[configured]) != dict(
            cast(Mapping[str, Any], source_artifacts[frozen_name])
        ):
            raise RuntimeError(f"Calibrator Phase-A {frozen_name} source descriptor changed.")
    return v1_config, v1d_freeze, v1d_artifacts, calibrator_freeze, calibrator_artifacts


def _build_hull_certificates(
    base: pd.DataFrame,
    month_indices: Mapping[tuple[str, str], np.ndarray],
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    design = cast(Mapping[str, Any], config["design"])
    numeric = cast(Mapping[str, Any], config["numerics"])
    rows: list[dict[str, Any]] = []
    for (role, period), indices in month_indices.items():
        month = base.iloc[indices]
        certificate = certify_complete_budget_hull(
            month["loan_amnt"].to_numpy(dtype=float),
            month["purpose"].astype(str).to_numpy(),
            budget=float(design["budget_dollars"]),
            purpose_cap=float(design["purpose_cap"]),
            absolute_tolerance=float(numeric["hull_absolute_tolerance_dollars"]),
            relative_tolerance=float(numeric["hull_relative_tolerance"]),
        )
        if not certificate.full_budget_hull_certified:
            raise RuntimeError(f"Complete full-budget hull was not certified for {role}/{period}.")
        rows.append(
            {
                "role": role,
                "period": period,
                "rows": len(indices),
                **certificate_record(certificate),
            }
        )
    return pd.DataFrame(rows)


def _score_record(
    source: np.ndarray,
    target: np.ndarray,
    *,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    design = cast(Mapping[str, Any], config["design"])
    numeric = cast(Mapping[str, Any], config["numerics"])
    certificate = certify_full_budget_score_equivalence(
        source,
        target,
        budget=float(design["budget_dollars"]),
        absolute_tolerance=float(numeric["score_absolute_tolerance"]),
        relative_tolerance=float(numeric["score_relative_tolerance"]),
    )
    return certificate_record(certificate)


def _v1d_embedding_audit(
    base: pd.DataFrame,
    month_indices: Mapping[tuple[str, str], np.ndarray],
    v4_recipes: Mapping[str, Mapping[str, Mapping[int, Any]]],
    *,
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    design = cast(Mapping[str, Any], config["design"])
    point_all = base["pd_point"].to_numpy(dtype=float)
    rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
    for window_id in design["windows"]:
        recipe = v4_recipes["catboost_platt"][str(window_id)][5]
        _, lower_all, original_upper_all = apply_binary_outcome_recipe(point_all, recipe)
        embedded_by_theta = {
            float(theta): set_preserving_upper(
                point_all,
                lower_all,
                original_upper_all,
                theta=float(theta),
            )
            for theta in design["theta_grid"]
        }
        for role in design["roles"]:
            role_mask = base["design_split"].astype(str).eq(str(role)).to_numpy(dtype=bool)
            for theta in design["theta_grid"]:
                diagnostic_rows.append(
                    {
                        "window_id": str(window_id),
                        "role": str(role),
                        **embedding_diagnostics(
                            point_all[role_mask],
                            lower_all[role_mask],
                            original_upper_all[role_mask],
                            theta=float(theta),
                        ),
                    }
                )
        for (role, period), indices in month_indices.items():
            point = point_all[indices]
            reference_upper = original_upper_all[indices]
            for gamma in design["gamma_grid"]:
                gamma_value = float(gamma)
                reference_score = point + gamma_value * (reference_upper - point)
                for theta in design["theta_grid"]:
                    theta_value = float(theta)
                    target_upper = embedded_by_theta[theta_value][indices]
                    target_score = point + gamma_value * (target_upper - point)
                    rows.append(
                        {
                            "family": "v1d_set_preserving_embedding",
                            "window_id": str(window_id),
                            "role": role,
                            "period": period,
                            "rows": int(len(indices)),
                            "theta": theta_value,
                            "theta_reference": 0.0,
                            "gamma": gamma_value,
                            "theta_zero_self_control": theta_value == 0.0,
                            "gamma_zero_identity_control": gamma_value == 0.0,
                            **_score_record(
                                reference_score,
                                target_score,
                                config=config,
                            ),
                        }
                    )
    return pd.DataFrame(rows), pd.DataFrame(diagnostic_rows)


def _reconcile_v1d_diagnostics(
    observed: pd.DataFrame,
    frozen_path: Path,
    *,
    tolerance: float,
) -> None:
    frozen = pd.read_parquet(frozen_path)
    keys = ["window_id", "role", "theta"]
    observed = observed.sort_values(keys, kind="mergesort").reset_index(drop=True)
    frozen = frozen.sort_values(keys, kind="mergesort").reset_index(drop=True)
    if list(observed.columns) != list(frozen.columns) or len(observed) != len(frozen):
        raise RuntimeError("V1d set-preservation diagnostic schema or census changed.")
    for column in frozen.columns:
        if pd.api.types.is_numeric_dtype(frozen[column]):
            left = pd.to_numeric(observed[column], errors="raise").to_numpy(dtype=float)
            right = pd.to_numeric(frozen[column], errors="raise").to_numpy(dtype=float)
            if not bool(np.allclose(left, right, rtol=0.0, atol=float(tolerance))):
                raise RuntimeError(f"V1d set-preservation replay changed {column}.")
        elif not observed[column].astype(str).equals(frozen[column].astype(str)):
            raise RuntimeError(f"V1d set-preservation replay changed {column}.")
    if not bool(observed["sets_changed"].eq(0).all()):
        raise RuntimeError("V1d replay changed at least one binary prediction set.")


def _load_calibrator_vectors(
    scores: pd.DataFrame,
    *,
    calibrator_freeze: Mapping[str, Any],
    calibrator_family_path: Path,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    with calibrator_family_path.open("rb") as handle:
        family = pickle.load(handle)
    if not isinstance(family, CalibratorFamily):
        raise TypeError("Frozen calibrator family has an unexpected type.")
    frozen_platt = scores["pd_catboost_platt"].to_numpy(dtype=float)
    margin, q_raw = recover_catboost_base_probability(frozen_platt, family.platt)
    probabilities, venn_pair = apply_calibrator_family(
        family,
        q_raw=q_raw,
        margin=margin,
        frozen_platt_probability=frozen_platt,
    )
    hashes = cast(Mapping[str, Any], calibrator_freeze["score_vector_hashes"])
    observed = {
        "id": string_array_sha256(scores["id"].astype(str)),
        "q_raw": float_array_sha256(q_raw),
        **{
            f"probability_{method}": float_array_sha256(probabilities[method])
            for method in CALIBRATOR_METHODS
        },
        "venn_abers_p0": float_array_sha256(venn_pair[:, 0]),
        "venn_abers_p1": float_array_sha256(venn_pair[:, 1]),
    }
    for name, digest in observed.items():
        if hashes.get(name) != digest:
            raise RuntimeError(f"Frozen calibrator vector hash changed: {name}.")
    return q_raw, probabilities


def _calibrator_audit(
    base: pd.DataFrame,
    scores: pd.DataFrame,
    q_raw: np.ndarray,
    probabilities: Mapping[str, np.ndarray],
    recipes: Mapping[str, Mapping[str, Any]],
    month_indices: Mapping[tuple[str, str], np.ndarray],
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    design = cast(Mapping[str, Any], config["design"])
    lookup = pd.DataFrame(
        {
            "id": scores["id"].astype(str),
            "q_raw": q_raw,
            **{f"probability_{name}": probabilities[name] for name in CALIBRATOR_METHODS},
        }
    )
    enriched = base.merge(lookup, on="id", how="left", sort=False, validate="one_to_one")
    if not np.array_equal(enriched["id"].astype(str).to_numpy(), base["id"].astype(str).to_numpy()):
        raise RuntimeError("Calibrator vector join changed the decision-base row order.")
    required = ["q_raw", *(f"probability_{name}" for name in CALIBRATOR_METHODS)]
    if bool(enriched[required].isna().any(axis=None)):
        raise RuntimeError("Calibrator vector join omitted at least one decision candidate.")
    q_base = enriched["q_raw"].to_numpy(dtype=float)
    probability_base = {
        method: enriched[f"probability_{method}"].to_numpy(dtype=float)
        for method in CALIBRATOR_METHODS
    }
    rows: list[dict[str, Any]] = []
    expected_pairs = unordered_method_pairs()
    if expected_pairs != tuple(combinations(CALIBRATOR_METHODS, 2)):
        raise RuntimeError("Calibrator unordered-pair contract changed.")
    for window_id in design["windows"]:
        upper: dict[str, np.ndarray] = {}
        for method in CALIBRATOR_METHODS:
            _, _, method_upper = apply_common_taxonomy_recipe(
                q_raw=q_base,
                calibrated_probability=probability_base[method],
                recipe=recipes[method][str(window_id)],
            )
            upper[method] = method_upper
        for (role, period), indices in month_indices.items():
            for gamma in design["gamma_grid"]:
                gamma_value = float(gamma)
                scores_by_method = {
                    method: probability_base[method][indices]
                    + gamma_value * (upper[method][indices] - probability_base[method][indices])
                    for method in CALIBRATOR_METHODS
                }
                if gamma_value == 0.0:
                    for method in CALIBRATOR_METHODS:
                        if not np.array_equal(
                            scores_by_method[method], probability_base[method][indices]
                        ):
                            raise RuntimeError(
                                f"Gamma-zero score did not exactly replay {method} probability."
                            )
                for method_a, method_b in expected_pairs:
                    rows.append(
                        {
                            "family": "closed_calibrator_q_gamma",
                            "window_id": str(window_id),
                            "role": role,
                            "period": period,
                            "rows": int(len(indices)),
                            "method_a": method_a,
                            "method_b": method_b,
                            "gamma": gamma_value,
                            "gamma_zero_probability_reconciliation": gamma_value == 0.0,
                            **_score_record(
                                scores_by_method[method_a],
                                scores_by_method[method_b],
                                config=config,
                            ),
                        }
                    )
    return pd.DataFrame(rows)


def _runtime_controls(
    base: pd.DataFrame,
    month_indices: Mapping[tuple[str, str], np.ndarray],
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    numeric = cast(Mapping[str, Any], config["numerics"])
    point = base["pd_point"].to_numpy(dtype=float)
    rows: list[dict[str, Any]] = []
    for (role, period), indices in month_indices.items():
        source = point[indices]
        positive = float(numeric["synthetic_positive_scale"]) * source + float(
            numeric["synthetic_positive_intercept"]
        )
        negative = deterministic_nonaffine_control(
            source,
            amplitude=float(numeric["synthetic_negative_amplitude"]),
        )
        for control_type, target, expected in (
            ("positive_affine", positive, True),
            ("negative_nonaffine", negative, False),
        ):
            record = _score_record(source, target, config=config)
            observed = bool(record["equivalent_on_complete_budget_hull"])
            rows.append(
                {
                    "role": role,
                    "period": period,
                    "rows": int(len(indices)),
                    "control_type": control_type,
                    "expected_equivalent": expected,
                    "observed_equivalent": observed,
                    "control_passed": observed is expected,
                    **record,
                }
            )
    return pd.DataFrame(rows)


def _require_finite_nonmissing(frame: pd.DataFrame, *, label: str) -> None:
    if frame.empty or bool(frame.isna().any(axis=None)):
        raise RuntimeError(f"{label} is empty or contains missing persisted values.")
    numeric_columns = [
        column for column in frame.columns if pd.api.types.is_numeric_dtype(frame[column])
    ]
    if numeric_columns and not bool(
        np.isfinite(frame[numeric_columns].to_numpy(dtype=float)).all()
    ):
        raise RuntimeError(f"{label} contains a non-finite persisted numeric value.")


def validate_complete_outputs(
    hull: pd.DataFrame,
    v1d: pd.DataFrame,
    calibrator: pd.DataFrame,
    controls: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> None:
    """Fail closed on every declared census, key, control, and numeric gate."""

    expected = cast(Mapping[str, Any], config["expected_census"])
    for label, frame, count in (
        ("complete hull", hull, expected["complete_hull_certificates"]),
        ("V1d equivalence", v1d, expected["v1d_embedding_comparisons"]),
        ("calibrator equivalence", calibrator, expected["calibrator_comparisons"]),
        ("runtime controls", controls, expected["runtime_controls"]),
    ):
        if len(frame) != int(count):
            raise RuntimeError(f"{label} census changed: {len(frame)} != {count}.")
        _require_finite_nonmissing(frame, label=label)
        forbidden = tuple(
            str(token).casefold()
            for token in cast(Mapping[str, Any], config["design"])["raw_forbidden_tokens"]
        )
        if any(
            any(token in str(column).casefold() for token in forbidden) for column in frame.columns
        ):
            raise RuntimeError(f"{label} persisted an outcome-like column name.")

    if bool(hull.duplicated(["role", "period"]).any()) or not bool(
        hull["full_budget_hull_certified"].astype(bool).all()
    ):
        raise RuntimeError("Complete-hull output is duplicated or uncertified.")
    if bool(v1d.duplicated(["window_id", "role", "period", "theta", "gamma"]).any()):
        raise RuntimeError("V1d score-equivalence grid contains duplicate keys.")
    if bool(
        calibrator.duplicated(
            ["window_id", "role", "period", "method_a", "method_b", "gamma"]
        ).any()
    ):
        raise RuntimeError("Calibrator score-equivalence grid contains duplicate keys.")
    if bool(controls.duplicated(["role", "period", "control_type"]).any()) or not bool(
        controls["control_passed"].astype(bool).all()
    ):
        raise RuntimeError("Runtime controls are duplicated or failed.")

    theta_zero = v1d["theta"].eq(0.0)
    gamma_zero = v1d["gamma"].eq(0.0)
    nonzero_theta_gamma_zero = gamma_zero & ~theta_zero
    if (
        int(theta_zero.sum()) != int(expected["v1d_theta_zero_self_controls"])
        or int(gamma_zero.sum()) != int(expected["v1d_gamma_zero_controls"])
        or int(nonzero_theta_gamma_zero.sum())
        != int(expected["v1d_nonzero_theta_gamma_zero_controls"])
        or not bool(
            v1d.loc[theta_zero | gamma_zero, "equivalent_on_complete_budget_hull"]
            .astype(bool)
            .all()
        )
    ):
        raise RuntimeError("V1d theta-zero or gamma-zero identity controls failed.")
    positive = controls["control_type"].eq("positive_affine")
    negative = controls["control_type"].eq("negative_nonaffine")
    if (
        int(positive.sum()) != int(expected["runtime_positive_controls"])
        or int(negative.sum()) != int(expected["runtime_negative_controls"])
        or not bool(controls.loc[positive, "observed_equivalent"].astype(bool).all())
        or bool(controls.loc[negative, "observed_equivalent"].astype(bool).any())
    ):
        raise RuntimeError("Synthetic positive or negative control behavior changed.")
    pair_count = len(calibrator.loc[:, ["method_a", "method_b"]].drop_duplicates())
    if pair_count != int(expected["calibrator_pairs"]):
        raise RuntimeError("Calibrator unordered-pair census changed.")


def run_complete_hull_audit(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Materialize the complete outcome-free audit under its tagged protocol."""

    started = time.perf_counter()
    started_at = utc_now_iso()
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_complete_hull_config(resolved_config)
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))
    if _annotated_tag_commit(root, str(config["protocol_tag"])) != protocol_commit:
        raise RuntimeError("Complete-hull protocol tag is not annotated at current HEAD.")
    source_tag_commits = _verify_source_tags(
        config,
        repo_root=root,
        protocol_commit=protocol_commit,
    )
    initial_git = git_provenance(root)
    initial_environment = environment_provenance(root)
    initial_implementation = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    paths = _verify_configured_sources(config, repo_root=root, include_raw_hash=False)
    configured_sources = cast(Mapping[str, Any], config["sources"])
    for source_name, commit_role, label in (
        ("v1d_outcome_free_freeze", "v1d_source", "V1d outcome-free freeze"),
        (
            "v1d_active_evaluation_manifest",
            "v1d_evaluation",
            "V1d active evaluation manifest",
        ),
        (
            "calibrator_phase_a_freeze",
            "calibrator_source",
            "calibrator Phase-A freeze",
        ),
    ):
        _require_descriptor_at_commit(
            root,
            commit=source_tag_commits[commit_role],
            descriptor=cast(Mapping[str, Any], configured_sources[source_name]),
            label=label,
        )
    (
        v1_config,
        v1d_freeze,
        v1d_artifacts,
        calibrator_freeze,
        calibrator_artifacts,
    ) = _load_verified_sources(config, paths=paths, repo_root=root)

    base = load_outcome_free_decision_base(
        scores_path=paths["scores"],
        raw_path=paths["raw_decision_archive"],
        config=v1_config,
    )
    identity_frame = base.assign(
        role=base["design_split"].astype("string"),
        period=pd.to_datetime(base["issue_d"]).dt.to_period("M").astype("string"),
    )
    if (
        _candidate_identity_contract(identity_frame)
        != cast(Mapping[str, Any], v1d_freeze["decision_contract"])["candidate_identity"]
    ):
        raise RuntimeError("Complete-hull candidate identity differs from frozen V1d.")
    month_indices = _month_indices(base, cast(Mapping[str, Any], config["design"])["roles"])
    role_month_counts = {
        role: sum(key[0] == role for key in month_indices)
        for role in cast(Mapping[str, Any], config["design"])["roles"]
    }
    if role_month_counts != {"policy_development": 11, "primary_oot": 15}:
        raise RuntimeError(f"Complete-hull month census changed: {role_month_counts}.")

    hull = _build_hull_certificates(base, month_indices, config=config)
    v4_recipes = load_recipes(paths["v4_residual_recipes"])
    v1d, replayed_diagnostics = _v1d_embedding_audit(
        base,
        month_indices,
        v4_recipes,
        config=config,
    )
    _reconcile_v1d_diagnostics(
        replayed_diagnostics,
        v1d_artifacts["embedding_diagnostics"],
        tolerance=float(
            cast(Mapping[str, Any], config["numerics"])["v1d_diagnostic_float_tolerance"]
        ),
    )

    scores = pd.read_parquet(paths["scores"])
    q_raw, probabilities = _load_calibrator_vectors(
        scores,
        calibrator_freeze=calibrator_freeze,
        calibrator_family_path=calibrator_artifacts["calibrator_family"],
    )
    calibrator_recipes = load_recipe_payload(
        json.loads(calibrator_artifacts["residual_recipes"].read_text(encoding="utf-8"))
    )
    calibrator = _calibrator_audit(
        base,
        scores,
        q_raw,
        probabilities,
        calibrator_recipes,
        month_indices,
        config=config,
    )
    controls = _runtime_controls(base, month_indices, config=config)
    validate_complete_outputs(hull, v1d, calibrator, controls, config=config)

    # Repeat every configured descriptor after all calculations and before any
    # output write.  The raw archive is hash-checked here and was independently
    # hash-checked by the four-column decision-base loader.
    repeated_paths = _verify_configured_sources(config, repo_root=root, include_raw_hash=True)
    if repeated_paths != paths:
        raise RuntimeError("A configured source path changed during complete-hull calculation.")
    if git_provenance(root) != initial_git:
        raise RuntimeError("Git state changed during complete-hull calculation.")
    if environment_provenance(root) != initial_environment:
        raise RuntimeError("Scientific environment changed during complete-hull calculation.")
    if (
        implementation_provenance(
            config_path=resolved_config,
            relative_paths=IMPLEMENTATION_PATHS,
            repo_root=root,
        )
        != initial_implementation
    ):
        raise RuntimeError("Complete-hull implementation changed during calculation.")

    outputs = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    output = cast(Mapping[str, Any], config["output"])
    written = {
        "complete_hull_certificates": atomic_write_parquet(
            hull,
            outputs.data_dir / str(output["complete_hull_certificates"]),
        ),
        "v1d_embedding_score_equivalence": atomic_write_parquet(
            v1d,
            outputs.data_dir / str(output["v1d_embedding_score_equivalence"]),
        ),
        "calibrator_score_equivalence": atomic_write_parquet(
            calibrator,
            outputs.data_dir / str(output["calibrator_score_equivalence"]),
        ),
        "runtime_controls": atomic_write_parquet(
            controls,
            outputs.data_dir / str(output["runtime_controls"]),
        ),
    }
    elapsed = float(time.perf_counter() - started)
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": RUN_STATUS,
        "artifact_status": ARTIFACT_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "required_artifact_tag": str(config["artifact_tag"]),
        "started_at_utc": started_at,
        "elapsed_seconds": elapsed,
        "counts": {
            "complete_hull_certificates": int(len(hull)),
            "v1d_embedding_comparisons": int(len(v1d)),
            "calibrator_comparisons": int(len(calibrator)),
            "runtime_controls": int(len(controls)),
            "v1d_equivalent_cells": int(
                v1d["equivalent_on_complete_budget_hull"].astype(bool).sum()
            ),
            "v1d_nonequivalent_cells": int(
                (~v1d["equivalent_on_complete_budget_hull"].astype(bool)).sum()
            ),
            "calibrator_equivalent_cells": int(
                calibrator["equivalent_on_complete_budget_hull"].astype(bool).sum()
            ),
            "calibrator_nonequivalent_cells": int(
                (~calibrator["equivalent_on_complete_budget_hull"].astype(bool)).sum()
            ),
        },
        "gates": {
            "complete_hull_all_26_months": True,
            "v1d_candidate_identity_exact": True,
            "v1d_set_preservation_80_rows_exact": True,
            "calibrator_full_vector_hash_replay_exact": True,
            "theta_zero_self_controls_pass": True,
            "gamma_zero_embedding_identity_controls_pass": True,
            "synthetic_positive_and_negative_controls_pass": True,
            "complete_grids_and_finite_outputs": True,
            "outcome_columns_passed": [],
            "optimization_run": False,
        },
        "source_tag_commits": source_tag_commits,
        "source_artifacts": {
            name: dict(cast(Mapping[str, Any], config["sources"])[name])
            for name in config["sources"]
        },
        "result_boundary": {
            "failure_means_global_invariance_not_certified": True,
            "failure_implies_fixed_cell_allocation_change": False,
            "passing_requires_translated_caps": True,
            "calibrator_common_objective_established": False,
            "calibrator_score_equivalence_certifies_full_optimizer_invariance": False,
            "selected_embedding_calibrator_gamma_window_role_month_or_policy": None,
            "portfolio_performance_claim": False,
            "selected_or_funded_set_validity": False,
        },
        "interpretation": dict(cast(Mapping[str, Any], config["interpretation"])),
        "artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in written.items()
        },
        "implementation_provenance": initial_implementation,
        "environment": initial_environment,
        "git": initial_git,
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    summary_path = atomic_write_json(outputs.model_dir / str(output["summary"]), summary)
    receipt = {
        "schema_version": str(config["schema_version"]),
        "status": RUN_STATUS,
        "artifact_status": ARTIFACT_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "required_artifact_tag": str(config["artifact_tag"]),
        "summary": relative_artifact_descriptor(summary_path, repo_root=root),
        "elapsed_seconds": elapsed,
        "outcome_columns_passed": [],
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    atomic_write_json(outputs.model_dir / str(output["execution_receipt"]), receipt)
    return summary_path


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    result = run_complete_hull_audit(config_path=args.config, repo_root=args.repo_root)
    print(result)


if __name__ == "__main__":
    main()
