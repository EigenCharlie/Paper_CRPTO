# Raw Data Source Notes

These notes support the IJDS Data and Code Disclosure Form and the accepted-paper
reproducibility package. They are not part of the anonymous reviewer manuscript.

Last checked for the submission package: 2026-07-10 UTC.

## Source Inventory

| Source | Paper role | Public access note | In-package handling |
|---|---|---|---|
| Lending Club Loan Data 2007-2020Q3 | Active 540,121-row fixed-taxonomy audit panel. | Kaggle mirrors and Figshare mirrors exist for `Loan_status_2007-2020Q3.csv`; the project uses a local raw CSV under `data/raw/`, ignored by Git and referenced by DVC metadata. | Provide acquisition instructions, expected size/SHA-256, schema/cleaning code, and all four active DVC pointers. Do not commit or rehost the 1.7 GB raw CSV in Git. |
| Prosper loan-level data | Historical external marketplace diagnostic, not active evidence. | Prosper documents loan-level data access through its investor/API data path: <https://help.prosper.com/hc/en-us/articles/210013083-Where-can-I-download-data-about-loans-through-Prosper>. | Retain source notes for project provenance; exclude from the minimal IJDS capsule unless requested. |
| Freddie Mac Single-Family Loan-Level Dataset | Historical external mortgage diagnostic, not active evidence. | Freddie Mac documents the Single-Family Loan-Level Dataset at <https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset>. | Retain source notes; do not redistribute raw Freddie files unless source terms and journal workflow permit it. |
| Freddie/Mendeley processed mortgage windows | Historical FM24/FM36/FM48/FM60 diagnostic windows. | Mendeley dataset page: <https://data.mendeley.com/datasets/bzr2rxttvz/3>. | Exclude from the minimal active capsule; historical A25--A34 cannot validate v2. |
| Home Credit Default Risk | Audited but not promoted. | Kaggle competition data page: <https://www.kaggle.com/competitions/home-credit-default-risk/data>. | Mention only as archived context: it lacks the clean `exposure + return` investment contract required for the external economic claim. |

## Source Permanence Caveat

The raw Lending Club retail-loan file is a historical public-source dataset, not
a source with an active issuer-maintained permanence guarantee for this paper.
Lending Club ended retail-loan originations after the 2020 window used here, and
the `Loan_status_2007-2020Q3.csv` copies available through Kaggle/Figshare-style
mirrors are community or repository mirrors rather than journal-controlled
archives. The reproducibility package should therefore avoid depending on a
single raw-data URL. It should disclose source pages, schema/cleaning code, DVC
pointers or processed artifacts where source terms permit, and manifest hashes
that let a reviewer verify the exact paper-facing artifact chain.

## Rebuild Boundary

The accepted-paper package should let a reader rebuild or audit the manuscript
artifacts without relying on author-local paths:

1. Obtain raw data from the public source pages above when redistribution is not
   allowed.
2. Recreate processed artifacts through the project scripts or retrieve
   processed/model artifacts through the declared DVC remote if access is
   provided by the journal workflow.
3. Verify frozen outputs with `EXTRACTION_MANIFEST.json` and
   `just validate-champion-strict` before submission freeze.
4. Rebuild the active paper evidence with `just ijds-evidence`, run
   `just publication-integrity`, and render the reviewer surfaces with
   `just paper-submission-pdf` and `just paper-submission-official`.

The protected search and champion stages are not routine reproduction steps.
They require a new run tag and explicit revalidation plan.
