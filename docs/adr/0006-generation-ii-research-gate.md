# ADR 0006: Separate progressive-compute research from Generation I

Status: accepted research direction; implementation unproven.

TC-S1's fixed-policy claim failed against competent conventional scheduling. Preserve its frozen inputs and complete results, merge PR #7 unchanged, and retire the incremental thesis pending contrary evidence. Do not retune workloads, improve the old scheduler to rescue the result, start TC-S2 or add contacts as the response.

Generation II studies feedback within computation: observe state, estimate marginal gain/cost/uncertainty, choose bounded work, observe again. This overlaps established adaptive computation/metareasoning; novelty and benefit must be demonstrated rather than asserted. Keep `TemporalTask`, the existing seven crates, TC-0 and TC-S1 unchanged.

TC-R1 — Marginal Compute in Path Tracing is the separate first gate. Preregister its question/acceptance rules now; require a concrete executable corpus/algorithm/reference/hardware freeze before measurements. Compare against strong adaptive rendering, include losing/equivalence scenes, preserve estimator correctness, charge all work and controller overhead, and stop/rethink if domain-specific adaptivity erases meaningful benefit.

Consequences: no new runtime API, renderer dependency, GPU service, contact model, domain integration or benchmark result is added by this decision. CPU/GPU backend and fully hashed implementation/assets are remaining pre-execution work, not evidence already obtained. A positive rendering result alone cannot establish cross-domain portability.
