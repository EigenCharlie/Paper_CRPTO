# CRPTO Parent Intake Register - 2026-05-29

Este registro cierra el barrido final del proyecto padre hacia `Paper_CRPTO`.
La decisión editorial es mantener CRPTO autocontenido para tesis/IJDS: traer
evidencia liviana y texto curado, no copiar el laboratorio completo ni reabrir el
champion.

## Qué se importó

Los CSVs estáticos quedaron en `reports/crpto/appendix/`, separados de
`reports/crpto/tables/` para no mezclarlos con la superficie canónica generada
por scripts.

| Archivo local | Rol |
|---|---|
| `reports/crpto/appendix/crpto_appendix_paper1_bound_pareto_decision_summary_2026-05-25.csv` | Ledger de decisiones Pareto y lectura de challengers. |
| `reports/crpto/appendix/crpto_appendix_paper1_return_aware_rerank_summary_2026-05-25.csv` | Señal `canonical_4_return_aware`: más retorno, peor `V` y `Gamma_CP`. |
| `reports/crpto/appendix/crpto_appendix_paper1_conformal_reopen_candidate_gap_diagnostics_2026-05-25.csv` | Diagnóstico conformal de candidatos y comparación contra el champion oficial. |
| `reports/crpto/appendix/crpto_appendix_paper1_bound_improvement_pd_intake_2026-05-21.csv` | Intake PD de challengers `bureau_behavior_15`, `canonical_4` y `affordability_rate_5`. |
| `reports/crpto/appendix/crpto_appendix_paper1_bound_improvement_conformal_group_diagnostics_2026-05-21.csv` | Diagnóstico de cobertura por grade, incluyendo la debilidad de grade E. |

También se incorporó como prosa curada:

- la evidence card IFRS9/SICR (`t*=0.30`, recall `75.8%`, ECL proxy `+22%`);
- el cierre PyEPO/SPO del 2026-05-28 (`48.51%`, `0.184366` vs `0.358073`,
  Wilcoxon `p = 3.80e-163`);
- la síntesis de challengers como resultados negativos o señales de protocolo
  futuro, no como candidatos promovidos.

## Qué se excluyó

No se copiaron modelos, datos procesados, logs, snapshots, run directories,
configs de búsqueda, RAPIDS/cuOpt, workflows, notebooks completos, Streamlit,
FastAPI, GPU, quantum, survival, causal/CATE, IFRS9 completo, MDCP/DLA ni
CVaR/OCE como objetivo oficial.

Tampoco se copió `paper1_raw_vs_exact_rerank_diagnostics_2026-05-25.csv`. Ese
archivo solo tendría sentido si se pidiera una auditoría exhaustiva del rerank;
para IJDS/tesis basta el resumen curado.

## Señales de posible búsqueda futura

Estas señales no reabren el champion. Solo indican qué valdría la pena convertir
en protocolo sellado si más adelante Carlos decide buscar un reemplazo.

| Señal | Lectura |
|---|---|
| `canonical_4_return_aware` | Exact pass y retorno `+$146.80` sobre el champion, pero peor `V=0.058675` y `Gamma_CP=0.270366`. Interesante solo para una búsqueda return-aware declarada antes de mirar resultados. |
| `canonical_4__phase1__portfolio` | Retorno alto en búsqueda temprana, pero `V=0.07055`, `Gamma_CP=0.517574` y cobertura débil. Negativo útil contra perseguir retorno sin robustez. |
| `bureau_behavior_15` | Mejora AUC/Brier, pero empeora ECE y deja debilidad conformal en grade E. Señal predictiva, no reemplazo de stack completo. |
| `affordability_rate_5` | Alternativa viable como sensibilidad, pero no domina retorno/robustez del champion. |

## Por qué no se reabre el champion

El champion congelado sigue siendo `bound_aware_276k_economic_champion`, con
retorno robusto `$170,464.54`, `V=0.03645`, `Gamma_CP=0.18591`, exact pass
`True` y región robusta `45/45`. Ningún ledger importado mejora simultáneamente
retorno, `V`, `Gamma_CP`, cobertura y gobernanza bajo el protocolo actual.

Reabrir el champion exigiría un protocolo nuevo, declarado antes de cualquier
búsqueda: split/holdout, gates, tolerancias, anti-cherry-pick, destino de tablas
y criterio de promoción. Este intake no autoriza esa búsqueda.
