# CRPTO Operating Contract

This repository contains one active IJDS manuscript. Historical searches,
promoted policies, thesis-book material, and earlier manuscript versions are
not active evidence.

## Read Before Changing Science

1. `docs/research/active_claims_2026-07-14.md`
2. `docs/research/ijds_binary_geometry_frontier_v4_protocol_2026-07-12.md`
3. `docs/research/ijds_evaluation_endpoint_recovery_v3_protocol_2026-07-14.md`
4. `docs/research/ijds_normalized_objective_frontier_protocol_2026-07-12.md`
5. `docs/research/ijds_normalized_objective_frontier_v1c_protocol_2026-07-13.md`
6. `docs/research/ijds_two_ruler_endpoint_recovery_v3_protocol_2026-07-14.md`
7. `docs/research/ijds_endpoint_availability_sensitivity_protocol_2026-07-14.md`
8. `docs/research/ijds_portfolio_structure_sensitivity_v6_protocol_2026-07-15.md`
9. `docs/research/ijds_fit_label_completion_sensitivity_protocol_2026-07-16.md`
10. `docs/research/ijds_allocation_granularity_sensitivity_protocol_2026-07-16.md`
11. `configs/ijds_active_evidence_sources.yaml`
12. `configs/ijds_claim_ledger.yaml`
13. `reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json`
14. `.codex/skills/crpto/SKILL.md`

The claim registry is the editorial authority. The source registry owns exact
lineage identities, artifact descriptors, and 31 DVC pointers. The V4 evidence
JSON is the only numeric paper-facing manifest.

## Active Scientific Object

- One status-independent universe of 640,543 eligible 36-month loans.
- Primary OOT: 376,890 candidates, of which 364,814 are resolved and 12,076
  remain unresolved under the declared six-month availability rule.
- Five frozen coverage specifications and eight complete residual windows.
- CatBoost/Platt is the only score entering portfolio optimization; logistic,
  monotonic CatBoost, and two WOE/IV scorecards are coverage controls.
- Five gamma values, two outcome-blind rulers, and three interior coordinates;
  none is selected.
- Fifteen separate monthly allocations, sharp common-outcome bounds, exact
  point-cap support, and 36 structural scenarios.
- All 40 six-month all-candidate coverage upper bounds are below 0.90.
- All 216 broad-support comparator envelopes cross zero.
- All 32 overall cells across four declared fit-label scenarios remain
  below 0.90, but the W7--W8 geometry change is not scenario-invariant.
- USD 25 floor rounding is numerically negligible in the declared archive; it
  is a diagnostic of the continuous relaxation, not an integer policy.

The paper supports archive-specific temporal transport failure, binary
residual geometry near a prevalence threshold, and comparator-dependent
decision identification. It does not support a policy winner.

## Forbidden Claims

Do not claim:

- selected model, missingness encoding, gamma, ruler, coordinate, cap,
  structural scenario, comparator, or policy;
- selected-set conformal validity or latent-PD confidence intervals;
- universal favorable or adverse portfolio direction;
- causal, prospective, confirmatory, deployment, fair-lending, or Markov
  conclusions;
- cash-flow return, IRR, NPV, welfare, or counterfactual funding effects.

The five-model coverage result and the CatBoost-only missingness/second-origin
sensitivities are distinct claims. Every first-use 40/40 statement must name
the six-month outcome-availability rule.

## Code Architecture

Active reusable modules:

- `src/ijds_audit/`: protocol, binary geometry, portfolio construction,
  evaluation, policy support, evidence loaders, and raw-data controls. Frozen
  synthetic mechanism outputs are compatibility material, not active evidence.
- `src/ijds_challengers/`: frozen/evaluated frontier lineage and archive
  contracts.
- `src/data/outcome_observability.py`: endpoint reconstruction.
- `src/models/`: maturity-safe PD and binary conformal guardrail components.
- `src/optimization/`: current portfolio, policy, and solver adapters.
- `src/evaluation/`: maturity-safe and paired policy evaluation.

Active execution is declared in
`configs/crpto_publication_targets.yaml`. Top-level scripts outside that list
may remain only because `dvc.yaml` or `EXTRACTION_MANIFEST.json` fixes their
paths. They are sealed compatibility, not active architecture.

## Protected Operations

Never run these without explicit permission:

- `crpto.pd.champion`
- `crpto.conformal.intervals`
- `crpto.conformal.validation`
- `crpto.portfolio.optimization`
- `crpto.portfolio.bound_exact_eval`

Never modify `EXTRACTION_MANIFEST.json` or protected historical artifacts.
Do not execute the sealed historical DVC graph merely to make `dvc status`
clean.

Safe evidence work reads registered roots and writes only the active
`crpto_ijds_v4_*` outputs and evidence JSON. New empirical objects require a
new predeclared protocol, a distinct run tag, contained output paths, and
updated source registration before manuscript use.

## Commands

Use Windows PowerShell and `uv run`.

```powershell
uv sync --extra dev
just smoke
just test
just lint
just type-check
just type-check-fast
just publication-integrity
just drift-gate
just ijds-active-check
just validate-champion
just submission-build
just submission-check
```

`submission-check` must retain `validate-champion-strict`. PD or conformal
implementation changes also require the separately authorized drift gate.

## Manuscript Rules

- Edit `paper/CRPTO_ijds.qmd` and `paper/supplement_ijds.qmd`.
- Generate official TeX with `scripts/build_ijds_submission_tex.py`; never edit
  generated TeX directly.
- Treat sharp bounds as finite-archive identification bounds, not confidence
  intervals.
- Distinguish fit-label timing from evaluation-endpoint availability.
- Distinguish five-model controls from CatBoost-only sensitivities.
- Keep iteration history out of the manuscript.
- Keep the submission double-anonymous.

## Compatibility And Archive

The complete pre-consolidation worktree, Git mirror, bundle, and selected
historical snapshots are preserved at `D:\crpto_legacy`. In-repository
historical files are retained only when path-bound by the immutable extraction
manifest or DVC graph. They must not appear in active commands, claims, or
paper narrative.
