# IJDS Data and Code Disclosure Form Responses

Editor-facing transfer text for the current official two-page form. The form
and policy were rechecked on July 12, 2026. The form remains version
`03.05.2025`, effective March 5, 2025, and the policy page remains updated
January 1, 2025.

- Form: <https://pubsonline.informs.org/ijds/data-and-code-disclosure-form>
- Policy: <https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>

Recheck both links during submission week.

## Page 1

**Title of manuscript**

CRPTO: Auditing Temporal Transport and Comparator Choice in Conformal
Portfolios

**Policy acknowledgement**

- [x] I am familiar with the policy and agree to comply.

**Data-use ethics**

- [x] The author confirms legitimate access and that the governing provisions
  do not prohibit this research use.
- [x] Yes, the author wishes to highlight data and algorithm ethics issues.

Paste in the ethics box:

> Historical consumer-credit records and algorithms trained on them may
> reflect socioeconomic and institutional disparities. This retrospective
> study does not use protected attributes, estimate causal effects, make
> individual lending recommendations, or provide a deployment or legal
> fair-lending certification. Terminal snapshot outcomes are partially
> unresolved; such rows remain in candidate menus and receive sharp bounds
> rather than being deleted. The results are a methodological audit of temporal
> transport, comparator design, and optimizer selection, not evidence that any
> evaluated policy is appropriate for live credit decisions.
> Comparator and residual-window choices can change policy conclusions, so a
> label such as "safer" is not used without its explicit decision contract.

## Page 2

**Select Option 4**

> The paper includes data and/or code. The code can be released but the full or
> partial set of the data cannot be released to the public. The author agrees
> to complete a reproducibility report.

Paste in the explanation box:

> The complete code set can be released at acceptance, including Python source,
> locked environment, experiment and evidence builders, tests, manuscript
> sources, protocol files, and reproduction commands. Aggregate publication
> tables and figures, schemas, data dictionary, execution receipts, artifact
> checksums, and a synthetic smoke-test fixture can also be released. The exact
> loan-level Lending Club snapshot and its loan-level processed derivatives
> will not be publicly redistributed unless the governing source terms are
> confirmed to permit it. An authoritative redistribution license for this
> exact historical snapshot is not currently available. The package will
> provide source and acquisition instructions, expected filename, size, schema,
> checksum, deterministic reconstruction code, DVC metadata, and an
> editor-approved verification route for immutable processed and model
> artifacts. The author agrees to complete the IJDS reproducibility report and
> any alternative disclosure plan approved by the Editor-in-Chief.

## Release Contract

| Material | Initial submission | Acceptance |
|---|---|---|
| Code, tests, lock, manuscript sources | Sanitized archive only if requested | Public release |
| Aggregate evidence | Anonymous PDFs; sanitized evidence if requested | Public release |
| Raw and processed loan-level data | Acquisition/schema/checksum instructions | Instructions and editor-approved verification unless terms permit release |
| Active model/result bundles | Anonymous descriptions | DVC or journal-approved archive with exact checksums |

Exact run, commit, receipt, and DVC identifiers remain in
`EDITOR_ONLY_REPRODUCIBILITY_CROSSWALK.md`; they do not appear in anonymous
review files.
