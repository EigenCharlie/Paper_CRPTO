# ScholarOne Final Checklist

Use only after an explicit submission freeze. Until then, this is a readiness
check rather than permission to upload.

## Files

| File | Reviewer-facing | Requirement |
|---|:---:|---|
| Official anonymous manuscript PDF | Yes | Generated from QMD through the INFORMS template |
| Anonymous online supplement PDF | Yes | Current protocol, proofs, full sensitivities, limitations |
| Separate title page | No | Author, affiliation, email, ORCID, declarations |
| Data and Code Disclosure Form | Editor/system | Current official form; release explanation reconciled |
| Cover letter | Editor | Current title, results, retrospective boundary |
| Reproducibility note/archive | Editor/system | Sanitized or exact identifiers according to audience |

## Scientific Reconciliation

- Title is "CRPTO: Auditing Binary Conformal Geometry and Portfolio
  Comparators" on every surface.
- The design universe has `640,543` status-independent loans; primary OOT has
  `376,890` candidates, `365,339` resolved and `11,551` unresolved.
- All five learner taxonomies use 2011 scores; all eight residual windows use
  availability-safe labels and none is selected by OOT results.
- The complete five-gamma path, two rulers, and three interior coordinates are
  reported; no selected learner, taxonomy, gamma, ruler, coordinate, policy,
  cap, comparator, or OOT winner appears.
- The two-ruler freeze contains `6,240` solves and `622,455` funded rows.
- Objective-matched `.25` is reported once: `44` changed loan-month positions,
  USD `155,937.27` one-way turnover, USD `5,603.66` higher payoff, and
  `-0.00679` pp default/miscoverage. It is not eight confirmations.
- Objective-matched `.50` is unfavorable; `.75` is mostly unidentified for
  payoff/default. Normalized-score tracks are adverse but are not called
  opportunity matched.
- All `40/40` model-window all-candidate coverage upper bounds are below 0.90;
  the largest upper bound is borrower-only WOE/IV at `0.896973`.
- The stratum-2 phase diagnostic is prevalence `0.101703 -> 0.097147`, residual
  quantile `0.888435 -> 0.111801`, and width `0.984263 -> 0.207631`.
- C2 matches funded point score to residual below `8.33e-17` in all `1,080`
  cells and is described only as a plug-in feasibility theorem.
- The exact point frontier contains `3,067` caps.
- All `216/216` broad-stress envelopes cross zero; default crosses in all
  `72/72` development-support cells; all `27/27` W8 envelopes cross zero.
- The 19,200-repetition simulation supports only a coverage mechanism; its
  portfolio component is disclosed as degenerate.
- The Platt score is not called a true conditional probability; its objective
  is model-implied. Standardized payoff is never called IRR, NPV, welfare, or
  investor return.
- No selected-set, causal, prospective, confirmatory, Markov, deployment, or
  fair-lending claim appears.

## Official Build QA

After the explicit freeze, record and verify:

- total official pages and pre-reference pages;
- reference start page and compliance with the 25-page exclusion rule;
- five main tables and two main figures, unless a documented editorial edit
  deliberately changes the count;
- abstract at most 300 words and 1--10 keywords;
- no BibTeX warnings or undefined references/citations;
- all four INFORMS style assets match the tracked SHA-256 manifest;
- every body, supplement, and official page has been rendered and visually
  checked; and
- no figure, table, equation, header, footer, or reference is clipped or
  overlapping.

## Full Local Gate

```powershell
just submission-check
just ijds-dvc-remote-status
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
- The completed title page is created locally as `TITLE_PAGE_PRIVATE.md`; the
  completed cover letter as `COVER_LETTER_PRIVATE.md`. Both are ignored by Git.
- Search the exact title before upload and document public discoverability.
- Supplement is designated as a separate online supplement.
- ScholarOne-generated proof is opened and compared with the validated local
  PDFs before submission.

Submission is NO-GO if identity leaks, a retired result appears, files are in
the wrong order, a figure/table/equation/reference is missing, the disclosure
conflicts with the package, or the proof differs from the validated build.
