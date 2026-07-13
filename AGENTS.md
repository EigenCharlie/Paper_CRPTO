# AGENTS.md - Agent context

The single operational source is [`CLAUDE.md`](CLAUDE.md). Read these files in
order before changing scientific code or paper claims:

1. [`CLAUDE.md`](CLAUDE.md) - repository rules and protected historical stages.
2. [`docs/research/active_claims_2026-07-12.md`](docs/research/active_claims_2026-07-12.md)
   - the only active IJDS claim registry.
3. [`docs/research/ijds_binary_geometry_frontier_v4_protocol_2026-07-12.md`](docs/research/ijds_binary_geometry_frontier_v4_protocol_2026-07-12.md)
   - complete-window V4 protocol and stop rules.
4. [`docs/research/ijds_binary_geometry_frontier_v4_v2_recovery_2026-07-12.md`](docs/research/ijds_binary_geometry_frontier_v4_v2_recovery_2026-07-12.md)
   - verified V1-freeze to V2-evaluation lineage.
5. [`docs/research/ijds_normalized_objective_frontier_protocol_2026-07-12.md`](docs/research/ijds_normalized_objective_frontier_protocol_2026-07-12.md)
   - two-ruler research question, estimands, and locked stop rules.
6. [`docs/research/ijds_normalized_objective_frontier_v1c_protocol_2026-07-13.md`](docs/research/ijds_normalized_objective_frontier_v1c_protocol_2026-07-13.md)
   - retained outcome-free numerical lineage.
7. [`docs/research/ijds_normalized_objective_frontier_v2_paper_facing_erratum_2026-07-13.md`](docs/research/ijds_normalized_objective_frontier_v2_paper_facing_erratum_2026-07-13.md)
   - finite-grid and repeated-allocation interpretation boundary.
8. [`reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json`](reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json)
   - the only active paper-facing evidence manifest.
9. [`.codex/skills/crpto/SKILL.md`](.codex/skills/crpto/SKILL.md) - concise
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
- No selected gamma, ruler, coordinate, policy, winner, universal guardrail
  direction, causal effect, or selected-set conformal claim is active.
- Historical V1--V3, selected-policy, compact-v7, pool93, and A1--A40 materials are
  provenance, not evidence for the active manuscript.
- Edit `paper/CRPTO_ijds.qmd`; generate the official TeX with
  `scripts/build_ijds_submission_tex.py` rather than editing it directly.
