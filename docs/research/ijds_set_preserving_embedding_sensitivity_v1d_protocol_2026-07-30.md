# IJDS set-preserving embedding sensitivity V1d recovery protocol (2026-07-30)

## Status and chronology

V1d is a retrospective, post-inspection, non-confirmatory successor to the V1c
NO-GO. Before V1d was locked, V1c had opened outcomes, completed the full Phase
B grid, and materialized nine local files. The exact V1c failure and inspected
facts are recorded in
`ijds_set_preserving_embedding_sensitivity_v1c_no_go_2026-07-30.md`. V1c has no
evaluation commit or tag, remains non-evidence, and its preserved local outputs
may not be reused by V1d.

V1d inherits the hash-bound V1a scientific sections and eleven Phase-A file
descriptors through the committed V1c base contract. It changes only successor
identity/transport, Windows preflight, and the Phase-B persistence contract
described below. It remains complete-grid and makes no selection, winner,
p-value, causal, conformal-repair, or confirmatory claim.

## Fresh Git-native authority

The only valid V1d chain is:

```text
P2 --single-parent direct child--> A2 --single-parent direct child--> B2
```

`P2` is the annotated V1d protocol tag. `A2` is a fresh annotated source tag
whose commit adds exactly the same eleven hash-pinned V1a files and no other
path; all eleven paths must be absent at `P2`. V1d rechecks the original V1a tag,
config/protocol blobs, freeze internals, schemas, runtime, complete Phase-A
science, worktree bytes, and Git blobs. It neither copies nor reads V1c Phase-B
outputs.

`B2` may add exactly the nine V1d outputs and no other path. Those paths must be
absent at `A2`. Both artifact tags must be annotated and both child commits must
have exactly one parent. DVC is not invoked. Runner-produced metadata says
`pending_git_artifact_commit_and_annotated_tag`; it records
`direct_child_required` and `annotated_tag_required`, never pre-attesting that a
future commit or tag already exists. A separate read-only verifier checks B2.

## Windows long-path preflight

The first V1c launch failed with Windows `MAX_PATH` before opening outcomes or
writing results; a later ephemeral long-path retry completed. On Windows, V1d
requires the effective Git `core.longpaths` value to be true before reading the
protected archive, constructing outcomes, or creating output directories. A
failed preflight stops the run without opening outcomes. Non-Windows platforms
record the check as not applicable. No absolute path is serialized.

## Persistence repair

The evaluated portfolio object produced by the shared evaluator has 50 columns.
`realized_payoff_exact` is undefined whenever positive funded exposure has an
unresolved endpoint. V1c observed 8,325 such rows and 9,675 resolved rows where
the exact value equaled both bounds. V1d validates that relationship in memory,
then removes `realized_payoff_exact` before persistence. It retains
`realized_payoff_lower` and `realized_payoff_upper`, the scientifically correct
identified set. The persisted evaluated table therefore has exactly 49 columns.

Every numeric field in all five persisted parquet outputs must be finite except
for this exact ruler-structural pattern in the evaluated table:

- `frontier_cap` is missing exactly for `objective_matched` rows;
- `objective_target` is missing exactly for `normalized_score` rows;
- `risk_tolerance` is missing exactly for `objective_matched` rows.

Each field has exactly 9,000 missing entries. The converse ruler entries must be
finite; infinity is never permitted. All numeric fields in monthly contrasts,
pooled contrasts, direction census, and outcome audit must be finite. Tests
mutate each persisted output with `NaN`/infinity and require failure.

As schema hardening, V1d also removes `period` from the pooled-window contrast
table. In V1c it was null in all 1,200 rows because a fifteen-month pooled scope
has no single month. Monthly contrasts retain `period`; pooled rows retain their
explicit `scope` and `window_id`. No sentinel period is introduced. The exact
persisted schema widths are 49, 40, 39, 16, and 7 columns for evaluated,
monthly, pooled-window, direction, and outcome-audit tables, respectively. All
persisted values outside the three declared evaluated structural fields must be
nonmissing, and every numeric value must be finite.
For each table, the V1c-inspected row census and complete ordered
column-name/dtype sequence are hash-bound in the V1d implementation and checked
both before writing and by the read-only B2 verifier against the Parquet files.

The raw and joined outcome objects may retain genuine unresolved
`snapshot_default` values in memory under the existing fail-closed binary/reason
parser. They are not persisted in the five parquet outputs. This exception does
not authorize any additional nullable numeric output.

## Estimands, outputs, and stop rules

All V1c/V1a scientific estimands remain unchanged: 18,000 primary portfolio
evaluations, 18,000 monthly contrasts, 1,200 pooled contrasts, 3,600 direction
rows, fifteen outcome-audit rows, fixed common capital `B`/`TB`, loan-wise
shared completions, and the complete gamma-zero control. The full joined table
is not written; its compact identity is retained.

Stop before outcomes on any source/tag/diff/hash/runtime/long-path failure. Stop
before writing on endpoint, complete-grid, fixed-capital, gamma-zero, census,
exact-column relationship, or numeric-finiteness failure. Stop on occupied V1d
output paths. After writing, repeat source/raw/Git TOCTOU gates and verify the
exact nine-file census. V1d remains non-evidence until B2 and its annotated tag
pass the separate verifier and any later claim-promotion decision is explicit.
