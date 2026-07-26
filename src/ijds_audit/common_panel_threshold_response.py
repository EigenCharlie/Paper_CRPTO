"""Exact adjacent-window threshold response on one frozen evaluation panel.

This module is deliberately evidence-neutral: it computes and validates the
integer identities needed by a future tagged replay, but it does not activate
any result or write paper-facing artifacts.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from hashlib import sha256
from itertools import pairwise
from typing import Any

import numpy as np
import pandas as pd

from src.ijds_audit.grid_contracts import require_exact_grid, require_unique_row
from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    apply_binary_outcome_recipe,
    assign_conformal_groups,
)

_REFERENCE_COLUMNS = {
    "learner",
    "window_id",
    "taxonomy_groups",
    "conformal_group",
    "role",
    "candidate_rows",
    "resolved_rows",
    "unresolved_rows",
    "resolved_misses",
    "coverage_resolved",
    "misses_min",
    "misses_max",
    "coverage_lower",
    "coverage_upper",
    "score_min",
    "score_max",
    "fit_residual_quantile",
}

_FIT_AUDIT_COLUMNS = {
    "id",
    "issue_d",
    "learner",
    "window_id",
    "taxonomy_groups",
    "conformal_group",
    "pd_point",
    "conformal_lower",
    "conformal_upper",
    "terminal_default",
    "covered",
}


def _declared_tuple(values: Sequence[str], *, label: str, length: int) -> tuple[str, ...]:
    declared = tuple(str(value) for value in values)
    if len(declared) != length or len(set(declared)) != length:
        raise ValueError(f"{label} must contain exactly {length} distinct values.")
    if any(not value for value in declared):
        raise ValueError(f"{label} may not contain empty values.")
    return declared


def _expected_count(value: int, *, label: str) -> int:
    if isinstance(value, (bool, np.bool_)) or int(value) != value or int(value) < 0:
        raise ValueError(f"{label} must be a nonnegative integer.")
    return int(value)


def _exact_integer(value: Any, *, label: str) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise RuntimeError(f"{label} is not an integer count.")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{label} is not numeric.") from exc
    if not np.isfinite(numeric) or not numeric.is_integer():
        raise RuntimeError(f"{label} is not an exact finite integer.")
    return int(numeric)


def _require_close_or_nan(
    actual: float,
    expected: Any,
    *,
    label: str,
    atol: float,
) -> None:
    try:
        reference = float(expected)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{label} is not numeric in the reference.") from exc
    if np.isnan(actual) and np.isnan(reference):
        return
    if not np.isfinite(actual) or not np.isfinite(reference):
        raise RuntimeError(f"{label} contains a nonfinite value.")
    if not np.isclose(actual, reference, atol=atol, rtol=0.0):
        raise RuntimeError(f"{label} did not reconcile: {actual!r} != {reference!r}.")


def _digest(parts: Sequence[bytes]) -> str:
    digest = sha256()
    for part in parts:
        digest.update(len(part).to_bytes(8, byteorder="little", signed=False))
        digest.update(part)
    return digest.hexdigest()


def _id_bytes(value: str) -> bytes:
    return value.encode("utf-8")


def _float_bytes(value: float) -> bytes:
    return np.asarray([value], dtype="<f8").tobytes()


def _int_bytes(value: int) -> bytes:
    return int(value).to_bytes(8, byteorder="little", signed=True)


def _hash_ids(ids: np.ndarray) -> str:
    return _digest([_id_bytes(str(value)) for value in ids])


def _hash_id_values(ids: np.ndarray, values: np.ndarray, *, integer: bool) -> str:
    parts: list[bytes] = []
    for identifier, value in zip(ids, values, strict=True):
        parts.append(_id_bytes(str(identifier)))
        parts.append(_int_bytes(int(value)) if integer else _float_bytes(float(value)))
    return _digest(parts)


def _validate_recipe(
    recipe: BinaryOutcomeConformalRecipe,
    *,
    learner: str,
    window_id: str,
    taxonomy_groups: int,
) -> tuple[np.ndarray, np.ndarray]:
    label = f"{learner}/{window_id}/{taxonomy_groups} recipe"
    if not isinstance(recipe, BinaryOutcomeConformalRecipe):
        raise RuntimeError(f"{label} has the wrong type.")
    if recipe.requested_groups != taxonomy_groups:
        raise RuntimeError(f"{label} changed requested_groups.")
    if recipe.alpha != 0.10:
        raise RuntimeError(f"{label} changed nominal miscoverage from 0.10.")
    if recipe.estimand != "binary_outcome_prediction_interval":
        raise RuntimeError(f"{label} changed the binary-outcome estimand.")
    if recipe.method != "fixed_taxonomy_split_mondrian_absolute_residual":
        raise RuntimeError(f"{label} is not the frozen fixed-taxonomy method.")
    if recipe.taxonomy_method != "fixed_empirical_linear_score_quantiles":
        raise RuntimeError(f"{label} changed the upstream taxonomy method.")
    expected_provenance = f"{learner}_201101_201112_all_status_independent_scores"
    if recipe.taxonomy_provenance != expected_provenance:
        raise RuntimeError(f"{label} changed taxonomy provenance.")
    if recipe.learned_widening or recipe.learned_floor:
        raise RuntimeError(f"{label} contains a learned widening or floor.")
    edges = np.asarray(recipe.bin_edges, dtype=float)
    quantiles = np.asarray(recipe.residual_quantiles, dtype=float)
    if (
        edges.shape != (taxonomy_groups + 1,)
        or not np.isfinite(edges).all()
        or np.any(np.diff(edges) <= 0.0)
    ):
        raise RuntimeError(f"{label} has invalid bin edges.")
    if (
        quantiles.shape != (taxonomy_groups,)
        or not np.isfinite(quantiles).all()
        or np.any((quantiles < 0.0) | (quantiles > 1.0))
    ):
        raise RuntimeError(f"{label} has invalid residual quantiles.")
    for field_name in ("group_counts", "finite_sample_ranks", "raw_finite_sample_ranks"):
        values = getattr(recipe, field_name)
        if len(values) != taxonomy_groups:
            raise RuntimeError(f"{label} changed {field_name} length.")
        for group, value in enumerate(values):
            integer = _exact_integer(value, label=f"{label} {field_name}[{group}]")
            if integer < 1:
                raise RuntimeError(f"{label} {field_name}[{group}] must be positive.")
    return edges, quantiles


def validate_residual_fit_audit(
    fit_audit: pd.DataFrame,
    recipes: Mapping[str, Mapping[str, Mapping[int, BinaryOutcomeConformalRecipe]]],
    *,
    learners: Sequence[str],
    window_ids: Sequence[str],
    taxonomy_groups: int,
    tolerance: float = 1.0e-12,
) -> dict[str, int]:
    """Recompute every frozen threshold from its calibration-row order statistic."""
    declared_learners = _declared_tuple(learners, label="learners", length=5)
    declared_windows = _declared_tuple(window_ids, label="window_ids", length=8)
    if isinstance(taxonomy_groups, (bool, np.bool_)) or taxonomy_groups != 5:
        raise ValueError("This contract requires exactly five taxonomy groups.")
    if not np.isfinite(tolerance) or tolerance < 0.0 or tolerance > 1.0e-12:
        raise ValueError("tolerance must be finite, nonnegative, and at most 1e-12.")
    missing = sorted(_FIT_AUDIT_COLUMNS.difference(fit_audit.columns))
    if missing:
        raise ValueError(f"Residual-fit audit omits columns: {missing}")
    if set(recipes) != set(declared_learners):
        raise RuntimeError("Frozen recipe learner domain changed.")

    frame = fit_audit.copy()
    taxonomy_numeric = pd.to_numeric(frame["taxonomy_groups"], errors="raise")
    if bool(taxonomy_numeric.isna().any()) or bool((taxonomy_numeric % 1.0 != 0.0).any()):
        raise RuntimeError("Residual-fit taxonomy_groups must contain exact integers.")
    frame["taxonomy_groups"] = taxonomy_numeric.astype(int)
    frame = frame.loc[frame["taxonomy_groups"].eq(taxonomy_groups)].copy()
    if frame.empty:
        raise RuntimeError("Residual-fit audit has no rows for the declared taxonomy.")
    if frame["learner"].isna().any() or frame["window_id"].isna().any():
        raise RuntimeError("Residual-fit learner or window identity is missing.")
    frame["learner"] = frame["learner"].astype(str)
    frame["window_id"] = frame["window_id"].astype(str)
    if set(frame["learner"].unique()) != set(declared_learners):
        raise RuntimeError("Residual-fit learner domain changed.")
    if set(frame["window_id"].unique()) != set(declared_windows):
        raise RuntimeError("Residual-fit window domain changed.")
    group_numeric = pd.to_numeric(frame["conformal_group"], errors="raise")
    if bool(group_numeric.isna().any()) or bool((group_numeric % 1.0 != 0.0).any()):
        raise RuntimeError("Residual-fit conformal_group must contain exact integers.")
    frame["conformal_group"] = group_numeric.astype(int)
    if not frame["conformal_group"].between(0, taxonomy_groups - 1).all():
        raise RuntimeError("Residual-fit conformal_group left the declared domain.")
    expected_cells = {
        (learner, window_id, group)
        for learner in declared_learners
        for window_id in declared_windows
        for group in range(taxonomy_groups)
    }
    actual_cells = set(
        frame[["learner", "window_id", "conformal_group"]].itertuples(index=False, name=None)
    )
    if actual_cells != expected_cells:
        missing_cells = sorted(expected_cells.difference(actual_cells), key=repr)[:5]
        extra_cells = sorted(actual_cells.difference(expected_cells), key=repr)[:5]
        raise RuntimeError(
            f"Residual-fit cell grid changed; missing={missing_cells}, extra={extra_cells}."
        )
    if frame["id"].isna().any():
        raise RuntimeError("Residual-fit IDs contain missing values.")
    frame["_canonical_id"] = frame["id"].astype(str)
    if (
        frame["_canonical_id"].eq("").any()
        or frame.duplicated(["learner", "window_id", "_canonical_id"]).any()
    ):
        raise RuntimeError("Residual-fit IDs are empty or duplicated within learner-window.")
    parsed_dates = pd.to_datetime(frame["issue_d"], errors="raise")
    if parsed_dates.isna().any():
        raise RuntimeError("Residual-fit issue dates contain missing values.")
    for column in ("pd_point", "conformal_lower", "conformal_upper", "terminal_default"):
        numeric = pd.to_numeric(frame[column], errors="raise")
        if not np.isfinite(numeric.to_numpy(dtype=float)).all():
            raise RuntimeError(f"Residual-fit {column} contains nonfinite values.")
        frame[column] = numeric.astype(float)
    if not frame["pd_point"].between(0.0, 1.0).all():
        raise RuntimeError("Residual-fit scores left [0, 1].")
    if not frame["terminal_default"].isin((0.0, 1.0)).all():
        raise RuntimeError("Residual-fit outcomes are not binary.")
    if (
        not frame["conformal_lower"].between(0.0, 1.0).all()
        or not frame["conformal_upper"].between(0.0, 1.0).all()
    ):
        raise RuntimeError("Residual-fit conformal endpoints left [0, 1].")
    if frame["covered"].isna().any() or not frame["covered"].isin((True, False)).all():
        raise RuntimeError("Residual-fit covered flag is not binary.")

    grouped = frame.groupby(["learner", "window_id", "conformal_group"], observed=True, sort=False)
    capped_cells = 0
    tied_threshold_cells = 0
    for learner in declared_learners:
        learner_recipes = recipes[learner]
        if set(learner_recipes) != set(declared_windows):
            raise RuntimeError(f"Frozen recipe window domain changed for {learner!r}.")
        common_edges: np.ndarray | None = None
        for window_id in declared_windows:
            taxonomy_map = learner_recipes[window_id]
            if taxonomy_groups not in taxonomy_map:
                raise RuntimeError(
                    f"Frozen recipe grid omits {learner}/{window_id}/{taxonomy_groups}."
                )
            recipe = taxonomy_map[taxonomy_groups]
            edges, quantiles = _validate_recipe(
                recipe,
                learner=learner,
                window_id=window_id,
                taxonomy_groups=taxonomy_groups,
            )
            if common_edges is None:
                common_edges = edges
            elif not np.array_equal(common_edges, edges):
                raise RuntimeError(f"Score-stratum edges changed across windows for {learner!r}.")
            for group in range(taxonomy_groups):
                block = grouped.get_group((learner, window_id, group))
                count = len(block)
                recipe_count = _exact_integer(
                    recipe.group_counts[group],
                    label=f"{learner}/{window_id}/stratum-{group} group_count",
                )
                if count != recipe_count:
                    raise RuntimeError(
                        f"{learner}/{window_id}/stratum-{group} fit count changed: "
                        f"{count} != {recipe_count}."
                    )
                raw_rank = math.ceil((count + 1) * (1.0 - recipe.alpha))
                frozen_raw_rank = _exact_integer(
                    recipe.raw_finite_sample_ranks[group],
                    label=f"{learner}/{window_id}/stratum-{group} raw rank",
                )
                finite_rank = min(raw_rank, count)
                frozen_rank = _exact_integer(
                    recipe.finite_sample_ranks[group],
                    label=f"{learner}/{window_id}/stratum-{group} finite rank",
                )
                if raw_rank != frozen_raw_rank or finite_rank != frozen_rank:
                    raise RuntimeError(
                        f"{learner}/{window_id}/stratum-{group} rank convention changed."
                    )

                point = block["pd_point"].to_numpy(dtype=float)
                labels = block["terminal_default"].to_numpy(dtype=float)
                assigned = assign_conformal_groups(point, tuple(float(value) for value in edges))
                if not np.equal(assigned, group).all():
                    raise RuntimeError(f"{learner}/{window_id}/stratum-{group} assignment changed.")
                residual = np.abs(labels - point)
                threshold = 1.0 if raw_rank > count else float(np.sort(residual)[raw_rank - 1])
                frozen_threshold = float(quantiles[group])
                if not np.isclose(threshold, frozen_threshold, atol=tolerance, rtol=0.0):
                    raise RuntimeError(
                        f"{learner}/{window_id}/stratum-{group} threshold left its order statistic."
                    )
                capped_cells += int(raw_rank > count)
                ties = int(np.sum(np.isclose(residual, frozen_threshold, atol=tolerance, rtol=0.0)))
                tied_threshold_cells += int(ties > 1)

                lower = np.clip(point - frozen_threshold, 0.0, 1.0)
                upper = np.clip(point + frozen_threshold, 0.0, 1.0)
                if (
                    not np.isclose(
                        lower,
                        block["conformal_lower"].to_numpy(dtype=float),
                        atol=tolerance,
                        rtol=0.0,
                    ).all()
                    or not np.isclose(
                        upper,
                        block["conformal_upper"].to_numpy(dtype=float),
                        atol=tolerance,
                        rtol=0.0,
                    ).all()
                ):
                    raise RuntimeError(f"{learner}/{window_id}/stratum-{group} endpoints changed.")
                covered = (labels >= lower) & (labels <= upper)
                if not np.array_equal(covered, block["covered"].to_numpy(dtype=bool)):
                    raise RuntimeError(
                        f"{learner}/{window_id}/stratum-{group} covered flag changed."
                    )
                if not np.array_equal(covered, residual <= frozen_threshold):
                    raise RuntimeError(
                        f"{learner}/{window_id}/stratum-{group} endpoint and residual "
                        "membership disagree."
                    )

    return {
        "fit_audit_rows": len(frame),
        "fit_audit_cells": len(actual_cells),
        "capped_cells": capped_cells,
        "tied_threshold_cells": tied_threshold_cells,
    }


def _prepare_reference(
    reference: pd.DataFrame,
    *,
    learners: tuple[str, ...],
    window_ids: tuple[str, ...],
    role: str,
    taxonomy_groups: int,
) -> pd.DataFrame:
    missing = sorted(_REFERENCE_COLUMNS.difference(reference.columns))
    if missing:
        raise ValueError(f"Reference coverage omits columns: {missing}")
    prepared = reference.copy()
    for column in ("taxonomy_groups", "conformal_group"):
        numeric = pd.to_numeric(prepared[column], errors="raise")
        if bool(numeric.isna().any()) or bool((numeric % 1.0 != 0.0).any()):
            raise RuntimeError(f"Reference {column} must contain exact integers.")
        prepared[column] = numeric.astype(int)
    scope = prepared.loc[
        prepared["role"].eq(role) & prepared["taxonomy_groups"].eq(taxonomy_groups)
    ].copy()
    if not scope["conformal_group"].isin((-1, *range(taxonomy_groups))).all():
        raise RuntimeError("Reference conformal_group left the aggregate-plus-strata domain.")
    selected = scope.loc[scope["conformal_group"].between(0, taxonomy_groups - 1)].copy()
    require_exact_grid(
        selected,
        domains={
            "learner": learners,
            "window_id": window_ids,
            "conformal_group": tuple(range(taxonomy_groups)),
        },
        label="common-panel threshold-response reference",
    )
    return selected


def _reconcile_reference_row(
    reference: pd.Series,
    *,
    learner: str,
    window_id: str,
    group: int,
    scores: np.ndarray,
    labels: np.ndarray,
    resolved: np.ndarray,
    contains_zero: np.ndarray,
    contains_one: np.ndarray,
    threshold: float,
    atol: float,
) -> None:
    label = f"{learner}/{window_id}/stratum-{group}"
    candidate_rows = int(len(scores))
    resolved_rows = int(resolved.sum())
    unresolved_rows = candidate_rows - resolved_rows
    covered_resolved = int(
        np.sum(resolved & (((labels == 0.0) & contains_zero) | ((labels == 1.0) & contains_one)))
    )
    resolved_misses = resolved_rows - covered_resolved
    unresolved = ~resolved
    empty = ~contains_zero & ~contains_one
    not_full = ~(contains_zero & contains_one)
    misses_min = resolved_misses + int(np.sum(unresolved & empty))
    misses_max = resolved_misses + int(np.sum(unresolved & not_full))
    actual_integer = {
        "candidate_rows": candidate_rows,
        "resolved_rows": resolved_rows,
        "unresolved_rows": unresolved_rows,
        "resolved_misses": resolved_misses,
        "misses_min": misses_min,
        "misses_max": misses_max,
    }
    for column, actual in actual_integer.items():
        expected = _exact_integer(reference[column], label=f"{label} {column}")
        if actual != expected:
            raise RuntimeError(f"{label} {column} changed: {actual} != {expected}.")
    coverage_resolved = covered_resolved / resolved_rows if resolved_rows else float("nan")
    actual_float = {
        "coverage_resolved": coverage_resolved,
        "coverage_lower": 1.0 - misses_max / candidate_rows,
        "coverage_upper": 1.0 - misses_min / candidate_rows,
        "score_min": float(np.min(scores)),
        "score_max": float(np.max(scores)),
        "fit_residual_quantile": threshold,
    }
    for column, actual_float_value in actual_float.items():
        _require_close_or_nan(
            actual_float_value,
            reference[column],
            label=f"{label} {column}",
            atol=atol,
        )


def _pair_cell(
    *,
    learner: str,
    pair_index: int,
    window_from: str,
    window_to: str,
    group: int,
    taxonomy_groups: int,
    scores: np.ndarray,
    labels: np.ndarray,
    resolved: np.ndarray,
    threshold_from: float,
    threshold_to: float,
    contains_zero_from: np.ndarray,
    contains_one_from: np.ndarray,
    contains_zero_to: np.ndarray,
    contains_one_to: np.ndarray,
    ids_sha256: str,
    scores_sha256: str,
    assignments_sha256: str,
) -> dict[str, Any]:
    threshold_low = min(threshold_from, threshold_to)
    threshold_high = max(threshold_from, threshold_to)
    threshold_delta = threshold_to - threshold_from
    threshold_sign = int(np.sign(threshold_delta))

    d0 = contains_zero_to.astype(np.int8) - contains_zero_from.astype(np.int8)
    d1 = contains_one_to.astype(np.int8) - contains_one_from.astype(np.int8)
    band0 = (scores > threshold_low) & (scores <= threshold_high)
    band1 = (scores >= 1.0 - threshold_high) & (scores < 1.0 - threshold_low)
    if not np.array_equal(d0, threshold_sign * band0.astype(np.int8)):
        raise RuntimeError(
            f"{learner}/{window_from}->{window_to}/stratum-{group} violated the y=0 "
            "ordered crossed-band identity."
        )
    if not np.array_equal(d1, threshold_sign * band1.astype(np.int8)):
        raise RuntimeError(
            f"{learner}/{window_from}->{window_to}/stratum-{group} violated the y=1 "
            "ordered crossed-band identity."
        )

    resolved_y0 = resolved & (labels == 0.0)
    resolved_y1 = resolved & (labels == 1.0)
    y0_delta = int(np.sum(d0[resolved_y0], dtype=np.int64))
    y1_delta = int(np.sum(d1[resolved_y1], dtype=np.int64))
    resolved_delta = y0_delta + y1_delta
    covered_from = int(
        np.sum(
            (resolved_y0 & contains_zero_from) | (resolved_y1 & contains_one_from),
            dtype=np.int64,
        )
    )
    covered_to = int(
        np.sum(
            (resolved_y0 & contains_zero_to) | (resolved_y1 & contains_one_to),
            dtype=np.int64,
        )
    )
    if covered_to - covered_from != resolved_delta:
        raise RuntimeError("Resolved coverage-change numerators do not reconcile exactly.")

    unresolved = ~resolved
    lower_contribution = np.minimum(d0, d1)
    upper_contribution = np.maximum(d0, d1)
    lower_numerator = resolved_delta + int(np.sum(lower_contribution[unresolved], dtype=np.int64))
    upper_numerator = resolved_delta + int(np.sum(upper_contribution[unresolved], dtype=np.int64))
    width_numerator = int(
        np.sum((upper_contribution - lower_contribution)[unresolved], dtype=np.int64)
    )
    if upper_numerator - lower_numerator != width_numerator:
        raise RuntimeError("Sharp completion-bound width failed exact integer reconciliation.")

    candidate_rows = int(len(scores))
    resolved_rows = int(resolved.sum())
    return {
        "learner": learner,
        "pair_id": f"{pair_index:02d}:{window_from}->{window_to}",
        "pair_index": pair_index,
        "window_from": window_from,
        "window_to": window_to,
        "taxonomy_groups": taxonomy_groups,
        "conformal_group": group,
        "score_stratum": group + 1,
        "candidate_rows": candidate_rows,
        "resolved_rows": resolved_rows,
        "unresolved_rows": candidate_rows - resolved_rows,
        "threshold_from": threshold_from,
        "threshold_to": threshold_to,
        "threshold_low": threshold_low,
        "threshold_high": threshold_high,
        "threshold_delta": threshold_delta,
        "threshold_sign": threshold_sign,
        "potential_y0_crossed_rows": int(band0.sum()),
        "potential_y1_crossed_rows": int(band1.sum()),
        "resolved_y0_crossed_rows": int(np.sum(resolved_y0 & band0)),
        "resolved_y1_crossed_rows": int(np.sum(resolved_y1 & band1)),
        "resolved_y0_delta_numerator": y0_delta,
        "resolved_y1_delta_numerator": y1_delta,
        "resolved_delta_numerator": resolved_delta,
        "resolved_covered_from_numerator": covered_from,
        "resolved_covered_to_numerator": covered_to,
        "resolved_delta_rate": (resolved_delta / resolved_rows if resolved_rows else float("nan")),
        "delta_lower_numerator": lower_numerator,
        "delta_upper_numerator": upper_numerator,
        "delta_width_numerator": width_numerator,
        "delta_lower": lower_numerator / candidate_rows,
        "delta_upper": upper_numerator / candidate_rows,
        "delta_width": width_numerator / candidate_rows,
        "ids_sha256": ids_sha256,
        "scores_sha256": scores_sha256,
        "assignments_sha256": assignments_sha256,
    }


def _pool_cells(cells: pd.DataFrame, *, taxonomy_groups: int) -> pd.DataFrame:
    integer_sums = (
        "candidate_rows",
        "resolved_rows",
        "unresolved_rows",
        "potential_y0_crossed_rows",
        "potential_y1_crossed_rows",
        "resolved_y0_crossed_rows",
        "resolved_y1_crossed_rows",
        "resolved_y0_delta_numerator",
        "resolved_y1_delta_numerator",
        "resolved_delta_numerator",
        "resolved_covered_from_numerator",
        "resolved_covered_to_numerator",
        "delta_lower_numerator",
        "delta_upper_numerator",
        "delta_width_numerator",
    )
    rows: list[dict[str, Any]] = []
    keys = ["learner", "pair_id", "pair_index", "window_from", "window_to"]
    for key, group_frame in cells.groupby(keys, sort=False, dropna=False):
        if len(group_frame) != taxonomy_groups:
            raise RuntimeError("Pooled threshold response does not contain every score stratum.")
        row: dict[str, Any] = dict(zip(keys, key, strict=True))
        row["taxonomy_groups"] = taxonomy_groups
        row["strata_rows"] = int(len(group_frame))
        for column in integer_sums:
            row[column] = int(group_frame[column].sum())
        for sign, name in ((-1, "decrease"), (0, "equal"), (1, "increase")):
            row[f"threshold_{name}_strata"] = int(group_frame["threshold_sign"].eq(sign).sum())
        if (
            row["resolved_covered_to_numerator"] - row["resolved_covered_from_numerator"]
            != row["resolved_delta_numerator"]
        ):
            raise RuntimeError("Pooled resolved numerators do not reconcile exactly.")
        if (
            row["delta_upper_numerator"] - row["delta_lower_numerator"]
            != row["delta_width_numerator"]
        ):
            raise RuntimeError("Pooled completion-bound width does not reconcile exactly.")
        candidate_rows = int(row["candidate_rows"])
        resolved_rows = int(row["resolved_rows"])
        row["resolved_delta_rate"] = (
            row["resolved_delta_numerator"] / resolved_rows if resolved_rows else float("nan")
        )
        row["delta_lower"] = row["delta_lower_numerator"] / candidate_rows
        row["delta_upper"] = row["delta_upper_numerator"] / candidate_rows
        row["delta_width"] = row["delta_width_numerator"] / candidate_rows
        rows.append(row)
    pooled = pd.DataFrame(rows)
    if len(pooled) != 35:
        raise RuntimeError(f"Expected 35 pooled rows, found {len(pooled)}.")
    return pooled.reset_index(drop=True)


def build_common_panel_threshold_response(
    scores: pd.DataFrame,
    outcomes: pd.DataFrame,
    recipes: Mapping[str, Mapping[str, Mapping[int, BinaryOutcomeConformalRecipe]]],
    reference: pd.DataFrame,
    *,
    fit_audit: pd.DataFrame,
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
    tolerance: float = 1.0e-12,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Build exact adjacent-window response cells, pooled rows, and hashes.

    The result has 175 stratum rows (five learners by five strata by seven
    adjacent window pairs) and 35 learner-pair rows. Bounds are sharp over all
    binary completions of unresolved labels on the same fixed panel.
    """
    declared_learners = _declared_tuple(learners, label="learners", length=5)
    declared_windows = _declared_tuple(window_ids, label="window_ids", length=8)
    declared_months = tuple(str(value) for value in expected_issue_months)
    if not declared_months or len(set(declared_months)) != len(declared_months):
        raise ValueError("expected_issue_months must contain distinct values.")
    if not isinstance(role, str) or not role:
        raise ValueError("role must be a nonempty string.")
    if isinstance(taxonomy_groups, (bool, np.bool_)) or taxonomy_groups != 5:
        raise ValueError("This contract requires exactly five taxonomy groups.")
    if not np.isfinite(tolerance) or tolerance < 0.0 or tolerance > 1.0e-12:
        raise ValueError("tolerance must be finite, nonnegative, and at most 1e-12.")
    expected = {
        "candidate": _expected_count(expected_candidates, label="expected_candidates"),
        "resolved": _expected_count(expected_resolved, label="expected_resolved"),
        "unresolved": _expected_count(expected_unresolved, label="expected_unresolved"),
        "resolved_y0": _expected_count(expected_resolved_y0, label="expected_resolved_y0"),
        "resolved_y1": _expected_count(expected_resolved_y1, label="expected_resolved_y1"),
    }
    if expected["resolved"] + expected["unresolved"] != expected["candidate"]:
        raise ValueError("Expected resolved and unresolved counts must sum to candidates.")
    if expected["resolved_y0"] + expected["resolved_y1"] != expected["resolved"]:
        raise ValueError("Expected class counts must sum to resolved rows.")

    required_scores = {"id", "issue_d", "design_split"}
    required_scores.update(f"pd_{learner}" for learner in declared_learners)
    missing_scores = sorted(required_scores.difference(scores.columns))
    if missing_scores:
        raise ValueError(f"Frozen scores omit columns: {missing_scores}")
    if not {"id", "snapshot_default"}.issubset(outcomes.columns):
        raise ValueError("Endpoint outcomes must contain id and snapshot_default.")

    panel = scores.loc[scores["design_split"].eq(role)].copy()
    if len(panel) != expected["candidate"] or panel["id"].duplicated().any():
        raise RuntimeError("Fixed-panel score census or ID uniqueness changed.")
    if panel["id"].isna().any():
        raise RuntimeError("Fixed-panel IDs contain missing values.")
    panel["_canonical_id"] = panel["id"].astype(str)
    if panel["_canonical_id"].eq("").any() or panel["_canonical_id"].duplicated().any():
        raise RuntimeError("Fixed-panel IDs are empty or collide after canonicalization.")
    issue_month = pd.to_datetime(panel["issue_d"], errors="raise").dt.to_period("M").astype(str)
    actual_months = tuple(sorted(issue_month.unique()))
    if actual_months != declared_months:
        raise RuntimeError(
            f"Fixed-panel issue-month set changed: {actual_months!r} != {declared_months!r}."
        )

    endpoint = outcomes.loc[:, ["id", "snapshot_default"]].copy()
    if endpoint["id"].isna().any() or endpoint["id"].duplicated().any():
        raise RuntimeError("Endpoint outcomes contain missing or duplicate IDs.")
    panel = panel.merge(
        endpoint,
        on="id",
        how="left",
        validate="one_to_one",
        indicator="_endpoint_merge",
    )
    if not panel["_endpoint_merge"].eq("both").all():
        examples = panel.loc[~panel["_endpoint_merge"].eq("both"), "id"].head(5).tolist()
        raise RuntimeError(f"Endpoint alignment is incomplete; examples={examples!r}.")
    panel = panel.drop(columns="_endpoint_merge").sort_values("_canonical_id", kind="stable")
    panel = panel.reset_index(drop=True)

    raw_labels = panel["snapshot_default"]
    resolved = raw_labels.notna().to_numpy(dtype=bool)
    labels = np.full(len(panel), np.nan, dtype=float)
    if resolved.any():
        try:
            resolved_labels = pd.to_numeric(raw_labels.loc[resolved], errors="raise").to_numpy(
                dtype=float
            )
        except (TypeError, ValueError) as exc:
            raise RuntimeError("Resolved endpoint contains a nonnumeric outcome.") from exc
        if not np.isfinite(resolved_labels).all() or not np.isin(resolved_labels, (0.0, 1.0)).all():
            raise RuntimeError("Resolved endpoint contains a nonbinary outcome.")
        labels[resolved] = resolved_labels
    actual_census = {
        "candidate": len(panel),
        "resolved": int(resolved.sum()),
        "unresolved": int((~resolved).sum()),
        "resolved_y0": int(np.sum(labels == 0.0)),
        "resolved_y1": int(np.sum(labels == 1.0)),
    }
    if actual_census != expected:
        raise RuntimeError(
            f"Fixed-panel outcome census changed: {actual_census!r} != {expected!r}."
        )

    if set(recipes) != set(declared_learners):
        raise RuntimeError("Frozen recipe learner domain changed.")
    fit_audit_summary = validate_residual_fit_audit(
        fit_audit,
        recipes,
        learners=declared_learners,
        window_ids=declared_windows,
        taxonomy_groups=taxonomy_groups,
        tolerance=tolerance,
    )
    canonical_reference = _prepare_reference(
        reference,
        learners=declared_learners,
        window_ids=declared_windows,
        role=role,
        taxonomy_groups=taxonomy_groups,
    )
    canonical_ids = panel["_canonical_id"].to_numpy(dtype=str)
    summary: dict[str, Any] = {
        "status": "candidate_module_only_no_active_evidence",
        "candidate_rows": len(panel),
        "resolved_rows": int(resolved.sum()),
        "unresolved_rows": int((~resolved).sum()),
        "learners": list(declared_learners),
        "window_ids": list(declared_windows),
        "taxonomy_groups": taxonomy_groups,
        "adjacent_pairs": len(declared_windows) - 1,
        "ids_sha256": _hash_ids(canonical_ids),
        "fit_audit": fit_audit_summary,
        "panel_hashes": {},
    }

    rows: list[dict[str, Any]] = []
    for learner in declared_learners:
        learner_recipes = recipes[learner]
        if set(learner_recipes) != set(declared_windows):
            raise RuntimeError(f"Frozen recipe window domain changed for {learner!r}.")
        probabilities = pd.to_numeric(panel[f"pd_{learner}"], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(probabilities).all() or np.any(
            (probabilities < 0.0) | (probabilities > 1.0)
        ):
            raise RuntimeError(f"Frozen probabilities are invalid for learner {learner!r}.")

        edges_by_window: dict[str, np.ndarray] = {}
        quantiles_by_window: dict[str, np.ndarray] = {}
        selected_recipes: dict[str, BinaryOutcomeConformalRecipe] = {}
        for window_id in declared_windows:
            taxonomy_map = learner_recipes[window_id]
            if taxonomy_groups not in taxonomy_map:
                raise RuntimeError(
                    f"Frozen recipe grid omits {learner}/{window_id}/{taxonomy_groups}."
                )
            recipe = taxonomy_map[taxonomy_groups]
            edges, quantiles = _validate_recipe(
                recipe,
                learner=learner,
                window_id=window_id,
                taxonomy_groups=taxonomy_groups,
            )
            selected_recipes[window_id] = recipe
            edges_by_window[window_id] = edges
            quantiles_by_window[window_id] = quantiles
        common_edges = edges_by_window[declared_windows[0]]
        for window_id in declared_windows[1:]:
            if not np.array_equal(common_edges, edges_by_window[window_id]):
                raise RuntimeError(f"Score-stratum edges changed across windows for {learner!r}.")

        assignments = assign_conformal_groups(
            probabilities, tuple(float(value) for value in common_edges)
        )
        if not np.array_equal(np.unique(assignments), np.arange(taxonomy_groups)):
            raise RuntimeError(f"Fixed panel does not populate all score strata for {learner!r}.")
        learner_hashes: dict[str, Any] = {
            "edges_sha256": _digest([_float_bytes(value) for value in common_edges]),
            "scores_sha256": _hash_id_values(canonical_ids, probabilities, integer=False),
            "assignments_sha256": _hash_id_values(canonical_ids, assignments, integer=True),
            "strata": {},
        }
        for group in range(taxonomy_groups):
            group_mask = assignments == group
            learner_hashes["strata"][str(group)] = {
                "ids_sha256": _hash_ids(canonical_ids[group_mask]),
                "scores_sha256": _hash_id_values(
                    canonical_ids[group_mask], probabilities[group_mask], integer=False
                ),
                "assignments_sha256": _hash_id_values(
                    canonical_ids[group_mask], assignments[group_mask], integer=True
                ),
            }
        summary["panel_hashes"][learner] = learner_hashes

        states: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for window_id in declared_windows:
            applied_groups, lower, upper = apply_binary_outcome_recipe(
                probabilities, selected_recipes[window_id]
            )
            if not np.array_equal(applied_groups, assignments):
                raise RuntimeError(
                    f"Recipe assignments changed for {learner}/{window_id} on the fixed panel."
                )
            contains_zero = lower <= 0.0
            contains_one = upper >= 1.0
            states[window_id] = (contains_zero, contains_one)
            for group in range(taxonomy_groups):
                mask = assignments == group
                reference_row = require_unique_row(
                    canonical_reference,
                    key={
                        "learner": learner,
                        "window_id": window_id,
                        "conformal_group": group,
                    },
                    label="common-panel threshold-response reference",
                )
                _reconcile_reference_row(
                    reference_row,
                    learner=learner,
                    window_id=window_id,
                    group=group,
                    scores=probabilities[mask],
                    labels=labels[mask],
                    resolved=resolved[mask],
                    contains_zero=contains_zero[mask],
                    contains_one=contains_one[mask],
                    threshold=float(quantiles_by_window[window_id][group]),
                    atol=tolerance,
                )

        for pair_index, (window_from, window_to) in enumerate(pairwise(declared_windows)):
            contains_zero_from, contains_one_from = states[window_from]
            contains_zero_to, contains_one_to = states[window_to]
            for group in range(taxonomy_groups):
                mask = assignments == group
                hashes = learner_hashes["strata"][str(group)]
                rows.append(
                    _pair_cell(
                        learner=learner,
                        pair_index=pair_index,
                        window_from=window_from,
                        window_to=window_to,
                        group=group,
                        taxonomy_groups=taxonomy_groups,
                        scores=probabilities[mask],
                        labels=labels[mask],
                        resolved=resolved[mask],
                        threshold_from=float(quantiles_by_window[window_from][group]),
                        threshold_to=float(quantiles_by_window[window_to][group]),
                        contains_zero_from=contains_zero_from[mask],
                        contains_one_from=contains_one_from[mask],
                        contains_zero_to=contains_zero_to[mask],
                        contains_one_to=contains_one_to[mask],
                        ids_sha256=hashes["ids_sha256"],
                        scores_sha256=hashes["scores_sha256"],
                        assignments_sha256=hashes["assignments_sha256"],
                    )
                )

    strata = pd.DataFrame(rows).reset_index(drop=True)
    if len(strata) != 175:
        raise RuntimeError(f"Expected 175 stratum rows, found {len(strata)}.")
    pooled = _pool_cells(strata, taxonomy_groups=taxonomy_groups)
    summary["strata_rows"] = len(strata)
    summary["pooled_rows"] = len(pooled)
    return strata, pooled, summary
