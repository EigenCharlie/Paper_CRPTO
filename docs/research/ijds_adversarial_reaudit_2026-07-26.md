# IJDS Adversarial Reaudit and Remediation Record — 2026-07-26

Status: implementation record; not an empirical evidence source.

## Scope

This review re-audited the active manuscript, supplement, claim registry,
publication builder, new binary-geometry code, attempted external lineage,
submission surfaces, and pending recommendations after the full PDF/literature
audit. Three independent adversarial passes focused on theory, lineage/data
rights, and scientific narrative. The standard was whether a statement follows
from the declared estimand and registered evidence, not whether it is intuitively
plausible or improves the headline.

## P0 corrections

### Exact binary geometry

Retained:

- the mirror-sample order-statistic characterization;
- the exact half-threshold criterion and its below-half condition;
- the calibration phase margin as a conditional diagnostic;
- the binary miscoverage identity.

Corrected:

- `m=0` and `m=1` are states of different calibration blocks. Their thresholds
  cannot be coupled through one common pair of fitted class maxima;
- for any common target and `c_L<c_H`, the exact coverage response is target mass
  in the two crossed score bands. It can be order one in the presence of atoms
  and is not a continuity theorem;
- score binning does not guarantee realized finite-bin prevalence ordering, a
  crossing of `alpha`, or any low-regime bin. A zero-positive-coverage conclusion
  additionally requires a target-support condition.

### Fixed-allocation outcome-free bounds

The proposed lower-endpoint-only funded-miscoverage floor was refuted by
`[l,u]=[0.6,1]`, which covers `Y=1`. The sharp outcome-free bounds over arbitrary
binary completions are instead:

- lower miscoverage: exposure in empty binary sets;
- upper miscoverage: all exposure except full binary sets.

Upper-endpoint saturation is retained only as the total-capital-normalized share
of exposure capable of covering a positive label. It is not conditional
positive-class coverage.

### Optimizer mechanism

The universal story that a plug-in objective anti-selects exactly the units able
to cover positives was removed. The plug-in coefficient decreases in the score
only ceteris paribus; contractual rates and constraints vary across loans, and
`u=1` depends on the stratum threshold. No global policy-direction theorem is
licensed.

### Proposition 4

The endpoint lemma is retained only under a unique optimal allocation on each
fixed-basis range and an exhaustive certified partition. The active solver-path
audit establishes neither. The unregistered midpoint affinity residual was
removed from the supplement because it proves neither uniqueness nor global
affinity.

## External V1 decision

Decision: **quarantine, not register**.

The V1 result preceded its purported protocol; Freddie fit and calibration were
not ordered temporal blocks; target support, target sets and target coverage were
not evaluated; both external models were logistic regressions; Prosper lacked a
defensible point-in-time endpoint and confirmed academic-use rights; and no input
hash/config/receipt/feature/taxonomy/environment lineage existed. The manuscript
paragraph, supplement appendix, publication entrypoint, runner, module, test, and
result JSON were removed. The stopped reasons and any requirements for an honest
future V2 are recorded in
`ijds_external_phase_replication_v1_quarantine_2026-07-26.md`.

## E-values decision

Decision: **do not add**.

Bonferroni and Holm already tolerate arbitrary dependence when the constituent
p-values and family are valid. E-values would not repair prior inspection, the
stronger joint-block null, or the absence of a one-future-point theorem-failure
claim; e-BH would change the target from FWER to FDR. Adding a calibrator after
inspection would create another post-hoc family without changing the active
conclusion.

## Narrative remediation

- Replaced “Vacuous by Construction” with an identification-audit title.
- Rewrote the abstract around exact geometry, 40/40 finite-archive bounds, the
  separately scoped 31/40 joint-block diagnostic, 216/216 broad envelopes
  crossing zero, and no selection.
- Restored a full Discussion that separates deterministic bounds, rank-reference
  diagnostics, design sensitivities, and comparator support.
- Added archive-specific threats: accepted-only population, endogenous platform
  signals, non-point-in-time servicing extract, descriptive drift, coarsened
  endpoint/payoff, and unresolved acquisition/licensing provenance.
- Removed the false funded floor, universal score-bin degeneracy, continuity,
  external replication, and optimizer-conflict narratives.

## Retained additions

- the exact crossed-band coverage identity and sharp empty/full-set
  fixed-allocation bounds;
- a quarantined, hash-indexed record of the V6 and post-freeze candidate replays,
  with no dependency from the active registry or evidence manifest;
- an anonymous deterministic machine-readable supplement, with the
  p-value-selected stratum fields removed;
- five learners as coverage controls, CatBoost only in the LP;
- two nonselective rulers, common-outcome bounds, and registered-support audit;
- exact rights/anonymity/raw-provenance blockers.

The all-candidate score-minus-outcome bounds, 200-row V6 census, resolved-panel
breakeven calculation, selected minimum-stratum magnitude, and adjacent-step
ranking remain candidate-only. They require new protocols and clean tagged
replays before paper-facing promotion.

## Current-version literature audit

The official full-text HTML for Zhao et al. v3 (revised 2026-07-09) and
Zhou--Zhu v3 (revised 2026-06-10) was audited after the local PDF-corpus pass.
The resulting manuscript boundary is deliberately narrower than either paper's
headline language:

- Zhao et al.'s general posterior guarantee freezes the optimized solution and
  uses a second i.i.d. calibration sample; it covers an offset constraint event.
  The original zero-threshold event needs the paper's additional quantile-shift
  conditions. No CPP certificate transfers to CRPTO's endpoint-weighted LP.
- Zhou--Zhu's central finite-sample statement is expected conservativeness for
  a prespecified robustness level. Its displayed frontier result assumes the
  coordinatewise inequalities it uses, and post-selection requires a held-out
  split. Version 3 corrects the split denominator but retains the empirical
  loss-bound heuristic and explicitly demonstrates that it can violate the
  theorem's bounded-loss contract. The weak-monotonicity/tied-coordinate Pareto
  issue and the duplicated Table 1 sensitivity block also remain.

This audit changes positioning, not the active method. It supports citing both
papers as adjacent conformal optimization constructions while expressly
withholding any funded-set, temporal-transport, or selected-policy guarantee.
The exact version adjudication and the remaining PDF-byte/visual-intake deficit
are recorded in
`conformal_optimization_v3_corpus_addendum_2026-07-26.md`.

## Verification state

- 29 claim contracts materialize successfully across body, supplement,
  registry, and claim matrix.
- 104 post-remediation real-assertion unit/contract tests pass in the
  protected-file-free geometry, post-freeze, claim-synchrony, ledger, ZIP, and
  PDF-freshness suite. In the broader run, 105 tests passed and fourteen were
  blocked at file open by the protected active evidence manifest; a separate
  ZIP-currency test is likewise blocked by protected S6B. Parquet-writing tests
  used an in-memory pickle transport shim because the assertion-enabled runtime
  lacks `pyarrow`; no production artifact was generated through that shim.
- Ruff lint passes over every changed Python implementation and test, and the
  formatter passes over 188 files. Three quarantined replay sources are
  formatter-excluded so their receipt-locked historical bytes remain intact;
  they remain included in lint.
- The official TeX regenerates byte-identically from the canonical QMD and no
  longer contains the quarantined diagnostics or external V1.
- The active abstract is a single paragraph of 287 words, leaving margin under
  the 300-word submission contract.
- The PDF cannot be rebuilt in this sandbox because TeX cannot read the two
  protected publication PNGs. The stale official PDF was removed by the failed
  rebuild, preventing accidental upload; body and supplement preview PDFs remain
  stale and must not be submitted.
- Two forbidden candidate table aliases and the stale active S6B/manifest remain
  physically protected under `reports/crpto`; source code and gates are corrected,
  but artifact regeneration/removal still requires write access to that root.
- Two new release tests now fail closed on the present tree: the deterministic
  reviewer ZIP exists but is not tracked, and the two quarantined publication
  aliases still exist. Clean-clone CI also verifies that the ZIP is tracked
  before comparing regenerated bytes.
- The current ZIP passes deterministic metadata, anonymity, census, and exact
  5-learner by 8-window multiplicity checks. Its byte equality with the final
  builder remains uncertified because protected S6B cannot be read here.
- The CRPTO skill has no required YAML front matter, remains stale at 29 tables,
  and contains quarantined and mathematically false support language. `.codex`
  is read-only in this execution environment, so skill validation and the
  inventory gate correctly remain red until that file is repaired.

## Page policy

Scientific editing has no active page limit. The ordinary `submission-check`
retains scientific, anonymity, PDF-layout, abstract, and build gates without a
page constraint. Page reduction is deferred until an explicit future freeze,
when `submission-freeze-check` activates the journal page gate.

## Human blockers before any public push or submission

1. Make the repository private and disable searchable Pages during
   double-anonymous review; verify from a signed-out session.
2. Confirm the actual raw-data acquisition source, date, and governing terms.
3. Resolve redistribution rights for raw and row-level derivatives.
4. Resolve the existing CC BY 4.0 content grant against the intended INFORMS
   copyright route.
5. Complete author, affiliation, conflict, funding, and disclosure sign-off.

These are not scientific tasks that code or another model run can certify.
