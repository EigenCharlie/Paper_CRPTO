# IJDS Claim Concept Audit: Alpha Grid, Robust Region, Bound, and Exact Frontier

Date: 2026-06-26

This memo audits the concepts that are easy to take for granted in the CRPTO
paper narrative. The goal is not to weaken the paper, but to make the strongest
IJDS-facing claim precise enough that it survives reviewer scrutiny.

## Current Run Snapshot

Active branch: `codex/champion-reopen-2026-06`.

Active pool93 run:

- run tag: `champion-reopen-2026-06-19__pool93__ijds-local-refine-stage1`
- stage: local exact refinement around ranks 96, 219, and 223
- total exact checks: 6,520
- latest observed progress: about 47.6%
- latest ETA at that point: about 9.3 hours

The current partial leaderboard is already informative:

- 815 local policies have appeared in the leaderboard.
- 329 policies pass all currently evaluated alpha checks and exceed the previous
  champion return reference.
- The current max-return local policy is around 222.6K realized return with
  `V(0.01)=0.071075` and `Gamma_CP(0.01)=0.459280`.
- The rank-219/rank-223 anchors are less explosive in return, but much cleaner
  for a bound-facing claim, with `Gamma_CP` around 0.205--0.223 and
  `V(0.01)` around 0.0446--0.0456 while still exceeding the previous champion
  return.

Interpretation: pool93 is not just producing one candidate. It is producing a
claim frontier: max realized return, tighter conformal premium, lower weighted
miscoverage, and balanced return-bound trade-offs.

Later in the same partial run, after the bound-efficient neighborhood started
arriving, the more defensible IJDS lens became clear. The paper-facing bound
quantity is not `Gamma_CP` alone; it is the endpoint budget implied by Theorem 1,

`tau + (1 - gamma) * Gamma_CP`,

and the corresponding Markov cap,

`tau + (1 - gamma) * Gamma_CP + sqrt(alpha)`.

Under that lens, the provisional `pool93` body-default claim should not be the
max-return endpoint. The better IJDS-facing candidate is the return-bound point
that improves realized return while tightening the theorem's endpoint budget.
At the latest audited partial snapshot, that point is:

- `local_candidate_id = 462`
- `local_family = bound_efficient_local`
- `risk_tolerance = 0.1725`, `gamma = 0.50`, `uncertainty_aversion = 0.10`
- realized return: `$183,832.67`
- return surplus versus the previous champion reference: `$13,368.13`
- `Gamma_CP(0.01) = 0.176347`
- `V(0.01) = 0.041341`
- endpoint budget: `0.2606735`
- Markov loss cap: `0.3606735`
- all-alpha pass count: `8/8` on the finite alpha grid

For comparison, the previous champion has endpoint budget
`0.175 + 0.55 * 0.187987 = 0.27839285` and Markov cap `0.37839285`.
Thus the provisional return-bound candidate is more modest than the max-return
frontier endpoint, but it gives a cleaner paper claim: higher realized return
and tighter theorem-facing endpoint budget. Its realized `V` is higher than the
previous champion's `0.028875`, so the claim should not say "lower realized
weighted miscoverage versus the old champion"; it should say "all-alpha-grid
safe under the Markov audit, with tighter endpoint budget and higher return."

## 1. What `8/8` Really Means

In code, the number eight comes from the current alpha sweep artifact and the
default alpha grid:

```python
DEFAULT_ALPHAS = [0.01, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.20]
```

These are the eight supported conformal levels in
`data/processed/alpha_sweep_pareto_mondrian.parquet`. Therefore `8/8` means:

> The policy passed every alpha level in the pre-specified finite alpha grid
> A = {0.01, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.20}.

It does not mean:

- a theorem requires exactly eight alpha values;
- all possible alpha values in (0, 1) were certified;
- the policy has universal conditional coverage;
- the policy is guaranteed for every future portfolio selection.

The related literature supports pre-specified risk or coverage levels, not a
canonical eight-point alpha grid. Conformal Risk Control controls expected
monotone losses at user-chosen levels; Risk-Controlling Prediction Sets and
Learn-Then-Test calibrate predictive algorithms to satisfy explicit finite-sample
risk criteria; conformal robust optimization papers use conformal sets as
uncertainty sets at declared coverage levels. None of these sources says the
audit must contain eight alpha levels.

Primary sources checked for this point:

- Angelopoulos et al., Conformal Risk Control, ICLR 2024:
  https://openreview.net/forum?id=33XGfHLtZg
- Bates et al., Distribution-Free, Risk-Controlling Prediction Sets:
  https://arxiv.org/abs/2101.02703
- Angelopoulos et al., Learn Then Test:
  https://arxiv.org/abs/2110.01052
- Johnstone and Cox, Conformal Uncertainty Sets for Robust Optimization:
  https://proceedings.mlr.press/v152/johnstone21a.html
- Patel et al., Conformal Contextual Robust Optimization, AISTATS 2024:
  https://proceedings.mlr.press/v238/patel24a.html
- Sun et al., Predict-then-Calibrate:
  https://arxiv.org/abs/2305.15686
- Bertsimas and Sim, The Price of Robustness:
  https://pubsonline.informs.org/doi/10.1287/opre.1030.0065

Recommended paper language:

> The promoted policy passes all evaluated levels in the pre-specified alpha
> grid, `8/8` over A = {0.01, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.20}.

Avoid:

> The policy is robust for all alpha.

If we want a stronger claim, the correct next step is to generate and freeze a
denser conformal alpha sweep, then rerun exact validation on that declared grid.
Interpolating unsupported alphas would be useful as a diagnostic curve, but not
as the primary certificate.

## 2. What The Robust Region Really Means

The existing `45/45` region means:

> Every policy in a finite, declared local policy grid passed the exact alpha01
> check.

For the current paper champion this grid is described as the cross-product of
five risk-tolerance values, three gamma values, and three uncertainty-aversion
settings within the bound-aware family.

This is valuable because it shows the promoted policy is not an isolated lucky
point. But it is not the same as a continuous robust feasible region in the
mathematical programming sense. Classical robust optimization discusses
uncertainty sets, robust counterparts, protection levels, and price of
robustness. CRPTO's "robust region" is better described as a finite policy-grid
stability surface.

Recommended paper language:

> The final finite policy-grid region contains 45 evaluated policies, and all
> 45 pass the alpha01 exact funded-set audit.

For pool93 local refinement, the equivalent claim should be reported as:

- exact evaluated policies;
- number and rate of all-alpha passers;
- number and rate of passers above champion-return reference;
- family-level pass rates;
- the alpha set used.

Do not transfer the old `45/45` phrase to pool93 unless the final selected
pool93 region is explicitly defined and frozen with exactly 45 policies. A
larger and better pool93 region can be stronger, but it needs its own denominator.

## 3. What The Bound Actually Certifies

The current implementation checks each alpha by computing:

- `weighted_miscoverage_V = sum_i w_i 1{Y_i > u_i(alpha)}`
- `gamma_cp = sum_i w_i clip(u_i(alpha) - p_hat_i, 0, 1)`
- `weighted_pd_true = sum_i w_i Y_i`
- `violation = max(0, weighted_pd_true - tau)`
- `all_bounds_hold = (violation <= alpha) and (V <= sqrt(alpha))`

The strongest clean theoretical object is:

1. A deterministic accounting identity: for fixed weights, realized loss is
   bounded by the conformal upper-endpoint budget plus realized weighted
   miscoverage.
2. A Markov bound under the explicit assumption
   `E[V(alpha)] <= alpha`.
3. An exact frozen funded-set audit showing the selected policy's realized
   `V`, `Gamma_CP`, violation, and pass/fail indicators.

The manuscript is already honest on the key point: for the existing champion,
`V(0.01)=0.028875` is above `alpha=0.01`, so the paper must not claim nominal
funded-set alpha coverage. The operative audit is `V <= sqrt(alpha)` and zero
violation, together with the explicit weighted funded-set validity assumption.

For IJDS this is a strength, not a weakness, if framed correctly:

> CRPTO separates deterministic portfolio accounting, distribution-free
> first-moment risk control under a stated funded-set validity assumption, and a
> frozen exact empirical certificate.

Avoid:

> The conformal method guarantees the selected funded set has 99% coverage.

## 4. What "Exact Frontier" Should Mean

The exact refinement is exact in the allocation solve for a fixed policy and
fixed alpha. It is not a proof of global optimality over all possible policy
families or continuous hyperparameter values.

Therefore:

- "exact full-universe rerank" is correct;
- "exact policy-grid frontier" is correct;
- "global exact optimum" is too strong unless the full continuous search space is
  formally restricted to the declared finite grid.

The pool93 local refinement improves the IJDS position because it ranks using
metrics from the exact full-universe allocation itself, not the earlier
frontier/proxy score. That is a better evidence chain for the paper.

Recommended default artifact for the paper:

- do not promote a single max-return point alone;
- promote a frontier with three named points:
  - economic max-return point;
  - bound-efficient point, ranked by `tau + (1-gamma) Gamma_CP + sqrt(alpha)`;
  - balanced IJDS point, ranked by a declared return-bound score.

This gives reviewers a principled choice surface rather than asking them to
accept one lucky corner. If the final pool93 result is promoted, the artifact
should expose the alpha grid, all-alpha denominator, candidate region
denominator, and claim lens used to select the paper-facing point.

## 5. The Biggest Remaining Conceptual Risk: Post-Selection

The optimizer does not see OOT labels when solving a fixed policy. However, the
research process can still overfit the OOT backtest if the final policy is chosen
because it has the best realized OOT return after many policies have been tried.

That does not invalidate the result, but it changes the claim:

- safe claim: retrospective frozen backtest plus exact funded-set certificate;
- stronger claim: predeclared policy selection rule evaluated once on untouched
  final OOT labels;
- strongest claim: nested temporal selection/evaluation or prospective replay.

For the current pool93 local refinement, the safest IJDS framing is:

> The search identifies a certified return-bound frontier on a frozen OOT
> backtest. Promotion should prefer a policy selected by a declared
> return-bound criterion, not solely by the realized-return maximum.

This is why the rank-219/rank-223 anchors matter. They are not just backup
policies; they are selection-bias insurance for the paper narrative.

## 6. Academic-Researcher Skill Audit

The `academic-researcher` skill recommends exactly the discipline needed here:

- define the claim target;
- define the evidence gate;
- define the artifact sink;
- define the stop rule;
- promote only what is supported by the artifact; park or archive the rest.

That skill is valuable for CRPTO. The current paper already follows much of it
through claim ladders, assumption maps, frozen artifacts, and negative-result
boundaries.

No installed skill named `crpto` was found in the visible skill registry for this
session. The CRPTO-specific source of truth is therefore the project itself:
scripts, frozen artifacts, Quarto manuscript, supplement, and research memos.

## 7. Recommended Claim Hierarchy For IJDS

Tier 1, strongest and safest:

> A frozen PD-calibration-conformal-optimization pipeline maps calibrated credit
> uncertainty into an auditable robust portfolio decision, with exact funded-set
> accounting on a full OOT universe.

Tier 2, empirical but defensible:

> The selected pool93 policy lies on a finite exact policy-grid frontier where
> all evaluated alpha levels in the declared grid pass the exact audit.

Tier 3, economic:

> The frontier contains policies that exceed the previous champion return while
> preserving zero violation and all-alpha-grid pass status.

Tier 4, optional if the final region supports it:

> The result is not isolated: a declared local policy-grid region has a high
> all-alpha pass rate, and a material subset of that region exceeds the champion
> return reference.

Do not make the primary paper claim:

- AUC leaderboard dominance;
- universal coverage of adaptively selected portfolios;
- global optimality over all policies;
- continuous-region robustness unless we explicitly solve or prove it.

## 8. Recommended Next Experimental Guardrail

After stage1 completes:

1. Freeze the exact alpha grid in the claim summary.
2. Report both count and denominator, never only `8/8`.
3. Choose the IJDS candidate from a predeclared claim score, for example:

   `pass_all_alpha_grid = true`
   `champion_return_surplus > 0`
   then maximize a balanced score over normalized return surplus, the inverse
   Markov loss cap, and inverse `V`.

4. Keep the pure max-return point as an economic frontier endpoint.
5. Keep the rank-219/rank-223 family as the bound-efficient endpoint.
6. If the local stage reveals a clean contiguous region, only then run expanded
   exact refinement around that region.

This makes the paper stronger because it shifts the story from "we found a big
number" to "we found a certified decision frontier and promoted the point whose
claim is hardest to attack."

## 9. Final Pool93 Closure Update - 2026-07-02

The terminal pool93 search closed the concept audit with a stronger and cleaner
denominator than the earlier `45/45` language:

- terminal endpoint search: 37,068 policies and 296,544 exact alpha checks;
- terminal all-alpha passers: 37,068/37,068;
- terminal all-alpha passers above the declared return floor: 14,814/37,068;
- consolidated semantic frontier: 50,010 deduplicated policies;
- consolidated eligible all-alpha and above-floor policies: 27,508;
- declared alpha grid remains the finite set
  `{0.01, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.20}`.

The strongest IJDS claim is now a finite-grid return-bound frontier, not a
single champion and not a continuous robust region. The recommended paper-facing
roles are:

| Role | Candidate | Return | Gamma_CP | V | Markov cap | Destination |
|---|---:|---:|---:|---:|---:|---|
| Body/default balanced point | 131 | 184,832.475845 | 0.162616 | 0.035350 | 0.345083740 | Body |
| Strict cap <= 0.345 proxy | 512 | 184,800.413581 | 0.162562 | 0.035350 | 0.344996495 | Body footnote or supplement |
| Above-floor minimum-cap endpoint | 10661 | 170,467.268819 | 0.095719 | 0.031875 | 0.273035950 | Body frontier sentence and supplement |
| Max-return endpoint | 4041 | 223,458.135875 | 0.457438 | 0.069575 | 0.510753090 | Supplement/frontier endpoint |

Final claim wording:

> CRPTO reports a frozen finite-grid exact return-bound frontier for credit
> allocation. On the Lending Club OOT universe, the selected pool93 body point
> earns 184.8K on a 1M budget, passes all eight declared alpha levels, and has
> Gamma_CP = 0.1626, V = 0.03535, and Markov cap = 0.3451. The same frontier
> contains an above-floor bound endpoint with Markov cap = 0.2730 and an
> economic endpoint above 223K, making the return-bound tradeoff explicit.

What changes conceptually:

- `8/8` remains a finite alpha-grid certificate; it is not universal alpha
  coverage.
- "Robust region" should be replaced by "finite policy-grid robustness
  surface" or "finite-grid return-bound frontier" with explicit denominators.
- The bound claim remains Theorem 1 plus Assumption 1 plus exact audit. It does
  not become a post-selection conformal theorem.
- The terminal endpoint is valuable because it improves the bound cap; it does
  not replace the body/default point, whose role is to be useful and defensible
  as the manuscript's main economic decision.
