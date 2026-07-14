# IJDS V3 Evaluation and Endpoint Recovery Protocol

## Status

This is a locked, evaluation-only recovery of the V4 portfolio audit and the
five credit-risk coverage controls. It may import only the hash-verified V4-v1
and credit-controls-v1b outcome-free freezes. It does not refit a learner,
change a residual recipe, alter a policy or comparator, select a window, or
inspect outcomes during construction.

V2 remains immutable provenance. V3 writes to fresh run directories and is the
only candidate lineage for subsequent paper-facing evidence.

## Defects Being Corrected

The V2 candidate-coverage aggregation assigned every unresolved binary outcome
to failure for the lower endpoint and success for the upper endpoint. That is
conservative but not sharp when a prediction set is empty or contains both
binary outcomes. For observed covered count `O`, unresolved count `U`,
unresolved always-covered count `B`, unresolved never-covered count `E`, and
candidate count `N`, V3 uses

`coverage_lower = (O + B) / N`

and

`coverage_upper = (O + U - E) / N`.

The distributed archive is also not established as a September 30, 2020
point-in-time status snapshot. V3 therefore does not use final terminal status
merely because it appears in the archive. It retains a terminal label only when
the declared conservative availability date is no later than September 30,
2020: last-payment month-end for Fully Paid and last-payment month-end plus six
months for Charged Off. All other rows remain unresolved. This is a
reconstruction rule, not a claim about the archive's actual publication date or
the exact operational charge-off date.

## Locked Inputs

- V4 outcome-free freeze: run
  `ijds-binary-geometry-frontier-v4-2026-07-12-v1`, SHA-256
  `c2b3dc2d18c9fed80708682d5a0369c80c89643e2d28024418522d954ebe667c`.
- Credit-control freeze: run `ijds-credit-risk-controls-2026-07-13-v1b`,
  SHA-256
  `da4805e644bcf5decfbb0a67c0c81a5b9dd61f3ab2e17d3dc5264100e7eb4d35`.
- Raw archive, design universe, scores, recipes, allocations, comparator
  support, payoff, and solver settings remain unchanged.

## Required Reconciliation

1. Frozen artifact hashes and cardinalities must match their source freezes.
2. Scores, recipes, fit audits, solve records, allocations, and comparator
   support must be byte-identical imports.
3. Coverage geometry and candidate counts must match V2; only endpoint
   observability and the two all-candidate bound columns may change.
4. Every changed resolved label must have `label_available_at` after the cutoff.
5. Portfolio allocations must remain unchanged. Any metric movement must be
   attributable solely to endpoint reconstruction.
6. All five learners and all eight windows remain co-primary; no model, window,
   ruler, coordinate, or policy may be selected from V3 outcomes.

## Stop and Interpretation Rules

- If any learner-window sharp upper coverage endpoint reaches 0.90, the paper
  must withdraw the universal all-model/all-window nontransport statement and
  report the complete mixed result.
- If portfolio direction changes under the reconstructed endpoint, both V2 and
  V3 directions must be reported and no direction may be promoted.
- The six-month charge-off lag remains a modeling assumption. Its sensitivity
  must be reported, and the W7-W8 empirical crossing may not be described as a
  causal mechanism.
- V3 cannot authorize a winner, causal effect, selected-set guarantee,
  prospective guarantee, or deployment claim.

Required tags are
`protocol/ijds-binary-geometry-frontier-v4-2026-07-14-v3` and
`protocol/ijds-credit-risk-controls-2026-07-14-v3`.
