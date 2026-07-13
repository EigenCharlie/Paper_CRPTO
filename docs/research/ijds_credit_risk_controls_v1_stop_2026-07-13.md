# IJDS Credit-Risk Controls V1 Technical Stop - 2026-07-13

## Status

V1 is stopped and cannot support a scientific result. No primary-OOT outcome
evaluation was run and no partial score, IV, PSI, coverage, or model metric was
inspected.

## Failure

The tagged V1 implementation completed model fitting and reached artifact
serialization. PyArrow rejected the OptBinning aggregate `Totals` row because
the `WoE` column mixed numeric bin values with an empty string. A valid
`protocol_freeze.json` was never written.

## Recovery Boundary

V1b changes only the diagnostic table representation: known numeric bin-table
columns are coerced with invalid aggregate placeholders represented as missing
numeric values. A synthetic test must serialize the complete table to Parquet.
The five learners, feature lists, monotonic constraints, OptBinning options,
row universe, temporal splits, taxonomies, residual windows, and stop rules are
unchanged. V1 partial directories are removed after recording this stop and
must never be resumed or evaluated.
