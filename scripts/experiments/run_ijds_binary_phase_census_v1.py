"""Run the clean, hash-bound 200-cell binary phase census."""

from __future__ import annotations

import argparse
import subprocess
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.ijds_audit.binary_phase_census import (
    FIT_INPUT_COLUMNS,
    FROZEN_INPUT_COLUMNS,
    build_binary_phase_census,
)
from src.utils.isolated_experiment import (
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    prepare_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_isolated_run_dir,
    resolve_repo_input,
    write_csv_atomic,
)
from src.utils.pipeline_runtime import atomic_write_strict_json

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
EXPECTED_RUN_TAG = "ijds-binary-phase-census-2026-08-01-v1"
EXPECTED_PROTOCOL_PATH = Path("docs/research/ijds_binary_phase_census_v1_protocol_2026-08-01.md")
EXPECTED_PROTOCOL_TAG = "protocol/ijds-binary-phase-census-2026-08-01-v1"
EXPECTED_ARTIFACT_TAG = "artifacts/ijds-binary-phase-census-2026-08-01-v1"
EXPECTED_SOURCE_ROLES = {
    "credit_control_freeze": "provenance_witness_unparsed",
    "residual_fit_audit": "scientific_table_allowlisted_columns",
    "exchangeability_summary": "provenance_witness_unparsed",
    "exchangeability_strata": "scientific_table_allowlisted_columns",
}
EXPECTED_OUTPUT = {
    "data_root": "data/processed/experiments/ijds_audit",
    "model_root": "models/experiments/ijds_audit",
    "immutability": "hard_no_overwrite_choose_fresh_run_tag",
    "cell_table": "binary_phase_census.csv",
    "summary": "binary_phase_census_summary.json",
    "execution_receipt": "execution_receipt.json",
}
EXPECTED_CLAIM_BOUNDARY = {
    "retrospective": True,
    "preregistered": False,
    "confirmatory": False,
    "complete_grid_only": True,
    "complete_ordered_stratum_summary": True,
    "learner_window_permutation_symmetric_summary": True,
    "no_stratum_omission_or_selection": True,
    "no_named_path_or_winner": True,
    "no_evaluation_endpoint_or_target_join": True,
    "no_coverage_transport_or_validity_claim": True,
    "no_optimization_policy_or_funded_set_claim": True,
    "no_unconditional_phase_margin_interpretation": True,
    "no_automatic_paper_or_claim_promotion": True,
}
EXPECTED_STOP_RULES = {
    "stop_on_source_hash_mismatch",
    "stop_on_source_role_mismatch",
    "stop_on_preexisting_output_path",
    "stop_on_protocol_gate_failure",
    "stop_on_implementation_drift",
    "stop_on_incomplete_or_asymmetric_grid",
    "stop_on_duplicate_key_or_fit_id",
    "stop_on_invalid_domain_score_label_count_or_rank",
    "stop_on_empty_calibration_class",
    "stop_on_threshold_or_tie_reconciliation_failure",
    "stop_on_exact_identity_failure",
}
IMPLEMENTATION_PATHS = (
    EXPECTED_PROTOCOL_PATH,
    Path("src/ijds_audit/binary_phase_census.py"),
    Path("scripts/experiments/run_ijds_binary_phase_census_v1.py"),
    Path("tests/test_ijds_audit/test_binary_phase_census.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Binary phase census config must be a mapping.")
    required = {
        "schema_version",
        "protocol_status",
        "run_tag",
        "protocol_path",
        "protocol_tag",
        "artifact_tag",
        "source",
        "design",
        "execution_gate",
        "output",
        "claim_boundary",
        "stop_rules",
    }
    actual = set(payload)
    if actual != required:
        raise ValueError(
            "Binary phase census config must contain the exact top-level contract; "
            f"missing={sorted(required.difference(actual))}, "
            f"extra={sorted(actual.difference(required))}."
        )
    return payload


def _require_fixed_output_contract(output: Any) -> None:
    if not isinstance(output, Mapping) or set(output) != set(EXPECTED_OUTPUT):
        raise RuntimeError("The exact output mapping contract changed.")
    filename_fields = ("cell_table", "summary", "execution_receipt")
    filenames: list[str] = []
    for field in filename_fields:
        value = output.get(field)
        if not isinstance(value, str):
            raise RuntimeError(f"Output filename {field} must be a safe basename.")
        filename = value.strip()
        candidate = Path(filename)
        if (
            not filename
            or filename in {".", ".."}
            or candidate.is_absolute()
            or len(candidate.parts) != 1
            or "/" in filename
            or "\\" in filename
            or candidate.name != filename
        ):
            raise RuntimeError(f"Output filename {field} must be a safe basename.")
        filenames.append(filename)
    if len(set(filenames)) != len(filenames):
        raise RuntimeError("The three output filenames must be unique.")
    if dict(output) != EXPECTED_OUTPUT:
        raise RuntimeError("The fixed output paths or filenames changed.")


def _require_fixed_contract(config: Mapping[str, Any]) -> None:
    if config.get("protocol_status") != "retrospectively_locked_before_execution":
        raise RuntimeError("The retrospective protocol lock is absent.")
    exact_values = {
        "run_tag": EXPECTED_RUN_TAG,
        "protocol_path": EXPECTED_PROTOCOL_PATH.as_posix(),
        "protocol_tag": EXPECTED_PROTOCOL_TAG,
        "artifact_tag": EXPECTED_ARTIFACT_TAG,
    }
    for field, expected in exact_values.items():
        if config.get(field) != expected:
            raise RuntimeError(f"The fixed {field} contract changed.")

    source = config.get("source")
    if not isinstance(source, Mapping) or set(source) != set(EXPECTED_SOURCE_ROLES):
        raise RuntimeError("The exact four-source contract changed.")
    for name, role in EXPECTED_SOURCE_ROLES.items():
        descriptor = source.get(name)
        if not isinstance(descriptor, Mapping) or descriptor.get("role") != role:
            raise RuntimeError(f"The source role changed for {name}.")
        if set(descriptor) != {"path", "bytes", "sha256", "role"}:
            raise RuntimeError(f"The source descriptor schema changed for {name}.")

    design = config.get("design")
    if not isinstance(design, Mapping):
        raise TypeError("The census design must be a mapping.")
    learners = design.get("learners")
    windows = design.get("window_ids")
    if not isinstance(learners, list) or not isinstance(windows, list):
        raise TypeError("The declared learner and window domains must be lists.")
    if (
        len(learners),
        len(set(map(str, learners))),
        len(windows),
        len(set(map(str, windows))),
        int(design.get("taxonomy_groups", -1)),
        int(design.get("expected_cells", -1)),
    ) != (5, 5, 8, 8, 5, 200):
        raise RuntimeError("The symmetric 5-by-8-by-5 census design changed.")
    if design.get("require_both_classes_nonempty") is not True:
        raise RuntimeError("The nonempty-class gate cannot be weakened.")
    if design.get("require_uncapped_rank") is not True:
        raise RuntimeError("The uncapped-rank gate cannot be weakened.")

    _require_fixed_output_contract(config.get("output"))

    gates = config.get("execution_gate")
    if not isinstance(gates, Mapping) or not gates:
        raise TypeError("The execution-gate contract must be a nonempty mapping.")
    if not all(value is True for value in gates.values()):
        raise RuntimeError("Every declared execution gate must remain enabled.")

    boundary = config.get("claim_boundary")
    if not isinstance(boundary, Mapping) or dict(boundary) != EXPECTED_CLAIM_BOUNDARY:
        raise RuntimeError("The exact claim-boundary contract changed.")

    stop_rules = config.get("stop_rules")
    if not isinstance(stop_rules, Mapping) or set(stop_rules) != EXPECTED_STOP_RULES:
        raise RuntimeError("The exact stop-rule contract changed.")
    if not all(value is True for value in stop_rules.values()):
        raise RuntimeError("Every frozen stop rule must remain enabled.")


def _require_annotated_tag(repo_root: Path, tag: str) -> None:
    try:
        object_type = subprocess.run(
            ["git", "cat-file", "-t", f"refs/tags/{tag}"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"Required annotated protocol tag is unavailable: {tag}") from exc
    if object_type != "tag":
        raise RuntimeError(f"Protocol tag {tag!r} must be an annotated tag object.")


def _verified_sources(
    source: Mapping[str, Any], *, repo_root: Path
) -> tuple[dict[str, Path], dict[str, dict[str, Any]]]:
    paths: dict[str, Path] = {}
    descriptors: dict[str, dict[str, Any]] = {}
    for name in EXPECTED_SOURCE_ROLES:
        declared = source[name]
        if not isinstance(declared, Mapping):
            raise TypeError(f"Source descriptor {name} must be a mapping.")
        path = resolve_repo_input(str(declared["path"]), repo_root=repo_root)
        actual = relative_artifact_descriptor(path, repo_root=repo_root)
        for field in ("path", "bytes", "sha256"):
            if actual[field] != declared.get(field):
                raise RuntimeError(f"Source {name} mismatched on {field}.")
        paths[name] = path
        descriptors[name] = {**actual, "role": str(declared["role"])}
    return paths, descriptors


def _require_fresh_output_paths(config: Mapping[str, Any], *, repo_root: Path) -> None:
    output = config["output"]
    if not isinstance(output, Mapping):
        raise TypeError("The output contract must be a mapping.")
    run_tag = str(config["run_tag"])
    candidates = (
        resolve_isolated_run_dir(
            repo_root=repo_root,
            configured_root=str(output["data_root"]),
            allowed_relative_root=ALLOWED_DATA_ROOT,
            run_tag=run_tag,
        ),
        resolve_isolated_run_dir(
            repo_root=repo_root,
            configured_root=str(output["model_root"]),
            allowed_relative_root=ALLOWED_MODEL_ROOT,
            run_tag=run_tag,
        ),
    )
    existing = [str(path) for path in candidates if path.exists()]
    if existing:
        raise FileExistsError(f"Census output paths already exist: {existing}")


def run(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Execute the census after every protocol, source, and symmetry gate passes."""
    started_at = _utc_now()
    started_counter = time.perf_counter()
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = _load_config(resolved_config)
    _require_fixed_contract(config)
    protocol_path = resolve_repo_input(str(config["protocol_path"]), repo_root=root)

    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))
    _require_annotated_tag(root, str(config["protocol_tag"]))
    _require_fresh_output_paths(config, repo_root=root)
    initial_git = git_provenance(root)
    implementation_start = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )

    source = config["source"]
    if not isinstance(source, Mapping):
        raise TypeError("The source contract must be a mapping.")
    source_paths, source_descriptors = _verified_sources(source, repo_root=root)

    calibration_rows = pd.read_parquet(
        source_paths["residual_fit_audit"], columns=list(FIT_INPUT_COLUMNS)
    )
    frozen_strata = pd.read_parquet(
        source_paths["exchangeability_strata"], columns=list(FROZEN_INPUT_COLUMNS)
    )
    design = config["design"]
    if not isinstance(design, Mapping):
        raise TypeError("The census design must be a mapping.")
    table, symmetric_results = build_binary_phase_census(
        calibration_rows,
        frozen_strata,
        expected_learners=tuple(str(value) for value in design["learners"]),
        expected_window_ids=tuple(str(value) for value in design["window_ids"]),
        taxonomy_groups=int(design["taxonomy_groups"]),
        expected_cells=int(design["expected_cells"]),
        alpha=float(design["alpha"]),
        threshold_tolerance=float(design["threshold_tolerance"]),
    )

    _, source_descriptors_end = _verified_sources(source, repo_root=root)
    if source_descriptors_end != source_descriptors:
        raise RuntimeError("A hash-bound source changed during census construction.")
    implementation_end = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    if implementation_end != implementation_start:
        raise RuntimeError("The census implementation changed during execution.")
    if require_clean_tagged_head(root, str(config["protocol_tag"])) != protocol_commit:
        raise RuntimeError("Git provenance changed during census construction.")
    _require_annotated_tag(root, str(config["protocol_tag"]))

    paths = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    output = config["output"]
    if not isinstance(output, Mapping):
        raise TypeError("The output contract must be a mapping.")
    table_path = write_csv_atomic(table, paths.data_dir / str(output["cell_table"]))
    table_descriptor = relative_artifact_descriptor(table_path, repo_root=root)
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_hash_bound_binary_phase_census",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "planned_artifact_tag": str(config["artifact_tag"]),
        "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
        "source_artifacts": source_descriptors,
        "source_read_contract": {
            "hash_bound_source_count": 4,
            "unparsed_provenance_witness_count": 2,
            "allowlisted_scientific_table_count": 2,
            "evaluation_endpoint_tables_read": 0,
        },
        "results": symmetric_results,
        "cell_table_schema": dataframe_schema(table),
        "artifacts": {"complete_cell_table": table_descriptor},
        "claim_boundary": dict(config["claim_boundary"]),
        "implementation_provenance": implementation_start,
        "environment": environment_provenance(root),
        "initial_git": initial_git,
        "artifact_commit_status": "pending_single_direct_child_commit_and_annotated_tag",
        "protected_stages_run": [],
        "protected_artifacts_read": [],
        "protected_artifacts_written": [],
    }
    summary_path = atomic_write_strict_json(paths.model_dir / str(output["summary"]), summary)
    completed_at = _utc_now()
    receipt = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_protocol_tagged_execution_receipt",
        "run_tag": str(config["run_tag"]),
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "runtime_seconds": float(time.perf_counter() - started_counter),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "planned_artifact_tag": str(config["artifact_tag"]),
        "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
        "implementation_provenance": implementation_start,
        "sources": source_descriptors,
        "summary": relative_artifact_descriptor(summary_path, repo_root=root),
        "artifacts": summary["artifacts"],
        "initial_git": initial_git,
        "final_git": git_provenance(root),
        "environment": environment_provenance(root),
        "promotion_boundary": (
            "Retrospective calibration-geometry census only. One direct-child artifact "
            "commit and annotated artifact tag remain pending; paper and active-claim "
            "promotion require a separate adversarial audit."
        ),
        "protected_stages_run": [],
        "protected_artifacts_read": [],
        "protected_artifacts_written": [],
    }
    atomic_write_strict_json(paths.model_dir / str(output["execution_receipt"]), receipt)
    return summary_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    print(run(config_path=args.config, repo_root=args.repo_root))


if __name__ == "__main__":
    main()
