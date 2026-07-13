# IJDS Tooling and Refactor Decisions

This is the live engineering contract for the IJDS paper, updated July 13,
2026. Scientific claims are governed only by
`docs/research/active_claims_2026-07-12.md`; historical selected-policy designs
remain provenance, not alternate execution paths.

## Objective

Maintain one auditable route from the immutable V4 and two-ruler
freeze/evaluation pairs to one evidence manifest and one manuscript. Prefer
explicit modules and named commands over parallel implementations, hidden
manuscript-time computation, or frameworks that do not improve validity.

## Adopted Tools

| Tool | Role | Decision |
|---|---|---|
| `uv` | Python environment, lockfile, commands | Sole Python package/runtime interface; use `--frozen` for reproduction. |
| Ruff | lint and formatting | Sole linter and formatter. |
| mypy | stable gradual type gate | Required over `src`, `scripts`, and `tests`. |
| ty | independent type audit | Full scope is a zero-diagnostic submission gate. |
| pytest | behavior and claim synchronization | Focused, smoke, and full suites. |
| just | human-facing command menu | Sole task runner and Windows-first entry point. |
| DVC | immutable experiment lineage | Eight active pointers for two freeze/evaluation pairs; never a substitute for protocol declarations. |
| pre-commit + prek | local hook compatibility | One shared hook policy, not two sets of checks. |
| pdoc | optional API browsing | Ephemeral only; no project dependency or publication artifact. |

`ty` complements mypy and is pinned to `0.0.59`. Every unsuppressed diagnostic
is blocking in the full scope. One per-file override suppresses ty's pandas
stub false positive for the final `Series.any()` reduction in protocol-hashed
`src/ijds_challengers/evaluation.py`; mypy strict and runtime tests still cover
that expression. The current locked environment has one accepted audit finding:
DVC's transitive
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

1. `src/ijds_audit/` contains the immutable V4 data, prediction, binary
   geometry, allocation, exact-frontier, bound, and protocol implementation.
2. `scripts/experiments/run_ijds_binary_geometry_frontier_v4.py` is the locked
   two-phase V4 entry point. Its source inventory is recorded in the V4 freeze.
3. `src/ijds_challengers/` contains the two outcome-free rulers and verified
   endpoint-evaluation helpers.
4. `scripts/experiments/run_ijds_normalized_objective_frontier.py` created V1c;
   `run_ijds_normalized_objective_frontier_v2.py` verified its hashes before the
   single archive-outcome join.
5. `scripts/build_ijds_binary_geometry_frontier_v4_evidence.py` validates both
   immutable lineages and emits the sole manifest, six CSVs, and six figure
   files used by the paper.
6. `paper/CRPTO_ijds.qmd` is canonical. The official TeX is generated and never
   edited as a second manuscript.

The four active tags are the V4 `v1`/`v2` and two-ruler `v1c`/`v2` tags named in
the claim registry. None may be overwritten. A changed scientific object needs
a declared protocol, new run tag, new paths, and complete reconciliation.

## Deliberate Simplifications

- Five score strata are fixed before OOT; all eight residual windows and both
  learners are complete coverage specifications, not votes.
- The complete gamma path is retained. Two outcome-free rulers and three
  interior coordinates define six endpoint tracks; none is selected.
- Objective matching controls model-implied opportunity cost. Normalized-score
  matching is positive-affine invariant but does not equalize that cost.
- The nine fixed-cap policies and C0/C1/C2 are supporting diagnostics, not a
  closed or co-primary promotion family.
- Exact HiGHS basis endpoints evaluate the declared point-cap supports without
  claiming a continuous joint frontier for both rulers.
- Unresolved outcomes receive sharp common-outcome bounds rather than
  complete-case deletion or a missing-at-random assumption.
- One evidence builder produces six CSVs, six figure files, and one manifest.
- One QMD body generates the official TeX; the supplement remains a separate
  anonymous source.
- Compact-v7, P1/C1, pool93, Prosper/Freddie, Markov, and A1--A40 are not
  active fallbacks.

## Architecture Audit, July 13

The repository is large because it preserves research history, but the active
method is bounded. The measured tree has 89 Python files/20,104 lines under
`src`, 101/54,015 under `scripts`, and 119/14,409 under `tests`; the two active
packages contain 18 files/5,032 lines. Radon analyzed 161 active blocks with
mean complexity `A (4.88)`, and Vulture found no dead code in the active
packages and entry points.

The remaining C/D hotspots mostly live in source inventories already hashed by
V4 or V1c. Reformatting or splitting those functions would require a new run
without changing the estimand. They therefore remain intact. The mutable
orchestration was simplified instead:

- `ijds-active-check` now verifies all eight DVC pointers and both locked pairs;
- the daily ty scope includes V4/V1c/V2 and excludes retired challengers;
- strict mypy covers every active challenger module and every mutable
  paper-facing entry point; three NumPy-return hotspots remain under the typed
  body gate because their V4 source hashes are frozen;
- pdoc targets the active audit/frontier APIs rather than the old champion;
- `configs/crpto_publication_targets.yaml` records the small operational
  surface and points to the immutable source inventories.

`uv.lock` resolves cleanly. Current direct scientific versions are retained:
CatBoost and HiGHS are at the tested releases, while pandas 3, PyArrow 25,
OR-Tools 9.15, and mypy 2 are major environment changes. Upgrading them inside
an already evaluated protocol would weaken reproducibility and offers no claim
improvement. Such an upgrade is a new-run sensitivity, not invisible
maintenance. The 34 default dependencies remain broad because full historical
tests import them; splitting extras now would move complexity into CI and setup
without shrinking the immutable reviewer evidence. The active code surface,
not package count, is the capsule boundary.

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

`just ijds-active-replay` verifies V4 plus the locked V1c/V2 diagnostic and
rebuilds publication evidence; it does not rerun either expensive allocation
protocol. `just submission-check` is the complete ordinary pre-freeze gate.
Protected historical DVC stages are never hidden behind either command.

## Compilation Contract

The official build generates TeX from `paper/CRPTO_ijds.qmd`. On Windows it
invokes TinyTeX's `latexmk.pl` payload through Perl, bypassing the fragile
`runscript.tlu` wrapper. If that route is unavailable or fails, the robust
fallback is:

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
