# IJDS submission rights and anonymity audit

## Current verdict

The scientific manuscript can be rebuilt as an anonymous reviewer package, but
submission remains blocked until the human and rights confirmations below are
complete. These controls do not change the empirical evidence.

## Double-anonymous review

As verified on 2026-07-22, the public repository and GitHub Pages still connect
the distinctive CRPTO title and acronym to author-identifying metadata. The
live Pages site also displays retired selected-policy and historical claims.
Attempts to disable Pages and make the repository private through the configured
GitHub CLI credential both returned HTTP 403 (`Resource not accessible by
personal access token`), so no external setting changed. Before ScholarOne
upload, an owner-authenticated administrator must:

1. keep `EigenCharlie/Paper_CRPTO` private during review;
2. keep GitHub Pages disabled;
3. ensure reviewer PDFs and machine-readable supplements contain no author,
   email, repository URL, path, commit, tag, hash, DVC coordinate, or historical
   selected-policy text;
4. test signed-out searches for the title, `CRPTO`, and distinctive phrases;
5. provide code to editors through a sanitized anonymous capsule rather than a
   public author-linked URL.

## Copyright and prior content license

`LICENSE-CONTENT` grants CC BY 4.0 over `paper/**`, figures, tables, and
documentation. That grant is not treated as revoked by deleting or changing a
repository file. INFORMS' current author materials distinguish conventional
copyright transfer from its Open Option. The submitting author must disclose
the prior public license to INFORMS and obtain written direction on the
appropriate publication route before certifying that conventional transfer is
unencumbered.

Authoritative pages to recheck at submission:

- IJDS submission guidelines:
  <https://pubsonline.informs.org/page/ijds/submission-guidelines>
- INFORMS rights and permissions:
  <https://pubsonline.informs.org/authorportal/rights-permissions>
- INFORMS Open Option:
  <https://pubsonline.informs.org/authorportal/open-option>
- IJDS data and code policy:
  <https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>
- IJDS generative-AI policy:
  <https://pubsonline.informs.org/page/ijds/llm-policy>

This record flags a rights question; it is not legal advice and does not choose
the publication route for the author.

## Human confirmations

Repository evidence cannot certify originality, simultaneous-review status,
prior-submission history, overlap with a thesis/preprint/book/site, author list
and order, consent, CRediT roles, affiliation, ORCID, funding, conflicts,
acknowledgements, legitimate data access, or the final scope of generative-AI
use. Each item must be confirmed by the responsible author in the private
ScholarOne materials.

## Credential and data boundary

`.dvc/config.local` is ignored, untracked, and absent from reachable Git
history in the 2026-07-21 audit. That is evidence of current repository hygiene,
not proof that credentials were never exposed elsewhere. Keep credentials in a
credential manager or environment-specific store and exclude local DVC config
from every capsule. Raw-data provenance and redistribution controls are tracked
separately in `ijds_raw_data_acquisition_provenance_2026-07-21.md`.
