SHARED EVIDENCE PACKET — exploratory study TC-IA2 (estimator efficiency per charged ray)
Source: public repo github.com/Kesh3805/temporal-compute; prior study TC-IA1 (branch research/tc-ia1-council, local). Nothing here is a TC-R1 outcome. TC-R1 itself forbids controller-specific denoising, clamping or estimator changes, so this is a separate study by construction.

SETTING (same as TC-IA1)
- Progressive Monte Carlo rendering: PBRT-v4 unidirectional path tracer, 256x256 frames, 16x16-pixel regions. Common 16-spp init, then 4-spp batches; cost is charged in traced rays. Current allocation: plug-in cost-aware Neyman (n_r ∝ sigma_r/sqrt(c_r)) with a defensive floor n_r >= 0.5*mean(n).
- Current per-pixel estimator: the unweighted sample mean of that pixel's samples (box reconstruction).
- Metric used so far: relative linear-radiance MSE vs an independent high-sample reference, log-averaged over ray checkpoints 2^20..2^26; also worst 16x16-region relative MSE, SSIM, LPIPS (fixed display transform), end-to-end time.
- Heavy tails dominate the hard scenes: specular/caustic frames need > 2^20 spp before two independent references agree to relative MSE <= 1e-4.

WHAT TC-IA1 ESTABLISHED (synthetic; lognormal base + rare Bernoulli spikes; 12 scenes x 2 seeds per cell)
- Allocation is exhausted: plug-in cost-aware Neyman ties a true-variance oracle under the same floor (-0.2% ± 2.2%); even a clairvoyant reactive policy that knows true means and each pixel's current error does not beat it. Both preregistered kill criteria triggered for allocation-only ideas.
- Under the log-averaged metric, rare spikes matter mainly through the fireflies that actually land. True-variance oracles lose 5–37% once spikes are spatially correlated (k x k pixel footprints).
- Median-of-means variance estimation lost up to 42% because it discards isolated spikes; leverage-damped variance changed nothing.
- Both models concluded the next lever is the estimator, and disagreed on bias:
  - unbiased estimators that exploit spatial covariance / shared path information (control variates, shared-sample or correlated estimators, gradient-domain-style reconstruction);
  - biased robust estimators (firefly re-weighting, Catoni/M-estimators, truncation or shrinkage), consistent as n grows.

CONSTRAINTS
- Zero budget: laptop (i5, 16 GB) + free GitHub Actions. Synthetic experiments first; rendering only if a hypothesis survives.
- Estimators may use only legal runtime information: the samples drawn so far (and any extra probes, charged to the budget). No reference image, no future samples.
- Any comparison is at matched charged rays, including estimator overhead where it is material.
- New ideas get their own preregistration before results.
