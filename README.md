# Temporal Compute

**Compute what matters while it still matters.**

Ostrium Temporal Compute investigates **adaptive progressive computation**: reallocating compute as intermediate results reveal where additional work has the greatest marginal value. The current implemented runtime is the Generation I TC-0 simulator for whole time-valued jobs; Generation II is a separately preregistered research direction, not an implemented adaptive renderer or a demonstrated performance advantage.

## Two generations of research

| Generation | Question | Evidence / status |
| --- | --- | --- |
| I — Inter-task temporal scheduling | Which whole waiting job should execute next? | TC-0 establishes deterministic semantics and exposes wins, ties and losses. TC-S1 rejected the registered greedy-policy advantage: Temporal Utility lost 5.07% to EDF and failed all five gates. This incremental research thesis is retired pending new contrary evidence. |
| II — Adaptive progressive computation | Given the intermediate state, what unit of computation is worth doing next? | TC-R1 — Marginal Compute in Path Tracing registers a new question against uniform and strong adaptive sampling. No rendering results or Generation II implementation exist yet. |

Read the [Generation II research statement](docs/generation-ii.md), [TC-R1 protocol](docs/tc-r1/preregistration.md) and [preserved TC-S1 report](docs/tc-s1/results.md). TC-0 and TC-S1 remain reproducible historical experiments. Contacts, TC-S2 and improvements to the old schedulers are not the next step.

A task can finish correctly and still be worthless: an observation may become stale, a decision window may close, or a result may arrive after its deadline. The existing TC-0 runtime makes that value explicit and measures how ordering whole jobs changes the outcome on one constrained CPU.

| Conventional scheduling asks | Temporal scheduling asks |
| --- | --- |
| What should execute next? | What is still worth computing, and before when? |
| Arrival order, priority, deadline | Expected completion utility, freshness, execution cost |

Consider Task A: runtime 40 seconds, value 100, deadline 60 seconds. Task B: runtime 4 seconds, value 70 now and 5 after 10 seconds. Running A first can destroy most of B's value even when both finish before their deadlines. EDF cannot distinguish that loss if the deadlines are equal. A greedy temporal policy can also make poor choices: the repository includes controls where EDF beats both temporal variants and where density sacrifices a valuable urgent task.

**Temporal Compute is experimental systems research, not flight-qualified spacecraft software.** No claim of optimality, production readiness or general superiority is made.

## Quick start

Install stable Rust with Rustfmt and Clippy. The workspace uses edition 2024 and declares Rust 1.99 as its minimum, matching stable used for validation; `rust-toolchain.toml` selects current stable. On GNU Windows this Rust-only workspace selects Rust's bundled LLD, avoiding a separate GCC linker driver. Python 3 is needed only for the full experiment script, not for the simulator.

```sh
cargo run --release -p tc-cli -- simulate scenarios/tc0-basic/scenario.toml \
  --scheduler temporal-utility --seed 42

cargo run --release -p tc-cli -- compare scenarios/mixed-utility/scenario.toml \
  --schedulers fifo,fixed-priority,edf,temporal-utility --seed 42

cargo run --release -p tc-cli -- compare scenarios/mixed-utility/scenario.toml \
  --format json --output results/mixed.json

cargo run --release -p tc-cli -- simulate scenarios/freshness-decay/scenario.toml \
  --scheduler temporal-utility-density --trace results/run.jsonl
```

`compare` defaults to all five policies, including `temporal-utility-density`. Output paths must have an existing parent directory. JSON reports include the full workload, configuration, seed, source commit, dirty status, metrics and ordered event stream. The seed is recorded but does not change TC-0's deterministic fixed workloads. Unknown scenario fields and invalid task definitions are rejected.

## Reproduce the entire TC-0 experiment

```sh
python scripts/tc0.py
```

This builds the release CLI, runs seven scenarios with all five schedulers twice, verifies byte-identical reports, and writes `results/local/`. Shell and PowerShell entry points are `sh scripts/tc0.sh` and `./scripts/tc0.ps1`. See [results](results/README.md) for canonical artifacts and provenance.

## Architecture

```text
tc-core       checked simulated time, task IDs, priorities, utility points
    ↓
tc-ir         validated TOML scenarios and utility curves
    ↓
tc-scheduler  FIFO, fixed priority, EDF, absolute utility, utility density
tc-trace      versioned JSON Lines event schema
tc-metrics    event-derived research measurements
    ↓
tc-sim        deterministic, single-CPU, non-preemptive discrete events
    ↓
tc-cli        simulation, comparisons, reports and trace files
```

Crates have separate responsibilities, not service boundaries. There is no async runtime, network server, database, task migration or distributed infrastructure. See [architecture](docs/architecture.md), [assumptions](docs/assumptions.md) and [trace schema](docs/trace-schema.md).

## Research status

TC-S1's frozen Earth-observation workload gate **failed**: absolute Temporal Utility earned 524,509 points versus EDF's 552,525 (-5.07%); all five preregistered gates failed. Density also fell short of EDF. The source-grounded corpus uses explicitly assumed numerical values, not mission telemetry. Its direction D decision is preserved; the separate TC-R1 question is the proposed substantial rethink, not a rescue of the old result. See the [full TC-S1 report](docs/tc-s1/results.md), [preregistration](docs/tc-s1/preregistration.md), [evidence dossier](docs/tc-s1/evidence.md) and [reproducible artifacts](results/tc-s1/README.md).

TC-0 tests whether explicit completion-time utility improves mission utility under compute pressure. It compares two fixed, named greedy policies with identical baselines and workload semantics. Fixtures include overload, equal-deadline decay, freshness, a mixed workload, an EDF-favorable control, an equivalent-policy control and a density failure control. These are executable semantic experiments, not a representative mission dataset or a statistical demonstration.

Read the [thesis](docs/thesis.md), [methodology and kill criteria](docs/research-methodology.md), [metric definitions](docs/metrics.md) and [roadmap](docs/roadmap.md). Benchmark outcomes are reported in `results/README.md`; scenarios are not retuned to improve temporal-policy results.

## Collaborating on the research

Use [Discussions](https://github.com/Kesh3805/temporal-compute/discussions) for questions, scheduling ideas, methodology and interpretation. Use [Issues](https://github.com/Kesh3805/temporal-compute/issues/new/choose) for reproducible problems and concrete work; the experiment form captures a hypothesis, baselines and validation plan. Use [Pull Requests](https://github.com/Kesh3805/temporal-compute/pulls) for proposed code, scenario, metric, methodology or documentation changes.

Read [contributing](CONTRIBUTING.md) for validation and research review, and the [collaboration guide](docs/github-collaboration.md) for triage, Discussions and lightweight planning. Report confidential vulnerabilities through [private security reporting](https://github.com/Kesh3805/temporal-compute/security/advisories/new); see [security guidance](SECURITY.md).

## Engineering checks

```sh
cargo fmt --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --all-features
cargo build --workspace --release
python scripts/tc0.py
```

CI runs these checks on Linux and Windows. See [contributing](CONTRIBUTING.md) and [security reporting](SECURITY.md). Licensed under MIT OR Apache-2.0.
