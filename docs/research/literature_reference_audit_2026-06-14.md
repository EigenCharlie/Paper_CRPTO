# Literature reference audit - 2026-06-14

Scope: cited references in the IJDS manuscript body, using
`paper/submission/CRPTO_ijds_submission.aux` as the current body-citation
surface. This is not a full supplement audit.

The audit question is deliberately strict: does the repository contain evidence
that a source was actually read or curated, beyond being present in BibTeX?

## Status labels

- `strong`: local PDF/read-note/deep-audit evidence exists, or the source was
  inspected directly in this session.
- `partial`: the source is discussed in the book or manuscript, but no standalone
  read-note or deep-audit row was found.
- `citation-only`: no local reading evidence found beyond BibTeX and citation
  use. These are not automatically wrong, but they should be spot-checked before
  freeze/submission if they carry a specific claim.

## Strong local reading evidence

These body references have local reading evidence from
`docs/research/papers_tesis_deep_audit_2026-06-06.md`, the new
Fernandez-Loria/Provost note, or direct PDF inspection in this session:

`albanesi2024credit`, `angelopoulos2023`, `angelopoulos2024foundations`,
`angelopoulos2024risk`, `bao2025croms`, `bates2021rcps`, `bental2007oce`,
`bertsimas2004`, `cresswell2024`, `donti2017`, `elmachtoub2022`,
`fernandezloria2022causaldecision`, `gibbs2024`, `hu2026crc`,
`jagtiani2019altdata`, `johnstone2021`, `liu2026portfolio`, `mandi2024`,
`patel2024`, `rockafellar2000cvar`, `schutte2024robust`, `sun2024ptc`,
`aior2025lendingclub`, `yang2026multidistribution`, `yeh2025training`,
`zhao2025robust`, `zhou2025credo`, `zhou2026creme`.

Supplement-only check: `fernandezloria2025observational` was also inspected in
this session. It supports the supplement's causal/experimental-design boundary,
but it is not credit or loan evidence.

## Partial evidence

These sources are used in plausible places and are discussed in the book or
manuscript, but I did not find a standalone local read note:

`ayari2026`, `bostrom2021`, `chen2024creditrisk`, `lessmann2015`, `vovk2005`,
`xia2017`, `yang2025costaware`, `zhou2024`.

Recommended action before freeze/submission: spot-check the exact sentence each
one supports, especially if it claims recency, a benchmark frontier, or a credit
domain fact.

## Citation-only / spot-check before freeze

These references appear in the manuscript body, but I did not find local
evidence that they were read in detail:

`boucheron2013concentration`, `das2023creditgraph`, `delage2010dro`,
`ghosh2002`, `goldfarb2003robustportfolio`, `hoeffding1963`,
`boosting2025default`, `serrano2016profitscoring`, `zhao2016p2pportfolio`,
`zheng2026twostage`.

The most important items to verify are `hoeffding1963`,
`boucheron2013concentration`, and `ghosh2002` because they support theory or
inequality language; `goldfarb2003robustportfolio` and `delage2010dro` because
they anchor robust-optimization positioning; and `das2023creditgraph`,
`yang2025costaware`, `zheng2026twostage`, and `boosting2025default` because they
are recent IJDS/credit references that make the manuscript look current.

## Bottom line

The core CRPTO spine is well supported by read/curated sources: conformal
prediction/risk control, conformal robust optimization, SPO+/DFL comparison,
Lending Club fintech context, and the new decision-vs-estimation framing.

The weaker area is not the main claim; it is citation hygiene. Several classical
or recent references are being used as positioning anchors without a local note
proving close reading. They can stay for now, but they deserve a targeted
pre-freeze source check rather than another broad literature expansion.
