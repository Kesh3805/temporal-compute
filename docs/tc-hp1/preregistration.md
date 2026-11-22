# TC-HP1 preregistration — does the Stage 0 gate predict adaptive-compute wins?

Status: **frozen before any held-out data is read** (2026-11-22). Context:
[programme reconsideration](../recalibration/programme-reconsideration.md), option B. Time box: results by
**2026-11-27 23:59 IST**, otherwise the study ends INCOMPLETE and the programme takes option A (close it).

## Claim

The Stage 0 gate adopted on 2026-11-21 ([recalibration](../recalibration/README.md)) predicts, *without evaluating
the method*, whether a feedback-driven method M cuts cost by ≥ 10% over a baseline B at B's quality.

## Held-out pairs (fixed; none used in building the gate)

| # | Substrate | M (feedback method, grid) | B (default point) | Expected by literature |
|---|---|---|---|---|
| P1 | Monkey Business MATH, Llama-3-8B-Instruct | Adaptive-Consistency, τ ∈ {.5,.6,.7,.8,.9,.95,.99} | uniform SC, N = 16 | win |
| P2 | Monkey Business GSM8K, Llama-3-8B-Instruct | same as P1 | uniform SC, N = 16 | win |
| P3 | Monkey Business MATH, Llama-3-70B-Instruct | ESC, windows {2,4,8} | Adaptive-Consistency τ = .95 | unclear |
| P4 | Monkey Business MATH, Llama-3-8B-Instruct | abandonment from first 4 samples, on top of B | Adaptive-Consistency τ = .95 | unclear |
| P5 | SPROUT, block-drift stream | online per-category router | static per-category router from a calibration prefix | unclear |
| P6 | SPROUT, shuffled stream | same as P5 | same as P5 | lose |

"Expected by literature" is recorded for transparency only. It plays no part in scoring.

## Data

- **Monkey Business** (`ScalingIntelligence/monkey_business`, MIT), files `MATH_Llama-3-8B-Instruct`,
  `MATH_Llama-3-70B-Instruct` and `GSM8K_Llama-3-8B-Instruct`, auto-converted parquet. These hold 128 questions
  each, with 10,000 samples per question. Only the **first 80 samples** in stored order are used (NMAX = 80).
  - Answers are extracted from the sample text: MATH takes the last `\boxed{…}` with brace matching and whitespace
    stripped; GSM8K takes the number after the last "answer is", else the last number in the text, with commas
    removed and trailing ".0" dropped. Samples without an answer do not vote.
  - The voted answer is correct if any sample with that extracted answer has `is_corrects = True`. If those
    samples disagree, the majority label decides (ties count as wrong).
  - Cost = sample length in characters ÷ 4 (a declared token proxy; no tokenizer is downloaded).
- **SPROUT** (`CARROT-LLM-Routing/SPROUT`, auto-converted parquet). The columns read are `dataset`, `dataset_idx`,
  and `score` / `num_input_tokens` / `num_output_tokens` of `openai-gpt-4o-mini` (cheap) and `openai-gpt-4o`
  (strong). Rows with a missing score for either model are dropped.
  - Cost uses list prices in $/M tokens: 4o-mini 0.15 in / 0.60 out, 4o 2.50 in / 10.00 out.
  - Quality is the judge `score`.
  - The P5 stream is ordered by (`dataset`, `dataset_idx`). The P6 stream is a shuffle with seed 20261122. The
    calibration prefix is the first 10% of each stream.

## Definitions

**Realized gain** `g = 1 − cost_M(q_B) / cost_B`, where `q_B` is B's quality at its default point.
- `cost_M(q)` comes from M's Pareto lower envelope over its grid, linearly interpolated.
- If M's envelope cannot reach `q_B`, then `g = −1` (LOSE). There is **no endpoint fallback** (the lesson from TC-01-HG amendment A1).
- For P4 only, the target is `q_B − 0.005` (an allowed accuracy loss of 0.5 pp), matching TC-01-HG.
- **Realized label:** WIN iff `g ≥ 0.10`.

**Stage 0 quantities,** all computed at the same target quality and **without running M**:
- **H** = `1 − cost_Odyn / cost_B`, with a 95% bootstrap interval over questions (P1–P4) or over 50 contiguous
  stream blocks (P5–P6). 2000 resamples, seed 734923.
- **D** = `(cost_Ostat − cost_Odyn) / cost_B`.
- **Obs** = held-out AUROC (GroupKFold 5, grouped by question, or by stream block for SPROUT) of the mid-run target
  defined per substrate, using only the signal M can see at its first decision.

Oracles reach the target via a Lagrangian, `λ` bisected over 60 steps.

| Substrate | O_dyn (hindsight, same action granularity) | O_stat (t=0 features only, in-sample) | Obs target and features |
|---|---|---|---|
| SC stopping (P1–P3) | per unit-permutation, choose n ∈ 1..80 maximizing correct − λ·cost | per question-length quintile, one n for all units in the bin | "plurality at n=4 equals plurality at n=80"; features = votes of leader, runner-up, distinct answers, entropy, no-answer share at n=4 |
| Abandonment (P4) | B's stops with units that SC@80 gets wrong set to cost 0 (TC-01-HG's O_abandon) | abandon whole length quintiles, chosen in-sample | "SC@80 wrong"; same first-4 features |
| Routing (P5–P6) | per query, the better model given λ (full hindsight) | per category, true full-stream mean Δscore, route if Δ > λ | "strong scores higher than cheap on this query"; feature = running causal per-category mean Δ from all earlier queries |

Units, permutations and plurality ties follow TC-01-HG (R = 20 permutations of the 80 samples, seed 20261121, ties
to the earliest-reaching answer). Cost for P1–P4 is the mean over permutations.

**Methods.**
- ASC and ESC are exactly as in `experiments/tc-01-hg/audit.py`.
- P4 abandonment is TC-01-HG's `realized()` with first-4 features and no model one-hot (one model).
- P5/P6 routers estimate the per-category mean Δ(strong − cheap). Categories unseen so far get the global mean.
  The router sends a query to strong iff the estimate > λ, with λ swept over the 2.5..97.5 percentiles of the
  observed Δ estimates in 39 steps.
  - The static router fixes its estimates on the calibration prefix.
  - The online router updates after every query using both models' scores. This full-feedback assumption is
    optimistic for M and is declared.
  - B's default point is the λ that sends 30% of calibration-prefix queries to strong.
  - Both routers are scored on the post-prefix part only.

## Predictor (frozen)

- **Predicted label:** WIN iff the gate passes: `lower CI of H ≥ 0.20` and `D ≥ 0.10` and `Obs ≥ 0.70`. The gate's
  baseline audit and substrate-cost checks are met by construction here.
- **Predicted magnitude:** `ĝ = clip(min(H_lower, D) · (2·Obs − 1), 0, 1)`.

## Procedure (two-phase, enforced by commits)

1. Write `predict.py` and `realize.py` and validate both on synthetic data. Commit them. **Then** fetch the data.
2. Run `predict.py` on all six pairs. Commit its JSON output **before** `realize.py` is run on real data.
3. Run `realize.py` and commit. Run scoring and commit.

No script, threshold, grid or pair changes after step 1. Defects found later are reported, not fixed silently.

## Scoring and decision

- **Informative** iff at least one predicted WIN and one predicted LOSE, **and** at least one realized WIN and one
  realized LOSE. Otherwise the result is UNINFORMATIVE: report it and take option A.
- **PASS** iff informative, labels agree on ≥ 5 of 6 pairs, and Spearman(ĝ, g) ≥ 0.6.
- **FAIL** otherwise. The gate stays in use as a cheap filter, but it is not claimed to be a predictor. The programme
  takes option A.
- **On PASS:** write up the gate plus the four frozen negative results as a methods contribution. Any extension needs
  its own preregistration.

## Declared risks

- *Partial tautology:* `g ≤ H` always holds, so small H mechanically predicts LOSE. The informative cases are pairs
  with large H, where D and Obs must do the work.
- *Construct mismatch:* in P5, M's advantage comes from learning online what B estimated on a prefix. The gate's D
  (O_stat − O_dyn) does not measure that. The pair stays in as specified, because it tests the gate as adopted, not a
  version tailored to it.
- Character-length cost, one model per file, and 128 questions per file. With six pairs, Spearman is coarse.

## Amendment A1 (pre-data, 2026-11-22)

Found on synthetic data before any held-out data was read. In the P5 stream the calibration prefix holds a single
category, so all static estimates tie and no λ sends 30% of prefix queries to strong (B collapses to all-cheap).
Both routers' estimates now get a seeded tie-breaking jitter of 1e-9 · U(0,1) (seed 20261123), applied identically
to the static and online routers. Nothing else changes. Implementation clarification recorded in `common.py`:
oracle λ search uses bisection over a fixed 401-point λ grid with linear interpolation, so bootstrap resamples use
the same oracle as the point estimate.
