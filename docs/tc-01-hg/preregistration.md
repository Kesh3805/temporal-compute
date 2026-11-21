# TC-01-HG — Stage 0 headroom audit: two-sided, token-aware stopping (preregistration)

Written 2026-11-21, **before any rollout data was downloaded or inspected.** It follows the Stage 0 gate in
[docs/recalibration/README.md](../recalibration/README.md). It is an audit only: no controller is built. A PASS permits
designing a controller study; it is not a performance claim.

## Claim under audit
In LLM self-consistency, agreement-only adaptive stoppers (Adaptive-Consistency, ESC) stop early on easy questions.
On hopeless questions, where the majority answer at the cap is wrong, they spend up to the full cap. They also count
samples, while reasoning traces vary several-fold in tokens. Claim: abandoning hopeless questions early, with token
cost as the cost measure, leaves **≥ 20% token headroom** at matched accuracy over the best tuned baseline, and
cheap early signals can capture enough of it.

Literature checked first (2026-11-21): Adaptive-Consistency (arXiv 2305.11860), ESC (ICLR 2024), UAB
(arXiv 2605.26849: across-question allocation, +2.3% over uniform, nothing significant at N=16), Knowing When to Quit
(arXiv 2604.18419, ICML 2026: per-trace probe abstention; not compared with ASC/ESC and not token-at-matched-accuracy),
CGES (arXiv 2511.02603), and PRICE (2026 PDF unreadable; not assessed). The audited corner is narrow but not closed.

## Data
- **Primary:** Hugging Face `AnonymizedTMLRSubmission/reasoning-traces`, `meta` config only (Parquet, about 1.36 GiB,
  MIT). It has 120 problems (aime24, aime25, brumo25, hmmt25_feb), 20 model configurations and 80 samples per
  problem (seeds 1234–1313). Fields used: `model_key, data_id, task, seed, extracted_answer, is_correct,
  num_completion_tokens, finish_reason, ground_truth`. Text is never used.
- The unit is a (model, problem) pair. Answers are compared as `extracted_answer` strings after strip; a missing
  answer is its own "none" value that is never correct. A sample's correctness is `is_correct`, and a vote's
  correctness is whether the winning answer equals any sample answer flagged correct.
- If the schema differs from the card (missing fields, or fewer than 80 samples), record the deviation before
  computing any policy result. Units with fewer than 80 samples are excluded and counted.

## Replay
For each unit, R = 20 random permutations of its 80 samples (numpy default_rng, seed 20261121). A policy draws
samples in permutation order. Cost = the sum of `num_completion_tokens` of the samples drawn (prompt tokens excluded,
equal for all policies). Answer = plurality of drawn answers, ties to the earliest-reaching answer. An abandoned unit
returns no answer, which counts as wrong. Metrics: accuracy (mean over units and permutations) and mean tokens per
unit. N_max = 80.

## Policies (each knob swept on a fixed grid)
- **Uniform** SC@n, n ∈ {1, 2, 4, 8, 16, 32, 64, 80}.
- **Adaptive-Consistency** (Dirichlet/Beta stopping as in the paper): stop when P(current leader is the mode) ≥ τ,
  τ ∈ {0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99}, min 2 samples, cap 80.
- **ESC:** windows of w ∈ {2, 4, 8}; stop at the first window whose answers are all identical; cap 80.
- **Token cap:** any of the above with a per-unit token cap T ∈ {¼, ½, 1, 2, 4} × the dataset's median
  single-sample tokens × 8. Stop when the next sample would exceed T.
- **Baseline frontier B:** the lower envelope (min tokens at each accuracy) over all of the above.

## Quantities
- **A\***: accuracy of Adaptive-Consistency at τ = 0.95 (paper default). If B's frontier does not reach A\*, use B's
  maximum accuracy.
- **O_abandon** (gating oracle, the claimed lever): any B policy plus perfect zero-cost abandonment of units whose
  SC@80 plurality is wrong. Its frontier uses the same sweep.
- **Headroom H** = 1 − tokens(O_abandon at A\*) / tokens(B at A\*), using linear interpolation on each frontier.
- **Realized R_k**: abandonment decided from the first k = 4 samples (their tokens are always paid) by a logistic
  regression. Features: number of distinct answers, leader share, answer entropy, fraction "none", mean and max
  completion tokens, fraction finish_reason ≠ stop, plus the model_key one-hot. The label is SC@80 wrong. Use 5-fold
  cross-validation **grouped by problem**. The threshold is chosen on training folds as the maximum savings subject
  to ≤ 0.5 pp training accuracy loss. Unabandoned units continue with the best B policy at A\*. R_k is the token
  reduction vs B at A\* on held-out folds, reported with its accuracy change.
- **Static share S_0**: the same as R_k but with t = 0 features only (model_key one-hot, task, problem-level prompt
  token count) and no samples drawn before deciding.
- Context only (non-gating): O_diff (knows each unit's p(n) curve and mean tokens; knapsack over fixed n per unit)
  and O_hind (per-permutation hindsight stopping, an optimistic upper bound).
- Uncertainty: 2000 bootstrap resamples of problems (cluster = data_id, carrying all models), seed 734923. Report
  the 95% percentile CI.

## Stage 0 gates (all must pass)
| Gate | Rule |
|---|---|
| G1 headroom | lower 95% CI of H ≥ 20% |
| G2 observability | held-out AUROC for "SC@80 wrong" from first-4-sample features ≥ 0.70, **and** point estimate R_4 ≥ 10% with accuracy loss ≤ 0.5 pp |
| G3 dynamic share | R_4 − S_0 ≥ 10 percentage points of token reduction (point estimate). Otherwise this is a static routing problem |
| G4 baseline audit | written below |
| G5 substrate | data plus analysis ≤ 2 days on the laptop |

**PASS** → design a preregistered controller study against B. **FAIL** on G1 → reject the domain claim. **G1 pass but
G2/G3 fail** → classify as "headroom exists but is not cheaply observable" (outcome B/D in the recalibration doc) and
do not build a controller. Results are reported per model as well as pooled. The pooled result is primary.

## G4 baseline audit
Strongest known methods: Adaptive-Consistency and ESC, plus a token cap. Their optimality assumption is that more
samples help until the leader is confirmed, with every sample costing the same. Two assumptions this domain may
violate: (a) on hopeless units the leader is wrong and confirming it is worthless, and (b) sample cost varies several-fold
and correlates with difficulty or failure (long traces, truncation). If neither holds in the data, H will be small and
G1 fails. That is an acceptable outcome.

## Limitations (declared)
AIME-class problems only, with high hopeless rates. That favours the claim, so a PASS here must be replicated on an
easier benchmark before any general statement. All models sample at temperature 0.6. This is a single dataset.
Abandonment counts as wrong, but real deployments may value abstention differently.

## Amendment A1 (2026-11-21, before any real data was inspected)
A synthetic smoke test (`experiments/tc-01-hg/audit.py` on generated data) showed the O_abandon frontier can top
out below A\*. Abandoning SC@80-wrong units also discards the units where a policy got the right answer by stopping
early, so H would be undefined. Rule: H is evaluated at **A' = min(A\*, maximum accuracy on the O_abandon
frontier)**, with the B frontier evaluated at the same A'. Both A\* and A' are reported. R_4 and S_0 are unchanged.
They are still compared against B's tokens at A' and report their accuracy change against A'. The analysis
environment is pinned in `experiments/tc-01-hg/requirements.txt`, an isolated venv, because the global numpy 2.5 is
incompatible with scipy, pandas and sklearn. No real rollout data had been read when this was written: the
column-only fetch was still running and its files were not opened.
