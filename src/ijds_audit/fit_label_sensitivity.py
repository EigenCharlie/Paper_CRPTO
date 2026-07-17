"""Fitting-label completion scenarios for the active temporal design."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

FIT_LABEL_SCENARIOS = (
    "observed_only",
    "all_unavailable_nondefault",
    "all_unavailable_default",
    "hindsight_terminal",
)
FIT_SPLITS = ("pd_development", "probability_calibration", "conformal_fit")


def apply_fit_label_scenario(
    universe: pd.DataFrame,
    *,
    scenario: str,
    fit_splits: Sequence[str] = FIT_SPLITS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Complete only unavailable fitting labels under one declared scenario."""
    if scenario not in FIT_LABEL_SCENARIOS:
        raise ValueError(f"Unknown fitting-label scenario: {scenario!r}.")
    required = {"design_split", "terminal_default", "label_available"}
    missing = sorted(required.difference(universe.columns))
    if missing:
        raise KeyError(f"Fitting-label sensitivity is missing columns: {missing}.")

    completed = universe.copy()
    fit_mask = completed["design_split"].astype(str).isin(tuple(map(str, fit_splits)))
    unavailable = fit_mask & ~completed["label_available"].astype(bool)
    if bool(completed.loc[unavailable, "terminal_default"].isna().any()):
        raise RuntimeError("Unavailable fitting rows do not have terminal archive outcomes.")

    if scenario != "observed_only":
        completed.loc[unavailable, "label_available"] = True
        if scenario == "all_unavailable_nondefault":
            completed.loc[unavailable, "terminal_default"] = 0
        elif scenario == "all_unavailable_default":
            completed.loc[unavailable, "terminal_default"] = 1
        elif scenario != "hindsight_terminal":
            raise AssertionError("Scenario validation is incomplete.")
    completed["terminal_default"] = completed["terminal_default"].astype("Int8")
    completed["label_available"] = completed["label_available"].astype(bool)

    outside_fit = ~fit_mask
    if not completed.loc[outside_fit, ["terminal_default", "label_available"]].equals(
        universe.loc[outside_fit, ["terminal_default", "label_available"]]
    ):
        raise RuntimeError("A fitting-label scenario changed an evaluation row.")

    rows: list[dict[str, object]] = []
    for split in fit_splits:
        split_mask = completed["design_split"].astype(str).eq(str(split))
        source_available = universe.loc[split_mask, "label_available"].astype(bool)
        active_available = completed.loc[split_mask, "label_available"].astype(bool)
        source_labels = universe.loc[split_mask, "terminal_default"].astype("Int8")
        active_labels = completed.loc[split_mask, "terminal_default"].astype("Int8")
        source_prevalence = (
            float(source_labels[source_available].mean())
            if bool(source_available.any())
            else np.nan
        )
        active_prevalence = (
            float(active_labels[active_available].mean())
            if bool(active_available.any())
            else np.nan
        )
        rows.append(
            {
                "scenario": scenario,
                "design_split": str(split),
                "rows": int(split_mask.sum()),
                "source_available_rows": int(source_available.sum()),
                "source_unavailable_rows": int((~source_available).sum()),
                "active_available_rows": int(active_available.sum()),
                "completed_rows": int((active_available & ~source_available).sum()),
                "source_available_prevalence": source_prevalence,
                "active_prevalence": active_prevalence,
            }
        )
    return completed, pd.DataFrame(rows)


def summarize_fit_label_coverage(
    coverage: pd.DataFrame,
    *,
    scenarios: Sequence[str] = FIT_LABEL_SCENARIOS,
    window_ids: Sequence[str],
    nominal_coverage: float,
) -> pd.DataFrame:
    """Summarize the complete overall-window coverage grid by scenario."""
    overall = coverage.loc[coverage["conformal_group"].eq(-1)].copy()
    expected = {(str(scenario), str(window)) for scenario in scenarios for window in window_ids}
    observed = set(zip(overall["fit_label_scenario"], overall["window_id"], strict=True))
    if observed != expected or len(overall) != len(expected):
        raise RuntimeError("Fitting-label coverage grid is incomplete.")
    rows: list[dict[str, object]] = []
    for scenario, frame in overall.groupby("fit_label_scenario", observed=True, sort=True):
        lower = pd.to_numeric(frame["coverage_lower"], errors="raise")
        upper = pd.to_numeric(frame["coverage_upper"], errors="raise")
        rows.append(
            {
                "fit_label_scenario": str(scenario),
                "windows": int(len(frame)),
                "coverage_lower_min": float(lower.min()),
                "coverage_upper_max": float(upper.max()),
                "windows_upper_below_nominal": int(upper.lt(nominal_coverage).sum()),
                "all_windows_upper_below_nominal": bool(upper.lt(nominal_coverage).all()),
                "mean_width_min": float(pd.to_numeric(frame["mean_width"], errors="raise").min()),
                "mean_width_max": float(pd.to_numeric(frame["mean_width"], errors="raise").max()),
            }
        )
    result = pd.DataFrame(rows)
    numeric = result.select_dtypes(include=[np.number]).to_numpy(dtype=float)
    if not bool(np.isfinite(numeric).all()):
        raise RuntimeError("Fitting-label coverage summary contains non-finite values.")
    return result
