# Contributing To CRPTO

CRPTO is a single-author academic repository for one IJDS manuscript, not a
general-purpose Python package. Contributions should improve the validity,
clarity, or reproducibility of that manuscript.

## Start Here

Read `CLAUDE.md`, the active claim registry, the source registry, and the
publication contract before changing scientific code or prose.

```powershell
uv sync --extra dev
just smoke
```

## Ordinary Changes

The following are normally safe when their tests pass:

- prose and citation corrections that remain inside the active claim boundary;
- tests and validation code that do not rewrite registered experiment roots;
- deterministic evidence, table, figure, and submission builders;
- CI, formatting, typing, and reproducibility documentation;
- refactors whose outputs are unchanged and whose compatibility paths remain
  intact.

Run:

```powershell
just test
just lint
just type-check
just type-check-fast
just publication-integrity
just ijds-active-check
just validate-champion
```

## Scientific Changes

A new estimand, data role, endpoint rule, model, comparator, sensitivity, or
optimization contract is a new scientific object, even if implemented as a
small code edit. Before running it:

1. state the research question and stop rule;
2. declare the information set and all outcome-blind choices;
3. assign a new run tag and contained output path;
4. separate freeze from outcome evaluation;
5. register exact hashes and DVC pointers before using results in prose;
6. reconcile every reported number against the evidence manifest.

Do not select a model, ruler, coordinate, gamma, scenario, or policy from OOT
outcomes.

## Protected Boundary

Never run the protected `crpto.pd.champion`, `crpto.conformal.intervals`,
`crpto.conformal.validation`, `crpto.portfolio.optimization`, or
`crpto.portfolio.bound_exact_eval` stages without explicit permission. Do not
modify `EXTRACTION_MANIFEST.json` or protected model/data artifacts.

`dvc.yaml` and manifest-fixed paths form a sealed compatibility capsule. Their
presence does not make them active workflows. The active execution surface is
the allow-list in `configs/crpto_publication_targets.yaml`.

## Paper Workflow

Edit the canonical QMD files, not generated outputs:

```powershell
just submission-build
just submission-check
```

The official TeX is generated from `paper/CRPTO_ijds.qmd`. Keep author identity
out of reviewer-facing files and keep project-version history out of the paper.

## Style

- English for code, tests, and manuscript prose.
- Type new public functions and keep comments limited to non-obvious logic.
- Prefer existing modules and structured parsers over new wrappers.
- Avoid one-off scripts when a current library function or registered runner
  already owns the behavior.
- Do not add services, dashboards, notebooks, or release machinery that does
  not improve the paper or its reproducibility.
