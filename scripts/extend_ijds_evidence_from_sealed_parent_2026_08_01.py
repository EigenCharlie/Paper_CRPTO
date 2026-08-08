"""Extend the sealed 2026-07-31 IJDS evidence generation with Git-native results.

This builder is intentionally narrower than the full publication rebuild.  It
verifies the exact parent manifest and registry at their pinned Git commit,
requires every unavailable source to remain an unchanged DVC-managed source,
recomputes the two new Git-native result payloads, and promotes one
transactional 45-table generation.  No protected scientific stage is run.
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
from tempfile import TemporaryDirectory
from typing import Any, cast

import pandas as pd

from scripts.build_ijds_binary_geometry_frontier_v4_evidence import (
    BINARY_PHASE_CENSUS_SOURCE_KEYS,
    DECISION_REPRESENTATION_SOURCE_KEYS,
    EVIDENCE_PATH,
    FIGURE_DIR,
    FIGURE_STEMS,
    SOURCE_REGISTRY_PATH,
    TABLE_TARGETS,
)
from src.ijds_audit.binary_phase_census_evidence import (
    binary_phase_census_publication_table,
    load_binary_phase_census_evidence,
)
from src.ijds_audit.claim_ledger import materialize_claim_ledger
from src.ijds_audit.decision_representation_evidence import (
    dual_coefficient_publication_table,
    load_decision_representation_evidence,
)
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
PARENT_COMMIT = "6e9086ed57492325787498d912b3f5f3e03458bf"
PARENT_MANIFEST_PATH = "reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json"
PARENT_REGISTRY_PATH = "configs/ijds_active_evidence_sources.yaml"
PARENT_MANIFEST_BYTES = 3_500_642
PARENT_MANIFEST_SHA256 = "02122d92270425540fba930de574e3b8abc940cc667b3a34f32f5504e21bb5e4"
PARENT_SCHEMA = "2026-07-31.1"
PARENT_STATUS = "active_ijds_v5_endpoint_reason_audited_paper_facing_evidence"
EXTENSION_SCHEMA = "2026-08-01.1"
EXTENSION_STATUS = "active_ijds_v5_phase_and_dual_set_native_paper_facing_evidence"
NEW_TABLE_KEYS = frozenset({"binary_phase_census", "dual_coefficient_binary_set_native"})
PROMOTED_EXTENSION_TARGETS = frozenset(TABLE_TARGETS[name] for name in NEW_TABLE_KEYS)
EDITORIAL_FIGURE_REFRESH_ARTIFACTS = frozenset(
    {
        "figure/phase_transition/png",
        "figure/phase_transition/pdf",
        "figure/development_envelopes/png",
        "figure/development_envelopes/pdf",
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
    manifest_bytes = _git_blob(PARENT_COMMIT, PARENT_MANIFEST_PATH)
    if (
        len(manifest_bytes) != PARENT_MANIFEST_BYTES
        or hashlib.sha256(manifest_bytes).hexdigest() != PARENT_MANIFEST_SHA256
    ):
        raise RuntimeError("The pinned parent evidence manifest no longer matches its seal.")
    manifest = json.loads(manifest_bytes)
    if (
        manifest.get("schema_version") != PARENT_SCHEMA
        or manifest.get("status") != PARENT_STATUS
        or len(manifest.get("paper_artifacts", {})) != 53
    ):
        raise RuntimeError("The pinned parent manifest has an unexpected contract.")
    return manifest_bytes, cast(dict[str, Any], manifest)


def _dual_payload(
    decision: Any,
    identity: Mapping[str, Any],
    table: pd.DataFrame,
) -> dict[str, Any]:
    return {
        "scope": (
            "complete_outcome_free_dual_set_native_risk_and_maximin_payoff_"
            "certificate_census_over_all_frozen_primary_catboost_platt_menus"
        ),
        "run_tag": decision.summary["run_tag"],
        "protocol": dict(decision.summary["protocol"]),
        "artifact_tag": identity["artifact_tag"],
        "artifact_commit": identity["artifact_commit"],
        "complete_certificate_census_verified": True,
        **dict(decision.findings),
        "role_rows": table.to_dict(orient="records"),
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
    }


def _phase_payload(phase: Any, identity: Mapping[str, Any], table: pd.DataFrame) -> dict[str, Any]:
    return {
        "scope": "five_learners_by_eight_windows_by_five_frozen_score_strata",
        "run_tag": phase.summary["run_tag"],
        "protocol_tag": phase.summary["protocol_tag"],
        "protocol_commit": phase.summary["protocol_commit"],
        "artifact_tag": identity["artifact_tag"],
        "artifact_commit": identity["artifact_commit"],
        "complete_census_verified": True,
        **dict(phase.findings),
        "rows": table.to_dict(orient="records"),
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
    }


def _stage_extension(staging_root: Path) -> tuple[Path, dict[Path, Path]]:
    parent_bytes, parent = _load_pinned_parent()
    registry, registered, missing_dvc = load_verified_or_sealed_source_registry(
        SOURCE_REGISTRY_PATH,
        repo_root=ROOT,
        sealed_parent_commit=PARENT_COMMIT,
        sealed_parent_registry_path=PARENT_REGISTRY_PATH,
    )
    diagnostics = cast(dict[str, Any], registry["lineages"])["diagnostics"]
    identities = {
        name: cast(dict[str, Any], diagnostics[name])
        for name in (
            "score_equivalence_complete_hull",
            "set_native_binary_robust_counterpart",
            "dual_coefficient_binary_set_native",
        )
    }
    decision = load_decision_representation_evidence(registered, identities, repo_root=ROOT)
    dual_table = dual_coefficient_publication_table(decision.dual_coefficient)
    phase_identity = cast(dict[str, Any], diagnostics["binary_phase_census"])
    phase = load_binary_phase_census_evidence(registered, phase_identity, repo_root=ROOT)
    phase_table = binary_phase_census_publication_table(phase)

    staged_outputs: dict[Path, Path] = {}
    table_paths: dict[str, Path] = {}
    for name, target in TABLE_TARGETS.items():
        staged = staged_output_path(staging_root, target, repo_root=ROOT)
        if name == "binary_phase_census":
            atomic_write_text(staged, phase_table.to_csv(index=False, lineterminator="\n"))
        elif name == "dual_coefficient_binary_set_native":
            atomic_write_text(staged, dual_table.to_csv(index=False, lineterminator="\n"))
        else:
            if not target.is_file():
                raise FileNotFoundError(f"Sealed parent publication table is absent: {target}")
            shutil.copy2(target, staged)
        table_paths[name] = staged
        staged_outputs[target] = staged

    figure_paths: dict[tuple[str, str], Path] = {}
    for name, stem in FIGURE_STEMS.items():
        for kind in ("png", "pdf"):
            target = FIGURE_DIR / f"{stem}.{kind}"
            if not target.is_file():
                raise FileNotFoundError(f"Sealed parent publication figure is absent: {target}")
            staged = staged_output_path(staging_root, target, repo_root=ROOT)
            shutil.copy2(target, staged)
            figure_paths[(name, kind)] = staged
            staged_outputs[target] = staged

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
            "binary_phase_census": _phase_payload(phase, phase_identity, phase_table),
            "dual_coefficient_binary_set_native": _dual_payload(
                decision.dual_coefficient,
                identities["dual_coefficient_binary_set_native"],
                dual_table,
            ),
            "incremental_parent": {
                "commit": PARENT_COMMIT,
                "path": PARENT_MANIFEST_PATH,
                "bytes": len(parent_bytes),
                "sha256": hashlib.sha256(parent_bytes).hexdigest(),
                "schema_version": PARENT_SCHEMA,
                "status": PARENT_STATUS,
                "extension_scope": [
                    "binary_phase_census",
                    "dual_coefficient_binary_set_native",
                ],
                "editorial_figure_refresh_scope": sorted(EDITORIAL_FIGURE_REFRESH_ARTIFACTS),
                "editorial_figure_refresh_reason": (
                    "label-only P2 clarification: the phase figure is identified as a "
                    "post-inspection illustration and the envelope figure uses a contains-zero "
                    "glyph; their source tables and numerical payloads are unchanged"
                ),
                "unmaterialized_unchanged_dvc_sources": list(missing_dvc),
                "protected_stages_run": [],
                "historical_numeric_payload_recomputed": False,
            },
            "audit_thesis": (
                str(parent["audit_thesis"])
                + " A clean calibration-only census reconciles exact binary threshold "
                "geometry in all 200 learner-window-stratum cells; it supplies no target, "
                "transport, or validity claim. A conditional dual-coefficient theorem and "
                "208 outcome-free menu certificates show that the maximin full optimal face "
                "collapses to singleton-zero support over cap [0,1]; this is decision algebra, "
                "not true zero risk, joint conformal validity, outcome dominance, or a policy."
            ),
        }
    )

    source_descriptors = deepcopy(cast(dict[str, Any], parent["source_artifacts"]))
    source_descriptors.update(publication_implementation_descriptors(ROOT))
    for name in DECISION_REPRESENTATION_SOURCE_KEYS:
        source_descriptors[f"decision_representation/{name}"] = relative_artifact_descriptor(
            registered[name], repo_root=ROOT
        )
    for name in BINARY_PHASE_CENSUS_SOURCE_KEYS:
        source_descriptors[f"binary_phase_census/{name}"] = relative_artifact_descriptor(
            registered[name], repo_root=ROOT
        )
    evidence["source_artifacts"] = source_descriptors

    paper_descriptors = {
        f"table/{name}": staged_artifact_descriptor(staged, TABLE_TARGETS[name], repo_root=ROOT)
        for name, staged in table_paths.items()
    }
    paper_descriptors.update(
        {
            f"figure/{name}/{kind}": staged_artifact_descriptor(
                staged,
                FIGURE_DIR / f"{FIGURE_STEMS[name]}.{kind}",
                repo_root=ROOT,
            )
            for (name, kind), staged in figure_paths.items()
        }
    )
    if len(paper_descriptors) != 55:
        raise RuntimeError("The extension did not produce exactly 45 tables and 10 figures.")
    evidence["paper_artifacts"] = paper_descriptors
    evidence["claim_ledger"] = materialize_claim_ledger(
        CLAIM_LEDGER_PATH, evidence=evidence, repo_root=ROOT
    )

    staged_manifest = staged_output_path(staging_root, EVIDENCE_PATH, repo_root=ROOT)
    atomic_write_strict_json(staged_manifest, evidence)
    return staged_manifest, staged_outputs


def build_extension(*, check: bool = False) -> Path:
    """Build and promote the sealed-parent extension, or compare it bytewise."""
    parent = ROOT / "reports/crpto"
    parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".ijds-sealed-extension-", dir=parent) as temporary:
        staging_root = Path(temporary)
        staged_manifest, staged_outputs = _stage_extension(staging_root)
        if check:
            if (
                not EVIDENCE_PATH.is_file()
                or staged_manifest.read_bytes() != EVIDENCE_PATH.read_bytes()
            ):
                raise RuntimeError("Canonical evidence differs from the sealed-parent extension.")
            for target, staged in staged_outputs.items():
                if not target.is_file() or staged.read_bytes() != target.read_bytes():
                    raise RuntimeError(f"Canonical paper artifact differs: {target}")
            return EVIDENCE_PATH
        # Stage and compare the complete inherited publication inventory, but
        # promote only the two additive tables. Re-promoting byte-identical
        # parent tables and figures would needlessly change their mtimes and
        # make already-current PDFs fail the freshness audit.
        promoted_outputs = {
            target: staged
            for target, staged in staged_outputs.items()
            if target in PROMOTED_EXTENSION_TARGETS
        }
        if set(promoted_outputs) != PROMOTED_EXTENSION_TARGETS:
            raise RuntimeError("The additive promotion target set is incomplete.")
        promote_publication_generation(
            promoted_outputs,
            staged_manifest=staged_manifest,
            manifest_target=EVIDENCE_PATH,
            repo_root=ROOT,
            transaction_root=staging_root,
            preserve_target_permissions=True,
        )
    return EVIDENCE_PATH


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Require byte-identical canonical output."
    )
    args = parser.parse_args(argv)
    print(build_extension(check=args.check))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
