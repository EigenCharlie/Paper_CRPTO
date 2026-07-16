# IJDS Tooling Decisions

Updated July 15, 2026. This note records engineering choices only. Scientific
authority lives in `docs/research/active_claims_2026-07-14.md`, executable claim
authority in `configs/ijds_claim_ledger.yaml`, and numerical authority in
`reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json`.

## Adopted Stack

| Tool | Active role |
|---|---|
| `uv` | Sole environment, lock, and Python command interface; reproduction uses `--frozen`. |
| Ruff | Sole formatter and linter. |
| mypy | Required gradual type gate over `src`, `scripts`, and `tests`. |
| `ty` | Independent zero-diagnostic advisory gate over the active scope. |
| pytest | Unit, contract, scientific-grid, claim-sync, and integration tests. |
| `just` | Sole human-facing Windows-first command runner. |
| DVC | Immutable large-artifact transport for the 21 registered pointers. |
| pre-commit / prek | One shared hook definition with two compatible runners. |

`pdoc` remains an ephemeral API browser. It is not a project dependency or a
publication artifact. Pyrefly and Commitizen remain unadopted: a third type
checker and commit-message automation do not improve this single-author
scientific evidence contract.

## Active Architecture

- `src/ijds_audit/` owns population, endpoint, prediction, conformal geometry,
  allocation, evaluation, exact-support, and sensitivity contracts.
- `src/ijds_challengers/` owns the two outcome-free comparator rulers and their
  endpoint evaluation helpers.
- Versioned runners under `scripts/experiments/` write only new run-tag roots.
- `scripts/build_ijds_binary_geometry_frontier_v4_evidence.py` verifies every
  registered source and transactionally emits one manifest, 16 CSV tables, and
  three figures in PDF and PNG.
- `paper/CRPTO_ijds.qmd` is canonical; the official TeX is generated and never
  edited as a second manuscript.
- The reviewer capsule includes the complete `src` package so transitive imports
  cannot be omitted, while historical execution entrypoints remain excluded.

The July 15 builder refactor separated V4, two-ruler, credit-control, raw-data,
rolling-origin, and missingness loaders. Its orchestration complexity fell from
112 to 49 and the file-wide mean from C to B. All 16 table hashes and all six
figure-file hashes remained identical. The manifest changed only because it
correctly binds the refactored builder hash, and consecutive builds are
byte-idempotent.

## Dependency Policy

`uv.lock` is the executable environment contract. A dependency update is
accepted only when it fixes a relevant defect or materially simplifies the
active path and the full gates remain green. Major numerical-library upgrades
are not invisible maintenance after a run: CatBoost, scikit-learn, NumPy,
pandas, PyArrow, HiGHS, or solver changes require a fresh tagged evaluation and
explicit drift comparison. Tool-only upgrades may proceed when they do not
alter scientific artifacts.

## Named Gates

```powershell
just ijds-active-replay
just ijds-active-check
just lint
just type-check
just type-advisory-full
just test
just validate-champion
just drift-gate
just paper-submission
just paper-submission-tex
just paper-submission-official
just ijds-dvc-verify-remote
```

The active replay rebuilds paper-facing evidence only. It never invokes the
protected champion, conformal, optimization, or exact-evaluation DVC stages.

## Compilation Contract

The official build attempts TinyTeX's `latexmk.pl` payload through Perl. The
Windows fallback is `pdflatex -> bibtex -> pdflatex -> pdflatex`: the first pass
creates the auxiliary graph, BibTeX creates the bibliography, and the final two
passes stabilize citations, cross-references, floats, and pagination.
