# CRPTO

CRPTO is a research repository for one manuscript targeted to the **INFORMS
Journal on Data Science**. It studies what happens when a binary conformal
score is used as a coefficient in a monthly credit-allocation linear program.
The contribution is an identification audit of the
machine-learning--conformal--optimization interface, not a promoted lending
policy or a new credit-scoring leaderboard.

## Active Result

The active design uses the Lending Club 2007--2020Q3 archive and declares all
time roles before evaluation.

| Quantity | Active value |
|---|---:|
| Raw archive | 2,925,493 rows |
| Eligible 36-month design universe | 640,543 loans |
| Primary OOT candidates | 376,890 loans |
| Resolved / unresolved at the six-month endpoint | 364,814 / 12,076 |
| Coverage controls | 5 frozen learner specifications x 8 windows |
| Largest all-candidate coverage upper bound | 0.897726 |
| Two-ruler optimization solves | 6,240 |
| Exact point-cap frontier | 3,067 caps |
| Broad-support comparator envelopes crossing zero | 216 / 216 |
| Structural sensitivity | 36 complete scenarios |

Under the declared six-month outcome-availability rule, all 40 sharp
all-candidate coverage upper bounds are below 0.90. Separately, the primary
CatBoost eight-window pattern recurs under three feature-semantics-preserving
missingness encodings and at a later retrospective origin. Portfolio direction
changes with the outcome-blind ruler, coordinate, and comparator support; no
model, encoding, gamma, ruler, coordinate, scenario, or policy is selected.

These are retrospective, archive-specific identification results. They are not
prospective validity, selected-set conformal coverage, causal lending effects,
cash-flow returns, or deployment evidence.

## Sources Of Truth

Read these in order:

1. [`docs/research/active_claims_2026-07-14.md`](docs/research/active_claims_2026-07-14.md)
2. [`configs/ijds_active_evidence_sources.yaml`](configs/ijds_active_evidence_sources.yaml)
3. [`configs/ijds_claim_ledger.yaml`](configs/ijds_claim_ledger.yaml)
4. [`reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json`](reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json)
5. [`paper/CRPTO_ijds.qmd`](paper/CRPTO_ijds.qmd)
6. [`paper/supplement_ijds.qmd`](paper/supplement_ijds.qmd)

The source registry owns lineage identities and 27 DVC pointers. The evidence
manifest is the only numeric paper-facing manifest. The body QMD is the only
editable source for the official submission TeX.

## Architecture

```text
raw archive + frozen experiment roots
              |
              v
  configs/ijds_active_evidence_sources.yaml
              |
              v
  scripts/build_ijds_binary_geometry_frontier_v4_evidence.py
              |
              +--> reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json
              +--> reports/crpto/tables/crpto_ijds_v4_*.csv
              +--> reports/crpto/figures/crpto_ijds_v4_*.{png,pdf}
              |
              v
  paper/CRPTO_ijds.qmd + paper/supplement_ijds.qmd
              |
              v
  generated HTML/PDF + official INFORMS TeX/PDF
```

Current reusable code is under `src/ijds_audit`, `src/ijds_challengers`, and
the retained data, model, evaluation, and optimization modules they import.
Current experiment entrypoints are the ten `scripts/experiments/run_ijds_*`
files named by `configs/crpto_publication_targets.yaml`.

`dvc.yaml`, `dvc.lock`, and paths fixed by `EXTRACTION_MANIFEST.json` form a
sealed compatibility capsule. They preserve old hashes and path-bound replay
metadata but are not active workflows or manuscript evidence. The complete
pre-consolidation repository is archived outside the project at
`D:\crpto_legacy`.

## Setup

Requirements: Python 3.11 or 3.12, `uv`, `just`, Quarto, Git, and TeX Live.

```powershell
uv sync --extra dev
just smoke
```

Use Windows PowerShell and `uv run` for Python commands.

## Main Commands

```powershell
just test                    # complete retained test suite
just lint                    # Ruff check and format check
just type-check              # mypy
just type-check-fast         # blocking ty check on the active surface
just publication-integrity   # source, claim, and artifact contracts
just drift-gate              # read-only PD/conformal/evidence regression
just ijds-active-check       # scientific and manuscript synchronization
just submission-build       # evidence, HTML, TeX, PDFs, previews
just submission-check       # all read-only submission gates
just submission-closeout    # build, check, and remote DVC verification
```

The manual fallback for official TeX compilation is intentionally
`pdflatex -> bibtex -> pdflatex -> pdflatex`: the first pass writes citation
and cross-reference metadata, BibTeX writes the bibliography, and the final two
passes stabilize references and pagination.

## Protected Boundary

Do not run these historical DVC stages without explicit permission:

- `crpto.pd.champion`
- `crpto.conformal.intervals`
- `crpto.conformal.validation`
- `crpto.portfolio.optimization`
- `crpto.portfolio.bound_exact_eval`

Do not modify `EXTRACTION_MANIFEST.json` or its protected model/data artifacts.
Use `just validate-champion` for ordinary work and
`just validate-champion-strict` when every protected artifact is available.

## Paper Editing

Edit `paper/CRPTO_ijds.qmd`, then generate the official TeX with:

```powershell
just paper-tex
```

Never edit `paper/submission/CRPTO_ijds_submission.tex` directly. The paper is
double-anonymous; author-identifying material belongs only in the separate
submission forms.

## Data And Literature

The raw CSV and experiment roots are DVC-managed and excluded from Git. The
local `Papers_tesis/` corpus is also excluded because it contains copyrighted
PDFs; bibliographic metadata belongs in `paper/references.bib`.

## License And Citation

Code is MIT licensed. See [`CITATION.cff`](CITATION.cff) for citation metadata.
