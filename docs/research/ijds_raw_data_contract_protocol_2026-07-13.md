# IJDS full-archive data-contract audit protocol

**Status:** declared descriptive audit; no model, learner, policy, window, or
comparator selection.

## Research question

The raw Lending Club file contains every accepted-loan record available in the
local 2007--2020Q3 archive, but rows and columns are not interchangeable across
scientific roles. This audit asks which information is legitimately usable at
origination and at the March 31, 2016 information cutoff of the active IJDS
estimand.

## Locked rules

1. Scan the complete DVC-tracked CSV, not a sample.
2. Preserve the active 36-month contract and status-independent membership.
3. Report every active fitting, policy, OOT, maturity-gap, extension, and
   post-extension cohort.
4. A raw candidate is eligible for the current temporal model only when it is
   not post-outcome, identifier/free text, or geography, and has at least 95%
   coverage in PD development, probability calibration, and conformal fitting.
5. A feature is labeled late-schema when fitting coverage is below 50% while
   primary-OOT coverage is at least 80%.
6. `loan_amnt` and `funded_amnt` are reconciled by cohort. Neither definition
   may be chosen after inspecting portfolio outcomes.
7. Rows in the 2014--March 2016 maturity gap are not promoted as ordinary
   binary training labels merely because their final 2020 status is known.
   Label availability is evaluated at the declared 2016 cutoff.
8. No protected stage or manifest-protected artifact is executed or written.

## Interpretation boundary

More raw rows or columns do not imply a more complete estimand. Late bureau
fields can support a later-vintage study, but imputing their total absence in
the early training block would not create a valid stronger version of the
active model. Likewise, resolved 2014--2016 loans form a duration-selected
subset at the information cutoff; using them as ordinary terminal labels would
reintroduce the maturity bias removed from the active paper.
