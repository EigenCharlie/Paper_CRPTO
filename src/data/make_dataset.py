"""Download raw data and perform initial cleaning.

Usage:
    uv run python -m src.data.make_dataset --input data/raw/lending_club.csv --output data/interim/
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

# Columns to drop immediately (known leakage or irrelevant)
LEAKAGE_COLS = [
    "total_pymnt",
    "total_pymnt_inv",
    "total_rec_prncp",
    "total_rec_int",
    "total_rec_late_fee",
    "recoveries",
    "collection_recovery_fee",
    "last_pymnt_d",
    "last_pymnt_amnt",
    "last_credit_pull_d",
    "out_prncp",
    "out_prncp_inv",
    "funded_amnt",
    "funded_amnt_inv",
    "total_bal_il",
    "il_util",
    "max_bal_bc",
    "all_util",
    "total_rev_hi_lim",
    "debt_settlement_flag",
    "settlement_status",
    "settlement_date",
    "settlement_amount",
    "settlement_percentage",
    "settlement_term",
    "hardship_flag",
    "hardship_type",
    "hardship_reason",
    "hardship_status",
    "hardship_amount",
    "hardship_start_date",
    "hardship_end_date",
    "hardship_length",
    "hardship_dpd",
    "hardship_loan_status",
    "hardship_payoff_balance_amount",
    "hardship_last_payment_amount",
    "payment_plan_start_date",
]

LGD_SNAPSHOT_DATE = pd.Timestamp("2020-09-30")

# Snapshot labels. Status variants such as "Does not meet the credit policy"
# are normalized by pattern rather than silently discarded.
DEFAULT_STATUSES = ["Charged Off", "Default"]
NONDEFAULT_STATUSES = ["Fully Paid"]


def _to_numeric_series(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    if col not in df.columns:
        return pd.Series(default, index=df.index, dtype=float)
    return pd.to_numeric(df[col], errors="coerce").fillna(default)


def _parse_issue_dates(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, format="%b-%Y", errors="coerce")
    missing = parsed.isna()
    if missing.any():
        parsed.loc[missing] = pd.to_datetime(series.loc[missing], errors="coerce")
    return parsed


def _snapshot_default_target(statuses: pd.Series) -> pd.Series:
    """Map resolved snapshot statuses to a nullable binary target.

    Unresolved loans remain missing. Their membership is an origination-time
    fact, while their eventual outcome is not available at the snapshot.
    """
    normalized = statuses.fillna("").astype(str).str.strip().str.lower()
    is_default = normalized.eq("default") | normalized.str.contains("charged off", regex=False)
    is_nondefault = normalized.str.contains("fully paid", regex=False)
    target = pd.Series(pd.NA, index=statuses.index, dtype="Int8", name="default_flag")
    target.loc[is_nondefault] = 0
    target.loc[is_default] = 1
    return target


def _compute_lgd(df: pd.DataFrame) -> pd.Series:
    """Compute realized LGD in [0, 1] using principal recovery components.

    Formula:
        LGD = 1 - (total_rec_prncp + recoveries - collection_recovery_fee) / exposure
    where exposure uses `funded_amnt` if available, otherwise `loan_amnt`.

    Notes:
    - LGD is a default-conditional target, but we persist 0.0 for non-default rows.
    - Values are clipped to [0, 1] to avoid data-quality outliers.
    """
    exposure = _to_numeric_series(df, "funded_amnt", default=0.0)
    if "loan_amnt" in df.columns:
        exposure = exposure.where(exposure > 0.0, _to_numeric_series(df, "loan_amnt", default=0.0))
    exposure = exposure.where(exposure > 0.0, pd.NA)

    total_rec_prncp = _to_numeric_series(df, "total_rec_prncp", default=0.0)
    recoveries = _to_numeric_series(df, "recoveries", default=0.0)
    collection_fee = _to_numeric_series(df, "collection_recovery_fee", default=0.0)
    recovered_principal = total_rec_prncp + recoveries - collection_fee

    lgd = 1.0 - (recovered_principal / exposure)
    lgd = lgd.clip(lower=0.0, upper=1.0)

    if "default_flag" not in df.columns:
        return lgd.fillna(1.0).clip(lower=0.0, upper=1.0).astype(float)

    target = pd.to_numeric(df["default_flag"], errors="coerce")
    default_mask = target.eq(1).fillna(False)
    nondefault_mask = target.eq(0).fillna(False)
    result = pd.Series(pd.NA, index=df.index, dtype="Float64", name="lgd")
    result.loc[default_mask] = lgd.loc[default_mask].fillna(1.0).clip(0.0, 1.0)
    result.loc[nondefault_mask] = 0.0
    return result


def load_raw_data(filepath: str | Path) -> pd.DataFrame:
    """Load raw Lending Club CSV."""
    logger.info(f"Loading raw data from {filepath}")
    df = pd.read_csv(filepath, low_memory=False)
    logger.info(f"Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


def initial_clean(df: pd.DataFrame, *, legacy_resolved_only: bool = False) -> pd.DataFrame:
    """Remove leakage columns while preserving the origination-time universe.

    ``legacy_resolved_only`` exists solely to reproduce the frozen historical
    lane. New research must retain unresolved rows and handle label availability
    through a declared temporal protocol.
    """
    if "loan_status" not in df.columns:
        raise KeyError("Raw Lending Club data must contain loan_status.")
    df = df.copy()
    df["default_flag"] = _snapshot_default_target(df["loan_status"])
    df["outcome_observed"] = df["default_flag"].notna()
    if legacy_resolved_only:
        df = df.loc[df["outcome_observed"]].copy()
        logger.warning("Applied explicit legacy resolved-only filter: {:,} rows", len(df))
    else:
        logger.info(
            "Retained status-independent universe: {:,} rows ({:,} unresolved)",
            len(df),
            int(df["default_flag"].isna().sum()),
        )

    observed = df.loc[df["outcome_observed"], "default_flag"].astype(float)
    if not observed.empty:
        logger.info("Observed-outcome default rate: {:.2%}", float(observed.mean()))

    # Build LGD target before leakage fields are dropped.
    df["lgd"] = _compute_lgd(df)
    if "issue_d" in df.columns:
        issue_dt = _parse_issue_dates(df["issue_d"])
        age_months = ((LGD_SNAPSHOT_DATE - issue_dt).dt.days.astype(float) / 30.4375).clip(
            lower=0.0
        )
        df["lgd_months_since_issue"] = age_months.fillna(0.0).astype(float)
        df["lgd_is_mature_24m"] = (age_months >= 24.0).fillna(False).astype(int)
    lgd_default = df.loc[df["default_flag"] == 1, "lgd"]
    if not lgd_default.empty:
        logger.info(
            "LGD target built: default_rows={}, mean={:.4f}, p50={:.4f}",
            len(lgd_default),
            float(lgd_default.mean()),
            float(lgd_default.median()),
        )

    cols_to_drop = [c for c in LEAKAGE_COLS if c in df.columns]
    df = df.drop(columns=cols_to_drop)
    logger.info(f"Dropped {len(cols_to_drop)} leakage/irrelevant columns")

    return df


def save_interim(df: pd.DataFrame, output_dir: str | Path) -> Path:
    """Save cleaned data to interim directory."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / "lending_club_cleaned.parquet"
    df.to_parquet(filepath, index=False)
    logger.info(f"Saved interim data to {filepath} ({len(df):,} rows)")
    return filepath


def main(
    input_path: str = "data/raw/Loan_status_2007-2020Q3.csv",
    output_dir: str = "data/interim/",
    *,
    legacy_resolved_only: bool = False,
) -> None:
    """Run full make_dataset pipeline."""
    df = load_raw_data(input_path)
    df = initial_clean(df, legacy_resolved_only=legacy_resolved_only)
    save_interim(df, output_dir)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Make dataset from raw Lending Club CSV")
    parser.add_argument("--input", default="data/raw/Loan_status_2007-2020Q3.csv")
    parser.add_argument("--output", default="data/interim/")
    parser.add_argument(
        "--legacy-resolved-only",
        action="store_true",
        help="Reproduce the frozen historical status filter; invalid for new prospective analyses.",
    )
    args = parser.parse_args()
    main(args.input, args.output, legacy_resolved_only=args.legacy_resolved_only)
