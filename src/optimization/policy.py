"""Policy enums for the portfolio optimization layer.

Centralizes the canonical names of the uncertainty-handling policies used in
:func:`crpto.optimization.portfolio_model.compute_effective_pd` and surrounding
scripts. Existing callers that pass plain strings keep working — the resolver
normalizes legacy aliases (``"point"``, ``"worst_case"``, ``"robust"``, ...)
into the canonical :class:`PolicyMode` value.
"""

from __future__ import annotations

from enum import StrEnum


class PolicyMode(StrEnum):
    """Canonical uncertainty policies for the PD constraint.

    The string value of each member equals the canonical name accepted by
    :func:`compute_effective_pd`, so passing the enum or its ``.value`` is
    interchangeable.
    """

    POINT_ESTIMATE = "point_estimate"
    HARD_WORST_CASE = "hard_worst_case"
    BLENDED_UNCERTAINTY = "blended_uncertainty"
    CAPPED_BLENDED_UNCERTAINTY = "capped_blended_uncertainty"
    TAIL_BLENDED_UNCERTAINTY = "tail_blended_uncertainty"
    SEGMENT_TAIL_BLENDED_UNCERTAINTY = "segment_tail_blended_uncertainty"
    SEGMENT_RELATIVE_TAIL_BLENDED_UNCERTAINTY = "segment_relative_tail_blended_uncertainty"


# Legacy aliases recognised by :func:`resolve_policy_mode`.
_ALIASES: dict[str, PolicyMode] = {
    "point": PolicyMode.POINT_ESTIMATE,
    "point_estimate": PolicyMode.POINT_ESTIMATE,
    "nonrobust": PolicyMode.POINT_ESTIMATE,
    "non_robust": PolicyMode.POINT_ESTIMATE,
    "hard_worst_case": PolicyMode.HARD_WORST_CASE,
    "worst_case": PolicyMode.HARD_WORST_CASE,
    "worstcase": PolicyMode.HARD_WORST_CASE,
    "robust": PolicyMode.HARD_WORST_CASE,
    "blended_uncertainty": PolicyMode.BLENDED_UNCERTAINTY,
    "blended": PolicyMode.BLENDED_UNCERTAINTY,
    "capped_blended_uncertainty": PolicyMode.CAPPED_BLENDED_UNCERTAINTY,
    "capped_blended": PolicyMode.CAPPED_BLENDED_UNCERTAINTY,
    "tail_blended_uncertainty": PolicyMode.TAIL_BLENDED_UNCERTAINTY,
    "tail_blended": PolicyMode.TAIL_BLENDED_UNCERTAINTY,
    "segment_tail_blended_uncertainty": PolicyMode.SEGMENT_TAIL_BLENDED_UNCERTAINTY,
    "segment_tail_blended": PolicyMode.SEGMENT_TAIL_BLENDED_UNCERTAINTY,
    "segment_relative_tail_blended_uncertainty": (
        PolicyMode.SEGMENT_RELATIVE_TAIL_BLENDED_UNCERTAINTY
    ),
    "segment_relative_tail_blended": PolicyMode.SEGMENT_RELATIVE_TAIL_BLENDED_UNCERTAINTY,
}


def resolve_policy_mode(value: str | PolicyMode | None) -> PolicyMode:
    """Normalize a policy mode label (legacy alias or canonical name) into a :class:`PolicyMode`.

    Raises:
        ValueError: If the label is unknown.
    """
    if value is None:
        return PolicyMode.HARD_WORST_CASE
    if isinstance(value, PolicyMode):
        return value
    key = str(value).strip().lower()
    if not key:
        return PolicyMode.HARD_WORST_CASE
    try:
        return _ALIASES[key]
    except KeyError as err:
        canonical = ", ".join(m.value for m in PolicyMode)
        raise ValueError(
            f"Unsupported policy_mode={value!r}. Canonical names: {canonical}."
        ) from err


def all_policy_modes() -> tuple[PolicyMode, ...]:
    """Tuple of all canonical policy modes — useful for parametrised tests and sweeps."""
    return tuple(PolicyMode)
