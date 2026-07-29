# Conformal decision SOTA last-mile audit (2026-07-26)

Status: literature-audit record; not an empirical evidence source.

## Scope and byte boundary

A final primary-source search after the 122-PDF local corpus identified two
nonduplicative 2026 papers that materially sharpen CRPTO's positioning:

1. Shekhar and Howard, *Decision-Calibrated Conformal Uncertainty for Pacing
   Decisions in Streaming Advertising*, arXiv:2606.10187v1, 29 pages; and
2. Lützow et al., *Multi-Variable Conformal Prediction: Optimizing Prediction
   Sets without Data Splitting*, arXiv:2605.12341v1, 23 pages.

Both versions were read in full through the primary arXiv document interface.
Neither title, arXiv identifier, nor author/title alias occurs in the local
corpus or existing bibliography. Network policy prevented materializing the PDF
bytes locally, so the verified local inventory remains 122 PDFs and 4,673
pages. No local SHA-256 is claimed. If the two primary PDFs are later acquired,
the expected inventory is 124 PDFs and 4,725 pages, subject to byte and page
verification at intake.

## Shekhar--Howard decision-calibrated pacing

The paper calibrates the largest affine effect of a forecast error over a finite
catalog of deployable policies. Its decision score is the support function of
the signed policy-sensitivity set. This is CRPTO's closest current neighbor:
both works place conformal uncertainty inside a budgeted decision system and
treat decision geometry as part of the estimand.

The objects remain different. Shekhar--Howard construct a catalog-uniform
forecast-error score and then select a robust pacing policy. CRPTO freezes a
binary default-label set, audits a nonidentified continuous per-loan endpoint
used as an LP coefficient, preserves unresolved outcomes, and assumes no
temporal transport guarantee. Their certificate therefore does not transfer to
funded loans or to CRPTO's comparator audit.

Adversarial theorem audit:

- The minimality theorem is relative to finite, semicontinuous, sublinear
  certificates that protect a finite catalog under affine downstream
  contributions. It is not minimality among all uncertainty measures.
- Split-conformal rank validity requires exchangeable planning blocks. The
  empirical replays do not establish that condition; the Criteo chronology is
  induced from row order and the policy catalog is constructed.
- Lemma A.1 and Proposition 5.1 state a concentration conclusion for
  exchangeable scores but invoke Dvoretzky--Kiefer--Wolfowitz. DKW requires an
  iid-type empirical-process contract, not arbitrary exchangeability. The
  exchangeable construction `S_1=...=S_n=Z` with continuous `Z` is a direct
  counterexample to concentration of the empirical quantile. This affects the
  sample-complexity/stability layer, not the ordinary rank guarantee.
- Selected-policy feasibility additionally assumes a simultaneous event
  uniform over policies and constraints. With the paper's three 0.1 error
  allocations, the stated union-bound level is 0.7. Response and experience
  radii in the replay also use standard-error and fallback components rather
  than one complete conformal certificate.
- Approximation of a continuous policy class requires the stated net and
  Lipschitz conditions; the experimental twelve-policy catalog is not itself a
  certificate of exhaustive continuous support.

Disposition: cite as the closest decision-calibrated construction, but do not
use its Proposition 5.1 or empirical selected-policy result to support any
CRPTO guarantee.

## Lützow et al. multi-variable conformal prediction

MCP makes prediction-set shape and calibration parameters explicit decision
variables in a scenario-optimization problem. RemMCP provides the cleanest
theoretical construction under exchangeability, convexity, optimizer
uniqueness, and nondegeneracy; high-confidence statements add an iid contract.
Its removal budget shrinks with parameter dimension, so flexible geometry has a
real calibration cost.

RelMCP permits nonconvex sets through a predeclared finite grid. The adaptive
penalty search used in the experiments is acknowledged to lie outside that
strict theorem, and its solution-complexity estimate is heuristic. Distribution
shift is not treated.

MCP does not refute CRPTO's binary-set embedding lemma. It can choose an
embedding only after adding a design objective and new regularity assumptions;
that is identification by design, not identification supplied by binary-set
coverage. Binary discreteness and ties also require a separate nondegeneracy
audit.

Disposition: cite as an adjacent replacement construction, not implement in the
active audit.

## Novelty boundary after intake

CRPTO must not claim priority for decision-calibrated conformal prediction,
decision-sensitive geometry, or finite policy catalogs; nor may it claim that
all geometry adaptation requires a second split. The defensible contribution is
the specific audited handoff

`binary label set -> set-equivalent continuous per-loan embedding -> credit LP`,

combined with exact binary geometry, partial outcome identification, temporal
transport diagnostics, and comparator dependence. No located paper studies
that complete object.

Primary records:

- <https://arxiv.org/abs/2606.10187v1>
- <https://arxiv.org/abs/2605.12341v1>
