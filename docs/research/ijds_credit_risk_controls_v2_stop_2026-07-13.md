# IJDS Credit-Risk Controls V2 Numerical Stop - 2026-07-13

## Status

V2 completed the frozen outcome join and its coverage, discrimination, loss,
and censoring outputs are valid. It is not promoted to paper-facing evidence
because BFGS returned `success=false` for 17 of 30 otherwise finite calibration
intercept/slope fits under an unnecessarily strict gradient tolerance.

## Preserved Result

The 3,520-row temporal-coverage artifact is frozen under SHA-256
`956bdc9880c80cebc1f48fc2cdf57688dfff7dddd3939b4fd972413d83039767`.
V2b must reproduce this frame exactly, including row order, values, dtypes, and
shape. No score, recipe, outcome, coverage cell, learner, or window may change.

## Recovery

V2b replaces only the two-parameter calibration diagnostic solver with
unpenalized scikit-learn logistic regression and fails on nonconvergence. It
also preindexes the immutable fit audit to remove repeated full-frame scans.
The optimization is accepted only after exact V2 coverage equivalence; it does
not alter the scientific model or react to result direction.
