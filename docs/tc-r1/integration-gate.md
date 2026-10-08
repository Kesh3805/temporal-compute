# TC-R1 integration decision gate

Status: **open decisions and validation; not execution-ready**. A-F are merged on
main at `1d295420aaa60a72782b3c824ebe46f8f42d392c`. This is the only next research
workstream. No further feature-track architecture is authorized by this gate.

| Track | Reviewed head | Merge commit |
| --- | --- | --- |
| A / #15 | e69364b0b1532fa80419ecd360c86494872fb8e1 | 99de3cf11df7d90c309b9eaf619440016c769d47 |
| B / #16 | 5731f81f64b8efa6ac8c5d16c478c74d58972b86 | d8a57901cbc75fb2e032aec14e130c994e0e103e |
| C / #17 | 0f9183eca0056954a628f605b35925760a8f422f | 1c9b8dcebad565b1ff5526024f8ab47f7c0e050d |
| D / #18 | 4caadb9256fde97b6a0969fdff1fa98895d740cb | 4a9dfdd35e96cfbbf8a95b50902e4698ead7fdec |
| E / #19 | 9256ecf30618ffbe2c8c0deac9788da1ba0b9fe5 | 1d295420aaa60a72782b3c824ebe46f8f42d392c |
| F / #20 | d0a9e0a15afefdccc2e80aa41ce80472e0a52431 | e69652053602665e37d802a9d2624315bc3498ce |

The original protocol and amendment 0001 remain preserved. E2 remains FAIL TO
QUALIFY due to incomplete evidence. E3 remains PASS, with exactly one authoritative
execution, Actions run 37578416061, all 298 retained hashes unchanged, PBRT CPU
selected. Neither candidate policies nor authored assets certify the experiment.

## Two decisions before host-dependent work

1. Review/adopt [proposed checkpoint amendment 0002](amendments/0002-initialization-aware-checkpoints.md).
   Its common reserve is derived from the pinned path bound, not intuition or
   observed comparative speed/quality. Actual accounting remains fully charged.
2. Select the actual dedicated CPU host. The maintainer explicitly kept host
   selection pending on 2026-10-08. GitHub Actions is validation infrastructure
   only. No chosen host, worker configuration, cap or resource allocation is
   implied by a local inventory or a green CI job.

The observed local candidate is Windows 11 Pro, i5-1135G7, four physical cores /
eight logical processors, approximately 16 GiB RAM. Its storage was nearly full;
reproducible Rust debug-cache cleanup restored space for repository work. It is
unselected and has not passed execution feasibility. Do not commit a transient
free-space observation as a promise of scientific storage capacity.

The selected-host manifest must bind stable host identity and isolation, CPU/core
topology, RAM, storage filesystem/capacity/free-space reserve, OS, PBRT upstream and
all submodule revisions, compiler/CMake/Ninja versions, flags, qualified source
hash and newly built binary hash. Bind worker count, exact CPU affinity, PBRT
thread count, nested threading (including Torch/BLAS), power/frequency policy,
warmup, synchronized CPU wall-clock boundaries, three repeats, seeded paired order,
checkpoint metric cadence, actual time cap and maximum storage/resource effort.
Validate filesystem evidence publication and exclusive ownership/recovery.
Do not reuse the Linux E3 binary hash as a claim about another build.
The [unfilled host template](../../research/tc-r1/integration/host-template.json)
records these missing decisions explicitly; its null fields and false authorization
flags are not defaults that an execution runner may silently fill.

## Ordered validation with explicit evidence

| Gate | Required evidence | Current state |
| --- | --- | --- |
| Checkpoints | Approved amendment; pinned source argument; actual class limits; complete paired initialization; threshold/overshoot tests | Proposed arithmetic/source argument only |
| Host/build | Selected dedicated CPU manifest, toolchain/submodules/flags/binary hashes, isolation and capacity | Pending maintainer selection |
| All 30 assets parse | Pinned PBRT parser invoked for every exact-hashed asset; command/stdout/stderr/status retained per asset; failures retained | Not executed |
| Production bridge | Non-primary native fixtures verify records/Film estimator, batching, thread/region order, fresh evidence and failure containment | Retained-parser tests alone; live check pending |
| Paired streams | All scene/frame/replicate stream identities reconcile; native projected seeds and actual per-pixel/index identities agree; both streams fully charged | Offline identity tests pass; native reconciliation pending |
| Strong baseline | Published-method mapping/deviations and fixed beta; independent scale/rare-event/applicability validation without TC results | Prototype equations tested; production competence unproven |
| Stopping/censoring | Complete paths/paired work, common cap/cadence, retained failures, identifiable medians and justified time estimand | Requires integration decision and non-primary fixtures |
| Integrated dry-run | All policies/ablations on unrelated synthetic fixtures, common runner/evidence joins, accounting/timing/error assertions | Small numeric joins pass; full native dry-run pending |

Parser acceptance is distinct from runtime construction and native rendering.
The pinned CLI's formatting path can parse syntax without a render; it cannot
certify material construction, transport behavior or reference convergence. Any
native fixture rendered here must be non-primary, with settings fixed before its
correctness results. Do not invoke the E3 execute-once workflow or retain another
E3 scientific result.

For time inference, the Track E implementation rejects unsupported positive
survival tails, interval-censored three-repeat medians and unjustified early
data-dependent censoring. A ray-cap exhaustion before a common time cap is not
automatically independent censoring. Do not invent idle follow-up, assign failure
zero time, drop a unit, or mark the primary time gate valid merely because KM
returns a number. Resolve a supported timing/stopping design before freezing it;
if a semantic amendment is needed, preserve the original and register it explicitly
before outcomes. No automatic analysis relaxation is part of this decision gate.

## Execution-freeze line

After decisions and all native/non-primary checks pass, prepare final independent
reference A/B images on the unchanged corpus, including prescribed escalation,
hashes and convergence evidence. This requires a separate concrete resource
authorization on the selected host; host selection is currently pending.

Then bind assets/licenses, streams, admitted renderer/binary, common kernel,
validated conventional methods, controller/ablations/configs, estimator/stopping,
metrics/models, adopted checkpoints, hardware/timing/cap, censoring/bootstrap/PASS
analysis and retained-output runner in one execution-freeze manifest. Its validator
must refuse incomplete, dirty or changed inputs. Only the separate approved tag
`tc-r1-execution-preregistered` permits **one real TC-R1 comparative run**.

No primary performance pilot, TC-vs-baseline outcome, reference render, final
execution manifest or execution tag is created by this initial decision record.
Issue #9 stays open. Missing evidence stays unverified; it is not a renderer
failure or scientific result.
