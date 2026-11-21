# Programme reconsideration (2026-11-21)

Written after TC-01-HG's Stage 0 FAIL, at the maintainer's request ("Reconsider the programme"). The TC-R1 run is
still in flight and nothing here touches it. Its outcome will be reported exactly as the freeze defines.

## The record: four tests, one mechanism

| Study | Domain | What beat us | Why |
|---|---|---|---|
| TC-S1 | Onboard EO scheduling | EDF at 98.5% of oracle | Value-of-time curves were already captured by deadline order |
| TC-IA1/IA2 | Rendering allocation (synthetic) | Plug-in cost-aware Neyman ≈ true-variance oracle | Allocation by concave 1/n returns has a closed-form optimum |
| TC-R1 | Path tracing (in flight) | Analytic ceiling of about 6% vs a 10% bar | Same KKT wall; only the cost lever is left |
| TC-01-HG | LLM self-consistency | Adaptive-Consistency left only about 11% realizable | Hopelessness is predictable, but abandoning it is a small lever |

**The common cause is not bad domain choice.** In every case the extra value of computation was either:
1. **smooth and concave**, so a classical plug-in rule already sits near the optimum (S1, IA, R1); or
2. **large but static**: TC-01-HG's difficulty oracle shows 91% headroom, but that headroom comes from knowing
   difficulty *before* running. It is a prediction problem, not a temporal-feedback problem, and the published
   attempt (UAB) realizes only about 2%.

The surviving gap, "feedback reveals something that t=0 features don't and a classical rule can't exploit", has not
appeared in any domain we could test for free. Russell & Wefald predicted this: metareasoning pays only when the
classical model is mis-specified, and mature fields have already fixed their mis-specification.

## What is actually true about the thesis

- **Dead:** the performance claim that a generic marginal-value controller beats domain allocators. It is a known
  theorem shape, not an open question.
- **Unproven and expensive to keep testing:** "somewhere, feedback allocation materially beats static". Our base rate
  is 0/4. Each new domain needs its own baseline audit, and incumbents are strong precisely where data is public.
- **Genuinely ours:** a methodology that kills these claims cheaply (the Stage 0 gate), and four documented, frozen,
  negative results with oracle decompositions (headroom = static share + dynamic share).

## Options

| | Option | Cost | Expected value |
|---|---|---|---|
| A | **Close the programme.** After TC-R1 reports, write a negative-results report: the four studies, the mechanism, and the gate. Archive the code. | ~1 day | Certain, modest; honest end state |
| B | **Pivot to the gate as the contribution.** Turn Stage 0 into a falsifiable *headroom predictor*: before seeing outcomes, predict the realized gain of published adaptive-compute methods on public traces from O_stat / O_dyn / B decomposition. Cascades-under-drift becomes one held-out test case, predicted before it is run. | ~3–5 days, zero CI | Publishable if predictions hold; if they fail, falls back to A with one more data point |
| C | Keep hunting domains with Stage 0 | ~0.5–2 days each | Low: 0/4 base rate, and the gate keeps saying the same thing |
| D | Chase the static headroom (difficulty prediction for LLM sampling) | Weeks; GPU-adjacent | Crowded ML field, no comparative advantage, and it is no longer temporal compute |

## Recommendation: B, time-boxed, with A as the pre-agreed fallback

B is the only option that turns what we already have into a claim that can still fail informatively.
Rules, to be frozen in a preregistration before any new outcome is computed:

1. **Claim:** the decomposition `realized gain ≤ min(O_dyn − B, observability-limited share)` predicts which
   published adaptive-compute methods deliver ≥ 10% over their strongest baseline, on traces we can replay for free.
2. **Held-out set:** at least 6 method–benchmark pairs not used to build the rule. Candidates: cascades under drift
   on RouterBench-style logs, ESC vs Adaptive-Consistency on a second rollout set, ASHA vs Hyperband on public HPO
   traces (e.g. LCBench/YAHPO surrogates), and early-exit networks on published per-layer confidence logs.
3. **Pass bar:** predicted win/lose labels agree on ≥ 5 of 6 and the predicted gain ranks correlate (Spearman ≥ 0.6).
   Fewer, and the predictor is refuted → option A.
4. **Time box:** 5 working days from the preregistration commit. Overrun → option A, with whatever is complete
   reported as incomplete.
5. **No new controllers, no CI, no reinterpretation of S1/IA/R1/01-HG.**

If the maintainer prefers a clean stop, A is fully defensible: the evidence already supports it.
