# Auditoría integral CRPTO — 2026-07-05

Auditoría de consistencia de claims, parsimonia de código, skills, docs y plan
editorial del paper, de cara a la submission IJDS (target interno 2026-08-10).
Método: tres pasadas de exploración paralelas (código, claims, tooling/docs)
más verificación directa de fuentes. Corrección post-auditoría: al retomar,
F1/F2 estaban en el working tree pero no committeadas. Codex movió ese trabajo
a `codex/crpto-full-audit-closeout` y cerró F1–F5 con commits separados; P3 se
auditó como no-op por falta de una rama muerta segura en
`scripts/generate_conformal_intervals.py`.

Alcance acordado con Carlos: el refactor incluye la capa protegida validando
con `just drift-gate`; la fuente editorial del paper es `paper/CRPTO_ijds.qmd`
(se porta a mano al `.tex`); el libro Quarto queda fuera de esta ronda.

## 1. Resumen ejecutivo

| Área | Veredicto | Estado |
|---|---|---|
| Claims paper/supplement/tex/tablas/JSONs | Limpio: 0 números stale en 15 claims verificados | Sin acción necesaria |
| `AGENTS.md` | Estaba stale (rebaseline como champion activo) | RESUELTO en F1: reducido a puntero |
| PDFs de submission | `supplement_ijds.pdf` stale (15-jun); PDF oficial sin garantía de frescura | RESUELTO en F1: recompilados y verificados |
| Skills `.claude/skills/` | No cargaban (formato plano) | RESUELTO en F1: migradas + 2 nuevas |
| Código | Sano; sin AI slop; F4 redujo helpers duplicados y F5 cerró el lane protegido seguro | Resuelto en F4/F5 |
| Docs | Memos cerrados mezclados con vigentes; la mayoría pinneados por referencias | Parcial en F2 (ver 7.2) |
| justfile / DVC / CI / pre-commit / configs | Coherentes, sin huérfanos | Sin acción necesaria |
| Escritura del paper | Sin slop de buzzwords; el riesgo real es densidad/repetición | F3 ejecutada |

## 2. Consistencia de claims

Los 15 claims cuantitativos del cuerpo se cotejaron entre `CRPTO_ijds.qmd`,
`supplement_ijds.qmd`, `submission/CRPTO_ijds_submission.tex`, las tablas
A35–A39, los JSONs de gobernanza pool93 y (spot-check) el libro. Referencia
canónica: `docs/research/active_claims_2026-07-04.md`.

| Claim | Valor canónico | Estado |
|---|---|---|
| Retorno body point pool93 | $184,832.48 | OK en qmd, tex (`\$184{,}832.48`), A35, gobernanza |
| V(alpha=0.01) | 0.035350 | OK en todas las fuentes |
| Gamma_CP(alpha=0.01) | 0.162616 | OK; notación Gamma_CP vs gamma de política bien separada |
| Markov cap (alpha=0.01) | 0.345084 | OK (A35 guarda 0.345083740; redondeo esperado) |
| Endpoint budget upper B_u | 0.245084 = 0.1715 + 0.4525 * 0.162616 | OK en body, supplement y A35 |
| Alpha grid | 8/8, violación exacta 0.0 | OK |
| Return floor declarado | $170,464.54 | OK; en gobernanza y supplement, no como headline |
| Frontera consolidada | 50,010 semánticas dedup; 27,508 all-alpha sobre floor | OK |
| Búsqueda terminal | 37,068/37,068 passers; 296,544 checks | OK |
| Panel OOT | 276,869 préstamos | OK |
| Policy mode body | capped_blended_uncertainty (tau 0.1715, gamma 0.5475) | OK |
| Endpoint conservador | $170,467.27, cap 0.273036 | OK |
| Endpoint económico | $223,458.14 ("above $223K" en abstract) | OK |
| Replicaciones externas | Prosper/Freddie como transferencia, no certificados nuevos | OK |
| Métricas PD | AUC 0.7139, Brier 0.1544, ECE 0.0070 | OK |

`tests/test_pool93_body_claim_sync.py` (242 líneas, 9 anclas) enforza la
sincronía manuscrito–gobernanza–tablas. La skill `/crpto-claim-sync` (creada
en F1) empaqueta ese gate más el cotejo por grep de esta tabla.

## 3. Backlog de refactor (parsimonia)

Cadena protegida (todo cambio pasa `just drift-gate` bit-exacto):
`scripts/train_pd_model.py` (2,341 líneas), `scripts/generate_conformal_intervals.py`
(1,870), `scripts/optimize_portfolio.py`, `scripts/validate_conformal_policy.py`,
`scripts/search/run_portfolio_bound_exact_eval.py`, `src/models/conformal/*`,
`src/models/optuna_tuning.py`, `src/models/conformal_tuning.py`,
`src/models/pd_model.py`, `src/models/calibration.py`. Por la regla 12 de
`CLAUDE.md`, cualquier archivo que matchee `src/models/conformal*.py` entra al
lane protegido aunque el cambio parezca trivial.

No se encontró AI slop en código (sin emojis en logs, sin bloques comentados,
sin retry/defensive code de producción). SPO/PyEPO es comparador externo real,
no código vestigial. El detalle ejecutado de S1–S5 y P0–P3 está en la sección 8.

## 4. Skills

Hallazgo principal (resuelto en F1): las 6 skills vivían como
`.claude/skills/<nombre>.md` plano y no cargaban en Claude Code actual, que
requiere `.claude/skills/<nombre>/SKILL.md`. Tras la migración, las 8 skills
cargan (verificado en vivo en la sesión del 2026-07-05).

Inventario post-F1:

| Skill | Estado |
|---|---|
| `/crpto-render` | Migrada; ahora referencia `just book-clean` para recovery |
| `/crpto-stage` | Migrada; ahora incluye nota de costo/tiempo de stages pesados |
| `/crpto-smoke` | Migrada sin cambios |
| `/crpto-paper-export` | Migrada sin cambios |
| `/crpto-validate-champion` | Migrada sin cambios |
| `/crpto-mrm-card` | Migrada; pre-check explícito de `skops` |
| `/crpto-claim-sync` | NUEVA: gate de sincronía de claims (3 pytest + grep de números canónicos en qmd/tex) |
| `/crpto-submission-freeze` | NUEVA: checklist ejecutable del freeze (gates, PDFs, anonimato, 25 páginas, ScholarOne) |

`.codex/skills/crpto/SKILL.md` ya estaba al día (pool93) y no se tocó.

## 5. Disposición de docs

Hallazgo clave al ejecutar F2: **la mayoría de los memos "archivables" están
pinneados por referencias externas** — capítulos del libro los citan
(07, 09, 13, 14, 19, 23), `EXTRACTION_MANIFEST.json` hashea tres de ellos,
y tests/scripts/configs citan otros. Archivar un memo exige editar la
superficie que lo cita, y el libro está fuera de alcance en esta ronda.

Movidos en F2 (cero referencias externas; `git mv` + índices actualizados):

- `docs/refactor/NEXT_WORK_PLAN_2026-06.md` -> `docs/refactor/archive/`
- `docs/refactor/FEATURE_CONFIG_PARQUET_PLAN.md` -> `docs/refactor/archive/`
- `docs/research/paper4_crpto_crosswalk_2026-07-02.md` -> `docs/research/archive/`

KEEP forzado por referencias (candidatos originales que NO se movieron):

| Memo | Pinneado por |
|---|---|
| `crpto_conditional_tightening_appendix_2026-05-04.md` | `EXTRACTION_MANIFEST.json`, `configs/crpto_publication_targets.yaml`, `models/crpto_evidence_status.json`, `scripts/analyze_crpto_evidence.py`, libro 02/03/05 |
| `crpto_journal_package_2026-05-04.md` | `EXTRACTION_MANIFEST.json`, `scripts/build_crpto_journal_package.py`, test del journal package, libro 05/07 |
| `crpto_p1_evidence_2026-05-04.md` | `EXTRACTION_MANIFEST.json`, `tests/test_scripts/test_export_crpto_tables.py`, `scripts/analyze_crpto_evidence.py` |
| `crpto_publication_strategy_2026-05-12.md` | `README.md`, `paper/README.md`, `tests/test_publication_targets.py`, libro 06 |
| `SENSITIVITY_RUN_DESIGN_2026-06.md` | `paper/supplement_ijds.qmd:586` |
| `crpto_bound_tightening_experiment_2026-06-11.md` | `scripts/build_bound_tightening_audit.py` |
| `CONFORMAL_REFACTOR_PLAN.md` | comentarios en `src/models/conformal_diagnostics.py` y `tests/test_models/test_calibrator_pickle_compat.py` |
| reopen plan / tournament protocol / regret closure / bound intake / pyepo intake / extended evidence cards | capítulos del libro 07/09/13/14/19/23 |

Si en la ronda post-submission se edita el libro, ese es el momento de mover
estos memos junto con sus citas. Mientras tanto son la superficie de
provenance que el libro enlaza — moverlos rompería más de lo que limpia.

## 6. Plan editorial del paper (F3 cerrada)

La prosa no tiene slop de buzzwords y los boundaries de claims son
disciplinados. El problema editorial real era densidad y repetición. Los cinco
puntos se cerraron en F3; el detalle de ejecución está en la sección 8.3:

1. Abstract: ~230 palabras con 10+ números; dejar los canónicos y mover
   denominadores de frontera al cuerpo.
2. $184,832.48 aparece 11 veces en el body; reducir donde no aporta.
3. Frase temprana con la regla de selección del body point.
4. Nombrar `test_pool93_body_claim_sync.py` en el párrafo de reproducibilidad.
5. Recompilar PDFs y re-verificar límite de 25 páginas.

### Narrativa y defensa (contexto para la sesión editorial)

El arco de contribución tal como está escrito funciona y no hay que
reinventarlo: (1) problema — la incertidumbre predictiva rara vez cambia el
funded set; (2) diseño — PD congelado + intervalos Mondrian + LP robusto como
capas modulares post-hoc; (3) teoría — el Teorema 1 separa la identidad
determinista del paso Markov bajo la Assumption 1 (weighted funded-set
validity); (4) evidencia — frontera finita pool93 con certificado exacto;
(5) transferencia — Prosper/Freddie como replicación de receta, no
certificados nuevos; (6) gobernanza — cadena bit-exacta y guardrail tests.

Los dos únicos riesgos de lectura que encontró la auditoría, y que F3 cerró sin
debilitar nada más:

1. Un reviewer puede leer el body point como cherry-picking o confundirlo con
   el endpoint económico de $223K — por eso el punto 3 (regla de selección
   enunciada temprano: mayor retorno pasando las ocho alphas bajo el cap
   declarado 0.345, elegido de una frontera finita declarada).
2. "Exact" puede leerse como validez universal en vez de contabilidad sobre el
   funded set congelado — el boundary ya está bien puesto (Teorema 1,
   supplement, CLAIM_AUDIT_MATRIX); al editar, no suavizarlo ni moverlo.

Checklist editorial final: `paper/submission/CLAIM_AUDIT_MATRIX.md` (mapa
claim→evidencia→boundary + banco de objeciones de reviewers) y
`paper/submission/IJDS_SUBMISSION_ROADMAP_2026-08-10.md`. No introducir claims
nuevos: el reopen gate de `active_claims_2026-07-04.md` define las cinco
únicas condiciones que justificarían reabrir la búsqueda.

## 7. Estado de ejecución

### 7.1 F1 — Consistencia rápida (EJECUTADA Y COMMITTEADA 2026-07-05)

- `AGENTS.md`: reducido de 243 líneas stale a un puntero de ~30 líneas hacia
  `CLAUDE.md`, `active_claims_2026-07-04.md` y `.codex/skills/crpto/SKILL.md`,
  con las reglas innegociables inline.
- Skills: 6 migradas vía `git mv` a `.claude/skills/<nombre>/SKILL.md` con
  frontmatter `name:`; 2 nuevas creadas. Las 8 cargan (verificado en vivo).
- `CLAUDE.md`: sección de skills actualizada con las 8.
- PDFs: `just paper-submission-pdf` regeneró `paper/CRPTO_ijds.pdf` y
  `paper/supplement_ijds.pdf`; `latexmk -pdf -gg` regeneró
  `paper/submission/CRPTO_ijds_submission.pdf` (26 páginas, 3 corridas de
  pdflatex + bibtex). Verificación de contenido con pypdf: el PDF contiene las
  frases del último commit del `.tex` (fba278a). Matices descubiertos:
  los tres PDFs están **gitignored por diseño** ("regenerate locally"), así
  que la frescura es local y no genera diffs; y `latexmk` sin `-gg` reporta
  "up-to-date" sin recompilar — usar siempre `-gg` para el freeze.
- Verificación: `just lint` (0 errores, 186 archivos formateados), `just smoke`
  (5 pass), `just validate-champion` (10 pass), más
  `test_pool93_body_claim_sync` + `test_supplement_table_sync` +
  `test_publication_targets` (12 pass).

### 7.2 F2 — Docs archive (EJECUTADA Y COMMITTEADA 2026-07-05, alcance reducido)

Ejecutado: los 3 movimientos listados en la sección 5, más actualización de
referencias en `docs/refactor/README.md`, `docs/research/README.md`,
`docs/SCOPE_AND_GOVERNANCE.md` (lane FEATURE_CONFIG como ejecutado/archivado)
y `docs/research/foundations/crpto_decision_changes_and_learnings.md`.

Reducción de alcance documentada: de ~15 candidatos originales, 12 quedaron
KEEP por la red de referencias (tabla en sección 5). Esto no es deuda: es la
constatación de que el repo usa los memos como superficie de citas.

## 8. Registro detallado de fases ejecutadas

### 8.1 Cómo auditar o retomar trabajo futuro

1. Leer `CLAUDE.md`, este memo (secciones 5–8) y
   `docs/research/active_claims_2026-07-04.md`. Con eso alcanza; no hace falta
   reconstruir la auditoría ni releer los reportes de exploración.
2. Para trabajo nuevo, no mezclar superficies en un commit: prosa, código no
   protegido y código protegido siguen lanes separados.
3. Nada de este cierre requirió re-correr stages DVC protegidos. Si una tarea
   futura parece requerirlo, está mal planteada: parar y preguntar.
4. Código/refactor va en rama + PR (regla 11 de `CLAUDE.md`).
5. Commitear con hooks activos (nunca `--no-verify`); los hooks de pre-push
   corren smoke + validate-champion.

### 8.2 Mapa de gates (qué verifica cada comando y cuánto cuesta)

| Gate | Verifica | Costo | Obligatorio en |
|---|---|---|---|
| `just lint` | ruff check + format | segundos | todo commit |
| `just smoke` | sync final del paper + guardrails del libro (5 tests) | ~30 s | todo commit |
| `just validate-champion` | hashes SHA256 vs `EXTRACTION_MANIFEST.json` (10 tests) | segundos | tras cualquier cambio que produzca outputs |
| `/crpto-claim-sync` | 3 tests de sincronía + grep de números canónicos en qmd/tex | ~1 min | tras editar paper/supplement (F3) |
| `just test-fast` | suite completa sin marks `slow` | minutos | F4 |
| `just bound-audit` | menú de bounds A21 + búsquedas bound-aware | minutos | si se toca optimización (S5) |
| `just drift-gate` | recomputa la cadena del certificado y exige diff bit-exacto; re-puntúa ~514k filas dos veces | largo | baseline antes de F5 y cada commit de F5 |

### 8.3 F3 — Editorial del paper (cerrada 2026-07-05)

Fuente de edición: `paper/CRPTO_ijds.qmd` y `paper/supplement_ijds.qmd`;
cada cambio se porta a mano a `paper/submission/CRPTO_ijds_submission.tex`
(el comentario del `.tex` documenta ese contrato). Solo prosa — ningún número
congelado cambia.

1. **Abstract** (qmd y tex): hoy incluye retorno, V, Gamma_CP, cap, violación,
   50,010, 27,508, endpoint 0.273036, ">$223K", premios externos +1.0/+9.5% y
   panel 276,869. Dejar: panel, retorno, 8/8 con (V, Gamma_CP, cap) y una
   frase de endpoints sin cifras finas. Mover los denominadores 50,010/27,508
   a introducción/resultados (ya están ahí; basta con quitarlos del abstract).
2. **Repetición del headline**: `\$184{,}832.48` aparece en tex líneas ~133,
   361, 632 (tabla certificado), 686, 705 (tabla frontera), 896, 911, 1058
   (conclusión) y en el abstract. Conservar abstract, tabla certificado,
   tabla frontera y conclusión; en el resto usar "the selected body point" o
   "$184.8K". Mismo criterio en el qmd (11 ocurrencias).
3. **Regla de selección del body point**: añadir una frase en la introducción
   (cerca de la primera mención del pool93): el body point es la política de
   mayor retorno que pasa las ocho alphas declaradas bajo el cap declarado
   0.345 — seleccionada de una frontera finita declarada, no un máximo global
   ni el endpoint económico de $223K. Redacción base en
   `active_claims_2026-07-04.md`, sección "How To Present The Denominators".
4. **Reproducibilidad**: en el párrafo de gobernanza del body (tex ~L560-573,
   añadido en fba278a) ya se habla de "guardrail tests"; nombrar explícitamente
   `tests/test_pool93_body_claim_sync.py` en qmd y tex.
5. **Cierre**: `just paper-submission-pdf`; en `paper/submission/`,
   `latexmk -pdf -gg -interaction=nonstopmode CRPTO_ijds_submission.tex`
   (exigir "Output written", no "up-to-date"); verificar <= 25 páginas de body
   excluyendo referencias (última build: 26 páginas totales, referencias
   arrancan en p. 23).

Gate de salida: `/crpto-claim-sync` verde + `just smoke`. Si un número
divergió, la edición se revierte — F3 no puede cambiar valores.

Trampas conocidas de F3:

- `tests/test_pool93_body_claim_sync.py` ancla strings exactos en qmd/tex; si
  una edición elimina la única ocurrencia de un ancla, el test falla — la
  respuesta es reponer el número, nunca ajustar el test.
- Las tablas A35–A39 en `reports/crpto/tables/` son congeladas: el pipeline de
  export no las regenera y ninguna edición editorial debe tocarlas.
- El abstract vive dos veces: `\ABSTRACT{...}` en el tex (~L66–90) y el bloque
  inicial del qmd. Editar ambos o el claim-sync reporta divergencia.
- Formatos al portar qmd->tex: `$184,832.48` vs `\$184{,}832.48`; `Γ_CP` vs
  `\Gamma_{\mathrm{CP}}`. El grep del claim-sync ya cubre ambas variantes.
- El supplement se edita en `paper/supplement_ijds.qmd`; su PDF es HTML-print
  (`just paper-ijds-supplement-pdf`), no LaTeX.

### 7.3 F3/F4/F5 — Cierre Codex 2026-07-05

Estado real de Git al retomar: F1/F2 estaban en el working tree, no
committeadas, pese a que este memo decía "committeadas". Codex movió el trabajo
a la rama `codex/crpto-full-audit-closeout` antes de tocar código.

F3 ejecutada:

- Abstract QMD/TEX comprimido: se quitaron denominadores de frontera, endpoint
  fino y porcentajes externos; quedan panel, retorno redondeado, `8/8`,
  `V`, `Gamma_CP`, cap y una frase de endpoints.
- Introducción QMD/TEX reforzada con la regla de selección del body point:
  mayor retorno que pasa las ocho alphas bajo el cap Markov declarado `0.345`
  dentro de una frontera finita, no óptimo global ni endpoint económico.
- Reproducibilidad QMD/TEX nombra `tests/test_pool93_body_claim_sync.py`.
- Se redujeron repeticiones exactas de `$184,832.48` fuera de certificado,
  frontera y conclusión.
- PDFs regenerados: `just paper-submission-pdf` OK; `latexmk` falló por el
  wrapper TinyTeX (`runscript.tlu` nil), así que se compiló el `.tex` oficial
  con `pdflatex`, `bibtex`, `pdflatex`, `pdflatex`. Resultado: 26 páginas
  totales; referencias arrancan en p. 22, body = 21 páginas.

F4 ejecutada:

- S1: migrados helpers duplicados en scripts paper-facing no protegidos hacia
  `src.utils.script_helpers`. `write_table` ahora acepta `float_precision` para
  preservar salidas `.tex` de 4 vs 6 decimales. `just tables` no dejó cambios
  de contenido en tablas; `just figures` solo produjo ruido PDF/timestamp y se
  descartó.
- S2 KEEP: `src/utils/pipeline_topology.py` no se archiva porque
  `scripts/search/run_conformal_reopen_search.py` importa `load_profile_config`.
- S3 ejecutada: `src/evaluation/calibration_mapping.py` y
  `tests/test_evaluation/test_calibration_mapping.py` retirados; los únicos
  usos vivos restantes son referencias a los artefactos históricos en docs/book.
- S5 KEEP: `src/optimization/cuopt_adapter.py` no se archiva porque está
  conectado a `src/optimization/portfolio_model.py`, perfiles `cuopt` y scripts
  de búsqueda/experimentos.

Gates F4: `just lint`, `just test-fast` y `just validate-champion` en verde.

F5 ejecutada/auditada:

- Baseline previo: `just validate-champion` y `just drift-gate` en verde.
- P0: eliminado `allow_legacy_fallback` de
  `src/models/conformal_artifacts.py`, sus call-sites y test.
- P1: `scripts/optimize_portfolio.py` y `scripts/train_pd_model.py` adoptan el
  `artifact_path` compartido. `generate_conformal_intervals.py` y
  `validate_conformal_policy.py` no tenían helper local equivalente que migrar.
  `_write_json` en `train_pd_model.py` se conservó porque envuelve
  `atomic_write_json`, no el writer LF-idempotente de publicación.
- P2: retirados los dataclasses privados single-use de `train_pd_model.py`
  (`ResolvedFeatureSets`, `TrainingSplits`, `PreparedTrainingInputs`) y
  reemplazados por tuplas desempaquetadas en el mismo flujo.
- P3: auditado sin cambio. `fallback_modes`, `evaluation_scope`,
  `shrinkback_enabled`, `global_rebalance_enabled`, fuentes de probabilidad y
  familias de escala están vivos por CLI/perfiles/tests/reopen; no se encontró
  rama muerta segura para remover sin cambiar superficie operacional.

Gates F5: `just drift-gate` verde con diff cero tras P0, P1/portfolio,
P1/PD y P2; checks enfocados de Ruff/py_compile en verde.

### 8.4 F4 — Refactor lane seguro (cerrada 2026-07-05)

Estado: ejecutada por Codex con alcance conservador. No quedan acciones F4
seguras pendientes; los hallazgos S2/S5 se convierten en KEEP por uso vivo. La
deduplicación protegida segura se cerró después en F5/P1.

- **S1 — script_helpers en scripts no congelados**: ejecutado para scripts
  paper-facing no protegidos. Validación: `just tables`, `just figures`,
  `just lint`, `just test-fast`, `just validate-champion`.
- **S2 — archivar `src/utils/pipeline_topology.py`**: no ejecutado; el grep
  encontró uso vivo en `scripts/search/run_conformal_reopen_search.py`.
- **S3 — archivar/inlinear `src/evaluation/calibration_mapping.py`**:
  ejecutado; el grep por símbolos encontró solo su test.
- **S5 — evaluar `src/optimization/cuopt_adapter.py`**: no ejecutado; el grep
  encontró uso vivo en `portfolio_model.py`, perfiles `cuopt` y scripts.
- **S4 movido al lane protegido**: quitar `allow_legacy_fallback` de
  `src/models/conformal_artifacts.py` matchea `conformal*.py` (regla 12), así
  que exigía drift-gate aunque fuera trivial. Cerrado después como P0 de F5.

Decisión considerada y rechazada: deduplicar `book/_helpers/` contra
`script_helpers` — el aislamiento del libro vale más que ~40 líneas.

Por qué importa la identidad byte a byte en S1: varios outputs de estos
scripts están hasheados en `EXTRACTION_MANIFEST.json` o comparados por tests
de sync, y los writers de `script_helpers` son LF-idempotentes en Windows
precisamente por eso. Si `git diff` muestra cambios de contenido tras
`just tables && just figures`, el refactor rompió algo: revertir y revisar,
no re-hashear.

### 8.5 F5 — Refactor lane protegido (cerrada 2026-07-05)

Estado: cerrada por Codex en `codex/crpto-full-audit-closeout` siguiendo el
protocolo **un cambio -> un `just drift-gate` verde -> un commit**. Cada corrida
de `drift-gate` reportó diff cero en `y_pred`, intervalos PD, score-band edges,
coberturas por celda y floor multipliers.

- **P0**: ejecutado. Se eliminó `allow_legacy_fallback` (deprecado) de
  `src/models/conformal_artifacts.py`, call-sites y test.
- **P1**: ejecutado donde había helper real que migrar. `optimize_portfolio.py`
  y `train_pd_model.py` usan `src.utils.script_helpers.artifact_path`;
  `generate_conformal_intervals.py` y `validate_conformal_policy.py` no tenían
  `_artifact_path`/writer/loader local equivalente. El wrapper `_write_json` de
  `train_pd_model.py` permanece por semántica atómica (`atomic_write_json`).
- **P2**: ejecutado. Los dataclasses privados single-use de `train_pd_model.py`
  (`ResolvedFeatureSets`, `TrainingSplits`, `PreparedTrainingInputs`) fueron
  sustituidos por tuplas privadas y desempaquetado inmediato.
- **P3**: auditado sin cambio. No se encontró rama muerta segura en
  `generate_conformal_intervals.py`: los modos/fallbacks sospechosos están
  conectados a CLI, perfiles, tests o reopen search; removerlos sería cambio de
  superficie, no limpieza mecánica.

Límites duros: no mover/renombrar clases que el calibrator pickle referencia
(compatibilidad documentada en `CONFORMAL_REFACTOR_PLAN.md` y
`tests/test_models/test_calibrator_pickle_compat.py`); no tocar
`EXTRACTION_MANIFEST.json`; si un cambio pide re-keying de DVC, es señal de
alcance excedido: parar y pedir permiso explícito.

Nota operativa para futuros lanes protegidos: mantener el mismo protocolo de
drift-gate por commit. Si un cambio pide re-keying de DVC o toca
`EXTRACTION_MANIFEST.json`, es alcance excedido: parar y pedir permiso
explícito.
