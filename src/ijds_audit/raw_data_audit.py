"""Full-archive schema and temporal-availability audit for the IJDS design."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import duckdb
import pandas as pd

POST_OUTCOME_COLUMNS = frozenset(
    {
        "loan_status",
        "out_prncp",
        "out_prncp_inv",
        "total_pymnt",
        "total_pymnt_inv",
        "total_rec_prncp",
        "total_rec_int",
        "total_rec_late_fee",
        "recoveries",
        "collection_recovery_fee",
        "last_pymnt_d",
        "last_pymnt_amnt",
        "next_pymnt_d",
        "last_credit_pull_d",
        "last_fico_range_high",
        "last_fico_range_low",
        "pymnt_plan",
        "hardship_flag",
        "hardship_type",
        "hardship_reason",
        "hardship_status",
        "deferral_term",
        "hardship_amount",
        "hardship_start_date",
        "hardship_end_date",
        "payment_plan_start_date",
        "hardship_length",
        "hardship_dpd",
        "hardship_loan_status",
        "orig_projected_additional_accrued_interest",
        "hardship_payoff_balance_amount",
        "hardship_last_payment_amount",
        "debt_settlement_flag",
    }
)

IDENTIFIER_OR_FREE_TEXT_COLUMNS = frozenset(
    {"column000", "id", "url", "title", "emp_title", "zip_code"}
)
GEOGRAPHY_PROXY_COLUMNS = frozenset({"addr_state"})
PROTOCOL_METADATA_COLUMNS = frozenset({"issue_d", "term"})
CONTEMPORANEOUS_FUNDING_COLUMNS = frozenset({"funded_amnt", "funded_amnt_inv"})


@dataclass(frozen=True)
class RawDataAudit:
    """Small, inspectable outputs from one full raw-CSV scan."""

    archive_inventory: pd.DataFrame
    status_inventory: pd.DataFrame
    inventory: pd.DataFrame
    feature_coverage: pd.DataFrame
    feature_contract: pd.DataFrame
    amount_alignment: pd.DataFrame
    cutoff_label_availability: pd.DataFrame


def _identifier(column: str) -> str:
    return '"' + str(column).replace('"', '""') + '"'


def _date(value: Any) -> str:
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        raise ValueError(f"Invalid protocol date: {value!r}")
    return cast(pd.Timestamp, timestamp).strftime("%Y-%m-%d")


def _period_start(value: Any) -> str:
    period = pd.Period(str(value), freq="M")
    if pd.isna(period):
        raise ValueError(f"Invalid protocol month: {value!r}")
    return cast(pd.Period, period).start_time.strftime("%Y-%m-%d")


def _period_end(value: Any) -> str:
    period = pd.Period(str(value), freq="M")
    if pd.isna(period):
        raise ValueError(f"Invalid protocol month: {value!r}")
    return cast(pd.Period, period).end_time.normalize().strftime("%Y-%m-%d")


def cohort_case_sql(design: Mapping[str, Any], source: Mapping[str, Any]) -> str:
    """Return the exhaustive 36-month cohort partition used by the audit."""
    return f"""CASE
        WHEN issue_date <= DATE '{_date(design["development_end"])}'
            THEN 'pd_development'
        WHEN issue_date BETWEEN DATE '{_date(design["probability_calibration_start"])}'
             AND DATE '{_date(design["probability_calibration_end"])}'
            THEN 'probability_calibration'
        WHEN issue_date BETWEEN DATE '{_date(design["conformal_fit_start"])}'
             AND DATE '{_date(design["conformal_fit_end"])}'
            THEN 'conformal_fit'
        WHEN issue_date BETWEEN DATE '{_date(design["policy_development_start"])}'
             AND DATE '{_date(design["policy_development_end"])}'
            THEN 'policy_development'
        WHEN issue_date > DATE '{_date(design["policy_development_end"])}'
             AND issue_date <= DATE '{_date(source["information_cutoff"])}'
            THEN 'maturity_gap'
        WHEN issue_date BETWEEN DATE '{_period_start(design["primary_oot_start_month"])}'
             AND DATE '{_period_end(design["primary_oot_end_month"])}'
            THEN 'primary_oot'
        WHEN issue_date BETWEEN DATE '{_period_start(design["censored_extension_start_month"])}'
             AND DATE '{_period_end(design["censored_extension_end_month"])}'
            THEN 'censored_extension'
        WHEN issue_date > DATE '{_period_end(design["censored_extension_end_month"])}'
            THEN 'post_extension'
        ELSE 'outside_declared_timeline'
    END"""


def classify_raw_column(column: str, *, active_required: Sequence[str]) -> tuple[str, str]:
    """Assign a conservative provenance role without looking at outcomes."""
    name = str(column)
    if name in POST_OUTCOME_COLUMNS or name.startswith("hardship_"):
        return "post_outcome_or_servicing", "never eligible as a prediction feature"
    if name in IDENTIFIER_OR_FREE_TEXT_COLUMNS:
        return "identifier_or_free_text", "excluded from the scientific feature contract"
    if name in GEOGRAPHY_PROXY_COLUMNS:
        return "geography_proxy", "available but excluded from the active model"
    if name in PROTOCOL_METADATA_COLUMNS:
        return "protocol_metadata", "used for chronology or term eligibility"
    if name in CONTEMPORANEOUS_FUNDING_COLUMNS:
        return (
            "contemporaneous_funding",
            "audited separately; not needed by the active portfolio because requested and funded amounts nearly coincide",
        )
    if name.startswith("sec_app_") or name in {
        "application_type",
        "annual_inc_joint",
        "dti_joint",
        "verification_status_joint",
        "revol_bal_joint",
    }:
        return "joint_application_origination", "origination-time but introduced late"
    if name in active_required:
        return "active_protocol_input", "loaded by the active maturity-safe protocol"
    return "candidate_origination", "requires temporal coverage and leakage review"


def _raw_relation(path: Path) -> str:
    escaped = str(path.resolve()).replace("'", "''")
    return (
        "read_csv('"
        + escaped
        + "', auto_detect=true, sample_size=200000, all_varchar=true, ignore_errors=false)"
    )


def _header(connection: duckdb.DuckDBPyConnection, raw_path: Path) -> list[str]:
    rows = connection.execute(f"DESCRIBE SELECT * FROM {_raw_relation(raw_path)}").fetchall()
    return [str(row[0]) for row in rows]


def _archive_inventory(
    connection: duckdb.DuckDBPyConnection,
    raw_path: Path,
    *,
    servicing_cutoff: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cutoff = pd.Timestamp(servicing_cutoff).date().isoformat()
    parsed = f"""
        SELECT *,
               try_strptime(issue_d, '%b-%Y') AS issue_date,
               try_strptime(last_pymnt_d, '%b-%Y') AS last_payment_date,
               try_strptime(last_credit_pull_d, '%b-%Y') AS last_credit_pull_date,
               try_cast(regexp_extract(term, '([0-9]+)', 1) AS INTEGER) AS term_months
        FROM {_raw_relation(raw_path)}
    """
    inventory = connection.execute(
        f"""
        WITH parsed AS ({parsed})
        SELECT count(*) AS raw_rows,
               count(DISTINCT nullif(trim(id), '')) AS distinct_nonblank_ids,
               sum(CASE WHEN id IS NULL OR trim(id) = '' THEN 1 ELSE 0 END) AS blank_id_rows,
               sum(CASE WHEN issue_date IS NOT NULL THEN 1 ELSE 0 END) AS valid_loan_rows,
               sum(CASE WHEN issue_date IS NULL THEN 1 ELSE 0 END) AS invalid_issue_date_rows,
               min(issue_date) AS first_issue_date,
               max(issue_date) AS last_issue_date,
               max(last_payment_date) AS last_payment_date_max,
               max(last_credit_pull_date) AS last_credit_pull_date_max,
               sum(CASE WHEN last_payment_date > DATE '{cutoff}' THEN 1 ELSE 0 END)
                   AS last_payment_rows_after_cutoff,
               sum(CASE WHEN last_credit_pull_date > DATE '{cutoff}' THEN 1 ELSE 0 END)
                   AS last_credit_pull_rows_after_cutoff,
               sum(CASE WHEN term_months = 36 THEN 1 ELSE 0 END) AS term36_rows,
               sum(CASE WHEN term_months = 60 THEN 1 ELSE 0 END) AS term60_rows,
               sum(CASE WHEN term_months NOT IN (36, 60) OR term_months IS NULL THEN 1 ELSE 0 END)
                   AS other_or_invalid_term_rows
        FROM parsed
        """
    ).fetchdf()
    for column in (
        "first_issue_date",
        "last_issue_date",
        "last_payment_date_max",
        "last_credit_pull_date_max",
    ):
        inventory[column] = inventory[column].map(
            lambda value: _date(value) if pd.notna(value) else None
        )
    statuses = connection.execute(
        f"""
        WITH parsed AS ({parsed})
        SELECT coalesce(nullif(trim(loan_status), ''), '__MISSING__') AS loan_status,
               count(*) AS rows,
               sum(CASE WHEN term_months = 36 THEN 1 ELSE 0 END) AS term36_rows,
               sum(CASE WHEN term_months = 60 THEN 1 ELSE 0 END) AS term60_rows
        FROM parsed
        GROUP BY loan_status
        ORDER BY rows DESC, loan_status
        """
    ).fetchdf()
    return inventory, statuses


def _profile_coverage(
    connection: duckdb.DuckDBPyConnection,
    raw_path: Path,
    *,
    columns: Sequence[str],
    cohort_sql: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    profile_columns = [
        column for column in columns if column not in {"column000", "id", "issue_d", "term"}
    ]
    expressions = ["count(*) AS rows"]
    for column in profile_columns:
        quoted = _identifier(column)
        present = f"({quoted} IS NOT NULL AND trim({quoted}) <> '')"
        expressions.extend(
            [
                f"sum(CASE WHEN {present} THEN 1 ELSE 0 END) AS {_identifier(column + '__n')}",
                f"min(issue_date) FILTER (WHERE {present}) AS {_identifier(column + '__first')}",
            ]
        )
    query = f"""
        WITH parsed AS (
            SELECT *,
                   try_strptime(issue_d, '%b-%Y') AS issue_date,
                   try_cast(regexp_extract(term, '([0-9]+)', 1) AS INTEGER) AS term_months
            FROM {_raw_relation(raw_path)}
        ), term36 AS (
            SELECT *, {cohort_sql} AS cohort
            FROM parsed
            WHERE issue_date IS NOT NULL AND term_months = 36
        )
        SELECT cohort, {", ".join(expressions)}
        FROM term36
        GROUP BY cohort
        ORDER BY cohort
    """
    wide = connection.execute(query).fetchdf()
    coverage_rows: list[dict[str, Any]] = []
    for record in wide.to_dict(orient="records"):
        cohort = str(record["cohort"])
        rows = int(record["rows"])
        for column in profile_columns:
            present_rows = int(record[f"{column}__n"])
            first_seen = record[f"{column}__first"]
            coverage_rows.append(
                {
                    "cohort": cohort,
                    "feature": column,
                    "rows": rows,
                    "present_rows": present_rows,
                    "coverage": present_rows / rows if rows else 0.0,
                    "first_seen": (
                        cast(pd.Timestamp, pd.Timestamp(first_seen)).strftime("%Y-%m-%d")
                        if pd.notna(first_seen)
                        else None
                    ),
                }
            )
    coverage = pd.DataFrame(coverage_rows).sort_values(["feature", "cohort"]).reset_index(drop=True)
    inventory = wide[["cohort", "rows"]].copy()
    return inventory, coverage


def _amount_alignment(
    connection: duckdb.DuckDBPyConnection, raw_path: Path, *, cohort_sql: str
) -> pd.DataFrame:
    query = f"""
        WITH parsed AS (
            SELECT try_strptime(issue_d, '%b-%Y') AS issue_date,
                   try_cast(regexp_extract(term, '([0-9]+)', 1) AS INTEGER) AS term_months,
                   try_cast(loan_amnt AS DOUBLE) AS loan_amnt,
                   try_cast(funded_amnt AS DOUBLE) AS funded_amnt
            FROM {_raw_relation(raw_path)}
        ), term36 AS (
            SELECT *, {cohort_sql} AS cohort
            FROM parsed
            WHERE issue_date IS NOT NULL AND term_months = 36
        )
        SELECT cohort,
               count(*) AS rows,
               sum(loan_amnt - funded_amnt) AS total_gap,
               avg(loan_amnt - funded_amnt) AS mean_gap,
               quantile_cont(loan_amnt - funded_amnt, 0.5) AS median_gap,
               max(loan_amnt - funded_amnt) AS max_gap,
               avg(CASE WHEN loan_amnt > funded_amnt THEN 1.0 ELSE 0.0 END) AS partial_share,
               sum(funded_amnt) / sum(loan_amnt) AS funded_ratio
        FROM term36
        GROUP BY cohort
        ORDER BY cohort
    """
    return connection.execute(query).fetchdf()


def _cutoff_label_availability(
    connection: duckdb.DuckDBPyConnection,
    raw_path: Path,
    *,
    design: Mapping[str, Any],
    source: Mapping[str, Any],
) -> pd.DataFrame:
    cutoff = _date(source["information_cutoff"])
    lag = int(source["charged_off_reporting_lag_months"])
    start = _date(pd.Timestamp(design["policy_development_end"]) + pd.Timedelta(days=1))
    query = f"""
        WITH parsed AS (
            SELECT try_strptime(issue_d, '%b-%Y') AS issue_date,
                   try_cast(regexp_extract(term, '([0-9]+)', 1) AS INTEGER) AS term_months,
                   lower(trim(loan_status)) AS status,
                   try_strptime(last_pymnt_d, '%b-%Y') AS last_payment
            FROM {_raw_relation(raw_path)}
        ), gap AS (
            SELECT *,
                   status LIKE '%fully paid%' AS is_good,
                   status LIKE '%charged off%' AS is_bad,
                   CASE
                       WHEN status LIKE '%fully paid%'
                           THEN last_payment <= DATE '{cutoff}'
                       WHEN status LIKE '%charged off%'
                           THEN last_payment + INTERVAL {lag} MONTH <= DATE '{cutoff}'
                       ELSE false
                   END AS label_available
            FROM parsed
            WHERE term_months = 36
              AND issue_date BETWEEN DATE '{start}' AND DATE '{cutoff}'
        )
        SELECT year(issue_date) AS issue_year,
               count(*) AS rows,
               sum(CASE WHEN is_good OR is_bad THEN 1 ELSE 0 END) AS terminal_at_snapshot,
               sum(CASE WHEN label_available THEN 1 ELSE 0 END) AS available_by_cutoff,
               avg(CASE WHEN label_available THEN 1.0 ELSE 0.0 END) AS available_rate,
               sum(CASE WHEN is_bad AND label_available THEN 1 ELSE 0 END) AS available_bad,
               sum(CASE WHEN is_good AND label_available THEN 1 ELSE 0 END) AS available_good
        FROM gap
        GROUP BY issue_year
        ORDER BY issue_year
    """
    return connection.execute(query).fetchdf()


def _feature_contract(
    coverage: pd.DataFrame,
    *,
    columns: Sequence[str],
    active_required: Sequence[str],
    rules: Mapping[str, Any],
) -> pd.DataFrame:
    fitting = {"pd_development", "probability_calibration", "conformal_fit"}
    minimum_required = float(rules["minimum_fitting_feature_coverage"])
    late_fitting = float(rules["late_feature_fitting_coverage"])
    late_primary = float(rules["late_feature_primary_coverage"])
    exceptions = rules.get("active_feature_coverage_exceptions", {})
    if not isinstance(exceptions, Mapping):
        raise TypeError("active_feature_coverage_exceptions must be a mapping.")
    pivot = coverage.pivot(index="feature", columns="cohort", values="coverage")
    rows: list[dict[str, Any]] = []
    for column in columns:
        role, reason = classify_raw_column(column, active_required=active_required)
        values = pivot.loc[column] if column in pivot.index else pd.Series(dtype=float)
        fitting_values = [float(values.get(cohort, 0.0)) for cohort in sorted(fitting)]
        minimum_fitting_coverage = min(fitting_values) if fitting_values else 0.0
        primary_coverage = float(values.get("primary_oot", 0.0))
        exception = exceptions.get(column)
        if exception is not None and not isinstance(exception, Mapping):
            raise TypeError(f"Coverage exception for {column} must be a mapping.")
        exception_type = None if exception is None else str(exception["type"])
        requires_sensitivity = bool(
            exception is not None and exception.get("requires_sensitivity", False)
        )
        eligible = role in {"active_protocol_input", "candidate_origination"} and (
            minimum_fitting_coverage >= minimum_required or exception is not None
        )
        late_feature = minimum_fitting_coverage < late_fitting and primary_coverage >= late_primary
        rows.append(
            {
                "feature": column,
                "provenance_role": role,
                "loaded_by_active_protocol": column in active_required,
                "minimum_fitting_coverage": minimum_fitting_coverage,
                "primary_oot_coverage": primary_coverage,
                "coverage_threshold": minimum_required,
                "coverage_exception": exception_type,
                "missingness_semantics": (
                    None if exception is None else str(exception["missingness_semantics"])
                ),
                "requires_sensitivity": requires_sensitivity,
                "late_feature": late_feature,
                "eligible_for_current_temporal_model": eligible,
                "decision": (
                    "eligible_with_declared_coverage_exception"
                    if eligible and exception is not None
                    else "eligible"
                    if eligible
                    else "exclude_post_outcome"
                    if role == "post_outcome_or_servicing"
                    else "exclude_late_schema"
                    if late_feature
                    else "exclude_by_role_or_coverage"
                ),
                "reason": reason,
            }
        )
    return pd.DataFrame(rows).sort_values(["decision", "feature"]).reset_index(drop=True)


def audit_raw_dataset(
    raw_path: Path,
    config: Mapping[str, Any],
    *,
    rules: Mapping[str, Any],
) -> RawDataAudit:
    """Scan the complete CSV once per audit family and return compact evidence."""
    connection = duckdb.connect()
    connection.execute("PRAGMA threads=8")
    columns = _header(connection, raw_path)
    archive_inventory, status_inventory = _archive_inventory(
        connection,
        raw_path,
        servicing_cutoff=str(config["source"]["snapshot_date"]),
    )
    cohort_sql = cohort_case_sql(config["design"], config["source"])
    inventory, coverage = _profile_coverage(
        connection, raw_path, columns=columns, cohort_sql=cohort_sql
    )
    active_required = [str(value) for value in config["source"]["required_raw_columns"]]
    contract = _feature_contract(
        coverage,
        columns=columns,
        active_required=active_required,
        rules=rules,
    )
    amount = _amount_alignment(connection, raw_path, cohort_sql=cohort_sql)
    labels = _cutoff_label_availability(
        connection,
        raw_path,
        design=config["design"],
        source=config["source"],
    )
    connection.close()
    return RawDataAudit(
        archive_inventory=archive_inventory,
        status_inventory=status_inventory,
        inventory=inventory,
        feature_coverage=coverage,
        feature_contract=contract,
        amount_alignment=amount,
        cutoff_label_availability=labels,
    )
