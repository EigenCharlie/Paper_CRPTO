# IJDS normalized/objective frontier V1c outcome-free results

## Status

V1c completed from clean tagged commit `46f4df9` under
`protocol/ijds-normalized-objective-frontier-2026-07-13-v1c`. Its status is
`outcome_free_frontiers_frozen_before_archive_outcome_join`. No status, payment,
default, realized-payoff, coverage, or miscoverage column entered the frontier.
No protected stage or protected artifact was run or written.

V1 and V1b remain immutable stopped runs. V1c did not overwrite either run tag
or output path.

## Complete census

The 3,332-second run produced:

- 6,240 solve records;
- 622,455 positive funded rows;
- 720 primary endpoint comparisons;
- 26 score-independent objective-optimum diagnostics;
- 1,440 reversed-ID endpoint reruns; and
- 288 independent OR-Tools GLOP validations.

All eight windows, both roles, 26 monthly menus, five gammas, three coordinates,
and two rulers are present in both solve and allocation artifacts.

## Numerical falsification

- score ranges: `0.0628853` to `0.8546764`;
- common plug-in objective ranges: USD `66,857.10` to `151,229.07`;
- minimum absolute nonbasic reduced cost: `0.0046533`;
- zero near-zero reduced costs and zero primal-degenerate objective bases;
- maximum budget residual: USD `6.3656e-6`;
- maximum absolute frontier-constraint mismatch: `1.1642e-10`;
- maximum endpoint order distance: `2.6833e-12`;
- maximum endpoint objective drift under reversed IDs: USD `2.1787e-7`;
- maximum GLOP--HiGHS objective-rate difference: `2.1787e-13`; and
- maximum GLOP--HiGHS funded-score difference: `3.5943e-13`.

Every value is below its locked V1c threshold. All artifact, source, summary,
receipt, and implementation descriptors were recomputed and matched the freeze.
The Parquet schemas contain optimizer metadata such as `solver_status`, but no
loan-outcome field.

## Endpoint geometry

The normalized exposure distance is `L1/(2B)` between `gamma=1` and `gamma=0`.

| Ruler | Coordinate | Cells | Nonidentical | Minimum | Median | Maximum |
|---|---:|---:|---:|---:|---:|---:|
| normalized score | .25 | 120 | 120 | .440800 | .583608 | .695504 |
| normalized score | .50 | 120 | 120 | .241637 | .328782 | .505132 |
| normalized score | .75 | 120 | 120 | .119339 | .168475 | .245161 |
| objective matched | .25 | 120 | 32 | .000000 | .000000 | .079757 |
| objective matched | .50 | 120 | 120 | .070744 | .148500 | .233846 |
| objective matched | .75 | 120 | 120 | .073525 | .309296 | .575863 |

Neither ruler is globally degenerate. The normalized ruler changes every
endpoint allocation. The objective-matched ruler changes 272 of 360, but 88 of
120 low-objective-coordinate cells have exactly the same point and full-upper
allocation.

## Scientific consequence before outcomes

The locked promotion rule required a common **nonzero** sign for every window,
coordinate, and ruler before any positive direction could advance. The 88
allocation-identical objective-matched `.25` cells necessarily have zero
payoff, default, and miscoverage contrasts under any outcome vector. A positive
all-cell promotion is therefore structurally impossible before V2.

This is not a reason to delete `.25`, select `.50`/`.75`, or narrow the support.
It is evidence that the CRPTO decision effect depends on where the common
efficient frontier is evaluated. V2 remains necessary to quantify signs and
sharp common-outcome bounds in the nonidentical cells and to determine whether
the two rulers also disagree beyond the structural zeros. It cannot revive a
winner by excluding the zeros.

## Frozen sources

- summary:
  `models/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v1c/normalized_objective_frontier_summary.json`;
- freeze:
  `models/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v1c/protocol_freeze.json`;
- data pointer:
  `data/processed/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v1c.dvc`;
- model pointer:
  `models/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v1c.dvc`.
