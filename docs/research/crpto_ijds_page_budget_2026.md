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
| IJDS body draft | `paper/CRPTO_ijds.pdf` | 14 | Includes references and generic Quarto formatting, not official IJDS pagination. |

This is comfortably below the 25-page conceptual limit even before excluding
references. The exact page budget must be rechecked after porting into the
official IJDS template, but the current draft is not page-constrained.

## Current Usage By Section

Approximate prose counts exclude YAML, submission-target callout, references,
table rows, figure markdown, code fences, captions, and inline citation keys.

| Section | Words | Approx. prose pages |
|---|---:|---:|
| Abstract | 145 | 0.28 |
| Introduction | 484 | 0.92 |
| Related Work | 526 | 1.00 |
| Method | 409 | 0.78 |
| Theory | 338 | 0.64 |
| Experimental Design | 254 | 0.48 |
| Results | 296 | 0.56 |
| Robustness And Comparators | 473 | 0.90 |
| Reproducibility And Companion | 177 | 0.34 |
| Discussion | 412 | 0.78 |
| **Total body prose** | **3,514** | **6.69** |

Body floats after the current polish:

| Float type | Count | Budget heuristic | Approx. pages |
|---|---:|---:|---:|
| Figures | 5 | 0.4 page each | 2.0 |
| Tables | 7 | 0.3 page each | 2.1 |
| **Float allowance** | 12 |  | **4.1** |

**Estimated body length before references: ~10.8 pages.** The Quarto PDF proxy
lands at 14 pages including references, which is consistent with this estimate.

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
