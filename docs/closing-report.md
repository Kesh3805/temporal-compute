# Temporal Compute: closing report (draft, 2026-11-23)

**Status: the programme is closed.** Five preregistered studies were run between October and November 2026. None found
that feedback-driven compute allocation beats a competent classical or static allocator by the margins it needed.
The research question was sound. Its answer, in every domain we could test for free, was "the incumbent is
already there". This report states what was tested, what was found, why it failed the same way each time, and what
remains usable.

All results were preregistered before data, analysed by frozen code, and reported as classified. No study was
reinterpreted, rerun or tuned after outcomes.

## The idea

*Temporal Compute* proposed that the value of computation depends on when, and on what, it is spent. A controller
that watches intermediate results and reallocates effort by marginal value per cost (E[ΔV]/E[C]) should beat
schedulers and allocators that commit up front.

## The record

| Study | Domain | Preregistered claim | Strongest baseline | Outcome |
|---|---|---|---|---|
| **TC-S1** | Onboard Earth-observation scheduling (simulated, 200 instances, 9,600 jobs) | Temporal-utility scheduling earns ≥ 5% more mission utility | EDF + priority | **FAIL.** −5.07% vs EDF. All five gates failed. Utility-density came within 0.35% of EDF. |
| **TC-IA1** | Rendering allocation, synthetic (exploratory) | Value-of-information or robust-variance allocation beats cost-aware Neyman | Plug-in cost-aware Neyman | **REFUTED.** A true-variance oracle ties the plug-in rule (−0.2% ± 2.2%). Even a clairvoyant greedy policy gains nothing. |
| **TC-IA2** | Rendering estimators, synthetic (exploratory) | Robust estimators beat the mean where allocation could not | Sample mean, fixed clamp | **CLOSED.** Unbiased spatial control variates are impossible on this corpus. The robust winsorizer is not non-inferior at high budget (−12% at 16,384 spp). |
| **TC-R1** | Physically based path tracing (PBRT, 30 frames, 6 policies, 3 timing repeats) | The generic marginal-value controller beats uniform, MC-UCB and variance-guided by ≥ 10% | Variance-guided / cost-aware | **INCONCLUSIVE.** 717/720 units completed. One unit failed an estimator-consistency check in every repeat. The prospective ceiling of the cost lever was about 6%, below the 10% bar. |
| **TC-01-HG** | LLM self-consistency stopping (20 models × 120 problems × 80 samples) | Two-sided, token-aware stopping leaves ≥ 20% headroom over Adaptive-Consistency | Adaptive-Consistency τ = 0.95 | **Stage 0 FAIL.** Hopeless questions are predictable (AUROC 0.91), but abandoning them saves only 10.8%, and half of that is static. |
| **TC-HP1** | Can the Stage 0 gate *predict* adaptive-compute wins? (6 held-out method/benchmark pairs) | Labels agree on ≥ 5/6 and Spearman ≥ 0.6 | — | **FAIL.** 4/6, Spearman −0.54. Hindsight headroom is about 90% for every sampling problem, so it does not discriminate. |

## Why it failed the same way each time

Every case fell into one of two shapes:

1. **Smooth, concave returns.** Rendering error falls as O(1/n), and deadlines value completion in a known order.
   Here the optimal allocation is a closed-form plug-in rule: EDF, or Neyman n ∝ σ/√c. Our controller's E[ΔV]/E[C]
   is single-step metareasoning (Russell & Wefald, 1991). With concave returns and additive cost, its KKT optimum
   *is* that plug-in rule. A generic controller can at best converge to it, and it pays estimation noise and
   overhead on the way. TC-S1, TC-IA1 and TC-R1 rediscovered this wall empirically.
2. **Large headroom that is static, not temporal.** On LLM sampling, a difficulty-knowing oracle would cut tokens by
   91%. But that oracle knows each question's difficulty *before* running. Mid-run feedback recovers little of it:
   about 11% by abandonment, and agreement-based stopping wins or loses depending on base accuracy (+74% on GSM8K,
   −27% on hard MATH). What predicts the outcome is a property known up front.

The general claim, "a generic marginal-value controller beats competent domain allocators", is therefore withdrawn
as a known theorem shape, not an open question. The narrower question, "when does feedback-driven allocation
materially beat static allocation?", met the same answer five times: **not where the incumbent is mature and the
data is public.**

## What remains usable

- **The Stage 0 gate as a kill filter.** Before building anything, compare the strongest baseline, a static oracle
  and a dynamic oracle on a pilot trace, with confidence intervals, an observability check, a written baseline
  audit, and a cost cap of 2 days. It rejected TC-01-HG in half a day with no CI. Run backwards, it would have killed
  TC-S1 and TC-R1 within 48 hours. **It is not a predictor** (TC-HP1). Hindsight oracles overstate headroom
  wherever luck can be selected after the fact. Use it to say *no* cheaply, not to say *yes*.
- **Reusable infrastructure.** This includes:
  - preregistration with freeze hashes and tags;
  - deterministic paired execution on free GitHub runners (717 jobs, bit-identical images across repeats);
  - sharded reference rendering up to 2^21 spp;
  - range-read extraction of JSON from parquet files and from Actions artifact zips (60 GB of artifacts read as 304 MB);
  - TC-01-HG and TC-HP1 replay code for test-time sampling policies.
- **A methodological lesson.** Specify headroom targets strictly inside both frontiers (TC-01-HG amendment A1 put
  the target at an unstable endpoint). Check design flaws on synthetic data before data is read (TC-HP1 amendment
  A1 caught a degenerate baseline this way).

## Process record

- Freeze and tag discipline held in every study. There were no post-outcome amendments. Pre-data amendments are
  dated and committed before data (TC-R1 0003–0007, TC-01-HG A1, TC-HP1 A1).
- The council (Claude coordinating, ChatGPT with web search, Gemini) produced the 2026-11-21 recalibration that
  withdrew the central claim and adopted Stage 0.
- Cost: zero spend. All compute was free GitHub-hosted runners and a laptop.

## Where the records are

| Study | Record | Branch |
|---|---|---|
| TC-S1 | `docs/tc-s1/results.md` | `main` |
| TC-IA1/IA2 | `docs/tc-ia1/README.md` | `research/tc-ia1-council` (local) |
| TC-R1 | `docs/tc-r1/`, `research/tc-r1/execution-result/README.md` | `research/tc-r1-execution-runner` (pushed), `research/tc-r1-execution` (result local) |
| Recalibration | `docs/recalibration/` | `research/tc-r1-execution-runner` and `research/tc-hp1` |
| TC-01-HG | `docs/tc-01-hg/result.md` | `research/tc-01-hg` → `research/tc-hp1` (local) |
| TC-HP1 | `docs/tc-hp1/result.md` | `research/tc-hp1` (local) |

## Open items for the maintainer

1. Whether to push the local result branches and merge the records into `main` through the review protocol.
2. Whether to publish this report externally (for example as a short negative-results write-up). Nothing has been
   published.
3. Repository housekeeping: archive or label the programme, and close or annotate open PRs (#29, #30).
