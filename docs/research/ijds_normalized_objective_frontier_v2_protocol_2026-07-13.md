# IJDS normalized/objective frontier V2 outcome-evaluation protocol

## Status

This protocol is locked after the completed V1c outcome-free freeze and before
the first V2 outcome join. It evaluates the allocations already frozen under
`protocol/ijds-normalized-objective-frontier-2026-07-13-v1c`; it cannot refit a
model, recalibrate a residual recipe, resolve a new LP, or select a favorable
window, ruler, coordinate, gamma, month, or metric.

V2 is retrospective, not a pristine lockbox, a conformal repair, or a
submission freeze. The active manuscript remains V4 until V2 is verified and a
separate promotion decision reconciles all evidence.

## Immutable source

Before loading any outcome, V2 must verify the exact V1c freeze descriptor:

- path:
  `models/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v1c/protocol_freeze.json`;
- bytes: `15192`;
- SHA-256:
  `7877c5e460772a0093e4132eaa542e9049f7ec15d2ddaa35c2df389892a0e185`;
- protocol commit: `46f4df915d38eb5a6cc144484c6e6fe56d8ed397`;
- status: `outcome_free_frontiers_frozen_before_archive_outcome_join`.

Every V1c outcome-free artifact descriptor, schema, row count, and empty
outcome-column declaration must also match. V2 stops before reading the raw
archive if any check fails.

## Single outcome join

After freeze verification, V2 loads the raw archive with the parent V4 temporal
contract and materializes `snapshot_default` plus `snapshot_resolution` once.
It verifies unique IDs and exact role/period alignment for the 94,885
policy-development and 376,890 primary-OOT candidates. Observed outcomes must
be binary; unresolved outcomes remain missing and are never imputed.

The shared outcomes are joined many-to-one to all 622,455 positive funded rows.
Every one of the 6,240 fixed portfolios is evaluated with the existing coherent
payoff, funded-default, and binary-miscoverage identities. Development results
are diagnostics; primary contrasts use all fifteen OOT monthly menus.

## Endpoint contrasts

The only primary pair is `gamma=1 - gamma=0`. Interior gammas remain frozen
diagnostics and cannot be selected.

V2 reports:

- 720 monthly contrasts:
  `8 windows x 15 months x 2 rulers x 3 coordinates`;
- 48 complete-window contrasts:
  `8 windows x 2 rulers x 3 coordinates`; and
- 144 metric-direction rows:
  `48 window contrasts x 3 metrics`.

For each pair, V2 forms the union of loans funded by either endpoint. One
unresolved loan receives one common binary outcome when deriving the sharp
lower and upper bound. Separate worst cases for the two policies are forbidden.
Standardized payoff is reported in dollars and per-dollar rate; default and
miscoverage are exposure-weighted rates.

## Direction and promotion

A bound is positive only when its lower endpoint exceeds its locked metric
tolerance, negative only when its upper endpoint is below the negative
tolerance, exact zero when both endpoints lie within tolerance, and otherwise
crosses zero.

For each metric, a universal descriptive direction exists only if all 48
predeclared window/ruler/coordinate bounds have the same nonzero direction.
Any zero, crossing bound, or direction disagreement defeats that condition. No
majority vote or favorable subset is reported as a universal direction.

Even a universal direction would not restore candidate coverage, funded-set
validity, exchangeability, or a conformal portfolio guarantee. A positive
policy-superiority narrative would additionally require higher realized
standardized payoff and non-higher funded default across the complete support,
then a separately locked rolling-origin challenger. V2 itself cannot promote a
winner.

## Outputs and stops

All evaluated portfolios, outcome-joined allocations, monthly contrasts,
window contrasts, metric directions, and outcome-join census are retained. V2
stops on a source descriptor mismatch, nonbinary observed outcome, ID or
role/period misalignment, missing portfolio, incomplete contrast grid, or
attempted overwrite. A stopped run is reported rather than repaired in place.
