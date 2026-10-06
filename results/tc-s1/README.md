# TC-S1 canonical artifacts — FAIL

The primary policy earned 524,509 points versus EDF's 552,525 (**-5.07%**). All five preregistered gates failed. Read the [full report](../../docs/tc-s1/results.md), [evidence](../../docs/tc-s1/evidence.md) and [frozen protocol](../../docs/tc-s1/preregistration.md) before interpreting these fictional EO results.

Freeze: `e5d7f916d45ddd63b97d0a50f5067f55a04fa726`, tag `tc-s1-preregistered`. First execution source: `aba8df62e0b485850193da35d3acc12d5c2c485c`. All numerical workload parameters are experimental assumptions. No tuning or scientific errata followed outcomes.

| Artifact | Content |
| --- | --- |
| `aggregate.json` | Primary totals/distributions, all gates, load/mix strata and worst paired losses |
| `paired-comparisons.json` | Every paired delta, quantiles, wins/ties/losses and four bootstrap intervals |
| `class-breakdown.json` | Class utility, completion, expiration, waiting and critical-success data |
| `sensitivity.json` | All twelve variants, all six policies, paired deltas and critical behavior |
| `controls.json` | All seven controls, including ties and temporal-policy failures |
| `oracle.json` | Forty exact optima, schedule certificates, captures and regrets |
| `corpus/metrics.jsonl.gz` | Complete 15,882 per-run metric/class projections with frozen definition hashes |
| `corpus/stream-hashes.json` | Every full canonical event-stream SHA-256 |
| `corpus/traces/` | 48 representative complete run reports, selected by fixed IDs, six policies each |
| `provenance.json` | Freeze/source SHA, seeds/spec digests, tool versions and replay counts |
| `artifact-manifest.json` | SHA-256 for numerical/provenance artifacts; figures and host timing are excluded |
| `performance.json` | Host-dependent elapsed time, excluded from scientific comparisons |
| `figures/` | Nine static PNG/SVG plots generated from retained metrics |

## Reproduce and audit

Use a clean checkout with all tags and the stable Rust toolchain. Python 3.12 is used by CI. Scientific generation/analysis needs only the Python standard library.

```sh
python -m unittest discover -s scripts -p test_tc_s1.py
python scripts/tc_s1_generate.py
python scripts/tc_s1_freeze.py
python scripts/tc_s1_validate.py
python scripts/tc_s1.py --output results/local/tc-s1
python scripts/tc_s1_verify_results.py results/local/tc-s1
python scripts/tc_s1_compare_results.py results/tc-s1 results/local/tc-s1
```

The runner refuses changed frozen inputs and dirty source, regenerates every definition, then simulates every policy twice. It writes complete compressed raw reports locally (about 132 MB), requests and the small retained artifacts. Large raw reports are deliberately regenerable; this repository retains all measured per-run outcomes and full-stream hashes. Re-running changes host/source provenance but must preserve scientific JSON values and canonical uncompressed streams. Compression bytes may vary with zlib versions; comparisons use uncompressed content.

Audit the committed result without scheduling any new jobs:

```sh
python scripts/tc_s1_verify_results.py
```

For figures, use a separate virtual environment and the pinned presentation requirements:

```sh
python -m venv target/tc-s1-figures-env
# Activate the environment using your platform's normal activation command.
python -m pip install -r research/tc-s1/figure-requirements.txt
python scripts/tc_s1_figures.py results/local/tc-s1
```

Default CI validates all frozen definitions and audits retained results on Linux/Windows. The `TC-S1 frozen experiment replay` manual workflow reruns all simulations and compares every scientific artifact with this directory on both platforms. Deterministic replay checks computation, not independent empirical replication.
