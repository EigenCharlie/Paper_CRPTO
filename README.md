# CRPTO

CRPTO is a research repository for one manuscript targeted to the **INFORMS
Journal on Data Science**. It studies what happens when a binary conformal
score is used as a coefficient in a monthly credit-allocation linear program.
The contribution is an exact geometric analysis and identification audit of the
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
| Joint-block rank diagnostic | 31 / 40 cells meet the locked nominal thresholds |
| Individual-age origin sensitivity | 16 / 16 upper bounds below 0.90 |
| Label-Mondrian sensitivity | 27 / 40 marginal and 109 / 400 category shortfalls |
| Closed CatBoost calibrator family | 18 / 32 pooled upper endpoints below 0.90 |
| Calibrator evaluation / pairwise cells | 192 / 288 |
| Two-ruler optimization solves | 6,240 |
| Registered finite point-cap support | 3,067 caps |
| Finite registered-cap endpoint envelopes including zero | 216 / 216 |
| Structural sensitivity | 36 complete scenarios |
| Joint fit-label completion stress | 32 / 32 upper bounds below 0.90 |
| USD 25 floor diagnostic | maximum rate perturbation 0.001284 pp |
| Set-preserving embedding audit | 80 / 80 binary-set cells unchanged |
| Positive-gamma allocation changes | 9,659 / 11,520 monthly contrasts |
| Fixed theta tracks with both separated signs | 77 / 576 |
| Clean binary-phase census | 200 / 200 exact reconciliations; 87 below-half cells |
| Dual set-native certificates | 208 / 208; 0 new optimization solves |

Under the declared six-month outcome-availability rule, all 40 sharp
all-candidate coverage upper bounds are below 0.90. That is a deterministic
finite-archive fact, not by itself a rejection of split conformal. In a
separate post-inspection combined-rank diagnostic, 31 of the 40 frozen
learner-window cells meet the locked Bonferroni-within-cell and
Holm-across-cell nominal thresholds. Its Beta--Binomial reference law assumes
the stronger joint exchangeability of each calibration stratum together with
its entire target block; it does not test or refute the usual one-future-point
marginal split-conformal guarantee. Because the family and pattern were
inspected before locking, the thresholds do not provide post-selection or
study-wide FWER control. The primary CatBoost eight-window finding also recurs
under three feature-semantics-preserving missingness encodings and at both April--June
origins with cutoffs 39 months after each issue-month end (equal whole-month
administrative age, not exact day-level age). Label-Mondrian calibration changes the
40 marginal states to 27 shortfalls, 12 crossings, and one lower endpoint at or
above nominal; it is a complete sensitivity, not a repair. A separate closed
four-map CatBoost sensitivity holds one common uncalibrated-probability
(`q_raw`) taxonomy fixed. Platt and beta retain upper endpoints below 0.90 in
8/8 pooled windows, while isotonic and the IVAP Venn--Abers scalar do so in
1/8 each; because only 18/32 pooled cells remain below, a uniform
closed-family shortfall is not established. This selects no calibrator,
transfers no Venn guarantee to the scalar, and supplies no portfolio result.
Portfolio direction
changes with the outcome-blind ruler, coordinate, and comparator support; no
model, encoding, gamma, ruler, coordinate, scenario, or policy is selected.
Exact downstream score-order invariance requires positive-affine equivalence
on the span of feasible allocation differences. Preserving binary sets or the
coordinatewise loan ranking is not sufficient, while failure of that condition
does not require every fixed cell to change.

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

The source registry owns lineage identities, 53 DVC pointers, and 11
scientific Git-native artifact lineages. The evidence builder emits 45
paper-facing CSV tables and five figure families. The evidence manifest is the
only numeric paper-facing manifest. The body QMD is the only editable source
for the official submission TeX.

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
Current experiment entrypoints are exactly the `scripts/experiments/run_ijds_*`
files named by `configs/crpto_publication_targets.yaml`.

`dvc.yaml`, `dvc.lock`, and paths fixed by `EXTRACTION_MANIFEST.json` form a
sealed compatibility capsule. They preserve old hashes and path-bound replay
metadata but are not active workflows or manuscript evidence. The complete
pre-consolidation repository is archived outside the project at
`D:\crpto_legacy`.

The current package and evidence flow is mapped in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Setup

Requirements: Python 3.11 or 3.12, `uv`, `just`, Quarto, Git, and TeX Live.

```powershell
uv sync --group dev --locked
just smoke
```

Use Windows PowerShell and `uv run` for Python commands.
Known transitive advisories and their containment rules are recorded in
[`docs/security/DEPENDENCY_RISK_REGISTER.md`](docs/security/DEPENDENCY_RISK_REGISTER.md).

## Main Commands

```powershell
just test                    # complete local/Git-native suite; no DVC bytes required
just coverage                # local/Git-native suite plus branch coverage XML
just lint                    # Ruff check and format check
just type-check              # mypy
just type-check-fast         # blocking ty check on the active surface
just publication-integrity   # source, claim, and artifact contracts
just drift-gate              # read-only PD/conformal/evidence regression
just ijds-active-science-tests # auto-discovered IJDS tests that need no DVC bytes
just ijds-active-dvc-tests   # materialized IJDS tier; run only after just ijds-pull
just ijds-active-check       # scientific and manuscript synchronization
just submission-build       # evidence, HTML, TeX, PDFs, previews
just submission-check       # pre-freeze read-only gates; no page cap
just submission-freeze-check # final-only gate; enforces configured page cap
just submission-closeout    # build, check, and remote DVC verification
just dependency-audit        # fail on unregistered dependency advisories
```

The manual GitHub workflow named `clean-clone-reproducibility` (kept at
`.github/workflows/tests-full.yml` to preserve its existing GitHub identity)
reconstructs the locked publication capsule on a disposable Windows CPU runner.
That operating system deliberately matches the canonical figure-generation
surface because the workflow compares PNG and PDF evidence byte for byte. The
lightweight lint workflow remains an independent Ubuntu portability check;
CRPTO does not require WSL, CUDA, a GPU, or cuOpt. The clean-clone workflow pulls
only active evidence and strict-manifest DVC targets,
then runs the same claim, drift, test, and coverage gates used locally. It is a
reproducibility audit, not the final reviewer-PDF page freeze. It also
rebuilds the reviewer HTML, generated TeX, and deterministic machine-readable
supplement. The official publisher PDF and browser-printed preview PDFs remain
the Windows closeout surface because the INFORMS style kit and local Chromium
installation are not distributed by this repository.

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

Code is MIT licensed. Narrative text, figures, tables, and documentation are
currently governed by [`LICENSE-CONTENT`](LICENSE-CONTENT). Because that prior
public grant may conflict with a journal copyright transfer, publication rights
remain a human-confirmation blocker rather than a resolved repository setting;
see
[`docs/research/ijds_submission_rights_anonymity_audit_2026-07-21.md`](docs/research/ijds_submission_rights_anonymity_audit_2026-07-21.md).
See [`CITATION.cff`](CITATION.cff) for citation metadata.
