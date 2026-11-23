# TC-IA2 Round A — independent proposals (2026-11-03)

Shared input: [packet.md](packet.md). Claude's blind hypotheses: [claude-blind.md](claude-blind.md).

| Source | Thread | Setting |
|---|---|---|
| ChatGPT | chatgpt.com/c/6ae9b49a-a620-83ec-953c-0bffbb60985f | default, effort Medium, free web UI |
| Gemini | gemini.google.com/u/1/app/6ef9060ba4c94825 | Argon, High (re-selected: the UI had reset to Flash-Lite after the free Argon quota window reset) |

Gemini's reply hit "An error occurred" twice (once inside a long code block); content below is what arrived.

## ChatGPT (theory)

- Neither family guarantees ≥ 10%. B is the shorter path; A needs an informative zero-mean control.
- **Winsorization, exact:** X = lognormal w.p. 1−p, spike a w.p. p; clipped at fixed t: MSE = δ_t² + v_t/n.
  Beats the sample mean iff n < n* = (σ² − v_t)/δ_t². Rare-spike limit, t ≪ a: **n* ≈ 1/p** (advantage
  disappears around one expected spike per pixel). Data-driven thresholds need a pilot split for the identity;
  growing thresholds t_n ∝ n^α (α < 1/2) give consistency, not a guaranteed gain.
- Log-averaging over log-spaced checkpoints weights early wins and late losses equally: no universal shifted
  crossover; must be computed explicitly.
- **Control variates:** Var = σ²(1 − ρ²)/n with a known-mean control ⇒ 10% needs |ρ| ≥ 0.316. With an estimated
  control mean, max gain ρ²·V_Z/(V_Z + W). "Spatial similarity of true means is not covariance of errors":
  independent per-pixel sampling gives ~zero cross-pixel error covariance; CRN would be a sampler change.
- No distribution-free ≥ 10% gain over the mean exists (the mean is MVUE in the normal location model).
- Citations (with web search): Yang & Moon, Imperfect Image-Space Control Variates (SIGGRAPH Asia 2025) —
  to verify; Singh et al. 2019 sample-correlation survey; Misso et al. 2022 debiasing; Buisine, Delepoulle &
  Renaud 2021 MoN firefly removal; Catoni 2012.
- Proposed E1 robust crossover, E2 covariance feasibility (CRN only as a labelled positive control),
  E3 spatial-structure stress test. Kill: paired 95% CI must exclude < 10%; worst-region ≤ 10% worse.

## Gemini (prior art / testbed)

- Dichotomy: A cannot combine neighbours without charged shift rays or known-mean controls; B wins in the sparse
  regime (np < 1) and hits a missing-energy bias wall once np > 1.
- A prior art: gradient-domain PT (Lehtinen et al. 2013; Kettunen et al. 2015; Manzi et al. 2014) — L2
  reconstruction unbiased, L1 biased, shift rays cost 2–4×; image-space CV (Rousselle, Clarberg, Jakob & Zwicker
  2016) and neural CV (Müller et al. 2020); ReSTIR (Bitterli et al. 2020; Ouyang et al. 2021).
- B prior art: Zirr & Dachsbacher (EGSR 2018; **author list corrected** from an earlier "Zirr, Hanika &
  Dachsbacher"), Catoni 2012, Lugosi & Mendelson 2019, Buisine et al. 2021 (venue ~80% sure), DeCoro, Weyrich &
  Rusinkiewicz (EGSR 2010) density-based outlier rejection, Kaplanyan & Dachsbacher 2013 path regularization,
  dual-buffer filtering (Rousselle et al. 2012; Bitterli et al. 2016). Excludes pretrained denoisers.
- "New" would be: B surviving the high-budget crossover under the log metric; gains on top of exhausted
  Neyman allocation; dynamic winsorization T_n ∝ n^β.

## Coordinator finding before Round B

All 30 TC-R1 scenes use `Sampler "independent"` + `PixelFilter "box"` r = 0.5 → independent pixel errors.
Family A has nothing to exploit without a sampler change, and the TC-IA1 footprint model was unphysical for
this renderer (TC-IA1 README corrected). TC-IA2 therefore tests Family B with independent pixels.
