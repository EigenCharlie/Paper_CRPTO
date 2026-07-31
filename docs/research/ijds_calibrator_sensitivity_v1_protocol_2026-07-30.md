# IJDS retrospective CatBoost calibrator sensitivity V1 protocol

**Date:** 2026-07-30
**Status:** retrospective protocol to be tagged before execution; no result is
active until both phases, transport gates, and promotion gates pass.

**Protocol tag P:** `protocol/ijds-calibrator-sensitivity-2026-07-30-v1`

**Phase-A source tag A:** `artifacts/ijds-calibrator-sensitivity-2026-07-30-v1-source`

**Phase-B protocol tag B:**
`protocol/ijds-calibrator-sensitivity-evaluation-2026-07-30-v1`

**Final evaluation tag C:** `artifacts/ijds-calibrator-sensitivity-2026-07-30-v1`

## 1. Question and scope

The active manuscript's primary probability score is the frozen CatBoost model
with a Platt map fitted on availability-safe 2011 labels. This protocol asks a
narrow robustness question:

> Does the complete-archive binary-set coverage conclusion change when the
> frozen CatBoost base score is mapped by Platt, isotonic, beta, or
> Venn--Abers calibration, while every method uses exactly the same loans,
> temporal windows, five score strata, endpoint, and unresolved-outcome
> treatment?

This is a retrospective sensitivity, not a preregistered comparison, a model
competition, or a search for a winning calibrator. No method or window may be
selected from 2016--2017 outcomes. All four methods, all eight windows, the
pooled target population, and all five common strata must be reported.

V1 does not run or modify portfolio optimization. A binary prediction set, an
IVAP multiprobability output, and the scalar Venn--Abers probability do not
identify the continuous probability endpoint required by the existing linear
portfolio objective.

## 2. Frozen inputs and common base score

The source is the active outcome-free V4 lineage:

- `scores.parquet`, 640,543 rows, including the frozen
  `pd_catboost_platt`;
- `catboost_platt.pkl`, the active one-margin Platt estimator;
- `residual_recipes.json`, including the eight canonical five-stratum
  CatBoost/Platt recipes;
- `residual_fit_audit.parquet`, which carries the availability-safe 2012
  residual-fit labels;
- the CatBoost model and V4 freeze, bound as lineage artifacts even though the
  score replay uses exact algebraic inversion;
- the raw archive with SHA-256
  `5878af2a088f8ab5214c9337289fb8b5eb6c6338fd3f417b6cdc18513dc6f35f`.

For active Platt probability \(p\), intercept \(a\), and positive slope \(b\),
the frozen raw margin and uncalibrated CatBoost probability are recovered as

\[
  m = \{\operatorname{logit}(p)-a\}/b,\qquad
  q_{\mathrm{raw}}=\operatorname{logit}^{-1}(m).
\]

Every source probability is strictly inside \((0,1)\). Applying the frozen
Platt map to the recovered margin must reproduce every stored probability to
absolute tolerance \(5\times10^{-14}\). No CatBoost model is refitted.

Only the 14,101 frozen 2011 probability-calibration IDs are retained from the
narrow raw-label scan. The same 14,077 availability-safe labels used by the
active Platt fit form the calibrator-fit population. This is a retrospective
archive that was previously inspected: the CSV reader necessarily reads
chunks containing status values outside 2011 before applying the row
predicate. Phase A therefore claims logical target-outcome nonuse, not a
physical lockbox. No primary-OOT outcome is retained, passed to a calibrator,
passed to a residual recipe, or evaluated in Phase A. The freeze records the
exact three fitting columns and the `probability_calibration` split identity.
Before fitting any alternative map, the ordered 14,077-row panel must reproduce
the active V4 Platt audit exactly: 12,602 nondefaults, 1,475 defaults, and the
six locked fields `rows`, default rate, ROC AUC, Brier score, log loss, and
ten-bin ECE with zero numerical tolerance. The ordered vectors are locked as
follows:

- ID SHA-256:
  `81045766e24eb4039c922437a92fb7e37c2715bbe67c5fd95cfd0386d07563de`;
- binary-label float64 SHA-256:
  `24e74d0ef1f29c60ee9b45c75741eeecb7623f8d7036a6219684df39260237c4`;
- frozen-Platt-probability float64 SHA-256:
  `3ce39046141dec723ffe080d3eb41857bbcb1f4f0e8d4a915472380a758daf57`.

## 3. Locked calibrator family

The four maps are:

1. **Platt:** the already frozen active `LogisticRegression`; it is not
   refitted or replaced.
2. **Isotonic:** `sklearn.isotonic.IsotonicRegression`, increasing, output
   clipped outside the fitted domain, and bounded to \([0,1]\).
3. **Beta:** `betacal.BetaCalibration(parameters="abm")`.
4. **Venn--Abers:** `venn_abers.VennAbers(setting="classification")`, with
   `precision=None`.

The environment pins `betacal==1.1.0` and `venn-abers==1.5.3`.

For Venn--Abers, the point score in the four-method comparison is the standard
positive-class IVAP scalarization

\[
  p^\prime = \frac{p_1}{1-p_0+p_1}.
\]

The package-returned \(p_0,p_1\) values are reconstructable from the frozen
map, hash-bound in full, and reported through compact \(p_1-p_0\) gap
summaries. The runner verifies
\(0\le p_0\le p^\prime\le p_1\le1\) and the formula above. This scalarization
does not itself inherit a multiprobability validity guarantee, is not a
latent-PD interval, and is not authorized as a portfolio endpoint. The
historical arithmetic midpoint \((p_0+p_1)/2\) is not a V1 method.

The Platt class order must be exactly `[0, 1]`. The beta map must have finite
parameters with nonnegative \(a,b\), and its internal logistic solver must stop
strictly before `max_iter`. The fitted Venn--Abers state tables and knots must
match the shapes and domains returned by package version 1.5.3. All four fitted
maps must be finite, lie in \([0,1]\), and be nondecreasing on the complete
sorted `q_raw` vector to numerical tolerance \(10^{-14}\). Every application
also verifies that its supplied `q_raw` equals
\(\operatorname{logit}^{-1}(m)\) to \(10^{-15}\).
Same-sample 2011 Brier, log-loss, AUC, and ECE values are descriptive fit
diagnostics only and cannot rank or select calibrators.

## 4. One common, outcome-free taxonomy

Method-specific quantile strata are forbidden because they would confound the
calibration map with membership changes, and isotonic/Venn--Abers ties could
collapse quantile edges.

The active five-group 2011 Platt edges are transformed through the exact
inverse above into the `q_raw` scale. They are not re-estimated as raw-score
quantiles: empirical linear interpolation does not commute with a nonlinear
monotone transform.

The resulting common edges must:

- be finite and strictly increasing;
- yield zero full-panel assignment changes relative to the active Platt
  taxonomy;
- reproduce the active 2011 group census;
- yield the same group membership for every calibrator;
- reproduce, for the Platt branch in all eight windows, the active assignments,
  group counts, finite-sample ranks, raw ranks, and residual quantiles. Integer
  fields and assignments are exact; residual quantiles have tolerance
  \(10^{-12}\).

For method \(c\), window \(w\), and common group \(g\), the residual is
\(\lvert Y-p_c\rvert\), and the finite-sample rank remains
\[
 k_{cwg}=\left\lceil(n_{wg}+1)(1-\alpha)\right\rceil,\qquad \alpha=0.10.
\]
Only the residual values change with the calibrator; \(n_{wg}\), membership,
and ranks cannot change. Every canonical group must retain at least 1,000
rows.

## 5. Phase A: target-outcome-nonuse freeze

Phase A runs only from a clean HEAD carrying annotated tag P. It is
retrospective and reads the locked archive, but it retains and uses labels only
for the declared 2011 calibration IDs. Outputs are immutable direct children
of the configured experiment roots:

- fitted calibrator-family pickle;
- transparent common-taxonomy JSON;
- complete 4 calibrators × 8 windows × 5 groups residual-recipe JSON;
- 160-row recipe audit;
- descriptive 2011 calibration-fit diagnostics;
- compact outcome-free geometry for every declared role;
- a protocol freeze and execution receipt.

No 640,543-row duplicate score artifact is written. Instead, the freeze
records deterministic hashes of the ordered ID vector, `q_raw`, all four
probability vectors, and both columns of the Venn--Abers multiprobability
pair. This keeps the Git
artifact compact while allowing exact Phase-B reconstruction from the
hash-bound V4 scores and fitted maps.

The Phase-A freeze and receipt are committed as the single direct child A of P,
without modifying the pending Phase-B config. A receives annotated source tag
A. A new single direct child B then replaces only the pending fields in the
Phase-B config with A's exact descriptors and commit and adds
`ijds_calibrator_sensitivity_v1_evaluation_lock_2026-07-30.md`, recording those
identities and the still-locked interpretation. B receives the annotated
Phase-B protocol tag. This extra commit is necessary because a Git commit
cannot contain its own SHA. Any extra parent, intervening commit, lightweight
tag, dirty worktree, descriptor mismatch, or vector-hash mismatch fails
closed.

The commit diffs are themselves gates, not instructions left to operator
judgment. Relative to P, A may add exactly the eight declared Phase-A files:
the three Parquet tables, three fitted-map/taxonomy/recipe artifacts, freeze,
and receipt. Relative to A, B may change exactly the pending Phase-B YAML and
add the evaluation-lock note. Any other path in either commit fails closed.

## 6. Phase B: endpoint evaluation

Before loading target outcomes, Phase B must:

1. run from clean annotated Phase-B protocol tag B;
2. prove A is the single direct child of P and B is the single direct child of
   A;
3. verify the exact Phase-A freeze, receipt, and every compact artifact;
4. reconstruct the complete score vectors and exactly match every frozen
   vector hash.

Only after those gates pass may it load the active V5 endpoint:

- 376,890 primary-OOT loans;
- 364,814 resolved and 12,076 unresolved;
- 307,842 resolved \(Y=0\) and 56,972 resolved \(Y=1\);
- the same 15 April 2016--June 2017 issue months and V5 availability rule.

The complete primary table contains

\[
4\text{ methods}\times8\text{ windows}\times
(1\text{ pooled}+5\text{ strata})=192
\]

cells. The compact overall table contains 32 cells. For each cell the runner
reports:

- resolved empirical coverage;
- sharp all-candidate coverage lower and upper bounds under arbitrary binary
  completion of unresolved outcomes;
- resolved \(Y=0\) and \(Y=1\) coverage, as descriptions rather than
  conditional guarantees;
- mean interval width and fixed width quantiles;
- average binary-set cardinality, singleton share, and the complete
  empty/\(\{0\}\)/\(\{1\}\)/\(\{0,1\}\) partition;
- target and residual-fit score ranges and range-exceedance counts.

All six unordered method pairs are evaluated over all eight windows and six
scopes, producing 288 cells. Pairwise coverage-difference bounds use the same
loan-wise unresolved completion for both methods. Subtracting separately
extremized marginal bounds is forbidden.

The 48 Platt rows (eight windows × six scopes) must reproduce the active V5
coverage and geometry table, including counts, ranks-derived quantities, set
partition, widths, and score-range fields, to \(10^{-12}\).

## 7. Stop rules and interpretation

Execution stops without paper-facing evidence if any of the following occurs:

- a source descriptor, raw hash, Git tag, direct-child relation, environment
  dependency, or implementation hash changes;
- the 2011 or V5 endpoint census changes;
- Platt inversion, common-taxonomy assignment, eight-recipe replay, vector
  replay, or V5 baseline reconciliation fails;
- any calibrator output is invalid/nonmonotone or the IVAP formula/pair-domain
  checks fail;
- any expected recipe/evaluation/pairwise cell is absent, duplicated, empty,
  or nonfinite where defined;
- any protected stage or protected artifact is invoked or written.

Interpretation is fixed before outcomes:

- if all 32 overall upper coverage bounds are below 0.90, the strongest
  permitted statement is that the **complete-archive shortfall is robust
  within this closed four-calibrator family under the common `q_raw`
  taxonomy**;
- if any upper bound reaches 0.90, the identified shortfall is not established
  uniformly across the closed calibrator family. The cells at or above 0.90
  must be reported, but this does not by itself establish that true coverage
  is calibrator-dependent;
- neither outcome refutes conformal theory, establishes sampling uncertainty,
  supplies a missing-at-random result, validates a selected/funded set, or
  chooses a best calibrator;
- efficiency and pairwise differences are reported completely and cannot be
  used for post-outcome promotion.

V1 remains quarantined until the final output commit C is committed as the
single direct child of B, receives its annotated artifact tag, passes the
ordinary repository gates,
and is explicitly added to the active source registry and claim ledger.

## 8. Operational budget

V1 trains no CatBoost model and solves no optimization problem. Its dominant
cost is hashing/scanning the 1.77 GB raw archive once per phase and applying
four vectorized maps. The pre-run estimate is 10--25 minutes and roughly
2--5 GiB peak memory on the reference Windows workstation. If an implementation
preflight revises the estimate above 30 minutes, execution must stop until an
atomic heartbeat/checkpoint/resume contract is added; the current short-run
runner must not be used as an unobservable long-run worker.

## 9. Deferred portfolio question

No Phase-C portfolio run is authorized. A later protocol would have to
predeclare, before inspecting portfolio results:

- which scalar probability enters each payoff coefficient;
- how Venn--Abers multiprobabilities are embedded;
- a complete set-preserving continuous embedding family;
- both objective rulers, all coordinates, all declared gammas, and all
  structural scenarios;
- complete reporting and a no-winner interpretation.

That later decision should be made on scientific value after V1, not on
whether a calibrator produces a favorable result.
