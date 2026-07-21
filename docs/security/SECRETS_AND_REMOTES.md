# Secrets And Remotes

CRPTO uses GitHub for source and DagsHub S3-compatible storage for DVC
artifacts. Credentials are local or GitHub Actions secrets; they never belong
in tracked files.

## Local Variables

Keep credentials in an ignored `.env` or in the current PowerShell process:

```powershell
$env:DAGSHUB_USER = "..."
$env:DAGSHUB_TOKEN = "..."
$env:DAGSHUB_REPO = "Paper_CRPTO"
$env:AWS_ACCESS_KEY_ID = $env:DAGSHUB_TOKEN
$env:AWS_SECRET_ACCESS_KEY = $env:DAGSHUB_TOKEN
$env:AWS_ENDPOINT_URL = "https://dagshub.com/EigenCharlie94/Paper_CRPTO.s3"
```

Do not print tokens into logs or place them in `.dvc/config`, YAML, Python,
paper sources, or submission forms. Machine-specific DVC configuration belongs
in ignored `.dvc/config.local`.

## Active DVC Capsule

The source registry declares exactly 33 DVC pointer files. Use the capsule manager
instead of an unrestricted historical replay:

```powershell
just ijds-pull
just ijds-dvc-status
just ijds-dvc-verify-remote
```

The historical `dvc.yaml` graph is sealed compatibility metadata. Never run its
protected PD, conformal, validation, portfolio, or exact-evaluation stages
without explicit permission.

## GitHub Actions

The manual full workflow requires `DAGSHUB_USER`, `DAGSHUB_TOKEN`, and
`DAGSHUB_REPO` repository secrets. It installs the locked development
environment with:

```powershell
uv sync --group dev --frozen
```

Secret scanning and dependency alerts should remain enabled. A leaked token
must be revoked first, then removed from Git history if it was committed.
Known transitive dependency exceptions are reviewed in
`docs/security/DEPENDENCY_RISK_REGISTER.md`; unregistered advisories fail
`just dependency-audit`.
