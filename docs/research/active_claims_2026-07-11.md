# CRPTO Active IJDS Claim Registry - 2026-07-11

This file is the source of truth for the single IJDS manuscript. It supersedes
the earlier single-policy narrative. The active paper is a retrospective audit
of temporal transport and decision comparability; it is not a claim that a
conformal guardrail or a point-PD policy is universally superior.

## Editorial Decision

- **NO-GO:** any superiority, dominance, winner, or champion-policy paper.
- **NO-GO:** the predeclared 9-of-9 guardrail direction. It did not pass.
- **GO:** one IJDS paper about why coverage, score conservatism, comparator
  stringency, and operational constraints must be audited as distinct objects.
- **No policy winner is allowed.** All nine policies remain co-primary.
- The empirical headline is a falsification: temporal coverage failure is
  stable, but portfolio conclusions are not invariant to the comparator or to
  binding background constraints.

The archive was inspected before this protocol. The tag limits subsequent
analyst degrees of freedom but does not make the analysis preregistered,
prospective, or confirmatory.

## Immutable Identifiers

### Outcome-free allocation freeze

- Run tag: `ijds-fixed-taxonomy-c2-2026-07-11-v1`.
- Protocol tag: `protocol/ijds-fixed-taxonomy-c2-2026-07-11-v1`.
- Protocol commit: `4835cc18a0117a695f89f9da70a4e3af97663a27`.
- Freeze SHA-256:
  `93690082880ef4ff1375dcd5b26d2df79f80e6ebe09a6d83b7fd99a9abb4cfae`.
- V1 completed all 7,347 outcome-free policy-month solves and then timed out in
  an inefficient post-freeze evaluator. It is not publication evidence by
  itself.

### Reconciled evaluation

- Run tag: `ijds-fixed-taxonomy-c2-2026-07-11-v2`.
- Protocol tag: `protocol/ijds-fixed-taxonomy-c2-2026-07-11-v2`.
- Protocol commit: `a88839dfe14875fca2c02c43725291bc49d98611`.
- Deterministic summary:
  `models/experiments/ijds_prefreeze/ijds-fixed-taxonomy-c2-2026-07-11-v2/fixed_taxonomy_c2_summary.json`.
- Paper evidence:
  `reports/crpto/ijds_fixed_taxonomy_c2_evidence.json`.
- V2 rehashes every imported V1 artifact, performs one validated outcome join,
  and records the complete lineage in its freeze and receipt.

## Research Object

- Raw archive scanned: 2,925,493 rows.
- Status-independent 36-month universe: 540,121 loans.
- Fitting blocks: PD development through 2010, Platt calibration in 2011, and
  conformal residual fitting in 2012H1.
- Policy-development menus: July--December 2012. Their outcomes select neither
  a policy nor a comparator.
- Primary OOT menus: 15 monthly decisions, April 2016--June 2017, with a fresh
  $1M budget per month.
- Censored extension: July--September 2017, secondary only.
- Information cutoff: March 31, 2016.
- Endpoint at the September 2020 administrative snapshot: Fully Paid is 0,
  Charged Off is 1, and exact Default plus every nonterminal status is right
  censored.
- Label retention by the information cutoff is 99.765% for PD development,
  99.830% for probability calibration, and 99.873% for conformal fitting.
- Candidate membership never uses loan status. Outcomes are physically absent
  from prediction, policy, and comparator construction.

## Active Method

### Prediction and conformal recipe

- CatBoost uses 29 numeric and 9 categorical origination-time features.
- Platt calibration is fitted on availability-safe 2011 labels.
- Five score strata are fixed from all 2011 calibrated scores without using
  2012H1 outcomes.
- Absolute residual order statistics are fitted on 14,948 availability-safe
  2012H1 labels with the exact rank
  `ceil((n_g + 1) * (1 - alpha))`, `alpha=0.10`.
- The output is a convex-hull representation of a binary-outcome prediction
  set. It is not a confidence interval for latent individual PD.
- Group counts 1, 2, 5, and 10 are diagnostics, not an OOT selection grid.

### Policy family

- All nine combinations of `tau in {0.15, 0.17, 0.19}` and
  `gamma in {0.25, 0.50, 0.75}` are co-primary.
- There is no champion, development-payoff selector, OOT winner, or tie-break.
- Guardrail score:
  `q_i=(1-gamma)p_i+gamma*u_i = p_i+gamma(u_i-p_i)`.
- The monthly LP maximizes expected standardized payoff
  `(1-p_i)r_i-p_i*LGD` with full budget, score cap, loan bounds, and a purpose
  concentration cap.
- Realized standardized payoff is `(1-Y_i)r_i-Y_i*LGD`, with canonical
  `LGD=0.45`. This is not IRR, NPV, welfare, or terminal investor profit.
- Undiscounted cumulative cash yield at the snapshot is reported separately as
  a descriptive metric.

### Comparator multiverse

- **C0:** point PD under the same numeric cap. This is intentionally retained
  as the common but stringency-confounded baseline.
- **C1:** a policy-specific point cap fixed from 2012H2 funded point PD.
- **C2 (primary):** for each guardrail and month, freeze its allocation, compute
  its funded point-PD moment, and solve point PD on the identical menu with that
  moment as the cap. C2 is outcome-free and matches to at most
  `4.17e-17`, but it is an audit comparator, not a deployable fixed rule.
- **Frontier:** point caps from 0.05 to 0.12 in increments of 0.0025.
- A conclusion is comparator-robust only if its sharp interval has one sign
  throughout the finite declared multiverse.

## Exact Theory Boundary

The paper may use these exact statements.

1. **Binary miscoverage identity.** For `Y in {0,1}`,
   `1{Y not in [l,u]} = 1{Y=0,l>0} + 1{Y=1,u<1}`.
2. **Sharp fixed-allocation bounds.** With unrestricted missing binary
   outcomes, additive endpoints are attained by loan-wise extremal completion.
3. **Sharp common-outcome policy contrasts.** Bounds are computed on the union
   funded by both policies, preserving the same unresolved outcome for a loan
   that appears in both allocations.
4. **Positive affine score-cap equivalence.** Under full budget, if
   `s_i=a p_i+b`, `a>0`, then an average-score cap translates exactly to a
   point cap. A non-affine score generally defines a different halfspace.
5. **Same-threshold nesting.** Because `q_i>=p_i`, using the same numeric cap
   makes the guardrail feasible set a subset of the point-PD feasible set.
6. **Finite multiverse identification region.** Taking the minimum lower and
   maximum upper sharp contrast across declared comparators identifies which
   directions are invariant to that finite design set. It is not a confidence
   interval over an unknown comparator distribution.

No Markov certificate, deterministic tail guarantee, selected-set conformal
validity, or causal policy effect is active.

## Predictive Evidence

For canonical seed 42:

| Quantity | Value |
|---|---:|
| Conformal-fit rows | 14,948 |
| Conformal-fit coverage | 0.900388 |
| 2012H2 resolved coverage, five strata | 0.903379 |
| Primary resolved coverage, five strata | 0.876312 |
| Primary all-candidate coverage, five strata | [0.854714, 0.879647] |
| Primary mean interval width, five strata | 0.664992 |
| Primary upper-endpoint-one share, five strata | 0.187084 |

The upper endpoint of the all-candidate OOT interval is below 0.90 for every
declared taxonomy:

- one stratum: `[0.853029, 0.880326]`;
- two strata: `[0.855929, 0.881820]`;
- five strata: `[0.854714, 0.879647]`;
- ten strata: `[0.857404, 0.881942]`.

This supports temporal coverage failure in the observed archive. It does not
establish a superpopulation guarantee or selected-set validity.

## Comparator-Dependent Results

Signs below are guardrail minus point PD across the nine canonical policies.
Negative payoff means the guardrail is worse; negative default or
miscoverage means it is lower.

| Comparator | Payoff | Default | Miscoverage |
|---|---:|---:|---:|
| C0 same numeric cap | 9 positive | 9 negative | 8 negative, 1 indeterminate |
| C1 fixed development cap | 5 negative, 2 positive, 2 indeterminate | 2 negative, 2 positive, 5 indeterminate | 7 positive, 1 negative, 1 indeterminate |
| C2 contemporaneous match | 7 negative, 2 indeterminate | 1 positive, 8 indeterminate | 8 positive, 1 indeterminate |
| Full finite multiverse | 9 indeterminate | 9 indeterminate | 9 indeterminate |

Thus C0 makes the guardrail look safer and economically better, while C2
removes every universal direction. All 27/27 policy-by-metric multiverse
envelopes cross zero. The paper must not elevate one comparator-specific sign
to a policy property.

## Sensitivity and Mechanism

- The seed-purpose matrix contains 180 C2 cells.
- Payoff directions: 59 negative, 37 positive, 84 indeterminate.
- Default directions: 50 negative, 33 positive, 97 indeterminate.
- Miscoverage directions: 33 negative, 64 positive, 83 indeterminate.
- Every 20%, 25%, and 30% purpose cap binds in every guardrail
  policy-month-seed cell; the no-cap diagnostic does not bind.
- Therefore background operational constraints interact materially with the
  score and comparator. The canonical 25% cap is not a neutral detail.
- The point-cap frontier changes direction around the range in which the
  guardrails' funded point-PD moments lie. Below roughly 0.0675 the guardrail
  usually looks worse; above roughly 0.0825 it usually looks better. This is
  direct evidence that the baseline can manufacture a directional claim.
- The unclipped group-residual ablation nearly reproduces the clipped
  guardrail contrasts. Allocation L1 differences are only $4,685--$46,609 over
  $15M, depending on policy.
- A pooled residual penalty is affine in point PD and reproduces its translated
  point allocation exactly. The nontrivial mechanism is coarse score-stratum
  penalization, not an affine uncertainty surcharge.
- C2 results vary with LGD. No universal economic direction survives
  `LGD in {0.25,0.45,0.65}`.
- Snapshot cash yield can disagree with standardized payoff for individual
  policies; this is metric dependence, not robustness.

## Controlled Simulation

The simulation fixes taxonomy scores on a sample independent of residual
calibration, then varies temporal shift.

- Mean calibration coverage is approximately 0.9034.
- Mean transported coverage falls from 0.9016 at zero shift to 0.8923 at shift
  0.15.
- The C0 same-cap comparison produces a large default difference, around
  -0.069 to -0.082, even though the C2 matched difference remains near zero on
  average with intervals spanning both signs.
- Endpoint saturation increases from 0.094 to 0.123.
- Taxonomy coarsening changes more allocation mass than endpoint clipping.

These are mechanism diagnostics only. They do not validate Lending Club signs.

## Permitted IJDS Claims

- Temporal transport can invalidate nominal binary-outcome conformal coverage
  before portfolio selection.
- A conformal score, a point score, and their numeric caps jointly define the
  feasible decision problem; copying a cap is not a neutral baseline.
- Exact funded-PD matching removes one scalar stringency difference but does
  not equate non-affine feasible halfspaces or create a causal counterfactual.
- Comparator and operational-constraint choices can reverse retrospective
  portfolio conclusions even when model, menu, objective, budget, and solver
  are fixed.
- Outcome-free allocation, explicit label availability, and sharp
  common-outcome bounds make this fragility auditable.
- The empirical contribution is a negative, baseline-aware audit, not a new
  winning credit policy.

## Forbidden Claims

- a universally better or worse guardrail;
- a selected best policy or OOT winner;
- 9-of-9 payoff, default, or miscoverage direction under C2;
- comparator-robust sign over the declared multiverse;
- unique, optimal, or deployment-ready C2 matching;
- selected-set conformal validity;
- causal, prospective, confirmatory, or preregistered evidence;
- latent-PD confidence intervals;
- investor return, IRR, NPV, welfare, or live post-2020 performance;
- fair-lending certification;
- Markov, tail, or deterministic safety certificate.

## Evidence Contract

- `reports/crpto/ijds_fixed_taxonomy_c2_evidence.json` is the only active
  paper-facing evidence manifest.
- Active tables use prefix `crpto_ijds_ft_`.
- Active figures use prefix `crpto_ijds_ft_`.
- Two consecutive evidence builds are byte-identical across all 42 generated
  files: 41 table/figure artifacts plus the evidence manifest.
- V1 outcome-free and V2 evaluation directories must be tracked together; V2
  alone is not a complete lineage.
- Protected historical champion stages and `EXTRACTION_MANIFEST.json` remain
  untouched.

## Required Limitations

- one historical consumer-credit platform and 36-month loans;
- previously inspected retrospective archive;
- terminal snapshot outcome with unrestricted censoring bounds;
- substantial 2012-to-2016 temporal shift;
- one CatBoost/Platt prediction stack and coarse score taxonomy;
- purpose caps bind and interact with policy results;
- standardized one-period payoff omits payment timing and prepayment;
- C2 is outcome-free but adaptive to each realized menu and guardrail;
- finite comparator multiverse, not universal quantification over baselines;
- no causal, prospective, deployment, or fairness interpretation.

## Historical Boundary

The compact-v7 champion, maturity-safe P1, comparator-stringency C1, selected
`linear-004`, pool93, Markov-style diagnostics, Prosper/Freddie exercises, and
A1--A40 tables remain available in Git history and immutable artifacts. They
may motivate a failure mode or document provenance, but they cannot fill,
validate, or redefine the active result. The final paper explains the active
method and evidence, not the project's sequence of discarded versions.
