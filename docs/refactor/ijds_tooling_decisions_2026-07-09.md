# IJDS Tooling and Refactor Decisions

This is the live engineering contract for the IJDS paper. Scientific claims
are governed only by `docs/research/active_claims_2026-07-12.md`; historical
selected-policy designs remain available in Git history, not in this workflow.

## Objective

Maintain one auditable route from immutable V1/V2 experiment artifacts to the
submitted evidence and manuscript. Prefer explicit modules and named commands
over parallel implementations, hidden manuscript-time computation, or new
frameworks that do not improve scientific validity.

## Adopted Tools

| Tool | Role | Decision |
|---|---|---|
| `uv` | Python environment, lockfile, commands | Sole Python package/runtime interface; use `--frozen` for reproduction. |
| Ruff | lint and formatting | Sole linter and formatter. |
| mypy | stable gradual type gate | Required over `src`, `scripts`, and `tests`. |
| ty | independent type audit | Full scope is a zero-diagnostic submission gate. |
| pytest | behavior and claim synchronization | Focused, smoke, and full suites. |
| just | human-facing command menu | Sole task runner and Windows-first entry point. |
| DVC | immutable experiment lineage | Six active V1/V2/V3 pointers; never a substitute for protocol declarations. |
| pre-commit + prek | local hook compatibility | One shared hook policy, not two sets of checks. |
| pdoc | optional API browsing | Ephemeral only; no project dependency or publication artifact. |

`ty` complements mypy. Its full scope has no frozen exceptions: every
diagnostic is blocking. The current
locked environment has one accepted audit finding: DVC's transitive
`diskcache 5.6.3` is affected by `CVE-2025-69872`, with no fixed release. Its
local-write threat model and mitigations are recorded in
`docs/security/DEPENDABOT_TRIAGE_2026-07-02.md`.

## Rejected Additions

| Tool | Decision | Reason |
|---|---|---|
| Pyrefly | Do not adopt | Duplicates two type checkers and adds migration noise without improving the evidence contract. |
| Commitizen | Do not adopt | Commit-message automation does not improve a single-author scientific release. |
| Permanent pdoc dependency | Do not adopt | Local API browsing is useful, generated API pages are not part of the paper. |
| A second task runner | Do not adopt | `just` already exposes the complete workflow. |
| Automatic semantic versioning | Do not adopt | Run tags, commits, DVC hashes, and evidence hashes are the scientific identifiers. |

## Active Methodology Path

1. `src/data/outcome_observability.py` defines label availability and keeps
   outcome fields outside allocation inputs.
2. `src/models/binary_conformal_guardrail.py` constructs the fixed score
   taxonomies and binary residual intervals.
3. `src/evaluation/maturity_safe_portfolio.py` defines coherent standardized
   payoff and sharp common-outcome bounds.
4. `src/evaluation/comparator_audit.py` implements C0, C1, exact C2, the
   point-cap frontier, and direction envelopes.
5. `src/evaluation/comparator_transport_simulation.py` isolates temporal
   transport, comparator matching, clipping, and taxonomy mechanisms.
6. `scripts/experiments/run_ijds_fixed_taxonomy_c2.py` created the immutable
   outcome-free V1 allocation capsule; its locked resume branch verifies V1
   hashes and performs the vectorized V2 outcome join without changing
   allocations.
7. `scripts/build_ijds_fixed_taxonomy_c2_evidence.py` validates both capsules
   and generates every paper-facing table, figure, and manifest entry.

The active tags are `ijds-fixed-taxonomy-c2-2026-07-11-v1` and
`ijds-fixed-taxonomy-c2-2026-07-11-v2`. Neither may be overwritten. A new
scientific result requires a new declared protocol, run tag, and output path.

## Deliberate Simplifications

- Four taxonomies fixed before OOT; the five-group recipe is canonical but not
  selected by OOT performance.
- Nine guardrails are co-primary; there is no policy selector or winner.
- Point PD remains the economic objective; the conformal score appears only in
  the risk constraint.
- C0 is a same-cap nesting control, C1 is a fixed development comparator, and
  C2 exactly matches the funded point-PD moment for each guardrail-month.
- A finite 29-cap frontier tests comparator dependence without claiming
  invariance over every conceivable baseline.
- Unresolved outcomes receive sharp common-outcome bounds rather than
  complete-case deletion or a missing-at-random assumption.
- One evidence builder produces 62 table/figure files plus one manifest.
- One QMD body generates the official TeX; the supplement remains a separate
  anonymous source.
- Compact-v7, P1/C1, pool93, Prosper/Freddie, Markov, and A1--A40 are not
  active fallbacks.

## Named Commands

```powershell
just ijds-evidence
just ijds-active-replay
just publication-integrity
just lint
just type-check
just type-advisory-full
just test
just validate-champion
just validate-champion-strict
just drift-gate
just paper-submission-pdf
just paper-submission-official
just submission-check
```

`just ijds-active-replay` validates V1/V2/V3 and rebuilds publication evidence; it
does not rerun the expensive allocation protocol. `just submission-check` is
the complete ordinary pre-freeze gate. Protected historical DVC stages are
never hidden behind either command.

## Compilation Contract

The official build generates TeX from `paper/CRPTO_ijds.qmd` and invokes the
TinyTeX `latexmk.pl` payload through Perl. If that payload is unavailable, the
robust fallback is:

```text
pdflatex -> bibtex -> pdflatex -> pdflatex
```

The first pass writes `.aux`, BibTeX writes `.bbl`, and the final two passes
resolve citations, cross-references, floats, and pagination. This is one
compilation workflow, not three independent builds.

## Drift Policy

Experimental drift is allowed only under a new run tag. Promotion requires a
scientific reason, an outcome-free protocol, new paths, complete reporting,
claim-sync tests, `just validate-champion`, and `just drift-gate` whenever PD
or conformal code changes. Light drift is not itself a benefit.

Protocol-frozen V1 hotspots are not refactored merely to lower complexity or
silence a type checker. A refactor that changes their source hash requires a
new full run and must offer methodological value commensurate with that cost.
