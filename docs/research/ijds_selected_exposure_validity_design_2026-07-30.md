# IJDS selected and exposure-weighted validity design (2026-07-30)

## Status

This document is a future-study design, not an executable protocol and not an
active evidence source. It authorizes no run against the current historical
grid. Any implementation requires a new dated protocol, immutable configuration
and tag, same-population or otherwise justified sampling law, fully declared
runtime budget, and fresh outputs.

The design separates three targets:

1. coverage conditional on a loan being selected;
2. false coverage rate (FCR), the expected count-weighted false coverage
   proportion among selected loans; and
3. exposure-weighted portfolio miscoverage.

They coincide only under additional structure. The current paper's descriptive
count, invested-dollar, and fixed-capital identified sets establish none of
these sampling guarantees.

## Why the historical archive is a NO-GO

The active 2012 calibration blocks and 2016--2017 target menus do not supply the
complete sampling and implementation contract needed by JOMI:

- swapping a 2012 loan into a later issue-month menu changes chronology,
  eligibility, and population;
- the existing LP uses conformal endpoints estimated from calibration labels,
  so it would require the more complex calibration-dependent JOMI construction,
  which has not been protocol-locked or audited;
- loans within an issue month form a coupled menu rather than an established
  exchangeable sequence;
- target endpoints are incompletely observed;
- the current policy grid and its results have already been inspected; and
- a generic full-grid swap-and-resolve census would be enormous without
  repairing any of the preceding validity failures.

Budget coupling is not itself the obstruction. JOMI explicitly accommodates
optimization-based selection when its exchangeability, permutation-invariance,
and reference-set conditions hold. The current archive fails the sampling and
estimand contracts, not a blanket prohibition on optimization.

## Phase 1: equal-notional JOMI

The first prospective design should deliberately make count and dollar
weighting identical.

### Locked policy

- Freeze one learner, score, eligibility rule, and policy before evaluation.
- Select exactly \(K\) loans from every nonempty target menu.
- Allocate exactly \(B/K\) to each selected loan.
- Before scoring, exclude loans whose declared capacity is below \(B/K\).
- Use a deterministic, permutation-equivariant optimizer with a separately
  verified stable tie rule.
- Fit the prediction model and any selector parameters on an independent
  training split.
- Keep the final JOMI calibration sample disjoint from policy construction and
  evaluation.

For selected support \(S\), \(|S|=K\), and miss indicator
\(M_i=\mathbf1\{Y_i\notin C_i\}\),

\[
\operatorname{FCP}^{\$}
=
\frac{1}{B}\sum_{i\in S}\frac{B}{K}M_i
=
\frac{1}{K}\sum_{i\in S}M_i
=
\operatorname{FCP}^{N}.
\]

Thus count FCR control is also control of the expected invested-dollar FCP. No
new exposure-weighted theorem is needed in this equal-notional case.

### JOMI construction

For each selected target loan and each candidate binary label, form the
swap-specific JOMI reference set using the exact locked selection rule.
Condition on the exact selected-set size \(K\). The selection taxonomy must be
fixed before labels, and the implementation must verify that permuting
calibration rows only permutes the corresponding reference calculation.

The first implementation should make selection depend on frozen covariates and
point scores, not on conformal endpoints. This keeps the selection rule
independent of final calibration labels and removes one binary-label branch
from the swap computation. A conformal-endpoint-dependent selector is a later,
strictly more expensive protocol.

### Feasibility gate before outcomes

On an outcome-free pilot drawn from the intended population:

1. enumerate every target menu and selected focal unit;
2. compute all reference-set sizes and exact rank indices;
3. verify exact \(K\), capacity, budget, permutation, ID-reversal, and repeated-
   solver invariance;
4. retain the complete runtime and reference-size census; and
5. stop before outcomes if any required reference set is empty or too small for
   a nontrivial binary cutoff.

At nominal error \(\beta\), a deterministic split rank can be finite only when
the reference size \(r\) satisfies \(r\ge 1/\beta-1\). This is a resolution
condition, not a universal sample-size validity threshold.

Only after a clean feasibility freeze may a separately tagged evaluation phase
open complete target outcomes.

## Phase 2: bounded-concentration fractional exposure

For a selected support \(S\) of size \(R>0\), total invested exposure
\(A=\sum_i a_i>0\), and a predeclared concentration factor \(\kappa\ge1\),
suppose the policy enforces, for every realization,

\[
\frac{a_i}{A}\le\frac{\kappa}{R}
\qquad\text{for every }i\in S.
\]

Then the following inequality is deterministic:

\[
\operatorname{FCP}^{\$}
=\sum_{i\in S}\frac{a_i}{A}M_i
\le
\frac{\kappa}{R}\sum_{i\in S}M_i
=\kappa\operatorname{FCP}^{N}.
\]

Consequently, count-weighted FCR control at level \(\alpha/\kappa\) implies

\[
\mathbb E[\operatorname{FCP}^{\$}]\le\alpha.
\]

The same argument applies directly to a fixed-capital loss if the design
enforces \(a_i/B\le\kappa/R\). Alternatively,
\(\operatorname{FCP}^{B}=(A/B)\operatorname{FCP}^{\$}\le
\operatorname{FCP}^{\$}\) when \(A\le B\). The fixed-capital complement remains
accounting notation; cash is not a conformal observation.

A clean implementation should again select exactly \(K\) positive-exposure
positions. For the invested-dollar guarantee it must impose

\[
a_i\le \kappa A/K
\qquad\text{equivalently}\qquad
\frac{a_i}{A}\le\frac{\kappa}{K}.
\]

The simpler cap \(a_i\le\kappa B/K\) implies this invested-dollar condition
only when the policy also enforces \(A=B\). If residual cash is allowed, the
\(B\)-relative cap instead supports the fixed-capital inequality
\(\operatorname{FCP}^{B}\le\kappa\operatorname{FCP}^{N}\); it must not be used
to claim the invested-dollar bound.

The value of \(\kappa\) is a policy choice frozen before evaluation, not a
quantity selected from historical outcome performance. Smaller \(\kappa\)
improves the statistical level but restricts allocation flexibility. Reference
sets and binary prediction sets may become uninformative at the smaller
\(\alpha/\kappa\), so informativeness is a mandatory feasibility outcome rather
than a success-based tuning criterion.

## Quarantined theory candidate: nested lot layers

For a USD 25 policy let \(q_i\) be the number of funded lots and define nested
supports \(S_\ell=\{i:q_i\ge\ell\}\). One possible construction would build a
JOMI set \(C_{i,\ell}\) for each layer and use

\[
C_i=\bigcup_{\ell\le q_i}C_{i,\ell}.
\]

It then has the deterministic comparison

\[
\sum_i q_i\mathbf1\{Y_i\notin C_i\}
\le
\sum_\ell\sum_{i\in S_\ell}
\mathbf1\{Y_i\notin C_{i,\ell}\}.
\]

This is not an active method. Before it can support even a protocol, it needs a
complete proof connecting layer-specific selection taxonomies to the desired
weighted expectation, adversarial checks under ties and empty layers, exhaustive
small-instance enumeration, and efficiency analysis. Lots belonging to one
loan may never be treated as independent exchangeable observations: they share
one label.

## Alternative target: direct portfolio risk

If focal-loan coverage is not required, a cleaner target may be the bounded
monthly loss

\[
L_t(\lambda)
=
\frac{1}{B}\sum_i a_{it}(\lambda)
\mathbf1\{Y_{it}\notin C_{it}(\lambda)\}.
\]

Classical scalar Conformal Risk Control can calibrate a monotone loss family
when its sampling and monotonicity conditions hold. Stability-based CRC can in
principle handle a symmetric non-monotone algorithm, but it requires a valid,
nonvacuous stability certificate and reference-risk margin
[@angelopoulos2026nonmonotonic]. If changing \(\lambda\) reoptimizes the LP and
no such solver-stability proof is available, Learn-Then-Test remains the cleaner
route for a finite, preregistered policy catalog. The exchangeable unit must then be the
complete month or portfolio context, not an individual loan. This controls
aggregate risk, not focal selection-conditional coverage.

The current eleven development and fifteen target months are overlapping,
chronologically shifted, and too few to be relabeled as independent portfolio
contexts. A future study needs substantially more prospective or externally
validated blocks and the temporal contract in
`ijds_temporal_transport_dependence_contract_2026-07-30.md`.

## Required stop rules

Stop without evaluation or promotion if any of the following occurs:

- no defensible same-population exchangeability or replacement theorem;
- target outcomes, policy choices, tie rules, or reported cells influence the
  frozen selector;
- calibration-row permutations change anything other than corresponding row
  identities;
- repeated solver runs or ID reversal change selected support;
- the support size differs from the declared taxonomy;
- ordinary conformal sets are reused instead of constructing JOMI sets;
- count FCR is translated to expected dollar FCP without equal exposure, a
  locked concentration inequality, or a separately proved construction;
- a \(B\)-relative exposure cap is used to claim the invested-dollar bound when
  residual cash makes \(A<B\);
- covariate-shift weighting, weighted multiple testing, or InfoSP weights are
  relabeled as endogenous LP-exposure validity;
- unresolved outcomes are imputed and treated as observed;
- only cells completing before a timeout are retained;
- reference sets cannot attain the declared rank without the full binary set;
- FCR in expectation is described as a high-probability bound on one realized
  portfolio; or
- a denominator containing residual cash is called coverage of funded loans.

## Literature boundary

JOMI is the primary method for focal selection-conditional coverage under an
optimization-based selection rule. Conditioning on exact selection size can
connect its strong focal guarantee to FCR. InfoSP and InfoSCOP instead control
FCR when reporting informative prediction sets under their own monotone
selection contracts; they do not validate an arbitrary funding LP. CRC and
Learn-Then-Test target aggregate bounded loss. None automatically transfers
candidate conformal coverage to calibration-dependent fractional exposures.

The implementation order is therefore:

1. equal-notional, fixed-\(K\), label-free-selection JOMI;
2. a predeclared bounded-concentration extension; and
3. only after a separate proof, any nested-lot construction.

No JOMI run on the inspected historical grid is authorized.
