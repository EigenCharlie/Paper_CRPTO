# IJDS Decision-Active Simulation Results

## Status and boundary

This is pre-freeze synthetic mechanism evidence from the protocol tagged
`protocol/ijds-decision-active-simulation-2026-07-12-v1` at commit `acbe65e`. It is not empirical sign
validation and does not modify the active V4 claim registry. All 72 cells and
3,600 repetitions are retained.

## Structural result

- Every guardrail cap binds; maximum absolute slack is
  `4.441e-16`.
- Maximum absolute budget residual is
  `1.421e-14` and maximum C2 moment
  residual is `1.665e-16`.
- C0 changes `3600` of 3,600 allocations. C2 changes
  `1866` of 3,600, including every five-stratum cell.
- With one stratum, C2 changes only `66` of
  1,800 allocations because the effective score is nearly a common monotone
  transformation of point PD. With five strata, group-specific residual
  quantiles alter ordering and activate C2.

## Coverage mechanism

At zero score and calibration shift, mean complete-outcome coverage is
`0.900767` for one stratum and
`0.900617` for five. A log-odds
calibration shift of 1.5 lowers those means to
`0.696717` and
`0.735733`. Under a score
shift of 0.08 with no calibration shift, five strata recover mean coverage
`0.909667` only with mean interval
width `0.919819` and both-outcome set share
`0.391133`. Coverage and informativeness
must therefore be reported together.

## Comparator result

C0 is a positive control, not a neutral baseline. Copying the effective-score
cap onto point PD weakly enlarges the feasible set and leaves positive mean
slack in `11` of 12 allocation cells. Mean
slack ranges between `0.000000` and
`0.299752` across the reported cells. C2 removes
that funded point-moment difference, but realized payoff, default, and
miscoverage directions still reverse across cells. At 15 percent censoring,
sharp bounds cross zero in most C2 contrasts. No universal simulated economic
direction is allowed.

## Consequence for the manuscript

The earlier V4 simulation remains valid negative provenance but is no longer
the best decision-mechanism experiment: its cap was slack. This locked run can
replace that degenerate portfolio subsection while preserving the boundary that
synthetic signs do not validate Lending Club. Its strongest contribution is
mechanistic: decision activation, taxonomy-dependent ordering, and comparator
semantics are distinct from candidate coverage.
