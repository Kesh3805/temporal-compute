# TC-R1 research plan: path to the one comparative run

Owner since 2026-10-25: Claude, by maintainer handoff. Constraint: zero budget.
The available compute is this laptop and free GitHub-hosted runners (the
repository is public). Integrity rules are unchanged:

- preregister before outcomes;
- no post-outcome tuning;
- one comparative run;
- PASS, FAIL and INCONCLUSIVE are reported exactly as they come out.

## What the experiment can and cannot show

After amendments 0004 and 0005, the controller differs from competent
variance-guided allocation mainly in being **cost-aware**. It ranks by expected
error reduction per charged ray, which approximates Neyman allocation with
unequal costs (`n ∝ σ/√c`). Variance-guided approximates `n ∝ σ`.

The theoretical ceiling of that difference depends on how much charged rays per
sample vary across regions:

- about 1–2% when the per-region spread is narrow (2–5 rays);
- about 6% for lognormal spread with sd 0.5;
- about 9–22% for wide spreads (1–17 rays, or lognormal sd 1).

The registered bar is ≥10% against the strongest conventional method. A PASS is
therefore possible but not expected by default. The method is classical
stratified-sampling theory applied to rendering budgets; it is not claimed as a
new algorithm. This was computed analytically, with no data, on 2026-10-25.

## Phases

| # | Phase | Output | Status |
| --- | --- | --- | --- |
| 1 | Merge PR stack #23–#27 | Amendments 0003–0005 on main | In review; CodeRabbit free-tier rate limits are the blocker |
| 2 | Hosted-runner measurement (non-primary) | Dispatch-latency breakdown, throughput, RSS, bytes per sample, per-region ray spread | **Done** (run 40123453245) |
| 3 | Dispatch engineering | Cached kernel; persistent PBRT worker; per-dispatch retention | **Done**: worker byte-equivalent, 12.1× faster (run 40124315189) |
| 4 | Host amendment 0006 | Free hosted runners; single validated binary; unit × repeat jobs; cap calibration | **Adopted** 2026-10-25 |
| 5 | References | 8192 spp, 60 streams, sharded; convergence; escalation | Running (run 40125241618) |
| 6 | Integrated dry run | Exact execution path on the non-primary fixture, two repeats, determinism | Ready to trigger once the binary is published |
| 7 | Execution freeze | `execution_freeze.py build`, then tag `tc-r1-execution-preregistered` | Tooling done; waiting on references, `C` and the dry run |
| 8 | The run | Three workflow runs (one per repeat) × 240 units; then `analysis_adapter.py` | Workflow ready |
| 9 | Report | PASS / FAIL / INCONCLUSIVE with full evidence | — |

## Decisions taken under ownership

- **2026-10-25:** the measurement host moved from the laptop's Docker to a free
  hosted runner before execution. The Docker engine was down and would reserve
  half the laptop's RAM.
- **2026-10-25:** cached observation chosen over a NumPy rewrite, because exact
  arithmetic equivalence avoids decision flips from rounding.

## Stop conditions

Stop and report rather than build further if:

- references cannot converge at 32768 spp;
- the free host cannot complete the run within its job limits after dispatch
  engineering;
- re-validation of the persistent worker fails.

Each stop is a documented outcome, not a failure to hide. Issue #9 stays open
until the report.
