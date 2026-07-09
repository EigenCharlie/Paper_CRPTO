# CRPTO Active Claim Registry - 2026-07-09

This registry is the current source of truth for paper-facing CRPTO claims. It
supersedes older research notes that centered the `45/45` local region or the
`paper-thesis-final-economic-2026-04-06` run as the active manuscript result.
Those notes remain useful as provenance, not as active operating instructions.

## Active Body Claim

CRPTO is an auditable conformal-robust credit-portfolio decision certificate:
a frozen calibrated PD model feeds Mondrian conformal upper endpoints, an
exact finite policy-grid portfolio search exposes a return-bound frontier, and
the selected funded set is audited on the full OOT universe.

Current body/default point:

- terminal run tag:
  `champion-reopen-2026-06-19__pool93__ijds-claim-bound-terminal`
- active certificate-semantics tag:
  `champion-reopen-2026-06-19__pool93__ijds-certificate-semantics-v2`
- body point source run:
  `champion-reopen-2026-06-19__pool93__ijds-claim-micro-ext`
- policy family: `claim_micro_ext_body_cap345`
- policy mode: `capped_blended_uncertainty`
- risk tolerance: `0.1715`
- gamma: `0.5475`
- delta cap quantile: `0.975`
- uncertainty aversion: `0.05`
- realized return on a 1M budget: `$184,832.48`
- return-floor surplus: `$14,367.94`
- `V(alpha=0.01)`: `0.035350`
- `Gamma_CP(alpha=0.01)`: `0.162616`
- `Gamma_internalized(alpha=0.01)`: `0.089032`
- `Gamma_residual(alpha=0.01)`: `0.073584`
- exact endpoint budget at `alpha=0.01`: `0.245083866` (`0.245084` paper rounding)
- exact Markov loss threshold at `alpha=0.01`: `0.345083866` (`0.345084` paper rounding)
- realized risk-tolerance excess: `0.0`
- declared alpha-grid pass: `8/8`
- fixed-allocation bootstrap return interval:
  `$167,963.20`--`$198,650.47`

Do not describe this as a newly retrained champion. The active pool93 claim is a
deterministic policy-grid re-evaluation over the same frozen upstream PD model,
calibrator and conformal interval outputs.

## Active Evidence

| Claim | Decision | Destination | Evidence | Stop Rule |
|---|---|---|---|---|
| CRPTO is a decision certificate, not a classifier leaderboard. | Promote | body | `paper/CRPTO_ijds.qmd`, Figure 1, exact certificate table, A35 | Do not reopen unless the decision certificate changes. |
| The pool93 body point is selected from a finite exact return-bound frontier. | Promote | body + A35 | `crpto_tableA35_pool93_ijds_frontier.csv`, certificate-semantics-v2 frontier/governance JSON | Do not run more portfolio search unless a new result can lower the exact threshold at the same return or materially lift return under the declared threshold. |
| The selected allocation has inspectable business composition and tail profile. | Append | supplement A36--A39 | A36 grade audit, A37 LGD/CVaR/OCE repricing, A38 cluster-bound audit, A39 bootstrap | Diagnostics only; do not use as hidden selector. |
| The conformal decision has a matched point-PD baseline. | Promote | body + supplement A40 | A40 table and `pool93_point_pd_baseline_audit.json` | Treat as one frozen OOT trade-off; do not claim causal or universal dominance. |
| The former `45/45` rebaseline remains provenance and return floor. | Archive/Append | provenance/supplement | `EXTRACTION_MANIFEST.json`, `ijds_rebaseline_2026-06-07.md` | Do not use as active headline except to explain the declared floor. |
| External Prosper/Freddie runs support recipe transfer. | Append | body short paragraph + supplement A25--A34 | external replication tables and figures | Do not promote as new Lending Club certificates. |

## Finite-Grid Semantics

The declared alpha grid is:

`A = {0.01, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.20}`.

Therefore, the maximum possible alpha-grid pass for a single policy under the
current evidence bundle is `8/8`. A different maximum would require a new,
explicitly declared alpha grid and regenerated exact validation outputs.

For the terminal endpoint run:

- `n_policies = 37,068`
- `|A| = 8`
- maximum exact candidate-alpha checks:
  `37,068 * 8 = 296,544`
- observed completion: `296,544/296,544`
- all-alpha passers: `37,068/37,068`
- all-alpha passers above the declared return floor: `14,814/37,068`

For the consolidated frontier:

- raw rows: `51,678`
- duplicate semantic rows removed: `1,668`
- maximum deduplicated semantic policies in this consolidated evidence file:
  `50,010`
- eligible all-alpha above-floor policies: `27,508/50,010`
- nonpass or below-floor policies: `22,502/50,010`

The v2 policy-aware rehydration uses the stored exact endpoint budget instead of
the linear-only residual shortcut. It changes neither denominator nor the body
selection, but changes 10,423 policy thresholds materially. Of these, 2,866
tail/segment-tail policies were understated; the maximum understatement was
`0.241324`, and 716 policies formerly labeled at or below `0.50` exceed `0.50`
on the exact endpoint scale. The max-return endpoint is therefore `0.697056`,
not the retired linear-shortcut value.

These denominators are finite-grid denominators, not continuous optimality
claims. If a later, separately tagged run adds new policy families, gamma
values, alpha levels or solvers, the denominators can grow under that run tag;
they must not be mixed with the current frozen denominators.

## How To Present The Denominators

The result should be presented as a finite-grid decision certificate, using the
same style that robust optimization and conformal risk-control papers use for
tunable risk levels: state the declared grid, report the denominator, expose the
trade-off frontier, and separate the selected body point from endpoints.

Recommended body wording:

> The selected policy is chosen from a declared finite policy-grid frontier. The
> consolidated frontier contains 50,010 deduplicated semantic policies, of which
> 27,508 both pass every declared alpha level and exceed the return floor. The
> terminal exact endpoint search evaluates 37,068 policies across eight alpha
> levels, for 296,544 candidate-alpha checks, and all terminal policies pass the
> all-alpha audit. These counts certify the declared finite search surface; they
> are not a continuous global-optimality claim.

Use `pool93` only for run tags, file names, governance JSONs, and internal
provenance. The body manuscript should say selected policy, selected decision,
or declared finite-grid frontier unless the run label is needed to disambiguate
an evidence source.

Report the screenshot numbers with explicit denominators:

- `alpha_grid_pass = 8/8`: one selected policy passed all eight declared alpha
  levels. The current maximum is eight because the alpha grid has eight
  levels.
- `50,010` semantic policies: the maximum deduplicated policy denominator in
  the current consolidated frontier. It equals `51,678` raw rows minus `1,668`
  duplicate semantic policies.
- `27,508` eligible all-alpha above-floor policies: the number of consolidated
  semantic policies that satisfy both gates: all-alpha pass and nonnegative
  surplus over the declared return floor.
- `37,068/37,068` terminal all-alpha passers: every policy in the terminal
  endpoint search passed all eight declared alpha checks.
- `296,544/296,544` exact terminal checks: the run completed all
  `37,068 * 8` policy-alpha evaluations. This is primarily a completion
  denominator; because all 37,068 policies are all-alpha passers, it also means
  there were no failed alpha cells inside the terminal surface.

Do not present these as:

- proof over all possible policy hyperparameters;
- proof over all possible alpha values in `(0, 1)`;
- a live-production coverage guarantee after adaptive policy selection;
- evidence that more policies are always better.

## Baseline Semantics Boundary

The frozen Lending Club field `price_of_robustness=-10.56%` is historical
provenance, not an active IJDS claim. Its stored `nonrobust` solve inherited an
endpoint constraint and therefore was not a point-PD comparator. A40 replaces
that field with a matched two-stage LP at the selected policy's `tau=0.1715`,
holding 276,869 candidates, budget, concentration, LGD, solver, and operating
constraints fixed. The point-PD allocation earns `$196,369.14`; selected CRPTO
earns `$184,832.48`, a cost of `$11,536.66` (`5.875%`). CRPTO reduces weighted
default/miscoverage by `0.08305` and the exact Markov threshold by `0.435495`.
See `pool93_certificate_semantics_v2_2026-07-09.md`.

This correction does not alter the selected pool93 allocation, its realized
return, `V`, `Gamma_CP`, exact Markov threshold, zero realized risk-tolerance
excess, alpha-grid pass, or finite-grid denominators. The active Lending Club
comparison is A40, interpreted jointly with the A35 exact return--bound
frontier. Frozen Table 0/Table 1/A2 fields remain untouched for
manifest provenance and must not be cited as evidence of robust dominance over
a point estimate. Historical A/B proxy flags that inherited that comparator are
also non-promoted.

The IJDS framing should emphasize data + methodology + decision + implication:
the finite-grid frontier is the decision object, the exact checks are the
auditable computation, and the endpoints expose the price of robustness.

## Theory Boundary

The paper-facing theorem uses deterministic accounting plus a distribution-free
Markov step under weighted funded-set validity. The body keeps Markov because
it is the weakest defensible assumption for the current selected allocation.
A38 reports cluster-aware thresholds as sensitivity; none is tighter than
Markov for the observed exposure concentration.

Every paper-facing policy now uses the policy-aware decomposition
`Gamma_CP = Gamma_internalized + Gamma_residual`, with exact endpoint budget
`B_u = sum(w*q) + Gamma_residual`. The shortcut
`Gamma_residual = (1-gamma) * Gamma_CP` is valid only for a pure linear blend.
It remains numerically valid for the selected capped policy because its row-level
cap is inactive on all 314 funded rows, but it must not be applied to tail or
segment-tail policies.

Do not claim:

- universal conditional coverage;
- global optimum over continuous policy parameters;
- future live-deployment validity;
- a CVaR/OCE/bootstrap-selected champion;
- that `8/8` is an external standard rather than the declared grid.

Literature-informed boundary added after the 2026-07-08 corpus scan:

- Contextual optimization and credit-scoring uncertainty papers support the
  framing of CRPTO as prediction-to-decision data science, but they do not
  change the certificate object.
- Non-exchangeable conformal risk control, valid selection among conformal sets,
  inverse/decision-calibrated robustness, and learned decision-aware conformal
  sets are outside the submitted claim unless rerun under a new tag with an
  explicit selection/calibration design.
- The current finite-grid frontier is strong audit evidence for the declared
  frozen surface; it is not a stability-based or independent-recalibration
  theorem for selecting among many conformal sets.

## Reopen Gate

A new search is justified only if it can plausibly change one of these claims:

1. same or higher return with materially lower exact Markov threshold or `Gamma_CP`;
2. much higher return under the same declared threshold;
3. a denser predeclared alpha grid that materially strengthens the certificate;
4. a nested/prospective evaluation design that reduces post-selection risk;
5. a reviewer-requested diagnostic that closes a specific objection.

Otherwise, append the idea to research notes after submission and keep the
current pool93 frontier closed.
