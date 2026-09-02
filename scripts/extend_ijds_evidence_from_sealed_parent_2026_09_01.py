"""Extend the sealed IJDS evidence with the complete target-support census.

The extension reads only hash-bound paper tables from the pinned parent,
derives all 200 learner-window-stratum rows without selection, refreshes the
two affected figures, and promotes one transactional publication generation.
No protected scientific stage is executed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import pandas as pd

from scripts.build_ijds_binary_geometry_frontier_v4_evidence import (
    EVIDENCE_PATH,
    FIGURE_DIR,
    FIGURE_STEMS,
    SOURCE_REGISTRY_PATH,
    TABLE_TARGETS,
    _binary_phase_target_support_manifest_payload,
    _binary_phase_target_support_publication_table,
    _coverage_figure,
    _phase_census_figure,
)
from src.ijds_audit.claim_ledger import materialize_claim_ledger
from src.ijds_audit.publication_generation import (
    promote_publication_generation,
    publication_implementation_descriptors,
    staged_artifact_descriptor,
    staged_output_path,
)
from src.ijds_audit.publication_sources import load_verified_or_sealed_source_registry
from src.utils.artifact_descriptor import relative_artifact_descriptor
from src.utils.pipeline_runtime import atomic_write_strict_json, atomic_write_text

ROOT = Path(__file__).resolve().parents[1]
CLAIM_LEDGER_PATH = ROOT / "configs/ijds_claim_ledger.yaml"
PARENT_COMMIT = "01b1b08437c1de415fad7569de42257ee5110e79"
PARENT_MANIFEST_PATH = "reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json"
PARENT_REGISTRY_PATH = "configs/ijds_active_evidence_sources.yaml"
PARENT_MANIFEST_BYTES = 3_984_046
PARENT_MANIFEST_SHA256 = "838fdff2fb0532ae2fd64f5ffa0649170e076bee50e800427b02d5c09de32261"
PARENT_SCHEMA = "2026-08-01.1"
PARENT_STATUS = "active_ijds_v5_phase_and_dual_set_native_paper_facing_evidence"
EXTENSION_SCHEMA = "2026-09-01.1"
EXTENSION_STATUS = "active_ijds_v5_phase_target_support_paper_facing_evidence"
NEW_TABLE_KEY = "binary_phase_target_support"
REFRESHED_FIGURES = frozenset({"coverage", "phase_transition"})
PROMOTED_TARGETS = frozenset(
    {
        TABLE_TARGETS[NEW_TABLE_KEY],
        *(
            FIGURE_DIR / f"{FIGURE_STEMS[name]}.{kind}"
            for name in REFRESHED_FIGURES
            for kind in ("png", "pdf")
        ),
    }
)


def _git_blob(commit: str, relative_path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Pinned Git blob is absent: {commit}:{relative_path}")
    return result.stdout


def _load_pinned_parent() -> tuple[bytes, dict[str, Any]]:
    payload = _git_blob(PARENT_COMMIT, PARENT_MANIFEST_PATH)
    if (
        len(payload) != PARENT_MANIFEST_BYTES
        or hashlib.sha256(payload).hexdigest() != PARENT_MANIFEST_SHA256
    ):
        raise RuntimeError("The pinned parent evidence manifest no longer matches its seal.")
    manifest = json.loads(payload)
    if (
        manifest.get("schema_version") != PARENT_SCHEMA
        or manifest.get("status") != PARENT_STATUS
        or len(manifest.get("paper_artifacts", {})) != 55
    ):
        raise RuntimeError("The pinned parent manifest has an unexpected contract.")
    return payload, cast(dict[str, Any], manifest)


def _verified_parent_artifact(
    parent: Mapping[str, Any],
    *,
    artifact_key: str,
    path: Path,
) -> Path:
    artifacts = parent.get("paper_artifacts")
    if not isinstance(artifacts, Mapping):
        raise TypeError("The pinned parent omits paper-artifact descriptors.")
    descriptor = artifacts.get(artifact_key)
    if not isinstance(descriptor, Mapping):
        raise KeyError(f"The pinned parent omits {artifact_key!r}.")
    actual = relative_artifact_descriptor(path, repo_root=ROOT)
    if actual != dict(descriptor):
        raise RuntimeError(f"Canonical parent artifact drifted: {artifact_key}.")
    return path


def _parent_table(parent: Mapping[str, Any], name: str) -> pd.DataFrame:
    path = _verified_parent_artifact(
        parent,
        artifact_key=f"table/{name}",
        path=TABLE_TARGETS[name],
    )
    return pd.read_csv(path)


def _coverage_input_from_parent_table(parent: Mapping[str, Any]) -> pd.DataFrame:
    """Reconstruct sharp pooled bounds from the sealed 40-row diagnostics table."""
    coverage = _parent_table(parent, "conformal_set_diagnostics")
    resolved_covered = (
        (coverage["coverage_resolved"] * coverage["resolved_rows"]).round().astype("int64")
    )
    if not (
        len(coverage) == 40
        and (
            coverage["candidate_rows"] == coverage["resolved_rows"] + coverage["unresolved_rows"]
        ).all()
        and (resolved_covered / coverage["resolved_rows"] == coverage["coverage_resolved"]).all()
    ):
        raise RuntimeError("The sealed 40-row coverage table no longer reconstructs exactly.")
    coverage["coverage_lower"] = resolved_covered / coverage["candidate_rows"]
    coverage["coverage_upper"] = (resolved_covered + coverage["unresolved_rows"]) / coverage[
        "candidate_rows"
    ]
    coverage["conformal_group"] = -1
    return coverage


def _stage_extension(staging_root: Path) -> tuple[Path, dict[Path, Path]]:
    parent_bytes, parent = _load_pinned_parent()
    registry, registered, missing_dvc = load_verified_or_sealed_source_registry(
        SOURCE_REGISTRY_PATH,
        repo_root=ROOT,
        sealed_parent_commit=PARENT_COMMIT,
        sealed_parent_registry_path=PARENT_REGISTRY_PATH,
    )
    phase = _parent_table(parent, "binary_phase_census")
    target = _parent_table(parent, "exchangeability_strata")
    support_table = _binary_phase_target_support_publication_table(phase, target)
    support_payload = _binary_phase_target_support_manifest_payload(support_table)

    coverage = _coverage_input_from_parent_table(parent)
    cells = _parent_table(parent, "exchangeability_cells")
    strata = _parent_table(parent, "exchangeability_strata")

    staged_outputs: dict[Path, Path] = {}
    staged_tables: dict[str, Path] = {}
    for name, target_path in TABLE_TARGETS.items():
        staged = staged_output_path(staging_root, target_path, repo_root=ROOT)
        if name == NEW_TABLE_KEY:
            atomic_write_text(staged, support_table.to_csv(index=False, lineterminator="\n"))
        else:
            source = _verified_parent_artifact(
                parent,
                artifact_key=f"table/{name}",
                path=target_path,
            )
            staged.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, staged)
        staged_tables[name] = staged
        staged_outputs[target_path] = staged

    staged_figure_dir = staging_root / "outputs" / FIGURE_DIR.relative_to(ROOT)
    refreshed = {
        "coverage": _coverage_figure(
            coverage,
            cells,
            strata,
            output_dir=staged_figure_dir,
        ),
        "phase_transition": _phase_census_figure(
            support_table,
            output_dir=staged_figure_dir,
        ),
    }
    staged_figures: dict[tuple[str, str], Path] = {}
    for name, stem in FIGURE_STEMS.items():
        for kind in ("png", "pdf"):
            target_path = FIGURE_DIR / f"{stem}.{kind}"
            if name in REFRESHED_FIGURES:
                staged = refreshed[name][kind]
            else:
                source = _verified_parent_artifact(
                    parent,
                    artifact_key=f"figure/{name}/{kind}",
                    path=target_path,
                )
                staged = staged_output_path(staging_root, target_path, repo_root=ROOT)
                staged.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, staged)
            staged_figures[(name, kind)] = staged
            staged_outputs[target_path] = staged

    evidence = deepcopy(parent)
    evidence.update(
        {
            "schema_version": EXTENSION_SCHEMA,
            "status": EXTENSION_STATUS,
            "source_registry": {
                "schema_version": str(registry["schema_version"]),
                "status": str(registry["status"]),
                "sources": sorted(registered),
            },
            "lineages": registry["lineages"],
            "sensitivities": registry["sensitivities"],
            "replay_dependencies": registry.get("replay_dependencies", {}),
            "binary_phase_target_support": support_payload,
            "incremental_parent": {
                "commit": PARENT_COMMIT,
                "path": PARENT_MANIFEST_PATH,
                "bytes": len(parent_bytes),
                "sha256": hashlib.sha256(parent_bytes).hexdigest(),
                "schema_version": PARENT_SCHEMA,
                "status": PARENT_STATUS,
                "extension_scope": [NEW_TABLE_KEY],
                "derived_from_parent_paper_artifacts": [
                    "table/binary_phase_census",
                    "table/conformal_set_diagnostics",
                    "table/exchangeability_cells",
                    "table/exchangeability_strata",
                ],
                "refreshed_figure_scope": sorted(
                    f"figure/{name}/{kind}" for name in REFRESHED_FIGURES for kind in ("png", "pdf")
                ),
                "unmaterialized_unchanged_dvc_sources": list(missing_dvc),
                "protected_stages_run": [],
                "historical_numeric_payload_recomputed": False,
                "all_declared_cells_reported_without_selection": True,
            },
            "audit_thesis": (
                str(parent["audit_thesis"])
                + " A sealed-table join now checks target support in every one of the 200 "
                "phase cells: all 87 below-half-threshold cells have target score maxima "
                "below one minus the threshold, so no prediction set in those cells contains "
                "label one. This exact set-membership statement is not a stratum-prevalence "
                "estimate, a universal LAC law, a transport guarantee, or a mechanism."
            ),
        }
    )
    source_descriptors = deepcopy(cast(dict[str, Any], parent["source_artifacts"]))
    source_descriptors.update(publication_implementation_descriptors(ROOT))
    evidence["source_artifacts"] = source_descriptors

    paper_descriptors = {
        f"table/{name}": staged_artifact_descriptor(
            staged,
            TABLE_TARGETS[name],
            repo_root=ROOT,
        )
        for name, staged in staged_tables.items()
    }
    paper_descriptors.update(
        {
            f"figure/{name}/{kind}": staged_artifact_descriptor(
                staged,
                FIGURE_DIR / f"{FIGURE_STEMS[name]}.{kind}",
                repo_root=ROOT,
            )
            for (name, kind), staged in staged_figures.items()
        }
    )
    if len(paper_descriptors) != 56:
        raise RuntimeError("The extension did not produce exactly 46 tables and 10 figures.")
    evidence["paper_artifacts"] = paper_descriptors
    evidence["claim_ledger"] = materialize_claim_ledger(
        CLAIM_LEDGER_PATH,
        evidence=evidence,
        repo_root=ROOT,
    )
    staged_manifest = staged_output_path(staging_root, EVIDENCE_PATH, repo_root=ROOT)
    atomic_write_strict_json(staged_manifest, evidence)
    return staged_manifest, staged_outputs


def stage_extension(stage_root: Path) -> Path:
    resolved = stage_root.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("Stage-only output must remain inside the repository.") from exc
    if resolved.exists() and any(resolved.iterdir()):
        raise FileExistsError(f"Stage-only output is not empty: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    staged_manifest, _ = _stage_extension(resolved)
    return staged_manifest


def _staged_paths(stage_root: Path) -> tuple[Path, dict[Path, Path]]:
    outputs_root = stage_root.resolve() / "outputs"
    manifest = outputs_root / EVIDENCE_PATH.relative_to(ROOT)
    targets = {
        *TABLE_TARGETS.values(),
        *(
            FIGURE_DIR / f"{stem}.{kind}"
            for stem in FIGURE_STEMS.values()
            for kind in ("png", "pdf")
        ),
    }
    return manifest, {target: outputs_root / target.relative_to(ROOT) for target in targets}


def verify_stages_match(left: Path, right: Path) -> Path:
    left_manifest, left_outputs = _staged_paths(left)
    right_manifest, right_outputs = _staged_paths(right)
    for first, second in (
        (left_manifest, right_manifest),
        *((left_outputs[target], right_outputs[target]) for target in left_outputs),
    ):
        if not first.is_file() or not second.is_file() or first.read_bytes() != second.read_bytes():
            raise RuntimeError(f"Staged extension outputs are not byte-identical: {first}")
    return right_manifest


def promote_staged_extension(stage_root: Path) -> Path:
    staged_manifest, staged_outputs = _staged_paths(stage_root)
    if not staged_manifest.is_file():
        raise FileNotFoundError(f"Staged extension manifest is missing: {staged_manifest}")
    payload = json.loads(staged_manifest.read_text(encoding="utf-8"))
    if (
        payload.get("schema_version") != EXTENSION_SCHEMA
        or payload.get("status") != EXTENSION_STATUS
        or payload.get("incremental_parent", {}).get("sha256") != PARENT_MANIFEST_SHA256
    ):
        raise RuntimeError("The staged extension manifest has an invalid identity.")
    descriptors = payload.get("paper_artifacts")
    if not isinstance(descriptors, Mapping) or len(descriptors) != 56:
        raise RuntimeError("The staged extension manifest has an invalid inventory.")
    by_path = {
        str(descriptor["path"]): descriptor
        for descriptor in descriptors.values()
        if isinstance(descriptor, Mapping)
    }
    for target, staged in staged_outputs.items():
        actual = staged_artifact_descriptor(staged, target, repo_root=ROOT)
        if actual != by_path.get(actual["path"]):
            raise RuntimeError(f"A staged extension artifact drifted: {staged}")
    selected = {target: staged_outputs[target] for target in PROMOTED_TARGETS}
    promote_publication_generation(
        selected,
        staged_manifest=staged_manifest,
        manifest_target=EVIDENCE_PATH,
        repo_root=ROOT,
        transaction_root=stage_root.resolve(),
        preserve_target_permissions=True,
    )
    return EVIDENCE_PATH


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-only", type=Path)
    parser.add_argument("--verify-stages", nargs=2, type=Path, metavar=("LEFT", "RIGHT"))
    parser.add_argument("--promote-from-stage", type=Path)
    args = parser.parse_args(argv)
    selected = sum(
        value is not None
        for value in (args.stage_only, args.verify_stages, args.promote_from_stage)
    )
    if selected != 1:
        parser.error("select exactly one extension mode")
    if args.stage_only is not None:
        output = stage_extension(args.stage_only)
    elif args.verify_stages is not None:
        output = verify_stages_match(*args.verify_stages)
    else:
        output = promote_staged_extension(cast(Path, args.promote_from_stage))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
