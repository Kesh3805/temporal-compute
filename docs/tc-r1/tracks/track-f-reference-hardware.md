# Track F preparation: reference and hardware pipeline

**Draft preparation only.** No reference generation, render, installation,
hardware selection, timing result or outcome is part of this PR. Implementation
depends on the reviewed [TC-R1E3 selection PR #14](https://github.com/Kesh3805/temporal-compute/pull/14) and reviewed shared
interfaces. E2's incomplete-evidence result is preserved. Related research issue:
#9; keep it open until the separate research decision/execution work is complete.

The [original protocol](../preregistration.md) remains authoritative. This plan
creates no execution freeze and changes no thresholds, inputs or results.

## Inputs and interface review before implementation

Agree versioned interfaces with Track D's corpus manifest, Track A's sampler and
charged-work adapter, and Track E's metrics before writing the pipeline. Freeze
linear RGB layout/encoding, finite-value handling, image/content hashes, stream
derivation, completed sample ranges and reference-validation output. References
are analysis-only inputs; controller/baseline state cannot read references,
reference errors or future production samples.

Require the frozen ten-scene/three-frame corpus, asset hashes/licenses, exact
camera/material/light/frame settings and approved stream mapping before any
final reference generation. A preparation-only synthetic feasibility measurement
must remain separately labeled and cannot choose workloads based on TC results.
Do not substitute provisional assets or generate final references before corpus
freeze. Never expose TC-vs-baseline outcomes before execution preregistration.

## Independent references and convergence

For each of 30 scene/frame pairs generate independent `reference-a` and
`reference-b` streams, initially 8192 camera samples/pixel each. Bind the master
seed 20261007 and registered SHA-256 stream derivation to Track A's explicit
counter/sample-index mapping, including reference replicate identifiers. Freeze
those identifiers and the final scoring-reference construction before generation;
do not assume the protocol already specifies whether scoring uses A, B or a
combination. Any clarification must be reviewed before outcomes and preserve the
original registration.

Validate A versus B with Track E's pinned relative linear MSE <= .0001, display
SSIM >= .995 and LPIPS <= .01. If convergence fails, double both streams to 16384,
then 32768 spp with no controller outcomes visible. Preserve prior levels,
hashes and convergence rows. Freeze whether doubling extends each independent
stream or regenerates its complete prefix; do not change that choice after a
failure. If either reference is invalid or convergence still fails at 32768,
halt the scene and overall PASS gate and require an explicit amendment. Keep the
difficult scene; do not lower effort or convergence standards for convenience.

Initial camera-sample total is exactly:

`10 scenes x 3 frames x 2 streams x 256^2 pixels x 8192 spp = 32,212,254,720`.

This already includes both streams. It is not a ray count, a benchmark, a measured
runtime or a feasibility guarantee. Escalation and trace costs require separate
planning; rays depend on completed paths and cannot be estimated as exact work
from spp. Full per-camera-sample logs need not be permanent reference artifacts;
freeze a sufficient auditable retention format and measure its actual size.

## Hardware, timing and capacity acceptance

Before execution freeze, retain a manifest with CPU model/backend, core/thread
counts, RAM, free storage, OS/compiler/build flags, PBRT upstream and patch hashes,
floating-point settings, library/metric/model revisions and executable hashes.
PBRT-v4 CPU at `b4ce9687e6c695f5582997c61b0c66cf064bdb4a` is the pending E3
selection dependency; no GPU migration or Mitsuba reopening belongs in this track.

Measure synthetic, non-primary throughput, peak memory, image/trace sizes and
analysis throughput on the proposed execution host before declaring feasibility.
Record fixture, actual samples/rays, wall time, repetitions and uncertainty.
Separate measured values from corpus extrapolations, disclose complexity gaps,
reference escalation and available storage. An insufficient host requires a
different approved resource or pre-outcome amendment, not weakened references.

Timing records must include end-to-end allocation, state updates, rendering,
dispatch, stopping checks and required live metric evaluation. Record their
breakdown, overhead fraction and worst latency without excluding overhead from
the total. Offline reference generation/reporting costs are separate. Require a
synchronized CPU completion boundary, monotonic clock, frozen warmup, threads,
common time cap/checkpoint cadence, and paired random policy order from the
registered `timing-order` stream. Three repeated executions supply per-unit
median time; they are not extra quality replicates. Track E must approve how
nonattainment, ray limits, failures and censoring enter the timing schema.

## Retained artifacts and readiness conditions

Propose an immutable run manifest linking corpus/asset hashes, reference stream
identity and sample ranges, image hashes, convergence measurements, metric/model
hashes, renderer/build revision, hardware and logs. Retain action traces and all
outcomes required by the protocol in the eventual runner. Freeze image format,
compression, trace granularity, checksums, partial-run recovery, failure rows,
storage margin, archive location and retrieval verification before production.
Preserve every escalated or failed convergence attempt rather than overwriting
it with the successful endpoint.

Synthetic acceptance should prove independent stream identities, deterministic
prefix resumption, corrupted/missing asset/model/image detection, convergence
escalation and terminal halt, complete failure retention, accurate clock/work
fields and separation of analysis references from legal controller observations.
No production references or final hardware promises are claimed by these tests
until they actually run. Corpus freeze, converged references, metrics, algorithms,
hardware and analysis must all be bound before `tc-r1-execution-preregistered`.
