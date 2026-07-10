# IJDS Three-Front Reconstruction Ledger - 2026-07-10

> **Reconstruction completed (2026-07-10):** the durable output of this ledger
> is the clean tagged maturity-safe bounded protocol v2 and the manuscript
> governed by `active_claims_2026-07-10.md`. Fronts A and B remain recovery
> sources; their numerical claims remain historical. References below to a
> dirty scratch challenger and a NO-GO current submission describe the state
> at the start of reconstruction, not the active end state.

## Status and purpose

This ledger freezes what is worth preserving before CRPTO performs any new
scientific run or rewrites the IJDS manuscript. It is the reconstruction
control document, not a new claim registry.

**Current submission status: NO-GO.** The compact v7 paper is computationally
reproducible, but its candidate universe, conformal fit/tune chronology,
economic objective, and pooled future menu do not match the decision it claims
to evaluate. The maturity-safe challenger repairs those four defects, but its
current output is a dirty scratch run and it does not preserve nominal
coverage after temporal transport and portfolio selection.

No protected DVC stage or manifest-listed artifact is authorized by this
ledger. Historical numbers remain provenance only unless a row below says
that they may be copied directly.

Machine-readable asset decisions live in
`docs/research/ijds_reconstruction_asset_inventory_2026-07-10.csv`.

## The three frozen fronts

| Front | Stable source | What it contains | Scientific status |
|---|---|---|---|
| A. Broad manuscript and hardening | `2a9b5e9` (broad closeout), `17811d8` / tag `ijds-refactor-checkpoint-2026-07-09` (hardened) | Full IJDS narrative, theory, external replication, robustness sections, 5 body figures, 11 body tables, 12 supplement figures, A3--A40 evidence map, code hardening | Rich source library, but its headline evidence is invalid for a new submission and must not be restored numerically |
| B. Compact v7 manuscript | `4134a6d` (simplification), `63f9a9b` / tag `checkpoint/ijds-v7-final-63f9a9b-2026-07-09`, merged at `0f613f9` | One linear policy, exact alpha replay, outcome-column isolation, matched comparator, concise 13-page body and 11-page supplement | Best editorial discipline and reusable software contracts; still NO-GO because the upstream design remains invalid |
| C. Maturity-safe challenger | working tree on `0f613f9`; config `champion_reopen_ijds_maturity_safe_coherent_payoff_v1.yaml`; scratch run tag `champion-reopen-2026-07-10__maturity-safe-coherent-payoff-v1` | Status-independent universe, explicit maturity contract, coherent standardized payoff, monthly decisions, outcome isolation, unresolved bounds | Correct direction, not promotable: dirty run, code changed after output, only seven OOT months, historical cap, severe drift, and funded-set coverage failure |

Additional recovery tags created for unambiguous access:

- `checkpoint/ijds-broad-submission-2a9b5e9-2026-07-09`
- `checkpoint/ijds-v7-final-63f9a9b-2026-07-09`

The old PDFs are also present in ignored MinerU scratch output, but Git source
and the tags above are the durable recovery mechanism. The 2026-07-07 snapshots
contain a 27-page Quarto body, 32-page supplement, and 26-page official TeX
submission. They can be rebuilt from the tagged sources; they are not evidence
to submit.

## What the page reduction actually removed

| Artifact | Front A (`17811d8`) | Front B (`63f9a9b`) | Change |
|---|---:|---:|---:|
| Official TeX pages | 28 at the hardening checkpoint; 26 at the immediately prior broad closeout | 13 | Roughly half the body |
| Official TeX lines / characters | 1,182 / 70,749 | 592 / 28,595 | -50% lines; -60% text |
| Body headings | 19 | 18 | Similar outline count, much less depth per section |
| Body tables | 11 | 7 | External, frontier, tail, and reviewer surfaces removed |
| Body figures | 4 at `17811d8` (5 at `2a9b5e9`) | 1 | Pipeline retained; theory/external/regret visuals removed |
| Unique body citations | 51 | 33 | Breadth reduced, while several newer close neighbors were added |
| Supplement lines / characters | 1,069 / 80,980 | 402 / 19,705 | -62% lines; -76% text |
| Supplement images | 12 | 0 | Visual diagnostics disappeared from the active package |

The reduction improved focus, removed multiple policy families from the
headline, and made statistical caveats visible. It also removed too much
scientific context, theory exposition, diagnostic evidence, and managerial
interpretation. The correct recovery target is neither old length nor current
length: it is a 16--19 page body with a substantive, evidence-bearing
supplement.

## Scientific validity across fronts

| Question | Front A | Front B | Front C | Reconstruction decision |
|---|---|---|---|---|
| Candidate membership known at origination | No: resolved-only filter | No: same 276,869 resolved-only rows | Yes: status-independent 36-month universe | Keep C contract and tests |
| Labels available before fitting each layer | No: fit/tune uses later 2017 outcomes | No: exact replay preserves that recipe | Yes for 2010/2011/2012 blocks and 2016 decisions | Keep C chronology; document all availability dates |
| Implementable decision menu | No: one 2018--2020 pooled menu | No: same future menu | Yes: fresh monthly budget | Keep monthly policy evaluation |
| Objective matches evaluated payoff | No: optimizes `r-pL` and evaluates `(1-Y)r-YL` | No | Yes: `(1-p)r-pL` versus `(1-Y)r-YL` | Keep C payoff module and independent reconciliation |
| Conformal object is named correctly | No: outcome prediction interval called a PD interval | No | Not yet: fields remain `pd_low`/`pd_high` | P0 rename/reframe or replace the uncertainty construction |
| Selected-set validity established | No | Explicitly disclaimed, but still used rhetorically | No: funded coverage is 0.6891 | Make failure a result; never call it a guarantee |
| Policy cap independent of reported test | No | No: 0.28 came from prior corpus development | No: inherited 0.28 | Treat as development-only, remove it, or justify it externally before a new test |
| Conformal group stored correctly | No: `conformal_group` copied from grade | No | Yes: score-quantile group is recomputed and asserted | Keep C group contract |
| Concentration named correctly | Ambiguous | Ambiguous | Config says `max_concentration_by_purpose` | Use "purpose concentration cap" everywhere |
| Temporal inference matches design | Weak fixed-allocation bootstrap | Better caveat, still 31 pooled months | Seven paired monthly observations only | Use paired monthly evidence; limit inferential claims |
| External evidence shares the final estimand | No audit of maturity/payoff equivalence | Removed from body | Not run | Re-audit or omit; never copy old external numbers |
| Clean-clone provenance | Partial | Stronger replay, incomplete upstream bundle | Scratch summary is dirty and stale relative to code | Require clean committed run plus separate execution receipt |

## Two additional P0 boundaries

### 1. The residual interval is not a confidence interval for PD

All three fronts build an absolute-residual interval around a calibrated
probability using binary outcomes:

`[L_i,U_i] = [max(0,p_i-q_g), min(1,p_i+q_g)]`.

This is a split-conformal prediction interval for the future binary outcome
`Y_i`, conditional on the stated exchangeability/Mondrian protocol. It is not a
confidence interval for the latent conditional probability of default. Calling
`U_i` an "upper PD endpoint" overstates what is covered.

For binary outcomes, empirical miscoverage has an exact and revealing form:

`1{Y not in [L,U]} = 1{Y=1,U<1} + 1{Y=0,L>0}`.

On the scratch 2016 OOT candidates, 98.7596% of lower endpoints are zero,
17.5644% of upper endpoints are one, and mean interval width is 0.5417. Thus
coverage is largely a question of which defaults receive a saturated upper
endpoint, not whether a numeric band contains a latent PD.

For the selected funded dollars, the 0.310896 miscoverage decomposes into
0.288628 exposure on defaults with `U<1` plus 0.022268 exposure on nondefaults
with `L>0`. This algebra belongs in the final supplement and should inform the
body language.

Before promotion, choose exactly one path:

1. Keep the current construction, rename it a binary-outcome conformal
   interval/upper prediction score, and make the paper an audit of that
   guardrail.
2. Replace it with a method whose estimand is genuinely decision risk or
   probability uncertainty, then run a separately tagged protocol.

The first path is simpler and currently more defensible. The second may yield a
stronger methodological claim but is new science and must not be smuggled in as
a refactor.

### 2. The endpoint screen is not an independent safety quantity

For the linear score `q=(1-gamma)p+gamma U`, if the weighted risk constraint
binds at `tau`, then

`gamma * B_U + (1-gamma) * P = tau`,

where `B_U` and `P` are the funded weighted upper endpoint and point score.
For the selected `gamma=0.5`, `tau=0.17` policy, this gives exactly
`B_U=0.34-P`. The OOT values `P=0.0811445` and `B_U=0.2588555` satisfy that
identity. Under a binding constraint, `B_U<=0.28` is equivalent to
`P>=0.06`; it is not an independent probabilistic certificate.

The final paper must either justify the screen as a declared preference,
report the full predeclared frontier without crowning a cap-selected winner, or
remove the screen. It must not describe 0.28 as a calibrated risk guarantee.

## Recovery classes

### KEEP_DIRECT

Use unchanged except for names/imports needed by the final package:

- strict ID alignment and one-to-one join guards;
- safe experiment-path containment and no-overwrite behavior;
- exact finite-sample rank implementation;
- outcome-free decision-frame checks;
- coherent expected/realized payoff formulas and reconciliation tests;
- status-independent membership and nullable outcome representation;
- monthly fresh-budget evaluation and unresolved-outcome bounds;
- `latexmk`/manual TeX compiler, publication-integrity checks, `uv`, Ruff,
  mypy, ty, pytest, just, and DVC protection gates;
- old Git history, tags, figures, tables, and memos as provenance.

### KEEP_REWRITE

Retain the idea and source material, but rewrite against the final estimand:

- Front A's data-science-for-decisions opening and managerial risk/payoff
  motivation;
- its four-family related-work organization and closest-work boundary;
- Front B's one-policy exposition, matched-comparator discipline, exact replay
  language, and explicit distinction between deterministic accounting and
  statistical validity;
- the old validity ladder, reviewer claim checks, evidence crosswalk, artifact
  lineage, and reproducibility protocol;
- the deterministic funded-set inequality and policy-premium algebra;
- transparent reporting of losses, reversals, and non-dominance.

### RECOMPUTE

Do not copy any number, table, or figure in these families:

- all return, default, miscoverage, endpoint, concentration, bootstrap, tail,
  regret, and policy-frontier results from Fronts A or B;
- every temporal table based on the resolved-only 2018--2020 pool;
- A3--A40 if it is to appear as final evidence;
- Prosper/Freddie replication and cross-dataset price-of-robustness figures;
- all selected-policy composition, grade/group, or fairness-adjacent tables;
- all figures whose geometry depends on the old selected allocation.

### HISTORY_ONLY

Preserve, cite internally for provenance, and exclude from active claims:

- `$184.8K`, `$179,327.59`, the 50,010-policy frontier, 8/8 alpha pass,
  alpha 0.01 headline, threshold 0.345084, and all pool93 promotion language;
- the v7 November/December "independent" selector narrative;
- the pooled 2018--2020 portfolio and its bootstrap interval;
- exact byte replay as evidence of scientific validity (it proves only
  computational fidelity to the stored artifact).

### RETIRE

Remove from the final method/novelty claim unless a new tagged experiment
directly needs it:

- Markov as headline theorem or "distribution-free funded-set certificate";
- cluster-bound tightening, Cantelli/Bennett/Bernstein menus, and Markov
  optimality as a contribution;
- capped/tail/OCE/CVaR/SPO+ policy families in the main method;
- "PD confidence interval," "nominal funded-set coverage," "preregistered,"
  "prospective," "untouched holdout," and fairness certification language;
- regret-auditability counts as a substitute for a matched decision baseline.

## Manuscript reconstruction blueprint

| Final body section | Best source material | Required reconstruction |
|---|---|---|
| 1. Introduction | A's decision framing; B's concise problem statement; C's maturity finding | Lead with outcome maturity, temporal shift, and selection; state one research question and proportional contributions |
| 2. Related Work | A's four-family map; B/C's close neighbors and 2024--2026 papers | Restore IJDS credit/cost-aware papers, censoring/profit scoring, conformal selection/risk control, and conformal optimization; remove catalog prose |
| 3. Data, outcome observability, and estimand | New from C and the state-of-art audit | Define origination-time universe, snapshot labels, unresolved outcomes, maturity gap, 36-month scope, and standardized payoff |
| 4. CRPTO guardrail and monthly decision | B's one-policy clarity; C's coherent solver contract | Name the conformal object correctly; state `p`, `[L,U]`, `q`, budget, purpose cap, comparator, and monthly timing |
| 5. What coverage can and cannot transport | A's deterministic proof; C's audits | Present binary interval semantics, deterministic accounting, and the exact all-candidate/temporal/selection decomposition; demote Markov |
| 6. Evaluation protocol | C's split and maturity contract | Show fit/calibration/conformal/selector/audit/OOT timeline, no-retune boundary, paired monthly metrics, and unresolved bounds |
| 7. Results | Fresh committed rerun only | Report predictive drift, candidate coverage, selected coverage, risk/payoff trade-off, monthly heterogeneity, and failure modes with equal prominence |
| 8. Decision and managerial implications | A's useful risk/payoff framing; B's non-dominance discipline | Explain when a guardrail hedges model optimism and why coverage failure prevents a certificate claim |
| 9. Reproducibility, limitations, and ethics | A/B governance material plus C receipts | State static retrospective development, simplified payoff, no fair-lending claim, and complete artifact lineage |
| 10. Conclusion | Rewrite | One result, one boundary, no additional paper/version narrative |

Target 16--19 official-template pages before references, comfortably below the
IJDS 25-page initial-submission body limit.

## Supplement reconstruction blueprint

1. **A. Estimand and data contracts.** Raw status mapping, feature availability,
   maturity logic, row counts, unresolved bounds, and split assertions.
2. **B. Conformal object and proofs.** Exact finite-sample rank, binary interval
   semantics, deterministic accounting, and coverage-transport decomposition.
3. **C. Predictive and temporal audit.** AUC/Brier/log loss/ECE, score range,
   group coverage, saturation, drift, and candidate-versus-funded coverage.
4. **D. Decision audit.** Full 3x3 development grid, coherent payoff
   reconciliation, purpose concentration, monthly allocations, and matched
   point-PD results.
5. **E. Robustness and inference.** Paired monthly differences, leave-period
   sensitivity, unresolved bounds, payoff/LGD sensitivity, and any justified
   block bootstrap.
6. **F. External evidence.** Include only after the same maturity, payoff, and
   decision-menu audit; otherwise state why it was omitted.
7. **G. Reproducibility and claims.** Commands, hashes, clean-clone receipt,
   validity ladder, reviewer checks, disclosure, and body/supplement crosswalk.

Restore the old supplement's useful navigation and auditability, not its old
evidence values or 32-page sprawl. A 18--24 page supplement is reasonable if
every table answers a live reviewer question.

## Claim reconstruction

| Candidate final claim | Status now | Promotion requirement |
|---|---|---|
| Status-independent maturity-safe credit decision protocol | Supported by C code/tests | Stable modular implementation, committed config, fresh immutable run |
| Coherent expected and realized standardized payoff | Supported by C code/tests | Preserve independent objective reconciliation; call it standardized payoff, not IRR/NPV |
| Monthly CRPTO guardrail reduces default relative to point-PD in 2016 | Directionally supported: -3.9443 pp aggregate; lower in 5/7 months | Fresh rerun and paired uncertainty; descriptive, not causal/universal |
| Guardrail improves realized standardized payoff | Directionally supported: +$21,545.80 over $7M; wins 4/7 months | Fresh rerun; report 0.3078 pp capital and temporal reversals |
| Guardrail preserves nominal conformal coverage | Falsified: funded coverage 0.6891 | Must not be promoted; make failure central |
| Marginal coverage degrades through time and selection | Supported in scratch | Save all-candidate temporal audit; report decomposition and group heterogeneity |
| Conformal score hedges PD optimism under shift | Plausible interpretation | Support with calibration-error and policy-allocation diagnostics; label as interpretation, not theorem |
| External transfer | Unsupported under final estimand | Re-audit from raw external menus or omit |
| Strong probabilistic funded-set certificate | Unsupported | Requires a genuinely selection-valid/decision-risk calibration protocol; not available now |

## Scratch result: what it does and does not say

The current C output is useful diagnostic evidence, not final evidence:

- Fit-period empirical coverage is 0.900161, a by-construction in-sample rank
  check, not an independent validation result.
- Resolved all-candidate OOT coverage is 0.873965; every score-Mondrian group is
  below 0.90 (0.8614--0.8953).
- The selected guardrail has funded coverage 0.689104 versus 0.716254 for the
  point-PD comparator. Selection amplifies, rather than repairs, miscoverage.
- Selected default is 0.301464 versus 0.340907; selected standardized payoff is
  `$56,698.18` versus `$35,152.38` over equal `$7M` capital.
- The guardrail wins payoff in 4/7 months and default in 5/7 months, but wins
  miscoverage in only 2/7 months and has lower expected objective in all seven.
- Expected objectives overstate realized payoff by `$1,048,464` (14.978% of
  capital) for the guardrail and `$1,138,257` (16.261%) for point-PD. The model
  is materially optimistic under temporal shift.
- Only 59 OOT candidate outcomes are unresolved and none receives funded
  exposure, so the current funded lower/upper bounds coincide. This may change
  in another time window and the bound machinery must remain.

The most defensible interpretation is conditional: the conformal-derived score
can act as a hedge against an optimistic, shifted PD model and improve a
risk/payoff contrast, while neither marginal coverage nor that economic hedge
transports into nominal funded-set coverage. That tension is more interesting
for IJDS than the old certificate claim, provided it survives a clean rerun and
is not sold as a guarantee.

## Mechanism audit: where the scratch differences come from

The current artifacts support a more informative descriptive decomposition
than a single candidate-versus-funded coverage gap. The nominal conformal
quantity is row-weighted, while the decision is dollar-weighted, so the audit
must expose that denominator change. Let:

- `M_row` be row-weighted OOT all-candidate miscoverage;
- `M_exp` be candidate miscoverage weighted by available loan exposure;
- `M_mix` combine candidate exposure-weighted group miss rates using the
  funded exposure share in each Mondrian group; and
- `M_fund` be funded-dollar miscoverage.

Then the identity

`M_fund-alpha = (M_row-alpha) + (M_exp-M_row) + (M_mix-M_exp) + (M_fund-M_mix)`

separates temporal/population degradation, exposure reweighting, between-group
composition, and within-group optimizer selection. It is descriptive, not
causal, but each term is exactly observable.

For the selected guardrail:

| Component | Value |
|---|---:|
| Temporal/population gap `M_row-alpha` | 0.026035 |
| Candidate exposure reweighting `M_exp-M_row` | 0.007150 |
| Mondrian composition shift `M_mix-M_exp` | 0.004472 |
| Within-group selection amplification `M_fund-M_mix` | 0.173238 |
| Total funded gap `M_fund-alpha` | 0.210896 |

Thus 97.5% of the shift from candidate exposure-weighted miscoverage to funded
miscoverage occurs *within* the declared score-Mondrian cells. The optimizer
selects high-rate subpopulations inside cells whose conformal guarantee is only
cell-marginal. A score-quantile partition does not protect an allocation that
adapts to contractual rate and other within-cell variables.

The matched point-PD allocation has the same pattern: 0.026035 temporal gap,
0.007150 exposure reweighting, 0.004746 composition shift, 0.145815
within-group amplification, and 0.183746 total funded gap. Both policies expose
the same transport problem.

The default-rate decomposition clarifies why the guardrail can still improve a
decision while worsening coverage:

| Policy | Candidate exposure-weighted default | Group-composition shift | Within-group selection increment | Funded default |
|---|---:|---:|---:|---:|
| Selected guardrail | 0.165221 | -0.033622 | 0.169865 | 0.301464 |
| Matched point-PD | 0.165221 | 0.010830 | 0.164857 | 0.340907 |

The guardrail's 3.9443 percentage-point default advantage comes more than
entirely from shifting capital toward lower-score Mondrian groups; its
within-group selection increment is about 0.50 percentage points worse and
offsets part of that composition benefit. It places 88.53% of exposure in
groups 0--1 versus 41.29% for point-PD and reduces the weighted conformal
premium from 0.53955 to 0.17771, while also reducing the weighted contractual
rate from 0.24694 to 0.21234.

Coverage moves in the opposite direction because the high-score groups often
have upper endpoint one. Defaults there count as covered even when decision
quality is poor. The point-PD policy therefore has more defaults but less
miscoverage, while the guardrail has fewer defaults but more miscoverage. This
is not a contradiction; it shows that saturated binary prediction coverage and
portfolio utility are different targets.

If the fresh run reproduces this decomposition, it should become the central
results mechanism. The strongest claim would be that the conformal score acts
as a coarse group-composition regularizer under shift, while marginal/Mondrian
coverage does not control the optimizer's within-group selection. That claim is
more precise and useful than saying the guardrail is generically robust.

## Code reconstruction decisions

| Component | Decision |
|---|---|
| `src/optimization/input_alignment.py` | Keep and strengthen; strict joins are a publication control |
| `src/optimization/policy_selection.py` | Keep generic grid/selection primitives; remove "active IJDS" wording and do not hard-code a scientifically privileged cap |
| `src/optimization/policy_evaluation.py` | Keep solver adapter; rename probability-like interval arguments if the final object is an outcome score |
| `src/optimization/certificate_semantics.py` | Split deterministic accounting from retired Markov/IJDS constants; preserve tested algebra only |
| `src/models/conformal_alpha_grid.py` | Keep as historical replay utility; do not use frozen widening as final scientific evidence |
| Maturity-safe runner | Refactor before rerun: current 1,958-line script has a D(21) `run_experiment` and maintainability index 0.00 |
| Data constructor changes | Preserve status-independent logic for new research; the canonical DVC command now opts explicitly into `--legacy-resolved-only` so frozen `prepare_dataset` remains compatible |
| Provenance | Keep deterministic core outputs, but restore implementation provenance in a separate receipt instead of deleting `source_commit` entirely |
| Tests | Keep all maturity, payoff, outcome-isolation, path-containment, ID-alignment, and operational guardrail tests |
| Dependency upgrades | Separate PR after the scientific lane is stable; never combine numerical migration with claim promotion |

Recommended module boundary for Front C:

- `src/data/outcome_observability.py`
- `src/data/maturity_design.py`
- `src/models/binary_conformal_guardrail.py`
- `src/evaluation/standardized_credit_payoff.py`
- `src/evaluation/coverage_transport.py`
- `scripts/experiments/run_ijds_maturity_safe_challenger.py` as orchestration only

The final runner should contain configuration, calls, and serialization, not a
second private data/model/conformal/evaluation framework.

## Preferred final empirical protocol before a new run

The current C split is valid for a diagnostic, but its April 2016 selector
cannot determine a risk preference by maximizing expected payoff alone without
the historically chosen endpoint cap. The smallest clean repair is to create a
separate matured policy-development block before the long decision gap:

1. **PD development:** originations through 2010, retaining the current
   temporal validation tail and fixed CatBoost parameters.
2. **Probability calibration:** calendar 2011 only.
3. **Conformal fit:** January--June 2012 only. The current status-independent
   universe contains 14,967 resolved 36-month loans in this half-year, enough
   for five score-quantile cells if the fresh group-count gate passes.
4. **Policy development:** July--December 2012 only, 28,503 resolved loans.
   Apply the already fitted conformal recipe and evaluate the declared small
   policy grid with one coherent, predeclared development criterion. Do not
   learn conformal widths or floors here.
5. **Maturity gap:** freeze model, calibrator, conformal recipe, policy rule,
   payoff, and all thresholds before April 2016. December 2012 to April 2016 is
   a 40-month gap for 36-month loans.
6. **Primary monthly OOT:** April 2016--June 2017, 15 fresh monthly decisions.
   June 2017 has at least 39 months to the September 2020 snapshot.
7. **Censored extension:** July--September 2017, reported separately with
   unresolved-outcome bounds rather than silently mixed into the primary OOT.
8. **Later originations:** 2018--2020 may illustrate menu size and censoring,
   but cannot provide a mature realized-payoff comparison at this snapshot.

The policy-development criterion must be committed before any new result. Two
defensible choices remain:

- **Preferred:** maximize development-block standardized payoff over the small
  grid, with no endpoint cap, then freeze the winner. Report development
  default/coverage as diagnostics, not additional selector constraints.
- **Fallback if selection is unstable:** do not crown a winner. Treat the 3x3
  linear grid as a declared sensitivity surface and use `gamma=0.5`,
  `tau=0.17` only as a historically motivated reference policy, never as an
  optimum or confirmatory champion.

The preferred split costs conformal sample size but buys the missing separation
between interval fitting and outcome-based policy development. It also yields a
longer maturity-safe monthly test than the current seven-month scratch run. No
2016/2017 outcome may change the grid, selector, payoff, groups, or dates after
the protocol commit.

## Final IJDS direction

Recommended working title:

**CRPTO: When Marginal Conformal Coverage Meets Maturity-Constrained Credit
Portfolio Selection**

Recommended research question:

> Under slow outcome maturity and temporal shift, can a conformal-derived
> guardrail improve monthly credit portfolio decisions, and what breaks when
> marginal coverage is transported to the selected funded set?

Recommended contribution set:

1. A status-independent, maturity-safe protocol for retrospective credit
   decisions with unresolved-outcome bounds.
2. A coherent monthly predict-then-optimize comparison in which the optimized
   and evaluated payoff are identical.
3. An exact audit separating temporal/population coverage degradation from
   selection amplification, with binary interval semantics made explicit.
4. Reproducible evidence that a guardrail may hedge model error and improve
   risk/payoff while still failing nominal funded-set coverage.

This remains one CRPTO paper. "Maturity-safe" is the corrected empirical design,
not CRPTO v2, and the negative coverage result is part of the method's honest
scope rather than a second paper.

## Promotion and stop conditions

No manuscript rewrite may turn scratch C numbers into active claims until all
of these are true:

1. The final conformal object and terminology are chosen and tested.
2. The cap is removed, externally justified, or explicitly limited to
   development sensitivity.
3. The maturity-safe code is modular, typed, linted, and committed before the
   result-producing run.
4. A fresh run tag is used; output directories do not exist beforehand.
5. Summary and execution receipt record config hash, implementation hashes,
   Git commit, dirty=false, package/solver versions, and artifact SHA-256s.
6. All-candidate temporal coverage, score-range extrapolation, endpoint
   saturation, and funded coverage are materialized as files, not only logs.
7. Monthly CRPTO and point-PD use identical menus, budgets, payoff, purpose cap,
   and solver contract.
8. The design-locked 2017 extension, if run, is called a retrospective temporal
   extension, never pristine confirmation: prior project work already inspected
   2017 labels.
9. External evidence is either re-audited under the final estimand or omitted.
10. `just lint`, `just type-check`, `just type-advisory-full`, full pytest,
    `just validate-champion`, required drift gate, paper builds, claim sync, and
    visual QA all pass from a clean clone/bundle.

Stop and keep the paper NO-GO if any result is selected by OOT outcomes, if the
canonical frozen lane is overwritten, if the payoff changes after results are
seen, or if the final prose upgrades empirical funded-set coverage into a
conformal guarantee.

## Immediate recovery completion checklist

- [x] Broad manuscript source frozen at `2a9b5e9` and `17811d8`.
- [x] Compact v7 source frozen at `63f9a9b` and `0f613f9`.
- [x] Maturity-safe scratch run identified separately from stable evidence.
- [x] Old sections, citations, figures, tables, supplement maps, and code
  contracts inventoried.
- [x] Direct recovery, rewrite, recomputation, history, and retirement classes
  defined.
- [x] Stale active-claim control documents marked NO-GO.
- [x] Canonical DVC dataset stage explicitly preserves historical resolved-only replay while new research defaults to status-independent membership.
- [x] Single-paper IJDS blueprint and promotion gates defined.
- [ ] Stable maturity-safe implementation and fresh evidence run.
- [ ] Final body/supplement/submission reconstruction after that run.
