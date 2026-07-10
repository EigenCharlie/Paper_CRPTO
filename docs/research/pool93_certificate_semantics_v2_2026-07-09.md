# Auditoria consolidada del certificado pool93 v2 - 2026-07-09

## Decision

Se promueve la semantica `certificate-semantics-v2` como fuente activa para
A35, la gobernanza pool93 y el baseline A40. No cambia el modelo PD, calibrador,
intervalos conformales, asignacion seleccionada, retorno del body, grilla alpha
ni denominadores. Corrige la lectura del endpoint para policies no lineales y
reemplaza el comparador Lending Club mal rotulado por una baseline point-PD
emparejada.

Tag activo:

`champion-reopen-2026-06-19__pool93__ijds-certificate-semantics-v2`

## Hallazgo 1: descomposicion policy-aware

La formula historica

`B_u = tau + (1 - gamma) * Gamma_CP`

es exacta solo para un blend lineal cuyo cap efectivo liga. La frontera tambien
contiene policies `capped`, `tail` y `segment_relative_tail`; en ellas `gamma`
no basta para reconstruir el endpoint.

Para cualquier score efectivo declarado `q_i` con
`p_hat_i <= q_i <= u_i`, la identidad general es:

```text
Gamma_CP  = sum_i w_i (u_i - p_hat_i)
Gamma_int = sum_i w_i (q_i - p_hat_i)
Gamma_res = sum_i w_i (u_i - q_i)
Gamma_CP  = Gamma_int + Gamma_res
B_u       = sum_i w_i q_i + Gamma_res
B_u       <= tau + solver_slack + Gamma_res
T_Markov  = B_u + sqrt(alpha)
```

`T_Markov` es un umbral de evento probabilistico bajo weighted funded-set
validity; no es un cap determinista. El campo historico `violation` mide exceso
realizado de default sobre `tau`, no violacion de la identidad
`sum(wY) <= B_u + V`.

## Punto seleccionado

En `alpha=0.01`, la asignacion seleccionada conserva:

| Cantidad | Valor |
|---|---:|
| Retorno realizado | `$184,832.48` |
| Filas financiadas | `314` |
| `V` / default ponderado | `0.035350` |
| PD puntual ponderada | `0.082468` |
| Score efectivo ponderado | `0.171500` |
| `Gamma_CP` | `0.162616` |
| `Gamma_int` | `0.089032` |
| `Gamma_res` | `0.073584` |
| Endpoint exacto `B_u` | `0.245084` |
| Umbral Markov exacto | `0.345084` |
| Exceso realizado sobre `tau` | `0.000000` |
| Pass grilla alpha | `8/8` |

El cap row-level de la policy `capped_blended_uncertainty` esta inactivo en las
314 filas financiadas. Por eso la formula lineal coincide numericamente en este
punto, aunque no sea valida como formula universal de la frontera.

## Auditoria de A35 sin nueva busqueda

La reconstruccion lee las estadisticas suficientes de seis evaluaciones exactas
ya existentes. No ejecuta HPO, busqueda de policy, generacion conformal ni solve
de portafolio.

- filas crudas: `51,678`;
- policies semanticas deduplicadas: `50,010`;
- policies elegibles all-alpha y sobre floor: `27,508`;
- seleccion del body: sin cambio;
- thresholds con cambio material: `10,423`;
- policies tail con understatement: `2,866`;
- understatement maximo: `0.241324`;
- antiguas filas `<=0.50` que exceden `0.50` exacto: `716`.

Los modos afectados son `tail_blended_uncertainty` y
`segment_relative_tail_blended_uncertainty`. El endpoint de maximo retorno sigue
ganando `$223,458.14`, pero su endpoint es `0.597056` y su umbral Markov exacto
es `0.697056`. El body y todos los denominadores permanecen iguales.

## Hallazgo 2: baseline point-PD A40

El campo historico `price_of_robustness=-10.56%` comparaba contra un solve
rotulado `nonrobust` que aun heredaba una restriccion `pd_high`. Una
recomputacion preliminar a `tau=0.175` sirvio para detectar el problema, pero no
era el contraste final del body y se retira como superficie activa.

A40 resuelve el contraste correcto con:

- los mismos `276,869` candidatos;
- presupuesto `$1M`;
- misma concentracion, `tau=0.1715`, LGD, solver y controles operativos;
- point PD en objetivo y restriccion como unica diferencia semantica;
- outcomes OOT usados solo despues del solve.

| Policy | Retorno | Funded | Default / `V` | `Gamma_CP` | `B_u` | Threshold |
|---|---:|---:|---:|---:|---:|---:|
| Point-PD two-stage LP | `$196,369.14` | `225` | `0.118400` | `0.526736` | `0.680579` | `0.780579` |
| CRPTO seleccionado | `$184,832.48` | `314` | `0.035350` | `0.162616` | `0.245084` | `0.345084` |

CRPTO cede `$11,536.66` (`5.875%`) y reduce default/miscoverage en `0.08305`
(8.305 puntos porcentuales) y el threshold en `0.435495` (43.55 puntos). Ambos
funded sets quedan debajo de `tau`; solo CRPTO pasa el screen tight
`V <= sqrt(0.01)`.

## Limite del claim

A40 es una auditoria emparejada sobre un OOT historico congelado. No demuestra
causalidad, significancia prospectiva ni dominancia universal. A35 es una
frontera de grilla finita, no un optimo continuo. La probabilidad del teorema
requiere weighted funded-set validity; el draw observado audita `V` pero no
prueba por si solo ese supuesto.

## Artefactos promovidos

- `reports/crpto/tables/crpto_tableA35_pool93_ijds_frontier.csv`
- `reports/crpto/tables/crpto_tableA35_pool93_ijds_frontier.tex`
- `reports/crpto/tables/crpto_tableA40_pool93_point_baseline.csv`
- `reports/crpto/tables/crpto_tableA40_pool93_point_baseline.tex`
- `models/experiments/champion_reopen/...__ijds-certificate-semantics-v2/portfolio/pool93_ijds_consolidated_frontier.json`
- `models/experiments/champion_reopen/...__ijds-certificate-semantics-v2/portfolio/pool93_ijds_consolidated_governance.json`
- `models/experiments/champion_reopen/...__ijds-certificate-semantics-v2/portfolio/pool93_point_pd_baseline_audit.json`

Las filas financiadas de A40 viven bajo `data/processed/experiments/`, no en el
directorio de modelos. Los artefactos antiguos se conservan como provenance,
pero no son fuentes de claims activos.
