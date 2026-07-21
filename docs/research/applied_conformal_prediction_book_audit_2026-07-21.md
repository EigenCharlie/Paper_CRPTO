# Technical audit of *Applied Conformal Prediction*

## Audit object and status

- Source: Valery Manokhin, *Applied Conformal Prediction: Reliable Uncertainty
  Quantification for Real-World Machine Learning*, author-published, copyright
  2025 / first printing 2026.
- Local object: `C:\Users\carlos\Downloads\Applied_Conformal_Prediction (3).pdf`.
- SHA-256: `5340A494E689427264A8E67389F11AD332569A19E5CB0E9205198016DD9D506F`.
- Size and extent: 9,079,908 bytes; 168 PDF pages; five substantive chapters.
- Intake: MinerU hybrid extraction with layout PDF and image assets, supplemented
  by Poppler/PDF metadata inspection and targeted visual checks against the PDF.
  The extraction contains 5,596 Markdown lines, 34 image markers, 24 table
  occurrences, 35 figure-caption/reference occurrences, and 372 display-math
  delimiters. The last count includes continued displays and code-derived
  expressions, so the mathematical audit below is organized by distinct
  mathematical object rather than by delimiter.
- Evidentiary status: secondary pedagogical source only. It is useful for
  vocabulary, examples, and implementation intuition, but it is not sufficiently
  precise to serve as the paper's authority for validity, conditional coverage,
  Venn prediction, or selection-after-conformalization claims. CRPTO should cite
  the relevant primary papers instead.

## Bottom line

The book gets the core construction that CRPTO uses mostly right: a fixed
classifier can be wrapped with the classification score
`s(x,y)=1-p_hat_y(x)`; for binary labels this equals `|y-p|`; split conformal
uses the order statistic indexed by `ceil((n+1)(1-alpha))`; and the guarantee is
marginal rather than pointwise conditional. Its discussion of empty,
singleton, and two-label sets is also useful for interpreting CRPTO's binary
geometry.

It nevertheless contains several material errors and overstatements:

1. It twice describes the conformal cutoff as the *k-th largest* score even
   though its own notation orders scores increasingly. It must be the k-th
   smallest score (or `+infinity` when the requested index is `n+1`).
2. One classification proof infers a uniform rank from identical marginal
   distributions. Identical distributions are insufficient; joint
   exchangeability of the scores is the key step.
3. It treats empirical coverage on one test set as if it must be at least the
   target. The standard theorem is marginal over the calibration sample and a
   new test observation. Realized finite-archive coverage can be below target
   under the null.
4. It repeatedly presents ordinary conformal classification as a way to turn
   scores into calibrated point probabilities. Standard split conformal makes
   prediction sets; Venn/Venn-Abers methods are separate probabilistic
   constructions.
5. It claims probability calibration itself repairs subgroup or conditional
   coverage, and attributes an "any subset" guarantee to Venn-Abers. Neither
   claim follows from ordinary calibration or Venn validity.
6. It states 50--100 observations per Mondrian group as though this were a
   validity threshold. It is an efficiency/resolution heuristic, not a minimum
   sample size for the finite-sample theorem.
7. It says data-driven Mondrian groups necessarily destroy exactness. A group
   map learned on independent training data and then frozen can preserve the
   needed calibration/test symmetry. Post hoc outcome-guided groups are the
   problematic case.
8. Several synthetic figures are described as confirming a theorem. A single
   empirical curve or run can illustrate, but cannot establish, marginal
   validity.

These points directly motivate two additions to CRPTO: an exact
Beta--Binomial reference test that distinguishes realized shortfall from
evidence against transport/exchangeability, and a complete label-Mondrian
benchmark rather than interpreting resolved-label coverage as if it were
class-conditional conformal validity.

## Audit of the mathematical objects

| Object | Book treatment | Technical verdict | CRPTO implication |
|---|---|---|---|
| Exchangeability | Defines invariance of the joint law to permutations and distinguishes it from i.i.d. | Correct. Some prose later weakens the argument incorrectly to equal marginals. | State exchangeability for calibration and evaluation scores conditional on the earlier fitted model and frozen group map. |
| Split score | Uses `s(x,y)=1-p_hat_y(x)` for classification. | Correct for the hinge/probability-complement score. It need not be a calibrated probability. | Exactly equals CRPTO's `|y-p|` for binary `y`. |
| Split rank | Uses `k=ceil((n+1)(1-alpha))`. | Correct when `k<=n`; otherwise use an infinite cutoff/full set. The prose calling it k-th largest is wrong. | Existing CRPTO groups are large and reconcile the k-th *ascending* order statistic. Keep an explicit assertion. |
| Marginal coverage | States `P{Y_new in C(X_new)} >= 1-alpha`. | Correct under score exchangeability and the stated inclusive tie rule. It is not a statement about every realized OOT panel. | Replace categorical "coverage failure" language with finite-archive shortfall plus a separate inferential test. |
| Conditional-on-calibration coverage | Mentioned informally as finite-sample fluctuation. | Needs the explicit law. Under an i.i.d.-continuous model, `F(S_(k)) ~ Beta(k,n+1-k)`. More generally, joint continuity and exchangeability give the same Beta--Binomial target miss-count law directly by uniform combined-rank allocation. | Use this reference to test whether the observed minimum miss count is compatible with the null. |
| Ties | Says inclusive ties are conservative and randomized ties can be exact. | First clause is right. Exact `1-alpha` generally also needs randomization calibrated to the unattainable fractional rank, not merely an unspecified tie break. | CRPTO uses inclusive sets; discrete score ties make the continuous Beta--Binomial reference conservative. |
| Proof by ranks | One proof uses exchangeability; another uses only identical distribution. | The exchangeability proof is the valid one. Equal marginals do not imply a uniform rank under dependence. | The manuscript should use only the permutation/rank argument. |
| Binary interval embedding | Presents thresholded probability scores and binary label sets. | The direct label set is conformal. A continuous interval around `p` is a design embedding, not a confidence interval for latent PD. | CRPTO already makes this distinction correctly and should retain it. |
| Set efficiency | Uses average cardinality and singleton rate. | Correct but incomplete if empty and full sets are hidden by an average. | CRPTO improves on the book by reporting empty and `{0,1}` shares separately. |
| Marginal versus conditional coverage | Explains the impossibility of unrestricted exact conditional coverage. | Broadly correct, but the book later implies ordinary calibration closes the gap. | Keep marginal, predefined-group, selected-set, and pointwise-conditional estimands distinct. |
| Mondrian coverage | Calibrates separately within predefined groups/classes. | Correct if the partition rule is fixed independently of calibration/test outcomes and each cell uses its own exact rank. | The score-stratum design is a valid Mondrian framework under transport; add label as a second Mondrian dimension for the benchmark. |
| Group sample size | Recommends 50--100 or 100 observations per group. | Practical heuristic only. Validity has no such minimum; small cells give coarse/conservative sets and low power. | Report every cell size and rank rather than impose an invented validity cutoff. |
| Data-driven groups | Warns against all data-driven groups. | Too broad. Independently learned and frozen group maps can be valid; adaptively choosing groups using calibration/test outcomes needs separate control. | CRPTO's 2011 score edges are outcome-free with respect to later residual/evaluation labels and are frozen before use. |
| Label-Mondrian sets | Describes class-conditional calibration. | Correct principle. Prediction must use the threshold belonging to each candidate label, not an interval threshold shared across labels. | Implement direct membership `y in S(x)` using `c_(g,y)`; do not force it into the symmetric continuous embedding. |
| APS | Uses cumulative probability mass and randomization. | Broad construction is correct. Randomization removes score ties but the ordinary ceiling rank still gives `k/(n+1)`, not universally exact `1-alpha`. | APS/RAPS add little in binary CRPTO and are not needed for the primary audit. |
| RAPS/SAPS | Presents regularized/adaptive multiclass scores. | Relevant mainly to multiclass efficiency; claims of universal superiority are empirical, not theorem-level. | Out of scope for a binary endpoint. |
| Regression residual CP | Gives symmetric residual intervals. | Correct under split assumptions; constant width ignores heteroscedasticity. | Not CRPTO's estimand. Do not import regression-interval language into binary PD. |
| CQR | Gives the standard max-residual conformalization. | Broadly correct, but one-run coverage plots cannot prove validity. | Not a reason to replace the binary observed-outcome set with a latent-PD interval. |
| Jackknife+/cross-conformal | Summarizes alternatives. | Useful overview, but exact guarantees differ by method and should be checked in primary sources. | They would change the frozen design and do not target temporal shift by themselves. |
| Probability calibration | Defines Brier/log-loss/reliability concepts. | These assess probabilistic forecasts, not conformal set validity. Calibration can improve or worsen set efficiency depending on the score and model. | Keep Platt diagnostics separate from conformal coverage and from portfolio performance. |
| Venn/Venn-Abers | Describes multiprobability outputs and isotonic taxonomies. | It is a distinct probabilistic-prediction framework. Validity does not mean calibrated for every arbitrary selected subset, nor universally best. | Do not relabel CRPTO's split sets as calibrated point probabilities. Venn-Abers is optional future work, not a repair for temporal transport. |
| Selection after CP | Only partially distinguishes set validity from downstream selection. | Candidate-level validity does not automatically survive data-dependent selection or allocation. | CRPTO's explicit no-funded-set-guarantee boundary is essential; use JOMI/FCR/action-conditional literature for future extensions. |
| Distribution shift | Notes that exchangeability can fail and mentions weighting/online methods. | Correct direction, but every repair adds assumptions or changes the guarantee. | Weighting is at most a diagnostic without a defensible density-ratio model; online ACI is not justified by this delayed-label archive. |

## Chapter-by-chapter assessment

### Chapter 1: introduction and history

The motivation for uncertainty sets and the calibration-versus-sharpness
distinction is useful. The chapter is much less reliable as history or
comparative methodology. It draws a long intellectual line from von Mises,
Solomonoff, Kolmogorov, and Chaitin to conformal prediction without showing
that these are necessary technical antecedents for the split-conformal result.
It also presents Bayesian, bootstrap, ensemble, and quantile approaches as
mostly assumption-bound foils. Those comparisons omit well-specified cases in
which the alternatives have valid inferential interpretations and should not
be cited as a balanced literature review.

The chapter's repeated "guaranteed confidence" wording needs three qualifiers:
the outcome/set estimand must be named, the relevant observations/scores must
be exchangeable or covered by a replacement theorem, and the guarantee is
marginal unless a stronger method is used. CRPTO already names observed
terminal binary `Y` and should keep doing so.

### Chapter 2: classification foundations

This is the strongest and most relevant chapter. The exchangeability
definition, the binary hinge construction, the separation of validity and
efficiency, and the marginal/conditional distinction are sound. The central
rank formula is also the one CRPTO implements.

The defects are consequential rather than cosmetic. The cutoff is called the
k-th largest in two locations although `S_(1)<=...<=S_(n)` is used. The theorem
does not handle `k=n+1`. The ties note promises exact nominal coverage too
loosely. Most importantly, the worked proof must rely on the exchangeable
rank, not merely on equal score distributions. The chapter also understates
the randomness of realized coverage conditional on one calibration sample.

### Chapter 3: conformal classification

The score catalogue is useful. In binary classification, the margin score is
a positive-affine transform of the hinge score, so it induces the same ranks
and sets when handled consistently. APS/RAPS/SAPS matter mainly when many
classes create a meaningful ranking/cumulative-mass problem.

The chapter's main conceptual error is to recast ordinary CP as a probability
calibrator for tabular classification. A collection of conformal p-values or
membership decisions is not automatically a vector of calibrated class
probabilities. Statements that the main purpose of tabular CP is to make
trusted probabilities should be removed or explicitly attributed to Venn,
conformal predictive systems, or another defined probabilistic method.

### Chapter 4: regression

The residual, normalized-residual, Mondrian-regression, CQR, and Jackknife+
sections provide useful comparative intuition. They do not justify treating
CRPTO's clipped interval around a default score as a regression prediction
interval or a confidence interval for individual PD. CRPTO predicts a binary
observed terminal outcome, and its continuous interval is only a downstream
score embedding.

Several figures compare CQR and CTI on one data set or run. They are
illustrations of a width/coverage trade-off, not evidence of general dominance.
Any claim that the curve "confirms validity" confuses empirical agreement with
the theorem.

### Chapter 5: probability calibration and Venn predictors

The definitions of Brier score, log-loss, reliability diagrams, Platt scaling,
isotonic regression, beta calibration, and temperature scaling are useful.
The chapter is too categorical when it says no classifier is calibrated by
default, declares Venn-Abers the safest general default, or extrapolates a
synthetic experiment/benchmark to every safety-critical task.

Probability calibration and set coverage answer different questions. A
calibrated score can still have poor subgroup conformal coverage; a
miscalibrated score can still yield marginally valid conformal sets under
exchangeability. Venn validity is not an arbitrary-subset guarantee. The
claim that ordinary calibration narrows all conditional-coverage gaps lacks a
theorem and can fail when the conditioning variable contains information not
captured by the calibrated score.

## Table audit

| Table or display | Assessment |
|---|---|
| Historical milestones (unnumbered, Chapter 1) | Pedagogical chronology, not a verified causal history. The algorithmic-randomness lineage is presented too strongly. |
| Table 2.1, nonconformity measures | Useful formula summary. Efficiency rankings are heuristic/model-dependent; validity still requires a correctly frozen score rule and exchangeability. |
| Full conformal advantages/drawbacks (unnumbered) | Fair high-level comparison, but "statistically most efficient" is not universal across every model, score, and computational approximation. |
| Table 2.2, terminology bridge | Helpful historical vocabulary crosswalk; should not be used as proof of modern coverage claims. |
| Table 3.1, uncertainty methods | Overstates CP's uniqueness and understates valid Bayesian/frequentist interpretations under their assumptions. |
| Table 3.2, model-specific scores | Useful examples; each score needs a symmetric/frozen construction for the theorem. |
| Table 3.3, APS/RAPS/SAPS | Good multiclass orientation. "All achieve finite-sample coverage" is conditional on the exact randomized/deterministic construction and rank rule. |
| Table 3.4, score decision guide | Practitioner heuristic, not a dominance result. Binary hinge and margin are rank-equivalent. |
| Table 4.1, regression methods | Same comparative overstatement as Table 3.1; conformal validity and model-based interval validity are different conditional statements. |
| Table 5.1, scikit-learn release wording | A documentation audit, not a statistical result; version-specific claims require direct source verification. |
| Table 5.2, documentation versus literature | Useful critique but rhetorically stronger than the evidence shown. |
| Table 5.3, calibrator experiment | One controlled synthetic experiment; it cannot establish a universal ordering of calibrators. |
| Table 5.4, calibration operators | Useful taxonomy. "Validity" must distinguish empirical calibration, asymptotic properties, and Venn multiprobability validity. |
| Table 5.5, minimum calibration sizes | Heuristic guidance, not theorem-backed minima. Tail support, score distribution, model class, and desired error matter. |
| Table 5.6, calibrator decision guide | Opinionated recommendation. Validate on the target scoring task and do not treat Venn-Abers as an automatic default. |

## Figure and graph audit

| Figure | What it shows | Audit judgment |
|---|---|---|
| 1.1 | CRPS as area between forecast and outcome CDFs | Correct intuition; peripheral to CRPTO's set coverage. |
| 1.2 | Photograph of Vapnik | Historical illustration, no evidentiary role. |
| 1.3 | Google Trends interest through 2025 | Descriptive popularity graph; query/geography/normalization are not documented enough for scientific use. |
| 2.1 | Split-conformal regression band | Construction is correct for absolute residuals. One realized test coverage value is illustrative only. |
| 2.2 | Binary split-conformal sets | Useful set-cardinality visualization. Claims that two-label sets are rare or the threshold exceeds 0.5 are data/run-specific. |
| 2.3 | Support vectors and an error-bound intuition | Stylized teaching picture; the formal bound needs its exact theorem assumptions. |
| 2.4 | VC dimension in two dimensions | Standard and essentially correct. |
| 2.5 | Complexity versus empirical error/capacity penalty | Stylized schematic, not measured data. |
| 2.6 | Marginal, conditional, and failed coverage regimes | Good conceptual warning; not a quantitative result. |
| 3.1 | Synthetic binary ICP in a two-feature view | Illustrates misses/set sizes. A single synthetic run cannot validate a procedure or locate all uncertainty. |
| 4.1 | True versus predicted values | Standard point-prediction diagnostic; no conformal guarantee is visible. |
| 4.2 | Calibration/test residual distributions and cutoff | Useful shift diagnostic. Similar-looking histograms do not prove exchangeability. |
| 4.3 | Symmetric conformal intervals | Correct illustration of one run; realized 90.7% is neither required nor proof of validity. |
| 4.4 | CQR width versus target coverage | Expected monotonic trade-off in the displayed implementation; not universal under every fitted model/numerical crossing rule. |
| 4.5 | Empirical versus target CQR coverage | Agreement in one experiment illustrates but does not confirm the theorem. |
| 4.6 | Interval width versus house price | Shows fitted heteroscedastic adaptation; association is data/model-specific. |
| 4.7 | CTI/CHR/CQR/split set sizes from another source | Must be cited to the original paper; method ranking is tied to its simulation/data design. |
| 4.8 | CQR versus CTI coverage | One data set/run; no general equality or dominance conclusion. |
| 4.9 | CQR versus CTI mean width | One data set/run; narrower CTI here is not a universal result. |
| 4.10 | Single-alpha CQR/CTI comparison | Same limitation, amplified by focusing on one alpha. |
| 5.1 | Logistic reliability under two `d/n` regimes | Useful synthetic counterexample to automatic calibration; not proof that every logistic model miscalibrates. |
| 5.2 | Raw logistic versus Venn-Abers | Controlled example only; the large reported percentage improvements are not portable effect sizes. |
| 5.3 | Calibration statistics versus `d/n` | Shows the selected simulation path; monotonicity depends on the data-generating and fitting setup. |
| 5.4 | Five calibrators on one task | Comparative illustration, not a universal leaderboard or safety guarantee. |

## What CRPTO is already doing correctly

1. The binary identity `|y-p|=1-p_hat_y` is exact.
2. Score-stratum boundaries are learned from an earlier outcome-independent
   score block and frozen before residual/evaluation outcomes.
3. Every residual window uses the exact ascending split-conformal rank.
4. The paper distinguishes the discrete prediction set from the continuous
   interval embedding and from latent individual PD.
5. It reports empty and full binary sets rather than relying only on average
   cardinality.
6. It keeps all candidates and gives sharp completion bounds for unresolved
   evaluation outcomes.
7. It does not claim candidate coverage for the funded/selected set.
8. It separates probability-model diagnostics from coverage controls and does
   not select an OOT model winner.

## Required corrections and additions to CRPTO

### Required

1. Replace statements that all 40 cells "fail the conformal guarantee" with
   two distinct statements:
   - all 40 realized finite-archive sharp upper coverage endpoints are below
     0.90 under the six-month endpoint contract; and
   - only cells rejected by the predeclared multiplicity-adjusted
     Beta--Binomial test are inferentially incompatible with the within-stratum
     exchangeable continuous-score reference.
2. Add the conditional coverage law and exact test definition, including the
   lower miss count over every completion of unresolved labels and the
   conservative role of inclusive ties.
3. Add the complete score-stratum-by-label Mondrian benchmark. It must use
   direct candidate-label set membership and report all learners/windows,
   class-cell sizes, exact ranks, overall sharp bounds, class-specific sharp
   ratio bounds, empty/full/singleton shares, and no selected recipe.
4. Replace the existing two-origin wording with an equal-minimum-follow-up
   sensitivity, or explicitly retain the unequal maturity as a limitation if
   that run cannot be completed.
5. Cite primary sources for class-conditional CP, nonexchangeable/online CP,
   post-selection/FCR, action-conditional guarantees, and censoring rather
   than citing this book.

### Worth adding if space permits

1. A PAC/tolerance-rank sensitivity can show how much larger the rank must be
   to obtain a high-probability lower bound on conditional coverage, but it is
   secondary once the exact Beta--Binomial diagnostic is present.
2. A sharp residual-threshold sensitivity over labels unavailable at the
   conformal-fitting cutoff would strengthen the current four-scenario refit,
   conditional on the already frozen score model. It would not sharply bound
   the nonlinear PD/Platt refits.
3. A prevalence-versus-within-class decomposition can explain why a
   label-Mondrian recipe changes overall geometry, but it must retain the
   unresolved-label coupling and must not be presented as causal.

### Do not add as current evidence

1. Online adaptive conformal inference: the archive does not provide a live,
   promptly revealed feedback stream.
2. Covariate-weighted CP as a claimed repair: a reliable target/source density
   ratio is not identified here; any weighting result would be diagnostic.
3. Survival conformal bands as a drop-in fix: they change the endpoint and add
   censoring assumptions.
4. Selected/funded-set validity from candidate CP: this needs a method designed
   for selection, action-conditional outcomes, or decision loss.
5. Venn-Abers as an automatic probability or coverage repair: it addresses a
   different estimand and still needs a transport argument.

## Final evidentiary recommendation

Use the book as a private cross-check and teaching aid. Do not cite it for the
paper's central theorem or frontier claims. The CRPTO manuscript should rely on
primary conformal sources and should explicitly correct the book's most
important practical misconception: a below-target realized OOT coverage rate
is a finite-archive fact, while evidence against the conformal transport null
requires a separate inferential calculation.
