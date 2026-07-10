"""Deterministic alignment of candidate loans and conformal interval rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

AlignmentMode = Literal["id", "row_number", "position"]


@dataclass(frozen=True)
class AlignedCandidateIntervals:
    """Candidate and interval frames that share the same sampled row order."""

    candidates: pd.DataFrame
    intervals: pd.DataFrame
    mode: AlignmentMode
    available_rows: int

    @property
    def selected_rows(self) -> int:
        return len(self.candidates)


def _normalized_limit(max_candidates: int | None) -> int | None:
    if max_candidates is None or int(max_candidates) <= 0:
        return None
    return int(max_candidates)


def _sample_positions(
    row_count: int,
    *,
    max_candidates: int | None,
    random_state: int,
) -> np.ndarray:
    if row_count <= 0:
        raise ValueError("Candidate/interval alignment produced zero rows.")
    limit = _normalized_limit(max_candidates)
    sample_size = row_count if limit is None else min(row_count, limit)
    if sample_size == row_count:
        return np.arange(row_count, dtype=int)
    positions = np.random.default_rng(random_state).choice(
        row_count,
        size=sample_size,
        replace=False,
    )
    return np.sort(positions.astype(int, copy=False))


def _require_unique_columns(frame: pd.DataFrame, *, source: str) -> None:
    duplicated = frame.columns[frame.columns.duplicated()].tolist()
    if duplicated:
        raise ValueError(f"{source} contains duplicate column names: {duplicated}")


def _validated_string_key(series: pd.Series, *, source: str) -> pd.Series:
    if series.isna().any():
        raise ValueError(f"{source} alignment key contains missing values.")
    keys = series.astype(str)
    if keys.str.strip().eq("").any():
        raise ValueError(f"{source} alignment key contains blank values.")
    duplicated = keys[keys.duplicated(keep=False)]
    if not duplicated.empty:
        examples = duplicated.drop_duplicates().head(3).tolist()
        raise ValueError(f"{source} alignment key is not unique; examples={examples}")
    return keys


def _validated_row_number_key(series: pd.Series) -> pd.Series:
    if series.isna().any():
        raise ValueError("interval _row_number contains missing values.")
    numeric = pd.to_numeric(series, errors="raise")
    values = numeric.to_numpy(dtype=float)
    if not np.isfinite(values).all() or not np.equal(values, np.floor(values)).all():
        raise ValueError("interval _row_number must contain finite integers.")
    keys = pd.Series(values.astype(np.int64), index=series.index)
    duplicated = keys[keys.duplicated(keep=False)]
    if not duplicated.empty:
        examples = duplicated.drop_duplicates().head(3).tolist()
        raise ValueError(f"interval _row_number is not unique; examples={examples}")
    return keys


def _unused_column_name(base: str, used: set[str]) -> str:
    name = base
    suffix = 1
    while name in used:
        name = f"{base}_{suffix}"
        suffix += 1
    used.add(name)
    return name


def _align_by_key(
    candidates: pd.DataFrame,
    intervals: pd.DataFrame,
    *,
    candidate_keys: pd.Series,
    interval_keys: pd.Series,
    mode: AlignmentMode,
    max_candidates: int | None,
    random_state: int,
    require_full_match: bool,
) -> AlignedCandidateIntervals:
    used_columns = set(candidates.columns) | set(intervals.columns)
    join_column = _unused_column_name("__crpto_alignment_key", used_columns)
    interval_aliases = {
        column: _unused_column_name(f"__crpto_interval_{index}", used_columns)
        for index, column in enumerate(intervals.columns)
    }

    candidate_work = candidates.copy()
    candidate_work[join_column] = candidate_keys.to_numpy()
    interval_work = intervals.rename(columns=interval_aliases).copy()
    interval_work[join_column] = interval_keys.to_numpy()
    merged = candidate_work.merge(
        interval_work,
        on=join_column,
        how="inner",
        sort=False,
        validate="one_to_one",
    )
    if require_full_match and (
        len(merged) != len(candidate_work) or len(merged) != len(interval_work)
    ):
        candidate_key_set = set(candidate_keys.tolist())
        interval_key_set = set(interval_keys.tolist())
        candidate_only = sorted(candidate_key_set - interval_key_set, key=str)[:3]
        interval_only = sorted(interval_key_set - candidate_key_set, key=str)[:3]
        raise ValueError(
            "Candidate/interval universes do not match exactly: "
            f"candidates={len(candidate_work)}, intervals={len(interval_work)}, "
            f"matched={len(merged)}, candidate_only_examples={candidate_only}, "
            f"interval_only_examples={interval_only}"
        )
    positions = _sample_positions(
        len(merged),
        max_candidates=max_candidates,
        random_state=random_state,
    )
    sampled = merged.iloc[positions].reset_index(drop=True)
    aligned_candidates = sampled.loc[:, list(candidates.columns)].copy()
    aligned_intervals = sampled.loc[:, list(interval_aliases.values())].rename(
        columns={alias: source for source, alias in interval_aliases.items()}
    )
    return AlignedCandidateIntervals(
        candidates=aligned_candidates,
        intervals=aligned_intervals,
        mode=mode,
        available_rows=len(merged),
    )


def align_candidate_intervals(
    candidates: pd.DataFrame,
    intervals: pd.DataFrame,
    *,
    max_candidates: int | None,
    random_state: int,
    allow_row_number: bool = True,
    require_full_match: bool = True,
) -> AlignedCandidateIntervals:
    """Align and sample candidate/interval rows under a strict one-to-one contract.

    Stable IDs take precedence. Legacy interval artifacts may instead provide a
    zero-based ``_row_number``. A positional fallback is retained for older
    artifacts, but samples from the full alignable universe rather than taking
    a deterministic prefix.
    """
    _require_unique_columns(candidates, source="candidates")
    _require_unique_columns(intervals, source="intervals")

    if "id" in candidates.columns and "id" in intervals.columns:
        return _align_by_key(
            candidates,
            intervals,
            candidate_keys=_validated_string_key(candidates["id"], source="candidate id"),
            interval_keys=_validated_string_key(intervals["id"], source="interval id"),
            mode="id",
            max_candidates=max_candidates,
            random_state=random_state,
            require_full_match=require_full_match,
        )

    if allow_row_number and "_row_number" in intervals.columns:
        return _align_by_key(
            candidates,
            intervals,
            candidate_keys=pd.Series(np.arange(len(candidates), dtype=np.int64)),
            interval_keys=_validated_row_number_key(intervals["_row_number"]),
            mode="row_number",
            max_candidates=max_candidates,
            random_state=random_state,
            require_full_match=require_full_match,
        )

    if require_full_match and len(candidates) != len(intervals):
        raise ValueError(
            "Positional candidate/interval universes do not match exactly: "
            f"candidates={len(candidates)}, intervals={len(intervals)}"
        )
    available_rows = min(len(candidates), len(intervals))
    positions = _sample_positions(
        available_rows,
        max_candidates=max_candidates,
        random_state=random_state,
    )
    return AlignedCandidateIntervals(
        candidates=candidates.iloc[positions].reset_index(drop=True).copy(),
        intervals=intervals.iloc[positions].reset_index(drop=True).copy(),
        mode="position",
        available_rows=available_rows,
    )
