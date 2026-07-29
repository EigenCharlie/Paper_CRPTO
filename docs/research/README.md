# Active Research Dossier

This directory contains only records needed to understand or reproduce the
current CRPTO IJDS paper. A dated document is evidence only when the active
claim or source registry names it.

## Reading Order

1. `active_claims_2026-07-14.md`
2. `ijds_binary_geometry_frontier_v4_protocol_2026-07-12.md`
3. `ijds_evaluation_endpoint_recovery_v3_protocol_2026-07-14.md`
4. `ijds_normalized_objective_frontier_protocol_2026-07-12.md`
5. `ijds_normalized_objective_frontier_v1c_protocol_2026-07-13.md`
6. `ijds_two_ruler_endpoint_recovery_v3_protocol_2026-07-14.md`
7. `ijds_raw_data_contract_protocol_2026-07-13.md`
8. `ijds_credit_risk_controls_protocol_2026-07-13.md`
9. `ijds_label_lag_sensitivity_protocol_2026-07-14.md`
10. `ijds_endpoint_availability_sensitivity_protocol_2026-07-14.md`
11. `ijds_portfolio_structure_sensitivity_v6_protocol_2026-07-15.md`
12. `ijds_fit_label_completion_sensitivity_protocol_2026-07-16.md`
13. `ijds_allocation_granularity_sensitivity_protocol_2026-07-16.md`
14. `ijds_conformal_set_diagnostics_protocol_2026-07-21.md`
15. `ijds_exchangeability_transport_test_protocol_2026-07-21.md`
16. `ijds_rolling_origin_individual_age_followup_protocol_2026-07-21.md`
17. `ijds_rolling_origin_equal_followup_protocol_2026-07-21.md` (parent provenance)
18. `ijds_label_mondrian_sensitivity_protocol_2026-07-21.md`
19. `../../configs/ijds_active_evidence_sources.yaml`
20. `../../configs/ijds_claim_ledger.yaml`
21. `../../reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json`

## Active Interpretation

The paper audits one frozen ML--conformal--optimization pipeline. Under the
declared six-month outcome-availability rule, all five learner specifications
have all eight sharp all-candidate coverage upper bounds below 0.90. Those
40/40 endpoints are finite-archive descriptions, not formal rejections. The
separate combined-rank lineage has 31/40 learner-window cells meeting its locked
Bonferroni-within-cell and Holm-across-cell nominal thresholds. That reference
law assumes joint exchangeability of each calibration stratum with its entire
target block, a stronger null than the usual one-future-point marginal
split-conformal condition. Because the family and pattern were inspected
before the lock, these flags carry no post-selection or study-wide FWER claim.
With cutoffs 39 months after each issue-month end, all 16 CatBoost
origin-window upper endpoints remain
below nominal. Label-Mondrian changes the marginal states to 27 shortfalls, 12
crossings, and one at-or-above-nominal cell, with 109/400 category shortfalls;
it is not a conditional-validity repair. Binary residual geometry changes
sharply near a prevalence threshold. Portfolio contrast signs depend on the
outcome-blind ruler, coordinate, and finite evaluated comparator support. All
216 endpoint envelopes over registered cap values spanning `[0.05, 0.12]`
include zero; this does not compute continuous-support extrema. No learner,
missingness encoding, conformal method,
gamma, ruler, coordinate, scenario, or policy is selected.

## Literature

Bibliographic metadata belongs in `paper/references.bib`. The local
`Papers_tesis/` directory contains the working PDF corpus and is ignored by
Git. Do not commit copyrighted PDFs. Literature supports positioning and
assumptions; it does not override the registered empirical evidence.
The complete local-corpus audit is
`conformal_literature_corpus_audit_2026-07-21.md`; the two nonlocal 2026
decision-calibration papers found in the final search and their theorem-level
boundaries are recorded in
`conformal_decision_sota_lastmile_2026-07-26.md`. They do not enter the local
PDF checksum until their bytes can be acquired and hashed.

## Historical Boundary

Earlier paper versions, search results, policy promotions, and development
memos are archived at `D:\crpto_legacy` and in Git history. A small number of
old paths remain in the repository only because immutable DVC or extraction
hashes require them. They are not active scientific records and should not be
summarized in the manuscript.

## Maintenance Rule

Do not add routine progress memos. Update the relevant protocol, registry,
test, builder, or manuscript surface directly. Create a new protocol only when
a scientific object changes before execution.
