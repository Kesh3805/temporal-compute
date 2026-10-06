# Metrics

Metrics include only terminal task outcomes and are derived from simulation events. For a valid completed run, `tasks_completed + tasks_expired = tasks_total`. A completed task may have zero utility. Expiration means no execution occurred; missed/stale running work is completed, not expired.

| Field | Definition |
| --- | --- |
| tasks_total | Number of task definitions. |
| tasks_completed | Number of completion events, including zero-valued results. |
| tasks_expired | Number of waiting-expiration events. |
| deadline_tasks_total | Number of tasks with a deadline, including expired tasks. |
| deadline_hits | Completed tasks whose completion is at or before their deadline. Freshness failure does not change technical deadline compliance. |
| deadline_hit_rate | Deadline hits / all deadline-bearing tasks. Expired tasks count as misses. `null` when there are no deadlines. |
| total_utility | Sum of integer utility recorded at completion. |
| maximum_task_utility_sum | Sum of declared base utility, including work which cannot fit before its limits. |
| normalized_utility | Total utility / base-utility sum. `null` when denominator is zero. |
| compute_time_used_us | Sum of execution cost of completed tasks. |
| compute_time_wasted_us | Full execution cost of completed tasks yielding exactly zero utility. Partially useful results are not counted as wasted. |
| average_completion_latency_us | Mean of completion minus arrival over completed tasks, including zero utility; `null` if none. |
| average_result_age_us | Mean of completion minus input time over completed tasks; input defaults to arrival; `null` if none. |
| simulation_end_us | Timestamp of simulation-completed event, including idle intervals. |

Normalized utility is a workload-relative fraction, not competitive ratio to an optimal feasible schedule. The denominator ignores contention and decay during even the fastest execution. Thus 1.0 may be infeasible; values should primarily be compared on identical workloads. Higher deadline hit rate need not imply higher mission utility, and wasted compute ignores degrees of diminished usefulness. Integer utility and these simplifying metric choices must be reported when comparing later implementations.

Ratios and means are display-only `f64`; raw integer counters are the scientific source. Sums detect overflow. The reducer expects the engine's complete authoritative trace; it is not a validator for arbitrary externally edited event streams.
