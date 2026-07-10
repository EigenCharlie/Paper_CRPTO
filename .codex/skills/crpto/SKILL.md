# CRPTO Skill

Use this skill inside `C:\Users\carlos\Documents\Paper_CRPTO`. CRPTO is a
single-author IJDS paper and reproducibility bundle, not a production service.
Prefer simple code, frozen evidence, and one coherent manuscript claim.

## Read First

1. `docs/ACADEMIC_CONTEXT.md`
2. `docs/SCOPE_AND_GOVERNANCE.md`
3. `docs/research/active_claims_2026-07-04.md`
4. `CONTRIBUTING.md`
5. `EXTRACTION_MANIFEST.md`
6. `configs/crpto_publication_targets.yaml`

Use Windows PowerShell and `uv run`. Do not introduce Unix-only workflow
assumptions.

## Active IJDS Policy

- Run tag:
  `champion-reopen-2026-06-19__pool93__ijds-calibration-selected-endpoint28-v7`
- Exact conformal replay: target `alpha=0.10`, frozen used alpha `0.095`.
- Decision score: `q=(p+u)/2`.
- Risk tolerance: `tau=0.17`.
- Objective: point-PD expected net return; conformal `q` is the risk guardrail.
- Selector: nine round-number policies on November 2017; five satisfy full
  budget, effective-PD, and deterministic `B_u<=0.28` screens. Outcomes are
  stored separately from the 12-column selector frame.
- Audit: an outcome-free December replay selects the same policy; opening
  outcomes afterward gives weighted default `0.145650` and miscoverage
  `0.124925`, so stability is not reported as selected-set validity.
- Full OOT: 276,869 candidates, 308 funded, `$179,327.59` realized return,
  `0.039375` weighted default, `0.036875` weighted miscoverage.
- `Gamma_CP=0.176102`, `Gamma_residual=0.088051`, endpoint `0.258051`.
- Markov sensitivity: threshold `0.574279` with probability bound `0.316228`
  under weighted funded-set validity.
- Matched point-PD: `$196,369.14`, `0.118400` weighted default, endpoint
  `0.921317`, threshold `1.237545`.

The exact paper-facing source is:

`models/experiments/champion_reopen/<run_tag>/portfolio/ijds_policy_governance.json`

A35--A40 provide exact-alpha, selector, temporal, grade, bootstrap, and matched
comparison evidence. The final selector does not read OOT outcomes, but prior
project development inspected the static OOT corpus. Say "retrospective
lockbox replay," not "preregistered," "prospective," or "untouched holdout."

Do not revive these as active claims: approximate alpha-0.01 scaling, `8/8`,
the 50,010-policy frontier, `0.345084`, capped/tail-selected policies, or OOT
outcome-selected hyperparameters.

## Frozen Provenance

Never overwrite the manifest-protected upstream or historical pool93 files:

- `models/pd_canonical.cbm`
- `models/pd_canonical_calibrator.pkl`
- `models/final_project_promotion.json`
- `models/conformal_policy_status.json`
- `data/processed/conformal_intervals_mondrian.parquet`
- `data/processed/portfolio_bound_aware/rank1_alpha01_bound_aware_276k_full_2026-04-05-1734/`
- historical `crpto_tableA35..A40_pool93_*` files
- historical pool93 governance JSON files
- `EXTRACTION_MANIFEST.json`

New experiments must use a distinct run tag and write under
`data/processed/experiments/champion_reopen/` and
`models/experiments/champion_reopen/`. Never replace frozen paths.

Protected DVC stages are `crpto.pd.champion`,
`crpto.conformal.intervals`, `crpto.conformal.validation`,
`crpto.portfolio.optimization`, and `crpto.portfolio.bound_exact_eval`.
Experiments may read their outputs. Run a protected stage only with explicit
permission and a drift report.

## Method Boundary

The submitted method has one linear policy. Capped, tail, OCE/CVaR, SPO+,
multi-distribution, online, causal, and external-data variants are comparators
or diagnostics, not additional CRPTO methods.

Keep these distinctions explicit:

- exact conformal quantile replay versus approximate width scaling;
- point PD in the economic objective versus conformal `q` in the constraint;
- deterministic `weighted outcome <= B_u + V` versus the
  assumption-conditional Markov statement;
- calibration-only final ranking versus historical OOT-aware development;
- full-OOT averages versus temporal heterogeneity;
- retrospective contrasts versus causal or universal dominance.

## Paper Workflow

Safe paper work may regenerate active A35--A40, figures, Quarto outputs, and the
official IJDS PDF. Keep body, supplement, submission TeX, governance JSON, and
claim-sync tests numerically aligned.

Standard closeout:

```powershell
uv run python scripts/build_ijds_calibration_selected_evidence.py
uv run pytest tests/test_ijds_active_claim_sync.py -q
just lint
just type-check
just type-advisory-full
just smoke
just validate-champion
just paper-submission
just paper-submission-official
uv run dvc status --no-updates
```

Run `just drift-gate` after changes to conformal or PD semantics. Do not bypass
hooks, commit secrets, or alter `EXTRACTION_MANIFEST.json`.

## Writing

- Paper and code identifiers are English; project notes may be Spanish.
- Lead with data, method, decision, and managerial implication.
- Report the price of robustness and temporal failures as prominently as wins.
- Treat reproducibility as evidence quality, not as the sole novelty.
- Keep the main IJDS body within 25 pages; move proofs and diagnostics to the
  separate supplement.
