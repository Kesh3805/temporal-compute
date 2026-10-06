"""Idempotent GitHub labels and planning issues; requires authenticated gh CLI."""
import json
import subprocess
import tempfile
from pathlib import Path

REPOSITORY = 'Kesh3805/temporal-compute'

def gh(*args):
    return subprocess.check_output(['gh', *args], text=True).strip()

def main():
    for name in ['research', 'runtime', 'scheduler', 'simulator', 'benchmark', 'correctness', 'performance', 'docs', 'experiment']:
        gh('label', 'create', name, '--repo', REPOSITORY, '--color', '355C7D', '--description', f'Temporal Compute {name}', '--force')
    existing = {issue['title'] for issue in json.loads(gh('issue', 'list', '--repo', REPOSITORY, '--state', 'all', '--limit', '200', '--json', 'title'))}
    plans = {
        'TC-0 Temporal Kernel': 'Acceptance: checked temporal semantics, deterministic single-CPU simulator, all five policies, seven fixed scenarios, replay/invariant tests, documented assumptions, reproducible results and passing Rust CI. Implementation belongs to TC-0 only.',
        'TC-S1 Earth Observation': 'Planning only. First freeze independent contact-bounded Earth-observation workload and utility definitions plus falsification protocol. Report both temporal heuristics against FIFO, fixed priority and EDF before adding contact or quality mechanisms. Do not assume toy-fixture gains generalize.',
        'TC-S2 Runtime Uncertainty': 'Planning only. Evaluate probabilistic runtime and sensitivity to prediction error after independent workload evidence. No runtime-distribution implementation is included in TC-0.',
        'TC-S3 Checkpointing': 'Planning only. Measure checkpoint/resume costs and define temporal debt before implementing preemption or migration.',
        'TC-S4 Contact-Aware Compute': 'Planning only. Couple compute decisions to delivery opportunities after workload and uncertainty validation. TC-0 has no contact model.',
        'TC-S5 Constellation Compute': 'Planning only. Investigate multi-node scheduling only after single-node limitations and communication costs are measured. No distributed infrastructure belongs in TC-0.',
    }
    for title, body in plans.items():
        if title in existing:
            continue
        with tempfile.TemporaryDirectory(prefix='tc-issue-') as directory:
            path = Path(directory) / 'body.md'
            path.write_text(body + '\n\nSee docs/roadmap.md and docs/research-methodology.md.\n', encoding='utf-8')
            print(gh('issue', 'create', '--repo', REPOSITORY, '--title', title, '--body-file', str(path), '--label', 'research'))

if __name__ == '__main__':
    main()
