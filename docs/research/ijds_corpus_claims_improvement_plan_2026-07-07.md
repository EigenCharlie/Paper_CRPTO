# IJDS Corpus, Claims, and Improvement Plan - 2026-07-07

> **Superseded metric vocabulary (2026-07-09).** This memo is retained as the
> corpus-reading and editorial decision trail. Its old "Markov cap" and
> preliminary frontier language must not be used as current evidence. The
> policy-aware A35 correction and matched A40 baseline in
> `pool93_certificate_semantics_v2_2026-07-09.md` are authoritative.

Scope: analyze the current CRPTO body paper, official IJDS submission PDF/source,
online supplement, frozen metrics/artifacts, and the local `Papers_tesis` corpus
using the global `academic-pdf-intake` skill outputs.

This memo does **not** reopen the champion, does **not** modify
`EXTRACTION_MANIFEST.json`, and does **not** recommend rerunning protected DVC
stages. The active paper claim remains the finite-grid decision certificate
registered in `docs/research/active_claims_2026-07-04.md`.

## Implementation Status

Status on 2026-07-07: the actionable P0/P1/P2 editorial recommendations in this
memo have been applied to the manuscript, official IJDS `.tex` handoff,
supplement, submission checklist, bibliography, and reviewer-defense matrix.
This file is retained as traceability for the corpus/IJDS analysis and parser
evidence, not as an open TODO list. Future edits should use
`paper/submission/SCHOLARONE_FINAL_CHECKLIST.md` and
`docs/research/active_claims_2026-07-04.md` as the active operating gates.

## Inputs Used

Skill / benchmark outputs:

- Full local inventory:
  `.tmp_pdf_intake_benchmark/run_20260707_1715/manifest.jsonl`
- Full parser benchmark:
  `.tmp_pdf_intake_benchmark/run_20260707_1715/runs.jsonl`
- Current literature matrix generated from extracted text:
  `.tmp_pdf_intake_benchmark/run_20260707_ijds_lit_analysis/corpus_current_inventory.csv`
- IJDS venue snippets:
  `.tmp_pdf_intake_benchmark/run_20260707_ijds_lit_analysis/ijds_venue_snippets.csv`
- Parser summary for active CRPTO PDFs:
  `.tmp_pdf_intake_benchmark/run_20260707_ijds_lit_analysis/active_crpto_parser_benchmark.csv`
- MinerU CUDA follow-up for active CRPTO PDFs:
  `.tmp_pdf_intake_benchmark/run_20260707_active_mineru_cuda/runs.jsonl`

CRPTO sources:

- `paper/CRPTO_ijds.qmd`
- `paper/submission/CRPTO_ijds_submission.tex`
- `paper/submission/CRPTO_ijds_submission.pdf`
- `paper/supplement_ijds.qmd`
- `paper/CRPTO_ijds.pdf`
- `paper/supplement_ijds.pdf`
- `reports/crpto/tables/crpto_tableA19_regret_auditability_frontier.csv`
- `reports/crpto/tables/crpto_tableA25_external_replication_gate.csv`
- `reports/crpto/tables/crpto_tableA35_pool93_ijds_frontier.csv`
- `reports/crpto/tables/crpto_tableA36_pool93_body_funded_grade_audit.csv`
- `reports/crpto/tables/crpto_tableA37_pool93_body_tail_risk.csv`
- `reports/crpto/tables/crpto_tableA38_pool93_body_cluster_bound_audit.csv`
- `reports/crpto/tables/crpto_tableA39_pool93_body_bootstrap_metrics.csv`
- `models/experiments/champion_reopen/.../pool93_ijds_claim_governance.json`
- `models/experiments/champion_reopen/.../pool93_ijds_consolidated_governance.json`

IJDS public sources checked on 2026-07-07:

- Submission guidelines:
  <https://pubsonline.informs.org/page/ijds/submission-guidelines>
- Reviewer guidelines:
  <https://pubsonline.informs.org/page/ijds/reviewer-guidelines>
- Editorial statement:
  <https://pubsonline.informs.org/page/ijds/editorial-statement>
- Data and Code Disclosure Policy:
  <https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>

## Executive Diagnosis

CRPTO is well matched to IJDS when written as **data science for decisions**:
real credit data, a methodological bridge from calibrated prediction to robust
optimization, managerial/model-risk relevance, practical implications, and
reproducible computational evidence. The strongest submission story is not
"better credit scoring." It is:

> CRPTO converts a frozen calibrated PD model into an auditable robust funding
> decision by carrying conformal uncertainty into a finite-grid portfolio
> frontier, exposing the return-bound trade-off and validating the selected
> funded set from frozen evidence.

The paper is already close to this framing. The main improvement opportunity is
reader focus: reduce the cognitive load around internal run history, make the
closest IJDS precedents visible, and make the A35 frontier the unmistakable
decision object.

The main risk is overclaiming by shorthand. In particular, the current body and
submission use "0.345 Markov cap" as a rounded lens. The active body/default
point has `Markov_cap = 0.345083740`; the strict `<= 0.345` frontier row is a
neighboring policy with return `$184,800.41`, not the body/default return
`$184,832.48`. This is fixable in prose by saying "approximately 0.3451" or
"the declared 0.345 return-bound lens" and by avoiding exact `<= 0.345` language
for the body/default row.

## Official IJDS Fit

The IJDS submission guidelines say IJDS publishes data science methodologies
for decision-making environments and expects four components: data, innovative
model/algorithm/approach, managerial/engineering/industrial relevance, and
implications. CRPTO has all four:

| IJDS component | CRPTO evidence | Current strength | Improvement |
|---|---|---|---|
| Data | Lending Club OOT panel; Prosper and Freddie/Mendeley external frozen applications. | Strong. | Keep external results as recipe transfer, not as extra certificates. |
| Model / algorithm | Calibrated PD -> Mondrian conformal intervals -> robust LP -> exact funded-set audit. | Strong. | Name the methodological unit earlier as a "decision certificate." |
| Decision relevance | `$1M` budgeted credit funding with return/risk trade-off. | Strong. | Make A35/A19 the reader-facing proof of relevance. |
| Implications | Reproducible model-risk audit surface; explicit limits on live/conditional claims. | Strong. | Put implications in abstract/conclusion as knowledge gained, not only actions performed. |

Venue constraints that matter:

- Initial submissions should be at most 25 IJDS-style pages excluding references
  and appendices.
- IJDS uses double-anonymous review for submissions on/after 2025-01-01.
- Abstract must be one paragraph and <=300 words; IJDS strongly encourages it
  to answer problem/relevance, methods/results, and insights/implications.
- Tables/figures should appear near first mention.
- Data/code disclosure is required at submission, and accepted computational
  papers are expected to upload data/code or an approved alternative plan.

The current official-template build is 26 pages total, with conclusion and
references starting on page 22, so the body appears inside the IJDS page budget
when references are excluded. The reproducibility package plan is aligned with
the IJDS policy, but review-stage path/identity sanitization remains essential.

## Current CRPTO Claim Stack

Active body point:

| Quantity | Current value |
|---|---:|
| OOT Lending Club universe | `276,869` loans |
| Budget | `$1,000,000` |
| Selected-policy realized return | `$184,832.48` |
| Return-floor surplus | `$14,367.94` |
| `V(alpha=0.01)` | `0.035350` |
| `Gamma_CP(alpha=0.01)` | `0.162616` |
| Endpoint budget upper | `0.245083740` |
| Markov cap | `0.345083740` |
| Exact alpha violation | `0.0` |
| Alpha-grid pass | `8/8` |
| Bootstrap return interval | `$167,963.20` to `$198,650.47` |

Finite-grid denominators:

| Surface | Denominator | Result |
|---|---:|---|
| Consolidated semantic policies | `50,010` | `27,508` pass every declared alpha and exceed return floor |
| Raw consolidated rows | `51,678` | `1,668` duplicate semantic rows removed |
| Terminal endpoint policies | `37,068` | `37,068/37,068` all-alpha passers |
| Terminal alpha checks | `296,544` | `296,544/296,544` completed checks |

Main claim boundary:

- Claim **finite-grid decision certificate**, not continuous global optimality.
- Claim **weighted funded-set validity plus Markov bound**, not universal
  conditional coverage.
- Claim **frozen external economic recipe transfer**, not Prosper/Freddie exact
  Lending Club-style certificates.
- Claim **regret-auditability trade-off**, not dominance over SPO+ or other
  decision-focused learners on every regret metric.
- Claim **fixed-allocation bootstrap diagnostics**, not a conformal/bootstrap
  guarantee over model retraining, solver inputs, or search.

## Paper / Submission / Supplement Assessment

### Body and official submission

Strengths:

- The abstract already starts with the correct IJDS premise: credit allocation is
  a data-science-for-decisions problem.
- The introduction explicitly says the research question is not a better
  classifier, but whether predictive uncertainty can be carried into a robust
  auditable portfolio decision.
- The contribution list separates construction, theorem, literature positioning,
  frozen evidence, and evidence ladder.
- The official submission uses the IJDS `informs4` class with `dblanonrev`, and
  the build instructions now document both `latexmk` and the robust
  `pdflatex -> bibtex -> pdflatex -> pdflatex` fallback.
- The body has the right core tables: certificate metrics, finite-grid frontier,
  reviewer-question boundary table, regret-auditability table, and supplement
  map.

Risks / repairs:

- **Cap wording repair:** replace exact-sounding "under the declared 0.345
  Markov cap" for the body/default point with "near the declared 0.345
  return-bound lens" or "Markov cap 0.345084." Keep the strict `<=0.345` row as
  a neighboring frontier endpoint, not the body point.
- **A35 should be the first durable result object.** The paper currently explains
  many pieces before the reader sees the frontier. A reviewer should encounter
  the frontier logic as soon as possible after the certificate table.
- **IJDS precedent paragraph is thin.** The body cites relevant work, but the
  venue-specific story can be sharper: IJDS has already published credit ML,
  cost-aware calibration, causal decision framing, and reproducibility-oriented
  data-science-for-decisions papers. CRPTO extends that line into a portfolio
  decision certificate.
- **External replications are valuable but slightly loud in the abstract.** They
  support transfer of the recipe; they should not compete with the Lending Club
  certificate as the abstract's main result.
- **SPO+ comparison is strong but needs a crisp takeaway sentence.** The current
  text is accurate: SPO+ wins synthetic regret; CRPTO buys auditable risk
  controls and a dollar-funded set. Put that exact contrast in one memorable
  sentence before the table.

### Supplement

Strengths:

- A35--A39 are exactly the right selected-policy closure block.
- A37--A39 correctly close tail, concentration, and empirical contribution
  objections without changing the selector.
- A25--A34 answer the single-dataset concern through external economic recipe
  transfer and exhaustiveness checks.
- Appendix E makes routine reproduction distinct from protected champion/search
  reruns.

Risks / repairs:

- The supplement is rich enough that a reader may miss the hierarchy. Add a
  short "how to read this supplement" map at the top that says: theory -> active
  certificate -> diagnostics -> external transfer -> reproduction.
- A35 should be introduced as the supplement's active frontier, not as another
  appendix table among many.
- A25--A34 should keep the words "economic replication" and "recipe transfer"
  visible. Avoid "external validation" unless it is immediately scoped.
- In A38, the fact that every cluster-aware threshold is looser than Markov is a
  strength: it explains why the body does not chase a more fragile bound.

## Parser / Skill Findings

The `academic-pdf-intake` skill routing is sensible for this repo:

- **Docling** remains the primary parser for born-digital academic PDFs and
  clean Markdown/JSON extraction.
- **OpenDataLoader hybrid** is the best comparison/fallback when bounding boxes,
  reading-order traceability, hidden-text safety, and table provenance matter.
- **MinerU CUDA hybrid-engine** is now viable on the local RTX/CUDA setup for
  the active CRPTO PDFs and is best kept for formula-heavy, OCR-heavy, scanned,
  or visual-QA cases.
- **Codex PDF / MarkItDown** are useful as fast baselines and smoke tests, not
  as the final source for complex academic extraction.

Active PDF benchmark:

| PDF | Pages | Docling | OpenDataLoader | MinerU CUDA |
|---|---:|---:|---:|---:|
| `paper/CRPTO_ijds.pdf` | 27 | 54.98s | 57.09s | 60.41s |
| `paper/submission/CRPTO_ijds_submission.pdf` | 26 | 46.14s | 35.00s | 54.47s |
| `paper/supplement_ijds.pdf` | 32 | 78.41s | 70.30s | 74.20s |

Operational recommendation:

- For day-to-day paper analysis: Docling first, ODL for table/traceability
  comparison, Codex PDF for fast diffable text.
- For final figure/table/formula QA: add MinerU on the active PDF(s), then check
  `layout.pdf` / visual outputs when extraction disagreement is material.
- For the full 81-PDF literature corpus: do not run all three heavy parsers
  routinely. Use fast baseline + Docling on close papers, then ODL/MinerU only
  on candidates with tables, equations, or layout ambiguity.

## `Papers_tesis` Corpus Summary

Current corpus inventory:

- `81` local literature PDFs in `Papers_tesis`
- `3,404` literature pages
- `3` active CRPTO PDFs separately, `85` pages
- Full generated matrix:
  `.tmp_pdf_intake_benchmark/run_20260707_ijds_lit_analysis/corpus_current_inventory.csv`

Topic signals from extracted text:

| Topic signal | PDFs |
|---|---:|
| Tables / metrics / experiments | 78 |
| Tail risk / CVaR / OCE / loss | 76 |
| Portfolio / optimization / decision | 68 |
| Robust optimization / uncertainty sets | 67 |
| Conformal / coverage / calibration | 57 |
| Fairness / governance / explainability | 57 |
| Source shift / weighted / multi-source | 55 |
| Credit / lending / default | 38 |
| Causal decision | 24 |
| Decision-focused / SPO / PTO | 22 |
| Online / adaptive conformal | 20 |

These counts are keyword/topic signals, not claims that every paper is equally
central. The editorial use is by cluster.

## IJDS Papers in or Adjacent to the Local Corpus

Confirmed IJDS papers with local or official evidence:

| Paper | Evidence | What it contributes | CRPTO use | Boundary |
|---|---|---|---|---|
| Das et al. (2023), "Credit Risk Modeling with Graph Machine Learning" | Local PDF header and DOI `10.1287/ijds.2022.00018`; official IJDS page. | Extends tabular credit scoring with corporate graph features and GNN/AutoML ensembles; includes reproducibility capsule. | Shows IJDS accepts credit-risk ML when data/method/reproducibility are clear. Position CRPTO as a **decision certificate after scoring**, not a richer scorer. | Corporate credit ratings, not consumer loan portfolio funding; no conformal/robust funded-set certificate. |
| Yang and Bi (2025), "Cost-Aware Calibration of Classifiers" | Official IJDS DOI `10.1287/ijds.2024.0038`; cited in CRPTO `.bbl`. | Defines cost-aware calibration, expected calibration cost, and MetaCal; emphasizes downstream costs of miscalibration. | Strongest IJDS calibration precedent. CRPTO extends calibration into **portfolio allocation and funded-set audit**. | Classifier calibration problem, not robust portfolio optimization. |
| Fernandez-Loria and Provost (2022), "Causal Decision Making and Causal Effect Estimation Are Not the Same..." | Official IJDS DOI `10.1287/ijds.2021.0006`; cited in CRPTO `.bbl`. | Separates decision quality from effect-estimation accuracy. | Use to sharpen the intro: CRPTO is a decision object, not a prediction leaderboard. | Causal treatment assignment framing, not credit PD/conformal portfolio. |
| Fernandez-Loria and Provost (2025), "Observational vs. Experimental Data When Making Automated Decisions Using Machine Learning" | Local PDF in supplement; official DOI `10.1287/ijds.2023.0012`. | Shows observational data can sometimes support automated decisions when the decision target is ranking/thresholding rather than unbiased effect estimation. | Supports CRPTO's observational-panel boundary and the claim that decision metrics differ from estimation metrics. | Causal/automated intervention setting; CRPTO should cite it as a limitation/future protocol, not as causal validity. |
| Falconer, Kazempour, and Pinson (2026), "Toward Replication-Robust Analytics Markets" | Local PDF header and DOI `10.1287/ijds.2025.0075`; official IJDS page. | Builds an analytics market robust to strategic data replication; emphasizes reproducibility and strategic robustness. | Useful venue signal: IJDS values robust/reproducible analytics systems. Use only as a light reproducibility/robustness cousin. | Market design/collaborative analytics, not credit, conformal prediction, or portfolio funding. |

The local corpus also references Morucci et al. (2022), an IJDS causal
uncertainty paper, but the PDF is not in `Papers_tesis`; do not count it as
local corpus evidence unless it is added.

## Closest Non-IJDS Literature Clusters

### 1. Conformal foundations and risk control

Key local papers:

- Angelopoulos and Bates (2023), gentle introduction.
- Angelopoulos et al. (2024), conformal risk control.
- Angelopoulos et al. (2025), Learn Then Test.
- Bates et al. (2021), risk-controlling prediction sets.
- Barber et al. (2021), conditional coverage limits.
- Angelopoulos et al. (2026), non-monotonic CRC.
- Gibbs/Candes, Lekeufack et al., Kiyani et al., Zhou/Orfanoudaki/Zhu.

What they give CRPTO:

- Validity language and finite-sample discipline.
- Justification for risk-control framing.
- Limits on conditional/group/live claims.

How to improve paper:

- Keep them as theory lineage, but do not over-expand.
- Use them to justify why CRPTO reports a bound and exact audit rather than only
  nominal coverage.

### 2. Conformal robust optimization / predict-then-calibrate

Key local papers:

- Johnstone and Cox (2021), conformal uncertainty sets for robust optimization.
- Patel et al. (2024), conformal contextual robust optimization.
- Sun et al. (2024), predict-then-calibrate.
- Zhao et al. (2026), conformal robust optimization and satisficing.
- Bao et al. (2025), CROMS model selection.
- Yeh et al. (2025/2026), conformal risk training / end-to-end calibration.
- Zhou and Zhu (2025), inverse conformal risk control.

What they give CRPTO:

- The nearest methodological neighborhood.
- A natural "what CRPTO adds" contrast: real credit payoff, funded-set weights,
  exact portfolio audit, finite frontier, and reproducibility harness.

How to improve paper:

- Add a compact contrast table: abstract CRO/LP papers vs. CRPTO's credit
  funded-set certificate.
- Say explicitly that CRPTO is post-hoc over a frozen PD system; end-to-end
  variants are future work.

### 3. Decision-focused learning and SPO+

Key local papers:

- Elmachtoub and Grigas (2022), SPO+.
- Donti et al. (2017), task-based end-to-end learning.
- Mandi et al. (2024), DFL survey.
- Liu and Grigas (2021), risk bounds/calibration for SPO.
- Schutte et al. (2024), robust losses for DFL.

What they give CRPTO:

- The main alternative methodological family.
- A strong reviewer question: "Why not train through the optimizer?"

How to improve paper:

- Keep A19/Figure 15 central.
- State the contrast in one sentence:
  "SPO+ is the low-regret corner; CRPTO is the auditable-risk-control corner
  with a funded-set dollar certificate."
- Do not apologize for higher synthetic regret; explain that the metric is
  different from the funded-set economic certificate.

### 4. Credit / P2P / fairness / governance

Key local papers:

- Jagtiani and Lemieux (2019), fintech Lending Club context.
- Serrano-Cinca and Gutierrez-Nieto (2016), profit scoring in P2P lending.
- Guo et al. (2016), instance-based P2P credit investment.
- Zhao et al. (2016), P2P portfolio selection.
- Chi, Ding, and Peng (2019), data-driven robust P2P credit portfolio.
- Das et al. (2023), IJDS graph ML credit risk.
- Albanesi and Vamossy (2024), score performance and equity.
- Fuster et al. (2022), unequal ML credit-market effects.
- Blattner and Nelson (2021), noisy data and consumer credit disparities.
- FinRegLab (2023), explainability and fairness in credit underwriting.
- CFPB (2014), proxy race/ethnicity methods.

What they give CRPTO:

- Domain legitimacy and governance boundaries.
- Support for reporting economic return, risk, calibration, and governance
  together.

How to improve paper:

- Keep fairness/proxy material bounded. CRPTO does not have protected labels or a
  legal fair-lending protocol.
- Use credit/P2P papers to motivate why classification metrics alone are
  insufficient for investment decisions.

### 5. Robust optimization, DRO, tail risk, and concentration

Key local papers:

- Bertsimas and Sim (2004), price of robustness.
- Ben-Tal, El Ghaoui, and Nemirovski (2009), robust optimization.
- Bertsimas, Gupta, and Kallus (2018), data-driven robust optimization.
- Bertsimas and Kallus (2020), predictive to prescriptive analytics.
- Delage and Ye (2010), moment DRO.
- Goldfarb and Iyengar (2003), robust portfolios.
- Rockafellar and Uryasev (2000), CVaR.
- Ben-Tal and Teboulle (2007), OCE.
- Hoeffding, Bennett, Freedman, Fuk-Nagaev for concentration context.

What they give CRPTO:

- The language for price of robustness and uncertainty budgets.
- Tail-risk diagnostics and the reason to keep Markov as the weakest defensible
  body-level statement.

How to improve paper:

- A37/A38 should be discussed as "assumption-priced sensitivity."
- Avoid making CVaR/OCE sound like promoted selectors.

### 6. Source shift, multi-distribution, online conformal

Key local papers:

- Tibshirani et al. (2019), conformal prediction under covariate shift.
- Barber, Candes, Ramdas, Tibshirani (2023), beyond exchangeability.
- Bhattacharyya and Barber (2026), group-weighted conformal prediction.
- Guan (2023), localized conformal prediction.
- Liu, Levis, Normand, Han (2024), multi-source conformal inference.
- Yang and Jin (2026), multi-distribution robust conformal prediction.
- Gibbs and Candes (2021), adaptive conformal inference.
- Liu et al. (2026), online conformal prediction via universal portfolios.

What they give CRPTO:

- A future-work lane and reviewer caveats for group/source/live deployment.

How to improve paper:

- Keep A23/A24 as diagnostics.
- Do not promote multi-distribution or online validity without a new protocol.

## High-Priority Improvement Plan

### P0: repair precision in cap wording

Change any exact-sounding text that says the body/default point is under a
`0.345` cap. The exact body/default cap is `0.345083740`; the strict
`<=0.345` row is a neighboring frontier point.

Recommended wording:

- "the selected policy sits at the declared approximately 0.345 return-bound
  lens, with Markov cap 0.345084"
- "the strict `<=0.345` endpoint earns `$184,800.41`; the body/default balanced
  point earns `$184,832.48` with Markov cap `0.345084`"

Avoid:

- "highest-return point under cap `<=0.345`" for the body/default row.
- "declared `0.345` Markov cap" unless the next words clarify rounding.

### P1: add a venue-specific IJDS precedent table

Add a compact body table or paragraph after the related-work overview:

| IJDS precedent | Lesson for CRPTO | CRPTO extension |
|---|---|---|
| Das et al. (2023) credit graph ML | IJDS accepts reproducible credit-risk ML. | CRPTO turns credit risk scores into a funded portfolio certificate. |
| Yang and Bi (2025) cost-aware calibration | Calibration matters because downstream costs are asymmetric. | CRPTO prices uncertainty inside a budgeted allocation. |
| Fernandez-Loria and Provost (2022/2025) decision vs estimation | Decision quality is not the same as estimation/prediction quality. | CRPTO evaluates the funded decision, not only PD quality. |
| Falconer et al. (2026) replication-robust analytics | IJDS values robust/reproducible analytics systems. | CRPTO supplies frozen evidence, exact checks, and a reproducibility harness. |

This helps the editor see fit immediately and helps reviewers place the paper
inside IJDS rather than only OR/ML.

### P1: make A35 the central result object

Move the reader quickly from method to A35:

1. Exact certificate table: what the selected policy achieved.
2. A35 frontier: why this is not a cherry-picked singleton.
3. A19 regret-auditability: why CRPTO is not trying to beat SPO+ on its own
   synthetic regret metric.
4. A25 external recipe transfer: why the method is not a Lending Club-only
   curiosity.

The current paper has these pieces; the improvement is ordering and signposting.

### P1: sharpen abstract to IJDS's three-question template

Current abstract is good but can be more IJDS-aligned:

1. Problem/relevance:
   "Credit allocation decisions need calibrated probabilities only insofar as
   they change funding choices under risk appetite."
2. Methods/results:
   "CRPTO maps frozen PD predictions through Mondrian conformal intervals into a
   robust LP and finite-grid funded-set audit; on 276,869 OOT loans it earns
   `$184.8K` on `$1M` with `V=0.035350`, `Gamma_CP=0.162616`, and Markov cap
   `0.345084`."
3. Insight/implication:
   "The insight is that uncertainty should be reported as a return-bound
   frontier, not as a post-hoc calibration table; reproducible decision
   certificates can be audited without retraining a production-style PD model."

Reduce abstract space devoted to external replications unless needed for
single-dataset defense.

### P1: make the baseline story a reviewer checklist

IJDS reviewers will ask whether the paper uses reasonable baselines and
quantifies improvement. CRPTO can answer with a table:

| Baseline / family | What it optimizes | CRPTO comparison |
|---|---|---|
| Two-stage baseline | Predict then optimize without conformal robust certificate. | CRPTO adds exact funded-set bound and frontier. |
| SPO+ / DFL | Synthetic regret / task-aligned training loss. | SPO+ has lower mean regret; CRPTO has funded-set dollar value and 3/3 verifiable risk controls. |
| P2P profit scoring | Economic loan selection. | CRPTO adds conformal premium and exact alpha-safe audit. |
| P2P robust portfolio | Robust credit allocation. | CRPTO calibrates uncertainty with conformal intervals and exposes finite-grid denominators. |
| Cost-aware calibration | Probability calibration under asymmetric costs. | CRPTO carries calibrated uncertainty into a portfolio decision. |

The goal is not to claim universal dominance; it is to make the trade-off
impossible to miss.

### P2: strengthen supplement navigation

Add a short supplement reader map:

- Appendix A: proof and Markov boundary.
- Appendix B: robustness/challenger diagnostics.
- Appendix C: active A35--A39 selected-policy closure.
- Appendix D: external recipe transfer.
- Appendix E: reproducibility, DVC, protected stages, and anonymization.

Then repeat the claim hierarchy in one table:

| Evidence | Promoted? | Why |
|---|---:|---|
| A35 | Yes | Active finite-grid frontier. |
| A36--A39 | Support | Selected-policy composition/tail/concentration/bootstrap diagnostics. |
| A19 | Support | Regret-auditability contrast. |
| A25--A34 | Support | External economic recipe transfer. |
| A20--A24 | Diagnostics | Tail/source/online objections, not selector changes. |

### P2: citation hygiene before freeze

The previous citation audit flagged several body references as partial or
citation-only. This pass reduces risk for `das2023creditgraph`,
`yang2025costaware`, and the Fernandez-Loria/Provost IJDS papers. Still
spot-check before final freeze:

- `hoeffding1963`, `boucheron2013concentration`, `ghosh2002`
- `goldfarb2003robustportfolio`, `delage2010dro`
- `serrano2016profitscoring`, `zhao2016p2pportfolio`
- any recent credit/IJDS references added after 2026-06-14

Do this as source verification, not as a broad literature expansion.

### P2: prepare response-ready reviewer objections

Prewrite one paragraph each:

- "Why not SPO+?"
- "Why not CVaR/OCE as the selector?"
- "Is the result cherry-picked?"
- "What happens under dependence?"
- "Is this a live-production guarantee?"
- "What exactly can be reproduced under double anonymous review?"

Most answers already exist in the body/supplement; the improvement is to make
them short and reusable.

## Concrete Editing Checklist

Before submission:

1. Replace exact-sounding `0.345` cap wording for the body/default point.
2. Add IJDS precedent paragraph/table with Das, Yang/Bi, Fernandez-Loria/Provost,
   and Falconer/Kazempour/Pinson.
3. Move or signpost A35 so the finite-grid frontier appears as the main results
   object, not only as a supporting table.
4. Add one compact "what the reviewer should remember" paragraph before the
   A19 regret table.
5. Tighten abstract external-replication language to "recipe transfer."
6. Add supplement reader map and promoted/support/diagnostic hierarchy.
7. Check all anonymous review paths: no repo URLs, local paths, author names,
   affiliations, or identifying metadata in body/supplement PDFs.
8. Run `just smoke` and `just validate-champion` after any paper edits.
9. Rebuild official submission PDF and check page count/log.

Do **not** do before submission unless a reviewer or explicit research decision
requires it:

- Rerun protected champion/search/conformal stages.
- Promote CVaR/OCE, multi-distribution, online, causal, or end-to-end DFL
  variants.
- Turn external Prosper/Freddie replications into new exact funded-set
  certificates.
- Expand the body with a long literature review.

## Best Current IJDS Story

The paper should read like this:

1. Credit allocation is a decision problem; PD calibration alone is insufficient.
2. Existing IJDS work shows calibration, credit ML, and causal decision framing
   matter for data-science decisions.
3. CRPTO contributes the missing bridge: a frozen predictive model becomes a
   robust funding decision with a conformal premium and exact finite-grid audit.
4. The selected policy earns `$184,832.48` on `$1M`, with `V=0.035350`,
   `Gamma_CP=0.162616`, and Markov cap `0.345084`.
5. The result is not a singleton: A35 exposes 50,010 semantic policies and a
   return-bound frontier.
6. The method does not beat SPO+ at SPO+'s own regret target; instead, it buys
   auditability, risk controls, and a funded-set dollar certificate.
7. The supplement shows tail, concentration, bootstrap, source, online, and
   external-recipe checks without changing the body claim.
8. The reproducibility package is part of the scientific contribution, not just
   administration.

That is the IJDS version of CRPTO: **a reproducible decision certificate for
credit portfolio allocation under conformal uncertainty**.
