# Current-version addendum: conformal optimization and robustness calibration

## Status and evidentiary boundary

This addendum records a targeted intake audit of two recent conformal
optimization papers as of 2026-07-26:

1. Zhao, Yu, Sesia, Deshmukh, and Lindemann, *Conformal Predictive
   Programming for Chance Constrained Optimization*, arXiv:2402.07407; and
2. Zhou and Zhu, *Calibrating Decision Robustness via Inverse Conformal Risk
   Control*, arXiv:2510.07750.

This is a literature-provenance addendum only. It does not activate a CRPTO
method, theorem, numerical result, policy claim, or evidence source. The active
claim registry, active-source registry, and paper-facing evidence manifest
remain authoritative. In particular, this file does not promote either paper
into `configs/ijds_active_evidence_sources.yaml`.

The official arXiv abstract and full-text HTML surfaces were inspected for both
current versions. They identify Zhao et al. v3 as revised 2026-07-09 and
Zhou--Zhu v3 as revised 2026-06-10. Direct shell downloads of both official
PDFs failed because this execution environment could not connect to
`arxiv.org`; no mirror was substituted. Consequently:

- current v3 metadata, theorem statements, assumptions, algorithms, proofs,
  tables exposed in HTML, and manuscript-facing positioning were audited;
- no local v3 byte identity, PDF page count, embedded metadata, SHA-256, or
  rendered-formula/figure visual QA is claimed;
- the Zhou--Zhu v2 PDF already in the corpus was parsed on every page and
  compared with the official v3 HTML at every previously flagged issue; and
- no local Zhao et al. PDF object was available, but its current theorem
  contracts were checked against the complete official v3 HTML.

Any sentence below labelled **v2 finding** applies only to the local Zhou--Zhu
v2 bytes. It must not be imputed to v3 without a clean v3 diff.

## Intake ledger

| Object | Current official revision | Local object | Pages / bytes | SHA-256 | Audit grade in this addendum |
|---|---|---|---:|---|---|
| Zhao et al., arXiv:2402.07407 | v3, revised 2026-07-09 | Official full-text HTML audited; PDF not materialized | PDF unknown | Not available | Full HTML theorem/assumption audit; no PDF visual QA |
| Zhou--Zhu, arXiv:2510.07750 | v3, revised 2026-06-10 | Official full-text HTML audited; PDF not materialized | PDF unknown | Not available | Full HTML theorem/algorithm/table audit; no PDF visual QA |
| Zhou--Zhu local comparator | v2; embedded arXiv banner dated 2026-01-29 | `Papers_tesis/supplement/Zhou Zhu 2025 - Calibrating Decision Robustness via Inverse Conformal Risk Control.pdf` | 20 / 1,022,807 | `D1828D14FF6CC6E5726543F9478CAC2B4C2E96FC3B7A1E1766BC9E57C613F25D` | Full-page text extraction plus targeted formula/proof audit |

The local v2 parser route was PyPDF 6.10.0 over all 20 pages. Poppler
26.05.0 renders of pages 4--6, 8, 12, 15, and 16 were visually checked against
the extracted equations, Algorithm 1, Table 1, the main validity/frontier
claims, and the corresponding proofs.

The local Zhou--Zhu PDF metadata identifies
`https://arxiv.org/abs/2510.07750v2`, the title and two authors, and a CC BY 4.0
license. Its title page says “Preprint. February 2, 2026,” while its arXiv
banner says v2, 29 January 2026. Those are properties of the local v2 object,
not of the unavailable current v3 object.

Official records:

- [Zhao et al., arXiv:2402.07407](https://arxiv.org/abs/2402.07407)
- [Zhou and Zhu, arXiv:2510.07750](https://arxiv.org/abs/2510.07750)

## Zhao et al.: current-version claim adjudication

### What the current-version full text supports

The v3 theorem and assumption surfaces support the following narrow
description:

- Conformal Predictive Programming (CPP) addresses chance-constrained
  optimization by inserting a conformal quantile associated with a constraint
  function into an optimization construction.
- Its general a-posteriori analysis freezes the optimized solution and uses a
  second i.i.d. calibration sample. The marginal result covers
  $f(x^*(K),Y)\leq C_m(x^*(K))$ under the product law, and the paper's
  “conditional” result is a PAC statement over the calibration sample for
  $f(x^*(K),Y)\leq C_c(x^*(K))$; neither is feature-conditional validity.
- The paper includes a robust CPP extension for distribution shift and a
  Mondrian CPP extension for group-conditional chance constraints. Robust CPP
  uses a predeclared $f$-divergence ambiguity radius. Mondrian CPP requires the
  finite-sample rank condition separately in every user-defined group.
- The original zero-threshold event $f(x^*(K),Y)\leq0$ is not supplied by the
  general offset results merely because CPP was optimized with a zero
  constraint. The separate quantile-shift theorem targets that event only when
  its calibration-dependent $\delta^*$ lies in $(0,1)$.

This is enough to support the high-level manuscript statement that conformal
quantities have been embedded directly in optimization constraints, that the
construction uses a conformal quantile of a constraint function, and that a
Mondrian chance-constraint variant exists. The manuscript's immediate
qualification—“under its stated sampling and chance-constraint contract”—is
essential and should remain.

The description does **not** support transferring a CPP certificate to CRPTO.
CPP calibrates a constraint-function construction for a chance-constrained
program. CRPTO places a prediction-set upper endpoint into a per-unit LP
risk-budget coefficient and studies the resulting finite-archive geometry.
Those are different random objects, constraints, estimands, and selection
maps.

### Boundary after the full-text audit

The HTML audit resolves the event, conditioning, sample-splitting,
calibration-size, quantile-shift, ambiguity-set, and class-size questions above.
It also reinforces the non-transfer boundary: the paper should not be cited for
feature-conditional validity, funded-set coverage, optimizer-selected-loan
coverage, temporal transport, or a certificate for CRPTO's risk-budget
substitution. The remaining intake deficit is documentary rather than
conceptual: the official PDF bytes still need hashing and rendered equations,
figures, and pagination still need visual QA.

### Manuscript-facing disposition

The Zhao paragraph in `paper/CRPTO_ijds.qmd` was tightened after this audit to
name the second i.i.d. calibration sample, the offset event, and the additional
conditions needed to reach the original zero-threshold constraint. It still
expressly says that CRPTO inherits no guarantee. The bibliography records v3's
revision date while retaining 2024 as the initial-posting year.

## Zhou--Zhu: exact scope visible in the local v2 object

### Statistical object and guarantees

The v2 setup starts from a nested, context-dependent uncertainty-set family

\[
  \{\mathcal U_\lambda(X):\lambda\in\Lambda\},
  \qquad
  \lambda_1\leq\lambda_2
  \Rightarrow
  \mathcal U_{\lambda_1}(X)\subseteq\mathcal U_{\lambda_2}(X),
\]

and defines the robust decision

\[
  z^*_{\lambda}(X)
  \in \arg\min_{z\in\mathcal Z}
  \max_{y\in\mathcal U_\lambda(X)} f(y,z).
\]

Its two paper-facing losses are outcome-set miscoverage

\[
  I_\lambda(X,Y)=\mathbf 1\{Y\notin\mathcal U_\lambda(X)\}
\]

and oracle regret

\[
  R_\lambda(X,Y)=
  f(Y,z^*_{\lambda}(X))-\min_{z\in\mathcal Z}f(Y,z).
\]

For a fixed, prespecified \(\lambda\), a nonnegative loss
\(\ell_\lambda\in[0,B]\) almost surely, and exchangeable calibration and test
pairs, v2 proposes the relaxed estimator

\[
  \widetilde\alpha_\ell(\lambda)
  =\frac{n}{n+1}\bar\ell_n(\lambda)+\frac{B}{n+1},
\]

along with a ceiling-based version
\(\widehat\alpha_\ell(\lambda)\). Theorem 3.4 proves the expectation statement

\[
  \mathbb E[\widehat\alpha_\ell(\lambda)]
  \geq
  \mathbb E[\ell_\lambda(X_{n+1},Y_{n+1})].
\]

That is an expectation-over-repeated-calibration-samples guarantee for a fixed
\(\lambda\). It is not, by itself, the realized-sample assertion
\(\widehat\alpha_\ell(\lambda)\geq
\mathbb E[\ell_\lambda(X,Y)]\), and it is not a simultaneous statement over a
grid of robustness levels.

Under i.i.d. sampling, v2 Proposition 3.5 adds a Hoeffding-style, fixed-
\(\lambda\), high-probability absolute-error bound. A genuinely simultaneous
frontier would need to add that error term and account for the number of
robustness levels and the two losses, or use another valid simultaneous
construction. If \(\lambda\) is selected after viewing the same frontier, v2
itself recognizes the resulting selection problem and proposes sample
splitting: one subset selects \(\widehat\lambda\), and the other recalibrates
the selected losses.

These distinctions matter for CRPTO. “Inverse conformal risk control” in v2
means estimating the expected loss associated with a specified robustness
level, with an additional split for post-hoc selection. It does not mean that
an arbitrary realized frontier is automatically an upper confidence frontier,
nor that a robustness parameter may be selected on the same observations
without correction.

### Assumptions needed for the frontier interpretation

The loss-estimator result and the Pareto-frontier result have different
requirements in v2:

- fixed-\(\lambda\) expectation validity uses exchangeability and a known or
  justified almost-sure bound \(B\);
- the high-probability error bound strengthens exchangeability to i.i.d.
  sampling;
- monotone miscoverage follows from nested uncertainty sets;
- monotone expected regret additionally requires “majorant consistency,”
  namely that the conditional expected realized cost of the chosen robust
  decision weakly increases with \(\lambda\); and
- post-selection recalibration requires a genuine data split that leaves the
  evaluation subset and test point exchangeable conditional on the selection
  subset.

Majorant consistency is a substantive property of the selected decision rule,
the outcome law, and the robust surrogate. Monotonicity of the worst-case
robust objective as an uncertainty set expands does not automatically imply
monotonicity of out-of-sample expected realized cost. The v2 paper supplies a
counterexample in which nested sets hold but expected regret moves in the
opposite direction. The assumption should therefore not be described in CRPTO
as automatic or universally “mild.”

### Adversarial findings first identified in v2

The following are **v2 findings**, not claims about v3.

#### 1. Expected conservativeness does not establish the displayed certified frontier

V2 Theorem 3.4 establishes
\(\mathbb E[\widehat\alpha]\geq\alpha\). Corollary 3.8 then assumes the
samplewise coordinate inequalities
\(\widehat\alpha_I(\lambda)\geq\alpha_I(\lambda)\) and
\(\widehat\alpha_R(\lambda)\geq\alpha_R(\lambda)\) for every \(\lambda\), and
uses them to call the lower-left envelope certified. The theorem does not
establish that premise. A repair could use the high-probability bound with an
explicit multiplicity adjustment over all evaluated coordinates, or a
different simultaneous-valid construction. The current v3 must be checked for
such a repair before “certified Pareto frontier” is cited as a realized-sample
guarantee.

#### 2. The printed split algorithm and its proof use different denominators

Algorithm 1 sums losses over split \(I_j\) but divides by the original \(n\)
in its displayed lines 5--6. The Appendix E validity argument instead uses
\(|I_2|\) and the correction \(B/(|I_2|+1)\). Read literally, the algorithm
underestimates the split mean and does not implement the proof. V3 must be
checked to determine whether this was corrected as a typographical error and
whether the released implementation follows the proof.

#### 3. The empirical choice of \(B\) does not satisfy the stated theorem contract

Assumption 3.2 requires a known or analytically justified almost-sure upper
bound \(B\). Appendix F says the experiments heuristically set \(B\) to the
maximum regret observed in \(10^2\) simulations. A simulated maximum is not an
almost-sure bound without an additional support argument. Therefore the v2
experimental “validity” claims are not covered by the displayed theorem solely
from the reported procedure. V3 must be checked for analytic bounds, clipping,
an independent bound-estimation argument, or revised claim language.

#### 4. Weak monotonicity does not make every image point Pareto efficient

V2 Proposition 3.7 claims that the full image of
\(\lambda\mapsto(\alpha_I(\lambda),\alpha_R(\lambda))\) is exactly the Pareto
frontier when miscoverage weakly decreases and regret weakly increases. Under
the usual Pareto definition, if miscoverage is tied while regret strictly
increases, the higher-regret point is dominated; similarly for a regret tie and
strictly worse miscoverage. The proof excludes only strict improvement in both
coordinates. The defensible object is the nondominated subset of the image
unless strict trade-off conditions or a nonstandard strong-dominance
definition are stated. This should be rechecked in v3.

The v2 empirical discussion on page 8 independently acknowledges that the
ground-truth curves for the newsvendor and portfolio examples contain points
that are not strictly on the Pareto frontier and says additional pruning is
needed. That observation is consistent with the tie counterexample but not
with Proposition 3.7's claim that the whole image is exactly the frontier.

#### 5. The claimed breadth of majorant consistency is stronger than the proof shown

V2 states that majorant consistency holds broadly and is directly implied by
several robust or distributionally robust formulations. The displayed
argument proves a particular norm-ball linear example and also gives a
counterexample. Monotonicity of a robust value function alone is insufficient
to prove the required monotonicity of expected realized cost for its selected
optimizer. A current-version audit should demand a theorem or problem-specific
derivation for each claimed class rather than accept the broad statement by
analogy.

#### 6. “Any family” still inherits setup and training-separation conditions

The abstract's phrase “any family of robust predict-then-optimize policies”
cannot erase the fixed-family, bounded-loss, sampling, and post-selection
conditions. If the uncertainty-set family, predictor, loss bound, or candidate
grid is learned using the same observations later treated as exchangeable
calibration data, an additional conditioning or splitting argument is needed.
The local v2 experiments also use degenerate contexts and synthetic problems;
they do not empirically validate a temporally drifting credit-allocation
archive.

#### 7. Table 1 contains a cell-for-cell duplicated sensitivity block

In the rendered v2 Table 1, every reported gap and runtime entry in the
\(|\Lambda|=10\) block is repeated in the corresponding \(|\Lambda|=20\)
block for all three sample sizes and all four optimization problems. Exact
duplication includes runtimes, even though the table is presented as a grid-size
sensitivity analysis. This may be a typesetting/copying error, reuse of the
same run, or an undocumented implementation detail; the PDF alone cannot
adjudicate which. V3 and its released experiment artifacts should be checked
before the sensitivity table is treated as independent evidence about scaling
with \(|\Lambda|\).

### V3 adjudication of the seven v2 findings

The official v3 HTML permits a direct disposition rather than leaving these as
open version-drift questions:

1. **Expected versus realized simultaneous certification: unresolved.**
   Theorem 3.4 still proves only
   $\mathbb E[\widehat\alpha_\ell(\lambda)]\geq
   \mathbb E[\ell_\lambda]$ for fixed $\lambda$. Proposition 3.5 gives a
   one-shot high-probability error bound for a fixed $\lambda$ under i.i.d.
   sampling. Corollary 3.8 still *assumes* coordinatewise upper bounds for all
   $\lambda$ and does not derive that simultaneous premise from either result.
   No multiplicity adjustment over the evaluated grid and two losses appears
   in the displayed chain.
2. **Split denominator: repaired.** Algorithm 1 now divides each split sum by
   $|\mathcal I_j|$, matching the Appendix E proof. The v2 printed
   $n$-denominator defect should not be attributed to v3.
3. **Empirical bound $B$: acknowledged, not repaired as a theorem input.** V3
   still allows experiments to approximate $B$ by the sample maximum, but its
   new ablation explicitly shows that this can violate Theorem 3.4. Results
   using the empirical maximum are therefore heuristic, while theorem-covered
   results require a genuine almost-sure bound.
4. **Weak-monotonicity/Pareto-tie defect: unresolved.** Proposition 3.7 still
   calls the entire weakly monotone image the Pareto frontier and its proof
   rules out only strict improvement in *both* coordinates. Under standard
   weak Pareto dominance, equality in one coordinate and strict improvement in
   the other makes a point dominated. The empirical section itself says some
   ground-truth image points require pruning.
5. **Breadth of majorant consistency: unresolved.** V3 continues to call the
   assumption standard, lists broad robust/DRO families, and says monotonicity
   of the robust objective directly implies it. That does not by itself prove
   monotonicity of the selected optimizer's conditional expected realized cost;
   problem-specific verification remains necessary.
6. **Fixed family and post-selection separation: clarified.** V3 explicitly
   limits the main estimator to prespecified $\lambda$, states that same-sample
   selection breaks its exchangeability argument, and uses an independent
   split for recalibration. It still does not license learning the entire
   policy family, loss bound, or candidate grid on the calibration split.
7. **Duplicated sensitivity block: persists.** Every displayed gap and runtime
   in the $|\Lambda|=10$ block remains repeated cell-for-cell in the
   $|\Lambda|=20$ block, while the $|\Lambda|=30$ block changes. V3 nevertheless
   states that runtime and accuracy improve as $|\Lambda|$ grows. The duplicated
   block cannot independently support that scaling statement without code or
   corrected results.

## Zhou--Zhu current-version claim adjudication

The v3 full text supports the high-level statement that the paper studies
inverse conformal risk assessment for robust predict-then-optimize policies,
traces a miscoverage--regret trade-off, and uses split recalibration after
selection. It does not support describing the displayed frontier as a
simultaneous realized-sample certificate without adding the missing joint
upper-bound argument.

Table S13 and Related Work were tightened to describe expected
miscoverage--regret assessment for prespecified robustness levels and split
recalibration after post-hoc selection. They deliberately avoid “simultaneously
certified Pareto frontier.”

CRPTO does not implement that protocol. Its eleven development menus are ruler
sensitivity diagnostics; they are neither an independent selection/calibration
split for a robust-policy family nor a simultaneous risk certificate. No CREME
guarantee is inherited.

## What should and should not change in the CRPTO paper

### Retain

- Retain the Zhao paragraph's contrast between a calibrated constraint-function
  quantile and CRPTO's prediction-set endpoint used as an LP coefficient.
- Retain the explicit statement that CRPTO inherits no CPP guarantee.
- Retain Table S13's descriptive expected miscoverage--regret assessment and
  split-recalibration wording.
- Retain the statement that the development menus do not support valid
  selection or decision-risk certificates.

### Tighten only if the prose is edited again

- Continue mapping Zhou--Zhu specifically to “expected miscoverage/regret
  assessment for a prespecified robustness level, with split recalibration
  after selection,” instead of a generic claim that it directly controls every
  form of decision loss.
- Avoid using “conditional guarantee” for Zhao without naming the conditioning
  sigma-field or Mondrian class and the probability level.
- Add explicit arXiv revision notes to the two bibliography records once the v3
  byte identities have been ingested.

### Do not add

- Do not claim feature-conditional, temporal, funded-set, or optimizer-selected
  coverage from CPP.
- Do not call the Zhou--Zhu frontier simultaneously certified unless the v3
  theorem supplies a realized-sample joint guarantee or the paper's
  high-probability bounds are adjusted over the evaluated grid and losses.
- Do not use either paper to justify selecting CRPTO's ruler, gamma,
  coordinate, policy, or structural scenario after inspecting the present
  archive.
- Do not promote either method into the active evidence registry merely because
  it is close related work.

## Remaining PDF-intake completion

The scientific claim audit is complete from official v3 HTML. Documentary PDF
intake remains fail-closed until the following are completed:

1. download only the two official arXiv v3 PDFs, without overwriting the local
   Zhou--Zhu v2 object;
2. use explicit filenames containing authors, title, arXiv identifier, and
   `v3`;
3. record byte size, page count, embedded version metadata, and SHA-256; and
4. parse every page and visually verify theorem statements, algorithms,
   equations, tables, figures, and captions against the official render.

The unavailable PDF bytes prevent a grade-A local corpus receipt, not a
manuscript-facing decision. Neither paper is an active empirical evidence
source for CRPTO, and no claim-ledger change is warranted.
