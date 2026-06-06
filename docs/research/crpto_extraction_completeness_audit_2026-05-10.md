# Auditoría De Completitud De Extracción CRPTO

Fecha: 2026-05-10

Esta segunda pasada revisó el libro Quarto completo y documentación fuente para incorporar material que el capítulo CRPTO usaba como conocimiento previo. El nuevo libro ahora separa el manuscrito/base journal de un dossier extendido para decidir qué entra al paper, appendix o versión journal.

## Capítulos Extendidos Añadidos

| Capítulo nuevo | Motivo | Fuentes origen |
|---|---|---|
| `15-fundamentos-riesgo-ml.qmd` | Base conceptual que el capítulo CRPTO original daba por conocida: PD, calibración, métricas y modelos tabulares. | `book/chapters/02-glossary/02a-credit-risk-fundamentals.qmd`, `book/chapters/02-glossary/02b-ml-statistics-foundations.qmd` |
| `16-fundamentos-conformal-optimizacion.qmd` | Marco teórico extendido para convertir incertidumbre conformal en conjuntos robustos de decisión. | `book/chapters/02-glossary/02c-uncertainty-conformal.qmd`, `book/chapters/02-glossary/02d-optimization-or.qmd` |
| `17-pipeline-datos-features.qmd` | Material de método y reproducibilidad previo al CRPTO: origen de datos, split temporal, leakage, WOE/IV y contrato de features. | `book/chapters/03-tech-stack.qmd`, `book/chapters/04-pipeline-overview/04a-data-ingestion-lineage.qmd`, `book/chapters/04-pipeline-overview/04b-temporal-splitting.qmd`, `book/chapters/05-feature-engineering/05a-woe-iv-optbinning.qmd`, `book/chapters/05-feature-engineering/05b-derived-features-ratios.qmd`, `book/chapters/05-feature-engineering/05c-feature-contract.qmd` |
| `18-pd-calibracion-champion.qmd` | Dossier predictivo que sostiene el score PD usado por CRPTO y sus decisiones robustas. | `book/chapters/06-pd-modeling/06a-logistic-regression-baseline.qmd`, `book/chapters/06-pd-modeling/06b-catboost-tuned.qmd`, `book/chapters/06-pd-modeling/06c-calibration-selection.qmd`, `book/chapters/06-pd-modeling/06d-model-comparison-champion.qmd` |
| `19-conformal-dossier.qmd` | Evidencia técnica ampliada para elegir la capa conformal, comparar incertidumbre y justificar el barrido de alpha. | `book/chapters/07-conformal/index.qmd`, `book/chapters/07-conformal/07a-split-conformal-basics.qmd`, `book/chapters/07-conformal/07b-mondrian-group-conditional.qmd`, `book/chapters/07-conformal/07c-cqr-variants-benchmark.qmd`, `book/chapters/07-conformal/07d-backtest-monitoring.qmd`, `book/chapters/13-advanced-topics/13a-uncertainty-baselines.qmd`, `book/chapters/13-advanced-topics/13b-alpha-sweep-pareto.qmd` |
| `20-portafolio-policy.qmd` | Puente entre predict-then-optimize, política económica y frontera de robustez que alimenta el claim central de CRPTO. | `book/chapters/09-portfolio/index.qmd`, `book/chapters/09-portfolio/09a-deterministic-portfolio.qmd`, `book/chapters/09-portfolio/09b-robust-portfolio.qmd`, `book/chapters/09-portfolio/09c-policy-selection.qmd`, `book/chapters/09-portfolio/09e-efficient-frontier.qmd` |
| `21-gobernanza-explicabilidad-dataset.qmd` | Material para appendix journal, defensa MRM, interpretabilidad y descripción profunda del universo Lending Club. | `book/chapters/10-ifrs9-governance/10e-model-risk-management.qmd`, `book/chapters/10-ifrs9-governance/10f-mrm-deep-dive.qmd`, `book/chapters/11-explainability/index.qmd`, `book/chapters/11-explainability/11a-global-explanations.qmd`, `book/chapters/11-explainability/11b-local-explanations.qmd`, `book/chapters/11-explainability/11c-explanation-drift.qmd`, `book/chapters/12-dataset-360/index.qmd`, `book/chapters/12-dataset-360/12a-eda-highlights.qmd`, `book/chapters/12-dataset-360/12b-geographic-temporal.qmd`, `book/chapters/12-dataset-360/12c-literature-benchmark.qmd` |
| `22-literatura-trazabilidad-entorno.qmd` | Contexto académico, contribuciones, notebooks, artefactos y configuración que ayudan a decidir qué va al paper y qué al journal. | `book/chapters/18-research-agenda/18a-state-of-the-art.qmd`, `book/chapters/18-research-agenda/18b-thesis-contributions.qmd`, `book/chapters/A-notebook-atlas.qmd`, `book/chapters/C-artifact-catalog.qmd`, `book/chapters/D-configuration-reference.qmd`, `book/chapters/F-rerun-v2-refactor.qmd` |

## Documentación Curada Añadida

- `docs/research/foundations/crpto_model_risk_management.md` desde `docs/MODEL_RISK_MANAGEMENT.md`
- `docs/research/foundations/crpto_paper_development_playbook_2026.md` desde `docs/PAPER_DEVELOPMENT_PLAYBOOK_2026.md`
- `docs/research/foundations/crpto_references_state_of_art.md` desde el mapa bibliografico original del dossier historico CRPTO
- `docs/research/foundations/crpto_runbook.md` desde `docs/RUNBOOK.md`
- `docs/research/foundations/crpto_pipeline_topology_2026-03-31.md` desde `docs/PIPELINE_FIRST_TOPOLOGY_2026-03-31.md`
- `docs/research/foundations/crpto_artifact_retention_policy.md` desde `docs/ARTIFACT_RETENTION_POLICY.md`
- `docs/research/foundations/crpto_integrations_setup.md` desde `docs/INTEGRATIONS_SETUP.md`
- `docs/research/foundations/crpto_project_justification.md` desde `docs/PROJECT_JUSTIFICATION.md`
- `docs/research/foundations/crpto_conformal_prediction_readme.md` desde `docs/conformal_prediction_README.md`
- `docs/research/foundations/crpto_quarto_traceability_2026-03-30.md` desde `docs/CANONICAL_DOCUMENTATION_AND_QUARTO_TRACEABILITY_2026-03-30.md`

## Exclusiones Deliberadas

| Área | Motivo |
|---|---|
| Inferencia causal/CATE | No entra al core CRPTO; se mantiene solo como ruta futura cuando aparece en discusión editorial. |
| Survival, IFRS9 ECL, LGD/EAD conformal | Pertenece a otros papers o líneas regulatorias; solo MRM se incluyó por gobernanza del CRPTO. |
| GPU, Quantum y Streamlit companion | No son necesarios para el paper/journal CRPTO actual; se excluyen para mantener independencia y foco. |

## Entorno Dedicado

El proyecto contiene `.venv/` propio generado por `uv`. El `pyproject.toml` declara el stack completo de CRPTO: CatBoost, Venn-Abers, MAPIE, Optuna, OptBinning, Pyomo/HiGHS, OR-Tools, DVC, MLflow, DagsHub, DuckDB/dbt, Pandera, Quarto/Jupyter helpers, visualización y el bloque SPO (`pyepo` + `torch`). `make setup` instala el entorno completo; `make setup-base` queda disponible si se necesita una instalación ligera sin SPO.

## Cierre Exhaustivo Final

La pasada final agregó la guía editorial completa (`06b-guia-editorial-claims`),
un apéndice curado de puentes regulatorios/future-work (`23-apendices-regulatorios-y-future-work`),
assets faltantes del libro grande, registros de pipeline CRPTO-only, perfiles
`crpto_e2e_default`, `crpto_core_canonical_cpu` y
`crpto_diagnostics_governance_default`, y JSONs equivalentes en
`models/pipeline_registry/`.

Se reforzó la reproducibilidad con `dvc.lock` completo para los stages CRPTO,
rutas dbt relativas, y un suite ampliado de tests. Validaciones finales:
`uv run pytest -q` pasó, `quarto render book --to html` pasó,
`uv run dbt parse/test` pasó, `uv run dvc status --no-updates` quedó limpio, y
los scans de branding legado no encontraron tokens heredados de la extracción
anterior en archivos públicos fuera de outputs renderizados/cache.
