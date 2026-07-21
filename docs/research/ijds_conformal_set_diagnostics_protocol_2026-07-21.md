# IJDS Conformal-Set Diagnostics Protocol V1 - 2026-07-21

## Status and retrospective boundary

This protocol adds a complete reporting diagnostic to the already inspected
five-model primary-OOT coverage audit. Exploratory calculations exposed a large
resolved-label coverage imbalance before this document was written. The run is
therefore retrospective discipline and exhaustive reporting, not
preregistration, confirmation, or an untouched analysis.

Required tag:
`protocol/ijds-conformal-set-diagnostics-2026-07-21-v1`.

Required run:
`ijds-conformal-set-diagnostics-2026-07-21-v1`.

## Immutable inputs

- Import and hash-verify the five-model outcome-free score-and-recipe freeze
  `ijds-credit-risk-controls-2026-07-13-v1b`.
- Reconstruct outcomes under the active reason-audited V5 endpoint and verify
  the complete canonical coverage table from
  `ijds-credit-risk-controls-2026-07-15-v5`.
- Retain all 376,890 status-independent primary-OOT candidates from April 2016
  through June 2017, all five learners, all eight six-month residual windows,
  the fixed five-stratum taxonomies, and alpha 0.10.
- Do not refit, recalibrate, retaxonomize, select, widen, or otherwise change a
  score or conformal recipe.

## Complete diagnostics

For every one of the 40 learner-window cells, report the canonical binary set

\[
S_i=\{y\in\{0,1\}:|y-p_i|\le c_{g(i)}\}
   =[\ell_i,u_i]\cap\{0,1\},
\]

and the following quantities:

1. average set size, `AvgC = mean(|S_i|)`;
2. singleton share, `OneC = mean(1{|S_i|=1})`;
3. empty, `{0}`, `{1}`, and `{0,1}` shares over every candidate;
4. resolved-case marginal coverage; and
5. resolved-label descriptive coverage separately for `Y=0` and `Y=1`.

The two label-specific quantities condition on the reconstructed resolved
panel. They are not all-candidate sharp bounds, label-conditional conformal
guarantees, equalized coverage constraints, or evidence about unresolved-label
prevalence.

## Reconciliation and stop rules

1. Stop if the source hashes, run identities, endpoint contract, issue-month
   set, learner-window grid, or candidate/resolved/unresolved census changes.
2. Recompute and match, within machine tolerance, every active canonical
   resolved-coverage value, interval width, and binary-set share before
   publishing any added diagnostic.
3. Require the binary-set shares to partition one and require
   `AvgC = OneC + 2 * both_share = 1 - empty_share + both_share` in every cell.
4. Report all 40 cells. Do not promote a learner, window, class, or efficiency
   metric because it looks favorable.
5. If the label-specific patterns differ by learner or window, report their
   complete ranges; do not average away the heterogeneity.
6. No result authorizes selected-set or funded-set validity, a latent-PD
   confidence interval, model selection, causal interpretation, deployment,
   or a fairness conclusion.

## Output contract

The runner writes one fresh parquet table, one summary, and one execution
receipt under isolated run directories. Outputs are immutable, hash-described,
and DVC-tracked before paper-facing registration. The active evidence builder
may consume the summary only after registry, claim-boundary, and publication
integrity checks are updated.
