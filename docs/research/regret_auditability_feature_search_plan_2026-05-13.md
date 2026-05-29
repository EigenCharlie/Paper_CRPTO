# CRPTO Regret-Auditability Feature Search Plan

Date: 2026-05-13
Branch: `codex/regret-auditability-sandbox`

## Inputs Reviewed

- `LCDataDictionary.xlsx`: Lending Club dictionary sheet `LoanStats`, 153 variable descriptions.
- `eda_summary_2.xlsx`: exploratory workbook with shape, dtypes, missingness, numerical/date/categorical summaries.
- `data/processed/feature_config.pkl`: current CRPTO feature contract used by the materialized train/calibration/test parquets.

## Feature Findings

The processed CRPTO dataset already contains a richer feature space than the frozen champion CatBoost lane uses by default. The existing feature config exposes:

- `CATBOOST_FEATURES`: 44 champion-like CatBoost features.
- `WOE_FEATURES`: 13 train-only Weight-of-Evidence transforms.
- `HIGH_COVERAGE_BUREAU_FEATURES`: 29 bureau balance, utilization, account-count, and delinquency fields with strong coverage.
- `MEDIUM_COVERAGE_CHALLENGER_FEATURES`: 10 inquiry/installment/revolver velocity and recency fields.
- `MISSINGNESS_INDICATORS`: 10 missingness flags for medium-coverage challenger variables.
- `CHALLENGER_FEATURE_POOL_V2`: 93 total materialized challenger features.

The IV ranking in `feature_config.pkl` supports widening the sandbox search without touching frozen artifacts:

| Feature | IV |
|---|---:|
| `sub_grade` | 0.488 |
| `grade` | 0.453 |
| `int_rate` | 0.425 |
| `term` | 0.183 |
| `fico_score` | 0.109 |
| `installment_burden` | 0.085 |
| `dti` | 0.062 |
| `verification_status` | 0.048 |
| `loan_amnt` | 0.033 |
| `annual_inc` | 0.026 |

## Sandbox Feature Profiles

The branch now trains PD lanes against shadow feature-config pickles under the external artifact root. No DVC feature stage is re-run and no champion feature config is overwritten.

| Profile | Purpose |
|---|---|
| `core_stable` | Champion-like CatBoost features with the stable-core gate enabled. |
| `core_wide` | Champion-like CatBoost features without the stable-core gate. |
| `core_woe` | Champion-like features plus WOE transforms. |
| `bureau_high` | Core features plus high-coverage bureau utilization/account-history fields. |
| `full_challenger` | Full materialized challenger pool. |
| `full_challenger_woe` | Full challenger pool plus WOE transforms. |

## Monotonic Policies

The original three policies remain, and three business-sensible monotonic policies were added for the sandbox. Constraints are filtered per feature profile, so a policy never constrains a missing column.

| Policy | Business intent |
|---|---|
| `canonical_4` | Current affordability constraints. |
| `affordability_rate_5` | Adds `int_rate:+1`. |
| `credit_history_7` | Adds delinquency severity/recency. |
| `bureau_utilization_11` | Adds utilization, BC utilization, high-utilization share, FICO, and credit age. |
| `bureau_behavior_15` | Adds severe delinquency, public record, bankruptcy, 90+ DPD, never-delinquent share, FICO, and credit age. |
| `inquiry_velocity_12` | Adds recent inquiries and account-opening velocity. |

## Nested PD Handoff

PD is now a real funnel:

1. `pd-smoke`: run every feature-profile x monotonic-policy lane with 12 trials.
2. `pd-broad`: rank smoke lanes by OOT AUC, then Brier/ECE; run only the top 8 lanes with 1000 trials each. The lane config is initialized from the lane's previous best params.
3. `pd-refine`: rank broad lanes by the same criteria; run only the top 4 lanes with 500 local-refine trials each, enqueuing the broad best params as the base trial.
4. The best refined PD model/calibrator is copied under `artifact_root/pd/best/models/` for the conformal phase.

This preserves the user-facing method family:

```text
CatBoost monotonic + Optuna + Venn-Abers + Mondrian conformal + robust portfolio optimization
```

SPO+ and hybrids remain out of scope.
