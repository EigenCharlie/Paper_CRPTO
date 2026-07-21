# CRPTO references: active state of the art

Last audited: 2026-07-21.

This note is a concise routing document. The complete paper-by-paper corpus
audit, extraction QA, and inclusion decisions are in
`docs/research/conformal_literature_corpus_audit_2026-07-21.md`. The separate
book audit is in
`docs/research/applied_conformal_prediction_book_audit_2026-07-21.md`.

## Corpus status

- `Papers_tesis` contains 112 PDFs and 4,412 pages.
- The 2026-07-21 frontier addition contains 15 PDFs and 557 pages.
- Every frontier PDF was read completely, including appendices, proofs,
  formulas, tables, and figures; suspicious formulas were checked against the
  rendered PDF rather than trusted to extraction alone.
- The external 168-page *Applied Conformal Prediction* book was independently
  extracted and audited. It is useful pedagogically but is not an authority for
  several claims about ordering, conditional coverage, calibration, and
  empirical validation.

## Theory that directly governs CRPTO

### Marginal and class-conditional conformal prediction

Classwise or label-Mondrian conformal prediction uses a threshold for each
label and targets

$$
P\{Y\in C(X)\mid Y=y\}\ge 1-\alpha
$$

under exchangeability within the relevant label category. Ding et al. (2023)
is the primary current reference. In binary CRPTO, clustering many classes is
unnecessary; direct label-Mondrian thresholds are the relevant benchmark.

The active paper therefore reports both:

1. the original score-stratified marginal recipe; and
2. a complete label-by-score-stratum sensitivity.

The latter does not restore validity under unverified temporal transport.

### Exchangeability and temporal transport

Split conformal's usual marginal finite-sample rank guarantee requires
exchangeability of the calibration scores with one new score in the frozen
category. Applying that statement separately to future points does not imply
that their whole target block is jointly exchangeable with calibration.
Temporal separation and overlapping windows do not themselves establish either
condition. Oliveira et al. (2024) gives approximate guarantees under explicitly
bounded dependence or distribution discrepancy; CRPTO has not identified such
bounds.

The active combined-rank reference diagnostic uses the following exact law
under its assumptions. For calibration
size $n$, rank $r=\lceil(n+1)(1-\alpha)\rceil$, and target size $m$, strict
misses satisfy

$$
M\sim\operatorname{BetaBinomial}(m,n+1-r,r)
$$

under continuous joint exchangeability of all $n+m$ scores. This is a stronger
block null than the condition used for the ordinary one-future-point marginal
guarantee. With tied scores, independent continuous
lexicographic tie breakers are used only as a proof device; deterministic
strict misses are bounded by the tie-broken count, making the same upper tail
conservative. This diagnostic is separate from the deterministic finite-archive
coverage bounds. In CRPTO it is reported only as a retrospective diagnostic:
31/40 cells meet locked nominal Bonferroni--Holm thresholds, but the family and
pattern were inspected before the lock, so those flags do not carry
post-selection or study-wide FWER control and do not refute the usual marginal
split-conformal guarantee.

### Selection and optimization

Candidate-level marginal or class-conditional coverage is not funded-set
validity. Jin and Ren (2025) is the closest theoretical reference for strong
selection-conditional coverage under permutation-invariant black-box
selection. Applying that theory to CRPTO would require a fully frozen solver
and randomization contract, exchangeability, and computational reference-set
construction that the current design does not implement.

Gazin et al. (2025) and related FCR methods control a different target: the
expected proportion of erroneous sets among selected informative sets. Their
selection rules do not automatically cover a budget-coupled knapsack or LP.

### Online and distribution-shift methods

Gibbs and Candes (2024) motivates adaptive online calibration under shift, but
CRPTO lacks prompt sequential label feedback because default labels mature
slowly. Weighted conformal and weighted conformal risk control require
identified density ratios or invariance assumptions that are not established
here. These are future-work directions, not repairs for the active archive.

## Frontier-paper dispositions

### Use in the manuscript

- Ding et al. (2023): class-conditional conformal prediction and finite-sample
  classwise variability.
- Oliveira et al. (2024): explicit conditions needed for nonexchangeable split
  conformal guarantees.
- Jin and Ren (2025): selection-conditional coverage boundary closest to the
  portfolio optimizer.
- Gazin et al. (2025): FCR as distinct from candidate or funded-set coverage.
- Gibbs and Candes (2024): adaptive online calibration as future work with a
  delayed-feedback limitation.

### Future work only

- long-tail multiclasse conformal prediction;
- interval-valued outcomes;
- optimized FCR;
- weighted conformal risk control;
- counterfactual decision sets;
- audited conformal prediction under a strictly nested target design.

These methods change assumptions or estimands and cannot be presented as
drop-in guarantees for CRPTO.

### Quarantine as support

- Peng and Lessmann (2026): target-definition, simulated-drift, cross-validation,
  calibration, and metric-orientation inconsistencies.
- Sesia and Svetnik (2025): reciprocal mismatch in the published IPCW theorem
  mapping; do not rely on the current proof as methodological support.
- Zhu et al. (2026): inverted utility tail in the method statement, unsupported
  convexity/subgradient steps, boundary KKT omission, experiment/theorem step
  mismatch, and reported coverage below nominal.

These papers remain in the local corpus for provenance and adversarial review,
not as affirmative support.

## Current research gaps, stated conservatively

The literature search did not find a method that simultaneously supplies all
of the following for the active CRPTO setting:

- delayed and partially unresolved binary credit outcomes;
- unverified temporal transport from conformal fit to evaluation;
- status-independent monthly candidate menus;
- a batch-coupled budget and concentration optimizer;
- selected- or funded-set coverage after optimization; and
- sharp finite-archive evaluation without a missing-at-random assumption.

This is a scoped corpus finding, not a universal claim that no such paper
exists. The defensible contribution is therefore an identification audit of
the handoff, not novelty of conformal prediction, credit scoring, or robust
optimization individually.

## Writing rules induced by the literature audit

- Say `k`-th smallest residual in ascending order and use `+infinity` when
  $k=n+1$.
- Distinguish a realized sharp coverage shortfall from a stronger joint-block
  rank diagnostic, and neither from a test of the usual marginal guarantee.
- Distinguish marginal, label-conditional, selection-conditional, and FCR
  guarantees.
- Never call Platt scaling, Venn--Abers calibration, or label-Mondrian fitting a
  generic repair for conditional coverage or temporal shift.
- Do not export a candidate-level guarantee to funded loans.
- Treat adaptive, weighted, survival, counterfactual, and action-conditional
  methods as different designs unless their assumptions and decision unit are
  implemented explicitly.
