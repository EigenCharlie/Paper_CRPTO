# Editor-Only Reproducibility Crosswalk

Do not include this file in the anonymous reviewer packet. It maps neutral
review labels to searchable repository identifiers.

## Active Outcome-Free Freeze

| Field | Exact value |
|---|---|
| Reviewer label | Outcome-free freeze |
| Run | `ijds-binary-geometry-frontier-v4-2026-07-12-v1` |
| Protocol tag | `protocol/ijds-binary-geometry-frontier-v4-2026-07-12-v1` |
| Protocol commit | `2f8a7606e4eb65aa3ae3701fb3af8d9a51c953cd` |
| Freeze SHA-256 | `c2b3dc2d18c9fed80708682d5a0369c80c89643e2d28024418522d954ebe667c` |
| Data pointer | `data/processed/experiments/ijds_audit/ijds-binary-geometry-frontier-v4-2026-07-12-v1.dvc` |
| Model pointer | `models/experiments/ijds_audit/ijds-binary-geometry-frontier-v4-2026-07-12-v1.dvc` |

The freeze contains two learner score vectors, 64 residual recipes, 51,117
solve records, 5,001,617 funded rows, 1,872 guardrail solves, 1,080 C2 solves,
72 development supports, and 46,005 monthly frontier rows. It contains no
forbidden OOT outcome column.

## Active Evaluation

| Field | Exact value |
|---|---|
| Reviewer label | Reconciled evaluation |
| Run | `ijds-binary-geometry-frontier-v4-2026-07-12-v2` |
| Protocol tag | `protocol/ijds-binary-geometry-frontier-v4-2026-07-12-v2` |
| Protocol commit | `60cdf298d965525cddaaf03abccd15ff805e1a15` |
| Summary SHA-256 | `1483713ce410a07851047f60b483774b866dfdbe864ea525a9cf098ad5ff8647` |
| Evaluation freeze SHA-256 | `2293424cad97a9e4dad81c0efe3a2c4d23067b9d35f53d0e0b1bfc3d48478994` |
| Data pointer | `data/processed/experiments/ijds_audit/ijds-binary-geometry-frontier-v4-2026-07-12-v2.dvc` |
| Model pointer | `models/experiments/ijds_audit/ijds-binary-geometry-frontier-v4-2026-07-12-v2.dvc` |

The evaluator verifies the complete V1 freeze and imports only outcome-free
objects. It removes all-null shared-frontier endpoint placeholders before
injecting window-specific endpoints. No scientific specification or allocation
changes between phases.

## Two-Ruler Outcome-Free Freeze

| Field | Exact value |
|---|---|
| Reviewer label | Two-ruler outcome-free freeze |
| Run | `ijds-normalized-objective-frontier-2026-07-13-v1c` |
| Protocol tag | `protocol/ijds-normalized-objective-frontier-2026-07-13-v1c` |
| Protocol commit | `46f4df915d38eb5a6cc144484c6e6fe56d8ed397` |
| Freeze SHA-256 | `7877c5e460772a0093e4132eaa542e9049f7ec15d2ddaa35c2df389892a0e185` |
| Data pointer | `data/processed/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v1c.dvc` |
| Model pointer | `models/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v1c.dvc` |

The freeze contains 6,240 solves, 622,455 funded rows, 720 endpoint
comparisons, 1,440 reversed-ID reruns, 288 GLOP validations, and 26
objective-optimum diagnostics. It contains no outcome column.

## Two-Ruler Evaluation

| Field | Exact value |
|---|---|
| Reviewer label | Two-ruler reconciled evaluation |
| Run | `ijds-normalized-objective-frontier-2026-07-13-v2` |
| Protocol tag | `protocol/ijds-normalized-objective-frontier-2026-07-13-v2` |
| Protocol commit | `d3041e5233ee74a6b1d38f678def75d8d5ef0169` |
| Manifest SHA-256 | `d3808ce7c7a8e6fee3ef51aefd031e8abf55e11ef3536745ee213fd04752588a` |
| Summary SHA-256 | `1dbfb2652d5bd2f9a1478ca10bbc829c9bcd0cf847a9e179454b3f2c629beb03` |
| Receipt SHA-256 | `3ef3e7c7e363bcf8630ae79cabe2847f5b70bc66416f384c043c16cef2b46ca8` |
| Data pointer | `data/processed/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v2.dvc` |
| Model pointer | `models/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v2.dvc` |

One invocation produced the immutable artifact set. A client timeout caused a
second fixed evaluation in memory; it stopped at no-overwrite and wrote no
artifact.

## Paper-Facing Evidence

| Field | Exact value |
|---|---|
| Manifest | `reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json` |
| Builder | `scripts/build_ijds_binary_geometry_frontier_v4_evidence.py` |
| Table prefix | `reports/crpto/tables/crpto_ijds_v4_` |
| Figure prefix | `reports/crpto/figures/crpto_ijds_v4_` |
| Outputs | one manifest, six CSV tables, three PNG figures, three PDF figures |

Every paper-facing descriptor is verified by SHA-256. Two consecutive evidence
builds must be byte-identical.

## Reproduction Sequence

```powershell
uv sync --frozen --extra dev --extra search --extra spo
uv run dvc pull data/processed/experiments/ijds_audit/ijds-binary-geometry-frontier-v4-2026-07-12-v1.dvc
uv run dvc pull models/experiments/ijds_audit/ijds-binary-geometry-frontier-v4-2026-07-12-v1.dvc
uv run dvc pull data/processed/experiments/ijds_audit/ijds-binary-geometry-frontier-v4-2026-07-12-v2.dvc
uv run dvc pull models/experiments/ijds_audit/ijds-binary-geometry-frontier-v4-2026-07-12-v2.dvc
uv run dvc pull data/processed/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v1c.dvc
uv run dvc pull models/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v1c.dvc
uv run dvc pull data/processed/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v2.dvc
uv run dvc pull models/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v2.dvc
just ijds-active-check
just paper-submission
just paper-submission-official
```

Neither sequence invokes a protected historical stage or writes
`EXTRACTION_MANIFEST.json`. A full methodology rerun must use a fresh run tag
and output roots. The maintainer separately runs `just submission-check`, whose
strict champion gate requires the historical manifest artifacts to exist but
does not reproduce them.

## Reviewer Labels

Anonymous files use prose labels such as *outcome-free freeze* and *reconciled
evaluation*. They omit run names, tags, commits, hashes, DVC fingerprints,
remote coordinates, and machine paths. This crosswalk is the only submission
surface that maps those labels to exact identifiers.
