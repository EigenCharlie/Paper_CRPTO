from __future__ import annotations

import copy
import inspect
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.experiments import run_ijds_set_preserving_embedding_sensitivity_v1d as runner
from src.ijds_challengers.set_preserving_embedding_v1d import (
    PERSISTED_SCHEMA_DTYPES,
    expected_v1d_persisted_schemas,
    prepare_v1d_evaluated_portfolios,
    prepare_v1d_window_sharp_contrasts,
    validate_v1d_persisted_numeric_finiteness,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/experiments/ijds_set_preserving_embedding_sensitivity_2026-07-30_v1d.yaml"


def _git(repo: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=check,
        capture_output=True,
        text=True,
    )


def test_v1d_delta_inherits_science_but_uses_fresh_p2_a2_b2() -> None:
    config = runner.load_v1d_config(CONFIG)
    if config["protocol_status"] != (
        "retrospective_post_inspection_v1c_no_go_recovery_phase_b_only"
    ):
        pytest.fail("V1d lost its retrospective NO-GO recovery status.")
    if len(config["git_transport"]["protocol_to_source_paths"]) != 11:
        pytest.fail("V1d does not reanchor exactly eleven V1a files at A2.")
    if len(config["git_transport"]["source_to_evaluation_paths"]) != 9:
        pytest.fail("V1d does not retain exactly nine compact B2 outputs.")
    if any(
        "2026-07-29-v1c" in path for path in config["git_transport"]["source_to_evaluation_paths"]
    ):
        pytest.fail("V1d B2 paths overlap the preserved V1c output directories.")
    if (
        config["v1c_no_go"]["outputs_are_evidence"] is not False
        or config["inspection_context"]["v1c_phase_b_outputs_reused"] is not False
    ):
        pytest.fail("V1d obscures or reuses the V1c NO-GO outputs.")


def test_v1d_base_config_descriptor_is_fail_closed(tmp_path: Path) -> None:
    text = CONFIG.read_text(encoding="utf-8").replace("bytes: 14468", "bytes: 14469", 1)
    mutated = tmp_path / "mutated.yaml"
    mutated.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="base V1c descriptor"):
        runner.load_v1d_config(mutated)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("outputs_are_evidence: false", "outputs_are_evidence: true", "NO-GO"),
        (
            'drop_columns: ["realized_payoff_exact"]',
            'drop_columns: ["realized_payoff_lower"]',
            "persistence contract",
        ),
        (
            'windows_requirement: "effective_git_core_longpaths_true"',
            'windows_requirement: "optional"',
            "long-path gate",
        ),
    ],
)
def test_v1d_delta_rejects_no_go_persistence_or_windows_drift(
    tmp_path: Path, old: str, new: str, message: str
) -> None:
    mutated = tmp_path / "mutated.yaml"
    mutated.write_text(CONFIG.read_text(encoding="utf-8").replace(old, new, 1), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        runner.load_v1d_config(mutated)


def test_windows_longpaths_gate_occurs_before_outcomes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    non_windows = runner.windows_longpaths_preflight(repo, platform_name="posix")
    if non_windows != {
        "platform": "non_windows",
        "status": "not_applicable",
        "checked_before_outcomes": True,
    }:
        pytest.fail(f"Unexpected non-Windows preflight: {non_windows}.")
    with pytest.raises(RuntimeError, match=r"core\.longpaths=true"):
        runner.windows_longpaths_preflight(repo, platform_name="nt")
    _git(repo, "config", "core.longpaths", "true")
    windows = runner.windows_longpaths_preflight(repo, platform_name="nt")
    if windows["status"] != "effective_git_core_longpaths_true":
        pytest.fail(f"Windows long-path authority was not retained: {windows}.")
    source = inspect.getsource(runner.run_phase_b)
    if source.index("windows_longpaths_preflight(root)") > source.index("v1c._tag_authority"):
        pytest.fail("V1d traverses source-tag paths before the Windows long-path gate.")


def test_v1d_implementation_binding_is_v1c_superset_plus_v1d_delta() -> None:
    expected = tuple(
        dict.fromkeys(
            (
                *runner.v1c.IMPLEMENTATION_PATHS,
                runner.CONFIG_RELATIVE,
                runner.PROTOCOL_RELATIVE,
                runner.NO_GO_RELATIVE,
                Path("scripts/experiments/run_ijds_set_preserving_embedding_sensitivity_v1d.py"),
                Path("src/ijds_challengers/set_preserving_embedding_v1d.py"),
            )
        )
    )
    if expected != runner.IMPLEMENTATION_PATHS:
        pytest.fail("V1d weakened or expanded the exact V1c-plus-V1d implementation lock.")


def _small_contract() -> dict[str, object]:
    contract = copy.deepcopy(runner.load_v1d_config(CONFIG)["persistence_contract"])
    contract["evaluated_portfolios"]["exact_missing_rows_observed_in_v1c"] = 2
    contract["evaluated_portfolios"]["exact_resolved_rows_observed_in_v1c"] = 2
    contract["numeric_finiteness"]["expected_missing_each"] = 2
    contract["pooled_window_contrasts"]["source_period_missing_rows_observed_in_v1c"] = 1
    contract["exact_persisted_schema_rows"] = {
        "evaluated_portfolios": 4,
        "monthly_sharp_contrasts": 1,
        "window_sharp_contrasts": 1,
        "metric_direction_census": 1,
        "outcome_join_audit": 1,
    }
    return contract


def _locked_frame(key: str, rows: int) -> pd.DataFrame:
    data: dict[str, pd.Series] = {}
    for name, dtype in PERSISTED_SCHEMA_DTYPES[key]:
        if dtype == "str":
            data[name] = pd.Series(["locked"] * rows, dtype="str")
        elif dtype == "float64":
            data[name] = pd.Series(np.ones(rows), dtype="float64")
        elif dtype == "int64":
            data[name] = pd.Series(np.ones(rows), dtype="int64")
        elif dtype == "bool":
            data[name] = pd.Series([True] * rows, dtype="bool")
        else:
            pytest.fail(f"Unsupported locked synthetic dtype: {dtype}.")
    return pd.DataFrame(data)


def _evaluated_source() -> pd.DataFrame:
    frame = _locked_frame("evaluated_portfolios", 4)
    frame["frontier_ruler"] = pd.Series(
        [
            "objective_matched",
            "normalized_score",
            "objective_matched",
            "normalized_score",
        ],
        dtype="str",
    )
    frame["frontier_cap"] = pd.Series([np.nan, 1.0, np.nan, 2.0], dtype="float64")
    frame["objective_target"] = pd.Series([10.0, np.nan, 20.0, np.nan], dtype="float64")
    frame["risk_tolerance"] = pd.Series([np.nan, 0.1, np.nan, 0.2], dtype="float64")
    frame["realized_payoff_lower"] = pd.Series([1.0, 2.0, 3.0, 4.0], dtype="float64")
    frame["realized_payoff_upper"] = pd.Series([1.0, 5.0, 3.0, 8.0], dtype="float64")
    frame["n_unresolved_positive_exposure"] = pd.Series([0, 1, 0, 2], dtype="int64")
    frame.insert(
        frame.columns.get_loc("weighted_default_lower"),
        "realized_payoff_exact",
        pd.Series([1.0, np.nan, 3.0, np.nan], dtype="float64"),
    )
    if len(frame.columns) != 50:
        pytest.fail(f"Synthetic evaluated source has {len(frame.columns)} columns.")
    return frame


def _persisted_frames() -> tuple[dict[str, pd.DataFrame], dict[str, object]]:
    contract = _small_contract()
    evaluated = prepare_v1d_evaluated_portfolios(_evaluated_source(), contract=contract)
    monthly = _locked_frame("monthly_sharp_contrasts", 1)
    monthly["scope"] = pd.Series(["primary_month"], dtype="str")
    monthly["period"] = pd.Series(["2016-04"], dtype="str")
    window_source = _locked_frame("window_sharp_contrasts", 1)
    window_source["scope"] = pd.Series(["pooled_primary_window"], dtype="str")
    window_source.insert(2, "period", pd.Series([None], dtype="object"))
    window = prepare_v1d_window_sharp_contrasts(window_source, contract=contract)
    directions = _locked_frame("metric_direction_census", 1)
    directions["metric"] = pd.Series(["standardized_payoff"], dtype="str")
    audit = _locked_frame("outcome_join_audit", 1)
    audit["role"] = pd.Series(["primary_oot"], dtype="str")
    return (
        {
            "evaluated_portfolios": evaluated,
            "monthly_sharp_contrasts": monthly,
            "window_sharp_contrasts": window,
            "metric_direction_census": directions,
            "outcome_join_audit": audit,
        },
        contract,
    )


def test_v1d_drops_exact_and_pooled_period_then_accepts_exact_schemas() -> None:
    frames, contract = _persisted_frames()
    if "realized_payoff_exact" in frames["evaluated_portfolios"]:
        pytest.fail("V1d retained the nullable exact payoff field.")
    if "period" in frames["window_sharp_contrasts"]:
        pytest.fail("V1d retained the all-null pooled period field.")
    if "period" not in frames["monthly_sharp_contrasts"]:
        pytest.fail("V1d removed period from the monthly output.")
    validate_v1d_persisted_numeric_finiteness(frames, contract=contract)
    schemas = expected_v1d_persisted_schemas(contract)
    if list(schemas["evaluated_portfolios"]["dtypes"].items()) != list(
        PERSISTED_SCHEMA_DTYPES["evaluated_portfolios"]
    ):
        pytest.fail("V1d exact schema descriptor lost ordered dtype authority.")


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("frontier_cap", "1", "string/boolean"),
        ("frontier_cap", True, "string/boolean"),
        ("frontier_cap", np.inf, "non-finite applicable"),
    ],
)
def test_structural_fields_reject_string_bool_and_infinity(
    column: str, value: object, message: str
) -> None:
    frames, contract = _persisted_frames()
    evaluated = frames["evaluated_portfolios"].copy()
    applicable_index = evaluated.index[evaluated["frontier_ruler"].eq("normalized_score")][0]
    if isinstance(value, (str, bool)):
        evaluated[column] = evaluated[column].astype(object)
    evaluated.loc[applicable_index, column] = value
    frames["evaluated_portfolios"] = evaluated
    with pytest.raises(RuntimeError, match=message):
        validate_v1d_persisted_numeric_finiteness(frames, contract=contract)


@pytest.mark.parametrize("value", ["missing", True])
def test_structural_expected_missing_slots_reject_coercible_or_invalid_values(
    value: object,
) -> None:
    frames, contract = _persisted_frames()
    evaluated = frames["evaluated_portfolios"].copy()
    missing_index = evaluated.index[evaluated["frontier_ruler"].eq("objective_matched")][0]
    evaluated["frontier_cap"] = evaluated["frontier_cap"].astype(object)
    evaluated.loc[missing_index, "frontier_cap"] = value
    frames["evaluated_portfolios"] = evaluated
    with pytest.raises(RuntimeError, match=r"string/boolean|NA pattern"):
        validate_v1d_persisted_numeric_finiteness(frames, contract=contract)


@pytest.mark.parametrize(
    "key",
    [
        "evaluated_portfolios",
        "monthly_sharp_contrasts",
        "window_sharp_contrasts",
        "metric_direction_census",
        "outcome_join_audit",
    ],
)
@pytest.mark.parametrize("value", [np.nan, np.inf])
def test_each_persisted_output_fails_on_undeclared_nan_or_infinity(key: str, value: float) -> None:
    frames, contract = _persisted_frames()
    mutated = frames[key].copy()
    numeric_candidates = [
        (name, dtype)
        for name, dtype in PERSISTED_SCHEMA_DTYPES[key]
        if dtype in {"float64", "int64"}
        and name not in {"frontier_cap", "objective_target", "risk_tolerance"}
    ]
    target, dtype = next(
        ((name, dtype) for name, dtype in numeric_candidates if dtype == "float64"),
        numeric_candidates[0],
    )
    if dtype == "int64":
        mutated[target] = mutated[target].astype("float64")
    mutated.loc[mutated.index[0], target] = value
    frames[key] = mutated
    with pytest.raises(RuntimeError, match=r"non-finite|missing|schema|dtype"):
        validate_v1d_persisted_numeric_finiteness(frames, contract=contract)


@pytest.mark.parametrize(
    "key",
    [
        "evaluated_portfolios",
        "monthly_sharp_contrasts",
        "window_sharp_contrasts",
        "metric_direction_census",
        "outcome_join_audit",
    ],
)
@pytest.mark.parametrize("value", ["1", True])
def test_each_persisted_output_rejects_string_or_bool_in_numeric_field(
    key: str, value: object
) -> None:
    frames, contract = _persisted_frames()
    mutated = frames[key].copy()
    target = next(
        name
        for name, dtype in PERSISTED_SCHEMA_DTYPES[key]
        if dtype in {"float64", "int64"}
        and name not in {"frontier_cap", "objective_target", "risk_tolerance"}
    )
    mutated[target] = mutated[target].astype(object)
    mutated.loc[mutated.index[0], target] = value
    frames[key] = mutated
    with pytest.raises(RuntimeError, match=r"schema|dtype|string/boolean"):
        validate_v1d_persisted_numeric_finiteness(frames, contract=contract)


@pytest.mark.parametrize(
    "column",
    [
        "realized_payoff_exact",
        "realized_payoff_lower",
        "realized_payoff_upper",
        "n_unresolved_positive_exposure",
    ],
)
@pytest.mark.parametrize("value", ["1", True])
def test_payoff_repair_rejects_coercible_string_or_bool(column: str, value: object) -> None:
    contract = _small_contract()
    source = _evaluated_source()
    source[column] = source[column].astype(object)
    source.loc[source.index[0], column] = value
    with pytest.raises(RuntimeError, match="string/boolean"):
        prepare_v1d_evaluated_portfolios(source, contract=contract)


def test_exact_persisted_schema_rejects_rename_reorder_and_dtype_drift() -> None:
    frames, contract = _persisted_frames()
    renamed = copy.deepcopy(frames)
    renamed["evaluated_portfolios"] = renamed["evaluated_portfolios"].rename(
        columns={"candidate_id": "candidate_id_renamed"}
    )
    with pytest.raises(RuntimeError, match=r"ordered column names|schema"):
        validate_v1d_persisted_numeric_finiteness(renamed, contract=contract)

    reordered = copy.deepcopy(frames)
    window = reordered["window_sharp_contrasts"]
    reordered["window_sharp_contrasts"] = window.loc[
        :, [window.columns[1], window.columns[0], *window.columns[2:]]
    ]
    with pytest.raises(RuntimeError, match=r"ordered column names|schema"):
        validate_v1d_persisted_numeric_finiteness(reordered, contract=contract)

    recast = copy.deepcopy(frames)
    recast["monthly_sharp_contrasts"]["normalization_periods"] = recast["monthly_sharp_contrasts"][
        "normalization_periods"
    ].astype("float64")
    with pytest.raises(RuntimeError, match=r"dtype|schema"):
        validate_v1d_persisted_numeric_finiteness(recast, contract=contract)


def test_manifest_schema_contract_rejects_order_or_dtype_drift() -> None:
    contract = _small_contract()
    schemas = expected_v1d_persisted_schemas(contract)
    runner._require_exact_schema_descriptors(schemas, contract=contract, label="test")
    mutated = copy.deepcopy(schemas)
    items = list(mutated["window_sharp_contrasts"]["dtypes"].items())
    mutated["window_sharp_contrasts"]["dtypes"] = dict([items[1], items[0], *items[2:]])
    with pytest.raises(RuntimeError, match="row/name/order/dtype"):
        runner._require_exact_schema_descriptors(mutated, contract=contract, label="test")


def test_pooled_period_must_be_all_missing_before_drop_and_absent_after() -> None:
    frames, contract = _persisted_frames()
    full = _locked_frame("window_sharp_contrasts", 1)
    full["scope"] = pd.Series(["pooled_primary_window"], dtype="str")
    full.insert(2, "period", pd.Series(["2016-04"], dtype="str"))
    with pytest.raises(RuntimeError, match="all-missing"):
        prepare_v1d_window_sharp_contrasts(full, contract=contract)
    improper = frames["window_sharp_contrasts"].assign(period=None)
    frames["window_sharp_contrasts"] = improper
    with pytest.raises(RuntimeError, match=r"schema|missing"):
        validate_v1d_persisted_numeric_finiteness(frames, contract=contract)


def test_exact_payoff_relationship_is_fail_closed() -> None:
    contract = _small_contract()
    wrong_missingness = _evaluated_source()
    wrong_missingness.loc[0, "realized_payoff_exact"] = np.nan
    with pytest.raises(RuntimeError, match="missingness"):
        prepare_v1d_evaluated_portfolios(wrong_missingness, contract=contract)
    wrong_exact = _evaluated_source()
    wrong_exact.loc[0, "realized_payoff_exact"] = 999.0
    with pytest.raises(RuntimeError, match="does not equal"):
        prepare_v1d_evaluated_portfolios(wrong_exact, contract=contract)


def test_pre_b_manifest_uses_requirements_not_future_fact_attestations() -> None:
    source = (
        ROOT / "scripts/experiments/run_ijds_set_preserving_embedding_sensitivity_v1d.py"
    ).read_text(encoding="utf-8")
    if (
        '"direct_child_required": True' not in source
        or '"annotated_tag_required": True' not in source
    ):
        pytest.fail("V1d manifest omits future B2 requirements.")
    if '"direct_child": True' in source or '"annotated_tag": True' in source:
        pytest.fail("V1d runner pre-attests a future B2 commit or tag.")
