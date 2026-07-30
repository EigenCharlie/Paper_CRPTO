"""V1d-only persistence repair for set-preserving embedding Phase B."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

PERSISTED_FRAME_KEYS = (
    "evaluated_portfolios",
    "monthly_sharp_contrasts",
    "window_sharp_contrasts",
    "metric_direction_census",
    "outcome_join_audit",
)
STRUCTURAL_NULL_RULES = {
    "frontier_cap": "objective_matched",
    "objective_target": "normalized_score",
    "risk_tolerance": "objective_matched",
}
PERSISTED_SCHEMA_DTYPES = {
    "evaluated_portfolios": (
        ("candidate_id", "str"),
        ("paired_policy_id", "str"),
        ("frontier_ruler", "str"),
        ("frontier_coordinate", "float64"),
        ("frontier_cap", "float64"),
        ("objective_target", "float64"),
        ("theta", "float64"),
        ("gamma", "float64"),
        ("risk_tolerance", "float64"),
        ("uncertainty_aversion", "float64"),
        ("embedding_contraction", "float64"),
        ("policy_mode", "str"),
        ("robust_guardrail", "bool"),
        ("solver_status", "str"),
        ("solver_backend_actual", "str"),
        ("expected_objective", "float64"),
        ("n_candidates", "int64"),
        ("n_positive_exposure", "int64"),
        ("n_exposure_above_reporting_tolerance", "int64"),
        ("total_allocated", "float64"),
        ("budget_residual", "float64"),
        ("weighted_pd_point", "float64"),
        ("weighted_pd_effective", "float64"),
        ("weighted_conformal_upper", "float64"),
        ("weighted_embedding_upper", "float64"),
        ("minimum_score", "float64"),
        ("score_at_objective", "float64"),
        ("score_range", "float64"),
        ("minimum_score_portfolio_objective", "float64"),
        ("common_objective_lower", "float64"),
        ("unconstrained_objective", "float64"),
        ("objective_retention", "float64"),
        ("constraint_slack", "float64"),
        ("highs_simplex_iterations", "int64"),
        ("window_id", "str"),
        ("role", "str"),
        ("period", "str"),
        ("policy_label", "str"),
        ("comparator_rule", "str"),
        ("n_unresolved_candidates", "int64"),
        ("n_unresolved_positive_exposure", "int64"),
        ("unresolved_exposure_share", "float64"),
        ("realized_payoff_lower", "float64"),
        ("realized_payoff_upper", "float64"),
        ("weighted_default_lower", "float64"),
        ("weighted_default_upper", "float64"),
        ("weighted_miscoverage_lower", "float64"),
        ("weighted_miscoverage_upper", "float64"),
        ("full_budget", "bool"),
    ),
    "monthly_sharp_contrasts": (
        ("scope", "str"),
        ("window_id", "str"),
        ("period", "str"),
        ("normalization_rule", "str"),
        ("normalization_periods", "int64"),
        ("committed_budget_per_period", "float64"),
        ("contrast_family", "str"),
        ("ruler", "str"),
        ("coordinate", "float64"),
        ("theta", "float64"),
        ("theta_reference", "float64"),
        ("gamma", "float64"),
        ("gamma_reference", "float64"),
        ("contrast", "str"),
        ("role", "str"),
        ("policy_a", "str"),
        ("policy_b", "str"),
        ("policy_a_capital", "float64"),
        ("policy_b_capital", "float64"),
        ("policy_a_normalization_capital", "float64"),
        ("policy_b_normalization_capital", "float64"),
        ("funded_union_loans", "int64"),
        ("unresolved_union_loans", "int64"),
        ("expected_objective_difference", "float64"),
        ("realized_payoff_difference_lower", "float64"),
        ("realized_payoff_difference_upper", "float64"),
        ("realized_payoff_rate_difference_lower", "float64"),
        ("realized_payoff_rate_difference_upper", "float64"),
        ("weighted_default_difference_lower", "float64"),
        ("weighted_default_difference_upper", "float64"),
        ("weighted_miscoverage_difference_lower", "float64"),
        ("weighted_miscoverage_difference_upper", "float64"),
        ("realized_payoff_identification_width", "float64"),
        ("realized_payoff_rate_identification_width", "float64"),
        ("weighted_default_identification_width", "float64"),
        ("weighted_miscoverage_identification_width", "float64"),
        ("payoff_direction_sign_robust", "bool"),
        ("default_direction_sign_robust", "bool"),
        ("miscoverage_direction_sign_robust", "bool"),
        ("causal_interpretation", "bool"),
    ),
    "window_sharp_contrasts": (
        ("scope", "str"),
        ("window_id", "str"),
        ("normalization_rule", "str"),
        ("normalization_periods", "int64"),
        ("committed_budget_per_period", "float64"),
        ("contrast_family", "str"),
        ("ruler", "str"),
        ("coordinate", "float64"),
        ("theta", "float64"),
        ("theta_reference", "float64"),
        ("gamma", "float64"),
        ("gamma_reference", "float64"),
        ("contrast", "str"),
        ("role", "str"),
        ("policy_a", "str"),
        ("policy_b", "str"),
        ("policy_a_capital", "float64"),
        ("policy_b_capital", "float64"),
        ("policy_a_normalization_capital", "float64"),
        ("policy_b_normalization_capital", "float64"),
        ("funded_union_loans", "int64"),
        ("unresolved_union_loans", "int64"),
        ("expected_objective_difference", "float64"),
        ("realized_payoff_difference_lower", "float64"),
        ("realized_payoff_difference_upper", "float64"),
        ("realized_payoff_rate_difference_lower", "float64"),
        ("realized_payoff_rate_difference_upper", "float64"),
        ("weighted_default_difference_lower", "float64"),
        ("weighted_default_difference_upper", "float64"),
        ("weighted_miscoverage_difference_lower", "float64"),
        ("weighted_miscoverage_difference_upper", "float64"),
        ("realized_payoff_identification_width", "float64"),
        ("realized_payoff_rate_identification_width", "float64"),
        ("weighted_default_identification_width", "float64"),
        ("weighted_miscoverage_identification_width", "float64"),
        ("payoff_direction_sign_robust", "bool"),
        ("default_direction_sign_robust", "bool"),
        ("miscoverage_direction_sign_robust", "bool"),
        ("causal_interpretation", "bool"),
    ),
    "metric_direction_census": (
        ("window_id", "str"),
        ("contrast_family", "str"),
        ("ruler", "str"),
        ("coordinate", "float64"),
        ("theta", "float64"),
        ("theta_reference", "float64"),
        ("gamma", "float64"),
        ("gamma_reference", "float64"),
        ("policy_a", "str"),
        ("policy_b", "str"),
        ("metric", "str"),
        ("lower", "float64"),
        ("upper", "float64"),
        ("geometric_direction", "str"),
        ("direction_at_tolerance", "str"),
        ("direction_tolerance", "float64"),
    ),
    "outcome_join_audit": (
        ("role", "str"),
        ("period", "str"),
        ("candidate_rows", "int64"),
        ("unresolved_rows", "int64"),
        ("funded_allocation_rows", "int64"),
        ("funded_unique_ids", "int64"),
        ("policies", "int64"),
    ),
}
NUMERIC_DTYPE_NAMES = frozenset({"float64", "int64"})


def _numeric_array(frame: pd.DataFrame) -> np.ndarray:
    return frame.to_numpy(dtype=float, na_value=np.nan)


def expected_v1d_persisted_schemas(
    contract: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Materialize the exact post-drop row/name/order/dtype schema contract."""
    widths = contract["exact_persisted_schema_columns"]
    rows = contract["exact_persisted_schema_rows"]
    if set(widths) != set(PERSISTED_SCHEMA_DTYPES) or set(rows) != set(PERSISTED_SCHEMA_DTYPES):
        raise RuntimeError("V1d exact persisted schema census changed.")
    result: dict[str, dict[str, Any]] = {}
    for key, ordered_dtypes in PERSISTED_SCHEMA_DTYPES.items():
        if int(widths[key]) != len(ordered_dtypes):
            raise RuntimeError(f"V1d {key} width differs from its locked ordered schema.")
        result[key] = {
            "rows": int(rows[key]),
            "columns": len(ordered_dtypes),
            "dtypes": dict(ordered_dtypes),
        }
    return result


def _reject_coercible_numeric_values(series: pd.Series, *, label: str) -> pd.Series:
    nonmissing = series.loc[series.notna()]
    invalid_type = nonmissing.map(lambda value: isinstance(value, (str, bytes, bool, np.bool_)))
    if bool(invalid_type.any()):
        raise RuntimeError(f"V1d {label} contains a string/boolean numeric value.")
    try:
        return pd.to_numeric(series, errors="raise")
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"V1d {label} contains a nonnumeric value.") from error


def _validate_locked_schema(frame: pd.DataFrame, *, key: str, contract: Mapping[str, Any]) -> None:
    expected = expected_v1d_persisted_schemas(contract)[key]
    observed_items = tuple((str(column), str(dtype)) for column, dtype in frame.dtypes.items())
    expected_items = tuple(PERSISTED_SCHEMA_DTYPES[key])
    if len(frame) != int(expected["rows"]):
        raise RuntimeError(f"V1d {key} row census changed from its locked schema.")
    if observed_items != expected_items:
        raise RuntimeError(
            f"V1d {key} ordered column names or dtype families changed from the locked schema."
        )


def prepare_v1d_evaluated_portfolios(
    evaluated: pd.DataFrame, *, contract: Mapping[str, Any]
) -> pd.DataFrame:
    """Validate the nullable V1c exact field, then persist only its identified set."""
    specification = contract["evaluated_portfolios"]
    required = {
        "realized_payoff_exact",
        "realized_payoff_lower",
        "realized_payoff_upper",
        "n_unresolved_positive_exposure",
    }
    missing = sorted(required - set(evaluated.columns))
    if missing:
        raise RuntimeError(f"V1d evaluated input is missing repair columns: {missing}.")
    if len(evaluated.columns) != int(specification["source_columns"]):
        raise RuntimeError("V1d evaluated source no longer has the locked 50-column schema.")
    if list(specification["drop_columns"]) != ["realized_payoff_exact"] or list(
        specification["retained_identified_set"]
    ) != ["realized_payoff_lower", "realized_payoff_upper"]:
        raise RuntimeError("V1d persistence repair no longer drops only the exact payoff field.")

    exact = _reject_coercible_numeric_values(
        evaluated["realized_payoff_exact"], label="realized_payoff_exact"
    )
    lower = _reject_coercible_numeric_values(
        evaluated["realized_payoff_lower"], label="realized_payoff_lower"
    )
    upper = _reject_coercible_numeric_values(
        evaluated["realized_payoff_upper"], label="realized_payoff_upper"
    )
    unresolved_count = _reject_coercible_numeric_values(
        evaluated["n_unresolved_positive_exposure"],
        label="n_unresolved_positive_exposure",
    )
    exact_values = exact.to_numpy(dtype=float, na_value=np.nan)
    lower_values = lower.to_numpy(dtype=float, na_value=np.nan)
    upper_values = upper.to_numpy(dtype=float, na_value=np.nan)
    unresolved_values = unresolved_count.to_numpy(dtype=float, na_value=np.nan)
    if (
        not bool(np.isfinite(lower_values).all())
        or not bool(np.isfinite(upper_values).all())
        or not bool(np.isfinite(unresolved_values).all())
        or bool((unresolved_values < 0.0).any())
        or bool((lower_values > upper_values).any())
    ):
        raise RuntimeError("V1d payoff bounds/counts are non-finite, negative, or reversed.")
    exact_missing = np.isnan(exact_values)
    unresolved = unresolved_values > 0.0
    if not np.array_equal(exact_missing, unresolved):
        raise RuntimeError(
            "realized_payoff_exact missingness is not exactly unresolved positive exposure."
        )
    if int(exact_missing.sum()) != int(specification["exact_missing_rows_observed_in_v1c"]):
        raise RuntimeError("V1d exact-payoff missing-row census changed from the locked NO-GO.")
    if int((~exact_missing).sum()) != int(specification["exact_resolved_rows_observed_in_v1c"]):
        raise RuntimeError("V1d exact-payoff resolved-row census changed from the locked NO-GO.")
    resolved = ~exact_missing
    if (
        not bool(np.isfinite(exact_values[resolved]).all())
        or not np.array_equal(exact_values[resolved], lower_values[resolved])
        or not np.array_equal(exact_values[resolved], upper_values[resolved])
    ):
        raise RuntimeError("A resolved exact payoff does not equal both identified-set endpoints.")
    if not bool((upper_values[unresolved] > lower_values[unresolved]).all()):
        raise RuntimeError("An unresolved exact payoff does not retain a noncollapsed interval.")

    persisted = evaluated.drop(columns=["realized_payoff_exact"]).copy()
    if len(persisted.columns) != int(specification["persisted_columns"]):
        raise RuntimeError("V1d evaluated persistence schema is not exactly 49 columns.")
    return persisted


def prepare_v1d_window_sharp_contrasts(
    window: pd.DataFrame, *, contract: Mapping[str, Any]
) -> pd.DataFrame:
    """Remove the all-null pooled period field; pooled scope has no single month."""
    specification = contract["pooled_window_contrasts"]
    if len(window.columns) != int(specification["source_columns"]):
        raise RuntimeError("V1d pooled-window source no longer has its locked 40 columns.")
    if list(specification["drop_columns"]) != ["period"] or "period" not in window:
        raise RuntimeError("V1d pooled-window repair no longer drops only period.")
    missing = window["period"].isna()
    if int(missing.sum()) != int(
        specification["source_period_missing_rows_observed_in_v1c"]
    ) or not bool(missing.all()):
        raise RuntimeError("V1d pooled-window period is not the locked all-missing field.")
    if "scope" not in window or set(window["scope"].astype(str)) != {"pooled_primary_window"}:
        raise RuntimeError("V1d pooled-window rows do not retain their pooled scope semantics.")
    persisted = window.drop(columns=["period"]).copy()
    if len(persisted.columns) != int(specification["persisted_columns"]):
        raise RuntimeError("V1d pooled-window persistence schema is not exactly 39 columns.")
    return persisted


def _validate_evaluated_numeric_finiteness(
    frame: pd.DataFrame, *, contract: Mapping[str, Any]
) -> None:
    if "realized_payoff_exact" in frame:
        raise RuntimeError("V1d persisted evaluated table still contains realized_payoff_exact.")
    required = {"frontier_ruler", *STRUCTURAL_NULL_RULES}
    if not required.issubset(frame):
        raise RuntimeError("V1d evaluated table omits its ruler-structural null contract.")
    ruler = frame["frontier_ruler"].astype(str)
    if set(ruler) != {"objective_matched", "normalized_score"}:
        raise RuntimeError("V1d evaluated table has an unknown or incomplete ruler census.")
    expected_missing = int(contract["numeric_finiteness"]["expected_missing_each"])
    for column, missing_ruler in STRUCTURAL_NULL_RULES.items():
        original = frame[column]
        nonmissing = original.notna()
        invalid_type = original.loc[nonmissing].map(
            lambda value: isinstance(value, (str, bytes, bool, np.bool_))
        )
        if bool(invalid_type.any()):
            raise RuntimeError(f"V1d {column} contains a string/boolean structural value.")
        numeric = _reject_coercible_numeric_values(original, label=column)
        values = numeric.to_numpy(dtype=float, na_value=np.nan)
        expected_mask = ruler.eq(missing_ruler).to_numpy(dtype=bool)
        observed_mask = original.isna().to_numpy(dtype=bool)
        if int(observed_mask.sum()) != expected_missing or not np.array_equal(
            observed_mask, expected_mask
        ):
            raise RuntimeError(f"V1d {column} violates its exact ruler-structural NA pattern.")
        if not bool(np.isfinite(values[~expected_mask]).all()):
            raise RuntimeError(f"V1d {column} contains a non-finite applicable value.")
    _validate_locked_schema(frame, key="evaluated_portfolios", contract=contract)
    numeric_columns = [
        name
        for name, dtype in PERSISTED_SCHEMA_DTYPES["evaluated_portfolios"]
        if dtype in NUMERIC_DTYPE_NAMES and name not in STRUCTURAL_NULL_RULES
    ]
    numeric = frame.loc[:, numeric_columns]
    if not bool(np.isfinite(_numeric_array(numeric)).all()):
        raise RuntimeError("V1d evaluated table contains an undeclared non-finite numeric value.")
    allowed_missing = frame.loc[:, list(STRUCTURAL_NULL_RULES)].isna().sum().sum()
    if int(frame.isna().sum().sum()) != int(allowed_missing):
        raise RuntimeError("V1d evaluated table contains undeclared nonnumeric missingness.")


def validate_v1d_persisted_numeric_finiteness(
    frames: Mapping[str, pd.DataFrame], *, contract: Mapping[str, Any]
) -> None:
    """Require finite numeric outputs except the exact three-field ruler pattern."""
    if set(frames) != set(PERSISTED_FRAME_KEYS):
        raise RuntimeError("V1d persisted-frame census is not exactly the five parquet outputs.")
    _validate_evaluated_numeric_finiteness(frames["evaluated_portfolios"], contract=contract)
    for key in PERSISTED_FRAME_KEYS[1:]:
        frame = frames[key]
        _validate_locked_schema(frame, key=key, contract=contract)
        if bool(frame.isna().any(axis=None)):
            raise RuntimeError(f"V1d {key} contains an undeclared persisted missing value.")
        numeric_columns = [
            name for name, dtype in PERSISTED_SCHEMA_DTYPES[key] if dtype in NUMERIC_DTYPE_NAMES
        ]
        numeric = frame.loc[:, numeric_columns]
        if not bool(np.isfinite(_numeric_array(numeric)).all()):
            raise RuntimeError(f"V1d {key} contains a non-finite persisted numeric value.")
