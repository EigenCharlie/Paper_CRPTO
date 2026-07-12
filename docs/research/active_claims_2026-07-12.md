# CRPTO Active IJDS Claim Registry - 2026-07-12

This is the source of truth for the single IJDS manuscript. It supersedes the
2026-07-11 registry by adding the locked temporal-design sensitivity and by
correcting the semantics of the conformal endpoint and default score.

## Editorial Status

- **NO-GO:** a superiority, dominance, champion-policy, or deployment paper.
- **GO:** one retrospective IJDS paper about auditing temporal transport,
  comparator stringency, censoring, and operational constraints in a frozen
  predict-then-optimize system.
- All nine policies are co-primary. No OOT outcome selects a policy, residual
  window, taxonomy, seed, cap, LGD, or comparator.
- No policy winner is allowed.
- The superiority stop preceded the negative audit framing. The framing is an
  explicitly post-result secondary interpretation, not a preregistered or
  confirmatory success.
- The late residual-window protocol was locked before its own outcomes were
  evaluated, but it was motivated by the early audit. It is a design
  sensitivity and cannot promote either window by result.

The strongest contribution is an outcome-isolated comparator-sensitivity
audit for replacing a point score with a non-affine uncertainty score inside a
constrained optimizer. CRPTO returns coverage bounds, paired policy-contrast
intervals, and declared comparator envelopes. It does not return a selected
policy.

## Immutable Lineage

### Early outcome-free freeze

- Run: `ijds-fixed-taxonomy-c2-2026-07-11-v1`.
- Protocol tag: `protocol/ijds-fixed-taxonomy-c2-2026-07-11-v1`.
- Protocol commit: `4835cc18a0117a695f89f9da70a4e3af97663a27`.
- Freeze SHA-256:
  `93690082880ef4ff1375dcd5b26d2df79f80e6ebe09a6d83b7fd99a9abb4cfae`.
- The run completed 7,347 outcome-free solves and froze 718,925 funded rows.
  Its inefficient row-wise evaluator timed out after the freeze.

### Early reconciled evaluation

- Run: `ijds-fixed-taxonomy-c2-2026-07-11-v2`.
- Protocol tag: `protocol/ijds-fixed-taxonomy-c2-2026-07-11-v2`.
- Protocol commit: `a88839dfe14875fca2c02c43725291bc49d98611`.
- V2 verifies and imports the V1 outcome-free artifacts, performs one validated
  outcome join, and changes no prediction or allocation.

### Late temporal-design sensitivity

- Run: `ijds-fixed-taxonomy-c2-temporal-v3-2026-07-12-v1`.
- Protocol tag:
  `protocol/ijds-fixed-taxonomy-c2-temporal-v3-2026-07-12-v1`.
- Protocol commit: `c5ceab737ab3cda8aed7d3c1fd24a506418cfa35`.
- V3 completes 7,437 outcome-free solves and freezes 729,789 funded rows before
  its outcome join.
- V3 is not a result-based replacement for V2. Both windows must be reported.

The only active paper-facing manifest is
`reports/crpto/ijds_fixed_taxonomy_c2_evidence.json`.

## Research Object

- Raw rows scanned: 2,925,493.
- Contractual term: 36 months.
- Early design rows: 540,121.
- Late design rows: 625,576 because residual and policy-development windows
  are longer.
- Common OOT panel: 465,117 loans, comprising 376,890 primary candidates and
  88,227 censored-extension candidates.
- Primary decisions: 15 monthly menus, April 2016--June 2017, each with a fresh
  USD 1 million budget.
- Extension: July--September 2017, secondary only.
- Information cutoff: March 31, 2016.
- Administrative outcome snapshot: September 30, 2020.
- Fully Paid is 0; Charged Off is 1; exact Default and every nonterminal status
  are unresolved.
- Candidate membership never uses loan status. Outcomes are physically absent
  from prediction, policy, and comparator construction.
- The scientific terminal endpoint has 499,845 resolved and 40,276 unresolved
  rows. A receipt-only status diagnostic reports 500,019/40,102 because it
  counted 174 literal Default rows as resolved; no scientific result uses that
  diagnostic.

## Prediction And Conformal Object

- CatBoost uses 29 numeric and 9 categorical origination-time features.
- A logistic Platt map is fitted on 14,077 availability-safe 2011 labels.
- Five score strata are fixed from all 2011 Platt-scaled scores without using
  either residual-window outcome.
- The early residual recipe uses 14,948 availability-safe labels from 2012H1.
- The late recipe uses 33,909 availability-safe labels from July
  2012--January 2013 under the canonical six-month charged-off lag.
- Both use rank `ceil((n_g + 1) * (1 - alpha))` at `alpha=0.10`.
- The output `[max(0,p-c_g), min(1,p+c_g)]` is a clipped residual prediction
  interval for the observed binary outcome. Its upper endpoint is a decision
  score. It is not a confidence limit for latent individual PD and not the
  convex hull of a discrete conformal prediction set.
- `p` is a Platt-scaled default score. The optimized coefficient
  `(1-p)r-p*LGD` is a model-implied plug-in objective, not an asserted true
  conditional expectation.
- Taxonomies with 1, 2, 5, and 10 groups are closed diagnostics, not an OOT
  selection grid.
- Label lags 0, 3, 6, and 12 months are evaluated for the late five-group
  recipe only. This is not a full taxonomy-by-lag cross-product.

For canonical seed 42, Platt calibration has AUC 0.676327, Brier 0.090206, log
loss 0.316543, and ten-bin ECE 0.003273. Late policy development has ECE
0.003330; primary OOT has AUC 0.640848, Brier 0.130753, and ECE 0.048323; the
extension has ECE 0.091447. These are drift diagnostics, not a leaderboard.

## Portfolio And Comparators

- Policies are all nine combinations of `tau in {0.15,0.17,0.19}` and
  `gamma in {0.25,0.50,0.75}`.
- Guardrail score: `q=p+gamma*(u-p)`.
- The monthly LP has a full budget, loan bounds, a score cap, and a purpose cap.
- The model-implied objective is `(1-p)r-p*LGD`; realized standardized payoff
  is `(1-Y)r-Y*LGD`. Canonical `LGD=0.45`.
- Standardized payoff is not IRR, NPV, welfare, or terminal investor profit.
- **C0:** point score under the same numeric cap. Because `q>=p`, its feasible
  region weakly contains the guardrail region. It is a positive control, not a
  neutral baseline.
- **C1:** a point cap fixed from outcome-free development allocations following
  each residual window: six early menus or eleven late menus.
- **C2:** a monthly point cap matching the already frozen guardrail's funded
  point-score moment. The maximum canonical residual is below `4.17e-17`.
  C2 matches one scalar moment but does not equal feasible sets or identify a
  unique counterfactual.
- **Comparator scopes:** core C0--C2; development-supported core plus caps
  `0.0600:0.0025:0.0825`; broad stress core plus caps
  `0.0500:0.0025:0.1200`.

The development-supported endpoints round outward from late-development
targets 0.0600396539710651--0.0814989466504543. The broad range may be used as
a stress test, never as the sole support for comparator ambiguity.

## Exact Statement Boundary

1. **Proposition 1, positive affine cap equivalence.** Under full budget, a
   globally positive-affine score admits an exact translated point cap. The
   actual guardrail is piecewise affine because of clipping and
   stratum-specific penalties, so this proposition does not equate it to point
   score.
2. **Corollary 1, same-cap nesting.** Since `q>=p`, C0 weakly contains the
   guardrail feasible region and weakly dominates its optimized plug-in
   objective. This does not order realized payoff, default, or miscoverage.
3. **Identity 1, binary miscoverage.** For binary `Y`, miscoverage equals
   `1{Y=0,l>0}+1{Y=1,u<1}`.
4. **Proposition 2, sharp fixed-allocation bounds.** Loan-wise extrema attain
   additive bounds under unrestricted missing binary outcomes.
5. **Paired-policy corollary.** Signed exposure on the funded union uses one
   common unresolved outcome per loan and gives sharp paired contrasts.
6. **Definition 1, declared comparator sensitivity envelope.** The minimum
   lower and maximum upper endpoints over a named finite scope report whether a
   sign survives that scope. This is not a confidence interval, causal
   identified set, or universal statement over comparators.
7. **Selection-transport identity.** Row weighting, available-exposure
   weighting, funded group mix, and within-group selection telescope exactly.
   Under censoring, intermediate terms depend on the extremal completion; only
   final fixed-allocation endpoints are claimed sharp.

No Markov certificate, selected-set conformal validity, deterministic tail
guarantee, or causal policy effect is active.

## Coverage Evidence

| Residual window | Fit rows | Fit coverage | Five-group resolved OOT | Five-group all-candidate bound | Largest taxonomy upper bound |
|---|---:|---:|---:|---:|---:|
| Early 2012H1 | 14,948 | 0.900388 | 0.876312 | [0.854714, 0.879647] | 0.881942 |
| Late 2012H2--2013M1 | 33,909 | 0.900174 | 0.867452 | [0.845072, 0.870973] | 0.875404 |

Every upper endpoint is below 0.90 across both windows and all four
taxonomies. For late five-group lag sensitivity, upper endpoints are 0.872767,
0.872634, 0.870973, and 0.861705 at lags 0, 3, 6, and 12 months. This supports
an observed candidate-coverage transport failure before portfolio selection.
It does not establish general conformal invalidity or selected-set validity.

## Comparator Evidence

Counts are guardrail minus point score, reported as negative / positive /
indeterminate over nine policies.

| Window/comparator | Payoff | Default | Miscoverage |
|---|---:|---:|---:|
| Early C0 | 0 / 9 / 0 | 9 / 0 / 0 | 8 / 0 / 1 |
| Late C0 | 0 / 9 / 0 | 9 / 0 / 0 | 7 / 0 / 2 |
| Early C1 | 5 / 2 / 2 | 2 / 2 / 5 | 1 / 7 / 1 |
| Late C1 | 5 / 0 / 4 | 0 / 5 / 4 | 0 / 8 / 1 |
| Early C2 | 7 / 0 / 2 | 0 / 1 / 8 | 0 / 8 / 1 |
| Late C2 | 5 / 0 / 4 | 0 / 1 / 8 | 0 / 8 / 1 |

The 7-of-9 early payoff count is not timing-stable and cannot be a general
headline. All 27 policy-metric envelopes cross zero in each comparator scope:
27/27 core, 27/27 development-supported, and 27/27 broad stress, or 81/81
scope-specific summaries.

Across the 180 C2 seed-purpose cells in each window:

| Window/metric | Negative | Positive | Indeterminate |
|---|---:|---:|---:|
| Early payoff | 59 | 37 | 84 |
| Late payoff | 56 | 36 | 88 |
| Early default | 50 | 33 | 97 |
| Late default | 51 | 33 | 96 |
| Early miscoverage | 33 | 64 | 83 |
| Late miscoverage | 27 | 85 | 68 |

Signs occur in both directions. Purpose caps 20%, 25%, and 30% bind in all
2,025 reference guardrail policy-month-seed cells; the 100% diagnostic removes
the constraint. Operational choices interact materially with score changes.

## Code-Path Equivalence

- Common OOT point-score rows: 465,117.
- Maximum absolute early/late point-score difference: 0.
- Canonical C0 and point-frontier policy-month cells: 570.
- Maximum absolute exposure difference: 0.
- Total allocation L1 difference: 0.

These controls isolate temporal differences to the residual recipe and
dependent comparators rather than PD, menu, objective, or point-policy code.

## Permitted Claims

- Candidate-level conformal coverage can fail after temporal transport before
  optimization.
- That observed failure survives the two locked windows, four fixed
  taxonomies, and late-window lag grid.
- A score and its numeric cap jointly define the decision problem; copying a
  threshold is not a neutral baseline.
- Exact funded-score matching removes one scalar stringency difference but does
  not equate non-affine feasible regions.
- Portfolio direction depends on comparator scope, residual timing, and binding
  operational constraints in this archive.
- Outcome isolation, explicit label availability, sharp common-outcome bounds,
  and complete policy-family reporting make this fragility auditable.
- The contribution is an audit framework and negative result, not a winning
  credit policy.

## Forbidden Claims

- a universally better or worse guardrail;
- a selected best policy, residual window, seed, cap, taxonomy, or comparator;
- comparator-robust direction over all possible baselines;
- selected-set conformal validity or a latent-PD confidence interval;
- true conditional calibration, causal effects, prospective confirmation, or
  preregistration;
- investor return, IRR, NPV, welfare, or live post-2020 performance;
- fair-lending certification or deployment readiness;
- Markov, tail, deterministic safety, or robustness certificates.

## Evidence Contract

- `reports/crpto/ijds_fixed_taxonomy_c2_evidence.json` is the only active
  paper-facing evidence manifest.
- Active table and figure prefixes are `crpto_ijds_ft_`.
- The builder emits 62 table/figure files plus one manifest. Consecutive builds
  must be byte-identical.
- V1, V2, and V3 DVC pointers must remain available together.
- Protected historical champion stages and `EXTRACTION_MANIFEST.json` remain
  untouched by this audit.

## Required Limitations

- one discontinued consumer-credit platform and accepted 36-month loans only;
- previously inspected retrospective archive;
- terminal snapshot endpoint with unrestricted censoring bounds;
- strong 2012--2016 temporal shift and no exchangeability claim;
- one CatBoost/Platt stack and coarse fixed score taxonomies;
- reporting-lag grid is not a resolution-time model;
- purpose caps bind and interact with policy results;
- one-period plug-in payoff omits cash-flow timing and prepayment;
- C2 is outcome-free but menu-adaptive and nondeployable;
- finite comparator scopes, not universal quantification;
- no causal, prospective, fairness, or deployment interpretation.

## Historical Boundary

Compact-v7, maturity-safe P1, comparator-stringency C1, selected
`linear-004`, pool93, Markov-style diagnostics, Prosper/Freddie exercises, and
A1--A40 tables remain provenance in Git history and immutable artifacts. They
must not fill, validate, or redefine the active result. The manuscript explains
the final audit method and evidence, not the sequence of discarded versions.
