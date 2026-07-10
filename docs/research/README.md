# paper-crpto — Research Dossier

Notas de investigación y registros que aún tienen valor de consulta para el
paper y la tesis. Las auditorías, backlogs y checklists puntuales fechados de
mayo-junio 2026 se retiraron el 2026-06-13 (su conocimiento ya está aplicado
en el paper, el código y el manifest; ver `CHANGELOG.md`). Lo que queda es lo
perenne y lo que el código lee/escribe.

## Current reconstruction control (2026-07-10)

The current IJDS submission is **NO-GO**. Before using any paper-facing result,
read these files in order:

1. `ijds_state_of_art_audit_2026-07-10.md` - scientific red-team and the four
   design blockers.
2. `ijds_three_front_reconstruction_2026-07-10.md` - preservation and final
   single-paper reconstruction decisions.
3. `ijds_reconstruction_asset_inventory_2026-07-10.csv` - machine-readable
   disposition of sections, claims, figures, tables, code, and scratch results.
4. `ijds_maturity_safe_locked_protocol_2026-07-10.md` - preregistered dates,
   methods, comparators, metrics, interpretation rules, and required Git tag
   for the confirmatory reconstruction.
5. `ijds_maturity_safe_locked_bounded_protocol_v2_2026-07-10.md` - narrowly
   scoped observability amendment after v1 stopped on unresolved primary rows;
   no dates, policies, objectives, or comparators changed.

`active_claims_2026-07-04.md` now names the historical compact-v7 claim. It is
retained because code and tests still replay that artifact, not because its
numbers are submission-ready.

## Registros activos (referenciados por el código o el paper)

- `active_claims_2026-07-04.md` — source-of-truth histórico del claim v7:
  replay conformal exacto al 90%, selector 3x3, política lineal 50/50 y
  evidencia A35--A40. No es evidencia activa para submission.
- `ijds_exact_alpha_calibration_selection_2026-07-09.md` — closeout que
  documenta por qué se retiró el alpha-0.01 aproximado y cómo se eligió la
  política simple sin outcomes OOT en el selector final.
- `crpto_p1_evidence_2026-05-04.md` — evidencia P1 alrededor del champion
  congelado (escrito por `scripts/analyze_crpto_evidence.py`).
- `crpto_journal_package_2026-05-04.md` — tablas A12–A34 y figuras journal
  (escrito por `scripts/build_crpto_journal_package.py`).
- `crpto_extended_evidence_cards_2026-06-06.md` — fichas de evidencia extendida
  (PyEPO/DFL, FICO proxy, IFRS9/SICR, CRC/CROMS-lite); superficie canónica en
  `reports/crpto/extended/`.
- `crpto_conditional_tightening_appendix_2026-05-04.md` — lemma condicional
  Hoeffding/Bernstein y caveats de dependencia (material del supplement).
- `crpto_bound_tightening_experiment_2026-06-11.md` — registro del menú de
  bounds A21 (Cantelli/Bennett/Bernstein + la fila agnóstica que prueba Markov
  óptimo). Generado por `scripts/build_bound_tightening_audit.py`.
- `pool93_tail_risk_closeout_2026-07-02.md` — cierre A37--A39 para la
  asignacion pool93 seleccionada: tail-risk repricing, cluster-bound y
  bootstrap fijo.
- `archive/paper4_crpto_crosswalk_2026-07-02.md` — decision autocontenida sobre
  que evidencia extendida entra al paper IJDS, que queda en supplement y que
  queda en tesis/future work (archivada tras aplicarse).
- `ijds_rebaseline_2026-06-07.md` — registro historico del rebaseline previo
  (`ijds-rebaseline-2026-06-07`), retenido como provenance despues del cierre
  pool93.
- `literature_reference_audit_2026-06-14.md` — auditoría de evidencia local de
  lectura para las referencias citadas en el cuerpo IJDS.
- `ijds_simplification_cleanup_audit_2026-07-06.md` — decisión reader-facing
  sobre qué lenguaje técnico queda en el body, qué pasa al supplement/package,
  limpieza local de peso y frontera entre refactor estricto y nueva corrida
  tolerante.
- `ijds_scientific_upgrade_audit_2026-07-07.md` — separación entre mejoras de
  paper que pueden entrar con evidencia congelada y extensiones que quedan
  fuera del claim enviado salvo un nuevo protocolo etiquetado.

- `ijds_corpus_claims_improvement_plan_2026-07-07.md` - analisis con
  `academic-pdf-intake` del paper, supplement, submission PDF y corpus
  `Papers_tesis`; sus recomendaciones editoriales IJDS quedaron aplicadas y se
  conserva como trazabilidad, no como backlog abierto.
- `ijds_literature_expansion_scan_2026-07-08.md` - scan de literatura externa y
  local para nuevas referencias IJDS: contextual optimization, incertidumbre de
  credit scoring, conformal no-exchangeable, post-selection y comparadores
  decision-calibrated 2026.
- `pool93_certificate_semantics_v2_2026-07-09.md` - auditoría histórica de la
  frontera pool93 y su baseline; conserva procedencia, no claims activos.

## Registros de gobernanza (decisiones; no se re-ejecutan sin permiso)

- `crpto_champion_reopen_plan_2026-05-21.md` — secuencia gobernada de reopen
  del champion y sus gates innegociables (documentación, no acción).
- `crpto_bound_improvement_intake_2026-05-21.md` — paquete de challengers
  PD/conformal del sandbox externo y sus gates.
- `crpto_champion_tournament_protocol_2026-05-25.md` — contrato anti-cherry-pick
  y gates del torneo de champion; histórico después de la promoción pool93.
- `crpto_publication_strategy_2026-05-12.md` — decisión de venue, plantilla,
  anonimato y salida IJDS/EJOR; algunas referencias a `45/45` son históricas.
- `crpto_pyepo_dfl_intake_2026-05-26.md` — PyEPO 1.3.7 y cierre del comparador
  DFL/SPO+ aislado.

## `literature/` — notas de lectura versionadas

Notas curadas sobre fuentes específicas. Los PDFs de literatura se mantienen en
`Papers_tesis/`, que está ignorado por Git, para no commitear material con
copyright. En `docs/research/literature/` deben quedar solo notas, hashes,
decisiones editoriales y trazabilidad de uso.

## `foundations/` — referencia técnica perenne

Material de fundamento que puede volver a consultarse para la tesis: conformal
prediction (research, quick reference, comparación de librerías), calibración,
MRM, literatura de portfolio selection, state-of-the-art, decisiones de
arquitectura (`crpto_decision_changes_and_learnings.md`), topología del
pipeline, runbook e integraciones.

## `future_work/` — backlog del segundo paper

Memos de extensión (incertidumbre temporal vNext, conformal de clasificación,
validation hardening) que no forman parte de los claims del manuscrito IJDS.

> Para el **estado de refactors**, ver [`../refactor/README.md`](../refactor/README.md);
> el backlog consolidado 2026-06 quedó ejecutado y archivado en
> [`../refactor/archive/NEXT_WORK_PLAN_2026-06.md`](../refactor/archive/NEXT_WORK_PLAN_2026-06.md).
> Las fases F1–F5 de la auditoría 2026-07-05 están cerradas; el registro de
> ejecución y el backlog post-submission viven en
> [`crpto_full_audit_2026-07-05.md`](crpto_full_audit_2026-07-05.md).
