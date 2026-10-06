# Terminology

| Term | TC-0 definition |
| --- | --- |
| Temporal task | Immutable arrival, execution-cost, deadline, priority, freshness and utility definition identified by a unique string ID. |
| Simulation time | Monotonic integer microseconds since simulated epoch zero; unrelated to elapsed host time. |
| Execution cost | Known, positive CPU duration required to complete a task once. |
| Deadline | Latest technically acceptable completion time, inclusive; absent means no deadline. |
| Freshness | Latest completion time at which input retains decision value, inclusive; independent of deadline. |
| Temporal utility | Nonnegative integer points yielded by completion at a given time. Deadline or freshness violations force zero. |
| Mission utility | Sum of actual completion utility; independent tasks have additive value. |
| Normalized utility | Actual mission utility divided by sum of declared base utility; undefined when that sum is zero. |
| Scheduler | Policy selecting one waiting task from the same immutable task set and current time. |
| Scenario | Versioned, validated TOML workload; contains no scheduler-dependent behavior. |
| Expired task | Waiting task retired after its deadline or freshness limit. A late running task completes, with zero utility, rather than becoming expired. |
| Result age | Completion time minus input observation time, defaulting to task arrival. |
| Utility density | Predicted next-completion utility divided by known execution cost. |
