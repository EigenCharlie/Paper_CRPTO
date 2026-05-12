# paper-crpto Journal Package - 2026-05-04

This dossier records the journal-oriented tables and figures generated from
frozen CRPTO artifacts. It does not reopen the champion search.

## Standalone Scope - 2026-05-12

This package is the journal/appendix layer for `Paper_CRPTO`. It is intentionally
larger than the short paper: A12--A19, Figures 12--15 and the robustness notes
can be selected into a journal appendix, reviewer response or future thesis
chapter without changing the official champion.

## Generated artifacts

- `reports/crpto/tables/crpto_tableA12_tail_risk_oce_cvar.csv`
- `reports/crpto/tables/crpto_tableA12_tail_risk_oce_cvar.tex`
- `reports/crpto/tables/crpto_tableA13_satisficing_margins.csv`
- `reports/crpto/tables/crpto_tableA13_satisficing_margins.tex`
- `reports/crpto/tables/crpto_tableA14_dependency_cluster_diagnostics.csv`
- `reports/crpto/tables/crpto_tableA14_dependency_cluster_diagnostics.tex`
- `reports/crpto/tables/crpto_tableA15_leave_one_period_stress.csv`
- `reports/crpto/tables/crpto_tableA15_leave_one_period_stress.tex`
- `reports/crpto/tables/crpto_tableA16_bootstrap_funded_set_metrics.csv`
- `reports/crpto/tables/crpto_tableA16_bootstrap_funded_set_metrics.tex`
- `reports/crpto/tables/crpto_tableA17_budget_cap_lgd_sensitivity.csv`
- `reports/crpto/tables/crpto_tableA17_budget_cap_lgd_sensitivity.tex`
- `reports/crpto/tables/crpto_tableA18_robust_region_policy_family.csv`
- `reports/crpto/tables/crpto_tableA18_robust_region_policy_family.tex`
- `reports/crpto/tables/crpto_tableA19_regret_auditability_frontier.csv`
- `reports/crpto/tables/crpto_tableA19_regret_auditability_frontier.tex`
- `reports/crpto/figures/crpto_fig12_crpto_conceptual_pipeline.png`
- `reports/crpto/figures/crpto_fig12_crpto_conceptual_pipeline.pdf`
- `reports/crpto/figures/crpto_fig13_alpha_gamma_funded_set.png`
- `reports/crpto/figures/crpto_fig13_alpha_gamma_funded_set.pdf`
- `reports/crpto/figures/crpto_fig14_robust_region_heatmap.png`
- `reports/crpto/figures/crpto_fig14_robust_region_heatmap.pdf`
- `reports/crpto/figures/crpto_fig15_regret_auditability_frontier.png`
- `reports/crpto/figures/crpto_fig15_regret_auditability_frontier.pdf`

## Scope notes

- A12--A19 are diagnostic robustness, comparator and packaging tables.
- Budget and segment-cap sensitivity are funded-set diagnostics, not
  re-optimized portfolios.
- Tail-risk and bootstrap return columns are funded-set repricing diagnostics;
  the official champion return remains sourced from `final_project_promotion.json`.
- `src/optimization/tail_satisficing_objective.py` exposes the same
  OCE/CVaR/satisficing primitives as a future-experiment scaffold,
  but this package still does not promote a new objective.
- The official champion remains `bound_aware_276k_economic_champion`.

## Appendix map

| Artifact | Purpose | Caveat |
|---|---|---|
| A12 tail risk OCE/CVaR | Adds funded-set tail-risk diagnostics under LGD alternatives. | Diagnostic repricing, not a new champion metric. |
| A13 satisficing margins | Converts champion evidence into OR-style pass/margin checks. | Editorial thresholds must be justified if moved to body. |
| A14 dependency clusters | Documents period/grade concentration for the tightening appendix. | Does not prove conditional independence. |
| A15 leave-one-period stress | Reweights the funded set by period. | Not a re-optimized portfolio. |
| A16 bootstrap funded-set metrics | Adds empirical intervals for realized funded-set quantities. | Not a conformal guarantee. |
| A17 budget/LGD/cap sensitivity | Checks practical sensitivity to budget, LGD and segment caps. | Cap checks are diagnostics, not solver constraints. |
| A18 robust region by family | Summarizes the `45/45` alpha01-safe region by `risk_tolerance x gamma`. | Bound-aware family only. |
| A19 regret-auditability frontier | Compares two-stage, SPO+ and CRPTO robust on regret versus verifiable risk controls. | Trade-off diagnostic, not a new champion selector. |

## Quarto integration

- `book/chapters/06-blueprint-manuscrito.qmd` uses
  these artifacts to define the paper outline and final table/figure plan.
- `book/chapters/07-apendice-robustez.qmd`
  renders A12--A19 and Figures 12--15.
