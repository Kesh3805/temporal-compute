# TC-R1 offline gate v2 result: GO (amendment 0004 effective)

Executed once on 2026-10-12, 17:48–18:31 (43 minutes, seven local processes),
under [contract-v2](../../research/tc-r1/offline-gate/contract-v2.json) (commit
`8745456`), implementation `16c5ce3`. The
[result](../../research/tc-r1/offline-gate/result-v2.json) binds the contract,
the [amendment 0004](amendments/0004-comparator-competence.md) JSON as adopted at
`8a6718a` (its later status-only edit to EFFECTIVE changes that file's hash) and
the hashes of all six source modules. Fresh seeds 3–5 under the v2 namespace;
criteria C1–C4 unchanged from v1. PBRT-free; no rendering, primary scene,
reference or controller image-quality score.

**Verdict: GO.** Amended MC-UCB COMPETENT, so **amendment 0004 is effective** for
the execution freeze. Amended variance-guided also COMPETENT. Controller
DISTINCT; not NOISE-DRIVEN.

## Post-result source changes

`experiments/tc-r1/amended_policies.py` was later changed after review (PR #26).
The defensive-floor path now runs the same structural input validation as the
controller's ranking path. That change rejects malformed states only;
decisions on valid states are unchanged, and the gate supplies only valid
states. The result's recorded hash therefore refers to the file at `16c5ce3`,
not the current one. `offline_gate.py` and `offline_gate_v2.py` are unchanged and
still match the recorded hashes. Nothing was re-run.

## Comparator competence

Mean oracle efficiency over seeds 3–5; scales 1e-3 → 1e3.

| Field, mean spp | Uniform | Amended MC-UCB | Amended VG | Original MC-UCB | Original VG |
| --- | --- | --- | --- | --- | --- |
| Gaussian, 64 | 0.50 | 0.94 every scale | 0.95 | 0.50 → 1.00 | 1.00 |
| Gaussian, 256 | 0.50 | 0.94 | 0.95 | 0.50 → 1.00 | 1.00 |
| Lognormal, 64 | 0.58 | 0.92 | 0.93 | 0.58 → 0.96 | 0.97 |
| Lognormal, 256 | 0.58 | 0.94 | 0.94 | 0.58 → 0.98 | 0.98 |
| Rare spike, 64 | 0.14 | 0.67 | 0.67 | 0.14 → 0.61 → 0.44 | 0.44 |
| Rare spike, 256 | 0.12 | 0.60 | 0.60 | 0.13 → 0.74 → 0.13 | 0.13 |

- **Scale equivariance holds exactly.** Amended MC-UCB has identical efficiency
  at every scale; drift is 0 against the 0.05 limit. Original MC-UCB again fails
  (18 failures, drift 0.38–0.61).
- **The floor works as bounded.** On rare-spike fields both amended methods rise
  from 0.13–0.44 to 0.60–0.67, about 5× uniform. The accepted cost is on smooth
  fields: variance-guided drops from 1.00 to 0.95.

## Disclosures

- **The rare-spike failure is seed-sensitive.** Original variance-guided failed
  C3 on v1 seeds (0.079 against uniform 0.127) but passes on v2 seeds (0.13
  against 0.12). The floor was justified by the defensive bound, not by the v1
  number, and it improves rare-spike efficiency on both seed sets. Still, the v1
  failure alone was not a stable property of that method.
- **The two amended conventional methods are nearly the same method** (0.92–0.95
  on smooth fields, identical on rare spikes). The "strongest conventional"
  comparator is effectively one floored variance-proportional allocator with an
  optional bonus. That is competent, but not a diverse baseline set.

## Controller identifiability (amended controller, option A)

| Quantity | v2 | v1 | Rule |
| --- | ---: | ---: | --- |
| Recent lever: equal-cost disagreement, non-exploration | 0.588 | 0.810 | ≥0.10 → DISTINCT |
| Cost lever: full deterministic heterogeneous minus equal-cost | 0.098 | 0.108 | ≥0.10 → DISTINCT |
| Timing noise: full wall homogeneous minus equal-cost | 0.070 | 0.094 | ≥0.10 → NOISE-DRIVEN |
| Full wall clock: heterogeneous vs homogeneous | 0.675 vs 0.675 | 0.916 vs 0.916 | reported |
| No-feedback total variation vs variance-guided | 0.138 | 0.177 | reported |

The controller is DISTINCT **only through the recent lever**. The cost lever now
falls just short of its threshold. The v1 diagnostic showed the recent lever is
the noisy single-batch recent-improvement term; it was not re-diagnosed on v2.
Disagreement fell because the shared floor now decides some steps identically
for both. Wall-clock cost still makes per-region ray cost invisible.

## Consequences

- Amendment 0004 takes effect: amended MC-UCB and amended variance-guided are the
  registered conventional comparators, and the shared floor applies to the
  controller and its ablations. Original contracts stay preserved.
- GO authorizes only the next step from the [next-step brief](next-step-brief.md):
  the remaining design amendment (cost predictor, time cap and cadence, batch and
  retention design), then a bounded one-worker local measurement. It does not
  authorize a host, references or comparative runs.
- Open maintainer question, now sharper: the controller differs from a competent
  baseline mainly through a noisy recent-improvement term, and its cost lever is
  marginal and invisible under wall-clock cost. Whether that is a meaningful test
  of the hypothesis should be decided before the design amendment.
- Issue #9 stays open.
