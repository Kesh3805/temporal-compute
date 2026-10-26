# Amendment 0007: extended reference effort for frames that halt at 32768 spp

Status: **adopted 2026-10-26 by the research owner (Claude, by maintainer
handoff).** Timing:

- No comparative outcome exists, and no policy has run on any primary scene.
- The 8192-spp convergence results were known (`docs/tc-r1/references-8192-result.md`).
- No 16384 or 32768 result was known.

The original protocol, amendments 0001–0006 and the convergence thresholds are
unchanged. JSON: [reference-amendment-0007.json](../../../research/tc-r1/reference-amendment-0007.json).

## Why

The protocol escalates a non-converged frame 8192 → 16384 → 32768 spp and then
halts that scene and the PASS gate. At 8192 spp:

- Both specular scenes' reference pairs differ by relative MSE 0.0086–0.023,
  86–232× the 1e-4 bar.
- The adaptive scenes miss SSIM or MSE by 4–8×.

If error halves per doubling, those 12 frames cannot converge by 32768, and the
experiment would be INCONCLUSIVE for lack of references rather than for
anything about the policies. The registered 32768 limit was a projected-cost
choice made before any renderer was selected ("8192 spp is a provisional
reference effort, not ground truth"). Sharding a stream's sample range across
free hosted jobs makes much higher reference effort affordable at no cost.

## Rule

- **Who extends.** A frame whose registered 32768-spp decision is `halt`
  continues at 65536, 131072, … up to a **ceiling of 2^21 = 2,097,152 spp per
  stream**, doubling each level.
- **What stops it.** At each level the unchanged thresholds decide `converged`
  or `escalate`. A frame that fails at the ceiling halts its scene and the PASS
  gate, exactly as originally registered.
- **Why that ceiling.** It was fixed before any 16384 or 32768 result, from cost
  alone. At about 580 s per 8192 spp on a 4-vCPU runner, one stream at 2^21 is
  about 41 runner-hours, split into 64 shards of 32768 spp.
- **Rendering.** Each stream is the Film estimate over sample indices
  `[0, spp)` for its registered identity and seed, using the validated portable
  worker binary (run 40165734171).
- **Sharding.** It is rendered as disjoint 32768-spp shards, each a worker DUMP
  of `[begin, end)`, then combined by count-weighted mean. The independent
  sampler fixes each sample by pixel and index, so the combination is the
  full-prefix estimate. Shards of lower levels are reused by higher levels
  because they are the identical deterministic prefix.
- **Validation on primary data.** Shard `[0, 32768)` of every extended stream
  must equal that stream's registered 32768-spp image within the frozen E2
  tolerance (`check_shard_prefix.py`). The extended convergence step re-verifies
  linear MSE independently of the metric report.
- **Retention.** All levels and shards are retained.
- **Scoring reference.** It is the mean of A and B at the first converged level,
  as before.

## Limits

Heavy-tailed specular noise may still fail at the ceiling. That remains a halt,
reported as INCONCLUSIVE for those scenes, not a pass. Extending reference effort
changes no policy, metric, threshold, corpus asset or analysis rule. Issue #9
stays open.
