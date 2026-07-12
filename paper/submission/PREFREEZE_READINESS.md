# IJDS Pre-Freeze Readiness

No submission date is fixed. Continue improving the active audit until an
explicit freeze decision; do not retune on 2016--2017 outcomes or promote a
policy.

## Already Ready

- one active scientific contract and one evidence manifest;
- outcome-free V1 freeze plus reconciled V2 evaluation;
- four local DVC pointers;
- canonical QMD body and generated INFORMS TeX;
- separate anonymous supplement;
- current cover letter, title page, disclosure draft, crosswalk, and checklist;
- deterministic evidence and TeX builders;
- official PDF within the 25-page pre-reference limit.
- clean-clone reproduction of the locked environment, four DVC pulls,
  evidence rebuild, publication-integrity gate, and official PDF build.

## Work Allowed Before Freeze

- improve exposition without changing supported claims;
- add tests, diagnostics, and reproducibility checks;
- modernize dependencies after a clean compatibility run;
- simplify active code while preserving exact frozen artifacts;
- prepare the final sanitized review archive;
- improve figure accessibility and grayscale legibility;
- resolve reviewer-style objections using existing evidence or a separately
  declared new experiment with fresh paths.

## Actions Requiring a New Protocol

- any new model fit, taxonomy, comparator, endpoint, payoff, or decision window;
- any result that could replace an active headline;
- any reoptimization based on inspected OOT outcomes;
- any run that writes outside a new versioned experiment directory.

Such work must be declared before execution, retain all cells, and cannot
silently overwrite V1/V2.

## Explicit Freeze Gate

At freeze, stop scientific changes and run:

```powershell
just submission-check
uv run dvc status --no-updates
git status --short
```

Then repeat the clean-clone reproduction as a release check, inspect all PDFs
page by page, update the QA record, create the final immutable tag, and prepare
the ScholarOne proof. The freeze is complete only after the user explicitly
approves it.
