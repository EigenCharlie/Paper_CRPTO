# IJDS Submission Roadmap - Target 2026-08-10

This roadmap keeps the CRPTO submission work aligned with INFORMS Journal on
Data Science rather than with a generic machine-learning or operations-research
paper. The target date is August 10, 2026. IJDS regular submissions are rolling;
the date is an internal quality gate, not an external deadline.

Official sources to recheck before freezing:

- Submission guidelines: <https://pubsonline.informs.org/page/ijds/submission-guidelines>
- Data and Code Disclosure Policy: <https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>
- Reviewer guidelines: <https://pubsonline.informs.org/page/ijds/reviewer-guidelines>
- LaTeX style files: <https://pubsonline.informs.org/authorportal/latex-style-files>

## Submission Thesis

CRPTO should be read as data science for decisions:

| IJDS component | CRPTO surface |
|---|---|
| Data | Static Lending Club OOT panel, plus Prosper and Freddie/Mendeley frozen external stress tests. |
| Models/algorithms | Calibrated PD, Mondrian conformal intervals, robust LP, exact funded-set audit. |
| Decision relevance | Funding a credit portfolio under budget, risk tolerance, and uncertainty. |
| Implications | Model-risk governance, reproducible auditability, robust-price interpretation, and limits of external transfer. |

## Work Plan

| Window | Goal | Required output |
|---|---|---|
| Jun 9-16 | Editorial contract | Body and supplement explicitly state data-model-decision-implication logic. |
| Jun 17-24 | Claim hardening | Every headline number maps to an artifact and a non-overclaim boundary. |
| Jun 25-Jul 2 | Related-work pressure test | Closest-work table reads as a novelty boundary, not a literature survey. |
| Jul 3-10 | Method and theorem audit | Exact funded-set certificate, weighted-validity assumption, and post-selection boundary are unambiguous. |
| Jul 11-17 | External replication polish | Prosper/Freddie remain evidence of recipe transfer, not new exact certificates. |
| Jul 18-24 | Figures and tables | Captions state takeaway; tables fit IJDS; figures remain readable in grayscale. |
| Jul 25-31 | Reproducibility package | Data/code disclosure plan, commands, hashes, DVC pointers, and raw-data instructions are ready. |
| Aug 1-5 | Official template | Body compiles in `informs4` with `dblanonrev`; current local build is 24 pages including references, with final ScholarOne proof still pending. |
| Aug 6-8 | Double-anonymous QA | Metadata, URLs, acknowledgements, local paths, and author signals are removed from reviewer-facing PDFs. |
| Aug 9-10 | Submission freeze | `just lint`, `just smoke`, `just validate-champion`, `just paper-submission-pdf`, and visual QA pass. |

## The 15 Improvement Tracks

| # | Track | Done definition |
|---:|---|---|
| 1 | Central methodological claim | Abstract, introduction, and conclusion describe CRPTO as an auditable conformal-robust decision certificate. |
| 2 | IJDS fit | The body visibly contains data, method, decision, and implication components. |
| 3 | Exact-certificate language | "Exact" is defined as funded-set accounting on frozen OOT outputs, with statistical assumptions stated separately. |
| 4 | Robust region | `45/45` is explained as the final evaluated robust region, not all candidate policies. |
| 5 | External datasets | Prosper/Freddie are frozen external economic replications, not new Lending Club champions. |
| 6 | Related work | The closest-work boundary distinguishes CRPTO from P2P OR, conformal credit scoring, conformal RO, DFL, and financial portfolios. |
| 7 | Figures | Main figures have single-sentence takeaways, readable axes, grayscale-safe contrast, and no unnecessary decorative elements. |
| 8 | Tables | Body tables are compact reviewer evidence; voluminous diagnostics stay in the supplement. |
| 9 | Supplement | A3--A34 are organized as a defense layer with scope caveats. |
| 10 | Reproducibility | Accepted-paper package has code, DVC pointers, manifest, raw-data instructions, and guardrail commands. |
| 11 | Double anonymity | Reviewer-facing body and supplement contain no author URLs, names, local paths, or private remotes. |
| 12 | Official IJDS template | `CRPTO_ijds_submission.tex` is synchronized with the QMD, compiles against the official files, and is rechecked after body edits. |
| 13 | Data/code form | Cover letter and disclosure text acknowledge IJDS accepted-paper reproducibility requirements. |
| 14 | Acceptance-risk audit | A short list of likely reviewer objections has body or supplement responses. |
| 15 | Freeze discipline | Protected champion/search stages are never rerun as routine paper reproduction. |

## Current Acceptance Risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| Perceived as applied pipeline | IJDS needs methodological data science, not just a case study. | Keep the decision-certificate framing central. |
| Overreading exact validity | Reviewers may object if "exact" sounds like universal conformal validity. | Define exact as funded-set accounting and state weighted validity separately. |
| External claims too strong | Prosper/Freddie are not new certificates. | Label them as economic replication and exhaustiveness audits. |
| Regret comparator confusion | SPO+ wins regret by design. | Present regret-auditability as a frontier with different governance outputs. |
| Template/page risk | Local HTML-print PDFs are not official. | Keep the `informs4` handoff build current and recheck the ScholarOne proof before submission. |
| Reproducibility policy | IJDS requires disclosure form at submission and archive workflow at acceptance. | Maintain `REPRODUCIBILITY_PACKAGE.md` and cover-letter language. |
