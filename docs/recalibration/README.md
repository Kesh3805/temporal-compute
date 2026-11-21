# Temporal Compute — central-idea recalibration (2026-11-21)

Council: Claude (coordinating; [blind position](claude-blind.md) written before reading replies), ChatGPT with web
search (thread `chatgpt.com/c/6b01556f-bb64-83e8-be22-4c02af9ada44`), Gemini Neon High (thread
`gemini.google.com/u/1/app/bc28bb9c80c6b7f4`). Same [brief](brief.md) to both. No outcomes were used or changed.

## Verdict on the central idea

**All three agree: the performance claim is withdrawn; the research question is kept.**

- *Withdrawn premise:* "a generic marginal-value controller beats competent domain-specific adaptivity." E[ΔV]/E[C]
  is Russell & Wefald (1991) single-step metareasoning. With smooth concave returns (O(1/n) Monte Carlo) and additive
  cost, the KKT optimum is a closed-form plug-in rule (EDF, Neyman n ∝ σ/√c), so a generic controller can at best
  converge to it while paying estimation noise and overhead. It sees *less* structure than the domain allocator.
  TC-S1, TC-R1 and TC-IA1 rediscovered this wall empirically; it was not bad luck with domains.
- *Kept question:* when does feedback-driven compute allocation materially beat a static/classical allocator, and
  can we predict that **before** building anything?

### Necessary conditions for a >10% feedback win (Gemini; consistent with ChatGPT and Claude)
All must hold together:
1. **Heterogeneity that static t=0 features cannot predict.** Per-item optimal compute spans about 10× or more. If
   cheap upfront features predict it, a static router wins and feedback isn't needed.
2. **Cheap mid-run observability.** Partial execution sharply narrows the remaining marginal value (c_obs ≪ c_step).
3. **Non-smooth stopping geometry or non-stationarity.** Big gains come from discrete exit or abandonment (0–1
   loss, verifiers, consensus, giving up on hopeless items) or from drift, not from re-weighting 1/n curves.
4. **A suboptimal incumbent.** The strongest published baseline leaves real oracle headroom (unlike EDF at 98.5%).

## New process rule — Stage 0 headroom gate (adopted)

Before any controller code, execution freeze, or more than 2 days of laptop/CI time, compute on a pilot or public
trace with the **same action space, objective and costs** as the proposed experiment:

- `B`: the strongest literature baseline (never uniform).
- `O_stat`: the best allocation using only t=0 features (no feedback).
- `O_dyn`: the clairvoyant reactive oracle (hindsight, same action granularity), with bootstrap CIs. A max over
  noisy outcomes is an optimistic estimate.

Proceed only if **all** hold:

| Check | Threshold (for a 10% pass bar) | Source |
|---|---|---|
| Oracle headroom `O_dyn` vs `B` | ≥ 2× bar (≥ 20%), lower CI bound | ChatGPT 1.5×, Gemini 2.5×; Claude picks 2× |
| Dynamic share `O_dyn` vs `O_stat` | ≥ bar (≥ 10%); otherwise it's a static routing problem, not Temporal Compute | Gemini |
| Observability | Out-of-sample prediction of remaining marginal value from mid-run telemetry (AUROC ≥ 0.70 or a meaningful R²) | both |
| Baseline audit | Written: the strongest known method, its optimality assumptions, and which one this domain violates | ChatGPT |
| Substrate cost | Ground truth for Stage 0 costs ≤ 2 days of free compute | Gemini |

Retro-check: TC-S1 (EDF 98.5% of oracle) and TC-R1 (ceiling about 6% vs a 10% bar) would both have been killed in
under 48 hours.

## Next domain (convergent): LLM test-time compute, starting with an audit only

Both models independently ranked it first. It is feasible with **no GPU** by exact replay of public pre-generated
rollout logs (N ≥ 32 samples per question, with correctness and token counts).

**Warning (Claude, verified by search):** this field is crowded. Adaptive-Consistency (Aggarwal et al. 2023,
[arXiv:2305.11860](https://arxiv.org/abs/2305.11860)) reports up to 7.9× fewer samples at <0.1% accuracy loss.
ESC (2024), ReASC ([arXiv:2601.02970](https://arxiv.org/html/2601.02970v1)), CASE (Findings EMNLP 2026) and
across-question budget allocation ([arXiv:2605.26849](https://arxiv.org/pdf/2605.26849)) followed. This is the same
trap shape as rendering. The baseline is therefore the tuned adaptive stoppers, never uniform N, and the Stage 0
gate decides.

**First study, TC-01-HG (headroom audit, no controller):** the sharpest candidate claim is Gemini's
*two-sided, token-aware stopping*. Agreement-only stoppers burn the full cap on hopeless queries, and they count
samples while rollouts vary 3–10× in tokens. On 2–3 public rollout sets (e.g. MATH-500, GSM8K, a code set):
- the share of tokens tuned ESC / Adaptive-Consistency spend on questions still wrong at N_max;
- `O_dyn` (per-item optimal stopping in tokens, including abandonment) and `O_stat` vs tuned baselines plus a
  trivial per-query token cap;
- the observability of "hopeless" from the first k samples.
Before Stage 0 runs: a literature check for 2025–2026 work on hopeless-query abandonment and token-aware stopping.

**Backup claim (Gemini B):** online feedback cascades beat static thresholds *only under workload drift*. Run it on
RouterBench-style public multi-model logs. The baseline is a static threshold plus a 5-line dual-ascent pacer.

**Rejected domains for now:** HPO early stopping (ASHA/Hyperband already harvest it), adaptive MCMC (failures are
unobservable mid-run), and CI test selection (data friction). Simulation-based inference was split: ChatGPT ranked
it 2nd; Gemini said skip because it is GPU-bound and SNPE already adapts. Defer it.

**Secondary deliverable (Gemini C, Claude endorses):** a cross-domain "headroom audit" write-up that turns TC-S1,
TC-R1, TC-IA1 and TC-IA2 into evidence for when adaptive compute cannot pay. Only if it predicts gain orderings on
held-out benchmarks.

## TC-R1 — split decision, needs maintainer call

| | Position |
|---|---|
| ChatGPT | **Retire unrun.** It hasn't failed empirically; it failed prospective headroom. Running it to get a FAIL label is sunk-cost spending. Close it as "Retired unrun — insufficient predicted headroom; no empirical result." |
| Gemini | **Launch once, frozen, hard cap, then close path tracing forever.** Marginal cost is tiny, and an empirical result inside the 6% ceiling is clean evidence for the headroom-audit claim. Abort and log as terminated if it needs >24–48 h unattended CI or babysitting. No TC-R2 under any outcome. |
| Claude | **Launch with Gemini's cap** (2 of 3). The freeze is verified, and a run is free on public-repo runners. A measured gain versus a predicted ceiling is the calibration point the new Stage 0 gate needs. Zero further engineering either way. |

Either way: **no further investment in path tracing**, and no reinterpretation of any outcome.

### Maintainer decision (2026-11-21): launch with hard cap

Recorded before the execution tag and before any comparative outcome exists.

- **Wall-clock estimate:** ~80 min per unit (6 policies × ~13 min, the cap-calibration median of 789 s)
  × 720 unit-jobs ÷ 20 concurrent free runners ≈ 48 h for all three repeats.
- **Hard cap:** 72 h from the first execute-repeat marker push. If the three workflow runs are not all complete
  by then, cancel whatever is still running. Record TC-R1 as **INCONCLUSIVE — terminated at hard cap**, and analyse
  nothing as a partial PASS.
- **No babysitting:** workflow re-runs are already refused by the guard (`GITHUB_RUN_ATTEMPT = 1`). No marker is
  re-pushed, and no code, threshold or config changes after the tag. Failed units are reported as the protocol
  defines (incomplete → INCONCLUSIVE).
- **After any outcome:** report it exactly with `analysis_adapter.py`, write a short postmortem comparing the
  measured gain to the ~6% analytic ceiling, and close path tracing. There will be no TC-R2.
