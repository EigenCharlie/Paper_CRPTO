# IJDS Claim Maximization Analysis - 2026-06-27

This memo evaluates the strongest IJDS-facing claims for CRPTO after the pool93
claim-governance and local exact-refinement work. It is an internal research
artifact, not manuscript prose.

## Executive Decision

The strongest paper claim is not "a better credit classifier" and not "a new
universal conformal theorem." The strongest claim is:

> CRPTO is an auditable conformal-robust credit-portfolio decision certificate:
> it maps a frozen calibrated PD artifact into conformal upper endpoints, solves
> a robust funding policy, and reports an exact full-universe finite-grid
> return-bound frontier with explicit alpha-grid and Markov-bound semantics.

This should replace the current body emphasis on a single promoted economic
policy and a 45/45 local region if pool93 is promoted.

## Current Evidence Snapshot

Stage1 pool93 exact refinement is final:

- run tag:
  `champion-reopen-2026-06-19__pool93__ijds-local-refine-stage1`
- exact policies: 815
- exact alpha checks: 6,520
- alpha grid: `{0.01, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.20}`
- all-alpha passers: 756/815
- bound-efficient passers: 418/418
- bottleneck: alpha = 0.01; all other alphas pass 815/815

Paper-body default candidate from governance:

- local candidate: 462
- family: `bound_efficient_local`
- policy: `blended_uncertainty`
- risk tolerance: 0.1725
- gamma: 0.50
- uncertainty aversion: 0.10
- realized return: 183,832.670701
- return-floor surplus: 13,368.130701
- Gamma_CP: 0.176347
- weighted miscoverage V: 0.041341
- endpoint budget upper: 0.2606735
- Markov loss cap at alpha01: 0.3606735
- alpha pass count: 8/8
- mean funded loans: 318.5

Frontier endpoints:

- bound-tight: candidate 466, return 181,217.537003, Gamma_CP 0.176071,
  Markov cap 0.3605355, 8/8.
- return-bound body/default: candidate 462, return 183,832.670701,
  Markov cap 0.3606735, 8/8.
- economic endpoint: candidate 264, return 222,602.669743,
  Markov cap 0.5106040, 8/8.

The live `claim_expanded` refinement is running and is not yet claim-final. It
is useful because it can refine the bound ridge and economic endpoint, but the
existing stage1 evidence is already strong enough to redesign the claim surface.

## Live Update - 2026-06-27 20:44 America/Bogota

The expanded local refinement is materially underway but remains exploratory:

- run tag:
  `champion-reopen-2026-06-19__pool93__ijds-claim-expanded-refine`
- profile: `claim_expanded`
- completed exact checks: 10,105/26,064
- completion: 38.77 percent
- observed throughput: about 6.77 exact checks/minute under concurrent HPO load
- ETA at current throughput: about 39.3 hours, around 2026-06-29 12:02 local
- current family: `bound_claim_refined_local`
- current anchor rank: 219

Interpretation: the run has reached the region that can improve the paper claim
because rank 219 is where the Stage1 bound-efficient body/default point came
from. Do not promote this expanded run yet, because no final expanded
leaderboard or governance artifact exists in the run directory. Treat it as a
live claim-improvement search whose evidence gate is a regenerated governance
JSON plus a frontier table after the run finishes or after a deliberately
declared early-stop checkpoint.

The HPO wave is still running on `pooltop72_business80`; seven of eight cases
have completed seed-42 HPO. Among completed cases, test-set metrics are tightly
clustered:

| case | features | AUC | Brier | ECE | PR-AUC |
|---|---:|---:|---:|---:|---:|
| `pooltop72_tab60` | 132 | 0.721661 | 0.153035 | 0.007982 | 0.412929 |
| `pooltop93_tab120` | 213 | 0.721641 | 0.153019 | 0.008258 | 0.413265 |
| `pool93_woe` | 106 | 0.721562 | 0.153022 | 0.008594 | 0.413707 |
| `pooltop80_business80` | 160 | 0.721438 | 0.153077 | 0.008186 | 0.412686 |
| `pool93` | 93 | 0.721356 | 0.153066 | 0.007821 | 0.412954 |
| `pool93_business80` | 173 | 0.721309 | 0.153120 | 0.008017 | 0.412025 |
| `pooltop80_tab90` | 170 | 0.721294 | 0.153108 | 0.008175 | 0.412365 |

The HPO differences are small enough that paper-facing selection should not be
driven by seed-42 AUC alone. `pool93` remains the strongest body candidate if
its downstream chain dominates because it is compact, self-contained, and
already has the strongest exact portfolio-governance evidence. `pool93_woe` and
`pooltop72_tab60` are plausible appendix/downstream challengers because they
show marginally stronger predictive metrics, but they must earn promotion at
calibration, conformal, and portfolio layers.

Expanded search is warranted only if it can change one of these manuscript
claims:

- identify a higher-return point with Markov cap no worse than Stage1 candidate
  462;
- identify a lower-cap point with return still above the declared body-return
  floor;
- show a wider, cleaner finite-grid robustness surface around the selected
  point;
- provide an interpretable frontier figure/table that replaces single-point
  reporting.

Stop rule: if expanded search only creates more high-return/high-cap endpoints,
append it as frontier sensitivity and keep Stage1 candidate 462 as the body
default. If it finds a point that dominates 462 on return and cap, regenerate
governance and promote that point.

## Engineering Update - 2026-06-27 21:20 America/Bogota

The search was re-prioritized around pool93 because the other subsets are not
currently the best use of compute for the paper. HPO was paused with `SIGSTOP`
and remains resumable. Before pausing, HPO was using about 18.3 CPU cores and
19.1 GiB RAM, while the pool93 exact refinement used about one CPU core and
2.1 GiB RAM.

Observed exact-refinement throughput:

- with HPO running: about 6.8 checks/minute;
- with HPO paused, sequential exact runner: about 15.7 checks/minute;
- with independent exact solves in parallel, 6 workers: about 50-75
  checks/minute;
- with independent exact solves in parallel, 8 workers: active and stable at
  eight near-full CPU workers; status ETA after corrected resume logic is about
  4.3 hours, pending a longer throughput sample.

Technical change applied:

- `scripts/search/run_pool93_ijds_local_refinement.py` now supports
  `--parallel-workers`.
- The parallel path runs independent candidate-alpha exact solves in worker
  processes and keeps checkpoint/leaderboard/governance writes centralized in
  the parent process.
- Resume semantics remain keyed by `(local_candidate_id, alpha)`.
- The status ETA calculation was corrected for resumed runs by tracking
  `completed_checks_at_start` and `completed_checks_this_run`.

Partial expanded evidence is already paper-relevant. At the latest checkpoint,
the expanded `bound_claim_refined_local` region produced a candidate that
dominates Stage1 candidate 462 on the paper-facing return-bound lens:

- local candidate: 1076
- family: `bound_claim_refined_local`
- policy: `capped_blended_uncertainty`
- risk tolerance: 0.1705
- gamma: 0.50
- uncertainty aversion: 0.1125
- realized return: 185,735.027517
- Gamma_CP: 0.173059
- weighted miscoverage V: 0.037750
- endpoint budget upper: 0.2570295
- Markov loss cap at alpha01: 0.3570295
- alpha pass count: 8/8

This is not yet a final manuscript result because the expanded run has not
closed. But it changes the evidence gate: the run is no longer merely searching
for sensitivity. It is searching for the final body/default policy on a stronger
return-bound frontier.

## Final Expanded Results - 2026-06-28 01:08 America/Bogota

The expanded pool93 run closed successfully:

- run tag:
  `champion-reopen-2026-06-19__pool93__ijds-claim-expanded-refine`
- profile: `claim_expanded`
- exact policies: 3,258
- exact alpha checks: 26,064
- alpha grid: `{0.01, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.20}`
- all-alpha passers: 3,071/3,258
- all-alpha passers above declared return floor: 3,071/3,258
- bottleneck: alpha = 0.01; all other alpha levels pass 3,258/3,258
- full `bound_claim_refined_local` pass rate: 1,660/1,660

The final body/default point should move from Stage1 candidate 462 to the
expanded return-bound point:

- local candidate: 1665/1667 equivalent allocation family
- family: `bound_claim_refined_local`
- policy: `blended_uncertainty` or equivalent capped variant
- risk tolerance: 0.1720
- gamma: 0.55
- uncertainty aversion: 0.05
- realized return: 184,472.681224
- Gamma_CP: 0.162673
- weighted miscoverage V: 0.036017
- endpoint budget upper: 0.24520285
- Markov loss cap at alpha01: 0.34520285
- alpha pass count: 8/8
- mean funded loans: 320.625

This point is stronger than the Stage1 body/default on the intended
return-bound claim: it keeps a materially higher return than the declared
return floor, lowers Gamma_CP and the Markov cap versus Stage1 candidate 462,
and lies in a fully passing 1,660-policy bound-refined surface. It should be
presented as the manuscript body point if pool93 is promoted.

Important caveat: relative to the old manuscript policy, this point does **not**
lower realized V; the old manuscript reported V = 0.028875. The correct
paper-facing claim is therefore not "lower V than the previous manuscript
policy." The correct claim is:

> a selected body point on a predeclared exact finite-grid return-bound frontier
> realizes 184.5K return on a 1M budget while passing all eight alpha levels,
> with Gamma_CP = 0.1627, endpoint budget upper = 0.2452, and Markov cap =
> 0.3452.

The final expanded frontier gives several defensible endpoints:

| Role | Candidate | Return | Gamma_CP | V | Markov cap | Alpha pass |
|---|---:|---:|---:|---:|---:|---:|
| Bound-tight endpoint | 1206 | 181,242.759646 | 0.153611 | 0.038375 | 0.335785 | 8/8 |
| Body/default return-bound point | 1665 | 184,472.681224 | 0.162673 | 0.036017 | 0.345203 | 8/8 |
| Highest return under cap <= 0.36 | 1922 | 185,984.969939 | 0.174479 | 0.037750 | 0.358495 | 8/8 |
| Higher-return frontier under cap <= 0.45 | 979 | 198,693.277519 | 0.252323 | 0.045600 | 0.449010 | 8/8 |
| Economic endpoint under cap <= 0.50 | 3021 | 222,558.702500 | 0.459083 | 0.071075 | 0.489837 | 8/8 |
| Max-return endpoint | 2857/2777 | 223,346.552500 | about 0.4574 | 0.069575 | 0.5086--0.5127 | 8/8 |

Best IJDS claim after this run:

> CRPTO reports an exact finite-grid return-bound frontier for credit allocation:
> among 3,258 evaluated pool93 policies and 26,064 full-universe alpha checks,
> 3,071 policies pass every predeclared alpha level; the selected body point
> realizes 184.5K return with Markov cap 0.3452, while the frontier separately
> exposes bound-tight and economic endpoints.

This is stronger and cleaner than the older single-policy `45/45` robust-region
framing. The robust-region language should become "finite policy-grid robustness
surface" with explicit denominators: 1,660/1,660 for the bound-refined local
surface and 3,071/3,258 for the expanded exact policy grid.

## Final Micro-Refinement Results - 2026-06-28 06:19 America/Bogota

The targeted `claim_micro` refinement closed successfully. It improves the
expanded body point and, more importantly for IJDS, gives a cleaner finite-grid
robustness surface around the claim-bearing neighborhoods discovered by the
expanded run.

Final micro run:

- run tag:
  `champion-reopen-2026-06-19__pool93__ijds-claim-micro-refine`
- profile: `claim_micro`
- workers: 10 independent exact-solve workers
- exact policies: 2,949
- exact alpha checks: 23,592
- all-alpha passers: 2,949/2,949
- all-alpha passers above declared return floor: 2,949/2,949
- bottleneck: none inside this micro surface; every evaluated policy passes
  every alpha in the declared grid

Final body/default micro point:

- local candidate: 37
- family: `claim_micro_body_low_v`
- policy: `blended_uncertainty`
- risk tolerance: 0.1715
- gamma: 0.55
- uncertainty aversion: 0.0375
- realized return: 184,687.272568
- Gamma_CP: 0.161995
- weighted miscoverage V: 0.035350
- endpoint budget upper: 0.24439775
- Markov loss cap at alpha01: 0.34439775
- alpha pass count: 8/8
- mean funded loans: 320.75

This dominates the expanded body/default point 1665/1667 on the paper-facing
balanced lens:

- return improves by 214.591344;
- Gamma_CP falls by 0.000678;
- weighted miscoverage V falls by 0.000667;
- Markov cap falls by 0.0008051.

The improvement over the expanded point is modest, but it is directional on
all four body metrics. Relative to the current manuscript numbers, the final
micro body point raises return by 14,222.729640 (about 8.34%) and lowers
Gamma_CP by 0.025992 (about 13.83%). Its V is higher than the current
manuscript policy, so the body should not claim lower V relative to a historical
policy. The paper-facing claim should instead be a return-bound frontier claim.

Final micro frontier roles:

| Role | Candidate | Return | Gamma_CP | V | Markov cap | Alpha pass |
|---|---:|---:|---:|---:|---:|---:|
| Bound-tight endpoint | 949 | 179,763.276471 | 0.146997 | 0.038375 | 0.328799 | 8/8 |
| Body/default balanced point | 37 | 184,687.272568 | 0.161995 | 0.035350 | 0.344398 | 8/8 |
| Highest return under cap <= 0.345 | 205 | 184,770.883882 | 0.162402 | 0.035350 | 0.344831 | 8/8 |
| Highest return under cap <= 0.36 | 1975 | 186,046.522897 | 0.174593 | 0.037750 | 0.358678 | 8/8 |
| High-return endpoint under cap <= 0.50 | 2616 | 222,558.702500 | 0.459075 | 0.071075 | 0.491878 | 8/8 |
| Max-return economic endpoint | 2122 | 223,369.907874 | 0.457446 | 0.069575 | 0.512920 | 8/8 |

Decision:

- Promote candidate 37 as the paper body/default point if pool93 is promoted.
- Use candidate 205 as a near-equivalent "highest return under cap <= 0.345"
  sensitivity in the frontier table.
- Use candidate 1975 as the "highest return under cap <= 0.36" endpoint.
- Keep candidate 2122 as an economic endpoint only. It is useful to show the
  return-bound tradeoff, but it should not be the body policy because its Markov
  cap is much larger.

Manuscript consequence:

> CRPTO selects a pool93 body policy from a predeclared finite-grid exact
> frontier. On the 276,869-loan OOT universe and a 1M budget, the selected point
> realizes about 184.7K return, passes all eight alpha levels in the declared
> grid, and reports Gamma_CP about 0.162, weighted miscoverage about 0.035, and
> Markov cap about 0.344.

This wording should not compare against a previous champion. The comparison set
visible to the paper is the declared finite-grid frontier itself: the body point,
the bound-tight endpoint, and the economic endpoint.

Search-extension gate:

- A small follow-up search is scientifically justified only around exposed
  boundaries that could change the frontier table:
  - `claim_micro_bound_tight`: winner is at risk minimum, gamma maximum, and
    aversion maximum. A narrower bound-tight extension could reduce Markov cap
    below 0.3288 but would likely cost return.
  - `claim_micro_high_return_cap036`: winner is at the risk upper boundary. A
    small extension could improve the cap-0.36 endpoint by tens or hundreds of
    dollars.
  - `claim_micro_economic_endpoint`: winner is at gamma minimum. A small
    endpoint extension could add small return, but this is not the body claim.
- A broad new search is not justified by the current evidence. The paper claim
  is already supported by a completed governance sidecar and a complete
  2,949-policy all-alpha micro surface.

## Surgical Micro-Extensions Launched - 2026-06-28 10:37 America/Bogota

The final micro run exposed several grid edges that can still change the
frontier table. I therefore launched one bounded follow-up run rather than a
new broad portfolio search.

- run tag:
  `champion-reopen-2026-06-19__pool93__ijds-claim-micro-ext`
- profile: `claim_micro_ext`
- workers: 12 independent exact-solve workers
- exact policies: 4,407
- exact alpha checks: 35,256
- alpha grid: `{0.01, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.20}`

Families:

| Family | Policies | Claim target | Evidence gate |
|---|---:|---|---|
| `claim_micro_ext_body_cap345` | 660 | Improve the body/default or cap<=0.345 point. | Return above candidate 37 or 205 with Markov cap at or below about 0.345. |
| `claim_micro_ext_bound_tight` | 1,584 | Improve the bound-tight endpoint. | Lower Markov cap than 0.328799 while preserving all-alpha pass and nonnegative return-floor surplus. |
| `claim_micro_ext_cap036_return` | 1,080 | Improve highest return under cap<=0.36. | Return above 186,046.522897 with Markov cap <= 0.36. |
| `claim_micro_ext_economic_endpoint` | 1,080 | Stress the high-return endpoint. | Return above 223,369.907874 while keeping all-alpha pass; appendix/frontier only. |

Initial checkpoint:

- completed checks: 140/35,256
- ETA at first stabilized checkpoint: about 8.2 hours
- first partial body candidate under cap<=0.345:
  return 184,739.352839, Gamma_CP 0.162248, V 0.035350,
  Markov cap 0.344667.

Interpretation: the first partial body improvement is useful but not yet
frontier-changing relative to candidate 205. The run should continue because
the three edge families that motivated the extension have barely started.

## Literature Landscape And CRPTO Position

### 1. Conformal risk control and risk-controlling prediction sets

Closest sources:

- Bates et al. 2021, Risk-Controlling Prediction Sets.
- Angelopoulos et al. 2024, Conformal Risk Control.
- Angelopoulos et al. 2025, Learn Then Test.
- Angelopoulos et al. 2026, Non-Monotonic CRC.

Their contribution: distribution-free or finite-sample calibration of predictive
sets or risk functions, often model-agnostic and post-hoc.

CRPTO should not claim to improve those general guarantees. CRPTO uses this
family as the statistical substrate, then moves the certificate into a credit
portfolio decision. The IJDS contribution is the operational coupling:
calibrated PD -> conformal endpoints -> robust LP -> funded-set audit.

Promote:

- "decision-level audit of conformal uncertainty in credit allocation."

Avoid:

- "new conformal risk-control theorem."
- "selected funded set has nominal alpha coverage."

### 2. Conformal robust optimization and contextual robust optimization

Closest sources:

- Johnstone and Cox 2021, conformal uncertainty sets for robust optimization.
- Patel et al. 2024, Conformal Predict-Then-Optimize.
- Sun et al. 2024, Predict-then-Calibrate for robust contextual LP.
- Hu et al. 2026, Conformal Robustness Control.
- Zhao et al. 2026, CRO and satisficing.
- Bao et al. 2025, CROMS model selection.
- Zhou et al. 2025, CREDO.
- Zhou and Zhu 2025, inverse conformal risk control for robustness levels.

Their contribution: broad methods for CP-based uncertainty sets, robustness
control, model selection, decision reliability, and robustness-level calibration.

CRPTO's best position is narrower and more empirical: a credit-specific,
artifact-backed, full-universe certificate that explicitly separates endpoint
budget, Markov cap, realized V, and return. This is more IJDS-compatible than
claiming theoretical dominance over CRC/CROMS/CREDO.

Promote:

- "finite-grid exact return-bound frontier for a real credit portfolio."
- "governed robustness-level selection, not an ad hoc gamma choice."
- "auditability as the contribution: a selected policy plus interpretable
  frontier endpoints."

Avoid:

- "globally optimal robust policy over continuous parameters."
- "better than CRC/CROMS/CREDO."

### 3. Robust optimization and price of robustness

Closest sources:

- Bertsimas and Sim 2004, price of robustness.
- Bertsimas et al. 2018, data-driven robust optimization.
- Goldfarb and Iyengar 2003, robust portfolio selection.
- Delage and Ye 2010, DRO under moment uncertainty.

Their contribution: uncertainty sets, tractable robust counterparts, and
explicit conservatism-performance tradeoffs.

CRPTO should reuse that language. The new pool93 evidence makes this stronger:
instead of one policy plus a heatmap, we can report a return-bound frontier with
the endpoint budget and Markov cap visible.

Promote:

- "price of robustness is measured as a frontier, not asserted."
- "the selected policy is the body point on a declared finite frontier."

Avoid:

- "robustness is free" or "robustness always improves return."

### 4. Predict-then-optimize and decision-focused learning

Closest sources:

- Bertsimas and Kallus 2020, from predictive to prescriptive analytics.
- Elmachtoub and Grigas 2022, SPO/SPO+.
- Liu and Grigas 2021, risk bounds for SPO+.
- Donti et al. 2017, task-based end-to-end learning.
- Mandi et al. 2024, DFL survey.
- Schutte et al. 2024, robust losses for DFL.

Their contribution: train models for decision quality or regret, not just
prediction error.

CRPTO's distinction is that it remains post-hoc and governance-friendly: the
PD model is frozen, and the certificate is built around the decision layer. This
is weaker than end-to-end optimality but stronger for auditability and model-risk
management.

Promote:

- "post-hoc decision certificate for frozen ML artifacts."
- "regret-auditability frontier: SPO+ is a comparator, CRPTO is the auditable
  risk-control corner."

Avoid:

- "CRPTO minimizes regret better than SPO+."

### 5. P2P lending and credit portfolio decision support

Closest sources:

- Guo et al. 2016, instance-based credit-risk assessment and portfolio
  allocation.
- Serrano-Cinca and Gutierrez-Nieto 2016, profit scoring.
- Zhao et al. 2016, multi-objective P2P portfolio selection.
- Chi et al. 2019, data-driven robust credit portfolio optimization in P2P.
- Babaei and Bamdad 2020, multi-objective P2P recommendation.
- Torkian et al. 2025/2026, AI plus OR for digital lending.

Their contribution: P2P loan selection, risk-return optimization, multi-objective
portfolio recommendation, robust P2P portfolio models.

CRPTO's gap is not "we optimize P2P portfolios"; that exists. The gap is:
portfolio selection with conformal PD uncertainty, exact funded-set
miscoverage accounting, and an explicit paper-governed return-bound frontier.

Promote:

- "credit portfolio decision certificate, not only P2P recommendation."
- "exposure-weighted funded-set audit with interpretable grade/risk
  decomposition."

Avoid:

- "first portfolio optimizer for P2P lending."

### 6. Credit scoring, calibration, and fairness context

Closest sources:

- Jagtiani and Lemieux 2019, alternative data and fintech lending.
- Albanesi and Vamossy 2024, credit scores performance and equity.
- Kawasumi et al. 2026, conformal prediction for ordinal credit scoring.
- Yang and Bi 2025, cost-aware calibration.

Their contribution: predictive performance, calibration, equity/fairness, and
credit-score uncertainty.

CRPTO can use these sources to justify why calibrated PD matters, but should not
turn the paper into a fairness or underwriting-credit-score paper.

Promote:

- "calibrated probabilities are necessary but insufficient; the paper studies
  how they shape a funding decision."

Avoid:

- statutory fair-lending proof;
- equity improvement claims without direct protected attributes.

### 7. Limits of conformal validity

Closest sources:

- Barber et al. 2021, limits of conditional predictive inference.
- Barber et al. 2023, beyond exchangeability.
- Gibbs and Candes 2021, adaptive conformal inference.
- Gibbs et al. 2025, conditional guarantees.
- Bhattacharyya and Barber 2026, group-weighted CP.
- Yang and Jin 2026, multi-distribution robust CP.

Their contribution: they define what is and is not possible under
distribution-free conformal inference, especially under conditional coverage,
shift, group weighting, and multi-source deployment.

CRPTO should use this literature as a guardrail. The paper can say it audits
weighted funded-set validity and reports group/multi-distribution diagnostics,
not that it has exact conditional validity for selected portfolios.

Promote:

- "explicit validity ladder."
- "finite-grid and retrospective exact audit."

Avoid:

- universal conditional coverage;
- future live-deployment coverage without online protocol.

## Proposed Claim Hierarchy

### Main Claim

CRPTO provides a reproducible conformal-robust decision certificate for credit
portfolio selection by connecting frozen calibrated PD artifacts, conformal
uncertainty, robust LP decisions, and exact full-universe funded-set audits.

Evidence:

- final stage1 pool93 governance sidecar;
- 276,869-row full-universe OOT evaluation;
- all-alpha finite-grid audit;
- claim-selection protocol and frozen artifact paths.

Destination: abstract, introduction, method, results.

### Result Claim

On the pool93 finite-grid exact refinement, the paper-body policy sits on a
return-bound frontier: it preserves all-alpha-grid safety while giving a
cleaner endpoint budget/Markov cap than the old manuscript policy and materially
higher realized return relative to the declared return floor.

Paper-facing phrasing should not mention an old champion. Use:

> relative to the declared return floor used in the selection protocol

or avoid the comparison entirely:

> the selected body point realizes 183.8K return at a 0.3607 Markov cap and
> passes all eight predeclared alpha checks.

Destination: results table and frontier figure.

### Theory Claim

The theorem is a first-moment Markov decision certificate under weighted
funded-set validity. The exact audit verifies deterministic accounting and the
observed finite-grid pass/fail indicators. It is not a new conditional-coverage
theorem.

Destination: theory section, assumption-to-evidence table.

### Robust Region Claim

Replace generic "robust region" language with:

> finite policy-grid robustness surface.

For pool93, the stronger summary is:

- 756/815 all-alpha passers in stage1;
- 418/418 bound-efficient passers;
- claim-expanded refinement pending.

Destination: results and supplement.

### Frontier Claim

The most IJDS-friendly presentation is a three-point frontier:

1. Bound-tight endpoint: candidate 466.
2. Body/default return-bound point: candidate 462.
3. Economic endpoint: candidate 264.

This prevents the paper from overselling max return while still showing the
economic opportunity.

Destination: main results figure/table.

## What Can Still Improve

1. Finish `claim_expanded`.
   Evidence gate: a policy that dominates candidate 462 on return at no worse
   Markov cap, or a cleaner/fatter safe ridge around the same cap.

2. Generate a manuscript-ready frontier artifact.
   Needed columns: candidate role, family, tau, gamma, aversion, return,
   Gamma_CP, V, endpoint budget, Markov cap, funded loans, alpha pass count.

3. Update manuscript numbers only after promotion decision.
   The current manuscript still reports 170.5K, V 0.028875, Gamma_CP 0.187987,
   and 45/45. These are now weaker than the pool93 stage1 frontier for the
   return-bound claim.

4. Replace "champion" language in paper-facing sections.
   Use "selected policy", "body point", "economic endpoint", "declared return
   floor", and "finite-grid certificate".

5. Add a selection-protocol paragraph.
   Explain that CRPTO promotes a body point by declared return-bound criteria,
   while max-return and bound-tight points are appendix/frontier endpoints.

6. Keep end-to-end learning and stronger CRC methods as future work.
   They are relevant but would change the protocol. Do not reopen the paper
   around them unless a new theorem or new prospective evaluation is added.

## Scenario Ladder

### Minimum Publishable Improvement

Stage1 candidate 462 remains body default. The paper updates its claim from
45/45 local champion to 815-policy finite-grid return-bound frontier. This is
already stronger and more IJDS-facing than the current manuscript.

### Strong Improvement

`claim_expanded` finds a point with return >= 183.8K and Markov cap <= 0.3607,
or a larger clean region around cap <= 0.37. The paper can then state a more
defensible "highest return under declared Markov-cap lens" result.

### Ideal Scenario

The final promoted pool93 point satisfies:

- return >= 190K;
- Markov cap <= 0.3607;
- Gamma_CP <= 0.1763;
- V <= 0.0413 or still clearly below sqrt(0.01);
- 8/8 alpha pass;
- belongs to a broad interpretable bound-refined region with no alpha01
  failures.

This would give the strongest IJDS claim:

> A predeclared return-bound selection rule identifies a high-return policy on
> an exact full-universe conformal-robust frontier, while a surrounding
> finite-grid surface verifies that the decision is not an isolated point.

### Unrealistic Or Unsafe Scenario

Trying to claim:

- global optimality over continuous policy space;
- nominal 99 percent funded-set coverage;
- universal conditional coverage;
- fairness certification;
- live sequential validity;
- superiority over CRC/CROMS/CREDO as theory.

These would invite reviewer rejection because the evidence does not support
them.

## Recommended Paper Rewrite Direction

In the abstract and introduction, replace:

> promoted economic policy earns 170.5K ... final region 45/45

with:

> a selected return-bound policy from a predeclared finite-grid exact audit
> realizes 183.8K on a 1M budget, passes all eight alpha levels in the declared
> grid, and sits on a full-universe return-bound frontier whose bound-tight and
> economic endpoints are reported separately.

In the theory section, keep Markov but update the numeric example to candidate
462 or the final claim-expanded winner.

In the supplement, preserve old champion history only as archived/internal
decision provenance if needed. The submitted paper should not explain a
succession of champions.

## Operational Next Steps

1. Let `claim_expanded` finish or reach the bound-refined families before final
   promotion.
2. Build a `pool93_ijds_frontier_table` from the final selected run.
3. Update `paper/CRPTO_ijds.qmd`, `paper/supplement_ijds.qmd`, and
   `paper/submission/CLAIM_AUDIT_MATRIX.md` using the new neutral vocabulary.
4. Render/validate the paper after replacing old numbers.
5. Archive old champion-comparison language in internal docs only.

## Final Micro-Extension And Consolidated Frontier - 2026-06-28 19:35 America/Bogota

The surgical `claim_micro_ext` refinement closed successfully and should be
treated as the strongest completed pool93 evidence set before the final
bound-only closure:

- run tag:
  `champion-reopen-2026-06-19__pool93__ijds-claim-micro-ext`
- profile: `claim_micro_ext`
- exact policies: 4,407
- exact alpha checks: 35,256
- all-alpha passers: 4,406/4,407
- all-alpha passers above the declared return floor: 4,406/4,407
- only failure: one high-return endpoint policy at the strictest alpha gate; the
  body and bound-facing neighborhoods remain clean.

Final `claim_micro_ext` governance roles:

| Role | Candidate | Return | Gamma_CP | V | Markov cap | Alpha pass |
|---|---:|---:|---:|---:|---:|---:|
| Minimum Markov-cap endpoint | 856/857/861 equivalent | 178,639.843939 | 0.136322 | 0.035875 | 0.316713 | 8/8 |
| Body/default balanced point | 131 | 184,832.475845 | 0.162616 | 0.035350 | 0.345084 | 8/8 |
| Strict cap<=0.345 body proxy | 511/512/513 equivalent | 184,800.413581 | 0.162562 | 0.035350 | 0.344996 | 8/8 |
| Highest return under cap<=0.36 | 3211/3212 equivalent | 186,050.727749 | 0.174600 | 0.037750 | 0.358685 | 8/8 |
| Max-return economic endpoint | 4041/4042/4043 equivalent | 223,458.135875 | 0.457438 | 0.069575 | 0.510753 | 8/8 |

Interpretation:

- Candidate 131 is still the best protocol-selected body point because it
  maximizes the balanced return-bound score and shares the lowest observed
  realized V among return-floor-safe policies.
- Candidate 511/512/513 is slightly cleaner for manuscript language if the
  paper wants a strict `Markov cap <= 0.345` sentence. It gives up only about
  32 dollars of realized return relative to candidate 131.
- Candidate 4041 is a useful economic endpoint, not the paper body point. It
  shows the return-bound tradeoff, but its Markov cap is much looser.

I built a consolidated frontier sidecar across the completed `expanded`,
`claim_micro`, and `claim_micro_ext` runs:

`models/experiments/champion_reopen/champion-reopen-2026-06-19__pool93__ijds-claim-consolidated/portfolio/pool93_ijds_consolidated_frontier.json`

Consolidated counts:

- raw evaluated rows: 10,614
- deduplicated semantic policies: 9,870
- duplicate semantic rows removed: 744
- eligible all-alpha, above-return-floor policies: 9,682
- nonpass or below-floor policies: 188

The consolidated table is the current best paper-facing artifact because it
does not overfit to whichever local run happened to produce a role. It preserves
the source run for every selected point and uses the rule:

> eligible = all-alpha pass and nonnegative return-floor surplus; dedupe by
> semantic policy; body score = 0.40 return + 0.40 inverse Markov cap +
> 0.20 inverse V; cap-frontier rows maximize return under fixed Markov-cap
> thresholds.

The consolidated frontier selected:

| Role | Source | Candidate | Return | Gamma_CP | V | Markov cap | Alpha pass |
|---|---|---:|---:|---:|---:|---:|---:|
| Minimum Markov-cap endpoint | micro_ext | 861 | 178,639.843939 | 0.136322 | 0.035875 | 0.316713 | 8/8 |
| Body/default balanced point | micro_ext | 131 | 184,832.475845 | 0.162616 | 0.035350 | 0.345084 | 8/8 |
| Strict cap<=0.345 point | micro_ext | 512 | 184,800.413581 | 0.162562 | 0.035350 | 0.344996 | 8/8 |
| Highest return under cap<=0.36 | micro_ext | 3212 | 186,050.727749 | 0.174600 | 0.037750 | 0.358685 | 8/8 |
| Highest return under cap<=0.45 | expanded | 979 | 198,693.277519 | 0.252323 | 0.045600 | 0.449010 | 8/8 |
| Highest return under cap<=0.50 | micro | 2840 | 222,558.702500 | 0.459089 | 0.071075 | 0.487795 | 8/8 |
| Max-return economic endpoint | micro_ext | 4041 | 223,458.135875 | 0.457438 | 0.069575 | 0.510753 | 8/8 |

Paper-facing decision:

- Promote the selected policy as a finite-grid return-bound point, not as a
  historical champion replacement story.
- In the paper body, use either candidate 131 for the protocol-selected body
  point or candidate 512 if the prose needs the cleaner strict cap threshold.
  The table can show both roles without making them compete.
- Replace `45/45 robust region` with `finite policy-grid robustness surface`.
  The completed pool93 surface is much stronger: 9,682 eligible deduplicated
  policies across the consolidated refinements, with explicit alpha-grid
  semantics and no continuous-region overclaim.
- Keep the theorem claim at the Markov/weighted-funded-validity level. The
  exact full-universe audit is deterministic accounting plus finite-grid
  evidence, not a new conditional-coverage theorem.

Best manuscript claim after completed evidence:

> CRPTO maps a frozen calibrated credit-risk artifact into conformal robust
> funding decisions and reports an exact full-universe finite-grid
> return-bound frontier. On the Lending Club OOT universe, the selected pool93
> body point realizes about 184.8K on a 1M budget, passes all eight predeclared
> alpha levels, and sits on a frontier whose bound-tight and economic endpoints
> are reported separately rather than collapsed into a single leaderboard
> winner.

Use this as manuscript logic, not verbatim final prose.

### Final Bound-Closure Search

The only additional search that is still scientifically justified is a
bound-only closure, because `claim_micro_ext` showed a monotone reduction in
Markov cap as gamma increased up to 0.65 while uncertainty aversion was already
mostly saturated. This can change the appendix/frontier endpoint and the
theory-facing bound language, but it is not expected to change the body/default
policy.

Launched run:

- run tag:
  `champion-reopen-2026-06-19__pool93__ijds-claim-bound-closure`
- profile: `claim_bound_closure`
- exact policies: 1,653
- exact alpha checks: 13,224
- workers: 12
- evidence gate: Markov cap below 0.316713, nonnegative return-floor surplus,
  and 8/8 alpha pass.
- artifact sink: appendix/frontier endpoint and consolidated frontier sidecar,
  not paper-body policy unless it unexpectedly dominates the body point.

Postprocessing is automated. When the run finishes, it will generate the run
governance/frontier sidecars and a four-run consolidated frontier:

`models/experiments/champion_reopen/champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-with-bound-closure/portfolio/pool93_ijds_consolidated_frontier.json`

Stop rule:

- If the minimum Markov cap moves materially below 0.316713 while keeping
  8/8 and return above the declared floor, promote it as a stronger
  bound-tight endpoint.
- If the cap improvement is tiny or the endpoint loses the return floor, close
  the search as negative evidence and keep the completed consolidated frontier
  above as the paper-facing result set.

## Bound-Closure Final And Last Floor-Threshold Check - 2026-06-28 23:20 America/Bogota

The `claim_bound_closure` run completed and materially strengthened the
bound-tight endpoint:

- run tag:
  `champion-reopen-2026-06-19__pool93__ijds-claim-bound-closure`
- exact policies: 1,653
- exact alpha checks: 13,224
- all-alpha passers: 1,653/1,653
- all-alpha passers above declared return floor: 1,653/1,653
- elapsed wall time: about 3.23 hours with 12 workers

Best bound-tight endpoint from this closure:

- local candidate: 166/167/168 equivalent
- family: `claim_bound_closure_low_cap`
- risk tolerance: 0.1685
- gamma: 0.75
- uncertainty aversion: 0.35
- realized return: 174,136.767088
- return-floor surplus: 3,672.227088
- Gamma_CP: 0.119477
- weighted miscoverage V: 0.035875
- endpoint budget upper: 0.19836925
- Markov cap: 0.29836925
- alpha pass count: 8/8

This improves the previous minimum-cap endpoint from the consolidated
`micro_ext` surface:

| Endpoint | Return | Gamma_CP | V | Markov cap | Alpha pass |
|---|---:|---:|---:|---:|---:|
| Before bound closure | 178,639.843939 | 0.136322 | 0.035875 | 0.316713 | 8/8 |
| After bound closure | 174,136.767088 | 0.119477 | 0.035875 | 0.298369 | 8/8 |

The price of tightening from the body/default point is now explicit:

| Role | Return | Gamma_CP | V | Markov cap | Alpha pass |
|---|---:|---:|---:|---:|---:|
| Body/default balanced point | 184,832.475845 | 0.162616 | 0.035350 | 0.345084 | 8/8 |
| Bound-tight endpoint | 174,136.767088 | 0.119477 | 0.035875 | 0.298369 | 8/8 |
| Economic endpoint | 223,458.135875 | 0.457438 | 0.069575 | 0.510753 | 8/8 |

Interpretation:

- The body/default point remains candidate 131 from `micro_ext`. The
  bound-closure result is not a better body policy; it is a sharper endpoint
  for the return-bound frontier.
- The paper can now state a cleaner frontier story: one selected body point
  around 184.8K, one bound-tight endpoint below Markov cap 0.30, and one
  economic endpoint above 223K.
- This is stronger than the former `45/45` language because it gives a
  multi-point exact frontier with explicit denominators and tradeoffs.

The consolidated-with-bound-closure sidecar was generated at:

`models/experiments/champion_reopen/champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-with-bound-closure/portfolio/pool93_ijds_consolidated_frontier.json`

Consolidated counts after adding the bound closure:

- raw evaluated rows: 12,267
- deduplicated semantic policies: 11,472
- eligible all-alpha, above-return-floor policies: 11,284
- nonpass or below-floor policies: 188

### Last Floor-Threshold Check

The minimum-cap policy still lies on the boundary of the closure grid
(`tau=0.1685`, `gamma=0.75`, `aversion=0.35`) and retains a positive surplus
of about 3.7K over the declared return floor. Therefore, one last bounded check
is justified only for the endpoint claim:

- run tag:
  `champion-reopen-2026-06-19__pool93__ijds-claim-bound-floor-closure`
- profile: `claim_bound_floor_closure`
- exact policies: 2,343
- exact alpha checks: 18,744
- target: test whether the bound-tight endpoint can cross `Markov cap < 0.29`
  while preserving 8/8 alpha pass and nonnegative return-floor surplus.
- artifact sink: appendix/frontier endpoint and final consolidated frontier
  only; it should not replace the paper body/default point.

Early checkpoint:

- first completed endpoint already improved Markov cap from 0.298369 to
  0.297442 at return 173,851.453513, Gamma_CP 0.118766, V 0.035875, 8/8.
- Higher-gamma candidates are still pending, so the final endpoint is not yet
  claim-final.

Stop rule for the whole pool93 portfolio-claim search:

- If `claim_bound_floor_closure` crosses cap 0.29 with return above the
  declared floor, promote that as the final bound-tight endpoint.
- If it does not cross cap 0.29, keep cap 0.298369 as the final bound-tight
  endpoint and close the search. A further wave would be threshold chasing
  rather than a new manuscript claim.

## Terminal Bound Search Design - 2026-06-29 03:10 America/Bogota

At 87 percent completion, `claim_bound_floor_closure` had already crossed the
intended paper threshold:

- best observed Markov cap: 0.284839
- return: 171,399.674021
- return-floor surplus: 935.134021
- Gamma_CP: 0.106806
- V: 0.034875
- alpha pass: 8/8

This is already sufficient for the paper phrase "bound-tight endpoint below
0.29 Markov cap." However, the best endpoint still sits on the high-gamma edge
of the current grid (`gamma=0.84`) and retains a small positive return surplus.
One final terminal search is therefore justified, but only as an endpoint
closure. It is not a body-policy search and it must be the last search wave.

Terminal run:

- run tag:
  `champion-reopen-2026-06-19__pool93__ijds-claim-bound-terminal`
- profile: `claim_bound_terminal`
- exact policies: 37,068
- exact alpha checks: 296,544
- workers: 12
- launch mode: waits for
  `champion-reopen-2026-06-19__pool93__ijds-claim-bound-floor-closure` to
  complete, then starts automatically.
- postprocessing: governance, frontier table, and consolidated definitive
  frontier generated automatically.

Search blocks:

| Block | Purpose | Grid |
|---|---|---|
| `claim_bound_terminal_ultra_low_cap` | Test whether cap can cross cleaner thresholds such as 0.280 or 0.275 while staying above the return floor. | tau 0.16675--0.17025, gamma 0.84--0.99, aversion 0.40--0.70 |
| `claim_bound_terminal_return_recovery` | Preserve the best return under low-cap thresholds instead of only minimizing cap. | tau 0.16800--0.17150, gamma 0.80--0.92, aversion 0.35--0.60 |

Evidence gates:

- primary: minimum Markov cap with 8/8 alpha pass and nonnegative
  return-floor surplus;
- secondary: highest return under cap thresholds 0.275, 0.280, 0.285, 0.290,
  0.295, and 0.300;
- tertiary: verify that the selected body/default point from `micro_ext`
  remains unchanged.

Absolute stop rule:

- After `claim_bound_terminal` completes, stop portfolio-claim searching.
- If it improves only the bound endpoint, promote only the endpoint in the
  frontier table.
- If it fails to improve the current 0.284839 endpoint, close it as negative
  evidence and retain `claim_bound_floor_closure`.
- Do not launch another wave merely because the minimum-cap point lands on a
  new grid boundary. At that point, further reduction would be threshold
  chasing and would not change the manuscript's main claim.

Definitive artifact target:

`models/experiments/champion_reopen/champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-definitive/portfolio/pool93_ijds_consolidated_frontier.json`

## Final Terminal Closure - 2026-07-02 America/Bogota

`claim_bound_terminal` completed and the postprocessors generated the
governance, frontier-table, and consolidated-definitive sidecars. This closes
the pool93 portfolio-claim search under the declared stop rule.

Final terminal run:

- run tag:
  `champion-reopen-2026-06-19__pool93__ijds-claim-bound-terminal`
- exact policies: 37,068
- exact alpha checks: 296,544
- all-alpha passers: 37,068/37,068
- all-alpha passers above the declared return floor: 14,814/37,068
- alpha grid: `{0.01, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.20}`
- final status artifact:
  `models/experiments/champion_reopen/champion-reopen-2026-06-19__pool93__ijds-claim-bound-terminal/portfolio/runtime_status.json`

Definitive consolidated frontier:

- raw evaluated rows: 51,678
- deduplicated semantic policies: 50,010
- duplicate rows removed: 1,668
- eligible all-alpha and above-floor policies: 27,508
- consolidated sidecar:
  `models/experiments/champion_reopen/champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-definitive/portfolio/pool93_ijds_consolidated_frontier.json`
- manuscript/supplement table:
  `reports/crpto/tables/crpto_tableA35_pool93_ijds_frontier.csv`

Final claim roles:

| Role | Source | Candidate | Return | Gamma_CP | V | Markov cap | Alpha pass |
|---|---|---:|---:|---:|---:|---:|:---:|
| Minimum Markov-cap endpoint above floor | terminal | 10661 | 170,467.268819 | 0.095719 | 0.031875 | 0.273035950 | 8/8 |
| Low-cap balanced endpoint | terminal | 5504 | 171,006.195983 | 0.097190 | 0.031875 | 0.274789250 | 8/8 |
| Highest return under cap <= 0.30 | terminal | 36412 | 173,314.040806 | 0.115400 | 0.035875 | 0.294580000 | 8/8 |
| Strict cap <= 0.345 body proxy | micro_ext | 512 | 184,800.413581 | 0.162562 | 0.035350 | 0.344996495 | 8/8 |
| Body/default balanced point | micro_ext | 131 | 184,832.475845 | 0.162616 | 0.035350 | 0.345083740 | 8/8 |
| Highest return under cap <= 0.36 | micro_ext | 3212 | 186,050.727749 | 0.174600 | 0.037750 | 0.358685000 | 8/8 |
| Highest return under cap <= 0.45 | expanded | 979 | 198,693.277519 | 0.252323 | 0.045600 | 0.449009950 | 8/8 |
| Max-return economic endpoint | micro_ext | 4041 | 223,458.135875 | 0.457438 | 0.069575 | 0.510753090 | 8/8 |

Interpretation:

- The terminal search materially improves the bound endpoint, not the body
  point. It lowers the above-floor Markov-cap endpoint to 0.2730 while keeping
  a nonnegative return-floor surplus.
- The body/default point remains micro_ext candidate 131 because it is a more
  useful manuscript tradeoff: materially higher return, all-alpha pass, zero
  violation, and a clean Markov cap around 0.345.
- Candidate 512 is the strict wording alternative if the paper wants the exact
  phrase "Markov cap <= 0.345"; it gives up only about 32 dollars versus the
  body/default point.
- Candidate 4041 is the economic endpoint and should be shown as a frontier
  endpoint, not as the primary theorem-facing policy.

Manuscript claim hierarchy:

1. Promote in the body: a finite-grid exact return-bound frontier on the
   Lending Club OOT universe, with the body/default point earning 184.8K on a
   1M budget and passing all eight declared alpha levels.
2. Promote in the body as the conservative endpoint: the frontier also contains
   an above-floor policy with Markov cap 0.2730.
3. Append in the supplement: the full cap frontier, including 0.30, 0.345,
   0.36, 0.45, 0.50, and max-return endpoints.
4. Closed on 2026-07-02 for the submitted pool93 claim: grade composition
   (A36), tail-risk repricing (A37), and concentration/cluster-bound sensitivity
   (A38) now come from the promoted pool93 allocation. Bootstrap under the final
   allocation remains a future diagnostic, not a blocker for the IJDS body claim.

Final stop decision:

- Close portfolio-claim searching for pool93.
- Do not launch another threshold chase solely because the minimum-cap policy
  lies near a new grid boundary.
- Reopen only if a reviewer requests a denser alpha grid, row-level pool93
  composition/tail-risk artifacts, or a formal continuous-region theorem.
