# IJDS Rolling-Origin Stability Results

## Status

This is a locked retrospective robustness audit, not a new active claim registry,
prospective validation, or submission freeze.

## Feasibility

The 2015 origin is infeasible under the unchanged five-stratum Mondrian
requirement. Its first residual window has group counts
`(1648, 1408, 1166, 927, 619)` against a minimum of 1,000. The protocol
was not relaxed, and no 2015 outcome join occurred.

## Common-Horizon Coverage

- 2016 CatBoost/Platt: 0.860861--0.874626 resolved; bounds 0.860861--0.874626.
- 2016 logistic/Platt: 0.868629--0.888619 resolved; bounds 0.868629--0.888619.
- 2017 CatBoost/Platt: 0.853436--0.855898 resolved; bounds 0.732923--0.876247.
- 2017 logistic/Platt: 0.855430--0.857242 resolved; bounds 0.734635--0.877401.

Every upper bound is below 0.90 in both feasible origins and all eight
windows. This is recurrence across two fitted origins, not three-origin
stability, because the 2015 design is infeasible.

## Comparator Identification

Development-supported envelope direction counts:

| Origin | Metric | Guardrail lower | Crosses zero | Guardrail higher |
|---:|---|---:|---:|---:|
| 2016 | funded_miscoverage | 8 | 10 | 54 |
| 2016 | standardized_payoff | 32 | 32 | 8 |
| 2016 | terminal_default | 7 | 42 | 23 |
| 2017 | funded_miscoverage | 0 | 56 | 16 |
| 2017 | standardized_payoff | 0 | 72 | 0 |
| 2017 | terminal_default | 0 | 64 | 8 |

No metric has one identified direction in every window-policy cell at either
origin. The rolling audit therefore strengthens comparator dependence and does
not revive a policy-winner claim.

## Simulation Audit

The inherited factorial has 19,200 repetitions,
but same-cap allocations change in only 2 and C2
allocations in only 1.
The guardrail score cap is slack in every repetition. The block remains useful
for binary coverage geometry but is decision-degenerate and cannot support a
portfolio claim.

## Consequence

The result supports a stronger audit narrative: below-target candidate coverage
recurs under two feasible calendar origins, feasibility itself is origin-dependent,
and portfolio direction remains comparator-dependent. It does not establish
selected-set validity, universal temporal failure, or guardrail superiority.
