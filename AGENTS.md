# AGENTS.md — Contexto para agentes (Codex y otros)

La fuente única de contexto operativo de este repositorio es
[`CLAUDE.md`](CLAUDE.md). Este archivo existía como copia para Codex y quedó
desactualizado (presentaba el rebaseline pre-pool93 como champion activo), así
que se redujo a puntero para eliminar la duplicación.

Lectura obligatoria, en este orden:

1. [`CLAUDE.md`](CLAUDE.md) — reglas de operación, champion congelado
   (esquema dual-tag pool93), stages prohibidos, comandos y convenciones.
2. [`docs/research/active_claims_2026-07-04.md`](docs/research/active_claims_2026-07-04.md)
   — registro vigente de claims del paper (replay exacto al 90%, selector de
   calibración 3x3, política lineal 50/50 y reopen gate).
3. [`.codex/skills/crpto/SKILL.md`](.codex/skills/crpto/SKILL.md) — skill de
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
