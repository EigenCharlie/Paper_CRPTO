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

Pick a plan up only when:

- A new run-tag is being prepared, OR
- The plan's acceptance criteria can be met without disturbing the frozen
  champion artefacts.
