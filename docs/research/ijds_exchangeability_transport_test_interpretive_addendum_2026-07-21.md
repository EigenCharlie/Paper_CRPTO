# IJDS Joint-Block Rank-Reference Interpretive Addendum - 2026-07-21

## Status

This is a post-run interpretive correction to the immutable V1 lineage
`protocol/ijds-exchangeability-transport-test-2026-07-21-v1`. It does not alter
the tagged protocol, executed code, source tables, p-values, tie audit, or
31/40 source decision count. It narrows the active paper claim after an
adversarial theoretical review.

## Null actually evaluated

Within one frozen learner--window--score-stratum cell, V1 uses the law

\[
M\sim\operatorname{BetaBinomial}(m,n+1-r,r)
\]

for the number of target residuals above the fitted calibration order
statistic. This combined-rank law is exact when the `n` calibration
nonconformity residuals and all `m` target residuals are continuous and jointly
exchangeable as one block. With arbitrary ties, the lexicographic augmentation
argument makes its upper tail conservative for that same joint-block null.

This is stronger than the exchangeability condition sufficient for ordinary
split-conformal marginal coverage of one future observation. Pointwise validity
can be argued separately for calibration plus each single target without
asserting that all target rows are jointly exchangeable with one another.
Consequently, a V1 flag can be driven by target--target dependence or
heterogeneity and does not by itself refute the usual one-future-point
split-conformal guarantee. The diagnostic is one-sided against excess strict
misses; it is not an omnibus two-sided test of every departure from
exchangeability.

The active name is therefore **joint-block combined-rank reference
diagnostic**, and the 40 cell hypotheses are intersections of five
within-stratum joint-block nulls.

## Multiplicity after inspection

For an ex ante fixed family of valid p-values, Bonferroni over the five strata
within cell followed by Holm over 40 cells would control FWER under arbitrary
dependence. In this project, an exploratory implementation and approximate flag
pattern were inspected before the V1 tag. Locking the complete reporting grid
after that inspection prevents further result-dependent deletion or tuning, but
it does not undo selection already induced by inspection.

The 31 source rows marked `holm_reject` are therefore reported actively as
**cells meeting the locked nominal Bonferroni--Holm thresholds**. The manuscript
claims neither post-selection nor study-wide FWER control. A flag does not
identify a shift mechanism; a nonflag does not establish exchangeability or
adequate power; stratum flags do not control a global 200-test family.

## Active claim boundary

Permitted:

- 31 of 40 joint-block learner--window intersection nulls meet the locked
  nominal reporting thresholds;
- the underlying upper-tail reference is exact for continuous joint-block
  exchangeability and conservative with ties; and
- the completion-minimized miss count gives the supremum reference p-value over
  unrestricted unresolved binary outcomes.

Not permitted:

- direct rejection of ordinary one-future-point split-conformal validity;
- post-selection, prospective, confirmatory, or study-wide FWER control;
- an identified reason for the flag pattern; or
- exchangeability, transportability, or adequate power inferred from a
  nonflag.

The paper-facing evidence manifest preserves the immutable source fields for
replay but exposes the corrected active interpretation and nominal-flag names.
