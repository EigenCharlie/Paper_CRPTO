# `docs/refactor/`

Refactor plans, drift reports and execution memory for code paths that touch
the frozen paper pipeline.

> The consolidated 2026-06 backlog was executed and archived:
> [`archive/NEXT_WORK_PLAN_2026-06.md`](archive/NEXT_WORK_PLAN_2026-06.md).
> The 2026-07-05 audit lanes (F1–F5) are closed; see
> [`docs/research/crpto_full_audit_2026-07-05.md`](../research/crpto_full_audit_2026-07-05.md)
> for the execution record and the post-submission backlog.

Each plan documents:

1. Why the change is desirable.
2. Why it was deferred or gated.
3. Acceptance criteria for execution.
4. Patch shape / file layout where useful.

| Plan | Touches the champion? | Current status |
| --- | --- | --- |
| [`CONFORMAL_REFACTOR_PLAN.md`](CONFORMAL_REFACTOR_PLAN.md) | Yes (calibrator pickle) | Full public split executed 2026-06-13; `src.models.conformal` is now a package facade with strict-typed submodules. |
| [`MAPIE_MIGRATION_PLAN.md`](MAPIE_MIGRATION_PLAN.md) | Yes (intervals parquet) | Runtime is already MAPIE 1.x and the drift report is green; protected reruns still require explicit approval. |
| [`archive/FEATURE_CONFIG_PARQUET_PLAN.md`](archive/FEATURE_CONFIG_PARQUET_PLAN.md) | Yes (downstream stages) | Executed 2026-06-13 and archived; `feature_config.pkl` retired from the live DVC DAG and manifest. |
| [`ijds_tooling_refactor_lab_2026-07-08.md`](ijds_tooling_refactor_lab_2026-07-08.md) | No (tooling/refactor only) | Active and full `ty` advisory scopes are clean; `pyrefly` is experimental; `pdoc`/`prek` are optional local helpers before IJDS submission. |

Executed lanes now in `main`:

- **R0 dead-code cleanup**: removed dead modules and consolidated policy
  matching helpers while preserving frozen artifact hashes.
- **R3 type-check cleanup**: `src/` and live scripts now pass `just type-check`
  with the gradual mypy profile.
- **R4/R5 tests and operations**: added contract tests and named operational
  gates for drift/bounds workflows.
- **R1 entrypoint extraction**: `scripts/train_pd_model.py`,
  `scripts/generate_conformal_intervals.py` and
  `scripts/optimize_portfolio_tradeoff.py` now have focused helpers for
  config/replay setup, feature/input preparation, conformal tuning
  selection, trade-off grid/input preparation and PD calibration selection.
  These were code-only refactors; tracked DVC dependency hashes were re-keyed
  without re-running protected stages.
- **2026-06-13 A/B closure**: conformal module split, YAML-first
  `feature_config` reader, explicit DVC split stage, `test_predictions` as
  `crpto.pd.champion` out, and executable `params.yaml` sync checker. No
  protected DVC stage was reproduced.
- **2026-06-13 A2 phase 4**: `crpto.data.features` now writes
  `feature_config.yml` and `feature_config.parquet`, no longer writes
  `feature_config.pkl`, and `EXTRACTION_MANIFEST.json` tracks the YAML/Parquet
  contract. The downstream champion/conformal stages were re-keyed with
  `dvc commit -f`; `just drift-gate` remained bit-exact.

Pick a plan up only when:

- A new run-tag is being prepared, or
- The plan's acceptance criteria can be met without disturbing the frozen
  champion artifacts.
