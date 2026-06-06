# CRPTO Book QA Audit - 2026-05-21

> Ported and adapted from the CRPTO research archive
> (`quarto_book_crpto_full_audit_2026-05-21`). The historical audit covered the full
> 123-chapter archive; this CRPTO version keeps the **reusable render-QA checklist
> and the alias/anonymization boundary** for the CRPTO book.

## Three-layer architecture

1. **Intellectual archive** (historical CRPTO archive): full implementation narrative, side
   papers, exploratory lanes, research governance.
2. **CRPTO book** (this repo, `book/`): focused extraction layer for IJDS, online
   supplement and thesis chapter design.
3. **IJDS manuscript/supplement** (`paper/`): anonymized, compact, 25-page paper
   plus reproducibility package.

## Render-QA checklist (run during `just book`)

- **Duplicate Quarto labels.** Watch for duplicate cross-reference labels for:
  ECE, Mondrian quantile, temporal splits, feature-family figures,
  calibration-impact tables, categorical-feature tables, and claim-artifact-test
  tables. Duplicate labels break cross-reference resolution in a full render.
- **Theorem/proposition references.** Do not write `@thm-*`/`@lem-*` handles
  unless a Quarto theorem environment exists; otherwise they look like missing
  bibliography keys. Point to section/equation labels instead.
- **Landing/part counts.** Keep part/chapter descriptions in sync with the actual
  chapter surface.

## Alias / anonymization boundary

- The legacy internal project alias must **not** appear in
  public-facing manuscript surfaces. Public name is **CRPTO** (and "Paper CRPTO"
  for the extraction layer).
- No personal absolute paths or private/non-redistributable material in the
  anonymized package (see `book/chapters/14-release.qmd` checklist).

## Extraction split (confirmed)

- **IJDS body**: CRPTO pipeline, calibrated PD gate, Mondrian conformal intervals,
  `Gamma_CP`, `V`, robust LP, champion, exact region, SPO+ boundary, compact
  governance implications.
- **IJDS supplement**: A3-A18 robustness, Mondrian ablation, funded-set
  composition, fair-lending proxy, MRM, claim-artifact-test map, data/code
  disclosure.
- **Thesis chapter**: foundations, WOE/IV governance, metric-governance caveats,
  full agenda extendida CRPTO/tesis living-lab closure, research stop rules.
- **Out of IJDS body**: GPU, quantum, deep IFRS9 contractual claims, CATE policy
  value, online conformal, MDCP, DLA, OCE/CVaR as a new optimized objective.

## Stop Rule

The QA loop is closed when: the CRPTO book renders; duplicate labels stay cleared;
paper/book guardrail tests pass; and the final manuscript extraction uses CRPTO,
not the legacy internal alias, in public-facing surfaces.
