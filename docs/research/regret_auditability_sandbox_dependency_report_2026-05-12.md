# CRPTO Regret-Auditability Sandbox Dependency Report

Date: 2026-05-12

Branch: `codex/regret-auditability-sandbox`

Command executed:

```powershell
uv lock --upgrade-package catboost --upgrade-package mapie --upgrade-package optuna --upgrade-package optuna-integration --upgrade-package pyomo --upgrade-package highspy --upgrade-package venn-abers --upgrade-package scikit-learn
```

Result: `uv lock` resolved successfully and did not change `uv.lock`; all targeted packages were already at the current PyPI versions available to the project on 2026-05-12.

## Version Check

| Package | Before | After | PyPI latest checked |
| --- | ---: | ---: | ---: |
| `catboost` | 1.2.10 | 1.2.10 | 1.2.10 |
| `mapie` | 1.4.0 | 1.4.0 | 1.4.0 |
| `optuna` | 4.8.0 | 4.8.0 | 4.8.0 |
| `optuna-integration` | 4.8.0 | 4.8.0 | 4.8.0 |
| `pyomo` | 6.10.0 | 6.10.0 | 6.10.0 |
| `highspy` | 1.14.0 | 1.14.0 | 1.14.0 |
| `venn-abers` | 1.5.3 | 1.5.3 | 1.5.3 |
| `scikit-learn` | 1.8.0 | 1.8.0 | 1.8.0 |

## Feature Notes For This Sandbox

- CatBoost: keep `task_type=CPU`, explicit `thread_count`, monotone constraints, and `allow_writing_files=false`. Optional uncertainty features such as Langevin/posterior sampling are CPU-oriented but are intentionally not activated because the sandbox scope is still monotonic CatBoost plus Venn-Abers plus conformal robust optimization.
- MAPIE: v1 uses the newer split workflow around `conformalize` and `confidence_level`; MAPIE's v1 notes state that `MondrianCP` is temporarily unavailable, so the current manual group-wise Mondrian conformal implementation remains the right fit for CRPTO.
- Optuna: the current code already uses `TPESampler(multivariate=True, group=True, constant_liar=True)` plus constrained sampling support. For this sandbox, RDB storage remains the default because the existing trainer already supports SQLite heartbeat and stale-trial recovery; JournalStorage is now also accepted through `journal:`, `journal+file:`, or `journalfile:` storage URLs for distributed/resumable experiments.
- Pyomo and HiGHS/highspy: current LP/MILP path remains appropriate. Pyomo APPSI/HiGHS is worth benchmarking only if repeated model resolves become the bottleneck in exact reranking.
- Venn-Abers: latest package remains 1.5.3 and still matches the chosen calibration lane.
- scikit-learn: 1.8.0 is current in this environment and is compatible with MAPIE 1.4.0 and the existing calibration/metric utilities.

## Sources Checked

- CatBoost PyPI: https://pypi.org/project/catboost/
- CatBoost parameters: https://catboost.ai/docs/en/references/training-parameters/common
- MAPIE PyPI: https://pypi.org/project/MAPIE/
- MAPIE v1 notes: https://mapie.readthedocs.io/en/v1.4.0/v1_release_notes.html
- Optuna PyPI: https://pypi.org/project/optuna/
- Optuna samplers: https://optuna.readthedocs.io/en/v4.8.0/reference/samplers/index.html
- Optuna JournalStorage: https://optuna.readthedocs.io/en/stable/tutorial/20_recipes/011_journal_storage.html
- Pyomo PyPI: https://pypi.org/project/pyomo/
- Pyomo APPSI: https://pyomo.readthedocs.io/en/stable/reference/topical/appsi/appsi.html
- highspy PyPI: https://pypi.org/project/highspy/
- Venn-Abers PyPI: https://pypi.org/project/venn-abers/
- scikit-learn PyPI: https://pypi.org/project/scikit-learn/
