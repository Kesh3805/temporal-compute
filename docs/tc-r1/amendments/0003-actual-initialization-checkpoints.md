# Amendment 0003: post-initialization checkpoint increments

Status: **adopted by maintainer decision 2026-10-12, before outcomes; not an
active execution freeze**. This adopts option D of the
[decision brief](0002-decision-brief.md). No comparative outcome, reference or
primary-scene performance observation informed it. The original protocol commit
`99ad341775ed3e60bd262134783eeb2244700e76`, registration/tag, amendment 0001,
[proposal 0002](0002-initialization-aware-checkpoints.md), its
[arithmetic](../../../research/tc-r1/integration/checkpoint-proposal.json) and all
retained evidence remain unchanged. Proposal 0002's `Imax + 2^k` common totals are
**not adopted**. The binding contract is
[checkpoint-amendment-0003.json](../../../research/tc-r1/integration/checkpoint-amendment-0003.json),
validated by `experiments/tc-r1/checkpoint_amendment.py`. It is a new module:
`integration_budget.py` stays byte-identical because the frozen native-validation
contract binds its hash.

## Why

The registered total-ray checkpoint `2^20` is smaller than the 2,097,152 camera
rays of the merged candidates' mandatory identical 16-spp initialization on both
streams. The original totals and the current candidates cannot coexist.

Option D is chosen over A, B and C because it:

- preserves the registered `2^20..2^26` adaptive-work increments exactly, so the
  64x span and geometric spacing survive (A collapses total span to 2.8x and
  moves every checkpoint to high sample counts);
- adds no compute beyond the original increments plus actual initialization,
  typically below A (B multiplies compute 5.2x or 41.8x);
- keeps the frozen Track B/C initialization contracts (C would amend coverage);
- uses an offset that is an observed, policy-independent charge, fixed before any
  allocation decision, never a performance-derived per-case choice.

## Rule

For each scene/frame/replicate unit `u`, checkpoint `k` has nominal total

`T_{u,k} = A_u + I_k`, with `I = (2^20, 2^22, 2^24, 2^26)`.

`A_u` is the **actual** validated charged rays (camera + continuation +
visibility, allocation and production streams) of the mandatory 16-spp
initialization for `u`. `I_k` are the registered values reinterpreted as fixed
post-initialization charged-ray increments.

- **Identity.** Initialization uses identical pixels, sample indices, seeds and
  coverage order for all six policies, so `A_u` must be identical across them.
  The runner asserts equality. A mismatch invalidates that unit as a correctness
  failure; it is retained, never dropped, and blocks PASS.
- **Bounds.** `A_u` is an int with `2,097,152 <= A_u <= Imax = 35,651,584` (one
  camera ray per mandatory sample; the conditional 17-ray bound of 0002). A
  violation is a bound/envelope failure that stops integration. Never widen the
  schedule.
- **Completion.** As in 0002: dispatch complete paired requests only while actual
  cumulative charge is below `T_{u,k}`; complete both streams and their paths;
  score the first committed pair reaching it. Overshoot is at most 34,815. No
  truncation.
- **Accounting.** Never charge `Imax` as observed work, reset counters, or exclude
  pilots or initialization from actual charge.
- **Disclosure.** Report each checkpoint as a **post-initialization increment**,
  with nominal increment, per-unit `A_u`, absolute nominal total, actual charge and
  overshoot.

Primary metric formula, thresholds, comparators, families and seeds are
unchanged. Analysis checkpoint keys remain the increments `2^20..2^26`;
`analysis.py` uses `BUDGETS` only as record keys and labels, never as ray totals.

## Limitations

Absolute totals differ by unit. This explicitly amends the protocol's "fixed
total-ray checkpoints" wording and proposal 0002's "no per-case offset" sentence.
Within a unit every policy is compared at the same nominal total. Across units,
equal increments do not mean equal totals or spp; long-path scenes spend more of
the total on initialization. Reports must say so and must not describe checkpoints
as common total-ray budgets.

## Integration items

- The runner must compute `A_u` from validated per-sample ledgers, call
  `require_identical_initialization` then `unit_checkpoints`, and retain `A_u`,
  totals, actual charges and overshoot per unit and policy.
- Records passed to `analysis.py` must be keyed by increment, with absolute totals
  carried as disclosure fields. The execution-freeze manifest must bind this
  contract.

## Still open

Selected-host native validation of `A_u` identity and bounds, host selection,
stopping/censoring/time cap, strong-baseline competence, references and the
execution freeze. Nothing here authorizes rendering, references or a primary run.
Issue #9 remains open.
