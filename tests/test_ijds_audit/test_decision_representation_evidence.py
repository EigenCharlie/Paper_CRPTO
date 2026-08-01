"""Focused contracts for the decision-representation evidence loader."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.ijds_audit import decision_representation_evidence as module
from src.ijds_audit.decision_representation_evidence import (
    DecisionRepresentationEvidence,
    load_decision_representation_evidence,
    score_equivalence_publication_table,
    set_native_direction_publication_table,
)

ROOT = Path(__file__).resolve().parents[2]


def _registered() -> dict[str, Path]:
    return {name: ROOT / relative for name, relative in module._REGISTERED_PATHS.items()}


def _identities() -> dict[str, Any]:
    return {
        "score_equivalence_complete_hull": {
            "run_tag": module._SCORE_RUN_TAG,
            "protocol_tag": module._SCORE_PROTOCOL_TAG,
            "protocol_commit": module._SCORE_PROTOCOL_COMMIT,
            "scientific_uv_lock_sha256": module._UV_LOCK_SHA256,
            "paper_role": (
                "complete_outcome_free_complete_candidate_hull_score_equivalence_census"
            ),
            "dvc_tracked": False,
            "artifact_tag": module._SCORE_ARTIFACT_TAG,
            "artifact_commit": module._SCORE_ARTIFACT_COMMIT,
            "artifact_parent_commit": module._SCORE_PROTOCOL_COMMIT,
            "artifact_transport": module._TRANSPORT,
            "artifact_paths": list(module._SCORE_ARTIFACT_PATHS),
        },
        "set_native_binary_robust_counterpart": {
            "outcome_free": {
                "run_tag": module._SET_PHASE_A_RUN_TAG,
                "protocol_tag": module._SET_P1_TAG,
                "protocol_commit": module._SET_P1_COMMIT,
                "scientific_uv_lock_sha256": module._UV_LOCK_SHA256,
                "paper_role": "outcome_free_complete_set_native_frontier_and_solver_audit",
                "dvc_tracked": False,
                "artifact_tag": module._SET_A1_TAG,
                "artifact_commit": module._SET_A1_COMMIT,
                "artifact_parent_commit": module._SET_P1_COMMIT,
                "artifact_transport": module._TRANSPORT,
                "artifact_paths": list(module._SET_PHASE_A_PATHS),
            },
            "evaluation": {
                "run_tag": module._SET_PHASE_B_RUN_TAG,
                "protocol_tag": module._SET_P2_TAG,
                "protocol_commit": module._SET_P2_COMMIT,
                "scientific_uv_lock_sha256": module._UV_LOCK_SHA256,
                "paper_role": "complete_retrospective_set_native_robust_minus_embedding_census",
                "dvc_tracked": False,
                "artifact_tag": module._SET_B1_TAG,
                "artifact_commit": module._SET_B1_COMMIT,
                "artifact_parent_commit": module._SET_P2_COMMIT,
                "artifact_transport": module._TRANSPORT,
                "artifact_paths": list(module._SET_PHASE_B_PATHS),
            },
        },
    }


@pytest.fixture(scope="module")
def evidence() -> DecisionRepresentationEvidence:
    return load_decision_representation_evidence(
        _registered(),
        _identities(),
        repo_root=ROOT,
    )


def test_active_registry_exposes_the_exact_loader_identities() -> None:
    registry = yaml.safe_load(
        (ROOT / "configs/ijds_active_evidence_sources.yaml").read_text(encoding="utf-8")
    )
    diagnostics = registry["lineages"]["diagnostics"]
    assert {
        "score_equivalence_complete_hull": diagnostics["score_equivalence_complete_hull"],
        "set_native_binary_robust_counterpart": diagnostics["set_native_binary_robust_counterpart"],
    } == _identities()


def test_complete_loader_verifies_both_lineages(
    evidence: DecisionRepresentationEvidence,
) -> None:
    assert evidence.score_equivalence.findings == {
        "complete_hulls": 26,
        "v1d_cells": 5200,
        "v1d_identity_equivalent_cells": 1872,
        "v1d_substantive_without_certificate": 3328,
        "calibrator_cells_without_certificate": 6240,
        "smallest_v1d_failing_max_coordinate_error": pytest.approx(0.04526086783713035),
        "smallest_calibrator_failing_max_coordinate_error": pytest.approx(0.0008133501900316614),
        "relation_tolerance": pytest.approx(1.01e-10),
        "outcome_columns_passed": [],
        "optimization_run": False,
    }
    assert evidence.set_native.findings["phase_a_cells"] == 1248
    assert evidence.set_native.findings["primary_cells"] == 720
    assert evidence.set_native.findings["taxonomy_rows"] == 208
    assert evidence.set_native.findings["solver_audit_rows"] == 1248
    assert evidence.set_native.findings["monthly_contrasts"] == 18000
    assert evidence.set_native.findings["pooled_contrasts"] == 1200
    assert evidence.set_native.findings["sign_order"] == [
        "positive",
        "negative",
        "includes_zero",
    ]
    assert evidence.set_native.findings["joint_coverage_guarantee_established"] is False
    assert "joint_coverage_for_cartesian_product" not in evidence.set_native.findings
    assert "allocations" not in evidence.set_native.__dataclass_fields__


def test_score_equivalence_publication_table_is_five_disjoint_rows(
    evidence: DecisionRepresentationEvidence,
) -> None:
    table = score_equivalence_publication_table(evidence.score_equivalence)
    assert tuple(table.columns) == (
        "family",
        "cell_group",
        "cells",
        "equivalent_cells",
        "without_complete_hull_certificate",
    )
    assert list(
        table[["cells", "equivalent_cells", "without_complete_hull_certificate"]].itertuples(
            index=False, name=None
        )
    ) == [
        (1040, 1040, 0),
        (832, 832, 0),
        (3328, 0, 3328),
        (1248, 0, 1248),
        (4992, 0, 4992),
    ]
    assert int(table.loc[table["family"].eq("v1d_embedding"), "cells"].sum()) == 5200
    assert int(table.loc[table["family"].eq("closed_calibrator_q_gamma"), "cells"].sum()) == 6240


def test_set_native_publication_table_has_75_complete_sign_partitions(
    evidence: DecisionRepresentationEvidence,
) -> None:
    table = set_native_direction_publication_table(evidence.set_native)
    assert len(table) == 75
    assert not table.duplicated(["theta", "gamma", "metric"]).any()
    assert set(table["metric"]) == {
        "standardized_payoff",
        "funded_default",
        "funded_binary_miscoverage",
    }
    assert table["monthly_cells"].eq(720).all()
    assert table["pooled_cells"].eq(48).all()
    assert (
        table[["monthly_positive", "monthly_negative", "monthly_includes_zero"]]
        .sum(axis=1)
        .eq(720)
        .all()
    )
    assert (
        table[["pooled_positive", "pooled_negative", "pooled_includes_zero"]]
        .sum(axis=1)
        .eq(48)
        .all()
    )
    assert tuple(
        table.loc[
            table["metric"].eq("standardized_payoff"),
            ["monthly_positive", "monthly_negative", "monthly_includes_zero"],
        ].sum()
    ) == (5840, 9853, 2307)
    assert tuple(
        table.loc[
            table["metric"].eq("funded_default"),
            ["pooled_positive", "pooled_negative", "pooled_includes_zero"],
        ].sum()
    ) == (1196, 0, 4)


def test_score_validator_rejects_equivalence_outside_identity_union(
    evidence: DecisionRepresentationEvidence,
) -> None:
    changed = evidence.score_equivalence.v1d.copy()
    row = changed.index[changed["theta"].gt(0.0) & changed["gamma"].gt(0.0)][0]
    changed.loc[row, "equivalent_on_complete_budget_hull"] = True
    with pytest.raises(RuntimeError, match="identity union"):
        module._validate_score_frames(
            evidence.score_equivalence.hulls,
            changed,
            evidence.score_equivalence.calibrators,
            evidence.score_equivalence.controls,
            summary=evidence.score_equivalence.summary,
        )


@pytest.mark.parametrize(
    ("column", "message"),
    [
        ("payoff_direction_sign_robust", "sign partition"),
        ("realized_payoff_rate_identification_width", "sharp-bound reconciliation"),
    ],
)
def test_contrast_validator_rejects_sign_or_width_drift(
    evidence: DecisionRepresentationEvidence,
    column: str,
    message: str,
) -> None:
    changed = evidence.set_native.monthly_contrasts.copy()
    if column.endswith("sign_robust"):
        changed.loc[0, column] = not bool(changed.loc[0, column])
    else:
        changed.loc[0, column] = float(changed.loc[0, column]) + 0.01
    with pytest.raises(RuntimeError, match=message):
        module._validate_contrast_frame(changed, pooled=False)


def test_registry_identity_drift_fails_before_artifact_loading() -> None:
    identities: Mapping[str, Any] = _identities()
    changed = {
        **identities,
        "score_equivalence_complete_hull": {
            **identities["score_equivalence_complete_hull"],
            "paper_role": "winner_selection",
        },
    }
    with pytest.raises(RuntimeError, match="registry identity"):
        module._require_lineages(changed, repo_root=ROOT)
