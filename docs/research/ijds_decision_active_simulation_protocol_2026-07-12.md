# IJDS Decision-Active Mechanism Simulation Protocol

## Status

This protocol locks a synthetic mechanism experiment before its full factorial
run. It is neither empirical validation nor a repair selected from Lending Club
outcomes. It cannot establish a policy winner, selected-set conformal validity,
an investor return, a causal effect, or a sign for the application.

Required protocol tag:
`protocol/ijds-decision-active-simulation-2026-07-12-v1`.

Executable configuration:
`configs/experiments/ijds_decision_active_simulation_2026-07-12.yaml`.

The experiment replaces the V4 simulation's decision component, whose nominal
0.40 guardrail cap was slack in all 19,200 repetitions and whose same-cap and
C2 allocations changed in only two and one repetitions, respectively. The V4
simulation remains immutable provenance and retains its coverage-geometry role.

## Research question

When a binary absolute-residual conformal score enters a genuinely active
portfolio constraint, how do temporal score shift, conditional calibration
shift, taxonomy size, cap stringency, censoring, and comparator semantics alter
coverage and allocation conclusions?

The experiment separates three objects:

1. candidate-level binary prediction-set coverage;
2. optimizer-induced selection under a conformal effective score; and
3. guardrail-minus-point contrasts under C0 and C2.

No claim may transfer a simulated sign to Lending Club.

## Data-generating mechanism

Each repetition uses independent deterministic random streams for residual-fit
data, outcome-free candidate menus, candidate outcomes, and censoring. The same
random block is reused across all 72 factorial cells for that repetition. This
common-random-number pairing holds the latent menu, rate noise, outcome
uniforms, and censoring uniforms fixed while factor levels change; it reduces
Monte Carlo noise and permits paired mechanism contrasts without changing the
50 independent repetition blocks.

- Fit scores are drawn from `Beta(2,18)` and fit outcomes from Bernoulli(score).
- Candidate base risk is drawn independently from the same beta distribution.
  The reported model score adds the declared score shift and is clipped inside
  `(0,1)`.
- Candidate true risk is obtained by adding the declared shift on the log-odds
  scale to the reported model score. Outcomes are drawn only after allocations
  have been constructed.
- Contractual rates equal `0.04 + 1.20 * score + Normal(0,0.015^2)`, clipped to
  `[0.03,0.40]`.
- The model-side coherent objective is `(1-p)r-p*0.45`.
- Absolute-residual binary conformal recipes use alpha 0.10 and either one or
  five fixed empirical fit-score quantile strata.
- The guardrail effective score is `q=p+0.5(U-p)`, where `U` is the clipped
  conformal upper endpoint.

Every menu contains 1,200 equal-unit candidates. Every policy funds exactly
120 units. There is one purpose category and a nonbinding purpose cap, so the
experiment isolates the score constraint.

## Outcome-free normalized cap

For each repetition, let `q_min` be the minimum achievable capital-weighted
effective score at the fixed budget, computed from the 120 smallest effective
scores. Let `q_obj` be the effective-score moment of the unconstrained
model-objective maximizer. The guardrail cap is

`q_cap(lambda) = q_min + lambda * (q_obj - q_min)`

for predeclared `lambda` in `{0.25,0.50,0.75}`.

This construction uses no candidate outcome. If `q_obj-q_min` is below `1e-4`,
the repetition stops as structurally uninformative. Otherwise the guardrail cap
must bind within `1e-7`; failure is an implementation or degeneracy stop, not
permission to tune lambda.

C0 solves the point-score portfolio under the same numeric `q_cap`. C2 solves
the point-score portfolio under the point-score moment of the already frozen
guardrail allocation. C2 must match that moment within `1e-10`, and its plug-in
objective must weakly dominate the guardrail within USD `1e-5` in unit-scaled
simulation currency.

## Locked factorial

The complete grid contains:

- score shift in `{0.00,0.08}`;
- calibration log-odds shift in `{0.00,0.75,1.50}`;
- taxonomy groups in `{1,5}`;
- normalized cap position in `{0.25,0.50,0.75}`; and
- censoring rate in `{0.00,0.15}`.

There are 72 cells and 50 repetitions per cell, for 3,600 repetitions. The
gamma, LGD, rate mechanism, sample sizes, budget, and solver settings are fixed.
No cell, repetition, or metric may be removed based on its sign.

## Required outputs

Every repetition reports:

- fit and candidate prevalence, candidate coverage bounds, and binary geometry;
- `q_min`, `q_obj`, normalized cap, realized guardrail cap slack, and full-budget
  checks;
- C0 and C2 allocation distances and expected-objective contrasts;
- C2 moment residual and objective dominance;
- guardrail, C0, and C2 selected miscoverage bounds;
- sharp guardrail-minus-comparator payoff, default, and miscoverage bounds under
  censoring, reconciled against the complete simulated outcomes;
- whether each allocation contrast exceeds the locked numerical tolerance.

Cell summaries must retain means, standard deviations, minima, maxima, and
nonzero-allocation rates. Reporting a grand average without the factorial cells
is forbidden.

## Stop and interpretation rules

1. Candidate outcomes must be generated after guardrail, C0, and C2 allocations.
2. Stop on repeated taxonomy edges, an effective-score range below `1e-4`, an
   unfilled budget, nonoptimal HiGHS solve, nonbinding guardrail cap, C2 mismatch,
   or C2 dominance failure.
3. Report all 72 cells even if allocation directions reverse.
4. Allocation activation is a structural validity check, not a favorable-result
   criterion. If distances remain zero despite binding caps, report that result.
5. Coverage changes do not imply selected-set validity. Selected miscoverage is
   a diagnostic outcome, not a conformal guarantee.
6. C0 and C2 answer different questions; neither may be called the unique point
   baseline without its cap semantics.
7. Simulation signs may explain mechanisms only. The empirical archive remains
   the only source for application-specific direction and remains bounded by its
   unresolved outcomes and comparator envelopes.

## Reproducibility contract

Code, configuration, tests, and this protocol must be committed and tagged
before the 3,600-repetition run. Outputs use a fresh immutable run directory,
atomic Parquet/JSON writes, source hashes, deterministic seed coordinates, and
empty protected-stage lists. Any post-tag implementation correction requires an
erratum, a fresh run tag, and a full rerun.
