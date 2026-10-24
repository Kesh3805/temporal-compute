# Amendment 0006: free hosted execution, single validated binary, references

Status: **adopted 2026-10-25 by the research owner (Claude, by maintainer
handoff), before any reference or comparative outcome.** The protocol, amendments
0001–0005 and all evidence are unchanged. Binding JSON:
[execution-host-amendment-0006.json](../../../research/tc-r1/execution-host-amendment-0006.json).

## Evidence this rests on

- **Hosted runners are free and adequate.** The repository is public, so
  GitHub-hosted `ubuntu-24.04` runners (4 vCPU, 16 GB, AMD EPYC 7763 in both
  measured runs) cost nothing. PBRT peaks at about 16 MiB; see the
  [measurement](../local-measurement-result.md).
- **The persistent worker is byte-equivalent and 12× faster.** It takes about
  33 ms per request; see the [worker validation](../worker-validation-result.md).
- **Builds are not byte-reproducible.** Three builds of the same pinned source
  produced three binary hashes (`2687c8ec`, `078378a4`, `713ec162`).

## 1. One validated binary

A single build job builds two binaries from pinned PBRT `b4ce968`: the
qualified e3 binary, and the worker binary (e3 plus the worker layer). In that
same job, before publishing, it must pass two checks on exactly those bytes:

1. The [worker equivalence contract](../../../research/tc-r1/worker-validation/contract.json),
   unchanged.
2. The reference-producer validation (section 3).

Only then is the worker binary published as an Actions artifact with 90-day
retention, together with its manifest and both validation reports. Every
reference and execution job downloads it and verifies its SHA-256 before use.
The execution freeze binds this hash. The worker binary serves both roles:
worker mode for policy runs, and batch mode for references (batch mode is proven
log-identical to the qualified binary).

## 2. Execution host and job layout

- **One job = one unit × one timing repeat.** A unit is a scene, frame and
  replicate; there are 240 units, so 720 jobs.
- **Each job runs all six registered policies sequentially.** Their order is the
  registered `timing-order` permutation for that unit and repeat, so a repeat's
  policies share hardware.
- **Each policy run** uses two persistent workers, one each for allocation and
  production, at 1 PBRT thread each, rendering concurrently. It uses the cached
  kernel and `execution_runner.PolicyRun`.
- **Run end** is the later of the final checkpoint and the common cap `C`
  (0005).
- **Concurrency** is at most 20 jobs (the free limit).
- **Disclosure.** Repeats of a unit may land on different CPU models. Every job
  records `lscpu`. Analysis reports how many units have repeats on mixed CPU
  models and a sensitivity analysis restricted to single-model units. That
  sensitivity is reported only; it is not a gate.

## 3. Reference production

- **Producer.** The worker binary in batch mode, 4 threads, renders the full
  frame with the stream's registered PBRT seed and the complete prefix
  `[0, spp)`. PBRT's float32 PFM output is converted exactly to canonical
  float64 `.npy` (`reference_producer.py`).
- **Producer validation.** On non-primary fixtures at 1 and 4 threads, the
  producer image must equal the per-pixel mean of the per-sample records within
  the frozen E2 tolerance. This checks orientation, seed and Film estimator
  (`reference_validation.py`). It runs in the build job.
- **Matrix.** 30 frames × 2 streams at 8192 spp, the corpus verified in every
  job.
- **Convergence.** Uses the existing `reference_metrics.report` and
  `reference_pipeline.pair_record`. Frames that fail escalate to 16384, then
  32768, regenerating the full prefix. Every level is retained.
- **Halt.** A frame still failing at 32768 halts that scene and the PASS gate,
  as registered.
- **Retention.** Images and records are retained as Actions artifacts and
  hashed in the repository; frames' scoring references are fixed before
  execution. The float32 PFM path is disclosed: a relative rounding of about
  6e-8 per value, far below the 1e-4 convergence bar.

## 4. Common cap C

`C` is calibrated once, before execution:

- uniform policy, worker and cached kernel;
- the non-primary 256² measurement fixture;
- on a hosted runner;
- to `A_u + 2^26`;
- three repeats.

`C = 2 ×` the median measured wall time, rounded up to a whole minute. That is
0005's rule, with the one available non-primary 256² fixture as the calibrated
class. Scenes with fewer rays per sample need more requests to reach the last
checkpoint; their runs end at the last checkpoint after `C`, and the run-end
rule already covers this. `C` is bound in the execution freeze and never changed
after outcomes.

## 5. Scoring and retention per job

- After each policy run, its production snapshots are scored offline against
  the frame's scoring reference: relative MSE, SSIM, LPIPS and the worst 16×16
  region, with the pinned metric stack.
- The four checkpoint images, all snapshot scores and hashes, the run record and
  the decision trace are retained. The snapshot images themselves are
  discarded after scoring.
- The determinism check requires checkpoint image hashes to be identical across
  a unit's three repeats. A mismatch is a correctness failure that blocks PASS.

## Limits

Hosted runners are shared virtual machines, so timing noise is higher than on a
dedicated host. This is mitigated by within-job pairing, seeded order and
three-repeat medians, not eliminated. No GPU, renderer or transport change is
made, and no corpus, policy or threshold changes. Issue #9 stays open.
