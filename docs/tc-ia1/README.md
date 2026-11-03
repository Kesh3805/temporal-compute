# TC-IA1 — information-aware allocation (exploratory, non-primary)

First research cycle of the three-model council (Claude coordinating; ChatGPT and Gemini Argon through their
free web UIs; no API, no spend). Run 2026-11-03 on the laptop. **No TC-R1 scene, reference, protocol or
outcome was used or changed.**

Question: can allocating rendering work by the future value of information beat competent cost-aware
(Neyman-with-costs), variance-guided and MC-UCB allocation, especially when per-region variance estimates
are unreliable (rare, heavy-tailed paths)?

## Answer

**No, not by allocation alone, in this synthetic family.** Classification: **REFUTED** for allocation-only
VOI and robust-variance policies (both preregistered kill criteria triggered). The work is not a TC-R1 result
and does not predict one.

## What each step produced

| Step | Record | Outcome |
|---|---|---|
| Shared packet + role prompts | [packet.md](packet.md), [prompts.md](prompts.md) | Same evidence to both models |
| Claude blind hypotheses (before reading replies) | [claude-blind.md](claude-blind.md) | C1 headroom test, C2 tail-aware variance, C3 log-metric artifact |
| Round A, independent | [round-a.md](round-a.md) | ChatGPT: VOI/robust-UCB/discovery stream; Gemini: Skeptical Neyman, spatial EB+KG, epochs. Gemini retracted one hallucinated citation when asked |
| Round B, cross-exam | [round-b.md](round-b.md) | ChatGPT corrected Gemini's flatness coefficient and "no policy beats the floor" claim; Gemini conceded the n=16 blindness argument and an α ≤ 2 error; ChatGPT withdrew its own VOI priority; Gemini found the strongest open regime (spatially correlated spikes) |
| E0 headroom sweep | results/headroom_*.txt, results/sweep_*.txt | True-variance oracle beats plug-in cost-aware by only 1–3% (cost sd 0.5) |
| E1 footprints (preregistered) | [prereg-footprint.md](prereg-footprint.md), [e1-result.md](e1-result.md) | Kill criteria K1 and K2 triggered |
| E2 current-state oracle | results/e2_cond_k*.txt | Even a clairvoyant greedy policy does not beat plug-in cost-aware |
| Round C, interpretation | [round-c.md](round-c.md) | Both models accept closure and independently point to the estimator |

## Findings

1. **Plug-in cost-aware Neyman is already at the allocation frontier here.** Under the same 0.5 floor, a
   true-variance oracle ties it (−0.2% ± 2.2%, iid pixels, 16 px/region; +0.4% ± 1.5% at cost sd 1.0).
   The unfloored oracle's edge (up to +10–12% at late checkpoints with cost sd 1.0) is the **price of the
   defensive floor**, not missing information.
2. **Even a clairvoyant reactive policy gains nothing.** E2's oracle knows the true means and each pixel's
   current error: vs plug-in cost-aware it is +0.6% / +0.3% at k = 1 and −3% to −22% at k ≥ 4 (caustic / mixed).
   It is greedy and optimizes expected MSE, so it is not a strict bound, but no allocation idea tested came close.
3. **Variance-guided and MC-UCB lose 2–10% to cost-aware throughout**, consistent with the repository's
   analytic cost-lever estimate.
4. **The registered log-averaged metric diverges from expected-MSE-optimal allocation under rare spikes**
   ([finding-log-metric.md](finding-log-metric.md)). True-variance oracles lose 5–37% once spikes are
   spatially correlated or regions are small (P = 16: −3% caustic, −15% mixed). Two compatible mechanisms:
   the log metric tracks typical-scale error; adaptive policies dilute the fireflies that actually landed.
   Relevance to TC-R1 (no outcome used): heavy-tailed scenes' log-metric differences can reflect how the metric
   treats rare spikes; TC-R1 also reports untransformed errors.
5. **Amendment 0004's "error ≤ 2× uniform" rationale holds only when cov(n_r, c_r) ≤ 0**
   ([finding-floor-bound.md](finding-floor-bound.md)). Implied bound reaches ~2.45× for MC-UCB with unequal
   ray costs. Rule unaffected; candidate post-outcome erratum. Raised by ChatGPT, derived by Claude, confirmed by Gemini.
6. **Gemini's Skeptical Neyman** (leverage-damped variance): +0.1% to +1.7% (caustic), −2.3% to +0.2% (mixed),
   CIs include zero everywhere. **Median-of-means robust variance**: up to −42% (discards rare spikes entirely).

## Correction (2026-11-03, found during TC-IA2)

TC-R1's scenes use `Sampler "independent"` and `PixelFilter "box"` radius 0.5, so every sample lands in one
pixel and pixel errors are **independent across pixels**. E1's k×k footprints (one random draw shared by many
pixels) model a cross-pixel error correlation this renderer does not produce. Therefore:
- Findings 1–3, 5 and 6 stand: they rest on the independent-pixel runs (k = 1 and the P sweeps).
- Finding 4's footprint numbers (oracle −5% to −37%) do **not** transfer to TC-R1's configuration; they apply
  only to correlated samplers, wider reconstruction filters or path reuse. The independent-pixel part of
  finding 4 still holds where λ = n·P·p ≪ 1 (P = 16: −3% caustic, −15% mixed; P = 4: −8% to −29%); at TC-R1's
  P = 256 the oracle wins by +1–3%, so the effect is confined to spikes rarer than ~1/(n·256).
The kill decision does not change: K1 and K2 also hold at k = 1.

## Next scientific question (both models converged independently)

Move from *where to sample* to *what the estimator does with the samples*:
- ChatGPT: unbiased estimators that exploit predictable spatial covariance / reusable path information
  (shared-sample estimators, control variates, correlated sampling) at identical ray budgets.
- Gemini: biased robust estimators (firefly re-weighting, Catoni M-estimators, truncated shrinkage).
The bias question separates them and should be the axis of TC-IA2, with its own preregistration. TC-R1 forbids
controller-specific estimator changes, so this is a separate study by construction.

## Limitations

Synthetic lognormal + Bernoulli-spike model, iid across samples; 64 regions; 12 scenes × 2 seeds per cell;
ray-matched only (controller time not charged); no rendering. The 4-px/region sweep (results/sweep_P4_*.txt)
finished after the first commit and agrees: no policy beats plug-in cost-aware; true-variance oracles lose
8–35% in the caustic and mixed families.

## Reproduce

```
cd experiments/tc-ia1
python headroom2.py 0.5 256 12 2
python footprint.py 8
python cond_oracle.py 8
python floorcheck.py
```
