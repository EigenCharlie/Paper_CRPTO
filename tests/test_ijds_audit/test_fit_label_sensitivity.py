from __future__ import annotations

import pandas as pd
import pytest

from src.ijds_audit.fit_label_sensitivity import (
    FIT_LABEL_SCENARIOS,
    apply_fit_label_scenario,
    summarize_fit_label_coverage,
)


def _universe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "design_split": [
                "pd_development",
                "pd_development",
                "probability_calibration",
                "conformal_fit",
                "primary_oot",
            ],
            "terminal_default": pd.Series([0, 1, 1, 0, pd.NA], dtype="Int8"),
            "label_available": [True, False, False, False, False],
        }
    )


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        ("observed_only", [0, 1, 1, 0]),
        ("all_unavailable_nondefault", [0, 0, 0, 0]),
        ("all_unavailable_default", [0, 1, 1, 1]),
        ("hindsight_terminal", [0, 1, 1, 0]),
    ],
)
def test_fit_label_scenario_changes_only_unavailable_fitting_rows(
    scenario: str,
    expected: list[int],
) -> None:
    completed, audit = apply_fit_label_scenario(_universe(), scenario=scenario)

    assert completed.loc[:3, "terminal_default"].astype(int).tolist() == expected
    assert pd.isna(completed.loc[4, "terminal_default"])
    assert bool(completed.loc[4, "label_available"]) is False
    expected_completed = 0 if scenario == "observed_only" else 3
    assert int(audit["completed_rows"].sum()) == expected_completed


def test_fit_label_scenario_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="Unknown"):
        apply_fit_label_scenario(_universe(), scenario="selected_after_outcomes")


def test_fit_label_coverage_summary_requires_complete_grid() -> None:
    rows = []
    for scenario in FIT_LABEL_SCENARIOS:
        for window in ("w01", "w02"):
            rows.append(
                {
                    "fit_label_scenario": scenario,
                    "window_id": window,
                    "conformal_group": -1,
                    "coverage_lower": 0.84,
                    "coverage_upper": 0.88,
                    "mean_width": 0.4,
                }
            )
    coverage = pd.DataFrame(rows)

    summary = summarize_fit_label_coverage(
        coverage,
        window_ids=("w01", "w02"),
        nominal_coverage=0.90,
    )

    assert len(summary) == len(FIT_LABEL_SCENARIOS)
    assert bool(summary["all_windows_upper_below_nominal"].all())

    with pytest.raises(RuntimeError, match="incomplete"):
        summarize_fit_label_coverage(
            coverage.iloc[:-1],
            window_ids=("w01", "w02"),
            nominal_coverage=0.90,
        )
