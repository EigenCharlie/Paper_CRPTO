# CRPTO IJDS Readiness Audit - 2026-06-05

This memo audits the current `Paper_CRPTO` submission surface against the IJDS
fit, reviewer-risk, artifact, and reproducibility criteria. It is intentionally
paper-facing and self-contained: it does not reference exploratory laboratory
paths or credentials.

## Executive Decision

The current package is strong enough to move toward IJDS production polish. The
highest-value remaining work is **not another champion search** and not another
dataset hunt. The most useful work is:

1. port the body into the official IJDS LaTeX template and re-check 25-page fit;
2. perform a final double-anonymous sweep of the body, supplement, cover letter
   and submission PDF;
3. keep the multidataset layer as A25--A34, with Freddie all-candidate
   exhaustiveness and price-of-robustness scaling as the main new defenses
   against the single-dataset critique;
4. avoid method-changing runs unless they are explicitly scoped as a new paper
   or future protocol.

## 2026-06-06 Closeout Update

The active submission previews are now the anonymous body and supplement PDFs
only: `paper/CRPTO_ijds.pdf` (24-page Chrome-print verification proxy) and
`paper/supplement_ijds.pdf` (22-page proxy). The full-book `CRPTO.pdf` is no
longer maintained because it is too large and layout-fragile for the current
thesis stage; the Quarto book remains the canonical HTML dossier until the
master's thesis section set and APA layout are fixed. The editor-facing
cover-letter/data-code disclosure draft now lives in
`paper/submission/COVER_LETTER_AND_DISCLOSURE.md`, separate from the
double-anonymous reviewer packet.

## IJDS Fit Gate

The IJDS public guidelines say the journal expects innovative data science
methodology for decision-making environments, with four components: data,
models/algorithms, managerial/engineering/industrial relevance, and practical or
ethical implications. They also state that initial submissions should not exceed
25 pages in journal style, excluding references and appendices; online
supplements should be separate; and double-anonymous review applies to
submissions on and after 2025-01-01.

| IJDS expectation | CRPTO evidence | Readiness |
|---|---|---|
| Real data | Lending Club OOT plus Prosper and Freddie/Mendeley static external replications. | Ready. |
| Models / algorithms | Frozen CatBoost PD -> Mondrian conformal intervals -> robust portfolio LP -> exact funded-set audit. | Ready. |
| Decision relevance | Credit allocation under budget/risk appetite; funded set, return, price of robustness, MRM/fairness diagnostics. | Ready. |
| Practical and ethical implications | Reproducibility companion, governance/MRM, fair-lending caveat, anonymization boundary, no overclaiming. | Ready with final submission sweep. |
| Page limit and supplement split | Body is ~7.7k words with six figures; supplement carries A3--A34. Local Chrome-print proxy is 24 pages body / 22 pages supplement. | Needs official template page check. |
| Data/code disclosure | Repository has code, DVC/MLflow lineage, manifests, and source logs; editor-facing wording is separated from the reviewer packet. | Ready after final venue disclosure timing decision. |

## Current Strongest Paper Claims

| Claim | Why it is now defensible | Primary artifact |
|---|---|---|
| CRPTO is a decision pipeline, not a classifier paper. | The body centers funded-set economics, exact alpha-safe audit and robust-region evidence. | `paper/CRPTO_ijds.qmd`, Fig. 1, Fig. 13, Fig. 14. |
| The exact certificate is honest about assumptions. | Theory separates deterministic identity, weighted-validity assumption and frozen empirical certificate. | Bound claim stack, supplement Appendix A. |
| The champion is not a single lucky point. | `45/45` robust-region policies pass the exact alpha01 check. | `crpto_tableA18_robust_region_policy_family.csv`. |
| The single-dataset critique is materially reduced. | Prosper and Freddie pass global gates; Freddie is solved on all `1,396,053` OOT candidates and the price-of-robustness scaling is reported. | A25--A34, Fig. 24--25, `crpto_multidataset_external_status.json`. |
| Regret and auditability are not confused. | SPO+ is framed as low-regret; CRPTO is framed as auditable risk control. | A19, Fig. 15. |

## Multidataset Readiness

The multidataset front is now paper-ready as a **static external replication**:

- Prosper final-status loans: `54,807` rows, `10,531` OOT candidates,
  coverage90 `0.9205`, alpha01 coverage `0.9943`, all-candidate robust LP
  `$199,419`.
- Freddie FM48: `3,173,355` rows, `1,396,053` OOT candidates, coverage90
  `0.9745`, alpha01 coverage `0.9907`, all-candidate robust LP `$1,291,228`.
- Freddie exhaustiveness: the robust objective is unchanged at `500k`, `1M`,
  and all candidates; worst funded rank is `551`; zero funded loans are outside
  the top-250k screen.
- Prosper default-definition sensitivity: main, `Defaulted` only and
  `Chargedoff` only all pass the global gates.
- Freddie red/green sensitivity: combined and green pass alpha01; red is
  documented as a caveat (`0.9850`) rather than promoted.

The correct wording is: CRPTO preserves global conformal gates and positive
robust LP value on two external economic credit datasets. The wrong wording is:
the Lending Club exact funded-set theorem automatically transfers to every
external subgroup.

## What We Should Not Run Now

| Candidate run | Decision | Reason |
|---|---|---|
| Reopen Lending Club champion search | Do not run. | It risks changing the official story and is not needed for IJDS fit. |
| Add Home Credit back into main claim | Do not run. | It lacks a clean investment-return/exposure contract. |
| New dataset hunt before submission | Do not run. | Freddie + Prosper already answer the reviewer concern; new datasets add engineering risk. |
| Online conformal / live deployment validation | Future work only. | Requires a prospective protocol, not a historical replay. |
| SPO+ + conformal hybrid training | Future paper. | Method-changing and would blur the post-hoc governance contribution. |
| OCE/CVaR as promoted objective | Future paper. | A22 is already a useful challenger audit; promotion would reopen the champion. |

## What Could Still Improve Acceptance Odds

| Priority | Action | Surface | Why it helps |
|---|---|---|---|
| P0 | Compile the final body in the official IJDS template and re-count pages. | Submission PDF. | The Quarto proxy is under budget, but IJDS template is the real gate. |
| P0 | Run final anonymous sweep for author names, public URLs, acknowledgments and metadata. | Body, supplement, submission PDF. | Double-anonymous review is now required. |
| P0 | Verify all paper/supplement figures are included near first citation in the template PDF. | Submission PDF. | IJDS explicitly asks tables/figures to remain near citations. |
| P1 | Add the multidataset reviewer question to the book reviewer map. | Book. | Done in the A25--A34 reviewer-map pass. |
| P1 | Keep the readiness memo and publication-target YAML aligned. | Docs/config. | Updated through A34/Fig. 25 closeout. |
| P1 | Prepare a cover-letter paragraph that frames CRPTO as data science for decisions. | Submission package. | Done in `paper/submission/COVER_LETTER_AND_DISCLOSURE.md`. |

## QA Results From This Audit

The following checks were run or inspected during this readiness pass:

- Quarto renders for `paper/CRPTO_ijds.qmd`, `paper/supplement_ijds.qmd`,
  `book/chapters/30-replicacion-multidataset.qmd` and
  `book/chapters/07-apendice-robustez.qmd` passed in the previous
  multidataset integration pass.
- `uv run pytest tests/test_quarto_book_guardrails.py
  tests/test_publication_targets.py tests/test_manifest_regression.py -q`
  passed with `14` tests.
- `uv run --extra dev ruff check
  scripts/build_multidataset_external_replication.py
  tests/test_publication_targets.py` passed.
- A citation/asset scan over paper, supplement and book chapters found no
  missing local figure assets, no missing cross-references and no figure labels
  lacking alt text. One false-positive citation scan item came from punctuation
  around `@powell2026sdam`; the BibTeX key exists.
- A sensitive-string scan found no credentials, dataset-root paths or
  exploratory-lab references in the paper-facing sources checked.

## Stop Rule

For the current IJDS submission, stop adding experiments when a proposed run
does not change one of these body claims:

1. decision-focused data science contribution;
2. exact funded-set audit on the frozen Lending Club champion;
3. robust-region stability;
4. external static replication on Prosper/Freddie;
5. reproducible artifact governance.

Everything else belongs in the book, a future-work paragraph, or a separate
named protocol.
