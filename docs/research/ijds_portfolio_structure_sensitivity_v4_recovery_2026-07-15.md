# IJDS Portfolio-Structure Sensitivity V4 Recovery Amendment

V4 inherits the complete scientific and numerical protocol from V2 and the
parallel execution architecture from V3. The V3 parent process was externally
interrupted before consolidation, after 29 scenario directories had completed
and before any outcome join or `protocol_freeze.json` write. Seven scenario
directories were absent. No result from a structural outcome evaluation
existed or was inspected.

V4 may recover only the 29 scenario identities locked in the V4 configuration.
For every recovered scenario it must verify:

- the exact seven-file Parquet inventory;
- the locked row counts for all fixed-cardinality artifacts;
- one and only one matching scenario ID in every artifact;
- absence of endpoint/outcome columns;
- retry slack in `{0, 1e-12}` and cap residual at most `1e-8`;
- fresh SHA-256 descriptors for source and destination files.

Only after those checks may V4 create same-volume NTFS hard links in a fresh
V4 run directory. Hard links preserve bytes but do not make an unvalidated V3
directory evidence. V4 recomputes the seven absent scenarios with seven
single-thread workers, independently inspects them under the same contract,
and writes one consolidated freeze only after all 36 identities are present.

This amendment changes neither a portfolio input nor a solver call. It cannot
select a scenario, model, ruler, coordinate, metric, or endpoint.

Required tag: `protocol/ijds-portfolio-structure-sensitivity-2026-07-15-v4`.
