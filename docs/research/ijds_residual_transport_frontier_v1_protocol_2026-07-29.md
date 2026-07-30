# IJDS finite-archive residual-transport frontier V1 protocol

**Protocol date:** 2026-07-29

**Run tag:** `ijds-residual-transport-frontier-2026-07-29-v1`

**Required clean tag:** `protocol/ijds-residual-transport-frontier-2026-07-29-v1`

**Status:** retrospectively locked after archive access and inspection of earlier
transport diagnostics, but before this V1 execution.

## Scientific role and non-claim boundary

This is a descriptive finite-archive diagnostic. It asks where the empirical
distribution of the frozen conformal-fit absolute residuals differs from the
empirical distribution on the fixed April 2016--June 2017 primary-OOT archive.
It does **not** test or establish exchangeability, temporal transport of
split-conformal coverage, selected-set validity, funded-portfolio validity,
causality, or prospective performance. No p-value, confidence interval,
multiplicity decision, learner ranking, window ranking, score-stratum
selection, or policy selection is produced.

The archive, the V5 coverage outputs, and earlier transport analyses were
already available for inspection when this protocol was written. Consequently
the replay is retrospective and neither preregistered nor confirmatory. Its
outputs remain candidate evidence until a later explicit audit and claim-ledger
promotion. Merely completing the run activates no manuscript claim.

## Locked source lineage

The YAML configuration binds every input by canonical repository-relative path,
byte count, and SHA-256. This includes the complete six-file V5 configuration
inheritance chain from the V5 leaf through V4, V3, V2, V1, and the fixed-
taxonomy parent; every `extends` edge is verified before the merged config is
loaded. The runner must also reconcile the nested descriptors
in the five-learner evaluation summary, its outcome-free freeze, and the
exchangeability-transport summary.

The scientific inputs are:

1. the active V5 configuration and raw archive endpoint contract;
2. the five-learner evaluation summary and temporal-coverage table;
3. the frozen outcome-free scores, residual recipes, and calibration-row
   residual-fit audit;
4. the raw archive, read only, used solely to reconstruct the locked endpoint;
5. the completed exchangeability-transport summary and its 200 stratum rows,
   used as an exact V5/q reconciliation reference, not as inferential input.

The optional `--protected-read-root` is only a materialization root. For each
canonical descriptor path, the runner may read an exact byte/hash-matching copy
under that root when the clone-local copy is unavailable. It must reject
absolute descriptor paths, traversal, root escape, size drift, or hash drift.
It must never serialize the absolute protected root, write beneath it, or use
it to relocate the protocol, configuration, implementation, or outputs.

## Locked population and grid

The target panel is the complete frozen `primary_oot` score panel for the 15
issue months from 2016-04 through 2017-06. The expected endpoint census is:

- 376,890 candidate rows;
- 364,814 resolved rows, comprising 307,842 nondefaults and 56,972 defaults;
- 12,076 unresolved rows.

The complete reporting grid is five frozen learner specifications by eight
calibration windows by five fixed score strata by 15 issue months: 3,000
monthly rows. A second table recomputes each diagnostic after pooling all 15
months within learner--window--stratum, giving 200 pooled rows. The five learner
specifications remain coverage controls; this diagnostic does not declare a
winner. No two-origin, first-versus-last-window, or selected-window sensitivity
is part of V1.

Every pooled cell must reproduce the active lineage at its frozen residual
quantile: candidate, resolved, unresolved, fit, and miss counts; resolved and
completion-bounded coverage; target and fit score extrema; and the residual
quantile itself. The V5 temporal table and exchangeability table must first
agree on their common fields and exact 200-cell key grid.

## Residuals and empirical CDFs

For learner \(a\), window \(w\), score stratum \(g\), let the frozen calibration
residuals be

\[
R_i^{\mathrm{cal}}=|Y_i-P_i|,
\qquad i=1,\ldots,n_{awg},
\]

and let \(F^{\mathrm{cal}}_{awg}\) be their empirical CDF. The residual-fit audit
must independently reproduce the frozen finite-sample order statistic and all
recipe assignments before any target diagnostic is computed.

For a target scope \(s\), resolved rows have
\(R_j^{\mathrm{tar}}=|Y_j-P_j|\). The resolved-only empirical CDF is
\(F^{\mathrm{res}}_{awgs}\). V1 reports both directional empirical-CDF suprema:

\[
D_{\mathrm{cal}>\mathrm{res}}
=\sup_t\{F^{\mathrm{cal}}_{awg}(t)-F^{\mathrm{res}}_{awgs}(t)\},
\]

\[
D_{\mathrm{res}>\mathrm{cal}}
=\sup_t\{F^{\mathrm{res}}_{awgs}(t)-F^{\mathrm{cal}}_{awg}(t)\}.
\]

Each supremum is evaluated exactly on the union of observed residual values and
is accompanied by the smallest finite grid value attaining the computed
maximum. These are descriptive directional KS distances, not KS hypothesis
tests.

## Sharp unresolved-completion extrema

For unresolved target score \(p_j\), the only two binary-outcome residuals are

\[
r_{j0}=p_j,\qquad r_{j1}=1-p_j.
\]

Define the rowwise endpoint residuals

\[
r_j^L=\min(r_{j0},r_{j1}),\qquad
r_j^H=\max(r_{j0},r_{j1}).
\]

Combining the resolved residuals with every \(r_j^L\) produces the
pointwise-largest feasible target empirical CDF \(F^L\); combining them with
every \(r_j^H\) produces the pointwise-smallest feasible target CDF \(F^H\).
Therefore the sharp cellwise extrema over all binary completions are

\[
\begin{aligned}
\min_z\sup_t(F^{\mathrm{cal}}-F^z)&=\sup_t(F^{\mathrm{cal}}-F^L),\\
\max_z\sup_t(F^{\mathrm{cal}}-F^z)&=\sup_t(F^{\mathrm{cal}}-F^H),\\
\min_z\sup_t(F^z-F^{\mathrm{cal}})&=\sup_t(F^H-F^{\mathrm{cal}}),\\
\max_z\sup_t(F^z-F^{\mathrm{cal}})&=\sup_t(F^L-F^{\mathrm{cal}}).
\end{aligned}
\]

The endpoint values and their witnesses are reported. Sharpness is cellwise:
the completion attaining an endpoint may differ across learners, windows,
strata, or months. V1 makes no joint-sharpness claim and no claim that every
interior distance between the two extrema is attainable.

For interpretation without selecting an extreme cell, V1 also applies one
prespecified symmetric comparison to every cell. Write the two sharp
directional-discrepancy ranges as \([D^-_{C>T},D^+_{C>T}]\) and
\([D^-_{T>C},D^+_{T>C}]\). The label is
`larger_target_residual_discrepancy_dominates` only when
\(D^-_{C>T}>D^+_{T>C}\),
`smaller_target_residual_discrepancy_dominates` only when
\(D^-_{T>C}>D^+_{C>T}\), and
`directional_discrepancies_not_robustly_ordered` otherwise. Inequality is
strict: equality or overlap is conservatively classified as not robustly
ordered. The implementation compares exact integer cross-product numerators
under the common empirical-CDF denominator, so floating-point roundoff cannot
turn a tie into a directional label. These labels compare the magnitudes of
the two maximum one-sided CDF discrepancies. They do **not** say that target
residuals or their distribution are larger or smaller, and they do not assert
stochastic ordering. This remains a descriptive full-census comparison, not an
inferential decision.

## Frozen-quantile reconciliation

Let \(q_{awg}\) be the frozen V5 residual quantile. Coverage is the scalar rule
\(R\le q_{awg}\), so a miss is strictly \(R>q_{awg}\). V1 reports the
calibration CDF, resolved target CDF, and sharp all-candidate target-CDF
endpoints at \(q_{awg}\). For an unresolved row, its minimum and maximum miss
contributions are respectively

\[
\min\{1(r_{j0}>q),1(r_{j1}>q)\},\qquad
\max\{1(r_{j0}>q),1(r_{j1}>q)\}.
\]

Monthly integer contributions must sum exactly to their pooled counterparts.
Every pooled count and floating result at \(q\) must reconcile with the locked
V5/exchangeability reference within absolute tolerance \(10^{-12}\).

## Outputs

Fresh, no-overwrite run directories contain only:

- `monthly_residual_transport_frontier.csv` (3,000 rows);
- `pooled_residual_transport_frontier.csv` (200 rows);
- `residual_transport_frontier_summary.json`;
- `execution_receipt.json`.

The tables include identifiers, target and fit counts, the frozen quantile and
rank, q-level miss/coverage identities, both resolved directional distances,
all four sharp completion extrema, and finite witnesses. The JSON files bind
the source descriptors, protocol commit/tag, implementation hashes,
environment, schemas, Git state, protected reads, and empty protected-write and
protected-stage lists.

## Predeclared Git artifact transport

The required artifact tag is
`artifacts/ijds-residual-transport-frontier-2026-07-29-v1`. The runner does not
create that tag or claim that transport is complete. Both its summary and its
receipt must exit in `pending_git_artifact_commit` status and serialize the
configuration's repository-relative artifact-transport contract without an
absolute path.

After the runner exits, exactly one artifact commit may be created. It must be
a single direct child of the protocol commit, and its complete Git diff must
contain exactly the four output paths listed above—no implementation,
configuration, protocol, source, DVC pointer, or unrelated file. The required
artifact tag must resolve to that direct-child commit. DVC is not required for
this small-output transport (`dvc_required: false`); a DVC operation is not
part of V1. Until both the direct-child relation and exact path set are audited,
the calculation remains pending and cannot be promoted.

## Fail-closed execution contract

Execution is permitted only after these new files are committed, the exact
required protocol tag points to that clean HEAD, all synthetic unit tests pass,
and the output run directories do not exist. The runner stops before writing on
any dirty/untagged HEAD, source or nested-descriptor mismatch, protected-root
escape, unsafe output name, grid duplication or omission, census drift,
monthly cell without resolved target rows, fit-order-statistic drift, score-edge
or assignment drift, V5/q mismatch,
directional/frontier ordering failure, monthly-to-pooled count failure, or
implementation change during execution.

The planned command is:

```powershell
uv run python scripts/experiments/run_ijds_residual_transport_frontier.py `
  --config configs/experiments/ijds_residual_transport_frontier_2026-07-29_v1.yaml `
  --protected-read-root <exact-materialized-repository-root>
```

Omit `--protected-read-root` only when every locked source is materialized and
hash-correct inside the clean clone. This protocol does not authorize any
protected model-fitting, conformal-fitting, optimization, or bound-evaluation
stage.
