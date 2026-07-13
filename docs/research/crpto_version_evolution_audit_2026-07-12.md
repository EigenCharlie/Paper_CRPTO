# Auditoria de evolucion cientifica y arquitectonica de CRPTO

**Fecha de corte:** 2026-07-12
**Rama auditada:** `codex/crpto-ijds-exhaustive-audit-2026-07-09`
**Commit activo:** `0cd8e7991dcf7ee2988ff0bbceae0c933519b04c`
**Estado:** diagnostico historico y programa de trabajo; **no** sustituye el
registro activo de claims, el protocolo V4 ni el manifiesto de evidencia.

Las unicas fuentes operativas para claims activos siguen siendo:

1. [`active_claims_2026-07-12.md`](active_claims_2026-07-12.md).
2. [`ijds_binary_geometry_frontier_v4_protocol_2026-07-12.md`](ijds_binary_geometry_frontier_v4_protocol_2026-07-12.md).
3. [`ijds_binary_geometry_frontier_v4_v2_recovery_2026-07-12.md`](ijds_binary_geometry_frontier_v4_v2_recovery_2026-07-12.md).
4. [`../../reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json`](../../reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json).

## 1. Dictamen ejecutivo

La esencia computacional de CRPTO **no murio**. La version activa todavia ejecuta
la cadena

`CatBoost -> Platt -> Mondrian conformal binario -> score de guardrail -> LP mensual -> evaluacion de cartera`.

Lo que murio fue la interpretacion positiva original de esa cadena. Los datos y
la teoria disponibles no permiten afirmar que cobertura conformal marginal
protege la cartera seleccionada, que el guardrail domina una politica point-PD,
que existe un ganador, ni que el certificado Markov historico sea operativo. El
paper cambio de una propuesta de politica ganadora a una auditoria de la interfaz
prediccion--decision. Eso es un cambio grande de contribucion, pero no un paper
sin relacion: el objeto cientifico es el mismo y la version actual explica por
que la lectura original de ese objeto era insegura.

La V4 es la version **mas defendible** construida hasta ahora. No es aun la mejor
submission IJDS alcanzable. Sus principales fortalezas son la higiene temporal,
el universo independiente del outcome, el payoff coherente, la separacion fisica
de outcomes, la especificacion completa de ventanas, la geometria binaria y la
identificacion del comparador. Sus principales debilidades son una sola plataforma,
un learner deliberadamente congelado y antiguo, una familia empirica de nueve
politicas heredada mas que derivada, teoria correcta pero en gran parte elemental,
y una simulacion cuyo componente de decision resulto no vinculante.

El paper positivo de `pool93`/V7 no tiene futuro **tal como estaba escrito**. Su
intuicion si tiene futuro, pero solo si una futura prueba dentro de este mismo
paper establece el claim en la unidad correcta: menus mensuales, labels disponibles
en la fecha de decision, payoff coherente y una garantia calibrada sobre perdida de
decision o seleccion, no inferida de cobertura marginal por prestamo.

## 2. Como se hizo esta auditoria

La auditoria no acepta los memos anteriores como autoridad. Se contrastaron:

- commits, tags, PRs y versiones historicas del QMD;
- codigo que construia el universo, ajustaba intervalos y resolvia el LP;
- manifests y tablas de `pool93`, V6/V7, maturity-safe, comparator audit,
  fixed-taxonomy, V3 y V4;
- el CSV crudo de Lending Club y los scores congelados V4;
- los 21 papers extraidos como vecinos metodologicos/IJDS de mayor proximidad;
- las guias vigentes de IJDS sobre aporte metodologico, decision, anonimato y
  reproducibilidad.

Una reconstruccion exploratoria inicial habia contado 2,249 solves y 11 bases
degeneradas. Ese conteo no era el censo completo y queda corregido por el audit
outcome-free etiquetado. La union tolerante contiene 7,297 pares cap-mes: 2,204
caps nominales unicos mas endpoints de soporte y 2,952 breakpoints propios de
los 15 meses. Hay 2,941 bases primalmente degeneradas, como es esperable en
breakpoints, pero cero costos reducidos no basicos dentro de `1e-7`; el minimo
absoluto es `3.87573e-4`. Las 2,941 bases activadas se resolvieron tambien con
orden de IDs inverso: ninguna fue tie-sensitive y la distancia maxima de
exposicion fue `1.45e-14`. Esto apoya estabilidad determinista en el censo
finito; no demuestra unicidad para cada cap real.

## 3. Cronologia verificable

| Generacion | Commit representativo | Titulo/objeto | Longitud QMD aproximada | Cambio dominante |
|---|---|---|---:|---|
| Bootstrap | `70b5ea7` | Pipeline standalone heredada | sin paper IJDS activo | Importa la arquitectura y los supuestos iniciales |
| Primer IJDS | `1252edd` | *Conformal Robust Predict-Then-Optimize...* | 3,053 palabras | Convierte la pipeline en una contribucion IJDS |
| Rebaseline | `e6a8c9b` | mismo titulo | 8,075 | Amplia evidencia, teoria y governance |
| `pool93` | `5da0849` | mismo titulo | 8,913 | Frontier de 50,010 politicas y narrativa positiva |
| Closeout amplio | `2a9b5e9` | mismo titulo | 9,773 | PDF oficial de 26 paginas; referencias desde p. 22 |
| V6 | `de9a5d6` | *Calibration-Selected Conformal Guardrail...* | 3,370 | Reduce a nueve politicas y selector de calibracion |
| V7 | `f83a0b8` | *Calibration-Selected... Credit Portfolios* | 3,824 | Intenta separar selector noviembre/auditoria diciembre |
| Maturity-safe | `78a64fe`/`ca632cc` | *When Marginal Coverage Meets...* | 3,824--6,144 | Corrige universo, madurez, outcome isolation y payoff |
| Comparator audit | `a88839d` | *Auditing Comparator Stringency...* | 7,026 | Muestra que C0 y C2 cambian la conclusion |
| Temporal V3 | `af952df` | *Auditing Temporal Transport...* | 7,778 | Fija taxonomia y amplia sensibilidad temporal |
| Binary geometry V4 | `0cd8e79` | *Binary Conformal Geometry and Comparator Identification...* | 7,250 | Ocho ventanas completas, teoria binaria y frontier exacto |

La compactacion V6/V7 si elimino demasiada profundidad editorial: el PDF V7 tenia
12 paginas y las referencias empezaban en la pagina 10. Esa perdida fue transitoria.
La entrega actual tiene 28 paginas oficiales, referencias desde la pagina 25, body
de verificacion de 21 paginas y suplemento de 13. Recupero profundidad y sigue
dentro de la regla IJDS de 25 paginas excluyendo referencias.

## 4. Que afirmaba cada familia de versiones

### 4.1 Programa original y `pool93`

La historia causal interna era atractiva:

1. CatBoost estima PD y Platt la calibra.
2. Mondrian conformal construye intervalos.
3. El upper endpoint o una mezcla con PD entra como coeficiente de riesgo.
4. Un LP robusto selecciona cartera.
5. Cobertura y un bound Markov certifican el riesgo financiado.
6. Una frontier elige el mejor balance retorno--proteccion.

Los numeros principales de `pool93` parecian fuertes:

- 276,869 loans OOT;
- 50,010 politicas semanticas deduplicadas;
- 27,508 por encima del piso de retorno y aprobando el grid declarado;
- policy del body: retorno `$184,832.48`, `Gamma_CP=0.162616`,
  `V(0.01)=0.035350`, endpoint/cap Markov `0.345084`;
- una frontera economica por encima de `$223K`;
- replicaciones Prosper y Freddie presentadas como transferencia.

Lo valioso era real: una cadena modular, un score de decision transparente, un LP
auditable, una frontera en vez de un unico numero y una preocupacion explicita por
la diferencia entre prediccion y asignacion. Lo invalido era la inferencia que se
construyo encima.

### 4.2 V6 y V7

V6 reconocio que una busqueda de 50,010 politicas sobre el mismo OOT no podia
sostener una promocion. La reemplazo por nueve reglas redondas y eligio
`linear-005` (`tau=0.17`, `gamma=0.50`) en un bloque de calibracion. V7 intento
fortalecerlo: noviembre de 2017 seleccionaba y diciembre auditaba bajo cap `0.28`.

Resultados preservados:

- 308 loans financiados;
- valor reportado `$179,327.59`;
- default ponderado `0.039375`;
- miscoverage financiado `0.036875`;
- endpoint ponderado `0.258051`;
- point-PD: `$196,369.14`, default `0.118400`, miscoverage `0.041900`;
- bootstrap mensual del valor: `[163,421, 193,552]`.

V6/V7 fueron mejores que `pool93` en seleccion explicita y parsimonia. No
resolvieron el problema porque la independencia era solo local: los endpoints ya
habian aprendido labels de noviembre/diciembre y el universo OOT seguia
condicionado retrospectivamente por el status final.

### 4.3 Reconstruccion maturity-safe

La reconstruccion cambio la unidad de decision de un pool retrospectivo a menus
mensuales disponibles. El primer challenger status-independent produjo:

- cobertura fit: `0.900161`;
- cobertura OOT all-candidate: `0.873965`;
- cobertura financiada: `0.689104`;
- default guardrail `0.301464` frente a point `0.340907`;
- payoff estandarizado `$56,698.18` frente a `$35,152.39` en una comparacion;
- solo siete meses y fuerte cambio 2012--2016.

La aparente mejora positiva no sobrevivio la definicion del comparador. Con el
mismo threshold, el guardrail parecia bajar default pero perder payoff; con un
point cap de igual stringency de desarrollo, el guardrail empeoraba payoff,
default y miscoverage. Este no fue un detalle de reporting: eran dos estimandos
distintos.

### 4.4 Fixed taxonomy y V3

La taxonomia se fijo sin outcomes, se separo del residual calibration y se
retuvieron todas las politicas. La evidencia principal fue negativa:

- cobertura fit cercana a `0.900388`;
- cobertura OOT all-candidate `[0.854714, 0.879647]`;
- bajo C2, 7/9 payoffs peores, 1/9 defaults mayores y 8/9 miscoverages mayores
  en la vista canonica;
- seeds, purpose caps y comparadores cambiaban signos;
- los 27 envelopes policy-by-metric cruzaban cero.

V3 amplio ventanas y timing. Confirmo que la falla de transporte era mas estable
que cualquier direccion de cartera. Ese hallazgo preparo V4, pero dos ventanas
elegidas y grids discretos aun dejaban una critica de specification search.

### 4.5 V4 activa

V4 reemplaza la pregunta "cual politica gana" por dos preguntas identificables:

1. Que hace un intervalo absolute-residual con outcome binario al cambiar la
   prevalencia y transportarse en el tiempo.
2. Que signo de cartera sobrevive una familia de comparadores definida sin
   outcomes.

Objetos activos:

- universo status-independent: 640,543 loans;
- PD development: 17,433; Platt/taxonomia: 14,101; residual pool: 49,007;
- policy development sin outcomes: 94,885;
- OOT primario: 376,890 en 15 meses; 365,339 resueltos y 11,551 unresolved;
- ocho ventanas residuales consecutivas de seis meses;
- CatBoost/Platt primario y logistic/Platt como control de cobertura;
- cinco score strata fijos por learner;
- nueve politicas co-primarias, sin selector;
- presupuesto mensual de `$1M`, purpose cap 25%, LGD 0.45;
- 3,067 caps exactos del frontier point-score.

Resultados activos:

- los ocho upper bounds CatBoost quedan bajo `0.90`; maximo `0.882167`;
- los ocho logistic quedan bajo `0.90`; maximo `0.895654`;
- en stratum 2, prevalencia W7--W8 `0.101703 -> 0.097147`, residual quantile
  `0.888435 -> 0.111801` y width `0.984263 -> 0.207631`;
- W8 stratum-2 OOT coverage `[0.822536, 0.853682]`;
- 1,080 celdas C2, residual maximo `8.33e-17`;
- point-minus-guardrail plug-in objective minimo `-1.46e-10`, cero numerico;
- 216/216 envelopes del soporte amplio `[0.05,0.12]` cruzan cero;
- en soporte de desarrollo `[0.055573,0.099997]`, default cruza en 72/72;
  payoff tiene 21 guardrail-lower y 51 crosses; miscoverage 39 higher y 33
  crosses; en W8 las 27 direcciones cruzan cero.

## 5. Por que las versiones positivas eran invalidas

### 5.1 Menu condicionado por el outcome

El constructor historico filtraba `loan_status` a `Charged Off`, `Default` o
`Fully Paid` antes de formar target y splits. Una consulta independiente al CSV
crudo mostro:

| Cohorte | Rows crudas | Retenidas como resueltas | Retencion |
|---|---:|---:|---:|
| 2018 | 495,242 | 197,178 | 39.81% |
| 2019 | 518,107 | 75,405 | 14.55% |
| 2020 | 146,717 | 4,286 | 2.92% |
| Total | 1,160,066 | 276,869 | **23.87%** |

La cartera historica no decidia entre los loans disponibles en la fecha de
originacion; decidia entre los que anos despues resultaron observables. Eso mezcla
calidad, madurez y censoring, y vuelve imposible interpretar el resultado como
politica ex ante.

### 5.2 Leakage temporal indirecto

La funcion final de seleccion V7 no recibia columns de outcome, pero la etapa de
conformal tuning si recibia labels posteriores:

- panel de tuning historico: 237,584 rows, marzo--diciembre 2017;
- bloque reciente: 178,188, mayo--diciembre;
- fit: 142,550, mayo--noviembre;
- tune: 35,638 = 14,943 noviembre + 20,695 diciembre;
- los widening factors del endpoint se aprendian en ese tune.

Por eso diciembre no era una auditoria independiente. La ausencia de una columna
en el selector no elimina informacion ya incorporada al score.

### 5.3 Payoff optimizado distinto del payoff evaluado

El LP historico usaba `r-p*LGD`. La evaluacion asignaba `r` si no habia default y
`-LGD` si habia default. La esperanza coherente es

`(1-p)r-p*LGD = r-p(r+LGD)`.

La formula vieja omitia `p*r` y sobrevaloraba la asignacion aproximadamente en:

- policy seleccionada: `$17.36K`;
- conformal 75: `$15.79K`;
- point-PD: `$44.01K`.

Los dolares historicos no son comparables con el payoff estandarizado V4 y no
deben recuperarse como resultado activo.

### 5.4 Look-ahead del menu y presupuesto

El LP pooled disponia simultaneamente de loans de 33 meses y un solo presupuesto
de `$1M`. Una politica real no puede reservar ese capital conociendo menus futuros.
V4 resuelve un presupuesto fresco por mes y hace del mes la unidad de decision.

### 5.5 Grupo conformal y concentration mal nombrados

El output historico llamaba `conformal_group` al grade, aunque el Mondrian real
usaba score deciles. La concentration era por `purpose`, no por loan. Ambos
errores parecian semanticos, pero ocultaban que teoria, tabla y solver no hablaban
del mismo objeto.

### 5.6 El bound Markov

La desigualdad determinista historica puede escribirse, para pesos financiados,
como una cota de default por upper endpoints mas miscoverage. El paso probabilista
requeria asumir `E[V_selected] <= alpha`. Split conformal solo daba cobertura
marginal en candidatos exchangeable; no daba esa esperanza para puntos elegidos
y ponderados por el optimizador. Markov era algebraicamente correcto **dada** la
asuncion, pero la asuncion era exactamente el claim que faltaba demostrar.

El bound puede volver a ser cientificamente relevante solo si una construccion
selection-valid o decision-risk-valid controla la perdida en la unidad de menu.
Reinsertarlo ahora aportaria apariencia de teoria, no identificacion.

### 5.7 Seleccion masiva sobre el OOT

`pool93` evaluo decenas de miles de politicas contra outcomes del mismo OOT y
promovio una frontier favorable. Reportar todo el frontier no corrige que las
frases centrales, el punto del body y los pisos se eligieran despues de verlo.
V4 evita esta trampa haciendo todas las ventanas y politicas co-primarias y
prohibiendo un winner.

## 6. Por que tardamos tanto en verlo

No hubo un unico bug oculto. Hubo una secuencia de contratos localmente
plausibles que protegian la respuesta anterior:

1. El filtro resolved-only es convencional en credit scoring; su invalidez se
   vuelve visible cuando el universo es tambien el menu de decision.
2. Un split por `issue_d` parece temporal hasta que se modela cuando el outcome
   se vuelve observable.
3. La leakage no estaba en la funcion auditada, sino upstream en el endpoint.
4. `r-p*LGD` y `(1-p)r-p*LGD` parecen variantes economicas hasta que se exige que
   el objetivo sea exactamente la esperanza del payoff reportado.
5. El teorema Markov declaraba su asuncion; los tests podian verificar algebra y
   aun dejar sin probar el puente selected-set.
6. Cada nueva iteracion optimizaba el contrato vigente. Hashes, drift gates y
   claim-sync hicieron ese contrato mas reproducible, no mas verdadero.
7. La literatura se uso inicialmente para apoyar la integracion ML+CP+OR, no
   para preguntar que garantia exacta exigian los vecinos mas cercanos.
8. Los PRs no tuvieron reviews externos. El PR #97, que promovio V7, tuvo cero
   reviews y cero comentarios; el draft #100 tambien sigue sin review.
9. Compilacion limpia, pagina correcta y cientos de tests se confundieron con
   readiness cientifica.
10. La instruccion de no tocar artefactos protegidos favorecia reproducibilidad
    historica, pero tambien hacia costoso cuestionar su estimando.

El patron de avance fue "mover la auditoria un nivel upstream":

```text
metricas finales
    -> seleccion de policy
    -> disponibilidad de labels
    -> construccion del menu
    -> coherencia del payoff
    -> definicion del comparador
    -> geometria del set binario
    -> completitud de especificaciones
```

No haber empezado con un DAG de informacion, una tabla de estimandos y tests
falsadores explica buena parte del costo. La leccion no es que iterar fue inutil;
es que una pipeline puede ser byte-reproducible y cientificamente mal identificada.

## 7. Que se perdio, que se recupero y que no debe volver

### Debe conservarse

- CatBoost/Platt como score congelado y no como leaderboard.
- Mondrian y el exact rank, ahora con taxonomia fija y objeto binario preciso.
- La interfaz explicita entre score y LP.
- Presupuesto, loan bounds y concentration por purpose auditables.
- Frontier y sensitivity, ahora sobre comparadores declarados sin outcomes.
- DVC, hashes, builders deterministas y separacion freeze/evaluate.
- La intuicion de "precio de proteccion", pero sin confundirlo con superioridad.
- Las replicaciones historicas solo como provenance o fuente de nuevas hipotesis.

### Fue reemplazado correctamente

- pool pooled -> menus mensuales;
- resolved-only -> universe status-independent + sharp unresolved bounds;
- `r-p*LGD` -> `(1-p)r-p*LGD`;
- grade disfrazado de Mondrian -> fixed score strata;
- una policy ganadora -> nueve co-primarias;
- grid arbitrario point cap -> HiGHS basis frontier;
- misma cifra de cap -> C0/C1/C2 + soportes;
- dos ventanas elegidas -> ocho ventanas consecutivas completas;
- "robust" sin objeto -> "risk-aware" y cantidad protegida explicitada.

### No debe recuperarse

- retorno `$184.8K`/`$179.3K` como evidencia activa;
- frontera de 50,010 politicas como prueba de validez;
- Markov certificate sin selected-set control;
- claims Prosper/Freddie de validacion equivalente;
- causalidad, deployment, fair-lending certification o policy winner;
- selected-set coverage inferida de candidate coverage;
- pagina adicional cuyo unico fin sea volver a contar la historia tecnica.

## 8. Arquitectura actual y crecimiento

### 8.1 Crecimiento cuantitativo

| Version | `src` LOC | `scripts` LOC | `tests` LOC | tests aprox. | QMD lines |
|---|---:|---:|---:|---:|---:|
| Bootstrap | 10,606 | 22,233 | 4,838 | 175 | 0 |
| Primer IJDS | 11,528 | 25,855 | 6,578 | 269 | 407 |
| `pool93` | 12,078 | 41,128 | 9,384 | 369 | 1,017 |
| V6 | 13,297 | 48,483 | 13,251 | 494 | 489 |
| V7 | 13,359 | 48,809 | 13,335 | 497 | 543 |
| Maturity-safe | 15,265 | 49,728 | 14,102 | 530 | 543 |
| Fixed taxonomy V2 | 16,473 | 54,055 | 15,571 | 591 | 927 |
| V3 | 17,209 | 55,435 | 15,906 | 602 | 990 |
| V4 | 19,840 | 55,951 | 15,954 | 604 historicos; 661 por conteo actual | 957 |

El crecimiento no significa que el metodo activo sea 3x mas complejo. El package
`src/ijds_audit` tiene ocho modulos y unas 2.6K lineas; contando helpers activos
transitivos, la superficie cientifica ronda 5.2K. La mayor parte de las 56K lineas
de scripts y de las 661 pruebas conserva pipelines historicas, searchers y
contratos de artefactos. Solo siete tests viven en `test_ijds_audit_core.py`; otros
tests activos validan evidencia y publicacion.

### 8.2 Arquitectura activa

```mermaid
flowchart LR
    A["Raw Lending Club CSV"] --> B["outcome_observability"]
    B --> C["prediction: CatBoost/Platt + logistic control"]
    C --> D["binary conformal recipes: 8 windows x taxonomies"]
    D --> E["allocations: 9 guardrails + C0/C1/C2"]
    E --> F["portfolio: HiGHS exact point-cap frontier"]
    F --> G["V4-v1 outcome-free freeze + SHA-256"]
    G --> H["single verified outcome join"]
    H --> I["sharp bounds + comparator envelopes"]
    I --> J["evidence manifest"]
    J --> K["QMD -> generated IJDS TeX -> PDF"]
```

La separacion conceptual es buena. Los puntos de complejidad medidos por Radon
que merecen refactor posterior son:

- `build_outcome_free_portfolios`: D(26);
- `fit_binary_outcome_recipe`: D(23);
- `load_v4_config`: D(22);
- `evaluate_frozen`: C(16);
- `load_design_universe` y basis ranging: C(14);
- `freeze_outcome_free` y `temporal_coverage_audit`: C(12).

No se deben reescribir antes de decidir los nuevos experimentos. Primero se
estabiliza la metodologia; despues se extraen helpers con tests de invariantes.

### 8.3 Dependencias y herramientas

El entorno activo ya usa correctamente:

- `uv` y `uv.lock` para entorno determinista;
- `ruff` para lint/format;
- `mypy` sobre `src`, `scripts` y `tests`;
- `ty` como chequeo rapido y gate full-scope mediante wrapper estable;
- `highspy` directamente, que es necesario para basis ranging y preferible a
  ocultarlo detras de Pyomo en esta parte;
- CatBoost 1.2.x pinneado por reproducibilidad;
- sklearn Pipeline para el control logistico;
- DVC para la capsula outcome-free/evaluated.

El `pyproject.toml` tiene 34 dependencias por defecto, mientras que el camino V4
usa directamente un subconjunto cercano a una docena. `pytest` esta en runtime;
SPO, notebooks, MLOps, search y pipelines historicas comparten el mismo entorno.
El analizador `deptry` no puede usarse sin configuracion porque mapea mal
`scikit-learn -> sklearn` y `pyyaml -> yaml`, pero expuso la necesidad real de
separar perfiles.

Mejoras de bajo riesgo:

1. Definir extras `active`, `repro`, `legacy`, `notebooks` y `dev`; mantener un
   lock completo, pero permitir una instalacion activa pequena.
2. Sacar `pytest` de runtime.
3. Actualizar `api-docs-core`, que aun documenta el champion historico, o retirarlo.
4. Hacer strict mypy explicito para `src.ijds_audit.*` y sus builders.
5. Corregir mojibake `CRPTO â€”` en metadata/comentarios.
6. Separar `just ijds-active-check` de un gate historico completo; no hacer que
   el ciclo diario ejecute 661 tests irrelevantes.
7. Marcar tests y scripts `historical` y excluirlos del package/release activo.

No conviene actualizar CatBoost, HiGHS, sklearn o NumPy dentro del mismo run. Una
actualizacion de libreria es una sensibilidad con nuevo run tag y reconciliacion
numerica, no un refactor invisible.

## 9. Que dicen los vecinos metodologicos

### 9.1 Lo que ya no es novedoso

- Johnstone--Cox y Patel ya conectan conformal sets con robust optimization.
- Sun separa prediction, calibration y contextual optimization.
- Yeh aprende sets decision-aware end-to-end y reporta aplicaciones de portfolio.
- Kiyani da una base decision-theoretic: prediction sets y max-min para agentes
  que optimizan quantiles de utility.
- CROMS selecciona modelos conformales usando decision risk y ofrece variantes
  con guarantees finitas/asintoticas.
- Hegazy demuestra por que elegir entre sets validos rompe coverage y construye
  seleccion estable.
- Zhou--Zhu calibra el frontier miscoverage--regret sobre familias robustas.
- CREDO usa conformal para auditar riesgo/suboptimalidad de decisiones.

Por tanto, "combinar ML, CP y OR" no es contribucion suficiente. Tampoco lo es
usar un midpoint/upper endpoint convencional.

### 9.2 Lo que esos metodos no resuelven automaticamente aqui

- La mayoria supone exchangeability/i.i.d.; no corrige por si sola el gap de
  madurez de 36 meses y el cambio 2012--2016.
- Seleccion valida entre prediction sets no equivale a coverage de los loans
  elegidos y ponderados por un LP acoplado.
- Decision calibration suele tratar una instancia contextual y un outcome; un
  menu mensual completo es la instancia correcta de CRPTO y hay pocos meses
  independientes para calibrarla.
- Un set producto loan-wise puede volverse trivialmente conservador en una
  cartera grande.
- E2E/PICNN/RAC seria una metodologia nueva de gran alcance, no un pequeno
  benchmark plug-and-play.

### 9.3 Que aprende CRPTO de IJDS

Los articulos IJDS mas proximos exigen una distincion precisa entre estimando y
decision (Fernandez-Loria--Provost), robustez sobre una familia declarada
(Morucci; Falconer), calibracion ligada a costo y seleccion separada (Yang--Bi),
una contribucion metodologica reproducible (Das; Chen) y una conexion AI--OR que
aporte mas que yuxtaponer herramientas (Wiberg et al.).

V4 se parece especialmente a Morucci: una eleccion del analista aparentemente
inocua puede revertir una conclusion y debe envolverse sobre el conjunto de
alternativas admisibles. La analogia es fuerte, pero CRPTO debe justificar por
que sus soportes de cap son "razonablemente buenos" y no solo convenientes.

Las guias vigentes de IJDS piden datos, metodologia/algoritmo innovador,
motivacion de decision e implicaciones, ademas de capsula reproducible. Una
auditoria negativa puede encajar, pero el framework de identificacion debe verse
como el metodo, no como una lista de errores de un proyecto anterior.

## 10. Ventajas y riesgos de la V4

### Ventajas defendibles

1. Formula con precision el objeto conformal: intervalo residual del outcome
   binario, no confidence interval de PD latente.
2. El information set es verificable y outcomes estan ausentes antes del freeze.
3. La falla de coverage aparece en ocho ventanas y dos learners.
4. La fase binaria explica un mecanismo discontinuo que width promedio oculta.
5. C0/C1/C2 separan mecanica, desarrollo y descomposicion contemporanea.
6. El frontier evita que un cap discreto elegido sostenga la narrativa.
7. Bounds comunes para unresolved outcomes son sharp para las asignaciones fijas.
8. El paper declara explicitamente lo que no identifica.

### Riesgos que siguen abiertos

1. **Novedad:** cinco proposiciones son utiles pero relativamente elementales;
   el valor debe estar en el framework conjunto y el algoritmo exacto.
2. **Single archive:** no hay una segunda aplicacion equivalente.
3. **Frozen-score stress:** el gap largo hace la falla creible, pero un reviewer
   puede preguntar si una actualizacion maturity-aware la corrige.
4. **Familia de policy:** el censo outcome-free confirma que las nueve reglas
   heredadas son factibles y casi siempre decision-active, pero tambien que
   `gamma=1` es factible y activo en 624/624 celdas. Omitir ese endpoint sin una
   justificacion semantica dejaria incompleta la familia; falta comparar una
   parametrizacion outcome-free de stringencia normalizada.
5. **Soporte de comparador:** los roles C0/C1/C2 y los endpoints de desarrollo
   ya tienen un censo exacto de actividad, pero development y broad stress
   siguen siendo soportes declarados, no universalmente canonicos. El intervalo
   `[.05,.12]` cruza deliberadamente de caps activos a slack y no debe leerse
   como dominio normativo.
6. **Simulation:** 19,200 repeticiones apoyan coverage, pero el cap de portfolio
   casi nunca liga; no puede sostener el claim de decision.
7. **Solver tie boundary:** queda cerrado para el censo finito evaluado. En
   7,297 pares cap-mes hubo 2,941 bases primalmente degeneradas, pero ningun
   nonbasic reduced cost dentro de `1e-7` de cero y ninguna de las 2,941
   reruns con orden de ID invertido cambio la asignacion mas de `1.45e-14`.
   Esto no es un teorema de unicidad para todo cap real.
8. **Retrospectivo:** no queda lockbox empirico pristino; cualquier run nuevo debe
   llamarse specification-complete retrospective, nunca confirmatory.
9. **Payoff:** es coherente pero deliberadamente simple; no es IRR/NPV/cash flow.
10. **Complejidad de repo:** el reviewer capsule no debe exponer 100 scripts
    historicos como si fueran necesarios para V4.

## 11. La esencia de CRPTO y el futuro del paper positivo

Hay tres posibles significados de "esencia":

1. **Pipeline:** ML + calibracion + conformal + optimization. Sobrevive completa.
2. **Hipotesis:** incertidumbre predictiva puede cambiar decisiones de credito y
   su evaluacion debe unir estadistica y OR. Sobrevive y es mas fuerte.
3. **Promesa:** el upper conformal produce una cartera robusta superior con un
   bound transferible. Esa promesa no sobrevivio.

Por eso V4 no es CRPTO V2 ni otro paper desconectado. Es la version en la que
CRPTO deja de asumir que el puente funciona y lo convierte en objeto de estudio.
El costo editorial es perder una historia de triunfo; la ganancia cientifica es
tener una historia que puede defenderse.

Una version positiva solo debe entrar en el mismo paper si supera un gate
predeclarado en la unidad mensual:

- universo y menus independientes de status;
- todos los labels de fit disponibles en la fecha de decision;
- score/conformal/selector sin outcomes futuros;
- payoff optimizado igual al evaluado;
- calibracion de decision o seleccion cuya garantia aplique al menu/acccion;
- evaluacion en todos los origenes y especificaciones declarados;
- unresolved outcomes conservados y bounded;
- comparador support fijado antes del outcome join;
- ningun winner si el signo no es estable.

Si una reparacion cumple eso, el paper puede ser "audit + repair" y recuperar una
contribucion positiva. Si no, la V4 negativa sigue siendo el resultado. No se
debe forzar CROMS, RAC, CRC o E2E solo para recuperar un headline: ninguno resuelve
automaticamente madurez, shift y seleccion acoplada.

## 12. Como medir progreso real desde ahora

Un commit o una nueva version cuenta como avance cientifico solo si mejora al
menos una de estas dimensiones sin empeorar silenciosamente otra:

| Dimension | Metrica de progreso | Falla que previene |
|---|---|---|
| Estimando | claim tiene unidad, tiempo, comparator y payoff | comparar objetos distintos |
| Informacion | DAG no permite path de outcome futuro | leakage indirecto |
| Especificacion | se reporta toda familia declarada | cherry-picking |
| Identificacion | signo sobrevive soporte o se declara no identificado | winner artificial |
| Validez | guarantee corresponde a candidate/selected/menu | transportar coverage |
| Reproducibilidad | raw-to-evidence desde clone limpio | hashes sin reconstruccion |
| Parsimonia | active LOC/deps/tests disminuyen o se justifican | acumulacion historica |
| Novedad | diferencia explicita frente a 5 vecinos mas cercanos | integracion no novedosa |
| Falsabilidad | cada claim tiene una prueba que podria hacerlo caer | tests confirmatorios |
| Revision | red-team independiente antes de readiness | consenso de agentes correlacionados |

El numero de tests no es una metrica de avance. Los tests correctos son los que
protegen invariantes cientificas: disponibilidad temporal, ausencia de outcomes,
alineacion de IDs, payoff identity, exact ranks, full budget, C2 feasibility,
sharp bounds, hashes y claim boundaries.

## 13. Programa de mejora antes del freeze

No hay freeze autorizado. El siguiente programa esta ordenado por valor
cientifico, no por facilidad.

### P0. Cerrar riesgos de la contribucion activa

1. **Rolling-origin maturity-lag audit.** Predeclarar varios decision origins y,
   en cada uno, ajustar/recalibrar usando solo terminal labels observables. Reportar
   coverage como funcion de staleness y separar "CP falla" de "score congelado
   por madurez falla". Stop si no hay suficientes cohorts/meses con retencion
   outcome-safe.
2. **Simulacion decision-nondegenerate.** Construir un DGP analitico donde risk cap
   y purpose/segment constraint liguen por diseno. Validar fase binaria, nesting,
   C2 y comparator reversal con truth conocido. Reportar todos los cells aunque
   contradigan V4.
3. **Justificar o completar policy family.** Derivar `tau/gamma` desde factibilidad
   y binding ranges outcome-free. Incluir extremos semanticos necesarios o
   demostrar por que no pertenecen al estimando.
4. **Tie/degeneracy audit persistido.** Verificar nonbasic reduced costs y resolver
   lexicographic perturbations en named caps y basis breakpoints. Si hay multiples
   optima, envolver realised contrasts o declarar la tie rule.
5. **Formalizar admissible comparator support.** Explicitar el criterio que hace
   un cap admisible y distinguir identificacion condicional al soporte de
   robustez universal.

### P1. Decidir si cabe una reparacion positiva

6. Construir una tabla de aplicabilidad para Hegazy, CROMS, RAC, inverse CRC y
   E2E: unidad de exchangeability, outcome, accion, garantia, datos requeridos y
   costo computacional.
7. Elegir **como maximo una** reparacion si su garantia puede formularse a nivel
   de menu mensual. No elegirla por el resultado historico.
8. Definir antes de correr: estimando, family completa, split, stop rules y
   criterio de promocion. La reparacion entra al mismo paper tanto si gana como
   si falla.
9. Si ninguna metodologia cercana aplica sin nuevas asunciones fuertes, no
   implementarla; convertir esa imposibilidad en una limitacion precisa.

### P1. Fortalecer el paper IJDS

10. Reorganizar la introduccion alrededor de una contribucion metodologica:
    information-safe decision audit + exact comparator identification + binary
    mechanism. La historia del proyecto no pertenece al body.
11. Integrar CROMS, Kiyani/RAC y inverse CRC en closest-work, explicando la
    diferencia de unidad de decision; no solo listarlos.
12. Mantener el body en 24 paginas antes de referencias. Cualquier experimento
    nuevo desplaza detalle, no lo apila; proofs/tablas extensas van al supplement.
13. Reemplazar cualquier lenguaje de "robust" sin perturbacion/cantidad por
    coverage transport, risk-aware constraint o comparator robustness.
14. Hacer una revision externa o verdaderamente independiente con el claim
    registry oculto al primer lector, para evitar que simplemente confirme el
    contrato actual.

### P2. Simplificar el codigo y la capsula

15. Crear un inventory machine-readable de archivos active, publication,
    protected-historical y removable-historical.
16. Mover tests historicos a un marker/gate separado; conservar el gate del
    manifest, pero no ejecutarlo en cada iteracion V4.
17. Separar extras de dependencias y generar un clean environment V4.
18. Hacer strict typing del package activo; mantener `ty` rapido y mypy como
    verificacion complementaria, no duplicar excepciones por herramienta.
19. Refactorizar solo las siete funciones C/D despues de fijar P0/P1, preservando
    hashes de evidencia mediante run tag nuevo cuando corresponda.
20. Retirar del HEAD scripts/configs sin consumidores activos despues de crear un
    tag/branch historico y comprobar que el clone limpio V4 reproduce todo.

## 14. Condiciones para volver a hablar de freeze

No se debe proponer freeze mientras ocurra cualquiera de estas condiciones:

- rolling-origin o simulation P0 no se ha ejecutado o se decidio omitir sin
  justificacion editorial;
- policy family y comparator support siguen siendo solo heredados;
- una reparacion positiva usa una garantia en la unidad equivocada;
- hay un claim de decision apoyado solo por candidate coverage;
- el active capsule necesita scripts historicos no declarados;
- no existe una revision cientifica independiente de primera ronda;
- paper, supplement, TeX y evidence manifest no comparten un unico claim ledger;
- el resultado depende de escoger una ventana, policy, learner o comparator
  despues de outcomes.

La siguiente decision no es "freeze o no freeze". Es si los P0 producen una
contribucion mas fuerte que V4 sin reintroducir selection. Solo despues de esa
evidencia se elige entre:

- **V4+**: auditoria negativa fortalecida por rolling origins y simulacion;
- **audit + una reparacion**: si existe control decision-valid aplicable;
- **no submission IJDS**: si el framework no alcanza novedad/metodo suficiente.

Hoy la opcion con mayor probabilidad y menor riesgo cientifico es **V4+**. Mantiene
la esencia ML--conformal--optimization, explica por que el puente puede fallar y
convierte las decisiones de comparador, madurez y outcome geometry en el aporte,
sin prometer una politica que los datos no identifican.

## 15. Actualizacion de ejecucion P0: rolling origins

El primer P0 ya fue ejecutado bajo un protocolo etiquetado y un erratum tambien
etiquetado. No modifica todavia el registro activo de claims.

- El origen 2015 fallo antes del outcome join: la primera ventana CatBoost tuvo
  conteos Mondrian `(1648, 1408, 1166, 927, 619)` y los dos ultimos grupos no
  alcanzaron el minimo bloqueado de 1,000. El umbral no se relajo.
- El origen 2016 se restringio mecanicamente a abril--junio: 74,537 candidatos,
  todos resueltos. Los ocho coverages CatBoost fueron 0.860861--0.874626 y los
  logisticos 0.868629--0.888619.
- El origen 2017 completo freeze y evaluacion: 77,105 candidatos, 66,217
  resueltos y 10,888 no resueltos. Los bounds superiores fueron como maximo
  0.876247 para CatBoost y 0.877401 para logistic.
- Los 32 bounds superiores de los dos origenes factibles quedaron bajo 0.90.
  Esto es recurrencia en dos origenes, no estabilidad de tres origenes, porque
  2015 no fue factible bajo el mismo estimando.
- Ningun scope/metric tuvo una sola direccion no nula en sus 72 celdas en 2016
  o 2017. La dependencia del comparador se mantuvo y no reaparecio un ganador.
- C2 conservo reconciliacion numerica menor que `6e-17` y dominancia plugin en
  las 216 celdas de cada origen factible.
- La simulacion heredada fue exactamente la misma en ambos runs: solo 2 de
  19,200 repeticiones cambiaron la asignacion same-cap y solo 1 cambio C2; el
  cap del guardrail fue slack en todas. No ofrece evidencia de cartera.

La evidencia, tablas y memo reproducibles estan en
`reports/crpto/ijds_rolling_origin_stability_evidence.json` y
`docs/research/ijds_rolling_origin_stability_results_2026-07-12.md`. El siguiente
P0 real es reemplazar la simulacion degenerada por un mecanismo predeclarado en
el que la restriccion cambie decisiones sin escoger resultados favorables.

## 16. Actualizacion de ejecucion P0: simulacion decision-active

El segundo P0 se predeclaro en el commit `acbe65e` y el tag
`protocol/ijds-decision-active-simulation-2026-07-12-v1`. Las 72 celdas usan 50
bloques aleatorios pareados, para 3,600 repeticiones. Los outcomes se generan
despues de fijar guardrail, C0 y C2; ningun signo selecciona una celda.

- Los 3,600 caps guardrail ligaron. El slack absoluto maximo fue `4.44e-16`, el
  residual de presupuesto `1.42e-14` y el residual C2 `1.67e-16`.
- C0 cambio las 3,600 asignaciones. Su cap numerico aplicado a point PD deja
  slack medio positivo en 11 de 12 celdas outcome-free agregadas; sigue siendo
  un control de nesting, no un baseline neutral.
- C2 cambio 1,866 asignaciones. Solo 66 de 1,800 cambiaron con un estrato, pero
  las 1,800 cambiaron con cinco estratos. La taxonomia altera el orden del score
  efectivo; matching de un solo momento no elimina esa geometria.
- Sin shift, coverage medio fue 0.900767 con un estrato y 0.900617 con cinco.
  Un shift de calibracion log-odds de 1.5 lo redujo a 0.696717 y 0.735733.
- Con score shift 0.08 y sin calibration shift, cinco estratos dieron coverage
  0.909667, pero con width medio 0.919819 y set `{0,1}` en 39.11% de candidatos.
  Coverage sin informativeness seria una lectura incompleta.
- Payoff, default y miscoverage revirtieron direccion entre celdas. Con 15% de
  censoring, la mayoria de bounds C2 cruzaron cero. No se permite transportar
  un signo sintetico al archivo Lending Club.

La simulacion V4 original permanece como procedencia negativa, pero ya no es el
mejor experimento de mecanismo para decisiones. El nuevo run demuestra que el
cap activo, la taxonomia y la semantica C0/C2 son mecanismos separados de
candidate coverage. La evidencia aun no modifica
`active_claims_2026-07-12.md`: la decision editorial se toma despues de cerrar
family support y solver ties.

Fuentes reproducibles:

- `reports/crpto/ijds_decision_active_simulation_evidence.json`;
- `docs/research/ijds_decision_active_simulation_results_2026-07-12.md`;
- tablas `crpto_ijds_decision_active_*` en `reports/crpto/tables`.

## 17. Actualizacion de ejecucion P1: soporte de policy y empates

El protocolo se fijo en el commit `115eaf1` y el tag
`protocol/ijds-policy-support-tie-audit-2026-07-12-v1`. El runner uso solo ID,
monto, tasa contractual, proposito, rol temporal, point score y recetas
conformales congeladas. Ningun outcome entro en los 3,120 solves de familia ni
en el censo de caps.

- Las 1,872 celdas heredadas fueron factibles y 1,846 fueron decision-active.
  Las 26 slack aparecen solo en `gamma=.25`, ventana W8.
- El endpoint `gamma=0` fue objective-slack en 624/624 celdas bajo los tres
  `tau`; confirma su funcion de control point-score, no de policy robusta.
- El endpoint `gamma=1` fue factible y decision-active en 624/624 celdas. Con
  el mismo menu y cap, su objetivo plug-in fue menor que `gamma=.75` en las
  624 celdas: diferencia media `-2519.44`, rango
  `[-8337.85,-579.98]` dolares de objetivo plug-in por presupuesto mensual de
  USD 1 millon.
- La union tolerante del frontier contiene 7,297 pares cap-mes: 2,204 caps
  nominales unicos y 2,952 breakpoints period-specific, ademas de endpoints de
  soporte. Los 45 C0 fueron slack; C1 tuvo 1,079 activos y uno slack; C2 tuvo
  1,075 activos y cuatro en la frontera del objetivo.
- Hubo 2,941 bases primalmente degeneradas, principalmente en breakpoints. El
  minimo reduced cost no basico absoluto fue `3.876e-4`; no hubo near-zero
  dual alternatives al umbral `1e-7`. Invertir el orden de ID no produjo una
  sola asignacion tie-sensitive.

El hallazgo elimina una explicacion espuria: los cambios de direccion V4 no son
un artefacto de empates numericos en los caps auditados. A la vez, invalida la
idea de que la grilla interior heredada sea automaticamente una familia
completa. El siguiente challenger debe fijar antes de outcomes una stringencia
normalizada
`lambda=(q_cap-q_min)/(q_obj-q_min)` e incluir `gamma={0,.25,.5,.75,1}`. Ese
diseno compara posiciones homologas entre el portfolio de menor score y el
portfolio sin cap; no convierte `lambda` en una tolerancia de riesgo
desplegable y debe conservar esa limitacion.

Fuentes reproducibles:

- `reports/crpto/ijds_policy_support_tie_evidence.json`;
- `docs/research/ijds_policy_support_tie_results_2026-07-12.md`;
- tablas `crpto_ijds_policy_family_domain.csv`,
  `crpto_ijds_gamma_endpoint_audit.csv` y
  `crpto_ijds_comparator_support_domain.csv`.

## 18. Cierre metodologico P1 antes del challenger normalizado

La revision de los metodos vecinos cambia la pregunta, pero no autoriza una
garantia nueva. La unidad estadistica relevante de CRPTO es el menu mensual
completo, su vector de outcomes y la asignacion acoplada por presupuesto y
proposito. Los 376,890 prestamos OOT no son 376,890 decisiones independientes:
hay 15 menus OOT y solo 11 menus comunes de desarrollo. CROMS, RAC, conformal
robustness control, decision-calibrated sets, CREME/inverse CRC, CREDO y los
metodos end-to-end requieren contextos de decision exchangeable, una secuencia
operativa suficiente o una ley generativa que este archivo no identifica. Su
software podria ejecutarse, pero su teorema no se transportaria.

El P1 no adopta por ello una supuesta reparacion conformal. Predeclara un
challenger de identificacion con dos reglas outcome-free:

1. La regla primaria iguala un piso absoluto de objetivo plug-in y minimiza
   cada score en el soporte comun eficiente.
2. La regla secundaria usa la posicion normalizada entre el portfolio de score
   minimo y el portfolio sin cap. Es invariante a transformaciones afines
   positivas, pero no iguala riesgo verdadero ni costo de oportunidad.

La familia ahora incluye `gamma={0,.25,.50,.75,1}` y tres coordenadas en ambas
reglas. El freeze V1 contiene exactamente 6,240 solves outcome-free; el unico
contraste primario futuro es `gamma=1 - gamma=0`. Los gammas interiores son una
ruta diagnostica completa, no candidatos para escoger un winner.

El contrato fue fijado antes del join de outcomes. Un smoke estructural en W1,
abril de 2016, reprodujo rangos de score de `0.078139`, `0.216985`, `0.355830`,
`0.494675` y `0.633521`; HiGHS y GLOP reconciliaron hasta `5.82e-17`. Estos son
chequeos de escala y formulacion, no resultados empiricos. El runner se aislo
en `src/ijds_challengers` y su constructor central se redujo de complejidad
ciclomatica D28 a C20 sin tocar V4 ni un outcome.

La promocion exige un freeze V1 hash-verificado y un V2 separado. Si cualquier
bound sharp cruza cero o las reglas, ventanas o coordenadas discrepan, el
resultado fortalece la auditoria de dependencia del comparador. Solo un signo
no nulo comun a las ocho ventanas, tres coordenadas y dos reglas habilitaria un
challenger rolling-origin adicional; aun asi no repararia candidate coverage
ni funded-set validity. No hay freeze de submission autorizado.

Contratos completos:

- `docs/research/ijds_decision_method_applicability_2026-07-12.md`;
- `docs/research/ijds_normalized_objective_frontier_protocol_2026-07-12.md`;
- `configs/experiments/ijds_normalized_objective_frontier_2026-07-12_v1.yaml`.

## 19. Stop V1 y correccion outcome-free V1b

V1 se ejecuto desde el tag bloqueado y se detuvo despues de 3,514.5 segundos,
antes de outcomes y sin crear directorios de salida. La celda W8, abril de 2017,
`gamma=.25` produjo un span de score `3.49719776749e-08` al permitir un deterioro
de objetivo de USD `1e-7`, por encima del stop `1e-8`.

La auditoria posterior, todavia outcome-free, mostro que no era una cara optima
alternativa. El minimo reduced cost no basico fue `0.004653`, no hubo reduced
costs cercanos a cero ni degeneracion primal, y el orden inverso reprodujo la
asignacion. El proxy V1 confundia el score que podia comprarse con una pequena
holgura de objetivo y un empate exacto. El tag V1 no se modifico ni su umbral se
relajo.

V1b reemplaza ese proxy por reduced costs de la base optima y orden inverso una
vez por menu. El smoke de los 26 menus dio cero near-zero reduced costs, cero
bases primalmente degeneradas, distancia maxima `9.09e-19` y drift de objetivo
`1.16e-10` dolares. Como el optimo plug-in no depende de gamma ni ventana, la
correccion tambien elimina miles de LP redundantes sin cambiar los 6,240 solves
de las dos reglas. V1b requiere commit, tag y run tag nuevos; todavia no modifica
claims ni autoriza outcomes o freeze de submission.

Trazabilidad:

- `docs/research/ijds_normalized_objective_frontier_v1_stop_2026-07-13.md`;
- `docs/research/ijds_normalized_objective_frontier_v1b_protocol_2026-07-13.md`;
- `configs/experiments/ijds_normalized_objective_frontier_2026-07-13_v1b.yaml`.

## 20. Stop V1b y alineacion de tolerancia V1c

V1b completo las ocho ventanas en memoria, pero se detuvo antes de escribir
outputs porque el residual maximo de presupuesto fue USD `6.366e-6`, superior
al stop final USD `1e-6`. Los dos wrappers LP ya aceptaban hasta USD `1e-4`, de
modo que el protocolo tenia dos definiciones incompatibles de factibilidad
numerica. El residual observado equivale a aproximadamente `6.4e-12` del
presupuesto mensual.

V1c fija el chequeo final en USD `1e-4`, exactamente el umbral interno existente
y `1e-10` del presupuesto. No redondea, reescala ni modifica una asignacion; no
cambia LPs, grids, endpoints, outcomes o claims. V1b permanece fallido bajo su
propio tag y V1c recibe config, commit, tag y directorios nuevos. Esta es otra
correccion outcome-free y no una adaptacion a resultados empiricos.

Trazabilidad:

- `docs/research/ijds_normalized_objective_frontier_v1b_stop_2026-07-13.md`;
- `docs/research/ijds_normalized_objective_frontier_v1c_protocol_2026-07-13.md`;
- `configs/experiments/ijds_normalized_objective_frontier_2026-07-13_v1c.yaml`.

## 21. Freeze outcome-free V1c

V1c completo en 3,332 segundos: 6,240 solves, 622,455 exposiciones positivas,
720 contrastes endpoint, 1,440 reruns por orden, 288 validaciones GLOP y 26
diagnosticos de base. El residual maximo de presupuesto fue USD `6.366e-6`; el
desacuerdo maximo GLOP--HiGHS fue `2.179e-13` en tasa de objetivo y `3.594e-13`
en score financiado. No hubo near-zero reduced costs, bases degeneradas ni un
ruler globalmente degenerado.

La geometria resuelve una duda y cierra otra ruta positiva. El ruler normalizado
cambio 360/360 endpoints. El ruler objective-matched cambio 272/360: en
coordenada `.25`, 88/120 pares `gamma=1` versus `gamma=0` fueron exactamente
identicos. Esas celdas tienen contraste mensual cero bajo cualquier outcome,
pero no fuerzan a cero el agregado de 15 meses: cada una de las ocho ventanas
conserva exactamente cuatro meses no identicos en `.25`. V1c por si solo no
establece ni descarta un signo agregado comun. No se permite retirar `.25`,
seleccionar `.50`/`.75` ni reportar solo los cuatro meses activos.

V2 sigue siendo necesario para cuantificar signos y bounds sharp en las celdas
no identicas y para medir discrepancia entre rulers. El hallazgo fortalece la
narrativa de identificacion del handoff ML--conformal--OR, no una politica
winner. Fuentes: `docs/research/ijds_normalized_objective_frontier_v1c_results_2026-07-13.md`
y los punteros DVC V1c.
