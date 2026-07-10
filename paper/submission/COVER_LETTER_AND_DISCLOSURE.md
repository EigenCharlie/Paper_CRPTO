# IJDS Cover Letter and Editor Disclosures

Editor-facing material only. Do not include this file in the double-anonymous
review packet.

## Cover Letter Draft

Dear Editors,

I submit "CRPTO: When Marginal Conformal Coverage Meets Maturity-Safe Credit
Portfolio Selection" for consideration at the *INFORMS Journal on Data
Science*.

The paper asks a decision-focused question: does marginal conformal coverage
continue to protect a portfolio after an optimizer selects and reweights the
candidate loans? CRPTO combines a calibrated probability-of-default model, an
exact 90% five-stratum split-conformal interval for the binary repayment
outcome, and a transparent monthly allocation LP. The empirical protocol is
designed around decision-time information. Its 540,121-loan universe is
independent of final status; statistical fitting and policy selection end in
2012; every month from April 2016 through June 2017 is solved as a separate
decision; and unresolved snapshot outcomes remain in the menu and receive
sharp bounds.

The result is deliberately not presented as a win-only story. Relative to a
matched point-PD allocation, the selected score `q=0.75p+0.25u` reduces the
exposure-weighted default rate by 2.01--4.63 percentage points, but lowers
standardized realized payoff by $58,040--$322,704 and increases funded-set
miscoverage by 0.88--2.99 percentage points. An exact transport identity shows
why: the default advantage comes from shifting capital toward the lowest score
stratum, while adaptive selection within strata drives the coverage failure.
The locked temporal comparison is itself informative: the guardrail led its
development point policy by $50,260 in realized standardized payoff even
though expected payoff was already $72,702 lower; primary payoff and
miscoverage then reverse direction without any retuning.

The contribution is therefore a maturity-safe audit of prediction-to-decision
validity, not a claim that marginal conformal coverage is a selected-set
guarantee. The paper aligns the optimized and evaluated payoff, retains
unresolved outcomes with sharp pairwise bounds, exposes temporal reversals, and
distinguishes binary-outcome coverage from confidence about latent PD. This
boundary is formalized through binary-interval geometry, sharp additive and
paired bounds, and an exact selection-transport identity. This combination of
data design, methodology, decision analysis, and practical
implication fits IJDS's focus on rigorous data science for decisions.

The experiment was executed from a clean tagged commit. Its versioned data and
model/result directories are tracked by DVC, an execution receipt hashes every
output, and an idempotent evidence builder regenerates the manuscript tables
and figures. The anonymous manuscript omits author-identifying repository
links. At acceptance, I will release the code, environment lock, manuscript
sources, artifact metadata, DVC pointers, and data-acquisition instructions,
subject to source redistribution terms.

This manuscript is original, is not under review elsewhere, and has one author.
I declare no conflict of interest and no specific funding for this work.

Thank you for your consideration.

Sincerely,

Carlos Alfredo Vergara Rojas

## Required Editor-Only Statements

- **Originality:** The manuscript is original and is not under simultaneous
  review elsewhere.
- **Authorship:** Carlos Alfredo Vergara Rojas is the sole author and accepts
  responsibility for the work.
- **Funding:** No specific funding supported this work.
- **Conflicts:** The author declares no conflicts of interest.
- **Data/code:** Complete the official IJDS Data and Code Disclosure Form. Use
  the accepted-paper release plan in `REPRODUCIBILITY_PACKAGE.md`.
- **Generative AI assistance:** Disclose any journal-required details about the
  use of coding or language-assistance tools. The author verified the code,
  calculations, citations, prose, and final claims and remains solely
  responsible; no AI system is an author.

## Anonymous-Packet Boundary

- Reviewer-facing files: anonymous official manuscript PDF and anonymous
  supplement PDF only, plus any anonymized reproducibility archive explicitly
  requested by the editor.
- Editor/system files: cover letter, title page, disclosure form, author
  identity, affiliation, email, ORCID, and non-anonymous repository details.
- Do not expose local paths, credentials, DVC remote secrets, personal URLs, or
  repository ownership in reviewer-facing files.
