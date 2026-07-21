# Editor-Only Reproducibility Crosswalk

Do not include this file in the anonymous reviewer archive. It contains
searchable protocol identifiers and immutable provenance.

## Active Authority

| Object | Path |
|---|---|
| Claim registry | `docs/research/active_claims_2026-07-14.md` |
| Executable claim ledger | `configs/ijds_claim_ledger.yaml` |
| Source registry | `configs/ijds_active_evidence_sources.yaml` |
| Evidence manifest | `reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json` |
| Body | `paper/CRPTO_ijds.qmd` |
| Supplement | `paper/supplement_ijds.qmd` |
| Generated TeX | `paper/submission/CRPTO_ijds_submission.tex` |

## Immutable Lineages

| Lineage | Outcome-free freeze | Endpoint-corrected evaluation |
|---|---|---|
| Binary geometry / registered point-cap support | `ijds-binary-geometry-frontier-v4-2026-07-12-v1` | `ijds-binary-geometry-frontier-v4-2026-07-15-v5` |
| Protocol tags | `protocol/ijds-binary-geometry-frontier-v4-2026-07-12-v1` | `protocol/ijds-binary-geometry-frontier-v4-2026-07-15-v5` |
| Protocol commits | `2f8a7606e4eb65aa3ae3701fb3af8d9a51c953cd` | `e2bba580a0b07c145bd64ff61440973d6e31349b` |
| Freeze SHA-256 | `c2b3dc2d18c9fed80708682d5a0369c80c89643e2d28024418522d954ebe667c` | See source registry and execution receipt |
| Two-ruler diagnostic | `ijds-normalized-objective-frontier-2026-07-13-v1c` | `ijds-normalized-objective-frontier-2026-07-15-v5` |
| Protocol tags | `protocol/ijds-normalized-objective-frontier-2026-07-13-v1c` | `protocol/ijds-normalized-objective-frontier-2026-07-15-v5` |
| Protocol commits | `46f4df915d38eb5a6cc144484c6e6fe56d8ed397` | `e2bba580a0b07c145bd64ff61440973d6e31349b` |
| Freeze SHA-256 | `7877c5e460772a0093e4132eaa542e9049f7ec15d2ddaa35c2df389892a0e185` | See source registry and verified manifest |
| Credit controls | `ijds-credit-risk-controls-2026-07-13-v1b` | `ijds-credit-risk-controls-2026-07-15-v5` |
| Protocol tags | `protocol/ijds-credit-risk-controls-2026-07-13-v1b` | `protocol/ijds-credit-risk-controls-2026-07-15-v5` |
| Protocol commits | `1776cbf8b201ae5b92756e5ea397a403d6cc7c9f` | `e2bba580a0b07c145bd64ff61440973d6e31349b` |
| Freeze SHA-256 | `da4805e644bcf5decfbb0a67c0c81a5b9dd61f3ab2e17d3dc5264100e7eb4d35` | See source registry and execution receipt |

The raw-data audit is `ijds-raw-data-contract-2026-07-14-v2`; the reporting-lag
sensitivity is `ijds-label-lag-sensitivity-2026-07-14-v1`; and the evaluated-cap
tie audit is `ijds-policy-support-tie-audit-2026-07-12-v1`. Their descriptors
are hash-locked in `configs/ijds_active_evidence_sources.yaml`.

The complete evaluation-endpoint availability sensitivity is
`ijds-endpoint-availability-sensitivity-2026-07-14-v1`, protocol-locked at
commit `8865f1cfbd387576bdf805f3e52f030261e4b717`. It reports lags 0, 3, 6, 8,
and 12 without selecting an endpoint; its six-month slice reconciles exactly
to the active evaluations. It is distinct from conformal-fit label timing.

The complete portfolio-structure sensitivity is
`ijds-portfolio-structure-sensitivity-2026-07-15-v6`, protocol-locked at commit
`490c653a43e2003d83184f47e1277bd2d4390c43`. Its outcome-free freeze reports
all 36 budget--purpose-cap--LGD scenarios; its separate evaluation selects no
scenario and reconciles the baseline exactly to the active evaluation.
Structural V1--V4 remain stopped provenance; V5 is a data-only replay
dependency for V6 and is not paper-facing evidence.

The active two-origin sensitivity is
`ijds-rolling-origin-individual-age-followup-2026-07-21-v1`, protocol-locked at
commit `78a0a588c35f53daeeef526c3fbe53c10e664385`. Each April--June candidate
receives a cutoff 39 calendar months after its issue-month end, giving
July--September 2019 and July--September 2020 cutoffs. The parent equal-quarter
run and the earlier primary-recovery and 2017 rolling-origin roots remain
registered only as replay dependencies; they are not paper-facing evidence.

The exact combined-rank reference analysis is
`ijds-exchangeability-transport-test-2026-07-21-v1`, protocol-locked at commit
`c9d30b02885bac516ae21eae32c56120cf7d296e`. It reports all 200 strata and all
40 learner-window omnibus reference calculations, with Bonferroni within cell
and Holm across cells. In 31/40 cells the reference p-values meet those locked
nominal thresholds. The Beta--Binomial law assumes joint exchangeability of a
calibration stratum with its entire target block, which is stronger than the
usual one-future-point marginal split-conformal condition. The family and
pattern were inspected before locking, so these flags provide no
post-selection or study-wide FWER guarantee.

The resolved-label and set-efficiency diagnostic is
`ijds-conformal-set-diagnostics-2026-07-21-v1`, protocol-locked at commit
`5248099e2c02fa0340acb6d9c0ef5fbaa1b4e3cf`. The label-Mondrian lineage uses
outcome-free freeze `ijds-label-mondrian-freeze-2026-07-21-v1`, protocol-locked
at commit `c9d30b02885bac516ae21eae32c56120cf7d296e`, followed by evaluation
`ijds-label-mondrian-evaluation-2026-07-21-v1`, protocol-locked at commit
`a341135eaf1ff32401a360fcb64c7a22fbf0b202`. It reports the complete 40/200/400
grid and selects no learner, window, category, or method. The missingness
sensitivity is `ijds-missingness-sensitivity-2026-07-15-v3`, protocol-locked at
commit `199afb083da37af6a51d5ba9e3c4d6280b952fe9`. These complete grids select no
model, encoding, origin, or observed-label subgroup.

The fit-label completion sensitivity is
`ijds-fit-label-completion-sensitivity-2026-07-16-v2`, protocol-locked at
commit `fbcafcf84645024b9753aba2f04a4263b8e76236`. The allocation-granularity
sensitivity is `ijds-allocation-granularity-sensitivity-2026-07-16-v3`,
protocol-locked at commit `fb1a7b1837d1f8ab2b81239533f51c996f41671c`.
Both record scientific `uv.lock` SHA-256
`25cefb168506538c22b86a348c42869ea7fda64338815f2adea3fe7e07608f93`;
their freezes, summaries, and DVC roots are verified by the source registry.

## DVC Capsule

The 47 DVC pointers are listed once in `configs/ijds_active_evidence_sources.yaml`.
They comprise data and model pointers for the active roots and sensitivities,
plus explicitly labeled replay dependencies, including the data-only
structural V5 shard root and the unequal-follow-up origin roots. Pull with:

```powershell
uv run --locked python scripts/manage_ijds_dvc_capsule.py pull
```

The registered evidence builder emits one paper-facing manifest, 27 CSV
tables, and three figure families in both PDF and PNG.

Machine-local DVC credentials belong in `.dvc/config.local` and are never
committed.

## Replay

Publication replay uses the current checked-out builder to verify immutable
evidence and regenerate reviewer artifacts. A scientific rerun instead checks
out the protocol commit and environment-lock hash recorded for that lineage.
These are complementary contracts; current source code is not treated as a
substitute for a historical scientific environment.

```powershell
uv sync --group dev --frozen
just submission-build
just ijds-active-check
uv run --locked python scripts/manage_ijds_dvc_capsule.py status
```

The paper-facing builder fails closed on source-hash, cardinality, endpoint,
selection-boundary, and solver-audit drift. Reviewer surfaces intentionally omit
the identifiers above. Protected historical champion stages and
`EXTRACTION_MANIFEST.json` are not modified or reproduced by this workflow.
