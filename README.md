# CRPTO — Conformal Robust Predict-Then-Optimize

Pipeline de investigación y libro Quarto que acompañan el paper **CRPTO**, una metodología que integra *conformal prediction* con *optimización robusta de carteras* aplicada a riesgo de crédito (datos de Lending Club, 2007–2020).

> CRPTO opera como repositorio standalone: GitHub, DVC y MLflow apuntan a recursos propios del paper. La historia de extracción y aprendizajes queda documentada en [`docs/PROJECT_HISTORY.md`](docs/PROJECT_HISTORY.md).

## Claim IJDS activo

| Campo | Valor |
| --- | --- |
| Run tag | `champion-reopen-2026-06-19__pool93__ijds-calibration-selected-endpoint28-v7` |
| Conformal | replay exacto al `90%` (`alpha=0.10`, used `0.095`) |
| Política | `q=(p+u)/2`, `tau=0.17`; PD puntual en el objetivo y `q` en el guardrail |
| Selector | grilla `3x3` en noviembre; cap determinista `B_u<=0.28`; misma política en auditoría de diciembre |
| Retorno realizado | **$179,327.59** |
| Default / miscoverage ponderados | `0.039375 / 0.036875` |
| `Gamma_CP / Gamma_residual` | `0.176102 / 0.088051` |
| Endpoint / contabilidad observada / umbral condicional | `0.258051 / 0.294926 / 0.574279` |
| Baseline A40 | `$196,369.14`; costo de retorno `8.678%`; reducción de default `7.9025` pp |
| Auditoría pre-OOT | diciembre: default `0.145650`, miscoverage `0.124925`; estabilidad no implica cobertura seleccionada |

Hashes SHA256 de los artefactos críticos están en [`EXTRACTION_MANIFEST.json`](EXTRACTION_MANIFEST.json). Verifica con `just validate-champion` o el skill `/crpto-validate-champion`.
El rebaseline y la frontera pool93 anterior se conservan como procedencia
congelada, no como claims activos del manuscrito IJDS.

## Requisitos del sistema

| Herramienta | Versión mínima | Notas |
| --- | --- | --- |
| Python | 3.11 (≤3.12) | Declarado en `.python-version` y `pyproject.toml`. |
| [uv](https://docs.astral.sh/uv/) | 0.4+ | Gestor de dependencias. Reemplaza pip/poetry. |
| [just](https://github.com/casey/just) | 1.28+ | Task runner cross-platform. Reemplaza `make`. Windows: `winget install Casey.Just`. |
| [Quarto CLI](https://quarto.org/docs/get-started/) | 1.9+ | Para renderizar el libro. CI usa 1.9.35. |
| LaTeX (LuaLaTeX) | TeX Live 2024+ | Solo si renderizas el PDF. Opcional para HTML. |
| DuckDB CLI | 1.3+ | Opcional, queries directas a `data/processed/crpto.duckdb`. |
| Git | 2.40+ | Para hooks pre-commit. |

En Windows, `uv`, `just` y `quarto` deben estar en `PATH`. El venv oficial del
proyecto vive en `.venv/Scripts/`; usa PowerShell como shell normal de trabajo.

## Setup rápido

```powershell
# Una sola vez
just setup              # uv sync --extra dev --extra search --extra spo
# O setup ligero (sin pyepo/torch)
just setup-base

# Copia el archivo de entorno y rellena con tus tokens reales
cp .env.example .env
# Edita .env (DagsHub/MLflow/DVC standalone de CRPTO)

# Verifica que todo está sano
just smoke              # tests críticos rápidos
```

## Comandos principales

```powershell
# Libro Quarto
just book               # HTML
just book-pdf           # no-op: PDF completo diferido hasta tesis curada
just book-preview       # live reload
just book-clean         # borra _book/, _freeze/, .quarto/

# Pipeline de paper (no toca el champion)
just paper-export       # tablas + figuras + evidence + journal + libro
just ijds-evidence      # A35--A40 y gobernanza de la política IJDS activa
just tables             # solo CSVs
just figures            # solo PNGs/PDFs

# Calidad
just lint               # ruff check + format check
just fmt                # ruff fix + format
just type-check         # mypy src scripts
just type-advisory      # ty sobre ruta activa IJDS, no bloqueante
just type-advisory-full # ty sobre src/scripts completos; bloquea el cierre IJDS
just api-docs-core      # pdoc local para modulos core, salida ignorada
just hooks-check        # valida hooks con pre-commit y prek
just smoke              # tests críticos rápidos
just test               # suite completa
just submission-check   # cierre IJDS: claims, lint, type, suite completa, champion y PDF oficial

# DVC
just dvc-status         # drift detection
just dvc-dag            # imprime el DAG en markdown

# dbt
just dbt-test           # parse + tests
just dbt-build          # marts materializadas

# Listado completo
just help
```

## Alcance y reglas de operación

El repositorio es público y está dedicado solo a CRPTO. El alcance operativo,
qué se puede regenerar, qué no debe tocarse en `main`, cómo manejar secretos y
qué refactors requieren revalidación están documentados en
[`docs/SCOPE_AND_GOVERNANCE.md`](docs/SCOPE_AND_GOVERNANCE.md).

Regla corta: documentación, CI, tablas, figuras y journal package son seguros;
reentrenar PD, recalcular intervalos conformal o reoptimizar el champion no lo
es sin una rama de revalidación y drift report.

## Estrategia de publicación

La decisión editorial activa es escribir primero para **INFORMS Journal on Data
Science** y mantener **European Journal of Operational Research** como pivote
principal si el manuscrito termina leyendo más como OR aplicada que como data
science reproducible. La decisión vive en
[`configs/crpto_publication_targets.yaml`](configs/crpto_publication_targets.yaml)
y está explicada en
[`docs/research/crpto_publication_strategy_2026-05-12.md`](docs/research/crpto_publication_strategy_2026-05-12.md).

Los borradores de extracción están en [`paper/`](paper/):

- `paper/CRPTO_ijds.qmd`: cuerpo anónimo IJDS.
- `paper/supplement_ijds.qmd`: online supplement con A3--A18, reproducibilidad,
  MRM y fairness.
- `paper/CRPTO.qmd`: entrada genérica.

Comandos rápidos:

```powershell
just paper-ijds
just paper-ijds-supplement
just paper-submission
```

## Estructura

```
.
├── CLAUDE.md                # Contexto para Claude Code
├── .claude/                 # Configuración Claude Code + skills CRPTO
│   ├── settings.json        # Permisos pre-aprobados (compartido)
│   └── skills/              # 6 skills custom (/crpto-render, /crpto-smoke, ...)
├── .codex/                  # Skill local CRPTO para Codex
├── .github/workflows/       # CI/CD (lint, book-publish, tests-full manual)
├── .pre-commit-config.yaml  # ruff + nbstripout + dvc-status + smoke
├── pyproject.toml           # Deps y tooling (ruff, pytest, mypy)
├── uv.lock                  # Lockfile reproducible
├── justfile                 # Task runner cross-platform
├── dvc.yaml / dvc.lock      # Pipeline de 13 stages
├── EXTRACTION_MANIFEST.json # Hashes SHA256 de artefactos congelados
├── book/                    # Libro Quarto (24 capítulos en español)
│   ├── _quarto.yml
│   ├── _brand.yml           # Paleta + tipografías (Fase 3)
│   ├── styles.scss          # CSS custom con dark mode + print media
│   ├── chapters/            # 24 .qmd (manuscrito + dossier)
│   ├── includes/            # snippets reutilizables
│   ├── assets/figures/      # editorial/, notebooks/, publication/
│   ├── _helpers/            # paquete Python con load_artifacts, plot_helpers
│   ├── references.bib       # 70 entradas
│   └── apa.csl              # estilo APA 7
├── crpto/                   # paquete público mínimo (`import crpto`)
├── src/                     # módulos fuente históricos (data, features, models, optimization, evaluation, utils)
├── scripts/                 # entry points; ver scripts/README.md para rutas IJDS vs históricas
├── tests/                   # 26 archivos pytest (markers slow / integration)
├── configs/                 # YAML (pd_model, conformal, optimization, fairness, mrm)
├── dbt_project/             # 3 staging + 3 marts sobre crpto.duckdb
├── data/
│   ├── raw/                 # Lending Club CSV (1.7 GB) — DVC tracked
│   └── processed/           # parquets + DuckDB
├── models/                  # champion + calibrator + status JSONs
├── reports/
│   ├── crpto/tables/        # 18 CSVs del paper
│   ├── crpto/figures/       # 8 PNGs/PDFs
│   └── mrm/                 # Model risk cards (skops)
├── docs/research/           # dossier académico
├── paper/                   # manuscrito principal + versión IJDS + supplement
└── notebooks/               # exploraciones Jupyter
```

## Qué stages son seguros re-correr

| Stage DVC | Seguro | Notas |
| --- | --- | --- |
| `crpto.data.dataset` | ⚠️ Lento | 1.7 GB; regenera todo downstream. |
| `crpto.data.features` | ⚠️ | Regenera train_fe/test_fe/calibration_fe. |
| `crpto.pd.champion` | ❌ | Rompe `pd_canonical.cbm`. |
| `crpto.conformal.intervals` | ❌ | Rompe intervalos congelados. |
| `crpto.conformal.validation` | ❌ | Rompe `conformal_policy_status.json`. |
| `crpto.portfolio.optimization` | ❌ | Rompe `portfolio_allocations.parquet`. |
| `crpto.portfolio.bound_exact_eval` | ❌ | Rompe `portfolio_bound_aware_bound_eval.parquet`. |
| `crpto.paper.export_tables` | ✅ | Determinista; regenera CSVs. |
| `crpto.paper.evidence` | ✅ | Determinista. |
| `crpto.paper.journal_package` | ✅ | Determinista. |
| `crpto.paper.figures` | ✅ | Determinista. |
| `crpto.paper.spo_stability` | ✅ | Determinista. |
| `crpto.book.render` | ✅ | Render Quarto. |

## Troubleshooting

**`quarto: command not found`** — instala Quarto CLI desde https://quarto.org/docs/get-started/ y reabre PowerShell.

**`uv: command not found`** — `winget install --id=astral-sh.uv` en Windows, o `pip install uv`.

**Render del libro falla con `ModuleNotFoundError`** — los chunks Python requieren el venv activo. `uv run -- quarto render book` resuelve esto.

**El entorno Python parece incorrecto** — borra variables locales que cambien el
entorno de `uv` o Quarto, recrea con `uv venv && uv sync --extra dev --extra
search`, y trabaja desde PowerShell en `C:\Users\carlos\Documents\Paper_CRPTO`.

**`dvc status` muestra muchos cambios** — probablemente el lockfile cambió. Ejecuta `just dvc-status` para ver detalle. Si los stages del champion están afectados, NO repro: documenta y consulta antes.

**Pre-commit bloquea un commit** — corre `just fmt && just smoke` para arreglar lint/format y verificar tests. Si el hook `dvc-status` falla, hay drift inesperado.

**Render PDF falla** — los PDFs activos son los borradores IJDS
(`just paper-submission-pdf`) y, más adelante, un PDF APA de tesis curado. El
PDF completo del libro no se mantiene como artefacto rutinario; ver
[`docs/THESIS_PDF_SCOPE.md`](docs/THESIS_PDF_SCOPE.md).

## Herramientas interactivas para reviewers

Comandos opcionales útiles para inspeccionar el champion sin tocar el pipeline:

```powershell
just duckdb              # REPL DuckDB sobre data/processed/crpto.duckdb
just datasette           # UI web sobre el warehouse (requiere datasette + datasette-duckdb)
just dbt-docs            # UI dbt en http://localhost:8088
just optuna-dashboard    # Optuna Dashboard sobre el journal de HPO
just pipeline-state      # Snapshot JSON de todos los status del pipeline
```

Ninguno modifica artefactos congelados — solo leen `data/processed/` y `models/`.

## Documentación adicional

- [`CLAUDE.md`](CLAUDE.md) — Contexto operativo para Claude Code (champion, comandos, convenciones).
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — Cómo reproducir las salidas y qué requiere plan de revalidación.
- [`CHANGELOG.md`](CHANGELOG.md) — Historial de cambios.
- [`docs/ACADEMIC_CONTEXT.md`](docs/ACADEMIC_CONTEXT.md) — Single-author, dataset estático, sin producción.
- [`docs/SCOPE_AND_GOVERNANCE.md`](docs/SCOPE_AND_GOVERNANCE.md) — Alcance CRPTO, límites del repo público y reglas de refactor.
- [`docs/refactor/`](docs/refactor/) — Planes de refactor diferido (MAPIE, conformal split, feature_config Parquet).
- [`docs/research/`](docs/research/) — Dossier académico (conformal prediction readme, audit, integrations).
- [`paper/README.md`](paper/README.md) — Workspace de manuscrito, target IJDS y
  comandos de render.
- [`docs/security/SECRETS_AND_REMOTES.md`](docs/security/SECRETS_AND_REMOTES.md) — Variables de entorno, secretos y remotes DVC/MLflow para Windows.
- [`EXTRACTION_MANIFEST.json`](EXTRACTION_MANIFEST.json) + [`EXTRACTION_MANIFEST.md`](EXTRACTION_MANIFEST.md) — Hashes y narrativa de la extracción.

## Citar este trabajo

Ver [`CITATION.cff`](CITATION.cff). Resumen:

> Vergara Rojas, C. A. (2026). *CRPTO: predict-then-optimize con conformal prediction para riesgo de crédito* [Master's thesis]. https://github.com/EigenCharlie/Paper_CRPTO

## Licencia

- Código fuente: [MIT](LICENSE).
- Texto del libro/paper, figuras y tablas: [CC BY 4.0](LICENSE-CONTENT).
