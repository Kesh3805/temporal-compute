# TC-IA1 E1 preregistration — correlated spike footprints (written before running)

Question: does intra-region spatial correlation of rare spikes open ≥ 10% allocation headroom over plug-in
cost-aware Neyman at TC-R1-like region size?

Design (experiments/tc-ia1/footprint.py, sim.py with `foot` parameter):
- 64 regions × 256 pixels (16×16). Spike draws are shared by all pixels in a k×k footprint block per sample;
  each pixel's marginal distribution is unchanged. k ∈ {1, 4, 8, 16} (effective independent spike draws per
  sample per region: 256, 16, 4, 1).
- Families: caustic, mixed (diffuse has no spikes). Cost log-sd 0.52 (the measured fixture value).
- 12 scenes × 2 seeds per (family, k). Checkpoints 32/64/128/256 mean cost per pixel. 16-spp init, 4-spp
  batches, 0.5 floor on adaptive policies.
- Policies: uniform, variance-guided, MC-UCB (scale-equivariant), plug-in cost-aware, robust-myopic (MoM),
  skeptical Neyman (Gemini H1), oracle-greedy and oracle-static (true σ).
- Effect = 1 − exp(mean over units of mean log(MSE/MSE_costaware)). Also report each checkpoint.

Kill criteria (fixed now):
- K1 (Gemini): at k = 8 and k = 16, if neither oracle (static or greedy) nor skeptical beats plug-in cost-aware
  by ≥ 10% in log-averaged relative MSE in either family → close the statistical-allocation track for this
  synthetic family.
- K2 (ChatGPT): if no (family, k) shows oracle headroom ≥ 12% → stop allocation-only VOI work here.
- If headroom ≥ 12% appears somewhere, a candidate advances only if it recovers ≥ half of that gap without
  worsening worst-region error; that would need a new preregistered test on fresh seeds.

Limitations stated up front: synthetic iid-across-samples model; 24 units per cell (CIs reported); no
rendering; no controller-time charging (ray-matched only).
