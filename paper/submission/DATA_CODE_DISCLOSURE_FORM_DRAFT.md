# IJDS Data and Code Disclosure Form Draft

Transfer this content into the official two-page form effective March 5, 2025:
<https://pubsonline.informs.org/ijds/data-and-code-disclosure-form>. This file
is a field map, not a substitute for the signed official form.

## Page 1

**Title of manuscript:** CRPTO: Auditing Binary Conformal Geometry and
Portfolio Comparators

**Policy confirmation:** Check the box confirming familiarity with and
agreement to comply with the IJDS Data and Code Disclosure Policy.

**Legitimate access confirmation:** Check the box confirming legitimate access
to the Lending Club research archive and that the provisions governing its use
do not prohibit this research. Reconfirm this statement against the actual
acquisition source before submission.

**Data-use ethics:** Select **Yes, considerations should be highlighted** and
enter:

> The study concerns historical consumer-credit decisions. The archive covers
> accepted loans and does not contain counterfactual outcomes for rejected
> applicants. The analysis does not use protected attributes, authorize
> lending decisions, estimate causal effects, or claim fair-lending compliance.
> Terminal status and a simplified payoff compress payment timing, competing
> events, recoveries, fees, and capital costs. The distributed archive is not a
> verified point-in-time snapshot, so endpoint observability is reconstructed
> under a disclosed conservative timing assumption and unresolved outcomes are
> retained in sharp bounds. These limitations constrain deployment and equity
> interpretations.

## Page 2

**Selected sharing option:** **Option 6**, because all active analysis code and
aggregate evidence can be released, while only a partial data set can be made
public. The author agrees to complete the IJDS reproducibility report.

**Explanation box:**

> (a) The accepted-paper package will release the complete active analysis
> code, tests, environment lock, configuration, protocol and claim registries,
> aggregate publication tables and figures, evidence metadata, and scripts for
> reconstructing every result from the source archive. It will also release
> non-row-level schema, census, and audit summaries. (b) The 1.7 GB Lending Club
> CSV and row-level derived score, allocation, and outcome artifacts will not be
> redistributed by the authors. The original file was acquired as a historical
> public research archive, but there is no stable issuer-maintained download and
> redistribution terms for copies and row-level derivatives must be respected.
> The package records the exact raw-file SHA-256, dimensions, schema checks, and
> acquisition/reconstruction instructions so a reader with a lawful copy can
> reproduce the analysis. The distinction is therefore complete code plus
> aggregate evidence, but no raw or row-level loan data.

## Verified Data Facts

- Raw identity: `Loan_status_2007-2020Q3.csv`, 2,925,493 rows, 142 columns,
  SHA-256 `5878af2a088f8ab5214c9337289fb8b5eb6c6338fd3f417b6cdc18513dc6f35f`.
- Active population: 640,543 eligible 36-month loans under the declared dates,
  schema, horizon, and origination-observability rules; no sampling.
- Primary OOT: 376,890 candidates, 364,814 outcomes reconstructed as observable
  by September 30, 2020, and 12,076 unresolved outcomes retained in sharp
  binary bounds.
- Endpoint reasons: 307,842 fully paid and 56,972 charged off by the cutoff;
  11,551 nonterminal; 47 terminal after the cutoff; and 478 terminal with a
  missing availability date. These categories partition the primary panel.
- Endpoint timing: Fully Paid is available at the month-end of `last_pymnt_d`;
  Charged Off is available at that month-end plus six calendar months. The
  latter is a modeling assumption, not an observed operational charge-off date.

## Package Boundary

The release includes `pyproject.toml`, `uv.lock`, active source and claim
registries and executable claim ledger, the complete `src` package,
active experiment/build scripts, 27 DVC
pointers, aggregate evidence, canonical QMD, generated TeX, bibliography, and
the scientific, type, drift, anonymity, compilation, and visual-QA gates.
Credentials, local DVC configuration, absolute paths, protected extraction
artifacts, and copyrighted publisher assets are excluded.

Recheck the selected option, acquisition rights, repository destination, and
the exact set of releasable data immediately before the official form is
signed. A change in what can legally be shared requires changing Option 6 and
its explanation, not silently changing the release package.
