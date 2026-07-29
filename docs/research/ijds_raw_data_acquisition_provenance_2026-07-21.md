# IJDS raw-data acquisition provenance record

## Status and boundary

This record separates verified local file identity from unverified acquisition
history. It is a submission-control document, not evidence that the author
obtained the file from any particular mirror or that a third-party license
authorizes redistribution.

## Verified local object

- Local filename: `Loan_status_2007-2020Q3.csv`
- Bytes: 1,773,470,505
- Data rows: 2,925,493
- Columns: 142
- SHA-256:
  `5878af2a088f8ab5214c9337289fb8b5eb6c6338fd3f417b6cdc18513dc6f35f`
- Git status: ignored and not tracked
- Active release boundary: raw and row-level derivatives are excluded from the
  reviewer capsule and from any public release unless redistribution rights are
  separately confirmed.

These facts are verified by the active full-file audit and identify the exact
input consumed by the analysis.

## Candidate public-source match

The local filename and byte size match the file `Loan_status_2007-2020Q3.gzip`
listed in the Kaggle dataset **Lending Club 2007--2020Q3**, owner `ethon0426`,
version 3, updated 2020-12-15:

<https://www.kaggle.com/datasets/ethon0426/lending-club-20072020q1>

Kaggle labels that dataset's license as “Other (specified in description),”
while the public description reviewed on 2026-07-21 does not state clear
redistribution terms. Matching name and size is useful provenance evidence but
does **not** prove that this was the author's acquisition source, acquisition
date, or governing license.

## Author confirmations required before submission

The submitting author must record in a private submission log:

1. the actual source/owner and URL or transfer channel;
2. acquisition date and, if applicable, account or agreement under which it
   was accessed;
3. the original compressed filename and any decompression or rename step;
4. confirmation that research use is legitimate under the applicable terms;
5. confirmation that neither the public repository, DVC remote, anonymous
   capsule, nor supplement redistributes raw or row-level data without rights;
6. the final IJDS data-sharing option and any editor-facing access procedure.

Until those confirmations are complete, the data/code disclosure must say that
the candidate Kaggle match is unconfirmed and must not describe the input as an
issuer-maintained public dataset or promise raw-data redistribution.

## Recommended submission posture

Option 6 remains the conservative working choice: release code, locks,
aggregate evidence, schema/census audits, and exact reconstruction checks, but
not the raw file or row-level derivatives. This is a reproducibility design,
not a substitute for legitimate-access confirmation. If the author's actual
source or terms differ, update this record and the disclosure form before
signing; do not alter the verified local hash.
