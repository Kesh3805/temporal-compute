# TC-R1 — Marginal Compute in Path Tracing

**Status: protocol preregistered; not yet execution-ready.** This is a new Generation II gate, separate from TC-0/TC-S1. No renderer, controller, scene assets, reference images or TC-R1 outcomes exist in this repository yet. The protocol commit/tag freezes the research question, outcomes and acceptance rules. A second, explicit **execution freeze** must bind concrete assets, executable algorithms, metrics, analysis and hardware before any comparative rendering outcome. Do not describe this document as a frozen executable corpus.

## Hypothesis

> Given a fixed compute budget or fixed target image quality, a state-aware marginal-value controller can allocate rendering work more efficiently than uniform sampling and a strong conventional adaptive-sampling baseline.

The primary test operationalizes “more efficiently” as better quality at matched ray budgets **and** a useful end-to-end time benefit against competent adaptivity. A win against uniform alone cannot pass. Rendering success would motivate a new independent second-domain gate, not establish a universal runtime abstraction.

## Scope and action model

Use one shared path-tracing kernel and estimator, with allocation outside the kernel. The controller observes evolving estimates and selects a bounded batch of further sampling work for an image region, refines an allocation region if the frozen algorithm permits it, or stops under a common stopping rule. Record state → candidate actions/estimates → selected action → observed state. No EDF comparison is used to establish the primary claim.

All policies share integrator settings, BSDF/light sampling, termination, reconstruction and admissible sample sequences. No controller-specific denoiser, clamping, integrator improvement, reference access or learned oracle. Start without denoising or temporal reuse so allocation is the experimental change. Motion cases are independently rendered at fixed frame times; they do not establish reuse or animation-coherence gains.

Administrative refinement/stop must not receive infinite value/cost scores. A local expected-gain/cost ranking is a candidate heuristic, not an optimal solution; actual estimator, uncertainty treatment, cost prediction, exploration and tie rules must be frozen as executable code. Do not add a universal process trait or the full action list before this narrow gate supplies evidence.

## Required baselines and ablations

1. **Uniform sampling:** equal work distribution with the common estimator.
2. **Conventional adaptive sampling:** an independently justified error/confidence-based allocator with minimum coverage and explicit estimator/stopping semantics.
3. **Variance-guided sampling:** observed variance/error allocation, with the same observation and accounting opportunities as the controller.
4. **Renderer-native adaptive baseline**, if the chosen renderer supplies one compatible with the experiment. Include it before execution; document incompatibility rather than silently excluding a competent native method. A literature claim must match the actual published method, not a convenient renamed implementation.

Report all individually; strongest conventional means the best registered conventional aggregate, never a weak selected comparator. Adaptive and variance-guided methods must have concrete independent validation and their equations/settings pinned in the execution freeze. A weak homegrown baseline cannot support a PASS.

Register two controller ablations: **no state feedback after initial observations**, and **equal-cost ranking**. They test whether feedback and cost information explain a benefit. If the full controller is equivalent to a conventional method under constant-cost assumptions, preserve the equivalence instead of manufacturing distinctions. Uniform/no-feedback/equal-cost outcomes remain visible even when losing.

## Workload design independent of policy outcomes

Five mandatory scene families, two independently specified scene variants per family:

| Family | Intended challenge, not a measured result |
| --- | --- |
| Uniformly noisy | Little spatial allocation benefit; possible equivalence or overhead loss |
| Highly specular | Rare/long-path contributions and unreliable uncertainty estimates |
| Simple diffuse | Cheap conventional rendering; controller overhead may dominate |
| Motion-heavy | Changing geometry/visibility across independently rendered frames |
| Adaptive-sampling-friendly | Strong conventional adaptivity should already exploit uneven difficulty |

Planned resolution is 256×256. Every scene has three fixed frame times; static families repeat static geometry with distinct sample streams. Eight paired seeds per scene give **80 scene/seed units and 240 frame renders per policy**. These are planned definitions, not an existing dataset. Scene geometry, materials, lights, camera, shutter/frame times, units and asset licensing must be specified and hashed before comparative runs. The intended adversarial descriptions do not prove the generated scenes have their intended noise properties.

Master seed is 20261007. Derive independent streams using the first eight big-endian SHA-256 bytes of UTF-8 `tc-r1-v1|20261007|scene_id|frame_id|replicate|stream`, with replicate 0–7. Stream names distinguish `allocation`, `production`, `reference-a`, `reference-b` and `timing-order`. A counter-based per-pixel/sample-index random stream, algorithm and dimensions must be pinned before execution so allocations cannot secretly select favorable samples. Seeds are pairing devices, not independent real-world sampling evidence.

No workload selection, variant replacement or camera adjustment based on policy quality/speed. Synthetic kernel/metric tests and renderer correctness fixtures are permitted before execution freeze. Hardware/reference feasibility work may assess whether a render/reference is technically valid, but must not compare policies or optimize allocation parameters on the primary scenes. If assets or implementation cannot satisfy this protocol, create a versioned **before-outcome amendment**, preserving this registration; do not call unfilled fields frozen.

## Reference quality and estimator correctness

Use independent high-sample reference streams, initially 8192 camera samples per pixel per stream. “8192 spp” is a provisional reference effort, **not ground truth**. For each scene/frame, compare reference A/B and require relative linear MSE ≤0.0001, display SSIM ≥0.995 and LPIPS ≤0.01. If it fails, double both independently to 16384 then 32768 spp, with no controller outcomes exposed. If still invalid, halt that scene and the overall PASS gate; report the failure and require an explicit reference/protocol amendment. Do not delete a difficult specular scene or score an inconclusive reference as a success. Store reference hashes and convergence metrics before execution freeze.

Review data-dependent sampling/stopping bias. Adaptive policies must state whether allocation and production streams are independent, how sample means/weights are formed, and why optional stopping does not invalidate their correctness claims. No truncating a light path solely to hit a budget without a justified estimator. Test simple analytic/reference fixtures, energy/finite-value behavior and reproducible sampler/kernel outputs. The controller cannot access reference images, full production errors or future sample values to choose actions. Reference evaluation is analysis, not controller state.

All methods need the same legal information and charging rules. Any extra allocation/probe rays are included in their budget and runtime, including probes discarded from the final estimator. If independent pilot streams are used to avoid bias, their cost cannot be free or imposed only on a baseline. Correctness failure prevents PASS regardless of image scores.

## Outcomes and accounting

Fixed total-ray checkpoints are **2^20, 2^22, 2^24 and 2^26 per frame**. Count primary, continuation, shadow, allocation/probe and other traced rays. Camera samples are reported separately; spp is not ray count. One common rule for indivisible sample completion, permitted budget overshoot and image checkpoints must be implemented and pinned before execution. Do not bias the estimator by censoring long paths. Record actual rays, overshoot and incomplete work; unequal budget accounting invalidates matched-budget claims.

The primary quality measure is relative linear-radiance MSE:

`sum((image-reference)^2) / (sum(reference^2) + number_of_RGB_values * 1e-12)`.

For each scene/seed unit, average log relative MSE over the four budgets and three frames. Use a declared floor of 1e-12 only for logs; retain unmodified errors too. Equal weight the ten scenes and paired seeds. Primary effect against each baseline is `1 - exp(mean(log(controller_error / baseline_error)))` over those units. Positive means lower error. This summarizes error over the registered budget range, not universal perceptual quality.

Report terminal/checkpoint MSE, SSIM and LPIPS; **quality at fixed ray budget**; **rays traced**; sample counts; total wall time; controller/estimator/dispatch overhead; and maximum 16×16-region relative MSE. Use the reference-energy denominator within each region, with the same floor. Report the worst region and distribution, not just global average.

SSIM/LPIPS use the same fixed display transform: clamp negative radiance to zero, apply `x/(1+x)`, then the standard sRGB transfer without scene-dependent exposure. SSIM: RGB channel mean, 11×11 Gaussian window, sigma 1.5, K1=0.01, K2=0.03, range 1, valid-window average. LPIPS: official AlexNet v0.1 setting, fixed weight hashes, input RGB scaled to [-1,1]. Pin numerical implementations/package versions and preprocessing tests at execution freeze; do not switch the favorable perceptual model after outcomes. No claimed equivalence of these scores to human judgment.

For **time to target**, record each metric separately and a joint target: relative linear MSE ≤0.01, SSIM ≥0.95, LPIPS ≤0.10. At recorded checkpoints, report first attainment and attainment sustained at all subsequent checkpoints. Targets and tolerances are experimental bars, not measured acceptance standards. A run that never reaches target is right-censored at its registered ray/time cap, not dropped or assigned zero time. A common time cap and checkpoint evaluation cadence must be set before execution; no after-result extension for the controller alone.

End-to-end time includes allocation, state updates, rendering, dispatch, stopping checks and required live metric evaluation. Separate offline reference/reporting cost. CPU wall time is the initial default; a GPU backend, if chosen before execution freeze, must record synchronized elapsed time and GPU configuration. No GPU-seconds savings claim from CPU rays or simulated cost. Record hardware, OS/compiler, threads, warmup, renderer/model revisions and random paired policy order. Use three repeated timing executions; aggregate their per-unit median, and do not count repeats as extra image-quality replicates.

## Statistical plan and pass/fail gate

Use 10,000 paired stratified bootstrap resamples with seed 734922. Resample scene/seed units within each scene; keep the three frames and four budgets together. Use common resamples for every comparator and report pointwise percentile 95% intervals for the mean log-error ratio. Inference is conditional on the chosen ten scenes; it is not evidence about all rendering workloads. Record raw paired effects, wins/ties/losses, quantiles, per-family outcomes and every censored/failed case. No p-values or selecting a favorable perceptual/time outcome as the primary result.

PASS requires **all** of:

- Primary relative-MSE reduction ≥10% against the strongest conventional aggregate, with a beneficial 95% interval against every required baseline.
- Positive primary reduction in at least four of five scene families. Uniformly noisy/simple diffuse ties or losses must remain visible.
- At least 90% of scene/seed/budget/frame cases have worst-region MSE no more than 20% worse than the strongest conventional method at that matched checkpoint. Report per-family tails too.
- Pooled checkpoint SSIM is no more than 0.01 below, and LPIPS no more than 0.01 above, the best conventional score for that metric; no family can hide a larger mean degradation. These are guards, not a new primary metric.
- A ≥5% end-to-end restricted mean time-to-joint-target benefit against the strongest conventional time comparator, with positive paired-bootstrap interval. Integrate observed target-attainment survival up to the same preregistered time cap; keep nonattainment censored, and disclose that cap-bounded benefit is not eventual uncensored convergence. Freeze executable censoring/analysis fixtures before outcomes.
- Reference convergence, estimator correctness, baseline validation, budget accounting and provenance all pass.

Ten percent quality and five percent time thresholds ask for a material incremental gain before a generic runtime is justified. They, the tail bar and perceptual tolerances are deliberate engineering design choices, not fitted data or scientific safety limits. Controller overhead must be counted; report its fraction and worst-case latency even if the end-to-end gate passes.

Keep comparisons at all four budgets and report conventional winners. A uniform-only win, extra uncharged probes, false targets from reference error, or a variance-guided baseline with deliberately inferior settings cannot pass. FAIL means stop or substantially rethink the generic abstraction before adding domains/mechanisms. An invalid reference/estimator or incomplete execution is **INCONCLUSIVE**, never a policy success or a hidden loss deletion. A pass permits only a new independent domain gate.

## Two freezes and execution checklist

Protocol registration uses tag **`tc-r1-protocol-preregistered`**, recorded hashes in `research/tc-r1/protocol-freeze.json`, and a research issue/PR. It preserves all Generation I inputs/artifacts byte-for-byte. Verify with `python scripts/tc_r1_protocol.py`. No TC-R1 outcome runs are part of this change.

Before execution, a separate commit/tag **`tc-r1-execution-preregistered`** must bind:

- Full scene/frame manifests, all asset hashes/licenses and paired random-stream definitions.
- Renderer/integrator settings, independent correctness tests and implementation revision.
- Exact controller, all conventional policies and ablations; predictor/uncertainty/exploration/tie settings and information boundaries.
- Estimator/stopping proof or limitations, ray counting and overshoot/checkpoint semantics.
- Reference images/hashes/convergence, metric implementations/model hashes and synthetic validation fixtures.
- Hardware/backend/thread configuration, timing cadence/order/warmup/cap and complete executable statistical/censoring analysis.
- A runner that verifies those inputs, retains every outcome/action trace and refuses dirty/changed frozen inputs.

These items are intentionally **not claimed complete** here. Commit any necessary before-outcome amendments with a reason and preserved versions; no relative-performance pilot on the primary corpus, tuning after results, choosing the best temporal variant anonymously, or moving acceptance thresholds after outcomes. Freeze first, execute second, then report PASS/FAIL/INCONCLUSIVE with one evidence-backed next decision. Contacts, TC-S2 and old-scheduler improvements remain outside this gate.
