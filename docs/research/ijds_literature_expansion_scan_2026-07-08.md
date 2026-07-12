# IJDS literature expansion scan, 2026-07-08

## Scope

This note records an external and local literature scan for the IJDS version of
CRPTO. It is designed as an editorial input, not as a request to reopen the
frozen champion. Its original pool93 framing is historical; the active paper
contract is `docs/research/active_claims_2026-07-11.md`.

Operational guardrails:

- Do not modify `EXTRACTION_MANIFEST.json` or artifacts listed there.
- Do not rerun protected champion stages without explicit permission.
- Keep the IJDS body focused on the implemented certificate: finite alpha grid,
  robust funding decision, exact violation audit, and economic return.
- Use the supplement for adjacent method families, diagnostics, and future work.

Sources reviewed:

- Local corpus: `Papers_tesis` inventory and benchmark snapshot
  `.tmp_pdf_intake_benchmark/run_20260707_ijds_lit_analysis/snapshot.md`.
- Current bibliography: `book/references.bib`.
- Current manuscript anchors: `book/chapters/CRPTO_*.qmd`, `paper/submission`,
  and the active claims register.
- External web scan on conformal decision-making, contextual optimization,
  credit scoring uncertainty, IJDS-adjacent work, and 2025-2026 emerging papers.

## Bottom line

The paper already cites the core CRPTO neighborhood well: conformal risk control,
predict-then-calibrate, conformal contextual robust optimization, conformal
robustness control, conformal robust optimization/satisficing, end-to-end
conformal calibration, and credit/P2P decision papers. The most useful additions
are not dozens of new citations. The highest-value improvement is a small set of
strategic anchors that sharpen the IJDS story:

1. Add one broad contextual optimization survey to show that CRPTO sits inside
   the modern prediction-to-decision literature.
2. Add one credit-specific profit/uncertainty paper to show that economic credit
   scoring is active, but CRPTO advances from score-level economics to a funded
   portfolio decision certificate.
3. Add one non-exchangeability/source-shift conformal reference in the
   supplement.
4. Add one post-selection or human-decision conformal limitation reference to
   make the paper look honest and current.
5. Keep 2026 inverse/decision-calibrated and decision-aware conformal-set papers
   as future-work comparators, not body-level foundations, unless reviewers ask.

## Recommended additions

### 1. Sadana et al. 2025, contextual optimization survey

Candidate:

- Rahul Sadana, Andrea Delage, Alexandre Forel, Emma Frejinger, Thibaut Vidal.
  "A survey of contextual optimization methods for decision-making under
  uncertainty." European Journal of Operational Research, 320(2), 2025.
- Sources: [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0377221724002200),
  [arXiv](https://arxiv.org/abs/2306.10374).

Why it matters:

- It is an OR-facing survey of contextual optimization, prescriptive analytics,
  predict-then-optimize, decision-focused learning, and smart predict/estimate-
  then-optimize methods.
- It gives IJDS reviewers a clean map for why CRPTO is a decision paper rather
  than a classifier leaderboard.

Recommended placement:

- Body, related work or positioning paragraph.
- One sentence is enough: CRPTO belongs to contextual/predictive-prescriptive
  optimization, but differs by producing an auditable finite-grid robust funding
  certificate rather than learning a new end-to-end policy.

Priority: High.

### 2. Xu, Kou, and Ergu 2025, profit-based uncertainty in credit scoring

Candidate:

- Zhuozhuo Xu, Gang Kou, Daji Ergu. "Profit-based uncertainty estimation with
  application to credit scoring." European Journal of Operational Research,
  325(2), 2025.
- Sources: [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0377221725002048),
  [IDEAS/RePEc](https://ideas.repec.org/a/eee/ejores/v325y2025i2p303-316.html).

Why it matters:

- It is close to our application domain and explicitly links credit scoring,
  uncertainty, rejection, and profitability.
- It supports the narrative that predictive uncertainty in lending should be
  evaluated economically, while CRPTO moves the unit of decision from
  application-level classification/rejection to portfolio funding under a
  distribution-free certificate.

Recommended placement:

- Body if there is space in the credit/P2P paragraph.
- Otherwise supplement literature table.

Priority: High.

### 3. Xu et al. 2024, profit- and risk-driven credit scoring

Candidate:

- Zhuozhuo Xu, Yishun Dou, Gang Kou, Daji Ergu. "Profit- and risk-driven credit
  scoring under parameter uncertainty: A multiobjective approach." Omega, 125,
  2024.
- Source: [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0305048323001688).

Why it matters:

- It gives a credit-scoring reference for profit/risk tradeoffs under uncertain
  cost-benefit parameters.
- It is useful if we want a short supplement note distinguishing CRPTO from
  multiobjective credit-score design: CRPTO certifies a portfolio decision over
  existing predictions and realized returns rather than optimizing an application
  classifier under assumed parameter uncertainty.

Recommended placement:

- Supplement, not body, unless reviewers ask for more credit-scoring economics.

Priority: Medium.

### 4. Farinhas et al. 2024, non-exchangeable conformal risk control

Candidate:

- Antonio Farinhas, Alessandro Zecchin, Andre Martins, David Grangier.
  "Non-Exchangeable Conformal Risk Control." ICLR 2024.
- Source: [arXiv](https://arxiv.org/abs/2310.01262).
- Local PDF already exists in `Papers_tesis/supplement`.

Why it matters:

- It directly addresses a limitation readers may raise: calibration/test
  exchangeability, time dependence, and distribution shift.
- It can strengthen the supplement language around source-shift diagnostics
  without making a new guarantee in the IJDS body.

Recommended placement:

- Supplement A23/A24 source-shift and calibration-drift discussion.
- Do not cite it as implemented protection unless we implement and validate the
  method.

Priority: High for supplement, low for body.

### 5. Hegazy et al. 2025, valid selection among conformal sets

Candidate:

- Mahmoud Hegazy, Emma Frejinger, Pierre Pinson, Alexandre Forel.
  "Valid Selection among Conformal Sets." 2025.
- Source: [arXiv](https://arxiv.org/abs/2506.20173).

Why it matters:

- It is conceptually important for CRPTO because our grid search selects among
  candidate decisions and alpha values after evaluating constraints.
- The current paper is careful because it reports finite-grid denominators,
  exact violation audit, and does not claim a new post-selection conformal
  theorem. This paper helps articulate that boundary.

Recommended placement:

- Supplement limitations/future protocol.
- Possible sentence: future CRPTO variants could study formal post-selection
  validity for choosing among multiple calibrated sets, whereas the present
  paper reports a finite-grid certificate and exact audit for the selected
  champion.

Priority: High for limitations.

### 6. Hullman et al. 2025, conformal prediction and human decision making

Candidate:

- Jessica Hullman, Christopher W. Zamecnik, Yuval Rabin, Fred Hohman.
  "Conformal Prediction and Human Decision Making." 2025.
- Source: [arXiv](https://arxiv.org/abs/2503.11709).

Why it matters:

- It argues that valid conformal sets are not automatically useful for decisions
  unless the downstream objective is explicit.
- This is useful for IJDS framing: CRPTO is not "uncertainty reporting"; it
  operationalizes uncertainty through a robust funding decision and economic
  audit.

Recommended placement:

- Optional short citation in introduction or limitations.
- Use sparingly; avoid turning the paper into a human-factors discussion.

Priority: Medium.

### 7. Djeundje, Crook, and Andreeva 2025, dynamic loan portfolio profitability

Candidate:

- Viani B. Djeundje, Jonathan Crook, Galina Andreeva. "The devil in the details:
  Dynamic prediction of loan portfolio profitability with macroeconomic drivers
  through multi-state modelling." European Journal of Operational Research,
  327(2), 2025.
- Sources: [IDEAS/RePEc](https://ideas.repec.org/a/eee/ejores/v327y2025i2p703-715.html),
  [University of Edinburgh](https://www.research.ed.ac.uk/en/publications/the-devil-in-the-details-dynamic-prediction-of-loan-portfolio-pro/).

Why it matters:

- It is a recent credit-portfolio profitability paper rather than a pure
  application-level classifier paper.
- It can help if a reviewer wants more credit portfolio literature around
  dynamic profitability and macroeconomic drivers.

Recommended placement:

- Supplement only, unless the introduction is rewritten to emphasize
  macro-sensitive portfolio profitability.
- Do not use it to imply that CRPTO currently models macro transitions; it does
  not.

Priority: Medium-low.

## Emerging close comparators to monitor

These papers are close to CRPTO but are very recent, mostly preprint-era, or in
different domains. They should strengthen future-work positioning rather than
drive the IJDS body.

### Zhou and Zhu 2026, inverse conformal risk control for decision robustness

- "Calibrating Decision Robustness via Inverse Conformal Risk Control."
- Sources: [arXiv](https://arxiv.org/abs/2510.07750),
  [OpenReview](https://openreview.net/forum?id=lV4tqcVIyx&referrer=%5Bthe+profile+of+Shixiang+Zhu%5D%28%2Fprofile%3Fid%3D~Shixiang_Zhu1%29).
- Value: Very close to CRPTO because it treats the robustness level itself as
  the calibrated object and reports finite-sample guarantees on miscoverage and
  regret for robust predict-then-optimize policy families.
- Recommendation: strongest 2026 future-work comparator. It is too new to make
  it a foundation of the current body, but it is the cleanest citation if we add
  one sentence about future calibration of robustness levels.

### Stratigakos et al. 2026, decision-calibrated prediction sets

- "Decision-calibrated prediction sets for robust power system operations."
- Source: [arXiv](https://arxiv.org/abs/2606.02081).
- Value: Closest phrase-level comparator for calibrating prediction sets by
  downstream decision reliability.
- Recommendation: future-work comparator only.

### Chen, Zhou, and Zhu 2026, learning polyhedral conformal sets for RO

- "Learning Polyhedral Conformal Sets for Robust Optimization."
- Source: [arXiv](https://arxiv.org/abs/2605.08506).
- Value: Decision-aware conformal uncertainty sets for robust optimization.
- Recommendation: cite in future work if adding a paragraph on learned
  uncertainty-set geometry.

### Wang and Dobriban 2026, optimal decisions from prediction sets

- "Optimal Decision-Making Based on Prediction Sets."
- Source: [arXiv](https://arxiv.org/abs/2602.00989).
- Value: Decision-theoretic framework for downstream use of prediction sets.
- Recommendation: monitor; useful if reviewers ask for more theory around
  prediction sets as decision objects.

### Huang, Farzaneh, and Simeone 2026, OCE risk-controlling prediction sets

- "Optimized Certainty Equivalent Risk-Controlling Prediction Sets."
- Source: [arXiv](https://arxiv.org/abs/2602.13660).
- Value: OCE/CVaR-style risk-control extension.
- Recommendation: supplement/future work near the existing OCE/CVaR diagnostics.

### Baesens et al. 2026, foundation models for credit risk prediction

- "Foundation Models for Credit Risk Prediction: A Game Changer?"
- Source: [arXiv](https://arxiv.org/abs/2605.18147).
- Value: Useful for monitoring PD-layer baselines in credit risk.
- Recommendation: do not add to IJDS body now. CRPTO does not claim a PD model
  leaderboard.

## Already-covered nearest neighbors

The current corpus and official submission already include the most important
methodological neighbors. These should remain the core comparison set:

- Patel et al. 2024, conformal contextual robust optimization.
- Sun et al. 2024, predict-then-calibrate.
- Hu et al. 2026, conformal robustness control.
- Zhao et al. 2025/2026, conformal robust optimization and satisficing.
- Yeh et al. 2025/2026, conformal risk training and end-to-end conformal
  calibration.
- Bao et al. 2025, CROMS.
- Zhou et al. 2025/2026, CREDO and CREME.
- Yang and Bi 2025, cost-aware calibration.
- Liu et al. 2026, online conformal portfolio selection.
- Yang and Jin 2026, multidistribution conformal prediction.

The key editorial move is to distinguish CRPTO from each in one sentence:

- Not a new PD scorer.
- Not a generic conformal-set method.
- Not end-to-end training.
- Not online rebalancing.
- Not a multidistribution fairness theorem.
- A finite-grid robust portfolio decision certificate with realized-return and
  exact-violation audit.

## IJDS-specific venue scan

Relevant IJDS-adjacent sources are useful mainly for framing, not for core
method positioning:

- Wiberg et al. 2025, "Synergizing Artificial Intelligence and Operations
  Research." IJDS. Source:
  [INFORMS](https://pubsonline.informs.org/doi/10.1287/ijds.2025.0077).
- Morucci et al. 2022, "A Robust Approach to Quantifying Uncertainty in Matching
  Problems of Causal Inference." IJDS. Source:
  [INFORMS](https://pubsonline.informs.org/doi/10.1287/ijds.2022.0020).
- "Rethinking Cost-Sensitive Classification in Deep Learning via Adversarial
  Data Augmentation." IJDS. Source:
  [INFORMS](https://pubsonline.informs.org/doi/10.1287/ijds.2022.0033).

Recommendation:

- Do not overload the paper with IJDS self-citations.
- If a cover letter or response-to-reviewers needs venue fit, Wiberg et al.
  2025 is a concise AI+OR anchor.
- Morucci et al. 2022 can be mentioned only if a reviewer asks about robust
  uncertainty quantification precedent in IJDS.
- The cost-sensitive classification IJDS paper is less aligned than Yang and Bi
  2025 for our current framing.

## Recent credit-risk papers to leave out unless needed

The 2025-2026 EJOR credit-risk stream is active. Several papers are useful for
background but should not crowd the IJDS body:

- Distaso, Roccazzella, and Vrins 2025, "Business cycle and realized losses in
  the consumer credit industry." Source:
  [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0377221724009688).
- Ballegeer, Bogaert, and Benoit 2025, "Evaluating the stability of model
  explanations in instance-dependent cost-sensitive credit scoring." Source:
  [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0377221725004230).
- Baesens et al. 2026, foundation models for credit risk prediction. Source:
  [arXiv](https://arxiv.org/html/2605.18147v1).

Recommendation:

- Use these only if a reviewer asks for macro-credit loss, explanation
  stability, or modern PD-model background.
- They do not change the CRPTO contribution because the paper is not proposing a
  new PD learner.

## Exact manuscript insertion plan

Keep the body lean. The highest-value body additions are two citations:

1. Add Sadana et al. 2025 to the contextual optimization / prescriptive
   analytics positioning.
2. Add Xu, Kou, and Ergu 2025 to the credit scoring uncertainty / profit
   paragraph.

Then use the supplement for three limitation/future-work citations:

3. Farinhas et al. 2024 in source-shift/non-exchangeability.
4. Hegazy et al. 2025 in post-selection validity.
5. Zhou and Zhu 2026 as the preferred emerging future-work comparator; if space
   allows, add one of Stratigakos et al. 2026, Chen et al. 2026, or Wang and
   Dobriban 2026 for decision-calibrated conformal-set geometry/use.

Suggested body language:

> CRPTO sits within contextual optimization and prescriptive analytics, where
> predictions and downstream decisions are optimized jointly or sequentially,
> but it differs by auditing a finite grid of robust funding decisions rather
> than training a new decision rule.

> Recent credit-scoring work evaluates uncertainty through profit and rejection
> decisions; CRPTO instead evaluates uncertainty at the funded-portfolio level,
> where the reported object is an economically realized decision certificate.

Suggested supplement language:

> The present certificate assumes the calibration/audit design documented in
> the finite-grid protocol. Extensions to non-exchangeable conformal risk control
> and formal selection among multiple conformal sets are natural next steps, but
> are not claimed by the current champion.

## Bibliography action list

Add or verify BibTeX entries for:

- `sadana2025contextual`
- `xu2025profit_uncertainty_credit`
- `xu2024profit_risk_credit`
- `farinhas2024nonexchangeable_crc`
- `hegazy2025valid_selection_conformal_sets`
- `hullman2025conformal_human_decision`
- `djeundje2025dynamic_loan_portfolio_profitability`
- `zhou2026inverse_crc_decision_robustness`
- `stratigakos2026decision_calibrated_sets`
- `chen2026polyhedral_conformal_ro`
- `wang2026optimal_decision_prediction_sets`
- `huang2026oce_rcps`
- `baesens2026foundation_credit_risk`

Before adding all of them, apply a manuscript budget rule:

- Body: at most two new citations unless a paragraph is rewritten.
- Supplement: three to six citations are acceptable.
- Future-work table: emerging 2026 papers are acceptable if clearly labeled as
  future work and not as implemented guarantees.

## Citation synchronization note

The official submission `.tex` currently contains several compact citation
anchors that are not all mirrored in the source `.qmd` files. Examples observed
during this scan include:

- `angelopoulos2024foundations`
- `bates2021rcps`
- `zhou2024`
- `sun2024ptc`
- `boosting2025default`
- `yeh2025training`

If the paper is regenerated from Quarto, these anchors could be lost unless the
QMD sources are synchronized. The safest path is to update QMD first, regenerate
official submission artifacts, and then re-run the IJDS compile checks.

## Do-not-add list for the current IJDS submission

Do not add broad or weakly related references unless a reviewer asks:

- Generic LLM/tabular-model credit-risk papers that do not affect the CRPTO
  certificate.
- Generic conformal prediction surveys beyond the already cited foundations.
- Extra IJDS venue papers solely for journal signaling.
- Additional classifier benchmarking papers unless they directly affect the
  LendingClub decision framing.

## Decision recommendation

For the current IJDS revision, implement the following compact literature
upgrade:

1. Add Sadana et al. 2025 and Xu, Kou, and Ergu 2025 to the body.
2. Add Farinhas et al. 2024 and Hegazy et al. 2025 to the supplement.
3. Add one 2026 emerging decision-calibrated conformal reference to future work.
4. Keep all language explicit that these are positioning and future-work
   references; they do not change the frozen champion or its claims.

This gives reviewers the right signals: the paper is current, aware of adjacent
decision-calibrated conformal work, and still disciplined about what it actually
implements and certifies.

## Post-read implementation note, 2026-07-08

After the missing PDFs were downloaded manually to `Downloads`, they were copied
into `Papers_tesis/supplement` with normalized names:

- `Xu Kou Ergu 2025 - Profit-based uncertainty estimation with application to credit scoring.pdf`
- `Xu et al 2024 - Profit- and risk-driven credit scoring under parameter uncertainty.pdf`
- `Djeundje Crook Andreeva 2025 - Dynamic prediction of loan portfolio profitability.pdf`
- `Wiberg Dai Lam Kulkarni 2025 - Synergizing AI and OR.pdf`

The expanded `academic-pdf-intake` inventory now sees 100 PDFs in scope:
97 under `Papers_tesis` and the three active CRPTO PDFs. The post-read
manuscript update keeps the body claim unchanged and implements only narrative
and boundary changes:

- Body: CRPTO is framed as a contextual-optimization credit instance, anchored
  by credit-scoring uncertainty/profit literature and the AI/OR IJDS perspective.
- Theory: post-selection conformal validity is named explicitly as future
  protocol, not as an implicit property of the finite-grid frontier.
- Supplement: non-exchangeable CRC, valid selected conformal sets,
  decision-calibrated/inverse conformal robustness, learned polyhedral sets,
  OCE-RCPS, and recent credit-profitability/explanation-stability papers are
  mapped to diagnostics or future-work boundaries.

No frozen champion artifact, manifest entry, or protected DVC stage is changed
by this literature update.

## Venue recheck, 2026-07-09

The current [IJDS submission guidelines](https://pubsonline.informs.org/page/ijds/submission-guidelines)
still require the Data + Models + Decisions + Implications synthesis and now
state an explicit abstract sequence: problem/data-science relevance, method and
results, then learned insight and implication. The CRPTO abstract already
covered the first two elements but ended by repeating pipeline architecture.
Its closing sentences now state the learned decision insight and committee use:
the return-bound frontier makes predictive uncertainty actionable, while the
certificate separates exact funded-set accounting from its weighted-validity
assumption.

Two recent accepted IJDS papers provide a useful style check rather than new
citation requirements:

- [Robust and Interpretable Policy Learning for Manufacturing Process Parameters](https://pubsonline.informs.org/doi/10.1287/ijds.2024.0041)
  leads from a concrete decision problem to a named policy method, robustness,
  interpretability and practical deployment evidence.
- [Using Operational Data Analytics for Planning Decisions Under Uncertainty](https://pubsonline.informs.org/doi/10.1287/ijds.2024.0051)
  makes the estimate-then-optimize gap explicit, compares against several
  decision baselines and closes with real-data effectiveness.

CRPTO already follows those structural signals through the funded-set decision,
the exact certificate, the A19 regret comparator and the managerial implication.
No additional venue self-citation is warranted: the existing Das et al. IJDS
credit-risk anchor and Wiberg et al. AI/OR anchor are sufficient, and adding
more would crowd the body without changing the novelty boundary.
