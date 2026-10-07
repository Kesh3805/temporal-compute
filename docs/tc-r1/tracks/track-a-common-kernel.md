# Track A preparation: common progressive kernel

Status: draft planning only. Depends on the pending [TC-R1E3 selection PR #14](https://github.com/Kesh3805/temporal-compute/pull/14) on `research/tc-r1e3-pbrt-coverage`, evidence commit `9984fd2`, scientific run `37578416061`. E3's retained PASS must be reviewed and merged before this becomes implementation work. This document neither changes E2's FAIL TO QUALIFY nor freezes the TC-R1 experiment.

The implementation will expose one TC-R1-specific adapter over PBRT-v4 CPU float path integration at upstream `b4ce9687e6c695f5582997c61b0c66cf064bdb4a`, preserving the selected surface-only envelope, sampler, Film, filter and charged-ray definitions. It will reuse the qualified mechanisms rather than introduce a renderer or cross-domain runtime. No implementation or rendering occurs in this preparation PR.

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

Track A supplies the reviewed schema to Tracks B/C and stream/retention boundaries to Track F; asset identifiers come from D, while E owns offline metrics. Planning may proceed concurrently. Adapter implementation waits for E3 selection and the shared schema freeze. A is complete only with reviewed executable contract, passing independent synthetic tests, pinned revisions/settings and documented limitations. Actual hardware/timing configuration remains a later execution-freeze dependency.

No registered corpus render, reference generation, baseline comparison or TC-vs-baseline outcome belongs here. No reference can be supplied to a policy. All assets, algorithms, baselines, references, metrics, analysis and hardware must subsequently be bound by `tc-r1-execution-preregistered` before any comparative experiment. Issue #9 remains open.
