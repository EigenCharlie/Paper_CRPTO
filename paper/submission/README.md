# IJDS Submission Package

This directory is the pre-freeze anonymous IJDS handoff. The official TeX is
generated from `paper/CRPTO_ijds.qmd` and must not be edited directly.

## Authorities

- body: `paper/CRPTO_ijds.qmd`;
- supplement: `paper/supplement_ijds.qmd`;
- claim registry: `docs/research/active_claims_2026-07-14.md`;
- executable claim ledger: `configs/ijds_claim_ledger.yaml`;
- evidence registry: `configs/ijds_active_evidence_sources.yaml`;
- evidence manifest: `reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json`;
- TeX generator: `scripts/build_ijds_submission_tex.py`;
- compiler: `scripts/compile_ijds_submission.py`.

The active study scans 2,925,493 raw rows and uses the exhaustive 640,543-loan
eligible design. It retains 376,890 primary OOT candidates, reconstructs
364,814 outcomes as observable by the cutoff, and bounds 12,076 unresolved
outcomes. Five retrospectively protocol-locked learner specifications support the coverage audit;
only CatBoost enters optimization. The decision audit reports five gamma
values, two rulers, three coordinates, finite registered point-cap supports, and
no winner. Evaluation-endpoint lags 0, 3, 6, 8, and 12 are reported without
selection; conformal-fit label timing is a separate sensitivity. An
observed-only fit and three declared stress rules vary the 215 labels that were
unavailable at their fitting cutoffs, without claiming sharp bounds over all
possible assignments. A USD 25 floor-with-residual-cash diagnostic shows that
the declared transformation negligibly perturbs evaluated rates; it does not
establish adequacy or optimality of the continuous relaxation or integer-policy
behavior.

All 40 sharp six-month coverage upper endpoints are below 0.90 as a
finite-archive descriptive result. Separately, 31/40 learner-window cells in an
exact combined-rank reference diagnostic meet its locked nominal
Bonferroni--Holm thresholds. This concerns the stronger joint exchangeability
of each calibration stratum and its entire target block, not the usual
one-future-point marginal guarantee; prior inspection precludes a
post-selection or study-wide FWER claim. The individual-age sensitivity
reports all 16 CatBoost origin-window cells at 39 months after each candidate's
issue-month end; that matches whole-month administrative age, not exact day-level
age.
The label-Mondrian sensitivity reports all 40/200/400 cells: 27/40 marginal
and 109/400 category upper endpoints remain below 0.90. None of these results
selects a model or method, rejects the marginal split-conformal guarantee,
identifies a shift mechanism, restores conditional validity, or authorizes a
fairness claim.

The separate closed CatBoost calibrator sensitivity reports every Platt,
isotonic, beta `abm`, and IVAP Venn--Abers cell under one common `q_raw`
taxonomy. Only 18/32 pooled upper endpoints are below 0.90, so a uniform
closed-family shortfall is not established. The result selects no calibrator,
does not transfer the Venn multiprobability guarantee to the scalar, and
contains no alternative-map portfolio optimization.

## IJDS Requirements

- IJDS-template PDF;
- at most 25 pages excluding references and appendices;
- separate online supplement;
- separate anonymous machine-readable supplement for full stratum tables,
  including calibrator Tables S2C, S6O, and S6P;
- double-anonymous review;
- abstract no longer than 300 words;
- 1--10 keywords; and
- data/code disclosure at submission.

The repository-content license and the journal copyright route must also be
resolved with INFORMS before certifying transfer; the existing CC BY 4.0 grant
cannot be treated as undone by deleting a file. Recheck the official guidelines during submission week. Current links are in
`configs/crpto_publication_targets.yaml`.

## Upload whitelist

Do not archive or upload this directory wholesale. Reviewer-facing uploads are
limited to `CRPTO_ijds_submission.pdf`, `../supplement_ijds.pdf`, and
`CRPTO_ijds_machine_readable_supplement.zip`. Upload the title page, cover/AI
disclosure, and data/code form only in their designated non-reviewer fields.
Provide `EDITOR_ONLY_REPRODUCIBILITY_CROSSWALK.md` only to the editor when
requested. Never upload LaTeX working files such as `.fls`, `.aux`, `.log`,
`.blg`, `.bbl`, or `*.latexmk.txt`: they can contain local paths or internal
provenance.

## Build

```powershell
just submission-build
just submission-check
```

On a Windows host where TinyTeX under `AppData` fails with `Can't get long
name`, compile the already generated official TeX with:

```powershell
just paper-official-windows
```

That non-freeze target uses `scripts/compile_ijds_submission_windows.ps1` to
mount the existing TinyTeX root behind a temporary drive alias, invoke the
bundled Perl and `latexmk.pl` until references and pagination converge, scan
the final log and BibTeX outputs, and restore the process path, location, and
drive mapping in a `finally` block. It neither installs packages nor copies the
TinyTeX tree. Use `-TexFile`, `-TinyTexRoot`, and `-OutputDirectory` when
calling the script directly; `-PlanOnly` prints the exact command and cleanup
plan without mounting or compiling.

The first command writes active evidence and document outputs in causal order;
the second verifies them without replaying scientific evidence and does not
enforce a page cap during the active scientific-editing phase. Page reduction
is intentionally deferred. Only when the manuscript enters an explicit final
freeze should `just submission-freeze-check` activate the journal page gate.
`build_ijds_submission_tex.py --check` rejects stale generated TeX.
`informs_style_assets.json` pins the local publisher kit. The generic Python
compiler attempts `latexmk`; when it is unavailable it retains the bounded
manual fallback:

```text
pdflatex -> bibtex -> pdflatex -> pdflatex
```

The first `pdflatex` creates `.aux`, BibTeX creates `.bbl`, and the remaining
passes resolve citations, labels, floats, and pagination. Its post-build scan
fails closed if another pass is still requested. On the affected Windows host,
prefer `paper-official-windows`: `latexmk.pl` repeats the dependency graph to a
fixed point instead of assuming that a bounded pass count is sufficient.

`just paper-pdf-audit` then verifies the three generated reviewer PDFs: Letter
page size, no blank pages, no identity or artifact fingerprints, and a
one-paragraph abstract of at most 300 words. It deliberately does not constrain
pages during development. Visual inspection remains required for clipping,
overlap, and table or figure legibility.

## QA Record

The current pre-freeze bundle was rebuilt and audited on 2026-08-08:

- official INFORMS PDF: 71 pages, with references beginning on page 64 (63
  pre-reference pages; the final-freeze page cap was deliberately not run);
- browser body preview: 50 pages;
- browser supplement preview: 77 pages;
- abstract: exactly 292 words in one paragraph, with normalized source-to-PDF
  equality;
- all 198 rendered pages: US Letter, no blank pages, no identity or artifact
  fingerprints; an adversarial high-resolution inspection covered the dense
  Related Work table, both theory suites, all principal figures, S12A--S12C,
  and both S13B panels for clipping, overlap, formula rendering, and
  table/figure legibility;
- the supplement's long prose tables were split and wrapped, the envelope
  image retains accessible alternative text without printing a duplicate
  caption, and S13B Panel B begins on a fresh page;
- the sealed-parent extension reproduced the 45-table/10-figure manifest with
  unavailable historical DVC bytes pinned to their unchanged descriptors;
  `publication-integrity` and a second bytewise extension check passed;
- official compiler scan: converged, with no undefined citation, reference, or
  rerun request; the remaining 17.54-point `maketitle` overfull warning belongs
  to the publisher header and has no visible clipping; and
- machine-readable supplement: rebuilt from the active evidence surface and
  passed its exact-content check.

This remains a pre-freeze record. Scientifically useful material was not removed
to meet a page target. A later explicit final freeze must rebuild all outputs,
run `just submission-freeze-check`, replace these counts, and visually inspect
every regenerated reviewer page again.

## Acceptance Criteria

- the evidence source registry and manifest verify by hash;
- generated TeX is current with QMD;
- `.blg` has no warnings and `.log` has no undefined citations or labels;
- the pre-reference body is within the IJDS limit at final freeze (deferred during
  active scientific editing);
- all tables and figures are legible and inside margins;
- reviewer files contain no identity, local path, commit, tag, or hash;
- the abstract stays below 300 words;
- no retired endpoint or favorable `.25` claim returns; and
- the package contains exactly 53 registered DVC pointers, 11 scientific Git
  artifact lineages, and 45 paper-facing CSV tables, with unequal-follow-up roots labeled
  only as replay provenance;
- scientific, drift, publication, compilation, and visual gates pass.

This is still pre-freeze. Final tagging and ScholarOne proof comparison require
an explicit later freeze decision.
