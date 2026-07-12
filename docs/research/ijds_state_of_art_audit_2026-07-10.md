# Auditoría del estado del arte y del encaje IJDS de CRPTO

> **Current boundary (2026-07-11):** this is a literature and historical
> diagnosis, not a claim registry. The active fixed-taxonomy comparator audit
> is governed by `active_claims_2026-07-12.md`; earlier variants remain Git-only
> provenance.

**Fecha de auditoría:** 2026-07-10
**Corte de literatura:** inclusivo hasta 2026-07-09
**Corpus local:** `Papers_tesis` (97 PDF) y, por separado, los tres PDF activos de CRPTO
**Inventario fila a fila:** `docs/research/literature_corpus_inventory_2026-07-10.csv`

## Conclusión ejecutiva

La versión activa no está lista para someterse a *INFORMS Journal on Data
Science* (IJDS). La decisión no depende de estilo ni de una exigencia de
sofisticación adicional: cuatro defectos alteran el estimando, la información
disponible al decidir o la política óptima.

1. El universo candidato se filtra *ex post* a préstamos resueltos. La fracción
   retenida cae de 39,81% en 2018 a 2,92% en 2020, de modo que la comparación
   temporal mezcla riesgo con madurez/censura y la optimización recibe una lista
   que ningún inversor habría conocido en originación.
2. Los resultados de noviembre y diciembre de 2017 entran indirectamente en la
   receta conformal mediante factores de ensanchamiento aprendidos con
   `y_true`. Por ello, ni la selección de noviembre ni la auditoría de diciembre
   son independientes, aunque la tabla que recibe el selector no contenga una
   columna de resultados.
3. La función objetivo usa `r - pL`, pero el pago que luego se evalúa es
   `(1-Y)r - YL`. La esperanza coherente de ese pago es
   `r - p(r+L)`. Corregirlo cambia los coeficientes relativos y exige
   reoptimizar; no basta con cambiar una etiqueta o una cifra en el texto.
4. Una sola cartera de USD 1 millón selecciona simultáneamente préstamos de 33
   meses (enero de 2018 a septiembre de 2020). Eso usa el menú futuro. No es una
   política implementable en tiempo real ni una evaluación rolling-origin.

La literatura reciente refuerza, no relaja, estos reparos. El frente 2024--2026
calibra pérdidas de decisión, trata explícitamente la selección entre recetas,
separa datos para restaurar validez y estudia deriva/no intercambiabilidad. En
IJDS, los artículos más próximos vinculan el objetivo estadístico con la
decisión, declaran condiciones y publican cápsulas de código. Un midpoint fijo
más un cap elegido retrospectivamente puede ser un comparador transparente,
pero no sostiene por sí solo una contribución metodológica IJDS cuando el
universo, los splits y el pago no son válidos.

La recomendación es **no someter la versión actual**. Debe conservarse como
diagnóstico histórico y sustituirse por un experimento maturity-safe, con pago
coherente, decisiones mensuales, receta conformal aprendida antes de selección
y una prueba temporal intacta. Si el challenger corregido no supera un point-PD
coherente de manera estable, el resultado científico correcto es negativo; no
se debe retunar el cap sobre la prueba.

## Método de búsqueda y criterio de saturación

Esta es una auditoría crítica dirigida, no una revisión sistemática PRISMA ni un
meta-análisis.

### Vía 1: corpus local

- Se inventariaron los 100 PDF encontrados por el benchmark: 97 en
  `Papers_tesis` y tres manuscritos activos.
- Para los 97 PDF se revisaron metadatos, páginas, cifrado, muestra de capa de
  texto, ruta recomendada, extracción baseline y tema. El CSV conserva ruta,
  páginas, parser, calidad, relevancia y huella SHA-1 del benchmark.
- Se hizo cribado por título/abstract para los 97; se profundizaron los ocho
  artículos de IJDS y las familias directamente relacionadas con (i)
  selección/censura/madurez, (ii) conformal risk control y selección de recetas,
  (iii) optimización prescriptiva/robusta y (iv) crédito, beneficio y equidad.
- Para pasajes de evidencia se prefirió Docling en documentos born-digital y
  MinerU en libros, tesis o capas débiles, conforme a
  `academic-pdf-intake`.

### Vía 2: búsqueda web primaria

El 2026-07-10 se buscaron fuentes elegibles publicadas o disponibles hasta el
2026-07-09. Se restringió la evidencia técnica a páginas del editor, actas
oficiales, DOI, arXiv del autor, organismos públicos y repositorios de la propia
revista. Las familias de consulta fueron:

- `IJDS + título/autor` para los ocho artículos locales;
- `valid selection conformal sets`, `learn then test`, `conformal risk
  control`, `inverse conformal risk control`, `decision-calibrated prediction
  sets`;
- `conformal robust/contextual optimization`, `predict then calibrate`,
  `decision-focused learning`;
- `loan maturity`, `right censoring`, `competing risks`, `profit scoring`,
  `LendingClub`, `dynamic loan portfolio profitability`;
- `temporal/rolling-origin evaluation`, `stationary/block bootstrap` y
  `credit fairness`.

Se consideró alcanzada la saturación temática cuando dos rondas sucesivas de
variantes solo devolvieron trabajos ya incluidos o instancias de una familia ya
mapeada. El cierre no significa que no exista otra publicación, sino que no
apareció una familia metodológica capaz de cambiar el diagnóstico. Los trabajos
2025--2026 se tratan como estado del frente, no como hechos ya estabilizados por
una larga historia de replicaciones.

## Inventario y confianza de extracción

### `Papers_tesis`

| Medida | Resultado |
|---|---:|
| PDF | 97 |
| Páginas | 3.855 |
| Bytes | 218.965.504 (208,82 MiB) |
| Cifrados / con error de apertura | 0 / 0 |
| Tipo de carpeta | 28 `paper`, 57 `supplement`, 12 `tesis` |
| Capa fuerte / parcial / débil | 93 / 1 / 3 |
| Ruta primaria Docling / MinerU | 82 / 15 |
| Extracción baseline pypdf exitosa | 97/97 |

Los nombres del CSV son nombres de archivo, no metadatos bibliográficos
normalizados. No se infirió DOI a partir del nombre. La huella registrada es el
`sha1_prefix` del benchmark (en estos archivos, el alcance señalado por el
manifest es el primer MiB), útil para detectar sustituciones pero no equivalente
a un hash criptográfico de archivo completo.

Casos que requieren cautela:

- **Hand y Henley (1997):** la capa original fue casi vacía. MinerU hybrid la
  recuperó con 66.363 bytes de Markdown, 1.319.189 bytes JSON, 3.021 marcadores
  de bounding box y un `layout.pdf`. Las citas deben salir de esa ruta y
  verificarse visualmente.
- **Hoeffding (1963):** la capa sigue débil; ejecutar MinerU/OCR antes de citar
  una proposición o fórmula.
- **Ben-Tal, El Ghaoui y Nemirovski (2009):** libro de 570 páginas con muestra
  débil; procesar por capítulo con MinerU antes de citar texto.
- **Basel Committee (2015):** capa parcial; verificar todo pasaje normativo
  contra la página renderizada.

### PDF activos de CRPTO

Los tres activos suman 37 páginas: cuerpo 13, submission oficial 13 y
suplemento 11. La extracción baseline fue exitosa en los tres. MarkItDown y
OpenDataLoader también completaron los tres; Docling completó cuerpo y
suplemento, y la exportación directa del submission oficial falló al crear un
directorio de artefactos. La conversión Docling con ruta corta/embebida sí
produjo Markdown y JSON, por lo que el fallo es operacional y no una ausencia
de texto. En QA contra el TeX, Docling y OpenDataLoader recuperaron las 18
secciones y 8 captions esperados; MarkItDown recuperó 10/18 secciones y 0/8
captions. Para auditar claims del manuscrito se usaron el TeX y las rutas
Docling/OpenDataLoader, no MarkItDown aislado.

## Qué exige IJDS y qué muestran sus artículos próximos

La guía vigente define un artículo IJDS como la síntesis de datos, metodología
innovadora, decisión y consecuencias prácticas/éticas. También exige la forma
de divulgación de datos/código al someter y un paquete reproducible al aceptar
([guía de submission](https://pubsonline.informs.org/page/ijds/submission-guidelines),
[política de datos y código, actualizada 2025-01-01](https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy)).
No basta una aplicación bien documentada si el método o enfoque no avanza el
conocimiento; las instrucciones a revisores preguntan expresamente si existe
una idea nueva, interesante y relevante
([reviewer guidelines](https://pubsonline.informs.org/page/ijds/reviewer-guidelines)).

### Ocho artículos IJDS del corpus, lectura profunda

| Artículo verificado | Aporte y estándar observable | Consecuencia para CRPTO |
|---|---|---|
| Fernández-Loría y Provost (2022), *Causal Decision Making and Causal Effect Estimation Are Not the Same* ([DOI 10.1287/ijds.2021.0006](https://doi.org/10.1287/ijds.2021.0006)) | Distingue calidad de estimación y calidad de decisión; formula cuándo una predicción de outcome puede ordenar decisiones útiles. | Obliga a evaluar la pérdida de decisión correcta. Un AUC, cobertura o PD bien calibrada no compensa un payoff económico mal especificado. |
| Morucci, Noor-E-Alam y Rudin (2022), *A Robust Approach to Quantifying Uncertainty in Matching Problems of Causal Inference* ([DOI 10.1287/ijds.2022.0020](https://doi.org/10.1287/ijds.2022.0020)) | Optimiza sobre asignaciones de matching plausibles y cuantifica sensibilidad; publica código y datos. | “Robusto” requiere un conjunto de perturbaciones y una cantidad protegida claramente definidos. El Markov condicional no reemplaza una garantía de la decisión seleccionada. |
| Das et al. (2023), *Credit Risk Modeling with Graph Machine Learning* ([DOI 10.1287/ijds.2022.00018](https://doi.org/10.1287/ijds.2022.00018)) | Combina datos tabulares y grafo corporativo, separa enfoques inductivo/transductivo y ofrece cápsula Code Ocean. Es crédito corporativo, no fair lending de consumo. | Muestra el umbral de contribución empírica y reproducibilidad de la revista. No valida extrapolar un resultado de crédito corporativo a una cartera P2P de consumo. |
| Chen et al. (2024), *Rethinking Cost-Sensitive Classification in Deep Learning via Adversarial Data Augmentation* ([DOI 10.1287/ijds.2022.0033](https://doi.org/10.1287/ijds.2022.0033)) | Formula una pérdida cost-sensitive, un problema bilevel y un algoritmo para reducir errores críticos. | Refuerza que el coste debe entrar coherentemente en entrenamiento/evaluación. Un objetivo `r-pL` no es la esperanza del pago evaluado. |
| Yang y Bi (online 2024; vol. 4, 2025), *Cost-Aware Calibration of Classifiers* ([DOI 10.1287/ijds.2024.0038](https://doi.org/10.1287/ijds.2024.0038)) | Define coste de miscalibración asimétrico, propone tres calibradores y reserva validación/cross-validation para elegirlos; ofrece cápsula. | Es el comparador IJDS más directo. La calibración debe reflejar costes y la selección debe usar datos separados. Los labels de noviembre/diciembre no pueden aprender el calibrador que allí se juzga. |
| Fernández-Loría y Provost (2025), *Observational vs. Experimental Data When Making Automated Decisions Using Machine Learning* ([DOI 10.1287/ijds.2023.0012](https://doi.org/10.1287/ijds.2023.0012)) | Deriva condiciones explícitas bajo las que datos observacionales sesgados conservan rankings de efectos y valida en 7.700 datasets más un caso publicitario. | No licencia el filtrado outcome-conditioned. Para usar datos sesgados hay que declarar y probar las condiciones que preservan la decisión; CRPTO hoy no lo hace. |
| Wiberg et al. (online 2025; vol. 5, 2026), *Synergizing Artificial Intelligence and Operations Research* ([DOI 10.1287/ijds.2025.0077](https://doi.org/10.1287/ijds.2025.0077)) | Sitúa la integración AI--OR en rigor matemático, interpretabilidad y traducción de predicciones a decisiones; divulga el uso de GenAI. | Apoya el encaje temático de CRPTO, pero no prueba novedad. La cadena PD--incertidumbre--LP debe ser coherente y auditable de extremo a extremo. |
| Falconer, Kazempour y Pinson (online 2025; vol. 5, 2026), *Toward Replication-Robust Analytics Markets* ([DOI 10.1287/ijds.2025.0075](https://doi.org/10.1287/ijds.2025.0075)) | Formaliza replication robustness, reemplaza condicionamiento observacional por intervencional y prueba propiedades; publica repositorio. | Ilustra que una palabra fuerte como “robusto” debe corresponder a una propiedad formal y a un adversario/perturbación definidos, no a una sensibilidad descriptiva. |

El patrón común no es complejidad por sí misma. Es alineación entre pregunta,
estimando, función de pérdida, decisión, split y evidencia; además, cada límite
de identificación se declara. CRPTO tiene buena disciplina de artefactos, pero
la versión activa rompe esa alineación en el universo y el payoff.

## Frente metodológico relevante a 2026-07-09

### De cobertura marginal a control de riesgo y selección válida

La predicción conformal clásica da cobertura marginal bajo intercambiabilidad;
no promete cobertura condicional exacta ni cobertura después de que un
optimizador repondera las observaciones. *Conformal Risk Control* controla la
esperanza de una pérdida monótona acotada
([ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/f3549ef9b5ff520a7e41ff3cc306ab2b-Abstract-Conference.html)).
*Learn then Test* convierte selección de hiperparámetros en multiple testing y
da control finito para pérdidas más generales
([AOAS 2025, DOI 10.1214/24-AOAS1998](https://doi.org/10.1214/24-AOAS1998)).

La selección entre sets conformales válidos no conserva automáticamente la
validez. Hegazy et al. diseñan selección estable precisamente para restaurarla
([NeurIPS 2025](https://papers.nips.cc/paper_files/paper/2025/hash/ff9386992bb2b9cee1dddf0bd5f328de-Abstract-Conference.html)).
Por eso, un selector cuya tabla final omite outcomes puede seguir filtrando
información si el intervalo, score, widening o cap fue aprendido con esos mismos
outcomes.

### No intercambiabilidad y tiempo

La literatura no trata una secuencia crediticia 2017--2020 como i.i.d. por
defecto. Hay métodos ponderados bajo covariate shift
([NeurIPS 2019](https://proceedings.neurips.cc/paper_files/paper/2019/hash/8fb21ee7a2207526da55a679f0332de2-Abstract.html)),
garantías más allá de intercambiabilidad bajo discrepancias explícitas
([Annals of Statistics 2023, DOI 10.1214/23-AOS2276](https://doi.org/10.1214/23-AOS2276)),
adaptación online
([NeurIPS 2021](https://papers.neurips.cc/paper_files/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html))
y CRC no intercambiable con pesos relevantes para change points y series de
tiempo
([ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/de04896f011beff76c91e094f72727f4-Abstract-Conference.html)).
CRPTO puede optar por una garantía sencilla bajo un bloque temporal antiguo y
una evaluación puramente empírica posterior, pero no debe presentar un pool de
33 meses como una sola decisión ex ante.

### Conformal + optimización: el comparador ya es decision-aware

Johnstone y Cox y Patel, Rayan y Tewari muestran cómo usar sets conformales como
regiones de incertidumbre robusta; el segundo trabajo construye regiones
contextuales no convexas y explicaciones visuales
([AISTATS 2024](https://proceedings.mlr.press/v238/patel24a.html)). El frente
posterior aprende o calibra el set con la pérdida downstream:

- Yeh et al. aprenden sets convexos condicionales informados por la decisión y
  reportan aplicaciones de arbitraje y portfolio
  ([TMLR 2025 / arXiv:2409.20534](https://arxiv.org/abs/2409.20534));
- Zhou y Zhu trazan un frente finito miscoverage--regret y seleccionan
  robustez con inverse CRC
  ([ICML 2026 / arXiv:2510.07750v3](https://arxiv.org/abs/2510.07750));
- Stratigakos et al. calibran directamente violaciones operativas, no solo
  cobertura, y comparan coste--reliability
  ([arXiv:2606.02081](https://arxiv.org/abs/2606.02081));
- *Conformalized Decision Risk Assessment* certifica la probabilidad de que una
  decisión candidata sea subóptima
  ([ICLR 2026 / arXiv:2505.13243](https://arxiv.org/abs/2505.13243)).

CRPTO puede defender una institución distinta —modelo PD congelado, regla
simple, gobierno fuerte—, pero entonces su novedad debe ser el protocolo
empírico válido y la evidencia de decisión. Con el split contaminado, ese
argumento desaparece.

### Crédito: madurez, cash flow, beneficio y equidad

En crédito, eliminar los casos censurados no es una operación neutra. El riesgo
empírico bajo censura requiere ponderación/modelado explícito; ignorarla puede
sesgar severamente el objetivo
([Ausset, Clémençon y Portier, JMLR 2022](https://jmlr.org/papers/v23/19-450.html)).
Para LendingClub, Li et al. modelan default y prepago como riesgos competitivos,
con horizontes y cash flows, y muestran que incorporar el tiempo mejora la
previsión de rentabilidad
([EJOR 2023, DOI 10.1016/j.ejor.2022.08.013](https://doi.org/10.1016/j.ejor.2022.08.013)).
Djeundje, Crook y Andreeva modelan transiciones de mora, macroeconomía, saldo y
valor presente para monitorizar beneficio dinámico
([EJOR, artículo S0377221725005338](https://www.sciencedirect.com/science/article/abs/pii/S0377221725005338)).

La literatura de profit scoring también separa PD de rentabilidad. Serrano-Cinca
y Gutiérrez-Nieto usan IRR y recuperaciones, no un premio binario
([DSS 2016, DOI 10.1016/j.dss.2016.06.014](https://doi.org/10.1016/j.dss.2016.06.014));
Lyócsa et al. comparan credit y profit scoring en LendingClub/Bondora y miden
retorno realizado y total profit
([Financial Innovation 2022, DOI 10.1186/s40854-022-00338-5](https://doi.org/10.1186/s40854-022-00338-5)).
Un payoff binario estandarizado es admisible como modelo pedagógico, pero debe
nombrarse así, explicitar que omite amortización, timing, prepago, fees y
recoveries, y optimizar la esperanza de exactamente ese payoff.

Finalmente, mejor predicción no implica distribución justa. Fuster et al.
documentan efectos desiguales de ML en crédito hipotecario
([Journal of Finance 2022, DOI 10.1111/jofi.13090](https://doi.org/10.1111/jofi.13090));
Albanesi y Vamossy encuentran heterogeneidad de misclasificación y potenciales
ganancias para grupos con datos de menor calidad
([NBER WP 32917](https://www.nber.org/papers/w32917)). La base LendingClub de
CRPTO no permite una certificación de fair lending. Si se quisiera una auditoría
con proxy, la metodología BISG de CFPB existe pero también requiere validación
propia
([CFPB 2014](https://www.consumerfinance.gov/data-research/research-reports/using-publicly-available-information-to-proxy-for-unidentified-race-and-ethnicity/)).

## Red-team científico de la versión activa

Los números de esta sección se recomputaron sobre el snapshot local congelado.
Son evidencia interna de auditoría; las referencias externas explican por qué
la desviación importa, no sustituyen la comprobación del repositorio.

### H1. Universo *resolved-only*: selección outcome-conditioned y censura por madurez

`src/data/make_dataset.py:115-124` ejecuta `initial_clean`, restringe
`loan_status` a `Fully Paid`, `Charged Off` o `Default` y solo entonces crea
`default_flag`. El filtro conoce un estado observado después de originación.
En el tramo que alimenta el OOT activo:

| Año de originación | Filas raw | Filas retenidas | Retención |
|---:|---:|---:|---:|
| 2018 | 495.242 | 197.178 | 39,81% |
| 2019 | 518.107 | 75.405 | 14,55% |
| 2020 | 146.717 | 4.286 | 2,92% |
| **Total** | **1.160.066** | **276.869** | **23,87%** |

La caída monotónica no es una propiedad de originación: refleja que las
cohortes recientes tuvieron menos tiempo para llegar a un estado terminal en
el snapshot. El optimizador no ve el menú que habría visto el inversor, sino el
subconjunto que el futuro resolvió. Esto afecta tres objetos a la vez:

- el denominador de la tasa de default;
- la distribución de covariables y tasas entre meses;
- la elección de préstamos, porque los no resueltos desaparecen antes del LP.

No es correcto describir 2018--2020 como un OOT de originaciones sin esta
salvedad. Una reparación aceptable debe usar cohortes completamente maduras
definidas solo por `issue_d` y término, o conservar todos los originados y
tratar la censura/prepago mediante survival/competing risks. El primer camino
es más simple para un binary 36-month challenger; el segundo es más fiel a
cash flows. En ambos, la lista candidata debe definirse sin mirar el estado
final.

### H2. Noviembre/diciembre no son splits independientes

La narrativa dice que noviembre de 2017 selecciona y diciembre audita. La
auditoría del artefacto conformal encontró:

- panel de calibración feature-engineered: 237.584 filas, marzo--diciembre de
  2017;
- ventana reciente de 75%: 178.188 filas, mayo--diciembre;
- `fit`: 142.550 filas, mayo--noviembre, incluidas 8.958 de noviembre;
- `tune`: 35.638 filas, 14.943 de noviembre y 20.695 de diciembre;
- `y_true` del tune aprende los factores de widening `q00=1.02`, `q01=1.05`,
  `q02=1.05`, `q03=1.02`, `q04=1.02`.

Por tanto, noviembre y diciembre influyen en los endpoints con los que luego
se selecciona/audita. La whitelist del selector evita fuga *en la última
función*, pero no en la tubería. Las frases “opened after”, “independent
December” y “Mar--Oct fit” no son sostenibles para este artefacto.

Reparación mínima: aprender modelo, calibrador, particiones, cuantiles y todo
widening antes de abrir el bloque de selección; elegir la regla en un bloque
posterior; aplicarla sin reselección en un audit block; reservar la prueba OOT
para una sola lectura. Una receta exacta sin widening aprendido es preferible a
un ajuste más fino contaminado. Si se seleccionan varias recetas conformales,
usar un procedimiento de selección válido o un split dedicado.

### H3. La esperanza optimizada no corresponde al payoff evaluado

Sea `r` la tasa estandarizada, `p` la PD, `L` el LGD y `Y` el indicador de
default. El código activo usa por dólar:

```text
objetivo actual       = r - p L
payoff evaluado       = (1 - Y) r - Y L
esperanza del payoff  = (1 - p) r - p L = r - p(r + L)
```

La diferencia `p r` varía por préstamo, así que puede cambiar el ranking y la
solución. Recalcular el valor de las asignaciones fijas muestra la magnitud,
pero esos valores **no** son el resultado de una reoptimización coherente:

| Política fija | “Expected objective” reportado | Esperanza coherente del payoff | Sobreestimación |
|---|---:|---:|---:|
| CRPTO midpoint | 168.271,56 | 150.911,23 | 17.360,33 |
| Conformal 75% | 160.690,13 | 144.904,14 | 15.785,99 |
| Point-PD | 214.019,15 | 170.007,53 | 44.011,62 |

Las líneas `scripts/experiments/run_ijds_calibration_selected_policy_challenger.py:374-378`
confirman que el payoff realizado paga `r` solo si no hay default y `-L` si lo
hay. La función del LP en `src/optimization/portfolio_model.py:258-265` y
`:721-723` omite la pérdida del interés en default.

La corrección requiere cambiar los coeficientes a `r-p(r+L)`, regenerar todas
las políticas y comparar de nuevo. Además, “realized return” debe reemplazarse
por “standardized terminal payoff” salvo que se incorporen calendario de
pagos, principal, recoveries, prepago, fees, descuento y reinversión. La
literatura de profit scoring muestra cómo construir una medida económica más
realista; no obliga a adoptarla si el paper declara honestamente un payoff
simplificado.

### H4. Cartera pooled de 33 meses: *future-menu lookahead*

La cartera activa asigna un único presupuesto entre originaciones desde enero
de 2018 hasta septiembre de 2020. En enero de 2018 no existía el menú de 2019 o
2020; en septiembre de 2020 ya no se podía financiar retroactivamente un
préstamo de 2018. El diseño mide la mejor selección retrospectiva dentro de un
archivo, no una política crediticia desplegable.

Dos marcos serían válidos, pero responden preguntas diferentes:

1. **operacional:** presupuesto nuevo por mes, regla fijada con anterioridad,
   comparador point-PD pareado en el mismo menú y agregación de resultados
   mensuales;
2. **estático:** declarar explícitamente que es un ranking retrospectivo de un
   archivo cerrado, retirar lenguaje de implementación temporal y no inferir
   rentabilidad de una estrategia de originación.

Para IJDS, el primer marco tiene mucho más encaje. La evaluación rolling-origin
y la predicción dinámica de cash flow son estándares maduros; un pool futuro
necesita una justificación sustantiva que hoy no existe.

### H5. Cap 0,28 y robustness level elegidos retrospectivamente

El propio manuscrito reconoce que iteraciones anteriores inspeccionaron el
corpus OOT. El cap `endpoint_budget_cap: 0.28` entra después en la elegibilidad
de nueve políticas y decide cuáles pueden ganar. Aunque sea round-number y
outcome-free durante la replay final, no es confirmatorio si fue escogido tras
ver resultados del mismo archivo.

La contribución de inverse conformal risk control es precisamente evitar un
robustness level ad hoc y estimar un frente miscoverage--regret con garantía.
CRPTO no necesita copiar un método complejo, pero sí debe elegir una de estas
opciones:

- declarar el cap por una norma externa anterior al experimento;
- seleccionarlo solo en calibración y congelarlo antes de audit/OOT;
- reportar todo el frente predeclarado sin coronar un único champion;
- reconocerlo como sensibilidad exploratoria y retirar inferencia
  confirmatoria.

No se debe volver a ajustar 0,28 si el nuevo challenger falla.

### H6. Bootstrap de meses: intervalo parcial, no incertidumbre de la tubería

El intervalo A39 remuestrea 31 meses como clusters con la asignación fija. Esto
preserva dependencia dentro de cada mes, pero trata los meses como unidades
intercambiables, destruye el orden y no rehace modelo, calibración, selector ni
solver. Con solo 31 meses y un cambio macroeconómico extremo al final del
panel, el resultado estima variación descriptiva del payoff de **esa asignación
fija**; no es un intervalo de la política aprendida ni de su generalización.

El stationary bootstrap fue creado para observaciones débilmente dependientes
([Politis y Romano 1994, DOI 10.1080/01621459.1994.10476870](https://doi.org/10.1080/01621459.1994.10476870)).
Una reparación proporcionada sería:

- diferencia mensual CRPTO menos point-PD sobre menús pareados;
- block/stationary bootstrap con longitud y supuestos declarados, más una
  sensibilidad leave-period-out;
- rolling-origin como evidencia primaria;
- si se afirma incertidumbre end-to-end, nested resampling que vuelva a
  calibrar, seleccionar y optimizar.

No es obligatorio hacer todo a la vez. Sí es obligatorio nombrar el intervalo
según lo que realmente remuestrea.

### H7. Markov es correcto condicionalmente, pero débil y no identifica el riesgo seleccionado

La desigualdad determinista actual

```text
sum_i w_i Y_i <= B_u + V,
V = sum_i w_i 1{Y_i > u_i}
```

es válida después de una asignación adaptativa. El paso probabilístico supone
`E[V] <= alpha`; esa validez ponderada del funded set no se deriva de cobertura
marginal/Mondrian porque el LP elige `w` usando `p` y `u`. Con `alpha=0.10`, el
paper obtiene el evento de default ponderado por encima de 0,574279 con cota de
probabilidad 0,316228. Es una sensibilidad bajo un supuesto no verificado, no
un cap operativo ni una garantía central competitiva con CRC.

Para outcome binario existe además un accounting bound punto a punto más
ajustado:

```text
Y_i <= 1{Y_i > u_i} + 1{u_i = 1}
```

y, por tanto,

```text
sum_i w_i Y_i <= V + sum_i w_i 1{u_i = 1}.
```

Sigue siendo contabilidad, no un teorema selected-set. Si se desea una cota
probabilística publicable, la pérdida de decisión/violación debe calibrarse
directamente en datos independientes con CRC/LTT o con un protocolo de
selección válido. Si no, conviene relegar Markov a una nota y centrar el paper
en resultados empíricos honestos.

### H8. `conformal_group` no representa la partición conformal

La asignación activa copia la letra `grade` en `conformal_group`. Al reconstruir
la partición score-Mondrian real, 0 de los 308 préstamos financiados coinciden
con esa columna. Esto no prueba que los intervalos se hayan calculado mal, pero
sí invalida cualquier tabla o claim que interprete `conformal_group` como la
partición usada por el certificado.

Reparación: regenerar el grupo desde la función canónica de partición, guardar
ambas columnas (`grade` y `score_partition`) con nombres distintos y añadir un
assert de igualdad con la fuente exacta. La validación por grupo debe usar el
identificador real; la cobertura por `grade` puede reportarse como diagnóstico
separado.

### Otros problemas que deben quedar delimitados

- `max_concentration` limita propósito, no concentración por préstamo. El
  nombre y el texto deben decir “purpose concentration”, o debe añadirse un cap
  individual distinto.
- Una tabla de `grade` o score partition no es una auditoría de grupos
  protegidos. Sin atributos o un proxy validado no hay claim de fair lending.
- Cobertura poblacional de un panel temporal no implica validez bajo
  nonexchangeability. El paper puede reportar cobertura retrospectiva, pero no
  usar lenguaje universal.
- Que el selector no vea una columna prohibida es un buen control de software,
  no una prueba de independencia estadística upstream.

## Mapa de claims: apoyo, desafío y disposición

| Claim de la versión activa | Evidencia que lo apoya | Evidencia que lo desafía | Disposición requerida |
|---|---|---|---|
| “Replay exacto al 90%” | La replay numérica de cuantiles/intervalos reproduce el artefacto congelado. | Exactitud computacional no corrige universo outcome-conditioned ni widening contaminado. | Conservar como claim de reproducibilidad del artefacto, no como validez científica del diseño. |
| “Noviembre selecciona sin outcomes” | El dataframe final del selector omite default, payoff y miscoverage. | Outcomes de noviembre aprendieron endpoints/widening upstream. | **Retirar** para el run activo; repetir con receta aprendida antes de noviembre. |
| “Diciembre es auditoría independiente” | Se aplica la regla elegida y se registran resultados por separado. | Outcomes de diciembre están en el tune que aprendió widening. | **Retirar**; construir audit split realmente unopened. |
| “Objetivo económico point-PD” | El LP usa tasa, PD y LGD, y es lineal/reproducible. | `r-pL` no es la esperanza del payoff evaluado. | **Falso como está**; corregir y reoptimizar. |
| “Realized return” | La aritmética del payoff binario se reproduce. | No representa cash flow, IRR o NPV de un préstamo amortizante. | Renombrar a standardized payoff o modelar cash flows. |
| “OOT 2018--2020 de una política de cartera” | Los meses son posteriores a calibración y el artefacto se congela. | Solo préstamos resueltos y un menú pooled futuro de 33 meses. | **No publicable como política**; usar cohortes maduras y decisiones mensuales. |
| “Cap de endpoint 0,28” | Es determinista en la replay y selecciona una regla simple. | Fue fijado tras desarrollo sobre el mismo OOT; no hay justificación externa ni risk calibration. | Tratar como exploratorio o elegirlo antes del test. |
| “Cobertura/funded-set risk” | Cobertura poblacional y por `grade` se calculan; la contabilidad determinista es válida. | Selected weights dependen de endpoints; Markov asume lo que necesita; `conformal_group` está mal rotulado. | Limitar claim a cobertura empírica; corregir grupos; calibrar pérdida de decisión si se busca garantía. |
| “Bootstrap temporal” | Remuestrea meses y evita un bootstrap loan-i.i.d. ingenuo. | 31 meses, orden destruido, asignación/tubería fijas. | Llamarlo fixed-allocation month resampling; añadir rolling/block/paired evidence. |
| “Novedad IJDS” | Protocolo simple, artefactos y separación conceptual PD/guardrail son comunicables. | El frente ya ofrece selection-valid y decision-calibrated methods; la evidencia activa está invalidada. | Novedad condicional a un protocolo maturity-safe convincente y resultados nuevos; no al midpoint por sí solo. |
| “Auditoría de grupo/fairness” | Se reporta composición por `grade`. | `grade` no es grupo protegido y `conformal_group` no es la partición real. | No hacer claim de fairness; usar términos exactos. |
| “Reproducibilidad IJDS” | Tests, builders y artefactos locales permiten replay exacto en la máquina auditada. | Una clean clone no contiene todos los upstream ignorados ni punteros DVC de la lane activa. | Añadir bundle/punteros/hash y probar replay desde clone limpio antes de submission. |

## Brechas que impiden publicación

### Bloqueantes científicos (P0)

1. Universo de decisión definido por el outcome futuro.
2. Selección/auditoría contaminadas por labels upstream.
3. Objetivo esperado incoherente con el payoff evaluado.
4. Menú futuro pooled no implementable.

Cualquiera de las cuatro basta para detener la submission. Las cuatro requieren
regenerar resultados; ninguna se resuelve con prose.

### Bloqueantes de claim (P1)

1. Cap 0,28 no predeclarado ni calibrado.
2. Identidad `conformal_group` incorrecta.
3. Markov demasiado débil y assumption-conditional para figurar como
   certificado central.
4. Inferencia fixed-allocation insuficiente para claims de estabilidad de la
   política.
5. Concentración por propósito descrita ambiguamente.

### Riesgo editorial IJDS (P1)

- El midpoint 50/50 es interpretable, pero metodológicamente modesto frente a
  CRC/LTT, valid selection, inverse CRC y decision-calibrated sets.
- La fortaleza potencial es una aplicación crediticia rigurosa, replicable y
  decision-aware. Los defectos P0 destruyen precisamente esa fortaleza.
- El lenguaje de “certificado” y “robusto” eleva el estándar de garantía. Si el
  método final solo ofrece guardrails heurísticos, usar “auditable guardrail” y
  declarar que la validez es empírica/retrospectiva.
- La submission debe cumplir doble anonimato, ORCID del submitting author,
  formulario de datos/código y divulgación responsable de GenAI
  ([política IJDS GenAI](https://pubsonline.informs.org/page/ijds/llm-policy)).

## Diseño mínimo que podría sostener un paper

### Protocolo recomendado

1. **Universo:** todos los préstamos de 36 meses en el snapshot; separar
   elegibilidad por `issue_d` y disponibilidad de label. No filtrar por estado
   para construir el menú.
2. **Model training:** cohortes suficientemente antiguas; validación temporal,
   parámetros congelados y sin HPO sobre el test.
3. **Calibración PD:** bloque posterior pero maduro.
4. **Conformal fit:** bloque distinto y anterior a selección; Mondrian exacto,
   sin widening aprendido con selección/audit.
5. **Gap de madurez:** al menos el horizonte contractual más margen de
   reporting antes de usar labels.
6. **Selección:** una grilla pequeña predeclarada en un mes; cap externo o
   seleccionado allí; no incluir resultados del audit/OOT.
7. **Audit:** mes posterior aplicado sin reselección.
8. **OOT:** varios meses posteriores; USD 1 millón fresco por mes; misma lista
   para CRPTO y point-PD; regla fija.
9. **Payoff:** optimizar `r-p(r+L)` si se conserva el payoff binario, o modelar
   cash flows/IRR de forma consistente.
10. **Censura residual:** los originados sin outcome observable permanecen en
    el menú. Para métricas finales, reportar bounds 0/1 o survival estimates;
    nunca eliminarlos según el futuro.
11. **Inferencia:** diferencias mensuales pareadas; rolling-origin primario y
    bootstrap temporal como sensibilidad.
12. **Reproducibilidad:** run tag nuevo, outputs inmutables, hashes completos y
    replay desde clean clone.

### Regla de decisión editorial después del challenger

- **Promover** solo si la regla congelada es elegible sin retuning, mejora una
  dimensión riesgo--payoff de forma estable frente al point-PD coherente y el
  resultado sobrevive slices temporales/bounds de censura.
- **Reformular como resultado negativo** si el guardrail compra poca o ninguna
  reducción de riesgo, o si no es elegible bajo el cap predeclarado. El valor
  puede ser una auditoría reproducible de cuándo la cobertura marginal no ayuda
  a una decisión seleccionada, pero ese encaje IJDS debe sostenerse con una
  proposición o insight generalizable, no solo un caso fallido.
- **No retunar** alpha, gamma, tau, cap, cohortes o payoff tras abrir OOT.

## Bibliografía primaria verificada

Acceso comprobado el 2026-07-10; solo se incorporaron trabajos disponibles no
después del corte 2026-07-09. La fecha entre paréntesis es publicación online o
versión consultada cuando la fuente la expone.

### IJDS y política editorial

1. IJDS. *Submission Guidelines* (vigente al acceso).
   <https://pubsonline.informs.org/page/ijds/submission-guidelines>
2. IJDS. *Data and Code Disclosure Policy*, actualización 2025-01-01.
   <https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>
3. IJDS. *Policy on Use of GenAI* (vigente al acceso).
   <https://pubsonline.informs.org/page/ijds/llm-policy>
4. Fernández-Loría, C.; Provost, F. (2022). *Causal Decision Making and Causal
   Effect Estimation Are Not the Same…and Why It Matters*.
   <https://doi.org/10.1287/ijds.2021.0006>
5. Morucci, M.; Noor-E-Alam, M.; Rudin, C. (2022). *A Robust Approach to
   Quantifying Uncertainty in Matching Problems of Causal Inference*.
   <https://doi.org/10.1287/ijds.2022.0020>
6. Das, S. et al. (online 2023-11-20). *Credit Risk Modeling with Graph Machine
   Learning*. <https://doi.org/10.1287/ijds.2022.00018>
7. Chen, Q. et al. (online 2024-02-28). *Rethinking Cost-Sensitive
   Classification in Deep Learning via Adversarial Data Augmentation*.
   <https://doi.org/10.1287/ijds.2022.0033>
8. Yang, M.; Bi, X. (online 2024-12-09). *Cost-Aware Calibration of
   Classifiers*. <https://doi.org/10.1287/ijds.2024.0038>
9. Fernández-Loría, C.; Provost, F. (online 2025-06-03). *Observational vs.
   Experimental Data When Making Automated Decisions Using Machine Learning*.
   <https://doi.org/10.1287/ijds.2023.0012>
10. Wiberg, H. et al. (online 2025-07-08). *Synergizing Artificial Intelligence
    and Operations Research*. <https://doi.org/10.1287/ijds.2025.0077>
11. Falconer, T.; Kazempour, J.; Pinson, P. (online 2025-10-17). *Toward
    Replication-Robust Analytics Markets*.
    <https://doi.org/10.1287/ijds.2025.0075>

### Conformal, selección y decisión robusta

12. Angelopoulos, A. N.; Bates, S. (2023). *A Gentle Introduction to Conformal
    Prediction and Distribution-Free Uncertainty Quantification*.
    <https://doi.org/10.1561/2200000101>
13. Angelopoulos, A. N. et al. (ICLR 2024). *Conformal Risk Control*.
    <https://proceedings.iclr.cc/paper_files/paper/2024/hash/f3549ef9b5ff520a7e41ff3cc306ab2b-Abstract-Conference.html>
14. Angelopoulos, A. N. et al. (AOAS 2025). *Learn then Test*.
    <https://doi.org/10.1214/24-AOAS1998>
15. Hegazy, M. et al. (NeurIPS 2025). *Valid Selection among Conformal Sets*.
    <https://papers.nips.cc/paper_files/paper/2025/hash/ff9386992bb2b9cee1dddf0bd5f328de-Abstract-Conference.html>
16. Barber, R. F. et al. (2023). *Conformal Prediction Beyond
    Exchangeability*. <https://doi.org/10.1214/23-AOS2276>
17. Farinhas, A. et al. (ICLR 2024). *Non-Exchangeable Conformal Risk Control*.
    <https://proceedings.iclr.cc/paper_files/paper/2024/hash/de04896f011beff76c91e094f72727f4-Abstract-Conference.html>
18. Patel, Y. P.; Rayan, S.; Tewari, A. (AISTATS 2024). *Conformal Contextual
    Robust Optimization*. <https://proceedings.mlr.press/v238/patel24a.html>
19. Yeh, C. et al. (TMLR 2025; arXiv v2, 2026-02-01). *End-to-End Conformal
    Calibration for Optimization Under Uncertainty*.
    <https://arxiv.org/abs/2409.20534>
20. Zhou, W.; Zhu, S. (arXiv v3, 2026-06-10; ICML 2026 según fuente de autor).
    *Calibrating Decision Robustness via Inverse Conformal Risk Control*.
    <https://arxiv.org/abs/2510.07750>
21. Stratigakos, A. et al. (arXiv v1, 2026-06-01). *Decision-Calibrated
    Prediction Sets for Robust Power System Operations*.
    <https://arxiv.org/abs/2606.02081>
22. Zhou, W.; Orfanoudaki, A.; Zhu, S. (arXiv, 2025-05-19; ICLR 2026 según
    OpenReview/fuente de autor). *Conformalized Decision Risk Assessment*.
    <https://arxiv.org/abs/2505.13243>
23. Goldfarb, D.; Iyengar, G. (2003). *Robust Portfolio Selection Problems*.
    <https://doi.org/10.1287/moor.28.1.1.14260>
24. Bertsimas, D.; Kallus, N. (2020). *From Predictive to Prescriptive
    Analytics*. <https://doi.org/10.1287/mnsc.2018.3253>

### Crédito, madurez, beneficio, tiempo y equidad

25. Ausset, G.; Clémençon, S.; Portier, F. (JMLR 2022). *Empirical Risk
    Minimization under Random Censorship*.
    <https://jmlr.org/papers/v23/19-450.html>
26. Li, Z. et al. (EJOR 2023). *The Profitability of Online Loans: A Competing
    Risks Analysis on Default and Prepayment*.
    <https://doi.org/10.1016/j.ejor.2022.08.013>
27. Djeundje, V. B.; Crook, J.; Andreeva, G. (online 2025). *The Devil in the
    Details: Dynamic Prediction of Loan Portfolio Profitability with
    Macroeconomic Drivers through Multi-State Modelling*.
    <https://www.sciencedirect.com/science/article/abs/pii/S0377221725005338>
28. Serrano-Cinca, C.; Gutiérrez-Nieto, B. (2016). *The Use of Profit Scoring
    as an Alternative to Credit Scoring Systems in P2P Lending*.
    <https://doi.org/10.1016/j.dss.2016.06.014>
29. Lyócsa, Š. et al. (2022). *Default or Profit Scoring Credit Systems?*
    <https://doi.org/10.1186/s40854-022-00338-5>
30. Xu, Y.; Kou, G.; Ergu, D. (2025). *Profit-Based Uncertainty Estimation with
    Application to Credit Scoring*.
    <https://doi.org/10.1016/j.ejor.2025.03.007>
31. Fuster, A. et al. (2022). *Predictably Unequal? The Effects of Machine
    Learning on Credit Markets*. <https://doi.org/10.1111/jofi.13090>
32. Albanesi, S.; Vamossy, D. F. (NBER WP 32917, 2024). *Credit Scores:
    Performance and Equity*. <https://www.nber.org/papers/w32917>
33. CFPB (2014). *Using Publicly Available Information to Proxy for
    Unidentified Race and Ethnicity*.
    <https://www.consumerfinance.gov/data-research/research-reports/using-publicly-available-information-to-proxy-for-unidentified-race-and-ethnicity/>
34. Politis, D. N.; Romano, J. P. (1994). *The Stationary Bootstrap*.
    <https://doi.org/10.1080/01621459.1994.10476870>

## Dictamen final

**No-go para IJDS en el estado activo.** El corpus y la ingeniería de replay
son fortalezas reales, pero hoy reproducen con precisión una comparación cuyo
universo, splits, objetivo y timing no corresponden a la decisión afirmada. El
camino publicable no es añadir más challengers a la lane contaminada: es una
sola reconstrucción maturity-safe, temporalmente implementable y
económicamente coherente, seguida de una lectura única del OOT y de un claim
proporcional al resultado.
