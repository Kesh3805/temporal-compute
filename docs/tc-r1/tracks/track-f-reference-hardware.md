# Track F preparation: reference and hardware pipeline

**Contract and pipeline work; execution not frozen.** PBRT selection
[PR #14](https://github.com/Kesh3805/temporal-compute/pull/14) is merged at
`3c4a1990f4a80e8f12f6fbf10bca81fdb22cf3ed`. No reference generation, render,
installation, hardware selection, timing result or outcome is part of this PR.
The pipeline validates supplied artifacts and plans; it does not invoke a renderer.
E2's incomplete-evidence result is preserved. Related research issue:
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
PBRT-v4 CPU at `b4ce9687e6c695f5582997c61b0c66cf064bdb4a` is selected by E3;
no GPU migration or Mitsuba reopening belongs in this track.

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

## Concrete Track F interface v1 (before implementation)

`research/tc-r1/reference-hardware-contract.json` defines the pipeline interface.
The corpus supplies exactly ten distinct scene IDs and three distinct frame IDs
per scene; every pair binds a PBRT asset SHA-256. Reference replicate is **0**
with the separately named `reference-a` and `reference-b` streams, derived by the
original SHA-256 rule. Each escalation regenerates the complete deterministic
prefix `[0,spp)`; previous levels and failure records remain immutable. This
choice concerns reference execution, not changing A's production stream mapping.

Canonical analysis images are `.npy`, C-order H×W×3 little-endian float64 linear
RGB, finite, preserving negative finite radiance. EXR-to-canonical conversion
must be tested by the eventual renderer adapter; this utility consumes canonical
files and cannot certify that absent conversion. A/B convergence uses the maximum
of both directional registered relative MSE values, with the unchanged SSIM and
LPIPS bars. Scoring image is `(A+B)/2`, approved in the root agent's independent
engineering review before outcomes. This concretizes the unspecified scoring
construction and preserves the original registration. The pipeline can validate
the construction on synthetic arrays; it generates no final reference image.

Records bind scene/frame, corpus and asset hashes, level, stream IDs, completed
sample ranges, both image hashes, metric implementation and model-weight hashes,
three convergence metrics, and a decision: `converged`, `escalate`, `halt`, or
`failed`. A failure remains a durable row, blocks continuation and cannot be
silently retried. Escalation is allowed only after a valid nonconverged pair;
32768 nonconvergence halts. Hashes are checked against files, not accepted as
unchecked declarations. Synthetic records are expressly marked synthetic.

The host utility records observed CPU/platform/logical threads/RAM/free storage
and binary hashes without installing dependencies or claiming this is the
execution host. Physical-core count, compiler/build flags, pinned thread count,
warmup, common time cap, final storage location and metric package/model hashes
must be supplied and independently validated at integration. Missing fields
cannot pass readiness. Use synchronized completed CPU work and monotonic
nanoseconds; three repeated timings and paired policy-order permutations derive
from the registered timing-order seed. Registered ray checkpoints are mandatory;
time-cap completion/nonattainment retention and early ray-cap censoring require
Track E's separately tested agreement. No time cap is guessed before host choice.
The user selected pipeline preparation with **host selection pending**. Final
references, actual-host feasibility renders and expensive production remain
unauthorized. Seed hashes alone cannot prove native sampler/dimension conformance;
Track A must demonstrate it before references are execution-ready.

Timing rows explicitly retain event/censor time and reason. Common-cap
administrative censoring is permitted. Early data-dependent ray-cap censoring
makes the primary time gate INCONCLUSIVE without independent-censoring
justification; never fabricate follow-up, extend one policy's cap or drop units.
Track E owns repeat aggregation: each event gives [t,t], each censor gives
[c,infinity]; equal finite median bounds identify an event, infinite upper bound
right-censors at the lower median, unequal finite bounds remain INCONCLUSIVE.

## Implemented preparation utilities

`experiments/tc-r1/reference_pipeline.py` provides a verified 30-pair corpus plan,
registered seed identities, prefix/escalation ledger, canonical-image checks,
actual artifact/metric-code/AlexNet-backbone/LPIPS-calibration weight bindings,
independent directional-MSE recomputation, scoring-reference mean, paired timing
orders, synchronized CPU timing wrapper and event/censor rows. Perceptual scores
come from Track E's separately validated metric producer; a hash-bound report
alone is not proof that its producer computed SSIM/LPIPS correctly. The reference
ledger is single-writer, rejects retries/identity changes and retains artifact
validation failures without silently escalating them. Cross-process locking and
EXR conversion remain integration responsibilities.

Read-only host inspection and corpus planning examples (outputs are ignored):

```powershell
python experiments/tc-r1/reference_pipeline.py inspect-host --storage C:/ --output results/local/host-observation.json
python experiments/tc-r1/reference_pipeline.py plan-corpus --repository-root . --manifest research/tc-r1/corpus/manifest.json --output results/local/reference-plan.json
```

The second command is usable after Track D's corpus is present. Plans explicitly
say final generation is unauthorized and native stream conformance unverified.
Tests use invented arrays/files/clock values, never scene rendering, reference
generation, model inference or TC-vs-baseline primary outcomes. Dedicated CI runs
these synthetic tests on Linux and Windows, in normal and optimized Python modes.
