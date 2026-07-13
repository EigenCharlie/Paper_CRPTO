# IJDS normalized/objective frontier V1b outcome-free stop

## Status

The tagged V1b run under
`protocol/ijds-normalized-objective-frontier-2026-07-13-v1b` completed all eight
frontier windows but stopped during final outcome-free validation. It created no
data or model output directory and never joined an outcome.

## Exact stop

V1b started from clean tagged commit `cb6b7ba`. All 6,240 frontier cells and
their diagnostics were constructed in memory. The final maximum recomputed
budget residual was `USD 6.366e-6`, above the separately configured V1b stop of
`USD 1e-6`. Elapsed wall time was 3,345.8 seconds.

The observed residual is approximately `6.4e-12` of the USD 1 million monthly
budget. Both portfolio session implementations already reject a solution only
when the recomputed budget differs by more than `USD 1e-4`. V1b therefore used
two inconsistent definitions of numerical budget feasibility: `1e-4` inside
the solver wrappers and `1e-6` in final census validation.

## Consequence

V1b remains immutable and failed. V1c aligns the final budget-reconciliation
threshold with the pre-existing solver-wrapper threshold of `USD 1e-4`. This is
`1e-10` of the monthly budget and does not change an LP, allocation, frontier
coordinate, endpoint, outcome rule, or claim boundary. Every other V1b
tolerance and stop remains unchanged.

The correction receives a new config, commit, protocol tag, run tag, and fresh
output directories. It is a numerical-contract erratum before outcomes, not a
retrospective empirical adjustment.
