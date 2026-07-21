from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import highspy
import numpy as np
import pandas as pd
import pytest
import yaml
from scipy.sparse import csc_matrix

from scripts.experiments.run_ijds_policy_support_optimal_face_v2 import (
    DEFAULT_CONFIG_PATH,
    FACE_COLUMNS,
    _frozen_allocation_reconciliation_fields,
    _load_frozen_allocation_reference,
    _load_v1_census,
    _policy_feasibility_fields,
    _reconcile_breakpoint_comparisons,
    _resolve_locked_config_path,
    _rhs_basis_range_coverage_diagnostics,
    _solver_identity,
    _summary,
    _validate_v1_census_frame,
    _verify_parent_config_from_freeze,
    load_config,
    preflight_output_paths,
    prepare_output_paths,
)
from src.ijds_audit.optimal_face_certification import (
    FullBasisAudit,
    audit_full_basis,
    breakpoint_probe_plan,
    normalized_exposure_distance,
    optimal_face_range,
)
from src.ijds_audit.portfolio import PointPortfolioSession

ROOT = Path(__file__).resolve().parents[1]


def _synthetic_session(
    *,
    cost: np.ndarray,
    matrix: np.ndarray,
    row_lower: np.ndarray,
    row_upper: np.ndarray,
    col_lower: np.ndarray | None = None,
    col_upper: np.ndarray | None = None,
) -> tuple[Any, Any]:
    objective = np.asarray(cost, dtype=float)
    rows = np.asarray(matrix, dtype=float)
    n_rows, n_columns = rows.shape
    lower = np.zeros(n_columns) if col_lower is None else np.asarray(col_lower, dtype=float)
    upper = np.ones(n_columns) if col_upper is None else np.asarray(col_upper, dtype=float)
    sparse = csc_matrix(rows)
    lp = highspy.HighsLp()
    lp.num_col_ = n_columns
    lp.num_row_ = n_rows
    lp.col_cost_ = objective.tolist()
    lp.col_lower_ = lower.tolist()
    lp.col_upper_ = upper.tolist()
    lp.row_lower_ = np.asarray(row_lower, dtype=float).tolist()
    lp.row_upper_ = np.asarray(row_upper, dtype=float).tolist()
    lp.sense_ = highspy.ObjSense.kMaximize
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.num_col_ = n_columns
    lp.a_matrix_.num_row_ = n_rows
    lp.a_matrix_.start_ = sparse.indptr.astype(np.int32).tolist()
    lp.a_matrix_.index_ = sparse.indices.astype(np.int32).tolist()
    lp.a_matrix_.value_ = sparse.data.astype(float).tolist()
    solver = highspy.Highs()
    solver.setOptionValue("output_flag", False)
    solver.setOptionValue("log_to_console", False)
    solver.setOptionValue("solver", "simplex")
    solver.setOptionValue("presolve", "off")
    solver.setOptionValue("threads", 1)
    solver.setOptionValue("dual_feasibility_tolerance", 1.0e-9)
    solver.setOptionValue("primal_feasibility_tolerance", 1.0e-9)
    assert solver.passModel(lp) == highspy.HighsStatus.kOk
    assert solver.run() != highspy.HighsStatus.kError
    assert "Optimal" in solver.modelStatusToString(solver.getModelStatus())
    session = SimpleNamespace(
        solver=solver,
        amount=np.ones(n_columns, dtype=float),
        objective=objective,
    )
    solution = SimpleNamespace(objective_value=float(solver.getObjectiveValue()))
    return session, solution


def _audit(session: Any, solution: Any, *, row_names: tuple[str, ...]) -> FullBasisAudit:
    return audit_full_basis(
        cast(Any, session),
        cast(Any, solution),
        dual_absolute_tolerance=1.0e-7,
        dual_relative_tolerance=1.0e-12,
        primal_tolerance=1.0e-9,
        row_names=row_names,
    )


def test_v2_config_is_locked_complete_and_outcome_free() -> None:
    config = load_config(DEFAULT_CONFIG_PATH)
    assert config["schema_version"] == "2026-07-21.1"
    assert config["hypothesis"].strip()
    assert config["protocol_status"].endswith("before_execution")
    assert config["census"] == {
        "expected_rows": 7_297,
        "expected_periods": 15,
        "expected_basis_breakpoints": 2_952,
        "expected_lateral_probe_rows": 5_874,
        "key_columns": ["period", "point_cap"],
        "breakpoint_column": "is_period_basis_breakpoint",
        "required_value_columns": [
            "expected_objective",
            "weighted_point_score",
            "basis_cap_lower",
            "basis_cap_upper",
            "is_development_support_lower",
            "is_development_support_upper",
        ],
        "complete_census_required": True,
    }
    assert config["claim_boundary"]["outcome_columns_passed"] == []
    assert config["claim_boundary"]["no_exact_symbolic_optimal_face_claim"] is True
    assert config["claim_boundary"]["no_global_optimal_face_diameter_claim"] is True
    assert (
        config["claim_boundary"]["certificate_requires_complete_frozen_allocation_reconciliation"]
        is True
    )
    assert (
        config["claim_boundary"]["fresh_rhs_basis_range_coverage_at_registered_tolerance_only"]
        is True
    )
    assert config["claim_boundary"]["no_allocation_continuity_or_seam_conditioning_claim"]
    assert config["replay_provenance_context"] == {
        "equal_quarter_followup": "non_primary_replay_provenance_only",
        "input_to_this_outcome_free_audit": False,
    }


@pytest.mark.parametrize(
    ("old", "new", "match"),
    [
        ("outcome_columns_passed: []", "outcome_columns_passed: [loan_status]", "outcomes"),
        (
            "input_to_this_outcome_free_audit: false",
            "input_to_this_outcome_free_audit: true",
            "replay provenance",
        ),
        (
            "no_untriggered_face_solves: true",
            "no_untriggered_face_solves: false",
            "Untriggered",
        ),
        ('schema_version: "2026-07-21.1"', 'schema_version: "2026-07-21.2"', "schema"),
        ("hypothesis: >-", "hypothesis: ''\nlocked_hypothesis_comment: >-", "hypothesis"),
    ],
)
def test_v2_config_fails_closed(tmp_path: Path, old: str, new: str, match: str) -> None:
    text = DEFAULT_CONFIG_PATH.read_text(encoding="utf-8").replace(old, new)
    path = tmp_path / "broken.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        load_config(path)


def test_execution_requires_the_canonical_tracked_v2_config_path(tmp_path: Path) -> None:
    canonical = tmp_path / "configs/experiments/ijds_policy_support_optimal_face_2026-07-21_v2.yaml"
    canonical.parent.mkdir(parents=True)
    canonical.write_text(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    alternate = tmp_path / "alternate.yaml"
    alternate.write_text(canonical.read_text(encoding="utf-8"), encoding="utf-8")
    assert _resolve_locked_config_path(canonical, repo_root=tmp_path) == canonical.resolve()
    with pytest.raises(RuntimeError, match="locked config"):
        _resolve_locked_config_path(alternate, repo_root=tmp_path)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("central_basis_diagnostics", "../escape.parquet", "contained basename"),
        (
            "fresh_rhs_basis_range_coverage",
            "central_full_basis_diagnostics.parquet",
            "distinct",
        ),
        ("deterministic_result", "summary.parquet", "must end in .json"),
    ],
)
def test_v2_output_names_fail_closed(tmp_path: Path, field: str, value: str, match: str) -> None:
    payload = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    payload["output"][field] = value
    path = tmp_path / "bad_output.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        load_config(path)


def test_solver_identity_persists_effective_highs_contract() -> None:
    identity = _solver_identity(load_config(DEFAULT_CONFIG_PATH))
    assert identity["highspy_version"] == "1.15.1"
    assert identity["highs_native_version"] == "1.15.1"
    assert identity["highs_githash"] == "04024d7"
    assert identity["dual_feasibility_tolerance"] == 1.0e-9
    assert identity["primal_feasibility_tolerance"] == 1.0e-9
    assert identity["zero_all_clocks_available"] is False


def test_v1_census_descriptor_is_hash_locked_and_complete() -> None:
    config = load_config(DEFAULT_CONFIG_PATH)
    census = _load_v1_census(config, repo_root=ROOT)
    assert len(census) == 7_297
    assert census["period"].nunique() == 15
    assert int(census["is_period_basis_breakpoint"].sum()) == 2_952


def _minimal_v1_census_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "period": ["2018-01", "2018-01"],
            "point_cap": [0.05, 0.12],
            "is_period_basis_breakpoint": [True, False],
            "expected_objective": [1.0, 0.9],
            "weighted_point_score": [0.05, 0.12],
            "basis_cap_lower": [0.04, 0.10],
            "basis_cap_upper": [0.07, 0.13],
            "is_development_support_lower": [True, False],
            "is_development_support_upper": [False, True],
        }
    )


def test_v1_census_schema_preflight_covers_every_late_consumed_field() -> None:
    config = load_config(DEFAULT_CONFIG_PATH)
    frame = _minimal_v1_census_frame()
    _validate_v1_census_frame(frame, contract=config["census"])

    missing = frame.drop(columns="expected_objective")
    with pytest.raises(RuntimeError, match="missing columns"):
        _validate_v1_census_frame(missing, contract=config["census"])

    nonfinite = frame.copy()
    nonfinite.loc[0, "basis_cap_upper"] = np.inf
    with pytest.raises(RuntimeError, match="not finite numeric"):
        _validate_v1_census_frame(nonfinite, contract=config["census"])

    nonboolean = frame.copy()
    nonboolean["is_development_support_lower"] = [1, 0]
    with pytest.raises(RuntimeError, match="not complete Boolean"):
        _validate_v1_census_frame(nonboolean, contract=config["census"])


def test_parent_v4_config_is_hash_locked_by_the_verified_parent_freeze() -> None:
    config = load_config(DEFAULT_CONFIG_PATH)
    freeze_path = ROOT / str(config["parent"]["protocol_freeze"]["path"])
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    path, descriptor = _verify_parent_config_from_freeze(config, freeze, repo_root=ROOT)
    assert path == (ROOT / str(config["parent"]["config"])).resolve()
    assert (
        descriptor["sha256"] == "fc340e75df0db016a7caf857baa236e559ef5ef34f5dc212fa1b0ab0b842c953"
    )


def test_frozen_allocation_loader_maps_caps_and_checks_duplicate_representations(
    tmp_path: Path,
) -> None:
    config = copy.deepcopy(load_config(DEFAULT_CONFIG_PATH))
    config["census"]["expected_rows"] = 2
    census = pd.DataFrame({"period": ["2018-01", "2018-01"], "point_cap": [0.1, 0.2]})
    records = pd.DataFrame(
        [
            {
                "role": "primary_oot",
                "period": "2018-01",
                "window_id": "w",
                "candidate_id": "point-point_cap_frontier-p-2018-01",
                "comparator_rule": "point_cap_frontier",
                "policy_label": "point_cap_frontier-0.1",
                "paired_policy_id": "p",
                "frontier_cap": 0.1,
            },
            {
                "role": "primary_oot",
                "period": "2018-01",
                "window_id": "w",
                "candidate_id": "point-c0_same_numeric_cap-p-2018-01",
                "comparator_rule": "c0_same_numeric_cap",
                "policy_label": "c0_same_numeric_cap-0.1",
                "paired_policy_id": "p",
                "frontier_cap": 0.1,
            },
            {
                "role": "primary_oot",
                "period": "2018-01",
                "window_id": "w",
                "candidate_id": "point-point_cap_frontier-p-2018-01",
                "comparator_rule": "point_cap_frontier",
                "policy_label": "point_cap_frontier-0.2",
                "paired_policy_id": "p",
                "frontier_cap": 0.2,
            },
        ]
    )
    allocations: list[dict[str, Any]] = []
    for rule, cap, shift in (
        ("point_cap_frontier", 0.1, 0.0),
        ("c0_same_numeric_cap", 0.1, 5.0e-8),
        ("point_cap_frontier", 0.2, 0.0),
    ):
        for candidate_id, exposure, point, payoff in (
            ("a", 60.0 + shift, 0.05, 0.10),
            ("b", 40.0 - shift, 0.15, 0.20),
        ):
            allocations.append(
                {
                    "role": "primary_oot",
                    "period": "2018-01",
                    "window_id": "w",
                    "candidate_id": f"point-{rule}-p-2018-01",
                    "comparator_rule": rule,
                    "policy_label": f"{rule}-{cap}",
                    "paired_policy_id": "p",
                    "frontier_cap": cap,
                    "id": candidate_id,
                    "exposure": exposure,
                    "pd_point": point,
                    "expected_payoff_rate": payoff,
                }
            )
    allocations_path = tmp_path / "allocations.parquet"
    records_path = tmp_path / "records.parquet"
    pd.DataFrame(allocations).to_parquet(allocations_path, index=False)
    records.to_parquet(records_path, index=False)
    reference = _load_frozen_allocation_reference(
        allocations_path,
        records_path,
        census,
        config=config,
    )
    assert len(reference.vectors) == 2
    assert reference.diagnostics["maximum_duplicate_exposure_spread_dollars"] == pytest.approx(
        5.0e-8
    )
    vector = reference.vectors[("2018-01", 0.1)]
    fields = _frozen_allocation_reconciliation_fields(
        vector,
        candidate_ids=("a", "b", "c"),
        raw_exposure=np.array([60.0, 40.0, 0.0]),
        point=np.array([0.05, 0.15, 0.25]),
        objective=np.array([0.10, 0.20, 0.30]),
        raw_objective=14.0,
        raw_weighted_point=0.09,
        v1_objective=14.0,
        v1_weighted_point=0.09,
        budget=100.0,
        tolerances=config["tolerances"],
    )
    assert fields["frozen_allocation_reconciliation_passed"] is True
    broken = pd.DataFrame(allocations)
    mask = broken["comparator_rule"].eq("c0_same_numeric_cap") & broken["id"].eq("a")
    broken.loc[mask, "exposure"] += 1.0e-3
    broken_path = tmp_path / "broken_allocations.parquet"
    broken.to_parquet(broken_path, index=False)
    with pytest.raises(RuntimeError, match="representations disagree"):
        _load_frozen_allocation_reference(
            broken_path,
            records_path,
            census,
            config=config,
        )
    missing_positive = pd.DataFrame(allocations)
    missing_mask = missing_positive["comparator_rule"].eq("c0_same_numeric_cap") & missing_positive[
        "id"
    ].eq("a")
    missing_positive = missing_positive.loc[~missing_mask]
    missing_positive_path = tmp_path / "missing_positive_allocations.parquet"
    missing_positive.to_parquet(missing_positive_path, index=False)
    with pytest.raises(RuntimeError, match="representations disagree"):
        _load_frozen_allocation_reference(
            missing_positive_path,
            records_path,
            census,
            config=config,
        )


def test_fresh_basis_ranges_must_cover_broad_and_development_support() -> None:
    config = load_config(DEFAULT_CONFIG_PATH)
    central = pd.DataFrame(
        {
            "period": ["2018-01"] * 5,
            "point_cap": [0.04, 0.05, 0.08, 0.12, 0.13],
            "fresh_basis_cap_lower": [0.04, 0.05, 0.07, 0.10, 0.12],
            "fresh_basis_cap_upper": [0.05, 0.07, 0.10, 0.12, 0.13],
            "basis_cap_lower": [0.04, 0.05, 0.07, 0.10, 0.12],
            "basis_cap_upper": [0.05, 0.07, 0.10, 0.12, 0.13],
            "is_development_support_lower": [True, False, False, False, False],
            "is_development_support_upper": [False, False, False, False, True],
        }
    )
    passed = _rhs_basis_range_coverage_diagnostics(central, config=config)
    assert bool(passed.loc[0, "fresh_rhs_basis_range_coverage_passed"]) is True
    assert float(passed.loc[0, "maximum_positive_gap"]) == pytest.approx(0.0)
    assert float(passed.loc[0, "maximum_raw_positive_gap"]) == pytest.approx(0.0)
    assert float(passed.loc[0, "required_coverage_lower"]) == pytest.approx(0.04)
    assert float(passed.loc[0, "required_coverage_upper"]) == pytest.approx(0.13)
    broken = central.copy()
    broken.loc[2, "fresh_basis_cap_lower"] = 0.071
    failed = _rhs_basis_range_coverage_diagnostics(broken, config=config)
    assert bool(failed.loc[0, "fresh_rhs_basis_range_coverage_passed"]) is False
    assert float(failed.loc[0, "maximum_positive_gap"]) == pytest.approx(0.001)
    assert float(failed.loc[0, "maximum_raw_positive_gap"]) == pytest.approx(0.001)
    sub_tolerance = central.copy()
    sub_tolerance.loc[2, "fresh_basis_cap_lower"] = 0.07 + 5.0e-11
    tolerated = _rhs_basis_range_coverage_diagnostics(sub_tolerance, config=config)
    assert bool(tolerated.loc[0, "fresh_rhs_basis_range_coverage_passed"]) is True
    assert float(tolerated.loc[0, "maximum_positive_gap"]) == pytest.approx(0.0)
    assert float(tolerated.loc[0, "maximum_raw_positive_gap"]) == pytest.approx(5.0e-11)


def test_bilateral_probe_plan_has_registered_left_right_midpoint_path_stresses() -> None:
    plan = breakpoint_probe_plan(np.array([0.05, 0.07, 0.10]))
    assert len(plan) == 4
    assert plan == (
        {"point_cap": 0.05, "probe_side": "right", "seed_cap": 0.060000000000000005},
        {"point_cap": 0.07, "probe_side": "left", "seed_cap": 0.060000000000000005},
        {"point_cap": 0.07, "probe_side": "right", "seed_cap": 0.085},
        {"point_cap": 0.10, "probe_side": "left", "seed_cap": 0.085},
    )


@pytest.mark.parametrize(
    ("cost", "row_lower", "row_upper", "status", "sign"),
    [
        (1.0, -highspy.kHighsInf, 0.5, "upper", 1.0),
        (-1.0, 0.5, highspy.kHighsInf, "lower", -1.0),
    ],
)
def test_row_dual_sign_convention_is_audited(
    cost: float,
    row_lower: float,
    row_upper: float,
    status: str,
    sign: float,
) -> None:
    session, solution = _synthetic_session(
        cost=np.array([cost]),
        matrix=np.array([[1.0]]),
        row_lower=np.array([row_lower]),
        row_upper=np.array([row_upper]),
    )
    audit = _audit(session, solution, row_names=("one_sided",))
    row = audit.row_details[0]
    assert row["basis_status"] == status
    assert sign * float(row["row_dual"]) > 0.0
    assert audit.summary["maximum_scaled_row_dual_sign_violation"] == 0.0


def test_fixed_equality_row_is_recorded_but_excluded_from_warning() -> None:
    session, solution = _synthetic_session(
        cost=np.array([1.0]),
        matrix=np.array([[1.0]]),
        row_lower=np.array([0.5]),
        row_upper=np.array([0.5]),
    )
    audit = _audit(session, solution, row_names=("budget_equality",))
    row = audit.row_details[0]
    assert row["is_equality"] is True
    assert row["is_movable_nonbasic"] is False
    assert row["is_near_zero_nonbasic"] is False
    assert not any(item["variable_kind"] == "row_activity" for item in audit.flagged_nonbasic)


def test_full_basis_summary_persists_every_highs_status_count_separately() -> None:
    session, solution = _synthetic_session(
        cost=np.array([1.0, 2.0]),
        matrix=np.array([[1.0, 1.0]]),
        row_lower=np.array([1.0]),
        row_upper=np.array([1.0]),
    )
    audit = _audit(session, solution, row_names=("fixed_sum",))
    summary = audit.summary
    assert sum(
        int(summary[field])
        for field in (
            "basic_columns",
            "lower_nonbasic_columns",
            "upper_nonbasic_columns",
            "zero_nonbasic_columns",
            "generic_nonbasic_columns",
        )
    ) == int(summary["columns"])
    assert sum(
        int(summary[field])
        for field in (
            "basic_rows",
            "lower_nonbasic_rows",
            "upper_nonbasic_rows",
            "zero_nonbasic_rows",
            "generic_nonbasic_rows",
        )
    ) == int(summary["rows"])
    assert int(summary["unsupported_nonbasic_columns"]) == (
        int(summary["zero_nonbasic_columns"]) + int(summary["generic_nonbasic_columns"])
    )


def test_scaled_row_dual_and_trigger_are_invariant_to_objective_units() -> None:
    audits: list[FullBasisAudit] = []
    for multiplier in (1.0, 1.0e6):
        session, solution = _synthetic_session(
            cost=np.array([multiplier]),
            matrix=np.array([[1.0]]),
            row_lower=np.array([-highspy.kHighsInf]),
            row_upper=np.array([0.5]),
        )
        audits.append(_audit(session, solution, row_names=("upper",)))
    first, second = (item.row_details[0] for item in audits)
    assert float(second["row_dual_reference_scale"]) == pytest.approx(
        1.0e6 * float(first["row_dual_reference_scale"])
    )
    assert (
        float(second["absolute_row_dual"]) / float(second["row_dual_reference_scale"])
    ) == pytest.approx(float(first["absolute_row_dual"]) / float(first["row_dual_reference_scale"]))
    assert second["is_near_zero_nonbasic"] == first["is_near_zero_nonbasic"]


def test_scaled_column_reduced_cost_is_invariant_to_objective_units() -> None:
    audits: list[FullBasisAudit] = []
    for multiplier in (1.0, 1.0e6):
        session, solution = _synthetic_session(
            cost=multiplier * np.array([1.0, 2.0]),
            matrix=np.array([[1.0, 1.0]]),
            row_lower=np.array([1.0]),
            row_upper=np.array([1.0]),
        )
        audits.append(_audit(session, solution, row_names=("fixed_sum",)))
    assert audits[1].summary["minimum_scaled_nonbasic_column_reduced_cost"] == pytest.approx(
        audits[0].summary["minimum_scaled_nonbasic_column_reduced_cost"]
    )
    assert (
        audits[1].summary["near_zero_nonbasic_columns"]
        == audits[0].summary["near_zero_nonbasic_columns"]
    )


def test_conditional_range_uses_raw_objective_and_reports_epsilon_mobility() -> None:
    session, solution = _synthetic_session(
        cost=np.array([1.0, 1.0]),
        matrix=np.array([[1.0, 1.0]]),
        row_lower=np.array([1.0]),
        row_upper=np.array([1.0]),
    )
    result = optimal_face_range(
        cast(Any, session),
        cast(Any, solution),
        variable_kind="column",
        variable_index=0,
        objective_absolute_tolerance=1.0e-7,
        objective_relative_tolerance=1.0e-12,
        time_limit=30,
        threads=1,
        dual_feasibility_tolerance=1.0e-9,
        primal_feasibility_tolerance=1.0e-9,
    )
    assert result["raw_primary_objective"] == pytest.approx(1.0)
    assert result["objective_face_epsilon"] == pytest.approx(1.0e-7)
    assert result["minimum_value"] == pytest.approx(0.0, abs=1.0e-8)
    assert result["maximum_value"] == pytest.approx(1.0, abs=1.0e-8)
    assert result["value_range"] == pytest.approx(1.0, abs=2.0e-8)
    assert result["minimum_solver_run_time_seconds"] >= 0.0
    assert result["maximum_solver_run_time_seconds"] >= 0.0
    assert result["minimum_maximum_row_bound_violation"] <= 1.0e-9
    assert result["maximum_maximum_row_bound_violation"] <= 1.0e-9


def test_conditional_range_contains_fixed_base_and_reports_zero_mobility() -> None:
    session, solution = _synthetic_session(
        cost=np.array([1.0]),
        matrix=np.array([[1.0]]),
        row_lower=np.array([0.5]),
        row_upper=np.array([0.5]),
    )
    result = optimal_face_range(
        cast(Any, session),
        cast(Any, solution),
        variable_kind="column",
        variable_index=0,
        objective_absolute_tolerance=1.0e-7,
        objective_relative_tolerance=1.0e-12,
        time_limit=30,
        threads=1,
        dual_feasibility_tolerance=1.0e-9,
        primal_feasibility_tolerance=1.0e-9,
    )
    assert result["minimum_value"] == pytest.approx(0.5)
    assert result["base_value"] == pytest.approx(0.5)
    assert result["maximum_value"] == pytest.approx(0.5)
    assert result["raw_value_range"] == pytest.approx(0.0)
    assert result["value_range"] == pytest.approx(0.0)
    assert result["maximum_range_consistency_violation"] <= 1.0e-9


def test_conditional_range_persists_primary_reconciliation_failure() -> None:
    session, solution = _synthetic_session(
        cost=np.array([1.0]),
        matrix=np.array([[1.0]]),
        row_lower=np.array([0.5]),
        row_upper=np.array([0.5]),
    )
    drifted_solution = SimpleNamespace(objective_value=float(solution.objective_value) + 1.0e-3)
    result = optimal_face_range(
        cast(Any, session),
        cast(Any, drifted_solution),
        variable_kind="column",
        variable_index=0,
        objective_absolute_tolerance=1.0e-7,
        objective_relative_tolerance=1.0e-12,
        time_limit=30,
        threads=1,
        dual_feasibility_tolerance=1.0e-9,
        primal_feasibility_tolerance=1.0e-9,
    )
    assert result["solution_to_raw_primary_objective_difference"] == pytest.approx(1.0e-3)
    assert result["minimum_value"] == pytest.approx(0.5)
    assert result["maximum_value"] == pytest.approx(0.5)


def test_point_lp_raw_policy_constraints_are_explicitly_reconciled() -> None:
    frame = pd.DataFrame(
        {
            "loan_amnt": [60.0, 50.0, 40.0, 30.0, 20.0],
            "purpose": ["a", "a", "b", "b", "c"],
        }
    )
    session = PointPortfolioSession(
        frame,
        point_score=np.array([0.03, 0.06, 0.09, 0.12, 0.15]),
        objective_rate=np.array([0.031, 0.081, 0.044, 0.103, 0.017]),
        budget=100.0,
        purpose_cap=0.6,
        threads=1,
    )
    solution = session.solve(0.09)
    audit = audit_full_basis(
        session,
        solution,
        dual_absolute_tolerance=1.0e-7,
        dual_relative_tolerance=1.0e-12,
        primal_tolerance=1.0e-9,
        row_names=("budget_equality", "point_risk_cap", "purpose:a", "purpose:b", "purpose:c"),
    )
    feasibility = _policy_feasibility_fields(audit, budget=100.0)
    assert abs(feasibility["raw_budget_equality_residual_dollars"]) <= 1.0e-9
    assert feasibility["raw_risk_cap_violation_dollars"] <= 1.0e-9
    assert feasibility["raw_maximum_purpose_cap_violation_dollars"] <= 1.0e-9
    assert feasibility["maximum_normalized_policy_constraint_violation"] <= 1.0e-10


def _summary_frames(
    *, unsupported_columns: int = 0, warning_without_mobility: bool = False
) -> dict[str, pd.DataFrame]:
    base = {
        "period": "2018-01",
        "is_period_basis_breakpoint": True,
        "basis_valid": True,
        "basis_dimension_valid": True,
        "value_valid": True,
        "dual_valid": True,
        "unsupported_nonbasic_columns": unsupported_columns,
        "unsupported_movable_nonbasic_rows": 0,
        "maximum_scaled_dual_sign_violation": 0.0,
        "objective_reconciliation_error": 0.0,
        "raw_objective_internal_reconciliation_error": 0.0,
        "solution_to_raw_solver_objective_error": 0.0,
        "maximum_normalized_policy_constraint_violation": 0.0,
        "maximum_primal_bound_violation": 0.0,
        "near_zero_nonbasic_columns": int(warning_without_mobility),
        "near_zero_nonbasic_rows": 0,
        "minimum_absolute_nonbasic_column_reduced_cost": 1.0,
        "minimum_absolute_nonbasic_row_dual": 1.0,
        "maximum_dual_sign_violation": 0.0,
    }
    comparison = {
        "maximum_pairwise_allocation_distance": 0.0,
        "allocation_difference_without_same_cap_epsilon_mobility": False,
        "allocation_difference_cooccurs_with_same_cap_epsilon_mobility": False,
        "lateral_objective_discrepancy": False,
        "lateral_weighted_point_discrepancy": False,
    }
    freeze = {
        "frozen_allocation_reconciliation_passed": True,
        "fresh_vs_frozen_l1_exposure_dollars": 0.0,
        "fresh_vs_frozen_normalized_l1_exposure": 0.0,
        "fresh_vs_frozen_expected_objective_difference": 0.0,
        "fresh_vs_frozen_weighted_point_difference": 0.0,
    }
    coverage = {
        "fresh_rhs_basis_range_coverage_passed": True,
        "maximum_positive_gap": 0.0,
        "maximum_raw_positive_gap": 0.0,
        "maximum_cap_containment_violation": 0.0,
    }
    flags = (
        pd.DataFrame(
            [
                {
                    "period": "2018-01",
                    "point_cap": 0.07,
                    "variable_kind": "column",
                    "variable_index": 0,
                },
                {
                    "period": "2018-01",
                    "point_cap": 0.07,
                    "variable_kind": "column",
                    "variable_index": 0,
                },
            ]
        )
        if warning_without_mobility
        else pd.DataFrame(columns=["period", "point_cap", "variable_kind", "variable_index"])
    )
    face = {
        "period": "2018-01",
        "point_cap": 0.07,
        "variable_kind": "column",
        "variable_index": 0,
        "objective_band_passed": True,
        "face_range_consistency_passed": True,
        "minimum_maximum_column_bound_violation": 0.0,
        "minimum_maximum_row_bound_violation": 0.0,
        "maximum_maximum_column_bound_violation": 0.0,
        "maximum_maximum_row_bound_violation": 0.0,
        "primary_objective_reconciliation_passed": True,
        "minimum_solver_run_time_seconds": 0.0,
        "maximum_solver_run_time_seconds": 0.0,
        "epsilon_near_optimal_mobility_detected": False,
    }
    return {
        "central_basis_diagnostics": pd.DataFrame([base]),
        "lateral_probe_diagnostics": pd.DataFrame([base]),
        "breakpoint_comparisons": pd.DataFrame([comparison]),
        "frozen_allocation_reconciliation": pd.DataFrame([freeze] * 7_297),
        "fresh_rhs_basis_range_coverage": pd.DataFrame([coverage] * 15),
        "flagged_nonbasic_variables": flags,
        "optimal_face_ranges": (
            pd.DataFrame([face], columns=list(FACE_COLUMNS))
            if warning_without_mobility
            else pd.DataFrame(columns=list(FACE_COLUMNS))
        ),
    }


def test_strict_certificate_is_gated_by_unsupported_nonbasic_status() -> None:
    config = load_config(DEFAULT_CONFIG_PATH)
    strict = _summary(_summary_frames(), config)
    failed = _summary(_summary_frames(unsupported_columns=1), config)
    assert strict["certification_status"] == (
        "strict_full_basis_freeze_and_fresh_rhs_range_coverage_numeric_certificate"
    )
    assert strict["strict_numeric_certificate_gate_passed"] is True
    assert strict["finite_grid_numerical_uniqueness_gate_passed"] is True
    assert strict["fresh_rhs_basis_range_coverage_gate_passed"] is True
    assert failed["certification_status"] == "numerical_contract_failed_claim_blocked"
    assert failed["strict_numeric_certificate_gate_passed"] is False
    assert failed["fresh_rhs_basis_range_coverage_gate_passed"] is True
    assert failed["scientific_stop_flags"]["basis_contract_failure"] is True


def test_coordinate_warnings_cannot_open_global_uniqueness_gate() -> None:
    config = load_config(DEFAULT_CONFIG_PATH)
    result = _summary(_summary_frames(warning_without_mobility=True), config)
    assert result["certification_status"] == (
        "registered_warnings_without_global_face_diameter_claim_inconclusive"
    )
    assert result["strict_numeric_certificate_gate_passed"] is False
    assert result["finite_grid_numerical_uniqueness_gate_passed"] is False
    assert result["fresh_rhs_basis_range_coverage_gate_passed"] is True
    assert result["global_optimal_face_diameter_claim_made"] is False
    assert (
        result["scientific_stop_flags"]["registered_warning_without_global_face_diameter"] is True
    )


def test_finite_secondary_primal_failure_is_retained_and_claim_gated() -> None:
    config = load_config(DEFAULT_CONFIG_PATH)
    frames = _summary_frames(warning_without_mobility=True)
    frames["optimal_face_ranges"].loc[0, "minimum_maximum_row_bound_violation"] = 1.0e-6
    result = _summary(frames, config)
    assert result["certification_status"] == "numerical_contract_failed_claim_blocked"
    assert result["scientific_stop_flags"]["face_primal_feasibility_failure"] is True


@pytest.mark.parametrize(
    ("frame_name", "column", "stop_flag", "rhs_gate"),
    [
        (
            "frozen_allocation_reconciliation",
            "frozen_allocation_reconciliation_passed",
            "frozen_allocation_reconciliation_failure",
            True,
        ),
        (
            "fresh_rhs_basis_range_coverage",
            "fresh_rhs_basis_range_coverage_passed",
            "fresh_rhs_basis_range_coverage_failure",
            False,
        ),
    ],
)
def test_freeze_and_rhs_range_coverage_are_strict_certificate_gates(
    frame_name: str, column: str, stop_flag: str, rhs_gate: bool
) -> None:
    config = load_config(DEFAULT_CONFIG_PATH)
    frames = _summary_frames()
    frames[frame_name].loc[0, column] = False
    result = _summary(frames, config)
    assert result["certification_status"] == "numerical_contract_failed_claim_blocked"
    assert result["strict_numeric_certificate_gate_passed"] is False
    assert result["finite_grid_numerical_uniqueness_gate_passed"] is False
    assert result["fresh_rhs_basis_range_coverage_gate_passed"] is rhs_gate
    assert result["scientific_stop_flags"][stop_flag] is True


def test_exposure_distance_is_symmetric_and_normalized() -> None:
    left = np.array([60.0, 40.0, 0.0])
    right = np.array([50.0, 40.0, 10.0])
    assert normalized_exposure_distance(left, right) == pytest.approx(0.1)
    assert normalized_exposure_distance(right, left) == pytest.approx(0.1)


def test_lateral_allocation_difference_records_only_same_cap_mobility_cooccurrence() -> None:
    config = load_config(DEFAULT_CONFIG_PATH)
    comparisons = pd.DataFrame(
        [
            {
                "period": "2018-01",
                "point_cap": 0.07,
                "maximum_pairwise_allocation_distance": 1.0e-4,
                "maximum_pairwise_objective_difference": 0.0,
                "maximum_pairwise_weighted_point_difference": 0.0,
            }
        ]
    )
    no_mobility = pd.DataFrame(
        columns=["period", "point_cap", "epsilon_near_optimal_mobility_detected"]
    )
    without_mobility = _reconcile_breakpoint_comparisons(
        comparisons, no_mobility, tolerances=config["tolerances"]
    )
    assert (
        bool(without_mobility.loc[0, "allocation_difference_without_same_cap_epsilon_mobility"])
        is True
    )
    mobility = pd.DataFrame(
        [
            {
                "period": "2018-01",
                "point_cap": 0.07,
                "epsilon_near_optimal_mobility_detected": True,
            }
        ]
    )
    cooccurring = _reconcile_breakpoint_comparisons(
        comparisons, mobility, tolerances=config["tolerances"]
    )
    assert (
        bool(cooccurring.loc[0, "allocation_difference_without_same_cap_epsilon_mobility"]) is False
    )
    assert (
        bool(cooccurring.loc[0, "allocation_difference_cooccurs_with_same_cap_epsilon_mobility"])
        is True
    )


def test_output_paths_are_contained_and_immutable(tmp_path: Path) -> None:
    config = copy.deepcopy(load_config(DEFAULT_CONFIG_PATH))
    config["run_tag"] = "optimal-face-v2-test"
    preflight = preflight_output_paths(config, repo_root=tmp_path)
    assert not preflight.data_dir.exists()
    assert not preflight.model_dir.exists()
    paths = prepare_output_paths(config, repo_root=tmp_path)
    assert paths.data_dir.is_relative_to(tmp_path)
    assert paths.model_dir.is_relative_to(tmp_path)
    with pytest.raises(FileExistsError, match="already exists"):
        preflight_output_paths(config, repo_root=tmp_path)
    with pytest.raises(FileExistsError, match="already exists"):
        prepare_output_paths(config, repo_root=tmp_path)
