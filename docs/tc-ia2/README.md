# TC-IA2 — estimator efficiency per charged ray (exploratory, non-primary)

Second council cycle (Claude coordinating; ChatGPT and Gemini Argon High via free web UIs; no spend).
Run 2026-11-03 on the laptop. **No TC-R1 scene, reference, protocol or outcome was used or changed.**
TC-R1 forbids controller-specific estimator changes, so this is a separate study by construction.

Question: once allocation is exhausted (TC-IA1), can a different per-pixel estimator cut log-averaged
relative MSE by ≥ 10% versus the sample mean at matched charged rays — unbiased spatial-covariance methods
(Family A) or biased-but-consistent robust methods (Family B)?

## Answer

- **Family A: not possible in TC-R1's configuration** (settled analytically, no experiment needed). All 30
  scenes use `Sampler "independent"` and a box filter of radius 0.5, so pixel errors are independent; there is
  no cross-pixel covariance for an unbiased estimator to exploit. It would need a sampler change (common random
  numbers, shift paths) or exported known-mean path auxiliaries. All three models agreed.
- **Family B: scoped pass, no broad claim.** Two frozen cross-fitted winsorizers clear the preregistered bar in
  the p = 1e-3 and mixed families (13–18% gains, CI lower bounds 11–14%), with worst-region error 49–61% better
  and no loss on the spike-free control. All candidates fail when spikes are frequent (p = 1e-2), and p = 1e-4
  fails narrowly on the CI rule (11.5–12.3%, CI lows 9.0–9.8%).

## E1 results ([prereg-e1.md](prereg-e1.md); raw: results/e1_*.txt)

Effect vs sample mean, log-averaged over checkpoints 32–512; [95% CI low]; worst-region; at 512.

| Family | ChatGPT B1 | Gemini B1 | Gemini B2 | clamp 10× (fixed comparator) |
|---|---|---|---|---|
| diffuse | +0.7%, @512 +0.3% | +1.3%, +1.2% | −2.2%, −3.4% | +1.0% |
| p = 1e-4 | 11.5% [9.0] ✗, worst +50% | 12.3% [9.8] ✗, +55% | 9.0% [6.6] ✗ | 11.7% |
| p = 1e-3 | **15.2% [12.9] ✓**, +49%, @512 +7.6% | **13.1% [11.1] ✓**, +53%, +1.4% | 9.9% [7.9] ✗ | 14.5%, @512 +2.5% |
| p = 1e-2 | 2.2% [1.4] ✗, @512 −0.1% | −3.4% ✗, @512 −18% | −1.6% ✗, @512 −9.7% | 0.3%, @512 −8.0% |
| mixed | **16.7% [13.0] ✓**, +50%, @512 +14% | **17.6% [14.4] ✓**, +61%, +8.4% | **15.7% [13.0] ✓**, +61% | 17.5% |

Median-of-8-means lost 10–36% everywhere (it slows convergence where there are no outliers). The 3×3 box
filter was 10–80× worse, which confirms the testbed makes spatial smoothing pay its real bias.

## What it means

1. **Robust per-pixel estimation buys ~12–18% when spikes are rare and localized, and nothing when they are
   frequent.** Consistent with ChatGPT's crossover n* ≈ 1/p: at p = 1e-2 the 32–512 range is past the crossover.
2. **A plain clamp matches the candidates' headline gains.** What ChatGPT's B1 (T = 8·s·(n/32)^¼, cross-fitted)
   adds is **safety**: it is the only estimator that never loses at the 512 checkpoint in any family (worst −0.1%)
   and never hurts the spike-free control. The fixed clamp loses 8% at 512 when p = 1e-2; Gemini's B1 loses 18%.
   This is an engineering property, not a new estimator (winsorization, cross-fitting and growing thresholds
   are all known).
3. **Both models' quantitative predictions overshot** (Gemini: 45–85% at p = 1e-4; ChatGPT's n·p ratio implied
   near-total gains). Spikes live only in caustic blobs, so base noise elsewhere dominates frame error; the large
   predicted gains appear in worst-region error (+50–61%).
4. Claude's blind prediction D4 (log effect larger than plain-MSE effect) was **wrong**: plain-MSE gains were
   larger (e.g. p = 1e-3: 19.0% vs 15.2%). D1 (testbed must punish smoothing) and D3 (unbiased route gives
   nothing without a sampler change) held.

## E2 — high-budget stability ([prereg-e2.md](prereg-e2.md); raw: results/e2_*.npz, e2_score.txt)

64×64 frames, checkpoints 1024 / 4096 / 16384, 24 new paired units per family; B1, fixed 10× clamp and mean only.

| Family | B1 vs mean (1024 / 4096 / 16384) | one-sided 95% worst case | D1 | B1 vs fixed clamp |
|---|---|---|---|---|
| diffuse | +0.2% / 0.0% / 0.0% | +0.03% | pass | +0.3% (CI −0.5..+1.2) |
| p = 1e-2 | −0.3% / 0.0% / 0.0% | −0.2% | pass | **+59%** (45..69) |
| p = 1e-3 | +4.1% / **−5.5% / −12.0%** | −6.5% | **FAIL** | **+35%** (28..41) |
| mixed | +9.0% / +2.7% / −5.4% | +0.6% | pass | **+49%** (32..62) |

- **D1 stability: REJECTED.** B1 is not non-inferior to the sample mean at high budgets: in the p = 1e-3 regime it
  loses 12% at 16384 spp, where ~16 spikes per pixel are expected and the n^¼ threshold still clips real energy.
  Gemini's "strictly non-inferior / zero-regret" reading is refuted; ChatGPT's caution was right.
- **D2 adaptive-threshold advantage: SURVIVES.** Pooled over 96 units B1 beats the fixed clamp by 39%
  (95% CI 31–46%); the fixed clamp's bias accumulates and it is 62–79% worse than B1 at 16384 in every spike family.

**Closing statement for TC-IA2.** Robust per-pixel estimation gives a real finite-budget gain (13–18%, worst
region ~50%) when spikes are rare and localized; a growing, cross-fitted threshold is far safer than a fixed
clamp; but no tested estimator is free at high budgets — each eventually trades bias for variance badly once
n·p reaches a few. A handoff rule (switch to the mean when the estimated n·p passes ~1) is the obvious next idea;
it was **not tested** here and is not claimed. The study is closed as preregistered.

## Relevance to Temporal Compute (no TC-R1 outcome used)

The estimator, not the allocator, is where a ≥ 10% gain is available in heavy-tailed rendering, but only as a
biased estimator, only in rare-spike regimes, and with no guarantee at high budgets unless the threshold grows.
A future gate built on this would have to be its own preregistered study with real PBRT renders and an
independent reference, and would have to report bias explicitly.

## Records

[packet.md](packet.md), [claude-blind.md](claude-blind.md), [round-a.md](round-a.md), [round-b.md](round-b.md),
[prereg-e1.md](prereg-e1.md). Code: experiments/tc-ia2/{testbed,estimators,e1}.py.

## Limitations

Synthetic, single channel, 128×128, 24 paired units per family, ray-matched only (estimators are O(n) per pixel;
overhead not charged), allocation fixed and driven by sample-mean statistics. Round C interpretations: [round-c.md](round-c.md).
Both models accept the scoped result; ChatGPT proposes one high-budget non-inferiority test (E2) before closing.

## Reproduce

```
cd experiments/tc-ia2
python e1.py caustic_p1e-3 12 2
```
