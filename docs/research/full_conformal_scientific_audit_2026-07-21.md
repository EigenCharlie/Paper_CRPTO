# Auditoría científica integral de CRPTO y conformal prediction

## Veredicto ejecutivo

CRPTO es defendible y más interesante como **auditoría de una interfaz
predictor--optimizador bajo identificación parcial** que como propuesta de una
política crediticia conformalmente válida. El procedimiento score-Mondrian
split conformal es correcto para construir conjuntos candidatos sobre el
resultado binario observado, con la taxonomía congelada, el estadístico de
orden ascendente y el caso `k=n+1` tratado como umbral infinito. Lo que el
archivo no permite sostener es transporte temporal, cobertura de préstamos
financiados, una garantía seleccionada o una mejora causal/económica de la
asignación.

La contribución más sólida combina cuatro resultados:

1. los 40 límites superiores de cobertura sobre el archivo finito quedan por
   debajo de 0.90 aun después de completar cada endpoint no resuelto de la
   manera más favorable;
2. el diagnóstico de rangos combinados coloca 31/40 bloques learner--window
   más allá de umbrales nominales bloqueados, pero prueba un null conjunto más
   fuerte que la condición conformal de un solo punto futuro y no conserva una
   interpretación FWER posterior a la inspección;
3. Label-Mondrian mejora cobertura de defaults en el panel resuelto a costa de
   conjuntos mucho más ambiguos y no repara uniformemente la cobertura del
   archivo; y
4. ninguna dirección de payoff, default o miscoverage sobrevive a todos los
   rulers, coordenadas, soportes y supuestos estructurales declarados.

Por tanto, no conviene reemplazar ahora el método primario por APS/RAPS,
Venn--Abers, weighted conformal, ACI o una técnica selected-set. Esas técnicas
responden a otros estimandos o requieren ratios de densidad, feedback rápido,
selección simétrica o datos contrafactuales que este archivo no identifica.
Sí conviene presentarlas como protocolos futuros claramente separados.

## Alcance y trazabilidad de la auditoría

La revisión cubrió código científico, protocolos, registros de claims,
evidencia activa, manuscrito, suplemento, tablas, figuras, DVC y superficies de
reproducibilidad. El corpus local inventariado contiene 120 PDFs y 4.636 páginas.
La frontera contiene 22 objetos PDF correspondientes a 21 trabajos (770
páginas; un artículo tiene suplemento separado), además del paper fundacional
de CatBoost (11 páginas). Todos se
extrajeron con el pipeline académico y se auditaron por teorema, estimando,
endpoint y posibilidad real de transferencia a CRPTO.

También se leyó completo *Applied Conformal Prediction* (168 páginas; SHA-256
`5340A494E689427264A8E67389F11AD332569A19E5CB0E9205198016DD9D506F`). Su
auditoría detallada está en
`docs/research/applied_conformal_prediction_book_audit_2026-07-21.md`; el
inventario y decisión sobre cada paper están en
`docs/research/conformal_literature_corpus_audit_2026-07-21.md`.

El libro sirve para intuición e implementación, no como autoridad formal. Entre
sus errores materiales están: llamar *k-th largest* al estadístico que su propia
notación ordena de forma ascendente; derivar uniformidad de rango desde
marginales idénticas en vez de exchangeability conjunta; tratar una cobertura
empírica como necesariamente superior al nominal; confundir conjuntos
conformales con probabilidades calibradas; sobreafirmar Venn--Abers y reparación
condicional; convertir 50--100 observaciones por grupo en una supuesta condición
de validez; y usar una corrida o figura como confirmación de un teorema.

La búsqueda dirigida añadió seis trabajos que cerraban huecos reales del
primer corpus: Candès--Lei--Ren y Gui et al. para censura Type-I, una propuesta
IPCW/AIPCW de Farina et al. para censura ordinaria, una propuesta de Alberge et
al. sobre calibración de riesgos competitivos, Gazin et al. para conjuntos del
vector batch y Barber--Pananjady para procesos estacionarios beta-mixing.
Ninguno es un reemplazo válido del pipeline activo. Además, Farina y Alberge
quedaron en cuarentena: la versión aceptada de Farina contiene orientaciones de
score invertidas y pasos de prueba inválidos, y el teorema de equivalencia
central de Alberge admite contraejemplos junto con errores de multiplicidad y
recalibración. Los cuatro trabajos restantes cambian el estimando o exigen
tiempos de evento/censura, independencia condicional, positividad, nuisance
models, estacionariedad, coeficientes de dependencia o labels batch observados.
La disposición correcta es usar sólo las fuentes que sobrevivieron para hacer
explícita la frontera y diseñar un estudio futuro, sin importar sus garantías
al label binario ni al funded set.

## Auditoría conceptual y metodológica

### 1. Objeto conformal

Para `Y in {0,1}` y score de default `p`, la igualdad
`1-p_hat_y(x)=|y-p|` es correcta. El conjunto

`S(x)={y in {0,1}: |y-p| <= c_g}`

es el objeto conformal canónico. El intervalo recortado `[max(0,p-c),
min(1,p+c)]` tiene el mismo evento de cobertura para `Y` binario, pero es una
**representación continua de diseño** usada por el LP, no un intervalo de
confianza para la PD individual. Esta distinción debe mantenerse en cada
superficie.

La regla de rango correcta es
`ceil((n_g+1)(1-alpha))` sobre scores ordenados ascendentemente, con umbral
infinito si el índice es `n_g+1`. El código y las pruebas activas ya contienen
esta convención.

### 2. Qué significa la cobertura observada

Un límite superior sharp inferior a 0.90 es un hecho determinista del archivo
finito bajo todas las completaciones binarias de endpoints faltantes. No es por
sí solo una prueba de significancia ni una refutación del teorema split
conformal. La terminología correcta es *finite-archive shortfall* y *sharp
completion bound*, no *the conformal guarantee failed*.

El diagnóstico Beta--Binomial cuenta misses estrictos usando rangos combinados.
Su ley exacta requiere que calibración y **todo el bloque target** sean
exchangeable conjuntamente dentro de estrato. Esta condición es más fuerte que
exchangeability entre calibración y un punto futuro; por ello un flag puede
reflejar dependencia u heterogeneidad target--target. Además, el patrón fue
inspeccionado antes del lock V1: Bonferroni y Holm son umbrales nominales
congelados, no control post-selection o study-wide de FWER. Los nueve nonflags
no validan transporte.

Tampoco es una región predictiva conjunta del vector de 376.890 labels. Los
métodos batch válidos invierten hipótesis para cada vector candidato y devuelven
un conjunto vectorial bajo contratos iid o class-conditional; nuestro
estadístico sólo referencia retrospectivamente un conteo de misses. Esa
distinción evita confundir un diagnóstico del bloque con joint batch coverage.

### 3. Conditional, group y label coverage

El score-Mondrian primario busca cobertura por estrato de score, no por clase.
La comparación de cobertura entre defaults y nondefaults resueltos es
descriptiva y está condicionada por resolución administrativa. No puede
llamarse label-conditional validity.

El benchmark Label-Mondrian implementado usa un umbral distinto para cada
label candidato dentro de cada estrato. En el panel resuelto mejora la cobertura
de defaults; en el archivo completo, 27/40
upper endpoints siguen debajo de 0.90, 12 cruzan y uno queda enteramente en o
por encima de nominal; AvgC sube a 1.724--1.785 y los conjuntos `{0,1}` a
72.37%--78.55%. Todos los gaps agregados cruzan cero, pero 88/200 gaps por
estrato excluyen cero. Es una redistribución descriptiva costosa de cobertura y
cardinalidad; no es una reparación de transporte o validez, prueba de
exchangeability dentro de categoría ni recomendación automática de despliegue.

### 4. Tiempo, madurez y endpoint

La fecha de issue solo identifica el mes. El seguimiento individual a 39 meses
desde fin de issue-month es por tanto una igualación de edad administrativa por
mes, no por día exacto. Aun así, sus dos orígenes conservan los ocho upper
endpoints debajo de 0.90: máximo 0.879120 en abril--junio 2016 y 0.875261 en
abril--junio 2017. Esto elimina el artefacto del cutoff trimestral común, pero
no convierte dos orígenes de una misma cronología en replicaciones.

La literatura beta-mixing reciente tampoco permite añadir una penalidad
numérica post hoc: su bound requiere una secuencia estacionaria predefinida y
coeficientes de mezcla o switch conocidos o acotados. La recurrencia entre dos
orígenes, PSI y los flags de rango no estiman esos objetos.

La sensibilidad completa al lag del endpoint y las cuatro completaciones de
labels de fitting deben permanecer separadas: una mantiene scores y
allocations congelados; la otra vuelve a ajustar modelos no lineales. No forman
un factorial conjunto ni límites sharp de todas las posibles asignaciones.

### 5. Selección y decisión

Candidate-level marginal o groupwise coverage no se transporta automáticamente
al conjunto financiado por un LP acoplado al presupuesto. JOMI, FCR e
informative-set methods muestran rutas futuras, pero exigen definir el evento
de selección, su simetría, reference sets y/o el error seleccionado. CRPTO no
implementa esos contratos y debe conservar explícitamente “no selected- or
funded-set coverage claim”.

El archivo contiene solo préstamos aceptados y no identifica outcomes de
rechazados ni efectos de financiar. Tampoco soporta una lectura
counterfactual/action-conditional. Los contrastes son históricos entre
asignaciones simuladas sobre outcomes observados, no treatment effects.

### 6. Economía y optimización

El coeficiente `(1-p)r-p*LGD` y el endpoint `(1-Y)r-Y*LGD` forman una pareja
coherente como **proxy estandarizado**, pero la tasa anual y un label terminal
de 36 meses no comparten escala de cash flow. No debe llamarse profit, NPV,
IRR, welfare o true expected return. Multiplicar todas las tasas por `k>0` es,
tras reescalar positivamente el objetivo, equivalente a usar `LGD/k`; por ello
el grid LGD ya cubre una sensibilidad de escala relativa sin requerir un run
redundante.

Los dos rulers miden cosas distintas. Objective matching iguala costo de
oportunidad model-implied; normalized score iguala relajación relativa e
invariante a transformaciones afines positivas, pero deja variar el objetivo
plug-in. Ninguno es neutral ni seleccionable por el signo observado. Los
envelopes sobre outcomes no resueltos deben usar una única completación por loan
compartida entre políticas; restar intervalos marginales sería no sharp.

El cierre del certificado LP de base completa y posibles caras óptimas se
registra en la sección “Cierre de optimización” al final de este documento.

## Evidencia nueva incorporada

| Frente | Diseño | Resultado que sí se puede sostener | Lo que no demuestra |
|---|---|---|---|
| Set geometry | 5 learners x 8 windows | 40/40 upper endpoints sharp debajo de 0.90 | Falla del teorema o causalidad del drift |
| Joint-block ranks | 40 intersecciones de 5 estratos | 31/40 cruzan umbrales nominales bloqueados | FWER post-selection o invalidez one-point |
| Label-Mondrian | 40 agregados, 200 estratos, 400 label-strata | Mejora resolved-panel default coverage con gran aumento de ambigüedad | Reparación uniforme o within-label exchangeability |
| Taxonomías cerradas | 2 learners x 4 taxonomías x 8 windows | 64/64 upper endpoints debajo de 0.90; máximo 0.897294 | Selección de taxonomía o extensión del test joint-block |
| Extensión censurada | Regla +6 meses; 2 learners x 8 windows, 28.936/88.227 no resueltos | CatBoost 8/8 debajo; logistic 2/8 debajo, con máximo 0.908928 | Evidencia OOT primaria, replicación o winner |
| Missingness | sentinel, indicator, native null | 8/8 debajo de nominal en las tres codificaciones | Identificación del mecanismo de missingness |
| Edad individual | dos orígenes, seis cutoffs mensuales | 16/16 debajo de nominal | Replicación independiente o edad exacta por día |
| Fit labels | cuatro completaciones | 32/32 debajo de nominal | Bound sharp sobre `2^215` completaciones |
| Endpoint lag | cinco lags administrativos | resultado 40/40 es específico del contrato; a 12 meses queda 39/40 | Selección retrospectiva del lag de seis meses |
| Portfolio structure | 36 escenarios | no aparece dirección universal | Robustez a todo modelo económico o estructura |
| Basis-derived point-cap support | 7.297 caps centrales + 196 midpoint seeds, 15 meses | cobertura numérica de `[0.05,0.12]` a `1e-10`; cero diferencias laterales materiales | Exactitud simbólica, unicidad, continuidad o enumeración de toda la cara óptima |

## Qué agregar, cambiar y quitar

### Agregar o conservar ahora

- Mantener el resultado de cobertura del archivo separado del diagnóstico
  joint-block y de las sensibilidades deterministas.
- Mantener Label-Mondrian como benchmark completo, incluyendo cardinalidad,
  empty/full sets y gaps sharp con completación común.
- Mantener el seguimiento por edad individual y relegar el cutoff trimestral
  común a provenance/replay.
- Mantener dos rulers y, condicionado al cierre V2, el soporte derivado por
  bases; son parte del estimando, no checks secundarios intercambiables.
- Mantener los cinco learners solo como coverage controls; CatBoost primario es
  el único que entra al LP y no hay winner OOT.
- Citar fuentes primarias para validez marginal, límites condicionales,
  nonexchangeability, classwise coverage y selección; usar el libro solo como
  material pedagógico.
- Citar el paper fundacional de CatBoost para identificar el algoritmo, sin
  convertir esa cita en una afirmación de superioridad o transporte.
- Conservar la matriz extensa de closest work en el suplemento y el cuerpo
  concentrado en la frontera de validez.

### Cambiar o vigilar

- Usar *meets/crosses locked nominal threshold*, no *rejects*, *significant* o
  *incompatible with conformal validity*.
- Usar *status-indexed standardized payoff proxy* y *model-implied plug-in
  objective*, no *profit* ni *expected return* sin calificador.
- Calificar siempre “all 40” con el endpoint administrativo de seis meses y la
  población finita declarada.
- No sumar votes entre ventanas solapadas, learners o sensibilidades con grids
  distintos.
- No seleccionar gamma, ruler, coordinate, support, learner, encoding, lag o
  escenario por el resultado.
- Mantener la auditoría de página oficial: 25 páginas antes de References; el
  preview HTML/PDF no sustituye el PDF LaTeX oficial.

### Quitar o no incorporar

- No presentar el upper interval score como PD conservadora o upper confidence
  bound de riesgo individual.
- No afirmar cobertura de financiados, singleton-selected coverage, ECL, SICR,
  causalidad, fairness o autorización de despliegue.
- No introducir APS/RAPS/SAPS: en binario añaden complejidad sin resolver el
  transporte temporal o la selección.
- No usar Venn--Abers como “reparación” de conformal coverage; su objeto es
  probabilístico y su validez no es una garantía para cualquier subset.
- No aplicar ACI sin un diseño secuencial con feedback compatible con el delay
  crediticio.
- No aplicar weighted CP/CRC sin demostrar covariate/posterior-shift structure,
  overlap y pesos controlados.
- No citar como soporte activo los papers en cuarentena `p08`, `p09` o `p15`,
  cuyos problemas de endpoint, theorem-to-estimator o teoría-algoritmo fueron
  documentados en la auditoría del corpus.
- Añadir `p18` y `p19` a esa cuarentena: el primero tiene fórmulas de región y
  pasos de prueba no válidos; el segundo una equivalencia falsa y
  recalibraciones que no preservan el vector CIF. Sus temas sí son relevantes,
  pero sus garantías impresas no deben entrar al manuscrito.

## Trabajo futuro que sí podría cambiar la conclusión

1. Una validación externa prospectiva con snapshots point-in-time, outcomes de
   rejected applicants cuando sean identificables y un endpoint de competing
   risks/survival con prepayment y cash flows.
2. Un protocolo temporal predeclarado que estime explícitamente las penalidades
   de dependencia o discrepancia de un resultado nonexchangeable, en vez de
   llamar robusta a la recurrencia empírica.
3. Una arquitectura selected-set para el LP exacto: evento de selección,
   reference set, simetría y objetivo FCR/JOMI definidos antes de outcomes.
4. Un modelo source--target con supuestos testables de overlap e invariancia
   antes de introducir weighting.
5. Una función económica de flujos descontados y competing events; sería un
   nuevo paper/estimando, no una corrección cosmética del proxy actual.
6. Una sensibilidad *set-native* para el handoff al LP. El score continuo
   `u=min(1,p+c)` es una representación de diseño no canónica: fuera del evento
   de pertenencia binaria no hereda una magnitud probabilística o conformal.
   Un protocolo futuro podría comparar una transformación basada directamente
   en el peor label admisible (con convención explícita para conjuntos vacíos)
   o calibrar pérdida de decisión sobre contextos completos. No debe agregarse
   post hoc con los once menús y labels tardíos disponibles.
7. Un rediseño de riesgos competitivos, sólo con fechas exactas y snapshots
   point-in-time, debería separar default, payoff/prepayment y censura
   administrativa; auditar `C perp (T,J) | X`, positividad, colas de pesos y
   ESS; exigir CIFs coherentes; y reportar calibration-in-the-large, slope/ICI,
   Brier/IBS multicause con IPCW válido, AUC/C-index por causa y OOT temporal.
   Esas métricas no pueden calcularse honestamente a partir del endpoint
   terminal coarsened actual.

## Cierre de optimización

El V2 inmutable fresh-solved las 7.297 combinaciones mes--cap, auditó todas las
variables estructurales y de holgura, reconcilió 7.297/7.297 asignaciones contra
el freeze y ejecutó 5.874 probes bilaterales. La interpretación inicial de
`row_bound_dn/up` era incorrecta para 69 filas de riesgo `basic`: en HiGHS esos
registros describen actividad de la variable de fila, no el intervalo del RHS
inactivo. Las 69 tienen multiplicador exactamente cero, por lo que el mismo
certificado primal--dual sostiene el rayo seguro desde actividad actual hasta
el upper bound del dominio. Esa corrección elimina 66 falsas fallas de
contención, pero deja 196 huecos reales entre witnesses centrales.

El predecesor V3 completó los 196 solves y falló después, antes de escribir
outputs, por un `KeyError` en el adaptador de reporte lateral. El tag quedó
inmutable. V3a declaró esa falla, añadió las dos tolerancias V2 omitidas y
re-solved los 196 midpoints en sesiones frescas. Pasan 196/196 auditorías de
base, signos duales, objetivo, factibilidad, contención y cobertura del hueco.
La unión final cubre numéricamente `[0.05,0.12]` en 15/15 meses a tolerancia
`1e-10`, con cero gaps; a tolerancia cero quedan 465 seams de redondeo de ancho
máximo `1.67e-16`, por lo que no se afirma exactitud simbólica.

Las rutas bilaterales muestran cero diferencias materiales de asignación
(máximo `3.08e-14`) y cero coocurrencias corregidas, no siete. Sin embargo, los
13 warnings scale-aware de V2 en ocho targets y un warning midpoint adicional
mantienen bloqueada la unicidad numérica. Todos los reduced costs conservan el
signo correcto; el mayor movimiento epsilon-near-optimal de una exposición es
USD `0.962`. Esto no demuestra un óptimo exacto alternativo ni autoriza sumar
rangos coordenados, inferir un diámetro global, continuidad de asignación,
seam conditioning o unicidad de la frontera conjunta.

## Estado de validación

La reconciliación independiente de V3a pasó sin P0/P1/P2: hashes, schemas,
counts, summary, receipt, tag y commit coinciden; V2 y sus diez artefactos
siguen byte-idénticos. El evidence intermedio se reconstruyó de forma
determinista en 17.110 bytes y SHA-256
`29c8aeff29e10618aab1965fb7e754bf3ef23c990d89d736afac3e3bc7b6cb62`;
el manifiesto principal se regeneró después con SHA-256
`ccdf19ddcea92c15fafc2a6a5b83e2acd5faaf87d6324311377b86857d96464b`
y pasó todos sus contratos. Una reconstrucción consecutiva dejó ambos hashes
idénticos.

El cierre de repositorio pasó `just lint`, `just type-check`,
`just type-check-fast`, `just test`, `just validate-champion`,
`just ijds-active-check`, `just publication-integrity`, `just drift-gate` y
`just submission-check`. La suite global contiene 538 tests. El gate estricto
descubrió 41 incompatibilidades de tipado que el checker ordinario no veía;
se corrigieron con vistas tipadas/casts sobre objetos dinámicos de pandas,
SciPy y HiGHS, sin cambiar fórmulas, solver, protocolos ni outputs. Ambos
checkers quedaron limpios sobre 172 archivos fuente.

El PDF oficial tiene 28 páginas y `References` comienza en la 26: son
exactamente 25 páginas pre-referencias. El abstract tiene 294 palabras y un
solo párrafo. El preview del cuerpo tiene 19 páginas y el suplemento 33; los
tres son US Letter, no tienen páginas vacías, fingerprint hits, identity hits
ni tamaños anómalos. Se renderizaron e inspeccionaron visualmente las 80 páginas
(28 + 19 + 33), además de páginas críticas a resolución completa: no se
observaron recortes, solapamientos, tablas fuera de margen, fórmulas ilegibles
o referencias rotas.

La cápsula activa contiene 51 punteros DVC. El estado local estaba actualizado;
la auditoría remota encontró 62 objetos activos aún no publicados —incluidos
V2/V3a y runs recientes Mondrian, exchangeability y rolling-origin—, todos se
subieron al remoto `dagshub`. `verify-remote` pasó y el estado final reporta
cache y remoto sincronizados. `EXTRACTION_MANIFEST.json` permanece intacto y
ningún artefacto histórico protegido fue reescrito.
