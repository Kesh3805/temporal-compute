# TC-R1 bounded measurement result

This was executed once, on 2026-10-24 (UTC), in
[Actions run 40123453245](https://github.com/Kesh3805/temporal-compute/actions/runs/40123453245),
attempt 1, under [the contract](../../research/tc-r1/local-measurement/contract.json)
(SHA-256 `b9692a3c…`, matching the report). The host was a GitHub-hosted runner:
AMD EPYC 7763, 4 vCPU, 16 GB.

- It built the pinned PBRT with the unchanged qualified e3 instrumentation.
- It used one non-primary 256×256 fixture.
- It used no primary scene, produced no reference, and compared no policies.
- The measured phase took 152 s.

The retained files are `report.json`, the build manifest, the runner identity
and artifact hashes, all in `research/tc-r1/local-measurement/result/`.

## Results

| Quantity | Value |
| --- | --- |
| PBRT peak RSS (stock and logged) | **16–17 MiB** |
| Stock throughput, 1 / 2 / 4 threads | 0.46 / 0.83 / 1.03 M camera samples/s (includes process start for 1M samples) |
| Logged render, 1 thread | 5.5 s for 1,048,576 samples (about 2.4× stock) |
| Charged rays per camera sample | 2.05 mean |
| Retained log bytes per sample | 189.9 uncompressed; gzip ratio 2.93 |
| Per-16×16-region rays per sample | min 1.0, p5 1.0, median 2.53, p95 3.57, max 4.49; log sd 0.52 |
| Bridge seconds per 4-spp 16×16 request | 0.42–0.44 |

The bridge request time breaks down as follows (three repeats, 64 requests
each):

| Part | Time | Share |
| --- | --- | --- |
| Native process launch and render | 256 ms | 61% |
| Python kernel `observe()` | 92–109 ms | |
| Per-dispatch provenance hashing | 36 ms | |
| Log validation | 19 ms | |
| Other | 16 ms | |

## Interpretation

- **Memory was never the constraint.** PBRT uses about 16 MiB on this kind of
  scene. The Python process peaked at about 600 MiB, mostly per-pixel kernel
  state at 256². The 8 GiB admission rule of 2026-10-08 had no evidential basis.
- **Dispatch overhead, not rendering, dominates.** Rendering 1,024 samples takes
  about 6 ms of the 256 ms native time, so the remainder is launch and parse.
  The persistent worker removes that, the cached kernel removes the `observe()`
  cost, and the persistent backend removes per-dispatch hashing. The projected
  request cost is about 40 ms. That is a projection to be confirmed by
  worker validation.
- **The cost lever on this fixture is moderate.** Region log sd 0.52 implies a
  theoretical cost-aware gain of about 6% over sample-proportional allocation.
  It is one non-primary fixture, not the corpus. It does not predict the primary
  outcome and is not used to tune anything.

Full-workload feasibility remains INCONCLUSIVE until the persistent worker is
validated and timed. Issue #9 stays open.
