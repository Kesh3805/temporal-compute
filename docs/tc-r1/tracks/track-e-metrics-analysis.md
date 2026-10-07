# Track E preparation: metrics and analysis

**Draft preparation only.** This PR adds no executable metrics, model downloads,
rendering or outcomes. It depends on the reviewed [TC-R1E3 selection PR #14](https://github.com/Kesh3805/temporal-compute/pull/14) before
implementation. E2 remains FAIL TO QUALIFY due to incomplete evidence, not an
observed PBRT failure. Related research issue: #9; this document does not close it.

The [original protocol](../preregistration.md) and
[comparator amendment](../amendments/0001-comparator-selection.md) govern this
track. No threshold, family, budget, seed or historical result changes. This plan
is neither the execution preregistration nor evidence for Temporal Compute.

## Interface proposal to review and freeze before implementation

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

These fields are proposed obligations, not frozen field names or a finished API.
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
| Display transform | Known transfer-function boundary values: clamp negative radiance, `x/(1+x)`, standard sRGB; fixed exposure for every image. |
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
Implementation, comparative analysis and the execution tag remain future work.
