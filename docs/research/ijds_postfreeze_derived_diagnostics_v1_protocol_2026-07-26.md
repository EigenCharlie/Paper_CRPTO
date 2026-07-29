# Post-freeze Derived Diagnostics V1 Protocol

Run tag: `ijds-postfreeze-derived-diagnostics-2026-07-26-v1`

Status: **retrospectively locked before the first contained replay**

This protocol was written after all source archives, the 40 coverage cells,
the 200 joint-block stratum results, and exploratory publication-derived
numbers had been inspected. It is not preregistration, confirmation, an
untouched holdout, or an independent experiment. It predeclares a complete
deterministic replay of three distinct derived diagnostics. They must remain
separate in outputs and interpretation.

## 1. Locked sources

Only these already frozen sources may enter:

1. the V1b outcome-free five-learner score table;
2. the active V5 endpoint-reason summary;
3. the complete V1 conformal-set diagnostic table;
4. the complete V1 joint-block stratum and learner-window tables.

The config must contain exact paths, byte counts, and SHA-256 digests, and the
runner must reconcile nested artifact descriptors in the parent summaries.
No paper-facing V4 JSON/CSV, protected report, exploratory output, refit,
recalibration, endpoint reconstruction, hypothesis retest, or optimization is
permitted.

## 2. S2B: sharp all-candidate score-minus-outcome bounds

For every one of the five frozen scores, let `pbar` be its mean over the exact
376,890 primary-OOT candidates. Let `D_R=56,972` be resolved defaults and
`U=12,076` unresolved outcomes under the active six-month endpoint contract.
The all-candidate default prevalence and mean calibration residual obey

`pi in [D_R/N,(D_R+U)/N]`,

`mean(p-Y) in [pbar-(D_R+U)/N,pbar-D_R/N]`.

These are sharp deterministic completion bounds, not sampling intervals.
Report all five learners; select none. Stop on a changed score census,
duplicated candidate identifier, nonfinite or out-of-domain score, changed
endpoint-reason partition, or a nonnegative upper residual endpoint. The last
rule is a declared claim gate, not permission to drop a failing learner.

## 3. Resolved-panel prevalence breakeven

For every one of the complete 40 learner-window cells, verify on the common
resolved panel

`C=(1-pi_R) C_0 + pi_R C_1`.

Holding that cell's realized class-conditional coverages fixed, define the
algebraic prevalence at nominal coverage `1-alpha` by

`pi_star=(C_0-(1-alpha))/(C_0-C_1)`.

Report every cell and the relative distance `(pi_R-pi_star)/pi_R`. Stop on a
duplicated or missing learner-window key, a varying resolved census, a mixture
residual above `1e-12`, `C_0<=C_1`, or `pi_star` outside `[0,1]`. This is a
resolved-panel reparameterization only. It is not completion-invariant,
causal label-shift attribution, an intervention target, required prevalence
change, future coverage, or learner ranking.

## 4. Minimum-reference-stratum descriptive magnitude

Within each of the same 40 learner-window cells, select the score stratum with
the smallest already frozen exact joint-block log tail area; ties are broken
by the smallest zero-based `conformal_group`. For that stratum report

`100 * (minimum-completion miss rate - finite-rank null expected miss rate)`

in percentage points. Join the already frozen cell-level nominal Holm flag and
summarize flagged and nonflagged cells separately. This is a post-inspection,
p-value-selected descriptive magnitude for an existing reference diagnostic.
It is not a new test family, unbiased effect estimate, controlled selective
inference, mechanism estimate, ordinary pointwise theorem test, or 200-stratum
FWER claim.

Stop on an incomplete 5 by 8 by 5 stratum grid, incomplete 5 by 8 cell grid,
duplicate keys, nonfinite inputs, a stratum outside `0,...,4`, changed 31/40
flag census, or a failed deterministic tie rule.

## 5. Execution and outputs

- config: `configs/experiments/ijds_postfreeze_derived_diagnostics_2026-07-26_v1.yaml`;
- runner: `scripts/experiments/run_ijds_postfreeze_derived_diagnostics_v1.py`;
- data directory:
  `data/processed/experiments/ijds_audit/ijds-postfreeze-derived-diagnostics-2026-07-26-v1/`;
- files: `all_candidate_calibration_bias.csv`,
  `resolved_coverage_breakeven.csv`, and
  `minimum_reference_stratum_effect.csv`;
- model directory:
  `models/experiments/ijds_audit/ijds-postfreeze-derived-diagnostics-2026-07-26-v1/`;
- files: `postfreeze_derived_diagnostics_summary.json` and
  `execution_receipt.json`.

Output directories are immutable: any pre-existing path stops the run. The
receipt must bind the protocol, config, runner, calculation module, inputs,
outputs, runtime, and initial/final Git state. A hash-bound replay from an
uncommitted protocol must say so and must not fabricate a protocol tag or
commit. A later clean tagged promotion requires a new tag and fresh run.

## 6. Claim boundary

All three products are deterministic retrospective descriptions of frozen
objects. They authorize no learner/window/stratum selection, universal
underprediction mechanism, causal or prospective claim, selected/funded-set
validity, external generality, policy direction, or deployment conclusion.
