# CRPTO Regret-Auditability Sandbox Closure - 2026-05-28

> Ported from the CRPTO research archive
> (`paper1_regret_auditability_sandbox_closure_2026-05-28`). **Documentation
> only.** This is the closure record of the broader regret-auditability search:
> the frozen champion (`paper-thesis-final-economic-2026-04-06`) is **not**
> replaced. (The earlier feature-search plan and sandbox dependency report were
> retired in the 2026-06-13 docs cleanup; this closure is the surviving record.)

## Purpose

Closes the external CRPTO regret-auditability sandbox intake. The sandbox was
created **outside this repository** (in an external experiments volume). The
question was whether a much broader CatBoost monotone + Optuna + Venn-Abers +
Mondrian conformal + robust portfolio search could improve the CRPTO champion,
or at least strengthen the paper's evidence around the regret-auditability
frontier.

## Closure Decision

The sandbox was useful, but it does not replace the frozen economic champion by
itself. It produced credible PD and conformal challenger evidence, triggered a
governed champion tournament, and generated negative-result evidence useful for
IJDS-style documentation. However, the downstream portfolio and bound evidence
does not produce a clean new champion that dominates the frozen policy on return,
`V`, `Gamma_CP`, violation, and coverage at the same time.

Frozen champion reference (unchanged):

- realized return: `170464.5429284627`
- `V`: `0.03645`
- `Gamma_CP`: `0.18591`
- violation: `0`
- funded coverage: `0.9433`
- policy: `blended_uncertainty`, risk `0.175`, gamma `0.45`, uncertainty
  aversion `0.1`
- region: `45/45`

## What Was Evaluated (archive-staged, not promoted)

The useful sandbox material was absorbed in the CRPTO research archive through paper-facing and
research artifacts (the dated CSV tables and staged PD challenger models live in
the CRPTO research archive; the child keeps the **conclusions** below, not the
challenger weights). Child-side companions:

- [crpto_bound_improvement_intake_2026-05-21](crpto_bound_improvement_intake_2026-05-21.md)
- [crpto_champion_reopen_plan_2026-05-21](crpto_champion_reopen_plan_2026-05-21.md)
- [crpto_champion_tournament_protocol_2026-05-25](crpto_champion_tournament_protocol_2026-05-25.md)

Three external PD challengers were staged in the CRPTO research archive and evaluated:
`bureau_behavior_15`, `affordability_rate_5`, `canonical_4`. None were promoted.

## PD Findings

The strongest sandbox contribution was the PD search. It showed the frozen PD
stack was not the predictive ceiling.

| Role | Candidate | AUC | Brier | ECE | Use |
| --- | ---: | ---: | ---: | --- |
| incumbent | `incumbent__frozen_champion` | `0.712678` | `0.154591` | `0.006152` | frozen reference |
| challenger | `full_challenger_woe__bureau_behavior_15` | `0.720679` | `0.153161` | `0.007689` | main challenger |
| challenger | `full_challenger__canonical_4` | `0.720624` | `0.153182` | `0.005917` | sensitivity baseline |
| challenger | `full_challenger_woe__affordability_rate_5` | `0.720052` | `0.153276` | `0.007502` | sensitivity baseline |

Interpretation:

- `bureau_behavior_15` is the best pure discrimination/Brier signal (AUC +0.008),
  but its ECE is worse than the incumbent and it carries a higher
  feature-governance burden.
- `canonical_4` is a cleaner governance sensitivity: nearly the same AUC lift,
  better Brier than incumbent, better ECE than the incumbent replay.
- `affordability_rate_5` tests whether affordability monotonicity and WOE
  transformations add a stable signal.

This is strong enough for a challenger appendix and a gated champion-reopen
protocol, but not enough by itself to change the CRPTO claim.

## Conformal Findings

The sandbox selected a usable but non-final conformal configuration (partition
`grade`, raw probability source, 5 score bins, `grade_then_global` fallback,
alpha90 `0.075`, alpha95 `0.06`, min group size `100`, `bernoulli_sqrt` scaling).
The follow-up showed why it should remain a challenger:

| Candidate | coverage90 | min group cov90 | avg width90 | worst group | Reading |
| --- | ---: | ---: | ---: | --- | --- |
| `affordability_rate_5` | `0.944317` | `0.916647` | `0.806270` | `score_q00` | viable but wider |
| `bureau_behavior_15` | `0.919951` | `0.870059` | `0.749615` | `E` | rare-grade weakness |
| `canonical_4` | `0.931878` | `0.917582` | `0.790729` | `score_q04` | viable sensitivity |
| `official_champion` | `0.929714` | `0.918983` | `0.784230` | `score_q03` | still balanced |

The conformal search revealed where PD improvements transfer cleanly and where
they create rare-grade weaknesses. `bureau_behavior_15` is predictive, but its
grade `E` weakness makes it hard to promote without further conformal repair.

## Portfolio And Bound Findings

The portfolio layer is where the frozen champion remains strongest as a balanced
paper-facing claim. The archived decision table contained 73 exact/pass decision
rows:

- `35` append-or-park rows with no champion case
- `20` Gamma-only challengers with worse V/return
- `9` V-only challengers with worse Gamma/return
- `7` bound-only challengers with worse return
- `1` return-only challenger with worse bounds
- `1` official baseline row

The best positive-return challenger found:

- candidate: `canonical_4_return_aware`
- return: `170611.34163424745` (delta vs champion `+146.80`)
- `V`: `0.058675`; `Gamma_CP`: `0.270366`; violation: `0`
- decision: `return_challenger_only_bound_worse`

The best V/Gamma challengers improved one bound dimension but paid too much in
return or worsened the other bound dimension. Useful negative evidence: the broad
search did not find a free lunch.

## Scientific Value For IJDS

1. Supports an anti-cherry-pick story: the project reopened PD, conformal, and
   portfolio under explicit gates rather than stopping at the first champion.
2. Clarifies the regret-auditability frontier: higher-return candidates exist,
   but they tend to weaken `V`, `Gamma_CP`, funded coverage, or group coverage.
3. Provides credible negative results: publishable as appendix/robustness
   evidence showing why the frozen champion remains the main balanced policy.
4. Separates predictive improvement from decision improvement: better AUC does
   not automatically imply a better robust portfolio under conformal guarantees.

Recommended paper framing: main text keeps the frozen economic champion as the
primary CRPTO result; appendix reports the governed reopen/tournament as
robustness and sensitivity evidence; agenda extendida CRPTO/tesis / methods appendix uses the
regret-auditability frontier and PyEPO regret suite to discuss decision
efficiency vs auditability.

## What Should Not Be Claimed

- Do not claim the sandbox produced a new champion unless a later sealed
  full-universe confirmation passes all champion replacement gates.
- Do not compare a child 25k quick portfolio return directly against the frozen
  276k champion.
- Do not promote `bureau_behavior_15` on AUC alone while the conformal rare-grade
  weakness remains unresolved.
- Do not treat high-return portfolio probes as paper champions when their
  `V`/`Gamma_CP` trade-off is worse than the frozen policy.

## Remaining Optional Work (only if pursuing replacement)

- run a sealed full-universe cuOpt + HiGHS rerank for a small predeclared set;
- repair or explicitly park the `bureau_behavior_15` grade `E` conformal issue;
- decide whether `canonical_4` becomes the main appendix challenger (cleanest
  PD/calibration/conformal balance);
- export a final negative-results registry for the IJDS appendix;
- avoid further open-ended search unless the protocol version is reopened before
  seeing downstream results.

## Final Closure Note

The sandbox is successful as evidence generation, not as a champion replacement.
It gave stronger PD challengers, a more rigorous conformal/portfolio tournament,
and a clearer empirical case for CRPTO's central tension: robust auditability can
be bought, but it is not free in return/regret space.
