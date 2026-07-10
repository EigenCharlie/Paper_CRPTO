# IJDS Cover Letter and Disclosure Draft

Editor-facing material only. Do not include it in the double-anonymous reviewer
packet unless ScholarOne requests the corresponding disclosure text.

## Cover Letter

Dear Editors,

We submit "CRPTO: A Calibration-Selected Conformal Guardrail for Auditable
Credit Portfolio Decisions" for consideration at the *INFORMS Journal on Data
Science*. The paper treats credit allocation as data science for decisions,
not as a credit-scoring leaderboard. A frozen calibrated PD model is combined
with an exactly replayed 90% Mondrian conformal endpoint. The resulting
midpoint score, `q=(p+u)/2`, constrains a `$1M` portfolio while point PD remains
in the expected-return objective.

The final policy is selected from nine round-number candidates on November
2017 using a deterministic endpoint cap. Outcomes are stored separately from
its 12-column ranking frame, which contains no assumption-conditional
statistics. An outcome-free
December replay selects the same rule; opening outcomes afterward reveals
miscoverage `0.124925`, so the paper explicitly does not infer selected-set
validity from policy stability. On 276,869 out-of-time Lending Club loans, the
fixed policy earns `$179,327.59`, with weighted default `0.039375`.
A matched point-PD allocation earns `$196,369.14` with weighted default
`0.118400`. The paper reports both the `8.678%` return cost and the `7.9025`
percentage-point default reduction, together with temporal periods in which
the point-PD decision performs better. We therefore position CRPTO as an
auditable retrospective return-risk guardrail, not as a universal winner or
prospective deployment guarantee.

The submission contributes an explicit prediction-to-decision contract, an
exact conformal replay, a temporally separated selector/audit, matched economic
comparisons, and a file-backed reproducibility package. These features align
with IJDS's emphasis on data, innovative methodology, decision relevance, and
reproducible evidence.

Sincerely,

[Author details supplied separately]

## Data and Code Availability

The body and supplement are double-anonymous. During review they refer to a
reproducible companion without exposing author-identifying URLs. The IJDS Data
and Code Disclosure Form will state that, when venue policy permits, the
companion includes:

- source code, configurations, and manuscript sources;
- A35--A40 evidence tables and active governance metadata;
- DVC metadata and artifact pointers for large processed data and model files;
- source instructions for Lending Club, Prosper, and Freddie/Mendeley data
  rather than unauthorized redistribution;
- exact-alpha and calibration-selector replay commands;
- manifest, claim-sync, and publication-integrity tests;
- commands for regenerating tables, previews, and the official-template PDF.

No secrets, tokens, private storage credentials, local usernames, or machine
paths belong in the reviewer package.

Suggested ScholarOne prose:

> Code, configurations, manuscript sources, and evidence-generation scripts
> will be released under the journal's accepted-paper reproducibility process.
> Public-source raw data are disclosed through source instructions; large or
> license-constrained artifacts are provided through documented pointers and
> integrity hashes where redistribution terms permit.

## Anonymity Handling

- Upload the `informs4` PDF built with `dblanonrev` as the manuscript.
- Upload the anonymous supplement separately.
- Keep the title page, affiliation, acknowledgements, repository ownership,
  and personal URLs outside reviewer-facing files.
- Use this file and ScholarOne fields for editor-only disclosure timing.

## Editorial Boundary

The final ranking code is outcome-free with respect to OOT policy selection,
but earlier project development inspected the static OOT corpus. The manuscript
therefore says "retrospective lockbox replay," not "preregistered" or
"untouched holdout." Marginal/Mondrian coverage is not promoted to nominal
validity under optimizer-selected funded weights. OCE/CVaR, SPO+, online-style
checks, and external datasets remain diagnostics or context rather than
additional active methods.
