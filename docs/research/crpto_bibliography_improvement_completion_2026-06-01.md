# CRPTO bibliography improvement completion - 2026-06-01

Source plan:
`docs/research/crpto_bibliography_synthesis_improvement_plan_2026-05-31.md`.

Execution ledger:
`docs/research/crpto_bibliography_improvement_backlog_2026-06-01.md`.

## Scope completed

The implemented work stayed on the safe research-documentation surface:
paper text, supplement text, Quarto book chapters, BibTeX metadata, and
validation. No protected DVC stage was rerun, and no frozen champion artifact was
modified.

## Implemented changes

| Area | Result |
|---|---|
| Paper IJDS | Tightened novelty around the auditable CRPTO bridge; added P2P/Lending Club predecessors; added Hu CRC, ordinal CP credit scoring, CREDO/CREME, and explicit limitations. |
| Supplement | Added decision-certificate landscape, coverage-validity ladder, and P2P/Lending Club predecessor table; strengthened A19--A24 as literature-aligned diagnostics rather than hidden method changes. |
| Chapter 15 | Added credit scoring as allocation infrastructure, with calibration, fairness/noise, credit invisibility, and ECL governance boundaries. |
| Chapter 16 | Added conformal validity ladder and conformal decision ladder. |
| Chapter 20 | Added portfolio lineage from robust optimization and P2P credit portfolio work to CRPTO. |
| Chapter 21 | Added protected-attribute, proxy, noise, BISG, and MRM boundary language. |
| Chapter 22 | Updated state-of-art taxonomy with the new CRPTO bibliography map and reformulated absolute "zero papers" claims into auditable gaps. |
| Chapter 23 | Separated safe diagnostics, literature positioning, and method-changing future work. |
| Bibliography | Added missing decision, robustness, P2P, credit-equity/noise, and future-work references; corrected `aior2025lendingclub`; added `babaei2020p2p`. |

## Deferred by design

The following remain future work because they would change the method, selector,
intervals, policy, or validation protocol:

- Recalibrating intervals or promoting CQR/utility-directed CP.
- Using CRC, CREDO, or CREME as a new selector for the champion.
- Running online conformal validation as a live protocol.
- Running end-to-end conformal or decision-focused retraining.
- Rerunning `crpto.portfolio.bound_exact_eval`, HPO, or protected DVC stages.

No new executable idea appeared that required an improvement-plan v2. The
existing deferred list is sufficient for the next research protocol.

## Validation

| Check | Result |
|---|---|
| Citation-key scan | `NO_MISSING_CITATION_KEYS` |
| Paper render | `uv run -- quarto render paper/CRPTO_ijds.qmd --to html` passed |
| Supplement render | `uv run -- quarto render paper/supplement_ijds.qmd --to html` passed |
| Book render | `uv run -- quarto render book --to html --no-execute` passed |
| Lint | `just lint` passed |
| Smoke tests | `just smoke` passed (`5 passed`) |
| Champion hashes | `just validate-champion` passed (`8 passed`) |
