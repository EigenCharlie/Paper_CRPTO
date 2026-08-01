# IJDS Label-Mondrian Retrospective Sensitivity Protocol V1 - 2026-07-21

## Status and question

This protocol asks whether replacing the active marginal absolute-residual
recipe with a class-conditional, score-stratified split-conformal recipe changes
the observed transport audit. The archive, active coverage results, and the
resolved-label imbalance were already inspected. The analysis is therefore a
retrospective, complete sensitivity, not preregistration, confirmation, or an
untouched holdout.

The analysis selects no learner, residual window, score stratum, class,
threshold, or favorable result. It cannot establish exchangeability in the
2016--2017 target period, repair temporal transport by construction, authorize
selected-set or funded-set validity, or support a fairness claim.

## Two-stage lineage and required tags

The lineage has two physically separate stages.

1. **F1 evaluation-outcome-free freeze.** It uses the already available
   historical conformal-fit labels but no primary-OOT endpoint. Required tag:
   `protocol/ijds-label-mondrian-freeze-2026-07-21-v1`. Required run:
   `ijds-label-mondrian-freeze-2026-07-21-v1`.
2. **E1 endpoint evaluation.** After F1 completes, the exact freeze and
   execution-receipt descriptors must replace the explicit pending fields in
   the E1 config. That change is
   committed and tagged as
   `protocol/ijds-label-mondrian-evaluation-2026-07-21-v1` before any endpoint
   join. Required run: `ijds-label-mondrian-evaluation-2026-07-21-v1`.

Both runners require their respective tag to resolve to a clean current HEAD.
F1 cannot load the raw archive or an evaluation endpoint. E1 refuses a pending,
unhashed, self-declared, or protocol-mismatched F1 freeze. Neither stage may
overwrite an existing output directory.

## Immutable source and complete grid

F1 imports and hash-verifies the five-model outcome-free freeze
`ijds-credit-risk-controls-2026-07-13-v1b`. It uses only its frozen:

- 640,543-row score frame, which contains no primary-OOT outcome column;
- historical conformal-fit audit, including only labels available for fitting;
- residual recipes and fixed 2011 score-taxonomy edges.

The grid is exactly

`5 learners x 8 windows x 5 score strata x 2 labels = 400 thresholds`.

All five learner specifications and all eight pre-existing six-month residual
windows are retained. The score stratum is assigned with each learner's frozen
five-bin taxonomy. Alpha remains 0.10. No score, learner, calibrator, taxonomy,
window, fit row, or label-completion rule is changed.

The eight windows overlap and the 40 learner--window summaries share the same
target panel. They are dependent complete specifications, not 40 replications
or multiplicative evidence.

F1 reconciles every historical fit score numerically within `5e-14` and every
ID, issue date, stratum, marginal interval, marginal fit-coverage indicator,
and marginal group count to the frozen sources before fitting a label-specific
threshold. The hash-locked score frame, not the audit copy, is canonical for
the new residual order statistic. Its persisted
threshold table is aggregate: it contains no loan ID or row-level label.

## Exact class-conditional threshold

For historical conformal-fit rows with score stratum `g` and observed label
`y`, let

`R_i(y) = |y - p_i|` and `n_gy = #{i: G_i=g, Y_i=y}`.

The rank is

`k_gy = ceil((n_gy + 1) * (1 - alpha))`.

If `k_gy <= n_gy`, the threshold `q_gy` is the `k_gy`-th order statistic of
the residuals. If `k_gy = n_gy + 1`, `q_gy = +infinity`; the rank is never
clipped to `n_gy`. Empty `(g,y)` cells stop the run.

For a candidate with frozen score `p` and stratum `g`, E1 constructs the
discrete prediction set directly as

`S(p,g) = {0: p <= q_g0} union {1: 1-p <= q_g1}`.

This need not be representable as the intersection of one symmetric continuous
interval with `{0,1}`. Empty, `{0}`, `{1}`, and `{0,1}` sets are all retained.

Under exchangeability within each `(G,Y)` cell, this is the standard
label-Mondrian finite-sample construction. The empirical analysis does not
assume or claim that this conditional exchangeability transports from the
2012 fitting windows to the 2016--2017 target period.

## Evaluation endpoint and complete reporting

E1 imports the hash-locked F1 thresholds, the same frozen candidate scores and
recipes, and the active reason-audited six-month endpoint at September 30,
2020. Candidate membership remains status-independent: all 376,890 primary-OOT
loans from April 2016 through June 2017 enter every learner-window cell. The
expected census is 364,814 resolved and 12,076 unresolved, with 307,842
resolved nondefaults and 56,972 resolved defaults. Partial ID joins stop E1.

The primary diagnostic table reports all
`5 learners x 8 windows x 5 score strata x 2 labels = 400` target categories.
For each `(learner, window, G, Y)` category it retains the fitted threshold,
fit count and rank; candidate, resolved-label, covered-label, and unresolved
counts; resolved-label coverage; sharp all-candidate conditional-coverage
bounds; sharp class-prevalence bounds within the score stratum; and whether
the sharp coverage upper endpoint is below 0.90. These 400 rows are necessary
because aggregation across score strata can hide offsetting category failures.
If a target category is empty under every admissible completion, its
conditional coverage is explicitly marked undefined rather than assigned a
numeric value.
They are descriptive identification diagnostics, not 400 unadjusted hypothesis
tests; V1 applies no inferential multiplicity procedure to them.

Every category is classified exhaustively relative to 0.90 as `robust
shortfall` (`upper < 0.90`), `robust at-or-above nominal` (`lower >= 0.90`),
`crosses nominal`, or `undefined`. The active marginal recipe is reported
side by side with the label-Mondrian recipe at all three reporting levels.
Resolved-panel and outcome-free set-geometry differences are direct; V1 does
not subtract separately optimized sharp endpoints and call the result a sharp
method difference.

A second complete table reports all
`5 learners x 8 windows x 5 score strata = 200` target strata. It gives the
sharp class-0-minus-class-1 coverage-gap interval within each stratum under
one common completion of that stratum's unresolved labels, together with its
witness class counts, sharp marginal coverage bounds, and set geometry. These are likewise descriptive
identification bounds, not significance tests.

Every one of the 40 learner-window summary cells also reports:

- threshold and fit-count details for all ten `(stratum,label)` cells;
- sharp all-candidate marginal coverage bounds;
- resolved marginal, label-0, and label-1 coverage;
- sharp all-candidate label-0 and label-1 coverage-ratio bounds;
- the sharp label-0-minus-label-1 coverage-gap interval under one common
  completion of unresolved outcomes;
- `AvgC`, `OneC`, and the empty, `{0}`, `{1}`, and `{0,1}` counts and shares;
- the number of infinite thresholds; and
- exact reconciliation of the original marginal recipe to the active coverage
  and conformal-set diagnostic artifacts.

## Sharp identification formulas

For candidate `i`, let `C_i(y)=1{y in S_i}`. Resolved labels remain fixed. An
unresolved row contributes `min(C_i(0),C_i(1))` to the marginal lower covered
count and `max(C_i(0),C_i(1))` to the upper covered count. These loan-wise
extrema give the sharp marginal coverage interval.

For one target class `y`, let `A_y` and `B_y` be the covered and total resolved
class-`y` counts. Let `U_y^0` and `U_y^1` be the unresolved counts with
`C_i(y)=0` and `C_i(y)=1`. The sharp class-specific ratio bounds are

`A_y / (B_y + U_y^0)` and
`(A_y + U_y^1) / (B_y + U_y^1)`.

These displayed formulas assume `B_y>0`, which holds in every active reporting
cell. In a generic cell with `B_y=0`, class coverage is defined only for
completions assigning at least one row to class `y`; `0/0` is not a coverage
endpoint.

The two class-ratio endpoints may use different completions. E1 therefore does
not obtain a gap by subtracting those marginal intervals. For the class-0 minus
class-1 gap it assigns every unresolved row once. Conditional on exactly `m`
unresolved labels assigned to class 1, denominators are fixed and the objective
is linear in the four set-membership types `(C_i(0),C_i(1))`. E1 takes the
`m` smallest or largest exact type weights and enumerates every integer
`m` satisfying `B_1+m>0` and `B_0+U-m>0`. Because both resolved class counts
are positive in every active cell, this admissible set equals `m=0,...,U`
there. This yields the sharp common-completion gap endpoints and their
class-1-count witnesses. Synthetic tests enumerate all binary completions and
must reconcile both endpoints exactly.

These intervals are finite-archive identification bounds. They are not
confidence intervals, missing-at-random estimates, or guarantees for latent
class prevalence.

## Baseline reconciliation

Before interpreting label-Mondrian output, E1 reconstructs the original
marginal recipe from the same frozen scores and recipes. For every learner and
window it must match the active references within absolute and relative
tolerance `5e-14` for:

- sharp lower and upper candidate coverage;
- resolved marginal, label-0, and label-1 coverage;
- `AvgC`, `OneC`, and all four set shares; and
- mean clipped-interval width.

Any mismatch stops the evaluation. This reconciliation validates the lineage;
it does not make the new method a selected replacement for the active recipe.

## Stop and interpretation rules

1. Stop if a source descriptor, run identity, fit ID, score, issue date,
   marginal recipe, stratum, group count, or historical coverage indicator
   fails reconciliation.
2. Stop F1 if any evaluation outcome column reaches the score frame or if any
   `(learner,window,stratum,label)` cell is missing.
3. Stop E1 unless the F1 freeze, execution receipt, and threshold artifact have
   exact predeclared path, byte count, SHA-256, protocol tag, and protocol
   commit, and the receipt points back to the same freeze descriptor.
4. Stop on a changed issue-month set, candidate census, endpoint census,
   partial ID join, nonbinary resolved label, incomplete 40-cell grid, failed
   set partition, reversed bound, or failed baseline reconciliation.
5. Report all 400 thresholds and all 40 evaluations. Do not select a learner,
   window, stratum, class, or result after seeing outcomes.
6. If any class-specific or marginal target coverage fails, report the complete
   mixed result. Do not widen, pool, retaxonomize, or recalibrate after E1.
7. A favorable resolved-label balance does not establish all-candidate
   label-conditional validity. Sharp ratio bounds and the common-completion gap
   must remain visible.
8. All 400 target categories and 200 within-stratum gap rows remain visible; a
   favorable class aggregate may not substitute for its score-stratified rows.
9. No result authorizes selected-set or funded-set validity, latent-PD
   intervals, a fairness conclusion, a model winner, a policy winner, causal
   interpretation, prospective confirmation, or deployment.
9. Do not execute a protected DVC stage, modify `EXTRACTION_MANIFEST.json`, or
   register the lineage in the manuscript/evidence builder before complete
   scientific review of E1.
