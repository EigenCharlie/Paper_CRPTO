# IJDS Cover Letter and Editor Disclosures

Editor-facing material only. Do not place this file in the anonymous packet.

## Cover Letter Draft

Dear Editors,

I submit "CRPTO: Auditing Temporal Transport and Comparator Choice in
Conformal Portfolios" for consideration at the *INFORMS Journal on Data
Science*.

The paper studies a decision-focused failure mode: a predictive guarantee and
a numerical risk cap need not retain their meaning after a score enters an
optimizer. CRPTO combines a calibrated probability of default, a 90%-target
binary-outcome conformal interval, and a monthly credit-allocation linear
program. Its 540,121-loan universe is independent of final status; score strata
are fixed before residual calibration; only labels observable before the first
decision are admitted; unresolved outcomes remain in every menu; and outcomes
are joined only after allocations are frozen.

Conformal-fit coverage is 0.900388, but five-stratum all-candidate coverage is
[0.854714, 0.879647] over 15 monthly decisions from April 2016 through June
2017. The upper endpoint remains below 0.90 under pooled, two-, five-, and
ten-group taxonomies. This temporal failure occurs before portfolio selection.

The decision audit then evaluates all nine prespecified guardrails. A copied
numeric cap makes every guardrail appear to improve default relative to point
PD, as predicted by feasible-set nesting. An outcome-free comparator instead
matches each monthly funded point-PD moment to numerical error below 4.17e-17.
Under that alignment, payoff is lower for 7 of 9 guardrails, default is higher
for only 1 of 9, and funded-set miscoverage is higher for 8 of 9; the remaining
sharp intervals cross zero. Across 180 seed-concentration cells, robust signs
occur in both directions. All 27 policy-metric envelopes over the declared
comparator multiverse contain zero.

The contribution is therefore not a winning credit policy. It is a
reproducible audit design that separates temporal coverage transport,
comparator stringency, unresolved outcomes, and binding operational
constraints. The empirical conclusion is deliberately negative: temporal
coverage failure is robust in this archive, whereas portfolio direction is
not invariant to the defensible comparison rule. This data-models-decisions-
implications chain fits IJDS's focus on rigorous data science for decisions.

The archive was inspected during earlier project iterations. The current code
and outcome-free allocation protocol were locked before the complete
evaluation, but the study is retrospective rather than prospective or
preregistered. The review package records this boundary, provides sharp
partial-identification bounds, and makes no causal, selected-set-validity,
fair-lending, or deployment claim.

The outcome-free freeze and evaluation have separate immutable records and DVC
pointers. A deterministic evidence builder verifies their lineage and
regenerates all 41 table and figure files. The official INFORMS TeX is generated
from the canonical QMD source to prevent manuscript drift. At acceptance, I
will release code, environment lock, manuscript sources, artifact metadata,
DVC pointers, and raw-data acquisition instructions, subject to source
redistribution terms.

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
