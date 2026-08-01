# IJDS binary phase census V1 protocol (2026-08-01)

## Status and purpose

This document locks a retrospective, outcome-free, complete-grid census before
its first execution. It is neither a preregistration nor a confirmatory study.
Its sole scientific question is whether the exact binary split-conformal
order-statistic identities and their explicitly conditional phase
interpretations reconcile in every cell of a fixed 5 learner x 8 window x 5
stratum design.

The census repairs the asymmetry of an earlier stopped lineage. It contains no
named diagnostic path, no learner/window comparison, and no choice of a
representative transition or stratum. The identifier-bearing result is the
complete 200-row cell table. The summary reports every one of the five ordered
conformal groups, with exactly 40 learner-window cells expected in each. Within
each group, every statistic is invariant to permutations of learner and window
labels; no group may be omitted, pooled after inspection, or promoted as the
representative group.

## Frozen design

- Run tag: `ijds-binary-phase-census-2026-08-01-v1`.
- Required annotated protocol tag:
  `protocol/ijds-binary-phase-census-2026-08-01-v1`.
- Planned direct-child artifact tag:
  `artifacts/ijds-binary-phase-census-2026-08-01-v1`.
- Miscoverage level: `alpha = 0.10`.
- Domain: five declared learners, eight declared windows, and conformal groups
  `0, 1, 2, 3, 4` under `taxonomy_groups = 5`.
- Required census size: exactly `5 x 8 x 5 = 200` unique cells.
- Every calibration cell must contain both binary classes.
- Every finite-sample rank must be attained (`k <= n`); rank capping is not
  admitted.
- Absolute reconciliation tolerance for frozen floating-point thresholds and
  score extrema: `1e-15`, with zero relative tolerance.

The exact learner and window identifiers are frozen in the configuration. They
may appear in the complete cell table because they define the census keys, but
they may not be used to construct a named slice or an identifier-specific
summary.

## Four hash-bound sources and the read boundary

All four files below must match path, byte count, and SHA-256 digest. The two
JSON files are provenance witnesses only: the runner hashes them but never
parses their contents. Consequently, no status, result, claim, endpoint, or
other scientific value is inherited from either JSON.

| Source | Bytes | SHA-256 | Role |
|---|---:|---|---|
| `models/experiments/ijds_audit/ijds-credit-risk-controls-2026-07-13-v1b/protocol_freeze.json` | 25,908 | `da4805e644bcf5decfbb0a67c0c81a5b9dd61f3ab2e17d3dc5264100e7eb4d35` | unparsed provenance witness |
| `data/processed/experiments/ijds_audit/ijds-credit-risk-controls-2026-07-13-v1b/prediction/residual_fit_audit.parquet` | 45,955,332 | `396c30d9bec7d222220cfe6f9870ab4994cf5c33e6da8c9e4ebbd99153155353` | calibration table, allowlisted columns only |
| `models/experiments/ijds_audit/ijds-exchangeability-transport-test-2026-07-21-v1/exchangeability_transport_test_summary.json` | 9,078 | `72d9d39b2bef36a36440f1ccc720575d74005f1ad1932a774a91f73ed26c8af6` | unparsed provenance witness |
| `data/processed/experiments/ijds_audit/ijds-exchangeability-transport-test-2026-07-21-v1/evaluation/exchangeability_transport_strata.parquet` | 90,676 | `4d34a1de1d3d9556e9b9b74d0517b01b117030d7036a6911d5ad6807080601e3` | frozen calibration-stratum table, allowlisted columns only |

The calibration-row table may expose only:

`id`, `learner`, `window_id`, `taxonomy_groups`, `conformal_group`,
`pd_point`, and `terminal_default`.

Here `terminal_default` is the already frozen calibration label needed to form
the calibration residual; it is not an evaluation endpoint. The frozen
stratum table may expose only:

`learner`, `window_id`, `taxonomy_groups`, `conformal_group`, `fit_rows`,
`finite_sample_rank`, `fit_residual_quantile`, `fit_score_min`,
`fit_score_max`, `fit_residual_below_threshold`,
`fit_residual_equal_threshold`, and `fit_residual_above_threshold`.

The runner must request these columns explicitly from Parquet. It must not read
resolved or unresolved labels, candidate or funded populations, evaluation
scores, endpoint fields, coverage fields, p-values, allocations, or policies.
There is no join to a target sample.

## Cell-level estimands and exact checks

For one cell let the calibration scores be `p_i in [0,1]`, labels be
`y_i in {0,1}`, residuals be `r_i = |y_i-p_i|`, and sample size be `n`. Define

`k = ceil((n+1)(1-alpha))`.

Execution stops unless `k <= n`. The threshold `q` is the exact `k`th order
statistic of the residual multiset. Let `D` be the number of defaults. The
rank boundary and phase margin are

`b = n-k = floor(alpha(n+1))-1`, and `m = D-b`.

The implementation checks the boundary identity exactly. It also counts
residuals strictly below, equal to, and strictly above `q`, requires
`below < k <= below+equal`, and reconciles every count, rank, threshold, and
score extremum to the frozen stratum row.

For the unconditional half-threshold identity define

- `A = #{i: y_i=0 and p_i<1/2}`;
- `B = #{i: y_i=1 and p_i>1/2}`.

Then the implementation must verify exactly that

`q < 1/2` if and only if `A+B >= k`.

The phase margin receives only two conditional interpretations:

1. If `max_i p_i < 1/2`, the implementation checks
   `m <= 0` if and only if `q < 1/2`.
2. If both classes are nonempty and
   `max_{y_i=0} p_i + max_{y_i=1} p_i < 1`, the two mirror-residual samples do
   not interleave. Only in that cell, `m <= 0` must place the order statistic
   in the nondefault mirror sample and `m > 0` in the default mirror sample.

If a condition does not hold, its interpretation is marked inapplicable; it is
not treated as a failed or approximately true theorem.

## Outputs and symmetric reporting contract

Only these fresh files are authorized after every gate passes:

- `binary_phase_census.csv` in the run-tagged data directory;
- `binary_phase_census_summary.json` in the run-tagged model directory;
- `execution_receipt.json` in the same model directory.

These three configured names are exact, unique safe basenames. Absolute paths,
`.` or `..`, path separators, extra output keys, alternate roots, and duplicate
filenames are execution-stopping configuration errors checked before either
run-tagged directory is created.

The CSV contains all 200 cells and their reconciliation diagnostics. The JSON
summary reports design cardinalities, global cell counts and checks, plus one
exhaustive ordered entry for each conformal group `0` through `4`. Each group
entry must show 40 expected and observed learner-window cells and counts for
`q<1/2`, `m<=0`, the two conditional-support predicates, their applicable
checks, and reconciliation. It may not contain a learner- or window-specific
breakdown or reproduce learner/window identifier values. It may not report a
proper subset of groups. No cell extremum is reported because it could silently
identify a cell after inspection.

## Interpretation boundary

This census does not establish or test:

- continuity of a finite order-statistic path;
- a common-maxima unit crossing;
- a universal low-score-bin property;
- a threshold-distance or miscoverage floor from a positive lower endpoint;
- calibration or target-sample coverage;
- temporal transport, stochastic dominance, or a mechanism;
- learner, window, stratum, map, ruler, coordinate, or policy superiority;
- selected-set, funded-set, joint-set, or portfolio validity;
- any optimization, causal, prospective, or robust-policy result.

Calibration support alone supplies no target-mass bound. A failure of a
conditional phase pattern permits no conclusion outside the exact cell-level
identity being checked. The census adds geometry and provenance only.

## Execution and promotion gates

Before reading either scientific table, the runner must require:

1. a clean Git worktree;
2. the required protocol tag resolving exactly to current `HEAD`;
3. that tag being annotated, not lightweight;
4. all four source descriptors matching;
5. the configuration, the four other new scientific implementation-contract
   files, both imported shared I/O/provenance helpers, `pyproject.toml`, and
   `uv.lock` retaining their start hashes;
6. both run-tagged output directories being absent.

Any domain, symmetry, duplicate-ID, numeric, binary-label, empty-class, rank,
order-statistic, tie-count, frozen-reconciliation, protocol, source, or
implementation failure stops the run before output creation. No protected
pipeline stage is authorized.

After a successful run, the outputs require one direct-child artifact commit
and the planned annotated artifact tag. Even then, this lineage is not promoted
automatically to the paper, active claim registry, or active evidence manifest;
that requires a separate adversarial promotion audit.
