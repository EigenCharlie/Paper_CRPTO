# IJDS Data and Code Disclosure Form Draft

Use the official IJDS form in ScholarOne. This file supplies consistent draft
language and is not a substitute for the publisher's form.

Official policy:
<https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>

## Proposed Disclosure Position

- **Code:** release at acceptance. Include the Python source, experiment and
  evidence builders, tests, manuscript sources, environment lock, task runner,
  DVC metadata, and exact reproduction commands.
- **Derived evidence:** release at acceptance. Include publication CSV/TeX
  tables, figures, evidence manifest, protocol config, execution receipt, and
  artifact hashes.
- **Large processed/model artifacts:** provide through the configured DVC
  remote or a journal-approved archive, with immutable pointers and checksums.
- **Raw Lending Club data:** do not place in Git. Provide source/acquisition
  instructions, expected filename/schema, size, SHA-256, and the deterministic
  reconstruction command, subject to the source's redistribution terms.
- **Review-stage verification:** provide an anonymized archive or controlled
  access if requested by the editor.

## Short Disclosure Statement

This computational paper uses a public-source Lending Club research snapshot,
versioned derived data, a tagged model/result bundle, and reproducible Python
code. During double-anonymous review, author-identifying repository and remote
details are withheld. At acceptance, the author will release source code,
manuscript sources, the locked environment, publication tables and figures,
the active protocol and execution receipt, artifact hashes, DVC pointers, and
instructions for obtaining and reconstructing the raw data. Large files will
be distributed through DVC or a journal-approved archive when redistribution
terms permit.

## Active Data Contract

| Component | Role | Availability plan |
|---|---|---|
| Lending Club 2007--2020Q3 snapshot | Main 540,121-row status-independent universe | Source instructions, schema, expected size/hash; raw file excluded from Git |
| Versioned processed experiment directory | Candidate panels, predictions, monthly allocations and audits | DVC pointer and remote/archive |
| Versioned model/results directory | Model, calibrator, conformal recipe, summary and receipt | DVC pointer and remote/archive |
| Publication evidence | Four compact main-table exports, S1--S7, four figures, 30-output evidence JSON | Git/reproducibility archive |

Prosper, Freddie/Mendeley, Home Credit, and historical A1--A40 artifacts are
not evidence for the active manuscript. They need not be part of the minimal
IJDS reproduction capsule unless the editor requests project-history material.

## Code Contract

The accepted package should include:

- `src/data/outcome_observability.py`;
- `src/models/maturity_safe_pd.py` and
  `src/models/binary_conformal_guardrail.py`;
- `src/evaluation/standardized_credit_payoff.py`,
  `policy_contrast_bounds.py`, `coverage_transport.py`, and
  `maturity_safe_portfolio.py`;
- `src/utils/isolated_experiment.py`;
- `scripts/experiments/run_ijds_maturity_safe_challenger.py`;
- `scripts/build_ijds_maturity_safe_evidence.py`;
- focused and publication-sync tests;
- `pyproject.toml`, `uv.lock`, `justfile`, and DVC metadata; and
- body, supplement, official TeX, bibliography, and submission instructions.

## Reproduction Commands

```powershell
uv sync --extra dev
uv run dvc pull data/processed/experiments/champion_reopen/champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2.dvc
uv run dvc pull models/experiments/champion_reopen/champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2.dvc
just ijds-evidence
uv run pytest tests/test_ijds_active_claim_sync.py -q
just paper-submission
just paper-submission-official
just validate-champion
```

The default reproduction rebuilds evidence from the immutable tagged run. It
does not rerun expensive methodology or historical protected stages. A full
experiment replay is available in a clean clone with an absent output path and
the raw source, using the locked v2 config.

## Protected Historical Boundary

The following stages are not routine reproduction steps because they overwrite
the manifest-protected historical chain:

```text
crpto.pd.champion
crpto.conformal.intervals
crpto.conformal.validation
crpto.portfolio.optimization
crpto.portfolio.bound_exact_eval
```

The active v2 experiment is separate from those paths. Neither the disclosure
form nor a reviewer request should be interpreted as permission to regenerate
protected outputs in place.

## Anonymous Review

Remove author names, repository ownership, personal URLs, local paths,
credentials, and non-anonymous DVC remote details from any review-stage archive.
Keep the protocol tag, content hashes, schemas, and relative paths so the editor
can verify integrity without learning author identity.
