# IJDS Tooling and Refactor Decisions - 2026-07-09

This is the final decision record for the IJDS code and manuscript workflow.
It replaces the iterative tooling lab from 2026-07-08, whose useful decisions
have been implemented. Scientific history remains in `docs/research/`; this
file describes only the live engineering contract.

## Objective

Keep one auditable route from frozen upstream artifacts to the submitted
claim. Prefer small, explicit modules and named commands over additional
frameworks, parallel implementations, or hidden manuscript-time computation.

## Adopted tools

| Tool | Role | Decision |
|---|---|---|
| `uv` | Python environment, lockfile, commands | Sole Python package/runtime interface. |
| Ruff | lint and formatting | Sole linter and formatter. |
| mypy | stable gradual type gate | Required by `just type-check`. |
| ty | fast independent type audit | Active and full scopes; full scope blocks submission closeout. |
| pytest | behavioral and claim-sync tests | Required for focused, smoke, and full suites. |
| just | named local workflow | Sole human-facing command menu. |
| DVC | frozen artifact lineage | Keep for scientific provenance; never use it as a general task runner. |
| pre-commit + prek | hook compatibility and fast config validation | Keep both checks; do not create a second hook policy. |
| pdoc | optional local API browsing | Ephemeral via `uv run --with pdoc`; no project dependency. |

`ty` complements rather than replaces mypy. The active scope includes the
exact-alpha replay and calibration-selected policy modules. Its full clean
scope is useful as an independent submission check, while mypy remains the
stable repository contract.

## Rejected additions

| Tool | Decision | Reason |
|---|---|---|
| Pyrefly | Do not adopt | It duplicated type checking and produced substantially more migration noise than actionable signal. |
| Commitizen | Do not adopt | Commit-message automation does not improve scientific validity or the one-author release flow. |
| Permanent pdoc dependency | Do not adopt | Generated API pages are useful locally but are not a publication artifact. |
| A second task runner | Do not adopt | `just` already exposes the complete Windows-first workflow. |
| Automatic semantic versioning | Do not adopt | Run tags, Git commits, and evidence hashes are the relevant scientific identifiers. |

## Live methodology path

1. `src/models/conformal_alpha_grid.py` exactly replays the frozen 90%
   intervals and reports the alpha sensitivity.
2. `src/optimization/policy_evaluation.py` uses point PD in the economic
   objective and an effective PD only in the risk constraint.
3. `src/optimization/policy_selection.py` defines the nine-cell round-number
   grid and rejects selectors containing outcome-derived columns.
4. `scripts/experiments/ijds_policy_support.py` owns shared alignment, solving,
   and evaluation for the active challengers.
5. `scripts/build_ijds_calibration_selected_evidence.py` materializes A35-A40
   from versioned experiment outputs. Manuscript rendering does not solve or
   retune portfolios.

The active run is
`champion-reopen-2026-06-19__pool93__ijds-calibration-selected-simple90-v6`.
The exact-alpha run is
`champion-reopen-2026-06-19__pool93__ijds-exact-alpha-grid-v1`.

## Deliberate simplifications

- One active policy family: `q=(p+u)/2`, `tau=0.17`, `gamma=0.50`.
- Point PD remains the economic objective; uncertainty is a feasibility
  guardrail.
- One deterministic 3x3 calibration selector, with an outcome-column denylist.
- One A35-A40 active evidence bundle.
- One body, one supplement, and one official submission TeX source.
- No nested temporal selector, effective-PD objective branch, active cap/tail
  variants, or manuscript-time optimizer.
- Historical A1-A34 tables remain diagnostics and provenance, not competing
  active claims.

## Named commands

```powershell
just ijds-evidence
just ijds-active-replay
just lint
just type-check
just type-advisory-full
just smoke
just validate-champion
just drift-gate
just test
just submission-check
```

`just submission-check` is the ordinary release gate and includes the full
pytest suite. `just
ijds-active-replay` is intentionally separate because it recomputes exact
interval grids and solves experiment portfolios.

## Compilation contract

The official source first attempts `latexmk`. On the current Windows TinyTeX
installation its `runscript.tlu` wrapper may fail, so the documented robust
fallback is:

```text
pdflatex -> bibtex -> pdflatex -> pdflatex
```

The first pass writes citation keys to `.aux`, BibTeX writes `.bbl`, and the
last two passes stabilize citations, cross-references, and pagination. This is
one compilation workflow, not three independent builds.

## Drift policy

Experimental drift is allowed only under a new run tag. Promotion requires:

- no writes to manifest-listed or protected champion artifacts;
- an explicit scientific reason and comparator;
- claim-sync and publication-integrity tests;
- `just validate-champion`;
- `just drift-gate` when PD or conformal paths change;
- regenerated tables and a visually inspected PDF.

Light drift is not itself a benefit. A challenger is promoted only when it
improves the submitted method or its defensibility enough to justify the extra
surface area. Otherwise it is removed from the live path.
