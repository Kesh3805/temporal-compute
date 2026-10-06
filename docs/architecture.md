# Architecture

The workspace separates domain types (`tc-core`), task/scenario representation and validation (`tc-ir`), policy selection (`tc-scheduler`), event encoding (`tc-trace`), event reduction (`tc-metrics`), execution state (`tc-sim`) and user-facing orchestration (`tc-cli`). Each crate has a real dependency boundary; none is a service. Trace encoding knows nothing about files, the simulator knows nothing about Git, and scheduler code cannot mutate task definitions.

The engine holds a private task lifecycle: pending → waiting → running → completed, or pending → waiting → expired. When idle, it jumps to the next arrival or waiting expiration. After dispatch it advances through all intervening arrivals/expirations before completing the running task. It then invokes the scheduler with all waiting tasks and simulated time. Each decision records the chosen ID and every candidate's predicted completion, utility and execution cost. Metrics are reduced from that same ordered stream.

`Scheduler::select_next` returns a task ID. Returning no choice for a nonempty runnable set or choosing a non-runnable ID is a contextual runtime error, not an assertion or silent fallback. The scenario is validated on every simulation entry, including callers constructing public types directly. Checked time arithmetic remains in execution paths even after conservative validation.

FIFO ranks by arrival. Fixed priority ranks by descending priority. EDF ranks by absolute deadline, absent last. `temporal-utility` maximizes `U(task, now + cost)`. `temporal-utility-density` maximizes that value divided by cost, using exact `u128` cross-products rather than floating-point comparisons. Both keep the same deterministic arrival/ID ties. Both start a zero-valued candidate if no positive score is available.

The absolute variant is the primary explicitly named temporal policy; density is always reported alongside it in the full experiment. Absolute utility directly targets the numerator of mission utility but neglects opportunity cost. Density approximates scarce compute efficiency but can delay long valuable urgent work. The choice is documented before results; neither is selected opportunistically as the project's winner.

Current extension points are the scheduler trait, validated utility enum, event schema and scenario version. Future changes to resources, execution semantics, quality, dependencies or contacts require evidence and new ADRs, rather than speculative TC-0 interfaces.
