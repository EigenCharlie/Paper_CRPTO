# `docs/refactor/`

Refactor plans, drift reports and execution memory for code paths that touch
the frozen paper pipeline.

> **Start here for what's next:**
> [`NEXT_WORK_PLAN_2026-06.md`](NEXT_WORK_PLAN_2026-06.md) — the consolidated,
> prioritized backlog after R0–R5 (PRs #52–#66). Lanes A (safe structural
> refactor, now unblocked), B (DAG governance, needs approval), C (paper
> editorial windows) and D (explicit NO-DO list to avoid churn).

Each plan documents:

1. Why the change is desirable.
2. Why it was deferred or gated.
3. Acceptance criteria for execution.
4. Patch shape / file layout where useful.

| Plan | Touches the champion? | Current status |
| --- | --- | --- |
| [`CONFORMAL_REFACTOR_PLAN.md`](CONFORMAL_REFACTOR_PLAN.md) | Yes (calibrator pickle) | Partially executed for pure diagnostics and script-level extraction; class/module split remains deferred. |
| [`MAPIE_MIGRATION_PLAN.md`](MAPIE_MIGRATION_PLAN.md) | Yes (intervals parquet) | Runtime is already MAPIE 1.x and the drift report is green; protected reruns still require explicit approval. |
| [`FEATURE_CONFIG_PARQUET_PLAN.md`](FEATURE_CONFIG_PARQUET_PLAN.md) | Yes (downstream stages) | YAML dual-write/read path exists; full Parquet/dataclass replacement remains deferred. |

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

Smaller deferred items without a dedicated plan file:

- **DAG completeness** (2026-06-09): `data/processed/{train,test,calibration}.parquet`
  (produced manually by `src/data/prepare_dataset.py`) and
  `data/processed/test_predictions.parquet` (exported by
  `scripts/train_pd_model.py`) are standalone `.dvc` artifacts, not stage
  outputs. Promoting them to stage outs requires removing the `.dvc`
  files and re-keying `crpto.pd.champion` in `dvc.lock`; champion-lock
  approval required. Until then the data flow is documented in comments
  inside `dvc.yaml`.
- **params.yaml unification** (2026-06-09; mirror fixed 2026-06-10): the
  stale `pd.catboost.learning_rate: 0.03` mirror was corrected to the
  canonical `0.0573...` during the april-lineage unification (the champion
  lock was being re-keyed anyway). The structural unification of
  `params.yaml` into `configs/` remains deferred. Contract enforced by
  `tests/test_configs/test_params_config_sync.py`.

Pick a plan up only when:

- A new run-tag is being prepared, or
- The plan's acceptance criteria can be met without disturbing the frozen
  champion artifacts.
