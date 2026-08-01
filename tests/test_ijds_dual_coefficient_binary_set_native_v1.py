from __future__ import annotations

import copy
import inspect
from pathlib import Path

import pandas as pd
import pytest

from scripts.experiments import run_ijds_dual_coefficient_binary_set_native_v1 as runner
from src.ijds_challengers.dual_coefficient_binary_set_native import (
    build_menu_certificates,
    certificate_digest,
    load_dual_coefficient_config,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/experiments/ijds_dual_coefficient_binary_set_native_2026-08-01_v1.yaml"
PROTOCOL = ROOT / "docs/research/ijds_dual_coefficient_binary_set_native_v1_protocol_2026-08-01.md"


def _synthetic_sources() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    solve_rows: list[dict[str, object]] = []
    taxonomy_rows: list[dict[str, object]] = []
    periods = [f"d{index:02d}" for index in range(11)] + [f"p{index:02d}" for index in range(15)]
    roles = ["policy_development"] * 11 + ["primary_oot"] * 15
    for window_index in range(8):
        window = f"w{window_index + 1:02d}"
        for role, period in zip(roles, periods, strict=True):
            taxonomy_rows.append(
                {
                    "window_id": window,
                    "role": role,
                    "period": period,
                    "n_candidates": 20,
                    "n_empty": 2,
                    "n_singleton_zero": 15,
                    "n_singleton_one": 1,
                    "n_two_label": 2,
                    "n_risk_zero": 15,
                    "n_risk_one": 5,
                    "empty_set_score": 1.0,
                }
            )
            for ruler in ("normalized_score", "objective_matched"):
                for coordinate in (0.25, 0.5, 0.75):
                    solve_rows.append(
                        {
                            "window_id": window,
                            "role": role,
                            "period": period,
                            "frontier_ruler": ruler,
                            "frontier_coordinate": coordinate,
                            "minimum_score": 0.0,
                            "minimum_score_portfolio_objective": 50_000.0,
                            "n_candidates": 20,
                            "total_allocated": 1_000_000.0,
                            "budget_residual": 0.0,
                            "cash_variable_present": False,
                            "set_native_score": "zero_iff_exact_singleton_zero_else_one",
                            "empty_set_convention": "fail_closed_one",
                            "solver_status": "Optimal",
                        }
                    )
    summary: dict[str, object] = {
        "status": "outcome_free_set_native_binary_robust_counterpart_complete",
        "run_tag": "ijds-set-native-binary-robust-counterpart-2026-07-31-v1",
        "counts": {"cells": 1248, "taxonomy_rows": 208},
        "outcome_columns_passed": [],
    }
    return pd.DataFrame(solve_rows), pd.DataFrame(taxonomy_rows), summary


def test_complete_grid_reduces_to_208_logical_certificates_without_solves() -> None:
    config = load_dual_coefficient_config(CONFIG)
    records, taxonomy, summary = _synthetic_sources()
    certificates = build_menu_certificates(records, taxonomy, summary, config=config)
    if len(certificates) != 208 or certificates["window_id"].nunique() != 8:
        pytest.fail("The 1,248 predecessor rows did not reduce to exactly 208 menus.")
    if not bool(certificates["all_maximin_optimizers_singleton_zero"].all()):
        pytest.fail("The conditional maximin conclusion is absent.")
    if not bool(certificates["continuous_cap_frontier_collapses"].all()):
        pytest.fail("The continuous frontier-collapse certificate is absent.")
    if bool(certificates["new_optimization_executed"].any()):
        pytest.fail("The logical certificate incorrectly reports a new optimization.")
    if len(certificate_digest(certificates)) != 64:
        pytest.fail("Certificate canonicalization did not produce one SHA-256 digest.")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("minimum", "zero minimum-score"),
        ("cash", "cash variable"),
        ("budget", "exact budget"),
        ("taxonomy", "partition"),
        ("missing", "1,248"),
        ("objective", "six predecessor repetitions"),
    ],
)
def test_certificate_builder_fails_closed_on_any_missing_condition(
    mutation: str, message: str
) -> None:
    config = load_dual_coefficient_config(CONFIG)
    records, taxonomy, summary = _synthetic_sources()
    if mutation == "minimum":
        records.loc[0, "minimum_score"] = 0.1
    elif mutation == "cash":
        records.loc[0, "cash_variable_present"] = True
    elif mutation == "budget":
        records.loc[0, "total_allocated"] = 999_000.0
    elif mutation == "taxonomy":
        taxonomy.loc[0, "n_empty"] = 1
    elif mutation == "missing":
        records = records.iloc[:-1].copy()
    elif mutation == "objective":
        records.loc[0, "minimum_score_portfolio_objective"] += 1.0
    with pytest.raises(RuntimeError, match=message):
        build_menu_certificates(records, taxonomy, summary, config=config)


def test_config_rejects_permission_for_raw_or_new_optimization(tmp_path: Path) -> None:
    import yaml

    payload = load_dual_coefficient_config(CONFIG)
    for key in ("no_raw_read", "no_new_optimization"):
        mutated = copy.deepcopy(payload)
        mutated["claim_boundary"][key] = False
        path = tmp_path / f"{key}.yaml"
        path.write_text(yaml.safe_dump(mutated, sort_keys=False), encoding="utf-8")
        with pytest.raises(ValueError, match="claim-boundary"):
            load_dual_coefficient_config(path)


def test_runner_has_no_raw_loader_or_optimizer_call() -> None:
    source = inspect.getsource(runner.run)
    forbidden = (
        "load_outcome_free_decision_base",
        "PointPortfolioSession",
        "solve_point_portfolio",
        "pd.read_csv",
    )
    for token in forbidden:
        if token in source:
            pytest.fail(f"Logical runner contains forbidden work: {token}.")


def test_protocol_uses_exact_singleton_zero_and_narrow_payoff_language() -> None:
    text = PROTOCOL.read_text(encoding="utf-8").casefold()
    required = (
        "singleton-zero",
        "minimum standardized credit payoff over",
        "empty set",
        "zero lp solves",
        "no phase b",
    )
    for phrase in required:
        if phrase not in text:
            pytest.fail(f"Protocol omits required boundary language: {phrase}.")
