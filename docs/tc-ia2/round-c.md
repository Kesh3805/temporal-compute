# TC-IA2 Round C — final interpretations (2026-11-03)

Both models received the E1 table and verdict and were asked for interpretation only. Collection was delayed:
the browser pane froze; ChatGPT's first reply failed ("couldn't load", nothing on the backend) and was
regenerated once; Gemini's send had not gone through and was sent later.

## ChatGPT

- Verdict: scoped success; run one final falsification experiment, then close TC-IA2.
- Why its n·p prediction overshot: it assumed spikes carry ~100% of variance with total suppression. Better
  approximation R(n) ≈ (1 − f) + f·n·p, with f the spike share of variance; f = 0.5 alone floors the ratio at
  ~50%, and aggregation over non-caustic pixels raises it further.
- B1's high-budget stability is "potentially the strongest empirical finding — not yet a demonstrated theoretical
  distinction". Not observing a loss is not proof of non-inferiority (−0.1% at p = 1e-2, 512).
- Proposed E2: freeze everything; extend to 1024, 4096, 16384 spp-equivalent, emphasizing p = 1e-2, diffuse and
  sharp caustic boundaries; compare B1, fixed 10× clamp and the mean. Decisions: (1) stability survives only if
  B1's high-budget disadvantage stays within a 2% non-inferiority margin (one-sided 95% bound); (2) the adaptive
  threshold's advantage survives only if B1 beats the fixed clamp on high-budget MSE with a paired CI excluding 0.
  "Run E2 once. Then close the study regardless of outcome."

## Gemini (Argon High)

- Overshoot: spatial dilution (spikes only in blobs; 0% gain on the base elsewhere) and zero-hit patches at
  p = 1e-4. Notes the worst-region gains (+50–61%) fall inside its predicted 45–85% range.
- Agrees all clamps capture the sparse-firefly gain; the real barrier is high-budget bias when spikes are dense.
  Calls ChatGPT-B1 "strictly non-inferior everywhere" and a "zero-regret, consistent default".
- Recommends closing the synthetic exploration; the only follow-up it endorses is one locked validation of B1 vs
  mean vs 10× clamp "on the cached PBRT-v4 TC-R1 scenes".

## Coordinator assessment

- **Gemini overclaims; ChatGPT is right.** "Strictly non-inferior" and "zero-regret" do not follow from point
  estimates of −0.1% and +0.7% over 24 units; non-inferiority needs a preregistered margin and a one-sided bound.
- **Gemini's suggested validation is not allowed as stated.** TC-R1's primary scenes and references are frozen
  and may not be used before the comparative outcome; a real-render check must use non-primary scenes (for
  example the non-primary measurement fixture) under its own preregistration.
- Agreement: TC-IA2's scoped result stands; open question is only whether B1's growing threshold beats a fixed
  clamp at high budgets. ChatGPT's E2 is the cheap synthetic way to settle it.
