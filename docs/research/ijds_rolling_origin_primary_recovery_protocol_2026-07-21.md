# IJDS 2016 Primary-Origin Three-Month Recovery Protocol V1

## Status and defect

This is a retrospectively locked lineage correction after the archive and the
rolling-origin results were inspected. The active rolling-origin protocol
requires exactly three issue months at every feasible origin. The paper-facing
evidence builder nevertheless compared the complete April 2016--June 2017
primary evaluation (15 months) with the April--June 2017 rolling evaluation
(3 months). The two horizons therefore did not estimate the locked common-
horizon recurrence question.

This recovery reconstructs only the missing April--June 2016 CatBoost coverage
object. It is error correction, not preregistration, prospective validation, an
independent replication, or a new model search. The historical 15-month V4
evaluation and the 2017 rolling artifacts remain immutable provenance.

Required tag:
`protocol/ijds-rolling-origin-primary-recovery-2026-07-21-v1`.

## Immutable inputs

- Outcome-free V4 freeze:
  `ijds-binary-geometry-frontier-v4-2026-07-12-v1`, protocol commit
  `2f8a7606e4eb65aa3ae3701fb3af8d9a51c953cd`, freeze SHA-256
  `c2b3dc2d18c9fed80708682d5a0369c80c89643e2d28024418522d954ebe667c`.
- Frozen score artifact SHA-256:
  `4053efdbf13066355bb772233231e5fe4ccb436ca75aaf873fb14e213c1e319c`.
- Frozen residual-recipe artifact SHA-256:
  `0874a5e9eea37adce302f4a059d4ccde5570230a7fdabcc29ceab410988f207a`.
- Frozen residual-fit audit SHA-256:
  `a80efcedfe749c52c0624536d361a8b1e9e5121901ee9b91ad4c746c68da107c`.
- Raw archive SHA-256:
  `5878af2a088f8ab5214c9337289fb8b5eb6c6338fd3f417b6cdc18513dc6f35f`.
- Raw archive, score values, taxonomy, residual recipes, alpha 0.10, and all
  endpoint rules remain unchanged. No learner, calibrator, taxonomy, or recipe
  is refit.

Only `pd_catboost_platt`, the canonical five-stratum recipes, and all eight
pre-existing six-month residual windows enter this recovery. The logistic and
other learner controls remain part of the separate five-model primary audit;
they are not silently added to this CatBoost-only two-origin sensitivity.

## Locked horizon and endpoint

Candidate membership is selected mechanically from frozen score identities and
issue dates. The common primary horizon is exactly:

`{2016-04, 2016-05, 2016-06}`.

The historical full-primary count of 376,890 or any 15-month period set is an
explicit stop condition. Later primary months cannot rescue or dilute this
origin.

Outcomes use the V4 reconstructed endpoint at September 30, 2020. Fully Paid is
available at last-payment month-end; Charged Off is available at last-payment
month-end plus six months. A terminal outcome is resolved only when its
availability date is nonmissing and no later than the cutoff. Terminal missing
dates, terminal dates after the cutoff, and nonterminal statuses remain distinct
unresolved reasons.

The already diagnosed identity census is used only as a reconciliation
criterion, not as empirical evidence to be estimated again:

| Issue month | Candidates | Resolved | Unresolved |
|---|---:|---:|---:|
| 2016-04 | 28,106 | 28,071 | 35 |
| 2016-05 | 21,831 | 21,803 | 28 |
| 2016-06 | 24,600 | 24,569 | 31 |
| Total | 74,537 | 74,443 | 94 |

The expected reason partition is 62,498 Fully Paid by the cutoff, 11,945
Charged Off by the cutoff, and 94 terminal outcomes with no reconstructible
availability date. Any mismatch stops the recovery rather than adapting the
horizon or endpoint.

## Estimand and complete reporting

For each of the eight frozen windows, apply the five-stratum absolute-residual
recipe to every candidate score. Let `M_i(0)` and `M_i(1)` denote binary
miscoverage under the two attainable outcomes. Resolved rows use their observed
outcome; unresolved rows contribute their loan-wise minimum and maximum. The
sharp all-candidate endpoints are

`coverage_lower = 1 - mean(miss_high)`

and

`coverage_upper = 1 - mean(miss_low)`.

Empty prediction sets are never covered and sets containing both binary
outcomes are always covered; neither case is replaced by a blanket unresolved-
failure/success rule. Report all eight windows, including resolved coverage,
sharp lower and upper endpoints, and binary-set geometry. No window is selected.

The two-origin CatBoost coverage failure may be called recurrent only if all
eight recovered 2016 upper endpoints and all eight existing 2017 upper
endpoints are below 0.90. If any recovered upper endpoint reaches 0.90, the
recurrence claim must be withdrawn and the complete mixed result reported.

## Reproducibility and interpretation boundary

The runner must require a clean HEAD at the protocol tag, verify every imported
descriptor, write to the fresh run tag
`ijds-rolling-origin-primary-recovery-2026-07-21-v1`, and emit atomic hashed
artifacts plus an execution receipt. It may not execute a protected DVC stage,
modify `EXTRACTION_MANIFEST.json`, overwrite V4 or rolling-origin history, or
pass an outcome-derived field into fitting or selection.

This recovery authorizes at most a two-origin retrospective recurrence statement
for the declared CatBoost coverage audit. It does not authorize temporal
invariance, an independent-replication count, a selected model or window,
selected-set conformal validity, a funded-set guarantee, causality, external
validity, or deployment guidance.

After committing and tagging the complete protocol implementation on a clean
HEAD, execute:

```powershell
uv run --locked python scripts/experiments/run_ijds_rolling_origin_primary_recovery.py `
  --config configs/experiments/ijds_rolling_origin_primary_recovery_2026-07-21_v1.yaml
```

Only after successful immutable output creation may the two fresh run
directories be added as new DVC pointers and registered as active sources.
