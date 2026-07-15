# IJDS Missingness Sensitivity Protocol

## Status and Question

This protocol closes the two sensitivity requirements declared by the full raw
data audit. The archive and active results have already been inspected, so the
exercise is retrospective discipline rather than preregistration or an
untouched confirmation.

Question: does the primary CatBoost candidate-coverage conclusion depend on the
frozen conventions for structurally nullable delinquency recency and the
partially supported legacy bankruptcy count?

Required tag: `protocol/ijds-missingness-sensitivity-2026-07-15-v1`.

## Fixed Information Contract

- Use the active 640,543-row status-independent design and every eligible row.
- Preserve the PD-development, 2011 Platt/taxonomy, eight residual-window, and
  primary OOT blocks.
- Preserve seed 42, CatBoost hyperparameters, the five-stratum taxonomy, alpha
  0.10, finite-sample ranks, and the V4 endpoint reconstruction.
- Import the active CatBoost score and recipe as the baseline by hash.
- Fit alternatives before loading the primary OOT endpoint. Scores, taxonomies,
  recipes, and fit audits must be frozen and hashed before evaluation.
- The alternatives are coverage controls only. They do not enter portfolio
  optimization and cannot select a model, feature convention, residual window,
  or endpoint.

## Complete Specification Family

All three specifications are co-reported:

1. **Active sentinel convention.** Retain `delinq_recency=999` when
   `mths_since_last_delinq` is missing and `has_bankruptcy=0` when
   `pub_rec_bankruptcies` is missing. Import the frozen V4 score and recipes.
2. **Explicit missing indicators.** Retain the active mapped features and add
   `delinq_recency_missing` and `bankruptcy_count_missing`.
3. **Native numeric missingness.** Remove mapped `delinq_recency` and
   `has_bankruptcy`; replace them with numeric raw delinquency recency and
   bankruptcy count, preserving `NaN` for CatBoost's native missing-value
   handling.

No hybrid or winning variant may be created after evaluation. The two
alternatives isolate sensitivity to the encoding contract; they are not a new
model contest or a claim that missingness is informative, ignorable, or causal.

## Outputs and Stop Rules

- Report all eight five-stratum primary OOT sharp coverage intervals and
  descriptive AUC, Brier, calibration, KS, Gini, and average precision for all
  three specifications.
- Report the raw missingness census by temporal role for both source fields.
- Stop before evaluation if the baseline score/recipe descriptors differ, a
  taxonomy edge repeats, a canonical residual group has fewer than 1,000 rows,
  or any OOT outcome-derived column reaches fitting.
- If any alternative upper coverage bound reaches 0.90, withdraw a
  missingness-insensitive coverage statement and report the complete mixed
  result. Do not select a convention that preserves failure.
- If every alternative remains below 0.90, report robustness only over these
  three declared encodings. Do not claim missing-at-random identification,
  general missing-data robustness, or model superiority.

The run writes only fresh experiment directories and never modifies protected
historical artifacts or `EXTRACTION_MANIFEST.json`.
