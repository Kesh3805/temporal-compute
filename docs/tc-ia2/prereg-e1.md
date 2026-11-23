# TC-IA2 E1 preregistration — robust per-pixel estimators at fixed allocation (written before running)

Question: with TC-R1's renderer configuration (independent sampler, box filter r = 0.5 → independent pixel
errors), does a frozen, biased-but-consistent per-pixel estimator reduce log-averaged relative MSE by ≥ 10%
versus the sample mean, at matched charged rays and identical samples?

Family A (unbiased spatial covariance) is out of scope: zero cross-pixel error covariance in this
configuration (agreed by ChatGPT, Gemini and Claude in Round B).

## Testbed (experiments/tc-ia2/testbed.py)

128×128 frames, 16×16 regions; true mean image with smooth gradient, three hard half-plane edges and a
high-frequency checker texture; lognormal base noise (shape 0.3–0.8); spikes inside 3 (caustic) or 6 (mixed)
circular blobs, **drawn independently per pixel and sample** (k = 1). Spike carries 50–95% of a blob pixel's
variance. Cost log-sd 0.52; mixed adds +0.5 log-cost to spike regions. Allocation fixed: plug-in cost-aware
Neyman + 0.5 floor, driven by sample-mean statistics; every estimator scores the same samples.

Families: `diffuse` (no spikes, control), `caustic_p1e-4`, `caustic_p1e-3`, `caustic_p1e-2` (fixed p),
`mixed` (p ~ logU[1e-4, 1e-2] per blob). Checkpoints 32, 64, 128, 256, 512 mean cost per pixel.
12 scenes × 2 seeds per family (24 paired units).

## Estimators (all frozen; definitions in experiments/tc-ia2/estimators.py)

- `mean` — reference.
- `gpt_b1` — ChatGPT B1: odd/even cross-fit; s = max(median, 1.4826·MAD, 1e-12); T = 8 s (n/32)^¼; mean for n < 32.
- `gem_b1` — Gemini B1: odd/even cross-fit; T = M + 3 S (n/16)^⅓, S = 1.4826·MAD + 1e-4·M.
- `gem_b2` — Gemini B2: cross-fit one-sided Catoni log-influence above the other half's median, α = √(2 ln n / n)/S.
- Literature comparators fixed before the council (not candidates): `mon8` (median of 8 means), `clamp10`
  (clamp at 10× pixel median). Negative control: `box3` (3×3 spatial box; pays edge/texture bias).

## Metrics

Per unit: log relative MSE at each checkpoint; effect = 1 − exp(mean over units of mean over checkpoints of
log(MSE_est / MSE_mean)); paired 95% CI over units. Also worst-region relative MSE (same aggregation), and the
512-checkpoint effect alone.

## Kill / pass criteria (fixed now)

A candidate passes a family only if all hold:
- P1: lower bound of the paired 95% CI of the log-averaged effect ≥ 10% (ChatGPT's criterion).
- P2: worst-region effect ≥ −10%.
- P3: effect at the 512 checkpoint ≥ −5% (Gemini's high-budget non-inferiority gate).
A **broad** claim needs a pass in every spike family and diffuse effect ≥ −2% (P4). Otherwise any pass is
reported as scoped to the families where it holds. No candidate passing anywhere → close the robust-estimator
track for this testbed.

## Predictions made before any data

- ChatGPT: in the spike-dominated limit ratio ≈ n·p; p = 1e-4 large gain throughout; p = 1e-3 gain throughout
  32–512 (crossover ~1000 spp); p = 1e-2 loss beyond ~100 spp. Positive aggregate only for spike-dominated scenes.
- Gemini: p = 1e-4: 45–85% gain at every checkpoint; p = 1e-3: 20–35% aggregate, near parity at 512;
  p = 1e-2: ~15% at 32, losses of 40–200% at 256–512, failing the high-budget gate.
- Claude (claude-blind D2/D4): large low-budget gains shrinking with budget; log effect larger than mean-MSE
  effect.

Limitations: synthetic; 24 units per family; ray-matched only (estimator overhead not charged, all are O(n)
per pixel); single channel instead of RGB.
