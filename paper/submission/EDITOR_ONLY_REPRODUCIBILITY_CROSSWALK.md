# Editor-Only Reproducibility Crosswalk

Do not include this file in the anonymous reviewer archive. It contains
searchable protocol identifiers and immutable provenance.

## Active Authority

| Object | Path |
|---|---|
| Claim registry | `docs/research/active_claims_2026-07-14.md` |
| Source registry | `configs/ijds_active_evidence_sources.yaml` |
| Evidence manifest | `reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json` |
| Body | `paper/CRPTO_ijds.qmd` |
| Supplement | `paper/supplement_ijds.qmd` |
| Generated TeX | `paper/submission/CRPTO_ijds_submission.tex` |

## Immutable Lineages

| Lineage | Outcome-free freeze | Endpoint-corrected evaluation |
|---|---|---|
| Binary geometry / exact support | `ijds-binary-geometry-frontier-v4-2026-07-12-v1` | `ijds-binary-geometry-frontier-v4-2026-07-14-v3` |
| Protocol tags | `protocol/ijds-binary-geometry-frontier-v4-2026-07-12-v1` | `protocol/ijds-binary-geometry-frontier-v4-2026-07-14-v3` |
| Protocol commits | `2f8a7606e4eb65aa3ae3701fb3af8d9a51c953cd` | `688f75dc4f285c75bc499c9e041dd30fb3acd70d` |
| Freeze SHA-256 | `c2b3dc2d18c9fed80708682d5a0369c80c89643e2d28024418522d954ebe667c` | See source registry and execution receipt |
| Two-ruler diagnostic | `ijds-normalized-objective-frontier-2026-07-13-v1c` | `ijds-normalized-objective-frontier-2026-07-14-v3` |
| Protocol tags | `protocol/ijds-normalized-objective-frontier-2026-07-13-v1c` | `protocol/ijds-normalized-objective-frontier-2026-07-14-v3` |
| Evaluation commit | Outcome-free freeze lineage | `a1ae516a6c9674686dba245cb275475073b298a0` |
| Freeze SHA-256 | `7877c5e460772a0093e4132eaa542e9049f7ec15d2ddaa35c2df389892a0e185` | See source registry and verified manifest |
| Credit controls | `ijds-credit-risk-controls-2026-07-13-v1b` | `ijds-credit-risk-controls-2026-07-14-v3` |
| Protocol tags | `protocol/ijds-credit-risk-controls-2026-07-13-v1b` | `protocol/ijds-credit-risk-controls-2026-07-14-v3` |
| Protocol commits | `1776cbf8b201ae5b92756e5ea397a403d6cc7c9f` | `688f75dc4f285c75bc499c9e041dd30fb3acd70d` |
| Freeze SHA-256 | `da4805e644bcf5decfbb0a67c0c81a5b9dd61f3ab2e17d3dc5264100e7eb4d35` | See source registry and execution receipt |

The raw-data audit is `ijds-raw-data-contract-2026-07-14-v2`; the reporting-lag
sensitivity is `ijds-label-lag-sensitivity-2026-07-14-v1`; and the evaluated-cap
tie audit is `ijds-policy-support-tie-audit-2026-07-12-v1`. Their descriptors
are hash-locked in `configs/ijds_active_evidence_sources.yaml`.

## DVC Capsule

The twelve pointers are listed once in
`configs/crpto_publication_targets.yaml`. They comprise data and model pointers
for each of the three outcome-free roots and three endpoint-corrected evaluation
roots. Pull with:

```powershell
uv run python scripts/manage_ijds_dvc_capsule.py pull
```

Machine-local DVC credentials belong in `.dvc/config.local` and are never
committed.

## Replay

```powershell
uv sync --frozen --extra dev --extra search --extra spo
just submission-build
just ijds-active-check
uv run python scripts/manage_ijds_dvc_capsule.py status
```

The paper-facing builder fails closed on source-hash, cardinality, endpoint,
selection-boundary, and solver-audit drift. Reviewer surfaces intentionally omit
the identifiers above. Protected historical champion stages and
`EXTRACTION_MANIFEST.json` are not modified or reproduced by this workflow.
