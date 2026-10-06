# TC-0 results

Run `python scripts/tc0.py` from the repository root. It builds the release CLI, evaluates every `scenarios/*/scenario.toml` with all five policies twice and verifies byte equality before writing JSON reports and a metrics-only `summary.json` to ignored `results/local/`.

Each full report embeds scenario definitions, scheduler, seed 42, source Git commit/dirty status, simulation version `tc0-1`, effective configuration, metrics and all ordered events. `summary.json` is a convenience table; retain the full reports as the provenance source. The seed does not drive randomness in TC-0.

Canonical reports are placed in `results/tc0/` after validation. They identify the clean source commit that produced them, which necessarily precedes the artifact commit. Reproduce that source commit in a clean checkout using `Cargo.lock`; compare events and metrics. Report headers can differ with checkout path or Git metadata. Do not confuse normalized utility with optimal-schedule performance.

See [methodology](../docs/research-methodology.md), [metrics](../docs/metrics.md) and [assumptions](../docs/assumptions.md). Favorable fixtures and intentional failure controls are reported together. These deterministic toy fixtures provide semantic evidence, not statistical proof or mission validation.
