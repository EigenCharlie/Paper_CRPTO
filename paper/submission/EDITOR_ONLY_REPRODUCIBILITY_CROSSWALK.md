# Editor-Only Reproducibility Crosswalk

**Confidential:** this file contains public-searchable identifiers and must not
be uploaded as reviewer-facing material.

## Outcome-Free Freeze

| Item | Exact value |
|---|---|
| Run | `ijds-fixed-taxonomy-c2-2026-07-11-v1` |
| Protocol tag | `protocol/ijds-fixed-taxonomy-c2-2026-07-11-v1` |
| Protocol commit | `4835cc18a0117a695f89f9da70a4e3af97663a27` |
| Protocol-freeze SHA-256 | `93690082880ef4ff1375dcd5b26d2df79f80e6ebe09a6d83b7fd99a9abb4cfae` |
| Processed-data DVC MD5 | `25ffeeb670487db5b696b32fc129dc4b.dir` |
| Model/allocation DVC MD5 | `f31feb6e61c015f5ef3191c16d764576.dir` |

V1 completed every outcome-free task: the canonical panel, five models, fixed
taxonomies, 7,347 solve records, and 718,925 funded allocation rows. The
original evaluator did not complete within its execution window. An
`INCOMPLETE_RUN.json` marker records that state; V1 is not represented as a
complete outcome evaluation.

## Reconciled Evaluation

| Item | Exact value |
|---|---|
| Run | `ijds-fixed-taxonomy-c2-2026-07-11-v2` |
| Protocol tag | `protocol/ijds-fixed-taxonomy-c2-2026-07-11-v2` |
| Protocol commit | `a88839dfe14875fca2c02c43725291bc49d98611` |
| Protocol-freeze SHA-256 | `f6489dd0d90bb7e8128ba4084ee8124024afa764ab097295db87ee87c6e0d40e` |
| Deterministic-summary SHA-256 | `b471629a23b07a97273850af9a192201557fd365467d99e6b3740eb8281864e8` |
| Execution-receipt SHA-256 | `de4fe7299bd651425dbac167d9cb0b5b9e3a1bda0db4bf3fd7a27ae1d313a192` |
| Processed-evaluation DVC MD5 | `609089f4960782bd4ce157ffe85a74ce.dir` |
| Result/receipt DVC MD5 | `c132326dc57d332b502b026813690e2f.dir` |
| Evidence manifest | `reports/crpto/ijds_fixed_taxonomy_c2_evidence.json` |

V2 verifies the V1 protocol identity, implementation descriptors, models,
recipes, panels, and allocations before reusing only outcome-free objects. It
performs one vectorized outcome join and generates 7,347 monthly evaluations,
515 aggregates, 504 paired contrasts, 594 coverage rows, and 800 simulation
repetitions.

## Reviewer Labels

Anonymous files use prose labels such as *outcome-free freeze* and *reconciled
evaluation*. They omit run names, tags, commits, hashes, DVC fingerprints,
remote coordinates, and machine paths. This crosswalk is the only submission
surface that maps those neutral labels to exact identifiers.

## Reproduction Sequence

```powershell
uv sync --extra dev
uv run dvc pull data/processed/experiments/ijds_prefreeze/ijds-fixed-taxonomy-c2-2026-07-11-v1.dvc
uv run dvc pull models/experiments/ijds_prefreeze/ijds-fixed-taxonomy-c2-2026-07-11-v1.dvc
uv run dvc pull data/processed/experiments/ijds_prefreeze/ijds-fixed-taxonomy-c2-2026-07-11-v2.dvc
uv run dvc pull models/experiments/ijds_prefreeze/ijds-fixed-taxonomy-c2-2026-07-11-v2.dvc
just ijds-evidence
just submission-check
```

Neither sequence invokes or writes a manifest-protected historical stage.
`EXTRACTION_MANIFEST.json` is not modified. Full methodology replay, if an
editor requests it, must use a new run tag and fresh output paths.
