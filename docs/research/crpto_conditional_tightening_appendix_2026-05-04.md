# paper-crpto Conditional Tightening Appendix - 2026-05-04

This note records the dependency audit behind the conditional Hoeffding/Bernstein
tightening used in the CRPTO theory section. It is an appendix to
`book/chapters/02-marco-teorico.qmd`, not a new
empirical claim and not a replacement for the main Markov theorem.

Standalone note: this appendix is retained because it is useful for the journal
version and reviewer response package. It must not be upgraded to the main claim
unless a dependence-aware proof or prospective validation design is added.

## Main Distribution-Free Claim

The main theorem controls the funded-set weighted noncoverage

```text
V = sum_i w_i 1{Y_i > u_i(alpha)}
```

for a bounded realized target `Y_i in [0, 1]` and an allocation fixed before the
evaluated labels are observed. Under exchangeability between calibration and
test observations, conformal validity gives `E[V] <= alpha`. Markov then gives
the finite-sample, distribution-free probability statement used by the paper.

This claim does not require independence among the evaluated loans. It also does
not require a parametric default model, a latent-PD assumption, or stable
covariates across all possible future regimes. That is why it remains the
primary theory claim.

## Conditional Tightening Claim

The Hoeffding/Bernstein tightening is narrower and conditional. It may be stated
only after conditioning on:

- the calibration sample used to form conformal radii;
- a funded-set allocation fixed before the evaluated labels are observed;
- additional independence, or conditional independence, of the indicators
  `Z_i = 1{Y_i > u_i(alpha)}`.

Under those extra assumptions, the weighted sum `V = sum_i w_i Z_i` becomes a
sum of bounded independent terms. Hoeffding gives a tail bound based on
`sum_i w_i^2`; Bernstein additionally uses conditional variance and `w_max`.

## Cluster-Aware Journal Proposition

The journal-strengthening version can state a weaker dependence-aware
proposition without pretending that loan-level indicators are independent.
Partition the funded set into clusters `g = 1, ..., G` such as period, grade, or
period-grade. Define

```text
Z_g = sum_{i in g} w_i 1{Y_i > u_i(alpha)}
W_g = sum_{i in g} w_i.
```

Within each cluster, the miss indicators may be arbitrarily dependent. After
conditioning on the calibration sample and the fixed funded allocation, assume
only that the cluster aggregates `Z_g` are independent or conditionally
independent across `g`. Then `0 <= Z_g <= W_g` and Hoeffding gives

```text
P(V - E[V] >= t) <= exp(-2 t^2 / sum_g W_g^2).
```

This is not the main theorem. It is a transparent supplement result: it moves
the extra assumption from loan-level independence to cross-cluster independence
and makes the exposure concentration term explicit. Table A14 supplies the
period, grade and period-grade weights that determine whether this tightening
is practically useful.

The numerical add-on is now Table A21:

| Cluster | 90% threshold | 95% threshold | Interpretation |
|---|---:|---:|---|
| period | 0.538 | 0.612 | Looser than the main `sqrt(alpha) = 0.100` Markov reporting threshold. |
| grade | 0.630 | 0.717 | Looser than Markov because exposure is concentrated by grade. |
| period-grade | 0.332 | 0.377 | Best of the cluster partitions, but still not tighter than Markov. |

So the dependence-aware result is mathematically transparent, but empirically
not more tight than Markov for this funded-set exposure concentration. It is
therefore useful as a journal caveat and reviewer-defense calculation, not as a
replacement main theorem.

## Dependency Caveat

Split conformal itself does not automatically make the test indicators
independent after calibration. They share a common calibration sample and may
also share unmodeled macro shocks, underwriting regimes, or borrower
correlation. Therefore the tightening should be presented as a conditional
journal appendix: useful, transparent, and mathematically standard, but not part
of the distribution-free core guarantee.

## Paper-Safe Wording

Use this distinction in the manuscript:

- Markov bound: main theorem; finite-sample; distribution-free; conservative.
- Hoeffding/Bernstein tightening: conditional lemma; sharper under additional
  independence or dependence-control assumptions.
- Exact 276K evidence: empirical validation of the promoted frozen policy and
  robust region; not a post-selection conformal guarantee by itself.

## Future Strengthening

A stronger journal version could replace the conditional independence assumption
with a dependence-aware concentration result, a cluster-level bound by period or
grade, or a prospective nested design where policy selection and final
confirmation are separated before labels are inspected.
