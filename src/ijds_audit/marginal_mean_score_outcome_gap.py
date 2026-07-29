"""Sharp finite-archive bounds for the marginal mean-score--outcome gap."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import numpy as np
import pandas as pd

ESTIMAND = "marginal_mean_score_outcome_gap"
RESOLVED_DEFAULT_REASON = "charged_off_by_reconstructed_cutoff"
RESOLVED_NONDEFAULT_REASON = "fully_paid_by_reconstructed_cutoff"
ENDPOINT_COLUMNS = (
    "role",
    "snapshot_resolution",
    "candidate_rows",
    "resolved_rows",
    "unresolved_rows",
)


@dataclass(frozen=True)
class MarginalMeanScoreOutcomeGapResult:
    """Complete five-learner table plus deterministic input-census evidence."""

    table: pd.DataFrame
    candidate_id_sha256: str
    issue_months: tuple[str, ...]
    endpoint_reason_census: tuple[dict[str, str | int], ...]


def _exact_nonnegative_integer(value: Any, *, label: str) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise RuntimeError(f"{label} is not an integer count.")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{label} is not numeric.") from exc
    if not np.isfinite(numeric) or not numeric.is_integer() or numeric < 0.0:
        raise RuntimeError(f"{label} is not an exact nonnegative integer.")
    return int(numeric)


def _hash_sorted_ids(values: pd.Series) -> str:
    identifiers = values.astype("string")
    if identifiers.isna().any():
        raise RuntimeError("The target candidate identifier census contains a missing value.")
    rendered = identifiers.astype(str)
    if rendered.str.strip().eq("").any():
        raise RuntimeError("The target candidate identifier census contains an empty value.")
    if rendered.duplicated().any():
        raise RuntimeError("The target candidate identifier census contains duplicates.")
    digest = sha256()
    for identifier in sorted(rendered.tolist()):
        encoded = identifier.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, byteorder="little", signed=False))
        digest.update(encoded)
    return digest.hexdigest()


def normalize_endpoint_resolution_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate and canonically order an aggregate endpoint-reason table."""
    missing = set(ENDPOINT_COLUMNS).difference(frame.columns)
    if missing:
        raise ValueError(f"Endpoint-reason table omits columns: {sorted(missing)}")
    table = frame.loc[:, list(ENDPOINT_COLUMNS)].copy()
    for column in ("role", "snapshot_resolution"):
        if table[column].isna().any():
            raise RuntimeError(f"Endpoint-reason column {column!r} contains a missing value.")
        table[column] = table[column].astype(str)
        if table[column].str.strip().eq("").any():
            raise RuntimeError(f"Endpoint-reason column {column!r} contains an empty value.")
    if table.duplicated(["role", "snapshot_resolution"]).any():
        raise RuntimeError("Endpoint-reason keys are duplicated.")
    for column in ("candidate_rows", "resolved_rows", "unresolved_rows"):
        table[column] = pd.Series(
            [
                _exact_nonnegative_integer(value, label=f"Endpoint {column}")
                for value in table[column].tolist()
            ],
            index=table.index,
            dtype="int64",
        )
    partitioned = table["resolved_rows"] + table["unresolved_rows"]
    if not bool(table["candidate_rows"].eq(partitioned).all()):
        raise RuntimeError(
            "An endpoint reason does not partition into resolved and unresolved rows."
        )
    return table.sort_values(["role", "snapshot_resolution"], kind="mergesort").reset_index(
        drop=True
    )


def _validated_primary_endpoint_census(
    endpoint_resolution: pd.DataFrame,
    *,
    role: str,
    expected_reason_census: Mapping[str, Mapping[str, int]],
    expected_candidates: int,
    expected_resolved: int,
    expected_unresolved: int,
    expected_resolved_y0: int,
    expected_resolved_y1: int,
) -> tuple[pd.DataFrame, int, int]:
    table = normalize_endpoint_resolution_table(endpoint_resolution)
    primary = table.loc[table["role"].eq(str(role))].reset_index(drop=True)
    if primary.empty:
        raise RuntimeError(f"Endpoint-reason table omits role {role!r}.")
    expected_reasons = tuple(str(reason) for reason in expected_reason_census)
    if len(expected_reasons) != len(set(expected_reasons)) or not expected_reasons:
        raise ValueError("Expected endpoint reasons must be nonempty and unique.")
    actual_reasons = set(primary["snapshot_resolution"].tolist())
    if actual_reasons != set(expected_reasons) or len(primary) != len(expected_reasons):
        raise RuntimeError("The target endpoint-reason partition changed.")

    for reason, expected in expected_reason_census.items():
        if not isinstance(expected, Mapping):
            raise TypeError(f"Expected endpoint reason {reason!r} must be a mapping.")
        row = primary.loc[primary["snapshot_resolution"].eq(str(reason))]
        if len(row) != 1:
            raise RuntimeError(f"Endpoint reason {reason!r} is not unique.")
        for column in ("candidate_rows", "resolved_rows", "unresolved_rows"):
            if column not in expected:
                raise ValueError(f"Expected endpoint reason {reason!r} omits {column!r}.")
            expected_value = _exact_nonnegative_integer(
                expected[column], label=f"Expected {reason}/{column}"
            )
            if int(row[column].iloc[0]) != expected_value:
                raise RuntimeError(
                    f"Endpoint reason {reason!r} changed on {column}: "
                    f"{int(row[column].iloc[0])} != {expected_value}."
                )

    totals = (
        int(primary["candidate_rows"].sum()),
        int(primary["resolved_rows"].sum()),
        int(primary["unresolved_rows"].sum()),
    )
    expected_totals = (
        _exact_nonnegative_integer(expected_candidates, label="Expected candidates"),
        _exact_nonnegative_integer(expected_resolved, label="Expected resolved rows"),
        _exact_nonnegative_integer(expected_unresolved, label="Expected unresolved rows"),
    )
    if totals != expected_totals:
        raise RuntimeError(f"The target endpoint totals changed: {totals} != {expected_totals}.")
    if expected_totals[0] != expected_totals[1] + expected_totals[2]:
        raise ValueError("Expected endpoint totals do not partition the target population.")

    default_row = primary.loc[primary["snapshot_resolution"].eq(RESOLVED_DEFAULT_REASON)]
    nondefault_row = primary.loc[primary["snapshot_resolution"].eq(RESOLVED_NONDEFAULT_REASON)]
    if len(default_row) != 1 or len(nondefault_row) != 1:
        raise RuntimeError("The active resolved binary endpoint reasons are not unique.")
    resolved_y1 = int(default_row["resolved_rows"].iloc[0])
    resolved_y0 = int(nondefault_row["resolved_rows"].iloc[0])
    if resolved_y1 != int(expected_resolved_y1):
        raise RuntimeError("The resolved-default endpoint census changed.")
    if resolved_y0 != int(expected_resolved_y0):
        raise RuntimeError("The resolved-nondefault endpoint census changed.")
    if resolved_y0 + resolved_y1 != expected_totals[1]:
        raise RuntimeError("The resolved binary endpoint classes do not exhaust resolved rows.")
    return primary, resolved_y0, resolved_y1


def marginal_mean_score_outcome_gap(
    scores: pd.DataFrame,
    endpoint_resolution: pd.DataFrame,
    *,
    learners: Sequence[str],
    score_columns: Mapping[str, str],
    role: str,
    expected_issue_months: Sequence[str],
    expected_reason_census: Mapping[str, Mapping[str, int]],
    expected_candidates: int,
    expected_resolved: int,
    expected_unresolved: int,
    expected_resolved_y0: int,
    expected_resolved_y1: int,
) -> MarginalMeanScoreOutcomeGapResult:
    """Return the complete sharp interval for every declared frozen learner."""
    candidates = _exact_nonnegative_integer(expected_candidates, label="Expected target candidates")
    resolved = _exact_nonnegative_integer(expected_resolved, label="Expected resolved rows")
    unresolved = _exact_nonnegative_integer(expected_unresolved, label="Expected unresolved rows")
    expected_y0 = _exact_nonnegative_integer(
        expected_resolved_y0, label="Expected resolved nondefaults"
    )
    expected_y1 = _exact_nonnegative_integer(
        expected_resolved_y1, label="Expected resolved defaults"
    )
    if candidates <= 0:
        raise ValueError("The target candidate census must be positive.")
    if candidates != resolved + unresolved or resolved != expected_y0 + expected_y1:
        raise ValueError("The declared target endpoint totals do not partition.")
    declared_learners = tuple(str(value) for value in learners)
    if len(declared_learners) != 5 or len(set(declared_learners)) != 5:
        raise ValueError("The estimand requires exactly five distinct declared learners.")
    if tuple(str(value) for value in score_columns) != declared_learners:
        raise ValueError("Score-column mapping order must equal the declared learner census.")
    declared_columns = tuple(str(score_columns[learner]) for learner in declared_learners)
    if len(set(declared_columns)) != len(declared_columns):
        raise ValueError("Declared learners must use distinct frozen score columns.")

    required_columns = ("id", "issue_d", "design_split", *declared_columns)
    if missing := set(required_columns).difference(scores.columns):
        raise ValueError(f"Frozen score table omits columns: {sorted(missing)}")
    primary = scores.loc[
        scores["design_split"].astype(str).eq(str(role)), list(required_columns)
    ].copy()
    if len(primary) != candidates:
        raise RuntimeError(f"Target score census changed: {len(primary)} != {candidates}.")
    candidate_id_sha256 = _hash_sorted_ids(primary["id"])

    issue_dates = pd.to_datetime(primary["issue_d"], errors="coerce")
    if issue_dates.isna().any():
        raise RuntimeError("The target score census contains an invalid issue date.")
    actual_issue_months = tuple(sorted(issue_dates.dt.to_period("M").astype(str).unique()))
    declared_issue_months = tuple(str(value) for value in expected_issue_months)
    if len(declared_issue_months) != len(set(declared_issue_months)):
        raise ValueError("Expected issue months must be distinct.")
    if actual_issue_months != declared_issue_months:
        raise RuntimeError(
            f"Target issue-month set changed: {actual_issue_months} != {declared_issue_months}."
        )

    endpoint, resolved_y0, resolved_y1 = _validated_primary_endpoint_census(
        endpoint_resolution,
        role=role,
        expected_reason_census=expected_reason_census,
        expected_candidates=candidates,
        expected_resolved=resolved,
        expected_unresolved=unresolved,
        expected_resolved_y0=expected_y0,
        expected_resolved_y1=expected_y1,
    )
    outcome_mean_lower = resolved_y1 / candidates
    outcome_mean_upper = (resolved_y1 + unresolved) / candidates
    identification_width = unresolved / candidates

    rows: list[dict[str, str | int | float | bool]] = []
    for learner_order, (learner, column) in enumerate(
        zip(declared_learners, declared_columns, strict=True), start=1
    ):
        if not pd.api.types.is_numeric_dtype(primary[column]):
            raise ValueError(f"Frozen score column {column!r} must be numeric.")
        values = primary[column].to_numpy(dtype=float, na_value=np.nan)
        if not bool(np.isfinite(values).all()):
            raise RuntimeError(f"Frozen score column {column!r} contains a nonfinite value.")
        if bool(np.any(values < 0.0) or np.any(values > 1.0)):
            raise RuntimeError(f"Frozen score column {column!r} leaves [0, 1].")
        score_sum = float(math.fsum(values.tolist()))
        mean_score = score_sum / candidates
        lower = mean_score - outcome_mean_upper
        upper = mean_score - outcome_mean_lower
        if not all(np.isfinite(value) for value in (score_sum, mean_score, lower, upper)):
            raise RuntimeError(f"The {learner!r} estimand contains a nonfinite value.")
        if lower > upper:
            raise RuntimeError(f"The {learner!r} identification interval is reversed.")
        if not 0.0 <= mean_score <= 1.0 or not -1.0 <= lower <= upper <= 1.0:
            raise RuntimeError(f"The {learner!r} estimand leaves its mathematical domain.")
        if not np.isclose(upper - lower, identification_width, atol=1.0e-15, rtol=0.0):
            raise RuntimeError(f"The {learner!r} identification width did not reconcile.")
        rows.append(
            {
                "estimand": ESTIMAND,
                "learner_order": learner_order,
                "learner": learner,
                "score_column": column,
                "candidate_rows": candidates,
                "resolved_rows": resolved,
                "resolved_nondefaults": resolved_y0,
                "resolved_defaults": resolved_y1,
                "unresolved_outcomes": unresolved,
                "candidate_id_sha256": candidate_id_sha256,
                "score_sum": score_sum,
                "mean_score": mean_score,
                "outcome_mean_lower": outcome_mean_lower,
                "outcome_mean_upper": outcome_mean_upper,
                "marginal_mean_score_outcome_gap_lower": lower,
                "marginal_mean_score_outcome_gap_upper": upper,
                "identification_width": identification_width,
                "sharp_binary_completion": True,
                "lower_endpoint_completion": "all_unresolved_outcomes_one",
                "upper_endpoint_completion": "all_unresolved_outcomes_zero",
            }
        )

    table = pd.DataFrame.from_records(rows)
    if len(table) != 5 or table["learner"].duplicated().any():
        raise RuntimeError("The complete five-learner reporting census was not produced.")
    reason_records: tuple[dict[str, str | int], ...] = tuple(
        {
            "snapshot_resolution": str(row.snapshot_resolution),
            "candidate_rows": int(row.candidate_rows),
            "resolved_rows": int(row.resolved_rows),
            "unresolved_rows": int(row.unresolved_rows),
        }
        for row in endpoint.sort_values("snapshot_resolution", kind="mergesort").itertuples(
            index=False
        )
    )
    return MarginalMeanScoreOutcomeGapResult(
        table=table.reset_index(drop=True),
        candidate_id_sha256=candidate_id_sha256,
        issue_months=actual_issue_months,
        endpoint_reason_census=reason_records,
    )
