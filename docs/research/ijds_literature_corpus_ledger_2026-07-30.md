# IJDS literature corpus ledger (through 2026-08-01)

Status: documentary literature-provenance record; not an empirical evidence
source and not an entry in the active-evidence registry.

## Scope and authority

This is the cumulative receipt for the five last-mile literature objects
materialized on 2026-07-30, two distinct intakes audited on 2026-07-31, and the
four-object theory-neighbor intake audited on 2026-08-01. The 2026-07-31
frontier intake consists of five newly materialized PDFs plus the already-local
non-monotonic conformal-risk-control preprint. The active-citation gap intake
materialized 19 PDFs from primary or official open-access surfaces and left
four works as metadata-only citations because no suitable primary/open full
text was verified. The 2026-08-01 intake adds exact versions for non-monotone
CRC, generalized Venn calibration, temperature scaling before conformal
prediction, and conformal mixed-integer constraint learning. Together these
receipts close the byte-level gaps recorded in
`conformal_decision_sota_lastmile_2026-07-26.md` and
`conformal_optimization_v3_corpus_addendum_2026-07-26.md`. The earlier audits
remain the authority for theorem interpretation; this ledger is the authority
for local PDF version, byte identity, parser route, visual QA, citation key, and
paper-facing disposition.

The canonical local corpus is the repository-relative
`Papers_tesis/supplement`. PDF objects are ignored by Git. No pre-existing PDF
was overwritten, `EXTRACTION_MANIFEST.json` was not modified, and no protected
DVC stage was invoked.

After the 2026-07-31 intake, `Papers_tesis` contains 132 PDF objects and 4,924
pages, versus 122 objects and 4,673 pages at the 2026-07-21 checksum. A
full-file inventory found 132 distinct full SHA-1 values and no duplicate PDF
object; the receipts below additionally use SHA-256. That dated SHA-1 result is
retained here as a historical receipt; no `.tmp_pdf_intake_benchmark` object is
required to reconstruct or validate the current inventory.

After the 2026-07-31 active-citation gap intake, `Papers_tesis` contains 151 PDF
objects, 5,408 pages, and 310,330,945 bytes. A full strict-parser and SHA-256
pass found 151 distinct hashes, no duplicate object, no encrypted object, and
no parse error. The 19 new objects contribute 484 pages and 23,444,014 bytes.

After the 2026-08-01 theory-neighbor intake, `Papers_tesis` contains 155 PDF
objects, 5,533 pages, and 319,875,860 bytes. A fresh full-corpus strict-PyPDF
and SHA-256 pass found 155 distinct hashes, no duplicate object, no encrypted
object, and no parse error. The four new objects contribute 125 pages and
9,544,915 bytes.

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
| Caunhye, Lu, and Martin-Barragan, *Smart predict-then-robustly-optimize*, arXiv:2607.21773v1 | `Papers_tesis/supplement/Caunhye Lu Martin-Barragan 2026 - Smart Predict Then Robustly Optimize - arXiv 2607.21773v1.pdf` | 2,248,235 | 40 | `cb4b3e9478367d5bc44a9133b87dd043e07a6e017a8ed00c352d62b64058018a` | CC BY 4.0 | `caunhye2026smartptro` | Body and supplement; watchlist context only | **C.** Keep as a current feature-perturbation/SPO neighbor. It robustifies covariates and surrogate loss under sub-Gaussian and structural assumptions; it is not a conformal-calibration or selected-set construction. | 2026-07-31 |
| Guo, *Learning Predictive Ambiguity Sets for Decision-Focused Distributionally Robust Optimization*, arXiv:2607.09820v1 | `Papers_tesis/supplement/Guo 2026 - Learning Predictive Ambiguity Sets - arXiv 2607.09820v1.pdf` | 779,683 | 7 | `b4614c3306274d97b8bf740c93f1cf36b3a673c68e3ee3e4cb9b977e59808168` | CC BY 4.0 | `guo2026lpas` | Body and supplement; watchlist context only | **C.** Keep as a learned-radius DRO idea, not affirmative support. The v1 has no coverage theorem, uses one rolling split over 20 assets, and reports that decision-aware tuning leaves empirical coverage below nominal and would require conformal post-calibration. | 2026-07-31 |
| Ziliaskopoulos, Vinel, and Smith, *Decision-Value Attribution in Predict-then-Optimize Systems*, arXiv:2606.29878v1 | `Papers_tesis/supplement/Ziliaskopoulos Vinel Smith 2026 - Decision Value Attribution - arXiv 2606.29878v1.pdf` | 4,408,295 | 27 | `b5447fe2e8804701b688eb75717dceaac993a93be2f21843f48d5bd8f7f73fe5` | arXiv non-exclusive distribution license; local research copy, not redistributed by Git | `ziliaskopoulos2026dva` | Body and supplement; conceptual context only | **B.** Retain as an adjacent explanation framework for when predictive changes do or do not matter downstream. Its Shapley attributions depend on the background and player grouping, can be computationally approximate, are noncausal, and provide no calibration or conformal guarantee. | 2026-07-31 |

## Active-citation PDF gap intake — 2026-07-31

The starting gap contained 23 works already cited on active manuscript or
supplement surfaces but lacking a local PDF. Nineteen exact objects were
obtained from primary, official, or author/institutional open-access surfaces.
Public downloadability is not treated as a general redistribution license:
objects without an explicit open license remain local research copies and are
ignored by Git.

| BibTeX key | Canonical local PDF | Primary/official provenance and access boundary | Bytes | Pages | SHA-256 |
|---|---|---|---:|---:|---|
| `bao2024fcr_conformal` | `Papers_tesis/supplement/Bao et al 2024 - Selective Conformal Inference with False Coverage-Statement Rate Control - arXiv 2301.00584v5.pdf` | [arXiv v5](https://arxiv.org/abs/2301.00584); arXiv distribution license, local research copy | 1,050,169 | 54 | `e285bef33b4d3285ff9db6da3e5989c82757a76863264514b50c702c3cc38bf7` |
| `benjamini2005fcr` | `Papers_tesis/supplement/Benjamini and Yekutieli 2005 - False Discovery Rate-Adjusted Multiple Confidence Intervals for Selected Parameters.pdf` | [author-hosted version of record](https://www.math.tau.ac.il/~yekutiel/papers/JASA%20FCR%20prints.pdf); local research copy, no systematic redistribution | 351,048 | 12 | `eca6eb8937296c0ee95f6dfc5890603677d433d5c2a38ba0a01eb503176499fd` |
| `bian2023training_conditional` | `Papers_tesis/supplement/Bian and Barber 2023 - Training-Conditional Coverage for Distribution-Free Predictive Inference - arXiv 2205.03647v2.pdf` | [arXiv v2](https://arxiv.org/abs/2205.03647); arXiv distribution license, local research copy | 1,263,346 | 24 | `36810566c4c33d45e21d63ebd6da339e3ac5b9afc38417d02b77f243649fc601` |
| `gazin2024transductive` | `Papers_tesis/supplement/Gazin et al 2024 - Transductive Conformal Inference with Adaptive Scores.pdf` | [PMLR version of record](https://proceedings.mlr.press/v238/gazin24a.html); CC BY 4.0 | 1,055,392 | 26 | `49d977b97dcc2b4dd66041f38a63e701c053204738a5901c2dd466eed8a294f2` |
| `guerdan2024policy_comparison` | `Papers_tesis/supplement/Guerdan et al 2024 - Predictive Performance Comparison of Decision Policies Under Confounding.pdf` | [PMLR version of record](https://proceedings.mlr.press/v235/guerdan24a.html); CC BY 4.0 | 967,362 | 33 | `17501eab8e79278ceaab82433e4bcba638a80fc937717ba9bee7359e4b73d710` |
| `huangfu_parallelizing_2018` | `Papers_tesis/supplement/Huangfu and Hall 2018 - Parallelizing the Dual Revised Simplex Method.pdf` | [Edinburgh version-of-record record](https://www.research.ed.ac.uk/en/publications/parallelizing-the-dual-revised-simplex-method/); CC BY | 4,172,331 | 26 | `b0b2b389657a944f4c1d91f6d9e8af7af8c774683b5b799ddb5261fc5c55db9d` |
| `kleinberg2018human` | `Papers_tesis/supplement/Kleinberg et al 2018 - Human Decisions and Machine Predictions.pdf` | [Stanford author-hosted QJE version](https://cs.stanford.edu/~jure/pubs/bail-qje17.pdf); local research copy | 1,584,795 | 53 | `29328df7b3d704676f8cda75969b55aaa73f3cf644f9357d997a09220d53a60f` |
| `kull2017` | `Papers_tesis/supplement/Kull Silva Filho Flach 2017 - Beta Calibration.pdf` | [PMLR version of record](https://proceedings.mlr.press/v54/kull17a.html); CC BY 4.0 | 389,366 | 9 | `3d3de5ee33d442c415c689c59b490ef09f310dc0c0e4bde47fb92a8c6f5f0e1a` |
| `lakkaraju2017selective` | `Papers_tesis/supplement/Lakkaraju et al 2017 - The Selective Labels Problem.pdf` | [author-hosted KDD paper](https://www.cs.cornell.edu/info/people/kleinber/kdd17-selective.pdf); public author manuscript, no general CC license asserted | 1,507,709 | 10 | `ccc62a45799ce768e07799ae9a3c990d3ba5960b0a1d3afc884280e739b51a90` |
| `lessmann2015` | `Papers_tesis/supplement/Lessmann et al 2015 - Benchmarking State-of-the-Art Classification Algorithms for Credit Scoring - Accepted Manuscript.pdf` | [Southampton accepted manuscript](https://eprints.soton.ac.uk/377196/); CC BY-NC-ND | 1,398,930 | 33 | `67d74f428effcb3d30716c6a0dfe42c17cbe7312fe9dc6034bb29f1d1e824f6f` |
| `li2023online_loans` | `Papers_tesis/supplement/Li et al 2023 - The Profitability of Online Loans - A Competing Risks Analysis on Default and Prepayment.pdf` | [author publication record](https://ag-bellotti.owlstown.net/publications); author-hosted version of record, all rights reserved/local only | 2,617,746 | 18 | `9837c75719d50fb880c5e591ac27267eb47fb1df25e16655da00d9eaa7bd3b3e` |
| `maiapolo2024partial_id_eval` | `Papers_tesis/supplement/Maia Polo et al 2024 - Weak Supervision Performance Evaluation via Partial Identification.pdf` | [NeurIPS proceedings version](https://proceedings.neurips.cc/paper_files/paper/2024/hash/f4c6bec746b0aeca8c2cd15096f1ad1f-Abstract-Conference.html); official open proceedings, no general CC license asserted | 2,554,735 | 37 | `5812210a239a0ea3ba36aae47a2d944cf9737940ff978b16c9d7abab282bdbc9` |
| `navaspalencia2020` | `Papers_tesis/supplement/Navas-Palencia 2020 - Optimal Binning - arXiv 2001.08025v3.pdf` | [arXiv v3](https://arxiv.org/abs/2001.08025); arXiv distribution license, local research copy | 493,806 | 22 | `0b915405d5306c64af4900ba0fe201992d8c051ae0d1f557f40163f0f80e55bf` |
| `sadinle2019lac` | `Papers_tesis/supplement/Sadinle Lei Wasserman 2019 - Least Ambiguous Set-Valued Classifiers - arXiv 1609.00451v2.pdf` | [arXiv v2](https://arxiv.org/abs/1609.00451); author manuscript, local research copy | 830,218 | 44 | `b790160a3feaaf9c05987840c17d983ee22ae23fa0a50fc9f5f7e9c6741d9be1` |
| `vovk2012conditional` | `Papers_tesis/supplement/Vovk 2012 - Conditional Validity of Inductive Conformal Predictors.pdf` | [PMLR version of record](https://proceedings.mlr.press/v25/vovk12.html); official open proceedings | 419,379 | 16 | `7687a3be5702c52074e1b48e7317f1e068e9581ff832c65f7efca659c665ed3a` |
| `vovk2003mondrian` | `Papers_tesis/supplement/Vovk Lindsay Nouretdinov Gammerman 2003 - Mondrian Confidence Machine.pdf` | [ALRW working paper](https://alrw.net/old/old.html); author-maintained public copy, no general CC license asserted | 282,572 | 24 | `cce239ecea71ef7287d73071cec56056fdf6866c9d633897596c30b8aa52c130` |
| `vovk2014` | `Papers_tesis/supplement/Vovk Petej 2014 - Venn-Abers Predictors - UAI.pdf` | [official UAI proceedings](https://www.auai.org/uai2014/acceptedPapers.shtml); public proceedings copy, no general CC license asserted | 247,596 | 10 | `551d296c86bc1317e22b6cbb8ab8dcfad79286778071564ca68cd7d517f271c9` |
| `zadrozny2002` | `Papers_tesis/supplement/Zadrozny Elkan 2002 - Transforming Classifier Scores into Accurate Multiclass Probability Estimates.pdf` | [official ACM Digital Library](https://dl.acm.org/doi/10.1145/775047.775151); publicly accessible, no retroactive CC license asserted | 690,254 | 6 | `e1437da5c0b28f4052302706daa45bba27b2c47cc85bbd5592d824f38681b5b0` |
| `zaffran2023missing` | `Papers_tesis/supplement/Zaffran et al 2023 - Conformal Prediction with Missing Values.pdf` | [PMLR version of record](https://proceedings.mlr.press/v202/zaffran23a.html); CC BY 4.0 | 1,567,260 | 27 | `80d2a6482a415d424e8cc77f4bcac0da0a4e45413cf77c2d60f00e858e0d5a15` |

Four active citations remain deliberately metadata-only:

| BibTeX key | Official landing | Why no local PDF was accepted | Safe next route |
|---|---|---|---|
| `holm1979` | [JSTOR](https://www.jstor.org/stable/4615733) | No primary/open PDF with sufficiently clear provenance and reuse terms was verified; an unlicensed university mirror was rejected. | Obtain through an institutional JSTOR entitlement or the rights holder. |
| `manski2003partial` | [Springer](https://link.springer.com/book/10.1007/b97478) | Subscription book; no official OA full text was found. | Library/licensed acquisition or author permission. |
| `platt2000` | [MIT Press book landing](https://mitpress.mit.edu/9780262194488/advances-in-large-margin-classifiers/) | No stable official OA full chapter was found. | Library/licensed acquisition or author permission. |
| `vovk2005` | [Springer](https://link.springer.com/book/10.1007/b106715) | Subscription book; the authors' site points to the book rather than an OA full text. | Library/licensed acquisition or author permission. |

All 19 accepted objects begin with a real PDF header, pass strict PyPDF parsing,
are unencrypted, and have zero pages with an empty extracted-text layer. There
are no duplicate SHA-256 values either within the intake or against the prior
132-object corpus. Huangfu--Hall has two pages below 200 extracted characters;
both are cover/license pages rather than missing OCR. The intake closes a
documentary provenance gap only: it activates no theorem, empirical result,
policy, or manuscript claim.

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
both logs were historical, noncanonical scratch under
`.tmp_pdf_intake_benchmark/literature-materialization-20260730/`; they are not
required by the current corpus inventory or any claim.

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
rendered contact sheets were historical, noncanonical scratch under
`.tmp_pdf_intake_benchmark/literature-materialization-20260730/visual`; they are
not required by the current corpus inventory or any claim.

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

## Theory-neighbor intake — 2026-08-01

The four exact local objects below were matched to their arXiv v2, PMLR ICML
2025, or NeurIPS 2025 primary records. Their inclusion records literature
identity and interpretation boundaries; it does not promote a new CRPTO method
or empirical claim.

| Work / exact version | Canonical local PDF | Bytes | Pages | SHA-256 | Primary surface / local-use boundary | BibTeX key | Citation surface | Intake grade and disposition |
|---|---|---:|---:|---|---|---|---|---|
| Aldirawi, Li, and Guo, *Conformal Risk Control under Non-Monotone Losses: Theory and Finite-Sample Guarantees*, arXiv:2604.01502v2 | `Papers_tesis/supplement/Aldirawi Li Guo 2026 - Conformal Risk Control under Non-Monotone Losses - arXiv 2604.01502v2.pdf` | 1,040,554 | 39 | `d5d1f3b61ff2736c024a38c4fc657e25230d4ae75675aecc5d549715618a021c` | [arXiv v2](https://arxiv.org/abs/2604.01502v2); local research copy under the arXiv distribution terms | `aldirawi2026nonmonotone_crc` | Body | **A-boundary.** Retain as the exact finite-grid non-monotone CRC neighbor. Its bounded-loss, i.i.d./exchangeability, feasible-grid, and positive excess-term contract does not retroactively validate the inspected CRPTO archive. |
| Van der Laan and Alaa, *Generalized Venn and Venn-Abers Calibration with Applications in Conformal Prediction*, ICML 2025 | `Papers_tesis/supplement/Van der Laan Alaa 2025 - Generalized Venn and Venn-Abers Calibration - ICML.pdf` | 467,159 | 16 | `a3dca5857f3cf87813966aed2b1cfc9c936087281e42a65456ed0ba3cd7841bf` | [PMLR version of record](https://proceedings.mlr.press/v267/van-der-laan25a.html); CC BY 4.0 | `vanderlaan2025generalized_venn` | Body | **A-boundary.** Retain for the distinction between Venn's set-valued calibrated output and a downstream scalar embedding. Its guarantees do not transfer to the historical IVAP scalar, temporal transport, or funded-set selection. |
| Dabah and Tirer, *On Temperature Scaling and Conformal Prediction of Deep Classifiers*, ICML 2025 | `Papers_tesis/supplement/Dabah Tirer 2025 - Temperature Scaling and Conformal Prediction - ICML.pdf` | 7,216,227 | 33 | `e347b8bec219bc0605dc4d0164b7690f554f0c1b1eff7e759774ae47eec5e59c` | [PMLR version of record](https://proceedings.mlr.press/v267/dabah25a.html); CC BY 4.0 | `dabah2025temperature_conformal` | Body | **B-context.** Retain as direct evidence that probability calibration, conformal coverage, conditional coverage diagnostics, and set efficiency are distinct objectives. Its deep multiclass temperature-scaling results neither select Platt nor establish the same response for binary CRPTO. |
| Ovalle, Biegler, Grossmann, Laird, and Dulce Rubio, *Conformal Mixed-Integer Constraint Learning with Feasibility Guarantees*, NeurIPS 2025 | `Papers_tesis/supplement/Ovalle et al 2025 - Conformal Mixed-Integer Constraint Learning - NeurIPS.pdf` | 820,975 | 37 | `d0e20efd6b73118ad9747996c68dfcc72c01e32996950aeaf85a818d468b5d47` | [NeurIPS proceedings version](https://proceedings.neurips.cc/paper_files/paper/2025/hash/73b0f567e5471e73261853dc962c92bf-Abstract-Conference.html); official open proceedings/local research copy | `ovalle2025cmicl` | Body | **A-boundary.** Retain as a close conformal-to-MIP construction. Its feasibility result uses a set-native learned-constraint formulation plus an explicit conditional-independence assumption; neither ingredient is supplied by CRPTO's scalar objective coefficient. |

### Parser and text-layer QA — 2026-08-01

All four objects are born-digital and unencrypted. PyPDF 6.14.2 found zero
empty pages and zero pages with fewer than 200 extracted characters. Median
text-layer characters per page were 1,772 for Aldirawi--Li--Guo, 4,744.5 for
Van der Laan--Alaa, 2,490 for Dabah--Tirer, and 3,410 for Ovalle et al.

Docling 2.110.0 was the primary structural parser. The standard pipeline ran
with OCR and all enrichment models disabled, table extraction enabled, and
placeholder image export. It processed the 125 pages in 194.362 seconds (1.555
seconds per page) without a document failure or parser warning. Markdown and
JSON outputs are noncanonical scratch under
`.tmp_pdf_intake_benchmark/literature-intake-20260801/docling/`.

| Object | Markdown bytes | JSON bytes | Section headings | Formula items | Tables | Pictures | Parser warning |
|---|---:|---:|---:|---:|---:|---:|---|
| Aldirawi--Li--Guo v2 | 75,028 | 792,769 | 33 | 161 | 3 | 6 | None |
| Van der Laan--Alaa | 72,875 | 643,249 | 30 | 51 | 2 | 1 | None |
| Dabah--Tirer | 102,831 | 1,780,858 | 55 | 82 | 10 | 19 | None |
| Ovalle et al. | 122,000 | 1,123,599 | 57 | 42 | 11 | 16 | None |

### Manual visual QA — 2026-08-01

Poppler renders were compared against the all-page text extraction and Docling
structure. Contact sheets are noncanonical scratch under
`.tmp_pdf_intake_benchmark/literature-intake-20260801/visual/`.

| Object | Pages visually checked | Objects checked | Result |
|---|---|---|---|
| Aldirawi--Li--Guo v2 | 1, 7, 8, 21 | arXiv v2 identity; Theorem 1; excess-term table and interpretation; importance-weighted distribution-shift proposition | Identity, bounded/i.i.d./finite-grid assumptions, formulas, table, and covariate-shift qualification are legible and agree with extraction. |
| Van der Laan--Alaa | 1, 4, 7, 8 | Proceedings identity; Theorems 3.1, 3.2, 4.1, and 4.2; conformal applications; Table 1 | The set-valued calibration construction, finite-sample marginal statements, formulas, and reported coverage/efficiency table are legible and agree with extraction. |
| Dabah--Tirer | 1, 3, 7, 12 | Proceedings identity; marginal-versus-conditional coverage distinction; Theorem 4.1 and Proposition 4.3; proof page | The coverage distinction, temperature-dependent cumulative-softmax results, and proof equations are legible and agree with extraction. |
| Ovalle et al. | 1, 5, 6, 17 | Proceedings identity; Theorem 3.1; Assumption 4.1 and Theorem 4.1; Mondrian theorem and main proof | The set-native MIP formulation, conditional-independence assumption, group-conditional statement, and proof are legible and agree with extraction. Poppler emitted missing-display-font warnings for `Symbol` and `ArialUnicode`, but the inspected formulas and glyphs showed no visible corruption. |

## Bibliography and use boundary

`paper/references.bib` now pins Zhao and Zhou--Zhu to their exact v3 URLs and
DOIs, contains `wei2024adjustability`, and adds exact proceedings records for
`zhao2021decisioncalibration` and `im2025spor`. Existing keys for Lützow and
Shekhar--Howard already pin v1. The new watchlist keys are
`caunhye2026smartptro`, `guo2026lpas`, and `ziliaskopoulos2026dva`; their
presence does not by itself authorize a manuscript claim. The
weighted-conformal citation `tibshirani2019covshift` was already present and
was not duplicated.

The 2026-08-01 exact keys are `aldirawi2026nonmonotone_crc`,
`vanderlaan2025generalized_venn`, `dabah2025temperature_conformal`, and
`ovalle2025cmicl`. The master remains `paper/references.bib`. Deterministic
active and reserve views plus their complete, disjoint partition receipt are
generated by `scripts/build_ijds_bibliography_views.py`; the views are never
edited as independent bibliographies.

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
