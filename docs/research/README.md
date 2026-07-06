# paper-crpto — Research Dossier

Notas de investigación y registros que aún tienen valor de consulta para el
paper y la tesis. Las auditorías, backlogs y checklists puntuales fechados de
mayo-junio 2026 se retiraron el 2026-06-13 (su conocimiento ya está aplicado
en el paper, el código y el manifest; ver `CHANGELOG.md`). Lo que queda es lo
perenne y lo que el código lee/escribe.

## Registros activos (referenciados por el código o el paper)

- `active_claims_2026-07-04.md` — source-of-truth operativo del claim IJDS
  activo: dual-tag governance, punto pool93, semántica de grilla finita,
  denominadores de frontera y stop rules para no reabrir búsquedas sin un
  claim que pueda cambiar.
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
