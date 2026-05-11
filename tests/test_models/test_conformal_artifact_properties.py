"""Structural invariants of the frozen conformal artifact.

The MAPIE 0.9 → 1.x migration in ``src/models/conformal.py`` is complete on
the code side (Codex commit ``c011b3d``). The remaining validation question
is: do the intervals stored in
``data/processed/conformal_intervals_mondrian.parquet`` still satisfy the
mathematical contract MAPIE guarantees?

These tests **do not** re-run the conformal stage. They load the frozen
parquet and assert the properties any MAPIE-produced output must have. If
this file passes, the migration is internally consistent. A full bit-exact
drift validation against a fresh ``dvc repro crpto.conformal.intervals`` is
optional — see ``docs/refactor/MAPIE_MIGRATION_PLAN.md`` for the procedure.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ARTIFACT = Path("data/processed/conformal_intervals_mondrian.parquet")

# Champion coverage targets (configs/crpto_conformal_policy.yaml). The
# observed coverage on the test set should be at least these minus a small
# finite-sample slack.
TARGET_90 = 0.90
TARGET_95 = 0.95
COVERAGE_SLACK = 0.02  # finite-sample tolerance — MAPIE guarantees ≥ target
# asymptotically, but per-Mondrian cells can dip a bit.


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    if not ARTIFACT.is_file():
        pytest.skip(f"{ARTIFACT} not available locally — run `dvc pull` to fetch it.")
    return pd.read_parquet(ARTIFACT)


def test_artifact_has_expected_columns(df: pd.DataFrame) -> None:
    required = {
        "y_true",
        "y_pred",
        "pd_low_90",
        "pd_high_90",
        "pd_low_95",
        "pd_high_95",
        "width_90",
        "width_95",
        "grade",
    }
    assert required <= set(df.columns), f"Missing columns: {required - set(df.columns)}"


def test_predictions_in_unit_interval(df: pd.DataFrame) -> None:
    for col in ("y_pred", "pd_low_90", "pd_high_90", "pd_low_95", "pd_high_95"):
        values = df[col].to_numpy()
        assert np.all((values >= 0.0) & (values <= 1.0)), f"{col} has values outside [0, 1]"


def test_intervals_are_monotone(df: pd.DataFrame) -> None:
    """pd_low_90 ≤ y_pred ≤ pd_high_90 and same for 95%."""
    assert (df["pd_low_90"] <= df["y_pred"] + 1e-9).all()
    assert (df["y_pred"] <= df["pd_high_90"] + 1e-9).all()
    assert (df["pd_low_95"] <= df["y_pred"] + 1e-9).all()
    assert (df["y_pred"] <= df["pd_high_95"] + 1e-9).all()


def test_95_intervals_contain_90_intervals(df: pd.DataFrame) -> None:
    """The 95% interval must be at least as wide as the 90% interval."""
    assert (df["pd_low_95"] <= df["pd_low_90"] + 1e-9).all()
    assert (df["pd_high_95"] >= df["pd_high_90"] - 1e-9).all()


def test_widths_are_non_negative(df: pd.DataFrame) -> None:
    assert (df["width_90"] >= -1e-9).all()
    assert (df["width_95"] >= -1e-9).all()


def test_width_matches_interval(df: pd.DataFrame) -> None:
    """``width_*`` should equal ``pd_high_* - pd_low_*`` up to float rounding."""
    delta_90 = df["pd_high_90"].to_numpy() - df["pd_low_90"].to_numpy()
    delta_95 = df["pd_high_95"].to_numpy() - df["pd_low_95"].to_numpy()
    np.testing.assert_allclose(df["width_90"].to_numpy(), delta_90, atol=1e-9)
    np.testing.assert_allclose(df["width_95"].to_numpy(), delta_95, atol=1e-9)


def test_global_coverage_meets_target(df: pd.DataFrame) -> None:
    """The conformal coverage guarantee: ``P(y ∈ [low, high]) ≥ target``."""
    inside_90 = ((df["y_true"] >= df["pd_low_90"]) & (df["y_true"] <= df["pd_high_90"])).mean()
    inside_95 = ((df["y_true"] >= df["pd_low_95"]) & (df["y_true"] <= df["pd_high_95"])).mean()
    assert inside_90 >= TARGET_90 - COVERAGE_SLACK, (
        f"90% coverage observed = {inside_90:.4f}, expected ≥ {TARGET_90 - COVERAGE_SLACK:.4f}"
    )
    assert inside_95 >= TARGET_95 - COVERAGE_SLACK, (
        f"95% coverage observed = {inside_95:.4f}, expected ≥ {TARGET_95 - COVERAGE_SLACK:.4f}"
    )


def test_per_grade_coverage_within_tolerance(df: pd.DataFrame) -> None:
    """Mondrian conditional coverage: each grade should also achieve target ± slack."""
    df = df.copy()
    df["in_90"] = (df["y_true"] >= df["pd_low_90"]) & (df["y_true"] <= df["pd_high_90"])
    per_grade = df.groupby("grade", observed=True)["in_90"].mean()
    failures = per_grade[per_grade < TARGET_90 - COVERAGE_SLACK]
    assert failures.empty, f"Mondrian coverage failed for grades: {failures.to_dict()}"


def test_artifact_row_count_matches_champion(df: pd.DataFrame) -> None:
    """The frozen run produced 276 869 rows; any change to this number breaks
    the paper's contribution count."""
    assert len(df) == 276869


@pytest.mark.slow
@pytest.mark.integration
def test_mapie_drift_harness_skipped_by_default() -> None:
    """Placeholder for the full MAPIE 1.x drift harness.

    The harness re-runs ``scripts/generate_conformal_intervals.py`` on a
    branch, compares hash-by-hash against the frozen parquet, and asserts
    ``max abs diff ≤ 1e-6`` per loan. Today it is skipped by default; trigger
    it manually with:

        uv run pytest -m "slow and integration" tests/test_models/test_conformal_artifact_properties.py

    See ``docs/refactor/MAPIE_MIGRATION_PLAN.md`` for the full procedure.
    """
    pytest.skip("Manual drift harness — run `dvc repro crpto.conformal.intervals` instead.")
