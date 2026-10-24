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
| 1 | Merge PR stack #23–#27 | Amendments 0003–0005 on main | In review |
| 2 | Hosted-runner measurement (non-primary) | Dispatch-latency breakdown, throughput, RSS, bytes per sample, per-region ray spread | Running |
| 3 | Dispatch engineering | Cached kernel observation (done); persistent PBRT worker if native launch dominates; aggregate retention; re-validation contract | Started |
| 4 | Host amendment 0006 | Hosted runners as execution host; all six policies of a unit inside one job; paired order; calibrated cap `C` | Planned |
| 5 | References | 30 frames × 2 independent streams, 8192→16384→32768 spp escalation, sharded across free runners, convergence evidence | Planned |
| 6 | Execution freeze | One manifest binding everything; tag `tc-r1-execution-preregistered` | Planned |
| 7 | The run | One comparative execution; analysis; PASS / FAIL / INCONCLUSIVE report | Planned |

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
