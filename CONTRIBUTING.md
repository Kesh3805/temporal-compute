# Contributing

Start with a reproducible problem or a falsifiable experiment. Keep TC-0 small, single-CPU and deterministic. Explain semantic changes and record decisions before broadening scope. Do not add future-phase infrastructure without evidence.

## Choose the right conversation

- [Discussions](https://github.com/Kesh3805/temporal-compute/discussions): questions, research ideas, methodology, result interpretation and early architecture proposals.
- [Issues](https://github.com/Kesh3805/temporal-compute/issues/new/choose): bugs, reproducibility failures, documentation tasks, concrete experiments and validated feature proposals. A short blank issue is fine for a simple documentation fix.
- Pull requests: proposed changes with their rationale, actual validation and research impact. Small fixes do not require a prior discussion or issue.

Link the conversation when an idea becomes actionable. Prefer one concrete question or change per issue/PR. Maintainers can request a minimal scenario before classifying a discrepancy; a temporal policy losing to EDF is not itself a correctness bug. See the [collaboration guide](docs/github-collaboration.md) for triage and planning.

## Change and validate

Run format, strict workspace Clippy, workspace tests, release build and `python scripts/tc0.py` before proposing changes. New utility behavior needs boundary coverage. Engine changes need event accounting and replay coverage. Workload changes need a rationale independent of observed scheduler outcomes. Compare all five policies and report losses.

```sh
cargo fmt --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --all-features
cargo build --workspace --release
python scripts/tc0.py
```

Existing CI validates Linux and Windows. Add focused tests when behavior changes; do not add tests merely to mirror a documentation edit. State actual checks and any omissions in the PR. Include exact commands, source commit, scenario/policy/seed and relevant event or metric differences when investigating a result. Replay verifies determinism, not independent statistical replication.

## Review research impact

Identify whether a change affects implementation, scenarios, metrics, methodology, experiments or interpretation. Review implementation correctness and experimental conclusions separately: passing tests does not establish a policy advantage, and a failed hypothesis can be a completed, useful experiment.

For research-affecting work, record the hypothesis, primary policy/outcome, independent workload/value assumptions, baselines, controls and falsification criteria before measuring outcomes. Explain the expected effect and which existing results become incomparable. Preserve losing cases and conventional-policy wins. If a frozen protocol has a genuine defect, document the defect and any replacement protocol explicitly; do not silently overwrite it or retune scenarios to improve temporal-policy outcomes.

Report complete comparisons for every declared policy. Changes to event schema or metrics need accounting and compatibility reasoning; workload changes need source/assumption rationale; interpretation changes need links to the unchanged evidence they reinterpret. Regenerate affected canonical artifacts together with clean source provenance, retaining prior protocol/history where conclusions change.

The PR template asks for a problem/change, validation and research impact. Use only the detail the change needs; “documentation only; no result or methodology changes” is enough when accurate.

## Agentic PR review lifecycle

Branch first, implement, validate locally and self-review, then open a PR using the template. Wait for CI and CodeRabbit, read all automated and human feedback, independently verify findings, fix justified issues in one coherent revision and wait for incremental review again. Complete final validation before reporting merge readiness; maintainers merge. See [the review procedure](docs/pr-review-protocol.md) and the authoritative agent instructions in [AGENTS.md](AGENTS.md).

CodeRabbit is mandatory review assistance, not automatically correct. It does not replace CI or the research protocol, authorize weaker validation, or merge code. Missing/skipped/failed review blocks readiness. Automated remediation stops after three substantive fix rounds for human escalation. The read-only helper `python scripts/pr_review_status.py --pr N --wait` provides bounded review snapshots; its feedback includes human and summary comments for manual assessment.

## Commits and research artifacts

Commit `Cargo.lock`. Keep local generated files under ignored `results/local/`; commit only small canonical research artifacts with source provenance. Use concise problem/behavior-focused commit messages. Contributions are accepted under MIT OR Apache-2.0.

Use the existing [changelog](CHANGELOG.md) for meaningful behavior or research changes, not every typo. A changelog heading or crate version does not prove a GitHub release exists. Maintainers choose version/tag and release timing after validation; release notes should identify the source revision, reproduction commands, compatibility changes and evidence limits. Do not publish a release or promise a future phase solely because a roadmap entry exists.
