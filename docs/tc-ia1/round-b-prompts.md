# TC-IA1 Round B — cross-examination prompts

## Shared evidence (Claude's synthetic headroom check, run before reading either reply's details)

Testbed (experiments/tc-ia1/sim.py): 64 regions × 64 pixels; each pixel draws iid samples
lognormal base + Bernoulli(p) spike, spike p ∈ [1e-4, 1e-2] carrying 30–95% of region variance in 20%
("caustic") or 40% ("mixed", spike regions also 1.65× more expensive) of regions; lognormal per-region
ray cost; 16-spp init, 4-spp batches, 0.5×mean floor on adaptive policies; region variance = within-pixel
sample variance averaged over the region's pixels (TC-R1 style). Checkpoints at 32/64/128/256 mean
cost-units per pixel. 12 scenes per family, one seed each (small; treat as indicative).
Effect = 1 − exp(mean log(MSE_policy / MSE_best)), best = strongest of variance / MC-UCB / cost-aware,
which was plug-in cost-aware Neyman in every family.

| cost log-sd | family | oracle static (true σ) | variance-guided | MC-UCB |
|---|---|---|---|---|
| 0.5 | diffuse | +1.5% | −4.6% | −6.7% |
| 0.5 | caustic | +3.2% | −2.7% | −3.7% |
| 0.5 | mixed | +1.4% | −3.6% | −3.8% |
| 1.0 | diffuse | +7.7% | −13.3% | −15.6% |
| 1.0 | caustic | +8.4% | −13.5% | −13.6% |
| 1.0 | mixed | +6.2% | −13.9% | −14.8% |

Reading: in this testbed, even perfect knowledge of every region's variance improves on plug-in
cost-aware Neyman by < 10%. Region variance is pooled over P pixels, so at init it is estimated from
16·P samples (4096 in TC-R1's 16×16 regions), not 16.
