# `docs/refactor/`

Refactors that are planned but **not yet executed** in the main branch.

Each plan documents:

1. Why the change is desirable.
2. Why it was deferred (almost always: it touches the frozen champion).
3. Acceptance criteria for execution.
4. Patch shape / file layout where useful.

| Plan | Touches the champion? | Linked to |
| --- | --- | --- |
| [`CONFORMAL_REFACTOR_PLAN.md`](CONFORMAL_REFACTOR_PLAN.md) | Yes (calibrator pickle) | Plan §C13 |
| [`MAPIE_MIGRATION_PLAN.md`](MAPIE_MIGRATION_PLAN.md) | Yes (intervals parquet) | Plan §B9 |
| [`FEATURE_CONFIG_PARQUET_PLAN.md`](FEATURE_CONFIG_PARQUET_PLAN.md) | Yes (downstream stages) | Plan §C14 |

Smaller deferred items without a dedicated plan file:

- **DAG completeness** (2026-06-09): `data/processed/{train,test,calibration}.parquet`
  (produced manually by `src/data/prepare_dataset.py`) and
  `data/processed/test_predictions.parquet` (exported by
  `scripts/train_pd_model.py`) are standalone `.dvc` artifacts, not stage
  outputs. Promoting them to stage outs requires removing the `.dvc`
  files and re-keying `crpto.pd.champion` in `dvc.lock` — champion-lock
  approval required. Until then the data flow is documented in comments
  inside `dvc.yaml`.
- **params.yaml unification** (2026-06-09): `params.yaml` is a documentary
  mirror with one known stale value (`pd.catboost.learning_rate: 0.03` vs
  the canonical `0.0573…` in `configs/crpto_pd_model.yaml` that the frozen
  champion actually consumed). Correcting it re-keys the protected
  `crpto.pd.champion` params block in `dvc.lock`, so it waits for the same
  champion-lock approval. Contract enforced by
  `tests/test_configs/test_params_config_sync.py`.

Pick a plan up only when:

- A new run-tag is being prepared, OR
- The plan's acceptance criteria can be met without disturbing the frozen
  champion artefacts.
