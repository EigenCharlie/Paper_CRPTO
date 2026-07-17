"""Contracts for paper-facing endpoint sensitivity evidence."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.ijds_audit.sensitivity_evidence import (
    _validate_endpoint_frames,
    endpoint_publication_table,
    load_endpoint_sensitivity_evidence,
)

ROOT = Path(__file__).resolve().parents[2]
SUMMARY = (
    ROOT
    / "models/experiments/ijds_audit"
    / "ijds-endpoint-availability-sensitivity-2026-07-14-v1"
    / "endpoint_sensitivity_summary.json"
)
IDENTITY = {
    "run_tag": "ijds-endpoint-availability-sensitivity-2026-07-14-v1",
    "protocol_tag": "protocol/ijds-endpoint-availability-sensitivity-2026-07-14-v1",
    "protocol_commit": "8865f1cfbd387576bdf805f3e52f030261e4b717",
}


def _load():
    return load_endpoint_sensitivity_evidence(
        SUMMARY,
        identity=IDENTITY,
        repo_root=ROOT,
        reference_coverage=pd.read_parquet(
            ROOT
            / "data/processed/experiments/ijds_audit"
            / "ijds-credit-risk-controls-2026-07-14-v3/evaluation/temporal_coverage.parquet"
        ),
        reference_two_ruler=pd.read_parquet(
            ROOT
            / "data/processed/experiments/ijds_audit"
            / "ijds-normalized-objective-frontier-2026-07-14-v3"
            / "evaluation/window_endpoint_contrasts.parquet"
        ),
        reference_envelopes=pd.read_parquet(
            ROOT
            / "data/processed/experiments/ijds_audit"
            / "ijds-binary-geometry-frontier-v4-2026-07-14-v3"
            / "evaluation/comparator_envelopes.parquet"
        ),
    )


def test_endpoint_sensitivity_is_complete_and_reconciles_exactly() -> None:
    evidence = _load()

    assert evidence.reconciliation == {
        "charged_off_lag_months": 6,
        "coverage_cells_exact": 120,
        "two_ruler_contrasts_exact": 48,
        "exact_support_envelopes_exact": 648,
        "byte_value_equal_after_lag_column_removed": True,
    }
    table = endpoint_publication_table(evidence).set_index("charged_off_lag_months")
    assert table.index.tolist() == [0, 3, 6, 8, 12]
    assert table.loc[0, "primary_resolved"] == 364_861
    assert table.loc[6, "primary_resolved"] == 364_814
    assert table.loc[8, "primary_unresolved"] == 12_320
    assert table.loc[12, "primary_unresolved"] == 13_602
    assert table.loc[0, "coverage_upper_max"] == pytest.approx(0.8976411849455659)
    assert table.loc[6, "coverage_upper_max"] == pytest.approx(0.8977258526333881)
    assert table.loc[8, "coverage_upper_max"] == pytest.approx(0.8981507095313236)
    assert table.loc[12, "coverage_upper_max"] == pytest.approx(0.9004108276571989)
    assert table.loc[12, "coverage_upper_below_0_90_cells"] == 39
    assert table.loc[12, "coverage_upper_at_or_above_0_90_cells"] == 1
    assert table["broad_stress_exact_frontier_standardized_payoff_crosses_zero_cells"].eq(72).all()
    assert table["broad_stress_exact_frontier_terminal_default_crosses_zero_cells"].eq(72).all()
    assert table["broad_stress_exact_frontier_funded_miscoverage_crosses_zero_cells"].eq(72).all()


def test_endpoint_grid_validation_is_order_invariant() -> None:
    evidence = _load()
    shuffled = {
        name: frame.sample(frac=1.0, random_state=20260715).reset_index(drop=True)
        for name, frame in evidence.frames.items()
    }

    _validate_endpoint_frames(shuffled)


def test_endpoint_grid_rejects_deleted_or_duplicate_cell() -> None:
    evidence = _load()
    deleted = {name: frame.copy() for name, frame in evidence.frames.items()}
    deleted["coverage_cells"] = deleted["coverage_cells"].iloc[1:].reset_index(drop=True)
    with pytest.raises(RuntimeError, match="grid changed"):
        _validate_endpoint_frames(deleted)

    duplicated = {name: frame.copy() for name, frame in evidence.frames.items()}
    duplicated["two_ruler_directions"] = pd.concat(
        [duplicated["two_ruler_directions"].iloc[1:], duplicated["two_ruler_directions"].iloc[[1]]],
        ignore_index=True,
    )
    with pytest.raises(RuntimeError, match="duplicate grid keys"):
        _validate_endpoint_frames(duplicated)


def test_endpoint_grid_rejects_vacuous_lag_subset() -> None:
    evidence = _load()
    frames = {name: frame.copy() for name, frame in evidence.frames.items()}
    frames["coverage_summary"] = frames["coverage_summary"].loc[
        ~frames["coverage_summary"]["charged_off_lag_months"].eq(12)
    ]

    with pytest.raises(RuntimeError, match="grid changed"):
        _validate_endpoint_frames(frames)
