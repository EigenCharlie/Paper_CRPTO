# Scientific dependency upgrade experiment - 2026-06-06

## Scope

This is an isolated experiment on branch `codex/experiment-scientific-upgrades` in
`C:\Users\carlos\Documents\Paper_CRPTO_science_upgrade_experiment`.

The stable work on `main` already merged low- and medium-risk upgrades. This report covers the
explicitly risky scientific replay: upgrade the upstream scientific stack, rerun frozen stages, and
measure reproducibility/drift without changing `main`.

## Effective experimental stack

The experimental environment resolved to:

| Package | Version |
| --- | ---: |
| `numpy` | `2.4.6` |
| `pandas` | `2.3.3` |
| `scikit-learn` | `1.9.0` |
| `scipy` | `1.15.3` |
| `catboost` | `1.2.10` |
| `mapie` | `1.4.0` |
| `fairlearn` | `0.13.0` |
| `pandera` | `0.31.1` |
| `ortools` | `9.11.4210` |
| `pyomo` | `6.10.1` |
| `pyarrow` | `24.0.0` |
| `duckdb` | `1.5.3` |
| `dbt-core` | `1.10.8` |
| `protobuf` | `5.26.1` |
| `mlflow` | `3.13.0` |
| `starlette` | `1.2.1` |

Important resolver side effect: upgrading `ortools` to `9.11.4210` forced older DBT/protobuf
constraints (`dbt-core==1.10.8`, `protobuf==5.26.1`). That is acceptable for this isolated replay,
but it is not a clean stable-branch upgrade candidate.

## Contract issues found during replay

The experiment surfaced several pipeline contract mismatches that were hidden by the frozen artifacts:

| Area | Finding | Experimental action |
| --- | --- | --- |
| Feature materialization | DVC called `scripts/materialize_feature_artifacts.py --config`, but the script did not accept `--config`. | Added ignored compatibility arg. |
| PD champion | DVC did not pass the explicit official run tag, while metadata now requires one. | Added `--run-tag` to `scripts/train_pd_model.py` and to DVC. |
| PD config | `configs/crpto_pd_model.yaml` pointed to stale `configs/fairness_policy.yaml`. | Updated to `configs/crpto_fairness_policy.yaml`. |
| Conformal intervals | DVC called `scripts/generate_conformal_intervals.py --config`, but the script did not accept it; it also needed explicit run tag. | Added compatibility args and DVC run tag. |
| Conformal validation | DVC did not pass `--run-tag`. | Added the official run tag to the stage command. |
| Conformal backtest | `validate_conformal_policy.py` consumes backtest parquet files that are not produced by DVC's interval stage. | Ran `scripts/backtest_conformal_coverage.py` manually and marked this as graph debt. |
| Exact portfolio replay | DVC passed `--config`, but the helper requires `--context-path`. The context also contains historical WSL paths. | Pointed DVC to the frozen exact context and normalized historical repo paths in memory. |

## Results so far

### Baseline validations before replay

Before rerunning frozen stages, the experimental environment passed:

- `uv pip check`
- `just lint`
- `just smoke`
- `just dbt-test` after `uv run dbt deps`
- `just validate-champion`

### PD replay

`crpto.pd.champion` completed under the experimental stack.

| Metric | Experimental value |
| --- | ---: |
| AUC ROC | `0.7126777845551742` |
| Brier score | `0.1545907367602431` |

This stage rewrote frozen model artifacts in the experiment, so the manifest is expected to fail after
the replay. That is the point of the branch, not a candidate change for `main`.

### Conformal replay

`crpto.conformal.intervals` completed and selected:

- partition: `grade`
- probability source: `raw`
- `n_bins`: `10`
- tuned `alpha_used`: `0.08`
- score scale family: `bernoulli_sqrt`
- holdout coverage: `0.9148`
- holdout min-group coverage: `0.8976`
- holdout width: `0.7725`

Final interval metrics:

| Metric | Experimental value |
| --- | ---: |
| 90% coverage | `0.9290241955581882` |
| 90% average width | `0.7611849331856254` |
| 90% min-group coverage | `0.9005356483191725` |
| 95% coverage | `0.966283693732415` |
| 90% Winkler | `1.1896980075533712` |
| Backtest alerts | `1` |

`crpto.conformal.validation` completed with:

- `overall_pass=true`
- `strict_overall_pass=false`
- `checks_passed=9/13`
- `methodological_justification_pass=true`
- failing checks: Kupiec and Christoffersen p-values at 90% and 95%

Interpretation: the non-statistical policy gates still pass, and the failures are statistical
diagnostics caused by systematic over-coverage on a very large sample. This is scientifically useful
drift, but not a stable-branch merge candidate.

### Portfolio replay

`crpto.portfolio.optimization` completed:

| Metric | Experimental value |
| --- | ---: |
| Solver termination | `optimal` |
| Objective value | `$56,733.98` |
| Funded loans | `98/5000` |
| Allocated budget | `$1,000,000` |
| Scenario expected | `$10,411.83` |
| Scenario worst case | `$45,000.00` |

`crpto.portfolio.bound_exact_eval` completed after two attempts:

- attempt 1 completed all 180 bound checks but failed during aggregation because the input shortlist
  already contained stale `alpha01_*`/`alpha03_*` columns; pandas merged the new metrics with suffixes
  and the selector looked for unsuffixed names.
- attempt 2 completed after making aggregation idempotent and persisting `bound_eval` before
  selection.

Final exact replay:

| Metric | Experimental value |
| --- | ---: |
| Selection reason | `selected_best_alpha01_exact_pass` |
| Risk tolerance | `0.175` |
| Policy mode | `blended_uncertainty` |
| Gamma | `0.45` |
| Realized total return | `$170,464.54` |
| Alpha 0.01 exact pass | `true` |
| Alpha 0.01 weighted miscoverage V | `0.028875` |
| Alpha 0.01 Gamma_CP | `0.187987` |
| Exact bound rows | `180` |

The economic champion identity and robust return survived the exact replay, but some exact diagnostic
columns changed because the helper re-aggregated the shortlist. This is another reason not to merge
artifact changes from this branch into `main`.

### Paper and book replay

Downstream paper/book stages completed after hydrating auxiliary, non-DVC artifacts that the book
references implicitly:

- `data/processed/alpha_sweep_pareto_both.parquet`
- `data/processed/uncertainty_baselines_comparison.parquet`
- `data/processed/uncertainty_baselines_by_grade.parquet`
- `data/processed/cqr_mondrian_comparison.parquet`
- `data/processed/cqr_comparison.parquet`
- `data/processed/cqr_mondrian_group_coverage.parquet`
- 11 additional `data/processed/*.parquet` artifacts referenced by the book
- `reports/mrm/`

Figure generation completed with `14/14` figures after hydration. The Quarto HTML book rendered
successfully.

## Final checks

| Check | Result |
| --- | --- |
| `uv pip check` | Pass |
| `just lint` | Pass |
| `just smoke` | Pass |
| `just dbt-test` | Pass |
| `uv run dvc status` | Pass: data and pipelines are up to date |
| `just validate-champion` | Expected fail: 8 frozen artifacts drifted |

Frozen artifacts that drifted from `EXTRACTION_MANIFEST.json`:

- `models/pd_canonical.cbm`
- `models/pd_canonical_calibrator.pkl`
- `models/conformal_results_mondrian.pkl`
- `models/conformal_policy_status.json`
- `data/processed/feature_manifest_v2.json`
- `data/processed/feature_manifest_v2.parquet`
- `data/processed/test_predictions.parquet`
- `data/processed/portfolio_bound_aware/rank1_alpha01_bound_aware_276k_full_2026-04-05-1734/portfolio_bound_aware_shortlist.parquet`

## Current interpretation

The experiment supports four conclusions:

1. The stable dependency upgrade path should stop at the already merged low- and medium-risk sets.
2. Scientific-stack upgrades are not a routine dependency maintenance task for this paper because
   they mutate frozen model artifacts and alter conformal statistical diagnostics.
3. The replay exposed real reproducibility debt in CLI/DVC contracts. Those fixes are useful, but
   they should be promoted separately from any scientific artifact changes.
4. The exact economic champion is robust to the solver replay in this branch, but the PD/conformal
   upstream replay changes enough frozen artifacts that the branch should remain experimental.

## Pending

- Decide whether to extract a small, safe PR for contract-only fixes:
  - DVC/script CLI compatibility.
  - exact-helper path normalization for historical WSL provenance.
  - idempotent exact aggregation when the shortlist already contains exact columns.
  - explicit DVC modeling for book/paper auxiliary artifacts that are currently implicit.
- Do not merge regenerated scientific artifacts from this experimental branch into `main`.
