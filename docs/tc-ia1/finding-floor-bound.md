# Finding F1 — the 0.5 floor's "2× uniform" rationale needs equal costs

Status: SUPPORTED (analytic + synthetic). Raised by ChatGPT in Round A (claim d); derived and checked by Claude.
Scope: a documentation-level correction to the *stated rationale* of TC-R1 amendment 0004. The floor
rule itself is unaffected, and nothing here is a TC-R1 outcome. TC-R1 frozen documents are not edited.

## Derivation

Image MSE with equal-size regions: `M(n) = (1/K) Σ σ_r² / n_r`. Floor: `n_r ≥ α n̄`, `n̄ = mean(n)`.
Then `M(n) ≤ (1/(α n̄)) (1/K) Σ σ_r²`.

Uniform at the **same ray budget** `B = Σ n_r c_r` gives every region `n_u = B / Σ c_r`, the
cost-weighted mean of `n`. So

    M(n) / M(uniform) ≤ (1/α) · n_u / n̄ = (1/α) · [Σ n_r c_r / Σ c_r] / n̄.

This is `≤ 1/α = 2` exactly when `cov(n_r, c_r) ≤ 0` across regions. With equal costs it is always 2.
A cost-blind policy that puts more samples into expensive regions (e.g. specular regions that are both
noisy and long-pathed) gets a weaker guarantee.

## Synthetic check (experiments/tc-ia1/floorcheck.py, cost log-sd 1.0, 6 scenes per cell)

| family | policy | median bound | max bound |
|---|---|---|---|
| diffuse | variance-guided | 1.97 | 2.24 |
| diffuse | MC-UCB | 2.01 | 2.14 |
| diffuse | cost-aware | 1.36 | 1.49 |
| caustic | variance-guided | 1.95 | 2.39 |
| caustic | MC-UCB | 1.99 | 2.20 |
| caustic | cost-aware | 1.54 | 1.61 |
| mixed | variance-guided | 1.86 | 1.96 |
| mixed | MC-UCB | 1.91 | 2.45 |
| mixed | cost-aware | 1.56 | 1.64 |

## Consequence

Amendment 0004's wording ("bounds error at 2× uniform") is exact only for equal per-sample costs. Under
TC-R1's ray charging the guarantee for variance-guided and MC-UCB is `2 · n_u/n̄`, observed up to ~2.45 here.
This does not change any rule, threshold or outcome. If the maintainer wants it recorded, the right place is
a post-outcome erratum note, not an edit to the frozen amendment.
