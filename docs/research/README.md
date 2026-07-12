# CRPTO Research Dossier

This directory keeps only current scientific control documents and durable
literature notes. Historical plans and version-by-version audits were removed
from the working tree after their useful content was incorporated; Git history
remains the recovery mechanism.

## Active Contract

Read in this order:

1. `active_claims_2026-07-11.md` - sole paper claim registry.
2. `ijds_fixed_taxonomy_c2_protocol_2026-07-11.md` - locked V1/V2 protocol and
   recovery boundary.
3. `../../reports/crpto/ijds_fixed_taxonomy_c2_evidence.json` - sole numeric
   paper-facing manifest.
4. `../../paper/CRPTO_ijds.qmd` - canonical manuscript source.
5. `../../paper/supplement_ijds.qmd` - online supplement.

The active IJDS result is a fixed-taxonomy comparator audit. Temporal candidate
coverage is below 90% under all four declared taxonomies. Portfolio direction
is not invariant over C0/C1/C2, a 29-cap frontier, seeds, purpose constraints,
and LGD. No selected policy or universal direction is active.

## Literature Assets

- `literature_corpus_inventory_2026-07-10.csv` - inventory of the local PDF
  corpus and active documents.
- `papers_tesis_deep_audit_2026-06-06.md` - detailed local-corpus synthesis.
- `ijds_state_of_art_audit_2026-07-10.md` - closest-work and IJDS positioning.
- `ijds_literature_expansion_scan_2026-07-08.md` - external literature scan.
- `literature_reference_audit_2026-06-14.md` - source-to-citation audit.
- `literature/` - curated notes, hashes, and editorial use decisions.

PDFs remain in `Papers_tesis/`, ignored by Git. Do not commit copyrighted
papers; version notes and bibliographic metadata instead.

## Durable Reference

- `foundations/` contains technical background and runbooks still useful for
  the thesis or code maintenance.
- `archive/` contains deliberately archived provenance already separated from
  the active contract.
- `bound_tightening_audit/` contains historical generated diagnostics and is
  not active evidence.
- `future_work/` is not a second-paper plan for the current submission. Treat
  it only as deferred technical ideas unless the user explicitly reopens it.

## Rule

Do not create a new dated memo for routine progress. Update the active claim
registry, protocol, code, tests, or submission documentation directly. Create a
new protocol only when a scientific object changes before execution.
