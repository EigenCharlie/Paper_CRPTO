"""Contracts for the active four-calibrator P/A/B/C evidence lineage."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import src.ijds_audit.calibrator_sensitivity_evidence as evidence_module
from src.ijds_audit.calibrator_sensitivity_evidence import (
    CalibratorSensitivityEvidence,
    calibrator_method_publication_table,
    calibrator_overall_publication_table,
    calibrator_pairwise_publication_table,
    load_calibrator_sensitivity_evidence,
)
from src.ijds_audit.publication_sources import load_verified_source_registry

pytestmark = pytest.mark.requires_dvc_materialized

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "configs/ijds_active_evidence_sources.yaml"
P = "808827926eff5030b3cb28d2b89a87a0e6210b2e"
A = "ea3e7326afc38ccc1b99b09de30792986640e3c3"
B = "753305e81e27f793acdea80b684b42e7eff2201d"
C = "6552524eae5a22ce66b50689900383d16df1ff13"


@pytest.fixture(scope="module")
def active() -> tuple[
    dict[str, Any],
    dict[str, Path],
    CalibratorSensitivityEvidence,
]:
    payload, registered = load_verified_source_registry(REGISTRY, repo_root=ROOT)
    evidence = load_calibrator_sensitivity_evidence(
        registered,
        payload["sensitivities"]["calibrator_family"],
        repo_root=ROOT,
    )
    return payload, registered, evidence


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_calibrator_lineage_is_exact_annotated_p_a_b_c(
    active: tuple[dict[str, Any], dict[str, Path], CalibratorSensitivityEvidence],
) -> None:
    payload, _, _ = active
    lineage = payload["sensitivities"]["calibrator_family"]
    source = lineage["outcome_free"]
    evaluation = lineage["evaluation"]

    assert source["protocol_commit"] == P
    assert source["artifact_commit"] == A
    assert source["artifact_parent_commit"] == P
    assert evaluation["protocol_commit"] == B
    assert evaluation["artifact_commit"] == C
    assert evaluation["artifact_parent_commit"] == B
    assert len(source["artifact_paths"]) == 8
    assert len(evaluation["artifact_paths"]) == 6
    assert _git("rev-list", "--parents", "-n", "1", A).split() == [A, P]
    assert _git("rev-list", "--parents", "-n", "1", B).split() == [B, A]
    assert _git("rev-list", "--parents", "-n", "1", C).split() == [C, B]
    for tag in (
        source["protocol_tag"],
        source["artifact_tag"],
        evaluation["protocol_tag"],
        evaluation["artifact_tag"],
    ):
        assert _git("cat-file", "-t", f"refs/tags/{tag}") == "tag"

    assert (
        _git(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "--no-renames",
            "-r",
            A,
        ).splitlines()
        == source["artifact_paths"]
    )
    assert (
        _git(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "--no-renames",
            "-r",
            C,
        ).splitlines()
        == evaluation["artifact_paths"]
    )


def test_calibrator_complete_grids_censuses_partitions_and_flags(
    active: tuple[dict[str, Any], dict[str, Path], CalibratorSensitivityEvidence],
) -> None:
    _, _, evidence = active
    frames = evidence.frames
    assert {name: frame.shape for name, frame in frames.items()} == {
        "calibration_fit_diagnostics": (4, 10),
        "recipe_audit": (160, 9),
        "outcome_free_geometry": (960, 32),
        "evaluation": (192, 46),
        "overall": (32, 46),
        "pairwise": (288, 13),
        "platt_v5_reconciliation": (48, 36),
    }

    evaluation = frames["evaluation"]
    assert (
        evaluation["candidate_rows"] == evaluation["resolved_rows"] + evaluation["unresolved_rows"]
    ).all()
    assert (
        evaluation[
            [
                "set_empty_count",
                "set_zero_only_count",
                "set_one_only_count",
                "set_both_count",
            ]
        ].sum(axis=1)
        == evaluation["rows"]
    ).all()
    assert evaluation["coverage_upper_below_nominal"].equals(evaluation["coverage_upper"].lt(0.90))
    assert (evaluation["coverage_lower"] <= evaluation["coverage_resolved"]).all()
    assert (evaluation["coverage_resolved"] <= evaluation["coverage_upper"]).all()

    overall = frames["overall"]
    method_counts = (
        overall.groupby("method", observed=True)["coverage_upper_below_nominal"]
        .sum()
        .astype(int)
        .to_dict()
    )
    assert method_counts == {
        "beta": 8,
        "isotonic": 1,
        "platt": 8,
        "venn_abers": 1,
    }
    assert int(overall["coverage_upper_below_nominal"].sum()) == 18
    assert int((~overall["coverage_upper_below_nominal"]).sum()) == 14

    pairwise = frames["pairwise"]
    assert pairwise["shared_loanwise_completion"].all()
    assert (pairwise["coverage_difference_lower"] <= pairwise["coverage_difference_resolved"]).all()
    assert (pairwise["coverage_difference_resolved"] <= pairwise["coverage_difference_upper"]).all()
    reconciliation = frames["platt_v5_reconciliation"].drop(
        columns=["window_id", "conformal_group"]
    )
    assert np.isfinite(reconciliation.to_numpy()).all()
    assert float(reconciliation.abs().max().max()) == 2.220446049250313e-16


def test_calibrator_receipts_findings_and_publication_tables_are_json_finite(
    active: tuple[dict[str, Any], dict[str, Path], CalibratorSensitivityEvidence],
) -> None:
    _, _, evidence = active
    assert evidence.freeze["protected_stages_run"] == []
    assert evidence.freeze["protected_artifacts_written"] == []
    assert evidence.source_receipt["protected_stages_run"] == []
    assert evidence.summary["protected_stages_run"] == []
    assert evidence.evaluation_receipt["protected_artifacts_written"] == []
    assert evidence.taxonomy["full_panel_assignment_changes"] == 0
    assert evidence.findings["result_state"] == ("uniform_closed_family_shortfall_not_established")
    assert evidence.findings["overall_cells_below_nominal"] == 18
    assert evidence.findings["overall_cells_at_or_above_nominal"] == 14
    assert evidence.findings["overall_cells_below_nominal_by_method"] == {
        "platt": 8,
        "isotonic": 1,
        "beta": 8,
        "venn_abers": 1,
    }

    method = calibrator_method_publication_table(evidence)
    cells = calibrator_overall_publication_table(evidence)
    pairwise = calibrator_pairwise_publication_table(evidence)
    assert method.shape == (4, 10)
    assert cells.shape == (192, 46)
    assert pairwise.shape == (288, 13)
    assert (
        method.loc[method["method"].ne("venn_abers"), "venn_multiprobability_gap_mean"].isna().all()
    )
    assert cells["conformal_group"].nunique() == 6
    for table in (method, cells, pairwise):
        json.dumps(table.to_dict(orient="records"), allow_nan=False)


def test_calibrator_active_source_authorities_are_exact(
    active: tuple[dict[str, Any], dict[str, Path], CalibratorSensitivityEvidence],
) -> None:
    payload, registered, evidence = active
    sources = cast_mapping(payload["sources"])
    phase_a = cast_mapping(evidence.freeze["source_artifacts"])
    phase_b = cast_mapping(evidence.summary["source_artifacts"])
    assert phase_b["active_v5_config"] == sources["v4_config"]
    assert phase_b["active_v5_summary"] == sources["v4_summary"]

    v5_summary = json.loads(registered["v4_summary"].read_text(encoding="utf-8"))
    assert phase_b["active_v5_temporal_coverage"] == v5_summary["artifacts"]["temporal_coverage"]
    raw_audit = json.loads(registered["raw_data_audit"].read_text(encoding="utf-8"))
    raw_authority = {key: raw_audit["raw_source"][key] for key in ("path", "bytes", "sha256")}
    assert phase_a["raw_archive"] == raw_authority
    assert phase_b["raw_archive"] == raw_authority

    v5_freeze_path = ROOT / v5_summary["outcome_free_freeze"]["path"]
    v5_freeze = json.loads(v5_freeze_path.read_text(encoding="utf-8"))
    v4_freeze_path = ROOT / v5_freeze["outcome_free_lineage"]["source_protocol_freeze"]["path"]
    v4_freeze = json.loads(v4_freeze_path.read_text(encoding="utf-8"))
    assert (
        phase_a["active_v4_freeze"] == v5_freeze["outcome_free_lineage"]["source_protocol_freeze"]
    )
    assert (
        phase_a["active_v4_config"]
        == v4_freeze["implementation_provenance"]["source_files"][
            evidence_module._V4_OUTCOME_FREE_CONFIG_PATH
        ]
    )
    for phase_name, authority_section, authority_name in (
        ("scores", "outcome_free_artifacts", "scores"),
        ("residual_recipes", "outcome_free_artifacts", "recipes"),
        ("fit_audit", "outcome_free_artifacts", "fit_audit"),
        ("catboost_model", "model_artifacts", "catboost"),
        ("platt_calibrator", "model_artifacts", "catboost_platt"),
    ):
        assert phase_a[phase_name] == v4_freeze[authority_section][authority_name]
        assert (
            v4_freeze[authority_section][authority_name]
            == v5_freeze[authority_section][authority_name]
        )


@pytest.mark.parametrize(
    ("phase", "name"),
    [
        ("a", "active_v4_config"),
        ("a", "active_v4_freeze"),
        ("a", "scores"),
        ("a", "residual_recipes"),
        ("a", "fit_audit"),
        ("a", "catboost_model"),
        ("a", "platt_calibrator"),
        ("a", "raw_archive"),
        ("b", "active_v5_config"),
        ("b", "active_v5_summary"),
        ("b", "active_v5_temporal_coverage"),
        ("b", "raw_archive"),
    ],
)
def test_calibrator_stale_source_descriptor_fails_closed(
    active: tuple[dict[str, Any], dict[str, Path], CalibratorSensitivityEvidence],
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    name: str,
) -> None:
    _, registered, evidence = active
    freeze = deepcopy(evidence.freeze)
    summary = deepcopy(evidence.summary)
    sources = freeze["source_artifacts"] if phase == "a" else summary["source_artifacts"]
    sources[name]["sha256"] = "0" * 64
    monkeypatch.setattr(
        evidence_module,
        "_descriptor_path",
        lambda raw, *, repo_root, label: (repo_root / raw["path"]).resolve(),
    )
    with pytest.raises(RuntimeError, match="descriptor, route, or hash"):
        evidence_module._require_active_source_authorities(
            freeze=freeze,
            summary=summary,
            registered=registered,
            repo_root=ROOT,
        )


def test_calibrator_stale_source_route_fails_closed(
    active: tuple[dict[str, Any], dict[str, Path], CalibratorSensitivityEvidence],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, registered, evidence = active
    summary = deepcopy(evidence.summary)
    summary["source_artifacts"]["active_v5_config"] = deepcopy(
        summary["source_artifacts"]["active_v5_summary"]
    )
    monkeypatch.setattr(
        evidence_module,
        "_descriptor_path",
        lambda raw, *, repo_root, label: (repo_root / raw["path"]).resolve(),
    )
    with pytest.raises(RuntimeError, match="descriptor, route, or hash"):
        evidence_module._require_active_source_authorities(
            freeze=evidence.freeze,
            summary=summary,
            registered=registered,
            repo_root=ROOT,
        )


def test_calibrator_derived_findings_are_complete_and_exact(
    active: tuple[dict[str, Any], dict[str, Path], CalibratorSensitivityEvidence],
) -> None:
    _, _, evidence = active
    assert evidence.findings["overall_method_summaries"] == {
        "platt": {
            "upper_below_nominal": 8,
            "coverage_lower_min": 0.8424845445620738,
            "coverage_upper_max": 0.8825970442304121,
            "coverage_resolved_min": 0.8658549288130389,
            "coverage_resolved_max": 0.879165821487114,
            "average_set_size_min": 1.128127570378625,
            "average_set_size_max": 1.1839422643211548,
        },
        "isotonic": {
            "upper_below_nominal": 1,
            "coverage_lower_min": 0.8703069861232721,
            "coverage_upper_max": 0.9273448486295737,
            "coverage_resolved_min": 0.8927864610459029,
            "coverage_resolved_max": 0.9249398323529251,
            "average_set_size_min": 1.1995171004802463,
            "average_set_size_max": 1.3857942635782323,
        },
        "beta": {
            "upper_below_nominal": 8,
            "coverage_lower_min": 0.8424845445620738,
            "coverage_upper_max": 0.8825970442304121,
            "coverage_resolved_min": 0.8658549288130389,
            "coverage_resolved_max": 0.879165821487114,
            "average_set_size_min": 1.128127570378625,
            "average_set_size_max": 1.1839422643211548,
        },
        "venn_abers": {
            "upper_below_nominal": 1,
            "coverage_lower_min": 0.8699328716601661,
            "coverage_upper_max": 0.9226087187242962,
            "coverage_resolved_min": 0.8924547851782004,
            "coverage_resolved_max": 0.9200469280235956,
            "average_set_size_min": 1.1980896282735016,
            "average_set_size_max": 1.3595531852795246,
        },
    }
    assert evidence.findings["platt_beta_aggregate_equality_cells"] == 48
    assert evidence.findings["alternative_overall_set_geometry_census"] == {
        "isotonic": {
            "rows": 8,
            "zero_empty_set_cells": 8,
            "two_label_count_greater_than_platt_cells": 8,
        },
        "venn_abers": {
            "rows": 8,
            "zero_empty_set_cells": 8,
            "two_label_count_greater_than_platt_cells": 8,
        },
    }
    assert evidence.findings["pairwise_overall_summaries"] == {
        "platt_minus_isotonic": {
            "rows": 8,
            "lower_min": -0.0550187057231553,
            "upper_max": -0.02606861418451007,
            "all_bounds_strictly_positive": False,
        },
        "platt_minus_beta": {
            "rows": 8,
            "lower_min": 0.0,
            "upper_max": 0.0,
            "all_bounds_strictly_positive": False,
        },
        "platt_minus_venn_abers": {
            "rows": 8,
            "lower_min": -0.049587412772957626,
            "upper_max": -0.025747565602695748,
            "all_bounds_strictly_positive": False,
        },
        "isotonic_minus_platt": {
            "rows": 8,
            "lower_min": 0.02606861418451007,
            "upper_max": 0.0550187057231553,
            "all_bounds_strictly_positive": True,
        },
        "isotonic_minus_beta": {
            "rows": 8,
            "lower_min": 0.02606861418451007,
            "upper_max": 0.0550187057231553,
            "all_bounds_strictly_positive": True,
        },
        "isotonic_minus_venn_abers": {
            "rows": 8,
            "lower_min": 0.00032104858181432246,
            "upper_max": 0.0054312929501976704,
            "all_bounds_strictly_positive": True,
        },
        "beta_minus_platt": {
            "rows": 8,
            "lower_min": 0.0,
            "upper_max": 0.0,
            "all_bounds_strictly_positive": False,
        },
        "beta_minus_isotonic": {
            "rows": 8,
            "lower_min": -0.0550187057231553,
            "upper_max": -0.02606861418451007,
            "all_bounds_strictly_positive": False,
        },
        "beta_minus_venn_abers": {
            "rows": 8,
            "lower_min": -0.049587412772957626,
            "upper_max": -0.025747565602695748,
            "all_bounds_strictly_positive": False,
        },
        "venn_abers_minus_platt": {
            "rows": 8,
            "lower_min": 0.025747565602695748,
            "upper_max": 0.049587412772957626,
            "all_bounds_strictly_positive": True,
        },
        "venn_abers_minus_isotonic": {
            "rows": 8,
            "lower_min": -0.0054312929501976704,
            "upper_max": -0.00032104858181432246,
            "all_bounds_strictly_positive": False,
        },
        "venn_abers_minus_beta": {
            "rows": 8,
            "lower_min": 0.025747565602695748,
            "upper_max": 0.049587412772957626,
            "all_bounds_strictly_positive": True,
        },
    }
    assert evidence.findings["platt_beta_zero_bound_cells"] == 48


@pytest.mark.parametrize(
    "corruption",
    [
        "method_grid",
        "strict_positive",
        "platt_beta",
        "platt_beta_geometry",
        "alternative_geometry",
    ],
)
def test_calibrator_derived_findings_corruption_fails_closed(
    active: tuple[dict[str, Any], dict[str, Path], CalibratorSensitivityEvidence],
    corruption: str,
) -> None:
    _, _, evidence = active
    evaluation = evidence.frames["evaluation"].copy()
    overall = evidence.frames["overall"].copy()
    pairwise = evidence.frames["pairwise"].copy()
    expected_error = ""
    if corruption == "method_grid":
        overall = overall.iloc[1:].copy()
        expected_error = "method-level findings grid"
    elif corruption == "strict_positive":
        row = pairwise.index[
            pairwise["method_a"].eq("isotonic")
            & pairwise["method_b"].eq("venn_abers")
            & pairwise["conformal_group"].eq(-1)
        ][0]
        pairwise.loc[row, "coverage_difference_lower"] = 0.0
        expected_error = "strict-positive pairwise boundary"
    elif corruption == "platt_beta":
        row = pairwise.index[pairwise["method_a"].eq("platt") & pairwise["method_b"].eq("beta")][0]
        pairwise.loc[
            row,
            [
                "coverage_difference_lower",
                "coverage_difference_resolved",
                "coverage_difference_upper",
            ],
        ] = 1.0e-6
        expected_error = "Platt-minus-beta"
    elif corruption == "platt_beta_geometry":
        row = evaluation.index[evaluation["method"].eq("beta")][0]
        evaluation.loc[row, "set_both_count"] += 1
        expected_error = "Platt/Beta aggregate set geometry"
    else:
        row = overall.index[overall["method"].eq("isotonic")][0]
        overall.loc[row, "set_empty_count"] = 1
        expected_error = "alternative overall set-geometry co-movement"
    with pytest.raises(RuntimeError, match=expected_error):
        evidence_module._validate_boundaries(
            freeze=evidence.freeze,
            summary=evidence.summary,
            evaluation=evaluation,
            overall=overall,
            pairwise=pairwise,
        )


def test_calibrator_loader_rejects_missing_registration(
    active: tuple[dict[str, Any], dict[str, Path], CalibratorSensitivityEvidence],
) -> None:
    payload, registered, _ = active
    incomplete = dict(registered)
    incomplete.pop("calibrator_sensitivity_pairwise")
    with pytest.raises(KeyError, match="registry keys are missing"):
        load_calibrator_sensitivity_evidence(
            incomplete,
            payload["sensitivities"]["calibrator_family"],
            repo_root=ROOT,
        )


@pytest.mark.parametrize("corruption", ["partition", "flag"])
def test_calibrator_cell_corruption_fails_closed(
    active: tuple[dict[str, Any], dict[str, Path], CalibratorSensitivityEvidence],
    corruption: str,
) -> None:
    _, _, evidence = active
    changed = evidence.frames["evaluation"].copy()
    if corruption == "partition":
        changed.loc[0, "candidate_rows"] += 1
    else:
        changed.loc[0, "coverage_upper_below_nominal"] = False
    with pytest.raises(RuntimeError, match="census, bounds, or nominal flags"):
        evidence_module._validate_evaluation(
            changed,
            evidence.frames["overall"],
            evidence.frames["outcome_free_geometry"],
            evidence.frames["recipe_audit"],
            summary=evidence.summary,
        )


def test_calibrator_pairwise_and_reconciliation_corruption_fail_closed(
    active: tuple[dict[str, Any], dict[str, Path], CalibratorSensitivityEvidence],
) -> None:
    _, _, evidence = active
    pairwise = evidence.frames["pairwise"].copy()
    pairwise.loc[0, "shared_loanwise_completion"] = False
    with pytest.raises(RuntimeError, match="pairwise grid, census, or sharp bounds"):
        evidence_module._validate_pairwise(pairwise, evidence.frames["evaluation"])

    reconciliation = evidence.frames["platt_v5_reconciliation"].copy()
    reconciliation.loc[0, "coverage_upper_difference"] = 1.0e-6
    with pytest.raises(RuntimeError, match="reconciliation gate changed"):
        evidence_module._validate_reconciliation(
            reconciliation,
            summary=evidence.summary,
        )


def test_calibrator_registered_hash_routes_are_complete(
    active: tuple[dict[str, Any], dict[str, Path], CalibratorSensitivityEvidence],
) -> None:
    payload, registered, _ = active
    sources = cast_mapping(payload["sources"])
    names = {name for name in sources if name.startswith("calibrator_sensitivity_")}
    assert names == set(evidence_module._REGISTERED_PATHS)
    assert all(registered[name].is_file() for name in names)
    for name in names:
        descriptor = sources[name]
        assert isinstance(descriptor, Mapping)
        assert set(descriptor) == {"path", "bytes", "sha256"}


def cast_mapping(value: Any) -> Mapping[str, Any]:
    """Narrow one fixture value without weakening production validation."""
    assert isinstance(value, Mapping)
    return value
