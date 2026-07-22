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
9. `docs/research/ijds_portfolio_structure_sensitivity_v6_protocol_2026-07-15.md`
10. `docs/research/ijds_rolling_origin_endpoint_v3_protocol_2026-07-15.md`
11. `docs/research/ijds_missingness_sensitivity_protocol_2026-07-15.md`
12. `docs/research/ijds_fit_label_completion_sensitivity_protocol_2026-07-16.md`
13. `docs/research/ijds_allocation_granularity_sensitivity_protocol_2026-07-16.md`
14. `docs/research/ijds_rolling_origin_primary_recovery_protocol_2026-07-21.md`
15. `docs/research/ijds_conformal_set_diagnostics_protocol_2026-07-21.md`
16. `docs/research/ijds_exchangeability_transport_test_protocol_2026-07-21.md`
17. `docs/research/ijds_exchangeability_transport_test_interpretive_addendum_2026-07-21.md`
18. `docs/research/ijds_rolling_origin_individual_age_followup_protocol_2026-07-21.md`
19. `docs/research/ijds_rolling_origin_equal_followup_protocol_2026-07-21.md` (parent provenance)
20. `docs/research/ijds_label_mondrian_sensitivity_protocol_2026-07-21.md`
21. `docs/research/ijds_policy_support_optimal_face_v2_protocol_2026-07-21.md`
22. `docs/research/ijds_policy_support_rhs_semantics_recovery_v3a_protocol_2026-07-21.md`
23. `docs/research/applied_conformal_prediction_book_audit_2026-07-21.md`
24. `docs/research/conformal_literature_corpus_audit_2026-07-21.md`
25. `reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json`
26. `docs/ACADEMIC_CONTEXT.md`
27. `docs/SCOPE_AND_GOVERNANCE.md`
28. `CONTRIBUTING.md`
29. `EXTRACTION_MANIFEST.md`

Active evidence:

- outcome-free freeze: `ijds-binary-geometry-frontier-v4-2026-07-12-v1`;
- verified evaluation: `ijds-binary-geometry-frontier-v4-2026-07-15-v5`;
- complete residual specification: eight consecutive six-month windows;
- primary OOT: 376,890 candidates in fifteen monthly USD 1 million menus;
- coverage learners: CatBoost/Platt primary plus numeric logistic, monotonic
  CatBoost, platform-signal WOE/IV, and pricing-excluded WOE/IV controls;
- portfolio learner: primary CatBoost only; no OOT learner is selected;
- score path: `gamma={0,.25,.50,.75,1}` with endpoint contrast gamma 1 minus
  gamma 0;
- objective-matched primary and normalized-score secondary rulers at three
  interior coordinates; there is no selector;
- the nine V4 fixed-cap policies are supporting exact-frontier diagnostics;
- C2 comparator: contemporaneous frozen funded point-score cap;
- exact point-cap frontier: 3,067 HiGHS basis/support endpoints;
- unresolved outcomes: retained with sharp common-outcome bounds.
- evaluation-endpoint availability: all lags 0, 3, 6, 8, and 12 months are
  reported without selection; the 6-month slice reconciles exactly to the
  active evaluation.
- portfolio structure: all 36 budget--purpose-cap--LGD scenarios are reported
  without selection; the baseline reconciles exactly to the active evaluation.
- endpoint resolution is partitioned exhaustively into 307,842 fully paid by
  cutoff, 56,972 charged off by cutoff, 11,551 nonterminal, 47 terminal after
  cutoff, and 478 terminal with missing availability date.
- three missingness encodings and an individual-age second retrospective
  origin are complete, bounded recurrences; the origin comparison uses
  April--June at both origins and cutoffs 39 months after each issue-month end
  (74,537 versus 77,105 candidates), equalizing whole-month administrative age
  rather than exact day-level age; neither family selects a representation or model.
- all 40 five-model/window binary-set cells report AvgC, OneC, empty/two-label
  shares, and resolved-label coverage. The label stratification conditions on
  administrative resolution and is not all-candidate label-conditional validity.
- the joint-block combined-rank reference diagnostic reports 200 strata and 40
  learner-window intersection nulls, with nominal Bonferroni-within-cell and
  Holm-across-cell thresholds. The block null is stronger than the usual
  calibration-plus-one-target condition, and the post-inspection family has no
  selective- or study-wide-FWER claim.
- the label-Mondrian sensitivity freezes all 400 historical classwise
  thresholds before the OOT outcome join and reports 40/200/400 summaries. It
  is descriptive under temporal shift and is not a repair or fairness method.
- four declared fit-label scenarios are complete; they stress 215
  unavailable fitting labels but are not sharp bounds over all assignments.
- USD 25 floor-with-cash rounding is complete for all 1,440 portfolios and 96
  tracks; it is not an optimized integer policy.

Headline evidence:

- under the declared six-month endpoint contract, every CatBoost five-group
  OOT upper bound is below 0.90; maximum `0.882597`;
- every logistic-control upper bound is below 0.90; maximum `0.896222`;
- monotonic CatBoost, platform WOE, and pricing-excluded WOE maxima are
  `0.886489`, `0.894908`, and `0.897726`; all 40 finite-archive upper endpoints
  are below nominal, which alone is not a theorem-failure claim;
- the joint-block combined-rank lineage places `31/40` learner-window nulls
  past locked nominal thresholds: `8/8` CatBoost, `4/8` logistic, `8/8`
  monotonic CatBoost, `6/8` platform WOE, and `5/8` pricing-excluded WOE. A flag
  neither directly refutes one-point validity nor identifies a cause, and a
  nonflag does not establish exchangeability;
- all `2,925,493` raw rows are audited; the `640,543` active rows exhaust the
  declared 36-month population rather than forming a convenience sample;
- all 45 OptBinning problems are optimal; WOE/IV, monotonicity, calibration,
  and PSI remain robustness controls rather than central novelty;
- resolved-panel nondefault coverage is `0.982982`--`0.992714` and resolved
  default coverage is `0.232570`--`0.363916` across all 40 cells; this is a
  descriptive resolved-label diagnostic only;
- with cutoffs 39 months after issue-month end, the 2016 and 2017 maximum upper
  bounds are `0.879120` and `0.875261`;
- label-Mondrian leaves `27/40` marginal and `109/400` category upper endpoints
  below 0.90; AvgC becomes `1.723718`--`1.785468` and `{0,1}` shares
  `0.723718`--`0.785468`. All 40 aggregate class-gap bounds cross zero;
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
- every structural scenario retains adverse default and miscoverage cells;
  zero scenarios are uniformly favorable or uniformly adverse;
- all 32 overall fit-completion cells remain below nominal, with scenario
  maxima from `0.882594` to `0.884669`; the W7--W8 crossing disappears in the
  all-default scenario and therefore is not scenario-invariant;
- USD 25 floor rounding changes 2,985 positive exposures; the largest rate
  perturbation is `0.001284` percentage points;
- for every binary contrast, identification width is the sum of the unresolved
  loan-wise attainable contribution ranges. It reduces to a count times one
  coefficient only when those contribution ranges are identical.

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
- active-upper-row RHS ranging versus basic slack-row activity ranging in
  HiGHS; only a status-aware interval may support a coverage statement;
- epsilon-near-optimal coordinate mobility versus a distinct exact optimum,
  global optimal-face diameter, or continuous-frontier nonuniqueness;
- tagged retrospective audit versus preregistration or confirmation.
- deterministic finite-archive shortfall versus exact rank-reference
  inference;
- cell-level nominal Holm flags versus unadjusted stratum flags;
- score-Mondrian marginal sets versus label-Mondrian classwise sets;
- class-specific sharp ratio bounds versus gap endpoints that each use a
  shared single-assignment completion for both class ratios (the two endpoint
  completions may differ);
- conformal-fit label timing versus evaluation-endpoint availability; these
  are separate one-factor sensitivities and were not crossed factorially.
- complete structural conditionality versus a selected scenario, universal
  adversity, or deployment guidance.
- four declared fit-label scenarios versus a sharp nonlinear region
  over all `2^215` assignments.
- deterministic floor-with-cash granularity versus reoptimized integer lending.

Do not claim a learner, gamma, ruler, coordinate, or policy winner, universal
direction, selected-set validity, Markov/tail certificate, causal effect, live
deployment result, missingness mechanism, independent temporal replication,
conformal theorem failure from a realized shortfall, ordinary one-point
validity refuted by a joint-block flag, exchangeability from a nonflag,
post-selection FWER, an identified shift mechanism from a flag, or label-Mondrian
repair/equalized coverage.

## Evidence Workflow

```powershell
uv run python scripts/build_ijds_binary_geometry_frontier_v4_evidence.py
just publication-integrity
just lint
just type-check
just type-check-fast
just test
just validate-champion
just ijds-active-check
just submission-build
just submission-check
just ijds-dvc-status
```

The active builder verifies the V4, two-ruler, raw-data, credit-control,
  endpoint, structural, rolling-primary recovery, conformal-set diagnostic,
  joint-block rank reference, individual-age follow-up, label-Mondrian, fit-label completion,
and allocation-granularity
manifests/freezes and every artifact descriptor. The active capsule contains
47 DVC pointers. It emits 27 paper-facing CSV tables, three figures under the
`crpto_ijds_v4_*` naming family, and
`ijds_binary_geometry_frontier_v4_evidence.json`. Consecutive builds must be
byte-identical. The canonical body is `paper/CRPTO_ijds.qmd`; generate official
TeX with `scripts/build_ijds_submission_tex.py` and never edit it by hand.

Manual LaTeX fallback:

```text
pdflatex -> bibtex -> pdflatex -> pdflatex
```

## Protected History

Never overwrite `EXTRACTION_MANIFEST.json`, canonical PD/calibrator, or other
artifacts protected by that manifest. Protected DVC
stages are `crpto.pd.champion`, `crpto.conformal.intervals`,
`crpto.conformal.validation`, `crpto.portfolio.optimization`, and
`crpto.portfolio.bound_exact_eval`.

Earlier studies are preserved in Git history and `D:\crpto_legacy`. The active
paper explains the final method and evidence, not discarded-version chronology.
