# Dependabot Triage

Date: 2026-07-02

Follow-up: 2026-07-11

GitHub Dependabot reported open alerts against `uv.lock`. These are
security/dependency-maintenance items, not scientific-result blockers. The
paper artifacts and champion metrics do not depend on notebook server exposure
or authenticated web services.

## Local Lockfile Remediation

The lockfile was updated with:

```bash
uv lock \
  --upgrade-package pydantic-settings \
  --upgrade-package msgpack \
  --upgrade-package jupyterlab \
  --upgrade-package jupyter-server \
  --upgrade-package starlette \
  --upgrade-package cryptography \
  --upgrade-package tornado \
  --upgrade-package aiohttp \
  --upgrade-package torch
```

Resolved local versions:

| Package | Updated version |
|---|---:|
| `aiohttp` | `3.14.1` |
| `cryptography` | `48.0.1` |
| `jupyter-server` | `2.20.0` |
| `jupyterlab` | `4.6.1` |
| `msgpack` | `1.2.1` |
| `pydantic-settings` | `2.14.2` |
| `starlette` | `1.3.1` |
| `torch` | `2.12.1` |
| `tornado` | `6.5.7` |

The 2026-07-11 follow-up closed three newly reported high-severity alerts with
the narrowest transitive lock updates:

| Package | Previous | Resolved | Alert class |
|---|---:|---:|---|
| `mistune` | `3.2.1` | `3.3.3` | Quadratic-time link-text parsing |
| `soupsieve` | `2.8.3` | `2.8.4` | Selector-parser ReDoS and memory exhaustion |

The full IJDS submission gate passed with these versions installed.

Dependabot may continue showing the old alerts until the branch is pushed and
GitHub refreshes the dependency graph.

## Residual Notes

- `pip-audit` still reports `CVE-2025-69872` for `diskcache 5.6.3`, with no
  patched release available. CRPTO does not import it; it is pulled only by
  `dvc-data -> dvc`. Exploitation requires an attacker to write a malicious
  pickle into the victim's local DVC cache before it is read. This single-user,
  nonservice research repository keeps `.dvc/cache` local and ignored and does
  not grant untrusted writers access to it, so the residual risk is accepted
  until DVC removes the dependency or a patched `diskcache` is published.
- The residual scan is reproducible with
  `uv run --with pip-audit pip-audit --progress-spinner off`; use
  `--ignore-vuln CVE-2025-69872` only after reviewing the threat-model note
  above, not to conceal a newly actionable finding.
- This triage intentionally avoids changing paper claims, model artifacts, or
  canonical scientific outputs.
- If GitHub still reports an alert after push, re-run the API query and compare
  the manifest path and resolved version in `uv.lock` before making a new
  dependency change.
