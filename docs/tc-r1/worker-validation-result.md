# Persistent worker validation: PASS

The validation ran once, on 2026-10-24 (UTC), in
[Actions run 40124315189](https://github.com/Kesh3805/temporal-compute/actions/runs/40124315189),
attempt 1, under the [frozen contract](../../research/tc-r1/worker-validation/contract.json);
the report's contract hash matches. Two binaries were built in the same job
from pinned PBRT `b4ce968`:

| Binary | Instrumentation | SHA-256 |
| --- | --- | --- |
| Qualified | Unchanged e3 instrumentation (source `ace0c1f2…`) | `713ec162…` |
| Worker | e3 plus the worker layer (source `7223b017…`) | `e7fa3fed…` |

The host was an AMD EPYC 7763 with 4 vCPU. Only non-primary fixtures were used.
The evidence is in `research/tc-r1/worker-validation/result/`.

| Check | Result |
| --- | --- |
| Byte equivalence | 0 mismatches in sample, event and Film log lines (sorted multisets), request by request. Three 16×16 fixtures × 11 requests and the 256² fixture × 8 requests: whole, quadrant, odd and edge regions; progressive, out-of-order, single-index, revisited and large ranges. Worker at 1 and 2 threads. 20,911 and 22,304 sample lines per comparison. |
| Batch-mode identity | The worker binary without `TC_R1W_WORKER` writes logs identical to the qualified binary on all small-fixture requests. |
| Kernel run | 24 amended variance-guided decisions on four quadrants: identical requests, observed states (except measured wall cost), trace and final image. `CachedProgressiveKernel` with the worker matches `ProgressiveKernel` with the qualified bridge. |
| Failure | Killing the worker makes the next request fail (`BrokenPipeError`) as unknown work; the backend then refuses reuse. |
| Timing (informational) | 4-spp 16×16 request on the 256² fixture: 0.399 s for the qualified bridge and `ProgressiveKernel`, against 0.033 s for the worker and cached kernel, a **12.1× speedup**. |

## Consequence

The qualified per-sample records, charged-ray classes and Film estimator are
reproduced exactly. The qualification of the e3 bridge therefore carries over
to the worker for the tested envelope. Amendment 0005 section 3(a)'s
re-validation requirement is met.

The production path is the worker with the cached kernel. At about 33 ms per
request, the projected cost of one policy run to the last checkpoint falls from
hours to minutes. The full schedule is set in amendment 0006. Issue #9 stays
open.
