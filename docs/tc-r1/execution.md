# TC-R1E — execution freeze work in progress

PR #10 merged at `661b21caa768ba8147ee7e9aaf9549c186a3671a`. The original protocol registration remains `99ad341775ed3e60bd262134783eeb2244700e76`, tagged `tc-r1-protocol-preregistered`. Issue #9 remains open.

**Execution is not frozen. No renderer is selected and no TC versus baseline comparison has run.** Do not create `tc-r1-execution-preregistered` until every prerequisite below has evidence and immutable hashes. This branch starts infrastructure qualification, rather than asserting completion through placeholder manifests.

Comparator amendment [0001](amendments/0001-comparator-selection.md) selects one conventional method across the complete corpus for primary quality and independently one for time. Synthetic executable fixtures live in `experiments/tc-r1/test_comparators.py`. The current complete-cap time fixture rejects early censoring; it is not a validated estimator for ray-limit-induced early censoring. Execution must resolve and test that case before freeze.

Qualification uses unrelated synthetic scenes only. Run the local probe in an isolated environment using `qualification-requirements.txt`, then:

```powershell
python experiments/tc-r1/qualify_mitsuba.py --output results/local/tc-r1e-mitsuba.json
python -m unittest discover -s experiments/tc-r1 -p 'test_*.py'
```

The PBRT qualification workflow builds an immutable upstream commit and retains synthetic probe artifacts. GitHub runner measurements concern that runner, not this laptop or eventual experiment hardware.

Remaining sequence: complete renderer qualification and select one; implement common kernel instrumentation; validate uniform estimation; implement and independently validate the strong conventional adaptive baseline; implement the controller without primary comparisons; generate and validate assets; generate and test converged independent references; freeze metrics, hardware, timing and analysis; pass synthetic correctness fixtures; create the execution freeze commit and tag. Only then run the first comparison.

All adaptive methods must receive the same count, mean, variance, standard error, regional aggregation, recent error reduction and estimated sample cost. Reference images and evaluation error are unavailable to policies. Actions are bounded `SampleRegion` and `Stop`, with `SplitRegion` only if explicitly frozen for all eligible policies. No integrator changes, bounce control, denoising, reuse, guiding, reconstruction, fidelity changes or backend migration are policy actions.

Before tagging, the execution manifest must bind renderer source/build and instrumentation, algorithms and configurations, paired stream mapping, assets, reference files and convergence evidence, metrics and analysis implementations, actual hardware/backend, timing/counter semantics, fixture results and amendment history. Preserve original reference requirements and protocol files. No generic `tc-runtime` is introduced.
