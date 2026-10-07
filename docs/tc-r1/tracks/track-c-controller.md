# Track C — minimal TC controller freeze candidate

Status: draft preparation only. This document scopes later implementation; it does not implement or freeze a controller. It depends on the pending [TC-R1E3 selection PR #14](https://github.com/Kesh3805/temporal-compute/pull/14). That change retains a PASS in scientific [run 37578416061](https://github.com/Kesh3805/temporal-compute/actions/runs/37578416061); merge/review completion must establish its selection record on main before production integration. E2 remains FAIL TO QUALIFY due to incomplete evidence, not an observed PBRT failure.

Related research issue: [#9](https://github.com/Kesh3805/temporal-compute/issues/9), which remains open. The [original protocol](../preregistration.md), [comparator amendment](../amendments/0001-comparator-selection.md) and historical evidence remain unchanged. No execution freeze or TC-vs-baseline outcome is created here.

## Dependency and interface acceptance

Track A must review and freeze the concrete action/state schema, stream mapping, estimator, stopping and charged-work semantics before Track C implementation consumes them. Track B must use that same reviewed interface. Shared information consists of sample count, mean, variance, standard error, region aggregates, recent observed improvement, measured sample cost and charged rays. Definitions, units, update cadence, unavailable-value handling and stream provenance must be explicit; an unavailable observation cannot be replaced with reference error or a controller-only probe. Every policy receives identical legal information and accounting opportunities.

The minimal action space is `SampleRegion(region, additional_samples)` and `Stop`. A region names image-space work, not transport internals. `SplitRegion` is excluded from the initial candidate; any later inclusion requires a justified, reviewed pre-outcome decision and symmetric availability to all policies. No bounce control, denoising, reconstruction change, reuse, path guiding, material approximation, GPU migration or generic cross-domain runtime belongs in this track.

All sampling uses the selected pinned PBRT `b4ce9687e6c695f5582997c61b0c66cf064bdb4a`, qualified CPU float native path and E2 surface-only envelope. Production sample counts and stream configuration must be bound by Track A and the execution freeze; the E2 16-sample fixture configuration is correctness evidence, not a final production/reference cap. Controller allocation cannot choose favorable future sample values.

## Candidate and correctness requirements

Later code must define one executable marginal gain/cost heuristic, with equations, uncertainty handling, exploration, initialization, minimum coverage, batch size bounds, predictor state, measured-cost treatment, ties and deterministic ordering. Local ranking is a candidate heuristic with no claim of optimal marginal value. Constant-cost equivalence to conventional allocation must remain visible rather than creating an artificial distinction.

Freeze the two required ablations with the candidate: no state feedback after initial observations and equal-cost ranking. All candidate and ablation settings must be declared before comparative outcomes. Their purpose is to test feedback/cost contributions; this draft supplies no results or parameter choices.

Reference streams/images, production-reference errors and future samples are inaccessible to allocation. Any pilot/probe rays, including discarded probes, are charged and included in runtime under the same rules as baselines. Allocation/production stream independence, estimator weights and optional-stopping limitations need an explicit reviewed correctness argument. `Stop` follows a common registered rule and cannot use hidden reference access or censor long paths to fit a budget. No unbiasedness or convergence claim is accepted merely because a synthetic test is green.

## Acceptance before the execution freeze

- Track A's shared interface and charged-work/overshoot semantics are reviewed and frozen; Track B and C consume the same revision.
- Candidate and both ablations are executable, versioned and deterministic under declared stream/tie semantics, with settings and dependencies pinned.
- Synthetic non-primary fixtures verify action legality, finite estimates, deterministic traces, bounded batches, information boundaries, charged probes and actual stopping behavior. Independent estimator/stopping review records its proof or limitations.
- Implementation does not read references or primary-corpus outcomes, and no TC-vs-baseline comparison or primary performance pilot has run.
- Traces retain state, candidate estimates/actions, chosen action, observed update and actual charged work/runtime; the execution freeze binds the final implementation hashes.

Missing prerequisites block freeze readiness. They do not authorize tuning on the registered corpus, widening the action space or another renderer gate. Review remediation addresses implementation/reproducibility defects within scope. A material research change requires an explicit pre-outcome decision preserving the existing protocol and evidence.
