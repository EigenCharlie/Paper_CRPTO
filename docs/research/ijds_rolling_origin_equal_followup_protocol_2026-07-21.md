# IJDS Rolling-Origin Equal-Follow-Up Coverage Protocol V1

## Status and retrospective defect

This is a retrospectively locked correction over an archive and rolling-origin
results that have already been inspected. The active comparison now uses the
same issue horizon, April--June, at both feasible origins, but its single
September 30, 2020 endpoint gives different administrative follow-up lengths:
51 months after the end of the 2016 issue quarter and 39 months after the end
of the 2017 issue quarter. That comparison therefore does not isolate a common
follow-up horizon.

This lineage evaluates the two frozen CatBoost origin families at one common
relative endpoint: 39 calendar months after the end of each April--June issue
quarter. It is error-controlled retrospective sensitivity analysis, not
preregistration, an untouched holdout, prospective validation, independent
replication, or a new model search.

Required tag:
`protocol/ijds-rolling-origin-equal-followup-2026-07-21-v1`.

Required run:
`ijds-rolling-origin-equal-followup-2026-07-21-v1`.

## Immutable outcome-free inputs

The evaluator imports and verifies only the score, residual-recipe, and
residual-fit-audit artifacts required for coverage. It must not import or
evaluate portfolio allocations.

### Origin 2016

- Outcome-free run:
  `ijds-binary-geometry-frontier-v4-2026-07-12-v1`.
- Protocol tag:
  `protocol/ijds-binary-geometry-frontier-v4-2026-07-12-v1`.
- Protocol commit:
  `2f8a7606e4eb65aa3ae3701fb3af8d9a51c953cd`.
- Freeze SHA-256:
  `c2b3dc2d18c9fed80708682d5a0369c80c89643e2d28024418522d954ebe667c`.
- Frozen candidate horizon: exactly April--June 2016, mechanically selected
  from 74,537 status-independent score identities.
- Frozen CatBoost window family: all eight ordinal windows W1--W8 fitted from
  January 2012--January 2013 as already declared.

### Origin 2017

- Outcome-free run:
  `ijds-rolling-origin-2017-2026-07-12-v2`.
- Protocol tag:
  `protocol/ijds-rolling-origin-stability-2026-07-12-v2`.
- Protocol commit:
  `9e689b2e3ca18aae5a2a967cc186da5dcd140891`.
- Freeze SHA-256:
  `e224e1ae534435d1b166a07c50fb1ce907b07d36257f37e826ee41a0cb086759`.
- Frozen candidate horizon: exactly April--June 2017, comprising 77,105
  status-independent score identities.
- Frozen CatBoost window family: all eight ordinal windows W1--W8 fitted from
  January 2013--January 2014 as already declared.

The evaluator verifies each freeze identity and digest, verifies the exact
score, recipe, and fit-audit descriptors embedded in each freeze, and verifies
those artifacts on disk. Neither learner, Platt map, taxonomy, residual
window, residual quantile, alpha, score, or candidate identity may be refit or
changed. Only `catboost_platt`, the canonical five-stratum taxonomy, and every
one of the eight frozen windows enter the analysis. No origin or window is
selected.

The raw archive remains
`data/raw/Loan_status_2007-2020Q3.csv`, SHA-256
`5878af2a088f8ab5214c9337289fb8b5eb6c6338fd3f417b6cdc18513dc6f35f`.
Candidate membership comes from the frozen score identities and issue dates,
never from status, payment, or endpoint fields. The raw join must be exact and
one-to-one for every frozen candidate ID.

## Common relative endpoint

For origin `o`, let `Q_o` be the end of its April--June issue quarter. The
endpoint cutoff is fixed mechanically as

`C_o = Q_o + 39 calendar months`.

Thus the two and only two cutoffs are:

| Origin | Issue months | Quarter end | Relative cutoff |
|---|---|---|---|
| 2016 | April--June 2016 | 2016-06-30 | 2019-09-30 |
| 2017 | April--June 2017 | 2017-06-30 | 2020-09-30 |

The 39-month horizon is the maximum common relative follow-up supported by the
already declared September 30, 2020 endpoint for the later origin. It is fixed
before this run and is not chosen from coverage outcomes.

At each origin, Fully Paid becomes available at last-payment month-end and
Charged Off becomes available at last-payment month-end plus the already frozen
six-calendar-month administrative lag. A terminal outcome is resolved only
when its reconstructed availability date is nonmissing and no later than that
origin's relative cutoff. The archive is not represented as a verified
point-in-time snapshot, and the reconstructed dates are not claimed to be the
true operational event dates.

## Complete endpoint census

The evaluator reports, without omission, both aggregate and monthly candidate,
resolved, and unresolved counts at each origin. It also reports the complete
five-reason endpoint taxonomy at both origin and origin-month levels, including
explicit zero-count rows:

1. `fully_paid_by_reconstructed_cutoff`;
2. `charged_off_by_reconstructed_cutoff`;
3. `nonterminal_or_unresolved_status`;
4. `terminal_after_reconstructed_cutoff`; and
5. `terminal_availability_date_missing`.

The five reason rows must partition every candidate. The first two categories
must be resolved and the last three unresolved. Aggregate reason counts must
equal the sum of their three monthly counts. No missingness mechanism is
identified.

## Coverage estimand and complete reporting

For candidate `i`, frozen score `p_i`, and its frozen five-stratum residual
quantile `c_g`, the binary prediction set is

`S_i = {y in {0,1}: |y - p_i| <= c_g}`.

Let `M_i(0)` and `M_i(1)` be the two attainable binary miss indicators.
Resolved candidates retain their reconstructed observed outcome. Each
unresolved candidate independently contributes its attainable minimum and
maximum miss indicator. The exact finite-archive endpoints are

`coverage_lower = 1 - mean(miss_high)`

and

`coverage_upper = 1 - mean(miss_low)`.

This handles empty and two-label prediction sets loan by loan; unresolved rows
are not assigned blanket failure/success values. The evaluator reports all 16
origin-window cells: resolved coverage, sharp lower and upper endpoints, score
range, fit range, residual geometry, continuous interval width, and the four
binary-set shares. W1 at one origin is aligned only ordinally with W1 at the
other; the windows use their own frozen calendar dates and are not pooled.

The nominal reference is 0.90. If all 16 sharp upper endpoints are below 0.90,
the paper may describe the finite-archive below-nominal sharp endpoints as
recurrent under equal 39-month follow-up at the two feasible fitted origins.
That descriptive result alone is not a finite-sample rejection of
exchangeability or a failure of the conformal theorem. If any endpoint reaches
0.90, the run must retain the complete mixed result and the existing two-origin
recurrence statement cannot be called equal-follow-up robust. No majority
vote, origin selection, window selection, or pooled coverage estimate is
permitted.

## Stop rules

The run stops before writing scientific artifacts if any of the following
occurs:

1. HEAD is dirty, the required tag is absent, or the tag does not resolve to
   current HEAD.
2. A source-freeze identity, commit, SHA-256, required artifact descriptor, raw
   archive digest, or implementation input differs from the locked config.
3. An outcome-bearing column is present in either frozen score artifact, a
   source freeze reports outcome leakage, or any outcome is used for selection
   or fitting.
4. The origin set is not exactly `{2016, 2017}`, either issue-month set is not
   exactly April--June, either cutoff differs from quarter-end plus 39 months,
   or the charged-off lag differs from six months.
5. The frozen candidate census is not exactly 74,537 or 77,105, an ID is
   missing or duplicated, or the raw join changes an ID, term, issue month, or
   origin assignment.
6. Either imported CatBoost recipe family does not contain exactly its eight
   declared five-stratum windows, or the coverage grid is not exactly 16
   aggregate cells.
7. The five endpoint reasons fail to partition any origin or month, resolved
   and unresolved counts disagree, or an aggregate reason count does not equal
   its monthly sum.
8. A coverage endpoint or geometry value is absent, nonfinite, out of range,
   or the sharp lower endpoint exceeds the upper endpoint.
9. Either fresh output directory already exists. No historical run may be
   overwritten.

An empirical exception to the nominal reference is a reportable result and
does not stop or redesign the run.

## Interpretation boundary

This lineage evaluates candidate-level coverage only. It performs no portfolio
optimization, imports no allocation for evaluation, and authorizes no funded-
set or selected-set conformal statement. It cannot select a learner, origin,
window, taxonomy, endpoint, or policy; establish temporal invariance,
independent replication, external validity, causality, fairness, or deployment
performance; or convert the reconstructed endpoint into a verified archive
snapshot.

After committing this complete protocol implementation and creating the
required clean tag, execute only:

```powershell
uv run --locked python scripts/experiments/run_ijds_rolling_origin_equal_followup.py `
  --config configs/experiments/ijds_rolling_origin_equal_followup_2026-07-21_v1.yaml
```

The present implementation phase must not execute that command or inspect its
empirical outputs.
