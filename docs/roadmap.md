# Evidence-driven roadmap

The active research direction is **Generation II — Adaptive Progressive Computation**. TC-R1 — Marginal Compute in Path Tracing is a separate protocol registration, with implementation/assets and an execution freeze still required before measurements. It tests state-aware allocation against competent domain-specific adaptivity. No new runtime or renderer is implemented, and no outcomes exist. See the [TC-R1 protocol](tc-r1/preregistration.md).

## Generation I record and parked roadmap

| Milestone | Scope and gate |
| --- | --- |
| TC-0 | Temporal semantics, deterministic simulation, honest baseline comparison and reproducible measurements. |
| TC-S1 | Completed independent EO workload preregistration and falsification gate. Primary hypothesis FAIL; contact-aware implementation is not justified by this result. |
| TC-S2 | Probabilistic runtime and uncertainty; quantify sensitivity to wrong predictions. |
| TC-S3 | Checkpoint/resume and temporal debt; measure costs before defining policy. |
| TC-S4 | Contact-aware computation, coupled delivery timing and opportunity windows. |
| TC-S5 | Multi-node constellation scheduling, supported by measured single-node limitations. |
| TC-S6 | Flight-software integration experiments; no qualification claim. |
| TC-X | Deep-space distributed temporal computation, contingent on earlier evidence. |

TC-S2+ are parked historical planning boundaries, not current commitments or implemented features. Do not start TC-S2, add contacts or improve the old schedulers as the response to TC-S1. TC-S1 models six fictional EO product classes on the unchanged TC-0 compute semantics. It does not implement contacts, quality levels, delivery or mission pipelines.

The selected next direction is **D: stop or substantially rethink the incremental-advantage thesis** before adding mechanisms. EDF beats both temporal heuristics in the primary aggregate; the primary loses in every registered load/mix group and all twelve sensitivities. Read the [TC-S1 report](tc-s1/results.md). A materially different future hypothesis needs new evidence and independent preregistration; these results do not authorize contact-aware complexity.

## Generation II gate

TC-R1 asks whether a reusable marginal-compute controller improves rendering allocation at a fixed compute budget or target quality over uniform sampling **and strong adaptive sampling**. Its protocol includes adversarial scene families, reference/error checks, controller overhead, worst-region quality and a failure/stop decision. Only after an independent execution freeze and a pass should another domain be considered under a new gate. Diffusion, CFD, molecular dynamics, EDA and 3D reconstruction are motivating possibilities, not queued deliverables. Eventual space work would need progressive computation alternatives and new evidence before contacts.
