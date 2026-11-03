# TC-IA1 E1 result — correlated spike footprints

Preregistration: [prereg-footprint.md](prereg-footprint.md) (written before running). Raw output:
`results/e1_footprint_k{1,4,8,16}.txt`. Code: `experiments/tc-ia1/footprint.py`, `sim.py`.

Effect vs plug-in cost-aware Neyman, log-averaged relative MSE over 4 checkpoints, 24 units per cell
(12 scenes × 2 seeds). Positive = better than plug-in cost-aware.

| family | k (footprint) | skeptical (Gemini H1) | robust-myopic (MoM) | oracle static (true σ) | oracle greedy | MC-UCB | variance |
|---|---|---|---|---|---|---|---|
| caustic | 1 | +0.1% | −1.4% | +3.1% | +3.2% | −6.0% | −3.9% |
| caustic | 4 | +1.0% | −19.5% | −5.0% | −5.6% | −7.0% | −5.1% |
| caustic | 8 | +0.6% | −18.7% | −11.7% | −5.2% | −6.7% | −3.5% |
| caustic | 16 | +1.7% | +0.4% | −11.9% | −6.6% | −3.8% | −2.2% |
| mixed | 1 | +0.2% | −3.1% | +1.9% | +2.1% | −6.8% | −5.0% |
| mixed | 4 | −2.3% | −26.8% | −15.2% | −18.1% | −6.6% | −5.4% |
| mixed | 8 | −1.5% | −41.6% | −23.7% | −26.3% | −3.7% | −2.2% |
| mixed | 16 | 0.0% | +1.2% | −37.5% | −26.4% | −9.5% | −5.4% |

Skeptical-Neyman 95% CIs include zero in every cell.

## Verdict against the preregistered kill criteria

- **K1 (Gemini) triggered:** at k = 8 and 16, neither oracle nor skeptical beats plug-in cost-aware by ≥ 10%.
- **K2 (ChatGPT) triggered:** no cell shows oracle headroom ≥ 12% (max +3.2%).
- Allocation-only VOI / robust-variance work is closed for this synthetic family.

## Decomposition added after preregistration (does not change the verdict)

`oracle_floor` = true-variance index under the same 0.5 floor. In the iid-pixel sweep at 16 px/region,
cost sd 0.5, diffuse: oracle_floor −0.2% ± 2.2% vs plug-in cost-aware, unfloored oracle +2.0..2.8%.
So plug-in cost-aware already matches a floored oracle, and the unfloored oracle's edge (up to +10–12% at late
checkpoints with cost sd 1.0) is the price of the defensive floor, not missing information.

## What the oracle's losses mean

With spatially correlated spikes, the expected-variance oracle loses by 5–37%. A region's realized error is
dominated by which spike footprints actually landed; plug-in policies see those and dilute them, the
unconditional oracle does not. So "oracle with true σ" is **not** an upper bound for adaptive policies on
realized error. The relevant ceiling is a conditional (realized-error) oracle — see the report.

## Limitations

Synthetic model (iid across samples, lognormal + Bernoulli spikes), 24 units per cell, ray-matched only
(controller time not charged), no rendering, 64 regions instead of 256.
