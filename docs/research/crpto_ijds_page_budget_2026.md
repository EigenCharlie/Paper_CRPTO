> **RESEARCH NOTE** — IJDS page-budget ledger for the CRPTO manuscript body.
> Working material for submission planning. The body source of truth is
> `paper/CRPTO_ijds.qmd`; the LaTeX surface is
> `paper/submission/CRPTO_ijds_submission.tex`.

# CRPTO — IJDS Page-Budget Ledger (2026)

IJDS caps the manuscript body at **25 pages**, excluding references and the online
supplement. This ledger estimates current usage so the body can be tuned before
submission. Because the official `informs4.cls` is gatekept by the INFORMS author
portal and is **not** on CTAN/TeX Live, the submission `.tex` cannot be compiled
locally for exact pagination; this ledger uses a word-count proxy instead.

## Method

- Source: `paper/CRPTO_ijds.qmd` body prose (front matter, the submission-target
  callout, code, table rows, figure markup and citation keys are excluded from the
  word count).
- Proxy: **~525 words/page** for a 1.5-spaced single-column journal body
  (`\OneAndAHalfSpacedXI`, the informs4 default). This is conservative; INFORMS
  body pages often run a little denser.
- Floats: each in-body figure is budgeted at ~0.4 pg and each table at ~0.3 pg.

## Current usage by section

| Section | Words | ~Pages |
|---|---:|---:|
| Abstract | 125 | 0.24 |
| Introduction | 406 | 0.77 |
| Related Work | 426 | 0.81 |
| Method | 427 | 0.81 |
| Theory | 174 | 0.33 |
| Experimental Design | 254 | 0.48 |
| Results | 183 | 0.35 |
| Robustness and Comparators | 439 | 0.84 |
| Reproducibility and Companion | 126 | 0.24 |
| Discussion | 263 | 0.50 |
| **Total (prose only)** | **2,823** | **5.38** |

Body floats: **4 figures** (pipeline, alpha–gamma, robust-region heatmap,
regret-auditability frontier) ≈ 1.6 pg; **2 tables** (core metrics, regret
frontier) ≈ 0.6 pg.

**Estimated body length: ~7.6 pages of 25.**

## Reading: the constraint is inverted

The original parent roadmap framed A3 as "compress the body to the 25-page
budget." For the CRPTO manuscript as written, that is **not** the binding
constraint: the draft is a compact, extended-abstract-style body at roughly
**30% of the page allowance**. The risk for an IJDS submission is the opposite —
a body that reads thin against reviewer expectations for a full research article.

The ~17 pages of headroom should be used to **promote the strongest supplement
material into the body**, not to cut. Recommended promotions, in priority order:

| Target section | Promote from supplement | Why it strengthens the body | Est. add |
|---|---|---|---|
| Method | Formal `u_i(α) → robust LP` constraint derivation; explicit objective + constraints | Reviewers expect the optimization model written out, not described | +1.5 pg |
| Theory | The Markov proposition statement + proof sketch, and the cluster-aware conditional bound | Currently only narrated; IJDS wants the lemma/proof in-body | +2.0 pg |
| Experimental Design | Split sizes table, feature-contract summary, leakage controls | Makes the empirical design auditable at a glance | +1.0 pg |
| Results | A18 robust-region policy-family table (compact), funded-set composition by grade | Direct evidence the 45/45 region is not a single point | +1.5 pg |
| Robustness | One compact A22 (CVaR/OCE) panel + A23 multi-distribution summary | Shows tail and distribution robustness in-body, not only appendix | +1.5 pg |

Promoting these would bring the body to roughly **15–16 pages**, a healthy IJDS
length that still leaves comfortable margin and keeps A3–A24 in the supplement.

## Hard limits to respect when expanding

- Keep **3–4 figures** as the visual spine; additional evidence goes to the
  supplement to avoid float clutter.
- Do **not** promote method-changing P2/P3 variants (optimized OCE/CVaR objective,
  online conformal, causal layers) into the body — they remain future work.
- Every promoted number must trace to a frozen artifact (the claim→artifact→test
  rule), so promotion is a writing task, not a re-run.

## Action

A3 is therefore re-scoped from "trim to 25 pp" to **"expand the body from ~7.6 to
~15 pp by promoting the listed supplement material, capped well under 25 pp."**
This is a finalization-time writing task and is gated on porting the prose into
the official `informs4` template (which requires the portal download).
