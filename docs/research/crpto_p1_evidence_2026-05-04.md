# paper-crpto P1 Evidence - 2026-05-04

This dossier records the P1 evidence now materialized around the official
`paper-thesis-final-economic-2026-04-06` champion. It does not reopen the
champion search.

## Standalone Scope - 2026-05-12

The evidence here is part of the independent paper-crpto dossier. It can be
rendered, audited and cited from the standalone Quarto book, but it should still
be read as evidence around the frozen champion rather than a new search.

## Generated artifacts

- `reports/crpto/tables/crpto_tableA3_nested_holdout.csv`
- `reports/crpto/tables/crpto_tableA3_nested_holdout.tex`
- `reports/crpto/tables/crpto_tableA4_segment_period_sensitivity.csv`
- `reports/crpto/tables/crpto_tableA4_segment_period_sensitivity.tex`
- `reports/crpto/tables/crpto_tableA5_decision_aware_selector.csv`
- `reports/crpto/tables/crpto_tableA5_decision_aware_selector.tex`
- `reports/crpto/tables/crpto_tableA6_synthetic_shift.csv`
- `reports/crpto/tables/crpto_tableA6_synthetic_shift.tex`
- `reports/crpto/tables/crpto_tableA7_funded_set_loans.csv`
- `reports/crpto/tables/crpto_tableA7_funded_set_loans.tex`
- `reports/crpto/tables/crpto_tableA8_funded_set_composition.csv`
- `reports/crpto/tables/crpto_tableA8_funded_set_composition.tex`
- `reports/crpto/tables/crpto_tableA9_strict_temporal_holdout.csv`
- `reports/crpto/tables/crpto_tableA9_strict_temporal_holdout.tex`
- `reports/crpto/tables/crpto_tableA10_conformal_finalist_exact_bound_eval.csv`
- `reports/crpto/tables/crpto_tableA10_conformal_finalist_exact_bound_eval.tex`
- `reports/crpto/tables/crpto_tableA11_enhanced_synthetic_shift.csv`
- `reports/crpto/tables/crpto_tableA11_enhanced_synthetic_shift.tex`
- `docs/research/crpto_conditional_tightening_appendix_2026-05-04.md`
- `models/crpto_evidence_status.json`
- `docs/research/crpto_p1_evidence_2026-05-04.md`

## Scope notes

- The nested-holdout evidence is an artifact-level staged confirmation
  chain: 5K screening, 25K refinement, and 276K full OOT confirmation. It
  is complemented by a strict temporal funded-set confirmation split in
  `crpto_tableA9_strict_temporal_holdout.csv`. That strict split evaluates
  the frozen policy; it does not reopen the champion search.
- The decision-aware conformal selector is a CROMS-style screen over the
  three conformal finalists. Exact 276K bound-aware evaluations now exist
  for ranks 1, 2 and 3, while ranks 2 and 3 still fail the conformal policy
  gate through minimum group coverage.
- Synthetic shift checks include both covariate reweighting and adversarial
  label-flip stress scenarios on OOT labels. They are stronger than the
  first pass, but they are still not an external dataset replacement.

## Key status

- Nested final return: `170464.542928`.
- Nested final V: `0.028875`.
- Decision-aware selected rank: `1`.
- Worst segment coverage 90: `0.903203`.
- Worst synthetic coverage 90: `0.929714`.

## Hardening status

- `strict_temporal_holdout`: `implemented`.
- `funded_set_export`: `implemented`.
- `funded_set_composition`: `implemented`.
- `conformal_finalist_exact_eval`: `implemented`.
- `enhanced_synthetic_shift`: `implemented`.
- `conditional_tightening`: `implemented_as_conditional_appendix`.
