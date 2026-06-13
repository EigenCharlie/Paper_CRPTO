# `docs/refactor/`

Refactor plans, drift reports and execution memory for code paths that touch
the frozen paper pipeline.

> **Start here for what's next:**
> [`NEXT_WORK_PLAN_2026-06.md`](NEXT_WORK_PLAN_2026-06.md) — the consolidated
> backlog after R0–R5 (PRs #52–#66) and the 2026-06-13 Codex execution memory.
> Lanes A/B are closed as code/DVC metadata changes; A2 phase 4 retired the
> feature-config pickle under the approved run-tag window; C4 remains
> prohibited until freeze/submission, and D is the explicit NO-DO list to
> avoid churn.

Each plan documents:

1. Why the change is desirable.
2. Why it was deferred or gated.
3. Acceptance criteria for execution.
4. Patch shape / file layout where useful.

| Plan | Touches the champion? | Current status |
| --- | --- | --- |
| [`CONFORMAL_REFACTOR_PLAN.md`](CONFORMAL_REFACTOR_PLAN.md) | Yes (calibrator pickle) | Full public split executed 2026-06-13; `src.models.conformal` is now a package facade with strict-typed submodules. |
| [`MAPIE_MIGRATION_PLAN.md`](MAPIE_MIGRATION_PLAN.md) | Yes (intervals parquet) | Runtime is already MAPIE 1.x and the drift report is green; protected reruns still require explicit approval. |
| [`FEATURE_CONFIG_PARQUET_PLAN.md`](FEATURE_CONFIG_PARQUET_PLAN.md) | Yes (downstream stages) | YAML/Parquet migration executed 2026-06-13; `feature_config.pkl` retired from the live DVC DAG and manifest. |

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
