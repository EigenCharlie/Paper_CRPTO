# ScholarOne Final Checklist

Use only after scientific content and official PDFs are frozen.

## Files

| File | Reviewer-facing | Requirement |
|---|:---:|---|
| Official anonymous manuscript PDF | Yes | Built from `CRPTO_ijds_submission.tex`, citation-clean, within page limit |
| Anonymous online supplement PDF | Yes | Correct title, complete S1--S7/proofs, visually inspected |
| Separate title page | No | Complete affiliation, email, ORCID and declarations |
| IJDS Data and Code Disclosure Form | Editor/system | Match package plan and raw-data terms |
| Cover letter | Editor | Match active title, method, results and limitations |
| Reproducibility archive/note | Editor/system | Sanitized identity, paths, remotes and credentials |

## Full Local Gate

```powershell
just submission-check
uv run dvc status --no-updates
git status --short
```

`submission-check` includes active evidence validation, publication integrity,
lint, Mypy, advisory `ty`, the full pytest suite, protected champion validation,
both Quarto renders, and the official TeX compile.

## Scientific Reconciliation

- Title is "CRPTO: When Marginal Conformal Coverage Meets Maturity-Safe Credit
  Portfolio Selection" on all surfaces.
- Active universe is 540,121; no resolved-status filter is implied.
- Active policy is `q=0.75p+0.25u`, `tau=0.17`.
- Development guardrail-minus-point realized payoff is `+$50,260.10`, while
  model-expected payoff is `-$72,701.67`; both directions reverse or remain
  adverse in locked OOT as stated in Main Table 6.
- Primary candidate coverage is `[0.854923, 0.879692]`.
- Guardrail-minus-point payoff is `[-$322,703.79, -$58,040.34]`.
- Guardrail-minus-point default is `[-0.046275, -0.020093]`.
- Guardrail-minus-point miscoverage is `[0.008822, 0.029850]`.
- Standardized payoff is never called realized investor return or IRR.
- No selected-set, causal, prospective, Markov, or fair-lending claim appears.
- Compact-v7 headline values and A35--A40 are historical only.
- The closest-work table, three propositions, development-to-OOT reversal, and
  managerial audit card appear on both body sources with the same boundaries.

## Official Build QA

The wrapper uses `latexmk` and falls back to the intentional
`pdflatex -> bibtex -> pdflatex -> pdflatex` sequence. Accept only when:

- `.blg` has no warnings;
- `.log` has no undefined citations or references;
- initial-submission body satisfies the 25-page rule;
- tables and figures remain readable and inside margins;
- PDF metadata and visible content are anonymous; and
- page images show no clipping, overlap, blank content, or missing glyphs.

Current local build (2026-07-10): 21 official pages, references from page 18,
and citation/reference clean. The body and supplement previews are 21 and 17
pages. Four figures and ten main tables are present and readable. Recount and
repeat visual QA after every substantive TeX edit.

## Anonymous Packet

- No author, affiliation, acknowledgement, repository owner, personal URL,
  email, local username/path, or private remote in reviewer-facing files.
- Title page and cover letter are uploaded only to their editor-facing slots.
- The supplement is identified as an online supplement and not concatenated
  accidentally with the body unless ScholarOne explicitly requests it.
- Any review-stage reproducibility bundle keeps tags and hashes but removes
  identity and secrets.

## ScholarOne Proof Go/No-Go

Open the ScholarOne-generated proof. Submission is NO-GO if identity leaks,
the wrong manuscript version appears, body/supplement order is wrong, any
figure/table/equation/reference is missing, data/code answers conflict, or the
uploaded PDF differs from the validated local build. Repair locally, rerun the
full gate, re-upload, and inspect the replacement proof.
