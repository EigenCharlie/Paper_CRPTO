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
- A3--A18 online supplement;
- Quarto/DVC/DagsHub/MLflow reproducibility story after anonymity handling.

Not current paper:

- P2 methodology extensions: OCE/CVaR objective, MDCP, online conformal,
  online DFL, SPO+ + conformal hybrid, dependence-aware main theorem,
  multi-dataset replication, regret-auditability frontier.
- P3 thesis/product tracks: multi-period portfolios, causal CRPTO, package
  extraction, multi-asset validation, field trial, production dashboard.

P2/P3 items may appear in discussion and future work. They are not acceptance
criteria for this submission.

## Implemented Submission Surfaces

| Surface | File | Status |
|---|---|---|
| IJDS body | `paper/CRPTO_ijds.qmd` | Active anonymous body source with P2/P3 boundary. |
| IJDS supplement | `paper/supplement_ijds.qmd` | Active online supplement source for A3--A18, MRM/fairness and reproducibility. |
| Venue config | `configs/crpto_publication_targets.yaml` | IJDS primary, EJOR pivot, P2/P3 excluded from current paper. |
| Release manifest | `book/chapters/14-release.qmd` | Body/appendix split, companion decision and release gates. |
| Backlog | `docs/research/crpto_backlog_2026-05-04.md` | P2/P3 explicitly demoted to future work. |

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
