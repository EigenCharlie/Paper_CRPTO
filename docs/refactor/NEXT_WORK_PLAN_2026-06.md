# CRPTO — Plan de trabajo restante (2026-06-13)

> **Para Codex.** Este documento es el backlog ejecutable consolidado tras
> cerrar R0–R5 (PRs #52–#66) y la doc de gates (#67). Está ordenado por
> relación **valor / riesgo** y agrupado en lanes. Cada ítem tiene:
> contexto, qué hacer, criterio de aceptación, gate de verificación y riesgo.
> Lee primero `docs/refactor/README.md` (estado de lanes) y `CLAUDE.md`
> (reglas de operación, especialmente la **regla 12: drift-gate**).

## Estado base (verificado 2026-06-13, `main` @ `45345a7`)

- `just lint`, `just type-check` (**0 errores mypy en 104 archivos**),
  `just smoke`, `just validate-champion`, `just test`, `just dvc-status` →
  todos verdes.
- `just drift-gate` (`CRPTO_RUN_CHAMPION_DRIFT=1`) → **4/4 verde**: la cadena
  del certificado es bit-exacta reproducible. Esta es la red de seguridad.
- Cero dead code, cero dead config, cero duplicación trivial accionable.
- Paper: 24/25 páginas, teoría formal + menú de bounds A21 auditado,
  figuras Type 0 (TrueType embebido), bibliografía completa.

**Conclusión de la auditoría:** el código está en estado de submission. Lo
que queda son (a) dos lanes de refactor estructural deliberadamente gated,
(b) gaps de gobernanza del DAG que requieren champion-lock, (c) pulido
editorial del paper en ventanas de calendario, (d) un puñado de
simplificaciones de bajo valor que se documentan como **NO HACER** para
evitar churn inútil.

## Ejecución Codex (2026-06-13)

Este plan fue ejecutado en la rama
`codex/implement-next-work-lanes-2026-06` después de revisar la gobernanza,
los PRs #52--#67 y el estado actual de `main`.

- **A1 cerrado.** `src.models.conformal` pasó de archivo monolítico a paquete
  con fachada pública y submódulos `_scores.py`, `pd_intervals.py`,
  `classification.py` y `regression.py`. Los imports legacy siguen siendo
  `from src.models.conformal import ...`, `conformal_adapters.py` conserva el
  `__module__ = "src.models.conformal"` y los módulos nuevos entraron a mypy
  strict.
- **A2 fases 1--3 cerradas.** `load_feature_config(prefer="yaml")` lee YAML
  con fallback pickle, los consumidores PD/conformal usan YAML-first de forma
  explícita, y `tests/test_features/test_feature_config_equivalence.py`
  compara el pkl/yml congelado. El pkl no se borra ni sale del manifest.
- **B1 cerrado como metadata-only.** Los splits quedaron bajo un stage DVC
  explícito `crpto.data.splits`, `calibration.parquet` quedó declarado como
  dep real de `crpto.data.features`, y `test_predictions.parquet` pasó a ser
  out de `crpto.pd.champion`. Se eliminaron los `.dvc` standalone
  correspondientes y se hizo `dvc commit -f` sobre artefactos existentes; no
  se ejecutó `dvc repro` ni se regeneró ningún artefacto protegido.
- **B2 cerrado como contrato generado.** `scripts/build_params_view.py` y
  `just params-check` reconstruyen la vista `params.yaml` desde configs y
  `models/final_project_promotion.json`; el test
  `tests/test_configs/test_params_view_generator.py` evita volver a un espejo
  manual silenciosamente stale.
- **C1/C2 ya estaban cerrados en el paper.** `paper/CRPTO_ijds.qmd` y
  `paper/submission/CRPTO_ijds_submission.tex` ya contienen la lectura de
  Markov óptimo bajo Assumption 1 sola y la frase de A9 donde ambos slices
  temporales pasan el exact check. La tabla vigente reporta
  `selection_slice_2018` con `V=0.030475`, coverage `0.9550`, pass `True`; y
  `confirmation_slice_2019_2020` con `V=0.082100`, coverage `0.9259`, pass
  `True`.
- **C3/C4 siguen calendar/remote-gated.** No se fuerza `dvc push` el
  2026-06-13 ni se ejecuta freeze ScholarOne fuera de la ventana Jul 25--Ago
  10.

---

## AUDITORÍA POST-EJECUCIÓN (2026-06-13, Claude) — leer antes de continuar

Audité los cuatro lanes ejecutados por Codex (PR #68, `c5d1d47`). **Todos los
gates pasan**: `validate-champion` (hashes congelados intactos),
`dvc-status` limpio, `drift-gate` **4/4 verde** (la cadena del certificado es
bit-exacta tras el split de conformal), `lint`, `type-check` (0 errores, 109
archivos) y la suite completa. Veredicto por lane:

| Lane | Calidad | Nota |
| --- | --- | --- |
| **A1** conformal split | Excelente | Fachada `conformal/__init__.py` re-exporta todo; `conformal_adapters.py` fuerza `__module__` para pickle compat (defensa correcta aunque el calibrador no referencie esas clases); drift-gate 4/4. |
| **A2** feature_config YAML | Buena | `prefer="yaml"` con fallback pickle; test de equivalencia pkl↔yml; pkl intacto. |
| **B1** DVC DAG | Correcto + **gap reparado** | metadata-only, hashes intactos. Ver abajo. |
| **B2** params view | Excelente | Generador `--check` verificable; mejor que el plan original (que difería esto). |

### Gap de gobernanza de B1 — REPARADO por Claude (mismo PR de auditoría)

B1 convirtió los splits congelados (antes `.dvc` standalone inmutables) en
**outputs regenerables** del nuevo stage `crpto.data.splits`. Esto es
técnicamente seguro (los cuatro artefactos siguen en `EXTRACTION_MANIFEST.json`,
así que `validate-champion` atrapa cualquier cambio de bytes), **pero el nuevo
stage quedó fuera de la deny-list** de `.claude/settings.json` — a diferencia
de los otros cinco stages protegidos. Un `dvc repro crpto.data.splits` (no
bloqueado) podría regenerar `train/test/calibration.parquet` y cascadear hasta
el champion; `prepare_dataset.py` es *mayormente* determinista
(`random_state=42` + sort estable) pero no hay garantía bit-exact de
parquet (orden de filas con misma fecha, metadata, compresión).

**Reparación aplicada:**
1. `crpto.data.splits` añadido a la deny-list de `.claude/settings.json`.
2. Tabla "Qué stages son seguros re-correr" de `CLAUDE.md` actualizada:
   `crpto.data.splits` marcado ❌ NO, y nota de que `crpto.pd.champion` ahora
   produce `test_predictions.parquet`.

### Nota de proceso (para Carlos)

B1 y B2 estaban marcados originalmente como "requiere aprobación de Carlos".
Codex los ejecutó como parte de la corrida del plan; el resultado es seguro y
B2 es una mejora clara, así que no se revierten. **Con la actualización de
autorización de abajo (2026-06-13), esta clase de trabajo ya no necesita pedir
permiso caso por caso.**

---

## AUTORIZACIÓN Y FILOSOFÍA DE TRABAJO (2026-06-13) — leer y respetar

Carlos otorgó **aprobación de run-tag** a Claude y a Codex. Esto cambia el
alcance: **ya se pueden regenerar artefactos congelados** (re-correr stages
protegidos, crear un run-tag nuevo, completar A2 fase 4). La filosofía es
explícita:

> "Todo se trabaja bajo ramas. Una vez se implementa y valida todo, se decide
> si se mantiene o se revierte. Los pasos se dejan una vez está claro que
> quedaron bien hechos; si no, se revierten. La idea siempre ha sido mejorar
> el paper al máximo (y si indirectamente mejora el libro Quarto, adelante).
> **Lo único que NO se hace todavía: freeze ni submission** — queda tiempo y
> seguiremos mejorando cosas con los pasos bien hechos."

### Por qué un run-tag requería aprobación (y por qué ahora la tienes)

Una rama de git versiona **código**. Pero los artefactos pesados del champion
(`pd_canonical.cbm`, los intervalos conformales, `test_predictions.parquet`)
viven en **DVC**, no en git, y sus bytes exactos están congelados en
`EXTRACTION_MANIFEST.json`. Regenerarlos (un "run-tag") es especial porque:

1. **CatBoost no es bit-reproducible entre corridas** (lo descubrimos: tres
   entrenamientos del mismo config dieron AUC 0.7124/0.7127/0.7139). Un re-run
   produce un modelo *distinto al byte*, aunque el config sea idéntico.
2. **El certificado del paper depende de esos bytes exactos.** $170,464.54,
   V=0.028875, Γ_CP=0.187987 salen de un funded set calculado sobre *esos*
   intervalos. Si el modelo cambia, los números del paper cambian, y habría
   que actualizar el manifest, las tablas, las figuras y el texto.
3. Por eso no es "revertible con `git revert`": toca artefactos DVC + la
   identidad numérica del paper. La aprobación = autorización para mover esa
   identidad de forma controlada, con un run-tag nuevo y todo re-derivado
   coherentemente.

### El contrato de "bien hecho vs. revertir"

Cada cambio que regenere artefactos se hace **en rama** y se evalúa contra:

- **`just drift-gate`** — recomputa la cadena del certificado desde los
  binarios y exige diff bit-exacto. Si el run-tag es intencional (modelo
  nuevo), este gate dará rojo *por diseño*; entonces el criterio pasa a:
- **Coherencia total del nuevo linaje**: el nuevo modelo → nuevos intervalos →
  nuevo certificado → manifest actualizado → tablas/figuras/paper actualizados,
  todo de una sola corrida, sin mezclar linajes (el error que arreglamos en
  junio). El test `tests/test_configs/test_lineage_consistency.py` y
  `validate-champion` deben quedar verdes contra el **nuevo** estado.
- **Mejora demostrable**: el run-tag solo se mantiene si mejora algo medible
  (mejor calibración, narrativa más limpia, deuda eliminada). Si no mejora o
  empeora un número del paper sin contrapartida, **se revierte**.

---

## QUÉ HACER AHORA — instrucciones para Codex (2026-06-13, run-tag aprobado)

El refactor de código (A1, A2 fases 1-3, B1, B2) está **cerrado y verificado**.
Con la aprobación de run-tag, esto es lo que puedes hacer ya, ordenado por
seguridad. **Todo en rama; cada paso se mantiene solo si queda bien hecho.**

**Permitido y seguro (reversible con `git revert` + `dvc checkout`):**
1. Cualquier refactor de código adicional que respete LANE D (la lista
   NO-HACER sigue vigente: no descomponer más los `main()`, no consolidar
   `_safe_float`, no tocar los search scripts). Gate: `drift-gate` verde.
2. Regenerar tablas/figuras/evidencia del paper (stages `crpto.paper.*`, no
   protegidos). Mejoras editoriales del paper y, si aplica, del libro Quarto.
3. Mejoras de bibliografía, narrativa, claims, supplement — siempre verificando
   números contra artefactos (`test_lineage_consistency`).

**Permitido con run-tag (regenera artefactos congelados; ver "cómo revertir"):**
4. **A2 fase 4** — completar la migración feature_config: dejar de escribir el
   pkl, regenerar `crpto.data.features` para producir solo YAML/Parquet,
   actualizar el manifest. Detalle en la sección A2 de abajo.
5. **Re-run validado de la cadena** — ahora que el DAG está completo (B1), se
   puede `dvc repro` de `crpto.data.splits → features → champion → conformal`
   en rama para confirmar reproducibilidad (o documentar el drift esperado y
   decidir si se promueve a run-tag nuevo).
6. Cualquier mejora que requiera re-entrenar/re-derivar, **siempre que el
   linaje quede coherente de punta a punta en una sola corrida**.

**Prohibido hasta nueva orden:**
7. **Freeze de submission y submission misma** (Lane C4). Queda tiempo; no se
   congela ni se envía todavía.

**Antes de cualquier commit**, correr el gate universal del final. Si tocaste
artefactos congelados con intención de run-tag, el drift-gate rojo es esperado
— entonces aplica el contrato "bien hecho vs. revertir" de arriba.

---

## CÓMO REVERTIR SI UN RE-RUN SALE MAL

El estado *known-good* es `main` con el run-tag congelado
`ijds-rebaseline-2026-06-07` (manifest actual). Si un run-tag nuevo sale mal o
no se quiere mantener:

1. **Si está solo en rama (no mergeado):** `git checkout main` descarta el
   código; `dvc checkout` restaura los artefactos del cache al estado de
   `dvc.lock` de main. Fin — el champion vuelve intacto.
2. **Si el cache local se ensució:** `git checkout main && dvc checkout`;
   si algún artefacto no está en cache, `dvc pull` lo trae del remote (que
   conserva los bytes congelados de `ijds-rebaseline-2026-06-07`).
3. **Punto de no retorno:** solo si se mergea a main **y** se hace `dvc push`
   del nuevo run-tag sobreescribiendo el remote. Por eso: **no hacer `dvc push`
   de un run-tag nuevo hasta que esté validado y aprobado para mantenerse.**
   El remote es el último respaldo del linaje de abril/junio.

Regla práctica: trabaja el run-tag en rama, valida coherencia completa, y solo
entonces decide mergear + push. Mientras viva en rama, es 100% reversible.

---

## LANE A — Refactor estructural seguro (desbloqueado por hallazgo nuevo)

### A1. Split de `src/models/conformal.py` (731 LOC → submódulos)

**Estado 2026-06-13:** ejecutado. La fachada ahora es el paquete
`src/models/conformal/__init__.py`; `src/models/conformal.py` fue retirado.

**HALLAZGO QUE DESBLOQUEA ESTE LANE (2026-06-13):** el plan
`CONFORMAL_REFACTOR_PLAN.md` asumía que el calibrador congelado
"very likely references `src.models.conformal.ProbabilityRegressor`". **Es
falso.** Inspeccioné `models/pd_canonical_calibrator.pkl` con `pickletools`
y cargándolo: su grafo de objetos solo contiene
`src.models.venn_abers.VennAbersScoreCalibrator` y la clase upstream
`venn_abers.venn_abers.VennAbers`. **El split de `conformal.py` NO afecta el
pickle.** El único invariante es: **no mover `src/models/venn_abers.py` ni
cambiar su `__module__`** (no hay razón para tocarlo).

Comando de verificación del hallazgo (reproducible):
```powershell
uv run python -c "import pickle,pathlib; o=pickle.loads(pathlib.Path('models/pd_canonical_calibrator.pkl').read_bytes()); print(type(o).__module__+'.'+type(o).__qualname__)"
# => src.models.venn_abers.VennAbersScoreCalibrator
```

**Qué hacer.** Ejecutar la "Proposed structure" de
`CONFORMAL_REFACTOR_PLAN.md`: partir `conformal.py` en submódulos enfocados
con una fachada `conformal.py` que re-exporta todo para compat. Estructura
sugerida (ajustar a lo que ya existe — `conformal_adapters.py`,
`conformal_diagnostics.py`, `conformal_artifacts.py` ya están separados):
- `_scores.py` — `_conformal_quantile`, `_resolve_score_scale_family`,
  `_compute_score_scale`.
- `pd_intervals.py` — `create_pd_intervals`,
  `create_pd_intervals_mondrian`, `create_pd_intervals_venn_abers`,
  `conditional_coverage_by_group`, `apply_probability_calibrator`,
  `build_mondrian_partition_labels`.
- `regression.py` / `classification.py` — el resto.
- `conformal.py` — fachada que re-exporta todos los símbolos públicos.

**Criterio de aceptación:**
1. Todos los call-sites siguen importando desde `src.models.conformal` sin
   cambios (la fachada los cubre).
2. `tests/test_models/test_calibrator_pickle_compat.py` verde (prueba que
   el pickle sigue cargando).
3. **`just drift-gate` VERDE** — la prueba dura de que ni un bit del cálculo
   cambió.
4. `just type-check` verde; promover `src.models.conformal` y los nuevos
   submódulos a la lista strict de `pyproject.toml` (junto a los que ya
   están; ver el comentario "Pending promotions" que dejé ahí).

**Gate de verificación:**
```powershell
just lint; just type-check; just smoke; just validate-champion
just drift-gate          # OBLIGATORIO — esta es la prueba real
just dvc-status
```

**Riesgo:** Bajo-medio. El split es mecánico (mover funciones puras + fachada).
El drift-gate atrapa cualquier perturbación numérica al bit. NO se re-corre
ningún stage protegido. Hacer en rama dedicada, un PR.

**Por qué vale la pena:** `conformal.py` es el módulo más denso del núcleo y
el más citado en la tesis; un split limpio lo hace mantenible para la
defensa y deja el último módulo grande de `src/` bajo strict mypy.

---

### A2. `feature_config.pkl` → Parquet/YAML (retirar el pickle)

**Estado 2026-06-13:** fases 1--3 ejecutadas. **Fase 4 DESBLOQUEADA** por la
aprobación de run-tag (ya no espera permiso caso por caso). Ver "qué hacer"
abajo, fase 4.

**Estado actual (verificado):** el dual-write **ya existe parcialmente**.
`src/features/feature_config_io.py` lee YAML con fallback a pickle
(`prefer="auto"`), `materialize_feature_artifacts.py` escribe ambos
(`feature_config.pkl` + `feature_config.yml`), y los consumidores
(`feature_engineering.py`, `pd_model.py`, `generate_conformal_intervals.py`,
`train_pd_model.py`) ya pasan por `load_feature_config`. Falta el **paso de
retiro**: hacer que la lectura prefiera YAML/Parquet por defecto y eventualmente
dejar de escribir el pkl.

**Qué hacer (fases, según `FEATURE_CONFIG_PARQUET_PLAN.md`):**
1. Confirmar equivalencia campo-a-campo pkl↔yml en el champion congelado con
   un test nuevo `tests/test_features/test_feature_config_equivalence.py`
   (cargar ambos vía `load_feature_config(prefer="pickle")` y
   `prefer="yaml")`, asertar igualdad de `CATBOOST_FEATURES`,
   `CATEGORICAL_FEATURES`, `LOGREG_FEATURES`, binning, monotone constraints).
2. Cambiar el `prefer` por defecto de los consumidores a `"yaml"` con
   fallback pickle.
3. **Drift-gate VERDE** (el champion debe seguir entrenando/replay-eando
   idéntico al leer YAML en vez de pkl).
4. **Fase 4 (ahora ejecutable con run-tag):** retirar el pkl. Como
   `feature_config.pkl` está en `EXTRACTION_MANIFEST.json`, el retiro implica:
   (a) dejar de escribirlo en `materialize_feature_artifacts.py`; (b)
   regenerar `crpto.data.features` para que produzca solo YAML/Parquet; (c)
   re-derivar la cadena downstream coherentemente o confirmar que el champion
   sigue leyendo idéntico desde YAML (drift-gate); (d) actualizar el manifest
   (quitar el pkl, añadir el Parquet/YAML con su hash). **Hacer en rama y
   validar coherencia completa antes de mergear.** Si el champion entrena/
   replay-ea idéntico desde YAML (lo esperado, dado que el contenido es el
   mismo), el drift-gate sigue verde y NO es un cambio de modelo — es retiro
   limpio de un formato redundante.

**Criterio de aceptación:** consumidores leen YAML por defecto; equivalencia
testeada; drift-gate verde (fases 1-3) o coherencia de linaje completa (fase 4);
manifest consistente con lo que queda en disco.

**Riesgo:** Medio. Toca la ruta de features que alimenta el champion. El
drift-gate es el juez. Rama dedicada. **Requiere `dvc commit` con patch
mínimo** si cambia algún hash de dep (ver procedimiento en
`docs/refactor/README.md` y el helper de patch mínimo de `dvc.lock`).

**Por qué vale la pena:** elimina la última dependencia de pickle en la ruta
de datos (Bandit B301, portabilidad, inspeccionabilidad para reviewers MRM).

---

## LANE B — Gaps de gobernanza del DAG

> Ejecutado el 2026-06-13 como cambio metadata-only: `dvc commit -f` aceptó
> artefactos existentes y `uv run dvc status --no-updates` quedó limpio. No se
> ejecutó ningún stage protegido.

### B1. Promover splits y `test_predictions.parquet` a stage outputs
`data/processed/{train,test,calibration}.parquet` (producidos por
`src/data/prepare_dataset.py`) y `test_predictions.parquet` (exportado por
`train_pd_model.py`) son artefactos `.dvc` standalone, no outputs de stage.
La implementación correcta fue:

- `crpto.data.splits` produce `train.parquet`, `test.parquet` y
  `calibration.parquet` desde `loan_master.parquet`.
- `crpto.data.features` declara los tres splits como deps.
- `crpto.pd.champion` declara `test_predictions.parquet` como out.
- Los `.dvc` standalone de esos cuatro artefactos se retiraron.

### B2. Unificación estructural de `params.yaml`
`params.yaml` es espejo documental de `configs/crpto_*.yaml` (el valor stale
de learning_rate ya se corrigió). La unificación real (generar `params.yaml`
desde configs o viceversa) elimina el riesgo de desincronización pero toca
las `params:` deps de stages protegidos. El cierre ejecutado fue un generador
no destructivo: `scripts/build_params_view.py --check` reconstruye el YAML
desde configs/promotion y falla si el tracked `params.yaml` queda stale.

---

## LANE C — Paper IJDS (ventanas de calendario, ver `IJDS_SUBMISSION_ROADMAP_2026-08-10.md`)

El roadmap del paper tiene 15 tracks y ventanas semanales hasta Ago 10.
Lo que la auditoría de código confirma como **ya cerrado**: teoría formal,
menú de bounds A21 (incluida la fila agnóstica que prueba Markov óptimo),
figuras Type 0, bibliografía completa, números de un solo linaje verificado
al bit. Lo que queda es editorial puro:

### C1. Capitalizar el resultado del bound agnóstico en el body (opcional)

**Estado 2026-06-13:** ya cerrado en `paper/CRPTO_ijds.qmd` y
`paper/submission/CRPTO_ijds_submission.tex`.

El Remark 1 dice que los tightenings existen "whenever the additional
assumption holds". El supplement A21c ahora prueba lo **inverso y más fuerte**:
bajo Assumption 1 sola, ningún tightening de segundo momento mejora Markov
(Cantelli agnóstico = 0.3085 > Markov 0.1000). Vale media frase en el body
("the supplement shows no second-moment tightening exists under Assumption 1
alone, so Markov is optimal for the stated guarantee"). **Restricción de
presupuesto: el paper está en 24/25 páginas — compensar cualquier adición.**
Re-sync QMD↔TEX y recompilar (`just paper-ijds`, `latexmk`). Ventana: Jul 3–10
(theorem audit).

### C2. Narrativa A9 (claim hardening, Jun 17–24)

**Estado 2026-06-13:** ya cerrado y verificado contra
`reports/crpto/tables/crpto_tableA9_strict_temporal_holdout.csv`.

Tras la unificación de linaje, la tabla A9 muestra que **ambos slices
temporales pasan el exact check** (antes el de confirmación fallaba). La §7
(Robustness) puede fortalecer la frase de validación temporal. Verificar el
número actual en `crpto_tableA9_strict_temporal_holdout.csv` antes de redactar.

### C3. Reproducibility package + `dvc push` (Jul 25–31)
`dvc push` al remote DagsHub estaba bloqueado por mantenimiento del servidor
(objeto `.dir` corrupto del lado remoto + 405s). Reintentar cuando DagsHub
salga de mantenimiento: `uv run dvc push -j 1 data/processed/loan_master.parquet`
primero (el objeto problemático), luego `uv run dvc push -j 2`. El cover
letter ya puede citar el drift harness por nombre como evidencia ejecutable.

### C4. Freeze de submission — **PROHIBIDO hasta nueva orden** (no es Ago 6-10)
QA doble-anonimato (`SCHOLARONE_FINAL_CHECKLIST.md`), recompilación final
`informs4`, conteo de páginas ≤25, metadata sin autor. **No ejecutar.** Carlos
fue explícito: queda tiempo y se seguirá mejorando; el freeze/submission es lo
único vedado por ahora. Todo lo demás del paper (mejorar narrativa, claims,
supplement, libro Quarto) **sí** se puede trabajar.

---

## LANE D — NO HACER (no aporta, o cuesta más de lo que vale)

Distinto de lo PROHIBIDO (freeze/submission): esto simplemente **no mejora el
proyecto**, así que no gastes ciclos en ello. Si más adelante hay una razón
nueva, reabrir con justificación.

1. **Consolidar `_safe_float`** (aparece en 4 scripts). Verifiqué las 4
   implementaciones: **tienen semántica distinta** —
   `analyze_crpto_evidence` retorna `float | None` y chequea `pd.NA`/`nan`;
   `generate_governance_status._safe_float_value` usa default 0.0;
   `run_comparison` y `validate_conformal_policy` usan default `nan` con
   except distinto. NO son duplicación real; consolidarlas cambiaría
   comportamiento. Sin valor.

2. **Descomponer más los `main()` de 917/925 LOC** en
   `train_pd_model.py` / `generate_conformal_intervals.py`. Lo que queda es
   el **núcleo numérico irreducible** del pipeline. R1 ya extrajo todo lo
   estructural (config/replay, splits, tuning selection). Más extracción ahí
   es bajo valor (se lee como receta top-down) — y aunque ahora se puede
   validar con drift-gate, el retorno de mantenibilidad es marginal. Solo
   hacerlo si una mejora concreta lo exige.

3. **Simplificar la duplicación interna de `_build_optuna_sampler_pruner`**
   (los branches `else` duplican `tpe`/`median`). Es código del path de
   entrenamiento; el valor es estético. Bajo valor.

4. **Reescribir los search scripts** (`run_regret_auditability_sandbox.py`
   2342 LOC, etc.). Son evidencia histórica congelada con tests, no código
   vivo. Refactor = riesgo sin retorno.

5. **Mover los helpers extraídos en R1 a `src/`**. Son orquestación de un
   solo uso. Vivir dentro del script es correcto para single-author
   orchestration; moverlos a `src/` añade indirección sin reuso real.

---

## Secuencia recomendada

1. **Cerrado y verificado (2026-06-13):** A1, A2 fases 1--3, B1, B2.
2. **Ejecutable ya, en rama, con run-tag aprobado:** A2 fase 4 (retiro del pkl),
   mejoras editoriales del paper/libro, cualquier re-derivación coherente. Ver
   "QUÉ HACER AHORA".
3. **Prohibido hasta nueva orden:** freeze de submission y submission (C4).
4. **Lo demás de C (C3 `dvc push`):** cuando DagsHub salga de mantenimiento.

## Gate universal (correr tras cada PR; obligatorio antes de mergear)

```powershell
just lint
just type-check
just smoke
just validate-champion
just drift-gate            # el juez de la cadena del certificado
just dvc-status
```
Si cualquiera da rojo en una lane que NO debía tocar el champion → es un
cambio numérico disfrazado de refactor: revertir y reportar.
