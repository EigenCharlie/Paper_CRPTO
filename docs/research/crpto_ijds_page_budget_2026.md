> **RESEARCH NOTE** -- IJDS page-budget ledger for the CRPTO manuscript body.
> Working material for submission planning. The body source of truth is
> `paper/CRPTO_ijds.qmd`; the final production surface should still be the
> official IJDS/INFORMS LaTeX template.

# CRPTO -- IJDS Page-Budget Ledger (2026-06-01)

IJDS caps the manuscript body at **25 pages**, excluding references and the
online supplement. The official `informs4.cls` template is not available in this
repository, so this ledger uses two proxies:

- Quarto PDF dry run: `uv run -- quarto render paper/CRPTO_ijds.qmd --to pdf`.
- Word/floats proxy: body prose by section plus a conservative float allowance.

## Dry-Run Result

The Quarto article PDF proxy rendered successfully on 2026-06-01.

| Surface | Local file | Proxy pages | Scope caveat |
|---|---|---:|---|
| IJDS body draft | `paper/CRPTO_ijds.pdf` | 15 | Includes references and generic Quarto formatting, not official IJDS pagination. |

This is comfortably below the 25-page conceptual limit even before excluding
references. The exact page budget must be rechecked after porting into the
official IJDS template, but the current draft is not page-constrained.

## Current Usage By Section

Approximate prose counts exclude YAML, submission-target callout, references,
table rows, figure markdown, code fences, captions, and inline citation keys.

| Section | Words | Approx. prose pages |
|---|---:|---:|
| Abstract | 164 | 0.31 |
| Introduction | 499 | 0.95 |
| Related Work | 536 | 1.02 |
| Method | 569 | 1.08 |
| Theory | 481 | 0.92 |
| Experimental Design | 260 | 0.50 |
| Results | 401 | 0.76 |
| Robustness And Comparators | 510 | 0.97 |
| Reproducibility And Companion | 177 | 0.34 |
| Discussion | 420 | 0.80 |
| **Total body prose** | **4,017** | **7.65** |

Body floats after the current polish:

| Float type | Count | Budget heuristic | Approx. pages |
|---|---:|---:|---:|
| Figures | 5 | 0.4 page each | 2.0 |
| Tables | 9 | 0.3 page each | 2.7 |
| **Float allowance** | 14 |  | **4.7** |

**Estimated body length before references: ~12.4 pages.** The Quarto PDF proxy
lands at 15 pages including references, which is consistent with this estimate.

## Interpretation

The draft has enough headroom for IJDS. The risk is no longer "too long"; the
main editorial risk is whether the body gives reviewers enough evidence without
feeling like a bibliography dump. The current version uses the headroom well:
the body now includes the bound claim stack, the closer-work boundary, the
exact certificate, the reviewer claim checks, and the regret-auditability
frontier.

## Before Real Submission

- Port the manuscript into the official IJDS/INFORMS LaTeX template and re-count
  body pages there.
- If the official template gets tight, demote the body-level reviewer-check
  table or the robust-region heatmap to the supplement before cutting theory.
- Keep the bound claim stack in the body; it explains the method faster than
  another paragraph.
- Keep the exact certificate in the body; it is the strongest auditability
  object in the paper.
