# IJDS Portfolio-Structure Sensitivity V5 Numerical Amendment

V5 inherits the scientific grid from V2, parallel execution from V3, and shard
validation/recovery from V4. V4 validated and recovered 29 V3 shards, completed
four additional shards, and stopped before consolidation when one USD 0.5
million, 20%-purpose-cap scenario returned HiGHS model status `Unknown` at an
exact minimum-score endpoint. No structural outcome evaluation existed or was
inspected.

An outcome-free diagnostic covered all 120 October 2016
LGD-window-gamma endpoint cells for the three missing scenarios:

- LGD 0.25: 25 of 40 exact endpoints initially failed as `Infeasible` or by
  budget reconciliation; all 25 solved at `minimum_score + 1e-12`.
- LGD 0.45 and 0.65: all 80 exact endpoints returned `Unknown` at zero and
  `1e-12`; all 80 solved at `minimum_score + 1e-10`.
- Every recovered solve filled the USD 500,000 budget to the locked tolerance.
  Its score residual was no larger than the applied slack.

V5 therefore replaces the single retry with the closed ladder
`[1e-12, 1e-10]`. It may advance only after `Infeasible`, `Unknown`, or the
already recognized budget-reconciliation failure at the exact minimum
endpoint. Any other error stops immediately. Failure at `1e-10` also stops.
The largest permitted retry remains 100 times smaller than the locked `1e-8`
cap-residual tolerance, and every applied step is persisted per
window-month-gamma cell.

V5 may recover the 33 complete V4 shards only after the full V4 validation
contract. It recomputes exactly the three locked USD 0.5 million, 20%-cap
scenarios and consolidates only after all 36 scenario identities pass.

Required tag: `protocol/ijds-portfolio-structure-sensitivity-2026-07-15-v5`.
