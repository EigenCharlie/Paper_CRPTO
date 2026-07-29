# Corrected Binary Phase Geometry V6 Audit Specification

Prospective run tag: `ijds-binary-phase-geometry-2026-07-26-v6`

Status: **retrospectively locked correction; no independent V6 run had executed
when this operational lock was written**

This specification was written after the archive, W7--W8 crossing, failed V5
theory, and publication-derived phase numbers had been inspected. It is neither
preregistration nor confirmatory evidence. It freezes the corrected computations
and failure conditions that any future V6 derivation must satisfy before
promotion.

## 1. Purpose

Audit three distinct binary-set objects without conflating them:

1. the exact calibration order statistic and its conditional phase diagnostic;
2. the exact coverage change on a common target panel between any two thresholds;
3. sharp outcome-free miscoverage bounds of a fixed allocation from empty and
   full binary sets.

No object below transfers a conformal guarantee to the temporal target or funded
set, identifies a shift mechanism, or selects a learner, window, stratum, ruler,
coordinate, cap, scenario, comparator, or policy.

## 2. Parent inputs

- Hash-registered frozen residual-fit rows from the active five-learner credit
  control lineage.
- The active frozen 200-row learner--window--stratum table.
- If target-band or allocation-set quantities are derived, the already frozen
  target scores, endpoint availability, binary-set endpoints, and allocations
  from the active V4 evaluation lineage; no refit or reoptimization is permitted.

Every input descriptor, row role, and key census must be recorded in the V6
receipt. Input paths alone are not provenance.

## 3. Exact calibration geometry

For each frozen stratum with `n` rows, binary labels, scores in `[0,1]`, and
`k=ceil((n+1)(1-alpha))`, form

`R = {{p_i:Y_i=0}} (+) {{1-p_i:Y_i=1}}`.

If `k<=n`, the threshold is `R_(k)`. If `k=n+1`, record the active binary cap
`c=1`, which is set-equivalent to `+infinity`; do not assign a phase regime.

Record

- `A=#{Y=0,p<1/2}` and `B=#{Y=1,p>1/2}`;
- the exact criterion `c<1/2 iff A+B>=k`;
- `n-k=floor(alpha*(n+1))-1`;
- `m=D-(n-k)` only with its condition `max_i p_i<1/2`;
- the no-interleaving condition separately.

Under no interleaving, `m<=0` selects the relevant nondefault order statistic and
`m>=1` gives `c=1-p^1_[m]`. The `m=0` and `m=1` formulas belong to their own
calibration blocks and must not share fitted class maxima.

## 4. Exact target-band identity

For a common fixed target distribution and `0<=c_L<c_H<=1`, compute or verify

`Cov(c_H)-Cov(c_L)
 = P(Y=0,c_L<p<=c_H) + P(Y=1,1-c_H<=p<1-c_L)`.

The endpoint conventions are part of the contract. For unresolved labels, define
`d_i(y)=1{|y-p_i|<=c_H}-1{|y-p_i|<=c_L}` and obtain sharp bounds by adding the
loan-wise minima and maxima over `y in {0,1}`. Threshold distance alone must never
be called a coverage bound or continuity result.

## 5. Sharp outcome-free set bounds

For a fixed nonnegative allocation `a` and declared positive normalizer `B_0`,
binary endpoints `(l_i,u_i)` imply

`MC_L=sum a_i*1{l_i>0 and u_i<1}/B_0`,

`MC_U=sum a_i*(1-1{l_i=0 and u_i=1})/B_0`.

The lower endpoint is exposure in empty sets; the complement of full-set exposure
is the upper endpoint. Both are sharp over unrestricted binary completions. The
separate share `sum a_i*1{u_i=1}/B_0` is exposure able to cover `Y=1`, not
conditional positive-class coverage.

## 6. Failure conditions

A V6 derivation stops without promotion if any declared key is duplicated or
missing; a score or label leaves its domain; counts, ranks, order statistics, or
frozen thresholds fail to reconcile; a claimed target comparison uses different
target panels; endpoint conventions differ; allocation weights are negative;
the normalizer is nonpositive; or an external archive enters the computation.

Every fail-closed branch requires a unit test. A stopped run remains provenance
and cannot be narrowed after inspection.

## 7. Operational lock before the V6 replay

The only permitted first replay uses:

- config: `configs/experiments/ijds_binary_phase_geometry_2026-07-26_v6.yaml`;
- runner: `scripts/experiments/run_ijds_binary_phase_geometry_v6.py`;
- run tag: `ijds-binary-phase-geometry-2026-07-26-v6`;
- input rows: the hash-declared V1b residual-fit audit and the hash-declared
  V1 exchangeability stratum table;
- contained data output:
  `data/processed/experiments/ijds_audit/ijds-binary-phase-geometry-2026-07-26-v6/stratum_phase_margins.csv`;
- contained model outputs:
  `models/experiments/ijds_audit/ijds-binary-phase-geometry-2026-07-26-v6/binary_phase_geometry_v6_summary.json`
  and `execution_receipt.json`.

The runner must reject pre-existing output directories and must not read any
paper-facing V4 JSON, table, figure, protected report, or exploratory V5/V6
output. It must bind the protocol, config, runner, reusable geometry module,
and every scientific input by byte count and SHA-256. Because the current
worktree cannot create a Git tag, a first replay may be hash-bound and must
record that limitation honestly; it must not invent a `protocol_commit`.
Promotion to a clean tagged lineage requires a fresh run tag and rerun, not a
retroactive commit identity for this execution.

The S6I table must contain, for every one of the 200 declared strata, the
calibration counts `A=#{Y=0,p<1/2}` and `B=#{Y=1,p>1/2}`, the exact half
criterion, capped-threshold flag, rank, `n-k`, its closed form, phase margin,
both separation diagnostics, score extrema, and the recomputed threshold.
Omitting these fields fails the publication-table contract.

## 8. Permitted interpretation

The V6 objects may support exact finite-sample bookkeeping and explicitly
conditional archive diagnostics. They may not support universal score-bin
degeneracy, continuity, an outcome-free floor based only on `l_i>0`, an optimizer
anti-selection theorem, external replication, selected/funded-set validity, a
split-conformal theorem-failure claim, or causal, prospective, deployment, and
fair-lending conclusions.
