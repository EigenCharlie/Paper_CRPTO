# CRPTO Mini-Book Expansion Audit - 2026-05-21

> Ported and adapted from the CRPTO research archive
> (`crpto_mini_book_expansion_audit_2026-05-21`). In this CRPTO project the prior
> mini-book is **not** recreated as a separate book; its unique editorial content
> is **folded into existing book chapters** (see folding map below). This doc is
> the traceability record of why those chapter additions exist.

## Decision

CRPTO is the shared spine for both the IJDS paper and the master's thesis over
the next 6-12 months. It must not duplicate the full intellectual archive. It adds
extraction controls: evidence spine, page budget, reviewer-defense bank, thesis
expansion ledger, release checklist and negative-results registry.

## Editorial additions (folded into child chapters)

| Editorial control | Child destination |
| --- | --- |
| Evidence spine (claim -> artifact -> test) + reopening rule | `book/chapters/13-trazabilidad.qmd` |
| IJDS page-budget ledger + supplement packages A-F | `book/chapters/06-blueprint-manuscrito.qmd` |
| Reviewer-defense bank (expanded to 13 objections) | `book/chapters/06b-guia-editorial-claims.qmd` |
| Stop-rules + 6 editorial gates + anonymization/double-blind checklist | `book/chapters/14-release.qmd` |
| Roadmap 6/12 months + P0-P3 backlog + intake matrix + thesis expansion map | `book/chapters/23-apendices-regulatorios-y-future-work.qmd` |
| Negative-results registry (from regret-auditability closure + agenda extendida CRPTO/tesis) | `book/chapters/07-apendice-robustez.qmd` / `23` |
| Figure/table decision log (3 figures, 2-3 tables IJDS body) | `book/chapters/06-blueprint-manuscrito.qmd` |

## Stop Rule

Do not reopen champion selection or agenda extendida CRPTO/tesis promotion. A parked item may enter the
manuscript spine only if it changes a claim, appendix table, figure, reviewer
response or thesis defense section, and remains consistent with
`models/final_project_promotion.json`.
