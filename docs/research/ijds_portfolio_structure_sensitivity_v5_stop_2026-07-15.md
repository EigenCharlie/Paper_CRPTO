# IJDS Portfolio-Structure Sensitivity V5 Stop

## Decision

V5 is a stopped outcome-free run, not a structural-sensitivity result. It must
not be evaluated, cited as a completed grid, or registered as active paper
evidence.

## What completed

- The run started from tagged commit
  `481528a6973eded94189435957f9b8064bc4bb06` under
  `protocol/ijds-portfolio-structure-sensitivity-2026-07-15-v5`.
- All 33 V4 shards named by the locked recovery complement passed inventory,
  identity, outcome-column, row-count, retry-ladder, and cap-residual checks.
- The new `b0500k_p020_l045` and `b0500k_p020_l065` shards completed and pass
  the same checks. Each used 40 declared minimum-endpoint retries at `1e-10`;
  its largest absolute minimum-cap residual is approximately `1.000001e-10`,
  below the locked `1e-8` tolerance.
- The only absent scenario directory is `b0500k_p020_l025`.

Thus 35 scenario shards are physically complete, but no 36-scenario protocol
freeze exists. The two newly completed shards are outcome-free checkpoint
material only; their presence does not promote V5.

## Stop trigger

The missing scenario reached all eight residual windows and then failed the
locked order audit with:

```text
RuntimeError: ID reversal changed a primary endpoint allocation.
```

The failure arose inside `_validate_complete_build` before the scenario could
be written. V5 therefore produced neither `protocol_freeze.json` nor any
structural outcome evaluation. No endpoint outcomes were joined and no
protected stage or protected artifact was touched.

## Required diagnosis before any successor

A successor may not merely increase the order-exposure tolerance. It must first
measure the failing cells, objective and score reconciliation, exposure
distance, and whether the difference reflects solver-scale noise or a genuinely
nonunique optimal allocation. If the allocation is nonunique, the successor
must define an outcome-free policy convention or a set-valued evaluation that
accounts for that ambiguity. Any amendment must use a fresh protocol, run tag,
and complete reporting; V5 remains immutable stopped provenance.
