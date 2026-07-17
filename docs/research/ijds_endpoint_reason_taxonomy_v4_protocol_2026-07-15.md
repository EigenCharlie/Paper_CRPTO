# IJDS Endpoint-Reason Taxonomy V4 Recovery Protocol

## Status

This protocol corrects one explanatory defect in the V3 reconstructed endpoint.
The archive and all V3 results have already been inspected. V4 is therefore a
retrospective reason-taxonomy recovery, not preregistration, confirmation, a new
endpoint choice, or submission freeze.

The outcome-free V4-v1, credit-controls-v1b, and two-ruler-v1c freezes remain
immutable. V4 may import them by hash and may change only the reason assigned to
an archive-terminal row that is unresolved at September 30, 2020. It cannot
refit scores or residual recipes, modify an allocation, select a result, or
overwrite V3.

Required tags:

- `protocol/ijds-binary-geometry-frontier-v4-2026-07-15-v4`;
- `protocol/ijds-credit-risk-controls-2026-07-15-v4`; and
- `protocol/ijds-normalized-objective-frontier-2026-07-15-v4`.

## Defect

V3 correctly required a nonmissing reconstructed availability date no later
than the cutoff before retaining a terminal label. Its prose and one resolution
string nevertheless described every reclassified terminal row as having a date
after the cutoff. Independent reconciliation found two distinct reasons among
the 525 primary rows:

- 478 `Charged Off` rows have no parseable `last_pymnt_d`, so no reconstructed
  availability date exists; and
- 47 terminal rows have a reconstructed availability date after the cutoff.

Both groups were already unresolved in V3. The defect is explanatory, not
numeric.

## Exhaustive Reason Taxonomy

For a configured cutoff, every candidate must receive exactly one reason:

1. `fully_paid_by_reconstructed_cutoff`;
2. `charged_off_by_reconstructed_cutoff`;
3. `terminal_availability_date_missing`;
4. `terminal_after_reconstructed_cutoff`; or
5. `nonterminal_or_unresolved_status`.

Only the first two reasons have an observed binary endpoint. A missing date is
never treated as a post-cutoff date. Exact `Default` remains in the fifth class
because the terminal charged-off event is not established by that status alone.

## Required Reconciliation

1. Candidate, resolved, and unresolved counts must remain exactly
   376,890, 364,814, and 12,076 in primary OOT.
2. The 525-row V3-to-V4 difference must partition into 478 missing-date and 47
   post-cutoff rows.
3. Every reference column in coverage, prediction metrics, portfolio
   evaluation, sharp contrasts, direction censuses, comparator envelopes, and
   simulation artifacts must be exactly equal after Parquet loading. V4 may
   append endpoint-reason and identification-width diagnostics only.
4. Scores, recipes, supports, rulers, coordinates, policies, allocations,
   payoff definitions, LGD, and endpoint labels must not change.
5. Any scientific metric or direction difference stops the recovery. It cannot
   be explained away as part of the taxonomy correction.

## Interpretation Boundary

V4 authorizes the statement that 525 archive-terminal candidates remain
unresolved under the conservative reconstruction, with 478 lacking a usable
availability date and 47 dated after the cutoff. It does not establish why a
date is missing, the true operational event date, missing-at-random behavior,
or a verified historical snapshot.
