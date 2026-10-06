# Generation II — Adaptive Progressive Computation

**Temporal Compute controls how much computation a problem receives as its state evolves.** The proposed runtime reallocates compute as intermediate results reveal where additional work may have the greatest marginal value. This is the active research question, not a description of currently implemented capabilities.

## What changed and what remains evidence

Generation I allocates whole independent jobs with known costs, fixed completion-time value curves and one execution mode. TC-0 demonstrates semantics and intentional failures. TC-S1 rejects the registered greedy-policy benefit on its independent-from-policy, assumed EO corpus: Temporal Utility loses 5.07% to EDF, Density loses 0.35%, and all primary gates fail. PR #7 was merged unchanged; the original frozen inputs, 15,882 run records, hashes and reports remain intact.

Retire the claim that these fixed temporal heuristics provide meaningful incremental benefit over competent conventional scheduling on the tested model. Do not turn this into a theorem about every scheduling policy or a claim that replayed simulations are independent empirical replications. EDF's 98.53% oracle capture applies to forty **derived nine-job** problems, not the complete 48-job scenarios. We cannot conclude how much optimization headroom remains in the full corpus from that number alone.

## State, actions and feedback

The proposed loop is:

```text
observe computational state
    → identify feasible next actions
    → estimate gain, cost and uncertainty
    → choose and execute a bounded unit of work
    → observe the resulting state
    → repeat or stop
```

Possible future actions include continue, stop, refine, coarsen, branch, prune, reuse, recompute, change fidelity, checkpoint/resume and validate. TC-R1 must start with a narrow rendering action space; it does not implement this entire list or replace the existing `TemporalTask` API.

A conceptual process exposes state, objective, constraints, feasible actions, cost/gain/uncertainty estimates and an action transition. Treat this as a model for the experiment, not a new universal Rust interface to add before evidence.

For feasible actions with positive expected cost, a candidate local score is:

\[
a_t^{\mathrm{greedy}} = \arg\max_{a\in A(S_t)}
\frac{\mathbb E[V(S_{t+1})-V(S_t)\mid S_t,a]}{\mathbb E[C(a)\mid S_t,a]}.
\]

Correctness, risk and budget limits constrain feasibility. Stop is a separate terminal decision; zero-cost administrative actions must not be ranked by division by zero. The process observes the resulting state before choosing again. Value may mean image-quality improvement, error reduction or objective progress, as defined by the domain.

This ratio is **not a proof of an optimal controller**. It can ignore the value of information, delayed gains, action interactions and uncertainty. A controller's estimates can be wrong, and its own computation can cost more than it saves. Tests must include those failure modes. A terminal value/cost ordering with no meaningful feedback would repeat the old limitation.

## Relationship to existing research

Adaptive sampling, rational metareasoning, anytime computation and multi-fidelity methods already study related decisions. Expected value of computation is not new: [Russell's rational-metareasoning account](https://people.eecs.berkeley.edu/~russell/research-bo.html) describes selecting computation steps by expected decision improvement. Rendering already allocates samples using evolving error estimates; [Rousselle, Knaus and Zwicker's 2011 work](https://www.cs.umd.edu/~zwicker/publications.html) couples adaptive sampling and reconstruction. [Tamstorf and Jensen](https://cseweb.ucsd.edu/~henrik/papers/adaptive_sampling/) explicitly discuss adaptive-sampling bias.

The research claim must therefore be incremental and testable: does a reusable state/action/control abstraction buy enough over competent domain-specific adaptivity after overhead and correctness costs? EDF does not supply rendering action choices in TC-0, but it is also not the appropriate strong baseline for this question. TC-R1 competes with adaptive rendering, not weakened whole-job scheduling.

## First gate and conditional future domains

[TC-R1 — Marginal Compute in Path Tracing](tc-r1/preregistration.md) tests rendering work allocation against uniform, conventional adaptive and variance-guided sampling, with a renderer-native comparator where available. Metrics include quality at a fixed ray budget; time to MSE, SSIM and LPIPS targets; actual rays traced; controller overhead; and worst-region error. Finite reference renders and perceptual scores have limitations; they are not exact correctness or universal human-quality guarantees.

If the controller cannot beat strong adaptivity while preserving correctness and end-to-end efficiency, stop or substantially rethink the generic abstraction again. If it passes, a separately registered second domain would test portability rather than infer it from rendering alone.

Diffusion might allocate steps/refinement across candidates; CFD might allocate resolution or iterations against a quantity of interest; molecular dynamics might allocate trajectories subject to valid statistical inference; EDA might escalate candidate fidelity while preserving exact signoff; 3D reconstruction might select updates/splits/pruning. These are hypotheses, not claims of implemented savings or plans to ship every domain. Aircraft design is a potential multi-fidelity study, not a flight-control claim. Space returns only if progressive processing alternatives independently warrant studying quality, bytes, delivery and contacts.
