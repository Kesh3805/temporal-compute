# TC-HP1 result: FAIL (2026-11-22)

**Verdict: FAIL.** The result is informative. The gate's win/lose call agrees with the realized outcome on 4 of 6 pairs (the bar was 5). Spearman(ĝ, g) = −0.54 (the bar was ≥ 0.6). Under the
[preregistration](preregistration.md) (`ea9c58c`, amendment A1 `76f27a6`), the Stage 0 gate is **not** a predictor
of adaptive-compute wins. It stays in use only as a cheap filter, and the programme takes option A: close it.

The predictions (`results/tc-hp1/predictions.json`) were committed in `bbee2a1` before `realize.py` ran on real
data. No script, grid or pair changed after `76f27a6`. Input hashes are in `results/tc-hp1/data-hashes.txt`. The
GSM8K file has 127 questions, not 128; all rows were used.

| Pair | H (lower CI) | D | Obs | Predicted | Realized g | Realized | Agree |
|---|---|---|---|---|---|---|---|
| P1 ASC vs SC@16, MATH 8B | 0.92 (0.90) | 0.72 | 0.83 | WIN | −0.27 | LOSE | ✗ |
| P2 ASC vs SC@16, GSM8K 8B | 0.92 (0.91) | 0.48 | 0.93 | WIN | +0.74 | WIN | ✓ |
| P3 ESC vs ASC .95, MATH 70B | 0.97 (0.95) | 0.94 | 0.90 | WIN | −0.17 | LOSE | ✗ |
| P4 abandonment vs ASC .95, MATH 8B | unreachable (−1) | — | 0.67 | LOSE | 0.00 | LOSE | ✓ |
| P5 online vs static router, drift | 0.38 (0.21) | 0.43 | 0.57 | LOSE | +0.06 | LOSE | ✓ |
| P6 same, shuffled | 0.72 (0.71) | 0.70 | 0.58 | LOSE | −0.01 | LOSE | ✓ |

## Reading

1. **The gate's oracle headroom does not discriminate.** For sample-stopping problems, the per-permutation
   hindsight oracle always shows about 90% headroom: it stops at the first sample whose plurality happens to be
   right. H was 0.92–0.97 on all three SC pairs, and the realized gains were −0.27, +0.74 and −0.17. Observability
   (0.83–0.93) did not separate them either. The gate passed exactly the cases where an agreement stopper beats a
   fixed N on an easy benchmark (GSM8K, q_B 0.87). It also passed the cases where it loses: hard MATH at 8B
   (q_B 0.38), where answers rarely agree, and ESC vs ASC at 70B.
2. **The correct LOSE calls were mostly mechanical.** P4: on this data the abandonment oracle cannot even reach the
   target, so H ≤ 0 by construction. P5/P6: Obs < 0.70 decided the call. Two of the four agreements came from the
   declared partial tautology, and Spearman is negative.
3. **What does predict the SC outcomes is base accuracy** (agreement exists only when the model is mostly right).
   That is a static, t=0-flavoured property. It fits the programme-wide pattern that the exploitable signal is
   static, not feedback-driven. This is noted, not claimed: it was observed after the outcome.

## Decision (preregistered)

FAIL → option A. Temporal Compute closes as a research programme once TC-R1 reports, with a negative-results write-up:
- TC-S1, TC-IA1/IA2, TC-R1 and TC-01-HG;
- the common mechanism;
- the Stage 0 gate as a cheap kill filter, with this result showing it is not a predictor.

There will be no new studies, controllers or domain hunts. TC-R1 finishes or hits its cap as frozen. Its outcome is
reported exactly, and it goes into the write-up.
