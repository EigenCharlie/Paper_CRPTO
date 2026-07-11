# Final Two-Pass IJDS Audit - 2026-07-10

## Disposition

**Scientific status: GO for the current single-paper claim.** The active paper
is no longer the positive-return compact-v7 paper. It is a maturity-safe,
baseline-aware falsification study showing that marginal conformal coverage,
score conservatism, and decision stringency are different objects.

**ScholarOne upload status: conditional GO.** The scientific, computational,
anonymous manuscript, and supplement surfaces are complete. Upload still
requires the author to supply the current affiliation, state the ORCID or
confirm that none exists, and transfer the prepared data/code responses into
the publisher's official form.

## What the Original Headline Lost and Why

The compact-v7 replay funded 308 loans and reported a realized return of
$179,327.59, weighted default 0.039375, miscoverage 0.036875, and endpoint
0.258051. Those values are preserved as immutable forensic provenance, not
active evidence. The result could not support an IJDS submission because:

1. candidate membership retained only resolved outcomes, about 23.87% of the
   relevant 2018--2020 universe;
2. the declared conformal fitting window used later November--December labels;
3. the optimized economic expression differed from the evaluated payoff;
4. one pooled menu mixed future originations, maturity and censoring;
5. the reported conformal group was not the fitted grouping object;
6. the concentration interpretation confused purpose exposure with a
   loan-level bound; and
7. the Markov certificate was too weak to identify the claimed decision
   guarantee.

No editorial polish can repair those estimand and chronology defects. Restoring
their headline numbers would make the current paper longer but less defensible.

## What Was Recovered

The reconstruction retained the useful intellectual structure rather than the
invalid positive result:

- the end-to-end prediction-to-allocation decision problem;
- calibrated PD as an input to a transparent monthly linear program;
- the distinction between candidate, exposure-weighted, and funded metrics;
- the original concern that optimizer selection can break the interpretation
  of population predictive diagnostics;
- coherent economic comparison under a declared standardized payoff;
- temporal ordering, external-literature positioning, implementation detail,
  managerial implications, and reproducibility discipline; and
- historical A1--A40 artifacts as regression and forensic evidence only.

The paper recovered four exact results that are supportable without pretending
to have a new selected-set theorem: same-threshold feasible-set nesting,
binary-outcome miscoverage geometry, sharp unresolved-outcome bounds, and the
candidate-to-funded selection-transport identity.

## Active Numerical Claim

The active P1 parent uses a 540,121-loan status-independent 36-month universe,
fits and selects through 2012, and evaluates 15 fresh monthly $1M decisions from
April 2016 through June 2017. Its score is
`q=0.75p+0.25u` with `tau_q=0.17`; the interval targets 90% using exact
finite-sample ranks for the binary snapshot outcome.

- conformal-fit coverage: 0.900448;
- all-candidate primary OOT coverage: [0.854923, 0.879692];
- unresolved primary candidates: 11,386;
- same-threshold point-PD cap slack: 0.054242;
- development-matched point-PD cap: 0.06831339893217318.

Against the loose same-numeric-cap point baseline, guardrail-minus-point
default is [-0.046275, -0.020093] and realized standardized payoff is
[-$322,703.79, -$58,040.34]. Proposition 1 and the observed slack show why that
comparison is mechanically favorable to the guardrail: the point cap is
nonbinding.

Against the C1 development-risk-matched point baseline, the conclusion reverses:

| Guardrail minus matched point PD | Sharp primary interval |
|---|---:|
| Realized standardized payoff | [-$506,587.03, -$295,967.17] |
| Weighted snapshot default | [0.034431, 0.056287] |
| Funded-set miscoverage | [0.027093, 0.046283] |

The selected-policy signs survive low/mean/high development matches and every
primary leave-one-month-out diagnostic. The complete nine-policy census has all
three adverse directions in 7/9 pairs, not 9/9. This is a post hoc historical
falsification and comparator audit, not a causal effect, confirmation, or new
policy winner.

## Pass 1: Statistical and Methodological Audit

An independent statistical pass found no remaining blocker in comparator
matching, common-outcome pairwise bounds, leave-one-month-out diagnostics,
family reporting, payoff decomposition, selection transport, or same-threshold
nesting. Its four requested refinements were implemented:

1. timing now says the comparator was tagged before the first successful
   persisted execution;
2. `exact 90%` was replaced by `90%-target using exact finite-sample ranks`;
3. transport language is explicitly algebraic/descriptive rather than causal;
4. the LGD result is labeled fixed-allocation and the $488,201.64 term is the
   resolved default-and-foregone-interest component; and
5. generic payoff-rate contrast bounds now normalize each policy's exposure,
   with an unequal-capital regression test.

The scientific boundary is therefore internally coherent: exact algebra is
claimed only for its declared objects, and empirical signs are reported with
sharp missing-outcome bounds rather than mislabeled confidence intervals.

## Pass 2: IJDS Editorial and Anonymity Audit

The independent editorial pass found that the science preserved all defensible
original material but identified three packaging blockers. They were resolved
as follows:

- Reviewer-facing sources and PDFs now replace public-searchable runs with P1
  and C1 and forbid exact tags, commits, SHA-256 values, DVC fingerprints,
  repository ownership, personal identifiers, and local paths.
- Exact provenance was moved to
  `paper/submission/EDITOR_ONLY_REPRODUCIBILITY_CROSSWALK.md`.
- A metadata-sanitized archive contract defines what may be sent during review.
- The data/code form has final copy-ready Option 4 and data-ethics responses.
- The cover letter and title page contain a factual GenAI disclosure naming
  OpenAI Codex and GPT-5.6 Sol and assigning full responsibility to the author.
- The body/supplement question-count mismatch was corrected to nine.

Affiliation and ORCID remain deliberately unresolved because they are personal
facts that cannot be inferred safely from stale public profiles.

## PDF and Package QA

- official IJDS PDF: 22 pages, references begin on page 19;
- browser-print body: 22 pages;
- online supplement: 21 pages;
- body: 12 tables and 4 figures;
- no blank pages, clipped content, overlapping tables, undefined citations, or
  undefined references;
- extracted text and PDF metadata contain no forbidden author identifiers,
  run/protocol tags, full commits, SHA-256 values, DVC fingerprints, or local
  paths; and
- the official abstract is under 300 words, the title is under 25 words, and
  seven keywords fall within IJDS's 1--10 range.

The final `just submission-check` is green: Ruff and formatting pass, Mypy
reports no issues in 254 source files, full-scope `ty` is clean, the complete
pytest suite passes with two expected skips, the historical manifest validates,
both Quarto surfaces render, and the official TeX is citation/reference clean.
`just drift-gate` reports a maximum absolute difference of zero for every
frozen prediction, interval endpoint, score-band edge, coverage cell, and floor
multiplier.

The final lockfile also closes all three high-severity Dependabot alerts visible
at freeze: Mistune's quadratic link-text parser issue is addressed by upgrading
3.2.1 to 3.3.3, and Soup Sieve's selector-parser denial-of-service and memory
exhaustion issues are addressed by upgrading 2.8.3 to 2.8.4. The complete
submission gate remains green with those versions installed.

An expanded `pip-audit` scan retains one documented, non-actionable finding:
`CVE-2025-69872` in `diskcache 5.6.3`, for which no patched version exists.
CRPTO never imports it directly; DVC brings it through `dvc-data`, and the
attack requires untrusted write access to the local DVC cache. The cache is
ignored, local to the single-author workstation, and not exposed by a service,
so the project records and accepts this residual risk until upstream provides a
fix rather than removing DVC reproducibility.

`dvc status --no-updates` still reports historical stage dependencies changed
by earlier refactors. This is expected and intentionally unresolved: clearing
that status would require reproducing manifest-protected stages, which this
audit neither authorizes nor performs. The two active P1/C1 experiment bundles
have separate exact DVC pointers and have already been pushed.

## IJDS Fit

The current paper is stronger for IJDS than the positive-return version because
it has one explicit data-models-decisions-implications chain:

- **Data:** a real, status-independent consumer-credit menu with unresolved
  outcomes retained;
- **Model/method:** calibrated PD, finite-sample binary conformal prediction,
  a transparent allocation LP, sharp bounds, and a comparator audit;
- **Decision:** monthly credit allocation with baseline stringency treated as
  part of the estimand; and
- **Implication:** marginal predictive coverage and copied numeric caps do not
  supply optimizer-selected validity or a fair baseline by themselves.

The negative result is not a retreat. It is the strongest claim the repaired
design identifies, and it yields a reusable audit sequence for decision-focused
data science.

## Stop Rule

Do not retune the PD model, conformal recipe, guardrail, dates, payoff, matching
rule, or family on 2016--2017 outcomes. Do not add a new 2017 confirmation,
survival variant, decision-calibrated model, external winner, or CRPTO v2 to
this manuscript. Reopen the method only if an IJDS reviewer requests a specific
test or a genuinely new estimand is locked before examining its outcomes.

The highest-value remaining work is administrative submission, not another
empirical run.
