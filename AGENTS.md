# Engineering invariants

Use CodeGraph before searching code only when `.codegraph/` exists. Do not initialize an index implicitly.
Use Context7 for dependency API documentation. Keep TC-0 deterministic, single-CPU and non-preemptive.
Validate format, strict Clippy, workspace tests, release build and canonical scenarios before publishing changes.
Never tune scenarios after observing results solely to favor a scheduler. Document semantic changes and regenerate all results together.

# Active research gate

Generation I's incremental-policy thesis is retired pending contrary evidence. Preserve TC-0/TC-S1 code, frozen inputs and complete results; do not start TC-S2, add contacts or tune the old schedulers to rescue TC-S1.
Generation II studies adaptive progressive computation. TC-R1 is a protocol registration, not an implemented renderer or an executable-corpus freeze. Read `docs/tc-r1/preregistration.md` before related work. No comparative TC-R1 outcomes until assets, algorithms, baselines, references, metrics, analysis and hardware are bound by the separate execution preregistration. No post-outcome tuning.
