"""Tests for the clean, complete binary phase census contract."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from scripts.experiments.run_ijds_binary_phase_census_v1 import (
    IMPLEMENTATION_PATHS,
    _load_config,
    _require_fixed_contract,
)
from src.ijds_audit.binary_phase_census import (
    CELL_OUTPUT_COLUMNS,
    FIT_INPUT_COLUMNS,
    FROZEN_INPUT_COLUMNS,
    build_binary_phase_census,
)
from src.utils.isolated_experiment import relative_artifact_descriptor

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs/experiments/ijds_binary_phase_census_2026-08-01_v1.yaml"
PROTOCOL_PATH = ROOT / "docs/research/ijds_binary_phase_census_v1_protocol_2026-08-01.md"
MODULE_PATH = ROOT / "src/ijds_audit/binary_phase_census.py"
RUNNER_PATH = ROOT / "scripts/experiments/run_ijds_binary_phase_census_v1.py"
TEST_PATH = ROOT / "tests/test_ijds_audit/test_binary_phase_census.py"

LEARNERS = (
    "catboost_platt",
    "numeric_logistic_platt",
    "catboost_monotonic_platt",
    "woe_scorecard_platform_platt",
    "woe_scorecard_borrower_platt",
)
WINDOWS = (
    "w01_2012m01_m06",
    "w02_2012m02_m07",
    "w03_2012m03_m08",
    "w04_2012m04_m09",
    "w05_2012m05_m10",
    "w06_2012m06_m11",
    "w07_2012m07_m12",
    "w08_2012m08_2013m01",
)
GROUPS = 5
EXPECTED_CELLS = 200
ALPHA = 0.10


def _freeze_from_fit(fit: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, cell in fit.groupby(
        ["learner", "window_id", "taxonomy_groups", "conformal_group"],
        sort=False,
    ):
        scores = cell["pd_point"].to_numpy(dtype=float)
        labels = cell["terminal_default"].to_numpy(dtype=float)
        residuals = np.abs(labels - scores)
        count = int(len(cell))
        rank = int(math.ceil((count + 1) * (1.0 - ALPHA)))
        threshold = float(np.partition(residuals, rank - 1)[rank - 1])
        rows.append(
            {
                "learner": key[0],
                "window_id": key[1],
                "taxonomy_groups": int(key[2]),
                "conformal_group": int(key[3]),
                "fit_rows": count,
                "finite_sample_rank": rank,
                "fit_residual_quantile": threshold,
                "fit_score_min": float(scores.min()),
                "fit_score_max": float(scores.max()),
                "fit_residual_below_threshold": int(np.sum(residuals < threshold)),
                "fit_residual_equal_threshold": int(np.sum(residuals == threshold)),
                "fit_residual_above_threshold": int(np.sum(residuals > threshold)),
            }
        )
    return pd.DataFrame(rows, columns=list(FROZEN_INPUT_COLUMNS))


def _complete_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    blocks = []
    for learner_index, learner in enumerate(LEARNERS):
        for window_index, window_id in enumerate(WINDOWS):
            for group in range(GROUPS):
                nondefault_base = 0.04 + 0.004 * group
                default_score = 0.20 + 0.005 * group
                scores = [nondefault_base + 0.0001 * index for index in range(9)]
                scores.append(default_score)
                blocks.append(
                    pd.DataFrame(
                        {
                            "id": [
                                f"{learner_index}-{window_index}-{group}-{index}"
                                for index in range(10)
                            ],
                            "learner": learner,
                            "window_id": window_id,
                            "taxonomy_groups": GROUPS,
                            "conformal_group": group,
                            "pd_point": scores,
                            "terminal_default": [0.0] * 9 + [1.0],
                        }
                    )
                )
    fit = pd.concat(blocks, ignore_index=True).loc[:, list(FIT_INPUT_COLUMNS)]
    return fit, _freeze_from_fit(fit)


def _build(
    fit: pd.DataFrame, frozen: pd.DataFrame, *, learners=LEARNERS, windows=WINDOWS
) -> tuple[pd.DataFrame, dict]:
    return build_binary_phase_census(
        fit,
        frozen,
        expected_learners=learners,
        expected_window_ids=windows,
        taxonomy_groups=GROUPS,
        expected_cells=EXPECTED_CELLS,
        alpha=ALPHA,
        threshold_tolerance=1.0e-15,
    )


def test_complete_census_has_200_cells_and_five_exhaustive_40_cell_summaries():
    fit, frozen = _complete_inputs()
    table, summary = _build(fit, frozen)

    assert len(table) == EXPECTED_CELLS
    assert list(table.columns) == list(CELL_OUTPUT_COLUMNS)
    assert (
        table.loc[:, ["learner", "window_id", "conformal_group"]].drop_duplicates().shape[0]
        == EXPECTED_CELLS
    )
    assert summary["design_cardinalities"] == {
        "learner_count": 5,
        "window_count": 8,
        "stratum_count_per_learner_window": 5,
        "expected_cells": 200,
        "observed_cells": 200,
    }
    strata = summary["complete_ordered_stratum_summary"]
    assert [row["conformal_group"] for row in strata] == list(range(5))
    assert [row["expected_cells"] for row in strata] == [40] * 5
    assert [row["observed_cells"] for row in strata] == [40] * 5
    assert [row["cells_reconciled"] for row in strata] == [40] * 5
    assert summary["global_checks"]["complete_grid"] is True
    assert summary["global_checks"]["all_cells_reconcile"] is True


def test_summary_is_invariant_to_learner_window_relabeling_and_row_order():
    fit, frozen = _complete_inputs()
    _, reference = _build(fit, frozen)

    learner_map = dict(zip(LEARNERS, reversed(LEARNERS), strict=True))
    window_map = dict(zip(WINDOWS, reversed(WINDOWS), strict=True))
    relabeled_fit = fit.assign(
        learner=fit["learner"].map(learner_map),
        window_id=fit["window_id"].map(window_map),
    ).sample(frac=1.0, random_state=17)
    relabeled_frozen = frozen.assign(
        learner=frozen["learner"].map(learner_map),
        window_id=frozen["window_id"].map(window_map),
    ).sample(frac=1.0, random_state=23)
    _, permuted = _build(
        relabeled_fit,
        relabeled_frozen,
        learners=tuple(reversed(LEARNERS)),
        windows=tuple(reversed(WINDOWS)),
    )

    assert permuted == reference
    rendered = json.dumps(permuted, sort_keys=True)
    assert all(learner not in rendered for learner in LEARNERS)
    assert all(window not in rendered for window in WINDOWS)


def test_conditions_are_inapplicable_not_generalized_when_they_do_not_hold():
    fit, _ = _complete_inputs()
    key = (
        fit["learner"].eq(LEARNERS[0])
        & fit["window_id"].eq(WINDOWS[0])
        & fit["conformal_group"].eq(0)
    )
    cell_index = fit.index[key]
    fit.loc[cell_index[:9], "pd_point"] = 0.80
    fit.loc[cell_index[9], "pd_point"] = 0.20
    frozen = _freeze_from_fit(fit)

    table, _ = _build(fit, frozen)
    row = table.loc[
        table["learner"].eq(LEARNERS[0])
        & table["window_id"].eq(WINDOWS[0])
        & table["conformal_group"].eq(0)
    ].iloc[0]
    assert bool(row["exact_half_criterion_pass"])
    assert not bool(row["max_score_below_half_condition"])
    assert not bool(row["phase_margin_half_check_applicable"])
    assert not bool(row["no_interleaving_condition"])
    assert not bool(row["phase_margin_source_check_applicable"])
    assert row["threshold_source_branch"] == "condition_not_met"


def test_missing_cell_fails_closed():
    fit, frozen = _complete_inputs()
    missing = (
        fit["learner"].eq(LEARNERS[-1])
        & fit["window_id"].eq(WINDOWS[-1])
        & fit["conformal_group"].eq(4)
    )
    with pytest.raises(RuntimeError, match="complete grid"):
        _build(fit.loc[~missing], frozen.iloc[:-1])


def test_duplicate_fit_id_fails_closed():
    fit, frozen = _complete_inputs()
    duplicated = pd.concat([fit, fit.iloc[[0]]], ignore_index=True)
    with pytest.raises(RuntimeError, match="duplicate fit ID"):
        _build(duplicated, frozen)


def test_empty_calibration_class_fails_closed():
    fit, frozen = _complete_inputs()
    cell = (
        fit["learner"].eq(LEARNERS[0])
        & fit["window_id"].eq(WINDOWS[0])
        & fit["conformal_group"].eq(0)
    )
    fit.loc[cell, "terminal_default"] = 0.0
    with pytest.raises(RuntimeError, match="empty binary class"):
        _build(fit, frozen)


@pytest.mark.parametrize("value", [-0.001, 1.001, float("nan"), float("inf")])
def test_invalid_calibration_score_fails_closed(value: float):
    fit, frozen = _complete_inputs()
    fit.loc[0, "pd_point"] = value
    with pytest.raises(ValueError, match="Calibration score"):
        _build(fit, frozen)


def test_frozen_rank_mismatch_fails_closed():
    fit, frozen = _complete_inputs()
    frozen.loc[0, "finite_sample_rank"] = 9
    frozen.loc[0, "fit_residual_below_threshold"] = 8
    frozen.loc[0, "fit_residual_equal_threshold"] = 1
    frozen.loc[0, "fit_residual_above_threshold"] = 1
    with pytest.raises(RuntimeError, match="does not reconcile"):
        _build(fit, frozen)


def test_frozen_threshold_mismatch_fails_closed():
    fit, frozen = _complete_inputs()
    frozen.loc[0, "fit_residual_quantile"] += 1.0e-4
    with pytest.raises(RuntimeError, match="does not reconcile"):
        _build(fit, frozen)


def test_frozen_tie_count_mismatch_fails_closed():
    fit, frozen = _complete_inputs()
    frozen.loc[0, "fit_residual_below_threshold"] = 8
    frozen.loc[0, "fit_residual_equal_threshold"] = 2
    with pytest.raises(RuntimeError, match="does not reconcile"):
        _build(fit, frozen)


def test_allowlisted_input_and_output_schemas_exclude_downstream_fields():
    assert FIT_INPUT_COLUMNS == (
        "id",
        "learner",
        "window_id",
        "taxonomy_groups",
        "conformal_group",
        "pd_point",
        "terminal_default",
    )
    assert FROZEN_INPUT_COLUMNS == (
        "learner",
        "window_id",
        "taxonomy_groups",
        "conformal_group",
        "fit_rows",
        "finite_sample_rank",
        "fit_residual_quantile",
        "fit_score_min",
        "fit_score_max",
        "fit_residual_below_threshold",
        "fit_residual_equal_threshold",
        "fit_residual_above_threshold",
    )
    forbidden = {
        "target",
        "evaluation",
        "coverage",
        "resolved",
        "unresolved",
        "funded",
        "allocation",
        "policy",
        "endpoint",
    }
    assert not any(token in column.lower() for token in forbidden for column in CELL_OUTPUT_COLUMNS)

    fit, frozen = _complete_inputs()
    fit["target_label"] = 0
    with pytest.raises(ValueError, match=r"extra=\['target_label'\]"):
        _build(fit, frozen)


def test_config_and_runner_lock_the_four_sources_and_clean_protocol_gate():
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    assert config["run_tag"] == "ijds-binary-phase-census-2026-08-01-v1"
    assert config["protocol_tag"] == "protocol/ijds-binary-phase-census-2026-08-01-v1"
    assert config["artifact_tag"] == "artifacts/ijds-binary-phase-census-2026-08-01-v1"
    assert config["design"]["expected_cells"] == 200
    assert len(config["design"]["learners"]) == 5
    assert len(config["design"]["window_ids"]) == 8
    assert config["design"]["taxonomy_groups"] == 5
    assert len(config["source"]) == 4
    assert [descriptor["role"] for descriptor in config["source"].values()].count(
        "provenance_witness_unparsed"
    ) == 2
    assert [descriptor["role"] for descriptor in config["source"].values()].count(
        "scientific_table_allowlisted_columns"
    ) == 2

    runner = RUNNER_PATH.read_text(encoding="utf-8")
    assert runner.count("pd.read_parquet(") == 2
    assert "columns=list(FIT_INPUT_COLUMNS)" in runner
    assert "columns=list(FROZEN_INPUT_COLUMNS)" in runner
    assert "json.loads" not in runner
    assert "require_clean_tagged_head" in runner
    assert '"git", "cat-file", "-t"' in runner
    assert "prepare_output_paths" in runner
    assert "selected_path" not in runner.lower()
    assert "illustrative" not in runner.lower()


def test_runner_hash_binds_shared_io_and_environment_contracts():
    paths = {path.as_posix() for path in IMPLEMENTATION_PATHS}
    assert {
        "src/utils/isolated_experiment.py",
        "src/utils/pipeline_runtime.py",
        "pyproject.toml",
        "uv.lock",
    }.issubset(paths)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("cell_table", "nested/table.csv", "safe basename"),
        ("summary", "..", "safe basename"),
        ("execution_receipt", "C:/outside/receipt.json", "safe basename"),
        ("summary", "binary_phase_census.csv", "must be unique"),
    ],
)
def test_output_filename_drift_fails_closed(field: str, value: str, message: str):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    changed = copy.deepcopy(config)
    changed["output"][field] = value
    with pytest.raises(RuntimeError, match=message):
        _require_fixed_contract(changed)


@pytest.mark.parametrize("section", ["claim_boundary", "stop_rules"])
def test_claim_and_stop_contract_extras_fail_closed(section: str):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    changed = copy.deepcopy(config)
    changed[section]["undeclared_switch"] = True
    with pytest.raises(RuntimeError, match="exact"):
        _require_fixed_contract(changed)


def test_top_level_config_extra_fails_closed(tmp_path: Path):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config["undeclared_section"] = {}
    path = tmp_path / "changed.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(ValueError, match="exact top-level contract"):
        _load_config(path)


def test_all_four_source_hashes_match_the_local_files():
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    for descriptor in config["source"].values():
        path = ROOT / descriptor["path"]
        actual = relative_artifact_descriptor(path, repo_root=ROOT)
        assert actual["path"] == descriptor["path"]
        assert actual["bytes"] == descriptor["bytes"]
        assert actual["sha256"] == descriptor["sha256"]


def test_five_file_protocol_surface_has_no_asymmetric_diagnostic_path():
    all_paths = (CONFIG_PATH, PROTOCOL_PATH, MODULE_PATH, RUNNER_PATH, TEST_PATH)
    assert all(path.is_file() for path in all_paths)
    operational_paths = (CONFIG_PATH, PROTOCOL_PATH, MODULE_PATH, RUNNER_PATH)
    combined = "\n".join(path.read_text(encoding="utf-8") for path in operational_paths).lower()
    assert "selected_path" not in combined
    assert "illustrative path" not in combined
    assert "primary_catboost" not in combined
    protocol = PROTOCOL_PATH.read_text(encoding="utf-8")
    assert "5 x 8 x 5 = 200" in protocol
    assert "exactly 40 learner-window cells expected in each" in protocol
    assert "hashes them but never\nparses their contents" in protocol
    assert "There is no join to a target sample." in protocol
    assert "continuity of a finite order-statistic path" in protocol
    assert "common-maxima unit crossing" in protocol
    assert "universal low-score-bin property" in protocol
    assert "miscoverage floor" in protocol
    assert "requires a separate adversarial promotion audit" in protocol
