# AGENTS.md — Contexto para Codex en Paper_CRPTO

## Quién soy y qué es este proyecto

Soy Carlos Vergara, científico de datos terminando un paper académico de tesis. **CRPTO** (Conformal Robust Predict-Then-Optimize) aplica **conformal prediction** + **optimización robusta de carteras** al dominio de **credit risk** usando datos de Lending Club. Este repositorio es standalone: GitHub, DVC y MLflow apuntan a recursos propios de CRPTO. La historia de extracción está en `docs/PROJECT_HISTORY.md`; el repositorio no debe re-correr el **pipeline de búsqueda** del champion sin permiso explícito.

**Prefiero código simple y funcional. Sin sobre-ingeniería, sin abstracciones prematuras, sin refactors gratuitos.**

## Contexto académico (lectura obligatoria)

Antes de cualquier cambio estructural, lee en este orden:

1. [`docs/ACADEMIC_CONTEXT.md`](docs/ACADEMIC_CONTEXT.md) — naturaleza single-author / dataset estático / no producción y consecuencias operacionales.
2. [`docs/SCOPE_AND_GOVERNANCE.md`](docs/SCOPE_AND_GOVERNANCE.md) — qué entra en CRPTO, lista explícita de stages prohibidos en `main`, refactor lanes con precondiciones, release checklist.
3. [`CONTRIBUTING.md`](CONTRIBUTING.md) — qué se puede cambiar libremente vs. qué requiere plan de revalidación.
4. [`EXTRACTION_MANIFEST.md`](EXTRACTION_MANIFEST.md) — qué es exactamente lo "congelado" y cómo los tests de regresión lo enforzan.

Lo crítico de `ACADEMIC_CONTEXT.md`:

- **Single-author.** Yo soy el único que toca este repo. No hay PR reviews, no hay branch protection necesaria, no hay reviewers que aprueben. Las reglas de operación existen para disciplinar agentes, no para satisfacer un proceso corporativo.
- **Dataset estático.** Lending Club cerró originación retail en 2020. No vamos a recibir datos nuevos. Sin streaming, sin concept drift por cohortes nuevas. Si re-entrenamos, es sobre el mismo histórico.
- **No va a producción.** Output: paper + journal + libro Quarto + MRM dossier. Sin servicio live, sin SLAs, sin on-call.
- **GitHub Actions minimalista.** `book-publish.yml` (Pages) y `lint.yml` corren en push; `tests-full.yml` queda manual para hitos de journal o revalidación con DVC. `test.yml`, `dbt.yml`, `book-build.yml` se retiraron porque el pre-push hook ya valida lo equivalente en local.

## Re-corrida del champion: matiz importante

El "champion congelado" se refiere al **pipeline de búsqueda** que produjo las decisiones del paper:

- ❌ **Prohibido sin permiso explícito**: `crpto.portfolio.bound_exact_eval` (es la búsqueda de 276k políticas — el resultado rank-1 es la contribución del paper).
- ❌ **Prohibido sin permiso explícito**: cualquier HPO Optuna que re-busque hiperparámetros.
- ✅ **Permitido para validación** (drift check requerido): `crpto.pd.champion`, `crpto.conformal.intervals`, `crpto.conformal.validation`, `crpto.portfolio.optimization`. Estos usan hiperparámetros/policies ya elegidos y congelados en `configs/`. Tolerancias documentadas en `ACADEMIC_CONTEXT.md`.
- ✅ **Libre re-corrida**: `crpto.paper.*` y `crpto.book.render`.

## Champion congelado — NO RE-CORRER

| Campo | Valor |
| --- | --- |
| Run tag | `paper-thesis-final-economic-2026-04-06` |
| Policy | `bound_aware_276k_economic_champion` |
| Retorno robusto | `$170,464.54` |
| V(α=0.01) | `0.03645` |
| Γ_CP(α=0.01) | `0.18591` |
| Exact pass | `True` |
| Región robusta | `45/45` |

Artefactos congelados cuyos hashes están en `EXTRACTION_MANIFEST.json` y **no se tocan** sin permiso:

- `models/pd_canonical.cbm`
- `models/pd_canonical_calibrator.pkl`
- `models/final_project_promotion.json`
- `models/conformal_policy_status.json`
- `data/processed/conformal_intervals_mondrian.parquet`
- `data/processed/portfolio_bound_aware/rank1_alpha01_bound_aware_276k_full_2026-04-05-1734/`
- `EXTRACTION_MANIFEST.json`

Stages DVC que regeneran estos artefactos (`crpto.pd.champion`, `crpto.conformal.intervals`, `crpto.conformal.validation`, `crpto.portfolio.optimization`, `crpto.portfolio.bound_exact_eval`) **no se ejecutan** sin permiso. Validar con `crpto-validate-champion` antes de cualquier merge.

## Stack técnico (resumen)

- **Python** 3.11 con `uv` (no pip, no poetry). `uv.exe` típicamente en `C:\Users\carlos\anaconda3\Scripts\uv.exe`.
- **ML**: CatBoost 1.2.x (PD), MAPIE 1.4 (conformal), Optuna 4 (HPO), fairlearn 0.13, scikit-learn 1.8, Venn-Abers 1.5.
- **Optimización**: Pyomo 6.10 + HiGHS 1.14 (LP/MILP), OR-Tools 9.10, PyEPO 1.1 (SPO+, opcional).
- **Data**: pandas 2.3, numpy 2.4, pyarrow 23, duckdb 1.5, pandera 0.31.
- **Pipeline**: DVC 3.67 (con remote S3), dbt-duckdb 1.10, MLflow 3.12, DagsHub 0.7.
- **Docs**: Quarto 1.9+ (libro de 24 capítulos en español, HTML + PDF).
- **Tooling**: ruff 0.15, pytest 9, pre-commit 4, jupytext 1.19.

Lista completa: `pyproject.toml`. Versiones efectivas: `uv.lock`.

## Plataforma y paths

- **OS**: Windows 11 Pro. Shell por defecto: PowerShell. No usar shells no Windows como flujo operativo del proyecto.
- **Venv**: `.venv/Scripts/python.exe`; todo debe pasar por `uv run` o por el Python de ese entorno.
- **Task runner**: `justfile` (cross-platform). Existió un `Makefile` que se retiró por bug Linux-only.
- **Quarto CLI**: debe estar en PATH. `quarto --version` ≥ 1.9.

## Comandos clave

```powershell
# Setup
just setup                  # uv sync --extra dev --extra search --extra spo
just setup-base             # sin pyepo/torch

# Render del libro
just book                   # uv run -- quarto render book --to html
just book-pdf               # uv run -- quarto render book --to pdf
just book-preview           # quarto preview book (live reload)

# Tests y validación
just smoke                  # pytest tests/test_crpto_final_sync.py tests/test_quarto_book_guardrails.py
just test                   # pytest completo
just lint                   # ruff check + format check
just type-check             # mypy src scripts
just validate-champion      # verifica hashes vs EXTRACTION_MANIFEST.json

# Paper outputs (re-genera artefactos pero NO toca el champion)
just tables                 # python scripts/export_crpto_tables.py
just figures                # python scripts/generate_crpto_figures.py --paper crpto
just paper-export           # tables + figures + book

# DVC / DBT
just dvc-status             # dvc status (sin re-correr)
just dvc-dag                # dvc dag --md
just dbt-test               # dbt parse + dbt test
```

## Variables de entorno (.env)

Copiar `.env.example` a `.env` y rellenar con tokens reales. Variables clave:

- `DAGSHUB_OWNER`, `DAGSHUB_USER`, `DAGSHUB_REPO=Paper_CRPTO`, `DAGSHUB_TOKEN` o `DAGSHUB_USER_TOKEN` — standalone CRPTO.
- `MLFLOW_TRACKING_URI`, `MLFLOW_TRACKING_USERNAME`, `MLFLOW_TRACKING_PASSWORD` — DagsHub MLflow.
- `AWS_ENDPOINT_URL`/`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` o `GDRIVE_FOLDER_ID` — DVC remote opcional.
- Variables manuales de entorno Python/Quarto — no setearlas en el flujo normal; `uv run` usa `.venv/Scripts` y resuelve Python para Quarto.

El archivo `.env` está en `.gitignore`. Nunca commitear tokens.

## Convenciones de código

- **Type hints obligatorios** en `src/` y `scripts/`. Verificados con `mypy` (laxo, gradual).
- **`from __future__ import annotations`** al tope de cada módulo nuevo.
- **Docstrings** en funciones públicas (estilo Google o NumPy, consistente con módulo).
- **Logging con `loguru`** — NO `print`, NO `logging` estándar salvo en librerías que ya lo usan.
- **Configs en YAML** bajo `configs/`, validados con Pandera donde aplique.
- **Paths absolutos via `pathlib.Path`**, no strings con `/` o `\\`.
- **Pandera schemas** para contratos de DataFrames en boundaries.
- **Ruff** corre en pre-commit con reglas: `E,F,W,I,UP,B,SIM,C4,ANN,RET,RUF,PERF,FURB` (gradual).

## Estructura del proyecto

```
.
├── book/                    # Libro Quarto (24 capítulos ES, HTML+PDF)
│   ├── _quarto.yml          # config raíz
│   ├── _brand.yml           # paleta + tipografías CRPTO
│   ├── styles.scss          # CSS custom
│   ├── chapters/            # 24 .qmd
│   ├── includes/            # snippets reutilizables
│   ├── assets/figures/      # PNG/PDF (editorial, notebooks, publication)
│   ├── _helpers/            # paquete Python con load_artifacts, plot_helpers
│   ├── references.bib       # 70 entradas
│   └── apa.csl              # estilo APA7
├── src/                     # paquete Python `crpto`
│   ├── data/                # ingesta + cleaning
│   ├── features/            # FE + Pandera contracts
│   ├── models/              # PD + conformal + calibración
│   ├── evaluation/          # métricas + fairness + backtesting
│   ├── optimization/        # Pyomo/HiGHS + robust + SPO
│   └── utils/               # I/O, MLflow, helpers
├── scripts/                 # 40+ entry points del pipeline
├── tests/                   # 26 pytest (slow / integration markers)
├── configs/                 # YAML config (modelos, conformal, optim, fairness)
├── dbt_project/             # 6 modelos (3 staging + 3 marts) sobre crpto.duckdb
├── data/
│   ├── raw/                 # Lending Club CSV (1.7 GB) — NO commit
│   └── processed/           # parquets + DuckDB — DVC tracked
├── models/                  # champion + calibrator + status JSONs
├── reports/
│   ├── crpto/tables/        # 18 CSVs del paper
│   ├── crpto/figures/       # 8 PNGs/PDFs
│   └── mrm/                 # Model Risk Management cards (skops)
├── docs/research/           # dossier académico
├── paper/                   # manuscrito principal
├── notebooks/               # exploraciones (Jupyter)
├── dvc.yaml / dvc.lock      # pipeline de 13 stages
├── pyproject.toml           # dependencias y tooling
├── uv.lock                  # lockfile reproducible
├── justfile                 # task runner cross-platform
└── EXTRACTION_MANIFEST.json # hashes de artefactos congelados
```

## Reglas de operación

1. **Champion congelado es ley.** Si una tarea sugiere re-correr stages que afecten al champion, parar y preguntar.
2. **No modificar `EXTRACTION_MANIFEST.json` ni artefactos listados** sin permiso.
3. **No subir secretos** (`.env`, tokens, credenciales DagsHub/AWS).
4. **No re-formatear el libro completo** en una sola pasada — preserva freeze cache y diffs limpios.
5. **Render del libro tras cambios a `_quarto.yml`** o capítulos, con QA visual.
6. **Antes de commit**: `just lint && just smoke` deben pasar (pre-commit hook lo enforza).
7. **No bypassar hooks** (`--no-verify`) sin permiso.
8. **Windows-first**: cualquier script o comando nuevo debe correr en Windows PowerShell sin depender de shells Unix.
9. **`uv run`** para invocar herramientas Python (`pytest`, `quarto`, `dbt`, `dvc`, `mlflow`, `optuna`).
10. **Repo público**: `https://github.com/EigenCharlie/Paper_CRPTO`. No subir secretos ni artefactos pesados; usar DVC remote para datos/modelos.
11. **Branch de trabajo**: para código/refactors usa rama y PR. Hotfixes de docs/CI en `main` solo si el usuario lo pide explícitamente.

## Qué stages son seguros re-correr

| Stage DVC | ¿Seguro? | Notas |
| --- | --- | --- |
| `crpto.data.dataset` | ⚠️ Lento (1.7 GB) | Determinista; no rompe champion pero re-corre todo downstream. |
| `crpto.data.features` | ⚠️ | Igual. |
| `crpto.pd.champion` | ❌ NO | Rompe `pd_canonical.cbm`. |
| `crpto.conformal.intervals` | ❌ NO | Rompe intervalos congelados. |
| `crpto.conformal.validation` | ❌ NO | Rompe `conformal_policy_status.json`. |
| `crpto.portfolio.optimization` | ❌ NO | Rompe `portfolio_allocations.parquet`. |
| `crpto.portfolio.bound_exact_eval` | ❌ NO | Rompe `portfolio_bound_aware_bound_eval.parquet`. |
| `crpto.paper.export_tables` | ✅ Sí | Determinista; regenera CSVs. |
| `crpto.paper.evidence` | ✅ Sí | Determinista; regenera `crpto_evidence_status.json`. |
| `crpto.paper.journal_package` | ✅ Sí | Determinista. |
| `crpto.paper.figures` | ✅ Sí | Determinista. |
| `crpto.paper.spo_stability` | ✅ Sí | Determinista. |
| `crpto.book.render` | ✅ Sí | Render Quarto; output a `book/_book/`. |

## Scope operativo

El documento rector es `docs/SCOPE_AND_GOVERNANCE.md`. En corto:

- Seguro: docs, Quarto no-execute, CI, tests utilitarios, tablas/figuras/evidence/journal package.
- Revisar antes: cambios dbt/DVC/dependencias que afecten contratos de datos.
- No seguro en `main`: PD champion, intervalos conformal, validación conformal, optimización portfolio, exact eval, MAPIE/conformal/feature-config migrations sin drift report.

## Sub-agentes y MCP útiles

- `Explore` (built-in) para búsquedas de código y archivos.
- `Plan` (built-in) para diseñar cambios estructurales.
- **Context7 MCP** — docs actualizadas de pandas/sklearn/MAPIE/Quarto/dbt.
- **Chrome/Playwright MCP** — QA visual del libro renderizado.
- **DuckDB MCP** — queries directas a `data/processed/crpto.duckdb`.
- **GitHub MCP** — repo `EigenCharlie/Paper_CRPTO`.

## Skills custom del proyecto (`.codex/skills/`)

- `/crpto-render` — render del libro + QA visual con Playwright.
- `/crpto-stage` — `dvc repro` de un stage aislado, con dry-run.
- `/crpto-smoke` — smoke tests + dbt parse + dbt test.
- `/crpto-paper-export` — pipeline completo de salida journal.
- `/crpto-validate-champion` — verifica hashes vs `EXTRACTION_MANIFEST.json`.
- `/crpto-mrm-card` — actualiza model cards en `reports/mrm/`.

## Plan vigente

Las fases bootstrap ya fueron publicadas. Los cambios estructurales que quedan
viven como planes explícitos en `docs/refactor/` y no se ejecutan sin validar
drift contra el champion congelado.

## Cómo me gusta trabajar

- Respuestas concisas. Sin resúmenes redundantes al final.
- Tool calls en paralelo cuando son independientes.
- Plan-first para cambios no triviales (3+ archivos).
- Comentarios solo cuando el WHY no es obvio.
- Sin emojis en archivos salvo que los pida.
- En español para el libro/paper/docs; inglés para código/docstrings/identifiers/CI.
