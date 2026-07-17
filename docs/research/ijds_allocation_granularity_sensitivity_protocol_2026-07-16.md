# IJDS Allocation-Granularity Sensitivity Protocol - 2026-07-16

## Question

Is the continuous dollar-allocation relaxation materially different from a
simple operational allocation expressed in USD 25 lots?

## Locked Design

- Use the complete active baseline structure: USD 1 million monthly budget,
  25% purpose cap, LGD 0.45, both rulers, all three coordinates, both gamma
  endpoints, eight windows, and all fifteen primary OOT months.
- For every positive exposure, apply
  `25 * floor(exposure / 25)` and retain the residual as zero-risk, zero-payoff
  cash. Never round upward and never reoptimize or refill the portfolio.
- Preserve all loan identities, scores, conformal endpoints, contractual rates,
  and the active six-month evaluation endpoint.
- Validate that the transform cannot increase invested capital, score use, or
  purpose concentration and that every retained exposure is a USD 25 multiple.
- Report all 1,440 monthly portfolios and all 96 window-by-candidate tracks.

## Estimands

For each track, report the residual-cash share and sharp
rounded-minus-continuous bounds for status-indexed payoff-proxy rate, weighted
default, and weighted miscoverage. Both policies use the same committed-capital
denominator, so residual cash remains explicit rather than disappearing through
renormalization.

## Interpretation Boundary

This is a deterministic granularity diagnostic, not an integer-programming
challenger, optimized discrete policy, or implementation claim. A small
perturbation supports the numerical adequacy of the continuous relaxation only
for this archive and declared USD 25 floor rule. It cannot select a ruler,
coordinate, gamma endpoint, or portfolio.

## Stop Rules

- Stop on tag, commit, lock, parent hash, portfolio census, period grid, or
  outcome-ID mismatch.
- Stop if rounding increases exposure or violates a risk or purpose constraint.
- Stop if any of the 96 contrast tracks or any bound is absent or nonfinite.
- Report every track regardless of direction.
- Do not execute or overwrite protected historical stages or artifacts.
