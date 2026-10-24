# TC-R1 next-step decision brief

Status: **independent assessment, 2026-10-12. Recommends; authorizes nothing.**
No build, install, native benchmark, rendering, reference or comparison was run
for it. Evidence: read-only inspection of the merged code and contracts, the
retained native-validation archive and the failed 2026-10-08 laptop admission
record. Every resource figure below is labeled as measured or projected.
Overall resource verdict: **INCONCLUSIVE**.

## A. What we are trying to falsify

Claim: *at equal charged rays, a controller that watches the evolving image and
ranks regions by predicted gain per predicted cost renders measurably better
(at least 10% lower error) and reaches a joint quality target at least 5% sooner
than competent conventional adaptive sampling, after paying its own overhead.*
A win over uniform alone does not count. A failure means stopping or rethinking
the generic abstraction.

| Kind of success | Evidence today |
| --- | --- |
| Implementation correctness | Strong. E3 selected PBRT CPU. PR #22 passed a bounded non-primary matrix: estimator/batch equivalence, paired streams, ray classes ≤17 per sample (max observed 13), checkpoint crossing/overshoot, failure containment. All 30 corpus files parse. |
| Scientific validity of the comparison | Not established. See B. |
| Efficiency of the controller | No evidence of any kind. Zero comparative outcomes. |

Parsing is not runtime construction; correctness is not efficiency; implemented
candidates are not validated comparators.

## B. Coherence and proportionality audit

1. **The controller is close to an existing baseline.** With the kernel's
   definitions, `Q = 3·A·V/n` (`progressive_kernel.py:166-167`,
   `tc_controller.py:134-150`). On the corpus's equal 16×16 regions, the score
   is variance-guided's `V/(n(n+4))` divided by measured seconds per sample,
   with part of the gain replaced by the observed recent SE² decrease and a
   forced exploration step every 16th decision. The 0.25 bonus only reweights
   model against recent (0.75/0.5). The existing test
   `test_tc_controller.py:74` already shows equivalence under equal cost. The
   experiment therefore mainly tests whether **(i)** a noisy wall-clock cost
   estimate and **(ii)** the recent-improvement term help.
2. **The cost input is dominated by process launch and is non-deterministic.**
   Each request starts a new PBRT process (`pbrt_batch_backend.py:103-112`);
   cost is elapsed time per sample of the last request (`progressive_kernel.py:213`).
   It mostly measures launch overhead, not transport difficulty, and makes
   allocations differ across the three timing repeats. No rule says which
   repeat supplies the quality images.
3. **The strong conventional baseline is not yet strong.** MC-UCB's index
   `(sqrt(V)+2β/sqrt(n))/n` with β=1.0 in absolute radiance units
   (`baselines.py:94-97`) is variance-guided plus a scale-dependent bonus: it
   approaches uniform in dim scenes and variance-guided in bright ones. Both
   conventional methods target the same Neyman-style allocation, so the
   "strongest conventional" set is effectively one method.
4. **The time gate cannot currently pass or fail.** `analysis.py:28-60,248-250`
   marks the time gate invalid for any censoring before the common cap or for
   interval-censored repeat medians. Ray-cap exhaustion happens at
   policy-specific wall times, so a run to the last ray checkpoint makes the
   whole result INCONCLUSIVE by construction. Cap, cadence and estimand are
   unresolved.
5. **Checkpoints.** Resolved in principle by amendment 0003 (option D): fixed
   post-initialization increments above a policy-independent actual
   initialization charge. Still needs the runner invariant and selected-host
   validation.
6. **Production scale is dominated by orchestration and logging, not by RAM.**
   - Projected: one quality pass is about 2.2–5.0×10^7 PBRT launches (256-pixel
     regions × 4 spp per stream, ~1.5–3.6×10^7 samples per policy-frame at 2–5
     rays per sample, 1,440 policy-frames). At the ~0.3 s per dispatch measured
     through the bridge on the Actions runner with logging, that is roughly
     **1,800–4,200 single-worker hours per pass**, times three timing repeats.
   - Measured: retained logs cost about 148 + 17·r bytes per camera sample
     uncompressed (2.6× gzip). Projected: **4.5–13.5 TB per pass**; first-level
     references 5.9–7.5 TB, up to 7× with escalation.
   - No aggregate-only production path exists; `load_batch` reads whole logs
     into memory, so it cannot handle reference-scale batches.
   - Kernel ray throughput alone is small by comparison: roughly 27–42
     thread-hours per pass, projected from 2-thread synthetic runner figures.
   - Sources. Dispatch latency: `paired/uniform/paired-trace.json` inside
     `research/tc-r1/native-validation/raw-artifacts.tar.gz` (archive SHA-256
     `03f586c1…`, Actions run 37756401842): 10 paired steps, 20 launches,
     6.02 s. Bytes per sample: that archive's `*.samples.csv`, `*.film.csv` and
     `*.events.csv` sizes divided by 236,672 validated samples and 470,577
     charged rays. Kernel throughput: `research/tc-r1/qualification/pbrt-probe.json`.
     Projection inputs: 256² pixels, 2 streams, 16-spp initialization,
     increments up to 2^26 rays, 2–5 rays per sample, 1,440 policy-frames,
     1,024 samples per dispatch.
7. **Memory.** The 8 GiB figure was an attempt-specific admission rule, not a
   requirement derived from evidence. Corpus scenes are 4–15 KB of procedural
   spheres and small meshes. Projected (unmeasured) peak: about 0.2–0.5 GB per
   worker for PBRT plus Python. A single worker plausibly fits in the 4–6 GiB
   this laptop had available. The real limits are dispatch time and log volume.

Conclusion: no host purchase, larger machine or renderer change addresses
items 1–4. Item 6 is an architecture issue that a bigger host only divides
by its core count. Spending on a host now would buy precise timing of an
experiment whose comparator, cost input and time estimand are not yet coherent.

## C. Options considered

| Option | Verdict |
| --- | --- |
| Lower-memory local feasibility test (one worker, ≤3 GiB cap) | Probably admissible, but it would measure an orchestration design that needs to change first. Do after the design is fixed. |
| Alternative CPU host | Divides items 6 by cores; fixes none of 1–4. Premature. |
| Hosted diagnostic benchmark | Measures a runner; same objection, plus cost. |
| Explicit pre-outcome amendment of design | Needed, but should be informed by a cheap offline check first. |
| Pause or stop path tracing | Justified if the offline check shows the controller differs from variance-guided only through a lever the corpus barely exercises. |

## D. Recommended next action: offline identifiability and competence gate

**One bounded, PBRT-free, laptop-only gate with frozen criteria and a go/stop
decision.** It needs no new resource authorization beyond the maintainer
approving its frozen contract: pure Python/NumPy (present), under 1 GiB RAM,
under one CPU-hour, no build, install, render, primary scene or reference.

Commit a contract before running anything, then execute it once:

Protocol basis: the preregistration permits synthetic tests before the
execution freeze, and the [integration gate](integration-gate.md) and Track B
require independent scale, rare-event and applicability validation of the
conventional methods **without TC results**. This gate stays inside that
permission. It computes no controller image quality, no primary-scene or
reference result, and no TC-versus-baseline outcome.

1. **Comparator competence (baselines only, no TC).** Synthetic 256-region
   fields with known per-region variance from Gaussian, lognormal and rare
   Bernoulli-spike distributions, across radiance scales 1e-3 to 1e3. Run the
   unchanged `baselines.py` policies through the existing `ProgressiveKernel`
   with a numeric backend. Compare total MSE at matched samples against uniform
   and against oracle Neyman allocation using the true σ. Freeze thresholds
   first (for example within X% of oracle at every scale; no worse than uniform
   by more than Y% on rare-event fields).
2. **Identifiability (decision agreement only, no quality).** On the same
   fields, plus fields with heterogeneous per-region rays per sample, record the
   fraction of decisions where the controller, its two ablations and
   variance-guided choose different regions, under (a) a **synthetic**
   wall-clock cost model (fixed launch overhead plus per-ray time with timing
   noise) and (b) a deterministic charged-rays-per-sample cost. Condition (a)
   models the launch-dominated shape of the current PBRT cost; it does not
   replay PBRT cost observations and cannot by itself establish production-cost
   identifiability. No image-quality comparison involving the controller is
   computed or retained.

What it resolves: whether the strong baseline is defensible or needs a frozen
β normalization; whether the controller is a materially distinct method, and
through which lever; whether the cost predictor must become deterministic.

Reused: `baselines.py`, `tc_controller.py`, `progressive_kernel.py`,
`paired_policy_runner.py` with numeric backends; all existing tests and evidence.

Missing evidence it does not supply: corpus rays per sample, real dispatch
latency on any chosen host, reference convergence, stopping/bias argument.

Acceptance and stop:
- **Go:** baselines meet the frozen competence criteria (or a β normalization
  is registered pre-outcome), and the controller's decisions differ materially
  through a lever the corpus can plausibly exercise. Then register one design
  amendment (deterministic cost predictor, β rule, common wall cap with fixed
  ray snapshot cadence, aggregate-only dispatch records with hashed transient
  logs and an audit subset, larger or persistent PBRT batches), and only then
  run the bounded one-worker local measurement.
- **Stop or rethink path tracing:** the controller collapses to variance-guided
  except for a noisy or negligible cost term. Record it as a design-level
  finding, not as a FAIL of the hypothesis, and return to a maintainer domain
  decision.
- Either way: no parameter of any policy changes in response to this gate's
  numbers except through a separately registered amendment justified
  independently of them.

Why it moves toward falsification: it removes the two ways the real
experiment could produce an indefensible result (a weak comparator, or a
controller indistinguishable from it) for under an hour of laptop CPU,
before committing thousands of worker-hours.

## E. Status line

PBRT CPU selected; native correctness PASS on a bounded matrix; checkpoint
design adopted as amendment 0003 (host validation pending); comparator
competence, controller identifiability, time estimand, production
architecture and host all unresolved. Full-workload feasibility:
**INCONCLUSIVE**. No references, execution freeze or comparative outcomes.
Issue #9 stays open.
