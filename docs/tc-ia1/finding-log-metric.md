# Hypothesis C3 — mean log-MSE is not minimized by the Neyman oracle under rare spikes

Status: UNDER REVIEW (prediction written before the full sweep results were read).

## Mechanism

Region r: base variance σ_b², plus a spike of size M with per-sample probability p. P pixels, n spp each.
Realized region MSE is the pixel average of squared pixel-mean errors. The spike part of one pixel's error
is M(k − np)/n with k ~ Binomial(n, p).

- Expected region MSE: (σ_b² + M² p(1−p)) / n. This is what Neyman allocation (oracle or plug-in) targets.
- If the expected spike count per region, λ = n·P·p, is ≪ 1, the typical realization has k = 0 everywhere,
  so the realized MSE is ≈ σ_b²/n and log MSE ≈ log(σ_b²/n). The spike term enters E[MSE] but barely
  enters E[log MSE].

So when λ ≪ 1, the allocation that minimizes the *registered* log-averaged metric behaves like Neyman on
σ_b (typical scale), not on σ (true second moment). The true-variance oracle overspends on spike regions
and can lose on the log metric while winning on expected MSE.

## Predictions for the sweep (experiments/tc-ia1/headroom2.py)

1. The oracle's log-metric effect falls as P falls (λ falls): positive at P = 256, smaller at P = 16, can be
   negative at P = 4, most visibly in the caustic and mixed families. Diffuse (no spikes) is unaffected.
2. Policies whose variance estimate tracks typical scale (median-of-means "robust_myopic") gain on the log
   metric relative to their expected-MSE standing at small P.

## Why it matters for TC-R1 interpretation (no outcome used)

TC-R1's 16×16 regions give P = 256, so λ ≪ 1 only for spikes with p ≲ 1/(n·256), i.e. below ~2.4e-4 at init.
For those, any policy's log-metric score mostly reflects typical-scale error. That is a property of the
registered metric, fixed before outcomes. It is not a reason to change it, but it should be stated when
reading a TC-R1 result: a log-metric gain or loss in heavy-tailed scenes may come from how the metric treats
rare spikes, not from allocation quality in expected-MSE terms. TC-R1 also reports untransformed errors,
so both readings will be available.
