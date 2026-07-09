# IJDS simplification and cleanup audit - 2026-07-06

> Certificate metrics in this historical cleanup memo were superseded on
> 2026-07-09 by `pool93_certificate_semantics_v2_2026-07-09.md`. The cleanup
> decisions remain valid; the active paper uses the policy-aware A35 frontier
> and matched point-PD baseline A40.

Scope: body manuscript, IJDS submission `.tex`, online supplement, code
refactor posture, and local repository weight. This memo follows the
2026-07-05 full audit but focuses on reader-facing parsimony: remove technical
runbook language from the paper body unless it protects a claim the reviewer
must understand.

## 1. Reader-facing prose decision

The body paper should speak in paper language:

- selected policy, selected decision, declared finite-grid frontier;
- frozen PD model, conformal intervals, robust portfolio decision;
- traceability, validation harness, governance files when needed.

The body paper should avoid internal run labels unless a number cannot be
understood otherwise:

- `pool93` as a prose label;
- A35--A39 as the main way to describe a body-level concept;
- `sidecars`, `artifact paths`, script names, test filenames, exact DVC
  implementation details;
- "bit-exact" as a rhetorical claim. The scientific point is narrower:
  retraining is a new research run, not the routine reproduction target.

Where those details belong:

- online supplement: appendix labels, table provenance, guardrails, DVC/manifest
  boundary, reproduction commands;
- submission package docs: raw-data permanence, DVC sanitization, code/data
  timing, ScholarOne checklist;
- code/tests/docs: exact file names and hash gates.

## 2. Changes applied in this pass

- Rewrote the body and `.tex` abstract/introduction language from
  "selected pool93 body point" to "selected policy" where the run label did not
  help the reader.
- Replaced the small Table 10 with a reviewer-question table:
  "Reviewer question / Body answer / Boundary".
- Removed `\resizebox{\textwidth}{!}` from the official `.tex` Table 10 and
  replaced it with wrapped `p{}` columns at `\small`, so the table no longer
  shrinks to unreadable text.
- Simplified the reproducibility body paragraph: the body now says that frozen
  inputs regenerate the paper surfaces, claim-sync tests protect body numbers,
  and retraining is a new research run. The detailed DVC/hash/drift language
  remains for the supplement and package docs.
- Softened supplement framing where it introduced A35--A39 with too much
  `pool93` terminology. The detailed appendix rows now use reader-facing
  `selected-policy` language while retaining source filenames where traceability
  matters.
- Removed rhetorical uses of `artifact` from the body, submission `.tex`, and
  supplement. The paper now uses "model", "evidence", "files", "outputs", or
  "reproducibility bundle" unless a package/debug context genuinely needs
  implementation language.
- Recompiled the official INFORMS-style `.tex` and visually checked page 20:
  Table 10 is readable, wrapped, and ragged-right rather than compressed by
  `resizebox`.

## 3. Code/refactor assessment

Current evidence does not support a broad code refactor before submission:

- The 2026-07-05 audit already closed the safe refactor lanes and reported no
  AI-slop/dead-code pattern in live code.
- The largest files are mostly search or paper-generation entrypoints:
  `scripts/train_pd_model.py`, `scripts/generate_conformal_intervals.py`,
  `scripts/search/run_portfolio_bound_aware_search.py`,
  `scripts/search/run_pool93_ijds_local_refinement.py`, and
  `scripts/search/run_regret_auditability_sandbox.py`.
- Splitting those files further would improve aesthetics, but it does not
  simplify the IJDS claim unless the claim itself changes.

The important distinction:

- If the goal is "same paper claim, cleaner code", drift-gate should remain
  strict. Otherwise a "refactor" can silently become a different empirical
  result.
- If the goal is "simpler claim and simpler code, small metric changes allowed",
  that is no longer a refactor. It is a new research run and should get a new
  run tag, a simpler claim target, and a new evidence bundle.

Recommended new-run shape if Carlos chooses that route:

1. Declare a simpler target before running: for example, "one selected policy
   family, one alpha level plus sensitivity grid, no pool93 local-refinement
   narrative in the body."
2. Write outputs under a new experiment path; do not overwrite the current
   frozen A35--A39 or model/conformal artifacts.
3. Compare against the current selected policy on: return, `V(0.01)`,
   `Gamma_CP`, `Gamma_res`, exact loss threshold, realized risk-tolerance
   excess, table/page simplicity, and code-path length.
4. Promote only if the paper becomes materially simpler or the result is
   materially easier to defend. A few basis points of metric loss may be fine,
   but only if the new claim is easier to explain.

## 4. Local repository weight

Before cleanup the workspace was roughly 24.8 GB. Safe cleanup performed:

- removed `.venv-champion-search` (~6.0 GB);
- removed `.venv-tabpfn` (~4.9 GB);
- removed local caches: `.mypy_cache`, `.pytest_cache`, `.ruff_cache`,
  `.hypothesis`, `.codex_tmp`;
- ran `git gc`, reducing `.git` from ~1.66 GB of loose objects to ~30 MB.

After cleanup the workspace is roughly 12 GB. Remaining expected weight:

| Path | Approx. size | Recommendation |
|---|---:|---|
| `data/` | 5.0 GB | Keep for local reproduction unless DVC remote availability is verified. |
| `.dvc/` | 2.8 GB | Keep for offline DVC cache; run `dvc gc` only after deciding what historical outputs can be dropped. |
| `models/` | 1.8 GB | Keep; contains frozen model/governance/search evidence. |
| `.venv/` | 1.6 GB | Keep; active project environment. |
| `reports/` | 0.3 GB | Keep; paper tables/figures/MRM outputs. |
| `Papers_tesis/` | 0.18 GB | Optional local literature cache; ignored by Git. |

Do not use broad `git clean -fdX` in this repo: it would delete DVC-tracked
data/model material, local templates, and ignored PDFs.

## 5. Current recommendation

For IJDS submission, continue with the current frozen claim but make the body
more reader-facing. The immediate acceptance risk is not code complexity; it is
overloading the body with internal labels. A new tolerant run is worth doing
only if Carlos wants to simplify the actual claim, not merely the code around
the existing claim.
