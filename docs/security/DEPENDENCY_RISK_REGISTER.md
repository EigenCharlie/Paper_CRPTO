# Dependency Risk Register

This register records known dependency advisories that cannot yet be removed
without breaking an active reproducibility contract. `just dependency-audit`
ignores only the identifiers listed here; any newly reported advisory fails.

## Active Exceptions

| Advisory | Dependency path | Exposure in CRPTO | Current control | Removal condition |
| --- | --- | --- | --- | --- |
| `PYSEC-2026-2447` (`GHSA-w8v5-vhqr-4h9v`) | `DVC -> dvc-data -> diskcache 5.6.3` | Unsafe pickle deserialization if an attacker can write the local DVC cache. DVC is tooling, not part of the scientific runtime. | DVC lives in the `repro` dependency group. Use only the authenticated project remote and never reuse an untrusted `.dvc/cache`. | Upgrade when DiskCache or DVC publishes a patched compatible release. |
| `PYSEC-2026-1806` (`GHSA-8qvm-5x2c-j2w7`) | `OptBinning -> OR-Tools 9.11 -> protobuf 5.26.1` | Denial of service while parsing adversarial recursive protobuf messages in the pure-Python backend. CRPTO uses CPython wheels, passes local numeric solver models, and does not parse external protobuf payloads. | OR-Tools is used only for declared scorecard/cross-solver controls. Inputs are repository-validated arrays and tables. | Move to patched protobuf after OptBinning supports a compatible OR-Tools release and scorecard parity is demonstrated under a new protocol. |
| `PYSEC-2026-1805` (`GHSA-7gcm-g887-7qv7`) | `OptBinning -> OR-Tools 9.11 -> protobuf 5.26.1` | Denial of service through deeply nested `Any` messages. The affected parser is not used by CRPTO. | Same isolation and trusted-input boundary as above. | Same compatibility and scientific-parity condition as above. |

## Environment Separation

- `uv sync --no-dev` installs the current scientific runtime without DVC,
  test runners, or author tooling.
- `uv sync --group repro` adds DVC and the authenticated S3 capsule tools.
- `uv sync --group dev` composes test, quality, and reproducibility groups for
  author validation.

The portfolio optimizer uses direct HiGHS interfaces (`highspy` in the active
path and SciPy HiGHS as a fallback). Historical Pyomo and cuOpt compatibility
layers are intentionally absent from the environment.

Do not force a protobuf override. OR-Tools 9.11 constrains protobuf below the
patched line, and OptBinning 0.21 constrains OR-Tools below 9.12. A forced
resolution would be neither dependency-safe nor a valid replay environment.
