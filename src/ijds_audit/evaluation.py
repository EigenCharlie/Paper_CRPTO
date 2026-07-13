"""Post-freeze archive evaluation, coverage transport, and comparator envelopes."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from typing import Any, cast

import numpy as np
import pandas as pd

from src.evaluation.maturity_safe_portfolio import (
    aggregate_monthly_evaluation,
    evaluate_prejoined_frozen_allocation,
)
from src.evaluation.policy_contrast_bounds import sharp_policy_contrast_bounds
from src.ijds_audit.geometry import summarize_binary_geometry
from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    apply_binary_outcome_recipe,
)

EVALUATION_ROLES = ("conformal_fit", "policy_development", "primary_oot", "censored_extension")


def build_archive_outcomes(universe: pd.DataFrame) -> pd.DataFrame:
    """Materialize the terminal-outcome panel kept outside policy construction."""
    terminal = universe["terminal_default"].astype("Int8")
    resolution = pd.Series("right_censored", index=universe.index, dtype="string")
    resolution.loc[terminal.eq(0).fillna(False)] = "fully_paid"
    resolution.loc[terminal.eq(1).fillna(False)] = "charged_off"
    return pd.DataFrame(
        {
            "id": universe["id"].astype("string"),
            "snapshot_default": terminal,
            "snapshot_resolution": resolution,
            "role": universe["design_split"].astype("string"),
            "period": pd.to_datetime(universe["issue_d"]).dt.to_period("M").astype(str),
        }
    )


def evaluate_frozen_portfolios(
    records: pd.DataFrame,
    allocations: pd.DataFrame,
    outcomes: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Perform one validated outcome join and evaluate every frozen allocation."""
    keys = ["window_id", "role", "period", "policy_label", "comparator_rule"]
    record_index = records.set_index(keys, verify_integrity=True)
    candidate_unresolved = outcomes.groupby(["role", "period"], observed=True)[
        "snapshot_default"
    ].apply(lambda values: int(values.isna().sum()))
    joined = allocations.merge(
        outcomes[["id", "snapshot_default", "snapshot_resolution"]],
        on="id",
        how="left",
        validate="many_to_one",
    )
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


def paired_portfolio_contrasts(
    joined_allocations: pd.DataFrame,
    *,
    policy_ids: tuple[str, ...],
    lgd: float,
) -> pd.DataFrame:
    """Compute guardrail-minus-point sharp bounds for named and frontier comparators."""
    rows: list[dict[str, Any]] = []
    for window_id, window in joined_allocations.groupby("window_id", observed=True, sort=True):
        primary = window.loc[window["role"].eq("primary_oot")]
        allocations_by_label = {
            str(label): frame
            for label, frame in primary.groupby("policy_label", observed=True, sort=False)
        }
        frontier = (
            primary.loc[
                primary["comparator_rule"].eq("point_cap_frontier"),
                [
                    "policy_label",
                    "frontier_cap",
                ],
            ]
            .drop_duplicates()
            .sort_values("frontier_cap")
        )
        for policy_id in policy_ids:
            guard_label = f"guardrail_{policy_id}"
            guard = allocations_by_label[guard_label]
            named = (
                ("c0_same_numeric_cap", f"c0_same_numeric_cap_{policy_id}"),
                ("c1_development_mean", f"c1_development_mean_{policy_id}"),
                ("c2_contemporaneous", f"c2_contemporaneous_{policy_id}"),
            )
            for rule, comparator_label in named:
                pair = pd.concat([guard, allocations_by_label[comparator_label]], ignore_index=True)
                bounds = sharp_policy_contrast_bounds(
                    pair,
                    policy_a=guard_label,
                    policy_b=comparator_label,
                    role="primary_oot",
                    lgd=float(lgd),
                )
                rows.append(
                    {
                        "window_id": str(window_id),
                        "paired_policy_id": policy_id,
                        "comparator_rule": rule,
                        "frontier_cap": float(
                            primary.loc[
                                primary["policy_label"].eq(comparator_label), "frontier_cap"
                            ].iloc[0]
                        ),
                        **bounds,
                    }
                )
            for item in frontier.itertuples(index=False):
                comparator_label = str(item.policy_label)
                pair = pd.concat([guard, allocations_by_label[comparator_label]], ignore_index=True)
                bounds = sharp_policy_contrast_bounds(
                    pair,
                    policy_a=guard_label,
                    policy_b=comparator_label,
                    role="primary_oot",
                    lgd=float(lgd),
                )
                rows.append(
                    {
                        "window_id": str(window_id),
                        "paired_policy_id": policy_id,
                        "comparator_rule": "point_cap_frontier",
                        "frontier_cap": float(item.frontier_cap),
                        **bounds,
                    }
                )
    return pd.DataFrame(rows)


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
    support_index = support.set_index(["window_id", "paired_policy_id"], verify_integrity=True)
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
    joined = scores.merge(
        outcomes[["id", "snapshot_default"]],
        on="id",
        how="left",
        validate="one_to_one",
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
                        covered = (outcome >= lower[mask]) & (outcome <= upper[mask])
                        n = int(mask.sum())
                        observed_covered = int(covered[observed].sum())
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
                                "coverage_resolved": float(np.mean(covered[observed])),
                                "coverage_lower": float(observed_covered / n),
                                "coverage_upper": float((observed_covered + (~observed).sum()) / n),
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
