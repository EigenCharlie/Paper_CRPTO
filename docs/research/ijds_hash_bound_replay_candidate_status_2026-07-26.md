# Hash-bound replay candidate status (2026-07-26)

## Decision

The V6 binary-phase replay and the post-freeze derived-diagnostic replay are
complete, deterministic, and hash-bound, but they are **not active IJDS paper
evidence**. At execution, their protocols, configurations, runners, and
implementations did not have a pre-existing protocol commit or tag, and the
working tree was dirty. The receipts therefore make no protocol-commit claim.

The only admissible promotion path is a fresh execution under new run tags and
new immutable output paths after the complete protocol/configuration/code
surface has been committed and tagged. Reusing either completed candidate run
as if it were preregistered or hiding its calculations inside the V4 builder is
forbidden.

An adversarial review found an additional protocol mismatch. The executed
`phase_geometry_evidence` helper selects `catboost_platt`, score stratum 3,
requires exactly one high-to-low regime change, identifies its adjacent step,
and ranks the W7--W8 resolved-coverage change. V6 Section 7 locked the complete
S6I census but did not predeclare that learner/stratum illustration, the
single-transition requirement, or the adjacent-change ranking rule. Those
selected path statistics are therefore post-inspection even within this
candidate replay. A future clean protocol must either declare them explicitly
as a retrospective illustration with a fixed selection/ranking rule, or the
runner must be refactored to emit only the complete 200-row S6I table without
requiring or selecting a transition.

The no-interleaving characterization also requires both calibration mirror
samples to be nonempty. All 200 realized cells contain both classes, but the
current helper treats an empty-class cell as separated by convention. Before
promotion, the theorem statement and implementation contract must explicitly
require positive default and nondefault counts (or mark the condition
undefined/fail closed); no separation-based supplier formula may be asserted
for a degenerate one-class calibration block.

The executed helper also describes a Poisson--binomial phase reference without
stating conditional independence of labels given fixed scores and correct
calibration. Varying Bernoulli marginals alone do not determine that sum law.
No crossing reference distribution is active; a future implementation must
either state and justify the full joint label model or omit the reference-law
claim.

The two executed runners also have engineering reuse blockers. They contain
their run-tag directories, but concatenate output filenames from YAML without
requiring a direct basename or uniqueness. A separator-bearing or absolute
name could therefore escape the run directory, and duplicate role names could
silently alias outputs. In addition, `conformal_group.astype(int)` is applied
before exact-integrality validation in the V6 runner; a fractional key could be
truncated. The executed configurations use distinct safe basenames, the
realized keys are integral, and the recorded outputs are unaffected. Because
the runner/module bytes are execution identities, they are frozen rather than
silently patched. A V7/post-freeze-V2 implementation must validate every output
name and every group key before creating an output directory.

The execution receipts hash the config, runner, scientific module, and protocol,
but not every imported shared I/O/provenance helper. The index therefore
preserves execution identity without claiming clean-clone replay
reproducibility. A future clean protocol must enumerate those transitive helper
dependencies in its implementation receipt.

## Chronology and execution identity

Both protocol documents and configurations were written before execution. The
replays used commit `087fab6ee586143940eb0efa6d512db628cdcd86` as the Git base,
with a dirty working tree; this is recorded rather than normalized away.

| Candidate | UTC execution | Protocol SHA-256 | Summary SHA-256 | Receipt SHA-256 |
|---|---|---|---|---|
| `ijds-binary-phase-geometry-2026-07-26-v6` | 08:48:18--08:48:19 | `64051f184ab77a7fa429d21a01740f1c8b028f37cc0b751f53a3f59db8e1b552` | `3f61bd3dc807635b2426d9e1dc5021fb66167fc5c9ff6c1642ce3a1c9f63f19f` | `73a34a52d1f71f1267b2e451ea5271573622bd0df51ab03dd3f48b60b27b9a13` |
| `ijds-postfreeze-derived-diagnostics-2026-07-26-v1` | 08:49:05--08:49:06 | `9de572399ee9603cd07dae3a730c66398948c3972bbfc5275cc9ddd6dbcf7083` | `00ec67641bf3adad0e359c5567e36e9baf4a2fd272e6fd7ef3fa9f0fda57b387` | `288ff00dccb29bad8dac4ae90cb006cf3389319d729eba3e601ff2d7a35f419e` |

The active source registry intentionally contains neither run, its inputs, nor
its implementation. Candidate chronology instead lives outside the active
registry in both protocols, both configurations, and
`configs/experiments/ijds_hash_bound_candidate_receipt_index_2026-07-26.yaml`.
That tracked index records the execution-time runner/module hashes plus all
local summary, receipt, and table descriptors. The outputs themselves remain
gitignored local quarantine: their recorded hashes do not imply availability
or reproducibility in a clean clone and do not confer promotion. No DVC pointer
was added; the registered pointer census remains 51.

## Candidate-only numerical results

These numbers are retained to check determinism and to decide whether a clean
rerun is scientifically worthwhile. They are not citable active results.

### Binary phase geometry V6

- Complete census: 200 learner--window--stratum cells.
- Exact order-statistic threshold reconciliation: 200/200, maximum absolute
  gap zero; no capped threshold.
- No-interleaving condition: 188/200; below-half calibration condition:
  184/200.
- Low-regime cells: 87/200, distributed 40, 40, 7, 0, 0 over the five ordered
  strata.
- Within-stratum fit-prevalence ranges are 0.0373--0.0525,
  0.0633--0.0915, 0.0865--0.1220, 0.1180--0.1610, and 0.1760--0.2180.
- The CatBoost W7--W8 threshold change is -0.776634 and the resolved-coverage
  change is -0.003673. Its absolute coverage change ranks fourth among the
  seven adjacent differences; the adjacent noncrossing change is -0.004118.

### Post-freeze derived diagnostics V1

- Sharp all-candidate prevalence range: 0.151163--0.183205. Across the five
  frozen learners, the lower endpoints of mean score minus outcome range from
  -0.074237 to -0.055975 and the upper endpoints from -0.042196 to -0.023934;
  all five upper endpoints are negative.
- Resolved-panel breakeven: 40/40 cells reconcile the mixture identity, with
  maximum residual `1.11e-16`. The resolved prevalence is 0.156167 and the
  breakeven range is 0.110670--0.147446; the relative reduction is
  0.0558--0.2910.
- P-value-selected minimum-reference-stratum magnitude: among the 31 cells
  already flagged by the registered joint-block diagnostic, the excess miss
  rate is 1.534--4.544 percentage points (median 2.939); among the nine
  nonflags it is 0.922--1.808 points (median 1.326). This is descriptive
  magnitude conditional on the already inspected reference, not a new test.

## Active objects that must be withdrawn pending a clean tagged rerun

The exact mathematical identities may remain: the two-mirror order statistic,
the exact half criterion with its conditions, the phase-margin reduction under
below-half calibration, the two-threshold crossed-mass identity, the sharp
completion formula for mean score minus outcome, and the resolved-panel mixture
identity. The following empirical objects cannot currently support active
claims:

1. The paper-facing S6I table
   `reports/crpto/tables/crpto_ijds_v4_tableS6I_stratum_phase_margins.csv`, its
   200-row census, and all archive counts/ranges derived from it (200/200, 188,
   184, 87, the 40/40/7/0/0 pattern, and the five prevalence ranges).
2. The realized phase-path claim and its numerical illustration: threshold
   change 0.776634, coverage change 0.003673, fourth-of-seven rank, adjacent
   change 0.004118, and any claim that the crossing step is not the largest.
   This affects the empirical portion of
   `geometry.coverage_response_depends_on_target_mass`, not the exact
   two-threshold theorem. It also includes the post-inspection selection of
   CatBoost score stratum 3, the exactly-one-transition requirement, and the
   W7--W8 adjacent-change ranking.
3. The paper-facing S2B table
   `reports/crpto/tables/crpto_ijds_v4_tableS2B_all_candidate_calibration_bias.csv`
   and the empirical assertion that all five upper endpoints are negative,
   including the learner-specific bounds and the numerical prevalence range.
4. The 40-cell resolved-panel breakeven range, resolved prevalence comparison,
   40/40 indicator, and 5.6%--29.1% relative-reduction statement. The algebraic
   mixture and breakeven formulas may remain without archive numbers.
5. The minimum-reference-stratum excess-miss ranges and medians in Supplement
   B.4.1. The underlying registered 31/40 cell flags remain active; only the
   later p-value-selected magnitude is quarantined.
6. Any V4 evidence-manifest fields, claim-ledger result pointers, manuscript or
   supplement prose, active-claim-registry entries, publication-target required
   artifacts, machine-readable ZIP members, or synchronization tests that
   present items 1--5 as active.

## Promotion checklist

1. Commit the final protocol, configuration, runner, implementation, and tests.
2. Resolve the V6 selection mismatch: predeclare the fixed retrospective
   CatBoost/stratum/ranking illustration, or remove all transition selection
   from the complete-table runner. Add the nonempty-class condition to the
   no-interleaving statement and fail-closed implementation contract.
3. Use new V7/V2 runners that reject absolute, separator-bearing, empty,
   reserved, or duplicated output filenames *before* creating run directories;
   require summary and receipt names to differ; validate group keys as finite
   exact integers before conversion; and bind shared I/O/provenance helpers in
   the implementation receipt.
4. Create protocol tags that resolve to that clean commit; do not back-date or
   retag either completed candidate.
5. Allocate new run tags and new immutable output directories.
6. Execute both replays from the clean tagged tree and record receipts that
   resolve the tags and scientific lock.
7. Register the fresh lineage and only then teach the paper builder to consume
   those registered outputs. The V4 builder must not recompute them internally.
8. If S6I is promoted, add its complete contractual fields to the
   machine-readable supplement and update the README, test census, and anonymity
   scanner in the same change.

No protected stage was executed and no protected artifact was read or written
by either candidate replay.
