# Drift report — revalidación conformal MAPIE 1.x (Track B, gate B1)

**Fecha**: 2026-06-09 (gate rojo) / **2026-06-10 (RESUELTO: gate VERDE)**
**Harness**: `tests/test_models/test_conformal_mapie_drift.py` (opt-in vía
`CRPTO_RUN_CHAMPION_DRIFT=1`)

## RESOLUCIÓN 2026-06-10 — gate VERDE con drift CERO

El binario de abril (`models/search_pd/pd-hpo-local-2026-04-03-1325/`,
modelo + calibrador + baselines) fue recuperado y el harness, apuntando a la
receta literal del pkl congelado, dio **drift 0.000e+00 en todas las
columnas** (y_pred, endpoints 90/95, edges de bandas, cobertura por celda) y
reprodujo exactamente los multiplicadores de piso `{score_q01: 1.05,
score_q04: 1.02}`. La cadena conformal congelada es **bit-exact
reproducible bajo el stack actual** (MAPIE 1.4 runtime, numpy/catboost/
sklearn de hoy); la migración MAPIE queda revalidada de facto.

Con aprobación explícita de Carlos se ejecutó la **unificación de linaje**
(camino 1 + corrección de identidad): `models/pd_canonical.cbm` y
`models/pd_canonical_calibrator.pkl` son ahora copias byte a byte del
candidato de abril, y `data/processed/test_predictions.parquet` se
reconstruyó desde ese bundle con
`scripts/rebuild_test_predictions_from_frozen.py` (assert duro: pd_calibrated
== y_pred congelado, diff máx 0.0). Métricas PD del paper actualizadas:
AUC 0.7127→0.7139, Brier 0.1546→0.1544, ECE 0.0062→0.0070; el certificado
($170,464.54, V=0.028875, Γ_CP=0.187987, 45/45) **no cambia**. Manifest:
bloque `april_lineage_unification` + 14 hashes re-freezados.

Hallazgo adicional documentado durante la unificación: la "identidad
candidato↔canónico" **nunca existió** (el pd_canonical de abril en el
proyecto de origen ya era un tercer re-entrenamiento, AUC 0.7124; CatBoost
con el mismo config no es bit-reproducible entre corridas). Además, las
tablas A7/A8 (funded set por préstamo) provienen de un re-solve LP
degenerado y **no se regeneran**: quedan congeladas como la vista oficial
del certificado (341 préstamos, Tabla 7 del paper). A5/A9/A10 (experimentos
derivados de re-solve, independientes del linaje PD) se re-freezaron bajo el
stack lockeado actual para que un revisor pueda regenerarlas.

---

## Registro histórico del gate rojo (2026-06-09)

**Resultado del gate**: **ROJO — STOP Track B** según el criterio de
`MAPIE_MIGRATION_PLAN.md` ("si el drift excede tolerancia, es un cambio de
modelo, no un refactor").

## Qué se midió

El harness recomputa en memoria los intervalos conformal del champion desde
la receta congelada en `models/conformal_results_mondrian.pkl` (partición
`score_decile_mondrian`, prob source raw, `n_score_bins=5`, fallback
`grade_then_global`, `alpha_90=0.1`, `alpha_95=0.05`, escala
`bernoulli_sqrt`, `min_group_size=100`, split de calibración 80/20 temporal
con seed 42, multiplicadores de piso `{score_q01: 1.05, score_q04: 1.02}`) y
compara contra `data/processed/conformal_intervals_mondrian.parquet`.

Tolerancias del plan: `1e-6` por préstamo en endpoints; `5e-4` de cobertura
por celda Mondrian.

## Resultado

| Columna | max abs diff | Tolerancia | Estado |
| --- | --- | --- | --- |
| `y_pred` | 2.107e-01 | 1e-6 | FALLA |
| `pd_low_90` | 4.007e-01 | 1e-6 | FALLA |
| `pd_high_90` | 8.244e-01 | 1e-6 | FALLA |
| `pd_low_95` | 4.043e-01 | 1e-6 | FALLA |
| `pd_high_95` | 2.921e-01 | 1e-6 | FALLA |
| edges de bandas de score | 5.805e-03 | 1e-6 | FALLA |
| cobertura por celda (peor: `score_q02`) | 2.728e-02 | 5e-4 | FALLA |
| etiquetas de partición drifteadas | 30,961 / 276,869 | 0 | FALLA |
| multiplicadores de piso re-aprendidos | `{q00:1.05, q01:1.05, q02:1.08, q03:1.05, q04:1.02}` vs congelado `{q01:1.05, q04:1.02}` | igualdad | FALLA |

Checks estructurales que SÍ pasan: tamaños del split de calibración
fit/holdout exactos vs el pkl; 5 grupos sin fallback; `id` y `y_true`
posicionalmente idénticos al parquet congelado (misma data, mismo orden).

## Atribución de causa raíz

El drift **no proviene de MAPIE ni de la capa conformal** (la ruta Mondrian
del champion usa cuantiles numpy puros, sin clases MAPIE). La causa está
aguas arriba, en la identidad del modelo:

- El pkl congelado registra `model_path =
  models/search_pd/pd-hpo-local-2026-04-03-1325/pd_candidate_model.cbm`: los
  intervalos congelados se generaron en abril con el candidato del search
  (no presente en el checkout local).
- `models/pd_canonical.cbm` es el re-entrenamiento de la rebaseline
  `ijds-rebaseline-2026-06-07` con el mismo config (`crpto_pd_model.yaml`,
  trial 56). El re-entrenamiento no fue bit-exact respecto del candidato de
  abril: correlación de `y_pred` 0.9917, mediana de |diff| 9.5e-3, p99
  5.9e-2, max 2.1e-1.
- Con predicciones distintas, los edges de deciles, las etiquetas de
  partición (11.2 % de filas cambian de celda), los cuantiles por celda y
  los multiplicadores de piso re-aprendidos difieren en cascada.

## Implicaciones

1. **La cadena computacional end-to-end no es reproducible** desde los
   artefactos canónicos: `pd_canonical.cbm` (junio) no regenera
   `conformal_intervals_mondrian.parquet` (abril). El diseño replay-mode de
   `crpto.conformal.intervals` es lo que mantiene la consistencia del
   pipeline: restaura bytes, no recomputa.
2. **El claim de reproducibilidad del paper se sostiene tal como está
   redactado** ("paper-facing reruns consume frozen artifacts"), pero un
   revisor que intente recomputar los intervalos desde el modelo canónico
   obtendrá números distintos. Conviene que el reproducibility package sea
   explícito en que la regeneración es por replay de artefactos congelados.
3. **Misma familia de causa raíz que el drift de hardening** detectado el
   2026-06-09 en `crpto_tableA5/A7–A10` (re-solves con el stack y modelo
   actuales vs tablas committeadas pre-rebaseline): la rebaseline de junio
   re-entrenó el PD canónico sin regenerar todas las superficies derivadas.

## Decisiones según el plan

- **B2 (migración MAPIE + split de `conformal.py`)**: NO se ejecuta. Sin un
  gate verde no hay forma de demostrar que el split/migración preserva la
  cadena congelada.
- **B3 (feature_config → Parquet)**: NO se ejecuta en esta ventana (el
  track completo queda detenido; es aditivo pero comparte la precondición
  de un gate verde para validar consumidores).
- El harness queda en el repo como gate permanente (opt-in por variable de
  entorno) para la próxima ventana de re-promoción.

## Caminos de resolución (decisión de Carlos, post-submission o run-tag nuevo)

1. **Restaurar el binario de abril**: `dvc pull` (o recuperar del remote) de
   `models/search_pd/pd-hpo-local-2026-04-03-1325/` y apuntar el harness al
   `model_path` del pkl. Si el gate pasa con el candidato de abril, la
   receta es íntegra y solo la identidad canonical↔candidato queda como
   nota de gobernanza.
2. **Re-promoción completa**: nuevo run-tag que re-entrene PD, regenere
   intervalos, re-valide policy y re-freezee manifest + tablas derivadas
   (incluye resolver el drift de hardening A5/A7–A10 de una vez).
3. **Documentar y seguir**: mantener replay-mode como única vía oficial de
   reproducción y reflejarlo en el data/code disclosure del journal.
