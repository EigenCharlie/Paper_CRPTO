# AGENTS.md - Agent context

The single operational source is [`CLAUDE.md`](CLAUDE.md). Read these files in
order before changing scientific code or paper claims:

1. [`CLAUDE.md`](CLAUDE.md) - repository rules and protected historical stages.
2. [`docs/research/active_claims_2026-07-14.md`](docs/research/active_claims_2026-07-14.md)
   - the only active IJDS claim registry.
3. [`docs/research/ijds_binary_geometry_frontier_v4_protocol_2026-07-12.md`](docs/research/ijds_binary_geometry_frontier_v4_protocol_2026-07-12.md)
   - complete-window V4 protocol and stop rules.
4. [`docs/research/ijds_evaluation_endpoint_recovery_v3_protocol_2026-07-14.md`](docs/research/ijds_evaluation_endpoint_recovery_v3_protocol_2026-07-14.md)
   - endpoint-corrected V1-freeze to V3-evaluation lineage.
5. [`docs/research/ijds_normalized_objective_frontier_protocol_2026-07-12.md`](docs/research/ijds_normalized_objective_frontier_protocol_2026-07-12.md)
   - two-ruler research question, estimands, and locked stop rules.
6. [`docs/research/ijds_normalized_objective_frontier_v1c_protocol_2026-07-13.md`](docs/research/ijds_normalized_objective_frontier_v1c_protocol_2026-07-13.md)
   - retained outcome-free numerical lineage.
7. [`docs/research/ijds_two_ruler_endpoint_recovery_v3_protocol_2026-07-14.md`](docs/research/ijds_two_ruler_endpoint_recovery_v3_protocol_2026-07-14.md)
   - endpoint-corrected finite-grid interpretation boundary.
8. [`reports/crpto/data_audit/ijds-raw-data-contract-2026-07-14-v2/evidence.json`](reports/crpto/data_audit/ijds-raw-data-contract-2026-07-14-v2/evidence.json)
   - active full-archive population, maturity, schema, and funding audit.
9. [`models/experiments/ijds_audit/ijds-credit-risk-controls-2026-07-15-v5/credit_risk_controls_summary.json`](models/experiments/ijds_audit/ijds-credit-risk-controls-2026-07-15-v5/credit_risk_controls_summary.json)
   - active five-model coverage, WOE/IV, monotonicity, calibration, and PSI evidence.
10. [`docs/research/ijds_label_lag_sensitivity_protocol_2026-07-14.md`](docs/research/ijds_label_lag_sensitivity_protocol_2026-07-14.md)
   - retrospectively locked fit-label timing sensitivity and retention stop rule.
11. [`docs/research/ijds_endpoint_availability_sensitivity_protocol_2026-07-14.md`](docs/research/ijds_endpoint_availability_sensitivity_protocol_2026-07-14.md)
   - complete nonselective evaluation-endpoint availability sensitivity.
12. [`docs/research/ijds_portfolio_structure_sensitivity_v6_protocol_2026-07-15.md`](docs/research/ijds_portfolio_structure_sensitivity_v6_protocol_2026-07-15.md)
   - retained complete budget--purpose-cap--LGD sensitivity and numerical lineage.
13. [`models/experiments/ijds_audit/ijds-portfolio-structure-sensitivity-2026-07-15-v6/structural_sensitivity_summary.json`](models/experiments/ijds_audit/ijds-portfolio-structure-sensitivity-2026-07-15-v6/structural_sensitivity_summary.json)
   - active complete-grid structural evidence.
14. [`docs/research/ijds_fit_label_completion_sensitivity_protocol_2026-07-16.md`](docs/research/ijds_fit_label_completion_sensitivity_protocol_2026-07-16.md)
   - observed-only fit plus three completion rules and nonlinear interpretation boundary.
15. [`docs/research/ijds_allocation_granularity_sensitivity_protocol_2026-07-16.md`](docs/research/ijds_allocation_granularity_sensitivity_protocol_2026-07-16.md)
   - USD 25 floor-with-cash diagnostic and fixed-capital estimands.
16. [`configs/ijds_active_evidence_sources.yaml`](configs/ijds_active_evidence_sources.yaml)
   - active lineage identities and exact DVC-pointer authority.
17. [`configs/ijds_claim_ledger.yaml`](configs/ijds_claim_ledger.yaml)
   - executable nonnumeric claim and surface contract.
18. [`reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json`](reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json)
   - the only active paper-facing evidence manifest.
19. [`.codex/skills/crpto/SKILL.md`](.codex/skills/crpto/SKILL.md) - concise
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
- No selected gamma, ruler, coordinate, structural scenario, policy, winner,
  universal guardrail direction, causal effect, or selected-set conformal claim
  is active.
- The five learner specifications are coverage controls; only the primary
  CatBoost enters portfolio optimization and no OOT model winner is active.
- Historical V1--V3, structural-sensitivity V1--V5, selected-policy,
  compact-v7, pool93, and A1--A40 materials are provenance, not evidence for
  the active manuscript.
- Edit `paper/CRPTO_ijds.qmd`; generate the official TeX with
  `scripts/build_ijds_submission_tex.py` rather than editing it directly.
