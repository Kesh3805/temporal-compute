# TC-IA2 Round B — cross-examination (2026-11-03)

Both models received the renderer fact (independent sampler + box filter r = 0.5 in all 30 TC-R1 scenes) and
the other's claims. Gemini was asked for plain prose only (its code blocks had triggered UI errors twice).

## Agreement

- **Family A retired** for this configuration: zero cross-pixel error covariance; any neighbour combination that
  cuts variance adds spatial bias (Gemini: Gauss–Markov). Needs CRN/shift paths or exported known-mean path
  auxiliaries — a different study.
- TC-IA1's shared-draw footprint model is unphysical here (both agree). Gemini's refinement: real caustics make
  the *parameter maps* p(x, y), μ(x, y) spatially coherent while samples stay independent — which is how the
  TC-IA2 testbed is built.

## Corrections and additions

- Gemini on ChatGPT's n* ≈ 1/p: with random spike amplitudes (κ = E[A²]/E[A]² > 1), n* ≈ κ/p — later crossover.
- Gemini: avoid wasting a pilot split; two-fold odd/even cross-fitting keeps the decoupling with zero waste.
  Thresholds must use a high-breakdown scale (MAD); an SD-based threshold jumps above the spike once one lands.
- Gemini on (b): before n*, at least 1 − np of pixels have no spike, where winsorization equals the mean; the
  whole gain comes from the np fraction where a firefly landed.
- Gemini on (c): a control correlated only with the base caps the gain at ρ_B²·Var(B)/Var(Y), < 10% when spikes
  dominate.
- ChatGPT: in the spike-dominated limit the candidate/mean MSE ratio ≈ n·p; ≥ 10% needs n·p ≤ 0.9.
- Citation check: ChatGPT confirmed Yang & Moon, "Imperfect Image-Space Control Variates for Monte Carlo
  Rendering", ACM TOG 44(6) Art. 205, SIGGRAPH Asia 2025, DOI 10.1145/3763335 (with code link). Gemini confirmed
  Zirr & Dachsbacher (two authors, EGSR 2018).

## Frozen candidates

- ChatGPT B1 (cross-fitted adaptive winsorization, T = 8·s·(n/32)^¼).
- Gemini B1 (cross-fitted MAD winsorization, T = M + 3S·(n/16)^⅓) and B2 (cross-fitted one-sided Catoni).
Both models' quantitative predictions are recorded in [prereg-e1.md](prereg-e1.md) before any data.
