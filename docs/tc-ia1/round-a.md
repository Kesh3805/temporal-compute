# TC-IA1 Round A — independent proposals (2026-11-03)

Exploratory, non-primary. No TC-R1 scene, reference or outcome was used.
Shared input: [packet.md](packet.md). Each model got the same packet and a role prompt
([prompts](prompts.md)). Claude wrote [its own hypotheses](claude-blind.md) before reading either reply.

| Source | Where | Model setting |
|---|---|---|
| ChatGPT | chatgpt.com/c/6ae98d86-7cb0-83ee-aa6c-d616b35c5544 | default (Thinking, effort Medium), free/Plus UI, no API |
| Gemini | gemini.google.com/u/1/app/4abcb5224e7a783a | Argon, High, free UI, no API |

## ChatGPT (theory role) — key claims

- Verdict: future-information-aware allocation can beat greedy plug-in allocation, but never the
  true-variance oracle under fixed-allocation unbiased stratified estimation. The only opportunity is
  reducing regret caused by variance uncertainty.
- Oracle risk R* = (Σ w_r σ_r √c_r)² / B with n_r ∝ w_r σ_r / √c_r.
- Estimator warning: outcome-dependent n_r can bias the per-region mean (worked ±1 example, E = 1/4).
  Recommends pilot + independent estimation phase, or Horvitz–Thompson with predictable probabilities.
- H1 finite-horizon Bayesian VOI (two-step rollout on a variance posterior with latent rare-event rate).
- H2 tail-aware robust UCB: median-of-means on Z = (X-μ)², needs bounded 4th moment.
- H3 defensive discovery stream p_t = ε q + (1-ε) p̃. P_miss = (1-p)^m; p = 1e-5 needs ~300k probes for 95%.
- Impossibility: known variances; identical optimal allocations across posterior hypotheses; no horizon
  left; indistinguishable rare events at available budget; infinite variance.
- Claims the 0.5×mean coverage floor is not automatically a 2×-uniform MSE guarantee.
- Recommendation: test H1 against an equally informed robust-myopic ablation; if it only beats naive
  variance, reject the VOI mechanism.
- Citations given: Carpentier–Munos–Antos 2015; Étoré–Jourdain 2010; Wright 2019 (Kadane); Hay–Russell–
  Tolpin–Shimony 2012; Frazier–Powell–Dayanik; Bubeck–Cesa-Bianchi–Lugosi 2013; Hesterberg 1995; Owen–Zhou 2000.

## Gemini (prior-art / counterexample role) — key claims

- Prior art: MC-UCB; Antos–Grover–Szepesvári (GAFS-WL); Étoré–Jourdain; Bubeck et al.; Catoni 2012;
  Frazier–Powell–Dayanik (KG); Chick–Inoue 2001; Russell–Wefald 1991; Rousselle–Knaus–Zwicker 2012;
  Zwicker et al. 2015 STAR; Zirr–Hanika–Dachsbacher 2018; Müller–Gross–Novák 2017.
- **Retracted on request:** "Lin, arXiv:2608.16730 (Aug 2026)" — Gemini states 0% confidence, hallucinated.
- Order-independence: only final n_r at each checkpoint matters; Neyman objective is flat near optimum
  (excess ≈ ½ Var(δ)), so refining σ rarely repays exploration.
- "Blind before the spike": with p = 1e-3 and n = 16, 98.4% of the time the sample carries no information
  about the spike; no local-moment policy can beat the defensive floor at discovering it.
- H1 "Skeptical Neyman": leverage-damped variance (blend of leave-max-out and full variance) to stop a single
  early firefly from locking the budget.
- H2 spatial empirical-Bayes prior (3×3 neighbours) + horizon-aware knowledge gradient.
- H3 geometric epoch scheduling to amortize dispatch overhead.
- Recommendation: H1 + H3 first; deprioritize pure VOI/KG lookahead.
- Kill criteria proposed include: oracle beats MC-UCB by < 12% → insufficient headroom.
- Proposed Pareto α ∈ [1.8, 2.5] in one regime (α ≤ 2 means infinite variance; flagged for cross-exam).
