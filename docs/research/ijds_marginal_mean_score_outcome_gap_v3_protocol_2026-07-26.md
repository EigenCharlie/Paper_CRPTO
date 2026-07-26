# IJDS Marginal Mean-Score--Outcome Gap V3 Protocol

Required protocol tag:
`protocol/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3`.

Required post-DVC artifact tag:
`artifacts/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3`.

Required run:
`ijds-marginal-mean-score-outcome-gap-2026-07-26-v3`.

Status: **retrospectively locked runtime, row-identity, and portability
recovery before V3 execution**.

The five scores, endpoint counts, V2 intervals, and their signs have already
been inspected. V3 is not preregistration, confirmation, an untouched holdout,
or an independent replication. No scientific result, including its sign or
learner ordering, is an execution, retention, or promotion condition.

## 1. Why V2 is quarantined

V2 retains correct arithmetic but cannot serve as active lineage. Its protocol
authorized only `uv run --locked python`, while its receipt records execution
under `calibre-debug.exe`. Hashing `uv.lock` did not prove that the authorized
launcher was used. V2 also compared score IDs only to themselves: its outcome
source was an aggregate reason table, so it did not establish that the
resolved and unresolved counts belonged to the exact same 376,890 score IDs.
Its transitive implementation closure, terminal Git/source revalidation, and
DVC portability were incomplete.

V3 imports no V2 output. It preserves the estimand, complete learner census,
endpoint rule, completion class, formulas, and no-sign-stop rule, while
reconstructing the outcome panel directly from the hash-pinned raw archive.
V2 remains immutable quarantine provenance.

## 2. Fixed scientific question and complete census

For each of the five frozen learners, V3 reports the finite-archive mean
score-minus-outcome interval on the complete status-independent primary OOT
population:

1. `catboost_platt`;
2. `numeric_logistic_platt`;
3. `catboost_monotonic_platt`;
4. `woe_scorecard_platform_platt`; and
5. `woe_scorecard_borrower_platt`.

No learner is selected, ranked, refit, recalibrated, rescaled, or passed to an
optimizer. Candidate membership uses only 36-month term and issue month from
April 2016 through June 2017. Loan status, last-payment date, score value, and
outcome resolution never determine membership.

The locked target contains `N=376,890` unique IDs in all fifteen declared
months. Its pre-inspection score-ID hash is
`72799b236a7e45d8746099adefba7da5683e8308959643d6ad341d3585e8fa74`.

## 3. Hash-pinned sources and population identity

The configuration pins path, bytes, and SHA-256 for:

- the V1b outcome-free credit-control freeze and five-score Parquet;
- both V1b data/model DVC pointers;
- `data/raw/Loan_status_2007-2020Q3.csv`;
- its DVC pointer, including the declared DVC MD5 and size; and
- the raw-data audit evidence and its configuration.

The V1b tag must resolve through the explicit ref
`refs/tags/protocol/ijds-credit-risk-controls-2026-07-13-v1b^{commit}`
to commit `1776cbf8b201ae5b92756e5ea397a403d6cc7c9f`, which must be an
ancestor of the V3 protocol commit. The freeze must retain its outcome-free
status, exhaustive sampling contract, no-selection status, five learners, and
nested descriptor for the exact score table.

Both V1b DVC directory pointers must also match their complete checked-out
directories byte for byte: V3 independently recomputes each `.dir` MD5, size,
and file count, and requires the score Parquet and freeze JSON to reside inside
the corresponding verified data and model directories.

The raw audit is a cross-check, not a substitute for a fresh scan. V3 scans all
2,925,493 archive rows using only `id`, `issue_d`, `term`, `loan_status`, and
`last_pymnt_d`; term and issue month alone select 376,890 target rows. It then
reconstructs the September 30, 2020 endpoint on every selected raw row. The
score and raw endpoint tables are outer-joined one-to-one by normalized ID.
Execution stops unless:

- both sides contain exactly 376,890 unique, nonblank IDs;
- there are zero score-only and zero outcome-only IDs;
- the score, raw-outcome, and joined ID hashes all equal the locked hash;
- every score issue month equals the raw issue month for that ID; and
- all five scores are finite, present, and inside `[0,1]` on those same rows.

V3 records a second canonical SHA-256 over ID, role, issue month, endpoint
reason, and nullable binary outcome. The retrospectively locked value is
`04c4d182b1223dc1c92df0898d4cd25e0a44fedded46dc1f52af62ba3d9317b6`.
It does not persist row-level outcomes. It also requires the score Parquet to
contain exactly the three identity columns and five score columns; reading an
allowlist while silently ignoring an added outcome column is forbidden.

Both hashes use a byte-level, implementation-independent contract. IDs are
normalized as unique stripped strings, sorted by Unicode code point, encoded
as UTF-8, and each byte string is preceded by its unsigned 64-bit
little-endian byte length. The literal vector `[é, ::, a]` therefore hashes
to `81f6992fb47d559c793c87786fe34a258f8a816b741079c8301d1af281d54e0d`.
Endpoint rows are sorted by normalized ID. Each record is the compact UTF-8
JSON array `[id,role,period,reason,y]`, where unresolved `y` is JSON `null`,
again preceded by its unsigned 64-bit little-endian JSON-byte length. The two
records `[a,primary_oot,2016-04,fully_paid_by_reconstructed_cutoff,0]` and
`[é,primary_oot,2016-04,nonterminal_or_unresolved_status,null]` hash to
`1e4d90031d9c00cabbb31dc16e591c3bcba0c7a2cbd1669f5778b37d091402c3`.
Unit tests pin both literal vectors, including non-ASCII and delimiter-like
IDs, so a serializer, sort, null, or endianness change is a protocol change.

## 4. Row-level endpoint reconstruction

The distributed archive is not represented as a verified point-in-time
snapshot. Fully Paid becomes available at last-payment month-end. Charged Off
becomes available at last-payment month-end plus six calendar months. A
terminal outcome is resolved only when that reconstructed date is no later
than September 30, 2020. `Default` and every other nonterminal status remain
unresolved under the established terminal-status rule.

The raw-derived rows must reproduce this complete partition:

| Endpoint reason | Candidate | Resolved | Unresolved |
|---|---:|---:|---:|
| Charged Off by reconstructed cutoff | 56,972 | 56,972 | 0 |
| Fully Paid by reconstructed cutoff | 307,842 | 307,842 | 0 |
| Nonterminal or unresolved status | 11,551 | 0 | 11,551 |
| Terminal after reconstructed cutoff | 47 | 0 | 47 |
| Terminal availability date missing | 478 | 0 | 478 |

Thus `D_R=56,972`, `R_0=307,842`, and `U=12,076`. V3 also emits the
complete month-by-reason census so aggregate agreement cannot conceal temporal
cancellation. These are reconstructed availability categories, not observed
operational event dates or a missingness-mechanism model.

## 5. Estimand and sharpness

For learner `j`, with frozen score `p_ij`,

`pbar_j = (1/N) sum_i p_ij`.

Each unresolved binary outcome may independently be zero or one, without a
MAR, MNAR, parametric, exchangeability, or transport restriction. Therefore

`mean(Y) in [D_R/N, (D_R+U)/N]`

and

`mean(p_j-Y) in [pbar_j-(D_R+U)/N, pbar_j-D_R/N]`.

Both endpoints are sharp. The all-one unresolved completion jointly attains
every learner's lower endpoint; the all-zero completion jointly attains every
upper endpoint. Every width is exactly `U/N`. More precisely, the exact
identified set for each learner is the finite grid

`pbar_j - (D_R+k)/N`, for `k=0,...,U`,

with `U+1=12,077` attainable points and step `1/N`. The reported interval is
the hull determined by the sharp lower and upper bounds; it does not claim
that every real number between them is attainable. These are deterministic
partial-identification bounds for this finite archive, not confidence,
prediction, posterior, or tolerance intervals.

The five marginal grids are projections of one shared joint set, not five
independently completed coordinates. If
`pbar=(pbar_1,...,pbar_5)` and `1_5` is the five-vector of ones, then the exact
joint identified set is

`{ pbar - ((D_R+k)/N) 1_5 : k=0,...,U }`.

It has only `U+1` collinear points. It is not the Cartesian product of the five
marginal intervals or grids. A single unresolved completion count `k` moves
all five coordinates together; this is why the all-one and all-zero
completions jointly attain the two endpoint vectors.

Negative, positive, zero-touching, and zero-crossing intervals are all valid
outputs. No sign, ordering, magnitude, or width triggers a stop or rerun.

## 6. Exact runtime contract

`uv` is not callable in the present Windows execution environment. V3 therefore
authorizes the actually available runtime rather than claiming an unobserved
launcher: Calibre **7.2.0**'s `calibre-debug.exe -e`. The canonical entry point
is the stdlib-only bootstrap, never the scientific runner directly. Before
NumPy, pandas, PyArrow, PyYAML, dateutil, six, tzdata, or any local scientific
module is importable, that bootstrap verifies:

- the absolute Git and Calibre executable paths plus hard-coded pre-Git hashes
  for Git's five dependency DLLs and Calibre's launcher, Python, frozen stdlib,
  hashing, and crypto root files;
- the exact sanitized Git environment, repository root, `.git` directory,
  SHA-1 object format, absence of replacement refs, clean HEAD, and explicit
  phase tag;
- exact `sys.orig_argv`, CPython 3.11.5, isolated interpreter flags, locale,
  timezone names, empty pre-import `sys.path`, and absence of scientific or
  site-customization modules;
- Git-blob equality for the bootstrap, complete recursively derived local
  Python closure including package initializers, protocol, configuration,
  runtime manifest, neutral Calibre template, tests, `.python-version`,
  `pyproject.toml`, and `uv.lock`;
- a byte composite over every RECORD-declared file for each of the seven
  required installed distributions, not merely their version strings;
- a complete 276-file, 379,912,649-byte composite over
  `C:/Program Files/Calibre2/app/bin`, which covers the native Calibre/stdlib,
  lxml, msgpack, Python, Qt, and DLL dependency substrate; every loaded `.pyd`
  must belong either to this inventory or to one of the seven sealed RECORD
  inventories;
- a dedicated Calibre directory containing only empty `caches/`, empty
  `plugins/`, and `global.py.json` byte-identical to the Git-bound neutral `{}`
  template; and
- an empty isolated pycache directory and the absence of forbidden Git,
  Python, Conda, virtual-environment, locale/timezone, OpenMP, BLAS/MKL,
  NumExpr, NumPy/pandas, and Arrow/PyArrow environment variables or prefixes.

Only after those checks does the bootstrap give the scientific runner exactly
the repository root and `.venv/Lib/site-packages` on `sys.path`. Built-in and
frozen importers retain precedence; a dedicated fail-closed sealed-byte finder
then handles every `src.*` and `scripts.*` source (including the explicit
`scripts.experiments` namespace) before `PathFinder` may serve the seven sealed
third-party distributions. The runner itself is compiled from its already
Git-authenticated in-memory bytes. Unknown local imports cannot fall back to
disk. The config, runtime manifest, AST closure, package initializers, canonical
bootstrap module, and all local modules are parsed or executed from those same
bytes, while stable one-handle rereads verify that disk and Git still agree.
The runner also verifies native-module membership, package and local-module
origins/loaders, the SHA-256 of `uv.lock`, and the bootstrap attestation.
Receipts store repository-local paths for project files; the neutral Calibre
template contains no library path, installation UUID, username, or unrelated
preference.

Calibre's embedded interpreter has `sys.flags.optimize=2` and `__debug__` is
false. This fact is recorded, not hidden. The exact transitive scientific
Python closure must contain no `assert` statement; every validation uses an
explicit exception and remains active under optimized Python. A static AST
gate enforces this condition.

The protocol authorizes no alternate launcher or free-form argument. The
dedicated directories must be absent and then be prepared exactly once:

```powershell
$v3Config = '.runtime_calibre/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3-config'
$v3Cache = '.runtime_calibre/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3-calibre-cache'
$v3Pycache = '.runtime_calibre/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3-pycache'
if ((Test-Path -LiteralPath $v3Config) -or
    (Test-Path -LiteralPath $v3Cache) -or
    (Test-Path -LiteralPath $v3Pycache)) {
  throw 'V3 isolated runtime paths must be absent before preparation.'
}
New-Item -ItemType Directory -Path `
  "$v3Config/caches", "$v3Config/plugins", $v3Cache, $v3Pycache
Copy-Item -LiteralPath `
  'configs/runtime/ijds_marginal_mean_score_outcome_gap_v3_calibre_global.json' `
  -Destination "$v3Config/global.py.json"
$env:CALIBRE_CONFIG_DIRECTORY = (Resolve-Path -LiteralPath $v3Config).Path
$env:CALIBRE_CACHE_DIRECTORY = (Resolve-Path -LiteralPath $v3Cache).Path
```

The shell must not define any forbidden environment variable enumerated in the
runtime manifest. The canonical compute invocation is then:

```powershell
& 'C:\Program Files\Calibre2\calibre-debug.exe' `
  -e scripts/experiments/bootstrap_ijds_marginal_mean_score_outcome_gap_v3.py -- `
  --phase compute `
  --config configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3.yaml
```

No compute invocation is valid until the complete protocol authority is
committed, explicitly tagged, and passes the pre-run adversarial gates.

## 7. Git, transitive authority, and TOCTOU seal

The compute phase accepts only the canonical V3 configuration. It requires a
clean current HEAD equal to the explicit protocol tag; revision expressions,
branches, abbreviated refs, and user-supplied repository roots are rejected.
The configuration bytes on disk must equal their exact Git blob at the tagged
commit.

The runner independently derives its repository-local AST import closure from
the sealed bytes and requires exact equality to the configured transitive path
census, including package initializers. It binds that closure, protocol, tests,
`.python-version`, `pyproject.toml`, and `uv.lock` to the same in-memory
descriptors, stable on-disk rereads, and exact Git blobs. All scientific closure
files are statically checked for forbidden `assert` nodes.

Small sources are parsed from the same sealed bytes that are hashed. The raw
archive is held through one open handle, hashed before and after its complete
chunked scan, and rehashed at every terminal source seal. Before computation,
immediately before output creation, after output creation, and before the
terminal seal, the runner requires identical:

- HEAD, explicit protocol tag, empty tracked/index/untracked Git state;
- implementation descriptors and Git blobs;
- runtime attestation;
- source descriptors, nested source identities, raw SHA-256, and DVC MD5.

Because experiment directories are Git-ignored, a clean Git status alone is
not accepted as output evidence. The runner directly inventories the exact
allowed files and rejects extra, missing, case-fold-colliding target paths,
symlinks, temporary files, or pre-existing paths. It does not infer that a DVC
checkout is physically unique merely from link count; DVC contents are instead
verified byte-for-byte from one open handle per file against the committed
`.dir` descriptor and a separate SHA-256 file inventory.

## 8. Immutable outputs and terminal seal

Both run directories must be absent at preflight. The run tag is never retried
after any partial output. Each file is written through exclusive creation and
a no-replace atomic promotion; an existing target is an error, not an
overwrite.

The data directory contains exactly:

1. `evaluation/marginal_mean_score_outcome_gap.parquet`;
2. `evaluation/endpoint_reason_census.parquet`; and
3. `evaluation/monthly_endpoint_reason_census.parquet`.

The model directory contains exactly:

1. `marginal_mean_score_outcome_gap_summary.json`;
2. `execution_receipt.json`; and
3. `execution_seal.json`.

The deterministic summary binds the three scientific artifacts. The receipt is
explicitly preterminal: it binds sources, runtime, implementation, authority,
summary, and artifacts before success is declared. After writing that receipt,
the runner again rehashes every source, repeats Git/runtime/implementation
authority, revalidates the full bootstrap substrate, and checks the exact
pre-seal inventory. Only then is `execution_seal.json` created as the sixth and
last output. A post-write validator rehashes all six outputs, recomputes the
protocol commit, Git snapshot, complete implementation provenance, invariant
runtime policy, and terminal bootstrap attestation, and requires exact equality
rather than accepting empty or coherently resealed authority objects. It checks
all cross-links and final inventory; it performs no new scientific action that
the seal falsely claims to precede. A partial directory without a valid terminal
seal is permanently nonpromotable.

The compute status is explicitly
`complete_clean_tagged_v3_pending_git_artifact_commit`; it is not active
evidence.

## 9. Git-native artifact commit and portability gate

V3 persists only three tiny aggregate Parquets plus summary, receipt, and seal.
It persists no row-level ID or outcome. Creating two new DVC pointers and a new
remote dependency would therefore weaken rather than improve delivery. The
prospectively locked transport is `dvc_tracked:false`: exactly the six outputs
are force-added to Git after the immutable compute run.

After a successful terminal seal, an operator must:

1. confirm that the six outputs pass the aggregate-only size/privacy contract;
2. force-stage exactly the six config-declared output paths despite their
   broad ignore rules;
3. confirm that the staged diff contains those six paths and no `.dvc`,
   `.gitignore`, `dvc.lock`, code, configuration, registry, or paper change;
4. create one commit whose sole parent is the protocol commit and whose sole
   diff is the six outputs, then create the declared artifact tag;
5. run the read-only `verify-artifact` phase below; and
6. in a separate clean clone on the same authenticated Windows substrate,
   fetch the artifact tag, materialize only the three already-existing source
   DVC pointers, prepare a byte-identical project venv plus fresh neutral
   Calibre/cache/pycache directories, and rerun full `verify-artifact` before
   any active-source registration.

The read-only Git-native artifact gate is shown here to pin its exact argv. In
a clean clone it must **not** be invoked until the chronological preparation
sequence stated after the venv-copy and DVC blocks below is complete:

```powershell
# In a fresh clone, first run the exact config/cache/pycache preparation block
# in Section 6. After any source-pull operator invocation, restore both
# canonical Calibre directories before scientific verification.
$env:CALIBRE_CONFIG_DIRECTORY = `
  (Resolve-Path '.runtime_calibre/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3-config').Path
$env:CALIBRE_CACHE_DIRECTORY = `
  (Resolve-Path '.runtime_calibre/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3-calibre-cache').Path
& 'C:\Program Files\Calibre2\calibre-debug.exe' `
  -e scripts/experiments/bootstrap_ijds_marginal_mean_score_outcome_gap_v3.py -- `
  --phase verify-artifact `
  --config configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3.yaml
```

The six outputs arrive natively with the artifact-tag checkout. A clean clone
does not contain the ignored `.venv`, and neither bare `uv` nor its project
trampoline is callable on this host. The scientific venv is therefore
materialized by an explicit, fail-closed operator. The operator accepts an
existing source venv through an environment variable (so no username is
hard-coded), verifies all seven source RECORD composites against the Git-bound
runtime manifest, copies only the union of those RECORD paths into the absent
target `.venv`, and verifies the seven target composites again. Packages or
files outside that union are not copied:

```powershell
if (-not $env:CRPTO_V3_SOURCE_VENV) {
  throw 'Set CRPTO_V3_SOURCE_VENV to the full .venv of the verified protocol clone.'
}
$sourceVenv = (Resolve-Path -LiteralPath $env:CRPTO_V3_SOURCE_VENV).Path
$venvWork = '.runtime_calibre/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3-venv-copy'
New-Item -ItemType Directory -Path `
  "$venvWork/calibre-config", "$venvWork/calibre-cache"
$env:CALIBRE_CONFIG_DIRECTORY = (Resolve-Path "$venvWork/calibre-config").Path
$env:CALIBRE_CACHE_DIRECTORY = (Resolve-Path "$venvWork/calibre-cache").Path
$venvCode = @'
import importlib.machinery
import json
import os
import sys
from pathlib import Path
original = list(sys.meta_path)
sys.meta_path[:] = [
    importlib.machinery.BuiltinImporter,
    importlib.machinery.FrozenImporter,
    importlib.machinery.PathFinder,
    original[0], original[1], original[2], original[6],
]
sys.path[:] = [str(Path.cwd().resolve())]
from scripts.experiments.bootstrap_ijds_marginal_mean_score_outcome_gap_v3 import (
    materialize_locked_project_venv,
)
receipt = materialize_locked_project_venv(
    Path(os.environ['CRPTO_V3_SOURCE_VENV']), repo_root=Path.cwd()
)
print(json.dumps(receipt, sort_keys=True))
'@
& 'C:\Program Files\Calibre2\calibre-debug.exe' -c $venvCode
if ($LASTEXITCODE -ne 0) { throw 'V3 seven-RECORD venv materialization failed.' }
```

The target scientific `.venv` intentionally does not contain DVC. Source
transport therefore runs in a separate Calibre process using the full source
venv only as an untrusted DVC transport environment. The scientific verifier
does not trust that process: it independently verifies every resulting source
pointer, raw archive hash, and directory/file inventory. The transport uses an
isolated writable DVC cache, analytics disabled, and exactly three hard-coded
targets:

```powershell
$dvcWork = '.runtime_calibre/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3-source-pull'
New-Item -ItemType Directory -Path `
  "$dvcWork/calibre-config", "$dvcWork/calibre-cache", `
  "$dvcWork/site-cache", "$dvcWork/global-config", "$dvcWork/system-config"
$env:CALIBRE_CONFIG_DIRECTORY = (Resolve-Path "$dvcWork/calibre-config").Path
$env:CALIBRE_CACHE_DIRECTORY = (Resolve-Path "$dvcWork/calibre-cache").Path
$env:DVC_SITE_CACHE_DIR = (Resolve-Path "$dvcWork/site-cache").Path
$env:DVC_GLOBAL_CONFIG_DIR = (Resolve-Path "$dvcWork/global-config").Path
$env:DVC_SYSTEM_CONFIG_DIR = (Resolve-Path "$dvcWork/system-config").Path
$env:DVC_NO_ANALYTICS = '1'
$env:CRPTO_V3_DVC_SITE_PACKAGES = `
  (Resolve-Path -LiteralPath "$sourceVenv/Lib/site-packages").Path
$dvcCode = @'
import importlib.machinery
import os
import sys
from pathlib import Path
original = list(sys.meta_path)
sys.meta_path[:] = [
    importlib.machinery.BuiltinImporter,
    importlib.machinery.FrozenImporter,
    importlib.machinery.PathFinder,
    original[0], original[1], original[2], original[6],
]
sys.path[:] = [str(Path(os.environ['CRPTO_V3_DVC_SITE_PACKAGES']).resolve())]
from dvc.cli import main
raise SystemExit(main([
    'pull',
    'data/raw/Loan_status_2007-2020Q3.csv.dvc',
    'data/processed/experiments/ijds_audit/ijds-credit-risk-controls-2026-07-13-v1b.dvc',
    'models/experiments/ijds_audit/ijds-credit-risk-controls-2026-07-13-v1b.dvc',
]))
'@
& 'C:\Program Files\Calibre2\calibre-debug.exe' -c $dvcCode
if ($LASTEXITCODE -ne 0) { throw 'V3 source DVC pull failed.' }
Remove-Item Env:CRPTO_V3_DVC_SITE_PACKAGES
Remove-Item Env:CRPTO_V3_SOURCE_VENV
Remove-Item Env:DVC_SITE_CACHE_DIR
Remove-Item Env:DVC_GLOBAL_CONFIG_DIR
Remove-Item Env:DVC_SYSTEM_CONFIG_DIR
Remove-Item Env:DVC_NO_ANALYTICS
```

The clean-clone order is mandatory: (1) materialize the seven-RECORD scientific
`.venv`; (2) pull exactly the three sources in the separate external DVC
transport process; (3) execute the Section 6 preparation block to create fresh
canonical scientific Calibre config/cache/pycache directories; (4) confirm all
`CRPTO_V3_*` and `DVC_*` transport variables are absent; and only then (5) execute the
previously shown canonical `verify-artifact` invocation. Reordering these steps
is not an authorized clean-clone verification.

The venv-copy transcript must retain the returned distribution composites,
union file/byte counts, and zero exit code. The source-pull transcript must
record Calibre/DVC versions, the external-transport role, isolated DVC
environment, exact three targets, and exit code, without entering either
scientific output directory. These are packaging provenance, not scientific
authority: the scientific verifier independently checks every source pointer,
directory/file MD5, file count, byte count, SHA-256 inventory, and the raw
archive again.

`verify-artifact` requires a clean HEAD at the explicit artifact tag. The
artifact commit must be the direct single-parent child of the protocol commit,
and its Git diff must contain exactly the six configured output paths. Each
workspace file must equal its exact artifact-commit Git blob and the terminal
seal descriptor. The verifier rejects row-level columns, row-scale JSON lists,
personal filesystem paths/metadata, or a total payload above 5 MB. It then
reopens and rescans all raw and V1b sources, reconstructs every endpoint row,
recomputes all three scientific Parquets and the complete deterministic
summary, compares them exactly to the Git-delivered outputs, and repeats
source, Git, implementation, runtime, bootstrap, seal, privacy, and Git-blob
checks at the terminal boundary. A coherently rewritten Parquet/JSON/seal
bundle therefore still fails recomputation.

Only after local and separate-clean-clone `verify-artifact` success may a later
change register V3 with `dvc_tracked:false`, the exact artifact tag and commit,
the six Git paths, and the direct-child diff certificate, or incorporate V3
numbers into the active manifest or manuscript. This protocol itself performs
none of those promotion steps.

## 10. Interpretation boundary

V3 supports only a deterministic five-learner description of mean frozen
scores relative to a partially identified mean binary outcome on one finite
archive. It does not establish individual calibration, conditional
calibration, discrimination, temporal transport, exchangeability, a selected
model, a shift mechanism, fairness, selected-set or funded-set validity,
causality, prospective performance, policy direction, or deployment readiness.

The archive and outcomes were already inspected; the stronger V3 lineage does
not convert this retrospective audit into confirmation.
