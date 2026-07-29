# IJDS Marginal Mean-Score--Outcome Gap V2 Protocol

Required future protocol tag:
`protocol/ijds-marginal-mean-score-outcome-gap-2026-07-26-v2`.

Required future run:
`ijds-marginal-mean-score-outcome-gap-2026-07-26-v2`.

Status: **retrospectively locked before V2 execution**.

The archive, five-learner score family, endpoint census, and an earlier bundled
diagnostic replay have already been inspected. V2 is therefore retrospective
protocol discipline, not preregistration, confirmation, an untouched holdout,
or an independent experiment. The implementation step creates only this
protocol, its configuration, calculation module, runner, and tests. It must not
execute the empirical replay or create the required tag.

## 1. Scope and correction relative to V1

V2 contains exactly one estimand, named
`marginal_mean_score_outcome_gap`. The earlier replay combined three unrelated
products and conditioned one technical stop on the sign of a reported
endpoint. V2 imports none of its outputs, contains no resolved-panel breakeven
calculation, contains no selected-stratum magnitude, and has no stop, success
condition, promotion rule, or output filter based on the sign or ordering of a
scientific result.

All five frozen learners are a complete reporting census:

1. `catboost_platt`;
2. `numeric_logistic_platt`;
3. `catboost_monotonic_platt`;
4. `woe_scorecard_platform_platt`; and
5. `woe_scorecard_borrower_platt`.

No learner is selected, ranked, refit, rescaled, pooled, or passed to portfolio
optimization.

## 2. Immutable sources and descriptor reconciliation

V2 reads only:

1. the V1b outcome-free five-learner score freeze
   `ijds-credit-risk-controls-2026-07-13-v1b`;
2. its nested `scores.parquet` descriptor; and
3. the active V5 execution receipt and reason-audited summary; and
4. the summary's nested
   `endpoint_resolution_audit.parquet` descriptor from
   `ijds-credit-risk-controls-2026-07-15-v5`.

The configuration pins path, byte count, and SHA-256 for the V5 receipt and
summary, V1b freeze, score table, and endpoint-reason table. Before reading
either Parquet table, the runner verifies each configured descriptor against
disk. It then requires exact descriptor equality along both parent chains:

- V5 receipt -> V5 summary and V1b source freeze;
- V5 summary -> V1b source freeze -> score table; and
- V5 summary -> endpoint-reason table.

The endpoint-reason rows embedded in the V5 summary must also equal the
hash-verified endpoint-reason table after a deterministic column and row
normalization. A self-declared child path, a matching filename with different
bytes, or agreement at only one level stops the replay.

The score freeze must retain its original no-outcome contract. V2 reads only
`id`, `issue_d`, `design_split`, and the five declared score columns. It never
loads a row-level evaluation label, raw archive, conformal recipe, prediction
set, allocation, or protected paper-facing artifact.

## 3. Candidate and endpoint census

The target is the exact status-independent `primary_oot` population from April
2016 through June 2017. It contains `N=376,890` unique, nonmissing candidate
identifiers and exactly the fifteen declared issue months. All five score
columns must be present on every one of those same rows, finite, numeric, and
inside `[0,1]`. The runner records a deterministic SHA-256 of the sorted target
identifier census.

The active September 30, 2020 endpoint uses the established six-calendar-month
Charged Off availability lag. Its five reason rows are fixed as follows:

| Endpoint reason | Candidate rows | Resolved rows | Unresolved rows |
|---|---:|---:|---:|
| Fully Paid by reconstructed cutoff | 307,842 | 307,842 | 0 |
| Charged Off by reconstructed cutoff | 56,972 | 56,972 | 0 |
| Nonterminal or unresolved status | 11,551 | 0 | 11,551 |
| Terminal after reconstructed cutoff | 47 | 0 | 47 |
| Terminal availability date missing | 478 | 0 | 478 |

Thus the active totals are 364,814 resolved outcomes, including
`D_R=56,972` resolved defaults, and `U=12,076` unresolved outcomes. Every
reason row must satisfy `candidate_rows = resolved_rows + unresolved_rows`,
the five reasons must be unique and exhaustive, and both the row-level and
aggregate counts must match the locked configuration.

The archive is not represented as a verified point-in-time snapshot, and the
reconstructed availability dates are not claimed to be observed operational
event dates. V2 inherits those endpoint boundaries without weakening them.

## 4. Estimand and sharp identification interval

For learner `j`, let `p_ij` be the frozen score of target candidate `i`, and
let

`pbar_j = (1/N) sum_i p_ij`.

Resolved outcomes retain their active reconstructed binary values. Each of the
`U` unresolved outcomes may independently be either zero or one, with no
missingness model or distributional restriction. Therefore

`E_N[Y] in [D_R/N, (D_R+U)/N]`,

and the sharp finite-archive interval is

`E_N[p_j-Y] in [pbar_j-(D_R+U)/N, pbar_j-D_R/N]`.

Sharpness is constructive: assigning every unresolved outcome to one attains
the lower endpoint, and assigning every unresolved outcome to zero attains the
upper endpoint. The width is exactly `U/N` for every learner. This is a
partial-identification interval over binary completions, not a sampling
interval, confidence interval, posterior interval, forecast for another
population, or causal estimand.

The runner reports the two endpoints for every learner exactly as obtained.
Intervals below zero, above zero, crossing zero, or touching zero are all
valid reportable outcomes and never alter execution.

## 5. Fail-closed execution and immutable outputs

The runner accepts only the canonical tracked configuration
`configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v2.yaml`.
It requires a clean current HEAD resolved by the future protocol tag before
opening any scientific source. The configuration, protocol, runner, and module
are hashed at the start and again before output creation; implementation drift
stops the replay.

The fresh run writes only:

- `evaluation/marginal_mean_score_outcome_gap.parquet` under the isolated data
  run directory;
- `marginal_mean_score_outcome_gap_summary.json`; and
- `execution_receipt.json` under the isolated model run directory.

All writes are atomic and hash-described. Both run directories must be absent
at preflight and immediately before creation; existing paths are never
overwritten. The receipt binds the clean protocol commit, protocol and config,
implementation files, parent and nested sources, outputs, runtime, environment,
and initial/final Git state.

## 6. Stop rules and interpretation boundary

Stop before scientific output if the clean tag, canonical config, run identity,
implementation hash, source identity, outer descriptor, nested descriptor,
learner list, score-column list, target ID census, issue-month set, score domain,
endpoint reason partition, or endpoint totals differ from the locked contract.
Also stop on duplicate or missing identifiers, nonexact or negative counts,
nonfinite arithmetic, reversed bounds, output aliasing, path escape, or a
pre-existing run directory.

Do **not** stop, select, redesign, narrow, or rerun because of the numerical
value, sign, width, or learner ordering of a completed interval.

V2 supports only a deterministic description of the five frozen mean scores
relative to the partially identified mean binary outcome on this finite target
archive. It does not establish temporal transport, exchangeability,
label-conditional validity, a model winner, a shift mechanism, fairness,
selected-set or funded-set validity, causal interpretation, prospective
performance, policy direction, or deployment readiness.

After a separate commit and creation of the required clean tag, the only
authorized empirical invocation is:

```powershell
uv run --locked python scripts/experiments/run_ijds_marginal_mean_score_outcome_gap_v2.py `
  --config configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v2.yaml
```

The present implementation step must not execute that command, register DVC
pointers, or promote the lineage to any paper-facing source.
