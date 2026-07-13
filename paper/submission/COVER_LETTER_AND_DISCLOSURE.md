# IJDS Cover Letter and Editor Disclosures

Editor-facing template only. At the eventual submission freeze, create the
ignored `COVER_LETTER_PRIVATE.md`, add the author identity, and upload it only
to the editor-facing ScholarOne slot.

## Cover Letter Draft

Dear Editors,

I submit "CRPTO: Binary Conformal Geometry and Comparator Identification in
Portfolio Optimization" for consideration at the *INFORMS Journal on Data
Science*.

The paper examines a data-models-decisions failure mode: a predictive guarantee
and a numerical risk cap need not retain their meaning after a score enters an
optimizer. CRPTO combines a Platt-scaled default score, a 90%-target
absolute-residual interval for a binary outcome, and a monthly credit-allocation
linear program. Candidate membership is status independent, unresolved loans
remain in every menu, allocations are persisted before outcomes are joined,
and realized comparisons use sharp common-outcome bounds.

The predictive audit reports every eligible consecutive six-month residual
window from January 2012 through January 2013. For 376,890 primary OOT
candidates, including 11,551 unresolved outcomes, every CatBoost five-stratum
coverage upper bound is below 0.90. An independently calibrated logistic
control is closer but also fails in all eight windows; its maximum upper bound
is 0.8957. The failure therefore survives both declared learners, although its
magnitude is learner-dependent.

The complete residual path exposes a discrete mechanism. In one CatBoost score
stratum, fit prevalence moves from 0.1017 to 0.0971 between the seventh and
eighth windows, crossing the nominal alpha of 0.10. Its residual quantile
changes from 0.8884 to 0.1118 and its OOT mean interval width from 0.9843 to
0.2076. The paper formalizes the corresponding constant-score binary phase
transition while keeping its conditions separate from the varying-score
empirical diagnostic.

The decision audit treats the comparator as part of the estimand. We prove
same-cap nesting and a contemporaneous funded-score feasibility theorem, then
enumerate the exact HiGHS basis frontier for the point-score cap. All 216
broad-stress policy-window-metric envelopes cross zero. Within the narrower
development-admissible support, default remains unidentified in all 72 cells,
and the payoff and miscoverage directions that survive windows 1--7 disappear
in window 8. No learner, window, policy, cap, or comparator is promoted.

The contribution is therefore not a winning credit policy. It is a
reproducible identification audit of binary conformal geometry, temporal
transport, and comparator support in a frozen predict-then-optimize system.
This data-models-decisions-implications chain fits IJDS's focus on rigorous data
science for decisions while making the negative result operationally useful:
coverage does not transport in the declared archive, and realized portfolio
direction cannot be interpreted without an outcome-free comparator support.

The archive was inspected during earlier project iterations. The active
protocol was committed before its complete run, but the study is retrospective
rather than prospective, confirmatory, or preregistered. It makes no causal,
selected-set-validity, fair-lending, or deployment claim. The constant-score
theory is not presented as proof for empirical varying-score strata, and the
factorial simulation's nonbinding portfolio component is disclosed as a
negative diagnostic rather than used as evidence.

The review package has a verified outcome-free freeze, a separate evaluation
join, four immutable DVC pointers, a deterministic evidence builder, and
claim-sync tests spanning the manuscript, supplement, evidence manifest, and
generated INFORMS TeX. At acceptance, I will release code, environment lock,
manuscript sources, artifact metadata, DVC pointers, and raw-data acquisition
instructions, subject to source redistribution terms.

This manuscript is original, is not under review elsewhere, and has one author.
I declare no conflict of interest and no specific funding for this work.

Thank you for your consideration.

Sincerely,

**Author name required in the private ScholarOne copy.**

## Required Editor-Only Statements

- **Originality:** The manuscript is original and is not under simultaneous
  review elsewhere.
- **Authorship:** The sole author accepts responsibility for the work. Insert
  the full legal name only in the private ScholarOne copy.
- **Funding:** No specific funding supported this work.
- **Conflicts:** The author declares no conflicts of interest.
- **Data/code:** Use the response selected in the current official IJDS form.
  Code can be released; loan-level redistribution depends on the governing
  source terms. Reconfirm the form and policy during submission week.
- **Retrospective boundary:** The archive was previously inspected. The active
  protocol is code locked but is not preregistered, prospective, or confirmatory.
- **Generative AI assistance:** OpenAI Codex, including GPT-5.6 Sol, assisted
  with code review and refactoring, test scaffolding, literature triage and
  summarization, consistency checks, and language editing. It was not treated
  as evidence or an author. The sole author inspected the primary sources,
  executed and validated the analyses, verified citations, numbers, code,
  prose, and claims, and accepts full responsibility for the work.

## Anonymous-Packet Boundary

Reviewer-facing files contain only the anonymous official manuscript,
anonymous supplement, and a sanitized archive if requested. Identity,
affiliation, email, ORCID, repository ownership, exact tags/hashes, local paths,
credentials, and DVC remotes remain editor-only.
