# IJDS Cover Letter and Editor Disclosures

Editor-facing material only. Do not include this file in the double-anonymous
review packet.

## Cover Letter Draft

Dear Editors,

I submit "CRPTO: Auditing Comparator Stringency in Maturity-Safe Conformal
Credit Portfolios" for consideration at the *INFORMS Journal on Data Science*.

The paper asks two linked decision-focused questions. Does marginal conformal
coverage protect a portfolio after an optimizer selects and reweights loans?
And does applying the same numeric risk cap to a conformal score and point PD
create a fair baseline? CRPTO combines a calibrated probability-of-default
model, a 90%-target five-stratum split-conformal interval using the exact
finite-sample rank for the binary repayment outcome, and a transparent monthly
allocation LP.

The empirical protocol is designed around decision-time information. Its
540,121-loan universe is independent of final status; statistical fitting and
guardrail selection end in 2012; every month from April 2016 through June 2017
is a separate decision; optimized and evaluated payoffs agree; and unresolved
snapshot outcomes remain in the menu and receive sharp common-outcome bounds.
All-candidate coverage nevertheless deteriorates from 0.900448 at conformal
fit to [0.854923, 0.879692] OOT.

The main methodological finding concerns baseline design. Because the
guardrail score satisfies `q>=p`, reusing `tau=0.17` nests its feasible set
inside a looser point-PD set. The point cap is nonbinding and leaves 0.054242
aggregate slack. Under that baseline, the guardrail appears to lower default.
A separately tagged comparator audit instead fixes point-PD tolerance at the
guardrail's mean development-funded PD, 0.068313. The conclusion reverses:
guardrail-minus-point realized standardized payoff is
[-$506,587.03, -$295,967.17], default is [0.034431, 0.056287], and funded-set
miscoverage is [0.027093, 0.046283]. These signs survive the closed
low/mean/high development matches and all 15 leave-one-month-out checks.

The paper is deliberately transparent about the boundary of that evidence.
The comparator audit was designed after the maturity-safe parent result was
known, then committed and tagged before the first successful persisted
execution. It is post hoc falsification, not preregistered confirmation. A
complete nine-policy census
finds all three adverse guardrail directions in seven of nine pairs, not nine
of nine, and no OOT policy is promoted. The selected directions are stable
under the locked diagnostics; the family result is heterogeneous.

The contribution is therefore an auditable method for separating predictive
validity, score conservatism, and decision stringency. Its comparator audit
checks score ordering, cap binding, development-only alignment, and closed
threshold, month, and family diagnostics. It combines that sequence with a
maturity-safe decision protocol, coherent payoff, sharp unresolved-outcome
bounds, and a selection-transport identity.
This data-models-decisions-implications chain, including the negative result,
fits IJDS's focus on rigorous data science for decisions.

Both evidence layers were executed from clean tagged commits. Their versioned
data and model/result directories are tracked by DVC; execution receipts hash
the summaries and artifacts; and deterministic builders regenerate the paper
tables and figures. The comparator builder reproduces 38 publication-output
hashes exactly on consecutive builds. The anonymous manuscript omits
author-identifying links.
At acceptance, I will release the code, environment lock, manuscript sources,
artifact metadata, DVC pointers, and data-acquisition instructions, subject to
source redistribution terms.

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
- **Data/code:** Select Option 4 on the official IJDS Data and Code Disclosure
  Form. All code can be released, but the loan-level source and processed data
  cannot be publicly redistributed unless their governing terms are confirmed.
  Use the exact responses in `DATA_CODE_DISCLOSURE_FORM_DRAFT.md` and the
  accepted-paper release plan in `REPRODUCIBILITY_PACKAGE.md`.
- **Post hoc analysis:** The comparator-stringency audit was designed after the
  parent result was inspected and is labeled post hoc throughout all files.
- **Generative AI assistance:** OpenAI Codex, including GPT-5.6 Sol, was used
  for code review and refactoring, test scaffolding, literature triage and
  summarization, consistency checks, and language editing. It was not treated
  as evidence and is not an author. The sole author inspected the primary
  sources, executed and validated the analyses, verified citations, numbers,
  code, prose, and claims, and accepts full responsibility for the work.

## Anonymous-Packet Boundary

- Reviewer-facing files: anonymous official manuscript PDF and anonymous
  supplement PDF only, plus an anonymized reproducibility archive if requested.
- Editor/system files: cover letter, title page, disclosure form, author
  identity, affiliation, email, ORCID, and non-anonymous repository details.
- Do not expose local paths, credentials, DVC secrets, personal URLs, or
  repository ownership in reviewer-facing files.
