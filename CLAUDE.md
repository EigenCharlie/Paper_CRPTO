# CLAUDE.md — Contexto para Claude Code en Paper_CRPTO

## Scientific status override - 2026-07-10

The active IJDS paper combines the clean, tagged maturity-safe bounded protocol
v2 with the separately tagged, explicitly post hoc comparator-stringency
audit. Its source of truth is `docs/research/active_claims_2026-07-10.md`. The
compact v7 claim is frozen historical provenance and remains NO-GO. Before
paper work, read the active registry, the locked comparator protocol, its
`ijds_comparator_stringency_results_2026-07-10.md` post-run audit,
`ijds_state_of_art_audit_2026-07-10.md`, and
`ijds_three_front_reconstruction_2026-07-10.md`, then use
`ijds_final_two_pass_audit_2026-07-10.md` for the final recovery disposition and
stop rule. Never overwrite either active run, the historical champion, or
manifest-protected artifacts.

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

## Re-corrida del champion: regla inequívoca

Ningún stage DVC que escriba una ruta protegida se ejecuta sin permiso explícito,
aunque consuma hiperparámetros ya congelados. Esto incluye
`crpto.pd.champion`, `crpto.conformal.intervals`,
`crpto.conformal.validation`, `crpto.portfolio.optimization` y
`crpto.portfolio.bound_exact_eval`. Tampoco se relanza HPO Optuna sobre el
champion. La validación ordinaria usa `just validate-champion`, `just
drift-gate` y replays con run tags y rutas experimentales nuevas; no usa `dvc
repro` sobre outputs canónicos. Los stages `crpto.paper.*` y el render
`crpto.book.render` son regenerables porque sólo consumen evidencia congelada.

Un permiso excepcional debe nombrar el stage, la rama, las rutas de salida y
el plan de drift. Nunca se interpreta una nota histórica de “re-runnable” como
autorización implícita.

## Champion congelado — NO RE-CORRER

El modelo PD, calibrador, intervalos y bundle pool93 del manifest permanecen
congelados como procedencia histórica. El body IJDS activo usa un experimento
nuevo, aislado y DVC-tracked; no regenera ni sobreescribe ningún artefacto
upstream protegido.

**Body claim activo maturity-safe v2 + comparator audit:**

| Campo | Valor |
| --- | --- |
| Run tag | `champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2` |
| Comparator run | `champion-reopen-2026-07-10__maturity-safe-v2-comparator-stringency-audit-v1` |
| Universo | `540,121` préstamos de 36 meses, membership independiente del status |
| Cronología | fit/selección termina 2012; 15 decisiones mensuales 2016-04--2017-06 |
| Conformal | intervalo binario Mondrian con target `90%` y rango finito exacto; no es CI de PD latente |
| Política | `q=0.75p+0.25u`, `tau=0.17`; payoff coherente `(1-p)r-p*LGD` |
| Cobertura candidata OOT | `[0.854923, 0.879692]` |
| Comparator point PD | `tau=0.068313`, matched al mean funded PD de 2012H2 |
| Diferencia de payoff vs matched point PD | `[-$506,587.03, -$295,967.17]` |
| Diferencia de default vs matched point PD | `[0.034431, 0.056287]` |
| Diferencia de miscoverage vs matched point PD | `[0.027093, 0.046283]` |
| Mecanismo | same numeric `tau` no iguala stringency; la ventaja de default se invierte con development matching |
| Evidencia | manifests `ijds_maturity_safe_evidence.json` e `ijds_comparator_stringency_evidence.json` |

El claim es una falsificación metodológica: el guardrail parecía reducir
default contra point PD con el mismo `tau=0.17`, pero ese cap point era no
vinculante. Contra el comparador alineado por riesgo de desarrollo, el
guardrail pierde payoff realizado y empeora default y miscoverage. La auditoría
de comparadores es post hoc, no causal, prospectiva ni confirmatoria; el censo
familiar es 7/9, no 9/9. La autoridad completa es
`docs/research/active_claims_2026-07-10.md`.

**Body claim histórico v7:** NO-GO y replay-only. Sus A35--A40, retorno
positivo, endpoint y sensibilidades no pueden reaparecer en superficies
editoriales activas.

**Cadena upstream congelada (histórica; su retorno es el return floor declarado del pool93):**

| Campo | Valor |
| --- | --- |
| Run tag | `ijds-rebaseline-2026-06-07` |
| Policy | `bound_aware_276k_economic_champion` |
| Retorno robusto | `$170,464.54` |
| V(α=0.01) | `0.028875` |
| Γ_CP(α=0.01) | `0.187987` |
| Exact pass | `True` |
| Región robusta | `45/45` |

Artefactos históricos congelados cuyos hashes están en
`EXTRACTION_MANIFEST.json` y **no se tocan** sin permiso:

- `models/pd_canonical.cbm`
- `models/pd_canonical_calibrator.pkl`
- `models/final_project_promotion.json`
- `models/conformal_policy_status.json`
- `data/processed/conformal_intervals_mondrian.parquet`
- `data/processed/portfolio_bound_aware/rank1_alpha01_bound_aware_276k_full_2026-04-05-1734/`
- `reports/crpto/tables/crpto_tableA35..A40_pool93_*.csv/.tex` (evidencia pool93)
- `models/experiments/champion_reopen/...__pool93__ijds-claim-bound-terminal/portfolio/pool93_ijds_claim_governance.json`
- `models/experiments/champion_reopen/...__pool93__ijds-certificate-semantics-v2/portfolio/pool93_ijds_consolidated_frontier.json`
- `models/experiments/champion_reopen/...__pool93__ijds-certificate-semantics-v2/portfolio/pool93_ijds_consolidated_governance.json`
- `models/experiments/champion_reopen/...__pool93__ijds-certificate-semantics-v2/portfolio/pool93_point_pd_baseline_audit.json`
- `EXTRACTION_MANIFEST.json`

La sincronía del claim maturity-safe v2 y del comparator audit con body,
supplement y TeX la vigilan `tests/test_ijds_active_claim_sync.py` y
`tests/test_ijds_comparator_evidence.py`.

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
just book-pdf               # no-op intencional: PDF completo diferido hasta tesis curada
just book-preview           # quarto preview book (live reload)

# Tests y validación
just smoke                  # pytest tests/test_crpto_final_sync.py tests/test_quarto_book_guardrails.py
just test                   # pytest completo
just lint                   # ruff check + format check
just type-check             # mypy src scripts (limpio: 0 errores)
just validate-champion      # verifica hashes vs EXTRACTION_MANIFEST.json
just drift-gate             # recomputa la cadena del certificado y exige diff bit-exacto (CRPTO_RUN_CHAMPION_DRIFT=1)
just bound-audit            # re-deriva el menú de bounds A21 + búsquedas bound-aware

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
12. **Drift-gate tras tocar la capa conformal/PD.** Cualquier refactor de `src/models/conformal*.py`, `src/models/optuna_tuning.py`, `scripts/generate_conformal_intervals.py` o `scripts/train_pd_model.py` debe pasar `just drift-gate` (diff bit-exacto vs la cadena del certificado). Un ROJO significa cambio numérico, no refactor: parar y preguntar. Es la red de seguridad que permitió descomponer los `main()` sin tocar el certificado.

## Qué stages son seguros re-correr

| Stage DVC | ¿Seguro? | Notas |
| --- | --- | --- |
| `crpto.data.dataset` | ⚠️ Lento (1.7 GB) | Determinista; no rompe champion pero re-corre todo downstream. |
| `crpto.data.splits` | ❌ NO | Regenera `train/test/calibration.parquet` (congelados en el manifest). En la deny-list: un `dvc repro` aquí cascada hasta el champion. |
| `crpto.data.features` | ⚠️ | No rompe champion pero re-corre todo downstream; ahora depende de `calibration.parquet`. |
| `crpto.pd.champion` | ❌ NO | Rompe `pd_canonical.cbm`. Ahora también produce `test_predictions.parquet` como out. |
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

## Skills custom del proyecto (`.claude/skills/<nombre>/SKILL.md`)

- `/crpto-render` — render del libro + QA visual con Playwright.
- `/crpto-stage` — `dvc repro` de un stage aislado, con dry-run.
- `/crpto-smoke` — smoke tests + dbt parse + dbt test.
- `/crpto-paper-export` — pipeline completo de salida journal.
- `/crpto-validate-champion` — verifica hashes vs `EXTRACTION_MANIFEST.json`.
- `/crpto-mrm-card` — actualiza model cards en `reports/mrm/`.
- `/crpto-claim-sync` — gate de sincronía de claims paper/gobernanza; obligatorio tras editar paper o supplement.
- `/crpto-submission-freeze` — checklist ejecutable del freeze de submission IJDS (gates, PDFs, anonimato, páginas).

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
