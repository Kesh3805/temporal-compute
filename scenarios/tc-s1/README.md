# TC-S1 compact frozen corpus

Definitions are reproduced from `research/tc-s1/preregistration.json` by `scripts/tc_s1_generate.py`. The checked-in `research/tc-s1/corpus-manifest.json` records every seed and exact scenario SHA-256, including prespecified sensitivity variants, controls and reduced oracle problems.

```sh
python scripts/tc_s1_generate.py
python scripts/tc_s1_generate.py --export results/local/tc-s1-scenarios
```

Exported files are ordinary JSON representations of the existing `tc-ir::Scenario`, read by the evaluation-only Rust batch adapter. The generator never imports or calls scheduling code. This directory intentionally avoids thousands of duplicate checked-in scenario files; complete definitions are recreated and hash-checked before evaluation.
