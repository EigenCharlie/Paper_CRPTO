# Binary-Geometry and Comparator-Frontier V4 Protocol

## Status

This protocol defines a new isolated retrospective audit over a previously
inspected archive. It does not alter or overwrite fixed-taxonomy V1--V3, the
historical champion, or `EXTRACTION_MANIFEST.json`. It cannot become
confirmatory, prospective, or preregistered. Locking limits additional analyst
degrees of freedom and makes every reported specification auditable.

Required protocol tag:
`protocol/ijds-binary-geometry-frontier-v4-2026-07-12-v1`.

Executable config:
`configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-12.yaml`.

Before the required tag was created, implementation smoke tests reloaded the
previously inspected archive, fitted both declared learners, checked all group
sizes and residual-window recipes, timed one monthly basis frontier, and
reconciled one guardrail/C2 cell. These checks motivated only computational
reuse of a HiGHS basis and shared point-frontier storage. They did not change
the eight windows, learner roles, nine policies, comparator definitions,
simulation grid, outcomes, hypotheses, or stop rules. V4 therefore remains a
retrospective specification audit, not a preregistration.

## Research Question

When an absolute-residual conformal construction for a binary outcome is used
as a score inside a constrained optimizer, how do binary prediction-set
geometry, temporal transport, and score-cap comparator choice jointly affect
the conclusions that can be drawn?

The estimand is the finite Lending Club archive declared below. No result is a
causal effect, selected-set guarantee, investor return, live policy result, or
superpopulation statement.

## Locked Information Contract

- Raw source, 36-month term, March 31, 2016 information cutoff, September 30,
  2020 administrative snapshot, endpoint taxonomy, features, CatBoost
  specification, 2007--2010 development block, 2011 Platt block, and 2011
  score-taxonomy source are inherited from V3.
- Candidate membership is determined by issue date and contractual term only.
- Fully Paid is zero, Charged Off is one, and exact Default plus every
  nonterminal snapshot state are unresolved.
- Label availability uses `last_pymnt_d`; a Charged Off label becomes available
  six calendar months later. Each included residual month must retain at least
  99% of terminal labels by the information cutoff.
- Outcomes are absent from prediction, policy, comparator, and frontier
  construction. Every allocation is persisted and hashed before one validated
  outcome join.

## Complete Residual-Window Specification

The primary temporal specification contains every consecutive six-month
window that starts in 2012 and ends no later than January 2013:

1. January--June 2012;
2. February--July 2012;
3. March--August 2012;
4. April--September 2012;
5. May--October 2012;
6. June--November 2012;
7. July--December 2012; and
8. August 2012--January 2013.

All eight windows are co-primary for coverage transport. No window is selected,
weighted, promoted, or removed using fit or OOT coverage. Outcome-free policy
development is February--December 2013 for every window, ensuring that the
same menus support every comparator definition.

The canonical taxonomy has five score strata fixed from all status-independent
2011 Platt scores. One, two, and ten strata are closed coverage diagnostics.
The exact split rank is `ceil((n_g + 1) * (1 - alpha))` at `alpha=0.10`.

## Binary Geometry

For every window, taxonomy, role, and score stratum, the run must report:

- continuous interval coverage and width mean/quantiles;
- discrete intersection with `{0,1}` as empty, `{0}`, `{1}`, or `{0,1}`;
- lower-endpoint positivity and upper-endpoint saturation;
- group prevalence, residual quantile, and score range; and
- below/above-fit score-range counts.

The implemented object is a clipped residual interval for the observed binary
outcome. It is not a latent-PD interval and not the convex hull of its discrete
intersection.

The paper may state a binary phase-transition proposition only for the exact
conditions proved in code and supplement. Empirical strata with varying scores
are an application diagnostic, not proof of the constant-score proposition.

## Learner Diagnostic

The CatBoost/Platt stack is primary. A numeric-feature logistic regression,
followed by an independent 2011 Platt map and its own fixed 2011 taxonomy, is a
coverage-only negative control. It does not select the primary learner and does
not enter portfolio optimization. Both learners must report every residual
window even if their conclusions differ.

## Closed Portfolio Family

All nine combinations of `tau in {0.15,0.17,0.19}` and
`gamma in {0.25,0.50,0.75}` are co-primary. The canonical empirical portfolio
audit uses seed 42, a 25% purpose cap, LGD 0.45, fifteen monthly USD 1 million
menus from April 2016 through June 2017, and every residual window. No winner
or aggregate vote across policies or windows is permitted.

Early/late seed and purpose-cap results from V2/V3 remain historical
sensitivities. V4 does not add another policy HPO or seed search.

## Comparator Identification

All comparators use the same menu, full budget, per-loan bounds, purpose cap,
and plug-in objective `(1-p)r-p*LGD`.

- C0 uses the point score and copies the guardrail's numeric cap.
- C1 uses, for each window and policy, the capital-weighted mean of the eleven
  outcome-free monthly point-score moments generated by that guardrail on the
  common 2013 development menus.
- C2 uses, for each OOT policy-month pair, the point-score moment of the already
  frozen guardrail allocation. Its numerical residual must not exceed `1e-10`.
- The development-admissible comparator set for a window-policy pair is the
  closed interval from the minimum to the maximum of its eleven monthly
  development point-score moments. No rounding or outcome enters this set.
- A broad stress interval of `[0.05,0.12]` is secondary only.

The point-score LP is represented with a binding budget equality, so its risk
cap enters as a right-hand side. HiGHS basis-ranging endpoints define the exact
piecewise-linear cap frontier. Every development-support endpoint, C0/C1/C2
cap, and basis breakpoint inside the declared interval must be evaluated.
Fixed-grid interpolation is not allowed to support an exact-frontier claim.
If a development-admissible endpoint lies outside the secondary broad stress
interval, basis enumeration expands mechanically to the closed hull of the
two declared supports; it may not truncate the development support.

For any guardrail allocation `x_q`, C2 sets
`tau_C2 = p' x_q / B`. Because `x_q` is then feasible for the point-score LP
under unchanged nonrisk constraints, the optimized point-score plug-in
objective must weakly dominate the guardrail objective. Every solve must
reconcile this proposition numerically.

## Outcomes and Identification

- Primary outcomes are standardized payoff, exposure-weighted terminal
  default, and exposure-weighted binary-interval miscoverage.
- Standardized payoff is not IRR, NPV, welfare, or a lifetime cash-flow model.
- Unresolved outcomes receive sharp fixed-allocation and common-outcome paired
  bounds. Sampling confidence intervals are not implied.
- A comparator envelope is reported once per policy, metric, window, and named
  scope. Nested scopes are not counted as independent confirmations.

## Factorial Simulation

The mechanism experiment crosses score shift, outcome-prevalence shift,
taxonomy size, and censoring rate using deterministic independent streams.
Every cell reports binary-set geometry, candidate coverage, same-cap and C2
allocation contrasts, and C2 objective dominance. The simulation explains
mechanisms only and cannot validate Lending Club signs.

The illustrative allocation mechanism is fixed at a 0.40 score cap, 0.25
upper-endpoint blend, 50 funded units from 2,000 equal-size candidates, no
binding segment concentration, and LGD 0.45. These values ensure that the
closed factorial can expose the binary phase transition without silently
dropping infeasible cells. They are not members of, or candidates for, the
empirical nine-policy family.

## Stop Rules

1. Stop if any outcome-derived field reaches fitting outside declared label
   blocks, policy construction, comparator construction, or frontier ranging.
2. Stop if any residual month has retention below 99%, a fixed edge repeats, a
   five-group window has fewer than 1,000 observations in a group, or a rank
   fails exact reconciliation.
3. Stop if any budget is not filled, HiGHS is not optimal, a C2 moment misses
   by more than `1e-10`, or point objective dominance fails by more than
   `1e-5` dollars.
4. Report all eight windows. If any OOT upper coverage bound reaches 0.90, the
   paper must state timing heterogeneity rather than invariant failure.
5. If CatBoost and logistic controls disagree, the result is learner-dependent.
6. If a direction fails anywhere in its named comparator support, report
   comparator dependence. Do not expand or contract support after outcomes.
7. Do not report `N/N` across nested scopes as independent evidence.
8. Do not add HPO, a policy selector, a preferred window, or a new external
   dataset after inspecting this run.
9. If the audit lacks a generalizable methodological contribution after the
   complete run, narrow the paper or stop rather than revive pool93 or v7.

## Reproducibility Contract

The implementation and protocol must be committed and tagged before the V4
run. Outputs use a fresh isolated run tag, immutable directories, atomic
writes, SHA-256 descriptors, and new DVC pointers. A clean-clone replay must
rebuild evidence and manuscript surfaces without executing protected stages.
