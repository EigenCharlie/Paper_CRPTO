# CRPTO Skill

Use this skill in `C:\Users\carlos\Documents\Paper_CRPTO`. CRPTO is one
single-author IJDS paper and reproducibility bundle, not a production service.

## Active Contract

Read first:

1. `docs/research/active_claims_2026-07-14.md`
2. `docs/research/ijds_binary_geometry_frontier_v4_protocol_2026-07-12.md`
3. `docs/research/ijds_evaluation_endpoint_recovery_v3_protocol_2026-07-14.md`
4. `docs/research/ijds_normalized_objective_frontier_v1c_protocol_2026-07-13.md`
5. `docs/research/ijds_two_ruler_endpoint_recovery_v3_protocol_2026-07-14.md`
6. `configs/ijds_active_evidence_sources.yaml`
7. `configs/ijds_claim_ledger.yaml`
8. `docs/research/ijds_endpoint_availability_sensitivity_protocol_2026-07-14.md`
9. `reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json`
10. `docs/ACADEMIC_CONTEXT.md`
11. `docs/SCOPE_AND_GOVERNANCE.md`
12. `CONTRIBUTING.md`
13. `EXTRACTION_MANIFEST.md`

Active evidence:

- outcome-free freeze: `ijds-binary-geometry-frontier-v4-2026-07-12-v1`;
- verified evaluation: `ijds-binary-geometry-frontier-v4-2026-07-14-v3`;
- complete residual specification: eight consecutive six-month windows;
- primary OOT: 376,890 candidates in fifteen monthly USD 1 million menus;
- coverage learners: CatBoost/Platt primary plus numeric logistic, monotonic
  CatBoost, platform-signal WOE/IV, and pricing-excluded WOE/IV controls;
- portfolio learner: primary CatBoost only; no OOT learner is selected;
- score path: `gamma={0,.25,.50,.75,1}` with endpoint contrast `gamma=1-gamma=0`;
- objective-matched primary and normalized-score secondary rulers at three
  interior coordinates; there is no selector;
- the nine V4 fixed-cap policies are supporting exact-frontier diagnostics;
- C2 comparator: contemporaneous frozen funded point-score cap;
- exact point-cap frontier: 3,067 HiGHS basis/support endpoints;
- unresolved outcomes: retained with sharp common-outcome bounds.
- evaluation-endpoint availability: all lags 0, 3, 6, 8, and 12 months are
  reported without selection; the 6-month slice reconciles exactly to V3.

Headline evidence:

- under the declared six-month endpoint contract, every CatBoost five-group
  OOT upper bound is below 0.90; maximum `0.882597`;
- every logistic-control upper bound is below 0.90; maximum `0.896222`;
- monotonic CatBoost, platform WOE, and pricing-excluded WOE maxima are
  `0.886489`, `0.894908`, and `0.897726`; all five fail in all eight windows;
- all `2,925,493` raw rows are audited; the `640,543` active rows exhaust the
  declared 36-month population rather than forming a convenience sample;
- all 45 OptBinning problems are optimal; WOE/IV, monotonicity, calibration,
  and PSI remain robustness controls rather than central novelty;
- CatBoost stratum 2 crosses prevalence alpha from W7 to W8 and its residual
  quantile changes from `0.888435` to `0.111801`;
- C2 match residual is at most `8.33e-17` and reconciles weak plug-in dominance;
- all 216 broad-stress envelopes cross zero;
- default crosses zero in all 72 development-support cells;
- all 27 W8 development-support envelopes cross zero;
- the objective-matched endpoint contrast crosses zero at `.25`, is adverse at
  `.50`, and is mostly unidentified for payoff/default at `.75`;
- normalized-score `.25` and `.50` are adverse; `.75` has adverse default and
  miscoverage while payoff is adverse in seven windows and crosses in one;
- the six ruler-coordinate tracks are not 48 independent replications;
- the factorial simulation is claim-bearing for coverage mechanism only; its
  portfolio component is degenerate.

The archive and earlier results were inspected. Each retained evaluation is
protocol-locked before its corresponding outcome join, but the study is not a
preregistration, untouched holdout, prospective confirmation, or model contest.
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
- objective-matched opportunity cost versus normalized-score relaxation;
- finite three-coordinate diagnostics versus a continuous joint frontier;
- standardized payoff versus cash-flow return, IRR, NPV, or welfare;
- sharp identification bounds versus sampling confidence intervals;
- C2 plug-in dominance versus realized-outcome dominance;
- exact declared comparator support versus universal baseline invariance;
- tagged retrospective audit versus preregistration or confirmation.
- conformal-fit label timing versus evaluation-endpoint availability; these
  are separate one-factor sensitivities and were not crossed factorially.

Do not claim a learner, gamma, ruler, coordinate, or policy winner, universal
direction, selected-set validity, Markov/tail certificate, causal effect, live
deployment result, or portfolio mechanism from the V4 simulation.

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

The active builder verifies the V4, two-ruler, raw-data, and credit-control
manifests/freezes and every artifact descriptor. It emits only
`crpto_ijds_v4_*` tables/figures and
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
