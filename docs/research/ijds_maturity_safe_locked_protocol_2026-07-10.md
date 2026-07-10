# Locked maturity-safe IJDS protocol (2026-07-10)

## Status

This document and
`configs/experiments/ijds_maturity_safe_locked_h1h2_2026-07-10.yaml` define the
confirmatory retrospective run before its 2016--2017 outcomes are analyzed.
The required Git tag is
`protocol/ijds-maturity-safe-locked-h1h2-2026-07-10-v1`. The runner refuses to
start unless that tag points to a clean current `HEAD`.

The earlier seven-month maturity-safe output is exploratory scratch evidence.
It cannot be promoted, pooled with this run, or used to alter this protocol.

## Research question

Under slow outcome maturity and temporal shift, can a conformal-upper-score
guardrail selected only on mature historical cohorts improve monthly credit
portfolio decisions relative to point-PD policies, and why does marginal
binary-outcome conformal coverage fail to transport to the funded set?

## Locked chronology

| Role | Issue window | Use |
|---|---:|---|
| PD development | through 2010-12 | fixed CatBoost fit and temporal validation tail |
| Probability calibration | 2011-01 to 2011-12 | Platt calibration only |
| Conformal fit | 2012-01 to 2012-06 | exact Mondrian absolute-residual recipe |
| Policy development | 2012-07 to 2012-12 | one-time policy selection using mature outcomes |
| Primary OOT | 2016-04 to 2017-06 | 15 monthly confirmatory decisions |
| Censored extension | 2017-07 to 2017-09 | three monthly decisions with sharp unresolved bounds |

Membership is determined by issue date and 36-month term only. Loan status may
label an outcome after membership but may never determine candidate inclusion.
The 40-month gap from 2012-12 to 2016-04 exceeds the declared 39-month minimum.

## Frozen methods

- Model: the YAML's fixed CatBoost hyperparameters; no HPO or refit after 2010.
- Calibration: Platt scaling on 2011 raw margins.
- Conformal object: a prediction interval for the observed binary outcome,
  grouped by five calibrated-score quantiles fitted on 2012H1. It is not a
  confidence interval for latent PD.
- Policy score: `q=(1-gamma)p+gamma U`, where `U` is the binary-outcome
  conformal upper endpoint used as a decision score.
- Objective: coherent standardized payoff `(1-p)r-p*LGD`, with `LGD=0.45`.
  Realized evaluation uses `(1-y)r-y*LGD`. This is not cash-flow IRR, NPV, or a
  causal return estimate.
- Constraints: fresh `$1,000,000` monthly budget, full utilization, and at most
  25% exposure by loan purpose. The historical `B_U <= 0.28` endpoint screen is
  removed.

## Policy selection and comparators

The guardrail grid is the fixed Cartesian product
`tau in {0.15,0.17,0.19}` and `gamma in {0.25,0.50,0.75}`. Each candidate is
solved separately in every month of 2012H2. Among candidates that use the full
budget in all six months, the selector maximizes summed realized coherent
payoff, then summed expected payoff, then lexicographic `candidate_id`.

Three policies are frozen before future outcomes are materialized:

1. The development-selected conformal guardrail.
2. A point-PD policy with the guardrail's same `tau`.
3. A point-PD policy whose `tau` is selected independently on 2012H2 by the
   same rule.

No 2016--2017 outcome may change the model, calibrator, conformal recipe, grid,
policy, dates, payoff, constraints, or comparison set.

## Primary evidence and interpretation

The primary table reports each fixed policy's monthly and pooled standardized
payoff, default, miscoverage, effective score, allocation, and group exposure.
Contrasts are retrospective and noncausal.

For default and binary miscoverage, the exact primary decomposition is

`funded - reference = (row - reference) + (candidate exposure - row)`

`+ (funded group mix - candidate exposure) + (funded - funded group mix)`.

The four terms are labeled temporal/population, row-to-exposure, group
composition, and within-group selection. This identity distinguishes marginal
coverage from exposure weighting and optimizer-induced selection. A policy may
improve payoff or default without preserving selected-set coverage; such a
result is a mechanism finding, not a failed implementation.

## Decision rules after the run

- A positive decision claim requires the guardrail to outperform the
  independently selected point-PD policy on primary realized standardized
  payoff without hiding default, coverage, or monthly instability.
- Marginal all-candidate coverage is reported as an empirical temporal audit,
  never as a four-year guarantee.
- Funded-set coverage is descriptive. It cannot be called conformal validity.
- Extension outcomes are reported as bounds whenever unresolved; they cannot
  replace the primary result.
- If the guardrail does not dominate economically, the paper becomes an audit
  and mechanism paper about maturity, objective coherence, and coverage
  transport. No post-result retuning is allowed.
- The 2018--2020 cohorts remain a censoring/menu illustration only.

## Protected boundaries

The run writes only fresh children of the allowlisted experiment roots. It does
not invoke protected DVC stages, alter `EXTRACTION_MANIFEST.json`, overwrite
the frozen champion, or promote an artifact automatically.

## Execution record

The tagged v1 execution halted before writing a result summary because at
least one status-independent primary candidate remained unresolved at the
2020-09-30 snapshot. No realized contrast was printed or persisted. The run
directory contains only its pre-future `protocol_freeze.json` and is retained
unchanged. The bounded v2 amendment is registered separately; it changes no
date, model, policy, comparator, objective, or metric.
