# IJDS complete-hull score-equivalence audit V1

**Date:** 2026-07-31
**Status:** retrospective, outcome-free protocol to be committed and tagged
before execution; no result is active until the complete artifact commit is
sealed and a later promotion decision is explicit.

**Protocol tag:**
`protocol/ijds-score-equivalence-complete-hull-2026-07-31-v1`

**Run tag:** `ijds-score-equivalence-complete-hull-2026-07-31-v1`

**Artifact tag:**
`artifacts/ijds-score-equivalence-complete-hull-2026-07-31-v1`

## 1. Question and interpretation boundary

The active exact theorem says that two score vectors preserve every weak order
on an allocation set \(\mathcal A\) exactly when

\[
t=\kappa s+h,\qquad \kappa>0,\quad
h\in\operatorname{span}(\mathcal A-\mathcal A)^\perp.
\]

Earlier finite diagnostics were tested on supplied synthetic allocation rows
and could certify only their observed span. V1 asks two outcome-free questions
on every complete monthly candidate menu:

1. Do the set-preserving endpoint embeddings used in active V1d satisfy the
   exact global score-equivalence condition relative to \(\theta=0\)?
2. Do the four frozen CatBoost calibration maps, after their own frozen
   conformal residual recipes are converted to the same
   \(q_\gamma=p+\gamma(u-p)\) decision score, satisfy that condition pairwise?

The audit does not optimize, select, or evaluate a portfolio. A failed
equivalence certificate means only that the theorem supplies no global
invariance guarantee for that cell. It does not establish that a particular
solver output, optimal face, funded set, payoff, or outcome changes. A passing
certificate is conditional on the exact nonrisk allocation polytope certified
here and requires translated—not copied—numeric caps.

## 2. Frozen, outcome-free sources

V1 reads only already frozen inputs:

- the active V4 score table and eight CatBoost/Platt residual recipes;
- the four-map calibrator-family pickle, common-taxonomy residual recipes, and
  their complete frozen vector hashes from the calibrator Phase-A artifact;
- the V1d outcome-free Phase-A freeze and its exact set-preservation
  diagnostic; and
- `id`, `loan_amnt`, `int_rate`, and `purpose` from the hash-locked raw archive.

The raw scan uses the existing four-column allowlist. Status, outcome,
payment, default, realized-value, and miscoverage fields are forbidden. No
evaluation endpoint, protected stage, refit, residual fit, optimizer, or
outcome join is invoked. The 2011 labels used historically to freeze the four
calibrator maps are not reopened by this run.

The runner requires an exact clean annotated protocol tag at `HEAD`, annotated
source tags resolving to their pinned commits, exact source descriptors, the
V1d candidate-identity contract, all frozen calibrator vector hashes, and an
unchanged source snapshot before writing.

## 3. Complete allocation affine hull

For one monthly menu let \(x_i\) be dollar exposure, \(U_i>0\) the loan amount,
\(B=\$1{,}000{,}000\), and \(c=.25\). Before adding any score constraint, the
declared nonrisk allocation set is

\[
0\le x_i\le U_i,\qquad
\sum_i x_i=B,\qquad
\sum_{i:g(i)=g}x_i\le cB\quad\text{for every purpose }g.
\]

For each purpose define total capacity \(U_g=\sum_{i:g(i)=g}U_i\) and
\(W_g=\min(U_g,cB)\). If \(\sum_gW_g>B\), set

\[
y_g=B\frac{W_g}{\sum_hW_h},
\qquad
x_i=y_{g(i)}\frac{U_i}{U_{g(i)}}.
\]

This point has strictly positive exposure, is strictly below every loan upper
bound and every purpose cap, and fills the budget. It is therefore in the
relative interior of the full-budget hyperplane, so

\[
\operatorname{aff}(\mathcal A)=\{x:\mathbf1^\top x=B\},
\quad
\dim\operatorname{aff}(\mathcal A)=n-1.
\]

V1 must construct and numerically verify this witness independently in all 26
monthly menus: 11 policy-development months and 15 primary-OOT months. Failure
in any month stops the entire run. Purpose or loan inequalities that happen to
bind in a historical optimizer output are irrelevant to this global affine
hull and are not added as equalities.

Once this hull is certified, score equivalence has the direct complete-vector
form

\[
t=\kappa s+b\mathbf1,\qquad \kappa>0.
\]

The runner estimates \(\kappa\) on centered score vectors and reports the
unit-level intercept, portfolio-score offset \(bB\), centered norms, residual
norm, maximum coordinate error, and the locked numerical tolerance. It never
subsamples loans or substitutes funded allocations for the candidate menu.

## 4. Primary family: active V1d embeddings

The primary family replays the exact active V1d construction. For each of the
eight windows, both roles, every month, every
\(\gamma\in\{0,.25,.5,.75,1\}\), and every
\(\theta\in\{0,.25,.5,.75,1\}\), define

\[
u_i^{(\theta)}=
\begin{cases}
1,&u_i^{(0)}=1,\\
p_i+(1-\theta)(u_i^{(0)}-p_i),&u_i^{(0)}<1,
\end{cases}
\qquad
q_i^{(\theta,\gamma)}=p_i+\gamma
\{u_i^{(\theta)}-p_i\}.
\]

Each score is compared with the same window/month/gamma reference at
\(\theta=0\). The complete table has

\[
8\times26\times5\times5=5{,}200
\]

rows. The 1,040 \(\theta=0\) self-comparisons are explicit positive controls.
All 1,040 \(\gamma=0\) rows, including 832 nonzero-\(\theta\) identity
comparisons, must pass exactly because \(q^{(\theta,0)}=p\). These controls
are gates, not scientific findings. Every nonzero-\(\gamma\), nonzero-\(\theta\)
cell is retained regardless of result.

Before comparisons, the replay must reproduce all 80 frozen V1d
set-preservation diagnostic rows (eight windows times two roles times five
theta values), including zero changed binary sets.

## 5. Secondary family: closed calibrator family

The secondary family contains the four frozen maps in their locked order:
Platt, isotonic, beta `abm`, and the declared IVAP Venn--Abers scalarization.
The runner algebraically reconstructs all four complete probability vectors
and requires exact agreement with the Phase-A hashes. For each map \(c\),
window \(w\), and loan, its frozen common-taxonomy recipe yields upper endpoint
\(u_{cwi}\), and

\[
q_{cwi}^{(\gamma)}=p_{ci}+\gamma(u_{cwi}-p_{ci}),
\qquad\gamma\in\{0,.25,.5,.75,1\}.
\]

All six unordered method pairs are compared for every window and all 26
months, producing

\[
6\times8\times26\times5=6{,}240
\]

rows. At \(\gamma=0\), the score is exactly the frozen calibrated probability
and is reconciled to that vector before any window-specific upper endpoint is
used. The run reports all maps and pairs; it selects no calibrator, gamma,
window, role, month, or direction. The Venn--Abers scalar does not inherit a
multiprobability guarantee and is not treated as a latent-PD interval.

This secondary family certifies only the order of the declared
\(q_\gamma\) score functional. If a future optimizer also replaces the point
probability inside loan-specific expected-payoff coefficients, its objective
vector changes across calibrators. Score equivalence alone then does not
certify equality of the full optimization problem or its optimizer set; that
would require a separately locked joint score--objective audit.

## 6. Runtime controls, outputs, and stop rules

For each of the 26 menus, a positive synthetic control
\(t=1.75s+.125\mathbf1\) must pass and a deterministic perturbation orthogonal
to \(\operatorname{span}\{\mathbf1,s\}\) must fail. These 52 controls detect a
runner that accepts every relation or rejects every relation. They are
reported separately and have no empirical interpretation.

The exact persisted census is:

- 26 complete-hull certificates;
- 5,200 V1d embedding comparisons;
- 6,240 calibrator-family comparisons;
- 52 synthetic controls;
- one summary and one execution receipt.

Every persisted numeric field must be finite. A nonequivalent comparison still
reports its finite least-squares scale, intercept, and residual; no nullable
numeric result is used as a sentinel. Output directories are fresh direct
children of the two experiment roots and cannot be overwritten.

Stop before writing on any tag, ancestry, descriptor, hash, candidate census,
candidate identity, forbidden-column, set-preservation, hull, vector-replay,
control, complete-grid, duplicate-key, nonfinite-value, or tolerance failure.
Repeat the source descriptor gates before the output seal. The final artifact
commit must be the single direct child of the protocol commit, change only the
six declared output paths, and receive the annotated artifact tag.

## 7. Locked interpretation

Permitted statements after a valid complete run are limited to the exact cell
census:

- a passing cell certifies positive-affine score equivalence on that complete
  monthly full-budget affine hull, with translated caps;
- a failing cell says global score-order invariance is not certified for that
  pair and cell; and
- the complete distribution of passing and failing cells may be described
  without selecting a method, embedding, or policy.

Even in a passing cell, reusing the same numerical right-hand side under both
scores need not preserve the feasible region. The certificate preserves cap
sets only after the right-hand side is translated by the reported positive
scale and portfolio-score offset.

The run cannot establish an actual allocation change, equal or unequal optimal
faces at any fixed cap, optimizer uniqueness, a preferred score, improved
coverage, prospective transport, selected/funded-set validity, causal effect,
or portfolio performance. In particular, the calibrator-family rows do not
hold the payoff objective invariant and therefore cannot certify full
calibrator-to-calibrator optimizer invariance. Outcome-free non-equivalence is
a decision-identification diagnostic, not an outcome claim.
