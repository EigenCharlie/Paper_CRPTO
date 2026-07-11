from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from scripts.experiments import (
    run_ijds_comparator_stringency_audit as audit,
    run_ijds_maturity_safe_challenger as parent_runner,
)
from src.utils.isolated_experiment import OutputPaths


def _synthetic_parent(config: dict[str, object]) -> audit.ParentFrames:
    locked = config["comparators"]["development_matched"]  # type: ignore[index]
    sensitivity = locked["sensitivity_risk_tolerances"]
    low = float(sensitivity["low"])
    mean = float(sensitivity["mid"])
    high = float(sensitivity["high"])
    middle = (6.0 * mean - low - high) / 4.0
    periods = pd.period_range("2012-07", "2012-12", freq="M").astype(str)
    rows: list[dict[str, object]] = []
    for index in range(1, 10):
        candidate_id = f"linear-{index:03d}"
        values = (
            [low, middle, middle, middle, middle, high]
            if candidate_id == "linear-004"
            else [0.05 + index / 1000.0] * 6
        )
        for period, value in zip(periods, values, strict=True):
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "period": period,
                    "weighted_pd_point": value,
                }
            )
    return audit.ParentFrames(
        decision=pd.DataFrame(),
        outcomes=pd.DataFrame(),
        development_guardrail_monthly=pd.DataFrame(rows),
        parent_allocations=pd.DataFrame(),
        parent_summary={},
        parent_config=parent_runner.load_config(parent_runner.DEFAULT_CONFIG_PATH),
        evidence_path=Path("evidence.json"),
        summary_path=Path("summary.json"),
    )


def test_locked_config_declares_posthoc_falsification_boundary() -> None:
    config = audit.load_config(audit.DEFAULT_CONFIG_PATH)

    assert config["posthoc_diagnostic_after_active_results"] is True
    assert config["primary_policy"]["candidate_id"] == "linear-004"
    assert config["primary_policy"]["promotion_locked"] is True
    assert config["family_census"]["oot_reselection_forbidden"] is True
    assert config["family_census"]["family_claim_requires_same_direction"] == "9_of_9"
    assert config["analysis"]["purpose_concentration_sensitivity"] is False


def test_audit_specs_lock_one_primary_match_and_closed_family_census() -> None:
    config = audit.load_config(audit.DEFAULT_CONFIG_PATH)
    specs = audit._derive_audit_specs(config, _synthetic_parent(config))

    assert len(specs.specs) == 21
    assert len(specs.family_pairs) == 9
    assert specs.selected_candidate_id == "linear-004"
    assert specs.selected_guardrail_label == "selected_conformal_guardrail"
    assert specs.selected_match_label == "development_matched_point_pd"
    selected = specs.thresholds.loc[specs.thresholds["candidate_id"].eq("linear-004")].iloc[0]
    locked = config["comparators"]["development_matched"]["sensitivity_risk_tolerances"]
    assert selected["monthly_point_pd_min"] == pytest.approx(locked["low"], abs=1e-15)
    assert selected["matched_point_pd_mean"] == pytest.approx(locked["mid"], abs=1e-15)
    assert selected["monthly_point_pd_max"] == pytest.approx(locked["high"], abs=1e-15)


def test_decision_gate_requires_both_baselines_and_every_leave_one_out() -> None:
    config = audit.load_config(audit.DEFAULT_CONFIG_PATH)
    specs = audit._derive_audit_specs(config, _synthetic_parent(config))
    selected = pd.DataFrame(
        [
            {
                "policy_b": specs.same_threshold_label,
                "realized_payoff_difference_upper": -1.0,
                "weighted_default_difference_lower": -0.04,
                "weighted_default_difference_upper": -0.02,
                "weighted_miscoverage_difference_lower": 0.01,
            },
            {
                "policy_b": specs.selected_match_label,
                "realized_payoff_difference_upper": -10.0,
                "weighted_default_difference_lower": 0.03,
                "weighted_default_difference_upper": 0.05,
                "weighted_miscoverage_difference_lower": 0.02,
            },
        ]
    )
    leave_one_out = pd.DataFrame(
        [
            {
                "policy_b": baseline,
                "dropped_period": f"2016-{month:02d}",
                "realized_payoff_difference_upper": -10.0,
                "weighted_default_difference_lower": (
                    -0.04 if baseline == specs.same_threshold_label else 0.03
                ),
                "weighted_default_difference_upper": -0.02,
                "weighted_miscoverage_difference_lower": 0.02,
            }
            for baseline in (specs.same_threshold_label, specs.selected_match_label)
            for month in range(1, 16)
        ]
    )

    gate = audit._decision_gate(selected, leave_one_out, specs)
    assert gate["headline_eligible"] is True

    leave_one_out.loc[
        leave_one_out["policy_b"].eq(specs.selected_match_label),
        "weighted_default_difference_lower",
    ] = -0.01
    gate = audit._decision_gate(selected, leave_one_out, specs)
    assert gate["leave_one_month_out_passes"] is False
    assert gate["headline_eligible"] is False


def test_payoff_decomposition_uses_one_common_unresolved_outcome() -> None:
    config = audit.load_config(audit.DEFAULT_CONFIG_PATH)
    specs = audit._derive_audit_specs(config, _synthetic_parent(config))
    common = {
        "role": "primary_oot",
        "period": "2016-04",
        "contractual_rate": 0.10,
        "pd_point": 0.20,
        "conformal_lower": 0.0,
        "conformal_upper": 0.4,
        "conformal_group": 0,
    }
    allocations = pd.DataFrame(
        [
            {
                **common,
                "id": "a",
                "policy_label": specs.selected_guardrail_label,
                "exposure": 50.0,
                "snapshot_default": 0.0,
            },
            {
                **common,
                "id": "b",
                "policy_label": specs.selected_guardrail_label,
                "exposure": 50.0,
                "snapshot_default": pd.NA,
            },
            {
                **common,
                "id": "a",
                "policy_label": specs.selected_match_label,
                "exposure": 100.0,
                "snapshot_default": 0.0,
            },
            {
                **common,
                "id": "a",
                "policy_label": specs.same_threshold_label,
                "exposure": 100.0,
                "snapshot_default": 0.0,
            },
        ]
    )

    result = audit._payoff_decomposition(allocations, specs, lgd=0.45)
    matched = result.loc[result["baseline"].eq(specs.selected_match_label)].iloc[0]
    assert matched["contractual_component"] == 0.0
    assert matched["realized_difference_lower"] == pytest.approx(-27.5)
    assert matched["realized_difference_upper"] == pytest.approx(0.0)


def test_write_artifacts_round_trips_csv_and_parquet(tmp_path: Path) -> None:
    paths = OutputPaths(data_dir=tmp_path / "data", model_dir=tmp_path / "models")
    paths.data_dir.mkdir()
    paths.model_dir.mkdir()
    protocol_freeze = paths.model_dir / "protocol_freeze.json"
    protocol_freeze.write_text("{}\n", encoding="utf-8")
    csv_frame = pd.DataFrame({"policy": ["guardrail"], "value": [1.25]})
    parquet_frame = pd.DataFrame({"id": ["loan-1"], "exposure": [100.0]})

    artifacts, schemas = audit._write_artifacts(
        paths=paths,
        repo_root=tmp_path,
        frames={
            "portfolio/summary.csv": csv_frame,
            "portfolio/allocations.parquet": parquet_frame,
        },
        protocol_freeze=protocol_freeze,
    )

    pd.testing.assert_frame_equal(
        pd.read_csv(paths.data_dir / "portfolio/summary.csv"),
        csv_frame,
    )
    pd.testing.assert_frame_equal(
        pd.read_parquet(paths.data_dir / "portfolio/allocations.parquet"),
        parquet_frame,
    )
    assert set(artifacts) == {
        "data/portfolio/allocations.parquet",
        "data/portfolio/summary.csv",
        "models/protocol_freeze.json",
    }
    assert set(schemas) == {
        "data/portfolio/allocations.parquet",
        "data/portfolio/summary.csv",
    }
