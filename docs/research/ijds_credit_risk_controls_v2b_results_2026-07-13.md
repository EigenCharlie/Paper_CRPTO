# IJDS Credit-Risk Controls V2b Results - 2026-07-13

## Status And Lineage

V2b is the complete no-selection evaluation of the V1b frozen learner family.
It verified the V1b freeze SHA-256
`da4805e644bcf5decfbb0a67c0c81a5b9dd61f3ab2e17d3dc5264100e7eb4d35`
and reproduced the 3,520-row V2 temporal-coverage frame exactly. All 30
unpenalized calibration regressions converged in 8--16 iterations. V2b ran no
protected stage and changed no score, bin, recipe, window, taxonomy, or outcome.

## Primary OOT Diagnostics

All models score the same 376,890 primary-OOT candidates; 365,339 have resolved
snapshot outcomes and 11,551 remain unresolved. The resolved default rate is
15.7380%.

| Learner | AUC | Gini | KS | Average precision | Brier | ECE-10 | Cal. slope | Five-group coverage bound over 8 windows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Active CatBoost | .64085 | .28170 | .20629 | .23708 | .13075 | .04832 | .79647 | [.83853, .88217] |
| Numeric logistic | .64208 | .28416 | .20981 | .24358 | .12967 | .03226 | .54322 | [.84569, .89565] |
| Monotonic CatBoost | .65224 | .30449 | .22011 | .24752 | .12946 | .04270 | .83668 | [.84405, .88599] |
| Platform-signal WOE scorecard | .63302 | .26605 | .18832 | .22553 | .13036 | .03710 | .91816 | [.84420, .89432] |
| Borrower-only WOE scorecard | .61271 | .22542 | .15794 | .21672 | .13106 | .03289 | .70802 | [.84685, .89697] |

Every learner has all eight canonical-window upper coverage bounds below the
nominal .90 target. The strongest upper endpoint is .89697 for the
borrower-only scorecard; it still excludes .90 even if every unresolved OOT
outcome were covered. The active V4 result therefore survives constrained
boosting, conventional WOE/IV binning, and removal of LendingClub's grade and
pricing signals.

All five learners underpredict the later resolved default prevalence on
average. Calibration-in-the-large ranges from -3.01 to -4.83 percentage points,
and every OOT calibration slope is below one. Model transport degrades even
when discrimination remains nontrivial.

## Domain Controls

The monotonic CatBoost control has an OOT AUC 0.01140 higher and Brier 0.00130
lower than the active CatBoost. This is a predeclared descriptive contrast, not
authorization to select or promote a new primary model after OOT inspection.
Its value is that the coverage failure is not repaired by imposing defensible
credit-risk directions.

The platform WOE scorecard exceeds the borrower-only scorecard by 0.02031 OOT
AUC and improves Brier by 0.00070. LendingClub's grade and price signals retain
predictive information, but the borrower-only model still exhibits the same
direction of temporal coverage failure. The result is therefore not an artifact
of simply recycling the platform's underwriting grade.

## IV, WOE, And Stability

All 45 OptBinning problems report `OPTIMAL`. In the platform scorecard, the
largest fitting-block IV values are 0.33757 for the price-grade interaction,
0.31933 for subgrade, 0.29954 for grade, and 0.27843 for interest rate. In the
borrower-only scorecard, FICO has IV 0.21357, recent inquiries 0.17086, purpose
0.08888, utilization 0.07390, and delinquency recency 0.04929.

These signals are not temporally stationary. Primary-OOT feature PSI reaches
0.96280 for the price-grade interaction, 0.60813 for verification status,
0.55226 for DTI, and 0.39044 for recent inquiries. Score PSI from development
to primary OOT is 0.14887 for the platform scorecard and 0.07233 for the
borrower-only scorecard. The active and monotonic CatBoost score PSI values are
0.13976 and 0.09371, respectively.

`recent_chargeoff` is constant in PD development and probability calibration.
It cannot contribute a learned split in this design and should be documented as
an inert inherited feature rather than advertised as useful information.

## Paper Consequence

The new evidence strengthens the paper's model-class robustness and data-
contract credibility. It does not change the paper into a scorecard-comparison
study and does not identify a best learner. The main text should report one
compact five-model table and the all-eight-windows conclusion. Detailed IV,
bins, PSI, per-role metrics, taxonomies, and window geometry belong in the
supplement.

No learner from this audit enters portfolio optimization. The active portfolio
evidence remains the frozen V4 CatBoost design, so this extension cannot create
a policy-superiority, causal, deployment, or selected-model claim.

Machine-readable artifacts are in the DVC-tracked V1b and V2b directories under
`data/processed/experiments/ijds_audit/` and
`models/experiments/ijds_audit/`.
