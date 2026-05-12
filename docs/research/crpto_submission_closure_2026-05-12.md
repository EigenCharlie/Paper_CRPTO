# CRPTO Submission Closure - 2026-05-12

This note closes the operational backlog for the current IJDS submission
package. It is intentionally narrow: it turns the existing CRPTO dossier into a
submission surface without reopening the champion or converting future-work
lanes into requirements.

## Scope Lock

Current paper:

- frozen `bound_aware_276k_economic_champion`;
- calibrated PD -> Mondrian conformal intervals -> robust portfolio decision;
- exact `alpha = 0.01` funded-set validation;
- `45/45` robust-region evidence;
- A3--A21 online supplement;
- regret-auditability frontier in the body/comparator section;
- OCE/CVaR and satisficing diagnostics in the supplement;
- cluster-aware dependence caveat/proposition in the theory supplement;
- Quarto/DVC/DagsHub/MLflow reproducibility story after anonymity handling.

Backlog for journal/follow-up, not blockers:

- OCE/CVaR or satisficing as a promoted optimized objective or hard
  portfolio-search constraint. The scoring scaffold now exists in
  `src/optimization/tail_satisficing_objective.py`, but it is not connected to
  champion promotion;
- MDCP, online conformal, online DFL, SPO+ + conformal hybrid, or causal CRPTO;
- dependence-aware main theorem without the cluster assumptions stated in the
  supplement;
- multi-dataset credit replication as a new external-validity experiment;
- P3 thesis/product tracks: multi-period portfolios, package extraction,
  multi-asset validation, field trial, production dashboard.

P2/P3 are therefore not a blanket exclusion anymore. The journal strengthening
pack enters when it is diagnostic, comparator framing, or a caveated theory
appendix based on frozen artifacts. Method-changing variants remain future work
and are not acceptance criteria for this submission.

## Implemented Submission Surfaces

| Surface | File | Status |
|---|---|---|
| IJDS body | `paper/CRPTO_ijds.qmd` | Active anonymous body source with regret-auditability framing. |
| IJDS supplement | `paper/supplement_ijds.qmd` | Active online supplement source for A3--A21, MRM/fairness and reproducibility. |
| Venue config | `configs/crpto_publication_targets.yaml` | IJDS primary, EJOR pivot, journal strengthening pack classified. |
| Release manifest | `book/chapters/14-release.qmd` | Body/appendix split, companion decision and release gates. |
| Backlog | `docs/research/crpto_backlog_2026-05-04.md` | Diagnostic pack included; method-changing P2/P3 remains backlog. |
| Future objective scaffold | `src/optimization/tail_satisficing_objective.py` and `configs/crpto_tail_satisficing_objective.yaml` | OCE/CVaR/satisficing scoring is implemented for future named experiments, not for the current champion. |
| Tail-satisficing audit | `reports/crpto/tables/crpto_tableA20_tail_satisficing_challenger_audit.csv` | Journal-only challenger audit over 45 alpha-safe policies; no promotion change. |
| Cluster-bound audit | `reports/crpto/tables/crpto_tableA21_cluster_bound_tightening.csv` | Dependence-aware Hoeffding calculation; transparent but not tighter than Markov here. |

## Final Submission Gates

Run before declaring a submission build ready:

```powershell
just lint
just smoke
just validate-champion
just paper-submission
uv run pytest tests/test_publication_targets.py -q
uv run dvc status --no-updates
```

Run only when DVC credentials are configured and anonymity policy permits
artifact disclosure:

```powershell
uv run dvc status -c -r dagshub
```

Final PDF production uses the official IJDS LaTeX template with
double-anonymous review settings. The public companion is disclosed according to
the IJDS data/code policy and the double-anonymous review process.

## Remaining Human-Facing Closeout

These are the real remaining tasks after the code/evidence pack is committed:

| Task | Owner | Blocking status |
|---|---|---|
| Final manuscript sweep for stale numbers, captions, appendix placement and IJDS length | author + agent | blocks submission PDF |
| Apply the official IJDS LaTeX template to the final `.qmd` export | author + agent | blocks submission PDF |
| Review anonymization for author names, GitHub, DagsHub and MLflow links | author + agent | blocks double-anonymous submission |
| Decide companion disclosure timing under IJDS policy | author | blocks final cover-letter/package wording |
| Create release tag and reproducibility bundle | author + agent | only after final PDF is ready |
| `dvc push` new non-frozen outputs | optional | only if remote sync is desired and credentials are available |
