# TC-R1 offline identifiability and competence gate

Status: **contract frozen before implementation or results; maintainer-approved
2026-10-12.** Implements the recommendation of the [next-step brief](next-step-brief.md).
The binding definition is
[contract.json](../../research/tc-r1/offline-gate/contract.json). No PBRT build,
rendering, primary scene, reference or TC image-quality comparison is part of it.

## Questions

1. **Is the registered strong conventional baseline competent?** The unchanged
   MC-UCB adaptation and variance-guided policy run on synthetic per-region noise
   fields (Gaussian, heavy-tailed lognormal and rare bright spikes) at radiance
   scales 1e-3 to 1e3. Each final allocation is scored against the oracle
   allocation `n_r ∝ σ_r` with the same 16-spp floor and total, using true
   variances. Competence requires ≥80% of oracle efficiency, no loss to uniform
   on smooth fields, at most 10% loss to uniform on rare-spike fields, and at most
   0.05 efficiency drift across scales.
2. **Is the controller a distinct method?** The unchanged full controller and its
   equal-cost ablation are shown every state of the variance-guided trajectory.
   We record only how often they would choose a different region. This separates
   three levers: per-region ray cost (deterministic cost, heterogeneous rays per
   sample), the recent-improvement term (equal-cost, exploration excluded), and
   timing noise from a launch-dominated wall-clock cost.

## Decision

| Verdict | Condition | Consequence |
| --- | --- | --- |
| GO | MC-UCB competent, controller distinct | Register the design amendment (cost predictor, β rule, time cap/cadence, batch and retention design), then a bounded one-worker local measurement |
| AMEND-BASELINE | Controller distinct, MC-UCB not competent | Register a comparator amendment justified independently of these numbers before GO |
| STOP-RETHINK | Controller collapsed to variance-guided | Return to a maintainer domain decision; a design-level finding, not a hypothesis FAIL |

If the wall-clock cost makes decisions noise-driven, replacing it is required
before any execution freeze whatever the verdict.

## Limits

One execution after this contract commit. Synthetic fields do not describe the
corpus; corpus rays-per-sample heterogeneity is unmeasured. Distinct decisions are
not better decisions. Thresholds are engineering choices fixed now, not fitted.
No policy parameter may change in response except through a separately
registered amendment justified independently of these results. Issue #9 stays open.
