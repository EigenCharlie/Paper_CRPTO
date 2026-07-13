"""Build the full-archive data and feature-contract audit for IJDS."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from src.ijds_audit.config import load_v4_config
from src.ijds_audit.raw_data_audit import audit_raw_dataset
from src.utils.isolated_experiment import (
    git_provenance,
    relative_artifact_descriptor,
    resolve_repo_input,
    sha256_file,
    validate_run_tag,
    write_csv_atomic,
)
from src.utils.pipeline_runtime import atomic_write_json

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs/experiments/ijds_raw_data_contract_2026-07-13.yaml"
ALLOWED_OUTPUT_ROOT = Path("reports/crpto/data_audit")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Raw-data audit config must be a YAML mapping.")
    if payload.get("status") != "retrospective_full_archive_data_contract_audit":
        raise ValueError("Unexpected raw-data audit status.")
    if payload.get("rules", {}).get("no_model_or_policy_selection") is not True:
        raise ValueError("The raw-data audit cannot select a model or policy.")
    return payload


def _output_dir(config: dict[str, Any], repo_root: Path) -> Path:
    run_tag = validate_run_tag(str(config["run_tag"]))
    configured = (repo_root / str(config["output"]["root"])).resolve()
    allowed = (repo_root / ALLOWED_OUTPUT_ROOT).resolve()
    if configured != allowed:
        raise ValueError(f"Output root {configured} is not allowlisted as {allowed}.")
    output = (allowed / run_tag).resolve()
    output.relative_to(allowed)
    if output.exists():
        raise FileExistsError(f"Audit output already exists: {output}")
    output.mkdir(parents=True)
    return output


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    root = args.repo_root.resolve()
    config_path = resolve_repo_input(args.config, repo_root=root)
    config = _load_config(config_path)
    base_path = resolve_repo_input(config["base_protocol"], repo_root=root)
    base = load_v4_config(base_path)
    raw_path = resolve_repo_input(base["source"]["raw_path"], repo_root=root)
    output = _output_dir(config, root)
    audit = audit_raw_dataset(raw_path, base)

    written = {
        "cohort_inventory": write_csv_atomic(audit.inventory, output / "cohort_inventory.csv"),
        "feature_coverage": write_csv_atomic(
            audit.feature_coverage, output / "raw_feature_coverage.csv"
        ),
        "feature_contract": write_csv_atomic(
            audit.feature_contract, output / "raw_feature_contract.csv"
        ),
        "amount_alignment": write_csv_atomic(
            audit.amount_alignment, output / "loan_amount_alignment.csv"
        ),
        "cutoff_label_availability": write_csv_atomic(
            audit.cutoff_label_availability, output / "cutoff_label_availability.csv"
        ),
    }
    primary = audit.amount_alignment.loc[audit.amount_alignment["cohort"].eq("primary_oot")].iloc[0]
    late_count = int(audit.feature_contract["late_feature"].sum())
    eligible_count = int(audit.feature_contract["eligible_for_current_temporal_model"].sum())
    evidence = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_full_archive_data_contract_audit",
        "run_tag": str(config["run_tag"]),
        "base_protocol": relative_artifact_descriptor(base_path, repo_root=root),
        "config": relative_artifact_descriptor(config_path, repo_root=root),
        "raw_source": {
            **relative_artifact_descriptor(raw_path, repo_root=root),
            "dvc_md5": "65adade308f21d60b7213088a88e684d",
        },
        "results": {
            "raw_schema_columns": int(len(audit.feature_contract)),
            "term36_active_design_rows": int(
                audit.inventory.loc[
                    audit.inventory["cohort"].isin(
                        [
                            "pd_development",
                            "probability_calibration",
                            "conformal_fit",
                            "policy_development",
                            "primary_oot",
                            "censored_extension",
                        ]
                    ),
                    "rows",
                ].sum()
            ),
            "eligible_raw_features": eligible_count,
            "late_schema_features": late_count,
            "primary_oot_partial_funding_share": float(primary["partial_share"]),
            "primary_oot_funded_ratio": float(primary["funded_ratio"]),
            "primary_oot_total_requested_minus_funded": float(primary["total_gap"]),
        },
        "artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in written.items()
        },
        "implementation_sha256": sha256_file(root / "src/ijds_audit/raw_data_audit.py"),
        "git": git_provenance(root),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    evidence_path = atomic_write_json(output / "evidence.json", evidence)
    print(evidence_path)


if __name__ == "__main__":
    main()
