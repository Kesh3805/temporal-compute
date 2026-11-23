# TC-01-HG result — Stage 0 FAIL (2026-11-21)

**Classification: FAIL. All three numeric gates fail. Under the preregistration, the domain claim (two-sided,
token-aware stopping leaves ≥ 20% headroom over tuned agreement stoppers) is rejected. No controller study follows.**

Preregistration: [preregistration.md](preregistration.md), committed `7aa47fd` before data, plus pre-data amendment
A1 (`04cfde9`). Script: `experiments/tc-01-hg/audit.py`, unchanged after the data was read. Full output:
`results/tc-01-hg/audit-result.json`.

Data: Hugging Face `AnonymizedTMLRSubmission/reasoning-traces` `meta/` (MIT), with 10 columns read by HTTP range
requests (`fetch_columns.py`, sha256 9878b133…). That gives 192,000 rows = 20 models × 120 problems × 80 samples,
with no unit excluded. Combined hash of the local column files: 0c17186c…. SC@80 is wrong on 39.1% of units. The
median sample is 13,027 completion tokens.

## Gates

| Gate | Rule | Result | Verdict |
|---|---|---|---|
| G1 headroom | lower 95% CI of H ≥ 20% | H = 56.3%, CI [−85.6%, 66.5%] | **FAIL** |
| G2 observability | AUROC ≥ 0.70, R_4 ≥ 10%, accuracy loss ≤ 0.5 pp | AUROC 0.907, R_4 = 10.8%, loss 0.508 pp | **FAIL** (accuracy loss misses by 0.008 pp) |
| G3 dynamic share | R_4 − S_0 ≥ 10 pts | 10.8% − 5.3% = 5.5 pts | **FAIL** |

A\* (Adaptive-Consistency τ = 0.95) = 60.7% accuracy at 393,560 tokens per unit. The cheapest frontier policy at A\*
was that same policy. Per-model H ranges from −595% to +77%: 14 of 20 models are positive and 6 negative.

## Reading (not a reinterpretation of the verdict)

1. **Hopeless questions are very predictable.** From the first 4 samples, held-out AUROC is 0.91 (0.71 from t = 0
   features alone). Acting on that prediction saves only about 11% of tokens at the allowed accuracy cost, and half
   of that comes from a static decision. Abandonment is a real but modest lever. It is not the ≥ 20% the claim
   needed.
2. **G1's wide interval comes from how A1 is built.** It evaluates both frontiers at the top accuracy O_abandon can
   reach, where that frontier is steep and unstable (see gpt-oss-20b_low at −595%). A1 was fixed before the data and
   it works against the claim. It is kept as is. Lesson for future gates: specify headroom at a target strictly
   inside both frontiers.
3. **Context oracles (non-gating).** A difficulty oracle that knows each unit's p(n) curve would need 91% fewer
   tokens than B at A\*. A per-permutation hindsight oracle reaches 65.0% accuracy at 26k tokens. So the waste sits in
   *how many samples each problem gets*, which needs knowing difficulty in advance. That is the across-question
   allocation problem where UAB (arXiv 2605.26849) realized only about +2% over uniform. It is not evidence for
   this claim, and it is not a new claim.
4. **Declared bias:** AIME-class problems favour abandonment. The claim still failed there, so an easier benchmark
   would not rescue it.

## Decision

TC-01-HG is closed as FAIL. Per the recalibration, the next candidate is the backup claim, which needs its own Stage 0
preregistration: online cascades beat static thresholds only under workload drift (RouterBench-style logs). The
alternative is to reconsider the programme. The Stage 0 gate did its job: this rejection cost about half a day and
zero CI.
