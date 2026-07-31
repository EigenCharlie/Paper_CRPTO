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
      gives every candidate exactly 39 whole calendar months after its
      issue-month end, but not exact day-level age.
- [ ] The missingness-encoding sensitivity is described as varying two declared
      fields, not as general robustness to every incomplete predictor.
- [ ] Label-Mondrian is reported as 27/40 shortfalls, 12/40 crossings, and
      1/40 at-or-above nominal, with 109/400 category shortfalls and all 40
      aggregate gap bounds crossing zero; each endpoint uses completions that
      assign every unresolved loan once and share it across both class ratios,
      although the two endpoint completions may differ. It is not a repair,
      hypothesis-test family, or fairness result.
- [ ] The closed CatBoost calibrator sensitivity reports all 192
      method-window-scope cells and all 288 shared-completion pairwise cells.
      Exactly 18/32 pooled upper endpoints are below 0.90 (Platt 8/8,
      isotonic 1/8, beta 8/8, IVAP scalar 1/8), so the uniform closed-family
      shortfall is not established. It is not described as a calibrator
      winner, true-coverage dependence, a Venn guarantee for the scalar, or
      portfolio robustness.
- [ ] Binary geometry is stated conditionally: score binning does not guarantee
      a low regime; zero positive coverage needs target support; W7 and W8 do not
      share one pair of calibration maxima; and the exact two-threshold identity
      is not described as continuity.
- [ ] No lower-endpoint-only funded-miscoverage floor or universal optimizer
      anti-selection mechanism appears; outcome-free bounds use empty/full sets.
- [ ] The quarantined external V1 contributes no archive name, number, method,
      citation, table, runner, or evidence claim to reviewer-facing surfaces.
- [ ] Identification-width statements match the exact unresolved-row identity and the six reported tracks.
- [ ] No learner, calibrator, window, gamma, ruler, coordinate, cap,
      comparator, or policy is selected.
- [ ] No selected-set, causal, prospective, confirmatory, deployment, Markov,
      point-in-time-snapshot, cash-flow-return, or fair-lending claim appears.

## Files

- [ ] Upload from the explicit whitelist; do not zip or upload
      `paper/submission` as a directory.
- [ ] Anonymous official IJDS PDF.
- [ ] Anonymous online supplement PDF.
- [ ] Separate title-page metadata form.
- [ ] Optional cover letter and generative-AI disclosure, if uploaded.
- [ ] Anonymous machine-readable supplement containing full S6C and S6E
      strata plus S2C, S6O, and S6P calibrator tables.
- [ ] Data and code disclosure form.
- [ ] Editor-only reproducibility crosswalk, if requested.
- [ ] Sanitized reproducibility capsule, if requested.
- [ ] LaTeX `.fls`, `.aux`, `.log`, `.blg`, and `.bbl` files are excluded from
      every reviewer upload; the editor-only crosswalk is not reviewer-facing.
- [ ] Capsule inventory reconciles to exactly 53 DVC pointers, seven scientific
      Git artifact lineages, and 41 paper-facing CSV tables; unequal-follow-up roots appear
      only as replay provenance.

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
- [ ] The public repository is private and GitHub Pages is disabled for the
      double-anonymous review period; verify title, acronym, and distinctive
      phrases in a signed-out search.
- [ ] Raw-data acquisition source, date, governing terms, local filename,
      transformation, size, and SHA-256 are author-confirmed; the candidate
      Kaggle match is not represented as proven provenance.
- [ ] The DVC remote and release capsule do not redistribute raw or row-level
      derivatives without confirmed rights.
- [ ] No secrets or `.dvc/config.local` contents are included.
- [ ] `.dvc/config.local` remains ignored and absent from reachable Git history;
      credentials are stored outside tracked files.

## Human and Rights Sign-off

- [ ] Every author confirms authorship, order, consent, CRediT roles, current
      affiliation, ORCID, corresponding-author details, funding, conflicts,
      acknowledgements, and full responsibility for the submission.
- [ ] Originality, no simultaneous review, prior IJDS submission, and overlap
      with any thesis, preprint, book, site, or other manuscript are confirmed
      and disclosed where required.
- [ ] The author has resolved with INFORMS whether the prior CC BY 4.0 grant over
      `paper/**` requires Open Option or another rights arrangement; do not
      certify conventional copyright transfer until confirmed.
- [ ] The final generative-AI disclosure is accurate, consistent across all
      forms, and human-verified.

## Final ScholarOne Proof

- [ ] Submitting-author ORCID iD is present in ScholarOne.
- [ ] Compare uploaded proof page by page with the validated local PDFs.
- [ ] Confirm title, abstract, keywords, equations, references, and supplement links.
- [ ] Record final page counts and artifact hashes.
- [ ] Create the immutable submission tag only after user approval.
