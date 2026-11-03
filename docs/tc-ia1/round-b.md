# TC-IA1 Round B — cross-examination (2026-11-03)

Prompts: [round-b-prompts.md](round-b-prompts.md) (both models got the other's claims plus Claude's headroom table).
The first Gemini Round B send was lost by the web UI (no reply, not persisted after reload); it was resent
with one added question (Q4, on the oracle losing under the log metric).

## ChatGPT on Gemini

- Order-independence: correct only for outcome-independent allocations.
- **Flatness coefficient corrected:** with n_r = n*_r(1+δ_r), a_r = c_r n*_r / B, Σ a_r δ_r = 0:
  R/R* = 1 + Σ a_r δ_r² + O(δ³). The excess is the weighted variance of relative misallocation, not half of it.
- "No policy discovers spikes faster than the floor" is **false**: zero-hit observations still update a
  posterior on p, and a policy can always allocate more exploration than the floor.
- Skeptical Neyman: Ṽ ≤ V by construction; it suppresses genuine caustics, and the first spike is exactly
  the evidence the region deserves more samples. Right comparator: calibrated shrinkage.
- Gemini's KG bonus Var(σ²)/n is dimensionally not an MSE reduction.
- Floor: 2× bound holds iff allocation-weighted mean cost ≤ plain mean cost (same as Claude's cov(n,c) ≤ 0).
- **Withdraws priority for its own H1 (finite-horizon VOI):** the oracle gap caps any VOI gain below 10%.
- Decisive experiment: oracle-gap grid over P ∈ {1, 16, 64, 256}; kill if no condition shows oracle headroom ≥ 12%.

## Gemini on ChatGPT

- Oracle-risk weights: with per-pixel MSE averaging, weights enter linearly (√w_r), not squared — notation point.
- The unconditional oracle is optimal only for unconditional E[MSE]; adaptive policies observe realized
  initialization sums and can beat it on realized error (reactive dilution of a firefly that actually landed).
- Pilot-discard design costs the whole 2^20 first checkpoint; selection bias on μ̂_r is O(1/(R n_r)) here.
- MoM on Z discards isolated spikes entirely when p ≪ 1/blocks (systematic underestimation).
- Floor: agrees the 2× bound fails with unequal costs; iff cov(c, n) ≤ 0; suggests defining the floor against
  uniform capacity (n_r ≥ 0.5 B/(R c̄)) to restore it.
- **Concedes** the n = 16 blindness argument: with 4096 pooled init samples a region is ≥ 50% blind only for
  p ≤ ln2/4096 ≈ 1.7e-4; its H1 is inert at that pooling.
- **Concedes** Pareto α ≤ 2 was an error (infinite variance; MSE undefined; must use α > 2).
- Explains oracle loss on log-MSE by reactive dilution + Jensen (E log ≤ log E).
- No candidate clears 10% with iid pixels. Two untested regimes could: (i) **intra-tile spatial correlation**
  of spikes (k×k footprints cut effective sample size to 16–256); (ii) wall-clock gains from epoch scheduling.
- Decisive experiment: k×k correlated spike footprints, k ∈ {1, 4, 8, 16}; kill if neither oracle nor H1 beats
  plug-in cost-aware Neyman by ≥ 10% at k = 8, 16.

## Coordinator synthesis

| Disagreement | Type | Resolution |
|---|---|---|
| Flatness ½ vs 1 | mathematical | ChatGPT correct (Hessian cancels the ½). |
| "No policy beats the floor at discovery" | mathematical | False as stated; true only without priors/side information. |
| Floor 2× bound | mathematical | Both agree with Claude's F1: iff cov(n, c) ≤ 0. |
| Pooling / blindness | factual | Resolved: blindness only for p ≲ 1.7e-4 at P = 256. |
| Why the oracle loses on log-MSE | explanatory | Two compatible mechanisms (typical-scale metric, reactive dilution). Testable via λ = nPp. |
| Where 10% could exist | open | Two concrete proposals: P-sweep (ChatGPT) and spatial footprints (Gemini). Footprints are the more realistic proxy; both run. |

Two rounds done; per protocol no third debate round — run the tests.
