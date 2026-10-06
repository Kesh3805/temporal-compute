# Renderer qualification status

No candidate currently passes all five requirements. No registered corpus assets or controller outcomes were used.

| Requirement | Mitsuba 3.9.1 scalar probe | PBRT-v4 CPU |
|---|---|---|
| Arbitrary bounded regions/batches | Demonstrated for a 24-pixel rectangle, eight individually keyed samples per pixel | Stock bounded synthetic throughput probe prepared; arbitrary sample-index batches remain unimplemented |
| Complete actual ray accounting | Not satisfied: native C++ path rays are not all exposed through this Python wrapper | Native regular/shadow counters require audit against every supported path type; not yet qualified |
| Paired sample stream control | Exact 192-sample replay after reorder in this fixture; seed map is qualification-only | Sample-level replay fixture still required |
| Intermediate statistics | Count/mean/unbiased variance/standard error demonstrated; regional/error-reduction/cost adapter remains | Common statistics adapter remains |
| Feasible full experiment | Tiny scene measurement only; insufficient evidence | Workflow measurements pending; insufficient evidence |

Retained local evidence: `research/tc-r1/qualification/mitsuba-windows-scalar.json`. Reproducible probe: `experiments/tc-r1/qualify_mitsuba.py`. This fixture uses the native path integrator, not an independently substituted Python path tracer. Its per-sample 32-bit seed map is not approved for the large corpus: collision handling and a frozen paired stream design remain required.

The 16×16 native synthetic render is too small for a reliable production estimate. Its recorded projection from 32,212,254,720 camera samples is diagnostic arithmetic only, not a feasibility claim. Camera samples are not actual rays. Qualification must add sufficiently long repeated production/reference workloads, representative unrelated materials/path complexity, actual counters, accumulation/trace/storage costs and analysis timing. Full per-sample traces at reference scale may be impractical; retain auditable bounded action/counter records and freeze retention before execution.

PBRT's workflow pins `b4ce9687e6c695f5582997c61b0c66cf064bdb4a` and uses the stock path kernel on an unrelated sphere. It reports scheduled camera samples separately from native statistics; scheduled counts must not be relabeled measured ray counts. A successful build/throughput run does not establish complete qualification or select CPU as the experimental backend.
