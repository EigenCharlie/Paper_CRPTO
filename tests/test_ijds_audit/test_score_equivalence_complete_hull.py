"""Tests for the outcome-free complete-hull score-equivalence audit."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from scripts.experiments.run_ijds_score_equivalence_complete_hull_v1 import (
    load_complete_hull_config,
    validate_complete_outputs,
)
from src.ijds_audit.score_equivalence_complete_hull import (
    certificate_record,
    certify_complete_budget_hull,
    certify_full_budget_score_equivalence,
    deterministic_nonaffine_control,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/experiments/ijds_score_equivalence_complete_hull_2026-07-31_v1.yaml"


def test_constructive_witness_certifies_complete_fixed_budget_hull() -> None:
    certificate = certify_complete_budget_hull(
        [10.0, 10.0, 10.0, 10.0, 10.0],
        ["a", "b", "c", "d", "e"],
        budget=10.0,
        purpose_cap=0.25,
    )

    assert certificate.full_budget_hull_certified is True
    assert certificate.ambient_dimension == 5
    assert certificate.affine_dimension == 4
    assert certificate.purpose_count == 5
    assert certificate.witness_budget_residual == pytest.approx(0.0)
    assert certificate.minimum_witness_exposure == pytest.approx(2.0)
    assert certificate.minimum_loan_upper_slack == pytest.approx(8.0)
    assert certificate.minimum_purpose_cap_slack == pytest.approx(0.5)


def test_hull_certificate_fails_closed_without_strict_purpose_slack() -> None:
    certificate = certify_complete_budget_hull(
        [10.0, 10.0, 10.0, 10.0],
        ["a", "b", "c", "d"],
        budget=10.0,
        purpose_cap=0.25,
    )

    assert certificate.full_budget_hull_certified is False
    assert certificate.affine_dimension is None
    assert certificate.witness_budget_residual is None


def test_complete_hull_score_certificate_accepts_positive_affine_translation() -> None:
    source = np.array([0.05, 0.12, 0.31, 0.70])
    target = 2.25 * source + 0.4

    certificate = certify_full_budget_score_equivalence(
        source,
        target,
        budget=1_000_000.0,
    )

    assert certificate.equivalent_on_complete_budget_hull is True
    assert certificate.estimated_scale == pytest.approx(2.25)
    assert certificate.positive_scale is True
    assert certificate.estimated_unit_intercept == pytest.approx(0.4)
    assert certificate.portfolio_score_offset == pytest.approx(400_000.0)
    assert certificate.maximum_coordinate_relation_error == pytest.approx(0.0, abs=1.0e-14)


def test_complete_hull_score_certificate_rejects_negative_and_nonaffine_maps() -> None:
    source = np.array([0.0, 0.2, 0.6, 1.0])
    reversed_score = 3.0 - source
    nonlinear_score = source**2

    negative = certify_full_budget_score_equivalence(
        source,
        reversed_score,
        budget=1.0,
    )
    nonlinear = certify_full_budget_score_equivalence(
        source,
        nonlinear_score,
        budget=1.0,
    )

    assert negative.equivalent_on_complete_budget_hull is False
    assert negative.positive_scale is False
    assert negative.maximum_coordinate_relation_error == pytest.approx(0.0, abs=1.0e-14)
    assert nonlinear.equivalent_on_complete_budget_hull is False
    assert nonlinear.positive_scale is True
    assert nonlinear.maximum_coordinate_relation_error > nonlinear.relation_tolerance


def test_constant_source_requires_constant_target() -> None:
    passing = certify_full_budget_score_equivalence(
        np.ones(4),
        np.full(4, 9.0),
        budget=10.0,
    )
    failing = certify_full_budget_score_equivalence(
        np.ones(4),
        np.array([9.0, 9.0, 9.0, 8.0]),
        budget=10.0,
    )

    assert passing.equivalent_on_complete_budget_hull is True
    assert passing.estimated_scale == pytest.approx(1.0)
    assert failing.equivalent_on_complete_budget_hull is False


def test_deterministic_negative_control_is_reliably_nonaffine() -> None:
    source = np.linspace(0.01, 0.99, 101)
    target = deterministic_nonaffine_control(source, amplitude=1.0e-3)
    certificate = certify_full_budget_score_equivalence(source, target, budget=1.0)

    assert np.isfinite(target).all()
    assert certificate.estimated_scale == pytest.approx(1.75, rel=1.0e-10)
    assert certificate.equivalent_on_complete_budget_hull is False
    assert certificate.maximum_coordinate_relation_error > certificate.relation_tolerance


@pytest.mark.parametrize(
    ("amounts", "purposes", "message"),
    [
        ([1.0, 0.0], ["a", "b"], "strictly positive"),
        ([1.0, 2.0], ["a"], "aligned"),
        ([1.0, np.nan], ["a", "b"], "finite"),
    ],
)
def test_hull_certificate_rejects_invalid_inputs(
    amounts: list[float],
    purposes: list[str],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        certify_complete_budget_hull(
            amounts,
            purposes,
            budget=1.0,
            purpose_cap=0.5,
        )


def test_locked_config_loads_and_rejects_grid_drift(tmp_path: Path) -> None:
    config = load_complete_hull_config(CONFIG)
    assert config["expected_census"]["v1d_embedding_comparisons"] == 5200
    assert config["expected_census"]["calibrator_comparisons"] == 6240

    changed = deepcopy(config)
    changed["design"]["gamma_grid"] = [0.0, 1.0]
    path = tmp_path / "changed.yaml"
    path.write_text(yaml.safe_dump(changed, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="scientific design"):
        load_complete_hull_config(path)


def _score_fields(equivalent: bool) -> dict[str, object]:
    source = np.array([0.1, 0.2, 0.4])
    target = 2.0 * source + 0.3 if equivalent else source**2
    return certificate_record(certify_full_budget_score_equivalence(source, target, budget=1.0))


def test_output_validator_enforces_identity_and_synthetic_controls() -> None:
    hull = pd.DataFrame(
        [
            {
                "role": "primary_oot",
                "period": "2016-04",
                "rows": 3,
                **certificate_record(
                    certify_complete_budget_hull(
                        [1.0, 1.0, 1.0, 1.0, 1.0],
                        ["a", "b", "c", "d", "e"],
                        budget=1.0,
                        purpose_cap=0.25,
                    )
                ),
            }
        ]
    )
    v1d = pd.DataFrame(
        [
            {
                "window_id": "w",
                "role": "primary_oot",
                "period": "2016-04",
                "theta": theta,
                "gamma": 0.0,
                **_score_fields(True),
            }
            for theta in (0.0, 0.25)
        ]
    )
    calibrator = pd.DataFrame(
        [
            {
                "window_id": "w",
                "role": "primary_oot",
                "period": "2016-04",
                "method_a": "platt",
                "method_b": "isotonic",
                "gamma": 0.0,
                **_score_fields(False),
            }
        ]
    )
    controls = pd.DataFrame(
        [
            {
                "role": "primary_oot",
                "period": "2016-04",
                "control_type": "positive_affine",
                "expected_equivalent": True,
                "observed_equivalent": True,
                "control_passed": True,
                **_score_fields(True),
            },
            {
                "role": "primary_oot",
                "period": "2016-04",
                "control_type": "negative_nonaffine",
                "expected_equivalent": False,
                "observed_equivalent": False,
                "control_passed": True,
                **_score_fields(False),
            },
        ]
    )
    config = {
        "design": {"raw_forbidden_tokens": ["outcome", "default", "status"]},
        "expected_census": {
            "complete_hull_certificates": 1,
            "v1d_embedding_comparisons": 2,
            "calibrator_comparisons": 1,
            "runtime_controls": 2,
            "v1d_theta_zero_self_controls": 1,
            "v1d_gamma_zero_controls": 2,
            "v1d_nonzero_theta_gamma_zero_controls": 1,
            "runtime_positive_controls": 1,
            "runtime_negative_controls": 1,
            "calibrator_pairs": 1,
        },
    }

    validate_complete_outputs(hull, v1d, calibrator, controls, config=config)
    broken = v1d.copy()
    broken.loc[1, "equivalent_on_complete_budget_hull"] = False
    with pytest.raises(RuntimeError, match="identity controls"):
        validate_complete_outputs(hull, broken, calibrator, controls, config=config)
