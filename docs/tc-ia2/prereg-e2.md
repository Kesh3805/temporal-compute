# TC-IA2 E2 preregistration — high-budget stability of ChatGPT-B1 (written before the run)

Proposed by ChatGPT in Round C. Last experiment of TC-IA2; the study closes after it regardless of outcome.

Question: at high budgets, does B1's growing threshold keep it non-inferior to the sample mean, and does it beat
a fixed 10×-median clamp?

## Design

Same generator and fixed allocation as E1, except: **64×64 frames** (16 regions) and float32 sample storage
(float64 accumulation) so 16384 spp fits in memory. Checkpoints **1024, 4096, 16384** mean cost per pixel.
Families: `diffuse`, `caustic_p1e-2` (emphasis), `caustic_p1e-3`, `mixed`. 12 scenes × 2 seeds per family
(24 paired units); new seed base (20261107) — no E1 scenes reused. Estimators frozen exactly as in E1:
`mean`, `gpt_b1`, `clamp10`. One pilot frame (p = 1e-2, single seed, not part of the 24 units) was run only
to check memory and timing.

## Decisions (fixed now)

Per unit u, high-budget log ratio L_u = mean over the three checkpoints of log(MSE_B1 / MSE_ref).

- **D1 stability** (B1 vs mean): survives in a family if the one-sided 95% upper bound of mean_u L_u
  ≤ log(1.02) (disadvantage within a 2% non-inferiority margin). The stability claim survives overall only if
  it holds in **every** family.
- **D2 adaptive-threshold advantage** (B1 vs clamp10): survives if, pooling all 96 units, the two-sided 95% CI
  of mean_u L_u lies entirely below 0, **and** no family shows B1 significantly worse than clamp10 (family CI
  entirely above 0).
- Worst-region error reported separately; it cannot compensate for failing D1 or D2.

If either decision fails, the E1 scoped result stands and the corresponding stronger claim is rejected.
