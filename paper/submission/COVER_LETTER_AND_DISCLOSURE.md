# IJDS Cover Letter and Editor Disclosures

Editor-facing template only. At freeze, create `COVER_LETTER_PRIVATE.md`
locally, insert the author identity, and upload it only to the editor-facing
ScholarOne slot. The private filename is ignored by Git.

## Cover Letter Draft

Dear Editors,

I submit "CRPTO: Auditing Temporal Transport and Comparator Choice in
Conformal Portfolios" for consideration at the *INFORMS Journal on Data
Science*.

The paper studies a decision-focused failure mode: a predictive guarantee and
a numerical risk cap need not retain their meaning after a score enters an
optimizer. CRPTO combines a Platt-scaled default score, a 90%-target
binary-outcome conformal residual interval, and a monthly credit-allocation
linear program. Its common OOT panel contains 465,117 status-independent loans;
score strata are fixed before residual fitting; unresolved outcomes remain in
every menu; and outcomes are joined only after allocations are frozen.

Two locked residual windows meet the target in their fit blocks: 0.900388 on
14,948 observable 2012H1 labels and 0.900174 on 33,909 labels from July
2012--January 2013. Their five-stratum all-candidate OOT bounds are respectively
[0.854714, 0.879647] and [0.845072, 0.870973] over 15 monthly decisions from
April 2016 through June 2017. Every upper endpoint remains below 0.90 across
four fixed taxonomies and a closed late-window reporting-lag grid. The failure
occurs before portfolio selection.

The decision audit evaluates all nine co-primary guardrails. A copied numeric
cap uses a weaker point-score feasible set and makes every guardrail appear to
improve realized default in both windows. Nesting predicts only the feasible
set and optimized plug-in objective ordering; the realized signs are empirical.
An outcome-free comparator instead matches each funded point-score moment. The
C2 payoff census changes from 7 of 9 robust losses in the early window to 5 of
9 in the late window; default is higher for 1 of 9 and funded-set miscoverage
for 8 of 9 in both. All 27 policy-metric envelopes cross zero in each of three
scopes, including the development-supported point-cap range 0.0600--0.0825.
Each residual window's 180-cell seed--concentration census contains signs in
both directions; no cell or window is promoted.

The contribution is therefore not a winning credit policy. It is a
reproducible audit design that separates temporal coverage transport,
comparator stringency, unresolved outcomes, and binding operational
constraints. The empirical conclusion is deliberately negative: temporal
candidate-coverage failure survives the declared timing checks, whereas
portfolio direction is not invariant to residual timing, comparator scope, or
binding constraints. This data-models-decisions-implications chain fits IJDS's
focus on rigorous data science for decisions.

The locked protocol required the superiority submission to stop if neither
declared 9-of-9 result survived. That gate failed. The present negative audit
framing was developed after observing the stop and is submitted as an
explicitly retrospective secondary interpretation, not as a prespecified
fallback or confirmatory success.

The archive was inspected during earlier project iterations. The current code
and outcome-free allocation protocol were locked before the complete
evaluation, but the study is retrospective rather than prospective or
preregistered. The review package records this boundary, provides sharp
partial-identification bounds, and makes no causal, selected-set-validity,
fair-lending, or deployment claim.

The early freeze/evaluation and late sensitivity have separate immutable
records and six DVC pointers. A deterministic evidence builder verifies their
lineage, exact common point path, and all 62 table and figure files. The official INFORMS TeX is generated
from the canonical QMD source to prevent manuscript drift. At acceptance, I
will release code, environment lock, manuscript sources, artifact metadata,
DVC pointers, and raw-data acquisition instructions, subject to source
redistribution terms.

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
