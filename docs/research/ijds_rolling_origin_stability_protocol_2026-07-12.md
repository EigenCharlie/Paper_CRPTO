# IJDS Rolling-Origin Stability Protocol

## Status and purpose

This document locks a retrospective stability audit before the 2015 and 2017
outcome joins. The Lending Club archive has been inspected repeatedly, so this
is not a preregistration, a prospective validation, or an independent test set.
Its narrower purpose is to prevent the active V4 result from resting on one
calendar origin while preserving the exact maturity-safe information contract.

Required protocol tag:
`protocol/ijds-rolling-origin-stability-2026-07-12-v1`.

Executable configurations:

- `configs/experiments/ijds_rolling_origin_2015_2026-07-12.yaml`;
- the existing V4 run, restricted mechanically to April--June 2016; and
- `configs/experiments/ijds_rolling_origin_2017_2026-07-12.yaml`.

The audit cannot replace or mutate the V4 evidence manifest, the active claim
registry, `EXTRACTION_MANIFEST.json`, or any protected historical artifact.

## Symmetric calendar design

For calendar origin `Y` in `{2015, 2016, 2017}`, every block moves by exactly
`Y - 2016` years relative to V4:

| Block | 2015 origin | 2016 origin | 2017 origin |
|---|---|---|---|
| PD development | through Dec 2009 | through Dec 2010 | through Dec 2011 |
| Platt/taxonomy block | Jan--Dec 2010 | Jan--Dec 2011 | Jan--Dec 2012 |
| Eight residual windows | Jan 2011--Jan 2012 | Jan 2012--Jan 2013 | Jan 2013--Jan 2014 |
| Outcome-free policy development | Feb--Dec 2012 | Feb--Dec 2013 | Feb--Dec 2014 |
| Information cutoff | Mar 31, 2015 | Mar 31, 2016 | Mar 31, 2017 |
| Common primary OOT | Apr--Jun 2015 | Apr--Jun 2016 | Apr--Jun 2017 |
| Secondary censored extension | Jul--Sep 2015 | Jul--Sep 2016 | Jul--Sep 2017 |

The CatBoost specification, Platt method, numeric logistic control, five fixed
score strata, eight consecutive six-month residual windows, nine policies,
USD 1 million monthly budget, 25% purpose cap, LGD 0.45, payoff, comparator
definitions, exact frontier, solver tolerances, and unresolved-outcome bounds
remain unchanged. The 2016 origin is not refitted: its frozen V4 artifacts are
subselected by the three declared calendar months.

Each origin is a different fitted model and taxonomy because only information
available under that origin enters fitting. Origins are not exchangeable
replicates and their nested training histories must not be counted as an
effective sample size of three.

## Locked questions

1. Does canonical five-stratum candidate coverage remain below 0.90 for every
   learner and all eight windows at each calendar origin?
2. Does the binary-set phase behavior recur, or is its location origin- and
   learner-dependent?
3. Does any payoff, default, or miscoverage direction remain identified over
   the complete development-supported point-cap interval in every origin?
4. Do C2 moment reconciliation and plug-in objective dominance remain exact?
5. Are feasibility failures themselves origin-dependent under the unchanged
   minimum group size, retention, budget, and solver rules?

These questions are descriptive stability checks. They do not create
selected-set conformal validity, causal effects, a policy winner, investor
returns, or a superpopulation guarantee.

## Reporting and decision rules

- Report every feasible origin, learner, residual window, taxonomy diagnostic,
  policy, metric, and declared comparator scope. Do not average away signs.
- Treat an origin that fails an unchanged protocol requirement as a reported
  feasibility failure. Do not reduce the 1,000-row canonical-group floor,
  retention threshold, number of groups, or number of windows after failure.
- Call below-target transport *stable across these origins* only if every
  canonical aggregate upper coverage bound is below 0.90 for both learners in
  all three origins. Otherwise report the exact origin/learner heterogeneity.
- Call a comparator direction stable only if its sharp envelope has the same
  identified sign for every window-policy cell at every origin. A crossing or
  opposite sign in one cell makes the direction unidentified over that scope.
- The April--June common horizon is primary. July--September is secondary and
  must not rescue a primary result.
- No pooled p-value, vote count, preferred origin, preferred learner, preferred
  residual window, or post-result policy may be introduced.
- The audit may narrow an active claim. It may expand the active manuscript
  only after an explicit claim-registry update backed by a deterministic
  cross-origin evidence artifact and independent reconciliation.

## Stop rules

1. Stop an origin before its outcome join if any label, terminal status, total
   payment, or outcome-derived field reaches prediction, policy, comparator,
   or frontier construction.
2. Stop and report if chronology is not exactly the table above, a residual
   month retains at most 99% of labels, a taxonomy edge repeats, or a canonical
   group has fewer than 1,000 observations.
3. Stop and report if any monthly budget is not filled, HiGHS is not optimal,
   a C2 point-score moment misses by more than `1e-10`, or plug-in dominance
   fails by more than `1e-5` dollars.
4. Do not alter any locked scientific choice after inspecting 2015 or 2017.
   A coding defect may be fixed only with an erratum, a fresh run tag, and a
   complete rerun of both new origins.
5. If results differ by origin, preserve the heterogeneity. Do not search for
   a fourth origin or a narrower horizon to manufacture uniformity.

## Reproducibility contract

The protocol, configurations, generalized chronology validator, and tests must
be committed and tagged before either new outcome-free freeze. Each origin uses
an immutable run directory and a two-phase freeze/evaluate workflow. A single
aggregation script must verify protocol hashes, select the declared 2016
months, reconcile cell keys, and emit both machine-readable evidence and a
human-readable report without editing source artifacts.
