# IJDS Fable 51 Execution Record — 2026-09-01

## Status and precedence

This file records implementation dispositions; it is not a protocol, claim
source, or evidence source. The attached Fable 51 audit and improvement plan is
a non-authoritative proposal. `AGENTS.md`, `CLAUDE.md`, the active claim
registry and ledger, exact-theory notes, sealed protocols, the active-source
registry, and registered evidence retain precedence.

Preflight began from `main` at `9db690f`, with four pre-existing modified
surfaces and the attached plan untracked. Those edits were preserved. Two
registered DVC summaries were unavailable locally; `dvc pull` could not use the
configured remote because credentials were unavailable. No number was
reconstructed or copied to replace either missing artifact.

## Phase dispositions

### Phase 0 — surface closure

- Accepted: distinguish physical freezes from logical target-outcome nonuse and
  expose the distinction in Supplement Table S10A.
- Corrected rather than accepted: the proposal classified the Label-Mondrian
  and fit-label-completion wording as overstated physical isolation. The sealed
  Label-Mondrian protocol requires physically separate F1/E1 stages, forbids F1
  from loading the raw archive or evaluation endpoint, and hash-binds E1 to F1.
  The fit-label runner likewise writes and verifies a separate freeze before
  reconstructing the endpoint in its evaluator. Their physical evaluation
  boundaries remain described as retrospective, not pristine prospective
  holdouts.
- Accepted: the closed calibrator-family scan has only logical target-outcome
  nonuse because its raw reader encounters chunks containing status values
  before retaining the locked 2011 IDs.
