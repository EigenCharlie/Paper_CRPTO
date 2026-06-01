# CRPTO bibliography synthesis and improvement plan - 2026-05-31

## Alcance

Este memo sintetiza la lectura de la bibliografia organizada en
`Papers_tesis/` despues de la mejora de corpus. El objetivo no es volver a
ordenar PDFs, sino extraer consecuencias concretas para:

- el paper IJDS de CRPTO;
- la tesis/libro Quarto;
- los artefactos y diagnosticos que vale la pena mejorar;
- los experimentos que conviene dejar como future work porque reabren el
  champion o cambian el metodo.

No se ejecuto ningun stage DVC protegido, no se corrio HPO, no se reabrio la
busqueda de 276k politicas y no se modifico ningun artefacto congelado.

## Corpus leido

El corpus local contiene 61 PDFs:

| Carpeta | PDFs | Rol |
|---|---:|---|
| `paper/` | 21 | Bibliografia que debe sostener el paper IJDS. |
| `tesis/` | 12 | Material de tesis/libro que amplia el paper. |
| `supplement/` | 28 | Apendices, future work, metodos vecinos y diagnosticos. |

La lectura combino texto completo, abstracts, conclusiones, secciones de
metodo/resultados, captions de figuras/tablas y paginas renderizadas de figuras
clave. Las paginas visuales mas informativas fueron:

- Hu et al. 2026: diagrama que separa cobertura conformal de robustez
  decision-level.
- Zhou y Zhu 2025/2026: frontera certificada riesgo-costo para elegir niveles
  de robustez.
- Zhou, Orfanoudaki y Zhu 2025: CREDO como certificado de confiabilidad de una
  decision candidata.
- Gibbs y Candes 2021: curvas de cobertura local adaptativa bajo drift.
- Torkian et al. 2025: pipeline aplicado AI+OR en Lending Club.
- Chi, Ding y Peng 2019: robust portfolio optimization para P2P lending.
- Albanesi y Vamossy 2024: figuras/tablas sobre performance y equity de credit
  scores.
- Kawasumi, Kato y Duan 2026: CP para credit scoring ordinal.

## Conclusion central

La bibliografia fortalece mucho a CRPTO, pero tambien obliga a ser mas preciso
con el claim.

El claim mas fuerte no es:

- "CRPTO inventa conformal robust optimization";
- "CRPTO es el primer uso de conformal prediction en credito";
- "CRPTO resuelve conditional coverage exacto";
- "CRPTO supera a todo decision-focused learning";
- "CRPTO produce certificacion legal de fair lending".

El claim mas defendible es:

> CRPTO operacionaliza conformal robust optimization para credit portfolio
> selection, con una tuberia auditada que conecta PD calibrada, intervalos
> conformal Mondrian, optimizacion robusta, validacion de artefactos congelados
> y limites de gobernanza sobre datos Lending Club.

Esta formulacion queda muy bien respaldada por la literatura porque junta cinco
bloques que suelen aparecer separados:

1. Predictive to prescriptive analytics: Bertsimas y Kallus, PTO, SPO+, DFL.
2. Robust optimization: Bertsimas-Sim, Ben-Tal, Bertsimas-Gupta-Kallus, CVaR/OCE.
3. Conformal prediction y risk control: Angelopoulos, Bates, LTT, CRC, RCPS.
4. Conformal robust/decision-aware optimization: Johnstone, Patel, Sun, Yeh,
   Hu, Zhao, Bao, Zhou.
5. Credit/P2P/fairness/governance: Jagtiani, Guo, Chi, Torkian, Albanesi,
   Fuster, Blattner, Brevoort, FinRegLab, CFPB, Basel.

## Que cambia para el paper IJDS

### P0 - Cambios que si deberian entrar antes de submission

1. Afinar el novelty paragraph.

   El paper ya esta bien centrado en "auditable bridge", pero conviene hacerlo
   todavia mas explicito. Debe decir que CRPTO no compite como leaderboard de
   AUC ni como nuevo algoritmo generico de CP, sino como integracion auditada
   para decisiones de cartera de credito.

2. Agregar una frase o parrafo corto de "domain predecessors".

   Chi et al. 2019, Guo et al. 2016 y Torkian et al. 2025 muestran que ya hay
   decision support/portfolio optimization para P2P/Lending Club. Esto no debilita
   a CRPTO; al contrario, permite decir:

   - P2P credit investment ya existia;
   - robust credit portfolio optimization ya existia;
   - AI+OR sobre Lending Club ya existia;
   - lo que faltaba era la capa conformal finita + robust portfolio + auditoria
     de artefactos congelados.

3. Agregar Hu et al. 2026 como vecino metodologico cercano.

   Hu et al. es especialmente importante porque su figura central muestra que
   coverage puede ser suficiente pero no necesaria para robustez. CRPTO debe
   posicionarse como un metodo post-hoc auditable que usa cobertura conformal
   para construir un conjunto robusto interpretable, no como el metodo mas
   eficiente de robustez directa.

4. Reconocer CP en credit scoring ordinal.

   Kawasumi, Kato y Duan 2026 impide hacer un claim amplio tipo "no hay CP en
   credit scoring". La mejor frase es:

   > Recent work has begun to study conformal uncertainty for credit scores,
   > including ordinal score intervals; CRPTO differs by carrying conformal
   > uncertainty into a robust loan-portfolio decision and audit protocol.

   Por estar en japones y ser reporte tecnico, no necesita ocupar mucho espacio
   en el paper; sirve sobre todo como frontera de claim.

5. Reforzar limitations.

   La bibliografia sugiere cuatro limites que deberian quedar visibles:

   - no se reclama conditional coverage exacto;
   - no se prueba un setting online/live, aunque A24 lo diagnostica;
   - no se certifica fair lending legal por ausencia de atributos protegidos;
   - no se aprende el conjunto de incertidumbre end-to-end ni utility-directed.

6. Corregir higiene bibliografica antes de citar formalmente.

   `book/references.bib` todavia parece incompleto para varios papers nuevos.
   Tambien hay una entrada sospechosa para `aior2025lendingclub` donde el autor
   aparece como `Integrating AI and OR`. Antes de submission conviene revisar:

   - Bertsimas y Kallus 2020;
   - Bertsimas, Gupta y Kallus 2018;
   - Chi, Ding y Peng 2019;
   - Hu et al. 2026;
   - Kawasumi, Kato y Duan 2026;
   - CREDO / CREME / Utility-Directed CP / Conformal Decision Theory;
   - Fuster, Blattner, Brevoort, Khandani, Basel.

### P1 - Si hay espacio en el supplement, no en el body

1. Tabla "decision certificate landscape".

   Comparar RCPS, CRC, Learn-Then-Test, CREDO, CREME/Inverse CRC, Utility-Directed
   CP, Conformal Decision Theory y CRPTO. La columna clave debe ser: "que
   certifica". Para CRPTO: `V(alpha)`, `Gamma_CP`, exact pass, robust region y
   lineage de artefactos.

2. Tabla "coverage validity ladder".

   Orden sugerido:

   - split conformal marginal;
   - Mondrian/group conditional;
   - localized/group-weighted;
   - conditional guarantees;
   - beyond exchangeability / covariate shift;
   - multi-source / multi-distribution;
   - online ACI;
   - decision-aware robust calibration.

   Esta tabla ayudaria a evitar overclaiming y a mostrar que CRPTO esta en un
   punto deliberadamente auditable de la escalera.

3. Tabla "P2P/Lending Club predecessors".

   Filas sugeridas:

   - Guo et al. 2016: instance-based credit risk assessment para decisiones de
     inversion.
   - Chi et al. 2019: robust credit portfolio optimization en P2P.
   - Babaei y Bamdad 2020: multi-objective investment recommendation.
   - Torkian et al. 2025: AI+OR, risk-return multi-objective, Lending Club.
   - CRPTO: PD calibrada + conformal uncertainty + robust portfolio + audit trail.

4. Reforzar A23 y A24 con citas.

   A23 encaja con multi-source, multi-distribution, group-weighted y localized
   conformal. A24 encaja con Gibbs-Candes ACI y online conformal via universal
   portfolios. No hace falta cambiar el champion; basta reforzar el lenguaje.

## Que cambia para la tesis/libro Quarto

### Capitulo 15 - fundamentos de riesgo ML

Agregar una subseccion mas fuerte sobre credit scoring como infraestructura de
asignacion, no solo como clasificacion. Papers principales:

- Khandani, Kim y Lo 2010: ML para consumer credit risk con valor economico.
- Albanesi y Vamossy 2024: performance y equity de credit scores.
- Fuster et al. 2022: efectos desiguales y predecibles de ML en credit markets.
- Blattner y Nelson 2021: costo del ruido y disparidades.
- Brevoort, Grimm y Kambara 2016: credit invisibles/unscored.
- FinRegLab 2023: explicabilidad/fairness en underwriting.
- Basel 2015: expected credit loss y disciplina prudencial.

Mensaje tesis: CRPTO vive en un dominio donde los errores no son solo metricos;
son decisiones de acceso, asignacion y capital.

### Capitulo 16 - conformal + optimizacion

Este capitulo deberia convertirse en la "gramatica teorica" de la tesis.
Agregar dos escaleras:

1. Escalera de validez conformal:
   marginal -> Mondrian -> localized/group -> conditional limits -> shift ->
   online -> multi-distribution.

2. Escalera de decision:
   prediction set -> risk-control set -> robust decision -> decision risk
   certificate -> inverse calibration of robustness -> end-to-end decision-aware
   uncertainty.

Aqui entran Angelopoulos/Bates, Barber, RCPS, CRC, LTT, CQR, ACI, Tibshirani
covariate shift, Barber beyond exchangeability, Gibbs conditional guarantees,
Hu CRC, CREDO, CREME, Utility-Directed CP, Conformal Decision Theory y E2E
conformal calibration.

### Capitulo 20 - portafolio/policy

Agregar un bloque historico y visual:

- Markowitz / mean-variance;
- Bertsimas-Sim / price of robustness;
- Bertsimas-Gupta-Kallus / data-driven uncertainty sets;
- Chi et al. / robust P2P credit portfolios;
- CRPTO / conformal uncertainty set para PD y cartera de prestamos.

La imagen mental importante es: "no calibramos Gamma a mano; lo heredamos de la
capa conformal y despues auditamos `Gamma_CP` en el funded set".

### Capitulo 21 - gobernanza, explicabilidad, dataset

Este capitulo debe absorber el bloque fairness/noise/MRM. La tesis puede hablar
mas que el paper de:

- por que Lending Club no permite certificacion legal de fair lending;
- que significa usar proxies como BISG;
- como el ruido de datos afecta grupos vulnerables;
- por que los credit invisibles son un limite de cualquier dataset de credito;
- por que model risk management exige lineage, freeze y drift reports.

### Capitulo 22 - literatura y trazabilidad

Debe convertirse en la taxonomia completa de los 61 papers. Ahora el corpus ya
permite una revision de estado del arte mucho mas madura:

- CP foundations;
- risk-control CP;
- conditional/group/shift CP;
- conformal robust optimization;
- decision-focused learning;
- robust optimization clasica;
- credit/P2P portfolio;
- credit fairness/governance;
- online/multi-source future work.

### Capitulo 23 - future work

Separar future work por "cambia metodo" vs "diagnostico seguro":

- Cambia metodo: Hu CRC, E2E conformal calibration, E2E conditional RO, conformal
  risk training, utility-directed CP, CREME robustness selection, CREDO decision
  risk certificates, multi-source CP.
- Diagnostico seguro: tablas de literatura, coverage ladder, decision certificate
  table, A23/A24 explanatory text, mapping of robust-region policies already
  computed.

## Mejoras de artefactos que valen la pena

### Seguras con el champion congelado

Estas mejoras no deberian reabrir la busqueda ni tocar artefactos congelados:

1. Crear tabla de posicionamiento bibliografico.

   Columnas: paper, familia, que resuelve, que no resuelve, relacion con CRPTO,
   ubicacion recomendada (body/supplement/tesis/future work).

2. Crear tabla de dominios P2P/Lending Club.

   Sirve para blindar el novelty claim frente a reviewers de OR/credit.

3. Crear tabla de decision certificates.

   Conecta CREDO/CREME/CRC con los outputs actuales de CRPTO. No requiere nuevo
   entrenamiento; es conceptual y de auditoria.

4. Mejorar captions de figuras existentes.

   Algunas figuras del supplement ya hacen exactamente lo que la bibliografia
   recomienda: regret-auditability frontier, tail-risk frontier, online ACI,
   multi-distribution coverage. El valor esta en conectar esas figuras con los
   papers correctos.

5. Mejorar `book/references.bib`.

   Agregar entradas limpias y corregir placeholders/autores. Esto es de bajo
   riesgo y alto valor academico.

6. Expandir el libro Quarto sin ejecutar codigo pesado.

   Varias mejoras son texto, tablas conceptuales y crosswalks. Solo requeririan
   render/QA visual si se editan los `.qmd`.

### Seguras solo si consumen artefactos existentes

Estas ideas son utiles, pero deben implementarse leyendo outputs congelados, no
recalculando stages protegidos:

1. Diagnostico de robust-region vs Pareto CREME.

   Si las 45 politicas ya estan disponibles, se puede presentar una frontera
   explicativa de miscoverage/regret/return. No debe convertirse en nuevo
   selector de champion.

2. Certificado CREDO-lite para funded set.

   Se puede escribir como analogia conceptual usando los checks existentes:
   exact pass, `V(alpha)`, `Gamma_CP`, robust region. Implementar CREDO real seria
   metodo nuevo.

3. A23 multi-distribution/grade-vintage.

   Puede reforzarse si ya existe la tabla/figura. Recalcular intervalos o cambiar
   particiones conformal seria stage protegido.

4. A24 online ACI stability.

   Puede explicarse como lectura secuencial del OOT congelado. No debe venderse
   como validacion streaming.

### Requieren permiso explicito y drift/revalidation plan

No hacer como parte del paper actual sin autorizacion:

- recalibrar intervalos conformal;
- entrenar CQR/utility-directed CP como nuevo intervalo promovido;
- correr Hu-style Conformal Robustness Control;
- correr E2E conformal calibration o E2E conditional RO;
- usar CREME para seleccionar nuevo nivel de robustez/champion;
- reoptimizar la cartera fuera de diagnosticos ya autorizados;
- correr `crpto.portfolio.bound_exact_eval`;
- correr HPO o busqueda de 276k politicas;
- tocar `EXTRACTION_MANIFEST.json` o artefactos congelados.

## Lectura por bloque de literatura

### 1. CP foundations

Angelopoulos/Bates, theoretical foundations, Barber limits, RCPS, CRC y LTT
apoyan el nucleo del paper: validez finita, split calibration, riesgo esperado
y limites de inferencia condicional. El paper ya los usa bien. La mejora es
didactica: explicar que CRPTO usa guarantees modestos, auditables y suficientes
para la decision, no guarantees imposibles.

### 2. Conditional, group, shift y online CP

Tibshirani covariate shift, Barber beyond exchangeability, Gibbs-Candes ACI,
Gibbs conditional guarantees, group-weighted, localized, multi-source y
multi-distribution CP son ideales para el libro y supplement. En el paper deben
aparecer como limites/future work, no como promesas actuales.

### 3. Decision-aware conformal y conformal robust optimization

Johnstone/Cox, Patel, Sun Predict-then-Calibrate, Yeh, Hu CRC, Zhao satisficing,
CROMS, CREDO, CREME, Utility-Directed CP, Conformal Decision Theory y CRT
forman el frente mas cercano a CRPTO. La conclusion es clara:

- CRPTO esta metodologicamente alineado con este frente;
- pero CRPTO es mas conservador y auditado;
- las variantes mas modernas optimizan conjuntos/robustez/utility de forma mas
  directa, lo cual es future work y no falla del paper.

### 4. Robust optimization y tail risk

Bertsimas-Sim, Ben-Tal, Bertsimas-Gupta-Kallus, CVaR y OCE dan el vocabulario
para explicar conservadurismo, presupuesto de robustez, sets de incertidumbre y
riesgo de cola. CRPTO debe enfatizar que `Gamma_CP` no es un parametro experto
arbitrario; es una metrica heredada/auditada desde la capa conformal.

### 5. Predictive to prescriptive / DFL

Bertsimas-Kallus, Donti, SPO+, Mandi y robust DFL justifican el framing
predict-then-optimize. La tesis debe reconocer que DFL puede mejorar regret,
pero CRPTO elige auditabilidad, modularidad y reproducibilidad post-hoc. La
frontera regret-auditability del supplement es la pieza correcta para eso.

### 6. Credit, P2P y Lending Club

Jagtiani/Lemieux, Guo, Chi, Babaei, Torkian, Albanesi y Khandani hacen que el
dominio quede mucho mas solido. Tambien evitan exagerar novedad. El paper debe
mostrar que conoce esta linea y que CRPTO aporta incertidumbre conformal +
robust portfolio audit, no que descubre Lending Club ni P2P optimization.

### 7. Fairness, noise, MRM y regulacion

Albanesi, Fuster, Blattner, Brevoort, CFPB, FinRegLab y Basel pertenecen mas a
tesis que a paper body. Sirven para explicar por que un modelo de credito debe
tener gobernanza, datos congelados, disclaimers de protected attributes y
auditoria de decisiones. En el paper bastan caveats y MRM appendix.

## Lista completa de uso recomendado por paper

| Paper | Uso principal en CRPTO |
|---|---|
| Albanesi & Vamossy 2024 | Motivacion credit scoring/equity; tesis y caveat de fairness. |
| Angelopoulos & Bates 2023 | Fundamento didactico de CP; paper/body. |
| Angelopoulos et al. 2024 CRC | Risk-control CP; paper/body y supplement. |
| Angelopoulos et al. 2024 Foundations | Teoria CP; paper/body y capitulo 16. |
| Angelopoulos et al. 2025 LTT | Calibracion via testing; supplement/tesis. |
| Barber et al. 2021 Conditional limits | Limite de claims condicionales; paper/body. |
| Bates et al. 2021 RCPS | Risk-controlling prediction sets; paper/body. |
| Bertsimas, Gupta & Kallus 2018 | Data-driven uncertainty sets; paper/body o tesis. |
| Bertsimas & Kallus 2020 | Puente predictive-prescriptive; paper/body. |
| Bertsimas & Sim 2004 | Price of robustness y Gamma analogy; paper/body. |
| Chi, Ding & Peng 2019 | Predecesor directo robust P2P credit portfolio; paper/body. |
| Donti et al. 2017 | DFL/task-based comparator; paper/body. |
| Elmachtoub & Grigas 2022 | SPO+ y regret; paper/body. |
| Guo et al. 2016 | Credit risk assessment para investment decisions P2P; paper/body o tesis. |
| Hu et al. 2026 CRC | Vecino metodologico cercano; paper/body/future work. |
| Jagtiani & Lemieux 2019 | Lending Club/alternative data; paper/body. |
| Johnstone & Cox 2021 | Conformal uncertainty sets for RO; paper/body. |
| Patel et al. 2024 | Conformal contextual RO; paper/body. |
| Sun et al. 2024 PtC | Predict-then-calibrate; paper/body. |
| Torkian et al. 2025 | AI+OR Lending Club comparator; paper/body o thesis. |
| Zhao et al. 2026 | Conformal robust optimization and satisficing; supplement/future. |
| Babaei & Bamdad 2020 | Multi-objective P2P recommendation; tesis. |
| Basel Committee 2015 | Expected credit loss governance; tesis/MRM. |
| Ben-Tal et al. 2009 | Robust optimization theory; tesis/capitulo 16-20. |
| Blattner & Nelson 2021 | Data noise/disparities; tesis/fairness. |
| Brevoort et al. 2016 | Credit invisibles/unscored; tesis/fairness. |
| Cresswell et al. 2024 | Human decision-making with CP sets; tesis/future HCI. |
| Einbinder et al. 2024 | Label noise robustness of CP; tesis/future. |
| Fuster et al. 2022 | Unequal effects of ML credit; tesis/fairness. |
| Kato 2024 | Conformal predictive portfolio selection; tesis/finance context. |
| Kawasumi et al. 2026 | CP for ordinal credit scoring; tesis y claim boundary. |
| Khandani et al. 2010 | ML consumer credit risk economic value; tesis/domain. |
| Noguer i Alonso 2024 | Conformal portfolio optimization; tesis/finance context. |
| Angelopoulos et al. 2026 non-monotonic CRC | Future risk-control for non-monotone losses; supplement. |
| Bao et al. 2025 CROMS | Model selection for conformalized RO; supplement/future. |
| Barber et al. 2023 Beyond exchangeability | Validity beyond iid; supplement/tesis. |
| Ben-Tal & Teboulle 2007 OCE | Tail-risk diagnostic; supplement. |
| Bhattacharyya & Barber 2026 | Group-weighted CP; supplement/future. |
| CFPB 2014 BISG | Proxy race/ethnicity methodology; supplement/tesis. |
| Chenreddy & Delage 2024 | E2E conditional RO; supplement/future. |
| Cortes-Gomez et al. 2025 | Utility-directed CP; supplement/future. |
| FinRegLab 2023 | Explainability/fairness ML credit governance; supplement/tesis. |
| Gibbs & Candes 2021 | ACI under distribution shift; A24/supplement. |
| Gibbs, Cherian & Candes 2025 | Conditional guarantees; supplement/tesis. |
| Guan 2023 | Localized CP; supplement/future. |
| Jonkers et al. 2024 | Conformal predictive systems under covariate shift; supplement. |
| Kiyani et al. 2025 | Decision-theoretic CP; supplement/future. |
| Lekeufack et al. 2023 | Conformal Decision Theory; supplement/future. |
| Lin, Delage & Chan 2024 | Conformal inverse optimization; supplement/future. |
| Liu et al. 2026 online CP portfolios | Online portfolio CP; A24/future. |
| Liu, Levis, Normand & Han 2024 | Multi-source conformal under shift; A23/future. |
| Mandi et al. 2024 | DFL survey; paper/body and thesis. |
| Rockafellar & Uryasev 2000 | CVaR optimization; supplement tail risk. |
| Romano, Patterson & Candes 2019 | CQR; supplement/conformal comparator. |
| Schutte et al. 2024 | Robust DFL losses; supplement/future. |
| Tibshirani et al. 2019 | CP under covariate shift; supplement/future. |
| Yang & Jin 2026 | Multi-distribution robust CP; A23/future. |
| Yeh et al. 2025 CRT | End-to-end conformal risk training; supplement/future. |
| Yeh et al. 2026 E2E conformal calibration | Decision-aware uncertainty learning; supplement/future. |
| Zhou, Orfanoudaki & Zhu 2025 CREDO | Decision risk certificates; supplement/future. |
| Zhou & Zhu 2025/2026 CREME | Robustness-level Pareto calibration; supplement/future. |

## Prioridad recomendada de trabajo

1. Primero, higiene bibliografica y claim tightening del paper.
2. Segundo, dos tablas de supplement: domain predecessors y decision certificate
   landscape.
3. Tercero, expansion de capitulos 15, 16, 20, 21, 22 y 23 del libro.
4. Cuarto, mejorar captions/prosa de A23/A24/A19/A20-A22 para conectar con la
   literatura nueva.
5. Quinto, dejar Hu CRC, CREDO, CREME, Utility-Directed CP y E2E calibration como
   future work formal, no como requisito para el submission actual.

## Bottom line

La mejor estrategia academica es no hacer mas grande el paper por ansiedad de
bibliografia. El paper debe volverse mas preciso, no mas pesado. La tesis si
puede absorber toda la riqueza del corpus: ahi conviene construir la taxonomia,
las escaleras conceptuales y la discusion de gobernanza. Los artefactos actuales
ya son suficientemente fuertes si se leen como decision-audit pipeline; abrir el
champion para perseguir los metodos 2025-2026 seria otro paper, no una mejora
necesaria del paper IJDS actual.
