# Dependabot Triage

Date: 2026-07-02

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

Dependabot may continue showing the old alerts until the branch is pushed and
GitHub refreshes the dependency graph.

## Residual Notes

- `diskcache` alert #1 was already dismissed upstream; no local change made.
- This triage intentionally avoids changing paper claims, model artifacts, or
  canonical scientific outputs.
- If GitHub still reports an alert after push, re-run the API query and compare
  the manifest path and resolved version in `uv.lock` before making a new
  dependency change.
