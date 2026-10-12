# Amendment 0005: execution design (cost, timing, dispatch, retention)

Status, by section, dated 2026-10-12 and before outcomes:

- Section 1 (deterministic cost): **adopted by maintainer decision.**
- Sections 2–4: **proposed**, needing a maintainer decision.

Nothing here authorizes a host, a build, rendering, references or comparative
runs. The original protocol `99ad341`, amendments 0001–0004, the kernel,
baseline and controller contracts, and all evidence remain unchanged. Binding
draft: [execution-design-amendment-0005.json](../../../research/tc-r1/execution-design-amendment-0005.json).

The [next-step brief](../next-step-brief.md) identified four design blockers:

1. a wall-clock cost input dominated by launch overhead;
2. a time estimand that is INCONCLUSIVE by construction;
3. per-request process launches;
4. per-sample logs at terabyte scale.

The [v2 offline gate](../offline-gate-v2-result.md) returned GO and showed the
controller's cost lever invisible under wall-clock cost.

## 1. Deterministic charged-ray cost (adopted)

The controller and its ablations rank by predicted gain per predicted
**charged ray**, the unit of the registered budget. For each region the cost is
its cumulative allocation-stream `charged_rays / sample_count`. It is undefined
before the region's first sample, and initialization never ranks.

- **Why.** Wall time per request is dominated by a fixed per-process launch
  (about 0.3 s against microseconds of per-ray work), so it measures dispatch,
  not transport difficulty. It differs between the three timing repeats, so it
  makes allocations non-reproducible. It also hid per-region ray cost entirely
  in both offline gates: decisions were identical for homogeneous and
  heterogeneous ray fields.
- **Information boundary.** Both fields already exist in every policy's
  `RegionState`. There is no new observation and no production or reference
  access.
- **Implementation.** `experiments/tc-r1/ray_cost.py` (`RayCostTcPolicy`, which
  wraps the amendment-0004 controller) substitutes only the cost field the
  controller reads. The hash-bound kernel still measures and records elapsed
  time for end-to-end accounting. Equal-cost ranking is unchanged and remains
  the cost ablation.
- **Consequence.** All six policies are deterministic given seeds and states.
  The three timing repeats must produce bit-identical images, which becomes a
  required determinism check. Under deterministic heterogeneous ray costs, gate
  v2 measured the cost lever at 0.098, just below that gate's 0.10 threshold. No
  claim that this lever helps is made or tested here.

## 2. Time estimand: common wall cap, fixed ray cadence (proposed)

Current analysis marks the time gate invalid whenever censoring precedes the
common cap. A run ending at the last ray checkpoint is censored at a
policy-specific time, so the registered design is INCONCLUSIVE by construction.

- Each run continues until **both** the final quality checkpoint
  (`A_u + 2^26`, amendment 0003) is committed **and** wall time reaches a common
  cap `C`. Both streams stay charged throughout. Quality uses only the four
  amendment-0003 checkpoints, unchanged.
- Snapshot the production image at every **2^20 charged rays after
  initialization** (a superset of the quality increments). Snapshot write time is
  inside measured wall time for every policy alike.
- Score snapshots **offline** after the run. There is no live metric-based
  stopping, so the protocol's "required live metric evaluation" is empty. A unit
  attains the joint target at the timestamp of the first snapshot meeting it;
  sustained attainment uses later snapshots up to `C`. Nonattainment is censored
  exactly at `C`, which the existing analysis accepts. Medians of three repeats
  are then always identifiable.
- **`C` is fixed before outcomes** from a non-primary throughput calibration on
  the selected host, rule: `C = 2 ×` the projected wall time for uniform to
  reach `A_u + 2^26` on the slowest-calibrated fixture class. Calibration uses
  only non-primary fixtures and uniform allocation.
- **Cost.** Units that finish rays before `C` continue to `C`; that compute is
  real and disclosed.

## 3. Dispatch: persistent native worker and vectorized state (proposed)

Projected cost is dominated by about 2–5×10^7 process launches per pass, plus a
Python per-pixel state loop of about 0.1 s per `observe()` at 256².

- **(a) Persistent PBRT worker per stream.** A request loop reads
  `(region, begin, end)` and reuses the parsed scene, with the same qualified
  instrumentation, sample logs, Film and charged classes. This is a harness
  change, not a transport change. It requires re-running the frozen
  native-validation matrix (estimator, ordering, threads, regions, ray classes,
  paired streams, failure containment) under a new contract before use.
- **(b) Vectorized kernel state.** A NumPy implementation of the kernel's
  sufficient statistics must pass exact-equivalence tests against the
  hash-bound `progressive_kernel.py`, as the offline-gate simulator already does
  for region statistics.
- **Unchanged:** 4-spp requests, 256-pixel regions, actions and checkpoints. No
  speed claim is made until measured.
- **Alternatives** if (a) is rejected: 16-spp requests (amends action
  granularity, about 4× fewer dispatches), or a smaller corpus resolution (a
  protocol amendment). Both change registered semantics; (a) does not.

## 4. Retention: aggregate records, transient logs, audit subset (proposed)

- **Permanent:**
  - one record per dispatch: identity, full and projected seed, region, sample
    range, command, binary and scene hashes, exit status, per-class ray totals,
    sample count, SHA-256 of each transient log, validation verdict;
  - kernel and paired traces, and checkpoint crossings with overshoot;
  - the four checkpoint images per unit, policy and repeat, plus snapshot scores
    and hashes;
  - every failure with its raw logs.
- **Transient:** per-sample, event and Film CSVs after validation, except a
  **seeded audit subset**. One in 1,024 dispatches is chosen by
  `SHA-256(unit|policy|stream|dispatch)` and kept in full. Determinism (section
  1) and the validated order and thread invariance make any dispatch exactly
  regenerable from its record.
- **Streaming validation.** Logs are validated line by line rather than read
  whole into memory. This is required at reference scale.
- **Not dropped:** charged-work, sample-identity, convergence and provenance
  evidence. Only redundant per-sample copies become transient.

## Next step if adopted

One bounded local measurement on this laptop, under a separate resource
authorization:

- **Caps:** one worker, a 3 GiB process-memory cap, 12 GiB of new disk including
  the build, and a 45-minute measured phase within a 2-hour session.
- **Work:** build the pinned PBRT once with one compile job. Re-run the
  native-validation fixtures with the persistent worker. Measure on non-primary
  fixtures only: throughput, dispatch latency, peak RSS and retained bytes per
  sample.
- **No:** primary scenes, references or policy comparison.

Its output replaces the projections in the brief. Full-workload feasibility
stays INCONCLUSIVE until then. Issue #9 stays open.
