# ADR-0002: Deterministic discrete events

Status: accepted.

Advance directly between arrivals, waiting expiration and task completion. Retain a fully ordered event stream and derive metrics from it. This avoids wall-clock and time-step drift, makes replay observable, and preserves arrivals during execution. TC-0 scans task state rather than maintaining an optimized heap: simpler invariants at small scale, quadratic overhead that should be profiled before scaling.
