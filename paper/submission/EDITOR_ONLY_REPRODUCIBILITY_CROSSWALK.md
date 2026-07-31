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

The complete per-solve column-and-row basis source audit is
`ijds-policy-support-optimal-face-audit-2026-07-21-v2`, protocol-locked at
commit `86fddefdcf4d40a971866b2d9acf1d34f5c3bca2`. Its immutable stored RHS gate
failed closed. The active status-aware recovery is
`ijds-policy-support-rhs-semantics-recovery-2026-07-21-v3a`, protocol-locked at
commit `388927ebfe34e872fc5d1085ece63300734d5b47`. It replays all 196 V2 gap
midpoints retrospectively registered in V3a and authorizes numerical support
coverage at tolerance `1e-10`, not
optimal-face or continuous-frontier uniqueness. The V3 predecessor at
`8508a339` created no outputs and remains failed implementation provenance.

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

The complete common-panel threshold-response diagnostic is
`ijds-common-panel-threshold-response-2026-07-26-v8`, protocol-locked by tag
`protocol/ijds-common-panel-threshold-response-2026-07-26-v8` at commit
`06a7d864776247fbb5128105deb229de4476be65`. It reuses one fixed
376,890-candidate panel and reports all 175 stratum transitions and all 35
integer-pooled learner transitions, with a shared unresolved-label completion
in each from/to contrast. Its four result files are the exact diff of artifact
tag `artifacts/ijds-common-panel-threshold-response-2026-07-26-v8` at commit
`526a71bd0a0a7663a313dc12b0ce0eb3307719d9`, whose sole parent is the protocol
commit. The source registry verifies both tags, that parent relation, the exact
four-path diff, the current Git transport, and every file hash. V8
supersedes V7 because its receipt discloses the protected raw-archive read; the
scientific CSV outputs are byte-identical. This is
a retrospective descriptive replay, not a selected transition, temporal
transport result, or explanation of threshold movement.

The closed CatBoost calibrator sensitivity uses a four-commit chain:
protocol P `808827926eff5030b3cb28d2b89a87a0e6210b2e`, outcome-free source A
`ea3e7326afc38ccc1b99b09de30792986640e3c3`, endpoint-evaluation lock B
`753305e81e27f793acdea80b684b42e7eff2201d`, and complete result C
`6552524eae5a22ce66b50689900383d16df1ff13`. Its four tags are annotated and
each commit after P is the single direct child of the preceding one. The
complete result has 192 coverage/geometry and 288 shared-completion pairwise
cells; 18/32 pooled upper endpoints are below 0.90, so the registered state is
`uniform_closed_family_shortfall_not_established`. This selects no calibrator,
transfers no Venn guarantee to the IVAP scalar, and supplies no portfolio
result.

### Git-transported publication lineages

Five publication lineages use one protocol-to-artifact direct-child edge. The
set-preserving-embedding lineage instead uses the registered two-stage
`P2 -> A2 -> B2` chain because its outcome-free source bytes and evaluated
outputs have separate authority. The calibrator lineage uses the four-stage
`P -> A -> B -> C` chain because the endpoint lock is committed after the
outcome-free source and before evaluation. Together these are seven scientific
Git-native lineages. Every tag below is annotated, every listed child has one
parent, and the source registry verifies the exact added-path census and file
hashes.

| Lineage | Protocol tag / commit | Intermediate source tag / commit | Evaluation artifact tag / commit |
|---|---|---|---|
| Common-panel V8 | `protocol/ijds-common-panel-threshold-response-2026-07-26-v8` / `06a7d864776247fbb5128105deb229de4476be65` | -- | `artifacts/ijds-common-panel-threshold-response-2026-07-26-v8` / `526a71bd0a0a7663a313dc12b0ce0eb3307719d9` |
| Marginal gap V3I | `protocol/ijds-marginal-mean-score-outcome-gap-2026-07-29-v3i` / `9c4b082ce68eb88bf60666b4cb794348bf57a40d` | -- | `artifacts/ijds-marginal-mean-score-outcome-gap-2026-07-29-v3i` / `8fff4834aa5443150b5c2d82d07723b0de75d76e` |
| Residual frontier V1 | `protocol/ijds-residual-transport-frontier-2026-07-29-v1` / `9c4b082ce68eb88bf60666b4cb794348bf57a40d` | -- | `artifacts/ijds-residual-transport-frontier-2026-07-29-v1` / `e6dd6422e853728a9880affbf61d8819728a1efb` |
| Decision catalog V1 | `protocol/ijds-decision-catalog-transport-2026-07-29-v1` / `9c4b082ce68eb88bf60666b4cb794348bf57a40d` | -- | `artifacts/ijds-decision-catalog-transport-2026-07-29-v1` / `0a016e87074d7e92ce57b2d83aaf30b8b31b7e5a` |
| Funded estimands V1 | `protocol/ijds-funded-selection-estimand-audit-2026-07-29-v1` / `9c4b082ce68eb88bf60666b4cb794348bf57a40d` | -- | `artifacts/ijds-funded-selection-estimand-audit-2026-07-29-v1` / `0d26e0247d41ae4ff1c9ad8ca230b0a627303190` |
| Set-preserving embedding V1d | `protocol/ijds-set-preserving-embedding-sensitivity-2026-07-30-v1d` / `174c4e3d894829473a787e6d34bfc3bbab2f8ef2` | `artifacts/ijds-set-preserving-embedding-sensitivity-2026-07-30-v1a-recovery-v1d` / `95e39f05bb990429025d0115a0e55c53b1fb1ea8` | `artifacts/ijds-set-preserving-embedding-sensitivity-2026-07-30-v1d` / `276a5db8772262aad2edd8936dbe226926e412b5` |
| Calibrator sensitivity V1 | `protocol/ijds-calibrator-sensitivity-2026-07-30-v1` / `808827926eff5030b3cb28d2b89a87a0e6210b2e` | `artifacts/ijds-calibrator-sensitivity-2026-07-30-v1-source` / `ea3e7326afc38ccc1b99b09de30792986640e3c3` | `protocol/ijds-calibrator-sensitivity-evaluation-2026-07-30-v1` / `753305e81e27f793acdea80b684b42e7eff2201d` -> `artifacts/ijds-calibrator-sensitivity-2026-07-30-v1` / `6552524eae5a22ce66b50689900383d16df1ff13` |

V1d is retrospective and post-inspection. V1c failed its persistence contract
before any evaluation commit or tag; its local Phase-B files are non-evidence
and were neither copied nor read by V1d.

The fit-label completion sensitivity is
`ijds-fit-label-completion-sensitivity-2026-07-16-v2`, protocol-locked at
commit `fbcafcf84645024b9753aba2f04a4263b8e76236`. The allocation-granularity
sensitivity is `ijds-allocation-granularity-sensitivity-2026-07-16-v3`,
protocol-locked at commit `fb1a7b1837d1f8ab2b81239533f51c996f41671c`.
Both record scientific `uv.lock` SHA-256
`25cefb168506538c22b86a348c42869ea7fda64338815f2adea3fe7e07608f93`;
their freezes, summaries, and DVC roots are verified by the source registry.

## DVC Capsule

The 53 DVC pointers are listed once in `configs/ijds_active_evidence_sources.yaml`.
They comprise data and model pointers for the active roots and sensitivities,
plus explicitly labeled replay dependencies, including the data-only
structural V5 shard root and the unequal-follow-up origin roots. Pull with:

```powershell
uv run --locked python scripts/manage_ijds_dvc_capsule.py pull
```

The registered evidence builder emits one paper-facing manifest, 41 CSV
tables, and five figure families in both PDF and PNG. Calibrator Table S2C
contains the four same-sample fit rows, S6O contains all 192
method--window--scope rows, and S6P contains all 288 unordered-pair
shared-completion rows.

Machine-local DVC credentials belong in `.dvc/config.local` and are never
committed.

## Replay

Publication replay uses the current checked-out builder to verify immutable
evidence and regenerate reviewer artifacts. A scientific rerun instead checks
out the protocol commit and environment-lock hash recorded for that lineage.
These are complementary contracts; current source code is not treated as a
substitute for a historical scientific environment.

```powershell
uv sync --group dev --locked
just submission-build
just ijds-active-check
uv run --locked python scripts/manage_ijds_dvc_capsule.py status
```

The paper-facing builder fails closed on source-hash, cardinality, endpoint,
selection-boundary, and solver-audit drift. Reviewer surfaces intentionally omit
the identifiers above. Protected historical champion stages and
`EXTRACTION_MANIFEST.json` are not modified or reproduced by this workflow.
