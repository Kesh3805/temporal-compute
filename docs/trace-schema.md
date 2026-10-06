# Trace schema v1

Each JSON Lines row has `schema_version=1`, a contiguous zero-based `sequence`, integer `sim_time_us`, `scheduler`, and an `event` discriminator. Equal timestamps are ordered by sequence, not by event name. JSON comparison reports embed the same rows under each run's `events`.

| Event | Additional fields |
| --- | --- |
| simulation_started | scenario, seed |
| task_arrived | task_id |
| scheduler_decision | selected, candidates |
| task_started | task_id, predicted_completion_us, predicted_utility |
| task_completed | task_id, utility, deadline_met (`true`, `false`, `null`), fresh, execution_cost_us, completion_latency_us, result_age_us |
| task_expired | task_id, reason (`deadline` or `freshness`) |
| simulation_completed | none |

A decision candidate contains `task_id`, `predicted_completion_us`, `predicted_utility`, `execution_cost_us`. Candidates are ordered by ID; scores can be reconstructed for both temporal variants. Equal deadline/freshness expiry limits use reason `deadline`. A late running task emits completion, with zero utility, rather than expiry.

Replay currently means rerunning the recorded full scenario, policy, seed, configuration and simulator version and comparing the ordered events and metrics. TC-0 does not execute a trace as a command stream. Scenario schema, trace schema, report schema and simulation semantics are separately versioned. Semantic changes require incrementing the simulation version, while incompatible field changes require the relevant schema version to change.
