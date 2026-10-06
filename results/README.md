# TC-0 results

Run `python scripts/tc0.py` from the repository root. It builds the release CLI, evaluates every `scenarios/*/scenario.toml` with all five policies twice and verifies byte equality before writing JSON reports and a metrics-only `summary.json` to ignored `results/local/`.

Each full report embeds scenario definitions, scheduler, seed 42, source Git commit/dirty status captured at CLI build time, compiler version, simulation version `tc0-1`, effective configuration, metrics and all ordered events. `summary.json` is a convenience table; retain the full reports as the provenance source. The seed does not drive randomness in TC-0.

Canonical reports are placed in `results/tc0/` after validation. They identify the clean source commit that produced them, which necessarily precedes the artifact commit. Reproduce that source commit in a clean checkout using `Cargo.lock`; compare events and metrics. Report headers can differ with checkout path or Git metadata. Do not confuse normalized utility with optimal-schedule performance.

See [methodology](../docs/research-methodology.md), [metrics](../docs/metrics.md) and [assumptions](../docs/assumptions.md). Favorable fixtures and intentional failure controls are reported together. These deterministic toy fixtures provide semantic evidence, not statistical proof or mission validation.

## Canonical TC-0 measurement

Source commit: `5bfe1df` (full revision is recorded in every report), clean build with Rust 1.99.0, seed 42, simulation `tc0-1`. All 35 scenario/policy combinations were executed twice with byte-identical reports. The unchanged fixture recipes were committed before measurements.

Total utility points:

| Scenario | FIFO | Fixed priority | EDF | Temporal utility | Utility density |
| --- | ---: | ---: | ---: | ---: | ---: |
| tc0-basic | 45 | 45 | 155 | 155 | 155 |
| deadline-pressure | 100 | 100 | **160** | 100 | 100 |
| temporal-decay | 126 | 126 | 126 | 166 | **260** |
| freshness-decay | 30 | 30 | 30 | **210** | **210** |
| mixed-utility | 1,145 | 1,181 | 353 | 2,910 | **4,370** |
| fifo-equivalent | 60 | 60 | 60 | 60 | 60 |
| density-trap | **130** | **130** | **130** | **130** | 30 |

On mixed utility, normalized utility is respectively 0.0968, 0.0998, 0.0298, 0.2459 and 0.3693. Wasted compute is 22, 15, 31, 7 and 7 simulated seconds. These results support further testing of explicit temporal value but refute a claim that the greedy policies always improve on EDF. The density trap loses 100 utility points and wastes eight seconds because choosing a short task first makes the long task late. Equal-policy and EDF-favorable controls remain in the canonical corpus.

Local validation passed: format, strict all-target Clippy, 16 tests, release workspace build, all canonical scenario executions and byte replay. GitHub Actions independently runs validation on Linux and Windows; its status is available on the repository, separately from local validation.
