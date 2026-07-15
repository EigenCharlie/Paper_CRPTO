# IJDS Portfolio-Structure Sensitivity V3 Execution Amendment

V3 inherits every scientific choice, numerical tolerance, claim boundary, and
stop rule from the locked V2 protocol. No outcome was inspected to make this
amendment. The only change is execution architecture.

- Spawn ten independent workers on the 12-core host.
- Keep each HiGHS solve at one thread.
- Read the 1.77 GB raw archive once in the parent, persist its explicit
  outcome-free decision allowlist as a hash-recorded Parquet artifact, and
  load that compact artifact once per worker.
- Assign each complete scenario to exactly one worker.
- Write each scenario only to its own directory.
- Consolidate artifacts in sorted scenario-ID order after all 36 workers'
  tasks succeed.
- Preserve the hard no-overwrite rule and stop on any worker exception,
  identity mismatch, missing scenario, or hash mismatch.

Parallel scheduling cannot select a scenario or change a scenario's inputs,
solver settings, validation, output schema, or hash. The scientific protocol
remains the V2 protocol.

Required tag: `protocol/ijds-portfolio-structure-sensitivity-2026-07-15-v3`.
