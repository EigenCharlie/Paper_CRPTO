from __future__ import annotations

import ast
import json
import pickle
import re
from itertools import product
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import yaml
from scipy.special import expit
from sklearn.linear_model import LogisticRegression

from src.ijds_audit.calibrator_sensitivity import (
    CALIBRATOR_METHODS,
    WINDOW_IDS,
    CalibratorResidualRecipe,
    apply_calibrator_family,
    apply_common_taxonomy_recipe,
    assign_common_groups,
    calibrator_state_audit,
    coverage_cell,
    fit_calibrator_family,
    fit_common_taxonomy_recipe,
    float_array_sha256,
    load_recipe_payload,
    recipe_payload,
    recover_catboost_base_probability,
    shared_completion_coverage_difference,
    string_array_sha256,
    transform_platt_edges_to_q_raw,
)
from src.ijds_audit.calibrator_sensitivity_protocol import (
    EVALUATION_PROTOCOL_TAG,
    FREEZE_PROTOCOL_TAG,
    FREEZE_RUN_TAG,
    PENDING_TOKEN,
    PHASE_A_COMMIT_PATHS,
    PHASE_B_COMMIT_PATHS,
    _available_2011_labels,
    _reconcile_active_platt_fit,
    _require_exact_commit_paths,
    load_calibrator_sensitivity_config,
    require_locked_evaluation_source,
)
from src.ijds_audit.prediction import binary_probability_metrics
from src.ijds_audit.protocol import load_recipes
from src.models.binary_conformal_guardrail import assign_conformal_groups

ROOT = Path(__file__).resolve().parents[1]
FREEZE_CONFIG = (
    ROOT / "configs" / "experiments" / "ijds_calibrator_sensitivity_freeze_2026-07-30_v1.yaml"
)
EVALUATION_CONFIG = (
    ROOT / "configs" / "experiments" / "ijds_calibrator_sensitivity_evaluation_2026-07-30_v1.yaml"
)


def _fitted_platt() -> LogisticRegression:
    margin = np.linspace(-2.0, 2.0, 120)
    event_probability = 0.15 + 0.65 * (margin - margin.min()) / np.ptp(margin)
    labels = (((np.arange(120) * 37) % 101) / 101.0 < event_probability).astype(int)
    model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000, random_state=42)
    model.fit(margin.reshape(-1, 1), labels)
    return model


def test_platt_inverse_roundtrip_and_transformed_taxonomy_preserve_membership() -> None:
    platt = _fitted_platt()
    margin = np.linspace(-4.0, 3.0, 301)
    probability = platt.predict_proba(margin.reshape(-1, 1))[:, 1]
    recovered_margin, q_raw = recover_catboost_base_probability(probability, platt)
    replay = platt.predict_proba(recovered_margin.reshape(-1, 1))[:, 1]
    assert np.max(np.abs(recovered_margin - margin)) < 1.0e-12
    assert np.max(np.abs(replay - probability)) < 1.0e-14
    assert np.array_equal(q_raw, expit(recovered_margin))

    platt_edges = tuple(np.quantile(probability, np.linspace(0.0, 1.0, 6)))
    raw_edges = transform_platt_edges_to_q_raw(platt_edges, platt)
    assert np.array_equal(
        assign_conformal_groups(probability, platt_edges),
        assign_common_groups(q_raw, raw_edges),
    )
    wrong_class_order = _fitted_platt()
    wrong_class_order.classes_ = np.array([1, 0])
    with pytest.raises(RuntimeError, match=r"class order must be exactly \[0, 1\]"):
        recover_catboost_base_probability(probability, wrong_class_order)


def test_four_calibrator_family_is_bounded_and_venn_scalarization_is_standard() -> None:
    rng = np.random.default_rng(20260730)
    q_raw = np.sort(rng.uniform(0.01, 0.85, size=500))
    labels = rng.binomial(1, 0.04 + 0.65 * q_raw).astype(int)
    platt = _fitted_platt()
    margin = np.log(q_raw / (1.0 - q_raw))
    frozen_platt = platt.predict_proba(margin.reshape(-1, 1))[:, 1]
    family = fit_calibrator_family(
        q_raw=q_raw,
        labels=labels,
        frozen_platt=platt,
        venn_abers_precision=None,
    )
    probabilities, multiprobability_pair = apply_calibrator_family(
        family,
        q_raw=q_raw,
        margin=margin,
        frozen_platt_probability=frozen_platt,
    )
    assert tuple(probabilities) == CALIBRATOR_METHODS
    for values in probabilities.values():
        assert values.shape == q_raw.shape
        assert np.isfinite(values).all()
        assert ((values >= 0.0) & (values <= 1.0)).all()
        assert np.min(np.diff(values)) >= -1.0e-14
    state = calibrator_state_audit(family)
    assert state["platt_classes"] == [0, 1]
    assert state["beta_parameters"]["a"] >= 0.0
    assert state["beta_parameters"]["b"] >= 0.0
    assert max(state["beta_iterations"]) < state["beta_max_iter"]
    expected_prime = multiprobability_pair[:, 1] / (
        1.0 - multiprobability_pair[:, 0] + multiprobability_pair[:, 1]
    )
    assert np.max(np.abs(expected_prime - probabilities["venn_abers"])) <= 1.0e-15
    assert (multiprobability_pair[:, 0] <= probabilities["venn_abers"]).all()
    assert (probabilities["venn_abers"] <= multiprobability_pair[:, 1]).all()
    with pytest.raises(RuntimeError, match=r"q_raw does not match expit\(raw_margin\)"):
        apply_calibrator_family(
            family,
            q_raw=q_raw + 1.0e-4,
            margin=margin,
        )


def test_common_taxonomy_recipe_decouples_membership_from_residual_score() -> None:
    q_raw = np.linspace(0.01, 0.99, 100)
    edges = tuple(np.linspace(0.01, 0.99, 6))
    labels = (np.arange(100) % 7 == 0).astype(int)
    calibrated = np.sqrt(q_raw)
    recipe = fit_common_taxonomy_recipe(
        method="isotonic",
        window_id="w_test",
        q_raw=q_raw,
        calibrated_probability=calibrated,
        labels=labels,
        alpha=0.1,
        taxonomy_edges_q_raw=edges,
        taxonomy_provenance="unit_test",
    )
    groups, lower, upper = apply_common_taxonomy_recipe(
        q_raw=q_raw,
        calibrated_probability=calibrated,
        recipe=recipe,
    )
    assert tuple(recipe.group_counts) == (20, 20, 20, 20, 20)
    assert tuple(recipe.raw_finite_sample_ranks) == (19, 19, 19, 19, 19)
    assert np.array_equal(groups, assign_common_groups(q_raw, edges))
    assert ((lower >= 0.0) & (lower <= upper) & (upper <= 1.0)).all()


def test_recipe_json_roundtrip_preserves_locked_method_order() -> None:
    recipe = CalibratorResidualRecipe(
        method="platt",
        window_id="w01",
        alpha=0.1,
        taxonomy_edges_q_raw=(0.0, 0.1, 0.2, 0.3, 0.5, 1.0),
        residual_quantiles=(0.1, 0.2, 0.3, 0.4, 0.5),
        group_counts=(10, 11, 12, 13, 14),
        finite_sample_ranks=(10, 11, 12, 13, 14),
        raw_finite_sample_ranks=(10, 11, 12, 13, 14),
        taxonomy_provenance="unit_test",
    )
    recipes = {
        method: {
            window_id: CalibratorResidualRecipe(
                **{
                    **recipe.__dict__,
                    "method": method,
                    "window_id": window_id,
                }
            )
            for window_id in WINDOW_IDS
        }
        for method in CALIBRATOR_METHODS
    }
    recovered = load_recipe_payload(json.loads(json.dumps(recipe_payload(recipes))))
    assert tuple(recovered) == CALIBRATOR_METHODS
    assert recovered["platt"][WINDOW_IDS[0]].window_id == WINDOW_IDS[0]
    assert recovered["platt"][WINDOW_IDS[0]].residual_quantiles == recipe.residual_quantiles


def _coverage_difference_for_completion(
    completion: tuple[int, ...],
    observed: np.ndarray,
    lower_a: np.ndarray,
    upper_a: np.ndarray,
    lower_b: np.ndarray,
    upper_b: np.ndarray,
) -> float:
    completed = observed.copy()
    completed[np.isnan(completed)] = np.asarray(completion, dtype=float)
    cover_a = (completed >= lower_a) & (completed <= upper_a)
    cover_b = (completed >= lower_b) & (completed <= upper_b)
    return float(np.mean(cover_a.astype(float) - cover_b.astype(float)))


def test_pairwise_bounds_use_one_shared_loanwise_completion() -> None:
    outcomes = np.array([np.nan, np.nan, 0.0, 1.0])
    lower_a = np.array([0.0, 0.2, 0.0, 0.0])
    upper_a = np.array([0.4, 1.0, 0.8, 1.0])
    lower_b = np.array([0.0, 0.0, 0.1, 0.2])
    upper_b = np.array([1.0, 0.4, 1.0, 1.0])
    result = shared_completion_coverage_difference(
        outcomes=outcomes,
        lower_a=lower_a,
        upper_a=upper_a,
        lower_b=lower_b,
        upper_b=upper_b,
    )
    brute_force = [
        _coverage_difference_for_completion(
            completion,
            outcomes,
            lower_a,
            upper_a,
            lower_b,
            upper_b,
        )
        for completion in product((0, 1), repeat=2)
    ]
    assert result["coverage_difference_lower"] == min(brute_force)
    assert result["coverage_difference_upper"] == max(brute_force)
    reverse = shared_completion_coverage_difference(
        outcomes=outcomes,
        lower_a=lower_b,
        upper_a=upper_b,
        lower_b=lower_a,
        upper_b=upper_a,
    )
    assert reverse["coverage_difference_lower"] == -result["coverage_difference_upper"]
    assert reverse["coverage_difference_upper"] == -result["coverage_difference_lower"]


def test_vector_hash_contracts_are_deterministic_and_unambiguous() -> None:
    assert float_array_sha256([1.0, 2.0]) == float_array_sha256(np.array([1.0, 2.0], dtype=">f8"))
    assert string_array_sha256(["a", "bc"]) != string_array_sha256(["ab", "c"])


def test_locked_configs_declare_complete_grids_and_pending_phase_b_fails_closed() -> None:
    freeze = load_calibrator_sensitivity_config(FREEZE_CONFIG)
    evaluation = load_calibrator_sensitivity_config(EVALUATION_CONFIG)
    assert freeze["run_tag"] == FREEZE_RUN_TAG
    assert freeze["protocol_tag"] == FREEZE_PROTOCOL_TAG
    assert freeze["design"]["methods"] == list(CALIBRATOR_METHODS)
    assert evaluation["design"]["expected_evaluation_cells"] == 192
    assert evaluation["design"]["expected_overall_cells"] == 32
    assert evaluation["design"]["expected_pairwise_cells"] == 288
    assert evaluation["protocol_tag"] == EVALUATION_PROTOCOL_TAG
    source = evaluation["source"]
    if PENDING_TOKEN in str(source["phase_a_source_commit"]):
        with pytest.raises(RuntimeError, match="pending"):
            require_locked_evaluation_source(evaluation)
    else:
        assert re.fullmatch(r"[0-9a-f]{40}", str(source["phase_a_source_commit"]))
        for name in ("phase_a_freeze", "phase_a_receipt"):
            descriptor = source[name]
            assert int(descriptor["bytes"]) > 0
            assert re.fullmatch(r"[0-9a-f]{64}", str(descriptor["sha256"]))
        require_locked_evaluation_source(evaluation)
    assert (
        evaluation["interpretation"]["if_any_upper_at_or_above_nominal"]
        == "uniform_closed_family_shortfall_not_established"
    )
    assert (
        evaluation["design"]["expected_calibrator_fit_ordered_id_sha256"]
        == "81045766e24eb4039c922437a92fb7e37c2715bbe67c5fd95cfd0386d07563de"
    )


def test_exact_commit_path_gate_rejects_extra_or_missing_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    expected = frozenset({"expected/a.json", "expected/b.parquet"})

    def install(paths: tuple[str, ...]) -> None:
        payload = b"".join(path.encode("utf-8") + b"\0" for path in paths)
        monkeypatch.setattr(
            "src.ijds_audit.calibrator_sensitivity_protocol.subprocess.run",
            lambda *args, **kwargs: SimpleNamespace(stdout=payload),
        )

    install(tuple(sorted(expected)))
    _require_exact_commit_paths(
        tmp_path,
        commit="a" * 40,
        expected_paths=expected,
        label="unit-test commit",
    )
    install((*sorted(expected), "unexpected/code.py"))
    with pytest.raises(RuntimeError, match=r"extra=.*unexpected/code\.py"):
        _require_exact_commit_paths(
            tmp_path,
            commit="a" * 40,
            expected_paths=expected,
            label="unit-test commit",
        )
    install(("expected/a.json",))
    with pytest.raises(RuntimeError, match=r"missing=.*expected/b\.parquet"):
        _require_exact_commit_paths(
            tmp_path,
            commit="a" * 40,
            expected_paths=expected,
            label="unit-test commit",
        )
    assert len(PHASE_A_COMMIT_PATHS) == 8
    assert (
        frozenset(
            {
                "configs/experiments/ijds_calibrator_sensitivity_evaluation_2026-07-30_v1.yaml",
                "docs/research/ijds_calibrator_sensitivity_v1_evaluation_lock_2026-07-30.md",
            }
        )
        == PHASE_B_COMMIT_PATHS
    )


def test_active_platt_fit_reconciliation_locks_ordered_panel_and_metrics() -> None:
    calibration = pd.DataFrame(
        {
            "id": pd.Series(["a", "b", "c", "d", "e", "f"], dtype="string"),
            "pd_catboost_platt": [0.05, 0.15, 0.2, 0.65, 0.8, 0.95],
            "terminal_default": np.array([0, 0, 1, 0, 1, 1], dtype=np.int8),
        }
    )
    labels = calibration["terminal_default"].to_numpy(dtype=int)
    probabilities = calibration["pd_catboost_platt"].to_numpy(dtype=float)
    metrics = binary_probability_metrics(labels, probabilities)
    source_freeze = {
        "learner_metrics": {
            "catboost_platt": {
                "probability_calibration": metrics,
            }
        }
    }
    kwargs = {
        "calibration": calibration,
        "source_freeze": source_freeze,
        "expected_ordered_id_sha256": string_array_sha256(calibration["id"].astype(str)),
        "expected_ordered_label_sha256": float_array_sha256(labels.astype(float)),
        "expected_platt_probability_sha256": float_array_sha256(probabilities),
        "expected_y0": 3,
        "expected_y1": 3,
        "tolerance": 0.0,
    }
    result = _reconcile_active_platt_fit(**kwargs)
    assert result["metric_max_abs_difference"] == 0.0
    assert result["metrics"] == metrics
    with pytest.raises(RuntimeError, match="ordered 2011 Platt-fit label hash"):
        _reconcile_active_platt_fit(
            **{
                **kwargs,
                "expected_ordered_label_sha256": "0" * 64,
            }
        )


def test_recipe_loader_fails_closed_on_rank_or_taxonomy_drift() -> None:
    counts = (10, 11, 12, 13, 14)
    template = CalibratorResidualRecipe(
        method="platt",
        window_id=WINDOW_IDS[0],
        alpha=0.1,
        taxonomy_edges_q_raw=(0.0, 0.1, 0.2, 0.3, 0.5, 1.0),
        residual_quantiles=(0.1, 0.2, 0.3, 0.4, 0.5),
        group_counts=counts,
        finite_sample_ranks=counts,
        raw_finite_sample_ranks=counts,
        taxonomy_provenance="unit_test",
    )
    recipes = {
        method: {
            window_id: CalibratorResidualRecipe(
                **{
                    **template.__dict__,
                    "method": method,
                    "window_id": window_id,
                }
            )
            for window_id in WINDOW_IDS
        }
        for method in CALIBRATOR_METHODS
    }
    payload = recipe_payload(recipes)
    payload["platt"][WINDOW_IDS[0]]["raw_finite_sample_ranks"] = (9, 11, 12, 13, 14)
    with pytest.raises(RuntimeError, match="rank formula"):
        load_recipe_payload(payload)

    payload = recipe_payload(recipes)
    payload["beta"][WINDOW_IDS[-1]]["taxonomy_edges_q_raw"] = (
        0.0,
        0.1,
        0.15,
        0.3,
        0.5,
        1.0,
    )
    with pytest.raises(RuntimeError, match="common taxonomy edges"):
        load_recipe_payload(payload)


@pytest.mark.parametrize(
    ("outcomes", "lower", "upper"),
    [
        ([2.0], [0.0], [1.0]),
        ([0.0], [np.nan], [1.0]),
        ([0.0], [0.8], [0.2]),
        ([np.nan], [0.0], [1.0]),
    ],
)
def test_coverage_validation_rejects_invalid_binary_cells(
    outcomes: list[float],
    lower: list[float],
    upper: list[float],
) -> None:
    with pytest.raises(ValueError):
        coverage_cell(
            outcomes=np.asarray(outcomes),
            lower=np.asarray(lower),
            upper=np.asarray(upper),
        )


def test_narrow_calibrator_label_scan_retains_only_declared_2011_ids(
    tmp_path: Path,
) -> None:
    raw = pd.DataFrame(
        {
            "id": ["cal_0", "oot_0", "cal_1"],
            "issue_d": ["Jan-2011", "Apr-2016", "Dec-2011"],
            "term": [" 36 months", " 36 months", " 36 months"],
            "loan_status": ["Fully Paid", "Charged Off", "Charged Off"],
            "last_pymnt_d": ["Jan-2012", "Jun-2017", "Jan-2012"],
        }
    )
    raw_path = tmp_path / "raw.csv"
    raw.to_csv(raw_path, index=False)
    calibration_scores = pd.DataFrame(
        {"id": pd.Series(["cal_0", "cal_1"], dtype="string"), "pd_catboost_platt": [0.1, 0.2]}
    )
    base_config = {
        "source": {
            "csv_chunksize": 1,
            "information_cutoff": "2016-03-31",
            "charged_off_reporting_lag_months": 6,
        },
        "design": {
            "probability_calibration_start": "2011-01-01",
            "probability_calibration_end": "2011-12-31",
            "term_months": 36,
        },
    }
    labels = _available_2011_labels(
        raw_path=raw_path,
        calibration_scores=calibration_scores,
        base_config=base_config,
    )
    assert labels.columns.tolist() == ["id", "terminal_default"]
    assert labels["id"].astype(str).tolist() == ["cal_0", "cal_1"]
    assert "oot_0" not in labels["id"].astype(str).tolist()


def test_dependencies_are_exactly_pinned_and_provenance_tracks_them() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    provenance = (ROOT / "src" / "utils" / "isolated_experiment.py").read_text(encoding="utf-8")
    assert '"betacal==1.1.0"' in pyproject
    assert '"venn-abers==1.5.3"' in pyproject
    assert '"betacal"' in provenance
    assert '"venn-abers"' in provenance


def test_new_runtime_modules_do_not_use_assert_statements_or_protected_stages() -> None:
    paths = (
        ROOT / "src" / "ijds_audit" / "calibrator_sensitivity.py",
        ROOT / "src" / "ijds_audit" / "calibrator_sensitivity_protocol.py",
        ROOT / "scripts" / "experiments" / "run_ijds_calibrator_sensitivity_v1.py",
    )
    protected = (
        "crpto.pd.champion",
        "crpto.conformal.intervals",
        "crpto.conformal.validation",
        "crpto.portfolio.optimization",
        "crpto.portfolio.bound_exact_eval",
    )
    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert not any(isinstance(node, ast.Assert) for node in ast.walk(tree))
        assert all(stage not in source for stage in protected)


def test_active_platt_common_taxonomy_replays_all_eight_canonical_recipes() -> None:
    scores_path = (
        ROOT
        / "data"
        / "processed"
        / "experiments"
        / "ijds_audit"
        / "ijds-binary-geometry-frontier-v4-2026-07-12-v1"
        / "prediction"
        / "scores.parquet"
    )
    fit_path = (
        ROOT
        / "data"
        / "processed"
        / "experiments"
        / "ijds_audit"
        / "ijds-binary-geometry-frontier-v4-2026-07-12-v1"
        / "prediction"
        / "residual_fit_audit.parquet"
    )
    recipe_path = (
        ROOT
        / "models"
        / "experiments"
        / "ijds_audit"
        / "ijds-binary-geometry-frontier-v4-2026-07-12-v1"
        / "prediction"
        / "residual_recipes.json"
    )
    platt_path = (
        ROOT
        / "models"
        / "experiments"
        / "ijds_audit"
        / "ijds-binary-geometry-frontier-v4-2026-07-12-v1"
        / "prediction"
        / "catboost_platt.pkl"
    )
    if not all(path.is_file() for path in (scores_path, fit_path, recipe_path, platt_path)):
        pytest.skip("Active V4 scientific artifacts are not materialized in this checkout.")
    with platt_path.open("rb") as handle:
        platt = pickle.load(handle)
    assert isinstance(platt, LogisticRegression)
    recipes = load_recipes(recipe_path)["catboost_platt"]
    fit = pd.read_parquet(fit_path)
    canonical = fit.loc[fit["learner"].eq("catboost_platt") & fit["taxonomy_groups"].eq(5)]
    first = recipes[next(iter(recipes))][5]
    q_edges = transform_platt_edges_to_q_raw(first.bin_edges, platt)
    for window_id, active in recipes.items():
        active_recipe = active[5]
        frame = canonical.loc[canonical["window_id"].eq(window_id)]
        _, q_raw = recover_catboost_base_probability(
            frame["pd_point"].to_numpy(dtype=float),
            platt,
        )
        replay = fit_common_taxonomy_recipe(
            method="platt",
            window_id=window_id,
            q_raw=q_raw,
            calibrated_probability=frame["pd_point"].to_numpy(dtype=float),
            labels=frame["terminal_default"].to_numpy(dtype=int),
            alpha=0.1,
            taxonomy_edges_q_raw=q_edges,
            taxonomy_provenance="test",
        )
        assert np.array_equal(
            assign_common_groups(q_raw, q_edges),
            frame["conformal_group"].to_numpy(dtype=int),
        )
        assert replay.group_counts == active_recipe.group_counts
        assert replay.finite_sample_ranks == active_recipe.finite_sample_ranks
        assert replay.raw_finite_sample_ranks == active_recipe.raw_finite_sample_ranks
        assert (
            np.max(
                np.abs(
                    np.asarray(replay.residual_quantiles)
                    - np.asarray(active_recipe.residual_quantiles)
                )
            )
            == 0.0
        )


def test_yaml_sources_bind_active_residual_recipe_descriptor() -> None:
    config = yaml.safe_load(FREEZE_CONFIG.read_text(encoding="utf-8"))
    descriptor = config["source"]["residual_recipes"]
    assert descriptor == {
        "path": (
            "models/experiments/ijds_audit/"
            "ijds-binary-geometry-frontier-v4-2026-07-12-v1/"
            "prediction/residual_recipes.json"
        ),
        "bytes": 74218,
        "sha256": "0874a5e9eea37adce302f4a059d4ccde5570230a7fdabcc29ceab410988f207a",
    }
