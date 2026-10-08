# Track C — minimal TC controller freeze candidate

Status: minimal controller contract and implementation work; not execution frozen.
PBRT selection [PR #14](https://github.com/Kesh3805/temporal-compute/pull/14)
and the deliberately small shared kernel interface [PR #15](https://github.com/Kesh3805/temporal-compute/pull/15)
are merged. E3 retains PASS in scientific
[run 37578416061](https://github.com/Kesh3805/temporal-compute/actions/runs/37578416061).
E2 remains FAIL TO QUALIFY due to incomplete evidence, not an observed PBRT failure.

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

## Concrete candidate v1, committed before implementation

`research/tc-r1/controller-contract.json` freezes the candidate settings. All
policies initialize every region to at least 16 samples/pixel using four-sample
requests, then use four-sample batches and geometry ties `(y0,x0,y1,x1)`. Track B
owns the same minimal paired harness: each chosen request executes on independent
allocation and production kernels, charging both; policy observation contains
only allocation state. There is no controller-only probe or production feedback.

For region area A and count n, define `Q=A²*sum(SE[c]²)`. This converts the shared
regional-mean standard error to integrated descriptive pixel uncertainty. The
constant-variance reduction heuristic is `model=Q*4/(n+4)`. Recent improvement
predicts `recent=max(A²*recent_improvement,0)*(n-4)/(n+4)`, falling back to model
when unavailable. Worsening signed improvement is clamped to zero, never rewarded.
Gain is `0.5*model+0.5*recent` with a fixed uncertainty bonus `0.25*model`.
Score divides their sum by `estimated_sample_cost*A*4`. That denominator predicts
the latest **allocation** request cost; it is not actual paired runtime. The
caller retains all paired work, overhead and timing independently.

Every 16th post-initialization choice explores the least-covered region, with the
same geometry ties. Other choices maximize exact finite score. Missing/invalid
counts, uncertainty or cost block scoring rather than invoking reference data.
The bonus and exploration period are engineering choices frozen before tests and
outcomes, without claiming calibrated confidence or optimality.

Equal-cost ranking replaces only the denominator by one. Under equal predicted
request costs it must select the same actions as the full candidate; that
equivalence is retained, including synthetic cases where it equals conventional
variance-guided allocation. No-feedback freezes the initial uncertainty/recent
coefficients and allocation costs, then decreases gain algebraically with its
own chosen sample counts. Later radiance/uncertainty/cost observations cannot
change its ranking; live counts only validate administrative action completion.
Both ablations retain the same coverage, batch size, exploration and action space.

The policy records snapshots, all candidate gain/bonus/cost/score values, reason
and choice. Subsequent observations and actual paired charged work belong to the
caller trace. Prototype stopping is an external fixed decision horizon, not an
experimental target/ray/time gate. Finite-budget stopping, estimator correctness,
common overshoot, references and execution resources remain integration blockers.
No scientific render, comparison or final execution tag belongs in this PR.
