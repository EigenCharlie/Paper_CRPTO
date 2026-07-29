"""Run the hash-bound, contained V6 binary phase-geometry replay."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.ijds_audit.binary_phase_geometry import phase_geometry_evidence
from src.utils.artifact_descriptor import relative_artifact_descriptor
from src.utils.isolated_experiment import (
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    prepare_output_paths,
    resolve_repo_input,
    write_csv_atomic,
)
from src.utils.pipeline_runtime import atomic_write_json

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
IMPLEMENTATION_PATHS = (
    Path("scripts/experiments/run_ijds_binary_phase_geometry_v6.py"),
    Path("src/ijds_audit/binary_phase_geometry.py"),
    Path("docs/research/ijds_binary_phase_geometry_v6_protocol_2026-07-26.md"),
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("V6 binary phase-geometry config must be a mapping.")
    required = {"schema_version", "run_tag", "protocol_path", "source", "design", "output"}
    if missing := required.difference(payload):
        raise ValueError(f"V6 config omits fields: {sorted(missing)}")
    return payload


def _verified_path(descriptor: Mapping[str, Any], *, root: Path) -> Path:
    path = resolve_repo_input(str(descriptor["path"]), repo_root=root)
    actual = relative_artifact_descriptor(path, repo_root=root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor.get(field):
            raise RuntimeError(f"V6 source mismatched on {field}: {path}.")
    return path


def _require_same_descriptor(
    actual: Mapping[str, Any], expected: Mapping[str, Any], *, label: str
) -> None:
    for field in ("path", "bytes", "sha256"):
        if actual.get(field) != expected.get(field):
            raise RuntimeError(f"{label} descriptor changed on {field}.")


def run(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Execute the post-protocol replay without reading paper-facing outputs."""
    started_at = _utc_now()
    started_counter = time.perf_counter()
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = _load_config(resolved_config)
    protocol_path = resolve_repo_input(str(config["protocol_path"]), repo_root=root)
    implementation_start = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    initial_git = git_provenance(root)

    source = config["source"]
    freeze_path = _verified_path(source["credit_control_freeze"], root=root)
    fit_path = _verified_path(source["residual_fit_audit"], root=root)
    exchange_summary_path = _verified_path(source["exchangeability_summary"], root=root)
    strata_path = _verified_path(source["exchangeability_strata"], root=root)

    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("status") != "credit_control_scores_frozen_before_primary_oot_outcome_join":
        raise RuntimeError("The source five-learner outcome-free freeze is incomplete.")
    frozen_artifacts = freeze.get("outcome_free_artifacts")
    if not isinstance(frozen_artifacts, Mapping):
        raise TypeError("The source freeze omits outcome-free artifacts.")
    frozen_fit = frozen_artifacts.get("fit_audit")
    if not isinstance(frozen_fit, Mapping):
        raise TypeError("The source freeze omits the residual-fit audit descriptor.")
    _require_same_descriptor(frozen_fit, source["residual_fit_audit"], label="Residual-fit audit")

    exchange = json.loads(exchange_summary_path.read_text(encoding="utf-8"))
    if exchange.get("status") != "complete_retrospective_exchangeability_transport_test":
        raise RuntimeError("The source joint-block diagnostic is incomplete.")
    exchange_artifacts = exchange.get("artifacts")
    if not isinstance(exchange_artifacts, Mapping):
        raise TypeError("The joint-block summary omits artifacts.")
    frozen_strata_descriptor = exchange_artifacts.get("stratum_tests")
    if not isinstance(frozen_strata_descriptor, Mapping):
        raise TypeError("The joint-block summary omits its stratum table.")
    _require_same_descriptor(
        frozen_strata_descriptor,
        source["exchangeability_strata"],
        label="Frozen 200-row stratum table",
    )

    design = config["design"]
    learners = tuple(str(value) for value in design["learners"])
    window_ids = tuple(str(value) for value in design["window_ids"])
    taxonomy_groups = int(design["taxonomy_groups"])
    if (len(learners), len(window_ids), taxonomy_groups) != (5, 8, 5):
        raise RuntimeError("The V6 five-by-eight-by-five design changed.")
    frozen_strata = pd.read_parquet(strata_path)
    frozen_strata = frozen_strata.copy()
    frozen_strata["score_stratum"] = frozen_strata["conformal_group"].astype(int) + 1
    evidence, phase_table = phase_geometry_evidence(
        fit_audit_path=fit_path,
        frozen_strata=frozen_strata,
        expected_learners=learners,
        expected_window_ids=window_ids,
        alpha=float(design["alpha"]),
        taxonomy_groups=taxonomy_groups,
    )
    required_publication_columns = {
        "learner",
        "window_id",
        "taxonomy_groups",
        "conformal_group",
        "score_stratum",
        "fit_rows",
        "fit_defaults",
        "fit_nondefaults",
        "finite_sample_rank",
        "boundary_count",
        "boundary_closed_form",
        "phase_margin",
        "recomputed_threshold",
        "threshold_is_capped",
        "threshold_below_half",
        "separation_no_interleave",
        "separation_below_half",
        "count_nondefault_below_half",
        "count_default_above_half",
        "exact_half_criterion",
        "fit_score_min",
        "fit_score_max",
        "fit_score_max_nondefault",
        "fit_score_max_default",
    }
    if missing := required_publication_columns.difference(phase_table.columns):
        raise RuntimeError(f"The V6 S6I publication contract omits: {sorted(missing)}")
    if len(phase_table) != int(design["expected_strata"]):
        raise RuntimeError("The V6 S6I census changed.")

    implementation_end = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    if implementation_end != implementation_start:
        raise RuntimeError("V6 implementation changed during execution.")

    paths = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    output = config["output"]
    phase_output = write_csv_atomic(phase_table, paths.data_dir / str(output["phase_table"]))
    source_descriptors = {
        "credit_control_freeze": relative_artifact_descriptor(freeze_path, repo_root=root),
        "residual_fit_audit": relative_artifact_descriptor(fit_path, repo_root=root),
        "exchangeability_summary": relative_artifact_descriptor(
            exchange_summary_path, repo_root=root
        ),
        "exchangeability_strata": relative_artifact_descriptor(strata_path, repo_root=root),
    }
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_hash_bound_post_protocol_binary_phase_geometry_v6_replay",
        "run_tag": str(config["run_tag"]),
        "protocol_commit_available_at_execution": False,
        "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
        "source_artifacts": source_descriptors,
        "results": evidence,
        "table_schema": dataframe_schema(phase_table),
        "artifacts": {
            "stratum_phase_margins": relative_artifact_descriptor(
                phase_output, repo_root=root
            )
        },
        "claim_boundary": dict(config["claim_boundary"]),
        "implementation_provenance": implementation_start,
        "environment": environment_provenance(root),
        "initial_git": initial_git,
        "protected_stages_run": [],
        "protected_artifacts_read": [],
        "protected_artifacts_written": [],
    }
    summary_path = atomic_write_json(paths.model_dir / str(output["summary"]), summary)
    final_git = git_provenance(root)
    atomic_write_json(
        paths.model_dir / str(output["execution_receipt"]),
        {
            "schema_version": str(config["schema_version"]),
            "status": "complete_hash_bound_uncommitted_protocol_execution_receipt",
            "run_tag": str(config["run_tag"]),
            "started_at_utc": started_at,
            "completed_at_utc": _utc_now(),
            "runtime_seconds": float(time.perf_counter() - started_counter),
            "protocol_commit_available_at_execution": False,
            "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
            "implementation_provenance": implementation_start,
            "sources": source_descriptors,
            "summary": relative_artifact_descriptor(summary_path, repo_root=root),
            "artifacts": summary["artifacts"],
            "initial_git": initial_git,
            "final_git": final_git,
            "environment": environment_provenance(root),
            "promotion_boundary": (
                "Hash-bound retrospective replay. A clean tagged promotion requires "
                "a new run tag and fresh replay; no protocol commit is asserted here."
            ),
            "protected_stages_run": [],
            "protected_artifacts_read": [],
            "protected_artifacts_written": [],
        },
    )
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
