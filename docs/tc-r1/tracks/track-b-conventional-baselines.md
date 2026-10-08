# Track B preparation: independently validated conventional baselines

Status: executable allocation candidates for review; not production baseline certification. [TC-R1E3 selection PR #14](https://github.com/Kesh3805/temporal-compute/pull/14) and the Track A interface PR #15 are merged. E3's sole scientific run remains `37578416061`; E2's FAIL TO QUALIFY remains unchanged. The [method decision](track-b-method-decision.md) and exact contract were committed before implementation at `1b550a29f2466c8719e05a397b7c97297eb6c2cd`. No native rendering occurs in this PR.

`baselines.py` implements uniform, a specifically labeled RGB/region batched MC-UCB adaptation and variance-guided allocation. `paired_policy_runner.py` is a fixed-decision-horizon prototype consuming the merged kernel; it mirrors allocation/production requests, exposes allocation observations only and retains both actual ray charges. Source inspection documents no compatible native allocator in the selected pinned CPU path. The shared interface is numeric, not a process security sandbox. Actual-ray checkpoints/overshoot, time-cap censoring, optional-stopping correctness, independent native bridge validation and competent adaptive scale/applicability are still integration gates.

The required set remains uniform, a strong independently justified error/confidence allocator, variance-guided allocation, and a compatible PBRT-native adaptive method if genuinely available. The prototype's independent source, deviations and limitations are explicit; passing numeric equations is not proof of a competent production comparator. That separate requirement cannot be waived by a favorable TC outcome.

## Shared interface to freeze first

Use Track A's TC-R1-specific `SampleRegion(region, additional_samples)`, `ObserveState()` and `Stop()` contract. Every policy receives the same sample count, mean, variance, standard error, region aggregates, recent improvement, measured sample cost and charged-ray fields, including the same units, cadence and undefined-value rules. All policies share the pinned kernel/Film/sampler, stream mapping, estimator weights, minimum legal information, charged probe costs, indivisible sample completion, overshoot and stopping/checkpoint semantics.

No baseline can access references, offline production errors or future sample values. Adaptive requests cannot skip indices to select favorable samples. `SplitRegion` is excluded unless justified and frozen symmetrically across the experiment. Freeze minimum coverage, allocation and production stream separation, estimator/stopping argument, batch bounds, exploration, tie rules and failure behavior before any implementation is used.

## Method-specific acceptance requirements

| Method | Required independent evidence and tests |
| --- | --- |
| Uniform | Exact equal per-pixel allocation under the shared completion/budget rule; deterministic remainder handling; analytic/synthetic Film correctness; all work charged. |
| Strong conventional adaptive | A documented error/confidence objective, minimum coverage, explicit adaptive allocation and repeated updates, common budget/stopping rule, and estimator semantics. Record the source, equations, applicability assumptions, implementation mapping, parameters and deviations. Validate numerical decisions against independently calculated state fixtures and uncertainty behavior on unrelated synthetic cases. Do not claim a confidence guarantee beyond the method's assumptions. |
| Variance-guided | Frozen variance-to-allocation equation, initial coverage, treatment of zero/undefined/nonfinite variance, batch limits and deterministic ties. Test known constant/heterogeneous variance states independently of the implementation and enforce the shared estimator/work rules. |
| PBRT-native adaptive, if eligible | Inspect the selected revision and document the actual capability and compatibility with sample identity, charged work, estimator, state and checkpoints. Include a compatible method before execution; otherwise retain evidence explaining incompatibility or absence. Do not invent a native baseline or silently omit it. |

Use synthetic non-primary fixtures only for correctness and declared method validation. Freeze any parameter-selection procedure before exercising it, retain all tested cases and justify competence from the method and validation rather than selecting settings to make TC look good. Track B cannot observe TC performance, run primary-corpus comparisons or choose a weak variant after controller results.

## Required shared regression checks

- Mock the adapter and prove identical observation access, stream/sample ownership and common budget accounting for every baseline. Verify unavailable statistics cannot yield spurious certainty or divide-by-zero rankings.
- Test minimum coverage, bounded repeated updates, deterministic ties, stopping, nonattainment and finite failure records. Test charge retention for allocation/probe samples omitted from the production image and for indivisible-path overshoot.
- Independently validate estimator/stopping semantics with analytic or numeric fixtures; adaptive sample means require a bias argument, not just image resemblance. Validate each implementation against its declared equations and source assumptions.
- Test the published-method mapping and implementation deviations, including rare/noisy observations, without tuning on the registered corpus. Preserve conventional equivalence when methods coincide under special conditions.
- Ensure all methods remain individually reportable. Track E must select one globally best conventional quality method and independently one globally best conventional time method under amendment 0001; per-case stitched winners cannot be a primary/time comparator.

## Dependencies and completion boundary

Track A owns kernel/state/stream implementation; B consumes its frozen schema and supplies policy definitions, configuration hashes, validation evidence and eligibility decisions to the execution freeze. Track E owns comparator/statistical analysis, C owns the controller and its ablations, and D/F own assets/references/hardware. B is complete only when each required conventional method is justified, independently validated and executable under the same adapter. Missing competent adaptivity prevents execution readiness.

No reference access, reference generation, TC-vs-baseline outcomes or comparative policy-quality benchmark is authorized by this planning PR. All assets, algorithms, baselines, references, metrics, analysis and hardware must later be bound by `tc-r1-execution-preregistered` before the first comparative run. Issue #9 remains open.
