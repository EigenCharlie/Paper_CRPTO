# CRPTO State-of-the-Art Review - 2026-05-18

> Ported from the CRPTO research archive
> (`crpto_state_of_art_review_2026-05-18`). Consolidates a deeper
> literature pass for the official CRPTO manuscript and the long-horizon agenda extendida CRPTO/tesis
> living lab agenda. It is not a new experimental loop and not a Quarto rewrite.
> The output is a source map and a claim-governance recommendation.

## Executive Decision

CRPTO should stay centered on the economic champion and the conformal-robust
portfolio contribution. The best literature additions are positioning and
reviewer defense, not new claims:

- Use conformal risk control, Learn-then-Test, conditional-coverage limits and
  conformal robust optimization to explain why the method controls decision risk
  without pretending to solve exact conditional validity.
- Use robust optimization and predict-then-optimize references to position CRPTO
  as prescriptive analytics with calibrated uncertainty, not merely prediction.
- Use credit scoring, fintech lending and model-risk references to explain why
  the Lending Club application is practically relevant and why auditability
  matters.
- Mention CVaR/OCE only as a tail-risk challenger appendix/sensitivity; do not
  reopen the champion.

agenda extendida CRPTO/tesis remains a governed living lab (agenda). Its strongest contribution is
not a near-term publication claim; it is a documented boundary map for seven
ambitious extensions. Four lanes are append-worthy as evidence appendices, while
three remain parked. The prudential IFRS9-inspired material enters agenda extendida CRPTO/tesis as
proxy evidence (ECL scenarios, conformal ECL ranges, SICR width signal,
CIF/prepayment correction, stage-cost governance, TS-to-ECL stress context),
never as contractual IFRS 9.

| lane | decision | literature role | claim boundary |
| --- | --- | --- | --- |
| IFRS9/SICR | append | IFRS 9, ECL, survival and competing-risk sources justify a proxy diagnostic | not contractual IFRS 9 without monthly DPD, contractual terms and macro scenarios |
| CVaR/OCE | append | CVaR and OCE sources justify tail-risk challenger analysis | not champion replacement without paired wealth gains |
| fair-lending proxy | append | BISG, proxy-fairness and ML underwriting governance sources justify proxy-risk governance | not legal fair-lending evidence without surname, protected attributes or tract-level geography |
| DLA/ADP | append | SDAM/ADP sources justify sequential rollout framing | not exact Bellman optimality without decision logs and state transition panels |
| online conformal | park | ACI and multi-source conformal explain what would be needed | no live feedback or external source distribution |
| CATE/policy value | park | causal and double-ML sources support a sensitivity appendix only | no causal policy claim without rejected applicants or an instrument |
| SPO/DFL | park | SPO+, PyEPO and cvxpylayers explain the prototype direction | no main-pipeline integration while benefit is only toy/oracle-regret evidence |

## CRPTO: Best Literature Fit

### 1. Conformal Decision Guarantees

The official manuscript already has a solid conformal backbone. The highest
value additions are not more conformal breadth, but clearer hierarchy:

- Foundation: Vovk et al. and Romano et al. establish distribution-free
  conformal prediction and conformalized quantile regression.
- Risk control: Bates et al., Angelopoulos et al. on Conformal Risk Control, and
  Learn-then-Test support the paper's risk-control language.
- Boundary: Barber, Candes, Ramdas and Tibshirani on limits of distribution-free
  conditional predictive inference should be used to prevent overclaiming source
  or subgroup validity.
- Prescriptive bridge: Johnstone and Cox, Patel et al., and Sun et al.
  strengthen the conformal robust optimization / robust contextual LP framing.

Recommended use: one compact paragraph in the theory/literature section, plus a
reviewer-facing note that CRPTO controls an operational risk target and does not
claim exact conditional coverage for every borrower/source subgroup.

### 2. Robust Optimization and Prescriptive Analytics

The robust optimization literature should position CRPTO as a decision pipeline,
not as a forecasting-only paper:

- Bertsimas and Sim is the core robust optimization reference for uncertainty
  budgets and the price of robustness.
- Conformal uncertainty sets for robust optimization and conformal contextual
  robust optimization are the closest methodological neighbors.
- Predict-then-Calibrate is especially useful because it frames robust contextual
  LP through calibration rather than pure point prediction.
- SPO+ and DFL should be cited only as adjacent decision-focused learning. CRPTO
  does not need to become a differentiable optimization paper.

Recommended use: add a "closest methods" contrast: CRPTO is closer to calibrated
robust prescriptive analytics than to end-to-end SPO/DFL.

### 3. Credit Scoring, Fintech Lending and Model Risk

The credit literature should support empirical relevance and governance:

- Lessmann et al. provide a widely cited credit-scoring benchmark and connect
  predictive accuracy with business value.
- Jagtiani and Lemieux are directly relevant because they study Lending Club and
  fintech lending with alternative data and loan grades.
- SR 11-7 and FinRegLab support model-risk governance, auditability,
  explainability and fair-lending sensitivity language.

Recommended use: strengthen the introduction and empirical setting. This is the
cleanest way to make the Lending Club application feel less like a dataset
exercise and more like a regulated credit decision problem.

### 4. Tail-Risk Challenger, Not Champion Reopening

CVaR and OCE references are valuable for reviewer defense if a reader asks why
the official champion is not tail-risk optimized:

- Rockafellar and Uryasev support the CVaR optimization formulation.
- Ben-Tal and Teboulle support OCE as a convex risk-measure family.
- The agenda extendida CRPTO/tesis CVaR/OCE experiment is useful as a challenger appendix because it
  improved tail framing but did not beat paired wealth.

Recommended use: keep this as appendix/sensitivity. Do not reopen the economic
champion unless future paired replay beats it robustly.

## agenda extendida CRPTO/tesis (agenda): Best Literature Fit By Lane

### IFRS9/SICR

The literature supports a proxy diagnostic, not a full IFRS 9 implementation.
IFRS Foundation and Basel/EBA materials establish the accounting and supervision
context. Recent survival, competing-risk and term-structure ECL work supports
the idea that default timing and lifetime PD matter. Keep as an appendix: the
project has useful cashflow, hardship and recovery fields, but lacks monthly
contractual days-past-due history, original effective interest rate accounting
infrastructure and macro scenario paths. The honest title is "IFRS9-inspired
SICR/ECL proxy diagnostic."

### Online Conformal / Source Holdouts

ACI, multi-source conformal and multi-distribution conformal references justify
the direction of the lane. The conditional-coverage impossibility literature is
also important: source-aware coverage is not free. Keep the existing source
holdout evidence as retrospective governance only. Do not claim online/adaptive
validity until there is live feedback, a production-like stream, or a genuinely
external source distribution.

### CVaR/OCE

Append-worthy. CVaR/OCE literature gives a clean mathematical language for tail
utility and risk aversion, and the existing experiment is useful as a
stress/challenger result. The blocker is not theory; it is empirical dominance.
The challenger did not replace the economic champion. Destination: appendix tail
challenger and caveat for CRPTO.

### CATE / Policy Value

The causal literature is useful mainly because it tells us to stop. DoWhy,
double/debiased ML and causal-forest references require explicit identification,
overlap and refutation. Lending Club accepted-loan data can support an
observational sensitivity screen, but not a strong policy-value claim because
rejected applicants, randomized pricing or a credible instrument are absent.
Destination: parked with a causal-identification memo, not a promoted
experiment.

### Fair-Lending Proxy

Valuable for claim boundaries. CFPB BISG and Zhang's proxy-method literature
show why surname plus fine geography matter. The project has state and zip3, not
surname or protected attributes. Destination: appendix source/proxy-governance
risk. Legal fair-lending claims remain false. A good example of a valuable
negative result.

### DLA/ADP

Powell's SDAM/ADP framing fits the sequential decision lab, but the data blocks
exact dynamic programming. Snapshot fields can support rollout-style diagnostics
and state summaries, not Bellman optimality. Destination: appendix
rollout/sequential analytics. Good framing, weak optimality claim.

### SPO/DFL

SPO+, PyEPO and cvxpylayers establish a legitimate frontier, but the current
project only has isolated toy/oracle-regret evidence. Integrating this would
increase dependency and maintenance risk without improving the official
champion. Destination: parked prototype. Reopen only on a specific reviewer
request or a compact optimization benchmark that directly dominates a CRPTO
comparator. See [crpto_pyepo_dfl_intake_2026-05-26](../crpto_pyepo_dfl_intake_2026-05-26.md)
for the PyEPO 1.3.7 update.

## Candidate Additions To Bibliography (small, text-tied)

Highest priority candidates not yet fully integrated into the official narrative:

- Barber et al. on limits of distribution-free conditional predictive inference.
- Jagtiani and Lemieux on Lending Club fintech lending.
- FinRegLab's ML credit underwriting policy/empirical reports.
- Rockafellar and Uryasev on CVaR if the tail-risk appendix is cited.
- Ben-Tal and Teboulle on OCE if OCE remains in the appendix text.
- CFPB BISG and Zhang if a fair-lending/proxy governance appendix is kept.
- Agrawal et al. and Tang/Khalil only if the SPO/DFL prototype is referenced.

## Anti-Loop Reopen Gates

Reopen a parked or append lane only if one of these happens:

- A monthly servicing panel becomes available (contractual DPD, payment states,
  macro scenario paths).
- Rejected-applicant data or randomized pricing/instrumental variation appears.
- Surname, tract-level geography or protected-attribute proxy inputs appear with
  an approved governance plan.
- A reviewer explicitly asks for a lane and the response fits one compact
  table/memo.
- A future run can change the official champion under the paired wealth gate.

Otherwise, the correct next move is not more experiments; it is citation
integration and manuscript extraction.

## Bibliography Integration Patch (2026-05-18)

Adds only sources that now appear in the manuscript; destinations expressed by
manuscript role (standalone CRPTO chapter labels differ from the old `14x` scheme):

| source | manuscript role | reason |
| --- | --- | --- |
| `barber2021_limits_conditional` | theory / claim frontier | Bound source/subgroup claims and avoid overstating conditional validity. |
| `jagtiani2019` | introduction / empirical setting | Establish Lending Club as a real fintech-lending empirical setting. |
| `rockafellar2000_cvar` | tail-risk appendix | Ground CVaR as a canonical tail-risk diagnostic. |
| `bental_teboulle2007_oce` | tail-risk appendix | Ground OCE as convex risk-measure framing. |
| `finreglab2023_ml_credit` | governance / fairness proxy | Support ML credit underwriting governance, explainability and fairness context. |
| `cfpb_bisg_proxy` | fairness proxy boundary | Document why surname plus fine geography are needed for BISG-style proxy analysis. |
| `zhang2018_fair_proxy` | fairness proxy boundary | Support the fair-lending proxy boundary and why current fields are insufficient for legal claims. |

No IFRS9, SPO/DFL prototype or agenda extendida CRPTO/tesis-only sources were integrated into CRPTO
in this patch. Those remain agenda extendida CRPTO/tesis (agenda) material unless a future appendix or
reviewer request creates a concrete textual need.

## Metrics Binder Addendum

The metrics binder was triaged on 2026-05-18 and logged in
[crpto_metrics_triage_2026-05-18](crpto_metrics_triage_2026-05-18.md). The only
source that should enter CRPTO as methodological support is Wuthrich's
Gini/autocalibration result: it reinforces the claim that CRPTO is not an AUC
leaderboard, and that rank metrics are meaningful only after the PD layer is
calibration-gated. Albanesi and Vamossy can support the credit scoring/equity
motivation as context only; it does not authorize a legal fair-lending claim.

For agenda extendida CRPTO/tesis, the binder opens one bounded future appendix: FICO/score proxy vs
champion ML, with misclassification, ranking difference and observable-group
diagnostics. Dinga et al. is taxonomy-only, Somers' D is optional metric
sensitivity, and ReScorer stays parked unless the project later audits
LLM-generated research reasons.
