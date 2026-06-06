> **RESEARCH NOTE** — Curated state-of-the-art bibliography for CRPTO, ported and
> de-identified from the CRPTO reference ledger
> (`docs/PAPER_REFERENCES_STATE_OF_ART.md`). This is working material for the
> IJDS paper and the thesis; it does not replace the live policy or results. The
> canonical citation database is `book/references.bib`.

# CRPTO — State of the Art (2026)

Curated bibliography for the CRPTO (Conformal Robust Predict-Then-Optimize)
publication strategy. Each entry includes a direct link. The "in `references.bib`?"
column tracks whether the entry is already wired into the local citation database.

The 17 thesis PDFs that anchor the conformal+optimization positioning were
re-read during the bound audit; their conclusion is that none forces a champion
change, but they sharpen the editorial agenda: CRPTO today is post-hoc/two-stage
and the journal version can move toward decision-aware conformal selection, OCE/CVaR
tail risk, multi-distribution coverage, and online recalibration as explicit
future work.

---

## A. Conformal Prediction — Foundations

| # | Paper | Authors | Year | Venue | BibTeX key |
|---|-------|---------|------|-------|------------|
| A1 | Algorithmic Learning in a Random World | Vovk, Gammerman & Shafer | 2005 | Springer (book) | `vovk2005` |
| A2 | Conformalized Quantile Regression | Romano, Patterson & Candès | 2019 | NeurIPS | `romano2019` |
| A3 | Conformal Prediction: A Gentle Introduction | Angelopoulos & Bates | 2023 | FnT ML | `angelopoulos2023` |
| A4 | Conformal Risk Control | Angelopoulos, Bates, et al. | 2024 | ICLR | `angelopoulos2024risk` |
| A5 | Theoretical Foundations of Conformal Prediction | Angelopoulos, Barber & Bates | 2024 | arXiv (monograph) | `angelopoulos2024foundations` |
| A6 | Conformal Prediction: A Data Perspective (Survey) | — | 2025 | ACM Comp. Surveys | `cpsurvey2025` |
| A7 | The Limits of Distribution-Free Conditional Predictive Inference | Barber et al. | 2021 | Inf. & Inference | `barber2021limits` |

## B. Mondrian & Group-Conditional Coverage

| # | Paper | Authors | Year | Venue | BibTeX key |
|---|-------|---------|------|-------|------------|
| B1 | Mondrian Conformal Predictive Distributions | Boström et al. | 2021 | COPA | `bostrom2021` |
| B2 | Class-Conditional Conformal Prediction with Many Classes | Ding et al. | 2023 | NeurIPS | `ding2023` |
| B3 | Conformal Prediction With Conditional Guarantees | Gibbs & Cherian | 2024 | JRSS-B | `gibbs2024` |
| B4 | Conformal Classification with Equalized Coverage for Adaptively Selected Groups | Zhou & Sesia | 2024 | NeurIPS | `zhou2024` |
| B5 | Kandinsky Conformal Prediction | Bairaktari et al. | 2025 | ICML | `bairaktari2025` |
| B6 | Probabilistic Conformal Prediction with Approximate Conditional Validity | Plassier et al. | 2024 | arXiv | `plassier2024` |
| B7 | Group-Weighted Conformal Prediction | Bhattacharyya & Barber | 2026 | EJS | `bhattacharyya2026groupweighted` |
| B8 | Localized Conformal Prediction | Guan | 2023 | Biometrika | `guan2023localized` |

## C. Conformal Prediction + Robust Optimization

| # | Paper | Authors | Year | Venue | BibTeX key |
|---|-------|---------|------|-------|------------|
| C1 | Conformal Uncertainty Sets for Robust Optimization | Johnstone & Cox | 2021 | COPA | `johnstone2021` |
| C2 | Conformal Contextual Robust Optimization | Patel, Rayan & Tewari | 2024 | AISTATS | `patel2024` |
| C3 | End-to-End Conformal Calibration for Optimization Under Uncertainty | Yeh et al. | 2025 | TMLR | `yeh2026` |
| C4 | End-to-End Conditional Robust Optimization | Chenreddy et al. | 2024 | UAI | `chenreddy2024` |
| C5 | Conformal Robust Optimization and Satisficing | Zhao, Jiang & Qi | 2026 | AISTATS-W / SSRN | `zhao2025robust` |
| C6 | Optimal Model Selection for Conformalized Robust Optimization (CROMS) | Bao et al. | 2025 | arXiv | `bao2025croms` |
| C7 | Conformal Inverse Optimization | Chan, Delage & Lin | 2024 | NeurIPS | `chan2024inverse` |
| C8 | Risk-controlling Prediction with Distributionally Robust Optimization | Iutzeler & Mazoyer | 2025 | TMLR | `iutzeler2025dro` |
| C9 | Multi-Distribution Robust Conformal Prediction | Yang & Jin | 2026 | arXiv | `yang2026multidistribution` |
| C10 | Predict-then-Calibrate: A New Perspective of Robust Contextual LP | Sun, Liu & Li | 2024 | arXiv | `sun2024ptc` |

## D. Conformal Prediction in Finance & Portfolios

| # | Paper | Authors | Year | Venue | BibTeX key |
|---|-------|---------|------|-------|------------|
| D1 | Conformal Predictive Portfolio Selection | Kato | 2025 | arXiv | `kato2025` |
| D2 | Conformal Portfolio Optimization | Noguer i Alonso | 2024 | SSRN | `noguer2024portfolio` |
| D3 | Conformal Prediction in Finance (survey) | Noguer i Alonso | 2024 | SSRN | `noguer2024survey` |
| D4 | Online Conformal Prediction via Universal Portfolio Algorithms | Liu, Dobriban & Orabona | 2026 | arXiv | `liu2026portfolio` |
| D5 | Adaptive Conformal Inference for Computing Market Risk Measures | Fantazzini | 2024 | JRFM | `fantazzini2024` |

## E. Decision-Focused Learning / Predict-then-Optimize

| # | Paper | Authors | Year | Venue | BibTeX key |
|---|-------|---------|------|-------|------------|
| E1 | Smart "Predict, then Optimize" (SPO+) | Elmachtoub & Grigas | 2022 | Management Science | `elmachtoub2022` |
| E2 | Decision-Focused Learning: Foundations, SOTA, Benchmark | Mandi et al. | 2024 | JAIR | `mandi2024` |
| E3 | Task-based End-to-end Model Learning in Stochastic Optimization | Donti, Amos & Kolter | 2017 | NeurIPS | `donti2017` |
| E4 | Decision Theoretic Foundations for Conformal Prediction | Kiyani et al. | 2025 | AISTATS/ICML | `kiyani2025` |
| E5 | Conformal Risk Training | Yeh et al. | 2025 | NeurIPS | `yeh2025training` |
| E6 | The Price of Robustness | Bertsimas & Sim | 2004 | Operations Research | `bertsimas2004` |
| E7 | Online Decision-Focused Learning | Capitaine et al. | 2026 | ICLR | `capitaine2026online` |
| E8 | Robust Losses for Decision-Focused Learning | Schutte, Postek & Yorke-Smith | 2024 | IJCAI | `schutte2024robust` |

## F. Credit Risk, IFRS9 & Survival Analysis

| # | Paper | Authors | Year | Venue | BibTeX key |
|---|-------|---------|------|-------|------------|
| F1 | PD for lifetime credit loss for IFRS 9 using ML competing risks | Bárcena Saavedra et al. | 2024 | Expert Sys. w/ Applications | `barcena2024` |
| F2 | Defining and comparing SICR-events under IFRS 9 | — | 2025 | Annals of OR | `sicr2025` |
| F3 | Approaches for modelling term-structure of default risk under IFRS 9 | Botha & Verster | 2026 | IJDSA | `botha2026` |
| F4 | Practical Credit Risk and Capital Modeling | Bellini et al. | 2024 | Springer | `bellini2024` |
| F5 | Random survival forests and Cox regression in LGD estimation | Ptak-Chmielewska & Kopciuszewski | 2024 | J. Credit Risk | `ptakchmielewska2024survival` |
| F8 | Financial Risk Assessment Model (CP + Cox PH) | — | 2025 | Preprints.org | `financialriskcp2025` |
| F6 | ECB IFRS 9 overlays and model improvements for novel risks | ECB | 2024 | ECB Banking Supervision | `ecb2024` |
| F7 | IFRS Board SICR Feedback Analysis | IFRS Board | 2024 | IFRS Meeting | `ifrsboard2024` |

## G. ML in Credit Scoring

| # | Paper | Authors | Year | Venue | BibTeX key |
|---|-------|---------|------|-------|------------|
| G1 | ML powered financial credit scoring: systematic review | Ayari, Guetari & Kraiem | 2026 | AI Review | `ayari2026` |
| G2 | Benchmarking state-of-the-art classification for credit scoring | Lessmann et al. | 2015 | EJOR | `lessmann2015` |
| G3 | Credit Scores: Performance and Equity | Albanesi & Vamossy | 2024 | NBER WP | `albanesi2024credit` |
| G4 | Roles of Alternative Data and ML in Fintech Lending (LendingClub) | Jagtiani & Lemieux | 2019 | FRB Philadelphia | `jagtiani2019altdata` |
| G5 | A boosted decision tree approach with Bayesian HPO for credit scoring | Xia et al. | 2017 | Expert Sys. w/ Applications | `xia2017` |
| G6 | Integrating AI and OR for Investment Decision-Making (LendingClub) | — | 2025 | JORS | `aior2025lendingclub` |
| G7 | Two-Stage ML for Credit Risk with Fragmentary Data | Zheng et al. | 2026 | Expert Sys. w/ Applications | `zheng2026twostage` |
| G8 | Comparative Analysis of Boosting Algorithms for Predicting Personal Default | Nguyen and Ngo | 2025 | Cogent Econ. & Finance | `boosting2025default` |

## H. Causal Inference in Credit

| # | Paper | Authors | Year | Venue | BibTeX key |
|---|-------|---------|------|-------|------------|
| H1 | Double/Debiased ML for Treatment and Structural Parameters | Chernozhukov et al. | 2018 | The Econometrics Journal | `chernozhukov2018` |
| H2 | Estimating Treatment Effects with Causal Forests | Athey & Wager | 2019 | Annals of Statistics | `athey2019` |
| H3 | Causal Inference for Banking, Finance, and Insurance (Survey) | — | 2023 | arXiv | `causalfinance2023` |

## I. Calibration

| # | Paper | Authors | Year | Venue | BibTeX key |
|---|-------|---------|------|-------|------------|
| I1 | Probabilistic Outputs for SVMs | Platt | 1999 | Adv. Large Margin Classifiers | `platt1999` |
| I2 | Transforming classifier scores into accurate probability estimates | Zadrozny & Elkan | 2002 | KDD | `zadrozny2002` |
| I3 | Venn-Abers Predictors | Vovk & Petej | 2014 | UAI | `vovk2014` |
| I4 | Beta Calibration | Kull, Silva Filho & Flach | 2017 | AISTATS | `kull2017` |

## J. Conformal under shift / online & robustness

| # | Paper | Authors | Year | Venue | BibTeX key |
|---|-------|---------|------|-------|------------|
| J1 | Adaptive Conformal Inference Under Distribution Shift (ACI) | Gibbs & Candès | 2021 | NeurIPS | `gibbs2021aci` |
| J2 | Conformal Prediction Under Covariate Shift | Tibshirani et al. | 2019 | NeurIPS | `tibshirani2019covshift` |
| J3 | Gradient Equilibrium in Online Learning | Angelopoulos, Jordan & Tibshirani | 2025 | JMLR | `angelopoulos2025gradient` |
| J4 | Label Noise Robustness of Conformal Prediction | Einbinder et al. | 2024 | JMLR | `einbinder2024labelnoise` |

## K. Tail risk (CVaR / OCE) — A22 support

| # | Paper | Authors | Year | Venue | BibTeX key |
|---|-------|---------|------|-------|------------|
| K1 | Optimization of Conditional Value-at-Risk | Rockafellar & Uryasev | 2000 | The Journal of Risk | `rockafellar2000cvar` |
| K2 | An Old-New Concept of Convex Risk Measures: OCE | Ben-Tal & Teboulle | 2007 | Mathematical Finance | `bental2007oce` |

## L. Fair lending: proxy methods and policy

| # | Paper | Authors | Year | Venue | BibTeX key |
|---|-------|---------|------|-------|------------|
| L1 | Using Publicly Available Info to Proxy Race/Ethnicity (BISG) | CFPB | 2014 | CFPB report | `cfpb2014bisg` |
| L2 | Explainability and Fairness in ML for Credit Underwriting | FinRegLab | 2023 | FinRegLab | `finreglab2023fairness` |

---

## Key gaps the literature still leaves open (CRPTO positioning)

These gaps are what make the CRPTO contribution defensible — they are the "white
space" the manuscript claims to occupy:

1. **No prior work** combines Mondrian conformal prediction with credit *portfolio*
   robust optimization end-to-end.
2. **No prior work** turns the conformal interval width into a robust *constraint*
   on a funded-set weighted-miscoverage bound (the `V` / `Γ_CP` construction).
3. **No prior work** uses conformal interval width as an SICR (IFRS9 staging) signal.
4. **No prior work** wires CatBoost → calibration → Mondrian CP → Pyomo robust LP
   as a single auditable pipeline.
5. **No prior work** treats SPO+ as an *auditability* comparator rather than a
   regret baseline (CRPTO trades minimal regret for distribution-free coverage).
6. Credit grades are naturally disjoint → Mondrian (not Kandinsky) is the right
   conditioning tool.

## Editorial agenda implied by the recent CP+RO frontier

| Recent line | Paper(s) | How CRPTO positions it |
|---|---|---|
| Decision-aware conformal model selection | CROMS (`bao2025croms`) | Future work: select the conformal family by robust return / `V` / `Γ_CP` / violation, not coverage alone |
| End-to-end conformal calibration | `yeh2026`, `yeh2025training` | Acknowledge CRPTO calibrates post-hoc; future: a conformal score trained by the portfolio loss |
| OCE / CVaR tail control | `yeh2025training`, `rockafellar2000cvar`, `bental2007oce` | Implemented as **Appendix A22** (tail-constrained re-optimization); body keeps Markov/`V` |
| Multi-distribution robust coverage | `yang2026multidistribution` | **Appendix A23**: coverage robustness without observing the test group |
| Online / non-stationary recalibration | `capitaine2026online`, `liu2026portfolio`, `gibbs2021aci`, `angelopoulos2025gradient` | **Appendix A24**: online/ACI sequential recalibration diagnostic |
| Robust satisficing | `zhao2025robust` | Related work + future fragility/satisficing metric beside `Γ_CP` |

## Bound positioning (audit conclusion)

- The theorem controls a **bounded target** `Y_i ∈ [0,1]` and the **weighted
  miscoverage** `V = Σ_i w_i · 1{Y_i > u_i}`.
- The reading of `Y_i` as a latent PD is flagged as an **additional assumption**,
  not an observable.
- The policy must be read as **fixed before** observing the evaluated labels; the
  276k evaluation is **post-selection empirical validation**, not a stronger
  conformal guarantee.
- **Markov** is the principal distribution-free result; **Hoeffding/Bernstein**
  remain a conditional tightening under additional independence/structure
  assumptions, not a replacement.
- Open journal question: formalize whether the conformal wrapper should cover
  observed default, latent PD, expected loss, or a calibrated risk score. The
  validation code compares `y_true`/`default_flag` against `pd_high`, so the text
  must not claim more than that without a separate lemma.
