# Fixed-Taxonomy Comparator-Multiverse Protocol

## Status

This protocol replaces the P1/C1 design for the remaining pre-freeze research
period. P1/C1 remain immutable provenance. The new run is a retrospective,
previously inspected archive audit; locking it limits further analyst degrees
of freedom but does not make it preregistered, prospective, or confirmatory.

Required tag: `protocol/ijds-fixed-taxonomy-c2-2026-07-11-v2`.

Executable config:
`configs/experiments/ijds_fixed_taxonomy_c2_2026-07-11.yaml`.

## Locked Post-Freeze Recovery

Version 1 completed all prediction, policy, comparator, and outcome-free
allocation work and wrote `protocol_freeze.json` before any outcome join. Its
post-freeze evaluator then exceeded two hours because it repeatedly joined
each of 7,347 policy-month groups to the full 540,121-row outcome panel. The
wrapper timed out and the original child was stopped after a further one-hour
observation window. No evaluation, contrast, simulation, summary, or receipt
artifact existed at that point, so version 1 is incomplete and is not
publication evidence.

Version 2 changes no scientific input, allocation, policy, comparator, seed,
cap, endpoint, or stop rule. It may import only the version-1 outcome-free
freeze at commit `4835cc18a0117a695f89f9da70a4e3af97663a27` with SHA-256
`93690082880ef4ff1375dcd5b26d2df79f80e6ebe09a6d83b7fd99a9abb4cfae`.
Every referenced artifact and model descriptor is rehashed before use. The
postprocessor performs one validated many-to-one outcome join, indexes solve
records by their complete cell key, and reconstructs diagnostic panels from
the frozen recipes. It also corrects `n_unresolved_candidates` to count the
declared monthly candidate menu rather than the full archive. This is an
operational and bookkeeping correction made without inspecting policy outcome
contrasts.

## Research Question

When a conformal-derived score enters a portfolio constraint, which conclusions
survive temporal coverage failure, right-censored outcomes, and a prespecified
multiverse of outcome-free point-score comparators?

The estimand is the finite Lending Club archive defined by the config. The
paper will not infer causal effects, selected-set validity, live performance,
or a superpopulation guarantee.

## Information Contract

The information cutoff is 2016-03-31, before the first primary decision menu.
For label-dependent fitting, Fully Paid is available at `last_pymnt_d` and a
Charged Off outcome is conservatively available six calendar months after
`last_pymnt_d`. Missing payment dates, exact Default, and all nonterminal states
are unavailable. At least 99% of every fitting block must survive this rule.

CatBoost uses availability-safe 2007--2010 labels. Platt calibration uses
availability-safe 2011 labels. The score taxonomy is then fixed from all 2011
calibrated scores without using 2012H1. Residual order statistics use only
availability-safe 2012H1 labels. The 2012H2 block may construct comparators
from predictions and allocations, but no outcome may select a policy or a
comparator.

The endpoint is terminal default observed by the September 2020 administrative
snapshot. Fully Paid is zero, Charged Off is one, and every other state is
right-censored. The interval is the convex-hull representation of a binary
prediction set, not a confidence interval or bound for latent PD.

## Closed Policy Family

All nine combinations of risk cap `{0.15, 0.17, 0.19}` and uncertainty weight
`{0.25, 0.50, 0.75}` are co-primary. There is no champion, development-payoff
selector, tie-break, or OOT winner. Every policy-month allocation is persisted
before outcomes are joined.

The canonical conformal recipe uses five fixed 2011 score strata and the exact
finite-sample order-statistic rank within each 2012H1 stratum. Exactness refers
only to rank computation under exchangeability. Group counts 1, 2, 5, and 10
are a declared diagnostic, not a selection grid.

## Comparator Multiverse

For each guardrail and month, the primary C2 benchmark first freezes the
guardrail allocation and computes its funded point-PD moment. It then solves a
point-PD portfolio on the identical menu, budget, payoff, and purpose cap using
that moment as its cap. The achieved moment must match within `1e-10`; otherwise
the run stops. This benchmark is outcome-free but adaptive to the current menu,
so it is an audit comparator rather than a standalone deployable policy.

The complete multiverse also reports the copied numeric cap, the fixed 2012H2
funded-PD cap, and the entire point-cap grid from 0.05 to 0.12 by 0.0025. No
comparator is chosen after viewing outcomes. A conclusion is comparator-robust
only when its sharp outcome interval has one sign throughout the declared
multiverse.

## Robustness Matrix

The canonical result uses seed 42 and a 25% purpose cap. Algorithmic seed
perturbations `{40,41,42,43,44}` and purpose caps `{0.20,0.25,0.30,1.00}` form
a declared 9 by 5 by 4 matrix on the primary OOT window. Every cell is
reported. The 2012H2 block is solved once under the canonical seed and purpose
cap solely to construct the fixed C1 comparator; it is not an outcome-based
selection or a second robustness grid. The analysis also
reoptimizes at LGD `{0.25,0.45,0.65}` and reports undiscounted cumulative cash
received through the snapshot as a secondary outcome, never as IRR, NPV, or
terminal investor profit.

The score ablations compare the clipped conformal blend, its unclipped
group-residual penalty, and a pooled-residual penalty. If group penalties
reproduce the conformal allocations, the mechanism is described as coarse
stratum penalization rather than uncertainty control.

## Theory and Simulation

The paper will add the score-cap equivalence result: for a full-budget
weighted-average constraint, an affine score transformation has an exactly
translated cap; absent a nondegenerate affine relationship, one scalar cap
cannot generally preserve the feasible halfspace. The comparator multiverse
and unresolved-outcome bounds form a joint finite identification region.

A controlled simulation isolates taxonomy coarsening, endpoint saturation,
temporal drift, and comparator mismatch. It supports mechanism interpretation
only; it cannot validate the Lending Club empirical signs.

## Stop Rules

1. Stop if an outcome field reaches policy or comparator construction.
2. Stop if label retention is below 99%, fixed edges repeat, a canonical group
   has fewer than 1,000 residuals, or rank reconciliation fails.
3. Stop if a budget is underfilled, the actual solver differs from locked
   HiGHS, or any C2 point-PD match residual exceeds `1e-10`.
4. Universal underperformance requires all nine canonical C2 intervals to have
   one sign and no seed-purpose cell with a robust opposite sign.
5. Comparator reversal requires opposite C0/C2 signs for all nine policies.
6. Funded-miscoverage direction requires 9 of 9 canonical policies.
7. Standardized payoff and cumulative cash are separate outcomes. Disagreement
   is payoff dependence, not a robustness success.
8. If neither the 9-of-9 comparator result nor the 9-of-9 funded-miscoverage
   result survives, stop the IJDS submission rather than selecting a policy,
   seed, cap, taxonomy, or payoff.

Protected historical stages and `EXTRACTION_MANIFEST.json` remain untouched.
