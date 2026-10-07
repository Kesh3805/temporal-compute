# Track E preparation: metrics and analysis

**Implementation under review.** [TC-R1E3 selection PR #14](https://github.com/Kesh3805/temporal-compute/pull/14) is merged;
PBRT CPU is selected. This track implements numeric metrics and analysis using
synthetic fixtures only. It adds no rendering or comparative outcomes. E2 remains FAIL TO QUALIFY due to incomplete evidence, not an
observed PBRT failure. Related research issue: #9; this document does not close it.

The [original protocol](../preregistration.md) and
[comparator amendment](../amendments/0001-comparator-selection.md) govern this
track. No threshold, family, budget, seed or historical result changes. This plan
is neither the execution preregistration nor evidence for Temporal Compute.

## Interfaces reviewed before implementation

Track D supplies a versioned scene/frame manifest with ten scenes, family labels,
three fixed frames and hashes. Track F supplies independent converged references,
RGB image format, metric/model hashes, hardware/timing manifest and convergence
status. Track A supplies completed checkpoint images and exact charged work.
The runner supplies policy identities, all expected paired units and failure rows.

Agree a versioned record schema across A, D, E and F before implementing it:

- Key: manifest version/hash, scene, family, frame, paired seed, policy, checkpoint,
  timing repeat and stream identity. Quality has eight paired seeds; the three
  timing repeats are not additional quality replicates.
- Image: linear RGB array, dimensions, dtype/encoding, content hash, reference
  stream/hash and finite-value status. Keep display-space conversion explicit.
- Work: actual charged rays, camera samples, checkpoint budget, indivisible-sample
  overshoot and completion/failure reason; never derive ray cost from spp.
- Time: synchronized end-to-end elapsed seconds, common administrative cap,
  observation/checkpoint times, attainment flags, censor time/reason and complete
  timing coverage. Missing/invalid units remain visible and cannot pass.

The concrete numerical choices in [metrics-contract.json](../../../research/tc-r1/metrics-contract.json)
were committed before implementation and independently reviewed by the maintainer
agent. They fill execution details without editing the original registration.
Canonical images are finite C-order little-endian float64 H,W,RGB `.npy` files.
References A/B are separately retained; their arithmetic mean is the scoring
target only after symmetric convergence checks. Actual official AlexNet and
LPIPS calibration files have separately verified full hashes. Scoring never
downloads models implicitly.

The whole experimental interface remains subject to integration freeze.
Image layout, serialization, cap, checkpoint cadence, tie rules for case-level
win/tie/loss reporting, early-censor support and analysis failure handling must be
reviewed and pinned before implementation/outcomes. Preserve protocol exact ties
for selecting global comparators; no fitted tolerance may change that rule.

## Numerical implementation and known-answer acceptance

Use only synthetic numeric fixtures until execution freeze. Pin package revisions
and, for LPIPS, official AlexNet v0.1 architecture and weight hashes before loading
models. Fixtures must establish the numerical implementation independently:

| Component | Acceptance fixture and required behavior |
| --- | --- |
| Relative linear MSE | Hand-computed RGB arrays, zero-energy references, negatives and scaling; use `sum((I-R)^2)/(sum(R^2)+N*1e-12)`; keep raw errors and apply `1e-12` only for logs. |
| Display transform | Known transfer-function boundary values: clamp negative radiance, `x/(1+x)`, standard sRGB; no exposure adjustment. |
| SSIM | Identity and hand-computed local windows; RGB mean, 11x11 Gaussian sigma 1.5, K1 .01, K2 .03, range 1, valid-window mean. Reject images too small for that definition. |
| LPIPS | Identity plus pinned deterministic cross-check vectors against the official implementation; display RGB scaled to [-1,1], AlexNet v0.1 and verified weight hashes. No substitute perceptual model. |
| Worst-region MSE | Known 16x16 hot-region example and energy denominator; report maximum, region identity and distribution. Freeze edge handling; 256x256 divides exactly. |
| Aggregation | Hand-computed unequal frame/budget errors proving mean-log aggregation over 3 frames and 4 budgets per scene/seed, then equal scene/seed weighting across 10 scenes x 8 seeds. |
| Paired bootstrap | Known paired arrays, deterministic seed 734922, 10,000 stratified resamples within each scene, preserving every unit's frames/budgets; common resamples for every comparator and percentile 95% intervals. |
| Comparator selection | Construct crossed case winners proving one corpus-wide quality winner and one independently selected time winner; exact registered tie order; hold identities fixed during bootstrap. |
| RMST/censoring | Hand-integrated survival curves including all-attain, none-attain and tied event/censor times; include nonattainment, common cap, three-repeat medians, first and sustained attainment separately. |
| PASS gate | Construct independent boundary examples for every conjunct, one failing conjunct at a time, invalid-reference/estimator cases, missing units and censored cases. A missing or invalid prerequisite cannot become PASS. |

For time analysis, explicitly settle how registered ray-cap nonattainment maps to
right censoring. Do not extend a run's survival beyond observed follow-up without
a frozen supported estimator. If follow-up is insufficient to identify RMST to
the common cap, expose nonidentifiability rather than inventing event times or
dropping cases. The earlier synthetic selection helper's complete-cap shortcut
is not proof that production censoring is implemented.

## Required analysis outputs and unchanged gate

Retain each individual conventional method, ablations, original paired effects,
wins/ties/losses, quantiles, family results, all four budgets and every failed or
censored unit. Label regional/perceptual best-method envelopes as guards, never
a stitched primary/time policy. Compute the quality reduction as
`1-exp(mean(log(controller_error/baseline_error)))`.

The gate remains conjunctive: at least 10% primary reduction against the one
global quality comparator; beneficial intervals against every required baseline;
positive family reduction in at least four of five families; at least 90% of cases
within the 20% worst-region degradation guard; pooled and per-family SSIM/LPIPS
degradation at most .01; at least 5% common-cap RMST benefit against the one global
time comparator with a positive paired interval; and valid references, estimator,
baselines, accounting and provenance. No conventional-only success can establish
the TC claim. Preserve FAIL/INCONCLUSIVE meanings from the protocol.

Implementation acceptance requires independently checked known answers, complete
unit reconciliation, immutable model/code hashes and synthetic gate fixtures.
Comparative rendering and the execution tag remain future work. The execution
host, time cap, live metric cadence, runner accounting, estimator/stopping
justification and actual references are integration prerequisites; this library
does not assert those are complete.

## Executable input and report schema

`experiments/tc-r1/metrics.py` implements radiance/display metrics and verified
official LPIPS. `reference_metrics.py` produces hash-bound reference-only
convergence metrics for Track F. `prepare_metric_models.py` is an explicit
provisioning command; both backbone and calibration hashes must match.

`analysis.py` accepts a five-family map to two scene IDs per family, complete
quality rows, complete timing rows, native-baseline eligibility, a positive
finite common time cap, and exact prerequisite attestations. Integration must
verify file hashes and provenance before supplying those attestations; numeric
analysis alone does not authenticate experimental inputs.

- Quality key: `policy,scene_id,frame_id,replicate,checkpoint`; metrics
  `mse,ssim,lpips,worst_region`. Exactly ten scenes, f0/f1/f2, seeds 0..7 and
  all four registered ray checkpoints are reconciled for every policy, including
  `controller,no-feedback,equal-cost`. Additional trace/hash/accounting fields
  remain retained in the raw rows.
- Timing key: `policy,scene_id,frame_id,replicate,repeat` with repeats 0..2.
  `first` and `sustained` each map `mse,ssim,lpips,joint` to `[seconds,event]`.
  Track F's elapsed/follow-up/censor fields must be retained alongside these
  observations; `target_observations` derives attainment from recorded metrics.
- Repeat aggregation treats events as `[t,t]` and censored observations as
  `[c,infinity)`. Equal finite median bounds identify an event; infinite upper
  bound identifies right censoring; differing finite bounds are INCONCLUSIVE.
- KM handles tied events before censor removal and rejects unsupported positive
  survival tails. Data-dependent early ray-cap/failure censoring also blocks the
  primary time gate without justified independent censoring. Descriptive KM
  estimates do not establish that assumption; no idle/fabricated follow-up.
- Output retains every supplied quality/timing row, individual methods and
  ablations, comparator identities, family effects, paired ratios, quantiles,
  wins/ties/losses, per-budget summaries and pooled/family guard envelopes.
  Global quality/time winners are selected separately and held fixed in common
  paired scene-stratified resamples. The library's bootstrap-count test hook
  always forces INCONCLUSIVE unless it is the registered 10,000.

`pass_gate` returns INCONCLUSIVE when correctness/provenance/completeness or time
inference is invalid, FAIL when a valid experiment misses any registered bar,
and PASS only when every unchanged conjunct passes. No production runner or
execution-tag creation is part of this track.
