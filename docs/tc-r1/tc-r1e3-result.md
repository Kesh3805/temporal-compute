# TC-R1E3 result — PBRT CPU selected

**E3 PASS: explicit transmission coverage and triangle coverage both pass. PBRT CPU is selected as the TC-R1 experimental kernel for the frozen E2 surface-only envelope.** This is substrate qualification, not a controller advantage or full execution freeze. E2 remains FAIL TO QUALIFY due to its incomplete evidence; its files and result are unchanged.

Pre-E3 contract commit: `b8b63e22f4b8b47267eeb8a281e8c980c68b2197`. Sole scientific [Actions run 37578416061](https://github.com/Kesh3805/temporal-compute/actions/runs/37578416061) at execution-marker head `b680605` built pinned PBRT `b4ce9687e6c695f5582997c61b0c66cf064bdb4a` with CPU float Release native path, existing sampler/seed/Film/box/tolerance/feature semantics. Build/source/instrumentation/binary/dependency/compiler hashes and flags are retained in `research/tc-r1/e3/build-manifest.json`.

The dielectric fixture observed 1,952 native BSDFSample.IsTransmission events in the [0,16) one-shot central region. Each has a unique pixel/sample/continuation ordinal and lies within that sample's already charged continuation sequence. Camera=1,024; generated continuations=2,052; visibility=0; charged total=3,076. Transmission is a classification, not a new charged class. Direct trace deltas and the unchanged common/class event identities pass.

The second scene contains only a two-triangle mesh. It exercised surface continuation and direct-light visibility; no sphere can account for those interactions. Primitive/BVH intersection tests are excluded from rendering-ray counts. The report retains counts for every evaluated batch/tile/thread configuration.

Both fixtures passed 26 evaluated calls each: exact keyed sample identity, one-shot versus four progressive batches, forward/reverse order, one/two threads, whole region/four tiles, sample mean/native Film and count-weighted Film equivalence. Every linear RGB channel passed the predeclared `1e-6 + 1e-5*max(abs(a),abs(b))` tolerance. Coverage observation introduces no transport/ray-count/Film architecture change. Combined with the preserved E2/source audit, this closes its two specifically identified runtime coverage gaps; no additional material gap was identified in the admitted envelope.

Raw source fixtures, samples, Film records, transmission observations, class events, logs, images and build artifacts are retained in deterministic `research/tc-r1/e3/raw-artifacts.tar.gz`, with per-file and archive hashes in `artifact-hashes.json`. The report deliberately keeps E2's inherited diagnostic metadata rather than rewriting old evidence.

Kernel selection: PBRT-v4 at the exact pinned source, CPU float native path and frozen surface-only feature envelope, with the qualified experiment instrumentation. Subsequent production work must preserve those semantics or use an explicit pre-outcome decision. No media/subsurface/specialized integrator/GPU/texture/reconstruction extensions are selected.

No TC-vs-baseline outcomes, controller/baseline comparisons, registered assets, final references or execution-freeze tag were produced. Generation I and the TC-R1 hypothesis/gates are unchanged. Next work is the authorized independent execution-freeze tracks; no additional renderer gate. Issue #9 remains open.
