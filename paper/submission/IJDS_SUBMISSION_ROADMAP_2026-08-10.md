# IJDS Submission Roadmap - Target 2026-08-10

The date is an internal quality gate; IJDS submissions are rolling.

Official sources to recheck in the submission week:

- <https://pubsonline.informs.org/page/ijds/submission-guidelines>
- <https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>
- <https://pubsonline.informs.org/page/ijds/reviewer-guidelines>
- <https://pubsonline.informs.org/authorportal/latex-style-files>

## Submission Thesis

| IJDS dimension | CRPTO answer |
|---|---|
| Data | Temporal Lending Club panel with conformal fit, November selection, December audit, and OOT evaluation. |
| Method | Exact 90% conformal replay, deterministic endpoint cap, and one midpoint portfolio guardrail. |
| Decision | Allocate `$1M` under capital, concentration, and effective-PD constraints. |
| Evidence | Split nine-cell selector/audit, matched point-PD decision, temporal reversals, and month-cluster bootstrap. |
| Implication | An inspectable price of uncertainty, including cases where the static guardrail should be rejected. |

## Completed Scientific Refactor

- Retired approximate cross-alpha headline values.
- Replayed conformal quantiles exactly at every sensitivity alpha.
- Selected the conventional 90% reference level; documented endpoint
  saturation at tighter levels.
- Replaced nonlinear/tail policy families with `q=(p+u)/2`.
- Separated point-PD economics from conformal feasibility.
- Reduced policy selection to a round-number `3x3` calibration grid.
- Replaced the Markov-based selector screen with deterministic `B_u<=0.28` and
  documented the exact cap-stability interval.
- Isolated outcomes from a 12-column selector frame; November selects and an
  outcome-free December replay checks policy identity.
- Added the independent December decision audit, including the funded-set
  coverage miss, and a 31-month cluster bootstrap.
- Added matched point-PD and 75% blend comparators.
- Promoted temporal reversals and limitations to the body.
- Rebuilt A35--A40 and active claim-sync tests.

## Remaining Submission Work

| Window | Deliverable | Exit condition |
|---|---|---|
| Jul 9--12 | Code and claim gates | Ruff, mypy, ty, focused tests, smoke, manifest, and drift gate green. |
| Jul 12--18 | PDF editorial QA | Official body and supplement render; no undefined citations; body within 25-page rule; visual QA complete. |
| Jul 18--24 | Reproducibility archive | Sanitized commands, source notes, run tags, hashes, and A35--A40 bundle staged. |
| Jul 25--31 | Anonymous package | Body, supplement, title page, cover letter, and disclosure form separated correctly. |
| Aug 1--8 | Cold review | Read only the generated PDFs; fix clarity, table, and citation defects. |
| Aug 9--10 | ScholarOne freeze | Upload, inspect ScholarOne proof, and submit only after go/no-go checklist. |

## Acceptance Risks

| Risk | Mitigation in current draft |
|---|---|
| Applied pipeline rather than method | One explicit objective/constraint contract and exact selector protocol. |
| Broad binary conformal intervals | A35 reports width and endpoint saturation; no 99% headline. |
| Adaptive funded-set validity | December directly demonstrates the coverage miss; deterministic accounting is separated from conditional Markov language. |
| Historical OOT reuse | "Retrospective lockbox replay" stated in abstract, design, limitations, supplement, and cover letter. |
| Baseline cherry-picking | Same candidates, budget, concentration, LGD, solver, and `tau`; temporal failures are shown. |
| Too many methods | A1--A34 demoted to diagnostics; A35--A40 support one midpoint policy. |
| Reproducibility mistaken for novelty | Decision method and managerial trade-off lead; tooling supports auditability. |
| Page and template risk | Official `informs4` build and visual QA are blocking gates. |

## Freeze Rule

After the scientific and PDF gates pass, do not reopen the policy for marginal
OOT gains. Reopen only for a concrete reviewer request, a simpler calibration-
only rule that matches the active result, or a formally stronger prospective or
selection-valid protocol.
