# CRPTO Champion Reopen Plan - 2026-05-21

> Ported from the parent research factory
> (`paper1_champion_reopen_plan_2026-05-21`). **Documentation only.** Records the
> governed reopen sequence and non-negotiable gates. The frozen champion is not
> reopened by porting this plan; superseded in outcome by
> [crpto_regret_auditability_sandbox_closure_2026-05-28](crpto_regret_auditability_sandbox_closure_2026-05-28.md)
> (closure: append/park, no replacement). Any real reopen must not contradict
> `models/final_project_promotion.json`.

## Objective

Reopen the champion search only where new evidence can plausibly replace the
frozen champion and improve the theoretical bound. The target is one governed
challenger package with a promote / append / park decision, not another broad
artifact loop.

## Current Evidence

External PD search produced a credible replacement candidate:

- main challenger `full_challenger_woe__bureau_behavior_15`: AUC `0.720679` vs
  incumbent replay `0.712678` (`+0.008001`); Brier `0.153161` vs `0.154591`
  (`-0.001430`); ECE `0.007689` vs `0.006152` (`+0.001537`).
- sensitivity: `full_challenger__canonical_4` (AUC `0.720624`, Brier `0.153182`,
  ECE `0.005917`); `full_challenger_woe__affordability_rate_5` (AUC `0.720052`,
  Brier `0.153276`, ECE `0.007502`).

The external PD model expands the feature contract from 42 to 106 features
(adding 64 bureau/behavior/WOE features while retaining current features):
predictive upside with governance cost, so promotion requires downstream proof,
not AUC alone. The external conformal package is usable but not final (grade E
misses the strict 90% group gate; E/G weak at 95%), so the next search focuses
conformal before portfolio promotion.

## Non-Negotiable Gates

1. **PD gate.** AUC improvement at least `+0.005` vs frozen incumbent replay;
   Brier improvement or non-inferiority; ECE not worse by more than `+0.0025` (or
   a sensitivity candidate with better ECE stays competitive downstream); no
   monotonicity/threshold/governance regression that invalidates the MRM story.
2. **Conformal gate.** Global 90/95 coverage passes; minimum grade coverage at
   90% passes the strict floor with grade E explicitly resolved or caveated; grade
   E/F/G 95% weakness improves or is proven irrelevant to funded-set risk;
   width/Winkler does not inflate enough to destroy portfolio value.
3. **Portfolio gate.** Full-universe run (not 25k quick signal); exact `alpha01`
   and `alpha03` pass; `violation = 0`; `V <= sqrt(alpha)` at alpha01; robust
   return beats the frozen economic champion on the same universe, or improves
   bound metrics enough to become an appendix challenger rather than a
   replacement.
4. **Bound-improvement gate.** `Gamma_CP` falls, or `V` falls, or the same return
   is achieved with a cleaner proof surface; funded-set group weights do not hide
   subgroup failure; a sealed/nested confirmation run remains possible after
   candidate selection.

## Reopen Sequence

- **Phase 0 - Stage PD challengers.** Stage only the three external PD finalists
  as candidate artifacts (do not overwrite canonical PD artifacts). This makes
  existing conformal code work via an upstream-run-tag indirection without
  changing canonical champion files.
- **Phase 1 - Focused Conformal Reopen.** Run conformal reopen using the staged
  PD candidate as upstream. Keep Venn-Abers/calibrated and raw sources; compare
  `grade`, `score_decile_mondrian`, `grade_x_scoreband_mondrian`; force attention
  to grade E/F/G and temporal slices; prefer configurations that reduce
  `Gamma_CP` and keep funded-set coverage, not only global coverage. Output: one
  winning conformal namespace, one comparison table, one memo on whether grade
  E/G got resolved.
- **Phase 2 - Portfolio Reopen (cuOpt frontier + exact rerank).** RAPIDS env for
  frontier generation (`cuOpt`), exact HiGHS rerank delegated to `.venv`. Waves:
  smoke (`max_candidates=25000`, alpha grid `0.01,0.03,0.10`); medium
  (`100000`/`150000`, wider grids); full universe (`max_candidates=0`, full alpha
  grid, promotion decision vs `bound_aware_276k_economic_champion`).
- **Phase 3 - Bound Hardening.** Only after Phase 2 selects a serious candidate:
  funded-set Mondrian bound `sum_g W_g alpha_g`; decision-aware selector audit;
  dependency-aware diagnostic (cluster by `issue_month`, `grade`, state/source
  proxy); nested/sealed confirmation on a predeclared holdout; direct CRC/LTT loss
  only if it can change the main theorem or appendix bound.

## Stop Rules

Stop and park the challenger if any of these happen:

- PD improvement fails to survive conformal/portfolio downstream.
- Conformal fixes E/G only by making intervals so wide that `Gamma_CP` or return
  becomes unusable.
- Full-universe portfolio cannot beat the frozen champion and does not improve
  `V`/`Gamma_CP` meaningfully.
- The only remaining improvement requires unsupported IFRS9/ECL, live deployment,
  or legal fair-lending claims.

## Promotion Outcomes

- **Promote**: replace champion only if full-universe return and bound metrics
  beat the current champion under exact validation.
- **Append**: keep as stronger challenger appendix if PD/conformal improves but
  portfolio does not replace champion.
- **Park**: keep for Paper 4 if it teaches a method lesson but does not change
  CRPTO.
- **Delete/archive**: discard scratch runs and repeated variants that do not
  change the decision.
