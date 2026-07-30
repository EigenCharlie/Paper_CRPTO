from __future__ import annotations

import copy
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.experiments import run_ijds_set_preserving_embedding_sensitivity_v1c as runner
from src.ijds_challengers import set_preserving_embedding_v1c as science
from src.ijds_challengers.set_preserving_embedding import (
    CONTRAST_GAMMA,
    CONTRAST_THETA,
    SetPreservingFrontierBuild,
    policy_label,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/experiments/ijds_set_preserving_embedding_sensitivity_2026-07-29_v1c.yaml"


def _git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "v1c@example.invalid")
    _git(repo, "config", "user.name", "V1c Test")
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "base.txt")
    _git(repo, "commit", "-m", "P")
    return repo


def test_config_is_explicitly_retrospective_git_native_and_compact() -> None:
    config = runner.load_v1c_config(CONFIG)
    context = config["inspection_context"]
    if (
        context["classification"] != "retrospective_post_inspection_recovery"
        or context["replay_clean"] is not False
        or context["confirmatory"] is not False
        or context["v1a_is_evidence"] is not False
        or context["phase_a_rerun"] is not False
    ):
        pytest.fail(f"V1c chronology boundary drifted: {context}.")
    transport = config["git_transport"]
    if transport["dvc_required"] is not False:
        pytest.fail("V1c unexpectedly reintroduced DVC transport.")
    if len(transport["protocol_to_source_paths"]) != 11:
        pytest.fail("V1c does not reanchor exactly eleven V1a files.")
    if len(transport["source_to_evaluation_paths"]) != 9:
        pytest.fail("V1c does not retain the exact nine-file compact output.")
    if any(
        "joined_primary_funded_allocations" in path
        for path in transport["source_to_evaluation_paths"]
    ):
        pytest.fail("V1c unexpectedly persists the full joined row-level table.")
    stop = context["superseded_operational_stop"]
    if stop["contemporaneous_git_evidence"] is not False:
        pytest.fail("The reconstructed stop note is mislabeled as contemporaneous Git evidence.")


def test_scientific_sections_reconcile_exactly_to_original_v1a_git_blob() -> None:
    config = runner.load_v1c_config(CONFIG)
    original = config["original_v1a"]
    payload = runner.yaml.safe_load(
        runner._git_blob_bytes(ROOT, original["protocol_commit"], original["config"]["path"])
    )
    runner._require_scientific_reconciliation(config, payload)
    mutated = copy.deepcopy(config)
    mutated["frontier"]["normalized_score"]["minimum_score_range"] = 0.5
    with pytest.raises(RuntimeError, match="frontier"):
        runner._require_scientific_reconciliation(mutated, payload)
    extra_census = copy.deepcopy(config)
    extra_census["expected_census"]["undeclared"] = 1
    with pytest.raises(RuntimeError, match="shared expected census"):
        runner._require_scientific_reconciliation(extra_census, payload)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        (
            'solver_allocated_capital_renormalization: "forbidden"',
            'solver_allocated_capital_renormalization: "allowed"',
            "fixed common-capital",
        ),
        (
            "replay_clean: false",
            "replay_clean: true",
            "chronology",
        ),
        (
            "dvc_required: false",
            "dvc_required: true",
            "Git-native",
        ),
    ],
)
def test_config_rejects_scientific_or_chronology_drift(
    tmp_path: Path, old: str, new: str, message: str
) -> None:
    mutated = CONFIG.read_text(encoding="utf-8").replace(old, new, 1)
    path = tmp_path / "mutated.yaml"
    path.write_text(mutated, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        runner.load_v1c_config(path)


@pytest.mark.parametrize(
    "path",
    ["../escape.json", "/absolute/file.json", r"C:\absolute\file.json", "a\\b.json"],
)
def test_paths_reject_traversal_absolute_and_noncanonical_values(path: str) -> None:
    with pytest.raises(ValueError, match="repository-relative POSIX"):
        runner._validated_relative_path(path, label="test")


def test_serialized_receipts_reject_absolute_path_leaks() -> None:
    with pytest.raises(RuntimeError, match="absolute path"):
        runner._reject_absolute_serialized_paths(
            {"safe": {"path": "data/raw/archive.csv"}, "leak": r"C:\secret\archive.csv"}
        )
    runner._reject_absolute_serialized_paths({"safe": {"path": "data/raw/archive.csv"}})


def test_protected_source_root_must_be_distinct_from_execution_checkout() -> None:
    config = runner.load_v1c_config(CONFIG)
    with pytest.raises(RuntimeError, match="distinct"):
        runner._resolve_protected_raw(
            config,
            protected_read_root=ROOT,
            repo_root=ROOT,
        )


def test_tag_authority_accepts_only_annotated_tags(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    _git(repo, "tag", "lightweight")
    with pytest.raises(RuntimeError, match="annotated"):
        runner._tag_authority(repo, "lightweight")
    _git(repo, "tag", "-a", "annotated", "-m", "authority")
    authority = runner._tag_authority(repo, "annotated")
    if authority["commit"] != _git(repo, "rev-parse", "HEAD"):
        pytest.fail("Annotated tag did not peel to HEAD.")
    if authority["tag_object"] == authority["commit"]:
        pytest.fail("Annotated tag object collapsed to its commit.")


def test_direct_child_exact_diff_and_parent_absence_contract(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    parent = _git(repo, "rev-parse", "HEAD")
    for name, content in (("a.bin", b"a"), ("nested/b.bin", b"b")):
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    _git(repo, "add", "a.bin", "nested/b.bin")
    _git(repo, "commit", "-m", "A")
    child = _git(repo, "rev-parse", "HEAD")
    runner._require_exact_addition_commit(
        repo,
        child=child,
        parent=parent,
        expected_paths=("a.bin", "nested/b.bin"),
    )
    with pytest.raises(RuntimeError, match="exactly"):
        runner._require_exact_addition_commit(
            repo,
            child=child,
            parent=parent,
            expected_paths=("a.bin",),
        )


def test_transport_rejects_modified_path_and_merge_commit(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    default_branch = _git(repo, "branch", "--show-current")
    parent = _git(repo, "rev-parse", "HEAD")
    (repo / "base.txt").write_text("changed\n", encoding="utf-8")
    _git(repo, "add", "base.txt")
    _git(repo, "commit", "-m", "not an artifact addition")
    modified = _git(repo, "rev-parse", "HEAD")
    with pytest.raises(RuntimeError, match="non-addition"):
        runner._require_exact_addition_commit(
            repo,
            child=modified,
            parent=parent,
            expected_paths=("base.txt",),
        )

    _git(repo, "checkout", "-b", "side", parent)
    (repo / "side.txt").write_text("side\n", encoding="utf-8")
    _git(repo, "add", "side.txt")
    _git(repo, "commit", "-m", "side")
    _git(repo, "checkout", default_branch)
    (repo / "main.txt").write_text("main\n", encoding="utf-8")
    _git(repo, "add", "main.txt")
    _git(repo, "commit", "-m", "main")
    _git(repo, "merge", "--no-ff", "side", "-m", "merge")
    merge = _git(repo, "rev-parse", "HEAD")
    with pytest.raises(RuntimeError, match="single-parent direct child"):
        runner._require_exact_addition_commit(
            repo,
            child=merge,
            parent=_git(repo, "rev-parse", "HEAD^1"),
            expected_paths=("side.txt",),
        )


def test_blob_worktree_hash_and_toctou_snapshot_fail_closed(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    (repo / "blob.bin").write_bytes(b"\x00source\xff")
    _git(repo, "add", "blob.bin")
    _git(repo, "commit", "-m", "binary source")
    commit = _git(repo, "rev-parse", "HEAD")
    blob = runner._blob_descriptor(repo, commit, "blob.bin")
    worktree = runner._file_descriptor(repo / "blob.bin", logical_path="blob.bin")
    runner._require_descriptor_match(blob, worktree, label="base")
    (repo / "blob.bin").write_bytes(b"tampered")
    tampered = runner._file_descriptor(repo / "blob.bin", logical_path="blob.bin")
    with pytest.raises(RuntimeError, match="Descriptor mismatch"):
        runner._require_descriptor_match(tampered, blob, label="base")
    initial = {"source": {"sha256": "a" * 64}}
    runner._require_unchanged_source_snapshot(initial, copy.deepcopy(initial))
    repeated = copy.deepcopy(initial)
    repeated["source"]["sha256"] = "b" * 64
    with pytest.raises(RuntimeError, match="TOCTOU"):
        runner._require_unchanged_source_snapshot(initial, repeated)


def _synthetic_joined_allocations() -> pd.DataFrame:
    gamma_one = policy_label("objective_matched", 0.0, 1.0, 0.25)
    gamma_zero = policy_label("objective_matched", 0.0, 0.0, 0.25)
    theta_quarter = policy_label("objective_matched", 0.25, 0.0, 0.25)
    facts = {
        "a": ("2016-04", 0.0, 0.05),
        "b": ("2016-04", 1.0, 0.06),
        "c": ("2016-05", 1.0, 0.07),
        "d": ("2016-05", 0.0, 0.08),
    }
    exposures = {
        gamma_one: {"a": 99.99999, "c": 100.0},
        gamma_zero: {"b": 100.0, "d": 99.99998},
        theta_quarter: {"b": 100.0, "d": 99.99998},
    }
    rows: list[dict[str, object]] = []
    for label, policy_exposure in exposures.items():
        for loan_id, exposure in policy_exposure.items():
            period, outcome, rate = facts[loan_id]
            rows.append(
                {
                    "id": loan_id,
                    "window_id": "W1",
                    "role": "primary_oot",
                    "period": period,
                    "policy_label": label,
                    "exposure": exposure,
                    "expected_payoff_contribution": exposure * 0.01,
                    "contractual_rate": rate,
                    "conformal_lower": 0.0,
                    "conformal_upper": 1.0,
                    "snapshot_default": outcome,
                }
            )
    return pd.DataFrame(rows)


def _science_config() -> dict[str, object]:
    config = copy.deepcopy(runner.load_v1c_config(CONFIG))
    config["frontier"]["expected_windows"] = 1
    config["frontier"]["expected_primary_months"] = 2
    config["normalization"]["committed_budget_per_period"] = 100.0
    config["expected_census"]["monthly_sharp_contrasts"] = 4
    config["expected_census"]["monthly_negative_controls"] = 2
    config["expected_census"]["window_sharp_contrasts"] = 2
    config["expected_census"]["window_negative_controls"] = 1
    config["expected_census"]["direction_rows"] = 6
    return config


def test_fixed_capital_monthly_pooled_and_gamma_zero_science(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specs = (
        {
            "contrast_family": CONTRAST_GAMMA,
            "ruler": "objective_matched",
            "coordinate": 0.25,
            "theta": 0.0,
            "theta_reference": 0.0,
            "gamma": 1.0,
            "gamma_reference": 0.0,
        },
        {
            "contrast_family": CONTRAST_THETA,
            "ruler": "objective_matched",
            "coordinate": 0.25,
            "theta": 0.25,
            "theta_reference": 0.0,
            "gamma": 0.0,
            "gamma_reference": 0.0,
        },
    )
    monkeypatch.setattr(science, "_contrast_specs", lambda: specs)
    # The base validator imports its own symbol, so align its expected spec source too.
    monkeypatch.setattr(
        "src.ijds_challengers.set_preserving_embedding._contrast_specs", lambda: specs
    )
    config = _science_config()
    monthly, window, directions = science.build_v1c_sharp_embedding_contrasts(
        _synthetic_joined_allocations(), config=config, lgd=1.0, budget=100.0
    )
    gamma_monthly = monthly.loc[monthly["contrast_family"].eq(CONTRAST_GAMMA)]
    np.testing.assert_array_equal(
        gamma_monthly[
            ["policy_a_normalization_capital", "policy_b_normalization_capital"]
        ].to_numpy(dtype=float),
        np.full((2, 2), 100.0),
    )
    gamma_window = window.loc[window["contrast_family"].eq(CONTRAST_GAMMA)].iloc[0]
    np.testing.assert_allclose(
        [
            gamma_window["weighted_default_difference_lower"],
            gamma_window["weighted_default_difference_upper"],
        ],
        [0.0, 0.0],
        rtol=0.0,
        atol=1.0e-15,
    )
    np.testing.assert_array_equal(
        gamma_window[
            [
                "policy_a_normalization_capital",
                "policy_b_normalization_capital",
                "normalization_periods",
                "committed_budget_per_period",
            ]
        ].to_numpy(dtype=float),
        np.array([200.0, 200.0, 2.0, 100.0]),
    )
    negative = window.loc[window["contrast_family"].eq(CONTRAST_THETA)].iloc[0]
    np.testing.assert_array_equal(
        negative[
            [
                "expected_objective_difference",
                "weighted_default_difference_lower",
                "weighted_default_difference_upper",
            ]
        ].to_numpy(dtype=float),
        np.zeros(3),
    )
    negative_directions = directions.loc[
        directions["contrast_family"].eq(CONTRAST_THETA), "direction_at_tolerance"
    ]
    if set(negative_directions) != {"within_tolerance"}:
        pytest.fail(f"Gamma-zero directions changed: {set(negative_directions)}.")


def test_fixed_capital_validation_rejects_nonfinite_and_wrong_normalizer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specs = (
        {
            "contrast_family": CONTRAST_GAMMA,
            "ruler": "objective_matched",
            "coordinate": 0.25,
            "theta": 0.0,
            "theta_reference": 0.0,
            "gamma": 1.0,
            "gamma_reference": 0.0,
        },
        {
            "contrast_family": CONTRAST_THETA,
            "ruler": "objective_matched",
            "coordinate": 0.25,
            "theta": 0.25,
            "theta_reference": 0.0,
            "gamma": 0.0,
            "gamma_reference": 0.0,
        },
    )
    monkeypatch.setattr(science, "_contrast_specs", lambda: specs)
    monkeypatch.setattr(
        "src.ijds_challengers.set_preserving_embedding._contrast_specs", lambda: specs
    )
    config = _science_config()
    monthly, window, directions = science.build_v1c_sharp_embedding_contrasts(
        _synthetic_joined_allocations(), config=config, lgd=1.0, budget=100.0
    )
    nonfinite = monthly.copy()
    nonfinite.loc[nonfinite.index[0], "policy_a_capital"] = np.nan
    with pytest.raises(RuntimeError, match="non-finite"):
        science.validate_v1c_complete_evaluation(nonfinite, window, directions, config=config)
    wrong = window.copy()
    wrong["policy_a_normalization_capital"] = 199.0
    with pytest.raises(RuntimeError, match="common capital"):
        science.validate_v1c_complete_evaluation(monthly, wrong, directions, config=config)


@pytest.mark.parametrize("invalid", ["1", "invalid", True, np.inf, -np.inf, 2.0])
def test_endpoint_parser_rejects_nonmissing_nonbinary_or_non_numeric_values(
    invalid: object,
) -> None:
    frame = pd.DataFrame(
        {
            "snapshot_default": pd.Series([invalid], dtype=object),
            "snapshot_resolution": ["charged_off_by_reconstructed_cutoff"],
        }
    )
    with pytest.raises(RuntimeError, match="endpoint"):
        runner._validate_endpoint_values(frame, label="test")


def test_endpoint_parser_allows_only_consistent_genuine_unresolved_values() -> None:
    frame = pd.DataFrame(
        {
            "snapshot_default": pd.Series([0, 1, pd.NA], dtype="Int8"),
            "snapshot_resolution": [
                "fully_paid_by_reconstructed_cutoff",
                "charged_off_by_reconstructed_cutoff",
                "nonterminal_or_unresolved_status",
            ],
        }
    )
    audit = runner._validate_endpoint_values(frame, label="test")
    if audit != {"rows": 3, "resolved_rows": 2, "unresolved_rows": 1}:
        pytest.fail(f"Endpoint audit changed: {audit}.")
    inconsistent = frame.copy()
    inconsistent.loc[0, "snapshot_resolution"] = "charged_off_by_reconstructed_cutoff"
    with pytest.raises(RuntimeError, match="inconsistent"):
        runner._validate_endpoint_values(inconsistent, label="test")


def test_shared_completion_sharp_bound_is_not_independent_marginal_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = {
        "contrast_family": CONTRAST_GAMMA,
        "ruler": "objective_matched",
        "coordinate": 0.25,
        "theta": 0.0,
        "theta_reference": 0.0,
        "gamma": 1.0,
        "gamma_reference": 0.0,
    }
    monkeypatch.setattr(science, "_contrast_specs", lambda: (spec,))
    policy_a = policy_label("objective_matched", 0.0, 1.0, 0.25)
    policy_b = policy_label("objective_matched", 0.0, 0.0, 0.25)
    allocations = pd.DataFrame(
        [
            {
                "id": "shared-unresolved",
                "role": "primary_oot",
                "policy_label": policy_a,
                "exposure": 100.0,
                "expected_payoff_contribution": 1.0,
                "contractual_rate": 0.05,
                "conformal_lower": 0.0,
                "conformal_upper": 1.0,
                "snapshot_default": pd.NA,
            },
            {
                "id": "shared-unresolved",
                "role": "primary_oot",
                "policy_label": policy_b,
                "exposure": 50.0,
                "expected_payoff_contribution": 0.5,
                "contractual_rate": 0.05,
                "conformal_lower": 0.0,
                "conformal_upper": 1.0,
                "snapshot_default": pd.NA,
            },
            {
                "id": "b-only-resolved-zero",
                "role": "primary_oot",
                "policy_label": policy_b,
                "exposure": 50.0,
                "expected_payoff_contribution": 0.5,
                "contractual_rate": 0.05,
                "conformal_lower": 0.0,
                "conformal_upper": 1.0,
                "snapshot_default": 0,
            },
        ]
    )
    row = science._fixed_capital_rows(
        allocations,
        scope="primary_month",
        window_id="W1",
        period="2016-04",
        lgd=1.0,
        committed_budget_per_period=100.0,
        normalization_periods=1,
    )[0]
    np.testing.assert_allclose(
        [
            row["weighted_default_difference_lower"],
            row["weighted_default_difference_upper"],
        ],
        [0.0, 0.5],
        rtol=0.0,
        atol=0.0,
    )
    independent_marginal_interval = (-0.5, 1.0)
    if (
        (
            row["weighted_default_difference_lower"],
            row["weighted_default_difference_upper"],
        )
    ) == independent_marginal_interval:
        pytest.fail("V1c incorrectly combined policy marginals with independent completions.")


def _minimal_frontier_build() -> SetPreservingFrontierBuild:
    records = pd.DataFrame(
        {
            "frontier_ruler": ["objective_matched", "normalized_score"],
            "frontier_cap": [np.nan, 1.0],
            "objective_target": [1.0, np.nan],
            "risk_tolerance": [np.nan, 1.0],
            "value": [1.0, 2.0],
        }
    )
    allocations = pd.DataFrame(
        {
            "frontier_ruler": ["objective_matched", "normalized_score"],
            "frontier_cap": [np.nan, 1.0],
            "objective_target": [1.0, np.nan],
            "value": [1.0, 2.0],
        }
    )
    plain = pd.DataFrame({"value": [1.0]})
    optimum = pd.DataFrame(
        {
            "basis_valid": pd.Series([True], dtype=bool),
            "minimum_absolute_nonbasic_reduced_cost": [1.0],
            "minimum_scaled_nonbasic_reduced_cost": [1.0],
            "maximum_dual_sign_violation": [0.0],
            "objective_reconciliation_error": [0.0],
        }
    )
    return SetPreservingFrontierBuild(
        solve_records=records,
        allocations=allocations,
        embedding_diagnostics=plain.copy(),
        minimum_endpoint_diagnostics=plain.copy(),
        objective_optimum_diagnostics=optimum,
        allocation_contrasts=plain.copy(),
        order_sensitivity=plain.copy(),
        independent_validation=plain.copy(),
    )


def test_v1c_frontier_audit_rejects_nonfinite_and_invalid_basis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(science, "validate_complete_frontier", lambda *args, **kwargs: None)
    build = _minimal_frontier_build()
    science.validate_v1c_complete_frontier(build, config={}, budget=1.0)
    nonfinite = _minimal_frontier_build()
    nonfinite.embedding_diagnostics.loc[0, "value"] = np.inf
    with pytest.raises(RuntimeError, match="non-finite"):
        science.validate_v1c_complete_frontier(nonfinite, config={}, budget=1.0)
    invalid = _minimal_frontier_build()
    invalid.objective_optimum_diagnostics["basis_valid"] = False
    with pytest.raises(RuntimeError, match="basis"):
        science.validate_v1c_complete_frontier(invalid, config={}, budget=1.0)


def test_dataframe_join_identity_is_order_stable_and_content_sensitive() -> None:
    frame = pd.DataFrame(
        {
            "window_id": ["W1", "W1"],
            "period": ["2016-04", "2016-04"],
            "policy_label": ["p", "p"],
            "id": ["b", "a"],
            "exposure": [2.0, 1.0],
            "snapshot_default": [1.0, 0.0],
        }
    )
    first = runner._dataframe_content_identity(frame)
    second = runner._dataframe_content_identity(frame.iloc[::-1].reset_index(drop=True))
    if first != second:
        pytest.fail("Compact join identity depends on input row order.")
    changed = frame.copy()
    changed.loc[0, "snapshot_default"] = 0.0
    if runner._dataframe_content_identity(changed)["sha256"] == first["sha256"]:
        pytest.fail("Compact join identity failed to detect outcome-byte drift.")
