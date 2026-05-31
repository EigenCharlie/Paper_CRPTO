# CRPTO literature deep dive - 2026-05-31

## Scope and guardrails

This memo records a literature audit for CRPTO after reading the project context,
the active IJDS manuscript, the thesis/book framing, the frozen champion metadata,
and all PDFs currently stored under `Papers_tesis/`.

No protected DVC stage was executed. No frozen champion artifact was modified.
This is a research and positioning memo only.

## Project reading

CRPTO is best framed as a post-hoc, auditable bridge from calibrated probability
of default estimation to conformal uncertainty quantification and robust credit
portfolio optimization. The current paper should not be sold as a predictive
leaderboard. Its defensible contribution is the decision layer:

- CatBoost/Venn-Abers style calibrated PD model as input, not the sole novelty.
- Split/Mondrian conformal intervals as distribution-free uncertainty wrappers.
- Robust portfolio selection over Lending Club loans using frozen policies.
- An audit trail that links `alpha`, conformal width, robust value, exact
  violation, and challenger diagnostics.
- A regret-auditability frontier: CRPTO favors decisions that remain interpretable
  and stress-testable, while SPO/DFL style methods are useful comparators and
  future work.

Current core numbers from frozen metadata:

- OOT Lending Club evaluation: 276,869 loans.
- Economic champion: `bound_aware_276k_economic_champion`.
- Robust return: USD 170,464.54.
- `V(alpha=0.01)`: 0.03645.
- `Gamma_CP(alpha=0.01)`: 0.18591.
- Exact pass: `True`.
- Robust region: 45/45 alpha-safe policies.
- PD diagnostics: AUC about 0.7124, Brier about 0.1546, ECE about 0.0064.

The manuscript already has the right center of gravity: limited operational
claims, explicit finite-sample boundaries, frozen champion governance, and a
supplement for sensitivity and future-method material.

## Local PDF inventory and recommendation

All 33 local PDFs were extracted to text and scanned for CRPTO relevance. The
highest-value mapping is below.

| PDF | Main contribution for CRPTO | Recommended use |
| --- | --- | --- |
| `10_Conformal_Robust_Optimizati.pdf` | Conformal robust optimization and satisficing with black-box predictors. | Strong future/related work. Use for satisficing and target-margin language, not as a current-method claim. |
| `A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification.pdf` | Core CP tutorial. | Body foundation. Already appropriate. |
| `An_Old-New_Concept_of_Convex_Risk_Measures_The_Opt.pdf` | Optimized certainty equivalents. | Supplement/tail-risk diagnostic only. |
| `Conformal Contextual Robust Optimization.pdf` | Contextual robust optimization with conformal regions. | Body nearest-neighbor method. Contrast CRPTO's credit portfolio and audit layer. |
| `Conformal Prediction Under Covariate Shift.pdf` | Weighted CP under covariate shift. | Future work or robustness caveat; static Lending Club does not need drift over new originations. |
| `Conformal Uncertainty Sets for Robust Optimization.pdf` | Conformal uncertainty sets for RO. | Body foundation and nearest-neighbor comparison. |
| `Conformal_Risk_Control.pdf` | CRC/risk-control framework for expected monotone losses. | Body/supplement foundation for risk-control language. |
| `CREDIT SCORES - PERFORMANCE AND EQUITY.pdf` | ML credit scores, performance/equity tradeoffs. | Intro/domain context. Do not overclaim legal fairness. |
| `Distribution-Free, Risk-Controlling Prediction Sets.pdf` | RCPS foundation. | Body/supplement risk-control foundation. |
| `FinRegLab_2023-12-07_Research-Report_Explainability-and-Fairness-in-Machine-Learning-for-Credit-Undewriting_Policy-Analysis.pdf` | Credit underwriting governance, explainability, fairness. | Governance/MRM framing and thesis chapter context. |
| `Group-weighted conformal prediction.pdf` | Group-weighted CP under group shift. | Future work and rationale for group-aware/Mondrian segmentation. |
| `Learn then test.pdf` | Calibration by hypothesis testing. | Foundation for finite-sample risk-control framing. |
| `Localized Conformal Prediction - A Generalized Inference Framework to Conformal Prediction.pdf` | Localized/segment-aware CP. | Future work or thesis expansion for local intervals. |
| `Multi-Distribution Robust Conformal Prediction.pdf` | Multi-distribution robust CP. | Supplement/future work for source-shift or multi-market extension. |
| `Optimal Model Selection for Conformalized Robust Optimization.pdf` | CRO model selection with decision risk. | Strong future/selector reference; supports decision-aware selection without rerunning champion search. |
| `Optimization of Conditional Value-at-Risk.pdf` | CVaR optimization. | Tail-risk/challenger diagnostics only. |
| `Predict-then-Calibrate.pdf` | Predict-then-calibrate for robust contextual LP. | One of the closest method neighbors. Body related work. |
| `Robust Losses for Decision-Focused Learning.pdf` | Robust losses for DFL. | Regret-auditability comparator and future work. |
| `shared_future_work/Conformal Risk Control for Non-Monotonic Losses.pdf` | CRC extension beyond monotone losses. | A22/future tail-risk material. |
| `shared_future_work/Conformal Risk Training End-to-End Optimization of Conformal Risk Control.pdf` | End-to-end training for conformal risk control. | Future work; would be method-changing, not current CRPTO. |
| `shared_future_work/Decision-Focused Learning - Foundations, State of the Art, Benchmark and Future Opportunities.pdf` | DFL survey. | Body comparator and thesis context. |
| `shared_future_work/End-to-End Conformal Calibration for Optimization Under Uncertainty.pdf` | End-to-end conformal calibration for optimization. | Important future-method neighbor; contrast with CRPTO's post-hoc auditability. |
| `shared_future_work/GradientEquilibriuminOnlineLearning - TheoryandApplications.pdf` | Online learning theory. | Thesis future work only. Low priority for IJDS. |
| `shared_future_work/Label Noise Robustness of Conformal Prediction.pdf` | CP robustness under label noise. | Data-quality caveat/future work. Low priority. |
| `shared_future_work/Online Conformal Prediction via Universal Portfolio Algorithms.pdf` | Online CP via universal portfolios. | A24/future online monitoring; not current static-dataset paper. |
| `shared_future_work/ONLINE DECISION-FOCUSED LEARNING.pdf` | Online DFL. | Future work only. |
| `Smart “Predict, then Optimize”.pdf` | SPO/SPO+ decision-focused learning. | Body comparator; supports regret-auditability framing. |
| `Task-based End-to-end Model Learning in Stochastic Optimization.pdf` | End-to-end task-based learning. | Body comparator/future work. |
| `The limits of distribution-free conditional predictive inference.pdf` | Impossibility of exact conditional distribution-free inference. | Essential claim boundary. Keep it prominent. |
| `The Price of Robustness.pdf` | Budgeted robust optimization tradeoff. | Body foundation for robust tradeoffs. |
| `the-roles-of-alternative-data.pdf` | Lending Club and alternative data in fintech lending. | Essential empirical-domain citation. |
| `Theoretical Foundations of Conformal Prediction.pdf` | Formal CP foundations. | Body/theory foundation. |
| `Using-Publicly-Available-Information-to-Proxy.pdf` | BISG proxy methodology. | Fairness-boundary citation; use to say what CRPTO does not legally claim. |

## What is already well integrated

The current `book/references.bib`, `paper/CRPTO_ijds.qmd`, and research notes
already cover most of the central spine:

- CP foundations: Vovk/Shafer, Angelopoulos and Bates, Angelopoulos et al.
  theoretical foundations.
- Risk-control foundations: Bates et al. RCPS, Angelopoulos CRC, Learn-then-Test.
- Conditional/group coverage boundaries: Barber limits, Mondrian/group-weighted
  CP, localized CP.
- Conformal robust optimization: Johnstone and Cox, Patel et al., Sun et al.,
  Yeh et al., CROMS, multi-distribution robust CP.
- Robust optimization and risk: Bertsimas and Sim, CVaR, OCE.
- Predict-then-optimize and DFL: SPO+, Donti, DFL survey, robust DFL losses.
- Credit-risk context: Lessmann, Bellini, Jagtiani and Lemieux, Albanesi and
  Vamossy, FinRegLab, CFPB BISG.

The most important editing principle is therefore restraint. The paper does not
need a larger bibliography dump. It needs a sharper novelty paragraph and a small
number of missing/updated neighbors.

## New or underused papers worth adding or verifying

### 1. Conformal Robustness Control

Source: Yang Hu, Jieren Tan, Changliang Zou, Yajie Bao, Haojie Ren,
`Conformal Robustness Control: A New Strategy for Robust Decision`, ICLR 2026
Oral, OpenReview: <https://openreview.net/forum?id=bt4Ahpemmi>.

Why it matters:

- This is a very close 2026 neighbor: conformal prediction plus contextual robust
  optimization plus decision robustness.
- It directly argues that coverage is sufficient but not necessary for robustness,
  and optimizes prediction-set construction under explicit robustness constraints.

Recommended use:

- Add to related work/future work as a nearest-neighbor method.
- Do not present it as invalidating CRPTO. CRPTO's claim is domain-specific,
  auditable credit portfolio optimization over frozen Lending Club artifacts,
  not a generic CRC algorithm.

### 2. Conformalized Decision Risk Assessment (CREDO)

Source: Wenbin Zhou, Agni Orfanoudaki, Shixiang Zhu,
`Conformalized Decision Risk Assessment`, arXiv:2505.13243:
<https://arxiv.org/abs/2505.13243>.

Why it matters:

- It gives distribution-free decision-risk certificates for candidate decisions.
- It fits CRPTO's auditability narrative: the decision itself can be certified,
  not only the predictive model.

Recommended use:

- Add to future work or related work on decision audit certificates.
- It is not a replacement for CRPTO's portfolio optimizer. It is better framed as
  adjacent support for the "auditable decision" thesis.

### 3. Conformal Prediction for Ordinal Credit Scoring

Source: Kawasumi, Kato, Duan, `Conformal Prediction for Ordinal Credit Scoring`,
JSAI Technical Report 2026, DOI `10.11517/jsaisigtwo.2026.fin-036_128`:
<https://cir.nii.ac.jp/crid/1390870529360837888>.

Why it matters:

- It means the broad claim "no CP in credit scoring" would be unsafe.
- It is about conformal intervals for ordinal credit scores, not robust credit
  portfolio optimization.

Recommended use:

- Mention only if the paper needs a sentence acknowledging CP-credit-scoring
  work.
- Use it to sharpen the gap: CRPTO is not merely CP for credit scores; it is CP
  feeding a robust portfolio decision and an audit protocol.

### 4. Data-Driven Robust Credit Portfolio Optimization for P2P Lending

Source: Guotai Chi, Shijie Ding, Xiankun Peng, `Data-Driven Robust Credit
Portfolio Optimization for Investment Decisions in P2P Lending`, Mathematical
Problems in Engineering, 2019, DOI `10.1155/2019/1902970`:
<https://doi.org/10.1155/2019/1902970>.

Why it matters:

- It is a direct predecessor for robust portfolio optimization in P2P lending.
- It does not use conformal prediction or CRPTO-style finite-sample interval
  calibration.

Recommended use:

- Add to related work if the current paper needs stronger credit-portfolio
  optimization lineage.
- Position as "credit portfolio RO exists; CRPTO adds conformal uncertainty and
  auditability."

### 5. Integrating AI and OR for digital lending investment decisions

Source: Vajiheh Torkian, Shahrooz Bamdad, Amir Homayoun Sarfaraz,
`Integrating AI and OR for investment decision-making in emerging digital lending
businesses: a risk-return multi-objective optimization approach`, Journal of the
Operational Research Society, DOI `10.1080/01605682.2025.2498652`.

Why it matters:

- Uses Lending Club and an AI/OR investment-decision framing.
- It is a recent applied OR comparator in the exact domain neighborhood.

Recommended use:

- Optional. Useful for thesis/book or a related-work footnote.
- Not essential for the IJDS core if space is tight.

### 6. Finance portfolio conformal papers

Sources:

- Miquel Noguer i Alonso, `Conformal Portfolio Optimization`, SSRN:
  <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5011129>.
- Masahiro Kato, `Conformal Predictive Portfolio Selection`, arXiv:2410.16333:
  <https://arxiv.org/abs/2410.16333>.

Why they matter:

- They show conformal prediction has entered portfolio selection.
- Their setting is financial asset returns, not installment-loan credit risk and
  not the Lending Club loan-selection problem.

Recommended use:

- Keep as broader finance context, not as main competition.

## Recommended novelty wording

Avoid:

- "No prior work uses conformal prediction in credit."
- "No prior work uses robust optimization for P2P lending."
- "CRPTO provides conditional coverage guarantees."
- "The champion is optimal in general."

Use:

> Existing work studies conformal uncertainty sets for robust optimization,
> conformal risk control, decision-focused learning, and credit-risk modeling
> largely as separate strands. CRPTO contributes an auditable predict-then-optimize
> pipeline for credit portfolio selection that combines calibrated PD estimates,
> Mondrian conformal uncertainty, robust portfolio optimization, and frozen
> artifact validation on Lending Club data.

If space allows, add:

> The closest methodological relatives are conformal robust/contextual
> optimization and predict-then-calibrate frameworks; the closest domain relatives
> are P2P lending credit-risk and robust portfolio optimization studies. CRPTO's
> distinct contribution is the end-to-end audited decision layer for credit
> portfolio selection rather than a new conformal algorithm in isolation.

## Where each literature block should go

Body of IJDS paper:

- CP foundations and finite-sample guarantees.
- Johnstone/Cox, Patel CPO, Predict-then-Calibrate, Conformal Robustness Control.
- Bertsimas and Sim for robust tradeoff.
- SPO+/DFL only as comparator.
- Lending Club/credit-risk foundations: Jagtiani and Lemieux, Lessmann, Bellini,
  FinRegLab/Albanesi if needed.
- Barber limits to guard claims.

Supplement:

- CVaR/OCE tail-risk diagnostics.
- CROMS, multi-distribution robust CP, group-weighted CP.
- Non-monotonic CRC, conformal risk training.
- Online CP via universal portfolios.
- End-to-end conformal calibration.

Thesis/book:

- Full 33-paper synthesis.
- Ordinal credit scoring CP.
- P2P robust portfolio optimization.
- AI+OR Lending Club decision-making paper.
- CFPB BISG and fair-lending boundaries.
- Label-noise and online-learning material.

## Bibliographic hygiene issues

These should be fixed before using the affected entries as formal citations:

- `docs/research/foundations/crpto_references_state_of_art.md` contains placeholder
  arXiv links that returned 404 in a direct check:
  - `2504.00000` for Counterfactually Fair Conformal Prediction.
  - `2401.00000` for Online conformal inference for multi-step TS forecasting.
  - `2407.00000` for JANET.
- `book/references.bib` has `jagtiani2019altdata` DOI as
  `10.21799/frbp.wp.2018.150`. The local PDF and FRB Philadelphia metadata point
  to `10.21799/frbp.wp.2018.15`. Verify before editing the bibliography.
- Some 2026 papers are preprint/workshop/conference-neighbor sources. They are
  valuable for positioning, but the paper should distinguish peer-reviewed,
  accepted, and preprint status.

## Prioritized action list

1. Keep the IJDS paper tight. Do not expand the body into a survey.
2. Add or verify `Conformal Robustness Control` as a nearest-neighbor 2026
   related-work/future-work citation.
3. Add or verify CREDO if the paper wants stronger "decision audit certificate"
   language.
4. Add the P2P robust credit portfolio paper if the novelty paragraph needs a
   direct domain predecessor.
5. Acknowledge CP-credit-scoring work only if making a broad CP-in-credit claim.
6. Clean the three placeholder arXiv links in the foundations note before using
   that note as citation source.
7. Verify and correct the Jagtiani/Lemieux DOI before the next bibliography pass.

## Bottom line

The literature strengthens CRPTO, but it also narrows the claim. The safest and
most publishable thesis is not "CRPTO invents conformal robust optimization" and
not "CRPTO is the first CP application in credit." The strongest claim is:

> CRPTO operationalizes conformal robust optimization for credit portfolio
> selection, with frozen-artifact validation and an audit trail that connects
> calibrated PD, conformal uncertainty, robust portfolio value, tail diagnostics,
> and governance boundaries in a static Lending Club setting.
