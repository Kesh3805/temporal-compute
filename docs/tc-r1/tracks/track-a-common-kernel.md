# Track A preparation: common progressive kernel

Status: concrete interface review. [TC-R1E3 selection PR #14](https://github.com/Kesh3805/temporal-compute/pull/14) merged unchanged at `3c4a1990f4a80e8f12f6fbf10bca81fdb22cf3ed`; scientific run `37578416061` remains its sole authoritative execution. This document neither changes E2's FAIL TO QUALIFY nor freezes the TC-R1 experiment.

The versioned [kernel contract](../../../research/tc-r1/kernel-contract.json) is committed before implementation. It fixes rectangular regions, a two-action policy boundary, sufficient statistics, observations, sample ownership, native stream mapping and failure semantics. Shared final image encoding is C-order little-endian float64 `H,W,RGB` NumPy arrays; policies see immutable numeric state only. There is no generic runtime or plugin layer. Integration still must settle actual hardware, checkpoints/overshoot and estimator/stopping limitations before execution freeze.

The implementation exposes one TC-R1-specific adapter over PBRT-v4 CPU float path integration at upstream `b4ce9687e6c695f5582997c61b0c66cf064bdb4a`, preserving the selected surface-only envelope, sampler, Film, filter and charged-ray definitions. It reuses the qualified mechanisms rather than introducing a renderer or cross-domain runtime. No rendering occurs in this PR: numeric fixtures and the retained native E3 artifact establish bridge/parser and state behavior without rerunning qualification. Independent live production-adapter validation, stream collision reconciliation across all final identities, estimator/stopping justification and budget/time-cap integration remain mandatory before the execution freeze; these are not claimed complete by retained-artifact tests.

`progressive_kernel.py` implements the two-action boundary and immutable observations. `pbrt_batch_backend.py` binds source/binary/scene hashes, requires an admitted scene hash set from the strict corpus verifier or independently reviewed synthetic fixtures, checks fresh per-sample native class ledgers/query deltas/Film, and retains failed work explicitly as unknown. Each request runs the unchanged native renderer synchronously; process/build/scene overhead is included in measured batch cost. Its scalability must be measured on the selected host rather than assumed. Policies cannot see reference images through this interface. This is the narrow common interface for B/C, not a declaration that the integrated experiment is ready.

## Interface to review and freeze before implementation

Tracks A, B and C must agree on a versioned request, observation and trace schema before writing their implementations. The following are required fields and invariants, not an already frozen API:

| Operation | Required contract |
| --- | --- |
| `SampleRegion(region, additional_samples)` | An explicit, validated set of pixels; a positive bounded per-pixel sample increment; run/scene/frame/stream identity; and deterministic next sample indices owned by the adapter. Requests cannot choose or skip samples based on their values. |
| `ObserveState()` | A read-only committed-state snapshot with version, region membership and statistics described below; no hidden rendering, reference access or future samples. |
| `Stop()` | A reason and final committed checkpoint; no additional samples, estimator replacement or unrecorded work. |

Each policy sees the same sample counts, mean, variance, standard error, regional aggregates, recent improvement, measured sample cost and charged rays at the same permitted observation cadence. Freeze whether each statistic is per pixel, per RGB channel or a regional scalar, its units, aggregation weights and unavailable-value representation. Specify behavior for zero/one observations and zero-cost histories; do not silently replace undefined uncertainty with certainty.

Freeze a mergeable sufficient-statistic representation (count, mean and second central moment), the final Film estimator and the exact relationship between observation statistics and final reconstruction. Define recent improvement from legal previous snapshots, never reference error. Record both actual charged rays and elapsed cost with their measurement boundaries. All policies get identical available information; cost/state collection overhead belongs in end-to-end time.

Freeze allocation versus production stream separation, per-pixel/sample/dimension mapping and estimator weights before baseline/controller implementation. If independent pilots are needed for sampling/stopping validity, their rays and time are charged for every policy. Optional stopping and selection bias require an explicit estimator argument and documented limitations; a deterministic replay alone is insufficient.

Requests must complete indivisible paths rather than truncate long paths at a budget. Review one common checkpoint, overshoot, overlap and duplicate-request rule; charge every permitted generated ray once, including probes discarded from Film. Changes in tile boundaries, execution order or thread count cannot change sample identities. `SplitRegion` is excluded unless separately justified and frozen symmetrically before implementation.

## Acceptance tests required before track completion

- Reject invalid bounds, empty regions, nonpositive/excessive batches, duplicate sample ownership and forbidden requests; verify observation/stop do not create rendering work.
- On unrelated synthetic fixtures, compare one-shot `[0,16)` with four consecutive batches, reordered batches, one versus multiple threads, and one region versus tiles. Verify sample identity separately from Film estimator equivalence using the preserved absolute/relative tolerance `1e-6 + 1e-5 * max(abs(a), abs(b))`.
- Compare merged statistics against independently calculated numeric fixtures, including unequal batch sizes, empty/one-sample histories and constant samples. Test finite-value failures and stable aggregate weights.
- Retain analytic estimator checks and qualified dielectric transmission/triangle coverage without changing historical evidence. Check common generated-ray ledgers independently of spp or renderer statistics, budget overshoot, discarded pilots and failure retention.
- Exercise mocked policies receiving identical snapshots; prove reference images, offline quality metrics and future samples are unreachable from the policy adapter. Verify trace replay captures request, state version, work charged, estimator update and errors.
- Establish an estimator/stopping argument and synthetic tests for the chosen stream/weight rule; all policies use that same rule. No policy-quality benchmark is an acceptance test here.

## Dependencies and completion boundary

Track A supplies the reviewed schema to Tracks B/C and stream/retention boundaries to Track F; asset identifiers come from D, while E owns offline metrics. Planning may proceed concurrently. Adapter implementation followed E3 selection and the shared schema freeze. Kernel and backend instances have one exclusive owner; interrupted requests propagate the interruption while invalidating uncertain work, blocking reuse/scoring and retaining failure evidence. Process termination/restart ownership still requires the integration runner's durable evidence protocol. A is complete only with reviewed executable contract, passing independent synthetic tests, pinned revisions/settings and documented limitations. Actual hardware/timing configuration remains a later execution-freeze dependency.

No registered corpus render, reference generation, baseline comparison or TC-vs-baseline outcome belongs here. No reference can be supplied to a policy. All assets, algorithms, baselines, references, metrics, analysis and hardware must subsequently be bound by `tc-r1-execution-preregistered` before any comparative experiment. Issue #9 remains open.
