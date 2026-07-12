# ScholarOne Final Checklist

Use only after an explicit submission freeze. Until then, this is a readiness
check rather than permission to upload.

## Files

| File | Reviewer-facing | Requirement |
|---|:---:|---|
| Official anonymous manuscript PDF | Yes | Generated from QMD through the INFORMS template |
| Anonymous online supplement PDF | Yes | Current protocol, proofs, full sensitivities, limitations |
| Separate title page | No | Author, affiliation, email, ORCID, declarations |
| Data and Code Disclosure Form | Editor/system | Current official form; Option 4 explanation reconciled |
| Cover letter | Editor | Current title, results, retrospective boundary |
| Reproducibility note/archive | Editor/system | Sanitized or exact identifiers according to audience |

## Scientific Reconciliation

- Title is "CRPTO: Auditing Temporal Transport and Comparator Choice in
  Conformal Portfolios" on every surface.
- Universe is `540,121`; membership never depends on final status.
- Taxonomy uses 2011 scores and residual calibration uses availability-safe
  2012H1 labels.
- All nine policies are co-primary; no selected policy or OOT winner appears.
- Fit coverage is `0.900388`.
- Canonical OOT coverage is `[0.854714, 0.879647]`; all four taxonomy upper
  endpoints are below 0.90.
- C2 matches funded point PD to residual below `4.17e-17`.
- Canonical C2 counts are payoff worse `7/9`, default higher `1/9`, and
  miscoverage higher `8/9`.
- All `27/27` finite comparator envelopes are indeterminate.
- The 180 seed-purpose cells are reported without selecting a favorable cell.
- All 2,025 sub-100% guardrail-month purpose caps are derived as binding.
- The terminal endpoint inventory is 499,845 resolved/40,276 unresolved; the
  distinct 500,019/40,102 receipt diagnostic is not used for claims.
- The superiority stop rule failed; the negative audit is labeled as a
  post-result retrospective interpretation, not a prespecified fallback.
- Standardized payoff is never called IRR, NPV, welfare, or investor return.
- No selected-set, causal, prospective, confirmatory, Markov, deployment, or
  fair-lending claim appears.

## Official Build QA

- official PDF: 27 pages;
- references start on page 25; 24 pre-reference pages;
- 8 main tables and 4 main figures;
- 280-word abstract and 7 keywords;
- no BibTeX warnings or undefined references/citations;
- all four INFORMS style assets match the tracked SHA-256 manifest;
- the known 17.54 pt publisher-class title diagnostic is visually within page;
- every page is rendered and checked after the final build.

## Full Local Gate

```powershell
just submission-check
uv run dvc status --no-updates
git status --short
```

`submission-check` validates evidence, QMD-to-TeX sync, publication integrity,
lint, Mypy, `ty`, full pytest, the protected champion, both Quarto surfaces,
and official compilation. It does not run protected DVC stages.

## Anonymous Packet

- No author, affiliation, email, acknowledgement, repository owner, personal
  URL, local path, exact tag/hash, or private remote appears in reviewer files.
- Title page, cover letter, disclosure form, and exact crosswalk are uploaded
  only in editor/system slots.
- The completed title page is created locally as `TITLE_PAGE_PRIVATE.md` from
  the tracked anonymous template and is never committed.
- The completed cover letter is created locally as `COVER_LETTER_PRIVATE.md`
  from the tracked anonymous template and is never committed.
- Search the exact title before upload and record any public repository or
  preprint discoverability. The [INFORMS peer-review
  policy](https://pubsonline.informs.org/authorportal/peer-review) notes that
  complete anonymity may be impossible for posted preprints; reviewer files
  still must contain no repository link or author identifier.
- Supplement is designated as a separate online supplement.
- ScholarOne-generated proof is opened and compared with the validated local
  PDFs before submission.

Submission is NO-GO if identity leaks, a retired result appears, files are in
the wrong order, a figure/table/equation/reference is missing, the disclosure
conflicts with the package, or the proof differs from the validated build.
