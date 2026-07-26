"""Row-identified sharp bounds for the marginal mean-score--outcome gap."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, BinaryIO

import numpy as np
import pandas as pd

from src.data.outcome_observability import (
    build_outcome_label_availability,
    parse_issue_dates,
    parse_term_months,
)

ESTIMAND = "marginal_mean_score_outcome_gap"
ROLE = "primary_oot"
RESOLUTION_CHARGED_OFF = "charged_off_by_reconstructed_cutoff"
RESOLUTION_FULLY_PAID = "fully_paid_by_reconstructed_cutoff"
RESOLUTION_NONTERMINAL = "nonterminal_or_unresolved_status"
RESOLUTION_TERMINAL_AFTER = "terminal_after_reconstructed_cutoff"
RESOLUTION_TERMINAL_MISSING = "terminal_availability_date_missing"
ENDPOINT_REASONS = (
    RESOLUTION_CHARGED_OFF,
    RESOLUTION_FULLY_PAID,
    RESOLUTION_NONTERMINAL,
    RESOLUTION_TERMINAL_AFTER,
    RESOLUTION_TERMINAL_MISSING,
)


@dataclass(frozen=True)
class RawPrimaryOotScan:
    """Status-independent raw target rows plus scan counters."""

    frame: pd.DataFrame
    audit: dict[str, Any]


@dataclass(frozen=True)
class MarginalMeanScoreOutcomeGapV3BResult:
    """Five-learner bounds and row-level population reconciliation evidence."""

    table: pd.DataFrame
    endpoint_reason_census: pd.DataFrame
    monthly_endpoint_reason_census: pd.DataFrame
    join_audit: dict[str, Any]
    issue_months: tuple[str, ...]
    endpoint_row_sha256: str


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


def _require_columns(frame: pd.DataFrame, columns: Sequence[str], *, label: str) -> None:
    missing = sorted(set(columns).difference(frame.columns))
    if missing:
        raise ValueError(f"{label} omits columns: {missing}.")


def normalized_unique_ids(values: pd.Series, *, label: str) -> pd.Series:
    """Return stripped string IDs after rejecting missing, blank, or duplicate values."""
    identifiers = values.astype("string")
    if bool(identifiers.isna().any()):
        raise RuntimeError(f"{label} contains missing identifiers.")
    identifiers = identifiers.str.strip()
    if bool(identifiers.eq("").any()):
        raise RuntimeError(f"{label} contains blank identifiers.")
    duplicate = identifiers.duplicated(keep=False)
    if bool(duplicate.any()):
        examples = identifiers.loc[duplicate].drop_duplicates().head(5).tolist()
        raise RuntimeError(f"{label} contains duplicate identifiers: {examples}.")
    return identifiers


def hash_sorted_identifiers(values: pd.Series, *, label: str) -> str:
    """Hash a unique identifier set with an unambiguous length-prefixed encoding."""
    identifiers = normalized_unique_ids(values, label=label)
    digest = sha256()
    for identifier in sorted(identifiers.astype(str).tolist()):
        encoded = identifier.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, byteorder="little", signed=False))
        digest.update(encoded)
    return digest.hexdigest()


def hash_endpoint_assignments(frame: pd.DataFrame) -> str:
    """Hash the canonical ID/role/month/reason/nullable-outcome record stream."""
    columns = ("id", "role", "period", "snapshot_resolution", "snapshot_default")
    _require_columns(frame, columns, label="Endpoint assignment table")
    endpoint = frame.loc[:, list(columns)].copy()
    endpoint["id"] = normalized_unique_ids(endpoint["id"], label="Endpoint assignment table")
    digest = sha256()
    for row in endpoint.sort_values("id", kind="mergesort").itertuples(index=False):
        outcome = None if pd.isna(row.snapshot_default) else int(row.snapshot_default)
        record = [
            str(row.id),
            str(row.role),
            str(row.period),
            str(row.snapshot_resolution),
            outcome,
        ]
        payload = json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        digest.update(len(payload).to_bytes(8, byteorder="little", signed=False))
        digest.update(payload)
    return digest.hexdigest()


def hash_canonical_records(
    frame: pd.DataFrame,
    *,
    columns: Sequence[str],
    sort_columns: Sequence[str],
) -> str:
    """Hash a deterministic table projection without delimiter ambiguity."""
    _require_columns(frame, (*columns, *sort_columns), label="Canonical record table")
    ordered = frame.sort_values(list(sort_columns), kind="mergesort").reset_index(drop=True)
    digest = sha256()
    for column in columns:
        encoded = str(column).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, byteorder="little", signed=False))
        digest.update(encoded)
    for row in ordered.loc[:, list(columns)].itertuples(index=False, name=None):
        for value in row:
            rendered = "<NA>" if pd.isna(value) else str(value)
            encoded = rendered.encode("utf-8")
            digest.update(len(encoded).to_bytes(8, byteorder="little", signed=False))
            digest.update(encoded)
    return digest.hexdigest()


def _rewind(source: Path | BinaryIO) -> None:
    if hasattr(source, "seek"):
        source.seek(0)


def scan_primary_oot_raw_archive(
    source: Path | BinaryIO,
    *,
    required_columns: Sequence[str],
    csv_chunksize: int,
    term_months: int,
    start_month: str,
    end_month: str,
    expected_raw_rows: int,
    expected_candidates: int,
    expected_issue_months: Sequence[str],
    expected_candidate_ids: pd.Series | None = None,
) -> RawPrimaryOotScan:
    """Scan the raw archive and select the target from term and issue month only."""
    required = tuple(str(value) for value in required_columns)
    if required != ("id", "issue_d", "term", "loan_status", "last_pymnt_d"):
        raise ValueError("The V3B raw column allowlist changed.")
    chunk_size = _exact_nonnegative_integer(csv_chunksize, label="CSV chunksize")
    if chunk_size <= 0:
        raise ValueError("CSV chunksize must be positive.")
    term = _exact_nonnegative_integer(term_months, label="Term months")
    start = pd.Period(str(start_month), freq="M")
    end = pd.Period(str(end_month), freq="M")
    if start > end:
        raise ValueError("The raw target month interval is reversed.")

    _rewind(source)
    header = pd.read_csv(source, nrows=0)
    missing = sorted(set(required).difference(map(str, header.columns)))
    if missing:
        raise KeyError(f"Raw archive omits V3B columns: {missing}.")
    _rewind(source)

    raw_rows = 0
    selected: list[pd.DataFrame] = []
    lookup: list[pd.DataFrame] = []
    lookup_ids: set[str] | None = None
    if expected_candidate_ids is not None:
        normalized_lookup_ids = normalized_unique_ids(
            expected_candidate_ids, label="Frozen score lookup census"
        )
        lookup_ids = set(normalized_lookup_ids.astype(str))
    dtype = dict.fromkeys(required, "string")
    reader = pd.read_csv(
        source,
        usecols=list(required),
        dtype=dtype,
        chunksize=chunk_size,
        low_memory=False,
    )
    for chunk in reader:
        raw_rows += int(len(chunk))
        normalized_chunk_ids = chunk["id"].astype("string").str.strip()
        issue_dates = parse_issue_dates(chunk["issue_d"])
        periods = issue_dates.dt.to_period("M")
        terms = parse_term_months(chunk["term"])
        if lookup_ids is not None:
            in_lookup = normalized_chunk_ids.isin(lookup_ids).fillna(False)
            if bool(in_lookup.any()):
                raw_lookup = chunk.loc[in_lookup, ["id", "issue_d", "term"]].copy()
                raw_lookup["id"] = normalized_chunk_ids.loc[in_lookup]
                raw_lookup["period"] = periods.loc[in_lookup].astype(str)
                raw_lookup["term_months"] = terms.loc[in_lookup]
                lookup.append(raw_lookup)
        keep = terms.eq(term).fillna(False) & periods.ge(start) & periods.le(end)
        if not bool(keep.any()):
            continue
        retained = chunk.loc[keep, list(required)].copy()
        retained["period"] = periods.loc[keep].astype(str)
        retained["role"] = ROLE
        selected.append(retained)

    expected_raw = _exact_nonnegative_integer(expected_raw_rows, label="Expected raw rows")
    if raw_rows != expected_raw:
        raise RuntimeError(f"Raw archive row census changed: {raw_rows} != {expected_raw}.")
    if not selected:
        raise RuntimeError("The raw scan produced no primary OOT candidates.")
    frame = pd.concat(selected, ignore_index=True)
    expected_n = _exact_nonnegative_integer(
        expected_candidates, label="Expected primary OOT candidates"
    )
    if len(frame) != expected_n:
        raise RuntimeError(f"Raw primary OOT census changed: {len(frame)} != {expected_n}.")
    frame["id"] = normalized_unique_ids(frame["id"], label="Raw primary OOT census")
    canonical_issue = (
        frame["issue_d"].astype("string").str.strip().str.fullmatch(r"[A-Za-z]{3}-\d{4}", na=False)
    )
    if not bool(canonical_issue.all()):
        raise RuntimeError("Raw primary OOT issue dates left the canonical Mon-YYYY format.")
    declared_months = tuple(str(value) for value in expected_issue_months)
    actual_months = tuple(sorted(frame["period"].astype(str).unique()))
    if actual_months != declared_months:
        raise RuntimeError(f"Raw primary OOT months changed: {actual_months} != {declared_months}.")
    lookup_audit: dict[str, Any] = {
        "performed": lookup_ids is not None,
        "rows": None,
        "candidate_id_sha256": None,
        "equals_raw_primary_ids": None,
        "period_mismatch_rows": None,
        "non_36_month_rows": None,
    }
    if lookup_ids is not None:
        if not lookup:
            raise RuntimeError("Raw archive lookup found none of the frozen score IDs.")
        lookup_frame = pd.concat(lookup, ignore_index=True)
        lookup_frame["id"] = normalized_unique_ids(
            lookup_frame["id"], label="Raw score-ID lookup census"
        )
        if len(lookup_frame) != expected_n or set(lookup_frame["id"].astype(str)) != lookup_ids:
            raise RuntimeError("Raw score-ID lookup is not identical to the frozen score census.")
        lookup_hash = hash_sorted_identifiers(
            lookup_frame["id"], label="Raw score-ID lookup census"
        )
        primary_lookup = frame.loc[:, ["id", "period"]].merge(
            lookup_frame.loc[:, ["id", "period", "term_months"]],
            on="id",
            how="outer",
            validate="one_to_one",
            indicator=True,
            suffixes=("_primary", "_lookup"),
        )
        if not bool(primary_lookup["_merge"].eq("both").all()):
            raise RuntimeError("Raw target and raw score-ID lookup censuses differ.")
        period_mismatch = int(
            primary_lookup["period_primary"]
            .astype(str)
            .ne(primary_lookup["period_lookup"].astype(str))
            .sum()
        )
        non_36 = int(primary_lookup["term_months"].ne(term).fillna(True).sum())
        if period_mismatch or non_36:
            raise RuntimeError(
                "Raw score-ID lookup disagrees with target membership: "
                f"period_mismatch={period_mismatch}, non_36_month={non_36}."
            )
        lookup_audit = {
            "performed": True,
            "rows": int(len(lookup_frame)),
            "candidate_id_sha256": lookup_hash,
            "equals_raw_primary_ids": True,
            "period_mismatch_rows": 0,
            "non_36_month_rows": 0,
        }
    frame = frame.sort_values(["period", "id"], kind="mergesort").reset_index(drop=True)
    return RawPrimaryOotScan(
        frame=frame,
        audit={
            "raw_rows_seen": raw_rows,
            "selection_columns": ["term", "issue_d"],
            "membership_uses_loan_status": False,
            "candidate_rows": int(len(frame)),
            "candidate_id_sha256": hash_sorted_identifiers(
                frame["id"], label="Raw primary OOT census"
            ),
            "issue_months": list(actual_months),
            "raw_score_id_lookup": lookup_audit,
        },
    )


def build_row_level_endpoint(
    raw_primary: pd.DataFrame,
    *,
    cutoff: str,
    charged_off_lag_months: int,
) -> pd.DataFrame:
    """Reconstruct the five-reason nullable endpoint on every raw target row."""
    required = ("id", "period", "role", "loan_status", "last_pymnt_d")
    _require_columns(raw_primary, required, label="Raw primary OOT endpoint source")
    identifiers = normalized_unique_ids(raw_primary["id"], label="Raw endpoint source")
    roles = raw_primary["role"].astype("string")
    if bool(roles.isna().any()) or not bool(roles.eq(ROLE).all()):
        raise RuntimeError("Raw endpoint source contains a non-primary role.")
    periods = raw_primary["period"].astype("string")
    if bool(periods.isna().any()):
        raise RuntimeError("Raw endpoint source contains a missing issue month.")
    last_payment = raw_primary["last_pymnt_d"].astype("string").str.strip()
    nonmissing_payment = last_payment.notna()
    canonical_payment = last_payment.str.fullmatch(r"[A-Za-z]{3}-\d{4}", na=False)
    if bool((nonmissing_payment & ~canonical_payment).any()):
        raise RuntimeError("Raw target last-payment dates left the canonical Mon-YYYY format.")

    labels = build_outcome_label_availability(
        raw_primary["loan_status"],
        raw_primary["last_pymnt_d"],
        cutoff=cutoff,
        charged_off_lag_months=int(charged_off_lag_months),
    )
    terminal = labels["terminal_outcome"].astype("Int8")
    available_at = pd.to_datetime(labels["label_available_at"], errors="coerce")
    available = labels["label_available"].astype(bool)
    snapshot_default = terminal.where(available).astype("Int8")

    cutoff_timestamp = pd.Timestamp(str(cutoff))
    terminal_missing = terminal.notna() & available_at.isna()
    terminal_after = terminal.notna() & available_at.notna() & available_at.gt(cutoff_timestamp)
    masks = {
        RESOLUTION_FULLY_PAID: snapshot_default.eq(0).fillna(False),
        RESOLUTION_CHARGED_OFF: snapshot_default.eq(1).fillna(False),
        RESOLUTION_TERMINAL_MISSING: terminal_missing,
        RESOLUTION_TERMINAL_AFTER: terminal_after,
        RESOLUTION_NONTERMINAL: terminal.isna(),
    }
    mask_sum = np.zeros(len(raw_primary), dtype=np.int8)
    for mask in masks.values():
        mask_sum += mask.to_numpy(dtype=np.int8)
    if not bool(np.equal(mask_sum, 1).all()):
        raise RuntimeError("The row-level endpoint reasons are not unique and exhaustive.")
    resolution = pd.Series(pd.NA, index=raw_primary.index, dtype="string")
    for reason, mask in masks.items():
        resolution.loc[mask] = reason
    if bool(resolution.isna().any()):
        raise RuntimeError("The row-level endpoint taxonomy left unclassified candidates.")

    endpoint = pd.DataFrame(
        {
            "id": identifiers,
            "role": roles,
            "period": periods,
            "snapshot_default": snapshot_default,
            "snapshot_resolution": resolution,
            "outcome_available_at": available_at,
        }
    )
    return endpoint.sort_values(["period", "id"], kind="mergesort").reset_index(drop=True)


def endpoint_reason_census(endpoint: pd.DataFrame) -> pd.DataFrame:
    """Return the exhaustive five-row target endpoint partition."""
    required = ("id", "role", "snapshot_default", "snapshot_resolution")
    _require_columns(endpoint, required, label="Row-level endpoint")
    normalized_unique_ids(endpoint["id"], label="Row-level endpoint")
    resolved = endpoint["snapshot_default"].notna()
    table = (
        endpoint.assign(__resolved=resolved)
        .groupby(["role", "snapshot_resolution"], observed=True, sort=True)
        .agg(candidate_rows=("id", "size"), resolved_rows=("__resolved", "sum"))
        .reset_index()
    )
    table["candidate_rows"] = table["candidate_rows"].astype("int64")
    table["resolved_rows"] = table["resolved_rows"].astype("int64")
    table["unresolved_rows"] = table["candidate_rows"] - table["resolved_rows"]
    if set(table["snapshot_resolution"].astype(str)) != set(ENDPOINT_REASONS):
        raise RuntimeError("The row-level endpoint does not contain the complete reason census.")
    if int(table["candidate_rows"].sum()) != len(endpoint):
        raise RuntimeError("Endpoint reasons do not partition the row-level candidate census.")
    return table.sort_values(["role", "snapshot_resolution"], kind="mergesort").reset_index(
        drop=True
    )


def monthly_endpoint_reason_census(endpoint: pd.DataFrame) -> pd.DataFrame:
    """Return a month-by-reason partition used to detect aggregate cancellation."""
    required = ("id", "role", "period", "snapshot_default", "snapshot_resolution")
    _require_columns(endpoint, required, label="Row-level endpoint")
    resolved = endpoint["snapshot_default"].notna()
    table = (
        endpoint.assign(__resolved=resolved)
        .groupby(["role", "period", "snapshot_resolution"], observed=True, sort=True)
        .agg(candidate_rows=("id", "size"), resolved_rows=("__resolved", "sum"))
        .reset_index()
    )
    table["candidate_rows"] = table["candidate_rows"].astype("int64")
    table["resolved_rows"] = table["resolved_rows"].astype("int64")
    table["unresolved_rows"] = table["candidate_rows"] - table["resolved_rows"]
    periods = tuple(sorted(endpoint["period"].astype(str).unique()))
    complete_index = pd.MultiIndex.from_product(
        [[ROLE], periods, ENDPOINT_REASONS],
        names=["role", "period", "snapshot_resolution"],
    )
    table = (
        table.set_index(["role", "period", "snapshot_resolution"])
        .reindex(complete_index, fill_value=0)
        .reset_index()
    )
    for column in ("candidate_rows", "resolved_rows", "unresolved_rows"):
        table[column] = table[column].astype("int64")
    if int(table["candidate_rows"].sum()) != len(endpoint):
        raise RuntimeError("Monthly endpoint reasons do not partition the target census.")
    return table.sort_values(
        ["role", "period", "snapshot_resolution"], kind="mergesort"
    ).reset_index(drop=True)


def _validate_reason_contract(
    census: pd.DataFrame,
    *,
    expected_reason_census: Mapping[str, Mapping[str, int]],
) -> None:
    if tuple(str(value) for value in expected_reason_census) != ENDPOINT_REASONS:
        raise ValueError("The expected endpoint reason order changed.")
    actual = census.set_index("snapshot_resolution")
    for reason in ENDPOINT_REASONS:
        if reason not in actual.index:
            raise RuntimeError(f"Endpoint census omits reason {reason!r}.")
        expected = expected_reason_census[reason]
        for column in ("candidate_rows", "resolved_rows", "unresolved_rows"):
            wanted = _exact_nonnegative_integer(
                expected.get(column), label=f"Expected {reason}/{column}"
            )
            observed = int(actual.loc[reason, column])
            if observed != wanted:
                raise RuntimeError(
                    f"Endpoint reason {reason!r} changed on {column}: {observed} != {wanted}."
                )


def marginal_mean_score_outcome_gap_v3b(
    scores: pd.DataFrame,
    endpoint: pd.DataFrame,
    *,
    learners: Sequence[str],
    score_columns: Mapping[str, str],
    role: str,
    expected_issue_months: Sequence[str],
    expected_candidate_id_sha256: str,
    expected_endpoint_row_sha256: str,
    expected_reason_census: Mapping[str, Mapping[str, int]],
    expected_monthly_reason_candidate_rows: Mapping[str, Mapping[str, int]],
    expected_candidates: int,
    expected_resolved: int,
    expected_unresolved: int,
    expected_resolved_y0: int,
    expected_resolved_y1: int,
) -> MarginalMeanScoreOutcomeGapV3BResult:
    """Join frozen scores to raw-derived outcomes and compute all sharp intervals."""
    if str(role) != ROLE:
        raise ValueError("V3B is defined only for the complete primary OOT census.")
    candidates = _exact_nonnegative_integer(expected_candidates, label="Expected candidates")
    resolved = _exact_nonnegative_integer(expected_resolved, label="Expected resolved")
    unresolved = _exact_nonnegative_integer(expected_unresolved, label="Expected unresolved")
    resolved_y0 = _exact_nonnegative_integer(
        expected_resolved_y0, label="Expected resolved nondefaults"
    )
    resolved_y1 = _exact_nonnegative_integer(
        expected_resolved_y1, label="Expected resolved defaults"
    )
    if (
        candidates <= 0
        or candidates != resolved + unresolved
        or resolved != resolved_y0 + resolved_y1
    ):
        raise ValueError("The declared endpoint totals do not partition the target population.")

    declared_learners = tuple(str(value) for value in learners)
    if len(declared_learners) != 5 or len(set(declared_learners)) != 5:
        raise ValueError("V3B requires exactly five distinct declared learners.")
    if tuple(str(value) for value in score_columns) != declared_learners:
        raise ValueError("Score-column order must equal the learner census.")
    declared_columns = tuple(str(score_columns[learner]) for learner in declared_learners)
    if len(set(declared_columns)) != 5:
        raise ValueError("Each learner must use a distinct frozen score column.")

    required_scores = ("id", "issue_d", "design_split", *declared_columns)
    _require_columns(scores, required_scores, label="Frozen score table")
    primary = scores.loc[scores["design_split"].astype(str).eq(ROLE), list(required_scores)].copy()
    if len(primary) != candidates:
        raise RuntimeError(f"Frozen score census changed: {len(primary)} != {candidates}.")
    primary["id"] = normalized_unique_ids(primary["id"], label="Frozen score census")
    score_dates = pd.to_datetime(primary["issue_d"], errors="coerce")
    if bool(score_dates.isna().any()):
        raise RuntimeError("Frozen score census contains an invalid issue date.")
    primary["score_period"] = score_dates.dt.to_period("M").astype(str)
    declared_months = tuple(str(value) for value in expected_issue_months)
    score_months = tuple(sorted(primary["score_period"].unique()))
    if score_months != declared_months:
        raise RuntimeError(f"Frozen score months changed: {score_months} != {declared_months}.")
    score_hash = hash_sorted_identifiers(primary["id"], label="Frozen score census")

    endpoint_required = (
        "id",
        "role",
        "period",
        "snapshot_default",
        "snapshot_resolution",
    )
    _require_columns(endpoint, endpoint_required, label="Raw-derived endpoint")
    outcomes = endpoint.loc[:, list(endpoint_required)].copy()
    if len(outcomes) != candidates:
        raise RuntimeError(f"Raw endpoint census changed: {len(outcomes)} != {candidates}.")
    outcomes["id"] = normalized_unique_ids(outcomes["id"], label="Raw endpoint census")
    outcome_hash = hash_sorted_identifiers(outcomes["id"], label="Raw endpoint census")
    expected_hash = str(expected_candidate_id_sha256)
    if len(expected_hash) != 64 or any(value not in "0123456789abcdef" for value in expected_hash):
        raise ValueError("Expected candidate ID SHA-256 is malformed.")
    if score_hash != expected_hash or outcome_hash != expected_hash:
        raise RuntimeError("Score and raw endpoint ID hashes do not equal the locked target hash.")

    score_payload = primary.loc[:, ["id", "score_period", *declared_columns]]
    outcome_payload = outcomes.rename(columns={"role": "outcome_role", "period": "outcome_period"})
    joined = score_payload.merge(
        outcome_payload,
        on="id",
        how="outer",
        validate="one_to_one",
        indicator="__join",
        sort=False,
    )
    left_only = int(joined["__join"].eq("left_only").sum())
    right_only = int(joined["__join"].eq("right_only").sum())
    both = int(joined["__join"].eq("both").sum())
    if left_only or right_only or both != candidates or len(joined) != candidates:
        raise RuntimeError(
            "Score-to-outcome candidate join is not bijective: "
            f"both={both}, score_only={left_only}, outcome_only={right_only}."
        )
    if not bool(joined["outcome_role"].astype(str).eq(ROLE).all()):
        raise RuntimeError("A joined raw outcome has the wrong design role.")
    period_match = joined["score_period"].astype(str).eq(joined["outcome_period"].astype(str))
    if not bool(period_match.all()):
        examples = joined.loc[~period_match, "id"].astype(str).head(5).tolist()
        raise RuntimeError(f"Score and raw issue months disagree for IDs: {examples}.")
    joined_hash = hash_sorted_identifiers(joined["id"], label="Joined target census")
    if joined_hash != expected_hash:
        raise RuntimeError("The joined candidate hash changed.")
    joined = joined.sort_values("id", kind="mergesort").reset_index(drop=True)

    labels = pd.to_numeric(joined["snapshot_default"], errors="coerce").astype("Int8")
    invalid_label = labels.notna() & ~labels.isin([0, 1])
    if bool(invalid_label.any()):
        raise RuntimeError("Raw-derived endpoint contains a nonbinary resolved label.")
    reasons = joined["snapshot_resolution"].astype("string")
    if bool(reasons.isna().any()) or set(reasons.astype(str)) != set(ENDPOINT_REASONS):
        raise RuntimeError("Raw-derived endpoint reason support changed.")
    consistency = (
        (reasons.eq(RESOLUTION_FULLY_PAID) & labels.eq(0).fillna(False))
        | (reasons.eq(RESOLUTION_CHARGED_OFF) & labels.eq(1).fillna(False))
        | (reasons.isin(ENDPOINT_REASONS[2:]) & labels.isna())
    )
    if not bool(consistency.all()):
        raise RuntimeError("A row-level outcome disagrees with its endpoint reason.")

    census_source = pd.DataFrame(
        {
            "id": joined["id"],
            "role": joined["outcome_role"],
            "period": joined["outcome_period"],
            "snapshot_default": labels,
            "snapshot_resolution": reasons,
        }
    )
    reason_census = endpoint_reason_census(census_source)
    _validate_reason_contract(reason_census, expected_reason_census=expected_reason_census)
    monthly_census = monthly_endpoint_reason_census(census_source)
    if tuple(str(value) for value in expected_monthly_reason_candidate_rows) != declared_months:
        raise ValueError("The expected monthly endpoint period order changed.")
    monthly_index = monthly_census.set_index(["period", "snapshot_resolution"])
    for period in declared_months:
        expected_month = expected_monthly_reason_candidate_rows[period]
        if tuple(str(value) for value in expected_month) != ENDPOINT_REASONS:
            raise ValueError(f"The expected endpoint reason order changed for {period}.")
        for reason in ENDPOINT_REASONS:
            observed = int(monthly_index.loc[(period, reason), "candidate_rows"])
            expected = _exact_nonnegative_integer(
                expected_month[reason], label=f"Expected {period}/{reason} rows"
            )
            if observed != expected:
                raise RuntimeError(
                    f"Monthly endpoint census changed for {period}/{reason}: "
                    f"{observed} != {expected}."
                )
    observed_resolved = int(labels.notna().sum())
    observed_y0 = int(labels.eq(0).fillna(False).sum())
    observed_y1 = int(labels.eq(1).fillna(False).sum())
    observed_unresolved = int(labels.isna().sum())
    if (observed_resolved, observed_unresolved, observed_y0, observed_y1) != (
        resolved,
        unresolved,
        resolved_y0,
        resolved_y1,
    ):
        raise RuntimeError("The row-level endpoint totals changed.")

    endpoint_row_hash = hash_endpoint_assignments(census_source)
    if endpoint_row_hash != str(expected_endpoint_row_sha256):
        raise RuntimeError(
            "The raw-derived endpoint assignment hash changed: "
            f"{endpoint_row_hash} != {expected_endpoint_row_sha256}."
        )

    outcome_mean_lower = resolved_y1 / candidates
    outcome_mean_upper = (resolved_y1 + unresolved) / candidates
    identification_width = unresolved / candidates
    rows: list[dict[str, str | int | float | bool]] = []
    for learner_order, (learner, column) in enumerate(
        zip(declared_learners, declared_columns, strict=True), start=1
    ):
        if not pd.api.types.is_numeric_dtype(joined[column]):
            raise ValueError(f"Frozen score column {column!r} must be numeric.")
        values = joined[column].to_numpy(dtype=float, na_value=np.nan)
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
        if lower > upper or not -1.0 <= lower <= upper <= 1.0:
            raise RuntimeError(f"The {learner!r} identification interval is invalid.")
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
                "score_candidate_id_sha256": score_hash,
                "outcome_candidate_id_sha256": outcome_hash,
                "joined_candidate_id_sha256": joined_hash,
                "endpoint_row_sha256": endpoint_row_hash,
                "score_sum": score_sum,
                "mean_score": mean_score,
                "outcome_mean_lower": outcome_mean_lower,
                "outcome_mean_upper": outcome_mean_upper,
                "marginal_mean_score_outcome_gap_lower": lower,
                "marginal_mean_score_outcome_gap_upper": upper,
                "identification_width": identification_width,
                "identified_grid_points": unresolved + 1,
                "identified_grid_step": 1.0 / candidates,
                "reported_interval_is_identified_set_hull": True,
                "sharp_binary_completion": True,
                "joint_endpoint_attainment": True,
                "lower_endpoint_completion": "all_unresolved_outcomes_one",
                "upper_endpoint_completion": "all_unresolved_outcomes_zero",
            }
        )
    table = pd.DataFrame.from_records(rows)
    if len(table) != 5 or table["learner"].duplicated().any():
        raise RuntimeError("The complete five-learner reporting census was not produced.")

    return MarginalMeanScoreOutcomeGapV3BResult(
        table=table.reset_index(drop=True),
        endpoint_reason_census=reason_census,
        monthly_endpoint_reason_census=monthly_census,
        join_audit={
            "score_rows": int(len(primary)),
            "outcome_rows": int(len(outcomes)),
            "joined_rows": int(len(joined)),
            "both_rows": both,
            "score_only_rows": left_only,
            "outcome_only_rows": right_only,
            "period_mismatch_rows": 0,
            "score_candidate_id_sha256": score_hash,
            "outcome_candidate_id_sha256": outcome_hash,
            "joined_candidate_id_sha256": joined_hash,
            "all_three_id_hashes_equal_locked_hash": True,
            "one_to_one_outer_join": True,
        },
        issue_months=score_months,
        endpoint_row_sha256=endpoint_row_hash,
    )
