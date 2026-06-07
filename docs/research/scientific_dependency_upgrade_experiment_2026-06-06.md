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
but it is not a clean stable-branch upgrade candidate unless the DBT/protobuf constraint interaction
is resolved.

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

Metrics below compare `main` frozen predictions with the experimental replay predictions in
`data/processed/test_predictions.parquet`.

| Metric | `main` | Experiment | Delta | Direction |
| --- | ---: | ---: | ---: | --- |
| AUC ROC | `0.712438241694` | `0.712677784555` | `+0.000239542861` | Better |
| Brier score | `0.154630517829` | `0.154590736760` | `-0.000039781069` | Better |
| Log loss | `0.477061133261` | `0.476942645225` | `-0.000118488036` | Better |
| ECE, 10 bins | `0.006379675622` | `0.006152293607` | `-0.000227382015` | Better |
| ECE, 20 bins | `0.006694598684` | `0.007068428020` | `+0.000373829336` | Worse |
| D2 Brier | `0.098239224398` | `0.098471216168` | `+0.000231991770` | Better |

This stage rewrote frozen model artifacts in the experiment, so the manifest is expected to fail after
the replay. The direction is mostly favorable but the effect sizes are tiny; the scientific conclusion is
"no material PD degradation under the upgraded stack", not "new champion".

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

Final interval metrics against current `main`:

| Metric | `main` | Experiment | Delta | Direction |
| --- | ---: | ---: | ---: | --- |
| 90% coverage | `0.929338423587` | `0.929024195558` | `-0.000314228028` | Slightly worse, still above target |
| 95% coverage | `0.962339590203` | `0.966283693732` | `+0.003944103529` | Better coverage |
| 90% average width | `0.764155715329` | `0.761184933186` | `-0.002970782143` | Better |
| 90% min-group coverage | `0.900350942002` | `0.900535648319` | `+0.000184706317` | Better |
| 90% Winkler | `1.193742537951` | `1.189698007553` | `-0.004044530398` | Better |
| 95% Winkler | `1.130559407415` | `1.112168938538` | `-0.018390468876` | Better |
| Backtest warning alerts | `0` | `1` | `+1` | Worse |
| MAPIE MWI 90 | `null` | `1.189698007553` | n/a | Now computed with MAPIE 1.4 API |

`crpto.conformal.validation` completed with:

- `overall_pass=true`
- `strict_overall_pass=false`
- `checks_passed=9/13`
- `methodological_justification_pass=true`
- failing checks: Kupiec and Christoffersen p-values at 90% and 95%

Interpretation: this is the same strict/overall pattern already present in the standalone bootstrap
commit (`2026-05-10`, `70b5ea7`): `overall_pass=true`, `strict_overall_pass=false`, `9/13`, and the
same four statistical failures. The strict failures are diagnostic p-value checks, not the promotion
gate. The actual gate is `overall_pass`, supported by `methodological_justification_pass=true` because
all non-statistical checks pass, coverage deviations stay within the 3 pp materiality band, and
Christoffersen independence p-values pass.

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

The economic champion identity and robust return survived the exact replay. The frozen promotion JSON
still reports the official alpha-0.01 values (`V=0.03645`, `Gamma_CP=0.18591`), while the enriched
shortlist now carries replay exact metrics (`V=0.028875`, `Gamma_CP=0.187987`) after idempotent
re-aggregation. Treat those as replay diagnostics until their lineage is documented explicitly.

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

Additional focused checks after conformal-validator fixes:

- `uv run pytest tests/test_scripts/test_validate_conformal_policy.py`: Pass (`9 passed`)
- `uv run ruff check scripts/validate_conformal_policy.py tests/test_scripts/test_validate_conformal_policy.py`: Pass

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

1. `strict_overall_pass=false` is not a blocker by itself. It is the historical diagnostic state of the
   conformal policy, and #37 reproduces it with `overall_pass=true`.
2. The scientific-stack replay is promising: PD metrics are stable/slightly improved, conformal metrics
   remain inside policy, and the economic champion identity survives.
3. The merge risk is not the strict conformal flag; it is the protected-artifact hash drift, the
   OR-Tools/DBT/protobuf resolver side effect, and the exact-shortlist metric lineage.
4. The replay exposed real reproducibility debt in CLI/DVC contracts. Those fixes are useful and should
   be separated from any decision to accept regenerated scientific artifacts.

## Pending

- Decide whether to extract a small, safe PR for contract-only fixes:
  - DVC/script CLI compatibility.
  - exact-helper path normalization for historical WSL provenance.
  - idempotent exact aggregation when the shortlist already contains exact columns.
  - MAPIE 1.4-compatible conformal MWI cross-check.
  - conformal status wording that marks `diagnostic_informational` statistical tests as non-blocking
    when methodological justification passes.
  - explicit DVC modeling for book/paper auxiliary artifacts that are currently implicit.
- If #37 is considered for merge, decide first whether it is:
  - a code-only reproducibility PR that excludes regenerated frozen artifacts;
  - a formal revalidation PR that updates `EXTRACTION_MANIFEST.json` with a drift report;
  - or a learning-only branch that remains unmerged.
