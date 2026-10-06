# ADR-0004: Non-preemptive execution and inclusive limits

Status: accepted.

Use one CPU and execute tasks to completion without preemption. Only waiting tasks expire; running tasks may finish with zero utility. Inclusive deadline/freshness limits mean expiration occurs one microsecond after the limit. The same rule applies to every scheduler, making stale wasted compute visible. Optimistic feasibility filtering, cancellation and checkpoint costs are deferred because they would alter the experiment.
