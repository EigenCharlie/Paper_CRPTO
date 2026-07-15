# IJDS Portfolio-Structure Sensitivity V6 Order-Tolerance Amendment

V6 inherits the complete 36-scenario scientific grid from V2, the deterministic
worker architecture from V3, the validated shard-recovery contract from V4,
and the closed minimum-endpoint retry ladder from V5. It changes one numerical
validator only: normalized exposure distance under ID-order reversal increases
from `1e-10` to `1e-8`. The plug-in objective tolerance remains exactly
`USD 1e-5`.

## Outcome-free basis for the amendment

V5 physically completed 35 scenario shards but stopped before consolidation
and before any endpoint join. Its missing `b0500k_p020_l025` scenario reached
all eight residual windows and failed one order-invariance check. A diagnostic
reran that scenario while bypassing only the final validator and joined no
outcome columns. Across 1,440 order-audit rows it found:

- maximum normalized exposure distance `1.3504744038073114e-10`;
- eight rows above `1e-10`, all repetitions of the same October 2016,
  normalized-score, coordinate-.25, gamma-0 endpoint;
- zero rows above `1e-8`;
- maximum absolute plug-in objective difference
  `USD 0.000007320079021155834`, below `USD 1e-5`;
- maximum absolute weighted-score difference `3.62847252244336e-12`.

These discrepancies are solver-scale numerical variation, not evidence of a
materially different optimal allocation. The amended exposure tolerance equals
the already locked cap-residual tolerance and remains roughly 74 times larger
than the diagnosed maximum. The objective check is not relaxed.

## Recovery and stop contract

V6 may recover exactly the 35 physical V5 shards after checking their complete
seven-file inventories, fixed row counts, scenario identities, retry slacks,
cap residuals, hashes, and absence of outcome columns. It recomputes only
`b0500k_p020_l025` with one single-thread worker. It writes a consolidated
outcome-free freeze only after all 36 scenario identities pass.

V6 stops if the recomputed scenario exceeds `1e-8` normalized exposure
distance, exceeds `USD 1e-5` objective difference, fails the closed endpoint
retry ladder, contains an outcome column, or leaves any grid cell incomplete.
Only a complete hash-frozen grid may proceed to the separately invoked
evaluation phase. Evaluation must report every declared scenario; it cannot
select a budget, purpose cap, LGD, ruler, coordinate, metric, or policy.

This is a retrospective numerical amendment informed by an outcome-free
failure diagnosis. It is not preregistration, confirmation, or a new paper
claim, and it does not create a submission freeze.

Required tag: `protocol/ijds-portfolio-structure-sensitivity-2026-07-15-v6`.
