# IJDS Rolling-Origin Endpoint V3 Recovery Protocol

## Status

This protocol recovers the previously locked 2015--2017 rolling-origin audit
under the active reconstructed endpoint. The earlier rolling results and the
archive have already been inspected. V3 is retrospective error correction and
stability evidence, not preregistration, prospective validation, an independent
replication count, or submission freeze.

Required tag:
`protocol/ijds-rolling-origin-stability-2026-07-15-v3`. Before execution, the
implementation-only V5 recovery erratum moved the fresh run to
`protocol/ijds-rolling-origin-stability-2026-07-15-v4`; the imported freeze,
endpoint contract, estimands, and stop rules are unchanged.

## Immutable Inputs

- The 2015 V2 failure receipt remains the complete result for that origin. Its
  first five-stratum residual window has counts
  `(1648, 1408, 1166, 927, 619)` against the locked minimum of 1,000. No 2015
  outcome join is permitted.
- The 2016 origin imports the active V4-v1 outcome-free freeze and is restricted
  mechanically to April--June 2016.
- The 2017 origin imports the V2 outcome-free freeze from
  `ijds-rolling-origin-2017-2026-07-12-v2`, SHA-256
  `e224e1ae534435d1b166a07c50fb1ce907b07d36257f37e826ee41a0cb086759`.
- Learners, hyperparameters, Platt blocks, taxonomies, residual windows,
  policies, comparator supports, solver settings, budget, purpose cap, payoff,
  and LGD remain unchanged at every origin.

## Sole Evaluation Correction

Both feasible origins use the V4 reconstructed endpoint at September 30, 2020
and the exhaustive five-reason taxonomy. A terminal label is observed only
when its reconstructed availability date is nonmissing and no later than the
cutoff. Missing dates and dates after the cutoff remain distinct unresolved
reasons.

The common horizon is exactly three issue months per feasible origin. Coverage
is recomputed over those candidate rows; portfolio bounds aggregate only the
same three monthly menus. No later month may rescue a primary result.

## Complete Questions and Reporting Rules

1. Report both learners and all eight windows for each feasible origin.
2. Report the 2015 infeasibility without relaxing the five-stratum minimum.
3. Report all nine guardrails, all declared comparator scopes, and all three
   metrics for the feasible origins.
4. Call coverage failure recurrent only if every reported upper bound is below
   0.90 at both feasible origins. This is recurrence across two fitted origins,
   not three-origin stability.
5. Call a portfolio direction stable only if one nonzero sign survives every
   window-policy cell at both feasible origins. A crossing cell defeats that
   statement.
6. Do not pool origins, calculate a vote, select an origin, search a fourth
   origin, or claim selected-set validity, causality, or external validity.

Any source-freeze mismatch, incomplete three-month census, endpoint alignment
failure, budget failure, C2 mismatch, or incomplete comparator envelope stops
the recovery. New outputs use fresh immutable run paths and do not overwrite
the V2 rolling artifacts.
