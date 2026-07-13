# IJDS normalized-score and objective-matched frontier V1c protocol

## Status and lineage

V1c is the second outcome-free numerical erratum of the locked two-ruler
challenger. No archive outcome has been loaded in V1, V1b, or the diagnostics
that motivated V1c. The complete lineage is:

1. V1 stopped because a slack-floor score span was not a valid exact-tie test.
2. V1b replaced that proxy with nonbasic reduced costs and reversed-ID order.
3. V1b then stopped because final validation required a budget residual below
   `USD 1e-6`, while both solver wrappers accepted residuals through
   `USD 1e-4`.

The exact records are:

- `docs/research/ijds_normalized_objective_frontier_v1_stop_2026-07-13.md`;
- `docs/research/ijds_normalized_objective_frontier_v1b_protocol_2026-07-13.md`;
- `docs/research/ijds_normalized_objective_frontier_v1b_stop_2026-07-13.md`.

V1c is not a pristine preregistration, a conformal repair, or a submission
freeze. V4 remains active until a completed outcome-free freeze and a separate
outcome evaluator satisfy the promotion contract.

## Single V1c correction

The final census budget tolerance is `USD 1e-4`, identical to the hard
reconciliation check already used by `PointPortfolioSession` and
`ObjectiveFloorPortfolioSession`. On a USD 1 million monthly budget this is a
relative tolerance of `1e-10`. The stopped V1b maximum was `USD 6.366e-6`.

V1c does not round, rescale, or repair allocations after optimization. It only
uses one internally consistent acceptance threshold for the same recomputed
sum of funded exposures.

## Unchanged contract

Everything else in V1b remains locked:

- the hash-verified V4-v1 parent and four-column raw allowlist;
- eight residual windows, 11 development menus, and 15 OOT menus;
- `gamma={0,.25,.50,.75,1}` and coordinates `{.25,.50,.75}`;
- objective-matched primary and normalized-score secondary rulers;
- exactly 6,240 solves, 720 endpoint comparisons, 1,440 endpoint order reruns,
  288 GLOP validations, and 26 objective-optimum basis diagnostics;
- reduced-cost threshold `1e-7`, order exposure threshold `1e-10`, order
  objective threshold `USD 1e-5`, cap residual `1e-8`, objective-floor mismatch
  `USD 1e-5`, and HiGHS--GLOP tolerances `1e-7`;
- outcome-free stop on incomplete cells, empty ranges, near-zero reduced costs,
  order sensitivity, solver mismatch, or a fully degenerate ruler; and
- no winner, selector, causal effect, conformal repair, selected-set validity,
  equal-risk claim, or submission freeze.

The future V2 contrast remains `gamma=1 - gamma=0` over every predeclared
window, coordinate, ruler, and metric. No majority vote or favorable subset may
be promoted.
