# Evidence-driven roadmap

| Milestone | Scope and gate |
| --- | --- |
| TC-0 | Temporal semantics, deterministic simulation, honest baseline comparison and reproducible measurements. |
| TC-S1 | Contact-bounded Earth observation. First freeze independently designed workloads and value assumptions; then add only the contact/quality mechanisms those workloads require. |
| TC-S2 | Probabilistic runtime and uncertainty; quantify sensitivity to wrong predictions. |
| TC-S3 | Checkpoint/resume and temporal debt; measure costs before defining policy. |
| TC-S4 | Contact-aware computation, coupled delivery timing and opportunity windows. |
| TC-S5 | Multi-node constellation scheduling, supported by measured single-node limitations. |
| TC-S6 | Flight-software integration experiments; no qualification claim. |
| TC-X | Deep-space distributed temporal computation, contingent on earlier evidence. |

TC-S1+ are planning boundaries, not implemented features. Candidate future Earth-observation tasks include cloud rejection, wildfire/ship detection, change detection, compression and classification, with contact windows, compute limits, freshness, quality levels and mission utility. TC-0 does not model these tasks or add speculative interfaces for them.

The immediate next milestone is TC-S1's independent workload specification and falsification protocol, before contact-aware implementation. The existing failure controls make it necessary to test broader evidence rather than assume that either greedy policy is generally successful.
