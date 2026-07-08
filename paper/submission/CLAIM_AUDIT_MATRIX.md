# CRPTO Claim Audit Matrix

This matrix is the pre-submission reviewer-defense layer. It maps each visible
claim to evidence, artifact provenance, and the boundary that prevents
overclaiming.

| Claim | Body location | Evidence/artifact | Reviewer risk | Boundary language |
|---|---|---|---|---|
| CRPTO is a data-science decision method, not a classifier leaderboard. | Abstract, Introduction, Related Work. | Pipeline Figure 1, exact certificate table, funded-set audit. | Desk screen reads it as applied ML. | State the central object as an auditable conformal-robust decision certificate. |
| The predictive input is frozen and calibrated. | Method, Results, Supplement Appendix E. | `models/pd_canonical.cbm`, `models/pd_canonical_calibrator.pkl`, Table 0 metrics, E3/E4 PD stability diagnostics. | Reviewer asks whether results depend on hidden retraining. | PD artifact is consumed, not re-searched, by paper renders; E3/E4 are non-promoted T1 diagnostics, not a new champion. |
| The conformal layer is conservative on OOT data. | Method, Results, Supplement A23-A24. | `conformal_intervals_mondrian.parquet`, coverage metrics, group audits. | Reviewer expects conditional coverage. | Claim marginal/Mondrian coverage; stronger local/multi-distribution claims are future work. |
| The 90% intervals are useful despite large raw width. | Method, funded-set audit, Tables A35-A39. | Average width `0.7842`, Winkler `1.1107`, and pool93 body-point `Gamma_CP=0.162616` after allocation; A37--A39 profile tail risk, concentration, and fixed-allocation bootstrap uncertainty from the selected allocation. | Reviewer says intervals are too wide on the `[0,1]` PD scale. | Width is not promoted as a standalone utility metric; the decision layer uses upper-endpoint ordering, funded-set miscoverage, and the conformal premium inside an exact portfolio frontier. |
| The promoted Lending Club body point passes the alpha-grid funded-set audit. | Results, Supplement A35-A39. | Body point: return `$184,832.48`, `V=0.035350`, `Gamma_CP=0.162616`, Markov cap `0.345084`, zero violation, `8/8` alpha pass; A36 shows funded exposure by grade; A37 reports baseline LGD tail repricing; A38 shows cluster bounds remain looser than Markov; A39 reports fixed-allocation bootstrap return interval `$167,963.20`--`$198,650.47`. | "Exact" may be misunderstood as universal validity. | Exact means direct accounting on frozen funded-set outputs (Theorem 1(i)); statistical interpretation uses weighted funded-set validity, stated as Assumption 1 with full proof in Supplement Appendix A. A39 is an empirical fixed-allocation interval, not a conformal guarantee. |
| The result is not a single lucky point. | Results, Supplement A35. | Consolidated pool93 frontier: `50,010` deduplicated semantic policies, `27,508` eligible all-alpha above-floor policies; terminal endpoint search: `37,068/37,068` all-alpha passers. | Reviewer asks whether one selected policy was cherry-picked. | The frontier is a declared finite policy-grid surface, not all possible continuous policy values and not a future-selection guarantee. |
| Prosper/Freddie show transfer of the recipe. | Results, Supplement A25-A34. | External replication gate, candidate sensitivity, all-candidate LP exhaustiveness. | Reviewer reads them as new champion certificates. | They are frozen external economic replications and exhaustiveness audits only. |
| The price of robustness is economically interpretable. | Results, Discussion. | Lending Club price `-10.56%`; external premiums `+1.00%` to `+9.46%`, ordered by panel default rate across the four frozen external applications. | Sign convention, selected-vs-blind confusion, or over-reading as a statistical scaling law. | Lending Club is selected; external panels are blind frozen applications; describe the pattern as ordered in these applications, not as a general law. |
| SPO+ is a comparator, not a replacement champion. | Robustness and Comparators. | A19/Fig. 15 committed regret-auditability artifact. | Reviewer says CRPTO has higher regret. | SPO+ optimizes synthetic regret; CRPTO emits funded-set risk controls. |
| Tail-risk alternatives exist and the selected point has been repriced. | Tail Risk section, Supplement A20-A22 and A37-A39. | CVaR/OCE and tail-constrained challenger tables; pool93 body repricing has baseline LGD return `$184,832.48`, realized CVaR95 `0.276211`, decision-time CVaR95 `0.218140`, no cluster-bound threshold tighter than Markov, and fixed-allocation bootstrap diagnostics. | Reviewer asks why not select lowest-tail policy. | The body selector is the finite-grid return-bound point; tail-risk/bootstrap tables are documented trade-offs and selected-point diagnostics, not hidden promotion criteria. |
| Fairness/MRM claims are limited. | Supplement Appendix D, Discussion. | Proxy/intersectional diagnostics and MRM scope. | Reviewer asks for statutory fair-lending proof. | Public data lack direct protected attributes; no legal certification claim. |
| The paper is reproducible. | Body design paragraph, Supplement E, submission docs. | `just smoke`, `just validate-champion`, DVC metadata, lockfile, manifest. | Reviewer asks how to reproduce without secrets. | Raw-data instructions and DVC pointers are disclosed through the accepted-paper package or an editor-approved review bundle. |
| The certificate chain is exactly recomputable from frozen artifacts. | Body design paragraph in the official `.tex`, Supplement E, submission docs. | Drift harness `tests/test_models/test_conformal_mapie_drift.py` (zero max abs diff per loan and per Mondrian cell, identical re-learned floor multipliers); `scripts/rebuild_test_predictions_from_frozen.py` hard-asserts score/interval identity. | Reviewer reads "reproducible" as including GBM retraining. | The verified property is prediction-to-decision: frozen PD binaries through conformal intervals to the certificate, under the locked dependency stack. Gradient-boosted retraining is not bit-reproducible, which is why the predictive layer ships as a hash-verified frozen binary; E3/E4 support this choice without becoming routine reruns. |

## Reviewer Objection Bank

| Objection | Short response |
|---|---|
| "CP + RO already exists." | CRPTO instantiates the bridge for frozen credit PD artifacts, funded-set economics, exact audit, and reproducible governance. |
| "CP + RO is a direct combination, not a theory contribution." | The paper's theory is intentionally modest: Theorem 1 separates deterministic funded-set accounting from the Markov step under weighted funded-set validity. The contribution is the decision-certificate bridge: frozen PD artifact -> conformal endpoint -> robust funded set -> exact post-decision audit with reproducible governance. |
| "Adaptive selection breaks conformal validity." | Correct concern, and exactly why the paper isolates it: Assumption 1 states weighted funded-set validity explicitly, Theorem 1 separates the deterministic identity from the Markov step, and the exact audit checks the selected frozen funded set after the fact. |
| "This is one dataset." | Lending Club carries the certificate; Prosper/Freddie test transfer of the recipe without claiming new certificates. |
| "The AUC is not high enough." | The paper is not a credit-scoring leaderboard; calibrated probabilities are inputs to an auditable decision. |
| "Why distribute a binary instead of asking readers to retrain?" | The certified object is the frozen prediction-to-decision chain. E3/E4 show seed and temporal PD diagnostics are stable enough to support the binary choice, while the exact artifact hashes keep the submitted certificate fixed. |
| "The intervals are too wide to use." | Raw width is expected on a binary PD-scale interval; the paper evaluates whether upper endpoints rank downside risk and produce a funded set that passes Winkler, funded-set miscoverage, and exact alpha-safe checks. |
| "SPO+ has lower regret." | Correct; the paper reports a frontier where SPO+ buys regret and CRPTO buys verifiable risk controls; the pool93 frontier updates the funding certificate, not the SPO+ regret experiment. |
| "Why not live validation?" | Lending Club retail originations ended in 2020; prospective live validation is future protocol, not hidden current evidence. |

## Response-Ready Reviewer Paragraphs

**Why not SPO+ as the main method?** SPO+ is the right comparator for
training-time decision regret, and the manuscript reports that comparison
directly. The point of CRPTO is different: it asks what can be certified after a
calibrated PD model is frozen and the decision layer must remain auditable. On
the A19 regret scale SPO+ owns the low-regret corner; CRPTO owns the funded-set
risk-control corner with a dollar-valued allocation, conformal premium,
finite-grid denominator, and exact post-allocation audit.

**Why not CVaR/OCE as the selector?** CVaR and OCE are useful tail-risk
diagnostics, but making either one the promoted selector would define a new
objective and require a new predeclared search/audit protocol. The current
submission deliberately promotes the finite-grid return-bound point and then
reprices that selected allocation under LGD, CVaR, OCE, cluster, and bootstrap
stress checks. This keeps tail risk visible without turning a diagnostic table
into a hidden promotion criterion.

**Is the selected point cherry-picked?** The selected policy is not a singleton
chosen after looking at one lucky allocation. It sits on a declared finite-grid
frontier: 50,010 deduplicated semantic policies are reported, 27,508 both pass
all declared alpha levels and exceed the return floor, and the terminal endpoint
search completes 296,544 exact policy-alpha checks. The body/default point and
the strict `<=0.345` neighboring point are separated explicitly to avoid
rounding-based overclaiming.

**What happens under dependence?** The body theorem uses the weakest
distribution-free Markov step under the stated weighted funded-set validity
assumption and does not require loan-level independence. The supplement prices
stronger assumptions through cluster-aware sensitivity tables; those rows show
what a reviewer would gain by accepting additional structure, but none becomes
the body guarantee. Dependence therefore appears as an assumption boundary, not
as an unstated theorem condition.

**Is this a live-production guarantee?** No. Lending Club retail originations
ended in 2020, and the manuscript is explicit that the evidence is a frozen
historical decision certificate, not a prospective control system. The
contribution is reproducible prediction-to-decision governance on the available
out-of-time panel; online conformal control, prospective validation, and live
monitoring are future protocols.

**What can be reproduced under double-anonymous review?** During anonymous
review, the manuscript and supplement describe the companion package without
author-identifying repository URLs. The reproducible object is the
prediction-to-decision chain from frozen PD artifacts and conformal intervals to
tables, figures, exact checks, and manifest validation. Protected searches and
retraining are intentionally excluded from routine reproduction because they
would change the submitted certificate rather than verify it.
