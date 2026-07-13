# IJDS Pre-Freeze Readiness

No submission date is fixed. Continue improving the active audit until an
explicit freeze decision; do not retune on 2016--2017 outcomes or promote a
learner, window, policy, cap, or comparator.

## Active Foundation

- one active V4 scientific contract and one paper-facing evidence manifest;
- verified outcome-free Phase 1 and separate Phase-2 outcome evaluation;
- four DVC pointers for the data/model roots of both phases;
- complete eight-window, two-learner, nine-policy specification;
- exact HiGHS basis frontier and sharp common-outcome bounds;
- canonical QMD body and generated INFORMS TeX;
- separate anonymous supplement;
- current cover letter, title page, disclosure draft, crosswalk, and checklist;
- deterministic evidence and TeX builders; and
- scientific, claim-sync, anonymity, typing, drift, and compilation gates.

## Work Allowed Before Freeze

- improve exposition without expanding a supported claim;
- add tests, diagnostics, and reproducibility checks;
- modernize dependencies after a clean compatibility run;
- simplify active code while preserving exact frozen artifacts;
- prepare the final sanitized review archive;
- improve figure accessibility and grayscale legibility; and
- resolve reviewer-style objections with existing evidence or a separately
  declared experiment using fresh paths.

## Actions Requiring a New Protocol

- any new model fit, taxonomy, comparator, endpoint, payoff, or decision window;
- any result that could replace an active headline;
- any reoptimization based on inspected OOT outcomes; or
- any run that writes outside a fresh versioned experiment directory.

Such work must be declared before execution, retain all cells, and cannot
silently overwrite either V4 phase or historical protected artifacts.

## Explicit Freeze Gate

At freeze, stop scientific changes and run:

```powershell
just submission-check
just ijds-dvc-remote-status
git status --short
```

Then repeat a clean-clone reproduction, inspect all PDFs page by page, update
the numerical QA record, create the final immutable tag, and compare the
ScholarOne proof with the local PDFs. Freeze is complete only after explicit
user approval.
