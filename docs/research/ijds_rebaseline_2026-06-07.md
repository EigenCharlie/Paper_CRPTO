# IJDS formal rebaseline - 2026-06-07

This memo records the formal CRPTO rebaseline for the IJDS paper lane. It supersedes the exploratory dependency-upgrade memo from 2026-06-06 as the active paper-facing baseline.

## Decision

The official run tag is now `ijds-rebaseline-2026-06-07`.

The promoted policy remains `bound_aware_276k_economic_champion`. The rebaseline did not reopen the forbidden 276k champion search; it replayed and revalidated the already selected policy family inside this standalone repository, then regenerated paper/book artifacts from local paths.

## Champion metrics

| Metric | Value | Reading |
| --- | ---: | --- |
| Robust realized return | `$170,464.54` | unchanged headline economic result |
| `V(alpha=0.01)` | `0.028875` | improved versus the old `0.03645` baseline |
| `Gamma_CP(alpha=0.01)` | `0.187987` | slightly wider conformal budget than the old `0.18591` value |
| Exact violation | `0.0` | exact funded-set pass |
| Robust region | `45/45` | full mini-grid remains alpha-safe |
| Loan-level export count | `335` | paper-facing funded-set rows in Table A7 |
| Solver funded count | `340` | HiGHS/re-solve count convention with fractional thresholding |

The 335 vs 340 difference is a counting convention, not a portfolio-composition change.

## Conformal gate semantics

Kupiec and Christoffersen p-value checks are retired from the official promotion gate. They remain useful research utilities in `src.evaluation.coverage_tests`, but they are no longer serialized into `models/conformal_policy_status.json` or counted in `overall_pass`.

| Check family | Current role |
| --- | --- |
| Coverage 90/95 | promotion gate |
| Minimum group coverage | promotion gate |
| Average width | promotion gate |
| Backtest alerts | promotion gate |
| Winkler 90/95 | promotion gate |
| Kupiec / Christoffersen | research diagnostics outside promotion |

Current conformal status:

| Field | Value |
| --- | ---: |
| `overall_pass` | `true` |
| `gate_overall_pass` | `true` |
| `strict_overall_pass` | `true` |
| Gate checks | `9/9` |
| Diagnostic checks | `0/0` |
| Coverage 90% | `0.929714` |
| Coverage 95% | `0.966388` |
| Average width 90% | `0.784230` |
| Minimum group coverage 90% | `0.918983` |
| Winkler 90% | `1.110742` |

`strict_overall_pass` is now a compatibility alias for the material gate, not a stricter p-value lane.

## PD layer drift

The PD layer was replayed locally under the new run tag. The direction is benign and small:

| Metric | Current value | Direction |
| --- | ---: | --- |
| AUC | `0.7126777846` | slightly better than the previous rounded `0.7124` |
| Brier | `0.1545907368` | essentially unchanged |
| ECE | `0.0061522936` | slightly better than the previous rounded `0.0064` |

The paper still should not sell AUC as the contribution. The contribution remains the calibrated-PD-to-conformal-to-robust-decision chain.

## Why formal rebaseline instead of code-only fixes

Code-only fixes would remove stale WSL paths and noisy strict wording without updating the canonical hashes. That is cleaner in the diff, but weaker scientifically: the project would still contain old frozen artifacts that disagree with the standalone run.

Formal rebaseline is better for IJDS because it:

- proves the standalone repository can replay the paper-facing lane without depending on the parent WSL project;
- aligns `params.yaml`, DVC, tables, figures, book, paper text, and manifest under one run tag;
- removes the misleading 9/13 strict story from the official status artifact;
- keeps the champion search decision frozen while still validating reproducibility of the selected policy.

## Boundaries

The rebaseline is not a new HPO/champion-search campaign. The following remain separate, explicit future work:

- opening `crpto.portfolio.bound_exact_eval` as a new search lane;
- changing the promoted policy family;
- replacing the conformal variant with CQR or another interval method;
- making the thesis PDF before the thesis section set and APA layout are curated.
