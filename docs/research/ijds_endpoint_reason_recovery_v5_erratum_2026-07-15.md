# IJDS Endpoint-Reason Recovery V5 Erratum

## Status

The V4 evaluation
`ijds-binary-geometry-frontier-v4-2026-07-15-v4` stopped before writing any
evaluation artifact. Its immutable failure receipt is
`models/experiments/ijds_audit/ijds-binary-geometry-frontier-v4-2026-07-15-v4/evaluate_failure_receipt.json`
(5,179 bytes; SHA-256
`f29ccaeb6341fe7c40e7826f0f40ba7fdc453adf680e4f20808c474715bfcc02`).
No protected stage or protected artifact was run or written.

The stop occurred in the V3 reference reconciliation. The checker required
bit-exact equality after recomputation. IEEE-754 roundoff changed values such
as `0.9739145159564250` to `0.9739145159564248`; Pandas therefore flagged
30.53977% of the `mean_width` cells despite differences at machine precision.
This is a validation-implementation defect, not an endpoint or result change.

## Locked V5 Repair

V5 makes exactly two implementation changes.

1. Reference reconciliation remains exact for IDs, strings, booleans,
   integers, datetimes, row order, column order, dtypes, and missingness masks.
   Floating columns use fixed absolute and relative tolerances of `5e-14`.
   This is below the protocol ceiling of `1e-12`; every frame records the
   maximum absolute and relative drift by floating column. Any larger drift
   stops the run before outputs are written.
2. The exact point-cap contrast loop uses the already tested
   `PolicyContrastIndex`. It validates loan facts and allocation IDs once per
   window, then evaluates the same policy pairs through the same sharp-bound
   array oracle. The public slow pairwise implementation remains the test
   oracle. This changes indexing cost, not arithmetic definitions or row
inventory.

A full pre-tag preflight rebuilt all 221,040 V3 contrast rows through the
indexed path in 196.679 seconds. Every inherited column matched the slow V3
artifact with maximum absolute floating drift `0.0` under the locked
tolerance. This benchmark is implementation validation, not paper evidence.

The benchmark preflight also confirmed that C2 has one matched point-score cap
per month, not one cap per window. The inherited window-level `frontier_cap`
field retains its deterministic first-month value solely for V3 column
reconciliation; C2 bounds always aggregate the full monthly sequence. Unique
window-level cap validation applies only to C0 and C1. No C2 result treats the
legacy scalar as its estimand.

The V5 repair does not alter the raw universe, endpoint cutoff, six-month
charge-off lag, endpoint reason taxonomy, source freezes, score vectors,
residual recipes, taxonomies, allocation panels, comparator support, rulers,
coordinates, LGD, simulation design, or claim boundary. No outcome may select
an implementation, model, window, policy, or comparator.

## Fresh Runs and Stop Rules

Required fresh tags are:

- `protocol/ijds-binary-geometry-frontier-v4-2026-07-15-v5`;
- `protocol/ijds-credit-risk-controls-2026-07-15-v5`;
- `protocol/ijds-normalized-objective-frontier-2026-07-15-v5`;
- `protocol/ijds-missingness-sensitivity-2026-07-15-v2`; and
- `protocol/ijds-rolling-origin-stability-2026-07-15-v4`.

The binary, credit-control, and two-ruler runs must reconcile every V3
reference column under the locked equivalence contract. The binary run may
append only endpoint-reason and identification-width diagnostics. Missingness
and rolling-origin retain their previously declared complete specification
families; their tags change only because implementation provenance changed.

Stop without adaptation if a reference frame changes inventory, a non-floating
column differs, a floating difference exceeds either tolerance, the optimized
grid differs from the slow oracle beyond `1e-15` in focused tests, or any
protected artifact would be touched. Failed directories remain immutable and
all retries require a fresh run tag.
