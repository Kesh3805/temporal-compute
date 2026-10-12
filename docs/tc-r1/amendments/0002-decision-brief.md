# Decision brief: amendment 0002 checkpoints

Status: **maintainer decision pending; this brief adopts nothing.** Date: 2026-10-12.
It supports decision 1 of the [integration gate](../integration-gate.md). The
[proposal](0002-initialization-aware-checkpoints.md), its
[source-bound arithmetic](../../../research/tc-r1/integration/checkpoint-proposal.json),
the original protocol and every retained result remain unchanged. No policy
performance was observed or used. Merging this brief records options and
consequences only; adoption, rejection or an alternative needs an explicit
maintainer decision committed before any reference or comparative outcome.

## Why a decision is required

The original checkpoints are total charged rays per frame `2^20, 2^22, 2^24, 2^26`.
The merged Track B/C candidates and baseline contract give every policy identical
16-spp initialization on both allocation and production streams: 2,097,152 camera
samples before adaptive work. The first original checkpoint (1,048,576 rays) is
smaller than the camera rays alone, so it cannot contain complete initialization.
Keeping both the original checkpoints and the current candidates is infeasible.

`python experiments/tc-r1/integration_budget.py` reproduces the proposal:
`Imax = 35,651,584`, request bound 34,816, overshoot at most 34,815, totals
`36,700,160, 39,845,888, 52,428,800, 102,760,448`.

## Consequences the proposal does not state numerically

Let `r` be a unit's actual charged rays per camera sample during initialization;
`1 <= r <= 17` in the admitted envelope. Initialization uses identical pixels,
sample indices and seeds for every policy, so its actual charge is a deterministic
property of the scene/frame/seed unit, not of a policy. Paired comparisons within
a unit therefore stay fair under every option below.

1. **The budget span shrinks from 64x to 2.8x.** Checkpoints 1 and 2 differ by
   8.6% of total work. The primary metric averages log error over the four budgets,
   so under the proposal it summarizes a narrow, nearly redundant high-sample range
   rather than the registered low-to-high range.
2. **The regime moves to high sample counts.** At `r=2` the proposed checkpoints
   correspond to roughly 140, 152, 200 and 392 spp per stream; the original
   intended roughly 4–256. Low-budget allocation, where adaptivity may matter
   most, is no longer measured.
3. **Adaptive work before checkpoint 1 varies by scene.** `Imax` reserves the
   worst case, but actual initialization is usually far smaller. Adaptive work
   before the first checkpoint is about 32.5M rays at `r=1.99`, 26.2M at `r=5`,
   and only 1.05M at `r=17`. Long-path scenes, often specular, get much less
   adaptive headroom at the same nominal budget. This remains fair across policies
   but changes what a "budget" means per family.

`r=1.99` is the class-sum ratio observed on the non-primary native validation
fixtures (470,577 rays / 236,672 samples). It is illustrative, not a primary-corpus
measurement.

## Options

| Option | Checkpoints (rays per frame) | Total span | Max work vs proposal | Main cost |
| --- | --- | ---: | ---: | --- |
| A. Adopt as proposed | `Imax + 2^{20,22,24,26}` | 2.8x | 1.00 | Consequences 1–3 above |
| B. Fixed geometric totals above `Imax` | e.g. `2^{26,27,28,29}` or `2^{26,28,30,32}` | 8x or 64x | 5.2x or 41.8x | Large compute increase; new spacing is itself a design choice |
| C. Lower mandatory initialization, e.g. 4 spp | `4spp Imax + 2^{20,22,24,26}` | 7.6x | 0.74 | Amends the frozen Track B/C candidate contracts; weaker initial variance estimates |
| D. Fixed increments above actual initialization | `actual_init(unit) + 2^{20,22,24,26}` | 64x in adaptive work | ≤1.00 (typically ~0.7) | Totals differ by unit; conflicts with the protocol's "fixed total-ray checkpoints" wording |

**A** keeps one shared total for all units and is already implemented in the
proposal arithmetic, but changes the character of the primary metric.

**B** keeps one shared total and restores a wider span, at a multiple of the
compute. The 64x version is infeasible unless a host is far faster than the
qualification runner; the 8x version still narrows the original span.

**C** keeps closest to the original budget range with one shared total. It requires
a before-outcome amendment of `controller-contract.json` and `baseline-contract.json`,
re-run of their synthetic tests and a reason for the new coverage independent of
outcomes. Reducing coverage has to be justified as estimator/initialization design,
not as making the budgets fit.

**D** preserves the registered adaptive-work increments exactly. The offset is an
observed, policy-independent initialization charge known before any allocation
decision. The runner must assert identical initialization charge across policies
for each unit and fail the unit otherwise. The protocol text and the proposal's
"no per-case offset" sentence both need an explicit amendment; reviewers may read
it as a per-case offset even though it uses no performance information.

Rejecting all options without an alternative means the current candidates cannot
run under the registered checkpoints; the gate then returns to a protocol/design
decision.

## Rough compute, not a feasibility claim

One quality pass runs 240 frame renders for each of six registered policies
(three conventional, the controller and two ablations) to the final checkpoint.
At the final checkpoint that is about 9.7e10 rays for the original budgets, 1.5e11
for A, 1.1e11 for C and 7.7e11 or 6.2e12 for B. Using only the qualification runner's
1.39–2.07 million camera samples/s and the fixture ratio above (about 2.8–4.1
million rays/s), A is about 10–15 hours per pass of native kernel time. That
excludes Python orchestration, paired dispatch, logging, metrics, timing
repetitions and references, and it is not a measurement of any host or of the
primary scenes. Host feasibility must be measured on the selected host.

## What the decision record should contain

- The chosen option, or rejection, with its date and a statement that no
  comparative outcome or primary-scene performance informed it.
- For A or D: whether the reduced span (A) or unit-dependent totals (D) are an
  accepted limitation, and how reports must label checkpoints.
- For C: the amended coverage value and its outcome-independent rationale.
- Confirmation that `analysis.py` budgets, the integrated runner and the
  execution-freeze manifest will consume the same adopted checkpoints.

Selected-host native validation of initialization, class bounds and overshoot,
host selection and the stopping/censoring decision remain separate and open.
Issue #9 remains open.
