# ScholarOne Final Checklist

Use only after an explicit submission-freeze decision. Until then this is a
living closeout checklist, not evidence that the package is final.

## Scientific Lock

- [ ] Active claim registry is `docs/research/active_claims_2026-07-14.md`.
- [ ] Evidence manifest, executable claim ledger, and source registry verify by hash.
- [ ] Census is 376,890 candidates, 364,814 resolved, and 12,076 unresolved.
- [ ] The five endpoint reasons sum exactly to the candidate, resolved, and unresolved totals.
- [ ] All 40 five-model sharp coverage upper bounds are below 0.90; largest
      0.897726; this is described as a finite-archive fact, not by itself an
      exchangeability rejection or conformal-theorem failure.
- [ ] The combined-rank diagnostic is described as 31/40 learner-window cell
      reference tail areas meeting locked nominal Bonferroni-within-cell and
      Holm-across-cell reporting thresholds under the stronger joint
      calibration-plus-target-block null.
      It is not described as rejecting the usual one-future-point marginal
      guarantee, providing post-selection or study-wide FWER, finding
      a shift cause, or establishing exchangeability in unflagged cells.
- [ ] Objective-matched .25 is described as crossing zero, never as favorable.
- [ ] Two-ruler, registered-support, fit-label-lag, endpoint-availability, and solver-stability limits are stated; no exhaustive continuous point-cap path is claimed.
- [ ] Endpoint lags 0/3/6/8/12 are complete, unselected, and the six-month slice reconciles to the active evaluation.
- [ ] Fit-label and evaluation-endpoint timing are not described as a joint factorial sensitivity.
- [ ] Missingness encodings and the individual-age origin sensitivity are
      bounded recurrences, not winners or independent validation; all 16
      origin-window upper bounds use cutoffs 39 months after issue-month end, which
      equalizes minimum rather than exact loan-level follow-up.
- [ ] Label-Mondrian is reported as 27/40 shortfalls, 12/40 crossings, and
      1/40 at-or-above nominal, with 109/400 category shortfalls and all 40
      aggregate gap bounds crossing zero; each endpoint uses completions that
      assign every unresolved loan once and share it across both class ratios,
      although the two endpoint completions may differ. It is not a repair,
      hypothesis-test family, or fairness result.
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
- [ ] Capsule inventory reconciles to exactly 51 DVC pointers and 27
      paper-facing CSV tables; unequal-follow-up roots appear only as replay
      provenance.

## Build and Numerical QA

- [ ] `just ijds-active-check` passes.
- [ ] `just validate-champion-strict`, `just type-check`, and
      `just type-check-fast` pass.
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
