# IJDS Full-Archive Data-Contract Results - 2026-07-13

## Result

The active V4 research object already uses every eligible record under its
36-month, maturity-safe, temporally separated estimand. It does not use a row
sample. Expanding mechanically to every row or every raw column would mix loan
horizons, unavailable outcomes, and schema eras rather than improve power or
generalization.

## Complete Archive

- Raw rows: 2,925,493, including one nonloan footer row.
- Valid dated loans: 2,925,492; distinct nonblank IDs: 2,925,493.
- First and last issue months: June 2007 and September 2020.
- 36-month loans: 2,060,077; 60-month loans: 865,415.
- Exact statuses include 1,497,783 `Fully Paid`, 362,548 `Charged Off`, and
  1,031,016 `Current`. An additional 1,988 fully paid and 761 charged-off loans
  carry the historical “does not meet credit policy” status prefix.

The 60-month population cannot be appended to the active one-period 36-month
payoff and maturity contract. It requires a different horizon, information
cutoff, cash-flow treatment, and OOT design.

## Exhaustive 36-Month Partition

| Role | Rows |
|---|---:|
| PD development | 17,433 |
| Probability calibration | 14,101 |
| Conformal residual pool | 49,007 |
| Policy development | 94,885 |
| Primary OOT | 376,890 |
| Censored extension | 88,227 |
| Maturity gap | 541,863 |
| Post-extension | 877,671 |

The six active design roles contain 640,543 loans. The remaining 36-month rows
are accounted for explicitly; none disappear through random or convenience
sampling.

## Why The Maturity Gap Is Not Extra Training Data

At the March 31, 2016 information cutoff, only 59,910 of 162,570 2014 loans
(36.85%), 28,878 of 283,173 2015 loans (10.20%), and 1,110 of 96,120 first-
quarter 2016 loans (1.15%) have observable labels under the declared reporting
lag. The 2016 observable subset contains no bad outcome. Treating these early
resolutions as ordinary terminal labels would select on duration and outcome.

A survival or censoring-aware target could use this block, but it would change
the estimand and require a new payoff and conformal construction. It is not a
free increase in sample size for the current paper.

## Raw Feature Availability

The CSV has 142 columns. The temporal contract classifies 28 raw candidates as
eligible after role and coverage checks and identifies 48 late-schema fields
with less than 50% fitting-era coverage but at least 80% primary-OOT coverage.
Many modern bureau aggregates are essentially absent in 2007--2011 and nearly
complete by 2016--2017. Filling an entirely absent training-era column would
encode schema vintage, not recover borrower information.

Post-outcome payment, recovery, hardship, settlement, last-payment, and last-
FICO fields remain forbidden predictors. Identifiers, free text, and geography
proxies remain outside the active scientific contract.

## Exposure Reconciliation

In primary OOT, requested amount exceeds funded amount by only USD 18,000 over
376,890 candidates. The funded/requested ratio is 0.999996 and only about two
loans are partially funded. Replacing the requested exposure cap with funded
amount cannot materially improve the active OOT portfolio result.

## Actionable Consequence

The justified robustness expansion is across learner assumptions, not through
invalid rows or late columns. The predeclared follow-up therefore reports the
active CatBoost and logistic learners alongside monotonic CatBoost, an
OptBinning WOE/IV scorecard, and a borrower-only scorecard that removes the
platform's grade and pricing signals. All five use the same complete eligible
rows and remain coverage-only controls.

Machine-readable evidence is under
`reports/crpto/data_audit/ijds-raw-data-contract-2026-07-13-v1/`.
