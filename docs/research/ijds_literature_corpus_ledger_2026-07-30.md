# IJDS literature corpus ledger (through 2026-07-31)

Status: documentary literature-provenance record; not an empirical evidence
source and not an entry in the active-evidence registry.

## Scope and authority

This is the cumulative receipt for the five last-mile literature objects
materialized on 2026-07-30 and the six-object frontier intake audited on
2026-07-31. The latter consists of five newly materialized PDFs plus the
already-local non-monotonic conformal-risk-control preprint. It closes the
byte-level gaps recorded in
`conformal_decision_sota_lastmile_2026-07-26.md` and
`conformal_optimization_v3_corpus_addendum_2026-07-26.md`. The earlier audits
remain the authority for theorem interpretation; this ledger is the authority
for local PDF version, byte identity, parser route, visual QA, citation key, and
paper-facing disposition.

The canonical local corpus is
`C:\Users\carlos\Documents\Paper_CRPTO\Papers_tesis\supplement`. PDF objects are
ignored by Git. No PDF was overwritten, `EXTRACTION_MANIFEST.json` was not
modified, and no protected DVC stage was invoked.

After the 2026-07-31 intake, `Papers_tesis` contains 132 PDF objects and 4,924
pages, versus 122 objects and 4,673 pages at the 2026-07-21 checksum. A
full-file inventory found 132 distinct full SHA-1 values and no duplicate PDF
object; the receipts below additionally use SHA-256. The current dynamic
inventory is
`.tmp_pdf_intake_benchmark/literature-frontier-20260731/corpus_inventory_post_intake.jsonl`.
The complete repository inventory has 134 PDFs because it also includes the
current body and supplement PDFs outside `Papers_tesis`.

## Exact-object ledger

| Work / exact version | Canonical local PDF | Bytes | Pages | SHA-256 | License recorded by primary surface/PDF | BibTeX key | Citation surface | Intake grade and disposition | Audit date |
|---|---|---:|---:|---|---|---|---|---|---|
| Zhao et al., *Conformal Predictive Programming for Chance Constrained Optimization*, arXiv:2402.07407v3, revised 2026-07-09 | `Papers_tesis/supplement/Zhao et al 2024 - Conformal Predictive Programming for Chance Constrained Optimization - arXiv 2402.07407v3.pdf` | 566,281 | 17 | `a967c53a4bf9fa42a1bd8603dc652b2c3bea0bdd408c2a3191487982ccac13e5` | CC BY 4.0 | `zhao2024cpp` | Body and supplement | **A.** Retain as adjacent chance-constrained conformal optimization; no funded-set, zero-threshold, or temporal-transport guarantee transfers to CRPTO. | 2026-07-30 |
| Zhou and Zhu, *Calibrating Decision Robustness via Inverse Conformal Risk Control*, arXiv:2510.07750v3, revised 2026-06-10 | `Papers_tesis/supplement/Zhou Zhu 2025 - Calibrating Decision Robustness via Inverse Conformal Risk Control - arXiv 2510.07750v3.pdf` | 1,111,714 | 22 | `8b7979c6c242570eab2b616d46609a1ac146ae91d0ae7ffdddaf9f3d1a8f03f4` | CC BY 4.0 | `zhou2026creme` | Body and supplement | **A.** Retain for expected miscoverage--regret assessment and split recalibration; do not call the displayed frontier a simultaneous realized-sample certificate. | 2026-07-30 |
| Lützow et al., *Multi-Variable Conformal Prediction: Optimizing Prediction Sets without Data Splitting*, arXiv:2605.12341v1, submitted 2026-05-12 | `Papers_tesis/supplement/Lutzow et al 2026 - Multi-Variable Conformal Prediction - arXiv 2605.12341v1.pdf` | 1,939,154 | 23 | `e23eb85c303a6756adb894204b72b1eca41352f13e458f1b70f421abda1f5955` | arXiv non-exclusive distribution license; local research copy, not redistributed by Git | `lutzow2026mcp` | Body and supplement | **A-local.** Retain as an adjacent set-design construction; MCP identifies geometry through a new objective and assumptions, not through CRPTO's binary set alone. | 2026-07-30 |
| Shekhar and Howard, *Decision-Calibrated Conformal Uncertainty for Pacing Decisions in Streaming Advertising*, arXiv:2606.10187v1, submitted 2026-06-08 | `Papers_tesis/supplement/Shekhar Howard 2026 - Decision-Calibrated Conformal Uncertainty - arXiv 2606.10187v1.pdf` | 2,717,280 | 29 | `546e3803f1e827a638b375c076f4c49e2f757068f2e2555972630cac4ad89ac6` | arXiv non-exclusive distribution license; local research copy, not redistributed by Git | `shekhar2026decision_calibrated_pacing` | Body and supplement | **A-local.** Retain as the closest catalog-uniform decision-calibrated construction; its block-exchangeability and simultaneous policy-catalog contract do not transfer to CRPTO. | 2026-07-30 |
| Wei and Zhang, *Adjustability in Robust Linear Optimization*, *Mathematical Programming* 208:581--628, Springer version of record, published 2024-01-27 | `Papers_tesis/supplement/Wei Zhang 2024 - Adjustability in Robust Linear Optimization - Springer VoR DOI 10.1007_s10107-023-02049-w.pdf` | 703,533 | 48 | `0359742a6f1dee3aed92085f490beb405ef1cc21a4af1eaf5563f6834244bb58` | CC BY 4.0 | `wei2024adjustability` | Body and supplement | **A.** Retain only as a normal-cone/co-optimality anchor for linear objectives over a common feasible set; it supplies no conformal, temporal, selected-set, or credit-specific guarantee. | 2026-07-30 |
| Zhao et al., *Calibrating Predictions to Decisions: A Novel Approach to Multi-Class Calibration*, NeurIPS 2021 | `Papers_tesis/supplement/Zhao et al 2021 - Calibrating Predictions to Decisions.pdf` | 957,387 | 12 | `59be9b445e086fe149ec5b44c6102e76a62068ef8d889a0935637823d6dec90c` | NeurIPS proceedings object; no open license asserted in the local PDF, so retained only as a local research copy | `zhao2021decisioncalibration` | Body and supplement | **A.** Retain as the foundational loss-family-relative decision-calibration reference. It is probability recalibration for declared decision classes, not conformal coverage, temporal transport, or funded-set validity. | 2026-07-31 |
| Im, Benslimane, and Grigas, *Smart Surrogate Losses for Contextual Stochastic Linear Optimization with Robust Constraints*, NeurIPS 2025 | `Papers_tesis/supplement/Im Benslimane Grigas 2025 - Smart Surrogate Losses with Robust Constraints.pdf` | 4,842,032 | 26 | `4018d40a45c30ff0f4b6106179d194b5212fe397878e72a20d7aabeedc3c7f37` | CC BY 4.0 on the primary arXiv record; local bytes are the NeurIPS proceedings version | `im2025spor` | Body and supplement | **A.** Retain as the closest integrated SPO treatment of uncertain robust constraints. Its conformal uncertainty set is an upstream module, its Fisher-consistency assumptions are explicit, and it supplies no post-selection or temporal guarantee for CRPTO. | 2026-07-31 |
| Angelopoulos, *Conformal Risk Control for Non-Monotonic Losses*, arXiv:2602.20151v1 | `Papers_tesis/supplement/Angelopoulos et al 2026 - Conformal Risk Control for Non-Monotonic Losses.pdf` | 1,039,161 | 22 | `099ff363853ea8150dfafb2b23e17a5137c4b5dbdb911db9b1e193b9de4d42dd` | arXiv non-exclusive distribution license; local research copy, not redistributed by Git | `angelopoulos2026nonmonotonic` | Prospective-design boundary | **B.** Retain for the stability-based route to non-monotonic or multidimensional risk control. The theorem requires exchangeability, a symmetric algorithm, a risk-controlling full-data reference rule, and a verified stability remainder; none is supplied by the active CRPTO archive. | 2026-07-31 |
| Caunhye, Lu, and Martin-Barragan, *Smart predict-then-robustly-optimize*, arXiv:2607.21773v1 | `Papers_tesis/supplement/Caunhye Lu Martin-Barragan 2026 - Smart Predict Then Robustly Optimize - arXiv 2607.21773v1.pdf` | 2,248,235 | 40 | `cb4b3e9478367d5bc44a9133b87dd043e07a6e017a8ed00c352d62b64058018a` | CC BY 4.0 | `caunhye2026smartptro` | Watchlist only | **C.** Keep as a current feature-perturbation/SPO neighbor. It robustifies covariates and surrogate loss under sub-Gaussian and structural assumptions; it is not a conformal-calibration or selected-set construction. | 2026-07-31 |
| Guo, *Learning Predictive Ambiguity Sets for Decision-Focused Distributionally Robust Optimization*, arXiv:2607.09820v1 | `Papers_tesis/supplement/Guo 2026 - Learning Predictive Ambiguity Sets - arXiv 2607.09820v1.pdf` | 779,683 | 7 | `b4614c3306274d97b8bf740c93f1cf36b3a673c68e3ee3e4cb9b977e59808168` | CC BY 4.0 | `guo2026lpas` | Watchlist only | **C.** Keep as a learned-radius DRO idea, not affirmative support. The v1 has no coverage theorem, uses one rolling split over 20 assets, and reports that decision-aware tuning leaves empirical coverage below nominal and would require conformal post-calibration. | 2026-07-31 |
| Ziliaskopoulos, Vinel, and Smith, *Decision-Value Attribution in Predict-then-Optimize Systems*, arXiv:2606.29878v1 | `Papers_tesis/supplement/Ziliaskopoulos Vinel Smith 2026 - Decision Value Attribution - arXiv 2606.29878v1.pdf` | 4,408,295 | 27 | `b5447fe2e8804701b688eb75717dceaac993a93be2f21843f48d5bd8f7f73fe5` | arXiv non-exclusive distribution license; local research copy, not redistributed by Git | `ziliaskopoulos2026dva` | Watchlist / conceptual context | **B.** Retain as an adjacent explanation framework for when predictive changes do or do not matter downstream. Its Shapley attributions depend on the background and player grouping, can be computationally approximate, are noncausal, and provide no calibration or conformal guarantee. | 2026-07-31 |

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

### 2026-07-31 frontier-intake QA

The six additional objects are born-digital and unencrypted. PyPDF found zero
empty pages and zero pages with fewer than 200 extracted characters. Median
text-layer characters per page were 3,820 for Zhao, 3,404 for Im--Benslimane--
Grigas, 2,414.5 for Caunhye--Lu--Martin-Barragan, 4,537 for Guo, 3,192 for
Ziliaskopoulos--Vinel--Smith, and 2,385.5 for Angelopoulos. The five newly
downloaded files match their source copies byte for byte after transfer into
the clean integration clone.

Primary-source metadata were checked against the NeurIPS proceedings for Zhao
and Im--Benslimane--Grigas and against the exact arXiv version pages for the
three 2026 watchlist objects and Angelopoulos. Poppler renders were then
compared with the extracted text:

| Object | Pages visually checked | Objects checked | Result |
|---|---|---|---|
| Zhao et al. (2021) | 1, 5 | Title/authors/proceedings banner; decision-calibration characterization and bounded-action qualification | The proceedings identity, table, theorem statement, and restriction to declared loss/decision families are legible and agree with extraction. |
| Im, Benslimane, and Grigas (2025) | 1, 4 | Proceedings identity; Fisher-consistency assumptions and theorem | The conformal-set modularity and full-distribution/unrestricted-class/uniqueness/symmetry assumptions are visible; this is not a conformal-validity theorem. |
| Caunhye, Lu, and Martin-Barragan (2026) | 1, 13 | arXiv v1 identity; sub-Gaussian surrogate-gap theorem | Formulas and assumptions are intact; the result concerns robust feature perturbation and surrogate alignment, not calibrated coverage. |
| Guo (2026) | 1, 6 | arXiv v1 identity; empirical-coverage figures and limitations | The below-nominal post-tuning coverage admission, one-split limitation, and call for conformal post-calibration are explicit and legible. |
| Ziliaskopoulos, Vinel, and Smith (2026) | 1, 17 | arXiv v1 identity; decision-value interpretation and limitations | The dependence on background distributions/player grouping, approximation error, and noncausal boundary are explicit. |
| Angelopoulos (2026) | 1, 2 | arXiv v1 identity; Theorem 1 and monotonic-loss specialization | Exchangeability, symmetry, reference-rule control, and the stability remainder are explicit and agree with extraction. |

## Bibliography and use boundary

`paper/references.bib` now pins Zhao and Zhou--Zhu to their exact v3 URLs and
DOIs, contains `wei2024adjustability`, and adds exact proceedings records for
`zhao2021decisioncalibration` and `im2025spor`. Existing keys for Lützow and
Shekhar--Howard already pin v1. The new watchlist keys are
`caunhye2026smartptro`, `guo2026lpas`, and `ziliaskopoulos2026dva`; their
presence does not by itself authorize a manuscript claim. The
weighted-conformal citation `tibshirani2019covshift` was already present and
was not duplicated.

The same metadata pass corrected three older records: Johnstone--Cox now names
the Tenth Symposium on Conformal and Probabilistic Prediction and Applications
and pages 72--90; Sun--Liu--Li now pins arXiv v4, revised 2024-05-10; and the
compatibility key `lekeufack2023cdt` now records the published ICRA 2024 paper,
pages 11668--11675, DOI `10.1109/ICRA57147.2024.10610041`. The compatibility
key was retained to avoid breaking historical citations; its year and venue are
no longer represented by the key name.

These PDFs are literature objects only. Their intake does not activate a
method, model, policy, theorem, result, selected ruler, or empirical evidence
source for CRPTO.
