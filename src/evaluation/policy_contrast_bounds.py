"""Sharp pairwise policy contrasts with nullable binary outcomes."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

_FACT_COLUMNS = (
    "contractual_rate",
    "conformal_lower",
    "conformal_upper",
    "snapshot_default",
)
_ALLOCATION_COLUMNS = (
    "id",
    "role",
    "policy_label",
    "exposure",
    "expected_payoff_contribution",
)


def _sharp_binary_sum_bounds(
    value_if_zero: np.ndarray,
    value_if_one: np.ndarray,
    outcomes: np.ndarray,
) -> tuple[float, float]:
    observed = np.isfinite(outcomes)
    if bool(np.any(observed & ~np.isin(outcomes, [0.0, 1.0]))):
        raise ValueError("Observed outcomes must be binary.")
    exact = np.where(outcomes == 1.0, value_if_one, value_if_zero)
    lower = np.where(observed, exact, np.minimum(value_if_zero, value_if_one))
    upper = np.where(observed, exact, np.maximum(value_if_zero, value_if_one))
    return float(lower.sum()), float(upper.sum())


def _binary_identification_width(
    value_if_zero: np.ndarray,
    value_if_one: np.ndarray,
    outcomes: np.ndarray,
) -> float:
    """Return the exact width contributed by unrestricted binary outcomes."""
    unresolved = ~np.isfinite(outcomes)
    return float(np.abs(value_if_one[unresolved] - value_if_zero[unresolved]).sum())


def _sharp_policy_bounds_from_arrays(
    *,
    exposure_a: np.ndarray,
    exposure_b: np.ndarray,
    outcomes: np.ndarray,
    rates: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    expected_difference: float,
    policy_a: str,
    policy_b: str,
    role: str,
    lgd: float,
    normalization_capital_a: float | None = None,
    normalization_capital_b: float | None = None,
) -> dict[str, Any]:
    lengths = {
        len(exposure_a),
        len(exposure_b),
        len(outcomes),
        len(rates),
        len(lower),
        len(upper),
    }
    if len(lengths) != 1:
        raise ValueError("Policy contrast arrays are not aligned.")
    numeric = {
        "policy-a exposure": exposure_a,
        "policy-b exposure": exposure_b,
        "contractual rate": rates,
        "conformal lower endpoint": lower,
        "conformal upper endpoint": upper,
    }
    for label, values in numeric.items():
        if not bool(np.isfinite(values).all()):
            raise ValueError(f"{label} values must be finite.")
    if bool((exposure_a < 0.0).any()) or bool((exposure_b < 0.0).any()):
        raise ValueError("Policy exposures must be non-negative.")
    if bool((rates < 0.0).any()):
        raise ValueError("Contractual rates must be non-negative.")
    if bool((lower < 0.0).any()) or bool((upper > 1.0).any()) or bool((lower > upper).any()):
        raise ValueError("Conformal endpoints must satisfy 0 <= lower <= upper <= 1.")
    if not np.isfinite(expected_difference):
        raise ValueError("Expected objective difference must be finite.")
    if not np.isfinite(lgd) or lgd < 0.0:
        raise ValueError("LGD must be finite and non-negative.")
    total_a = float(exposure_a.sum())
    total_b = float(exposure_b.sum())
    if total_a <= 0.0 or total_b <= 0.0:
        raise ValueError("Both policies must allocate positive capital.")
    normalizer_a = total_a if normalization_capital_a is None else float(normalization_capital_a)
    normalizer_b = total_b if normalization_capital_b is None else float(normalization_capital_b)
    if not np.isfinite(normalizer_a) or not np.isfinite(normalizer_b):
        raise ValueError("Policy normalization capital must be finite.")
    if normalizer_a <= 0.0 or normalizer_b <= 0.0:
        raise ValueError("Policy normalization capital must be positive.")
    if normalizer_a < total_a - 1.0e-8 or normalizer_b < total_b - 1.0e-8:
        raise ValueError("Policy normalization capital cannot be below invested capital.")
    delta_exposure = exposure_a - exposure_b
    delta_weight = exposure_a / normalizer_a - exposure_b / normalizer_b
    payoff_if_zero = delta_exposure * rates
    payoff_if_one = delta_exposure * -float(lgd)
    payoff_rate_if_zero = delta_weight * rates
    payoff_rate_if_one = delta_weight * -float(lgd)
    default_if_zero = np.zeros(len(outcomes), dtype=float)
    default_if_one = delta_weight
    miscoverage_if_zero = delta_weight * (lower > 0.0).astype(float)
    miscoverage_if_one = delta_weight * (upper < 1.0).astype(float)
    payoff_lower, payoff_upper = _sharp_binary_sum_bounds(payoff_if_zero, payoff_if_one, outcomes)
    payoff_rate_lower, payoff_rate_upper = _sharp_binary_sum_bounds(
        payoff_rate_if_zero, payoff_rate_if_one, outcomes
    )
    default_lower, default_upper = _sharp_binary_sum_bounds(
        default_if_zero, default_if_one, outcomes
    )
    miscoverage_lower, miscoverage_upper = _sharp_binary_sum_bounds(
        miscoverage_if_zero, miscoverage_if_one, outcomes
    )
    widths = {
        "realized_payoff_identification_width": _binary_identification_width(
            payoff_if_zero, payoff_if_one, outcomes
        ),
        "realized_payoff_rate_identification_width": _binary_identification_width(
            payoff_rate_if_zero, payoff_rate_if_one, outcomes
        ),
        "weighted_default_identification_width": _binary_identification_width(
            default_if_zero, default_if_one, outcomes
        ),
        "weighted_miscoverage_identification_width": _binary_identification_width(
            miscoverage_if_zero, miscoverage_if_one, outcomes
        ),
    }
    bound_widths = {
        "realized_payoff_identification_width": payoff_upper - payoff_lower,
        "realized_payoff_rate_identification_width": payoff_rate_upper - payoff_rate_lower,
        "weighted_default_identification_width": default_upper - default_lower,
        "weighted_miscoverage_identification_width": miscoverage_upper - miscoverage_lower,
    }
    for name, width in widths.items():
        if not np.isclose(width, bound_widths[name], atol=1.0e-10, rtol=1.0e-12):
            raise RuntimeError(f"Sharp-bound width failed direct reconciliation for {name}.")
    return {
        "contrast": f"{policy_a}_minus_{policy_b}",
        "role": role,
        "policy_a": policy_a,
        "policy_b": policy_b,
        "policy_a_capital": total_a,
        "policy_b_capital": total_b,
        "policy_a_normalization_capital": normalizer_a,
        "policy_b_normalization_capital": normalizer_b,
        "funded_union_loans": int(len(outcomes)),
        "unresolved_union_loans": int((~np.isfinite(outcomes)).sum()),
        "expected_objective_difference": float(expected_difference),
        "realized_payoff_difference_lower": payoff_lower,
        "realized_payoff_difference_upper": payoff_upper,
        "realized_payoff_rate_difference_lower": payoff_rate_lower,
        "realized_payoff_rate_difference_upper": payoff_rate_upper,
        "weighted_default_difference_lower": default_lower,
        "weighted_default_difference_upper": default_upper,
        "weighted_miscoverage_difference_lower": miscoverage_lower,
        "weighted_miscoverage_difference_upper": miscoverage_upper,
        **widths,
        "payoff_direction_sign_robust": bool(payoff_lower > 0.0 or payoff_upper < 0.0),
        "default_direction_sign_robust": bool(default_lower > 0.0 or default_upper < 0.0),
        "miscoverage_direction_sign_robust": bool(
            miscoverage_lower > 0.0 or miscoverage_upper < 0.0
        ),
        "causal_interpretation": False,
    }


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...], *, label: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise KeyError(f"{label} is missing required columns: {missing}.")


def _validated_loan_facts(
    source: pd.DataFrame,
    *,
    required_ids: pd.Index,
    require_unique_ids: bool,
) -> pd.DataFrame:
    _require_columns(source, ("id", *_FACT_COLUMNS), label="Policy loan facts")
    facts = source.loc[source["id"].isin(required_ids), ["id", *_FACT_COLUMNS]].copy()
    if bool(facts["id"].isna().any()):
        raise ValueError("Policy loan facts contain missing IDs.")
    fact_counts = facts.groupby("id", observed=True, dropna=False)[list(_FACT_COLUMNS)].nunique(
        dropna=False
    )
    conflicting = fact_counts.gt(1)
    if bool(conflicting.any(axis=None)):
        conflict_ids = conflicting.index[conflicting.any(axis=1)].astype(str).tolist()
        conflict_columns = conflicting.columns[conflicting.any(axis=0)].tolist()
        raise ValueError(
            "Conflicting policy facts for the same loan: "
            f"ids={conflict_ids[:5]}, columns={conflict_columns}."
        )
    if require_unique_ids and bool(facts["id"].duplicated().any()):
        raise ValueError("External policy loan facts contain duplicate IDs.")
    facts = facts.drop_duplicates().set_index("id")
    if bool(facts.index.duplicated().any()):
        raise ValueError("Policy loan facts do not reduce to one row per ID.")
    missing_ids = required_ids.difference(facts.index)
    extra_ids = facts.index.difference(required_ids)
    if len(missing_ids) or len(extra_ids):
        raise ValueError(
            f"Policy loan-fact ID mismatch: missing={len(missing_ids)}, extra={len(extra_ids)}."
        )
    return facts.reindex(required_ids)


def _union_policy_allocations(
    allocations: pd.DataFrame,
    *,
    policy_a: str,
    policy_b: str,
    role: str,
) -> pd.DataFrame:
    subset = allocations.loc[
        allocations["role"].eq(role) & allocations["policy_label"].isin([policy_a, policy_b])
    ].copy()
    if subset.empty:
        raise ValueError(f"No allocations found for role {role!r}.")
    counts = subset.groupby(["id", "policy_label"], observed=True).size()
    if bool((counts > 1).any()):
        raise ValueError("A loan appears more than once within a policy contrast.")
    present = set(subset["policy_label"].astype(str))
    if present != {policy_a, policy_b}:
        raise ValueError(
            f"Policy contrast is missing labels: {sorted({policy_a, policy_b} - present)}"
        )

    attributes = ["id", *_FACT_COLUMNS]
    fact_counts = subset.groupby("id", observed=True, dropna=False)[list(_FACT_COLUMNS)].nunique(
        dropna=False
    )
    conflicting = fact_counts.gt(1)
    if bool(conflicting.any(axis=None)):
        conflict_ids = conflicting.index[conflicting.any(axis=1)].astype(str).tolist()
        conflict_columns = conflicting.columns[conflicting.any(axis=0)].tolist()
        raise ValueError(
            "Conflicting policy facts for the same loan: "
            f"ids={conflict_ids[:5]}, columns={conflict_columns}."
        )
    loans = subset[attributes].drop_duplicates()
    if bool(loans["id"].duplicated().any()):
        raise ValueError("Policy loan facts do not reduce to one row per ID.")
    loans = loans.set_index("id")
    exposure = subset.pivot(index="id", columns="policy_label", values="exposure").fillna(0.0)
    union = loans.join(exposure, how="outer").reset_index()
    union[policy_a] = pd.to_numeric(union[policy_a], errors="coerce").fillna(0.0)
    union[policy_b] = pd.to_numeric(union[policy_b], errors="coerce").fillna(0.0)
    return union


class PolicyContrastIndex:
    """Validated allocation index for repeated sharp pairwise contrasts.

    The allocation support is indexed once. Each contrast then gathers two sparse
    exposure vectors over the exact funded union and restores the deterministic ID
    order used by the public single-pair oracle.
    """

    def __init__(
        self,
        allocations: pd.DataFrame,
        *,
        role: str,
        loan_facts: pd.DataFrame | None = None,
    ) -> None:
        _require_columns(allocations, _ALLOCATION_COLUMNS, label="Policy allocations")
        subset = allocations.loc[allocations["role"].eq(role), list(_ALLOCATION_COLUMNS)].copy()
        if subset.empty:
            raise ValueError(f"No allocations found for role {role!r}.")
        if bool(subset[["id", "policy_label"]].isna().any(axis=None)):
            raise ValueError("Policy allocations contain missing IDs or policy labels.")
        subset["policy_label"] = subset["policy_label"].astype(str)
        duplicate = subset.duplicated(["id", "policy_label"], keep=False)
        if bool(duplicate.any()):
            raise ValueError("A loan appears more than once within a policy contrast index.")

        ids = pd.Index(subset["id"].drop_duplicates(), name="id")
        fact_source = allocations if loan_facts is None else loan_facts
        facts = _validated_loan_facts(
            fact_source,
            required_ids=ids,
            require_unique_ids=loan_facts is not None,
        )
        self._role = str(role)
        self._ids = ids
        self._rates = pd.to_numeric(facts["contractual_rate"], errors="raise").to_numpy(dtype=float)
        self._lower = pd.to_numeric(facts["conformal_lower"], errors="raise").to_numpy(dtype=float)
        self._upper = pd.to_numeric(facts["conformal_upper"], errors="raise").to_numpy(dtype=float)
        self._outcomes = pd.to_numeric(facts["snapshot_default"], errors="coerce").to_numpy(
            dtype=float
        )

        id_positions = pd.Series(np.arange(len(ids), dtype=np.int64), index=ids)
        self._sort_rank = np.empty(len(ids), dtype=np.int64)
        sorted_positions = id_positions.loc[ids.sort_values()].to_numpy(dtype=np.int64)
        self._sort_rank[sorted_positions] = np.arange(len(ids), dtype=np.int64)
        self._positions: dict[str, np.ndarray] = {}
        self._exposures: dict[str, np.ndarray] = {}
        self._expected: dict[str, float] = {}
        for label, frame in subset.groupby("policy_label", observed=True, sort=False):
            policy_label = str(label)
            positions = id_positions.loc[frame["id"]].to_numpy(dtype=np.int64)
            exposure = pd.to_numeric(frame["exposure"], errors="raise").to_numpy(dtype=float)
            if not bool(np.isfinite(exposure).all()):
                raise ValueError(f"Policy {policy_label!r} contains non-finite exposure.")
            if bool((exposure < 0.0).any()):
                raise ValueError(f"Policy {policy_label!r} contains negative exposure.")
            expected_contributions = pd.to_numeric(
                frame["expected_payoff_contribution"], errors="raise"
            ).to_numpy(dtype=float)
            if not bool(np.isfinite(expected_contributions).all()):
                raise ValueError(
                    f"Policy {policy_label!r} contains non-finite expected contributions."
                )
            self._positions[policy_label] = positions
            self._exposures[policy_label] = exposure
            self._expected[policy_label] = float(expected_contributions.sum())
        self._anchor_cache: dict[str, tuple[np.ndarray, np.ndarray]] = {}

    def _anchor_lookup(self, policy_label: str) -> tuple[np.ndarray, np.ndarray]:
        cached = self._anchor_cache.get(policy_label)
        if cached is not None:
            return cached
        positions = self._positions[policy_label]
        present = np.zeros(len(self._ids), dtype=bool)
        destination = np.full(len(self._ids), -1, dtype=np.int64)
        present[positions] = True
        destination[positions] = np.arange(len(positions), dtype=np.int64)
        cached = (present, destination)
        self._anchor_cache[policy_label] = cached
        return cached

    def sharp_bounds(
        self,
        *,
        policy_a: str,
        policy_b: str,
        lgd: float,
        normalization_capital_a: float | None = None,
        normalization_capital_b: float | None = None,
    ) -> dict[str, Any]:
        """Return sharp ``policy_a - policy_b`` bounds from the reusable index."""
        missing = sorted({policy_a, policy_b} - set(self._positions))
        if missing:
            raise ValueError(f"Policy contrast is missing labels: {missing}")

        positions_a = self._positions[policy_a]
        positions_b = self._positions[policy_b]
        exposure_values_a = self._exposures[policy_a]
        exposure_values_b = self._exposures[policy_b]
        present_a, destination_a = self._anchor_lookup(policy_a)
        overlap_b = present_a[positions_b]
        new_b = ~overlap_b
        union_positions = np.concatenate([positions_a, positions_b[new_b]])
        exposure_a = np.zeros(len(union_positions), dtype=float)
        exposure_b = np.zeros(len(union_positions), dtype=float)
        exposure_a[: len(positions_a)] = exposure_values_a
        exposure_b[destination_a[positions_b[overlap_b]]] = exposure_values_b[overlap_b]
        exposure_b[len(positions_a) :] = exposure_values_b[new_b]
        union_order = np.argsort(self._sort_rank[union_positions], kind="stable")
        union_positions = union_positions[union_order]
        exposure_a = exposure_a[union_order]
        exposure_b = exposure_b[union_order]

        outcomes = self._outcomes[union_positions]
        return _sharp_policy_bounds_from_arrays(
            exposure_a=exposure_a,
            exposure_b=exposure_b,
            outcomes=outcomes,
            rates=self._rates[union_positions],
            lower=self._lower[union_positions],
            upper=self._upper[union_positions],
            expected_difference=self._expected[policy_a] - self._expected[policy_b],
            policy_a=policy_a,
            policy_b=policy_b,
            role=self._role,
            lgd=lgd,
            normalization_capital_a=normalization_capital_a,
            normalization_capital_b=normalization_capital_b,
        )


def sharp_policy_contrast_bounds(
    allocations: pd.DataFrame,
    *,
    policy_a: str,
    policy_b: str,
    role: str,
    lgd: float,
) -> dict[str, Any]:
    """Return sharp ``policy_a - policy_b`` bounds on their funded union."""
    union = _union_policy_allocations(
        allocations,
        policy_a=policy_a,
        policy_b=policy_b,
        role=role,
    )
    exposure_a = union[policy_a].to_numpy(dtype=float)
    exposure_b = union[policy_b].to_numpy(dtype=float)
    outcomes = pd.to_numeric(union["snapshot_default"], errors="coerce").to_numpy(dtype=float)
    rates = union["contractual_rate"].to_numpy(dtype=float)
    lower = union["conformal_lower"].to_numpy(dtype=float)
    upper = union["conformal_upper"].to_numpy(dtype=float)
    expected = (
        allocations.loc[
            allocations["role"].eq(role) & allocations["policy_label"].eq(policy_a),
            "expected_payoff_contribution",
        ].sum()
        - allocations.loc[
            allocations["role"].eq(role) & allocations["policy_label"].eq(policy_b),
            "expected_payoff_contribution",
        ].sum()
    )
    return _sharp_policy_bounds_from_arrays(
        exposure_a=exposure_a,
        exposure_b=exposure_b,
        outcomes=outcomes,
        rates=rates,
        lower=lower,
        upper=upper,
        expected_difference=float(expected),
        policy_a=policy_a,
        policy_b=policy_b,
        role=role,
        lgd=lgd,
    )
