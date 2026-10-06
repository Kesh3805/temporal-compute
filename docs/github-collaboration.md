# Collaborating on Temporal Compute

Temporal Compute is experimental systems research. TC-0 compares five fixed policies on controlled single-CPU workloads. Correct implementation, reproducible measurements and support for a research claim are separate review questions. Conventional-policy wins and temporal-policy failures are part of the evidence.

Start with the [README](../README.md), [architecture](architecture.md), [methodology and kill criteria](research-methodology.md), [metrics](metrics.md), [scenarios](../scenarios/), [canonical results](../results/README.md) and [contribution guidance](../CONTRIBUTING.md).

## Conversation, work and changes

| Surface | Use it for | Useful next step |
| --- | --- | --- |
| [Discussions](https://github.com/Kesh3805/temporal-compute/discussions) | Questions, research ideas, methodology, interpretation and design exploration | Link a focused issue when the question becomes concrete work |
| [Issues](https://github.com/Kesh3805/temporal-compute/issues/new/choose) | Reproducible discrepancies, documentation tasks, defined experiments and validated features | Specify the change or experiment and how completion will be assessed |
| [Pull requests](https://github.com/Kesh3805/temporal-compute/pulls) | Proposed code, scenario, metric, experiment, methodology or interpretation changes | Explain what changed, why, actual validation and result comparability |
| Projects | A lightweight view of selected research and engineering work | Track existing issues/PRs; avoid duplicating their discussion |

Early ideas need no implementation commitment. Small documentation fixes need no prior discussion. Keep blank issues available for simple work; the forms provide structure when it helps. Confidential security reports use [private reporting](https://github.com/Kesh3805/temporal-compute/security/advisories/new), not public conversation.

## Recommended Discussion categories

Keep five categories. GitHub categories have a format; use Q&A for answerable questions and open-ended discussions for research debate.

| Category | Format | Purpose |
| --- | --- | --- |
| Questions | Question and answer | Reproduction, semantics and how to understand the research; mark an answer when resolved |
| Research Ideas | Open-ended | Scheduling ideas, proposed experiments and architecture exploration before concrete scope exists |
| Methodology | Open-ended | Workload/value assumptions, controls, measurement, provenance and falsification |
| Results / Interpretation | Open-ended | Challenge or explain recorded results, losses and validity limits; link the source/artifacts |
| General | Open-ended | Contributor coordination and repository matters outside the four categories |

Discussions is enabled. GitHub initially supplies default categories. In the Discussions category editor, rename Q&A to Questions and Ideas to Research Ideas, retain General, and create Methodology and Results / Interpretation. Review existing content before retiring unused default categories; do not delete discussions to tidy the taxonomy. Category names containing a slash can instead use “Results and Interpretation” if preferred. Category configuration is a GitHub setting, not a repository YAML file. No additional forms or announcement channel are needed initially.

Official reference: [managing categories and formats](https://docs.github.com/en/discussions/managing-discussions-for-your-community/managing-categories-for-discussions).

## Issue triage and labels

Use a small working set from the repository's existing labels plus `reproducibility`:

| Label | Meaning |
| --- | --- |
| `correctness` | Simulator, trace, metric or scenario discrepancy requiring investigation |
| `reproducibility` | Build, replay, provenance or artifact-regeneration problem |
| `research` | Concrete research work with a question and falsification criteria |
| `experiment` | Defined workload/baseline/measurement experiment; often paired with `research` |
| `enhancement` | Concrete capability proposal justified by a current problem |
| `documentation` | Explanations, navigation or contributor guidance |
| `good first issue` | Maintainer-confirmed small scope, reproduction/acceptance criteria and a clear entry point |
| `help wanted` | Work ready for contributors, with validation expectations stated |

Existing area labels may be reused when they help routing; do not add one label for every crate or use labels as another status system. Name affected paths such as `tc-scheduler`, `tc-metrics`, `tc-cli`, `scenarios/` or `results/` in the issue. Existing aliases/default labels are retained to avoid breaking history; prefer the working set above for new triage. A label is not proof that a reported defect or hypothesis is valid.

Ask for missing reproduction details, separate a simulator defect from mistaken scenario interpretation, and link the documented semantics. Move research conversation toward Discussions when no actionable task exists. Feature proposals become implementation work only when their concrete problem and scope are established. Never mark an issue beginner-friendly solely because nobody has started it.

## Lightweight planning

If a board becomes useful, create **one repository-linked GitHub Project** with a board grouped by a single Status field:

| Status | Meaning |
| --- | --- |
| Backlog | A concrete candidate awaiting prioritization or sufficient scope |
| Ready | Scope, acceptance/falsification criteria and validation plan are clear |
| In Progress | Someone is actively doing the work |
| Validation | Code correctness, replay, artifact provenance and research analysis are being checked |
| Review | Proposed change or experiment report is ready for review |
| Done | Change accepted or research gate completed and documented, including a failed hypothesis |

Use linked issues/PRs, their existing assignees and labels. No sprints, estimates, extra fields or automation service are needed. Do not auto-mark an experiment Done merely because its code PR merged; its declared measurements and interpretation must be recorded. A failed hypothesis is not an incomplete experiment. Keep future-phase issues contingent on evidence, not delivery promises. Use milestones only for an actual agreed stage; do not create speculative future milestones from the roadmap.

Official reference: [GitHub Projects board layout](https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/customizing-the-board-layout).

## Review and repository settings

Existing Linux/Windows CI and the manual TC-0 artifact workflow already cover useful validation; no new automation is added. The PR template separates the proposed change, actual checks and research impact. [CODEOWNERS](../.github/CODEOWNERS) routes repository-wide review to the verified repository owner, `@Kesh3805`; it does not invent crate maintainers or enforce branch protection.

Discussions and private vulnerability reporting are enabled. Issue chooser links and templates become the default contributor experience after this branch is merged into main. Category customization and an optional Project board remain UI setup. No Project or release was created by this change.

Maintainers decide whether to adopt a board and how restrictive main's rules should be. If adding a ruleset, select the actual Linux/Windows validation checks shown on PRs; consider PR-based changes and resolved conversations. Required owner approval or approval counts need a workable reviewer arrangement, especially while there is only one verified owner. No ruleset or reviewer quorum is imposed here.

Release/tag timing stays with the maintainer. Follow the existing changelog and contribution guidance; do not fabricate releases, benchmarks, results or next-phase commitments as part of community setup.
