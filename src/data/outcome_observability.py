"""Status-independent loan universes and maturity-aware temporal blocks."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

LABEL_REQUIRED_SPLITS = frozenset(
    {
        "pd_development",
        "probability_calibration",
        "conformal_fit",
        "policy_development",
    }
)
DECISION_SPLITS = frozenset({"policy_development", "primary_oot", "censored_extension"})


def normalize_loan_status(statuses: pd.Series) -> pd.Series:
    """Normalize Lending Club snapshot statuses without changing membership."""
    return (
        statuses.astype("string")
        .fillna("")
        .str.strip()
        .str.casefold()
        .str.replace(r"\s+", " ", regex=True)
    )


def snapshot_default_from_status(statuses: pd.Series) -> pd.Series:
    """Map resolved snapshot statuses to a nullable binary default outcome."""
    normalized = normalize_loan_status(statuses)
    positive = normalized.str.contains("charged off", regex=False) | normalized.eq("default")
    negative = normalized.str.contains("fully paid", regex=False)
    if bool((positive & negative).any()):
        raise ValueError("A loan status cannot be both default and fully paid.")
    target = pd.Series(pd.NA, index=statuses.index, dtype="Int8", name="snapshot_default")
    target.loc[negative] = 0
    target.loc[positive] = 1
    return target


def snapshot_resolution_from_status(statuses: pd.Series) -> pd.Series:
    """Classify snapshot statuses as default, nondefault, or unresolved."""
    target = snapshot_default_from_status(statuses)
    resolution = pd.Series("unresolved", index=statuses.index, dtype="string")
    resolution.loc[target.eq(0).fillna(False)] = "nondefault"
    resolution.loc[target.eq(1).fillna(False)] = "default"
    return resolution.rename("snapshot_resolution")


def terminal_outcome_from_status(statuses: pd.Series) -> pd.Series:
    """Map terminal repayment statuses to the pre-freeze nullable outcome.

    Charged-off status variants are defaults and fully-paid variants are
    nondefaults. ``Default`` remains unresolved because the snapshot status
    alone does not establish the protocol's terminal charged-off label.
    """
    normalized = normalize_loan_status(statuses)
    charged_off = normalized.str.contains("charged off", regex=False)
    fully_paid = normalized.str.contains("fully paid", regex=False)
    if bool((charged_off & fully_paid).any()):
        raise ValueError("A loan status cannot be both charged off and fully paid.")
    target = pd.Series(pd.NA, index=statuses.index, dtype="Int8", name="terminal_outcome")
    target.loc[fully_paid] = 0
    target.loc[charged_off] = 1
    return target


def parse_last_payment_dates(values: pd.Series) -> pd.Series:
    """Parse ``last_pymnt_d``, using month-end for month-granularity values."""
    strings = values.astype("string").str.strip()
    month_year = strings.str.fullmatch(r"[A-Za-z]{3}-\d{4}", na=False)
    parsed = pd.to_datetime(strings, format="%b-%Y", errors="coerce")
    fallback = parsed.isna() & strings.notna()
    parsed.loc[fallback] = pd.to_datetime(strings.loc[fallback], format="mixed", errors="coerce")
    parsed.loc[month_year & parsed.notna()] = parsed.loc[
        month_year & parsed.notna()
    ] + pd.offsets.MonthEnd(0)
    return parsed.rename("last_pymnt_d_parsed")


def conservative_label_available_mask(
    statuses: pd.Series,
    last_payment_dates: pd.Series,
    *,
    cutoff: str | pd.Timestamp,
    charged_off_lag_months: int = 6,
) -> pd.Series:
    """Return labels conservatively observable by an explicit cutoff."""
    if not statuses.index.equals(last_payment_dates.index):
        raise ValueError("Status and last-payment series must have identical indices.")
    lag_months = int(charged_off_lag_months)
    if lag_months < 0:
        raise ValueError("charged_off_lag_months must be nonnegative.")
    cutoff_date = _require_timestamp(cutoff, context="label-availability cutoff")
    outcomes = terminal_outcome_from_status(statuses)
    payment_dates = parse_last_payment_dates(last_payment_dates)
    available_at = payment_dates.copy()
    charged_off = outcomes.eq(1).fillna(False)
    available_at.loc[charged_off] = payment_dates.loc[charged_off] + pd.DateOffset(
        months=lag_months
    )
    available = outcomes.notna() & available_at.notna() & available_at.le(cutoff_date)
    return available.astype(bool).rename("label_available")


def build_outcome_label_availability(
    statuses: pd.Series,
    last_payment_dates: pd.Series,
    *,
    cutoff: str | pd.Timestamp,
    charged_off_lag_months: int = 6,
) -> pd.DataFrame:
    """Build row-level terminal outcomes and conservative availability dates."""
    outcomes = terminal_outcome_from_status(statuses)
    payment_dates = parse_last_payment_dates(last_payment_dates)
    available_at = payment_dates.copy().rename("label_available_at")
    charged_off = outcomes.eq(1).fillna(False)
    available_at.loc[charged_off] = payment_dates.loc[charged_off] + pd.DateOffset(
        months=int(charged_off_lag_months)
    )
    available = conservative_label_available_mask(
        statuses,
        last_payment_dates,
        cutoff=cutoff,
        charged_off_lag_months=charged_off_lag_months,
    )
    return pd.concat([outcomes, payment_dates, available_at, available], axis=1)


def audit_outcome_label_availability(
    frame: pd.DataFrame,
    *,
    cutoff: str | pd.Timestamp,
    charged_off_lag_months: int = 6,
    block_column: str = "design_split",
    status_column: str = "loan_status",
    last_payment_column: str = "last_pymnt_d",
) -> pd.DataFrame:
    """Report conservative outcome-label counts and retention by design block."""
    required = {block_column, status_column, last_payment_column}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise KeyError(f"Outcome-label audit is missing columns: {missing}")
    labels = build_outcome_label_availability(
        frame[status_column],
        frame[last_payment_column],
        cutoff=cutoff,
        charged_off_lag_months=charged_off_lag_months,
    )
    audited = pd.DataFrame(
        {
            block_column: frame[block_column],
            "terminal_outcome": labels["terminal_outcome"],
            "label_available": labels["label_available"],
        },
        index=frame.index,
    )
    rows: list[dict[str, Any]] = []
    for block, group in audited.groupby(block_column, dropna=False, sort=True):
        total = int(len(group))
        resolved = int(group["terminal_outcome"].notna().sum())
        retained = int(group["label_available"].sum())
        rows.append(
            {
                block_column: block,
                "total_rows": total,
                "terminal_outcome_rows": resolved,
                "unresolved_outcome_rows": total - resolved,
                "label_available_rows": retained,
                "label_unavailable_rows": total - retained,
                "retention_rate": retained / total if total else 0.0,
            }
        )
    return pd.DataFrame(rows)


def validate_minimum_label_retention(
    audit: pd.DataFrame,
    *,
    minimum_retention: float,
    block_column: str = "design_split",
) -> None:
    """Require every audited block to exceed the declared retention floor."""
    threshold = float(minimum_retention)
    if not 0.0 <= threshold < 1.0:
        raise ValueError("minimum_retention must lie in [0, 1).")
    required = {block_column, "retention_rate"}
    missing = sorted(required.difference(audit.columns))
    if missing:
        raise KeyError(f"Retention audit is missing columns: {missing}")
    rates = pd.to_numeric(audit["retention_rate"], errors="coerce")
    failed = rates.isna() | rates.le(threshold)
    if bool(failed.any()):
        details = ", ".join(
            f"{block}={rate:.6f}"
            for block, rate in zip(
                audit.loc[failed, block_column].astype(str), rates.loc[failed], strict=True
            )
        )
        raise RuntimeError(
            f"Outcome-label retention must exceed {threshold:.2%} in every block; failed: {details}"
        )


def parse_term_months(terms: pd.Series) -> pd.Series:
    """Extract integer term months from raw Lending Club values."""
    return pd.to_numeric(
        terms.astype("string").str.extract(r"(\d+)", expand=False),
        errors="coerce",
    ).astype("Int16")


def parse_issue_dates(values: pd.Series) -> pd.Series:
    """Parse the raw month-year issue date with a conservative fallback."""
    parsed = pd.to_datetime(values, format="%b-%Y", errors="coerce")
    missing = parsed.isna() & values.notna()
    if bool(missing.any()):
        parsed.loc[missing] = pd.to_datetime(values.loc[missing], errors="coerce")
    return parsed


def _between(dates: pd.Series, start: object, end: object) -> pd.Series:
    return dates.between(pd.Timestamp(str(start)), pd.Timestamp(str(end)))


def assign_design_split(issue_dates: pd.Series, design: Mapping[str, Any]) -> pd.Series:
    """Assign every block from issue date alone; status never affects membership."""
    dates = pd.to_datetime(issue_dates, errors="coerce")
    labels = pd.Series("outside_design", index=issue_dates.index, dtype="string")
    labels.loc[dates.le(pd.Timestamp(str(design["development_end"])))] = "pd_development"
    labels.loc[
        _between(
            dates,
            design["probability_calibration_start"],
            design["probability_calibration_end"],
        )
    ] = "probability_calibration"
    labels.loc[_between(dates, design["conformal_fit_start"], design["conformal_fit_end"])] = (
        "conformal_fit"
    )
    labels.loc[
        _between(
            dates,
            design["policy_development_start"],
            design["policy_development_end"],
        )
    ] = "policy_development"

    periods = dates.dt.to_period("M").astype("string")
    primary = pd.period_range(
        str(design["primary_oot_start_month"]),
        str(design["primary_oot_end_month"]),
        freq="M",
    ).astype(str)
    extension = pd.period_range(
        str(design["censored_extension_start_month"]),
        str(design["censored_extension_end_month"]),
        freq="M",
    ).astype(str)
    labels.loc[periods.isin(primary)] = "primary_oot"
    labels.loc[periods.isin(extension)] = "censored_extension"
    return labels.rename("design_split")


def _require_timestamp(value: Any, *, context: str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if not isinstance(timestamp, pd.Timestamp):
        raise ValueError(f"{context} is missing or is not a valid timestamp.")
    return timestamp


def temporal_tail_split(
    frame: pd.DataFrame,
    *,
    tail_fraction: float,
    date_column: str = "issue_d",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    """Split a development frame at a whole-month temporal boundary."""
    fraction = float(tail_fraction)
    if not 0.0 < fraction < 1.0:
        raise ValueError("tail_fraction must lie in (0, 1).")
    ordered = frame.sort_values([date_column, "id"], kind="mergesort")
    if len(ordered) < 2:
        raise ValueError("Temporal validation requires at least two rows.")
    position = max(1, min(len(ordered) - 1, int(np.floor(len(ordered) * (1 - fraction)))))
    cutoff_value = _require_timestamp(
        ordered.iloc[position][date_column], context="temporal validation cutoff"
    )
    cutoff = cutoff_value.to_period("M").to_timestamp()
    train = ordered.loc[ordered[date_column] < cutoff].copy()
    validation = ordered.loc[ordered[date_column] >= cutoff].copy()
    if train.empty or validation.empty:
        raise ValueError("Whole-month temporal tail split produced an empty block.")
    train_max = _require_timestamp(train[date_column].max(), context="training maximum")
    validation_min = _require_timestamp(validation[date_column].min(), context="validation minimum")
    if train_max >= validation_min:
        raise AssertionError("Temporal validation blocks overlap or contain invalid dates.")
    return train, validation, cutoff


def maturity_gap_months(earlier_end: str | pd.Timestamp, later_start: str | pd.Timestamp) -> int:
    """Return the difference between two calendar-month indices."""
    earlier = _require_timestamp(earlier_end, context="earlier boundary")
    later = _require_timestamp(later_start, context="later boundary")
    return int((later.year * 12 + later.month) - (earlier.year * 12 + earlier.month))


def load_design_universe(
    config: Mapping[str, Any],
    *,
    raw_path: Path,
    label_required_splits: Collection[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load declared windows from raw data without filtering on loan status.

    ``label_required_splits`` separates blocks that consume outcomes from
    outcome-free decision-development menus. The legacy default preserves the
    historical maturity-safe selector contract.
    """
    source = config["source"]
    design = config["design"]
    required_columns = [str(value) for value in source["required_raw_columns"]]
    header_frame = pd.read_csv(raw_path, nrows=0)
    header = [str(column) for column in header_frame.columns]
    missing = sorted(set(required_columns).difference(header))
    if missing:
        raise KeyError(f"Raw Lending Club CSV is missing columns: {missing}")

    chunks: list[pd.DataFrame] = []
    counters: dict[str, Any] = {
        "raw_rows_seen": 0,
        "invalid_issue_date_rows": 0,
        "term_36_rows_all_dates": 0,
        "declared_window_rows_all_terms": 0,
        "retained_rows": 0,
    }
    reader = pd.read_csv(
        raw_path,
        usecols=required_columns,
        dtype={"id": "string", "loan_status": "string", "term": "string"},
        chunksize=int(source["csv_chunksize"]),
        low_memory=False,
    )
    for chunk in reader:
        counters["raw_rows_seen"] += int(len(chunk))
        issue_dates = parse_issue_dates(chunk["issue_d"])
        terms = parse_term_months(chunk["term"])
        design_split = assign_design_split(issue_dates, design)
        counters["invalid_issue_date_rows"] += int(issue_dates.isna().sum())
        counters["term_36_rows_all_dates"] += int(terms.eq(36).fillna(False).sum())
        in_window = design_split.ne("outside_design")
        counters["declared_window_rows_all_terms"] += int(in_window.sum())
        keep = terms.eq(int(design["term_months"])).fillna(False) & in_window
        if not bool(keep.any()):
            continue
        retained = chunk.loc[keep].copy()
        retained["issue_d"] = issue_dates.loc[keep]
        retained["term_months"] = terms.loc[keep]
        retained["design_split"] = design_split.loc[keep]
        chunks.append(retained)
        counters["retained_rows"] += int(len(retained))

    if not chunks:
        raise RuntimeError("Raw scan found no loans under the declared design.")
    frame = pd.concat(chunks, ignore_index=True)
    if bool(frame["id"].isna().any()):
        raise ValueError("Retained design universe contains missing loan IDs.")
    frame["id"] = frame["id"].astype("string").str.strip()
    if bool(frame["id"].duplicated().any()):
        examples = frame.loc[frame["id"].duplicated(keep=False), "id"].head(5).tolist()
        raise ValueError(f"Retained design universe contains duplicate IDs: {examples}")
    frame["snapshot_default"] = snapshot_default_from_status(frame["loan_status"])
    frame["snapshot_resolution"] = snapshot_resolution_from_status(frame["loan_status"])
    frame = frame.sort_values(["issue_d", "id"], kind="mergesort").reset_index(drop=True)

    required_labels = (
        LABEL_REQUIRED_SPLITS
        if label_required_splits is None
        else frozenset(str(value) for value in label_required_splits)
    )
    required_splits = required_labels | DECISION_SPLITS
    observed_splits = set(frame["design_split"].astype(str))
    absent = sorted(required_splits.difference(observed_splits))
    if absent:
        raise RuntimeError(f"Declared design blocks are empty: {absent}")
    label_rows = frame["design_split"].isin(required_labels)
    unresolved = int(frame.loc[label_rows, "snapshot_default"].isna().sum())
    if unresolved:
        raise RuntimeError(f"Label-required blocks contain {unresolved} unresolved rows.")

    split_inventory = (
        frame.groupby(["design_split", "snapshot_resolution"], observed=True)
        .size()
        .to_frame("rows")
        .reset_index()
    )
    status_inventory = (
        frame.assign(normalized_status=normalize_loan_status(frame["loan_status"]))
        .groupby(["design_split", "normalized_status"], observed=True)
        .size()
        .to_frame("rows")
        .reset_index()
    )
    counters.update(
        {
            "retained_rows_by_split": {
                str(key): int(value)
                for key, value in frame["design_split"].value_counts().sort_index().items()
            },
            "resolved_rows": int(frame["snapshot_default"].notna().sum()),
            "unresolved_rows": int(frame["snapshot_default"].isna().sum()),
            "raw_schema_columns": header,
            "split_inventory": split_inventory.to_dict(orient="records"),
            "status_inventory": status_inventory.to_dict(orient="records"),
            "membership_uses_loan_status": False,
            "label_required_splits": sorted(required_labels),
        }
    )
    return frame, counters


def _month_set(frame: pd.DataFrame, split: str) -> set[str]:
    dates = pd.to_datetime(frame.loc[frame["design_split"].eq(split), "issue_d"], errors="coerce")
    return set(dates.dt.to_period("M").astype(str))


def _expected_months(start: object, end: object) -> set[str]:
    return set(pd.period_range(str(start), str(end), freq="M").astype(str))


def validate_maturity_contract(
    frame: pd.DataFrame,
    design: Mapping[str, Any],
    source: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate chronology, label maturity, and snapshot observability."""
    ordered_blocks = [
        "pd_development",
        "probability_calibration",
        "conformal_fit",
        "policy_development",
        "primary_oot",
        "censored_extension",
    ]
    bounds: dict[str, dict[str, str]] = {}
    previous_max: pd.Timestamp | None = None
    for block in ordered_blocks:
        dates = pd.to_datetime(
            frame.loc[frame["design_split"].eq(block), "issue_d"], errors="coerce"
        )
        if dates.empty or bool(dates.isna().any()):
            raise RuntimeError(f"Chronology block {block} is empty or has invalid dates.")
        block_min = _require_timestamp(dates.min(), context=f"{block} minimum")
        block_max = _require_timestamp(dates.max(), context=f"{block} maximum")
        if previous_max is not None and previous_max >= block_min:
            raise RuntimeError(f"Chronology blocks overlap or are out of order at {block}.")
        bounds[block] = {
            "first_issue_month": str(block_min.to_period("M")),
            "last_issue_month": str(block_max.to_period("M")),
        }
        previous_max = block_max

    expected = {
        "primary_oot": _expected_months(
            design["primary_oot_start_month"], design["primary_oot_end_month"]
        ),
        "censored_extension": _expected_months(
            design["censored_extension_start_month"], design["censored_extension_end_month"]
        ),
    }
    for split, expected_months in expected.items():
        if _month_set(frame, split) != expected_months:
            raise RuntimeError(f"{split} does not cover its complete declared monthly range.")

    policy_end = _require_timestamp(
        str(design["policy_development_end"]), context="policy development end"
    )
    primary_start = _require_timestamp(
        str(design["primary_oot_start_month"]), context="primary OOT start"
    )
    gap = maturity_gap_months(policy_end, primary_start)
    required = int(design["minimum_maturity_gap_months"])
    if gap < required:
        raise RuntimeError(f"Maturity gap is {gap} months; declared minimum is {required}.")
    term_months = int(design["term_months"])
    policy_maturity = policy_end + pd.DateOffset(months=term_months)
    if policy_maturity >= primary_start:
        raise RuntimeError("The latest policy-development loan is not mature before primary OOT.")

    snapshot_date = _require_timestamp(str(source["snapshot_date"]), context="snapshot date")
    latest_issue = _require_timestamp(frame["issue_d"].max(), context="latest issue date")
    latest_contract_maturity = latest_issue + pd.DateOffset(months=term_months)
    return {
        "block_boundaries": bounds,
        "policy_development_contract_maturity_month": str(policy_maturity.to_period("M")),
        "primary_oot_first_issue_month": str(primary_start.to_period("M")),
        "maturity_gap_months": gap,
        "minimum_maturity_gap_months": required,
        "snapshot_date": str(snapshot_date.date()),
        "latest_retained_contract_maturity_month": str(latest_contract_maturity.to_period("M")),
        "latest_contract_maturity_after_snapshot": bool(latest_contract_maturity > snapshot_date),
        "membership_uses_loan_status": False,
        "passes": True,
    }
