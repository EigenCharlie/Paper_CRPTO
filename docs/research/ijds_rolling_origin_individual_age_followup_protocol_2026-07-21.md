# IJDS Rolling-Origin Individual-Age Follow-Up Sensitivity Protocol V1

## Status and retrospective question

The active equal-follow-up comparison fixes one cutoff 39 calendar months after
the end of each April--June issue quarter. Relative to the end of an
individual loan's issue month, that construction still supplies 41, 40, and 39
months to April, May, and June loans, respectively. This protocol removes that
within-quarter age heterogeneity by assigning every frozen candidate its own
administrative cutoff at the available calendar-month resolution.

The Lending Club archive, the active equal-follow-up results, and the proposed
individual-age design have already been inspected. This is therefore a
retrospectively locked, complete descriptive sensitivity. It is not
preregistration, confirmation, an untouched holdout, or independent
replication. It is not an error-controlled hypothesis-test family.

Required future protocol tag:
`protocol/ijds-rolling-origin-individual-age-followup-2026-07-21-v1`.

Required future run:
`ijds-rolling-origin-individual-age-followup-2026-07-21-v1`.

The protocol implementation step creates the document, configuration, runner,
and tests only. It must not execute the empirical run or create the tag.

## Immutable outcome-free parent

The sensitivity imports the hash-locked configuration of the active
equal-quarter-follow-up lineage:

- parent config:
  `configs/experiments/ijds_rolling_origin_equal_followup_2026-07-21_v1.yaml`;
- parent config SHA-256:
  `5a3d8369a371b346b2268377a195028e84ed8efca74a9e55e468b4df0ed0828a`;
- parent config bytes: `5,502`.

Loading that parent must reproduce, before any outcome join, both frozen source
contracts:

1. April--June 2016: 74,537 status-independent score identities from
   `ijds-binary-geometry-frontier-v4-2026-07-12-v1` and all eight frozen
   CatBoost/Platt residual windows W1--W8.
2. April--June 2017: 77,105 status-independent score identities from
   `ijds-rolling-origin-2017-2026-07-12-v2` and all eight frozen
   CatBoost/Platt residual windows W1--W8.

The evaluator hash-verifies the parent config, both source freezes, and only
their score, residual-recipe, and residual-fit-audit artifacts. It imports no
portfolio allocation. Learner, Platt map, five-stratum taxonomy, alpha 0.10,
residual windows, fitted residual thresholds, score, and candidate identities
are unchanged. Candidate membership is selected from frozen IDs and issue
month, never status, payment, or endpoint fields.

The raw endpoint source remains
`data/raw/Loan_status_2007-2020Q3.csv`, SHA-256
`5878af2a088f8ab5214c9337289fb8b5eb6c6338fd3f417b6cdc18513dc6f35f`.
The raw join is exact and one-to-one for every frozen candidate ID.

## Individual-age endpoint

For candidate `i`, let `I_i` be the calendar month containing its frozen and
raw-reconciled `issue_d`. The issue-month endpoint and evaluation cutoff are

`E_i = month_end(I_i)`

and

`C_i = month_end(I_i + 39 calendar months)`.

Equivalently, the month index of `C_i` is exactly 39 greater than the month
index of `E_i`. The complete predeclared cutoff map is:

| Origin | Issue month | Loan-specific cutoff |
|---|---|---|
| 2016 | 2016-04 | 2019-07-31 |
| 2016 | 2016-05 | 2019-08-31 |
| 2016 | 2016-06 | 2019-09-30 |
| 2017 | 2017-04 | 2020-07-31 |
| 2017 | 2017-05 | 2020-08-31 |
| 2017 | 2017-06 | 2020-09-30 |

The archive exposes `issue_d` at calendar-month resolution. Consequently this
design equalizes administrative age to 39 whole months from issue-month end;
it does not claim 39 exact days-to-days months from a latent origination day.
The latest cutoff remains September 30, 2020, so the sensitivity does not
extrapolate beyond the already declared endpoint support.

Fully Paid becomes available at last-payment month-end. Charged Off becomes
available at last-payment month-end plus the frozen six-calendar-month
administrative lag. Candidate `i` is resolved only when its reconstructed
terminal availability date is nonmissing and no later than `C_i`. The archive
is not represented as a verified point-in-time snapshot, and reconstructed
availability dates are not claimed to be exact operational event dates.

## Complete endpoint and coverage reporting

The evaluator reports both origin-level and issue-month-level candidate,
resolved, and unresolved counts. It also reports the complete five-reason
endpoint taxonomy, with explicit zero-count rows, at both levels:

1. `fully_paid_by_reconstructed_cutoff`;
2. `charged_off_by_reconstructed_cutoff`;
3. `nonterminal_or_unresolved_status`;
4. `terminal_after_reconstructed_cutoff`; and
5. `terminal_availability_date_missing`.

The five reasons must partition every candidate. The first two are resolved;
the last three are unresolved. Every monthly reason count must aggregate
exactly to its origin-level counterpart.

For candidate `i`, frozen score `p_i`, and frozen residual threshold `c_g`, the
binary prediction set is

`S_i = {y in {0,1}: |y - p_i| <= c_g}`.

Resolved candidates retain their reconstructed outcome. For unresolved
candidate `i`, the two attainable miss indicators are `M_i(0)` and `M_i(1)`.
The finite-archive sharp endpoints remain

`coverage_lower = 1 - mean(miss_high)`

and

`coverage_upper = 1 - mean(miss_low)`.

All 16 origin-window cells are reported: eight frozen CatBoost residual
windows at each of the two origins. Each cell includes resolved coverage,
sharp all-candidate coverage endpoints, residual geometry, continuous interval
width, and the four binary-set shares. W1 at one origin is only ordinally
aligned with W1 at the other; the two origins use their own frozen historical
fit calendars.

The nominal 0.90 level is a descriptive reference only. The runner performs no
hypothesis test, p-value calculation, confidence interval, or multiplicity
adjustment. Whether zero, some, or all 16 sharp upper endpoints fall below
0.90, the complete mixed result is retained. Counts such as `k/16` may describe
the finite archive but must not be called significant, error-controlled,
confirmatory, or independent evidence.

## Outcome isolation

The score census for both origins is selected and validated before the raw
endpoint columns are loaded. Frozen score inputs reject outcome-bearing
columns. Status and last-payment date enter only after the complete
status-independent candidate ID set and all score/recipe descriptors have been
verified. Outcomes cannot refit, retaxonomize, select, widen, drop, pool, or
otherwise alter a learner, window, score, residual threshold, candidate, or
endpoint rule.

## Stop rules

The future run stops before writing scientific artifacts if any of the
following occurs:

1. HEAD is dirty, the required future tag is absent, or the tag does not
   resolve to current HEAD.
2. The parent-config descriptor, source-freeze identity, source artifact
   descriptor, raw archive descriptor, or implementation input differs from
   the locked configuration.
3. An outcome-bearing column appears in a frozen score artifact, a source
   freeze reports outcome leakage, or an outcome is used for fitting,
   candidate selection, or specification selection.
4. The origin set is not exactly `{2016, 2017}`, the issue-month set is not
   exactly April--June at both origins, or the candidate counts differ from
   74,537 and 77,105.
5. Any raw ID is missing or duplicated, raw and frozen issue months disagree,
   a term is not 36 months, or the two origin ID sets overlap.
6. Any loan-specific cutoff differs from the six-row locked map, any month
   index difference is not 39, the maximum cutoff exceeds September 30, 2020,
   or the Charged Off lag differs from six months.
7. Either imported CatBoost recipe family is not exactly its eight declared
   five-stratum windows or the coverage grid is not exactly 16 cells.
8. The five endpoint reasons fail to partition an origin or issue month,
   resolved/unresolved counts disagree, a monthly count fails to aggregate, or
   any declared issue month is empty.
9. A coverage endpoint or set-geometry value is missing, nonfinite, outside
   `[0,1]`, internally inconsistent, or has lower endpoint above upper.
10. Either fresh output directory already exists. Historical artifacts are
    never overwritten.

An empirical exception to the nominal reference is a reportable outcome and
does not stop, narrow, rerun, or redesign the complete family.

## Interpretation boundary

This sensitivity evaluates candidate-level coverage only. It imports no
portfolio allocation and supports no funded-set or selected-set conformal
claim. It cannot establish exchangeability, temporal invariance, independent
replication, external validity, a cause of distribution shift, label-
conditional validity, fairness, causality, prospective performance, or
deployment readiness. It selects no learner, origin, month, window, endpoint,
or policy.

After a separate commit and creation of the required clean tag, the only
authorized empirical invocation is:

```powershell
uv run --locked python scripts/experiments/run_ijds_rolling_origin_individual_age_followup.py `
  --config configs/experiments/ijds_rolling_origin_individual_age_followup_2026-07-21_v1.yaml
```

The present implementation step must not execute that command, inspect new
empirical outputs, register DVC pointers, or add the lineage to paper-facing
evidence.
