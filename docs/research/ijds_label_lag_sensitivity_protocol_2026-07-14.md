# IJDS Label-Lag Sensitivity Protocol

## Question

Does the empirical W7-W8 phase crossing survive plausible alternatives to the
six-month rule used to date a Charged Off label, and which alternatives still
satisfy the locked greater-than-99% monthly label-retention requirement?

## Locked Design

- Use the hash-verified V4-v1 CatBoost scores and 2011 taxonomy edges.
- Refit only the eight binary conformal residual recipes.
- Evaluate charge-off reporting lags of 0, 3, 6, 8, and 12 months.
- Report every lag and every window. Stratum 2 is the pre-existing phase
  diagnostic; no lag or window may be selected from the results.
- Record retained rows, minimum monthly retention, phase-stratum prevalence,
  residual quantile, mean interval width, and `{0,1}` share.
- A lag passes the inherited maturity rule only when every residual month has
  retention strictly above 0.99.

The archive and the six-month result were previously inspected. This is a
retrospective assumption sensitivity, not preregistration or independent
confirmation. No portfolio allocation or OOT outcome enters the run.

## Paper Rule

If the W7-W8 jump changes materially under any plausible lag, the finite-sample
observation must be described as lag-sensitive and illustrative. The
constant-score population proposition may remain as algebra, but the empirical
crossing cannot be described as a causal explanation or robust phase estimate.

Required tag: `protocol/ijds-label-lag-sensitivity-2026-07-14-v1`.
