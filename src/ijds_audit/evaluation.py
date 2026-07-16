"""Post-freeze archive evaluation, coverage transport, and comparator envelopes."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from typing import Any, cast

import numpy as np
import pandas as pd

from src.evaluation.coverage_transport import binary_miscoverage_bounds
from src.evaluation.maturity_safe_portfolio import (
    aggregate_monthly_evaluation,
    evaluate_prejoined_frozen_allocation,
)
from src.evaluation.policy_contrast_bounds import PolicyContrastIndex
from src.ijds_audit.geometry import summarize_binary_geometry
from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    apply_binary_outcome_recipe,
)

EVALUATION_ROLES = ("conformal_fit", "policy_development", "primary_oot", "censored_extension")

_EXPECTED_ROLE = "__expected_role"
_EXPECTED_PERIOD = "__expected_period"
_OUTCOME_ROLE = "__outcome_role"
_OUTCOME_PERIOD = "__outcome_period"
_OUTCOME_JOIN = "__outcome_join"

RESOLUTION_FULLY_PAID_BY_CUTOFF = "fully_paid_by_reconstructed_cutoff"
RESOLUTION_CHARGED_OFF_BY_CUTOFF = "charged_off_by_reconstructed_cutoff"
RESOLUTION_TERMINAL_DATE_MISSING = "terminal_availability_date_missing"
RESOLUTION_TERMINAL_AFTER_CUTOFF = "terminal_after_reconstructed_cutoff"
RESOLUTION_NONTERMINAL = "nonterminal_or_unresolved_status"


def _outcome_payload(
    outcomes: pd.DataFrame,
    *,
    value_columns: Sequence[str],
) -> pd.DataFrame:
    required = {"id", *value_columns}
    missing = sorted(required - set(outcomes.columns))
    if missing:
        raise KeyError(f"Outcome census is missing required columns: {missing}.")
    if bool(outcomes["id"].isna().any()):
        raise RuntimeError("The outcome census contains missing IDs.")
    duplicate_ids = outcomes.loc[outcomes["id"].duplicated(keep=False), "id"]
    if not duplicate_ids.empty:
        sample = duplicate_ids.astype(str).drop_duplicates().head(5).tolist()
        raise RuntimeError(f"The outcome census contains duplicate IDs: {sample}.")

    columns = ["id", *value_columns]
    rename: dict[str, str] = {}
    if "role" in outcomes.columns:
        columns.append("role")
        rename["role"] = _OUTCOME_ROLE
    if "period" in outcomes.columns:
        columns.append("period")
        rename["period"] = _OUTCOME_PERIOD
    return outcomes.loc[:, columns].rename(columns=rename)


def _with_expected_outcome_metadata(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    if "role" in result.columns:
        result[_EXPECTED_ROLE] = result["role"].astype("string")
    elif "design_split" in result.columns:
        result[_EXPECTED_ROLE] = result["design_split"].astype("string")

    if "period" in result.columns:
        result[_EXPECTED_PERIOD] = result["period"].astype("string")
    elif "issue_d" in result.columns:
        issue_date = pd.to_datetime(result["issue_d"], errors="coerce")
        if bool(issue_date.isna().any()):
            raise RuntimeError("The expected outcome census contains an invalid issue date.")
        result[_EXPECTED_PERIOD] = issue_date.dt.to_period("M").astype("string")
    return result


def _validate_outcome_metadata(joined: pd.DataFrame) -> None:
    comparisons = (
        ("role", _EXPECTED_ROLE, _OUTCOME_ROLE),
        ("period", _EXPECTED_PERIOD, _OUTCOME_PERIOD),
    )
    for label, expected_column, outcome_column in comparisons:
        if expected_column not in joined.columns or outcome_column not in joined.columns:
            continue
        expected = joined[expected_column].astype("string")
        observed = joined[outcome_column].astype("string")
        mismatch = expected.isna() | observed.isna() | expected.ne(observed).fillna(True)
        if bool(mismatch.any()):
            sample = joined.loc[mismatch, "id"].astype(str).head(5).tolist()
            raise RuntimeError(f"Outcome {label} disagrees with the frozen census: {sample}.")


def _drop_outcome_join_helpers(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.drop(
        columns=[
            _EXPECTED_ROLE,
            _EXPECTED_PERIOD,
            _OUTCOME_ROLE,
            _OUTCOME_PERIOD,
            _OUTCOME_JOIN,
        ],
        errors="ignore",
    )


def _scoped_outcome_payload(
    expected: pd.DataFrame,
    payload: pd.DataFrame,
) -> pd.DataFrame:
    expected_ids = expected["id"]
    metadata_scope = np.zeros(len(payload), dtype=bool)
    metadata_pairs = (
        (_EXPECTED_ROLE, _OUTCOME_ROLE),
        (_EXPECTED_PERIOD, _OUTCOME_PERIOD),
    )
    available_pairs = [
        (expected_column, outcome_column)
        for expected_column, outcome_column in metadata_pairs
        if expected_column in expected.columns and outcome_column in payload.columns
    ]
    if len(available_pairs) == 2:
        expected_keys = pd.MultiIndex.from_frame(
            expected[[column for column, _ in available_pairs]].drop_duplicates()
        )
        outcome_keys = pd.MultiIndex.from_frame(payload[[column for _, column in available_pairs]])
        metadata_scope = outcome_keys.isin(expected_keys)
    elif len(available_pairs) == 1:
        expected_column, outcome_column = available_pairs[0]
        metadata_scope = payload[outcome_column].isin(expected[expected_column])
    return payload.loc[payload["id"].isin(expected_ids) | metadata_scope].copy()


def _exact_outcome_join(
    expected: pd.DataFrame,
    outcomes: pd.DataFrame,
    *,
    value_columns: Sequence[str],
) -> pd.DataFrame:
    census = _with_expected_outcome_metadata(expected)
    if bool(census["id"].isna().any()):
        raise RuntimeError("The frozen census contains missing IDs.")
    if bool(census["id"].duplicated().any()):
        raise RuntimeError("The frozen census contains duplicate IDs.")
    payload = _scoped_outcome_payload(
        census,
        _outcome_payload(outcomes, value_columns=value_columns),
    )
    joined = census.merge(
        payload,
        on="id",
        how="outer",
        validate="one_to_one",
        indicator=_OUTCOME_JOIN,
        sort=False,
    )
    missing = int(joined[_OUTCOME_JOIN].eq("left_only").sum())
    extra = int(joined[_OUTCOME_JOIN].eq("right_only").sum())
    if missing or extra:
        raise RuntimeError(f"Outcome ID census mismatch: missing={missing}, extra={extra}.")
    _validate_outcome_metadata(joined)
    return _drop_outcome_join_helpers(joined)


def _validate_portfolio_candidate_census(
    records: pd.DataFrame,
    outcomes: pd.DataFrame,
) -> None:
    required = {"role", "period", "n_candidates"}
    missing = sorted(required - set(records.columns))
    if missing:
        raise KeyError(f"Solve records are missing candidate census columns: {missing}.")
    if not {"role", "period"}.issubset(outcomes.columns):
        raise KeyError("Portfolio outcomes must contain role and period columns.")

    expected = records.loc[:, ["role", "period", "n_candidates"]].copy()
    expected["role"] = expected["role"].astype("string")
    expected["period"] = expected["period"].astype("string")
    candidate_counts = pd.to_numeric(expected["n_candidates"], errors="raise")
    candidate_values = candidate_counts.to_numpy(dtype=float)
    if (
        not bool(np.isfinite(candidate_values).all())
        or bool((candidate_values < 0).any())
        or not bool(np.equal(candidate_values, np.floor(candidate_values)).all())
    ):
        raise RuntimeError("Solve records contain an invalid candidate census.")
    expected["expected_candidates"] = candidate_counts.astype("int64")
    conflicts = expected.groupby(["role", "period"], observed=True)["expected_candidates"].nunique(
        dropna=False
    )
    if bool(conflicts.gt(1).any()):
        raise RuntimeError("Solve records disagree on the role/period candidate census.")
    expected = expected[["role", "period", "expected_candidates"]].drop_duplicates()

    evaluated_roles = expected["role"].drop_duplicates()
    actual = outcomes.loc[
        outcomes["role"].astype("string").isin(evaluated_roles), ["role", "period", "id"]
    ].copy()
    actual["role"] = actual["role"].astype("string")
    actual["period"] = actual["period"].astype("string")
    actual = (
        actual.groupby(["role", "period"], observed=True, sort=False)
        .size()
        .rename("actual_candidates")
        .reset_index()
    )
    comparison = expected.merge(
        actual,
        on=["role", "period"],
        how="outer",
        validate="one_to_one",
        indicator="__candidate_census_join",
    )
    expected_count = comparison["expected_candidates"].fillna(0).to_numpy(dtype=np.int64)
    actual_count = comparison["actual_candidates"].fillna(0).to_numpy(dtype=np.int64)
    missing_count = int(np.maximum(expected_count - actual_count, 0).sum())
    extra_count = int(np.maximum(actual_count - expected_count, 0).sum())
    if missing_count or extra_count:
        raise RuntimeError(
            f"Portfolio outcome ID census mismatch: missing={missing_count}, extra={extra_count}."
        )


def build_archive_outcomes(
    universe: pd.DataFrame,
    *,
    evaluation_cutoff: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Materialize the nullable endpoint panel kept outside policy construction.

    When ``evaluation_cutoff`` is supplied, a terminal status is retained only
    when its conservative ``label_available_at`` date is no later than that
    cutoff. This reconstructs an as-of endpoint from the distributed archive;
    it does not pretend that the archive itself is a point-in-time snapshot.
    """
    archive_terminal = universe["terminal_default"].astype("Int8")
    available_at = pd.to_datetime(
        universe.get("label_available_at", pd.Series(pd.NaT, index=universe.index)),
        errors="coerce",
    )
    terminal = archive_terminal.copy()
    observed_by_cutoff = archive_terminal.notna()
    resolution = pd.Series("right_censored", index=universe.index, dtype="string")
    if evaluation_cutoff is not None:
        cutoff = pd.Timestamp(evaluation_cutoff)
        if pd.isna(cutoff):
            raise ValueError("Evaluation cutoff must be a valid timestamp.")
        observed_by_cutoff &= available_at.notna() & available_at.le(cutoff)
        terminal = archive_terminal.where(observed_by_cutoff).astype("Int8")
        terminal_missing_date = archive_terminal.notna() & available_at.isna()
        terminal_after_cutoff = (
            archive_terminal.notna() & available_at.notna() & available_at.gt(cutoff)
        )
        resolution[:] = RESOLUTION_NONTERMINAL
        resolution.loc[terminal.eq(0).fillna(False)] = RESOLUTION_FULLY_PAID_BY_CUTOFF
        resolution.loc[terminal.eq(1).fillna(False)] = RESOLUTION_CHARGED_OFF_BY_CUTOFF
        resolution.loc[terminal_missing_date] = RESOLUTION_TERMINAL_DATE_MISSING
        resolution.loc[terminal_after_cutoff] = RESOLUTION_TERMINAL_AFTER_CUTOFF
    else:
        resolution.loc[terminal.eq(0).fillna(False)] = "fully_paid"
        resolution.loc[terminal.eq(1).fillna(False)] = "charged_off"
    return pd.DataFrame(
        {
            "id": universe["id"].astype("string"),
            "snapshot_default": terminal,
            "snapshot_resolution": resolution,
            "outcome_available_at": available_at,
            "role": universe["design_split"].astype("string"),
            "period": pd.to_datetime(universe["issue_d"]).dt.to_period("M").astype(str),
        }
    )


def endpoint_resolution_audit(
    outcomes: pd.DataFrame,
    *,
    roles: Collection[str] | None = None,
) -> pd.DataFrame:
    """Count resolved and unresolved candidates by explicit endpoint reason."""
    required = {"id", "role", "snapshot_default", "snapshot_resolution"}
    missing = sorted(required.difference(outcomes.columns))
    if missing:
        raise KeyError(f"Endpoint audit is missing required columns: {missing}.")
    selected = outcomes.copy()
    if roles is not None:
        selected = selected.loc[selected["role"].astype(str).isin(map(str, roles))].copy()
    if selected.empty:
        raise ValueError("Endpoint audit received no candidate rows.")
    selected["resolved"] = selected["snapshot_default"].notna()
    audit = (
        selected.groupby(["role", "snapshot_resolution"], observed=True, sort=True)
        .agg(candidate_rows=("id", "size"), resolved_rows=("resolved", "sum"))
        .reset_index()
    )
    audit["resolved_rows"] = audit["resolved_rows"].astype("int64")
    audit["unresolved_rows"] = audit["candidate_rows"] - audit["resolved_rows"]
    if int(audit["candidate_rows"].sum()) != len(selected):
        raise RuntimeError("Endpoint reason taxonomy does not partition the candidate census.")
    return audit


def evaluate_frozen_portfolios(
    records: pd.DataFrame,
    allocations: pd.DataFrame,
    outcomes: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Perform one validated outcome join and evaluate every frozen allocation."""
    keys = ["window_id", "role", "period", "policy_label", "comparator_rule"]
    record_index = records.set_index(keys)
    if not record_index.index.is_unique:
        raise ValueError("Solve records contain duplicate evaluation keys.")
    outcome_payload = _outcome_payload(
        outcomes,
        value_columns=("snapshot_default", "snapshot_resolution"),
    )
    join_source = _with_expected_outcome_metadata(allocations)
    joined = join_source.merge(
        outcome_payload,
        on="id",
        how="left",
        validate="many_to_one",
        indicator=_OUTCOME_JOIN,
        sort=False,
    )
    missing_funded = int(joined[_OUTCOME_JOIN].eq("left_only").sum())
    if missing_funded:
        raise RuntimeError(f"Funded outcome ID census mismatch: missing={missing_funded}.")
    _validate_outcome_metadata(joined)
    joined = _drop_outcome_join_helpers(joined)
    _validate_portfolio_candidate_census(records, outcomes)
    candidate_unresolved = outcomes.groupby(["role", "period"], observed=True)[
        "snapshot_default"
    ].apply(lambda values: int(values.isna().sum()))
    if len(joined) != len(allocations) or bool(joined["snapshot_resolution"].isna().any()):
        raise RuntimeError("The shared outcome join did not preserve every funded row.")
    evaluated: list[dict[str, Any]] = []
    joined_groups: list[pd.DataFrame] = []
    grouped = joined.groupby(keys, observed=True, sort=True, dropna=False)
    if grouped.ngroups != len(record_index):
        raise RuntimeError("Solve records and allocation groups have different cardinality.")
    for raw_keys, allocation in grouped:
        key_values = raw_keys if isinstance(raw_keys, tuple) else (raw_keys,)
        base = record_index.loc[key_values]
        if isinstance(base, pd.DataFrame):
            raise RuntimeError(f"Solve-record key is not unique: {key_values}.")
        record = base.to_dict()
        record.update(dict(zip(keys, key_values, strict=True)))
        unresolved_key = (str(record["role"]), str(record["period"]))
        if unresolved_key not in candidate_unresolved.index:
            raise RuntimeError(f"Candidate outcome count is unavailable for {unresolved_key}.")
        result, funded = evaluate_prejoined_frozen_allocation(
            record,
            allocation,
            config=config,
            n_unresolved_candidates=int(candidate_unresolved.loc[unresolved_key]),
        )
        evaluated.append(result)
        joined_groups.append(funded)
    return pd.DataFrame(evaluated), pd.concat(joined_groups, ignore_index=True)


def aggregate_portfolios(evaluated: pd.DataFrame) -> pd.DataFrame:
    """Aggregate monthly cells without treating months or scopes as replications."""
    keys = ["window_id", "role", "policy_label", "comparator_rule", "paired_policy_id"]
    rows: list[dict[str, Any]] = []
    for raw_keys, frame in evaluated.groupby(keys, observed=True, sort=True, dropna=False):
        key_values = raw_keys if isinstance(raw_keys, tuple) else (raw_keys,)
        row = aggregate_monthly_evaluation(frame)
        row.update(dict(zip(keys, key_values, strict=True)))
        cap = pd.to_numeric(frame["frontier_cap"], errors="coerce")
        row["frontier_cap"] = float(cap.dropna().iloc[0]) if bool(cap.notna().any()) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def indexed_portfolio_contrasts(
    allocations: pd.DataFrame,
    *,
    loan_facts: pd.DataFrame | None,
    window_id: str,
    policy_ids: tuple[str, ...],
    lgd: float,
) -> pd.DataFrame:
    """Compute one window's contrast grid from one validated sparse index."""
    primary = allocations.loc[allocations["role"].eq("primary_oot")]
    observed_windows = set(primary["window_id"].astype(str))
    if observed_windows != {str(window_id)}:
        raise RuntimeError(
            f"Indexed contrast window mismatch: expected={window_id!r}, "
            f"observed={sorted(observed_windows)}."
        )
    index = PolicyContrastIndex(primary, role="primary_oot", loan_facts=loan_facts)
    frontier = primary.loc[
        primary["comparator_rule"].eq("point_cap_frontier"),
        ["policy_label", "frontier_cap"],
    ].drop_duplicates()
    duplicate_frontier = frontier["policy_label"].duplicated(keep=False)
    if bool(duplicate_frontier.any()):
        raise RuntimeError("A frontier policy label maps to conflicting cap values.")
    frontier = frontier.sort_values("frontier_cap")

    rows: list[dict[str, Any]] = []
    for policy_id in policy_ids:
        guard_label = f"guardrail_{policy_id}"
        named = (
            ("c0_same_numeric_cap", f"c0_same_numeric_cap_{policy_id}"),
            ("c1_development_mean", f"c1_development_mean_{policy_id}"),
            ("c2_contemporaneous", f"c2_contemporaneous_{policy_id}"),
        )
        for rule, comparator_label in named:
            cap = primary.loc[primary["policy_label"].eq(comparator_label), "frontier_cap"]
            if cap.empty:
                raise RuntimeError(f"Named comparator {comparator_label!r} is missing.")
            cap_values = pd.to_numeric(cap, errors="raise").drop_duplicates()
            if rule != "c2_contemporaneous" and len(cap_values) != 1:
                raise RuntimeError(
                    f"Named comparator {comparator_label!r} maps to conflicting cap values."
                )
            rows.append(
                {
                    "window_id": str(window_id),
                    "paired_policy_id": policy_id,
                    "comparator_rule": rule,
                    # C2 is matched monthly; the retained scalar is legacy metadata.
                    "frontier_cap": float(pd.to_numeric(cap, errors="raise").iloc[0]),
                    **index.sharp_bounds(
                        policy_a=guard_label,
                        policy_b=comparator_label,
                        lgd=float(lgd),
                    ),
                }
            )
        for item in frontier.itertuples(index=False):
            comparator_label = str(item.policy_label)
            rows.append(
                {
                    "window_id": str(window_id),
                    "paired_policy_id": policy_id,
                    "comparator_rule": "point_cap_frontier",
                    "frontier_cap": float(item.frontier_cap),
                    **index.sharp_bounds(
                        policy_a=guard_label,
                        policy_b=comparator_label,
                        lgd=float(lgd),
                    ),
                }
            )
    return pd.DataFrame(rows)


def paired_portfolio_contrasts(
    joined_allocations: pd.DataFrame,
    *,
    policy_ids: tuple[str, ...],
    lgd: float,
) -> pd.DataFrame:
    """Compute guardrail-minus-point bounds while indexing each window once."""
    frames = [
        indexed_portfolio_contrasts(
            window,
            loan_facts=None,
            window_id=str(window_id),
            policy_ids=policy_ids,
            lgd=lgd,
        )
        for window_id, window in joined_allocations.groupby("window_id", observed=True, sort=True)
    ]
    if not frames:
        raise ValueError("No allocation windows are available for policy contrasts.")
    return pd.concat(frames, ignore_index=True)


def comparator_envelopes(
    contrasts: pd.DataFrame,
    support: pd.DataFrame,
    *,
    broad_lower: float,
    broad_upper: float,
) -> pd.DataFrame:
    """Summarize one interval per policy, metric, window, and named comparator scope."""
    metrics = {
        "standardized_payoff": (
            "realized_payoff_difference_lower",
            "realized_payoff_difference_upper",
        ),
        "terminal_default": (
            "weighted_default_difference_lower",
            "weighted_default_difference_upper",
        ),
        "funded_miscoverage": (
            "weighted_miscoverage_difference_lower",
            "weighted_miscoverage_difference_upper",
        ),
    }
    rows: list[dict[str, Any]] = []
    support_index = support.set_index(["window_id", "paired_policy_id"])
    if not support_index.index.is_unique:
        raise ValueError("Comparator support contains duplicate policy-window keys.")
    for raw_keys, frame in contrasts.groupby(
        ["window_id", "paired_policy_id"], observed=True, sort=True
    ):
        key_values = raw_keys if isinstance(raw_keys, tuple) else (raw_keys,)
        if len(key_values) != 2:
            raise RuntimeError("Comparator-envelope key has unexpected cardinality.")
        window_id, policy_id = key_values
        limits = support_index.loc[(window_id, policy_id)]
        scopes = {
            "named_c0_c1_c2": frame.loc[
                frame["comparator_rule"].isin(
                    ["c0_same_numeric_cap", "c1_development_mean", "c2_contemporaneous"]
                )
            ],
            "development_admissible_exact_frontier": frame.loc[
                frame["comparator_rule"].eq("point_cap_frontier")
                & frame["frontier_cap"].between(
                    float(limits["support_lower"]),
                    float(limits["support_upper"]),
                    inclusive="both",
                )
            ],
            "broad_stress_exact_frontier": frame.loc[
                frame["comparator_rule"].eq("point_cap_frontier")
                & frame["frontier_cap"].between(
                    float(broad_lower), float(broad_upper), inclusive="both"
                )
            ],
        }
        for scope, scoped in scopes.items():
            if scoped.empty:
                raise RuntimeError(
                    f"Comparator scope {scope} is empty for {window_id}/{policy_id}."
                )
            for metric, (lower, upper) in metrics.items():
                lower_value = float(scoped[lower].min())
                upper_value = float(scoped[upper].max())
                rows.append(
                    {
                        "window_id": str(window_id),
                        "paired_policy_id": str(policy_id),
                        "scope": scope,
                        "metric": metric,
                        "lower": lower_value,
                        "upper": upper_value,
                        "direction": (
                            "guardrail_higher"
                            if lower_value > 0.0
                            else "guardrail_lower"
                            if upper_value < 0.0
                            else "crosses_zero"
                        ),
                        "evaluated_comparators": int(len(scoped)),
                        "nested_scope_independent_replications": False,
                    }
                )
    return pd.DataFrame(rows)


def temporal_coverage_audit(
    scores: pd.DataFrame,
    outcomes: pd.DataFrame,
    recipes: Mapping[str, Mapping[str, Mapping[int, BinaryOutcomeConformalRecipe]]],
    fit_audit: pd.DataFrame,
    *,
    roles: Sequence[str] = EVALUATION_ROLES,
    taxonomy_group_counts: Collection[int] | None = None,
    strata: Collection[int] | None = None,
) -> pd.DataFrame:
    """Evaluate all learner/window/taxonomy/role/stratum coverage cells."""
    requested_roles = frozenset(str(role) for role in roles)
    score_role = "role" if "role" in scores.columns else "design_split"
    selected_scores = scores.loc[scores[score_role].astype(str).isin(requested_roles)].copy()
    joined = _exact_outcome_join(
        selected_scores,
        outcomes,
        value_columns=("snapshot_default",),
    )
    fit_lookup: dict[tuple[str, str, int], pd.DataFrame] = {}
    for raw_key, frame in fit_audit.groupby(
        ["learner", "window_id", "taxonomy_groups"],
        observed=True,
        sort=False,
    ):
        learner, window_id, taxonomy_groups = cast(tuple[Any, Any, Any], raw_key)
        fit_lookup[(str(learner), str(window_id), int(taxonomy_groups))] = frame
    rows: list[dict[str, Any]] = []
    selected_taxonomies = (
        None
        if taxonomy_group_counts is None
        else frozenset(int(value) for value in taxonomy_group_counts)
    )
    for learner, learner_windows in recipes.items():
        probability = joined[f"pd_{learner}"].to_numpy(dtype=float)
        for window_id, group_recipes in learner_windows.items():
            for taxonomy_groups, recipe in sorted(group_recipes.items()):
                if selected_taxonomies is not None and taxonomy_groups not in selected_taxonomies:
                    continue
                assigned, lower, upper = apply_binary_outcome_recipe(probability, recipe)
                selected_strata = (
                    (-1, *range(int(taxonomy_groups)))
                    if strata is None
                    else tuple(int(value) for value in strata)
                )
                invalid_strata = [
                    value for value in selected_strata if value < -1 or value >= taxonomy_groups
                ]
                if invalid_strata:
                    raise ValueError(
                        f"Invalid strata for {taxonomy_groups} groups: {invalid_strata}."
                    )
                for role in roles:
                    role_mask = joined["design_split"].eq(role).to_numpy(dtype=bool)
                    for stratum in selected_strata:
                        mask = role_mask & ((assigned == stratum) if stratum >= 0 else True)
                        if not bool(mask.any()):
                            raise RuntimeError(
                                f"Empty coverage cell: {learner}/{window_id}/{role}/{stratum}."
                            )
                        outcome = pd.to_numeric(
                            joined.loc[mask, "snapshot_default"], errors="coerce"
                        ).to_numpy(dtype=float)
                        observed = np.isfinite(outcome)
                        miss_low, miss_high = binary_miscoverage_bounds(
                            outcome,
                            lower[mask],
                            upper[mask],
                        )
                        n = int(mask.sum())
                        geometry = summarize_binary_geometry(lower[mask], upper[mask])
                        fitted_base = fit_lookup.get(
                            (str(learner), str(window_id), int(taxonomy_groups))
                        )
                        if fitted_base is None:
                            raise RuntimeError(
                                f"Missing fit audit: {learner}/{window_id}/{taxonomy_groups}."
                            )
                        fitted = (
                            fitted_base.loc[fitted_base["conformal_group"].eq(stratum)]
                            if stratum >= 0
                            else fitted_base
                        )
                        if fitted.empty:
                            raise RuntimeError(
                                f"Missing fit audit: {learner}/{window_id}/{taxonomy_groups}/{stratum}."
                            )
                        fit_min = float(fitted["pd_point"].min())
                        fit_max = float(fitted["pd_point"].max())
                        if stratum >= 0:
                            residual_quantile = float(recipe.residual_quantiles[stratum])
                        else:
                            residual = np.sort(
                                np.abs(
                                    fitted["terminal_default"].to_numpy(dtype=float)
                                    - fitted["pd_point"].to_numpy(dtype=float)
                                )
                            )
                            raw_rank = int(np.ceil((len(residual) + 1) * (1.0 - recipe.alpha)))
                            residual_quantile = (
                                1.0 if raw_rank > len(residual) else float(residual[raw_rank - 1])
                            )
                        rows.append(
                            {
                                "learner": learner,
                                "window_id": window_id,
                                "taxonomy_groups": int(taxonomy_groups),
                                "role": role,
                                "conformal_group": int(stratum),
                                "candidate_rows": n,
                                "resolved_rows": int(observed.sum()),
                                "unresolved_rows": int((~observed).sum()),
                                "coverage_resolved": float(1.0 - miss_low[observed].mean()),
                                "coverage_lower": float(1.0 - miss_high.mean()),
                                "coverage_upper": float(1.0 - miss_low.mean()),
                                "score_min": float(np.min(probability[mask])),
                                "score_max": float(np.max(probability[mask])),
                                "fit_rows": int(len(fitted)),
                                "fit_prevalence": float(fitted["terminal_default"].mean()),
                                "fit_residual_quantile": residual_quantile,
                                "fit_score_min": fit_min,
                                "fit_score_max": fit_max,
                                "scores_below_fit_range": int(
                                    np.sum(probability[mask] < fit_min - 1e-12)
                                ),
                                "scores_above_fit_range": int(
                                    np.sum(probability[mask] > fit_max + 1e-12)
                                ),
                                **geometry,
                            }
                        )
    return pd.DataFrame(rows)
