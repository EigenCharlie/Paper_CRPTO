# Raw Data Source Notes

These notes support the IJDS Data and Code Disclosure Form and the accepted-paper
reproducibility package. They are not part of the anonymous reviewer manuscript.

Last checked for the submission package: 2026-07-06 UTC.

## Source Inventory

| Source | Paper role | Public access note | In-package handling |
|---|---|---|---|
| Lending Club Loan Data 2007-2020Q3 | Main static credit-risk panel and promoted Lending Club funded-set certificate. | Kaggle mirrors and Figshare mirrors exist for `Loan_status_2007-2020Q3.csv`; the project uses a local raw CSV under `data/raw/`, which is ignored by Git and tracked through DVC metadata. | Provide acquisition instructions, schema/cleaning code, DVC pointers for processed artifacts when allowed, and manifest hashes. Do not commit or rehost the 1.7 GB raw CSV in Git. |
| Prosper loan-level data | Frozen external marketplace-loan economic replication. | Prosper documents loan-level data access through its investor/API data path: <https://help.prosper.com/hc/en-us/articles/210013083-Where-can-I-download-data-about-loans-through-Prosper>. | Provide source notes, curated summary CSVs, and generated A25-A34 evidence. Do not treat Prosper as a new exact funded-set certificate. |
| Freddie Mac Single-Family Loan-Level Dataset | Source ecosystem for the Freddie/Mendeley mortgage-credit replication. | Freddie Mac documents the Single-Family Loan-Level Dataset at <https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset>. | Provide source notes and external replication summaries; do not redistribute raw Freddie files unless the journal workflow and source terms permit it. |
| Freddie/Mendeley processed mortgage windows | Processed FM24/FM36/FM48/FM60 windows used for the external replication audit. | Mendeley dataset page used by the paper: <https://data.mendeley.com/datasets/bzr2rxttvz/3>. | Provide the exact window definition used in the scripts and the generated A25-A34 artifacts. |
| Home Credit Default Risk | Audited but not promoted. | Kaggle competition data page: <https://www.kaggle.com/competitions/home-credit-default-risk/data>. | Mention only as archived context: it lacks the clean `exposure + return` investment contract required for the external economic claim. |

## Rebuild Boundary

The accepted-paper package should let a reader rebuild or audit the manuscript
artifacts without relying on author-local paths:

1. Obtain raw data from the public source pages above when redistribution is not
   allowed.
2. Recreate processed artifacts through the project scripts or retrieve
   processed/model artifacts through the declared DVC remote if access is
   provided by the journal workflow.
3. Verify frozen outputs with `EXTRACTION_MANIFEST.json` and
   `just validate-champion`.
4. Rebuild safe paper surfaces with `just tables`, `just figures`,
   `just evidence`, `just journal-package`, and `just paper-submission-pdf`.

The protected search and champion stages are not routine reproduction steps.
They require a new run tag and explicit revalidation plan.
