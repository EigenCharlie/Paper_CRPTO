# Bounded maturity-safe IJDS protocol v2 (2026-07-10)

## Reason for the amendment

The tagged v1 run stopped on its predeclared observability guard: contractual
maturity did not imply that every 2016-04--2017-06 snapshot status was resolved.
The process had selected the policy on 2012H2 and solved future allocations,
but it wrote no summary and exposed no realized payoff, default, coverage, or
transport contrast.

This amendment is therefore limited to missing-outcome handling. It does not
alter the chronology, candidate universe, features, model, calibration,
conformal recipe, policy grid, 2012H2 selector, constraints, payoff, monthly
budgets, baselines, metrics, or interpretation of the conformal object.

## Locked amendment

- Required tag:
  `protocol/ijds-maturity-safe-locked-bounded-h1h2-2026-07-10-v2`.
- Executable config:
  `configs/experiments/ijds_maturity_safe_locked_bounded_h1h2_2026-07-10.yaml`.
- Fresh run tag:
  `champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2`.
- Every primary and extension candidate remains in its issue-month menu.
- Nullable binary outcomes receive sharp lower and upper default, payoff, and
  miscoverage bounds; no unresolved row is coerced or discarded.
- The transport identity is evaluated under lower and upper extremal
  completions. Its funded endpoint is a sharp aggregate bound. Intermediate
  terms describe that completion and are not component-wise confidence bounds.
- A directional primary claim must be sign-robust across bounds relative to
  the independently selected point-PD baseline. Otherwise the result is
  reported as ambiguous.

All other clauses and decision rules in the v1 protocol remain in force. No
post-result tuning is permitted.
