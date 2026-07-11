# CRPTO Skill

Use this skill inside `C:\Users\carlos\Documents\Paper_CRPTO`. CRPTO is a
single-author IJDS paper and reproducibility bundle, not a production service.
Prefer simple code, immutable evidence, and one coherent manuscript claim.

## Active Scientific Contract - 2026-07-10

Read these first:

1. `docs/research/active_claims_2026-07-10.md`
2. `docs/research/ijds_comparator_stringency_locked_protocol_2026-07-10.md`
3. `docs/research/ijds_comparator_stringency_results_2026-07-10.md`
4. `docs/research/ijds_state_of_art_audit_2026-07-10.md`
5. `docs/research/ijds_three_front_reconstruction_2026-07-10.md`
6. `docs/research/ijds_final_two_pass_audit_2026-07-10.md`
7. `docs/ACADEMIC_CONTEXT.md`
8. `docs/SCOPE_AND_GOVERNANCE.md`
9. `CONTRIBUTING.md`
10. `EXTRACTION_MANIFEST.md`

The active paper combines the clean, tagged maturity-safe bounded protocol v2
with a separate post hoc comparator-stringency audit:

- run:
  `champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2`;
- protocol tag:
  `protocol/ijds-maturity-safe-locked-bounded-h1h2-2026-07-10-v2`;
- protocol commit: `78a64fe67a4df46c3d19b9243deb991c56fd1ff6`;
- universe: 540,121 status-independent 36-month loans;
- conformal object: 90%-target five-stratum interval using the exact
  finite-sample rank for the binary snapshot outcome, not a latent-PD
  confidence interval;
- selected guardrail: `q=0.75p+0.25u`, `tau=0.17`;
- payoff: expected `(1-p)r-p*LGD`, realized `(1-Y)r-Y*LGD`, `LGD=0.45`;
- evaluation: 15 fresh monthly $1M decisions from 2016-04 through 2017-06;
- unresolved outcomes: retained and reported with sharp aggregate and pairwise
  bounds.

Comparator audit:

- run:
  `champion-reopen-2026-07-10__maturity-safe-v2-comparator-stringency-audit-v1`;
- protocol tag:
  `protocol/ijds-maturity-safe-v2-comparator-stringency-audit-2026-07-10-v1`;
- protocol commit: `ca632ccfbbfaec0e6cdf482a279468665cdb62c0`;
- status: designed after the parent result, tagged before the first successful
  persisted execution, and therefore post hoc rather than confirmatory;
- primary point-PD comparator: `tau=0.06831339893217318`, the selected
  guardrail's mean development-funded point PD.

Primary guardrail-minus-development-matched-point contrasts:

- standardized realized payoff: `[-$506,587.03, -$295,967.17]`;
- weighted default: `[0.034431, 0.056287]`;
- weighted miscoverage: `[0.027093, 0.046283]`.

Interpretation: using `tau=0.17` for both scores confounds the conformal score
with a looser point-PD feasible set and creates an apparent default benefit.
After development-risk matching, that benefit reverses. The selected result is
robust to the locked diagnostics, but the family direction is 7 of 9, not 9 of
9. Do not promote confirmation, universal dominance, a unique matching rule,
or selected-set validity.

## Claim Boundaries

Always preserve these distinctions:

- candidate membership at decision time versus ex-post outcome resolution;
- binary-outcome conformal intervals versus confidence intervals for latent PD;
- marginal/Mondrian coverage versus optimizer-selected funded-set coverage;
- coherent standardized payoff versus cash-flow return, IRR, or NPV;
- sharp partial-identification bounds versus sampling confidence intervals;
- exact transport identities versus formal regularization guarantees;
- same numeric thresholds versus comparable decision stringency;
- retrospective contrasts versus causal effects;
- post hoc comparator falsification versus confirmatory evidence;
- code-locked retrospective audit versus preregistration or a pristine
  prospective lockbox.

The paper may claim four exact theory results: binary miscoverage geometry,
sharp additive bounds for unresolved binary outcomes, the telescoping
row/exposure/group/within-group transport identity, and same-threshold
feasible-set nesting when `q>=p`. The last result diagnoses a comparator
defect; it does not prove development matching uniquely correct. The paper
does not claim a new selected-set theorem, distributional robustness, or a
Markov certificate.

## Active Evidence

The paper-facing manifests are:

`reports/crpto/ijds_maturity_safe_evidence.json`

`reports/crpto/ijds_comparator_stringency_evidence.json`

It validates:

- `maturity_safe_locked_summary.json`;
- `execution_receipt.json`;
- protocol tag and commit;
- every versioned data/model artifact hash;
- tables `crpto_ijds_ms_table1`--`table4` and S1--S7; and
- figures `crpto_ijds_ms_fig0`--`fig3`.

The comparator manifest additionally validates the exact parent replay,
selected low/mean/high sensitivity, 15 leave-one-month-out checks, nine-policy
census, payoff/LGD decomposition, and comparator tables/figures.

Large active run directories are tracked by exact DVC pointers under
`data/processed/experiments/champion_reopen/` and
`models/experiments/champion_reopen/`. The builder is byte-idempotent.

## Historical Boundary

The compact-v7 run and A35--A40 bundle are replay provenance only. Its positive
return claim is invalid for submission because the old design used
outcome-conditioned membership, contaminated conformal ingredients, an
incoherent payoff, and a pooled future menu. Earlier A1--A34 OCE/CVaR, SPO+,
online-style, Prosper, and Freddie/Mendeley analyses remain historical
diagnostics and cannot validate the active maturity-safe policy.

Never overwrite these protected files:

- `models/pd_canonical.cbm`
- `models/pd_canonical_calibrator.pkl`
- `models/final_project_promotion.json`
- `models/conformal_policy_status.json`
- `data/processed/conformal_intervals_mondrian.parquet`
- `data/processed/portfolio_bound_aware/rank1_alpha01_bound_aware_276k_full_2026-04-05-1734/`
- historical pool93 governance and A35--A40 files
- `EXTRACTION_MANIFEST.json`

Protected DVC stages are `crpto.pd.champion`,
`crpto.conformal.intervals`, `crpto.conformal.validation`,
`crpto.portfolio.optimization`, and `crpto.portfolio.bound_exact_eval`.
Experiments may read their outputs. Run a protected stage only with explicit
permission naming the branch, output paths, and drift plan.

## Paper Workflow

Use Windows PowerShell and `uv run`. Ordinary paper work rebuilds evidence from
the committed active run; it does not hide an expensive experiment rerun.

```powershell
just ijds-evidence
uv run pytest tests/test_ijds_active_claim_sync.py -q
uv run pytest tests/test_ijds_comparator_evidence.py -q
just publication-integrity
just lint
just type-check
just type-advisory-full
just test
just validate-champion
just paper-submission
just paper-submission-official
uv run dvc status --no-updates
```

The manual official-TeX fallback is intentionally:

```text
pdflatex -> bibtex -> pdflatex -> pdflatex
```

The first LaTeX pass creates `.aux`, BibTeX creates `.bbl`, and the last two
passes resolve then stabilize citations, references, floats, and pagination.

## Writing

- Paper and code identifiers are English; project notes may be Spanish.
- Lead with comparator non-invariance, the baseline-dependent reversal, and
  the remaining coverage-transport failure.
- Report unresolved exposure and temporal failures as prominently as wins.
- Call the outcome `snapshot default` and the objective `standardized payoff`.
- Do not call the interval a PD interval, the result a causal effect, or the
  protocol prospective/preregistered.
- Keep the main official body within 25 pages; put complete grids, proofs,
  hashes, and historical boundaries in the separate supplement.
- Preserve one method and one paper. Future survival, decision-calibrated, or
  selection-valid variants require a new locked protocol and are not implied
  by the current claim.
