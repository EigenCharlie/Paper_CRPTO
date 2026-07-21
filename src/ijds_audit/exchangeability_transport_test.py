"""Exact-rank transport tests for frozen split-conformal recipes.

The Beta--Binomial law implemented here is exact for continuous exchangeable
calibration and target nonconformity scores within a frozen Mondrian stratum.
With ties, the same upper tail is conservative for the deterministic strict
miss count: independent continuous tie breakers give the exact rank law, and
the strict-score miss count is no larger than its lexicographically broken-tie
counterpart.  This is an audit of exchangeability, not a repair of conformal
validity and not evidence that exchangeability holds when the null is not
rejected.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from itertools import product
from typing import Any

import numpy as np
import pandas as pd
from scipy.special import betaln, gammaln, logsumexp

from src.ijds_audit.grid_contracts import require_exact_grid, require_finite
from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    apply_binary_outcome_recipe,
    assign_conformal_groups,
)


def split_conformal_beta_parameters(calibration_rows: int, rank: int) -> tuple[int, int]:
    """Return Beta--Binomial parameters for a continuous exchangeable rank.

    Uniform allocation of the combined continuous ranks to calibration and
    target indices yields a target exceedance count with parameters
    ``(calibration_rows + 1 - rank, rank)``.  Under the stronger i.i.d. model,
    these are also the Beta parameters of ``1 - F(q)``.
    """
    rows = int(calibration_rows)
    order = int(rank)
    if rows < 1:
        raise ValueError("Split-conformal calibration_rows must be positive.")
    if not 1 <= order <= rows:
        raise ValueError("Split-conformal rank must lie in [1, calibration_rows].")
    return rows + 1 - order, order


def beta_binomial_log_upper_tail(
    *,
    trials: int,
    misses_at_least: int,
    beta_a: int,
    beta_b: int,
) -> float:
    """Return ``log P[X >= misses_at_least]`` for an exact Beta--Binomial law.

    The finite discrete tail is summed in log space instead of using a normal,
    binomial, chi-squared, or other large-sample approximation.  Keeping the
    logarithm also preserves multiplicity decisions when the ordinary
    probability underflows IEEE-754 double precision.
    """
    size = int(trials)
    threshold = int(misses_at_least)
    shape_a = int(beta_a)
    shape_b = int(beta_b)
    if size < 0:
        raise ValueError("Beta--Binomial trials must be non-negative.")
    if not 0 <= threshold <= size:
        raise ValueError("Beta--Binomial tail threshold must lie in [0, trials].")
    if shape_a < 1 or shape_b < 1:
        raise ValueError("Beta--Binomial shape parameters must be positive integers.")
    if threshold == 0:
        return 0.0

    values = np.arange(threshold, size + 1, dtype=np.float64)
    log_choose = gammaln(size + 1.0) - gammaln(values + 1.0) - gammaln(size - values + 1.0)
    log_mass = (
        log_choose + betaln(values + shape_a, size - values + shape_b) - betaln(shape_a, shape_b)
    )
    result = float(logsumexp(log_mass))
    if not math.isfinite(result):
        raise RuntimeError("Exact Beta--Binomial tail evaluation returned a nonfinite value.")
    if result > 1.0e-9:
        raise RuntimeError("Exact Beta--Binomial tail exceeded probability one numerically.")
    return min(0.0, result)


def probability_from_log(log_probability: float) -> float:
    """Convert a finite nonpositive log probability, allowing benign underflow."""
    value = float(log_probability)
    if not math.isfinite(value) or value > 1.0e-12:
        raise ValueError("A log probability must be finite and nonpositive.")
    if value >= 0.0:
        return 1.0
    return float(math.exp(value))


def holm_adjustment(log_p_values: Sequence[float], *, alpha: float) -> pd.DataFrame:
    """Return Holm step-down decisions and adjusted p-values in input order.

    The implementation operates on log p-values so arbitrarily small exact
    tails remain ordered correctly.  Holm controls familywise error under
    arbitrary dependence, which is essential for overlapping residual windows
    and repeated candidate panels.
    """
    family_alpha = float(alpha)
    if not 0.0 < family_alpha < 1.0:
        raise ValueError("Holm family alpha must lie in (0, 1).")
    logs = np.asarray(tuple(log_p_values), dtype=float)
    if logs.ndim != 1 or len(logs) == 0:
        raise ValueError("Holm adjustment requires a nonempty one-dimensional family.")
    if not bool(np.isfinite(logs).all()) or bool((logs > 1.0e-12).any()):
        raise ValueError("Holm log p-values must be finite and nonpositive.")
    logs = np.minimum(logs, 0.0)

    family_size = len(logs)
    order = np.argsort(logs, kind="stable")
    ranks = np.empty(family_size, dtype=int)
    critical = np.empty(family_size, dtype=float)
    adjusted_logs = np.empty(family_size, dtype=float)
    rejected = np.zeros(family_size, dtype=bool)
    continue_rejecting = True
    running_adjusted_log = -math.inf
    for position, original_index in enumerate(order):
        multiplier = family_size - position
        rank = position + 1
        threshold = family_alpha / multiplier
        raw_adjusted_log = min(0.0, float(logs[original_index]) + math.log(multiplier))
        running_adjusted_log = max(running_adjusted_log, raw_adjusted_log)
        ranks[original_index] = rank
        critical[original_index] = threshold
        adjusted_logs[original_index] = min(0.0, running_adjusted_log)
        passes = float(logs[original_index]) <= math.log(threshold)
        rejected[original_index] = continue_rejecting and passes
        if not passes:
            continue_rejecting = False

    return pd.DataFrame(
        {
            "holm_rank": ranks,
            "holm_critical_value": critical,
            "holm_adjusted_log_p_value": adjusted_logs,
            "holm_adjusted_p_value": [probability_from_log(value) for value in adjusted_logs],
            "holm_reject": rejected,
        }
    )


def _validate_endpoint_panel(
    scores: pd.DataFrame,
    outcomes: pd.DataFrame,
    *,
    learners: Sequence[str],
    role: str,
    expected_issue_months: Sequence[str],
    expected_candidates: int,
    expected_resolved: int,
    expected_unresolved: int,
    expected_resolved_y0: int,
    expected_resolved_y1: int,
) -> pd.DataFrame:
    required_scores = {"id", "issue_d", "design_split"}
    required_scores.update(f"pd_{learner}" for learner in learners)
    missing_scores = sorted(required_scores.difference(scores.columns))
    if missing_scores:
        raise ValueError(f"Frozen scores omit columns: {missing_scores}.")
    if not {"id", "snapshot_default"}.issubset(outcomes.columns):
        raise ValueError("Endpoint outcomes must contain id and snapshot_default.")

    primary = scores.loc[scores["design_split"].eq(role)].copy()
    primary["issue_month"] = (
        pd.to_datetime(primary["issue_d"], errors="raise").dt.to_period("M").astype(str)
    )
    actual_months = tuple(sorted(primary["issue_month"].unique()))
    if actual_months != tuple(expected_issue_months):
        raise RuntimeError(
            f"Primary issue-month set changed: {actual_months!r} != "
            f"{tuple(expected_issue_months)!r}."
        )
    if len(primary) != int(expected_candidates) or bool(primary["id"].duplicated().any()):
        raise RuntimeError("Primary score census or ID uniqueness changed.")

    endpoint = outcomes.loc[:, ["id", "snapshot_default"]].copy()
    if bool(endpoint["id"].duplicated().any()):
        raise RuntimeError("Endpoint outcomes contain duplicate IDs.")
    joined = primary.merge(
        endpoint,
        on="id",
        how="left",
        validate="one_to_one",
        indicator="_endpoint_merge",
    )
    if not bool(joined["_endpoint_merge"].eq("both").all()):
        examples = joined.loc[~joined["_endpoint_merge"].eq("both"), "id"].head(5)
        raise RuntimeError(
            "Endpoint alignment is incomplete for frozen primary IDs; "
            f"examples={examples.astype(str).tolist()}."
        )
    joined = joined.drop(columns="_endpoint_merge")
    raw_labels = joined["snapshot_default"]
    labels = pd.to_numeric(raw_labels, errors="coerce").to_numpy(dtype=float)
    invalid_nonmissing = raw_labels.notna().to_numpy() & np.isnan(labels)
    if bool(invalid_nonmissing.any()) or bool(np.isinf(labels).any()):
        raise RuntimeError("Endpoint contains a nonnumeric or infinite outcome.")
    resolved = np.isfinite(labels)
    observed = labels[resolved]
    if not bool(np.isin(observed, (0.0, 1.0)).all()):
        raise RuntimeError("Resolved endpoint contains a nonbinary outcome.")
    counts = {
        "candidates": int(len(joined)),
        "resolved": int(resolved.sum()),
        "unresolved": int((~resolved).sum()),
        "resolved_y0": int(np.sum(observed == 0.0)),
        "resolved_y1": int(np.sum(observed == 1.0)),
    }
    expected = {
        "candidates": int(expected_candidates),
        "resolved": int(expected_resolved),
        "unresolved": int(expected_unresolved),
        "resolved_y0": int(expected_resolved_y0),
        "resolved_y1": int(expected_resolved_y1),
    }
    if counts != expected:
        raise RuntimeError(f"Endpoint census changed: {counts!r} != {expected!r}.")
    return joined


def _canonical_fit_audit(
    fit_audit: pd.DataFrame,
    scores: pd.DataFrame,
    *,
    learners: Sequence[str],
    window_ids: Sequence[str],
    taxonomy_groups: int,
) -> pd.DataFrame:
    required = {
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
    missing = sorted(required.difference(fit_audit.columns))
    if missing:
        raise ValueError(f"Frozen residual-fit audit omits columns: {missing}.")
    canonical = fit_audit.loc[
        fit_audit["taxonomy_groups"].eq(taxonomy_groups)
        & fit_audit["learner"].isin(learners)
        & fit_audit["window_id"].isin(window_ids)
    ].copy()
    keys = ("learner", "window_id", "conformal_group")
    observed_keys = set(canonical.loc[:, list(keys)].itertuples(index=False, name=None))
    expected_keys = set(product(learners, window_ids, range(taxonomy_groups)))
    if observed_keys != expected_keys:
        missing_keys = sorted(expected_keys.difference(observed_keys), key=repr)[:5]
        extra_keys = sorted(observed_keys.difference(expected_keys), key=repr)[:5]
        raise RuntimeError(
            "Canonical residual-fit audit grid changed; "
            f"missing={missing_keys}, extra={extra_keys}."
        )
    if bool(canonical.duplicated(["learner", "window_id", "id"]).any()):
        raise RuntimeError("Canonical residual-fit audit contains duplicate learner-window IDs.")
    if bool(scores["id"].duplicated().any()):
        raise RuntimeError("Frozen score frame contains duplicate IDs.")

    reconciled: list[pd.DataFrame] = []
    for learner in learners:
        score_column = f"pd_{learner}"
        required_scores = {"id", "issue_d", "design_split", score_column}
        missing_scores = sorted(required_scores.difference(scores.columns))
        if missing_scores:
            raise ValueError(f"Frozen scores omit columns for {learner}: {missing_scores}.")
        lookup = scores.loc[
            scores["design_split"].eq("conformal_fit"),
            ["id", "issue_d", score_column],
        ].copy()
        if len(lookup) == 0 or bool(lookup["id"].duplicated().any()):
            raise RuntimeError(
                f"Frozen conformal-fit scores are empty or duplicated for {learner}."
            )
        learner_audit = canonical.loc[canonical["learner"].eq(learner)].copy()
        learner_audit = learner_audit.merge(
            lookup,
            on="id",
            how="left",
            validate="many_to_one",
            suffixes=("_audit", "_score"),
            indicator="_score_merge",
        )
        if not bool(learner_audit["_score_merge"].eq("both").all()):
            raise RuntimeError(f"Residual-fit IDs do not align to frozen scores for {learner}.")
        if not bool(
            pd.to_datetime(learner_audit["issue_d_audit"], errors="raise")
            .eq(pd.to_datetime(learner_audit["issue_d_score"], errors="raise"))
            .all()
        ):
            raise RuntimeError(f"Residual-fit issue dates changed for {learner}.")
        audit_point = pd.to_numeric(learner_audit["pd_point"], errors="coerce").to_numpy(
            dtype=float
        )
        source_point = pd.to_numeric(learner_audit[score_column], errors="coerce").to_numpy(
            dtype=float
        )
        if not bool(np.isfinite(audit_point).all()) or not bool(np.isfinite(source_point).all()):
            raise RuntimeError(f"Residual-fit/source scores are nonfinite for {learner}.")
        if not bool(np.isclose(audit_point, source_point, atol=5.0e-14, rtol=5.0e-14).all()):
            raise RuntimeError(f"Residual-fit scores changed from the frozen source for {learner}.")
        learner_audit["pd_point"] = source_point
        learner_audit = learner_audit.drop(
            columns=["issue_d_score", score_column, "_score_merge"]
        ).rename(columns={"issue_d_audit": "issue_d"})
        reconciled.append(learner_audit)
    return pd.concat(reconciled, ignore_index=True)


def _fit_stratum_audit(
    frame: pd.DataFrame,
    *,
    recipe: BinaryOutcomeConformalRecipe,
    group: int,
) -> dict[str, Any]:
    calibration_rows = int(recipe.group_counts[group])
    rank = int(recipe.finite_sample_ranks[group])
    raw_rank = int(recipe.raw_finite_sample_ranks[group])
    expected_raw_rank = int(math.ceil((calibration_rows + 1) * (1.0 - recipe.alpha)))
    if len(frame) != calibration_rows:
        raise RuntimeError(
            f"Frozen fit-stratum count changed for group {group}: "
            f"{len(frame)} != {calibration_rows}."
        )
    if raw_rank != expected_raw_rank:
        raise RuntimeError("The frozen split-conformal rank does not match alpha and n.")
    if raw_rank != rank:
        raise RuntimeError("The exact-rank Beta--Binomial audit requires an attained split rank.")
    beta_a, beta_b = split_conformal_beta_parameters(calibration_rows, rank)

    point = pd.to_numeric(frame["pd_point"], errors="coerce").to_numpy(dtype=float)
    labels = pd.to_numeric(frame["terminal_default"], errors="coerce").to_numpy(dtype=float)
    if not bool(np.isfinite(point).all()) or not bool(np.isin(labels, (0.0, 1.0)).all()):
        raise RuntimeError("Frozen residual-fit stratum contains invalid scores or labels.")
    assigned = assign_conformal_groups(point, recipe.bin_edges)
    if not bool(np.equal(assigned, group).all()):
        raise RuntimeError("Frozen residual-fit group does not match the recipe taxonomy.")

    threshold = float(recipe.residual_quantiles[group])
    lower = np.clip(point - threshold, 0.0, 1.0)
    upper = np.clip(point + threshold, 0.0, 1.0)
    if not bool(
        np.allclose(
            lower,
            pd.to_numeric(frame["conformal_lower"], errors="coerce").to_numpy(dtype=float),
            atol=1.0e-15,
            rtol=1.0e-15,
        )
    ) or not bool(
        np.allclose(
            upper,
            pd.to_numeric(frame["conformal_upper"], errors="coerce").to_numpy(dtype=float),
            atol=1.0e-15,
            rtol=1.0e-15,
        )
    ):
        raise RuntimeError("Frozen residual-fit endpoints do not match the recipe threshold.")
    covered = (labels >= lower) & (labels <= upper)
    if not np.array_equal(covered, frame["covered"].astype(bool).to_numpy()):
        raise RuntimeError("Frozen residual-fit coverage flag does not reconcile.")

    residual = np.abs(labels - point)
    covered_from_residual = residual <= threshold
    if not np.array_equal(covered, covered_from_residual):
        raise RuntimeError("Fit endpoint membership differs from the scalar residual rule.")
    ordered_threshold = float(np.sort(residual)[rank - 1])
    if not np.isclose(ordered_threshold, threshold, atol=1.0e-15, rtol=1.0e-15):
        raise RuntimeError("Frozen residual quantile does not equal its declared order statistic.")
    below = int(np.sum(residual < threshold))
    equal = int(np.sum(residual == threshold))
    above = int(np.sum(residual > threshold))
    if not below < rank <= below + equal or below + equal + above != calibration_rows:
        raise RuntimeError("Frozen residual threshold does not bracket its declared rank.")
    return {
        "fit_rows": calibration_rows,
        "finite_sample_rank": rank,
        "beta_a": beta_a,
        "beta_b": beta_b,
        "fit_residual_quantile": threshold,
        "fit_score_min": float(point.min()),
        "fit_score_max": float(point.max()),
        "fit_residual_below_threshold": below,
        "fit_residual_equal_threshold": equal,
        "fit_residual_above_threshold": above,
        "continuous_threshold_tie_singleton": equal == 1,
    }


def _reconcile_active_temporal_coverage(
    strata: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    learners: Sequence[str],
    window_ids: Sequence[str],
    taxonomy_groups: int,
    role: str,
) -> pd.DataFrame:
    """Require the exact-test statistics to reproduce the active V5 audit."""
    selected = reference.loc[
        reference["taxonomy_groups"].eq(taxonomy_groups)
        & reference["role"].eq(role)
        & reference["learner"].isin(learners)
        & reference["window_id"].isin(window_ids)
        & reference["conformal_group"].isin(range(taxonomy_groups))
    ].copy()
    require_exact_grid(
        selected,
        domains={
            "learner": tuple(learners),
            "window_id": tuple(window_ids),
            "conformal_group": tuple(range(taxonomy_groups)),
        },
        label="active V5 stratum coverage reference",
    )
    keys = ["learner", "window_id", "taxonomy_groups", "role", "conformal_group"]
    integer_metrics = ["candidate_rows", "resolved_rows", "unresolved_rows", "fit_rows"]
    numeric_metrics = [
        "coverage_resolved",
        "coverage_lower",
        "coverage_upper",
        "score_min",
        "score_max",
        "fit_residual_quantile",
        "fit_score_min",
        "fit_score_max",
    ]
    required = set(keys + integer_metrics + numeric_metrics)
    missing = sorted(required.difference(selected.columns))
    if missing:
        raise ValueError(f"Active V5 temporal coverage omits columns: {missing}.")
    merged = strata.merge(
        selected[keys + integer_metrics + numeric_metrics],
        on=keys,
        how="left",
        validate="one_to_one",
        suffixes=("", "_active_reference"),
        indicator="_active_reference_merge",
    )
    if not bool(merged["_active_reference_merge"].eq("both").all()):
        raise RuntimeError("Exact-test strata do not align to the active V5 coverage audit.")
    for metric in integer_metrics:
        reference_metric = f"{metric}_active_reference"
        if not np.array_equal(
            merged[metric].to_numpy(dtype=np.int64),
            merged[reference_metric].to_numpy(dtype=np.int64),
        ):
            raise RuntimeError(f"Exact-test {metric} does not reconcile to active V5.")
    for metric in numeric_metrics:
        reference_metric = f"{metric}_active_reference"
        actual = merged[metric].to_numpy(dtype=float)
        expected = merged[reference_metric].to_numpy(dtype=float)
        if not bool(np.isclose(actual, expected, atol=5.0e-14, rtol=5.0e-14).all()):
            raise RuntimeError(f"Exact-test {metric} does not reconcile to active V5.")
        merged[f"{metric}_active_difference"] = actual - expected
    return merged.drop(columns="_active_reference_merge")


def build_exchangeability_transport_test(
    scores: pd.DataFrame,
    outcomes: pd.DataFrame,
    fit_audit: pd.DataFrame,
    baseline_coverage_reference: pd.DataFrame,
    recipes: Mapping[str, Mapping[str, Mapping[int, BinaryOutcomeConformalRecipe]]],
    *,
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
    nominal_miscoverage: float,
    familywise_alpha: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build all stratum tests and hierarchical multiplicity-adjusted cells."""
    learner_names = tuple(str(value) for value in learners)
    windows = tuple(str(value) for value in window_ids)
    group_count = int(taxonomy_groups)
    if not learner_names or not windows or group_count < 1:
        raise ValueError("The exchangeability audit requires a nonempty declared grid.")
    if len(set(learner_names)) != len(learner_names) or len(set(windows)) != len(windows):
        raise ValueError("Learner and window identities must be unique.")
    nominal_alpha = float(nominal_miscoverage)
    if not 0.0 < nominal_alpha < 1.0:
        raise ValueError("Nominal miscoverage must lie in (0, 1).")
    if not 0.0 < float(familywise_alpha) < 1.0:
        raise ValueError("Familywise alpha must lie in (0, 1).")

    joined = _validate_endpoint_panel(
        scores,
        outcomes,
        learners=learner_names,
        role=role,
        expected_issue_months=expected_issue_months,
        expected_candidates=expected_candidates,
        expected_resolved=expected_resolved,
        expected_unresolved=expected_unresolved,
        expected_resolved_y0=expected_resolved_y0,
        expected_resolved_y1=expected_resolved_y1,
    )
    canonical_fit = _canonical_fit_audit(
        fit_audit,
        scores,
        learners=learner_names,
        window_ids=windows,
        taxonomy_groups=group_count,
    )
    grouped_fit = canonical_fit.groupby(
        ["learner", "window_id", "conformal_group"],
        observed=True,
        sort=False,
    )
    labels = pd.to_numeric(joined["snapshot_default"], errors="coerce").to_numpy(dtype=float)
    resolved = np.isfinite(labels)

    rows: list[dict[str, Any]] = []
    for learner in learner_names:
        if learner not in recipes:
            raise RuntimeError(f"Frozen recipes omit learner {learner!r}.")
        expected_taxonomy_provenance = f"{learner}_201101_201112_all_status_independent_scores"
        canonical_bin_edges: tuple[float, ...] | None = None
        probabilities = pd.to_numeric(joined[f"pd_{learner}"], errors="coerce").to_numpy(
            dtype=float
        )
        if not bool(np.isfinite(probabilities).all()) or bool(
            ((probabilities < 0.0) | (probabilities > 1.0)).any()
        ):
            raise RuntimeError(f"Frozen candidate scores are invalid for {learner!r}.")
        for window_id in windows:
            try:
                recipe = recipes[learner][window_id][group_count]
            except KeyError as exc:
                raise RuntimeError(
                    f"Frozen recipe grid omits {learner}/{window_id}/{group_count}."
                ) from exc
            if int(recipe.requested_groups) != group_count:
                raise RuntimeError("Frozen recipe group count changed.")
            if recipe.taxonomy_method != "fixed_empirical_linear_score_quantiles":
                raise RuntimeError("Frozen taxonomy method is not the fixed upstream design.")
            if recipe.taxonomy_provenance != expected_taxonomy_provenance:
                raise RuntimeError("Frozen taxonomy provenance changed.")
            recipe_edges = tuple(float(value) for value in recipe.bin_edges)
            if canonical_bin_edges is None:
                canonical_bin_edges = recipe_edges
            elif recipe_edges != canonical_bin_edges:
                raise RuntimeError("Frozen score-taxonomy edges changed across residual windows.")
            if not np.isclose(recipe.alpha, nominal_alpha, atol=0.0, rtol=0.0):
                raise RuntimeError("Frozen recipe nominal miscoverage changed.")
            groups, lower, upper = apply_binary_outcome_recipe(probabilities, recipe)
            for group in range(group_count):
                key = (learner, window_id, group)
                fit = _fit_stratum_audit(
                    grouped_fit.get_group(key),
                    recipe=recipe,
                    group=group,
                )
                mask = groups == group
                candidate_rows = int(mask.sum())
                if candidate_rows < 1:
                    raise RuntimeError(f"Primary candidate stratum is empty: {key!r}.")
                group_resolved = resolved[mask]
                group_labels = labels[mask]
                group_probability = probabilities[mask]
                threshold = float(fit["fit_residual_quantile"])
                miss_zero = group_probability > threshold
                miss_one = (1.0 - group_probability) > threshold
                geometry_miss_zero = lower[mask] > 0.0
                geometry_miss_one = upper[mask] < 1.0
                if not np.array_equal(miss_zero, geometry_miss_zero) or not np.array_equal(
                    miss_one, geometry_miss_one
                ):
                    raise RuntimeError(
                        "Candidate endpoint membership differs from the strict residual rule."
                    )
                resolved_misses = int(
                    np.sum(
                        np.where(
                            group_labels[group_resolved] == 0.0,
                            miss_zero[group_resolved],
                            miss_one[group_resolved],
                        )
                    )
                )
                unresolved_min = int(
                    np.minimum(miss_zero[~group_resolved], miss_one[~group_resolved]).sum()
                )
                unresolved_max = int(
                    np.maximum(miss_zero[~group_resolved], miss_one[~group_resolved]).sum()
                )
                misses_min = resolved_misses + unresolved_min
                misses_max = resolved_misses + unresolved_max
                if not 0 <= misses_min <= misses_max <= candidate_rows:
                    raise RuntimeError("Sharp unresolved miss bounds are incoherent.")

                log_p_value = beta_binomial_log_upper_tail(
                    trials=candidate_rows,
                    misses_at_least=misses_min,
                    beta_a=int(fit["beta_a"]),
                    beta_b=int(fit["beta_b"]),
                )
                bonferroni_log = min(0.0, log_p_value + math.log(group_count))
                expected_miss_rate = float(fit["beta_a"]) / (
                    float(fit["beta_a"]) + float(fit["beta_b"])
                )
                resolved_residual = np.where(
                    group_labels[group_resolved] == 0.0,
                    group_probability[group_resolved],
                    1.0 - group_probability[group_resolved],
                )
                unresolved_equal_zero = group_probability[~group_resolved] == threshold
                unresolved_equal_one = (1.0 - group_probability[~group_resolved]) == threshold
                rows.append(
                    {
                        "learner": learner,
                        "window_id": window_id,
                        "taxonomy_groups": group_count,
                        "conformal_group": group,
                        "role": role,
                        **fit,
                        "candidate_rows": candidate_rows,
                        "score_min": float(group_probability.min()),
                        "score_max": float(group_probability.max()),
                        "resolved_rows": int(group_resolved.sum()),
                        "unresolved_rows": int((~group_resolved).sum()),
                        "resolved_misses": resolved_misses,
                        "coverage_resolved": float(
                            1.0 - resolved_misses / int(group_resolved.sum())
                        ),
                        "resolved_target_residual_equal_threshold": int(
                            np.sum(resolved_residual == threshold)
                        ),
                        "unresolved_equal_threshold_if_y0": int(unresolved_equal_zero.sum()),
                        "unresolved_equal_threshold_if_y1": int(unresolved_equal_one.sum()),
                        "unresolved_min_equal_threshold": int(
                            np.minimum(unresolved_equal_zero, unresolved_equal_one).sum()
                        ),
                        "unresolved_max_equal_threshold": int(
                            np.maximum(unresolved_equal_zero, unresolved_equal_one).sum()
                        ),
                        "unresolved_min_misses": unresolved_min,
                        "unresolved_max_misses": unresolved_max,
                        "misses_min": misses_min,
                        "misses_max": misses_max,
                        "miss_rate_min": float(misses_min / candidate_rows),
                        "miss_rate_max": float(misses_max / candidate_rows),
                        "coverage_lower": float(1.0 - misses_max / candidate_rows),
                        "coverage_upper": float(1.0 - misses_min / candidate_rows),
                        "null_expected_miss_rate": expected_miss_rate,
                        "null_expected_misses": float(candidate_rows * expected_miss_rate),
                        "exact_log_p_value": log_p_value,
                        "exact_p_value": probability_from_log(log_p_value),
                        "exact_neg_log10_p_value": float(-log_p_value / math.log(10.0)),
                        "bonferroni_log_p_value": bonferroni_log,
                        "bonferroni_p_value": probability_from_log(bonferroni_log),
                        "within_cell_bonferroni_reject_at_cell_alpha": (
                            bonferroni_log <= math.log(float(familywise_alpha))
                        ),
                    }
                )

    strata = pd.DataFrame(rows)
    require_exact_grid(
        strata,
        domains={
            "learner": learner_names,
            "window_id": windows,
            "conformal_group": tuple(range(group_count)),
        },
        label="exact exchangeability transport strata",
    )
    require_finite(
        strata,
        (
            "fit_residual_quantile",
            "score_min",
            "score_max",
            "coverage_resolved",
            "miss_rate_min",
            "miss_rate_max",
            "coverage_lower",
            "coverage_upper",
            "null_expected_miss_rate",
            "null_expected_misses",
            "exact_log_p_value",
            "exact_p_value",
            "exact_neg_log10_p_value",
            "bonferroni_log_p_value",
            "bonferroni_p_value",
        ),
        label="exact exchangeability transport strata",
    )
    strata = _reconcile_active_temporal_coverage(
        strata,
        baseline_coverage_reference,
        learners=learner_names,
        window_ids=windows,
        taxonomy_groups=group_count,
        role=role,
    )
    cell_rows: list[dict[str, Any]] = []
    for (learner, window_id), frame in strata.groupby(
        ["learner", "window_id"], sort=False, observed=True
    ):
        if len(frame) != group_count:
            raise RuntimeError("A learner-window cell does not contain every frozen stratum.")
        minimum_log = float(frame["exact_log_p_value"].min())
        cell_log = min(0.0, minimum_log + math.log(group_count))
        cell_rows.append(
            {
                "learner": str(learner),
                "window_id": str(window_id),
                "taxonomy_groups": group_count,
                "stratum_tests": int(len(frame)),
                "minimum_stratum_log_p_value": minimum_log,
                "minimum_stratum_p_value": probability_from_log(minimum_log),
                "cell_bonferroni_log_p_value": cell_log,
                "cell_bonferroni_p_value": probability_from_log(cell_log),
                "strata_with_non_singleton_calibration_threshold_ties": int(
                    (~frame["continuous_threshold_tie_singleton"].astype(bool)).sum()
                ),
                "all_calibration_threshold_ties_singleton": bool(
                    frame["continuous_threshold_tie_singleton"].astype(bool).all()
                ),
            }
        )
    cells = pd.DataFrame(cell_rows)
    require_exact_grid(
        cells,
        domains={"learner": learner_names, "window_id": windows},
        label="Bonferroni learner-window exchangeability cells",
    )
    holm = holm_adjustment(
        cells["cell_bonferroni_log_p_value"].to_numpy(dtype=float),
        alpha=float(familywise_alpha),
    )
    cells = pd.concat([cells.reset_index(drop=True), holm], axis=1)
    cells["hierarchical_fwer_alpha"] = float(familywise_alpha)
    cells["holm_reject_exchangeability_null"] = cells["holm_reject"].astype(bool)

    learner_order = {name: index for index, name in enumerate(learner_names)}
    window_order = {name: index for index, name in enumerate(windows)}
    for frame in (strata, cells):
        frame["_learner_order"] = frame["learner"].map(learner_order)
        frame["_window_order"] = frame["window_id"].map(window_order)
    strata = (
        strata.sort_values(["_learner_order", "_window_order", "conformal_group"], kind="stable")
        .drop(columns=["_learner_order", "_window_order"])
        .reset_index(drop=True)
    )
    cells = (
        cells.sort_values(["_learner_order", "_window_order"], kind="stable")
        .drop(columns=["_learner_order", "_window_order"])
        .reset_index(drop=True)
    )
    return strata, cells
