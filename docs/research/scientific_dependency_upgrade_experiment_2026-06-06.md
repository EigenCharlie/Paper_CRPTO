# Scientific dependency upgrade experiment - 2026-06-06

## Scope

This is an isolated scientific revalidation on branch
`codex/experiment-scientific-upgrades`. The goal is not to silently replace the
frozen IJDS champion. The goal is to learn what changes when the scientific
stack is upgraded, fix standalone Windows/DVC contracts that were exposed by the
rerun, and decide whether the branch is a merge candidate, a rebaseline
candidate, or only a learning branch.

This report documents the third route adopted after the first replay:

1. Keep the dependency experiment alive.
2. Separate genuine paper-facing gates from diagnostic p-values.
3. Make CRPTO standalone and repo-relative, with no WSL or parent-project paths.
4. Fix DVC contracts that made regenerated artifacts implicit or side-effectful.
5. Regenerate paper/book outputs from the improved graph before making a merge
   decision.

## Effective experimental stack

| Package | Version |
| --- | ---: |
| `numpy` | `2.4.6` |
| `pandas` | `2.3.3` |
| `scikit-learn` | `1.9.0` |
| `scipy` | `1.17.1` |
| `catboost` | `1.2.10` |
| `mapie` | `1.4.0` |
| `fairlearn` | `0.14.0` |
| `pandera` | `0.31.1` |
| `ortools` | `9.11.4210` |
| `pyomo` | `6.10.1` |
| `pyarrow` | `24.0.0` |
| `duckdb` | `1.5.3` |
| `dbt-core` | `1.10.8` |
| `protobuf` | `5.26.1` |
| `mlflow` | `3.13.0` |
| `starlette` | `1.2.1` |
| `cvxpy` | `1.9.1` |

Additional safe upgrades applied during this pass:

- `scipy 1.15.3 -> 1.17.1`
- `fairlearn 0.13.0 -> 0.14.0`
- `cvxpy 1.8.2 -> 1.9.1`

The `ortools 9.11.4210` resolver side effect keeps `dbt-core` at `1.10.8` and
`protobuf` at `5.26.1`. This is not a scientific degradation by itself: DBT is
only used for local DuckDB model checks, not for the IJDS estimator, conformal
policy or portfolio optimizer. It is still a maintenance smell for a direct
merge because it couples the optimization stack to data-build tooling.

## Replay results

### PD replay

`crpto.pd.champion` completed under the experimental stack.

| Metric | Frozen `main` | Experiment | Delta | Direction |
| --- | ---: | ---: | ---: | --- |
| AUC ROC | `0.712438241694` | `0.712677784555` | `+0.000239542861` | Better |
| Brier score | `0.154630517829` | `0.154590736760` | `-0.000039781069` | Better |
| Log loss | `0.477061133261` | `0.476942645225` | `-0.000118488036` | Better |
| ECE, 10 bins | `0.006379675622` | `0.006152293607` | `-0.000227382015` | Better |
| ECE, 20 bins | `0.006694598684` | `0.007068428020` | `+0.000373829336` | Worse |
| D2 Brier | `0.098239224398` | `0.098471216168` | `+0.000231991770` | Better |

Interpretation: no material PD degradation. The effects are tiny and mostly
favorable, but this is not a new champion claim unless a new run tag is accepted.

### Conformal replay

`crpto.conformal.intervals` completed with the upgraded stack and
`crpto.conformal.validation` now reports separate gate and diagnostic fields.

| Metric | Frozen `main` | Experiment | Delta | Direction |
| --- | ---: | ---: | ---: | --- |
| 90% coverage | `0.929338423587` | `0.929024195558` | `-0.000314228028` | Slightly worse, still above target |
| 95% coverage | `0.962339590203` | `0.966283693732` | `+0.003944103529` | Better coverage |
| 90% average width | `0.764155715329` | `0.761184933186` | `-0.002970782143` | Better |
| 90% min-group coverage | `0.900350942002` | `0.900535648319` | `+0.000184706317` | Better |
| 90% Winkler | `1.193742537951` | `1.189698007553` | `-0.004044530398` | Better |
| 95% Winkler | `1.130559407415` | `1.112168938538` | `-0.018390468876` | Better |
| Backtest warning alerts | `0` | `1` | `+1` | Worse |
| MAPIE MWI 90 | `null` | `1.189698007553` | n/a | Now computed with MAPIE 1.4 API |

Current validation status:

| Field | Value |
| --- | ---: |
| `overall_pass` | `true` |
| `gate_overall_pass` | `true` |
| `gate_checks_passed` | `9/9` |
| `strict_overall_pass` | `false` |
| `diagnostic_statistical_pass` | `false` |
| `diagnostic_checks_passed` | `0/4` |
| Diagnostic failing checks | Kupiec and Christoffersen p-values at 90% and 95% |

Interpretation: `strict_overall_pass=false` is historical and diagnostic. The
bootstrap commit already had the same pattern: `overall_pass=true`,
`strict_overall_pass=false`, `9/13`, and the same four p-value failures. The
reason is not subcoverage; it is overcoverage with a very large OOT sample.
For IJDS, the material gate is coverage, width, group coverage, warning alerts,
Winkler score, independence/materiality and downstream portfolio validity.
Kupiec and Christoffersen p-values remain useful diagnostics, but they should
not be the promotion gate for this paper.

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

`crpto.portfolio.bound_exact_eval` now uses the frozen exact context through a
DVC stage and reuses a complete 180-row bound-eval cache when present.

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

Interpretation: the economic champion identity and robust return survived the
exact replay. The replay exact metrics differ from the frozen promotion JSON
values (`V=0.03645`, `Gamma_CP=0.18591`), so they should remain replay
diagnostics unless the branch is promoted into a formal rebaseline.

## Contract fixes implemented

| Area | Issue found | Fix |
| --- | --- | --- |
| DVC CLI contracts | Several stages had stale args (`--config`, missing `--run-tag`, exact helper with no `--context-path`). | Stage commands and script parsers were aligned. |
| Conformal backtest | Validation consumed monthly/alert backtest outputs that DVC did not produce. | Added `crpto.conformal.backtest` and made validation depend on its outputs. |
| Conformal outputs | `conformal.intervals` produced multiple consumed artifacts not declared in DVC. | Declared group metrics, tuning, floor, shrinkback, attribution and MAPIE result outputs. |
| Conformal gate | `strict_overall_pass` mixed material gates with diagnostic statistical p-values. | Added `gate_overall_pass`, `diagnostic_statistical_pass`, gate counts and diagnostic counts. |
| Exact eval side effects | Exact helper rewrote its input shortlist and wrote absolute paths after resolving context paths. | Split input `shortlist.parquet` from derived `shortlist_exact.parquet`; payload paths are repo-relative. |
| Exact eval runtime | DVC removed `bound_eval` before the helper could reuse it. | Marked `bound_eval` as persistent and added cache validation. |
| Tail audit runtime | A20 replay solved 45 policies even when a complete matching audit table existed. | Added complete-table reuse with source-metric validation. |
| WSL provenance | Historical JSONs had WSL/intermediate parent paths. | Normalized active JSON artifacts to repo-relative paths or explicit legacy placeholders. |
| Figure status | `paper_figures_status.json` wrote an absolute local `output_dir`. | Changed producer and artifact to `reports/crpto/figures`. |

## Paper/book impact

The book narrative now explains the conformal gate as:

- `overall_pass=true`
- `gate_overall_pass=true`
- `gate_checks_passed=9/9`
- `strict_overall_pass=false` only because p-value diagnostics are strict
  statistical checks, not the IJDS promotion criterion.

The paper-facing tables, evidence report, figures, journal package and tail
audit were regenerated from the improved DAG. `uv run dvc status` is clean after
the rerun.

## Path hygiene

The branch now passes a source/artifact scan for legacy Linux mount paths,
the former parent-project slug, WSL hostnames and distro labels.

The parent WSL project was not needed for recovery in this pass.

## Final checks

| Check | Result |
| --- | --- |
| `uv pip check` | Pass |
| Focused evaluation/optimization tests | Pass |
| `just smoke` | Pass |
| `uv run dvc status` | Pass |
| `crpto.portfolio.bound_exact_eval` | Pass, reused 180-row exact cache |
| `crpto.paper.export_tables` | Pass |
| `crpto.paper.evidence` | Pass |
| `crpto.paper.figures` | Pass |
| `crpto.paper.journal_package` | Pass |
| `crpto.paper.tail_satisficing_audit` | Pass, reused complete A20 table |
| `just validate-champion` | Expected fail: 22 frozen model/data/table artifacts drifted |

Additional focused checks:

- `uv run pytest tests/test_scripts/test_validate_conformal_policy.py`
- `uv run pytest tests/test_scripts/test_run_portfolio_bound_exact_eval.py`
- `uv run pytest tests/test_scripts/test_run_portfolio_bound_aware_search.py`
- `uv run ruff check` on modified pipeline scripts

## Current interpretation

The branch is stronger than a code-only cleanup and safer than a blind rebaseline.
It demonstrates that the upgraded stack can reproduce the economic story while
exposing and fixing real standalone/DVC problems.

Merge decision:

- As a learning branch, #37 is already valuable.
- As a direct merge, the blocker is not `strict_overall_pass`; it is whether we
  want to accept protected-artifact drift and the DBT/protobuf resolver side
  effect on `main`.
- As an IJDS revalidation candidate, the next clean step would be a formal drift
  report and a deliberate decision about whether to regenerate
  `EXTRACTION_MANIFEST.json` under a new schema/run note.
