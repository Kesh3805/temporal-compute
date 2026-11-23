# TC-R1 execution result: INCONCLUSIVE (2026-11-23)

**Classification: INCONCLUSIVE.** This comes from the frozen `experiments/tc-r1/analysis_adapter.py` at tag
`tc-r1-execution-preregistered`, unchanged. Adapter error: *"missing quality units; failed units cannot be dropped"*.
Under the [preregistration](../../../docs/tc-r1/preregistration.md), an invalid estimator or incomplete execution is
INCONCLUSIVE. It is never a policy success and never a hidden loss deletion. No comparative number is reported or
analysed.

## Execution

| Run (repeat) | Unit jobs succeeded | Failed |
|---|---|---|
| 44886737222 (r0) | 239 / 240 | adaptive-02 / f1 / 4 (job 136793603400) |
| 44886767127 (r1) | 239 / 240 | adaptive-02 / f1 / 4 (job 136793717660) |
| 44886789566 (r2) | 239 / 240 | adaptive-02 / f1 / 4 (job 136793751991) |

- Markers were pushed at 2026-11-21 08:50:51Z. The runs completed 2026-11-23 10:46–11:12Z, inside the 72-hour hard cap
  (deadline 2026-11-24 08:50:51Z). Nothing was cancelled, rerun or edited.
- In all three repeats the same unit raised `ValueError: native Film estimator mismatch` after about 18 minutes. The
  failure is deterministic, an estimator-consistency defect on one adaptive-scene frame, not an infrastructure
  failure. That job uploaded no result files.

## Adapter inputs

- **Job outputs:** only the `*.json` entries of the 720 unit artifacts, read by HTTP range requests from the artifact
  zips (about 304 MB instead of about 60 GB). Images were not needed by the adapter. This gave 717 summaries, all with
  binary sha256 `ca84d2ff624e…`, cap 1620 s and initialization parity `identical`.
- **Evidence flags:** [adapter-evidence.json](adapter-evidence.json). Each flag cites its basis. `estimator` is false
  because of the mismatch above.
- **Output:** [analysis-report.json](analysis-report.json). Prerequisites: references ✓, baselines ✓, provenance ✓,
  accounting ✓ (checkpoint images are bit-identical across the three repeats for every completed unit), estimator ✗,
  execution_complete ✗.

## Postmortem

- The planned comparison of the measured gain against the analytic ceiling of about 6% cannot be made. The protocol
  forbids analysing an incomplete run as a partial result, and this note does not do so. The prospective ceiling
  (about 6% against a 10% pass bar) stands as the only quantitative statement about the cost lever on this corpus.
- The engineering held up: the frozen binary, the reference set at up to 2^21 spp, the freeze verification and
  deterministic execution all worked across 717 jobs on free runners. The study failed at the last guard, the
  estimator-consistency check, on one frame of the hardest scene family.
- As decided on 2026-11-21: no reruns, no TC-R2, and **path tracing closes**. TC-R1 enters the programme's closing
  negative-results write-up as INCONCLUSIVE (estimator defect, one unit), not as a FAIL.
