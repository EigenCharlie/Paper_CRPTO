# IJDS Data and Code Disclosure Form Responses

Final response text for transfer into the publisher's two-page form. This file
is editor-facing and is not a substitute for checking and signing the official
PDF in ScholarOne.

Form version verified: **Effective March 5, 2025**. Policy page last updated
January 1, 2025:
<https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>.

## Page 1

**Title of manuscript**

CRPTO: Auditing Comparator Stringency in Maturity-Safe Conformal Credit
Portfolios

**Policy acknowledgement**

- [x] I am familiar with the IJDS Data and Code Disclosure Policy and agree to
  comply.

**Data-use ethics**

- [x] The author confirms legitimate access to the data and that nothing in
  the provisions governing its use prohibits this research.
- [x] Yes, the author wishes to highlight data and algorithm ethics issues.

Paste this text in the ethics box:

> Historical consumer-credit records and algorithms trained on them may
> reflect socioeconomic and institutional disparities. This retrospective
> study does not use protected attributes, estimate causal effects, make
> individual lending recommendations, or provide a deployment or legal
> fair-lending certification. Outcomes are snapshot-based and partially
> unresolved; all such rows are retained and bounded rather than silently
> discarded. The results should therefore be read as a methodological audit of
> comparator design and optimizer selection, not as evidence that either
> policy is appropriate for live credit decisions.

## Page 2

**Select Option 4**

> The paper includes data and/or code. The code can be released but the full or
> partial set of the data cannot be released to the public. The author agrees
> to complete a reproducibility report.

Paste this text in the explanation box:

> The complete code set can be released at acceptance, including Python source,
> locked environment, experiment and evidence builders, tests, manuscript
> sources, protocol files, and reproduction commands. Aggregate publication
> tables and figures, schemas, data dictionary, execution receipts, and
> artifact checksums can also be released. The exact loan-level Lending Club
> snapshot and its loan-level processed derivatives will not be publicly
> redistributed unless the governing source terms are confirmed to permit it.
> The snapshot was obtained from public-source mirrors, but an authoritative
> redistribution license for this exact historical file is not currently
> available. The reproducibility package will provide source and acquisition
> instructions, expected filename, size, schema and checksum, deterministic
> reconstruction code, and a journal-approved verification route for the
> immutable processed/model artifacts. The author agrees to complete the IJDS
> reproducibility report and to follow any alternative disclosure plan approved
> by the Editor-in-Chief.

## Release Contract

| Material | Submission | Acceptance |
|---|---|---|
| Code, tests, environment lock, manuscript sources | Withheld from anonymous review unless requested through a sanitized archive | Public release |
| Aggregate publication tables, figures and evidence manifests | Anonymous PDFs at submission; sanitized evidence if requested | Public release |
| Raw and processed loan-level data | Acquisition/schema/checksum instructions; no public redistribution | Instructions plus editor-approved verification route unless terms permit release |
| Large model/result artifacts | Opaque P1/C1 provenance in reviewer files | DVC or journal-approved archive with exact checksums |

## Submission Action

1. Download the current official form from the policy page.
2. Transfer the title, checked responses, ethics text, Option 4, and explanation
   exactly as written above.
3. Confirm the form version is still March 5, 2025 or later.
4. Upload the completed publisher PDF as an editor/system file, never as an
   anonymous supplement.

Exact run, commit, receipt and DVC identifiers are maintained in
`EDITOR_ONLY_REPRODUCIBILITY_CROSSWALK.md`; reviewer-facing materials use the
opaque labels P1 and C1.
