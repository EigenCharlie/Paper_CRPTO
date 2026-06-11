# CRPTO Claim Audit Matrix

This matrix is the pre-submission reviewer-defense layer. It maps each visible
claim to evidence, artifact provenance, and the boundary that prevents
overclaiming.

| Claim | Body location | Evidence/artifact | Reviewer risk | Boundary language |
|---|---|---|---|---|
| CRPTO is a data-science decision method, not a classifier leaderboard. | Abstract, Introduction, Related Work. | Pipeline Figure 1, exact certificate table, funded-set audit. | Desk screen reads it as applied ML. | State the central object as an auditable conformal-robust decision certificate. |
| The predictive input is frozen and calibrated. | Method, Results. | `models/pd_canonical.cbm`, `models/pd_canonical_calibrator.pkl`, Table 0 metrics. | Reviewer asks whether results depend on hidden retraining. | PD artifact is consumed, not re-searched, by paper renders. |
| The conformal layer is conservative on OOT data. | Method, Results, Supplement A23-A24. | `conformal_intervals_mondrian.parquet`, coverage metrics, group audits. | Reviewer expects conditional coverage. | Claim marginal/Mondrian coverage; stronger local/multi-distribution claims are future work. |
| The 90% intervals are useful despite large raw width. | Method, funded-set audit, Table 7. | Average width `0.7842`, Winkler `1.1107`, funded-set mean upper endpoint A-B `0.12529` vs E-G `0.52587`, `Gamma_CP=0.187987`. | Reviewer says intervals are too wide on the `[0,1]` PD scale. | Width is not promoted as a standalone utility metric; the decision layer uses relative upper endpoints, Winkler, funded-set miscoverage, and the conformal premium. |
| The promoted Lending Club policy passes the alpha01 funded-set audit. | Results. | `V=0.028875`, `Gamma_CP=0.187987`, zero violation. | "Exact" may be misunderstood as universal validity. | Exact means direct accounting on frozen funded-set outputs (Theorem 1(i)); statistical interpretation uses weighted funded-set validity, stated as Assumption 1 with full proof in Supplement Appendix A. |
| The result is not a single lucky point. | Results, Supplement A18/A20. | `45/45` alpha-safe robust region, heatmap, champion JSON. | Reviewer asks whether one selected policy was cherry-picked. | The 45 policies are the final evaluated robust region, not all 276k candidates. |
| Prosper/Freddie show transfer of the recipe. | Results, Supplement A25-A34. | External replication gate, candidate sensitivity, all-candidate LP exhaustiveness. | Reviewer reads them as new champion certificates. | They are frozen external economic replications and exhaustiveness audits only. |
| The price of robustness is economically interpretable. | Results, Discussion. | Lending Club price `-10.56%`; external premiums `+1.00%` to `+9.46%`. | Sign convention or selected-vs-blind confusion. | Lending Club is selected; external panels are blind frozen applications. |
| SPO+ is a comparator, not a replacement champion. | Robustness and Comparators. | A19/Fig. 15 committed regret-auditability artifact. | Reviewer says CRPTO has higher regret. | SPO+ optimizes synthetic regret; CRPTO emits funded-set risk controls. |
| Tail-risk alternatives exist. | Tail Risk section, Supplement A20-A22. | CVaR/OCE and tail-constrained challenger tables. | Reviewer asks why not select lowest-tail policy. | Champion maximizes return inside alpha-safe region; tail policies are documented trade-offs. |
| Fairness/MRM claims are limited. | Supplement Appendix D, Discussion. | Proxy/intersectional diagnostics and MRM scope. | Reviewer asks for statutory fair-lending proof. | Public data lack direct protected attributes; no legal certification claim. |
| The paper is reproducible. | Reproducibility section, Supplement E, submission docs. | `just smoke`, `just validate-champion`, DVC metadata, lockfile, manifest. | Reviewer asks how to reproduce without secrets. | Raw-data instructions and DVC pointers are disclosed after anonymity/acceptance rules. |
| The certificate chain is exactly recomputable from frozen artifacts. | Reproducibility section (body and tex), Supplement E. | Drift harness `tests/test_models/test_conformal_mapie_drift.py` (zero max abs diff per loan and per Mondrian cell, identical re-learned floor multipliers); `scripts/rebuild_test_predictions_from_frozen.py` hard-asserts score/interval identity. | Reviewer reads "reproducible" as including GBM retraining. | The verified property is prediction-to-decision: frozen PD binaries through conformal intervals to the certificate, under the locked dependency stack. Gradient-boosted retraining is not bit-reproducible, which is why the predictive layer ships as a hash-verified frozen binary. |

## Reviewer Objection Bank

| Objection | Short response |
|---|---|
| "CP + RO already exists." | CRPTO instantiates the bridge for frozen credit PD artifacts, funded-set economics, exact audit, and reproducible governance. |
| "Adaptive selection breaks conformal validity." | Correct concern, and exactly why the paper isolates it: Assumption 1 states weighted funded-set validity explicitly, Theorem 1 separates the deterministic identity from the Markov step, and the exact audit checks the selected frozen funded set after the fact. |
| "This is one dataset." | Lending Club carries the certificate; Prosper/Freddie test transfer of the recipe without claiming new certificates. |
| "The AUC is not high enough." | The paper is not a credit-scoring leaderboard; calibrated probabilities are inputs to an auditable decision. |
| "The intervals are too wide to use." | Raw width is expected on a binary PD-scale interval; the paper evaluates whether upper endpoints rank downside risk and produce a funded set that passes Winkler, funded-set miscoverage, and exact alpha-safe checks. |
| "SPO+ has lower regret." | Correct; the paper reports a frontier where SPO+ buys regret and CRPTO buys verifiable risk controls. |
| "Why not live validation?" | Lending Club retail originations ended in 2020; prospective live validation is future protocol, not hidden current evidence. |
