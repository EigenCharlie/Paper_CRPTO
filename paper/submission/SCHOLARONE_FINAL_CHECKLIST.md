# ScholarOne Final Checklist

Use only after the scientific content and official PDFs are frozen.

## Files

| File | Reviewer-facing | Local status |
|---|:---:|---|
| Anonymous manuscript PDF from `CRPTO_ijds_submission.tex` | Yes | Rebuild and recheck after every body edit. |
| Anonymous supplement PDF | Yes | Render and visually inspect. |
| Separate title page | No | Complete from `TITLE_PAGE_DRAFT.md`. |
| Data and Code Disclosure Form | Editor/system | Finalize from the draft. |
| Cover letter | Editor | Finalize from `COVER_LETTER_AND_DISCLOSURE.md`. |
| Reproducibility note/archive | Editor/system | Sanitize identity, paths, and remotes. |

## Official Build

```powershell
just paper-submission-official
```

The wrapper uses the direct `latexmk.pl` payload on Windows and falls back to the verified
`pdflatex -> bibtex -> pdflatex -> pdflatex` loop. Accept only when:

- `.blg` has zero warnings;
- `.log` has no undefined citation/reference warnings;
- body page count satisfies the IJDS 25-page rule;
- figures and tables fit;
- PDF metadata and visible content remain anonymous.

Current local build (2026-07-09): 12 pages total, with References beginning on
page 10; citation/reference scans are clean. Recount after every substantive
TeX edit.

## Local Gates

```powershell
just ijds-evidence
uv run pytest tests/test_ijds_active_claim_sync.py -q
just publication-integrity
just lint
just type-check
just type-advisory-full
just smoke
just validate-champion
just paper-submission
just paper-submission-official
uv run dvc status --no-updates
```

`dvc status` is a report, not permission to rerun protected stages. Do not
repair paper-stage drift by overwriting the frozen upstream chain.

## Anonymous PDF QA

- No author names, affiliations, acknowledgements, repository ownership,
  personal URLs, local usernames, or private remotes.
- Correct title, abstract, keywords, section order, and supplement designation.
- References use the official INFORMS bibliography style.
- No missing glyphs, clipped figures, overflow tables, orphan headings, or
  unreadably small text.
- Active numbers match A35--A40 and governance.
- Temporal reversals and retrospective-design caveat remain visible.
- OCE/CVaR, SPO+, and external datasets remain diagnostics, not active methods.

## ScholarOne Proof Go/No-Go

Open the ScholarOne-generated proof, not only the local files. Submission is
**NO-GO** if any of these occur:

- title page or author identity leaks into reviewer files;
- body/supplement order is wrong;
- figure, equation, table, or bibliography is missing or clipped;
- data/code answers differ from the cover letter;
- page count or anonymous-review option is wrong;
- uploaded PDF differs from the locally validated build.

Repair locally, rerun the gates, re-upload, and inspect the new proof before
final submission.
