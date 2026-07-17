# Binary-Geometry V4 V2 Evaluation Recovery

## Status

V4-v1 completed its outcome-free freeze at commit
`2f8a7606e4eb65aa3ae3701fb3af8d9a51c953cd`. An external pre-evaluation
audit found 1,872 guardrail solves, 1,080 C2 solves, a maximum absolute C2
match residual of `8.33e-17`, no forbidden outcome columns, and complete
eight-window/nine-policy cardinality. Its `protocol_freeze.json` SHA-256 is
`c2b3dc2d18c9fed80708682d5a0369c80c89643e2d28024418522d954ebe667c`.

A no-write post-freeze smoke test then exposed an evaluation-only dataframe
collision. Shared frontier rows intentionally lacked window-specific
conformal endpoints, but concatenation with other allocation rows retained
all-null endpoint columns. Merging the selected window's endpoints therefore
created pandas suffixes instead of canonical `conformal_lower` and
`conformal_upper` columns. No evaluation artifact or deterministic summary
was written.

## V2 Rule

V4-v2 changes no scientific specification, model, score, residual recipe,
window, policy, comparator, frontier, simulation, outcome, hypothesis, or
stop rule. It:

1. imports the V4-v1 outcome-free freeze only after verifying its identity,
   SHA-256, and every artifact descriptor;
2. drops any placeholder window-specific endpoint columns before injecting
   the chosen window recipe; and
3. writes all evaluation outputs under the fresh V4-v2 run directory.

The imported allocations remain frozen before outcomes. V4-v1 is preserved
as valid outcome-free provenance but is not an evaluable final run. Required
V4-v2 tag:
`protocol/ijds-binary-geometry-frontier-v4-2026-07-12-v2`.
