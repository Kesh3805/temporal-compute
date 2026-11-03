# Claude — blind hypotheses for TC-IA2 (written 2026-11-03 before sending any prompt)

D1 (testbed validity first). TC-IA1's synthetic model gives every pixel in a region the same mean. Any
spatial estimator (pooling, denoising, control variates built from neighbours) would look spectacular on a
flat image and mean nothing. The TC-IA2 testbed must have within-region mean structure (smooth gradients,
hard edges, texture) so spatial estimators pay their real bias. Without it, no spatial result counts.

D2 (biased robust, prediction). Firefly-aware estimators (e.g. per-pixel winsorization at a data-driven
threshold, or Zirr-style cascaded re-weighting) cut log-relative-MSE by well over 10% at 2^20–2^22 rays in
spike-heavy scenes, and the gain shrinks with budget because bias does not average away while variance does.
The interesting quantity is the crossover budget where the biased estimator stops winning, and whether it
lies inside the registered 2^20..2^26 range. Prior art (Zirr et al. 2018; median-of-means rendering;
clamping) makes the mechanism non-novel; only the crossover characterization might be useful.

D3 (unbiased covariance, prediction). Unbiased control variates need a correlated quantity with a known
mean. Within one frame, neighbour pixels' means are unknown, so a "neighbour control variate" either needs
correlated sampling (same random numbers across pixels — changes the sampler, which TC-R1 holds fixed) or
becomes a biased smoother. Without changing the sampler, I expect the unbiased route to give little
(< 5%) at matched rays; with correlated sampling, gains depend on footprint correlation and need rendering
to judge.

D4 (metric). Because the registered metric is log-averaged relative MSE, a biased estimator's advantage will
look larger in log terms than in mean-MSE terms (it removes the right tail of realized error). Both must be
reported, plus worst-region error, or a biased win could be a metric artifact.
