# AGENTS.md — Contexto para agentes (Codex y otros)

La fuente única de contexto operativo de este repositorio es
[`CLAUDE.md`](CLAUDE.md). Este archivo existía como copia para Codex y quedó
desactualizado (presentaba el rebaseline pre-pool93 como champion activo), así
que se redujo a puntero para eliminar la duplicación.

Lectura obligatoria, en este orden:

1. [`CLAUDE.md`](CLAUDE.md) — reglas de operación, champion congelado
   (esquema dual-tag pool93), stages prohibidos, comandos y convenciones.
2. [`docs/research/ijds_state_of_art_audit_2026-07-10.md`](docs/research/ijds_state_of_art_audit_2026-07-10.md)
   — auditoría científica que deja el submission v7 en NO-GO.
3. [`docs/research/ijds_three_front_reconstruction_2026-07-10.md`](docs/research/ijds_three_front_reconstruction_2026-07-10.md)
   — ledger de recuperación y diseño del único paper IJDS final.
4. [`docs/research/active_claims_2026-07-10.md`](docs/research/active_claims_2026-07-10.md)
   - active maturity-safe v2 claims plus the post hoc comparator-stringency
     audit, bounds, and transport mechanism.
5. [`docs/research/ijds_comparator_stringency_locked_protocol_2026-07-10.md`](docs/research/ijds_comparator_stringency_locked_protocol_2026-07-10.md)
   - immutable comparator design and its post hoc interpretation boundary.
6. [`docs/research/ijds_final_two_pass_audit_2026-07-10.md`](docs/research/ijds_final_two_pass_audit_2026-07-10.md)
   - final scientific/editorial disposition, recovery ledger, and stop rule.
7. [`docs/research/active_claims_2026-07-04.md`](docs/research/active_claims_2026-07-04.md)
   — registro histórico v7, conservado para replay y no como claim activo.
8. [`.codex/skills/crpto/SKILL.md`](.codex/skills/crpto/SKILL.md) — skill de
   Codex con el detalle operativo del certificado y sus artefactos.

Reglas mínimas que ningún agente puede violar (detalle en `CLAUDE.md`):

- El champion congelado es ley: los stages `crpto.pd.champion`,
  `crpto.conformal.intervals`, `crpto.conformal.validation`,
  `crpto.portfolio.optimization` y `crpto.portfolio.bound_exact_eval` no se
  ejecutan sin permiso explícito.
- No modificar `EXTRACTION_MANIFEST.json` ni los artefactos que lista.
- Validar con `just validate-champion` antes de cualquier merge; refactors de
  la capa conformal/PD exigen `just drift-gate` en verde.
- Windows-first, `uv run` para todo tooling Python, sin secretos en Git.
