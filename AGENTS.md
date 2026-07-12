# AGENTS.md - Agent context

The single operational source is [`CLAUDE.md`](CLAUDE.md). Read these files in
order before changing scientific code or paper claims:

1. [`CLAUDE.md`](CLAUDE.md) - repository rules and protected historical stages.
2. [`docs/research/active_claims_2026-07-12.md`](docs/research/active_claims_2026-07-12.md)
   - the only active IJDS claim registry.
3. [`docs/research/ijds_fixed_taxonomy_c2_protocol_2026-07-11.md`](docs/research/ijds_fixed_taxonomy_c2_protocol_2026-07-11.md)
   - locked protocol and V1-to-V2 execution lineage.
4. [`docs/research/ijds_fixed_taxonomy_c2_temporal_v3_protocol_2026-07-12.md`](docs/research/ijds_fixed_taxonomy_c2_temporal_v3_protocol_2026-07-12.md)
   - locked late-window sensitivity and no-promotion rule.
5. [`docs/research/ijds_fixed_taxonomy_c2_protocol_errata_2026-07-12.md`](docs/research/ijds_fixed_taxonomy_c2_protocol_errata_2026-07-12.md)
   - terminology correction; no numerical or protocol change.
6. [`reports/crpto/ijds_fixed_taxonomy_c2_evidence.json`](reports/crpto/ijds_fixed_taxonomy_c2_evidence.json)
   - the only active paper-facing evidence manifest.
7. [`.codex/skills/crpto/SKILL.md`](.codex/skills/crpto/SKILL.md) - concise
   execution and writing guidance.

Minimum rules:

- Do not run `crpto.pd.champion`, `crpto.conformal.intervals`,
  `crpto.conformal.validation`, `crpto.portfolio.optimization`, or
  `crpto.portfolio.bound_exact_eval` without explicit permission.
- Do not modify `EXTRACTION_MANIFEST.json` or artifacts protected by it.
- Validate ordinary work with `just validate-champion`; `submission-check`
  invokes `just validate-champion-strict` so missing protected artifacts fail.
  PD/conformal refactors also require `just drift-gate`.
- Use `uv run` and Windows-first commands. Never commit secrets.
- No selected policy, winner, universal guardrail direction, causal effect, or
  selected-set conformal claim is active.
- Historical selected-policy, compact-v7, pool93, and A1--A40 materials are
  provenance, not evidence for the active manuscript.
- Edit `paper/CRPTO_ijds.qmd`; generate the official TeX with
  `scripts/build_ijds_submission_tex.py` rather than editing it directly.
