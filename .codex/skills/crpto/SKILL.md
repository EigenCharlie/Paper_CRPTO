# CRPTO Skill

Use this skill in `C:\Users\carlos\Documents\Paper_CRPTO`. CRPTO is one
single-author IJDS paper and reproducibility bundle, not a production service.

## Active Contract

Read first:

1. `docs/research/active_claims_2026-07-12.md`
2. `docs/research/ijds_binary_geometry_frontier_v4_protocol_2026-07-12.md`
3. `docs/research/ijds_binary_geometry_frontier_v4_v2_recovery_2026-07-12.md`
4. `reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json`
5. `docs/ACADEMIC_CONTEXT.md`
6. `docs/SCOPE_AND_GOVERNANCE.md`
7. `CONTRIBUTING.md`
8. `EXTRACTION_MANIFEST.md`

Active evidence:

- outcome-free freeze: `ijds-binary-geometry-frontier-v4-2026-07-12-v1`;
- verified evaluation: `ijds-binary-geometry-frontier-v4-2026-07-12-v2`;
- complete residual specification: eight consecutive six-month windows;
- primary OOT: 376,890 candidates in fifteen monthly USD 1 million menus;
- learners: CatBoost/Platt primary and independent logistic/Platt coverage control;
- all nine `(tau, gamma)` policies are co-primary; there is no selector;
- C2 comparator: contemporaneous frozen funded point-score cap;
- exact point-cap frontier: 3,067 HiGHS basis/support endpoints;
- unresolved outcomes: retained with sharp common-outcome bounds.

Headline evidence:

- every CatBoost five-group OOT upper bound is below 0.90; maximum `0.882167`;
- every logistic-control upper bound is below 0.90; maximum `0.895654`;
- CatBoost stratum 2 crosses prevalence alpha from W7 to W8 and its residual
  quantile changes from `0.888435` to `0.111801`;
- C2 match residual is at most `8.33e-17` and reconciles weak plug-in dominance;
- all 216 broad-stress envelopes cross zero;
- default crosses zero in all 72 development-support cells;
- all 27 W8 development-support envelopes cross zero;
- the factorial simulation is claim-bearing for coverage mechanism only; its
  portfolio component is degenerate.

The superiority paper is NO-GO. The IJDS identification-audit narrative is GO.

## Claim Boundaries

Preserve these distinctions:

- candidate membership versus snapshot outcome resolution;
- clipped binary residual interval versus latent-PD confidence limit;
- continuous interval versus its intersection with `{0,1}`;
- constant-score phase proposition versus varying-score empirical strata;
- overlapping residual windows versus independent replications;
- Platt score and plug-in objective versus true conditional probability;
- candidate coverage versus funded-set validity;
- standardized payoff versus cash-flow return, IRR, NPV, or welfare;
- sharp identification bounds versus sampling confidence intervals;
- C2 plug-in dominance versus realized-outcome dominance;
- exact declared comparator support versus universal baseline invariance;
- tagged retrospective audit versus preregistration or confirmation.

Do not claim a policy winner, universal direction, selected-set validity,
Markov/tail certificate, causal effect, live deployment result, or portfolio
mechanism from the V4 simulation.

## Evidence Workflow

```powershell
uv run python scripts/build_ijds_binary_geometry_frontier_v4_evidence.py
just publication-integrity
just lint
just type-check
just type-advisory-full
just test
just validate-champion
just drift-gate
just paper-submission
just paper-submission-tex
just paper-submission-official
uv run dvc status --no-updates
```

The active builder verifies the V4 summary, freeze, and every artifact
descriptor. It emits only `crpto_ijds_v4_*` tables/figures and
`ijds_binary_geometry_frontier_v4_evidence.json`. Consecutive builds must be
byte-identical. The canonical body is `paper/CRPTO_ijds.qmd`; generate official
TeX with `scripts/build_ijds_submission_tex.py` and never edit it by hand.

Manual LaTeX fallback:

```text
pdflatex -> bibtex -> pdflatex -> pdflatex
```

## Protected History

Never overwrite `EXTRACTION_MANIFEST.json`, canonical PD/calibrator, historical
conformal intervals, pool93 bundles, or A35--A40 champion files. Protected DVC
stages are `crpto.pd.champion`, `crpto.conformal.intervals`,
`crpto.conformal.validation`, `crpto.portfolio.optimization`, and
`crpto.portfolio.bound_exact_eval`.

Fixed-taxonomy V1--V3, selected-policy studies, compact-v7, pool93,
Prosper/Freddie, and A1--A40 are Git/DVC provenance only. The active paper
explains the final method and evidence, not discarded-version chronology.
