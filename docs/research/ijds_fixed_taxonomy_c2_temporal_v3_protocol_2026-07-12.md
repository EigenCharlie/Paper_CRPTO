# Fixed-Taxonomy Temporal Sensitivity V3 Protocol

## Status

This is a locked, retrospective design-sensitivity run over a previously
inspected archive. It does not replace V1/V2 by construction and cannot promote
a policy, comparator, calibration window, or favorable result. The required
tag is `protocol/ijds-fixed-taxonomy-c2-temporal-v3-2026-07-12-v1`.

## Fixed Research Question

Does the V2 temporal-coverage finding, and the absence of a comparator-stable
portfolio direction, survive when residual calibration uses the latest
contiguous issue-month window whose labels each exceed 99% observability by the
unchanged March 31, 2016 information cutoff?

## Frozen Elements

- Raw Lending Club snapshot, 36-month term, endpoint taxonomy, information
  cutoff, CatBoost specification, 2007--2010 development block, 2011 Platt
  block, 2011 score-taxonomy source, nine policies, monthly OOT menus, payoff,
  solver, purpose-cap grid, LGD grid, C0/C1/C2 definitions, broad point-cap
  frontier, simulation, and sharp outcome bounds remain unchanged from V2.
- The residual window is July 2012 through January 2013. In a pre-result raw
  observability audit, every included issue month exceeds 99% label
  availability under the canonical six-month charge-off lag.
- Outcome-free C1 development menus are February through December 2013. Their
  outcomes are not required or read.
- Label lags `{0,3,6,12}` are a closed coverage-only sensitivity. They cannot
  select a recipe or trigger portfolio reoptimization.

## Comparator Scopes

Three scopes must be reported without choosing among them:

1. `core_rules`: C0 same-cap, C1 development-fixed, and C2 contemporaneous.
2. `development_supported`: C1, C2, and broad-frontier caps inside the range
   obtained by rounding the nine outcome-free development funded-PD targets
   outward to the fixed 0.0025 grid.
3. `broad_stress`: C0, C1, C2, and every cap from 0.05 to 0.12.

The second scope is a declared design-sensitivity envelope, not an identified
counterfactual set. The third is deliberately broad stress evidence.

## Decision Rules

- Report all nine policies and all declared sensitivities.
- If late-window coverage reaches 0.90, retire any claim that temporal failure
  is invariant to a maturity-safe calibration window.
- If comparator scopes disagree, report scope dependence; do not select the
  scope yielding the preferred direction.
- If V3 and V2 differ, retain both as a timing sensitivity and explain the
  estimand change. Do not overwrite either run.
- No result from this run is confirmatory, prospective, causal, or
  preregistered.

## Reproducibility Contract

The run must start from a clean commit carrying the protocol tag, write to a
fresh `ijds_prefreeze` run directory, freeze all allocations before joining
outcomes, use HiGHS only, record exact source hashes, and receive new DVC
pointers. Historical champion stages and `EXTRACTION_MANIFEST.json` remain
untouched.
