# Multidataset External Replication Source Log

This folder contains only curated, local CSV summaries used by the paper and book.
It intentionally does not contain credentials, browser-session references, or paths to the exploratory laboratory.

## Public Dataset Sources

- Prosper loan-level data access documentation: https://help.prosper.com/hc/en-us/articles/210013083-Where-can-I-download-data-about-loans-through-Prosper
- Freddie Mac Single Family Loan-Level Dataset: https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset
- Freddie/Mendeley processed mortgage windows: https://data.mendeley.com/datasets/bzr2rxttvz/3
- Home Credit Default Risk page, archived only and not used in the main external claim: https://www.kaggle.com/competitions/home-credit-default-risk/data

## Editorial Decision

Prosper final-status loans and Freddie FM48 are reported as external economic replications. Home Credit is discarded from the IJDS main claim because it lacks a clean investment-return and exposure contract comparable to Lending Club, Prosper, and Freddie.

## Extended Audit Layer

A28 solves the Freddie FM48 LP on the full OOT candidate universe and documents that the all-candidate optimum funds only loans inside the top-return screen. A29 isolates sparse Mondrian groups. A30--A33 report confidence intervals, OOT subperiods, Prosper default-definition sensitivity, and Freddie red/green segment sensitivity.
