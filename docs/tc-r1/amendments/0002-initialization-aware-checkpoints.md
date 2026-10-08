# Proposed amendment 0002: initialization-aware ray checkpoints

Status: **proposed, before outcomes; not an active execution freeze**. Date:
2026-10-08. The original protocol commit
`99ad341775ed3e60bd262134783eeb2244700e76`, registration/tag, inputs and results
remain unchanged. Adoption needs an explicit maintainer decision in the single
integration gate. No primary comparative rendering has occurred.

The merged B/C candidates require identical 16-spp coverage on both allocation
and production streams before adaptive selection. At 256x256, this is 2,097,152
camera rays even without continuation or visibility. The original first total-ray
checkpoint, 1,048,576, cannot include completed mandatory initialization.
Substituting 2^22 without a path-work bound does not solve that constraint.

## Derivation independent of performance

For the selected surface-only CPU path at maximum depth D=8, each camera sample
has at most one camera charge, D generated continuation charges, and D visibility
charges. Thus Rmax=1+2D=17. The bound includes continuations discarded by roulette;
it does not assume a measured average ray multiplier or a favorable scene.

The source argument is conditional on the already admitted envelope: no media,
null-boundary skipping, subsurface transport, additional integrators or other
ray-producing features. In pinned
[PathIntegrator::Li](https://github.com/mmp/pbrt-v4/blob/b4ce9687e6c695f5582997c61b0c66cf064bdb4a/src/pbrt/cpu/integrators.cpp#L628),
the depth check precedes the direct-light and continuation operations. Each
eligible iteration can generate one continuation and call SampleLd once.
[SampleLd](https://github.com/mmp/pbrt-v4/blob/b4ce9687e6c695f5582997c61b0c66cf064bdb4a/src/pbrt/cpu/integrators.cpp#L764)
can make one Unoccluded call, which issues one predicate ray in
[integrators.h](https://github.com/mmp/pbrt-v4/blob/b4ce9687e6c695f5582997c61b0c66cf064bdb4a/src/pbrt/cpu/integrators.h#L48).
Source hashes and the exact corpus manifest are bound in
[the proposal](../../../research/tc-r1/integration/checkpoint-proposal.json).
This inspection does not certify a future binary or unsupported features.

Reserve the global worst-case initialization work:

`Imax = 2 * 256 * 256 * 16 * 17 = 35,651,584 rays`.

Propose **total charged-ray** checkpoints `Imax + [2^20, 2^22, 2^24, 2^26]`:

| Checkpoint | Proposed total charged rays |
| --- | ---: |
| 1 | 36,700,160 |
| 2 | 39,845,888 |
| 3 | 52,428,800 |
| 4 | 102,760,448 |

These are identical for every policy, scene, frame and seed. They preserve the
original four increments above a conservative initialization reserve, while
changing the total-budget range explicitly. They do not preserve the original
geometric spacing of total budgets; this is a methodological amendment, not an
operational workaround. The original hypothesis, metric definitions, thresholds,
comparators and paired statistical plan remain unchanged.

The reserve is **not an artificial charge**. Accumulate only validated actual
camera/continuation/visibility work from both streams, including discarded pilots,
from the beginning of initialization. Do not reset the counter, subtract pilot
work, charge Imax as observed work, normalize by spp, or choose a per-case offset
from performance. Since actual initialization is at most Imax, each first scored
checkpoint occurs after complete initialization, with at least the first original
increment available above that conservative bound.

## Complete paired requests and record overshoot

After initialization, a request is a maximum 256-pixel region with four additional
samples on each of two streams. Its charged-work bound is
`Jmax = 2 * 256 * 4 * 17 = 34,816 rays`.
Dispatch only while actual cumulative charge is below the next threshold. Complete
both streams and their paths, then score the first committed pair reaching that
threshold. Integer overshoot is at most Jmax-1 = **34,815 rays**. Never truncate a
long path or a paired request to force equality. Retain nominal threshold, actual
charge, overshoot, per-stream charges, sample ranges and failure evidence.

Matched-budget reports must disclose this bounded difference in actual work;
they cannot call differing overshot images exact equal-ray observations. Unknown
partial work invalidates that unit and the correctness gate. All losing/invalid
cases remain in the retained output. Native validation must independently verify
camera=1, continuation<=8 and visibility<=8 for each actual sample and both stream
ledgers. Any bound violation or unsupported path stops integration; do not widen
the schedule after inspecting policy performance.

## Remaining adoption gates

The calculation is executable without rendering. Selected-host native validation
must still prove the admission assumptions, complete initialization, independent
paired streams and bounded checkpoint behavior on non-primary fixtures. A
resource review must establish that this range is feasible on the selected host;
the formula supplies no runtime estimate. If it is infeasible, retain this version
and obtain another explicit pre-outcome decision. Never silently lower coverage,
change scenes, exempt pilots or choose budgets after comparative results.

The current analysis library still contains the original checkpoints. It must
consume the adopted amendment identically with the integrated runner before an
execution manifest can pass. This proposal changes neither library nor candidate
settings. The separate timing/stopping/censoring decision and actual host/time cap
remain open. No reference generation, execution tag or primary run is authorized
by this proposed document.
