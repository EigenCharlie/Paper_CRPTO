# Fable 5.1 Audit of CRPTO: auditoría adversarial y plan de implementación (2026-09-01)

Status: research-governance record y plan de implementación para un agente ejecutor.
No es fuente de evidencia, no activa claims, no modifica ninguna autoridad. Si algo aquí
contradice `docs/research/active_claims_2026-07-14.md`, las notas de teoría exacta o los
artefactos sellados, la autoridad existente gana hasta que el cambio propuesto se aplique
mediante los gates descritos en §11.

Alcance de la auditoría: árbol de trabajo tal como existe el 2026-09-01 (rama `main` en
`9db690f` más cuatro archivos modificados sin commit). Modo estrictamente de solo lectura:
no se ejecutó builder, test, experimento ni etapa protegida. Las propuestas de redacción
para el manuscrito están en inglés y listas para pegar; el resto está en español.

---

## 0. Cómo usar este documento

1. Leer §2 (contexto operativo) antes de tocar cualquier archivo: contiene las
   restricciones de tests que romperán si se aplican los cambios sin actualizar sus
   aserciones.
2. Ejecutar las fases de §11 en orden; las tareas marcadas "∥" pueden correr en paralelo
   en worktrees distintos siempre que no toquen el mismo archivo.
3. Cada fase termina con un commit lógico y con los gates enumerados. Si un gate falla,
   detenerse; no relajar tests para "hacerlos pasar".
4. Ningún número nuevo entra al manuscrito escrito a mano: se emite desde el builder y se
   propaga por claim-sync (§12).

---

## 1. Executive verdict

**Qué artículo existe realmente.** Un artículo retrospectivo de *identificación* sobre la
cadena predicción → calibración Platt → conjunto binario split-conformal → embedding
continuo → coeficiente de un LP mensual → asignación fundada → outcome administrativo
parcialmente observado. Cubre 640,543 préstamos LendingClub a 36 meses, 376,890 candidatos
OOT (364,814 resueltos, 12,076 no resueltos) y acota lo no resuelto con completación
binaria sharp. No selecciona learner, calibrador, embedding, regla, coordenada, cap ni
política.

**Contribución central (reconstruida).** Tres piezas se sostienen solas:
(i) geometría exacta del umbral binario LAC como estadístico de orden de dos muestras
espejo, con la identidad de bandas cruzadas (Prop. 1–2);
(ii) no identificación del coeficiente continuo por el conjunto binario y el criterio
exacto de invariancia de decisión, equivalencia afín positiva módulo el complemento
ortogonal de las diferencias factibles (Lema 1 + Prop. 5), con contraejemplos de tres
préstamos;
(iii) contabilidad sharp por completación común de los 12,076 outcomes no resueltos,
aplicada a cobertura candidata, respuesta a umbrales adyacentes, contrastes pareados y
estimandos fundados (Prop. 3–4, D.5).
El resto son censos completos que ilustran esas piezas.

**Mayor fortaleza.** Disciplina de estimando y de frontera de información; cadena
registro → ledger → JSON → tablas → tests verificable. Todos los números materiales
recomputados reconciliaron (§7).

**Mayor vulnerabilidad.** El artículo bajo-interpreta su hallazgo central. En los estratos
de umbral bajo, el déficit 40/40 es aritméticamente equivalente al aumento de prevalencia
entre calibración (2011–2013, 0.105) y target (2016–2017, prevalencia identificada
[0.151, 0.183]). El manuscrito nunca nombra *label shift*, no cita su reparación conformal
canónica (Podkopaev–Ramdas 2021), reporta las prevalencias solo en el suplemento y no
explica que la brecha temporal de tres años está impuesta por el plazo de 36 meses más los
6 meses de charge-off. Un revisor lee "calibrar en 2012 y evaluar en 2017 sin recalibrar
falla, como era obvio". En paralelo, resultados estructuralmente triviales (Prop. 7 y sus
208 certificados; censo de hull) ocupan ~20% del abstract y varias secciones.

**P0/P1.** No hay P0. Tres P1: F-01 (posicionamiento y mecanismo), F-02 (huella de
resultados triviales), F-03 (descomposición exacta por clase y corolario techo ausentes).
Ninguna corrección P1 requiere evidencia empírica nueva.

**Veredicto.** GO con revisiones mayores de narrativa, posicionamiento y jerarquía
teórica.

**Lo que no debe cambiar.** Protocolos sellados y tags; números registrados; postura de no
selección; bounds sharp vs intervalos de confianza; contabilidad loan-wise de no
resueltos; Lema 1, Prop. 1 y Prop. 5 con sus contraejemplos; regla de primer uso
"six-month outcome-availability rule" para 40/40; separación cinco learners vs
sensibilidades solo-CatBoost; tabla de objetos calibrados en Related Work; Tablas
S12A–S12C.

---

## 2. Contexto operativo para el agente ejecutor

### 2.1 Autoridades y precedencia

- Operativa: `CLAUDE.md` (fuente única), `AGENTS.md`.
- Claims (prosa): `docs/research/active_claims_2026-07-14.md` (título interno 2026-08-09).
- Claims (ejecutable): `configs/ijds_claim_ledger.yaml` (`schema_version: 2026-08-09.1`,
  48 claims). Cada claim declara `surfaces.required` y `surfaces.allowed`; el marcador
  `<!-- claim:<id> -->` debe aparecer en cada superficie requerida y en ninguna no
  permitida (`src/ijds_audit/claim_ledger.py:180-195`).
- Fuentes y linajes: `configs/ijds_active_evidence_sources.yaml` (`schema_version:
  2026-08-01.1`): 53 punteros DVC y 11 linajes Git-nativos.
- Números: `reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json` (único
  manifiesto paper-facing; status
  `active_ijds_v5_phase_and_dual_set_native_paper_facing_evidence`; construido como
  extensión del padre sellado `6e9086e` con 33 fuentes DVC no materializadas, ver clave
  `incremental_parent`).
- Teoría exacta: `docs/research/ijds_exact_binary_conformal_theory_2026-07-24.md`,
  `docs/research/ijds_decision_invariance_theory_2026-07-30.md`. Precedencia sobre
  resúmenes del skill.
- Manuscrito: `paper/CRPTO_ijds.qmd` y `paper/supplement_ijds.qmd`. TeX oficial solo por
  `scripts/build_ijds_submission_tex.py`; `--check` compara hash y no escribe (`:114-117`).
- Builder: `scripts/build_ijds_binary_geometry_frontier_v4_evidence.py` (6,118 líneas):
  emite 45 tablas `reports/crpto/tables/crpto_ijds_v4_table*.csv` y cinco familias de
  figuras (`_coverage_figure` :1310, `_phase_figure` :1512, `_envelope_figure` :1599,
  `_common_panel_threshold_response_figure` :1778,
  `_common_panel_threshold_response_census_figure` :2004; stems en :187-192; rutas de
  tablas en :92-118; `paper_artifacts` con 55 descriptores).
- Extensión sellada: `scripts/extend_ijds_evidence_from_sealed_parent_2026_08_01.py`.

### 2.2 Prohibiciones vigentes

- No ejecutar `crpto.pd.champion`, `crpto.conformal.intervals`,
  `crpto.conformal.validation`, `crpto.portfolio.optimization`,
  `crpto.portfolio.bound_exact_eval`.
- No modificar `EXTRACTION_MANIFEST.json`, protocolos sellados, tags ni artefactos
  protegidos.
- No `assert` como guarda en `src/**` ni `scripts/**` (Calibre usa `-OO`); usar
  excepciones explícitas.
- No copiar números a mano al manuscrito; todo número paper-facing sale del builder.
- Cualquier objeto empírico nuevo requiere protocolo predeclarado, tag distinto, rutas
  contenidas y registro en fuentes antes del uso en el manuscrito.
- Runs > 30 min: unidad atómica, heartbeat, throughput, deadline, cancelación cooperativa
  y resume hash-bound; estado operativo fuera de Git y de raíces protegidas.
- Windows PowerShell + `uv run`; `just` para recetas.

### 2.3 Estado del árbol de trabajo el 2026-09-01

`git status`: modificados sin commit `book/chapters/06-blueprint-manuscrito.qmd`,
`paper/CRPTO_ijds.qmd`, `paper/submission/CRPTO_ijds_submission.tex`,
`paper/supplement_ijds.qmd`. El diff introduce la redacción "information-boundary audit /
physical isolation along the primary lineage / logical target-outcome nonuse---not a
physical lockbox---in retrospective sensitivities" (`CRPTO_ijds.qmd:193-199`;
`supplement:40-48`, `:3017-3024`, `:3321`). Los tres PDFs
(`paper/submission/CRPTO_ijds_submission.pdf` 76 pp., `paper/CRPTO_ijds.pdf` 52 pp.,
`paper/supplement_ijds.pdf` 80 pp., todos del 2026-08-09 00:35) siguen diciendo
"outcome-isolated audit": están desfasados respecto a QMD/TeX. El TeX del árbol parece
regenerado por el builder (mismo cambio que el QMD) pero no se verificó con `--check`.

### 2.4 Restricciones de tests que condicionan el plan (leídas del código)

- `tests/test_ijds_v4_claim_sync.py::test_theory_has_two_suites_and_sequential_propositions`
  (`:207-225`) exige exactamente dos `##` en la sección de teoría y `**Proposition 1..8**`
  secuenciales. Renombrar (F-07) o trasladar (F-02) exige actualizar
  `assert proposition_numbers == list(range(1, 9))`.
- `::test_related_work_is_ordered_by_calibrated_object` (`:104-126`) fija los seis títulos
  `##` de Related Work: no crear subsección nueva; el párrafo de label shift va dentro de
  "Conformal membership and temporal transport".
- `::test_body_wording_preserves_information_and_identification_boundaries` (`:128-148`)
  exige en el cuerpo "208 window-by-role-month certificates over 26 candidate menus" y
  "A uniform shortfall across the four calibrators is therefore not established".
- `::test_fixed_top_k_jomi_corollary_keeps_its_exact_boundary` (`:150-179`) exige en el
  cuerpo `\operatorname{BetaBinomial}(n,K+1,m-K)`, `Z_i>T_{\mathrm{topK}}`, `r_\alpha`,
  `1\le K<m`, `\alpha\in(0,1)`, "finite cutoff", "not a new beta--binomial law"; un solo
  marcador `<!-- claim:theory.jomi_top_k_reference_size_law -->` por superficie.
- `::test_secondary_theory_claims_remain_as_results_bridges_only` (`:227-246`) prohíbe en
  el cuerpo los títulos `**Proposition 8 (sharp directional residual-distribution
  bounds).**`, `**Identity 1 (count versus exposure weighting).**`, `**Lemma 2 (monotone
  finite-catalog completion).**`.
- `::test_dual_coefficient_certificate_count_names_the_repeated_unit` (`:181-192`) exige
  "208 window-by-role-month certificates over 26" en cuerpo, suplemento, registro y matriz.
- `::test_v4_wording_keeps_theory_and_empirical_scope_separate` (`:76-101`) exige "not a
  confidence interval", "not a selected operating policy", "not independent replications",
  "target-support condition", "does not imply continuity" en ambas superficies.
- `tests/test_ijds_active_claim_sync.py::test_manuscript_surfaces_share_v4_claims_and_retire_old_headlines`
  (`:926-976`) exige en todas las superficies los tokens `0.1017`, `0.0971`, `0.8884`,
  `0.1118`, `6,240`, `216`, `72`, `31 of 40`, `109`, `44 loan-month positions`, `14,738`,
  `155,937.27`, `3,067`, `2,985`, `0.001284`, `215`, `individual-age`, `label-mondrian`,
  `status-indexed`, `selected-set`, y prohíbe los retirados. Mover la Fig. 2 (F-05) no
  puede eliminar los números S3 del texto.
- `::test_official_tex_is_deterministically_generated_from_qmd` llama
  `render_submission_tex(check=True)`: regenerar TeX tras cada edición del QMD.
- `tests/test_inspect_ijds_pdfs.py::test_active_abstract_satisfies_ijds_length_and_paragraph_contract`:
  abstract ≤ 300 palabras, un párrafo (hoy 292).
- `tests/test_supplement_table_sync.py`: valores de las tablas CSV citados en el
  suplemento deben coincidir.
- `tests/test_book_active_companion.py`: coherencia del libro con suplemento y registro.

### 2.5 Recetas `just` relevantes

`lint`, `type-check`, `type-check-fast`, `test`, `publication-integrity`, `drift-gate`,
`ijds-active-check`, `ijds-active-science-tests`, `validate-champion`, `paper-tex`,
`paper-tex-check`, `paper-official`, `paper-official-windows`, `paper-pdf-audit`,
`paper-machine-supplement`, `submission-build`, `submission-check`; en freeze
`submission-freeze-check` y `submission-closeout` (requieren `ijds-pull`).

---

## 3. Qué se revisó y cómo se verificó

**Leído íntegramente:** `AGENTS.md`; `CLAUDE.md`; `active_claims_2026-07-14.md` (1,256
líneas); `ijds_claim_ledger.yaml`; `ijds_active_evidence_sources.yaml` (secciones
relevantes); JSON de evidencia (todas las secciones paper-facing volcadas);
`paper/CRPTO_ijds.qmd` (2,561 líneas, 20,127 palabras); `paper/supplement_ijds.qmd`
(3,373 líneas, 28,505 palabras); `CLAIM_AUDIT_MATRIX.md`; ambas notas de teoría exacta;
`ijds_full_theory_sota_protocol_reaudit_2026-07-31.md`;
`ijds_predict_calibrate_optimize_sota_audit_2026-07-31.md`;
`ijds_literature_corpus_ledger_2026-07-30.md`;
`ijds_pending_scientific_work_disposition_2026-08-01.md`;
`ijds_equal_notional_jomi_synthetic_feasibility_v1_protocol_2026-08-08.md`;
`.codex/skills/crpto/SKILL.md`; `paper/submission/README.md`;
`configs/crpto_publication_targets.yaml`; entradas clave de `references.bib`;
`tests/test_ijds_v4_claim_sync.py`; `tests/test_ijds_active_claim_sync.py` (parcial);
índice de `tests/test_supplement_table_sync.py`; estructura de
`src/ijds_audit/claim_ledger.py`; cabeceras de las tablas CSV.

**Superficies generadas:** los tres PDFs; el TeX; figuras `fig1_coverage`,
`fig2_phase_transition`, `fig4_common_panel_threshold_response`,
`crpto_ijds_information_boundary`.

**Recomputaciones independientes (Python desechable fuera del repo):**
- Beta-binomial JOMI: PMF suma 1; media `n(K+1)/(m+1)`; varianza cerrada; Monte Carlo
  200k réplicas (`n=30,m=20,K=5`), desviación máxima de PMF 0.00125; gate
  `⌈(1−α)(R+1)⌉ ≤ R ⇔ R ≥ ⌈1/α−1⌉` verificado para `R=0..14`, `α=0.10`.
- CRC finito: `D(2,11)=0.34156`, `D(2,15)=0.29250`, `D(2,128)=0.10013`,
  `D(2,129)=0.09974`.
- W7/W8: `k=5,337`, `n−k=592=⌊0.1·5930⌋−1`; `k=5,616`, `n−k=622`; `m=+11`, `m=−16`;
  tasas 0.099848/0.099711; `1−0.111801=0.888199`.
- Respuesta común: `−281/76,495=−0.0036734`; `[−312,−290]/79,047=[−0.0039470,−0.0036687]`;
  ancho `22/79,047=0.000278`.
- `12,076/376,890=0.0320412`; prevalencia `[56,972; 69,048]/376,890=[0.151163, 0.183205]`.
- Contraejemplo Prop. 1 (`n=20`, 18 nondefaults `p=0.10`, uno `p=0.70`, un default
  `p=0.20` → `k=19`, `c=0.70`). Contraejemplos Prop. 5 (`s=(0,.6,1)` vs `t=(0,.36,1)`;
  `p=(.3,.1,.8)`, `c=(.3,.6,.3)` → `[0,.6],[0,.7],[.5,1]`, sets `{0},{0},{1}`).
- Particiones: 1,040+832=1,872; 5,200−1,872=3,328; 1,248+4,992=6,240;
  4·4·2·3·8·15=11,520; 4·4·2·3·8=768; 4·2·3·8·3=576; 36·48=1,728; 15+1,065+120=1,200;
  1,196+4=1,200; 1,009+120+71=1,200; 5,840+9,853+2,307=18,000; 8·26=208=88+120;
  40+40+7=87; 200−16=184; 200−12=188; 52,311+3,003,924+717,965=3,774,200;
  52,311+717,965=770,276; 45 CSV.
- Descomposición por clase (S6A, CatBoost W1): `0.843833·0.986867 + 0.156167·0.283648 =
  0.87705 = coverage_resolved`; miscobertura 0.12295 = 0.11187 (defaults) + 0.01108
  (nondefaults).
- Conteos léxicos (cuerpo/suplemento): "does not" 64/58; "neither" 46/40; "not a" 40/31;
  "sharp" 57/72; "exact" 66/97; "complete" 52/91; "declared" 37/45; "finite" 83/71;
  "label shift" 0/0; "ceiling" 0/0.

**Fuentes primarias verificadas en la web (2026-09-01):** Jin & Ren JRSS-B 87(4):1239–1259
(arXiv 2403.03868 v3; Prop. 2, 6, 9 y Teorema 1 leídos del PDF: Prop. 6 da
`R_topk={i: S_i>T_topk}` con `T_topk` el `(m−K)`-ésimo score de test; Prop. 9 es
asintótica con umbral convergente y `G` continua; Teorema 1 exige invariancia a
permutaciones de `D_calib` y exchangeability de calibración con el focal condicional a los
demás test; la selección knapsack está en los ejemplos); Marques SPL 219:110350 (2025);
Barber & Pananjady ALT 2026 PMLR 313 (switch coefficient, β-mixing); Aldirawi–Li–Guo
2604.01502 v2 (2026-04-17); Angelopoulos 2602.20151 v1; Birbil–Chi 2608.04474 v1
(2026-08-05); Zheng–Jin 2602.10018 v1; Lützow et al. 2605.12341 v1; Shekhar–Howard
2606.10187 v1; Kato 2410.16333 v2 (sin venue); Podkopaev–Ramdas 2103.03323 v4;
Ramos–Graziadei–Cabezas 2605.19024 v1 (2026-05-18); Xu–Guo–Wei 2512.12844 v2
(2026-04-27); Zhou–Fathony–Nguyen–Sesia 2606.14909 v1 (2026-06-12);
Braun–Holzmüller–Jordan–Bach 2512.11779 v2 (2026-05-29); Long et al. 2608.29789 v1
(2026-08-30); Farzaneh–Simeone 2608.28179 v1 (2026-08-28); Patel–Tewari 2602.08215 v2.

**Limitaciones.** No se ejecutaron tests ni builders. No se abrieron parquet/CSV crudos de
DVC. Búsqueda web US-only. Venue de Podkopaev–Ramdas no confirmado (probable UAI 2021,
PMLR 161): verificar antes de citar.

---

## 4. Mapa del argumento

`data → score → calibration → residual/set → embedding → candidate decision → funded
decision → outcomes → claims`

| Flecha | Probado | Solo diagnosticado | No identificado | Garantía que no transfiere |
|---|---|---|---|---|
| data → score | Universo status-independiente exhaustivo; cronología `tbl-protocol` | AUC/Brier/PSI en panel resuelto | Transporte de covariables; efectos de aprobación | Ninguna garantía predictiva OOT |
| score → calibration | Platt fijo; cuatro mapas sobre `q_raw` común | Brecha marginal 5/5 negativa; ECE resuelto | Calibración individual; mecanismo (label vs covariate shift) | Calibración de probabilidad ⇏ exchangeability de residuos |
| calibration → residual/set | Prop. 1; Prop. 2; censo 200 celdas | 40/40 bounds < 0.90; 31/40 flags; frontera CDF; label-Mondrian | Validez temporal; causa | Cobertura bajo exchangeability ⇏ cobertura 2016–17 |
| set → embedding | Lema 1: contacto con 0/1; fibra `[p, p+γ(1−p))` | V1d: 80/80 sets iguales, 9,659/11,520 asignaciones cambian | Magnitud de `u_i` | Cobertura del set ⇏ invariancia del coeficiente |
| embedding → candidate decision | Prop. 5; Prop. 6; hull 26/26 | 0/3,328 y 0/6,240 sin certificado | Igualdad de caras; unicidad | Ranking o set-igualdad ⇏ invariancia LP |
| candidate → funded | Prop. 3; identidad covarianza | Conteo−dólar > 0 en 96/96 | Validez fundada; FCR | Cobertura candidata ⇏ cobertura fundada |
| funded → outcomes | Prop. 4 (bounds pareados; ancho) | Direcciones por regla/coordenada; 216/216 envolventes incluyen 0 | Causalidad; cash-flow; ganador | Payoff estandarizado ⇏ retorno |
| outcomes → claims | Registro/ledger/JSON sincronizados | — | — | Hecho de archivo finito ⇏ refutación del teorema conformal |

---

## 5. Hallazgos P0–P3

### 5.1 Tabla resumen

| ID | Prioridad | Estado | Conf. | Dominio | Hallazgo | Evidencia file:line | Corrección |
|---|---|---|---|---|---|---|---|
| F-01 | P1 | PROBABLE | 80% | Posicionamiento/inferencia | Label shift nunca nombrado ni citado; prevalencias solo en suplemento; brecha temporal forzada por retraso de etiquetas no explicada | `paper/CRPTO_ijds.qmd:147-158`, `:717-720`, `:1728-1736`; `paper/supplement_ijds.qmd:377-381`; grep "label shift"=0 | §5.2 |
| F-02 | P1 | VERIFIED | 85% | Narrativa/teoría | Prop. 7 y 208 certificados triviales con huella en abstract, Intro, Teoría, Results, Discussion, Conclusion | `:31-36`, `:182-191`, `:232-236`, `:1487-1530`, `:2021-2056`, `:2266-2275`, `:2547-2555` | §5.2 |
| F-03 | P1 | VERIFIED | 90% | Claims/números | Descomposición por clase de la miscobertura (≈91% defaults perdidos) y corolario techo ausentes | `supplement:589-631`; nota teórica `:174-184`; grep "ceiling"=0 | §5.2 |
| F-04 | P2 | VERIFIED | 85% | Métodos/figuras | Diagnóstico joint-block con `m` 35k–120k tiene potencia ≈1; flags casi tautológicos ocupan medio panel de Fig. 1 | `:1599`, `:1650-1654`; JSON `exchangeability_transport_test` | §5.2 |
| F-05 | P2 | VERIFIED | 80% | Figuras | Fig. 2 dedica figura principal a celda post-inspección | `:1824` | §5.2 |
| F-06 | P2 | VERIFIED | 90% | Reproducibilidad | "Físico" vs "lógico" inconsistente entre cuerpo y B.4.2/B.9 | `:193-198`, `:713-715`; `supplement:44-45`, `:730`, `:1469-1470` | §5.2 |
| F-07 | P2 | VERIFIED | 85% | Teoría | Jerarquía infla alcance (Prop. 2,3,4 lemas; 6 corolario; 7 remark; 8 lema) | `:1201`, `:1306`, `:1338`, `:1445`, `:1487`, `:1549` | §5.2 |
| F-08 | P2 | VERIFIED | 85% | Literatura | Omitidos Podkopaev–Ramdas; Ramos et al.; Xu–Guo–Wei; Zhou et al. | `references.bib`; `:270-338` | §5.2, §8 |
| F-09 | P2 | VERIFIED | 95% | Editorial | Acumulación de negaciones y adjetivos | conteos §3 | §5.2 |
| F-10 | P2 | VERIFIED | 80% | Narrativa | Censo de hull con sección propia | `:1931-1956`; `supplement:2738-2769` | §5.2 |
| F-11 | P2 | HYPOTHESIS TO TEST | 60% | Claims | Platt≈beta en 48/48 celdas; probable colapso numérico del beta | `:1686-1709`; `supplement:339-345` | §5.2, E-13 |
| F-12 | P2 | VERIFIED | 75% | Narrativa | Bounds isotónicos idénticos entre ventanas = umbral en átomo; ilustra Prop. 2 | `supplement:832-855` | §5.2 |
| F-13 | P2 | VERIFIED | 80% | Teoría | Corolario JOMI asume i.i.d.; basta exchangeability sin empates | `supplement:1718-1794` | §5.2 |
| F-14 | P3 | VERIFIED | 90% | Terminología | "permutation-equivariant" vs invariancia a permutaciones de calibración | `:358`; `supplement:3199` vs `:346-347` | §5.2 |
| F-15 | P3 | VERIFIED | 100% | Repo | PDFs desfasados respecto a QMD/TeX no commiteados | `git diff`; pypdf | Fase 0 |
| F-16 | P3 | VERIFIED | 90% | Autoridades | Deriva de fechas (registro 08-09; ledger 08-09.1; sources 08-01.1; skill 08-08); run JOMI sintético con tags sin nota de no registro | cabeceras; `SKILL.md:13`; `git tag` | Fase 7 |
| F-17 | P3 | VERIFIED | 85% | Tablas | Colisión S6/S7/S9 entre numeración del suplemento y nombres CSV | `supplement:524`, `:1003`, `:2401`; `reports/crpto/tables/` | Fase 5 |
| F-18 | P3 | VERIFIED | 80% | Datos | Exclusión 2014–2016Q1 justificada solo para fitting | `supplement:132-139` | Fase 3 |
| F-19 | P3 | VERIFIED | 70% | Reproducibilidad | JSON extendido desde padre sellado con 33 fuentes DVC no materializadas | JSON `incremental_parent` | Freeze |

### 5.2 Fichas detalladas

#### F-01 (P1) — Mecanismo evidente no nombrado; brecha temporal no explicada

**Texto actual.**
- `CRPTO_ijds.qmd:166-168`: "...the crossing does not, by itself, identify the source of
  the shortfall."
- `:1734-1736`: "This is a finite-panel marginal level gap, not individual or conditional
  calibration, a sampling interval, a learner ranking, or an identified cause of the
  coverage shortfall."
- `:2242`: "The marginal gap and residual frontiers ask different questions and identify
  no mechanism linking them to coverage."
- `:717-720`: "Label-dependent fitting is additionally restricted by an information cutoff
  of March 31, 2016. ..."
- `supplement_ijds.qmd:379-381`: "Among resolved primary OOT outcomes, default prevalence
  is 0.156167, versus 0.104781 on the 2011 Platt block and 0.196438 among resolved
  extension loans."

**Por qué es problemático.** Por la identidad de cobertura `Cov = (1−π_t)P_t(p≤c|Y=0) +
π_t P_t(p≥1−c|Y=1)`, en un estrato con `c<1/2` y `max_target p < 1−c` se tiene `Cov ≤
1−π_t`. El déficit es, en esos estratos, el exceso de prevalencia target sobre la
tolerancia; en el panel resuelto ≈91% de la miscobertura de CatBoost W1 proviene de
defaults perdidos. Esto es label shift en sentido técnico y su reparación conformal
canónica existe desde 2021. El paper cita covariate shift ponderado y feedback shift pero
no label shift. Además, la razón por la que la calibración es de 2012–2013 y el target de
2016–2017 es estructural: un préstamo a 36 meses solo tiene etiqueta completa en
`t + 36m + 6m`; con cutoff 2016-03-31 la cohorte más reciente con etiquetas casi completas
es 2012–2013-01. Este argumento desarma la crítica de straw man y solo está implícito.

**Contraargumento más fuerte.** El registro prohíbe "shift mechanism inferred from a flag"
y "cause of the coverage gap inferred from the marginal level audit". Correcto: no se
infiere causalidad. Nombrar label shift como *mecanismo consistente, no descompuesto* y
citar su reparación como diseño prospectivo respeta la frontera, igual que el paper ya
hace con covariate shift.

**Veredicto.** Under-claim que daña la defensa; no cambia conclusiones.

**Redacción propuesta (inglés).**

(a) Data, nuevo párrafo tras `:720`:
> "The gap between the residual windows (2012--January 2013) and the primary target
> (April 2016--June 2017) is not a design choice. A 36-month contract resolves only about
> 39 months after origination under the six-month Charged Off rule, so at the March 31,
> 2016 information cutoff the most recent cohorts with near-complete labels were
> originated in 2012 and early 2013. Any split-conformal calibration available at the
> decision date is therefore at least three years older than the loans it scores. This
> label-delay constraint is the reason the paper audits transport rather than assuming
> it."

(b) Data, tras `tbl-protocol` (`:696`):
> "Resolved default prevalence is 0.104781 on the 2011 calibration block, 0.156167 on the
> resolved primary target, and 0.196438 on the resolved extension; the sharp
> all-candidate target prevalence is [0.151163, 0.183205]."
(Emitir 0.104781 y 0.196438 como campos del manifiesto si aún no lo están; ver §12.)

(c) Results, sustituir la última frase de `:1734-1736`:
> "This is a finite-panel marginal level gap. Together with the resolved-label
> decomposition in Table 3, it is consistent with an increase in default prevalence
> between the calibration blocks and the target (label shift). The audit does not
> decompose label from covariate shift, does not estimate individual or conditional
> calibration, does not rank learners, and infers no cause."

(d) Related Work, dentro de "Conformal membership and temporal transport", tras `:321`:
> "Label shift is the transport construction closest to the prevalence change documented
> here. Podkopaev and Ramdas [-@podkopaev2021labelshift] reweight split-conformal
> calibration by estimated class-prior ratios and obtain marginal target coverage when
> unlabeled target data identify those priors and the class-conditional feature law is
> invariant. At CRPTO's decision date no target label is available for three years, so
> the class priors of the loans being scored cannot be estimated from resolved outcomes
> without post-hoc selection; estimating them after the fact would not define a valid
> interpretation of the frozen thresholds. We therefore report the prevalence contrast as
> a diagnostic and list label-shift-aware recalibration as a prospective design."

(e) Discussion `:2242`, sustituir "identify no mechanism linking them to coverage" por:
> "are consistent with, but do not decompose, a prevalence increase between calibration
> and target; neither identifies a mechanism beyond that arithmetic."

(f) Fila nueva en Apéndice G.1 (`supplement:3196-3202`):
> "| Marginal coverage under a prevalence change | Label-shift-weighted split conformal
> with class priors estimated from unlabeled target covariates before any target label is
> read [@podkopaev2021labelshift] | Invariant class-conditional feature law and
> consistent prior estimation | Priors estimated after target outcomes, or a
> class-conditional law that the residual frontier already contradicts |"

**Archivos.** `paper/CRPTO_ijds.qmd` (Data, Related Work, Results, Discussion);
`paper/supplement_ijds.qmd` (G.1); `paper/references.bib` (`podkopaev2021labelshift`);
`docs/research/active_claims_2026-07-14.md` ("Permitted Claims": "The marginal gap and
class decomposition are consistent with a prevalence increase (label shift); the audit does
not decompose label from covariate shift or infer a cause"); `configs/ijds_claim_ledger.yaml`
(si se emite prevalencia 2011: nuevo claim `data.calibration_target_prevalence_contrast`,
kind empirical); `paper/submission/CLAIM_AUDIT_MATRIX.md` (fila "Marginal score--outcome
gap": Permitted "+ consistent with label shift; not decomposed"; Forbidden "+ label shift
identified as cause").

**Tests.** claim-sync; `test_related_work_is_ordered_by_calibrated_object`;
`test_publication_integrity`; `test_ijds_bibliography_views`; `paper-tex-check`.

#### F-02 (P1) — Huella desproporcionada de Prop. 7 y del censo de hull

**Texto actual.** Abstract `:31-36`; Intro `:182-191`, `:232-236`; Teoría `:1487-1530`
(Proposition 7); Results `:2021-2056`; Discussion `:2266-2275`; Conclusion `:2547-2555`;
suplemento D.2.2 `:1957-2033`, E.4.6 `:2828-2868`, Tabla S9O.

**Por qué es problemático.** Con `w_i ∈ {r_i, −LGD}` y `q_i ∈ {0,1}` alineados, el óptimo
maximin excluye toda exposición con `w_i=−LGD` siempre que exista una asignación factible
de presupuesto completo con `q_i=0`; la restricción de riesgo es redundante para todo
`τ∈[0,1]`. Los 208 certificados verifican que 3,003,924 de 3,774,200 membresías son `{0}` y
que caben USD 1M. El censo de hull es consecuencia directa de que
`q^(θ)−q^(0) = −γθc_g 1{1∉S}` no es constante entre préstamos.

**Contraargumento.** El registro lo llama "stopping rule". Válido como gobernanza, no como
contribución.

**Cambio mínimo suficiente.**
1. Abstract: eliminar `:31-36` y sustituir por:
   > "Making both coefficients set-native collapses the constructed cap frontier for
   > structural reasons and is reported as a boundary, not as a result."
2. Intro: eliminar `:182-191` desde "Replacing the payoff coefficient too changes the
   question" hasta "claim follows"; en `:232-236` sustituir por:
   > "A second set-native construction, which also replaces the payoff coefficient, is
   > shown to make the cap redundant by substitution (Supplement D.2.2)."
3. Teoría: eliminar Proposition 7 (`:1483-1530`) del cuerpo; conservar en D.2.2 como
   `**Remark (set-native degeneracy).**` con la misma prueba. Actualizar el test de
   proposiciones (§2.4).
4. Results: sustituir `:2021-2056` por un párrafo dentro de la sección set-native
   (`:1958-2019`), conservando ambos marcadores de claim:
   > "If the payoff coefficient is also replaced by the set-internal minimum
   > `w_i = min_{y∈S̄_i}{(1−y)r_i − y·LGD}`, every loan outside the singleton-`{0}` class
   > receives `w_i = −LGD` and `q_i = 1`, so any maximin optimizer funds only
   > singleton-`{0}` loans whenever such a full-budget allocation is feasible; the
   > constructed cap is then redundant on `[0,1]` (Supplement D.2.2). The feasibility
   > premise holds in all 208 window-by-role-month certificates over 26 candidate menus
   > using the primary CatBoost--Platt specification, reconciled from the hash-pinned
   > set-native solves without new optimization (Supplement Table S9O). This is a
   > structural boundary of the fully set-native model, not an outcome, validity, or
   > policy result."
5. Discussion `:2266-2275`: una frase. Conclusion `:2547-2555`: eliminar.
6. Fila de `tbl-claim-boundary` "Dual set-native ...": conservar.
7. Censo de hull `:1931-1956` → un párrafo:
   > "Because Proposition 5 is a statement about every allocation in a menu, we certified
   > the full-budget affine hull of all 26 role--month menus (dimension `n−1`,
   > 6,011--28,106 candidates) and evaluated the global certificate on every declared
   > score pair. It holds exactly on the 1,872 identity controls (`θ=0`, or `θ>0` with
   > `γ=0`) and fails on all 3,328 comparisons with `θ,γ>0` and on all 6,240
   > closed-calibrator pairs, as the construction `q^{(θ)}−q^{(0)} = −γθc_g 1{1∉S}`
   > predicts. Failure withholds the global certificate; it does not force an allocation
   > change at a fixed cap, and calibrator rows also change the payoff coefficient
   > (Supplement Table S9M)."

**Archivos.** Cuerpo; suplemento (D.2.2 título); registro (§Active Exact Statements punto 7
reetiquetado como remark, contenido intacto); `tests/test_ijds_v4_claim_sync.py`. Ledger:
si ambos marcadores permanecen en el cuerpo, sin cambio; si se retira alguno, quitar `body`
de `surfaces.required` del claim correspondiente y mantenerlo en `allowed`.

**Tests.** claim-sync; `test_dual_coefficient_certificate_count_names_the_repeated_unit`;
`test_body_wording_preserves_information_and_identification_boundaries`; abstract ≤300.

#### F-03 (P1) — Descomposición por clase y corolario techo ausentes

**Derivación.** `1 − Cov_res = π̂·(1 − Cov_{Y=1}) + (1 − π̂)·(1 − Cov_{Y=0})`, con
`π̂ = 56,972/364,814 = 0.156167`. CatBoost W1: `0.156167·0.716352 + 0.843833·0.013133 =
0.11187 + 0.01108 = 0.12295 = 1 − 0.877047`. Corolario (nota teórica L4 `:174-184`): si
`c_g<1/2`, `Cov_{t,g} ≤ 1 − π_{t,g} + π_{t,g}·P_t(p ≥ 1−c_g | Y=1)`; si además
`sup_{target,g} p < 1−c_g`, `Cov_{t,g} ≤ 1 − π_{t,g}`.

**Redacción propuesta (cuerpo, tras `:1220`).**
> "**Corollary 1 (low-regime coverage ceiling).** In a stratum with `c<1/2`, stratum
> coverage satisfies `Cov_t ≤ 1 − π_t + π_t·Pr_t(p ≥ 1−c | Y=1)`. If in addition every
> target score in the stratum is below `1−c`, then `Cov_t ≤ 1 − π_t`: the stratum can
> cover at most the nondefault share, whatever the calibration block promised. The
> condition is sufficient, not necessary, and it is calibration-plus-target: the phase
> margin fixes `c<1/2`, the target support fixes the second term. The ceiling is an
> identity about one fixed target distribution, not a transport statement."

**Redacción propuesta (Results, tras `:1620`).**
> "Table 3 decomposes resolved miscoverage exactly by observed class: with resolved
> prevalence 0.156167, missed defaults account for `<builder range>` of the `<builder
> range>` resolved miscoverage across the 40 cells, and missed nondefaults for the rest.
> Under Corollary 1 this is the arithmetic signature of a target prevalence above the
> calibration allowance in low-threshold strata; it is descriptive, conditions on
> resolution, and identifies no cause."

**Builder (§12.1).** Columnas derivadas de S6A: `resolved_prevalence`,
`miss_share_default`, `miss_share_nondefault`, `miss_default_fraction`; reconciliación
`|miss_share_default + miss_share_nondefault − (1 − coverage_resolved)| < 1e-12` con
excepción explícita; agregados min/max por learner en la tabla 6 y en el JSON bajo
`conformal_set_diagnostics.class_decomposition`.

**Registro/ledger/matriz.** Nuevo claim `theory.low_regime_coverage_ceiling` (theorem,
documented, lineages `[binary_geometry.outcome_free]`, surfaces required
body+supplement+registry+claim_matrix, forbidden_inference `[transport_statement,
necessity_of_target_support_condition, causal_mechanism, individual_calibration]`). Nuevo
claim `coverage.resolved_miscoverage_class_decomposition` (empirical, equals,
result_pointer `/conformal_set_diagnostics/class_decomposition/reconciles`, expected true,
forbidden_inference `[all_candidate_label_conditional_coverage, cause_of_shortfall,
learner_ranking]`). Registro: corolario en "Active Exact Statements" y viñeta en "Coverage
and Geometry Evidence". Matriz: dos filas.

**Tests.** claim-sync; `test_supplement_table_sync`; builds byte-idénticos ×2.

#### F-04 (P2) — Panel B de la Fig. 1

Con `m` por estrato entre 35k y 120k, `BB(m, n+1−r, r)` está tan concentrada que cualquier
déficit de décimas produce log-p ≈ −57; los 31/40 flags son casi tautológicos dado el
40/40. Cambio mínimo: sustituir el heatmap F/NF de `_coverage_figure` por la desviación
`(M_min/m) − (n+1−r)/(n+1)` por celda (numeradores sumados sobre estratos; datos en
S6B/S6C), con el conteo 31/40 en el pie. Alternativa: mover el Panel B a una Fig. S3.

Caption propuesto:
> "Resolved coverage (open dots) and sharp completion bounds (segments) for all 40
> learner--window cells under the six-month rule; segments are identification bounds, not
> error bars. Panel B shows, per cell, the pooled minimum strict-miss rate minus the
> finite-sample reference rate `(n+1−r)/(n+1)`; 31 of 40 cells exceed the locked nominal
> Bonferroni--Holm thresholds of the joint-block reference (Supplement B.4.1), a
> post-inspection diagnostic without FWER interpretation."

Archivos: builder `_coverage_figure`; caption `:1599`. Tests: `publication-integrity`,
`inspect_ijds_pdfs`, `test_submission_preview_layout`.

#### F-05 (P2) — Fig. 2 es una celda post-inspección

Cambio mínimo: reemplazar `_phase_figure` por un heatmap 5 learners × 8 ventanas × 5
estratos del `phase_margin` (tabla S6I), colormap divergente centrado en 0, las 87 celdas
`c<1/2` resaltadas y CatBoost S3 W8 recuadrada; panel derecho opcional con
`frozen_threshold`. La ilustración S3 actual pasa a Fig. S1 (o se fusiona con la S1
existente). El texto conserva `0.1017`, `0.0971`, `0.8884`, `0.1118`.

Caption propuesto:
> "Complete calibration-only phase census: the integer phase margin `m = D − (n−k)` for
> all 200 learner--window--ordered-stratum cells. Nonpositive margins (below-half
> thresholds) occur in 87 cells, all in the first three ordered strata (40/40/7/0/0). The
> outlined cell is the post-inspection CatBoost S3 W8 illustration discussed in the text;
> the census reads no target outcome and selects no cell."

Archivos: builder (`_phase_figure` → `_phase_census_figure`; conservar el stem
`crpto_ijds_v4_fig2_phase_transition` o registrar un nuevo stem y actualizar
`paper_artifacts`), `CRPTO_ijds.qmd:1824`, suplemento (nueva Fig. S1b). Tests:
`publication-integrity`; `test_complete_phase_path_is_visible_in_supplement`.

#### F-06 (P2) — Clase de aislamiento por linaje

Contradicción: cuerpo `:193-198`, `:713-715` vs suplemento `:730` ("A physically separate
outcome-free freeze") y `:1469-1470` ("physically isolated"). Cambio mínimo: tabla en
Apéndice F.1 (tras `:3030`) con columnas Lineage / Reads any target-period outcome before
its freeze? / Isolation class / Evaluation join, una fila por linaje activo (V4, two-ruler,
credit controls, label-Mondrian, fit-label completion, calibrator A→B→C, endpoint
availability, structure, granularity, catalog, funded estimands, V1d, hull, set-native,
phase census, dual). La clase exacta se confirma leyendo el `execution_receipt.json` de cada
linaje (flags `protected_read`/`raw_archive_read`). Reescribir `:730` ("A separate
outcome-free freeze, run under the logical target-outcome nonuse contract of Appendix F.1,
also fits 400 class-specific thresholds") y `:1469-1470` ("Target outcomes are not read by
the refits; they enter only at the keyed evaluation join, under the same nonuse
contract"). Tests: claim-sync; `test_book_active_companion`.

#### F-07 (P2) — Jerarquía teórica

Propuesta: `Proposition 1` mantener; `Proposition 2` → `**Lemma 2 (crossed-band coverage
identity).**` + `**Corollary 1 (low-regime coverage ceiling).**`; `Lemma 1` mantener;
`Proposition 3` → `**Lemma 3 (...)**`; `Proposition 4` → `**Lemma 4 (...)**`;
`Proposition 5` → `**Proposition 2 (feasible-difference score-order equivalence).**`;
`Proposition 6` → `**Corollary 2 (what comparator matching preserves).**`; `Proposition 7`
→ Remark en suplemento; `Proposition 8` → `**Lemma 5 (...)**` en Supplement D.6 con una
frase en el cuerpo. Evitar los títulos exactos prohibidos por
`test_secondary_theory_claims_remain_as_results_bridges_only`. Actualizar
`test_theory_has_two_suites_and_sequential_propositions` para exigir `Proposition 1..2`,
`Lemma 1..4` y `Corollary 1..2` secuenciales. Actualizar referencias cruzadas
("Proposition 5 states", "Proposition 6, part 4", "Proposition 4 reconciles",
"Proposition 1's conditional ...") en cuerpo, suplemento, registro (`:656-659`, `:695`,
`:735-771`) y matriz.

#### F-08 (P2) — Literatura (entradas en §8)

Añadir: `podkopaev2021labelshift` (A), `ramos2026transported_beta` (A),
`xu2026selective_crc` (B), `zhou2026audited_cp` (B); reserva: `long2026cp_wdro`,
`farzaneh2026oce_risk_control`, `braun2026conditional_coverage_diagnostics`,
`wasserstein_regularized_cp_2025`. Ubicaciones: label shift (F-01 d); Ramos et al. en el
párrafo de Marques (`:286-292`):
> "Ramos, Graziadei, and Cabezas [-@ramos2026transported_beta] quantify how test-side
> shift and calibration dependence move the realized-coverage law away from its Beta
> reference; their decomposition is the reason a flag in our joint-block diagnostic can
> reflect target-side transport, target--target dependence, or heterogeneity without
> refuting the pointwise guarantee."
Xu–Guo–Wei tras `:398`:
> "Selective conformal risk control [-@xu2026selective_crc] combines a confidence-based
> selection stage with risk control on the selected units under exchangeability; its
> selection rule is unit-level and label-free, not a budget-coupled fractional allocation."
Zhou et al. en Discussion `:2330-2336`:
> "Audited conformal prediction [-@zhou2026audited_cp] repairs an unknown shift with a
> small labeled target sample; under three-year label delay no such sample exists at the
> decision date, which is precisely the constraint this archive imposes."
Tests: `test_ijds_bibliography_views`, `test_ijds_literature_corpus_manifest` (regenerar
manifest y views), títulos de Related Work intactos.

#### F-09 (P2) — Acumulación editorial

Regla operativa: (1) en Results, una frase de frontera por subsección, al final; (2)
eliminar listas de más de tres negaciones fuera de `tbl-claim-boundary` y Limitations;
(3) Conclusion sin repetir fronteras; (4) "exact"/"sharp"/"complete" solo como
calificativos matemáticos. Aceptación: "does not"+"neither"+"not a" en el cuerpo de 150 a
≤ 90 sin perder ninguna frase exigida por tests (§2.4).

#### F-10 (P2) — Censo de hull

Ver F-02 punto 7. Tabla S9M permanece.

#### F-11 (P2, hipótesis) — Platt ≈ beta

Ver E-13. Si se confirma, añadir en Results `:1708`:
> "The beta `abm` fit reproduces the Platt map almost exactly on this block (maximum
> absolute probability difference `<value>`), which is why its sets coincide with Platt's
> in all 48 cells; the closed family therefore contains three distinct maps in effect."

#### F-12 (P2) — Átomos isotónicos

Añadir en Results `:1709`:
> "The isotonic and IVAP maps are piecewise constant, so their residual thresholds sit on
> atoms: the isotonic threshold takes only two distinct values across the eight windows,
> which is why W2--W4 and W1, W5--W7 report identical bounds. This is the atomic case
> anticipated by Lemma 2: a small change in the calibration block can leave the threshold
> unchanged or move it by a full atom."

#### F-13 (P2) — Hipótesis del corolario JOMI

Reescribir la prueba de D.1.2 (`supplement:1777-1787`): "Under joint exchangeability of the
`n+m` selection scores with almost surely no ties, the calibration indices occupy a
uniformly random `n`-subset of the combined ranks; the number of calibration ranks above
the `(m−K)`-th test order statistic is then the beta--binomial count `BB(n, K+1, m−K)` by
the same urn argument as D.1.1. The i.i.d. continuous case is a special case." Conservar
las frases exigidas por el test JOMI.

#### F-14 (P3) — Terminología JOMI

Sustituir "permutation-equivariant selection" (`CRPTO_ijds.qmd:358`; `supplement:3199`;
`ijds_pending_scientific_work_disposition_2026-08-01.md:53`) por "selection rules
invariant to permutations of the calibration units" (coincide con `:346-347` y con el
Teorema 1 de Jin–Ren).

#### F-15 a F-19 (P3)

- F-15: Fase 0.
- F-16: alinear `SKILL.md:13` tras aplicar el plan; schema de sources al siguiente cambio
  de fuentes; añadir en el registro (§Pre-Freeze Boundary): "The sealed synthetic JOMI
  lineage `protocol/ijds-equal-notional-jomi-synthetic-feasibility-2026-08-08-v1` is
  deliberately unregistered as an evidence source."
- F-17: tabla "Supplement table label → CSV file" en `paper/submission/README.md` y en el
  README del zip (S6 → `table1_coverage_windows` + `tableS6A`; S7 → `table2_phase_transition`;
  S9 → `table5_two_ruler_tracks`; ...). Renombrar CSV solo en freeze.
- F-18: frase en A.1 tras `:138`: "The 2014--2016Q1 cohorts were also excluded from
  outcome-free policy development so that no post-2013 origination informs the comparator
  supports; they remain untouched for a possible later-origin study."
- F-19: frase en F.2: "The active manifest was regenerated as a sealed-parent extension of
  commit `6e9086e`; 33 DVC sources were accepted by descriptor identity. The submission
  freeze must rebuild with every DVC byte materialized."

---

## 6. Auditoría de teoría

| Resultado | Supuestos | Corrección | Brecha | Casos borde | Literatura previa | Novedad | Ubicación | Acción |
|---|---|---|---|---|---|---|---|---|
| Prop. 1 (umbral exacto; `n−k=⌊α(n+1)⌋−1`; `c<1/2 ⇔ A+B≥k`; rama) | `p∈[0,1]`, `k≤n`; clases no vacías para la rama | Correcta; verificada con W7/W8 y `c=0.70` | Ninguna | `k=n+1`; `D=0` | Sadinle 2019 (LAC) | Modesta: margen de fase entero | Cuerpo | Añadir Corolario techo |
| Prop. 2 (bandas cruzadas) | Target fijo; `c_L<c_H` | Correcta | Ninguna | Átomos tratados | Elemental | Baja | Cuerpo como Lema | Renombrar; conectar F-12 |
| Lema 1 (fibra `[p, p+γ(1−p))`) | Intervalo contiene `p`; `0<γ≤1` | Correcta | Ninguna | `γ=0`; sup no alcanzado | No conocida así | Real | Cuerpo | Mantener |
| Prop. 3 (bounds outcome-free) | `a≥0`, `B_a>0` | Correcta, sharp | Ninguna | Sets vacíos/llenos | Trivial | Baja | Suplemento como Lema | Renombrar |
| Prop. 4 (bounds comunes; ancho) | Funcional aditivo | Correcta; hull vs conjunto no convexo bien tratado | Ninguna | Sets por política distintos declarados | Manski; Maia Polo | Aplicación con unión de soportes | Cuerpo como Lema | Renombrar |
| Prop. 5 (afín módulo `D^⊥`) | `A` convexo no vacío | Correcta (interior relativo) | Ninguna | `s\|_D=0`; cash | Álgebra elemental; Wei–Zhang | Media (uso) | Cuerpo | Mantener |
| Prop. 6 (reglas) | Presupuesto atado; `u≥p` | Correcta | Ninguna | Empates del anchor | Trivial | Baja | Corolario | Renombrar |
| Prop. 7 (colapso dual) | Presupuesto exacto; sin cash; partición; testigo `{0}` | Correcta y trivial | Ninguna | Falla con cash/LGD=0 | — | Nula | Remark | Degradar |
| Prop. 8 (endpoints por base) | Óptimo único; base fija | Correcta, condicional | Brecha declarada | Degeneración dual | Jansen et al. 1997 | Baja | Suplemento | Mover |
| Ley joint-block `BB(m, n+1−r, r)` | Exchangeability conjunta; continuidad | Correcta | Ninguna | `r=n+1` | Marques 2025 | Aplicación | Métodos | Reducir énfasis |
| Corolario JOMI `BB(n,K+1,m−K)`; gate | i.i.d. continuo | Correcta (verificada) | Puede probarse bajo exchangeability | Empates; sin reemplazo | Jin–Ren Prop. 6 y 9 | Baja; cálculo de diseño | Suplemento | Debilitar hipótesis |
| Identidad covarianza; equal-notional | Panel fijo; `A>0` | Correcta | Ninguna | `A<B` | Elemental | Baja | Suplemento | Mantener |
| Frontera CDF (D.5.1) | CDF calibración fija | Correcta | Ninguna | — | — | Baja-media | Suplemento | Mantener |
| Catálogo monótono (D.5.3) | Monotonía; sin `{1}` | Correcta; gate necesario | Ninguna | — | — | Baja | Suplemento | Mantener |

Contraejemplos confirmados: no-interleaving sin `c<1/2`; ranking preservado sin
invariancia; sets iguales con asignaciones distintas; cuadrado vs triángulo con `v=(1,0)`.

---

## 7. Auditoría de claims y números

**Bien soportados (recalculados o reconciliados con el JSON).** 640,543 = suma exacta de
los seis bloques (17,433 + 14,101 + 49,007 + 94,885 + 376,890 + 88,227); 376,890 = 364,814
+ 12,076; taxonomía 307,842/56,972/11,551/47/478; 40/40 con máximo 0.897726 (23 pb); 64/64
taxonomías (máx 0.897294); extensión 8/8 y 2/8 (máx 0.908928); AvgC 1.128128–1.268134,
vacíos 0.67–1.61%, dos etiquetas 14.42–27.48%, singletons 71.85–83.97%; 31/40 =
8+4+8+6+5; 18/32 = 8+8+1+1 con extremos exactos; brecha marginal y prevalencia
[0.151163, 0.183205], ancho 0.032041; residual 158/8/34 y 2,140/488/372; censo de fase 87 =
40+40+7, 184, 188; W7/W8; `−281/76,495`, `[−312,−290]/79,047`; 175 = 122+48+5; 35 = 31+4;
V1d 9,659/11,520 (83.85%); hull 1,872 = 1,040+832 y 6,240; set-native 1,200 y 18,000;
208 = 88+120; two-ruler 32/16, 33/15, 40/8; ancho USD 14,738; objetivo normalizado
28,263–557,294; catálogo 0.014413/0.009545/0.006825; fundados 96/96, 80/96,
0.008537/0.008534; estructura 1,728; granularidad 0.001284 pp; CRC 0.342/0.292/129; 45
tablas; abstract 292 palabras.

**Sobre-enunciados.** Ninguno numérico. Cualitativos: F-02; el "no mechanism identified"
repetido cuando la aritmética por clase ya está (F-01/F-03).

**Ambiguos.** Aislamiento físico vs lógico (F-06); "permutation-equivariant" (F-14);
"four maps" con dos idénticos en todas las celdas (F-11).

**Denominadores/unidades.** Consistentes; S2 mezcla métricas sobre 364,814 con bounds sobre
376,890, declarado en el pie; S9F reporta proporciones y el texto pp, declarado.

**Conflictos entre superficies.** PDFs desfasados (F-15); numeración S6/S7/S9 (F-17);
fechas de autoridad (F-16). El resto reconcilia en todo número material comprobado.

**Resultados valiosos enterrados.** Prevalencia 2011 vs OOT vs extensión; descomposición
por clase; corolario techo; átomos isotónicos; retraso de etiquetas como causa estructural
de la brecha.

**Debilitar/mover/eliminar.** Prop. 7 → remark; hull → párrafo; fórmula JOMI en Discussion
→ display compacto con prosa mínima (el test exige el display); Panel B y Fig. 2 →
suplemento o rediseño; negaciones repetidas → `tbl-claim-boundary`.

---

## 8. Estado del arte

| Familia | Vecino | Qué garantiza | Supuestos | Relación con CRPTO | Acción |
|---|---|---|---|---|---|
| Calibración de probabilidad | Platt; Zadrozny–Elkan; Kull; Vovk–Petej; van der Laan–Alaa; Dabah–Tirer | Mapa escalar / par Venn | Datos de ajuste | Correcto; falta explicar Platt≈beta | Mantener; F-11 |
| Membresía conformal | Vovk 2005; Angelopoulos–Bates; Barber 2021; Duchi 2025; Sadinle 2019 | Cobertura marginal | Exchangeability | Correcto | Mantener |
| Dependencia/lote | Marques 2025; Barber–Pananjady ALT 2026; Gazin 2025; **Ramos et al. 2605.19024** | Ley beta-binomial; pérdida bajo mixing; desviaciones Wasserstein de la ley Beta | i.i.d.; estacionariedad | Ramos et al. es el vecino más cercano al diagnóstico joint-block | Añadir A |
| Transporte | Tibshirani 2019; Barber 2023; Oliveira 2024; Gibbs–Candès 2024; Yang–Jin ICML 2026; feedback shift | Cobertura con ratio / penalización | Ratio conocido; familia declarada | Falta label shift: **Podkopaev–Ramdas 2021** | Añadir A; reserva Wasserstein-regularized CP (ICLR 2025); **Zhou et al. 2606.14909** como diseño B |
| Selección / FCR | Benjamini–Yekutieli; Bao 2024; Jin–Ren 2025; Gazin informative; Zheng–Jin | Cobertura condicional; FCR ≤ α | Exchangeability; invariancia a permutaciones de calibración | Correcto; F-14; **Xu–Guo–Wei 2512.12844** omitido | Añadir B |
| Selección de predictor/set | Yang–Kuchibhotla; Hegazy; Liang–Zhu–Barber | Cobertura tras selección | Split/estabilidad | Correcto | Mantener |
| Diagnóstico condicional | **Braun et al. 2512.11779 v2** | Métrica ERT | Muestra etiquetada | Relevante al diagnóstico por etiqueta | Reserva |
| Decisión / CRC / LTT | Zhao 2021; Angelopoulos 2024/25/26; Aldirawi v2; Joshi; CPC; Zhu | Riesgo esperado | Contextos exchangeable | Correcto; **Farzaneh–Simeone 2608.28179** nuevo | Reserva |
| PtO / RO conformal | Johnstone–Cox; Sun; Patel; Chenreddy; Yeh; Chen 2026; Ovalle; Zhao CPP; Im; Birbil–Chi; **Long et al. 2608.29789**; Patel–Tewari 2602.08215 | Región/feasibilidad; certificado local | Recalibración; base única | Correcto | Reserva Long; excluir Patel–Tewari |
| Portafolio | Kato v2 | Cobertura aproximada por portafolio fijo | Ergodicidad aprox. | Correcto | Mantener |
| Crédito / censura | Lessmann; Serrano; Li 2023; Djeundje; Peng–Lessmann v2; Lakkaraju; Kleinberg; Candès 2023; Gui 2024 | — | — | Correcto | Mantener |

Usados correctamente: casi todo el corpus; ninguna versión pendiente entre las
comprobadas. Incompletos: Jin–Ren (terminología). Omitidos que cambian el posicionamiento:
Podkopaev–Ramdas; Ramos et al. No añadir: Patel–Tewari; "Conformal Kelly"; UP-OCP; crédito
sin objeto conformal.

**Borradores BibTeX (verificar campos marcados VERIFY en la fuente primaria antes de
commit; intake en `Papers_tesis/supplement` con SHA-256 y receipt en el ledger de
literatura):**

```bibtex
@inproceedings{podkopaev2021labelshift,
  author    = {Podkopaev, Aleksandr and Ramdas, Aaditya},
  title     = {Distribution-Free Uncertainty Quantification for Classification under Label Shift},
  booktitle = {Proceedings of the 37th Conference on Uncertainty in Artificial Intelligence},
  series    = {Proceedings of Machine Learning Research},
  volume    = {161},
  year      = {2021},
  note      = {VERIFY volume/pages on PMLR; arXiv:2103.03323v4},
  url       = {https://arxiv.org/abs/2103.03323v4}
}
@article{ramos2026transported_beta,
  author  = {Ramos, Thiago R. and Graziadei, Helton and Cabezas, Luben M. C.},
  title   = {Conformal Prediction via Transported Beta Laws},
  journal = {arXiv preprint arXiv:2605.19024},
  year    = {2026},
  note    = {Version 1, submitted May 18, 2026},
  url     = {https://arxiv.org/abs/2605.19024v1}
}
@article{xu2026selective_crc,
  author  = {Xu, Yunpeng and Guo, Wenge and Wei, Zhi},
  title   = {Selective Conformal Risk Control},
  journal = {arXiv preprint arXiv:2512.12844},
  year    = {2026},
  note    = {Version 2, revised April 27, 2026},
  url     = {https://arxiv.org/abs/2512.12844v2}
}
@article{zhou2026audited_cp,
  author  = {Zhou, Yanfei and Fathony, Rizal and Nguyen, Nam H. and Sesia, Matteo},
  title   = {Audited Conformal Prediction for Classification under Unknown Distribution Shift},
  journal = {arXiv preprint arXiv:2606.14909},
  year    = {2026},
  note    = {Version 1, submitted June 12, 2026},
  url     = {https://arxiv.org/abs/2606.14909v1}
}
@article{long2026cp_wdro,
  author  = {Long, Kehan and Zhao, Yiqi and Mestres, Pol and Lindemann, Lars and Atanasov, Nikolay and Cort{\'e}s, Jorge},
  title   = {A Unified Perspective on Conformal Prediction and Wasserstein Distributionally Robust Optimization for Uncertainty Quantification},
  journal = {arXiv preprint arXiv:2608.29789},
  year    = {2026},
  note    = {Version 1, submitted August 30, 2026; reserve},
  url     = {https://arxiv.org/abs/2608.29789v1}
}
@article{farzaneh2026oce_risk_control,
  author  = {Farzaneh, Amirmohammad and Simeone, Osvaldo},
  title   = {Conformal Risk-Averse Decision Making with Optimized Certainty Equivalent Risk Control},
  journal = {arXiv preprint arXiv:2608.28179},
  year    = {2026},
  note    = {Version 1, submitted August 28, 2026; reserve},
  url     = {https://arxiv.org/abs/2608.28179v1}
}
@article{braun2026conditional_coverage_diagnostics,
  author  = {Braun, Sacha and Holzm{\"u}ller, David and Jordan, Michael I. and Bach, Francis},
  title   = {Conditional Coverage Diagnostics for Conformal Prediction},
  journal = {arXiv preprint arXiv:2512.11779},
  year    = {2026},
  note    = {Version 2, revised May 29, 2026; reserve},
  url     = {https://arxiv.org/abs/2512.11779v2}
}
```

**Novedad defendible (inglés).**
> "CRPTO's contribution is an identification audit of the handoff from a binary
> split-conformal set to a linear allocation program under label delay and partially
> observed outcomes. Its new elements are (i) the exact finite-sample geometry of the
> binary absolute-residual threshold as an order statistic of two mirror samples, with the
> crossed-band coverage identity and a prevalence ceiling; (ii) the proof that a binary set
> identifies only boundary contact, so any continuous embedding used as an LP coefficient
> lies in an unidentified half-open fibre, together with the exact criterion---positive-
> affine equivalence modulo the orthogonal complement of feasible allocation
> differences---for two scores to induce identical allocation orderings; and (iii) sharp
> common-completion identification bounds that carry 12,076 unresolved outcomes through
> candidate coverage, adjacent-threshold responses, paired policy contrasts, and count-,
> dollar-, and fixed-capital funded estimands. No prior work performs this audit; the
> elementary ingredients are known and are cited as such."

---

## 9. Narrativa, estructura y presentación

**Abstract.** Pregunta → objeto (label-delayed binary conformal set as LP coefficient) →
tres contribuciones → 40/40 con regla de seis meses y prevalencia identificada → 18/32 →
frontera en una frase. Retirar Prop. 7 y los 208 certificados; 9,659/11,520 a Results o
frase cualitativa. Mantener ≤300 palabras.

**Introduction.** Handoff; hecho estructural del retraso de etiquetas; qué se prueba y qué
se diagnostica; tres contribuciones. Sin enumeración de censos.

**Related Work.** Mantener los seis títulos (test); añadir label shift dentro de
"Conformal membership and temporal transport"; mantener la tabla de objetos calibrados.

**Theory.** Suite 1: Prop. 1, Lema 2 + Corolario 1, Lema 1, Lemas 3–4. Suite 2: Prop. 2
(ex 5) + tres préstamos + Corolario 2. Remarks al suplemento.

**Methods.** Añadir tabla de notación (`p, c_g, S_i, [ℓ,u], q(γ), θ, τ, ρ, η, m`) y clase
de aislamiento por linaje.

**Results.** (1) 40/40 + descomposición por clase + Corolario 1 (Fig. 1 rediseñada); (2)
censo de fase (nueva Fig. 2) y respuesta común; (3) calibradores con nota de átomos; (4)
marginal y frontera en un bloque; (5) V1d + párrafo de hull; (6) set-native + párrafo dual;
(7) two-ruler, catálogo, fundados, estructura, caps. Una frase de frontera por subsección.

**Discussion.** Qué está identificado; qué no; qué diseño lo resolvería (recalibración
label-shift-aware con priors target estimables; fixed-K JOMI; LTT con ≥129 contextos). JOMI
en un párrafo con el display exigido por el test y remisión al suplemento.

**Supplement.** Añadir tabla de aislamiento (F.1), crosswalk de numeración, Remark
set-native (D.2.2), prueba JOMI por rangos (D.1.2), nueva Fig. S1b.

**Título (opcional).** "Auditing the Handoff from Binary Conformal Sets to Credit
Allocation: Exact Geometry, Label-Delayed Transport, and Comparator Dependence".

**Contribución en una frase.**
> "We show, exactly and on a complete finite archive, what a nominal-90% binary conformal
> set does and does not identify once it becomes a credit-allocation coefficient under
> three-year label delay: it identifies boundary contact and a prevalence-driven coverage
> ceiling, but not the continuous coefficient, the allocation ordering, or funded-set
> validity."

**Párrafo de posicionamiento.**
> "Existing conformal-optimization work either learns a decision-aware uncertainty region
> with its own recalibration contract or certifies coverage for a selected unit under a
> declared selection rule. CRPTO audits the opposite direction: a frozen marginal binary
> set is lifted to a continuous coefficient and consumed by a budget-coupled LP whose
> outcomes resolve only years later. We prove which properties survive each handoff, bound
> what the archive leaves unresolved, and report every cell of each declared family
> without selecting a favorable one. The paper therefore claims no method, no winner, and
> no repair; it claims an exact map of what is identified."

**Claim-boundary card (fila sustituta).**
> "Marginal score and default prevalence --- May conclude: a sharp finite-archive interval
> for mean score minus prevalence and an exact class decomposition of resolved
> miscoverage, consistent with an increase in default prevalence between calibration and
> target. Does not pass: individual calibration, a decomposition of label from covariate
> shift, or a causal mechanism."

**Orden de figuras/tablas.** Fig. 1 cobertura + descomposición; Fig. 2 heatmap del censo de
fase; Fig. 3 respuesta común; Fig. 4 envolventes (opcional en cuerpo); S3 → Fig. S1b.
Tablas del cuerpo: protocolo; roles Mondrian; controles de crédito con columnas por clase;
calibradores; censo de fase; dirección embedding; set-native; two-ruler; catálogo; claim
boundary.

---

## 10. Experimentos y extensiones

| Estudio | Pregunta | Datos | Diseño mínimo | Valor | Riesgo | GO/NO-GO | Prioridad |
|---|---|---|---|---|---|---|---|
| E-1 Descomposición por clase y Corolario 1 en 40 celdas | ¿Qué fracción exacta de la miscobertura proviene de defaults perdidos? | S6A/S6C registradas | Columnas derivadas en el builder | Alto | Nulo | GO ahora | 1 |
| E-2 Bounds sharp por clase para todos los candidatos | ¿Cambia 0.98/0.23–0.36 al acotar los 12,076 no resueltos? | Sets V5 + panel de outcomes | Protocolo + tag; solo evaluación | Medio-alto | Bajo | GO con protocolo | 2 |
| E-3 JOMI equal-notional fixed-K real | Cobertura condicional a selección con FCP conteo = dólar | Cohorte no inspeccionada o fuente externa | D1; gate `P(R≥9)` | Muy alto | Sin datos | NO-GO hasta datos; GO como diseño | 3 |
| E-4 Recalibración label-shift-aware | ¿Priors target estimables corrigen la brecha? | Covariables target en decisión | Solo diseño | Alto | Post-hoc en el archivo | NO-GO como corrida; GO como fila de G.1 | 4 |
| E-5 FCR ponderada por exposición | `FCP^$ ≤ κ FCP^N` | Tras E-3 | κ predeclarado | Medio | Depende de E-3 | NO-GO hasta E-3 | 6 |
| E-6 CRC/LTT mensual | Control de riesgo por contexto | ≥129 contextos o catálogo + LTT | Ruta antes de outcomes | Alto | 11–15 contextos: vacuo | NO-GO en archivo | 5 |
| E-7 Réplica externa V2 | ¿Recurre la geometría? | Fuente verificada | Protocolo honesto | Medio | Derechos | Condicional | 7 |
| E-8 Cota de transporte temporal | Penalización teorema-compatible | Fresca | Track A/B | Prerequisito | No estimable | GO como diseño | 3 |
| E-9 Cohorte prospectiva | Confirmación | No disponible | — | Muy alto | Sin datos | NO-GO | — |
| E-10 Modelo constraint-native | Nuevo método | — | Teorema propio | Alto, otro paper | Alcance | Diferir | — |
| E-11 Action-conditional | Nuevo objeto | — | Acciones discretas | Medio | No aplica a LP fraccional | Diferir | — |
| E-12 Cara óptima del LP viejo | Unicidad | Existente | Paramétrico exacto | Bajo | Degeneración | NO-GO (N6) | — |
| E-13 Parámetros beta vs Platt | ¿El beta colapsa a Platt? | `calibrator_family.pkl` | Lectura de artefacto | Bajo-medio | Nulo | GO ahora | 8 |

### 10.1 Borrador de protocolo E-2: bounds sharp de cobertura por clase para todos los candidatos

- **Nombre y tags.** Run tag `ijds-class-conditional-sharp-coverage-2026-MM-DD-v1`;
  protocolo `protocol/ijds-class-conditional-sharp-coverage-2026-MM-DD-v1`; artefacto
  `artifacts/ijds-class-conditional-sharp-coverage-2026-MM-DD-v1` (direct child).
- **Pregunta.** Para cada una de las 40 celdas learner×ventana (y las 200 celdas por
  estrato), ¿cuáles son los bounds sharp de cobertura condicional a la clase observada,
  `[A_y/(B_y+U_y^0), (A_y+U_y^1)/(B_y+U_y^1)]`, cuando los 12,076 no resueltos se completan
  loan-wise, y cuáles los bounds del gap `C_0−C_1` con completación compartida?
- **Estimando.** Cobertura por clase sobre todos los candidatos (ratio), no sobre el panel
  resuelto; identificación finita, no inferencia.
- **Insumos.** Sets binarios congelados V5 por learner/ventana (fuente V5 registrada), panel
  de outcomes con la regla de seis meses (misma tabla que la evaluación V5). Sin lectura
  del archivo crudo; sin optimización.
- **Implementación.** Reutilizar `sharp_class_coverage_ratio_bounds` y
  `sharp_class_coverage_gap_bounds` de `src/ijds_audit/label_mondrian.py` (:357, :429)
  aplicadas a los sets baseline; nuevo runner `scripts/experiments/run_ijds_class_conditional_sharp_coverage_v1.py`;
  módulo `src/ijds_audit/class_conditional_sharp_coverage.py`; excepciones explícitas.
- **Reporte completo.** 40 celdas × 2 clases + 200 celdas × 2 clases + 40 gaps; sin
  selección; reconciliar `coverage_resolved_y0/y1` con S6A a `1e-12`.
- **Stop rules.** Detener si alguna celda tiene `B_y=0`; si la reconciliación falla; si el
  protocolo no está commiteado y taggeado antes de correr.
- **Claim permitido si pasa.** "Sharp all-candidate class-conditional coverage bounds for
  the baseline sets are [ranges]; they replace the resolved-only descriptive columns and
  remain identification diagnostics, not label-conditional validity."
- **Claim si falla o cruza.** Reportar tal cual; no elimina el caveat de resolución en las
  columnas resueltas existentes.
- **Coste.** Minutos; sin runtime contract especial (< 30 min).
- **Registro.** Nueva entrada en `configs/ijds_active_evidence_sources.yaml` (Git-native
  direct child), claim nuevo en ledger, viñeta en registro, fila en matriz, tabla nueva del
  builder (`tableS6Q`).

### 10.2 Borrador E-13: casi-identidad Platt–beta

- Lectura de `models/experiments/ijds_audit/ijds-calibrator-sensitivity-2026-07-30-v1-source/prediction/calibrator_family.pkl`
  y `data/processed/.../prediction/outcome_free_geometry.parquet` (ya registrados; sin
  nueva optimización).
- Emitir: parámetros `a,b,m` del beta, `max_i |p_beta,i − p_platt,i|` sobre 376,890
  candidatos, número de candidatos cuyo estrato o set cambiaría (esperado 0).
- Si `max |Δp| < 1e-3` (umbral a declarar antes de leer), añadir la frase de F-11 al
  cuerpo; emitir el valor por el builder como campo del manifiesto
  (`sensitivity.calibrator_family.beta_platt_max_abs_difference`).
- Sin protocolo pesado: es lectura de artefacto registrado; registrar en el receipt del
  builder y en el registro como diagnóstico descriptivo.

---

## 11. Plan de implementación dependiente de orden

### Fase 0 — Cierre de superficie (sin nueva evidencia)

- **Objetivo.** Árbol limpio y superficies sincronizadas.
- **Decisiones previas.** Ninguna.
- **Archivos.** `paper/CRPTO_ijds.qmd`, `paper/supplement_ijds.qmd`,
  `paper/submission/CRPTO_ijds_submission.tex` (regenerado), `book/chapters/06-blueprint-manuscrito.qmd`.
- **Tareas.** (1) F-06: tabla de aislamiento en F.1; corregir `supplement:730` y
  `:1469-1470`. (2) `uv run python scripts/build_ijds_submission_tex.py` y luego `--check`.
  (3) `just paper-body paper-supplement paper-official` (o `paper-official-windows`).
- **Checks.** `just paper-tex-check`; `uv run pytest tests/test_ijds_active_claim_sync.py
  tests/test_book_active_companion.py tests/test_inspect_ijds_pdfs.py -q`.
- **Aceptación.** Los PDFs contienen "information-boundary audit"; `git status` limpio tras
  commit.
- **Stop.** Cualquier test rojo.
- **Riesgo de regresión.** Nulo.
- **Commit.** `paper: reconcile physical-vs-logical isolation wording and rebuild surfaces`.

### Fase 1 — Teoría (depende de 0) ∥ Fase 4

- **Objetivo.** Jerarquía y corolario.
- **Decisión previa.** Aprobar renombrado (F-07) y degradación de Prop. 7 (F-02).
- **Archivos.** Cuerpo §Theory; suplemento B.5, D.1.2, D.2.2, D.6; registro §Active Exact
  Statements; ledger (`theory.low_regime_coverage_ceiling`; `surfaces` del dual si aplica);
  matriz; `tests/test_ijds_v4_claim_sync.py`.
- **Tareas.** Corolario 1; renombres; Remark set-native; prueba JOMI por rangos (F-13);
  "calibration-permutation-invariant" (F-14); actualizar aserción de proposiciones;
  actualizar referencias cruzadas.
- **Checks.** Lectura de la prueba del corolario (dos líneas); claim-sync; `paper-tex-check`.
- **Aceptación.** Ningún claim pierde superficie requerida; tests verdes.
- **Stop.** Marcador de claim huérfano.
- **Commit.** `paper: theory hierarchy, coverage ceiling corollary, JOMI proof under exchangeability`.

### Fase 2 — Claims y números (depende de 1)

- **Objetivo.** F-01 numérico y F-03.
- **Archivos.** `scripts/build_ijds_binary_geometry_frontier_v4_evidence.py` (columnas
  derivadas §12.1; campos de prevalencia 2011/extensión), JSON regenerado, tablas 6 y S6A,
  registro, ledger, matriz, cuerpo Data/Results.
- **Tareas.** Implementar columnas y reconciliación; regenerar dos veces en staging
  (`--stage-only` y `--promote-from-stage`, ver `.codex/skills/crpto/SKILL.md`); comparar
  hashes; añadir claims; redactar frases con los rangos emitidos.
- **Checks.** `just publication-integrity`; claim-sync; `test_supplement_table_sync`.
  `drift-gate` no requerido (sin cambio PD/conformal).
- **Aceptación.** Builds byte-idénticos; números del cuerpo trazables al JSON.
- **Stop.** Si el builder exige materializar DVC ausente, documentar como F-19 y no
  fabricar.
- **Commit.** `evidence: class decomposition of resolved miscoverage and calibration-target prevalence contrast`.

### Fase 3 — Narrativa (depende de 1–2) ∥ Fase 5

- **Objetivo.** F-01 texto, F-02, F-09, F-10, F-12, F-18.
- **Archivos.** Cuerpo (Abstract, Intro, Data, Related Work, Results, Discussion,
  Conclusion); suplemento A.1.
- **Checks.** Abstract ≤300 palabras; `test_manuscript_surfaces_share_v4_claims...`;
  `test_v4_wording_keeps_theory_and_empirical_scope_separate`; conteo de negaciones ≤ 90.
- **Aceptación.** Tests verdes; lectura completa sin listas duplicadas.
- **Commit.** `paper: label-delay framing, label-shift positioning, demote trivial results`.

### Fase 4 — Literatura (depende de 0) ∥ Fase 1

- **Archivos.** `paper/references.bib`; `docs/research/ijds_literature_corpus_ledger_2026-07-30.md`;
  `configs/ijds_literature_corpus_manifest.json` (regenerar con
  `scripts/build_ijds_literature_corpus_manifest.py`); views con
  `scripts/build_ijds_bibliography_views.py`; PDFs en `Papers_tesis/supplement` con SHA-256.
- **Tareas.** Intake de Podkopaev–Ramdas (verificar PMLR 161), Ramos et al. v1, Xu–Guo–Wei
  v2, Zhou et al. v1 (A/B); reserva Long, Farzaneh–Simeone, Braun, Wasserstein-regularized
  CP.
- **Checks.** `test_ijds_bibliography_views`, `test_ijds_literature_corpus_manifest`.
- **Commit.** `docs(literature): label-shift, transported-beta, selective-CRC neighbors`.

### Fase 5 — Figuras y tablas (depende de 2)

- **Tareas.** Fig. 1 Panel B (F-04); Fig. 2 heatmap (F-05); S3 → Fig. S1b; columnas por
  clase en `tbl-credit-controls`; crosswalk S6/S7/S9 en `paper/submission/README.md`
  (F-17).
- **Checks.** `inspect_ijds_pdfs`; `test_submission_preview_layout`;
  `test_complete_phase_path_is_visible_in_supplement`.
- **Commit.** `figures: census-first phase figure and standardized joint-block departures`.

### Fase 6 — Experimentos (decisión del autor)

- E-13 primero (lectura de artefacto). E-2 solo con protocolo commiteado y taggeado antes
  de correr, registro en fuentes, claim en ledger, tabla nueva en builder.
- **Gates.** Protocolo antes de la corrida; reporte completo; sin selección; receipt.
- **Commits.** `research: lock class-conditional sharp coverage V1`; `research: seal ...`.

### Fase 7 — Validación final y gobernanza

- `uv sync --group dev --locked`; `just test`; `just lint`; `just type-check`;
  `just type-check-fast`; `just publication-integrity`; `just ijds-active-check`;
  `just validate-champion`; `just submission-build`; `just submission-check`; inspección
  visual de los tres PDFs.
- F-16: alinear fechas (`SKILL.md`, registro, ledger schema si cambió, sources si cambió);
  nota de no registro del run JOMI sintético.
- En freeze (fuera de alcance ahora): `just ijds-pull`; `just ijds-active-dvc-tests`;
  re-materializar F-19; renombrar CSV (F-17); anonimato; derechos.

---

## 12. Especificaciones técnicas

### 12.1 Columnas derivadas en el builder (Fase 2)

En el módulo que emite `crpto_ijds_v4_tableS6A_conformal_set_diagnostics.csv` (fuente
`src/ijds_audit/conformal_set_diagnostics.py::build_conformal_set_diagnostics` :23 y
`conformal_set_diagnostic_ranges` :258), añadir por fila:

```
resolved_prevalence      = resolved_y1_rows / resolved_rows
miss_share_default       = resolved_prevalence * (1 - coverage_resolved_y1)
miss_share_nondefault    = (1 - resolved_prevalence) * (1 - coverage_resolved_y0)
miss_default_fraction    = miss_share_default / (miss_share_default + miss_share_nondefault)
```

Guardas (excepciones, no `assert`): `resolved_rows > 0`; `|miss_share_default +
miss_share_nondefault - (1 - coverage_resolved)| <= 1e-12`; `0 <= miss_default_fraction <=
1`. Agregados en `conformal_set_diagnostic_ranges`: por learner min/max de las cuatro
columnas; global. Exponer en el JSON bajo `conformal_set_diagnostics.class_decomposition`
con `reconciles: true`. Añadir a `crpto_ijds_v4_table6_credit_controls.csv` las columnas
`miss_default_fraction_min` y `miss_default_fraction_max`.

Campos nuevos del manifiesto para F-01(b): `credit_risk_controls.calibration_block_default_rate`
(0.104781, del artefacto de calibración 2011 ya registrado) y
`closed_coverage_diagnostics.extension_resolved_default_rate` (0.196438). Si el builder no
tiene acceso a esas fuentes sin materializar DVC, mantener los números solo en el suplemento
(donde ya están) y no citarlos en el cuerpo.

### 12.2 Figuras

- `_coverage_figure` (:1310): Panel B toma `exchangeability_cells` (S6B) y `exchangeability_strata`
  (S6C). Nueva métrica por celda: `sum_g M_min,g / sum_g m_g − sum_g m_g·(n_g+1−r_g)/(n_g+1) /
  sum_g m_g`. Colormap secuencial; anotar "F" solo como texto pequeño; pie con 31/40.
- `_phase_figure` (:1512) → `_phase_census_figure(census: pd.DataFrame)`: entrada
  `crpto_ijds_v4_tableS6I_binary_phase_census.csv`; `require_exact_grid` sobre
  `learner × window_id × conformal_group` (200); heatmap de `phase_margin` con
  `TwoSlopeNorm(vcenter=0)`; recuadro en `(catboost_platt, w08_2012m08_2013m01, 2)`;
  etiquetas de estrato lector `s = conformal_group + 1`. Conservar el stem
  `crpto_ijds_v4_fig2_phase_transition` para no alterar `paper_artifacts`, o registrar
  `crpto_ijds_v4_fig2_phase_census` y actualizar los descriptores y tests.
- La ilustración S3 se mueve a un nuevo panel de la Fig. S1 (`_common_panel_threshold_response_census_figure`)
  o a una Fig. S1b con el código actual de `_phase_figure`.

### 12.3 Ledger: plantilla de claims nuevos

```yaml
  - id: theory.low_regime_coverage_ceiling
    status: active
    kind: theorem
    rule: documented
    lineages: [binary_geometry.outcome_free]
    scope: stratum_with_below_half_threshold_on_one_fixed_target_distribution_with_optional_target_support_condition
    forbidden_inference:
      [transport_statement, necessity_of_target_support_condition,
       causal_mechanism, individual_calibration, label_shift_identified_as_cause]
    surfaces:
      required: [body, supplement, registry, claim_matrix]
      allowed: [body, supplement, registry, claim_matrix]

  - id: coverage.resolved_miscoverage_class_decomposition
    status: active
    kind: empirical
    rule: equals
    result_pointer: /conformal_set_diagnostics/class_decomposition/reconciles
    expected: true
    lineages: [credit_controls.evaluation, conformal_set_diagnostics]
    scope: resolved_primary_oot_panel_all_five_learners_all_eight_windows_exact_class_decomposition
    forbidden_inference:
      [all_candidate_label_conditional_coverage, cause_of_shortfall,
       learner_ranking, label_shift_identified_as_cause]
    surfaces:
      required: [body, supplement, registry, claim_matrix]
      allowed: [body, supplement, registry, claim_matrix]
```

---

## 13. Preservar, recuperar, abandonar, diferir

**Preservar sin cambios:** protocolos sellados y tags; números registrados; Lema 1, Prop.
1, Prop. 5 y contraejemplos; contabilidad loan-wise; regla de primer uso "six-month
outcome-availability rule"; tabla de objetos calibrados; Tablas S12A–S12C; no selección;
separación cinco learners vs sensibilidades CatBoost.

**Recuperar:** corolario techo (nota teórica L4); remark "empty set requires `c<p<1−c`"
(nota L3); prevalencias de B.2 al cuerpo; el argumento de retraso de etiquetas.

**Abandonar:** Prop. 7 como proposición del cuerpo y del abstract; el censo de hull como
sección propia; la prosa extensa JOMI en la Discussion del cuerpo (mantener solo el display
exigido); cualquier retorno a Venn seleccionado, pool93, 45/45, external V1; densificación
de caps del LP viejo.

**Diferir a freeze:** compresión de páginas (25 pre-referencias); anonimato de tags/hashes;
renombrado de CSV; re-materialización DVC completa; derechos y licencias.

---

## 14. Top 10 acciones (valor científico / coste / riesgo)

1. F-01 texto (retraso de etiquetas, prevalencias, label shift consistente, Podkopaev–Ramdas).
2. F-03 Corolario 1 y descomposición por clase (E-1).
3. F-02 degradar Prop. 7 y comprimir hull.
4. F-07 jerarquía teórica.
5. F-08 literatura (Ramos et al.; Xu–Guo–Wei; Zhou et al.).
6. F-05 Fig. 2 → censo.
7. F-04 Fig. 1 Panel B.
8. F-09 pasada editorial.
9. E-2 bounds por clase para todos los candidatos.
10. F-06 y F-15 sincronización de aislamiento y PDFs.

---

## 15. Preguntas abiertas

1. ¿Acepta el autor nombrar label shift como mecanismo consistente, no inferido
   causalmente, y añadir el corolario techo? Cambia Fases 1–3.
2. ¿Se autoriza E-2 antes del freeze? Cambia Fase 6 y una fila de la claim card.
3. ¿Prop. 7 se degrada a remark o se mantiene con menos huella? Cambia el ledger.
4. ¿Se verifica el venue exacto de Podkopaev–Ramdas antes de citar?
5. ¿Título actual o propuesto?

---

## 16. Handoff operativo y checklist final

- **P1 inmediatos:** F-01, F-02, F-03. Ninguno requiere evidencia empírica nueva; F-03
  requiere columnas derivadas en el builder.
- **Secuencia:** Fase 0 → Fase 1 ∥ Fase 4 → Fase 2 → Fase 3 ∥ Fase 5 → Fase 6 (si se
  autoriza) → Fase 7.
- **Archivos exactos:** `paper/CRPTO_ijds.qmd`; `paper/supplement_ijds.qmd`;
  `docs/research/active_claims_2026-07-14.md`; `configs/ijds_claim_ledger.yaml`;
  `paper/submission/CLAIM_AUDIT_MATRIX.md`; `paper/references.bib`;
  `docs/research/ijds_literature_corpus_ledger_2026-07-30.md`;
  `configs/ijds_literature_corpus_manifest.json`;
  `scripts/build_ijds_binary_geometry_frontier_v4_evidence.py`;
  `reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json` (regenerado);
  `tests/test_ijds_v4_claim_sync.py`; `paper/submission/README.md`;
  `.codex/skills/crpto/SKILL.md`; PDFs regenerados.
- **Gates:** `build_ijds_submission_tex.py --check`; `just test`; `just lint`;
  `just type-check`; `just type-check-fast`; `just publication-integrity`;
  `just ijds-active-check`; `just validate-champion`; `just submission-build`;
  `just submission-check`; builds byte-idénticos ×2; inspección visual.
- **Prohibido:** editar TeX generado a mano; ejecutar etapas protegidas; modificar
  `EXTRACTION_MANIFEST.json` o protocolos sellados; `assert` como guarda; inferir
  causalidad, ranking o validez fundada; corridas sobre el grid inspeccionado sin protocolo
  y tag nuevos; copiar números a mano fuera del builder; relajar tests para pasar.
- **Decisiones no resueltas:** las cinco de §15.

**Checklist de cierre por fase.**

- [ ] Fase 0: tabla de aislamiento; TeX regenerado; PDFs recompilados; tests verdes; commit.
- [ ] Fase 1: Corolario 1; renombres; Remark; prueba JOMI; test de proposiciones
      actualizado; referencias cruzadas; commit.
- [ ] Fase 2: columnas derivadas; builds byte-idénticos; claims nuevos en ledger/registro/
      matriz; commit.
- [ ] Fase 3: abstract ≤300; label delay; prevalencias; label shift; Prop. 7 y hull
      comprimidos; negaciones ≤90; commit.
- [ ] Fase 4: cuatro claves nuevas + reservas; manifest y views regenerados; commit.
- [ ] Fase 5: Fig. 1 y Fig. 2 rediseñadas; S1b; crosswalk; commit.
- [ ] Fase 6 (opcional): E-13; E-2 con protocolo y tag.
- [ ] Fase 7: gates completos; fechas alineadas; nota de no registro del run sintético.
