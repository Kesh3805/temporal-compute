# Contributing

Start with a reproducible issue or a falsifiable experiment. Keep TC-0 small, single-CPU and deterministic. Explain semantic changes and record decisions before broadening scope. Do not add future-phase infrastructure without evidence.

Run format, strict workspace Clippy, workspace tests, release build and `python scripts/tc0.py` before proposing changes. New utility behavior needs boundary coverage. Engine changes need event accounting and replay coverage. Workload changes need a rationale independent of observed scheduler outcomes. Compare all five policies and report losses.

Commit `Cargo.lock`. Keep local generated files under ignored `results/local/`; commit only small canonical research artifacts with source provenance. Use concise problem/behavior-focused commit messages. Contributions are accepted under MIT OR Apache-2.0.
