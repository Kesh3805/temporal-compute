# Research methodology and falsification

## Question and provisional hypothesis

Can a scheduler explicitly modeling completion-time utility outperform FIFO, fixed priority and EDF on mission utility under constrained compute? The provisional hypothesis is that temporal scheduling produces higher normalized utility under overloaded workloads with changing utility. It is deliberately stronger than TC-0's evidence can currently support; a single win does not validate it universally.

## Experimental design

Independent variables are policy and fixed workload (arrival, duration, deadline, priority, curve and freshness). The seed is held at 42 as provenance; it is not an independent behavioral variable in TC-0. CPU capacity, dispatch overhead, non-preemption and expiration semantics are identical. Primary dependent variable is total/normalized utility; secondary variables are deadline compliance, completions, expirations, used/wasted compute, latency and age.

Compare FIFO, fixed priority, EDF, absolute next-completion utility and utility density. Report every policy on every fixture. Do not hide the losing temporal variant or choose whichever wins as an unnamed temporal algorithm. No schedulers modify task data, and all run independently from the same initial state.

The seven fixed fixtures are specified in `scripts/create_scenarios.py` and checked into `scenarios/`. The mixed fixture uses a public arithmetic recipe, not scheduler-specific generation. Four primary experiments cover overload, equal-deadline decay, freshness and mixed utility. Three controls expose EDF's advantage, policy equivalence and a density trap. Controls are designed to expose algorithmic failure, and are not representative frequency estimates.

## Measurement and reproducibility

`python scripts/tc0.py` executes 35 runs twice and checks byte equality before saving reports. Tests independently assert monotonic time, unique execution, arrival eligibility, consumed duration, completion utility, reconciliation and stable ties. Unit tests cover curve and time boundaries; a finite-domain property test checks utility bounds and monotonicity. No ceremonial property-testing dependency is needed.

Every JSON report records full scenario definitions, scenario path, policy, seed, source Git commit and dirty flag, simulator version and effective configuration. Integer arithmetic controls all scheduling decisions. Reproduce source commit with a clean checkout and `Cargo.lock`; then use the same commands. Git metadata changes after committing artifact files, so compare event streams/metrics rather than report headers across different commits. If Git is unavailable, provenance fields are `null`, never fabricated.

## Kill criteria

The universal interpretation of the provisional hypothesis is falsified by any valid losing case; TC-0 includes such controls. A narrower research program remains worthwhile only if gains survive independently designed, representative overloaded workloads after both greedy variants and all baselines are reported.

Before claiming mission relevance, freeze an independent workload corpus and utility definitions before execution, predeclare the primary policy and aggregate comparison, then evaluate against all three baselines and report the full distribution including losses. Stop expanding the runtime if gains disappear outside favorable toy cases, require implausibly accurate utility/runtime predictions, or are dominated by simpler baseline improvements. TC-0 has no representative corpus or threshold for such claims yet; do not infer statistical significance from deterministic repeats.

## Threats to validity

Fixtures are small and handcrafted, including intentional favorable and unfavorable cases. Equal simulated time is not equal real hardware overhead. Additive known utility ignores dependencies, quality and interactions. Known cost excludes prediction error. Hard expiration favors systems that know value lifetimes accurately. Non-preemption and work-conserving zero-value fallback can dominate results. Integer quantization changes small rewards. Static priorities may poorly encode mission intent. Repetition checks determinism but supplies no independent samples or confidence intervals. Finite fixtures cannot establish fairness under sustained arrivals. No benchmark should be retuned after observing outcomes to make a temporal algorithm win.
