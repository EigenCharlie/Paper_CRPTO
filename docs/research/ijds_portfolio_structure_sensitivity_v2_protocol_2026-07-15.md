# IJDS Portfolio-Structure Sensitivity V2 Protocol

## Question

Does the active conclusion that portfolio direction is not universally
favorable depend on the stylized LGD, the purpose-concentration limit, or the
monthly budget?

## Retrospective Boundary

The archive, active endpoint results, baseline binding diagnostics, and one
failed V1 structural execution were already inspected. This is a complete
retrospective assumption sensitivity. It is not preregistration, prospective
confirmation, model selection, policy selection, or scenario selection.

V1 stopped before writing an artifact in scenario `b0500k_p020_l025`. A
separate outcome-free diagnostic found 25 exact-minimum failures among 600
window-month-gamma cells, all in October 2016. The menu had USD 1.2 million of
purpose-capped capacity for a USD 0.5 million budget, and every failed cell
resolved after adding `1e-14` to the score cap. The failure was therefore an LP
boundary reconciliation issue, not evidence that the economic constraints
were infeasible.

## Locked Numerical Amendment

- First solve the exact minimum cap without adjustment.
- Retry only `Infeasible` or budget-reconciliation failures at that exact
  minimum endpoint.
- The sole retry is `minimum_score + 1e-12`.
- The retry is forbidden for every other exception and is 10,000 times smaller
  than the locked `1e-8` cap-residual tolerance.
- Persist every retry indicator, applied slack, and achieved cap residual for
  all five gamma states, including the three states used to construct a ruler
  but not reported as endpoint policies.
- Stop if a retried endpoint exceeds the cap-residual tolerance.

No outcome was used to choose or tune this numerical amendment.

## Locked Outcome-Free Grid

- Budgets: USD 0.5, 1, and 2 million.
- Maximum purpose shares: 0.20, 0.25, 0.30, and 1.00.
- LGD: 0.25, 0.45, and 0.65.
- Report the complete 36-cell Cartesian product.
- Preserve all five gamma states when constructing each common ruler range,
  but materialize only the frozen `gamma=1` versus `gamma=0` endpoint contrast.
- Preserve both rulers, coordinates 0.25/0.50/0.75, all eight windows, and all
  fifteen primary-OOT monthly menus.
- Rebuild allocations without any outcome column. Join the declared six-month
  endpoint only after every scenario artifact is hash frozen.

## Interpretation Rule

No scenario may be promoted. A conclusion is structurally robust only if it is
supported by the complete grid. Standardized payoff remains a stylized
one-period payoff, not cash-flow return, IRR, NPV, welfare, or a lending
recommendation. Removing the purpose cap is a stress specification, not a
deployable policy recommendation.

Required tag: `protocol/ijds-portfolio-structure-sensitivity-2026-07-15-v2`.
