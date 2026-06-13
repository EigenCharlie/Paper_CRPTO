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

---

## LANE A — Refactor estructural seguro (desbloqueado por hallazgo nuevo)

### A1. Split de `src/models/conformal.py` (731 LOC → submódulos)

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
4. **NO borrar el pkl todavía**: `feature_config.pkl` está en
   `EXTRACTION_MANIFEST.json` (es artefacto congelado). Retirarlo del
   manifest y del disco requiere champion-lock approval y un run-tag nuevo.
   Dejar la fase 4 documentada como pendiente de aprobación.

**Criterio de aceptación:** consumidores leen YAML por defecto; equivalencia
testeada; drift-gate verde; pkl intacto en disco y manifest.

**Riesgo:** Medio. Toca la ruta de features que alimenta el champion. El
drift-gate es el juez. Rama dedicada. **Requiere `dvc commit` con patch
mínimo** si cambia algún hash de dep (ver procedimiento en
`docs/refactor/README.md` y el helper de patch mínimo de `dvc.lock`).

**Por qué vale la pena:** elimina la última dependencia de pickle en la ruta
de datos (Bandit B301, portabilidad, inspeccionabilidad para reviewers MRM).

---

## LANE B — Gaps de gobernanza del DAG (requieren champion-lock approval)

> **No ejecutar sin que Carlos apruebe explícitamente.** Estos cambian
> `dvc.lock` de stages protegidos. Documentados en
> `docs/refactor/README.md` → "Smaller deferred items".

### B1. Promover splits y `test_predictions.parquet` a stage outputs
`data/processed/{train,test,calibration}.parquet` (producidos por
`src/data/prepare_dataset.py`) y `test_predictions.parquet` (exportado por
`train_pd_model.py`) son artefactos `.dvc` standalone, no outputs de stage.
Promoverlos a `outs` de `crpto.pd.champion` cierra el DAG pero re-keya el
stage protegido. **Acción:** solo con aprobación; usar `dvc commit` con patch
mínimo, verificar `validate-champion` y `drift-gate` antes/después.

### B2. Unificación estructural de `params.yaml`
`params.yaml` es espejo documental de `configs/crpto_*.yaml` (el valor stale
de learning_rate ya se corrigió). La unificación real (generar `params.yaml`
desde configs o viceversa) elimina el riesgo de desincronización pero toca
las `params:` deps de stages protegidos. **Acción:** solo con aprobación.
El contrato actual lo protege `tests/test_configs/test_params_config_sync.py`.

---

## LANE C — Paper IJDS (ventanas de calendario, ver `IJDS_SUBMISSION_ROADMAP_2026-08-10.md`)

El roadmap del paper tiene 15 tracks y ventanas semanales hasta Ago 10.
Lo que la auditoría de código confirma como **ya cerrado**: teoría formal,
menú de bounds A21 (incluida la fila agnóstica que prueba Markov óptimo),
figuras Type 0, bibliografía completa, números de un solo linaje verificado
al bit. Lo que queda es editorial puro:

### C1. Capitalizar el resultado del bound agnóstico en el body (opcional)
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

### C4. Freeze de submission (Ago 6–10)
QA doble-anonimato (`SCHOLARONE_FINAL_CHECKLIST.md`), recompilación final
`informs4`, conteo de páginas ≤25, metadata sin autor.

---

## LANE D — NO HACER (documentado para evitar churn inútil)

Estas son trampas que parecen mejoras pero no lo son. **No las ejecutes.**

1. **Consolidar `_safe_float`** (aparece en 4 scripts). Verifiqué las 4
   implementaciones: **tienen semántica distinta** —
   `analyze_crpto_evidence` retorna `float | None` y chequea `pd.NA`/`nan`;
   `generate_governance_status._safe_float_value` usa default 0.0;
   `run_comparison` y `validate_conformal_policy` usan default `nan` con
   except distinto. NO son duplicación real; consolidarlas cambiaría
   comportamiento y 2 son deps de stages protegidos. **Dejarlas como están.**

2. **Descomponer más los `main()` de 917/925 LOC** en
   `train_pd_model.py` / `generate_conformal_intervals.py`. Lo que queda es
   el **núcleo numérico irreducible** del pipeline congelado (las ~8 fases
   de cómputo conformal/PD). R1 ya extrajo todo lo seguro (config/replay,
   splits, tuning selection). Más extracción ahí es bajo valor (se lee como
   receta top-down) y riesgo no-cero sobre el certificado. **Parar aquí.**

3. **Simplificar la duplicación interna de `_build_optuna_sampler_pruner`**
   (los branches `else` duplican `tpe`/`median`). Es código del path de
   entrenamiento del champion; el valor es estético y el riesgo es perturbar
   un futuro re-train. **No vale la pena.**

4. **Reescribir los search scripts** (`run_regret_auditability_sandbox.py`
   2342 LOC, etc.). Son evidencia histórica congelada con tests, no código
   vivo. Refactor = riesgo sin retorno.

5. **Mover los helpers extraídos en R1 a `src/`**. Son orquestación de un
   solo uso. Vivir dentro del script es correcto para single-author
   orchestration; moverlos a `src/` añade indirección sin reuso real.

---

## Secuencia recomendada

1. **Ahora (seguro, sin aprobación):** A1 (conformal split — desbloqueado),
   luego A2 fases 1–3 (feature_config lectura YAML). Cada uno en su rama/PR
   con drift-gate como juez.
2. **Editorial en ventanas:** C1–C4 según el roadmap del paper.
3. **Solo con aprobación de Carlos:** B1, B2, A2 fase 4 (retiro del pkl).
   Estos esperan a un run-tag nuevo o champion-lock explícito.

## Gate universal (correr tras cada PR de las lanes A/B)

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
