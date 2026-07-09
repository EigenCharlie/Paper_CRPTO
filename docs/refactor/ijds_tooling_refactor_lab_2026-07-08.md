# IJDS tooling and refactor lab - 2026-07-08

## Decision

This branch keeps the CRPTO workflow intentionally narrow for IJDS. The daily
path should optimize for claim integrity, reproducible paper outputs and low
maintenance, not for adopting every new Python tool.

## Tooling decisions

| Tool | Decision | Rationale |
| --- | --- | --- |
| `uv` | Keep as canonical environment/package runner. | Already matches the repo, lockfile and Windows-first workflow. Official docs position it as a fast Python package/project manager: <https://docs.astral.sh/uv/>. |
| `ruff` | Keep as formatter/linter gate. | It already replaces separate formatter/import/lint tools with one fast gate: <https://docs.astral.sh/ruff/>. |
| `ty` | Use a pinned daily advisory and a blocking final full-scope gate. | `just type-advisory` keeps the active IJDS-safe surface visible without competing with `mypy`; `just type-advisory-full` is clean and now blocks `submission-check` on future diagnostics. Official docs: <https://docs.astral.sh/ty/>. |
| `pyrefly` | Do not gate before submission. Use only for targeted experiments. | `uvx pyrefly` works (`1.1.1`), but active-scope trial produced 56 diagnostics, mostly pandas/matplotlib inference noise. Pyrefly is stable and fast, but not yet lower-maintenance than `ty` for this repo: <https://pyrefly.org/>. |
| `pdoc` | Add optional local API-doc recipe only. | `just api-docs-core` builds ignored docs for core optimization/calibration/evaluation modules. Useful for technical inspection, not IJDS-critical. Docs: <https://pdoc.dev/>. |
| `prek` | Add compatibility validation, not a full migration. | `just hooks-check` validates the existing `.pre-commit-config.yaml` with both `pre-commit` and `prek`. `prek` is a fast drop-in alternative, but changing hook execution semantics before submission is unnecessary. Docs: <https://prek.j178.dev/>. |
| `commitizen` | Do not adopt before IJDS submission. | Commitizen helps teams enforce conventional commits/changelogs, but CRPTO is single-author and the paper/release checklist matters more than semantic-version automation. Docs: <https://commitizen-tools.github.io/commitizen/>. |

## Implemented process simplifications

- Added `scripts/run_ty_advisory.py` so pinned `ty==0.0.57` has two deterministic
  scopes: active IJDS path and full repository debt.
- Updated `just type-advisory` to use the active scope. Current result:
  `ty advisory clean` over 102 active files.
- Added `just type-advisory-full`; after the final cleanup pass it is also
  clean over 131 files. Optional TabPFN/SPO/cuOpt dependencies now load through
  explicit optional-import helpers, and retired generic search entrypoints fail
  with actionable messages instead of unresolved imports. The previously noisy
  pandas/PD/conformal typing issues in protected scripts were removed without
  changing drift.
- Updated `just submission-check` to enforce the full `ty` scope now that it is
  clean and cheap. `mypy` remains the stable contractual type gate; `ty` adds a
  second fast regression check without introducing Pyrefly's duplicate noise.
- Added `just api-docs-core`; generated output lives in ignored
  `reports/api-docs/`.
- Added `just hooks-check`; both `pre-commit validate-config` and
  `prek validate-config` pass.
- Added `just complexity-report` as an explicit `radon` report over `src/` and
  `scripts/`. It is intentionally a refactor radar, not a submission gate,
  because remaining long scripts include historical/protected search
  entrypoints that should not be rewritten before IJDS without a concrete
  claim-risk reduction.
- Split the policy arithmetic inside
  `src.optimization.portfolio_model.compute_effective_pd` into small helpers
  for clipped deltas, quantiles, blending, and tail selection. The public API
  and policy semantics are unchanged, but the main policy resolver no longer
  appears in the complexity report.
- Split `src.evaluation.model_shift.interpret_model_shift` into named
  structural-shift, predictive-degradation, shift-type, governance-posture and
  p-value-note helpers. This keeps the MRM/governance semantics auditable and
  removes the module from the C-or-higher complexity report.
- Split `src.models.conformal_tuning.shrink_group_multipliers` into a small
  immutable shrink context plus private helpers for factor normalization,
  interval application, metric calculation, constraint checks, candidate
  generation, tie-breaking and reporting. The public API and greedy policy are
  unchanged, but the conformal shrink step is now easier to audit against the
  paper's coverage/fairness claims.
- Extracted the shared continuous-portfolio LP algebra in
  `src.optimization.portfolio_model` so SciPy HiGHS and native highspy consume
  the same constraint matrix, bounds and objective coefficients. This removes
  duplicated budget/PD/purpose/slack construction.
- Rewired the native cuOpt adapter to consume that same shared LP component
  builder instead of reconstructing budget, concentration, PD-cap and slack
  rows locally. This keeps the optional GPU backend aligned with the canonical
  CPU formulation and removes another D-level complexity hotspot.
- Split `src.models.optuna_tuning.train_catboost_tuned_optuna` from a single
  F-level HPO orchestrator into explicit helpers for local/global search-space
  materialization, feature-prior normalization, constraints, incumbent metrics,
  objective evaluation, storage/study creation, trial enqueueing, trial
  selection and final fit/refit. The CatBoost/Optuna defaults and public return
  shape are preserved, while the HPO path is now much easier to inspect when
  defending the frozen model recipe.
- Split `scripts.build_papers_tesis_deep_audit.write_audit` into small Markdown
  section builders for inventory, paper-facing literature, extended thesis
  lanes, visual curation, bibliography control and closeout. This keeps the
  local literature audit regenerable without one large opaque memo writer.
- Split `scripts.generate_governance_status._build_explanation_drift_report`
  into helpers for recent-period selection, segment construction, SHAP ranking,
  feature PSI details and per-segment pass/fail rows. This clarifies the MRM
  explanation-drift logic without changing the governance artifact contract.
- Split the `scripts.generate_governance_status` orchestrator into explicit
  threshold/path dataclasses plus helpers for train/test loading, JSON sidecar
  reads, drift metrics, model-shift interpretation and status serialization.
  This keeps `governance_status.json`, `model_shift_status.json` and parquet
  paths unchanged while removing the remaining E-level main function.
- Split `scripts.run_comparison._gate_ab_no_regression` into helpers for A/B
  return extraction, current self-gate evaluation and baseline comparison
  warnings. The gate still passes only on the self no-regression rule, with the
  documented selective-ambiguity cross-scenario exception preserved.
- Split the remaining D-level comparison-report helpers in
  `scripts.run_comparison`: artifact/status metadata now has explicit source,
  observation, timestamp-skew and run-tag-coherence helpers, and comparison
  report writing now separates gate execution, gate field extraction, quality
  contract construction and JSON/Markdown emission. This makes the promotion
  evidence easier to inspect without changing the gate semantics.
- Split `scripts.generate_crpto_figures._crpto_fig8_alpha_pareto` into helpers
  for semantic column detection, variant styling, alpha sorting, tick labels and
  annotation offsets. This keeps the IJDS alpha-sweep figure logic auditable
  without changing the plotted data or the figure contract.
- Split `scripts.run_fairness_audit` so SHAP per-group interpretation,
  CatBoost SHAP preparation, Fairlearn sidecar bootstrap summaries, primary
  status construction and SHAP status writing are isolated helpers. This turns
  the fairness audit script from a mixed I/O/analysis block into a clearer
  pipeline while preserving thresholds, sidecar paths and JSON/parquet
  contracts.
- Split `scripts.validate_conformal_policy` into helpers for config/sensitivity
  loading, namespace application, alert fallback, valid interval extraction,
  Winkler/MAPIE cross-checks, compensated Winkler policy handling, material
  check construction and latest-month selection. The validation contract and
  output schema stay the same, but the conformal promotion gate is now much
  easier to audit against the IJDS coverage/width/group-coverage claims.
- Split `scripts.run_crpto_vs_spo_stability` into import-safe optional SPO
  loading plus helpers for period masks, deterministic per-period sampling,
  coverage aggregation, detail rows and summary JSON. The output contract stays
  the same, but tests can now import the module without PyEPO/Torch, and period
  sampling no longer depends on Python's randomized `hash()` seed.
- Split `scripts.select_economic_portfolio_policy` into explicit selector
  settings, decision inputs, candidate evaluation, hard-filter eligibility,
  A/B-like ranking, fallback construction and payload serialization helpers.
  This preserves the champion-policy/status JSON contracts while making the
  economic selector auditable as a sequence of declared gates instead of one
  long mixed orchestration block.
- Split `scripts.simulate_ab_test._resolve_robust_policy` into champion-policy
  selection, selected-policy normalization, robustness-summary validation,
  summary row choice and default fallback helpers. This makes the A/B audit
  policy precedence explicit: champion artifact first, summary second, fallback
  last, with `explicit_champion_only` still failing loudly when the artifact is
  absent.
- Split `scripts.benchmark_conformal_variants` into benchmark-data loading,
  normalized search-space construction, variant accumulation, global/Mondrian/
  cross-conformal appenders, calibration-size sensitivity rows, final frame
  assembly and artifact writing. The benchmark still writes the same parquet
  and JSON surfaces, but the conformal experiment is now inspectable as stages
  instead of one F-level orchestrator.
- Split `scripts.benchmark_pd_set_prediction` into set-benchmark data loading,
  settings normalization, per-variant prediction, calibration-size sensitivity,
  benchmark matrix assembly, slice summaries, promotion-gate calculation,
  status payload construction and artifact writing. The binary set-prediction
  sidecar remains a triage/abstention diagnostic, but its evidence path is now
  explicit and no longer an E-level `main`.
- Split the high-risk paths in `scripts.train_pd_model`: config defaults,
  CLI overrides, replay expectation checks, calibration backtests, Optuna seed
  replay, tuned-CatBoost/HPO orchestration, decision-threshold resolution,
  MAPIE statistical calibration tests, walk-forward diagnostics and SHAP export
  now live behind named helpers. This preserves the training contracts while
  making the PD replay and evidence path easier to audit. The script still has
  a long main orchestrator, but it is now C-level instead of D/F-level and no
  D-level helper remains.
- Split `scripts.generate_conformal_intervals` so feature resolution,
  contract-matrix alignment, tuning-grid normalization, 90% Mondrian tuning
  search, 90% coverage-floor/shrinkback evidence, optional global rebalance,
  95% alpha selection and final artifact-table/payload persistence are
  explicit helpers. The conformal interval generator's `main` is now B-level:
  it reads like the paper's certificate sequence instead of mixing tuning,
  coverage policy and artifact-writing branches.
- Split `scripts.search.run_pool93_ijds_local_refinement` so the IJDS finite
  policy-grid construction is organized by declared profile/family rather than
  one F-level function. The candidate generator is now covered by per-profile
  semantic-key fingerprints, including the terminal `37,068`-policy surface,
  so future edits cannot silently change the paper-facing grid denominators.
- Split the `scripts.search.run_pool93_ijds_local_refinement` entrypoint into
  parser, path, conformal-source, candidate, manifest, resume, pending-task,
  progress persistence, serial/parallel execution and final-output helpers.
  The candidate-grid fingerprints remain unchanged for every declared profile,
  including the terminal `37,068`-policy surface, and no exact refinement run
  was executed.
- Split `scripts.search.run_portfolio_bound_exact_eval` into explicit context
  paths, exact-evaluation plan, resume/cache handling, pending-task iteration,
  selection payload writing and final status helpers. This removes the D-level
  `main()` from the exact finite-grid evaluator without running the protected
  `crpto.portfolio.bound_exact_eval` search stage or changing artifact paths.
- Split `scripts.search.run_portfolio_bound_aware_search` so parser
  construction, typed grid/execution state, run paths, budget profiles,
  search-space payloads, selection context, frontier artifact writes,
  frontier-only completion, external exact delegation, in-process exact
  evaluation, success/failure cleanup and selection output writes are explicit
  helpers. The protected search stage was not executed; the refactor clarifies
  the finite-grid certificate plumbing and leaves no C-or-higher block in the
  file. The targeted policy-family grid is table-driven so segment-tail
  families are easier to audit.
- Added `src.optimization.certificate_semantics` as the code-level source of
  truth for the eight IJDS alpha levels. Pool93 refinement, the bound-aware CLI
  default and the regret-auditability portfolio command now consume the same
  tuple/CSV contract. A sync test checks the code constant against the
  paper-facing search profile and active claim registry.
- Split `scripts.search.run_regret_auditability_sandbox` so sandbox-local PD
  config snapshots are assembled by feature/profile, model params,
  Venn-Abers calibration, HPO/warm-start, validation, output paths, threshold
  disablement and sandbox metadata helpers. The resumable command scheduler now
  separates phase grouping, resume skips, launch, completion logging and
  PD-phase winner selection. Command planning is now split into PD incumbent,
  PD lane, conformal, portfolio and metrics builders; the former C(20)
  `build_phase_commands` no longer appears in the C-level report. The portfolio
  phase now defaults to the declared eight-level IJDS alpha grid instead of an
  older seven-level exploratory grid. No sandbox commands or protected stages
  were run.
- Split `scripts.search.run_conformal_reopen_search` so parser construction,
  resume-vs-fresh phase-1 materialization, OOT confirmation and optional phase-2
  promotion are explicit helpers with small dataclass handoffs. This removes the
  last live D-level search orchestrator without executing the reopen search or
  touching frozen conformal artifacts.
- Split the phase-2 calibrator tournament inside
  `scripts.search.run_conformal_reopen_search` into explicit helpers for method
  normalization, progress-state writes, baseline metric fitting, degradation
  gating, holdout candidate execution, candidate ranking and final OOT
  confirmation. The phase-2 search no longer appears in the C-or-higher report,
  and no reopen search was executed.
- Split `scripts.experiments.run_champion_claim_max_downstream._portfolio_command`
  into base-command, frontier-option, execution-option and cuOpt-option
  helpers. The downstream watcher remains an isolated experiment lane, but its
  portfolio search command is now inspectable and covered for proxy-vs-exact
  sampling, exact-python and cuOpt flags.
- Split the legacy Pyomo `solve_portfolio` wrapper into backend solving,
  result extraction and termination-status helpers. After this pass,
  `src.optimization.portfolio_model` no longer appears in the C-or-higher
  complexity report.

## Code refactor stance

The useful pre-submission refactor lane is not a broad rewrite. It is:

1. Keep `mypy` as the contractual gate.
2. Keep `ty` active scope clean so new IJDS-path issues stand out.
3. Convert pandas/Pyomo dynamic edges only where the change is local and tests
   can cover it.
4. Keep full-scope historical/protected diagnostics visible through
   `just type-advisory-full`, but do not install optional TabPFN/SPO/cuOpt
   stacks unless an isolated experiment needs them.
5. Stop live-code complexity cleanup at this point: `src` and active `scripts/`
   no longer have D-or-higher radon findings. The only remaining D-level report
   is in `scripts/archive/`, so further pre-submission refactors should happen
   only when they reduce a concrete claim-risk or maintenance burden.

## Current validation evidence

- Focused `ruff` and `mypy` checks passed for edited modules.
- Focused tests passed for conformal adapters, calibration pickle compatibility,
  TabPrep challengers, MLflow tracing, MRM report generation and the new
  `ty` wrapper.
- Focused policy/portfolio tests pass, including exact regression checks for
  segment-tail and segment-relative-tail effective-PD semantics.
- Focused model-shift tests pass, including structural-only, predictive-only,
  mixed and stable governance postures.
- Focused conformal-tuning tests pass, including new regression coverage for
  temporal-factor shrinkage and the initial-infeasible report path.
- Focused portfolio tests pass for sparse HiGHS vs Pyomo equivalence, native
  highspy vs sparse HiGHS equivalence, native fallback behavior and the PD
  slack/min-budget case.
- Focused cuOpt adapter tests pass with a fake cuOpt API, covering shared LP
  matrix handoff, solver settings, generated log files, allocation payloads,
  PD slack and non-feasible termination handling without requiring RAPIDS on
  Windows.
- Focused PD-model tests pass, including small real CatBoost/Optuna runs for
  tuned-vs-default predictions and local-refine materialization.
- Focused literature-audit memo tests pass for editorial sections, experiment
  rows, bibliography-status counts and the no-champion-change boundary.
- Focused governance tests pass for overall/grade explanation-drift rows,
  insufficient-support empty reports and the public governance-status summary,
  checks and artifact-path contract.
- Focused run-comparison tests pass for ordinary A/B no-regression and the
  selective-ambiguity cross-gate exception, plus artifact metadata coherence
  and the causal/CATE insights-only run-tag mismatch exception.
- Focused CRPTO figure tests pass for alpha-sweep column detection, variant
  labels/colors, alpha sorting, tick labels and annotation offsets.
- Focused fairness-audit tests pass for threshold resolution, auto-selected
  decision policy writing, SHAP categorical detection/fill behavior and
  per-group SHAP driver summaries.
- Focused conformal-policy validation tests pass for MAPIE current/legacy MWI
  signatures, valid interval extraction, compensated Winkler gates, material
  status JSON fields, official-baseline run-tag fallback, artifact namespaces
  and sensitivity overrides.
- Focused CRPTO-vs-SPO stability tests pass for artifact presence,
  deterministic per-period sampling seeds and summary/detail aggregation.
- Focused economic-selector tests pass for robust promotion, fallback,
  breadth-aware v2 selection, A/B-like v3 ranking and breadth hard filters.
- Focused A/B policy-resolution tests pass for guardrail champion priority,
  summary fallback when no champion artifact exists and explicit champion-only
  missing-artifact failure.
- Focused conformal-variant benchmark tests pass for namespaced shadow output
  paths and search-space normalization/deduplication.
- Focused PD set-prediction tests pass for namespaced shadow output paths,
  settings normalization/fallback coercion and the guardrail promotion gate.
- Focused PD training config tests pass for CLI/replay overrides, feature
  resolution, split loading/sampling and the new Optuna replay gate-tier
  ranking contract, plus walk-forward stage normalization and SHAP summary
  export.
- Focused conformal interval CLI tests pass for tuple parsers, tuning-grid
  normalization, tuning candidate counts, split materialization, global
  rebalance no-op behavior, 95% alpha tie-breaking, tuning-selection
  materialization, learned floor-policy application, temporal-segment
  eligibility and final artifact-table metadata preservation.
- Focused pool93 local-refinement tests pass for all declared candidate-grid
  profiles (`stage1`, `expanded`, `claim_expanded`, `claim_micro`,
  `claim_micro_ext`, `claim_bound_closure`, `claim_bound_floor_closure`,
  `claim_bound_terminal`) using stable semantic-key fingerprints and for the
  finite-grid claim-summary protocol. Additional helper tests cover manifest
  path coherence and pending candidate-alpha task construction after the
  entrypoint split. `mypy` is clean for
  `scripts/search/run_pool93_ijds_local_refinement.py`, and the former D-level
  `main()` no longer appears in the C-or-higher report.
- Focused exact-eval tests pass for completed-cache reuse, partial-cache
  resume filtering, full-universe seed deduplication, alpha-grid payload
  normalization and priority-context ordering. `mypy` is clean for
  `scripts/search/run_portfolio_bound_exact_eval.py`, and `radon` reports the
  exact-eval `main()` as A-level with no C-or-higher blocks.
- Focused bound-aware search tests pass for shortlist preservation, exact
  aggregation ranking, table-driven policy-grid order, budget-profile parsing,
  shared alpha-grid defaults, separated proxy/exact sampling, exact-work counts
  and selection-context path/search-space coherence. `mypy` is clean for
  `scripts/search/run_portfolio_bound_aware_search.py`, and `radon` reports no
  C-or-higher blocks in that file.
- Focused champion-reopen orchestration tests pass for paper-facing downstream
  candidate selection and the portfolio command builder, including separated
  proxy/exact sampling plus cuOpt option propagation. `mypy` is clean for
  `scripts/experiments/run_champion_claim_max_downstream.py`, and its former
  D-level `_portfolio_command` no longer appears in the C-or-higher report.
- Focused regret-auditability sandbox tests pass for protected-output rejection,
  sandbox lane materialization, PD snapshot writing, external output-dir
  command planning, declared alpha-grid propagation, phase grouping, resume
  skip behavior and validation-policy scaling. `mypy` is clean for
  `scripts/search/run_regret_auditability_sandbox.py`; its former D-level
  `write_pd_config_snapshot` and `_run_commands` plus the former C-level
  `build_phase_commands` no longer appear at those thresholds.
- Focused conformal-reopen tests pass for phase-2 design fallback, resume
  source-path preservation, OOT confirmation ranking, phase1-only phase-2 skip
  behavior, explicit calibrator metric-gate skips and final phase-2 candidate
  ranking/confirmation. `mypy` is clean for
  `scripts/search/run_conformal_reopen_search.py`, and `radon` reports no
  D-or-higher blocks in that file.
- `uvx radon cc src -s -n D` returns no findings after the conformal tuning,
  portfolio, cuOpt and Optuna refactors.
- `uvx radon cc scripts/run_comparison.py -s -n D` returns no findings after
  the comparison metadata/report split.
- `uvx radon cc scripts/generate_crpto_figures.py -s -n D` returns no findings
  after the alpha/Pareto figure refactor.
- `uvx radon cc scripts/run_fairness_audit.py -s -n D` returns no findings
  after the fairness SHAP/Fairlearn sidecar split.
- `uvx radon cc scripts/validate_conformal_policy.py -s -n D` returns no
  findings after the conformal validation split.
- `uvx radon cc scripts/generate_governance_status.py -s -n D` returns no
  findings after the governance status orchestration split.
- `uvx radon cc scripts/run_crpto_vs_spo_stability.py -s -n D` returns no
  findings after the optional-dependency and aggregation split.
- `uvx radon cc scripts/select_economic_portfolio_policy.py -s -n D` returns
  no findings after the selector orchestration split; `main` is now A-level.
- `uvx radon cc scripts/simulate_ab_test.py -s -n D` returns no findings after
  the robust-policy resolver split.
- `uvx radon cc scripts/benchmark_conformal_variants.py -s -n D` returns no
  findings after the benchmark orchestration split.
- `uvx radon cc scripts/benchmark_pd_set_prediction.py -s -n D` returns no
  findings after the set-prediction sidecar split.
- `uvx radon cc scripts/train_pd_model.py -s -n D` now returns no findings;
  `main` is C(19) and all helper functions are below D-level after the
  PD-training orchestration split.
- `uvx radon cc scripts/generate_conformal_intervals.py -s -a` now reports
  average complexity A after the conformal generator split; `main` dropped
  from 83 to B(9). The remaining C-level logic is localized in
  `_build_90_interval_evidence` and `_load_conformal_inputs`.
- `uvx radon cc scripts/search/run_pool93_ijds_local_refinement.py -s -n C`
  no longer reports `_generate_candidate_grid` or `main` as D-level; candidate
  generation, claim summarization and entrypoint flow are helperized and
  fingerprint-tested.
- `just complexity-report` now reports only
  `scripts/archive/search/monitor_regret_auditability.py::render` at D-level;
  the active `src/` and `scripts/` surfaces are clear of D-or-higher findings.
- `just type-advisory` passes clean.
- `just type-advisory-full` passes clean; the latest report is written to
  `reports/ci/ty-advisory-full.txt`.
- `just drift-gate` stayed bit-exact after touching PD/conformal scripts:
  max absolute diffs for predictions, intervals and score-band edges were
  `0.000e+00`.
- `just submission-check` passes with the full `ty` advisory, body/supplement
  Quarto renders, and the official IJDS LaTeX fallback build; the current
  official PDF has 28 pages, References begin on page 24, and the build is
  citation/reference clean.
- `just test` passes.

## Remaining caution

This branch touched `src/models/optuna_tuning.py`, conformal adapter code and
the conformal tuning shrink path in small interface/refactor-only ways. The
latest `just drift-gate` stayed bit-exact, but keep it in the promotion
checklist alongside the standard submission gates because these modules sit
close to the paper's certificate.

## Portfolio input and baseline semantics audit (2026-07-09)

- Added `src/optimization/input_alignment.py` as the single alignment contract
  for the canonical and trade-off portfolio entrypoints. It enforces one-to-one
  ID or `_row_number` matching, preserves interval-origin columns, rejects
  duplicate/missing keys, and makes positional sampling reproducible over the
  full universe.
- Replayed canonical alignments at 17, 5,000 and 276,869 rows. ID and
  `pd_high_90` fingerprints were bit-identical before and after the refactor in
  both entrypoints.
- Added `portfolio_model.solution_allocation_vector` as the validated contract
  for dense and sparse solver payloads. Migrated the primary optimizer,
  trade-off wrapper, economic selector, evidence audit, alpha--gamma validator,
  body-allocation audit and pool93 refinement. Their previous all-row indexing
  or local fallback copies were incompatible or redundant under the modern
  sparse solver payload.
- Corrected `robust=False` semantics: it now forces `point_estimate`, `gamma=0`
  and point PD in the optimization constraint. Previously an endpoint override
  had precedence, so the stored `nonrobust` baseline was still constrained by
  `pd_high`.
- The preliminary read-only comparison at `tau=0.175` was superseded by the
  matched A40 audit: same 276,869-candidate universe, `$1M` budget,
  `tau=0.1715`, concentration and LGD contracts, and solver settings. Point-PD
  earns `$196,369.14`; the selected CRPTO allocation earns `$184,832.48`, a
  cost of `$11,536.66` (`5.875%`) alongside an 8.305 pp reduction in realized
  weighted default and a 43.55 pp reduction in the exact loss threshold. The
  historical signed-price interpretation and preliminary unmatched comparison
  are retired from active paper surfaces; protected historical tables remain
  provenance.
- Focused tests cover source-column preservation, deterministic sampling,
  key-integrity failures, wrapper parity, effective nonrobust policy metadata,
  and dense/sparse allocation payloads.
