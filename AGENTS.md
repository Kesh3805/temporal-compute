# Engineering invariants

Use CodeGraph before searching code only when `.codegraph/` exists. Do not initialize an index implicitly.
Use Context7 for dependency API documentation. Keep TC-0 deterministic, single-CPU and non-preemptive.
Validate format, strict Clippy, workspace tests, release build and canonical scenarios before publishing changes.
Never tune scenarios after observing results solely to favor a scheduler. Document semantic changes and regenerate all results together.
