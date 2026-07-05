# paper-crpto Publication Strategy - 2026-05-12

> Historical note, 2026-07-04: this memo predates the pool93 promotion. Use
> `docs/research/active_claims_2026-07-04.md` and
> `docs/SCOPE_AND_GOVERNANCE.md` for active paper-facing metrics. Mentions of
> `45/45` and the earlier champion are retained as venue-strategy provenance,
> not as the current IJDS headline.

## Decision

Write the first submission for **INFORMS Journal on Data Science (IJDS)** and
keep **European Journal of Operational Research (EJOR)** as the primary pivot.

The working rule is:

- primary venue: IJDS;
- secondary venue: EJOR;
- stretch venues: INFORMS Journal on Optimization, Management Science and
  Operations Research;
- applied fallbacks: Decision Support Systems and Expert Systems with
  Applications.

This decision is encoded in `configs/crpto_publication_targets.yaml`.

## Why IJDS First

IJDS is the best first target because paper-crpto is not just a credit-risk
case study. The contribution is a reproducible decision-focused data science
pipeline: calibrated PD, conformal uncertainty, robust optimization,
artifact-backed tables, DVC lineage and a public companion.

Official IJDS guidance is unusually aligned with the project:

- initial submissions should fit a 25-page IJDS-style body, excluding
  references and appendices;
- appendices and lengthy robustness material should be online supplements;
- submissions use the IJDS LaTeX template;
- IJDS uses double-anonymous review for submissions on or after
  January 1, 2025;
- data/code disclosure and reproducibility are explicit parts of the process.

Sources:

- IJDS submission guidelines:
  <https://pubsonline.informs.org/page/ijds/submission-guidelines>
- IJDS data/code disclosure policy:
  <https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>

## Why EJOR Second

EJOR is the strongest second target if the paper reads more as operational
research than data science. Its scope is explicitly about both OR methodology
and decision-making practice. CRPTO can fit as an innovative OR application or
theory/methodology paper if we emphasize conformal uncertainty sets, robust
portfolio decisions, price of robustness and the active finite-grid pool93
return-bound frontier.

Source:

- EJOR journal page and aims/scope:
  <https://www.sciencedirect.com/journal/european-journal-of-operational-research>

## What This Means For The Manuscript

The first paper draft should be written as:

- title: `CRPTO: Conformal Robust Predict-Then-Optimize for Auditable Credit Portfolio Decisions`;
- body: 25-page IJDS-style manuscript;
- supplement: A3--A39, proofs, extended tables, reproducibility,
  MRM/fairness and external replication;
- review mode: anonymous by default;
- companion: GitHub/DVC/DagsHub/MLflow after the anonymity policy is handled.

The short paper should keep only the strongest body material:

- problem and contribution;
- PD calibration summary;
- Mondrian conformal layer;
- robust portfolio formulation;
- Markov bound and conditional tightening caveat;
- pool93 body metrics and A35 finite-grid frontier;
- A36--A39 selected-allocation audits;
- regret-auditability frontier with one concise SPO+/DFL comparison;
- data/code reproducibility statement.

Everything else lives in the supplement or book.

## Submission Scope Lock

The current paper is centered on the promoted pool93 finite-grid body claim,
with the frozen upstream CRPTO chain retained as provenance and the declared
return floor. P2/P3 ideas are no longer treated as a blanket exclusion when
they use frozen artifacts and do not change the promoted policy: OCE/CVaR as a
diagnostic, satisficing as margin evidence, regret-auditability as the
SPO+/CRPTO comparator, and dependence-aware theory as a caveated supplement
proposition.

In scope for the current paper:

- promoted pool93 finite-grid return-bound frontier;
- frozen upstream CRPTO chain as provenance and return floor;
- calibrated PD -> Mondrian conformal intervals -> robust portfolio decision;
- exact alpha-safe funded-set validation and A35 finite-grid frontier;
- A3--A39 as supplement evidence;
- regret-auditability frontier in the body;
- OCE/CVaR tail-risk diagnostics and robust satisficing margins in the
  supplement;
- cluster-aware dependence caveat/proposition with Markov retained as the main
  distribution-free bound;
- external economic replication on Prosper and Freddie/Mendeley as A25--A34,
  without reopening the Lending Club body claim;
- reproducibility via Quarto, DVC, DagsHub/MLflow and guardrail tests.

Out of scope for the current paper:

- OCE/CVaR as the optimized objective or constraint;
- multi-distribution robust conformal prediction as the promoted layer;
- online conformal recalibration or online DFL;
- SPO+ + conformal hybrid training;
- prospective/live multidataset validation beyond the static Prosper/Freddie
  replications;
- causal/CATE CRPTO;
- multi-period portfolio rebalancing;
- field trial, production monitoring dashboard, or open-source package
  extraction.

If any of those become central, the project moves to a new run/protocol rather
than quietly expanding the current manuscript.

## Template Policy

Do not optimize the final PDF template before the venue is fixed. The repo now
uses Quarto skeletons for writing:

- `paper/CRPTO_ijds.qmd`: IJDS first-submission body;
- `paper/supplement_ijds.qmd`: IJDS online supplement;
- `paper/CRPTO.qmd`: generic landing manuscript stub.

When the text is ready for submission, convert or render the IJDS `.qmd` into
the official IJDS LaTeX template rather than inventing a custom journal style.
The author portal/Overleaf template uses `\documentclass[ijds,dblanonrev]{informs4}`
for double-anonymous review, so the conversion target is explicit.

## Pivot Rules

Stay with IJDS if the paper's strongest claim is:

- reproducible decision-focused data science;
- auditability and code/data disclosure;
- a complete pipeline from prediction to decision.

Pivot to EJOR if the paper's strongest claim becomes:

- robust optimization methodology;
- operational decision practice;
- applied OR evidence and sensitivity analysis.

Pivot to INFORMS Journal on Optimization only if a stronger optimization or
dependence-aware theory contribution is added.

Treat Management Science and Operations Research as stretch targets, not the
first submission path, unless the manuscript gains broader managerial or OR
theory significance beyond the current Lending Club study.

## Anonymity And Public Repo

The repository is public, but IJDS requires double-anonymous manuscripts. Before
submission:

- remove author names from the manuscript and supplement;
- avoid first-person claims that reveal ownership of the public repo;
- decide whether the GitHub/DagsHub companion is disclosed in the cover letter,
  supplement, or only after review according to journal policy;
- create a release tag for the reproducibility bundle once anonymity handling is
  settled.

## Current Implementation

- Config: `configs/crpto_publication_targets.yaml`.
- Body skeleton: `paper/CRPTO_ijds.qmd`.
- Supplement skeleton: `paper/supplement_ijds.qmd`.
- Book linkage: `book/chapters/06-blueprint-manuscrito.qmd` and
  `book/chapters/14-release.qmd`.
- Commands:
  - `just paper-ijds`
  - `just paper-ijds-supplement`
  - `just paper-submission`
