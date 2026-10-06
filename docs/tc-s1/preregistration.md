# TC-S1 preregistration — before outcome measurement

## Question, hypothesis and research boundary

Do unchanged greedy temporal policies yield more useful completed EO products than competent conventional schedulers under a policy-independent, externally motivated fictional onboard workload?

The primary hypothesis is exactly:

> Across the frozen 200-instance Earth-observation corpus, Temporal Utility will achieve at least 5% more total realized mission utility than the strongest preregistered conventional baseline, with positive paired gains across multiple mission mixes and load regimes, without a material reduction in critical-task success.

This is a test of this model and these algorithms. External sources support EO application classes, not the quantitative utility model. The corpus is independent of scheduling policy, not an independently observed mission dataset. No flight, incident-response or general EO frequency inference is justified. See [evidence](evidence.md), [mission model](mission-model.md) and [value model](value-model.md). No contact/delivery mechanics, quality modes, ML runtime or runtime/policy redesign is allowed.

## Frozen design and parameters

The executable specification is `research/tc-s1/preregistration.json`; every numerical product parameter, arrival process, priority and experimental threshold is D, and all control parameters are E. Class existence is A; limited-resource/time-value motivation is B; the dossier identifies contextual measurements that are deliberately not transferred. The value-model table gives inclusive class bounds, purpose, provenance, rationale and sensitivity concerns.

The 200 primary instances cross five mixes, four load regimes and ten separately seeded replicates per cell, each with 48 tasks (9,600 primary task instances). Mix categorical weights, in class order cloud/fire/vessel/marine/compression/map, are routine `20/5/15/10/35/15`, emergency `10/35/5/5/10/35`, cloud `55/5/10/5/20/5`, maritime `10/5/40/30/10/5`, mixed `20/15/15/15/20/15`. Nominal loads are 0.35, 0.80, 1.25 and 2.00. These are balanced experimental factors, not estimated mission prevalence. The corpus size provides ten draws in each of 20 explicit cells without pretending thousands of runs are independent samples. Oracle and sensitivity instances are separate derived experiments, not additional primary samples.

Generate in manifest insertion order: mission mix, load, replicate 0..9. IDs are `eo-0001` through `eo-0200`. The full seed set and SHA-256 of every generated representation are recorded in `corpus-manifest.json`; no seed rejection or outcome-based selection occurs.

## Generator and exact reproduction

Master seed is 20261006. Instance seed is the first eight bytes, big-endian unsigned, of SHA-256 over ASCII `tc-s1-v1|master|kind|mix|load|replicate`. Primary kind is `primary`; oracle kind is `oracle`; control kind is `control` with its name as mix, `none` as load and replicate zero. Generator version is `tc-s1-v1`.

SplitMix64 uses state increment `0x9E3779B97F4A7C15`, xor-right-30/multiply `0xBF58476D1CE4E5B9`, xor-right-27/multiply `0x94D049BB133111EB`, xor-right-31, masking to 64 bits after additions/products. Each primary task consumes exactly ten raw words, regardless of class: class, cost, base, deadline age, freshness age, exponential interval, retention, step age 1, step age 2, arrival. Unused words are discarded. Inclusive integer range `[a,b]` maps word `x` to `a + floor(x*(b-a+1)/2^64)`. Categorical weights use the same multiply-high mapping followed by cumulative subtraction. These maps are nearly uniform; each bucket's probability differs from uniform by at most 1/2^64. This tiny bounded discretization is explicit, not platform randomness.

Draw class/cost/value/age/curve parameters first; set acquisition horizon seconds to `ceil(sum(base execution cost seconds)/nominal_load)` and map arrival words uniformly to integer seconds 0..horizon-1. Input time equals arrival; deadline and freshness ages are added to arrival. Jobs remain immutable. Base utility and cost use independent latent words; importance is not made systematically cheap. Parameter bounds ensure every primary job is initially feasible under its own hard limits. All policies use the exact same workload.

Canonical scenario bytes are ASCII JSON (`ensure_ascii=True`, keys sorted, compact separators) followed by LF; SHA-256 hashes those bytes. JSON is the existing `Scenario` serialization, not a new runtime model or DSL. `python scripts/tc_s1_generate.py --export results/local/tc-s1-scenarios` recreates complete definitions; the compact config, recipe and all hashes are checked in instead of thousands of scenario files. Static descriptors and schema/hash tests do not run any policy.

## Policies and competent controls

Primary: `temporal-utility` (absolute next-completion utility). Mandatory secondary: `temporal-utility-density`. Baselines: unchanged FIFO, fixed priority and EDF, plus one evaluation-only `edf-priority` control. The additional control ranks by deadline (absent last), descending static mission priority, arrival, then ID. It cannot inspect utility or change the original policies. Discrete-second dates make deadline ties plausible. Static priorities coherently rank emergency output above routine work, without encoding decay. Baseline runtime and all five policy sources must remain byte-identical in Git to TC-0 commit `9166a6630db64b17dda84552c14fa752cbdc72ac`.

All dispatch/execution/expiration rules remain TC-0's. In particular, every policy is work-conserving and may execute work predicting zero value; only waiting work expires. A correct implementation does not become an admission-control experiment. Exceptions for correctness defects require documented errata and a revision, not silent retuning.

## Outcomes and aggregation

Primary outcome: sum of actual integer utility across all 200 primary instances. The strongest conventional baseline is the one with highest corpus total among the four fixed baselines, ties in manifest order. Compare the named primary policy with **each** baseline; selecting the comparator by a preregistered rule is not selecting the winning temporal heuristic. Corpus normalization is sum(actual)/sum(base), never oracle capture. Sum numerators and denominators before division.

For each policy report per-instance utility mean, median, P10/P25/P50/P75/P90, corpus total/base normalization, paired wins/ties/losses versus the primary, deadline hits over all deadline tasks, compute used/wasted, zero-utility completions, expired-unstarted counts and maximum waiting time. Report paired raw and base-normalized deltas, means/medians/quantiles and aggregate relative effect. Quantiles linearly interpolate at `(n-1)*p`; integer utility ties are exact. Results are stratified by all four load regimes, all five mixes and six classes. Average latency and result age are completion-weighted across scenarios, including zero-utility completions; missing denominators produce null, never invented zero.

For each class, report total/base/retained/lost utility, task count, completion rate, unstarted expiration and zero-utility completion. For both critical classes separately, and their union, success is completion with `2*actual >= base` (base is positive). Report success rate and retained-utility fraction separately. Finite-workload starvation is named **expired-unstarted**, not a proof of starvation under an infinite stream. Maximum waiting includes expired tasks' wait to their expiration event and completed tasks' wait to start.

## Paired statistical analysis

Use 10,000 deterministic paired, stratified bootstrap resamples. Analysis seed 734921 initializes SplitMix64; bounded sampling uses rejection to avoid modulo bias. Each resample draws ten indices with replacement within each of the 20 fixed cells. The same sampled indices apply to all policy comparisons. Percentile 2.5/97.5 intervals describe mean raw paired utility delta. Report normalized paired effect and aggregate gain as effect sizes as well. No p-values, significance-star narrative or real-mission population inference. Intervals are pointwise, not simultaneous familywise coverage; the research gate requires all four lower limits positive but does not claim a joint 95% confidence statement. Seeds are reproducibility devices, not proof of statistical independence. Inference is conditional on this chosen generator and its fixed factor grid.

## Sensitivity, frozen before outcomes

Run all 200 seeds under each of twelve one-factor perturbations: ±20% execution costs, age budgets, emergency base value, arrival intensity, cloud class weight and emergency class weights. No combinations or data-selected sweeps are allowed in the primary report. Cost scales durations on fixed arrivals. Age scales relative deadlines/freshness and exponential/step clocks; linear endpoints are coupled to deadline, so this also changes feasibility. Emergency value scales fire/map base (and any step utility). Intensity scales arrival times and horizon by inverse factor while preserving relative age budgets. Cloud/event weights multiply the indicated categorical weights before renormalization and regeneration from the same latent words; the acquisition horizon then follows the regenerated base cost to preserve nominal load. They are weight changes, not literal ±20% probability changes. Integer scaling floors microseconds/points; all are positive. Sensitivities share seeds, are not independent replication, and never enter primary totals.

## Negative and adversarial controls

Seven E-valued recipes are fully frozen in the hashed generator. Constant-value has 24 jobs, costs `1+i%7`, values `10+i%11`, no hard limits: all policies should earn the same total. Underload-equivalence uses the same jobs at `20*i` seconds with deadlines `arrival+15`, so each job completes before the next arrives. These controls test measurement semantics rather than support a superiority claim.

Long-urgent uses `(cost,value,deadline)=(8,100,8)` and `(2,30,12)`. Density-starvation uses a map `(20,100,30)` and twenty compression jobs `(1,10,100)`. Absolute-starvation uses a critical fire `(1,70,10)` and eight maps `(10,100,100)`. Deadline-dominant uses compression `(6,100,20)` and fire `(4,60,4)`. Priority-dominant uses compression `(4,80,20)` and fire `(4,100,6)`. All arrive at zero; priorities use the same class mapping. These expose long urgent work, both greedy starvation mechanisms and competent conventional policies. They are not mission-frequency claims, do not enter primary totals, and their intentional losses do not automatically fail the mission-corpus gate. Unexpected negative-control disagreement invalidates the measurement until explained.

## Exact offline oracle plan

Full 48-job exact optimization is not tractable as a reliable developer-machine corpus requirement: 2^48 subsets before time/value frontiers. Use forty prespecified reduced instances, replicates 0 and 1 in every mix/load cell. Seeded Fisher–Yates shuffling selects nine indices without replacement, then indices are sorted. Scale their arrivals by new/old acquisition horizon, where the new horizon preserves the nominal offered-load ratio using subset demand. Preserve costs, values, priorities, curves and relative deadline/freshness ages. Thus these are **derived reduced problems**, not optimal references for the original 48-job instances.

Use exact subset dynamic programming with Pareto frontiers of `(finish_time, utility, schedule)`; smaller/equal time and greater/equal utility dominates. For each remaining task, start at `max(current_finish, arrival)` and evaluate earliest completion; zero-valued execution is omitted. Allow skipping and intentional idle until a release. For nonincreasing utilities, earliest completion for a fixed sequence dominates delaying it, and a dominated prefix cannot improve a common suffix. This proves exactness for the modeled reduced problem. Record the schedule certificate and utility; cross-check it and exhaustive enumeration on small test cases. No node/time cap or approximate result may be called optimal. Report regret = oracle-policy, normalized regret and capture = policy/oracle; zero oracle yields null ratios. Neither oracle nor schedule certificate is a runtime policy.

## Quantitative falsification gate

PASS requires every condition below; any failure is a failure of the **preregistered primary policy claim**, not automatic falsification of time-dependent value:

1. Primary corpus total exceeds the best of four conventional totals by at least 5%; all four bootstrap lower limits for mean paired delta are positive.
2. Median per-scenario base-normalized primary-minus-strongest-global-baseline delta is at least 0.005.
3. At least two of moderate/overloaded/severe load groups, and at least three of five mission mixes, show >=2% total gain over their strongest conventional baseline.
4. Every one of twelve sensitivity runs has nonnegative aggregate gain; at least ten retain >=2% gain. Losses are never dropped.
5. Pooled critical success rate, and each critical class separately, are no more than 2 percentage points below the best conventional rate. In at least 90% of instances containing the relevant critical jobs, primary success is no more than 10 points below that instance's best conventional rate. Apply the tail test to the union and both classes; absent-class instances are excluded, not scored as zero.

Thresholds are engineering research bars, not mission safety limits or externally measured tolerances. Five percent asks for a material output gain before further complexity while being lower than the ±20% assumed-parameter perturbations. Half a percentage point median normalized output prevents a tiny set of high-value cases from carrying an otherwise negligible benefit. Breadth requirements demand more than one favorable cell. Two-percent sensitivity gains distinguish surviving useful effect from mere numerical positivity. Critical tolerances are stricter because average routine reward must not hide alert degradation; 10-point tail tolerance acknowledges small job counts without excusing frequent critical losses. These choices are contestable and explicitly frozen, not fitted from results. The stronger EDF-priority control is included in all strongest-baseline calculations; its gap-closing effect is reported rather than ignored.

Report PASS only if all gates pass and controls/replay/oracle validation remain sound. Otherwise report FAIL for the primary hypothesis; a PARTIAL overall research interpretation may identify robust abstraction evidence or limited regimes, but cannot relabel a failed primary gate as passing. Select exactly one next direction: contact-bounded work only on a full pass; stronger-policy research if useful temporal information remains but the primary loses/regrets critical work; value-model revision if sensitivity drives the conclusion; rethink if competent conventional policies erase meaningful benefit throughout. Document the data behind that choice.

## Freeze and execution procedure

Phase A performs generation, hashes, bounds, static descriptors, actual Rust `Scenario` validation and synthetic unit tests only. It never evaluates a TC-S1 policy, including the oracle. Before the freeze: fmt, strict Clippy, workspace tests and release build, generator/manifest tests and validation of every primary/derived/control definition. TC-0 regression tests are allowed and must remain unchanged.

An explicit commit `research(tc-s1): preregister earth-observation corpus and falsification protocol`, tagged `tc-s1-preregistered`, is the freeze point. The file `research/tc-s1/freeze.json` binds the specification, corpus manifest, generator, analysis implementation and runtime/policy sources with normalized-LF SHA-256 hashes. The runner verifies those against the exact tagged revision and current content before execution, and refuses dirty or modified frozen inputs.

Only after that commit: build the release batch adapter; evaluate all six policies with paired replay on all primary and sensitivity instances, controls and reduced oracle instances; retain canonical per-run/class/critical metrics and full-stream hashes, representative traces, provenance, paired/bootstrap output, all sensitivities and oracle certificates. Full raw reports may be compressed under ignored local output and regenerated on demand. Static figures use honest axes, identical scales and no web UI. The final report names the freeze SHA and any errata, distinguishes abstraction from algorithms, includes every loss, and updates issue #2 after freeze and final analysis. No post-freeze changes to seeds, workloads, values, policies, primary outcome, gates or analysis methods are permitted because of outcomes.
