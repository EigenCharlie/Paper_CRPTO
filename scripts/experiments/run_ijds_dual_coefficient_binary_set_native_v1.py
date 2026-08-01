"""Build the 208 logical certificates for the dual-coefficient set-native model."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ijds_audit.config import load_v4_config  # noqa: E402
from src.ijds_challengers.dual_coefficient_binary_set_native import (  # noqa: E402
    build_menu_certificates,
    certificate_digest,
    load_dual_coefficient_config,
)
from src.utils.isolated_experiment import (  # noqa: E402
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    relative_artifact_descriptor,
    resolve_isolated_run_dir,
    resolve_repo_input,
)
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    utc_now_iso,
)

DEFAULT_CONFIG = (
    ROOT / "configs/experiments/ijds_dual_coefficient_binary_set_native_2026-08-01_v1.yaml"
)
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
STATUS = "outcome_free_dual_coefficient_binary_set_native_certificates_complete"
IMPLEMENTATION_PATHS = (
    Path("docs/research/ijds_dual_coefficient_binary_set_native_v1_protocol_2026-08-01.md"),
    Path("scripts/experiments/run_ijds_dual_coefficient_binary_set_native_v1.py"),
    Path("src/ijds_challengers/dual_coefficient_binary_set_native.py"),
    Path("tests/test_ijds_dual_coefficient_binary_set_native_v1.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args(argv)


def _resolve_annotated_tag(root: Path, tag: str) -> tuple[str, str]:
    reference = f"refs/tags/{tag}"
    valid = subprocess.run(
        ["git", "check-ref-format", reference],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if valid.returncode != 0 or str(tag).startswith(("-", "refs/")):
        raise RuntimeError(f"Invalid explicit tag name: {tag!r}.")
    object_id = subprocess.run(
        ["git", "rev-parse", "--verify", "--end-of-options", reference],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    object_type = subprocess.run(
        ["git", "cat-file", "-t", object_id],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    commit = subprocess.run(
        ["git", "rev-parse", "--verify", "--end-of-options", f"{reference}^{{commit}}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(object_id) != 40 or object_type != "tag" or len(commit) != 40:
        raise RuntimeError(f"An annotated tag is required: {tag!r}.")
    return object_id, commit


def _require_clean_tagged_head(root: Path, tag: str) -> dict[str, str]:
    state = git_provenance(root)
    if state.get("dirty") is not False:
        raise RuntimeError("Execution requires a clean predeclared worktree.")
    object_id, commit = _resolve_annotated_tag(root, tag)
    if state.get("commit") != commit:
        raise RuntimeError(f"Annotated protocol tag {tag!r} must resolve exactly to HEAD.")
    return {"tag": tag, "tag_object": object_id, "commit": commit}


def _require_source_descriptor(descriptor: Mapping[str, Any], *, root: Path, label: str) -> Path:
    path = resolve_repo_input(str(descriptor["path"]), repo_root=root)
    if relative_artifact_descriptor(path, repo_root=root) != dict(descriptor):
        raise RuntimeError(f"Hash-pinned predecessor source changed: {label}.")
    return path


def _require_predecessor_authority(
    config: Mapping[str, Any], *, root: Path
) -> tuple[dict[str, Path], dict[str, Any]]:
    predecessor = config["predecessor"]
    protocol = _resolve_annotated_tag(root, str(predecessor["protocol_tag"]))
    artifact = _resolve_annotated_tag(root, str(predecessor["artifact_tag"]))
    if protocol[1] != predecessor["protocol_commit"]:
        raise RuntimeError("Predecessor protocol tag changed.")
    if artifact[1] != predecessor["artifact_commit"]:
        raise RuntimeError("Predecessor artifact tag changed.")
    paths = {
        name: _require_source_descriptor(predecessor[name], root=root, label=name)
        for name in ("solve_records", "taxonomy", "summary", "manifest")
    }
    implementation_paths = {
        name: _require_source_descriptor(descriptor, root=root, label=f"implementation.{name}")
        for name, descriptor in predecessor["implementation_sources"].items()
    }
    parent_config = load_v4_config(implementation_paths["parent_config"])
    inherited = config["inherited_contract"]
    observed_contract = {
        "budget_dollars": float(parent_config["policy"]["budget"]),
        "maximum_concentration_by_purpose": float(
            parent_config["policy"]["max_concentration_by_purpose"]
        ),
        "lgd": float(parent_config["payoff"]["lgd"]),
    }
    expected_contract = {
        key: float(inherited[key])
        for key in ("budget_dollars", "maximum_concentration_by_purpose", "lgd")
    }
    if observed_contract != expected_contract:
        raise RuntimeError("Inherited budget, purpose cap, or LGD changed.")
    summary = json.loads(paths["summary"].read_text(encoding="utf-8"))
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    if not isinstance(summary, dict) or not isinstance(manifest, dict):
        raise TypeError("Predecessor summary and manifest must be JSON objects.")
    expected_status = "outcome_free_set_native_binary_robust_counterpart_complete"
    if summary.get("status") != expected_status or manifest.get("status") != expected_status:
        raise RuntimeError("Predecessor summary/manifest completion status changed.")
    if manifest.get("run_tag") != predecessor["run_tag"]:
        raise RuntimeError("Predecessor manifest run identity changed.")
    official = manifest.get("official_artifacts")
    if not isinstance(official, dict):
        raise RuntimeError("Predecessor manifest lacks official artifacts.")
    if official.get("solve_records") != predecessor["solve_records"]:
        raise RuntimeError("Predecessor solve-record descriptor disagrees with its manifest.")
    if official.get("set_taxonomy") != predecessor["taxonomy"]:
        raise RuntimeError("Predecessor taxonomy descriptor disagrees with its manifest.")
    return paths, summary


def _require_committed_implementation(
    provenance: Mapping[str, Any], *, commit: str, root: Path
) -> None:
    sources = provenance.get("source_files")
    if not isinstance(sources, dict) or provenance.get("hash_algorithm") != "sha256":
        raise RuntimeError("Implementation provenance schema is invalid.")
    for relative, descriptor in sources.items():
        blob = subprocess.run(
            ["git", "show", f"{commit}:{relative}"],
            cwd=root,
            check=False,
            capture_output=True,
        )
        observed = {
            "path": relative,
            "bytes": len(blob.stdout),
            "sha256": hashlib.sha256(blob.stdout).hexdigest(),
        }
        if blob.returncode != 0 or observed != descriptor:
            raise RuntimeError(f"Tagged Git blob disagrees with authority: {relative}.")


def _output_dirs(config: Mapping[str, Any], root: Path) -> tuple[Path, Path]:
    output = config["output"]
    data_dir = resolve_isolated_run_dir(
        repo_root=root,
        configured_root=output["data_root"],
        allowed_relative_root=ALLOWED_DATA_ROOT,
        run_tag=config["run_tag"],
    )
    model_dir = resolve_isolated_run_dir(
        repo_root=root,
        configured_root=output["model_root"],
        allowed_relative_root=ALLOWED_MODEL_ROOT,
        run_tag=config["run_tag"],
    )
    return data_dir, model_dir


def run(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Verify existing outcome-free evidence and emit only logical certificates."""
    started = time.perf_counter()
    started_at = utc_now_iso()
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_dual_coefficient_config(resolved_config)
    protocol = _require_clean_tagged_head(root, str(config["protocol_tag"]))
    implementation = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    _require_committed_implementation(implementation, commit=protocol["commit"], root=root)
    source_paths, predecessor_summary = _require_predecessor_authority(config, root=root)
    data_dir, model_dir = _output_dirs(config, root)
    if data_dir.exists() or model_dir.exists():
        raise FileExistsError("Official output is occupied; historical artifacts are immutable.")

    solve_records = pd.read_parquet(source_paths["solve_records"])
    taxonomy = pd.read_parquet(source_paths["taxonomy"])
    certificates = build_menu_certificates(
        solve_records,
        taxonomy,
        predecessor_summary,
        config=config,
    )
    digest = certificate_digest(certificates)
    repeated_paths, repeated_summary = _require_predecessor_authority(config, root=root)
    if repeated_paths != source_paths or repeated_summary != predecessor_summary:
        raise RuntimeError("Predecessor authority changed during certificate construction.")

    data_dir.mkdir(parents=True, exist_ok=False)
    model_dir.mkdir(parents=True, exist_ok=False)
    output = config["output"]
    certificate_path = atomic_write_parquet(
        certificates, data_dir / str(output["menu_certificates"])
    )
    certificate_descriptor = relative_artifact_descriptor(certificate_path, repo_root=root)
    summary_payload = {
        "schema_version": config["schema_version"],
        "status": STATUS,
        "run_tag": config["run_tag"],
        "protocol": protocol,
        "counts": {"menu_certificates": int(len(certificates)), "new_optimizations": 0},
        "certificate_sha256": digest,
        "all_conditions_certified": True,
        "all_maximin_optimizers_singleton_zero": True,
        "continuous_cap_frontier_collapses": True,
        "cap_domain": [0.0, 1.0],
        "raw_archive_read": False,
        "outcome_columns_passed": [],
        "selection": {"cap": None, "window": None, "policy": None},
        "validity_claim_established": False,
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    summary_path = atomic_write_json(model_dir / str(output["summary"]), summary_payload)
    receipt_path = atomic_write_json(
        model_dir / str(output["receipt"]),
        {
            "schema_version": config["schema_version"],
            "status": STATUS,
            "run_tag": config["run_tag"],
            "protocol": protocol,
            "started_at_utc": started_at,
            "completed_at_utc": utc_now_iso(),
            "elapsed_seconds": float(time.perf_counter() - started),
            "predecessor_rows_read": int(len(solve_records) + len(taxonomy)),
            "new_optimizations": 0,
            "raw_archive_read": False,
            "outcome_columns_passed": [],
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    manifest_path = atomic_write_json(
        model_dir / str(output["manifest"]),
        {
            "schema_version": config["schema_version"],
            "status": STATUS,
            "run_tag": config["run_tag"],
            "official_artifacts": {"menu_certificates": certificate_descriptor},
            "official_schemas": {"menu_certificates": dataframe_schema(certificates)},
            "source_artifacts": {
                name: dict(config["predecessor"][name])
                for name in ("solve_records", "taxonomy", "summary", "manifest")
            },
        },
    )
    freeze_path = atomic_write_json(
        model_dir / str(output["protocol_freeze"]),
        {
            "schema_version": config["schema_version"],
            "status": STATUS,
            "artifact_status": "pending_git_artifact_commit_and_annotated_tag",
            "run_tag": config["run_tag"],
            "protocol": protocol,
            "predecessor": {
                "run_tag": config["predecessor"]["run_tag"],
                "artifact_tag": config["predecessor"]["artifact_tag"],
                "artifact_commit": config["predecessor"]["artifact_commit"],
            },
            "official_artifacts": {"menu_certificates": certificate_descriptor},
            "summary": relative_artifact_descriptor(summary_path, repo_root=root),
            "execution_receipt": relative_artifact_descriptor(receipt_path, repo_root=root),
            "manifest": relative_artifact_descriptor(manifest_path, repo_root=root),
            "implementation_provenance": implementation,
            "environment": environment_provenance(root),
            "git": git_provenance(root),
            "artifact_contract": {
                "expected_tag": output["artifact_tag"],
                "dvc_required": False,
            },
            "outcome_columns_passed": [],
            "new_optimizations": 0,
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    return freeze_path


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    print(run(config_path=args.config))


if __name__ == "__main__":
    main()
