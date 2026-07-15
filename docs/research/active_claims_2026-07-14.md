# CRPTO Active IJDS Claim Registry - 2026-07-14

This is the sole claim registry for the active IJDS manuscript. Numerical
statements must be traceable to
`reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json`, whose inputs are
hash-locked by `configs/ijds_active_evidence_sources.yaml`. Earlier
fixed-taxonomy V1--V3, pool93, compact-v7, selected-policy, and all
pre-endpoint-correction evaluations are provenance only.

## Editorial Decision

- **GO:** one retrospective paper about identification at the interface of
  credit-risk prediction, binary conformal intervals, and constrained monthly
  allocation.
- **NO-GO:** model or policy superiority, selected-set conformal validity,
  causal effects, a universal guardrail direction, prospective confirmation,
  or deployment claims.
- The strongest result is negative but constructive: candidate coverage does
  not transport under five reported learner specifications, binary residual
  geometry changes near a prevalence threshold, and realized portfolio
  direction depends on the outcome-free ruler and coordinate used to define
  comparable decision stringency.
- No OOT outcome selects a learner, window, taxonomy, gamma, ruler, coordinate,
  cap, comparator, or policy.

## Active Lineages

### Binary geometry and exact point-cap audit

- Outcome-free freeze: `ijds-binary-geometry-frontier-v4-2026-07-12-v1`, tag
  `protocol/ijds-binary-geometry-frontier-v4-2026-07-12-v1`, commit
  `2f8a7606e4eb65aa3ae3701fb3af8d9a51c953cd`.
- Endpoint-corrected evaluation: `ijds-binary-geometry-frontier-v4-2026-07-14-v3`,
  tag `protocol/ijds-binary-geometry-frontier-v4-2026-07-14-v3`, commit
  `688f75dc4f285c75bc499c9e041dd30fb3acd70d`.
- V3 imports and verifies the V1 freeze. It changes the evaluation endpoint and
  sharp bounds, not frozen scores, residual recipes, supports, or allocations.

### Two-ruler diagnostic

- Outcome-free freeze: `ijds-normalized-objective-frontier-2026-07-13-v1c`, tag
  `protocol/ijds-normalized-objective-frontier-2026-07-13-v1c`.
- Endpoint-corrected evaluation: `ijds-normalized-objective-frontier-2026-07-14-v3`,
  tag `protocol/ijds-normalized-objective-frontier-2026-07-14-v3`, commit
  `a1ae516a6c9674686dba245cb275475073b298a0`.
- The freeze contains 6,240 solves and 622,455 funded rows. V3 reports 720
  monthly contrasts, 48 window contrasts, and 144 metric-direction cells.

### Credit-risk controls and data audits

- Frozen five-model scores: `ijds-credit-risk-controls-2026-07-13-v1b`, tag
  `protocol/ijds-credit-risk-controls-2026-07-13-v1b`.
- Endpoint-corrected evaluation: `ijds-credit-risk-controls-2026-07-14-v3`, tag
  `protocol/ijds-credit-risk-controls-2026-07-14-v3`, commit
  `688f75dc4f285c75bc499c9e041dd30fb3acd70d`.
- Full archive audit: `ijds-raw-data-contract-2026-07-14-v2`.
- Label-lag sensitivity: `ijds-label-lag-sensitivity-2026-07-14-v1`.
- Evaluated-cap solver audit: `ijds-policy-support-tie-audit-2026-07-12-v1`.

## Research Object

- Raw archive: 2,925,493 rows, 2,925,492 valid dated loans, 142 columns,
  2,060,077 36-month contracts, and 865,415 60-month contracts.
- Active status-independent design: all 640,543 eligible 36-month loans under
  the declared dates, maturity, schema, and origination-observability rules.
  This is not a computational sample.
- PD development: 17,433 rows. Probability calibration/taxonomy: 14,101 rows.
  Residual pool: 49,007 rows. Outcome-free policy development: 94,885 rows.
- Primary OOT: 376,890 candidates in 15 monthly menus from April 2016 through
  June 2017. Censored extension: 88,227 candidates from July--September 2017.
- Primary endpoint census: 364,814 resolved and 12,076 unresolved candidates.
- The distributed archive is not a verified September 2020 point-in-time
  snapshot. Terminal status is conservatively reconstructed as observable by
  September 30, 2020; terminal statuses whose reconstructed availability is
  later remain unresolved.
- The raw file contains 36,485 last-payment dates and 40,214 last-credit-pull
  dates after the evaluation cutoff. These facts prohibit calling the file a
  contemporaneous administrative snapshot.
- Candidate membership never uses status. Allocations are frozen before the
  endpoint panel is joined, and partial ID joins fail.

## Prediction and Conformal Object

- Primary score: CatBoost followed by a separate 2011 Platt map. Only this
  score enters portfolio optimization.
- Coverage-only controls: numeric logistic, domain-constrained monotonic
  CatBoost, platform-signal WOE/IV, and a pricing-excluded application WOE/IV
  scorecard. Each has a separately fitted Platt map and fixed 2011 taxonomy.
- The two original V4 specifications and three later credit-risk controls form
  a complete reported coverage audit, not a model contest. Every retained
  evaluation was protocol-locked before its corresponding outcome join, but
  the inspected archive means this is not preregistration or an untouched
  holdout. OOT AUC, Brier, calibration, IV, and PSI are descriptive.
- Five score strata are fixed separately from 2011 scores. All eight eligible
  consecutive six-month residual windows beginning January--August 2012 are
  reported. The windows overlap and are not independent replications.
- At alpha 0.10, the interval
  `[max(0,p-c_g), min(1,p+c_g)]` predicts the observed binary endpoint. It is
  neither a confidence interval for individual latent PD nor the convex hull of
  a discrete prediction set.
- Exact all-candidate sharp coverage bounds are
  `1 - mean(miss_high)` and `1 - mean(miss_low)`. Singleton, empty, and
  `{0,1}` prediction sets are handled loan by loan.

## Active Exact Statements

1. **Positive-affine cap equivalence.** Under a binding budget, a globally
   positive-affine score admits an exact translated cap. The empirical upper
   score is not globally affine in the point score.
2. **Normalized-ruler affine invariance.** A positive-affine transformation
   preserves normalized-score coordinates; this does not equalize plug-in
   opportunity cost or realized outcomes for non-affine scores.
3. **Same-cap nesting.** Because the upper score is no smaller than the point
   score, the copied-cap point feasible set weakly contains the guardrail set.
   This orders only the optimized plug-in objective.
4. **C2 plug-in dominance.** Matching the frozen guardrail allocation's funded
   point-score moment makes that allocation feasible for the point LP. It does
   not order realized payoff, default, or miscoverage.
5. **Constant-score binary threshold discontinuity.** For fixed `0 <= p < 1/2`, the
   population absolute-residual quantile changes from `p` to `1-p` when binary
   prevalence crosses alpha. Empirical scores vary, so this is a mechanism, not
   a finite-sample proof.
6. **Binary miscoverage identity.** Miscoverage is
   `1{Y=0,l>0} + 1{Y=1,u<1}`.
7. **Sharp common-outcome bounds.** Candidate and fixed-allocation bounds use
   binary loan-wise extrema; paired-policy bounds optimize one common unresolved
   endpoint assignment over the funded union.
8. **Basis-endpoint sufficiency.** On each LP basis, allocations are affine in
   the cap and the sharp contrast endpoints are concave/convex. Basis endpoints
   suffice for extrema over the declared point-cap support up to solver
   tolerance.
9. **Declared comparator envelope.** A support envelope is partial
   identification over that declared support, not a confidence interval, a
   causal identified set, or a universal comparator claim.

## Coverage and Geometry Evidence

Under the declared six-month endpoint contract, all eight all-candidate
coverage upper bounds are below 0.90 for every model:

| Specification | Lowest lower bound | Highest upper bound | OOT AUC | OOT Brier |
|---|---:|---:|---:|---:|
| CatBoost | 0.842485 | 0.882597 | 0.640605 | 0.129878 |
| Numeric logistic | 0.850031 | 0.896222 | 0.642045 | 0.128846 |
| Monotonic CatBoost | 0.848396 | 0.886489 | 0.651954 | 0.128613 |
| Platform-signal WOE/IV | 0.848908 | 0.894908 | 0.633066 | 0.129485 |
| Pricing-excluded application WOE/IV | 0.852013 | 0.897726 | 0.612939 | 0.130190 |

- Mean calibration error is negative for all five models (-0.047109 to
  -0.028923), and every calibration slope is below one (0.543210--0.918655).
- All 45 OptBinning fits are optimal. The WOE/IV and monotonic specifications
  challenge model-class and platform-pricing explanations; they are not the
  paper's methodological novelty and cannot promote a model.
- Two active raw features have declared coverage exceptions:
  `mths_since_last_delinq` is structurally nullable and
  `pub_rec_bankruptcies` has partial legacy support. Their deterministic
  missing-value conventions must be disclosed; no missingness-robustness claim
  is active without a dedicated sensitivity.
- In CatBoost stratum 2, prevalence changes from 0.101703 in W7 to 0.097147 in
  W8; the fitted residual quantile changes from 0.888435 to 0.111801 and mean
  OOT width from 0.984263 to 0.207631.
- The W7--W8 threshold crossing persists for the predeclared 0-, 3-, and
  6-month charged-off reporting lags, each retaining more than 99% in every
  fitting month. It disappears at 8 and 12 months, which fail the locked
  retention rule. This is sensitivity evidence, not a causal attribution.
- W8 stratum-2 coverage remains bounded by [0.822536, 0.854707]. Narrower
  intervals do not restore transport.

## Decision and Comparator Evidence

The frozen contrast is gamma 1 minus gamma 0. The objective-matched ruler holds
the common plug-in objective floor fixed; the normalized-score ruler holds a
positive-affine-invariant relative score relaxation fixed but does not equalize
opportunity cost.

| Ruler / coordinate | Payoff hull (USD) | Default hull (pp) | Miscoverage hull (pp) |
|---|---:|---:|---:|
| Objective matched .25 | [-9,134.34, 5,603.66] | [-0.0068, 0.1265] | [-0.0068, 0.1265] |
| Objective matched .50 | [-82,616.17, -27,958.37] | [0.4572, 1.0973] | [1.0154, 1.9321] |
| Objective matched .75 | [-179,484.66, 92,558.18] | [-0.4352, 2.4948] | [1.3252, 4.1848] |
| Normalized score .25 | [-626,374.61, -195,967.63] | [8.4829, 13.4246] | [8.3910, 13.7536] |
| Normalized score .50 | [-259,658.18, -54,025.82] | [3.2214, 6.5637] | [2.1070, 5.2142] |
| Normalized score .75 | [-135,781.22, 9,812.59] | [1.4392, 2.3807] | [0.3447, 1.6991] |

Endpoint reconstruction reclassified 525 archive-terminal candidates whose
modeled availability date followed the cutoff. V2 had 365,339 resolved and
11,551 unresolved primary candidates; active V3 has 364,814 resolved and
12,076 unresolved. The required direction reconciliation is:

| Quantity | V2 | V3 |
|---|---:|---:|
| Objective-matched .25 payoff (higher/lower/cross) | 8/0/0 | 0/0/8 |
| Objective-matched .25 default (lower/higher/cross) | 8/0/0 | 0/0/8 |
| Objective-matched .25 miscoverage (lower/higher/cross) | 8/0/0 | 0/0/8 |
| Normalized .75 payoff (higher/lower/cross) | 0/8/0 | 0/7/1 |
| All payoff cells (higher/lower/cross) | 8/33/7 | 0/32/16 |
| All default cells (lower/higher/cross) | 8/33/7 | 0/33/15 |
| All miscoverage cells (lower/higher/cross) | 8/40/0 | 0/40/8 |

V2 is immutable provenance and V3 is the active endpoint; no direction from
either endpoint version is promoted.

- Objective-matched .25 crosses zero for all three metrics in all eight
  windows. Its repeated allocation remains identical across windows, but the
  12,076 unresolved endpoints eliminate the earlier favorable point claim.
- Objective-matched .50 is adverse in all eight windows. At .75, payoff and
  default cross zero in seven windows and are adverse in one; miscoverage is
  adverse in all eight.
- Normalized .25 and .50 are adverse in all eight windows. At normalized .75,
  default and miscoverage are adverse in all eight; payoff is adverse in seven
  and crosses zero in one.
- Across all 48 cells, payoff is lower in 32 and crosses zero in 16; default is
  higher in 33 and crosses zero in 15; miscoverage is higher in 40 and crosses
  zero in 8. No opposite one-sided direction survives.
- Broad stress `[0.05,0.12]` places zero in all 216 exact envelopes.
- Over development-admissible support, terminal default crosses zero in 72/72
  cells, payoff is lower in 6 and crosses in 66, and miscoverage is higher in
  27 and crosses in 45. All 27 W8 envelopes cross zero.
- The evaluated-cap audit contains 7,297 point-cap rows. It finds no near-zero
  nonbasic reduced costs and no allocation sensitivity in 2,941 reversed-order
  reruns; maximum allocation distance is `1.45e-14`. This supports numerical
  stability at evaluated caps, not continuous-frontier uniqueness.

## Permitted Claims

- Under the declared six-month endpoint contract, candidate-level binary
  coverage fails after temporal transport before optimization for all five
  reported score specifications.
- Binary absolute-residual geometry is prevalence-sensitive.
- The score, ruler, and coordinate jointly define the portfolio comparison.
- Within the finite predeclared grid, direction is not invariant to ruler or
  coordinate and no endpoint has a universal realized-outcome ordering.
- Exact support envelopes quantify partial identification over declared
  outcome-free comparator supports.
- CRPTO remains one integrated ML--conformal--optimization object; its result is
  an audit of the handoff, not abandonment of any component.

## Forbidden Claims

- Policy, gamma, ruler, coordinate, learner, or window winner.
- Selected-set or funded-set conformal guarantee.
- Universal economic, default, or miscoverage dominance.
- A verified September 2020 archive snapshot.
- Causal, prospective, confirmatory, preregistered, deployment, or fair-lending
  conclusions.
- Standardized payoff as cash-flow return, IRR, or welfare.
- Independent replication counts from overlapping windows or repeated
  allocations.
- Continuous-frontier uniqueness or a universal comparator support.

## Pre-Freeze Boundary

Submission freeze is not active. Further work may improve code, sensitivity
analysis, exposition, and reproducibility, but it may not select results from
2016--2017 outcomes or rewrite protected historical artifacts. Any new
paper-facing run requires a predeclared protocol, immutable tag, explicit stop
rules, complete reporting, and a new versioned evidence source.
