# CRPTO conformal-literature corpus audit

## Status, scope, and evidentiary boundary

This audit records the literature-intake state as of 2026-07-21. It covers the
complete local corpus under `Papers_tesis`, the fifteen-paper frontier intake,
and the separately supplied book *Applied Conformal Prediction*. Its purpose is
to decide what the active IJDS manuscript may cite, what ideas are technically
applicable, and what material must remain future work or be excluded.

This document is not an active claim registry and does not activate a numerical
or policy claim. The claim registry, source registry, and paper-facing evidence
manifest remain the authorities for the manuscript. A paper being present in
the corpus also does not certify its correctness or applicability to CRPTO.

The audit reached three central conclusions:

1. CRPTO's direct binary score and split-conformal rank are standard, but their
   marginal guarantee must remain conditional on the relevant score
   exchangeability. A realized finite-archive shortfall is not, by itself, a
   theorem violation.
2. Direct label-Mondrian calibration is the appropriate binary benchmark for
   the observed label-coverage asymmetry. It must use a separate frozen cutoff
   for each candidate label, and it does not identify label-conditional
   validity for unresolved candidates without additional assumptions.
3. Neither candidate-level marginal coverage nor label-Mondrian calibration
   automatically survives portfolio selection. Selection-conditional, FCR,
   online-shift, covariate-shift, censoring, and action-conditional methods each
   require assumptions or data structures that are absent from the active
   design.

## Corpus inventory and provenance

The inventory checksum for `Papers_tesis` is **112 PDFs and 4,412 pages**.
Derived manuscript PDFs are not included in this count.

| Intake layer | PDFs | Pages | Composition |
|---|---:|---:|---|
| Existing corpus | 97 | 3,855 | 28 `paper`, 57 `supplement`, and 12 `tesis` objects |
| Frontier intake | 15 | 557 | `Papers_tesis/supplement/p01.pdf` through `p15.pdf` |
| Total | 112 | 4,412 | Complete local literature corpus |

The existing 97-document corpus spans six connected literatures:

- split, conditional, localized, weighted, and non-exchangeable conformal
  inference;
- conformal risk control, valid selection, and prediction-set efficiency;
- robust, distributionally robust, contextual, and predict-then-optimize
  decision methods;
- P2P lending, credit scoring, default/prepayment modelling, and portfolio
  construction;
- calibration, class imbalance, label noise, cost-sensitive learning, and
  model controls; and
- credit equity, explainability, regulation, and the distinction between
  observational and causal decision claims.

This breadth is sufficient for CRPTO's current conceptual interfaces. The
frontier intake was therefore targeted rather than indiscriminate: classwise
coverage, temporal non-exchangeability, selection after conformalization,
partially observed outcomes, and decision-dependent coverage.

The book is outside `Papers_tesis` and is not included in the 112/4,412
checksum:

- source: `C:\Users\carlos\Downloads\Applied_Conformal_Prediction (3).pdf`;
- extent: 168 pages;
- SHA-256:
  `5340A494E689427264A8E67389F11AD332569A19E5CB0E9205198016DD9D506F`;
- durable assessment:
  `docs/research/applied_conformal_prediction_book_audit_2026-07-21.md`.

## Extraction and quality-assurance method

### Existing 97-document corpus

All 3,855 pages were processed with page-delimited `pypdf` layout extraction.
The run produced 13,532,623 text characters and a structured dossier for every
PDF containing its opening, abstract, conclusion or discussion, tail,
reference preview, and page-linked theorem/table/coverage/portfolio evidence.
The durable scratch objects are:

- `.tmp_pdf_intake_benchmark/literature_audit_2026-07-21/dossiers.json`;
- `.tmp_pdf_intake_benchmark/literature_audit_2026-07-21/inventory.jsonl`; and
- `.tmp_pdf_intake_benchmark/literature_audit_2026-07-21/pypdf_layout/`.

The page-yield audit found 103 text-empty pages across four documents and 136
pages below 100 extracted characters across ten documents. Three PDFs had no
usable text layer at all: Bertsimas--Kallus (57 pages), Hand--Henley (20
pages), and Hoeffding (25 pages). They were rerouted through MinerU hybrid as
`bk`, `hh`, and `hoeffding`; the fallback recovered the titles, substantive
body text, and mathematical statements. The 570-page robust-optimization book
had one empty and 20 low-yield pages, mostly front matter or display-heavy
pages, while its remaining extraction was usable. Low-yield pages in other
objects were treated as visual-QA targets rather than silently discarded.

The automated dossier pass makes the whole corpus searchable and auditable; it
does not mean that every equation in all 97 objects was independently
re-proved. Manual review was concentrated on claims, formulas, tables, and
figures that could alter the active manuscript.

### Fifteen-paper frontier intake

All fifteen PDFs had strong born-digital text layers and were routed to
Docling with OCR disabled. Every run succeeded. The combined outputs contain:

- 1,693,113 Markdown bytes and 29,609,698 JSON bytes;
- 560 headings;
- 1,487 formula markers;
- 1,933 Markdown table lines;
- 163 image markers; and
- 38,692 bounding-box markers.

The extraction records are:

- `.tmp_pdf_intake_benchmark/f/inventory.jsonl` for identity, extent, and
  checksums;
- `.tmp_pdf_intake_benchmark/x/runs.jsonl` and `scores.jsonl` for parser QA;
  and
- `.tmp_pdf_intake_benchmark/x/docling/` for Markdown, JSON, page images, and
  extracted assets.

Each frontier verdict used the full extracted text, with targeted checks of
the title page, theorem assumptions, defining equations, empirical tables,
appendices, limitations, and conclusion. Material sign, quantile-direction,
or denominator concerns were checked against the PDF rather than inferred
from Markdown alone.

Docling occasionally loses a negation glyph in mathematical text, rendering
`!=`/`\neq` as equality. Those instances are extraction defects, not paper
errors. No adverse paper verdict below is based solely on a dropped glyph.
Conversely, the p08 label-definition conflict, p09 weighting substitution,
p14 order-statistic inconsistency, and p15 tail/optimization problems remain
after contextual or visual verification.

### Book intake

The 168-page book was routed to MinerU hybrid because of its length and dense
mix of formulas, tables, code, and figures. Poppler/PDF metadata and targeted
page-image checks supplemented the extraction. It is a secondary pedagogical
source only. The book is useful for the binary hinge identity, the marginal
versus conditional distinction, and empty/singleton/full set geometry, but it
contains enough rank, proof, calibration, Venn, and Mondrian overstatements
that it must not serve as authority for CRPTO's validity claims. Primary papers
should be cited instead.

## Evidence grades

| Grade | Meaning | Frontier objects |
|---|---|---|
| A: cite and use for a stated boundary | Primary result is relevant and its assumptions can be stated without implying that CRPTO already implements the method | p01, p03, p04, p05, p07 |
| B: retain for a predeclared future extension | Technically informative, but its estimand, data structure, or assumptions do not match the active design | p02, p06, p10, p11, p12, p13, p14 |
| C: do not use as methodological support | The supplied version contains a material internal inconsistency or empirical contradiction that prevents safe reliance | p08, p09, p15 |

Grade A does not mean wholesale adoption. In particular, p03 and p05 explain
why selected-set guarantees require a new method; p04 and p07 explain possible
shift-aware alternatives; none retroactively gives the active portfolios a
selected-set or non-exchangeable coverage certificate.

## Paper-by-paper frontier audit

### p01 — Ding et al., *Class-Conditional Conformal Prediction with Many Classes*

**Object.** NeurIPS 2023, 22 pages. The paper distinguishes marginal coverage
from class-conditional coverage and proposes clustered conformal prediction to
pool classes with similar score distributions when fully classwise calibration
would be data-starved.

**Technical assessment.** The relevant baseline is CLASSWISE/Mondrian
calibration: for candidate label `y`, membership is determined with the cutoff
estimated from calibration examples whose true label is `y`. The clustered
method learns a class partition on independent data and then provides formal
cluster-conditional coverage; approximate per-class conclusions require the
paper's score-distribution similarity conditions. Pooling is an efficiency
device, not an automatic route to exact coverage for every original class.

**CRPTO decision.** **Cite and adopt the classwise principle, not the clustered
algorithm.** CRPTO is binary and its frozen cells have enough observations for
direct label-specific cutoffs. This paper supports the distinction between
marginal and label-conditional coverage and the construction
`y in C(x)` using the cutoff belonging to candidate label `y`. It does not
justify treating coverage on the resolved subset as all-candidate
label-conditional validity, and it does not repair temporal transport.

### p02 — Ding, Fermanian, and Salmon, *Conformal Prediction for Long-Tailed Classification*

**Object.** arXiv:2507.06867v3, 32 pages. It studies the coverage--set size
trade-off across thousands of highly imbalanced classes, introduces a
prevalence-adjusted score, and considers interpolation between standard and
classwise conformal thresholds.

**Technical assessment.** The work is unusually explicit about its limits.
Its threshold-interpolation result gives a weaker marginal bound (the displayed
proposition is at least `1-2 alpha`), and choosing the interpolation parameter
to hit a calibration-set size target is acknowledged to violate the symmetry
needed for the clean theorem unless it is reconformalized on an independent
split. The many-class macro-coverage objective and human search-effort examples
do not map directly to a binary endpoint.

**CRPTO decision.** **Retain as future work; do not cite for the current binary
benchmark.** Prevalence-aware or interpolated cutoffs would introduce an extra
tuning/selection layer and a different estimand. The direct two-label
Mondrian benchmark is simpler and better aligned with the current audit.

### p03 — Gazin et al., *Selecting Informative Conformal Prediction Sets with False Coverage Rate Control*

**Object.** JRSS B 2025, 50-page downloaded version. The paper develops InfoSP
and InfoSCOP for reporting only informative conformal sets while controlling
the expected false coverage proportion among selected cases.

**Technical assessment.** The FCR result is not a free consequence of vanilla
conformal coverage. It combines conformal p-values with a BH-type selection
rule and requires an independently trained score, no-tie/regularity
conditions, a monotone informative-set collection, and either the stated iid
model or its class-conditional model. InfoSCOP pays an additional sample split
to make preliminary selection compatible with calibration.

**CRPTO decision.** **Cite as the primary selected-set boundary.** It directly
supports the statement that discarding ambiguous sets or acting only on
singletons changes the target error criterion and requires multiplicity-aware
selection control. CRPTO does not implement InfoSP/InfoSCOP and must not claim
FCR or funded-set coverage. A future selected-loan procedure would need a new
locked protocol, a compatible selection rule, and fully observed evaluation
labels.

### p04 — Gibbs and Candès, *Conformal Inference for Online Prediction with Arbitrary Distribution Shifts*

**Object.** JMLR 2024, 36 pages. The dynamically tuned ACI procedure adapts
online to changing error processes and controls local interval regret through
an expert/online-convex-optimization construction.

**Technical assessment.** The method addresses a genuinely different data
structure from a frozen split-conformal evaluation. Its update uses sequential
feedback after each prediction, and its local/long-run guarantees are not the
same as the ordinary one-shot marginal split-conformal guarantee. Hyperparameter
choices trade local responsiveness against long-run behavior.

**CRPTO decision.** **Cite as a shift-aware alternative, not as a repair.** The
36-month credit endpoint and administrative label delay prevent the immediate
feedback loop assumed by online ACI. A delayed-feedback implementation would
need a new sequential estimand and protocol. The paper helps explain why a
frozen 2011 calibration cannot simply be called adaptive.

### p05 — Jin and Ren, *Confidence on the Focal: Conformal Prediction with Selection-Conditional Coverage*

**Object.** JRSS B 2025, 48-page downloaded version. JOMI constructs a
selection-specific reference set of calibration observations that remain
exchangeable with a focal test unit conditional on the selection event.

**Technical assessment.** JOMI is relevant to top-k, optimization-based,
conformal-p-value, and preliminary-set selection. Its exact conditional result
depends on the original exchangeability structure and on a selection rule
that is permutation-invariant in the calibration observations. It is not a
generic post-hoc correction for any optimized portfolio, and the reference set
must be derived for the exact selection mechanism.

**CRPTO decision.** **Cite as the second primary selected-set boundary.** It
supports the warning that candidate-level validity does not imply validity for
loans selected by an optimizer. It is a plausible future architecture only
after defining the funded-set selection event, proving the required symmetry,
and resolving the temporal exchangeability and missing-endpoint problems.

### p06 — Liu, de Paula, and Tamer, *Prediction Sets and Conformal Inference with Interval Outcomes*

**Object.** 2026 working-paper version, 48 pages. It partially identifies
minimum-volume oracle prediction sets when the latent continuous outcome is
observed only through an interval `[Y_L,Y_U]`, then conformalizes a score built
from the interval observation.

**Technical assessment.** The paper carefully separates partial identification
of the oracle set, consistency of the estimated oracle object, and finite-sample
marginal validity under iid sampling. It also gives partition-local variants.
Those are valuable distinctions, but its observation model is not CRPTO's:
an administratively unresolved binary endpoint is missing, not a continuously
valued outcome observed within an informative censoring bracket.

**CRPTO decision.** **Retain as a partial-identification analogue.** It should
not be cited as proof for CRPTO's sharp binary completion bounds or as a
selected-set guarantee. A future integration would have to define the binary
set-valued observation `{0}`, `{1}`, or `{0,1}` as the estimand from the start
and prove that the availability mechanism matches the proposed score and
sampling assumptions.

### p07 — Oliveira et al., *Split Conformal Prediction and Non-Exchangeable Data*

**Object.** JMLR 2024, 38 pages. The paper derives explicit coverage penalties
for ordinary split conformal under concentration and decoupling conditions,
including stationary beta-mixing and certain nonstationary processes.

**Technical assessment.** This paper prevents an overly simple dichotomy:
failure of exact exchangeability does not imply that split conformal has no
possible theorem. The replacement guarantee, however, contains dependence or
drift penalties whose assumptions and magnitudes must be established. The
empirical examples do not make those penalties automatically small in a new
archive.

**CRPTO decision.** **Cite in the non-exchangeability discussion.** The current
rank-reference audit concerns the stronger null that each calibration stratum
and its entire target block are jointly exchangeable. It does not test the
usual one-future-point marginal condition, estimate beta-mixing coefficients,
decoupling errors, or a nonstationary discrepancy bound. Its 31/40 locked
nominal threshold flags also carry no post-selection FWER guarantee because the
family and pattern were inspected before the lock. Therefore p07 cannot restore
a 90% guarantee to the active cells. It identifies a strong future route: predeclare a temporal
dependence model and report the resulting penalty rather than asserting
robustness from empirical recurrence alone.

### p08 — Peng and Lessmann, *Incorporating Data Drift to Perform Survival Analysis on Credit Risk*

**Object.** arXiv:2601.20533v1, 27 pages. It proposes landmark-style joint
survival modelling with isotonic calibration under simulated credit drift.

**Adversarial findings.** The supplied version is not safe support for CRPTO:

- the target is coded as `CurLoanDel != 0`, but later prose interprets
  `P(CurLoanDel=0)` as default, reversing the event semantics;
- simulated label flips are independent of covariates and do not establish
  robustness to realistic conditional drift;
- grouped random cross-validation mixes regimes and weakens the temporal
  generalization claim;
- the isotonic split is not enough to cure leakage or mixed-regime validation;
- F1/AUC patterns are consistent with a positive-class orientation problem;
- the appendix reports Cox Brier scores of 0.052/0.075 versus LMISO
  0.188/0.194, contradicting the broad superiority language; and
- the mortgage design omits prepayment as a competing risk.

**CRPTO decision.** **Do not cite or adopt.** The paper may remain in the
quarantine corpus as an example of why endpoint definitions, class
orientation, temporal splitting, calibration isolation, and competing risks
must be audited together.

### p09 — Sesia and Svetnik, *Conformal Survival Bands for Risk Screening under Right-Censoring*

**Object.** arXiv:2505.04568v4, 52 pages. It combines inverse-probability of
censoring weighting, conformal p-values, and FDR-controlled risk screening.

**Adversarial findings.** The theorem mapping in the supplied version has a
material reciprocal inconsistency. The paper defines the censoring weight as
`w=1/S_C`, but maps its generic `D/E` theorem using `E=hat w`. That substitution
produces `D/hat w = D*S_C`, whereas IPCW requires `D*hat w = D/S_C`. The mapping
would instead need `E=1/hat w`; the accompanying positivity orientation would
also have to be rewritten consistently. This is a proof-to-estimator problem,
not a Markdown loss of `\neq`.

**CRPTO decision.** **Do not cite as support unless a corrected version or
erratum resolves the mapping.** The topic is highly relevant, but relevance
cannot substitute for a valid bridge between the generic theorem and the
implemented IPCW p-value.

### p10 — Solomon et al., *Selecting Informative Conformal Prediction Sets with an Optimized FCR-Controlled Approach*

**Object.** arXiv:2605.22004v1, 41 pages. It develops an oracle-guided
informative-set policy, a resolution-adjusted power objective, and a calibrated
OGInfoSP procedure intended to improve power while retaining FCR control.

**Technical assessment.** The work is a meaningful refinement of p03. Its
optimality argument depends on conditional membership probabilities and
regularity/nestedness conditions; the finite-sample procedure then needs a
calibration construction that keeps estimation separate from final error
control. The authors explicitly describe some probability-estimation steps as
plug-in heuristics rather than guaranteed improvements.

**CRPTO decision.** **Retain for future selected-loan design.** It is premature
for the active paper because CRPTO does not optimize which prediction sets to
report and has not defined FCR as the funded-set estimand. It should follow,
not precede, a defensible selection-conditional protocol.

### p11 — Wang and Qiao, *Conformal Prediction under Generalized Covariate Shift with Posterior Drift*

**Object.** AISTATS 2025, 15 pages. The method combines source and target data
with class-specific weights under generalized covariate shift with posterior
drift (CSPD/g-CSPD), aiming at target-domain set coverage and efficiency.

**Technical assessment.** The formal result requires classwise absolute
continuity, the CSPD structure, and controlled or consistently estimated
weights. The asymptotic efficiency result adds estimation and margin
conditions. These are substantive restrictions; “posterior drift” is not an
assumption-free label for any temporal deterioration.

**CRPTO decision.** **Retain as a future weighted-transfer option.** CRPTO has
not established CSPD, classwise density ratios, or bounded weights between
2011 and later origins. The paper cannot be invoked to convert observed shift
diagnostics into a target-domain guarantee.

### p12 — Zecchin et al., *Generalization and Informativeness of Weighted Conformal Risk Control under Covariate Shift*

**Object.** ISIT 2025/arXiv:2501.11413, 9 pages. It relates W-CRC set size to
base-predictor generalization, calibration/training allocation, and the degree
of covariate shift.

**Technical assessment.** W-CRC assumes covariate shift: the conditional law
of the outcome given covariates remains fixed while the covariate marginal
changes, and importance weights connect the source and target populations.
Its efficiency bound also uses bounded monotone loss and generalization
conditions. The phrase “under covariate shift” is therefore doing essential
work.

**CRPTO decision.** **Retain for future work only.** The active evidence shows
temporal score/residual transport problems and does not establish invariant
`P(Y|X)` or defensible density ratios. W-CRC would be a new method and guarantee,
not a sensitivity label for the current unweighted procedure.

### p13 — Zheng and Jin, *Prediction Sets for Counterfactual Decisions: Coverage, Optimality, and Conformal Prediction*

**Object.** arXiv:2607.02206v1, 42 pages. It introduces policy-coupled coverage
for potential outcomes, connects prediction sets to a max-min decision rule,
and derives a conformal procedure for action-dependent realized outcomes.

**Technical assessment.** The contribution addresses the case in which the
action changes which potential outcome is observed. Its optimality and
coverage objects are explicitly coupled to the induced policy and require a
counterfactual/potential-outcome model. That is more than downstream
optimization of predictions in an observational archive.

**CRPTO decision.** **Retain as a future causal-decision extension; do not use
to support the active paper.** CRPTO estimates observed historical terminal
outcomes and does not identify counterfactual repayment under alternative
funding actions. Citing p13 as current support would blur the paper's explicit
noncausal boundary.

### p14 — Zhou et al., *Audited Conformal Prediction for Classification under Unknown Distribution Shift*

**Object.** arXiv:2606.14909v1, 59 pages. ACP trains an auxiliary model on a
target-population split to predict when a legacy classifier will fail, then
uses that audit score for marginal or group-oriented conformal calibration.

**Adversarial findings.** The general architecture is relevant, but the
supplied version is not ready for active adoption:

- the main split-conformal description correctly uses the k-th smallest score
  and includes `+infinity`, while Appendix A1/A2 says k-th largest and omits
  the infinite atom;
- the adaptive AACP evaluation uses resubstitution and a dependent t-test in a
  way that does not support a clean confirmatory comparison; and
- performance of the learned audit group depends on target-label quality and
  sample splitting, so empirical conditional improvement is not an
  assumption-free conditional-coverage theorem.

**CRPTO decision.** **Keep only as a nested future experiment.** A frozen audit
model trained on an earlier, outcome-isolated target split could be studied
under a new protocol. It should not replace the simpler label-Mondrian
diagnostic, and the current version should not be cited as authority for the
rank rule.

### p15 — Zhu et al., *Conformal Risk-Averse Decision Making with Action Conditional Guarantee*

**Object.** arXiv:2606.05551v2, 38 pages. The paper proposes action-conditional
prediction sets and a risk-averse decision rule calibrated through an
optimization over action-specific multipliers.

**Adversarial findings.** The supplied version contains several linked issues:

- Equation 14 uses the wrong tail orientation for the stated utility set;
- the empirical objective `F_y` changes with the induced action, so the claimed
  convexity/Lipschitz argument is not established as written;
- the KKT treatment omits relevant boundary cases;
- the constant experimental step sizes conflict with the convergence
  conditions later imposed on the sequence of step sizes;
- reported action-conditional coverage falls below nominal in parts of the
  empirical evaluation; and
- the medical utility construction is generated by ChatGPT rather than a
  validated domain elicitation.

**CRPTO decision.** **Do not cite or adopt.** Action-conditional validity would
in any event require a different action/outcome design than the historical
loan archive. The internal theory--algorithm--experiment inconsistencies make
the current version unsuitable even as indirect methodological support.

## Book disposition

The book's durable audit should be read together with this corpus record. Its
correct and useful pieces are:

- `s(x,y)=1-p_hat_y(x)` and, for binary `y`, the identity
  `1-p_hat_y(x)=|y-p|`;
- the ascending rank index `ceil((n+1)(1-alpha))`, subject to the infinite
  cutoff when the index is `n+1`;
- the distinction between marginal, group-conditional, and feature-conditional
  coverage; and
- the geometry of empty, singleton, and two-label binary sets.

Its material defects include calling the ascending order statistic the k-th
largest, using identical marginals where exchangeable ranks are needed,
treating one realized empirical coverage as mandatory, conflating conformal
sets with calibrated probabilities, overstating Venn/Venn--Abers guarantees,
presenting 50--100 observations as a Mondrian validity threshold, and treating
all data-driven groups as invalid. CRPTO should use the book for orientation
only and cite the primary papers above for formal statements.

## Gaps that remain after the frontier intake

The corpus is broad, but five gaps remain material to the next research cycle:

1. **Correct, mature conformal inference for delayed or right-censored binary
   endpoints.** The downloaded p09 version cannot fill this role. Candès, Lei,
   and Ren's *Conformalized Survival Analysis* is a primary starting point, but
   its estimand and censoring assumptions still need to be compared carefully
   with CRPTO's administrative 36-month label availability.
2. **A predeclared dependence model for batch temporal loan panels.** p07 gives
   a framework, but CRPTO has not estimated the mixing/discrepancy objects that
   would turn it into a numerical coverage penalty.
3. **Selection-conditional coverage for the exact portfolio optimizer with
   missing endpoints.** JOMI and FCR methods cover parts of this problem, not
   their combination with sharp completion bounds and capital constraints.
4. **A defensible source-to-target weighting model.** The corpus contains
   covariate-shift and posterior-drift methods, but the active archive has not
   established their invariance, overlap, or weight-boundedness assumptions.
5. **External credit-domain validation of binary conformal sets under label
   delay and competing prepayment.** Existing credit papers rarely combine a
   locked temporal split, explicit outcome availability, classwise set
   geometry, and downstream portfolio selection.

These are research gaps, not novelty claims. A targeted search should prefer
peer-reviewed primary sources and corrected versions, then subject every new
candidate to the same theorem-to-code and endpoint audit used here.

## Recommended incorporation map

| Manuscript surface | Add or retain | Do not infer |
|---|---|---|
| Related work: class-conditional coverage | Cite `ding2023`; distinguish direct CLASSWISE/Mondrian calibration from clustered many-class pooling | That resolved-label diagnostics are all-candidate class-conditional validity |
| Related work: temporal shift | Cite `gibbs2024online` and `oliveira2024split` as two different replacement frameworks | That either applies without online feedback or a quantified dependence/drift penalty |
| Related work and limitations: selection | Cite `jin2025focal` and `gazin2025informative` | Funded-set, singleton-selected, JOMI, or FCR coverage for the active portfolios |
| Method: binary label benchmark | Define candidate-label membership with a separate frozen cutoff for `y=0` and `y=1`; report cell sizes and exact ranks | A symmetric latent-PD confidence interval or a post hoc selected-set claim |
| Identification and theory | Separate deterministic all-candidate completion bounds, the stronger joint-block rank reference, and deterministic design sensitivities | That either a sharp upper bound below 0.90 or the block diagnostic refutes the usual marginal split-conformal guarantee |
| Results | Report finite-archive set geometry and label-Mondrian comparisons descriptively; report 31/40 cells as meeting locked nominal Bonferroni--Holm thresholds for the joint-block reference | Rejection/significance language, post-selection or study-wide FWER, causal source of drift, prospective guarantee, or universal learner winner |
| Discussion/future work | Mention delayed-feedback ACI, quantified non-exchangeable penalties, JOMI/FCR selection, interval/censoring methods, and weighted shift as distinct protocols | That naming a method repairs the present archive |
| References | Use the five verified primary records added in this audit | Cite p08, p09, or p15 as methodological support |

## Bibliographic changes made by this audit

`paper/references.bib` already contained the correct NeurIPS record under
`ding2023`; its URL was changed from the arXiv abstract to the official NeurIPS
proceedings page. Four nonduplicative primary records were added:

- `gibbs2024online` — JMLR 25(162), 1--36;
- `oliveira2024split` — JMLR 25(225), 1--38;
- `jin2025focal` — JRSS B 87(4), 1239--1259, DOI qkaf016; and
- `gazin2025informative` — JRSS B 87(4), 909--929, DOI qkae120.

No bibliographic entry was added for a quarantined paper or for a future-work
paper that the active manuscript does not need to cite.

## Frontier object checksum table

| ID | Pages | SHA-1 | Short title | Grade |
|---|---:|---|---|---|
| p01 | 22 | `4a96baed6959ee6716f1861798baa05d43261fd2` | Class-Conditional CP with Many Classes | A |
| p02 | 32 | `c244cbdab64b87660cf2fa71ccb9586d9de1022e` | CP for Long-Tailed Classification | B |
| p03 | 50 | `41cb64e779e654e193a6f10ceff53ee8ced5a75b` | Informative Sets with FCR Control | A |
| p04 | 36 | `2a2547f278bf3bccb239f23c22936104c7650c2d` | Online CP under Arbitrary Shifts | A |
| p05 | 48 | `a638d4a08193fccb300273a69d070f2dceb12a0f` | Confidence on the Focal / JOMI | A |
| p06 | 48 | `6ef59060c5e3c5681a705e6ffae6208442570718` | Prediction Sets with Interval Outcomes | B |
| p07 | 38 | `1324ac3be476cec3269d3ed2e7b18f272d95a5e5` | Split CP and Non-Exchangeable Data | A |
| p08 | 27 | `c92acf07323d280fe4f037fcf3746701a5462c2e` | Credit Survival under Data Drift | C |
| p09 | 52 | `c3c422ec79fa7725ac6572a221cb183f9ccb7293` | Conformal Survival Bands | C |
| p10 | 41 | `0475c2cacbe4f5d5004ca56fbf8db0c3960abc7b` | Optimized FCR-Controlled Informative Sets | B |
| p11 | 15 | `3449bfdecb26031ff65d92aca446c1817c6eb200` | CP under Posterior Drift | B |
| p12 | 9 | `0b383f459cc23b6918a79f803842d93b7fb32177` | Weighted CRC under Covariate Shift | B |
| p13 | 42 | `3ef439babb94f96388951daaea407494e3dbe8b5` | Prediction Sets for Counterfactual Decisions | B |
| p14 | 59 | `78170dc19ec1b4ed7e38c42aecc968f93f0c5842` | Audited Conformal Prediction | B |
| p15 | 38 | `21c1c1b5111bd7f0d807bd15f95e3ecca9ab3fab` | Action-Conditional Risk-Averse CP | C |
