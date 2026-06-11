# CRPTO Bound Tightening Experiment - 2026-06-11

Experimental branch result. This audit reads frozen funded-set weights only; it does not re-run DVC stages, does not search policies, and does not promote a new Lending Club champion.

## Fixed Funded-Set Diagnostics

- funded loans: `341`
- effective sample size: `126.1`
- sum of squared weights: `0.007932`
- max loan weight: `0.0350`
- observed `V(alpha=0.01)`: `0.028875`

## Alpha 0.01 Bound Menu

| Bound | Mode | threshold t | margin vs V | Role |
|---|---|---:|---:|---|
| `cantelli_one_sided` | `strong_individual_validity` | `0.036719` | `0.007844` | conditional variance diagnostic; sharper one-sided Chebyshev |
| `bennett` | `strong_individual_validity` | `0.048945` | `0.020070` | conditional independence/variance tightening; appendix-only |
| `cantelli_one_sided` | `weak_weighted_validity` | `0.066125` | `0.037250` | conditional variance diagnostic; sharper one-sided Chebyshev |
| `bernstein` | `strong_individual_validity` | `0.069832` | `0.040957` | conditional independence/variance tightening; appendix-only |
| `freedman_martingale` | `strong_individual_validity` | `0.069832` | `0.040957` | martingale analogue of Bernstein; needs a sealed sequential protocol |
| `bennett` | `weak_weighted_validity` | `0.072231` | `0.043356` | conditional independence/variance tightening; appendix-only |
| `bernstein` | `weak_weighted_validity` | `0.085169` | `0.056294` | conditional independence/variance tightening; appendix-only |
| `freedman_martingale` | `weak_weighted_validity` | `0.085169` | `0.056294` | martingale analogue of Bernstein; needs a sealed sequential protocol |
| `markov` | `none` | `0.100000` | `0.071125` | main distribution-free claim; only first moment needed |
| `hoeffding` | `loan_independence` | `0.105564` | `0.076689` | conditional bounded-difference diagnostic |

## Recommendation

- Keep Markov as the body theorem: it is the only first-moment, distribution-free statement compatible with the current post-selection caveat.
- Keep A21 cluster-aware Hoeffding as a dependence caveat, not a tightening: cluster exposure is too concentrated.
- Use A21b/A21c as an appendix sensitivity table. Cantelli, Bernstein, Bennett and Freedman show how much tightness is available if a reviewer accepts stronger independence, variance, or martingale assumptions.
- Drop Chebyshev, Azuma, Chernoff and naive union-Markov from paper-facing tables. They are respectively dominated, duplicative, too strong for the current individual-alpha evidence, or vacuous after policy-region correction.

## Assumption Audit

| assumption                        | status                  |   diagnostic_value | interpretation                                                                                                                              |
|:----------------------------------|:------------------------|-------------------:|:--------------------------------------------------------------------------------------------------------------------------------------------|
| nonnegative_normalized_weights    | pass                    |           1        | Funded-set weights are non-negative and normalized.                                                                                         |
| bounded_miss_indicators           | pass                    |           1        | miscovered_alpha01 is binary, so V is a bounded weighted sum.                                                                               |
| effective_sample_size             | concentrated            |         126.066    | n_eff is far below the funded loan count, so iid-style concentration does not get to use the headline OOT sample size.                      |
| loan_independence                 | not_verified            |         nan        | Defaults and conformal misses can share calibration history and macro period shocks; loan-level concentration bounds are appendix-only.     |
| post_selection_uniformity         | not_supported_by_markov |          45        | A naive union Markov statement over the 45 final policies is vacuous at alpha01; the exact robust-region audit remains empirical evidence.  |
| sequential_martingale_protocol    | not_available           |         nan        | Azuma/Freedman need a prospective filtration or online validation design; the current A24 replay is diagnostic, not a live guarantee.       |
| chebyshev_two_sided               | drop_from_table         |         nan        | Two-sided Chebyshev is dominated by Cantelli for the one-sided exceedance probability used in A21.                                          |
| azuma_hoeffding_martingale        | drop_from_table         |         nan        | Azuma gives the same numerical threshold as Hoeffding here while adding a sequential validation protocol assumption.                        |
| chernoff_mgf                      | drop_from_table         |         nan        | Chernoff is sharp, but it requires independent misses with each individual miss probability bounded by alpha.                               |
| union_markov_45_policy_region     | drop_from_table         |          45        | A naive union Markov statement over the 45 final policies is vacuous at the paper alphas.                                                   |
| empirical_bernstein_or_bootstrap  | diagnostic_only         |         nan        | Empirical-Bernstein or bootstrap intervals would use observed OOT labels; useful for sensitivity, not for the distribution-free theorem.    |
| cluster_independence_period       | conditional_loose       |           0.536464 | Cluster Hoeffding threshold at delta=0.10 is 0.5365; max cluster exposure is 0.2913, so this is not tighter than Markov's 0.1000 threshold. |
| cluster_independence_grade        | conditional_loose       |           0.651238 | Cluster Hoeffding threshold at delta=0.10 is 0.6512; max cluster exposure is 0.4235, so this is not tighter than Markov's 0.1000 threshold. |
| cluster_independence_period_grade | conditional_loose       |           0.334416 | Cluster Hoeffding threshold at delta=0.10 is 0.3344; max cluster exposure is 0.1480, so this is not tighter than Markov's 0.1000 threshold. |

## Paper-Read Audit

The local paper folder now includes Bennett (1962), Hoeffding (1963), Freedman
(1975), and Fuk--Nagaev (1971). Their roles for the IJDS draft are different:

- Bennett (1962) is directly relevant to A21c. Its assumptions match the
  conditional finite-sample calculation: independent, not necessarily identical
  summands, with only the variance of the sum plus component means and bounds.
  This supports keeping Bennett as an appendix sensitivity bound, especially for
  the frozen weighted Bernoulli miscoverage sum.
- Hoeffding (1963) supports the bounded-sum benchmark used in A21/A21b. It is
  weaker than Markov at `alpha=0.01` for the actual exposure concentration, but
  useful as a transparent negative benchmark.
- Freedman (1975) justifies the martingale analogue of Bernstein only under a
  prospective filtration with bounded increments and a conditional-variance
  process. It belongs in the supplement as a conditional comparison, not as a
  claim about the current frozen replay.
- Fuk--Nagaev (1971) is not promoted in the paper. Its inequalities are designed
  for independent sums with tail-probability and truncated-moment terms, useful
  when summands are unbounded or heavy-tailed. CRPTO's A21 variable is a bounded
  weighted sum of Bernoulli miscoverage indicators, so Bennett/Hoeffding/Freedman
  are more direct. Fuk--Nagaev may become relevant only for a future unbounded
  LGD or realized-loss extension.

Paper integration decision: cite Bennett and Freedman in A21c, keep Hoeffding
and Boucheron--Lugosi--Massart as concentration references, and leave
Fuk--Nagaev out of the manuscript to avoid a citation that does not support the
current bounded-indicator claim.
