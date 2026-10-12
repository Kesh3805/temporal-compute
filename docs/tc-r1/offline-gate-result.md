# TC-R1 offline gate result: AMEND-BASELINE

Executed once on 2026-10-12 under the [frozen contract](offline-gate.md)
(contract commit `29bfb57`, implementation `4565cd5`). The retained
[result](../../research/tc-r1/offline-gate/result.json) binds the contract
SHA-256 `61610a26…` and the source hashes of `offline_gate.py`, `baselines.py`,
`tc_controller.py` and `progressive_kernel.py`. PBRT-free; no rendering, primary
scene, reference or controller image-quality score. One prior launch attempt
failed to start (wrong working directory) and computed nothing.

**Verdict: AMEND-BASELINE.** Controller DISTINCT; the registered strong
baseline (MC-UCB) NOT COMPETENT; not NOISE-DRIVEN. Wall time 39 minutes on six
local processes, about 20 MB each. This is more than the brief's one-CPU-hour
estimate; the contract set no time limit.

## Comparator competence

Mean oracle efficiency over three seeds (1 = oracle allocation with the same
16-spp floor and total). Scales run 1e-3 → 1e3.

| Field, mean spp | Uniform | MC-UCB (β=1) | Variance-guided |
| --- | --- | --- | --- |
| Gaussian, 64 | 0.44 at every scale | 0.44, 0.44, 0.58, 0.89, 0.99, 1.00, 1.00 | 1.00 at every scale |
| Gaussian, 256 | 0.43 | 0.43, 0.47, 0.68, 0.94, 1.00, 1.00, 1.00 | 1.00 |
| Lognormal, 64 | 0.60 | 0.60, 0.60, 0.68, 0.87, 0.95, 0.95, 0.95 | 0.95 |
| Lognormal, 256 | 0.59 | 0.59, 0.62, 0.75, 0.93, 0.97, 0.97, 0.97 | 0.97 |
| Rare spike, 64 | 0.15 | 0.15, 0.22, 0.51, 0.38, 0.29, 0.29, 0.29 | 0.29 |
| Rare spike, 256 | 0.13 | 0.14, 0.22, 0.59, 0.75, 0.09, 0.08, 0.08 | 0.08 |

- **MC-UCB: NOT COMPETENT (21 failures).** Exactly the predicted scale
  dependence: with β=1.0 in absolute radiance units it equals uniform in dim
  fields and equals variance-guided in bright ones. Drift across scales is
  0.36–0.67 against the 0.05 limit. Its good rare-spike values at mid scales come
  from the same accident, not from a designed property.
- **Variance-guided: NOT COMPETENT (7 failures, all C3).** Near-oracle and
  scale-invariant on smooth fields, but at 256 spp it starves undetected rare
  spikes and is worse than uniform (0.079 against 0.127). At 64 spp it beats
  uniform. All three methods are far from oracle on rare-spike fields.

## Controller identifiability

Shadow decisions on the variance-guided trajectory, scale 1, 256 spp, mean over
fields and seeds.

| Quantity | Value | Rule |
| --- | ---: | --- |
| Equal-cost disagreement, non-exploration (recent lever) | 0.810 | ≥0.10 → DISTINCT |
| Full, deterministic, heterogeneous rays minus equal-cost (cost lever) | 0.108 | ≥0.10 → DISTINCT |
| Full, wall clock, homogeneous minus equal-cost (timing noise) | 0.094 | ≥0.10 → NOISE-DRIVEN |
| Full, wall clock: heterogeneous = homogeneous | 0.916 = 0.916 | reported |
| No-feedback allocation total variation vs variance-guided | 0.177 | reported |

**Interpretation, labeled as post-result diagnosis.** One diagnostic run
(Gaussian field, seed 0, 1,024 decisions; it changes no gate number or policy)
replaced every `recent_improvement` with "unavailable". The equal-cost
controller then agreed with variance-guided on **every** non-exploration
decision (disagreement 0.838 → 0.000; the remaining 0.062 is the scheduled
exploration step). So:

- The controller is "distinct" almost entirely because of its recent-improvement
  term. That term is the single-batch decrease in SE², a very noisy estimate
  whose expectation equals the model term the baseline already uses. Distinct
  decisions are not better decisions; this gate did not measure quality.
- With the current wall-clock cost, per-region ray cost is invisible:
  launch overhead (0.3 s per request) swamps per-ray time, so heterogeneous and
  homogeneous ray fields produce identical decisions. The cost lever exists only
  with a deterministic charged-rays cost, and only barely clears its threshold.
- Timing noise alone moves 9.4% of decisions, just below the 10% flag.

## Consequences under the contract

- AMEND-BASELINE: a comparator amendment, justified independently of these
  numbers, is required before any GO. The evidence points at a radiance-scale
  normalization of β (MC-UCB) and a rare-event safeguard (both adaptive methods),
  but choosing them is a separate registered decision.
- The design questions the brief listed remain: replace the wall-clock cost
  predictor (per-region ray cost is otherwise invisible) and decide whether a
  noisy recent-improvement term is the intended distinguishing feature of the
  controller. A controller that differs mainly through that term is a weak basis
  for the registered hypothesis; this is for the maintainer to judge.
- No policy parameter is changed by this result. Synthetic fields do not
  describe the corpus. No rendering, references or comparative outcomes exist;
  Issue #9 stays open.
