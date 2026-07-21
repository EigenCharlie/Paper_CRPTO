# IJDS Exact Exchangeability/Transport Test Protocol V1 - 2026-07-21

## Status and question

This lineage adds a complete retrospective falsification test for the
split-conformal exchangeability null. The Lending Club archive, the active
coverage results, their class asymmetry, and an exploratory implementation and
approximate rejection pattern from this test family were already inspected.
V1 therefore fixes a complete reproducible reporting analysis after inspection;
it is not preregistration, confirmation, an untouched holdout, independent
inference from the exploratory analysis, or a conformal repair.

The question is deliberately narrower than "does conformal prediction work?":
within each frozen learner--window--score-stratum cell, is the sharp minimum
number of primary-OOT misses compatible with the exact continuous-rank count
law, used as a conservative upper-tail bound when scores tie?

Required protocol tag:
`protocol/ijds-exchangeability-transport-test-2026-07-21-v1`.

Required run:
`ijds-exchangeability-transport-test-2026-07-21-v1`.

## Immutable sources and complete grid

The runner imports, without refitting or retaxonomizing, the outcome-free
five-model freeze `ijds-credit-risk-controls-2026-07-13-v1b` and reconstructs
the active six-month endpoint through the reason-audited V5 configuration.
The source freeze SHA-256 is
`da4805e644bcf5decfbb0a67c0c81a5b9dd61f3ab2e17d3dc5264100e7eb4d35`.
The frozen score, residual-recipe, and residual-fit-audit SHA-256 values are,
respectively,
`5795bc0a75be90e86d37cf7d297f4b4fd6e6604b38f8179bc5042c024a53a8dc`,
`969ecbefe46bec4893a03be57385eda29b33dd291d73e7c0120f6d488a9e9936`,
and
`396c30d9bec7d222220cfe6f9870ab4994cf5c33e6da8c9e4ebbd99153155353`.

The reporting grid is fixed at:

- five learner specifications;
- all eight six-month residual windows;
- all five frozen outcome-free score strata; and
- all 376,890 status-independent primary-OOT candidates from April 2016
  through June 2017 under the active endpoint census of 364,814 resolved and
  12,076 unresolved outcomes.

This yields 200 stratum tests nested in 40 learner--window cells. No learner,
window, stratum, endpoint completion, or p-value threshold is selected after
outcomes. Overlapping windows and common candidate rows are retained as
dependent tests, not counted as independent replications.

The five score-taxonomy edges for each learner were learned once on the
status-independent 2011 score block, before and separately from both the
residual windows and target panel. The runner verifies the declared taxonomy
method and provenance and requires identical edges across all eight windows
for a learner. A grouping learned asymmetrically on the calibration residuals
would not inherit this conditional-exchangeability argument.

## Exact rank law and tie-safe exchangeability test

Fix one learner, residual window, and score stratum. Let `n` be its calibration
count, let

\[
r=\left\lceil(n+1)(1-\alpha)\right\rceil,
\qquad \alpha=0.10,
\]

and let `q` be the attained `r`-th ordered calibration residual. The run stops
if the frozen recipe uses an unattained rank (`r > n`) or if the fit audit does
not reproduce the declared count, group, rank, threshold, endpoints, and
coverage flags.

First suppose that the `n` calibration residuals and `m` target residuals are
jointly continuous and exchangeable within this fixed stratum. Their combined
ranks are uniformly assigned to the calibration and target indices. Counting
the target ranks above the `r`-th calibration rank gives

\[
M\sim\operatorname{BetaBinomial}(m,n+1-r,r).
\]

This is an exact rank-combinatorial law under continuous joint exchangeability;
it does not require an i.i.d. representation. Under the stronger i.i.d.-continuous
model with CDF `F`, the same law can equivalently be represented by
`1-F(q) ~ Beta(n+1-r,r)` followed by a conditionally Binomial target count.

The implementation also remains valid when residuals tie. Append independent
continuous auxiliary tie breakers to every calibration and target score and
order the pairs lexicographically. The paired scores are almost surely tie-free
and exchangeable, so their target exceedance count `M*` has the Beta--Binomial
law above. The fitted scalar threshold is unchanged, and every deterministic
strict miss has a lexicographic miss; hence `M <= M*` pointwise. Therefore the
same upper tail is a conservative p-value under arbitrary joint exchangeability
with ties, and is exact for the continuous case. Auxiliary tie breakers are a
proof device only: V1 neither generates them nor changes any prediction set.

The one-sided stratum p-value is the finite discrete tail

\[
p_g=\Pr\{M\ge M_{g,\min}\}.
\]

The implementation evaluates the complete Beta--Binomial tail in log space;
it does not use a normal, binomial, chi-squared, or asymptotic approximation.
The finite-sample null miss rate is `(n + 1 - r)/(n + 1)`, not silently
replaced by 0.10.

The runner reports the number of calibration residuals tied at every fitted
threshold and target-threshold tie counts for resolved labels and both possible
unresolved labels. A singleton calibration tie, or even no observed target tie,
is consistent with but does not prove joint continuity. With ties, the
Beta--Binomial count law is not asserted to be the exact deterministic-score
law; its upper tail is used conservatively through the domination argument
above. No randomized prediction rule or post hoc tie correction is permitted
in V1.

## Sharp handling of unresolved endpoints

For resolved candidate `i`, its binary miss indicator is fixed. For unresolved
candidate `i`, let `M_i(0)` and `M_i(1)` be the two attainable miss indicators
under the frozen interval. The primary test count is

\[
M_{g,\min}
=\sum_{i\in R_g}M_i(Y_i)
 +\sum_{i\in U_g}\min\{M_i(0),M_i(1)\}.
\]

Because the binary completions are unrestricted and additive, this minimum is
sharp loan by loan. The upper-tail p-value is nonincreasing in the miss count,
so using `M_{g,min}` gives the supremum p-value over all unresolved binary
completions. A rejection based on it is therefore robust to every such
completion. The sharp maximum miss count and both coverage endpoints are also
reported, but they do not enter the rejection rule. No missingness model,
imputation distribution, MAR assumption, or selected completion is introduced.

## Hierarchical multiplicity contract

The familywise level is fixed at 0.05.

1. Within each learner--window cell, the five stratum p-values form the
   Bonferroni omnibus p-value
   `p_cell = min(1, 5 * min_g p_g)`.
2. The 40 cell p-values are adjusted by Holm's step-down procedure. If
   `p_(j)` is the `j`-th ordered cell p-value, testing continues only while
   `p_(j) <= 0.05/(41-j)`.
3. Raw log p-values, ordinary p-values, within-cell Bonferroni values, Holm
   ranks, critical values, adjusted values, and step-down decisions are all
    persisted. Log values remain authoritative if ordinary p-values underflow.

The stratum-level Bonferroni flags are diagnostics within their own
learner--window cell; they do not control FWER over the family of 200 strata and
must not be called globally significant or incompatible. Formal rejection
claims in V1 are restricted to the 40 Holm-adjusted learner--window cells.

Bonferroni and Holm control familywise error without independence assumptions;
therefore no independence claim is made for overlapping windows, shared
learners, or the common target panel. The cell null is the intersection of its
five stratum-specific exchangeability nulls. The 0.05 level is nominal
within-lineage FWER for this fixed post-inspection family, not study-wide
confirmatory error control over earlier analytical choices.

## Interpretation and stop rules

- Rejection means incompatibility with within-stratum exchangeability after
  the locked hierarchy; the test is exact for continuous scores and
  conservative with ties. It does not identify
  covariate shift, label shift, calibration drift, censoring, model error, or
  any other cause.
- Failure to reject does not establish exchangeability, transportability,
  prospective coverage, or adequate power.
- This test does not create label-conditional, selected-set, funded-set,
  latent-PD, causal, fairness, policy, or deployment validity.
- Report all 200 strata and all 40 cells. Do not promote a favorable learner,
  window, stratum, or subset.
- Stop on any source hash, run identity, endpoint census, issue-month set,
  learner--window--stratum grid, attained rank, row-level fit-score
  reconciliation, active V5 coverage reconciliation, or finite-tail failure.
- Stop if any output directory already exists. Never overwrite a historical
  artifact, modify `EXTRACTION_MANIFEST.json`, or execute a protected DVC
  stage.

## Reproducibility contract

The protocol, config, reusable implementation, runner, and tests must be
committed and tagged before any empirical execution. The runner requires a
clean HEAD exactly at the required tag and writes only fresh isolated paths
under its run tag. It emits two Parquet tables, one hash-described summary, and
one execution receipt; all writes are atomic.

After committing and tagging the complete implementation on a clean HEAD,
execute only:

```powershell
uv run --locked python scripts/experiments/run_ijds_exchangeability_transport_test.py `
  --config configs/experiments/ijds_exchangeability_transport_test_2026-07-21_v1.yaml
```

No empirical run is part of the protocol-implementation step.
