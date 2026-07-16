# ScholarOne Final Checklist

Use only after an explicit submission-freeze decision. Until then this is a
living closeout checklist, not evidence that the package is final.

## Scientific Lock

- [ ] Active claim registry is `docs/research/active_claims_2026-07-14.md`.
- [ ] Evidence manifest, executable claim ledger, and source registry verify by hash.
- [ ] Census is 376,890 candidates, 364,814 resolved, and 12,076 unresolved.
- [ ] The five endpoint reasons sum exactly to the candidate, resolved, and unresolved totals.
- [ ] All 40 five-model coverage upper bounds are below 0.90; largest 0.897726.
- [ ] Objective-matched .25 is described as crossing zero, never as favorable.
- [ ] Two-ruler, exact-support, fit-label-lag, endpoint-availability, and solver-stability limits are stated.
- [ ] Endpoint lags 0/3/6/8/12 are complete, unselected, and the six-month slice reconciles to the active evaluation.
- [ ] Fit-label and evaluation-endpoint timing are not described as a joint factorial sensitivity.
- [ ] Missingness encodings and the second origin are bounded recurrences, not winners or independent validation.
- [ ] Identification-width statements match the exact unresolved-row identity and the six reported tracks.
- [ ] No learner, window, gamma, ruler, coordinate, cap, comparator, or policy is selected.
- [ ] No selected-set, causal, prospective, confirmatory, deployment, Markov,
      point-in-time-snapshot, cash-flow-return, or fair-lending claim appears.

## Files

- [ ] Anonymous official IJDS PDF.
- [ ] Anonymous online supplement PDF.
- [ ] Separate title-page metadata form.
- [ ] Optional cover letter and generative-AI disclosure, if uploaded.
- [ ] Data and code disclosure form.
- [ ] Editor-only reproducibility crosswalk, if requested.
- [ ] Sanitized reproducibility capsule, if requested.

## Build and Numerical QA

- [ ] `just ijds-active-check` passes.
- [ ] `just validate-champion` and `just drift-gate` pass.
- [ ] Full active tests, Ruff, mypy, and ty pass.
- [ ] Generated TeX is current with QMD.
- [ ] `.blg` has no warnings.
- [ ] `.log` has no undefined citations, labels, or rerun requests.
- [ ] Pre-reference body is within the IJDS page limit.
- [ ] Abstract is at most 300 words and keywords are within 1--10.
- [ ] Every official, body-preview, and supplement page is visually inspected.
- [ ] No clipping, overlap, blank page, broken table, missing glyph, or tiny figure text.

## Anonymity and Availability

- [ ] Reviewer files contain no author name, email, local path, repository URL,
      protocol tag, commit, hash, DVC coordinate, or acknowledgments.
- [ ] Public/searchable code does not create an identity leak in reviewer files.
- [ ] Raw-data acquisition and hash instructions are accurate.
- [ ] No secrets or `.dvc/config.local` contents are included.

## Final ScholarOne Proof

- [ ] Submitting-author ORCID iD is present in ScholarOne.
- [ ] Compare uploaded proof page by page with the validated local PDFs.
- [ ] Confirm title, abstract, keywords, equations, references, and supplement links.
- [ ] Record final page counts and artifact hashes.
- [ ] Create the immutable submission tag only after user approval.
