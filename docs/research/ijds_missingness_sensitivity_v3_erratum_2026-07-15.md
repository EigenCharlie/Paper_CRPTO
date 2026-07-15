# IJDS Missingness Sensitivity V3 Erratum

## Stop Decision

V1 and V2 were stopped before freeze or evaluation. Their proposed native-
missingness arm removed the binary `has_bankruptcy` feature and inserted the
raw `pub_rec_bankruptcies` count. That arm changed both missing-value encoding
and feature semantics, so it could not isolate the declared sensitivity.

No output directory exists for either stopped run. No outcome was inspected to
choose the repair, no protected stage was run, and no protected artifact was
modified.

## Locked V3 Repair

V3 retains all rows, splits, labels, CatBoost parameters, Platt calibration,
taxonomy groups, residual windows, endpoint reconstruction, and evaluation
rules. It changes only the third feature matrix:

- `delinq_recency_native` is the same delinquency-recency source used by the
  active feature, with source missingness retained as `NaN` instead of mapped
  to 999;
- `has_bankruptcy_native` retains the active binary meaning: an observed
  strictly positive count maps to 1 and an observed zero maps to 0, while a
  missing source count remains `NaN`; and
- the raw bankruptcy count is not included.

The complete family remains baseline sentinel, sentinel plus explicit missing
indicators, and native nullable values. The alternatives are coverage controls
for primary CatBoost only. They cannot select a model or encoding, enter
portfolio optimization, identify a missingness mechanism, or support MAR/MNAR
claims.

The fresh tag is
`protocol/ijds-missingness-sensitivity-2026-07-15-v3`. Any implementation,
specification, row-universe, or pre-outcome contract mismatch stops execution
and requires a new tag.
