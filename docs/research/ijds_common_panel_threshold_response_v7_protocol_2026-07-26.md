# Common-Panel Threshold-Response V7 Audit Specification

Prospective eligible run tag:
`ijds-common-panel-threshold-response-2026-07-26-v7`

Status: **retrospectively specified after inspection; execution requires a new
clean tagged commit**

This protocol was written after the archive, the W7--W8 CatBoost stratum-2
crossing, the V6 candidate replay, and the common-panel identity of the frozen
score taxonomy had been inspected. It is not preregistration, confirmation, or
an inferential test. It freezes an exhaustive deterministic replay and its stop
rules before the first eligible V7 execution.

## 1. Question and scope

For every adjacent pair of the eight frozen residual-calibration windows, apply
both fitted thresholds to one fixed target panel and measure the exact change in
binary-set coverage. Report all

`5 learners x 5 score strata x 7 adjacent transitions = 175`

stratum contrasts and all

`5 learners x 7 adjacent transitions = 35`

learner-level aggregates. No learner, stratum, window pair, sign, magnitude, or
outcome completion is selected after evaluation. W7--W8 CatBoost stratum 2 is
retained only as the previously disclosed retrospective illustration and must
always appear with the complete census.

This audit does not refit a model, change a score taxonomy, reoptimize a
portfolio, test exchangeability, transfer conformal validity through time, or
establish a selected/funded-set guarantee.

## 2. Frozen sources and common-panel contract

The run must hash-bind and cross-reconcile:

- the active V5 endpoint configuration and raw LendingClub archive;
- the five-learner outcome-free score freeze, score table, residual recipes,
  and residual-fit audit;
- the active temporal-coverage table; and
- the active exchangeability stratum table and its summary.

The target contract requires, within each learner and score stratum, exactly the
same candidate IDs, score values, score-bin assignments, endpoint definition,
and normalization for both thresholds. The five-group score edges must be
identical across W1--W8. Outcomes are joined once, one-to-one, after the frozen
score panel is verified. The expected primary panel is 376,890 unique IDs:
364,814 resolved (307,842 nondefaults and 56,972 defaults) and 12,076 unresolved.

The run records global and learner--stratum SHA-256 digests of sorted IDs, score
vectors, bin edges, and assignments. It reconciles every learner--window--stratum
count, score range, threshold, resolved coverage, and sharp marginal coverage
bound against the frozen 200-row stratum table. A path is not provenance without
its byte count and SHA-256.

## 3. Temporal signed response

For target loan `i` in learner `l`, stratum `g`, and adjacent windows
`j -> j+1`, let `p_i` be its single frozen score, `c_from` and `c_to` the two
frozen residual thresholds, and

```
d0_i = 1{p_i <= c_to} - 1{p_i <= c_from}
d1_i = 1{p_i >= 1-c_to} - 1{p_i >= 1-c_from}.
```

The inequalities are part of the contract and remain unchanged in the presence
of ties. For the resolved set `R_g`, with observed binary outcome `Y_i`, record
the integer numerator

`A_R = sum_{i in R_g} dY_i`

and the resolved-panel response `DeltaCov_R=A_R/R_g`. If `R_g=0` in a future
replay, retain the row, mark the rate undefined, and continue to identify the
all-candidate bounds; never encode an undefined conditional rate as zero.

The response is temporal and signed. Do not divide it by `c_to-c_from`, fit a
slope, or imply continuity.

## 4. Exact crossed-band identity

Let `c_L=min(c_from,c_to)`, `c_H=max(c_from,c_to)`, and
`s=sign(c_to-c_from)`. For resolved outcomes, the unsigned crossed-band count is

```
B_R = #{Y=0, c_L < p <= c_H}
    + #{Y=1, 1-c_H <= p < 1-c_L}.
```

The run must reconcile the integer identity `A_R=s*B_R` exactly, including the
two class contributions. If the thresholds are equal, every contribution is
zero. A capped threshold `c=1` is allowed for this identity even though its
calibration phase regime is undefined.

The identity concerns target mass in crossed bands. Threshold distance or
continuous interval-width change is not a coverage bound.

## 5. Sharp common-completion identification

For each unresolved target loan, its two attainable temporal contributions are
`d0_i` and `d1_i`. One shared binary completion must be used for both thresholds.
The sharp all-candidate endpoints are

```
DeltaCov_L = (A_R + sum_U min(d0_i,d1_i)) / N_g
DeltaCov_U = (A_R + sum_U max(d0_i,d1_i)) / N_g.
```

Their exact width is `sum_U |d1_i-d0_i|/N_g`. These endpoints are sharp over
unrestricted loan-wise binary completions because every unresolved outcome is
assigned once. They are not obtained by subtracting separately extremized
coverage intervals. The resolved rate uses denominator `R_g`; the sharp
all-candidate interval uses `N_g`, so the two quantities must remain labeled and
must not be compared as though they shared a denominator.

## 6. Learner-level aggregation

For each learner and adjacent transition, sum the five stratum integer
numerators, unresolved minima, and unresolved maxima before dividing by the
common resolved or all-candidate census. Do not average stratum rates. The five
strata must partition the learner panel exactly, so the sum of stratum sharp
endpoints remains sharp. There is no learner-level scalar threshold distance.

## 7. Required outputs

The immutable output generation contains:

1. `adjacent_stratum_threshold_response.csv`, exactly 175 rows;
2. `adjacent_learner_threshold_response.csv`, exactly 35 rows;
3. a JSON summary with census, exact-identity, common-panel, tie, hash, and
   illustrative W7--W8 reconciliation fields; and
4. an execution receipt binding protocol, config, runner, reusable module,
   transitive scientific helpers, `uv.lock`, environment, Git commit/tag, every
   source descriptor, and every output descriptor.

Output names must be plain unique basenames, validated case-insensitively before
any directory is created. Atomic writes may not escape the fresh run directory.

## 8. Stop rules

Stop without output promotion if any of the following occurs:

- HEAD is dirty, the declared protocol tag is absent, or its commit differs;
- a source path, byte count, SHA-256, or nested descriptor differs;
- an ID is missing/duplicated, an outcome join is incomplete, or the endpoint
  census/issue-month set changes;
- a score, threshold, outcome, group key, or edge leaves its domain;
- five-group edges or assignments differ across windows;
- the 200 threshold cells, 175 adjacent cells, or 35 aggregates are incomplete
  or duplicated;
- target IDs/scores/strata differ between either side of a contrast;
- any source reconciliation, integer coverage identity, sharp-bound order,
  width identity, or pooled numerator reconciliation fails; or
- a pre-existing output directory or path-escape attempt is encountered.

Every fail-closed branch requires a focused test. An aborted or development run
is provenance only and cannot be narrowed after inspection.

## 9. Permitted interpretation

V7 may establish exact finite-archive bookkeeping on a common fixed panel and
show whether a large threshold step corresponds to a small or large realized
resolved response and sharp common-completion interval. It may not establish
causality, prospective validity, continuity, a universal prevalence phase,
independent replication, a model/window/stratum winner, a temporal monitoring
test, or selected/funded-set validity.

Permitted disclosure for the highlighted pair is:

> The CatBoost stratum-2 W7--W8 pair and earlier candidate outputs were
> inspected before this protocol. V7 is an exhaustive deterministic
> retrospective replay, not preregistration or confirmation. W7--W8 is retained
> solely as the previously disclosed illustration alongside all 175 adjacent
> pairs; it is neither a winner, an extreme, nor an inferential test.

