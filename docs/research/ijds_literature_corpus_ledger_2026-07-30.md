# IJDS literature corpus ledger (2026-07-30)

Status: documentary literature-provenance record; not an empirical evidence
source and not an entry in the active-evidence registry.

## Scope and authority

This is the single receipt for the five last-mile literature objects
materialized on 2026-07-30. It closes the byte-level gaps recorded in
`conformal_decision_sota_lastmile_2026-07-26.md` and
`conformal_optimization_v3_corpus_addendum_2026-07-26.md`. The earlier audits
remain the authority for theorem interpretation; this ledger is the authority
for local PDF version, byte identity, parser route, visual QA, citation key, and
paper-facing disposition.

The canonical local corpus is
`C:\Users\carlos\Documents\Paper_CRPTO\Papers_tesis\supplement`. PDF objects are
ignored by Git. No PDF was overwritten, `EXTRACTION_MANIFEST.json` was not
modified, and no protected DVC stage was invoked.

After intake, `Papers_tesis` contains 127 PDF objects and 4,812 pages, versus
122 objects and 4,673 pages at the 2026-07-21 checksum. A full-file inventory
found 127 distinct full SHA-1 values; the five receipts below additionally use
SHA-256. The post-intake inventory is
`.tmp_pdf_intake_benchmark/literature-materialization-20260730/corpus_inventory_post_intake.jsonl`.

## Exact-object ledger

| Work / exact version | Canonical local PDF | Bytes | Pages | SHA-256 | License recorded by primary surface/PDF | BibTeX key | Citation surface | Intake grade and disposition | Audit date |
|---|---|---:|---:|---|---|---|---|---|---|
| Zhao et al., *Conformal Predictive Programming for Chance Constrained Optimization*, arXiv:2402.07407v3, revised 2026-07-09 | `Papers_tesis/supplement/Zhao et al 2024 - Conformal Predictive Programming for Chance Constrained Optimization - arXiv 2402.07407v3.pdf` | 566,281 | 17 | `a967c53a4bf9fa42a1bd8603dc652b2c3bea0bdd408c2a3191487982ccac13e5` | CC BY 4.0 | `zhao2024cpp` | Body and supplement | **A.** Retain as adjacent chance-constrained conformal optimization; no funded-set, zero-threshold, or temporal-transport guarantee transfers to CRPTO. | 2026-07-30 |
| Zhou and Zhu, *Calibrating Decision Robustness via Inverse Conformal Risk Control*, arXiv:2510.07750v3, revised 2026-06-10 | `Papers_tesis/supplement/Zhou Zhu 2025 - Calibrating Decision Robustness via Inverse Conformal Risk Control - arXiv 2510.07750v3.pdf` | 1,111,714 | 22 | `8b7979c6c242570eab2b616d46609a1ac146ae91d0ae7ffdddaf9f3d1a8f03f4` | CC BY 4.0 | `zhou2026creme` | Body and supplement | **A.** Retain for expected miscoverage--regret assessment and split recalibration; do not call the displayed frontier a simultaneous realized-sample certificate. | 2026-07-30 |
| Lützow et al., *Multi-Variable Conformal Prediction: Optimizing Prediction Sets without Data Splitting*, arXiv:2605.12341v1, submitted 2026-05-12 | `Papers_tesis/supplement/Lutzow et al 2026 - Multi-Variable Conformal Prediction - arXiv 2605.12341v1.pdf` | 1,939,154 | 23 | `e23eb85c303a6756adb894204b72b1eca41352f13e458f1b70f421abda1f5955` | arXiv non-exclusive distribution license; local research copy, not redistributed by Git | `lutzow2026mcp` | Body and supplement | **A-local.** Retain as an adjacent set-design construction; MCP identifies geometry through a new objective and assumptions, not through CRPTO's binary set alone. | 2026-07-30 |
| Shekhar and Howard, *Decision-Calibrated Conformal Uncertainty for Pacing Decisions in Streaming Advertising*, arXiv:2606.10187v1, submitted 2026-06-08 | `Papers_tesis/supplement/Shekhar Howard 2026 - Decision-Calibrated Conformal Uncertainty - arXiv 2606.10187v1.pdf` | 2,717,280 | 29 | `546e3803f1e827a638b375c076f4c49e2f757068f2e2555972630cac4ad89ac6` | arXiv non-exclusive distribution license; local research copy, not redistributed by Git | `shekhar2026decision_calibrated_pacing` | Body and supplement | **A-local.** Retain as the closest catalog-uniform decision-calibrated construction; its block-exchangeability and simultaneous policy-catalog contract do not transfer to CRPTO. | 2026-07-30 |
| Wei and Zhang, *Adjustability in Robust Linear Optimization*, *Mathematical Programming* 208:581--628, Springer version of record, published 2024-01-27 | `Papers_tesis/supplement/Wei Zhang 2024 - Adjustability in Robust Linear Optimization - Springer VoR DOI 10.1007_s10107-023-02049-w.pdf` | 703,533 | 48 | `0359742a6f1dee3aed92085f490beb405ef1cc21a4af1eaf5563f6834244bb58` | CC BY 4.0 | `wei2024adjustability` | Body and supplement | **A.** Retain only as a normal-cone/co-optimality anchor for linear objectives over a common feasible set; it supplies no conformal, temporal, selected-set, or credit-specific guarantee. | 2026-07-30 |

## Parser and text-layer QA

All five objects are born-digital, unencrypted, have zero empty pages and zero
pages below 200 extracted characters. Median text-layer yield per page was
4,375 characters for Zhao, 3,835.5 for Zhou--Zhu, 3,529 for Lützow, 3,340 for
Shekhar--Howard, and 2,603 for Wei--Zhang. PyPDF 6.10.0 was used for the
all-page text-layer and metadata pass.

Docling was the primary parser with OCR and enrichment disabled. The requested
`referenced` image-export mode parsed the first document but failed during
export because Docling did not create its referenced-image artifact directory.
A clean fallback run used `placeholder` image export while retaining Markdown
and JSON layout, table, formula, and hierarchy extraction. Parser outputs and
both logs are under
`.tmp_pdf_intake_benchmark/literature-materialization-20260730/`.

The successful five-document run processed 139 pages in approximately 267
seconds (1.92 seconds per page, measured from process start to final output
timestamp). Its output scorecard is:

| Object | Markdown bytes | JSON bytes | Section headings | Formula items | Tables | Pictures | Parser warning |
|---|---:|---:|---:|---:|---:|---:|---|
| Zhao v3 | 80,489 | 633,744 | 26 | 52 | 0 | 3 | None |
| Zhou--Zhu v3 | 75,999 | 1,296,193 | 26 | 67 | 1 | 10 | None |
| Lützow et al. v1 | 78,646 | 1,010,504 | 34 | 42 | 3 | 10 | None |
| Shekhar--Howard v1 | 99,591 | 837,375 | 35 | 108 | 7 | 7 | None |
| Wei--Zhang version of record | 153,425 | 2,701,022 | 36 | 79 | 9 | 51 | One table-cell left coordinate on page 29 was outside the page boundary and was clamped to zero; targeted table/formula renders remained legible. |

## Manual visual QA

Poppler 26.05.0 renders were compared with the all-page extracted text. The
rendered contact sheets are under
`.tmp_pdf_intake_benchmark/literature-materialization-20260730/visual`.

| Object | Pages visually checked | Objects checked | Result |
|---|---|---|---|
| Zhao v3 | 1, 6--8 | Version banner; Theorems 3.4--3.6; quantile-shift qualification; robust and Mondrian CPP; case-study figures | Title/version, equations, theorem qualifiers, headings, and figure captions are legible and agree with the extracted text. |
| Zhou--Zhu v3 | 1, 5, 6, 8, 15 | Theorem 3.4; Proposition 3.5; Proposition 3.7; corrected Algorithm 1 denominators; Table 1; post-selection proof | The v3 split denominator is `|I_j|`; the duplicated `|Lambda|=10`/`20` sensitivity rows remain visible; formulas and proof layout are intact. |
| Lützow et al. v1 | 1, 4, 6, 7, 23 | Exchangeability/regularity assumptions; RemMCP Theorem 1; RelMCP Theorem 2 and Algorithm 1; limitations | Equations, assumptions, algorithm, and dimension/removal-budget qualifications are legible and agree with extraction. |
| Shekhar--Howard v1 | 1, 8, 9, 24 | Calibration quantities; Proposition 5.1; selector algorithm; DKW step and union-bound proof | Equations, algorithm, finite-catalog contract, and DKW/sample-complexity layer are legible and agree with extraction. |
| Wei--Zhang version of record | 1, 10, 14 | Publication identity; Definition 5; common-normal-cone/co-optimality statement; Theorem 2; co-optimal index cover | Version-of-record metadata, normal-cone formulas, theorem statement, and optimization display are intact. |

## Bibliography and use boundary

`paper/references.bib` now pins Zhao and Zhou--Zhu to their exact v3 URLs and
DOIs and contains `wei2024adjustability`. Existing keys for Lützow and
Shekhar--Howard already pin v1. The weighted-conformal citation
`tibshirani2019covshift` was already present and was not duplicated.

These PDFs are literature objects only. Their intake does not activate a
method, model, policy, theorem, result, selected ruler, or empirical evidence
source for CRPTO.
