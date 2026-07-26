from __future__ import annotations

import ast
import copy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import src.ijds_challengers.set_preserving_embedding as embedding_module
from scripts.experiments.run_ijds_set_preserving_embedding_sensitivity_v1 import (
    IMPLEMENTATION_PATHS,
    TRANSITIVE_PYTHON_PATHS,
    _candidate_identity_contract,
    _require_tagged_ancestor,
    _require_v2_implementation_equals_v1,
    _require_v2_is_v1_plus_pin,
    _resolve_strict_tag,
    parse_args,
    prepare_output_paths,
    run_evaluation,
)
from src.ijds_challengers.normalized_frontier import (
    _is_minimum_endpoint_boundary_failure,
)
from src.ijds_challengers.set_preserving_embedding import (
    CONTRAST_GAMMA,
    CONTRAST_THETA,
    GAMMA_GRID,
    THETA_GRID,
    build_sharp_embedding_contrasts,
    common_25_score_objective_lower,
    embedding_diagnostics,
    load_set_preserving_config,
    metric_direction_census,
    policy_label,
    retain_primary_decision_inputs,
    set_preserving_upper,
    validate_complete_evaluation,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/experiments/ijds_set_preserving_embedding_sensitivity_2026-07-26_v1.yaml"


def test_config_locks_complete_grid_and_both_contrast_families() -> None:
    config = load_set_preserving_config(CONFIG)

    observed = (
        tuple(config["embedding"]["theta_grid"]),
        tuple(config["frontier"]["gamma_grid"]),
        config["expected_census"]["frontier_solves"],
        config["expected_census"]["order_replays"],
        config["expected_census"]["independent_solver_cells"],
        config["contrasts"]["families"],
        all(config["claim_boundary"].values()),
    )
    expected = (
        THETA_GRID,
        GAMMA_GRID,
        31_200,
        18_000,
        3_600,
        [CONTRAST_GAMMA, CONTRAST_THETA],
        True,
    )
    if observed != expected:
        pytest.fail(f"Locked embedding configuration changed: {observed!r}.")


def test_config_rejects_directory_components_in_output_names(tmp_path: Path) -> None:
    invalid = CONFIG.read_text(encoding="utf-8").replace(
        'allocations: "frontier_funded_allocations.parquet"',
        'allocations: "../frontier_funded_allocations.parquet"',
    )
    path = tmp_path / "invalid.yaml"
    path.write_text(invalid, encoding="utf-8")

    with pytest.raises(ValueError, match="directory component"):
        load_set_preserving_config(path)


def test_config_rejects_disabled_no_selection_boundary(tmp_path: Path) -> None:
    invalid = CONFIG.read_text(encoding="utf-8").replace(
        "no_theta_selection: true", "no_theta_selection: false"
    )
    path = tmp_path / "invalid.yaml"
    path.write_text(invalid, encoding="utf-8")

    with pytest.raises(ValueError, match="no-selection"):
        load_set_preserving_config(path)


def test_v1_cannot_self_authorize_outcome_evaluation() -> None:
    with pytest.raises(RuntimeError, match="V1 cannot authorize outcomes"):
        run_evaluation(config_path=CONFIG, repo_root=ROOT)


def test_hash_pinned_evaluation_config_requires_complete_source_authority(
    tmp_path: Path,
) -> None:
    source = """source_frontier:
  run_tag: "source-v1"
  protocol_tag: "protocol/source-v1"
  protocol_commit: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  config:
    path: "configs/experiments/source-v1.yaml"
    bytes: 456
    sha256: "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
  freeze:
    path: "models/source-v1/protocol_freeze.json"
    bytes: 123
    sha256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
"""
    valid = CONFIG.read_text(encoding="utf-8").replace(
        'protocol_status: "locked_candidate_two_phase_before_execution"',
        'protocol_status: "locked_hash_pinned_postfreeze_evaluation"',
    )
    valid = valid.replace(
        'run_tag: "ijds-set-preserving-embedding-sensitivity-2026-07-26-v1"',
        'run_tag: "evaluation-v2"\n' + source.rstrip(),
    )
    valid_path = tmp_path / "valid-v2.yaml"
    valid_path.write_text(valid, encoding="utf-8")
    loaded = load_set_preserving_config(valid_path)
    if loaded["source_frontier"]["freeze"]["bytes"] != 123:
        pytest.fail("Hash-pinned evaluation authority was not retained exactly.")

    missing = valid.replace(source.rstrip() + "\n", "")
    missing_path = tmp_path / "missing-source-v2.yaml"
    missing_path.write_text(missing, encoding="utf-8")
    with pytest.raises(ValueError, match="requires a committed source_frontier"):
        load_set_preserving_config(missing_path)


def test_v2_may_change_only_administrative_identity_and_source_pin() -> None:
    source = load_set_preserving_config(CONFIG)
    evaluation = copy.deepcopy(source)
    evaluation.update(
        {
            "schema_version": "2026-07-26.2",
            "protocol_status": "locked_hash_pinned_postfreeze_evaluation",
            "protocol_tag": "protocol/evaluation-v2",
            "run_tag": "evaluation-v2",
            "source_frontier": {"pinned": True},
        }
    )
    _require_v2_is_v1_plus_pin(evaluation, source)

    endpoint_drift = copy.deepcopy(evaluation)
    endpoint_drift["outcomes"]["parent_config"] = str(source["parent"]["config"])
    with pytest.raises(RuntimeError, match="canonically identical"):
        _require_v2_is_v1_plus_pin(endpoint_drift, source)

    tolerance_drift = copy.deepcopy(evaluation)
    tolerance_drift["contrasts"]["rate_negative_control_tolerance"] = 1.0
    with pytest.raises(RuntimeError, match="canonically identical"):
        _require_v2_is_v1_plus_pin(tolerance_drift, source)


def test_candidate_identity_contract_is_order_invariant_but_id_exact() -> None:
    candidates = pd.DataFrame(
        {
            "id": ["3", "1", "2"],
            "role": ["primary_oot", "policy_development", "primary_oot"],
            "period": ["2016-05", "2015-04", "2016-04"],
        }
    )
    expected = _candidate_identity_contract(candidates)
    observed = _candidate_identity_contract(candidates.iloc[::-1].reset_index(drop=True))
    if observed != expected:
        pytest.fail("Candidate fingerprint depends on input row order.")

    swapped = candidates.copy()
    swapped.loc[0, "id"] = "4"
    if _candidate_identity_contract(swapped) == expected:
        pytest.fail("Candidate fingerprint accepted an ID swap with unchanged counts.")
    with pytest.raises(RuntimeError, match="duplicate loan IDs"):
        _candidate_identity_contract(pd.concat([candidates, candidates.iloc[[0]]]))


def test_strict_tag_resolution_accepts_only_actual_tag_refs() -> None:
    parent_tag = "protocol/ijds-binary-geometry-frontier-v4-2026-07-12-v1"
    expected = "2f8a7606e4eb65aa3ae3701fb3af8d9a51c953cd"
    if _resolve_strict_tag(ROOT, parent_tag) != expected:
        pytest.fail("Strict tag resolution changed for the verified parent tag.")
    for revision_expression in (
        "HEAD",
        "--all",
        expected,
        "codex/full-conformal-audit-remediation",
    ):
        with pytest.raises(RuntimeError):
            _resolve_strict_tag(ROOT, revision_expression)


def test_source_tag_must_be_an_ancestor_of_evaluation_head() -> None:
    parent_tag = "protocol/ijds-binary-geometry-frontier-v4-2026-07-12-v1"
    parent_commit = "2f8a7606e4eb65aa3ae3701fb3af8d9a51c953cd"
    head = _resolve_strict_tag(ROOT, parent_tag)
    _require_tagged_ancestor(
        source_tag=parent_tag,
        source_commit=parent_commit,
        evaluation_commit=head,
        root=ROOT,
    )
    with pytest.raises(RuntimeError, match="no longer resolves"):
        _require_tagged_ancestor(
            source_tag=parent_tag,
            source_commit="0" * 40,
            evaluation_commit=head,
            root=ROOT,
        )


def test_v2_implementation_requires_exact_census_and_identical_shared_bytes() -> None:
    locked = {path.as_posix() for path in IMPLEMENTATION_PATHS}

    def descriptor(path: str, digest: str) -> dict[str, object]:
        return {"path": path, "bytes": 1, "sha256": digest}

    source_files = {path: descriptor(path, "a" * 64) for path in locked}
    evaluation_files = copy.deepcopy(source_files)
    source_files["configs/source-v1.yaml"] = descriptor("configs/source-v1.yaml", "b" * 64)
    evaluation_files["configs/evaluation-v2.yaml"] = descriptor(
        "configs/evaluation-v2.yaml", "c" * 64
    )
    source = {"source_files": source_files}
    evaluation = {"source_files": evaluation_files}
    _require_v2_implementation_equals_v1(
        source,
        evaluation,
        source_config_path="configs/source-v1.yaml",
        evaluation_config_path="configs/evaluation-v2.yaml",
    )

    drifted = copy.deepcopy(evaluation)
    drifted["source_files"][next(iter(locked))]["sha256"] = "d" * 64
    with pytest.raises(RuntimeError, match="scientific dependency changed"):
        _require_v2_implementation_equals_v1(
            source,
            drifted,
            source_config_path="configs/source-v1.yaml",
            evaluation_config_path="configs/evaluation-v2.yaml",
        )

    incomplete = copy.deepcopy(evaluation)
    incomplete["source_files"].pop(next(iter(locked)))
    with pytest.raises(RuntimeError, match="omits or adds"):
        _require_v2_implementation_equals_v1(
            source,
            incomplete,
            source_config_path="configs/source-v1.yaml",
            evaluation_config_path="configs/evaluation-v2.yaml",
        )


def test_transitive_authority_includes_outcome_and_v5_dependencies() -> None:
    observed = {path.as_posix() for path in IMPLEMENTATION_PATHS}
    required = {
        "src/data/outcome_observability.py",
        "src/ijds_audit/prediction.py",
        "src/evaluation/coverage_transport.py",
        "src/models/maturity_safe_pd.py",
        "src/optimization/portfolio_model.py",
        "docs/research/ijds_endpoint_reason_recovery_v5_erratum_2026-07-15.md",
        "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-15_v5.yaml",
    }
    missing = required - observed
    if missing:
        pytest.fail(f"Transitive authority omits dependencies: {sorted(missing)}.")


def _repo_import_closure(start: Path) -> set[str]:
    """Independently derive the repo-local AST import closure plus package initializers."""

    def module_file(name: str) -> Path | None:
        candidate = ROOT.joinpath(*name.split("."))
        source = candidate.with_suffix(".py")
        if source.is_file():
            return source
        initializer = candidate / "__init__.py"
        return initializer if initializer.is_file() else None

    def module_name(path: Path) -> str:
        parts = list(path.relative_to(ROOT).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    observed: set[Path] = set()
    queue = [start.resolve()]
    while queue:
        path = queue.pop(0)
        if path in observed:
            continue
        observed.add(path)
        for parent in list(path.relative_to(ROOT).parents)[:-1]:
            initializer = (ROOT / parent / "__init__.py").resolve()
            if initializer.is_file() and initializer not in observed and initializer not in queue:
                queue.append(initializer)

        tree = ast.parse(path.read_text(encoding="utf-8"))
        current = module_name(path)
        package = current if path.name == "__init__.py" else current.rsplit(".", 1)[0]
        for node in ast.walk(tree):
            candidates: list[str] = []
            if isinstance(node, ast.Import):
                candidates.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = package.split(".")
                    if node.level > 1:
                        base = base[: -(node.level - 1)]
                    prefix = ".".join(base)
                    imported = ".".join(value for value in (prefix, node.module or "") if value)
                else:
                    imported = node.module or ""
                candidates.append(imported)
                candidates.extend(
                    ".".join(value for value in (imported, alias.name) if value)
                    for alias in node.names
                )
            for candidate in candidates:
                if not candidate.startswith(("src", "scripts")):
                    continue
                resolved = module_file(candidate)
                if resolved is not None and resolved.resolve() not in observed:
                    queue.append(resolved.resolve())
    return {path.relative_to(ROOT).as_posix() for path in observed}


def test_transitive_python_authority_equals_ast_closure() -> None:
    runner = ROOT / "scripts/experiments/run_ijds_set_preserving_embedding_sensitivity_v1.py"
    expected = _repo_import_closure(runner)
    observed = {path.as_posix() for path in TRANSITIVE_PYTHON_PATHS}
    if observed != expected:
        pytest.fail(
            "Transitive Python authority differs from AST closure: "
            f"missing={sorted(expected - observed)}, extra={sorted(observed - expected)}."
        )


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Point LP is not optimal: Infeasible.", True),
        ("Point LP is not optimal: Unknown.", True),
        ("Point LP did not fill its budget: residual=1e-10", True),
        ("Point LP is not optimal: Unbounded.", False),
        ("Point LP did not bind its cap.", False),
    ],
)
def test_minimum_endpoint_retry_taxonomy_is_closed(message: str, expected: bool) -> None:
    observed = _is_minimum_endpoint_boundary_failure(RuntimeError(message))
    if observed is not expected:
        pytest.fail(f"Retry classification changed for {message!r}: {observed}.")


def test_runner_requires_an_explicit_phase() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--config", str(CONFIG)])


def test_output_paths_are_contained_and_immutable(tmp_path: Path) -> None:
    config = copy.deepcopy(load_set_preserving_config(CONFIG))
    config["run_tag"] = "set-preserving-test"
    paths = prepare_output_paths(config, repo_root=tmp_path)

    expected_data = tmp_path / "data/processed/experiments/ijds_audit/set-preserving-test"
    expected_model = tmp_path / "models/experiments/ijds_audit/set-preserving-test"
    if paths.data_dir != expected_data or paths.model_dir != expected_model:
        pytest.fail(f"Output paths escaped isolation: {paths!r}.")
    with pytest.raises(FileExistsError, match="already exists"):
        prepare_output_paths(config, repo_root=tmp_path)


def test_embedding_preserves_all_four_binary_set_types_exactly() -> None:
    point = np.array([0.20, 0.30, 0.70, 0.80])
    lower = np.array([0.05, 0.00, 0.40, 0.00])
    upper = np.array([0.60, 0.80, 1.00, 1.00])
    original_code = (lower == 0.0).astype(np.int8) + 2 * (upper == 1.0)
    np.testing.assert_array_equal(original_code, np.array([0, 1, 2, 3]))

    for theta in THETA_GRID:
        embedded = set_preserving_upper(point, lower, upper, theta=theta)
        embedded_code = (lower == 0.0).astype(np.int8) + 2 * (embedded == 1.0)
        np.testing.assert_array_equal(embedded_code, original_code)
        ordinary = upper < 1.0
        if not bool(np.all(point[ordinary] <= embedded[ordinary])):
            pytest.fail("Embedded upper endpoint fell below the point score.")
        if not bool(np.all(embedded[ordinary] <= upper[ordinary])):
            pytest.fail("Embedded upper endpoint exceeded the original endpoint.")
        if not bool(np.all(embedded[ordinary] < 1.0)):
            pytest.fail("Embedding acquired label 1 outside the original set.")
        if not bool(np.all(embedded[~ordinary] == 1.0)):
            pytest.fail("Embedding removed label 1 from the original set.")


def test_primary_decision_scrub_rejects_residual_learner_controls() -> None:
    config = load_set_preserving_config(CONFIG)
    retained = list(config["source_ingest"]["retained_decision_columns"])
    discarded = list(config["source_ingest"]["discarded_coverage_control_columns"])
    frame = pd.DataFrame({column: [0] for column in [*retained, *discarded]})

    scrubbed = retain_primary_decision_inputs(frame, config=config)

    if scrubbed.columns.tolist() != retained:
        pytest.fail(f"Primary-only scrub retained the wrong schema: {scrubbed.columns.tolist()}.")
    drifted = frame.assign(pd_unexpected_control=0.5)
    with pytest.raises(RuntimeError, match="schema drifted"):
        retain_primary_decision_inputs(drifted, config=config)


def test_embedding_endpoints_and_gamma_zero_are_exact_negative_controls() -> None:
    point = np.array([0.2, 0.4, 0.7])
    lower = np.array([0.0, 0.1, 0.2])
    upper = np.array([0.8, 1.0, 0.9])

    theta_zero = set_preserving_upper(point, lower, upper, theta=0.0)
    theta_one = set_preserving_upper(point, lower, upper, theta=1.0)
    np.testing.assert_array_equal(theta_zero, upper)
    np.testing.assert_array_equal(theta_one, np.array([0.2, 1.0, 0.7]))
    for theta in THETA_GRID:
        embedded = set_preserving_upper(point, lower, upper, theta=theta)
        score = point + 0.0 * (embedded - point)
        np.testing.assert_array_equal(score, point)
        if embedding_diagnostics(point, lower, upper, theta=theta)["sets_changed"] != 0:
            pytest.fail("Embedding diagnostic reports a changed binary set.")


@pytest.mark.parametrize(
    ("point", "lower", "upper", "message"),
    [
        ([0.2], [0.3], [0.8], "lower <= point"),
        ([0.9], [0.1], [0.8], "lower <= point"),
        ([np.nan], [0.0], [1.0], "finite"),
        ([1.1], [0.0], [1.0], r"\[0,1\]"),
    ],
)
def test_embedding_fails_closed_on_invalid_intervals(
    point: list[float], lower: list[float], upper: list[float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        set_preserving_upper(np.asarray(point), np.asarray(lower), np.asarray(upper), theta=0.25)


def test_global_objective_lower_uses_all_25_scores() -> None:
    states = {
        (theta, gamma): SimpleNamespace(minimum_objective=10.0 + theta + gamma)
        for theta in THETA_GRID
        for gamma in GAMMA_GRID
    }
    states[(1.0, 0.75)] = SimpleNamespace(minimum_objective=42.0)

    lower = common_25_score_objective_lower(
        states,
        objective_optimum=100.0,
        minimum_range=1.0e-4,
    )
    if lower != 42.0:
        pytest.fail(f"Global objective lower endpoint ignored a score cell: {lower}.")

    incomplete = dict(states)
    incomplete.pop((1.0, 0.75))
    with pytest.raises(ValueError, match="all 25 scores"):
        common_25_score_objective_lower(
            incomplete,
            objective_optimum=100.0,
            minimum_range=1.0e-4,
        )


def test_policy_labels_are_unique_over_the_complete_grid() -> None:
    labels = {
        policy_label(ruler, theta, gamma, coordinate)
        for ruler in ("objective_matched", "normalized_score")
        for theta in THETA_GRID
        for gamma in GAMMA_GRID
        for coordinate in (0.25, 0.5, 0.75)
    }
    if len(labels) != 150:
        pytest.fail(f"Policy labels collide: observed {len(labels)} labels.")


def test_direction_census_separates_literal_sign_from_tolerance_decision() -> None:
    config = load_set_preserving_config(CONFIG)
    base = {
        "window_id": "W1",
        "contrast_family": CONTRAST_GAMMA,
        "ruler": "objective_matched",
        "coordinate": 0.25,
        "theta": 0.0,
        "theta_reference": 0.0,
        "gamma": 1.0,
        "gamma_reference": 0.0,
        "policy_a": policy_label("objective_matched", 0.0, 1.0, 0.25),
        "policy_b": policy_label("objective_matched", 0.0, 0.0, 0.25),
        "weighted_default_difference_lower": 0.0,
        "weighted_default_difference_upper": 0.0,
        "weighted_miscoverage_difference_lower": 0.0,
        "weighted_miscoverage_difference_upper": 0.0,
    }
    bounds = pd.DataFrame(
        [
            {
                **base,
                "realized_payoff_difference_lower": 5.0e-5,
                "realized_payoff_difference_upper": 5.0e-5,
            },
            {
                **base,
                "window_id": "W2",
                "realized_payoff_difference_lower": -2.0e-4,
                "realized_payoff_difference_upper": -5.0e-5,
            },
        ]
    )
    directions = metric_direction_census(bounds, metrics=config["metrics"])
    payoff = directions.loc[directions["metric"].eq("standardized_payoff")]
    observed = payoff[["geometric_direction", "direction_at_tolerance"]].itertuples(
        index=False, name=None
    )
    expected = [
        ("positive", "within_tolerance"),
        ("negative", "not_directionally_separated_at_tolerance"),
    ]
    if list(observed) != expected:
        pytest.fail(f"Literal/tolerance direction semantics drifted: {payoff.to_dict('records')}.")


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
        gamma_one: {"a": 100.0, "c": 300.0},
        gamma_zero: {"b": 100.0, "d": 300.0},
        theta_quarter: {"b": 100.0, "d": 300.0},
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


def test_window_bounds_pool_numerators_instead_of_averaging_monthly_rates(
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
    monkeypatch.setattr(embedding_module, "_contrast_specs", lambda: specs)
    config = copy.deepcopy(load_set_preserving_config(CONFIG))
    config["frontier"]["expected_windows"] = 1
    config["frontier"]["expected_primary_months"] = 2
    config["expected_census"]["monthly_sharp_contrasts"] = 4
    config["expected_census"]["monthly_negative_controls"] = 2
    config["expected_census"]["window_sharp_contrasts"] = 2
    config["expected_census"]["window_negative_controls"] = 1
    config["expected_census"]["direction_rows"] = 6

    monthly, window, directions = build_sharp_embedding_contrasts(
        _synthetic_joined_allocations(), config=config, lgd=1.0
    )

    gamma_monthly = monthly.loc[monthly["contrast_family"].eq(CONTRAST_GAMMA)]
    np.testing.assert_allclose(
        gamma_monthly["weighted_default_difference_lower"].to_numpy(),
        np.array([-1.0, 1.0]),
    )
    gamma_window = window.loc[window["contrast_family"].eq(CONTRAST_GAMMA)].iloc[0]
    # Capital is 100 in month one and 300 in month two: pooled result is 0.5,
    # whereas an invalid unweighted average of monthly rates would be zero.
    np.testing.assert_allclose(
        [
            gamma_window["weighted_default_difference_lower"],
            gamma_window["weighted_default_difference_upper"],
        ],
        [0.5, 0.5],
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
        pytest.fail(f"Negative-control directions changed: {set(negative_directions)}.")

    mutated_reference = monthly.copy()
    mutated_reference.loc[mutated_reference.index[0], "policy_b"] = "mutated-policy"
    with pytest.raises(RuntimeError, match="mutated contrast specification"):
        validate_complete_evaluation(mutated_reference, window, directions, config=config)

    corrupted_directions = directions.copy()
    gamma_direction = corrupted_directions.index[
        corrupted_directions["contrast_family"].eq(CONTRAST_GAMMA)
    ][0]
    corrupted_directions.loc[gamma_direction, "lower"] += 0.5
    with pytest.raises(RuntimeError, match="does not reconcile"):
        validate_complete_evaluation(monthly, window, corrupted_directions, config=config)

    cancelled = monthly.copy()
    cancelled_negative = cancelled.index[cancelled["contrast_family"].eq(CONTRAST_THETA)]
    cancelled.loc[cancelled_negative, "expected_objective_difference"] = [50.0, -50.0]
    for lower_name, upper_name in (
        ("realized_payoff_difference_lower", "realized_payoff_difference_upper"),
        ("weighted_default_difference_lower", "weighted_default_difference_upper"),
    ):
        values = [50.0, -50.0] if lower_name.startswith("realized") else [1.0, -1.0]
        cancelled.loc[cancelled_negative, lower_name] = values
        cancelled.loc[cancelled_negative, upper_name] = values
    with pytest.raises(RuntimeError, match="monthly negative control"):
        validate_complete_evaluation(cancelled, window, directions, config=config)
