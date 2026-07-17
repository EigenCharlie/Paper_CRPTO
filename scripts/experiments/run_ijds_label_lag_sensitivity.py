"""Run the predeclared label-lag sensitivity on the frozen V4 score."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.ijds_audit.config import load_v4_config
from src.ijds_audit.lag_sensitivity import build_label_lag_phase_sensitivity
from src.ijds_audit.protocol import (
    load_outcome_universe,
    load_recipes,
    verified_freeze_artifact_paths,
)
from src.utils.isolated_experiment import (
    implementation_provenance,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_repo_input,
    validate_run_tag,
    write_csv_atomic,
)
from src.utils.pipeline_runtime import atomic_write_json

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs/experiments/ijds_label_lag_sensitivity_2026-07-14.yaml"
ALLOWED_OUTPUT_ROOT = Path("reports/crpto/sensitivity")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Label-lag sensitivity config must be a mapping.")
    sensitivity = payload.get("lag_sensitivity", {})
    if sensitivity.get("outcome_based_selection") is not False:
        raise ValueError("Label-lag sensitivity cannot select from outcomes.")
    if [int(value) for value in sensitivity.get("charged_off_lag_months", [])] != [
        0,
        3,
        6,
        8,
        12,
    ]:
        raise ValueError("Label-lag sensitivity grid must remain 0/3/6/8/12 months.")
    return payload


def _output_dir(config: dict[str, Any], root: Path) -> Path:
    allowed = (root / ALLOWED_OUTPUT_ROOT).resolve()
    output = (allowed / validate_run_tag(str(config["run_tag"]))).resolve()
    output.relative_to(allowed)
    if output.exists():
        raise FileExistsError(f"Sensitivity output already exists: {output}")
    output.mkdir(parents=True)
    return output


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    root = args.repo_root.resolve()
    config_path = resolve_repo_input(args.config, repo_root=root)
    config = _load_config(config_path)
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))
    parent_path = resolve_repo_input(config["parent"]["config"], repo_root=root)
    parent = load_v4_config(parent_path)
    freeze_path = resolve_repo_input(config["parent"]["protocol_freeze"]["path"], repo_root=root)
    freeze_descriptor = relative_artifact_descriptor(freeze_path, repo_root=root)
    for field in ("path", "bytes", "sha256"):
        if freeze_descriptor[field] != config["parent"]["protocol_freeze"][field]:
            raise RuntimeError(f"Parent freeze mismatch for {field}.")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    artifacts = verified_freeze_artifact_paths(freeze, repo_root=root)
    raw_path = resolve_repo_input(parent["source"]["raw_path"], repo_root=root)
    universe = load_outcome_universe(parent, raw_path=raw_path)
    scores = pd.read_parquet(artifacts["scores"])
    if not scores["id"].astype("string").equals(universe["id"].astype("string")):
        raise RuntimeError("Frozen scores do not align to the design universe.")
    recipes = load_recipes(artifacts["recipes"])["catboost_platt"]
    table = build_label_lag_phase_sensitivity(
        universe,
        scores["pd_catboost_platt"].to_numpy(dtype=float),
        recipes,
        {**parent, "lag_sensitivity": config["lag_sensitivity"]},
        lag_months=[int(value) for value in config["lag_sensitivity"]["charged_off_lag_months"]],
    )
    output = _output_dir(config, root)
    table_path = write_csv_atomic(table, output / "label_lag_phase_sensitivity.csv")
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_frozen_score_label_lag_sensitivity",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "historical_archive_previously_inspected": True,
        "outcome_based_selection": False,
        "source_freeze": freeze_descriptor,
        "results": {
            "rows": int(len(table)),
            "lags": sorted(table["charged_off_lag_months"].unique().tolist()),
            "windows": int(table["window_id"].nunique()),
            "minimum_monthly_retention_by_lag": {
                str(int(lag)): float(frame["minimum_monthly_retention"].iloc[0])
                for lag, frame in table.groupby("charged_off_lag_months", sort=True)
            },
            "retention_stop_pass_by_lag": {
                str(int(lag)): bool(frame["passes_locked_retention"].all())
                for lag, frame in table.groupby("charged_off_lag_months", sort=True)
            },
        },
        "artifact": relative_artifact_descriptor(table_path, repo_root=root),
        "implementation": implementation_provenance(
            config_path=config_path,
            repo_root=root,
            relative_paths=[
                Path("src/ijds_audit/lag_sensitivity.py"),
                Path("scripts/experiments/run_ijds_label_lag_sensitivity.py"),
                Path("docs/research/ijds_label_lag_sensitivity_protocol_2026-07-14.md"),
            ],
        ),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    print(atomic_write_json(output / "evidence.json", summary))


if __name__ == "__main__":
    main()
