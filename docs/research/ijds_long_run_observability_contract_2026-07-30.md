# IJDS long-run observability and checkpoint contract (2026-07-30)

## Status and scope

This is an operational design contract for future long scientific runs. It
does not modify, resume, or authorize execution of any protected stage or
byte-sealed IJDS lineage. In particular, the completed set-preserving embedding
V1/V1c/V1d implementation and artifacts remain immutable.

Observability is not evidence. Runtime status, heartbeats, resource snapshots,
and scratch checkpoints must never activate a scientific claim, expose a
partial result for selection, or masquerade as a completed artifact.

## Implemented MVP boundary

The current `LongRunObserver` and read-only inspector implement only a bounded
single-writer, same-process-worker MVP. The worker or a thread in that same
process must call each heartbeat explicitly. The snapshot reports only that
process and, when the process backend is available, binds its PID to its
creation time so a recycled Windows PID is not accepted as the original
worker. It does not inspect child processes or a process pool. A fresh,
run-specific runtime directory outside every forbidden root remains a
caller-enforced precondition because the MVP has no interprocess lease.

The MVP provides an atomic latest snapshot, monotone in-memory unit counts,
bounded allowlisted operational detail, a neutral
`no_recent_progress_or_cpu_signal` observation, cooperative stop checks at
declared boundaries, and a simple advisory global-mean ETA after a minimum
number of units. It rejects collisions among status/control paths and among a
checkpoint, its atomic staging names, and bound artifacts.

The detail allowlist, scalar-only JSON checks, and size limits are syntactic
guards, not a semantic detector of scientific content. A future runner must
predeclare the operational meaning and admissible values of every detail field;
it may not pass free-form solver output, scientific values, or local paths and
rely on this utility to recognize them.

The current checkpoint is explicitly an integrity receipt with
`resume_authorized=false`; it is not resume authority. The MVP has no event
journal, event sequence, deadline enforcement, process-tree monitoring,
interprocess writer exclusion, robust phase ETA, shard schema/census gates, or
canonical resume/merge implementation. Those remain future requirements below.
No protected or long scientific execution is authorized by this implementation.

## Provenance: the 7.5-hour embedding run

The outcome-free V1a execution receipt records:

| Field | Recorded value |
|---|---:|
| Start | 2026-07-29 16:39:16.177782 UTC |
| Completion | 2026-07-30 00:13:01.291606 UTC |
| Elapsed | 27,224.0978 seconds |
| Elapsed in ordinary units | 7 h 33 min 44 s |

Its completed summary records 31,200 frontier solve rows, 5,200 minimum-score
endpoints, 26 objective optima, 18,000 order replays, 3,600 independent-solver
cells, and 3,120,241 funded-allocation rows. The base execution entails
approximately 63,252 LP calls before any declared endpoint retry:

- 52 objective-optimum and reversed-order solves;
- 10,400 minimum-score and efficient-endpoint solves;
- 31,200 two-ruler frontier solves;
- 18,000 reversed-order audit solves; and
- 3,600 independent GLOP checks.

The screenshot taken at approximately 7 h 29 min 47 s showed 26,691 process CPU
seconds and about 2.48 GiB resident memory. CPU time was therefore about 98.9%
of wall time: strong evidence of approximately one logical-core-equivalent of
CPU work, not proof that the same logical processor remained occupied
continuously, and not evidence of a deadlock. The receipt shows that the run
completed about four minutes later.

The apparent silence was created by the runner structure. It computed the
entire `build_set_preserving_frontiers` object in memory, with HiGHS console
output disabled, and began atomic Parquet/JSON materialization only after that
function returned. There was no progress counter, heartbeat, partial shard, or
machine-readable solve throughput.

The scientific computation advanced. The monitoring conversation did not: it
could observe only process liveness, cumulative CPU, resident memory, empty
logs, Git state, and the absence of final files, so repeated snapshots produced
the same conclusion without reducing uncertainty about completion.

## Resource diagnosis

The diagnosed computer has an AMD Ryzen 9 5900X with 12 physical cores and 24
logical processors. A process consuming one logical processor at approximately
100% can appear near 4.2% in Task Manager's whole-machine CPU view. The observed
2.1--2.7 GiB process memory was also a small fraction of 64 GiB physical RAM.
Consequently, neither aggregate CPU nor aggregate RAM needed to reach its limit
for the worker and application to feel slow.

The screenshot also showed a large application state: 42 subagents marked in
progress, 83 completed, 113 modified files, and a very large displayed diff.
Rendering that state, updating file watchers, rescanning Git, and maintaining a
long WebView conversation can delay the interface independently of the
single-threaded solver.

A later diagnostic snapshot found only about 15.2 GiB, or 3.27%, free on C:,
while D: had substantially more free space. That is a dated diagnostic, not
proof of the free-space state throughout the historical run. It nevertheless
establishes a present operational risk: Windows temporary files, the pagefile,
NTFS metadata, application caches, and SSD garbage collection can all become
less responsive on a nearly full system volume. Background game clients,
Overwolf, WebView2, and ChatGPT processes were also active in that later
snapshot; they are possible contemporaneous competitors, not evidence about
the entire earlier execution.

## Lessons from the recovery chain

Three later failures were operational rather than reasons to discard the
scientific question:

1. V1a completed Phase A, but an in-worktree `.dvc/site-cache` created an
   undeclared Git path and prevented the exact two-pointer artifact commit.
2. The first V1c Phase-B launch hit Windows `MAX_PATH` before outcome access or
   output creation.
3. The completed V1c Phase B exposed an undeclared nullable exact-payoff field;
   V1d correctly retained the identified lower and upper endpoints and removed
   the undefined exact field.

The V1a scientific bytes were ultimately anchored in the Git-native V1d source
chain and V1d Phase B completed in about 168 seconds. Thus the 7.5-hour
calculation was useful, but its lack of observability and its in-repository
scratch configuration created avoidable uncertainty and recovery work.

## Design goals

A future long-run layer must:

- distinguish healthy computation, I/O, materialization, waiting, failure, and
  genuine lack of progress;
- report objective progress without exposing scientific results;
- survive UI disconnection and agent turnover;
- allow cooperative cancellation at a prespecified safe boundary;
- support protocol-authorized resume from verified atomic shards;
- leave the scientific worktree and protected-read root unchanged;
- preserve deterministic, complete-grid outputs; and
- make elapsed time and ETA auditable rather than conversational guesses.

It must not:

- alter a solver, tolerance, grid, tie rule, order rule, or scientific result;
- write an undeclared file into an official artifact directory;
- inspect partial outcomes to decide whether to continue;
- infer success merely because CPU is high;
- infer failure merely because no final output exists; or
- resume one protocol's scratch state under a different protocol or run tag.

## Runtime location

Every future protocol must declare a runtime root outside:

- the Git worktree;
- `.git`;
- every official data/model/report output directory;
- the protected-read root;
- the DVC cache used for evidence; and
- any path enumerated by an artifact-transport contract.

An acceptable Windows default is a run-tagged directory beneath
`%LOCALAPPDATA%\CRPTO\runtime`, or an explicit scratch directory on a volume
with adequate free space. The portable scientific receipt may record the
runtime schema and final operational summary, but it must not serialize the
absolute local runtime path.

Before execution, the runner must verify that the runtime root is outside all
forbidden roots, is writable, has no prior state for the run tag, and satisfies
a protocol-declared free-space reserve. Free-space thresholds are operational
preflight values and must be evaluated at launch; a dated diagnostic percentage
must never be hard-coded as a permanent property of a drive.

## Runtime state schema

The observer should maintain one atomic `latest.json` and a crash-tolerant
event sequence. Every state record should contain:

- schema version;
- run tag, protocol tag, commit, configuration digest, and scientific-plan
  digest;
- observer PID and worker PID plus process-creation time or a stronger run
  identity;
- monotonically increasing event sequence;
- lifecycle state and current phase;
- completed and total units for the current phase and globally;
- a non-outcome current unit key;
- start and update timestamps in UTC;
- elapsed wall seconds and process CPU seconds;
- CPU-to-wall ratio over the latest interval;
- resident memory bytes when available;
- last-completed-unit and last-heartbeat timestamps;
- phase and global throughput;
- ETA value, interval, method, and eligibility flag;
- checkpoint count and last verified checkpoint key;
- cancellation/deadline state; and
- error class and sanitized message after failure.

Current-unit keys may name a window, role, period, theta, gamma, ruler,
coordinate, shard, or validation phase. Status files must exclude scores,
objectives, exposures, coverage, payoff, endpoint values, winners, directions,
or any other scientific result that could induce continuation or selection.

## Lifecycle

The required lifecycle is:

```text
preflight
  -> loading_sources
  -> validating_sources
  -> computing
  -> validating_scientific_state
  -> materializing
  -> sealing
  -> completed
```

Terminal alternatives are `failed_prewrite`, `failed_postwrite`,
`cancelled_at_safe_boundary`, and `deadline_reached_at_safe_boundary`.
`stalled_suspected` is an observer diagnosis, not a terminal scientific state
and not automatic authority to kill a process.

Each transition must be explicit and monotonic. A worker process that exits
without a terminal record is classified as `unexpected_exit`, even if some
scratch shards exist.

## Heartbeats and liveness

A lightweight observer thread or parent process should update the heartbeat at
a protocol-declared interval, recommended initially as 30 seconds. Console
summaries should be much less frequent, for example every five minutes, to
avoid recreating the previous high-volume monitoring loop.

Health classification must use three separate signals:

1. completed-unit progress;
2. process CPU accumulation; and
3. process existence and heartbeat age.

If CPU time is increasing while a solver remains inside its declared
per-solve time limit, the state is `computing_without_unit_boundary`, not
stalled. If no unit completes beyond a predeclared multiple of the solver time
limit and process CPU also stops increasing, the observer may mark
`stalled_suspected`. The warning and terminal thresholds must be fixed in the
future protocol; they may not be expanded repeatedly in chat.

The implemented MVP deliberately uses the neutral observation
`no_recent_progress_or_cpu_signal`. Without phase-aware I/O/wait telemetry,
that observation is not a stall diagnosis and supplies no authority to
terminate a process.

The observer must continue heartbeats during one slow solver call. It must not
depend solely on callbacks that occur after a solve.

## Progress and throughput

Future runners must define their progress denominator from the complete locked
grid before computation. Heterogeneous operations should be separated into
phases rather than counted as equal work without disclosure.

For a successor to the embedding run, suitable phase counters include:

- objective optima;
- minimum-score endpoint pairs;
- two-ruler frontier solves;
- order replays;
- independent-solver validations;
- scientific-frame validation;
- materialized files; and
- sealed files.

Throughput should be calculated with monotonic clocks and robust recent
durations. ETA must remain unavailable until a declared minimum number of
comparable units or shards has completed. It should report a range, not only a
point estimate, and must reset or change method when the phase changes. A first
cell, aggregate process CPU, or absence of output is not enough to infer ETA.

The final receipt should preserve actual phase durations and counts so that a
later protocol can use them as pre-run planning information without treating
them as scientific evidence.

## Future 208-shard embedding design

The natural resumable unit for a future embedding successor is

```text
(window_id, role, period)
```

There are eight windows and 26 declared role-period combinations, giving 208
complete shards. Each shard must include the entire locked theta--gamma--ruler--
coordinate family for that key and every required audit for its role. It may
not contain a result-selected subset.

Objective optima currently cached across windows need an explicit future
contract. A successor may either:

- create a separately sealed 26-key outcome-free optimum phase and bind each
  shard to it; or
- recompute the optimum within every shard and require exact reconciliation
  across windows.

The choice must be fixed before execution. Silent reuse of an in-memory cache
is insufficient for resumable shards.

Every shard must be written atomically to scratch and carry:

- run/config/protocol/source/implementation/runtime digests;
- exact shard key;
- ordered schema and dtypes for every component;
- row and complete-key censuses;
- solver and tolerance identities;
- protected-read and protected-write declarations;
- content digests; and
- completion timestamp and elapsed/CPU time.

Shards are operational checkpoints, not paper-facing artifacts. Their
scientific values must not be surfaced in status summaries or inspected to
choose whether the run continues.

## Resume contract

Resume is permitted only when the future protocol explicitly authorizes it
before execution. At resume, every retained shard must pass:

1. exact run, protocol, commit, config, source, code, runtime, and solver
   identity;
2. exact shard-key membership in the locked 208-key plan;
3. schema, dtype, row-count, key-completeness, and numeric-finiteness gates;
4. content-digest verification;
5. no outcome leakage into an outcome-free phase;
6. no duplicate or overlapping shard;
7. no file outside the scratch contract; and
8. no human or automated selection based on partial scientific values.

One mismatch invalidates that shard. Cross-tag reuse is forbidden unless a new
protocol names the exact source shards, their hashes, and the scientific reason
reuse is valid. A retry may never copy a partial official artifact and call it
a checkpoint.

After all 208 shards pass, the finalizer must concatenate them in a canonical
key order, impose exact dtypes, validate the complete monolithic census, and
reconcile against single-process synthetic fixtures. Only then may it write
fresh official outputs and proceed to the existing artifact-transport gates.

## Cooperative cancellation and deadlines

A future runner may support an external `cancel.request` only in the declared
runtime root. The worker checks it between atomic shards or other
protocol-defined safe boundaries, writes a terminal operational state, and
exits without creating official scientific outputs. It must not interrupt an
atomic replace or artifact seal.

Every long protocol should declare:

- a total wall-time budget;
- per-solve time limits;
- a heartbeat warning threshold;
- a no-progress warning threshold;
- a no-progress terminal threshold;
- a cooperative-cancel polling boundary; and
- whether verified scratch shards may be resumed.

Deadlines are fixed operational rules. Crossing one cannot be handled by an
ad hoc extension after partial results are inspected. A scientifically
necessary extension requires the protocol's declared amendment/successor
procedure.

Force termination remains an emergency action. It leaves only previously
atomic, independently verifiable scratch shards eligible for consideration;
in-memory work and partial temporary files are discarded.

## Windows and responsiveness preflight

Before any protected archive read or official output creation, a future runner
must check:

- effective Git `core.longpaths=true` on Windows when required;
- runtime and output path lengths;
- free space against the declared reserve;
- process priority and solver thread count;
- absence of a prior output directory;
- clean and correctly tagged Git authority;
- source hashes and protected-root separation; and
- that caches and temporary directories resolve outside the worktree.

HiGHS should remain one thread per solve unless a new numerical protocol proves
otherwise. A future sharded runner may use a small process pool, recommended
initially as no more than two workers on an interactive workstation, with
below-normal process priority. Parallel execution is eligible only after tests
show that one-worker and multi-worker runs yield the same canonically sorted
scientific frames, schemas, counts, and declared numerical tolerances.

Moving a future clean clone and runtime scratch to a roomier drive is an
operational option, not permission to relocate protected inputs silently or
serialize local absolute paths.

## Stop rules

A future long run stops before official materialization if:

1. Git, tag, config, source, implementation, runtime, or protected-root
   authority changes.
2. Runtime scratch resolves inside a forbidden root.
3. Windows long-path or free-space preflight fails.
4. The progress plan is missing, nonfinite, nonmonotonic, or changes size.
5. A heartbeat or checkpoint exposes a scientific result.
6. A checkpoint is missing identity, schema, key, census, or content hashes.
7. A duplicate, overlapping, undeclared, or result-selected shard appears.
8. A worker exits without a valid terminal state.
9. A declared wall deadline or safe-boundary cancellation is reached.
10. A scientific or numerical validation fails.
11. Any official output path is occupied.
12. A protected stage is requested without separate explicit authority.

High CPU alone is not a stop condition. Low aggregate Task Manager utilization
alone is not a continuation condition. The decision must follow objective
progress, liveness, deadlines, and protocol gates.

## Required tests

A reusable implementation should include tests for:

- atomic latest-status replacement with no temporary-file leak;
- monotonic event sequence and completed-unit counts;
- heartbeat updates during a simulated slow solver;
- correct distinction among computing, idle, suspected stall, exit, and
  completion;
- ETA suppression before the minimum sample and reset at phase transitions;
- deterministic ETA under a fake clock;
- cooperative cancellation only at a safe boundary;
- rejection of runtime roots inside the repo, protected root, or official
  output tree;
- low-space and Windows long-path preflight;
- crash injection during status and shard writes;
- corrupt-tail recovery for the event sequence;
- checkpoint rejection under every identity, hash, schema, count, dtype, key,
  and finiteness mutation;
- duplicate/missing shard detection over the exact 208-key set;
- no outcome column in outcome-free checkpoints;
- no scientific result or absolute local path in portable status summaries;
- canonical final merge independent of shard completion order; and
- one-worker versus two-worker scientific equivalence.

The existing `src/utils/pipeline_runtime.py` atomic writers and the progress
logic in `scripts/search/run_portfolio_bound_exact_eval.py` are useful
implementation references. The latter's resumable partial table is not by
itself sufficient for this contract because the future shard design additionally
requires complete identity, schema, key, and content-hash validation.

## Integration and monitoring boundary

Implementation should be added through a new utility and new successor runners,
not by editing the active byte-pinned V1d runner or its registered
implementation. A small read-only inspector may display `latest.json`, recent
events, throughput, ETA eligibility, and health classification.

One monitor is sufficient. It should emit only state transitions or material
progress and should not spawn a growing tree of agents to repeat unchanged
snapshots. If no state changed, the monitor waits. If the worker requests
approval or a scientific gate fails, it yields to the user rather than silently
extending the run.

The final scientific receipt may summarize the observer version, heartbeat
count, phase durations, peak recorded memory, cancellation status, checkpoint
count, and whether resume occurred. It must independently verify final outputs;
observability metadata never substitutes for scientific or artifact validation.
