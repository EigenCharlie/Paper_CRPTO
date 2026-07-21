"""Complete binary-set and resolved-label diagnostics for frozen conformal scores."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from src.ijds_audit.grid_contracts import require_exact_grid, require_finite, require_unique_row
from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    apply_binary_outcome_recipe,
)


def _require_close(actual: float, expected: float, *, label: str, atol: float) -> None:
    if not np.isclose(actual, expected, atol=atol, rtol=atol):
        raise RuntimeError(f"{label} did not reconcile: {actual!r} != {expected!r}.")


def build_conformal_set_diagnostics(
    scores: pd.DataFrame,
    outcomes: pd.DataFrame,
    recipes: Mapping[
        str,
        Mapping[str, Mapping[int, BinaryOutcomeConformalRecipe]],
    ],
    reference_coverage: pd.DataFrame,
    *,
    learners: Sequence[str],
    window_ids: Sequence[str],
    role: str,
    taxonomy_groups: int,
    expected_issue_months: Sequence[str],
    expected_candidates: int,
    expected_resolved: int,
    expected_unresolved: int,
    expected_resolved_y0: int,
    expected_resolved_y1: int,
    reconciliation_atol: float = 5.0e-14,
) -> pd.DataFrame:
    """Return every declared learner-window binary-set diagnostic.

    Label-specific coverage is calculated only over outcomes resolved under the
    supplied endpoint. It is a descriptive partition of resolved coverage, not
    a label-conditional conformal guarantee.
    """
    required_score_columns = {"id", "issue_d", "design_split"}
    required_score_columns.update(f"pd_{learner}" for learner in learners)
    missing_score_columns = required_score_columns.difference(scores.columns)
    if missing_score_columns:
        raise ValueError(f"Frozen scores omit columns: {sorted(missing_score_columns)}")
    if not {"id", "snapshot_default"}.issubset(outcomes.columns):
        raise ValueError("Endpoint outcomes must contain id and snapshot_default.")

    primary = scores.loc[scores["design_split"].eq(role)].copy()
    primary["issue_month"] = pd.to_datetime(primary["issue_d"], errors="raise").dt.to_period("M")
    actual_months = tuple(sorted(primary["issue_month"].astype(str).unique()))
    if actual_months != tuple(expected_issue_months):
        raise RuntimeError(
            f"Primary issue-month set changed: {actual_months!r} != "
            f"{tuple(expected_issue_months)!r}."
        )
    if len(primary) != expected_candidates or primary["id"].duplicated().any():
        raise RuntimeError("Primary score census or ID uniqueness changed.")

    endpoint = outcomes[["id", "snapshot_default"]].copy()
    if endpoint["id"].duplicated().any():
        raise RuntimeError("Endpoint outcomes contain duplicate IDs.")
    joined = primary.merge(
        endpoint,
        on="id",
        how="left",
        validate="one_to_one",
        indicator="_endpoint_merge",
    )
    if not joined["_endpoint_merge"].eq("both").all():
        missing_ids = joined.loc[~joined["_endpoint_merge"].eq("both"), "id"].astype(str)
        raise RuntimeError(
            "Endpoint alignment is incomplete for frozen primary IDs; "
            f"examples={missing_ids.head(5).tolist()}."
        )
    joined = joined.drop(columns="_endpoint_merge")
    resolved = joined["snapshot_default"].notna().to_numpy(dtype=bool)
    labels = joined.loc[resolved, "snapshot_default"].to_numpy(dtype=float)
    if not set(np.unique(labels)).issubset({0.0, 1.0}):
        raise RuntimeError("Resolved endpoint contains a nonbinary outcome.")
    resolved_y0 = labels == 0.0
    resolved_y1 = labels == 1.0
    counts = {
        "resolved": int(resolved.sum()),
        "unresolved": int((~resolved).sum()),
        "resolved_y0": int(resolved_y0.sum()),
        "resolved_y1": int(resolved_y1.sum()),
    }
    expected_counts = {
        "resolved": expected_resolved,
        "unresolved": expected_unresolved,
        "resolved_y0": expected_resolved_y0,
        "resolved_y1": expected_resolved_y1,
    }
    if counts != expected_counts:
        raise RuntimeError(f"Resolved-label census changed: {counts!r} != {expected_counts!r}.")

    canonical = reference_coverage.loc[
        reference_coverage["taxonomy_groups"].eq(taxonomy_groups)
        & reference_coverage["role"].eq(role)
        & reference_coverage["conformal_group"].eq(-1)
    ].copy()
    require_exact_grid(
        canonical,
        domains={"learner": tuple(learners), "window_id": tuple(window_ids)},
        label="conformal-set diagnostic reference coverage",
    )

    rows: list[dict[str, Any]] = []
    for learner in learners:
        if learner not in recipes:
            raise RuntimeError(f"Frozen recipes omit learner {learner!r}.")
        probabilities = joined[f"pd_{learner}"].to_numpy(dtype=float)
        for window_id in window_ids:
            try:
                recipe = recipes[learner][window_id][taxonomy_groups]
            except KeyError as exc:
                raise RuntimeError(
                    f"Frozen recipe grid omits {learner}/{window_id}/{taxonomy_groups}."
                ) from exc
            _, lower, upper = apply_binary_outcome_recipe(probabilities, recipe)
            contains_zero = lower <= 0.0
            contains_one = upper >= 1.0
            empty = ~contains_zero & ~contains_one
            zero_only = contains_zero & ~contains_one
            one_only = ~contains_zero & contains_one
            both = contains_zero & contains_one
            partition = empty.astype(int) + zero_only + one_only + both
            if not np.equal(partition, 1).all():
                raise RuntimeError(
                    f"Binary prediction sets do not partition in {learner}/{window_id}."
                )

            covered_resolved = (resolved_y0 & contains_zero[resolved]) | (
                resolved_y1 & contains_one[resolved]
            )
            cardinality = contains_zero.astype(int) + contains_one.astype(int)
            singleton = cardinality == 1
            row: dict[str, Any] = {
                "learner": learner,
                "window_id": window_id,
                "taxonomy_groups": int(taxonomy_groups),
                "role": role,
                "candidate_rows": int(len(joined)),
                "resolved_rows": int(resolved.sum()),
                "unresolved_rows": int((~resolved).sum()),
                "resolved_y0_rows": int(resolved_y0.sum()),
                "resolved_y1_rows": int(resolved_y1.sum()),
                "coverage_resolved": float(covered_resolved.mean()),
                "coverage_resolved_y0": float(contains_zero[resolved][resolved_y0].mean()),
                "coverage_resolved_y1": float(contains_one[resolved][resolved_y1].mean()),
                "average_set_size": float(cardinality.mean()),
                "singleton_share": float(singleton.mean()),
                "set_empty_share": float(empty.mean()),
                "set_zero_only_share": float(zero_only.mean()),
                "set_one_only_share": float(one_only.mean()),
                "set_both_share": float(both.mean()),
                "mean_width": float(np.mean(upper - lower)),
            }

            reference = require_unique_row(
                canonical,
                key={"learner": learner, "window_id": window_id},
                label="conformal-set diagnostic reference coverage",
            )
            for count_column in ("candidate_rows", "resolved_rows", "unresolved_rows"):
                if int(row[count_column]) != int(reference[count_column]):
                    raise RuntimeError(
                        f"{learner}/{window_id} changed {count_column}: "
                        f"{row[count_column]} != {reference[count_column]}."
                    )
            for value_column in (
                "coverage_resolved",
                "mean_width",
                "set_empty_share",
                "set_zero_only_share",
                "set_one_only_share",
                "set_both_share",
            ):
                _require_close(
                    float(row[value_column]),
                    float(reference[value_column]),
                    label=f"{learner}/{window_id} {value_column}",
                    atol=reconciliation_atol,
                )
            _require_close(
                float(row["average_set_size"]),
                float(row["singleton_share"] + 2.0 * row["set_both_share"]),
                label=f"{learner}/{window_id} AvgC identity",
                atol=reconciliation_atol,
            )
            _require_close(
                float(row["average_set_size"]),
                float(1.0 - row["set_empty_share"] + row["set_both_share"]),
                label=f"{learner}/{window_id} AvgC partition identity",
                atol=reconciliation_atol,
            )
            _require_close(
                float(row["singleton_share"]),
                float(row["set_zero_only_share"] + row["set_one_only_share"]),
                label=f"{learner}/{window_id} OneC identity",
                atol=reconciliation_atol,
            )
            weighted_resolved_coverage = (
                row["resolved_y0_rows"] * row["coverage_resolved_y0"]
                + row["resolved_y1_rows"] * row["coverage_resolved_y1"]
            ) / row["resolved_rows"]
            _require_close(
                float(row["coverage_resolved"]),
                float(weighted_resolved_coverage),
                label=f"{learner}/{window_id} resolved-label coverage identity",
                atol=reconciliation_atol,
            )
            rows.append(row)

    result = pd.DataFrame(rows)
    require_exact_grid(
        result,
        domains={"learner": tuple(learners), "window_id": tuple(window_ids)},
        label="complete conformal-set diagnostics",
    )
    require_finite(
        result,
        (
            "coverage_resolved",
            "coverage_resolved_y0",
            "coverage_resolved_y1",
            "average_set_size",
            "singleton_share",
            "set_empty_share",
            "set_zero_only_share",
            "set_one_only_share",
            "set_both_share",
            "mean_width",
        ),
        label="complete conformal-set diagnostics",
    )
    learner_order = {name: index for index, name in enumerate(learners)}
    window_order = {name: index for index, name in enumerate(window_ids)}
    result["_learner_order"] = result["learner"].map(learner_order)
    result["_window_order"] = result["window_id"].map(window_order)
    return (
        result.sort_values(["_learner_order", "_window_order"])
        .drop(columns=["_learner_order", "_window_order"])
        .reset_index(drop=True)
    )


def conformal_set_diagnostic_ranges(table: pd.DataFrame) -> list[dict[str, Any]]:
    """Summarize complete per-learner ranges without choosing a window."""
    rows: list[dict[str, Any]] = []
    for learner, frame in table.groupby("learner", sort=False, observed=True):
        rows.append(
            {
                "learner": str(learner),
                "coverage_resolved_y0_min": float(frame["coverage_resolved_y0"].min()),
                "coverage_resolved_y0_max": float(frame["coverage_resolved_y0"].max()),
                "coverage_resolved_y1_min": float(frame["coverage_resolved_y1"].min()),
                "coverage_resolved_y1_max": float(frame["coverage_resolved_y1"].max()),
                "average_set_size_min": float(frame["average_set_size"].min()),
                "average_set_size_max": float(frame["average_set_size"].max()),
                "singleton_share_min": float(frame["singleton_share"].min()),
                "singleton_share_max": float(frame["singleton_share"].max()),
                "set_empty_share_min": float(frame["set_empty_share"].min()),
                "set_empty_share_max": float(frame["set_empty_share"].max()),
                "set_both_share_min": float(frame["set_both_share"].min()),
                "set_both_share_max": float(frame["set_both_share"].max()),
            }
        )
    return rows
