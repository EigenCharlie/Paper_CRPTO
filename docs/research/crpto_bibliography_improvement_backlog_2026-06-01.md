# CRPTO bibliography improvement backlog - 2026-06-01

Source plan:
`docs/research/crpto_bibliography_synthesis_improvement_plan_2026-05-31.md`.

This backlog is the execution ledger for the bibliography-driven improvement
goal. Status values:

- `todo`: not started.
- `doing`: actively being edited or validated.
- `done`: implemented and checked.
- `deferred`: not executed because it changes the champion or needs a new
  research protocol.
- `superseded`: replaced by a better scoped item.

## Paper IJDS

| ID | Item | Status | Evidence |
|---|---|---|---|
| P-IJDS-01 | Tighten novelty claim around auditable CRPTO bridge, not AUC leaderboard or generic CP algorithm. | done | `paper/CRPTO_ijds.qmd` |
| P-IJDS-02 | Add P2P/Lending Club domain predecessors: Guo, Chi, Babaei/Torkian as appropriate. | done | `paper/CRPTO_ijds.qmd`, `book/references.bib` |
| P-IJDS-03 | Add Hu et al. 2026 as close conformal-robustness neighbor. | done | `paper/CRPTO_ijds.qmd`, `book/references.bib` |
| P-IJDS-04 | Acknowledge ordinal CP credit scoring as claim boundary. | done | `paper/CRPTO_ijds.qmd`, `book/references.bib` |
| P-IJDS-05 | Strengthen limitations: no exact conditional coverage, no online/live validation, no legal fair-lending certification, no end-to-end uncertainty learning. | done | `paper/CRPTO_ijds.qmd` |

## Supplement

| ID | Item | Status | Evidence |
|---|---|---|---|
| P-SUP-01 | Add decision certificate landscape table. | done | `paper/supplement_ijds.qmd` |
| P-SUP-02 | Add coverage validity ladder table. | done | `paper/supplement_ijds.qmd` |
| P-SUP-03 | Add P2P/Lending Club predecessor table. | done | `paper/supplement_ijds.qmd` |
| P-SUP-04 | Strengthen A19-A24 prose/captions with new literature while keeping diagnostics non-promotional. | done | `paper/supplement_ijds.qmd` |

## Book / Thesis

| ID | Item | Status | Evidence |
|---|---|---|---|
| P-BOOK-15 | Expand chapter 15 with credit scoring as allocation infrastructure, equity, noise, credit invisibles, ECL governance. | done | `book/chapters/15-fundamentos-riesgo-ml.qmd` |
| P-BOOK-16 | Add validity ladder and decision ladder to chapter 16. | done | `book/chapters/16-fundamentos-conformal-optimizacion.qmd` |
| P-BOOK-20 | Add portfolio lineage from Markowitz/Bertsimas/data-driven RO/P2P/CRPTO to chapter 20. | done | `book/chapters/20-portafolio-policy.qmd` |
| P-BOOK-21 | Add fairness, noise, BISG, protected-attribute and MRM boundary language to chapter 21. | done | `book/chapters/21-gobernanza-explicabilidad-dataset.qmd` |
| P-BOOK-22 | Replace/update state-of-art taxonomy with 61-paper CRPTO bibliography map. | done | `book/chapters/22-literatura-trazabilidad-entorno.qmd` |
| P-BOOK-23 | Separate future work into method-changing vs safe diagnostics. | done | `book/chapters/23-apendices-regulatorios-y-future-work.qmd` |

## Bibliography

| ID | Item | Status | Evidence |
|---|---|---|---|
| P-BIB-01 | Add missing references: Bertsimas-Kallus, Bertsimas-Gupta-Kallus, Hu, Kawasumi, CREDO, CREME, utility-directed CP, CDT, fairness/noise/domain papers. | done | `book/references.bib` |
| P-BIB-02 | Correct suspicious `aior2025lendingclub` author metadata. | done | `book/references.bib` |
| P-BIB-03 | Check all new citation keys resolve in paper/supplement/book. | done | Quarto render/logs |

## Safe Artifact / Documentation Improvements

| ID | Item | Status | Evidence |
|---|---|---|---|
| P-DOC-01 | Create/update literature positioning table conceptually, without touching frozen artifacts. | done | supplement/book/docs |
| P-DOC-02 | Document CREDO-lite and CREME/robust-region as future decision-certificate extensions, not champion selectors. | done | supplement/book/docs |
| P-DOC-03 | Completion report maps every source-plan item to result. | done | `docs/research/crpto_bibliography_improvement_completion_2026-06-01.md` |
| P-DOC-04 | Improvement plan v2 if new executable ideas appear during execution. | done | No new executable v2 item emerged; existing deferred protocol list retained. |

## Validation

| ID | Item | Status | Evidence |
|---|---|---|---|
| P-VAL-01 | Check citation keys after edits. | done | `NO_MISSING_CITATION_KEYS` |
| P-VAL-02 | Render paper/supplement if edited. | done | `uv run -- quarto render paper/...` |
| P-VAL-03 | Render book no-execute if chapters edited. | done | `uv run -- quarto render book --to html --no-execute` |
| P-VAL-04 | Run safe tests/lint where feasible. | done | `just lint`, `just smoke` |
| P-VAL-05 | Validate champion hashes if any risk surface touched. | done | `just validate-champion` |

## Deferred By Design Unless A New Research Protocol Is Approved

| ID | Item | Status | Reason |
|---|---|---|---|
| P-DEF-01 | Recalibrate conformal intervals or replace promoted intervals with CQR/utility-directed CP. | deferred | Would touch protected conformal artifacts. |
| P-DEF-02 | Run Hu-style Conformal Robustness Control as a new promoted method. | deferred | Method-changing research lane. |
| P-DEF-03 | Run end-to-end conformal calibration / E2E conditional robust optimization. | deferred | Method-changing research lane. |
| P-DEF-04 | Use CREME to select a new robustness level/champion. | deferred | Would turn a diagnostic into a new selector. |
| P-DEF-05 | Re-run `crpto.portfolio.bound_exact_eval` or HPO. | deferred | Protected champion/search stage. |
